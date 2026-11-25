// 角色：載入 GLB（public/models/<代號>.glb），載不到就用程式產生的替身；
// GLB 缺某個動作名稱時，改用同一套「程式補間動作」（PROC）。之後把模型檔補上，不必改程式就會換成真模型。
//
// 節點結構：root（世界位置與面向）→ pose（補間動作：衝刺、擠壓、倒下…）→ bob（待機呼吸／飛行漂浮）→ 內容（GLB 或替身）
// 模型約定：臉朝 +Z、原點在腳底。載入後會依 height 等比縮放。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import MODEL_FILES from 'virtual:model-list';
import { ease, lerp } from './engine.js';

/* ---------- 模型載入（同一場戰鬥內快取；清單由 vite.config.js 讀 public/models 產生，避免對不存在的檔案發請求） ---------- */
export function createLoader(){
  const loader=new GLTFLoader(),cache=new Map();
  return name=>{if(!name)return Promise.resolve(null);if(cache.has(name))return cache.get(name);
    const p=!MODEL_FILES.includes(name+".glb")?Promise.resolve(null)
      :new Promise(res=>loader.load(import.meta.env.BASE_URL+"models/"+name+".glb",g=>res(g),undefined,()=>res(null)));
    cache.set(name,p);return p};
}

/* ---------- 卡通材質與描邊（打怪模式用） ---------- */
export function toonGradient(){const d=new Uint8Array([110,110,110,255,185,185,185,255,255,255,255,255]);const t=new THREE.DataTexture(d,3,1,THREE.RGBAFormat);t.minFilter=t.magFilter=THREE.NearestFilter;t.needsUpdate=true;return t}
function toonify(obj,grad){obj.traverse(o=>{if(!o.isMesh)return;const conv=m=>{if(m.isMeshToonMaterial||m.isMeshBasicMaterial)return m;
    const t=new THREE.MeshToonMaterial({color:m.color?m.color.clone():0xffffff,map:m.map||null,gradientMap:grad,transparent:m.transparent,opacity:m.opacity,side:m.side,alphaTest:m.alphaTest||0,name:m.name});
    if(m.emissive){t.emissive.copy(m.emissive);t.emissiveIntensity=m.emissiveIntensity==null?1:m.emissiveIntensity;t.emissiveMap=m.emissiveMap||null}
    if(m.vertexColors)t.vertexColors=true;m.dispose();return t};
  o.material=Array.isArray(o.material)?o.material.map(conv):conv(o.material)})}
const outlineMat=th=>{const m=new THREE.MeshBasicMaterial({color:0x232038,side:THREE.BackSide});
  m.onBeforeCompile=s=>{s.vertexShader=s.vertexShader.replace("#include <begin_vertex>",`#include <begin_vertex>\ntransformed+=normalize(normal)*${th.toFixed(5)};`)};
  m.customProgramCacheKey=()=>"outline"+th.toFixed(5);m.userData.outline=true;return m};
// 反向外殼描邊：只描夠大的不透明部位（身體），小零件不描
function addOutline(obj,worldH,scale){const list=[];obj.traverse(o=>{if(!o.isMesh||o.userData.noOutline)return;const m=Array.isArray(o.material)?o.material[0]:o.material;if(!m||m.transparent||m.userData.outline)return;
    if(!o.geometry.boundingSphere)o.geometry.computeBoundingSphere();if(o.geometry.boundingSphere.radius*scale<worldH*.2)return;list.push(o)});
  for(const o of list){const mat=outlineMat(worldH*.022/scale);let c;
    if(o.isSkinnedMesh){c=new THREE.SkinnedMesh(o.geometry,mat);c.bind(o.skeleton,o.bindMatrix)}else c=new THREE.Mesh(o.geometry,mat);
    c.position.copy(o.position);c.quaternion.copy(o.quaternion);c.scale.copy(o.scale);c.userData.isOutline=true;c.frustumCulled=o.frustumCulled;o.parent.add(c)}}

/* ---------- 程式補間動作 ----------
   每個動作：{dur 總長, impact 命中時間點, hold 播完停在最後姿勢, run(a, T) }；T(obj, props, 秒, easing) 是補間。
   只動 pose（整體）與替身的零件（a.parts，可能不存在），所以真模型缺動作時也能套用。 */
