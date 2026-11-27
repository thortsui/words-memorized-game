// 音效與配樂
// 音效：優先用真實取樣（public/sfx/*.mp3，CC0／CC-BY，來源見 public/sfx/CREDITS.md）；
//       取樣還沒載入或載入失敗時，退回下面 synth() 的 Web Audio 合成音（舊版聲音）。
//       Artifact 版（claude.ai）若抓不到 .mp3，會改抓同名的 .mp3.b64.txt 再解回二進位（比照模型的做法）。
// 配樂：全部合成，沒有音檔（魂系偶爾的遠鐘會借用 bell.mp3，沒有就用合成鐘）。
//
// sfx(name, {v, low, boss, rate}) 名字清單：
//   舊名字（全部保留，現在改用取樣）
//     shot   介面小提示（獲得、ATB、連段開始、閃避）→ tick
//     hit    砍中（肉＋輕金屬）            crit  重擊（重金屬＋肉）
//     hurt   主角受擊（悶擊＋甲片）        parry 彈反「鏘」
//     faint  敵人失衡／暈眩                win   勝利／回血（清亮鈴）    lose  敗北（遠鐘＋悶響）
//     step   Boss 踏步（= stomp）          swoosh 揮擊破風（o.low＝Boss 的重揮 swingH，否則 swingL）
//     heavy  重擊落地（= slam）            roar  咆哮（帶 o.boss 或先 setSfxBoss(id) 就用該 Boss 的咆哮）
//   新名字
//     clash        劍砍甲、兵器相交（4 種）      clashBig   重金屬撞擊、Boss 兵器相交（2 種）
//     swingL       輕揮破風（5 種）              swingH     重揮破風（3 種）
//     flesh        砍中肉（3 種）                stone      砍中石（石像鬼、石巨人，2 種）
//     block        格擋盾響（2 種）              roll       翻滾布料＋甲片（2 種）
//     footstep     主角腳步（4 種）              stomp      Boss 重踏（2 種）
//     slam         重砸地／爆裂（2 種）
//     roar_sentinel 鏽鐵巨人低沉咆哮             roar_gargoyle 石像鬼尖嘯
//     roar_priest   冰霜祭司鬼魅低吟              roar_executioner 影處刑者野獸低吼
//     roar_devourer 魔王多重咆哮
//     bossDie      Boss 死亡（長）               phase      階段轉換轟鳴（長）
//     drink        喝藥                          charge     連段蓄勢（拔劍聲＋魔力）
//     gradePerfect 判定完美（清亮鈴）            gradeNormal 判定普通（短促）     gradeWrong 判定錯誤（悶響）
//     finisher     終結重擊                      ice        冰裂（冰霜祭司招式）  dark  暗影（處刑者／魔王招式）
//     tick         介面小提示                    bell       遠鐘（配樂用，也可當儀式音）
// 其他匯出：sfxPreload()（進魂系戰鬥前先載）、setSfxBoss(id)（roar 沒帶 boss 時用）、sfxReady(name)、SFX_NAMES
import { $, lsGet, lsSet } from './util.js';

// 音量常數集中在這裡，之後要調整只改這一段
export const VOL={
  bgm:.02,       // 配樂主音量（打怪 bright）
  bgmSoul:.015,  // 魂系配樂主音量（使用者要求小聲；量測整體 RMS 約與打怪配樂同級）
  bgmDuck:.006,  // 朗讀時的配樂音量
  sfx:.7,        // 音效整體倍率（1 = 原始音量）
  // 魂系配樂各聲部的相對音量（乘在 bgmSoul 上）
  soulMel:.42, soulBass:.8, soulPad:.34, soulDrum:.9, soulBell:.5, soulChoir:.22,
};

let actx=null;
function ac(){actx=actx||new (window.AudioContext||window.webkitAudioContext)();if(actx.state==="suspended")actx.resume();return actx}

