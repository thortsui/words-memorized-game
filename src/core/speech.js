// 朗讀系統：預設先用瀏覽器內建語音，失敗才改用 Google 翻譯語音（非官方端點）
import { $, esc, once, lsGet } from './util.js';
import { sayable, zhSay } from './grading.js';
import { bgmDuck } from './audio.js';

// sp：聲音設定（練習設定頁會改這些值）
export const sp={rate:+(lsGet("vc-rate","0.9")),eng:lsGet("vc-eng3","auto"),voiceName:lsGet("vc-voice",""),voice:null,onVoices:null};
let gFail=false,gHost=0,gBad=0,gFailAt=0,dBad=0,dFail=false,dFailAt=0,spkId=0;
export const resetGoogleFail=()=>{gFail=false};
const hasSys=()=>"speechSynthesis" in window&&typeof SpeechSynthesisUtterance!=="undefined";

function pickVoice(){try{const vs=speechSynthesis.getVoices().filter(v=>/^en[-_]US/i.test(v.lang));const rank=[/Google US English/i,/(Ava|Samantha|Zoe|Allison|Evan|Nathan).*(Premium|Enhanced)/i,/Natural/i,/Siri/i,/Samantha/i,/Ava/i,/Aria|Jenny/i];sp.voice=null;for(const r of rank){sp.voice=vs.find(v=>r.test(v.name));if(sp.voice)break}sp.voice=sp.voice||vs[0]||null}catch(e){}}
if("speechSynthesis" in window){pickVoice();speechSynthesis.onvoiceschanged=()=>{pickVoice();sp.onVoices&&sp.onVoices()}}
export function enVoices(){try{return speechSynthesis.getVoices().filter(v=>/^en([-_]|$)/i.test(v.lang))}catch(e){return[]}}
const zhVoice=()=>{try{const vs=speechSynthesis.getVoices();return vs.find(v=>/Google.*(國語|臺灣|台灣)/.test(v.name))||vs.find(v=>/zh[-_]TW/i.test(v.lang))||vs.find(v=>/zh[-_](HK|Hant)/i.test(v.lang))||vs.find(v=>/^zh/i.test(v.lang))||null}catch(e){return null}};

const au=new Audio();
// 超過 180 字元依標點切段
function chunks(t){const out=[];let s="";for(const p of t.split(/(?<=[.!?,;])\s+/)){if((s+" "+p).trim().length>180){if(s)out.push(s);s=p}else s=(s+" "+p).trim()}if(s)out.push(s);return out}

const KEEP=[]; // 保留 utterance 參考，避免被回收
function deviceSpeak(text,done,fail,lang,my){if(!hasSys()){fail(text);return}
  const ss=speechSynthesis,alive=()=>my===spkId;
  const go=()=>{if(!alive())return;let u;try{u=new SpeechSynthesisUtterance(text)}catch(e){fail(text);return}KEEP.push(u);if(KEEP.length>12)KEEP.shift();
    u.lang=lang==="zh"?"zh-TW":"en-US";const v=lang==="zh"?zhVoice():(enVoices().find(x=>x.name===sp.voiceName)||sp.voice);if(v)u.voice=v;u.rate=sp.rate<.8?.75:1;
    let started=false,fin=false;const t0=Date.now();let iv=null;const end=ok=>{if(fin)return;fin=true;clearInterval(iv);if(!alive())return;if(ok){dBad=0;done()}else{dBad++;if(dBad>=2){dFail=true;dFailAt=Date.now()}fail(text)}};
    u.onstart=()=>{started=true};u.onend=()=>end(true);u.onerror=()=>end(started);
    try{ss.speak(u);if(ss.paused)ss.resume()}catch(e){end(false);return}
    // 不依賴 onend（Chrome 常不觸發）：每 200 毫秒檢查 speaking
    iv=setInterval(()=>{if(!alive()){clearInterval(iv);return}if(ss.speaking)started=true;
      if(started){if(!ss.speaking&&!ss.pending)end(true);else if(Date.now()-t0>20000)end(true)}
      else if(Date.now()-t0>2500){try{ss.cancel()}catch(e){}end(false)}},200)};
  if(ss.speaking||ss.pending){try{ss.cancel()}catch(e){}setTimeout(go,90)}else go()}

