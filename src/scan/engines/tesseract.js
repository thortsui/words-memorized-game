// 提取引擎：免費 OCR（tesseract.js 5.1.1，eng+chi_tra），用規則式解析成條目
import { loadScript } from '../../core/util.js';
import { parseLines } from '../parse.js';

let worker=null,report=null;
export const ocrEngine={
  id:"ocr",label:"免費 OCR（準確度較低）",needsKey:false,
  note:"第一次會下載中英文辨識資料（約 10–20MB）",
  ready:()=>true,
  async extract(canvas,{onProgress}={}){report=onProgress||null;
    if(!window.Tesseract)await loadScript("https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js");
    if(!worker)worker=await window.Tesseract.createWorker(["eng","chi_tra"],1,{logger:m=>{if(m.status&&report)report("OCR："+m.status+(m.progress?" "+Math.round(m.progress*100)+"%":""))}});
    const {data}=await worker.recognize(canvas);const H=canvas.height||1;
    // 有逐行座標就帶上位置（頁面百分比），核對時可以裁出該筆的小圖
    const lines=Array.isArray(data.lines)&&data.lines.length?data.lines.map(l=>({text:l.text||"",y0:l.bbox?l.bbox.y0/H*100:null,y1:l.bbox?l.bbox.y1/H*100:null})):String(data.text||"").split("\n").map(t=>({text:t}));
    return parseLines(lines)}
};
