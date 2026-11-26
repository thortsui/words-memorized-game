// 掃描上傳：載入照片 → 調四角 → 透視校正＋去陰影 → 兩個引擎各提取一次並交叉比對 → 規則檢查＋Google 翻譯核對 → 逐筆人工確認後存入
// 設計見 docs/掃描強化設計.md：一筆條目只有「兩個獨立引擎讀的完全一樣而且規則檢查通過」或「使用者對著原圖確認過」才能存入。
import { $, app, esc, rid, toast, ask, SC, loadScript, lsGet, lsSet } from '../core/util.js';
import { S, save, allDicts, ownDict } from '../core/store.js';
import { sayable, gtrans, cjk } from '../core/grading.js';
import { spkBtn } from '../core/speech.js';
import { ENGINES, FREE, getEngine } from '../scan/engines/index.js';
import { consensus, leftovers, FIELD_NAME } from '../scan/consensus.js';
import { parseHead, tidy } from '../scan/parse.js';
import { ruleWarnings } from '../scan/rules.js';
import { loadLexicon } from '../scan/wordlist.js';
import { straighten } from '../scan/deskew.js';
import { pdfPages } from '../scan/pdf.js';
import { parseLayout } from '../scan/parse.js';

// engA／engB：主引擎與複核引擎（"none"＝不複核）；adv：有沒有打開「進階」裡的 Claude
let pages=[],cur=0,review=[],showOut=true,engA=lsGet("vc-ext","ppocr"),engB=lsGet("vc-ext2","ocr"),adv=lsGet("vc-adv","0")==="1";

/* ----- 透視校正：由四角解 3×3 單應矩陣（8 元線性方程） ----- */
export function solve(A,b){const n=b.length;for(let i=0;i<n;i++){let p=i;for(let r=i+1;r<n;r++)if(Math.abs(A[r][i])>Math.abs(A[p][i]))p=r;[A[i],A[p]]=[A[p],A[i]];[b[i],b[p]]=[b[p],b[i]];for(let r=i+1;r<n;r++){const f=A[r][i]/A[i][i];for(let c=i;c<n;c++)A[r][c]-=f*A[i][c];b[r]-=f*b[i]}}const x=Array(n);for(let i=n-1;i>=0;i--){let s=b[i];for(let c=i+1;c<n;c++)s-=A[i][c]*x[c];x[i]=s/A[i][i]}return x}
export function homog(src,dst){const A=[],b=[];for(let i=0;i<4;i++){const[x,y]=src[i],[u,v]=dst[i];A.push([x,y,1,0,0,0,-u*x,-u*y]);b.push(u);A.push([0,0,0,x,y,1,-v*x,-v*y]);b.push(v)}return solve(A,b)}
// 分段執行：每 40ms 讓出主執行緒一次，掃描大圖時畫面不會卡住
async function scan(p){if(p.pdf){const c=document.createElement("canvas");c.width=p.src.width;c.height=p.src.height;c.getContext("2d").drawImage(p.src,0,0);p.out=c;p._jpg=null;p.status="scanned";return}
  let t0=performance.now();const brk=async()=>{if(performance.now()-t0>40){await new Promise(r=>setTimeout(r,0));t0=performance.now()}};const q=p.q,d=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  let W=Math.max(d(q[0],q[1]),d(q[3],q[2])),H=Math.max(d(q[0],q[3]),d(q[1],q[2]));const k=Math.min(1,2000/Math.max(W,H));W=Math.round(W*k);H=Math.round(H*k);
  const h=homog([[0,0],[W,0],[W,H],[0,H]],q),sc=p.src,sw=sc.width,sh=sc.height,sd=sc.getContext("2d").getImageData(0,0,sw,sh).data;
  const out=document.createElement("canvas");out.width=W;out.height=H;const ctx=out.getContext("2d"),im=ctx.createImageData(W,H),o=im.data;
  // 雙線性取樣
  for(let y=0;y<H;y++){if(!(y&31))await brk();for(let x=0;x<W;x++){const w=h[6]*x+h[7]*y+1,sx=(h[0]*x+h[1]*y+h[2])/w,sy=(h[3]*x+h[4]*y+h[5])/w;
    const x0=Math.max(0,Math.min(sw-2,sx|0)),y0=Math.max(0,Math.min(sh-2,sy|0)),fx=Math.min(1,Math.max(0,sx-x0)),fy=Math.min(1,Math.max(0,sy-y0)),i=(y0*sw+x0)*4,j=(y*W+x)*4;
    for(let c=0;c<3;c++){const a=sd[i+c]*(1-fx)+sd[i+4+c]*fx,b=sd[i+sw*4+c]*(1-fx)+sd[i+sw*4+4+c]*fx;o[j+c]=a*(1-fy)+b*fy}o[j+3]=255}}
  // 去陰影：每 16 px 一格取最大亮度當背景，一次 3×3 最大值、三次 3×3 平均，再把 35–232 拉伸到 0–255
  if(p.clean){const f=16,gw=Math.ceil(W/f),gh=Math.ceil(H/f);let g=new Float32Array(gw*gh);
    for(let y=0;y<H;y++){if(!(y&63))await brk();for(let x=0;x<W;x++){const j=(y*W+x)*4,L=.3*o[j]+.59*o[j+1]+.11*o[j+2],gi=(y/f|0)*gw+(x/f|0);if(L>g[gi])g[gi]=L}}
    for(let pass=0;pass<4;pass++){const n=new Float32Array(gw*gh);for(let y=0;y<gh;y++)for(let x=0;x<gw;x++){let s=0,c=0,m=0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const yy=y+dy,xx=x+dx;if(yy<0||xx<0||yy>=gh||xx>=gw)continue;const v=g[yy*gw+xx];s+=v;c++;if(v>m)m=v}n[y*gw+x]=pass<1?m:s/c}g=n}
    for(let y=0;y<H;y++){if(!(y&63))await brk();const gy=Math.min(gh-1.001,Math.max(0,y/f-.5)),y0=gy|0,ty=gy-y0;for(let x=0;x<W;x++){const gx=Math.min(gw-1.001,Math.max(0,x/f-.5)),x0=gx|0,tx=gx-x0;
      const bg=Math.max(40,(g[y0*gw+x0]*(1-tx)+g[y0*gw+x0+1]*tx)*(1-ty)+(g[(y0+1)*gw+x0]*(1-tx)+g[(y0+1)*gw+x0+1]*tx)*ty),j=(y*W+x)*4;
      for(let c=0;c<3;c++){let v=o[j+c]/bg*255;v=(v-35)*255/(232-35);o[j+c]=v<0?0:v>255?255:v}}}}
  ctx.putImageData(im,0,0);
  // 手機照片的文字列常常是斜的、往下越歪越多：沿著文字列的方向把每一列拉平（歪得很少就不動）
  try{const st=await straighten(out);p.out=st.canvas;p.warp=st.info}catch(e){p.out=out}
  p._jpg=null;p.status="scanned"}

