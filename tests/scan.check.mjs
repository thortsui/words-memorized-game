// 掃描「漏網」情境的純邏輯測試：node tests/scan.check.mjs（tests/check.mjs 最後也會載入它）
// 來源：試用測試找到的問題（tests/playtest/site/ 的 hard2／hard2b／hard2c／hard3／hard5 與 sim-parser.mjs）。
// 兩個引擎共用同一個版面解析器，所以這裡直接假設「兩邊都讀得一字不差」（consensus(a,a)），
// 檢查解析器自己出的錯會不會被標成需確認、漏掉的文字會不會出現在覆蓋率清單裡。
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { parseRows, parseLayout, parseHead, deriveBlank, classifyRows, FLAG, dictHead, dictWord } from '../src/scan/parse.js';
import { toTrad, mostlyTraditional } from '../src/scan/s2t.js';
import { consensus, leftovers, compareRaw, regionText } from '../src/scan/consensus.js';
import { ruleWarnings, isInflection } from '../src/scan/rules.js';
import { makeLexicon } from '../src/scan/wordlist.js';

let n=0;const t=(name,fn)=>{fn();n++;console.log("ok  "+name)};
const rd=f=>fs.readFileSync(new URL("../"+f,import.meta.url),"utf8"),lex=makeLexicon(rd("public/wordlist/en-words.txt"),rd("public/wordlist/en-names.txt"));
const B=(text,x0,y0,x1,y1)=>({text,x0,y0,x1,y1}),W=1240,H=1754;
// 「自動通過」＝兩邊解析結果一致＋原始文字一致＋沒有任何規則警告（Google 翻譯核對不在這裡測）
const autoPass=(boxes)=>{const a=parseLayout(boxes,{W,H}),b=parseLayout(boxes,{W,H});return consensus(a,b,{rawA:a.cover.boxes,rawB:b.cover.boxes,W,H}).map(it=>({...it.entry,auto:it.status==="agree"&&!!it.raw&&it.raw.same&&!ruleWarnings(it.entry,lex).length,why:ruleWarnings(it.entry,lex)}))};
const rowsOf=lines=>lines.map((text,i)=>({text,x0:100,x1:900,y0:100+i*40,y1:130+i*40}));
const gate=lines=>parseRows(rowsOf(lines)).map(e=>({...e,auto:!ruleWarnings(e,lex).length}));

/* ---------- S1：兩欄版面，右欄很短 ---------- */
// hard2.png 的版面：左欄 3 筆（有例句、例句會換行），右欄只有標題和 3 筆沒有例句的片語
const leftCol=[B("Unit 9",80,92,157,118),
  B("achieve v. 達成；實現",80,150,312,176),B("After years of hard work, she finally achieved her goal of",110,182,551,204),B("becoming a doctor.",110,210,261,232),
  B("behavior n. 行為；舉止",80,253,328,279),B("The teacher was pleased with the students' good behavior",110,285,560,307),B("during the trip.",110,313,228,335),
  B("community n. 社區；群體",80,356,353,382),B("The whole community helped to clean up the park after the",110,388,572,410),B("storm.",110,416,162,438)];
const truthL=[["achieve","v.","達成；實現","After years of hard work, she finally achieved her goal of becoming a doctor.","Unit 9"],["behavior","n.","行為；舉止","The teacher was pleased with the students' good behavior during the trip.","Unit 9"],["community","n.","社區；群體","The whole community helped to clean up the park after the storm.","Unit 9"]];
const flat=e=>[e.en,e.pos,e.zh,e.ex,e.unit];
t("S1 右欄只有 3 筆沒有例句的片語（hard2）：照樣分欄，左欄不受影響、右欄三筆都在、單元各歸各的",()=>{
  const r=autoPass([...leftCol,B("Key Phrases",660,92,810,118),B("deal with 處理；應付",660,150,878,176),B("in charge of 負責；掌管",660,210,905,236),B("come up with 想出；提出",660,270,921,296)]);
  assert.deepEqual(r.map(flat),[...truthL,["deal with","片語","處理；應付","","Key Phrases"],["in charge of","片語","負責；掌管","","Key Phrases"],["come up with","片語","想出；提出","","Key Phrases"]]);
  assert.ok(r.every(e=>e.auto),JSON.stringify(r.filter(e=>!e.auto).map(e=>[e.en,e.why])))});
