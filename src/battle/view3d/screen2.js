// 魂系 v2 畫面層（Screen）：電影感調色、Boss 主色輪廓光＋背光暈、各場地環境粒子、階段越高越壓迫，
// 以及給「感覺／動畫」用的螢幕效果 API（閃光、色差、徑向模糊、泛光脈衝、墨邊收縮、去色）。
// 只在魂系場景使用（soulScene.js 一行呼叫）；打怪模式、封面不經過這裡，維持原本的明亮風格。
// 規格：art/v2/design.md 第 5 節；API 文件：art/v2/reports/screen.md。
// 效能：環境粒子＝1 個 Points（1 次 draw call，位置全在 vertex shader 算，CPU 每幀只更新幾個 uniform）；
//      背光暈＝1 張 sprite；不新增任何燈（只改既有 rim／hemi 的顏色，不會重編 shader）。
//      低畫質（engine 降級）：後製整個關掉，閃光／暗角改用 DOM 疊層；粒子減到 35%；色差／模糊／顆粒不跑。
//      FPS < 42（還沒降級前）：先關顆粒、色差、模糊、墨邊。prefers-reduced-motion：不做色差、模糊、泛光脈衝，閃光減半。
import * as THREE from 'three';
import { ease, clamp } from './engine.js';

// Boss 主色（design.md §2）與輪廓光混色比例（§5.2：devourer 中，其他弱）
const ACCENT={sentinel:0x7dffb0,gargoyle:0xff8a3a,priest:0x8fe3ff,executioner:0xb07aff,devourer:0xff3a2a};
const RIM_K={sentinel:.5,gargoyle:.5,priest:.45,executioner:.55,devourer:.7};
// 基準調色（§5.1）
export const BASE={bloom:.7,radius:.55,threshold:.82,vig:.38,grain:.03,sat:.90,contrast:1.08,shadow:0xdfe8ff,high:0xffe9c8,keep:.75,exposure:1.45};
// 階段壓迫表（§5.3）：index＝phaseTint（0 一階、1 二階、2 三階）
export const MOOD=[
  {vig:.38,sat:.90,bloom:.70,ink:0,  amb:1,  ambTint:0,  parts:1,  rim:1,   halo:1},
  {vig:.46,sat:.86,bloom:.78,ink:.2, amb:.85,ambTint:.12,parts:1.3,rim:1.2, halo:1.1},
  {vig:.55,sat:.80,bloom:.85,ink:.55,amb:.70,ambTint:.25,parts:1.5,rim:1.4, halo:1.2}];
// 各場地環境粒子（§4 #24）：shape 0 圓點／1 方片（紙、灰燼片）；fall＝下落速度（負＝上升）；sway 左右飄；size 世界尺寸
const AMB={
  gate_ruins:     {color:0x8a7f72,alt:0xff8a3a,altK:.16,shape:1,fall:.22,sway:.35,size:.05, alpha:.6, spin:1.2}, // 灰燼片＋零星火星
  cathedral_roof: {color:0x8b8880,alt:0xd8c4a4,altK:.3, shape:0,fall:.05,sway:.18,size:.04, alpha:.42,spin:0},   // 碎石塵、懸浮微粒
  frozen_chapel:  {color:0xe6f6ff,alt:0xbfe8ff,altK:.5, shape:0,fall:.55,sway:.4, size:.045,alpha:.75,spin:0},   // 細雪
  execution_yard: {color:0x1c1626,alt:0x5a3e88,altK:.22,shape:0,fall:-.12,sway:.25,size:.1, alpha:.6, spin:0},   // 上升的墨霧顆粒
  throne_of_words:{color:0xb8a27a,alt:0xff6a3a,altK:.2, shape:1,fall:.1, sway:.5, size:.085,alpha:.62,spin:.6},  // 飄浮書頁碎片（邊緣燃紅）
};
// 各場地的基準霧色（§5.2）：轉階段後霧色可以偏主色，但亮度不得超過基準 ×1.1（壓迫感＝更暗，不是更亮）
const FOG0={gate_ruins:0x18211f,cathedral_roof:0x151b28,frozen_chapel:0x1b2a37,execution_yard:0x1d1727,throne_of_words:0x24130f};
const lum=c=>.2126*c.r+.7152*c.g+.0722*c.b;
const N_MAX=420,N_BASE=260,BOX={x:10,y:7.5,z0:-10,z1:8};

