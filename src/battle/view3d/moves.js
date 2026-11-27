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
import { sfx } from '../../core/audio.js';

const v3=(x,y,z)=>new THREE.Vector3(x,y,z);

export function createMoves(ctx){
  const {eng,fx,hero}=ctx,pal=ctx.pal;
  let st=null; // 目前這一招的狀態：{move, circle, orb, sword, air, melee}
  const foeC=(k=.5)=>ctx.foe().center(v3(),k);
  const heroHand=()=>{const c=hero.center(v3(),.62),f=v3(Math.sin(hero.root.rotation.y),0,Math.cos(hero.root.rotation.y));return c.addScaledVector(f,hero.h*.42)};
  const melee=m=>m==="slash"||m==="gale"||m==="quick"||m==="counter"||m==="chain";
  /* 魂系自動連斬：3／4／5 段各三組動作，事件帶 variant（0–2）隨機挑一組。
     c0–c2＝Combo 片段的第 1–3 揮、s＝斬擊、sf＝反手斬擊、h＝重斬、spin＝迴旋斬、leap＝躍起下劈、thrust＝突刺（往前踏一步） */
  const CHAIN={
    2:[["s","h"],["c0","c2"],["sf","thrust"]],
    3:[["c0","c1","c2"],["s","sf","h"],["spin","thrust","leap"]],
    4:[["c0","c1","c2","h"],["s","sf","thrust","leap"],["spin","c1","sf","h"]],
    5:[["c0","c1","c2","s","leap"],["s","sf","thrust","c2","h"],["spin","c0","c1","sf","leap"]]};
  // 劍砍到金屬：白金火花＋小閃光；重擊（最後一段）火花加倍、多一圈衝擊環
  // 火花分三層：拉長的火花條（主體，HDR 亮度吃光暈）＋細碎光點＋白熱閃光；方向偏向鏡頭側與上方，才看得到噴出去
  const metal=(c,big)=>{const cam=eng.camera.position,toCam=v3(cam.x-c.x,0,cam.z-c.z).normalize(),dir=v3(toCam.x*.55,.65,toCam.z*.55);
    fx.streaks({p:c,n:big?70:40,dir,spread:1.1,speed:[5,big?17:13],life:[.18,big?.6:.45],hdr:big?4.5:3.4,width:big?.03:.024,len:.05});
    fx.streaks({p:c,n:big?26:14,color:[0xffffff,0xfff6dc],speed:[8,big?20:15],life:[.08,.18],hdr:6,width:.018,len:.035,gravity:4});
    fx.emit({p:c,n:big?50:26,color:[0xfff4d0,0xffffff,0xffb050,0xff8a2a],speed:[2.5,big?12:9],size:[.06,.16],life:[.2,.6],gravity:9,drag:1.1,kind:1});
    fx.flash(c,{color:0xffffff,size:big?.9:.55,dur:.07,opacity:1});
    fx.flash(c,{color:0xffd9a0,size:big?2.2:1.3,dur:big?.24:.16,opacity:.95});fx.burstRing(c,{color:0xffe0a0,r1:big?1.6:.9,dur:big?.3:.2})};
  async function chainStep(code,i,p){const P=hero.pose;
    if(code[0]==="c"){const k=+code[1],ht=hero.comboTimes("Combo",3),t0=k?ht[k-1]+.03:0,sp=1.2;
      if(hero.has&&hero.has("Combo")&&hero.playSeg("Combo",t0,ht[k],sp)){await eng.wait(Math.max(.1,(ht[k]-t0)/sp));return}
      hero.play("Slash",{speed:1.4});await eng.wait(hero.impactTime("Slash",1.4));return}
    if(code==="s"||code==="sf"){hero.play("Slash",{speed:1.35,fade:.05});if(code==="sf")eng.to(P.rotation,{y:-.5},.12,ease.out).then(()=>eng.to(P.rotation,{y:0},.25,ease.out));await eng.wait(hero.impactTime("Slash",1.35));return}
    if(code==="h"){hero.play("HeavySlash",{speed:1.25,fade:.05});await eng.wait(hero.impactTime("HeavySlash",1.25));return}
    if(code==="thrust"){hero.play("Slash",{speed:1.5,fade:.05});const T=hero.impactTime("Slash",1.5);P.position.z=0;await eng.tween(T,k=>{P.position.z=.45*ease.out(k)});eng.to(P.position,{z:0},.3,ease.out);return}
    if(code==="spin"){hero.play("HeavySlash",{speed:1.3,fade:.05});const T=hero.impactTime("HeavySlash",1.3);await eng.tween(T,k=>{P.rotation.y=Math.PI*2*ease.out(k)});P.rotation.y=0;return}
    if(code==="leap"){hero.play("HeavySlash",{speed:1.1,fade:.05});const T=hero.impactTime("HeavySlash",1.1);await eng.tween(T,k=>{P.position.y=Math.sin(k*Math.PI*.95)*.9});P.position.y=0;
      const g=hero.root.position;fx.ring(v3(g.x,0,g.z),{color:0xffe0a0,r1:2.4,dur:.4});fx.emitN({p:v3(g.x,.1,g.z),n:16,color:[0x6b7078,0x8a8f98],speed:[1,3],flat:.3,up:.6,size:[.3,.6],life:[.4,.8],alpha:.4,drag:2,grow:.8});return}
    hero.play("Slash");await eng.wait(hero.impactTime("Slash"))}

  /* ---- v1.3.0 連續連斬 ----
     答題期間不出刀：主角架在 ChainReady 蓄勢，每答對一題只亮一下判定（完美／普通）；整套答完（或答錯、擊倒、被突襲）才一口氣播完整段連續動作。
     第 i 刀依那一題的判定挑片段：完美＝ChainP1–P4（華麗）、普通＝ChainN1–N4（樸素）；最後一刀是終結技——全部完美＝FinishAll、最後一題完美＝FinishP、否則 FinishN。
     答錯＝播完已答對的刀之後接 ChainBreak（被彈開、踉蹌）。每一段在 cancel 時間交叉淡入下一段，所以任何判定組合都串成一整段。 */
  const ROW={perfect:["ChainP1","ChainP2","ChainP3","ChainP4"],normal:["ChainN1","ChainN2","ChainN3","ChainN4"]};
  const hasFlow=()=>hero.has("ChainP1")&&hero.has("ChainN1")&&hero.has("FinishN")&&hero.has("FinishP");
  const LUNGE={ChainP1:.15,ChainP3:.1,ChainN3:.12,FinishAll:.1,FinishP:.1,AssaultEnd:.3,Execution:.15,Riposte:.15}; // 這一段往前踏多少（公尺，片段原地播放）
  const ANG={ChainP1:.7,ChainP2:-1.0,ChainP3:1.5,ChainP4:.2,ChainN1:-1.3,ChainN2:-.8,ChainN3:.1,ChainN4:0,FinishAll:-1.5,FinishP:3.1,FinishN:-1.4,AssaultA:.6,AssaultB:-.7,AssaultEnd:.1,Execution:-1.2,Riposte:.4};
  function flowClip(p,fin,grades){const g=p.grade==="perfect"?"perfect":"normal";
    if(fin)return grades.length>1&&grades.every(x=>x==="perfect")?"FinishAll":g==="perfect"?"FinishP":"FinishN";
    return ROW[g][Math.min(p.index||0,3)]}
  // 答題中的判定提示：主角頭上冒出「完美／普通」、劍上聚光（完美更亮）
  function mark(p){const perf=p.grade==="perfect",c=hero.center(v3(),1.12);
    fx.text(c,perf?"完美":"普通",perf?"soul gold big":"soul",{dur:.8,rise:18,dx:0,rot:0});sfx(perf?"gradePerfect":"gradeNormal",{v:.7});sfx("charge",{v:.5});
    const hc=heroHand();fx.emit({p:hc,n:perf?16:7,color:perf?[0xffe2a0,0xffffff,0xffc04a]:[0xdfe8ff,0xffffff],speed:[.3,1.4],up:.6,size:[.04,perf?.12:.08],life:[.25,.55],radius:.25,kind:1});
    if(perf)fx.flash(hc,{color:0xffe2a0,size:.6,dur:.16,opacity:.8})}
  const until=t=>eng.wait(Math.max(0,t-eng.time));
  // 一段：播片段、命中那幾格出刀光與傷害、到 cancel 時間就交給下一段。回傳 impact 的 promise
  async function seg(clip,p,{fade=.1,power=.85,last=false}={}){const f=ctx.foe();if(!f)return;const P=hero.pose;
    if(window.__soulTest)(window.__chainLog=window.__chainLog||[]).push({clip,grade:p.grade,index:p.index,t:+eng.time.toFixed(2)});
    hero.play(clip,{fade,hold:true});const t0=eng.time,D=hero.duration(clip),hits=(hero.hitTimes(clip)||[hero.impactTime(clip)]).slice(),cut=last?D*.9:hero.cancelTime(clip),L=LUNGE[clip]||0;
    sfx(/^Finish/.test(clip)?"swingH":"swingL",{v:.8});
    if(L)eng.tween(Math.max(.08,hits[0]),k=>{P.position.z=L*ease.out(k)}).then(()=>eng.wait(Math.max(0,cut-hits[0]-.15))).then(()=>{if(st&&st.flowing)eng.to(P.position,{z:0},.25,ease.io)});
    let im=null;const n=hits.length;
    for(let j=0;j<n;j++){await until(t0+hits[j]);const c=foeC(),fin=j===n-1;
      const a=(ANG[clip]??rand(-.9,.9))+(j%2?Math.PI*.6:0);
      fx.slash(c,{color:pal.slash,size:Math.min(2.4,f.h*(power>1.2?1.35:1)+.2),ang:a,flip:j%2===1,sweep:/P2|FinishP|FinishAll/.test(clip)?2.4:1.5});
      if(/FinishAll|FinishP/.test(clip)&&fin){fx.slash(c,{color:0xffffff,size:Math.min(2.4,f.h*1.2+.3),ang:-a,sweep:2.2,flip:true});fx.burstRing(c,{color:0xffe0a0,r1:2.2,dur:.35})}
      metal(c,power>1.2&&fin);sfx(power>1.2&&fin?"clashBig":"clash",{v:.8});
      // 傷害（扣血、數字）落在這一段最後一個命中；前面的命中只有刀光與火花
      if(fin){im=ctx.impact(p,{power,color:pal.slash});if(last)sfx("finisher",{v:.9})}else{const b=ctx.foe();if(b){b.flash(0xffffff,.6);b.knock(.05,.02)}}}
    if(/FinishAll/.test(clip)){const g=hero.root.position;fx.ring(v3(g.x,0,g.z),{color:0xffe0a0,r1:2.6,dur:.45});sfx("slam",{v:.6})}
    await until(t0+cut);return im}
  // 播放累積的連斬。mode：final（砍完／擊倒，最後一刀是終結技）、break（答錯）、cut（被突襲打斷）、partial（中途轉階段：播完已答的刀，回到蓄勢）
  async function flush(mode="final"){const S=st;if(!S||!S.flow||S.flowing)return;const Q=S.queue.splice(0);
    if(!Q.length&&mode!=="break"){if(mode==="final")await finish();return}
    S.flowing=true;ctx.cam("melee");if(S.reapproach){S.reapproach=false;await ctx.approach(.22)}
    const grades=Q.length?(Q[Q.length-1].grades||Q.map(x=>x.grade)):[];let im=null;
    for(let k=0;k<Q.length;k++){const p=Q[k],fin=mode==="final"&&k===Q.length-1&&(p.last||p.kill),clip=flowClip(p,fin,grades);
      const pw=clip==="FinishAll"?2.2:fin?1.6:p.grade==="perfect"?.95:.75;
      im=await seg(clip,p,{fade:!k?.14:fin&&(p.index||0)<4?.15:.1,power:pw,last:fin});if(st!==S)return}
    if(im)await im;
    if(mode==="break"&&hero.has("ChainBreak")){hero.play("ChainBreak",{fade:.08,hold:true});sfx("clashBig",{v:.6});sfx("gradeWrong",{v:.6});metal(foeC(),false);
      await eng.wait(hero.duration("ChainBreak")*.85)}
    S.flowing=false;hero.pose.position.z=0;
    if(mode==="partial"){S.reapproach=true;hero.play("ChainReady",{fade:.15});return}
    if(mode==="cut")return;
    if(hero.has("ChainRecover")&&mode==="final"){hero.play("ChainRecover",{fade:.12,hold:true});await eng.wait(hero.duration("ChainRecover")*.45)}
    await finish()}

  async function start(p){const move=p.move||p.skillId||"slash";st={move,n:0};const h=hero.h;
    // 連斬三種演出：flow（攻擊題開始的連續連斬）、assault（突擊）、exec（弱點擊破處決）
    if(move==="chain"&&hasFlow()){if(p.assault){st.assault=true;st.final=(p.index||0)>=(p.total||1)-1;st.ai=p.index||0}else if(p.type==="weakBreak"&&hero.has("Execution"))st.exec=true;
      else{st.flow=true;st.queue=[]}}
    if(melee(move)){st.melee=true;ctx.cam("melee");await ctx.approach(move==="counter"?.16:move==="quick"?.2:.3);
      if(st&&st.flow&&hero.has("ChainReady")){hero.play("ChainReady",{fade:.18});sfx("charge",{v:.6})}return}
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
    if(move==="chain"&&S.flow){S.queue.push(p);if(!(p.last||p.kill))p.deferred=true;mark(p);if(p.last||p.kill)await flush("final");return}
    if(move==="chain"&&(S.assault||S.exec)){
      if(i===0){S.clip=S.exec?"Execution":S.final?"AssaultEnd":S.ai%2?"AssaultB":"AssaultA";S.t0=eng.time;hero.play(S.clip,{fade:.1,hold:true});sfx(S.exec||S.final?"swingH":"swingL",{v:.8});const L=LUNGE[S.clip]||0;
        if(L)eng.tween(Math.max(.08,hero.impactTime(S.clip)),k=>{hero.pose.position.z=L*ease.out(k)})}
      const ht=hero.hitTimes(S.clip)||[hero.impactTime(S.clip)],at=i<ht.length?ht[i]:ht[ht.length-1]+.12*(i-ht.length+1);await until(S.t0+at);
      fx.slash(c,{color:pal.slash,size:Math.min(2.3,f.h*(p.last?1.3:1)+.2),ang:(ANG[S.clip]||0)+(i%2?Math.PI*.6:0),flip:i%2===1,sweep:p.last?2.2:1.5});metal(c,!!p.last);sfx(p.last?"clashBig":"clash",{v:.8});
      await ctx.impact(p,{power:p.last?(S.exec?2:1.5):.8,color:pal.slash});
      if(p.last){await until(S.t0+hero.cancelTime(S.clip));eng.to(hero.pose.position,{z:0},.25,ease.io);if(st===S)await finish()}return}
    if(move==="chain"){const n=p.n||p.total||3,set=(CHAIN[n]||CHAIN[3])[(p.variant||0)%3],code=set[Math.min(i,set.length-1)];
      await chainStep(code,i,p);
      const ang={c0:.6,c1:-.7,c2:1.6,s:.4,sf:-.9,h:-1.3,spin:0,leap:-1.5,thrust:.1}[code]??rand(-.9,.9);
      fx.slash(c,{color:pal.slash,size:Math.min(2.2,f.h*(p.last?1.3:.95)+.2),ang,flip:code==="sf"||code==="c1",sweep:code==="spin"?2.6:1.4});
      if(code==="spin")fx.slash(c,{color:0xffffff,size:Math.min(2,f.h*.9+.2),ang:Math.PI,sweep:2.6,flip:true});
      metal(c,!!p.last);
      await ctx.impact(p,{power:p.last?1.5:.8,ono:p.last?(code==="leap"?"破！！":"斬！！"):["鏘","唰","鏘"][i%3],color:pal.slash});
      }
    else if(melee(move)){
      // 連斬：整段 Combo 只播一次，各段傷害對在片段裡實際揮到的那幾格（秒數表在 actors.js 的 IMPACT）
      if(move==="gale"){if(i===0){st.times=hero.comboTimes("Combo",p.total);st.t0=eng.time;hero.play("Combo")}
        const at=st.times[Math.min(i,st.times.length-1)]+(i>=st.times.length?.22*(i-st.times.length+1):0);await eng.wait(Math.max(0,st.t0+at-eng.time))}
      else if(move==="counter"&&hero.has("Riposte")){hero.play("Riposte",{fade:.08});sfx("swingL",{v:.8});eng.tween(hero.impactTime("Riposte"),k=>{hero.pose.position.z=LUNGE.Riposte*ease.out(k)}).then(()=>eng.to(hero.pose.position,{z:0},.3,ease.io));await eng.wait(hero.impactTime("Riposte"))}
      else{const sp=move==="quick"||move==="counter"?1.35:1;hero.play("Slash",{speed:sp});await eng.wait(hero.impactTime("Slash",sp))}
      const ang=move==="gale"?[.6,-.7,1.6][i%3]:rand(.3,.9);
      fx.slash(c,{color:pal.slash,size:Math.min(1.9,f.h*(p.last&&move==="gale"?1.25:.95)+.2),ang,flip:i%2===1});
      metal(c,move==="counter"||!!p.last);if(move==="counter")fx.slash(c,{color:0xffffff,size:Math.min(2,f.h*.9+.3),ang:-ang,sweep:1.8,flip:true});
      await ctx.impact(p,{power:move==="gale"?(p.last?1.3:.8):move==="counter"?1.4:1,ono:move==="gale"?(p.last?"斬！！":"唰"):move==="counter"?"反擊！":"斬！",color:pal.slash});
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
  async function finish(){const s=st;st=null;if(!s)return;cleanup(s);hero.pose.position.z=0;ctx.dim(0,.4);ctx.cam("base");
    if(s.melee||s.air)await ctx.retreat();else{hero.setLoop("Idle");hero.play("Idle")}}
  function cleanup(s){if(s.circle)s.circle.remove();if(s.orb)s.orb.remove();if(s.cloud)s.cloud.remove();if(s.glow)s.glow.remove();
    if(s.sword){eng.scene.remove(s.sword);s.sword.children.forEach(m=>m.material.dispose())}}
  return{start,hit,finish,flush,abort(){if(st){cleanup(st);st=null;hero.pose.position.z=0}},
    // 還有累積、還沒播出來的連斬（controller 用來延後扣 Boss 血條；轉階段前先播完）
    pending:()=>!!(st&&st.flow&&(st.queue.length||st.flowing))};
}
