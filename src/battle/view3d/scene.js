// 3D 戰鬥畫面的進入點（由 view3d.js 動態 import，three.js 也在這個 chunk 裡）。
// 建立引擎與特效，依 api.kind 選場景，再把場景的事件處理器包成 view 介面。
import { createEngine } from './engine.js';
import { createFx } from './fx.js';
import { createMonsterScene } from './monsterScene.js';
import { createSoulScene } from './soulScene.js';

export function create(container,api){
  const soul=api.kind==="soul";
  const eng=createEngine(container,{reducedMotion:!!api.reducedMotion});
  let S,fx;
  try{fx=createFx(eng,{soul});S=(soul?createSoulScene:createMonsterScene)(eng,fx,api)}
  catch(err){eng.dispose();throw err} // 交給 view3d.js 退回文字畫面
  eng.wrap.classList.add(soul?"soul":"cute");
  eng.onQuality.push(q=>S.onQuality&&S.onQuality(q));
  eng.start();
  // 主角模型載入完（最多等 2.5 秒）才開始播第一個事件，避免替身閃一下又換掉
  const first=Promise.race([S.ready,new Promise(r=>setTimeout(r,2500))]);
  let dead=false;
  return {
    async play(name,payload){if(dead)return;await first;if(dead)return;
      const h=S.handlers[name],p={...(payload||{})},orig=p.onImpact;let fired=false;
      // onImpact 保證只呼叫一次；就算演出中途出錯或畫面被關掉，HUD 也會被更新
      p.onImpact=()=>{if(fired)return;fired=true;if(orig&&!dead)orig()};
      if(h){let tm;const guard=new Promise(r=>{tm=setTimeout(r,15000)}); // 保險：演出卡住時不要讓整場戰鬥停住
        try{await Promise.race([Promise.resolve(h(p)),guard])}catch(err){console.warn("[view3d] 事件 "+name+" 演出失敗：",err)}clearTimeout(tm)}
      if(orig)p.onImpact()},
    setTimeScale(s){eng.timeScale=Math.max(.05,s);container.classList.toggle("slowmo",s<1);S.setSlow&&S.setSlow(s<.5)},
    resize(){eng.resize()},
    stats(){return{fps:eng.fps,dpr:eng.dpr,quality:eng.quality,calls:eng.renderer.info.render.calls,triangles:eng.renderer.info.render.triangles,particles:fx.particleCount}},
    dispose(){if(dead)return;dead=true;container.classList.remove("slowmo");eng.dispose()},
  };
}
