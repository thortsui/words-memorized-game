// 打擊感（Feel）：hitstop、震屏、鏡頭衝擊（推拉／側移／繞行／FOV）、慢動作，全部依 design.md §6 的 S0–S7 分級，數值集中在下面一張表。
// 場景只呼叫分級函式（feel.hit("S3")、feel.strike(p)、feel.hurt(p)…），不再各自寫 eng.hitStop／eng.shake 的數字。
//
// 規則（§6）：
//   ・Hitstop 不疊加：取最大值（引擎的 freezeUntil 本來就取 max）；同一 300 ms 內最多 2 次；一套連斬合計 ≤ 450 ms。
//   ・hitstop／慢動作只影響畫面時間（eng.time），答題計時器用 performance.now()（controller.js 的 timer()），不受影響。
//   ・eng.rm（減少動態）：震屏 ×0.4（引擎在 rm 下本來就完全不震，等於更保守）、取消鏡頭推拉、慢動作保留（引擎 rm 下關掉 slowmo，這裡用 eng.fast 自己補）。
//   ・手機（粗指標或短邊 < 600px）：震屏 ×0.65、鏡頭推拉 ×0.8，並限制同時疊加的震動強度。
// 鏡頭衝擊是「畫面層」偏移：鏡頭彈簧（soulScene 的 updateCamera，order 100）算完之後才加上去（order 101），每格重算、不累積，
// 也不改鏡頭本身的阻尼狀態；FOV 在 order 99 先還原再讓 updateCamera 計算。
import * as THREE from 'three';
import { ease, lerp, clamp } from './engine.js';

/* ---------- 分級表（單位：hitstop ms；shake = [幅度, 秒, 頻率]；cam：push 前推 m、side 側移 m、fov 度、elev 仰角度、bias 偏向命中方向 m；slow = [倍率, ms]） ---------- */
export const FEEL={
  S0:{stop:0,  shake:[.012,.20,9]},                                                     // 腳步、Boss 落地
  S1:{stop:60, shake:[.025,.22,20], cam:{push:.15,dur:.22}},                             // 一般斬、連斬 1–2 段、格擋
  S2:{stop:80, shake:[.045,.28,18], cam:{push:.25,fov:-1,dur:.28}},                      // 連斬 3–4 段、玩家輕受擊
  S3:{stop:110,shake:[.07,.35,14],  cam:{push:.4,fov:-2,bias:.18,dur:.36},slow:[.5,200]}, // 完美斬、連斬第 5 段、玩家重受擊（慢放只限完美斬）
  S4:{stop:130,shake:[.06,.30,24],  cam:{side:.6,fov:-2,dur:.5},slow:[.22,700],slowMid:[.4,350]}, // 彈反、弱點擊破、突擊
  S5:{stop:160,shake:[.09,.45,12],  cam:{elev:20,fov:-4,push:.2,dur:.9},slow:[.25,700]}, // 終結斬（擊殺 Boss）
  S6:{stop:0,  shake:[.16,.9,11],   pre:[.35,150]},                                      // 階段轉換爆發（鏡頭由 phaseShow 負責）
  S7:{stop:200,shake:[.05,.5,10],   rumble:[.04,1.2], cam:{elev:14,lift:.8,push:-.6,dur:1.6,hold:.5},slow:[.5,900]}, // Boss 死亡：拉高俯視
};
// 非表內的特殊事件（都由上面的等級派生，只改少數欄位）
const EXTRA={
  dodge:  {stop:0,  shake:[.045,.25,14],cam:{side:-.3,dur:.4}},                 // 翻滾閃開，Boss 砸地
  ambush: {stop:100,shake:[.07,.35,12], cam:{push:.45,fov:-3,dur:.45}},          // 突襲切到面前（S3 減一點停頓）
  land:   {stop:0,  shake:[.08,.6,10],  cam:{push:-.15,dur:.5}},                 // Boss 登場站定
  loom:   {stop:0,  shake:[.03,.3,8]},                                           // Boss 衝到近身／踏前一步
  // 必殺／突襲的預警壓迫：鏡頭慢慢往前壓、視角收窄，直到玩家作答（任何下一個回饋事件會自動放開）
  pressure:{cam:{push:.35,fov:-3,dur:1}},
  dangerPressure:{cam:{push:.55,fov:-5,elev:-4,dur:1}},
};
const COMBO_BUDGET=450,WIN_MS=300,WIN_MAX=2,FLASH_MAX_PER_S=3;