t("S1 右欄 2 筆有例句（hard2b）、兩欄之間的空白很窄（hard2c，只剩 20 幾 px）也分得開",()=>{
  const r=autoPass([...leftCol,B("Key Phrases",612,92,762,118),B("deal with 處理；應付",612,150,830,176),B("The manager has to deal with many complaints.",642,182,1010,204),B("in charge of 負責；掌管",612,225,857,251),B("Ms. Lin is in charge of the sales department.",642,257,1000,279)]);
  assert.deepEqual(r.map(flat),[...truthL,["deal with","片語","處理；應付","The manager has to deal with many complaints.","Key Phrases"],["in charge of","片語","負責；掌管","Ms. Lin is in charge of the sales department.","Key Phrases"]]);
  assert.equal(r[4].blank,"in charge of");assert.ok(r.every(e=>e.auto))});
t("S1 萬一真的沒分開（有一個文字框橫跨兩欄）：併在一起的條目一律被攔下，不會有內容錯卻自動通過的",()=>{
  // 左欄一行例句被 OCR 黏到右欄去（一個框從左欄一路蓋到右欄），整頁找不到完整的直向空白帶
  const bs=[...leftCol.filter(b=>!b.text.startsWith("After years")),B("After years of hard work, she finally achieved her goal of deal with 處理；應付",110,182,878,204),
    B("Key Phrases",660,92,810,118),B("in charge of 負責；掌管",660,255,905,281),B("come up with 想出；提出",660,358,921,384)],r=autoPass(bs),truth=new Map([...truthL,["in charge of","片語","負責；掌管","","Key Phrases"],["come up with","片語","想出；提出","","Key Phrases"]].map(x=>[x[0],x.join("|")]));
  for(const e of r)if(e.auto)assert.equal(flat(e).join("|"),truth.get(e.en),"自動通過但內容不對："+flat(e).join("|"));
  assert.ok(r.filter(e=>!e.auto).length>=2);
  // 單元標籤左右各一個時，照左右位置對，不會全部標成右欄的
  assert.ok(r.filter(e=>["achieve","behavior","community"].includes(e.en)).every(e=>e.unit==="Unit 9"))});
t("表格式版面（左邊全英文、右邊全中文）不會被切成兩欄，但因為同一列相隔很遠，全部要人工確認",()=>{const bs=[];["abandon v.","borrow v.","climate n.","damage n."].forEach((x,i)=>{bs.push(B(x,90,100+i*60,300,130+i*60));bs.push(B(["放棄","借入","氣候","損害"][i],700,100+i*60,800,130+i*60))});
  const r=autoPass(bs);assert.deepEqual(r.map(e=>e.en+"|"+e.zh),["abandon|放棄","borrow|借入","climate|氣候","damage|損害"]);assert.ok(r.every(e=>!e.auto&&e.flags.includes(FLAG.wide)))});

/* ---------- S2：例句後面的非例句文字、特殊寫法的條目 ---------- */
t("S2 同義字列（= …）、反義字列（↔ …）不會接進例句",()=>{for(const note of ["= desert, give up","↔ mean, stingy","syn. desert","反：keep"]){
  const r=gate(["abandon v. 放棄；拋棄","The sailors abandoned the damaged ship.",note,"dye v. 染色","Mary dyed her hair red."]);
  assert.deepEqual(r.map(e=>e.ex),["The sailors abandoned the damaged ship.","Mary dyed her hair red."]);assert.ok(r.every(e=>e.auto))}});
t("S2 頁尾書名與頁碼不會接進例句；留在覆蓋率清單，上一筆要人工確認",()=>{const c=classifyRows(rowsOf(["experiment n. 實驗","The students did an interesting experiment on plants.","Senior High English Vocabulary Book Three","23"]));
  assert.equal(c.entries[0].ex,"The students did an interesting experiment on plants.");assert.deepEqual(c.rows.map(r=>r.use),["head","ex",null,"hf"]);assert.ok(c.entries[0].flags.includes(FLAG.trail))});
