// 戰鬥畫面掛載介面（3D 版）。
// 這個檔案很小、只負責「要不要載入 3D」：three.js 與整個場景（view3d/scene.js）在進入戰鬥時才動態 import，
// 不會拖慢其他頁面。WebGL 不可用或 3D 啟動失敗時退回 view3d/textview.js 的文字畫面。
//
//   const view = mount(container, api)
//     container : 戰鬥畫面中間的 <div id="arena">（HUD、題目卡、選單由 controller 用 DOM 疊在外面）
//     api       : { kind:'monster'|'soul', getState():快照, foes:[...怪物或 Boss 資料表（含 model 代號）], reducedMotion:boolean }
//   view.play(eventName, payload) => Promise   // 播完該事件的動畫才 resolve；controller 會依序 await
//   view.setTimeScale(scale)                   // 魂系指令選單開啟時的慢動作（1 = 正常）；動畫與粒子都會跟著變慢
//   view.resize()
//   view.dispose()
//
// payload 一律帶 s（規則引擎當下的狀態快照）。有傷害的事件另外帶回呼，讓 HUD 在命中瞬間才扣血：
//   hit       : 每一段傷害各一個事件 {skillId, move, index, total, dmg, mhp, last, kill, big}；命中瞬間呼叫 payload.onImpact()
//   playerHit : 玩家受擊 {dmg, hp, kind:'hit'|'guard'|'graze', lethal, source}；命中瞬間呼叫 payload.onImpact()
// 招式流程：skill（起手，含 hitCount/totalDmg）→ hit × N → （faint → heal → enter ／ win）
//
// 事件清單見 EVENTS（docs/魂系模式設計.md 有說明）。各事件的演出寫在 view3d/monsterScene.js 與 view3d/soulScene.js。
import { mountText } from './view3d/textview.js';

export const EVENTS={
  common:["skill","hit","playerHit","faint","heal","win","lose"],
  monster:["enter","gain","hold","chainStart","chainCharge","chainFire","chainStage","chainDone","chainBreak","foeAttack"],
  soul:["bossEnter","playerTurn","atb","miss","quickSlash","windowEnd","bossPhase","enemyTurn","telegraph","parry","counter","deflect","delayRelease","dodge","guard","graze","foeHit","flaskStart","drink","spill","flaskPunish","flaskRefill","ambush","ambushEnd"],
};

// 先用一個丟棄式 canvas 確認 WebGL 能用，不能用就不必下載 three.js
let glProbe=null; // 探測結果快取：整個分頁只建立一次探測用的 context，用完立刻釋放
function webglOK(){if(glProbe!==null)return glProbe;return glProbe=probe()}
function probe(){try{const c=document.createElement("canvas");const gl=c.getContext("webgl2")||c.getContext("webgl");if(!gl)return false;
  const ext=gl.getExtension("WEBGL_lose_context");ext&&ext.loseContext();return true}catch(e){return false}}

export function mount(container,api){
  if(!webglOK())return mountText(container,api);
  let impl=null,dead=false,scale=1;
  container.innerHTML=`<div class="v3-load">戰場準備中…</div>`;
  const ready=import("./view3d/scene.js").then(m=>m.create(container,api))
    .catch(err=>{console.warn("[view3d] 3D 場景無法啟動，改用文字畫面：",err);return dead?null:mountText(container,api)})
    .then(v=>{if(!v)return null;if(dead){v.dispose();return null}impl=v;v.setTimeScale(scale);return v});
  return {
    play(name,payload){if(dead)return Promise.resolve();return ready.then(v=>v&&!dead?v.play(name,payload):undefined)},
    setTimeScale(s){scale=s;impl&&impl.setTimeScale(s)},
    resize(){impl&&impl.resize()},
    skip(){impl&&impl.skip&&impl.skip()},              // 快轉目前這段演出（Boss 登場可點畫面跳過）
    setPaused(v){impl&&impl.setPaused&&impl.setPaused(v)}, // 頁面切到背景時暫停
    dispose(){dead=true;if(impl){try{impl.dispose()}catch(e){}impl=null}container.classList.remove("slowmo");container.innerHTML=""},
  };
}
