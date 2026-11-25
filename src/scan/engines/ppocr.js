// 提取引擎：PP-OCRv6（PaddleOCR 官方 ONNX 模型，用 onnxruntime-web 的 wasm 在瀏覽器本機執行；免金鑰、不上傳圖片）
//   文字偵測 PP-OCRv6_small_det → 一個個文字框；文字辨識 PP-OCRv6_small_rec（簡繁中文＋英文同一個模型）→ 每框的文字
//   條目結構交給規則式版面解析（src/scan/parse.js）。
// 模型與執行檔從 CDN 用到才下載，存進 Cache Storage，之後離線可用。來源與授權見 docs/第三方資源.md。
import { cachedBytes, cachedText, cachedBlobUrl, allCached } from '../cache.js';
import { parseLayout } from '../parse.js';

const ORT="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.31.1/dist/";
const HF=(repo,rev,f)=>`https://huggingface.co/PaddlePaddle/${repo}/resolve/${rev}/${f}`;
export const FILES={
  ortJs:ORT+"ort.wasm.bundle.min.mjs",                                                                       // 0.08 MB
  ortWasm:ORT+"ort-wasm-simd-threaded.wasm",                                                                 // 14.2 MB
  det:HF("PP-OCRv6_small_det_onnx","28fe5895c24fd108c19eb3e8479f4ab385fbfc62","inference.onnx"),             // 9.4 MB
  rec:HF("PP-OCRv6_small_rec_onnx","b8f84f0b80c529de40b4fbb3544b84fa7233a513","inference.onnx"),             // 20.2 MB
  dict:HF("PP-OCRv6_small_rec_onnx","b8f84f0b80c529de40b4fbb3544b84fa7233a513","inference.yml")};            // 0.15 MB（字元表）
const DET={limit:1600,thresh:.2,boxThresh:.45,unclip:1.4,mean:[.485,.456,.406],std:[.229,.224,.225]}; // 官方 inference.yml 的後處理參數
const REC_H=48;

// 官方 inference.yml 裡的 character_dict（YAML 清單）→ 字元陣列
export function parseDict(yml){const out=[];let on=false;for(const line of yml.split(/\r?\n/)){if(/^\s*character_dict:/.test(line)){on=true;continue}if(!on)continue;const m=line.match(/^\s*- (.*)$/);if(!m)break;let v=m[1];
    if(/^'.*'$/.test(v))v=v.slice(1,-1).replace(/''/g,"'");else if(/^".*"$/.test(v)){try{v=JSON.parse(v)}catch(e){v=v.slice(1,-1)}}out.push(v)}return out}

let rt=null;
async function load(say){if(rt)return rt;const prog=name=>(n,t)=>say&&say(`下載${name}… ${(n/1048576).toFixed(1)}${t?" / "+(t/1048576).toFixed(1):""} MB（只有第一次）`);
  const [jsUrl,wasm,det,rec,yml]=[await cachedBlobUrl(FILES.ortJs),await cachedBytes(FILES.ortWasm,prog("辨識執行檔")),await cachedBytes(FILES.det,prog("文字偵測模型")),await cachedBytes(FILES.rec,prog("文字辨識模型")),await cachedText(FILES.dict)];
  say&&say("PP-OCR：載入模型…");
  const ort=await import(/* @vite-ignore */jsUrl);ort.env.wasm.wasmBinary=wasm.buffer;ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;ort.env.logLevel="error";
  const o={executionProviders:["wasm"],graphOptimizationLevel:"all"};
  const detS=await ort.InferenceSession.create(det,o),recS=await ort.InferenceSession.create(rec,o),chars=parseDict(yml);
  if(chars.length<1000)throw new Error("PP-OCR 字元表讀取失敗");
  return rt={ort,detS,recS,chars}}

const mk=(w,h)=>{const c=document.createElement("canvas");c.width=w;c.height=h;return c};
// 畫布 → [1,3,h,w] 張量（PaddleOCR 用 BGR 順序）
function tensor(ort,c,norm){const w=c.width,h=c.height,d=c.getContext("2d",{willReadFrequently:true}).getImageData(0,0,w,h).data,n=w*h,f=new Float32Array(3*n);
  for(let i=0;i<n;i++){const r=d[i*4]/255,g=d[i*4+1]/255,b=d[i*4+2]/255;f[i]=norm(b,0);f[n+i]=norm(g,1);f[2*n+i]=norm(r,2)}
  return new ort.Tensor("float32",f,[1,3,h,w])}

