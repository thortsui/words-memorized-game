// 中翻英・填空的作答時限：依玩家的平均英文打字速度換算。
//   時限＝思考 2 秒＋答案字數 ÷（平均打字速度 − 5 WPM）。減 5 是讓時間寬一點；WPM 以「5 個字元＝1 個字」計。
//   平均打字速度：每次中翻英・填空答對時，量「第一次按鍵 → 送出」的速度，指數平均後存在這台裝置（vc-typing）。
//   還沒量過時用 35 WPM（國高中生英文打字的一般速度），所以一開始是 30 WPM 換算。
const KEY="vc-typing",DEF=35,THINK=2000,SLACK=5,MIN=8;
const ls=()=>{try{return globalThis.localStorage||null}catch(e){return null}};
export function typingWpm(){try{const s=ls(),v=s&&JSON.parse(s.getItem(KEY)||"null");if(v&&v.wpm>0)return v.wpm}catch(e){}return DEF}
export function typingInfo(){try{const s=ls(),v=s&&JSON.parse(s.getItem(KEY)||"null");if(v&&v.wpm>0)return{wpm:v.wpm,n:v.n||0,measured:true}}catch(e){}return{wpm:DEF,n:0,measured:false}}
// 記一次答對的打字：chars 個字元花了 ms 毫秒（不含思考：從第一次按鍵算起）
export function recordTyping(chars,ms){if(!(chars>=3&&ms>=250))return;const w=Math.max(MIN,Math.min(150,chars/5/(ms/60000)));
  const cur=typingInfo(),n=Math.min(20,cur.n+1),wpm=cur.measured?cur.wpm+(w-cur.wpm)/n:w;
  try{const s=ls();s&&s.setItem(KEY,JSON.stringify({wpm:Math.round(wpm*10)/10,n}))}catch(e){}}
// 打出 text 需要的時限（毫秒）：思考 2 秒＋打字時間（以平均速度 − 5 WPM 換算），取整到 0.1 秒
export function typeLimitMs(text,wpm=typingWpm()){const chars=[...String(text||"").trim()].length,r=Math.max(MIN,wpm-SLACK);
  return Math.round((THINK+chars*12000/r)/100)*100}
export const TYPE_THINK_MS=THINK;