t("S2 頁尾離內文很遠時自動歸成頁首頁尾（不擋、但列在「自動略過」）",()=>{const rows=rowsOf(["experiment n. 實驗","The students did an interesting experiment on plants."]).concat([{text:"Senior High English Vocabulary Book Three",x0:100,x1:560,y0:300,y1:326},{text:"23",x0:1090,x1:1112,y0:300,y1:326}]),c=classifyRows(rows);
  assert.deepEqual(c.rows.map(r=>r.use),["head","ex","hf","hf"]);assert.deepEqual(c.entries[0].flags,[])});
t("S2 ~ 與 ... 的片語／句型是條目（be famous for ~、It is said that ...），不會消失或併進上一筆",()=>{
  let r=gate(["social adj. 社交的；社會的","Amy shares photos on social media every day.","be famous for ~ 以……聞名","Tainan is famous for its delicious street food.","dye v. 染色","Mary dyed her hair red."]);
  assert.deepEqual(r.map(flat).map(x=>x.slice(0,4)),[["social","adj.","社交的；社會的","Amy shares photos on social media every day."],["be famous for ~","片語","以……聞名","Tainan is famous for its delicious street food."],["dye","v.","染色","Mary dyed her hair red."]]);
  r=gate(["social adj. 社交的；社會的","Amy shares photos on social media every day.","It is said that ... 據說……","It is said that the old house is haunted.","dye v. 染色","Mary dyed her hair red."]);
  assert.deepEqual(r.map(e=>e.en),["social","It is said that ...","dye"]);assert.equal(r[1].ex,"It is said that the old house is haunted.");assert.equal(r[0].ex,"Amy shares photos on social media every day.");
  assert.deepEqual(parseHead("be famous for ~ 以......聞名"),{en:"be famous for ~",pos:"片語",zh:"以……聞名"});       // OCR 把刪節號讀成六個句點
  assert.ok(gate(["be famous for ~ 以.....聞名","Tainan is famous for its delicious street food."])[0].flags.includes(FLAG.dots))});      // 點數不對 → 標疑點
t("S2 一字多義分行（charge v. 1. 收費／2. 充電）：整筆留著、中文和例句合併，並要求人工確認",()=>{const r=gate(["charge v. 1. 收費","The hotel charges two thousand dollars a night.","2. 充電","I need to charge my phone.","dye v. 染色","Mary dyed her hair red."]);
  assert.deepEqual(r.map(e=>e.en),["charge","dye"]);assert.equal(r[0].zh,"1. 收費 2. 充電");assert.equal(r[0].ex,"The hotel charges two thousand dollars a night. I need to charge my phone.");assert.ok(!r[0].auto&&r[0].flags.includes(FLAG.sense));assert.ok(r[1].auto)});
t("S2 例句有兩列完整的句子（A: B: 對話）會接起來，但要人工確認；不是完整句子的不接",()=>{const r=gate(["borrow v. 借入","A: May I borrow your pen?","B: Sure. Here you are.","dye v. 染色","Mary dyed her hair red."]);
  assert.equal(r[0].ex,"A: May I borrow your pen? B: Sure. Here you are.");assert.ok(!r[0].auto&&r[0].flags.includes(FLAG.multi));assert.ok(r[1].auto)});
t("S2 衍生字列、搭配詞列各自成為一筆",()=>{assert.deepEqual(gate(["appreciate v. 感激；欣賞","Emma appreciated her neighbor taking care of her dog.","appreciation n. 感激；欣賞","dye v. 染色","Mary dyed her hair red."]).map(e=>e.en),["appreciate","appreciation","dye"]);
  assert.deepEqual(gate(["effort n. 努力","With a little more effort, you will pass the test.","make an effort to V. 努力做……","dye v. 染色","Mary dyed her hair red."]).map(e=>e.en+"|"+e.pos),["effort|n.","make an effort to V.|片語","dye|v."])});