async function addFiles(files){for(const f of files){
  // PDF：每一頁畫成圖；有文字層的（電子檔）把文字層一起留著，提取時當第一個引擎
  if(f.type==="application/pdf"||/\.pdf$/i.test(f.name)){try{const pr=$("#prog");const ps=await pdfPages(f,t=>{if(pr)pr.textContent="讀取 "+t+"…"});
      for(const x of ps){const c=x.canvas;pages.push({name:`${f.name} 第 ${x.n} 頁`,src:c,thumb:c.toDataURL("image/jpeg",.5),q:[[0,0],[c.width,0],[c.width,c.height],[0,c.height]],clean:false,pdf:true,pdfText:x.text,out:null,status:"new"})}}
    catch(e){toast("PDF 讀不進來："+f.name+"（"+(e&&e.message||e)+"）")}continue}
  if(!f.type.startsWith("image/"))continue;try{
  const bmp=await createImageBitmap(f,{imageOrientation:"from-image"}).catch(()=>createImageBitmap(f));const k=Math.min(1,2400/Math.max(bmp.width,bmp.height));
  const c=document.createElement("canvas");c.width=Math.round(bmp.width*k);c.height=Math.round(bmp.height*k);c.getContext("2d").drawImage(bmp,0,0,c.width,c.height);
  const m=.02;pages.push({name:f.name,src:c,thumb:c.toDataURL("image/jpeg",.5),q:[[c.width*m,c.height*m],[c.width*(1-m),c.height*m],[c.width*(1-m),c.height*(1-m)],[c.width*m,c.height*(1-m)]],clean:true,out:null,status:"new"})}catch(e){toast("有一張圖讀不進來："+f.name)}}
  cur=Math.max(0,pages.length-1);showOut=false;renderUpload()}

/* ----- 提取引擎的選擇：主引擎＋複核引擎。預設兩個都是本機、免金鑰的；Claude 收在「進階」 ----- */
const engName=id=>{const e=getEngine(id);return e?e.label.replace(/（.*$/,""):""};
function fixEngines(){const ok=adv?ENGINES:FREE,ids=ok.map(e=>e.id);if(!ids.includes(engA))engA=ids[0];
  if(engB!=="none"&&(!ids.includes(engB)||engB===engA))engB=ids.find(x=>x!==engA)||"none"}
function engineHTML(){fixEngines();const list=adv?ENGINES:FREE,A=getEngine(engA),B=engB==="none"?null:getEngine(engB);
  const chips=(sel,attr,extra)=>list.map(e=>`<button class="chip ${sel===e.id?"on":""}" ${attr}="${e.id}">${esc(e.label)}</button>`).join("")+(extra||"");
  const dl=[A,B].filter(e=>e&&e.local).map(e=>`<span data-dl="${e.id}">${esc(engName(e.id))} ${e.size}</span>`).join("、");
  return`<div class="note eng" style="margin-top:16px"><b>提取方式：兩個引擎各讀一次，互相核對</b>
   <div class="small">兩邊讀的完全一樣才算「雙重確認」；有任何不同，都會請你對照原圖逐筆確認。${[A,B].every(e=>!e||e.local)?"兩個引擎都在這台裝置上執行，免金鑰、不花錢，照片不會上傳。":""}</div>
   <div class="engrow"><span class="small">主引擎</span><div class="chips">${chips(engA,"data-ea")}</div></div>
   <div class="engrow"><span class="small">複核引擎</span><div class="chips">${chips(engB,"data-eb",`<button class="chip ${engB==="none"?"on":""}" data-eb="none">不複核</button>`)}</div></div>
   ${dl?`<div class="small" style="margin-top:6px">第一次使用要下載辨識模型：${dl}。下載後存在瀏覽器裡，之後離線也能用。</div>`:""}
   ${B?"":`<div class="small warnline">只用一個引擎時沒有第二份讀法可以比對，所以每一筆都要你自己對照原圖按確認才能存入。</div>`}
   <details class="adv" id="adv" ${adv?"open":""}><summary>進階（需自備金鑰、會計費）</summary>
    <label class="row small" style="gap:6px;margin-top:6px"><input type="checkbox" id="adv-on" style="width:20px;min-height:20px" ${adv?"checked":""}>啟用 Claude AI 引擎（用你自己的 Anthropic API 金鑰，依用量向你的帳號收費）</label>
    ${adv?`<input id="key" type="password" autocomplete="off" placeholder="Anthropic API 金鑰 sk-ant-…" value="${esc(lsGet("vc-key",""))}" style="margin-top:6px"><div class="small" style="margin-top:4px">啟用後上面的引擎選項會多一個 Claude。金鑰只存在這個瀏覽器，照片會直接送到 api.anthropic.com。</div>`:""}
   </details></div>`}
// 已經下載過的模型標上「已下載」
function markCached(){FREE.forEach(e=>{if(e.cached)e.cached().then(ok=>{const el=document.querySelector(`[data-dl="${e.id}"]`);if(el&&ok)el.textContent=engName(e.id)+"（已下載）"}).catch(()=>{})})}

export function renderUpload(){
  app.innerHTML=`<h1>掃描上傳</h1><p class="sub">拍下單字書頁 → 拖動四個角對齊紙張 → 掃描（拉平＋去陰影）→ 兩個辨識引擎各讀一次並互相核對 → 你對照原圖確認後存進字典。</p>
  <label class="drop" id="drop"><input type="file" accept="image/*,application/pdf,.pdf" multiple id="file" class="hide"><b>選擇或拖入照片或 PDF</b><div class="small">可一次選多張，手機可直接拍照；PDF 每一頁都會讀</div></label>
  ${!review.length&&!pages.length&&readDraft()?`<div class="note" id="draft" style="margin-top:12px">上次有一份還沒存入字典的核對清單（${readDraft().review.length} 筆）。<div class="row" style="gap:8px;margin-top:8px"><button class="pri sm" id="d-load">還原，繼續核對</button><button class="sm ghost" id="d-drop">不要了，丟掉</button></div></div>`:""}
  ${pages.length?`<h2>頁面（${pages.length}）</h2><div class="thumbs" id="thumbs">${pages.map((p,i)=>`<button class="${i===cur?"on":""}" data-i="${i}" aria-label="第 ${i+1} 頁"><img src="${p.thumb}" alt=""><span class="st">${{new:"未掃描",scanned:"已掃描",done:"已提取",err:"失敗",busy:"處理中"}[p.status]}</span></button>`).join("")}</div>
  <div class="row" style="margin:12px 0"><button class="${showOut?"":"chip on"} sm" id="v-src">調整四角</button><button class="${showOut?"chip on":""} sm" id="v-out" ${pages[cur].out?"":"disabled"}>掃描結果</button>
   <label class="row small" style="gap:6px;margin-left:auto"><input type="checkbox" id="clean" style="width:20px;min-height:20px" ${pages[cur].clean?"checked":""}>去陰影、提亮</label></div>
  <div class="stage" id="stage"></div>
  <div class="row" style="margin-top:12px"><button id="reset" class="sm">四角重設</button><button id="rm" class="sm" style="color:var(--bad)">移除此頁</button><span style="flex:1"></span><button id="doscan">掃描這頁</button><button id="pdf" class="hide">下載掃描 PDF</button></div>
  ${engineHTML()}
  <div class="row" style="margin-top:14px"><button class="pri" id="extract" style="flex:1 1 260px">掃描全部並提取單字</button></div><p class="small" id="prog"></p>`:""}
  <div id="manual"><h2>手動貼上</h2><p class="small">也可以每行貼一個：英文 | 詞性 | 中文 | 例句</p><textarea id="paste" placeholder="abandon | v. | 放棄；拋棄 | The sailors abandoned the damaged ship."></textarea><button id="parse" class="sm" style="margin-top:8px">加入檢查清單</button></div>
  <div id="revbox"></div>`;
  $("#file").onchange=e=>addFiles(e.target.files);
  const dr=$("#drop");dr.ondragover=e=>{e.preventDefault();dr.style.borderColor="var(--or)"};dr.ondragleave=()=>dr.style.borderColor="";dr.ondrop=e=>{e.preventDefault();addFiles(e.dataTransfer.files)};
  $("#parse").onclick=()=>{$("#paste").value.split("\n").map(l=>l.split("|").map(s=>s.trim())).filter(a=>a[0]).forEach(a=>review.push(mk({en:a[0],pos:a[1],zh:a[2],ex:a[3]},null,{cs:"manual"})));$("#paste").value="";renderReview()};
  const dl=$("#d-load");if(dl){dl.onclick=restoreDraft;$("#d-drop").onclick=()=>{clearDraft();renderUpload()}}
  renderReview();
  if(!pages.length)return;
  $("#thumbs").onclick=e=>{const b=e.target.closest("[data-i]");if(b){cur=+b.dataset.i;showOut=!!pages[cur].out;renderUpload()}};
  $("#v-src").onclick=()=>{showOut=false;renderUpload()};$("#v-out").onclick=()=>{showOut=true;renderUpload()};
  $("#clean").onchange=e=>{pages[cur].clean=e.target.checked;if(pages[cur].out)scan(pages[cur]).then(renderUpload)};
  $("#reset").onclick=()=>{const p=pages[cur],c=p.src;p.q=[[0,0],[c.width,0],[c.width,c.height],[0,c.height]];p.out=null;p.status="new";showOut=false;renderUpload()};
  $("#rm").onclick=()=>{pages.splice(cur,1);cur=Math.max(0,cur-1);renderUpload()};
  $("#doscan").onclick=()=>{const b=$("#doscan");b.disabled=true;b.textContent="處理中…";const p=pages[cur];setTimeout(()=>scan(p).then(()=>{showOut=true;renderUpload()}),30)};
  $("#extract").onclick=extractAll;
  app.querySelectorAll("[data-ea]").forEach(b=>b.onclick=()=>{const old=engA;engA=b.dataset.ea;if(engB===engA)engB=old;saveEng();renderUpload()});
  app.querySelectorAll("[data-eb]").forEach(b=>b.onclick=()=>{const old=engB;engB=b.dataset.eb;if(engB===engA)engA=old==="none"?(adv?ENGINES:FREE).map(e=>e.id).find(x=>x!==engB):old;saveEng();renderUpload()});
  $("#adv-on").onchange=e=>{adv=e.target.checked;lsSet("vc-adv",adv?"1":"0");fixEngines();saveEng();renderUpload()};
  const ki=$("#key");if(ki)ki.onchange=()=>lsSet("vc-key",ki.value.trim());
  if(pages.some(p=>p.out)){const b=$("#pdf");b.classList.remove("hide");b.onclick=makePdf}
  markCached();drawStage()}
