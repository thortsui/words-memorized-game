// 提取引擎：tesseract.js 5.1.1（LSTM，eng+chi_tra；在瀏覽器本機執行，免金鑰、不上傳圖片）
//   先把掃描圖放大並轉灰階再辨識；逐行文字依字距切成文字框，條目結構交給規則式版面解析（src/scan/parse.js）。
// 程式檔存進 Cache Storage、語言資料由 tesseract.js 存進 IndexedDB，下載過一次之後離線可用。
import { cachedBlobUrl, allCached } from '../cache.js';
import { parseLayout } from '../parse.js';

const V="https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/";
export const FILES={
  main:V+"tesseract.min.js",                                                                    // 0.07 MB
  worker:V+"worker.min.js",                                                                     // 0.12 MB
  core:"https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1/tesseract-core-simd-lstm.wasm.js"};// 3.8 MB
// 語言資料（tesseract.js 預設來源）：eng 2.8 MB＋chi_tra 1.6 MB
const TARGET=2600; // 辨識前把長邊放大到這個像素數（小字放大後比較準）

let worker=null,report=null;
async function getWorker(){if(worker)return worker;
  if(!window.Tesseract){const s=document.createElement("script");s.src=await cachedBlobUrl(FILES.main);await new Promise((ok,no)=>{s.onload=ok;s.onerror=()=>no(new Error("tesseract.js 載入失敗"));document.head.appendChild(s)})}
  // 核心檔用 blob: 網址載入；網址要以 js 結尾 tesseract.js 才會當成檔案（而不是資料夾），所以加上 #js
  const [wp,cp]=[await cachedBlobUrl(FILES.worker),await cachedBlobUrl(FILES.core,"text/javascript",(n,t)=>report&&report(`tesseract：下載辨識核心… ${(n/1048576).toFixed(1)} / 3.8 MB（只有第一次）`))];
  const ZH={"loading tesseract core":"載入辨識核心","initializing tesseract":"啟動辨識核心","initialized tesseract":"辨識核心就緒","loading language traineddata":"下載語言資料（只有第一次）","loaded language traineddata":"語言資料就緒","initializing api":"載入語言資料","initialized api":"準備完成","recognizing text":"辨識文字"};
  const log=m=>{if(m.status&&report)report("tesseract："+(ZH[m.status]||"處理中")+(m.progress&&m.progress<1?" "+Math.round(m.progress*100)+"%":""))};
  try{worker=await window.Tesseract.createWorker(["eng","chi_tra"],1,{workerPath:wp,corePath:cp+"#js",workerBlobURL:false,logger:log})}
  catch(e){worker=await window.Tesseract.createWorker(["eng","chi_tra"],1,{logger:log})} // blob 載入不被瀏覽器接受時，退回直接從 CDN 載
  await worker.setParameters({preserve_interword_spaces:"1"});
  paths={wp,cp};return worker}
// 中文專用的第二個 worker（只載 chi_tra、單行模式）：英中混合模型常把彩色的中文解釋讀成英文亂碼（FERRY、BEYER），
// 所以「詞性後面那一段」再用它重讀一次。只在用到時建立
let paths=null,zhw=null;
async function getZhWorker(){if(zhw)return zhw;await getWorker();
  try{zhw=await window.Tesseract.createWorker(["chi_tra"],1,{workerPath:paths.wp,corePath:paths.cp+"#js",workerBlobURL:false})}catch(e){zhw=await window.Tesseract.createWorker(["chi_tra"],1)}
  await zhw.setParameters({tessedit_pageseg_mode:"7"});return zhw}
