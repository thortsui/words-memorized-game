// 純邏輯檢查：node tests/check.mjs
import assert from 'node:assert/strict';
import { BUILTIN } from '../src/data/no307.js';
import { isPhrase, normEn, enVariants, checkEn, checkZh, nearZh, zhSegs, clozeAns, opts, mcOf, sayable } from '../src/core/grading.js';
import { parseOcr, parseLines } from '../src/scan/parse.js';
import { createMonsterBattle, comboMult, energyGain } from '../src/battle/monster.js';
import { createSoulBattle, difficulty, gradeDodge } from '../src/battle/soul.js';
import { MON, SKILLS, SOUL_BOSSES, SOUL } from '../src/battle/data.js';

let n=0;const t=(name,fn)=>{fn();n++;console.log("ok  "+name)};
const W=BUILTIN.words,by=en=>W.find(w=>w.en===en);

// 原始碼的 RAW 實際是 95 個單字＋33 個片語（規格書寫 96＋32，以原始碼為準）
t("內建字典 128 筆＝95 單字＋33 片語",()=>{assert.equal(W.length,128);const ph=W.filter(isPhrase).length;assert.equal(ph,33);assert.equal(W.length-ph,95);assert.equal(new Set(W.map(w=>w.id)).size,128)});
t("normEn 去掉文法標記",()=>{assert.equal(normEn("let go of sth/sb"),"let go of");assert.equal(normEn("act as N."),"act as");assert.equal(normEn("be used to N./V-ing"),"be used to");assert.equal(normEn("open the door(s) to sth"),"open the door s to")});
t("enVariants 斜線寫法任一個都算對",()=>{const v=enVariants("see/regard ... as ...");assert.ok(v.includes("see as"));assert.ok(v.includes("regard as"));assert.ok(checkEn("Regard as",by("see/regard ... as ...")));assert.ok(checkEn("immediately ",by("immediately")));assert.ok(!checkEn("imediately",by("immediately")))});
t("checkZh 與書上義項相同或互相包含",()=>{const w=by("abandon");assert.ok(checkZh("放棄",w.zh));assert.ok(checkZh("遺棄",w.zh));assert.ok(!checkZh("喜歡",w.zh));assert.ok(!checkZh("",w.zh));assert.deepEqual(zhSegs("放棄；拋棄、遺棄"),["放棄","拋棄","遺棄"])});
t("nearZh 共同字過半算意思相近",()=>{assert.ok(nearZh("喜好",["喜歡","愛好"]));assert.ok(!nearZh("桌子",["喜歡"]))});
t("clozeAns 用 blank 或字幹",()=>{assert.equal(clozeAns(by("dye")),"dyed");assert.equal(clozeAns({en:"recycle",pos:"v.",ex:"David recycles bottles.",blank:""}),"recycles");assert.equal(clozeAns(by("hold back")),"");assert.equal(clozeAns(by("give away")),"giving away")});
t("opts 4 個不重複選項且含答案、片語配片語",()=>{for(const key of ["zh","en","cloze"]){for(const w of [by("dye"),by("pick up"),by("fluent")]){const o=opts(w,key,W);const ans=key==="cloze"?clozeAns(w):w[key];assert.equal(o.length,4);assert.equal(new Set(o.map(x=>x.toLowerCase())).size,4);assert.ok(o.includes(ans))}}
  const o=opts(by("pick up"),"en",W);o.forEach(x=>assert.ok(/\s/.test(x)||x==="pick up"))});
