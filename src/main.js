// 進入點：hash 路由（#dicts、#dict-<id>、#upload、#practice、#history）
import './style.css';
import { $ } from './core/util.js';
import { ctx, pool } from './core/store.js';
import { renderDicts, renderDict } from './pages/dicts.js';
import { renderUpload } from './pages/upload.js';
import { renderSetup, startQuiz } from './pages/practice.js';
import { renderHist } from './pages/history.js';
import { endBattle } from './battle/controller.js';
import { stopSpeech } from './core/speech.js';

function route(){const h=location.hash.slice(1)||"dicts";
  if(ctx.B){endBattle();stopSpeech()} // 換頁就離開戰鬥
  document.body.classList.remove("inbattle","soulmode");ctx.Q=null;ctx.view=h;
  ["dicts","upload","practice","history"].forEach(n=>$("#n-"+n).classList.toggle("on",h===n||(n==="dicts"&&h.startsWith("dict-"))));
  if(h.startsWith("dict-"))renderDict(h.slice(5));
  else if(h==="upload")renderUpload();
  else if(h==="practice"){if(ctx.autoStart){ctx.autoStart=false;const p=pool();p.length?startQuiz(p):renderSetup()}else renderSetup()}
  else if(h==="history")renderHist();
  else renderDicts();
  window.scrollTo(0,0)}
addEventListener("hashchange",route);
route();
