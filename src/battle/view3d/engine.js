// 3D 引擎底層：renderer、單一 requestAnimationFrame 迴圈、遊戲時間（受時間倍率影響）、補間、頓格、震動、
// 解析度自動調降、頁面隱藏時暫停、資源釋放。場景（monsterScene／soulScene）只管內容。
import * as THREE from 'three';

export const ease={
  lin:t=>t,
  in:t=>t*t,
  out:t=>1-(1-t)*(1-t),
  io:t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2,
  in3:t=>t*t*t,
  out3:t=>1-Math.pow(1-t,3),
  back:t=>{const c=1.70158;return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2)},
  elastic:t=>t<=0?0:t>=1?1:Math.pow(2,-10*t)*Math.sin((t*10-.75)*2.0944)+1,
  // 0→1→0 的來回
  arc:t=>Math.sin(Math.PI*t),
};
export const lerp=(a,b,t)=>a+(b-a)*t;
export const clamp=(v,a,b)=>v<a?a:v>b?b:v;
export const rand=(a,b)=>a+Math.random()*(b-a);

export function createEngine(container,{reducedMotion=false}={}){
  const baseDpr=Math.min(window.devicePixelRatio||1,2);
  // DPR 2 的手機不開 MSAA（解析度已經夠細），省填色成本
  const renderer=new THREE.WebGLRenderer({antialias:baseDpr<2,powerPreference:"high-performance",alpha:false,stencil:false});
  renderer.setPixelRatio(baseDpr);
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  const canvas=renderer.domElement;canvas.className="v3-canvas";
  const wrap=document.createElement("div");wrap.className="v3d";
  const overlay=document.createElement("div");overlay.className="v3-ovl";
  wrap.append(canvas,overlay);container.innerHTML="";container.appendChild(wrap);

  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(45,1,.1,200);
  const E={THREE,renderer,scene,camera,canvas,overlay,wrap,container,rm:reducedMotion,
    dead:false,time:0,timeScale:1,dpr:baseDpr,quality:"high",fps:0,width:1,height:1,aspect:1,
    onResize:[],onQuality:[]};

  /* ---------- 補間（以遊戲時間計；real:true 則不受時間倍率影響） ---------- */
  let tweens=[];
  const durK=1;
  // fn(k, rawT)：k 是套過 easing 的 0..1。回傳 Promise，播完才 resolve。
  E.tween=(dur,fn,ez=ease.io,opt={})=>new Promise(res=>{
    if(E.dead||E.lost)return res(); // context 遺失期間不播演出，直接往下走
    tweens.push({t:0,dur:Math.max(.0001,dur*durK),fn,ez,res,real:!!opt.real,target:opt.target||null})});
  E.wait=(dur,opt)=>E.tween(dur,null,ease.lin,opt);
  // 把物件的數值屬性從目前值補間到目標值，例如 E.to(mesh.position,{x:1,y:2},.3)
  E.to=(obj,props,dur,ez=ease.io)=>{const from={};for(const k in props)from[k]=obj[k];
    return E.tween(dur,k=>{for(const p in props)obj[p]=lerp(from[p],props[p],k)},ez,{target:obj})};
  // 取消某個物件身上還在跑的補間（直接結束，不跳到終點）
  E.kill=obj=>{for(const tw of tweens)if(tw.target===obj&&!tw.done){tw.done=true;tw.res()}};

  /* ---------- 每幀更新 ---------- */
  const updaters=new Set();
  E.onUpdate=fn=>{updaters.add(fn);return()=>updaters.delete(fn)};

  /* ---------- 頓格／局部慢動作／震動 ---------- */
  let freezeUntil=0,slowUntil=0,slowK=1,shakeAmp=0,shakeDur=0,shakeT=0;
  E.hitStop=ms=>{if(reducedMotion)return;freezeUntil=Math.max(freezeUntil,performance.now()+ms)};
  E.slowmo=(k,ms)=>{if(reducedMotion)return;slowK=k;slowUntil=performance.now()+ms};
  E.shake=(amp,dur=.3)=>{if(reducedMotion)return;if(amp>=shakeAmp*(1-shakeT/Math.max(.001,shakeDur))){shakeAmp=amp;shakeDur=dur;shakeT=0}};

  /* ---------- 尺寸 ---------- */
  E.resize=()=>{const w=Math.max(1,container.clientWidth),h=Math.max(1,container.clientHeight);
    if(w===E.width&&h===E.height&&!E._forceResize)return;E._forceResize=false;
    E.width=w;E.height=h;E.aspect=w/h;renderer.setSize(w,h,false);camera.aspect=E.aspect;camera.updateProjectionMatrix();
    for(const f of E.onResize)f(w,h)
    // setSize 會清空畫布；立刻補畫一格，否則到下一個 rAF 之前會閃一下空白
    if(E._started&&!E.dead){try{renderer.render(scene,camera)}catch(e){}}};
  const ro=typeof ResizeObserver!=="undefined"?new ResizeObserver(()=>E.resize()):null;ro&&ro.observe(container);
  const onWinResize=()=>E.resize();window.addEventListener("resize",onWinResize);

  /* ---------- 掉幀偵測：分三段降級 ①DPR 降到 1 ②低畫質（場景各自關描邊／陰影／環境光、減粒子）③DPR 再降到 0.75 ----------
     累計 2 秒低於 38fps（中間沒有回到 48fps 以上）就降一段；任何一秒低於 20fps 就立刻把 ①② 一次做完。模型載完（E.armed）一秒後才開始判斷。 */
  let fpsN=0,fpsT=0,fpsReal=0,lowCount=0,warm=0;
  const LOCK=typeof window!=="undefined"&&window.__v3q||"";
  const setDpr=d=>{E.dpr=d;renderer.setPixelRatio(d);E._forceResize=true;E.resize()};
  const setLow=()=>{if(E.quality==="low")return;E.quality="low";for(const f of E.onQuality){try{f("low")}catch(e){console.warn("[view3d] quality",e)}}};
  function degrade(hard){
    if(E.dpr>1){setDpr(1);if(hard)setLow()}
    else if(E.quality!=="low")setLow();
    else if(E.dpr>.75)setDpr(.75);
    warm=1} // 降完先觀察一秒再判斷
  function fpsTick(rdt,real){fpsN++;fpsT+=rdt;fpsReal+=real;if(fpsT<1)return;E.fps=Math.round(fpsN/Math.max(fpsT,fpsReal));fpsN=0;fpsT=0;fpsReal=0;container.dataset.fps=E.fps;container.dataset.dpr=E.dpr;container.dataset.quality=E.quality;container.dataset.calls=renderer.info.render.calls;
    if(!E.armed){warm=0;return}       // 還在載模型、編譯 shader：不列入判斷
    if(LOCK){if(LOCK==="low"&&E.dpr>.75){degrade(true);degrade();degrade()}return} // 測試用：window.__v3q="high" 不降級、"low" 一開始就降到底
    if(E.paused||++warm<=1)return;
    if(E.fps<20){lowCount=0;degrade(true);return} // 差很多（低於 20fps）：不等累計，量到就直接降兩級（DPR 1＋低畫質），已經降過就再往下一級
    if(warm<=2)return;
    if(E.fps<38)lowCount++;else if(E.fps>=48)lowCount=0;
    if(lowCount>=2){lowCount=0;degrade(E.fps<22)}}

  /* ---------- 主迴圈 ---------- */
  let raf=0,last=0;
  const shakeOff=new THREE.Vector3();
  function frame(now){raf=requestAnimationFrame(frame);
    let rdt=(now-last)/1000;last=now;if(rdt<=0)return;const real=Math.min(rdt,1);if(rdt>.1)rdt=.1;
    fpsTick(rdt,real);
    if(E.paused){renderer.render(scene,camera);return} // 暫停：畫面留著，時間不走
    let k=E.timeScale*(E.fast||1); // fast：跳過演出時的快轉倍率
    if(E.fast>1)rdt=Math.min(rdt,.034);if(now<freezeUntil)k*=.02;else if(now<slowUntil)k*=slowK;
    const dt=rdt*k;E.time+=dt;E.dt=dt;E.rdt=rdt;
    // 補間
    const n=tweens.length;let anyDone=false;
    for(let i=0;i<n;i++){const tw=tweens[i];if(tw.done){anyDone=true;continue}
      tw.t+=tw.real?rdt:dt;const r=tw.t>=tw.dur?1:tw.t/tw.dur;
      if(tw.fn){try{tw.fn(tw.ez(r),r)}catch(e){console.warn("[view3d] tween",e);tw.done=true;tw.res();anyDone=true;continue}}
      if(r>=1){tw.done=true;anyDone=true;tw.res()}}
    if(anyDone)tweens=tweens.filter(t=>!t.done);
    for(const f of updaters)f(dt,rdt,E.time);
    // 震動：只在這一幀暫時偏移鏡頭
    let sh=false;
    if(shakeAmp>0){shakeT+=rdt;const kk=1-shakeT/shakeDur;if(kk<=0)shakeAmp=0;else{sh=true;shakeOff.set(rand(-1,1),rand(-1,1),rand(-1,1)).multiplyScalar(shakeAmp*kk);camera.position.add(shakeOff)}}
    renderer.render(scene,camera);
    if(sh)camera.position.sub(shakeOff)}
  const start=()=>{if(raf||E.dead)return;last=performance.now();raf=requestAnimationFrame(frame)};
  const stop=()=>{cancelAnimationFrame(raf);raf=0};
  // 頁面隱藏時暫停渲染（動畫也跟著停，回來再接著播）
  const onVis=()=>{document.hidden?stop():start()};document.addEventListener("visibilitychange",onVis);
  // WebGL context 遺失時不要讓瀏覽器丟例外；回來後繼續畫
  // context 遺失：先讓進行中的演出全部結束（不然每個事件都要等保險的 15 秒），再試著恢復；恢復不了由 scene.js 換成文字畫面
  E.onLost=[];const loseExt=renderer.getContext().getExtension("WEBGL_lose_context");
  const onLost=e=>{e.preventDefault();E.lost=true;stop();const tw=tweens;tweens=[];for(const t of tw)if(!t.done){t.done=true;t.res()}for(const f of E.onLost)f();
    setTimeout(()=>{if(E.lost&&!E.dead){try{loseExt&&loseExt.restoreContext()}catch(err){}}},400)};
  const onRestored=()=>{E.lost=false;E._forceResize=true;E.resize();start()};
  canvas.addEventListener("webglcontextlost",onLost);canvas.addEventListener("webglcontextrestored",onRestored);
  E.start=()=>{E.resize();E._started=true;if(!document.hidden)start()};

  /* ---------- 把 3D 座標投影到畫面（給 DOM 浮字用） ---------- */
  const pv=new THREE.Vector3();
  E.project=p=>{pv.copy(p).project(camera);return{x:(pv.x*.5+.5)*E.width,y:(-pv.y*.5+.5)*E.height,behind:pv.z>1}};

  /* ---------- 釋放 ---------- */
  const extra=[]; // 不在場景樹裡、但需要 dispose 的資源（共用貼圖等）
  E.track=o=>{extra.push(o);return o};
  E.disposeObject=obj=>{obj.traverse(o=>{if(o.geometry)o.geometry.dispose();const ms=o.material?(Array.isArray(o.material)?o.material:[o.material]):[];
    for(const m of ms){for(const k in m){const v=m[k];if(v&&v.isTexture)v.dispose()}if(m.uniforms)for(const u in m.uniforms){const v=m.uniforms[u].value;if(v&&v.isTexture)v.dispose()}m.dispose()}
    if(o.skeleton&&o.skeleton.boneTexture)o.skeleton.dispose()})};
  E.dispose=()=>{if(E.dead)return;E.dead=true;stop();
    document.removeEventListener("visibilitychange",onVis);window.removeEventListener("resize",onWinResize);ro&&ro.disconnect();
    canvas.removeEventListener("webglcontextlost",onLost);canvas.removeEventListener("webglcontextrestored",onRestored);
    const tw=tweens;tweens=[];for(const t of tw)if(!t.done){t.done=true;t.res()}
    updaters.clear();
    try{E.disposeObject(scene)}catch(e){}
    if(scene.background&&scene.background.isTexture)scene.background.dispose();
    for(const o of extra){try{o.dispose&&o.dispose()}catch(e){}}
    renderer.renderLists.dispose();renderer.dispose();
    try{renderer.forceContextLoss()}catch(e){}
    wrap.remove()};
  return E;
}