const PI=Math.PI;
const arm=(a,T,x,d,ez)=>a.parts.armR?T(a.parts.armR.rotation,{x},d,ez):null;
const armL=(a,T,x,d,ez)=>a.parts.armL?T(a.parts.armL.rotation,{x},d,ez):null;
const PROC={
  Enter:{dur:.8,run:async(a,T)=>{const P=a.pose;
    if(a.cute){P.scale.set(.01,.01,.01);P.position.y=a.h*1.6;T(P.position,{y:0},.38,ease.in);await T(P.scale,{x:1,y:1,z:1},.38,ease.out);
      await T(P.scale,{x:1.3,y:.65,z:1.3},.09,ease.out);await T(P.scale,{x:1,y:1,z:1},.33,ease.elastic)}
    else{P.scale.set(.96,.9,.96);P.rotation.x=.25;T(P.rotation,{x:0},.8,ease.out);await T(P.scale,{x:1,y:1,z:1},.8,ease.out)}}},
  Attack:{dur:.78,impact:.4,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.scale,{x:1.12,y:.86,z:1.12},.26,ease.out);T(P.rotation,{x:-.22},.26,ease.out);arm(a,T,-2.5,.26,ease.out);await T(P.position,{z:-.22*h},.26,ease.out);
    T(P.scale,{x:.9,y:1.14,z:.9},.14,ease.out);T(P.rotation,{x:.38},.14,ease.in);arm(a,T,.7,.14,ease.in);await T(P.position,{z:.55*h},.14,ease.in);
    T(P.scale,{x:1,y:1,z:1},.38,ease.elastic);T(P.rotation,{x:0},.3,ease.out);arm(a,T,a.rest.armR,.3,ease.io);await T(P.position,{z:0},.38,ease.out)}},
  Attack2:{dur:.95,impact:.52,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{y:-1.1},.34,ease.out);arm(a,T,-1.6,.34,ease.out);await T(P.position,{y:.12*h,z:-.15*h},.34,ease.out);
    T(P.rotation,{y:PI*2+.5},.24,ease.in);arm(a,T,.4,.2,ease.in);await T(P.position,{y:0,z:.4*h},.24,ease.in);
    P.rotation.y-=PI*2;T(P.rotation,{y:0},.36,ease.out);arm(a,T,a.rest.armR,.3,ease.io);await T(P.position,{z:0},.36,ease.out)}},
  Slash:{dur:.48,impact:.22,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{y:-.55,x:-.08},.14,ease.out);arm(a,T,-2.4,.14,ease.out);await T(P.position,{z:-.06*h},.14,ease.out);
    T(P.rotation,{y:.65,x:.2},.1,ease.in);arm(a,T,.9,.1,ease.in);await T(P.position,{z:.16*h},.1,ease.in);
    T(P.rotation,{y:0,x:0},.24,ease.out);arm(a,T,a.rest.armR,.24,ease.io);await T(P.position,{z:0},.24,ease.out)}},
  HeavySlash:{dur:.82,impact:.46,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:-.34},.32,ease.out);arm(a,T,-3,.32,ease.out);await T(P.position,{y:.1*h,z:-.1*h},.32,ease.out);
    T(P.rotation,{x:.5},.14,ease.in);arm(a,T,1.1,.14,ease.in);await T(P.position,{y:0,z:.28*h},.14,ease.in);
    T(P.rotation,{x:0},.36,ease.out);arm(a,T,a.rest.armR,.36,ease.io);await T(P.position,{z:0},.36,ease.out)}},
  Combo:{dur:.9,impact:.2,run:async(a,T)=>{const P=a.pose;
    for(let i=0;i<3;i++){const s=i%2?-1:1;T(P.rotation,{y:-.6*s},.1,ease.out);arm(a,T,-2.2,.1,ease.out);await a.eng.wait(.1);T(P.rotation,{y:.7*s},.1,ease.in);arm(a,T,.9,.1,ease.in);await a.eng.wait(.16)}
    arm(a,T,a.rest.armR,.12,ease.io);await T(P.rotation,{y:0},.12,ease.out)}},
  Cast:{dur:.75,impact:.5,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:-.16},.3,ease.out);arm(a,T,-2.9,.3,ease.out);armL(a,T,-1.2,.3,ease.out);await T(P.position,{y:.12*h},.3,ease.out);await a.eng.wait(.2);
    T(P.rotation,{x:0},.25,ease.io);arm(a,T,a.rest.armR,.25,ease.io);armL(a,T,a.rest.armL,.25,ease.io);await T(P.position,{y:0},.25,ease.in)}},
  Hit:{dur:.38,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.scale,{x:1.14,y:.84,z:1.14},.07,ease.out);T(P.rotation,{x:-.32},.07,ease.out);await T(P.position,{z:-.24*h},.07,ease.out);
    T(P.scale,{x:1,y:1,z:1},.3,ease.elastic);T(P.rotation,{x:0},.3,ease.out);await T(P.position,{z:0},.3,ease.out)}},
  Stagger:{dur:.9,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:-.4,z:.14},.12,ease.out);await T(P.position,{z:-.4*h},.12,ease.out);
    T(P.rotation,{x:.3,z:-.06},.22,ease.io);await T(P.position,{y:-.1*h},.22,ease.io);await a.eng.wait(.22);
    T(P.rotation,{x:0,z:0},.34,ease.io);await T(P.position,{y:0,z:0},.34,ease.io)}},
  Faint:{dur:1,hold:true,run:async(a,T)=>{const P=a.pose,h=a.h;
    if(a.cute){T(P.rotation,{y:PI*2},.5,ease.out);await T(P.position,{y:.35*h},.22,ease.out);await T(P.position,{y:0},.24,ease.in);
      T(P.scale,{x:1.35,y:.32,z:1.35},.16,ease.out);await a.eng.wait(.16);await T(P.scale,{x:1.2,y:.45,z:1.2},.3,ease.elastic)}
    else{T(P.rotation,{x:.2},.3,ease.out);await T(P.position,{y:-.12*h},.3,ease.out);T(P.rotation,{x:-1.45},.5,ease.in);await T(P.position,{y:.1*h,z:-.3*h},.5,ease.in);await a.eng.wait(.2)}}},
  Victory:{dur:1.1,run:async(a,T)=>{const P=a.pose,h=a.h;arm(a,T,-2.9,.2,ease.out);
    for(let i=0;i<2;i++){if(a.cute&&i===0)T(P.rotation,{y:PI*2},.5,ease.io);await T(P.position,{y:.3*h},.2,ease.out);await T(P.position,{y:0},.2,ease.in);T(P.scale,{x:1.1,y:.9,z:1.1},.05);await a.eng.wait(.05);await T(P.scale,{x:1,y:1,z:1},.08)}
    P.rotation.y=0;await a.eng.wait(.1)}},
  Roll:{dur:.55,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.scale,{y:.62},.1,ease.out);T(P.position,{y:.12*h},.1,ease.out);await T(P.rotation,{x:PI*2},.45,ease.io);P.rotation.x=0;T(P.position,{y:0},.1,ease.in);await T(P.scale,{y:1},.1,ease.out)}},
  Parry:{dur:.4,impact:.12,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{y:.7,x:-.1},.1,ease.out);arm(a,T,-1.9,.1,ease.out);armL(a,T,-1.5,.1,ease.out);await T(P.position,{z:.12*h},.1,ease.out);await a.eng.wait(.1);
    T(P.rotation,{y:0,x:0},.2,ease.io);arm(a,T,a.rest.armR,.2,ease.io);armL(a,T,a.rest.armL,.2,ease.io);await T(P.position,{z:0},.2,ease.io)}},
  Guard:{dur:.6,impact:.14,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:.18},.12,ease.out);armL(a,T,-1.5,.12,ease.out);arm(a,T,-1.1,.12,ease.out);await T(P.position,{y:-.07*h},.12,ease.out);await a.eng.wait(.26);
    T(P.rotation,{x:0},.2,ease.io);armL(a,T,a.rest.armL,.2,ease.io);arm(a,T,a.rest.armR,.2,ease.io);await T(P.position,{y:0},.2,ease.io)}},
  Telegraph:{dur:.8,hold:true,run:async(a,T)=>{const P=a.pose,h=a.h;a.tremble=.012*h;
    T(P.rotation,{x:-.26},.6,ease.out);T(P.scale,{x:1.06,y:1.08,z:1.06},.6,ease.out);arm(a,T,-2.7,.6,ease.out);await T(P.position,{y:.05*h,z:-.12*h},.6,ease.out);await a.eng.wait(.2)}},
  PhaseShift:{dur:1.3,run:async(a,T)=>{const P=a.pose,h=a.h;a.tremble=.02*h;
    T(P.rotation,{x:.35},.5,ease.out);await T(P.scale,{x:.92,y:.86,z:.92},.5,ease.out);a.tremble=0;
    T(P.rotation,{x:-.3},.14,ease.out);arm(a,T,-2.8,.14,ease.out);armL(a,T,-2.8,.14,ease.out);await T(P.scale,{x:1.18,y:1.2,z:1.18},.14,ease.out);await a.eng.wait(.3);
    T(P.rotation,{x:0},.36,ease.io);arm(a,T,a.rest.armR,.36,ease.io);armL(a,T,a.rest.armL,.36,ease.io);await T(P.scale,{x:1,y:1,z:1},.36,ease.io)}},
};
PROC.Die=PROC.Faint;
const LOOPS={Idle:"idle",Walk:"walk",Run:"run"};

