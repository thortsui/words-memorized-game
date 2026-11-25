// 提取引擎登記處。每個引擎的介面：
//   { id, label, needsKey, note, ready():boolean,
//     extract(canvas, {onProgress(text)}) => Promise<Entry[]> }
//   Entry = { en, pos, zh, ex, blank, unit, bbox?:{y0,y1}（整頁高度的百分比）, unsure?:boolean }
// 要加新引擎（或之後的「雙引擎交叉比對」）：寫一個檔案匯出同樣介面的物件，加進 ENGINES 即可。
import { claudeEngine } from './claude.js';
import { ocrEngine } from './ocr.js';

export const ENGINES=[claudeEngine,ocrEngine];
export const getEngine=id=>ENGINES.find(e=>e.id===id)||ENGINES[0];
