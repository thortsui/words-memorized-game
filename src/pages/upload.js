// 掃描上傳：載入照片 → 調四角 → 透視校正＋去陰影 → 提取（Claude 或 OCR）→ Google 翻譯核對 → 人工確認存入
import { $, app, esc, rid, toast, ask, SC, loadScript, lsGet, lsSet } from '../core/util.js';
import { S, save, allDicts, ownDict } from '../core/store.js';
import { isPhrase, clozeAns, sayable, gtrans, cjk } from '../core/grading.js';
import { spkBtn } from '../core/speech.js';
import { ENGINES, getEngine } from '../scan/engines/index.js';

let pages=[],cur=0,review=[],showOut=true,ext=lsGet("vc-ext","claude");

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

export function renderUpload(){
  app.innerHTML=`<h1>掃描上傳</h1><p class="sub">拍下單字書頁 → 拖動四個角對齊紙張 → 掃描（拉平＋去陰影）→ AI 提取單字 → 你檢查後存進字典。</p>
  <label class="drop" id="drop"><input type="file" accept="image/*" multiple id="file" class="hide"><b>選擇或拖入照片</b><div class="small">可一次選多張，手機可直接拍照</div></label>
  ${pages.length?`<h2>頁面（${pages.length}）</h2><div class="thumbs" id="thumbs">${pages.map((p,i)=>`<button class="${i===cur?"on":""}" data-i="${i}" aria-label="第 ${i+1} 頁"><img src="${p.thumb}" alt=""><span class="st">${{new:"未掃描",scanned:"已掃描",done:"已提取",err:"失敗",busy:"處理中"}[p.status]}</span></button>`).join("")}</div>
  <div class="row" style="margin:12px 0"><button class="${showOut?"":"chip on"} sm" id="v-src">調整四角</button><button class="${showOut?"chip on":""} sm" id="v-out" ${pages[cur].out?"":"disabled"}>掃描結果</button>
   <label class="row small" style="gap:6px;margin-left:auto"><input type="checkbox" id="clean" style="width:20px;min-height:20px" ${pages[cur].clean?"checked":""}>去陰影、提亮</label></div>
  <div class="stage" id="stage"></div>
  <div class="row" style="margin-top:12px"><button id="reset" class="sm">四角重設</button><button id="rm" class="sm" style="color:var(--bad)">移除此頁</button><span style="flex:1"></span><button id="doscan">掃描這頁</button><button id="pdf" class="hide">下載掃描 PDF</button></div>
  <div class="note" style="margin-top:16px"><b>提取方式</b><div class="chips" style="margin:8px 0">${ENGINES.map(e=>[e.id,e.label]).map(([v,l])=>`<button class="chip ${ext===v?"on":""}" data-ext="${v}">${l}</button>`).join("")}</div>
   ${ext==="claude"?`<input id="key" type="password" autocomplete="off" placeholder="Anthropic API 金鑰 sk-ant-…" value="${esc(lsGet("vc-key",""))}"><div class="small" style="margin-top:4px">金鑰只存在這個瀏覽器，直接送到 api.anthropic.com，不經過其他地方。</div>`:'<div class="small">第一次會下載中英文辨識資料（約 10–20MB），之後較快。提取完一定要逐筆檢查。</div>'}</div>
  <div class="row" style="margin-top:14px"><button class="pri" id="extract" style="flex:1 1 260px">掃描全部並提取單字</button></div><p class="small" id="prog"></p>`:""}
  <div id="manual"><h2>手動貼上</h2><p class="small">也可以每行貼一個：英文 | 詞性 | 中文 | 例句</p><textarea id="paste" placeholder="abandon | v. | 放棄；拋棄 | The sailors abandoned the damaged ship."></textarea><button id="parse" class="sm" style="margin-top:8px">加入檢查清單</button></div>
  <div id="revbox"></div>`;
  $("#file").onchange=e=>addFiles(e.target.files);
  const dr=$("#drop");dr.ondragover=e=>{e.preventDefault();dr.style.borderColor="var(--or)"};dr.ondragleave=()=>dr.style.borderColor="";dr.ondrop=e=>{e.preventDefault();addFiles(e.dataTransfer.files)};
  $("#parse").onclick=()=>{$("#paste").value.split("\n").map(l=>l.split("|").map(s=>s.trim())).filter(a=>a[0]).forEach(a=>review.push(mk({en:a[0],pos:a[1],zh:a[2],ex:a[3]})));$("#paste").value="";renderReview()};
  renderReview();
  if(!pages.length)return;
  $("#thumbs").onclick=e=>{const b=e.target.closest("[data-i]");if(b){cur=+b.dataset.i;showOut=!!pages[cur].out;renderUpload()}};
  $("#v-src").onclick=()=>{showOut=false;renderUpload()};$("#v-out").onclick=()=>{showOut=true;renderUpload()};
  $("#clean").onchange=e=>{pages[cur].clean=e.target.checked;if(pages[cur].out){scan(pages[cur]);renderUpload()}};
  $("#reset").onclick=()=>{const p=pages[cur],c=p.src;p.q=[[0,0],[c.width,0],[c.width,c.height],[0,c.height]];p.out=null;p.status="new";showOut=false;renderUpload()};
  $("#rm").onclick=()=>{pages.splice(cur,1);cur=Math.max(0,cur-1);renderUpload()};
  $("#doscan").onclick=()=>{const b=$("#doscan");b.disabled=true;b.textContent="處理中…";setTimeout(()=>{scan(pages[cur]);showOut=true;renderUpload()},30)};
  $("#extract").onclick=extractAll;
  app.querySelectorAll("[data-ext]").forEach(b=>b.onclick=()=>{ext=b.dataset.ext;lsSet("vc-ext",ext);renderUpload()});
  const ki=$("#key");if(ki)ki.onchange=()=>lsSet("vc-key",ki.value.trim());
  if(pages.some(p=>p.out)){const b=$("#pdf");b.classList.remove("hide");b.onclick=makePdf}
  drawStage()}

