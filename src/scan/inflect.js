// 例句裡的字形是不是英文單字的規則變化（dye→dyed、recycle→recycles、stop→stopped、study→studies…）。純函式。
// 刻意不收 -er／-or：painter、teacher、driver 是另一個字，不是 paint、teach、drive 的變化形。
// 常見的不規則動詞（原形 → 過去式／過去分詞），單字書例句最常出現的那些
const IRR={};"be:am,is,are,was,were,been|begin:began,begun|break:broke,broken|bring:brought|build:built|buy:bought|catch:caught|choose:chose,chosen|come:came|do:did,done,does|draw:drew,drawn|drink:drank,drunk|drive:drove,driven|eat:ate,eaten|fall:fell,fallen|feel:felt|fight:fought|find:found|fly:flew,flown|forget:forgot,forgotten|get:got,gotten|give:gave,given|go:went,gone,goes|grow:grew,grown|have:had,has|hear:heard|hide:hid,hidden|hold:held|keep:kept|know:knew,known|lead:led|leave:left|lend:lent|lie:lay,lain,lying|lose:lost|make:made|mean:meant|meet:met|pay:paid|ride:rode,ridden|ring:rang,rung|rise:rose,risen|run:ran|say:said|see:saw,seen|sell:sold|send:sent|shake:shook,shaken|shine:shone|shoot:shot|sing:sang,sung|sit:sat|sleep:slept|speak:spoke,spoken|spend:spent|stand:stood|steal:stole,stolen|swim:swam,swum|take:took,taken|teach:taught|tear:tore,torn|tell:told|think:thought|throw:threw,thrown|understand:understood|wake:woke,woken|wear:wore,worn|win:won|write:wrote,written".split("|").forEach(x=>{const [b,v]=x.split(":");IRR[b]=v.split(",")});
export function isInflection(en,form){const a=String(en).toLowerCase().replace(/[^a-z]/g,""),f=String(form).toLowerCase().replace(/[^a-z]/g,"");if(!a||!f)return false;if(a===f||(IRR[a]&&IRR[a].includes(f)))return true;
  const suf=["s","es","d","ed","ing","est","st","ly","n","en"],c=[a];
  if(a.endsWith("e"))c.push(a.slice(0,-1));                                  // make → making
  if(a.endsWith("y"))c.push(a.slice(0,-1)+"i");                              // study → studies、happy → happily
  if(a.endsWith("ie"))c.push(a.slice(0,-2)+"y");                             // die → dying
  if(/[^aeiou][aeiou][^aeiouwxy]$/.test(a)||/[aeiou][^aeiou]$/.test(a))c.push(a+a.slice(-1)); // stop → stopped
  if(a.endsWith("f"))c.push(a.slice(0,-1)+"v");if(a.endsWith("fe"))c.push(a.slice(0,-2)+"v");  // leaf → leaves
  if(a.endsWith("c"))c.push(a+"k");                                          // panic → panicked
  if(c.some(b=>suf.some(x=>b+x===f)))return true;
  if(/(er|ers|or|ors)$/.test(f)&&!/(er|or)$/.test(a))return false;
  // 不規則變化（understand → understood）：開頭至少七成相同、長度差不多，也算
  let p=0;while(p<a.length&&p<f.length&&a[p]===f[p])p++;return p>=4&&p>=a.length*.7&&Math.abs(a.length-f.length)<=2}
