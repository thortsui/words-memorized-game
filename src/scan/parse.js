// OCR 文字的規則式版面解析（純函式，可在 Node 測試）。
// 兩個本機 OCR 引擎都只給「文字框＋座標」，條目結構（英文／詞性／中文／例句／blank／單元）全部在這裡組出來：
//   parseLayout(boxes,{W,H})：依座標分欄 → 併成橫列 → parseRows
//   parseRows(rows)：「英文＋詞性＋中文」開頭的列是一筆，後面的英文列併為例句（處理換行、連字號斷字）
//   parseLines / parseOcr：只有逐行文字（沒有 x 座標）時用
import { clozeAns } from '../core/grading.js';

const CJK=/[㐀-鿿]/, CJKP="㐀-鿿，。、；：！？（）「」『』…—";
const POSW="n|v|vt|vi|adj|adv|prep|conj|pron|int|interj|aux|art|det|num|abbr|phr";
// 行尾的詞性：n. / v., n. / adj./adv. / (v.) / n.[C]；OCR 常把句點看成逗號，所以結尾的 , 也收
const POS_END=new RegExp(`(?:^|\\s|\\()((?:${POSW})\\s?[.,](?:\\s?\\[[A-Za-z]{1,2}\\])?(?:\\s?[,/&;]?\\s?(?:${POSW})\\s?[.,](?:\\s?\\[[A-Za-z]{1,2}\\])?)*)\\)?\\s*$`);   // 只收小寫：大寫的 N. / V. 是片語裡的文法記號
const EN_OK=/^[A-Za-z][A-Za-z'.\/\-+ ()…,]*$/;
// 側邊單元標籤：NO.307 Unit 5、Unit 5、Key Phrases
const UNIT=/^\s*((?:NO\.?\s*\d+\s*)?(?:Unit\s*\d+|Key\s*Phrases?)|NO\.?\s*\d+)(?=$|[^A-Za-z0-9])/i;
const GRAM=/\b(?:N|V|O|S|Adj|Adv)\.|\bV-ing\b|\bp\.p\.|\bsb\b|\bsth\b|\bone's\b|\boneself\b|\.\.\.|…/g;

// 統一引號／破折號寫法、去掉中文字之間的空白（tesseract 常在中文字間插空白）
export const tidy=s=>String(s||"").replace(/[|｜¦]/g," ").replace(/[’‘`´]/g,"'").replace(/[“”]/g,'"').replace(/\s+/g," ")
  .replace(new RegExp(`([${CJKP}])\\s+(?=[${CJKP}])`,"g"),"$1")
  .replace(/([㐀-鿿）])\s*([;,:])\s*(?=[㐀-鿿（])/g,(m,a,p)=>a+({";":"；",",":"，",":":"："})[p])
  .replace(/([㐀-鿿；，、])\s*\(\s*([^()]*[㐀-鿿…][^()]*?)\s*\)/g,"$1（$2）").trim();   // 中文之間的半形標點是 OCR 寫法，換回全形
const fixPos=p=>(p.match(/(interj|prep|conj|pron|abbr|adj|adv|aux|art|det|num|phr|int|vt|vi|n|v)\s?[.,]?(\s?\[[A-Za-z]{1,2}\])?/g)||[]).map(t=>{const m=t.match(/^([A-Za-z]+)\s?[.,]?\s?(\[[A-Za-z]{1,2}\])?/);return m[1].toLowerCase()+"."+(m[2]||"")}).join(", ");
const unitName=u=>u.replace(/\s+/g," ").replace(/^no\.?\s*/i,"NO.").replace(/unit\s*/i,"Unit ").replace(/key\s*phrases?/i,"Key Phrases").replace(/(\d)(Unit)/,"$1 $2").trim();
const words=s=>(s.match(/[A-Za-z][A-Za-z'\-]*/g)||[]);

// 例句（常附中文翻譯）不能被當成條目開頭：大寫開頭、三個字以上，而且句尾有標點或很長
function isSentence(left){const t=left.replace(GRAM," ").replace(/\s+/g," ").trim(),n=words(t).length;
  return /^["']?[A-Z][a-z']*[ ,]/.test(t)&&n>=3&&(/[.?!]["']?$/.test(t)||n>=6||/ (is|are|was|were|has|have|had|will|can) /.test(t))}

// 判斷一列是不是條目開頭。回傳 {en,pos,zh} 或 null
export function parseHead(line){let l=line.replace(/^[\s*＊•·.□■◆▲○●✓☐\-–]+/,"").replace(/^\d{1,4}[.)、]?\s+(?=[A-Za-z])/,"");
  const ci=l.search(/[㐀-鿿（]/);let left=ci<0?l:l.slice(0,ci),zh=ci<0?"":l.slice(ci).trim();
  if(zh&&!CJK.test(zh))return null;
  // 音標：[...]、含非 ASCII 字元的 /.../
  left=left.replace(/\[[^\]]*[^A-Za-z\]][^\]]*\]|［[^］]*］/g," ").replace(/\/[^\/\s]*[^\x00-\x7f][^\/]*\//g," ").replace(/\s+/g," ").trim().replace(/[(\[]\s*$/,"").trim();
  if(!left)return null;
  let pos="";const pm=left.match(POS_END);
  if(pm){pos=fixPos(pm[1]);left=left.slice(0,pm.index).trim().replace(/\($/,"").trim()}
  else{const cm=left.match(/^([A-Za-z][A-Za-z'\-]*)\s+((?:N|V|Vt|Vi|Adj|Adv|Prep|Conj|Pron)[.,])$/);if(cm){left=cm[1];pos=fixPos(cm[2].toLowerCase())}} // 單一個字後面的大寫詞性（OCR 把 v. 看成 V.）
  if(!zh&&!pos)return null;                       // 沒有中文時，至少要有詞性才算開頭（中文在下一列）
  const en=left.replace(/[,;:]$/,"").trim();
  if(!en||!EN_OK.test(en)||en.replace(/[^A-Za-z]/g,"").length<2||words(en).length>9)return null;
  if(/^(NO\b|Unit\b|Key\s+Phrases?)/i.test(en))return null;
  if(!pos&&isSentence(en))return null;
  return{en,pos:pos||(/\s/.test(en)?"片語":""),zh}}

// 例句裡對應這個字或片語的實際字形（dye → dyed、give away → giving away）；找不到給空字串
export function deriveBlank(en,pos,ex){if(!ex)return"";
  const ph=/片語|phr/i.test(pos||"")||/\s/.test(en.trim());if(!ph)return clozeAns({en,pos:pos||"",ex,blank:""});
  if(GRAM.test(en)){GRAM.lastIndex=0;return""}GRAM.lastIndex=0;
  const t=en.toLowerCase().match(/[a-z']+/g)||[];if(t.length<2||/[\/()]/.test(en))return"";
  const re=/[A-Za-z'\-]+/g,toks=[];let m;while((m=re.exec(ex)))toks.push({w:m[0].toLowerCase(),i:m.index,e:m.index+m[0].length});
  const stem=t[0].slice(0,Math.max(2,t[0].length-(t[0].length>3?1:0)));
  for(let i=0;i+t.length<=toks.length;i++){if(!(toks[i].w===t[0]||(toks[i].w.startsWith(stem)&&toks[i].w.length<=t[0].length+4)))continue;
    let ok=true;for(let k=1;k<t.length;k++)if(toks[i+k].w!==t[k]){ok=false;break}
    if(ok)return ex.slice(toks[i].i,toks[i+t.length-1].e)}
  return""}

// rows：[{text, x0?,y0?,x1?,y1?}]（座標單位隨意，回傳的 bbox 沿用同一單位）。opt.units：[{y,unit}] 已知的側邊標籤
export function parseRows(rows,opt={}){const out=[];let cur=null,unit="";const labels=(opt.units||[]).slice().sort((a,b)=>a.y-b.y);
  const grow=r=>{if(!cur||r.y0==null)return;if(!cur.bbox){cur.bbox={y0:r.y0,y1:r.y1};if(r.x0!=null){cur.bbox.x0=r.x0;cur.bbox.x1=r.x1}return}
    cur.bbox.y0=Math.min(cur.bbox.y0,r.y0);cur.bbox.y1=Math.max(cur.bbox.y1,r.y1);if(r.x0!=null&&cur.bbox.x0!=null){cur.bbox.x0=Math.min(cur.bbox.x0,r.x0);cur.bbox.x1=Math.max(cur.bbox.x1,r.x1)}};
  for(const raw of rows){let l=tidy(raw.text);if(!l)continue;
    // 單元標籤：整列沒有中文、以標籤開頭 → 只記標籤，不進內文
    const um=l.match(UNIT);
    if(um){const rest=l.slice(um[0].length).trim();unit=unitName(um[1]);
      if(!CJK.test(rest)){continue}l=rest}
    const h=parseHead(l);
    if(h){const u=labels.length&&raw.y0!=null?(labels.filter(x=>x.y<=raw.y1).pop()||{}).unit||unit:unit;
      cur={en:h.en,pos:h.pos,zh:h.zh,ex:"",blank:"",unit:u,bbox:null};out.push(cur);grow(raw);continue}
    if(!cur)continue;
    const cj=(l.match(/[㐀-鿿]/g)||[]).length,la=(l.match(/[A-Za-z]/g)||[]).length;
    if(cj&&cj>=la){ // 以中文為主的列：還沒有例句 → 中文解釋換行；已有例句 → 例句的中文翻譯（不收，但算進裁切範圍）
      if(!cur.ex)cur.zh=tidy(cur.zh+l);grow(raw);continue}
    if(!la)continue;
    let e=l.replace(/[㐀-鿿（「].*$/,"").replace(/^[•·*▶►→\-–]\s*/,"").replace(/^(?:e\.g\.|ex[.:]|例[:：])\s*/i,"").trim();if(!e)continue;
    if(!cur.ex&&!/^["'(]?[A-Z0-9]/.test(e)&&words(e).length<3)continue;
    // 換行：上一列以連字號結尾、這列小寫開頭 → 接回同一個字
    if(cur.ex&&/[A-Za-z]-$/.test(cur.ex)&&/^[a-z]/.test(e))cur.ex=cur.ex.slice(0,-1)+e;else cur.ex=(cur.ex+" "+e).trim();
    grow(raw)}
  return out.filter(x=>x.en&&x.zh).map(x=>({...x,zh:x.zh.trim(),blank:deriveBlank(x.en,x.pos,x.ex)}))}

/* ----- 有座標的文字框 → 分欄 → 橫列 ----- */
// 找左右兩欄之間的空白帶：中間 30%–70% 有一條沒有文字框的直帶，而且兩邊各自都有中文和英文
export function splitColumns(boxes,W){if(boxes.length<8)return[boxes];const x0=Math.min(...boxes.map(b=>b.x0)),x1=Math.max(...boxes.map(b=>b.x1)),span=x1-x0;if(span<=0)return[boxes];
  const N=240,cov=new Uint16Array(N);for(const b of boxes){const a=Math.max(0,Math.floor((b.x0-x0)/span*N)),z=Math.min(N-1,Math.ceil((b.x1-x0)/span*N)-1);for(let i=a;i<=z;i++)cov[i]++}
  const tol=Math.max(1,Math.floor(boxes.length*.04));let best=null,s=-1;
  for(let i=Math.floor(N*.3);i<=Math.ceil(N*.7);i++){if(cov[i]<=tol){if(s<0)s=i}else if(s>=0){if(!best||i-s>best[1]-best[0])best=[s,i];s=-1}}
  if(s>=0){const e=Math.ceil(N*.7)+1;if(!best||e-s>best[1]-best[0])best=[s,e]}
  if(!best||(best[1]-best[0])/N<.02)return[boxes];
  const cut=x0+(best[0]+best[1])/2/N*span,L=[],R=[];for(const b of boxes)((b.x0+b.x1)/2<cut?L:R).push(b);
  const ok=g=>g.filter(b=>CJK.test(b.text)).length>=3&&g.filter(b=>/[A-Za-z]{3}/.test(b.text)&&!CJK.test(b.text)).length>=3&&g.filter(b=>/[A-Za-z]{2}/.test(b.text)).length>=4;
  // 表格式版面（左邊全英文、右邊全中文）不是兩欄：兩邊都要各自有「英文在左、中文在右」的列
  if(!ok(L)||!ok(R))return[boxes];
  const hasHead=g=>groupRows(g).some(r=>parseHead(tidy(r.text)));if(!hasHead(L)||!hasHead(R))return[boxes];
  return[L,R]}

// 同一欄裡，垂直方向重疊過半的框併成一列，列內由左到右
export function groupRows(boxes){const bs=boxes.slice().sort((a,b)=>(a.y0+a.y1)-(b.y0+b.y1)),rows=[];
  for(const b of bs){const h=b.y1-b.y0;let hit=null;
    for(let i=rows.length-1;i>=0&&i>=rows.length-4;i--){const r=rows[i],ov=Math.min(r.y1,b.y1)-Math.max(r.y0,b.y0);if(ov>=.5*Math.min(h,r.y1-r.y0)){hit=r;break}}
    if(hit){hit.items.push(b);hit.y0=Math.min(hit.y0,b.y0);hit.y1=Math.max(hit.y1,b.y1);hit.x0=Math.min(hit.x0,b.x0);hit.x1=Math.max(hit.x1,b.x1)}
    else rows.push({items:[b],x0:b.x0,y0:b.y0,x1:b.x1,y1:b.y1})}
  rows.sort((a,b)=>a.y0-b.y0);
  return rows.map(r=>({text:r.items.sort((a,b)=>a.x0-b.x0).map(b=>b.text).join(" "),x0:r.x0,y0:r.y0,x1:r.x1,y1:r.y1}))}

// boxes：[{text,x0,y0,x1,y1}]（像素）。回傳條目，bbox 換成整頁百分比（y0,y1,x0,x1：這一筆自己的範圍，核對時裁圖用）
export function parseLayout(boxes,{W,H}){const bs=boxes.filter(b=>b&&tidy(b.text)),units=[],flow=[];
  for(const b of bs){const t=tidy(b.text),um=t.match(UNIT);if(um&&!CJK.test(t)&&words(t.slice(um[0].length)).length<=4)units.push(b);else flow.push(b)}
  const cols=splitColumns(flow,W),out=[];
  cols.forEach((col,ci)=>{
    // 側邊標籤不進內文，只記位置；兩欄時歸到所在的那一欄
    const edge=cols.length>1?(Math.max(...cols[0].map(b=>b.x1))+Math.min(...cols[1].map(b=>b.x0)))/2:0;
    const mine=cols.length<2?units:units.filter(u=>((u.x0+u.x1)/2<edge)===(ci===0));
    const rows=groupRows(col),labels=mine.map(u=>({y:u.y0,unit:unitName(tidy(u.text).match(UNIT)[1])}));
    for(const e of parseRows(rows,{units:labels})){const b=e.bbox;
      out.push({...e,bbox:b?{y0:b.y0/H*100,y1:b.y1/H*100,...(b.x0!=null?{x0:b.x0/W*100,x1:b.x1/W*100}:{})}:null})}});
  return out}

// lines：[{text, y0, y1}]（y 為頁面百分比，可省略）。回傳的每筆帶 bbox（有 y 才有）。
export function parseLines(lines){return parseRows(lines.map(l=>({text:l.text,y0:l.y0==null?null:l.y0,y1:l.y1==null?null:l.y1}))).map(e=>({...e,bbox:e.bbox?{y0:e.bbox.y0,y1:e.bbox.y1}:null}))}
export const parseOcr=text=>parseLines(text.split("\n").map(t=>({text:t}))).map(({bbox,...x})=>x);