function haloTexture(){const S=128,c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d"),g=x.createRadialGradient(S/2,S/2,0,S/2,S/2,S/2);
  g.addColorStop(0,"rgba(255,255,255,1)");g.addColorStop(.35,"rgba(255,255,255,.45)");g.addColorStop(.7,"rgba(255,255,255,.1)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,S,S);
  return new THREE.CanvasTexture(c)}

function ambientPoints(){
  const geo=new THREE.BufferGeometry(),pos=new Float32Array(N_MAX*3),seed=new Float32Array(N_MAX*4);
  for(let i=0;i<N_MAX;i++){pos[i*3]=(Math.random()*2-1)*BOX.x;pos[i*3+1]=Math.random()*BOX.y;pos[i*3+2]=BOX.z0+Math.random()*(BOX.z1-BOX.z0);
    seed[i*4]=Math.random();seed[i*4+1]=.6+Math.random()*.8;seed[i*4+2]=Math.random()*6.283;seed[i*4+3]=i/N_MAX}
  geo.setAttribute("position",new THREE.BufferAttribute(pos,3));geo.setAttribute("aSeed",new THREE.BufferAttribute(seed,4));
  geo.boundingSphere=new THREE.Sphere(new THREE.Vector3(0,4,0),30);
  const mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,fog:false,
    uniforms:{uTime:{value:0},uFall:{value:.2},uSway:{value:.3},uSize:{value:.05},uScale:{value:400},uAlpha:{value:0},uShape:{value:0},uSpin:{value:0},
      uColor:{value:new THREE.Color()},uAlt:{value:new THREE.Color()},uAltK:{value:.2},uAccent:{value:new THREE.Color()},uBaseFrac:{value:1},uAccK:{value:0},
      uFogC:{value:new THREE.Color()},uFogD:{value:.05},uH:{value:BOX.y}},
    vertexShader:`attribute vec4 aSeed;uniform float uTime,uFall,uSway,uSize,uScale,uH,uSpin;varying float vA,vRank,vRot,vDist,vAlt;
      void main(){vec3 p=position;float sp=aSeed.y,ph=aSeed.z;
        p.y=mod(p.y-uTime*uFall*sp+uH*40.,uH);
        p.x+=sin(uTime*.37*sp+ph)*uSway+sin(uTime*.9+ph*2.)*uSway*.3;p.z+=cos(uTime*.29*sp+ph)*uSway;
        vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;vDist=-mv.z;
        float e=smoothstep(0.,.6,p.y)*(1.-smoothstep(uH-1.2,uH,p.y));vA=e*(.55+.45*sin(uTime*1.3*sp+ph*3.));
        vRank=aSeed.w;vRot=uTime*uSpin*(sp-.9)*2.+ph;vAlt=aSeed.x;
        gl_PointSize=clamp(uSize*uScale*(.6+.8*aSeed.x)/max(.5,-mv.z),1.,48.);}`,
    fragmentShader:`uniform float uAlpha,uShape,uAltK,uBaseFrac,uAccK,uFogD;uniform vec3 uColor,uAlt,uAccent,uFogC;varying float vA,vRank,vRot,vDist,vAlt;
      void main(){vec2 q=gl_PointCoord-.5;float a;
        if(uShape>.5){float cs=cos(vRot),sn=sin(vRot);vec2 r=vec2(cs*q.x-sn*q.y,sn*q.x+cs*q.y);vec2 b=abs(r)-vec2(.36,.22);a=1.-smoothstep(-.06,.04,max(b.x,b.y));}
        else{a=1.-smoothstep(.12,.5,length(q));}
        vec3 col=vAlt<uAltK?uAlt:uColor;
        if(vRank>uBaseFrac){col=uAccent*1.6;a*=uAccK;}
        float f=1.-exp(-vDist*vDist*uFogD*uFogD*.55);col=mix(col,uFogC,f*.8);
        a*=vA*uAlpha*(1.-f*.6);if(a<.01)discard;gl_FragColor=vec4(col,a);}`});
  const pts=new THREE.Points(geo,mat);pts.frustumCulled=false;pts.renderOrder=6;return pts}

