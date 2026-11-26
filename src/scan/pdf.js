// PDF 上傳：用 pdf.js（cdnjs，用到才下載，存進 Cache Storage）把每一頁畫成圖，同時取出 PDF 內嵌的文字層。
//   文字層是 PDF 本身帶的字（電子檔、不是掃描），一字不差，當成「第一個引擎」；畫出來的圖再交給 PP-OCR 讀一次互相核對。
//   掃描成的 PDF（沒有文字層）就只當圖片，走一般的兩個 OCR 引擎。
import { cachedBlobUrl } from './cache.js';

const V="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/";
export const PDF_FILES={main:V+"pdf.min.js",worker:V+"pdf.worker.min.js"};   // 約 0.3 MB＋1 MB
let lib=null;
async function load(){if(lib)return lib;
  if(!window.pdfjsLib){const s=document.createElement("script");s.src=await cachedBlobUrl(PDF_FILES.main);await new Promise((ok,no)=>{s.onload=ok;s.onerror=()=>no(new Error("pdf.js 載入失敗"));document.head.appendChild(s)})}
  lib=window.pdfjsLib;lib.GlobalWorkerOptions.workerSrc=await cachedBlobUrl(PDF_FILES.worker);return lib}

// 同一行、相鄰的文字片段併起來（pdf.js 常把一個儲存格拆成好幾段，甚至一個字一段）
export function mergeItems(items){const out=[];const bs=items.slice().sort((a,b)=>(a.y1-b.y1)||(a.x0-b.x0));
  for(const b of bs){const h=b.y1-b.y0,last=out.find(o=>Math.abs(o.y1-b.y1)<.3*h&&b.x0-o.x1<.35*h&&b.x0-o.x1>-.3*h);
    if(last){const gap=b.x0-last.x1;last.text+=(gap>.15*h&&!/\s$/.test(last.text)?" ":"")+b.text;last.x1=Math.max(last.x1,b.x1);last.y0=Math.min(last.y0,b.y0);last.y1=Math.max(last.y1,b.y1)}
    else out.push({...b})}
  return out.map(b=>({...b,text:b.text.replace(/\s+/g," ").trim()})).filter(b=>b.text)}

// file → [{canvas, text:[{text,x0,y0,x1,y1,conf:1}]|null, n, total}]；長邊畫成約 2000 px
export async function pdfPages(file,say){const L=await load(),doc=await L.getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise,out=[];
  for(let i=1;i<=doc.numPages;i++){say&&say(`PDF 第 ${i}/${doc.numPages} 頁`);const pg=await doc.getPage(i),v0=pg.getViewport({scale:1}),vp=pg.getViewport({scale:2000/Math.max(v0.width,v0.height)});
    const c=document.createElement("canvas");c.width=Math.round(vp.width);c.height=Math.round(vp.height);const g=c.getContext("2d");g.fillStyle="#fff";g.fillRect(0,0,c.width,c.height);
    await pg.render({canvasContext:g,viewport:vp}).promise;
    const tc=await pg.getTextContent(),items=[];
    for(const it of tc.items){if(!it.str||!it.str.trim())continue;const m=L.Util.transform(vp.transform,it.transform),h=Math.hypot(m[2],m[3]),x=m[4],y=m[5],w=it.width*vp.scale;
      items.push({text:it.str,x0:x,x1:x+w,y0:y-h*.9,y1:y+h*.2,conf:1})}
    const text=mergeItems(items);out.push({canvas:c,text:text.length>=5?text:null,n:i,total:doc.numPages})}
  return out}
