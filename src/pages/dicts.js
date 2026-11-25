// 字典頁與字典內頁
import { $, app, esc, rid, toast, ask, SC } from '../core/util.js';
import { S, save, allDicts, ownDict, setup, saveSetup, replaceAll, exportJson, forget } from '../core/store.js';
import { normalizeState } from '../core/normalize.js';
import { isPhrase } from '../core/grading.js';
import { spkBtn } from '../core/speech.js';

export function renderDicts(){const D=allDicts(),ids=Object.keys(D);
  app.innerHTML=`<h1>我的字典</h1><p class="sub">每本字典都能拿去練習：中英選擇、中英填空、克漏字，還能逐字朗讀。</p>
  <div class="dicts">${ids.map(id=>{const d=D[id],m=Object.keys(S.miss[id]||{}).length,ph=d.words.filter(isPhrase).length;return`<div class="cut">${SC}<div class="tab"><span>${esc(d.builtin?"NO.307":"MY DICT")}</span></div><div class="body">
   <p class="dname">${esc(d.name)}</p><div class="row" style="gap:18px;margin:8px 0 12px"><div><div class="stat">${d.words.length}</div><div class="small">條目（片語 ${ph}）</div></div><div><div class="stat" style="color:var(--bad)">${m}</div><div class="small">錯題</div></div></div>
   <div class="row"><button class="pri sm" data-go="${esc(id)}">練習</button><button class="sm" data-open="${esc(id)}">瀏覽・編輯</button></div></div></div>`}).join("")}
   <div class="cut">${SC}<div class="tab"><span>NEW</span></div><div class="body"><p class="dname">新增字典</p><p class="small" style="margin:4px 0 12px">拍下單字書頁，掃描後自動提取，檢查完存進來。</p><div class="row"><a class="btn pri" href="#upload" style="text-decoration:none">掃描上傳</a><button class="sm" id="blank">建立空白字典</button></div></div></div></div>
  <div class="row" style="margin-top:20px"><button class="sm" id="exp">匯出備份</button><label class="btn sm">匯入備份<input type="file" accept=".json,application/json" id="imp" class="hide"></label><span class="small">資料存在這個瀏覽器裡；換電腦或清除瀏覽資料前，先匯出備份。</span></div>
  ${S.hidden.no307?`<p class="note" style="margin-top:16px">${ids.length?"內建的 NO.307 字典已被刪除。":"目前沒有字典。"}<button class="sm ghost" id="restore">還原內建 NO.307 字典</button></p>`:""}`;
  app.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>{setup.dict=b.dataset.go;saveSetup();location.hash="practice"});
  app.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>location.hash="dict-"+b.dataset.open);
  $("#blank").onclick=()=>{const id=rid();S.dicts[id]={id,name:"新字典 "+new Date().toLocaleDateString("zh-TW"),words:[]};if(!save()){delete S.dicts[id];return}location.hash="dict-"+id};
  $("#exp").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([exportJson()],{type:"application/json"}));a.download="單字剪卡備份-"+localDate()+".json";document.body.appendChild(a);a.click();a.remove()};
  $("#imp").onchange=async e=>{const inp=e.target,f=inp.files[0];if(!f)return;
    let j;try{j=JSON.parse(await f.text())}catch(x){inp.value="";toast("這不是有效的備份檔（不是 JSON 格式），沒有匯入任何資料",5000);return}
    inp.value=""; // 清空，取消後再選同一個檔案才會再觸發 change
    // 先完整驗證；任何一處格式不對就整份不匯入，原本的資料完全不動
    let n;try{n=normalizeState(j,{strict:true})}catch(x){toast("這不是有效的備份檔："+(x&&x.message||"格式不對")+"。沒有匯入任何資料",6000);return}
    const nd=Object.keys(n.dicts).length,nw=Object.values(n.dicts).reduce((a,d)=>a+d.words.length,0);
    if(!await ask(`用這個備份（${nd} 本字典、${nw} 個條目）取代目前所有字典與紀錄？`))return;
    let ok=false;try{ok=replaceAll(j)}catch(x){toast("這不是有效的備份檔，沒有匯入任何資料",5000);return}
    if(!ok){toast("匯入失敗：瀏覽器的儲存空間不足。原本的資料沒有變動。",6000);return}
    toast("已匯入備份");renderDicts()};
  const r=$("#restore");if(r)r.onclick=()=>{delete S.hidden.no307;save();renderDicts()}}
