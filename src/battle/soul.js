// 魂系模式規則狀態機。鎖定視角、所有動作由答題驅動：
//   玩家回合：限時內答題累積 ATB 出招；敵人回合：每次攻擊出一題閃避題，答題速度決定彈反／閃避／擦傷／中招。
//   並依最近的答題速度動態調整難度。不碰 DOM、不計時：作答毫秒數由外部傳入。
import { SOUL, SOUL_BOSSES, SOUL_CMDS, SOUL_BIG, SOUL_PERKS, PLAYER_HP, HEAL_ON_KILL } from './data.js';
import { shuffle, mcOf } from '../core/grading.js';
import { comboMult } from './monster.js';

const clamp=(v,a,b)=>v<a?a:v>b?b:v;

// 動態難度：recent = [{ok, ms}]。d 介於 -1（放寬）到 +1（加壓）。
export function difficulty(recent){const r=recent.slice(-SOUL.paceWindow);
  if(r.length<SOUL.paceMin)return{d:0,pace:null,limitMul:1,extra:0,perfectMs:SOUL.perfectMs,dmgMul:1,foeMul:1};
  const pace=r.reduce((a,x)=>a+(x.ok?Math.min(x.ms/1000,SOUL.wrongAs):SOUL.wrongAs),0)/r.length;
  const d=clamp((SOUL.paceCenter-pace)/SOUL.paceSpan,-1,1);
  // d 接近上限（高手）時彈反門檻再收緊：tight 從 tightAt 起線性加到 1
  const tight=clamp((d-SOUL.tightAt)/(1-SOUL.tightAt),0,1);
  return{d,pace,limitMul:1-SOUL.limitSwing*d,extra:d>=SOUL.extraAt?1:(SOUL.easeDown&&d<=-SOUL.extraAt)?-1:0,perfectMs:Math.round(SOUL.perfectMs-SOUL.perfectSwing*d-SOUL.perfectTight*tight),dmgMul:1+SOUL.dmgBonus*Math.max(0,d),
    foeMul:1+SOUL.foeDmgSwing*Math.max(0,d)}} // foeMul：Boss 傷害倍率，只跟動態難度掛勾（答得越快越痛）

// 閃避判定：回傳 parry（彈反）／dodge（閃避）／graze（擦傷）／hit（中招）。perfectMs ≤ 0＝這一招不能彈反（突進、必殺）
export function gradeDodge(ok,ms,limitMs,perfectMs){if(!ok||ms>limitMs)return"hit";if(perfectMs>0&&ms<=Math.min(perfectMs,limitMs*.5))return"parry";if(ms<=limitMs*SOUL.slowAt)return"dodge";return"graze"}

