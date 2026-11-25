// 戰鬥控制器：把規則引擎（monster.js／soul.js）、HUD（DOM）與戰鬥畫面（view3d.js）接在一起。
// 計時、作答、朗讀、錯題紀錄都在這裡；規則本身在引擎裡，畫面動畫在 view 裡。
import { $, app, esc, ask, SC, wait, lsGet, lsSet } from '../core/util.js';
import { setup, mark, pushHist, allWords, ctx, save } from '../core/store.js';
import { clozeAns, opts, normEn, checkEn, checkZhSmart, zhPrompt, clozePos } from '../core/grading.js';
import { speak, readAll, gate, spkBtn, stopSpeech, releaseSpeech } from '../core/speech.js';
import { sfx, bgmStart, bgmStop, bgmToggle, bgmOn } from '../core/audio.js';
import { MON, SKILLS, MAXEN, STORY, SOUL_STORY, SOUL_BOSSES, SOUL } from './data.js';
import { createMonsterBattle, comboMult } from './monster.js';
import { createSoulBattle } from './soul.js';
import { mount } from './view3d.js';
import { wordRow } from '../pages/dicts.js';
import { toSetup, exLine, startQuiz } from '../pages/practice.js';

const RM=matchMedia("(prefers-reduced-motion: reduce)").matches;
let T=null; // 目前這場戰鬥：{E 引擎, view, soul, phase, …}
const alive=t=>t===T&&ctx.B===t;
const TAP_GUARD_MS=350; // 題目出現後這段時間內的點擊不算作答
const say=(t,cls)=>{const el=$("#msg");if(!el)return;el.className="msgbox "+(cls||"");el.textContent=t};

export function startBattle(ws,soul){if(!ws.length)return;ctx.Q=null;stopSpeech();
  const t=T=ctx.B={soul:!!soul,mode:setup.mode,pool:ws,bank:allWords(),phase:"busy",readP:Promise.resolve(),raf:0,tmo:0,seq:0};
  t.E=(soul?createSoulBattle:createMonsterBattle)({pool:ws,mode:setup.mode});
  document.body.classList.add("inbattle");document.body.classList.toggle("soulmode",!!soul);window.scrollTo(0,0);vvOn();guardOn();
  app.innerHTML=`<div class="bwrap ${soul?"soul":""}"><div class="row btop"><button class="sm ghost" id="run" style="padding-left:0">← 逃跑</button><button class="sm ghost" id="bgmb">${bgmOn()?"♪ 音樂開":"♪ 音樂關"}</button><span class="small" style="margin-left:auto" id="bstat"></span></div>
  <div class="arenawrap"><div class="arena" id="arena"></div>
   <div class="hpbox foe"><div class="row" style="gap:6px;flex-wrap:nowrap"><b id="fname"></b><span class="small" id="flv"></span></div><div class="hp"><span>HP</span><div><i id="fhp"></i></div></div><div class="small" style="text-align:right" id="fhpt"></div></div>
   <div class="hpbox me"><div class="row" style="gap:6px;flex-wrap:nowrap"><b>你</b><span class="small" id="combo"></span><span class="small" id="diff" style="margin-left:auto"></span></div><div class="hp"><span>HP</span><div><i id="php"></i></div><b id="phpt"></b></div>
    ${soul?'<div class="enb sta"><span>耐力</span><div><i id="pst"></i></div><b id="pstt"></b></div>':""}
    <div class="enb"><span id="enl">${soul?"ATB":"能量"}</span><div><i id="pen"></i></div><b id="pent"></b></div></div>
   <div id="ovl"></div></div>
  <div class="msgbox" id="msg"></div><div id="bq"></div></div>`;
  t.view=mount($("#arena"),{kind:soul?"soul":"monster",getState:()=>t.E.snapshot(),foes:soul?SOUL_BOSSES:MON,reducedMotion:RM});
  $(".arenawrap").addEventListener("click",()=>{if(t.skippable&&t.view.skip)t.view.skip()});
  $("#bgmb").onclick=bgmToggle;bgmStart(soul?"soul":"bright");
  $("#run").onclick=()=>flee(t);
  hud(t.E.snapshot());
  const key=soul?"vc-story-soul":"vc-story";
  (lsGet(key,"0")==="1"?Promise.resolve():story(t,soul?SOUL_STORY:STORY,key)).then(async()=>{if(!alive(t))return;await run(t,t.E.start());if(!alive(t))return;soul?sQ(t):mReady(t)})}

