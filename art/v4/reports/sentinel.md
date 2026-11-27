# boss_sentinel 鏽蝕守門者：v1.3.0 新招報告（2026-11-28）

依 `art/v4/BRIEF.md` 新增 5 個片段：**Sweep、Smash、Leap、ComboB、Special**。只新增片段，原本 17 個片段的名稱、時長、hits 完全沒變（新舊 `export_raw/boss_sentinel.clipmeta.json` 逐項比對相同）。外觀、P2 部件、材質、貼圖也都沒變（沿用 v3 的烘焙貼圖）。

## 交付
| 項目 | 值 |
|---|---|
| `public/models/boss_sentinel.glb` | **4.43 MB**（4,428,756 bytes，≤4.5 MB；原本 4.24 MB，多出來的都是動畫資料），**48,230 三角面**（≤50k），32 骨，22 個片段 |
| P2 | 22 個 P2_* 節點，名稱與 scale 0 和舊版完全相同；材質清單、圖片清單也相同 |
| 外觀 | v3 預覽圖（views／cmp_p1／cmp_p2／closeups）重新渲染後和舊圖平均像素差 < 0.002（等於相同），所以把這四張還原成 git 版，沒有提交無意義的變動 |
| `check_soul_glb.py` | boss_sentinel **OK**（別隻 Boss 還沒做完所以 FAIL，不是我的檔案） |
| `merge_clipmeta.py` | 已跑（`src/battle/view3d/clipmeta.json` 已含 5 個新片段與 cancel） |

## 新片段（30 fps；秒）
| 片段 | 招式名 | 時長 | hits | cancel | 起訖姿勢 |
|---|---|---|---|---|---|
| Sweep | 鏽戟橫掃 | 2.600 | [1.000] | 1.733 | Idle |
| Smash | 門板震地 | 2.867 | [1.133] | 2.000 | IdleAggro |
| Leap | 躍起戟擊 | 3.267 | [1.500] | 2.267 | IdleAggro |
| ComboB | 根鬚三連 | 3.400 | [1.033, 1.333, 1.667] | 2.400 | IdleAggro |
| Special | 根鬚纏擊 | 4.133 | [1.500, 2.533] | 3.200 | IdleAggro |

- hits＝戟尖（WeaponTip）速度峰值，跟既有片段同一套量法。
- cancel＝跟隨動作做完、開始回勢的那一格。
- 決定：一階招 Sweep 起訖用 Idle；二階四招起訖用 **IdleAggro**，因為二階待機就是 IdleAggro，這樣淡入淡出最順。既有片段的 Combo3／Delayed／Dash 仍用 Idle，沒有改。

### Sweep 鏽戟橫掃（一階）
- **動作**：身體往左扭、壓低，戟拖到左側腰下（0.33–0.83 s 蓄力，0.83 s 時再往下壓一點）→ 左腳大跨步，戟由左往右**在膝蓋高度低掃**（1.0 s）→ 戟甩過右後方、身體扭到右邊（1.2–1.53 s 停住，顯得很重）→ 慢慢收回 Idle。
- **和既有招的差別**：Attack 是胸口高度、由右往左；Sweep 是**膝蓋高度、由左往右的反手低掃**，蓄力在另一側，揮過的範圍約 200°。
- **特效／音效**：0.33 s 甲冑摩擦＋布料；0.85 s 起刀破風（低沉）；1.0 s 命中＋低處弧形刀光（0.87–1.2 s），地面掃起塵土；1.4 s 戟頭拖地的金屬刮聲（可選）。

### Smash 門板震地（二階）
- **動作**：雙手把戟**橫握舉過頭**（像扛起一整扇門），同時提起左膝、上身微後仰（0.4–1.0 s；1.0 s 再往上一提）→ 踏地同時把整支戟**平拍地面**、身體蹲到最低（1.133 s）→ 反彈小抬（1.23 s）→ 壓在地上停住（到 1.8 s）→ 起身回 IdleAggro。
- **和既有招的差別**：Attack2／Delayed 是戟頭斜向直劈；Smash 的蓄力剪影是「橫桿舉過頭＋單腳提膝」，命中是整支戟水平拍地＋重踏，屬於範圍震擊。
- **特效／音效**：0.4 s 鐵器鏗鏘提起；0.9 s 低吼；**1.133 s 重砸地＋踏地（兩個聲音同時）＋圓形衝擊波＋碎石＋鏡頭震動**；1.23 s 碎石落地小聲；2.0 s 起身甲冑聲。