t("S2 例句的中文翻譯（夾英文人名）不會變成一筆「Mary」，也不會接進例句",()=>{const r=gate(["dye v./n. 染色；染料","Mary dyed her hair red for a fresh look.","Mary 把頭髮染成紅色。","social adj. 社交的；社會的","Amy shares photos on social media every day.","Amy 用 Facebook 和 Instagram 分享照片。"]);
  assert.deepEqual(r.map(flat).map(x=>x.slice(0,4)),[["dye","v./n.","染色；染料","Mary dyed her hair red for a fresh look."],["social","adj.","社交的；社會的","Amy shares photos on social media every day."]]);assert.ok(r.every(e=>e.auto))});
t("詞性照書上的寫法：v./n. 不改成 v., n.；v.,n. 與 v , n. 統一成 v., n.",()=>{assert.equal(parseHead("dye v./n. 染色").pos,"v./n.");assert.equal(parseHead("record v., n. 記錄").pos,"v., n.");assert.equal(parseHead("record v.,n. 記錄").pos,"v., n.");assert.equal(parseHead("clean adj./v. 乾淨的").pos,"adj./v.")});
t("克漏字答案：painter／teacher／driver 不是 paint／teach／drive 的變化形",()=>{assert.equal(deriveBlank("paint","v.","The painter painted the wall blue."),"painted");assert.equal(deriveBlank("teach","v.","Our teacher teaches math and science."),"teaches");assert.equal(deriveBlank("drive","v.","The driver drove us to the airport."),"drove");assert.equal(deriveBlank("lead","v.","The guide led us to the top of the hill."),"led");assert.equal(deriveBlank("modern","adj.","Modern buildings stand next to the ancient temple."),"Modern");
  assert.ok(!isInflection("paint","painter")&&!isInflection("act","actor")&&isInflection("paint","painted")&&isInflection("big","biggest")&&isInflection("lie","lies"));
  assert.ok(ruleWarnings({en:"paint",pos:"v.",zh:"油漆",ex:"The painter came.",blank:"painter"},lex).some(x=>x.includes("規則變化")))});

/* ---------- S3：漏掉的條目一定看得見（覆蓋率） ---------- */
// hard3.jpg 的版面：有編號、有音標；第 2 筆的開頭被 OCR 讀壞（讀不出條目）
const hard3=[B("Unit 3 校園生活",97,45,230,70),B("Senior High English Vocabulary",630,60,840,82),
  B("1. abandon [ə`bændən] v. 放棄；拋棄",95,105,436,133),B("The sailors abandoned the damaged ship.",140,140,452,162),B("= desert, give up",140,166,266,188),
  B("2.d¥e [da1 v/n 將染色；染料",93,205,480,233),B("Mary dyed her hair red for a fresh look.",138,240,436,262),
  B("3. e-mail [`i,mel] n. 電子郵件",91,280,345,308),B("Please send me an e-mail when you arrive.",136,314,450,336),
  B("4. lie [laɪ] v. 躺；位於；說謊",89,355,348,383),B("The town lies at the foot of the mountain.",134,389,438,411),
  B("Senior High English Vocabulary Book Three",70,1235,386,1257),B("23",803,1250,820,1270)];
t("S3 讀不出來的條目開頭不會無聲無息消失：它和它的例句都留在「沒被收進條目的文字」，上一筆也不會被污染",()=>{const e=parseLayout(hard3,{W:930,H:1316}),lo=leftovers(e.cover,e.cover);
  assert.deepEqual(e.map(x=>[x.en,x.pos,x.zh,x.ex]),[["abandon","v.","放棄；拋棄","The sailors abandoned the damaged ship."],["e-mail","n.","電子郵件","Please send me an e-mail when you arrive."],["lie","v.","躺；位於；說謊","The town lies at the foot of the mountain."]]);
  assert.deepEqual(lo.left.map(l=>l.text),["2.d¥e [da1 v/n 將染色；染料","Mary dyed her hair red for a fresh look."]);
  assert.deepEqual(lo.skipped.map(l=>l.text).sort(),["23","Senior High English Vocabulary","Senior High English Vocabulary Book Three"]);
  assert.ok(e.every(x=>x.unit==="Unit 3"));assert.equal(e[2].blank,"lies")});
