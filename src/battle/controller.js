// 戰鬥控制器：把規則引擎（monster.js／soul.js）、HUD（DOM）與戰鬥畫面（view3d.js）接在一起。
// 計時、作答、朗讀、錯題紀錄都在這裡；規則本身在引擎裡，畫面動畫在 view 裡。
import { $, app, esc, ask, SC, wait, lsGet, lsSet } from '../core/util.js';
import { setup, mark, pushHist, allWords, ctx } from '../core/store.js';
import { clozeAns, opts, normEn, checkEn, checkZhSmart } from '../core/grading.js';
import { speak, readAll, gate, spkBtn, stopSpeech } from '../core/speech.js';
import { sfx, bgmStart, bgmStop, bgmToggle, bgmOn } from '../core/audio.js';
import { MON, SKILLS, MAXEN, STORY, SOUL_STORY, SOUL_BOSSES } from './data.js';
import { createMonsterBattle, comboMult } from './monster.js';
import { createSoulBattle } from './soul.js';
import { mount } from './view3d.js';
import { wordRow } from '../pages/dicts.js';
import { toSetup, exLine, startQuiz } from '../pages/practice.js';

const RM=matchMedia("(prefers-reduced-motion: reduce)").matches;
let T=null; // 目前這場戰鬥：{E 引擎, view, soul, phase, …}
const alive=t=>t===T&&ctx.B===t;
const say=(t,cls)=>{const el=$("#msg");if(!el)return;el.className="msgbox "+(cls||"");el.textContent=t};

export function startBattle(ws,soul){if(!ws.length)return;ctx.Q=null;stopSpeech();
  const t=T=ctx.B={soul:!!soul,mode:setup.mode,pool:ws,bank:allWords(),phase:"busy",readP:Promise.resolve(),raf:0,tmo:0,seq:0};
  t.E=(soul?createSoulBattle:createMonsterBattle)({pool:ws,mode:setup.mode});
  document.body.classList.add("inbattle");document.body.classList.toggle("soulmode",!!soul);window.scrollTo(0,0);
  app.innerHTML=`<div class="bwrap ${soul?"soul":""}"><div class="row btop"><button class="sm ghost" id="run" style="padding-left:0;min-height:32px">← 逃跑</button><button class="sm ghost" id="bgmb" style="min-height:32px">${bgmOn()?"♪ 音樂開":"♪ 音樂關"}</button><span class="small" style="margin-left:auto" id="bstat"></span></div>
  <div class="arenawrap"><div class="arena" id="arena"></div>
   <div class="hpbox foe"><div class="row" style="gap:6px;flex-wrap:nowrap"><b id="fname"></b><span class="small" id="flv"></span></div><div class="hp"><span>HP</span><div><i id="fhp"></i></div></div><div class="small" style="text-align:right" id="fhpt"></div></div>
   <div class="hpbox me"><div class="row" style="gap:6px;flex-wrap:nowrap"><b>你</b><span class="small" id="combo"></span><span class="small" id="diff" style="margin-left:auto"></span></div><div class="hp"><span>HP</span><div><i id="php"></i></div><b id="phpt"></b></div>
    ${soul?'<div class="enb sta"><span>耐力</span><div><i id="pst"></i></div><b id="pstt"></b></div>':""}
    <div class="enb"><span id="enl">${soul?"ATB":"能量"}</span><div><i id="pen"></i></div><b id="pent"></b></div></div>
   <div id="ovl"></div></div>
  <div class="msgbox" id="msg"></div><div id="bq"></div></div>`;
  t.view=mount($("#arena"),{kind:soul?"soul":"monster",getState:()=>t.E.snapshot(),foes:soul?SOUL_BOSSES:MON,reducedMotion:RM});
  $("#bgmb").onclick=bgmToggle;bgmStart();
  $("#run").onclick=async()=>{if(await ask("要逃跑嗎？這場戰鬥的進度不會保留。")){endBattle();toSetup()}};
  hud(t.E.snapshot());
  const key=soul?"vc-story-soul":"vc-story";
  (lsGet(key,"0")==="1"?Promise.resolve():story(t,soul?SOUL_STORY:STORY,key)).then(async()=>{if(!alive(t))return;await run(t,t.E.start());if(!alive(t))return;soul?sQ(t):mReady(t)})}

