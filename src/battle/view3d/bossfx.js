// 魂系 Boss 的浮誇演出：蓄力（地上魔法陣、光柱、能量往身上聚、身體壓低再拉長）、
// 出手命中（多層斬痕、地面衝擊波、碎石、煙塵牆、畫面閃光）、各 Boss 的招牌特效、第二階段起的常駐氣場。
// 只處理畫面，不碰規則。品質降到 low 或「減少動態效果」時自動減量。
import * as THREE from 'three';
import { ease, lerp, rand } from './engine.js';

const v3=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
const LETTERS="ABCDEFGHIJKLMNOPQRSTUVWXYZ";

// 各 Boss 的配色：主色（招牌特效）、副色（碎屑／煙）
const SIG={
  sentinel:{main:0x9dff7a,alt:0xff8a3a,debris:[0x6a4a30,0x8a6a40,0x3a2a1a]},     // 鏽與根鬚
  gargoyle:{main:0xff8a2a,alt:0xd8dde6,debris:[0x7a7f88,0x9aa0a8,0x55595f]},     // 石屑與狂風
  priest:{main:0x8fe9ff,alt:0xffffff,debris:[0xbfe9ff,0xffffff,0x7fb8d8]},       // 冰霧
  executioner:{main:0xb05cff,alt:0x2a0a3a,debris:[0x3a2a4a,0x1a1024,0x6a4a8a]},  // 暗影
  devourer:{main:0xff3020,alt:0x8a1aff,debris:[0x2a0a0a,0x5a1a1a,0x1a0a1a]},     // 虛空與吞噬的文字
};