// ambushRng：突襲判定用的亂數（預設同 rng；測試可單獨控制）
export function createSoulBattle({pool,mode,rng=Math.random,ambushRng=null,onEvent}){const arng=ambushRng||rng;
  const B={kind:"soul",mode,pool,queue:shuffle(pool),hp:PLAYER_HP,stamina:SOUL.staminaMax,atb:0,mi:0,mhp:SOUL_BOSSES[0].hp,bphase:0,
    combo:0,best:0,fast:99,right:0,n:0,wrong:[],kills:0,parries:0,atkLeft:0,recent:[],phase:"intro",w:null,over:null,enemy:null,
    flasks:SOUL.flaskStart,drinks:0,punish:false,ambushed:false,ambushN:0,ambushes:0,knocks:0,
    // 練等（只在這一局）：pk＝各強化的層數、perks＝依序選過的強化、offer＝目前可選的 3 個
    hpMax:PLAYER_HP,staMax:SOUL.staminaMax,flaskMax:SOUL.flaskMax,pk:{},perks:[],offer:null,
    win:SOUL.windowMs,wstreak:0,weakDone:false,weaks:0,dstreak:0,as:null,assaults:0};
  const pk=id=>B.pk[id]||0;
  const rr=a=>Math.round(a[0]+rng()*(a[1]-a[0]));
  const dmgMul=()=>comboMult(B.combo)*diff().dmgMul*(1+.15*pk("blade"));
  const boss=()=>SOUL_BOSSES[B.mi];
  const ph=()=>B.bphase?boss().phases[B.bphase-1]:null;
  const diff=()=>difficulty(B.recent);
  const snap=()=>{const d=diff();return{hp:B.hp,hpMax:B.hpMax,stamina:B.stamina,staminaMax:B.staMax,atb:B.atb,atbMax:SOUL.atbMax,mi:B.mi,mhp:B.mhp,mhpMax:boss().hp,bphase:B.bphase,
    combo:B.combo,right:B.right,n:B.n,kills:B.kills,atkLeft:B.atkLeft,windowMs:B.win,d:d.d,pace:d.pace,flasks:B.flasks,flaskMax:B.flaskMax,perks:B.perks.slice(),wstreak:B.wstreak,dstreak:B.dstreak}};
  const mk=out=>(type,p)=>{const e={type,...p,s:snap()};out.push(e);onEvent&&onEvent(e);return e};
  const nextWord=()=>{if(B.queue.length<2)B.queue.push(...shuffle(B.pool));return B.queue.shift()};
  const record=(ok,ms)=>{B.recent.push({ok,ms});if(B.recent.length>24)B.recent.shift()};
  const addStamina=v=>{B.stamina=clamp(B.stamina+v,0,B.staMax)};
  const requeue=w=>{if((w._rep||0)<3)B.queue.splice(Math.min(3,B.queue.length),0,{...w,_rep:(w._rep||0)+1});if(!w._rep)B.wrong.push(w)};

  // 對 Boss 造成傷害；回傳是否擊倒。跨過血量門檻就進入下一階段。
  function damage(ev,type,p,base){const mult=dmgMul(),dmgs=base.map(x=>Math.round(x*mult)),total=dmgs.length,target=boss().id;
    ev(type,{...p,skillId:p.move,hitCount:total,totalDmg:dmgs.reduce((a,b)=>a+b,0),mult,target});
    dmgs.forEach((dmg,i)=>{const before=B.mhp;B.mhp=Math.max(0,B.mhp-dmg);ev("hit",{skillId:p.move,move:p.move,index:i,total,dmg,mhp:B.mhp,mhpMax:boss().hp,last:i===total-1,kill:before>0&&B.mhp<=0,big:!!p.big,target})});
    if(B.mhp>0){const b=boss(),r=B.mhp/b.hp;while(B.bphase<b.phases.length&&r<=b.phases[B.bphase].at){B.bphase++;ev("bossPhase",{boss:b,phase:B.bphase,info:b.phases[B.bphase-1]})}}
    return B.mhp<=0}
  function faint(ev){const b=boss();B.kills++;ev("faint",{boss:b,index:B.mi,lastBoss:B.mi+1>=SOUL_BOSSES.length});
    if(B.mi+1>=SOUL_BOSSES.length){B.phase="end";B.over="win";ev("win",{});return}
    const heal=Math.min(SOUL.healOnKill??HEAL_ON_KILL,B.hpMax-B.hp);B.hp+=heal;if(heal)ev("heal",{amount:heal,hp:B.hp});
    if(B.flasks<B.flaskMax){B.flasks=Math.min(B.flaskMax,B.flasks+SOUL.flaskOnKill);ev("flaskRefill",{flasks:B.flasks})}B.punish=false;
    // 練等：從還沒疊滿的強化裡抽 3 個（不重複），選完才進下一隻 Boss（choosePerk）
    B.enemy=null;B.as=null;B.offer=shuffleR(SOUL_PERKS.filter(x=>pk(x.id)<x.max).map(x=>x.id)).slice(0,3);
    if(!B.offer.length){nextBoss(ev);return}
    B.phase="perk";ev("perkOffer",{options:B.offer.map(perkInfo),level:B.kills})}
  function perkInfo(id){const x=SOUL_PERKS.find(p=>p.id===id);return{...x,lv:pk(id)}}
  function shuffleR(a){a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
  function applyPerk(id){B.pk[id]=pk(id)+1;B.perks.push(id);
    if(id==="flask"){B.flaskMax++;B.flasks=Math.min(B.flaskMax,B.flasks+2)}
    if(id==="vigor"){B.hpMax+=20;B.hp=Math.min(B.hpMax,B.hp+20)}
    if(id==="stamina"){B.staMax+=25;B.stamina=B.staMax}}
  function nextBoss(ev){B.mi++;B.mhp=boss().hp;B.bphase=0;B.enemy=null;B.atb=0; // 換下一隻 Boss：ATB 歸零（不能把上一場存的大招帶過來秒殺）
    ev("bossEnter",{boss:boss(),index:B.mi});playerTurn(ev)}
  // 突襲結算完：攻擊時間還有就回到玩家回合（不重給時間、不回耐力），沒有就直接進敵人回合
  function endAmbush(ev){B.enemy=null;if(B.atkLeft>=SOUL.ambushResumeMs){B.phase="pturn";ev("ambushEnd",{atkLeft:B.atkLeft})}else{ev("windowEnd",{});enemyTurn(ev)}}
  function playerTurn(ev){B.win=rr(SOUL.windowRange||[SOUL.windowMs,SOUL.windowMs])+1000*pk("time");B.atkLeft=B.win;B.ambushed=false;B.ambushN=0;B.wstreak=0;B.weakDone=false;B.as=null;
    addStamina(SOUL.staminaTurn+8*pk("stamina"));B.phase="pturn";ev("playerTurn",{windowMs:B.win})}
  // 敵人回合的招式表：出幾招（attacks＋階段＋動態難度），每招依該階段的比重抽種類；連擊一招算多題。
  // 第二階段起，回合最後一招有機率換成必殺（階段招式名）。
  function planTurn(){const b=boss(),p=ph(),d=diff(),n=Math.max(1,b.attacks+(p?p.extra:0)+(SOUL.extraSeg?0:d.extra)),kit=(b.kit&&b.kit[Math.min(B.bphase,b.kit.length-1)])||{single:1},
      cr=(b.combo&&b.combo[Math.min(B.bphase,b.combo.length-1)])||[2,2],names=b.names||{},plan=[];
    for(let k=0;k<n;k++){let kind="single";
      if(p&&k===n-1&&rng()<(p.danger||0))kind="danger";
      else{let r=rng()*Object.values(kit).reduce((a,x)=>a+x,0);for(const [kk,w] of Object.entries(kit)){if((r-=w)<0){kind=kk;break}}}
      const segs=kind==="combo"?cr[0]+Math.floor(rng()*(cr[1]-cr[0]+1)):1;
      // 招式名：必殺用階段招式名；回合最後一記單擊沿用「階段招式」
      const name=kind==="danger"?p.move:kind==="single"?(p&&k===n-1?p.move:b.move):(names[kind]||b.move);
      plan.push({kind,segs,name})}
    // 攻擊時間快用完才喝藥：Boss 趁空檔逼近，這個回合先來一記突進
    if(B.punish){B.punish=false;plan.unshift({kind:"dash",segs:1,name:names.dash||b.move,punish:true})}
    // 答得快（d ≥ extraAt）：多一段攻擊——有連擊就接在連擊後面多一段，沒有就多一記單擊
    if(SOUL.extraSeg&&d.extra>0){const c=plan.find(m=>m.kind==="combo");if(c)c.segs=Math.min(5,c.segs+1);else plan.unshift({kind:"single",segs:1,name:b.move})}
    return plan}
  function enemyTurn(ev){const b=boss(),d=diff(),plan=planTurn(),total=plan.reduce((a,m)=>a+m.segs,0);
    B.enemy={i:0,total,plan,mi:0,si:0,cur:null};B.phase="enemy";ev("enemyTurn",{boss:b,total,moves:plan.length,plan:plan.map(m=>({kind:m.kind,segs:m.segs,name:m.name})),punish:plan.some(m=>m.punish),d:d.d})}
  const cmds=()=>{const big=SOUL_BIG[B.mi%SOUL_BIG.length];return[...SOUL_CMDS,{k:3,id:"big",name:big.name,bars:3,move:big.move,hits:big.hits,big:true},{k:4,id:"flask",name:"藥壺",bars:0,hits:[],flask:true}]};
  /* ---- 突襲：攻擊回合中 Boss 搶先出手（每個玩家回合最多一次） ----
     機率＝ambushBase[第幾隻] ×（第二階段起 ambushPhaseMul）＋ 拖延加成（作答或猶豫超過 ambushSlackMs 的部分，每秒 ambushPerSec）＋ 喝藥加成，上限 ambushMax。
     大招（3 格 ATB）不會被打斷。 */
  const ambushP=(ms,extra=0)=>{if(B.ambushed||!SOUL.ambushBase)return 0;const b0=SOUL.ambushBase[Math.min(B.mi,SOUL.ambushBase.length-1)]*(B.bphase?SOUL.ambushPhaseMul:1);
    return Math.min(SOUL.ambushMax,b0+Math.max(0,(ms||0)-SOUL.ambushSlackMs)/1000*SOUL.ambushPerSec+extra)*(pk("alert")?.6:1)};
  // 觸發突襲：建立只有一題的「突襲」敵人行動，答完回到攻擊回合剩下的時間（時間已用完就直接進敵人回合）
  function ambush(ev,from,info={}){const b=boss();B.ambushN++;B.ambushed=B.ambushN>=(SOUL.ambushPerTurn||1);B.ambushes++;
    B.enemy={i:0,total:1,plan:[{kind:"ambush",segs:1,name:(b.names&&b.names.dash)||b.move}],mi:0,si:0,cur:null,ambush:true};B.phase="enemy";
    ev("ambush",{boss:b,from,move:B.enemy.plan[0].name,...info})}
  // 破綻：攻擊回合答錯（作答題或喝藥題），Boss 立刻衝上來把主角打倒——不能閃、不能擋，倒地再多扣 knockMs 攻擊時間。回傳是否陣亡。
  function knock(ev,from){if(!SOUL.knockMul)return false;const b=boss(),p=ph(),move=(b.names&&b.names.dash)||b.move;
    const dmg=Math.max(1,Math.round((b.atk+Math.round(rng()*4))*(p?p.atkMul:1)*(diff().foeMul||1)*SOUL.knockMul*(pk("steady")?.5:1)));
    B.knocks++;B.atkLeft=Math.max(0,B.atkLeft-(pk("steady")?0:SOUL.knockMs||0));B.hp=Math.max(0,B.hp-dmg);
    ev("knockdown",{boss:b,from,dmg,move});
    ev("playerHit",{dmg,hp:B.hp,kind:"knockdown",lethal:B.hp<=0,source:b.id,move,knockdown:true});
    if(B.hp<=0){B.phase="end";B.over="lose";ev("lose",{});return true}return false}
  // 藥壺能不能喝：還有次數、而且 HP 掉到 flaskBelow 以下（滿血時不會一直跳出指令列）
  const flaskReady=()=>B.flasks>0&&B.hp<B.hpMax*SOUL.flaskBelow;
  const flaskHeal=()=>Math.round(B.hpMax*(SOUL.flaskHeal+.15*pk("brew")));
  // 突擊：連續 need 次快閃避就觸發——打斷 Boss 剩下的攻擊，換玩家連續答 total 題（每題 2–5 秒）
  function tryAssault(ev){const need=pk("assault")?2:SOUL.assaultN;if(!SOUL.assaultN||B.dstreak<need||B.phase==="end"||B.phase==="perk")return false;
    const E=B.enemy,cut=E?Math.max(0,E.total-E.i):0;B.dstreak=0;B.enemy=null;B.assaults++;B.as={i:0,total:SOUL.assaultQs+pk("assault"),hits:0};B.phase="assault";
    ev("assault",{total:B.as.total,cut});return true}

  return {
    state:B, snapshot:snap, bosses:SOUL_BOSSES, difficulty:diff,
    get boss(){return boss()},
    commands(){const mult=dmgMul();return cmds().map(c=>({...c,ready:c.flask?flaskReady():B.atb>=c.bars,count:c.flask?B.flasks:undefined,heal:c.flask?flaskHeal():undefined,approx:Math.round(c.hits.reduce((a,b)=>a+b,0)*mult)}))},
    start(){const out=[],ev=mk(out);ev("bossEnter",{boss:boss(),index:B.mi});playerTurn(ev);return out},

    /* ---- 玩家回合 ---- */
    // 攻擊時間用完回傳 null（接著呼叫 startEnemyTurn）
    nextAttackQuestion(){if(B.atkLeft<=0)return null;const w=nextWord();B.w=w;B.phase="q";return{w,mode:B.mode,leftMs:B.atkLeft,windowMs:B.win}},
    /* ---- 練等 ---- */
    get perkOffer(){return B.phase==="perk"&&B.offer?B.offer.map(perkInfo):null},
    choosePerk(id){const out=[],ev=mk(out);if(B.phase!=="perk"||!B.offer||!B.offer.includes(id))return out;applyPerk(id);B.offer=null;ev("perk",{perk:perkInfo(id)});nextBoss(ev);return out},
    /* ---- 突擊 ---- */
    nextAssault(){if(B.phase!=="assault"||!B.as)return null;const w=nextWord();B.w=w;B.phase="assaultQ";const limitMs=rr(SOUL.assaultRange)+500*pk("dodgeT");B.as.limitMs=limitMs;
      return{w,mode:mcOf(B.mode),limitMs,index:B.as.i,total:B.as.total}},
    // 答對一題砍一刀（最後一題是重擊）；答錯或超時突擊結束。結束後換玩家回合
    answerAssault(ok,ms,opt={}){const out=[],ev=mk(out);if(B.phase!=="assaultQ")return out;const w=B.w,A=B.as;B.n++;if(opt.timeout)ms=Math.max(ms,A.limitMs+1);record(ok,ms);A.i++;
      const good=ok&&ms<=A.limitMs;
      if(good){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.fast=Math.min(B.fast,ms/1000);A.hits++;const last=A.i>=A.total,D=SOUL.assaultDmg;
        if(damage(ev,"skill",{move:last?"gale":"quick",name:last?"突擊・終結":"突擊",assault:true,index:A.i-1,total:A.total},last?[D[D.length-1]]:[D[Math.min(A.i-1,D.length-2)]])){faint(ev);return out}}
      else{B.combo=0;requeue(w);ev("miss",{ms,assault:true,timeout:!!opt.timeout})}
      if(!good||A.i>=A.total){ev("assaultEnd",{hits:A.hits,total:A.total});B.as=null;playerTurn(ev)}else B.phase="assault";
      return out},
    // ms：這一題花掉的攻擊時間（朗讀、選單、動畫期間不計）
    // opt.noAmbush：測試用，關掉這一題的突襲判定；opt.noKnock：測試用，答錯不觸發破綻
    answerAttack(ok,ms,opt={}){const out=[],ev=mk(out);if(B.phase!=="q")return out;const w=B.w;
      // 突襲：這一題作廢（不加 ATB、不算對錯、字放回佇列前面），花掉的時間照扣
      if(!opt.noAmbush&&arng()<ambushP(ms)){B.atkLeft=Math.max(0,B.atkLeft-Math.max(ms,SOUL.minCostMs||0));B.queue.unshift(w);ambush(ev,"answer",{ms});return out}
      // 每題至少消耗 minCostMs 的攻擊時間；答錯再多扣 missPenaltyMs（速度記錄仍用實際作答時間）
      B.atkLeft=Math.max(0,B.atkLeft-Math.max(ms,SOUL.minCostMs||0)-(ok?0:SOUL.missPenaltyMs||0));B.n++;record(ok,ms);
      if(ok){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.fast=Math.min(B.fast,ms/1000);B.atb=Math.min(SOUL.atbMax,B.atb+1);addStamina(SOUL.staminaHit);ev("atb",{gain:1,ms});
        // 很快答對：追加一記不耗 ATB 的迅擊
        if(ms<=SOUL.quickMs+500*pk("quick")){if(damage(ev,"quickSlash",{move:"quick",name:"迅擊"},[SOUL.quickDmg*(pk("quick")?2:1)])){faint(ev);return out}}
        // 弱點擊破：同一回合連續 weakN 題都在攻擊時間的 weakAt 內答對（＝剩 75% 以上的時間就完成）
        if(SOUL.weakN&&!B.weakDone&&ms<=B.win*(pk("weak")?.4:SOUL.weakAt)){if(++B.wstreak>=SOUL.weakN){B.weakDone=true;B.wstreak=0;B.weaks++;B.atb=Math.min(SOUL.atbMax,B.atb+SOUL.weakAtb);
          if(damage(ev,"weakBreak",{move:"gale",name:"弱點擊破",atbGain:SOUL.weakAtb},SOUL.weakHits)){faint(ev);return out}}}
        else B.wstreak=0}
      else{B.combo=0;B.wstreak=0;requeue(w);ev("miss",{ms});if(!opt.noKnock&&knock(ev,"answer"))return out}
      B.phase="cmd";return out},
    // 題目顯示中時間用完
    attackTimeout(){const out=[],ev=mk(out);if(B.phase!=="q")return out;B.atkLeft=0;if(B.w)B.queue.unshift(B.w);ev("windowEnd",{});enemyTurn(ev);return out},
    // k：1 斬擊、2 疾風連斬、3 大招、0 繼續答題（時間用完則結束攻擊）
    // opt.ms：開指令列到按下的猶豫時間（越久越容易被突襲）；opt.noAmbush：測試用
    command(k,opt={}){const out=[],ev=mk(out);if(B.phase!=="cmd")return out;
      if(k===0){if(B.atkLeft>0)B.phase="pturn";else{ev("windowEnd",{});enemyTurn(ev)}return out}
      // 藥壺：按下後出一題（flaskQuestion／answerFlask），答對才喝下
      if(k===4){if(!flaskReady())return out;B.w=nextWord();B.phase="flask";ev("flaskStart",{flasks:B.flasks});return out}
      const c=cmds()[k-1];if(!c||B.atb<c.bars)return out;B.atb-=c.bars;
      // 斬擊／連斬出招途中可能被突襲打斷：只結算打斷前已命中的段數，沒打到的段數按比例返還 ATB（無條件捨去）。大招不會被打斷。
      if(!c.big&&!opt.noAmbush&&arng()<ambushP(opt.ms)){const landed=Math.floor(arng()*c.hits.length),refund=Math.floor(c.bars*(c.hits.length-landed)/c.hits.length);
        B.atb=Math.min(SOUL.atbMax,B.atb+refund);
        if(landed>0){if(damage(ev,"skill",{move:c.move,name:c.name,interrupted:true},c.hits.slice(0,landed))){faint(ev);return out}}
        else ev("skill",{move:c.move,name:c.name,skillId:c.move,hitCount:0,totalDmg:0,interrupted:true,target:boss().id});
        ambush(ev,"skill",{landed,total:c.hits.length,refund});return out}
      if(damage(ev,"skill",{move:c.move,name:c.name,big:!!c.big},c.hits))faint(ev);
      return out},

    /* ---- 藥壺 ---- */
    // 喝藥題：選擇題，攻擊時間照樣倒數（喝藥本身至少要花 flaskCostMs）
    flaskQuestion(){if(B.phase!=="flask")return null;return{w:B.w,mode:mcOf(B.mode),leftMs:B.atkLeft,windowMs:SOUL.windowMs,flasks:B.flasks}},
    // ok：答對才喝下（回復 flaskHeal×最大 HP）；答錯藥灑掉。次數都會扣。喝完攻擊時間剩不到 flaskPunishMs，下個敵人回合 Boss 先突進
    answerFlask(ok,ms,opt={}){const out=[],ev=mk(out);if(B.phase!=="flask")return out;const w=B.w;
      // 喝藥時最容易被突襲：藥沒喝到、但壺不扣（題目作廢），花掉的時間照扣
      if(!opt.noAmbush&&!opt.timeout&&arng()<ambushP(ms,SOUL.ambushFlask)){B.atkLeft=Math.max(0,B.atkLeft-Math.max(ms,SOUL.flaskCostMs));B.queue.unshift(w);ambush(ev,"flask",{ms});return out}
      B.flasks--;B.n++;record(ok,ms);
      B.atkLeft=Math.max(0,B.atkLeft-Math.max(ms,SOUL.flaskCostMs));
      if(ok){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.drinks++;const amount=Math.min(flaskHeal(),B.hpMax-B.hp);B.hp+=amount;ev("drink",{amount,hp:B.hp,flasks:B.flasks})}
      else{B.combo=0;requeue(w);ev("spill",{flasks:B.flasks,timeout:!!opt.timeout});if(!opt.noKnock&&knock(ev,"flask"))return out}
      if(B.atkLeft<SOUL.flaskPunishMs){B.punish=true;ev("flaskPunish",{})}
      if(B.atkLeft<=0||opt.timeout){B.atkLeft=0;ev("windowEnd",{});enemyTurn(ev);return out}
      B.phase="cmd";return out},

    /* ---- 敵人回合 ---- */
    startEnemyTurn(){const out=[],ev=mk(out);if(B.phase==="enemy"&&B.enemy)return out;enemyTurn(ev);return out},
    // 下一次攻擊：先蓄力（telegraph），再出一題限時閃避題。全部打完回傳 null（接著呼叫 startPlayerTurn）。
    nextDodge(){if(B.phase!=="enemy"||!B.enemy||B.enemy.i>=B.enemy.total)return null;const out=[],ev=mk(out);const b=boss(),p=ph(),d=diff(),w=nextWord(),E=B.enemy,m=E.plan[E.mi],seg=E.si,kind=m.kind;
      const km=kind==="combo"?SOUL.comboLimit[Math.min(seg,SOUL.comboLimit.length-1)]:kind==="delayed"?SOUL.delayLimitMul:kind==="dash"?SOUL.dashLimitMul:kind==="danger"?SOUL.dangerLimitMul:kind==="ambush"?SOUL.ambushLimitMul:1;
      // 時限 2–5 秒不固定：依種類抽範圍 × 階段 × 動態難度，夾在 dodgeClamp 內；閃避延長再往上加
      const R=SOUL.dodgeRange,limitMs=R?Math.round(clamp(rr(R[kind]||R.base)*(p?p.limitMul:1)*d.limitMul,SOUL.dodgeClamp[0],SOUL.dodgeClamp[1]))+500*pk("dodgeT")
        :Math.max(SOUL.minLimitMs,Math.round(b.limitMs*(p?p.limitMul:1)*d.limitMul*km));
      // 連擊越後面越快：彈反門檻跟著時限一起縮（高手也會被逼到翻滾）
      const noParry=kind==="dash"||kind==="danger",perfectMs=noParry?0:Math.min(Math.round(d.perfectMs*(kind==="combo"?km:1))+200*pk("parry"),Math.round(limitMs*.5));
      const lockMs=kind==="delayed"?Math.round(SOUL.delayLockMs[0]+rng()*(SOUL.delayLockMs[1]-SOUL.delayLockMs[0])):0;
      const info={kind,seg,segs:m.segs,moveIndex:E.mi,moves:E.plan.length,chain:seg<m.segs-1,lockMs,noParry,danger:kind==="danger",ambush:!!E.ambush};
      B.w=w;E.cur={limitMs,perfectMs,move:m.name,foeMul:d.foeMul,...info};B.phase="dodge";
      ev("telegraph",{boss:b,move:m.name,index:E.i,total:E.total,limitMs,perfectMs,...info});
      return{w,mode:mcOf(B.mode),limitMs,perfectMs,index:E.i,total:E.total,move:m.name,...info,events:out}},
    // opt：{timeout, early（延遲攻擊鎖住期間亂點的次數）}
    answerDodge(ok,ms,opt={}){const out=[],ev=mk(out);if(B.phase!=="dodge")return out;const w=B.w,E=B.enemy,cur=E.cur,b=boss(),p=ph();
      E.i++;if(++E.si>=E.plan[E.mi].segs){E.mi++;E.si=0}B.n++;
      ms+=Math.min(2,opt.early||0)*SOUL.flinchMs;if(opt.timeout)ms=Math.max(ms,cur.limitMs+1);record(ok,ms);
      let g=gradeDodge(ok,ms,cur.limitMs,cur.noParry?-1:cur.perfectMs);
      // 突擊的「快閃避」：答對而且用不到時限的 assaultFast（突襲那一題不算）
      if(!E.ambush){if(ok&&ms<=cur.limitMs*SOUL.assaultFast)B.dstreak++;else B.dstreak=0}
      const cm=1+.6*pk("counter"),gm=pk("guard")?.6:1;
      const km=cur.kind==="combo"?SOUL.comboDmg:cur.kind==="delayed"?SOUL.delayDmg:cur.kind==="dash"?SOUL.dashDmg:cur.kind==="danger"?SOUL.dangerDmg:1;
      const full=Math.max(1,Math.round((b.atk+Math.round(rng()*6))*(p?p.atkMul:1)*(cur.foeMul||1)*km));
      if(ok){B.right++;B.combo++;B.best=Math.max(B.best,B.combo);B.fast=Math.min(B.fast,ms/1000)}else{B.combo=0;requeue(w)}
      B.phase="enemy";const base={move:cur.move,ms,kind:cur.kind,chain:cur.chain,timeout:!!opt.timeout,early:opt.early||0};
      if(g==="parry"){B.parries++;B.atb=Math.min(SOUL.atbMax,B.atb+1);addStamina(SOUL.staminaParry);ev("parry",base);
        // 連擊中段的彈反只彈開刀（小傷害、不衝上去）；整招最後一段才完整反擊
        if(cur.chain?damage(ev,"deflect",{move:"deflect",name:"彈刀"},[Math.round(SOUL.chainParryDmg*cm)]):damage(ev,"counter",{move:"counter",name:"反擊"},[Math.round(SOUL.counterDmg*cm)])){faint(ev);return out}
        if(E.ambush&&E.i>=E.total)endAmbush(ev);else tryAssault(ev);return out}
      let dmg=0;
      if(g==="dodge"){if(B.stamina>=SOUL.dodgeCost){addStamina(-SOUL.dodgeCost);ev("dodge",base)}
        // 必殺不能格擋：答對但耐力不夠翻滾，只能撲開、被餘波擦到
        else if(cur.danger){g="graze";B.stamina=0;dmg=Math.max(1,Math.round(full*SOUL.grazeRate))}
        else{g="guard";B.stamina=0;dmg=Math.max(1,Math.round(full*SOUL.guardRate*gm))}}
      else if(g==="graze"){addStamina(-SOUL.grazeCost);dmg=Math.max(1,Math.round(full*SOUL.grazeRate))}
      // 答錯或超時：耐力足夠就硬擋下來（扣耐力、只受格擋傷害），耐力不足才吃全額；必殺擋不住
      else if(!cur.danger&&B.stamina>=SOUL.blockCost){g="guard";addStamina(-SOUL.blockCost);dmg=Math.max(1,Math.round(full*SOUL.blockRate*gm))}
      else dmg=full;
      if(dmg){ev(g==="hit"?"foeHit":g,{...base,blocked:g==="guard"&&!ok});
        B.hp=Math.max(0,B.hp-dmg);ev("playerHit",{dmg,hp:B.hp,kind:g,lethal:B.hp<=0,source:b.id,move:cur.move,timeout:!!opt.timeout,chain:cur.chain,danger:!!cur.danger});
        if(B.hp<=0){B.phase="end";B.over="lose";ev("lose",{});return out}}
      if(E.ambush&&E.i>=E.total)endAmbush(ev);else tryAssault(ev);
      return out},
    // 目前這一招後面還有沒有連擊段（控制器用來決定要不要停下來等「繼續」）
    get chainPending(){const E=B.enemy;return!!(E&&E.si>0&&E.mi<E.plan.length)},
    // 只有敵人回合結束時才能呼叫；重複呼叫（例如按鈕被連點）不會再開一次回合
    startPlayerTurn(){const out=[],ev=mk(out);if(B.phase!=="enemy")return out;B.enemy=null;playerTurn(ev);return out},
    result(){return{win:B.over==="win",kills:B.kills,total:SOUL_BOSSES.length,right:B.right,n:B.n,best:B.best,fast:B.fast,wrong:B.wrong,parries:B.parries,drinks:B.drinks,knocks:B.knocks,perks:B.perks.map(perkInfo),weaks:B.weaks,assaults:B.assaults}}
  }}