const saveEng=()=>{lsSet("vc-ext",engA);lsSet("vc-ext2",engB)};

function drawStage(){const p=pages[cur],st=$("#stage"),c=showOut&&p.out?p.out:p.src,cv=document.createElement("canvas");cv.width=c.width;cv.height=c.height;cv.getContext("2d").drawImage(c,0,0);st.innerHTML="";st.appendChild(cv);if(showOut&&p.out)return;
  const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox",`0 0 ${c.width} ${c.height}`);svg.setAttribute("preserveAspectRatio","none");st.appendChild(svg);
  const r=c.width/ (st.clientWidth||600),draw=()=>{svg.innerHTML=`<polygon points="${p.q.map(a=>a.join(",")).join(" ")}" fill="rgba(220,79,34,.12)" stroke="#dc4f22" stroke-width="${3*r}"/>`+p.q.map((a,i)=>`<circle data-c="${i}" cx="${a[0]}" cy="${a[1]}" r="${16*r}" fill="#dc4f22" stroke="#fff" stroke-width="${3*r}" style="cursor:grab"/>`).join("")};draw();
  let drag=-1;svg.onpointerdown=e=>{const pt=toImg(e);let best=-1,bd=1e9;p.q.forEach((a,i)=>{const dd=Math.hypot(a[0]-pt[0],a[1]-pt[1]);if(dd<bd){bd=dd;best=i}});if(bd<60*r){drag=best;svg.setPointerCapture(e.pointerId)}};
  svg.onpointermove=e=>{if(drag<0)return;const pt=toImg(e);p.q[drag]=[Math.max(0,Math.min(c.width,pt[0])),Math.max(0,Math.min(c.height,pt[1]))];p.out=null;p.status="new";draw()};
  svg.onpointerup=svg.onpointercancel=()=>{if(drag>=0){drag=-1;const b=$("#v-out");if(b)b.disabled=true}};
  function toImg(e){const b=svg.getBoundingClientRect();return[(e.clientX-b.left)/b.width*c.width,(e.clientY-b.top)/b.height*c.height]}}

/* ----- 提取：主引擎與複核引擎各讀一次 → consensus 逐筆比對（欄位＋原始文字）＋ 覆蓋率（還有哪些字沒被收進條目） ----- */
async function extractAll(){fixEngines();const A=getEngine(engA),B=engB==="none"?null:getEngine(engB);
  if(!A.ready()||(B&&!B.ready())){toast("請先在「進階」輸入 API 金鑰，或改用免金鑰的引擎");return}
  const btn=$("#extract"),prog=$("#prog");btn.disabled=true;let got=0,err="";const names={a:engName(engA),b:B?engName(engB):""};
  for(let i=0;i<pages.length;i++){const p=pages[i];if(p.status==="done")continue;const head=`第 ${i+1}/${pages.length} 頁：`;
    prog.textContent=head+"掃描中（拉平、去陰影）…";await new Promise(r=>setTimeout(r,20));if(!p.out)await scan(p);p.status="busy";
    const PDFE=p.pdfText?{id:"pdf",label:"PDF 文字層",local:true,extract:async()=>{const e=parseLayout(p.pdfText,{W:p.out.width,H:p.out.height});e.lines=p.pdfText;return e}}:null;
    const EA=PDFE||A,EB=PDFE?A:B;names.a=PDFE?"PDF 文字層":engName(engA);names.b=PDFE?engName(engA):(B?engName(engB):"");
    const st={a:"準備中…",b:"準備中…"},show=()=>{prog.textContent=head+`主引擎 ${names.a}：${st.a}`+(EB?`｜複核 ${names.b}：${st.b}`:"")};show();
    const run=(E,k)=>E.extract(p.out,{onProgress:t=>{st[k]=t.replace(/^[^：]{1,12}：/,"");show()}}).then(r=>{st[k]="完成";show();const l=(r||[]).filter(x=>x&&x.en);l.lines=r&&r.lines;l.cover=r&&r.cover;return l},e=>{st[k]="失敗";show();throw e});
    let [ra,rb]=await Promise.allSettled([run(EA,"a"),EB?run(EB,"b"):Promise.reject(new Error("none"))]);
    // 測試用掛鉤（只在開發模式存在，正式建置會整段拿掉）：window.__vcScanTamper(which:"a"|"b", entries, pageIndex) 回傳要改成的條目
    if(import.meta.env.DEV){const tam=globalThis.__vcScanTamper,keep=(r,v)=>{v.lines=r.value.lines;v.cover=r.value.cover;r.value=v};if(tam){if(ra.status==="fulfilled")keep(ra,tam("a",ra.value,i)||ra.value);if(rb.status==="fulfilled")keep(rb,tam("b",rb.value,i)||rb.value)}}
    const msg=r=>String(r.reason&&r.reason.message||r.reason||""),uni=(x,y)=>[...new Set([...(x&&x.flags||[]),...(y&&y.flags||[])])];
    if(ra.status==="fulfilled"&&rb.status==="fulfilled"){const a=ra.value,b=rb.value;
      // 位置優先用本機 OCR 引擎量到的（Claude 的位置是估的）
      for(const it of consensus(a,b,{rawA:a.cover?a.cover.boxes:a.lines,rawB:b.cover?b.cover.boxes:b.lines,W:p.out.width,H:p.out.height})){const bb=it.a&&it.b?((EA.local?it.a.bbox:null)||(EB.local?it.b.bbox:null)||it.a.bbox||it.b.bbox):it.entry.bbox;
        review.push(mk({...it.entry,bbox:bb,flags:uni(it.a,it.b),unsure:!!((it.a&&it.a.unsure)||(it.b&&it.b.unsure))},p,{cs:it.status,cmp:it.fields?{a:it.a,b:it.b,fields:it.fields,bad:it.bad}:null,raw:it.raw||null,names}));got++}
      p.cov=leftovers(a.cover,b.cover);p.status="done"}
    else if(ra.status==="fulfilled"||rb.status==="fulfilled"){const okA=ra.status==="fulfilled",list=okA?ra.value:rb.value;
      const why=!EB?"沒有選複核引擎":okA?`複核引擎（${names.b}）這一頁失敗：${msg(rb)}`:`主引擎（${names.a}）這一頁失敗：${msg(ra)}`;
      list.forEach(x=>{review.push(mk(x,p,{cs:"single",why,names:{a:okA?names.a:names.b,b:""}}));got++});p.cov=leftovers(list.cover,null);p.status="done"}
    else{p.status="err";err=msg(ra);if(/api.key|auth|401/i.test(err))break}
    if(p.cov){p.cov.W=p.out.width;p.cov.H=p.out.height;p.cov.left.forEach(l=>l.state="todo");p.names=names;p.expect=""}}
  renderUpload();const pr=$("#prog");
  if(pr){const n=review.filter(w=>w.cs==="agree"&&w.raw&&w.raw.same).length;pr.textContent=got?`提取到 ${got} 個條目，其中 ${n} 筆兩個引擎讀的完全一樣；其餘請在下方對照原圖逐筆確認。`:("沒有提取到條目。"+(err?"錯誤："+err:"可以調整四角後重試。"))}
  if(got)$("#revbox").scrollIntoView({behavior:"smooth"})}
