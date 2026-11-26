// 練習設定頁與一般練習（五種題型）
import { $, app, esc, SC, lsSet, toast, KEY_HINT } from '../core/util.js';
import { S, allDicts, setup, saveSetup, pool, mark, unlog, pushHist, allWords, ctx } from '../core/store.js';
import { MODES, shuffle, clozeAns, clozePos, zhPrompt, opts, normEn, checkEn, checkZhSmart } from '../core/grading.js';
import { recordTyping } from '../core/typing.js';
import { sp, speak, readAll, gate, spkBtn, enVoices, stopSpeech, resetGoogleFail } from '../core/speech.js';
import { bgmStop } from '../core/audio.js';
import { wordRow } from './dicts.js';
import { startBattle } from '../battle/controller.js';

sp.onVoices=()=>{if(ctx.view==="practice"&&!ctx.Q&&!ctx.B&&$("#vsel"))renderSetup()};

export function renderSetup(){const D=allDicts();if(!D[setup.dict]&&setup.dict!=="__all")setup.dict=Object.keys(D)[0]||"__all";const n=pool().length;
  const chip=(k,v,l)=>`<button class="chip ${setup[k]===v?"on":""}" data-k="${k}" data-v="${esc(JSON.stringify(v))}">${l}</button>`;
  const eng=sp.eng;
  app.innerHTML=`<h1>練習</h1><p class="sub">選字典與題型，開始刷題。答錯的會記進錯題本。</p>
  <div class="cut">${SC}<div class="tab"><span>SETUP</span></div><div class="body">
  <label><span class="small">字典</span><select id="dsel"><option value="__all">全部字典</option>${Object.values(D).map(d=>`<option value="${esc(d.id)}" ${d.id===setup.dict?"selected":""}>${esc(d.name)}（${d.words.length}）</option>`).join("")}</select></label>
  <h2 style="font-size:16px;margin:18px 0 8px">玩法</h2><div class="chips">${chip("game",false,"一般練習")}${chip("game",true,"打怪模式")}${chip("game","soul","魂系模式")}</div>${setup.game==="soul"?'<p class="small" style="margin:6px 0 0">黑暗奇幻的 Boss 戰，所有動作都由答題驅動。你的回合有 10 秒攻擊時間（讀音與出招時暫停），每答對一題累積 1 格 ATB，可用 1 格斬擊、2 格連斬，或存滿 3 格放大招。Boss 出手時會出限時閃避題：<b>很快答對＝彈反並反擊</b>，一般速度答對＝翻滾閃避（消耗耐力），太慢只能擦傷，答錯或超時就會中招。Boss 會連擊（段與段之間不停）、延遲出手（選項先鎖住，太急會慢半拍）、突進（不能彈反），第二階段還有擋不住的必殺；你攻擊時拖太久也可能被突襲打斷。HP 低時可以喝藥壺（也要答對才喝得下去）。遊戲會依你最近的答題速度自動調整難度：你答得越快，Boss 出手越多、時限越短。</p>':setup.game?'<p class="small" style="margin:6px 0 0">劍與魔法的世界：按「下一題」才開始計時；答對獲得 1～10 點能量（越快越多，最多存 40），再選劍技或魔法出手（普通斬擊免費，其他從 10 點起跳），或保留能量放大招。連招（3／5／7 題）不耗能量，連續答對指定題數（時間更短）才會一次發動，傷害最高；答錯會被怪物攻擊、連招中斷。打倒 5 隻怪物就破關！</p>':""}
  <h2 style="font-size:16px;margin:18px 0 8px">題型</h2><div class="chips">${MODES.map(m=>chip("mode",m[0],m[1])).join("")}</div>
  <h2 style="font-size:16px;margin:18px 0 8px">範圍</h2><div class="chips">${chip("scope","all","單字＋片語")}${chip("scope","w","只有單字")}${chip("scope","p","只有片語")}${chip("wrong",true,"只練錯題")}${chip("wrong",false,"全部題目")}</div>
  <h2 style="font-size:16px;margin:18px 0 8px">題數</h2><div class="chips">${chip("n",10,"10 題")}${chip("n",20,"20 題")}${chip("n",0,"全部")}</div>
  <h2 style="font-size:16px;margin:18px 0 8px">例句模式 <span class="small" style="font-weight:400">開啟後題目下方顯示英文例句（不附中文）</span></h2><div class="chips">${chip("exmode",false,"關閉")}${chip("exmode",true,"開啟")}</div>
  <h2 style="font-size:16px;margin:18px 0 8px">發音</h2><div class="chips">${chip("auto",true,"出題時自動唸英文")}${chip("auto",false,"不自動唸")}<button class="chip ${sp.rate<.8?"on":""}" id="slow">慢速</button></div>
  <h2 style="font-size:16px;margin:18px 0 8px">聲音</h2><div class="chips">${[["auto","自動（推薦，最穩定）"],["device","只用裝置語音"],["google","Google 翻譯語音優先"]].map(([v,l])=>`<button class="chip ${eng===v?"on":""}" data-eng="${v}">${l}</button>`).join("")}<button class="chip" data-say="Emma appreciated her neighbor taking care of her dog.">試聽</button></div>
  <div class="row ${eng!=="google"?"":"hide"}" style="margin-top:8px"><select id="vsel" style="flex:1 1 220px;width:auto">${enVoices().length?enVoices().map(v=>`<option value="${esc(v.name)}" ${(sp.voiceName?v.name===sp.voiceName:sp.voice&&v.name===sp.voice.name)?"selected":""}>${esc(v.name)}（${esc(v.lang)}）</option>`).join(""):'<option value="">預設英文聲音</option>'}</select></div>
  <p class="small" style="margin:6px 0 0">${eng==="auto"?"先用瀏覽器內建語音（Chrome 的「Google US English」與「Google 國語」，穩定且不會被擋）；內建語音沒反應時才改用 Google 翻譯語音。":eng==="google"?"Google 翻譯語音不是正式服務，常被限流；連不上時會自動改用裝置語音。":"iPhone／Mac 可到 設定 → 輔助使用 → 朗讀內容 → 聲音 → 英文，下載「Ava（進階）」或 Siri 聲音，這裡就會出現，聲音最自然。"}</p>
  <div class="row" style="margin-top:22px"><button class="pri" id="start" ${n?"":"disabled"} style="flex:1 1 220px">${setup.game==="soul"?"開始魂系戰鬥！":setup.game?"開始戰鬥！":"開始"}（可出 ${n} 題）</button></div>
  ${n?"":`<p class="small">${setup.wrong?"這個範圍目前沒有錯題，太好了！":setup.mode==="cloze"?"這個範圍沒有可用的例句克漏字。":"這個範圍沒有條目。"}</p>`}</div></div>`;
  $("#dsel").onchange=e=>{setup.dict=e.target.value;saveSetup();renderSetup()};
  app.querySelectorAll("[data-k]").forEach(b=>b.onclick=()=>{setup[b.dataset.k]=JSON.parse(b.dataset.v);saveSetup();renderSetup()});
  app.querySelectorAll("[data-eng]").forEach(b=>b.onclick=()=>{sp.eng=b.dataset.eng;resetGoogleFail();lsSet("vc-eng3",sp.eng);renderSetup()});
  $("#vsel").onchange=e=>{sp.voiceName=e.target.value;lsSet("vc-voice",sp.voiceName)};
  $("#slow").onclick=()=>{sp.rate=sp.rate<.8?.9:.65;lsSet("vc-rate",sp.rate);renderSetup()};
  $("#start").onclick=()=>setup.game?startBattle(pool(),setup.game==="soul"):startQuiz(pool())}