/* ───────── 取樣 ───────── */
const N=(b,n)=>Array.from({length:n},(_,i)=>b+(i+1));
// 群組名 → 檔名（public/sfx/<檔名>.mp3）
const FILES={
  clash:N("clash",4), clashBig:N("clashBig",2), parry:N("parry",2),
  swingL:N("swingL",5), swingH:N("swingH",3), flesh:N("flesh",3), stone:N("stone",2), block:N("block",2), roll:N("roll",2),
  footstep:N("footstep",4), stomp:N("stomp",2), slam:N("slam",2), hurt:N("hurt",2),
  roar:["roar1"], roar_sentinel:["roar_sentinel"], roar_gargoyle:["roar_gargoyle"], roar_priest:["roar_priest"],
  roar_executioner:["roar_executioner"], roar_devourer:["roar_devourer"],
  bossDie:["bossDie"], phase:["phase"], drink:["drink"], charge:["charge"], finisher:["finisher"], ice:["ice"], dark:["dark"],
  gradePerfect:["gradePerfect"], gradeNormal:["gradeNormal"], gradeWrong:["gradeWrong"], tick:["tick"], bell:["bell"],
};
// 各群組的基準音量（檔案都正規化到峰值 -1 dB，這裡做混音平衡）
const GAIN={clash:.55,clashBig:.7,parry:.65,swingL:.42,swingH:.55,flesh:.6,stone:.6,block:.62,roll:.42,footstep:.3,stomp:.75,slam:.8,hurt:.55,
  roar:.75,roar_sentinel:.8,roar_gargoyle:.62,roar_priest:.78,roar_executioner:.78,roar_devourer:.85,bossDie:.85,phase:.72,drink:.55,charge:.45,
  finisher:.85,ice:.55,dark:.6,gradePerfect:.4,gradeNormal:.38,gradeWrong:.5,tick:.3,bell:.5};
// 舊名字 → 取樣組合 [群組, 音量倍率]
const ALIAS={shot:[["tick",1]],hit:[["flesh",1],["clash",.45]],crit:[["clashBig",1],["flesh",.8]],faint:[["clashBig",.55],["stomp",.7]],
  win:[["gradePerfect",1]],lose:[["bell",.9],["gradeWrong",.8]],step:[["stomp",1]],heavy:[["slam",1]]};
// 取樣沒載好時的合成退路：新名字 → [舊合成名, 音量倍率, low]
const SYN={clash:["parry",.8],clashBig:["crit",.8],swingL:["swoosh",1],swingH:["swoosh",1,1],flesh:["hit",1],stone:["hit",1],block:["parry",.7],
  roll:["swoosh",.6,1],footstep:["step",.25],stomp:["step",1],slam:["heavy",1],bossDie:["heavy",1],phase:["heavy",.8],drink:["win",.7],
  charge:["shot",.6],finisher:["crit",1],ice:["parry",.6],dark:["roar",.4],gradePerfect:["win",.5],gradeNormal:["shot",.6],gradeWrong:["hurt",.5],
  tick:["shot",.6],bell:["faint",.4]};
export const SFX_NAMES=[...new Set(["shot","hit","crit","hurt","parry","faint","win","lose","step","swoosh","heavy","roar",...Object.keys(FILES)])];

const BUF=new Map();       // 檔名 → AudioBuffer
const LAST=new Map();      // 群組 → {i:上次用的檔, t:上次時間}
let curBoss=null,loading=null,useB64=null;
export function setSfxBoss(id){curBoss=id||null}
export const sfxReady=n=>(FILES[n]||[]).some(f=>BUF.has(f));
const SFX_BASE=()=>((import.meta.env&&import.meta.env.BASE_URL)||"./")+"sfx/";
function unB64(buf){const t=new TextDecoder().decode(buf).replace(/\s+/g,""),b=atob(t),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer}
const decode=(c,ab)=>new Promise((res,rej)=>{try{const p=c.decodeAudioData(ab,res,rej);if(p&&p.then)p.then(res,rej)}catch(e){rej(e)}});
async function loadOne(c,f){const url=SFX_BASE()+f+".mp3";
  // 先抓 mp3；失敗（Artifact 版沒有 mp3 檔型、404、解碼失敗）再抓 .mp3.b64.txt。一旦確定哪種可用，後面的檔就直接用那種。
  const tryMp3=async()=>{const r=await fetch(url);if(!r.ok)throw new Error("HTTP "+r.status);return decode(c,await r.arrayBuffer())};
  const tryB64=async()=>{const r=await fetch(url+".b64.txt");if(!r.ok)throw new Error("HTTP "+r.status);return decode(c,unB64(await r.arrayBuffer()))};
  const order=useB64===true?[tryB64,tryMp3]:[tryMp3,tryB64];
  for(let k=0;k<order.length;k++){try{const b=await order[k]();if(useB64===null)useB64=(order[k]===tryB64);BUF.set(f,b);return}catch(e){}}}