const ZPOS=/^[(\[>»►▶]?(?:n|v|vt|vi|yt|adj|dj|adv|prep|conj|pron|pn)[.,]?$/i,ZBR=/^(?:[\[f(][A-Za-z,]{0,5}[\]J)]?|sing\.?|pl\.?|[CU]\]?,?)$/,ZEN=/^[a-z][a-z'\-]+[,.;]?$/;
const CJ=/[㐀-鿿]/g;
// 在每一行裡找「詞性」字，後面到英文解釋（小寫英文字）之前的那一段，用中文 worker 重讀；讀出來大多是中文才換掉
async function fixZh(lines,c){let w2=null;
  for(const l of lines){const ws=(l.words||[]).filter(w=>w.bbox);
    // 詞性只會在一行的開頭（前面最多一個三角形記號）
    for(let i=0;i<Math.min(ws.length,3);i++){if(!ZPOS.test(ws[i].text.trim()))continue;let j=i+1;while(j<ws.length&&j<i+3&&ZBR.test(ws[j].text.trim()))j++;
      let k=j;while(k<ws.length&&k<j+8&&!ZEN.test(ws[k].text.trim()))k++;if(k===j)continue;
      const x0=Math.min(...ws.slice(j,k).map(w=>w.bbox.x0)),x1=Math.max(...ws.slice(j,k).map(w=>w.bbox.x1)),y0=Math.min(l.bbox.y0,...ws.slice(j,k).map(w=>w.bbox.y0)),y1=Math.max(l.bbox.y1,...ws.slice(j,k).map(w=>w.bbox.y1)),h=y1-y0;
      if(x1-x0<h*.8||x1-x0>h*30)continue;
      // 英中混合模型已經讀成中文的就不重讀（重讀不一定比較好）
      {const o=ws.slice(j,k).map(w=>w.text).join("").replace(/[\s；;，,、（）()…．.]/g,"");if(o&&(o.match(CJ)||[]).length>=.7*o.length){i=k-1;continue}}
      const pad=Math.round(h*.25),sx=Math.max(0,x0-Math.round(h*.5)),sy=Math.max(0,y0-pad),sw=Math.min(c.width,x1+pad)-sx,sh=Math.min(c.height,y1+pad)-sy,k2=Math.min(3,Math.max(1,64/sh));
      const cv=document.createElement("canvas");cv.width=Math.round(sw*k2);cv.height=Math.round(sh*k2);const g=cv.getContext("2d");g.fillStyle="#fff";g.fillRect(0,0,cv.width,cv.height);g.imageSmoothingQuality="high";g.drawImage(c,sx,sy,sw,sh,0,0,cv.width,cv.height);
      try{w2=w2||await getZhWorker();const {data}=await w2.recognize(cv);const t=String(data.text||"").replace(/\s+/g,""),n=(t.match(CJ)||[]).length;
        if(n>=1&&n>=.5*t.replace(/[；;，,、（）()…．.]/g,"").length&&data.confidence>=20){ws[j].text=t;ws[j].confidence=data.confidence;for(let q=j+1;q<k;q++)ws[q].text=""}}catch(e){}
      i=k-1}}}

// 前處理：放大 → 灰階 → 去陰影（每 24 px 一格取最亮當紙色，平滑後把每個像素除以紙色）→ 拉高對比。
// tesseract 內部用整張圖一個門檻做二值化，有陰影時會整片讀不到，所以先把底色拉平。
async function prep(src){let t0=performance.now();const brk=async()=>{if(performance.now()-t0>40){await new Promise(r=>setTimeout(r,0));t0=performance.now()}};   // 每 40ms 讓出主執行緒，畫面不會卡住
  const k=Math.max(1,Math.min(2,TARGET/Math.max(src.width,src.height))),c=document.createElement("canvas"),W=c.width=Math.round(src.width*k),H=c.height=Math.round(src.height*k);
  const g=c.getContext("2d",{willReadFrequently:true});g.fillStyle="#fff";g.fillRect(0,0,W,H);g.imageSmoothingQuality="high";g.drawImage(src,0,0,W,H);
  const im=g.getImageData(0,0,W,H),o=im.data,f=24,gw=Math.ceil(W/f),gh=Math.ceil(H/f),L=new Float32Array(W*H);let bg=new Float32Array(gw*gh);
  for(let y=0;y<H;y++){if(!(y&63))await brk();for(let x=0;x<W;x++){const j=(y*W+x)*4,v=.3*o[j]+.59*o[j+1]+.11*o[j+2],gi=(y/f|0)*gw+(x/f|0);L[y*W+x]=v;if(v>bg[gi])bg[gi]=v}}
  for(let pass=0;pass<3;pass++){const n=new Float32Array(gw*gh);for(let y=0;y<gh;y++)for(let x=0;x<gw;x++){let s=0,q=0,m=0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const yy=y+dy,xx=x+dx;if(yy<0||xx<0||yy>=gh||xx>=gw)continue;const v=bg[yy*gw+xx];s+=v;q++;if(v>m)m=v}n[y*gw+x]=pass<1?m:s/q}bg=n}
  for(let y=0;y<H;y++){if(!(y&63))await brk();const gy=Math.min(gh-1.001,Math.max(0,y/f-.5)),y0=gy|0,ty=gy-y0,y1=Math.min(gh-1,y0+1);for(let x=0;x<W;x++){const gx=Math.min(gw-1.001,Math.max(0,x/f-.5)),x0=gx|0,tx=gx-x0,x1=Math.min(gw-1,x0+1);
      const b=Math.max(40,(bg[y0*gw+x0]*(1-tx)+bg[y0*gw+x1]*tx)*(1-ty)+(bg[y1*gw+x0]*(1-tx)+bg[y1*gw+x1]*tx)*ty);let v=L[y*W+x]/b*255;v=(v-40)*255/(225-40);v=v<0?0:v>255?255:v;const j=(y*W+x)*4;o[j]=o[j+1]=o[j+2]=v;o[j+3]=255}}
  g.putImageData(im,0,0);return{c,k}}

// 一行裡字距超過 0.9 倍行高就切成兩個文字框（兩欄版面時 tesseract 會把左右兩欄讀成同一行；切多了沒關係，版面解析會把同一欄同一列的框再併回來）
function segments(line,k){const ws=(line.words||[]).filter(w=>w.text&&w.text.trim()&&w.bbox);if(!ws.length)return line.text&&line.bbox?[{text:line.text,x0:line.bbox.x0/k,y0:line.bbox.y0/k,x1:line.bbox.x1/k,y1:line.bbox.y1/k,conf:line.confidence/100}]:[];
  const h=line.bbox.y1-line.bbox.y0,out=[];let cur=null;
  for(const w of ws){if(cur&&w.bbox.x0-cur.x1<=.9*h){cur.text+=" "+w.text;cur.x1=Math.max(cur.x1,w.bbox.x1);cur.y0=Math.min(cur.y0,w.bbox.y0);cur.y1=Math.max(cur.y1,w.bbox.y1);cur.cs+=w.confidence;cur.n++}
    else{cur={text:w.text,x0:w.bbox.x0,y0:w.bbox.y0,x1:w.bbox.x1,y1:w.bbox.y1,cs:w.confidence,n:1};out.push(cur)}}
  return out.map(s=>({text:s.text,x0:s.x0/k,y0:line.bbox.y0/k,x1:s.x1/k,y1:line.bbox.y1/k,conf:s.cs/s.n/100}))}

// 逐行重讀：手機照片上 tesseract 自己切行常常切壞（歪的、彩色粗體的字整行變亂碼），
// 有主引擎找到的文字列位置（strips）時，就一列一列裁下來用單行模式辨識——位置共用，但「讀出來的字」仍是 tesseract 自己的，核對的意義不變。
// 詞性後面的中文再用中文專用模型重讀一次（fixZh）。
// 一小塊圖裡墨水的主軸角度（弧度）：書頁靠近裝訂處會翹起來，左欄的單字常斜 15–25°，整頁拉平也拉不正
function inkAngle(c){const g=c.getContext("2d",{willReadFrequently:true}),{width:W,height:H}=c,d=g.getImageData(0,0,W,H).data;let n=0,sx=0,sy=0,sxx=0,syy=0,sxy=0,sum=0;
  for(let i=0;i<W*H;i++)sum+=.3*d[i*4]+.59*d[i*4+1]+.11*d[i*4+2];const th=sum/(W*H)*.7;
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const j=(y*W+x)*4;if(.3*d[j]+.59*d[j+1]+.11*d[j+2]<th){n++;sx+=x;sy+=y;sxx+=x*x;syy+=y*y;sxy+=x*y}}
  if(n<30)return 0;const mx=sx/n,my=sy/n;return .5*Math.atan2(2*(sxy/n-mx*my),(sxx/n-mx*mx)-(syy/n-my*my))}
