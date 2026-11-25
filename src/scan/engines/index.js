// 提取引擎登記處。每個引擎的介面：
//   { id, label, needsKey, local, size, note, ready():boolean, cached?():Promise<boolean>,
//     extract(canvas, {onProgress(text)}) => Promise<Entry[]> }
//   Entry = { en, pos, zh, ex, blank, unit, bbox?:{y0,y1,x0?,x1?}（整頁的百分比）, unsure?:boolean }
//   本機 OCR 引擎回傳的陣列另外帶 .lines（原始文字框），除錯與量測正確率用。
// 預設流程只用免金鑰、在瀏覽器本機執行的兩個引擎互相複核（主引擎 PP-OCR、複核 tesseract）；
// Claude 要自備 API 金鑰而且會計費，收在「進階」裡，預設不啟用。
import { ppocrEngine } from './ppocr.js';
import { ocrEngine } from './tesseract.js';
import { claudeEngine } from './claude.js';

export const ENGINES=[ppocrEngine,ocrEngine,claudeEngine];
export const FREE=ENGINES.filter(e=>!e.needsKey);
export const getEngine=id=>ENGINES.find(e=>e.id===id)||null;