// 預載全部取樣（約 0.5 MB）。第一次呼叫 sfx／bgmStart 時會自動開始；進魂系戰鬥前可先呼叫。
export function sfxPreload(){if(loading)return loading;let c;try{c=ac()}catch(e){return Promise.resolve()}
  const all=Object.values(FILES).flat(),q=all.slice();
  // 先載一個探路（決定走 mp3 還是 b64），再 6 條並行
  loading=loadOne(c,q.shift()).then(()=>Promise.all(Array.from({length:6},async()=>{while(q.length)await loadOne(c,q.shift())}))).catch(()=>{});
  return loading}
let voices=0;
function playGroup(c,g,mul,o){const fs=(FILES[g]||[]).filter(f=>BUF.has(f));if(!fs.length)return false;
  const now=c.currentTime,last=LAST.get(g);
  if(last&&now-last.t<.03&&g!=="clash"&&g!=="flesh")return true; // 同一聲 30 毫秒內不重複疊（腳步、踏步連發）
  if(voices>28)return true;
  let i=Math.floor(Math.random()*fs.length);if(fs.length>1&&last&&fs[i]===last.f)i=(i+1)%fs.length;
  const s=c.createBufferSource(),gg=c.createGain();s.buffer=BUF.get(fs[i]);
  s.playbackRate.value=(o.rate||1)*(1+(Math.random()*2-1)*.05); // 音高隨機 ±5%，避免重複感
  gg.gain.value=VOL.sfx*(GAIN[g]==null?.6:GAIN[g])*mul;s.connect(gg);gg.connect(c.destination);
  voices++;s.onended=()=>{voices--;try{gg.disconnect()}catch(e){}};s.start(now);LAST.set(g,{f:fs[i],t:now});return true}

// o.v：這一聲的音量倍率（0–1，只會更小聲）；o.low：swoosh 用較低沉的版本（Boss 揮擊）；o.boss：roar 用哪隻 Boss；o.rate：音高倍率
export function sfx(t,o={}){try{const c=ac();if(!loading)sfxPreload();const ov=Math.max(0,Math.min(1,o.v==null?1:o.v));
  let plan;
  if(t==="roar"){const b=o.boss||curBoss;plan=[[b&&FILES["roar_"+b]?"roar_"+b:"roar",1]]}
  else if(t==="swoosh")plan=[[o.low?"swingH":"swingL",1]];
  else plan=ALIAS[t]||(FILES[t]?[[t,1]]:null);
  if(plan&&plan.every(([g])=>sfxReady(g))){for(const[g,m]of plan)playGroup(c,g,m*ov,o);return}
  // 退路：合成音
  const sy=SYN[t];if(sy)synth(c,sy[0],{v:ov*sy[1],low:sy[2]||o.low});else synth(c,t.startsWith("roar")?"roar":t,{v:ov,low:o.low});
}catch(e){}}