t("mcOf／sayable",()=>{assert.equal(mcOf("en2zhT"),"en2zh");assert.equal(mcOf("zh2enT"),"zh2en");assert.equal(mcOf("cloze"),"cloze");assert.equal(sayable("talk sb out of N./V-ing"),"talk somebody out of");assert.equal(sayable("open the door(s) to sth"),"open the doors to something")});
t("parseOcr 規則式解析",()=>{const r=parseOcr("abandon v. 放棄；拋棄\nThe sailors abandoned the damaged ship.\ngive away 贈送、分送\nThe store is giving away free samples.");assert.equal(r.length,2);assert.equal(r[0].en,"abandon");assert.equal(r[0].pos,"v.");assert.equal(r[0].ex,"The sailors abandoned the damaged ship.");assert.equal(r[1].pos,"片語");
  const l=parseLines([{text:"dye v. 染色",y0:10,y1:12},{text:"Mary dyed her hair red.",y0:12,y1:14}]);assert.deepEqual(l[0].bbox,{y0:10,y1:14})});

/* ---------- 打怪模式 ---------- */
const pool=W.slice(0,20).map(w=>({...w,dict:"no307"}));
const types=evs=>evs.map(e=>e.type);
t("能量與連擊公式",()=>{assert.equal(energyGain(0.4),10);assert.equal(energyGain(3.2),7);assert.equal(energyGain(30),1);assert.equal(comboMult(1),1);assert.equal(comboMult(3),1.2);assert.equal(comboMult(20),1.5)});
t("打怪：答對得能量→選招→逐段 hit 事件",()=>{const E=createMonsterBattle({pool,mode:"en2zh",rng:()=>0});assert.deepEqual(types(E.start()),["enter"]);
  E.nextQuestion();let ev=E.answer(true,1);assert.deepEqual(types(ev),["gain"]);assert.equal(E.state.en,9);assert.equal(E.state.phase,"skill");
  ev=E.useSkill(0);assert.deepEqual(types(ev),["skill","hit"]);assert.equal(ev[0].skillId,"slash");assert.equal(ev[1].dmg,8);assert.equal(ev[1].last,true);assert.equal(ev[1].index,0);assert.equal(E.state.mhp,62);assert.equal(E.state.phase,"ready");
  // 能量不足的招式不能用
  E.nextQuestion();E.answer(true,1);assert.equal(E.state.en,18);assert.deepEqual(E.useSkill(4),[]);
  ev=E.useSkill(1);assert.deepEqual(types(ev),["skill","hit","hit","hit"]);assert.equal(E.state.en,8);assert.deepEqual(ev.slice(1).map(e=>e.dmg),[11,11,15]);assert.deepEqual(ev.slice(1).map(e=>e.last),[false,false,true])});
t("打怪：答錯被攻擊、錯字 3 題後重出、連擊歸零",()=>{const E=createMonsterBattle({pool,mode:"en2zh",rng:()=>1});E.start();const q=E.nextQuestion();const ev=E.answer(false,2);
  assert.deepEqual(types(ev),["foeAttack","playerHit"]);assert.equal(ev[1].dmg,18);assert.equal(E.state.hp,82);assert.equal(E.state.phase,"wrong");assert.equal(E.state.queue[3].id,q.w.id);assert.equal(E.state.queue[3]._rep,1);assert.equal(E.state.wrong.length,1);E.ack();assert.equal(E.state.phase,"ready")});
t("打怪：連招要全部答對才發動，答錯中斷",()=>{const E=createMonsterBattle({pool,mode:"en2zh",rng:()=>0});E.start();E.nextQuestion();E.answer(true,1);
  assert.deepEqual(types(E.useSkill(6)),["chainStart"]);let q=E.nextQuestion();assert.equal(q.timed,true);assert.equal(q.limitMs,5000);
  assert.deepEqual(types(E.answer(true,1)),["gain","chainCharge"]);q=E.nextQuestion();assert.equal(q.limitMs,4000);E.answer(true,1);q=E.nextQuestion();assert.equal(q.limitMs,3000);
  const ev=E.answer(true,1);const ty=types(ev);assert.deepEqual(ty.slice(0,3),["gain","chainCharge","chainFire"]);assert.equal(ty.filter(x=>x==="chainStage").length,2);assert.equal(ty.filter(x=>x==="skill").length,2); // 第 2 式就把史萊姆打倒，和原版一樣中途結束
  // 連擊 4 → ×1.3：26+13+13+18 = 70 ≥ 70 → 擊倒並換下一隻
  assert.ok(ty.includes("faint"));assert.ok(ty.includes("enter"));assert.equal(E.state.mi,1);assert.equal(E.state.mhp,MON[1].hp);
  // 中斷
  E.nextQuestion();E.answer(true,1);E.useSkill(7);E.nextQuestion();const b=E.answer(false,6,{timeout:true});assert.deepEqual(types(b),["chainBreak","foeAttack","playerHit"]);assert.equal(E.state.chain,null)});
