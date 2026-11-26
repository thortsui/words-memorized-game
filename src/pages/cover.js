// 魂系模式的封面（按「開始魂系戰鬥」後出現；外面是一般的背單字網站）：全螢幕 3D 背景＋墨金書法標題「單字魂」。3D 場景（three.js）動態載入，失敗或不支援 WebGL 時只顯示靜態背景。
import { $ } from '../core/util.js';

let cover=null;
export function leaveCover(){document.body.classList.remove("cover");if(cover){const c=cover;cover=null;c.then(v=>v&&v.dispose()).catch(()=>{})}}

export function renderCover({onStart,onBack}={}){
  leaveCover();document.body.classList.add("cover");window.scrollTo(0,0);
  $("#app").innerHTML=`<section class="cov">
  <div class="cov-bg" id="covbg"></div>
  <svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
    <filter id="brush" x="-5%" y="-10%" width="110%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".035 .09" numOctaves="3" seed="7" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G"/></filter></defs></svg>
  <div class="cov-ui">
    <div class="cov-head"><h1 class="cov-title" aria-label="單字魂"><span>單</span><span>字</span><span>魂</span></h1><div class="cov-seal" aria-hidden="true">字</div></div>
    <div class="cov-sub">WORD&nbsp;&nbsp;SOUL</div>
    <p class="cov-tag">一字一劍　斬盡遺忘</p>
    <div class="cov-btns">
      <button class="cov-btn main" id="covgo">踏上試煉</button>
      <button class="cov-btn" id="covback">返回設定</button>
    </div>
    <div class="cov-foot">背好單字，才能斬下魔王</div>
  </div></section>`;
  $("#covgo").onclick=()=>{leaveCover();onStart&&onStart()};$("#covback").onclick=()=>{leaveCover();onBack&&onBack()};
  const rm=matchMedia("(prefers-reduced-motion: reduce)").matches;
  let ok=false;try{const c=document.createElement("canvas");const gl=c.getContext("webgl2")||c.getContext("webgl");ok=!!gl;if(gl){const e=gl.getExtension("WEBGL_lose_context");e&&e.loseContext()}}catch(e){}
  if(!ok)return;
  const host=$("#covbg");
  cover=import("../battle/view3d/coverScene.js").then(m=>{if(!host.isConnected)return null;const v=m.createCover(host,{reducedMotion:rm});
      v.ready.then(()=>host.classList.add("on"));setTimeout(()=>host.classList.add("on"),4000);return v})
    .catch(err=>{console.warn("[cover] 3D 背景無法啟動",err);return null});
}
