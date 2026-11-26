// 用專案的規則引擎（src/battle/soul.js，唯讀匯入）跑蒙地卡羅，評估平衡。
// 這不是實機遊玩：沒有畫面與朗讀，只有規則。玩家模型＝作答秒數分布＋正確率＋出招策略＋是否會在延遲攻擊鎖住時亂點。
// 另外用「時間模型」估一場要打多久（作答時間＋各種演出的固定秒數），比較改版前後整場長度用；數值是估計，不是實測。
import { createSoulBattle } from '../../src/battle/soul.js';
import { SOUL, SOUL_BOSSES } from '../../src/battle/data.js';
import { RAW } from '../../src/data/no307.js';
const pool = RAW.map((r, i) => ({ id: 'b' + i, en: r[0], pos: r[1], zh: r[2], ex: r[3] }));
const U = (a, b) => () => a + Math.random() * (b - a);
const smart = (E) => { const s = E.state; if (s.atb >= 3) return 3; if (s.atkLeft <= 0) return s.atb >= 2 ? 2 : s.atb >= 1 ? 1 : 0; return 0 };
const rndCmd = (E) => { const c = E.commands().filter(c => c.ready).map(c => c.k); c.push(0); return c[Math.floor(Math.random() * c.length)] };
// hasty：延遲攻擊鎖住期間會亂點（每點一下被加 flinchMs）；其他玩家看得到鎖定倒數，會等解鎖
export const PLAYERS = {
  '高手 0.45–0.85s 100%': { think: U(450, 850), acc: 1, cmd: smart, read: .9, menu: 350 },
  '熟練 1.2–2.0s 90%': { think: U(1200, 2000), acc: .9, cmd: smart, read: 1.2, menu: 700 },
  '普通 2–3s 75%': { think: U(2000, 3000), acc: .75, cmd: smart, read: 1.6, menu: 1100 },
  '偏慢 3–4.5s 60%': { think: U(3000, 4500), acc: .6, cmd: smart, read: 2, menu: 1500 },
  '很差 3–6s 40%': { think: U(3000, 6000), acc: .4, cmd: smart, read: 2, menu: 1800 },
  '亂點 0.3–0.9s 25%': { think: U(300, 900), acc: .25, cmd: rndCmd, hasty: true, read: .4, menu: 300 },
  '亂點＋聰明出招 25%': { think: U(300, 900), acc: .25, cmd: smart, hasty: true, read: .4, menu: 300 },
};
// 演出的固定秒數（對照 controller.js／soulScene.js 的等待時間估的）
export const TM = { drink: 1.6, ambush: 1.2, enter: 5.5, firstEnter: 3, phase: 2.5, pturn: 1, atb: .2, wrongHold: 1.1, menu: .7, quick: 1.5, slash: 1.7, gale: 2.7, big: 3.3,
  eturn: .6, tele: .75, teleChain: .35, strike: .55, chainGap: .3, autoNext: .6, counter: 1.4, deflect: .4 };
