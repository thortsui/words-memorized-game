// 版本與更新檢查（v1.0.0 起）。
// 最新版本號從兩個地方找，取比較新的那個：
//   1. ./version.json（一般網站：重新部署就會變；用 no-store 繞過快取）
//   2. claude.ai Artifact 的資料庫 meta/release（Artifact 每一版的網址是固定的，自己的 version.json 永遠是舊的，
//      所以每次發布後另外寫一筆「目前最新版本」到資料庫）
// 重新啟動＝重新載入頁面。Artifact 內嵌頁只能重載自己這一版；重載後還是舊版，就請使用者把 App 完全關掉再打開。
/* global __APP_VER__, __APP_BUILD__ */
export const VERSION=typeof __APP_VER__!=="undefined"?__APP_VER__:"dev";
export const BUILD=typeof __APP_BUILD__!=="undefined"?__APP_BUILD__:0;
export const inArtifact=()=>/claudeusercontent\.com$/.test(location.hostname);

async function fromFile(){try{const r=await fetch("./version.json?t="+Date.now(),{cache:"no-store"});if(!r.ok)return null;const j=await r.json();return j&&j.build?j:null}catch(e){return null}}
async function fromDb(){try{const c=window.claude;if(!c||!c.use)return null;
    const db=await Promise.race([c.use("db"),new Promise(r=>setTimeout(()=>r(null),6000))]);if(!db)return null;
    const s=await db.doc("meta/release").get();const d=s&&(typeof s.data==="function"?s.data():s.data);return d&&d.build?d:null}catch(e){return null}}

// 回傳 {state:"new"|"latest"|"unknown", latest:{version,build}|null}
export async function checkUpdate(){const [a,b]=await Promise.all([fromFile(),fromDb()]);
  const latest=[a,b].filter(Boolean).sort((x,y)=>y.build-x.build)[0]||null;
  if(!latest)return{state:"unknown",latest:null};
  return{state:latest.build>BUILD?"new":"latest",latest}}

const KEY="wg-restart";
export async function restart(target){try{sessionStorage.setItem(KEY,JSON.stringify({from:BUILD,want:target&&target.build||0,at:Date.now()}))}catch(e){}
  // 一般網站：先把首頁的 HTTP 快取換掉再重載（資源檔名有雜湊，首頁新了其他就都新了）
  if(!inArtifact()){try{await fetch("./",{cache:"reload"})}catch(e){}}
  location.reload()}
// 重新啟動後呼叫：回傳要顯示的提示（沒有就 null）
export function afterRestart(){let o=null;try{o=JSON.parse(sessionStorage.getItem(KEY)||"null");sessionStorage.removeItem(KEY)}catch(e){}
  if(!o||Date.now()-o.at>60000)return null;
  if(BUILD>=o.want&&BUILD!==o.from)return`已更新到 v${VERSION}`;
  return inArtifact()?"還在舊版：請把 App 從多工畫面完全關掉，再重新打開一次":"還在舊版：請稍等一分鐘再試（網站剛更新，快取還沒換掉）"}
export const isIOS=()=>/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);
export const standalone=()=>navigator.standalone===true||matchMedia("(display-mode: standalone)").matches;
