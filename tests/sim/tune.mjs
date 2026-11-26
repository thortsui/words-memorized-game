// 調數值用：node tests/sim/tune.mjs '{"SOUL":{"dodgeCost":20},"hp":[..],"atk":[..],"lim":[..]}' [N]
import { SOUL, SOUL_BOSSES } from '../../src/battle/data.js';
const o=JSON.parse(process.argv[2]||'{}'),N=+process.argv[3]||1000;Object.assign(SOUL,o.SOUL||{});
for(const k of ['hp','atk','limitMs','attacks'])if(o[k])SOUL_BOSSES.forEach((b,i)=>b[k]=o[k][i]);
process.argv[2]='none';const { PLAYERS, batch }=await import('./soul-sim-lib.mjs');
for(const [n,p] of Object.entries(PLAYERS)){const r=batch(p,{},N);console.log(n.padEnd(20),String(r['win%']).padStart(4)+'%','kills',r.kills,'dist',r.dist,'eT/boss',r.eTurnsPerBoss,'parry',r.parry,'dodge',r.dodge,'guard',r.guard,'graze',r.graze,'hit',r.hit,'d',r.avgD,'weak',r.weak,'asl',r.assault,'knock',r.knock,'amb',r.ambush,'sec',r.sec,'eT',r.eTurns)}
