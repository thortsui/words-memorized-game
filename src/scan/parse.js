// OCR 文字的規則式解析（純函式）：「英文＋詞性＋中文」開頭的行是一筆，後續英文行併為例句。
const HEAD=/^[*＊•·.\s]*([A-Za-z][A-Za-z'’.\/\-+ ()…]*?)\s*(?:\[[^\]]*\]|［[^］]*］)?\s*((?:n|v|adj|adv|prep|conj)\.(?:\s*,\s*(?:n|v|adj|adv)\.)?)?\s*([㐀-鿿（(].*)$/;
const clean=s=>s.replace(/[|｜]/g," ").replace(/\s+/g," ").trim();

// lines：[{text, y0, y1}]（y 為頁面百分比，可省略）。回傳的每筆帶 bbox（有 y 才有）。
export function parseLines(lines){const out=[];let cur=null;
  const grow=l=>{if(cur&&l.y0!=null&&cur.bbox){cur.bbox.y0=Math.min(cur.bbox.y0,l.y0);cur.bbox.y1=Math.max(cur.bbox.y1,l.y1)}};
  for(const raw of lines){const l=clean(raw.text);if(!l)continue;const m=l.match(HEAD);
    if(m&&m[1].trim().length>1&&/[㐀-鿿]/.test(m[3])&&!/^(NO|Unit|Key)/i.test(m[1].trim())){const en=m[1].replace(/[\[(]\s*$/,"").trim();cur={en,pos:m[2]||(/\s/.test(en)?"片語":""),zh:m[3].trim(),ex:"",bbox:raw.y0!=null?{y0:raw.y0,y1:raw.y1}:null};out.push(cur)}
    else if(cur){if(/[㐀-鿿]/.test(l)&&!cur.ex){cur.zh+=l;grow(raw)}else if(/^[A-Z"“']/.test(l)||cur.ex){const e=l.replace(/[㐀-鿿].*$/,"").trim();if(e){cur.ex=(cur.ex+" "+e).trim();grow(raw)}}}}
  return out.filter(x=>x.en&&x.zh)}
export const parseOcr=text=>parseLines(text.split("\n").map(t=>({text:t}))).map(({bbox,...x})=>x);
