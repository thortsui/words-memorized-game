// 單字魂 v2 特效（VFX）：玩家這一側的「金」與 Boss 那一側的「墨＋主色」（art/v2/design.md §4）。
// 只處理畫面，不碰規則與數值。soulScene.js 只在幾個事件點各加一行呼叫（hitBoss／parry／dodge／guard／hurt／bossDeath），
// 其餘事件用 wrap(H) 包在場景的事件處理器外面（在原本的演出之前／之後補特效，不改原本的流程與等待時間）。
//
//   #1–4 玩家刀光：fx.slash 在魂系已改成筆刷刀光（fx.js）；這裡依連斬段數調粗細亮度、第 3 段起墨滴飛濺、第 5 段金色收鋒大弧、
//        完美斬的「一閃」細線＋金箔、終結斬的貫穿畫面金墨橫劃＋地面墨暈
//   #5 彈反金色圓相＋交叉金筆＋Boss 武器迸出主色碎光　#6 翻滾墨色殘影＋塵土弧（完美閃避加金色時間漣漪）
//   #7 受擊暗紅墨潑　#8 格擋鐵灰火花　#9 突襲落點墨圈、眼睛紅閃　#12 延遲攻擊解鎖的武器尖端星芒
//   #18 Boss 受擊材質碎屑　#19 弱點擊破金色裂紋　#22 Boss 死亡化為墨與金色符字、最後一點金光落到主角劍上
//   #23 喝藥的淡綠＋金螺旋　#24 各場地環境粒子（灰燼、石塵、墨霧、飄浮書頁）
// 效能：FPS < 40 持續 2 秒 → eng.fxLow＝true、eng.fxK＝0.5（粒子減半、關掉墨潑貼片與殘影，fx.js 讀這兩個值）；FPS ≥ 52 持續 6 秒恢復。
import * as THREE from 'three';
import { ease, lerp, rand, clamp } from './engine.js';
import { weaponTip, headPos } from './bossfx.js';

export const PAL={gold:0xffd27a,ink:0x0b0a0f,white:0xfff2c0,hurt:0xc0242a,warn:0xff2a1a,
  boss:{sentinel:0x7dffb0,gargoyle:0xff8a3a,priest:0x8fe3ff,executioner:0xb07aff,devourer:0xff3a2a}};
const v3=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
const {gold:GOLD,ink:INK,white:WHITE,warn:WARN}=PAL;

let cssDone=false;
function injectCss(){if(cssDone||typeof document==="undefined")return;cssDone=true;const s=document.createElement("style");s.textContent=
  `.v3-t.soul.vx-perfect{font:900 30px/1 "Noto Serif TC","Noto Sans TC",serif;letter-spacing:.32em;color:#ffe7b0;text-shadow:0 0 16px #ffb84a,0 0 4px #000,0 2px 0 #1a1208}
   .v3-t.soul.vx-break{font:900 28px/1 "Noto Serif TC","Noto Sans TC",serif;letter-spacing:.3em;color:#ffd27a;text-shadow:0 0 14px #ff9a2a,0 0 4px #000}
   .vx-veil{pointer-events:none;will-change:opacity,transform}`;document.head.appendChild(s)}

