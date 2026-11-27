// 手機直式實機遊玩錄影（真 UI）：攻擊、Boss 反擊閃避／彈反、答錯受擊、突襲
import { chromium } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/playwright-core/index.mjs';
import { readState, answersFor } from '../pt/lib4173.mjs';
import fs from 'node:fs';
const TARGET=+(process.argv[2]||4),LEN=+(process.argv[3]||100000),out=process.argv[4]||`raw_play${TARGET}`;
fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const b=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=d3d11','--enable-gpu','--ignore-gpu-blocklist']});
const c=await b.newContext({viewport:{width:430,height:932},deviceScaleFactor:2,hasTouch:true,isMobile:true,userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'});
const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(String(e)));
await p.addInitScript(()=>{localStorage.setItem('vc-story','1');localStorage.setItem('vc-story-soul','1');localStorage.setItem('wg-a2hs','1');window.__amb=1;window.__soulTest={ambushRng:()=>window.__amb,expose:true};
  const fake={speaking:false,pending:false,paused:false,getVoices:()=>[],speak(u){setTimeout(()=>u.onend&&u.onend(),300)},cancel(){},resume(){},pause(){},addEventListener(){},removeEventListener(){}};
  try{Object.defineProperty(window,'speechSynthesis',{value:fake,configurable:true})}catch(e){}
  window.__ev=[];const ev=(k,v)=>window.__ev.push([performance.timeOrigin+performance.now(),k,v]);
  new MutationObserver(rs=>{for(const r of rs){for(const n of r.addedNodes)if(n.classList&&n.classList.contains('v3-banner'))ev('banner',n.textContent);
    const m=document.getElementById('msg');if(m&&(r.target===m||m.contains(r.target))){const t=m.textContent;if(t!==window.__lm){window.__lm=t;ev('msg',m.className+'|'+t)}}}}).observe(document,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class']})});
const ev=[];const E=(k,v)=>ev.push([Date.now(),k,v]);
const cdp=await c.newCDPSession(p);let n=0,rec=false;
cdp.on('Page.screencastFrame',async f=>{n++;fs.writeFileSync(`${out}/${String(n).padStart(6,'0')}_${Math.round(f.metadata.timestamp*1000)}.jpg`,Buffer.from(f.data,'base64'));cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{})});
await p.goto('http://127.0.0.1:4173/#practice');await p.waitForSelector('#start');
await p.locator('.chip',{hasText:'魂系模式'}).first().click();await p.click('#start');await p.waitForSelector('#covgo');await p.click('#covgo');
await p.waitForFunction(()=>window.__soulE,null,{timeout:60000});
const click=s=>p.evaluate(s=>{const e=document.querySelector(s);e&&e.click()},s);
let t0=0,k=0,bk=0,pk=0,last=null,ambDone=false;
while(true){
  const g=await p.evaluate(()=>{const B=window.__soulE.state;return{mi:B.mi,hp:B.hp,mhp:B.mhp,msg:document.getElementById('msg')?.textContent||''}});
  if(!rec&&g.mi===TARGET){await sleep(200);await cdp.send('Page.startScreencast',{format:'jpeg',quality:90,maxWidth:860,maxHeight:1864,everyNthFrame:1});rec=true;t0=Date.now();E('start',TARGET)}
  if(rec&&Date.now()-t0>LEN)break;
  if(last&&g.mi===last.mi){if(g.hp<last.hp)E('hurt',last.hp-g.hp);if(g.mhp<last.mhp)E('hit',last.mhp-g.mhp)}
  await p.evaluate(([tg])=>{const B=window.__soulE.state;if(B.hp<B.hpMax*.45)B.hp=B.hpMax*.8;if(B.mi<tg){if(B.mhp>1)B.mhp=1}else if(B.mhp>300)B.mhp=300},[TARGET]);
  last=await p.evaluate(()=>{const B=window.__soulE.state;return{mi:B.mi,hp:B.hp,mhp:B.mhp}});
  const st=await readState(p);if(st.end)break;
  if(await p.locator('#skov [data-p]').count()){await sleep(rec?900:0);await click('#skov [data-p]');continue}
  if(await p.locator('#skov [data-s="0"]:not([disabled])').count()){await sleep(rec?700:0);await click('#skov [data-s="0"]');continue}
  if(st.bnx&&!st.bnx.dis){await sleep(rec?500:0);await click('#bnx');continue}
  if(st.opts&&st.opts.some(o=>!o.dis)){const A=answersFor(st);const ri=st.opts.findIndex(o=>A.right.includes(o.t));
    if(!rec){await click(`#bopts [data-o="${Math.max(0,ri)}"]`);await sleep(80);continue}
    const boss=/金色區|連擊|突進|必殺|突襲|閃避|段）|的回合，/.test(g.msg);const player=!boss&&/斬擊|你的回合/.test(g.msg);
    // 中段觸發一次突襲：玩家回合故意慢答
    let delay=boss?750:1100,wrong=false;k++;
    if(!ambDone&&player&&/你的回合/.test(g.msg)&&Date.now()-t0>3000){await p.evaluate(()=>window.__amb=0);delay=2600;ambDone=true;E('ambArm',1)}
    else{await p.evaluate(()=>window.__amb=1);wrong=boss?(++bk%3===2):(++pk%4===3)}
    await sleep(delay);const ch=wrong?(ri+1)%st.opts.length:ri;
    E('q',{boss,player,msg:g.msg.slice(0,30),prompt:st.pEn||st.pZh,ok:!wrong});await click(`#bopts [data-o="${ch}"]`);await sleep(120);continue}
  if(st.gonext&&!st.gonext.dis){await sleep(rec?400:0);await click('#gonext');continue}
  await sleep(40)}
await cdp.send('Page.stopScreencast');
fs.writeFileSync(`${out}/events.json`,JSON.stringify({node:ev,page:await p.evaluate(()=>window.__ev),errs}));
console.log('frames',n,'errs',errs.length,'q',ev.filter(e=>e[1]==='q').length);await b.close();
