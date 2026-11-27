// 階段轉換演出驗證：五隻 Boss（devourer 二、三階）各錄一段 CDP screencast。
// 用法：URL0=http://127.0.0.1:5185/ node phase.mjs [nodes|plain|rm]
//   nodes：攔截 GLB 換成加了 P2_/P3_ 測試節點的版本（scratchpad/ph/glb）；plain：原始 GLB；rm：nodes＋prefers-reduced-motion
import { open, readState, sleep, answersFor, URL0 } from './lib4173.mjs';
import fs from 'node:fs';
import path from 'node:path';
const mode=process.argv[2]||'nodes',port=process.argv[3]==='portrait';
const GLB='C:/Users/ethan/AppData/Local/Temp/claude/bf3cea3b8889bf19/2a62c364-c7b9-4d63-a6de-11eac9f5ae7e/scratchpad/ph/glb';
const S=await open({tag:'phase-'+mode+(port?'-p':''),width:port?430:1280,height:port?900:800,ttsMs:200,storage:{'vc-story':'1','vc-story-soul':'1'}});const {page,cdp,tap}=S;
if(mode!=='plain')await page.route(/\/models\/boss_[a-z]+\.glb/,route=>{const id=route.request().url().match(/boss_([a-z]+)\.glb/)[1];const f=path.join(GLB,`boss_${id}.glb`);if(fs.existsSync(f))route.fulfill({path:f,contentType:'model/gltf-binary'});else route.continue()});
// 其他人改檔會觸發 Vite HMR 整頁重載：把 /@vite/client 換成空殼
await page.route(/\/@vite\/client/,route=>route.fulfill({contentType:'application/javascript',body:`export function createHotContext(){return{accept(){},acceptExports(){},dispose(){},prune(){},invalidate(){},on(){},off(){},send(){},decline(){},data:{}}}
export function updateStyle(id,css){let s=document.querySelector('style[data-vite-dev-id="'+id+'"]');if(!s){s=document.createElement('style');s.setAttribute('data-vite-dev-id',id);document.head.appendChild(s)}s.textContent=css}
export function removeStyle(id){const s=document.querySelector('style[data-vite-dev-id="'+id+'"]');s&&s.remove()}
export function injectQuery(u){return u}
export class ErrorOverlay extends HTMLElement{}`}));
if(mode==='rm')await page.emulateMedia({reducedMotion:'reduce'});
await page.addInitScript(()=>{window.__soulTest={ambushRng:()=>1,expose:true}});
await page.goto(URL0+'#practice');await page.waitForSelector('#start');
await page.locator('.chip',{hasText:'魂系模式'}).first().click();await sleep(150);await page.click('#start');
await page.waitForSelector('#covgo',{timeout:15000});await sleep(1500);
await page.click('#covgo');await page.waitForFunction(()=>window.__soulE,null,{timeout:60000});
await page.waitForFunction(()=>!document.querySelector('.v3-loading'),null,{timeout:90000}).catch(()=>{});
// screencast ring buffer
const ring=[];let cast=true;
cdp.on('Page.screencastFrame',f=>{ring.push({t:Date.now(),data:f.data});while(ring.length&&ring[0].t<Date.now()-7000)ring.shift();cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{})});
await cdp.send('Page.startScreencast',{format:'jpeg',quality:72,maxWidth:port?860:1280,maxHeight:port?1800:800,everyNthFrame:1});
const ATS=[[.5],[.5],[.5],[.5],[.66,.33]],NAMES=['sentinel','gargoyle','priest','executioner','devourer'];
let seenN=0;const saves=[],after=[];
async function dump(i,det,info){await sleep(2600);const fr=ring.filter(x=>x.t>=det-2600&&x.t<=det+2600);const RAW='D:/Documents/ThorWorkSpace/Remamber word game/art/v2/shots/phase/_raw/'+S.tag;const dir=path.join(RAW,`${String(i).padStart(2,'0')}-${info.id}-p${info.form}`);fs.mkdirSync(dir,{recursive:true});
  const rect=await page.evaluate(()=>{const r=document.querySelector('#arena').getBoundingClientRect();return[r.left/innerWidth,r.top/innerHeight,r.right/innerWidth,r.bottom/innerHeight]});fs.writeFileSync(path.join(dir,'crop.txt'),rect.map(v=>v.toFixed(3)).join(','));
  fr.forEach((x,k)=>fs.writeFileSync(path.join(dir,`${String(k).padStart(3,'0')}_${x.t-det}.jpg`),Buffer.from(x.data,'base64')));saves.push({dir,n:fr.length});
  await sleep(1200);const f=path.join(RAW,`${String(i).padStart(2,'0')}-${info.id}-p${info.form}-after.png`);await page.screenshot({path:f});after.push(f)}
