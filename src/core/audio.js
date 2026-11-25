// 音效與配樂：全部用 Web Audio 合成，沒有音檔
import { $, lsGet, lsSet } from './util.js';

// 音量常數集中在這裡，之後要調整只改這一段
export const VOL={
  bgm:.02,       // 配樂主音量
  bgmDuck:.006,  // 朗讀時的配樂音量
  sfx:.7,        // 音效整體倍率（1 = 原始音量）
};

let actx=null;
function ac(){actx=actx||new (window.AudioContext||window.webkitAudioContext)();if(actx.state==="suspended")actx.resume();return actx}

export function sfx(t){try{const c=ac(),n=c.currentTime;
  const tone=(f1,f2,d,type,v,at=0)=>{const o=c.createOscillator(),gg=c.createGain();o.type=type;o.frequency.setValueAtTime(f1,n+at);o.frequency.exponentialRampToValueAtTime(f2,n+at+d);gg.gain.setValueAtTime(v*VOL.sfx,n+at);gg.gain.exponentialRampToValueAtTime(.001,n+at+d);o.connect(gg);gg.connect(c.destination);o.start(n+at);o.stop(n+at+d)};
  const noise=(d,v,at=0)=>{const b=c.createBuffer(1,c.sampleRate*d,c.sampleRate),a=b.getChannelData(0);for(let i=0;i<a.length;i++)a[i]=(Math.random()*2-1)*(1-i/a.length);const s=c.createBufferSource(),gg=c.createGain();s.buffer=b;gg.gain.value=v*VOL.sfx;s.connect(gg);gg.connect(c.destination);s.start(n+at)};
  if(t==="shot")tone(300,1200,.18,"square",.08);
  if(t==="hit"){noise(.25,.35,.0);tone(180,40,.3,"sine",.5)}
  if(t==="crit"){noise(.4,.45);tone(220,30,.5,"sawtooth",.25);tone(880,1760,.25,"square",.08,.05)}
  if(t==="hurt"){tone(520,90,.45,"sawtooth",.2);noise(.3,.3,.05)}
  if(t==="parry"){tone(1400,2400,.12,"square",.1);noise(.12,.3)}
  if(t==="faint")tone(600,60,.9,"triangle",.3);
  if(t==="win")[523,659,784,1047].forEach((f,i)=>tone(f,f,.22,"square",.08,i*.12));
  if(t==="lose")[392,330,262,196].forEach((f,i)=>tone(f,f*.98,.3,"triangle",.2,i*.2));}catch(e){}}

/* 配樂：兩套主題，音量都由 VOL 控制
   bright（打怪）：C 大調，每步 0.2 秒，64 步循環；方波主旋律、三角波低音、hi-hat、大鼓
   soul（魂系）  ：A 小調，每步 0.5 秒，64 步循環；低八度的三角波旋律、長音正弦低音與五度墊底、緩慢的低鼓，沒有 hi-hat */
const BGM={on:lsGet("vc-bgm","1")!=="0",g:null,timer:null,step:0,next:0,duck:false,theme:"bright"};
const MEL=[72,0,76,79,77,76,74,0, 72,74,76,0,74,72,71,0, 69,0,72,76,74,72,71,69, 71,72,74,0,79,0,0,0, 72,0,76,79,81,79,77,76, 77,0,74,77,76,74,72,0, 69,72,76,74,72,71,69,71, 72,0,0,0,67,0,0,0];
const BAS=[48,48,55,48,45,45,52,45,41,41,48,41,43,43,50,43];
// 魂系：Am – F – Dm – E 的緩慢進行（每個和弦 8 步＝4 秒），旋律在 A3–E4 之間低迴
const SMEL=[57,0,0,60,59,0,57,0, 53,0,0,57,55,0,53,0, 50,0,53,0,57,0,55,53, 52,0,0,0,56,0,0,0, 57,0,60,0,64,0,62,60, 60,0,57,0,53,0,0,0, 62,0,0,60,57,0,53,0, 52,0,56,0,52,0,0,0];
const SBAS=[33,29,26,28,33,29,26,28]; // A1 F1 D1 E1
const mf=m=>440*Math.pow(2,(m-69)/12);
export const bgmOn=()=>BGM.on;
// theme：'bright'（預設，打怪）或 'soul'（魂系）。不傳就沿用上一次的主題（給開關按鈕用）。
export function bgmStart(theme){if(theme)BGM.theme=theme;if(!BGM.on||BGM.timer)return;let c;try{c=ac()}catch(e){return}
  BGM.g=c.createGain();BGM.g.gain.value=BGM.duck?VOL.bgmDuck:VOL.bgm;BGM.g.connect(c.destination);BGM.step=0;BGM.next=c.currentTime+.1;
  const soul=BGM.theme==="soul",SP=soul?.5:.2;
  // a：起音時間（秒）。魂系用慢起音，聽起來像弦樂／管風琴的長音
  const note=(f,t,d,type,v,a=0)=>{const o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.value=f;
    if(a){g.gain.setValueAtTime(.001,t);g.gain.linearRampToValueAtTime(v,t+a)}else g.gain.setValueAtTime(v,t);
    g.gain.exponentialRampToValueAtTime(.001,t+d);o.connect(g);g.connect(BGM.g);o.start(t);o.stop(t+d+.02)};
  const hat=t=>{const b=c.createBuffer(1,c.sampleRate*.04,c.sampleRate),a=b.getChannelData(0);for(let i=0;i<a.length;i++)a[i]=(Math.random()*2-1)*(1-i/a.length);const s=c.createBufferSource(),g=c.createGain();g.gain.value=.25;s.buffer=b;s.connect(g);g.connect(BGM.g);s.start(t)};
  BGM.timer=setInterval(()=>{while(BGM.next<c.currentTime+.4){const s=BGM.step,t=BGM.next;
      if(soul){const m=SMEL[s%64];if(m)note(mf(m),t,SP*3.2,"triangle",.5,.08);
        if(s%8===0){const b=SBAS[(s>>3)%8];note(mf(b),t,SP*8.2,"sine",.9,.4);note(mf(b+12),t,SP*8.2,"triangle",.32,.6);note(mf(b+19),t,SP*8.2,"sine",.2,.9)}
        if(s%8===0||s%16===11)note(58,t,.5,"sine",.8)}
      else{const m=MEL[s%64];
        if(m)note(mf(m),t,SP*1.6,"square",.32);if(s%2===0)note(mf(BAS[(s>>2)%16]),t,SP*1.8,"triangle",.7);if(s%2===1)hat(t);if(s%8===0)note(110,t,.18,"sine",.9)}
      BGM.step++;BGM.next+=SP}},100)}
export function bgmStop(){clearInterval(BGM.timer);BGM.timer=null;try{BGM.g&&BGM.g.disconnect()}catch(e){}BGM.g=null}
// 朗讀時把配樂音量壓低
export function bgmDuck(d){BGM.duck=d;if(BGM.g&&actx)try{BGM.g.gain.setTargetAtTime(d?VOL.bgmDuck:VOL.bgm,actx.currentTime,.15)}catch(e){}}
export function bgmToggle(){BGM.on=!BGM.on;lsSet("vc-bgm",BGM.on?"1":"0");if(BGM.on)bgmStart();else bgmStop();const b=$("#bgmb");if(b)b.textContent=BGM.on?"♪ 音樂開":"♪ 音樂關"}
