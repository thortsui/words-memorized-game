// 掃描「漏網」實測：真的開瀏覽器跑上傳頁，把每張測試圖走完 上傳 →（調四角）→ 提取 → 核對，和正確答案比。
//   node tests/scan-leak.mjs [網址] [圖片名稱…]        （預設網址 http://127.0.0.1:4181/，預設跑全部 10 張）
//   先：npx vite build --outDir dist-scan && npx vite preview --outDir dist-scan --port 4181 --strictPort
// 每張圖回報：
//   自動通過且全對（雙重確認、每一欄都和答案一樣）／被攔下（需人工確認，不論對錯）／
//   漏條目（答案有、清單裡沒有）與其中「有被覆蓋率核對列出來」的筆數／漏網（雙重確認但內容和答案不一樣，或多出不存在的條目）。
// 另外量提取時主執行緒卡住的最長時間，並檢查「還有沒處理的就不能存入」。結果寫到 tests/scan-leak.result.json。
import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE=path.dirname(fileURLToPath(import.meta.url)),args=process.argv.slice(2),BASE=(args.find(a=>/^http/.test(a))||"http://127.0.0.1:4181/"),only=args.filter(a=>!/^http/.test(a)&&!/^--/.test(a)),PHONE=args.includes("--phone");
const SETS=[[path.join(HERE,"fixtures"),["page1.png","page2.png","page3.jpg"]],[path.join(HERE,"playtest","site","img"),["hard1.jpg","hard2.png","hard2b.png","hard2c.png","hard3.jpg","hard4.jpg","hard5.png"]]];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const lev=(a,b)=>{const m=[...Array(a.length+1)].map((_,i)=>[i]);for(let j=1;j<=b.length;j++)m[0][j]=j;for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)m[i][j]=Math.min(m[i-1][j]+1,m[i][j-1]+1,m[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return m[a.length][b.length]};
const key=s=>String(s).toLowerCase().replace(/[^a-z]+/g," ").trim();
const FIELDS=["en","pos","zh","ex","blank","unit"];
// 和試用測試（tests/playtest/site/t5-scan.mjs）同一套算法：每一欄都要和答案一字不差
function score(cards,truth,left){const used=new Set(),rows=[];
  for(const t of truth){let ci=cards.findIndex((c,i)=>!used.has(i)&&c.en===t.en);if(ci<0)ci=cards.findIndex((c,i)=>!used.has(i)&&key(c.en)===key(t.en));
    if(ci<0){let best=-1,bd=1e9;cards.forEach((c,i)=>{if(used.has(i))return;const d=lev(key(c.en),key(t.en))/Math.max(key(c.en).length,key(t.en).length,1);if(d<bd){bd=d;best=i}});if(bd<=.4)ci=best}
    if(ci<0)ci=cards.findIndex((c,i)=>!used.has(i)&&c.badge!=="雙重確認"&&((t.zh&&(c.zh.startsWith(t.zh.slice(0,4))||c.zh.includes(t.zh.slice(-4))))||(t.ex&&c.ex===t.ex)));   // 英文讀壞了但中文或例句對得上：算「有讀到、被攔下」
    if(ci<0){if(!t.optional){const k=key(t.en),listed=left.some(l=>{const lk=key(l.text+" "+(l.textB||""));return lk.includes(k)||lev(lk.slice(0,k.length),k)/Math.max(1,k.length)<=.34});rows.push({en:t.en,res:"MISSED",listed})}continue}
    used.add(ci);const c=cards[ci],diff=FIELDS.filter(k=>(c[k]||"").trim()!==(t[k]||"").trim()).map(k=>`${k}: 讀成「${c[k]}」正確「${t[k]}」`),auto=c.badge==="雙重確認";
    rows.push({en:t.en,badge:c.badge,res:auto?(diff.length?"LEAK":"auto-correct"):(diff.length?"caught-wrong":"caught-but-correct"),diff,why:c.why,optional:t.optional})}
  cards.forEach((c,i)=>{if(!used.has(i))rows.push({en:c.en,badge:c.badge,res:c.badge==="雙重確認"?"LEAK-phantom":"extra-flagged",diff:[`多出來的條目：${c.en}｜${c.pos}｜${c.zh}｜${c.ex}`],why:c.why})});
  const cnt=k=>rows.filter(r=>r.res===k&&!r.optional).length,N=truth.filter(t=>!t.optional).length,miss=rows.filter(r=>r.res==="MISSED");
  return{N,cards:cards.length,autoCorrect:cnt("auto-correct"),caught:cnt("caught-wrong")+cnt("caught-but-correct"),caughtWrong:cnt("caught-wrong"),missed:miss.length,missedListed:miss.filter(r=>r.listed).length,leak:rows.filter(r=>/^LEAK/.test(r.res)).length,extraFlagged:cnt("extra-flagged"),rows}}

const browser=await chromium.launch({channel:"chrome",headless:true});
const context=await browser.newContext(PHONE?{viewport:{width:390,height:700},hasTouch:true,isMobile:true,deviceScaleFactor:2,locale:"zh-TW"}:{viewport:{width:1280,height:900},locale:"zh-TW"});
const page=await context.newPage(),errors=[];
page.on("console",m=>{if(m.type()==="error")errors.push(m.text().slice(0,200))});page.on("pageerror",e=>errors.push("pageerror: "+e.message));page.on("dialog",d=>d.accept().catch(()=>{}));
const out={base:BASE,viewport:PHONE?"390x700":"1280x900",images:{},errors};
try{
  for(const [dir,names] of SETS){const truth=JSON.parse(fs.readFileSync(path.join(dir,"truth.json"),"utf8")),quads=fs.existsSync(path.join(dir,"quads.json"))?JSON.parse(fs.readFileSync(path.join(dir,"quads.json"),"utf8")):{};
    for(const name of names){if(only.length&&!only.includes(name))continue;const r={};out.images[name]=r;
      await page.goto(BASE+"#upload");await page.evaluate(()=>{sessionStorage.clear();["vc-ext","vc-ext2","vc-adv"].forEach(k=>localStorage.removeItem(k))});await page.reload();await page.waitForSelector("#file",{state:"attached"});
      await page.setInputFiles("#file",path.join(dir,name));await page.waitForSelector("#stage canvas");
      const q=quads[name];
      if(q&&!PHONE){ // 斜拍的照片：把四個角拖到紙張的四個角
        for(let i=0;i<4;i++){await page.evaluate(([i,qy])=>{const s=document.querySelector("#stage svg"),b=s.getBoundingClientRect(),vb=s.viewBox.baseVal,c=s.querySelectorAll("circle")[i],y=b.top+((+c.getAttribute("cy")+qy)/2)/vb.height*b.height;scrollBy(0,y-innerHeight*.55)},[i,q[i][1]]);await sleep(120);
          const g=await page.evaluate(()=>{const s=document.querySelector("#stage svg"),b=s.getBoundingClientRect(),vb=s.viewBox.baseVal;return{l:b.left,t:b.top,w:b.width,h:b.height,W:vb.width,H:vb.height,pts:[...s.querySelectorAll("circle")].map(c=>[+c.getAttribute("cx"),+c.getAttribute("cy")])}});
          const toC=([x,y])=>[g.l+x/g.W*g.w,g.t+y/g.H*g.h],[x0,y0]=toC(g.pts[i]),[x1,y1]=toC(q[i]);
          await page.mouse.move(x0,y0);await page.mouse.down();await page.mouse.move((x0+x1)/2,(y0+y1)/2,{steps:4});await page.mouse.move(x1,y1,{steps:4});await page.mouse.up();await sleep(80)}}
      // 提取：記錄主執行緒卡住的時間與進度文字
      await page.evaluate(()=>{window.__gaps=[];let last=performance.now();window.__hb=setInterval(()=>{const n=performance.now();if(n-last>150)window.__gaps.push(Math.round(n-last));last=n},25)});
      const prog=new Set();let stop=false;const sampler=(async()=>{while(!stop){const t=await page.evaluate(()=>(document.querySelector("#prog")||{}).textContent||"").catch(()=>"");if(t)prog.add(t.replace(/[\d.]+/g,"#"));await sleep(200)}})();
      const t0=Date.now();await page.locator("#extract").scrollIntoViewIfNeeded();await page.click("#extract");
      await page.waitForFunction(()=>document.querySelector("#rev .rc,#rev .pp")||/沒有提取到/.test((document.querySelector("#prog")||{}).textContent||""),null,{timeout:600000});
      r.extractMs=Date.now()-t0;stop=true;await sampler;
      r.freeze=await page.evaluate(()=>{clearInterval(window.__hb);const g=window.__gaps;return{maxMs:Math.max(0,...g),stalls:g.length}});
      r.progress=[...prog].filter(t=>/下載|tesseract|PP-OCR/.test(t)).slice(0,12);r.badProgress=[...prog].filter(t=>/[a-z]{4,} [a-z]{4,}/.test(t.replace(/tesseract|PP-OCR/g,""))).slice(0,4);
      if(await page.locator("#rev .rc").count())await page.waitForFunction(()=>!/核對中|檢查中/.test(document.querySelector("#revbox").innerText),null,{timeout:180000});
      await sleep(400);
      const snap=await page.evaluate(()=>({cards:[...document.querySelectorAll("#rev .rc")].map(c=>{const v=k=>(c.querySelector(`[data-k=${k}]`)||{}).value||"";return{badge:c.querySelector(".badge").textContent,en:v("en"),pos:v("pos"),zh:v("zh"),ex:v("ex"),blank:v("blank"),unit:v("unit"),why:[...c.querySelectorAll(".why li")].map(x=>x.textContent).join("；"),raw:[...c.querySelectorAll(".df.raw .val")].map(v=>v.innerHTML.replace(/<mark class="dfc">/g,"⟦").replace(/<.mark>/g,"⟧").replace(/<[^>]+>/g,"")).join("  ‖  ")}}),
        left:[...document.querySelectorAll("#rev .loi")].map(l=>({text:(l.querySelector(".lotx")||{}).textContent||"",textB:[...l.querySelectorAll(".small")].map(x=>x.textContent).join(" "),todo:l.classList.contains("st-todo")})),
        skipped:[...document.querySelectorAll("#rev .pp details")].map(d=>d.textContent).join(" ").slice(0,300),pageHead:[...document.querySelectorAll("#rev .pphead b")].map(b=>b.textContent).join("；"),sum:document.querySelector("#vsum")?document.querySelector("#vsum").innerText.replace(/\n+/g," | "):""}));
      r.pageHead=snap.pageHead;r.leftovers=snap.left.map(l=>l.text);r.skipped=snap.skipped;r.sum=snap.sum;
      const s=score(snap.cards,truth[name],snap.left);r.score={N:s.N,cards:s.cards,autoCorrect:s.autoCorrect,caught:s.caught,caughtWrong:s.caughtWrong,missed:s.missed,missedListed:s.missedListed,leak:s.leak,extraFlagged:s.extraFlagged};
      r.problems=s.rows.filter(x=>/LEAK|MISSED/.test(x.res)).map(x=>({res:x.res,en:x.en,listed:x.listed,diff:x.diff}));r.caughtDetail=s.rows.filter(x=>/caught|extra/.test(x.res)).map(x=>`${x.res}｜${x.en}｜${(x.diff||[]).join("、")}｜${x.why||""}`);r.rawDiffs=snap.cards.filter(c=>c.raw).map(c=>c.en+"： "+c.raw);
      // 存入門檻：還有沒處理的就不能存
      const need=snap.cards.filter(c=>!/^(雙重確認|手動輸入・檢查通過)$/.test(c.badge)).length+snap.left.filter(l=>l.todo).length;
      if(need&&await page.locator("#savebtn").count()){const before=await page.evaluate(()=>Object.keys((JSON.parse(localStorage.getItem("vocab-cards-v1")||"{}").dicts)||{}).length);await page.locator("#savebtn").scrollIntoViewIfNeeded();await page.click("#savebtn");await sleep(300);
        r.gate={blocked:(await page.locator("#rev .rc,#rev .pp").count())>0&&before===await page.evaluate(()=>Object.keys((JSON.parse(localStorage.getItem("vocab-cards-v1")||"{}").dicts)||{}).length),msg:await page.locator("#saveerr").innerText().catch(()=>"")}}
      console.log(`${name}: N=${s.N} 自動通過且全對=${s.autoCorrect} 被攔下=${s.caught}（其中讀錯 ${s.caughtWrong}） 漏條目=${s.missed}（有列出 ${s.missedListed}） 漏網=${s.leak} 多出來被攔下=${s.extraFlagged} 沒收進條目的文字=${snap.left.length} 段 卡住最長=${r.freeze.maxMs}ms 提取=${r.extractMs}ms`);
      for(const p of r.problems)console.log("    "+p.res+(p.res==="MISSED"?(p.listed?"（已列出）":"（沒列出！）"):"")+" "+p.en+" "+JSON.stringify(p.diff||""))}}
}finally{await browser.close()}
const tot=Object.values(out.images).reduce((t,r)=>{for(const k of ["N","autoCorrect","caught","missed","missedListed","leak"])t[k]=(t[k]||0)+r.score[k];t.maxFreeze=Math.max(t.maxFreeze||0,r.freeze.maxMs);return t},{});
out.total=tot;fs.writeFileSync(path.join(HERE,"scan-leak.result"+(PHONE?".phone":"")+".json"),JSON.stringify(out,null,1));
console.log("合計",JSON.stringify(tot),"console 錯誤",errors.length,errors.slice(0,3));
process.exit(tot.leak||tot.missed!==tot.missedListed?1:0);
