# boss_devourer 噬語魔王：v1.3.0 新招 7 個（動畫報告）

2026-11-28｜負責：devourer 動畫師｜合約：`art/v4/BRIEF.md`

## 結果摘要
- 新增 7 個片段（名稱照合約）：`Sweep`、`Smash`、`Leap`、`ComboB`、`Special`、`ComboC`、`Special3`。GLB 共 25 片段。
- `public/models/boss_devourer.glb`：**4.23 MiB（4,433,056 bytes）**、**49,894 三角面**（跟之前一樣）、`check_soul_glb.py` → **boss_devourer OK**（hero_knight／boss_priest 的 FAIL 是別人的檔案，沒有處理）。
- 既有 18 片段（含 PhaseShift2）：未壓縮 GLB 逐聲道比對**完全相同**（maxdiff 0），clipmeta 的時長／hits 也完全相同。
- 型態部件：節點名稱與縮放（`P2_*`、`P3_*`、`X3_*`、`X3_HornLongR`）、材質、貼圖都和之前一樣。重新建模會有浮點誤差：UnderTorso 有 4 個頂點差 ≤ 8 mm，X3_GreaveL 少 1 個頂點（merge-by-distance）。UV 與烘焙貼圖不變，看起來沒有差別。
- 逐片段逐格地面檢查（`v3_devourer_groundcheck.py`，25 片段 × 每格 × 9 類部件）：**不合格 0 格**。新招劍尖最低點都在地面以上（出招期間最低約 0.1 m，起訖的拄劍待機是 0.04 m，跟既有 Idle 一樣）。網格最低點 ≥ 0（secondary 最後的骨盆微抬 ≤ 6 cm，既有片段也是這樣處理）。

## 片段表（30 fps；hits／cancel 單位：秒）
hits 是在標記格附近，量劍尖（WeaponTip）速度峰值得到的；ComboB 第 2 擊量的是左手 HandL。cancel ＝ 跟隨動作結束、開始回戒備姿勢的時間，可以從這裡交叉淡入下一招。

| 片段 | 招式名 | 階段 | 起／訖 | 時長 | hits | cancel |
|---|---|---|---|---|---|---|
| Sweep | 墨刃橫掃 | 一階起 | Idle | 2.533 | [1.1] | 1.867 |
| Smash | 魔劍震地 | 二階 | IdleAggro | 2.733 | [1.2] | 2.133 |
| Leap | 虛空躍擊 | 二階 | IdleAggro | 3.0 | [1.533] | 2.4 |
| ComboB | 吞字三連 | 二階 | IdleAggro | 3.467 | [0.9, 1.433, 1.9] | 2.867 |
| Special | 詞語風暴 | 二階必殺 | IdleAggro | 3.733 | [1.8, 2.333] | 3.067 |
| ComboC | 終焉四連 | 三階 | IdleAggro | 3.733 | [0.833, 1.1, 1.467, 2.2] | 3.133 |
| Special3 | 終焉之言 | 三階終極必殺 | IdleAggro | 5.533 | [2.533, 3.833] | 4.933 |

## 動作描述與特效／音效建議時間點（秒）

### Sweep 墨刃橫掃（2.53 s，1 擊）
劍收到**左肩後方**反手握住，上身往左扭到幾乎背對主角（0.33–0.93 s 蓄力、微顫）。1.1 s 時**由左往右**低位（膝高）大範圍橫掃，弓步前踏；1.2–1.53 s 劍甩到右後方，再慢慢回到 Idle。
跟 Attack（直劈）、Attack2（右→左、胸高）比：方向相反、高度低、預備時背對主角，剪影很好認。紙翼蓄力時收攏、命中時張開。
- 0.35 s：低沉吸氣、甲冑摩擦聲（預警）。0.9 s：劍刃墨光聚集（紅黑墨流沿劍刃）。
- 1.0 s：破風聲。1.1 s：命中＋地面掃出一道弧形墨痕。1.3 s：墨滴甩落。

