// 頁首的版本號與「檢查更新」按鈕，以及 iPhone「加入主畫面」提示。
import { $, toast, lsGet, lsSet } from '../core/util.js';
import { VERSION, checkUpdate, restart, afterRestart, isIOS, standalone, inArtifact } from '../core/update.js';

function dialog(html,buttons){const m=$("#modal"),box=m.firstElementChild,old=box.innerHTML;
  box.innerHTML=`<div class="updlg">${html}</div><div class="row" style="justify-content:flex-end;margin-top:14px">${buttons.map((b,i)=>`<button data-i="${i}" class="${b.pri?"pri":""}">${b.t}</button>`).join("")}</div>`;
  m.classList.remove("hide");
  return new Promise(r=>{box.querySelectorAll("button[data-i]").forEach(el=>el.onclick=()=>{m.classList.add("hide");box.innerHTML=old;r(+el.dataset.i)})})}

async function onCheck(btn){btn.disabled=true;const t0=btn.textContent;btn.textContent="檢查中…";
  try{const r=await checkUpdate();
    if(r.state==="new"){const i=await dialog(`<h3>有新版本！</h3><p>目前 v${VERSION} → 最新 <b>v${r.latest.version}</b></p><p>按「重新啟動」就會重開並換成新版本。</p>`,[{t:"稍後"},{t:"重新啟動",pri:true}]);
      if(i===1)restart(r.latest)}
    else if(r.state==="latest")toast(`已經是最新版本 v${VERSION}`);
    else toast("目前無法檢查更新（離線或網站不支援），請稍後再試")}
  finally{btn.disabled=false;btn.textContent=t0}}

export function mountUpdate(){const v=$("#ver"),b=$("#updb");if(!v||!b)return;v.textContent="v"+VERSION;b.onclick=()=>onCheck(b);
  const msg=afterRestart();if(msg)setTimeout(()=>toast(msg,4500),400);
  // iPhone 用 Safari 打開（不是從主畫面）時提示一次：加入主畫面就像 App 一樣
  if(isIOS()&&!standalone()&&!inArtifact()&&!lsGet("wg-a2hs",""))setTimeout(()=>{lsSet("wg-a2hs","1");
    dialog(`<h3>把單字魂放到主畫面</h3><p>點 Safari 下方的「分享」<b>⬆︎</b> →「加入主畫面」，之後就能像 App 一樣全螢幕使用。</p><p class="small">要更新時，按右上角「檢查更新」就好。</p>`,[{t:"知道了",pri:true}])},1500)}
