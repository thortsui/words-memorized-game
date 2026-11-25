// 程式產生的替身模型：GLB 還沒做好（或載入失敗）時使用。全部用基本形體拼出可辨識的輪廓。
// 約定與真模型相同：臉朝 +Z（所以右手在 −X）、原點在腳底。回傳 {group, parts, height}：
//   parts 是給補間動作用的關節群組（armR、armL、legL、legR、wingL、wingR、cape…，沒有就略過）
//   height 是替身自己的身高（Actor 會依目標身高等比縮放）
// 造型依 art/reference 的設定圖簡化（原創角色，不模仿任何現有遊戲）。
import * as THREE from 'three';

const PI=Math.PI;
// 材質工廠：打怪模式用卡通材質（之後由 Actor 統一轉成帶漸層的 toon），魂系用寫實的 Standard
function kit(soul){const cache={};
  const mat=(color,o={})=>{const key=color+JSON.stringify(o);if(cache[key])return cache[key];
    const m=soul?new THREE.MeshStandardMaterial({color,roughness:o.rough==null?.8:o.rough,metalness:o.metal||0,flatShading:!!o.flat})
      :new THREE.MeshToonMaterial({color});
    if(o.emissive!=null){m.emissive=new THREE.Color(o.emissive);m.emissiveIntensity=o.ei==null?1:o.ei}
    if(o.opacity!=null){m.transparent=true;m.opacity=o.opacity}
    if(o.double)m.side=THREE.DoubleSide;
    return cache[key]=m};
  const add=(parent,geo,m,p=[0,0,0],r=[0,0,0],s=[1,1,1])=>{const x=new THREE.Mesh(geo,m);x.position.set(p[0],p[1],p[2]);x.rotation.set(r[0],r[1],r[2]);if(typeof s==="number")x.scale.setScalar(s);else x.scale.set(s[0],s[1],s[2]);parent.add(x);return x};
  const grp=(parent,p=[0,0,0],r=[0,0,0])=>{const g=new THREE.Group();g.position.set(p[0],p[1],p[2]);g.rotation.set(r[0],r[1],r[2]);parent.add(g);return g};
  const sph=(r,w=14,h=10)=>new THREE.SphereGeometry(r,w,h),cyl=(a,b,h,n=12)=>new THREE.CylinderGeometry(a,b,h,n),cone=(r,h,n=8)=>new THREE.ConeGeometry(r,h,n),box=(x,y,z)=>new THREE.BoxGeometry(x,y,z);
  return{mat,add,grp,sph,cyl,cone,box};
}
// 平面多邊形（翅膀、披風碎片）
function poly(pts){const s=new THREE.Shape();pts.forEach((p,i)=>s[i?"lineTo":"moveTo"](p[0],p[1]));s.closePath();return new THREE.ShapeGeometry(s)}