function drawStage(){const p=pages[cur],st=$("#stage"),c=showOut&&p.out?p.out:p.src,cv=document.createElement("canvas");cv.width=c.width;cv.height=c.height;cv.getContext("2d").drawImage(c,0,0);st.innerHTML="";st.appendChild(cv);if(showOut&&p.out)return;
  const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox",`0 0 ${c.width} ${c.height}`);svg.setAttribute("preserveAspectRatio","none");st.appendChild(svg);
  const r=c.width/ (st.clientWidth||600),draw=()=>{svg.innerHTML=`<polygon points="${p.q.map(a=>a.join(",")).join(" ")}" fill="rgba(220,79,34,.12)" stroke="#dc4f22" stroke-width="${3*r}"/>`+p.q.map((a,i)=>`<circle data-c="${i}" cx="${a[0]}" cy="${a[1]}" r="${16*r}" fill="#dc4f22" stroke="#fff" stroke-width="${3*r}" style="cursor:grab"/>`).join("")};draw();
  let drag=-1;svg.onpointerdown=e=>{const pt=toImg(e);let best=-1,bd=1e9;p.q.forEach((a,i)=>{const dd=Math.hypot(a[0]-pt[0],a[1]-pt[1]);if(dd<bd){bd=dd;best=i}});if(bd<60*r){drag=best;svg.setPointerCapture(e.pointerId)}};
  svg.onpointermove=e=>{if(drag<0)return;const pt=toImg(e);p.q[drag]=[Math.max(0,Math.min(c.width,pt[0])),Math.max(0,Math.min(c.height,pt[1]))];p.out=null;p.status="new";draw()};
  svg.onpointerup=svg.onpointercancel=()=>{if(drag>=0){drag=-1;const b=$("#v-out");if(b)b.disabled=true}};
  function toImg(e){const b=svg.getBoundingClientRect();return[(e.clientX-b.left)/b.width*c.width,(e.clientY-b.top)/b.height*c.height]}}

