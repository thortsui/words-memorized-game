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

  /* ---------- 每幀更新 ----------
     order：小的先跑。場景的走位邏輯（-20〜-10）→ 角色（0：動畫混合器、陰影跟腳）→ 特效（50）→ 鏡頭（100）。
     原本依註冊順序跑：Boss 比鏡頭晚建立，鏡頭會用到上一格的 Boss 位置，陰影也會落後主角一格（走位時腳下會抖）。 */
  let updaters=[],updN=0;
  E.onUpdate=(fn,order=0)=>{const u={fn,order,n:updN++};updaters.push(u);updaters.sort((a,b)=>a.order-b.order||a.n-b.n);return()=>{u.dead=true;updaters=updaters.filter(x=>x!==u)}};

  /* ---------- 頓格／局部慢動作／震動 ----------
     頓格（hitStop）：命中那一刻時間幾乎停住 60–150ms（輕擊短、重擊長）。
     震動：平滑的多頻正弦雜訊（不是每格亂跳的白雜訊）＋輕微滾轉，強度依重量分級；freq 越低越「沉」。
     rumble：低頻、持續的晃動（咆哮、巨獸踏步）。prefers-reduced-motion 時震動、頓格、局部慢動作全部關掉。 */
  let freezeUntil=0,slowUntil=0,slowFrom=0,slowK=1;
  const shakes=[]; // {amp, dur, t, freq, roll, ph}
  E.hitStop=ms=>{if(reducedMotion)return;freezeUntil=Math.max(freezeUntil,performance.now()+ms)};
  E.slowmo=(k,ms)=>{if(reducedMotion)return;slowK=k;slowFrom=performance.now();slowUntil=slowFrom+ms};
  E.shake=(amp,dur=.3,o={})=>{if(reducedMotion||amp<=0)return;if(shakes.length>5)shakes.shift();
    shakes.push({amp,dur,t:0,freq:o.freq||(amp>.08?14:22),roll:o.roll==null?amp*.35:o.roll,ph:[rand(0,9),rand(0,9),rand(0,9),rand(0,9)],dir:o.dir||null})};
  E.rumble=(amp,dur=1)=>E.shake(amp,dur,{freq:7,roll:amp*.5});

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
  let raf=0,last=0,avgDt=1/60,tsNow=1;
  const shakeOff=new THREE.Vector3(),camQ=new THREE.Quaternion();
  function frame(now){raf=requestAnimationFrame(frame);
    let rdt=(now-last)/1000;last=now;if(rdt<=0)return;const real=Math.min(rdt,1);
    // 幀時間尖峰：偶發的長幀（GC、shader 編譯、DOM 重排）不要讓動作一次跳一大段——上限是平均幀長的 1.6 倍（至少 1/20 秒、最多 0.1 秒）。
    // 真的一直很慢的裝置平均幀長會跟著變大，遊戲時間仍和真實時間一致。
    const cap=Math.max(.05,Math.min(.1,avgDt*1.6));avgDt+=(Math.min(rdt,.25)-avgDt)*.08;if(rdt>cap)rdt=cap;
    fpsTick(rdt,real);
    if(E.paused){renderer.render(scene,camera);return} // 暫停：畫面留著，時間不走
    // 時間倍率不直接跳：指令選單的慢動作、出招時的 0.85 倍都在約 0.1 秒內滑過去
    tsNow+=(E.timeScale-tsNow)*(1-Math.exp(-rdt*14));if(Math.abs(E.timeScale-tsNow)<.002)tsNow=E.timeScale;
    let k=tsNow*(E.fast||1); // fast：跳過演出時的快轉倍率
    // 局部慢動作：最後 35% 的時間平滑回到正常速度（不會突然恢復）
    if(E.fast>1)rdt=Math.min(rdt,.034);if(now<freezeUntil)k*=.02;else if(now<slowUntil){const r=(now-slowFrom)/Math.max(1,slowUntil-slowFrom);k*=r<.65?slowK:lerp(slowK,1,ease.io((r-.65)/.35))}
    const dt=rdt*k;E.time+=dt;E.dt=dt;E.rdt=rdt;
    // 補間
    const n=tweens.length;let anyDone=false;
    for(let i=0;i<n;i++){const tw=tweens[i];if(tw.done){anyDone=true;continue}
      tw.t+=tw.real?rdt:dt;const r=tw.t>=tw.dur?1:tw.t/tw.dur;
      if(tw.fn){try{tw.fn(tw.ez(r),r)}catch(e){console.warn("[view3d] tween",e);tw.done=true;tw.res();anyDone=true;continue}}
      if(r>=1){tw.done=true;anyDone=true;tw.res()}}
    if(anyDone)tweens=tweens.filter(t=>!t.done);
    for(const u of updaters)if(!u.dead)u.fn(dt,rdt,E.time);
    // 震動：只在這一幀暫時偏移／滾轉鏡頭（畫完就還原，不影響鏡頭的阻尼計算）
    let sh=false,roll=0;shakeOff.set(0,0,0);
    for(let i=shakes.length-1;i>=0;i--){const s=shakes[i];s.t+=rdt;const r=s.t/s.dur;if(r>=1){shakes.splice(i,1);continue}
      const env=(1-r)*(1-r)*Math.min(1,s.t*40),w=s.freq*Math.PI*2*s.t,a=s.amp*env; // 起音 25ms、平方衰減
      const nx=Math.sin(w+s.ph[0])*.6+Math.sin(w*2.3+s.ph[1])*.4,ny=Math.sin(w*1.1+s.ph[2])*.6+Math.sin(w*1.9+s.ph[3])*.4;
      if(s.dir){shakeOff.addScaledVector(s.dir,a*Math.sin(w*.5+s.ph[0]))}
      shakeOff.x+=nx*a;shakeOff.y+=ny*a*.8;roll+=Math.sin(w*.7+s.ph[1])*s.roll*env;sh=true}
    if(sh){camQ.copy(camera.quaternion);shakeOff.applyQuaternion(camera.quaternion);camera.position.add(shakeOff);if(roll)camera.rotateZ(roll*.25)}
    renderer.render(scene,camera);
    if(sh){camera.position.sub(shakeOff);camera.quaternion.copy(camQ)}}
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
    updaters=[];
    try{E.disposeObject(scene)}catch(e){}
    if(scene.background&&scene.background.isTexture)scene.background.dispose();
    for(const o of extra){try{o.dispose&&o.dispose()}catch(e){}}
    renderer.renderLists.dispose();renderer.dispose();
    try{renderer.forceContextLoss()}catch(e){}
    wrap.remove()};
  return E;
}