export function exLine(w,hideAns){if(!setup.exmode||!w.ex)return"";const a=clozeAns(w),i=clozePos(w.ex,a);
  if(i<0)return hideAns?"":`<div class="row" style="gap:8px;flex-wrap:nowrap;margin-top:12px"><div class="ex en" style="font-size:17px;color:var(--ink)">${esc(w.ex)}</div>${spkBtn(w.ex,"朗讀例句")}</div>`;
  const mid=hideAns?'<span class="blank">　?　</span>':`<b style="color:var(--or)">${esc(w.ex.slice(i,i+a.length))}</b>`;
  return `<div class="row" style="gap:8px;flex-wrap:nowrap;margin-top:12px;padding-top:12px;border-top:1px dashed var(--line)"><div class="ex en" style="font-size:17px;color:var(--ink)">${esc(w.ex.slice(0,i))}${mid}${esc(w.ex.slice(i+a.length))}</div>${hideAns?"":spkBtn(w.ex,"朗讀例句")}</div>`}

export function toSetup(){ctx.Q=null;ctx.B=null;document.body.classList.remove("inbattle");bgmStop();stopSpeech();if(location.hash!=="#practice")location.hash="practice";else renderSetup();window.scrollTo(0,0)}

let Q=null;
// over：只套用這一輪的設定（錯題頁的「練習待複習」），不寫回 setup
export function startQuiz(ws,over){if(!ws.length)return;const c=over?{...setup,...over}:setup,n=c.n||ws.length;const all=pool(over);const items=shuffle(ws).slice(0,n);
  Q=ctx.Q={items,n0:items.length,i:0,right:0,wrong:[],reps:0,fixed:0,mode:c.mode,dict:c.dict,over:over||null,all:all.length>=4?all:ws,bank:allWords()};ctx.B=null;stopSpeech();renderQ()}

