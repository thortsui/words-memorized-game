// 純邏輯檢查：node tests/check.mjs
import assert from 'node:assert/strict';
import { BUILTIN } from '../src/data/no307.js';
import { isPhrase, normEn, enVariants, checkEn, checkZh, nearZh, zhSegs, clozeAns, opts, mcOf, sayable } from '../src/core/grading.js';
import { parseOcr, parseLines, parseLayout, parseHead, deriveBlank } from '../src/scan/parse.js';
import { consensus, tally, charDiff, alignEntries, NORM } from '../src/scan/consensus.js';
import { makeLexicon, unknownWords } from '../src/scan/wordlist.js';
import { ruleWarnings, isInflection } from '../src/scan/rules.js';
import { parseDict } from '../src/scan/engines/ppocr.js';
import fs from 'node:fs';
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

/* ---------- 掃描：版面解析、雙引擎交叉比對、詞表與規則檢查 ---------- */
const root=new URL("..",import.meta.url),rd=f=>fs.readFileSync(new URL(f,root),"utf8");
const lex=makeLexicon(rd("public/wordlist/en-words.txt"),rd("public/wordlist/en-names.txt"));
const E=(en,pos,zh,ex,blank)=>({en,pos,zh,ex,blank:blank??deriveBlank(en,pos,ex),unit:""});
const st=r=>r.map(x=>x.status+":"+x.entry.en);
t("parseHead：音標、編號、詞性寫法、片語、例句不當開頭",()=>{
  assert.deepEqual(parseHead("12. fluent [ˋfluənt] adj. 流利的"),{en:"fluent",pos:"adj.",zh:"流利的"});
  assert.deepEqual(parseHead("record v., n. 記錄；唱片"),{en:"record",pos:"v., n.",zh:"記錄；唱片"});
  assert.deepEqual(parseHead("effect n.[C] 影響"),{en:"effect",pos:"n.[C]",zh:"影響"});
  assert.deepEqual(parseHead("immediately adv, 立刻"),{en:"immediately",pos:"adv.",zh:"立刻"});            // OCR 把句點看成逗號
  assert.deepEqual(parseHead("abandon V. 放棄"),{en:"abandon",pos:"v.",zh:"放棄"});                       // OCR 把 v 看成大寫
  assert.deepEqual(parseHead("act as N. 充當；擔任"),{en:"act as N.",pos:"片語",zh:"充當；擔任"});         // 片語裡的 N. 不是詞性
  assert.equal(parseHead("talk sb out of N./V-ing 說服某人不做…").en,"talk sb out of N./V-ing");
  assert.equal(parseHead("see/regard ... as ... 把…視為…").pos,"片語");
  assert.equal(parseHead("The sailors abandoned the ship. 船員們棄船了。"),null);
  assert.equal(parseHead("Taiwan is beautiful 台灣很美"),null);
  assert.deepEqual(parseHead("abandon /əˈbændən/ v."),{en:"abandon",pos:"v.",zh:""})});
t("parseLines：例句換行、連字號斷字、中文解釋換行、單元標籤、例句翻譯不收",()=>{const r=parseLines([
    {text:"NO.307 Unit 5"},{text:"record v., n. 記錄；"},{text:"唱片"},{text:"The scientist recorded the tempera-"},{text:"ture of the water every hour"},{text:"during the experiment."},{text:"科學家每小時記錄水溫。"},
    {text:"Key Phrases"},{text:"give away 贈送、分送"},{text:"The store is giving away free samples. 這家店在送試用品。"}]);
  assert.equal(r.length,2);assert.equal(r[0].zh,"記錄；唱片");assert.equal(r[0].ex,"The scientist recorded the temperature of the water every hour during the experiment.");assert.equal(r[0].blank,"recorded");assert.equal(r[0].unit,"NO.307 Unit 5");
  assert.equal(r[1].unit,"Key Phrases");assert.equal(r[1].ex,"The store is giving away free samples.");assert.equal(r[1].blank,"giving away")});
