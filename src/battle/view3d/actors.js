// 角色：載入 GLB（public/models/<代號>.glb），載不到就用程式產生的替身；
// GLB 缺某個動作名稱時，改用同一套「程式補間動作」（PROC）。之後把模型檔補上，不必改程式就會換成真模型。
//
// 節點結構：root（世界位置與面向）→ pose（補間動作：衝刺、擠壓、倒下…）→ bob（待機呼吸／飛行漂浮）→ 內容（GLB 或替身）
// 模型約定：臉朝 +Z、原點在腳底。載入後會依 height 等比縮放。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';
import MODEL_FILES from 'virtual:model-list';
import { ease, lerp } from './engine.js';

/* ---------- 模型載入（同一場戰鬥內快取；清單由 vite.config.js 讀 public/models 產生，避免對不存在的檔案發請求） ---------- */
// 兩層快取：
//   MEM（記憶體）：已解析的 GLTF 原件，整個分頁生命週期共用；每場戰鬥用 SkeletonUtils.clone 複製一份來用（材質也另外複製，原件不會被改到）。
//   Cache Storage：GLB 原始檔。第二次進戰鬥不必重新下載，離線時也拿得到進過的模型。快取鍵帶「大小-修改時間」，模型換檔後自動失效。
// 已接上 Meshopt 解碼器；WebP 貼圖（EXT_texture_webp）GLTFLoader 本身就支援。之後換成壓縮過的 GLB 不必改程式。
const MEM=new Map(),VER=MODEL_FILES.ver||{},CACHE="vc-models-v1";
const gltfLoader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
// claude.ai Artifact 版不提供 .glb 檔型，建置時設 VITE_GLB_B64=1 會改抓 base64 文字檔（<名>.glb.b64.txt）再解回二進位
const B64=!!import.meta.env.VITE_GLB_B64;
function unB64(buf){const t=new TextDecoder().decode(buf).replace(/\s+/g,""),b=atob(t),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer}
async function fetchGLB(name,st){const url=import.meta.env.BASE_URL+"models/"+name+".glb"+(B64?".b64.txt":""),key=url+"?v="+(VER[name+".glb"]||"0");
  let cache=null;try{if(typeof caches!=="undefined")cache=await caches.open(CACHE)}catch(e){}
  if(cache){const hit=await cache.match(key).catch(()=>null);if(hit){st.cached=true;return hit.arrayBuffer()}}
  const res=await fetch(url);if(!res.ok)throw new Error("HTTP "+res.status);
  const total=+res.headers.get("content-length")||0;st.total=total;let buf;
  if(res.body&&total){const rd=res.body.getReader(),chunks=[];let n=0;for(;;){const{done,value}=await rd.read();if(done)break;chunks.push(value);n+=value.length;st.loaded=n}
    const u=new Uint8Array(n);let o=0;for(const c of chunks){u.set(c,o);o+=c.length}buf=u.buffer}
  else buf=await res.arrayBuffer();
  if(B64)buf=unB64(buf);
  if(cache){try{await cache.put(key,new Response(buf.slice(0),{headers:{"content-type":"model/gltf-binary"}}));
      for(const r of await cache.keys())if(r.url!==new URL(key,location.href).href&&r.url.split("?")[0].endsWith("/"+name+".glb"))cache.delete(r)}catch(e){}} // 清掉同一個檔的舊版本
  return buf}
function master(name,st){if(MEM.has(name)){st.done=true;return MEM.get(name)}
  const p=fetchGLB(name,st).then(buf=>new Promise((res,rej)=>gltfLoader.parse(buf,"",res,rej))).then(g=>{
      // 每個片段的時間平移到從 0 開始（匯出時多半從 0.033 秒起算，不處理的話循環會卡一格）；只需對原件做一次
      for(const clip of g.animations||[]){let t0=Infinity;for(const tr of clip.tracks)if(tr.times.length)t0=Math.min(t0,tr.times[0]);if(t0>1e-4&&t0<Infinity){for(const tr of clip.tracks)tr.shift(-t0);clip.resetDuration()}}
      return g})
    .catch(()=>{MEM.delete(name);return null}); // 失敗不留在快取裡，下一場再試
  MEM.set(name,p);return p}
// 從原件複製一份給這場戰鬥用（骨架、材質各自獨立；幾何與貼圖共用）
function instance(g){if(!g)return null;const scene=cloneSkinned(g.scene);
  scene.traverse(o=>{if(o.material)o.material=Array.isArray(o.material)?o.material.map(m=>m.clone()):o.material.clone()});return{scene,animations:g.animations}}
export function createLoader(){
  const prog=new Map();
  // warm：只確保原件已下載並解析（預載用）；load：再複製一份給呼叫者（每次呼叫都是新的一份）
  const warm=name=>{if(!name||!MODEL_FILES.includes(name+".glb"))return Promise.resolve(null);let st=prog.get(name);if(!st){st={loaded:0,total:0,done:false};prog.set(name,st)}
    return master(name,st).then(g=>{st.done=true;return g},()=>{st.done=true;return null})};
  const load=name=>warm(name).then(instance);load.warm=warm;
  // 指定幾個模型的整體下載進度（0–1）
  load.progress=names=>{let a=0,n=0;for(const k of names){if(!k||!MODEL_FILES.includes(k+".glb"))continue;const s=prog.get(k);n++;if(!s)continue;a+=s.done?1:s.total?Math.min(.99,s.loaded/s.total):0}return n?a/n:1};
  return load;
}

/* ---------- 卡通材質與描邊（打怪模式用） ---------- */
export function toonGradient(){const d=new Uint8Array([110,110,110,255,185,185,185,255,255,255,255,255]);const t=new THREE.DataTexture(d,3,1,THREE.RGBAFormat);t.minFilter=t.magFilter=THREE.NearestFilter;t.needsUpdate=true;return t}
function toonify(obj,grad){obj.traverse(o=>{if(!o.isMesh)return;const conv=m=>{if(m.isMeshToonMaterial||m.isMeshBasicMaterial||m.isMeshPhongMaterial)return m;
    // 史萊姆的膠體身體保留高光（Phong），其他都轉成卡通漸層
    if(/SlimeBody/.test(m.name)){const g=new THREE.MeshPhongMaterial({color:m.color.clone(),specular:0xffffff,shininess:70,transparent:m.transparent,opacity:m.opacity,side:m.side,name:m.name});g.emissive.copy(m.color).multiplyScalar(.16);m.dispose();return g}
    const t=new THREE.MeshToonMaterial({color:m.color?m.color.clone():0xffffff,map:m.map||null,gradientMap:grad,transparent:m.transparent,opacity:m.opacity,side:m.side,alphaTest:m.alphaTest||0,name:m.name});
    if(m.emissive){t.emissive.copy(m.emissive);t.emissiveIntensity=m.emissiveIntensity==null?1:m.emissiveIntensity;t.emissiveMap=m.emissiveMap||null}
    if(m.vertexColors)t.vertexColors=true;m.dispose();return t};
  o.material=Array.isArray(o.material)?o.material.map(conv):conv(o.material)})}
