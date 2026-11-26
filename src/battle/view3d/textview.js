// 純文字戰鬥畫面：WebGL 不可用（或 3D 場景啟動失敗）時的退回方案。
// 介面與 3D 版相同：mountText(container, api) → { play, setTimeScale, resize, dispose }
const wait=ms=>new Promise(r=>setTimeout(r,ms));

export function mountText(container,api){
  let scale=1,dead=false;
  const fast=api.reducedMotion?.15:1;
  container.innerHTML=`<div class="tview"><div class="tv-foe"></div><div class="tv-log" aria-live="polite"></div><div class="tv-note">這台裝置無法顯示 3D 場景，改用文字戰鬥畫面</div></div>`;
  const foe=container.querySelector(".tv-foe"),log=container.querySelector(".tv-log");
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
    telegraph:async p=>{line(p.kind==="danger"?`！！！ 必殺：${p.move}`:p.kind==="dash"?`！！ 突進：${p.move}`:p.kind==="combo"?`！ ${p.move}（${p.seg+1}/${p.segs}）`:`！ ${p.boss.name} 蓄力：${p.move}`,"bad");await W(p.kind==="combo"&&p.seg?200:420)},
    parry:async p=>{line(p.chain?"彈開！":"彈反！","big good");await W(300)},
    deflect:async()=>{},flaskStart:async()=>{line("拿出藥壺…","good");await W(200)},drink:async p=>{p.onImpact&&p.onImpact();line(`喝下藥壺 +${p.amount} HP`,"good");await W(300)},spill:async()=>{line("藥灑了…","bad");await W(250)},
    flaskPunish:async()=>{line("Boss 趁機逼近！","bad")},flaskRefill:async()=>{line("藥壺 +1","good")},ambush:async p=>{line(`！！ 突襲：${p.move}`,"big bad");await W(300)},ambushEnd:async()=>{line("撐過突襲，繼續攻擊！","good");await W(150)},delayRelease:async()=>{line("　出手了！","bad")},
    dodge:async()=>{line("翻滾閃避。","good");await W(300)},
    guard:async()=>{line("耐力不足，勉強格擋。","bad");await W(250)},
    graze:async()=>{line("太慢了，被擦傷。","bad");await W(250)},
    foeHit:async p=>{line(p.timeout?"來不及了！":"沒有躲開！","bad");await W(300)},
    faint:async p=>{line(`${(p.monster||p.boss).name} 倒下了！`,"big good");await W(700)},
    heal:async p=>{p.onImpact&&p.onImpact();line(`回復 ${p.amount} HP`,"good");await W(300)},
    win:async()=>{line("勝利！","big good");await W(500)},
    lose:async()=>{line("你倒下了…","big bad");await W(500)},
  };
  return {
    play(name,payload){if(dead)return Promise.resolve();const h=H[name];return h?Promise.resolve(h(payload||{})):Promise.resolve()},
    setTimeScale(s){scale=s;container.classList.toggle("slowmo",s<1)},
    resize(){},skip(){},setPaused(){},
    dispose(){dead=true;container.classList.remove("slowmo");container.innerHTML=""},
  };
}
