// 提取引擎：Claude（把掃描圖切成上下兩半送出，要求回傳每筆的大約位置）
import { lsGet } from '../../core/util.js';

export const MODEL="claude-opus-5-5";
const TOP=.56; // 上下兩半各佔 56% 高度，有重疊
const blobOf=(c,q=.86)=>new Promise(r=>c.toBlob(r,"image/jpeg",q));
function halves(c){const H=c.height,h=Math.round(H*TOP),mk=y=>{const x=document.createElement("canvas");x.width=c.width;x.height=h;x.getContext("2d").drawImage(c,0,y,c.width,h,0,0,c.width,h);return x};return[mk(0),mk(H-h)]}
const b64=b=>new Promise(r=>{const f=new FileReader();f.onload=()=>r(String(f.result).split(",")[1]);f.readAsDataURL(b)});
export const PROMPT=`你是英文單字書的 OCR 助手。附圖是同一頁單字書（台灣高中英文）的上半部（第 1 張）與下半部（第 2 張），兩張有重疊，重複的條目只列一次。
請提取頁面上所有印刷的單字與片語條目（忽略手寫筆跡、圈圈、音標、頁碼與頁首說明）。
每個字都必須照圖上印刷的原樣逐字抄寫，不可以憑印象補字、改寫或修正拼字；看不清楚的地方照看到的抄，並把該筆的 "unsure" 設為 true。
只回傳一個 JSON 陣列，不要任何其他文字。每筆格式：
{"en":"英文單字或片語，照書上原樣，如 talk sb out of N./V-ing","pos":"n. / v. / adj. / adv. / v., n. 等；片語寫 片語","zh":"中文解釋，照原文，可含括號補充","ex":"英文例句，照原文","blank":"例句中對應這個字或片語的實際出現字形（例如 dye 的例句裡是 dyed、give away 是 giving away）；片語被拆開或找不到就給空字串","unit":"側邊標籤，如 NO.307 Unit 5 或 Key Phrases；沒有就空字串","img":這筆出現在第幾張圖（1 或 2）,"y0":這筆（含例句）在該張圖裡的上緣位置（佔該張圖高度的百分比，0–100 的數字）,"y1":下緣位置（同樣是百分比）,"unsure":有任何看不清楚的字就是 true，否則 false}`;

// 把「第幾張圖裡的百分比」換算成整頁百分比
export function toPageBBox(x){const a=+x.y0,b=+x.y1;if(!isFinite(a)||!isFinite(b)||b<=a)return null;const off=+x.img===2?(1-TOP)*100:0;const c=v=>Math.max(0,Math.min(100,off+v*TOP));return{y0:c(a),y1:c(b)}}

export const claudeEngine={
  id:"claude",label:"Claude AI（最準，需 API 金鑰）",needsKey:true,
  note:"約 20–60 秒",
  ready:()=>!!lsGet("vc-key","").trim(),
  async extract(canvas,{onProgress}={}){const key=lsGet("vc-key","").trim();onProgress&&onProgress("Claude 正在讀取單字…（約 20–60 秒）");
    const content=[];for(const c of halves(canvas))content.push({type:"image",source:{type:"base64",media_type:"image/jpeg",data:await b64(await blobOf(c))}});content.push({type:"text",text:PROMPT});
    const r=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"content-type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"},body:JSON.stringify({model:MODEL,max_tokens:16000,messages:[{role:"user",content}]})});
    const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error((j.error&&j.error.message)||("HTTP "+r.status));
    const t=(j.content||[]).map(c=>c.text||"").join("");const arr=JSON.parse(t.slice(t.indexOf("["),t.lastIndexOf("]")+1));
    return arr.filter(x=>x&&x.en).map(x=>({en:x.en,pos:x.pos,zh:x.zh,ex:x.ex,blank:x.blank,unit:x.unit,bbox:toPageBBox(x),unsure:!!x.unsure}))}
};
