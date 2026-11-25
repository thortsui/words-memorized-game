// 掃描引擎實測（在瀏覽器裡跑）：開著 npm run dev，在主控台執行
//   (await import('/tests/scan-bench.js')).run().then(r=>console.log(JSON.stringify(r,null,1)))
// 對 tests/fixtures/ 的合成書頁跑兩個本機引擎，和 truth.json 比，回報：
//   每個引擎的字元正確率、兩引擎比對後各狀態的筆數、主引擎讀錯的筆數與其中被攔下的筆數。
import { ppocrEngine } from '/src/scan/engines/ppocr.js';
import { ocrEngine } from '/src/scan/engines/tesseract.js';
import { consensus, alignEntries, editDistance, NORM } from '/src/scan/consensus.js';
import { loadLexicon } from '/src/scan/wordlist.js';
import { ruleWarnings } from '/src/scan/rules.js';

const KEYS=["en","pos","zh","ex"];
async function load(name){const img=new Image();img.src="/tests/fixtures/"+name;await img.decode();const c=document.createElement("canvas");c.width=img.naturalWidth;c.height=img.naturalHeight;c.getContext("2d").drawImage(img,0,0);return c}
const same=(a,b)=>KEYS.every(k=>NORM[k](a[k]||"")===NORM[k](b[k]||""));

// 字元正確率：每筆正確答案對到引擎讀到的條目，逐欄算編輯距離；漏掉的條目整筆算錯
function score(truth,got){const {ma}=alignEntries(truth,got);let total=0,err=0,exact=0,missing=0;
  truth.forEach((t,i)=>{const g=ma[i]>=0?got[ma[i]]:null;if(!g)missing++;
    for(const k of KEYS){const a=NORM[k](t[k]||""),b=g?NORM[k](g[k]||""):"";total+=[...a].length;err+=Math.min([...a].length,editDistance(a,b))}
    if(g&&same(t,g))exact++});
  return{chars:total,charErrors:err,accuracy:+(100*(1-err/total)).toFixed(2),entries:truth.length,exact,missing,extra:got.length-ma.filter(x=>x>=0).length}}

export async function run(pages=["page1.png","page2.png","page3.jpg"]){const truth=await (await fetch("/tests/fixtures/truth.json")).json(),lex=await loadLexicon(),out={pages:{},total:{}};
  const sum={A:{chars:0,charErrors:0},B:{chars:0,charErrors:0},wrong:0,caught:0,escaped:0,agree:0,diff:0,onlyA:0,onlyB:0,ruleFlags:0};
  for(const name of pages){const c=await load(name),T=truth[name];let t=performance.now();
    const a=await ppocrEngine.extract(c,{}),ta=Math.round(performance.now()-t);t=performance.now();
    const b=await ocrEngine.extract(c,{}),tb=Math.round(performance.now()-t);
    const sa=score(T,a),sb=score(T,b),items=consensus(a,b),detail=[];
    for(const it of items){const e=it.entry,tr=T.find(x=>NORM.en(x.en)===NORM.en(e.en))||T[alignEntries([e],T).ma[0]]||null;
      const wrong=!tr||!same(tr,e),rules=ruleWarnings(e,lex),flagged=it.status!=="agree"||rules.length>0;
      sum[it.status]++;if(rules.length)sum.ruleFlags++;if(wrong){sum.wrong++;flagged?sum.caught++:sum.escaped++}
      if(flagged||wrong)detail.push({en:e.en,status:it.status,diffFields:it.bad,rules,wrongVsTruth:wrong,A:it.a&&KEYS.map(k=>it.a[k]).join(" | "),B:it.b&&KEYS.map(k=>it.b[k]).join(" | ")})}
    for(const k of ["chars","charErrors"]){sum.A[k]+=sa[k];sum.B[k]+=sb[k]}
    out.pages[name]={ppocr:{ms:ta,...sa},tesseract:{ms:tb,...sb},flagged:detail}}
  out.total={ppocrAccuracy:+(100*(1-sum.A.charErrors/sum.A.chars)).toFixed(2),tesseractAccuracy:+(100*(1-sum.B.charErrors/sum.B.chars)).toFixed(2),
    status:{agree:sum.agree,diff:sum.diff,onlyA:sum.onlyA,onlyB:sum.onlyB},ruleFlags:sum.ruleFlags,
    mainEngineWrongEntries:sum.wrong,caught:sum.caught,escaped:sum.escaped};
  return out}
