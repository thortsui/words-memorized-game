// OCR 文字的規則式版面解析（純函式，可在 Node 測試）。
// 兩個本機 OCR 引擎都只給「文字框＋座標」，條目結構（英文／詞性／中文／例句／blank／單元）全部在這裡組出來：
//   parseLayout(boxes,{W,H})：依座標分欄 → 併成橫列 → 逐列分類 → 條目；另外回傳「覆蓋率」（每個文字框被誰用了）
//   parseRows(rows)／parseLines／parseOcr：只有逐列文字時用
// 兩個引擎共用這個解析器，所以解析器自己出的錯兩邊會一模一樣。對策有三層（都不靠「兩邊一致」）：
//   1. 每一列一定被分類：條目開頭／中文／例句／例句翻譯／同反義字列／單元標籤／頁首頁尾／雜訊／「沒用到」。
//      看不懂的列絕不硬接到上一筆，而是讓上一筆收尾、自己留在「沒用到」。
//   2. 覆蓋率：parseLayout 回傳的 .cover 記錄每個文字框的用途，沒用到的框由上傳頁列出來逼使用者處理。
//   3. 結構旗標（entry.flags）：例句後面緊接著沒收進去的文字、同一列的字相隔很遠、範圍裡有別人的字…… → 一律要人工確認。
import { clozeAns } from '../core/grading.js';
import { isInflection } from './inflect.js';