function renderQ(){const w=Q.items[Q.i],m=Q.mode,tot=Q.n0;Q.done=false;Q.checking=false;
  // 進度只算原本的題數；答錯重出的題目另外標「重考」，分母不會邊做邊變
  const prog=Q.i<tot?`${Q.i+1} / ${tot}`:`重考 ${Q.i-tot+1} / ${Q.items.length-tot}（原 ${tot} 題已答完）`;
  let prompt="",body="";
  if(m==="en2zh"||m==="en2zhT")prompt=`<div class="row" style="gap:12px;flex-wrap:nowrap"><div class="prompt en">${esc(w.en)}</div>${spkBtn(w.en)}</div><div class="small">${esc(w.pos)}</div>${exLine(w,false)}`;
  else if(m==="zh2en"||m==="zh2enT")prompt=`<div class="prompt zh">${esc(zhPrompt(w))}</div><div class="small">${esc(w.pos)}${m==="zh2enT"?`・提示：${esc(w.en.trim()[0]||"")}… 共 ${esc(String(normEn(w.en).replace(/ /g,"").length))} 個字母`:""}</div>${exLine(w,true)}`;
  else{const a=clozeAns(w),i=clozePos(w.ex,a);prompt=`<div class="cloze">${esc(w.ex.slice(0,i))}<span class="blank">　?　</span>${esc(w.ex.slice(i+a.length))}</div><p class="small">提示：${esc(zhPrompt(w))}</p>`}
  if(m==="en2zh"||m==="zh2en"||m==="cloze"){const key=m==="en2zh"?"zh":m==="zh2en"?"en":"cloze";Q.ans=key==="cloze"?clozeAns(w):w[key];Q.opts=opts(w,key,Q.bank);
    body=`<div class="opts" id="opts">${Q.opts.map((o,i)=>`<button data-o="${i}" class="${key==="zh"?"":"en"}"><span class="k">${i+1}</span>${esc(o)}</button>`).join("")}</div>`}
  else body=`<form id="tf" class="row" style="margin-top:18px"><input id="ti" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="${m==="en2zhT"?"輸入中文意思":"輸入英文"}" style="flex:1 1 220px;width:auto" class="${m==="zh2enT"?"en":""}"><button class="pri" id="tsub">送出</button><button type="button" id="idk" class="ghost">不會</button></form>`;
  app.innerHTML=`<div class="row"><button class="sm ghost" id="quit" style="padding-left:0">← 結束練習</button><span class="small" id="prog" style="margin-left:auto">${MODES.find(x=>x[0]===m)[1]}・${prog}・答對 ${Q.right}</span></div>
  <div class="bar"><i style="width:${Math.min(Q.i,tot)/tot*100}%"></i></div>
  <div class="cut qcard">${SC}<div class="tab"><span>${esc(w.unit||"WORD")}</span></div><div class="body">${w._rep?'<div class="small" style="color:var(--bad);font-weight:700;margin-bottom:6px">剛剛答錯，再考一次</div>':""}${prompt}${body}<div id="fb"></div></div></div>`;
  $("#quit").onclick=toSetup;
  if(setup.auto&&(m==="en2zh"||m==="en2zhT"))speak(w.en,app.querySelector(".spk"));
  const o=$("#opts");if(o)o.onclick=e=>{const b=e.target.closest("[data-o]");if(b&&!Q.done)answer(Q.opts[+b.dataset.o]===Q.ans,+b.dataset.o,Q.opts[+b.dataset.o])};
  const f=$("#tf");if(f){const ti=$("#ti");ti.focus();let k0=0;ti.addEventListener("input",()=>{if(!k0)k0=performance.now()});
    f.onsubmit=e=>{e.preventDefault();if(Q.done){const n=$("#nx");if(n&&!n.disabled)next();return}const v=ti.value;if(!v.trim())return;
    if(m==="zh2enT"&&k0&&checkEn(v,w))recordTyping(v.trim().length,performance.now()-k0);
    if(m==="en2zhT"){if(Q.checking)return;Q.checking=true;ti.readOnly=true;const sb=$("#tsub");if(sb)sb.textContent="判斷中…";const q=Q,wi=Q.i;
      checkZhSmart(v,w).catch(()=>({ok:false})).then(r=>{if(ctx.Q!==q||Q.i!==wi)return;Q.checking=false;answer(r.ok,-1,v,r.loose)});return}
    answer(checkEn(v,w),-1,v)};$("#idk").onclick=()=>{if(!Q.done&&!Q.checking)answer(false,-1,"")}}}

