import { chromium } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/playwright-core/index.mjs';
const b=await chromium.launch({channel:'chrome',headless:true});const p=await b.newPage({viewport:{width:1920,height:1080}});
const css=`@font-face{font-family:S;src:url(file:///C:/Windows/Fonts/NotoSerifTC-VF.ttf)}@font-face{font-family:K;src:url(file:///C:/Windows/Fonts/kaiu.ttf)}
html,body{margin:0;background:transparent;width:1920px;height:1080px;overflow:hidden}
.c{position:absolute;inset:0;font-family:S,serif;color:#e9e2d2}
.nar{position:absolute;left:0;right:0;text-align:center;font:700 58px S;letter-spacing:.32em;text-shadow:0 0 24px rgba(0,0,0,.9),0 2px 4px #000;filter:url(#brush)}
.gold{background:linear-gradient(180deg,#fff1c4 0%,#e9c06a 45%,#a8701f 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.boss{position:absolute;left:150px;bottom:205px}
.boss .ord{font:600 26px S;letter-spacing:.8em;color:#c9a24a;margin-bottom:6px;text-shadow:0 2px 8px #000}
.boss .nm{font:900 148px/1.05 S;letter-spacing:.04em;filter:url(#brush) drop-shadow(0 6px 22px rgba(0,0,0,.95))}
.boss .ln{width:560px;height:2px;margin:18px 0 14px;background:linear-gradient(90deg,#c9a24a,transparent)}
.boss .sub{font:500 30px S;letter-spacing:.3em;color:#d9cfbb;text-shadow:0 2px 8px #000}
.seal{display:inline-grid;place-items:center;border:4px solid #b3261e;color:#d0392e;border-radius:10px;font:900 1em S;transform:rotate(-8deg);background:rgba(179,38,30,.1)}
.word{position:absolute;inset:0;display:grid;place-items:center;text-align:center}
.word b{display:block;font:800 150px Georgia,serif;letter-spacing:.12em;color:#f3ead6;text-shadow:0 0 40px rgba(233,192,106,.45)}
.word i{display:block;font:700 46px S;font-style:normal;letter-spacing:.4em;color:#c9a24a;margin-top:10px}
`;
const svg=`<svg width=0 height=0 style=position:absolute><filter id=brush x=-5% y=-5% width=110% height=110%><feTurbulence type=fractalNoise baseFrequency=.045 numOctaves=3 seed=7 result=n /><feDisplacementMap in=SourceGraphic in2=n scale=7 /></filter></svg>`;
const boss=(i,ord,nm,lv,mv)=>[`boss${i}`,`<div class=boss><div class=ord>${ord}</div><div class="nm gold">${nm}</div><div class=ln></div><div class=sub>Lv.${lv}　・　${mv}</div></div>`];
const word=(k,en,zh)=>[k,`<div class=word><div><b>${en}</b><i>${zh}</i></div></div>`];
const cards=[
 ['n1',`<div class=nar style="top:430px">詞語之火熄滅之後</div>`],
 ['n2',`<div class=nar style="top:540px;font-size:46px;color:#bdb39f">王國只剩下灰與低語</div>`],
 ['n3',`<div class=nar style="top:800px;font-size:50px">你是最後一名記得單字的人</div>`],
 ['n4',`<div class=nar style="top:420px;font-size:64px">每答出一個字</div>`],
 ['n5',`<div class="nar gold" style="top:540px;font-size:88px;font-weight:900">劍就多一分重量</div>`],
 boss(1,'第一試煉','腐朽守門騎士',5,'鏽戟橫掃'),boss(2,'第二試煉','教堂石像鬼',10,'俯衝利爪'),boss(3,'第三試煉','霜冠祭司',16,'霜槍突刺'),
 boss(4,'第四試煉','暗影行刑者',22,'斷頭斧斬'),boss(5,'終焉之王','噬語魔王',30,'噬語巨劍'),
 ['ui1',`<div style="position:absolute;left:130px;top:390px"><div class="gold" style="font:900 96px/1.2 S;filter:url(#brush)">答對單字<br>即是出劍</div><div style="font:500 32px S;letter-spacing:.3em;margin-top:28px;color:#d9cfbb">答錯　便由魔王出手</div><div style="font:500 24px S;letter-spacing:.25em;margin-top:14px;color:#8a7f6c">英翻中・中翻英・克漏字・拼字</div></div>`],
 word('w1','DETERMINED','下定決心的'),word('w2','CONCLUDE','作出結論'),word('w3','REMEMBER','記住'),
 ['title',`<div style="position:absolute;left:150px;top:300px"><div style="position:relative;display:inline-block;padding-right:110px"><div class=gold style="font:900 250px/1 S;letter-spacing:-.02em;filter:url(#brush) drop-shadow(0 8px 30px rgba(0,0,0,.9))">單字魂</div><span class=seal style="position:absolute;right:0;top:14px;width:86px;height:86px;font-size:52px">字</span></div><div style="font:600 30px Georgia,serif;letter-spacing:.9em;color:#c9a24a;margin:14px 0 0 .4em">WORD SOUL</div><div style="font:500 42px S;letter-spacing:.42em;margin-top:34px;color:#e2d8c3;text-shadow:0 2px 8px #000">一字一劍　斬盡遺忘</div></div>`],
 ['end',`<div style="position:absolute;inset:0;display:grid;place-items:center;text-align:center"><div><div class=gold style="font:900 84px S;letter-spacing:.3em;filter:url(#brush)">即刻踏上試煉</div><div style="font:500 36px Georgia,serif;letter-spacing:.06em;color:#e9e2d2;margin-top:44px">thortsui.github.io/words-memorized-game</div><div style="font:500 26px S;letter-spacing:.3em;color:#8a7f6c;margin-top:22px">免費遊玩　・　iPhone 可加入主畫面　・　v1.0.1</div></div></div>`],
];
await p.setContent(`<style>${css}</style>${svg}<div class=c id=c></div>`);await p.waitForTimeout(500);
for(const [k,h] of cards){await p.evaluate(h=>document.getElementById('c').innerHTML=h,h);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(150);await p.screenshot({path:`cards/${k}.png`,omitBackground:true})}
await b.close();console.log('cards',cards.length);
