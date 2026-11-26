// 戰鬥控制器：把規則引擎（monster.js／soul.js）、HUD（DOM）與戰鬥畫面（view3d.js）接在一起。
// 計時、作答、朗讀、錯題紀錄都在這裡；規則本身在引擎裡，畫面動畫在 view 裡。
import { $, app, esc, ask, SC, wait, lsGet, lsSet, KEY_HINT } from '../core/util.js';
import { setup, mark, pushHist, allWords, ctx, save } from '../core/store.js';
import { clozeAns, opts, normEn, checkEn, checkZhSmart, zhPrompt, clozePos } from '../core/grading.js';
import { speak, readAll, gate, spkBtn, stopSpeech, releaseSpeech } from '../core/speech.js';
import { sfx, bgmStart, bgmStop, bgmToggle, bgmOn } from '../core/audio.js';
import { MON, SKILLS, MAXEN, PLAYER_HP, STORY, SOUL_STORY, SOUL_BOSSES, SOUL } from './data.js';
import { createMonsterBattle, comboMult } from './monster.js';
import { createSoulBattle } from './soul.js';
import { mount } from './view3d.js';
import { wordRow } from '../pages/dicts.js';
import { toSetup, exLine, startQuiz } from '../pages/practice.js';

const RM=matchMedia("(prefers-reduced-motion: reduce)").matches;
let T=null; // 目前這場戰鬥：{E 引擎, view, soul, phase, …}
const alive=t=>t===T&&ctx.B===t;
// 題目出現後這段時間內的點擊不算作答（選項同時顯示成未啟用）。魂系的閃避題分秒必爭，維持原本的 350ms
const guardMs=t=>t.soul?350:500;
const setAns=v=>{const w=app.querySelector(".bwrap");if(w)w.classList.toggle("ans",!!v)}; // 已作答的回饋狀態（版面讓出高度）
function nextBtn(label){const nb=document.createElement("button");nb.className="pri nextbtn";nb.id="bnx";nb.textContent=label;$("#bq").appendChild(nb);return nb}
const say=(t,cls)=>{const el=$("#msg");if(!el)return;el.className="msgbox "+(cls||"");el.textContent=t};