export class Actor{
  // o: {model 代號, height 目標身高（公尺）, standin: ()=>({group, parts, height}), cute, fly 飛行高度, shadow 陰影半徑, toon 漸層貼圖, outline, castShadow}
  constructor(eng,fx,o){this.eng=eng;this.fx=fx;this.o=o;this.h=o.height;this.cute=!!o.cute;this.name=o.model;
    this.root=new THREE.Group();this.pose=new THREE.Group();this.bob=new THREE.Group();this.root.add(this.pose);this.pose.add(this.bob);
    this.parts={};this.rest={armR:0,armL:0};this.actions={};this.mixer=null;this.curAct=null;this.seq=0;this.bobMode="idle";this.bobT=Math.random()*9;this.tremble=0;
    this.mats=[];this.flashK=0;this.flashC=new THREE.Color(0xffffff);this.glowK=0;this.glowC=new THREE.Color(0xff2a1a);this._tint=false;this.opacity=1;
    this.shadow=fx.blob(o.shadow||o.height*.42,o.cute?.55:.75);eng.scene.add(this.shadow);eng.scene.add(this.root);
    this._setContent(o.standin(),true);
    this._off=eng.onUpdate((dt,rdt,time)=>this._update(dt,time));
    this.ready=o.load?o.load(o.model).then(g=>{if(g&&!eng.dead&&!this.gone)this._setGLB(g);return this}):Promise.resolve(this)}

