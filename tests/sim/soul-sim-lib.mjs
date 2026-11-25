// （由 tests/playtest/mobile-soul/sim.mjs 複製而來；規則已內建每題最低耗時、答錯扣時、擊倒回復，不再用 opt 模擬）
// 用專案的規則引擎（src/battle/soul.js，唯讀匯入）跑蒙地卡羅，評估平衡與調整建議。
// 這不是實機遊玩：沒有畫面與朗讀，只有規則。玩家模型＝作答秒數分布＋正確率＋出招策略。
import { createSoulBattle } from '../../src/battle/soul.js';
import { SOUL, SOUL_BOSSES } from '../../src/battle/data.js';
import { RAW } from '../../src/data/no307.js';
const pool = RAW.map((r, i) => ({ id: 'b' + i, en: r[0], pos: r[1], zh: r[2], ex: r[3] }));
const U = (a, b) => () => a + Math.random() * (b - a);
const smart = (E) => { const s = E.state; if (s.atb >= 3) return 3; if (s.atkLeft <= 0) return s.atb >= 2 ? 2 : s.atb >= 1 ? 1 : 0; return 0 };
const rndCmd = (E) => { const c = E.commands().filter(c => c.ready).map(c => c.k); c.push(0); return c[Math.floor(Math.random() * c.length)] };
export const PLAYERS = {
  '高手 0.45–0.85s 100%': { think: U(450, 850), acc: 1, cmd: smart },
  '熟練 1.2–2.0s 90%': { think: U(1200, 2000), acc: .9, cmd: smart },
  '普通 2–3s 75%': { think: U(2000, 3000), acc: .75, cmd: smart },
  '偏慢 3–4.5s 60%': { think: U(3000, 4500), acc: .6, cmd: smart },
  '很差 3–6s 40%': { think: U(3000, 6000), acc: .4, cmd: smart },
  '亂點 0.3–0.9s 25%': { think: U(300, 900), acc: .25, cmd: rndCmd },
  '亂點＋聰明出招 25%': { think: U(300, 900), acc: .25, cmd: smart },
};
// opt：penaltyMs 攻擊回合答錯多扣的攻擊時間；minCostMs 每題至少消耗的攻擊時間；maxQ 每回合最多幾題
export function one(pl, opt = {}) {
  const E = createSoulBattle({ pool, mode: 'en2zh' }); E.start(); const B = E.state;
  const st = { q: 0, eturns: 0, eturnsPerBoss: [0, 0, 0, 0, 0], attacks: 0, minSta: 100, guard: 0, parry: 0, dodge: 0, graze: 0, hit: 0, dSum: 0, dN: 0 };
  let guardLoop = 0, lastKills = 0;
  while (!B.over && guardLoop++ < 5000) {
    if (B.kills > lastKills) { lastKills = B.kills; B.hp = Math.min(100, B.hp + (opt.healExtra || 0)) }
    if (B.phase === 'pturn') { let nq = 0;
      while (B.phase === 'pturn' && !B.over) {
        if (opt.maxQ && nq >= opt.maxQ) { const q = E.nextAttackQuestion(); if (q) E.attackTimeout(); else E.startEnemyTurn(); break }
        const q = E.nextAttackQuestion(); if (!q) { E.startEnemyTurn(); break }
        const t = pl.think(); if (t >= q.leftMs) { E.attackTimeout(); break }
        const ok = Math.random() < pl.acc; nq++; st.q++;
        const before = B.atkLeft; E.answerAttack(ok, t);
        // 額外時間成本（規則引擎沒有這個參數，直接扣狀態來模擬）
        if (!B.over && B.phase === 'cmd') { const extra = (ok ? 0 : (opt.penaltyMs || 0)) + Math.max(0, (opt.minCostMs || 0) - t); if (extra) B.atkLeft = Math.max(0, B.atkLeft - extra) }
        while (B.phase === 'cmd' && !B.over) { const k = pl.cmd(E); E.command(k); if (k === 0) break; if (B.phase === 'pturn') nq = 0 }
      }
    } else if (B.phase === 'enemy') { st.eturns++; st.eturnsPerBoss[B.mi]++; let d;
      st.dSum += E.difficulty().d; st.dN++;
      while (!B.over && (d = E.nextDodge())) { st.attacks++; st.q++; const t = pl.think(); const ok = Math.random() < pl.acc; const hp0 = B.hp, sta0 = B.stamina, par0 = B.parries;
        const evs = t > d.limitMs ? E.answerDodge(false, d.limitMs + 1, { timeout: true }) : E.answerDodge(ok, t);
        for (const e of evs) if (st[e.type] !== undefined && ['guard', 'dodge', 'graze', 'parry'].includes(e.type)) st[e.type]++; if (evs.some(e => e.type === 'foeHit')) st.hit++;
        st.minSta = Math.min(st.minSta, B.stamina); if (B.phase === 'pturn') break }
      if (!B.over && B.phase === 'enemy') E.startPlayerTurn();
    } else break;
  }
  return { win: B.over === 'win', kills: B.kills, ...st };
}
export function batch(pl, opt, N = 2000) { const a = { win: 0, kills: 0, q: 0, eturns: 0, attacks: 0, minSta: 0, guard: 0, parry: 0, dodge: 0, graze: 0, hit: 0, killsDist: [0, 0, 0, 0, 0, 0], et: [0, 0, 0, 0, 0], d: 0 };
  for (let i = 0; i < N; i++) { const r = one(pl, opt); a.win += r.win; a.kills += r.kills; a.q += r.q; a.eturns += r.eturns; a.attacks += r.attacks; a.minSta += r.minSta; for (const k of ['guard', 'parry', 'dodge', 'graze', 'hit']) a[k] += r[k]; a.killsDist[r.kills]++; r.eturnsPerBoss.forEach((x, i) => a.et[i] += x); a.d += r.dN ? r.dSum / r.dN : 0 }
  const f = x => +(x / N).toFixed(2);
  return { 'win%': Math.round(a.win / N * 100), kills: f(a.kills), dist: a.killsDist.map(x => Math.round(x / N * 100)).join('/'), q: f(a.q), eTurns: f(a.eturns), eTurnsPerBoss: a.et.map(f).join('/'), atk: f(a.attacks), parry: f(a.parry), dodge: f(a.dodge), guard: f(a.guard), graze: f(a.graze), hit: f(a.hit), minSta: f(a.minSta), avgD: f(a.d) } }
export function table(title, opt) { console.log('\n### ' + title); for (const [n, p] of Object.entries(PLAYERS)) { const r = batch(p, opt); console.log(n.padEnd(22), JSON.stringify(r)) } }

const base = JSON.parse(JSON.stringify({ SOUL, B: SOUL_BOSSES }));
export const reset = () => { Object.assign(SOUL, base.SOUL); SOUL_BOSSES.forEach((b, i) => Object.assign(b, JSON.parse(JSON.stringify(base.B[i])))) };
