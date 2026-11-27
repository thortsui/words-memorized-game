// 魂系 Boss 的浮誇演出：蓄力（地上符紋圈、光柱、能量往武器聚、身體壓低再拉長）、
// 出手命中（筆刷刀光、地面衝擊波、碎屑、煙塵、畫面閃光）、各 Boss 的招牌特效、第二階段起的常駐氣場。
// 只處理畫面，不碰規則。品質降到 low、vfx2 判定掉幀（eng.fxLow）或「減少動態效果」時自動減量。
//
// v2（特效）：「墨與鏽」——Boss 的力量＝墨＋主色（design.md §4）。招牌特效依招式種類分開（telegraph 時由 vfx2 呼叫 setAtk 記下）：
//   sentinel   鏽戟橫掃（一般）／根鬚纏擊（延遲、必殺、連擊收尾）／盾牌衝撞（突進、突襲）
//   gargoyle   狂亂爪擊（一般、連擊）／俯衝利爪（突進、突襲）／碎石吐息（延遲、必殺）
//   priest     霜槍突刺（一般、連擊）／冰面滑襲（突進、突襲）／霜環（延遲）／冰棺降臨（必殺）
//   executioner 斷頭斧斬（一般、延遲）／影步突進（突進、突襲）／影分身處刑（必殺、連擊收尾）／交叉斬（連擊中段）
//   devourer   噬語巨劍（一般、連擊中段）／詞語風暴（延遲、連擊收尾）／終焉之言（必殺）
import * as THREE from 'three';
import { ease, lerp, rand } from './engine.js';

const v3=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
const INK=0x0b0a0f,GOLD=0xffd27a,WARN=0xff2a1a;

// 各 Boss 的配色：主色（招牌特效，design.md §2）、副色、碎屑（被打中時的材質碎屑也用這組）
export const SIG={
  sentinel:{main:0x7dffb0,alt:0xc0622a,debris:[0x6b3a22,0x8a5a30,0x2f4a2a]},     // 鏽與根鬚
  gargoyle:{main:0xff8a3a,alt:0xd8dde6,debris:[0x5d5a57,0x7a7672,0x3e3c3a]},     // 風化石
  priest:{main:0x8fe3ff,alt:0xffffff,debris:[0xbfe9ff,0xffffff,0x7fb8d8]},       // 冰
  executioner:{main:0xb07aff,alt:0x2a0a3a,debris:[0x0b0a0f,0x2a1a3a,0x4a2a6a]},  // 墨影
  devourer:{main:0xff3a2a,alt:0x0b0a0f,debris:[0x2a0a0a,0x5a1a1a,0x1a0a1a]},     // 墨與被吞掉的書頁
};

/* ---------- 骨架上的特效錨點（快取在 actor 上） ---------- */
function findNode(a,res){if(!a||!a.content)return null;let hit=null;for(const re of res){a.content.traverse(o=>{if(!hit&&re.test(o.name))hit=o});if(hit)return hit}return null}
// 武器尖端：Tip_Weapon 空物件 → 武器骨（沿骨頭方向延伸）→ 右手；都沒有就用胸口前方
export function weaponTip(a,out=v3()){if(!a)return out;if(a._vtipFor!==a.content){a._vtipFor=a.content;a._vtip=findNode(a,[/^Tip_Weapon/i]);a._vtipK="tip";
    if(!a._vtip){a._vtip=findNode(a,[/^(Weapon|Sword|Staff|Axe)$/i]);a._vtipK="bone"}if(!a._vtip){a._vtip=findNode(a,[/^Hand\.?R$/i]);a._vtipK="hand"}}
  const n=a._vtip;if(!n||a.isStandin)return a.center(out,.7).add(v3(Math.sin(a.root.rotation.y),0,Math.cos(a.root.rotation.y)).multiplyScalar(a.h*.25));
  n.updateWorldMatrix(true,false);if(a._vtipK==="bone"){const ws=n.getWorldScale(v3());return n.localToWorld(out.set(0,a.h*.3/Math.max(1e-4,ws.y),0))}return n.getWorldPosition(out)}
// 頭（眼睛的位置）：Head 骨稍微往前
export function headPos(a,out=v3()){if(!a)return out;if(a._vheadFor!==a.content){a._vheadFor=a.content;a._vhead=a.isStandin?null:findNode(a,[/^Head$/i,/Head/i])}
  if(a._vhead){a._vhead.updateWorldMatrix(true,false);a._vhead.getWorldPosition(out)}else a.center(out,.88);
  return out.add(v3(Math.sin(a.root.rotation.y),0,Math.cos(a.root.rotation.y)).multiplyScalar(a.h*.06))}

