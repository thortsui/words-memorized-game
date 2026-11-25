// 英文詞表拼字檢查。詞表：public/wordlist/en-words.txt（SCOWL，約 8 萬字，含詞形變化）＋ en-names.txt（專有名詞約 1.7 萬），用到才載入。
// 純邏輯（makeLexicon／unknownWords）可在 Node 測試；loadLexicon 只在瀏覽器用。
import { cachedText } from './cache.js';
const CONTR=new Set("don't doesn't didn't can't couldn't won't wouldn't shouldn't isn't aren't wasn't weren't hasn't haven't hadn't mustn't needn't shan't mightn't ain't i'm i've i'll i'd you're you've you'll you'd he's he'll he'd she's she'll she'd it's it'll we're we've we'll we'd they're they've they'll they'd that's there's here's what's who's where's when's how's let's o'clock".split(" "));
// 單字書裡的文法記號與縮寫，不算拼錯
const MARK=new Set("sb sth n v o s adj adv p pp ing wh vs etc mr mrs ms dr tv ok pm am st nd rd th".split(" "));

// text：一行一個字的詞表；names：一行一個的專有名詞表（人名、地名，小寫）。回傳 Set，另外帶 .names
export function makeLexicon(text,names=""){const rd=t=>{const set=new Set();for(const w of String(t).split(/\r?\n/)){const x=w.trim().toLowerCase();if(x)set.add(x)}return set},lex=rd(text);lex.names=rd(names);return lex}
const plain=s=>s.normalize("NFD").replace(/[\u0300-\u036f]/g,"");   // café → cafe

function known(tok,lex){const w=plain(tok).toLowerCase().replace(/^'+|'+$/g,"");if(!w||w.length<2||MARK.has(w)||CONTR.has(w)||lex.has(w))return true;
  if(/'s$|s'$/.test(w)&&lex.has(w.replace(/'s$|'$/,"")))return true;          // 所有格
  if(/'(ll|ve|re|d)$/.test(w)&&lex.has(w.replace(/'(ll|ve|re|d)$/,"")))return true;
  if(w.includes("-")){const p=w.split("-").filter(Boolean);return p.length>1&&p.every(x=>x.length<2||MARK.has(x)||lex.has(x))}
  return false}

// 回傳文字裡查不到的字（去重複、照出現順序）。
// 大寫開頭的字先查專有名詞表（Mary、Taiwan）。sentence=true（例句）時，句子中間大寫開頭又都查不到的字
// 當作沒收錄的專有名詞略過；句首的字一定要查得到（句首本來就大寫，分不出是不是專有名詞）。
export function unknownWords(text,lex,{sentence=false}={}){const out=[],seen=new Set(),s=String(text||"").replace(/[’‘`]/g,"'"),re=/[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'\-]*/g;let m,first=true,prevEnd=0;
  while((m=re.exec(s))){const tok=m[0].replace(/-+$/,""),gap=s.slice(prevEnd,m.index),start=first||/[.?!]["')]*\s*["'(]*$/.test(gap);first=false;prevEnd=m.index+m[0].length;
    if(known(tok,lex))continue;
    if(/^[A-Z]/.test(tok)){const n=plain(tok).toLowerCase().replace(/'s$|'$/,"");if(lex.names&&lex.names.has(n))continue;if(sentence&&!start)continue}
    const k=tok.toLowerCase();if(!seen.has(k)){seen.add(k);out.push(tok)}}
  return out}

let lexP=null;
export function loadLexicon(){if(!lexP){const b=(import.meta.env&&import.meta.env.BASE_URL)||"./";
    const get=f=>cachedText(new URL(b+"wordlist/"+f,location.href).href);   // 也存進 Cache Storage，離線可用
    lexP=Promise.all([get("en-words.txt"),get("en-names.txt")]).then(([w,n])=>makeLexicon(w,n)).then(l=>{if(l.size<10000)throw new Error("詞表不完整");return l}).catch(e=>{lexP=null;throw e})}
  return lexP}
