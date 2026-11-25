// 掃描上傳：載入照片 → 調四角 → 透視校正＋去陰影 → 兩個引擎各提取一次並交叉比對 → 規則檢查＋Google 翻譯核對 → 逐筆人工確認後存入
// 設計見 docs/掃描強化設計.md：一筆條目只有「兩個獨立引擎讀的完全一樣而且規則檢查通過」或「使用者對著原圖確認過」才能存入。
import { $, app, esc, rid, toast, ask, SC, loadScript, lsGet, lsSet } from '../core/util.js';
import { S, save, allDicts, ownDict } from '../core/store.js';
import { sayable, gtrans, cjk } from '../core/grading.js';
import { spkBtn } from '../core/speech.js';
import { ENGINES, FREE, getEngine } from '../scan/engines/index.js';
import { consensus, FIELD_NAME } from '../scan/consensus.js';
import { ruleWarnings } from '../scan/rules.js';
import { loadLexicon } from '../scan/wordlist.js';

// engA／engB：主引擎與複核引擎（"none"＝不複核）；adv：有沒有打開「進階」裡的 Claude
let pages=[],cur=0,review=[],showOut=true,engA=lsGet("vc-ext","ppocr"),engB=lsGet("vc-ext2","ocr"),adv=lsGet("vc-adv","0")==="1";

/* ----- 透視校正：由四角解 3×3 單應矩陣（8 元線性方程） ----- */
export function solve(A,b){const n=b.length;for(let i=0;i<n;i++){let p=i;for(let r=i+1;r<n;r++)if(Math.abs(A[r][i])>Math.abs(A[p][i]))p=r;[A[i],A[p]]=[A[p],A[i]];[b[i],b[p]]=[b[p],b[i]];for(let r=i+1;r<n;r++){const f=A[r][i]/A[i][i];for(let c=i;c<n;c++)A[r][c]-=f*A[i][c];b[r]-=f*b[i]}}const x=Array(n);for(let i=n-1;i>=0;i--){let s=b[i];for(let c=i+1;c<n;c++)s-=A[i][c]*x[c];x[i]=s/A[i][i]}return x}
export function homog(src,dst){const A=[],b=[];for(let i=0;i<4;i++){const[x,y]=src[i],[u,v]=dst[i];A.push([x,y,1,0,0,0,-u*x,-u*y]);b.push(u);A.push([0,0,0,x,y,1,-v*x,-v*y]);b.push(v)}return solve(A,b)}
function scan(p){const q=p.q,d=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  let W=Math.max(d(q[0],q[1]),d(q[3],q[2])),H=Math.max(d(q[0],q[3]),d(q[1],q[2]));const k=Math.min(1,2000/Math.max(W,H));W=Math.round(W*k);H=Math.round(H*k);
  const h=homog([[0,0],[W,0],[W,H],[0,H]],q),sc=p.src,sw=sc.width,sh=sc.height,sd=sc.getContext("2d").getImageData(0,0,sw,sh).data;
  const out=document.createElement("canvas");out.width=W;out.height=H;const ctx=out.getContext("2d"),im=ctx.createImageData(W,H),o=im.data;
  // 雙線性取樣
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const w=h[6]*x+h[7]*y+1,sx=(h[0]*x+h[1]*y+h[2])/w,sy=(h[3]*x+h[4]*y+h[5])/w;
    const x0=Math.max(0,Math.min(sw-2,sx|0)),y0=Math.max(0,Math.min(sh-2,sy|0)),fx=Math.min(1,Math.max(0,sx-x0)),fy=Math.min(1,Math.max(0,sy-y0)),i=(y0*sw+x0)*4,j=(y*W+x)*4;
    for(let c=0;c<3;c++){const a=sd[i+c]*(1-fx)+sd[i+4+c]*fx,b=sd[i+sw*4+c]*(1-fx)+sd[i+sw*4+4+c]*fx;o[j+c]=a*(1-fy)+b*fy}o[j+3]=255}
  // 去陰影：每 16 px 一格取最大亮度當背景，一次 3×3 最大值、三次 3×3 平均，再把 35–232 拉伸到 0–255
  if(p.clean){const f=16,gw=Math.ceil(W/f),gh=Math.ceil(H/f);let g=new Float32Array(gw*gh);
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){const j=(y*W+x)*4,L=.3*o[j]+.59*o[j+1]+.11*o[j+2],gi=(y/f|0)*gw+(x/f|0);if(L>g[gi])g[gi]=L}
    for(let pass=0;pass<4;pass++){const n=new Float32Array(gw*gh);for(let y=0;y<gh;y++)for(let x=0;x<gw;x++){let s=0,c=0,m=0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const yy=y+dy,xx=x+dx;if(yy<0||xx<0||yy>=gh||xx>=gw)continue;const v=g[yy*gw+xx];s+=v;c++;if(v>m)m=v}n[y*gw+x]=pass<1?m:s/c}g=n}
    for(let y=0;y<H;y++){const gy=Math.min(gh-1.001,Math.max(0,y/f-.5)),y0=gy|0,ty=gy-y0;for(let x=0;x<W;x++){const gx=Math.min(gw-1.001,Math.max(0,x/f-.5)),x0=gx|0,tx=gx-x0;
      const bg=Math.max(40,(g[y0*gw+x0]*(1-tx)+g[y0*gw+x0+1]*tx)*(1-ty)+(g[(y0+1)*gw+x0]*(1-tx)+g[(y0+1)*gw+x0+1]*tx)*ty),j=(y*W+x)*4;
      for(let c=0;c<3;c++){let v=o[j+c]/bg*255;v=(v-35)*255/(232-35);o[j+c]=v<0?0:v>255?255:v}}}}
  ctx.putImageData(im,0,0);p.out=out;p.status="scanned"}