// 提取：交給目前選的引擎（src/scan/engines/），每筆記住來源頁與位置，核對時裁出小圖對照
async function extractAll(){const en=getEngine(ext);if(!en.ready()){toast("請先輸入 API 金鑰，或改選免費 OCR");return}
  const btn=$("#extract"),prog=$("#prog");btn.disabled=true;let got=0,err="";
  for(let i=0;i<pages.length;i++){const p=pages[i];if(p.status==="done")continue;const head=`第 ${i+1}/${pages.length} 頁：`;
    prog.textContent=head+"掃描中…";await new Promise(r=>setTimeout(r,20));if(!p.out)scan(p);p.status="busy";
    prog.textContent=head+"提取中…";
    try{const a=await en.extract(p.out,{onProgress:t=>{prog.textContent=head+t}});
      a.filter(x=>x&&x.en).forEach(x=>{review.push(mk(x,p,en.id));got++});p.status="done"}
    catch(e){p.status="err";err=String(e&&e.message||e);if(/api.key|auth|401/i.test(err))break}}
  renderUpload();const pr=$("#prog");if(pr)pr.textContent=got?`提取到 ${got} 個條目，請在下方對照原圖逐筆檢查。`:("沒有提取到條目。"+(err?"錯誤："+err:"可以調整四角後重試。"));if(got)$("#revbox").scrollIntoView({behavior:"smooth"})}
const mk=(x,pg,engine)=>({id:rid(),en:String(x.en||"").trim(),pos:String(x.pos||"").trim(),zh:String(x.zh||"").trim(),ex:String(x.ex||"").trim(),blank:String(x.blank||"").trim(),unit:String(x.unit||"").trim(),keep:true,bbox:x.bbox||null,pg:pg||null,engine:engine||"manual",unsure:!!x.unsure});
// 在每筆旁邊畫出它在掃描圖上的位置：有 bbox 就裁切該區塊，沒有就顯示整頁縮圖
function drawCrops(){document.querySelectorAll("canvas[data-crop]").forEach(cv=>{const w=review[+cv.dataset.crop],src=w&&w.pg&&w.pg.out;if(!src)return;let y0=0,y1=src.height;
  if(w.bbox){const pad=src.height*.015;y0=Math.max(0,w.bbox.y0/100*src.height-pad);y1=Math.min(src.height,w.bbox.y1/100*src.height+pad)}
  const h=Math.max(8,y1-y0),k=Math.min(1,(w.bbox?900:420)/src.width);cv.width=Math.round(src.width*k);cv.height=Math.round(h*k);cv.getContext("2d").drawImage(src,0,y0,src.width,h,0,0,cv.width,cv.height)})}