// 離開戰鬥（逃跑、換頁、結束）時清理
export function endBattle(){const t=T;if(!t)return;cancelAnimationFrame(t.raf);clearTimeout(t.tmo);try{t.view&&t.view.dispose()}catch(e){}T=null;ctx.B=null;document.body.classList.remove("inbattle","soulmode");bgmStop()}

/* ---------- 序章 ---------- */
function story(t,lines,key){return new Promise(res=>{const st=document.createElement("div");st.className="story";st.innerHTML=`<button class="sm sskip" id="sskip">跳過序章 ✕</button><div class="sbox"><p id="stxt"></p><div class="row" style="justify-content:space-between;margin-top:8px"><span class="small" id="spg" style="color:#555"></span><button class="sm pri" id="snext">繼續 ▶</button></div></div>`;$("#ovl").appendChild(st);
  let i=0;const show=()=>{$("#stxt").textContent=lines[i];$("#spg").textContent=`${i+1} / ${lines.length}　點畫面任何地方繼續`};show();say("序章（可跳過）");
  const done=()=>{t.storyNext=t.storySkip=null;lsSet(key,"1");st.remove();res()};
  const nx=()=>{i++;if(i<lines.length)show();else done()};st.onclick=e=>{if(e.target.closest("#sskip"))done();else nx()};t.storyNext=nx;t.storySkip=done})}

/* ---------- HUD ---------- */
function hud(s,part){if(!$("#fhp"))return;const t=T;if(!t)return;const foe=t.soul?SOUL_BOSSES[s.mi]:MON[s.mi];
  const setBar=(el,r)=>{el.style.transform=`scaleX(${Math.max(0,Math.min(1,r))})`;el.dataset.c=r>.5?"g":r>.2?"y":"r"};
  if(part!=="me"){$("#fname").textContent=foe.name+(t.soul&&s.bphase?`・第 ${s.bphase+1} 階段`:"");$("#flv").textContent="Lv."+foe.lv;setBar($("#fhp"),s.mhp/s.mhpMax);$("#fhpt").textContent=Math.ceil(s.mhp)+" / "+s.mhpMax}
  if(part!=="foe"){setBar($("#php"),s.hp/s.hpMax);$("#phpt").textContent=s.hp;
    if(t.soul){$("#pen").style.transform=`scaleX(${s.atb/s.atbMax})`;$("#pent").textContent=s.atb+"/"+s.atbMax;$("#pst").style.transform=`scaleX(${s.stamina/s.staminaMax})`;$("#pstt").textContent=s.stamina;
      $("#diff").textContent=s.pace==null?"":s.d>=.6?"難度 ▲▲":s.d>=.2?"難度 ▲":s.d<=-.6?"難度 ▽▽":s.d<=-.2?"難度 ▽":"難度 ＝"}
    else{$("#pen").style.transform=`scaleX(${s.en/s.enMax})`;$("#pent").textContent=s.en+"/"+s.enMax}
    $("#combo").textContent=s.combo>=2?`連擊 ×${s.combo}`:""}
  $("#bstat").textContent=`第 ${s.mi+1} / ${(t.soul?SOUL_BOSSES:MON).length} 隻・答對 ${s.right} / ${s.n}`}

