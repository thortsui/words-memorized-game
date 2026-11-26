// 出題與判分（純函式，不碰 DOM；可在 Node 直接測試）
export const shuffle=a=>{a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
export const isPhrase=w=>/片語|phr/i.test(w.pos)||/\s/.test(w.en.trim());
export const MODES=[["en2zh","英翻中・選擇"],["zh2en","中翻英・選擇"],["en2zhT","英翻中・填空"],["zh2enT","中翻英・填空"],["cloze","克漏字"]];
export const modeName=m=>m==="mix"?"綜合題型":(MODES.find(x=>x[0]===m)||[0,""])[1];
// 綜合題型：練習設定可以複選題型（modes），選兩種以上時 mode＝"mix"，每一題從選到的題型裡隨機抽一種；
// 克漏字只出給有例句、挖得出答案的字，挖不出來就從其他選到的題型抽
export const MODE_IDS=["en2zh","zh2en","en2zhT","zh2enT","cloze"];
export const canMode=(w,m)=>m!=="cloze"||!!(w&&w.ex&&clozeAns(w));
export function pickMode(mode,modes,w,rng=Math.random){if(mode!=="mix")return mode;const ok=(modes&&modes.length?modes:MODE_IDS).filter(m=>canMode(w,m));
  if(!ok.length)return(modes||[]).find(m=>m!=="cloze")||"en2zh";return ok[Math.floor(rng()*ok.length)%ok.length]}
// 填空題型對應的選擇題型（魂系閃避題一律選擇題）
export const mcOf=m=>m==="en2zhT"?"en2zh":m==="zh2enT"?"zh2en":m;

// 朗讀前清理英文
export const sayable=t=>String(t).replace(/\(s\)/g,"s").replace(/\bsb\b/g,"somebody").replace(/\bsth\b/g,"something").replace(/one's/g,"one's").replace(/\b(N\.|V-ing|V\.|O\.|S\.|Adj\.|p\.p\.)|wh-疑問詞|[+/()]|\.\.\.|…/g," ").replace(/\s+/g," ").trim();
export const zhSay=t=>String(t).replace(/（[^）]*）|\([^)]*\)/g,"").replace(/……|…/g,"").replace(/sb|sth/g,"").trim();

// 常見不規則變化（動詞過去式／過去分詞／第三人稱、名詞複數、形容詞比較級）
const IRREG={};
("be:am,is,are,was,were,been,being|have:has,had,having|do:does,did,done|go:goes,went,gone|say:said|get:got,gotten|make:made|know:knew,known|think:thought|take:took,taken|see:saw,seen|come:came|give:gave,given|find:found|tell:told|"+
"become:became|leave:left|feel:felt|bring:brought|begin:began,begun|keep:kept|hold:held|write:wrote,written|stand:stood|hear:heard|let:let|mean:meant|set:set|meet:met|run:ran|pay:paid|sit:sat|speak:spoke,spoken|lie:lay,lain|lead:led|"+
"read:read|grow:grew,grown|lose:lost|fall:fell,fallen|send:sent|build:built|understand:understood|draw:drew,drawn|break:broke,broken|spend:spent|cut:cut|rise:rose,risen|drive:drove,driven|buy:bought|wear:wore,worn|choose:chose,chosen|"+
"seek:sought|throw:threw,thrown|catch:caught|deal:dealt|win:won|forget:forgot,forgotten|lay:laid|sell:sold|fight:fought|bear:bore,born,borne|teach:taught|eat:ate,eaten|sing:sang,sung|strike:struck,stricken|hang:hung|shake:shook,shaken|"+
"ride:rode,ridden|feed:fed|shoot:shot|drink:drank,drunk|hit:hit|arise:arose,arisen|fly:flew,flown|sleep:slept|steal:stole,stolen|swim:swam,swum|wake:woke,woken|hide:hid,hidden|blow:blew,blown|bite:bit,bitten|bend:bent|bind:bound|"+
"bleed:bled|breed:bred|burn:burnt|cost:cost|creep:crept|dig:dug|dream:dreamt|flee:fled|forbid:forbade,forbidden|forgive:forgave,forgiven|freeze:froze,frozen|hurt:hurt|kneel:knelt|lean:leant|leap:leapt|learn:learnt|lend:lent|light:lit|"+
"overcome:overcame|put:put|quit:quit|ring:rang,rung|shine:shone|shut:shut|sink:sank,sunk|slide:slid|smell:smelt|spell:spelt|spill:spilt|spin:spun|split:split|spread:spread|spring:sprang,sprung|stick:stuck|sting:stung|swear:swore,sworn|"+
"sweep:swept|swing:swung|tear:tore,torn|weep:wept|wind:wound|withdraw:withdrew,withdrawn|undo:undid,undone|undergo:underwent,undergone|mistake:mistook,mistaken|shrink:shrank,shrunk|sew:sewn|show:shown|sow:sown|prove:proven|"+
"man:men|woman:women|child:children|person:people|foot:feet|tooth:teeth|mouse:mice|goose:geese|ox:oxen|crisis:crises|analysis:analyses|basis:bases|phenomenon:phenomena|criterion:criteria|medium:media|datum:data|cactus:cacti|"+
"good:better,best|well:better,best|bad:worse,worst|far:farther,farthest,further,furthest|little:less,least|many:more,most|much:more,most")
  .split("|").forEach(x=>{const [b,f]=x.split(":");IRREG[b]=f.split(",")});
// 一個字「文法上的變化形」：複數／第三人稱、過去式、分詞、-ing；形容詞與副詞才加比較級 -er／-est。
// 不含 -er／-or／-ist／-ly／-ment 這類衍生出來的另一個字（paint→painter、teach→teacher 不算）。
export function inflections(en,pos){const a=String(en).toLowerCase().replace(/[^a-z]/g,""),F=new Set();if(!a)return F;F.add(a);
  const L=a.slice(-1),cons=/[^aeiou]$/.test(a),dbl=cons&&!/[wxy]$/.test(a)?a+L:"";
  ["s","es","ed","d","ing"].forEach(x=>F.add(a+x));
  if(a.endsWith("e"))F.add(a.slice(0,-1)+"ing");                                     // make → making
  if(a.endsWith("ie"))F.add(a.slice(0,-2)+"ying");                                   // die → dying
  if(/[^aeiou]y$/.test(a)){F.add(a.slice(0,-1)+"ies");F.add(a.slice(0,-1)+"ied")}   // study → studies／studied
  if(dbl){F.add(dbl+"ed");F.add(dbl+"ing")}                                          // stop → stopped／stopping
  if(a.endsWith("c")){F.add(a+"ked");F.add(a+"king")}                                // panic → panicked
  if(a.endsWith("fe"))F.add(a.slice(0,-2)+"ves");else if(a.endsWith("f"))F.add(a.slice(0,-1)+"ves"); // knife → knives
  if(/adj|adv|形|副/i.test(pos||"")){["er","est","r","st"].forEach(x=>F.add(a+x));if(a.endsWith("y")){F.add(a.slice(0,-1)+"ier");F.add(a.slice(0,-1)+"iest")}if(dbl){F.add(dbl+"er");F.add(dbl+"est")}}
  (IRREG[a]||[]).forEach(x=>F.add(x));return F}
const WORD_RE=/[A-Za-z]+(?:[’'-][A-Za-z]+)*/g;
// 克漏字答案：使用者（或掃描）填的 blank 優先；否則在例句裡找這個字真正的詞形變化。找不到就回空字串（這題不出克漏字）。
export function clozeAns(w){const ex=String(w.ex||"");if(w.blank&&ex.toLowerCase().includes(w.blank.toLowerCase()))return w.blank;if(isPhrase(w))return"";
  const F=inflections(w.en,w.pos);if(!F.size)return"";
  for(const t of ex.match(WORD_RE)||[]){const k=t.replace(/[’']s$/i,"");if(!/[’']/.test(k)&&F.has(k.toLowerCase().replace(/[^a-z]/g,"")))return k}
  return""}
// 答案在例句裡的位置：整個字比對，不會挖到別的字裡面（paint 不會挖到 painter 的前五個字母）。回傳 -1＝找不到
export function clozePos(ex,a){if(!a)return-1;const lo=String(ex).toLowerCase(),al=a.toLowerCase(),L=/[a-z]/i;let i=-1;
  while((i=lo.indexOf(al,i+1))>=0){if(!(i>0&&L.test(lo[i-1])&&L.test(al[0]))&&!(L.test(lo[i+al.length]||"")&&L.test(al[al.length-1])))return i}
  return lo.indexOf(al)}
// 中翻英／克漏字的題目要顯示的中文：把會洩題的英文遮掉（括號裡含答案的整段用法說明拿掉，其餘與答案相同的英文字改成底線）。
// 字典頁與作答後的解說仍顯示完整的 w.zh。
export function zhPrompt(w){const keys=new Set();normEn(w.en).split(" ").concat(normEn(clozeAns(w)).split(" ")).forEach(x=>{if(x.length>=2)inflections(x,"adj").forEach(y=>keys.add(y))});
  const leak=t=>keys.has(t.toLowerCase().replace(/[^a-z]/g,"")),has=m=>(m.match(WORD_RE)||[]).some(leak);
  const z=String(w.zh||"").replace(/（[^（）]*）|\([^()]*\)/g,m=>has(m)?"":m).replace(WORD_RE,t=>leak(t)?"＿＿":t).replace(/\s+/g," ").trim();
  return z||String(w.zh||"")}

// 詞形分類（克漏字選項用）：base 原形、s 複數／第三人稱、ed 過去式／分詞、ing、er 比較級／最高級、other
export function formOf(form,en,pos){const f=String(form).toLowerCase().replace(/[^a-z ]/g,"").trim(),b=String(en).toLowerCase().replace(/[^a-z ]/g,"").trim();
  if(!f||f===b)return"base";if(/\s/.test(f))return"other";
  if(/ing$/.test(f))return"ing";if(/ed$/.test(f))return"ed";
  if((IRREG[b]||[]).includes(f)){if(/adj|adv|形|副/i.test(pos||""))return"er";if(/^n|名/i.test(pos||""))return"s";return/s$/.test(f)?"s":"ed"} // went／taught／children／better
  if(/(er|est)$/.test(f)&&/adj|adv|形|副/i.test(pos||""))return"er";
  if(/s$/.test(f))return"s";
  // 認不出來的不規則變化（misunderstood、mice…）：動詞當過去式、名詞當複數
  if(/^v|動/i.test(pos||""))return"ed";if(/^n|名/i.test(pos||""))return"s";return"other"}
// 把原形變成指定詞形（只做規則變化；不規則字、要重複字尾子音的短字回傳空字串＝不用它）
export function inflectAs(en,form){const b=String(en).trim().toLowerCase();if(!/^[a-z]{3,}$/.test(b)||IRREG[b]||/(ye|oe|ee)$/.test(b)||Object.keys(IRREG).some(k=>k.length>=3&&b.endsWith(k)))return""; // 含不規則字根的（misunderstand）也不變
  const cvc=/[^aeiou][aeiou][^aeiouwxy]$/.test(b);
  if(form==="s")return/[^s]s$/.test(b)?"":/(s|x|z|ch|sh)$/.test(b)?b+"es":/[^aeiou]y$/.test(b)?b.slice(0,-1)+"ies":/(f|fe|o)$/.test(b)?"":b+"s";
  if(form==="ed")return/e$/.test(b)?b+"d":/[^aeiou]y$/.test(b)?b.slice(0,-1)+"ied":cvc||/c$/.test(b)?"":b+"ed";
  if(form==="ing")return/ie$/.test(b)?"":/[^e]e$/.test(b)?b.slice(0,-1)+"ing":cvc||/c$/.test(b)?"":b+"ing";
  return""}
const posSet=p=>String(p||"").toLowerCase().split(/[\/、,\s]+/).filter(Boolean);
const samePos=(a,b)=>{const B=posSet(b);return posSet(a).some(x=>B.includes(x))}; // 「v./n.」和「v.」算同詞性
// 大小寫跟著正解：正解字首大寫（句首）→ 干擾項字首也大寫；正解小寫（句中）→ 干擾項字首小寫。全大寫的縮寫（TV）與 I 不動。
export function matchCase(v,ans){v=String(v);const a=String(ans).match(/[A-Za-z]/);if(!a||!v)return v;if(/^[A-Z]{2,}\b/.test(v)||/^I\b/.test(v))return v;
  const up=a[0]===a[0].toUpperCase();return v.replace(/[A-Za-z]/,c=>up?c.toUpperCase():c.toLowerCase())}
// 干擾選項：先限同為單字或片語；同詞性夠 3 個就只用同詞性。
// 克漏字另外要求：大小寫與正解一致（不能靠句首大寫認出答案）、盡量挑同詞形的字（正解是 -ed 就都給 -ed、正解是複數就都給複數）。
export function opts(w,key,bank){const ph=isPhrase(w),cz=key==="cloze",val=x=>cz?clozeAns(x):x[key],ans=val(w),al=ans.toLowerCase();
  if(cz){const form=formOf(ans,w.en,w.pos),lc=s=>String(s||"").trim().toLowerCase();
    // 候選：別的字在它自己例句裡的詞形；正解是原形時，沒有例句的單字也能直接拿原形來用
    const cand=[],made=[];for(const x of bank){if(x.id===w.id)continue;const v=clozeAns(x);if(v)cand.push({v,f:formOf(v,x.en,x.pos),pos:x.pos,ph:isPhrase(x)});
      // 同詞形的字不夠時的備案：拿同詞性的字照規則變成同一種詞形（overlooking 的干擾項用 abandoning、carving…）
      if(!ph&&!isPhrase(x)&&samePos(x.pos,w.pos)&&(form==="s"||form==="ed"||form==="ing")){const m=inflectAs(x.en,form);if(m)made.push({v:m,f:form,pos:x.pos,ph:false})}
      if(form==="base"&&!isPhrase(x)&&/^[A-Za-z]+$/.test(String(x.en).trim())&&lc(v)!==lc(x.en))cand.push({v:String(x.en).trim(),f:"base",pos:x.pos,ph:false})}
    const ok=cand.filter(c=>lc(c.v)!==al),sameKind=ok.filter(c=>ph?c.ph:(!c.ph&&!/\s/.test(c.v)));
    const tail=s=>/[^s]s$/i.test(s),at=tail(ans),fit=c=>c.f===form&&tail(c.v)===at; // 字尾有沒有 s 也要一致（goods 不混進單數名詞裡）
    // 由嚴到寬：同詞性＋同詞形 → 同詞形 → 同詞性 → 同為單字／片語 → 全部
    const tiers=[sameKind.filter(c=>fit(c)&&samePos(c.pos,w.pos)),sameKind.filter(fit),made.filter(c=>lc(c.v)!==al&&tail(c.v)===at),sameKind.filter(c=>c.f===form),sameKind.filter(c=>samePos(c.pos,w.pos)),sameKind,ok];
    const pick=[],seen=new Set([al]);
    for(const tr of tiers){for(const c of shuffle(tr)){const v=matchCase(c.v,ans),k=v.toLowerCase();if(seen.has(k))continue;seen.add(k);pick.push(v);if(pick.length===3)break}if(pick.length===3)break}
    return shuffle([ans,...pick])}
  let c=bank.filter(x=>x.id!==w.id&&val(x)&&val(x).toLowerCase()!==al&&isPhrase(x)===ph);
  const sp=c.filter(x=>x.pos===w.pos);if(sp.length>=3)c=sp;if(c.length<3)c=bank.filter(x=>x.id!==w.id&&val(x)&&val(x).toLowerCase()!==al);
  const pick=[],seen=new Set([al]);for(const x of shuffle(c)){const v=val(x);if(seen.has(v.toLowerCase()))continue;seen.add(v.toLowerCase());pick.push(v);if(pick.length===3)break}
  return shuffle([ans,...pick])}

// (s) 這種可有可無的複數直接拿掉；sb／sth／somebody／someone／something 這些受詞標記寫不寫都一樣
export const normEn=s=>String(s).toLowerCase().replace(/[’]/g,"'").replace(/\(s\)/g,"").replace(/\b(sb|sth|somebody|someone|something|n\.|v-ing|v\.|o\.|s\.|adj\.|p\.p\.)(?=\s|$|[/)+])/g," ").replace(/wh-疑問詞|[+()…]|\.\.\./g," ").replace(/[^a-z' ]/g," ").replace(/\s+/g," ").trim();
// 可接受的寫法：door(s) → door／doors；(for sb) 這種括號整段可省略；see/regard 任選一個；整個標題照抄（斜線當空白）也算
export function enVariants(en){en=String(en);let base=[en];
  for(let g=0;g<4;g++){const nx=[];let hit=false;for(const b of base){const m=b.match(/\(([^()]*)\)/);if(!m){nx.push(b);continue}hit=true;const pre=b.slice(0,m.index),post=b.slice(m.index+m[0].length);
      nx.push(pre+" "+post);nx.push(/[a-z]$/i.test(pre)&&/^[a-z]{1,2}$/i.test(m[1])?pre+m[1]+post:pre+" "+m[1]+" "+post)}base=nx;if(!hit)break}
  const out=new Set([normEn(en)]);
  for(const b of base){let v=[""];b.split(/\s+/).forEach(tok=>{const alts=/^[a-z]+(\/[a-z]+)+$/i.test(tok)?tok.split("/"):[tok];v=v.flatMap(p=>alts.map(a=>p+" "+a))});v.forEach(x=>out.add(normEn(x)));out.add(normEn(b))}
  out.delete("");return[...out]}
export const checkEn=(inp,w)=>enVariants(w.en).includes(normEn(inp));
export const zhSegs=zh=>zh.replace(/（[^）]*）|\([^)]*\)/g,"").split(/[、；;，,]/).map(s=>s.replace(/[…\.。\s]|等$/g,"")).filter(Boolean);
const ZSTOP="的了是在把被與和或及某人事物一個種使得地之者等再……";
export const zc=s=>[...String(s).replace(/（[^）]*）|\([^)]*\)/g,"")].filter(c=>/[㐀-鿿]/.test(c)&&!ZSTOP.includes(c));
const zlen=s=>[...s].length;
// 互相包含：只有一個字的輸入不算；短的那邊至少要佔長的那邊一半（「放」不能靠「放開」過關，「外貌」對「外貌特徵」可以）
const zhContain=(t,s)=>{const a=zlen(t),b=zlen(s);if(a<2||!b)return false;return(s.includes(t)&&a*2>=b)||(t.includes(s)&&b*2>=a)};
// 意思相近：完全相同，或（輸入至少兩個字）互相包含／共同字佔輸入與該義項各一半以上
export function nearZh(t,terms){t=String(t);const tc=zc(t);if(!tc.length)return false;return terms.some(s=>{s=String(s).replace(/[\s…\.。]/g,"");if(!s)return false;if(s===t)return true;if(zlen(t)<2||tc.length<2)return false;
  if(zhContain(t,s)&&zc(s).length)return true;const sc=zc(s),ss=new Set(sc),hit=tc.filter(c=>ss.has(c)).length;return hit>=1&&hit*2>=tc.length&&hit*2>=sc.length})}
export function checkZh(inp,zh){const t=inp.replace(/[\s…\.。]/g,"");if(!t)return false;return zhSegs(zh).some(s=>s===t||zhContain(t,s))}

// Google 翻譯（非官方端點）
const GC={};
export async function gtrans(t,sl,tl){sl=sl||"en";tl=tl||"zh-TW";const key=sl+tl+t;if(GC[key])return GC[key];const r=await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl="+sl+"&tl="+tl+"&dt=t&dt=bd&q="+encodeURIComponent(t));if(!r.ok)throw new Error("HTTP "+r.status);
  const j=await r.json(),main=(j[0]||[]).map(x=>x&&x[0]||"").join(""),dict=[];(j[1]||[]).forEach(e=>(e&&e[1]||[]).forEach(x=>dict.push(x)));return GC[key]={main,dict}}
const tmo=(p,ms)=>Promise.race([p,new Promise((_,no)=>setTimeout(()=>no(new Error("timeout")),ms))]);
// 中文填空：只認書上（掃描圖片上）給的中文——完全符合某個義項，或和某個義項共同字過半。
// 不再用 Google 翻譯放寬：翻譯上說得通、但書上沒有的意思不算對（使用者要求，2026-11-26）
export async function checkZhSmart(inp,w){const t=inp.replace(/[\s…\.。，,]/g,"");if(!t)return{ok:false};if(checkZh(t,w.zh))return{ok:true};
  if(nearZh(t,zhSegs(w.zh)))return{ok:true,loose:"和書上的意思相近"};
  return{ok:false}}

// 掃描核對用
const STOP=new Set("的了是在把被與和或及某人事物一個種使得到地之者等再".split(""));
export const cjk=s=>[...String(s).replace(/（[^）]*）|\([^)]*\)/g,"")].filter(c=>/[㐀-鿿]/.test(c)&&!STOP.has(c));
