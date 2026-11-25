// 純邏輯檢查：node tests/check.mjs
import assert from 'node:assert/strict';
import { BUILTIN } from '../src/data/no307.js';
import { isPhrase, normEn, enVariants, checkEn, checkZh, nearZh, zhSegs, clozeAns, clozePos, zhPrompt, inflections, checkZhSmart, opts, mcOf, sayable } from '../src/core/grading.js';
import { normalizeState, normalizeSetup } from '../src/core/normalize.js';
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
t("normEn 去掉文法標記",()=>{assert.equal(normEn("let go of sth/sb"),"let go of");assert.equal(normEn("act as N."),"act as");assert.equal(normEn("be used to N./V-ing"),"be used to");assert.equal(normEn("open the door(s) to sth"),"open the door to")});
t("enVariants 斜線寫法任一個都算對",()=>{const v=enVariants("see/regard ... as ...");assert.ok(v.includes("see as"));assert.ok(v.includes("regard as"));assert.ok(checkEn("Regard as",by("see/regard ... as ...")));assert.ok(checkEn("immediately ",by("immediately")));assert.ok(!checkEn("imediately",by("immediately")))});
t("checkZh 與書上義項相同或互相包含",()=>{const w=by("abandon");assert.ok(checkZh("放棄",w.zh));assert.ok(checkZh("遺棄",w.zh));assert.ok(!checkZh("喜歡",w.zh));assert.ok(!checkZh("",w.zh));assert.deepEqual(zhSegs("放棄；拋棄、遺棄"),["放棄","拋棄","遺棄"])});
t("nearZh 共同字過半算意思相近",()=>{assert.ok(nearZh("喜好",["喜歡","愛好"]));assert.ok(!nearZh("桌子",["喜歡"]))});
t("clozeAns 用 blank 或字幹",()=>{assert.equal(clozeAns(by("dye")),"dyed");assert.equal(clozeAns({en:"recycle",pos:"v.",ex:"David recycles bottles.",blank:""}),"recycles");assert.equal(clozeAns(by("hold back")),"");assert.equal(clozeAns(by("give away")),"giving away")});
t("opts 4 個不重複選項且含答案、片語配片語",()=>{for(const key of ["zh","en","cloze"]){for(const w of [by("dye"),by("pick up"),by("fluent")]){const o=opts(w,key,W);const ans=key==="cloze"?clozeAns(w):w[key];assert.equal(o.length,4);assert.equal(new Set(o.map(x=>x.toLowerCase())).size,4);assert.ok(o.includes(ans))}}
  const o=opts(by("pick up"),"en",W);o.forEach(x=>assert.ok(/\s/.test(x)||x==="pick up"))});
t("mcOf／sayable",()=>{assert.equal(mcOf("en2zhT"),"en2zh");assert.equal(mcOf("zh2enT"),"zh2en");assert.equal(mcOf("cloze"),"cloze");assert.equal(sayable("talk sb out of N./V-ing"),"talk somebody out of");assert.equal(sayable("open the door(s) to sth"),"open the doors to something")});
t("parseOcr 規則式解析",()=>{const r=parseOcr("abandon v. 放棄；拋棄\nThe sailors abandoned the damaged ship.\ngive away 贈送、分送\nThe store is giving away free samples.");assert.equal(r.length,2);assert.equal(r[0].en,"abandon");assert.equal(r[0].pos,"v.");assert.equal(r[0].ex,"The sailors abandoned the damaged ship.");assert.equal(r[1].pos,"片語");
  const l=parseLines([{text:"dye v. 染色",y0:10,y1:12},{text:"Mary dyed her hair red.",y0:12,y1:14}]);assert.deepEqual(l[0].bbox,{y0:10,y1:14})});