t("音標：純英文字母的 [dai]、漏掉右括號的 [daɪ、詞性後面的 [C] 都處理得對",()=>{assert.deepEqual(parseHead("2. dye [dai] v./n. 染色；染料"),{en:"dye",pos:"v./n.",zh:"染色；染料"});assert.deepEqual(parseHead("8. lie [lar v. 躺；位於"),{en:"lie",pos:"v.",zh:"躺；位於"});assert.equal(parseHead("effect n.[C] 影響").pos,"n.[C]");assert.equal(parseHead("5.responsible [rɪ`spɑnsəb!] adj. 負責任的").en,"responsible")});
t("每個文字框都有去處：條目用掉的、單元標籤、頁首頁尾、沒用到的，加起來等於全部",()=>{const e=parseLayout(hard3,{W:930,H:1316}),u=e.cover.boxes.map(b=>b.use);assert.equal(u.length,hard3.length);
  assert.equal(u.filter(x=>x===null).length,2);assert.equal(u.filter(x=>x==="hf").length,3);assert.equal(u.filter(x=>x==="unit").length,1);assert.equal(u.filter(x=>x==="note").length,1);
  // 每筆條目的欄位都對得回來源文字框
  assert.deepEqual(e[0].src.head.map(i=>hard3[i].text),["1. abandon [ə`bændən] v. 放棄；拋棄"]);assert.deepEqual(e[0].src.ex.map(i=>hard3[i].text),["The sailors abandoned the damaged ship."]);assert.deepEqual(e[0].src.other.map(i=>hard3[i].text),["= desert, give up"])});
t("複核引擎讀到、主引擎完全沒看到的文字也會列出來",()=>{const a=parseLayout(hard3.filter(b=>!b.text.startsWith("4.")&&!b.text.startsWith("The town")),{W:930,H:1316}),b=parseLayout(hard3,{W:930,H:1316});
  // 主引擎漏看第 4 筆 → 複核引擎有讀到 → 清單裡多一筆「只有複核引擎讀到」（onlyB），不是無聲消失
  assert.deepEqual(consensus(a,b).filter(x=>x.status==="onlyB").map(x=>x.entry.en),["lie"]);
  const cb={W:930,H:1316,boxes:[...b.cover.boxes,{text:"extra line",x0:100,y0:600,x1:300,y1:625,use:null,ei:-1}]};assert.ok(leftovers(a.cover,cb).left.some(l=>l.text==="extra line"&&l.from==="b"))});

/* ---------- 雙重確認的定義：欄位一致＋原始文字一致＋單元一致 ---------- */
t("S5 單元標籤納入比對：兩邊單元不同就是差異",()=>{const a=[{en:"dye",pos:"v.",zh:"染色",ex:"Mary dyed her hair red.",blank:"dyed",unit:"NO.307 Unit 5"}],b=[{...a[0],unit:"NO.307 Unit $"}],r=consensus(a,b);
  assert.equal(r[0].status,"diff");assert.deepEqual(r[0].bad,["unit"])});
t("原始文字比對：解析後一樣、但那一塊原圖上兩邊讀到的字不同（被解析器丟掉的字也算）→ 不是雙重確認",()=>{
  const A=[B("abandon v. 放棄；拋棄",80,150,312,176),B("The sailors abandoned the damaged ship.",110,182,451,204),B("= desert, give up",110,210,240,232),B("dye v. 染色",80,260,220,286),B("Mary dyed her hair red.",110,292,300,314)];
  const Bx=A.map(b=>b.text.startsWith("=")?{...b,text:"= dessert, give up"}:b),a=parseLayout(A,{W,H}),b=parseLayout(Bx,{W,H}),r=consensus(a,b,{rawA:a.cover.boxes,rawB:b.cover.boxes,W,H});
  assert.deepEqual(r.map(x=>x.status),["agree","agree"]);assert.equal(r[0].raw.same,false);assert.equal(r[1].raw.same,true);assert.ok(r[0].raw.diff.b.some(([s,d])=>d&&s==="s"));
  assert.equal(consensus(a,b)[0].raw,null);                                          // 沒有原始文字可比（例如 Claude）→ null，上傳頁會要求人工確認
  // 例句的中文翻譯不存進字典，兩邊都判成翻譯時不列入比對
  const T=[...A.slice(0,2),B("船員們拋棄了那艘受損的船。",110,210,400,232)],T2=T.map(b=>b.text.startsWith("船")?{...b,text:"船員們拋華了那艘受損的船。"}:b),ta=parseLayout(T,{W,H}),tb=parseLayout(T2,{W,H});
  assert.equal(consensus(ta,tb,{rawA:ta.cover.boxes,rawB:tb.cover.boxes,W,H})[0].raw.same,true);
  assert.equal(regionText(A,{x0:0,y0:140,x1:W,y1:240}),"abandon v. 放棄；拋棄 The sailors abandoned the damaged ship. = desert, give up")});