// 離開戰鬥（逃跑、換頁、結束）時清理
export function endBattle(){const t=T;if(!t)return;cancelAnimationFrame(t.raf);clearTimeout(t.tmo);try{t.view&&t.view.dispose()}catch(e){}T=null;ctx.B=null;document.body.classList.remove("inbattle","soulmode");vvOff();guardOff();const po=$("#pauseov");if(po)po.remove();bgmStop();releaseSpeech()}

// 逃跑（按鈕或瀏覽器上一頁）：先確認；中斷時把這場已作答的紀錄寫進練習歷程
let asking=false;
async function flee(t){if(asking||!alive(t))return;asking=true;const ok=await ask("要逃跑嗎？已作答的題目會記進練習歷程，但這場戰鬥不能接續。");asking=false;if(!ok||!alive(t))return;saveProgress(t);endBattle();toSetup()}
function saveProgress(t){if(!t||t.saved)return;const r=t.E.result();if(!r.n)return;t.saved=true;
  pushHist({t:Date.now(),mode:t.mode,dict:setup.dict,n:r.n,right:r.right,wrong:r.wrong.map(w=>[w.dict||setup.dict,w.id]),game:t.soul?"soul":true,aborted:true})}
// 戰鬥中多推一筆 history：按上一頁會先跳出逃跑確認（不會直接離開網站）；重新整理或關分頁前由瀏覽器提示
const onPop=()=>{const t=T;if(!t||ctx.B!==t)return;history.pushState({battle:1},"");flee(t)};
const onUnload=e=>{if(!T||ctx.B!==T)return;e.preventDefault();e.returnValue=""};
const onHide=()=>{if(T&&ctx.B===T)saveProgress(T)}; // 真的離開頁面時才寫入
function guardOn(){guardOff();try{history.pushState({battle:1},"")}catch(e){}window.addEventListener("popstate",onPop);window.addEventListener("beforeunload",onUnload);window.addEventListener("pagehide",onHide)}
function guardOff(){window.removeEventListener("popstate",onPop);window.removeEventListener("beforeunload",onUnload);window.removeEventListener("pagehide",onHide)}

// 軟鍵盤彈出時 visualViewport 會變矮：把高度寫進 --vvh 讓 .bwrap 跟著縮，並加上 body.kbd 讓戰場讓出空間給題目與輸入框
const vv=window.visualViewport;
function vvSync(){if(!vv)return;const h=Math.round(vv.height);document.documentElement.style.setProperty("--vvh",h+"px");document.body.classList.toggle("kbd",h<window.innerHeight-120||h<430);if(vv.offsetTop||window.scrollY)window.scrollTo(0,0)}
function vvOn(){if(!vv)return;vv.addEventListener("resize",vvSync);vv.addEventListener("scroll",vvSync);vvSync()}
function vvOff(){if(!vv)return;vv.removeEventListener("resize",vvSync);vv.removeEventListener("scroll",vvSync);document.documentElement.style.removeProperty("--vvh");document.body.classList.remove("kbd")}

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
    // 倒下、登場、結局一律用正常速度播（不沿用出招時的慢動作）
    if(e.type==="faint"||e.type==="bossEnter"||e.type==="enter"||e.type==="win"||e.type==="lose")t.view.setTimeScale(1);
    if(t.soul){const bq=$("#bq");
      // 換 Boss 或換回合時，把上一題的題目卡與倒數標籤清掉
      if(bq&&(e.type==="faint"||e.type==="bossEnter"||e.type==="win"||e.type==="lose")){closeMenu();bq.innerHTML=""}
      else if(bq&&(e.type==="windowEnd"||e.type==="enemyTurn")){closeMenu();bq.innerHTML=soulHud();$("#sphase").textContent="敵人回合";$("#satb").innerHTML=atbHtml(s)}
      if(e.type==="bossEnter"&&e.index>0){t.skippable=true;say(`${e.boss.name} 擋在你面前。（點戰場可跳過登場）`,"bad")}}
    await t.view.play(e.type,e);t.skippable=false;if(!alive(t))return;hud(s);if(t.soul){const sa=$("#satb");if(sa)sa.innerHTML=atbHtml(s)}}}