/* ---------- 試用回報的修正 ---------- */
t("clozeAns 只挑真正的詞形變化，不挑 -er／-or／-ist 衍生名詞",()=>{const c=(en,pos,ex)=>clozeAns({en,pos,ex,blank:""});
  assert.equal(c("paint","v.","The painter painted the wall blue."),"painted");assert.equal(c("teach","v.","The teacher taught us math."),"taught");assert.equal(c("drive","v.","The driver drove us home."),"drove");
  assert.equal(c("paint","v.","The painter is very famous."),"");assert.equal(c("act","v.","The actor forgot his lines."),"");assert.equal(c("art","n.","The artist sold two works."),"");assert.equal(c("fluent","adj.","She speaks English fluently."),"");
  assert.equal(c("stop","v.","The bus stopped suddenly."),"stopped");assert.equal(c("study","v.","He studies and studied hard."),"studies");assert.equal(c("make","v.","She is making a cake."),"making");assert.equal(c("die","v.","The plant is dying."),"dying");
  assert.equal(c("watch","v.","He watches TV."),"watches");assert.equal(c("dye","v.","Mary dyed her hair."),"dyed");assert.equal(c("run","v.","He was running late."),"running");assert.equal(c("knife","n.","The knives are sharp."),"knives");assert.equal(c("child","n.","The children are playing."),"children");
  assert.equal(c("tall","adj.","Tom is taller than me."),"taller");assert.equal(c("happy","adj.","She is the happiest girl."),"happiest");assert.equal(c("good","adj.","This one is better."),"better");
  assert.equal(c("dog","n.","The dog's tail is long."),"dog");assert.equal(c("paint","v.","Paint the wall, painter!"),"Paint");
  assert.equal(clozeAns({en:"paint",pos:"v.",ex:"The painter came.",blank:"painter"}),"painter"); // 使用者自己填的 blank 仍然優先
  assert.ok(inflections("paint","v.").has("painting")&&!inflections("paint","v.").has("painter")&&!inflections("visit","v.").has("visitor"))});
t("clozePos 整個字比對，不會挖到別的字裡面",()=>{assert.equal(clozePos("The painter will paint the wall.","paint"),17);assert.equal(clozePos("Mary dyed her hair.","dyed"),5);assert.equal(clozePos("The store is giving away samples.","giving away"),13);assert.equal(clozePos("abc","")
,-1);assert.equal(clozePos("No such word.","xyz"),-1)});
t("enVariants：(s) 可有可無、受詞標記可省略、整個標題照抄也算對",()=>{const d=by("open the door(s) to sth");
  for(const a of ["open the door to","open the doors to","open the door to something","open the doors to sth","Open the door(s) to sth","open the door to sb"])assert.ok(checkEn(a,d),a);
  assert.ok(!checkEn("open the door",d));assert.ok(!checkEn("open door to",d));
  const s=by("see/regard ... as ...");for(const a of ["see/regard ... as ...","see/regard as","see as","regard ... as ...","regard as"])assert.ok(checkEn(a,s),a);assert.ok(!checkEn("see",s));
  assert.ok(checkEn("let go of",by("let go of sth/sb")));assert.ok(checkEn("let go of something",by("let go of sth/sb")));assert.ok(checkEn("let go of sth/sb",by("let go of sth/sb")));
  const m=by("make it + Adj./N. + (for sb/sth) + to V.");assert.ok(checkEn("make it to",m));assert.ok(checkEn("make it for to",m));assert.ok(checkEn("make it + Adj./N. + (for sb/sth) + to V.",m));
  for(const w of W)assert.ok(checkEn(w.en,w),"標題照抄要算對："+w.en)});
t("zhPrompt：中翻英題目遮掉中文欄裡的英文答案，字典內容不變",()=>{const c=by("capable");assert.ok(/capable/.test(c.zh));assert.equal(zhPrompt(c),"能幹的；有能力的");
  assert.equal(zhPrompt({en:"pick up",pos:"片語",zh:"撿起；接（某人）",ex:"",blank:""}),"撿起；接（某人）");assert.equal(zhPrompt({en:"dye",pos:"v.",zh:"染色 dyed 是過去式",ex:"",blank:""}),"染色 ＿＿ 是過去式");
  assert.equal(zhPrompt({en:"CD",pos:"n.",zh:"光碟（compact disc）",ex:"",blank:""}),"光碟（compact disc）");
  for(const w of W){const z=zhPrompt(w);assert.ok(z,w.en);for(const k of normEn(w.en).split(" "))if(k.length>=3)assert.ok(!new RegExp("\\b"+k+"\\b","i").test(z),"洩題："+w.en+" → "+z)}});
