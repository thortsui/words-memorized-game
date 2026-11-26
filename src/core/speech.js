// 朗讀系統：預設先用瀏覽器內建語音，失敗才改用 Google 翻譯語音（非官方端點）
import { $, esc, once, lsGet } from './util.js';
import { sayable, zhSay } from './grading.js';
import { bgmDuck } from './audio.js';

// sp：聲音設定（練習設定頁會改這些值）
export const sp={rate:+(lsGet("vc-rate","0.9")),eng:lsGet("vc-eng3","auto"),voiceName:lsGet("vc-voice",""),voice:null,onVoices:null};
// gFail／dFail：引擎被判定失敗，RETRY 毫秒內直接跳過；時間到了只「試探」一次，再失敗就立刻再跳過
let gFail=false,gHost=0,gBad=0,gFailAt=0,dBad=0,dFail=false,dFailAt=0,spkId=0,gProbe=false,dWarm=false,talking=false,gapUntil=0;
const RETRY=120000;
export const resetGoogleFail=()=>{gFail=false;gBad=0;gProbe=false;dFail=false;dBad=0};
const hasSys=()=>"speechSynthesis" in window&&typeof SpeechSynthesisUtterance!=="undefined";

function pickVoice(){try{const vs=speechSynthesis.getVoices().filter(v=>/^en[-_]US/i.test(v.lang));const rank=[/Google US English/i,/(Ava|Samantha|Zoe|Allison|Evan|Nathan).*(Premium|Enhanced)/i,/Natural/i,/Siri/i,/Samantha/i,/Ava/i,/Aria|Jenny/i];sp.voice=null;for(const r of rank){sp.voice=vs.find(v=>r.test(v.name));if(sp.voice)break}sp.voice=sp.voice||vs[0]||null}catch(e){}}
if("speechSynthesis" in window){pickVoice();speechSynthesis.onvoiceschanged=()=>{pickVoice();sp.onVoices&&sp.onVoices()}}
export function enVoices(){try{return speechSynthesis.getVoices().filter(v=>/^en([-_]|$)/i.test(v.lang))}catch(e){return[]}}
const zhVoice=()=>{try{const vs=speechSynthesis.getVoices();return vs.find(v=>/Google.*(國語|臺灣|台灣)/.test(v.name))||vs.find(v=>/zh[-_]TW/i.test(v.lang))||vs.find(v=>/zh[-_](HK|Hant)/i.test(v.lang))||vs.find(v=>/^zh/i.test(v.lang))||null}catch(e){return null}};

const au=new Audio();
// 超過 180 字元依標點切段
function chunks(t){const out=[];let s="";for(const p of t.split(/(?<=[.!?,;])\s+/)){if((s+" "+p).trim().length>180){if(s)out.push(s);s=p}else s=(s+" "+p).trim()}if(s)out.push(s);return out}

const KEEP=[]; // 保留 utterance 參考，避免被回收
// utterance 的事件處理器會抓住當時的按鈕（進而抓住整個戰鬥畫面的 DOM）：離開戰鬥時清掉
export const releaseSpeech=()=>{KEEP.length=0};
function deviceSpeak(text,done,fail,lang,my){if(!hasSys()){fail(text);return}
  const ss=speechSynthesis,alive=()=>my===spkId;
  const go=()=>{if(!alive())return;let u;try{u=new SpeechSynthesisUtterance(text)}catch(e){fail(text);return}KEEP.push(u);if(KEEP.length>12)KEEP.shift();
    u.lang=lang==="zh"?"zh-TW":"en-US";const v=lang==="zh"?zhVoice():(enVoices().find(x=>x.name===sp.voiceName)||sp.voice);if(v)u.voice=v;u.rate=sp.rate<.8?.75:1;
    let started=false,fin=false;const t0=Date.now();let iv=null;const end=ok=>{if(fin)return;fin=true;clearInterval(iv);if(!alive())return;if(ok){dBad=0;done()}else{dBad++;if(dBad>=2){dFail=true;dFailAt=Date.now()}fail(text)}};
    u.onstart=()=>{started=true;dWarm=true};u.onend=()=>end(true);u.onerror=()=>end(started);
    try{ss.speak(u);if(ss.paused)ss.resume()}catch(e){end(false);return}
    // 不依賴 onend（Chrome 常不觸發）：每 200 毫秒檢查 speaking
    iv=setInterval(()=>{if(!alive()){clearInterval(iv);return}if(ss.speaking){started=true;dWarm=true}
      if(started){if(!ss.speaking&&!ss.pending)end(true);else if(Date.now()-t0>20000)end(true)}
      else if(Date.now()-t0>(dWarm?3000:6000)){try{ss.cancel()}catch(e){}end(false)}},200)};
  if(ss.speaking||ss.pending){try{ss.cancel()}catch(e){}setTimeout(go,90)}else go()}

