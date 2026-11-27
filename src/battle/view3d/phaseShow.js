// 魂系 Boss 階段轉換（變身）演出：時間軸、鏡頭、慢放、閃光遮掩、型態節點（P2_*／P3_*）切換、Glow 材質變亮。
// 規格見 art/v2/design.md §3（總長 ≤ 2.8 秒）。只處理畫面，不碰規則；soulScene.js 的 bossPhase() 呼叫 run()。
//
// 型態節點合約（建模 ↔ 動畫）：
//   - 名稱以 P2_ 開頭＝二階才出現、P3_ 開頭＝三階才出現（只看最上層的 P 節點，子節點跟著父節點）。
//   - 匯出時預設隱藏（scale 0 或不可見）；就算沒藏好，載入後這裡也會藏起來。
//   - 剛體部件（掛在骨頭下的一般 Mesh／Group，或名為 P2_* 的骨頭）：爆發那一格用 scale 彈出 0→1.08→1（0.25 秒）。
//     匯出時 scale 是 0 的節點，顯示後的目標 scale 視為 1；片段裡有 scale 軌（例如 IdleAggro 把它 key 成 1）就以片段為準。
//   - SkinnedMesh（或底下有 SkinnedMesh 的節點）縮放沒有作用，只能在爆發那一格切成可見（同樣有閃光遮掩）。
//   - 材質名含 Glow 的發光材質：蓄力時漸亮、爆發瞬間最亮、新階段底值比一階亮（emissiveIntensity 倍率）。
//   - 沒有任何 P 節點（舊模型、替身）時照常演出，只是沒有部件切換。
//   - devourer 三階：GLB 有 PhaseShift2 片段就用它，沒有就用 PhaseShift＋程式特效差異。
import * as THREE from 'three';
import { ease, lerp, rand, clamp } from './engine.js';
import { sfx } from '../../core/audio.js';

const v3=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
// Boss 主色（design.md §2）
const MAIN={sentinel:0x7dffb0,gargoyle:0xff8a3a,priest:0x8fe3ff,executioner:0xb07aff,devourer:0xff3a2a};
const GLOW_MUL=[1,1,1.7,2.3]; // 依型態（1 一階／2 二階／3 三階）的 Glow emissiveIntensity 倍率
const BASE_GLOW=[0,0,.7,1]; // 轉換後 Actor.glow 底值（二階 0.7、三階 1.0）
const TINY=1e-4;

/* ---------- 程式產生的小貼圖 ---------- */
let inkTex=null,paperTex=null;
function inkTexture(){if(inkTex)return inkTex;const S=256,c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d"),h=S/2;
  // 墨潑：中心濃、外緣不規則的飛濺
  for(let i=0;i<46;i++){const a=Math.random()*6.28,r=i<14?rand(0,h*.35):rand(h*.3,h*.92),s=i<14?rand(h*.22,h*.4):rand(3,h*.09);
    const g=x.createRadialGradient(h+Math.cos(a)*r,h+Math.sin(a)*r,0,h+Math.cos(a)*r,h+Math.sin(a)*r,s);g.addColorStop(0,"rgba(0,0,0,.95)");g.addColorStop(.7,"rgba(0,0,0,.75)");g.addColorStop(1,"rgba(0,0,0,0)");
    x.fillStyle=g;x.beginPath();x.arc(h+Math.cos(a)*r,h+Math.sin(a)*r,s,0,6.29);x.fill()}
  inkTex=new THREE.CanvasTexture(c);inkTex.colorSpace=THREE.SRGBColorSpace;return inkTex}
function paperTexture(){if(paperTex)return paperTex;const W=64,H=88,c=document.createElement("canvas");c.width=W;c.height=H;const x=c.getContext("2d");
  x.fillStyle="#cdbb8e";x.fillRect(0,0,W,H);x.fillStyle="rgba(60,40,20,.55)";for(let i=0;i<9;i++)x.fillRect(8,10+i*8,rand(28,48),2); // 原創「字行」：只是細線，不是可讀文字
  const g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,"rgba(255,70,30,0)");g.addColorStop(.8,"rgba(255,70,30,0)");g.addColorStop(1,"rgba(255,60,20,.95)");x.fillStyle=g;x.fillRect(0,0,W,H);
  x.strokeStyle="rgba(255,80,40,.9)";x.lineWidth=3;x.strokeRect(1.5,1.5,W-3,H-3);
  paperTex=new THREE.CanvasTexture(c);paperTex.colorSpace=THREE.SRGBColorSpace;return paperTex}