  _setContent(c,isStandin){if(this.content){this.bob.remove(this.content);this.eng.disposeObject(this.content)}
    this.content=c.group;this.parts=isStandin?(c.parts||{}):{};this.isStandin=isStandin;
    this.rest={armR:this.parts.armR?this.parts.armR.rotation.x:0,armL:this.parts.armL?this.parts.armL.rotation.x:0};
    if(isStandin){const s=this.h/(c.height||1);c.group.scale.setScalar(s)}
    this.bob.add(c.group);
    if(this.o.toon)toonify(c.group,this.o.toon);
    if(this.o.outline)addOutline(c.group,this.h,c.group.scale.x);
    this.mats=[];c.group.traverse(m=>{if(!m.isMesh)return;if(this.o.castShadow&&!m.userData.isOutline)m.castShadow=true;
      for(const mt of Array.isArray(m.material)?m.material:[m.material]){if(mt.userData.outline||this.mats.find(x=>x.m===mt))continue;this.mats.push({m:mt,e0:mt.emissive?mt.emissive.clone():null,o0:mt.opacity,t0:mt.transparent})}});
    this._tint=true}
  _setGLB(g){const sc=g.scene;sc.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(sc),hh=Math.max(.001,box.max.y-box.min.y),s=this.h/hh;
    sc.scale.multiplyScalar(s);sc.position.y-=box.min.y*s;
    sc.traverse(o=>{if(o.isSkinnedMesh)o.frustumCulled=false});
    this._setContent({group:sc},false);
    this.mixer=new THREE.AnimationMixer(sc);this.actions={};for(const clip of g.animations||[])this.actions[clip.name]=this.mixer.clipAction(clip);
    // 換上真模型後接續目前的循環動作
    this.curAct=null;const loop=this._loopName||"Idle";if(this.actions[loop]){this.curAct=this.actions[loop];this.curAct.play()}else if(this.actions.Idle){this.curAct=this.actions.Idle;this.curAct.play()}
    this.bobMode=this.actions[loop]?"none":(LOOPS[loop]||"idle")}