const localDate=()=>{const d=new Date(),p=n=>String(n).padStart(2,"0");return d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())};

// editing：正在編輯的條目 id；draft：按了「新增單字」但還沒儲存的條目（只放在這裡，儲存時才真的加進字典）
let dq="",editing=null,draft=null,curDict=null;
// 路由切換時呼叫：沒按儲存的新增／編輯一律丟掉（空白條目不會留在字典裡）；換一本字典時搜尋字也清掉
export function leaveDict(h){editing=null;draft=null;const id=h&&h.startsWith("dict-")?h.slice(5):null;if(id!==curDict)dq="";curDict=id}
export function renderDict(id){const d=allDicts()[id];if(!d){location.hash="dicts";return}
  const q=dq.toLowerCase(),ws=d.words.filter(w=>!q||(w.en+w.zh+w.ex).toLowerCase().includes(q));
  if(draft&&draft.dict!==id)draft=null;
  app.innerHTML=`<p style="margin:0"><a href="#dicts" class="small back">← 所有字典</a></p><div class="row" style="align-items:flex-end"><h1 style="margin-right:auto;flex:1 1 200px">${esc(d.name)}</h1><button class="sm" id="ren">重新命名</button><button class="sm" id="del" style="color:var(--bad)">刪除字典</button></div>
  <p class="sub">${d.words.length} 個條目</p>
  <div class="row" style="margin-bottom:12px"><input id="q" placeholder="搜尋英文、中文或例句" value="${esc(dq)}" style="flex:1 1 220px;width:auto"><button class="pri" id="prac">練習這本</button><button id="add">＋ 新增單字</button></div>
  <div class="cut">${SC}<div class="tab"><span>${esc(d.builtin?"NO.307":"WORDS")}</span></div><div class="body list" id="list">${(draft?editRow(draft.w):"")+ws.map(w=>editing===w.id?editRow(w):wordRow(w)).join("")||'<p class="small">沒有符合的條目。</p>'}</div></div>`;
  const ef=app.querySelector("#list .editing [data-k=en]");if(ef&&focusEdit){focusEdit=false;ef.focus()}
  $("#q").oninput=e=>{dq=e.target.value;const p=e.target.selectionStart;renderDict(id);const i=$("#q");i.focus();i.setSelectionRange(p,p)};
  $("#prac").onclick=()=>{setup.dict=id;saveSetup();location.hash="practice"};
  $("#add").onclick=()=>{draft={dict:id,w:{id:rid(),en:"",pos:"",zh:"",ex:"",blank:"",unit:""}};editing=null;dq="";focusEdit=true;renderDict(id)};
  // 重新命名：Enter 或離開輸入框＝儲存，Esc＝取消
  $("#ren").onclick=()=>{const h=app.querySelector("h1");h.innerHTML=`<input id="nm" value="${esc(d.name)}" aria-label="字典名稱">`;const i=$("#nm");let done=false;i.focus();i.select();
    i.onblur=i.onkeydown=e=>{if(e.type==="keydown"&&e.key!=="Enter"&&e.key!=="Escape")return;if(done)return;done=true;
      if(e.type==="keydown"&&e.key==="Escape"){renderDict(id);return}
      const nm=i.value.trim();if(nm&&nm!==d.name){ownDict(id).name=nm;save()}renderDict(id)}};
  $("#del").onclick=async()=>{if(!await ask(`確定要刪除「${d.name}」？這本字典的錯題紀錄也會一起刪除，無法復原。`))return;if(id==="no307")S.hidden.no307=true;delete S.dicts[id];forget(id);save();location.hash="dicts"};
  const saveRow=(f,wid)=>{const v={};["en","pos","zh","ex","blank","unit"].forEach(k=>v[k]=f.querySelector(`[data-k=${k}]`).value.trim());
    if(draft&&draft.w.id===wid){if(v.en)ownDict(id).words.unshift({...draft.w,...v});const had=!!v.en;draft=null;if(had)save()}
    else{const dd=ownDict(id),w=dd.words.find(x=>x.id===wid);if(w){if(v.en)Object.assign(w,v);else{dd.words=dd.words.filter(x=>x!==w);forget(id,wid)}}editing=null;save()}
    renderDict(id)};
  const cancelRow=()=>{draft=null;editing=null;renderDict(id)};
  $("#list").onclick=async e=>{const b=e.target.closest("button");if(!b)return;const wid=b.dataset.w;
    if(b.dataset.a==="edit"){editing=wid;draft=null;focusEdit=true;renderDict(id)}
    else if(b.dataset.a==="rm"){if(!await ask("刪除這個條目？它的錯題紀錄也會一起刪除。"))return;const dd=ownDict(id);dd.words=dd.words.filter(w=>w.id!==wid);forget(id,wid);save();renderDict(id)}
    else if(b.dataset.a==="ok")saveRow(b.closest(".it"),wid);
    else if(b.dataset.a==="cancel")cancelRow()};
  // 新增中的條目：打到一半的內容先記在 draft 裡（搜尋等重畫時不會不見）
  $("#list").oninput=e=>{const k=e.target.dataset&&e.target.dataset.k,f=e.target.closest(".it.editing");if(k&&f&&draft&&draft.w.id===f.dataset.w)draft.w[k]=e.target.value};
  // 編輯列：Enter＝儲存、Esc＝取消
  $("#list").onkeydown=e=>{const f=e.target.closest(".it.editing");if(!f||e.target.tagName!=="INPUT"||e.isComposing)return;
    if(e.key==="Enter"){e.preventDefault();saveRow(f,f.dataset.w)}else if(e.key==="Escape"){e.preventDefault();cancelRow()}}}