const outlineMat=th=>{const m=new THREE.MeshBasicMaterial({color:0x232038,side:THREE.BackSide});
  m.onBeforeCompile=s=>{s.vertexShader=s.vertexShader.replace("#include <begin_vertex>",`#include <begin_vertex>\ntransformed+=normalize(normal)*${th.toFixed(5)};`)};
  m.customProgramCacheKey=()=>"outline"+th.toFixed(5);m.userData.outline=true;return m};
// 反向外殼描邊：只描夠大的不透明部位（身體），小零件不描
// 不描邊的小零件（五官、頭髮尖刺、冰刺、寶石…）：尖刺用反向外殼會結成黑塊
const NO_OUTLINE=/Eye|Iris|Pupil|Shine|Blush|Mouth|Tongue|Fang|Glass|Ink|Hair|Spike|Gem|Stem|Leaf|Blade|Line/i;
function addOutline(obj,worldH,scale){const list=[];obj.traverse(o=>{if(!o.isMesh||o.userData.noOutline)return;const m=Array.isArray(o.material)?o.material[0]:o.material;if(!m||m.transparent||m.userData.outline||NO_OUTLINE.test(m.name||""))return;
    if(!o.geometry.boundingSphere)o.geometry.computeBoundingSphere();if(o.geometry.boundingSphere.radius*scale<worldH*.1)return;list.push(o)});
  for(const o of list){const mat=outlineMat(worldH*.012/scale);let c;
    if(o.isSkinnedMesh){c=new THREE.SkinnedMesh(o.geometry,mat);c.bind(o.skeleton,o.bindMatrix)}else c=new THREE.Mesh(o.geometry,mat);
    c.position.copy(o.position);c.quaternion.copy(o.quaternion);c.scale.copy(o.scale);c.userData.isOutline=true;c.frustumCulled=o.frustumCulled;o.parent.add(c)}}

/* ---------- 片段資訊 clipmeta.json（Blender 匯出時一起產生；檔案不存在時 glob 是空的，退回下面的 IMPACT 表） ----------
   接受的格式：{ "<模型代號>": { "<片段名>": { "dur": 秒, "hits": [秒,…], "steps": [秒,…] } } }，
   也接受外面多包一層 {models:{…}}、或模型底下多一層 {clips:{…}}；hits 也可以寫 hit（單一數字）。
   實際片長和 dur 不同（例如重新烘焙過）時，hits 依比例縮放。 */
const META_RAW=Object.values(import.meta.glob('./clipmeta.json',{eager:true,import:'default'}))[0]||null;
const META=(()=>{let m=META_RAW;if(!m||typeof m!=="object")return{};if(m.models&&typeof m.models==="object")m=m.models;const out={};
  for(const [model,v] of Object.entries(m)){if(!v||typeof v!=="object")continue;const clips=v.clips&&typeof v.clips==="object"?v.clips:v;out[model]={};
    for(const [clip,c] of Object.entries(clips)){if(!c||typeof c!=="object")continue;const hits=Array.isArray(c.hits)?c.hits.filter(x=>typeof x==="number"&&x>=0):typeof c.hit==="number"?[c.hit]:[];
      out[model][clip]={dur:typeof c.dur==="number"&&c.dur>0?c.dur:null,hits:hits.sort((a,b)=>a-b),steps:Array.isArray(c.steps)?c.steps.filter(x=>typeof x==="number"):null}}}
  return out})();
export const hasClipMeta=()=>Object.keys(META).length>0;
// 某模型某片段的命中秒數（已依實際片長縮放）；沒有資料回傳 null
function metaHits(model,clip,actual){const c=META[model]&&META[model][clip];if(!c||!c.hits.length)return null;const k=c.dur&&actual&&Math.abs(actual/c.dur-1)>.02?actual/c.dur:1;return c.hits.map(h=>Math.min(h*k,actual||h*k))}
function metaSteps(model,clip,actual){const c=META[model]&&META[model][clip];if(!c||!c.steps||!c.steps.length)return null;const k=c.dur&&actual?actual/c.dur:1;return c.steps.map(h=>h*k)}

/* ---------- 命中時間表（秒，從片段開頭算起；逐格量測的結果見 tests/playtest/art/data） ----------
   數字＝武器／身體實際打到對手的那一格；陣列＝連段各擊；{f}＝片長比例。查不到才用片長的 45%。 */
const IMPACT={
  hero_cute:{Slash:.47,Combo:[.22,.48,1.0]},
  hero_knight:{Slash:.5,HeavySlash:.8,Combo:[.37,.67,1.08]},
  boss_sentinel:{Attack:.27,Attack2:.83,PhaseShift:{f:.3}},
  boss_gargoyle:{Attack:.3,Attack2:.92,PhaseShift:{f:.3}},
  boss_priest:{Attack:.38,Attack2:.45,PhaseShift:{f:.3}},
  boss_executioner:{Attack:.31,Attack2:.68,PhaseShift:{f:.3}}, // 第二輪實測：傷害數字比斧刃碰到主角晚 60–80ms，各提前 0.07 秒
  boss_devourer:{Attack:.42,Attack2:.6,PhaseShift:{f:.3}},
};
// 怪物攻擊片段自帶的前衝距離（身高的倍數）：場景移動怪物時要扣掉，才不會衝過頭
export const LUNGE={slime:1.57,bat:2.08};

/* ---------- 程式補間動作 ----------
   每個動作：{dur 總長, impact 命中時間點, hold 播完停在最後姿勢, run(a, T) }；T(obj, props, 秒, easing) 是補間。
   只動 pose（整體）與替身的零件（a.parts，可能不存在），所以真模型缺動作時也能套用。 */
