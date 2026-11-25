// 資料驗證與正規化（純函式，不碰 DOM、不碰 localStorage；可在 Node 直接測試）
// 用在兩個地方：
//   1. 匯入備份（strict）：格式不對就丟出 Error（message 是給使用者看的原因），呼叫端完全不寫入。
//   2. 啟動時讀 localStorage（寬鬆）：壞掉的字典／條目直接略過，其餘補預設值，保證網站開得起來。
const isObj=x=>!!x&&typeof x==="object"&&!Array.isArray(x);
const str=x=>typeof x==="string"?x:typeof x==="number"?String(x):"";
const mkId=()=>Math.random().toString(36).slice(2,10);
export const blankState=()=>({dicts:{},miss:{},hidden:{},wlog:{},hist:[],t:0});

// 一個條目：英文一定要有；其他欄位缺就補空字串；id 缺或重複就重新產生
function normWord(w,seen,strict,where){
  if(!isObj(w)){if(strict)throw new Error(where+"有不是條目的資料");return null}
  if(typeof w.en!=="string"||!w.en.trim()){if(strict)throw new Error(where+"有條目缺少英文（en）");return null}
  if(strict&&w.zh!=null&&typeof w.zh!=="string")throw new Error(where+"「"+w.en+"」的中文（zh）不是文字");
  let id=str(w.id);if(!id||seen.has(id))id=mkId();seen.add(id);
  return{id,en:w.en,pos:str(w.pos),zh:str(w.zh),ex:str(w.ex),blank:str(w.blank),unit:str(w.unit)}}

function normDict(key,d,strict){const where="字典「"+(isObj(d)&&typeof d.name==="string"&&d.name?d.name:key)+"」";
  if(!isObj(d)){if(strict)throw new Error("字典「"+key+"」不是物件");return null}
  if(typeof d.name!=="string"||!d.name.trim()){if(strict)throw new Error("字典「"+key+"」缺少名稱（name）");if(!Array.isArray(d.words))return null}
  if(!Array.isArray(d.words)){if(strict)throw new Error(where+"缺少條目清單（words）");return null}
  if(strict&&typeof d.id!=="string"&&typeof d.id!=="number")throw new Error(where+"缺少代號（id）");
  const seen=new Set(),words=[];for(const w of d.words){const n=normWord(w,seen,strict,where);if(n)words.push(n)}
  // id 一律以所在的鍵為準（選單、路由都用鍵）
  return{id:key,name:(typeof d.name==="string"&&d.name.trim())?d.name:"未命名字典",words}}

export function normalizeState(j,opt){const strict=!!(opt&&opt.strict),out=blankState();
  if(!isObj(j)){if(strict)throw new Error("內容不是備份資料");return out}
  if(!isObj(j.dicts)){if(strict)throw new Error("找不到字典資料（dicts）");}
  else for(const k of Object.keys(j.dicts)){const d=normDict(k,j.dicts[k],strict);if(d)out.dicts[k]=d}
  // 其他頂層欄位：缺就用預設，格式不對的項目略過
  if(isObj(j.hidden))for(const k in j.hidden)if(j.hidden[k])out.hidden[k]=true;
  if(isObj(j.miss))for(const d in j.miss){if(!isObj(j.miss[d]))continue;const o={};for(const id in j.miss[d]){const n=+j.miss[d][id];if(n>0)o[id]=Math.floor(n)}out.miss[d]=o}
  if(isObj(j.wlog))for(const d in j.wlog){if(!isObj(j.wlog[d]))continue;const o={};for(const id in j.wlog[d]){const L=j.wlog[d][id];if(!isObj(L))continue;const n=+L.n;if(!(n>0))continue;
    o[id]={n:Math.floor(n),last:+L.last||0,ans:(Array.isArray(L.ans)?L.ans:[]).filter(isObj).slice(0,5).map(a=>({a:str(a.a).slice(0,80),m:str(a.m),t:+a.t||0}))}}out.wlog[d]=o}
  if(Array.isArray(j.hist))out.hist=j.hist.filter(isObj).slice(0,80).map(h=>({t:+h.t||0,mode:str(h.mode),dict:str(h.dict),n:Math.max(0,+h.n||0),right:Math.max(0,+h.right||0),
    wrong:(Array.isArray(h.wrong)?h.wrong:[]).filter(x=>Array.isArray(x)&&x.length>=2).map(x=>[str(x[0]),str(x[1])]),game:h.game==="soul"?"soul":!!h.game}));
  out.t=+j.t||0;return out}

// 練習設定：值不在允許範圍就退回預設（壞掉的設定不能讓練習頁出錯）
export const SETUP_DEFAULT={dict:"no307",mode:"en2zh",scope:"all",n:10,wrong:false,auto:true,exmode:false,game:false};
export function normalizeSetup(j){const s={...SETUP_DEFAULT};if(!isObj(j))return s;
  if(typeof j.dict==="string"&&j.dict)s.dict=j.dict;
  if(["en2zh","zh2en","en2zhT","zh2enT","cloze"].includes(j.mode))s.mode=j.mode;
  if(["all","w","p"].includes(j.scope))s.scope=j.scope;
  if([0,10,20].includes(j.n))s.n=j.n;
  s.wrong=!!j.wrong;if(typeof j.auto==="boolean")s.auto=j.auto;s.exmode=!!j.exmode;s.game=j.game==="soul"?"soul":!!j.game;return s}
