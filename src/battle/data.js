// 戰鬥資料表（與畫面無關）。model 欄位是之後 3D 場景要載入的模型代號。
export const PLAYER_HP=100;
export const MAXEN=40;
export const HEAL_ON_KILL=25;

/* ---------- 打怪模式 ---------- */
export const MON=[
 {id:"slime",name:"字母史萊姆",lv:3,hp:70,atk:12,move:"黏液衝撞",model:"slime_green",scale:.78},
 {id:"bat",name:"文法蝙蝠",lv:7,hp:100,atk:15,move:"文法超音波",model:"bat_orange",scale:1},
 {id:"slimeIce",name:"冰晶史萊姆",lv:12,hp:130,atk:18,move:"冰霜衝撞",model:"slime_ice",scale:.88},
 {id:"batShadow",name:"暗影蝙蝠",lv:18,hp:170,atk:22,move:"暗影咬擊",model:"bat_shadow",scale:1.05},
 {id:"slimeKing",name:"史萊姆魔王",lv:30,hp:240,atk:28,move:"魔王壓頂",model:"slime_king",scale:1.5,boss:true}];
// move：3D 場景要播的招式動畫代號
export const SKILLS=[
 {id:"slash",name:"普通斬擊",cost:0,move:"slash",hits:[8],d:"劍技・不耗能量"},
 {id:"gale",name:"疾風連斬",cost:10,move:"gale",hits:[10,10,14],d:"劍技・三連斬"},
 {id:"fire",name:"火球術",cost:14,move:"fire",hits:[44],d:"魔法・火焰爆裂"},
 {id:"thunder",name:"雷霆之矛",cost:18,move:"thunder",hits:[62],d:"魔法・天降落雷"},
 {id:"ice",name:"冰晶風暴",cost:22,move:"ice",hits:[15,15,15,15,24],d:"魔法・五段冰雨"},
 {id:"holy",name:"聖光審判劍",cost:28,move:"holy",hits:[135],d:"終極奧義"},
 {id:"c3",name:"流星三連斬",cost:0,chain:["slash","gale","meteorEnd"],stages:[[20],[10,10,14],[56]],times:[5,4,3]},
 {id:"c5",name:"魔劍五連舞",cost:0,chain:["slash","gale","fire","ice","meteorEnd"],stages:[[20],[10,10,14],[34],[10,10,10,10,16],[66]],times:[5,5,4,4,3]},
 {id:"c7",name:"七曜天地斬",cost:0,chain:["slash","gale","fire","ice","thunder","meteorEnd","holy"],stages:[[10],[6,6,8],[18],[5,5,5,5,8],[26],[50],[150]],times:[5,5,4,4,4,3,3]}];
// 七曜天地斬：發動時連擊必定 ≥7（傷害 ×1.5）。前六式合計 152×1.5＝230，打不死滿血的魔王（240），
// 重心放在最後的聖光劍（150×1.5），所以七式都播得到。
export const MOVE_NAMES={slash:"普通斬擊",gale:"疾風連斬",fire:"火球術",thunder:"雷霆之矛",ice:"冰晶風暴",meteorEnd:"流星斬",holy:"聖光審判劍"};
export const QUESTION_MS=10000; // 一般題的能量計時（不會超時）
export const STORY=["這裡是劍與魔法的大陸——艾爾文斯。","千年前，史萊姆魔王偷走了「詞語之力」，把它封進了怪物的身體裡。","從此，劍失去了鋒芒，魔法也失去了咒文。","你是見習魔劍士。只要正確說出單字，就能取回力量——","以劍斬擊，以魔法吟唱。踏上旅程吧！"];