/* ---------- 題目卡（兩種模式共用） ---------- */
function qCard(t,w,m,o={}){let prompt="",body="";
  if(m==="en2zh"||m==="en2zhT")prompt=`<div class="row" style="gap:8px;flex-wrap:nowrap"><div class="bprompt en">${esc(w.en)}</div>${o.plain?"":spkBtn(w.en)}<span class="small">${esc(w.pos)}</span></div>${o.plain?"":exLine(w,false)}`;
  else if(m==="zh2en"||m==="zh2enT")prompt=`<div class="bprompt zh">${esc(zhPrompt(w))}</div>${m==="zh2enT"?`<div class="small">提示：${esc(w.en.trim()[0]||"")}… 共 ${normEn(w.en).replace(/ /g,"").length} 個字母</div>`:""}${o.plain?"":exLine(w,true)}`;
  else{const a=clozeAns(w),i=clozePos(w.ex,a);prompt=`<div class="cloze" style="font-size:17px;line-height:1.45">${esc(w.ex.slice(0,i))}<span class="blank">　?　</span>${esc(w.ex.slice(i+a.length))}</div><div class="small">提示：${esc(zhPrompt(w))}</div>`}
  if(m==="en2zh"||m==="zh2en"||m==="cloze"){const key=m==="en2zh"?"zh":m==="zh2en"?"en":"cloze";t.ans=key==="cloze"?clozeAns(w):w[key];t.opts=opts(w,key,t.bank);
    body=`<div class="bopts" id="bopts">${t.opts.map((x,i)=>`<button data-o="${i}" class="${key==="zh"?"":"en"}${x.length>(key==="zh"?13:22)?" long":""}"><span class="k">${i+1}</span><span class="ot">${esc(x)}</span></button>`).join("")}</div>`}
  else{t.opts=null;body=`<form id="btf" class="row" style="margin-top:8px"><input id="bti" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="send" ${m==="zh2enT"?'inputmode="text" lang="en"':""} placeholder="${m==="en2zhT"?"輸入中文意思":"輸入英文"}" style="flex:1 1 160px;width:auto"><button class="pri">送出</button></form>`}
  t.qAt=performance.now();
  return `<div class="bqcard ${o.cls||""}" id="bqc"><div class="tline"><i id="tb"></i></div>${w._rep?'<div class="small" style="color:var(--bad);font-weight:700">剛剛答錯，再考一次</div>':""}${prompt}${body}<div id="bans"></div></div>`}
// 接上作答：cb(ok, 選項索引, 作答內容, 近義說明)。填空英翻中要等 Google 判定，期間暫停計時。
function hook(t,w,m,cb,onPause){const o=$("#bopts");if(o)o.onclick=e=>{const b=e.target.closest("[data-o]");if(b&&t.phase==="q"){if(t.paused||performance.now()-t.qAt<TAP_GUARD_MS)return;t.phase="busy";cb(t.opts[+b.dataset.o]===t.ans,+b.dataset.o,t.opts[+b.dataset.o])}};
  const f=$("#btf");if(f){const ti=$("#bti");ti.focus();f.onsubmit=e=>{e.preventDefault();if(t.phase!=="q"||t.paused)return;const v=ti.value;if(!v.trim())return;t.phase="busy";ti.readOnly=true;
    if(m==="en2zhT"){onPause&&onPause();say("判斷中…");checkZhSmart(v,w).then(r=>{if(alive(t))cb(r.ok,-1,v,r.loose)})}else cb(checkEn(v,w),-1,v)}}}