t("打怪：打倒 5 隻破關、HP 歸零失敗",()=>{const E=createMonsterBattle({pool,mode:"en2zh",rng:()=>0});E.start();let guard=0,last=[];
  while(E.state.phase!=="end"&&guard++<500){E.nextQuestion();E.answer(true,0.2);if(E.state.phase==="skill"){const i=[5,4,3,2,1,0].find(i=>E.state.en>=SKILLS[i].cost);last=E.useSkill(i)}}
  assert.equal(E.result().win,true);assert.equal(E.result().kills,5);assert.equal(last.at(-1).type,"win");
  const L=createMonsterBattle({pool,mode:"en2zh",rng:()=>1});L.start();let ev=[];for(let i=0;i<20&&L.state.phase!=="end";i++){L.nextQuestion();ev=L.answer(false,1);L.ack()}
  assert.equal(L.result().win,false);assert.equal(ev.at(-1).type,"lose");assert.equal(ev.at(-2).lethal,true)});

/* ---------- 魂系模式 ---------- */
t("魂系：閃避判定依答題速度分級",()=>{assert.equal(gradeDodge(true,900,4000,1500),"parry");assert.equal(gradeDodge(true,2000,4000,1500),"dodge");assert.equal(gradeDodge(true,3500,4000,1500),"graze");assert.equal(gradeDodge(true,4001,4000,1500),"hit");assert.equal(gradeDodge(false,500,4000,1500),"hit")});
t("魂系：動態難度隨答題速度變化",()=>{assert.equal(difficulty([]).d,0);const fast=difficulty(Array(8).fill({ok:true,ms:1200})),slow=difficulty(Array(8).fill({ok:true,ms:5500})),bad=difficulty(Array(8).fill({ok:false,ms:1000}));
  assert.equal(fast.d,1);assert.ok(Math.abs(fast.limitMul-.8)<1e-9);assert.equal(fast.extra,1);assert.equal(fast.perfectMs,1200);assert.ok(fast.dmgMul>1.14);
  assert.equal(slow.d,-1);assert.ok(Math.abs(slow.limitMul-1.2)<1e-9);assert.equal(slow.extra,-1);assert.equal(slow.perfectMs,1800);assert.equal(slow.dmgMul,1);assert.equal(bad.d,-1)});
t("魂系：玩家回合累積 ATB、迅擊、出招、時間用完換敵人",()=>{const E=createSoulBattle({pool,mode:"en2zhT",rng:()=>0});assert.deepEqual(types(E.start()),["bossEnter","playerTurn"]);
  let q=E.nextAttackQuestion();assert.equal(q.leftMs,10000);let ev=E.answerAttack(true,3000);assert.deepEqual(types(ev),["atb"]);assert.equal(E.state.atb,1);assert.equal(E.state.atkLeft,7000);assert.equal(E.state.phase,"cmd");
  assert.deepEqual(types(E.command(0)),[]);assert.equal(E.state.phase,"pturn");
  E.nextAttackQuestion();ev=E.answerAttack(true,1000);assert.deepEqual(types(ev),["atb","quickSlash","hit"]);assert.equal(E.state.atb,2);
  ev=E.command(2);assert.deepEqual(types(ev).slice(0,4),["skill","hit","hit","hit"]);assert.equal(E.state.atb,0);assert.equal(E.state.phase,"cmd");assert.deepEqual(E.command(1),[]);
  E.command(0);E.nextAttackQuestion();ev=E.answerAttack(false,7000);assert.deepEqual(types(ev),["miss"]);assert.equal(E.state.atkLeft,0);
  ev=E.command(0);assert.deepEqual(types(ev),["windowEnd","enemyTurn"]);assert.equal(E.state.phase,"enemy")});