### Leap 躍起戟擊（二階）
- **動作**：深蹲、戟拖右後下方（0.33–0.83 s 壓縮）→ 0.97 s 蹬地起跳 → **離地**（約 1.0–1.45 s：骨盆最高上升約 0.6 m，雙腳收起，最高點的腳尖離地約 0.6 m），空中把戟舉過頭、上身後仰 → 下落同時往前劈，1.5 s 落地成弓步、戟頭砸地 → 壓低停住（到 2.07 s）→ 起身，往後收回原位。
- **位移**：Root 不動，照 Dash 的做法只移骨盆／腳目標。落地時骨盆往前約 0.75 m，前腳往前約 1.0 m；結尾回到原點。遊戲如果要真的拉近距離，請在 0.97–1.5 s 之間移動 Boss 根節點，並在回勢時抵銷。
- **特效／音效**：0.95 s 蹬地＋塵土；1.0–1.4 s 甲冑與布料呼嘯；1.2 s 頂點可接短促吼聲；**1.5 s 落地重擊＋戟砸地＋衝擊波＋鏡頭震動**；2.27 s 起身。

### ComboB 根鬚三連（二階，慢—快—快）
- **動作**：① 戟拖右後低處**久蓄**（0.33–0.9 s）→ 由右下往左上的**上撩斬**（1.033 s），戟甩到左上方；② 隨即由左上往右下**斜劈**（1.333 s）；③ 短拉一下、跨步**往前上方挑刺**（1.667 s），停住到 2.2 s → 回 IdleAggro。
- **和 Combo3 的差別**：Combo3 是快—快—慢（橫掃、回掃、重劈）；ComboB 是**慢—快—快**（間隔 0.30 s、0.33 s），三下的方向是上撩、斜劈、上挑刺，沒有一下和 Combo3 相同。第三下的刺是往上 30° 左右的挑刺，和 Dash 的水平突進刺看起來不一樣。
- **特效／音效**：0.33 s 戟頭刮地；1.0 s 第 1 下破風＋命中；1.3 s 第 2 下（音高高一點、短一點）；1.65 s 第 3 下刺擊（尖銳的金屬聲）；刀光：上撩弧形、斜劈弧形、刺擊直線殘影。

### Special 根鬚纏擊（二階必殺）
- **動作**：**單手把戟直舉向天**、左手向前張爪、上身後仰仰頭（0.4–0.73 s）→ 原地**顫抖蓄力**（0.73–1.4 s，頭和身體左右抽動）→ **1.5 s 雙手猛把戟頭刺進前方地面**（第 1 擊：根鬚從刺入點往目標竄出、纏住目標）→ 1.67–2.37 s 壓住戟柄、全身繃緊，左右扭轉（纏繞中）→ **2.533 s 爆發把戟從地裡往上後方拔起**（第 2 擊：把纏住的目標甩飛）→ 高舉停在 2.67–3.0 s → 3.33 s 戟橫在胸前 → 回 IdleAggro。
- **預備**：從開始到第 1 擊有 **1.5 s**，是五招裡最長的；剪影是「長戟直指天空＋張爪」，五招裡辨識度最高。
- **特效／音效**：0.4 s 低吼＋地面開始震動；0.73–1.4 s 地面綠光裂紋往目標方向蔓延（預警範圍）、根鬚摩擦聲（可配心跳）；**1.5 s 刺地重擊＋根鬚破土（多條根從刺入點到目標竄出）**；1.67–2.37 s 根鬚纏緊的嘎吱聲、綠光脈動；**2.533 s 拔起爆裂聲＋根鬚斷裂＋往上甩的碎土**；3.33 s 收戟金屬聲。