function markOpts(t,idx){app.querySelectorAll("#bopts button").forEach((b,i)=>{b.disabled=true;if(t.opts[i]===t.ans)b.classList.add("right");else if(i===idx)b.classList.add("wrong")});const bi=$("#bti");if(bi)bi.readOnly=true;const sb=app.querySelector("#btf button");if(sb){sb.disabled=true;sb.hidden=true}}
function answerLine(w,ok,extra=""){const el=$("#bans");if(!el)return;el.innerHTML=`<div class="ansline ${ok?"ok":"no"}"><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span> ${spkBtn(w.en)}<span class="zhm">${esc(w.zh)}</span>${extra}</div>`}
// 倒數條。回傳 {elapsed(), stop()}；時間到呼叫 onEnd。
function timer(t,totalMs,startLeft,els,onEnd,onTick){let t0=performance.now(),stopped=false,at=0,pausedAt=0;
  const draw=left=>{const s=`scaleX(${Math.max(0,left/totalMs)})`;els.forEach(e=>{if(e)e.style.transform=s});onTick&&onTick(Math.max(0,left))};draw(startLeft);
  const el=()=>(pausedAt||performance.now())-t0;
  const tick=()=>{if(stopped||pausedAt||!alive(t))return;const left=startLeft-el();draw(left);if(left<=0){stopped=true;at=startLeft;if(t.tm===me)t.tm=null;onEnd&&onEnd();return}t.raf=requestAnimationFrame(tick)};
  const me={elapsed:()=>stopped?at:Math.min(startLeft,el()),stop(){if(!stopped){at=Math.min(startLeft,el());stopped=true;cancelAnimationFrame(t.raf);if(t.tm===me)t.tm=null}return at},
    // 切到背景時暫停、回來按「繼續」才恢復（見 pauseBattle）
    pause(){if(!stopped&&!pausedAt){pausedAt=performance.now();cancelAnimationFrame(t.raf)}},resume(){if(!stopped&&pausedAt){t0+=performance.now()-pausedAt;pausedAt=0;t.raf=requestAnimationFrame(tick)}}};
  t.tm=me;t.raf=requestAnimationFrame(tick);return me}
// 頁面切到背景：暫停計時與畫面，回來後要點一下才繼續（否則回來時已經超時扣血）
function pauseBattle(t){if(t.paused||!alive(t))return;t.paused=true;t.tm&&t.tm.pause();t.view.setPaused&&t.view.setPaused(true);stopSpeech();
  const ov=document.createElement("button");ov.className="pauseov";ov.id="pauseov";ov.innerHTML="<b>已暫停</b><span>點一下繼續</span>";document.body.appendChild(ov);
  ov.onclick=()=>{ov.remove();if(!alive(t))return;t.paused=false;t.view.setPaused&&t.view.setPaused(false);t.tm&&t.tm.resume()}}
document.addEventListener("visibilitychange",()=>{if(document.hidden&&T&&ctx.B===T)pauseBattle(T)});
function closeMenu(){const s=$("#skov");if(s)s.remove();const w=app.querySelector(".bwrap");if(w)w.classList.remove("menuopen")}
const menuOpen=()=>{const w=app.querySelector(".bwrap");if(w)w.classList.add("menuopen")};

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
    nb.onclick=()=>{if(t.phase!=="wrong")return;nb.disabled=true;nb.remove();t.E.ack();t.phase="ready";mQuestion(t)};gate(nb,t.readP,"朗讀中…");nb.focus({preventScroll:true});return}
  if(c)say(`連招蓄力 ${c.stage}/${c.s.chain.length}！（${sec.toFixed(1)} 秒）再答對 ${c.s.chain.length-c.stage} 題就能發動「${c.s.name}」`,"good");
  mReady(t)}