/* ---------- 可愛主角：2.5 頭身、金色刺蝟頭、銀胸甲、藍衣藍披風、背後圓盾、短寬劍 ---------- */
export function heroCute(){const K=kit(false),{mat,add,grp,sph,cyl,cone,box}=K,g=new THREE.Group(),parts={};
  const skin=mat(0xffd9b0),blue=mat(0x2f7fe0),steel=mat(0xcfd6e2),brown=mat(0x8a5230),gold=mat(0xf2b632),dark=mat(0x20324f);
  for(const [k,x] of [["legL",.12],["legR",-.12]]){const l=parts[k]=grp(g,[x,.27,0]);add(l,cyl(.1,.12,.2),brown,[0,-.13,0]);add(l,sph(.12),brown,[0,-.22,.04],[0,0,0],[1,.7,1.3])}
  add(g,cyl(.17,.27,.26),blue,[0,.38,0]);                          // 裙襬
  add(g,sph(.2),steel,[0,.54,.01],[0,0,0],[1,1.05,.92]);           // 胸甲
  add(g,cyl(.2,.2,.05),brown,[0,.44,0]);                           // 腰帶
  const head=grp(g,[0,.88,0]);add(head,sph(.27,18,14),skin);
  for(const x of [.1,-.1]){add(head,sph(.05),dark,[x,-.01,.235],[0,0,0],[1,1.35,.6]);add(head,sph(.018),mat(0xffffff),[x+.015,.02,.262])}
  add(head,sph(.04),skin,[.27,-.02,0]);add(head,sph(.04),skin,[-.27,-.02,0]);
  // 刺蝟頭：頭頂與後腦的尖刺
  const spikes=[[0,.27,.05,-.25,0],[.16,.24,.02,-.1,-.6],[-.16,.24,.02,-.1,.6],[.24,.12,-.06,.2,-1.1],[-.24,.12,-.06,.2,1.1],[0,.2,-.18,.9,0],[.14,.1,-.22,1.1,-.5],[-.14,.1,-.22,1.1,.5],[.08,.24,.16,-.9,-.3],[-.08,.24,.16,-.9,.3]];
  for(const [x,y,z,rx,rz] of spikes)add(head,cone(.11,.3,6),gold,[x,y,z],[rx,0,rz]);
  add(head,sph(.265,14,10),gold,[0,.075,-.075],[0,0,0],[1,.92,1]);   // 頭髮底
  // 手臂：手自然下垂時劍指向前方
  const aR=parts.armR=grp(g,[-.25,.62,0],[-.5,0,0]);add(aR,cyl(.055,.055,.18),blue,[0,-.08,0]);add(aR,sph(.085),brown,[0,-.22,0]);
  add(aR,box(.07,.03,.46),steel,[0,-.22,.34]);add(aR,cone(.04,.1,4),steel,[0,-.22,.61],[PI/2,PI/4,0],[.9,1,.4]);add(aR,box(.2,.05,.05),gold,[0,-.22,.1]);
  const aL=parts.armL=grp(g,[.25,.62,0],[.15,0,0]);add(aL,cyl(.055,.055,.18),blue,[0,-.08,0]);add(aL,sph(.085),brown,[0,-.22,0]);
  const cape=parts.cape=grp(g,[0,.66,-.15]);cape.userData.rx=.12;add(cape,box(.42,.46,.03),blue,[0,-.23,0]);
  add(g,cyl(.21,.21,.04,16),steel,[0,.5,-.24],[PI/2,0,0]);add(g,cyl(.08,.08,.06,10),brown,[0,.5,-.25],[PI/2,0,0]);
  return{group:g,parts,height:1.28}}

/* ---------- 史萊姆（GLB 載入失敗時才會用到） ---------- */
export function slime(code){const K=kit(false),{mat,add,grp,sph,cone,cyl}=K,g=new THREE.Group();
  const col={slime_green:0x45c653,slime_ice:0x74cbff,slime_king:0xdc3030}[code]||0x45c653;
  const body=mat(col);add(g,sph(.5,20,14),body,[0,.4,0],[0,0,0],[1,.8,1]);
  for(const x of [.17,-.17]){add(g,sph(.11),mat(0xffffff),[x,.47,.39],[0,0,0],[1,1.25,.6]);add(g,sph(.06),mat(0x17202a),[x,.46,.44],[0,0,0],[1,1.3,.6])}
  add(g,sph(.07),mat(0xffffff,{opacity:.8}),[-.2,.66,.3]);
  if(code==="slime_king"){const gold=mat(0xf5c237);add(g,cyl(.24,.2,.14,10),gold,[0,.86,0]);for(let i=0;i<5;i++){const a=i/5*PI*2;add(g,cone(.06,.16,4),gold,[Math.cos(a)*.21,.99,Math.sin(a)*.21])}add(g,sph(.05),mat(0x5ad1ff),[0,.86,.23])}
  else if(code==="slime_ice"){const ice=mat(0xd6f3ff);for(const [x,z,r] of [[0,0,0],[.16,-.05,-.4],[-.15,.02,.4]])add(g,cone(.08,.3,5),ice,[x,.86,z],[0,0,r])}
  else{add(g,cyl(.015,.02,.16),mat(0x2e8b3a),[0,.86,0]);add(g,sph(.08),mat(0x7be36a),[.07,.95,0],[0,0,-.5],[1.3,.35,.8])}
  return{group:g,parts:{},height:code==="slime_king"?1.07:.95}}