// 依序播放引擎回傳的事件：更新訊息與音效 → 交給畫面播放 → 同步 HUD
const MSG={
  enter:e=>[`野生的 ${e.monster.name} 出現了！`],
  bossEnter:e=>[`${e.boss.name} 擋在你面前。`,"bad"],
  chainStart:e=>[`連招「${e.skill.name}」蓄力開始！連續答對 ${e.skill.chain.length} 題才會發動，中途答錯就中斷。`,"good"],
  chainFire:e=>[`連續答對 ${e.skill.chain.length} 題！發動「${e.skill.name}」！`,"good"],
  chainDone:e=>[`${e.skill.name} 打完了！`,"good"],
  chainBreak:()=>["連招中斷了…","bad"],
  skill:e=>[`${e.name}！`],
  quickSlash:()=>["答得夠快，追加迅擊！","good"],
  foeAttack:e=>[`${e.timeout?"時間到！":"答錯了！"}${e.monster.name} 使出了 ${e.move}！`,"bad"],
  playerTurn:e=>[`你的回合！${e.windowMs/1000} 秒內盡量答對，累積 ATB 出招！（讀音與出招時時間暫停）`,"good"],
  windowEnd:()=>["攻擊時間結束！","bad"],
  enemyTurn:e=>[`${e.boss.name} 的回合，準備閃避 ${e.total} 次攻擊！`,"bad"],
  bossPhase:e=>[`${e.boss.name} 進入第 ${e.phase+1} 階段——${e.info.name}！`,"bad"],
  telegraph:e=>[`${e.boss.name} 準備使出 ${e.move}！快答對才能彈反！`,"bad"],
  parry:()=>["彈反成功！ATB +1，立刻反擊！","good"],
  dodge:()=>["翻滾閃避成功！","good"],
  guard:()=>["耐力不足，只能勉強格擋！","bad"],
  graze:()=>["答得太慢，被擦傷！","bad"],
  foeHit:e=>[e.timeout?"來不及了！":"答錯了，沒有躲開！","bad"],
  faint:e=>[`${(e.monster||e.boss).name} 倒下了！`,"good"],
  heal:e=>[`你恢復了 ${e.amount} HP！`,"good"],
};
const SFX={gain:"shot",atb:"shot",chainStart:"shot",chainCharge:"shot",telegraph:"hurt",parry:"parry",dodge:"shot",faint:"faint",heal:"win"};
async function run(t,events){for(const e of events){if(!alive(t))return;const m=MSG[e.type]&&MSG[e.type](e);if(m)say(m[0],m[1]);if(SFX[e.type])sfx(SFX[e.type]);
    const s=e.s;
    if(e.type==="hit"){e.onImpact=()=>{sfx(e.big||e.dmg>=40?"crit":"hit");hud(s,"foe")}} // 命中瞬間才扣怪物血
    else if(e.type==="playerHit"){e.onImpact=()=>{sfx("hurt");hud(s,"me")}}
    else hud(s);
    if(e.type==="win")sfx("win");if(e.type==="lose")sfx("lose");
    await t.view.play(e.type,e);if(!alive(t))return;hud(s)}}