function answer(ok,idx,typed,loose){if(Q.done)return;Q.done=true;const w=Q.items[Q.i],m=Q.mode;
  // 成績只算第一次作答；答錯的加到本輪最後再考，每字最多重出 3 次
  Q.pushed=false;if(w._rep){if(ok)Q.fixed++}else if(ok)Q.right++;else Q.wrong.push(w);
  if(!ok&&(w._rep||0)<3){Q.items.push({...w,_rep:(w._rep||0)+1});Q.reps++;Q.pushed=true}mark(w,ok,typed,Q.mode);
  const ob=app.querySelectorAll("#opts button");ob.forEach((b,i)=>{b.disabled=true;if(Q.opts[i]===Q.ans)b.classList.add("right");else if(i===idx)b.classList.add("wrong")});
  const ti=$("#ti");if(ti)ti.readOnly=true;
  // 作答後：送出鈕恢復文字並停用（不會一直停在「判斷中…」），「不會」也停用
  const sb=$("#tsub");if(sb){sb.textContent="送出";sb.disabled=true}const ik=$("#idk");if(ik)ik.disabled=true;
  const typedMode=m==="en2zhT"||m==="zh2enT";
  $("#fb").innerHTML=`<div class="fb ${ok?"ok":"no"}"><b class="t">${ok?"答對了！":"答錯了"}${ok&&loose?`<span class="small" style="font-weight:500">（${esc(loose)}，算對）</span>`:""}</b>
   <div style="margin-top:6px"><span class="w">${esc(w.en)}</span><span class="pos">${esc(w.pos)}</span> ${spkBtn(w.en)}</div><div>${esc(w.zh)}</div>
   ${w.ex?`<div class="row" style="gap:8px;flex-wrap:nowrap;margin-top:6px"><div class="ex en">${esc(w.ex)}</div>${spkBtn(w.ex,"朗讀例句")}</div>`:""}
   ${!ok&&typed&&idx<0?`<p class="small" style="margin:8px 0 0">你的答案：${esc(typed)}</p>`:""}</div>
   <div class="row" style="margin-top:12px"><button class="pri" id="nx" style="flex:1 1 200px">${Q.i+1<Q.items.length?(Q.i+1<Q.n0?"下一題":"下一題・重考"):"看結果"}${KEY_HINT}</button>${!ok&&typedMode&&typed?'<button id="ovr" class="ghost">我其實答對了</button>':""}</div>`;
  $("#nx").onclick=next;$("#nx").focus();const ov=$("#ovr");if(ov)ov.onclick=()=>{if(Q.pushed){Q.items.pop();Q.reps--}if(w._rep)Q.fixed++;else{Q.right++;Q.wrong.pop()}unlog(w);mark(w,true,"",Q.mode);next()};
  Q.readP=readAll(w,app.querySelector("#fb .spk"));gate($("#nx"),Q.readP,"朗讀中…（英文→中文→例句）")}