  has(name){return !!this.actions[name]}
  // 命中時間點（秒）：真模型的動作抓片長的 45%，補間動作用表定值
  impactTime(name,speed=1){const a=this.actions[name];if(a)return a.getClip().duration*.45/speed;const p=PROC[name];return p?(p.impact==null?p.dur*.5:p.impact)/speed:.2}
  duration(name,speed=1){const a=this.actions[name];if(a)return a.getClip().duration/speed;const p=PROC[name];return p?p.dur/speed:.3}

  resetPose(){const E=this.eng,P=this.pose;E.kill(P.position);E.kill(P.rotation);E.kill(P.scale);P.position.set(0,0,0);P.rotation.set(0,0,0);P.scale.set(1,1,1);this.tremble=0;
    for(const k of ["armR","armL"])if(this.parts[k]){E.kill(this.parts[k].rotation);this.parts[k].rotation.x=this.rest[k]}}

  // 播放動作。循環動作（Idle／Walk／Run）立刻 resolve；單次動作播完才 resolve，並自動回到待機（hold 例外）。
  play(name,{speed=1,hold=false,fade=.12}={}){if(this.eng.dead||this.gone)return Promise.resolve();const tok=++this.seq,loop=name in LOOPS;
    if(loop)this._loopName=name;
    const act=this.actions[name];
    if(act){this.resetPose();act.reset();act.setLoop(loop?THREE.LoopRepeat:THREE.LoopOnce,Infinity);act.clampWhenFinished=true;act.timeScale=speed;
      if(this.curAct&&this.curAct!==act){act.crossFadeFrom(this.curAct,fade,false)}act.play();this.curAct=act;this.bobMode="none";
      if(loop)return Promise.resolve();
      return this.eng.wait(act.getClip().duration/speed).then(()=>{if(tok===this.seq&&!hold&&!PROC[name]?.hold)this.idle()})}
    // 沒有這個動作片段 → 程式補間（真模型則讓 Idle 片段繼續在底下播）
    if(loop){this.resetPose();this.bobMode=LOOPS[name];if(this.mixer&&this.actions.Idle&&this.curAct!==this.actions.Idle){const i=this.actions.Idle;i.reset();this.curAct&&i.crossFadeFrom(this.curAct,fade,false);i.play();this.curAct=i}
      if(this.mixer&&this.actions.Idle)this.bobMode=name==="Idle"?"none":LOOPS[name];return Promise.resolve()}
    const p=PROC[name];if(!p)return this.eng.wait(.3);
    this.resetPose();if(this.mixer&&this.actions.Idle&&this.curAct!==this.actions.Idle){const i=this.actions.Idle;i.reset();this.curAct&&i.crossFadeFrom(this.curAct,fade,false);i.play();this.curAct=i}
    this.bobMode=this.mixer&&this.actions.Idle?"none":"still";
    const T=(obj,props,d,ez)=>this.eng.to(obj,props,d/speed,ez);
    return p.run(this,T).then(()=>{if(tok!==this.seq)return;if(hold||p.hold)return;this.idle()})}
  idle(){return this.play(this._loopName||"Idle")}
  // 設定「單次動作播完後要回到哪個循環動作」，不立刻切換
  setLoop(name){this._loopName=name}