/* ---------- 題目卡（兩種模式共用） ---------- */
function qCard(t,w,m,o={}){let prompt="",body="";
  if(m==="en2zh"||m==="en2zhT")prompt=`<div class="row" style="gap:8px;flex-wrap:nowrap"><div class="bprompt en">${esc(w.en)}</div>${o.plain?"":spkBtn(w.en)}<span class="small">${esc(w.pos)}</span></div>${o.plain?"":exLine(w,false)}`;
  else if(m==="zh2en"||m==="zh2enT")prompt=`<div class="bprompt zh">${esc(w.zh)}</div>${m==="zh2enT"?`<div class="small">提示：${esc(w.en.trim()[0]||"")}… 共 ${normEn(w.en).replace(/ /g,"").length} 個字母</div>`:""}${o.plain?"":exLine(w,true)}`;
  else{const a=clozeAns(w),i=w.ex.toLowerCase().indexOf(a.toLowerCase());prompt=`<div class="cloze" style="font-size:17px;line-height:1.45">${esc(w.ex.slice(0,i))}<span class="blank">　?　</span>${esc(w.ex.slice(i+a.length))}</div><div class="small">提示：${esc(w.zh)}</div>`}
  if(m==="en2zh"||m==="zh2en"||m==="cloze"){const key=m==="en2zh"?"zh":m==="zh2en"?"en":"cloze";t.ans=key==="cloze"?clozeAns(w):w[key];t.opts=opts(w,key,t.bank);
    body=`<div class="bopts" id="bopts">${t.opts.map((x,i)=>`<button data-o="${i}" class="${key==="zh"?"":"en"}"><span class="k">${i+1}</span>${esc(x)}</button>`).join("")}</div>`}
  else{t.opts=null;body=`<form id="btf" class="row" style="margin-top:8px"><input id="bti" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="${m==="en2zhT"?"輸入中文意思":"輸入英文"}" style="flex:1 1 160px;width:auto"><button class="pri">送出</button></form>`}
  return `<div class="bqcard ${o.cls||""}" id="bqc"><div class="tline"><i id="tb"></i></div>${w._rep?'<div class="small" style="color:var(--bad);font-weight:700">剛剛答錯，再考一次</div>':""}${prompt}${body}<div id="bans"></div></div>`}
// 接上作答：cb(ok, 選項索引, 作答內容, 近義說明)。填空英翻中要等 Google 判定，期間暫停計時。
function hook(t,w,m,cb,onPause){const o=$("#bopts");if(o)o.onclick=e=>{const b=e.target.closest("[data-o]");if(b&&t.phase==="q"){t.phase="busy";cb(t.opts[+b.dataset.o]===t.ans,+b.dataset.o,t.opts[+b.dataset.o])}};
  const f=$("#btf");if(f){const ti=$("#bti");ti.focus();f.onsubmit=e=>{e.preventDefault();if(t.phase!=="q")return;const v=ti.value;if(!v.trim())return;t.phase="busy";ti.readOnly=true;
    if(m==="en2zhT"){onPause&&onPause();say("判斷中…");checkZhSmart(v,w).then(r=>{if(alive(t))cb(r.ok,-1,v,r.loose)})}else cb(checkEn(v,w),-1,v)}}}
function markOpts(t,idx){app.querySelectorAll("#bopts button").forEach((b,i)=>{b.disabled=true;if(t.opts[i]===t.ans)b.classList.add("right");else if(i===idx)b.classList.add("wrong")});const bi=$("#bti");if(bi)bi.readOnly=true}
function answerLine(w,ok){const el=$("#bans");if(!el)return;el.innerHTML=`<div class="ansline ${ok?"ok":"no"}"><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span> ${spkBtn(w.en)}<span class="zhm">${esc(w.zh)}</span></div>`}
// 倒數條。回傳 {elapsed(), stop()}；時間到呼叫 onEnd。
function timer(t,totalMs,startLeft,els,onEnd){const t0=performance.now();let stopped=false,at=0;
  const draw=left=>{const s=`scaleX(${Math.max(0,left/totalMs)})`;els.forEach(e=>{if(e)e.style.transform=s})};draw(startLeft);
  const tick=()=>{if(stopped||!alive(t))return;const left=startLeft-(performance.now()-t0);draw(left);if(left<=0){stopped=true;at=startLeft;onEnd&&onEnd();return}t.raf=requestAnimationFrame(tick)};t.raf=requestAnimationFrame(tick);
  return{elapsed:()=>stopped?at:Math.min(startLeft,performance.now()-t0),stop(){if(!stopped){at=Math.min(startLeft,performance.now()-t0);stopped=true;cancelAnimationFrame(t.raf)}return at}}}
function closeMenu(){const s=$("#skov");if(s)s.remove()}