const TTS_HOSTS=["https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob","https://translate.googleapis.com/translate_tts?ie=UTF-8&client=gtx"];
const ttsUrl=(t,lang,hi)=>TTS_HOSTS[hi]+"&tl="+(lang==="zh"?"zh-TW":"en-US")+"&q="+encodeURIComponent(t);
function googleSpeak(text,done,fail,lang,my){const q=chunks(text);let k=0,hi=gHost,tries=0,stall=null,iv=null,lastT=-1,lastC=0;const alive=()=>my===spkId;
  try{if(hasSys()&&(speechSynthesis.speaking||speechSynthesis.pending))speechSynthesis.cancel()}catch(e){}
  const cleanup=()=>{clearTimeout(stall);clearInterval(iv);if(alive()){au.onended=au.onerror=au.onplaying=null}};
  // 兩個主機都試過還是不行（試探時只試一個）就判定失敗，之後的句子不再等
  const giveUp=()=>{cleanup();gBad++;gFail=true;gFailAt=Date.now();gProbe=false;fail(q.slice(k).join(" "))};
  const bad=()=>{if(!alive())return;cleanup();try{au.pause()}catch(e){}if(tries<1&&!gProbe){tries++;hi=1-hi;return start()}giveUp()};
  const start=()=>{if(!alive())return;au.src=ttsUrl(q[k],lang,hi);au.playbackRate=sp.rate<.8?.75:1;
    au.onplaying=()=>{if(!alive())return;clearTimeout(stall);gBad=0;gProbe=false;gHost=hi;lastT=-1;lastC=Date.now();clearInterval(iv);
      iv=setInterval(()=>{if(!alive()){clearInterval(iv);return}if(au.ended)return;if(au.currentTime!==lastT){lastT=au.currentTime;lastC=Date.now()}else if(Date.now()-lastC>4000)bad()},400)};
    au.onended=()=>{if(!alive())return;cleanup();k++;tries=0;if(k>=q.length)done();else start()};
    au.onerror=bad;clearTimeout(stall);stall=setTimeout(bad,2500);
    const p=au.play();if(p&&p.catch)p.catch(err=>{if(!alive())return;if(err&&err.name==="NotAllowedError"){cleanup();fail(q.slice(k).join(" "))}else if(err&&err.name!=="AbortError")bad()})};
  start()}

// 字幕條：一般頁面固定在頂端；戰鬥中放進戰場（.arenawrap）底緣，不擋上面那排按鈕與血量
export function caption(label,text){let c=$("#cap");if(!c){if(!text)return;c=document.createElement("div");c.id="cap";c.innerHTML='<b></b><span></span>';
    // 戰場裡的血量框要依字幕高度往上讓：高度用 ResizeObserver 取（不在這裡強制重排）
    if(typeof ResizeObserver!=="undefined")new ResizeObserver(()=>{const h=c.parentNode;if(h&&h!==document.body)h.style.setProperty("--caph",c.offsetHeight+"px")}).observe(c)}
  const host=document.querySelector(".arenawrap")||document.body;if(c.parentNode!==host)host.appendChild(c);
  clearTimeout(c._t);if(!text){c._t=setTimeout(()=>c.classList.remove("on"),700);return}c.querySelector("b").textContent=label;c.querySelector("span").textContent=text;c.classList.add("on");}