const TTS_HOSTS=["https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob","https://translate.googleapis.com/translate_tts?ie=UTF-8&client=gtx"];
const ttsUrl=(t,lang,hi)=>TTS_HOSTS[hi]+"&tl="+(lang==="zh"?"zh-TW":"en-US")+"&q="+encodeURIComponent(t);
function googleSpeak(text,done,fail,lang,my){const q=chunks(text);let k=0,hi=gHost,tries=0,stall=null,iv=null,lastT=-1,lastC=0;const alive=()=>my===spkId;
  try{if(hasSys()&&(speechSynthesis.speaking||speechSynthesis.pending))speechSynthesis.cancel()}catch(e){}
  const cleanup=()=>{clearTimeout(stall);clearInterval(iv);if(alive()){au.onended=au.onerror=au.onplaying=null}};
  const giveUp=()=>{cleanup();gBad++;if(gBad>=2){gFail=true;gFailAt=Date.now()}fail(q.slice(k).join(" "))};
  const bad=()=>{if(!alive())return;cleanup();try{au.pause()}catch(e){}if(tries<1){tries++;hi=1-hi;return start()}giveUp()};
  const start=()=>{if(!alive())return;au.src=ttsUrl(q[k],lang,hi);au.playbackRate=sp.rate<.8?.75:1;
    au.onplaying=()=>{if(!alive())return;clearTimeout(stall);gBad=0;gHost=hi;lastT=-1;lastC=Date.now();clearInterval(iv);
      iv=setInterval(()=>{if(!alive()){clearInterval(iv);return}if(au.ended)return;if(au.currentTime!==lastT){lastT=au.currentTime;lastC=Date.now()}else if(Date.now()-lastC>4000)bad()},400)};
    au.onended=()=>{if(!alive())return;cleanup();k++;tries=0;if(k>=q.length)done();else start()};
    au.onerror=bad;clearTimeout(stall);stall=setTimeout(bad,2500);
    const p=au.play();if(p&&p.catch)p.catch(err=>{if(!alive())return;if(err&&err.name==="NotAllowedError"){cleanup();fail(q.slice(k).join(" "))}else if(err&&err.name!=="AbortError")bad()})};
  start()}

// 頂端字幕條
export function caption(label,text){let c=$("#cap");if(!c){c=document.createElement("div");c.id="cap";c.innerHTML='<b></b><span></span>';document.body.appendChild(c)}
  clearTimeout(c._t);if(!text){c._t=setTimeout(()=>c.classList.remove("on"),700);return}c.querySelector("b").textContent=label;c.querySelector("span").textContent=text;c.classList.add("on")}

let readFin=null;
export function speak(text,btn,opt){opt=opt||{};if(readFin&&!opt.chain)readFin();const lang=opt.lang||"en";const shown=String(text);text=lang==="zh"?zhSay(text):sayable(text);if(!text){opt.done&&opt.done();return}const id=++spkId;
  caption(opt.label||(lang==="zh"?"中文":"英文"),shown);bgmDuck(true);
  document.querySelectorAll(".spk.on").forEach(b=>b.classList.remove("on"));if(btn)btn.classList.add("on");let fired=false;const off=()=>{if(fired)return;fired=true;btn&&btn.classList.remove("on");if(id===spkId){caption();bgmDuck(false)}if(opt.done&&id===spkId)setTimeout(opt.done,250)};
  try{au.pause()}catch(e){}
  // 某引擎連續失敗 2 次，跳過它 2 分鐘
  if(gFail&&Date.now()-gFailAt>120000){gFail=false;gBad=0}
  if(dFail&&Date.now()-dFailAt>120000){dFail=false;dBad=0}
  const gOK=!gFail&&navigator.onLine!==false,eng=sp.eng,order=eng==="google"?(gOK?["g","d"]:["d"]):eng==="device"?["d"]:!gOK?["d"]:dFail?["g","d"]:["d","g"];let i=0;
  const run=t=>{if(id!==spkId)return;if(i>=order.length){once("mute","沒有聲音？請確認音量，或到練習頁換一種聲音");off();return}const e=order[i++];(e==="g"?googleSpeak:deviceSpeak)(t,off,rest=>run(rest||t),lang,id)};run(text)}

// 作答後依序念英文、中文、例句；最長 25 秒
export function readAll(w,btn){return new Promise(res=>{let done=false;const fin=()=>{if(done)return;done=true;if(readFin===fin)readFin=null;res()};if(readFin)readFin();readFin=fin;setTimeout(fin,25000);
  speak(w.en,btn,{chain:1,label:"英文",done:()=>speak(w.zh,btn,{lang:"zh",chain:1,label:"中文",done:()=>w.ex?speak(w.ex,btn,{chain:1,label:"例句",done:fin}):fin()})})})}
// 朗讀期間鎖住按鈕
export function gate(btn,p,label){if(!btn)return;const t=btn.innerHTML;btn.disabled=true;btn.classList.add("reading");btn.innerHTML=label||"朗讀中…（英文→中文→例句）";p.then(()=>{if(!btn.isConnected)return;btn.disabled=false;btn.classList.remove("reading");btn.innerHTML=t})}
export function stopSpeech(){spkId++;if(readFin)readFin();try{au.pause();speechSynthesis.cancel()}catch(e){}caption();bgmDuck(false)}

const SPK='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
export const spkBtn=(t,label)=>`<button class="spk" data-say="${esc(t)}" aria-label="${label||"朗讀"}">${SPK}</button>`;
document.addEventListener("click",e=>{const b=e.target.closest("[data-say]");if(b){e.stopPropagation();speak(b.dataset.say,b)}},true);