/* ---------- 文法蝙蝠：圓滾滾的毛球、圓眼鏡、書頁翅膀 ---------- */
export function bat(code){const K=kit(false),{mat,add,grp,sph,cone}=K,g=new THREE.Group(),parts={};const shadow=code==="bat_shadow";
  const fur=mat(shadow?0x6a3fb8:0xf08a2c),belly=mat(shadow?0xb9a2ea:0xffd9a0),page=mat(shadow?0xcfc3ee:0xf7ecd2,{double:true}),ink=mat(shadow?0x2a1846:0x6b4a2a);
  const c=grp(g,[0,.36,0]);add(c,sph(.3,18,14),fur);add(c,sph(.2),belly,[0,-.06,.14],[0,0,0],[1,1,.7]);
  for(const x of [.17,-.17]){add(c,cone(.1,.24,5),fur,[x,.3,0],[0,0,x>0?-.35:.35]);add(c,cone(.05,.14,5),belly,[x,.29,.04],[0,0,x>0?-.35:.35])}
  for(const x of [.11,-.11]){add(c,sph(.075),mat(0xffffff),[x,.06,.25],[0,0,0],[1,1.1,.5]);add(c,sph(.04),mat(shadow?0xc01d5a:0x2a1c12),[x,.055,.28],[0,0,0],[1,1.2,.5]);
    add(c,new THREE.TorusGeometry(.095,.014,6,16),ink,[x,.06,.275])}
  add(c,cone(.02,.06,4),mat(0xffffff),[.04,-.1,.27],[PI,0,0]);add(c,cone(.02,.06,4),mat(0xffffff),[-.04,-.1,.27],[PI,0,0]);
  for(const x of [.09,-.09])add(c,sph(.05),ink,[x,-.3,.04],[0,0,0],[1,.6,1.4]);
  // 書頁翅膀：羊皮紙色的扇形，上面有幾道「文字」橫線
  const wing=poly([[0,.05],[.2,.3],[.62,.36],[.56,.1],[.6,-.12],[.38,-.08],[.3,-.24],[.16,-.12],[0,-.1]]);
  for(const [k,sg] of [["wingL",1],["wingR",-1]]){const w=parts[k]=grp(c,[.22*sg,.04,-.05]);const m=add(w,wing,page,[0,0,0],[0,sg>0?0:PI,0]);m.userData.noOutline=true;
    for(let i=0;i<3;i++)add(w,new THREE.BoxGeometry(.24,.012,.004),ink,[.34*sg,.2-i*.09,.005])}
  return{group:g,parts,height:.74}}