const t0=Date.now();let n=0,lastProg=Date.now(),lastKey='';const pend=[];
while(Date.now()-t0<12*60000){const st=await readState(page);if(st.end||!st.inbattle&&!st.opts&&!st.input)break;
  const info=await page.evaluate(([ATS])=>{const E=window.__soulE;if(!E)return null;const B=E.state;B.hp=B.hpMax;const mx=window.__mx=window.__mx||{};if(B.mhp>0)mx[B.mi]=Math.max(mx[B.mi]||0,B.mhp);const max=mx[B.mi],ats=ATS[B.mi]||[.5];
    if(B.bphase<ats.length){const tg=Math.ceil(ats[B.bphase]*max)+2;if(B.mhp>tg)B.mhp=tg}else if(B.mhp>8&&!window.__holdKill)B.mhp=8;
    return{mi:B.mi,bphase:B.bphase,log:(window.__phaseLog||[]).slice()}},[ATS]);
  if(info&&info.log.length>seenN){for(let k=seenN;k<info.log.length;k++){const e=info.log[k];console.log('phase',JSON.stringify(e));pend.push(dump(k+1,Date.now(),e))}seenN=info.log.length;
    await page.evaluate(()=>{window.__holdKill=true;setTimeout(()=>{window.__holdKill=false},6000)})} // 轉換後先多打一兩回合（看回到戰鬥）
  if(await page.locator('#skov [data-p]').count()){await tap('#skov [data-p]');await sleep(300);lastProg=Date.now();continue}
  if(await page.locator('#skov [data-s="0"]:not([disabled])').count()){await page.click('#skov [data-s="0"]').catch(()=>{});await sleep(300);lastProg=Date.now();continue}
  if(st.story){await page.click('#app',{position:{x:10,y:10}}).catch(()=>{});await sleep(200)}
  if(st.bnx&&!st.bnx.dis){await tap('#bnx');await sleep(150);lastProg=Date.now();continue}
  if(st.opts&&st.opts.some(o=>!o.dis)){const A=answersFor(st);const i=st.opts.findIndex(o=>A.right.includes(o.t));await sleep(300);await tap(`#bopts [data-o="${Math.max(0,i)}"]`);n++;lastProg=Date.now();continue}
  if(st.gonext&&!st.gonext.dis){await tap('#gonext');await sleep(200);lastProg=Date.now();continue}
  const key=JSON.stringify([st.msg,st.end]);if(key!==lastKey){lastKey=key;lastProg=Date.now()}
  if(Date.now()-lastProg>40000){console.log('STUCK',st.msg);await page.screenshot({path:S.dir+'/STUCK.png'});break}
  await sleep(80)}
await Promise.all(pend);
const log=await page.evaluate(()=>window.__phaseLog||[]);
console.log(JSON.stringify({mode,log,saves,after,errors:S.logs.pageerror,console:S.logs.console.filter(x=>/error|phaseShow/i.test(x.text)).slice(0,8)},null,1));
await cdp.send('Page.stopScreencast').catch(()=>{});await S.browser.close();
