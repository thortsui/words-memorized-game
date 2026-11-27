// 對決素材：直接跳到指定 Boss，逐題紀錄題目／選項／對錯／命中／受擊
import { chromium } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/playwright-core/index.mjs';
import { readState, answersFor } from '../pt/lib4173.mjs';
import fs from 'node:fs';
const TARGET=+(process.argv[2]||4),LEN=+(process.argv[3]||80000),out=`raw_duel${TARGET}`;
fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const b=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=d3d11','--enable-gpu','--ignore-gpu-blocklist']});
const c=await b.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1});const p=await c.newPage();
const errs=[];p.on('pageerror',e=>errs.push(String(e)));
await p.addInitScript(()=>{localStorage.setItem('vc-story','1');localStorage.setItem('vc-story-soul','1');window.__soulTest={ambushRng:()=>1,expose:true};
  const fake={speaking:false,pending:false,paused:false,getVoices:()=>[],speak(u){setTimeout(()=>u.onend&&u.onend(),300)},cancel(){},resume(){},pause(){},addEventListener(){},removeEventListener(){}};
  try{Object.defineProperty(window,'speechSynthesis',{value:fake,configurable:true})}catch(e){}
  window.__ev=[];new MutationObserver(rs=>{for(const r of rs)for(const n of r.addedNodes)if(n.classList&&n.classList.contains('v3-banner'))window.__ev.push([performance.timeOrigin+performance.now(),'banner',n.textContent])}).observe(document,{subtree:true,childList:true})});
const ev=[];const E=(k,v)=>ev.push([Date.now(),k,v]);
const cdp=await c.newCDPSession(p);let n=0,recording=false;
cdp.on('Page.screencastFrame',async f=>{n++;fs.writeFileSync(`${out}/${String(n).padStart(6,'0')}_${Math.round(f.metadata.timestamp*1000)}.jpg`,Buffer.from(f.data,'base64'));cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{})});
await p.goto('http://127.0.0.1:4173/#practice');await p.waitForSelector('#start');
await p.locator('.chip',{hasText:'魂系模式'}).first().click();await p.click('#start');await p.waitForSelector('#covgo');await p.click('#covgo');
await p.waitForFunction(()=>window.__soulE,null,{timeout:60000});
await p.addStyleTag({content:`header,.btop,.hpbox,#msg{display:none!important}.arenawrap{position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;z-index:40;border:0!important;margin:0!important}#arena,.arena{width:100%!important;height:100%!important;border:0!important;border-radius:0!important}#bq{position:fixed!important;left:0;top:0;opacity:0!important;z-index:1}main#app{max-width:none!important;padding:0!important}body{overflow:hidden}`});
const click=s=>p.evaluate(s=>{const e=document.querySelector(s);e&&e.click()},s);
let t0=0,k=0,last=null;
while(true){
  const g=await p.evaluate(()=>{const B=window.__soulE.state;return{mi:B.mi,hp:B.hp,hpMax:B.hpMax,mhp:B.mhp}});
  if(!recording&&g.mi===TARGET){await sleep(300);await cdp.send('Page.startScreencast',{format:'jpeg',quality:88,maxWidth:1920,maxHeight:1080,everyNthFrame:1});recording=true;t0=Date.now();E('start',TARGET)}
  if(recording&&Date.now()-t0>LEN)break;
  // 受擊／命中紀錄，然後把主角補滿、Boss 血量限制
  if(last&&g.mi===last.mi){if(g.hp<last.hp)E('hurt',last.hp-g.hp);if(g.mhp<last.mhp)E('hit',last.mhp-g.mhp)}
  await p.evaluate(([tg])=>{const B=window.__soulE.state;B.hp=B.hpMax;if(B.mi<tg){if(B.mhp>1)B.mhp=1}else if(B.mhp>70)B.mhp=70},[TARGET]);
  last=await p.evaluate(()=>{const B=window.__soulE.state;return{mi:B.mi,hp:B.hp,mhp:B.mhp}});
  const st=await readState(p);if(st.end)break;
  if(await p.locator('#skov [data-p]').count()){await click('#skov [data-p]');await sleep(200);continue}
  if(await p.locator('#skov [data-s="0"]:not([disabled])').count()){await click('#skov [data-s="0"]');await sleep(200);continue}
  if(st.bnx&&!st.bnx.dis){await click('#bnx');await sleep(100);continue}
  if(st.opts&&st.opts.some(o=>!o.dis)){const A=answersFor(st);const ri=st.opts.findIndex(o=>A.right.includes(o.t));
    const prompt=st.pEn||st.pZh||st.cloze;
    if(recording){k++;const wrong=k%3===2;const ch=wrong?(ri+1)%st.opts.length:ri;await sleep(900);
      E('q',{prompt,mode:A.m,opts:st.opts.map(o=>o.t),right:ri,chose:ch,ok:!wrong});await click(`#bopts [data-o="${ch}"]`);E('ans',!wrong)}
    else{await click(`#bopts [data-o="${Math.max(0,ri)}"]`)}
    await sleep(120);continue}
  if(st.gonext&&!st.gonext.dis){await click('#gonext');await sleep(100);continue}
  await sleep(40)}
await cdp.send('Page.stopScreencast');
const pe=await p.evaluate(()=>window.__ev);
fs.writeFileSync(`${out}/events.json`,JSON.stringify({node:ev,page:pe,errs}));console.log('frames',n,'errs',errs.length,'q',ev.filter(e=>e[1]==='q').length);await b.close();