function mSkills(t){if(!alive(t))return;t.phase="skill";const S=t.E.state,mult=comboMult(S.combo);closeMenu();
  const ov=document.createElement("div");ov.className="skov";ov.id="skov";
  ov.innerHTML=`<div class="row" style="margin-bottom:6px;flex-wrap:nowrap"><b>選擇招式</b><span class="small" style="margin-left:auto;color:#5ad1ff">能量 ${S.en}/${MAXEN}${mult>1?`・×${mult.toFixed(1)}`:""}</span><button class="skip sm" data-s="-1" style="padding:2px 12px">不出招</button></div><div class="skills">${SKILLS.map((s,i)=>s.chain?"":`<button data-s="${i}" ${S.en<s.cost?"disabled":""}><b><span class="k">${i+1}</span>${s.name}</b><span class="c">${s.cost?"⚡"+s.cost:"免費"}・約 ${s.hits.reduce((a,b)=>a+Math.round(b*mult),0)}</span></button>`).join("")}<div class="chl"><b>連招（不耗能量、還會累積能量）</b> 連續答對指定題數後一次打出整套，限時較短</div>${SKILLS.map((s,i)=>s.chain?`<button class="chainb" data-s="${i}"><b><span class="k">${i+1}</span>${s.name}</b><span class="c">連對 ${s.chain.length} 題・約 ${(m=>s.stages.flat().reduce((a,b)=>a+Math.round(b*m),0))(comboMult(S.combo+s.chain.length))}</span></button>`:"").join("")}</div>`;
  $("#ovl").appendChild(ov);menuOpen();
  ov.onclick=async e=>{const b=e.target.closest("[data-s]");if(!b||b.disabled||t.phase!=="skill")return;const i=+b.dataset.s;closeMenu();t.phase="busy";
    if(i<0)say(`保留能量 ${S.en}/${MAXEN}。`);
    await run(t,t.E.useSkill(i));if(!alive(t))return;if(t.E.state.phase==="end")return finish(t);mReady(t)}}

/* ---------- 魂系模式 ---------- */
const atbHtml=s=>"ATB "+[0,1,2].map(i=>`<b class="${i<s.atb?"on":""}"></b>`).join("");
const soulHud=()=>`<div class="shud"><span id="sphase"></span><div class="stime"><i id="stb"></i></div><span id="satb" class="satb"></span></div>`;
// 魂系作答後只唸英文＋中文（例句改成答案列上可點的喇叭），而且不鎖按鈕：按「繼續」就中斷朗讀
const readShort=(w,btn)=>{speak(w.en,btn,{label:"英文",done:()=>speak(w.zh,btn,{lang:"zh",chain:1,label:"中文"})})};
const exSpk=w=>w.ex?`<span class="exsay">${spkBtn(w.ex,"朗讀例句")}<span class="small">例句</span></span>`:"";
// 玩家回合：出題累積 ATB
function sQ(t){if(!alive(t)||!$("#bq"))return;++t.seq;t.view.setTimeScale(1);closeMenu();stopSpeech();const q=t.E.nextAttackQuestion();
  if(!q)return run(t,t.E.startEnemyTurn()).then(()=>alive(t)&&sEnemy(t));
  const w=q.w,m=q.mode;t.phase="q";t.qkind="atk";
  $("#bq").innerHTML=soulHud()+qCard(t,w,m);$("#satb").innerHTML=atbHtml(t.E.snapshot());
  const tm=timer(t,q.windowMs,q.leftMs,[$("#stb"),$("#tb")],async()=>{if(t.phase!=="q")return;t.phase="busy";markOpts(t,-9);await run(t,t.E.attackTimeout());if(alive(t))sEnemy(t)},
    left=>{const el=$("#sphase");if(el)el.textContent=`攻擊時間 ${(left/1000).toFixed(1)} 秒`});
  hook(t,w,m,async(ok,idx,given,loose)=>{const ms=tm.stop();mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok,exSpk(w));readShort(w,$("#bans .spk"));
    const evs=t.E.answerAttack(ok,ms),s=t.E.snapshot();$("#satb").innerHTML=atbHtml(s);
    say(ok?`答對！${loose?"（"+loose+"）":""}ATB ${s.atb}/3。剩餘攻擊時間 ${(s.atkLeft/1000).toFixed(1)} 秒`:`答錯了，多扣 ${SOUL.missPenaltyMs/1000} 秒！剩餘攻擊時間 ${(s.atkLeft/1000).toFixed(1)} 秒`,ok?"good":"bad");
    await run(t,evs);if(!alive(t))return;const ph=t.E.state.phase;if(ph==="end")return finish(t);if(ph==="pturn")return sQ(t);sCmd(t)},()=>tm.stop());
  if(setup.auto&&(m==="en2zh"||m==="en2zhT"))speak(w.en,$("#bq .spk"))}
