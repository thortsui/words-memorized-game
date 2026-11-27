import { chromium } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/playwright-core/index.mjs';
const b=await chromium.launch({channel:'chrome',headless:true});const p=await b.newPage({viewport:{width:1920,height:1080}});
const css=`@font-face{font-family:S;src:url(file:///C:/Windows/Fonts/NotoSerifTC-VF.ttf)}html,body{margin:0;background:transparent;width:1920px;height:1080px;overflow:hidden}
.dim{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(0,0,0,.45),rgba(0,0,0,.78))}
.q{position:absolute;left:50%;top:190px;transform:translateX(-50%);width:1240px;text-align:center;font-family:S}
.tag{font:600 24px S;letter-spacing:.6em;color:#c9a24a;margin-bottom:10px}
.pr{font:700 108px Georgia,serif;color:#f6eedb;letter-spacing:.02em;text-shadow:0 0 40px rgba(233,192,106,.35),0 4px 10px #000}
.ops{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:42px}
.op{position:relative;padding:20px 26px 20px 74px;text-align:left;font:500 34px S;color:#e2d8c3;background:rgba(20,16,12,.72);border:2px solid rgba(201,162,74,.35);border-radius:6px}
.op .k{position:absolute;left:22px;top:50%;transform:translateY(-50%);font:600 26px Georgia;color:#8a7f6c}
.op.ok{border-color:#f0cf7a;background:linear-gradient(90deg,rgba(150,110,40,.65),rgba(40,30,15,.75));color:#fff6df;box-shadow:0 0 40px rgba(240,207,122,.55)}
.op.bad{border-color:#e0453a;background:linear-gradient(90deg,rgba(150,30,25,.7),rgba(40,12,10,.8));color:#ffe9e6;box-shadow:0 0 40px rgba(224,69,58,.6)}
.op.hint{border-color:rgba(240,207,122,.8)}
.op .m{position:absolute;right:24px;top:50%;transform:translateY(-50%);font:900 46px S}
.op.ok .m{color:#ffe08a}.op.bad .m{color:#ff6b5e}
.res{position:absolute;left:150px;bottom:210px;font-family:S}
.res .a{font:900 120px/1 S;filter:url(#brush) drop-shadow(0 6px 22px rgba(0,0,0,.95))}
.res .b{font:500 30px S;letter-spacing:.3em;color:#d9cfbb;margin-top:16px;text-shadow:0 2px 8px #000}
.gold{background:linear-gradient(180deg,#fff1c4 0%,#e9c06a 45%,#a8701f 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.red{background:linear-gradient(180deg,#ffd0c8 0%,#ff5a48 45%,#8e1a12 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.vig{position:absolute;inset:0;box-shadow:inset 0 0 260px 90px rgba(200,20,10,.75)}
.slo{position:absolute;inset:0;display:grid;place-items:center;text-align:center;font-family:S}`;
const svg=`<svg width=0 height=0 style=position:absolute><filter id=brush x=-5% y=-5% width=110% height=110%><feTurbulence type=fractalNoise baseFrequency=.045 numOctaves=3 seed=7 result=n /><feDisplacementMap in=SourceGraphic in2=n scale=7 /></filter></svg>`;
const Q=[['q1','let go of sth/sb',["開啟……的機會；為……創造可能性","最後變成、結果成為……","感覺好像……；似乎……","放開……；放棄……"],3,3],
 ['q2','option',["社區；群體；共同體","曆法；日曆；行事曆","選擇、選項；可選擇的事物","家教、私人教師"],2,3],
 ['q3','in the end',["過去經常……","說到底、歸根究柢、總而言之","已經習慣於……","本來可以……但實際上沒有"],1,1]];
const cards=[];
for(const [k,pr,ops,r,c] of Q){
  const mk=sel=>`<div class=dim></div><div class=q><div class=tag>英　翻　中</div><div class=pr>${pr}</div><div class=ops>${ops.map((o,i)=>{let cl='';let m='';if(sel){if(i===c)cl=c===r?'ok':'bad',m=c===r?'✓':'✗';else if(i===r)cl='hint'}return `<div class="op ${cl}"><span class=k>${'ABCD'[i]}</span>${o}${m?`<span class=m>${m}</span>`:''}</div>`}).join('')}</div></div>`;
  cards.push([k,mk(false)],[k+'s',mk(true)])}
cards.push(['r_ok1',`<div class=res><div class="a gold">答對　出劍</div><div class=b>let go of sth/sb ── 放開……；放棄……</div></div>`]);
cards.push(['r_bad',`<div class=vig></div><div class=res><div class="a red">答錯　受擊</div><div class=b>option ── 不是「家教」，是「選擇、選項」</div></div>`]);
cards.push(['r_ok2',`<div class=res><div class="a gold">答對　格擋反擊</div><div class=b>in the end ── 說到底、總而言之</div></div>`]);
cards.push(['slogan',`<div class=slo><div><div class=gold style="font:900 110px/1.25 S;filter:url(#brush)">答對單字　即是出劍</div><div class=red style="font:900 64px S;margin-top:26px;filter:url(#brush)">答錯一字　魔王就會出手</div><div style="font:500 26px S;letter-spacing:.3em;margin-top:40px;color:#8a7f6c">英翻中・中翻英・克漏字・拼字　四種題型</div></div></div>`]);
await p.setContent(`<style>${css}</style>${svg}<div id=c></div>`);
for(const [k,h] of cards){await p.evaluate(h=>document.getElementById('c').innerHTML=h,h);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(120);await p.screenshot({path:`cards/${k}.png`,omitBackground:true})}
await b.close();console.log(cards.length);