const PI=Math.PI;
const arm=(a,T,x,d,ez)=>a.parts.armR?T(a.parts.armR.rotation,{x},d,ez):null;
const armL=(a,T,x,d,ez)=>a.parts.armL?T(a.parts.armL.rotation,{x},d,ez):null;
const PROC={
  Enter:{dur:.8,run:async(a,T)=>{const P=a.pose;
    if(a.cute){P.scale.set(.01,.01,.01);P.position.y=a.h*1.6;T(P.position,{y:0},.38,ease.in);await T(P.scale,{x:1,y:1,z:1},.38,ease.out);
      await T(P.scale,{x:1.3,y:.65,z:1.3},.09,ease.out);await T(P.scale,{x:1,y:1,z:1},.33,ease.elastic)}
    else{P.scale.set(.96,.9,.96);P.rotation.x=.25;T(P.rotation,{x:0},.8,ease.out);await T(P.scale,{x:1,y:1,z:1},.8,ease.out)}}},
  Attack:{dur:.78,impact:.4,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.scale,{x:1.12,y:.86,z:1.12},.26,ease.out);T(P.rotation,{x:-.22},.26,ease.out);arm(a,T,-2.5,.26,ease.out);await T(P.position,{z:-.22*h},.26,ease.out);
    T(P.scale,{x:.9,y:1.14,z:.9},.14,ease.out);T(P.rotation,{x:.38},.14,ease.in);arm(a,T,.7,.14,ease.in);await T(P.position,{z:.55*h},.14,ease.in);
    T(P.scale,{x:1,y:1,z:1},.38,ease.elastic);T(P.rotation,{x:0},.3,ease.out);arm(a,T,a.rest.armR,.3,ease.io);await T(P.position,{z:0},.38,ease.out)}},
  Attack2:{dur:.95,impact:.52,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{y:-1.1},.34,ease.out);arm(a,T,-1.6,.34,ease.out);await T(P.position,{y:.12*h,z:-.15*h},.34,ease.out);
    T(P.rotation,{y:PI*2+.5},.24,ease.in);arm(a,T,.4,.2,ease.in);await T(P.position,{y:0,z:.4*h},.24,ease.in);
    P.rotation.y-=PI*2;T(P.rotation,{y:0},.36,ease.out);arm(a,T,a.rest.armR,.3,ease.io);await T(P.position,{z:0},.36,ease.out)}},
  Slash:{dur:.48,impact:.22,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{y:-.55,x:-.08},.14,ease.out);arm(a,T,-2.4,.14,ease.out);await T(P.position,{z:-.06*h},.14,ease.out);
    T(P.rotation,{y:.65,x:.2},.1,ease.in);arm(a,T,.9,.1,ease.in);await T(P.position,{z:.16*h},.1,ease.in);
    T(P.rotation,{y:0,x:0},.24,ease.out);arm(a,T,a.rest.armR,.24,ease.io);await T(P.position,{z:0},.24,ease.out)}},
  HeavySlash:{dur:.82,impact:.46,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:-.34},.32,ease.out);arm(a,T,-3,.32,ease.out);await T(P.position,{y:.1*h,z:-.1*h},.32,ease.out);
    T(P.rotation,{x:.5},.14,ease.in);arm(a,T,1.1,.14,ease.in);await T(P.position,{y:0,z:.28*h},.14,ease.in);
    T(P.rotation,{x:0},.36,ease.out);arm(a,T,a.rest.armR,.36,ease.io);await T(P.position,{z:0},.36,ease.out)}},
  Combo:{dur:.9,impact:.2,run:async(a,T)=>{const P=a.pose;
    for(let i=0;i<3;i++){const s=i%2?-1:1;T(P.rotation,{y:-.6*s},.1,ease.out);arm(a,T,-2.2,.1,ease.out);await a.eng.wait(.1);T(P.rotation,{y:.7*s},.1,ease.in);arm(a,T,.9,.1,ease.in);await a.eng.wait(.16)}
    arm(a,T,a.rest.armR,.12,ease.io);await T(P.rotation,{y:0},.12,ease.out)}},
  Cast:{dur:.75,impact:.5,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:-.16},.3,ease.out);arm(a,T,-2.9,.3,ease.out);armL(a,T,-1.2,.3,ease.out);await T(P.position,{y:.12*h},.3,ease.out);await a.eng.wait(.2);
    T(P.rotation,{x:0},.25,ease.io);arm(a,T,a.rest.armR,.25,ease.io);armL(a,T,a.rest.armL,.25,ease.io);await T(P.position,{y:0},.25,ease.in)}},
  Hit:{dur:.38,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.scale,{x:1.14,y:.84,z:1.14},.07,ease.out);T(P.rotation,{x:-.32},.07,ease.out);await T(P.position,{z:-.24*h},.07,ease.out);
    T(P.scale,{x:1,y:1,z:1},.3,ease.elastic);T(P.rotation,{x:0},.3,ease.out);await T(P.position,{z:0},.3,ease.out)}},
  Stagger:{dur:.9,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:-.4,z:.14},.12,ease.out);await T(P.position,{z:-.4*h},.12,ease.out);
    T(P.rotation,{x:.3,z:-.06},.22,ease.io);await T(P.position,{y:-.1*h},.22,ease.io);await a.eng.wait(.22);
    T(P.rotation,{x:0,z:0},.34,ease.io);await T(P.position,{y:0,z:0},.34,ease.io)}},
  Faint:{dur:1,hold:true,run:async(a,T)=>{const P=a.pose,h=a.h;
    if(a.cute){T(P.rotation,{y:PI*2},.5,ease.out);await T(P.position,{y:.35*h},.22,ease.out);await T(P.position,{y:0},.24,ease.in);
      T(P.scale,{x:1.35,y:.32,z:1.35},.16,ease.out);await a.eng.wait(.16);await T(P.scale,{x:1.2,y:.45,z:1.2},.3,ease.elastic)}
    else{T(P.rotation,{x:.2},.3,ease.out);await T(P.position,{y:-.12*h},.3,ease.out);T(P.rotation,{x:-1.45},.5,ease.in);await T(P.position,{y:.1*h,z:-.3*h},.5,ease.in);await a.eng.wait(.2)}}},
  Victory:{dur:1.1,run:async(a,T)=>{const P=a.pose,h=a.h;arm(a,T,-2.9,.2,ease.out);
    for(let i=0;i<2;i++){if(a.cute&&i===0)T(P.rotation,{y:PI*2},.5,ease.io);await T(P.position,{y:.3*h},.2,ease.out);await T(P.position,{y:0},.2,ease.in);T(P.scale,{x:1.1,y:.9,z:1.1},.05);await a.eng.wait(.05);await T(P.scale,{x:1,y:1,z:1},.08)}
    P.rotation.y=0;await a.eng.wait(.1)}},
  Roll:{dur:.55,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.scale,{y:.62},.1,ease.out);T(P.position,{y:.12*h},.1,ease.out);await T(P.rotation,{x:PI*2},.45,ease.io);P.rotation.x=0;T(P.position,{y:0},.1,ease.in);await T(P.scale,{y:1},.1,ease.out)}},
  Parry:{dur:.4,impact:.12,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{y:.7,x:-.1},.1,ease.out);arm(a,T,-1.9,.1,ease.out);armL(a,T,-1.5,.1,ease.out);await T(P.position,{z:.12*h},.1,ease.out);await a.eng.wait(.1);
    T(P.rotation,{y:0,x:0},.2,ease.io);arm(a,T,a.rest.armR,.2,ease.io);armL(a,T,a.rest.armL,.2,ease.io);await T(P.position,{z:0},.2,ease.io)}},
  Guard:{dur:.6,impact:.14,run:async(a,T)=>{const P=a.pose,h=a.h;
    T(P.rotation,{x:.18},.12,ease.out);armL(a,T,-1.5,.12,ease.out);arm(a,T,-1.1,.12,ease.out);await T(P.position,{y:-.07*h},.12,ease.out);await a.eng.wait(.26);
    T(P.rotation,{x:0},.2,ease.io);armL(a,T,a.rest.armL,.2,ease.io);arm(a,T,a.rest.armR,.2,ease.io);await T(P.position,{y:0},.2,ease.io)}},
  Telegraph:{dur:.8,hold:true,run:async(a,T)=>{const P=a.pose,h=a.h;a.tremble=.012*h;
    T(P.rotation,{x:-.26},.6,ease.out);T(P.scale,{x:1.06,y:1.08,z:1.06},.6,ease.out);arm(a,T,-2.7,.6,ease.out);await T(P.position,{y:.05*h,z:-.12*h},.6,ease.out);await a.eng.wait(.2)}},
  PhaseShift:{dur:1.3,run:async(a,T)=>{const P=a.pose,h=a.h;a.tremble=.02*h;
    T(P.rotation,{x:.35},.5,ease.out);await T(P.scale,{x:.92,y:.86,z:.92},.5,ease.out);a.tremble=0;
    T(P.rotation,{x:-.3},.14,ease.out);arm(a,T,-2.8,.14,ease.out);armL(a,T,-2.8,.14,ease.out);await T(P.scale,{x:1.18,y:1.2,z:1.18},.14,ease.out);await a.eng.wait(.3);
    T(P.rotation,{x:0},.36,ease.io);arm(a,T,a.rest.armR,.36,ease.io);armL(a,T,a.rest.armL,.36,ease.io);await T(P.scale,{x:1,y:1,z:1},.36,ease.io)}},
};
PROC.Die=PROC.Faint;
// 循環動作：值＝沒有片段時用的程式擺動（stalk＝巨獸踏步，比 walk 慢、沉）
const LOOPS={Idle:"idle",IdleAggro:"idle",Walk:"walk",Run:"run",Stalk:"stalk",StrafeL:"strafeL",StrafeR:"strafeR"};
// 片段不存在時依序找替代（同事的新片段之後才會到；沒有就退回現有片段＋位移）
const FALLBACK={IdleAggro:["Idle"],Stalk:["Walk"],StrafeL:["Walk"],StrafeR:["Walk"],Delayed:["Attack2","Attack"],Dash:["Attack"],Combo3:[],Roar:[]};
// 這些片段播放時開武器拖尾
const SWING=/^(Slash|HeavySlash|Combo|Combo3|Attack|Attack2|Delayed|Dash)$/;
// 交叉淡入淡出。three.js 的 crossFadeFrom 會讓「被淡出的片段」從權重 1 開始淡出——如果它自己還在淡入中（例如剛切到待機又馬上出招），
// 那一格權重會突然跳到 1，畫面就跳一下。這裡改成從它「目前的權重」開始淡出。
function xfade(from,to,d){if(!from||from===to){to.stopFading();to.setEffectiveWeight(1);return}
  const w0=from.getEffectiveWeight();from.stopFading();from._scheduleFading(d,w0,0);to.stopFading();to._scheduleFading(d,0,1)}
