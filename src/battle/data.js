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
 {id:"c7",name:"七曜天地斬",cost:0,chain:["slash","gale","fire","ice","thunder","meteorEnd","holy"],stages:[[10],[6,6,8],[18],[5,5,5,5,8],[26],[50],[150]],times:[5,5,4,4,4,3,3]},
 // 回血招式：放在最後（索引 9），連招維持 7–9 號；鍵盤用 H。heal＝回復量、perFoe＝每隻怪物最多用幾次（換下一隻怪物重算）
 {id:"heal",name:"治癒之光",cost:14,move:"heal",heal:35,perFoe:2,d:"魔法・回復 HP"}];
// 七曜天地斬：發動時連擊必定 ≥7（傷害 ×1.5）。前六式合計 152×1.5＝230，打不死滿血的魔王（240），
// 重心放在最後的聖光劍（150×1.5），所以七式都播得到。
export const MOVE_NAMES={slash:"普通斬擊",gale:"疾風連斬",fire:"火球術",thunder:"雷霆之矛",ice:"冰晶風暴",meteorEnd:"流星斬",holy:"聖光審判劍"};
export const QUESTION_MS=10000; // 一般題的能量計時（不會超時）
export const STORY=["這裡是劍與魔法的大陸——艾爾文斯。","千年前，史萊姆魔王偷走了「詞語之力」，把它封進了怪物的身體裡。","從此，劍失去了鋒芒，魔法也失去了咒文。","你是見習魔劍士。只要正確說出單字，就能取回力量——","以劍斬擊，以魔法吟唱。踏上旅程吧！"];

