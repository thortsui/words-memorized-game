# 感覺（Feel）報告：打擊感分級

## 做了什麼
- 新檔 `src/battle/view3d/feel.js`：hitstop／震屏／鏡頭衝擊／慢動作全部集中在一張 `FEEL` 表（S0–S7，照 design.md §6）＋少數派生事件（`EXTRA`）。
- `soulScene.js` 原本零散的 `eng.hitStop`／`eng.shake`／`eng.slowmo` 數字改成呼叫 feel 的分級函式（只換呼叫、不動流程；`bossPhase()` 沒碰）。
- `engine.js` 沒改（現有的 hitStop 取最大值、shake 支援 `dir`、slowmo、rumble 已經夠用）。

## 參數表（`FEEL`，單位：hitstop ms；震屏＝幅度／秒／頻率；鏡頭＝推 m、側移 m、FOV 度、仰角度；慢動作＝倍率／ms）
| 等級 | 事件 | Hitstop | 震屏 | 鏡頭 | 慢動作 |
|---|---|---|---|---|---|
| S0 | Boss 腳步（× 距離·體型） | 0 | .012／.20／9 | — | — |
| S1 | 連斬 1–2 段、格擋、彈刀、輕招 | 60 | .025／.22／20 | 推 .15 回彈 | — |
| S2 | 連斬 3–4 段、玩家受擊（hit／graze） | 80 | .045／.28／18 | 推 .25、FOV −1 | — |
| S3 | 連斬最後一刀、重招、玩家重受擊（必殺／破綻倒地） | 110 | .07／.35／14（受擊時方向＝Boss→主角） | 推 .4、FOV −2、偏向命中側 .18 | .5／200（只限完美連斬的最後一刀） |
| S4 | 彈反、弱點擊破、突擊 | 130 | .06／.30／24 | 側移 .6（彈反 ×.6，場景本身已有 csTo 側移）、FOV −2 | 彈反 .22／700；連擊中段彈反、弱點擊破、突擊 .4／350 |
| S5 | 擊殺 Boss 的那一刀 | 160 | .09／.45／12 | 仰角 20°、FOV −4、推 .2 | .25／700 |
| S6 | 階段爆發（給 phaseShow 用 `feel.phase()`，本人未掛） | 0 | .16／.9／11 | — | 爆發前 .35／150 |
| S7 | Boss 化灰 | 200 | .05／.5／10＋rumble .04／1.2 | 仰角 14°、升高 .8、後拉 .6、停 .5 s | .5／900（倒下開頭另有 `fall()` .5／350） |

派生：`dodge`（翻滾閃開，Boss 砸地）0 ms／.045·.25·14／側移 −.3；`ambush`（突襲切到面前）100 ms／.07·.35·12／推 .45 FOV −3；`land`（登場站定）.08·.6·10；`loom`（Boss 踏前／衝到近身）.03·.3·8；`pressure`（一般蓄力：推 .35 FOV −3）、`dangerPressure`（必殺／突襲：推 .55 FOV −5 仰 −4），蓄力期間慢慢壓上去、維持到玩家作答後下一個回饋事件才放開（最多 limit+6 s 自動放開）。

規則落實：
- hitstop 取最大值（頓格中再來一次只延長差額）；300 ms 內最多 2 次；一套連斬（`skill` 事件或 i=0 開始）預算 450 ms。5 連斬實測 60+60+80+80+110＝**390 ms**；第 5 刀擊殺時 60+60+80+80+160＝440 ms。
- 完美連斬最後一刀：慢放 .5／200＋色差＋金閃（後兩者走 screen2，見下）。
- 彈反「金色節奏」：相擊瞬間 S4，140 ms 後第二拍（小震 .03／.18／26＋金閃）。
- 受擊：方向性震屏（`eng.shake` 的 `dir`，世界方向轉成相機座標）＋頓格；重受擊另加色差與紅閃（≤ .3）。
- `eng.rm`：鏡頭推拉全部取消、震屏 ×.4（引擎在 rm 下本來就不震、也不 hitStop，等於更保守）；慢動作保留——引擎 rm 下 `slowmo` 直接 return，所以 feel 在 rm 時改用 `eng.fast`（<1）自己做，並且不和「跳過演出」的 `eng.fast=10` 搶（看到被改就放手）。
- 手機（粗指標或短邊 < 600）：震屏 ×.65、推拉 ×.8，120 ms 內連續震動第二下 ×.6。
- 閃光走 §5.4：白 ≤ .15、紅 ≤ .3、每秒 ≤ 3 次（feel 內限流）。