/* ---------- 魂系主角：鏽蝕板甲騎士、全罩頭盔、破披風、長劍 ---------- */
export function heroKnight(){const K=kit(true),{mat,add,grp,sph,cyl,cone,box}=K,g=new THREE.Group(),parts={};
  const steel=mat(0x7b8088,{rough:.45,metal:.75}),rust=mat(0x5c4a3e,{rough:.7,metal:.5}),mail=mat(0x3d4147,{rough:.6,metal:.6}),cloth=mat(0x1d2a4a,{rough:.95,double:true}),black=mat(0x08090b,{rough:1});
  for(const [k,x] of [["legL",.13],["legR",-.13]]){const l=parts[k]=grp(g,[x,.86,0]);add(l,cyl(.1,.085,.44),mail,[0,-.22,0]);add(l,sph(.1),steel,[0,-.44,.02]);add(l,cyl(.09,.1,.36),steel,[0,-.64,0]);add(l,box(.15,.09,.3),rust,[0,-.815,.05])}
  add(g,cyl(.24,.3,.3,10),mail,[0,.9,0]);                                   // 鎖子甲裙
  add(g,cyl(.27,.22,.5,10),steel,[0,1.22,0]);add(g,sph(.25,12,8),steel,[0,1.36,.03],[0,0,0],[1,.8,.85]);add(g,cyl(.25,.25,.07,10),rust,[0,.99,0]);
  for(const x of [.31,-.31])add(g,sph(.14,10,8),rust,[x,1.44,0],[0,0,0],[1,.85,1]);
  const head=grp(g,[0,1.66,0]);add(head,sph(.15,12,10),steel,[0,.02,0],[0,0,0],[1,1.15,1.05]);add(head,cyl(.155,.165,.12,10),steel,[0,-.07,0]);
  add(head,box(.2,.025,.05),black,[0,.02,.135]);add(head,box(.02,.12,.04),black,[0,-.04,.15]);add(head,box(.03,.16,.2),rust,[0,.15,-.02]);
  const aR=parts.armR=grp(g,[-.34,1.42,0],[-.45,0,0]);add(aR,cyl(.075,.065,.34),mail,[0,-.17,0]);add(aR,cyl(.075,.065,.3),steel,[0,-.48,0]);add(aR,sph(.08),rust,[0,-.66,0]);
  add(aR,box(.065,.022,1.05),steel,[0,-.66,.68]);add(aR,box(.3,.04,.05),rust,[0,-.66,.14]);add(aR,cyl(.025,.025,.2),black,[0,-.66,.02],[PI/2,0,0]);
  const aL=parts.armL=grp(g,[.34,1.42,0],[.1,0,0]);add(aL,cyl(.075,.065,.34),mail,[0,-.17,0]);add(aL,cyl(.075,.065,.3),steel,[0,-.48,0]);add(aL,sph(.08),rust,[0,-.66,0]);
  // 破披風：三片長短不一的布條
  const cape=parts.cape=grp(g,[0,1.46,-.2]);cape.userData.rx=.1;for(const [x,l] of [[-.17,.95],[0,1.1],[.17,.8]])add(cape,box(.17,l,.02),cloth,[x,-l/2,0]);
  return{group:g,parts,height:1.86}}

/* ---------- Boss 共用骨架 ---------- */
// c: {h 身高, w 寬度倍率, armor, trim, skin, eye 發光色, robe（長袍，沒有腿）, hunch 駝背角度}
function bossBase(K,c){const {mat,add,grp,sph,cyl,box}=K,g=new THREE.Group(),parts={},w=c.w||1;
  const armor=mat(c.armor,{rough:c.rough==null?.6:c.rough,metal:c.metal==null?.6:c.metal,flat:c.flat}),trim=mat(c.trim,{rough:.5,metal:.7,flat:c.flat});
  if(c.robe){add(g,cyl(.3*w,.72*w,1.5,12),mat(c.robe,{rough:.9}),[0,.75,0])}
  else for(const [k,x] of [["legL",.2*w],["legR",-.2*w]]){const l=parts[k]=grp(g,[x,1.0,0]);add(l,cyl(.15*w,.12*w,.5,8),armor,[0,-.25,0]);add(l,sph(.14*w,8,6),trim,[0,-.5,.03]);add(l,cyl(.13*w,.15*w,.42,8),armor,[0,-.74,0]);add(l,box(.24*w,.12,.42*w),trim,[0,-.94,.08])}
  const torso=grp(g,[0,1.0,0],[c.hunch||0,0,0]);parts.torso=torso;
  add(torso,cyl(.42*w,.3*w,.75,10),armor,[0,.42,0]);add(torso,sph(.4*w,12,8),armor,[0,.72,.04],[0,0,0],[1,.75,.85]);add(torso,cyl(.33*w,.36*w,.14,10),trim,[0,.04,0]);
  for(const x of [.5*w,-.5*w])add(torso,sph(.21*w,10,8),trim,[x,.84,0],[0,0,0],[1,.8,1]);
  const head=grp(torso,[0,1.12,.06]);parts.head=head;
  const eye=mat(0x111111,{emissive:c.eye,ei:2.2});for(const x of [.065,-.065])add(head,sph(.028,8,6),eye,[x,.02,.15]);
  const aR=parts.armR=grp(torso,[-.56*w,.82,0],[-.4,0,0]);add(aR,cyl(.11*w,.09*w,.5,8),armor,[0,-.25,0]);add(aR,cyl(.1*w,.085*w,.46,8),trim,[0,-.72,0]);add(aR,sph(.11*w,8,6),armor,[0,-.98,0]);
  const aL=parts.armL=grp(torso,[.56*w,.82,0],[.12,0,0]);add(aL,cyl(.11*w,.09*w,.5,8),armor,[0,-.25,0]);add(aL,cyl(.1*w,.085*w,.46,8),trim,[0,-.72,0]);add(aL,sph(.11*w,8,6),armor,[0,-.98,0]);
  return{g,parts,torso,head,aR,aL,armor,trim,hand:-.98}}

