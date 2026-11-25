// 魂系模式規則狀態機。鎖定視角、所有動作由答題驅動：
//   玩家回合：限時內答題累積 ATB 出招；敵人回合：每次攻擊出一題閃避題，答題速度決定彈反／閃避／擦傷／中招。
//   並依最近的答題速度動態調整難度。不碰 DOM、不計時：作答毫秒數由外部傳入。
import { SOUL, SOUL_BOSSES, SOUL_CMDS, SOUL_BIG, PLAYER_HP, HEAL_ON_KILL } from './data.js';
import { shuffle, mcOf } from '../core/grading.js';
import { comboMult } from './monster.js';

const clamp=(v,a,b)=>v<a?a:v>b?b:v;

// 動態難度：recent = [{ok, ms}]。d 介於 -1（放寬）到 +1（加壓）。
export function difficulty(recent){const r=recent.slice(-SOUL.paceWindow);
  if(r.length<SOUL.paceMin)return{d:0,pace:null,limitMul:1,extra:0,perfectMs:SOUL.perfectMs,dmgMul:1};
  const pace=r.reduce((a,x)=>a+(x.ok?Math.min(x.ms/1000,SOUL.wrongAs):SOUL.wrongAs),0)/r.length;
  const d=clamp((SOUL.paceCenter-pace)/SOUL.paceSpan,-1,1);
  return{d,pace,limitMul:1-SOUL.limitSwing*d,extra:d>=SOUL.extraAt?1:(SOUL.easeDown&&d<=-SOUL.extraAt)?-1:0,perfectMs:Math.round(SOUL.perfectMs-SOUL.perfectSwing*d),dmgMul:1+SOUL.dmgBonus*Math.max(0,d)}}

// 閃避判定：回傳 parry（彈反）／dodge（閃避）／graze（擦傷）／hit（中招）
export function gradeDodge(ok,ms,limitMs,perfectMs){if(!ok||ms>limitMs)return"hit";if(ms<=Math.min(perfectMs,limitMs*.5))return"parry";if(ms<=limitMs*SOUL.slowAt)return"dodge";return"graze"}

