// 掃描上傳頁的操作測試（真的開瀏覽器，手機大小 390×700）：
//   node tests/scan-ui.mjs [網址]        （預設 http://127.0.0.1:4181/；先 build 到 dist-scan 並 preview）
// 檢查：沒被收進條目的文字要處理完才能存、筆數不符會擋、手動貼上的不算雙重確認、重新整理後可以還原清單、
//       localStorage 滿了存入會明講失敗而且清單還在、手機版面（例句可換行、觸控目標 ≥44px、跳到下一個時原圖還在畫面內）。
import { chromium } from 'playwright-core';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE=path.dirname(fileURLToPath(import.meta.url)),BASE=process.argv[2]||"http://127.0.0.1:4181/",sleep=ms=>new Promise(r=>setTimeout(r,ms));
const browser=await chromium.launch({channel:"chrome",headless:true});
const context=await browser.newContext({viewport:{width:390,height:700},hasTouch:true,isMobile:true,deviceScaleFactor:2,locale:"zh-TW"});
const page=await context.newPage(),errors=[],R={},fails=[];
const ok=(name,cond,info)=>{R[name]=cond?"OK":"FAIL"+(info!==undefined?" "+JSON.stringify(info):"");if(!cond)fails.push(name)};
page.on("console",m=>{if(m.type()==="error")errors.push(m.text().slice(0,200))});page.on("pageerror",e=>errors.push("pageerror: "+e.message));page.on("dialog",d=>d.accept().catch(()=>{}));
const dicts=()=>page.evaluate(()=>Object.keys((JSON.parse(localStorage.getItem("vocab-cards-v1")||"{}").dicts)||{}).length);
const settle=()=>page.waitForFunction(()=>!/核對中|檢查中/.test(document.querySelector("#revbox").innerText),null,{timeout:180000});
try{
  await page.goto(BASE+"#upload");await page.evaluate(()=>{sessionStorage.clear();localStorage.clear()});await page.reload();await page.waitForSelector("#file",{state:"attached"});
  // 手動貼上一筆
  await page.fill("#paste","borrow | v. | 借入 | May I borrow your umbrella for a while?");await page.click("#parse");await page.waitForSelector("#rev .rc");await settle();
  const man=await page.evaluate(()=>({badge:document.querySelector("#rev .badge").textContent,tally:document.querySelector("#vsum").textContent}));
  ok("手動貼上的條目不算進雙重確認",/手動輸入/.test(man.badge)&&/雙重確認 0/.test(man.tally)&&/手動輸入 1/.test(man.tally),man);
  // 斜拍、有漏條目的那張圖（不調四角，讓它讀得更差）
  await page.setInputFiles("#file",path.join(HERE,"playtest","site","img","hard5.png"));await page.waitForSelector("#extract");
  await page.evaluate(()=>{window.__gaps=[];let last=performance.now();window.__hb=setInterval(()=>{const n=performance.now();if(n-last>150)window.__gaps.push(Math.round(n-last));last=n},25)});
  await page.locator("#extract").scrollIntoViewIfNeeded();await page.click("#extract");await page.waitForSelector("#rev .pp",{timeout:600000});await settle();
  const fz=await page.evaluate(()=>{clearInterval(window.__hb);return Math.max(0,...window.__gaps)});ok("提取（含掃描）時畫面沒有卡超過 0.3 秒",fz<=300,fz);
  // 版面
  const lay=await page.evaluate(()=>{const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
    const small=[...document.querySelectorAll("#rev .rc input,#rev .rc textarea,#rev .pp input,#rev .rc button,#rev .pp button")].filter(vis).map(e=>{const r=e.getBoundingClientRect();return{t:e.tagName+"."+(e.className||e.dataset.k||"")+" "+(e.textContent||"").slice(0,8),w:Math.round(r.width),h:Math.round(r.height)}}).filter(x=>x.h<44||x.w<44);
    return{overflowX:document.documentElement.scrollWidth-innerWidth,exIsTextarea:!!document.querySelector("#rev .rc textarea[data-k=ex]"),small:[...new Map(small.map(x=>[x.t+x.w+x.h,x])).values()].slice(0,8)}});
  ok("手機沒有水平捲動",lay.overflowX<=0,lay.overflowX);ok("例句是可換行的多行欄位",lay.exIsTextarea);
  ok("核對卡片的輸入框與勾選框觸控目標 ≥44px",!lay.small.some(x=>/INPUT|TEXTAREA/.test(x.t)),lay.small.filter(x=>/INPUT|TEXTAREA/.test(x.t)));R.小於44px的按鈕=lay.small.filter(x=>/BUTTON/.test(x.t));
  // 跳到下一個：卡片上方的原圖裁切要留在置頂摘要下面、畫面之內
  await page.click("#nexttodo");await sleep(900);await page.click("#nexttodo");await sleep(900);
  const jump=await page.evaluate(()=>{const el=document.querySelector("#rev .flash")||[...document.querySelectorAll("#rev .rc")].find(c=>c.getBoundingClientRect().top>0),cv=el&&el.querySelector("canvas"),vs=document.querySelector("#vsum").getBoundingClientRect(),t=document.querySelector("#toast");if(!cv)return{none:true,cls:el&&el.className};const r=cv.getBoundingClientRect();return{cropTop:Math.round(r.top),cropBottom:Math.round(r.bottom),vsumBottom:Math.round(vs.bottom),vh:innerHeight,toast:t&&!t.classList.contains("hide")}});
  ok("跳到下一個之後原圖裁切在畫面內、沒被置頂摘要蓋住",jump.none||(jump.cropTop>=jump.vsumBottom-2&&jump.cropTop<jump.vh-60),jump);ok("核對完沒有跳出蓋住卡片的訊息",!jump.toast,jump);
  // 存入門檻
  const n0=await dicts();await page.locator("#savebtn").scrollIntoViewIfNeeded();await page.click("#savebtn");await sleep(300);
  ok("還有沒確認的條目時存入被擋下",await dicts()===n0&&/還不能存入/.test(await page.innerText("#saveerr")),await page.innerText("#saveerr"));
  // 逐筆確認
  for(let i=0;i<80;i++){const b=page.locator("#rev button[data-a=okd]").first();if(!(await b.count()))break;await b.scrollIntoViewIfNeeded();await b.click()}
  // 筆數不符
  await page.locator("[data-expect]").first().fill("99");await page.locator("[data-expect]").first().blur();await sleep(200);
  await page.locator("#savebtn").scrollIntoViewIfNeeded();await page.click("#savebtn");await sleep(300);
  ok("書上筆數和清單不符時存入被擋下",await dicts()===n0&&/筆數/.test(await page.innerText("#saveerr")),await page.innerText("#saveerr"));
  const cnt=await page.evaluate(()=>+document.querySelector(".pphead b").textContent.match(/讀到 (\d+)/)[1]);await page.locator("[data-expect]").first().fill(String(cnt));await page.locator("[data-expect]").first().blur();await sleep(200);
  // 重新整理 → 還原
  const before=await page.evaluate(()=>({cards:document.querySelectorAll("#rev .rc").length,okd:[...document.querySelectorAll("#rev .badge")].filter(b=>b.textContent==="已人工確認").length}));
  await sleep(900);await page.reload();await page.waitForSelector("#file",{state:"attached"});
  const banner=await page.locator("#d-load").count();ok("重新整理後出現「還原核對清單」",banner===1);
  if(banner){await page.click("#d-load");await page.waitForSelector("#rev .rc");await settle();
    const after=await page.evaluate(()=>({cards:document.querySelectorAll("#rev .rc").length,okd:[...document.querySelectorAll("#rev .badge")].filter(b=>b.textContent==="已人工確認").length,crop:[...document.querySelectorAll("#rev canvas[data-crop]")].filter(c=>c.width>50).length,expect:document.querySelector("[data-expect]").value}));
    ok("還原後條目、已確認狀態、原圖裁切、筆數都還在",after.cards===before.cards&&after.okd===before.okd&&after.crop>0&&after.expect===String(cnt),{before,after})}
  // localStorage 滿了 → 存入失敗要明講，清單要留著
  await page.evaluate(()=>{const big="x".repeat(1024*1024);try{for(let i=0;i<20;i++)localStorage.setItem("__fill"+i,big)}catch(e){}try{for(let i=0;i<200;i++)localStorage.setItem("__f"+i,"y".repeat(20000))}catch(e){}try{for(let i=0;i<2000;i++)localStorage.setItem("__g"+i,"z".repeat(500))}catch(e){}});
  const left=await page.locator("#rev .loi.st-todo").count();for(let i=0;i<left;i++){await page.locator("#rev .loi.st-todo button[data-l=ignore]").first().click()}
  for(let i=0;i<80;i++){const b=page.locator("#rev button[data-a=okd]").first();if(!(await b.count()))break;await b.scrollIntoViewIfNeeded();await b.click()}
  const n1=await dicts(),c1=await page.locator("#rev .rc").count();await page.locator("#savebtn").scrollIntoViewIfNeeded();await page.click("#savebtn");await sleep(500);
  const sf={dicts:await dicts(),cards:await page.locator("#rev .rc").count(),err:await page.innerText("#saveerr").catch(()=>""),toast:await page.innerText("#toast").catch(()=>""),hash:await page.evaluate(()=>location.hash)};
  ok("空間不足時顯示存入失敗、清單保留、沒有顯示已存入",sf.dicts===n1&&sf.cards===c1&&/存入失敗/.test(sf.err)&&!/已存入/.test(sf.toast)&&sf.hash==="#upload",sf);
  // 清出空間後再存一次要成功
  await page.evaluate(()=>{Object.keys(localStorage).filter(k=>k.startsWith("__")).forEach(k=>localStorage.removeItem(k))});
  await page.click("#savebtn");await sleep(500);const s2={dicts:await dicts(),toast:await page.innerText("#toast").catch(()=>""),draft:await page.evaluate(()=>sessionStorage.getItem("vc-scan-draft")),hash:await page.evaluate(()=>location.hash),err:await page.innerText("#saveerr").catch(()=>"(gone)"),used:await page.evaluate(()=>JSON.stringify(localStorage).length)};R.dbg=s2.hash+" | "+s2.err.slice(0,60)+" | "+s2.used;
  ok("清出空間後存入成功，暫存的清單也清掉",s2.dicts===n1+1&&/已存入/.test(s2.toast)&&!s2.draft,{dicts:s2.dicts,toast:s2.toast,draft:!!s2.draft});
}catch(e){fails.push("例外："+e.message.slice(0,300))}finally{await browser.close()}
console.log(JSON.stringify(R,null,1));console.log("console 錯誤",errors.length,errors.slice(0,5));console.log(fails.length?"失敗："+fails.join("、"):"全部通過");
process.exit(fails.length||errors.length?1:0);
