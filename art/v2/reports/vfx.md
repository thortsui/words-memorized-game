# 特效（VFX）報告：墨與金

負責檔案：`src/battle/view3d/fx.js`、`src/battle/view3d/bossfx.js`、新檔 `src/battle/view3d/vfx2.js`。
`soulScene.js` 只加了掛鉤：import 一行、建立 `vfx` 一行、六個事件點各一個呼叫（`vfx.hitBoss`、`vfx.parry`、`vfx.dodge`、`vfx.guard`、`vfx.hurt`、`vfx.bossDeath`），最後一行 `vfx.wrap(H)`。沒有動 `bossPhase()`，也沒有改規則和數值。

## 新的基礎元件（fx.js，只在魂系生效；打怪模式不受影響）
- **粒子圖集**：4×4 格，用 canvas 產生，256²。內容有 8 個原創符字（不可讀）、墨滴、墨潑、金箔、筆觸、書頁、星芒、灰燼、小圓相。粒子 `kind` 4–19 會從圖集取圖，小數部分當作旋轉角；`fx.K` 有對照表。
- **筆刷刀光 `fx.brush`**：特製的著色器，筆畫頭粗尾細，帶飛白鬃毛紋。底下一層一般混合的墨色，上面一層加色的主色和白熱芯，揭示後尾端先散成墨絲再消失。可以是弧線，也可以是直線（`straight`）。
  魂系的 `fx.slash` 全部改走筆刷：玩家刀光原本是淡藍白 `0xdfe8ff`，自動換成金色 `#ffd27a`；Boss 刀光用 Boss 主色加墨。
- `fx.enso`：圓相，一筆畫出的圓，依角度逐筆顯示，可以面向鏡頭或貼在地上。
- `fx.seal`：地面的印章符紋圈，墨色底加主色，T 秒內逐筆畫出。
- `fx.decal`：墨潑、裂紋貼片。
- `fx.inkVeil`：全畫面墨色收縮。
- `fx.afterimage`：殘影。用 SkeletonUtils 複製當下姿勢，幾何共用，同時最多 6 個。
- **閃光安全**：魂系的 `pulseVig` 白閃上限 0.15、紅閃上限 0.3（§5.4）。`flash` 光暈會依離鏡頭的距離限制大小（直式畫面 ≤ 畫面高 16%），不透明度 ≤ 0.55，時長 ≤ 0.18 秒。同一點一次爆出 30 顆以上的加色粒子會自動壓暗，火花條 HDR 上限 2.4。這幾項是在處理 lead 轉來的「手機彈反閃光蓋滿畫面」問題，之後在 390 寬重拍，光暈只剩主角周圍。