let focusEdit=false;

export function wordRow(w,plain){const m=Object.values(S.miss).some(o=>o[w.id]);return`<div class="it${plain?"":" acts"}"><div><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span>${m?' <span class="small" style="color:var(--bad)">・錯過</span>':""}<div>${esc(w.zh)}</div>${w.ex?`<div class="ex en">${esc(w.ex)}</div>`:""}</div>
  <div class="row" style="gap:4px;align-items:flex-start">${spkBtn(w.en,"朗讀單字")}${w.ex?spkBtn(w.ex,"朗讀例句"):""}${plain?"":`<button class="sm ghost" data-a="edit" data-w="${esc(w.id)}">編輯</button><button class="sm ghost" data-a="rm" data-w="${esc(w.id)}" aria-label="刪除">✕</button>`}</div></div>`}
function editRow(w){const f=(k,l,c)=>`<label class="${c}"><span class="small">${l}</span><input data-k="${k}" value="${esc(w[k])}"></label>`;
  return`<div class="it editing" data-w="${esc(w.id)}" style="grid-template-columns:minmax(0,1fr)"><div class="rev"><div class="rc" style="border:0;padding:0">${f("en","英文","f3 wide")}${f("pos","詞性","f1")}${f("unit","單元","f2")}${f("zh","中文","f6")}${f("ex","例句","f6")}${f("blank","克漏字答案（例句中的實際字形）","f6")}</div></div>
  <div class="row"><button class="pri sm" data-a="ok" data-w="${esc(w.id)}">儲存</button><button class="sm" data-a="cancel" data-w="${esc(w.id)}">取消</button></div></div>`}