t("魂系：彈反／閃避／擦傷／中招與耐力",()=>{const mkE=()=>{const E=createSoulBattle({pool,mode:"zh2enT",rng:()=>0});E.start();E.nextAttackQuestion();E.answerAttack(false,10000);E.command(0);return E};
  let E=mkE(),d=E.nextDodge();assert.equal(d.mode,"zh2en");assert.equal(d.limitMs,4000);assert.equal(types(d.events)[0],"telegraph");
  let ev=E.answerDodge(true,1000);assert.deepEqual(types(ev),["parry","counter","hit"]);assert.equal(E.state.atb,1);assert.equal(E.state.hp,100);assert.equal(E.nextDodge(),null);assert.deepEqual(types(E.startPlayerTurn()),["playerTurn"]);
  E=mkE();E.nextDodge();ev=E.answerDodge(true,2500);assert.deepEqual(types(ev),["dodge"]);assert.equal(E.state.stamina,SOUL.staminaMax-SOUL.dodgeCost);
  E=mkE();E.nextDodge();ev=E.answerDodge(true,3500);assert.deepEqual(types(ev),["graze","playerHit"]);assert.equal(ev[1].dmg,7);assert.equal(E.state.hp,93);
  E=mkE();E.nextDodge();ev=E.answerDodge(false,4001,{timeout:true});assert.deepEqual(types(ev),["foeHit","playerHit"]);assert.equal(ev[1].dmg,13);assert.equal(E.state.hp,87);
  E=mkE();E.state.stamina=5;E.nextDodge();ev=E.answerDodge(true,2500);assert.deepEqual(types(ev),["guard","playerHit"]);assert.equal(ev[1].dmg,5);assert.equal(E.state.stamina,0)});
t("魂系：Boss 階段轉換、擊倒後換下一隻、全破",()=>{const E=createSoulBattle({pool,mode:"en2zh",rng:()=>0});E.start();E.state.atb=3;E.state.phase="cmd";
  let ev=E.command(3);assert.ok(types(ev).includes("bossPhase"));assert.equal(E.state.bphase,1);assert.equal(E.state.mhp,8);
  E.state.atb=1;ev=E.command(1);assert.deepEqual(types(ev),["skill","hit","faint","bossEnter","playerTurn"]);assert.equal(E.state.mi,1);assert.equal(E.state.bphase,0);assert.equal(E.state.phase,"pturn");
  let guard=0;while(E.state.phase!=="end"&&guard++<400){E.state.atb=3;E.state.phase="cmd";ev=E.command(3)}
  assert.equal(E.result().win,true);assert.equal(E.result().kills,SOUL_BOSSES.length);assert.equal(ev.at(-1).type,"win")});
t("魂系：完整流程可以一路跑到結束（答題驅動）",()=>{const E=createSoulBattle({pool,mode:"en2zh",rng:()=>.5});E.start();let steps=0;
  while(E.state.phase!=="end"&&steps++<3000){const p=E.state.phase;
    if(p==="pturn"){const q=E.nextAttackQuestion();if(!q)E.startEnemyTurn();else E.answerAttack(true,1800)}
    else if(p==="cmd"){const c=E.commands().filter(c=>c.ready).pop();E.command(c?c.k:0)}
    else if(p==="enemy"){const d=E.nextDodge();if(!d)E.startPlayerTurn();else E.answerDodge(true,d.perfectMs+200)}
    else throw new Error("卡在 "+p)}
  assert.equal(E.state.phase,"end");assert.equal(E.result().win,true)});
console.log(`\n全部通過：${n} 項`);