## design.md §4 對照
| # | 項目 | 做法 | 位置 |
|---|---|---|---|
| 1 | 一般斬 | 金色筆刷刀光＋金火花 15＋短白閃 | fx.slash／vfx2.hitBoss |
| 2 | 連斬 | 段數越高越粗越亮；第 3 段起墨滴飛濺（第 4 段起加地面墨點）；第 5 段金色收鋒大弧 | vfx2.slashStyle／hitBoss |
| 3 | 完美斬 | 0.05 秒後一道金色細線「一閃」＋金箔 30 片緩慢飄落＋「完美」字 | hitBoss |
| 4 | 終結斬 | 貫穿畫面的金墨橫劃兩道＋金與墨粒子 100＋金圓相＋地面墨暈 | vfx2.finisher |
| 5 | 彈反 | 金色圓相＋交叉金筆＋Boss 武器尖端迸出主色碎光（「彈反」字沿用場景原本的） | vfx2.parry |
| 6 | 閃避（P1） | 翻滾起點留墨色殘影（主角姿勢複製）＋塵土弧；完美閃避（≤ 35% 時限）加金色地面漣漪＋「見切」 | vfx2.dodge |
| 7 | 受擊 | 暗紅墨潑貼片＋暗紅墨滴（紅暗角、閃紅沿用場景原本的）；必殺命中加地面暗紅墨 | vfx2.hurt |
| 8 | 格擋（P1） | 鐵灰火花條＋短白環 | vfx2.guard |
| 9 | 突襲預警 | 落點墨圈＋主色圓相＋眼睛紅閃星芒 | vfx2.ambushWarn |
| 10 | 蓄力預警 | 腳下細紅圓相；紅色筆觸粒子往**武器尖端**聚（Tip_Weapon → 武器骨 → 右手） | bossfx.charge |
| 11 | 必殺預警 | 大型墨紅印章符紋圈逐筆畫出＋紅光柱＋Boss 背後主色光柱（暗角與橫幅沿用場景） | bossfx.charge |
| 12 | 延遲解鎖（P1） | 武器尖端白色星芒＋閃光 | vfx2.tipDing |
| 13 | sentinel | 鏽戟橫掃（鏽色筆刷橫弧＋鏽屑＋孢子）／根鬚纏擊（3–5 根，間隔 0.05 秒，墨點、木屑、苔綠孢子）／盾牌衝撞（木屑＋塵牆） | bossfx |
| 14 | gargoyle | 狂亂爪擊（三道平行爪痕）／俯衝利爪（翼尖兩道橘痕）／碎石吐息（約 40 顆燒紅碎石，分 4 波＋黑煙） | bossfx |
| 15 | priest | 霜槍突刺（直線冰晶筆刷）／冰面滑襲（地面結霜軌跡）／霜環／冰棺降臨（4 根冰柱落下，0.6 秒後碎裂） | bossfx |
| 16 | executioner | 斷頭斧斬（垂直紫墨巨刃＋地面裂痕）／影步（2–3 個紫色殘影）／影分身處刑（左右分身＋各一道紫刃，0.7 秒後散成墨滴） | bossfx |
| 17 | devourer | 噬語巨劍（紅黑雙層刀光＋符字）／詞語風暴（30 片燒紅邊書頁旋轉，InstancedMesh 一次 draw call）／終焉之言（紅字環擴到場邊＋全畫面墨收縮） | bossfx |
| 18 | Boss 受擊（P1） | 主色碎光＋材質碎屑（鏽／石／冰／墨／書頁） | hitBoss |
| 19 | 弱點擊破（P1） | 金色裂紋擴散＋金箔＋「擊破」 | vfx2.weakCrack |
| 21 | 常駐 aura（P1） | 主色餘燼 ≤ 6 顆/秒＋淡墨煙；三階（phase ≥ 2）腳下兩層反向旋轉的墨潮環 | bossfx.aura |
| 22 | Boss 死亡 | 主色轉金；1.6 秒內身體位置湧出金色符字與墨煙上飄，最後一點金光沿弧線飛到主角劍尖，劍尖閃金、出金圓相 | vfx2.bossDeath |
| 23 | 喝藥（P2） | 淡綠＋金雙螺旋上升 | vfx2.drinkSpiral |
| 24 | 場地環境（P2） | gate 灰燼、cathedral 石塵、yard 墨霧、throne 飄浮書頁＋符字（chapel 沿用原本的雪）；都是裝飾粒子，降級時不發 | vfx2.ambient |
| 20 | 階段轉換 | 屬動畫負責。`phaseBurst` 加了墨潑、主色圓相、符字、墨滴 | bossfx.phaseBurst |

招式種類怎麼判斷：`vfx.wrap` 在 telegraph 時呼叫 `bfx.setAtk(p)` 記下 kind／chain／seg；knockdown 記成 dash，ambush 記成 ambush。`bfx.impact` 依這個值選招牌特效。

**給動畫（lead 要求）**：`phaseBurst(b, phase, o)` 新增第三個選用參數 `{pillar:false}`（不要光柱）、`{pillarScale, pillarDur}`（光柱粗細倍率、秒數，預設 1／1.2）、`{squash:false}`（不做身體膨脹）。舊的兩個參數呼叫行為不變。請動畫改用 `bfx.phaseBurst(b, phase, {pillarScale:.4, pillarDur:.6})` 或 `{pillar:false}`，不必自己縮放。

另外，主角武器拖尾改成金色（設定 `hero.trailColor` 和 `trail.color`）。fx 和 bossfx 都不再呼叫 `eng.hitStop`／`eng.shake`，打擊感一律交給 feel.js（原本 bossfx.impact 裡的 hitStop 已拿掉）。