// 交叉淡入淡出（秒）：攻擊／受擊進場要短（反應快），回到待機與循環動作要長（不硬切）
const FADE_IN=.12,FADE_LOOP=.35,FADE_IDLE=.3;

export class Actor{
  // o: {model 代號, height 目標身高（公尺）, standin: ()=>({group, parts, height}), cute, fly 飛行高度, shadow 陰影半徑, toon 漸層貼圖, outline, castShadow}
  constructor(eng,fx,o){this.eng=eng;this.fx=fx;this.o=o;this.h=o.height;this.cute=!!o.cute;this.name=o.model;
    this.root=new THREE.Group();this.pose=new THREE.Group();this.bob=new THREE.Group();this.root.add(this.pose);this.pose.add(this.bob);
    this.parts={};this.rest={armR:0,armL:0};this.actions={};this.mixer=null;this.curAct=null;this.seq=0;this.bobMode="idle";this.bobT=Math.random()*9;this.tremble=0;
    this.mats=[];this.flashK=0;this.flashC=new THREE.Color(0xffffff);this.glowK=0;this.glowC=new THREE.Color(0xff2a1a);this._tint=false;this.opacity=1;
    this.kn={z:0,vz:0,r:0,vr:0};this.alt={};this.bobRate=1;this.onStep=null;this._stepS=0;this.trail=null;this.trailColor=o.trail||0xdfe8ff;
    this.shadow=fx.blob(o.shadow||o.height*.42,o.cute?.55:.75);eng.scene.add(this.shadow);eng.scene.add(this.root);
    this._setContent(o.standin(),true);
    this._off=eng.onUpdate((dt,rdt,time)=>this._update(dt,time),0);
    this.ready=o.load?o.load(o.model).then(g=>{if(g&&!eng.dead&&!this.gone)this._setGLB(g);return this}):Promise.resolve(this)}

  _setContent(c,isStandin){if(this.content){this.bob.remove(this.content);this.eng.disposeObject(this.content)}
    this.content=c.group;this.parts=isStandin?(c.parts||{}):{};this.isStandin=isStandin;
    this.rest={armR:this.parts.armR?this.parts.armR.rotation.x:0,armL:this.parts.armL?this.parts.armL.rotation.x:0};
    if(isStandin){const s=this.h/(c.height||1);c.group.scale.setScalar(s)}
    this.bob.add(c.group);
    if(this.o.toon)toonify(c.group,this.o.toon);
    if(this.o.outline){addOutline(c.group,this.h,c.group.scale.x);if(this.eng.quality==="low")this.setOutline(false)}
    this.mats=[];c.group.traverse(m=>{if(!m.isMesh)return;if(this.o.castShadow&&!m.userData.isOutline)m.castShadow=true;
      for(const mt of Array.isArray(m.material)?m.material:[m.material]){if(mt.userData.outline||this.mats.find(x=>x.m===mt))continue;this.mats.push({m:mt,e0:mt.emissive?mt.emissive.clone():null,o0:mt.opacity,t0:mt.transparent,glow:/Glow/i.test(mt.name||"")||!!mt.emissiveMap||(isStandin&&mt.emissive&&mt.emissiveIntensity>1.5)})}});
    this._tint=true}
  _setGLB(g){const sc=g.scene;sc.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(sc),hh=Math.max(.001,box.max.y-box.min.y),s=this.h/hh;
    // 飛行怪（keepOrigin）保留模型原點：模型本來就懸在空中，不要用包圍盒壓到地面
    sc.scale.multiplyScalar(s);if(this.o.keepOrigin)this.baseY=box.min.y*s;else{sc.position.y-=box.min.y*s;this.baseY=0}
    sc.traverse(o=>{if(o.isSkinnedMesh)o.frustumCulled=false});
    this._setContent({group:sc},false);
    this.eng.container.dataset.glb=(+this.eng.container.dataset.glb||0)+1; // 已換上真模型的角色數（檢查用）
    // 測試用：window.__v3dropClips＝要假裝不存在的片段名（驗證「片段不存在就退回」的路徑）
    const drop=typeof window!=="undefined"&&Array.isArray(window.__v3dropClips)?window.__v3dropClips:null;
    const clips=(g.animations||[]).filter(c=>!drop||!drop.includes(c.name));
    this.loco=locoOf(this.name,sc,clips);
    this.mixer=new THREE.AnimationMixer(sc);this.actions={};this.alt={};for(const clip of clips)this.actions[clip.name]=this.mixer.clipAction(clip);
    if(this.o.trail&&!this.eng.dead){if(this.trail)this.trail.dispose();this.trail=makeTrail(this,sc)}
    // 換上真模型後接續目前的循環動作
    this.curAct=null;const loop=this._loopName||"Idle";if(this.actions[loop]){this.curAct=this.actions[loop];this.curAct.play()}else if(this.actions.Idle){this.curAct=this.actions.Idle;this.curAct.play()}
    this.bobMode=this.actions[loop]?"none":(LOOPS[loop]||"idle")}