t("parseLayout：依座標分兩欄、同列的框併起來、側邊標籤、tesseract 的中文空白",()=>{const B=(text,x0,y0,x1,y1)=>({text,x0,y0,x1,y1}),bs=[
    B("Unit 6",90,100,180,130),B("Key Phrases",680,100,860,130),
    B("ancient",90,170,190,200),B("adj.",205,170,250,200),B("古 代 的",270,170,345,200),B("They visited an ancient temple in the",120,210,500,238),B("mountains.",120,245,240,273),
    B("borrow v. 借入",90,300,300,330),B("May I borrow your umbrella for a while?",120,340,530,368),
    B("climate n. 氣候",90,395,300,425),B("The climate here is warm and wet in summer.",120,435,585,463),
    B("give away 贈送 、 分送",680,170,960,200),B("The store is giving away free samples today.",710,210,1155,238),
    B("pick up 撿起 ; 接 ( 某人 )",680,265,1000,295),B("She picked up the coins from the floor.",710,305,1100,333),
    B("run out of 用完",680,360,890,390),B("The car ran out of gas on the highway.",710,400,1100,428)];
  const r=parseLayout(bs,{W:1240,H:1754});
  assert.deepEqual(r.map(x=>x.en),["ancient","borrow","climate","give away","pick up","run out of"]);
  assert.equal(r[0].zh,"古代的");assert.equal(r[0].ex,"They visited an ancient temple in the mountains.");assert.equal(r[0].unit,"Unit 6");
  assert.equal(r[3].zh,"贈送、分送");assert.equal(r[3].unit,"Key Phrases");assert.equal(r[4].zh,"撿起；接（某人）");assert.equal(r[4].blank,"picked up");assert.equal(r[5].blank,"");
  assert.ok(r[0].bbox.x1<50&&r[3].bbox.x0>50);assert.ok(Math.abs(r[0].bbox.y0-170/1754*100)<.01&&Math.abs(r[0].bbox.y1-273/1754*100)<.01);
  // 表格式版面（左邊全英文、右邊全中文）不能被切成兩欄
  const tb=[];["abandon v.","borrow v.","climate n.","damage n.","effort n.","fluent adj."].forEach((x,i)=>{tb.push(B(x,90,100+i*60,300,130+i*60));tb.push(B(["放棄","借入","氣候","損害","努力","流利的"][i],700,100+i*60,800,130+i*60))});
  assert.deepEqual(parseLayout(tb,{W:1240,H:1754}).map(x=>x.en+"|"+x.zh),["abandon|放棄","borrow|借入","climate|氣候","damage|損害","effort|努力","fluent|流利的"])});
t("deriveBlank：單字用字幹、片語找連續出現的字形",()=>{assert.equal(deriveBlank("dye","v.","Mary dyed her hair red."),"dyed");assert.equal(deriveBlank("give away","片語","The store is giving away free samples."),"giving away");
  assert.equal(deriveBlank("pick up","片語","She picked up the coins."),"picked up");assert.equal(deriveBlank("run out of","片語","The car ran out of gas."),"");assert.equal(deriveBlank("talk sb out of N./V-ing","片語","He talked me out of going."),"")});
const A0=[E("dye","v.","染色","Mary dyed her hair red."),E("give away","片語","贈送、分送","The store is giving away free samples."),E("fluent","adj.","流利的","She is fluent in three languages."),E("immediately","adv.","立刻；馬上","Please call me immediately.")];
t("consensus：兩邊完全相同 → 全部雙重確認（全形半形、引號寫法不算差異）",()=>{const B0=A0.map(x=>({...x}));B0[1].zh="贈送,分送";B0[3].zh="立刻;馬上";B0[0].ex="Mary dyed her hair red. ";
  const r=consensus(A0,B0);assert.deepEqual(tally(r),{agree:4,diff:0,onlyA:0,onlyB:0});assert.equal(r[1].entry.zh,"贈送、分送")});
t("consensus：dye／dyed 配成同一筆並標出差異字元",()=>{const B0=A0.map(x=>({...x}));B0[0]={...B0[0],en:"dyed"};const r=consensus(A0,B0);
  assert.equal(r[0].status,"diff");assert.deepEqual(r[0].bad,["en"]);assert.deepEqual(r[0].fields.en.diff,{a:[["dye",false]],b:[["dye",false],["d",true]]});assert.equal(r.filter(x=>x.status==="agree").length,3)});
t("consensus：片語少一個空格、例句少一個句點都是差異",()=>{const B0=A0.map(x=>({...x}));B0[1]={...B0[1],en:"giveaway",pos:""};B0[2]={...B0[2],ex:"She is fluent in three languages"};const r=consensus(A0,B0);
  assert.equal(r[1].status,"diff");assert.ok(r[1].bad.includes("en")&&r[1].bad.includes("pos"));assert.equal(r[2].status,"diff");assert.deepEqual(r[2].bad,["ex"]);assert.deepEqual(r[2].fields.ex.diff.a.at(-1),[".",true])});
t("consensus：一邊漏條目／多條目",()=>{const B0=[A0[0],A0[1],E("ghost","n.","鬼","A ghost appeared."),A0[3]].map(x=>({...x}));const r=consensus(A0,B0);
  assert.deepEqual(st(r),["agree:dye","agree:give away","onlyB:ghost","onlyA:fluent","agree:immediately"]);assert.deepEqual(tally(r),{agree:3,diff:0,onlyA:1,onlyB:1});
  assert.deepEqual(tally(consensus(A0,[])),{agree:0,diff:0,onlyA:4,onlyB:0});assert.deepEqual(tally(consensus([],A0)),{agree:0,diff:0,onlyA:0,onlyB:4})});
t("consensus：單字拼錯一個字母 → 差異，而且詞表也標可能拼錯",()=>{const B0=A0.map(x=>({...x}));B0[2]={...B0[2],en:"fluant"};const r=consensus(A0,B0);
  assert.equal(r[2].status,"diff");assert.deepEqual(r[2].fields.en.diff,{a:[["flu",false],["e",true],["nt",false]],b:[["flu",false],["a",true],["nt",false]]});
  assert.ok(ruleWarnings(B0[2],lex).some(x=>x.includes("fluant")));assert.deepEqual(ruleWarnings(A0[2],lex),[])});
