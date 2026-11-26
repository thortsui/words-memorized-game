// 打怪模式規則狀態機（回合制）。不碰 DOM、不計時：作答秒數由外部傳入。
// 每個動作回傳「事件陣列」，控制器依序交給畫面播放；每個事件都帶 s（當下狀態快照）。
// 事件切得很細，方便動畫逐段對接：招式起手（skill）、每一段傷害（hit）、連招每一階段（chainStage）、
// 怪物出手（foeAttack）與玩家受擊（playerHit）、登場／倒下／回復／勝敗都各自獨立。
import { MON, SKILLS, MAXEN, PLAYER_HP, HEAL_ON_KILL, QUESTION_MS } from './data.js';
import { shuffle } from '../core/grading.js';

export const comboMult=combo=>1+Math.min(.5,.1*Math.max(0,combo-1));
export const energyGain=sec=>Math.max(1,Math.min(10,Math.round(10-sec)));

// typeLimit(w,k)：中翻英・填空的時限（思考時間乘 k）；連招蓄力題改用它
export function createMonsterBattle({pool,mode,rng=Math.random,onEvent,typeLimit=null}){
  const B={kind:"monster",mode,pool,queue:shuffle(pool),hp:PLAYER_HP,en:0,mi:0,mhp:MON[0].hp,combo:0,best:0,fast:99,right:0,n:0,wrong:[],kills:0,heals:0,chain:null,phase:"intro",w:null,over:null};
  const snap=()=>({hp:B.hp,hpMax:PLAYER_HP,en:B.en,enMax:MAXEN,mi:B.mi,mhp:B.mhp,mhpMax:MON[B.mi].hp,combo:B.combo,right:B.right,n:B.n,kills:B.kills,heals:B.heals,
    chain:B.chain?{id:B.chain.s.id,name:B.chain.s.name,stage:B.chain.stage,total:B.chain.s.chain.length}:null});
  const mk=(out)=>(type,p)=>{const e={type,...p,s:snap()};out.push(e);onEvent&&onEvent(e);return e};

  // 一招：先發 skill（起手），再逐段發 hit。回傳是否擊倒。
  function hitSkill(ev,skillId,move,name,base,mult,extra){const dmgs=base.map(x=>Math.round(x*mult)),total=dmgs.length,target=MON[B.mi].id;
    ev("skill",{skillId,move,name,hitCount:total,totalDmg:dmgs.reduce((a,b)=>a+b,0),mult,target,...extra});
    dmgs.forEach((dmg,i)=>{const before=B.mhp;B.mhp=Math.max(0,B.mhp-dmg);ev("hit",{skillId,move,index:i,total,dmg,mhp:B.mhp,mhpMax:MON[B.mi].hp,last:i===total-1,kill:before>0&&B.mhp<=0,big:!!(extra&&extra.big),target})});
    return B.mhp<=0}
  function faint(ev){const m=MON[B.mi];B.kills++;ev("faint",{monster:m,index:B.mi,lastMonster:B.mi+1>=MON.length});
    if(B.mi+1>=MON.length){B.phase="end";B.over="win";ev("win",{});return}
    const heal=Math.min(HEAL_ON_KILL,PLAYER_HP-B.hp);B.hp+=heal;if(heal)ev("heal",{amount:heal,hp:B.hp,source:"kill"});
    B.mi++;B.mhp=MON[B.mi].hp;B.heals=0;B.phase="ready";ev("enter",{monster:MON[B.mi],index:B.mi})}

  // 回血招式能不能用：{ok, reason:"full"（HP 已滿）|"used"（這隻怪物已用完次數）|"en"（能量不足）, left 剩幾次}
  function healCheck(s){const left=Math.max(0,s.perFoe-B.heals);
    return{ok:B.hp<PLAYER_HP&&left>0&&B.en>=s.cost,reason:B.hp>=PLAYER_HP?"full":left<=0?"used":B.en<s.cost?"en":null,left}}

  return {
    state:B,healCheck:i=>healCheck(SKILLS[i]), snapshot:snap, monsters:MON, skills:SKILLS,
    get monster(){return MON[B.mi]},
    start(){const out=[],ev=mk(out);B.phase="ready";ev("enter",{monster:MON[B.mi],index:B.mi});return out},
    // 出下一題。連招蓄力中每題有較短的限時，超時算答錯；一般題只計能量不會超時。
    nextQuestion(){if(B.queue.length<2)B.queue.push(...shuffle(B.pool));const w=B.queue.shift();B.w=w;B.phase="q";
      // 連招蓄力題：中翻英・填空時＝打字時間＋思考時間（思考時間隨蓄力階段縮短：原本 5 秒的階段給滿 2 秒）
      const c=B.chain,tl=c&&B.mode==="zh2enT"&&typeLimit?typeLimit(w,c.s.times[c.stage]/5):0;return{w,mode:B.mode,limitMs:c?(tl||c.s.times[c.stage]*1000):QUESTION_MS,timed:!!c,chain:c?{name:c.s.name,stage:c.stage,total:c.s.chain.length}:null}},
    answer(ok,sec,opt={}){const out=[],ev=mk(out);if(B.phase!=="q")return out;const w=B.w;B.n++;
      if(ok){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.fast=Math.min(B.fast,sec);
        const gain=energyGain(sec),before=B.en;B.en=Math.min(MAXEN,B.en+gain);ev("gain",{amount:B.en-before,raw:gain,sec,en:B.en});
        if(B.chain){const c=B.chain;c.stage++;const N=c.s.chain.length;ev("chainCharge",{skill:c.s,skillId:c.s.id,stage:c.stage,total:N,ready:c.stage>=N});
          if(c.stage<N){B.phase="ready";return out}
          // 最後一題答對：一次播完整套招式
          B.chain=null;B.phase="busy";const mult=comboMult(B.combo);ev("chainFire",{skill:c.s,skillId:c.s.id,total:N});
          for(let st=0;st<N;st++){const last=st===N-1;ev("chainStage",{skill:c.s,skillId:c.s.id,stage:st+1,total:N,move:c.s.chain[st],last});
            if(hitSkill(ev,c.s.id,c.s.chain[st],c.s.name,c.s.stages[st],mult,{big:last,chainStage:st+1,chainTotal:N})){faint(ev);return out}}
          ev("chainDone",{skill:c.s,skillId:c.s.id});B.phase="ready";return out}
        B.phase="skill";return out}
      // 答錯：連招中斷、連擊歸零、該字插回 3 題後再考（最多 3 次）、怪物攻擊
      const broke=B.chain;B.chain=null;B.combo=0;if(broke)ev("chainBreak",{skill:broke.s,skillId:broke.s.id,stage:broke.stage,timeout:!!opt.timeout});
      if((w._rep||0)<3)B.queue.splice(Math.min(3,B.queue.length),0,{...w,_rep:(w._rep||0)+1});if(!w._rep)B.wrong.push(w);
      const m=MON[B.mi],dmg=m.atk+Math.round(rng()*6);ev("foeAttack",{monster:m,move:m.move,timeout:!!opt.timeout});
      B.hp=Math.max(0,B.hp-dmg);ev("playerHit",{dmg,hp:B.hp,kind:"hit",lethal:B.hp<=0,source:m.id,move:m.move});
      if(B.hp<=0){B.phase="end";B.over="lose";ev("lose",{});return out}
      B.phase="wrong";return out},
    // 選招式：i 是 SKILLS 的索引；-1 是不出招（保留能量）
    useSkill(i){const out=[],ev=mk(out);if(B.phase!=="skill")return out;
      if(i<0){B.phase="ready";ev("hold",{en:B.en});return out}
      const s=SKILLS[i];if(!s||B.en<s.cost)return out;
      if(s.heal){if(!healCheck(s).ok)return out;
        // 回血：先發 skill（起手、扣能量），再發 heal（回復量不超過上限），之後照常出下一題
        B.phase="busy";B.en-=s.cost;B.heals++;ev("skill",{skillId:s.id,move:s.move,name:s.name,hitCount:0,totalDmg:0,mult:1,target:null,heal:true,cost:s.cost});
        const amount=Math.min(s.heal,PLAYER_HP-B.hp);B.hp+=amount;ev("heal",{amount,hp:B.hp,source:"skill",skillId:s.id,left:s.perFoe-B.heals});
        B.phase="ready";return out}
      if(s.chain){B.chain={s,stage:0};B.phase="ready";ev("chainStart",{skill:s,skillId:s.id,total:s.chain.length});return out}
      B.phase="busy";B.en-=s.cost;const dead=hitSkill(ev,s.id,s.move,s.name,s.hits,comboMult(B.combo),{big:s.cost>=18,cost:s.cost});
      if(dead)faint(ev);else B.phase="ready";return out},
    // 答錯後按「下一題」
    ack(){if(B.phase==="wrong")B.phase="ready"},
    result(){return{win:B.over==="win",kills:B.kills,total:MON.length,right:B.right,n:B.n,best:B.best,fast:B.fast,wrong:B.wrong}}
  }}