export function createVfx2({eng,fx,bfx,hero,boss}){
  injectCss();
  const K=fx.K,st={perfect:false,limitMs:0,amb:null,peak:{add:0,norm:0,streak:0},lowEvents:0};
  eng._vfxHero=hero;eng.fxK=1;eng.fxLow=false;
  const B=()=>boss();
  const lite=()=>eng.rm||eng.quality==="low"||eng.fxLow;
  const n=x=>Math.max(1,Math.round(x*(lite()?.5:1)));
  const sig=b=>bfx.sig(b);

  // 主角的武器拖尾改成金色（玩家的力量＝金）
  hero.trailColor=GOLD;const setTrail=()=>{if(hero.trail)hero.trail.color(GOLD)};hero.ready&&hero.ready.then(setTrail);

  /* ---------- 掉幀降級與預算統計 ---------- */
  let lowT=0,okT=0;
  eng.onUpdate((dt,rdt)=>{const c=fx.counts;if(c){const P=st.peak;if(c.add>P.add)P.add=c.add;if(c.norm>P.norm)P.norm=c.norm;if(c.streak>P.streak)P.streak=c.streak}
    if(eng.quality==="low"){eng.fxLow=true;eng.fxK=.5;return}
    const f=eng.fps;if(!f||!eng.armed||eng.paused)return;
    if(f<40){lowT+=rdt;okT=0}else{lowT=Math.max(0,lowT-rdt*.5);okT=f>=52?okT+rdt:0}
    if(!eng.fxLow&&lowT>=2){eng.fxLow=true;eng.fxK=.5;st.lowEvents++;lowT=0}
    else if(eng.fxLow&&okT>=6){eng.fxLow=false;eng.fxK=1;okT=0}},5);

  /* ---------- Boss 發光材質亮度上限（可讀性） ----------
     新模型的 Glow 材質面積大、強度 1.7–6（二、三階再 ×1.7／×2.3）。Boss 被染成金色（弱點擊破）、受擊閃白、
     階段底色時，發光量＝顏色亮度×強度會到 4–6，經 bloom 放大後整個畫面被洗成一片。
     這裡在每次繪製前把「發光顏色亮度 × 強度」壓到 GLOW_CAP 以下，畫完再還原，不改任何人寫進材質的值；
     顏色變化（變紅、變金、閃白）照常看得到，只是不會亮到溢出。 */
  // 上限：發光部位一律 0.5；只有眼睛（材質名含 Eye）放寬到 1.6，眼光照樣刺眼。
  // 不用網格大小判斷：噬語魔王的書頁邊、符文是很多小片，單片小、合起來卻佔半個畫面。
  // 0.5 是在噬語魔王三階＋弱點擊破追加連斬（最糟情況）逐步試出來的：0.8 仍會在連斬尾段整片泛光，0.5 主角與 Boss 輪廓都清楚。
  const GLOW_CAP=.5,GLOW_CAP_SMALL=1.6;let gB=null,gN=-1;
  const lumOf=c=>.2126*c.r+.7152*c.g+.0722*c.b;
  function capBefore(r,s,cam,g,m){if(!m||!m.emissive||!st.glowSet||!st.glowSet.has(m))return;const L=lumOf(m.emissive)*m.emissiveIntensity,C=/Eye/i.test(m.name||"")?GLOW_CAP_SMALL:GLOW_CAP;
    if(L>C){m.userData._ei=m.emissiveIntensity;m.emissiveIntensity*=C/L}}
  function capAfter(r,s,cam,g,m){if(m&&m.userData._ei!=null){m.emissiveIntensity=m.userData._ei;m.userData._ei=null}}
  eng.onUpdate(()=>{const b=B();if(!b||!b.content||!b.mats)return;if(b===gB&&b.mats.length===gN)return;gB=b;gN=b.mats.length;
    st.glowSet=new Set(b.mats.filter(x=>x.glow).map(x=>x.m));
    b.content.traverse(o=>{if(!o.isMesh||o.userData._glowCap)return;o.userData._glowCap=1;
      const ob=o.onBeforeRender,oa=o.onAfterRender;
      o.onBeforeRender=function(...a){ob&&ob.apply(this,a);capBefore.apply(this,a)};o.onAfterRender=function(...a){capAfter.apply(this,a);oa&&oa.apply(this,a)}})},4);

  const camDir=p=>{const c=eng.camera.getWorldPosition(v3());return c.sub(p).normalize()};
  const toward=(p,d)=>p.clone().addScaledVector(camDir(p),d);

  /* ---------- #1–4、#18 命中 Boss（soulScene 的 impact 在火花之後呼叫） ---------- */
  // 每一刀的筆刷樣式（H.hit 之前設定，fx.slash 取用）：連斬段數越高越粗、越亮
  function slashStyle(p){const mv=p.move||"",i=p.index||0;
    if(mv==="chain")return{w:.22+.04*Math.min(4,i),hdr:1.05+.08*Math.min(4,i),size:1+.04*i,inkOp:.5+.06*Math.min(4,i),dur:1};
    if(mv==="counter")return{w:.3,hdr:1.4,size:1.1,inkOp:.7};return{w:.24,hdr:1.15}}
  function hitBoss(p,b,c,power=1){if(!b||!p)return;const S=sig(b),id=b.data&&b.data.id,mv=p.move||"",i=p.index||0,N=p.n||p.total||1,hp=hero.root.position;
    const away=v3().subVectors(c,hp).setY(.25).normalize(),cc=toward(c,.25);
    // #1 金火花 15 顆＋短白閃
    fx.emit({p:cc,n:n(15),color:[GOLD,WHITE,0xffb84a],speed:[2,6.5],dir:away,spread:.95,size:[.05,.11],life:[.25,.42],gravity:7,drag:1.2,kind:1});
    fx.flash(cc,{color:0xffffff,size:.55+.15*power,dur:.08,opacity:.9});
    // #18 Boss 受擊：主色碎光＋材質碎屑（鏽／石／冰／墨／紙）
    fx.emit({p:cc,n:n(8),color:[S.main,0xffffff],speed:[2,5],dir:away,spread:1,size:[.04,.09],life:[.2,.36],kind:1});
    const mat=id==="devourer"?{color:[0xd8c8a0,0xb89a60,0x2a0a0a],kind:[K.page,K.page,K.splat]}:id==="executioner"?{color:[INK,0x1a1024,0x2a1a3a],kind:[K.drop,K.splat]}:id==="priest"?{color:[0xbfe9ff,0xffffff,0x9fd8f0],kind:[2,K.ash]}:{color:S.debris,kind:[2,K.ash]};
    fx.emitN({p:c,n:n(8+4*Math.min(2,power)),color:mat.color,speed:[1.5,4],dir:away,spread:.9,up:1.2,size:id==="devourer"?[.14,.22]:[.05,.12],life:[.5,.9],gravity:id==="devourer"?3:10,drag:id==="devourer"?1.4:.5,kind:mat.kind});
    // #2 連斬：第 3 段起墨滴飛濺；第 5 段金色收鋒大弧
    if(mv==="chain"&&i>=2){fx.emitN({p:cc,n:n(10+4*(i-2)),color:[INK,0x18141c],speed:[2.5,6.5],dir:away,spread:.75,size:[.05,.14],life:[.45,.85],gravity:9,kind:[K.drop,K.splat,2]});
      if(i>=3)fx.decal(v3(c.x,0,c.z).addScaledVector(away.setY(0).normalize(),.4),{color:INK,s0:.2,s1:.9+.2*i,dur:1.1,op:.65})}
    // 收鋒大弧：芯用金色、亮度 .85（原本白熱芯 1.45）、晚 0.14 秒出（原本 0.04，和命中閃光、火花、徑向模糊同一格，經 bloom 變成蓋住主角的一團光）
    if(mv==="chain"&&N>=5&&i===4&&!p.kill)eng.wait(.14).then(()=>fx.brush(c,{size:Math.min(2.4,b.h*.7+.5),ang:-.35,sweep:2.4,w:.28,dur:.55,hdr:.85,core:0xffd27a,inkOp:.85,draw:.3}));
    // #3 完美斬：0.05 秒後第二道金色細線「一閃」＋金箔緩慢飄落（第一刀 30 片＋「完美」字）
    if(st.perfect&&mv==="chain"){const a=rand(-.45,.45);eng.wait(.05).then(()=>fx.brush(c,{straight:true,ang:a,size:.34,stretch:Math.min(9,b.h*1.3+1.5)/.34*.5,w:.1,dur:.32,draw:.22,hdr:1.8,ink:false,toCam:.5}));
      fx.emit({p:cc,n:n(i===0?30:8),color:[GOLD,0xffe7a8,0xc89a3a,0xfff2c0],speed:[.8,2.6],up:.9,size:[.12,.22],life:[1.3,2],gravity:.75,drag:1.7,kind:K.leaf});
      if(i===0)fx.text(v3(c.x,c.y+b.h*.32,c.z),"完美","soul vx-perfect",{dur:1.1,rise:26,dx:-30,rot:0})}
    // #4 終結斬
    if(p.kill)finisher(c,b)}
  // 終結斬：慢動作中一道貫穿畫面的金色墨筆橫劃，命中點金＋墨雙色粒子 100 顆，地面墨暈擴散
  function finisher(c,b){const cam=eng.camera,d=cam.getWorldPosition(v3()).distanceTo(c),vw=2*d*Math.tan(cam.fov*Math.PI/360)*eng.aspect;
    fx.brush(c,{straight:true,ang:rand(-.22,.1),size:.55,stretch:vw*.62/.55,w:.3,dur:1,draw:.2,hdr:1.5,inkOp:.88,toCam:Math.min(1.2,d*.3),bend:.05});
    eng.wait(.06).then(()=>fx.brush(c,{straight:true,ang:rand(-.15,.15)+.04,size:.3,stretch:vw*.5/.3,w:.12,dur:.7,draw:.18,hdr:1.9,ink:false,toCam:Math.min(1.3,d*.32)}));
    fx.emit({p:c,n:n(60),color:[GOLD,WHITE,0xffe7a8],speed:[2,8],size:[.06,.2],life:[.6,1.3],drag:1.3,gravity:1.5,kind:[1,K.leaf,...K.glyph]});
    fx.emitN({p:c,n:n(40),color:[INK,0x1a1418],speed:[2,7],size:[.06,.18],life:[.6,1.1],gravity:8,kind:[K.drop,K.splat]});
    fx.enso(c,{color:GOLD,r0:.4,r1:b.h*.9,dur:.7,hdr:2.2,draw:.3});
    const g=b.root.position;fx.decal(g,{color:INK,s0:.5,s1:b.h*1.7,dur:2.4,grow:.35,hold:.4,op:.82,keep:true});fx.decal(g,{color:GOLD,normal:false,s0:.4,s1:b.h*1.2,dur:1,grow:.3,hold:.1,op:.4,keep:true})}

  /* ---------- #5 彈反 ---------- */
  function parry(at,b){if(!b)return;const S=sig(b);
    fx.enso(at,{color:GOLD,r0:.2,r1:1,dur:.36,draw:.22,hdr:2});
    for(const a of [.78,-.78])fx.brush(at,{straight:true,ang:a,size:.3,stretch:2.4,w:.16,dur:.3,draw:.25,hdr:2.4,inkOp:.55,toCam:.35});
    const tip=weaponTip(b);fx.emit({p:tip,n:n(20),color:[S.main,0xffffff],speed:[3,8],size:[.04,.1],life:[.2,.45],gravity:6,kind:[1,K.star]});
    fx.streaks({p:tip,n:12,color:[S.main,0xffffff],speed:[5,12],hdr:3});fx.flash(tip,{color:S.main,size:1,dur:.16,opacity:.8})}

  /* ---------- #6 閃避翻滾（t＝到命中的秒數；翻滾在命中前 0.38 秒開始） ---------- */
  function dodge(spot,p,t=.4){const perfect=!!(p&&st.limitMs&&p.ms!=null&&p.ms<=st.limitMs*.35);
    eng.wait(Math.max(0,t-.38)).then(()=>{if(eng.dead)return;fx.afterimage(hero,{color:0x17141f,op:.55,dur:.45,grow:.03,drift:v3(0,.08,0)});
      const hp=hero.root.position,b=B(),f=b?v3().subVectors(b.root.position,hp).setY(0).normalize():v3(0,0,-1),s=v3(-f.z,0,f.x);
      for(let i=0;i<n(7);i++){const a=(i/6-.5)*2.4,q=v3(hp.x,.08,hp.z).addScaledVector(s,Math.sin(a)*.75).addScaledVector(f,-Math.cos(a)*.45);fx.emitN({p:q,n:1,color:[0x6b7078,0x8a8f98],speed:[.3,.9],flat:.25,up:.35,size:[.35,.6],life:[.4,.7],alpha:.4,drag:2,grow:.9})}});
    if(perfect)eng.wait(t).then(()=>{if(eng.dead)return;const hp=hero.root.position;for(let i=0;i<2;i++)eng.wait(i*.09).then(()=>fx.enso(hp,{ground:true,color:GOLD,r0:.4,r1:2+i*.8,dur:.55,draw:.3,hdr:1.8,op:.8}));
      fx.enso(hero.center(v3(),.55),{color:GOLD,r0:.3,r1:1.1,dur:.4,hdr:1.8,op:.6});fx.text(hero.center(v3(),1.15),"見切","soul vx-perfect",{dur:.9,rise:20,dx:0,rot:0})})}

  /* ---------- #8 硬擋／格擋 ---------- */
  function guard(at){fx.streaks({p:at,n:20,color:[0x9aa0a8,0xd8dde6,0xffffff],speed:[5,12],hdr:2.4});fx.burstRing(at,{color:0xffffff,r0:.1,r1:.9,dur:.25})}

  /* ---------- #7 玩家受擊：暗紅墨潑（非寫實血） ---------- */
  function hurt(c,k=1,p){const b=B(),away=b?v3().subVectors(hero.root.position,b.root.position).setY(.3).normalize():v3(0,.3,1);
    fx.decal(toward(c,.35),{ground:false,color:0x6a0c14,s0:.3,s1:.75+.45*k,dur:.4,grow:.1,hold:.12,op:.85});
    fx.emitN({p:c,n:n(10+8*k),color:[0x6a0c12,PAL.hurt,0x2a0608],speed:[2,5+2*k],dir:away,spread:.7,size:[.05,.13],life:[.35,.7],gravity:9,kind:[K.drop,K.splat]});
    if(k>=1.3)fx.decal(hero.root.position,{color:0x3a0a0e,s0:.4,s1:1.6,dur:1.2,op:.6})}

  /* ---------- #9 突襲預警：落點主色墨圈、眼睛紅閃、「！」 ---------- */
  function ambushWarn(){const b=B();if(!b)return;const S=sig(b),hp=hero.root.position,r=b.root.position,d=v3().subVectors(r,hp).setY(0),cur=d.length()||1;d.multiplyScalar(1/cur);
    const to=hp.clone().addScaledVector(d,Math.min(cur,1.6+b.h*.12));
    fx.decal(to,{color:INK,s0:.5,s1:b.h*.6,dur:.55,grow:.3,hold:.2,op:.75});fx.enso(to,{ground:true,color:S.main,r0:b.h*.55,r1:b.h*.4,dur:.3,draw:.6,hdr:1.8});
    const h=headPos(b);fx.flash(h,{color:WARN,size:1.3,dur:.25,opacity:.95});fx.emit({p:h,n:1,color:WARN,speed:[0,0],size:[.9,.9],life:[.22,.22],kind:K.star})}

  /* ---------- #12 延遲攻擊解鎖：武器尖端一點白光「叮」 ---------- */
  function tipDing(){const b=B();if(!b)return;const t=weaponTip(b);fx.flash(t,{color:0xffffff,size:.8,dur:.18,opacity:1});fx.emit({p:t,n:1,color:0xffffff,speed:[0,0],size:[.7,.7],life:[.2,.2],kind:K.star})}

  /* ---------- #19 弱點擊破：金色裂紋擴散 ---------- */
  function weakCrack(){const b=B();if(!b)return;const c=b.center(v3(),.55);fx.decal(toward(c,.5),{tex:"crack",ground:false,color:GOLD,normal:false,s0:.3,s1:b.h*.75,dur:.65,grow:.3,hold:.15,op:1,keep:true});
    fx.emit({p:c,n:n(16),color:[GOLD,0xffe7a8],speed:[1,3],size:[.1,.18],life:[.8,1.4],gravity:1,drag:1.5,kind:K.leaf});fx.text(v3(c.x,c.y+b.h*.25,c.z),"擊破","soul vx-break",{dur:1,rise:22,dx:30,rot:0})}

  /* ---------- #22 Boss 死亡：化為墨與金色符字上飄（約 1.6 秒），最後一點金光落到主角劍上 ---------- */
  function bossDeath(b){if(!b)return;b.glow(GOLD,1.6);const bp=b.root.position.clone(),h=b.h;let acc=0,acc2=0;
    fx.enso(b.center(v3(),.5),{color:GOLD,r0:.5,r1:h*.8,dur:.6,hdr:1.8,op:.7});
    eng.tween(1.6,(k,r)=>{const dt=eng.dt||0;acc+=dt*(lite()?30:60);acc2+=dt*(lite()?10:22);
      while(acc>=1){acc--;fx.emit({p:v3(bp.x+rand(-.3,.3)*h*.45,rand(.1,1)*h*(1-r*.45),bp.z+rand(-.3,.3)*h*.45),n:1,color:[GOLD,0xffe7a8,WHITE],speed:[.1,.4],up:rand(.8,1.7),size:[.16,.28],life:[1,1.6],gravity:-.5,drag:.5,kind:K.glyph})}
      while(acc2>=1){acc2--;fx.emitN({p:v3(bp.x+rand(-.3,.3)*h*.4,rand(.05,.9)*h*(1-r*.5),bp.z+rand(-.3,.3)*h*.4),n:1,color:[INK,0x1a1418],speed:[.1,.3],up:rand(.5,1.1),size:[.4,.8],life:[.8,1.3],alpha:.4,grow:.8,drag:.6,kind:[0,K.dab]})}},ease.lin)
      .then(()=>{if(eng.dead)return;const from=v3(bp.x,h*.55,bp.z),o=fx.orb(from,{color:GOLD,size:.45,opacity:1}),mid=v3();
        return eng.tween(.5,(k,r)=>{const to=weaponTip(hero);mid.lerpVectors(from,to,.5).y+=1.2;const q=v3().lerpVectors(v3().lerpVectors(from,mid,k),v3().lerpVectors(mid,to,k),k);o.sprite.position.copy(q);
          fx.emit({p:q,n:1,color:[GOLD,WHITE],speed:[.05,.2],size:[.06,.1],life:[.25,.4]})},ease.io).then(()=>{const t=weaponTip(hero);o.remove();fx.flash(t,{color:GOLD,size:1.3,dur:.3,opacity:1});fx.enso(t,{color:GOLD,r0:.15,r1:.7,dur:.35,hdr:2});hero.flash(GOLD,.5);
          fx.emit({p:t,n:n(14),color:[GOLD,WHITE],speed:[.5,2],size:[.04,.09],life:[.3,.6],kind:1})})})}

  /* ---------- #23 喝藥：淡綠＋金螺旋上升 ---------- */
  function drinkSpiral(){const hp=hero.root.position.clone();let acc=0;eng.tween(.6,(k,r)=>{acc+=(eng.dt||0)*60;while(acc>=1){acc--;const a=r*14+Math.random()*.4;for(const s of [0,Math.PI])fx.emit({p:v3(hp.x+Math.sin(a+s)*.45,.1+r*1.9,hp.z+Math.cos(a+s)*.45),n:1,color:s?[GOLD,0xffe7a8]:[0xbfffd0,0x9fe8b0],speed:[.05,.2],up:.4,size:[.05,.1],life:[.4,.7],gravity:-.2})}},ease.lin)}

  /* ---------- #24 場地環境粒子（裝飾：低效能時不發） ---------- */
  function ambient(arena){if(st.amb){st.amb();st.amb=null}let acc=0;
    const E={
      gate_ruins:{rate:3,f:()=>fx.emitN({p:v3(rand(-8,8),rand(3,5.5),rand(-8,5)),n:1,color:[0x9a9a96,0x6a6a66],speed:[.05,.2],up:-.35,size:[.05,.09],life:[5,7],alpha:.7,drag:.2,kind:K.ash,deco:true})},
      cathedral_roof:{rate:3,f:()=>fx.emitN({p:v3(rand(-7,7),rand(.1,2.5),rand(-7,5)),n:1,color:[0x8a7a68,0x6a6258],speed:[.05,.2],up:.08,size:[.04,.08],life:[3,5],alpha:.6,drag:.3,deco:true})},
      execution_yard:{rate:1.6,f:()=>fx.emitN({p:v3(rand(-8,8),rand(.1,.6),rand(-8,5)),n:1,color:[INK,0x1a1024],speed:[.05,.25],up:.05,flat:.2,size:[1.4,2.4],life:[3,4.5],alpha:.22,grow:.6,drag:.3,deco:true})},
      throne_of_words:{rate:1.4,f:()=>{fx.emitN({p:v3(rand(-8,8),rand(.5,4),rand(-8,5)),n:1,color:[0xd8c8a0,0xb89a70],speed:[.1,.3],up:.12,size:[.2,.3],life:[4,6],alpha:.85,drag:.2,kind:K.page,deco:true});
        if(Math.random()<.35)fx.emit({p:v3(rand(-6,6),rand(.5,3),rand(-6,4)),n:1,color:[0xff6a4a,GOLD],speed:[.05,.2],up:.2,size:[.14,.22],life:[2,3],gravity:-.1,kind:K.glyph,deco:true})}},
    }[arena];if(!E)return;
    const off=eng.onUpdate(dt=>{acc+=dt*E.rate;while(acc>=1){acc--;E.f()}},61);st.amb=off}

  /* ---------- 包住場景的事件處理器 ---------- */
  function wrap(H){const W=(name,before,after)=>{const f=H[name];if(typeof f!=="function")return;
      H[name]=async function(p){if(before){try{before(p||{})}catch(e){console.warn("[vfx2] "+name,e)}}const r=await f.call(this,p);if(after){try{after(p||{})}catch(e){console.warn("[vfx2] "+name,e)}}return r}};
    W("skill",p=>{st.perfect=!!p.perfect;setTrail()});
    W("hit",p=>{fx.st2.nextSlash=slashStyle(p)},()=>{fx.st2.nextSlash=null});
    W("telegraph",p=>{bfx.setAtk(p);st.limitMs=p.limitMs||0});
    W("knockdown",()=>bfx.setAtk({kind:"dash"}));
    W("ambush",()=>{bfx.setAtk({kind:"ambush"});ambushWarn()});
    W("delayRelease",()=>tipDing());
    W("weakBreak",()=>weakCrack());
    W("drink",()=>{eng.wait(.32).then(drinkSpiral)});
    W("bossEnter",p=>{st.perfect=false;ambient(p.boss&&p.boss.arena)});
    if(typeof window!=="undefined"&&window.__v3test)window.__vfx2={st,H,eng,fx,bfx,hero,boss:B,api};
    return H}

  const api={hitBoss,finisher,parry,dodge,guard,hurt,ambushWarn,tipDing,weakCrack,bossDeath,drinkSpiral,ambient,wrap,st};
  return api}