t("中文判分：一個字不能靠包含或共同字過關",()=>{const seg=zh=>zhSegs(zh),A=by("appearance"),L=by("let go of sth/sb");
  assert.ok(!checkZh("外",A.zh)&&!nearZh("外",seg(A.zh)));assert.ok(!checkZh("放",L.zh)&&!nearZh("放",seg(L.zh)));assert.ok(!nearZh("好",["喜好","愛好","愛"]));assert.ok(!nearZh("好",["很好的東西"]));
  assert.ok(checkZh("外貌",A.zh)&&checkZh("外表",A.zh)&&checkZh("放開",L.zh)&&checkZh("放棄",L.zh));
  assert.ok(nearZh("愛",["愛","喜愛"]));assert.ok(checkZh("愛","愛；喜愛"));          // 一個字但與義項完全相同
  assert.ok(nearZh("喜好",["愛","喜歡","愛好"]));assert.ok(nearZh("喜愛",["愛"]));    // 規格書驗收：輸入「喜好」答 love
  assert.ok(checkZh("立刻",by("immediately").zh));assert.ok(!checkZh("立",by("immediately").zh));
  assert.ok(!checkZh("棄","放棄；拋棄"));assert.ok(!nearZh("開啟機會創造",["開"]));assert.ok(!nearZh("桌子",["喜歡"]))});
// checkZhSmart 會連 Google：測試時把 fetch 換成假的（love 的翻譯結果）
const realFetch=globalThis.fetch;
const fakeG=(main,dict)=>async()=>({ok:true,json:async()=>[[[main]],[["verb",dict]]]});
const LOVE={id:"x1",en:"love",pos:"v./n.",zh:"愛；喜愛",ex:"",blank:""};
globalThis.fetch=async u=>{const q=decodeURIComponent(String(u).split("&q=")[1]||"");
  if(/sl=en/.test(u))return fakeG("愛",["喜歡","愛","愛好","熱愛"])();
  return fakeG(q==="好"?"good":q==="放"?"let go of":q==="喜好"?"love":"table",q==="放"?["put","let go of","release"]:[])()};
const smart=[await checkZhSmart("好",LOVE),await checkZhSmart("喜好",LOVE),await checkZhSmart("愛",LOVE),await checkZhSmart("放",by("let go of sth/sb")),await checkZhSmart("外",by("appearance")),await checkZhSmart("桌子",LOVE)];
globalThis.fetch=realFetch;
t("checkZhSmart：love 答「喜好」算對、答「好」不算；一個字不走 Google 那條路過關",()=>{assert.deepEqual(smart.map(r=>r.ok),[false,true,true,false,false,false])});
t("備份驗證：格式不完整就整份拒絕（丟出原因），不會回傳半套資料",()=>{const bad=j=>assert.throws(()=>normalizeState(j,{strict:true}),Error,JSON.stringify(j));
  bad({dicts:{x:{id:"x",name:"壞字典"}}});bad(null);bad([]);bad("abc");bad({});bad({dicts:[]});bad({dicts:{x:null}});bad({dicts:{x:{id:"x",words:[]}}});bad({dicts:{x:{name:"n",words:[]}}});
  bad({dicts:{x:{id:"x",name:"n",words:"no"}}});bad({dicts:{x:{id:"x",name:"n",words:[null]}}});bad({dicts:{x:{id:"x",name:"n",words:[{id:"a",zh:"沒有英文"}]}}});bad({dicts:{x:{id:"x",name:"n",words:[{id:"a",en:"a",zh:5}]}}});
  const ok=normalizeState({dicts:{x:{id:"x",name:"好字典",words:[{id:"a",en:"apple",zh:"蘋果"},{id:"a",en:"bee"},{en:"cat",pos:"n.",zh:"貓",ex:"A cat.",blank:"cat",unit:"U1",extra:1}]}}},{strict:true});
  assert.deepEqual(Object.keys(ok),["dicts","miss","hidden","wlog","hist","t"]);assert.deepEqual(ok.miss,{});assert.deepEqual(ok.hist,[]);assert.equal(ok.t,0);
  const ws=ok.dicts.x.words;assert.equal(ws.length,3);assert.deepEqual(ws[0],{id:"a",en:"apple",pos:"",zh:"蘋果",ex:"",blank:"",unit:""});assert.equal(new Set(ws.map(w=>w.id)).size,3);assert.deepEqual(Object.keys(ws[2]),["id","en","pos","zh","ex","blank","unit"]);
  // 真正匯出的備份原樣通過
  const real={dicts:{no307:{...BUILTIN,builtin:false}},miss:{no307:{b0:2}},hidden:{},wlog:{no307:{b0:{n:2,last:5,ans:[{a:"x",m:"en2zh",t:5}]}}},hist:[{t:1,mode:"en2zh",dict:"no307",n:10,right:9,wrong:[["no307","b0"]],game:false}],t:9};
  const r=normalizeState(JSON.parse(JSON.stringify(real)),{strict:true});assert.equal(r.dicts.no307.words.length,128);assert.deepEqual(r.miss,real.miss);assert.deepEqual(r.wlog,real.wlog);assert.deepEqual(r.hist,real.hist);assert.equal(r.t,9)});