## 驗證
- **穿地**（`art/v4/tmp/sentinel/ground2.py`，從審查用的 `ground.py` 改成**逐格**檢查、左右腳分開、可只跑指定片段；對 `export_raw/boss_sentinel.glb`；結果在 `art/v4/tmp/sentinel/ground_final.txt`）：
  - Sweep、Smash、Leap、Special：全部部件 ≥ −0.02 m（最差 Leap 戟 −0.006 m、Smash 右腳 −0.015 m）。
  - ComboB：右腳 −0.030 m（只有 1 格），和既有 Attack 的右腳 −0.030 m 同等級；戟、布料、P2 全部 ≥ 0。
  - 修正過程：Smash 拍地時戟刃 −0.12 m（刃口朝下＋蹲太低）→ 刃口改成朝前下、拍地高度提高；Smash、Special 下蹲時背上門板下緣 −0.04 m → 骨盆少蹲 0.06–0.08；Leap 起跳腳尖下壓 −0.06 m → 起跳時腳掌放平。
- **關鍵影格拼圖**（3/4 正面＋右側面，每 6 格一張，命中格用紅字標示）：
  - 有貼圖的最終版：`art/v4/tmp/sentinel/final/sheet_{Sweep,Smash,Leap,ComboB,Special}.jpg`
  - 試作版（quick 材質）：`art/v4/tmp/sentinel/prev/`
  - 也更新了 `art/blender/preview/v3_sentinel_actions1.jpg`／`actions2.jpg`（動作連拍，現在含新片段）。

## 怎麼重跑
- 全部：`bash art/blender/v3_sentinel_run.sh --nobake`（約 1.5 分鐘：沿用 `art/v3/tmp/sentinel/baked/` 的烘焙圖，再做建模、22 個動作、匯出、壓縮、P2、量測、merge、check）。不加 `--nobake` 就會重新烘焙（約 6 分鐘）。
- 只調動作：`bash art/v4/tmp/sentinel/dev.sh [Sweep,Smash]`（quick 建模＋只做指定片段 → `dev.blend` → 關鍵影格 → 拼圖，約 50 秒）。
- 穿地：`blender -b --factory-startup --python art/v4/tmp/sentinel/ground2.py -- <glb 或 blend> [片段,...]`

## 改了哪些檔
| 檔案 | 改動 |
|---|---|
| `art/blender/v3_sentinel_actions.py` | `A()` 加上 `cancel` 參數（寫進 meta 的 `"cancel"`，單位秒）；檔尾新增 5 個片段（既有片段的程式完全沒動） |
| `art/blender/v3_sentinel_poses.py` | 握法表新增 `v4_*` 共 33 個鍵 |
| `art/blender/v3_sentinel_build.py` | 設了環境變數 `SEN_DEVBLEND` 時另外存一份試作 blend＋meta（給 `--only` 試作用；不影響正式流程） |
| `art/blender/v3_sentinel_run.sh` | 只在註解補上 `--nobake` 的說明 |
| `art/blender/v3_sentinel_v4prev.py`、`v3_sentinel_v4sheet.py` | 新檔：新招關鍵影格渲染、拼圖 |
| `public/models/boss_sentinel.glb`、`art/blender/export_raw/boss_sentinel.*`、`art/blender/source/v3_sentinel.blend`、`preview/v3_sentinel_actions1/2.jpg` | 重跑後的產出 |
| `src/battle/view3d/clipmeta.json` | 由 `merge_clipmeta.py` 產生（lead 最後會再跑一次） |

## 已知問題／給 lead
1. GLB 4.43 MB，離上限只剩約 70 KB。之後如果還要再加片段，要先壓動畫（例如降取樣）或把貼圖降一級。
2. ComboB 和既有 Attack、Combo3 一樣，右腳在跨步那 1 格會沉進地面約 3 cm（腳尖下壓＋腳往外轉造成）。肉眼看不出來，這次沒有再處理。
3. Leap 的往前位移只做在骨盆上（Root 不動）。遊戲如果要真的突進，要自己移動根節點，並且在回勢時拉回來（片段結束時骨盆已經回到原點）。
4. 依共用規則 README 要寫修改紀錄，但 README 不在我的檔案範圍內，請 lead 統一補上。
5. 沒有 git commit／push，也沒有跑 npm run build。