// 指令列（時間減速）：放在題目卡下面的一排按鈕，不蓋住戰場
function sCmd(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;t.phase="cmd";t.view.setTimeScale(.3);closeMenu();const S=t.E.snapshot(),cmds=t.E.commands();
  const ov=document.createElement("div");ov.className="cmdrow";ov.id="skov";
  ov.innerHTML=`<div class="cmdhead"><b>指令</b><span>時間減速中・ATB ${S.atb}/3</span></div><div class="cmds">${cmds.map(c=>`<button data-c="${c.k}" ${c.ready?"":"disabled"} class="${c.big?"big":""}"><b><span class="k">${c.k}</span>${c.name}</b><span class="c">ATB ${c.bars}・約 ${c.approx}</span></button>`).join("")}<button class="skip" data-c="0" id="cgo"><b><span class="k">0</span>${S.atkLeft>0?"繼續答題":"結束攻擊"}</b><span class="c">${S.atkLeft>0?"保留 ATB":"輪到敵人"}</span></button></div>`;
  $("#bq").appendChild(ov);menuOpen();
  ov.onclick=async e=>{const b=e.target.closest("[data-c]");if(!b||b.disabled||t.phase!=="cmd"||t.paused)return;const k=+b.dataset.c;t.phase="busy";closeMenu();
    if(k)t.view.setTimeScale(k===3?.6:.85);else t.view.setTimeScale(1);
    await run(t,t.E.command(k));if(!alive(t))return;t.view.setTimeScale(1);const ph=t.E.state.phase;
    if(ph==="end")return finish(t);if(ph==="pturn")return sQ(t);if(ph==="enemy")return sEnemy(t);
    if(alive(t)&&t.seq===seq&&t.phase==="busy")sCmd(t)}}
// 敵人回合：每次攻擊先蓄力，再出一題限時閃避題
async function sEnemy(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;closeMenu();stopSpeech();t.view.setTimeScale(1);t.phase="busy";const d=t.E.nextDodge();
  if(!d){await run(t,t.E.startPlayerTurn());if(alive(t)&&t.seq===seq)sQ(t);return}
  $("#bq").innerHTML=soulHud();$("#sphase").textContent=`敵人攻擊 ${d.index+1}/${d.total}`;$("#satb").innerHTML=atbHtml(t.E.snapshot());
  await run(t,d.events);if(!alive(t)||t.seq!==seq)return;const w=d.w,m=d.mode;
  $("#bq").innerHTML=soulHud()+qCard(t,w,m,{cls:"chainq",plain:true});$("#satb").innerHTML=atbHtml(t.E.snapshot());t.phase="q";t.qkind="dodge";
  // 倒數條分區：右邊金色＝還在彈反時間內，左邊紅色＝太慢會被擦傷（倒數條由右往左縮）
  $(".stime").insertAdjacentHTML("beforeend",`<em class="zg" style="left:${((1-d.perfectMs/d.limitMs)*100).toFixed(1)}%"></em><em class="zr" style="width:${((1-SOUL.slowAt)*100).toFixed(1)}%"></em>`);
  say("金色區內答對＝彈反（地上金圈消失前）；拖到紅色區才答對會被擦傷。","bad");
  let done=false;
  const fin=async(ok,idx,given,opt)=>{if(done)return;done=true;const ms=tm.stop();t.phase="busy";mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok,exSpk(w));readShort(w,$("#bans .spk"));
    await run(t,t.E.answerDodge(ok,opt&&opt.timeout?d.limitMs+1:ms,opt||{}));if(!alive(t)||t.seq!==seq)return;const ph=t.E.state.phase;
    if(ph==="end"){await wait(400);return alive(t)&&finish(t)}
    if(!$("#bqc"))return ph==="pturn"?sQ(t):sEnemy(t); // 題目卡已經被清掉（例如反擊打倒了 Boss）：直接往下走
    const nb=document.createElement("button");nb.className="pri nextbtn";nb.id="bnx";nb.textContent="繼續 ▶";$("#bqc").appendChild(nb);t.phase="wrong";
    {const el=$("#msg"),more=t.E.state.enemy&&t.E.state.enemy.i<t.E.state.enemy.total;if(el)el.textContent=el.textContent.replace(/（按「繼續」.*$/,"")+(more?"（按「繼續」迎接下一擊）":"（按「繼續」換你進攻）")}
    // 只能按一次：按下立刻失效並移除（連點兩下會讓下一回合開始兩次）
    nb.onclick=()=>{if(t.phase!=="wrong"||t.seq!==seq)return;t.phase="busy";nb.disabled=true;nb.remove();ph==="pturn"?sQ(t):sEnemy(t)}};
  const tm=timer(t,d.limitMs,d.limitMs,[$("#stb"),$("#tb")],()=>{if(t.phase==="q"){t.phase="busy";say("來不及了！","bad");fin(false,-9,"（超時）",{timeout:true})}},
    left=>{const el=$("#sphase");if(el)el.textContent=`閃避！${(left/1000).toFixed(1)} 秒`});
  hook(t,w,m,(ok,idx,given)=>fin(ok,idx,given))}