## 效能
- 預算（§4.1）在 fx.js 的池裡強制執行：加色 500、一般 300、條紋 160。存活數超過預算的 85% 時，新粒子減量，裝飾粒子不發。
- 降級：`vfx2` 監看 `eng.fps`。FPS < 40 持續 2 秒就設 `eng.fxLow=true`、`eng.fxK=0.5`：粒子減半，墨潑貼片、殘影關掉。FPS ≥ 52 持續 6 秒恢復。引擎降到 low 畫質時一律視為低效能。`eng.rm` 時粒子 ×0.4、不做全畫面墨收縮。
- 實測最重場景：390×700、DPR 2、Chrome CPU 4× 降速，噬語魔王轉到二階、三階後，連續 3 輪「三段連擊（含延遲＝詞語風暴）＋完美 5 連斬」。
  - 用 `__v3q=high` 鎖高畫質：FPS 中位數約 49，範圍 29–67。29 是轉階段第一秒、正在編譯 shader；另有幾秒在 36–40，期間觸發過一次 fxLow 降級。粒子峰值：加色 227、一般 106、條紋 110，都在預算內。
  - 不鎖畫質時，引擎在載入期間就降到 low，FPS 69–130。
  - 這一項沒有量「不開特效」的基準，所以無法區分哪些成本來自特效、哪些來自場景本身。
- 每個事件新增的粒子都控制在 ≤ 120 顆以內。全畫面貼片最多兩層：danger 暗角＋墨收縮。

## 驗證
- 自己的 dev server：5182，用自訂 config 關掉 HMR，避免別人存檔時整頁重新載入。截圖腳本：`scratchpad/pt/vfxshot.mjs`。它會停在「準備」畫面，直接呼叫場景事件處理器觸發各招，再連拍。
- 截圖在 `art/v2/shots/vfx/`：chain_5hits、parry、finisher_kill、sentinel_combo_rust_roots、sentinel_danger_seal、gargoyle_claws、gargoyle_breath、priest_danger、executioner_dash、executioner_clones、ghost_exec（殘影）、devourer_wordstorm、devourer_finalword、dodge、hurt、ambush、delayed、weak、death、phone_parry、phone_chain（390 寬）。
  ghost_exec、phone_parry、phone_chain、hurt、dodge、priest_danger、death、weak、ambush、delayed 是調降亮度和尺寸之後拍的。
  chain_5hits、parry、finisher_kill、sentinel_*、gargoyle_*、executioner_dash、executioner_clones、devourer_* 是在一部分調整之前拍的：之後冰棺柱又調暗、影步／影分身殘影改成加色紫光，這幾張不代表最終效果。
- `node tests/check.mjs`：全部通過（67 項＋25 項）。
- `URL0=http://localhost:5182/ node verify.mjs soul`：結果見最後一節。

## 已知問題
- **ink 底層在暗背景上幾乎看不見**：墨色主要靠墨滴、墨暈、地面墨潑和紅黑刀光呈現。刀光的墨底只有疊在亮處（火光、Boss 主色）時才明顯。
- 玩家刀光是以命中點為圓心的弧，在鏡頭很近時（直式、Boss 很大）只看得到弧的一段。
- **殘影會顯示 P2 部件**：行刑者的殘影頭頂有尖刺狀部件，可能是 P2 部件被顯示出來。已改成逐節點照抄 visible／scale，但在一階截圖中仍看得到，沒有再追查。
- 蓄力的筆觸粒子在小尺寸下看起來仍像點。
- **C: 槽空間**：拍攝途中 C: 槽一度被寫滿（0 MB）。之後截圖都改存 D:，raw 幀已刪除。
- 終焉之言的全畫面墨收縮（inkVeil）在截圖中不明顯，可能被 danger 暗角蓋住，需要在實機確認。

## verify.mjs soul 結果（最終程式碼）
`done:true, end:true`，五隻 Boss（0–4）全部打完，費時 84 秒。pageerror 0，console error 0。完整紀錄在 `art/v2/shots/vfx/raw/verify_soul.log`。

## 修正紀錄：連斬時畫面被金光淹沒（整合後，新模型）
**現象**：噬語魔王二、三階連斬（尤其弱點擊破追加連斬）時整個畫面泛金，主角、Boss 幾乎看不見。

**找原因**：用 `scratchpad/pt/p3fix.mjs` 測試。它在 430×900、DPR 2、鎖高畫質下，指定 Boss 和階段，重複兩輪「完美 5 連斬＋弱點擊破追加 5 連斬」，連拍 40 張 3D 畫面，再用 `p3m.py` 算亮度。逐層關掉比對，噬語魔王二階的結果：

| 關掉 | 平均亮度 | >200 像素比例（最大） |
|---|---|---|
| 不關（原始） | 91 | 14% |
| 特效（fx 全部） | 84 | 13% |
| bloom | 42 | 4% |
| Boss 的 Glow 材質 | 38 | 4% |

