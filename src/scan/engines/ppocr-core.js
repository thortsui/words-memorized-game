// PP-OCRv6 的辨識流程本體（不碰 DOM，Web Worker 與主執行緒共用）：
//   文字偵測 PP-OCRv6_small_det → 一個個文字框；文字辨識 PP-OCRv6_small_rec（簡繁中文＋英文同一個模型）→ 每框的文字。
// 平常在 ppocr.worker.js 裡跑（提取時畫面不會卡住）；瀏覽器不支援 Worker／OffscreenCanvas 時由 ppocr.js 在主執行緒直接呼叫。
import { cachedBytes, cachedText, cachedBlobUrl } from '../cache.js';

const ORT="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.31.1/dist/";
const HF=(repo,rev,f)=>`https://huggingface.co/PaddlePaddle/${repo}/resolve/${rev}/${f}`;
export const FILES={
  ortJs:ORT+"ort.wasm.bundle.min.mjs",
  ortWasm:ORT+"ort-wasm-simd-threaded.wasm",
  det:HF("PP-OCRv6_small_det_onnx","28fe5895c24fd108c19eb3e8479f4ab385fbfc62","inference.onnx"),
  rec:HF("PP-OCRv6_small_rec_onnx","b8f84f0b80c529de40b4fbb3544b84fa7233a513","inference.onnx"),
  dict:HF("PP-OCRv6_small_rec_onnx","b8f84f0b80c529de40b4fbb3544b84fa7233a513","inference.yml")};
// 各檔案實際大小（位元組）。伺服器回的 content-length 是壓縮後的大小，不能拿來當下載進度的總量
const SIZE={ortWasm:14848852,det:9880512,rec:21159378},TOTAL=SIZE.ortWasm+SIZE.det+SIZE.rec;
const DET={limit:1600,thresh:.2,boxThresh:.45,unclip:1.4,mean:[.485,.456,.406],std:[.229,.224,.225]}; // 官方 inference.yml 的後處理參數
const REC_H=48;
const tick=()=>new Promise(r=>setTimeout(r,0));

// 官方 inference.yml 裡的 character_dict（YAML 清單）→ 字元陣列
export function parseDict(yml){const out=[];let on=false;for(const line of yml.split(/\r?\n/)){if(/^\s*character_dict:/.test(line)){on=true;continue}if(!on)continue;const m=line.match(/^\s*- (.*)$/);if(!m)break;let v=m[1];
    if(/^'.*'$/.test(v))v=v.slice(1,-1).replace(/''/g,"'");else if(/^".*"$/.test(v)){try{v=JSON.parse(v)}catch(e){v=v.slice(1,-1)}}out.push(v)}return out}

let rt=null;
async function load(say){if(rt)return rt;const mb=n=>(n/1048576).toFixed(1);let done=0;
  // 三個大檔案合成一條進度：已下載／總量（都是解壓縮後的實際大小）
  const get=async k=>{const b=await cachedBytes(FILES[k],n=>say&&say(`下載辨識模型… ${mb(Math.min(TOTAL,done+n))} / ${mb(TOTAL)} MB（只有第一次，之後離線可用）`));done+=SIZE[k];return b};
  const jsUrl=await cachedBlobUrl(FILES.ortJs),wasm=await get("ortWasm"),det=await get("det"),rec=await get("rec"),yml=await cachedText(FILES.dict);
  say&&say("載入模型…");
  const ort=await import(/* @vite-ignore */jsUrl);ort.env.wasm.wasmBinary=wasm.buffer;ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;ort.env.logLevel="error";
  const o={executionProviders:["wasm"],graphOptimizationLevel:"all"};
  const detS=await ort.InferenceSession.create(det,o),recS=await ort.InferenceSession.create(rec,o),chars=parseDict(yml);
  if(chars.length<1000)throw new Error("PP-OCR 字元表讀取失敗");
  return rt={ort,detS,recS,chars}}

// 畫布 → [1,3,h,w] 張量（PaddleOCR 用 BGR 順序）
function tensor(ort,c,norm){const w=c.width,h=c.height,d=c.getContext("2d",{willReadFrequently:true}).getImageData(0,0,w,h).data,n=w*h,f=new Float32Array(3*n);
  for(let i=0;i<n;i++){const r=d[i*4]/255,g=d[i*4+1]/255,b=d[i*4+2]/255;f[i]=norm(b,0);f[n+i]=norm(g,1);f[2*n+i]=norm(r,2)}
  return new ort.Tensor("float32",f,[1,3,h,w])}