// Boss 1 腐朽守門騎士：樹根與青苔纏繞的鏽甲、骷髏臉、長戟、背後破塔盾
function sentinel(){const K=kit(true),{mat,add,grp,sph,cyl,cone,box}=K;const b=bossBase(K,{armor:0x54503f,trim:0x6b4a35,eye:0x9dff7a,rough:.8,metal:.45});
  const bone=mat(0xcfc7ad,{rough:.9}),moss=mat(0x3f5a2c,{rough:1}),root=mat(0x33261b,{rough:1}),iron=mat(0x4a4d52,{rough:.5,metal:.8});
  add(b.head,sph(.17,10,8),bone,[0,.04,0],[0,0,0],[1,1.1,1]);add(b.head,box(.16,.1,.12),bone,[0,-.1,.07]);add(b.head,cyl(.19,.2,.12,10),iron,[0,.14,0]);add(b.head,cone(.19,.16,10),iron,[0,.28,0]);
  for(const x of [.065,-.065])add(b.head,sph(.045,8,6),mat(0x050505),[x,.03,.125]);
  add(b.aR,cyl(.035,.035,2.9,6),root,[0,b.hand,.5],[PI/2,0,0]);add(b.aR,box(.03,.5,.34),iron,[0,b.hand-.08,1.6]);add(b.aR,cone(.06,.5,4),iron,[0,b.hand,2.15],[PI/2,0,0]);
  add(b.torso,box(.9,1.3,.08),iron,[0,.45,-.42],[.08,0,.06]);add(b.torso,box(.3,.4,.09),mat(0x0b0b0b),[.2,.75,-.425],[0,0,.3]);
  for(const [x,y,z,r] of [[.3,.5,.3,.6],[-.25,.25,.33,-.5],[.1,.8,-.3,1.2]])add(b.torso,new THREE.TorusGeometry(.42,.035,5,14,PI*1.2),root,[x*.2,y,0],[PI/2+r*.3,r,0]);
  for(const [x,y,z] of [[.3,.95,.2],[-.45,.9,.05],[.1,.2,.36],[-.2,.55,.34]])add(b.torso,sph(.13,6,5),moss,[x,y,z],[0,0,0],[1.2,.5,1]);
  return{group:b.g,parts:b.parts,height:2.55}}