export function createFeel(eng,ctx={}){
  const {camera}=eng,rm=!!eng.rm;
  const mobile=typeof window!=="undefined"&&((window.matchMedia&&window.matchMedia("(pointer:coarse)").matches)||Math.min(window.innerWidth||999,window.innerHeight||999)<600);
  const SHK=(rm?.4:1)*(mobile?.65:1),CAMK=rm?0:(mobile?.8:1);
  const now=()=>performance.now();
  const log=[];const note=o=>{log.push({t:Math.round(now()),...o});if(log.length>400)log.shift()};
  // 畫面工程師的 screen2（可能不存在）：ctx.screen2()、eng.screen2、或模組本身的具名匯出
  let s2mod=null;
  try{const m=import.meta.glob('./screen2.js');const ld=m['./screen2.js'];if(ld)ld().then(x=>{s2mod=x}).catch(()=>{})}catch(e){}
  const S2=()=>{try{return(ctx.screen2&&ctx.screen2())||eng.screen2||s2mod||null}catch(e){return null}};
  let flashes=[];
  const flash=(o)=>{const t=now();flashes=flashes.filter(x=>t-x<1000);if(flashes.length>=FLASH_MAX_PER_S)return;flashes.push(t);
    // §5.4：白閃 ≤ .15、紅閃 ≤ .3
    const cap=o.color===0xffffff?.15:o.red?.3:.25;const op=Math.min(cap,o.opacity==null?.12:o.opacity);
    try{S2()?.flash?.({color:o.color,opacity:op,dur:o.dur||.15})}catch(e){}};
  const chroma=(k,dur=.2)=>{if(rm)return;try{S2()?.pulseChromatic?.(k,dur)}catch(e){}};

  /* ---------- hitstop：取最大值、300 ms 內最多 2 次、連斬預算 ---------- */
  let stops=[],freezeEnd=0,combo={left:COMBO_BUDGET,perfect:false,active:false};
  function stop(ms,{chain=false}={}){if(!ms)return 0;const t=now();stops=stops.filter(x=>t-x<WIN_MS);
    if(chain&&combo.active){ms=Math.min(ms,combo.left);if(ms<=0)return 0}
    // 已經在頓格中：取最大值（只延長差額，不疊加）
    if(t<freezeEnd){const add=Math.max(0,t+ms-freezeEnd);if(!add)return 0;freezeEnd=t+ms;eng.hitStop(ms);if(chain&&combo.active)combo.left-=add;return add}
    if(stops.length>=WIN_MAX)return 0;
    stops.push(t);freezeEnd=t+ms;eng.hitStop(ms);if(chain&&combo.active)combo.left-=ms;return ms}

  /* ---------- 震屏：方向性（相機座標的 x/y）、手機限制疊加 ---------- */
  let lastShake=0;const tmpQ=new THREE.Quaternion(),tmpV=new THREE.Vector3();
  function shake([amp,dur,freq],k=1,dirWorld=null){let a=amp*k*SHK;if(a<=0)return;const t=now();
    if(mobile&&t-lastShake<120)a*=.6;lastShake=t;
    let dir=null;if(dirWorld){tmpQ.copy(camera.quaternion).invert();tmpV.copy(dirWorld).applyQuaternion(tmpQ);tmpV.z=0;if(tmpV.lengthSq()>1e-4){tmpV.normalize();dir=new THREE.Vector3(tmpV.x,tmpV.y*.5,0).multiplyScalar(1.4)}}
    eng.shake(a,dur,{freq,dir})}

  /* ---------- 慢動作：一般交給引擎；rm 時引擎不做，改用 eng.fast 自己做（不和跳過演出的快轉搶） ---------- */
  let rmSlow=null;
  function slow([k,ms]){if(!ms)return;if(!rm){eng.slowmo(k,ms);return}
    if(eng.fast&&eng.fast!==1&&!(rmSlow&&eng.fast===rmSlow.v))return;rmSlow={k,t0:now(),ms,v:k};eng.fast=k}
  eng.onUpdate(()=>{if(!rmSlow)return;if(eng.fast!==rmSlow.v){rmSlow=null;return} // 被跳過演出改掉了：放手
    const r=(now()-rmSlow.t0)/rmSlow.ms;if(r>=1){eng.fast=1;rmSlow=null;return}
    rmSlow.v=eng.fast=r<.65?rmSlow.k:lerp(rmSlow.k,1,ease.io((r-.65)/.35))},-50);

  /* ---------- 鏡頭衝擊層 ---------- */
  const punches=[];let fovApplied=0;
  const fwd=new THREE.Vector3(),rgt=new THREE.Vector3(),up=new THREE.Vector3(0,1,0),L=new THREE.Vector3(),off=new THREE.Vector3(),biasV=new THREE.Vector3();
  function punch(c,{k=1,dirWorld=null,hold=0}={}){if(!c||CAMK<=0)return null;
    const p={c,k:k*CAMK,t:0,dur:c.dur||.3,att:Math.min(.08,(c.dur||.3)*.25),hold:c.hold!=null?c.hold:hold,bias:0,held:false,rel:null};
    if(c.bias&&dirWorld){camera.getWorldDirection(fwd);rgt.crossVectors(fwd,up).normalize();p.bias=Math.sign(rgt.dot(dirWorld))*c.bias}
    punches.push(p);if(punches.length>6)punches.shift();return p}
  const envOf=p=>{const t=p.t;if(t<p.att)return ease.out(t/p.att);if(p.held)return 1;const t2=t-p.att-p.hold;if(t2<0)return 1;const rd=Math.max(.05,p.dur-p.att);return Math.max(0,1-ease.io(Math.min(1,t2/rd)))};
  eng.onUpdate(()=>{if(fovApplied){camera.fov-=fovApplied;fovApplied=0;camera.updateProjectionMatrix()}},99);
  eng.onUpdate((dt,rdt)=>{if(!punches.length)return;let push=0,side=0,fov=0,elev=0,lift=0,bias=0;
    for(let i=punches.length-1;i>=0;i--){const p=punches[i];p.t+=rdt;
      if(p.held&&p.rel!=null&&now()>p.rel){p.held=false;p.t=p.att+p.hold}
      const e=envOf(p)*p.k;if(!p.held&&p.t>p.att+p.hold+p.dur){punches.splice(i,1);continue}
      const c=p.c;push+=(c.push||0)*e;side+=(c.side||0)*e;fov+=(c.fov||0)*e;elev+=(c.elev||0)*e;lift+=(c.lift||0)*e;bias+=p.bias*e}
    camera.getWorldDirection(fwd);rgt.crossVectors(fwd,up).normalize();
    if(elev){const f=ctx.focus&&ctx.focus();const D=f?Math.max(2,camera.position.distanceTo(f)):6;L.copy(camera.position).addScaledVector(fwd,D);
      off.subVectors(camera.position,L).applyAxisAngle(rgt,-elev*Math.PI/180);camera.position.copy(L).add(off);camera.position.y+=lift;camera.lookAt(L)}
    else if(lift)camera.position.y+=lift;
    camera.position.addScaledVector(fwd,push).addScaledVector(rgt,side+bias);
    if(Math.abs(fov)>.01){fovApplied=fov;camera.fov+=fov;camera.updateProjectionMatrix()}},101);

  /* ---------- 預警壓迫（突襲、必殺、一般蓄力） ---------- */
  let pres=null;
  function pressure(kind="pressure",{dur=.7,maxMs=6000}={}){release();const c={...EXTRA[kind].cam,dur:.35};const p=punch(c,{hold:0});if(!p)return;
    p.att=Math.max(.1,dur);p.held=true;p.rel=now()+dur*1000+maxMs;pres=p;note({ev:"pressure",kind})}
  function release(){if(pres){pres.held=false;pres.t=pres.att;pres.hold=0;pres.rel=null;pres=null}}

  /* ---------- 共用：套用一個等級 ---------- */
  function apply(row,o={}){release();const k=o.k==null?1:o.k;
    const ms=o.noStop?0:stop(Math.round((o.stop!=null?o.stop:row.stop)||0),{chain:!!o.chain});
    if(row.shake)shake(row.shake,k,o.dir||null);
    if(row.rumble)eng.rumble(row.rumble[0]*SHK,row.rumble[1]);
    if(row.cam&&!o.noCam)punch(row.cam,{k:o.camK==null?1:o.camK,dirWorld:o.dir||null});
    const sl=o.slow===false?null:o.slow||(row.slow&&o.withSlow?row.slow:null);if(sl)slow(sl);
    note({ev:o.ev||"hit",lvl:o.lvl,stop:ms,slow:sl?sl.join("/"):null,chain:!!o.chain});return ms}
  const row=l=>FEEL[l]||EXTRA[l]||FEEL.S1;

  const api={
    table:FEEL,extra:EXTRA,log,
    // 直接用等級：feel.hit("S3",{dir, k, slow:true})
    hit(lvl,o={}){const r=row(lvl);return apply(r,{...o,lvl,withSlow:o.slow===true,slow:o.slow===true?undefined:o.slow})},
    // 連斬開始（skill 事件）：重置 450 ms 預算、記下是否完美
    combo(p){if(!p)return;if(p.move==="chain"||p.move==="gale"){combo={left:COMBO_BUDGET,perfect:!!p.perfect,active:true,fresh:true};note({ev:"combo",perfect:!!p.perfect,n:p.n||p.hitCount})}},
    // 主角命中 Boss：依招式、段數、輕重分級
    strike(p,{power=1,heavy=false,dir=null}={}){const i=p.index||0,n=p.total||p.n||1,multi=p.move==="chain"||p.move==="gale";
      // 第一刀：剛由 combo() 開好的就沿用（帶完美旗標），否則（弱點擊破的 gale、上一套中斷殘留）重新開一套
      if(multi&&i===0&&!combo.fresh)combo={left:COMBO_BUDGET,perfect:false,active:true};combo.fresh=false;
      let lvl,o={dir,ev:"strike"};
      if(p.kill){lvl="S5";o.withSlow=true}
      else if(p.move==="deflect")lvl="S1";
      else if(multi){lvl=p.last?"S3":i>=2?"S2":"S1";o.chain=true;if(p.last&&combo.perfect){o.withSlow=true}
        // 完美連斬的終結一刀：一點色差＋金色閃光
        if(p.last&&combo.perfect){chroma(.6,.22);flash({color:0xffd75a,opacity:.12,dur:.16})}}
      else lvl=heavy||power>=2?"S3":power<.9?"S1":"S2";
      if(lvl==="S5"){chroma(1,.35);flash({color:0xffffff,opacity:.15,dur:.2})}
      const ms=apply(row(lvl),{...o,lvl});
      if(multi&&p.last)combo.active=false;
      return ms},
    // 彈反：清脆頓格＋側移＋慢動作；金色節奏＝相擊一下、0.14 秒後再一個小拍（閃光＋輕震）
    parry({chain=false,dir=null}={}){const r=FEEL.S4;apply(r,{lvl:"S4",ev:"parry",dir,camK:.6,slow:chain?r.slowMid:r.slow}); // 場景本身也會把鏡頭往側邊帶（csTo side +.6），這裡只補 60%
      flash({color:0xffd75a,opacity:.2,dur:.12});chroma(.5,.16);
      setTimeout(()=>{if(eng.dead)return;shake([.03,.18,26]);flash({color:0xffd75a,opacity:.12,dur:.18})},140)},
    // 弱點擊破／突擊：S4，慢動作用中段版（後面緊接著主角連斬）
    breakFoe(ev="assault"){const r=FEEL.S4;flash({color:0xffd75a,opacity:.15,dur:.15});return apply(r,{lvl:"S4",ev,slow:r.slowMid})},
    // 格擋（Boss 打在劍上）
    guard(dir){return apply(FEEL.S1,{lvl:"S1",ev:"guard",dir})},
    dodge(){return apply(EXTRA.dodge,{lvl:"dodge",ev:"dodge"})},
    // 玩家受擊：guard→S1、graze/hit→S2、必殺／被打倒→S3＋紅暗角（暗角由場景的 fx.pulseVig 處理）；震屏方向＝Boss→主角
    hurt(p,dir=null){const heavy=p.danger||p.kind==="knockdown",lvl=p.kind==="guard"?"S1":heavy?"S3":"S2";
      if(heavy){chroma(.8,.3);flash({color:0xff2a1a,red:true,opacity:.22,dur:.22})}
      return apply(row(lvl),{lvl,ev:"hurt",dir,k:p.kind==="graze"?.85:1})},
    ambush(dir){chroma(.6,.25);return apply(EXTRA.ambush,{lvl:"ambush",ev:"ambush",dir})},
    pressure,release,
    // S0：腳步、Boss 落地（k＝距離／體型縮放）
    step(k=1){shake(FEEL.S0.shake,k)},
    loom(){shake(EXTRA.loom.shake)},
    land(){return apply(EXTRA.land,{lvl:"land",ev:"land"})},
    // Boss 倒下：開頭一小段慢放（倒下動作），化灰那一刻 S7
    fall(){release();slow([.5,350]);note({ev:"fall"})},
    die(){return apply(FEEL.S7,{lvl:"S7",ev:"die",withSlow:true})},
    // 階段轉換（給 phaseShow／bossPhase 用；感覺這邊不改 bossPhase）
    phase(){slow(FEEL.S6.pre);return apply(FEEL.S6,{lvl:"S6",ev:"phase"})},
  };
  if(typeof window!=="undefined"&&import.meta.env&&import.meta.env.DEV)window.__feel=api;
  return api;
}