### Smash 魔劍震地（2.73 s，1 擊）
雙手把劍**直舉向天**、抬起左腳（0.67–1.1 s 定格蓄力，劍微微後仰）。1.2 s 跺腳、全身深蹲，**劍身幾乎平拍**到前方地面（劍尖停在地面上方約 0.1 m，不會插進地裡）。1.37–1.8 s 保持低姿、身體顫動，2.13 s 起身。紙翼舉劍時上張，落地時向下拍。
- 0.7 s：劍尖凝聚紅光、低鳴。1.15 s：左腳跺地（悶響）。
- 1.2 s：命中，重砸地＋地面衝擊波（圓形裂紋、碎石、塵土），鏡頭震動。1.4 s：迴響、石屑落地。

### Leap 虛空躍擊（3.0 s，1 擊；原地播放，前進位移由遊戲處理）
伏低、劍拖在右後方（0.4–0.83 s 壓縮蓄力，抬頭盯著主角，紙翼收攏）。約 0.9 s 蹬地**躍起**（骨盆升高約 1.7 m），劍舉過頭往後倒，雙腳收起，紙翼全開，在 1.07–1.4 s 滯空。1.53 s 落地，**雙手斜劈前下方**，弓步。1.67–2.07 s 保持低姿，2.4 s 回勢。
- 0.85 s：蹬地爆聲＋地面墨濺。1.0–1.4 s：紙翼拍擊、書頁飛散。
- 1.53 s：命中＋落地重擊（衝擊圈）。建議遊戲在 0.9–1.5 s 之間把 Boss 往主角方向推進。

### ComboB 吞字三連（3.47 s，3 擊；節奏 慢—快—快）
劍低放在右後方蓄力（0.4–0.83 s）→ ① 0.9 s **右下往左上**斜撩 → 左手往後拉 → ② 1.43 s **左手符紋爪前抓**（「吞字」，命中量左手）→ 劍舉到左上 → ③ 1.9 s **左上往右下**斜劈。2.07–2.53 s 保持跟隨姿勢，2.87 s 回勢。
- 0.9 s：撩斬破風＋紅色墨弧。1.35 s：左手符紋發光。1.43 s：爪擊＋吸入字元的特效（字從主角身上被吸走）、低沉吞嚥聲。1.9 s：斜劈命中、金屬聲。

### Special 詞語風暴（3.73 s，2 擊，二階必殺）
雙手把巨劍**橫舉過頂**，仰首，紙翼全開到最大（0.4–1.33 s，約 1.4 秒預兆，是二階預備最長的招）。1.53–1.63 s 往右後扭身蓄力。1.8 s 開始**向左原地旋轉兩圈**：劍水平伸出、腰高，每圈經過正面命中一次（1.8 s、2.33 s）。之後甩出減速，3.07 s 回正、低姿，最後回到 IdleAggro。旋轉時紙翼、披風、墨潮都會跟著轉。
- 0.4 s：咆哮（胸口巨口）＋書頁開始在四周盤旋。1.3 s：字元旋渦變濃。
- 1.8 s／2.33 s：命中×2，旋風斬破風聲（連續）＋環狀書頁風暴。2.6 s：風暴散開、紙片落下。

### ComboC 終焉四連（3.73 s，4 擊，三階）
劍收到右腰（0.33–0.67 s）→ ① 0.83 s **直刺**（身體直立、短踏步，不是 Dash 的長突進）→ ② 1.1 s 刺出後**往上翻挑** → ③ 1.47 s **向右**旋身一圈、肩高斬（和 Special 的方向、高度都不同）→ 旋轉後段把劍舉過頂、小跳（1.83–2.07 s）→ ④ 2.2 s **落地重劈**（劍身停在地面上方）。2.33–2.8 s 保持低姿，3.13 s 回勢。
- 0.83 s：刺擊（尖銳破風）。1.1 s：上挑、金屬刮擦。1.47 s：旋斬破風。
- 2.0 s：舉劍時符字環亮起。2.2 s：重劈＋地裂墨火、鏡頭震動。