let readFin=null;
export function speak(text,btn,opt){opt=opt||{};if(readFin&&!opt.chain)readFin();const lang=opt.lang||"en";const shown=String(text);text=lang==="zh"?zhSay(text):sayable(text);if(!text){opt.done&&opt.done();return}const id=++spkId;
  caption(opt.label||(lang==="zh"?"中文":"英文"),shown);bgmDuck(true);
  talking=true;gapUntil=0;document.querySelectorAll(".spk.on").forEach(b=>b.classList.remove("on"));if(btn)btn.classList.add("on");let fired=false;const off=()=>{if(fired)return;fired=true;btn&&btn.classList.remove("on");if(id===spkId){caption();bgmDuck(false);talking=false;gapUntil=opt.done?Date.now()+450:0}if(opt.done&&id===spkId)setTimeout(opt.done,250)};
  try{au.pause()}catch(e){}
  // 被判定失敗的引擎跳過 2 分鐘；時間到了再試探一次（試探時失敗一次就再跳過，不必重新等兩輪）
  if(gFail&&Date.now()-gFailAt>RETRY){gFail=false;gBad=0;gProbe=true}
  if(dFail&&Date.now()-dFailAt>RETRY){dFail=false;dBad=1}
  const gOK=!gFail&&navigator.onLine!==false,dOK=!dFail&&hasSys(),eng=sp.eng;
  const order=(eng==="google"?["g","d"]:eng==="device"?["d"]:["d","g"]).filter(e=>e==="g"?gOK:dOK);let i=0;
  // 能用的引擎都被判定失敗：直接跳過朗讀、立刻解鎖，不讓每一句都空等
  if(!order.length){once("mute","現在沒辦法朗讀（裝置語音與 Google 語音都沒有反應），先跳過朗讀，稍後會自動再試");fired=true;talking=false;btn&&btn.classList.remove("on");caption();bgmDuck(false);opt.done&&opt.done();return}
  const run=t=>{if(id!==spkId)return;
    while(i<order.length&&(order[i]==="g"?gFail:dFail))i++; // 這一句進行中才被判定失敗的引擎也跳過
    if(i>=order.length){
      // 這一句所有引擎都沒聲音：裝置語音只要失敗過就一併判定失敗，下一句起直接跳過（不必再多等一句）
      if(order.includes("d")&&dBad>=1&&(gFail||navigator.onLine===false)){dFail=true;dFailAt=Date.now()}
      once("mute","沒有聲音？請確認音量，或到練習頁換一種聲音");off();return}
    const e=order[i++];(e==="g"?googleSpeak:deviceSpeak)(t,off,rest=>run(rest||t),lang,id)};run(text)}

// 作答後依序念英文、中文、例句；最長 25 秒
export function readAll(w,btn){return new Promise(res=>{let done=false;const fin=()=>{if(done)return;done=true;if(readFin===fin)readFin=null;res()};if(readFin)readFin();readFin=fin;setTimeout(fin,25000);
  speak(w.en,btn,{chain:1,label:"英文",done:()=>speak(w.zh,btn,{lang:"zh",chain:1,label:"中文",done:()=>w.ex?speak(w.ex,btn,{chain:1,label:"例句",done:fin}):fin()})})})}
// 朗讀期間鎖住按鈕
export function gate(btn,p,label){if(!btn)return;const t=btn.innerHTML;btn.disabled=true;btn.classList.add("reading");btn.innerHTML=label||"朗讀中…（英文→中文→例句）";p.then(()=>{if(!btn.isConnected)return;btn.disabled=false;btn.classList.remove("reading");btn.innerHTML=t;
  // 鎖住時瀏覽器會把焦點丟回 body；解鎖後還給按鈕，鍵盤才接得上
  const a=document.activeElement;if(!a||a===document.body)try{btn.focus({preventScroll:true})}catch(e){}})}
// 停止朗讀：字幕立刻收起來（不等平常句子之間的 0.7 秒緩衝）
// 目前是否在朗讀（連續朗讀的句子之間有 0.25 秒空檔，這段也算在朗讀中）
export const speechBusy=()=>talking||Date.now()<gapUntil;
// 等目前的朗讀唸完（最多 maxMs 毫秒）。戰鬥自動換題前用，避免單字唸到一半被下一題切掉
export function waitSpeech(maxMs=3000){const t0=Date.now();return new Promise(res=>{const chk=()=>{if(!speechBusy()||Date.now()-t0>=maxMs)return res();setTimeout(chk,100)};chk()})}
export function stopSpeech(){spkId++;talking=false;gapUntil=0;if(readFin)readFin();try{au.pause()}catch(e){}try{speechSynthesis.cancel()}catch(e){}caption();const c=$("#cap");if(c){clearTimeout(c._t);c.classList.remove("on")}document.querySelectorAll(".spk.on").forEach(b=>b.classList.remove("on"));bgmDuck(false)}

const SPK='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
export const spkBtn=(t,label)=>`<button class="spk" data-say="${esc(t)}" aria-label="${label||"朗讀"}">${SPK}</button>`;
document.addEventListener("click",e=>{const b=e.target.closest("[data-say]");if(b){e.stopPropagation();speak(b.dataset.say,b)}},true);
