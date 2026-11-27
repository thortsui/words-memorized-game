// 宣傳片素材錄製：node cap.mjs cover|title|soul|ui
import { chromium } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/playwright-core/index.mjs';
import { BUILTIN } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/src/data/no307.js';
import fs from 'node:fs';
const mode=process.argv[2];const W=+(process.argv[3]||1920),H=+(process.argv[4]||1080);
const out=`raw_${mode}`;fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const b=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=d3d11','--enable-gpu','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required']});
const c=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:1});const p=await c.newPage();
const errs=[];p.on('pageerror',e=>errs.push(String(e)));
await p.addInitScript(()=>{localStorage.setItem('vc-story','1');localStorage.setItem('vc-story-soul','1');window.__soulTest={ambushRng:()=>Math.random()<.5?0:1,expose:true};
  const fake={speaking:false,pending:false,paused:false,getVoices:()=>[],speak(u){setTimeout(()=>u.onend&&u.onend(),300)},cancel(){},resume(){},pause(){},addEventListener(){},removeEventListener(){}};
  try{Object.defineProperty(window,'speechSynthesis',{value:fake,configurable:true})}catch(e){}
  window.__ev=[];const ev=(k,v)=>window.__ev.push([performance.timeOrigin+performance.now(),k,v]);window.__evf=ev;
  new MutationObserver(rs=>{for(const r of rs)for(const n of r.addedNodes)if(n.classList&&n.classList.contains('v3-banner'))ev('banner',n.textContent)}).observe(document,{subtree:true,childList:true})});
const events=[];const ev=(k,v)=>events.push([Date.now(),k,v]);
const cdp=await c.newCDPSession(p);let n=0;
cdp.on('Page.screencastFrame',async f=>{n++;fs.writeFileSync(`${out}/${String(n).padStart(6,'0')}_${Math.round(f.metadata.timestamp*1000)}.jpg`,Buffer.from(f.data,'base64'));cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{})});
const rec=()=>cdp.send('Page.startScreencast',{format:'jpeg',quality:88,maxWidth:W,maxHeight:H,everyNthFrame:1});
const stop=()=>cdp.send('Page.stopScreencast');
const FULL=`header,.btop,.hpbox,#msg,.cov::after{display:none!important}
 .arenawrap{position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;z-index:40;border:0!important;margin:0!important}
 #arena,.arena{width:100%!important;height:100%!important;border:0!important;border-radius:0!important}
 #bq{position:fixed!important;left:0;top:0;opacity:0!important;z-index:1}
 main#app{max-width:none!important;padding:0!important}body{overflow:hidden}`;
await p.goto('http://127.0.0.1:4173/#practice');await p.waitForSelector('#start');
await p.locator('.chip',{hasText:'魂系模式'}).first().click();await p.click('#start');await p.waitForSelector('#covgo');
if(mode==='cover'||mode==='title'){
  await p.addStyleTag({content:'header{display:none!important}main#app{max-width:none!important;padding:0!important}'+(mode==='cover'?'.cov-ui{display:none!important}':'.cov-btns,.cov-foot{display:none!important}.cov-ui{opacity:0}.cov-ui.go{opacity:1}')});
  await sleep(mode==='cover'?3500:6000);
  if(mode==='title'){await p.evaluate(()=>{const u=document.querySelector('.cov-ui');u.querySelectorAll('*').forEach(e=>{e.style.animation='none';e.offsetWidth;e.style.animation=''});u.classList.add('go')})}
  ev('start');await rec();await sleep(mode==='cover'?24000:9000);await stop();
}else{
  await p.click('#covgo');await p.waitForFunction(()=>window.__soulE,null,{timeout:60000});
  if(mode==='soul')await p.addStyleTag({content:FULL});
  await p.waitForFunction(()=>!document.querySelector('.v3-loading'),null,{timeout:90000}).catch(()=>{});
  const WR=BUILTIN.words;
  ev('start');await rec();
  const t0=Date.now();let lastMi=-1,k=0;const LIM=mode==='ui'?45000:16*60000;
  while(Date.now()-t0<LIM){
    const st=await p.evaluate(()=>{const E=window.__soulE,B=E&&E.state;if(B){B.hp=B.hpMax;if(B.mhp>(window.__cap||26))B.mhp=window.__cap||26}
      const q=s=>document.querySelector(s);const o=[...document.querySelectorAll('#bopts button')].map((x,i)=>({i,t:x.textContent,d:x.disabled}));
      return{mi:B&&B.mi,end:!!q('#again'),o,pEn:q('.bprompt.en')?.textContent,pZh:q('.bprompt.zh')?.textContent,skp:!!q('#skov [data-p]'),sk0:!!q('#skov [data-s="0"]:not([disabled])'),bnx:q('#bnx')&&!q('#bnx').disabled,gon:q('#gonext')&&!q('#gonext').disabled}});
    if(st.mi!=null&&st.mi!==lastMi){lastMi=st.mi;ev('boss',st.mi)}
    if(st.end){ev('end');await sleep(4000);break}
    const click=s=>p.evaluate(s=>{const e=document.querySelector(s);e&&e.click()},s);
    if(st.skp){await sleep(800);await click('#skov [data-p]');continue}
    if(st.sk0){await sleep(500);await click('#skov [data-s="0"]');continue}
    if(st.bnx){await click('#bnx');await sleep(150);continue}
    if(st.o.some(x=>!x.d)){
      // 找正確答案：題目是英文就找中文、反之亦然
      let i=-1;const pe=(st.pEn||'').trim(),pz=(st.pZh||'').trim();
      for(const w of WR){if(pe&&(w.en===pe||pe.includes(w.en))){i=st.o.findIndex(x=>x.t.includes((w.zh||'').split(/[；;、，,]/)[0]));if(i>=0)break}
        if(pz&&w.zh&&(pz.includes(w.zh)||w.zh.includes(pz))){i=st.o.findIndex(x=>x.t.trim().endsWith(w.en)||x.t.includes(w.en));if(i>=0)break}}
      k++;const wrong=k%4===0;if(wrong||i<0)i=(Math.max(0,i)+1)%st.o.length;
      await sleep(mode==='ui'?1400:500);await click(`#bopts [data-o="${i}"]`);ev('ans',wrong?'wrong':'ok');await sleep(200);continue}
    if(st.gon){await click('#gonext');await sleep(200);continue}
    await sleep(60)}
  await stop();
}
const evs=await p.evaluate(()=>window.__ev).catch(()=>[]);
fs.writeFileSync(`${out}/events.json`,JSON.stringify({node:events,page:evs,errs}));
console.log(mode,'frames',n,'errs',errs.length,'events',events.length+evs.length);await b.close();
