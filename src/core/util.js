// DOM 小工具
export { shuffle } from './grading.js';
export const $=s=>document.querySelector(s);
export const app=document.querySelector("#app");
export const $$=s=>[...app.querySelectorAll(s)];
export const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
export const rid=()=>Math.random().toString(36).slice(2,10);
export const wait=ms=>new Promise(r=>setTimeout(r,ms));
// ms：顯示多久。較長的重要訊息（例如儲存失敗）顯示期間，不會被之後的一般訊息蓋掉
export function toast(m,ms){const t=$("#toast");if(!t)return;const now=Date.now();if(!ms&&t._hold>now)return;t._hold=ms?now+ms:0;t.textContent=m;t.classList.remove("hide");clearTimeout(t._t);t._t=setTimeout(()=>t.classList.add("hide"),ms||2600)}
export function ask(msg){return new Promise(r=>{const m=$("#modal");$("#m-msg").textContent=msg;m.classList.remove("hide");const done=v=>{m.classList.add("hide");$("#m-yes").onclick=$("#m-no").onclick=null;r(v)};$("#m-yes").onclick=()=>done(true);$("#m-no").onclick=()=>done(false)})}
export function loadScript(src){return new Promise((ok,no)=>{const s=document.createElement("script");s.src=src;s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
export const SC='<span class="scis"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/></svg></span>';
export const fmt=t=>{const d=new Date(t);return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`};
const told={};
export function once(k,m){if(told[k])return;told[k]=1;toast(m)}
// 讀寫 localStorage 的小包裝
export const lsGet=(k,d)=>{try{const v=localStorage.getItem(k);return v===null?d:v}catch(e){return d}};
export const lsSet=(k,v)=>{try{localStorage.setItem(k,v);return true}catch(e){return false}};
