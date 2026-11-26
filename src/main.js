// 進入點：hash 路由（#home 封面、#dicts、#dict-<id>、#upload、#practice、#missed、#history）
import './style.css';
import { $ } from './core/util.js';
import { ctx, pool } from './core/store.js';
import { renderDicts, renderDict, leaveDict } from './pages/dicts.js';
import { renderUpload } from './pages/upload.js';
import { renderSetup, startQuiz, startCards } from './pages/practice.js';
import { renderMissed } from './pages/missed.js';
import { renderHist } from './pages/history.js';
import { renderCover, leaveCover } from './pages/cover.js';
import { endBattle } from './battle/controller.js';
import { stopSpeech } from './core/speech.js';

function route(){const h=location.hash.slice(1)||"home";
  leaveCover();         // 離開封面：停掉 3D 背景
  if(ctx.B)endBattle(); // 換頁就離開戰鬥
  stopSpeech();         // 換頁一律停止朗讀與字幕
  leaveDict(h);         // 離開字典內頁：丟掉還沒儲存的新增／編輯
  document.body.classList.remove("inbattle","soulmode");ctx.Q=null;ctx.view=h;
  ["dicts","upload","practice","missed","history"].forEach(n=>$("#n-"+n).classList.toggle("on",h===n||(n==="dicts"&&h.startsWith("dict-"))));
  if(h.startsWith("dict-"))renderDict(h.slice(5));
  else if(h==="upload")renderUpload();
  else if(h==="practice"){const o=ctx.autoStart;ctx.autoStart=false;
    // o：只套用這一次的設定（錯題頁的「練習待複習」）；目前題型出不了題（例如克漏字沒有例句）就改用英翻中選擇
    // only：只出這些字（歷史錯誤單字頁）；cards：改用閃卡
    if(o&&typeof o==="object"){const only=o.only?new Set(o.only):null,cards=o.cards;delete o.only;delete o.cards;
      const pick=x=>{let p=pool(x);if(only)p=p.filter(w=>only.has(w.dict+"|"+w.id));return p};
      if(cards){const p=pick({...o,mode:"en2zh"});if(p.length)startCards(p,o.n);else renderSetup()}
      else{let p=pick(o);if(!p.length&&!o.mode){o.mode="en2zh";p=pick(o)}if(p.length)startQuiz(p,o);else renderSetup()}}else renderSetup()}
  else if(h==="history")renderHist();
  else if(h==="missed")renderMissed();
  else if(h==="home")renderCover();
  else renderDicts();
  window.scrollTo(0,0)}
addEventListener("hashchange",route);
route();