const mk=(x,pg,o={})=>({id:rid(),en:String(x.en||"").trim(),pos:String(x.pos||"").trim(),zh:String(x.zh||"").trim(),ex:String(x.ex||"").trim(),blank:String(x.blank||"").trim(),unit:String(x.unit||"").trim(),keep:true,bbox:x.bbox||null,pg:pg||null,unsure:!!x.unsure,
  flags:Array.isArray(x.flags)?x.flags:[],cs:o.cs||"manual",cmp:o.cmp||null,raw:o.raw||null,names:o.names||{a:"",b:""},why:o.why||"",pick:{},touched:false,okd:false});
// 從掃描圖裁一塊畫到 canvas 上（座標是整頁百分比；沒有左右範圍就裁整頁寬）
function cropTo(cv,src,b,maxW){let y0=0,y1=src.height,x0=0,x1=src.width;
  if(b){const pad=src.height*.015;y0=Math.max(0,b.y0/100*src.height-pad);y1=Math.min(src.height,b.y1/100*src.height+pad);
    if(b.x0!=null){const px=src.width*.03;x0=Math.max(0,b.x0/100*src.width-px);x1=Math.min(src.width,b.x1/100*src.width+px)}}
  const h=Math.max(8,y1-y0),sw=Math.max(8,x1-x0),k=Math.min(1,maxW/sw);cv.width=Math.round(sw*k);cv.height=Math.round(h*k);cv.getContext("2d").drawImage(src,x0,y0,sw,h,0,0,cv.width,cv.height)}
// 在每筆旁邊畫出它在掃描圖上的位置：有 bbox 就裁切該區塊，沒有就顯示整頁縮圖
function drawCrops(only){document.querySelectorAll("canvas[data-crop]").forEach(cv=>{const w=review[+cv.dataset.crop],src=w&&w.pg&&w.pg.out;if(!src||(only&&w!==only))return;cropTo(cv,src,w.bbox,w.bbox?900:420)});
  if(!only)drawPages()}
// 每頁的「沒被收進條目的文字」：整頁縮圖上框出來（紅＝待處理、灰＝已處理），每一段再各裁一張小圖
function drawPages(){document.querySelectorAll("canvas[data-map]").forEach(cv=>{const p=pages[+cv.dataset.map],src=p&&p.out;if(!src||!p.cov)return;const k=Math.min(1,760/src.width);cv.width=Math.round(src.width*k);cv.height=Math.round(src.height*k);
    const g=cv.getContext("2d");g.drawImage(src,0,0,cv.width,cv.height);g.lineWidth=3;
    p.cov.left.forEach((l,j)=>{const todo=l.state==="todo";g.strokeStyle=todo?"#d1202a":"#8a8a8a";g.fillStyle=todo?"rgba(209,32,42,.12)":"rgba(120,120,120,.10)";const x=l.x0*k-3,y=l.y0*k-3,w=(l.x1-l.x0)*k+6,h=(l.y1-l.y0)*k+6;g.fillRect(x,y,w,h);g.strokeRect(x,y,w,h);
      g.fillStyle=todo?"#d1202a":"#8a8a8a";g.font="bold 13px sans-serif";g.fillText(String(j+1),Math.max(2,x-14),y+13)})});
  document.querySelectorAll("canvas[data-lcrop]").forEach(cv=>{const [pi,j]=cv.dataset.lcrop.split(":").map(Number),p=pages[pi],l=p&&p.cov&&p.cov.left[j];if(!l||!p.out)return;const W=p.cov.W,H=p.cov.H;
    cropTo(cv,p.out,{x0:l.x0/W*100,x1:l.x1/W*100,y0:l.y0/H*100,y1:l.y1/H*100},700)})}

/* ----- 規則檢查（詞表拼字、例句字形、版面疑點…）＋ Google 翻譯核對 ----- */
const tmo=(p,ms)=>Promise.race([p,new Promise((_,no)=>setTimeout(()=>no(new Error("timeout")),ms))]);
async function verifyOne(w){w.chk="busy";w.msg=[];w.g=null;w.gnote="";paintV(w);
  const lex=await loadLexicon().catch(()=>null),warn=ruleWarnings(w,lex,{manual:w.cs==="manual"});let na=false;
  try{if(w.en){const g=await tmo(gtrans(sayable(w.en)),8000);w.g=[...new Set([g.main,...g.dict])].filter(Boolean).slice(0,8);
      if(!/[㐀-鿿]/.test(g.main)&&!g.dict.length)warn.push("Google 不認得這個英文，可能拼錯");
      else if(w.zh){const a=new Set(cjk(w.zh)),b=new Set(cjk(w.g.join(""))),common=[...a].filter(c=>b.has(c)).length;
        // 中文以書上（圖片）為準：和 Google 翻譯說法不同只當參考，不擋存入
        if(a.size&&common===0)w.gnote="Google 翻譯的說法和書上不同（以書上為準，僅供參考）";else if(a.size>=4&&common<2&&common/a.size<.2)w.gnote="Google 翻譯的說法和書上差很多（以書上為準，僅供參考）"}}
  }catch(e){na=true;w.g=null}
  w.chk=warn.length?"warn":na?"na":"ok";w.msg=warn;paintV(w);paintSum()}
// 最多 4 筆同時核對（結果寫在置頂摘要，不另外跳訊息蓋住卡片）
async function verifyAll(){const q=review.filter(w=>!w.chk);q.forEach(w=>w.chk="queued");paintSum();let k=0;const run=async()=>{while(k<q.length){const w=q[k++];await verifyOne(w)}};await Promise.all([run(),run(),run(),run()])}

/* ----- 存入門檻 -----
   不用人工就能存入的只有一種「雙重確認」：兩個引擎解析出來的每一欄（含單元）都一樣、這一筆範圍裡兩邊的原始文字也逐字一樣、
   版面上沒有疑點、提取後沒被改過、規則檢查與 Google 核對都通過。（自己手動貼上的條目沒有原圖可比，規則檢查通過即可，但不算雙重確認。）
   其餘每一筆都要按「確認」或取消勾選；每頁沒被收進條目的文字也要逐段處理；填了書上的筆數就要對得上。否則不能存入。 */