/* ---------- 打怪模式 ---------- */
function mReady(t){if(!alive(t)||!$("#bq"))return;t.phase="ready";closeMenu();const c=t.E.state.chain,S=t.E.state;
  $("#bq").innerHTML=c?`<button class="pri go chaingo" id="gonext">${esc(c.s.name)}・蓄力 第 ${c.stage+1} / ${c.s.chain.length} 題 ▶<span style="font-size:13px;font-weight:500">限時 ${c.s.times[c.stage]} 秒！${c.s.chain.length} 題全對才會發動（Enter）</span></button>`:`<button class="pri go" id="gonext">下一題 ▶<span style="font-size:13px;font-weight:500">按下後才開始計時（Enter）</span></button>`;
  $("#gonext").onclick=()=>mQuestion(t);gate($("#gonext"),t.readP,c?"朗讀中…（聽完就能繼續蓄力）":"朗讀中…（英文→中文→例句）");
  if(c){if(!/連招/.test($("#msg").textContent))say(`連招蓄力中：${c.s.name}（${c.stage}/${c.s.chain.length}）`,"good")}else if(!/出現|倒下|恢復|連招/.test($("#msg").textContent))say(`能量 ${S.en}/${MAXEN}。準備好就按「下一題」。`)}
function mQuestion(t){if(!alive(t)||t.phase!=="ready")return;const q=t.E.nextQuestion(),w=q.w,m=q.mode;t.phase="q";
  $("#bq").innerHTML=qCard(t,w,m,{cls:q.chain?"chainq":""});
  if(q.chain)say(`連招蓄力 ${q.chain.stage+1}/${q.chain.total}：${q.limitMs/1000} 秒內答對！`,"bad");else say(`${t.E.monster.name} 正盯著你…越快答對，能量越多！`);
  const fin=(ok,idx,given,loose,opt)=>mAnswer(t,w,ok,idx,given,tm.stop()/1000,loose,opt);
  // 一般題的計時條只影響能量，不會超時；連招題超時算答錯
  const tm=timer(t,q.limitMs,q.limitMs,[$("#tb")],q.timed?()=>{if(t.phase==="q"){t.phase="busy";say("時間到！","bad");fin(false,-1,"（超時）",null,{timeout:true})}}:null);
  hook(t,w,m,fin,()=>tm.stop());
  if(setup.auto&&(m==="en2zh"||m==="en2zhT"))speak(w.en,$("#bq .spk"))}
async function mAnswer(t,w,ok,idx,given,sec,loose,opt){mark(w,ok,given,t.mode);if(t.opts)markOpts(t,idx);else markOpts(t,-9);answerLine(w,ok);t.readP=readAll(w,$("#bans .spk"));
  const evs=t.E.answer(ok,sec,opt||{});const g=evs.find(e=>e.type==="gain");
  if(ok&&g&&!t.E.state.chain&&t.E.state.phase==="skill")say(`答對了！${loose?"（"+loose+"）":""}${sec.toFixed(1)} 秒，+${g.raw} 能量`+(t.E.state.en===MAXEN?"（已滿）":"")+"。看一下單字，再選招式。","good");
  await run(t,evs);if(!alive(t))return;const ph=t.E.state.phase,c=t.E.state.chain;
  if(ph==="end")return finish(t);
  if(ph==="skill")return mSkills(t);
  if(ph==="wrong"){t.phase="wrong";say("答錯了，記住正確答案。","bad");const nb=document.createElement("button");nb.className="pri nextbtn";nb.id="bnx";nb.textContent="下一題 ▶";$("#bqc").appendChild(nb);
    nb.onclick=()=>{t.E.ack();t.phase="ready";mQuestion(t)};gate(nb,t.readP,"朗讀中…");nb.focus({preventScroll:true});return}
  if(c)say(`連招蓄力 ${c.stage}/${c.s.chain.length}！（${sec.toFixed(1)} 秒）再答對 ${c.s.chain.length-c.stage} 題就能發動「${c.s.name}」`,"good");
  mReady(t)}
