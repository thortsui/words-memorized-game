import { chromium } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/playwright-core/index.mjs';
const b=await chromium.launch({channel:'chrome',headless:true});const p=await b.newPage({viewport:{width:1920,height:1080}});
const css=`@font-face{font-family:S;src:url(file:///C:/Windows/Fonts/NotoSerifTC-VF.ttf)}html,body{margin:0;background:transparent;width:1920px;height:1080px;overflow:hidden}
.cap{position:absolute;left:150px;top:0;bottom:0;width:960px;display:flex;flex-direction:column;justify-content:center;font-family:S}
.st{font:600 26px S;letter-spacing:.6em;color:#c9a24a;margin-bottom:14px;text-shadow:0 2px 8px #000}
.a{font:900 124px/1.1 S;filter:url(#brush) drop-shadow(0 6px 22px rgba(0,0,0,.95))}
.b{font:500 38px S;letter-spacing:.24em;color:#e2d8c3;margin-top:22px;text-shadow:0 2px 10px #000}
.gold{background:linear-gradient(180deg,#fff1c4 0%,#e9c06a 45%,#a8701f 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.red{background:linear-gradient(180deg,#ffd0c8 0%,#ff5a48 45%,#8e1a12 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.white{background:linear-gradient(180deg,#ffffff 0%,#d9d2c2 60%,#8a8272 100%);-webkit-background-clip:text;background-clip:text;color:transparent}`;
const svg=`<svg width=0 height=0 style=position:absolute><filter id=brush x=-5% y=-5% width=110% height=110%><feTurbulence type=fractalNoise baseFrequency=.045 numOctaves=3 seed=7 result=n /><feDisplacementMap in=SourceGraphic in2=n scale=7 /></filter></svg>`;
const cap=(k,st,a,cl,sub)=>[k,`<div class=cap><div class=st>${st}</div><div class="a ${cl}">${a}</div><div class=b>${sub}</div></div>`];
const cards=[
 cap('p1','實　戰','你的回合','gold','答對單字　自動連斬'),
 cap('p2','警　告','突襲！','red','時限極短　答對才閃得開'),
 cap('p3','反　擊','完美彈反','gold','金色區內答對　立刻反擊'),
 cap('p4','失　誤','答錯　露出破綻','red','魔王衝上來把你打倒'),
 cap('p5','防　守','魔王的回合','white','每一擊都要答題閃避'),
 cap('p6','閃　避','突進　翻滾','gold','不能彈反　答對才翻得開'),
 cap('p7','失　誤','答錯　舉盾硬擋','red','耐力 −50　連擊還沒結束'),
 cap('p8','反　攻','看穿攻勢','gold','突擊！連續答對　每題砍一刀'),
];
await p.setContent(`<style>${css}</style>${svg}<div id=c></div>`);
for(const [k,h] of cards){await p.evaluate(h=>document.getElementById('c').innerHTML=h,h);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(120);await p.screenshot({path:`cards/${k}.png`,omitBackground:true})}
// 手機外框：外框不透明、螢幕區透明（圓角）
const W=461,H=1000,B=16,R=50;
await p.setContent(`<canvas id=k width=${W+2*B} height=${H+2*B}></canvas>`);
await p.evaluate(([W,H,B,R])=>{const c=document.getElementById('k'),x=c.getContext('2d');const rr=(x0,y0,w,h,r)=>{x.beginPath();x.moveTo(x0+r,y0);x.arcTo(x0+w,y0,x0+w,y0+h,r);x.arcTo(x0+w,y0+h,x0,y0+h,r);x.arcTo(x0,y0+h,x0,y0,r);x.arcTo(x0,y0,x0+w,y0,r);x.closePath()};
  rr(0,0,W+2*B,H+2*B,R+B);const g=x.createLinearGradient(0,0,W,H);g.addColorStop(0,'#3a3530');g.addColorStop(.5,'#141210');g.addColorStop(1,'#2c2722');x.fillStyle=g;x.fill();
  x.lineWidth=2;x.strokeStyle='rgba(201,162,74,.55)';rr(1,1,W+2*B-2,H+2*B-2,R+B-1);x.stroke();
  x.globalCompositeOperation='destination-out';rr(B,B,W,H,R);x.fill()},[W,H,B,R]);
const data=await p.evaluate(()=>document.getElementById('k').toDataURL('image/png'));
(await import('node:fs')).writeFileSync('cards/bezel.png',Buffer.from(data.split(',')[1],'base64'));
await b.close();console.log('ok');