/* ----- Google 翻譯核對 ----- */
async function verifyOne(w){w.chk="busy";w.msg=[];w.okd=false;paintV(w);const warn=[];
  if(w.unsure)warn.push("提取時標示這筆有看不清楚的字，請對照原圖");
  if(!w.en)warn.push("英文是空的");if(!w.zh)warn.push("中文是空的");
  if(w.en&&!isPhrase(w)&&w.ex&&!clozeAns({...w,blank:""})&&!(w.blank&&w.ex.toLowerCase().includes(w.blank.toLowerCase())))warn.push("例句裡找不到這個字，英文或例句可能辨識錯");
  if(w.ex&&/[㐀-鿿]/.test(w.ex))warn.push("例句裡混到中文");
  if(w.en&&!/^[A-Za-z][A-Za-z'’.\/\-+ ()…,]*$/.test(w.en.replace(/wh-疑問詞/g,"")))warn.push("英文含有奇怪的字元");
  try{if(w.en){const g=await gtrans(sayable(w.en));w.g=[...new Set([g.main,...g.dict])].filter(Boolean).slice(0,8);
      if(!/[㐀-鿿]/.test(g.main)&&!g.dict.length)warn.push("Google 不認得這個英文，可能拼錯");
      else if(w.zh){const a=new Set(cjk(w.zh)),b=new Set(cjk(w.g.join(""))),common=[...a].filter(c=>b.has(c)).length;
        if(a.size&&common===0)warn.push("中文和 Google 翻譯完全對不上");else if(a.size>=4&&common<2&&common/a.size<.2)warn.push("中文和 Google 翻譯差很多")}}
    w.chk=warn.length?"warn":"ok"}catch(e){w.chk=warn.length?"warn":"na";w.g=null}
  w.msg=warn;paintV(w);paintSum()}
// 最多 4 筆同時核對
async function verifyAll(){const q=review.filter(w=>!w.chk);q.forEach(w=>w.chk="queued");paintSum();let k=0;const run=async()=>{while(k<q.length){const w=q[k++];await verifyOne(w)}};await Promise.all([run(),run(),run(),run()]);
  const n=review.filter(w=>w.chk==="warn"&&w.keep).length;if(n)toast(`有 ${n} 筆可能辨識錯誤，請逐筆確認紅框的條目`)}
function vHTML(w){if(!w.chk||w.chk==="busy"||w.chk==="queued")return'<span class="small">Google 翻譯核對中…</span>';
  const g=w.g&&w.g.length?`<div class="small">Google 翻譯：${esc(w.g.join("、"))}</div>`:"";
  if(w.chk==="ok")return`<div class="small" style="color:var(--ok)">✓ 與 Google 翻譯相符</div>${g}`;
  if(w.chk==="na")return w.okd?'<div class="small" style="color:var(--ok)">✓ 你已確認</div>':`<div class="small" style="color:var(--or)">連不到 Google 翻譯，請自己確認一次</div><button class="sm" data-a="recheck">重新檢查</button> <button class="sm" data-a="okd">我確認沒問題</button>`;
  if(w.okd)return`<div class="small" style="color:var(--ok)">✓ 你已確認（${esc(w.msg.join("；"))}）</div>${g}`;
  return`<div style="color:var(--bad);font-weight:700;font-size:14px">⚠ 可能辨識錯誤：${esc(w.msg.join("；"))}</div>${g}<div class="row" style="gap:6px;margin-top:6px"><button class="sm" data-a="recheck">改好了，重新檢查</button><button class="sm" data-a="okd">我確認沒問題</button></div>`}
const needs=w=>w.keep&&(w.chk==="warn"||w.chk==="na")&&!w.okd;
function paintV(w){const i=review.indexOf(w),el=$("#vs-"+i);if(!el)return;el.innerHTML=vHTML(w);const c=el.closest(".rc");if(c)c.style.borderColor=needs(w)?"var(--bad)":w.chk==="ok"?"var(--ok)":"";if(c)c.style.borderStyle=needs(w)?"solid":"dashed"}
function paintSum(){const el=$("#vsum");if(!el)return;const n=review.filter(needs).length,busy=review.filter(w=>!w.chk||w.chk==="busy"||w.chk==="queued").length;
  el.className=n?"note":"small";el.style.background=n?"var(--badbg)":"";el.innerHTML=busy?`正在用 Google 翻譯核對…（剩 ${busy} 筆）`:n?`<b style="color:var(--bad)">⚠ 有 ${n} 筆可能辨識錯誤</b>，請看紅框條目，修改後按「重新檢查」，或確認沒問題。`:"✓ 全部條目都已核對。"}
function renderReview(){const box=$("#revbox");if(!box)return;if(!review.length){box.innerHTML="";return}
  const seen={},D=allDicts(),exist=new Set();Object.values(D).forEach(d=>d.words.forEach(w=>exist.add(w.en.toLowerCase())));
  box.innerHTML=`<h2>檢查提取結果（${review.filter(r=>r.keep).length}/${review.length}）</h2><p class="small">每筆都附上掃描圖上的原始位置，請逐筆對照；另外會自動用 Google 翻譯核對中文和英文是否對得上。直接修改錯字；取消勾選的不會存入。橘框代表已經在某本字典裡出現過。</p><div id="vsum" style="margin-bottom:12px"></div>
  <div class="rev" id="rev">${review.map((w,i)=>{const dup=exist.has(w.en.toLowerCase())||seen[w.en.toLowerCase()];seen[w.en.toLowerCase()]=1;const f=(k,l,c)=>`<label class="${c}"><span class="small">${l}</span><input data-i="${i}" data-k="${k}" value="${esc(w[k])}" class="${k==="en"&&dup?"dup":""}"></label>`;
   return`<div class="rc" style="${w.keep?"":"opacity:.45"}">${f("en","英文","f3 wide")}${f("pos","詞性","f1")}<label class="f2 row small" style="gap:6px;align-self:end"><input type="checkbox" data-i="${i}" data-k="keep" ${w.keep?"checked":""} style="width:20px;min-height:20px">保留 ${spkBtn(w.en)}</label>${f("zh","中文","f6")}${f("ex","例句","f6")}${f("blank","克漏字答案","f3 wide")}${f("unit","單元","f3 wide")}${w.pg&&w.pg.out?`<div class="f6 wide crop"><span class="small">${w.bbox?"掃描圖上的這一筆（請對照）":"這筆沒有位置資訊，顯示整頁掃描圖"}</span><canvas data-crop="${i}" class="${w.bbox?"":"whole"}"></canvas></div>`:""}<div class="f6 wide" id="vs-${i}" data-i="${i}"></div></div>`}).join("")}</div>
  <div class="cut" style="margin-top:16px">${SC}<div class="tab"><span>SAVE</span></div><div class="body"><div class="row"><label style="flex:1 1 200px"><span class="small">存到</span><select id="target"><option value="__new">＋ 新字典</option>${Object.values(D).map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("")}</select></label>
   <label style="flex:1 1 200px" id="nmw"><span class="small">新字典名稱</span><input id="newname" value="${esc("單字 "+new Date().toLocaleDateString("zh-TW"))}"></label></div>
   <div class="row" style="margin-top:12px"><button class="pri" id="savebtn">存入字典</button><button id="clear" class="sm ghost">清空清單</button></div></div></div>`;
  review.forEach(paintV);paintSum();drawCrops();
  $("#rev").oninput=e=>{const t=e.target,i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k||k==="keep")return;review[i][k]=t.value};
  $("#rev").onchange=e=>{const t=e.target,i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k)return;if(k==="keep"){review[i].keep=t.checked;renderReview();return}review[i][k]=t.value.trim();if(k==="en"||k==="zh"||k==="ex"||k==="blank")verifyOne(review[i])};
  $("#rev").onclick=e=>{const b=e.target.closest("button[data-a]");if(!b)return;const w=review[+b.closest("[id^=vs-]").dataset.i];if(b.dataset.a==="recheck")verifyOne(w);else{w.okd=true;paintV(w);paintSum()}};
  $("#target").onchange=e=>$("#nmw").classList.toggle("hide",e.target.value!=="__new");
  $("#clear").onclick=async()=>{if(await ask("清空所有尚未儲存的提取結果？")){review=[];renderReview()}};
  $("#savebtn").onclick=async()=>{const ws=review.filter(w=>w.keep&&w.en).map(({keep,chk,msg,g,okd,bbox,pg,engine,unsure,...w})=>w);if(!ws.length){toast("沒有要儲存的條目");return}
    const n=review.filter(needs).length;if(n&&!await ask(`還有 ${n} 筆可能辨識錯誤、你還沒確認。確定要直接存入？`))return;
    let id=$("#target").value;if(id==="__new"){id=rid();S.dicts[id]={id,name:$("#newname").value.trim()||"新字典",words:[]}}const d=ownDict(id);d.words.push(...ws);save();review=[];pages=[];toast(`已存入 ${ws.length} 個條目`);location.hash="dict-"+id}
  if(review.some(w=>!w.chk))verifyAll()}

async function makePdf(){const b=$("#pdf");b.disabled=true;b.textContent="產生中…";try{
  if(!window.jspdf)await loadScript("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js");
  const ps=pages.filter(p=>p.out);let doc=null;for(const p of ps){const w=p.out.width,h=p.out.height,o=w>h?"l":"p";if(!doc)doc=new window.jspdf.jsPDF({unit:"px",format:[w,h],orientation:o,hotfixes:["px_scaling"]});else doc.addPage([w,h],o);doc.addImage(p.out.toDataURL("image/jpeg",.85),"JPEG",0,0,w,h)}
  doc.save("單字掃描.pdf");toast("PDF 已下載")}catch(e){toast("PDF 沒有下載成功")}b.disabled=false;b.textContent="下載掃描 PDF"}