// 文字偵測：機率圖 → 連通區塊 → 外接矩形 → 向外擴張（DB 的 unclip）。
// 手機照片的文字列常常是斜的、彎的：同時記下區塊每一欄的上下緣，算出平滑的中心線（line），辨識時沿著中心線把這一列拉直再裁下來。
async function detect({ort,detS},src,mk){const k=Math.min(1,DET.limit/Math.max(src.width,src.height)),w=Math.max(32,Math.round(src.width*k/32)*32),h=Math.max(32,Math.round(src.height*k/32)*32),c=mk(w,h),g=c.getContext("2d",{willReadFrequently:true});
  g.fillStyle="#fff";g.fillRect(0,0,w,h);g.drawImage(src,0,0,w,h);
  const out=await detS.run({[detS.inputNames[0]]:tensor(ort,c,(v,i)=>(v-DET.mean[i])/DET.std[i])}),p=out[detS.outputNames[0]].data;
  const seen=new Uint8Array(w*h),stack=new Int32Array(w*h),boxes=[],sx=src.width/w,sy=src.height/h,cmin=new Int32Array(w).fill(h),cmax=new Int32Array(w).fill(-1);
  for(let s=0;s<w*h;s++){if(seen[s]||p[s]<DET.thresh)continue;let top=0,x0=w,x1=0,y0=h,y1=0,sum=0,cnt=0;stack[top++]=s;seen[s]=1;
    while(top){const i=stack[--top],x=i%w,y=(i-x)/w;sum+=p[i];cnt++;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;if(y<cmin[x])cmin[x]=y;if(y>cmax[x])cmax[x]=y;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const j=yy*w+xx;if(!seen[j]&&p[j]>=DET.thresh){seen[j]=1;stack[top++]=j}}}
    const bw=x1-x0+1,bh=y1-y0+1;let line=null;
    if(Math.min(bw,bh)>=3&&sum/cnt>=DET.boxThresh){
      // 每一欄的中心與厚度 → 厚度取中位數（字的高度），中心線用約一個字高寬的移動平均抹平
      const cs=[],ts=[];for(let x=x0;x<=x1;x++){if(cmax[x]>=0){cs.push((cmin[x]+cmax[x]+1)/2);ts.push(cmax[x]-cmin[x]+1)}else{cs.push(cs.length?cs[cs.length-1]:(y0+y1+1)/2);ts.push(0)}}
      const th=ts.filter(t=>t>0).sort((a,b)=>a-b)[ts.filter(t=>t>0).length>>1]||bh;
      // 比字高明顯高的區塊才值得拉直（長而歪、或彎曲的列）
      if(bw>=3*th&&bh>1.35*th){const k=Math.max(1,Math.round(th)),sm=cs.map((_,i)=>{let a=0,n=0;for(let j=Math.max(0,i-k);j<=Math.min(cs.length-1,i+k);j++){a+=cs[j];n++}return a/n});
        const d=th*bw*DET.unclip/(2*(bw+th));line={x0:Math.max(0,(x0-d)*sx),x1:Math.min(src.width,(x1+1+d)*sx),th:(th+2*d)*sy,c:sm.map(v=>v*sy),cx0:x0*sx,step:sx}}}
    for(let x=x0;x<=x1;x++){cmin[x]=h;cmax[x]=-1}
    if(Math.min(bw,bh)<3||sum/cnt<DET.boxThresh)continue;
    const d=bw*bh*DET.unclip/(2*(bw+bh));
    if(line){const cy=line.c[Math.min(line.c.length-1,Math.round(line.c.length*.15))]; // 版面用「拉直後」的框：高度是字高，位置取這一列左端附近的中心
      boxes.push({x0:line.x0,y0:Math.max(0,cy-line.th/2),x1:line.x1,y1:Math.min(src.height,cy+line.th/2),line});continue}
    boxes.push({x0:Math.max(0,(x0-d)*sx),y0:Math.max(0,(y0-d)*sy),x1:Math.min(src.width,(x1+1+d)*sx),y1:Math.min(src.height,(y1+1+d)*sy)})}
  return boxes.sort((a,b)=>a.y0-b.y0||a.x0-b.x0)}

