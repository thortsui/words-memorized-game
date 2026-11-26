// 資料模型與儲存：全部放在 localStorage 的 vocab-cards-v1
import { BUILTIN } from '../data/no307.js';
import { isPhrase, clozeAns } from './grading.js';
import { toast, once, lsGet, lsSet } from './util.js';
import { normalizeState, normalizeSetup, blankState } from './normalize.js';

export const LS="vocab-cards-v1";
export const S=blankState();
// n 必須是 normalizeState 的結果（每本字典都有 words 陣列、每個條目欄位齊全）
function load(n){for(const k in S)delete S[k];Object.assign(S,n)}
// 啟動：讀到什麼都先正規化；整份讀不懂就留一份原始內容在 LS+"-bad"（方便救資料），用空白狀態開站
try{const j=localStorage.getItem(LS);if(j){let p=null,bad=false;try{p=JSON.parse(j)}catch(e){bad=true}
  if(bad||!p||typeof p!=="object"||Array.isArray(p)){try{localStorage.setItem(LS+"-bad",j)}catch(e){}}
  load(normalizeState(p))}}catch(e){}

const FULL="儲存失敗：瀏覽器的儲存空間不足，這次的變更沒有存下來（重新整理後會消失）。請刪掉不用的字典，或先匯出備份。";
// 回傳是否真的寫進 localStorage；失敗時會跳出提示，呼叫端不要再顯示成功訊息
export function save(){S.t=Date.now();try{localStorage.setItem(LS,JSON.stringify(S));return true}catch(e){toast(FULL,6000);return false}}
// 匯入備份：先完整驗證（格式不對會丟出 Error），再寫入 localStorage，寫入成功才換掉記憶體裡的資料。
// 回傳 false 表示空間不足寫不進去——這時 localStorage 與記憶體裡的原資料都沒有被動到。
export function replaceAll(j){const n=normalizeState(j,{strict:true});n.t=Date.now();
  try{localStorage.setItem(LS,JSON.stringify(n))}catch(e){return false}
  load(n);return true}
export const exportJson=()=>JSON.stringify(S);
export function allDicts(){const o={};if(!S.hidden.no307)o.no307=BUILTIN;for(const k in S.dicts)o[k]=S.dicts[k];return o}
// 第一次編輯內建字典時複製一份
export function ownDict(id){if(!S.dicts[id]&&id==="no307")S.dicts[id]=JSON.parse(JSON.stringify({...BUILTIN,builtin:false,name:BUILTIN.name}));return S.dicts[id]}
export function findW(d,id){const D=allDicts();return D[d]&&D[d].words.find(w=>w.id===id)}
export function allWords(){const b=[];Object.values(allDicts()).forEach(d=>d.words.forEach(w=>b.push(w)));return b}

// 練習設定
export const setup=normalizeSetup(null);
try{Object.assign(setup,normalizeSetup(JSON.parse(lsGet("vc-setup","{}"))))}catch(e){}
export const saveSetup=()=>{if(!lsSet("vc-setup",JSON.stringify(setup)))once("lsfull","練習設定存不進去：瀏覽器的儲存空間不足")};

// over：只套用這一次的設定（例如錯題頁的「練習待複習」），不會改到 setup
export function pool(over){const c=over?{...setup,...over}:setup,D=allDicts(),ids=c.dict==="__all"?Object.keys(D):[c.dict];let ws=[];ids.forEach(id=>D[id]&&D[id].words.forEach(w=>ws.push({...w,dict:id})));
  if(c.scope==="w")ws=ws.filter(w=>!isPhrase(w));if(c.scope==="p")ws=ws.filter(isPhrase);
  if(c.wrong)ws=ws.filter(w=>S.miss[w.dict]&&S.miss[w.dict][w.id]);if(c.mode==="cloze")ws=ws.filter(w=>w.ex&&clozeAns(w));if(c.mode==="mix"&&c.modes&&c.modes.every(m=>m==="cloze"))ws=ws.filter(w=>w.ex&&clozeAns(w));return ws}
// 刪除字典或條目時，一併清掉錯題紀錄與待複習計數（wid 不給＝整本字典）
export function forget(d,wid){if(wid===undefined){delete S.miss[d];delete S.wlog[d]}else{if(S.miss[d])delete S.miss[d][wid];if(S.wlog[d])delete S.wlog[d][wid]}}

// 答題紀錄：miss 待複習計數、wlog 永久錯題紀錄
export function mark(w,ok,given,mode){const d=w.dict||setup.dict;
  if(!ok){S.wlog[d]=S.wlog[d]||{};const L=S.wlog[d][w.id]=S.wlog[d][w.id]||{n:0,ans:[]};L.n++;L.last=Date.now();L.ans.unshift({a:String(given||"（不會）").slice(0,80),m:mode||"",t:L.last});L.ans=L.ans.slice(0,5)}
  S.miss[d]=S.miss[d]||{};if(ok){if(S.miss[d][w.id]){S.miss[d][w.id]--;if(S.miss[d][w.id]<=0)delete S.miss[d][w.id]}}else S.miss[d][w.id]=(S.miss[d][w.id]||0)+1;save()}
export function unlog(w){const d=w.dict||setup.dict,L=S.wlog[d]&&S.wlog[d][w.id];if(!L)return;L.n--;L.ans.shift();if(L.n<=0)delete S.wlog[d][w.id];save()}
export function pushHist(h){S.hist.unshift(h);S.hist=S.hist.slice(0,80);save()}

// 共用執行期狀態（路由、進行中的練習與戰鬥）
// autoStart：false，或一個只套用一次的設定物件（進練習頁時直接開始）
export const ctx={view:"",Q:null,B:null,autoStart:false};
