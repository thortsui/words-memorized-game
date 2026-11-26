// 歷史錯誤單字：每個字歷史上總共錯了幾次（之後答對也不會減少），依次數排行，方便複習
import { $, app, esc, SC, fmt } from '../core/util.js';
import { S, allDicts, findW, ctx } from '../core/store.js';
import { spkBtn } from '../core/speech.js';

const mf={dict:"__all",sort:"n"};
function rows(){const out=[];
  for(const d in S.wlog){if(mf.dict!=="__all"&&mf.dict!==d)continue;for(const id in S.wlog[d]){const w=findW(d,id),L=S.wlog[d][id];if(w&&L&&L.n>0)out.push({d,id,w,n:L.n,last:L.last||0,todo:!!(S.miss[d]&&S.miss[d][id])})}}
  out.sort(mf.sort==="t"?(a,b)=>b.last-a.last:mf.sort==="az"?(a,b)=>a.w.en.localeCompare(b.w.en,"en",{sensitivity:"base"}):(a,b)=>b.n-a.n||b.last-a.last);
  return out}
export function renderMissed(){const D=allDicts(),R=rows(),total=R.reduce((a,r)=>a+r.n,0),max=R.reduce((a,r)=>Math.max(a,r.n),1);
  const chip=(v,l)=>`<button class="chip ${mf.sort===v?"on":""}" data-s="${v}">${l}</button>`;
  app.innerHTML=`<h1>歷史錯誤單字</h1><p class="sub">每個字歷史上總共答錯幾次。之後答對也不會減少，越上面的越常錯，最值得複習。</p>
  <div class="row" style="gap:22px;margin-bottom:16px"><div><div class="stat">${R.length}</div><div class="small">錯過的字</div></div><div><div class="stat" style="color:var(--bad)">${total}</div><div class="small">累計答錯次數</div></div></div>
  <div class="row" style="margin-bottom:12px"><select id="md" style="flex:1 1 220px;width:auto"><option value="__all">全部字典</option>${Object.values(D).map(d=>`<option value="${esc(d.id)}" ${d.id===mf.dict?"selected":""}>${esc(d.name)}</option>`).join("")}</select></div>
  <div class="chips" style="margin-bottom:12px">${chip("n","錯最多次")}${chip("t","最近答錯")}${chip("az","字母順序")}</div>
  <div class="row" style="gap:8px;margin-bottom:14px"><button class="pri" id="mq10" ${R.length?"":"disabled"}>隨機抽 10 個練習</button><button id="mqall" ${R.length?"":"disabled"}>全部練習（${R.length}）</button><button id="mcard" ${R.length?"":"disabled"}>用閃卡複習</button></div>
  <div class="cut">${SC}<div class="tab"><span>RANKING</span></div><div class="body list mlist">${R.map((r,i)=>`<div class="it"><div class="mrow"><span class="mrank">${i+1}</span><div style="min-width:0">
    <div><span class="w">${esc(r.w.en)}</span><span class="pos">${esc(r.w.pos)}</span>${r.todo?'<span class="small" style="margin-left:6px;color:var(--bad)">待複習</span>':""}</div><div>${esc(r.w.zh)}</div>
    <div class="mbar"><i style="width:${(r.n/max*100).toFixed(1)}%"></i></div><div class="small">錯 <b style="color:var(--bad)">${r.n}</b> 次・上次 ${r.last?fmt(r.last):"—"}${mf.dict==="__all"&&D[r.d]?"・"+esc(D[r.d].name):""}</div></div></div>
    <div class="row" style="gap:4px;align-items:flex-start">${spkBtn(r.w.en)}</div></div>`).join("")||'<p class="small">還沒有答錯過的字，去練習吧！</p>'}</div></div>`;
  $("#md").onchange=e=>{mf.dict=e.target.value;renderMissed()};
  app.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>{mf.sort=b.dataset.s;renderMissed()});
  // 只練這些字：交給練習頁（only＝「字典|id」清單）；n:10＝從中隨機抽 10 個
  const go=(n,cards)=>{const R2=rows();if(!R2.length)return;ctx.autoStart={dict:mf.dict,scope:"all",wrong:false,n,only:R2.map(r=>r.d+"|"+r.id),cards:!!cards};location.hash="practice"};
  $("#mq10").onclick=()=>go(10);$("#mqall").onclick=()=>go(0);$("#mcard").onclick=()=>go(0,true)}
