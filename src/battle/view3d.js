// 戰鬥畫面掛載介面。
// 目前是「暫時的純文字畫面」：只把事件寫成文字記錄，讓整個流程可玩、可驗證。
// 之後由 Three.js 3D 場景取代這個檔案的實作，介面不變：
//
//   const view = mount(container, api)
//     container : 戰鬥畫面中間的 <div id="arena">（HUD、題目卡、選單由 controller 用 DOM 疊在外面）
//     api       : { kind:'monster'|'soul', getState():快照, foes:[...怪物或 Boss 資料表（含 model 代號）], reducedMotion:boolean }
//   view.play(eventName, payload) => Promise   // 播完該事件的動畫才 resolve；controller 會依序 await
//   view.setTimeScale(scale)                   // 魂系指令選單開啟時的慢動作（1 = 正常）
//   view.resize()
//   view.dispose()
//
// payload 一律帶 s（規則引擎當下的狀態快照）。有傷害的事件另外帶回呼，讓 HUD 在命中瞬間才扣血：
//   hit       : 每一段傷害各一個事件 {skillId, move, index, total, dmg, mhp, last, kill, big}；命中瞬間呼叫 payload.onImpact()
//   playerHit : 玩家受擊 {dmg, hp, kind:'hit'|'guard'|'graze', lethal, source}；命中瞬間呼叫 payload.onImpact()
// 招式流程：skill（起手，含 hitCount/totalDmg）→ hit × N → （faint → heal → enter ／ win）
//
// 事件清單見 EVENTS（docs/魂系模式設計.md 有說明）。
export const EVENTS={
  common:["skill","hit","playerHit","faint","heal","win","lose"],
  monster:["enter","gain","hold","chainStart","chainCharge","chainFire","chainStage","chainDone","chainBreak","foeAttack"],
  soul:["bossEnter","playerTurn","atb","miss","quickSlash","windowEnd","bossPhase","enemyTurn","telegraph","parry","counter","dodge","guard","graze","foeHit"],
};
const wait=ms=>new Promise(r=>setTimeout(r,ms));

export function mount(container,api){
  let scale=1,dead=false;
  const fast=api.reducedMotion?.15:1;
  container.innerHTML=`<div class="tview"><div class="tv-foe" id="tv-foe"></div><div class="tv-log" id="tv-log" aria-live="polite"></div><div class="tv-note">暫時的文字戰鬥畫面・3D 場景製作中</div></div>`;
  const foe=container.querySelector("#tv-foe"),log=container.querySelector("#tv-log");
  const line=(t,cls)=>{if(dead)return;const d=document.createElement("div");d.className="tv-l "+(cls||"");d.textContent=t;log.appendChild(d);while(log.children.length>7)log.firstChild.remove()};
  const W=ms=>wait(ms*fast/Math.max(.2,scale));
  const start=async(p,label)=>{line(`▶ ${label}`,p.big?"big":"");await W(p.big?420:220)};
  const hurt=async p=>{p.onImpact&&p.onImpact();line(`　你受到 -${p.dmg}`,"dmg bad");await W(260)};
  const H={
    enter:async p=>{foe.textContent=`${p.monster.name}　Lv.${p.monster.lv}`;line(`${p.monster.name} 出現了！`);await W(500)},
    bossEnter:async p=>{foe.textContent=`${p.boss.name}　Lv.${p.boss.lv}`;line(`${p.boss.name} 擋在前方。`,"big");await W(700)},
    gain:async p=>{line(`能量 +${p.amount}`,"good");await W(120)},
    atb:async()=>{line("ATB +1","good");await W(120)},
    miss:async()=>{line("答錯，失去節奏。","bad");await W(150)},
    hold:async()=>{},
    chainStart:async p=>{line(`連招「${p.skill.name}」蓄力開始`,"good");await W(300)},
    chainCharge:async p=>{line(`蓄力 ${p.stage} / ${p.total}`,"good");await W(300)},
    chainFire:async p=>{line(`發動「${p.skill.name}」！`,"big");await W(400)},
    chainDone:async()=>{line("連招完成！","good");await W(200)},
    chainBreak:async()=>{line("連招中斷！","bad");await W(300)},
    skill:p=>start(p,p.name),
    hit:async p=>{p.onImpact&&p.onImpact();line(`　命中 -${p.dmg}${p.kill?"（擊倒）":""}`,"dmg");await W(160)},
    playerHit:hurt,
    chainStage:async p=>{line(`第 ${p.stage} / ${p.total} 式`,"good");await W(120)},
    quickSlash:p=>start(p,"迅擊"),
    counter:p=>start(p,"反擊"),
    foeAttack:async p=>{line(`${p.monster.name} 使出 ${p.move}`,"bad");await W(380)},
    playerTurn:async()=>{line("—— 你的回合 ——");await W(200)},
    windowEnd:async()=>{line("攻擊時間結束。");await W(250)},
    enemyTurn:async p=>{line(`—— ${p.boss.name} 的回合（${p.total} 次攻擊）——`,"bad");await W(350)},
    bossPhase:async p=>{line(`${p.boss.name} 進入第 ${p.phase+1} 階段：${p.info.name}`,"big bad");await W(800)},
    telegraph:async p=>{line(`！ ${p.boss.name} 蓄力：${p.move}`,"bad");await W(420)},
    parry:async()=>{line("彈反！","big good");await W(300)},
    dodge:async()=>{line("翻滾閃避。","good");await W(300)},
    guard:async p=>{line("耐力不足，勉強格擋。","bad");await W(250)},
    graze:async p=>{line("太慢了，被擦傷。","bad");await W(250)},
    foeHit:async p=>{line(p.timeout?"來不及了！":"沒有躲開！","bad");await W(300)},
    faint:async p=>{line(`${(p.monster||p.boss).name} 倒下了！`,"big good");await W(700)},
    heal:async p=>{line(`回復 ${p.amount} HP`,"good");await W(300)},
    win:async()=>{line("勝利！","big good");await W(500)},
    lose:async()=>{line("你倒下了…","big bad");await W(500)},
  };
  return {
    play(name,payload){if(dead)return Promise.resolve();const h=H[name];return h?Promise.resolve(h(payload||{})):Promise.resolve()},
    setTimeScale(s){scale=s;container.classList.toggle("slowmo",s<1)},
    resize(){},
    dispose(){dead=true;container.innerHTML=""},
  };
}