// Boss 2 教堂石像鬼：風化石灰岩、石翼、鎚頭尾、裂縫透橘光
function gargoyle(){const K=kit(true),{mat,add,grp,sph,cyl,cone,box}=K;const b=bossBase(K,{armor:0x8a857a,trim:0x6f6a60,eye:0xff8a2a,rough:.95,metal:0,flat:true,hunch:.38,w:1.1});
  const stone=b.armor,lava=mat(0x221008,{emissive:0xff6a14,ei:1.8}),wingM=mat(0x77726a,{rough:.95,flat:true,double:true});
  add(b.head,sph(.2,7,5),stone,[0,.03,0],[0,0,0],[1,.95,1.15]);add(b.head,box(.18,.1,.2),stone,[0,-.09,.14]);
  for(const x of [.13,-.13]){add(b.head,cone(.055,.34,5),b.trim,[x,.24,-.04],[-.4,0,x>0?-.35:.35]);add(b.head,cone(.07,.2,4),stone,[x*1.5,.05,-.02],[0,0,x>0?-1.2:1.2])}
  for(const [x,y,r] of [[.12,.5,.5],[-.16,.3,-.4],[.02,.7,1.4],[-.05,.15,.2]])add(b.torso,box(.03,.3,.03),lava,[x,y,.34],[0,0,r]);
  const wing=poly([[0,0],[.5,.9],[1.5,1.2],[1.25,.5],[1.4,-.2],[.9,0],[.75,-.6],[.4,-.2],[0,-.5]]);
  for(const [k,sg] of [["wingL",1],["wingR",-1]]){const w=b.parts[k]=grp(b.torso,[.3*sg,.8,-.3],[.1,-.5*sg,0]);w.userData.flap=.16;add(w,wing,wingM,[0,0,0],[0,sg>0?0:PI,0]);add(w,cyl(.05,.03,1.5,5),b.trim,[.72*sg,.56,0],[0,0,-.9*sg])}
  const tail=grp(b.g,[0,.95,-.3],[-.9,0,0]);add(tail,cyl(.1,.06,1.1,6),stone,[0,-.55,0]);add(tail,box(.34,.22,.22),b.trim,[0,-1.15,0]);
  for(const p of [b.aR,b.aL])for(const x of [-.06,0,.06])add(p,cone(.03,.2,4),b.trim,[x,b.hand-.14,.05],[PI,0,0]);
  return{group:b.g,parts:b.parts,height:2.5}}

// Boss 3 霜冠祭司：結冰祭袍、冰晶王冠、無口銀面具、提燈權杖
function priest(){const K=kit(true),{mat,add,grp,sph,cyl,cone,box}=K;const b=bossBase(K,{armor:0x8fa6b8,trim:0xc9d8e4,eye:0x8fe9ff,robe:0x6f8798,rough:.5,metal:.2,w:.82});
  const ice=mat(0xbfefff,{emissive:0x3fbfff,ei:.7,rough:.15,flat:true}),silver=mat(0xd9dde2,{rough:.25,metal:.9}),wood=mat(0x2c2a30,{rough:.8});
  add(b.head,sph(.17,12,10),mat(0x56687a,{rough:.9}),[0,.04,-.03],[0,0,0],[1,1.2,1]);add(b.head,sph(.15,12,10),silver,[0,.02,.04],[0,0,0],[.95,1.25,.7]);
  for(let i=0;i<7;i++){const a=(i/6-.5)*PI*1.3;add(b.head,cone(.035,.26+(i===3?.2:i%2?.1:0),5),ice,[Math.sin(a)*.17,.3,Math.cos(a)*.1-.02],[0,0,-Math.sin(a)*.5])}
  add(b.torso,cone(.62,.5,10),b.trim,[0,.78,0]);
  for(let i=0;i<8;i++){const a=i/8*PI*2;add(b.g,cone(.06,.3,4),ice,[Math.cos(a)*.66,.12,Math.sin(a)*.66],[PI,0,0])}
  add(b.aR,cyl(.03,.03,2.6,6),wood,[0,b.hand+.5,.12]);add(b.aR,new THREE.TorusGeometry(.14,.02,5,12),silver,[0,b.hand+1.85,.12]);
  add(b.aR,sph(.09,8,6),mat(0x0a2030,{emissive:0x7fe6ff,ei:3}),[0,b.hand+1.85,.12]);add(b.aR,cone(.05,.3,5),ice,[0,b.hand+2.1,.12]);
  return{group:b.g,parts:b.parts,height:2.6}}