const pending=w=>!w.chk||w.chk==="busy"||w.chk==="queued";
const rawOk=w=>!!(w.raw&&w.raw.same);
// 只差在單元標籤、而且使用者已經在那一頁上方選定哪個標籤才對：其餘欄位仍然是兩邊一致，視同雙重確認
const unitOnly=w=>w.cs==="diff"&&w.cmp&&w.cmp.bad.length===1&&w.cmp.bad[0]==="unit";
const auto=w=>w.chk==="ok"&&(w.cs==="manual"||((w.cs==="agree"||(unitOnly(w)&&w.unitOk))&&!w.touched&&rawOk(w)));
const needs=w=>w.keep&&!w.okd&&!auto(w);
const pageCount=p=>review.filter(w=>w.pg===p&&w.keep).length;
const pageTodo=p=>p.cov?p.cov.left.filter(l=>l.state==="todo").length:0;
const pageBadCount=p=>p.cov&&p.expect!==""&&p.expect!=null&&+p.expect!==pageCount(p);
// 這筆為什麼要人工確認（顯示在卡片上）
function reasons(w){const r=[];
  if(unitOnly(w)&&!w.touched)r.push("兩個引擎讀到的單元標籤不一樣（其他欄位都一樣）：請在這一頁最上面選正確的單元");
  else if(w.cs==="diff")r.push(w.touched||Object.keys(w.pick).length?"兩個引擎讀的不一樣（你已選邊或修改）":"兩個引擎讀的不一樣");
  else if(w.cs==="onlyA"||w.cs==="onlyB")r.push(`只有${w.cs==="onlyA"?"主引擎":"複核引擎"}（${w.cs==="onlyA"?w.names.a:w.names.b}）讀到這一筆，另一個引擎沒讀到或讀成別的`);
  else if(w.cs==="single")r.push("這一筆只有一個引擎讀過（"+w.why+"），沒有第二份讀法可以比對");
  else if(w.cs==="added")r.push("這一筆是你從「沒被收進條目的文字」新增的，請把各欄位填好並對照原圖");
  else if(w.cs==="agree"&&w.touched)r.push("提取後內容被修改過");
  if((w.cs==="agree"||w.cs==="diff")&&!w.touched){if(!w.raw)r.push("這組引擎沒有提供原始文字，沒辦法逐字比對原圖上的這一塊");
    else if(!w.raw.same)r.push(w.cs==="agree"?"欄位內容兩邊一樣，但這一筆範圍裡兩個引擎讀到的原始文字不完全一樣（多半是例句翻譯、音標或附註）":"這一筆範圍裡兩個引擎讀到的原始文字不一樣")}
  if(w.chk==="warn")r.push(...w.msg);if(w.chk==="na")r.push("連不到 Google 翻譯，沒辦法核對中文");
  return r}
function badge(w){if(!w.keep)return['off',"不存入"];if(w.okd)return['okd',"已人工確認"];
  if(w.cs==="manual")return auto(w)?['man',"手動輸入・檢查通過"]:pending(w)?['wait',"手動輸入・檢查中"]:['bad',"需確認"];
  if(auto(w))return['ok',"雙重確認"];
  if(w.cs==="onlyA"||w.cs==="onlyB")return['one',"只有一邊讀到"];
  if(w.cs==="single")return['one',"需確認・單一引擎"];
  if(w.cs==="added")return['one',"你新增的・需確認"];
  if(w.cs==="agree"&&!w.touched&&rawOk(w)&&pending(w))return['wait',"兩邊一致・規則檢查中"];
  return['bad',"需確認"]}
const segs=(parts)=>parts&&parts.length?parts.map(([t,d])=>d?`<mark class="dfc">${esc(t)}</mark>`:esc(t)).join(""):'<span class="small">（空白）</span>';
// 兩種讀法並排、差異字元標色；點其中一邊就採用那一邊
function diffHTML(w){if(w.cs!=="diff"||!w.cmp)return"";const c=w.cmp;
  const rows=c.bad.map(k=>{const f=c.fields[k],cell=(s)=>`<button type="button" class="dfv ${w.pick[k]===s?"on":""}" data-pick="${s}" data-f="${k}" aria-label="採用${s==="a"?w.names.a:w.names.b}讀到的${FIELD_NAME[k]}"><span class="who">${esc(s==="a"?w.names.a:w.names.b)}${w.pick[k]===s?"　✓ 已採用":""}</span><span class="val">${segs(f.diff[s])}</span></button>`;
    return`<div class="dfrow"><div class="dfk">${FIELD_NAME[k]}</div>${cell("a")}${cell("b")}</div>`}).join("");
  return`<div class="f6 wide df"><div class="small">兩個引擎讀的不一樣（標色的是不同的字）。對照上面的原圖，點正確的那一邊；都不對就直接在下面改。</div>${rows}
   <div class="row" style="gap:6px;margin-top:6px"><button class="sm" data-a="useA">全部採用 ${esc(w.names.a)}</button><button class="sm" data-a="useB">全部採用 ${esc(w.names.b)}</button></div></div>`}
// 原始文字不一致時，把兩個引擎在這一塊讀到的原文並排（只給看，不能點）
function rawHTML(w){if(!w.raw||w.raw.same||!w.raw.diff)return"";const cell=s=>`<div class="dfv ro"><span class="who">${esc(s==="a"?w.names.a:w.names.b)}</span><span class="val">${segs(w.raw.diff[s])}</span></div>`;
  return`<details class="f6 wide df raw" ${w.cs==="agree"?"open":""}><summary class="small">這一塊的原始文字，兩個引擎讀的不完全一樣（標色的是不同的字；包含不存入的例句翻譯、音標、附註）</summary><div class="dfrow"><div class="dfk">原文</div>${cell("a")}${cell("b")}</div></details>`}
function vHTML(w){const g=w.g&&w.g.length?`<div class="small">Google 翻譯：${esc(w.g.join("、"))}${w.gnote?"・"+esc(w.gnote):""}</div>`:"";
  if(pending(w))return'<span class="small">規則檢查與 Google 翻譯核對中…</span>';
  if(!w.keep)return'<div class="small">已取消勾選，不會存入。</div>';
  if(w.okd)return`<div class="small" style="color:var(--ok)">✓ 你已對照原圖確認這一筆</div>${g}<button class="sm" data-a="unokd" style="margin-top:6px">取消確認</button>`;
  if(auto(w))return`<div class="small" style="color:var(--ok)">✓ ${w.cs==="manual"?"規則檢查通過，":"兩個引擎讀的完全一樣（欄位與原始文字），規則檢查也通過，"}${w.gnote?"中文照書上的":"與 Google 翻譯相符"}</div>${g}`;
  const r=reasons(w),soft=w.chk!=="warn";
  return`<div class="why ${soft?"soft":""}">${soft?"需要你確認":"⚠ 可能有錯"}：<ul>${r.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>${g}
   <div class="row" style="gap:6px;margin-top:6px"><button class="sm pri" data-a="okd">我已對照原圖，確認這筆正確</button><button class="sm" data-a="recheck">重新檢查</button><button class="sm ghost" data-a="drop">不存這筆</button></div>`}