function rotated(c,a){const W=c.width,H=c.height,cs=Math.abs(Math.cos(a)),sn=Math.abs(Math.sin(a)),w=Math.round(W*cs+H*sn),h=Math.round(W*sn+H*cs),o=document.createElement("canvas");o.width=w;o.height=h;
  const g=o.getContext("2d");g.fillStyle="#fff";g.fillRect(0,0,w,h);g.translate(w/2,h/2);g.rotate(-a);g.drawImage(c,-W/2,-H/2);return o}
async function stripBoxes(canvas,strips,say){const w=await getWorker(),out=[];await w.setParameters({tessedit_pageseg_mode:"7"});
  try{for(let i=0;i<strips.length;i++){const b=strips[i];if(i%4===0&&say)say(`tesseract：逐行辨識 ${i+1}/${strips.length}`);
      const h=b.y1-b.y0;if(!(h>4)||b.x1-b.x0<4)continue;const pad=h*.15,sx=Math.max(0,b.x0-pad),sy=Math.max(0,b.y0-pad),sw=Math.min(canvas.width,b.x1+pad)-sx,sh=Math.min(canvas.height,b.y1+pad)-sy,k=Math.max(.5,Math.min(4,64/sh));
      const c=document.createElement("canvas");c.width=Math.max(8,Math.round(sw*k));c.height=Math.max(8,Math.round(sh*k));const g=c.getContext("2d");g.fillStyle="#fff";g.fillRect(0,0,c.width,c.height);g.imageSmoothingQuality="high";g.drawImage(canvas,sx,sy,sw,sh,0,0,c.width,c.height);
      let {data}=await w.recognize(c),cc=c;
      // 信心低的：量墨水的傾斜角，轉正再讀一次，取信心高的那次
      if((data.confidence||0)<70){const a=inkAngle(c);if(Math.abs(a)>.05&&Math.abs(a)<.6){const rc=rotated(c,a),r2=(await w.recognize(rc)).data;if((r2.confidence||0)>(data.confidence||0)+5){data=r2;cc=rc}}}
      const lines=Array.isArray(data.lines)?data.lines:[];await fixZh(lines,cc);
      const text=lines.flatMap(l=>(l.words||[]).map(x=>x.text)).filter(t=>t&&t.trim()).join(" ").replace(/\s+/g," ").trim();
      if(text)out.push({text,x0:b.x0,y0:b.y0,x1:b.x1,y1:b.y1,conf:(data.confidence||0)/100})}}
  finally{await w.setParameters({tessedit_pageseg_mode:"3"})}
  return out}