/* ---------- 結束畫面 ---------- */
function finish(t){const r=t.E.result(),soul=t.soul,pl=t.pool;t.saved=true;endBattle();stopSpeech();
  pushHist({t:Date.now(),mode:t.mode,dict:setup.dict,n:r.n,right:r.right,wrong:r.wrong.map(w=>[w.dict||setup.dict,w.id]),game:soul?"soul":true});
  const saved=save(); // pushHist 已經寫過一次；再確認一次有沒有成功，失敗就在結算頁提示
  const title=r.win?(soul?"噬語魔王被討伐了！":"史萊姆魔王被擊敗了！"):"你倒下了…";
  const sub=r.win?(soul?"詞語之火重新點燃，灰燼中的王國再次有了名字。":"詞語之力回到了艾爾文斯大陸，你成為了真正的魔劍士。"):(soul?"灰燼會記得你。複習單字，再次挑戰。":"別灰心，見習魔劍士，複習單字再出發吧！");
  app.innerHTML=`<div class="${soul?"soulres":"res"}"><div class="cut qcard">${SC}<div class="tab"><span>${r.win?"VICTORY":"GAME OVER"}</span></div><div class="body" style="text-align:center">
   <div class="big" style="font-size:clamp(34px,9vw,60px)">${title}</div><p class="small">${sub}</p>
   <p>打倒 ${r.kills} / ${r.total} 隻${soul?" Boss":"怪物"}・答對 ${r.right} / ${r.n} 題・最高連擊 ×${r.best}${r.fast<99?`・最快 ${r.fast.toFixed(1)} 秒`:""}${soul?`・彈反 ${r.parries} 次`:""}</p>
   ${saved?"":'<p class="small" style="color:var(--bad);font-weight:700">這場戰鬥的紀錄沒有存進去（瀏覽器儲存空間不足），錯題與歷程不會保留。</p>'}
   <div class="row" style="justify-content:center"><button class="pri" id="again">再戰一次</button>${r.wrong.length?'<button id="rw">只練這次錯的</button>':""}<button id="chg">回設定</button></div></div></div>
   ${r.wrong.length?`<h2>這場答錯的（${r.wrong.length}）</h2><div class="cut">${SC}<div class="tab"><span>REVIEW</span></div><div class="body list">${r.wrong.map(w=>wordRow(w,true)).join("")}</div></div>`:""}</div>`;
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