function cardHTML(w,i,dup){const f=(k,l,c)=>`<label class="${c}"><span class="small">${l}</span><input data-i="${i}" data-k="${k}" value="${esc(w[k])}" class="${k==="en"&&dup?"dup":""}"></label>`,[bc,bt]=badge(w);
  // 例句用可換行的多行欄位（手機上一行放不下）
  const ta=(k,l,c)=>`<label class="${c}"><span class="small">${l}</span><textarea data-i="${i}" data-k="${k}" rows="2">${esc(w[k])}</textarea></label>`;
  return`<div class="rc st-${bc}" id="rc-${i}" data-i="${i}"><div class="f6 wide rchead"><span class="badge b-${bc}" id="bd-${i}">${bt}</span><span style="flex:1"></span>${spkBtn(w.en)}<label class="row small keepl"><input type="checkbox" class="ck" data-i="${i}" data-k="keep" ${w.keep?"checked":""}>存入</label></div>
   ${w.pg&&w.pg.out?`<div class="f6 wide crop"><span class="small">${w.bbox?"掃描圖上的這一筆（請對照）":"這筆沒有位置資訊，顯示整頁掃描圖"}</span><canvas data-crop="${i}" class="${w.bbox?"":"whole"}"></canvas></div>`:""}
   ${diffHTML(w)}${rawHTML(w)}${f("en","英文","f3 wide")}${f("pos","詞性","f1")}${f("unit","單元","f2")}${f("zh","中文","f6 wide")}${ta("ex","例句","f6 wide")}${f("blank","克漏字答案（例句裡的字形）","f6 wide")}
   <div class="f6 wide" id="vs-${i}" data-i="${i}">${vHTML(w)}</div></div>`}
// 沒被收進條目的文字要收進哪一筆：同一頁、在它上方、左右位置對得上的最後一筆
function mergeTarget(p,l){const W=p.cov.W,H=p.cov.H,cx=(l.x0+l.x1)/2/W*100,cy=(l.y0+l.y1)/2/H*100,c=review.filter(w=>w.pg===p&&w.keep&&w.bbox&&w.bbox.y0<=cy);
  const inx=c.filter(w=>w.bbox.x0==null||(cx>=w.bbox.x0-3&&cx<=Math.max(w.bbox.x1,w.bbox.x0+45)));return(inx.length?inx:c).sort((a,b)=>b.bbox.y0-a.bbox.y0)[0]||null}
// 這一頁還沒選定的單元標籤差異（兩個引擎讀到的單元不同），同一組差異只問一次
function unitPairs(p){const m=new Map();for(const w of review){if(w.pg!==p||!w.keep||!w.cmp||!w.cmp.bad.includes("unit")||w.unitOk||w.pick.unit)continue;const f=w.cmp.fields.unit,k=f.a+" ⇄ "+f.b;if(!m.has(k))m.set(k,{a:f.a,b:f.b,n:0});m.get(k).n++}return[...m.values()]}
function pickUnit(p,k,side){const u=unitPairs(p)[k];if(!u)return;for(const w of review){if(w.pg!==p||!w.cmp||!w.cmp.bad.includes("unit"))continue;const f=w.cmp.fields.unit;if(f.a!==u.a||f.b!==u.b||w.unitOk||w.pick.unit)continue;w.unit=f[side];w.pick.unit=side;w.unitOk=true}renderReview()}
const latinMajor=t=>(t.match(/[A-Za-z]/g)||[]).length>(t.match(/[㐀-鿿]/g)||[]).length;
// 每一頁的面板：讀到幾筆（請使用者對照書上的筆數）＋還沒被收進條目的文字
function pageHTML(p,pi){if(!p.cov)return"";const n=pageCount(p),cov=p.cov,todo=pageTodo(p),bad=pageBadCount(p),nm=p.names||{a:"",b:""};
  const item=(l,j)=>{const t=l.state==="todo"?mergeTarget(p,l):null;
    return`<div class="loi st-${l.state}" data-p="${pi}" data-j="${j}"><div class="lon">${j+1}</div><div class="lob"><canvas data-lcrop="${pi}:${j}"></canvas><div class="lotx">${esc(l.text)}</div>
      ${l.textB&&l.textB!==l.text?`<div class="small">${esc(nm.b)}讀成：${esc(l.textB)}</div>`:""}${l.from==="b"?`<div class="small">（只有複核引擎 ${esc(nm.b)} 讀到這一段）</div>`:""}
      ${l.state==="todo"?`<div class="row" style="gap:6px;margin-top:6px"><button class="sm" data-l="add">新增成條目</button>${t?`<button class="sm" data-l="merge">收進「${esc(t.en)}」的${latinMajor(l.text)?"例句":"中文"}</button>`:""}<button class="sm ghost" data-l="ignore">不是單字內容，忽略</button></div>`
        :`<div class="row small" style="gap:6px;margin-top:4px">${{ignored:"已忽略",added:"已新增成條目（在清單裡，請填好並確認）",merged:"已收進「"+esc(l.into||"")+"」"}[l.state]}${l.state==="ignored"?'<button class="sm ghost" data-l="undo">復原</button>':""}</div>`}</div></div>`};
  return`<div class="pp ${todo||bad?"todo":"done"}" id="pp-${pi}" data-p="${pi}">
    <div class="pphead"><b>第 ${pi+1} 頁：讀到 ${n} 筆</b><label class="small">書上這一頁實際有幾筆？請數一下：<input type="number" inputmode="numeric" min="0" data-expect="${pi}" value="${esc(p.expect||"")}" placeholder="筆數"></label></div>
    ${bad?`<div class="warnline">你數到 ${esc(p.expect)} 筆，但清單裡這一頁是 ${n} 筆。請找出${+p.expect>n?"漏掉":"多出來"}的條目（對照下面的原圖），補上、刪掉或把數字改對之後才能存入。</div>`:""}
    ${unitPairs(p).map((u,k)=>`<div class="upick"><div class="small"><b>單元標籤兩個引擎讀的不一樣</b>（影響 ${u.n} 筆）。請對照原圖點正確的那個，這一頁會一起套用：</div><div class="row" style="gap:6px;margin-top:6px"><button class="sm" data-u="a" data-k="${k}">${esc(nm.a)}：${esc(u.a||"（沒有）")}</button><button class="sm" data-u="b" data-k="${k}">${esc(nm.b)}：${esc(u.b||"（沒有）")}</button></div></div>`).join("")}
    ${cov.left.length?`<div class="lo"><div class="lohd">頁面上還有沒被收進條目的文字：${todo} 段待處理（共 ${cov.left.length} 段）</div><div class="small">下圖紅框是辨識到、但沒有放進任何一筆的文字（可能是漏掉的條目，或被切斷的例句）。每一段都要處理完才能存入：新增成條目、收進前一筆，或確定不是單字內容後按忽略。</div>
      <canvas class="lomap" data-map="${pi}"></canvas>${cov.left.map(item).join("")}</div>`:`<div class="small" style="color:var(--ok)">✓ 這一頁辨識到的文字都已經收進條目${cov.skipped.length?"（頁首、頁尾、頁碼除外）":""}。</div>`}
    ${cov.skipped.length?`<details class="small"><summary>自動略過的頁首、頁尾、頁碼（${cov.skipped.length} 段，點開檢查）</summary>${cov.skipped.map(s=>esc(s.text)).join("　｜　")}</details>`:""}</div>`}
// 只重畫狀態區與徽章（核對結果回來時用，不動輸入框，打字不會被打斷）
function paintV(w){const i=review.indexOf(w),el=$("#vs-"+i);if(!el)return;el.innerHTML=vHTML(w);const c=$("#rc-"+i),b=$("#bd-"+i),[bc,bt]=badge(w);if(c)c.className="rc st-"+bc;if(b){b.className="badge b-"+bc;b.textContent=bt}}
const grow=root=>(root||document).querySelectorAll(".rev textarea").forEach(t=>{t.style.height="auto";t.style.height=Math.max(44,t.scrollHeight+2)+"px"});
// 整張卡片重畫（選邊、勾選存入時）
function paintCard(w){const i=review.indexOf(w),el=$("#rc-"+i);if(!el)return;const t=document.createElement("div");t.innerHTML=cardHTML(w,i,el.querySelector("input.dup"));const n=t.firstElementChild;el.replaceWith(n);grow(n);drawCrops(w);paintPage(w.pg);paintSum()}
// 重畫某一頁的面板（筆數、沒被收進條目的文字）
function paintPage(p){const pi=pages.indexOf(p),el=$("#pp-"+pi);if(pi<0||!el)return;const f=document.activeElement&&document.activeElement.dataset&&document.activeElement.dataset.expect===String(pi);
  const t=document.createElement("div");t.innerHTML=pageHTML(p,pi);el.replaceWith(t.firstElementChild);drawPages();if(f){const inp=$(`[data-expect="${pi}"]`);if(inp){inp.focus();const v=inp.value;inp.value="";inp.value=v}}}