/* 舊版合成音（取樣的退路） */
function synth(c,t,o){const n=c.currentTime,ov=Math.max(0,Math.min(1,o.v==null?1:o.v));
  const tone=(f1,f2,d,type,v,at=0)=>{const o=c.createOscillator(),gg=c.createGain();o.type=type;o.frequency.setValueAtTime(f1,n+at);o.frequency.exponentialRampToValueAtTime(f2,n+at+d);gg.gain.setValueAtTime(v*VOL.sfx*ov,n+at);gg.gain.exponentialRampToValueAtTime(.001,n+at+d);o.connect(gg);gg.connect(c.destination);o.start(n+at);o.stop(n+at+d)};
  const noise=(d,v,at=0)=>{const b=c.createBuffer(1,c.sampleRate*d,c.sampleRate),a=b.getChannelData(0);for(let i=0;i<a.length;i++)a[i]=(Math.random()*2-1)*(1-i/a.length);const s=c.createBufferSource(),gg=c.createGain();s.buffer=b;gg.gain.value=v*VOL.sfx*ov;s.connect(gg);gg.connect(c.destination);s.start(n+at)};
  // 濾波雜訊：type＝lowpass／bandpass，f1→f2 掃頻，起音 a 秒（破風聲、咆哮的氣聲、踏步的悶響）
  const fnoise=(d,v,type,f1,f2,q=1,at=0,a=.01)=>{const b=c.createBuffer(1,Math.ceil(c.sampleRate*d),c.sampleRate),ch=b.getChannelData(0);for(let i=0;i<ch.length;i++)ch[i]=Math.random()*2-1;
    const s=c.createBufferSource(),f=c.createBiquadFilter(),gg=c.createGain();s.buffer=b;f.type=type;f.Q.value=q;f.frequency.setValueAtTime(f1,n+at);f.frequency.exponentialRampToValueAtTime(f2,n+at+d);
    gg.gain.setValueAtTime(.0001,n+at);gg.gain.linearRampToValueAtTime(v*VOL.sfx*ov,n+at+a);gg.gain.exponentialRampToValueAtTime(.001,n+at+d);s.connect(f);f.connect(gg);gg.connect(c.destination);s.start(n+at);s.stop(n+at+d+.02)};
  if(t==="shot")tone(300,1200,.18,"square",.08);
  if(t==="hit"){noise(.25,.35,.0);tone(180,40,.3,"sine",.5)}
  if(t==="crit"){noise(.4,.45);tone(220,30,.5,"sawtooth",.25);tone(880,1760,.25,"square",.08,.05)}
  if(t==="hurt"){tone(520,90,.45,"sawtooth",.2);noise(.3,.3,.05)}
  if(t==="parry"){tone(1400,2400,.12,"square",.1);noise(.12,.3)}
  if(t==="faint")tone(600,60,.9,"triangle",.3);
  if(t==="win")[523,659,784,1047].forEach((f,i)=>tone(f,f,.22,"square",.08,i*.12));
  if(t==="lose")[392,330,262,196].forEach((f,i)=>tone(f,f*.98,.3,"triangle",.2,i*.2));
  // 魂系用的重低音（音量都不超過既有的 hit：正弦 0.5）
  if(t==="step"){tone(72,38,.28,"sine",.32);fnoise(.16,.12,"lowpass",420,90,.7)}             // 巨獸踏步
  if(t==="swoosh"){if(o.low)fnoise(.32,.2,"bandpass",260,1300,1.4,0,.12);else fnoise(.2,.16,"bandpass",900,3200,1.6,0,.07)} // 揮擊破風
  if(t==="heavy"){tone(110,32,.55,"sine",.45);fnoise(.35,.18,"lowpass",900,120,.8)}         // 重擊、落地
  if(t==="roar"){tone(92,58,1.2,"sawtooth",.1);tone(61,44,1.3,"sine",.34);fnoise(1.1,.2,"bandpass",380,180,2.2,0,.18)} // 咆哮
}

/* 配樂：兩套主題
   bright（打怪）：C 大調，每步 0.2 秒，64 步循環；方波主旋律、三角波低音、hi-hat、大鼓（音量 VOL.bgm）
   soul（魂系）  ：A 小調，每步 0.5 秒，64 步循環（32 秒）；音量 VOL.bgmSoul，各聲部比例見 VOL.soul*
     ・低八度的三角波旋律、長音正弦低音與五度墊底（原本就有）
     ・弦樂墊：每個和弦（4 秒）兩把微走音鋸齒波過低通，慢起音慢收
     ・低鼓脈動：每 2 秒一下低沉的定音鼓（強–弱），第 14 步加一下輕的
     ・遠鐘：每 16 秒有機會敲一下（借 bell.mp3，沒載到就用合成鐘），音高跟著和弦根音
     ・低吟：每 32 秒一次，鋸齒波過兩個共振峰（像遠處的男聲「喔—」），很輕 */
