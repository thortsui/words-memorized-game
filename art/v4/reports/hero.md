# hero_knight v4：連段與新動作 25 個（2026-11-28）

合約：`art/v4/BRIEF.md`。模型外觀沒改（沿用既有烘焙貼圖，預覽 `art/blender/preview/v3_hero_compare.jpg` 和之前一樣），只新增動作片段和 meta 的 `cancel` 欄位。

## 交付
| 項目 | 結果 |
|---|---|
| 遊戲檔 | `public/models/hero_knight.glb` **4.38 MB**（原本 3.90 MB，增加的是動畫資料；上限 4.5 MB 內）、41,955 三角面、25 骨，材質與貼圖沒變 |
| 片段 | 原本 17 個加上新的 25 個，共 **42 個**。舊片段的名稱、時長、hits 跟之前的 clipmeta 逐欄比對完全相同 |
| clipmeta | `export_raw/hero_knight.clipmeta.json`。新片段有 `cancel` 欄位（秒），已跑 `merge_clipmeta.py`，`src/battle/view3d/clipmeta.json` 已更新 |
| 檢查 | `check_soul_glb.py` → hero_knight **OK**（boss_priest 當時 FAIL 4.58 MB，是別人的檔案） |

## 25 個新片段（30 fps；hits 是用劍尖速度峰值量出來的，跟舊片段同一個方法）
| 名稱 | 時長 s | hits s | cancel s | 動作 |
|---|---|---|---|---|
| ChainReady | 2.000（循環） | – | – | 連段蓄勢：低重心、劍豎在右側、左手前伸。呼吸、重心左右微晃、劍尖輕擺 |
| ChainP1 | 1.000 | 0.467 | 0.700 | 劍舉過右肩、劍尖朝後上，左腳踏出成弓步，右上往左下大弧斜劈，身體跟著轉，停在左下 |
| ChainN1 | 0.900 | 0.333 | 0.633 | 雙手舉劍過頭、踏步直劈，收在左下（跟 P1 同一個結束姿勢 E1） |
| ChainP2 | 1.067 | 0.533 | 0.800 | 從左下起手，下沉後向右轉一整圈並小跳（腳跟著轉、騰空不滑步）。落地那一刻反手橫斬掃過正前方 |
| ChainN2 | 0.900 | 0.300 | 0.600 | 劍收到左肩，反手斜斬到右側，同時收回弓步 |
| ChainP3 | 1.067 | 0.367 | 0.800 | 深蹲後劍從右下往前上撩起，身體跟著跳起約 30 cm，劍舉到頭頂，落地架在右肩 |
| ChainN3 | 0.900 | 0.267 | 0.667 | 右腰蓄勢，弓步突刺，收劍架到右肩 |
| ChainP4 | 1.133 | 0.433, 0.700 | 0.867 | 跳起（約 36 cm），空中先左上往右下、再右上往左下交叉雙斬，重落地壓低 |
| ChainN4 | 0.900 | 0.300 | 0.600 | 腰帶動，右往左水平掃斬，收在左側 |
| FinishN | 1.800 | 0.933 | 1.333 | 雙手高舉，頂點停頓蓄力，踏前重劈到地面，壓低停住 |
| FinishP | 1.867 | 0.667, 1.133 | 1.467 | 雙旋重斬：向右連轉兩圈，每圈結尾橫斬掃過正前方。第二圈小跳，落地弓步壓低 |
| FinishAll | 2.500 | 0.600, 1.067 | 1.733 | 深蹲躍起（約 60 cm），空中迴旋斬，空中改雙手高舉，落地重劈，停頓約 0.5 秒後起身 |
| ChainBreak | 1.400 | – | – | 答錯：劍被往右後彈開、上身後仰，踉蹌退兩步，壓低穩住，重新架劍，收在戒備 G |
| ChainRecover | 0.900 | – | 0.633 | 從 CR 甩劍（血振）往右下，再收回戒備 G |
| AssaultA | 1.000 | 0.200, 0.500 | 0.667 | 正手橫斬接反手上撩 |
| AssaultB | 1.000 | 0.300, 0.467 | 0.667 | 弓步突刺，收劍過肩斜劈 |
| AssaultEnd | 1.467 | 0.400 | 1.000 | 深蹲蓄力，爆發成長弓步突刺貫穿，停住，拔回收腳 |
| Execution | 2.733 | 0.533, 1.700 | 2.133 | 踏前、雙手把劍架在右肩、停頓，往前下方刺入，推深並扭轉停頓，拔劍蓄勢，迴身大橫斬 |
| Riposte | 1.200 | 0.467 | 0.800 | 格開對方的劍，劍從頭上繞回右側，踏入橫斬 |
| Deflect | 0.700 | 0.133 | 0.367 | 劍往右外小幅格開，馬上回位 |
| SideL / SideR | 0.700 | – | 0.467 | 壓低，往側面小跳（骨盆側傾、兩腳先後離地），落地緩衝（左右互為鏡像） |
| Drink | 1.600 | 0.733（左手，喝下那格） | – | 劍垂在右側，左手從腰間取壺舉到嘴邊，仰頭喝，放下 |
| GetUp | 1.400 | – | – | 從 Die 的最後一格（趴地）開始：撐起，雙膝跪地，拄劍成單膝跪，起身，回戒備 |
| BattleCry | 1.667 | – | – | 下沉蓄氣，劍高舉向天、左拳握緊振臂、仰頭，停住，甩劍回戒備 |