// 文字偵測：機率圖 → 連通區塊 → 外接矩形（掃描圖已經拉平，用正矩形即可）→ 向外擴張（DB 的 unclip）
async function detect({ort,detS},src){const k=Math.min(1,DET.limit/Math.max(src.width,src.height)),w=Math.max(32,Math.round(src.width*k/32)*32),h=Math.max(32,Math.round(src.height*k/32)*32),c=mk(w,h),g=c.getContext("2d",{willReadFrequently:true});
  g.fillStyle="#fff";g.fillRect(0,0,w,h);g.drawImage(src,0,0,w,h);
  const out=await detS.run({[detS.inputNames[0]]:tensor(ort,c,(v,i)=>(v-DET.mean[i])/DET.std[i])}),p=out[detS.outputNames[0]].data;
  const seen=new Uint8Array(w*h),stack=new Int32Array(w*h),boxes=[],sx=src.width/w,sy=src.height/h;
  for(let s=0;s<w*h;s++){if(seen[s]||p[s]<DET.thresh)continue;let top=0,x0=w,x1=0,y0=h,y1=0,sum=0,cnt=0;stack[top++]=s;seen[s]=1;
    while(top){const i=stack[--top],x=i%w,y=(i-x)/w;sum+=p[i];cnt++;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const j=yy*w+xx;if(!seen[j]&&p[j]>=DET.thresh){seen[j]=1;stack[top++]=j}}}
    const bw=x1-x0+1,bh=y1-y0+1;if(Math.min(bw,bh)<3||sum/cnt<DET.boxThresh)continue;
    const d=bw*bh*DET.unclip/(2*(bw+bh));
    boxes.push({x0:Math.max(0,(x0-d)*sx),y0:Math.max(0,(y0-d)*sy),x1:Math.min(src.width,(x1+1+d)*sx),y1:Math.min(src.height,(y1+1+d)*sy)})}
  return boxes.sort((a,b)=>a.y0-b.y0||a.x0-b.x0)}

// 文字辨識：把框裁下來縮到高 48，CTC 解碼（索引 0 是空白符，最後一類是空格）
async function recognize({ort,recS,chars},src,b){const bw=b.x1-b.x0,bh=b.y1-b.y0,vert=bh>=bw*1.5;let w=Math.round(REC_H*(vert?bh/bw:bw/bh));w=Math.max(16,Math.min(3200,w));
  const c=mk(w,REC_H),g=c.getContext("2d",{willReadFrequently:true});g.fillStyle="#fff";g.fillRect(0,0,w,REC_H);g.imageSmoothingQuality="high";
  if(vert){g.translate(0,REC_H);g.rotate(-Math.PI/2);g.drawImage(src,b.x0,b.y0,bw,bh,0,0,REC_H,w)}else g.drawImage(src,b.x0,b.y0,bw,bh,0,0,w,REC_H);
  const out=await recS.run({[recS.inputNames[0]]:tensor(ort,c,v=>(v-.5)/.5)}),t=out[recS.outputNames[0]],T=t.dims[1],C=t.dims[2],p=t.data;
  if(C!==chars.length+2)throw new Error(`PP-OCR 模型與字元表對不上（${C} / ${chars.length}）`);
  let text="",last=0,conf=0,n=0;for(let i=0;i<T;i++){let bi=0,bv=-1;const o=i*C;for(let k=0;k<C;k++){const v=p[o+k];if(v>bv){bv=v;bi=k}}
    if(bi!==0&&bi!==last){text+=bi===C-1?" ":chars[bi-1];conf+=bv;n++}last=bi}
  return{text:text.trim(),conf:n?conf/n:0}}

// 只做 OCR：回傳文字框 [{text,conf,x0,y0,x1,y1}]（像素座標）
export async function ocrBoxes(canvas,say){const R=await load(say);say&&say("PP-OCR：找出文字位置…");await new Promise(r=>setTimeout(r,0));
  const boxes=await detect(R,canvas),out=[];
  for(let i=0;i<boxes.length;i++){if(i%4===0){say&&say(`PP-OCR：辨識文字 ${i+1}/${boxes.length}`);await new Promise(r=>setTimeout(r,0))}
    const r=await recognize(R,canvas,boxes[i]);if(r.text&&r.conf>=.5)out.push({...boxes[i],...r})}
  return out}

export const ppocrEngine={
  id:"ppocr",label:"PP-OCR（本機，免金鑰）",needsKey:false,local:true,
  size:"約 44 MB",note:"第一次使用會下載辨識模型約 44 MB（之後存在瀏覽器裡，離線也能用）。圖片不會上傳。",
  ready:()=>true,
  cached:()=>allCached(Object.values(FILES)),
  async extract(canvas,{onProgress}={}){const lines=await ocrBoxes(canvas,onProgress),e=parseLayout(lines,{W:canvas.width,H:canvas.height});e.lines=lines;return e}
};