export function createBossFx({eng,fx,scene,dust}){
  const lite=()=>eng.rm||eng.quality==="low"||eng.fxLow;
  const n=x=>Math.max(1,Math.round(x*(lite()?.45:1)));
  const sig=b=>SIG[b&&b.data&&b.data.id]||SIG.sentinel;
  let atk={kind:"single"};
  const cam=()=>eng.camera.getWorldPosition(v3());
  // 兩個世界座標點在畫面上連線的角度（直線筆刷的方向）
  const pa=v3(),pb=v3();
  const screenAng=(a,b)=>{pa.copy(a).project(eng.camera);pb.copy(b).project(eng.camera);return Math.atan2((pb.y-pa.y),(pb.x-pa.x)*eng.aspect)};
  // 直線一筆：從 a 畫到 b（面向鏡頭），size＝半寬的基準
  const line=(a,b,o={})=>{const mid=v3().lerpVectors(a,b,.5),L=a.distanceTo(b),size=o.size||.4;return fx.brush(mid,{straight:true,ang:screenAng(a,b),size,stretch:L/2/size,toCam:.3,w:.3,...o})};

  /* ---------- 蓄力 ---------- */
  // 回傳 stop()：出手（或被打斷）時呼叫，收掉符紋圈與光柱
  // 一般：腳下細紅圓相、紅色筆觸粒子往武器聚；必殺：大型墨紅符紋圈逐筆畫出、Boss 背後主色光柱＋紅光柱
  function charge(b,{T=.7,danger=false,dash=false}={}){if(!b)return()=>{};const S=sig(b),p=b.root.position,h=b.h;
    const seal=danger?fx.seal(p,{color:WARN,r:h*1.05,T:T*.9,spin:.35,hdr:1.8}):null;
    if(!danger)fx.enso(p,{ground:true,color:WARN,r0:h*.72,r1:h*.55,dur:T+.15,draw:.7,hdr:1.3,op:.75});
    // 身體先壓低（預備動作）：pose 的縮放，出手時再拉長回彈
    const P=b.pose.scale,s0=b._s||1;if(!eng.rm)eng.to(P,{x:1.07*s0,y:.9*s0,z:1.07*s0},T*.8,ease.out);
    let alive=true,acc=0;const tip=v3();
    const off=eng.onUpdate(dt=>{if(!alive||!b.root.visible)return;acc+=dt;if(seal)seal.set(p);
      // 能量往武器聚：紅色筆觸從外圈飛向武器尖端
      if(acc>(lite()?.06:.03)){acc=0;weaponTip(b,tip);const a=rand(0,6.28),R=h*rand(.6,1.1),from=v3(tip.x+Math.sin(a)*R,tip.y+rand(-.6,.8)*h*.4,tip.z+Math.cos(a)*R);
        fx.emit({p:from,n:1,color:[WARN,danger?S.main:0xff7a4a,0xffffff],speed:[R*2.2,R*2.8],dir:[tip.x-from.x,tip.y-from.y,tip.z-from.z],spread:.04,size:[.12,.24],life:[.3,.4],kind:fx.K.dab})}},60);
    if(!dash)fx.pillar(p,{color:danger?WARN:S.main,r:h*(danger?.5:.22),h:h*(danger?4:2.2),dur:T+.25});
    if(danger&&eng._vfxHero){const hp=eng._vfxHero.root.position,d=v3().subVectors(p,hp).setY(0).normalize(),q=p.clone().addScaledVector(d,h*.55);fx.pillar(q,{color:S.main,r:h*.8,h:h*5,dur:T+.4})}
    fx.ring(p,{color:danger?WARN:S.main,r0:h*1.6,r1:.2,dur:T,opacity:.6}); // 往內收的環＝在吸力
    if(danger){for(let i=0;i<n(2);i++)eng.wait(i*T/2).then(()=>{if(!alive)return;const c=b.center(v3(),.8),a=rand(0,6.28);fx.bolt(v3(c.x+Math.sin(a)*h,c.y+h*1.2,c.z+Math.cos(a)*h),c,{color:0xff5a3a,width:.08,dur:.16,jag:.5})})}
    return()=>{if(!alive)return;alive=false;off();if(seal)seal.remove(.35)}}

  /* ---------- 出手瞬間 ---------- */
  // 身體拉長＋往前探（伸展），命中後彈回
  function lunge(b,t){if(!b||eng.rm)return;const P=b.pose.scale,s0=b._s||1;eng.to(P,{x:.94*s0,y:1.1*s0,z:.94*s0},Math.max(.06,t*.6),ease.out).then(()=>eng.to(P,{x:s0,y:s0,z:s0},.45,ease.elastic))}
  // 被打斷（彈反、突擊）時把身體縮放收回原狀
  function settle(b){if(!b)return;const s0=b._s||1;eng.to(b.pose.scale,{x:s0,y:s0,z:s0},.25,ease.out)}
  // 突進的殘光：沿衝刺路徑留下一串光點；行刑者另留 2–3 個紫色墨影殘像
  function streak(b,from,to){if(!b)return;const S=sig(b),c=b.h*.5,id=b.data&&b.data.id;for(let i=0;i<n(12);i++){const k=i/11,p=v3().lerpVectors(from,to,k);p.y=c*rand(.4,1.4);
      fx.emit({p,n:1,color:[S.main,0xffffff],speed:[.1,.4],size:[.12,.28],life:[.25,.45]})}
    if(id==="executioner")shadowStep(b,from,to);
    else if(id==="gargoyle")diveTrails(b,from,to);
    else if(id==="priest")frostTrail(from,to)}

  /* ---------- 命中（不管玩家有沒有閃掉都會播：刀落地） ---------- */
  // at：命中點；k：力道（連擊中段 .6、一般 1、連擊／延遲／突進 1.3、必殺 1.8）；dodged：玩家閃掉（衝擊打在地上）
  function impact(b,at,{k=1,dodged=false,from}={}){if(!b)return;const S=sig(b),g=v3(at.x,.05,at.z),id=b.data&&b.data.id;
    // 筆刷刀光：外層主色（帶墨底）、內層白芯，角度錯開
    const ang=rand(-.9,.9);fx.slash(at,{color:S.main,size:1.15+.45*k,ang,dur:.32,sweep:1.8});fx.slash(at,{color:0xffffff,size:.95+.3*k,ang:ang+.08,dur:.22,sweep:1.8});
    // 地面：主色圓相＋細白環＋煙塵＋碎屑；重擊加墨暈
    fx.enso(g,{ground:true,color:S.main,r0:.4,r1:1.3+1.3*k,dur:.5,hdr:1.4,op:.85});fx.ring(g,{color:0xffffff,r1:.8+1*k,dur:.3,opacity:.5});
    if(k>=1.3)fx.decal(g,{color:INK,s0:.4,s1:1.4+.6*k,dur:1.2,op:.7});
    dust(g,n(6+6*k),[0x5a5f68,0x7a7f88,0x4a4038]);
    fx.emitN({p:v3(g.x,.15,g.z),n:n(8+8*k),color:S.debris,speed:[2,4+3*k],up:3,size:[.07,.16],life:[.5,.9],gravity:14,alpha:1,drag:.6});
    fx.flash(at,{color:S.main,size:1.6+1.2*k,dur:.22,opacity:.7});
    if(k>=1.3){fx.pulseVig("white",Math.min(.15,.06+.04*k),.22)}
    if(dodged)fx.emit({p:v3(g.x,.3,g.z),n:n(12),color:[S.main,0xffffff],speed:[3,7],flat:.15,up:.6,size:[.04,.09],life:[.2,.45],gravity:6});
    // 招牌特效（依 telegraph 記下的招式種類）
    const K=atk.kind||"single",heavy=K==="danger",rush=K==="dash"||K==="ambush",combo=K==="combo",fin=combo&&!atk.chain,del=K==="delayed";
    try{
      if(id==="sentinel"){if(rush)shieldBash(g,from,k);else if(heavy||del||fin)roots(g,from,k);else rustSweep(at,g,k)}
      else if(id==="gargoyle"){if(rush)gust(g,k);else if(heavy||del)breath(b,at,k);else claws(at,g,k)}
      else if(id==="priest"){if(heavy)iceCoffin(at,k);else if(del)frostRing(g,k);else if(!rush)frostThrust(b,at,k);frost(g,k)}
      else if(id==="executioner"){if(heavy||fin)shadowClones(b,at,from,k);else if(rush)shadowX(at,k);else if(combo)shadowX(at,k);else guillotine(at,g,from,k)}
      else if(id==="devourer"){if(heavy)finalWord(b,at,k);else if(del||fin)wordStorm(b,at,k);else doubleSlash(at,g,k)}
    }catch(e){console.warn("[bossfx] 招牌特效",e)}}

  /* ---- 守門騎士（鏽橙＋苔綠） ---- */
  // 鏽戟橫掃：橫向的鏽色筆刷弧＋鏽屑
  function rustSweep(at,g,k){fx.brush(at,{color:0xc0622a,core:0xffc080,size:2.2+.4*k,ang:-Math.PI/2+rand(-.25,.25),sweep:1.7,w:.32,dur:.42,hdr:1.5,inkOp:.7});
    fx.emitN({p:at,n:n(16),color:[0x6b3a22,0x8a4a22,0x4a2a18],speed:[2,6],up:1.5,size:[.05,.12],life:[.5,.9],gravity:11,drag:.4,kind:[2,fx.K.splat]});
    fx.emit({p:at,n:n(6),color:[0x7dffb0,0xb8ffd0],speed:[.3,1],up:.6,size:[.05,.1],life:[.9,1.5],gravity:-.3,drag:.8})}
  // 根鬚纏擊：一排 3–5 根樹根朝攻擊方向破土（間隔 0.05 秒）＋苔綠孢子、木屑、鏽色火星
  function roots(g,from,k){const d=from?v3().subVectors(g,from).setY(0).normalize():v3(0,0,1);const N=Math.min(5,3+Math.round(1.2*k));
    for(let i=0;i<N;i++)eng.wait(i*.05).then(()=>{const p=g.clone().addScaledVector(d,(i-1)*.55).add(v3(rand(-.25,.25),0,rand(-.25,.25))),hgt=rand(.9,1.5)*(.8+.3*k);
      const m=new THREE.Mesh(fx.G.cone,new THREE.MeshStandardMaterial({color:0x3a2a1a,roughness:.9,emissive:0x1a4a20,emissiveIntensity:.7}));m.position.copy(p);m.rotation.set(rand(-.35,.35),rand(0,6),rand(-.35,.35));
      fx.temp(m,.8,(kk,r)=>{const s=r<.18?ease.back(r/.18):r>.7?1-(r-.7)/.3:1;m.scale.set(.24*s,Math.max(.01,hgt*s),.24*s);m.position.y=m.scale.y*.45});
      fx.decal(p,{color:INK,s0:.2,s1:.7,dur:.9,op:.6});
      fx.emitN({p:v3(p.x,.2,p.z),n:n(5),color:[0x5a3a20,0x7a5030],speed:[1,3],up:2.4,size:[.04,.09],life:[.4,.7],gravity:12,kind:2});
      fx.emit({p:v3(p.x,.3,p.z),n:n(4),color:[0x7dffb0,0xc0ffd8],speed:[.2,.8],up:.8,size:[.05,.1],life:[1,1.6],gravity:-.35,drag:.6})})}
  // 盾牌衝撞：前方木屑＋一道塵牆
  function shieldBash(g,from,k){const d=from?v3().subVectors(g,from).setY(0).normalize():v3(0,0,1),s=v3(-d.z,0,d.x);
    fx.emitN({p:v3(g.x,.6,g.z),n:n(20),color:[0x5a3a20,0x7a5030,0x3a2614],speed:[3,7],dir:[d.x,.5,d.z],spread:.6,size:[.06,.14],life:[.5,.9],gravity:12,drag:.4,kind:[2,fx.K.dab]});
    for(let i=0;i<n(7);i++){const p=g.clone().addScaledVector(d,.5).addScaledVector(s,(i-3)*.45);fx.emitN({p:v3(p.x,.3,p.z),n:2,color:[0x6b6258,0x8a8070],speed:[.4,1.2],dir:[d.x,.6,d.z],spread:.5,size:[.6,1.1],life:[.6,1],alpha:.45,drag:1.8,grow:1.2})}
    fx.enso(g,{ground:true,color:0x7dffb0,r0:.3,r1:2.2,dur:.5,op:.6})}

  /* ---- 石像鬼（熔橘＋石灰） ---- */
  // 狂亂爪擊：三道平行的爪痕（直線筆刷，間隔 40ms）＋石屑
  function claws(at,g,k){const a=-1.05+rand(-.25,.25),c=eng.camera,R=v3(1,0,0).applyQuaternion(c.quaternion),U=v3(0,1,0).applyQuaternion(c.quaternion),perp=v3().addScaledVector(R,Math.cos(a+Math.PI/2)).addScaledVector(U,Math.sin(a+Math.PI/2));
    for(let i=0;i<3;i++)eng.wait(i*.04).then(()=>{const p=at.clone().addScaledVector(perp,(i-1)*.38);fx.brush(p,{straight:true,ang:a,size:.42,stretch:2.6,w:.22,color:0xff8a3a,core:0xffe0a0,dur:.34,hdr:1.8,toCam:.4})});
    fx.emitN({p:at,n:n(12),color:[0x7a7672,0x9a9690,0x5d5a57],speed:[2,5],up:1.5,size:[.06,.14],life:[.5,.9],gravity:12,kind:2})}
  // 俯衝利爪：翼尖兩道橘色殘痕（沿衝刺路徑）
  function diveTrails(b,from,to){const d=v3().subVectors(to,from).setY(0),L=d.length();if(L<.3)return;d.multiplyScalar(1/L);const s=v3(-d.z,0,d.x);
    for(const sg of [-1,1]){const a=from.clone().addScaledVector(s,sg*b.h*.55).setY(b.h*.75),e=to.clone().addScaledVector(s,sg*b.h*.35).setY(b.h*.45);
      line(a,e,{size:.3,w:.22,color:0xff8a3a,core:0xffd090,dur:.45,hdr:1.7,inkOp:.45});
      for(let i=0;i<n(8);i++)fx.emit({p:v3().lerpVectors(a,e,i/7),n:1,color:[0xff8a3a,0xffc070],speed:[.1,.4],size:[.08,.16],life:[.3,.5]})}}
  // 石屑＋一圈直立的風壓環（俯衝落地）
  function gust(g,k){for(let i=0;i<n(2);i++)eng.wait(i*.07).then(()=>{const m=new THREE.Mesh(fx.G.ringThin,fx.basic(0xd8dde6));m.position.set(g.x,.9,g.z);
      fx.temp(m,.45,(kk,r)=>{m.quaternion.copy(eng.camera.quaternion);m.scale.setScalar(.4+(2.4+k)*ease.out3(r));m.material.opacity=.6*(1-r)})});
    fx.emitN({p:v3(g.x,.6,g.z),n:n(14),color:[0x8a8f98,0xb0b6bf],speed:[3,6],up:1.5,size:[.08,.18],life:[.4,.8],gravity:12,drag:.4,kind:2});
    claws(v3(g.x,1,g.z),g,k*.6)}
  // 碎石吐息：從嘴噴出錐形的燒紅碎石（約 40 顆，分 4 波）＋黑煙
  function breath(b,at,k){const h0=headPos(b),d=v3().subVectors(at,h0).normalize();
    for(let i=0;i<4;i++)eng.wait(i*.07).then(()=>{const p=headPos(b);
      fx.emit({p,n:n(10),color:[0xff8a3a,0xffc070,0xff4a1a,0xfff0c0],speed:[6,10],dir:d,spread:.22,size:[.07,.16],life:[.45,.75],gravity:7,drag:.6,kind:[1,2]});
      fx.emitN({p,n:n(3),color:[0x2a2624,0x3a3430],speed:[2,4],dir:d,spread:.3,size:[.5,.9],life:[.6,1],alpha:.45,drag:1.4,grow:1.1})});
    fx.flash(h0,{color:0xff8a3a,size:1.4,dur:.3,opacity:.8});fx.decal(v3(at.x,0,at.z),{color:0x1a0c06,s0:.4,s1:1.8,dur:1.4,op:.7})}

  /* ---- 霜冠祭司（霜藍＋白） ---- */
  // 寒霧＋雪花爆散（每次命中的底）
  function frost(g,k){fx.emitN({p:v3(g.x,.3,g.z),n:n(8),color:[0xbfe9ff,0xffffff],speed:[.5,1.6],flat:.3,up:.3,size:[.5,1],life:[.7,1.2],alpha:.3,drag:1.5,grow:1});
    fx.emit({p:v3(g.x,.8,g.z),n:n(16),color:[0x8fe3ff,0xffffff],speed:[2,5+2*k],up:1,size:[.04,.1],life:[.4,.9],gravity:2,kind:[1,fx.K.star]})}
  // 霜槍突刺：沿槍線的直線冰晶刀光＋冰屑
  function frostThrust(b,at,k){const t=weaponTip(b),a=b.center(v3(),.62);const e=at.clone().addScaledVector(v3().subVectors(at,a).normalize(),.6);
    line(a.lerp(t,.3),e,{size:.32,w:.24,color:0x8fe3ff,core:0xffffff,dur:.32,hdr:1.8,inkColor:0x0b1420,inkOp:.5});
    fx.emit({p:at,n:n(14),color:[0x8fe3ff,0xffffff,0xbfe9ff],speed:[2,6],up:1,size:[.05,.12],life:[.3,.6],gravity:5,kind:1})}
  // 冰面滑襲：沿滑行路徑的地面結霜
  function frostTrail(from,to){const N=lite()?2:5;for(let i=0;i<N;i++){const p=v3().lerpVectors(from,to,(i+.5)/N);eng.wait(i*.03).then(()=>fx.decal(p,{color:0x8fe3ff,normal:false,s0:.3,s1:rand(.8,1.2),dur:1.3,op:.55}));
    fx.emitN({p:v3(p.x,.15,p.z),n:n(2),color:[0xdff3ff,0xffffff],speed:[.2,.6],flat:.3,size:[.5,.8],life:[.8,1.2],alpha:.28,drag:1.5,grow:.8})}}
  // 霜環：地面結霜圈擴散
  function frostRing(g,k){fx.enso(g,{ground:true,color:0x8fe3ff,r0:.3,r1:3.2,dur:.7,draw:.3,hdr:1.6});fx.decal(g,{color:0x8fe3ff,normal:false,s0:.5,s1:3,dur:1.2,op:.4})}
  // 冰棺降臨：四根冰柱從天而降框住主角，0.6 秒後碎裂
  function iceCoffin(at,k){const c=v3(at.x,0,at.z),cr=eng.camera.position,base=Math.atan2(cr.x-c.x,cr.z-c.z)+Math.PI/4;
    for(let i=0;i<4;i++){const a=base+i*Math.PI/2,p=v3(c.x+Math.sin(a)*.95,0,c.z+Math.cos(a)*.95);
      const g=new THREE.Group(),core=new THREE.Mesh(fx.G.box,new THREE.MeshBasicMaterial({color:0x5a8aa8,transparent:true,opacity:.38,depthWrite:false,fog:false})),glow=new THREE.Mesh(fx.G.box,fx.basic(0x8fe3ff));
      core.scale.set(.32,2.6,.32);glow.scale.set(.42,2.7,.42);g.add(core,glow);g.rotation.y=a;g.position.set(p.x,6,p.z);
      eng.wait(i*.04).then(()=>fx.temp(g,.85,(kk,r)=>{const f=Math.min(1,r/.17);g.position.y=lerp(6,1.3,ease.in(f));glow.material.opacity=r<.17?.22:.12*(1-r);core.material.opacity=r>.8?.38*(1-(r-.8)/.2):.38;
        if(r>=.17&&!g.userData.landed){g.userData.landed=1;fx.emit({p:v3(p.x,.2,p.z),n:n(8),color:[0x8fe3ff,0xffffff],speed:[1,4],up:1,size:[.05,.1],life:[.3,.6],gravity:6,kind:1})}
        if(r>=.78&&!g.userData.broke){g.userData.broke=1;fx.emit({p:v3(p.x,1.2,p.z),n:n(10),color:[0x8fe3ff,0xffffff,0xbfe9ff],speed:[2,6],size:[.06,.14],life:[.4,.8],gravity:9,kind:[1,fx.K.star],radius:.3,radiusY:1})}},ease.lin))}
    eng.wait(.66).then(()=>{fx.enso(c,{ground:true,color:0x8fe3ff,r0:.6,r1:2.6,dur:.5});fx.flash(v3(c.x,1.2,c.z),{color:0xbfe9ff,size:2.4,dur:.25,opacity:.6})})}

  /* ---- 暗影行刑者（影紫＋墨） ---- */
  // 交叉的紫黑 X 斬＋黑煙（連擊中段）
  function shadowX(at,k){fx.slash(at,{color:0xb07aff,size:2+.6*k,ang:.8,dur:.36,sweep:1.2});fx.slash(at,{color:0x7a2aff,size:2+.6*k,ang:-.8,dur:.36,sweep:1.2,flip:true});
    fx.emitN({p:at,n:n(10),color:[0x1a1024,0x2a1a3a],speed:[.6,1.8],up:.6,size:[.4,.8],life:[.6,1],alpha:.5,drag:1.4,grow:.8})}
  // 斷頭斧斬：垂直的紫墨巨刃＋地面裂痕
  function guillotine(at,g,from,k){const top=v3(at.x,at.y+1.7,at.z),bot=v3(g.x,.05,g.z);line(top,bot,{size:.5,w:.36,color:0xb07aff,core:0xf0e0ff,dur:.42,hdr:1.9,inkOp:.8});
    const d=from?v3().subVectors(g,from).setY(0).normalize():v3(0,0,1),rot=Math.atan2(d.x,d.z);
    fx.decal(g,{tex:"crack",color:INK,s0:.5,s1:2.4,dur:1.3,grow:.12,op:.85,rot});fx.decal(g,{tex:"crack",color:0xb07aff,normal:false,s0:.5,s1:2.3,dur:.8,grow:.12,op:.9,rot,keep:true});
    fx.emitN({p:v3(g.x,.3,g.z),n:n(14),color:[INK,0x1a1024],speed:[1.5,4],up:2,size:[.06,.14],life:[.5,.9],gravity:10,kind:[fx.K.drop,fx.K.splat]})}
  // 影步突進：沿路徑留 2–3 個紫色墨影殘像
  function shadowStep(b,from,to){const N=lite()?1:3;for(let i=0;i<N;i++){const t=(i+1)/(N+1),off=v3().lerpVectors(from,to,t).sub(to).setY(0);
      fx.afterimage(b,{color:0x6a3ab0,op:.5-.1*i,dur:.5+.08*i,offset:off,drift:v3(0,.15,0),additive:true})}
    for(let i=0;i<n(10);i++)fx.emitN({p:v3().lerpVectors(from,to,i/9).setY(rand(.3,b.h*.8)),n:1,color:[INK,0x2a1a3a],speed:[.2,.6],up:.4,size:[.3,.6],life:[.5,.8],alpha:.4,grow:.8,drag:1.2})}
  // 影分身處刑：左右各一個墨影分身（凍結當下姿勢）同步落斧，接著散成墨滴
  function shadowClones(b,at,from,k){const hp=at,bp=b.root.position,d=v3().subVectors(hp,bp).setY(0).normalize(),s=v3(-d.z,0,d.x);
    for(const sg of [-1,1]){const off=v3().copy(s).multiplyScalar(sg*1.7).addScaledVector(d,-.3);const ai=fx.afterimage(b,{color:0x6a3ab0,op:.55,dur:.85,offset:off,fadeIn:.12,grow:.02,additive:true});
      const cp=v3().copy(bp).add(off),front=cp.clone().addScaledVector(d,b.h*.35);
      eng.wait(.05).then(()=>line(v3(front.x,b.h*.95,front.z),v3(front.x,.05,front.z),{size:.42,w:.34,color:0xb07aff,core:0xf0e0ff,dur:.4,hdr:1.8,inkOp:.75}));
      eng.wait(.7).then(()=>{fx.emitN({p:v3(cp.x,b.h*.5,cp.z),n:n(22),color:[INK,0x1a1024,0x2a1a3a],speed:[.5,2.2],up:.8,size:[.06,.16],life:[.5,1],gravity:7,radius:b.h*.22,radiusY:2,kind:[fx.K.drop,fx.K.splat,2]});
        fx.emit({p:v3(cp.x,b.h*.5,cp.z),n:n(8),color:[0xb07aff,0x7a2aff],speed:[.3,1.2],up:.6,size:[.06,.12],life:[.4,.8],radius:b.h*.2,radiusY:2})});
      if(!ai)fx.emitN({p:v3(cp.x,b.h*.5,cp.z),n:n(10),color:[0x1a1024,0x2a1a3a],speed:[.2,.8],up:.5,size:[.6,1],life:[.6,.9],alpha:.5,grow:.8,drag:1.2})}
    guillotine(at,v3(at.x,.05,at.z),from,k)}

  /* ---- 噬語魔王（噬紅＋墨＋金） ---- */
  // 噬語巨劍：紅黑雙層刀光（一層濃墨、一層噬紅）＋原創符字從命中點噴出
  function doubleSlash(at,g,k){const a=rand(-.8,.8);fx.brush(at,{color:0x000000,inkOp:.85,w:.42,size:2.2+.4*k,ang:a-.18,sweep:1.6,dur:.42});fx.brush(at,{color:0xff3a2a,core:0xffd0a0,size:1.9+.4*k,ang:a,sweep:1.7,w:.26,dur:.36,hdr:1.9,ink:false});
    glyphBurst(at,n(10+4*k),[0xff3a2a,0xffd27a,0xff7050])}
  const glyphBurst=(p,N,color)=>fx.emit({p,n:N,color,speed:[1,3.5],up:.8,size:[.18,.3],life:[.6,1.1],drag:1.2,gravity:-.4,kind:fx.K.glyph});
  // 詞語風暴：30 片燒紅邊的書頁繞著 Boss 旋轉上升（一次 draw call），加上符字粒子
  function wordStorm(b,at,k){const N=lite()?12:30,pg=new THREE.PlaneGeometry(.28,.38),mat=new THREE.MeshBasicMaterial({map:fx.T2.page,side:THREE.DoubleSide,transparent:true,depthWrite:false,fog:false,opacity:1});
    const im=new THREE.InstancedMesh(pg,mat,N);im.frustumCulled=false;const c=b.root.position.clone(),D=new THREE.Object3D(),P=[];
    for(let i=0;i<N;i++)P.push({a:i/N*6.283+rand(-.2,.2),r:rand(1.2,2.2),y:rand(.2,b.h*.9),w:rand(2.2,3.6)*(Math.random()<.5?1:1),sp:rand(-6,6),rx:rand(0,6)});
    fx.temp(im,1.5,(kk,r)=>{for(let i=0;i<N;i++){const q=P[i],rr=q.r+r*2.6,a=q.a+r*q.w;D.position.set(c.x+Math.sin(a)*rr,q.y+r*1.4+Math.sin(r*6+i)*.2,c.z+Math.cos(a)*rr);D.rotation.set(q.rx+r*q.sp,a+Math.PI/2,r*q.sp*.6);const s=r<.1?r/.1:1;D.scale.setScalar(s);D.updateMatrix();im.setMatrixAt(i,D.matrix)}
      im.instanceMatrix.needsUpdate=true;mat.opacity=r>.75?1-(r-.75)/.25:1},ease.lin).then(()=>pg.dispose());
    glyphBurst(v3(c.x,b.h*.5,c.z),n(24),[0xff3a2a,0xffd27a]);doubleSlash(at,v3(at.x,0,at.z),k*.8)}
  // 終焉之言：地面紅字環從 Boss 擴到場邊＋全畫面墨色收縮
  function finalWord(b,at,k){const c=b.root.position.clone(),s=fx.seal(c,{color:0xff3a2a,r:1,T:.15,spin:.6,hdr:2,inkOp:.6});
    eng.tween(1.2,(kk,r)=>{s.group.scale.setScalar(2*lerp(1,9.5,ease.out3(r)))},ease.lin).then(()=>s.remove(.25));
    fx.inkVeil(.85,1.3);glyphBurst(v3(c.x,b.h*.6,c.z),n(40),[0xff3a2a,0xffd27a,0xff7050]);fx.decal(v3(at.x,0,at.z),{color:INK,s0:.6,s1:3,dur:1.6,op:.8});doubleSlash(at,v3(at.x,0,at.z),k)}

  /* ---------- 第二階段起的常駐氣場 ---------- */
  // 主色餘燼緩慢上飄（≤ 6 顆／秒）＋淡墨煙；第三階段（噬語魔王）腳下再加一圈翻湧的墨潮環。回傳 stop()
  function aura(b,phase){if(!b)return()=>{};const S=sig(b),id=b.data&&b.data.id;let acc=0,acc2=0,alive=true;const rate=Math.min(6,4+phase),tide=[];
    if(phase>=2||(id==="devourer"&&phase>=2)){for(let i=0;i<2;i++){const m=new THREE.Mesh(fx.G.plane,new THREE.MeshBasicMaterial({map:fx.T2.splat,color:INK,transparent:true,opacity:0,depthWrite:false,fog:false,polygonOffset:true,polygonOffsetFactor:-1}));
      m.rotation.x=-Math.PI/2;m.renderOrder=8;scene.add(m);tide.push(m)}}
    let el=0;const off=eng.onUpdate(dt=>{if(!alive)return;el+=dt;
      for(let i=0;i<tide.length;i++){const m=tide[i],p=b.root.position;m.visible=b.root.visible;m.position.set(p.x,.03+i*.004,p.z);m.rotation.z+=dt*(i?-.35:.25);m.scale.setScalar(b.h*(1.5+i*.45)*(1+.06*Math.sin(el*1.7+i*2)));m.material.opacity=Math.min(.75-.2*i,el*.8)}
      if(!b.root.visible)return;acc+=dt*(lite()?.5:1);acc2+=dt;
      while(acc>1/rate){acc-=1/rate;const c=b.center(v3(),rand(.1,.9)),a=rand(0,6.28),r=b.h*.25;
        fx.emit({p:v3(c.x+Math.sin(a)*r,c.y,c.z+Math.cos(a)*r),n:1,color:[S.main,0xffffff],speed:[.1,.4],up:.9,size:[.05,.11],life:[1,1.6],gravity:-.35,drag:.5})}
      if(acc2>.45){acc2=0;const c=b.center(v3(),rand(.05,.4));fx.emitN({p:c,n:1,color:[INK,0x1a1418],speed:[.1,.3],up:.5,size:[.6,1],life:[1,1.6],alpha:.28,grow:.7,drag:.6});
        if(tide.length){const p=b.root.position,a=rand(0,6.28),R=b.h*rand(.7,1.1);fx.emitN({p:v3(p.x+Math.sin(a)*R,.15,p.z+Math.cos(a)*R),n:1,color:[INK],speed:[.2,.5],up:.6,size:[.08,.16],life:[.5,.9],gravity:3,kind:fx.K.drop})}}},60);
    return()=>{alive=false;off();for(const m of tide){const o0=m.material.opacity;eng.tween(.5,k=>{m.material.opacity=o0*(1-k)}).then(()=>{scene.remove(m);m.material.dispose()})}}}

  /* ---------- 登場／變身 ---------- */
  // 咆哮衝擊波：主色圓相＋地面環＋一圈面向鏡頭的大環＋碎石
  function roarBlast(b){if(!b)return;const S=sig(b),p=b.root.position;for(let i=0;i<3;i++)eng.wait(i*.12).then(()=>fx.ring(p,{color:i?S.main:0xffffff,r1:6+i*2,dur:.7,opacity:.6}));
    fx.enso(p,{ground:true,color:S.main,r0:.8,r1:b.h*2,dur:.8,hdr:1.4,op:.8});
    fx.burstRing(b.center(v3(),.7),{color:S.main,r1:b.h*1.4,dur:.5});
    fx.emitN({p:v3(p.x,.2,p.z),n:n(24),color:S.debris,speed:[3,7],up:3,size:[.08,.2],life:[.6,1.2],gravity:12,radius:b.h*.3})}
  // 變身：身體膨脹一下（之後維持稍大）、主色光柱、墨潑、主色符字飛散（≤ 120 顆）
  // o（可省略，舊呼叫相容）：{pillar:false 不要光柱, pillarScale 光柱粗細倍率（預設 1）, pillarDur 光柱秒數（預設 1.2）, squash:false 不做身體膨脹}
  function phaseBurst(b,phase,o={}){if(!b)return;const S=sig(b),p=b.root.position,s=1+.06*phase;b._s=s;
    if(!eng.rm&&o.squash!==false){b.pose.scale.set(s*1.15,s*.85,s*1.15);eng.to(b.pose.scale,{x:s,y:s,z:s},.7,ease.elastic)}
    if(o.pillar!==false)fx.pillar(p,{color:S.main,r:b.h*.7*(o.pillarScale==null?1:o.pillarScale),h:b.h*5,dur:o.pillarDur==null?1.2:o.pillarDur});roarBlast(b);
    fx.decal(p,{color:INK,s0:1,s1:b.h*2.4,dur:2,grow:.15,hold:.5,op:.8});fx.enso(b.center(v3(),.6),{color:S.main,r0:.5,r1:b.h*1.3,dur:.6,hdr:1.8});
    fx.emit({p:b.center(v3(),.6),n:n(30),color:[S.main,0xffffff],speed:[2,6],size:[.16,.28],life:[.6,1.1],drag:1.3,kind:fx.K.glyph,radius:b.h*.2});
    fx.emitN({p:b.center(v3(),.5),n:n(20),color:[INK,0x1a1418],speed:[2,5],size:[.06,.16],life:[.5,1],gravity:8,kind:[fx.K.drop,fx.K.splat]});
    for(let i=0;i<n(3);i++)eng.wait(i*.1).then(()=>{const a=rand(0,6.28),t=v3(p.x+Math.sin(a)*b.h*.8,0,p.z+Math.cos(a)*b.h*.8);fx.bolt(v3(t.x,b.h*2.5,t.z),t,{color:i%2?0xffffff:S.main,width:.12,dur:.22,jag:.55})})}

  // 招式種類：telegraph 時由 vfx2 設定（{kind, chain, seg, segs, danger}）
  function setAtk(p){atk={kind:p&&p.kind||"single",chain:!!(p&&p.chain),seg:p&&p.seg||0,segs:p&&p.segs||1,danger:!!(p&&p.danger)};if(atk.danger)atk.kind="danger"}

  return{charge,lunge,settle,streak,impact,aura,roarBlast,phaseBurst,sig,setAtk,get atk(){return atk}};
}