function mSkills(t){if(!alive(t))return;t.phase="skill";const S=t.E.state,mult=comboMult(S.combo);closeMenu();
  const ov=document.createElement("div");ov.className="skov";ov.id="skov";
  ov.innerHTML=`<div class="row" style="margin-bottom:6px;flex-wrap:nowrap"><b>選擇招式</b><span class="small" style="margin-left:auto;color:#5ad1ff">能量 ${S.en}/${MAXEN}${mult>1?`・×${mult.toFixed(1)}`:""}</span><button class="skip sm" data-s="-1" style="min-height:32px;padding:2px 10px">不出招</button></div><div class="skills">${SKILLS.map((s,i)=>s.chain?"":`<button data-s="${i}" ${S.en<s.cost?"disabled":""}><b><span class="k">${i+1}</span>${s.name}</b><span class="c">${s.cost?"⚡"+s.cost:"免費"}・約 ${Math.round(s.hits.reduce((a,b)=>a+b,0)*mult)}</span></button>`).join("")}<div class="chl"><b>連招（不耗能量、還會累積能量）</b> 連續答對指定題數後一次打出整套，限時較短</div>${SKILLS.map((s,i)=>s.chain?`<button class="chainb" data-s="${i}"><b><span class="k">${i+1}</span>${s.name}</b><span class="c">連對 ${s.chain.length} 題・約 ${Math.round(s.stages.flat().reduce((a,b)=>a+b,0)*mult)}</span></button>`:"").join("")}</div>`;
  $("#ovl").appendChild(ov);
  ov.onclick=async e=>{const b=e.target.closest("[data-s]");if(!b||b.disabled||t.phase!=="skill")return;const i=+b.dataset.s;closeMenu();t.phase="busy";
    if(i<0)say(`保留能量 ${S.en}/${MAXEN}。`);
    await run(t,t.E.useSkill(i));if(!alive(t))return;if(t.E.state.phase==="end")return finish(t);mReady(t)}}

/* ---------- 魂系模式 ---------- */
const atbHtml=s=>"ATB "+[0,1,2].map(i=>`<b class="${i<s.atb?"on":""}"></b>`).join("");
const soulHud=()=>`<div class="shud"><span id="sphase"></span><div class="stime"><i id="stb"></i></div><span id="satb" class="satb"></span></div>`;
// 玩家回合：出題累積 ATB
function sQ(t){if(!alive(t)||!$("#bq"))return;++t.seq;t.view.setTimeScale(1);closeMenu();const q=t.E.nextAttackQuestion();
  if(!q)return run(t,t.E.startEnemyTurn()).then(()=>alive(t)&&sEnemy(t));
  const w=q.w,m=q.mode;t.phase="q";t.qkind="atk";
  $("#bq").innerHTML=soulHud()+qCard(t,w,m);$("#sphase").textContent="攻擊時間";$("#satb").innerHTML=atbHtml(t.E.snapshot());
  const tm=timer(t,q.windowMs,q.leftMs,[$("#stb"),$("#tb")],async()=>{if(t.phase!=="q")return;t.phase="busy";markOpts(t,-9);await run(t,t.E.attackTimeout());if(alive(t))sEnemy(t)});
  hook(t,w,m,async(ok,idx,given,loose)=>{const ms=tm.stop();mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok);t.readP=readAll(w,$("#bans .spk"));
    const evs=t.E.answerAttack(ok,ms),s=t.E.snapshot();$("#satb").innerHTML=atbHtml(s);
    say(ok?`答對！${loose?"（"+loose+"）":""}ATB ${s.atb}/3。剩餘攻擊時間 ${(s.atkLeft/1000).toFixed(1)} 秒`:`答錯了！剩餘攻擊時間 ${(s.atkLeft/1000).toFixed(1)} 秒`,ok?"good":"bad");
    await run(t,evs);if(!alive(t))return;const ph=t.E.state.phase;if(ph==="end")return finish(t);if(ph==="pturn")return sQ(t);sCmd(t)},()=>tm.stop());
  if(setup.auto&&(m==="en2zh"||m==="en2zhT"))speak(w.en,$("#bq .spk"))}
