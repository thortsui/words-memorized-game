// 出題與判分（純函式，不碰 DOM；可在 Node 直接測試）
export const shuffle=a=>{a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
export const isPhrase=w=>/片語|phr/i.test(w.pos)||/\s/.test(w.en.trim());
export const MODES=[["en2zh","英翻中・選擇"],["zh2en","中翻英・選擇"],["en2zhT","英翻中・填空"],["zh2enT","中翻英・填空"],["cloze","克漏字"]];
export const modeName=m=>(MODES.find(x=>x[0]===m)||[0,""])[1];
// 填空題型對應的選擇題型（魂系閃避題一律選擇題）
export const mcOf=m=>m==="en2zhT"?"en2zh":m==="zh2enT"?"zh2en":m;

// 朗讀前清理英文
export const sayable=t=>String(t).replace(/\(s\)/g,"s").replace(/\bsb\b/g,"somebody").replace(/\bsth\b/g,"something").replace(/one's/g,"one's").replace(/\b(N\.|V-ing|V\.|O\.|S\.|Adj\.|p\.p\.)|wh-疑問詞|[+/()]|\.\.\.|…/g," ").replace(/\s+/g," ").trim();
export const zhSay=t=>String(t).replace(/（[^）]*）|\([^)]*\)/g,"").replace(/……|…/g,"").replace(/sb|sth/g,"").trim();

export function clozeAns(w){if(w.blank&&w.ex.toLowerCase().includes(w.blank.toLowerCase()))return w.blank;if(isPhrase(w))return"";const base=w.en.toLowerCase().replace(/[^a-z]/g,""),stem=base.slice(0,Math.max(3,base.length-2));const m=w.ex.match(/[A-Za-z’'-]+/g)||[];return m.find(t=>t.toLowerCase().startsWith(stem))||""}

// 干擾選項：先限同為單字或片語；同詞性夠 3 個就只用同詞性
export function opts(w,key,bank){const ph=isPhrase(w),val=x=>key==="cloze"?clozeAns(x):x[key],ans=val(w);let c=bank.filter(x=>x.id!==w.id&&val(x)&&val(x).toLowerCase()!==ans.toLowerCase()&&isPhrase(x)===ph);
  const sp=c.filter(x=>x.pos===w.pos);if(sp.length>=3)c=sp;if(c.length<3)c=bank.filter(x=>x.id!==w.id&&val(x)&&val(x).toLowerCase()!==ans.toLowerCase());
  const pick=[],seen=new Set([ans.toLowerCase()]);for(const x of shuffle(c)){const v=val(x);if(seen.has(v.toLowerCase()))continue;seen.add(v.toLowerCase());pick.push(v);if(pick.length===3)break}
  return shuffle([ans,...pick])}

export const normEn=s=>String(s).toLowerCase().replace(/[’]/g,"'").replace(/\b(sb|sth|somebody|something|n\.|v-ing|v\.|o\.|s\.|adj\.|p\.p\.)(?=\s|$|[/)+])/g," ").replace(/wh-疑問詞|[+()…]|\.\.\./g," ").replace(/[^a-z' ]/g," ").replace(/\s+/g," ").trim();
export function enVariants(en){const t=en.split(/\s+/);let v=[""];t.forEach(tok=>{const alts=/^[a-z]+\/[a-z]+$/i.test(tok)?tok.split("/"):[tok];v=v.flatMap(p=>alts.map(a=>p+" "+a))});return v.map(normEn)}
export const checkEn=(inp,w)=>enVariants(w.en).includes(normEn(inp));
export const zhSegs=zh=>zh.replace(/（[^）]*）|\([^)]*\)/g,"").split(/[、；;，,]/).map(s=>s.replace(/[…\.。\s]|等$/g,"")).filter(Boolean);
const ZSTOP="的了是在把被與和或及某人事物一個種使得地之者等再……";
export const zc=s=>[...String(s).replace(/（[^）]*）|\([^)]*\)/g,"")].filter(c=>/[㐀-鿿]/.test(c)&&!ZSTOP.includes(c));
export function nearZh(t,terms){const tc=zc(t);if(!tc.length)return false;return terms.some(s=>{s=String(s);if(!s)return false;const sc=new Set(zc(s));if(s===t||(t.length>=1&&s.length>=1&&(s.includes(t)||t.includes(s))&&zc(s).length))return true;const hit=tc.filter(c=>sc.has(c)).length;return hit>=1&&hit/tc.length>=.5})}
export function checkZh(inp,zh){const t=inp.replace(/[\s…\.。]/g,"");if(!t)return false;return zhSegs(zh).some(s=>s===t||(t.length>=2&&(s.includes(t)||t.includes(s))))}

// Google 翻譯（非官方端點）
const GC={};
export async function gtrans(t,sl,tl){sl=sl||"en";tl=tl||"zh-TW";const key=sl+tl+t;if(GC[key])return GC[key];const r=await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl="+sl+"&tl="+tl+"&dt=t&dt=bd&q="+encodeURIComponent(t));if(!r.ok)throw new Error("HTTP "+r.status);
  const j=await r.json(),main=(j[0]||[]).map(x=>x&&x[0]||"").join(""),dict=[];(j[1]||[]).forEach(e=>(e&&e[1]||[]).forEach(x=>dict.push(x)));return GC[key]={main,dict}}
const tmo=(p,ms)=>Promise.race([p,new Promise((_,no)=>setTimeout(()=>no(new Error("timeout")),ms))]);
// 中文填空：書上義項 → 共同字過半 → Google 翻譯 → 翻回英文含字幹
export async function checkZhSmart(inp,w){const t=inp.replace(/[\s…\.。，,]/g,"");if(!t)return{ok:false};if(checkZh(t,w.zh))return{ok:true};
  if(nearZh(t,zhSegs(w.zh)))return{ok:true,loose:"意思相近"};
  try{const g=await tmo(gtrans(sayable(w.en)),3500);if(nearZh(t,[g.main,...g.dict]))return{ok:true,loose:"Google 翻譯也有這個意思"}}catch(e){}
  try{const r=await tmo(gtrans(t,"zh-TW","en"),3500),txt=(r.main+" "+r.dict.join(" ")).toLowerCase(),base=w.en.toLowerCase().replace(/[^a-z ]/g," ").trim().split(/\s+/).filter(x=>!/^(sb|sth|n|v|o|s|adj|ing|be|to|a|the)$/.test(x));
    if(base.length&&base.every(b=>{const stem=b.slice(0,Math.max(3,b.length-2));return txt.includes(stem)}))return{ok:true,loose:"翻回英文就是這個字"}}catch(e){}
  return{ok:false}}

// 掃描核對用
const STOP=new Set("的了是在把被與和或及某人事物一個種使得到地之者等再".split(""));
export const cjk=s=>[...String(s).replace(/（[^）]*）|\([^)]*\)/g,"")].filter(c=>/[㐀-鿿]/.test(c)&&!STOP.has(c));