  has(name){return !!this.actions[name]}
  // 實際會播的片段名：有就用自己，沒有就找替代（FALLBACK），都沒有回傳原名（交給程式補間／循環擺動）
  clipName(name){if(this.actions[name])return name;for(const f of FALLBACK[name]||[])if(this.actions[f])return f;return name}
  // 命中時間點（秒）：clipmeta.json → IMPACT 表 → 片長的 45%；補間動作用表定值
  impactTime(name,speed=1){name=this.clipName(name);const a=this.actions[name];
    if(a){const d=a.getClip().duration,mh=metaHits(this.name,name,d);if(mh)return mh[0]/speed;const v=(IMPACT[this.name]||{})[name];const t=v==null?d*.45:Array.isArray(v)?v[0]:typeof v==="object"?d*v.f:v;return Math.min(t,d)/speed}
    const p=PROC[name];return p?(p.impact==null?p.dur*.5:p.impact)/speed:.2}
  // 片段裡所有命中時間（秒，未除速度）：clipmeta → IMPACT 陣列 → null
  hitTimes(name){name=this.clipName(name);const a=this.actions[name];if(!a)return null;const d=a.getClip().duration,mh=metaHits(this.name,name,d);if(mh)return mh;const v=(IMPACT[this.name]||{})[name];return Array.isArray(v)?v.slice():null}
  // 連段各擊的命中時間（秒）。clipmeta／IMPACT 表；都沒有就平均分布
  comboTimes(name="Combo",n=3){const h=this.hitTimes(name);if(h&&h.length)return h;const d=this.duration(name);return Array.from({length:n},(_,i)=>d*(.22+.56*i/Math.max(1,n-1)))}
  // 走路類片段原速播放時，身體應有的移動速度（m/s，從支撐腳往後滑的速度量出來）。位移速度＝這個值×播放速度，腳才不會滑步。沒有片段回傳 0
  locoSpeed(name){const n=this.clipName(name),v=this.loco&&this.loco[n];return v?v:0}
  duration(name,speed=1){name=this.clipName(name);const a=this.actions[name];if(a)return a.getClip().duration/speed;const p=PROC[name];return p?p.dur/speed:.3}

  // soft：補間動作留下的姿勢（前傾、縮放）用 0.15 秒滑回原位，不在換片段的那一格瞬間跳回
  resetPose(soft=false){const E=this.eng,P=this.pose;E.kill(P.position);E.kill(P.rotation);E.kill(P.scale);this.tremble=0;
    const off=P.position.lengthSq()+P.rotation.x*P.rotation.x+P.rotation.y*P.rotation.y+P.rotation.z*P.rotation.z+Math.abs(P.scale.x-1)+Math.abs(P.scale.y-1);
    if(soft&&off>1e-5&&!E.rm){P.rotation.y=Math.atan2(Math.sin(P.rotation.y),Math.cos(P.rotation.y));E.to(P.position,{x:0,y:0,z:0},.15,ease.out);E.to(P.rotation,{x:0,y:0,z:0},.15,ease.out);E.to(P.scale,{x:1,y:1,z:1},.15,ease.out)}
    else{P.position.set(0,0,0);P.rotation.set(0,0,0);P.scale.set(1,1,1)}
    for(const k of ["armR","armL"])if(this.parts[k]){E.kill(this.parts[k].rotation);this.parts[k].rotation.x=this.rest[k]}}
  // 同一個片段連續播（例如兩次 Attack）：沒辦法自己淡入自己，改用一份複本交替，前一次的收招和下一次的起手才接得起來
  // 還在淡出中的同一個片段也一樣（例如 Stalk→Idle 才淡到一半又切回 Stalk）：拿它重來會讓它的權重瞬間歸零，改用複本、讓舊的那份自己淡完
  _act(name){const a=this.actions[name];if(!a)return a;const busy=x=>x===this.curAct||(x.isRunning()&&x.getEffectiveWeight()>.01);if(!busy(a))return a;
    let b=this.alt[name];if(!b){const c=a.getClip().clone();b=this.mixer.clipAction(c)}
    if(busy(b)&&b.getEffectiveWeight()>a.getEffectiveWeight()&&a!==this.curAct)return a; // 兩份都在用：拿權重比較小的那份
    this.alt[name]=a;this.actions[name]=b;return b}