// 指令選單（時間減速）
function sCmd(t){if(!alive(t))return;const seq=++t.seq;t.phase="cmd";t.view.setTimeScale(.3);closeMenu();const S=t.E.snapshot(),cmds=t.E.commands();
  const ov=document.createElement("div");ov.className="skov cmdov";ov.id="skov";
  ov.innerHTML=`<div class="row" style="margin-bottom:6px;flex-wrap:nowrap"><b>指令（時間減速中）</b><span class="small" style="margin-left:auto;color:#5ad1ff">ATB ${S.atb}/3</span></div><div class="skills">${cmds.map(c=>`<button data-c="${c.k}" ${c.ready?"":"disabled"} class="${c.big?"chainb":""}"><b><span class="k">${c.k}</span>${c.name}</b><span class="c">ATB ${c.bars}・約 ${c.approx}</span></button>`).join("")}<button class="skip" data-c="0" id="cgo"><b><span class="k">0</span>${S.atkLeft>0?"繼續答題":"結束攻擊"}</b><span class="c">${S.atkLeft>0?"保留 ATB":"輪到敵人"}</span></button></div>`;
  $("#ovl").appendChild(ov);gate($("#cgo"),t.readP,"朗讀中…");
  ov.onclick=async e=>{const b=e.target.closest("[data-c]");if(!b||b.disabled||t.phase!=="cmd")return;const k=+b.dataset.c;t.phase="busy";closeMenu();
    if(k)t.view.setTimeScale(k===3?.6:.85);else t.view.setTimeScale(1);
    await run(t,t.E.command(k));if(!alive(t))return;t.view.setTimeScale(1);const ph=t.E.state.phase;
    if(ph==="end")return finish(t);if(ph==="pturn")return sQ(t);if(ph==="enemy")return sEnemy(t);
    await t.readP;if(alive(t)&&t.seq===seq&&t.phase==="busy")sCmd(t)}}
// 敵人回合：每次攻擊先蓄力，再出一題限時閃避題
async function sEnemy(t){if(!alive(t))return;++t.seq;closeMenu();t.view.setTimeScale(1);t.phase="busy";const d=t.E.nextDodge();
  if(!d){await run(t,t.E.startPlayerTurn());if(alive(t))sQ(t);return}
  $("#bq").innerHTML=soulHud();$("#sphase").textContent=`敵人攻擊 ${d.index+1}/${d.total}`;$("#satb").innerHTML=atbHtml(t.E.snapshot());
  await run(t,d.events);if(!alive(t))return;const w=d.w,m=d.mode;
  $("#bq").innerHTML=soulHud()+qCard(t,w,m,{cls:"chainq",plain:true});$("#sphase").textContent=`閃避！${(d.limitMs/1000).toFixed(1)} 秒`;$("#satb").innerHTML=atbHtml(t.E.snapshot());t.phase="q";t.qkind="dodge";
  let done=false;
  const fin=async(ok,idx,given,opt)=>{if(done)return;done=true;const ms=tm.stop();t.phase="busy";mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok);t.readP=readAll(w,$("#bans .spk"));
    await run(t,t.E.answerDodge(ok,opt&&opt.timeout?d.limitMs+1:ms,opt||{}));if(!alive(t))return;const ph=t.E.state.phase;
    if(ph==="end"){await wait(400);return alive(t)&&finish(t)}
    const nb=document.createElement("button");nb.className="pri nextbtn";nb.id="bnx";nb.textContent="繼續 ▶";$("#bqc").appendChild(nb);t.phase="wrong";gate(nb,t.readP,"朗讀中…");
    nb.onclick=()=>{t.phase="busy";ph==="pturn"?sQ(t):sEnemy(t)}};
  const tm=timer(t,d.limitMs,d.limitMs,[$("#stb"),$("#tb")],()=>{if(t.phase==="q"){t.phase="busy";say("來不及了！","bad");fin(false,-9,"（超時）",{timeout:true})}});
  hook(t,w,m,(ok,idx,given)=>fin(ok,idx,given))}

