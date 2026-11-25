// 進入點：hash 路由（#dicts、#dict-<id>、#upload、#practice、#history）
import './style.css';
import { $ } from './core/util.js';
import { ctx, pool } from './core/store.js';
import { renderDicts, renderDict, leaveDict } from './pages/dicts.js';
import { renderUpload } from './pages/upload.js';
import { renderSetup, startQuiz } from './pages/practice.js';
import { renderHist } from './pages/history.js';
import { endBattle } from './battle/controller.js';
import { stopSpeech } from './core/speech.js';

function route(){const h=location.hash.slice(1)||"dicts";
  if(ctx.B)endBattle(); // 換頁就離開戰鬥
  stopSpeech();         // 換頁一律停止朗讀與字幕
  leaveDict(h);         // 離開字典內頁：丟掉還沒儲存的新增／編輯
  document.body.classList.remove("inbattle","soulmode");ctx.Q=null;ctx.view=h;
  ["dicts","upload","practice","history"].forEach(n=>$("#n-"+n).classList.toggle("on",h===n||(n==="dicts"&&h.startsWith("dict-"))));
  if(h.startsWith("dict-"))renderDict(h.slice(5));
  else if(h==="upload")renderUpload();
  else if(h==="practice"){const o=ctx.autoStart;ctx.autoStart=false;
    // o：只套用這一次的設定（錯題頁的「練習待複習」）；目前題型出不了題（例如克漏字沒有例句）就改用英翻中選擇
    if(o&&typeof o==="object"){let p=pool(o);if(!p.length&&!o.mode){o.mode="en2zh";p=pool(o)}if(p.length)startQuiz(p,o);else renderSetup()}else renderSetup()}
  else if(h==="history")renderHist();
  else renderDicts();
  window.scrollTo(0,0)}
addEventListener("hashchange",route);
route();