export function createPhaseShow({eng,fx,bfx,getBoss}){
  const {scene,camera,renderer}=eng;
  const lite=()=>eng.rm||eng.quality==="low";
  const N=x=>Math.max(1,Math.round(x*(lite()?.5:1)));
  // 可選呼叫畫面工程師 screen2.js 的 API（掛在 eng.screen）：不存在、丟錯都不影響演出；回傳 undefined＝沒有這個 API
  const scr=(name,...a)=>{for(const o of [eng.screen,eng.screen2]){const f=o&&o[name];if(typeof f==="function"){try{return f.apply(o,a)??true}catch(e){console.warn("[phaseShow] screen2."+name,e);return true}}}return undefined};

  /* ---------- 型態節點 ---------- */
  const FORM=new WeakMap(); // actor → {content, nodes, glows, form}
  function scan(a){const c=a.content,st={content:c,nodes:[],glows:[],form:(FORM.get(a)||{}).form||1};
    if(c&&!a.isStandin){const tracks=new Set();for(const k in a.actions){for(const t of a.actions[k].getClip().tracks)if(/\.scale$/.test(t.name))tracks.add(t.name.slice(0,-6))}
      const isP=o=>/^P[23]_/i.test(o.name||"");
      c.traverse(o=>{if(!isP(o))return;for(let p=o.parent;p&&p!==c;p=p.parent)if(isP(p))return; // 只取最上層的 P 節點
        let skinned=false;o.traverse(x=>{if(x.isSkinnedMesh)skinned=true});
        const s0=o.scale.clone(),zero=Math.max(Math.abs(s0.x),Math.abs(s0.y),Math.abs(s0.z))<1e-3;
        st.nodes.push({o,form:/^P3_/i.test(o.name)?3:2,tgt:zero?v3(1,1,1):s0,tracked:tracks.has(o.name)||tracks.has(o.uuid),skinned,shown:false,pop:-1})});
      // 隱藏的 SkinnedMesh 不會被 compile：先在這裡編好 shader，爆發那一格才不會卡一下
      const hid=st.nodes.filter(n=>n.skinned);if(hid.length){try{for(const n of hid)n.o.visible=true;renderer.compile(c,camera,scene)}catch(e){}}
      for(const x of a.mats||[])if(/Glow/i.test(x.m.name||"")&&x.m.emissiveIntensity!=null)st.glows.push({m:x.m,ei0:x.m.emissiveIntensity});
      for(const n of st.nodes)n.shown=n.form<=st.form;
      if(st.nodes.length||st.glows.length)setGlow(st,GLOW_MUL[st.form])}
    FORM.set(a,st);return st}
  const stateOf=a=>{let st=FORM.get(a);if(!st||st.content!==a.content)st=scan(a);return st};
  function setGlow(st,k){for(const g of st.glows)g.m.emissiveIntensity=g.ei0*k}
  const popCurve=r=>r>=1?1:r<.6?1.08*ease.out(r/.6):lerp(1.08,1,ease.io((r-.6)/.4)); // 0→1.08→1
  // 每幀在動畫混合器（order 0）之後套用：隱藏中的節點縮到幾乎 0（片段的 scale 軌蓋不過來）、彈出中的節點乘上彈出倍率
  eng.onUpdate(dt=>{const a=getBoss();if(!a||!a.content)return;const st=stateOf(a);
    for(const n of st.nodes){const o=n.o;
      if(!n.shown){if(n.skinned)o.visible=false;else o.scale.setScalar(TINY);continue}
      if(n.skinned){o.visible=true;continue}
      let k=1;if(n.pop>=0){n.pop+=dt/.25;k=Math.max(TINY,popCurve(Math.min(1,n.pop)));if(n.pop>=1)n.pop=-1}
      if(n.tracked){if(Math.max(o.scale.x,o.scale.y,o.scale.z)<1e-3)o.scale.copy(n.tgt);if(k!==1)o.scale.multiplyScalar(k)}
      else if(k!==1||n.pop===-1&&!n.set){o.scale.copy(n.tgt).multiplyScalar(k);n.set=k===1}}},1);
  // 顯示到第 form 型態（2＝二階、3＝三階）；回傳這次新出現的節點數
  function reveal(a,form,pop=true){const st=stateOf(a);st.form=Math.max(st.form,form);let c=0;
    // 三階要「消失」的原部件（例：devourer 原本的長角 HornLongR 換成斷角 P3_HornBroken）；命名 X3_* 亦同
    if(st.form>=3&&st.content)st.content.traverse(o=>{if(/^(HornLongR|X3_)/.test(o.name))o.visible=false});
    for(const n of st.nodes)if(!n.shown&&n.form<=st.form){n.shown=true;n.set=false;n.pop=pop&&!eng.dead?0:-1;if(!pop){n.o.scale.copy(n.tgt)}c++}
    return c}

  /* ---------- 小工具 ---------- */
  const R_MAX=9.3; // 演出鏡頭的最遠半徑（外圈石柱在 10.6 m、牆在 12 m）
  const keepIn=p=>{const r=Math.hypot(p.x,p.z);if(r>R_MAX){p.x*=R_MAX/r;p.z*=R_MAX/r}p.y=Math.max(.25,p.y);return p};
  // 爆發閃光：面向鏡頭的加色光球蓋住 Boss 全身，先滿亮 0.05 秒（≥ 3 幀）再由白轉主色淡出
  function burstFlash(b,color){const m=new THREE.Sprite(new THREE.SpriteMaterial({map:fx.glowTex,color:0xffffff,transparent:true,depthWrite:false,depthTest:false,blending:THREE.AdditiveBlending,fog:false}));
    const c=b.center(v3(),.55);m.position.copy(c);const S=b.h*2.5,col=new THREE.Color(color),W=new THREE.Color(0xffffff);
    fx.temp(m,.2,(k,r)=>{const hold=r<.25;m.scale.setScalar(S*(hold?1:1+.25*(r-.25)));m.material.color.copy(W).lerp(col,hold?0:Math.min(1,(r-.25)/.4));m.material.opacity=hold?1:Math.max(0,1-(r-.25)/.75)});
    m.renderOrder=30}
  // 墨潑地貼片
  function inkSplat(p,r1,dur=1.3,opacity=.85,color=0x060408){const m=new THREE.Mesh(fx.G.plane,new THREE.MeshBasicMaterial({map:inkTexture(),color,transparent:true,depthWrite:false,opacity:0,fog:false}));
    m.rotation.set(-Math.PI/2,0,rand(0,6.28));m.position.set(p.x,.035,p.z);
    return fx.temp(m,dur,(k,r)=>{m.scale.setScalar(r1*2*(.35+.65*ease.out3(Math.min(1,r/.3))));m.material.opacity=opacity*(r<.08?r/.08:r>.55?1-(r-.55)/.45:1)})}
  // 全畫面墨邊（自己的 DOM 層）：k 0..1＝收縮程度
  let inkEl=null;
  function inkEdge(k){if(!inkEl){if(k<=0)return;inkEl=document.createElement("div");inkEl.style.cssText="position:absolute;inset:0;pointer-events:none;opacity:0;will-change:opacity,background";eng.overlay.appendChild(inkEl)}
    const r=lerp(78,34,k);inkEl.style.background=`radial-gradient(ellipse at center,transparent ${r}%,rgb(6 4 8/.88) ${r+18}%,rgb(2 1 3/.97) 100%)`;inkEl.style.opacity=k>0?Math.min(1,k*1.6):0}
  // 地面破土尖刺（樹根／冰刺）
  function spike(p,{h=1.2,w=.22,mat,dur=.9,tilt=null}){const m=new THREE.Mesh(fx.G.cone,mat);m.position.copy(p);m.position.y=0;
    if(tilt)m.rotation.set(tilt.x,rand(0,6.28),tilt.z);else m.rotation.set(rand(-.25,.25),rand(0,6.28),rand(-.25,.25));
    return fx.temp(m,dur,(k,r)=>{const s=r<.2?ease.back(r/.2):r>.72?Math.max(.01,1-(r-.72)/.28):1;m.scale.set(w*s,Math.max(.01,h*s),w*s);m.position.y=m.scale.y*.45})}
  // 地面放射裂痕（行刑者）
  function crack(p,dir,len,color){const m=new THREE.Mesh(fx.G.plane,fx.basic(color));m.rotation.set(-Math.PI/2,0,Math.atan2(dir.x,dir.z));m.renderOrder=12;
    return fx.temp(m,1.1,(k,r)=>{const L=len*ease.out3(Math.min(1,r/.22));m.scale.set(.09*(1-r*.5),L,1);m.position.set(p.x+dir.x*L/2,.04,p.z+dir.z*L/2);m.material.opacity=r<.5?.95:.95*(1-(r-.5)/.5)})}
  // 殘影：面向鏡頭、拉長的主色光片（魂系不用膠囊殘影）
  function afterimage(p,h,color,dur=.55){const m=new THREE.Sprite(new THREE.SpriteMaterial({map:fx.glowTex,color,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false}));m.position.set(p.x,h*.5,p.z);
    return fx.temp(m,dur,(k,r)=>{m.scale.set(h*.55*(1+r*.3),h*1.15,1);m.material.opacity=.55*(1-r)})}
  // HUD 淡出到 40%（演出結束一定還原）
  const huds=()=>{const host=eng.container&&eng.container.parentElement;return host?[...host.querySelectorAll(".hpbox")]:[]};
  function hudFade(on){for(const el of huds()){el.style.transition="opacity .3s";el.style.opacity=on?".4":""}}

  /* ---------- 演出 ---------- */
  // S：soulScene 提供的掛鉤 {hero, alive(), setCine(c|null), cut(pos,look,fov), pushBack(d,dur), dust(p,n), flamesDown(k,hold,back), burst(), settle(), csReset(dur)}
  async function run(b,p,S){const id=b.data&&b.data.id||"sentinel",form=(p.phase|0)+1,color=MAIN[id]||b.eye||0xff3020,rm=!!eng.rm,t0=performance.now(),g0=eng.time;
    const hero=S.hero,bp=b.root.position.clone(),hp=()=>hero.root.position;
    // 片段：三階有 PhaseShift2 就用；速度正規化讓爆發落在 0.75–1.1 秒、整段片長 ≤ 約 2.5 秒
    const clip=form>=3&&b.has("PhaseShift2")?"PhaseShift2":"PhaseShift",hasClip=b.has(clip);
    const D=b.duration(clip),H=b.impactTime(clip);
    const sp=hasClip?clamp(Math.max(H/1.02,D/2.5),.75,2.4):Math.max(.6,D/1.3);
    const T=clamp(H/sp,.75,1.02),TS=Math.max(.6,T-.15); // T＝爆發（遊戲時間）、TS＝開始 0.35 倍慢放
    const tCam=T+.85,tEnd=T+1.3,clipEnd=D/sp;
    const st=stateOf(b);
    const d=v3().subVectors(hp(),bp).setY(0);if(d.lengthSq()<1e-4)d.set(0,0,1);d.normalize(); // Boss → 主角
    const sv=v3(d.z,0,-d.x); // 戰鬥鏡頭所在的那一側
    const headY=b.h*.8;
    // 各 Boss 鏡頭（design.md §3.2）：以 Boss 為圓心的極座標——ang＝偏離「Boss→主角」方向的角度（往戰鬥鏡頭那一側）、R＝離 Boss 的距離。
    // 主角在前景的一側（肩後仰拍），不擋住 Boss；主角被壓得很近時 R 自動加大，鏡頭不會鑽進主角身體
    const dist=Math.hypot(hp().x-bp.x,hp().z-bp.z);
    const RK=clamp(1.35-.35*eng.aspect,1,1.22); // 直式畫面（水平視角窄）退遠一點，Boss 頭不被切掉
    const at=(ang,R,y)=>{const a=ang*Math.PI/180;R*=RK;return keepIn(bp.clone().addScaledVector(d,Math.cos(a)*R).addScaledVector(sv,Math.sin(a)*R).setY(y))};
    let pos0,look0,fov0=50,fov1=44;
    if(id==="sentinel"){pos0=at(50,Math.max(dist+1,4.2),.5);look0=bp.clone().setY(b.h*.95)}   // 偏側面、看頭頂上方：背後門板裂開、樹根往上張
    else if(id==="gargoyle"){pos0=at(40,Math.max(dist+1.3,4.6),.85);look0=bp.clone().setY(headY)} // 機位略高（翅膀張開比較寬，退遠一點）
    else if(id==="priest"){pos0=at(28,Math.max(dist+1.3,4.3),.35);look0=bp.clone().setY(b.h*.88)} // 正面略低，看頭後光環
    else if(id==="devourer"&&form>=3){pos0=at(32,Math.max(dist+4,7.2),1.4);look0=bp.clone().setY(b.h*.5);fov0=54;fov1=50} // 先拉遠看全身墨潮
    else{pos0=at(40,Math.max(dist+1,4.2),.5);look0=bp.clone().setY(headY)}
    // 蓄力時 Boss 多半跪下／蜷縮：注視點先放在身體中段（0.5→0.62 身高），爆發後才抬到各 Boss 的頭部目標（lookHi）
    const lookHi=look0.y,lookLo=Math.min(lookHi,b.h*.5);look0.y=lookLo;
    // 主角保護：鏡頭與主角的水平距離至少 1.7 m（主角被擊退、鏡頭推近時都套用）
    const guard=p=>{const h=hp(),dx=p.x-h.x,dz=p.z-h.z,l=Math.hypot(dx,dz);if(p.y<2.1&&l<1.7){const k=1.7/Math.max(.001,l);if(l<.001){p.addScaledVector(sv,1.7)}else{p.x=h.x+dx*k;p.z=h.z+dz*k}}return keepIn(p)};
    // 爆發點光（借用場景的 danger 點光，design §4.1 的「爆發點光，用完歸零」）：放在 Boss 與鏡頭之間，低機位仰拍時 Boss 才不會整隻黑掉
    const lightPos=()=>{const c=b.center(v3(),.62),cp=(cine&&!rm?cine.pos:camera.position),dv=v3().subVectors(cp,c).setY(0);if(dv.lengthSq()<1e-4)dv.copy(d);return c.addScaledVector(dv.normalize(),1.7)};
    const light=k=>{if(S.light)S.light(k,color,lightPos())};
    const polar=p=>{const r=v3().subVectors(p,bp).setY(0);return{ang:Math.atan2(r.dot(sv),r.dot(d))*180/Math.PI,R:r.length(),y:p.y}};
    const cine={pos:pos0.clone(),look:look0.clone(),fov:fov0,k:5};
    if(!rm)S.setCine(cine);
    // 開場：低頻嗡鳴、HUD 淡出、地面主色符紋圈、Boss 發光 0.5→1.0
    hudFade(true);eng.rumble(.022*(b.h/3.2),T);sfx("heavy",{v:.3});b.glow(color,.5);
    const circ=fx.circle(bp,{color,r:.2,spin:1.6});circ.setRadius(b.h*.75);
    b.play(clip,{speed:sp});
    if(form>=3&&!b.has("PhaseShift2")&&!eng.rm){ // 沒有三階專用片段：用程式補一點「痙攣」差異
      b.tremble=Math.max(b.tremble||0,.018*b.h)}
    let fired=false,cutBack=0,pulled=false,idled=false,inward=0,lastT=0,squeezed=false,ownInk=false;const p3=id==="devourer"&&form>=3;
    const burstPos=v3(),orbitFrom=v3();
    const total=tEnd;
    // 特效（別人的函式或自己的）丟錯不能中斷時間軸：時間軸一斷，鏡頭與 AI 就回不來
    const safe=f=>{try{f()}catch(e){console.warn("[phaseShow]",e)}};
    const tick=t=>{const dt=Math.max(0,t-lastT);lastT=t;if(!S.alive())return;
      // 蓄力：主色粒子由外往 Boss 吸入（總共 ≤ 60 顆）、Glow 漸亮、鏡頭緩推 0.6 m、FOV 50→44
      if(t<T){const k=t/T;b.glow(color,lerp(.5,1,k));light(lerp(.5,6,ease.in(k)));setGlow(st,GLOW_MUL[form-1]*lerp(1,1.5,k));
        inward+=dt*N(60)/Math.max(.3,T-.1);while(inward>=1){inward--;const a=rand(0,6.28),R=b.h*rand(.9,1.4),c=b.center(v3(),rand(.35,.8)),from=v3(c.x+Math.sin(a)*R,rand(.2,b.h*1.1),c.z+Math.cos(a)*R);
          fx.emit({p:from,n:1,color:[color,0xffffff],speed:[R*1.7,R*2.1],dir:[c.x-from.x,c.y-from.y,c.z-from.z],spread:.04,size:[.05,.12],life:[.38,.5]})}
        if(!rm){const kk=ease.io(Math.min(1,t/Math.max(.3,TS)));cine.pos.copy(pos0).addScaledVector(v3().subVectors(bp,pos0).setY(0).normalize(),.6*kk);cine.fov=lerp(fov0,fov1,kk);cine.look.y=lerp(lookLo,Math.min(lookHi,b.h*.62),kk);cine.k=t<.35?5:3.2}
        // devourer 二階：爆發前 0.35 秒推到胸口嘴特寫
        if(!rm&&id==="devourer"&&form===2&&t>T-.38){const kk=ease.out((t-(T-.38))/.38);const close=at(45,2.7,b.h*.56);cine.pos.lerpVectors(pos0,close,kk);cine.look.lerpVectors(look0,bp.clone().setY(b.h*.62),kk);cine.fov=lerp(fov1,46,kk);cine.k=4.5}
        if(t>=TS){if(!pulled){pulled=true;eng.slowmo(.35,323);sfx("step",{v:.15})} // 爆發前 0.35 倍慢放，約 0.15 秒遊戲時間；聲音先收住
          if(!squeezed){squeezed=true;if(scr("inkSqueeze",p3?1:.6,300,40,450)===undefined)ownInk=true;else if(p3)ownInk=true}
          if(ownInk)inkEdge((p3?.95:.6)*Math.min(1,(t-TS)/Math.max(.05,T-TS)))}}
      // 爆發：同一格顯示 P 節點、閃光、震屏、FOV 彈、橫幅
      if(t>=T&&!fired){fired=true;doBurst()}
      if(fired&&t<tCam){const k=(t-T)/(tCam-T);
        if(!rm&&!cutBack){ // 繞 Boss 15° 並緩退
          const e=ease.out(k),q=polar(burstPos);cine.pos.copy(at(q.ang+15*e,q.R/RK+(id==="devourer"&&form===2?1.6:.5)*e,q.y+(id==="gargoyle"?.35*e:0)));
          if(!(id==="devourer"&&form>=3))cine.look.y=lerp(cine.look.y,lookHi+(id==="gargoyle"?Math.tan(8*Math.PI/180)*q.R*e:0),Math.min(1,k*3)); // 抬頭看新型態；gargoyle 隨騰空上揚 8°
          cine.k=3.2}
        if(cutBack&&t>=cutBack){cutBack=0;cine.pos.copy(orbitFrom);cine.look.copy(look0).setY(lookHi);S.cut(orbitFrom,cine.look,cine.fov);cine.k=60;eng.wait(.05).then(()=>{cine.k=3.2})}
        light(lerp(22,0,ease.out(Math.min(1,k*1.25))));
        // 爆發後 Glow 由最亮回到新階段的底值
        setGlow(st,lerp(GLOW_MUL[form]*1.8,GLOW_MUL[form],ease.out(Math.min(1,k*1.4))))}
      if(!rm&&cine.k!==-1&&!(cutBack&&t<cutBack))guard(cine.pos);
      if(fired&&t>=tCam&&cine.k!==-1){cine.k=-1;S.setCine(null);S.csReset(.45)}
      // 片段快播完（或最晚 T+1.2）切 IdleAggro
      if(fired&&!idled&&t>=Math.max(T+.8,Math.min(clipEnd-.2,T+1.2))){idled=true;S.settle()}};
    function doBurst(){const c=b.center(v3(),.55);
      const nNew=reveal(b,form);setGlow(st,GLOW_MUL[form]*1.8);b.glow(color,1.6);b.tremble=0;
      burstFlash(b,color);if(scr("flash",0xffffff,.15,120)===undefined)fx.pulseVig("white",.15,.12);inkEdge(0);circ.remove();
      eng.shake(rm?.08:.16,.9,{freq:11});eng.rumble(.05,1.2);sfx("roar",{v:.95});sfx("heavy",{v:.8});S.flamesDown(.3,.5,1);
      if(!rm){cine.fov+=6;eng.to(cine,{fov:cine.fov-6},.3,ease.out)}
      // 特效工程師的 phaseBurst：其中的光柱在低機位近景會蓋滿整個畫面（看不到變身），演出期間把光柱改細、改短
      safe(()=>bfx.phaseBurst(b,p.phase,{pillarScale:.4,pillarDur:.6})); // 特效工程師：身體膨脹回彈、光柱、咆哮衝擊波、閃電
      // （爆發環、墨潑、符字粒子、閃電由 bossfx.phaseBurst 負責，這裡不重複）
      fx.emit({p:c,n:N(24),color:[color,0xffffff,0xffd27a],speed:[3,9],size:[.05,.12],life:[.4,.9],drag:1.4});
      S.dust(bp,16);S.pushBack(.4,.4);hero.play("Guard");hero.knock(.2,.15);
      fx.banner(p.info&&p.info.name||"",`soul phase ph-${id}${form>=3?" p3":""}`,1.4);
      S.burst();scr("setPhaseMood",p.phase,1.2);
      burstPos.copy(cine.pos);orbitFrom.copy(cine.pos);
      safe(()=>sig(id,form,b,c,color));
      if(window.__soulTest){(window.__phaseLog=window.__phaseLog||[]).push({id,form,clip,hasClip,sp:+sp.toFixed(3),T:+T.toFixed(3),nodes:nNew,glows:st.glows.length,burstMs:Math.round(performance.now()-t0)})}}
    // 各 Boss 爆發特效差異（design.md §3.2）
    function sig(id,form,b,c,color){const P=bp,h=b.h;
      if(id==="sentinel"){const mat=new THREE.MeshStandardMaterial({color:0x3a2a1a,roughness:.9,emissive:0x1f4a18,emissiveIntensity:.7});
        for(let i=0;i<6;i++){const a=i/6*6.283+rand(-.2,.2),rr=rand(1.3,2.3);eng.wait(rand(0,.2)).then(()=>{const q=v3(P.x+Math.sin(a)*rr,0,P.z+Math.cos(a)*rr);
          spike(q,{h:rand(1.2,1.9),w:.26,mat,dur:1,tilt:{x:Math.cos(a)*.35,z:-Math.sin(a)*.35}});S.dust(q,4,[0x4a3a2a,0x6a5a40]);
          fx.emitN({p:v3(q.x,.3,q.z),n:N(7),color:[0x6a4a30,0x8a6a40,0x3a2a1a],speed:[1.5,4],up:2.5,size:[.05,.11],life:[.5,.9],gravity:12})})}
        eng.wait(1.05).then(()=>mat.dispose());
        fx.emit({p:v3(P.x,h*.6,P.z),n:N(30),color:[0x7dffb0,0xc8ffd8],speed:[.4,1.6],up:.6,size:[.04,.09],life:[1.4,2.4],gravity:-.25,drag:.8,radius:h*.35})} // 苔綠孢子
      else if(id==="gargoyle"){fx.emitN({p:c,n:N(46),color:[0x5d5a57,0x7a7f88,0x9aa0a8],speed:[3,9],up:3,size:[.08,.2],life:[.6,1.3],gravity:13,drag:.4,radius:h*.25}); // 石殼碎片
        fx.emit({p:v3(P.x,h*.4,P.z),n:N(34),color:[0xff8a3a,0xffc36a,0xff5a1a],speed:[.6,2.2],up:4,size:[.04,.1],life:[.7,1.4],gravity:-1.2,drag:.6,radius:h*.3})} // 熔橘火星上竄
      else if(id==="priest"){fx.ring(P,{color:0xdff6ff,r1:8,dur:.4,opacity:.85,thin:false});fx.ring(P,{color:0x8fe3ff,r1:8.5,dur:.9,opacity:.5});
        if(!lite())inkSplat(P,8,1.6,.35,0xcfefff); // 結霜圈（淡藍貼片擴散）
        const ice=new THREE.MeshBasicMaterial({color:0x9fe6ff,transparent:true,opacity:.92});
        for(let i=0;i<12;i++){const a=i/12*6.283,rr=1.35+.25*(i%2);spike(v3(P.x+Math.sin(a)*rr,0,P.z+Math.cos(a)*rr),{h:i%2?1.1:1.6,w:.2,mat:ice,dur:1.1,tilt:{x:Math.cos(a)*.3,z:-Math.sin(a)*.3}})}
        eng.wait(1.15).then(()=>ice.dispose());
        fx.emitN({p:v3(P.x,h*.9,P.z),n:N(44),color:[0xffffff,0xdff6ff],speed:[1.5,3.5],up:1.2,size:[.04,.09],life:[1.6,2.4],gravity:1.1,drag:4,alpha:.9,radius:h*.3})} // 雪粒在空中停一下再落
      else if(id==="executioner"){const ax=v3(P.x+d.x*1.25,0,P.z+d.z*1.25);
        for(let i=0;i<7;i++){const a=Math.atan2(d.x,d.z)+(i-3)*.42+rand(-.1,.1);crack(ax,v3(Math.sin(a),0,Math.cos(a)),rand(1.8,3.2),i%2?0xb07aff:0x7a2aff)}
        fx.flash(ax,{color:0xb07aff,size:2.4,dur:.3,opacity:.8});
        fx.emitN({p:v3(P.x-d.x*.4,h*.7,P.z-d.z*.4),n:N(22),color:[0x1a1024,0x2a1a3a,0x3a2a5a],speed:[.6,2],up:1,size:[.35,.7],life:[.7,1.2],alpha:.5,drag:1.3,grow:.8,radius:h*.25}); // 影臂拖出的墨絲
        for(const s of [-1,1])afterimage(v3(P.x+sv.x*s*1.05,0,P.z+sv.z*s*1.05),h,0xb07aff);
        // 硬切側面 0.1 秒再切回（處刑感）
        if(!rm){const side=at(90,4.4,1.15),lk=P.clone().setY(h*.5);S.cut(side,lk,44);cine.pos.copy(side);cine.look.copy(lk);cine.k=60;cutBack=T+.14}}
      else if(id==="devourer"&&form===2){pages(b);
        const hc=hero.center(v3(),.6);for(let i=0;i<N(26);i++)eng.wait(i*.025).then(()=>{const from=hc.clone().add(v3(rand(-.4,.4),rand(-.3,.4),rand(-.4,.4))),to=b.center(v3(),.62);
          fx.emit({p:from,n:1,color:[0xffd27a,0xfff2c0],speed:[from.distanceTo(to)*1.9,from.distanceTo(to)*2.1],dir:[to.x-from.x,to.y-from.y,to.z-from.z],spread:.03,size:[.05,.1],life:[.45,.5]})})} // 金字粒子被吸向胸口
      else if(id==="devourer"){ // 三階：墨收縮 → 紅光環炸開、墨潮推到場邊、去色 0.4 秒
        fx.ring(P,{color:0xff3a2a,r1:12,dur:.8,opacity:.9,thin:false});fx.burstRing(b.center(v3(),.9),{color:0xff3a2a,r1:h*2,dur:.5});
        fx.ring(P,{color:0x050308,r1:9.5,dur:1.3,opacity:.85,normal:true,thin:false});if(!lite())inkSplat(P,7.5,1.5,.75);
        fx.emitN({p:v3(P.x,.2,P.z),n:N(30),color:[0x0b0a0f,0x1a0a10],speed:[3,6],flat:.2,up:.3,size:[.5,1],life:[.8,1.3],alpha:.6,drag:1,grow:1});
        if(!rm){cine.pos.copy(at(40,Math.max(3.6,dist+.6),.6));cine.look.set(P.x,h*.85,P.z);cine.fov=44+6;cine.k=9;burstPos.copy(cine.pos)}
        if(scr("desaturate",.3,400,500)===undefined){const U=eng.post&&eng.post.grade&&eng.post.grade.uniforms;if(U&&U.uSat){const s0=U.uSat.value;U.uSat.value=s0*.32;eng.wait(.4).then(()=>eng.tween(.3,k=>{U.uSat.value=lerp(s0*.32,s0,k)}))}}}}
    // 書頁貼片（≤ 40 片）從披風飛旋成背後一對紙翼
    function pages(b){const n=lite()?18:36,P=bp,h=b.h,mats=[],back=v3(-d.x,0,-d.z),geo=fx.G.plane;
      for(let i=0;i<n;i++){const m=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({map:paperTexture(),transparent:true,side:THREE.DoubleSide,depthWrite:false,fog:true}));mats.push(m.material);
        const s=i%2?1:-1,j=(i>>1)/(n/2),a0=rand(0,6.28),r0=rand(.6,1.4),y0=rand(.3,h*.6);
        const wing=v3(P.x,0,P.z).addScaledVector(back,.5+.25*j).addScaledVector(sv,s*(.5+j*h*.55)),wy=h*(.62+.35*Math.sin(j*Math.PI*.9));
        m.scale.set(.26,.36,1);fx.temp(m,1.6,(k,r)=>{const f=ease.io(Math.min(1,r/.55)),a=a0+r*7;
          const sx=P.x+Math.sin(a)*r0,sz=P.z+Math.cos(a)*r0;m.position.set(lerp(sx,wing.x,f),lerp(y0,wy,f)+Math.sin(r*9+i)*.04*(1-f),lerp(sz,wing.z,f));
          m.rotation.set(rand(-.05,.05)+r*3*(1-f),a*(1-f)+Math.atan2(sv.x,sv.z)*f,s*(.3+j*.6)*f);m.material.opacity=r>.8?1-(r-.8)/.2:1})}}
    try{await eng.tween(total,(k,r)=>tick(r*total),ease.lin)}
    finally{if(S.light)S.light(0);if(!fired&&S.alive()){reveal(b,form,false)}inkEdge(0);hudFade(false);circ.remove();b.tremble=0;
      if(S.alive()){if(cine.k!==-1){S.setCine(null);S.csReset(.45)}if(!idled)S.settle();setGlow(st,GLOW_MUL[form]);b.glow(color,BASE_GLOW[form]);
        // 新階段的眼光（Actor.glow 的顏色）恢復成 Boss 本來的眼色
        b.glow(b.eye,BASE_GLOW[form])}
      if(window.__soulTest){const L=window.__phaseLog||[],e=L[L.length-1];if(e&&e.id===id&&e.form===form){e.totalMs=Math.round(performance.now()-t0);e.gameS=+(eng.time-g0).toFixed(3)}}}}

  return{run,reveal,state:a=>stateOf(a)};
}
