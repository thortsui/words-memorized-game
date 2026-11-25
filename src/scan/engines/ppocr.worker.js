// PP-OCR 的 Web Worker：模型下載、載入、推論都在這裡，主執行緒只送圖、收進度與結果。
import { ocrBoxes } from './ppocr-core.js';

const mk=(w,h)=>new OffscreenCanvas(w,h);
self.onmessage=async e=>{const {id,bmp}=e.data;
  try{const boxes=await ocrBoxes(bmp,t=>self.postMessage({id,prog:t}),mk);self.postMessage({id,boxes})}
  catch(err){self.postMessage({id,error:String(err&&err.message||err)})}
  finally{try{bmp.close()}catch(_){}}};
