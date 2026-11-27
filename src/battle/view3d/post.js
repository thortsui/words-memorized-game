// 後製：HDR 繪製 → 泛光（火焰、眼睛、餘燼、魔法會發光暈）→ 色調映射 → 調色（對比、飽和、冷暖分離、暗角、底片顆粒）。
// 只在高畫質時開；掉幀降級成低畫質就整個關掉，回到直接畫到螢幕。
// v2（畫面）：調色 pass 多了幾個「預設關閉」的效果，打怪模式／封面不傳參數就跟原本一模一樣：
//   lift（暗部冷色抬升）、keep（高彩度像素少降飽和＝Boss 主色保留）、ink（水墨筆刷邊的暗角）、
//   flash（全畫面閃光）、chroma（徑向色差）、blur（徑向模糊，指向某個畫面點）。
// 這些參數由 screen2.js 每幀設定；昂貴的取樣（色差、模糊）只在數值 > 0 時才跑（uniform 分支，整個畫面一致，不會拖慢平常的幀）。
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';

const GradeShader={
  uniforms:{tDiffuse:{value:null},uTime:{value:0},uVig:{value:.35},uGrain:{value:.03},uSat:{value:1},uContrast:{value:1},
    uShadow:{value:new THREE.Color(1,1,1)},uHigh:{value:new THREE.Color(1,1,1)},uAspect:{value:1},
    uLift:{value:new THREE.Color(0,0,0)},uKeep:{value:0},uInk:{value:0},uInkC:{value:new THREE.Color(0x0b0a0f)},
    uFlash:{value:0},uFlashC:{value:new THREE.Color(1,1,1)},uChroma:{value:0},uBlur:{value:0},uBlurC:{value:new THREE.Vector2(.5,.5)}},
  vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader:`uniform sampler2D tDiffuse;uniform float uTime,uVig,uGrain,uSat,uContrast,uAspect,uKeep,uInk,uFlash,uChroma,uBlur;uniform vec3 uShadow,uHigh,uLift,uInkC,uFlashC;uniform vec2 uBlurC;varying vec2 vUv;
    float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
    float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
    void main(){vec4 c=texture2D(tDiffuse,vUv);vec3 col=c.rgb;
      // 徑向模糊（重擊瞬間）：往 uBlurC 方向取 6 點
      if(uBlur>.001){vec2 dv=(vUv-uBlurC)*uBlur*.022;vec3 acc=col;for(int i=1;i<6;i++){acc+=texture2D(tDiffuse,vUv-dv*float(i)).rgb;}col=acc/6.;}
      // 徑向色差：紅往外、藍往內
      if(uChroma>.001){vec2 dc=(vUv-.5)*uChroma*.012;col.r=texture2D(tDiffuse,vUv+dc).r;col.b=texture2D(tDiffuse,vUv-dc).b;}
      float l=dot(col,vec3(.2126,.7152,.0722));
      // 高彩度（Boss 主色、特效）少降一點飽和
      float ch=max(col.r,max(col.g,col.b))-min(col.r,min(col.g,col.b));
      col=mix(vec3(l),col,mix(uSat,1.,uKeep*smoothstep(.18,.55,ch)));
      col=(col-.5)*uContrast+.5;
      // 冷暖分離：暗部、亮部各染一點顏色；最暗的地方再抬一點冷色（冷墨底）
      col*=mix(uShadow,uHigh,smoothstep(.05,.75,l));
      col+=uLift*(1.-smoothstep(0.,.32,l));
      vec2 d=(vUv-.5)*vec2(uAspect,1.);float rr=length(d)*1.25;float v=1.-uVig*smoothstep(.35,1.05,rr);col*=v;
      // 水墨邊：邊緣用雜訊打散的筆刷狀墨色（不是正圓漸層）
      if(uInk>.001){float a=atan(d.y,d.x);float n=vn(vec2(a*5.,uTime*.15))*.6+vn(vUv*vec2(uAspect,1.)*9.)*.4;
        float rn=length(d)/length(vec2(uAspect*.5,.5));float e=smoothstep(.98-uInk*.5,1.1-uInk*.35,rn+(n-.5)*.22);col=mix(col,uInkC,clamp(e,0.,1.)*min(1.,uInk*1.6));}
      col+=(h(vUv*vec2(1931.,1213.)+fract(uTime)*91.)-.5)*uGrain;
      col=mix(col,uFlashC,uFlash);
      gl_FragColor=vec4(clamp(col,0.,1.),c.a);}`};

export function createPost(E,o={}){
  const {renderer,scene,camera}=E;
  const samples=E.dpr<2?4:0;
  const rt=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,samples});
  const composer=new EffectComposer(renderer,rt);
  composer.addPass(new RenderPass(scene,camera));
  let bloom=null;
  if(o.bloom){bloom=new UnrealBloomPass(new THREE.Vector2(256,256),o.bloom.strength??.6,o.bloom.radius??.5,o.bloom.threshold??.9);composer.addPass(bloom)}
  composer.addPass(new OutputPass());
  const grade=new ShaderPass(GradeShader);const U=grade.uniforms;
  const setGrade=(g={})=>{if(g.vig!=null)U.uVig.value=g.vig;if(g.grain!=null)U.uGrain.value=g.grain;if(g.sat!=null)U.uSat.value=g.sat;if(g.contrast!=null)U.uContrast.value=g.contrast;
    if(g.shadow!=null)U.uShadow.value.set(g.shadow);if(g.high!=null)U.uHigh.value.set(g.high);if(g.lift!=null)U.uLift.value.set(g.lift);if(g.keep!=null)U.uKeep.value=g.keep;
    if(g.ink!=null)U.uInk.value=g.ink;if(g.inkColor!=null)U.uInkC.value.set(g.inkColor)};
  const g=o.grade||{};U.uVig.value=g.vig??.35;U.uGrain.value=g.grain??.03;U.uSat.value=g.sat??1;U.uContrast.value=g.contrast??1;setGrade({shadow:g.shadow,high:g.high,lift:g.lift,keep:g.keep,ink:g.ink,inkColor:g.inkColor});
  composer.addPass(grade);
  const P={composer,bloom,grade,enabled:true,U,setGrade,
    // 泛光強度／半徑／門檻（screen2 依階段調整）
    setBloom(b={}){if(!bloom)return;if(b.strength!=null)bloom.strength=b.strength;if(b.radius!=null)bloom.radius=b.radius;if(b.threshold!=null)bloom.threshold=b.threshold},
    // 一次性的畫面效果（每幀由 screen2 設定）：閃光、色差、徑向模糊
    setFx(f={}){if(f.flash!=null)U.uFlash.value=f.flash;if(f.flashColor!=null)U.uFlashC.value.set(f.flashColor);if(f.chroma!=null)U.uChroma.value=f.chroma;
      if(f.blur!=null)U.uBlur.value=f.blur;if(f.blurAt)U.uBlurC.value.set(f.blurAt[0],f.blurAt[1])},
    setSize(w,h){composer.setPixelRatio(E.dpr);composer.setSize(w,h);U.uAspect.value=w/h;
      // 泛光只用四分之一解析度（UnrealBloomPass 內部會再減半）：手機上最吃填色的就是它
      if(bloom)bloom.setSize(Math.max(2,Math.round(w*E.dpr/2)),Math.max(2,Math.round(h*E.dpr/2)))},
    render(dt){U.uTime.value+=dt||0;composer.render(dt)},
    dispose(){composer.dispose();rt.dispose();bloom&&bloom.dispose();grade.material.dispose()}};
  return P;
}