### 連段怎麼接（給 lead 寫 soul.js 參考）
- **CR**＝ChainReady 姿勢。第 1 下（P1／N1）從 CR 起手。
- 第 i 下在 **cancel 那一格剛好是結束姿勢 E(i)**。同一位置的 P 版和 N 版共用同一個 E(i)，第 i+1 下的第 0 格就是 E(i)。所以任何「完美／普通」組合在 cancel 交叉淡入時，姿勢都完全接得上。
  - E1：劍在左下（弓步）
  - E2：劍在右側水平
  - E3：劍架在右肩上方
  - E4：劍在左側
- **終結技（FinishN／P／All）從 E4 起手**。連段如果不到 4 下就接終結技，起手姿勢會差一點，建議淡入 0.15 秒。
- cancel 之後，片段的尾段會收回 CR（從左側收劍時先把劍豎到身前，不會橫掃穿過腰）。所以**播完後接 ChainReady 是無縫的**。反過來，從 ChainReady 接下一下（起手是 E(i)）會有小幅姿勢差，建議淡入 0.12–0.15 秒。
- 終結技最後收回 CR。要回一般戒備，接 ChainRecover（CR → G）。ChainBreak 從 CR 開始、收在 G。
- 其他單發動作（Assault*、Execution、Riposte、Deflect、Side*、Drink、BattleCry）都是 G 起、G 收。GetUp 從 Die 的最後一格起、收在 G。
- 全部原地播放，Root 不動。旋轉類片段（ChainP2、FinishP、FinishAll）的骨盆實際轉了 360°／720°，起訖朝向和 E2／CR 相同（四元數只差正負號，three.js 的混合會自動處理）。

## 修改的檔案
- `art/blender/v3_hero_actions.py`：新增 `_v4()`，裡面是 25 個片段，在 `build()` 最後呼叫。`A()` 多了 `cancel` 參數。新增小工具：
  - `Arc`：用大圓弧描述揮砍，刃口自動朝運動方向
  - `feet(dy=…)`：整組腳位繞 Z 軸旋轉，抬腳、墊腳
  - `body()`：軀幹姿勢，有 `dy` 整體旋轉參數
  - `spin_pose()`：旋轉類動作用
- `art/blender/v3_hero_rig.py`：`V3Rig.action(..., cancel=格號)` 會把 `cancel` 換算成秒寫進 `meta[name]`。只改 meta，其他行為不變。
- `art/blender/v3_hero_build.py`（合約檔案清單沒列，但這是主角專用檔，改動很小）：
  - 新增 `--reusebake`：不重烘，直接載入 `textures/baked/v3_hero_knight_*` 的既有貼圖，照常匯出
  - 新增環境變數 `HERO_TMP`：可以改暫存資料夾
  - quick／only 模式會把 meta 寫到暫存的 `meta_quick.json`
