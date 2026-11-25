// 字典頁與字典內頁
import { $, app, esc, rid, toast, ask, SC } from '../core/util.js';
import { S, save, allDicts, ownDict, setup, replaceAll, exportJson } from '../core/store.js';
import { isPhrase } from '../core/grading.js';
import { spkBtn } from '../core/speech.js';

export function renderDicts(){const D=allDicts(),ids=Object.keys(D);
  app.innerHTML=`<h1>我的字典</h1><p class="sub">每本字典都能拿去練習：中英選擇、中英填空、克漏字，還能逐字朗讀。</p>
  <div class="dicts">${ids.map(id=>{const d=D[id],m=Object.keys(S.miss[id]||{}).length,ph=d.words.filter(isPhrase).length;return`<div class="cut">${SC}<div class="tab"><span>${esc(d.builtin?"NO.307":"MY DICT")}</span></div><div class="body">
   <p class="dname">${esc(d.name)}</p><div class="row" style="gap:18px;margin:8px 0 12px"><div><div class="stat">${d.words.length}</div><div class="small">條目（片語 ${ph}）</div></div><div><div class="stat" style="color:var(--bad)">${m}</div><div class="small">錯題</div></div></div>
   <div class="row"><button class="pri sm" data-go="${esc(id)}">練習</button><button class="sm" data-open="${esc(id)}">瀏覽・編輯</button></div></div></div>`}).join("")}
   <div class="cut">${SC}<div class="tab"><span>NEW</span></div><div class="body"><p class="dname">新增字典</p><p class="small" style="margin:4px 0 12px">拍下單字書頁，掃描後自動提取，檢查完存進來。</p><div class="row"><a class="btn pri" href="#upload" style="text-decoration:none">掃描上傳</a><button class="sm" id="blank">建立空白字典</button></div></div></div></div>
  <div class="row" style="margin-top:20px"><button class="sm" id="exp">匯出備份</button><label class="btn sm" style="min-height:36px;padding:5px 11px;font-size:14px">匯入備份<input type="file" accept=".json,application/json" id="imp" class="hide"></label><span class="small">資料存在這個瀏覽器裡；換電腦或清除瀏覽資料前，先匯出備份。</span></div>
  ${ids.length?"":'<p class="note" style="margin-top:16px">目前沒有字典。<button class="sm ghost" id="restore">還原內建 NO.307 字典</button></p>'}`;
  app.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>{setup.dict=b.dataset.go;location.hash="practice"});
  app.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>location.hash="dict-"+b.dataset.open);
  $("#blank").onclick=()=>{const id=rid();S.dicts[id]={id,name:"新字典 "+new Date().toLocaleDateString("zh-TW"),words:[]};save();location.hash="dict-"+id};
  $("#exp").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([exportJson()],{type:"application/json"}));a.download="單字剪卡備份-"+new Date().toISOString().slice(0,10)+".json";document.body.appendChild(a);a.click();a.remove()};
  $("#imp").onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const j=JSON.parse(await f.text());if(!j||typeof j.dicts!=="object")throw 0;if(!await ask("用這個備份取代目前所有字典與紀錄？"))return;replaceAll(j);toast("已匯入備份");renderDicts()}catch(x){toast("這不是有效的備份檔")}};
  const r=$("#restore");if(r)r.onclick=()=>{delete S.hidden.no307;save();renderDicts()}}