const BGM={on:lsGet("vc-bgm","1")!=="0",g:null,timer:null,step:0,next:0,duck:false,theme:"bright"};
const MEL=[72,0,76,79,77,76,74,0, 72,74,76,0,74,72,71,0, 69,0,72,76,74,72,71,69, 71,72,74,0,79,0,0,0, 72,0,76,79,81,79,77,76, 77,0,74,77,76,74,72,0, 69,72,76,74,72,71,69,71, 72,0,0,0,67,0,0,0];
const BAS=[48,48,55,48,45,45,52,45,41,41,48,41,43,43,50,43];
// 魂系：Am – F – Dm – E 的緩慢進行（每個和弦 8 步＝4 秒），旋律在 A3–E4 之間低迴
const SMEL=[57,0,0,60,59,0,57,0, 53,0,0,57,55,0,53,0, 50,0,53,0,57,0,55,53, 52,0,0,0,56,0,0,0, 57,0,60,0,64,0,62,60, 60,0,57,0,53,0,0,0, 62,0,0,60,57,0,53,0, 52,0,56,0,52,0,0,0];
const SBAS=[33,29,26,28,33,29,26,28]; // A1 F1 D1 E1
const SCHORD=[[57,60,64],[53,57,60],[50,53,57],[52,56,59]]; // 弦樂墊：Am F Dm E（第三、四八度）
const mf=m=>440*Math.pow(2,(m-69)/12);
const bgmLevel=()=>BGM.duck?VOL.bgmDuck:(BGM.theme==="soul"?VOL.bgmSoul:VOL.bgm);
export const bgmOn=()=>BGM.on;
// theme：'bright'（預設，打怪）或 'soul'（魂系）。不傳就沿用上一次的主題（給開關按鈕用）。
export function bgmStart(theme){if(theme)BGM.theme=theme;if(!BGM.on||BGM.timer)return;let c;try{c=ac()}catch(e){return}
  if(BGM.theme==="soul"&&!loading)sfxPreload();
  BGM.g=c.createGain();BGM.g.gain.value=bgmLevel();BGM.g.connect(c.destination);BGM.step=0;BGM.next=c.currentTime+.1;
  const soul=BGM.theme==="soul",SP=soul?.5:.2,out=BGM.g;
  // a：起音時間（秒）。魂系用慢起音，聽起來像弦樂／管風琴的長音
  const note=(f,t,d,type,v,a=0)=>{const o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.value=f;
    if(a){g.gain.setValueAtTime(.001,t);g.gain.linearRampToValueAtTime(v,t+a)}else g.gain.setValueAtTime(v,t);
    g.gain.exponentialRampToValueAtTime(.001,t+d);o.connect(g);g.connect(out);o.start(t);o.stop(t+d+.02)};
  const hat=t=>{const b=c.createBuffer(1,c.sampleRate*.04,c.sampleRate),a=b.getChannelData(0);for(let i=0;i<a.length;i++)a[i]=(Math.random()*2-1)*(1-i/a.length);const s=c.createBufferSource(),g=c.createGain();g.gain.value=.25;s.buffer=b;s.connect(g);g.connect(out);s.start(t)};
  // ── 魂系聲部 ──
  // 弦樂墊：兩把微走音鋸齒波 → 低通（慢慢打開再關上）→ 慢起慢收
  const pad=(m,t,d,v)=>{const f=c.createBiquadFilter(),g=c.createGain();f.type="lowpass";f.Q.value=.6;f.frequency.setValueAtTime(380,t);f.frequency.linearRampToValueAtTime(1100,t+d*.5);f.frequency.linearRampToValueAtTime(420,t+d);
    g.gain.setValueAtTime(.0001,t);g.gain.linearRampToValueAtTime(v,t+1.6);g.gain.setValueAtTime(v,t+d-1.4);g.gain.linearRampToValueAtTime(.0001,t+d+.4);f.connect(g);g.connect(out);
    for(const dt of[-6,5]){const o=c.createOscillator();o.type="sawtooth";o.frequency.value=mf(m);o.detune.value=dt;o.connect(f);o.start(t);o.stop(t+d+.5)}};
  // 低鼓：正弦掉音（55→36 Hz）＋一點點低通雜訊當鼓皮
  const drum=(t,v)=>{const o=c.createOscillator(),g=c.createGain();o.type="sine";o.frequency.setValueAtTime(58,t);o.frequency.exponentialRampToValueAtTime(36,t+.5);
    g.gain.setValueAtTime(.0001,t);g.gain.linearRampToValueAtTime(v,t+.012);g.gain.exponentialRampToValueAtTime(.001,t+.9);o.connect(g);g.connect(out);o.start(t);o.stop(t+.95);
    const n=Math.ceil(c.sampleRate*.25),b=c.createBuffer(1,n,c.sampleRate),a=b.getChannelData(0);for(let i=0;i<n;i++)a[i]=(Math.random()*2-1)*Math.pow(1-i/n,3);
    const s=c.createBufferSource(),f=c.createBiquadFilter(),g2=c.createGain();s.buffer=b;f.type="lowpass";f.frequency.value=260;g2.gain.value=v*.5;s.connect(f);f.connect(g2);g2.connect(out);s.start(t)};
  // 遠鐘：有 bell.mp3 就用（音高對到和弦根音），沒有就用不諧和泛音的合成鐘
  const bell=(m,t,v)=>{const bb=BUF.get("bell");
    if(bb){const s=c.createBufferSource(),g=c.createGain();s.buffer=bb;s.playbackRate.value=Math.max(.5,Math.min(1.6,mf(m)/mf(57)));g.gain.value=v;s.connect(g);g.connect(out);s.start(t);return}
    for(const[k,vv,d]of[[1,1,4],[2.76,.45,2.4],[5.4,.22,1.4],[.5,.35,5]]){const o=c.createOscillator(),g=c.createGain();o.type="sine";o.frequency.value=mf(m)*k;
      g.gain.setValueAtTime(.0001,t);g.gain.linearRampToValueAtTime(v*vv*.5,t+.006);g.gain.exponentialRampToValueAtTime(.0001,t+d);o.connect(g);g.connect(out);o.start(t);o.stop(t+d+.05)}};
  // 低吟：鋸齒波（根音）過兩個帶通共振峰（約 400／800 Hz，「喔」），慢起慢收，帶一點顫音
  const choir=(m,t,d,v)=>{const g=c.createGain();g.gain.setValueAtTime(.0001,t);g.gain.linearRampToValueAtTime(v,t+d*.35);g.gain.linearRampToValueAtTime(.0001,t+d);g.connect(out);
    const fs=[[420,6,1],[820,8,.5]].map(([fr,q,gn])=>{const f=c.createBiquadFilter(),fg=c.createGain();f.type="bandpass";f.frequency.value=fr;f.Q.value=q;fg.gain.value=gn*4;f.connect(fg);fg.connect(g);return f});
    const lfo=c.createOscillator(),lg=c.createGain();lfo.frequency.value=4.8;lg.gain.value=5;lfo.connect(lg);
    for(const dt of[-8,0,9]){const o=c.createOscillator();o.type="sawtooth";o.frequency.value=mf(m);o.detune.value=dt;lg.connect(o.detune);fs.forEach(f=>o.connect(f));o.start(t);o.stop(t+d+.1)}
    lfo.start(t);lfo.stop(t+d+.1)};
  BGM.timer=setInterval(()=>{while(BGM.next<c.currentTime+.4){const s=BGM.step,t=BGM.next;
      if(soul){const m=SMEL[s%64],ci=(s>>3)%4;if(m)note(mf(m),t,SP*3.2,"triangle",.5*VOL.soulMel/.42,.08);
        if(s%8===0){const b=SBAS[(s>>3)%8],bv=VOL.soulBass;note(mf(b),t,SP*8.2,"sine",.9*bv,.4);note(mf(b+12),t,SP*8.2,"triangle",.32*bv,.6);note(mf(b+19),t,SP*8.2,"sine",.2*bv,.9);
          for(const pm of SCHORD[ci])pad(pm-12,t,SP*8,VOL.soulPad*.16)}
        if(s%8===0)drum(t,VOL.soulDrum);else if(s%8===4)drum(t,VOL.soulDrum*.55);else if(s%16===14)drum(t,VOL.soulDrum*.3);
        if(s%32===16&&Math.random()<.75)bell(SBAS[(s>>3)%8]+36,t,VOL.soulBell);
        if(s%64===32)choir(SBAS[(s>>3)%8]+24,t,SP*14,VOL.soulChoir)}
      else{const m=MEL[s%64];
        if(m)note(mf(m),t,SP*1.6,"square",.32);if(s%2===0)note(mf(BAS[(s>>2)%16]),t,SP*1.8,"triangle",.7);if(s%2===1)hat(t);if(s%8===0)note(110,t,.18,"sine",.9)}
      BGM.step++;BGM.next+=SP}},100)}
export function bgmStop(){clearInterval(BGM.timer);BGM.timer=null;try{BGM.g&&BGM.g.disconnect()}catch(e){}BGM.g=null}
// 朗讀時把配樂音量壓低
export function bgmDuck(d){BGM.duck=d;if(BGM.g&&actx)try{BGM.g.gain.setTargetAtTime(bgmLevel(),actx.currentTime,.15)}catch(e){}}
export function bgmToggle(){BGM.on=!BGM.on;lsSet("vc-bgm",BGM.on?"1":"0");if(BGM.on)bgmStart();else bgmStop();const b=$("#bgmb");if(b)b.textContent=BGM.on?"♪ 音樂開":"♪ 音樂關"}