- `v3_hero_bake.py` 沒動（`write_meta` 原本就是直接輸出 `rig.meta`）。
- 輸出：`public/models/hero_knight.glb`、`export_raw/hero_knight.glb`／`.clipmeta.json`、`source/v3_hero_knight.blend`、`preview/v3_hero_*.jpg`（重拍）、`src/battle/view3d/clipmeta.json`（merge 產生）。

## 怎麼重跑
```
bash art/blender/v3_hero_run.sh --reusebake      # 約 75 秒：建模＋動作＋沿用烘焙圖匯出 → 壓縮 → merge → check
bash art/blender/v3_hero_run.sh                  # 要重烘貼圖時（很久）
```
快速迭代工具放在 `art/v4/tmp/hero/`（不進 git）：
- `iter.sh [片段,…] [格數] [方位角]`：quick 建置後用 Workbench 拍圖並拼圖
- `feetz.py`：逐格量腳踝高度
- `swordbody.py`：檢查劍有沒有穿身

## 驗證
- **逐格穿地**（`v3_hero_ground.py`，42 片段每一格）：全部 OK，結果在 `art/v4/tmp/hero/ground.txt`。新片段的最低點都是 −0.008 m（靴底）。劍尖最低：FinishAll +0.002（落地重劈，劍尖貼地）、FinishN +0.035、ChainP3 +0.045。
- **劍穿身**（`swordbody.py`：劍身頂點落進骨盆、胸、頭的橢圓柱就算）：20 個片段是 0。ChainP2 2.5 cm、FinishP 2.4 cm、FinishAll 2.9 cm 都在旋轉段，是護手和握柄靠近腰側。Execution 2.1 cm（拔劍那格）。ChainP4 0.2 cm。修之前旋轉蓄力那幾格最深 5.5 cm，已經把劍移到身體外側。
- **滑步**：腳只在抬起的格子之間換位置，`feetz.py` 逐格確認過。落地重劈時後腳的腳踝高 4 cm，是故意墊腳（腳跟抬起）。ChainBreak 收腳時後腳原本構不到地（懸空 4 cm），已改成骨盆晚一點往前。
- **目視**：每個片段都用 Workbench 拍 10–12 格拼圖看過（`art/v4/tmp/hero/sheet.jpg`、`row_*.jpg`）。依看到的問題改了這些地方：
  - P1 起手改成真的舉過右肩
  - 收劍路徑改成先豎到身前（原本會橫穿腰）
  - P3 的命中時機和撩起曲線
  - GetUp 拄劍時劍尖插進地面 −0.30 m（已修正）
  - 處決蓄勢時劍太靠近頭盔

## 已知問題
1. **旋轉類片段的披風穿身**：ChainP2 8.9 cm、FinishP 9.7 cm、FinishAll 9.3 cm。和既有 Roll（9.6 cm，之前審查判定為輕微）是同一種情況：快速旋轉時布料鏈跟不上。數字是用軀幹橢圓柱近似量的，畫面上主要是披風貼著背轉。
2. 命中時間是用劍尖速度峰值量的，比劍真正指向正前方的那一格早 1–2 格（33–67 ms），舊片段也一樣。
3. 喝藥沒有藥壺模型，左手是空握的。遊戲端如果要顯示藥壺，需要另外掛在 HandL 上。
4. `hero_knight.glb` 4.38 MB，接近 4.5 MB 上限。以後再加動畫可能要降取樣，或調 `export_optimize_animation_size`。
5. Gemini 參考圖（可選）沒有做。動作是依合約描述直接設計的，沒有參考任何現有遊戲的招式或美術。
6. 依規則 README 修改紀錄和工作日誌由 lead 統一補，我沒有動。