// 具名匯出（秒為單位）：轉給目前作用中的魂系場景；沒有魂系場景（打怪模式）時什麼都不做
let active=null;
const act=()=>active&&!active.dead&&active.screen2?active.screen2:null;
export function flash(o){const s=act();s&&s.flash(o)}
export function pulseChromatic(k,dur){const s=act();s&&s.pulseChromatic(k,dur)}
export function pulseRadial(k,dur,at){const s=act();s&&s.pulseRadial(k,dur,at)}
export function pulseBloom(peak,dur){const s=act();s&&s.pulseBloom(peak,dur)}
export function setPhaseMood(n,dur){const s=act();s&&s.setPhaseMood(n,dur)}

export function createScreen2(eng,ctx={}){
  const {scene,camera,renderer}=eng,{hemi,rim}=ctx,getBoss=ctx.boss||(()=>null),getPhase=ctx.phase||(()=>0);
  const rm=!!eng.rm;
  // 套用基準調色（soulScene 原本的 usePost 參數在這裡覆蓋成 v2 基準）
  const lift=new THREE.Color(0x0a1424).multiplyScalar(.35); // 暗部抬一點冷青（冷墨底）
  if(eng.post){eng.post.setGrade({vig:BASE.vig,grain:BASE.grain,sat:BASE.sat,contrast:BASE.contrast,shadow:BASE.shadow,high:BASE.high,lift,keep:BASE.keep});eng.post.setBloom({strength:BASE.bloom,radius:BASE.radius,threshold:BASE.threshold})}
  if(renderer)renderer.toneMappingExposure=BASE.exposure;

  /* ---------- 低畫質時的 DOM 疊層（後製關掉後的閃光、暗角） ---------- */
  const mk=css=>{const el=document.createElement("div");el.style.cssText="position:absolute;inset:0;pointer-events:none;opacity:0;"+css;eng.overlay.prepend(el);return el};
  const domVig=mk("background:radial-gradient(ellipse at center,transparent 50%,rgb(4 4 8/.85) 100%)"),domFlash=mk("background:#fff;will-change:opacity");

  /* ---------- Boss 背光暈（剪影從霧中跳出）：一張加色 sprite 放在 Boss 身後 ---------- */
  const haloMat=new THREE.SpriteMaterial({map:haloTexture(),color:0xffffff,transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending,fog:false});
  const halo=new THREE.Sprite(haloMat);halo.renderOrder=-1;halo.visible=false;scene.add(halo);

  /* ---------- 環境粒子 ---------- */
  const amb=ambientPoints();scene.add(amb);const AU=amb.material.uniforms;
  let ambKey="",ambFade=0,ambA=.5;
  const setAmbStyle=k=>{const s=AMB[k]||AMB.gate_ruins;AU.uColor.value.set(s.color);AU.uAlt.value.set(s.alt);AU.uAltK.value=s.altK;AU.uShape.value=s.shape;AU.uFall.value=s.fall*(rm?.5:1);AU.uSway.value=s.sway*(rm?.5:1);AU.uSize.value=s.size;AU.uSpin.value=s.spin*(rm?.3:1);ambA=s.alpha};
  setAmbStyle("gate_ruins");

  /* ---------- 狀態 ---------- */
  const rimC0=rim?rim.color.clone():new THREE.Color(0x9fb8e8),hemiC0=hemi?hemi.color.clone():null,hemiG0=hemi?hemi.groundColor.clone():null;
  const accent=new THREE.Color(0xffffff),tmpC=new THREE.Color(),tmpV=new THREE.Vector3(),dirV=new THREE.Vector3();
  const M={...MOOD[0]}; // 目前（平滑後）的值
  let manualMood=null,lastBoss=null,bossK="",haloK=0;
  // 脈衝（加在基準上，用真實時間衰減）
  const pulses=[]; // {kind, k, t, dur, color?, at?, in?, hold?}
  let lastFlash=-1e9,flashN=[];
  const now=()=>performance.now();
  function addPulse(kind,k,ms,o={}){if(eng.dead||!(k>0))return;const p={kind,k,t:0,dur:Math.max(.016,ms/1000),...o};
    // 同種的脈衝只留一個：目前那個剩下的比新的強就不換（避免疊到過亮）
    for(let i=pulses.length-1;i>=0;i--)if(pulses[i].kind===kind){const q=pulses[i],rem=q.k*(1-q.t/q.dur);if(rem>k)return;pulses.splice(i,1)}
    pulses.push(p)}
  const pulseVal=kind=>{for(const p of pulses)if(p.kind===kind){const r=p.t/p.dur;let e;
      if(p.hold!=null){const a=Math.max(.001,p.in||0),h=p.hold;e=p.t<a?ease.out(p.t/a):p.t<a+h?1:1-ease.io((p.t-a-h)/Math.max(.001,p.dur-a-h))}
      else e=r<.12?r/.12:1-ease.out((r-.12)/.88);return[p.k*clamp(e,0,1),p]}return[0,null]};

  const lite=()=>eng.quality==="low"||(eng.fps>0&&eng.fps<42);

  /* ---------- 公開 API（掛在 eng.screen，feel.js／phaseShow.js 可呼叫） ---------- */
  const api={
    // 全畫面閃光：color 數字或字串；strength 0..1（上限：紅 ≤0.3，其他 ≤0.08，比 §5.4 嚴）；ms 長度。每秒最多 3 次（多的併入目前這次）。
    flash(color=0xffffff,strength=.12,ms=120){if(color&&typeof color==="object"&&!color.isColor)return eng.screen2.flash(color); // 物件參數（秒）也接受
      const c=new THREE.Color(color),t=now();
      const red=c.r>.5&&c.g<.35&&c.b<.35,cap=red?.3:.08; // 可讀性修正（vfx）：白／金／其他色的全畫面閃光原本 .15／.22，連斬時疊上刀光與 bloom 會整片泛白；紅閃（受擊）不變
      const k=Math.min(strength,cap)*(rm?.5:1);
      flashN=flashN.filter(x=>t-x<1000);if(flashN.length>=3||t-lastFlash<120){const [v,p]=pulseVal("flash");if(p&&k>v){p.k=k;p.t=0}return}
      flashN.push(t);lastFlash=t;addPulse("flash",k,ms,{color:c})},
    // 徑向色差：k 0..1.5（1≈畫面邊緣偏移 1.2%），ms 長度
    pulseChromatic(k=.6,ms=160){if(rm)return;addPulse("chroma",clamp(k,0,1.5),ms)},
    // 徑向模糊：k 0..1；at＝世界座標 Vector3 或畫面 [u,v]（0..1，左下原點），省略＝畫面中央
    pulseRadial(k=.5,ms=180,at=null){if(rm)return;let uv=[.5,.5];
      if(at&&at.isVector3){tmpV.copy(at).project(camera);uv=[clamp(tmpV.x*.5+.5,0,1),clamp(tmpV.y*.5+.5,0,1)]}else if(Array.isArray(at))uv=at;
      addPulse("blur",clamp(k,0,1),ms,{at:uv})},
    // 泛光脈衝：peak＝泛光強度峰值（§5.1：完美斬／終結斬 1.1），ms 長度（0.15 s 回落）
    pulseBloom(peak=1.1,ms=150){if(rm)return;addPulse("bloom",Math.max(0,peak-M.bloom),ms)},
    // 墨邊收縮（§3 爆發前 T−0.15 秒）：k 0..1 目標墨邊；inMs 收進來、holdMs 停住、outMs 退回
    inkSqueeze(k=.6,inMs=150,holdMs=150,outMs=450){addPulse("ink",clamp(k,0,1),inMs+holdMs+outMs,{in:inMs/1000,hold:holdMs/1000})},
    // 暫時去色（devourer 三階爆發：sat 0.3，0.4 s 後恢復）：sat＝目標飽和度
    desaturate(sat=.3,holdMs=400,outMs=500){addPulse("desat",clamp(1-sat,0,1),60+holdMs+outMs,{in:.06,hold:holdMs/1000})},
    // 階段氛圍：n＝0 一階、1 二階、2 三階；dur 秒內漸變。預設自動跟著 soulScene 的 phaseTint；呼叫後以呼叫值為準，直到換 Boss 或呼叫 setPhaseMood(null)
    setPhaseMood(n,dur=1.2){manualMood=n==null?null:{n:clamp(n|0,0,2),rate:4.6/Math.max(.1,dur)}},
    // 打擊組合包：level 對應 design §6 的 S1–S7（給 feel.js 一行呼叫）；at＝命中點（Vector3，徑向模糊的中心）
    // 可讀性修正（vfx）：白閃 .14／.1 → .08／.06、泛光峰值 1.1 → .95、徑向模糊 .55 → .22（會把金色刀光拖成整片放射光）；原值疊上金色刀光後整個畫面泛白
    impact(level=1,at=null){if(level>=3)api.pulseChromatic(level>=5?.9:level>=4?.6:.35,level>=5?260:150);
      if(level>=4)api.flash(0xfff2c0,level>=5?.08:.06,110);if(level===3||level>=5)api.pulseBloom(.95,150);if(level>=5)api.pulseRadial(.22,320,at)},
    // 玩家受擊：紅閃＋色差（heavy＝必殺命中）
    hurt(heavy=false){api.flash(0xc0242a,heavy?.3:.16,heavy?260:180);api.pulseChromatic(heavy?.7:.3,heavy?220:140)},
    // 除錯：目前的數值
    state(){const r={};for(const k in M)r[k]=+M[k].toFixed(3);return{mood:r,phase:manualMood?manualMood.n:getPhase(),boss:bossK,lite:lite(),quality:eng.quality,pulses:pulses.map(p=>p.kind),amb:{key:ambKey,n:amb.geometry.drawRange.count,a:+AU.uAlpha.value.toFixed(2)}}},
  };
  eng.screen=api;
  // 相容包裝（秒為單位、物件參數）：feel.js 走 eng.screen2 或本模組的具名匯出
  eng.screen2={flash:(o={})=>api.flash(o.color??0xffffff,o.opacity??o.strength??.12,(o.dur??.12)*1000),pulseChromatic:(k=.6,dur=.16)=>api.pulseChromatic(k,dur*1000),
    pulseRadial:(k=.5,dur=.18,at=null)=>api.pulseRadial(k,dur*1000,at),pulseBloom:(peak=1.1,dur=.15)=>api.pulseBloom(peak,dur*1000),setPhaseMood:(n,dur=1.2)=>api.setPhaseMood(n,dur),api};
  active=eng;

  /* ---------- 每幀（order 90：在鏡頭 100 之前，rim 燈位置由 soulScene 鏡頭那段更新） ---------- */
  eng.onUpdate((dt,rdt)=>{try{
    const b=getBoss();
    // 換 Boss：主色
    if(b!==lastBoss){lastBoss=b;manualMood=null;if(b){const id=b.data&&b.data.id;bossK=id||"";accent.set(ACCENT[id]??b.eye??0xff3020)}}
    // 場地粒子：換場地時先淡出再換樣式
    const want=b&&b.data&&b.data.arena||ambKey||"gate_ruins";
    if(want!==ambKey){ambFade=Math.max(0,ambFade-rdt*1.4);if(ambFade<=0||!ambKey){ambKey=want;setAmbStyle(want)}}else ambFade=Math.min(1,ambFade+rdt*.8);
    // 階段：目標值往前平滑（約 1.2 s 完成）
    const n=manualMood?manualMood.n:clamp(getPhase()|0,0,2),T=MOOD[n],k=1-Math.exp(-rdt*(manualMood?manualMood.rate:4.6));
    for(const key in M)M[key]+=(T[key]-M[key])*k;
    // 脈衝
    for(let i=pulses.length-1;i>=0;i--){pulses[i].t+=rdt;if(pulses[i].t>=pulses[i].dur)pulses.splice(i,1)}
    const [fl,fp]=pulseVal("flash"),[ch]=pulseVal("chroma"),[bl,bp]=pulseVal("blur"),[bm]=pulseVal("bloom"),[ik]=pulseVal("ink"),[ds]=pulseVal("desat");
    const L=lite(),post=eng.post&&eng.quality!=="low"?eng.post:null;
    if(post){post.setGrade({vig:M.vig+ik*.25,sat:M.sat*(1-ds),ink:L?0:Math.max(M.ink,ik),grain:L?0:BASE.grain});post.setBloom({strength:M.bloom+bm});
      post.setFx({flash:fl,flashColor:fp?fp.color:undefined,chroma:L?0:ch,blur:L?0:bl,blurAt:bp?bp.at:null});domFlash.style.opacity=0;domVig.style.opacity=0}
    else{ // 後製關掉：DOM 閃光＋暗角
      domFlash.style.opacity=fl.toFixed(3);if(fp)domFlash.style.background="#"+fp.color.getHexString();
      domVig.style.opacity=clamp((M.vig-.3)*1.6+ik*.6,0,1).toFixed(3)}
    // 輪廓光：既有的 Boss 背後 rim 燈換成「冷色＋主色」；環境光依階段變暗、偏主色（只改顏色，不和別人的強度補間打架）
    if(rim){const rk=b?(RIM_K[bossK]??.5)*M.rim:0;rim.color.copy(rimC0).lerp(accent,clamp(rk,0,.9))}
    if(hemi&&hemiC0){hemi.color.copy(hemiC0).lerp(tmpC.copy(accent).multiplyScalar(.6),M.ambTint).multiplyScalar(M.amb);hemi.groundColor.copy(hemiG0).multiplyScalar(.6+.4*M.amb)}
    // 背光暈：Boss 身後、胸口高度（從鏡頭看過去在 Boss 背後一點）；Boss 倒下化灰時跟著淡掉
    const op=b?(b.opacity==null?1:b.opacity):0;
    haloK+=((b&&b.root.visible?op:0)-haloK)*(1-Math.exp(-rdt*3));
    if(b&&haloK>.01){const bp_=b.root.position;dirV.subVectors(bp_,camera.position).setY(0);const len=dirV.length()||1;dirV.multiplyScalar(1/len);
      halo.position.copy(bp_).addScaledVector(dirV,1.4);halo.position.y=(b.h||3)*.58;const s=(b.h||3)*2.1*(.94+.06*M.halo);halo.scale.set(s*1.05,s,1);
      haloMat.color.copy(accent).multiplyScalar(.55);haloMat.opacity=(bossK==="devourer"?.13:.1)*M.halo*haloK*(eng.quality==="low"?.7:1);halo.visible=true}
    else halo.visible=false;
    // 環境粒子：數量依畫質與階段；多出來的那段是主色餘燼
    const base=Math.round(N_BASE*(eng.quality==="low"?.35:1)*(rm?.6:1)),cnt=Math.min(N_MAX,Math.round(base*M.parts));
    amb.geometry.setDrawRange(0,cnt);AU.uBaseFrac.value=base/N_MAX+.0001;AU.uAccK.value=clamp((M.parts-1)*2.2,0,1);AU.uAccent.value.copy(accent);
    AU.uTime.value+=dt;AU.uAlpha.value=ambA*ambFade;AU.uScale.value=eng.height*eng.dpr/(2*Math.tan(camera.fov*Math.PI/360));
    // 霧色亮度上限（只在超過時等比例壓暗，色相保留）
    if(scene.fog&&b&&FOG0[want]!=null){const cap=lum(tmpC.set(FOG0[want]))*1.1,fc=scene.fog.color,l=lum(fc);if(l>cap&&l>0){fc.multiplyScalar(cap/l);if(scene.background&&scene.background.isColor)scene.background.copy(fc)}}
    if(scene.fog){AU.uFogC.value.copy(scene.fog.color);AU.uFogD.value=scene.fog.density}
  }catch(e){if(!api._warned){api._warned=1;console.warn("[screen2]",e)}}},90);

  eng.track({dispose(){if(active===eng)active=null;haloMat.map&&haloMat.map.dispose();haloMat.dispose();amb.geometry.dispose();amb.material.dispose();domVig.remove();domFlash.remove()}});
  return api;
}