/* ---------- 結束畫面 ---------- */
function finish(t){const r=t.E.result(),soul=t.soul,pl=t.pool;endBattle();stopSpeech();
  pushHist({t:Date.now(),mode:t.mode,dict:setup.dict,n:r.n,right:r.right,wrong:r.wrong.map(w=>[w.dict||setup.dict,w.id]),game:soul?"soul":true});
  const title=r.win?(soul?"噬語魔王被討伐了！":"史萊姆魔王被擊敗了！"):"你倒下了…";
  const sub=r.win?(soul?"詞語之火重新點燃，灰燼中的王國再次有了名字。":"詞語之力回到了艾爾文斯大陸，你成為了真正的魔劍士。"):(soul?"灰燼會記得你。複習單字，再次挑戰。":"別灰心，見習魔劍士，複習單字再出發吧！");
  app.innerHTML=`<div class="cut qcard">${SC}<div class="tab"><span>${r.win?"VICTORY":"GAME OVER"}</span></div><div class="body" style="text-align:center">
   <div class="big" style="font-size:clamp(34px,9vw,60px)">${title}</div><p class="small">${sub}</p>
   <p>打倒 ${r.kills} / ${r.total} 隻${soul?" Boss":"怪物"}・答對 ${r.right} / ${r.n} 題・最高連擊 ×${r.best}${r.fast<99?`・最快 ${r.fast.toFixed(1)} 秒`:""}${soul?`・彈反 ${r.parries} 次`:""}</p>
   <div class="row" style="justify-content:center"><button class="pri" id="again">再戰一次</button>${r.wrong.length?'<button id="rw">只練這次錯的</button>':""}<button id="chg">回設定</button></div></div></div>
   ${r.wrong.length?`<h2>這場答錯的（${r.wrong.length}）</h2><div class="cut">${SC}<div class="tab"><span>REVIEW</span></div><div class="body list">${r.wrong.map(w=>wordRow(w,true)).join("")}</div></div>`:""}`;
  $("#again").onclick=()=>startBattle(pl,soul);$("#chg").onclick=toSetup;const rw=$("#rw");if(rw)rw.onclick=()=>startQuiz(r.wrong)}

/* ---------- 鍵盤：Enter 下一題、1–4 作答、1–9 選招、0 不出招；魂系 1–3 出招、0／Enter 繼續 ---------- */
document.addEventListener("keydown",e=>{const t=T;if(!t||!ctx.B||ctx.view!=="practice"||e.target.tagName==="INPUT")return;
  if(t.storyNext){if(e.key==="Enter"||e.key===" "){e.preventDefault();t.storyNext()}else if(e.key==="Escape")t.storySkip();return}
  if(t.phase==="ready"&&(e.key==="Enter"||e.key===" ")){e.preventDefault();const g=$("#gonext");if(g&&!g.disabled)g.click()}
  else if(t.phase==="q"&&/^[1-4]$/.test(e.key)){const b=app.querySelector(`#bopts [data-o="${+e.key-1}"]`);if(b)b.click()}
  else if(t.phase==="skill"&&/^[0-9]$/.test(e.key)){const b=document.querySelector(`#skov [data-s="${e.key==="0"?-1:+e.key-1}"]`);if(b)b.click()}
  else if(t.phase==="cmd"&&/^[0-3]$/.test(e.key)){const b=document.querySelector(`#skov [data-c="${e.key}"]`);if(b&&!b.disabled)b.click()}
  else if(t.phase==="cmd"&&e.key==="Enter"){const b=$("#cgo");if(b&&!b.disabled)b.click()}
  else if(t.phase==="wrong"&&e.key==="Enter"){e.preventDefault();const b=$("#bnx");if(b&&!b.disabled)b.click()}});