async function addFiles(files){for(const f of files){if(!f.type.startsWith("image/"))continue;try{
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
  <label class="drop" id="drop"><input type="file" accept="image/*" multiple id="file" class="hide"><b>選擇或拖入照片</b><div class="small">可一次選多張，手機可直接拍照</div></label>
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
  renderReview();
  if(!pages.length)return;
  $("#thumbs").onclick=e=>{const b=e.target.closest("[data-i]");if(b){cur=+b.dataset.i;showOut=!!pages[cur].out;renderUpload()}};
  $("#v-src").onclick=()=>{showOut=false;renderUpload()};$("#v-out").onclick=()=>{showOut=true;renderUpload()};
  $("#clean").onchange=e=>{pages[cur].clean=e.target.checked;if(pages[cur].out){scan(pages[cur]);renderUpload()}};
  $("#reset").onclick=()=>{const p=pages[cur],c=p.src;p.q=[[0,0],[c.width,0],[c.width,c.height],[0,c.height]];p.out=null;p.status="new";showOut=false;renderUpload()};
  $("#rm").onclick=()=>{pages.splice(cur,1);cur=Math.max(0,cur-1);renderUpload()};
  $("#doscan").onclick=()=>{const b=$("#doscan");b.disabled=true;b.textContent="處理中…";setTimeout(()=>{scan(pages[cur]);showOut=true;renderUpload()},30)};
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

/* ----- 提取：主引擎與複核引擎各讀一次 → consensus 逐筆比對 ----- */
// 測試用掛鉤：window.__vcScanTamper(which:"a"|"b", entries, pageIndex) 回傳要改成的條目（自動化測試拿來故意改錯一邊）
async function extractAll(){fixEngines();const A=getEngine(engA),B=engB==="none"?null:getEngine(engB);
  if(!A.ready()||(B&&!B.ready())){toast("請先在「進階」輸入 API 金鑰，或改用免金鑰的引擎");return}
  const btn=$("#extract"),prog=$("#prog");btn.disabled=true;let got=0,err="";const names={a:engName(engA),b:B?engName(engB):""};
  for(let i=0;i<pages.length;i++){const p=pages[i];if(p.status==="done")continue;const head=`第 ${i+1}/${pages.length} 頁：`;
    prog.textContent=head+"掃描中…";await new Promise(r=>setTimeout(r,20));if(!p.out)scan(p);p.status="busy";
    const st={a:"準備中…",b:"準備中…"},show=()=>{prog.textContent=head+`主引擎 ${names.a}：${st.a}`+(B?`｜複核 ${names.b}：${st.b}`:"")};show();
    const run=(E,k)=>E.extract(p.out,{onProgress:t=>{st[k]=t.replace(/^[^：]{1,12}：/,"");show()}}).then(r=>{st[k]="完成";show();return(r||[]).filter(x=>x&&x.en)},e=>{st[k]="失敗";show();throw e});
    let [ra,rb]=await Promise.allSettled([run(A,"a"),B?run(B,"b"):Promise.reject(new Error("none"))]);
    const tam=globalThis.__vcScanTamper;if(tam){if(ra.status==="fulfilled")ra.value=tam("a",ra.value,i)||ra.value;if(rb.status==="fulfilled")rb.value=tam("b",rb.value,i)||rb.value}
    const msg=r=>String(r.reason&&r.reason.message||r.reason||"");
    if(ra.status==="fulfilled"&&rb.status==="fulfilled"){
      // 位置優先用本機 OCR 引擎量到的（Claude 的位置是估的）
      for(const it of consensus(ra.value,rb.value)){const bb=it.a&&it.b?((A.local?it.a.bbox:null)||(B.local?it.b.bbox:null)||it.a.bbox||it.b.bbox):it.entry.bbox;
        review.push(mk({...it.entry,bbox:bb,unsure:!!((it.a&&it.a.unsure)||(it.b&&it.b.unsure))},p,{cs:it.status,cmp:it.fields?{a:it.a,b:it.b,fields:it.fields,bad:it.bad}:null,names}));got++}
      p.status="done"}
    else if(ra.status==="fulfilled"||rb.status==="fulfilled"){const okA=ra.status==="fulfilled",list=okA?ra.value:rb.value;
      const why=!B?"沒有選複核引擎":okA?`複核引擎（${names.b}）這一頁失敗：${msg(rb)}`:`主引擎（${names.a}）這一頁失敗：${msg(ra)}`;
      list.forEach(x=>{review.push(mk(x,p,{cs:"single",why,names:{a:okA?names.a:names.b,b:""}}));got++});p.status="done"}
    else{p.status="err";err=msg(ra);if(/api.key|auth|401/i.test(err))break}}
  renderUpload();const pr=$("#prog");
  if(pr){const n=review.filter(w=>w.cs==="agree").length;pr.textContent=got?`提取到 ${got} 個條目，其中 ${n} 筆兩個引擎讀的完全一樣；其餘請在下方對照原圖逐筆確認。`:("沒有提取到條目。"+(err?"錯誤："+err:"可以調整四角後重試。"))}
  if(got)$("#revbox").scrollIntoView({behavior:"smooth"})}
const mk=(x,pg,o={})=>({id:rid(),en:String(x.en||"").trim(),pos:String(x.pos||"").trim(),zh:String(x.zh||"").trim(),ex:String(x.ex||"").trim(),blank:String(x.blank||"").trim(),unit:String(x.unit||"").trim(),keep:true,bbox:x.bbox||null,pg:pg||null,unsure:!!x.unsure,
  cs:o.cs||"manual",cmp:o.cmp||null,names:o.names||{a:"",b:""},why:o.why||"",pick:{},touched:false,okd:false});
// 在每筆旁邊畫出它在掃描圖上的位置：有 bbox 就裁切該區塊（有左右範圍就連左右一起裁，手機上字才夠大），沒有就顯示整頁縮圖
function drawCrops(only){document.querySelectorAll("canvas[data-crop]").forEach(cv=>{const w=review[+cv.dataset.crop],src=w&&w.pg&&w.pg.out;if(!src||(only&&w!==only))return;let y0=0,y1=src.height,x0=0,x1=src.width;
  if(w.bbox){const pad=src.height*.015;y0=Math.max(0,w.bbox.y0/100*src.height-pad);y1=Math.min(src.height,w.bbox.y1/100*src.height+pad);
    if(w.bbox.x0!=null){const px=src.width*.03;x0=Math.max(0,w.bbox.x0/100*src.width-px);x1=Math.min(src.width,w.bbox.x1/100*src.width+px)}}
  const h=Math.max(8,y1-y0),sw=Math.max(8,x1-x0),k=Math.min(1,(w.bbox?900:420)/sw);cv.width=Math.round(sw*k);cv.height=Math.round(h*k);cv.getContext("2d").drawImage(src,x0,y0,sw,h,0,0,cv.width,cv.height)})}

/* ----- 規則檢查（詞表拼字、例句字形…）＋ Google 翻譯核對 ----- */
const tmo=(p,ms)=>Promise.race([p,new Promise((_,no)=>setTimeout(()=>no(new Error("timeout")),ms))]);
async function verifyOne(w){w.chk="busy";w.msg=[];w.g=null;paintV(w);
  const lex=await loadLexicon().catch(()=>null),warn=ruleWarnings(w,lex,{manual:w.cs==="manual"});let na=false;
  try{if(w.en){const g=await tmo(gtrans(sayable(w.en)),8000);w.g=[...new Set([g.main,...g.dict])].filter(Boolean).slice(0,8);
      if(!/[㐀-鿿]/.test(g.main)&&!g.dict.length)warn.push("Google 不認得這個英文，可能拼錯");
      else if(w.zh){const a=new Set(cjk(w.zh)),b=new Set(cjk(w.g.join(""))),common=[...a].filter(c=>b.has(c)).length;
        if(a.size&&common===0)warn.push("中文和 Google 翻譯完全對不上");else if(a.size>=4&&common<2&&common/a.size<.2)warn.push("中文和 Google 翻譯差很多")}}
  }catch(e){na=true;w.g=null}
  w.chk=warn.length?"warn":na?"na":"ok";w.msg=warn;paintV(w);paintSum()}
// 最多 4 筆同時核對
async function verifyAll(){const q=review.filter(w=>!w.chk);q.forEach(w=>w.chk="queued");paintSum();let k=0;const run=async()=>{while(k<q.length){const w=q[k++];await verifyOne(w)}};await Promise.all([run(),run(),run(),run()]);
  const n=review.filter(needs).length;if(n)toast(`有 ${n} 筆需要你對照原圖確認`)}

/* ----- 存入門檻 -----
   不用人工就能存入的只有一種：兩個引擎每一欄都讀得一樣（雙重確認）、提取後沒被改過、而且規則檢查與 Google 核對都通過。
   （自己手動貼上的條目沒有原圖可比，規則檢查通過即可。）其餘每一筆都要按「確認」或取消勾選，否則不能存入。 */
const pending=w=>!w.chk||w.chk==="busy"||w.chk==="queued";
const auto=w=>w.chk==="ok"&&(w.cs==="manual"||(w.cs==="agree"&&!w.touched));
const needs=w=>w.keep&&!w.okd&&!auto(w);
// 這筆為什麼要人工確認（顯示在卡片上）
function reasons(w){const r=[];
  if(w.cs==="diff")r.push(w.touched||Object.keys(w.pick).length?"兩個引擎讀的不一樣（你已選邊或修改）":"兩個引擎讀的不一樣");
  else if(w.cs==="onlyA"||w.cs==="onlyB")r.push(`只有${w.cs==="onlyA"?"主引擎":"複核引擎"}（${w.cs==="onlyA"?w.names.a:w.names.b}）讀到這一筆，另一個引擎沒讀到或讀成別的`);
  else if(w.cs==="single")r.push("這一筆只有一個引擎讀過（"+w.why+"），沒有第二份讀法可以比對");
  else if(w.cs==="agree"&&w.touched)r.push("提取後內容被修改過");
  if(w.chk==="warn")r.push(...w.msg);if(w.chk==="na")r.push("連不到 Google 翻譯，沒辦法核對中文");
  return r}
function badge(w){if(!w.keep)return['off',"不存入"];if(w.okd)return['okd',"已人工確認"];
  if(auto(w))return w.cs==="manual"?['ok',"手動輸入・檢查通過"]:['ok',"雙重確認"];
  if(w.cs==="onlyA"||w.cs==="onlyB")return['one',"只有一邊讀到"];
  if(w.cs==="single")return['one',"需確認・單一引擎"];
  if(w.cs==="agree"&&!w.touched&&pending(w))return['wait',"雙重確認・規則檢查中"];
  return['bad',"需確認"]}
const segs=(parts)=>parts&&parts.length?parts.map(([t,d])=>d?`<mark class="dfc">${esc(t)}</mark>`:esc(t)).join(""):'<span class="small">（空白）</span>';
// 兩種讀法並排、差異字元標色；點其中一邊就採用那一邊
function diffHTML(w){if(w.cs!=="diff"||!w.cmp)return"";const c=w.cmp;
  const rows=c.bad.map(k=>{const f=c.fields[k],cell=(s)=>`<button type="button" class="dfv ${w.pick[k]===s?"on":""}" data-pick="${s}" data-f="${k}" aria-label="採用${s==="a"?w.names.a:w.names.b}讀到的${FIELD_NAME[k]}"><span class="who">${esc(s==="a"?w.names.a:w.names.b)}${w.pick[k]===s?"　✓ 已採用":""}</span><span class="val">${segs(f.diff[s])}</span></button>`;
    return`<div class="dfrow"><div class="dfk">${FIELD_NAME[k]}</div>${cell("a")}${cell("b")}</div>`}).join("");
  return`<div class="f6 wide df"><div class="small">兩個引擎讀的不一樣（標色的是不同的字）。對照上面的原圖，點正確的那一邊；都不對就直接在下面改。</div>${rows}
   <div class="row" style="gap:6px;margin-top:6px"><button class="sm" data-a="useA">全部採用 ${esc(w.names.a)}</button><button class="sm" data-a="useB">全部採用 ${esc(w.names.b)}</button></div></div>`}
function vHTML(w){const g=w.g&&w.g.length?`<div class="small">Google 翻譯：${esc(w.g.join("、"))}</div>`:"";
  if(pending(w))return'<span class="small">規則檢查與 Google 翻譯核對中…</span>';
  if(!w.keep)return'<div class="small">已取消勾選，不會存入。</div>';
  if(w.okd)return`<div class="small" style="color:var(--ok)">✓ 你已對照原圖確認這一筆</div>${g}<button class="sm" data-a="unokd" style="margin-top:6px">取消確認</button>`;
  if(auto(w))return`<div class="small" style="color:var(--ok)">✓ ${w.cs==="manual"?"規則檢查通過，":"兩個引擎讀的完全一樣，規則檢查也通過，"}與 Google 翻譯相符</div>${g}`;
  const r=reasons(w),soft=w.chk!=="warn";
  return`<div class="why ${soft?"soft":""}">${soft?"需要你確認":"⚠ 可能有錯"}：<ul>${r.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>${g}
   <div class="row" style="gap:6px;margin-top:6px"><button class="sm pri" data-a="okd">我已對照原圖，確認這筆正確</button><button class="sm" data-a="recheck">重新檢查</button><button class="sm ghost" data-a="drop">不存這筆</button></div>`}
function cardHTML(w,i,dup){const f=(k,l,c)=>`<label class="${c}"><span class="small">${l}</span><input data-i="${i}" data-k="${k}" value="${esc(w[k])}" class="${k==="en"&&dup?"dup":""}"></label>`,[bc,bt]=badge(w);
  const u=w.cmp&&w.cmp.a&&w.cmp.b&&(w.cmp.a.unit||"")!==(w.cmp.b.unit||"")?`<div class="f6 wide small unote">單元標籤兩邊讀的不同：${esc(w.names.a)}「${esc(w.cmp.a.unit||"（無）")}」／${esc(w.names.b)}「${esc(w.cmp.b.unit||"（無）")}」，請確認下面的單元。</div>`:"";
  return`<div class="rc st-${bc}" id="rc-${i}" data-i="${i}"><div class="f6 wide rchead"><span class="badge b-${bc}" id="bd-${i}">${bt}</span><span style="flex:1"></span>${spkBtn(w.en)}<label class="row small" style="gap:6px"><input type="checkbox" data-i="${i}" data-k="keep" ${w.keep?"checked":""} style="width:20px;min-height:20px">存入</label></div>
   ${w.pg&&w.pg.out?`<div class="f6 wide crop"><span class="small">${w.bbox?"掃描圖上的這一筆（請對照）":"這筆沒有位置資訊，顯示整頁掃描圖"}</span><canvas data-crop="${i}" class="${w.bbox?"":"whole"}"></canvas></div>`:""}
   ${diffHTML(w)}${f("en","英文","f3 wide")}${f("pos","詞性","f1")}${f("unit","單元","f2")}${f("zh","中文","f6 wide")}${f("ex","例句","f6 wide")}${f("blank","克漏字答案（例句裡的字形）","f6 wide")}${u}
   <div class="f6 wide" id="vs-${i}" data-i="${i}">${vHTML(w)}</div></div>`}
// 只重畫狀態區與徽章（核對結果回來時用，不動輸入框，打字不會被打斷）
function paintV(w){const i=review.indexOf(w),el=$("#vs-"+i);if(!el)return;el.innerHTML=vHTML(w);const c=$("#rc-"+i),b=$("#bd-"+i),[bc,bt]=badge(w);if(c)c.className="rc st-"+bc;if(b){b.className="badge b-"+bc;b.textContent=bt}}
// 整張卡片重畫（選邊、勾選存入時）
function paintCard(w){const i=review.indexOf(w),el=$("#rc-"+i);if(!el)return;const t=document.createElement("div");t.innerHTML=cardHTML(w,i,el.querySelector("input.dup"));el.replaceWith(t.firstElementChild);drawCrops(w);paintSum()}
function paintSum(){const el=$("#vsum");if(!el)return;const kept=review.filter(w=>w.keep),n=kept.filter(needs).length,busy=kept.filter(pending).length,c=k=>kept.filter(w=>badge(w)[0]===k).length;
  const single=kept.find(w=>w.cs==="single");
  el.className="vsum "+(n?"todo":"done");const hd=document.querySelector("header");el.style.top=((hd&&getComputedStyle(hd).position==="sticky"?hd.offsetHeight:0)+4)+"px"; // 釘在頁首導覽列下面
  el.innerHTML=`<div class="tallies"><span class="badge b-ok">雙重確認 ${c("ok")}</span><span class="badge b-bad">需確認 ${c("bad")+c("wait")}</span><span class="badge b-one">只有一邊／單一引擎 ${c("one")}</span><span class="badge b-okd">已人工確認 ${c("okd")}</span></div>
   <div>${busy?`正在做規則檢查與 Google 翻譯核對…（剩 ${busy} 筆）`:n?`<b style="color:var(--bad)">還有 ${n} 筆要處理</b><span class="long">：每一筆都要對照原圖按「確認」，或取消「存入」的勾選，才能存進字典。</span> <button class="sm" id="nexttodo">跳到下一筆</button>`:"✓ 每一筆都是雙重確認或已經人工確認，可以存入。"}</div>
   ${single?`<div class="small warnline">有些條目只有一個引擎讀過（${esc(single.why)}），沒有第二份讀法可以互相核對，所以這些條目每一筆都要你對照原圖確認。</div>`:""}`;
  const nb=$("#nexttodo");if(nb)nb.onclick=gotoTodo;
  const sb=$("#savebtn");if(sb)sb.textContent=n?`存入字典（還有 ${n} 筆要確認）`:"存入字典";
  const h=$("#revcount");if(h)h.textContent=`${kept.length}/${review.length}`}
let todoAt=-1;
function gotoTodo(){const idx=review.map((w,i)=>needs(w)?i:-1).filter(i=>i>=0);if(!idx.length)return;todoAt=idx.find(i=>i>todoAt)??idx[0];const el=$("#rc-"+todoAt);if(el){el.scrollIntoView({behavior:"smooth",block:"center"});el.classList.add("flash");setTimeout(()=>el.classList.remove("flash"),1200)}}
function adopt(w,side,keys){keys=keys.slice();
  // 克漏字答案是從英文和例句推出來的：英文或例句選了某一邊，克漏字答案也跟著用那一邊的（可以再另外點）
  if(keys.length===1&&(keys[0]==="en"||keys[0]==="ex")&&w.cmp.bad.includes("blank"))keys.push("blank");
  for(const k of keys){const f=w.cmp.fields[k];if(!f)continue;w[k]=f[side];w.pick[k]=side}
  w.okd=false;w.touched=true;paintCard(w);verifyOne(w)}
function renderReview(){const box=$("#revbox");if(!box)return;if(!review.length){box.innerHTML="";return}
  const seen={},D=allDicts(),exist=new Set();Object.values(D).forEach(d=>d.words.forEach(w=>exist.add(w.en.toLowerCase())));
  box.innerHTML=`<h2>核對清單（<span id="revcount">${review.filter(r=>r.keep).length}/${review.length}</span>）</h2><p class="small">每筆都附上掃描圖上的原始位置。綠色「雙重確認」代表兩個引擎讀的完全一樣、拼字與翻譯檢查也通過；其他顏色的每一筆都要你對照原圖按確認（或取消勾選）才能存入。橘框的英文代表已經在某本字典裡出現過。</p><div id="vsum"></div>
  <div class="rev" id="rev">${review.map((w,i)=>{const dup=exist.has(w.en.toLowerCase())||seen[w.en.toLowerCase()];seen[w.en.toLowerCase()]=1;return cardHTML(w,i,dup)}).join("")}</div>
  <div class="cut" style="margin-top:16px">${SC}<div class="tab"><span>SAVE</span></div><div class="body"><div class="row"><label style="flex:1 1 200px"><span class="small">存到</span><select id="target"><option value="__new">＋ 新字典</option>${Object.values(D).map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("")}</select></label>
   <label style="flex:1 1 200px" id="nmw"><span class="small">新字典名稱</span><input id="newname" value="${esc("單字 "+new Date().toLocaleDateString("zh-TW"))}"></label></div>
   <div class="row" style="margin-top:12px"><button class="pri" id="savebtn">存入字典</button><button id="clear" class="sm ghost">清空清單</button></div></div></div>`;
  paintSum();drawCrops();
  const R=$("#rev");
  // 改過內容：雙重確認不再成立，之前按過的確認也作廢，要重新確認
  R.oninput=e=>{const t=e.target,i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k||k==="keep")return;const w=review[i];w[k]=t.value;if(k!=="unit"&&(!w.touched||w.okd)){w.touched=true;w.okd=false;paintV(w);paintSum()}};
  R.onchange=e=>{const t=e.target,i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k)return;const w=review[i];if(k==="keep"){w.keep=t.checked;paintCard(w);return}w[k]=t.value.trim();if(k!=="unit")verifyOne(w)};
  R.onclick=e=>{const pk=e.target.closest("button[data-pick]");if(pk){const w=review[+pk.closest(".rc").dataset.i];adopt(w,pk.dataset.pick,[pk.dataset.f]);return}
    const b=e.target.closest("button[data-a]");if(!b)return;const w=review[+b.closest(".rc").dataset.i],a=b.dataset.a;
    if(a==="recheck")verifyOne(w);else if(a==="okd"){w.okd=true;paintCard(w)}else if(a==="unokd"){w.okd=false;paintCard(w)}else if(a==="drop"){w.keep=false;paintCard(w)}
    else if(a==="useA"||a==="useB")adopt(w,a==="useA"?"a":"b",w.cmp.bad)};
  $("#target").onchange=e=>$("#nmw").classList.toggle("hide",e.target.value!=="__new");
  $("#clear").onclick=async()=>{if(await ask("清空所有尚未儲存的提取結果？")){review=[];renderReview()}};
  $("#savebtn").onclick=()=>{const kept=review.filter(w=>w.keep&&w.en);if(!kept.length){toast("沒有要儲存的條目");return}
    if(kept.some(pending)){toast("規則檢查還沒跑完，請稍等一下");return}
    // 存入門檻：還有沒確認的就不能存，沒有「直接存入」的捷徑
    const n=review.filter(needs).length;if(n){toast(`還有 ${n} 筆沒有確認，不能存入。請逐筆按確認，或取消勾選。`);todoAt=-1;gotoTodo();return}
    const ws=kept.map(w=>({id:w.id,en:w.en,pos:w.pos,zh:w.zh,ex:w.ex,blank:w.blank,unit:w.unit}));
    let id=$("#target").value;if(id==="__new"){id=rid();S.dicts[id]={id,name:$("#newname").value.trim()||"新字典",words:[]}}const d=ownDict(id);d.words.push(...ws);save();review=[];pages=[];toast(`已存入 ${ws.length} 個條目`);location.hash="dict-"+id};
  if(review.some(w=>!w.chk))verifyAll()}

async function makePdf(){const b=$("#pdf");b.disabled=true;b.textContent="產生中…";try{
  if(!window.jspdf)await loadScript("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js");
  const ps=pages.filter(p=>p.out);let doc=null;for(const p of ps){const w=p.out.width,h=p.out.height,o=w>h?"l":"p";if(!doc)doc=new window.jspdf.jsPDF({unit:"px",format:[w,h],orientation:o,hotfixes:["px_scaling"]});else doc.addPage([w,h],o);doc.addImage(p.out.toDataURL("image/jpeg",.85),"JPEG",0,0,w,h)}
  doc.save("單字掃描.pdf");toast("PDF 已下載")}catch(e){toast("PDF 沒有下載成功")}b.disabled=false;b.textContent="下載掃描 PDF"}