function paintSum(){const el=$("#vsum");if(!el)return;const kept=review.filter(w=>w.keep),n=kept.filter(needs).length,busy=kept.filter(pending).length,c=k=>kept.filter(w=>badge(w)[0]===k).length;
  const single=kept.find(w=>w.cs==="single"),left=pages.reduce((t,p)=>t+pageTodo(p),0),cnt=pages.filter(pageBadCount).length,blocked=n+left+cnt,man=c("man");
  el.className="vsum "+(blocked?"todo":"done");const hd=document.querySelector("header");el.style.top=((hd&&getComputedStyle(hd).position==="sticky"?hd.offsetHeight:0)+4)+"px"; // 釘在頁首導覽列下面
  const todo=[n?`${n} 筆條目要確認`:"",left?`${left} 段沒被收進條目的文字要處理`:"",cnt?`${cnt} 頁的筆數和你數的不一樣`:""].filter(Boolean).join("、");
  el.innerHTML=`<div class="tallies"><span class="badge b-ok">雙重確認 ${c("ok")}</span><span class="badge b-bad">需確認 ${c("bad")+c("wait")}</span><span class="badge b-one">只有一邊／單一引擎 ${c("one")}</span><span class="badge b-okd">已人工確認 ${c("okd")}</span>${man?`<span class="badge b-man">手動輸入 ${man}</span>`:""}</div>
   <div>${busy?`正在做規則檢查與 Google 翻譯核對…（剩 ${busy} 筆）`:blocked?`<b style="color:var(--bad)">還有 ${todo}</b><span class="long">：條目要逐筆對照原圖按「確認」或取消「存入」的勾選；沒被收進條目的文字要逐段處理。全部做完才能存進字典。</span> <button class="sm" id="nexttodo">跳到下一個</button>`:"✓ 每一筆都是雙重確認或已經人工確認，頁面上的文字也都處理完了，可以存入。"}</div>
   ${single?`<div class="small warnline">有些條目只有一個引擎讀過（${esc(single.why)}），沒有第二份讀法可以互相核對，所以這些條目每一筆都要你對照原圖確認。</div>`:""}`;
  const nb=$("#nexttodo");if(nb)nb.onclick=gotoTodo;
  const sb=$("#savebtn");if(sb)sb.textContent=blocked?`存入字典（還有 ${blocked} 項要處理）`:"存入字典";
  const h=$("#revcount");if(h)h.textContent=`${kept.length}/${review.length}`;
  pages.forEach((p,pi)=>{const b=$("#pp-"+pi+" .pphead b");if(b)b.textContent=`第 ${pi+1} 頁：讀到 ${pageCount(p)} 筆`});
  touchDraft()}
let todoAt=-1;
// 跳到下一個要處理的地方（頁面面板或卡片），捲到置頂摘要的下面，卡片上方的原圖裁切會留在畫面內
function gotoTodo(){const els=[...document.querySelectorAll("#rev .pp.todo, #rev .rc")].filter(e=>e.classList.contains("pp")||needs(review[+e.dataset.i]));if(!els.length)return;
  todoAt=(todoAt+1)%els.length;const el=els[todoAt],hd=document.querySelector("header"),vs=$("#vsum"),off=(hd&&getComputedStyle(hd).position==="sticky"?hd.offsetHeight:0)+(vs?vs.offsetHeight:0)+14;
  window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY-off,behavior:"smooth"});el.classList.add("flash");setTimeout(()=>el.classList.remove("flash"),1200)}
function adopt(w,side,keys){keys=keys.slice();
  // 克漏字答案是從英文和例句推出來的：英文或例句選了某一邊，克漏字答案也跟著用那一邊的（可以再另外點）
  if(keys.length===1&&(keys[0]==="en"||keys[0]==="ex")&&w.cmp.bad.includes("blank"))keys.push("blank");
  for(const k of keys){const f=w.cmp.fields[k];if(!f)continue;w[k]=f[side];w.pick[k]=side}
  w.okd=false;w.touched=true;paintCard(w);verifyOne(w)}
// 處理一段沒被收進條目的文字：add 新增成條目、merge 收進前一筆、ignore 忽略、undo 復原
function leftAct(pi,j,act){const p=pages[pi],l=p&&p.cov&&p.cov.left[j];if(!l)return;
  if(act==="ignore")l.state="ignored";else if(act==="undo")l.state="todo";
  else if(act==="merge"){const t=mergeTarget(p,l);if(!t)return;const k=latinMajor(l.text)?"ex":"zh";t[k]=(t[k]+(k==="ex"?" ":"")+l.text).trim();t.touched=true;t.okd=false;l.state="merged";l.into=t.en;renderReview();verifyOne(t);return}
  else if(act==="add"){const W=p.cov.W,H=p.cov.H,h=parseHead(tidy(l.text)),lat=latinMajor(l.text);
    const w=mk({en:h?h.en:lat?l.text:"",pos:h?h.pos:"",zh:h?h.zh:lat?"":l.text,bbox:{x0:l.x0/W*100,x1:l.x1/W*100,y0:l.y0/H*100,y1:l.y1/H*100}},p,{cs:"added",names:p.names});
    // 插在同一頁、位置在它上方的最後一筆後面
    const t=mergeTarget(p,l),at=t?review.indexOf(t)+1:Math.max(0,review.findIndex(x=>x.pg===p));review.splice(at,0,w);l.state="added";renderReview();const el=$("#rc-"+review.indexOf(w));if(el)el.scrollIntoView({behavior:"smooth",block:"center"});return}
  paintPage(p);paintSum()}