**主因是 Boss 的發光材質經 bloom 放大，不是刀光**：
- 新噬語魔王有 19 個 Glow 材質，強度 1.7–6，二、三階再乘 ×1.7／×2.3。書頁邊、符文是很多小片，合起來面積很大。
- 弱點擊破時 `b.glow(金, 1.5)` 把這些部位整片染金；每一刀 `b.flash(白)` 又讓它們閃白。發光量（顏色亮度×強度）因此到 4–6，bloom 再把它擴散成一整片。
- 二階底色 `glow(eye, .7)` 也讓畫面一直泛紅。

**次要原因**：拿掉 Glow 之後，其他 Boss 第 5 刀命中那一格仍有一團蓋住主角的光球。逐個關掉 enso、streaks、emit、screen 脈衝比對，來源是同一格裡疊在一起的這幾樣，經 bloom 和徑向模糊放大：
- 收鋒大弧的白熱芯
- moves.js 的 70＋26 條火花（hdr 4.5–6）
- 幾個命中閃光精靈
- 全畫面金閃
- 徑向模糊

**修法**（soul.js、moves.js、feel.js、actors.js、phaseShow.js 都沒動）：
1. **vfx2.js：Boss 發光材質亮度上限**。每個 Boss 網格在繪製前（onBeforeRender），把 Glow 材質的「發光顏色亮度 × 強度」壓到 0.5，畫完（onAfterRender）還原；眼睛（材質名含 Eye）放寬到 1.6。
   - 不改任何人寫進材質的值，phaseShow 的倍率、Actor.glow、閃白照常運作，變紅、變金、閃白的顏色都看得到，只是不再溢出。
   - 0.5 是試出來的：0.8 在連斬尾段仍整片泛光，0.05 等於關掉發光。
   - 原本試過依網格大小判斷、讓小部位放寬，但書頁、符文是很多小片，判斷失效，改成只看材質名。
2. **fx.js：刀光（brush）**
   - 弧形半徑 ≤ 畫面高 24%（直式）／32%（橫式）。
   - 直線總長 ≤ 畫面寬 70%。
   - 亮度（hdr）上限 1.25。
   - 同時存在的刀光超過 3 道時，新的一道逐級變淡（最低 35%）。
3. **fx.js：其他特效**
   - 火花條（streaks）亮度上限 2.4 → 1.7，單次最多 40 條。
   - 命中閃光精靈不透明度上限 .55 → .45；同一點 0.12 秒內的第二個閃光只留 30%。
4. **vfx2.js：收鋒大弧**。芯改成金色、亮度 1.45 → .85，出現時間由命中後 0.04 秒延到 0.14 秒，避開命中閃光那一格。
5. **screen2.js**
   - 全畫面閃光上限：紅色 .3 不變，其他顏色 .15／.22 → .08。
   - `impact()` 暖白閃 .14／.1 → .08／.06，泛光脈衝 1.1 → .95，徑向模糊 .55 → .22。

**結果**：直式 430×900，每組 40 張。

| Boss／階段 | 平均亮度 | >200 像素比例（最大） |
|---|---|---|
| 噬語魔王二階（修正前） | 91 | 14% |
| 噬語魔王二階 | 43 | 1.5% |
| 噬語魔王三階 | 58 | 3.0% |
| 守門騎士二階 | 48 | 1.7% |
| 石像鬼二階 | 47 | 1.4% |
| 霜冠祭司二階 | 64 | 5.0% |
| 暗影行刑者二階 | 40 | 2.8% |

- 每張都看得到主角與 Boss 的輪廓。
- 第 5 刀命中那一格仍有金色放射光與收鋒大弧（華麗感保留），但主角、Boss 透得出來。
- 截圖：
  - `art/v2/shots/vfx/readability_before_after.jpg`：上排修正前、下排修正後，噬語魔王二階同一套連斬。
  - `art/v2/shots/vfx/readability_allbosses.jpg`：五隻 Boss 二階＋噬語魔王三階，修正後；第 2–3 欄是第 5 刀命中。
  - 原始連拍與逐層比對在 `art/v2/shots/vfx/raw/p3fix/`。
- **驗證**：`URL0=http://localhost:5182/ node verify.mjs soul`：done、end，pageerror 0、console error 0（`raw/p3fix/verify_soul3.log`）。`node tests/check.mjs`：67＋25 項全部通過。
- **注意**：
  - 這個上限也會讓一階的大面積發光部位比模型原設定暗一些（眼睛不受影響）。如果美術要某個部位更亮，可以在材質名加 Eye，或調整 vfx2.js 的 `GLOW_CAP`。
  - 全畫面閃光上限 .08 比 §5.4 嚴，所有呼叫端都會受影響（紅色受擊閃不受影響）。