t("規則檢查：例句沒有句尾標點、中文夾英文、簡體字、結構疑點都要人工確認",()=>{const w={en:"achieve",pos:"v.",zh:"達成；實現",ex:"She finally achieved her goal.",blank:"achieved"},has=(x,s)=>ruleWarnings(x,lex).some(m=>m.includes(s));
  assert.deepEqual(ruleWarnings(w,lex),[]);assert.ok(has({...w,ex:"After years of hard work, she finally achieved her goal of"},"結尾"));assert.ok(has({...w,zh:"達成；實現 deal with 處理；應付"},"夾著英文"));
  assert.ok(!has({...w,zh:"能幹的（be capable of V-ing 有能力做某事）"},"夾著英文"));assert.ok(has({...w,zh:"达成；实现"},"簡體"));assert.ok(has({...w,flags:[FLAG.trail]},"沒被收進條目"));assert.ok(!has({en:"be famous for ~",pos:"片語",zh:"以……聞名",ex:"Tainan is famous for its food.",blank:""},"奇怪"))});
/* ---------- S9：課本的字典式版面（手機照片：分隔線是斜的、有手寫筆記、旁邊露出隔壁頁和講義） ---------- */
// 左欄：編號單字＋音標、衍生字＋音標、手寫筆記；右欄：「▶ 詞性 中文 英文解釋」→「• 例句」；同一個字的第二個意思右欄另起一個 ▶、左欄沒有字。
// 分隔線往右下斜（x＝440＋0.1·y），模擬照片沒拍正。
{const dx=y=>Math.round(.1*y),L=(text,x0,y,x1)=>B(text,x0+dx(y)*.4,y,x1+dx(y)*.4,y+40),R=(text,x0,y,x1)=>B(text,x0+dx(y),y,x1+dx(y),y+40);
const page=[B("Lesson 3 Things at Home",800,30,1150,62),
  L("1. glow",120,150,250),L("[glo]",140,198,230),L("shine",130,250,230),                              // shine 是手寫的同義字（不同字根）
  R("▶ vi. 發光 to give out a soft light",440,150,980),R("• The lamp glows softly in the dark room.",460,198,1010),
  L("glowing",120,330,270),L("[ˈgloɪŋ]",140,378,270),
  R("▶ adj. 發光的",440,330,640),R("• We saw a glowing light over the",460,378,960),R("hill at midnight.",490,426,700),
  L("2. kind",110,560,240),L("[kaɪnd]",140,608,260),
  R("▶ adj. 仁慈的 friendly and helpful",440,560,960),R("• She is always kind to animals.",460,608,900),
  R("▶ n. [C] 種類",440,700,640),R("• What kind of music do you like?",460,748,940),R("• This is a new kind of apple.",460,796,900),
  B("作業；任務",1300,560,1460,600),B("ike",0,330,40,370),                                                   // 右邊另一張講義、左邊隔壁頁的字
  L("3. careful",110,900,290),L("[ˈkɛrfəl]",140,948,290),L("careless 粗心",120,1000,330),             // 手寫：同字根但同一段有中文
  R("▶ adj. 小心的",440,900,640),R("• Be careful when you cross the street.",460,948,1000)];
t("字典式版面：左欄單字配右欄區塊（斜的分隔線）、第二個意思併進同一筆、音標／講義／隔壁頁不算漏字、手寫筆記留給使用者",()=>{
  const r=parseLayout(page,{W,H});assert.equal(r.layout,"dict");
  assert.deepEqual(r.map(e=>[e.en,e.pos,e.zh]),[["glow","vi.","發光"],["glowing","adj.","發光的"],["kind","adj., n.","仁慈的；種類"],["careful","adj.","小心的"]]);
  assert.equal(r[0].ex,"The lamp glows softly in the dark room.");assert.equal(r[0].blank,"glows");
  assert.equal(r[1].ex,"We saw a glowing light over the hill at midnight.","例句換行接回來");
  assert.equal(r[2].ex,"She is always kind to animals.","第二個意思的例句不收");assert.ok(r[2].flags.includes(FLAG.dsense),"併起來的要人工確認");
  assert.ok(r.every(e=>e.unit==="Lesson 3"),"頁首 Lesson 當單元");
  const use=txt=>r.cover.boxes.find(b=>b.text===txt).use;
  assert.equal(use("[glo]"),"note");assert.equal(use("作業；任務"),"hf");assert.equal(use("ike"),"hf");assert.equal(use("• This is a new kind of apple."),"tr");
  assert.equal(use("▶ vi. 發光 to give out a soft light"),"zh");
  assert.equal(use("shine"),null,"手寫的字不配給任何一筆，但要列出來給使用者處理");assert.equal(use("careless 粗心"),null);
  // 一般的條列式版面不會被當成字典式
  assert.notEqual(parseLayout(leftCol,{W,H}).layout,"dict")});
t("字典式版面：手寫的同字根筆記搶不走印刷單字的區塊；沒讀到單字的區塊不硬配手寫的字",()=>{
  // 手寫的 glowy 寫在 ▶ 那一列旁邊（比印刷的 1. glow 更貼近），印刷的單字有編號、下一列有音標，要贏
  const p2=[L("glowy",130,140,230),L("1. glow",120,190,250),L("[glo]",140,238,230),R("▶ vi. 發光",440,150,640),R("• The lamp glows softly.",460,198,900),
    L("2. kind",110,400,240),L("[kaɪnd]",140,448,260),R("▶ adj. 仁慈的",440,400,640),R("• She is kind.",460,448,700),
    R("▶ n. [C] 種類",440,600,640),R("• What kind of music do you like?",460,648,940),L("In",130,600,170)];  // In 是手寫，剛好在第二個意思旁邊
  const r=parseLayout(p2,{W,H});assert.deepEqual(r.map(e=>[e.en,e.zh]),[["glow","發光"],["kind","仁慈的；種類"]])});
}
t("簡體字：PP-OCR 在繁體書上讀成的簡體字換回繁體；簡體書不換",()=>{
  assert.equal(toTrad("羡慕；擠满的；消费者；毒药；环境"),"羨慕；擠滿的；消費者；毒藥；環境");
  assert.equal(toTrad("头发"),"头发","一對多的字（发→發／髮）不換");
  assert.ok(mostlyTraditional(["消费者","毒药","物質"]),"繁體書上偶爾幾個簡體字");assert.ok(!mostlyTraditional(["这是我们的学习时间","国家","说话"]),"簡體書")});
t("字典式版面的詞性列：[U] 被讀成 [UJ／fUJ、vt. 讀成 yt.、中文半形括號",()=>{
  assert.deepEqual(dictHead("▶ n. [UJ 傷害 damage or injury"),{pos:"n.",zh:"傷害",rest:"damage or injury"});
  assert.deepEqual(dictHead("yt.羡慕 to desire"),{pos:"vt.",zh:"羡慕",rest:"to desire"});
  assert.equal(dictHead("adj. 塑膠(製）的 made of plastic").zh,"塑膠（製）的");assert.equal(dictHead("n. sing. 自然環境 the natural world").pos,"n.");
  assert.equal(dictHead("The house is big."),null);assert.equal(dictWord("13. recycling").w,"recycling");assert.equal(dictWord("[kraʊd]"),null);assert.equal(dictWord("drift apart 漂走"),null)});
console.log(`掃描漏網情境：全部通過 ${n} 項`);
