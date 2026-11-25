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
  const [wp,cp]=[await cachedBlobUrl(FILES.worker),await cachedBlobUrl(FILES.core,"text/javascript",(n,t)=>report&&report(`下載 tesseract 辨識核心… ${(n/1048576).toFixed(1)} MB（只有第一次）`))];
  const log=m=>{if(m.status&&report)report("tesseract："+m.status+(m.progress?" "+Math.round(m.progress*100)+"%":""))};
  try{worker=await window.Tesseract.createWorker(["eng","chi_tra"],1,{workerPath:wp,corePath:cp+"#js",workerBlobURL:false,logger:log})}
  catch(e){worker=await window.Tesseract.createWorker(["eng","chi_tra"],1,{logger:log})} // blob 載入不被瀏覽器接受時，退回直接從 CDN 載
  await worker.setParameters({preserve_interword_spaces:"1"});
  return worker}

// 前處理：放大 → 灰階 → 去陰影（每 24 px 一格取最亮當紙色，平滑後把每個像素除以紙色）→ 拉高對比。
// tesseract 內部用整張圖一個門檻做二值化，有陰影時會整片讀不到，所以先把底色拉平。
function prep(src){const k=Math.max(1,Math.min(2,TARGET/Math.max(src.width,src.height))),c=document.createElement("canvas"),W=c.width=Math.round(src.width*k),H=c.height=Math.round(src.height*k);
  const g=c.getContext("2d",{willReadFrequently:true});g.fillStyle="#fff";g.fillRect(0,0,W,H);g.imageSmoothingQuality="high";g.drawImage(src,0,0,W,H);
  const im=g.getImageData(0,0,W,H),o=im.data,f=24,gw=Math.ceil(W/f),gh=Math.ceil(H/f),L=new Float32Array(W*H);let bg=new Float32Array(gw*gh);
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const j=(y*W+x)*4,v=.3*o[j]+.59*o[j+1]+.11*o[j+2],gi=(y/f|0)*gw+(x/f|0);L[y*W+x]=v;if(v>bg[gi])bg[gi]=v}
  for(let pass=0;pass<3;pass++){const n=new Float32Array(gw*gh);for(let y=0;y<gh;y++)for(let x=0;x<gw;x++){let s=0,q=0,m=0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const yy=y+dy,xx=x+dx;if(yy<0||xx<0||yy>=gh||xx>=gw)continue;const v=bg[yy*gw+xx];s+=v;q++;if(v>m)m=v}n[y*gw+x]=pass<1?m:s/q}bg=n}
  for(let y=0;y<H;y++){const gy=Math.min(gh-1.001,Math.max(0,y/f-.5)),y0=gy|0,ty=gy-y0,y1=Math.min(gh-1,y0+1);for(let x=0;x<W;x++){const gx=Math.min(gw-1.001,Math.max(0,x/f-.5)),x0=gx|0,tx=gx-x0,x1=Math.min(gw-1,x0+1);
      const b=Math.max(40,(bg[y0*gw+x0]*(1-tx)+bg[y0*gw+x1]*tx)*(1-ty)+(bg[y1*gw+x0]*(1-tx)+bg[y1*gw+x1]*tx)*ty);let v=L[y*W+x]/b*255;v=(v-40)*255/(225-40);v=v<0?0:v>255?255:v;const j=(y*W+x)*4;o[j]=o[j+1]=o[j+2]=v;o[j+3]=255}}
  g.putImageData(im,0,0);return{c,k}}

// 一行裡字距超過 2.2 倍行高就切開（兩欄版面時 tesseract 會把左右兩欄讀成同一行）
function segments(line,k){const ws=(line.words||[]).filter(w=>w.text&&w.bbox);if(!ws.length)return line.text&&line.bbox?[{text:line.text,x0:line.bbox.x0/k,y0:line.bbox.y0/k,x1:line.bbox.x1/k,y1:line.bbox.y1/k,conf:line.confidence/100}]:[];
  const h=line.bbox.y1-line.bbox.y0,out=[];let cur=null;
  for(const w of ws){if(cur&&w.bbox.x0-cur.x1<=2.2*h){cur.text+=" "+w.text;cur.x1=Math.max(cur.x1,w.bbox.x1);cur.y0=Math.min(cur.y0,w.bbox.y0);cur.y1=Math.max(cur.y1,w.bbox.y1);cur.cs+=w.confidence;cur.n++}
    else{cur={text:w.text,x0:w.bbox.x0,y0:w.bbox.y0,x1:w.bbox.x1,y1:w.bbox.y1,cs:w.confidence,n:1};out.push(cur)}}
  return out.map(s=>({text:s.text,x0:s.x0/k,y0:line.bbox.y0/k,x1:s.x1/k,y1:line.bbox.y1/k,conf:s.cs/s.n/100}))}

// 只做 OCR：回傳文字框 [{text,conf,x0,y0,x1,y1}]（像素座標，對應原本的畫布）
export async function ocrBoxes(canvas,say){report=say||null;const w=await getWorker(),{c,k}=prep(canvas);
  const {data}=await w.recognize(c);const lines=Array.isArray(data.lines)?data.lines:[];
  return lines.flatMap(l=>segments(l,k)).filter(b=>b.text.trim())}

export const ocrEngine={
  id:"ocr",label:"tesseract（本機，免金鑰）",needsKey:false,local:true,
  size:"約 9 MB",note:"第一次使用會下載辨識資料約 9 MB（之後存在瀏覽器裡，離線也能用）。圖片不會上傳。",
  ready:()=>true,
  cached:()=>allCached(Object.values(FILES)),
  async extract(canvas,{onProgress}={}){const lines=await ocrBoxes(canvas,onProgress),e=parseLayout(lines,{W:canvas.width,H:canvas.height});e.lines=lines;return e}
};
