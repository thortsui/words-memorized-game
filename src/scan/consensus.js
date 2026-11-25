// 雙引擎交叉比對（純函式，可在 Node 測試）。
// consensus(a,b)：把兩個引擎讀到的條目對齊、逐欄比對，回傳每筆的狀態：
//   agree  兩邊每一欄（正規化後）完全相同 → 雙重確認
//   diff   對得上是同一筆，但有欄位不同（附兩邊內容與字元級差異）
//   onlyA / onlyB  只有一邊讀到（漏條目或多條目）
export const FIELDS=["en","pos","zh","ex","blank"];
export const FIELD_NAME={en:"英文",pos:"詞性",zh:"中文",ex:"例句",blank:"克漏字答案"};

const base=s=>String(s??"").normalize("NFKC").replace(/[’‘`´]/g,"'").replace(/[“”„]/g,'"').replace(/[‐‑‒–—―]/g,"-").replace(/\s+/g," ").trim();
const fold=c=>{const t=base(c);return t===""?" ":t==="、"?",":t};
// 比對用的正規化：只抹平「寫法」差異（全形半形、引號樣式、空白），字母、標點有無、大小寫都照比
export const NORM={
  en:s=>base(s).replace(/\s*([\/()])\s*/g,"$1").replace(/ ?\.\.\. ?/g," ... ").trim(),
  pos:s=>{const t=base(s).toLowerCase().replace(/[.\s]/g,"").replace(/[;&]/g,",");return /^(phr|phrase|片語)$/.test(t)?"片語":t},
  zh:s=>base(s).replace(/\s+/g,"").replace(/、/g,","),
  ex:s=>base(s).replace(/ ([,.;:!?])/g,"$1"),
  blank:s=>base(s).toLowerCase()};
// 對齊用的鍵：只留小寫字母
export const enKey=s=>base(s).toLowerCase().replace(/[^a-z]+/g," ").trim();

export function editDistance(a,b){a=[...a];b=[...b];const n=a.length,m=b.length;if(!n)return m;if(!m)return n;let prev=Array.from({length:m+1},(_,j)=>j);
  for(let i=1;i<=n;i++){const cur=[i];for(let j=1;j<=m;j++)cur[j]=Math.min(prev[j]+1,cur[j-1]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));prev=cur}return prev[m]}

// 字元級差異（LCS）：回傳兩邊各自的片段 [[文字, 是否不同], …]
// key：比較前先把每個字元折成同一種寫法（全形／半形標點算同一個字），顯示仍用原本的字
export function charDiff(a,b,key=c=>c){const A=[...String(a??"")],B=[...String(b??"")],KA=A.map(key),KB=B.map(key),n=A.length,m=B.length,L=Array.from({length:n+1},()=>new Uint16Array(m+1));
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)L[i][j]=KA[i]===KB[j]?L[i+1][j+1]+1:Math.max(L[i+1][j],L[i][j+1]);
  const ra=[],rb=[],push=(r,c,d)=>{const l=r[r.length-1];if(l&&l[1]===d)l[0]+=c;else r.push([c,d])};let i=0,j=0;
  while(i<n&&j<m){if(KA[i]===KB[j]){push(ra,A[i],false);push(rb,B[j],false);i++;j++}else if(L[i+1][j]>=L[i][j+1]){push(ra,A[i++],true)}else push(rb,B[j++],true)}
  while(i<n)push(ra,A[i++],true);while(j<m)push(rb,B[j++],true);return{a:ra,b:rb}}

// 逐欄比對一對條目。fields：兩個引擎都有提供的欄位
export function compareEntries(a,b,fields=FIELDS){const out={},bad=[];
  for(const k of fields){const va=String(a[k]??"").trim(),vb=String(b[k]??"").trim(),same=NORM[k](va)===NORM[k](vb);out[k]={a:va,b:vb,same};
    if(!same){out[k].diff=charDiff(va.replace(/\s+/g," "),vb.replace(/\s+/g," "),fold);bad.push(k)}}
  return{fields:out,bad}}

// 對齊：先配英文完全相同的，再依編輯距離由小到大配（距離／長度 ≤ 0.4），最後用「中文完全相同」補配
export function alignEntries(a,b){const ka=a.map(x=>enKey(x.en)),kb=b.map(x=>enKey(x.en)),ma=new Array(a.length).fill(-1),mb=new Array(b.length).fill(-1),cand=[];
  for(let i=0;i<a.length;i++)for(let j=0;j<b.length;j++){if(!ka[i]||!kb[j])continue;const len=Math.max(ka[i].length,kb[j].length);
    // 一邊是另一邊再多出幾個字（OCR 把詞性或雜訊黏進英文）也算同一筆，排在距離小的後面
    const [sh,lo]=ka[i].length<=kb[j].length?[ka[i],kb[j]]:[kb[j],ka[i]];if(sh!==lo&&sh.length>=3&&lo.startsWith(sh+" ")&&lo.split(" ").length-sh.split(" ").length<=3){cand.push([.39,Math.abs(i/Math.max(1,a.length)-j/Math.max(1,b.length)),i,j]);continue}
    if(Math.abs(ka[i].length-kb[j].length)>len*.4)continue;
    const d=ka[i]===kb[j]?0:editDistance(ka[i],kb[j]);if(d/len<=.4)cand.push([d/len,Math.abs(i/Math.max(1,a.length)-j/Math.max(1,b.length)),i,j])}
  cand.sort((x,y)=>x[0]-y[0]||x[1]-y[1]);for(const [, ,i,j] of cand)if(ma[i]<0&&mb[j]<0){ma[i]=j;mb[j]=i}
  const zk=x=>NORM.zh(x.zh);
  for(let i=0;i<a.length;i++){if(ma[i]>=0||!zk(a[i]))continue;const j=b.findIndex((x,j)=>mb[j]<0&&zk(x)===zk(a[i]));if(j>=0){ma[i]=j;mb[j]=i}}
  return{ma,mb}}

// 回傳 [{status, a, b, fields, bad, entry}]，順序照 A，只有 B 有的插在它前一筆配對的後面。
// entry：建議存入的內容（agree／diff／onlyA 先放 A 的，onlyB 放 B 的），diff 一定要人工選邊或修改。
export function consensus(a,b,{fields=FIELDS}={}){const {ma,mb}=alignEntries(a,b),items=a.map((x,i)=>{
    if(ma[i]<0)return{status:"onlyA",a:x,b:null,fields:null,bad:[],entry:{...x}};
    const y=b[ma[i]],c=compareEntries(x,y,fields);
    return{status:c.bad.length?"diff":"agree",a:x,b:y,fields:c.fields,bad:c.bad,entry:{...x,unit:x.unit||y.unit||"",bbox:x.bbox||y.bbox||null}}});
  // 只有 B 有的：找它前面最近一筆有配對的 B，插在對應的 A 後面
  const after=new Map();let last=-1;
  for(let j=0;j<b.length;j++){if(mb[j]>=0){last=mb[j];continue}if(!after.has(last))after.set(last,[]);after.get(last).push({status:"onlyB",a:null,b:b[j],fields:null,bad:[],entry:{...b[j]}})}
  const out=[...(after.get(-1)||[])];items.forEach((it,i)=>{out.push(it);if(after.has(i))out.push(...after.get(i))});
  return out}

// 統計（給畫面摘要與測試用）
export const tally=items=>items.reduce((t,x)=>{t[x.status]=(t[x.status]||0)+1;return t},{agree:0,diff:0,onlyA:0,onlyB:0});