// 文字辨識：把框裁下來縮到高 48，CTC 解碼（索引 0 是空白符，最後一類是空格）
// 沿中心線把一列拉直：輸出寬 w、高 REC_H，第 u 欄取原圖 x＝x0＋u·(x1−x0)/w 那一欄、中心線上下各半個厚度（雙線性取樣）
function warpLine(src,L,w,mk,px){const c=mk(w,REC_H),g=c.getContext("2d",{willReadFrequently:true}),im=g.createImageData(w,REC_H),o=im.data,SW=src.width,SH=src.height;
  for(let u=0;u<w;u++){const x=L.x0+(u+.5)*(L.x1-L.x0)/w,ci=Math.max(0,Math.min(L.c.length-1,Math.round((x-L.cx0)/L.step))),cy=L.c[ci],xi=Math.max(0,Math.min(SW-2,x|0)),fx=x-xi;
    for(let v=0;v<REC_H;v++){const y=cy-L.th/2+(v+.5)*L.th/REC_H,j=(v*w+u)*4;if(y<0||y>SH-1.001){o[j]=o[j+1]=o[j+2]=255;o[j+3]=255;continue}
      const yi=y|0,fy=y-yi,i0=(yi*SW+xi)*4,i1=i0+SW*4;for(let k=0;k<3;k++)o[j+k]=(px[i0+k]*(1-fx)+px[i0+4+k]*fx)*(1-fy)+(px[i1+k]*(1-fx)+px[i1+4+k]*fx)*fy;o[j+3]=255}}
  g.putImageData(im,0,0);return c}
async function recognize({ort,recS,chars},src,b,mk,px){const bw=b.x1-b.x0,bh=b.y1-b.y0,vert=!b.line&&bh>=bw*1.5;let w=Math.round(REC_H*(vert?bh/bw:bw/bh));w=Math.max(16,Math.min(3200,w));
  let c;if(b.line&&px)c=warpLine(src,b.line,w,mk,px);else{c=mk(w,REC_H);const g=c.getContext("2d",{willReadFrequently:true});g.fillStyle="#fff";g.fillRect(0,0,w,REC_H);g.imageSmoothingQuality="high";
  if(vert){g.translate(0,REC_H);g.rotate(-Math.PI/2);g.drawImage(src,b.x0,b.y0,bw,bh,0,0,REC_H,w)}else g.drawImage(src,b.x0,b.y0,bw,bh,0,0,w,REC_H)}
  const out=await recS.run({[recS.inputNames[0]]:tensor(ort,c,v=>(v-.5)/.5)}),t=out[recS.outputNames[0]],T=t.dims[1],C=t.dims[2],p=t.data;
  if(C!==chars.length+2)throw new Error(`PP-OCR 模型與字元表對不上（${C} / ${chars.length}）`);
  let text="",last=0,conf=0,n=0;for(let i=0;i<T;i++){let bi=0,bv=-1;const o=i*C;for(let k=0;k<C;k++){const v=p[o+k];if(v>bv){bv=v;bi=k}}
    if(bi!==0&&bi!==last){text+=bi===C-1?" ":chars[bi-1];conf+=bv;n++}last=bi}
  return{text:text.trim(),conf:n?conf/n:0}}

// 只做 OCR：回傳文字框 [{text,conf,x0,y0,x1,y1}]（像素座標）。src：畫布或 ImageBitmap；mk(w,h)：建立畫布的函式
export async function ocrBoxes(src,say,mk){const R=await load(say);say&&say("找出文字位置…");await tick();
  const boxes=await detect(R,src,mk),out=[];let px=null;
  if(boxes.some(b=>b.line)){const c=mk(src.width,src.height),g=c.getContext("2d",{willReadFrequently:true});g.drawImage(src,0,0);px=g.getImageData(0,0,src.width,src.height).data}
  for(let i=0;i<boxes.length;i++){if(i%3===0){say&&say(`辨識文字 ${i+1}/${boxes.length}`);await tick()}
    const r=await recognize(R,src,boxes[i],mk,px),{line,...bx}=boxes[i];if(r.text&&r.conf>=.5)out.push({...bx,...r})}
  return out}
