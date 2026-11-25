// 模型檔與辨識程式的下載快取：存進 Cache Storage，下載過一次之後離線也能用。
// （Cache Storage 只在 https 或 localhost 可用；不可用時退回一般下載，功能照常。）
const NAME="vc-scan-models-v1";
const open=async()=>{try{return typeof caches!=="undefined"?await caches.open(NAME):null}catch(e){return null}};

// 回傳 Uint8Array。onProgress(已下載位元組, 總位元組或 0)
export async function cachedBytes(url,onProgress){const c=await open();
  if(c){const hit=await c.match(url).catch(()=>null);if(hit)return new Uint8Array(await hit.arrayBuffer())}
  const r=await fetch(url);if(!r.ok)throw new Error("下載失敗（HTTP "+r.status+"）："+url.split("/").pop());
  const total=+r.headers.get("content-length")||0;let buf;
  if(r.body&&onProgress){const rd=r.body.getReader(),parts=[];let n=0;for(;;){const {done,value}=await rd.read();if(done)break;parts.push(value);n+=value.length;onProgress(n,total)}
    buf=new Uint8Array(n);let o=0;for(const p of parts){buf.set(p,o);o+=p.length}}
  else buf=new Uint8Array(await r.arrayBuffer());
  if(c)await c.put(url,new Response(buf,{headers:{"content-type":r.headers.get("content-type")||"application/octet-stream"}})).catch(()=>{});
  return buf}
export const cachedText=async(url,onProgress)=>new TextDecoder().decode(await cachedBytes(url,onProgress));
// 把快取的程式檔變成 blob: 網址（給 import()、Worker、importScripts 用，離線也能載入）
export const cachedBlobUrl=async(url,type="text/javascript",onProgress)=>URL.createObjectURL(new Blob([await cachedBytes(url,onProgress)],{type}));
// 這些網址是不是都已經在快取裡（畫面上用來顯示「已下載」）
export async function allCached(urls){const c=await open();if(!c)return false;for(const u of urls)if(!await c.match(u).catch(()=>null))return false;return true}
export const mb=n=>(n/1048576).toFixed(n<10485760?1:0)+" MB";