### Special3 終焉之言（5.53 s，2 擊，三階終極必殺）
劍**豎在面前**，低頭像在宣誓（0.4–0.73 s）→ **懸浮升空**（骨盆上升約 0.9 m），劍直指天空（1.13–1.87 s）→ 劍收到左肩後方（2.13–2.33 s）。預兆總長約 2.5 秒。① 2.53 s 俯衝落地，**左上往右下**斜劈，**單膝跪地**。跪姿顫動、劍拖到右後方（2.7–3.67 s）。② 3.83 s 起身，反方向大撩（**右下往左上**），雙臂高舉、劍指天（4.03–4.53 s 定格）。4.93 s 回勢，回到 IdleAggro。
- 0.4 s：場景變暗、低語合唱。1.1–2.3 s：懸浮時有墨柱／字元往上捲。2.3 s：所有符字環聚到劍上（最強預警）。
- 2.53 s：命中 1，落地斜劈＋大範圍地裂。3.0–3.6 s：跪地蓄力，地面字元往劍身集中。
- 3.83 s：命中 2，上撩光柱（終焉之言）。4.1 s：白閃、餘震。

## 實作與檔案
- `art/blender/v3_devourer_actions.py`：新增 `build_v4()`（檔案末端），在 `build()` 最後呼叫。`T()` 加了 `air=True`（躍起／懸浮的姿勢不限制骨盆高度），`A()` 的 hits 支援 `(格, 關節)`。整身自轉用 `KP(th=…)` 把骨盆、腳、武器目標一起繞 Z 軸旋轉。meta 的 `cancel` 也寫在這裡。既有片段的程式路徑沒有改。
- `art/blender/v3_devourer_secondary.py`：只對新片段生效。`rig.wing_keys` 控制各招的紙翼開合（`WING_SIGN=-1`，正值＝往上張開，已渲染確認）；`rig.spin_keys` 讓紙翼、墨潮骨、披風地面骨跟著整身自轉，轉完回到 IdleAggro 的慣例方向；躍起／懸浮時，披風地面段跟著離地（0.9 倍）。
- `art/blender/v3_devourer_model.py`：新增 `--nobake`（沿用 `textures/baked/v3_devourer_*` 的既有烘焙）。
- `art/blender/v3_devourer_run.sh`：新增 `--nobake` 參數；暫存與 log 改放到 `art/v4/tmp/devourer/`。
- 新檔：`art/blender/v3_devourer_v4shots.py`（關鍵影格渲染＋逐格劍尖／網格最低點）、`art/blender/v3_devourer_v4sheet.py`（拼圖）。
- 輸出：`public/models/boss_devourer.glb`、`art/blender/export_raw/boss_devourer.{glb,clipmeta.json}`、`source/v3_devourer.blend`。已跑 `merge_clipmeta.py`，它重寫了 `src/battle/view3d/clipmeta.json`（合約允許；lead 最後會再跑一次）。

## 怎麼重跑
```
bash art/blender/v3_devourer_run.sh --nobake --noprev     # 約 2 分鐘：建模（沿用烘焙）→ 動作 → 量測 → 逐格地面檢查 → 壓縮 → merge → check
# 只看新招（quick 模型，約 25 秒＋渲染）：
blender --background --factory-startup --python art/blender/v3_devourer_model.py -- --quick --only Sweep,Smash,Leap,ComboB,Special,ComboC,Special3
blender --background --factory-startup --python art/blender/v3_devourer_v4shots.py -- [blend] --clips Special --frames "Special:0,24,54,69"
python art/blender/v3_devourer_v4sheet.py <shots_dir> <out_dir>
```
關鍵影格拼圖：`art/v4/tmp/devourer/final/sheet_<片段>.jpg`（正式烘焙模型，-35° 與 80° 兩個角度）。各片段逐格數據：`art/v4/tmp/devourer/shots_final/diag_<片段>.txt`。地面表：`art/v4/tmp/devourer/ground.md`。

## 已知問題／交給 lead
1. Leap、Special3 的前進／懸浮都是原地播放：Leap 要由遊戲在 0.9–1.5 s 推進位移；Special3 的懸浮是骨盆上升，Root 不動。
2. 三階時紙翼隱藏，所以 ComboC／Special3 的翅膀動作看不到（還是有 key，不影響）。
3. 旋轉招（Special、ComboC）在背面那幾格會露出披風暗紅內襯的大面積，這是模型原本的樣子，不是動畫造成的。
4. Special3 懸浮時，三階墨潮（P3_InkBody）跟著骨盆一起升起。
5. 依共用規則，README 的「修改紀錄」要補一筆。README 屬於 lead 的檔案，我沒有改，請 lead 合併時補上（本次沒有新增或變更遊戲連結）。