t("consensus：中文差一個字 → 差異並標出那個字",()=>{const B0=A0.map(x=>({...x}));B0[3]={...B0[3],zh:"立即;馬上"};const r=consensus(A0,B0);
  assert.equal(r[3].status,"diff");assert.deepEqual(r[3].bad,["zh"]);assert.deepEqual(r[3].fields.zh.diff,{a:[["立",false],["刻",true],["；馬上",false]],b:[["立",false],["即",true],[";馬上",false]]})});
t("consensus：OCR 把詞性黏進英文、順序不同也配得上",()=>{const B0=[E("immediately","adv.","立刻；馬上","Please call me immediately."),E("fluent adj","片語","流利的","She is fluent in three languages.",""),A0[1],A0[0]];const r=consensus(A0,B0);
  assert.deepEqual(st(r),["agree:dye","agree:give away","diff:fluent","agree:immediately"]);
  const {ma}=alignEntries([E("abandon","v.","放棄","")],[E("obondan","v.","放棄","")]);assert.deepEqual(ma,[0])}); // 英文差太多時用相同的中文補配
t("charDiff／NORM",()=>{assert.deepEqual(charDiff("abc","abc"),{a:[["abc",false]],b:[["abc",false]]});assert.deepEqual(charDiff("","x"),{a:[],b:[["x",true]]});
  assert.equal(NORM.pos("V., N."),NORM.pos("v.,n."));assert.equal(NORM.pos("phr."),"片語");assert.notEqual(NORM.en("pick up"),NORM.en("pickup"));assert.notEqual(NORM.ex("A cat."),NORM.ex("a cat."))});
t("詞表：拼錯標出來；詞形變化、縮寫、所有格、專有名詞、文法記號不誤判",()=>{assert.ok(lex.size>70000);
  assert.deepEqual(unknownWords("abandan",lex),["abandan"]);assert.deepEqual(unknownWords("recieve",lex),["recieve"]);
  assert.deepEqual(unknownWords("The sailors abandaned the damaged ship.",lex,{sentence:true}),["abandaned"]);
  assert.deepEqual(unknownWords("Mary dyed her hair red. David's dog can't swim in Taipei, and Bruno doesn't care.",lex,{sentence:true}),[]);
  assert.deepEqual(unknownWords("talk sb out of N./V-ing",lex),[]);assert.deepEqual(unknownWords("see/regard ... as ...",lex),[]);assert.deepEqual(unknownWords("open the door(s) to sth",lex),[]);assert.deepEqual(unknownWords("well-known",lex),[]);
  assert.deepEqual(unknownWords("Tbe cat sat.",lex,{sentence:true}),["Tbe"]);                                  // 句首的字一定要查得到
  assert.deepEqual(unknownWords("We met Xyzzyx in Qwertia.",lex,{sentence:true}),[])});                       // 句中沒收錄的專有名詞略過
t("規則檢查：兩個引擎犯同一種錯也攔得下（片語黏成一個字、兩邊都拼錯）",()=>{
  assert.ok(isInflection("dye","dyed")&&isInflection("stop","stopped")&&isInflection("study","studies")&&isInflection("understand","understood")&&!isInflection("pickup","picked"));
  const glued={en:"pickup",pos:"",zh:"撿起；接（某人）",ex:"She picked up the coins from the floor.",blank:"picked"},w=ruleWarnings(glued,lex);
  assert.ok(w.some(x=>x.includes("規則變化"))&&w.some(x=>x.includes("詞性")));
  assert.ok(ruleWarnings(E("oportunity","n.","機會","This is a great oportunity."),lex).length>0);
  assert.ok(ruleWarnings(E("dye","v.","染色","Mary likes her hair red."),lex).some(x=>x.includes("找不到")));
  assert.ok(ruleWarnings({...A0[0],blank:"dyes"},lex).some(x=>x.includes("克漏字")));
  assert.ok(ruleWarnings(A0[0],null).some(x=>x.includes("詞表")));
  for(const w of A0)assert.deepEqual(ruleWarnings(w,lex),[]);
  const bad=W.filter(w=>ruleWarnings(w,lex).length);assert.ok(bad.length<=3,"內建字典被誤判的筆數："+bad.map(w=>w.en))});
t("測試書頁的正確答案：只有故意印錯的 recieve 會被規則檢查標出來",()=>{const T=JSON.parse(rd("tests/fixtures/truth.json")),all=Object.values(T).flat();assert.equal(all.length,26);
  assert.deepEqual(all.filter(w=>ruleWarnings(w,lex).length).map(w=>w.en),["recieve"]);for(const w of all)assert.equal(deriveBlank(w.en,w.pos,w.ex),w.blank,w.en)});
t("PP-OCR 字元表（YAML）解析",()=>{assert.deepEqual(parseDict("PostProcess:\n  name: CTCLabelDecode\n  character_dict:\n  - '!'\n  - ''''\n  - a\n  - \\\n  - 棄\nOther: 1\n"),["!","'","a","\\","棄"])});
console.log(`\n全部通過：${n} 項`);
