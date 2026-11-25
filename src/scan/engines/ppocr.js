// 提取引擎：PP-OCRv6（PaddleOCR 官方 ONNX 模型，用 onnxruntime-web 的 wasm 在瀏覽器本機執行；免金鑰、不上傳圖片）
//   辨識流程在 ppocr-core.js，放在 Web Worker（ppocr.worker.js）裡跑，提取時畫面不會卡住；條目結構交給規則式版面解析（src/scan/parse.js）。
// 模型與執行檔從 CDN 用到才下載，存進 Cache Storage，之後離線可用。來源與授權見 docs/第三方資源.md。
import { allCached } from '../cache.js';
import { parseLayout } from '../parse.js';
import { FILES, parseDict, ocrBoxes as coreBoxes } from './ppocr-core.js';
export { FILES, parseDict };

let wk=null,seq=0,broken=false;const pend=new Map();
function worker(){if(wk)return wk;
  wk=new Worker(new URL('./ppocr.worker.js',import.meta.url),{type:"module"});
  wk.onmessage=e=>{const m=e.data,p=pend.get(m.id);if(!p)return;if(m.prog){p.say&&p.say(m.prog);return}pend.delete(m.id);m.error?p.no(new Error(m.error)):p.ok(m.boxes)};
  wk.onerror=e=>{broken=true;for(const p of pend.values())p.no(new Error("worker："+(e&&e.message||"無法啟動")));pend.clear();try{wk.terminate()}catch(_){}wk=null};
  return wk}

// 只做 OCR：回傳文字框 [{text,conf,x0,y0,x1,y1}]（像素座標）
export async function ocrBoxes(canvas,say){const tell=t=>say&&say("PP-OCR："+t);
  if(!broken&&typeof Worker!=="undefined"&&typeof OffscreenCanvas!=="undefined"&&typeof createImageBitmap!=="undefined"){
    try{const bmp=await createImageBitmap(canvas),id=++seq;return await new Promise((ok,no)=>{pend.set(id,{ok,no,say:tell});worker().postMessage({id,bmp},[bmp])})}
    catch(e){if(!broken)throw e}}   // worker 本身起不來才退回主執行緒；辨識途中的錯誤照常往外丟
  return coreBoxes(canvas,tell,(w,h)=>{const c=document.createElement("canvas");c.width=w;c.height=h;return c})}

export const ppocrEngine={
  id:"ppocr",label:"PP-OCR（本機，免金鑰）",needsKey:false,local:true,
  size:"約 44 MB",note:"第一次使用會下載辨識模型約 44 MB（之後存在瀏覽器裡，離線也能用）。圖片不會上傳。",
  ready:()=>true,
  cached:()=>allCached(Object.values(FILES)),
  async extract(canvas,{onProgress}={}){const lines=await ocrBoxes(canvas,onProgress),e=parseLayout(lines,{W:canvas.width,H:canvas.height});e.lines=lines;return e}
};