t("啟動時的正規化：壞資料不丟例外，能救的留下、救不了的略過",()=>{for(const j of [null,undefined,5,"x",[],{},{dicts:null},{dicts:5,miss:[],wlog:"x",hist:{},hidden:1}])assert.deepEqual(normalizeState(j),{dicts:{},miss:{},hidden:{},wlog:{},hist:[],t:0});
  const r=normalizeState({dicts:{x:{id:"x",name:"壞字典"},y:{id:"zzz",name:"好",words:[{id:"1",en:"a",zh:"甲"},{id:"2",en:""},null,{id:"3",en:"c",zh:null,ex:7}]},z:{words:[{en:"q"}]}},miss:{y:{1:3,2:"x",3:-1},q:null},wlog:{y:{1:{n:2},2:null,3:{n:0}}},hist:[null,{t:"5",wrong:"x"}],hidden:{no307:1}});
  assert.deepEqual(Object.keys(r.dicts),["y","z"]);assert.equal(r.dicts.y.id,"y");assert.deepEqual(r.dicts.y.words.map(w=>w.en),["a","c"]);assert.equal(r.dicts.y.words[1].zh,"");assert.equal(r.dicts.y.words[1].ex,"7");assert.equal(r.dicts.z.name,"未命名字典");assert.ok(r.dicts.z.words[0].id);
  assert.deepEqual(r.miss,{y:{1:3}});assert.deepEqual(r.wlog,{y:{1:{n:2,last:0,ans:[]}}});assert.deepEqual(r.hist,[{t:5,mode:"",dict:"",n:0,right:0,wrong:[],game:false}]);assert.deepEqual(r.hidden,{no307:true})});
t("練習設定正規化：不認得的值退回預設",()=>{assert.deepEqual(normalizeSetup(null),{dict:"no307",mode:"en2zh",scope:"all",n:10,wrong:false,auto:true,exmode:false,game:false});
  assert.deepEqual(normalizeSetup({dict:5,mode:"xx",scope:"q",n:7,wrong:1,auto:"no",game:"soul",junk:1}),{dict:"no307",mode:"en2zh",scope:"all",n:10,wrong:true,auto:true,exmode:false,game:"soul"});
  assert.deepEqual(normalizeSetup({dict:"__all",mode:"cloze",scope:"p",n:0,wrong:false,auto:false,exmode:true,game:true}),{dict:"__all",mode:"cloze",scope:"p",n:0,wrong:false,auto:false,exmode:true,game:true})});

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
  assert.equal(fast.d,1);assert.ok(Math.abs(fast.limitMul-(1-SOUL.limitSwing))<1e-9);assert.equal(fast.extra,1);assert.equal(fast.perfectMs,SOUL.perfectMs-SOUL.perfectSwing);assert.equal(fast.dmgMul,1+SOUL.dmgBonus);
  // 答得慢：時限放寬，但 Boss 不會少出手（亂點會被判成「很慢」，不能讓它佔便宜）
  assert.equal(slow.d,-1);assert.ok(Math.abs(slow.limitMul-(1+SOUL.limitSwing))<1e-9);assert.equal(slow.extra,0);assert.equal(slow.perfectMs,SOUL.perfectMs+SOUL.perfectSwing);assert.equal(slow.dmgMul,1);assert.equal(bad.d,-1)});