let dq="",editing=null;
export function renderDict(id){const d=allDicts()[id];if(!d){location.hash="dicts";return}
  const q=dq.toLowerCase(),ws=d.words.filter(w=>!q||(w.en+w.zh+w.ex).toLowerCase().includes(q));
  app.innerHTML=`<p><a href="#dicts" class="small">← 所有字典</a></p><div class="row" style="align-items:flex-end"><h1 style="margin-right:auto">${esc(d.name)}</h1><button class="sm" id="ren">重新命名</button><button class="sm" id="del" style="color:var(--bad)">刪除字典</button></div>
  <p class="sub">${d.words.length} 個條目</p>
  <div class="row" style="margin-bottom:12px"><input id="q" placeholder="搜尋英文、中文或例句" value="${esc(dq)}" style="flex:1 1 220px;width:auto"><button class="pri" id="prac">練習這本</button><button id="add">＋ 新增單字</button></div>
  <div class="cut">${SC}<div class="tab"><span>${esc(d.builtin?"NO.307":"WORDS")}</span></div><div class="body list" id="list">${ws.map(w=>editing===w.id?editRow(w):wordRow(w)).join("")||'<p class="small">沒有符合的條目。</p>'}</div></div>`;
  $("#q").oninput=e=>{dq=e.target.value;const p=e.target.selectionStart;renderDict(id);const i=$("#q");i.focus();i.setSelectionRange(p,p)};
  $("#prac").onclick=()=>{setup.dict=id;location.hash="practice"};
  $("#add").onclick=()=>{const dd=ownDict(id),w={id:rid(),en:"",pos:"",zh:"",ex:"",blank:"",unit:""};dd.words.unshift(w);editing=w.id;dq="";renderDict(id)};
  $("#ren").onclick=()=>{const h=app.querySelector("h1");h.innerHTML=`<input id="nm" value="${esc(d.name)}">`;const i=$("#nm");let done=false;i.focus();i.onblur=i.onkeydown=e=>{if(e.type==="keydown"&&e.key!=="Enter")return;if(done)return;done=true;const dd=ownDict(id);dd.name=i.value.trim()||dd.name;save();renderDict(id)}};
  $("#del").onclick=async()=>{if(!await ask(`確定要刪除「${d.name}」？這無法復原。`))return;if(id==="no307")S.hidden.no307=true;delete S.dicts[id];delete S.miss[id];save();location.hash="dicts"};
  $("#list").onclick=async e=>{const b=e.target.closest("button");if(!b)return;const wid=b.dataset.w;
    if(b.dataset.a==="edit"){editing=wid;renderDict(id)}
    else if(b.dataset.a==="rm"){if(!await ask("刪除這個條目？"))return;const dd=ownDict(id);dd.words=dd.words.filter(w=>w.id!==wid);save();renderDict(id)}
    else if(b.dataset.a==="ok"){const dd=ownDict(id),w=dd.words.find(x=>x.id===wid),f=b.closest(".it");["en","pos","zh","ex","blank","unit"].forEach(k=>w[k]=f.querySelector(`[data-k=${k}]`).value.trim());if(!w.en){dd.words=dd.words.filter(x=>x!==w)}editing=null;save();renderDict(id)}
    else if(b.dataset.a==="cancel"){const dd=S.dicts[id],w=dd&&dd.words.find(x=>x.id===wid);if(w&&!w.en)dd.words=dd.words.filter(x=>x!==w);editing=null;renderDict(id)}}}

export function wordRow(w,plain){const m=Object.values(S.miss).some(o=>o[w.id]);return`<div class="it"><div><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span>${m?' <span class="small" style="color:var(--bad)">・錯過</span>':""}<div>${esc(w.zh)}</div>${w.ex?`<div class="ex en">${esc(w.ex)}</div>`:""}</div>
  <div class="row" style="gap:4px;align-items:flex-start">${spkBtn(w.en,"朗讀單字")}${w.ex?spkBtn(w.ex,"朗讀例句"):""}${plain?"":`<button class="sm ghost" data-a="edit" data-w="${esc(w.id)}">編輯</button><button class="sm ghost" data-a="rm" data-w="${esc(w.id)}" aria-label="刪除">✕</button>`}</div></div>`}
function editRow(w){const f=(k,l,c)=>`<label class="${c}"><span class="small">${l}</span><input data-k="${k}" value="${esc(w[k])}"></label>`;
  return`<div class="it" style="grid-template-columns:1fr"><div class="rev"><div class="rc" style="border:0;padding:0">${f("en","英文","f3 wide")}${f("pos","詞性","f1")}${f("unit","單元","f2")}${f("zh","中文","f6")}${f("ex","例句","f6")}${f("blank","克漏字答案（例句中的實際字形）","f6")}</div></div>
  <div class="row"><button class="pri sm" data-a="ok" data-w="${esc(w.id)}">儲存</button><button class="sm" data-a="cancel" data-w="${esc(w.id)}">取消</button></div></div>`}