export function createSoulBattle({pool,mode,rng=Math.random,onEvent}){
  const B={kind:"soul",mode,pool,queue:shuffle(pool),hp:PLAYER_HP,stamina:SOUL.staminaMax,atb:0,mi:0,mhp:SOUL_BOSSES[0].hp,bphase:0,
    combo:0,best:0,fast:99,right:0,n:0,wrong:[],kills:0,parries:0,atkLeft:0,recent:[],phase:"intro",w:null,over:null,enemy:null};
  const boss=()=>SOUL_BOSSES[B.mi];
  const ph=()=>B.bphase?boss().phases[B.bphase-1]:null;
  const diff=()=>difficulty(B.recent);
  const snap=()=>{const d=diff();return{hp:B.hp,hpMax:PLAYER_HP,stamina:B.stamina,staminaMax:SOUL.staminaMax,atb:B.atb,atbMax:SOUL.atbMax,mi:B.mi,mhp:B.mhp,mhpMax:boss().hp,bphase:B.bphase,
    combo:B.combo,right:B.right,n:B.n,kills:B.kills,atkLeft:B.atkLeft,windowMs:SOUL.windowMs,d:d.d,pace:d.pace}};
  const mk=out=>(type,p)=>{const e={type,...p,s:snap()};out.push(e);onEvent&&onEvent(e);return e};
  const nextWord=()=>{if(B.queue.length<2)B.queue.push(...shuffle(B.pool));return B.queue.shift()};
  const record=(ok,ms)=>{B.recent.push({ok,ms});if(B.recent.length>24)B.recent.shift()};
  const addStamina=v=>{B.stamina=clamp(B.stamina+v,0,SOUL.staminaMax)};
  const requeue=w=>{if((w._rep||0)<3)B.queue.splice(Math.min(3,B.queue.length),0,{...w,_rep:(w._rep||0)+1});if(!w._rep)B.wrong.push(w)};

  // 對 Boss 造成傷害；回傳是否擊倒。跨過血量門檻就進入下一階段。
  function damage(ev,type,p,base){const mult=comboMult(B.combo)*diff().dmgMul,dmgs=base.map(x=>Math.round(x*mult)),total=dmgs.length,target=boss().id;
    ev(type,{...p,skillId:p.move,hitCount:total,totalDmg:dmgs.reduce((a,b)=>a+b,0),mult,target});
    dmgs.forEach((dmg,i)=>{const before=B.mhp;B.mhp=Math.max(0,B.mhp-dmg);ev("hit",{skillId:p.move,move:p.move,index:i,total,dmg,mhp:B.mhp,mhpMax:boss().hp,last:i===total-1,kill:before>0&&B.mhp<=0,big:!!p.big,target})});
    if(B.mhp>0){const b=boss(),r=B.mhp/b.hp;while(B.bphase<b.phases.length&&r<=b.phases[B.bphase].at){B.bphase++;ev("bossPhase",{boss:b,phase:B.bphase,info:b.phases[B.bphase-1]})}}
    return B.mhp<=0}
  function faint(ev){const b=boss();B.kills++;ev("faint",{boss:b,index:B.mi,lastBoss:B.mi+1>=SOUL_BOSSES.length});
    if(B.mi+1>=SOUL_BOSSES.length){B.phase="end";B.over="win";ev("win",{});return}
    const heal=Math.min(SOUL.healOnKill??HEAL_ON_KILL,PLAYER_HP-B.hp);B.hp+=heal;if(heal)ev("heal",{amount:heal,hp:B.hp});
    B.mi++;B.mhp=boss().hp;B.bphase=0;B.enemy=null;B.atb=0; // 換下一隻 Boss：ATB 歸零（不能把上一場存的大招帶過來秒殺）
    ev("bossEnter",{boss:boss(),index:B.mi});playerTurn(ev)}
  function playerTurn(ev){B.atkLeft=SOUL.windowMs;addStamina(SOUL.staminaTurn);B.phase="pturn";ev("playerTurn",{windowMs:SOUL.windowMs})}
  function enemyTurn(ev){const b=boss(),p=ph(),d=diff();const total=Math.max(1,b.attacks+(p?p.extra:0)+d.extra);B.enemy={i:0,total,cur:null};B.phase="enemy";ev("enemyTurn",{boss:b,total,d:d.d})}
  const cmds=()=>{const big=SOUL_BIG[B.mi%SOUL_BIG.length];return[...SOUL_CMDS,{k:3,id:"big",name:big.name,bars:3,move:big.move,hits:big.hits,big:true}]};

  return {
    state:B, snapshot:snap, bosses:SOUL_BOSSES, difficulty:diff,
    get boss(){return boss()},
    commands(){const mult=comboMult(B.combo)*diff().dmgMul;return cmds().map(c=>({...c,ready:B.atb>=c.bars,approx:Math.round(c.hits.reduce((a,b)=>a+b,0)*mult)}))},
    start(){const out=[],ev=mk(out);ev("bossEnter",{boss:boss(),index:B.mi});playerTurn(ev);return out},

    /* ---- 玩家回合 ---- */
    // 攻擊時間用完回傳 null（接著呼叫 startEnemyTurn）
    nextAttackQuestion(){if(B.atkLeft<=0)return null;const w=nextWord();B.w=w;B.phase="q";return{w,mode:B.mode,leftMs:B.atkLeft,windowMs:SOUL.windowMs}},
    // ms：這一題花掉的攻擊時間（朗讀、選單、動畫期間不計）
    answerAttack(ok,ms){const out=[],ev=mk(out);if(B.phase!=="q")return out;const w=B.w;
      // 每題至少消耗 minCostMs 的攻擊時間；答錯再多扣 missPenaltyMs（速度記錄仍用實際作答時間）
      B.atkLeft=Math.max(0,B.atkLeft-Math.max(ms,SOUL.minCostMs||0)-(ok?0:SOUL.missPenaltyMs||0));B.n++;record(ok,ms);
      if(ok){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.fast=Math.min(B.fast,ms/1000);B.atb=Math.min(SOUL.atbMax,B.atb+1);addStamina(SOUL.staminaHit);ev("atb",{gain:1,ms});
        // 很快答對：追加一記不耗 ATB 的迅擊
        if(ms<=SOUL.quickMs){if(damage(ev,"quickSlash",{move:"quick",name:"迅擊"},[SOUL.quickDmg])){faint(ev);return out}}}
      else{B.combo=0;requeue(w);ev("miss",{ms})}
      B.phase="cmd";return out},
    // 題目顯示中時間用完
    attackTimeout(){const out=[],ev=mk(out);if(B.phase!=="q")return out;B.atkLeft=0;if(B.w)B.queue.unshift(B.w);ev("windowEnd",{});enemyTurn(ev);return out},
    // k：1 斬擊、2 疾風連斬、3 大招、0 繼續答題（時間用完則結束攻擊）
    command(k){const out=[],ev=mk(out);if(B.phase!=="cmd")return out;
      if(k===0){if(B.atkLeft>0)B.phase="pturn";else{ev("windowEnd",{});enemyTurn(ev)}return out}
      const c=cmds()[k-1];if(!c||B.atb<c.bars)return out;B.atb-=c.bars;
      if(damage(ev,"skill",{move:c.move,name:c.name,big:!!c.big},c.hits))faint(ev);
      return out},

    /* ---- 敵人回合 ---- */
    startEnemyTurn(){const out=[],ev=mk(out);if(B.phase==="enemy"&&B.enemy)return out;enemyTurn(ev);return out},
    // 下一次攻擊：先蓄力（telegraph），再出一題限時閃避題。全部打完回傳 null（接著呼叫 startPlayerTurn）。
    nextDodge(){if(B.phase!=="enemy"||!B.enemy||B.enemy.i>=B.enemy.total)return null;const out=[],ev=mk(out);const b=boss(),p=ph(),d=diff(),w=nextWord();
      const limitMs=Math.max(SOUL.minLimitMs,Math.round(b.limitMs*(p?p.limitMul:1)*d.limitMul));const perfectMs=Math.min(d.perfectMs,Math.round(limitMs*.5));
      const move=p&&B.enemy.i===B.enemy.total-1?p.move:b.move;
      B.w=w;B.enemy.cur={limitMs,perfectMs,move};B.phase="dodge";
      ev("telegraph",{boss:b,move,index:B.enemy.i,total:B.enemy.total,limitMs,perfectMs});
      return{w,mode:mcOf(B.mode),limitMs,perfectMs,index:B.enemy.i,total:B.enemy.total,move,events:out}},
    answerDodge(ok,ms,opt={}){const out=[],ev=mk(out);if(B.phase!=="dodge")return out;const w=B.w,cur=B.enemy.cur,b=boss(),p=ph();B.enemy.i++;B.n++;record(ok,ms);
      let g=gradeDodge(ok,ms,cur.limitMs,cur.perfectMs);const full=Math.round((b.atk+Math.round(rng()*6))*(p?p.atkMul:1));
      if(ok){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.fast=Math.min(B.fast,ms/1000)}else{B.combo=0;requeue(w)}
      B.phase="enemy";
      if(g==="parry"){B.parries++;B.atb=Math.min(SOUL.atbMax,B.atb+1);addStamina(SOUL.staminaParry);ev("parry",{move:cur.move,ms});
        if(damage(ev,"counter",{move:"counter",name:"反擊"},[SOUL.counterDmg])){faint(ev);return out}return out}
      let dmg=0;
      if(g==="dodge"){if(B.stamina>=SOUL.dodgeCost){addStamina(-SOUL.dodgeCost);ev("dodge",{move:cur.move,ms})}
        else{g="guard";B.stamina=0;dmg=Math.max(1,Math.round(full*SOUL.guardRate))}}
      else if(g==="graze"){addStamina(-SOUL.grazeCost);dmg=Math.max(1,Math.round(full*SOUL.grazeRate))}
      // 答錯或超時：耐力足夠就硬擋下來（扣耐力、只受格擋傷害），耐力不足才吃全額
      else if(B.stamina>=SOUL.blockCost){g="guard";addStamina(-SOUL.blockCost);dmg=Math.max(1,Math.round(full*SOUL.blockRate))}
      else dmg=full;
      if(dmg){ev(g==="hit"?"foeHit":g,{move:cur.move,ms,timeout:!!opt.timeout,blocked:g==="guard"&&!ok});
        B.hp=Math.max(0,B.hp-dmg);ev("playerHit",{dmg,hp:B.hp,kind:g,lethal:B.hp<=0,source:b.id,move:cur.move,timeout:!!opt.timeout});
        if(B.hp<=0){B.phase="end";B.over="lose";ev("lose",{});return out}}
      return out},
    // 只有敵人回合結束時才能呼叫；重複呼叫（例如按鈕被連點）不會再開一次回合
    startPlayerTurn(){const out=[],ev=mk(out);if(B.phase!=="enemy")return out;B.enemy=null;playerTurn(ev);return out},
    result(){return{win:B.over==="win",kills:B.kills,total:SOUL_BOSSES.length,right:B.right,n:B.n,best:B.best,fast:B.fast,wrong:B.wrong,parries:B.parries}}
  }}