export function startBattle(ws,soul){if(!ws.length)return;ctx.Q=null;stopSpeech();
  const t=T=ctx.B={soul:!!soul,mode:setup.mode,pool:ws,bank:allWords(),phase:"busy",readP:Promise.resolve(),raf:0,tmo:0,seq:0};
  // window.__soulTest：自動化測試用（例如 {ambushRng} 強制觸發突襲），一般使用不會有
  t.E=(soul?createSoulBattle:createMonsterBattle)({pool:ws,mode:setup.mode,...(soul&&window.__soulTest?window.__soulTest:{})});if(soul&&window.__soulTest&&window.__soulTest.expose)window.__soulE=t.E;
  document.body.classList.add("inbattle");document.body.classList.toggle("soulmode",!!soul);window.scrollTo(0,0);vvOn();guardOn();
  app.innerHTML=`<div class="bwrap ${soul?"soul":""}"><div class="row btop"><button class="sm ghost" id="run" style="padding-left:0">← 逃跑</button><button class="sm ghost" id="bgmb">${bgmOn()?"♪ 音樂開":"♪ 音樂關"}</button><span class="small" style="margin-left:auto" id="bstat"></span></div>
  <div class="arenawrap"><div class="arena" id="arena"></div>
   <div class="hpbox foe"><div class="row" style="gap:6px;flex-wrap:nowrap"><b id="fname"></b><span class="small" id="flv"></span></div><div class="hp"><span>HP</span><div><i id="fhp"></i></div></div><div class="small" style="text-align:right" id="fhpt"></div></div>
   <div class="hpbox me"><div class="row" style="gap:6px;flex-wrap:nowrap"><b>你</b><span class="small" id="combo"></span>${soul?'<span class="small pflask" id="pflask"></span>':""}<span class="small" id="diff" style="margin-left:auto"></span></div><div class="hp"><span>HP</span><div><i id="php"></i></div><b id="phpt"></b></div>
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
// 確認框開著的期間暫停計時與畫面（兩個模式都是），取消後接著跑
async function flee(t){if(asking||!alive(t))return;asking=true;
  const po=$("#pauseov");if(po)po.remove(); // 「已暫停」遮罩還在就先收掉（它會蓋住確認框）；暫停狀態由這裡接手
  if(!t.paused){t.paused=true;t.tm&&t.tm.pause();t.view.setPaused&&t.view.setPaused(true)}
  const ok=await ask("要逃跑嗎？已作答的題目會記進練習歷程，但這場戰鬥不能接續。");asking=false;if(!alive(t))return;
  if(!ok){t.paused=false;t.view.setPaused&&t.view.setPaused(false);t.tm&&t.tm.resume();return}
  saveProgress(t);endBattle();toSetup()}
function saveProgress(t){if(!t||t.saved)return;const r=t.E.result();if(!r.n)return;t.saved=true;
  pushHist({t:Date.now(),mode:t.mode,dict:setup.dict,n:r.n,right:r.right,wrong:r.wrong.map(w=>[w.dict||setup.dict,w.id]),game:t.soul?"soul":true,aborted:true})}
// 戰鬥中多推一筆 history：按上一頁會先跳出逃跑確認（不會直接離開網站）；重新整理或關分頁前由瀏覽器提示。
// 這一筆在離開戰鬥時收回（history.back），否則離開後第一次按上一頁會沒反應；popSkip＝自己觸發的 popstate，不當成使用者按上一頁。
let popSkip=0;
const hasMark=()=>{try{return!!(history.state&&history.state.battle)}catch(e){return false}};
window.addEventListener("popstate",()=>{if(popSkip>0){popSkip--;return}const t=T;
  if(!t||ctx.B!==t){if(hasMark()){popSkip++;try{history.back()}catch(e){popSkip--}}return} // 沒在戰鬥卻走到殘留的那一筆：直接再退一步
  if(!hasMark())try{history.pushState({battle:1},"")}catch(e){}flee(t)});
const onUnload=e=>{if(!T||ctx.B!==T)return;e.preventDefault();e.returnValue=""};
const onHide=()=>{if(T&&ctx.B===T)saveProgress(T)}; // 真的離開頁面時才寫入
function unbind(){window.removeEventListener("beforeunload",onUnload);window.removeEventListener("pagehide",onHide)}
function guardOn(){unbind();if(!hasMark())try{history.pushState({battle:1},"")}catch(e){}window.addEventListener("beforeunload",onUnload);window.addEventListener("pagehide",onHide)}
function guardOff(){unbind();if(hasMark()){popSkip++;try{history.back()}catch(e){popSkip--}}}

// 軟鍵盤彈出時 visualViewport 會變矮：把高度寫進 --vvh 讓 .bwrap 跟著縮，並加上 body.kbd 讓戰場讓出空間給題目與輸入框
// 鍵盤是否彈出：只在輸入框有焦點時，看可視高度比「沒在打字時的高度」縮了多少（不能用絕對高度判斷，橫式手機本來就只有 390px 高）
const vv=window.visualViewport;let vvBase=0,vvW=0;
const typing=()=>{const a=document.activeElement;return!!a&&(a.tagName==="INPUT"||a.tagName==="TEXTAREA")};
function vvSync(){if(!vv)return;const h=Math.round(vv.height),full=Math.round(vv.height*(vv.scale||1)),w=Math.round(vv.width*(vv.scale||1)),ty=typing();
  if(w!==vvW||!ty){vvW=w;vvBase=Math.max(full,ty?0:window.innerHeight)}else vvBase=Math.max(vvBase,full); // 轉向或沒在打字：重新記基準
  document.documentElement.style.setProperty("--vvh",h+"px");document.body.classList.toggle("kbd",ty&&vvBase-full>120);if(vv.offsetTop||window.scrollY)window.scrollTo(0,0)}
const vvLater=()=>setTimeout(()=>{if(T)vvSync()},0);
function vvOn(){if(!vv)return;vvBase=0;vvW=0;vv.addEventListener("resize",vvSync);vv.addEventListener("scroll",vvSync);document.addEventListener("focusin",vvLater);document.addEventListener("focusout",vvLater);vvSync()}
function vvOff(){if(!vv)return;vv.removeEventListener("resize",vvSync);vv.removeEventListener("scroll",vvSync);document.removeEventListener("focusin",vvLater);document.removeEventListener("focusout",vvLater);document.documentElement.style.removeProperty("--vvh");document.body.classList.remove("kbd")}

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
      {const pf=$("#pflask");if(pf)pf.textContent=s.flasks!=null?`藥壺 ${s.flasks}`:""}
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
  skill:e=>e.interrupted?null:[`${e.name}！`,e.perfect?"good":""],
  quickSlash:()=>["答得夠快，追加迅擊！","good"],
  foeAttack:e=>[`${e.timeout?"時間到！":"答錯了！"}${e.monster.name} 使出了 ${e.move}！`,"bad"],
  playerTurn:e=>[`你的回合！這回合 ${(e.windowMs/1000).toFixed(1)} 秒。答對自動連斬：剩 60% 以上時間答完＝完美 5 連斬，連續 3 題完美＝弱點擊破（看答案時時間暫停）`,"good"],
  weakBreak:()=>["弱點擊破！連續快答看穿破綻，追加連斬！","good"],
  assault:e=>[`看穿攻勢！${e.cut?`打斷 Boss 剩下的 ${e.cut} 擊，`:""}突擊——連續答對 ${e.total} 題，每題砍一刀！`,"good"],
  assaultEnd:e=>[e.hits>=e.total?"突擊完成！":`突擊中斷（命中 ${e.hits}/${e.total}）`,e.hits>=e.total?"good":"bad"],
  perkOffer:()=>["練等！選一個強化（只在這一局有效）","good"],
  perk:e=>[`獲得「${e.perk.name}」：${e.perk.d}`,"good"],
  windowEnd:()=>["攻擊時間結束！","bad"],
  enemyTurn:e=>[`${e.boss.name} 的回合，準備閃避 ${e.total} 次攻擊！`+(e.punish?"（趁你喝藥逼近，先來一記突進！）":"")+(e.plan&&e.plan.some(m=>m.kind==="combo")?"（有連擊，段與段之間不停）":""),"bad"],
  bossPhase:e=>[`${e.boss.name} 進入第 ${e.phase+1} 階段——${e.info.name}！`,"bad"],
  telegraph:e=>e.kind==="ambush"?[`突襲「${e.move}」！快答——答對閃開，夠快還能彈反！`,"bad danger"]
    :e.kind==="danger"?[`必殺「${e.move}」！只有答對才躲得開，擋不住！`,"bad danger"]
    :e.kind==="dash"?[`${e.move}！突進太快，不能彈反——快答對翻滾閃開！`,"bad dash"]
    :e.kind==="delayed"?[`${e.boss.name} 舉起武器停住了…（${e.move}）等選項解鎖再答，太急會慢半拍！`,"bad"]
    :e.kind==="combo"?[`${e.move}（第 ${e.seg+1} / ${e.segs} 段）${e.seg?"接著來了！":"！"}`,"bad"]
    :[`${e.boss.name} 準備使出 ${e.move}！快答對才能彈反！`,"bad"],
  parry:e=>[e.chain?"完美彈開！連擊還沒結束！":"完美彈反！立刻反擊！","good"],
  deflect:()=>null,
  dodge:()=>["翻滾閃避成功！","good"],
  guard:e=>e.blocked?[`答錯了！舉盾硬擋（耐力 −${SOUL.blockCost}）`,"bad"]:["耐力不足，勉強格擋！","bad"],
  graze:()=>["答得太慢，被擦傷！","bad"],
  foeHit:e=>[(e.timeout?"來不及了！":"答錯了，沒有躲開！")+(e.chain?"下一段來了！":""),"bad"],
  faint:e=>[`${(e.monster||e.boss).name} 倒下了！`,"good"],
  heal:e=>[`你恢復了 ${e.amount} HP！`+(e.source==="skill"?(e.left>0?`（這隻怪物還能再用 ${e.left} 次）`:"（這隻怪物已經用完了）"):""),"good"],
  flaskStart:()=>["拿出藥壺……答對這題才喝得下去！（攻擊時間照樣在走）","good"],
  drink:e=>[`喝下藥壺，回復 ${e.amount} HP！（剩 ${e.flasks} 壺）`,"good"],
  spill:e=>[`${e.timeout?"來不及喝，":"手一抖，"}藥灑了……（剩 ${e.flasks} 壺）`,"bad"],
  flaskPunish:()=>["喝藥拖太久，Boss 逼近了！它的回合會先突進。","bad"],
  flaskRefill:e=>[`撿回一壺藥（藥壺 ${e.flasks}）`,"good"],
  ambush:e=>e.from==="skill"?[`${e.boss.name} 突襲！招式被打斷${e.landed?`（只打中 ${e.landed}/${e.total} 段）`:""}——快答閃開！`,"bad danger"]
    :e.from==="flask"?[`${e.boss.name} 趁你喝藥突襲！藥還沒喝到（壺沒扣）——快答閃開！`,"bad danger"]:[`${e.boss.name} 突襲！這題作廢——快答閃開！`,"bad danger"],
  knockdown:e=>[e.from==="flask"?`藥灑了還露出破綻！${e.boss.name} 衝上來把你打倒（−${e.dmg}）`:`答錯露出破綻！${e.boss.name} 衝上來把你打倒（−${e.dmg}）`,"bad danger"],
  ambushEnd:e=>[`撐過突襲，繼續攻擊！（剩 ${(e.atkLeft/1000).toFixed(1)} 秒）`,"good"],
};
const SFX={gain:"shot",atb:"shot",chainStart:"shot",chainCharge:"shot",telegraph:"hurt",parry:"parry",dodge:"shot",faint:"faint",heal:"win"};
const LOCK_TIP="鎖住時亂點，每下慢 "+SOUL.flinchMs/1000+" 秒";
// 大招演出期間（起手到最後一段傷害）在 .bwrap 掛 bigfx：「你」的血量框先收起來，不擋畫面
const bigFx=v=>{const w=app.querySelector(".bwrap");if(w)w.classList.toggle("bigfx",!!v)};
async function run(t,events){try{await runEvents(t,events)}finally{if(alive(t))bigFx(false)}}
// 耐力被扣（翻滾、硬擋、格擋、擦傷）：耐力條閃紅＋冒出扣減數字
function staDrain(n){const el=app.querySelector(".enb.sta");if(!el||!n)return;el.classList.remove("drain");void el.offsetWidth;el.classList.add("drain");
  const f=document.createElement("em");f.className="stadrop";f.textContent="−"+n;el.appendChild(f);setTimeout(()=>f.remove(),900)}
async function runEvents(t,events){for(const e of events){if(!alive(t))return;
    if(!t.soul){if((e.type==="skill"&&e.big)||e.type==="chainFire")bigFx(true);else if(e.type!=="hit"&&e.type!=="chainStage"&&!(e.type==="skill"&&e.chainStage))bigFx(false)}const m=MSG[e.type]&&MSG[e.type](e);if(m)say(m[0],m[1]);if(SFX[e.type])sfx(SFX[e.type]);
    const s=e.s;
    if(e.type==="hit"){e.onImpact=()=>{sfx(e.big||e.dmg>=40?"crit":"hit");hud(s,"foe")}} // 命中瞬間才扣怪物血
    else if(e.type==="playerHit"){e.onImpact=()=>{sfx("hurt");hud(s,"me")}}
    else if(e.type==="drink"){e.onImpact=()=>{sfx("win");hud(s,"me")}} // 喝下去那一刻才補血
    else if(e.type==="heal"&&!t.soul){e.onImpact=()=>hud(s,"me")} // 打怪模式：治癒光落到身上那一刻才補血（音效照舊在事件開頭）
    else hud(s);
    if(t.soul&&(e.type==="guard"||e.type==="dodge"||e.type==="graze")){const prev=t.lastSta==null?s.stamina:t.lastSta;if(prev>s.stamina)staDrain(prev-s.stamina)}
    if(t.soul&&s)t.lastSta=s.stamina;
    if(e.type==="win")sfx("win");if(e.type==="lose")sfx("lose");
    // 倒下、登場、結局一律用正常速度播（不沿用出招時的慢動作）
    if(e.type==="faint"||e.type==="bossEnter"||e.type==="enter"||e.type==="win"||e.type==="lose")t.view.setTimeScale(1);
    if(t.soul){const bq=$("#bq");
      // 換 Boss 或換回合時，把上一題的題目卡與倒數標籤清掉
      if(bq&&(e.type==="faint"||e.type==="bossEnter"||e.type==="win"||e.type==="lose")){closeMenu();bq.innerHTML=""}
      else if(bq&&(e.type==="windowEnd"||e.type==="enemyTurn")){closeMenu();bq.innerHTML=soulHud();$("#sphase").textContent="敵人回合";$("#satb").innerHTML=atbHtml(s)}
      else if(bq&&e.type==="assault"){closeMenu();bq.innerHTML=soulHud();$("#sphase").textContent="突擊！";$("#satb").innerHTML=atbHtml(s)}
      else if(bq&&e.type==="perkOffer"){closeMenu();bq.innerHTML=""}
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
  t.qAt=performance.now();setAns(false);
  return `<div class="bqcard ${o.cls||""}" id="bqc"><div class="tline"><i id="tb"></i></div>${w._rep?'<div class="small" style="color:var(--bad);font-weight:700">剛剛答錯，再考一次</div>':""}${prompt}${body}<div id="bans"></div></div>`}
// 接上作答：cb(ok, 選項索引, 作答內容, 近義說明)。填空英翻中要等 Google 判定，期間暫停計時。
function hook(t,w,m,cb,onPause){const o=$("#bopts");if(o){o.classList.add("guard");setTimeout(()=>o.classList.remove("guard"),guardMs(t))}if(o)o.onclick=e=>{const b=e.target.closest("[data-o]");if(b&&t.phase==="q"){if(t.paused||performance.now()-t.qAt<guardMs(t))return;t.phase="busy";cb(t.opts[+b.dataset.o]===t.ans,+b.dataset.o,t.opts[+b.dataset.o])}};
  const f=$("#btf");if(f){const ti=$("#bti");ti.focus();f.onsubmit=e=>{e.preventDefault();if(t.phase!=="q"||t.paused)return;const v=ti.value;if(!v.trim())return;t.phase="busy";ti.readOnly=true;
    if(m==="en2zhT"){onPause&&onPause();say("判斷中…");checkZhSmart(v,w).then(r=>{if(alive(t))cb(r.ok,-1,v,r.loose)})}else cb(checkEn(v,w),-1,v)}}}
function markOpts(t,idx){app.querySelectorAll("#bopts button").forEach((b,i)=>{b.disabled=true;if(t.opts[i]===t.ans)b.classList.add("right");else if(i===idx)b.classList.add("wrong")});const bi=$("#bti");if(bi){bi.readOnly=true;bi.blur()} /* 作答後收起軟鍵盤，版面回到完整高度 */const sb=app.querySelector("#btf button");if(sb){sb.disabled=true;sb.hidden=true}}
function answerLine(w,ok,extra=""){const el=$("#bans");if(!el)return;el.innerHTML=`<div class="ansline ${ok?"ok":"no"}"><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span> ${spkBtn(w.en)}<span class="zhm">${esc(w.zh)}</span>${extra}</div>`;
  const al=el.firstChild;al.classList.add("fresh");setTimeout(()=>al.classList.remove("fresh"),400)}
// 倒數條。回傳 {elapsed(), stop()}；時間到呼叫 onEnd。
function timer(t,totalMs,startLeft,els,onEnd,onTick){let t0=performance.now(),stopped=false,at=0,pausedAt=0;
  const draw=left=>{const s=`scaleX(${Math.max(0,left/totalMs)})`;els.forEach(e=>{if(e)e.style.transform=s});onTick&&onTick(Math.max(0,left))};draw(startLeft);
  const el=()=>(pausedAt||performance.now())-t0;
  let lastTick=t0;
  const tick=()=>{if(stopped||pausedAt||!alive(t))return;const now=performance.now();if(now-lastTick>1000)t0+=now-lastTick;lastTick=now;const left=startLeft-el();draw(left);if(left<=0){stopped=true;at=startLeft;if(t.tm===me)t.tm=null;onEnd&&onEnd();return}t.raf=requestAnimationFrame(tick)};
  const me={elapsed:()=>stopped?at:Math.min(startLeft,el()),stop(){if(!stopped){at=Math.min(startLeft,el());stopped=true;cancelAnimationFrame(t.raf);if(t.tm===me)t.tm=null}return at},
    // 切到背景時暫停、回來按「繼續」才恢復（見 pauseBattle）
    pause(){if(!stopped&&!pausedAt){pausedAt=performance.now();cancelAnimationFrame(t.raf)}},resume(){if(!stopped&&pausedAt){t0+=performance.now()-pausedAt;pausedAt=0;lastTick=performance.now();t.raf=requestAnimationFrame(tick)}}};
  t.tm=me;t.raf=requestAnimationFrame(tick);return me}
// 頁面切到背景：暫停計時與畫面，回來後要點一下才繼續（否則回來時已經超時扣血）
function pauseBattle(t){if(t.paused||!alive(t))return;t.paused=true;t.tm&&t.tm.pause();t.view.setPaused&&t.view.setPaused(true);stopSpeech();
  const ov=document.createElement("button");ov.className="pauseov";ov.id="pauseov";ov.innerHTML='<span class="pbox"><b>已暫停</b><span>點一下繼續</span></span>';document.body.appendChild(ov);
  ov.onclick=()=>{ov.remove();if(!alive(t))return;t.paused=false;t.view.setPaused&&t.view.setPaused(false);t.tm&&t.tm.resume()}}
document.addEventListener("visibilitychange",()=>{if(document.hidden&&T&&ctx.B===T)pauseBattle(T)});
function closeMenu(){const s=$("#skov");if(s)s.remove();const w=app.querySelector(".bwrap");if(w)w.classList.remove("menuopen")}
const menuOpen=()=>{const w=app.querySelector(".bwrap");if(w)w.classList.add("menuopen")};

/* ---------- 打怪模式 ---------- */
function mReady(t){if(!alive(t)||!$("#bq"))return;t.phase="ready";closeMenu();setAns(false);const c=t.E.state.chain,S=t.E.state;
  $("#bq").innerHTML=c?`<button class="pri go chaingo" id="gonext">${esc(c.s.name)}・蓄力 第 ${c.stage+1} / ${c.s.chain.length} 題 ▶<span style="font-size:13px;font-weight:500">限時 ${c.s.times[c.stage]} 秒！${c.s.chain.length} 題全對才會發動${KEY_HINT}</span></button>`:`<button class="pri go" id="gonext">下一題 ▶<span style="font-size:13px;font-weight:500">按下後才開始計時${KEY_HINT}</span></button>`;
  $("#gonext").onclick=()=>mQuestion(t);gate($("#gonext"),t.readP,c?"朗讀中…（聽完就能繼續蓄力）":"朗讀中…（英文→中文→例句）");
  if(c){if(!/連招/.test($("#msg").textContent))say(`連招蓄力中：${c.s.name}（${c.stage}/${c.s.chain.length}）`,"good")}else if(!/出現|倒下|恢復|連招/.test($("#msg").textContent))say(`能量 ${S.en}/${MAXEN}。準備好就按「下一題」。`)}
function mQuestion(t){if(!alive(t)||t.phase!=="ready")return;const q=t.E.nextQuestion(),w=q.w,m=q.mode;t.phase="q";setAns(false);
  $("#bq").innerHTML=qCard(t,w,m,{cls:q.chain?"chainq":""});
  if(q.chain)say(`連招蓄力 ${q.chain.stage+1}/${q.chain.total}：${q.limitMs/1000} 秒內答對！`,"bad");else say(`${t.E.monster.name} 正盯著你…越快答對，能量越多！`);
  const fin=(ok,idx,given,loose,opt)=>mAnswer(t,w,ok,idx,given,tm.stop()/1000,loose,opt);
  // 一般題的計時條只影響能量，不會超時；連招題超時算答錯
  const tm=timer(t,q.limitMs,q.limitMs,[$("#tb")],q.timed?()=>{if(t.phase==="q"){t.phase="busy";say("時間到！","bad");fin(false,-1,"（超時）",null,{timeout:true})}}:null);
  hook(t,w,m,fin,()=>tm.stop());
  if(setup.auto&&(m==="en2zh"||m==="en2zhT"))speak(w.en,$("#bq .spk"))}
async function mAnswer(t,w,ok,idx,given,sec,loose,opt){setAns(true);mark(w,ok,given,t.mode);if(t.opts)markOpts(t,idx);else markOpts(t,-9);answerLine(w,ok);t.readP=readAll(w,$("#bans .spk"));
  const evs=t.E.answer(ok,sec,opt||{});const g=evs.find(e=>e.type==="gain");
  if(ok&&g&&!t.E.state.chain&&t.E.state.phase==="skill")say(`答對了！${loose?"（"+loose+"）":""}${sec.toFixed(1)} 秒，+${g.raw} 能量`+(t.E.state.en===MAXEN?"（已滿）":"")+"。看一下單字，再選招式。","good");
  await run(t,evs);if(!alive(t))return;const ph=t.E.state.phase,c=t.E.state.chain;
  if(ph==="end")return finish(t);
  if(ph==="skill")return mSkills(t);
  if(ph==="wrong"){t.phase="wrong";say("答錯了，記住正確答案。","bad");const nb=nextBtn("下一題 ▶");
    nb.onclick=()=>{if(t.phase!=="wrong")return;nb.disabled=true;nb.remove();t.E.ack();t.phase="ready";mQuestion(t)};gate(nb,t.readP,"朗讀中…");nb.focus({preventScroll:true});return}
  if(c)say(`連招蓄力 ${c.stage}/${c.s.chain.length}！（${sec.toFixed(1)} 秒）再答對 ${c.s.chain.length-c.stage} 題就能發動「${c.s.name}」`,"good");
  mReady(t)}
// 回血招式：一般招式下面的整列按鈕，鍵盤 H（數字鍵 1–9、0 維持原本的招式與不出招）
const HEAL_I=SKILLS.findIndex(s=>s.heal);
function healBtn(t){if(HEAL_I<0)return"";const s=SKILLS[HEAL_I],S=t.E.state,c=t.E.healCheck(HEAL_I);
  const note=c.reason==="full"?"HP 已滿":c.reason==="used"?"這隻怪物已用完":`⚡${s.cost}・回復 ${Math.min(s.heal,PLAYER_HP-S.hp)}・剩 ${c.left} 次`;
  return`<button class="healb" data-s="${HEAL_I}" ${c.ok?"":"disabled"}><b><span class="k">H</span><i class="hh">♥</i>${s.name}</b><span class="c">${note}</span></button>`}
function mSkills(t){if(!alive(t))return;t.phase="skill";const S=t.E.state,mult=comboMult(S.combo);closeMenu();
  const ov=document.createElement("div");ov.className="skov";ov.id="skov";
  ov.innerHTML=`<div class="row" style="margin-bottom:6px;flex-wrap:nowrap"><b>選擇招式</b><span class="small" style="margin-left:auto;color:#5ad1ff;white-space:nowrap"><span style="color:#9dffb8">HP ${S.hp}</span>・能量 ${S.en}/${MAXEN}${mult>1?`・×${mult.toFixed(1)}`:""}</span><button class="skip sm" data-s="-1" style="padding:2px 12px">不出招</button></div><div class="skills">${SKILLS.map((s,i)=>s.chain||s.heal?"":`<button data-s="${i}" ${S.en<s.cost?"disabled":""}><b><span class="k">${i+1}</span>${s.name}</b><span class="c">${s.cost?"⚡"+s.cost:"免費"}・約 ${s.hits.reduce((a,b)=>a+Math.round(b*mult),0)}</span></button>`).join("")}${healBtn(t)}<div class="chl"><b>連招（不耗能量、還會累積能量）</b> 連續答對指定題數後一次打出整套，限時較短</div>${SKILLS.map((s,i)=>s.chain?`<button class="chainb" data-s="${i}"><b><span class="k">${i+1}</span>${s.name}</b><span class="c">連對 ${s.chain.length} 題・約 ${(m=>s.stages.flat().reduce((a,b)=>a+Math.round(b*m),0))(comboMult(S.combo+s.chain.length))}</span></button>`:"").join("")}</div>`;
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
// 玩家回合：答對自動連斬
function sQ(t){if(!alive(t)||!$("#bq"))return;++t.seq;t.view.setTimeScale(1);closeMenu();stopSpeech();const q=t.E.nextAttackQuestion();
  if(!q)return run(t,t.E.startEnemyTurn()).then(()=>alive(t)&&sEnemy(t));
  const w=q.w,m=q.mode;t.phase="q";t.qkind="atk";
  $("#bq").innerHTML=soulHud()+qCard(t,w,m);$("#satb").innerHTML=atbHtml(t.E.snapshot());
  const tm=timer(t,q.windowMs,q.leftMs,[$("#stb"),$("#tb")],async()=>{if(t.phase!=="q")return;t.phase="busy";markOpts(t,-9);answerLine(w,false,exSpk(w));const seq=t.seq;if(!await settle(t,seq,t.E.attackTimeout()))return;sGo(t)},
    left=>{const el=$("#sphase");if(el)el.textContent=`攻擊時間 ${(left/1000).toFixed(1)} 秒`});
  hook(t,w,m,async(ok,idx,given,loose)=>{const ms=tm.stop();mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok,exSpk(w));readShort(w,$("#bans .spk"));
    const evs=t.E.answerAttack(ok,ms),s=t.E.snapshot(),sk=evs.find(e=>e.type==="skill");
    say(ok?`答對！${loose?"（"+loose+"）":""}${sk?(sk.perfect?"完美！":"")+sk.n+" 連斬":""}。剩餘攻擊時間 ${(s.atkLeft/1000).toFixed(1)} 秒`:`答錯了，多扣 ${SOUL.missPenaltyMs/1000} 秒！剩餘攻擊時間 ${(s.atkLeft/1000).toFixed(1)} 秒`,ok?"good":"bad");
    setAns(true);const seq=t.seq;
    const r=await settle(t,seq,evs,{flask:true});if(!r)return;if(t.E.state.phase!=="cmd")return sGo(t); // 被突襲、打倒 Boss（練等）、陣亡
    if(r==="flask"){await run(t,t.E.command(4));if(!alive(t))return;return sFlask(t)}
    soulNext(t,seq)},()=>tm.stop());
  if(setup.auto&&(m==="en2zh"||m==="en2zhT"))speak(w.en,$("#bq .spk"))}
// 指令列（時間減速）：放在題目卡下面的一排按鈕，不蓋住戰場
// 等一小段時間（暫停中不算）
async function holdFor(t,ms){let left=ms;while(left>0&&alive(t)){await wait(50);if(!t.paused)left-=50}}
async function soulNext(t,seq){await run(t,t.E.command(0));if(!alive(t)||t.seq!==seq)return;sGo(t)}
// 作答後一律停下來，按「下一題」才繼續（中間可以看答案、記單字；停著的時候攻擊時間不倒數）。
// 會清掉題目卡的事件（換回合、Boss 倒下、突擊、練等…）先等玩家按，再播；其他先播完再等。回傳 false＝流程已經換掉
const CLEARS=new Set(["windowEnd","enemyTurn","faint","bossEnter","win","lose","assault","perkOffer"]);
// flask：同一列多一顆「喝藥」按鈕（攻擊回合、藥壺可以喝時）。回傳 false／"next"／"flask"
function waitNext(t,seq,label="下一題 ▶",flask=null){return new Promise(res=>{if(!alive(t)||t.seq!==seq||!$("#bq"))return res(false);for(const id of ["#bnx","#bflask"]){const o=$(id);if(o)o.remove()}
  const nb=nextBtn(label);t.phase="wrong";let fb=null;
  const done=v=>{if(t.phase!=="wrong"||t.seq!==seq)return;t.phase="busy";nb.remove();if(fb)fb.remove();res(v)};
  nb.onclick=()=>done("next");
  if(flask){fb=document.createElement("button");fb.className="flaskbtn";fb.id="bflask";fb.innerHTML=`<span class="k">4</span>喝藥（剩 ${flask.count}）・回復 ${flask.heal}`;$("#bq").appendChild(fb);fb.onclick=()=>done("flask")}
  nb.focus({preventScroll:true})})}
async function settle(t,seq,evs,o={}){if(evs.some(e=>CLEARS.has(e.type))){if(!await waitNext(t,seq))return false;await run(t,evs);return alive(t)&&t.seq===seq?"next":false}
  await run(t,evs);if(!alive(t)||t.seq!==seq)return false;
  const f=o.flask&&t.E.state.phase==="cmd"?t.E.commands().find(c=>c.flask&&c.ready):null;
  const r=await waitNext(t,seq,"下一題 ▶",f);return alive(t)&&t.seq===seq?r:false}
// 依規則引擎目前的階段走到下一個畫面
function sGo(t){if(!alive(t))return;const ph=t.E.state.phase;if(ph==="end")return finish(t);if(ph==="perk")return sPerk(t);if(ph==="assault")return sAssault(t);if(ph==="pturn")return sQ(t);if(ph==="enemy")return sEnemy(t);if(ph==="cmd")return soulNext(t,t.seq)}
// 練等：打倒 Boss 後 3 選 1（只在這一局有效），選完才進下一隻
function sPerk(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;closeMenu();stopSpeech();t.view.setTimeScale(1);const offer=t.E.perkOffer;if(!offer)return sGo(t);
  t.phase="perk";const n=t.E.state.perks.length;
  $("#bq").innerHTML=`<div class="cmdrow perkrow" id="skov"><div class="cmdhead"><b>練等・選一個強化</b><span>只在這一局有效・已選 ${n} 個</span></div><div class="cmds perks">${offer.map((p,i)=>`<button data-p="${p.id}"><b><span class="k">${i+1}</span>${esc(p.name)}${p.lv?` Lv.${p.lv+1}`:""}</b><span class="c">${esc(p.d)}</span></button>`).join("")}</div></div>`;
  const box=$("#skov");box.onclick=async e=>{const b=e.target.closest("[data-p]");if(!b||t.phase!=="perk"||t.paused||t.seq!==seq)return;t.phase="busy";box.remove();await run(t,t.E.choosePerk(b.dataset.p));if(alive(t)&&t.seq===seq)sGo(t)}}
// 突擊：連續答 N 題（選擇題，每題 2–5 秒），答對砍一刀，答錯或超時結束，接著換玩家回合
function sAssault(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;closeMenu();stopSpeech();t.view.setTimeScale(1);const q=t.E.nextAssault();if(!q)return sGo(t);
  const w=q.w,m=q.mode;t.phase="q";t.qkind="assault";
  $("#bq").innerHTML=soulHud()+qCard(t,w,m,{cls:"chainq k-assault",plain:true});$("#satb").innerHTML=atbHtml(t.E.snapshot());
  say(`突擊 ${q.index+1}/${q.total}：答對就砍一刀！`,"good");
  let done=false,tm=null;
  const fin=async(ok,idx,given,opt)=>{if(done)return;done=true;const ms=tm?tm.stop():0;t.phase="busy";setAns(true);mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok,exSpk(w));readShort(w,$("#bans .spk"));
    if(!await settle(t,seq,t.E.answerAssault(ok,opt&&opt.timeout?q.limitMs+1:ms,opt||{})))return;sGo(t)};
  tm=timer(t,q.limitMs,q.limitMs,[$("#stb"),$("#tb")],()=>{if(t.phase==="q"){t.phase="busy";say("來不及了！","bad");fin(false,-9,"（超時）",{timeout:true})}},
    left=>{const el=$("#sphase");if(el)el.textContent=`突擊 ${q.index+1}/${q.total}・${(left/1000).toFixed(1)} 秒`});
  hook(t,w,m,(ok,idx,given)=>fin(ok,idx,given))}
function sCmd(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;closeMenu();const S=t.E.snapshot(),cmds=t.E.commands();
  // ATB 不夠出任何招：沒有選擇可做，直接出下一題（攻擊時間用完就直接輪到敵人）
  if(!cmds.some(c=>c.ready)){t.phase="busy";t.view.setTimeScale(1);return soulNext(t,seq)}
  t.phase="cmd";t.view.setTimeScale(.3);
  const ov=document.createElement("div");ov.className="cmdrow";ov.id="skov";
  const label=c=>c.flask?`${c.name} (${c.count})`:c.name;
  ov.innerHTML=`<div class="cmdhead"><b>指令</b><span>時間減速中・ATB ${S.atb}/3</span></div><div class="cmds">${cmds.map(c=>c.flask?`<button data-c="4" ${c.ready?"":"disabled"} class="flask"><b><span class="k">4</span>${label(c)}</b><span class="c">${c.ready?`回復 ${c.heal}・${SOUL.flaskCostMs/1000} 秒`:c.count?`HP<${Math.round(SOUL.flaskBelow*100)}% 可喝`:"喝光了"}</span></button>`:`<button data-c="${c.k}" ${c.ready?"":"disabled"} class="${c.big?"big":""}"><b><span class="k">${c.k}</span>${c.name}</b><span class="c">ATB ${c.bars}・約 ${c.approx}</span></button>`).join("")}<button class="skip" data-c="0" id="cgo"><b><span class="k">0</span>${S.atkLeft>0?"繼續答題":"結束攻擊"}</b><span class="c">${S.atkLeft>0?"保留 ATB":"輪到敵人"}</span></button></div>`;
  $("#bq").appendChild(ov);menuOpen();const shownAt=performance.now();let pausedMs=0,pz=0;
  ov.onclick=async e=>{const b=e.target.closest("[data-c]");if(!b||b.disabled||t.phase!=="cmd"||t.paused)return;const k=+b.dataset.c;t.phase="busy";closeMenu();
    // 猶豫時間（開指令列到按下）：拖越久越容易被 Boss 突襲（規則在 soul.js）
    const hes=Math.max(0,performance.now()-shownAt);
    if(k===4){t.view.setTimeScale(1);await run(t,t.E.command(4,{ms:hes}));if(!alive(t))return;return sFlask(t)}
    if(k)t.view.setTimeScale(k===3?.6:.85);else t.view.setTimeScale(1);
    await run(t,t.E.command(k,{ms:hes}));if(!alive(t))return;t.view.setTimeScale(1);const ph=t.E.state.phase;
    if(ph!=="cmd")return sGo(t);
    if(alive(t)&&t.seq===seq&&t.phase==="busy")sCmd(t)}}
// 喝藥：出一題（選擇題），攻擊時間照樣倒數；答對喝下、答錯灑掉。喝的時候 Boss 會壓近，也可能突襲。
function sFlask(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;closeMenu();stopSpeech();const q=t.E.flaskQuestion();if(!q)return sCmd(t);
  const w=q.w,m=q.mode;t.phase="q";t.qkind="flask";
  $("#bq").innerHTML=soulHud()+qCard(t,w,m,{cls:"flaskq",plain:true});$("#satb").innerHTML=atbHtml(t.E.snapshot());
  let done=false;
  const after=async evs=>{if(!await settle(t,seq,evs))return;if(t.E.state.phase!=="cmd")return sGo(t);soulNext(t,seq)};
  const tm=timer(t,q.windowMs,q.leftMs,[$("#stb"),$("#tb")],async()=>{if(t.phase!=="q"||done)return;done=true;t.phase="busy";markOpts(t,-9);answerLine(w,false,exSpk(w));await after(t.E.answerFlask(false,q.leftMs,{timeout:true}))},
    left=>{const el=$("#sphase");if(el)el.textContent=`喝藥中…攻擊時間 ${(left/1000).toFixed(1)} 秒`});
  hook(t,w,m,async(ok,idx,given)=>{if(done)return;done=true;const ms=tm.stop();mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok,exSpk(w));readShort(w,$("#bans .spk"));setAns(true);
    await after(t.E.answerFlask(ok,ms))})}
// 敵人回合：每次攻擊先蓄力，再出一題限時閃避題。
//   連擊：每段一題、段與段之間不停（中招也一樣，下一段接著來）；整招打完才看情況停下來等「繼續」。
//   延遲攻擊：題目先出現、選項鎖住 lockMs（Boss 舉著武器停住），解鎖後才開始倒數；鎖住時亂點每下作答時間 +flinchMs。
//   突進：時限短、沒有彈反（沒有金色區）；必殺：全畫面泛紅，答錯擋不住。
async function sEnemy(t){if(!alive(t)||!$("#bq"))return;const seq=++t.seq;closeMenu();stopSpeech();t.view.setTimeScale(1);t.phase="busy";const d=t.E.nextDodge();
  if(!d){await run(t,t.E.startPlayerTurn());if(alive(t)&&t.seq===seq)sQ(t);return}
  const label=()=>`敵人攻擊 ${d.index+1}/${d.total}`+(d.segs>1?`・連擊 ${d.seg+1}/${d.segs}`:"");
  $("#bq").innerHTML=soulHud();$("#sphase").textContent=label();$("#satb").innerHTML=atbHtml(t.E.snapshot());
  await run(t,d.events);if(!alive(t)||t.seq!==seq)return;const w=d.w,m=d.mode;
  $("#bq").innerHTML=soulHud()+qCard(t,w,m,{cls:"chainq k-"+d.kind,plain:true});$("#satb").innerHTML=atbHtml(t.E.snapshot());t.qkind="dodge";
  // 倒數條分區：右邊金色＝還在彈反時間內（突進、必殺沒有），左邊紅色＝太慢會被擦傷（倒數條由右往左縮）
  $(".stime").insertAdjacentHTML("beforeend",(d.perfectMs>0?`<em class="zg" style="left:${((1-d.perfectMs/d.limitMs)*100).toFixed(1)}%"></em>`:"")+`<em class="zr" style="width:${((1-SOUL.slowAt)*100).toFixed(1)}%"></em>`);
  if(d.kind==="ambush")say("突襲！時限很短——答對就能閃開，金色區內答對還能彈反！","bad danger");
  else if(d.kind==="danger")say(`必殺！只有答對才躲得開——答錯或超時會吃下全部傷害。`,"bad danger");
  else if(d.kind==="dash")say("突進！不能彈反，只能在紅色區之前答對翻滾閃開。","bad dash");
  else if(d.kind==="delayed")say(`Boss 停住了——等選項解鎖再答（${LOCK_TIP}）。`,"bad");
  else if(d.seg>0)say(`連擊第 ${d.seg+1} 段！時限更短，金色區內答對＝彈開。`,"bad");
  else say("剩 60% 以上時間答對（金色區）＝完美彈反；拖到紅色區才答對會被擦傷。","bad");
  let done=false,early=0,tm=null;
  const fin=async(ok,idx,given,opt)=>{if(done)return;done=true;const ms=tm?tm.stop():0;t.phase="busy";t.onEarly=null;setAns(true);mark(w,ok,given,t.mode);markOpts(t,idx);answerLine(w,ok,exSpk(w));readShort(w,$("#bans .spk"));
    const evs=t.E.answerDodge(ok,opt&&opt.timeout?d.limitMs+1:ms,{...(opt||{}),early});
    if(!await settle(t,seq,evs))return;
    if(t.E.state.phase==="end"){await wait(300);return alive(t)&&finish(t)}
    sGo(t)};
  const go=()=>{if(!alive(t)||t.seq!==seq||done)return;t.phase="q";t.qAt=performance.now()-guardMs(t);const o=$("#bopts");if(o)o.classList.remove("locked","guard");const lb=$("#lockb");if(lb)lb.remove();
    tm=timer(t,d.limitMs,d.limitMs,[$("#stb"),$("#tb")],()=>{if(t.phase==="q"){t.phase="busy";say("來不及了！","bad");fin(false,-9,"（超時）",{timeout:true})}},
      left=>{const el=$("#sphase");if(el)el.textContent=`${d.seg>0?`連擊 ${d.seg+1}/${d.segs}・`:""}閃避！${(left/1000).toFixed(1)} 秒`})};
  hook(t,w,m,(ok,idx,given)=>fin(ok,idx,given));
  if(d.lockMs>0){
    // 選項鎖住：倒數條上方多一條鎖定條（由滿到空），點選項不算作答，只會被記一次「太急」
    t.phase="lock";const o=$("#bopts");if(o)o.classList.add("locked");
    $("#bqc").insertAdjacentHTML("afterbegin",`<div class="lockb" id="lockb"><i></i><span>蓄力中…等它出手</span></div>`);
    t.onEarly=()=>{if(t.phase!=="lock")return;early++;const ob=$("#bopts");if(ob){ob.classList.remove("shake");void ob.offsetWidth;ob.classList.add("shake")}
      const lb=$("#lockb span");if(lb)lb.textContent=`太急了！作答時間 +${(Math.min(2,early)*SOUL.flinchMs/1000).toFixed(1)} 秒`};
    if(o)o.addEventListener("pointerdown",()=>{if(t.phase==="lock")t.onEarly()});
    tm=timer(t,d.lockMs,d.lockMs,[$("#lockb i")],()=>{tm=null;if(!alive(t)||t.seq!==seq||done)return;t.onEarly=null;t.view.play("delayRelease",{s:t.E.snapshot()});go()},
      left=>{const el=$("#sphase");if(el)el.textContent=`蓄力中… ${(left/1000).toFixed(1)}`})}
  else go()}

/* ---------- 結束畫面 ---------- */
function finish(t){const r=t.E.result(),soul=t.soul,pl=t.pool;t.saved=true;endBattle();stopSpeech();
  pushHist({t:Date.now(),mode:t.mode,dict:setup.dict,n:r.n,right:r.right,wrong:r.wrong.map(w=>[w.dict||setup.dict,w.id]),game:soul?"soul":true});
  const saved=save(); // pushHist 已經寫過一次；再確認一次有沒有成功，失敗就在結算頁提示
  const title=r.win?(soul?"噬語魔王被討伐了！":"史萊姆魔王被擊敗了！"):"你倒下了…";
  const sub=r.win?(soul?"詞語之火重新點燃，灰燼中的王國再次有了名字。":"詞語之力回到了艾爾文斯大陸，你成為了真正的魔劍士。"):(soul?"灰燼會記得你。複習單字，再次挑戰。":"別灰心，見習魔劍士，複習單字再出發吧！");
  app.innerHTML=`<div class="${soul?"soulres":"res"}"><div class="cut qcard">${SC}<div class="tab"><span>${r.win?"VICTORY":"GAME OVER"}</span></div><div class="body" style="text-align:center">
   <div class="big" style="font-size:clamp(34px,9vw,60px)">${title}</div><p class="small">${sub}</p>
   <p>打倒 ${r.kills} / ${r.total} 隻${soul?" Boss":"怪物"}・答對 ${r.right} / ${r.n} 題・最高連擊 ×${r.best}${r.fast<99?`・最快 ${r.fast.toFixed(1)} 秒`:""}${soul?`・彈反 ${r.parries} 次${r.weaks?`・弱點擊破 ${r.weaks} 次`:""}${r.assaults?`・突擊 ${r.assaults} 次`:""}`:""}</p>
   ${soul&&r.perks&&r.perks.length?`<p class="small">這一局的強化：${r.perks.map(p=>esc(p.name)).join("、")}</p>`:""}
   ${saved?"":'<p class="small" style="color:var(--bad);font-weight:700">這場戰鬥的紀錄沒有存進去（瀏覽器儲存空間不足），錯題與歷程不會保留。</p>'}
   <div class="row" style="justify-content:center"><button class="pri" id="again">再戰一次</button>${r.wrong.length?'<button id="rw">只練這次錯的</button>':""}<button id="chg">回設定</button></div></div></div>
   ${r.wrong.length?`<h2>這場答錯的（${r.wrong.length}）</h2><div class="cut">${SC}<div class="tab"><span>REVIEW</span></div><div class="body list">${r.wrong.map(w=>wordRow(w,true)).join("")}</div></div>`:""}</div>`;
  $("#again").onclick=()=>startBattle(pl,soul);$("#chg").onclick=toSetup;const rw=$("#rw");if(rw)rw.onclick=()=>startQuiz(r.wrong)}

/* ---------- 鍵盤：Enter 下一題、1–4 作答、1–9 選招、0 不出招；魂系 1–3 出招、0／Enter 繼續 ---------- */
document.addEventListener("keydown",e=>{const t=T;if(!t||!ctx.B||ctx.view!=="practice"||e.target.tagName==="INPUT"||asking||t.paused)return;
  if(t.storyNext){if(e.key==="Enter"||e.key===" "){e.preventDefault();t.storyNext()}else if(e.key==="Escape")t.storySkip();return}
  if(t.phase==="ready"&&(e.key==="Enter"||e.key===" ")){e.preventDefault();const g=$("#gonext");if(g&&!g.disabled)g.click()}
  else if(t.phase==="q"&&/^[1-4]$/.test(e.key)){const b=app.querySelector(`#bopts [data-o="${+e.key-1}"]`);if(b)b.click()}
  else if(t.phase==="lock"&&/^[1-4]$/.test(e.key)){t.onEarly&&t.onEarly()}
  else if(t.phase==="skill"&&/^[hH]$/.test(e.key)){const b=document.querySelector(`#skov .healb`);if(b&&!b.disabled)b.click()}
  else if(t.phase==="skill"&&/^[0-9]$/.test(e.key)){const b=document.querySelector(`#skov [data-s="${e.key==="0"?-1:+e.key-1}"]`);if(b)b.click()}
  else if(t.phase==="perk"&&/^[1-3]$/.test(e.key)){const b=document.querySelectorAll("#skov [data-p]")[+e.key-1];if(b)b.click()}
  else if(t.phase==="cmd"&&/^[0-4]$/.test(e.key)){const b=document.querySelector(`#skov [data-c="${e.key}"]`);if(b&&!b.disabled)b.click()}
  else if(t.phase==="cmd"&&e.key==="Enter"){const b=$("#cgo");if(b&&!b.disabled)b.click()}
  else if(t.phase==="wrong"&&e.key==="Enter"){e.preventDefault();const b=$("#bnx");if(b&&!b.disabled)b.click()}
  else if(t.phase==="wrong"&&e.key==="4"){const b=$("#bflask");if(b)b.click()}});