/* ---------- 魂系模式 ---------- */
export const SOUL={
  windowMs:10500,      // 玩家回合的攻擊時間（只在題目顯示中倒數）；10.5 秒＝每題 2.5 秒的玩家答得到第 4 題
  minCostMs:2500,      // 每一題至少消耗這麼多攻擊時間（答得再快，一回合也只有 4 題）
  missPenaltyMs:2000,  // 攻擊回合答錯，多扣的攻擊時間
  healOnKill:40,       // 打倒 Boss 回復的 HP
  atbMax:3,
  staminaMax:100,
  staminaTurn:15,      // 每次輪到玩家回復
  staminaHit:8,        // 攻擊回合每答對一題回復
  staminaParry:10,     // 彈反回復
  dodgeCost:20,        // 翻滾閃避消耗
  blockCost:50,        // 答錯／超時但耐力足夠：硬擋下來要消耗的耐力（耐力不足才吃全額傷害）
  blockRate:.5,        // 硬擋承受 50% 傷害
  grazeCost:5,
  guardRate:.3,        // 格擋承受 30% 傷害（答對但耐力不足以翻滾、或答錯但耐力足以硬擋）
  grazeRate:.5,        // 太慢才答對：擦傷，承受 50% 傷害
  slowAt:.8,           // 超過時限的 80% 才答對算「太慢」
  perfectMs:1500,      // 彈反（完美閃避）基準秒數
  quickMs:1500,        // 攻擊回合在這個時間內答對，追加一記迅擊
  quickDmg:4,
  counterDmg:10,
  minLimitMs:1500,
  // 動態難度：看最近 N 題的平均作答秒數（答錯算 wrongAs 秒）
  paceWindow:8, paceMin:3, paceCenter:3.2, paceSpan:1.6, wrongAs:6,
  limitSwing:.35,      // 時限最多縮短／放寬 35%
  perfectSwing:300,    // 彈反判定最多 ±0.3 秒
  tightAt:.8, perfectTight:420, // d 超過 tightAt 後彈反門檻再收緊，d=1 時多收 0.42 秒（1.5−0.3−0.42＝0.78 秒）：高手也會有一兩成落到翻滾
  foeDmgSwing:1,       // Boss 傷害 ×(1＋foeDmgSwing×max(0,d))：只跟動態難度掛勾的壓力（模擬：0.3 對熟練玩家幾乎沒影響，1.0 才把熟練壓到約九成）
  dmgBonus:0,          // 高難度時的玩家傷害加成（已取消：答得快本來就打得多）
  extraAt:.6,          // d 超過這個值，Boss 多出手一次
  easeDown:false,      // true＝d 低於 −extraAt 時少出手一次（已關閉：亂點會被判成「很慢」而佔到便宜）
};
export const SOUL_CMDS=[
 {k:1,id:"slash",name:"斬擊",bars:1,move:"slash",hits:[12]},
 {k:2,id:"gale",name:"疾風連斬",bars:2,move:"gale",hits:[11,11,14]}];
// 3 格 ATB 的大招，依第幾隻 Boss 輪替
export const SOUL_BIG=[
 {name:"雷霆之矛",move:"thunder",hits:[72]},
 {name:"冰晶風暴",move:"ice",hits:[15,15,15,15,22]},
 {name:"流星斬",move:"meteorEnd",hits:[84]},
 {name:"火球術",move:"fire",hits:[76]},
 {name:"聖光審判劍",move:"holy",hits:[115]}];
// phases：血量比例降到 at 以下就進入該階段（atkMul 攻擊倍率、extra 多出手次數、limitMul 閃避時限倍率）
export const SOUL_BOSSES=[
 {id:"sentinel",name:"腐朽守門騎士",lv:5,hp:60,atk:10,move:"鏽戟橫掃",attacks:1,limitMs:4000,model:"boss_sentinel",arena:"gate_ruins",
  phases:[{at:.5,name:"根鬚暴走",atkMul:1.15,extra:0,limitMul:.95,move:"根鬚纏擊"}]},
 {id:"gargoyle",name:"教堂石像鬼",lv:10,hp:200,atk:13,move:"俯衝利爪",attacks:1,limitMs:4000,model:"boss_gargoyle",arena:"cathedral_roof",
  phases:[{at:.5,name:"石翼狂嘯",atkMul:1.15,extra:1,limitMul:.95,move:"碎石吐息"}]},
 {id:"priest",name:"霜冠祭司",lv:16,hp:230,atk:13,move:"霜槍連刺",attacks:2,limitMs:4000,model:"boss_priest",arena:"frozen_chapel",
  phases:[{at:.5,name:"永凍禱詞",atkMul:1.2,extra:0,limitMul:.9,move:"冰棺降臨"}]},
 {id:"executioner",name:"暗影行刑者",lv:22,hp:270,atk:14,move:"斷頭斧斬",attacks:2,limitMs:4000,model:"boss_executioner",arena:"execution_yard",
  phases:[{at:.5,name:"處刑之舞",atkMul:1.2,extra:1,limitMul:.9,move:"影分身處刑"}]},
 {id:"devourer",name:"噬語魔王",lv:30,hp:350,atk:15,move:"噬語巨劍",attacks:3,limitMs:3600,model:"boss_devourer",arena:"throne_of_words",boss:true,
  phases:[{at:.66,name:"吞噬詞語",atkMul:1.15,extra:0,limitMul:.95,move:"詞語風暴"},{at:.33,name:"終焉咒言",atkMul:1.3,extra:1,limitMul:.9,move:"終焉之言"}]}];
export const SOUL_STORY=["詞語之火熄滅之後，王國只剩下灰與低語。","被奪走名字的騎士們，仍守著早已無人通過的門。","你是最後一名記得單字的人。","每答出一個字，劍就多一分重量；每遲疑一瞬，死亡就近一步。","穿過廢墟，討伐噬語魔王。"];
