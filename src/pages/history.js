// 錯題紀錄頁
import { $, app, esc, ask, SC, fmt } from '../core/util.js';
import { S, save, allDicts, setup, findW, ctx } from '../core/store.js';
import { modeName } from '../core/grading.js';
import { spkBtn } from '../core/speech.js';

let hf={dict:"__all",sort:"n"};
export function renderHist(){const D=allDicts();let rows=[];
  for(const d in S.wlog)for(const id in S.wlog[d]){if(hf.dict!=="__all"&&hf.dict!==d)continue;const w=findW(d,id);if(w)rows.push({d,w,L:S.wlog[d][id],todo:!!(S.miss[d]&&S.miss[d][id])})}
  rows.sort(hf.sort==="n"?(a,b)=>b.L.n-a.L.n||b.L.last-a.L.last:hf.sort==="t"?(a,b)=>b.L.last-a.L.last:(a,b)=>(b.todo-a.todo)||b.L.n-a.L.n);
  const todo=rows.filter(r=>r.todo).length,hs=S.hist.filter(s=>hf.dict==="__all"||s.dict===hf.dict);
  const chip=(v,l)=>`<button class="chip ${hf.sort===v?"on":""}" data-s="${v}">${l}</button>`;
  app.innerHTML=`<h1>錯題紀錄</h1><p class="sub">每次答錯都會留下紀錄：錯幾次、什麼時候、你當時答了什麼。後來答對會從「待複習」移除，但紀錄會保留。</p>
  <div class="row" style="gap:22px;margin-bottom:16px"><div><div class="stat">${rows.length}</div><div class="small">答錯過的字</div></div><div><div class="stat" style="color:var(--bad)">${todo}</div><div class="small">待複習</div></div><div><div class="stat">${hs.length}</div><div class="small">練習次數</div></div></div>
  <div class="row" style="margin-bottom:12px"><select id="hd" style="flex:1 1 220px;width:auto"><option value="__all">全部字典</option>${Object.values(D).map(d=>`<option value="${esc(d.id)}" ${d.id===hf.dict?"selected":""}>${esc(d.name)}</option>`).join("")}</select><button class="pri" id="hp" ${todo?"":"disabled"}>練習待複習的 ${todo} 個</button></div>
  <div class="chips" style="margin-bottom:12px">${chip("n","錯最多次")}${chip("t","最近答錯")}${chip("todo","待複習優先")}</div>
  <div class="cut">${SC}<div class="tab"><span>MISSED</span></div><div class="body list">${rows.map(({w,L,todo})=>`<div class="it"><div><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span>
    <span class="small" style="margin-left:6px;color:${todo?"var(--bad)":"var(--ok)"}">${todo?"待複習":"已練會"}</span><div>${esc(w.zh)}</div>
    <div class="small">錯 ${L.n} 次・上次 ${fmt(L.last)}</div>${L.ans.length?`<div class="small">你答過：${L.ans.map(a=>`「${esc(a.a)}」<span style="opacity:.7">${esc(modeName(a.m))}・${fmt(a.t)}</span>`).join("；")}</div>`:""}</div>
    <div class="row" style="gap:4px;align-items:flex-start">${spkBtn(w.en)}</div></div>`).join("")||'<p class="small">還沒有答錯紀錄，去練習吧！</p>'}</div></div>
  <h2>練習歷程</h2><div class="cut">${SC}<div class="tab"><span>LOG</span></div><div class="body list">${hs.map(s=>{const ws=s.wrong.map(([d,id])=>findW(d,id)).filter(Boolean);return`<details class="it" style="display:block"><summary style="cursor:pointer;min-height:40px"><b>${fmt(s.t)}</b>・${esc(modeName(s.mode))}${s.game==="soul"?"・魂系":s.game?"・打怪":""}・${esc((D[s.dict]||{name:"全部字典"}).name)}・<b style="color:${s.right===s.n?"var(--ok)":"var(--or)"}">${s.right}/${s.n}</b></summary>
    ${ws.length?`<div class="small" style="padding:6px 0 0">答錯：${ws.map(w=>`<span class="w">${esc(w.en)}</span> ${esc(w.zh)}`).join("　")}</div>`:'<div class="small">全對！</div>'}</details>`}).join("")||'<p class="small">還沒有練習紀錄。</p>'}</div></div>
  ${rows.length||hs.length?'<p style="margin-top:16px"><button class="sm ghost" id="hclr" style="color:var(--bad)">清除所有紀錄</button></p>':""}`;
  $("#hd").onchange=e=>{hf.dict=e.target.value;renderHist()};
  app.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>{hf.sort=b.dataset.s;renderHist()});
  // 一鍵練待複習：直接開始只含這些字的練習
  $("#hp").onclick=()=>{setup.dict=hf.dict;setup.wrong=true;setup.scope="all";ctx.autoStart=true;location.hash="practice"};
  const c=$("#hclr");if(c)c.onclick=async()=>{if(!await ask("清除所有錯題紀錄與練習歷程？待複習清單也會一起清空。"))return;S.wlog={};S.hist=[];S.miss={};save();renderHist()}}
