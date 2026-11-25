// 3D 戰鬥畫面的進入點（由 view3d.js 動態 import，three.js 也在這個 chunk 裡）。
// 建立引擎與特效，依 api.kind 選場景，再把場景的事件處理器包成 view 介面。
import { createEngine } from './engine.js';
import { createFx } from './fx.js';
import { createMonsterScene } from './monsterScene.js';
import { createSoulScene } from './soulScene.js';
import { mountText } from './textview.js';

export function create(container,api){
  const soul=api.kind==="soul";
  const eng=createEngine(container,{reducedMotion:!!api.reducedMotion});
  let S,fx;
  try{fx=createFx(eng,{soul});S=(soul?createSoulScene:createMonsterScene)(eng,fx,api)}
  catch(err){eng.dispose();throw err} // 交給 view3d.js 退回文字畫面
  eng.wrap.classList.add(soul?"soul":"cute");
  eng.onQuality.push(q=>S.onQuality&&S.onQuality(q));
  eng.start();
  // 開場先等主角與第一個對手的模型（顯示載入進度）；超過 12 秒才用替身開打，模型到了再熱替換
  const tip=document.createElement("div");tip.className="v3-loading";tip.innerHTML="<b>載入模型中… 0%</b><span>第一次進入需要下載模型，請稍候</span><i><u></u></i>";eng.wrap.appendChild(tip);
  const tick=setInterval(()=>{const p=Math.round((S.progress?S.progress():0)*100);tip.firstChild.textContent=`載入模型中… ${p}%`;tip.querySelector("u").style.width=p+"%"},150);
  const first=Promise.race([S.ready,new Promise(r=>setTimeout(r,12000))]).then(()=>{clearInterval(tick);tip.classList.add("done");setTimeout(()=>tip.remove(),350)});
  let dead=false,text=null; // text：WebGL context 遺失且無法恢復時改用的文字畫面
  eng.onLost.push(()=>{setTimeout(()=>{if(dead||text||!eng.lost)return;console.warn("[view3d] WebGL context 遺失且無法恢復，改用文字畫面");
    clearInterval(tick);try{eng.dispose()}catch(e){}text=mountText(container,api)},3000)});
  return {
    async play(name,payload){if(dead)return;if(text)return text.play(name,payload);await first;if(dead)return;if(text)return text.play(name,payload);
      const h=S.handlers[name],p={...(payload||{})},orig=p.onImpact;let fired=false;
      // onImpact 保證只呼叫一次；就算演出中途出錯或畫面被關掉，HUD 也會被更新
      p.onImpact=()=>{if(fired)return;fired=true;if(orig&&!dead)orig()};
      if(h){let tm;const guard=new Promise(r=>{tm=setTimeout(r,15000)}); // 保險：演出卡住時不要讓整場戰鬥停住
        try{await Promise.race([Promise.resolve(h(p)),guard])}catch(err){console.warn("[view3d] 事件 "+name+" 演出失敗：",err)}clearTimeout(tm)}
      eng.fast=1;if(orig)p.onImpact()},
    // 快轉目前這段演出（到這個事件播完為止）
    skip(){eng.fast=10},
    setPaused(v){eng.paused=!!v},
    setTimeScale(s){if(text)return text.setTimeScale(s);eng.timeScale=Math.max(.05,s);container.classList.toggle("slowmo",s<1);S.setSlow&&S.setSlow(s<.5)},
    resize(){eng.resize()},
    stats(){return{fps:eng.fps,dpr:eng.dpr,quality:eng.quality,calls:eng.renderer.info.render.calls,triangles:eng.renderer.info.render.triangles,particles:fx.particleCount}},
    dispose(){if(dead)return;dead=true;clearInterval(tick);if(text){text.dispose();return}container.classList.remove("slowmo");eng.dispose()},
  };
}