export function createBossFx({eng,fx,scene,dust}){
  const lite=()=>eng.rm||eng.quality==="low";
  const n=x=>Math.max(1,Math.round(x*(lite()?.45:1)));
  const sig=b=>SIG[b&&b.data&&b.data.id]||SIG.sentinel;

  /* ---------- 蓄力 ---------- */
  // 回傳 stop()：出手（或被打斷）時呼叫，收掉魔法陣與光柱
  function charge(b,{T=.7,danger=false,dash=false}={}){if(!b)return()=>{};const S=sig(b),p=b.root.position,h=b.h;
    const circ=fx.circle(p,{color:danger?0xff2a1a:S.main,r:h*(danger?.85:.6),spin:danger?3.2:2});
    // 身體先壓低（預備動作）：pose 的縮放，出手時再拉長回彈
    const P=b.pose.scale,s0=b._s||1;if(!eng.rm)eng.to(P,{x:1.07*s0,y:.9*s0,z:1.07*s0},T*.8,ease.out);
    let alive=true,acc=0;
    const off=eng.onUpdate(dt=>{if(!alive||!b.root.visible)return;acc+=dt;circ.mesh.position.set(p.x,.04,p.z);
      // 能量往身上聚：從外圈往胸口
      if(acc>(lite()?.06:.025)){acc=0;const a=rand(0,6.28),R=h*rand(.9,1.5),c=b.center(v3(),.6),from=v3(c.x+Math.sin(a)*R,rand(.1,h*1.1),c.z+Math.cos(a)*R);
        fx.emit({p:from,n:1,color:[danger?0xff2a1a:S.main,0xffffff],speed:[R*1.6,R*2],dir:[c.x-from.x,c.y-from.y,c.z-from.z],spread:.05,size:[.06,.14],life:[.35,.5]})}},60);
    // 細光柱從腳下升起（必殺：粗、紅）
    if(!dash)fx.pillar(p,{color:danger?0xff2a1a:S.main,r:h*(danger?.5:.28),h:h*(danger?4:2.4),dur:T+.25});
    fx.ring(p,{color:danger?0xff2a1a:S.main,r0:h*1.6,r1:.2,dur:T,opacity:.7}); // 往內收的環＝在吸力
    if(danger){for(let i=0;i<n(3);i++)eng.wait(i*T/3).then(()=>{if(!alive)return;const c=b.center(v3(),.8),a=rand(0,6.28);fx.bolt(v3(c.x+Math.sin(a)*h,c.y+h*1.2,c.z+Math.cos(a)*h),c,{color:0xff5a3a,width:.1,dur:.18,jag:.5})})}
    return()=>{if(!alive)return;alive=false;off();circ.remove()}}

  /* ---------- 出手瞬間 ---------- */
  // 身體拉長＋往前探（伸展），命中後彈回
  function lunge(b,t){if(!b||eng.rm)return;const P=b.pose.scale,s0=b._s||1;eng.to(P,{x:.94*s0,y:1.1*s0,z:.94*s0},Math.max(.06,t*.6),ease.out).then(()=>eng.to(P,{x:s0,y:s0,z:s0},.45,ease.elastic))}
  // 被打斷（彈反、突擊）時把身體縮放收回原狀
  function settle(b){if(!b)return;const s0=b._s||1;eng.to(b.pose.scale,{x:s0,y:s0,z:s0},.25,ease.out)}
  // 突進的殘光：沿衝刺路徑留下一串光點
  function streak(b,from,to){if(!b)return;const S=sig(b),c=b.h*.5;for(let i=0;i<n(14);i++){const k=i/13,p=v3().lerpVectors(from,to,k);p.y=c*rand(.4,1.4);
      fx.emit({p,n:1,color:[S.main,0xffffff],speed:[.1,.4],size:[.12,.28],life:[.25,.45]})}}

  /* ---------- 命中（不管玩家有沒有閃掉都會播：刀落地） ---------- */
  // at：命中點；k：力道（連擊中段 .6、一般 1、最後一段／重擊 1.3、必殺 1.8）；dodged：玩家閃掉（衝擊打在地上）
  function impact(b,at,{k=1,dodged=false,from}={}){if(!b)return;const S=sig(b),g=v3(at.x,.05,at.z),id=b.data&&b.data.id;
    // 多層斬痕：外層主色、內層白芯、殘層副色，角度錯開
    const ang=rand(-.9,.9);fx.slash(at,{color:S.main,size:1.15+.45*k,ang,dur:.3,sweep:1.8});fx.slash(at,{color:0xffffff,size:.95+.3*k,ang:ang+.08,dur:.22,sweep:1.8});
    if(k>=1)fx.slash(at,{color:S.alt,size:1.45+.5*k,ang:ang-.15,dur:.4,sweep:1.5,flip:true});
    // 地面衝擊波（兩圈）＋煙塵牆＋碎石
    fx.ring(g,{color:S.main,r1:1.6+1.6*k,dur:.45,opacity:.8});fx.ring(g,{color:0xffffff,r1:.8+1*k,dur:.3,opacity:.6});
    dust(g,n(8+8*k),[0x5a5f68,0x7a7f88,0x4a4038]);
    fx.emitN({p:v3(g.x,.15,g.z),n:n(10+10*k),color:S.debris,speed:[2,4+3*k],up:3,size:[.07,.16],life:[.5,.9],gravity:14,alpha:1,drag:.6});
    fx.flash(at,{color:S.main,size:1.6+1.2*k,dur:.22,opacity:.75});
    if(k>=1.3){fx.pulseVig("white",.18+.1*k,.22);eng.hitStop(60+30*k)}
    // 招牌特效
    if(id==="sentinel")roots(g,from,k);
    else if(id==="gargoyle")gust(g,k);
    else if(id==="priest")frost(g,k);
    else if(id==="executioner")shadowX(at,k);
    else if(id==="devourer")voidWords(at,g,k);
    if(dodged)fx.emit({p:v3(g.x,.3,g.z),n:n(12),color:[S.main,0xffffff],speed:[3,7],flat:.15,up:.6,size:[.04,.09],life:[.2,.45],gravity:6})}

  // 守門騎士：鏽色火星＋從地面竄出的根鬚（朝主角一排）
  function roots(g,from,k){const d=from?v3().subVectors(g,from).setY(0).normalize():v3(0,0,1);const N=n(3+Math.round(2*k));
    for(let i=0;i<N;i++)eng.wait(i*.05).then(()=>{const p=g.clone().addScaledVector(d,(i-1)*.55).add(v3(rand(-.3,.3),0,rand(-.3,.3))),hgt=rand(.8,1.4)*(.8+.3*k);
      const m=new THREE.Mesh(fx.G.cone,new THREE.MeshStandardMaterial({color:0x3a2a1a,roughness:.9,emissive:0x1a3a10,emissiveIntensity:.6}));m.position.copy(p);m.rotation.set(rand(-.3,.3),rand(0,6),rand(-.3,.3));
      fx.temp(m,.8,(kk,r)=>{const s=r<.18?ease.back(r/.18):r>.7?1-(r-.7)/.3:1;m.scale.set(.22*s,Math.max(.01,hgt*s),.22*s);m.position.y=m.scale.y*.45});
      fx.emit({p:v3(p.x,.2,p.z),n:n(6),color:[0xff8a3a,0xffd09a],speed:[1,3],up:2,size:[.03,.07],life:[.3,.6],gravity:8})})}
  // 石像鬼：石屑＋一圈直立的風壓環
  function gust(g,k){for(let i=0;i<n(2);i++)eng.wait(i*.07).then(()=>{const m=new THREE.Mesh(fx.G.ringThin,fx.basic(0xd8dde6));m.position.set(g.x,.9,g.z);
      fx.temp(m,.45,(kk,r)=>{m.quaternion.copy(eng.camera.quaternion);m.scale.setScalar(.4+(2.4+k)*ease.out3(r));m.material.opacity=.7*(1-r)})});
    fx.emitN({p:v3(g.x,.6,g.z),n:n(14),color:[0x8a8f98,0xb0b6bf],speed:[3,6],up:1.5,size:[.08,.18],life:[.4,.8],gravity:12,drag:.4})}
  // 霜冠祭司：寒霧＋雪花爆散
  function frost(g,k){fx.emitN({p:v3(g.x,.3,g.z),n:n(10),color:[0xbfe9ff,0xffffff],speed:[.5,1.6],flat:.3,up:.3,size:[.5,1],life:[.7,1.2],alpha:.35,drag:1.5,grow:1});
    fx.emit({p:v3(g.x,.8,g.z),n:n(22),color:[0x8fe9ff,0xffffff],speed:[2,5+2*k],up:1,size:[.04,.1],life:[.4,.9],gravity:2,kind:1})}
  // 暗影行刑者：交叉的紫黑 X 斬＋黑煙
  function shadowX(at,k){fx.slash(at,{color:0xb05cff,size:2+.6*k,ang:.8,dur:.36,sweep:1.2});fx.slash(at,{color:0x7a2aff,size:2+.6*k,ang:-.8,dur:.36,sweep:1.2,flip:true});
    fx.emitN({p:at,n:n(10),color:[0x1a1024,0x2a1a3a],speed:[.6,1.8],up:.6,size:[.4,.8],life:[.6,1],alpha:.55,drag:1.4,grow:.8})}
  // 噬語魔王：被吞掉的字母從命中點噴出、黑紫雷從天而降
  function voidWords(at,g,k){for(let i=0;i<n(5+3*k);i++){const L=LETTERS[Math.floor(Math.random()*26)];fx.text(v3(at.x+rand(-.6,.6),at.y+rand(-.3,.5),at.z+rand(-.6,.6)),L,"soul voidl",{dur:.9,rise:rand(30,70),dx:rand(-60,60)})}
    for(let i=0;i<n(k>=1.3?3:1);i++)eng.wait(i*.06).then(()=>{const t=v3(g.x+rand(-1.2,1.2),0,g.z+rand(-1.2,1.2));fx.bolt(v3(t.x+rand(-.5,.5),7,t.z),t,{color:i%2?0x8a1aff:0xff3020,width:.16,dur:.22,jag:.6});fx.ring(t,{color:0x8a1aff,r1:1.4,dur:.35})})}

  /* ---------- 第二階段起的常駐氣場 ---------- */
  // 身邊不斷冒出主色的火星與黑煙；階段越高越濃。回傳 stop()
  function aura(b,phase){if(!b)return()=>{};const S=sig(b);let acc=0,alive=true;
    const off=eng.onUpdate(dt=>{if(!alive||!b.root.visible)return;acc+=dt*(1+phase)*(lite()?.4:1);while(acc>.12){acc-=.12;const c=b.center(v3(),rand(.1,.9)),a=rand(0,6.28),r=b.h*.25;
        fx.emit({p:v3(c.x+Math.sin(a)*r,c.y,c.z+Math.cos(a)*r),n:1,color:[S.main,0xffffff],speed:[.2,.6],up:1.4,size:[.05,.12],life:[.6,1.1],gravity:-.5});
        if(Math.random()<.35)fx.emitN({p:v3(c.x,c.y*.5,c.z),n:1,color:[0x111014,0x241a1a],speed:[.1,.4],up:.8,size:[.5,.9],life:[.8,1.4],alpha:.3,grow:.6})}},60);
    return()=>{alive=false;off()}}

  /* ---------- 登場／變身 ---------- */
  // 咆哮衝擊波：三圈地面環＋一圈面向鏡頭的大環＋碎石
  function roarBlast(b){if(!b)return;const S=sig(b),p=b.root.position;for(let i=0;i<3;i++)eng.wait(i*.12).then(()=>fx.ring(p,{color:i?S.main:0xffffff,r1:6+i*2,dur:.7,opacity:.7}));
    fx.burstRing(b.center(v3(),.7),{color:S.main,r1:b.h*1.4,dur:.5});
    fx.emitN({p:v3(p.x,.2,p.z),n:n(26),color:S.debris,speed:[3,7],up:3,size:[.08,.2],life:[.6,1.2],gravity:12,radius:b.h*.3})}
  // 變身：身體膨脹一下（之後維持稍大）、主色光柱與多道閃電
  function phaseBurst(b,phase){if(!b)return;const S=sig(b),p=b.root.position,s=1+.06*phase;b._s=s;
    if(!eng.rm){b.pose.scale.set(s*1.15,s*.85,s*1.15);eng.to(b.pose.scale,{x:s,y:s,z:s},.7,ease.elastic)}
    fx.pillar(p,{color:S.main,r:b.h*.7,h:b.h*5,dur:1.2});roarBlast(b);
    for(let i=0;i<n(5);i++)eng.wait(i*.1).then(()=>{const a=rand(0,6.28),t=v3(p.x+Math.sin(a)*b.h*.8,0,p.z+Math.cos(a)*b.h*.8);fx.bolt(v3(t.x,b.h*2.5,t.z),t,{color:i%2?0xffffff:S.main,width:.14,dur:.25,jag:.55})})}

  return{charge,lunge,settle,streak,impact,aura,roarBlast,phaseBurst,sig};
}