// 延遲攻擊：t＝從題目出現算起的思考時間。會等的人在鎖住期間讀題，解鎖後 ms＝t−鎖定（至少 0.25 秒反應）
function dodgeTime(pl, d) {
  const t = pl.think(); if (!d.lockMs) return { ms: t, early: 0, wall: t };
  if (pl.hasty && t < d.lockMs) { const ms = 250 + Math.random() * 300; return { ms, early: 1, wall: d.lockMs + ms } }
  const ms = Math.max(250, t - d.lockMs); return { ms, early: 0, wall: d.lockMs + ms };
}
// 喝藥策略：聰明的玩家 HP 低於 drinkAt（預設 40%）才喝；亂點的玩家在指令列隨機按（rndCmd 會按到藥壺）
const wantDrink = (pl, E) => { const s = E.state, c = E.commands().find(c => c.flask); return c && c.ready && pl.cmd !== rndCmd && s.hp < s.hpMax * (pl.drinkAt ?? .4) };
export function one(pl, opt = {}) {
  const E = createSoulBattle({ pool, mode: 'en2zh' }); E.start(); const B = E.state;
  const st = { q: 0, eturns: 0, eturnsPerBoss: [0, 0, 0, 0, 0], attacks: 0, minSta: 100, guard: 0, parry: 0, dodge: 0, graze: 0, hit: 0, dSum: 0, dN: 0, sec: TM.firstEnter, kinds: {}, chainHits: 0, dangerHit: 0, flinch: 0, hpLost: 0, drinks: 0, spills: 0, ambush: 0, ambushHit: 0, punish: 0, knock: 0, weak: 0, assaultN: 0 };
  let guardLoop = 0, lastKills = 0, lastPhase = 0;
  const after = () => { if (B.kills > lastKills) { st.sec += TM.enter * (B.kills - lastKills); lastKills = B.kills; lastPhase = 0 } if (B.bphase > lastPhase) { st.sec += TM.phase * (B.bphase - lastPhase); lastPhase = B.bphase } };
  const count = evs => { for (const e of evs) { if (e.type === 'drink') st.drinks++; if (e.type === 'spill') st.spills++; if (e.type === 'ambush') { st.ambush++; st.sec += TM.ambush } if (e.type === 'flaskPunish') st.punish++; if (e.type === 'knockdown') { st.knock++; st.sec += TM.knock || 1.2 } if (e.type === 'weakBreak') { st.weak++; st.sec += 2.7 } if (e.type === 'skill' && !e.assault) st.sec += (e.hitCount || 0) * .35 + .6; if (e.type === 'assault') { st.assaultN++; st.sec += 1 } } };
  // 一題閃避（敵人回合與突襲共用）
  const dodgeOne = d => { st.attacks++; st.q++; st.kinds[d.kind] = (st.kinds[d.kind] || 0) + 1;
    st.sec += d.seg > 0 || d.kind === 'ambush' ? TM.teleChain : TM.tele;
    const { ms, early, wall } = dodgeTime(pl, d); st.flinch += early; const ok = Math.random() < pl.acc; const hp0 = B.hp;
    let evs;
    if (ms > d.limitMs) { st.sec += ((d.lockMs || 0) + d.limitMs) / 1000; evs = E.answerDodge(false, d.limitMs + 1, { timeout: true }) }
    else { st.sec += wall / 1000; evs = E.answerDodge(ok, ms, { early }) }
    after(); count(evs); st.sec += TM.strike;
    for (const e of evs) if (['guard', 'dodge', 'graze', 'parry'].includes(e.type)) st[e.type]++; if (evs.some(e => e.type === 'foeHit')) st.hit++;
    if (evs.some(e => e.type === 'counter')) st.sec += TM.counter; if (evs.some(e => e.type === 'deflect')) st.sec += TM.deflect;
    const hurt = B.hp < hp0; st.hpLost += hp0 - B.hp; if (hurt && d.chain) st.chainHits++; if (hurt && d.danger) st.dangerHit++; if (hurt && d.kind === 'ambush') st.ambushHit++;
    // 連擊段之間、突襲之後不停；整招結束：沒受傷自動接下一招，受傷要看答案再按「繼續」
    st.sec += d.chain || d.kind === 'ambush' ? TM.chainGap : hurt || !ok ? pl.read : TM.autoNext;
    st.minSta = Math.min(st.minSta, B.stamina) };
  let inTurn = false;
  while (!B.over && guardLoop++ < 20000) {
    const ph = B.phase;
    if (ph === 'pturn') { if (!inTurn) { inTurn = true; st.sec += TM.pturn }
      const q = E.nextAttackQuestion(); if (!q) { E.startEnemyTurn(); continue }
      const t = pl.think(); if (t >= q.leftMs) { st.sec += q.leftMs / 1000; count(E.attackTimeout()); continue }
      const ok = Math.random() < pl.acc; st.q++; st.sec += t / 1000;
      const evs = E.answerAttack(ok, t); after(); count(evs);
      st.sec += ok ? TM.atb : TM.wrongHold; if (evs.some(e => e.type === 'quickSlash')) st.sec += TM.quick }
    else if (ph === 'cmd') { const ready = E.commands().some(c => c.ready); const hes = ready ? (pl.menu ?? 700) * (.6 + Math.random() * .8) : 0; if (ready) st.sec += hes / 1000;
      const k = wantDrink(pl, E) ? 4 : 0; const evs = E.command(k, { ms: hes }); after(); count(evs);
      if (k === 1 || k === 2 || k === 3) st.sec += k === 1 ? TM.slash : k === 2 ? TM.gale : TM.big; if (k === 4) st.sec += TM.drink }
    else if (ph === 'flask') { const q = E.flaskQuestion(); const t = pl.think(); const ok = Math.random() < pl.acc; st.q++;
      if (t >= q.leftMs) { st.sec += q.leftMs / 1000; count(E.answerFlask(false, q.leftMs, { timeout: true })) } else { st.sec += t / 1000; count(E.answerFlask(ok, t)) } after() }
    else if (ph === 'enemy') { const amb = B.enemy && B.enemy.ambush; if (!amb) { inTurn = false; st.eturns++; st.eturnsPerBoss[B.mi]++; st.sec += TM.eturn; st.dSum += E.difficulty().d; st.dN++ }
      let d; while (!B.over && B.phase === 'enemy' && (d = E.nextDodge())) dodgeOne(d);
      if (!B.over && B.phase === 'enemy') { count(E.startPlayerTurn()) } }
    else if (ph === 'slash') { const q = E.nextSlash(); const t = pl.think() * .85; const ok = Math.random() < Math.min(1, pl.acc + .1); st.q++;
      if (t > q.limitMs) { st.sec += q.limitMs / 1000; count(E.answerSlash(false, q.limitMs, { timeout: true })) } else { st.sec += t / 1000 + .45; count(E.answerSlash(ok, t)) } after() }
    else if (ph === 'perk') { const o = B.offer; const pick = pl.perk ? pl.perk(o) : o[Math.floor(Math.random() * o.length)]; count(E.choosePerk(pick)); st.sec += 3 }
    else if (ph === 'assault') { const q = E.nextAssault(); const t = pl.think(); const ok = Math.random() < pl.acc; st.q++;
      if (t > q.limitMs) { st.sec += q.limitMs / 1000; count(E.answerAssault(false, q.limitMs, { timeout: true })) } else { st.sec += t / 1000 + 1.5; count(E.answerAssault(ok, t)) } after() }
    else break;
  }
  return { win: B.over === "win", kills: B.kills, endPhase: B.over || B.phase, endHp: B.hp, ...st };
}
export function batch(pl, opt, N = 2000) {
  const a = { win: 0, kills: 0, q: 0, eturns: 0, attacks: 0, minSta: 0, guard: 0, parry: 0, dodge: 0, graze: 0, hit: 0, killsDist: [0, 0, 0, 0, 0, 0], et: [0, 0, 0, 0, 0], d: 0, sec: 0, winSec: 0, chainHits: 0, dangerHit: 0, flinch: 0, hpLost: 0, hurtWins: 0, drinks: 0, spills: 0, ambush: 0, ambushHit: 0, punish: 0, knock: 0, weak: 0, assaultN: 0 };
  for (let i = 0; i < N; i++) { const r = one(pl, opt); a.win += r.win; if (r.win) { a.winSec += r.sec; if (r.hpLost > 0) a.hurtWins++ } a.kills += r.kills; a.q += r.q; a.eturns += r.eturns; a.attacks += r.attacks; a.minSta += r.minSta; a.sec += r.sec;
    for (const k of ['guard', 'parry', 'dodge', 'graze', 'hit', 'chainHits', 'dangerHit', 'flinch', 'hpLost', 'drinks', 'spills', 'ambush', 'ambushHit', 'punish', 'knock', 'weak', 'assaultN']) a[k] += r[k]; a.killsDist[r.kills]++; r.eturnsPerBoss.forEach((x, i) => a.et[i] += x); a.d += r.dN ? r.dSum / r.dN : 0 }
  const f = x => +(x / N).toFixed(2);
  return { 'win%': Math.round(a.win / N * 100), kills: f(a.kills), dist: a.killsDist.map(x => Math.round(x / N * 100)).join('/'), q: f(a.q), eTurns: f(a.eturns), eTurnsPerBoss: a.et.map(f).join('/'), atk: f(a.attacks), parry: f(a.parry), dodge: f(a.dodge), guard: f(a.guard), graze: f(a.graze), hit: f(a.hit), chainHits: f(a.chainHits), dangerHit: f(a.dangerHit), flinch: f(a.flinch), hpLost: f(a.hpLost), drinks: f(a.drinks), spills: f(a.spills), ambush: f(a.ambush), ambushHit: f(a.ambushHit), punish: f(a.punish), knock: f(a.knock), weak: f(a.weak), assault: f(a.assaultN), hurtWin: a.win ? Math.round(a.hurtWins / a.win * 100) : null, minSta: f(a.minSta), avgD: f(a.d), sec: Math.round(a.sec / N), winSec: a.win ? Math.round(a.winSec / a.win) : null } }
export function table(title, opt, N = 2000) { console.log('\n### ' + title); const out = {}; for (const [n, p] of Object.entries(PLAYERS)) { const r = batch(p, opt, N); out[n] = r; console.log(n.padEnd(22), JSON.stringify(r)) } return out }

const base = JSON.parse(JSON.stringify({ SOUL, B: SOUL_BOSSES }));
export const reset = () => { Object.assign(SOUL, base.SOUL); SOUL_BOSSES.forEach((b, i) => Object.assign(b, JSON.parse(JSON.stringify(base.B[i])))) };
