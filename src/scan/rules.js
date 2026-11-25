// 條目的規則檢查（純函式，不連網；Google 翻譯核對另外在上傳頁做）。回傳警告文字陣列，空陣列＝通過。
import { isPhrase, clozeAns } from '../core/grading.js';
import { unknownWords } from './wordlist.js';

// 例句裡的字形是不是英文的規則變化（dye→dyed、recycle→recycles、stop→stopped、study→studies…）
export function isInflection(en,form){const a=en.toLowerCase().replace(/[^a-z]/g,""),f=form.toLowerCase().replace(/[^a-z]/g,"");if(!a||!f)return false;if(a===f)return true;
  const suf=["s","es","d","ed","ing","er","est","ly","r","st","n","en"],c=[a];
  if(a.endsWith("e"))c.push(a.slice(0,-1));                                  // make → making
  if(a.endsWith("y"))c.push(a.slice(0,-1)+"i");                              // study → studies、happy → happily
  if(a.endsWith("ie"))c.push(a.slice(0,-2)+"y");                             // die → dying
  if(/[^aeiou][aeiou][^aeiouwxy]$/.test(a)||/[aeiou][^aeiou]$/.test(a))c.push(a+a.slice(-1)); // stop → stopped
  if(a.endsWith("f"))c.push(a.slice(0,-1)+"v");if(a.endsWith("fe"))c.push(a.slice(0,-2)+"v");  // leaf → leaves
  if(a.endsWith("c"))c.push(a+"k");                                          // panic → panicked
  if(c.some(b=>suf.some(x=>b+x===f)))return true;
  // 不規則變化（understand → understood）：開頭至少七成相同、長度差不多，也算
  let p=0;while(p<a.length&&p<f.length&&a[p]===f[p])p++;return p>=4&&p>=a.length*.7&&Math.abs(a.length-f.length)<=2}

// lex：英文詞表（Set）；傳 null 表示詞表沒載到，會多一條警告（拼字沒檢查就不能算通過）
// opt.manual：使用者自己打的條目，不檢查「沒有詞性」
export function ruleWarnings(w,lex,opt={}){const warn=[],en=String(w.en||""),ex=String(w.ex||""),blank=String(w.blank||"");
  if(w.unsure)warn.push("提取時標示這筆有看不清楚的字，請對照原圖");
  if(!en)warn.push("英文是空的");if(!w.zh)warn.push("中文是空的");
  if(en&&!isPhrase(w)&&ex&&!clozeAns({...w,blank:""})&&!(blank&&ex.toLowerCase().includes(blank.toLowerCase())))warn.push("例句裡找不到這個字，英文或例句可能辨識錯");
  if(blank&&ex&&!ex.toLowerCase().includes(blank.toLowerCase()))warn.push("克漏字答案不在例句裡");
  // 兩個引擎可能犯同一種錯（例如都把片語 pick up 黏成 pickup）：例句裡的字形要像是這個字的變化形，單字也要有詞性
  if(en&&!isPhrase(w)&&ex){const f=blank&&ex.toLowerCase().includes(blank.toLowerCase())?blank:clozeAns({...w,blank:""});
    if(f&&!/\s/.test(f.trim())&&!isInflection(en,f))warn.push(`例句裡是「${f}」，不像「${en}」的規則變化（不規則變化請自行確認；也可能是片語少了空格）`)}
  if(en&&!opt.manual&&!String(w.pos||"").trim()&&!/\s/.test(en.trim()))warn.push("單字沒有讀到詞性（如果是片語，英文可能少了空格）");
  if(ex&&/[㐀-鿿]/.test(ex))warn.push("例句裡混到中文");
  if(en&&!/^[A-Za-z][A-Za-z'’.\/\-+ ()…,]*$/.test(en.replace(/wh-疑問詞/g,"").replace(/^(?:\.\.\.|…)[, ]*/,"")))warn.push("英文含有奇怪的字元");
  if(w.pos&&!/^(片語|phr\.?|(?:(?:n|v|vt|vi|adj|adv|prep|conj|pron|int|interj|aux|art|det|num|abbr)\.(?:\[[A-Za-z]{1,2}\])?)(?:\s*[,\/&;]\s*(?:n|v|vt|vi|adj|adv|prep|conj|pron|int|interj|aux|art|det|num|abbr)\.(?:\[[A-Za-z]{1,2}\])?)*)$/.test(String(w.pos).trim()))warn.push("詞性的寫法不常見，請確認");
  if(!lex)warn.push("英文詞表沒有載入，拼字沒有檢查");
  else{const a=unknownWords(en.replace(/wh-疑問詞/g,""),lex);if(a.length)warn.push(`英文「${a.join("、")}」不在英文詞表裡，可能拼錯`);
    const b=unknownWords(ex,lex,{sentence:true}).filter(x=>!a.some(y=>y.toLowerCase()===x.toLowerCase()));if(b.length)warn.push(`例句裡的「${b.join("、")}」不在英文詞表裡，可能拼錯`)}
  return warn}