// 換題前先停掉上一題還沒唸完的朗讀（25 秒強制解鎖後也一樣）
function next(){stopSpeech();Q.i++;if(Q.i<Q.items.length)renderQ();else renderEnd()}

function renderEnd(){const t=Q.items.length-Q.reps,p=Math.round(Q.right/t*100);
  if(!Q.logged){Q.logged=true;pushHist({t:Date.now(),mode:Q.mode,dict:Q.dict,n:t,right:Q.right,wrong:Q.wrong.map(w=>[w.dict||Q.dict,w.id]),game:false})}
  app.innerHTML=`<div class="cut qcard">${SC}<div class="tab"><span>RESULT</span></div><div class="body" style="text-align:center"><div class="big">${p}%</div><p style="font-size:18px">第一次就答對 ${Q.right} / ${t} 題</p>${Q.reps?`<p class="small">錯的題目重出了 ${Q.reps} 次，重出時答對 ${Q.fixed} 次</p>`:""}
  <div class="row" style="justify-content:center">${Q.wrong.length?'<button class="pri" id="rw">重練這次錯的</button>':""}<button id="again">再來一輪</button><button id="chg">換題型</button></div></div></div>
  ${Q.wrong.length?`<h2>這次答錯的（${Q.wrong.length}）</h2><div class="cut">${SC}<div class="tab"><span>REVIEW</span></div><div class="body list">${Q.wrong.map(w=>wordRow(w,true)).join("")}</div></div>`:""}`;
  const over=Q.over;const rw=$("#rw");if(rw)rw.onclick=()=>{const ws=Q.wrong;startQuiz(ws,over?{...over,n:0}:{n:0})};
  $("#again").onclick=()=>{const p=pool(over);if(p.length)startQuiz(p,over);else{toast(over&&over.wrong||setup.wrong?"待複習的題目都練完了！":"這個範圍沒有題目可出");toSetup()}};$("#chg").onclick=toSetup}

// 鍵盤：選擇題 1–4 選答案；作答後 Enter＝下一題（選擇題與填空題都一樣，焦點在哪裡都接得到）
document.addEventListener("keydown",e=>{if(!ctx.Q||ctx.view!=="practice"||e.isComposing||e.ctrlKey||e.metaKey||e.altKey)return;
  if(/^[1-4]$/.test(e.key)&&!Q.done&&$("#opts")){const b=app.querySelector(`[data-o="${+e.key-1}"]`);if(b)b.click()}
  else if(e.key==="Enter"&&Q.done){const n=$("#nx");if(!n)return;const t=e.target,tag=t&&t.tagName;
    // 焦點在別的按鈕／連結上（例如「我其實答對了」、喇叭）就照那個按鈕的原本行為
    if((tag==="BUTTON"||tag==="A"||tag==="SELECT")&&t!==n)return;
    e.preventDefault();if(!n.disabled&&!e.repeat)n.click()}});