/* ---------- 魂系模式 ---------- */
export const SOUL={
  windowMs:6000,       // 舊欄位（顯示用預設值）；實際每回合從 windowRange 抽
  windowRange:[5000,7000], // 玩家回合的攻擊時間每回合 5–7 秒不固定（只在題目顯示中倒數）
  minCostMs:2000,      // 每一題至少消耗這麼多攻擊時間（答得再快，一回合也只有 3 題）
  missPenaltyMs:1000,  // 攻擊回合答錯，多扣的攻擊時間
  // ---- 弱點擊破：同一個攻擊回合連續 weakN 題都在「攻擊時間的 25% 內」答對（＝剩 75% 以上就完成），立刻追加一套短時間連斬 ----
  weakAt:.4, weakN:3, weakHits:[3,3,3,3,6], weakAtb:0,
  // ---- 玩家攻擊（2026-11-26 改）：不能選招，每答對一題自動出連斬，段數看答題速度 ----
  // 「完美」＝還剩 perfectAt 以上的時間就答完（ms ≤ (1−perfectAt)×時限）。攻擊題的時限＝這回合的攻擊時間
  perfectAt:.6,
  chainAt:[.6,.3],     // 剩 60% 以上＝5 連斬、剩 30% 以上＝4 連斬、其他＝3 連斬
  chainHits:{3:[5,5,7],4:[4,4,5,7],5:[4,4,4,4,6]},
  // 斬擊也要答題：連斬第 2 刀起，每一刀出一題「這一局答對過的字」（加固記憶），答對才砍得下去，答錯或超時連斬中斷
  slashLimitMs:4000,
  // ---- 閃避時限：每一擊 2–5 秒不固定（依招式種類抽範圍，再乘階段與動態難度，最後夾在 dodgeClamp 內） ----
  dodgeRange:{base:[2000,5000],dash:[2000,3000],danger:[2000,3500],ambush:[2000,4000]},
  dodgeClamp:[2000,5000],
  // ---- 突擊：連續 assaultN 次「快閃避」（答對且用不到時限的 assaultFast）＝看穿攻勢，打斷 Boss 剩下的攻擊，換你連續攻擊 assaultQs 題 ----
  assaultN:3, assaultFast:.4, assaultQs:3, assaultRange:[2000,5000], assaultDmg:[7,7,13],
  healOnKill:35,       // 打倒 Boss 回復的 HP（有藥壺之後從 40 降到 15；突襲／破綻變多之後拉回 30）
  atbMax:3,
  staminaMax:100,
  staminaTurn:25,      // 每次輪到玩家回復（連擊改版：敵人回合題數變多，從 15 提高）
  staminaHit:8,        // 攻擊回合每答對一題回復
  staminaParry:10,     // 彈反回復
  dodgeCost:22,        // 翻滾閃避消耗
  blockCost:50,        // 答錯／超時但耐力足夠：硬擋下來要消耗的耐力（耐力不足才吃全額傷害）
  blockRate:.55,       // 硬擋承受 55% 傷害
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
  paceWindow:8, paceMin:3, paceCenter:2.5, paceSpan:1.6, wrongAs:6,
  limitSwing:.35,      // 時限最多縮短／放寬 35%
  perfectSwing:300,    // 彈反判定最多 ±0.3 秒
  tightAt:.8, perfectTight:420, // d 超過 tightAt 後彈反門檻再收緊，d=1 時多收 0.42 秒（1.5−0.3−0.42＝0.78 秒）：高手也會有一兩成落到翻滾
  foeDmgSwing:1.5,     // Boss 傷害 ×(1＋foeDmgSwing×max(0,d))：只跟動態難度掛勾的壓力（連擊／藥壺／突襲改版後用模擬定在 0.75，熟練約 90%）
  dmgBonus:0,          // 高難度時的玩家傷害加成（已取消：答得快本來就打得多）
  foeEase:.9,          // 答得慢（d<0）時 Boss 傷害 ×(1−foeEase×|d|)：只幫跟不上的人，熟練以上不受影響
  extraAt:.6,          // d 超過這個值，Boss 多出手一次（extraSeg：改成連擊多一段，沒有連擊才多一記單擊）
  extraSeg:true,
  easeDown:false,      // true＝d 低於 −extraAt 時少出手一次（已關閉：亂點會被判成「很慢」而佔到便宜）
  // ---- 敵人回合的招式種類（壓迫感：連擊、延遲、突進、必殺） ----
  comboLimit:[1,.85,.7,.7], // 連擊每一段的時限倍率（逐段縮短；彈反門檻也跟著縮）
  comboDmg:.3,          // 連擊每一段的傷害倍率（段數多，單段輕一點）
  chainParryDmg:3,     // 連擊中段彈反：不衝上去反擊，只彈刀造成的小傷害（最後一段才完整反擊）
  delayLockMs:[700,900], // 延遲攻擊：題目先出現、選項鎖住的時間＝Delayed 片段舉起後的停頓（約 0.8 秒，畫面依實際值微調停頓速度）
  delayLimitMul:.85,   // 延遲攻擊解鎖後的時限倍率（鎖住期間已經能讀題）
  delayDmg:1.1,
  flinchMs:400,        // 延遲攻擊鎖住期間亂點：每點一下作答時間 +0.4 秒（最多算 2 下）
  dashLimitMul:.6,     // 突進：時限只有 60%，不能彈反（答得再快也只是翻滾）
  dashDmg:.7,
  dangerLimitMul:.9,   // 必殺（第二階段起）：答對才閃得掉，答錯／超時不能硬擋、吃全額
  dangerDmg:1.25,
  // ---- 突襲（攻擊回合中 Boss 搶先出手，每個玩家回合最多 ambushPerTurn 次；大招不會被打斷） ----
  ambushBase:[.09,.10,.11,.12,.14], // 每次判定（答一題／出一招／喝一次藥）的基本機率，依第幾隻 Boss
  ambushPhaseMul:1.5,  // 第二階段起
  ambushSlackMs:1500,  // 作答或猶豫超過這個時間的部分才加機率
  ambushPerSec:.05,    // 每多拖 1 秒 +5%
  ambushFlask:.15,     // 喝藥時額外 +15%
  ambushMax:.45,
  ambushPerTurn:2,     // 每個玩家回合最多被突襲幾次
  // ---- 破綻（攻擊回合答錯：Boss 立刻衝上來把你打倒，不能閃、不能擋） ----
  knockMul:.25,        // 傷害＝Boss 攻擊力×階段倍率×動態難度×這個倍率
  knockMs:600,         // 倒地爬起來額外花掉的攻擊時間
  ambushLimitMul:.9,   // 突襲閃避題的時限倍率（突襲變頻繁之後從 .75 放寬）
  ambushResumeMs:1000, // 撐過突襲後攻擊時間還有這麼多才回到攻擊回合，不然直接進敵人回合（剩 0.1 秒回去也答不了）
  // ---- 藥壺（戰鬥中回血） ----
  flaskStart:3,        // 開場幾壺
  flaskMax:3,          // 上限（打倒 Boss 補 flaskOnKill 壺，不會超過上限）
  flaskOnKill:1,
  flaskHeal:.4,        // 答對喝下回復最大 HP 的 40%
  flaskBelow:.75,      // HP 低於 75% 才能喝（滿血時指令列不會一直跳出來）
  flaskCostMs:2500,    // 喝藥至少花掉的攻擊時間
  flaskPunishMs:2500,  // 喝完攻擊時間剩不到這麼多：Boss 趁空檔逼近，下個敵人回合先出一記突進
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
// phases：血量比例降到 at 以下就進入該階段（atkMul 攻擊倍率、extra 多出手次數、limitMul 閃避時限倍率、danger 該回合最後一招改成必殺的機率）
// kit：各階段的招式比重 {single 單擊, combo 連擊, delayed 延遲, dash 突進}；combo：各階段連擊段數 [最少, 最多]；names：各招式名
// attacks＝每個敵人回合出幾「招」（連擊一招算多題）
export const SOUL_BOSSES=[
 {id:"sentinel",name:"腐朽守門騎士",lv:5,hp:40,atk:10,move:"鏽戟橫掃",attacks:1,limitMs:4000,model:"boss_sentinel",arena:"gate_ruins",
  names:{combo:"鏽戟三連刺",delayed:"沉重高舉斬",dash:"盾牌衝撞"},
  kit:[{single:.6,dash:.2,delayed:.2},{single:.3,combo:.4,dash:.15,delayed:.15}],combo:[[3,3],[3,4]],
  phases:[{at:.5,name:"根鬚暴走",atkMul:1.15,extra:0,limitMul:.95,move:"根鬚纏擊",danger:.35}]},
 {id:"gargoyle",name:"教堂石像鬼",lv:10,hp:95,atk:13,move:"俯衝利爪",attacks:1,limitMs:4000,model:"boss_gargoyle",arena:"cathedral_roof",
  names:{combo:"狂亂爪擊",delayed:"懸停俯衝",dash:"石翼突襲"},
  kit:[{single:.35,combo:.3,dash:.2,delayed:.15},{single:.15,combo:.45,dash:.2,delayed:.2}],combo:[[3,4],[3,5]],
  phases:[{at:.5,name:"石翼狂嘯",atkMul:1.15,extra:1,limitMul:.95,move:"碎石吐息",danger:.5}]},
 {id:"priest",name:"霜冠祭司",lv:16,hp:110,atk:13,move:"霜槍突刺",attacks:1,limitMs:4000,model:"boss_priest",arena:"frozen_chapel",
  names:{combo:"霜槍連刺",delayed:"寒冰蓄勢",dash:"冰面滑襲"},
  kit:[{single:.3,combo:.35,dash:.15,delayed:.2},{single:.15,combo:.45,dash:.2,delayed:.2}],combo:[[3,4],[4,5]],
  phases:[{at:.5,name:"永凍禱詞",atkMul:1.2,extra:0,limitMul:.9,move:"冰棺降臨",danger:.5}]},
 {id:"executioner",name:"暗影行刑者",lv:22,hp:135,atk:14,move:"斷頭斧斬",attacks:1,limitMs:4000,model:"boss_executioner",arena:"execution_yard",
  names:{combo:"處刑連斬",delayed:"高舉斷罪",dash:"影步突進"},
  kit:[{single:.25,combo:.4,dash:.15,delayed:.2},{single:.1,combo:.5,dash:.2,delayed:.2}],combo:[[3,5],[4,5]],
  phases:[{at:.5,name:"處刑之舞",atkMul:1.2,extra:1,limitMul:.9,move:"影分身處刑",danger:.6}]},
 {id:"devourer",name:"噬語魔王",lv:30,hp:180,atk:15,move:"噬語巨劍",attacks:2,limitMs:3600,model:"boss_devourer",arena:"throne_of_words",boss:true,
  names:{combo:"吞字連斬",delayed:"沉默之劍",dash:"虛空突刺"},
  kit:[{single:.25,combo:.4,dash:.15,delayed:.2},{single:.1,combo:.5,dash:.2,delayed:.2},{single:.1,combo:.5,dash:.2,delayed:.2}],combo:[[3,5],[4,5],[4,5]],
  phases:[{at:.66,name:"吞噬詞語",atkMul:1.15,extra:0,limitMul:.95,move:"詞語風暴",danger:.5},{at:.33,name:"終焉咒言",atkMul:1.3,extra:1,limitMul:.9,move:"終焉之言",danger:1}]}];
// 練等：每打倒一隻 Boss（最後一隻除外）從 3 個裡選 1 個強化，只在這一局有效。max＝最多疊幾層
export const SOUL_PERKS=[
 {id:"time",name:"時間延長",d:"攻擊時間 +1 秒",max:2},
 {id:"dodgeT",name:"閃避延長",d:"每次閃避時限 +0.5 秒",max:2},
 {id:"flask",name:"回復藥水",d:"立刻 +2 壺藥，藥壺上限 +1",max:3},
 {id:"brew",name:"藥效強化",d:"喝藥多回復 15% 最大 HP",max:2},
 {id:"vigor",name:"生命強化",d:"最大 HP +20，並回復 20",max:2},
 {id:"stamina",name:"耐力強化",d:"耐力上限 +25，每回合多回 8 耐力",max:2},
 {id:"guard",name:"鐵壁",d:"硬擋、格擋承受的傷害再減 40%",max:1},
 {id:"blade",name:"利刃",d:"所有攻擊傷害 +15%",max:3},
 {id:"quick",name:"連斬精通",d:"連斬段數的判定各放寬 10%（更容易打出 5 連斬）",max:2},
 {id:"parry",name:"彈反大師",d:"彈反判定放寬 10% 時間",max:2},
 {id:"counter",name:"反擊強化",d:"彈反後的反擊、彈刀傷害 +60%",max:2},
 {id:"alert",name:"警覺",d:"被突襲的機率 −40%",max:1},
 {id:"steady",name:"穩如泰山",d:"破綻被打倒的傷害減半、不再多扣時間",max:1},
 {id:"weak",name:"弱點看破",d:"弱點擊破只要連續 2 題完美",max:1},
 {id:"assault",name:"突擊強化",d:"快閃避 2 次就能突擊，突擊多 1 題",max:1}];
export const SOUL_STORY=["詞語之火熄滅之後，王國只剩下灰與低語。","被奪走名字的騎士們，仍守著早已無人通過的門。","你是最後一名記得單字的人。","每答出一個字，劍就多一分重量；每遲疑一瞬，死亡就近一步。","穿過廢墟，討伐噬語魔王。"];
