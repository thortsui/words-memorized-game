// 條目的規則檢查（純函式，不連網；Google 翻譯核對另外在上傳頁做）。回傳警告文字陣列，空陣列＝通過。
import { isPhrase, clozeAns } from '../core/grading.js';
import { unknownWords } from './wordlist.js';

import { isInflection } from './inflect.js';
import { TERM } from './parse.js';
export { isInflection };
// 常見、而且和繁體寫法不同的簡體字（繁體書上不會出現）
const SIMP=new Set("当静学习说话这为们时来国会对开关东车马门问间见长书买卖儿两个么义乌乐乔亚产亲亿仅从仓仪价众优伤传伟体侠俩债倾偿侧储党兰兴养兽冈写军农决况冻净减凤击则刚创别刘剂剑动务势劳勋区医华协单卫却厂历厉压厌县参双发变叙号叹吓吗听启员呜响哑唤啸喷团园围图圆圣场坏块坚垒处备复够头夹夺奋奖妇妈娱婴孙宁实宠审宪宫宽宾寻导将尔尘尝层属岁岛岭峡币师带帮库应废广庆庐异弃张弹强归录彻径忆态怀总恋恶悦惊惧惯愤愿戏战户扑执扩扫护报担拟拥择挂挡挤挥损换据掳掷搁携摄摆摇撑敌数斋断旧显晋晒晓暂术机杀杂权条极构枪样标栏树档梦检楼横欢欧残毁毕气汇汉汤沟没泪泼洁浅济涂涛润涨渐渔温湾湿满滚滞潜灭灯灵灾灿炉点炼烂烛烟烦烧热爱爷牵牺状狭狮独猎献环现琼电画畅疗疯痒瘦盐监盖盘矿码础确礼祸离种积称稳窃竞笔笼筑签简类粮纠红纤约级纪纬纯纱纲纳纵纷纸纹纺组细织终绍经绑结绕绘给络绝统绢继绩绪续维绵综绿缓编缘缚缩罗罚罢羡翘联聪肃肠胁胜脉脏脑脚脱脸腊舰艰艺节芦苏苹荣药莲获营萧萨蓝蔼虏虑虽虾蚀蚁蚂蛮补装观规视览觉誉计订认讨让训议讯记讲讶许论设访证评识诉词译试诗诚该详语误诵请诸读课谁调谈谊谋谜谢谣谦谨谱贝负贡财责贤败货质贩贪贫购贯贱贴贵贷贸费贺赁资赋赌赏赔赖赛赞赠赵赶趋跃踪践轨轩转轮软轰轻载较辅辆辈辉输辞边达迁过迈运还进远违连迟适选逊递逻遗邓邮邻郑酱释针钉钓钟钢钥钱钻铁铃铅银铜铝铸链销锁锅锋错锡锦键镇镜闪闭闯闲闷闸闹闻阅队阳阴阵阶际陆陈险随隐难雾顶顷项顺须顾顿颁预领颇频颗题颜额风飞饥饭饮饰饱馆驱驳驶驻验骂骄骑骗骤鱼鲁鲜鸟鸡鸣鸭鸿鹅鹰麦黄齐齿龙龟".split(""));

// lex：英文詞表（Set）；傳 null 表示詞表沒載到，會多一條警告（拼字沒檢查就不能算通過）
// opt.manual：使用者自己打的條目，不檢查「沒有詞性」
export function ruleWarnings(w,lex,opt={}){const warn=[],en=String(w.en||""),ex=String(w.ex||""),blank=String(w.blank||"");
  if(w.unsure)warn.push("提取時標示這筆有看不清楚的字，請對照原圖");
  if(Array.isArray(w.flags))warn.push(...w.flags);                                    // 版面解析時記下的結構疑點
  if(ex&&!TERM.test(ex.trim()))warn.push("例句不是以句號、問號或驚嘆號結尾，可能被截斷或接錯");
  if(!en)warn.push("英文是空的");if(!w.zh)warn.push("中文是空的");
  if(en&&!isPhrase(w)&&ex&&!clozeAns({...w,blank:""})&&!(blank&&ex.toLowerCase().includes(blank.toLowerCase())))warn.push("例句裡找不到這個字，英文或例句可能辨識錯");
  if(blank&&ex&&!ex.toLowerCase().includes(blank.toLowerCase()))warn.push("克漏字答案不在例句裡");
  // 兩個引擎可能犯同一種錯（例如都把片語 pick up 黏成 pickup）：例句裡的字形要像是這個字的變化形，單字也要有詞性
  if(en&&!isPhrase(w)&&ex){const f=blank&&ex.toLowerCase().includes(blank.toLowerCase())?blank:clozeAns({...w,blank:""});
    if(f&&!/\s/.test(f.trim())&&!isInflection(en,f))warn.push(`例句裡是「${f}」，不像「${en}」的規則變化（不規則變化請自行確認；也可能是片語少了空格）`)}
  if(en&&!opt.manual&&!String(w.pos||"").trim()&&!/\s/.test(en.trim()))warn.push("單字沒有讀到詞性（如果是片語，英文可能少了空格）");
  if(ex&&/[㐀-鿿]/.test(ex))warn.push("例句裡混到中文");
  // 中文解釋裡夾著英文字（文法記號 sb、sth、N.、V-ing 除外）：多半是把旁邊另一欄或另一筆的字併進來了
  if(/[A-Za-z]{2,}/.test(String(w.zh||"").replace(/（[^）]*）|\([^)]*\)/g,"").replace(/\b(?:sb|sth|N|V|O|S|Adj|Adv|V-ing|p\.p|one's|oneself)\b\.?/g,"")))warn.push("中文解釋裡夾著英文字，可能把別筆或另一欄的內容併進來了");
  // 本機 OCR 模型同時認得簡體字，偶爾會把繁體讀成簡體（當／当、靜／静）：出現常見的簡體字就要人看
  {const sc=[...String(w.zh||"")].filter(c=>SIMP.has(c));if(sc.length)warn.push(`中文裡有簡體字「${[...new Set(sc)].join("")}」，可能辨識錯（書上應該是繁體）`)}
  if(en&&!/^[A-Za-z][A-Za-z'’.\/\-+ ()…,~]*$/.test(en.replace(/wh-疑問詞/g,"").replace(/^(?:\.\.\.|…)[, ]*/,"")))warn.push("英文含有奇怪的字元");
  if(w.pos&&!/^(片語|phr\.?|(?:(?:n|v|vt|vi|adj|adv|prep|conj|pron|int|interj|aux|art|det|num|abbr)\.(?:\[[A-Za-z]{1,2}\])?)(?:\s*[,\/&;]\s*(?:n|v|vt|vi|adj|adv|prep|conj|pron|int|interj|aux|art|det|num|abbr)\.(?:\[[A-Za-z]{1,2}\])?)*)$/.test(String(w.pos).trim()))warn.push("詞性的寫法不常見，請確認");
  if(!lex)warn.push("英文詞表沒有載入，拼字沒有檢查");
  else{const a=unknownWords(en.replace(/wh-疑問詞/g,""),lex);if(a.length)warn.push(`英文「${a.join("、")}」不在英文詞表裡，可能拼錯`);
    const b=unknownWords(ex,lex,{sentence:true}).filter(x=>!a.some(y=>y.toLowerCase()===x.toLowerCase()));if(b.length)warn.push(`例句裡的「${b.join("、")}」不在英文詞表裡，可能拼錯`)}
  return warn}