  // 播放動作。循環動作（Idle／Walk／Run）立刻 resolve；單次動作播完才 resolve，並自動回到待機（hold 例外）。
  // fade：不指定就依種類決定（單次動作 0.08 秒、循環／回待機 0.3–0.35 秒）
  play(name,{speed=1,hold=false,fade=null}={}){if(this.eng.dead||this.gone)return Promise.resolve();const tok=++this.seq,loop=name in LOOPS,want=name;
    if(loop)this._loopName=name;
    name=this.clipName(name);
    const fd=fade!=null?fade:loop?(name==="Idle"||name==="IdleAggro"?FADE_IDLE:FADE_LOOP):FADE_IN;
    if(loop&&this.actions[name]&&this.curAct===this.actions[name]&&this.curAct.isRunning()&&this.curAct.getEffectiveWeight()>.5){this.curAct.timeScale=speed;this.bobMode="none";this.resetPose(true);return Promise.resolve()} // 已經在播同一個循環：不重來
    const act=this.actions[name]&&this._act(name);
    if(act){this.resetPose(true);act.reset();act.setLoop(loop?THREE.LoopRepeat:THREE.LoopOnce,Infinity);act.clampWhenFinished=true;act.timeScale=speed;act.setEffectiveWeight(1);
      if(this.curAct&&this.curAct!==act){xfade(this.curAct,act,fd)}act.play();this.curAct=act;this.bobMode="none";
      if(SWING.test(name)){if(this.trail)this.trail.on(act.getClip().duration/speed*.8);if(this.onSwing)this.onSwing(name,speed)}
      if(loop)return Promise.resolve();
      return this.eng.wait(act.getClip().duration/speed).then(()=>{if(tok===this.seq&&!hold&&!PROC[want]?.hold&&!PROC[name]?.hold)this.idle()})}
    // 沒有這個動作片段 → 程式補間（真模型則讓待機片段繼續在底下播）
    const base=this.mixer?this.actions[this.clipName(this._loopName==="IdleAggro"?"IdleAggro":"Idle")]:null;
    if(loop){this.resetPose(true);this.bobMode=LOOPS[want];if(base&&this.curAct!==base){const b=this._act(this.clipName("Idle"));b.reset();b.setEffectiveWeight(1);this.curAct&&xfade(this.curAct,b,fd);b.play();this.curAct=b}
      if(base)this.bobMode=(want==="Idle"||want==="IdleAggro")?"none":LOOPS[want];return Promise.resolve()}
    const p=PROC[name];if(!p)return this.eng.wait(.3);
    this.resetPose();if(base&&this.curAct!==base){const b=this._act(this.clipName("Idle"));b.reset();b.setEffectiveWeight(1);this.curAct&&xfade(this.curAct,b,FADE_IDLE);b.play();this.curAct=b}
    this.bobMode=base?"none":"still";
    const T=(obj,props,d,ez)=>this.eng.to(obj,props,d/speed,ez);
    return p.run(this,T).then(()=>{if(tok!==this.seq)return;if(hold||p.hold)return;this.idle()})}
  idle(){return this.play(this._loopName||"Idle")}
  // 分段播放（例如三連擊的每一段各配一題）：從 t0 秒播到 t1 秒，之後幾乎停住（極慢地往前飄，不是死格），
  // 下一段 t0 傳 null 就從目前位置接著播。片段不存在回傳 null。
  playSeg(name,t0,t1,speed=1){const a0=this.actions[name];if(!a0||this.eng.dead||this.gone)return null;const tok=++this.seq;let a=a0;
    if(this.curAct!==a||t0!=null){if(this.curAct!==a||t0===0){a=this._act(name);this.resetPose(true);a.reset();a.setLoop(THREE.LoopOnce,Infinity);a.clampWhenFinished=true;a.setEffectiveWeight(1);if(this.curAct&&this.curAct!==a)xfade(this.curAct,a,FADE_IN);a.play();this.curAct=a;this.bobMode="none"}
      if(t0!=null)a.time=t0}
    a.paused=false;a.timeScale=speed;const from=a.time;if(this.trail)this.trail.on(Math.max(.1,(t1-from)/speed+.12));
    return this.eng.wait(Math.max(0,(t1-from)/speed)).then(()=>{if(tok===this.seq&&this.curAct===a)a.timeScale=.04;return tok===this.seq})}
  // 把目前片段放慢到幾乎停住（延遲攻擊的「舉著武器停住」）
  freeze(k=.03){if(this.curAct)this.curAct.timeScale=k}
  // 受擊位移與後仰（彈簧：先被推開，再回到原位，帶一點過衝）。dist：公尺（往自己背後）、lean：弧度（後仰）
  // 不是瞬間給速度（會在一格內跳一大段），而是把「目標偏移」推出去再讓它衰減，彈簧追著目標走：約 60ms 內推到、再帶點過衝回原位
  knock(dist=.2,lean=.15){if(this.eng.rm){dist*=.4;lean*=.4}const k=this.kn;k.tz=(k.tz||0)+dist;k.tr=(k.tr||0)+lean}
  // 設定「單次動作播完後要回到哪個循環動作」，不立刻切換
  setLoop(name){this._loopName=name}

  /* ---------- 閃白／發光／透明度 ---------- */
  flash(color=0xffffff,k=1){this.flashC.set(color);this.flashK=k;this._tint=true}
  glow(color,k){if(color!=null)this.glowC.set(color);this.glowK=k;this._tint=true}
  // 低畫質：描邊整個關掉（每個部位少畫一次、少算一次蒙皮）
  setOutline(on){this.content.traverse(o=>{if(o.userData.isOutline)o.visible=on&&this.opacity>.9})}
  setOpacity(v){this.opacity=v;for(const x of this.mats){x.m.transparent=v<1?true:x.t0;x.m.opacity=x.o0*v}const ol=this.eng.quality!=="low";this.content.traverse(o=>{if(o.userData.isOutline)o.visible=ol&&v>.9});this.shadow.material.opacity=(this.cute?.55:.75)*v}

