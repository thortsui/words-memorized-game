// 玩家招式的演出（兩種模式共用，配色與鏡頭由場景提供的 ctx 決定）。
// 流程對應規則引擎的事件：start(p)＝skill／quickSlash／counter（起手），hit(p)＝每一段傷害。
//
// ctx（由場景提供）：
//   eng, fx, hero（Actor）, foe()（目前的敵人 Actor）, soul
//   approach() / retreat()   主角衝到敵人面前／回到原位
//   impact(p, {power, ono, color})  命中表現：呼叫 p.onImpact()、敵人受擊、傷害數字、頓格、震動
//   cam(name)                鏡頭提示：'melee' 'cast' 'sky' 'base'
//   dim(k, dur)              天色轉暗（0 = 恢復）
//   pal                      配色 {slash, fire, thunder, ice, holy, meteor}
import * as THREE from 'three';
import { ease, rand } from './engine.js';

const v3=(x,y,z)=>new THREE.Vector3(x,y,z);

export function createMoves(ctx){
  const {eng,fx,hero}=ctx,pal=ctx.pal;
  let st=null; // 目前這一招的狀態：{move, circle, orb, sword, air, melee}
  const foeC=(k=.5)=>ctx.foe().center(v3(),k);
  const heroHand=()=>{const c=hero.center(v3(),.62),f=v3(Math.sin(hero.root.rotation.y),0,Math.cos(hero.root.rotation.y));return c.addScaledVector(f,hero.h*.42)};
  const melee=m=>m==="slash"||m==="gale"||m==="quick"||m==="counter";

  async function start(p){const move=p.move||p.skillId||"slash";st={move,n:0};const h=hero.h;
    if(melee(move)){st.melee=true;ctx.cam("melee");await ctx.approach(move==="counter"?.16:move==="quick"?.2:.3);return}
    if(move==="meteorEnd"){st.air=true;ctx.cam("sky");
      // 躍起：飛到敵人上方
      const f=ctx.foe(),r=hero.root.position,from=r.clone(),to=v3().lerpVectors(from,f.root.position,.62);to.y=Math.max(2.6,f.h*1.9);
      hero.play("Run");fx.ring(from,{color:pal.meteor,r1:1.3,dur:.35});fx.emit({p:from,n:14,color:pal.meteor,speed:[1,3],up:2,size:[.12,.24],life:[.3,.6],gravity:4});
      await eng.tween(.42,k=>{r.lerpVectors(from,to,k);r.y=to.y*ease.out(k)},ease.out);
      hero.setLoop("Idle");hero.play("HeavySlash",{hold:true,speed:.6});st.glow=fx.orb(hero.center(),{color:pal.meteor,size:h*1.6,opacity:.7});await eng.wait(.16);return}
    // 魔法：吟唱＋魔法陣
    ctx.cam("cast");hero.play("Cast",{hold:true});
    const col=pal[move==="thunder"?"thunder":move==="ice"?"ice":move==="holy"?"holy":"fire"];
    st.circle=fx.circle(hero.root.position,{color:col,r:h*.95});
    fx.emit({p:hero.root.position,n:16,color:col,speed:[.2,.8],up:1.6,size:[.08,.16],life:[.5,.9],radius:h*.6,radiusY:.05});
    if(move==="fire"){st.orb=fx.orb(heroHand(),{color:pal.fire,size:.1});const o=st.orb.sprite;
      await eng.tween(.5,k=>{o.scale.setScalar(.1+h*.75*k);o.position.copy(heroHand());o.position.y+=h*.25*k;if(Math.random()<.5)fx.emit({p:o.position,n:1,color:[pal.fire,0xffe08a],speed:[.3,1],size:[.06,.14],life:[.2,.4]})},ease.out)}
    else if(move==="thunder"){ctx.dim(.55,.4);const c=foeC(1);const cloud=st.cloud=fx.orb(v3(c.x,c.y+5,c.z),{color:pal.thunder,size:.5,opacity:.5});
      await eng.tween(.5,k=>{cloud.sprite.scale.setScalar(.5+4*k);if(Math.random()<.4){const a=v3(c.x+rand(-1.5,1.5),c.y+5+rand(-.4,.4),c.z+rand(-1,1));fx.emit({p:a,n:1,color:pal.thunder,speed:[.2,1],size:[.1,.2],life:[.15,.3],kind:1})}},ease.out)}
    else if(move==="ice"){const c=foeC(1);fx.emit({p:v3(c.x,c.y+2.4,c.z),n:24,color:[pal.ice,0xffffff],speed:[.1,.6],size:[.1,.22],life:[.5,1],radius:1,radiusY:.3,kind:1});await eng.wait(.42)}
    else if(move==="holy"){ctx.dim(.5,.4);ctx.cam("sky");
      // 巨大光劍在敵人上空成形
      const c=foeC(0),g=new THREE.Group(),s=Math.max(1,ctx.foe().h*.9);
      const blade=new THREE.Mesh(fx.G.box,fx.basic(pal.holy,{map:fx.beamTex})),tip=new THREE.Mesh(fx.G.cone,fx.basic(pal.holy)),guard=new THREE.Mesh(fx.G.box,fx.basic(0xffffff)),grip=new THREE.Mesh(fx.G.box,fx.basic(pal.holy));
      blade.scale.set(.42*s,4.2*s,.1*s);blade.position.y=2.7*s;blade.rotation.z=Math.PI; /* 漸層貼圖亮的一端朝下（劍尖） */tip.scale.set(.5*s,.7*s,.12*s);tip.rotation.z=Math.PI;tip.rotation.y=Math.PI/6;tip.position.y=.25*s;guard.scale.set(1.3*s,.14*s,.14*s);guard.position.y=3.9*s;grip.scale.set(.14*s,.8*s,.12*s);grip.position.y=4.35*s;guard.material.opacity=grip.material.opacity=.5;
      g.add(blade,tip,guard,grip);g.position.set(c.x,7.5,c.z);g.rotation.y=Math.atan2(eng.camera.position.x-c.x,eng.camera.position.z-c.z);eng.scene.add(g);st.sword=g;st.swordS=s;
      const setOp=o=>g.children.forEach((m,i)=>m.material.opacity=o*(i>1?.45:1));setOp(0);
      await eng.tween(.7,k=>{setOp(k*.9);g.position.y=7.5-1.6*k;if(Math.random()<.7)fx.emit({p:v3(c.x+rand(-.5,.5)*s,g.position.y+rand(0,4)*s,c.z),n:1,color:[pal.holy,0xffffff],speed:[.1,.5],size:[.1,.2],life:[.3,.6],kind:1})},ease.out)}
    else await eng.wait(.3)}

  async function hit(p){if(!st)st={move:p.move||"slash",n:0,melee:true};const S=st,move=st.move,i=p.index||0,h=hero.h,f=ctx.foe();if(!f)return ctx.impact(p,{power:1});const c=foeC();
    if(melee(move)){
      // 連斬：整段 Combo 只播一次，各段傷害對在片段裡實際揮到的那幾格（秒數表在 actors.js 的 IMPACT）
      if(move==="gale"){if(i===0){st.times=hero.comboTimes("Combo",p.total);st.t0=eng.time;hero.play("Combo")}
        const at=st.times[Math.min(i,st.times.length-1)]+(i>=st.times.length?.22*(i-st.times.length+1):0);await eng.wait(Math.max(0,st.t0+at-eng.time))}
      else{const sp=move==="quick"||move==="counter"?1.35:1;hero.play("Slash",{speed:sp});await eng.wait(hero.impactTime("Slash",sp))}
      const ang=move==="gale"?[.6,-.7,1.6][i%3]:rand(.3,.9);
      fx.slash(c,{color:pal.slash,size:Math.min(1.9,f.h*(p.last&&move==="gale"?1.25:.95)+.2),ang,flip:i%2===1});
      await ctx.impact(p,{power:move==="gale"?(p.last?1.3:.8):move==="counter"?1.4:1,ono:move==="gale"?(p.last?"斬！！":"唰"):"斬！",color:pal.slash});
      }
    else if(move==="fire"){if(!st.orb)return ctx.impact(p,{power:2,color:pal.fire});const o=st.orb.sprite,from=o.position.clone();hero.play("Slash");
      const near=c.clone().addScaledVector(v3().subVectors(from,c).setY(0).normalize(),Math.min(.6,f.h*.15));
      await eng.tween(.27,k=>{o.position.lerpVectors(from,near,k);o.position.y+=Math.sin(k*Math.PI)*.5;fx.emit({p:o.position,n:2,color:[pal.fire,0xffd36a,0xff5a1a],speed:[.2,1],size:[.12,.28],life:[.25,.5],grow:-.6})},ease.in);
      st.orb.remove();st.orb=null;
      fx.flash(c,{color:pal.fire,size:f.h*3});fx.ring(f.root.position,{color:pal.fire,r1:f.h*1.8+1});
      fx.emit({p:c,n:46,color:[pal.fire,0xffe08a,0xff4a1a],speed:[2,7],size:[.15,.4],life:[.35,.8],gravity:3,drag:2});
      fx.emit({p:c,n:14,color:0x553322,speed:[.5,2],up:1.5,size:[.4,.8],life:[.6,1.1],alpha:.5,drag:1});
      await ctx.impact(p,{power:2,ono:"轟！",color:pal.fire})}
    else if(move==="thunder"){const top=v3(c.x+rand(-.6,.6),c.y+6,c.z),g=v3(c.x,0,c.z);
      fx.bolt(top,g,{color:0xffffff,width:.2,dur:.26});fx.bolt(v3(top.x+.8,top.y,top.z),g,{color:pal.thunder,width:.12,dur:.3,jag:.7});
      fx.pulseVig("white",.7,.25);fx.flash(c,{color:pal.thunder,size:f.h*3.5});fx.ring(g,{color:pal.thunder,r1:f.h*2+1});
      fx.emit({p:c,n:40,color:[pal.thunder,0xffffff],speed:[2,8],size:[.1,.26],life:[.25,.6],kind:1,drag:2.5});
      const im=ctx.impact(p,{power:2.5,ono:"轟隆！！",color:pal.thunder});
      await eng.wait(.09);fx.bolt(v3(top.x-.9,top.y,top.z+.3),g,{color:0xffffff,width:.16,dur:.2,jag:.6});await im}
    else if(move==="ice"){const big=p.last,s=(big?1.5:.85)*Math.max(.8,f.h*.6),m=new THREE.Mesh(fx.G.cone,new THREE.MeshBasicMaterial({color:big?0xffffff:pal.ice,transparent:true,opacity:.92,fog:false}));
      const off=v3(big?0:rand(-.35,.35)*f.h,0,big?0:rand(-.25,.25)*f.h),from=v3(c.x+off.x+rand(-.5,.5),c.y+3.2,c.z+off.z),to=v3(c.x+off.x,c.y,c.z+off.z);
      m.scale.set(.32*s,1.15*s,.32*s);m.rotation.z=Math.PI;
      await fx.temp(m,big?.22:.14,k=>{m.position.lerpVectors(from,to,k);if(Math.random()<.6)fx.emit({p:m.position,n:1,color:[pal.ice,0xffffff],speed:[.1,.6],size:[.08,.16],life:[.2,.4],kind:1})},ease.in);
      fx.emit({p:to,n:big?36:14,color:[pal.ice,0xffffff,0xbfe9ff],speed:[1.5,big?7:4.5],size:[.1,.26],life:[.3,.7],gravity:5,kind:1,drag:1.5});
      if(big){fx.ring(f.root.position,{color:pal.ice,r1:f.h*2+1});fx.flash(c,{color:pal.ice,size:f.h*2.6})}
      await ctx.impact(p,{power:big?1.7:.75,ono:big?"碎！！":"鏘",color:pal.ice})}
    else if(move==="meteorEnd"){const r=hero.root.position,from=r.clone(),dir=v3().subVectors(from,f.root.position).setY(0).normalize(),to=f.root.position.clone().addScaledVector(dir,f.h*.45+h*.35);to.y=0;
      hero.play("HeavySlash",{speed:1.4});await eng.wait(Math.max(0,hero.impactTime("HeavySlash",1.4)-.17));
      await eng.tween(.17,k=>{r.lerpVectors(from,to,k);if(S.glow)S.glow.sprite.position.copy(hero.center());fx.emit({p:hero.center(),n:3,color:[pal.meteor,0xffffff],speed:[.2,1.2],size:[.16,.34],life:[.25,.5]})},ease.in);
      if(S.glow){S.glow.remove();S.glow=null}
      fx.slash(c,{color:pal.meteor,size:f.h*1.5+.4,ang:-1.2,sweep:1.8});fx.ring(f.root.position,{color:pal.meteor,r1:f.h*2.2+1.2});fx.flash(c,{color:0xffffff,size:f.h*3});
      fx.emit({p:v3(c.x,.1,c.z),n:40,color:[pal.meteor,0xffffff,0xffe08a],speed:[2,7],flat:.35,up:2,size:[.12,.3],life:[.35,.8],gravity:6,kind:1});
      await ctx.impact(p,{power:2.6,ono:"流星斬！",color:pal.meteor})}
    else if(move==="holy"){const g=st.sword,s=st.swordS;if(!g)return ctx.impact(p,{power:3.6,color:pal.holy});const y0=g.position.y;hero.play("HeavySlash");await eng.wait(Math.max(0,hero.impactTime("HeavySlash")-.2));
      await eng.tween(.2,k=>{g.position.y=y0+(-.35*s-y0)*k},ease.in3);
      const gp=v3(c.x,0,c.z);fx.pillar(gp,{color:pal.holy,r:f.h*.8+.5,h:14,dur:.7});fx.pulseVig("white",.85,.4);fx.ring(gp,{color:pal.holy,r1:f.h*3+2,dur:.6});fx.ring(gp,{color:0xffffff,r1:f.h*2+1,dur:.4});
      fx.flash(c,{color:0xffffff,size:f.h*5,dur:.4});
      fx.emit({p:c,n:70,color:[pal.holy,0xffffff],speed:[2,9],size:[.12,.34],life:[.4,1],kind:1,drag:2});
      fx.emit({p:gp,n:30,color:pal.holy,speed:[.2,1],up:4,size:[.1,.2],life:[.6,1.2],radius:f.h*.8,radiusY:.1});
      const im=ctx.impact(p,{power:3.6,ono:"聖光審判！",color:pal.holy});
      eng.tween(.5,k=>g.children.forEach(m=>m.material.opacity=.9*(1-k))).then(()=>{eng.scene.remove(g);g.children.forEach(m=>m.material.dispose())});st.sword=null;await im}
    else await ctx.impact(p,{power:1,ono:"砰！"});
    S.n++;
    if(p.last&&st===S)await finish()}

  // 收招：清掉魔法陣等殘留、恢復天色、主角回位
  async function finish(){const s=st;st=null;if(!s)return;cleanup(s);ctx.dim(0,.4);ctx.cam("base");
    if(s.melee||s.air)await ctx.retreat();else{hero.setLoop("Idle");hero.play("Idle")}}
  function cleanup(s){if(s.circle)s.circle.remove();if(s.orb)s.orb.remove();if(s.cloud)s.cloud.remove();if(s.glow)s.glow.remove();
    if(s.sword){eng.scene.remove(s.sword);s.sword.children.forEach(m=>m.material.dispose())}}
  return{start,hit,finish,abort(){if(st){cleanup(st);st=null}}};
}