  /* ---------- 閃白／發光／透明度 ---------- */
  flash(color=0xffffff,k=1){this.flashC.set(color);this.flashK=k;this._tint=true}
  glow(color,k){if(color!=null)this.glowC.set(color);this.glowK=k;this._tint=true}
  setOpacity(v){this.opacity=v;for(const x of this.mats){x.m.transparent=v<1?true:x.t0;x.m.opacity=x.o0*v}this.content.traverse(o=>{if(o.userData.isOutline)o.visible=v>.9});this.shadow.material.opacity=(this.cute?.55:.75)*v}

  _update(dt,time){if(this.mixer)this.mixer.update(dt);
    // 待機／走路／飛行的程式擺動
    this.bobT+=dt;const t=this.bobT,b=this.bob,h=this.h,fly=this.isStandin?(this.o.fly||0):0,P=this.parts;
    let y=fly,sy=1,rz=0,rx=0,sw=0;
    if(this.bobMode==="idle"){if(fly)y+=Math.sin(t*2.4)*.07*h;else sy=1+Math.sin(t*(this.cute?3.2:1.8))*(this.cute?.035:.012)}
    else if(this.bobMode==="walk"){y+=Math.abs(Math.sin(t*5.5))*.035*h;rz=Math.sin(t*5.5)*.035;sw=Math.sin(t*5.5)*.55}
    else if(this.bobMode==="run"){y+=Math.abs(Math.sin(t*10))*(this.cute?.14:.05)*h;rx=.22;sw=Math.sin(t*10)*.9}
    else if(this.bobMode==="still"&&fly)y+=0;
    b.position.y=y;b.scale.set(1/Math.sqrt(sy),sy,1/Math.sqrt(sy));b.rotation.set(rx,0,rz);
    if(this.tremble)b.position.x=(Math.random()-.5)*this.tremble*2;else b.position.x=0;
    if(P.legL){P.legL.rotation.x=sw;P.legR.rotation.x=-sw}
    if(P.wingL){const slow=P.wingL.userData.flap,f=slow?Math.sin(t*1.7)*slow:Math.sin(t*(this.bobMode==="still"?22:13))*.55;P.wingL.rotation.z=f;P.wingR.rotation.z=-f}
    if(P.cape)P.cape.rotation.x=(P.cape.userData.rx||0)+Math.sin(t*2.2)*.06+(this.bobMode==="run"?.5:this.bobMode==="walk"?.15:0);
    // 閃白衰減、發光（發光量除以材質的發光強度，避免本來就會發光的材質整個過曝）
    if(this.flashK>0){this.flashK=Math.max(0,this.flashK-dt*5.5);this._tint=true}
    if(this.glowK!==this._g0){this._g0=this.glowK;this._tint=true}
    if(this._tint){this._tint=this.flashK>0;for(const x of this.mats){if(!x.e0)continue;x.m.emissive.copy(x.e0);if(this.glowK>0){const g=this.glowK*.25/Math.max(1,x.m.emissiveIntensity||1);x.m.emissive.r+=this.glowC.r*g;x.m.emissive.g+=this.glowC.g*g;x.m.emissive.b+=this.glowC.b*g}if(this.flashK>0)x.m.emissive.lerp(this.flashC,Math.min(1,this.flashK))}}
    // 假陰影跟著腳下，跳高時縮小
    const r=this.root,s=this.shadow;s.position.x=r.position.x;s.position.z=r.position.z;s.visible=r.visible;
    const lift=Math.max(0,r.position.y+this.pose.position.y+y),k=(this.o.shadow||h*.42)*2*Math.max(.35,1-lift/(h*2.5))*((this.pose.scale.x+1)/2);s.scale.setScalar(k)}

  // 面向某個世界座標（只轉 Y 軸）
  face(p){this.root.rotation.y=Math.atan2(p.x-this.root.position.x,p.z-this.root.position.z)}
  // 身體中心的世界座標（特效用）
  center(out=new THREE.Vector3(),k=.5){return out.set(this.root.position.x,this.root.position.y+this.pose.position.y+(this.isStandin?(this.o.fly||0):0)+this.h*k,this.root.position.z)}
  remove(){this.gone=true;this._off();this.eng.scene.remove(this.root);this.eng.scene.remove(this.shadow);this.shadow.material.dispose();if(this.mixer){this.mixer.stopAllAction();this.mixer.uncacheRoot(this.content)}this.eng.disposeObject(this.root)}
}
export { PROC };