  _update(dt,time){if(this.mixer)this.mixer.update(dt);
    // 待機／走路／飛行的程式擺動
    this.bobT+=dt;const t=this.bobT,b=this.bob,h=this.h,fly=this.isStandin?(this.o.fly||0):0,P=this.parts;
    let y=fly,sy=1,rz=0,rx=0,sw=0;
    if(this.bobMode==="idle"){if(fly)y+=Math.sin(t*2.4)*.07*h;else sy=1+Math.sin(t*(this.cute?3.2:1.8))*(this.cute?.035:.012)}
    else if(this.bobMode==="walk"){y+=Math.abs(Math.sin(t*5.5))*.035*h;rz=Math.sin(t*5.5)*.035;sw=Math.sin(t*5.5)*.55}
    // 巨獸踏步（Boss 沒有走路片段時）：慢而沉，落腳時往下頓一下；橫移時身體往移動方向傾
    else if(this.bobMode==="stalk"||this.bobMode==="strafeL"||this.bobMode==="strafeR"){const f=2.7*this.bobRate,s=Math.sin(t*f),c=Math.abs(s);
      y+=-(1-c)*(1-c)*.022*h+c*.012*h;rx=.05;rz=this.bobMode==="stalk"?s*.022:(this.bobMode==="strafeL"?.05:-.05)+s*.012;sw=s*.45;
      const side=s>=0?1:-1;if(side!==this._stepS){this._stepS=side;this.onStep&&this.onStep(side)}}
    else if(this.bobMode==="run"){y+=Math.abs(Math.sin(t*10))*(this.cute?.14:.05)*h;rx=.22;sw=Math.sin(t*10)*.9}
    else if(this.bobMode==="still"&&fly)y+=0;
    // 受擊彈簧（ω≈14、阻尼比 0.5：被推開後帶一點過衝回到原位）
    {const K=this.kn,w=20,z=.55,d=Math.min(dt,.033),dec=Math.exp(-d/.09);K.tz=(K.tz||0)*dec;K.tr=(K.tr||0)*dec;
      K.vz+=(w*w*(K.tz-K.z)-2*z*w*K.vz)*d;K.z+=K.vz*d;K.vr+=(w*w*(K.tr-K.r)-2*z*w*K.vr)*d;K.r+=K.vr*d}
    // 有走路片段時，落腳由片段時間決定（clipmeta 的 steps，沒有就用片長的 0 與 1/2）
    if(this.bobMode==="none"&&this.onStep&&this.curAct&&/^(Walk|Stalk|StrafeL|StrafeR)/.test(this.curAct.getClip().name)&&this.curAct.getEffectiveWeight()>.5){const cl=this.curAct.getClip(),d=cl.duration,st=metaSteps(this.name,cl.name,d)||[0,d/2];
      const tt=this.curAct.time%d;let idx=-1;for(let i=0;i<st.length;i++)if(tt>=st[i])idx=i;if(idx!==this._stepI){this._stepI=idx;if(idx>=0)this.onStep(idx%2?1:-1)}}
    b.position.y=y;b.position.z=-this.kn.z;b.scale.set(1/Math.sqrt(sy),sy,1/Math.sqrt(sy));b.rotation.set(rx-this.kn.r,0,rz);
    if(this.tremble)b.position.x=(Math.random()-.5)*this.tremble*2;else b.position.x=0;
    if(P.legL){P.legL.rotation.x=sw;P.legR.rotation.x=-sw}
    if(P.wingL){const slow=P.wingL.userData.flap,f=slow?Math.sin(t*1.7)*slow:Math.sin(t*(this.bobMode==="still"?22:13))*.55;P.wingL.rotation.z=f;P.wingR.rotation.z=-f}
    if(P.cape)P.cape.rotation.x=(P.cape.userData.rx||0)+Math.sin(t*2.2)*.06+(this.bobMode==="run"?.5:this.bobMode==="walk"?.15:0);
    // 閃白衰減、發光（發光量除以材質的發光強度，避免本來就會發光的材質整個過曝）
    if(this.flashK>0){this.flashK=Math.max(0,this.flashK-dt*5.5);this._tint=true}
    if(this.glowK!==this._g0){this._g0=this.glowK;this._tint=true}
    if(this._tint){this._tint=this.flashK>0;const soft=this.o.soft,fk=soft?Math.min(1,this.flashK)*.008:Math.min(1,this.flashK); // 暗場景裡 3% 的白色自發光就足以把整隻洗成灰白，所以只留 0.8%，主要靠輪廓光脈衝 // 魂系場景很暗，自發光只要一點點就很亮
      for(const x of this.mats){if(!x.e0)continue;x.m.emissive.copy(x.e0);
        if(this.glowK>0){
          if(soft){ // 魂系：只讓「本來就會發光」的部位（眼睛、裂縫）換色變亮，身體只帶一點點色
            if(x.glow)x.m.emissive.lerp(this.glowC,Math.min(1,this.glowK));
            else{const g=this.glowK*.006;x.m.emissive.r+=this.glowC.r*g;x.m.emissive.g+=this.glowC.g*g;x.m.emissive.b+=this.glowC.b*g}}
          else{const g=this.glowK*.25/Math.max(1,x.m.emissiveIntensity||1);x.m.emissive.r+=this.glowC.r*g;x.m.emissive.g+=this.glowC.g*g;x.m.emissive.b+=this.glowC.b*g}}
        if(fk>0)x.m.emissive.lerp(this.flashC,fk/(soft?Math.max(1,x.m.emissiveIntensity||1):1))}}
    // 假陰影跟著腳下，跳高時縮小
    const r=this.root,s=this.shadow;s.position.x=r.position.x;s.position.z=r.position.z;s.visible=r.visible;
    const lift=Math.max(0,r.position.y+this.pose.position.y+y),k=(this.o.shadow||h*.42)*2*Math.max(.35,1-lift/(h*2.5))*((this.pose.scale.x+1)/2);s.scale.setScalar(k);
    if(this.trail)this.trail.update(dt)}

  // 面向某個世界座標（只轉 Y 軸）
  face(p){this.root.rotation.y=Math.atan2(p.x-this.root.position.x,p.z-this.root.position.z)}
  // 身體中心的世界座標（特效用）
  center(out=new THREE.Vector3(),k=.5){return out.set(this.root.position.x,this.root.position.y+this.pose.position.y+(this.isStandin?(this.o.fly||0):(this.baseY||0))+this.h*k,this.root.position.z)}
  remove(){this.gone=true;this._off();if(this.trail){this.trail.dispose();this.trail=null}this.eng.scene.remove(this.root);this.eng.scene.remove(this.shadow);this.shadow.material.dispose();if(this.mixer){this.mixer.stopAllAction();this.mixer.uncacheRoot(this.content)}this.eng.disposeObject(this.root)}
}
/* ---------- 走路片段的步速（載入時量一次，依模型快取） ----------
   用一個暫時的 mixer 把 Stalk／StrafeL／StrafeR／Walk／Run 各取 30 格，找比較低的那隻腳（支撐腳），算它在模型座標裡往後滑的平均速度。
   量完把骨頭姿勢還原，不影響正式的 mixer。換了模型檔（重新匯出）也會自動跟著變。 */
const LOCO=new Map();
function locoOf(name,sc,clips){const key=name+"|"+sc.scale.x.toFixed(4)+"|"+clips.map(c=>c.name+c.duration.toFixed(3)).join(",");if(LOCO.has(key))return LOCO.get(key);const out={};
  try{let fl=null,fr=null;const bones=[];sc.traverse(o=>{if(o.isBone)bones.push(o);if(/^Foot\.?L$/.test(o.name)&&!fl)fl=o;if(/^Foot\.?R$/.test(o.name)&&!fr)fr=o});
    if(fl&&fr){const saved=bones.map(b=>[b.position.clone(),b.quaternion.clone(),b.scale.clone()]),mx=new THREE.AnimationMixer(sc),a=new THREE.Vector3(),b=new THREE.Vector3();
      for(const c of clips){if(!/^(Stalk|StrafeL|StrafeR|Walk|Run)$/.test(c.name))continue;const act=mx.clipAction(c);act.play();const N=30,P=[];
        for(let i=0;i<=N;i++){mx.setTime(c.duration*i/N);sc.updateMatrixWorld(true);P.push([fl.getWorldPosition(new THREE.Vector3()),fr.getWorldPosition(new THREE.Vector3())])}
        act.stop();mx.uncacheClip(c);const dt=c.duration/N;let minY=Infinity;for(const p of P)minY=Math.min(minY,p[0].y,p[1].y);const box=new THREE.Box3().setFromObject(sc),hh=box.max.y-box.min.y;
        let vx=0,vz=0,n=0;for(let i=0;i<N;i++){const k=P[i][0].y<P[i][1].y?0:1;a.copy(P[i][k]);b.copy(P[i+1][k]);if(a.y>minY+.04*hh)continue;vx-=(b.x-a.x)/dt;vz-=(b.z-a.z)/dt;n++}
        if(n)out[c.name]=Math.hypot(vx/n,vz/n)}
      mx.uncacheRoot(sc);bones.forEach((bn,i)=>{bn.position.copy(saved[i][0]);bn.quaternion.copy(saved[i][1]);bn.scale.copy(saved[i][2])});sc.updateMatrixWorld(true)}}catch(e){console.warn("[view3d] 步速量測失敗",e)}
  LOCO.set(key,out);return out}