const CJK=/[㐀-鿿]/, CJKP="㐀-鿿，。、；：！？（）「」『』…—";
const POSW="interj|prep|conj|pron|abbr|adj|adv|aux|art|det|num|phr|int|vt|vi|n|v";
// 行尾的詞性：n. / v., n. / v./n. / (v.) / n.[C]；OCR 常把句點看成逗號，所以結尾的 , 也收。只收小寫：大寫的 N. / V. 是片語裡的文法記號
const POS_END=new RegExp(`(?:^|\\s|\\()((?:${POSW})\\s?[.,](?:\\s?\\[[A-Za-z]{1,2}\\])?(?:\\s?[,/&;]?\\s?(?:${POSW})\\s?[.,](?:\\s?\\[[A-Za-z]{1,2}\\])?)*)\\)?\\s*$`);
const EN_OK=/^[A-Za-z][A-Za-z'.\/\-+ ()…,~]*$/;
// 單元標籤：NO.307 Unit 5、Unit 5、Key Phrases
const UNIT=/^\s*((?:NO\.?\s*\d+\s*)?(?:Unit\s*\d+|Key\s*Phrases?)|NO\.?\s*\d+)(?=$|[^A-Za-z0-9])/i;
const GRAM=/\b(?:N|V|O|S|Adj|Adv)\.|\bV-ing\b|\bp\.p\.|\bsb\b|\bsth\b|\bone's\b|\boneself\b|\.\.\.|…|~/g;
// 同義／反義／比較／衍生字列的開頭記號
const NOTE=/^(?:=|≒|≈|↔|⇔|⟷|←→|<[-=]+>|≠|→|⇒|▶|►|syn\b\.?|ant\b\.?|cf\.|同[:：義]|反[:：義]|比較[:：]|衍生?[:：])/i;
const PAGENO=/^[-–—\s]*\d{1,4}[-–—\s]*$/;
const SENSE=/^(\(?\d{1,2}[.)]|[①-⑩])\s*(?=[㐀-鿿（])/;
export const TERM=/[.?!]["'”’)\]]*$/;                       // 例句的結尾：句號、問號、驚嘆號（後面可以有引號）

// 統一引號／破折號寫法、去掉中文字之間的空白（tesseract 常在中文字間插空白）
export const tidy=s=>String(s||"").replace(/[|｜¦]/g," ").replace(/[’‘`´]/g,"'").replace(/[“”]/g,'"').replace(/～/g,"~").replace(/\s+/g," ")
  .replace(new RegExp(`([${CJKP}])\\s+(?=[${CJKP}])`,"g"),"$1")
  .replace(/([㐀-鿿）])\s*([;,:])\s*(?=[㐀-鿿（])/g,(m,a,p)=>a+({";":"；",",":"，",":":"："})[p])
  .replace(/([㐀-鿿；，、])\s*\(\s*([^()]*[㐀-鿿…][^()]*?)\s*\)/g,"$1（$2）").trim();   // 中文之間的半形標點是 OCR 寫法，換回全形
// 中文解釋裡的刪節號：六個點 → ……、三個點 → …（書上印的是全形刪節號，OCR 讀成一串句點）
// 點數不是 3 或 6 的留成一串句點，後面會標成疑點（FLAG.dots）
const zhDots=s=>s.replace(/⋯/g,"…").replace(/\s*(?:[.…]{2,}|…)\s*/g,m=>{const t=m.trim(),n=[...t].reduce((a,c)=>a+(c==="…"?3:1),0);return n===6?"……":n===3?"…":t.replace(/…/g,"...")});
// 詞性：統一成小寫加句點；分隔符號照書上的（v./n. 不改成 v., n.）
function fixPos(p){const re=new RegExp(`(${POSW})\\s?[.,]?(\\s?\\[[A-Za-z]{1,2}\\])?`,"g");let out="",last=0,m;
  while((m=re.exec(p))){const sep=p.slice(last,m.index);if(out)out+=sep.includes("/")?"/":sep.includes("&")?" & ":", ";out+=m[1].toLowerCase()+"."+(m[2]||"").trim();last=re.lastIndex}return out}
const unitName=u=>u.replace(/\s+/g," ").replace(/^no\.?\s*/i,"NO.").replace(/unit\s*/i,"Unit ").replace(/key\s*phrases?/i,"Key Phrases").replace(/(\d)(Unit)/,"$1 $2").trim();
const words=s=>(s.match(/[A-Za-z][A-Za-z'\-]*/g)||[]);

// 例句（常附中文翻譯）不能被當成條目開頭：大寫開頭、三個字以上，而且句尾有標點或很長
function isSentence(left){const t=left.replace(GRAM," ").replace(/\s+/g," ").trim(),n=words(t).length;
  return /^["']?[A-Z][a-z']*[ ,]/.test(t)&&n>=3&&(/[.?!]["']?$/.test(t)||n>=6||/ (is|are|was|were|has|have|had|will|can) /.test(t))}
const fullSentence=e=>/^(?:[A-Z]:\s*)?["'(]?[A-Z]/.test(e)&&TERM.test(e)&&words(e).length>=2;

// 判斷一列是不是條目開頭。回傳 {en,pos,zh}（多義條目另帶 sense:true）或 null
export function parseHead(line){let l=line.replace(/^[\s*＊•·.□■◆▲○●✓☐\-–]+/,"").replace(/^\(?\d{1,4}(?:[.)、]\s*|\s+)(?=[A-Za-z])/,"");
  const ci=l.search(/[㐀-鿿（]/);let left=ci<0?l:l.slice(0,ci),zh=ci<0?"":l.slice(ci).trim();
  if(zh&&!CJK.test(zh))return null;
  // 一字多義：「charge v. 1. 收費」的編號歸到中文那邊
  let sense="";const sm=zh&&left.match(/\s(\(?\d{1,2}[.)]|[①-⑩])\s*$/);if(sm){sense=sm[1];left=left.slice(0,sm.index)}
  // 音標：[...]（詞性後面的 [C]、[U] 不是音標）、含非 ASCII 字元的 /.../；OCR 漏掉右括號時切到詞性前
  left=left.replace(/［[^］]*］/g," ").replace(/\[[^\]]*\]/g,m=>/^\[(?:C|U|C, ?U|U, ?C|I|T|pl\.?|sing\.?)\]$/.test(m)?m:" ").replace(/\/[^\/\s]*[^\x00-\x7f][^\/]*\//g," ");
  if(left.includes("[")&&!/\[(?:C|U|I|T)/.test(left))left=left.replace(new RegExp(`\\[.*?(?=\\s(?:${POSW})\\s?[.,]|$)`)," ");
  left=left.replace(/\s+/g," ").trim().replace(/[(\[]\s*$/,"").trim();
  if(!left)return null;
  let pos="";const pm=left.match(POS_END);
  if(pm){pos=fixPos(pm[1]);left=left.slice(0,pm.index).trim().replace(/\($/,"").trim()}
  else{const cm=left.match(/^([A-Za-z][A-Za-z'\-]*)\s+((?:N|V|Vt|Vi|Adj|Adv|Prep|Conj|Pron)[.,])$/);if(cm){left=cm[1];pos=fixPos(cm[2].toLowerCase())}} // 單一個字後面的大寫詞性（OCR 把 v. 看成 V.）
  if(!zh&&!pos)return null;                       // 沒有中文時，至少要有詞性才算開頭（中文在下一列）
  const en=left.replace(/[,;:]$/,"").trim();
  if(!en||!EN_OK.test(en)||en.replace(/[^A-Za-z]/g,"").length<2||words(en).length>9)return null;
  if(/^(NO\b|Unit\b|Key\s+Phrases?)/i.test(en))return null;
  // 以 ... 或 ~ 結尾的是句型／片語（It is said that ...、be famous for ~），不是例句
  if(!pos&&!/(\.\.\.|…|~)$/.test(en)&&isSentence(en))return null;
  const h={en,pos:pos||(/\s/.test(en)?"片語":""),zh:zhDots(sense?sense+" "+zh:zh)};if(sense)h.sense=true;return h}

// 例句裡對應這個字或片語的實際字形（dye → dyed、give away → giving away）；找不到給空字串
export function deriveBlank(en,pos,ex){if(!ex)return"";
  const ph=/片語|phr/i.test(pos||"")||/\s/.test(en.trim());
  if(!ph){ // 單字：先找一模一樣的，再找規則／常見不規則變化（painter 不是 paint 的變化形），都沒有才退回字幹比對
    const toks=ex.match(/[A-Za-z][A-Za-z'\-]*/g)||[],k=s=>s.toLowerCase().replace(/[^a-z]/g,""),b=k(en);
    return toks.find(t=>k(t)===b)||toks.find(t=>isInflection(en,t))||(()=>{const c=clozeAns({en,pos:pos||"",ex,blank:""});return c&&!/(er|ers|or|ors)$/i.test(c)?c:""})()}
  GRAM.lastIndex=0;if(GRAM.test(en)){GRAM.lastIndex=0;return""}GRAM.lastIndex=0;
  const t=en.toLowerCase().match(/[a-z']+/g)||[];if(t.length<2||/[\/()]/.test(en))return"";
  const re=/[A-Za-z'\-]+/g,toks=[];let m;while((m=re.exec(ex)))toks.push({w:m[0].toLowerCase(),i:m.index,e:m.index+m[0].length});
  const stem=t[0].slice(0,Math.max(2,t[0].length-(t[0].length>3?1:0)));
  for(let i=0;i+t.length<=toks.length;i++){if(!(toks[i].w===t[0]||(toks[i].w.startsWith(stem)&&toks[i].w.length<=t[0].length+4)))continue;
    let ok=true;for(let k=1;k<t.length;k++)if(toks[i+k].w!==t[k]){ok=false;break}
    if(ok)return ex.slice(toks[i].i,toks[i+t.length-1].e)}
  return""}

export const FLAG={
  trail:"這一筆後面緊接著沒被收進條目的文字，可能其實是這一筆的一部分",
  wide:"同一列的文字相隔很遠，可能把左右兩欄併在一起了",
  multi:"例句是分開的兩列以上（或有對話），請確認沒有接到別筆的句子",
  sense:"一個字有好幾個編號的意思（1. 2. …），中文和例句是合併起來的，請確認",
  region:"這一筆的範圍裡有不屬於它的文字",
  mixed:"例句那一列的英文還沒到句尾就接了中文，可能混進了別筆或另一欄的內容",
  dots:"中文裡的刪節號點數不尋常，請對照原圖"};

// 逐列分類。rows：[{text, x0?,y0?,x1?,y1?, ids?, gap?}]（座標單位隨意）。opt.units：[{y,unit}] 已知的側邊標籤。
// 回傳 {entries, rows}：每一列多了 use（head／zh／ex／tr 例句翻譯／note 同反義字列／unit／hf 頁首頁尾／noise／null 沒用到）與 ei（屬於第幾筆）。
export function classifyRows(rows,opt={}){const out=[],labels=(opt.units||[]).slice().sort((a,b)=>a.y-b.y);let cur=null,unit="",orphan=false;
  const R=rows.map(r=>({...r,use:null,ei:-1}));
  // 收進目前這一筆。列內左右間隙很大（超過四倍字高）的列，可能是把兩欄併在一起了 → 記疑點
  const take=(r,use)=>{r.use=use;r.ei=out.length-1;cur.rows.push(r);if(r.y1!=null)cur.lastY1=r.y1;if(r.gap!=null&&r.h&&r.gap>4*r.h)cur.flags.add("wide")};
  // 單元標籤：取這一列上方最近的標籤；同一高度有好幾個標籤（左右兩欄各一個）時，取左右位置對得上的那個
  const unitOf=r=>{if(!labels.length||r.y0==null)return unit;const c=labels.filter(x=>x.y<=r.y1);if(!c.length)return unit;const top=c[c.length-1].y,hh=(r.y1-r.y0)||1,band=c.filter(x=>x.y>=top-1.5*hh);
    if(band.length<2||r.x0==null)return band[band.length-1].unit;const ok=band.filter(x=>x.x0!=null&&x.x0<=r.x0+2*hh).sort((a,b)=>a.x0-b.x0);return(ok.length?ok[ok.length-1]:band.slice().sort((a,b)=>(a.x0||0)-(b.x0||0))[0]).unit};
  // 例句的中文翻譯長什麼樣：以句號等結尾、或有逗號，或縮排和例句對齊。不像的（例如辨識壞掉的條目開頭）不能當翻譯吞掉
  const looksTr=(r,l,ind)=>/[。！？.!?]["」』）)]*$/.test(l)||/[，、]/.test(l)||(ind==="in"&&cur.exX!=null&&Math.abs(r.x0-cur.exX)<=.5*Math.max(1,cur.hh));
  for(const r of R){let l=tidy(r.text);if(!l||!/[A-Za-z0-9㐀-鿿]/.test(l)){r.use="noise";continue}
    if(PAGENO.test(l)){r.use="hf";continue}
    // 單元標籤：以標籤開頭而且後面不是一筆條目 → 整列當標籤（「Unit 3 校園生活」也是），目前這一筆到此為止
    const um=l.match(UNIT);
    if(um){const rest=l.slice(um[0].length).trim();unit=unitName(um[1]);if(!rest||!parseHead(rest)){r.use="unit";cur=null;orphan=false;continue}l=rest}
    const h=r.h!=null?r.h:(r.y1!=null?r.y1-r.y0:null),geo=cur&&r.x0!=null&&cur.hx!=null;
    const d=geo?(r.x0-cur.hx)/Math.max(1,cur.hh):0,ind=!geo?null:d>.5?"in":d<-.5?"out":"same";
    const far=!!(cur&&r.y0!=null&&cur.lastY1!=null&&r.y0-cur.lastY1>1.6*Math.max(cur.hh||0,h||0));
    // 同義／反義字列：算這一筆的附註，不進例句
    if(NOTE.test(l)){if(cur&&!orphan&&!far)take(r,"note");continue}
    // 一字多義的第二個以後的意思：「2. 充電」
    if(cur&&!orphan&&!far&&SENSE.test(l)){cur.zh=tidy(cur.zh+" "+l);cur.flags.add("sense");cur.senseOpen=true;take(r,"zh");continue}
    const hd=parseHead(l);
    // 例句後面那一列如果像「Mary 把頭髮染成紅色。」（沒有詞性，而且中文以句號結尾、或縮排和例句一樣）是例句的翻譯，不是新條目
    if(hd&&!hd.pos&&cur&&!orphan&&!far&&cur.ex&&TERM.test(cur.ex)&&(/[。！？]$/.test(hd.zh)||(ind==="in"&&cur.exX!=null&&Math.abs(r.x0-cur.exX)<=.5*Math.max(1,cur.hh)))){take(r,"tr");continue}
    if(hd){const u=unitOf(r);
      cur={en:hd.en,pos:hd.pos,zh:hd.zh,ex:"",unit:u,rows:[],flags:new Set(),hx:r.x0!=null?r.x0:null,hh:h,lastY1:null,exInd:null,senseOpen:!!hd.sense};if(hd.sense)cur.flags.add("sense");
      out.push(cur);orphan=false;take(r,"head");continue}
    if(!cur||orphan)continue;
    // 以下是條目裡面的列。看不懂的列不硬接：讓這一筆收尾（近的話加旗標），後面到下一筆開頭之前都留在「沒用到」
    const drop=()=>{if(!far)cur.flags.add("trail");orphan=true};
    if(far){drop();continue}
    if(cur.exInd==="in"&&(ind==="same"||ind==="out")){drop();continue}            // 例句有縮排的版面裡，回到左邊界的列應該是新條目，卻不是 → 看不懂
    const cj=(l.match(/[㐀-鿿]/g)||[]).length,la=(l.match(/[A-Za-z]/g)||[]).length;
    if(cj&&!cur.ex&&cj>=la){cur.zh=tidy(cur.zh+l);take(r,"zh");continue}          // 中文解釋換行
    if(cj&&cur.ex&&(TERM.test(cur.ex)||cj>=la)){if(looksTr(r,l,ind))take(r,"tr");else drop();continue}   // 例句的中文翻譯（可能夾英文人名）：不收，但算這一筆的
    if(!la){drop();continue}
    const e=l.replace(/[㐀-鿿（「].*$/,"").replace(/^[•·*\-–]\s*/,"").replace(/^(?:e\.g\.|ex[.:]|例[:：])\s*/i,"").trim();if(!e){drop();continue}
    if(cj&&!TERM.test(e))cur.flags.add("mixed");                                  // 這一列英文後面的中文被切掉了；英文如果還沒到句尾，切掉的就不是「例句翻譯」
    if(!cur.ex){if(!/^(?:[A-Z]:\s*)?["'(]?[A-Z0-9]/.test(e)&&words(e).length<3){drop();continue}cur.ex=e;cur.exInd=ind;cur.exX=r.x0!=null?r.x0:null;take(r,"ex");continue}
    if(!TERM.test(cur.ex)){ // 例句換行；上一列以連字號結尾、這列小寫開頭 → 接回同一個字
      if(/[A-Za-z]-$/.test(cur.ex)&&/^[a-z]/.test(e))cur.ex=cur.ex.slice(0,-1)+e;else cur.ex=cur.ex+" "+e;take(r,"ex");continue}
    // 例句已經結束了還有英文列：只有「新的一個意思的例句」或「完整的另一句」才接，而且要人工確認
    if(cur.senseOpen&&fullSentence(e)){cur.ex+=" "+e;cur.senseOpen=false;take(r,"ex");continue}
    if(fullSentence(e)&&ind!=="same"&&ind!=="out"||fullSentence(e)&&cur.exInd!=="in"&&ind!=="out"){cur.ex+=" "+e;cur.flags.add("multi");take(r,"ex");continue}
    drop()}
  // 頁首：第一筆之前、不可能是條目的列（沒有同時含英文和中文）。頁尾：最後面一段離內文很遠、沒有中文的列。
  const first=R.findIndex(r=>r.use==="head");
  R.forEach((r,i)=>{if(r.use===null&&(first<0||i<first)){const t=tidy(r.text);if(!(/[A-Za-z]{2}/.test(t)&&CJK.test(t)))r.use="hf"}});
  let lastUsed=-1;R.forEach((r,i)=>{if(r.ei>=0)lastUsed=i});
  if(lastUsed>=0&&lastUsed<R.length-1){const t=R.slice(lastUsed+1),a=R[lastUsed],b=t.find(r=>r.use===null);
    if(b&&b.y0!=null&&a.y1!=null&&b.y0-a.y1>1.6*Math.max(a.y1-a.y0,b.y1-b.y0)&&t.every(r=>r.use!==null||!CJK.test(r.text)))t.forEach(r=>{if(r.use===null)r.use="hf"})}
  const entries=out.map((c,i)=>{const zh=zhDots(c.zh.trim()),fl=c.flags;if(/\.{2,}/.test(zh))fl.add("dots");
    const used=c.rows.filter(r=>r.y0!=null),bbox=used.length?{y0:Math.min(...used.map(r=>r.y0)),y1:Math.max(...used.map(r=>r.y1))}:null;
    if(bbox&&used.every(r=>r.x0!=null)){bbox.x0=Math.min(...used.map(r=>r.x0));bbox.x1=Math.max(...used.map(r=>r.x1))}
    const ids=u=>c.rows.filter(r=>u.includes(r.use)).flatMap(r=>r.ids||[]);
    return{en:c.en,pos:c.pos,zh,ex:c.ex,blank:deriveBlank(c.en,c.pos,c.ex),unit:c.unit,bbox,flags:[...fl].map(k=>FLAG[k]),src:{head:ids(["head"]),zh:ids(["zh"]),ex:ids(["ex"]),other:ids(["tr","note"])},_i:i}});
  // 沒有中文的「開頭」（只有英文＋詞性，中文也沒在下一列）不算條目：它用掉的列放回「沒用到」
  const keep=entries.map(e=>!!(e.en&&e.zh)),map=[];let n=0;keep.forEach((k,i)=>map[i]=k?n++:-1);
  R.forEach(r=>{if(r.ei>=0){r.ei=map[r.ei];if(r.ei<0)r.use=null}});
  return{entries:entries.filter((e,i)=>keep[i]).map(({_i,...e})=>e),rows:R}}

export const parseRows=(rows,opt)=>classifyRows(rows,opt).entries;

/* ----- 有座標的文字框 → 分欄 → 橫列 ----- */
const med=a=>{const s=a.slice().sort((x,y)=>x-y);return s.length?s[s.length>>1]:0};
// 分欄：找「整頁從上到下都沒有文字框跨過」的直向空白帶（看文字框的 x 分布，不要求每欄至少幾筆），可以遞迴分成三欄以上。
// 表格式版面（左邊全英文、右邊全中文）中間也有空白帶，所以兩邊都要各自有完整的條目開頭（英文＋中文在同一列）才算兩欄。
export function splitColumns(boxes,W,depth=0){if(boxes.length<4||depth>2)return[boxes];const x0=Math.min(...boxes.map(b=>b.x0)),x1=Math.max(...boxes.map(b=>b.x1)),span=x1-x0;if(span<=0)return[boxes];
  const mh=med(boxes.map(b=>b.y1-b.y0)),minGap=Math.max(.008*(W||span),.6*mh),N=800;   // 空白帶至少要有 0.6 個字高那麼寬（字和字之間的空白大約 0.3 個字高）
  const find=bs=>{const cov=new Uint16Array(N);for(const b of bs){const a=Math.max(0,Math.floor((b.x0-x0)/span*N)),z=Math.min(N-1,Math.ceil((b.x1-x0)/span*N)-1);for(let i=a;i<=z;i++)cov[i]++}
    let best=null,s=-1;const lo=Math.floor(N*.15),hi=Math.ceil(N*.85);
    for(let i=lo;i<=hi;i++){if(cov[i]===0){if(s<0)s=i}else if(s>=0){if(!best||i-s>best[1]-best[0])best=[s,i];s=-1}}
    if(s>=0&&(!best||hi+1-s>best[1]-best[0]))best=[s,hi+1];
    return best&&(best[1]-best[0])/N*span>=minGap?x0+(best[0]+best[1])/2/N*span:null};
  let cut=find(boxes);
  if(cut==null){ // 頁首頁尾常有橫跨整頁的一行：去掉最上面和最下面 6% 的框再找一次
    const ys=Math.min(...boxes.map(b=>b.y0)),ye=Math.max(...boxes.map(b=>b.y1)),m=(ye-ys)*.06;cut=find(boxes.filter(b=>b.y0>ys+m&&b.y1<ye-m))}
  if(cut==null)return[boxes];
  const L=[],Rr=[];for(const b of boxes)((b.x0+b.x1)/2<cut?L:Rr).push(b);
  const hasHead=g=>groupRows(g).some(r=>{const t=tidy(r.text).replace(UNIT,"").trim(),h=parseHead(t);return h&&h.zh});
  if(!L.length||!Rr.length||!hasHead(L)||!hasHead(Rr))return[boxes];
  return[...splitColumns(L,W,depth+1),...splitColumns(Rr,W,depth+1)]}

// 同一欄裡，垂直方向重疊過半的框併成一列，列內由左到右。每列帶 ids（用到哪些框）、gap（列內最大的左右間隙）、h（框的高度中位數）
export function groupRows(boxes){const bs=boxes.slice().sort((a,b)=>(a.y0+a.y1)-(b.y0+b.y1)),rows=[];
  for(const b of bs){const h=b.y1-b.y0;let hit=null;
    for(let i=rows.length-1;i>=0&&i>=rows.length-4;i--){const r=rows[i],ov=Math.min(r.y1,b.y1)-Math.max(r.y0,b.y0);if(ov>=.5*Math.min(h,r.y1-r.y0)){hit=r;break}}
    if(hit){hit.items.push(b);hit.y0=Math.min(hit.y0,b.y0);hit.y1=Math.max(hit.y1,b.y1);hit.x0=Math.min(hit.x0,b.x0);hit.x1=Math.max(hit.x1,b.x1)}
    else rows.push({items:[b],x0:b.x0,y0:b.y0,x1:b.x1,y1:b.y1})}
  rows.sort((a,b)=>a.y0-b.y0);
  return rows.map(r=>{const it=r.items.sort((a,b)=>a.x0-b.x0);let gap=0;for(let i=1;i<it.length;i++)gap=Math.max(gap,it[i].x0-it[i-1].x1);
    return{text:it.map(b=>b.text).join(" "),x0:r.x0,y0:r.y0,x1:r.x1,y1:r.y1,ids:it.map(b=>b.i).filter(i=>i!=null),gap,h:med(it.map(b=>b.y1-b.y0))}})}

// boxes：[{text,x0,y0,x1,y1}]（像素）。回傳條目陣列：bbox 是整頁百分比（y0,y1,x0,x1：這一筆自己的範圍，核對時裁圖用），
// src 記每個欄位來自哪些文字框，flags 是結構上的疑點。陣列另外帶 .cover：
//   {W,H,boxes:[{i,text,x0,y0,x1,y1,use,ei}]}，use＝head／zh／ex／tr／note／unit／hf／noise／null（沒被任何條目用到）
export function parseLayout(boxes,{W,H}){const bs=boxes.map((b,i)=>({text:String(b.text||""),x0:b.x0,y0:b.y0,x1:b.x1,y1:b.y1,i})),cov=bs.map(b=>({...b,use:null,ei:-1})),units=[],flow=[];
  for(const b of bs){const t=tidy(b.text),um=t.match(UNIT);if(!t){cov[b.i].use="noise";continue}
    if(um&&!CJK.test(t)&&words(t.slice(um[0].length)).length<=4){units.push(b);cov[b.i].use="unit"}else flow.push(b)}
  const cols=splitColumns(flow,W),out=[];
  const cx=cols.map(c=>({x0:Math.min(...c.map(b=>b.x0)),x1:Math.max(...c.map(b=>b.x1))}));
  cols.forEach((col,ci)=>{
    // 側邊標籤不進內文，只記位置；多欄時歸到水平位置最近的那一欄
    const near=u=>{const c=(u.x0+u.x1)/2;let best=0,bd=1e18;cx.forEach((k,i)=>{const d=c<k.x0?k.x0-c:c>k.x1?c-k.x1:0;if(d<bd){bd=d;best=i}});return best};
    const rows=groupRows(col),labels=units.filter(u=>cols.length<2||near(u)===ci).map(u=>({y:u.y0,x0:u.x0,unit:unitName(tidy(u.text).match(UNIT)[1])}));
    const res=classifyRows(rows,{units:labels}),base=out.length;
    for(const r of res.rows)for(const id of r.ids||[]){cov[id].use=r.use;cov[id].ei=r.ei>=0?base+r.ei:-1}
    for(const e of res.entries){const b=e.bbox;out.push({...e,_px:b,bbox:b?{y0:b.y0/H*100,y1:b.y1/H*100,...(b.x0!=null?{x0:b.x0/W*100,x1:b.x1/W*100}:{})}:null})}});
  // 範圍檢查：一筆條目的外框裡如果有不屬於它的文字框（別筆的、或沒人用的），就是疑點
  out.forEach((e,ei)=>{const b=e._px;if(b&&b.x0!=null&&cov.some(c=>c.ei!==ei&&c.use!=="unit"&&c.use!=="noise"&&(c.x0+c.x1)/2>b.x0&&(c.x0+c.x1)/2<b.x1&&(c.y0+c.y1)/2>b.y0&&(c.y0+c.y1)/2<b.y1))e.flags=[...e.flags,FLAG.region];delete e._px});
  out.cover={W,H,boxes:cov};return out}

// lines：[{text, y0, y1}]（y 為頁面百分比，可省略）。回傳的每筆帶 bbox（有 y 才有）。
export function parseLines(lines){return parseRows(lines.map(l=>({text:l.text,y0:l.y0==null?null:l.y0,y1:l.y1==null?null:l.y1}))).map(e=>({...e,bbox:e.bbox?{y0:e.bbox.y0,y1:e.bbox.y1}:null}))}
export const parseOcr=text=>parseLines(text.split("\n").map(t=>({text:t}))).map(({bbox,...x})=>x);