t("魂系：玩家回合累積 ATB、迅擊、出招、時間用完換敵人",()=>{const E=createSoulBattle({pool,mode:"en2zhT",rng:()=>0});assert.deepEqual(types(E.start()),["bossEnter","playerTurn"]);
  let q=E.nextAttackQuestion();assert.equal(q.leftMs,SOUL.windowMs);let ev=E.answerAttack(true,3000);assert.deepEqual(types(ev),["atb"]);assert.equal(E.state.atb,1);assert.equal(E.state.atkLeft,SOUL.windowMs-3000);assert.equal(E.state.phase,"cmd");
  assert.deepEqual(types(E.command(0)),[]);assert.equal(E.state.phase,"pturn");
  // 答得再快，每題也至少消耗 minCostMs 的攻擊時間
  E.nextAttackQuestion();ev=E.answerAttack(true,1000);assert.deepEqual(types(ev),["atb","quickSlash","hit"]);assert.equal(ev[2].dmg,Math.round(SOUL.quickDmg*comboMult(2)));assert.equal(E.state.atb,2);assert.equal(E.state.atkLeft,SOUL.windowMs-3000-SOUL.minCostMs);
  ev=E.command(2);assert.deepEqual(types(ev).slice(0,4),["skill","hit","hit","hit"]);assert.equal(E.state.atb,0);assert.equal(E.state.phase,"cmd");assert.deepEqual(E.command(1),[]);
  // 答錯多扣 missPenaltyMs
  E.command(0);let left=E.state.atkLeft;E.nextAttackQuestion();ev=E.answerAttack(false,2600);assert.deepEqual(types(ev),["miss"]);assert.equal(E.state.atkLeft,Math.max(0,left-2600-SOUL.missPenaltyMs));
  assert.equal(E.state.atkLeft,0);
  ev=E.command(0);assert.deepEqual(types(ev),["windowEnd","enemyTurn"]);assert.equal(E.state.phase,"enemy")});
t("魂系：彈反／閃避／擦傷／格擋／中招與耐力",()=>{const b=SOUL_BOSSES[0],mkE=()=>{const E=createSoulBattle({pool,mode:"zh2enT",rng:()=>0});E.start();E.nextAttackQuestion();E.answerAttack(false,10000);E.command(0);return E};
  let E=mkE(),d=E.nextDodge();assert.equal(d.mode,"zh2en");assert.equal(d.limitMs,b.limitMs);assert.equal(types(d.events)[0],"telegraph");
  let ev=E.answerDodge(true,1000);assert.deepEqual(types(ev),["parry","counter","hit"]);assert.equal(E.state.atb,1);assert.equal(E.state.hp,100);assert.equal(E.nextDodge(),null);assert.deepEqual(types(E.startPlayerTurn()),["playerTurn"]);
  E=mkE();E.nextDodge();ev=E.answerDodge(true,2500);assert.deepEqual(types(ev),["dodge"]);assert.equal(E.state.stamina,SOUL.staminaMax-SOUL.dodgeCost);
  // 超過時限的 slowAt 才答對：擦傷
  E=mkE();E.nextDodge();ev=E.answerDodge(true,b.limitMs*SOUL.slowAt+100);assert.deepEqual(types(ev),["graze","playerHit"]);assert.equal(ev[1].dmg,Math.max(1,Math.round(b.atk*SOUL.grazeRate)));assert.equal(E.state.hp,100-ev[1].dmg);
  // 答錯／超時：耐力足夠就硬擋（扣 blockCost、只受 blockRate 的傷害）
  E=mkE();E.nextDodge();ev=E.answerDodge(false,b.limitMs+1,{timeout:true});assert.deepEqual(types(ev),["guard","playerHit"]);assert.equal(ev[0].blocked,true);assert.equal(ev[1].kind,"guard");assert.equal(ev[1].dmg,Math.max(1,Math.round(b.atk*SOUL.blockRate)));assert.equal(E.state.stamina,SOUL.staminaMax-SOUL.blockCost);assert.equal(E.state.combo,0);
  // 耐力不足以硬擋：吃全額
  E=mkE();E.state.stamina=SOUL.blockCost-1;E.nextDodge();ev=E.answerDodge(false,1200);assert.deepEqual(types(ev),["foeHit","playerHit"]);assert.equal(ev[1].dmg,b.atk);assert.equal(E.state.hp,100-b.atk);assert.equal(E.state.stamina,SOUL.blockCost-1);
  // 答對但耐力不足以翻滾：勉強格擋
  E=mkE();E.state.stamina=5;E.nextDodge();ev=E.answerDodge(true,2500);assert.deepEqual(types(ev),["guard","playerHit"]);assert.equal(ev[1].dmg,Math.max(1,Math.round(b.atk*SOUL.guardRate)));assert.equal(E.state.stamina,0)});