/* ---------- 武器拖尾 ----------
   找武器骨（Weapon／Sword／Staff，沒有就用右手指／右手），用蒙皮權重找出刀身在骨頭座標裡的兩端（只算一次、依模型快取）。
   揮擊片段播放時每格記下刀根與刀尖的世界座標，畫成一條往後淡出的帶子（Catmull-Rom 補點，快速揮砍也是圓弧不是折線）。一個角色一次 draw call。 */
const BLADE=new Map();
function bladeOf(name,sc){if(BLADE.has(name))return BLADE.get(name);let res=null;
  try{let mesh=null;sc.traverse(o=>{if(o.isSkinnedMesh&&!mesh)mesh=o});
    if(mesh){const bones=mesh.skeleton.bones,pick=re=>bones.findIndex(b=>re.test(b.name));let j=pick(/^(Weapon|Sword|Staff)$/i);const weapon=j>=0;if(j<0)j=pick(/^Fingers\.?R$/i);if(j<0)j=pick(/^Hand\.?R$/i);
      if(j>=0){const g=mesh.geometry,P=g.attributes.position,SI=g.attributes.skinIndex,SW=g.attributes.skinWeight,inv=mesh.skeleton.boneInverses[j],v=new THREE.Vector3(),pts=[];
        for(let i=0;i<P.count;i++){let w=0;for(let k=0;k<4;k++)if(SI.getComponent(i,k)===j)w+=SW.getComponent(i,k);if(w<.5)continue;v.fromBufferAttribute(P,i).applyMatrix4(mesh.bindMatrix).applyMatrix4(inv);pts.push(v.clone())}
        if(pts.length>=4){let tip=pts[0];for(const q of pts)if(q.lengthSq()>tip.lengthSq())tip=q;const dir=tip.clone().normalize();let lo=Infinity;for(const q of pts)lo=Math.min(lo,q.dot(dir));
          const len=tip.length();res={bone:bones[j].name,tip:tip.clone(),base:dir.clone().multiplyScalar(Math.max(lo,weapon?len*.3:len*.1))}}}}}catch(e){res=null}
  BLADE.set(name,res);return res}
const TRAIL_VS=`attribute float alpha;varying float vA;void main(){vA=alpha;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
const TRAIL_FS=`uniform vec3 uColor;uniform float uOp;varying float vA;void main(){gl_FragColor=vec4(uColor*vA*uOp,1.);}`;
function makeTrail(actor,sc){const info=bladeOf(actor.name,sc);if(!info)return null;let bone=null;sc.traverse(o=>{if(o.isBone&&o.name===info.bone&&!bone)bone=o});if(!bone)return null;
  const N=12,SUB=3,M=(N-1)*SUB+1,pos=new Float32Array(M*2*3),al=new Float32Array(M*2),idx=[];
  for(let i=0;i<M-1;i++){const a=i*2;idx.push(a,a+1,a+2,a+1,a+3,a+2)}
  const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3).setUsage(THREE.DynamicDrawUsage));g.setAttribute("alpha",new THREE.BufferAttribute(al,1).setUsage(THREE.DynamicDrawUsage));g.setIndex(idx);
  // 加色混合：輸出顏色×透明度，黑色＝不加任何東西
  const mat=new THREE.ShaderMaterial({vertexShader:TRAIL_VS,fragmentShader:TRAIL_FS,uniforms:{uColor:{value:new THREE.Color(actor.trailColor)},uOp:{value:.8}},transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(g,mat);mesh.frustumCulled=false;mesh.renderOrder=12;mesh.visible=false;actor.eng.scene.add(mesh);
  const hb=[],ht=[];let left=0,fade=0;const wb=new THREE.Vector3(),wt=new THREE.Vector3();
  const cr=(p0,p1,p2,p3,t,o)=>{const t2=t*t,t3=t2*t;o.set(0,0,0).addScaledVector(p0,-.5*t3+t2-.5*t).addScaledVector(p1,1.5*t3-2.5*t2+1).addScaledVector(p2,-1.5*t3+2*t2+.5*t).addScaledVector(p3,.5*t3-.5*t2);return o};
  const tmpA=new THREE.Vector3(),tmpB=new THREE.Vector3();
  return{color(c){mat.uniforms.uColor.value.set(c)},
    on(dur){if(!fade){hb.length=0;ht.length=0}left=Math.max(left,dur);fade=1},
    update(dt){if(!fade&&!left)return;if(dt<=0)return;left=Math.max(0,left-dt);if(!left){fade=Math.max(0,fade-dt*5);if(!fade){mesh.visible=false;hb.length=0;ht.length=0;return}}
      bone.updateWorldMatrix(true,false);wb.copy(info.base).applyMatrix4(bone.matrixWorld);wt.copy(info.tip).applyMatrix4(bone.matrixWorld);
      // 沒在動（例如停住的延遲攻擊）就不推新點，拖尾自然縮短
      if(hb.length&&ht[0].distanceToSquared(wt)<1e-6){hb.pop();ht.pop()}
      hb.unshift(wb.clone());ht.unshift(wt.clone());if(hb.length>N){hb.length=N;ht.length=N}
      const n=hb.length;if(n<2){mesh.visible=false;return}mesh.visible=true;let k=0;
      for(let i=0;i<n-1;i++)for(let s=0;s<SUB;s++){if(k>=M-1)break;const t=s/SUB,i0=Math.max(0,i-1),i3=Math.min(n-1,i+2);
        cr(hb[i0],hb[i],hb[i+1],hb[i3],t,tmpA);cr(ht[i0],ht[i],ht[i+1],ht[i3],t,tmpB);const a=Math.pow(Math.max(0,1-(i+t)/(N-1)),1.6)*fade;
        pos[k*6]=tmpA.x;pos[k*6+1]=tmpA.y;pos[k*6+2]=tmpA.z;pos[k*6+3]=tmpB.x;pos[k*6+4]=tmpB.y;pos[k*6+5]=tmpB.z;al[k*2]=a*.12;al[k*2+1]=a;k++}
      const last=hb[n-1],lt=ht[n-1];while(k<M){pos[k*6]=last.x;pos[k*6+1]=last.y;pos[k*6+2]=last.z;pos[k*6+3]=lt.x;pos[k*6+4]=lt.y;pos[k*6+5]=lt.z;al[k*2]=0;al[k*2+1]=0;k++}
      g.attributes.position.needsUpdate=true;g.attributes.alpha.needsUpdate=true},
    dispose(){actor.eng.scene.remove(mesh);g.dispose();mat.dispose()}}}
export { PROC };