## 答題計時不受影響
`controller.js` 的 `timer()` 用 `performance.now()` 計時；hitstop／慢動作只改引擎的遊戲時間（`eng.time`、補間）。頓格只會讓「答完之後的演出」晚一點結束（下一題出現前），倒數本身是真實時間。蓄力時的威脅環也是用 `rdt`（真實時間）。

## screen2（畫面工程師）
目前還沒有 `screen2.js`。feel 用 `import.meta.glob('./screen2.js')` 可選載入（檔案不存在時是空物件、不報錯），並依序找 `ctx.screen2()`、`eng.screen2`、模組具名匯出，呼叫：
- `flash({color, opacity, dur})`（feel 已先套 §5.4 上限）
- `pulseChromatic(k, dur)`（rm 時不呼叫）
請畫面工程師照這兩個簽名提供，或告訴我實際簽名我來改。

## 掛鉤位置（`soulScene.js`，皆為單行替換）
- import 一行；`camKick` 下一行 `const feel=createFeel(eng,{focus:…})`
- Boss `onStep` → `feel.step()`；AI 衝到近身、`enemyTurn`、`flaskPunish` → `feel.loom()`；`bossEnter` 站定 → `feel.land()`
- `impact()` → `feel.strike(p,{power,heavy,dir})`（取代 hitStop／shake／kill slowmo）
- `skill` → `feel.combo(p)`（記完美、重置預算）
- `weakBreak` → `feel.breakFoe("weakBreak")`；`assault` → `feel.breakFoe("assault")`
- `ambush` → `feel.ambush(dir)`＋`feel.pressure("dangerPressure")`；`telegraph` 蓄力 → `feel.pressure(...)`
- `parry` → `feel.parry({chain,dir})`（取代 shake／hitStop／兩種 slowmo）
- `dodge` → `feel.dodge()`；`guard` → `feel.guard(dir)`；`playerHit` → `feel.hurt(p,dir)`
- `faint` → `feel.fall()`（開頭）、`feel.die()`（化灰瞬間）
- 保留沒改：`roar` 與必殺蓄力的 `eng.rumble`（氛圍性持續晃動）、`lose` 的 slowmo、`bossPhase()`（動畫的）。

## 驗證
- 自動玩（手機 390×700，Playwright，`scratchpad/pt/feeltest.mjs`，dev server 5184、關 HMR 以免別人改檔讓頁面重整）：64 題、0 pageerror。`window.__feel.log`（DEV 才掛）統計：S1 27、S2 22、S3 11、S4 11（彈反 8／弱點 1／突擊 1）、S5 4、S7 4、ambush 1、pressure 8。
  - 每套 5 連斬 hitstop 合計 390 ms（完美最後一刀帶 .5／200）；擊殺收尾那套 360–440 ms；弱點擊破 gale 5 段 390 ms。全部 ≤ 450。
  - 格擋（S1 60）緊接受擊 → 受擊只延長 1–2 ms（取最大值不疊加，正確）。
  - CDP screencast 連拍：`scratchpad/pt/feel-390/{chain,parry,hurt}/`（每張檔名含毫秒），彈反對照表 `feel-390/parry_sheet.jpg`。
- `prefers-reduced-motion`（emulateMedia reduce）自動玩 31 題：0 pageerror、0 console error，五隻 Boss 照常推進。
- `URL0=http://127.0.0.1:5184/ node verify.mjs soul`：五隻全打完（end=true），pageerror 0、console error 0。
- `node tests/check.mjs` 全過；`node tests/sim/soul-sim.mjs`：高手 100%／熟練 65%／普通 8%（模擬本身不經過畫面層，數字與規則無關，屬隨機誤差範圍）。

## 已知問題／給別人
- 彈反那一下手機畫面幾乎整片被金白光蓋住約 0.5 s（連拍 `parry_sheet.jpg` 下排），來源是 fx／bossfx 的 `fx.flash(size 1.3)`＋火花在近距離被放大，不是 feel（screen2 尚不存在）。建議特效端在手機上縮小彈反閃光（§5.4）。
- 「命中音效早 40 ms」需要改 moves.js／音效呼叫時機，不在我的檔案，未做。
- S6 只提供 `feel.phase()`，由動畫決定要不要在 `bossPhase()`／phaseShow 呼叫。