t("魂系：Boss 階段轉換、擊倒後換下一隻（回復 HP、ATB 歸零）、全破",()=>{const E=createSoulBattle({pool,mode:"en2zh",rng:()=>0});E.start();E.state.atb=3;E.state.phase="cmd";
  let ev=E.command(3);assert.ok(types(ev).includes("bossPhase"));assert.equal(E.state.bphase,1);assert.ok(E.state.mhp>0&&E.state.mhp<=SOUL_BOSSES[0].hp*SOUL_BOSSES[0].phases[0].at);
  E.state.atb=3;E.state.hp=30;E.state.phase="cmd";ev=E.command(1);assert.deepEqual(types(ev),["skill","hit","faint","heal","bossEnter","playerTurn"]);assert.equal(E.state.mi,1);assert.equal(E.state.bphase,0);assert.equal(E.state.phase,"pturn");
  assert.equal(E.state.hp,30+SOUL.healOnKill);assert.equal(E.state.atb,0);
  let guard=0;while(E.state.phase!=="end"&&guard++<400){E.state.atb=3;E.state.phase="cmd";ev=E.command(3)}
  assert.equal(E.result().win,true);assert.equal(E.result().kills,SOUL_BOSSES.length);assert.equal(ev.at(-1).type,"win")});
t("魂系：高手也一定會遇到敵人回合（每回合最多 4 題、換 Boss 時 ATB 歸零）",()=>{const E=createSoulBattle({pool,mode:"en2zh",rng:()=>.5});E.start();let n=0;
  // 每題 0.5 秒全對、能出大招就出：第 2 隻 Boss 不可能在第一個玩家回合內倒下
  E.state.mi=1;E.state.mhp=SOUL_BOSSES[1].hp;E.state.combo=20;
  while(E.state.phase!=="end"&&E.state.phase!=="enemy"&&n++<50){const p=E.state.phase;if(p==="pturn"){const q=E.nextAttackQuestion();if(!q)E.startEnemyTurn();else E.answerAttack(true,500)}else if(p==="cmd"){const c=E.commands().filter(c=>c.ready).pop();E.command(c?c.k:0)}}
  assert.equal(E.state.phase,"enemy");assert.equal(E.state.mi,1);assert.ok(E.state.n<=Math.ceil(SOUL.windowMs/SOUL.minCostMs))});
t("魂系：startPlayerTurn 重複呼叫不會開兩次回合（按鈕連點防護）",()=>{const E=createSoulBattle({pool,mode:"en2zh",rng:()=>0});E.start();E.nextAttackQuestion();E.answerAttack(false,10000);E.command(0);
  E.nextDodge();E.answerDodge(true,2500);assert.equal(E.nextDodge(),null);const sta=E.state.stamina;
  assert.deepEqual(types(E.startPlayerTurn()),["playerTurn"]);assert.equal(E.state.stamina,Math.min(SOUL.staminaMax,sta+SOUL.staminaTurn));const q=E.nextAttackQuestion();
  assert.deepEqual(E.startPlayerTurn(),[]);assert.equal(E.state.stamina,Math.min(SOUL.staminaMax,sta+SOUL.staminaTurn));assert.equal(E.state.phase,"q");assert.equal(E.state.w,q.w)});
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
// 掃描「漏網」情境（試用測試找到的問題）另外放在 scan.check.mjs
await import("./scan.check.mjs");