function renderReview(){const box=$("#revbox");if(!box)return;if(!review.length&&!pages.some(p=>p.cov&&p.cov.left.length)){box.innerHTML="";touchDraft();return}
  const seen={},D=allDicts(),exist=new Set();Object.values(D).forEach(d=>d.words.forEach(w=>exist.add(w.en.toLowerCase())));let lastPg;
  box.innerHTML=`<h2>核對清單（<span id="revcount">${review.filter(r=>r.keep).length}/${review.length}</span>）</h2><p class="small">每筆都附上掃描圖上的原始位置。綠色「雙重確認」代表兩個引擎讀的完全一樣、拼字與翻譯檢查也通過；其他顏色的每一筆都要你對照原圖按確認（或取消勾選）才能存入。每一頁開頭會列出讀到幾筆、還有哪些文字沒被收進條目，請對照書上數一數。橘框的英文代表已經在某本字典裡出現過。</p><div id="vsum"></div>
  <div class="rev" id="rev">${review.map((w,i)=>{const dup=exist.has(w.en.toLowerCase())||seen[w.en.toLowerCase()];seen[w.en.toLowerCase()]=1;let pre="";if(w.pg!==lastPg){lastPg=w.pg;const pi=pages.indexOf(w.pg);if(pi>=0)pre=pageHTML(w.pg,pi)}return pre+cardHTML(w,i,dup)}).join("")
    +pages.map((p,pi)=>p.cov&&!review.some(w=>w.pg===p)?pageHTML(p,pi):"").join("")}</div>
  <div class="cut" style="margin-top:16px">${SC}<div class="tab"><span>SAVE</span></div><div class="body"><div class="row"><label style="flex:1 1 200px"><span class="small">存到</span><select id="target"><option value="__new">＋ 新字典</option>${Object.values(D).map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("")}</select></label>
   <label style="flex:1 1 200px" id="nmw"><span class="small">新字典名稱</span><input id="newname" value="${esc("單字 "+new Date().toLocaleDateString("zh-TW"))}"></label></div>
   <div class="warnline hide" id="saveerr"></div>
   <div class="row" style="margin-top:12px"><button class="pri" id="savebtn">存入字典</button><button id="clear" class="sm ghost">清空清單</button></div></div></div>`;
  paintSum();grow();drawCrops();
  const R=$("#rev");
  // 改過內容：雙重確認不再成立，之前按過的確認也作廢，要重新確認
  R.oninput=e=>{const t=e.target;if(t.dataset.expect!=null){pages[+t.dataset.expect].expect=t.value.trim();return}const i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k||k==="keep")return;const w=review[i];w[k]=t.value;if(t.tagName==="TEXTAREA")grow(t.closest(".rc"));if(!w.touched||w.okd){w.touched=true;w.okd=false;paintV(w);paintSum()}else touchDraft()};
  R.onchange=e=>{const t=e.target;if(t.dataset.expect!=null){const p=pages[+t.dataset.expect];p.expect=t.value.trim();paintPage(p);paintSum();return}const i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k)return;const w=review[i];if(k==="keep"){w.keep=t.checked;paintCard(w);return}w[k]=t.value.trim();if(k!=="unit")verifyOne(w);else paintSum()};
  R.onclick=e=>{const ub=e.target.closest("button[data-u]");if(ub){pickUnit(pages[+ub.closest(".pp").dataset.p],+ub.dataset.k,ub.dataset.u);return}
    const lb=e.target.closest("button[data-l]");if(lb){const it=lb.closest(".loi");leftAct(+it.dataset.p,+it.dataset.j,lb.dataset.l);return}
    const pk=e.target.closest("button[data-pick]");if(pk){const w=review[+pk.closest(".rc").dataset.i];adopt(w,pk.dataset.pick,[pk.dataset.f]);return}
    const b=e.target.closest("button[data-a]");if(!b)return;const w=review[+b.closest(".rc").dataset.i],a=b.dataset.a;
    if(a==="recheck")verifyOne(w);else if(a==="okd"){w.okd=true;paintCard(w)}else if(a==="unokd"){w.okd=false;paintCard(w)}else if(a==="drop"){w.keep=false;paintCard(w)}
    else if(a==="useA"||a==="useB")adopt(w,a==="useA"?"a":"b",w.cmp.bad)};
  $("#target").onchange=e=>$("#nmw").classList.toggle("hide",e.target.value!=="__new");
  $("#clear").onclick=async()=>{if(await ask("清空所有尚未儲存的提取結果？")){review=[];pages.forEach(p=>{p.cov=null});renderReview()}};
  $("#savebtn").onclick=()=>{const kept=review.filter(w=>w.keep&&w.en),fail=m=>{const e=$("#saveerr");e.textContent=m;e.classList.remove("hide")};if(!kept.length){toast("沒有要儲存的條目");return}
    if(kept.some(pending)){toast("規則檢查還沒跑完，請稍等一下");return}
    // 存入門檻：還有沒處理的就不能存，沒有「直接存入」的捷徑
    const n=review.filter(needs).length,left=pages.reduce((t,p)=>t+pageTodo(p),0),cnt=pages.filter(pageBadCount).length;
    if(n||left||cnt){fail(`還不能存入：${[n?`${n} 筆條目沒有確認`:"",left?`${left} 段沒被收進條目的文字沒處理`:"",cnt?`${cnt} 頁的筆數和你數的不一樣`:""].filter(Boolean).join("、")}。`);todoAt=-1;gotoTodo();return}
    const ws=kept.map(w=>({id:w.id,en:w.en,pos:w.pos,zh:w.zh,ex:w.ex,blank:w.blank,unit:w.unit}));
    let id=$("#target").value,created=false;if(id==="__new"){id=rid();S.dicts[id]={id,name:$("#newname").value.trim()||"新字典",words:[]};created=true}const d=ownDict(id),before=d.words.length;d.words.push(...ws);
    // 寫不進 localStorage（空間滿了）：把剛加的拿掉、核對清單原封不動留著，明講沒有存成功
    if(!save()){d.words.length=before;if(created)delete S.dicts[id];fail(`存入失敗：瀏覽器的儲存空間不足，這 ${ws.length} 筆沒有存進字典。核對清單還留在這裡，請先到「字典」刪掉不用的字典或匯出備份，再回來按一次存入。`);return}
    review=[];pages=[];clearDraft();toast(`已存入 ${ws.length} 個條目`,2600);location.hash="dict-"+id};
  if(review.some(w=>!w.chk))verifyAll()}

/* ----- 還沒存入的核對清單：暫存在 sessionStorage，重新整理或誤關分頁後可以還原；離開前先警告 ----- */
const DK="vc-scan-draft";let dT=0;
const clearDraft=()=>{clearTimeout(dT);try{sessionStorage.removeItem(DK)}catch(e){}};
function saveDraft(){try{if(!review.length){sessionStorage.removeItem(DK);return}
    const ps=pages.map(p=>({name:p.name,cov:p.cov||null,expect:p.expect||"",names:p.names||null,img:p.out?(p._jpg||(p._jpg=p.out.toDataURL("image/jpeg",.78))):null}));
    const data={t:Date.now(),pages:ps,review:review.map(({pg,chk,msg,g,...w})=>({...w,pgi:pages.indexOf(pg)}))};
    let s=JSON.stringify(data);if(s.length>4.2e6){data.pages.forEach(p=>{p.img=null});s=JSON.stringify(data)}   // 掃描圖太大就只存文字（還原後沒有原圖裁切）
    sessionStorage.setItem(DK,s)}catch(e){}}
function touchDraft(){clearTimeout(dT);dT=setTimeout(saveDraft,700)}
const readDraft=()=>{try{const d=JSON.parse(sessionStorage.getItem(DK)||"null");return d&&Array.isArray(d.review)&&d.review.length?d:null}catch(e){return null}};
async function restoreDraft(){const d=readDraft();if(!d)return;
  const ps=await Promise.all(d.pages.map(async p=>{let c=null;if(p.img){try{const im=new Image();im.src=p.img;await im.decode();c=document.createElement("canvas");c.width=im.naturalWidth;c.height=im.naturalHeight;c.getContext("2d").drawImage(im,0,0)}catch(e){c=null}}
    if(!c){c=document.createElement("canvas");c.width=c.height=8}
    return{name:p.name,src:c,thumb:p.img||c.toDataURL(),q:[[0,0],[c.width,0],[c.width,c.height],[0,c.height]],clean:false,out:p.img?c:null,_jpg:p.img,status:"done",cov:p.cov,expect:p.expect,names:p.names}}));
  pages=ps;cur=0;showOut=true;review=d.review.map(({pgi,...w})=>({...w,pg:pgi>=0?pages[pgi]:null}));renderUpload()}
if(typeof window!=="undefined")window.addEventListener("beforeunload",e=>{if(review.length){saveDraft();e.preventDefault();e.returnValue=""}});

async function makePdf(){const b=$("#pdf");b.disabled=true;b.textContent="產生中…";try{
  if(!window.jspdf)await loadScript("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js");
  const ps=pages.filter(p=>p.out);let doc=null;for(const p of ps){const w=p.out.width,h=p.out.height,o=w>h?"l":"p";if(!doc)doc=new window.jspdf.jsPDF({unit:"px",format:[w,h],orientation:o,hotfixes:["px_scaling"]});else doc.addPage([w,h],o);doc.addImage(p.out.toDataURL("image/jpeg",.85),"JPEG",0,0,w,h)}
  doc.save("單字掃描.pdf");toast("PDF 已下載")}catch(e){toast("PDF 沒有下載成功")}b.disabled=false;b.textContent="下載掃描 PDF"}