// 只做 OCR：回傳文字框 [{text,conf,x0,y0,x1,y1}]（像素座標，對應原本的畫布）。strips：主引擎找到的文字列位置（有給就逐行重讀）
export async function ocrBoxes(canvas,say,strips){if(strips&&strips.length>=3){report=say||null;return stripBoxes(canvas,strips,say)}report=say||null;const w=await getWorker();report&&report("tesseract：影像前處理");const {c,k}=await prep(canvas);
  const {data}=await w.recognize(c);const lines=Array.isArray(data.lines)?data.lines:[];
  // 整頁模式不做中文重讀（乾淨的掃描頁本來就讀得好，重讀反而可能改壞）；逐行模式才做
  return lines.flatMap(l=>segments(l,k)).filter(b=>b.text.trim())}

export const ocrEngine={
  id:"ocr",label:"tesseract（本機，免金鑰）",needsKey:false,local:true,
  size:"約 9 MB",note:"第一次使用會下載辨識資料約 9 MB（之後存在瀏覽器裡，離線也能用）。圖片不會上傳。",
  ready:()=>true,
  cached:()=>allCached(Object.values(FILES)),
  // strips／expect：主引擎找到的文字列位置與條目數。先照原本整頁讀；讀出來的條目明顯比主引擎少（手機照片常見）才逐行重讀，取條目多的那一份
  async extract(canvas,{onProgress,strips,expect}={}){const P=l=>{const e=parseLayout(l,{W:canvas.width,H:canvas.height});e.lines=l;return e};
    const full=P(await ocrBoxes(canvas,onProgress));if(!strips||strips.length<3||!expect||full.length>=.7*expect)return full;
    const st=P(await ocrBoxes(canvas,onProgress,strips));return st.length>full.length?st:full}
};