// Boss 4 暗影行刑者：黑鐵甲＋皮圍裙、鉚釘鐵面罩、纏鏈、寬刃巨劍、紫煙
function executioner(){const K=kit(true),{mat,add,grp,sph,cyl,cone,box}=K;const b=bossBase(K,{armor:0x26262c,trim:0x3a3438,eye:0xb05cff,rough:.55,metal:.75,w:1.3});
  const leather=mat(0x3d2a20,{rough:.95}),iron=mat(0x4b4b52,{rough:.4,metal:.85}),chain=mat(0x6a6a70,{rough:.4,metal:.9});
  add(b.head,cyl(.17,.2,.3,8),iron,[0,.02,0]);add(b.head,cone(.2,.3,8),mat(0x151518,{rough:.9}),[0,.3,-.02]);add(b.head,box(.24,.03,.05),mat(0x050505),[0,.03,.16]);
  for(const [x,y] of [[.12,.13],[-.12,.13],[.12,-.08],[-.12,-.08]])add(b.head,sph(.02,5,4),chain,[x,y,.16]);
  add(b.torso,box(.62,1.05,.05),leather,[0,.05,.4],[-.08,0,0]);
  for(const [y,r] of [[.3,.3],[.5,-.25],[.7,.15]])add(b.torso,new THREE.TorusGeometry(.5,.035,5,16),chain,[0,y,0],[PI/2+r,0,r]);
  add(b.aR,box(.3,.04,1.9),iron,[0,b.hand,1.2]);add(b.aR,box(.5,.07,.08),leather,[0,b.hand,.22]);add(b.aR,cyl(.04,.04,.4,6),leather,[0,b.hand,0],[PI/2,0,0]);
  return{group:b.g,parts:b.parts,height:2.55}}

// Boss 5 噬語魔王：扭曲黑角、骷髏臉、金黑華甲、書頁披風、鋸齒巨劍、符文手
function devourer(){const K=kit(true),{mat,add,grp,sph,cyl,cone,box}=K;const b=bossBase(K,{armor:0x1b191d,trim:0xa8842f,eye:0xff3020,rough:.4,metal:.85,w:1.18});
  const bone=mat(0xd8cfb6,{rough:.85}),horn=mat(0x0d0c0e,{rough:.6}),page=mat(0xd9cfb0,{rough:1,double:true}),rune=mat(0x200804,{emissive:0xff5a1a,ei:2.6}),blade=mat(0x2a2a30,{rough:.35,metal:.9});
  add(b.head,sph(.18,10,8),bone,[0,.04,0],[0,0,0],[1,1.12,1]);add(b.head,box(.17,.12,.13),bone,[0,-.11,.07]);for(const x of [.065,-.065])add(b.head,sph(.05,8,6),mat(0x050505),[x,.03,.13]);
  for(const sg of [1,-1]){add(b.head,cone(.08,.5,6),horn,[.2*sg,.3,-.05],[-.3,0,-.7*sg]);add(b.head,cone(.055,.45,6),horn,[.42*sg,.56,-.14],[-.5,0,.15*sg])}
  add(b.head,cyl(.2,.19,.06,10),b.trim,[0,.17,0]);for(let i=0;i<5;i++){const a=(i/4-.5)*PI;add(b.head,cone(.03,.14,4),b.trim,[Math.sin(a)*.19,.26,Math.cos(a)*.19])}
  // 書頁披風：一排排泛黃的紙頁
  const cape=b.parts.cape=grp(b.torso,[0,.92,-.36]);cape.userData.rx=.14;for(let r=0;r<4;r++)for(let i=0;i<5;i++)add(cape,box(.24,.34,.012),page,[(i-2)*.24+(r%2?.1:0),-.2-r*.3,r*.02],[.12,0,(i-2)*.05]);
  add(b.aR,box(.26,.045,2.2),blade,[0,b.hand,1.35]);for(let i=0;i<6;i++)add(b.aR,cone(.07,.22,3),blade,[-.17,b.hand,.5+i*.34],[0,0,PI/2]);add(b.aR,box(.56,.08,.09),b.trim,[0,b.hand,.2]);
  add(b.aL,sph(.15,8,6),rune,[0,b.hand,0]);
  return{group:b.g,parts:b.parts,height:2.6}}

const BOSS={boss_sentinel:sentinel,boss_gargoyle:gargoyle,boss_priest:priest,boss_executioner:executioner,boss_devourer:devourer};
export const standinFor=code=>()=>code==="hero_cute"?heroCute():code==="hero_knight"?heroKnight():code.startsWith("slime")?slime(code):code.startsWith("bat")?bat(code):(BOSS[code]||sentinel)();
