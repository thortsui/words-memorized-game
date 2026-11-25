// 資料模型與儲存：全部放在 localStorage 的 vocab-cards-v1
import { BUILTIN } from '../data/no307.js';
import { isPhrase, clozeAns } from './grading.js';
import { toast, lsGet, lsSet } from './util.js';

export const LS="vocab-cards-v1";
const blank=()=>({dicts:{},miss:{},hidden:{},wlog:{},hist:[],t:0});
export const S=blank();
function load(j){for(const k in S)delete S[k];Object.assign(S,blank(),j);S.wlog=S.wlog||{};S.hist=S.hist||[];S.miss=S.miss||{};S.hidden=S.hidden||{};S.dicts=S.dicts||{}}
try{const j=localStorage.getItem(LS);if(j)load(JSON.parse(j))}catch(e){}

export function save(){S.t=Date.now();try{localStorage.setItem(LS,JSON.stringify(S))}catch(e){toast("儲存失敗：瀏覽器空間不足")}}
export function replaceAll(j){load(j);save()}
export const exportJson=()=>JSON.stringify(S);
export function allDicts(){const o={};if(!S.hidden.no307)o.no307=BUILTIN;for(const k in S.dicts)o[k]=S.dicts[k];return o}
// 第一次編輯內建字典時複製一份
export function ownDict(id){if(!S.dicts[id]&&id==="no307")S.dicts[id]=JSON.parse(JSON.stringify({...BUILTIN,builtin:false,name:BUILTIN.name}));return S.dicts[id]}
export function findW(d,id){const D=allDicts();return D[d]&&D[d].words.find(w=>w.id===id)}
export function allWords(){const b=[];Object.values(allDicts()).forEach(d=>d.words.forEach(w=>b.push(w)));return b}

// 練習設定
export const setup={dict:"no307",mode:"en2zh",scope:"all",n:10,wrong:false,auto:true,exmode:false,game:false};
try{Object.assign(setup,JSON.parse(lsGet("vc-setup","{}")))}catch(e){}
export const saveSetup=()=>lsSet("vc-setup",JSON.stringify(setup));

export function pool(){const D=allDicts(),ids=setup.dict==="__all"?Object.keys(D):[setup.dict];let ws=[];ids.forEach(id=>D[id]&&D[id].words.forEach(w=>ws.push({...w,dict:id})));
  if(setup.scope==="w")ws=ws.filter(w=>!isPhrase(w));if(setup.scope==="p")ws=ws.filter(isPhrase);
  if(setup.wrong)ws=ws.filter(w=>S.miss[w.dict]&&S.miss[w.dict][w.id]);if(setup.mode==="cloze")ws=ws.filter(w=>w.ex&&clozeAns(w));return ws}

// 答題紀錄：miss 待複習計數、wlog 永久錯題紀錄
export function mark(w,ok,given,mode){const d=w.dict||setup.dict;
  if(!ok){S.wlog[d]=S.wlog[d]||{};const L=S.wlog[d][w.id]=S.wlog[d][w.id]||{n:0,ans:[]};L.n++;L.last=Date.now();L.ans.unshift({a:String(given||"（不會）").slice(0,80),m:mode||"",t:L.last});L.ans=L.ans.slice(0,5)}
  S.miss[d]=S.miss[d]||{};if(ok){if(S.miss[d][w.id]){S.miss[d][w.id]--;if(S.miss[d][w.id]<=0)delete S.miss[d][w.id]}}else S.miss[d][w.id]=(S.miss[d][w.id]||0)+1;save()}
export function unlog(w){const d=w.dict||setup.dict,L=S.wlog[d]&&S.wlog[d][w.id];if(!L)return;L.n--;L.ans.shift();if(L.n<=0)delete S.wlog[d][w.id];save()}
export function pushHist(h){S.hist.unshift(h);S.hist=S.hist.slice(0,80);save()}

// 共用執行期狀態（路由、進行中的練習與戰鬥）
export const ctx={view:"",Q:null,B:null,autoStart:false};
