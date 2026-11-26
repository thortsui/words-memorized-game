// 後製：HDR 繪製 → 泛光（火焰、眼睛、餘燼、魔法會發光暈）→ 色調映射 → 調色（對比、飽和、冷暖分離、暗角、底片顆粒）。
// 只在高畫質時開；掉幀降級成低畫質就整個關掉，回到直接畫到螢幕。
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';

const GradeShader={
  uniforms:{tDiffuse:{value:null},uTime:{value:0},uVig:{value:.35},uGrain:{value:.03},uSat:{value:1},uContrast:{value:1},
    uShadow:{value:new THREE.Color(1,1,1)},uHigh:{value:new THREE.Color(1,1,1)},uAspect:{value:1}},
  vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader:`uniform sampler2D tDiffuse;uniform float uTime,uVig,uGrain,uSat,uContrast,uAspect;uniform vec3 uShadow,uHigh;varying vec2 vUv;
    float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
    void main(){vec4 c=texture2D(tDiffuse,vUv);vec3 col=c.rgb;
      float l=dot(col,vec3(.2126,.7152,.0722));
      col=mix(vec3(l),col,uSat);
      col=(col-.5)*uContrast+.5;
      // 冷暖分離：暗部、亮部各染一點顏色
      col*=mix(uShadow,uHigh,smoothstep(.05,.75,l));
      vec2 d=(vUv-.5)*vec2(uAspect,1.);float v=1.-uVig*smoothstep(.35,1.05,length(d)*1.25);col*=v;
      col+=(h(vUv*vec2(1931.,1213.)+fract(uTime)*91.)-.5)*uGrain;
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
  const grade=new ShaderPass(GradeShader);const g=o.grade||{},U=grade.uniforms;
  U.uVig.value=g.vig??.35;U.uGrain.value=g.grain??.03;U.uSat.value=g.sat??1;U.uContrast.value=g.contrast??1;
  if(g.shadow)U.uShadow.value.set(g.shadow);if(g.high)U.uHigh.value.set(g.high);
  composer.addPass(grade);
  const P={composer,bloom,grade,enabled:true,
    setSize(w,h){composer.setPixelRatio(E.dpr);composer.setSize(w,h);U.uAspect.value=w/h;
      // 泛光只用四分之一解析度（UnrealBloomPass 內部會再減半）：手機上最吃填色的就是它
      if(bloom)bloom.setSize(Math.max(2,Math.round(w*E.dpr/2)),Math.max(2,Math.round(h*E.dpr/2)))},
    render(dt){U.uTime.value+=dt||0;composer.render(dt)},
    dispose(){composer.dispose();rt.dispose();bloom&&bloom.dispose();grade.material.dispose()}};
  return P;
}
