# 單字魂 v3：人形角色重新建模（團隊合約）

使用者評語（原話重點）：「人形的角色你做得很糟糕」。要求：
- 建模師不是只建出重點，要建出**紋理**與**壓迫感**。
- 每個部位具體是什麼（一塊布？皮？鎖子甲？板甲？紙？）**材質要區分清楚**。
- **身材比例**（手臂直徑、手腕、腰圍直徑、胸、腿…）要**按照參考圖重新檢查**。
- 建模後要有人檢查並修改。尤其是人形角色。

範圍：人形角色 5 個——`boss_sentinel`（腐朽守門騎士）、`boss_priest`（霜冠祭司）、`boss_executioner`（暗影行刑者）、`boss_devourer`（噬語魔王）、`hero_knight`（主角騎士）。gargoyle 不在範圍。

## 參考資料
- Boss 參考圖：`art/reference/v2/<id>_p1.jpg`、`_p2.jpg`（devourer 另有 `_p3.jpg`）、`lineup.jpg`；主角：`art/reference/hero_knight_sheet.jpg`。
- 設計規格 `art/v2/design.md`、美術拆解 `art/v2/art_guide.md`、v2 報告 `art/v2/reports/modeling_a.md`、`modeling_b.md`、`animation.md`（型態節點合約）。
- **每隻的詳細規格表 `art/v3/specs/<id>.md`**（參考分析師產出：比例表、部位材質表、表面細節清單、壓迫感要點）。建模以這份為準。
- 現有腳本（可讀、可複製，不要改）：`art/blender/v2a_*`、`v2b_*`、`soul_humanoid_*.py`、`soul_hero_actions.py`、`build_soul_hero.py`、`soul_humanoid_bake.py`、`check_soul_glb.py`、`merge_clipmeta.py`、`make_sheet.py`。
- 本機 CC0 貼圖 `art/blender/textures/acg_*`（Metal024、Rust009、Chainmail004、Leather026、Fabric030、Moss002、Bark012、Wood066）。**不要下載任何新檔案**；其他材質（粗麻、亞麻、絲、宣紙／書頁、錘紋鐵、霜、冰、骨）用 Blender 程序化節點（Noise／Voronoi／Wave／Brick、織紋）做出，烘焙成 basecolor／normal／ORM 貼圖。

## 不可違反
- 角色原創，不可抄任何既有遊戲。
- Blender 只用 headless：`"/c/Program Files/Blender Foundation/Blender 4.2/blender.exe" --background --factory-startup --python <script> -- <args>`。**絕對不要用 Blender MCP。**
- 不要 git commit／push、不要 `npm run build`、不要改遊戲邏輯（soul.js、controller.js）。
- **C: 槽幾乎滿**：所有暫存、渲染、連拍一律放 `D:\Documents\ThorWorkSpace\Remamber word game\art\v3\tmp\<你的角色>\`，用完清掉大檔。
- 回覆與文件用繁體中文（台灣用語）。

## 檔案所有權（只改自己的）
| 角色 | 擁有的檔案 | dev 埠 |
|---|---|---|
| 分析師 1 | `art/v3/specs/{boss_sentinel,boss_priest,hero_knight}.md` | – |
| 分析師 2 | `art/v3/specs/{boss_executioner,boss_devourer}.md` | – |
| 建模 sentinel | `art/blender/v3_sentinel_*.py`、`public/models/boss_sentinel.glb`、`art/blender/export_raw/boss_sentinel.clipmeta.json`、`art/blender/source/v3_sentinel*.blend` | 5191 |
| 建模 priest | `art/blender/v3_priest_*.py`、`public/models/boss_priest.glb`、對應 clipmeta／blend | 5192 |
| 建模 executioner | `art/blender/v3_executioner_*.py`、`public/models/boss_executioner.glb`、對應 clipmeta／blend | 5193 |
| 建模 devourer | `art/blender/v3_devourer_*.py`、`public/models/boss_devourer.glb`、對應 clipmeta／blend | 5194 |
| 建模 hero | `art/blender/v3_hero_*.py`、`public/models/hero_knight.glb`、對應 clipmeta／blend | 5195 |
| 審查 1（sentinel、priest、hero） | `art/v3/reviews/{boss_sentinel,boss_priest,hero_knight}.md` | 5196 |
| 審查 2（executioner、devourer） | `art/v3/reviews/{boss_executioner,boss_devourer}.md` | 5197 |

共用 lib 不准改；要改就複製成自己的 `v3_<id>_*.py`。`merge_clipmeta.py` 從各自的 export_raw 檔合併，誰跑都安全。

## 模型合約（遊戲端依賴，必須相容）
- 檔名不變；遊戲縮放身高：hero 1.8 左右（見現有）、sentinel 3.1、priest 3.2、executioner 3.4、devourer 3.9。
- 骨架與片段：保留現有 GLB 的所有動作片段名稱（Boss：Idle, IdleAggro, Stalk, StrafeL, StrafeR, Enter, Telegraph, Attack, Attack2, Combo3, Delayed, Dash, Hit, Stagger, PhaseShift, Roar, Die，devourer 加 PhaseShift2；hero 照 `clipmeta.json` 的 hero_knight 清單），hit 時間對準武器命中瞬間，完成後更新 export_raw 並跑 merge。比例改了就要重新檢查所有動作有無穿模、武器握持、腳底貼地。hero 的武器尖端等節點名稱照現有 GLB（先讀現有 GLB 的節點清單）。
- 型態部件：二階 `P2_*`、三階 `P3_*`，剛性綁骨，用「群組節點 scale 0＋子 mesh」匯出（meshopt 量化問題，見 modeling_a.md）；二階起要消失的原部件命名 `X2_*`（例如 priest 腰間經書在二階變成浮書）、三階要消失的命名 `X3_*`。發光材質名含 `Glow`。
- 預算：每隻 ≤ 50k 三角面、GLB ≤ 4.5 MB、貼圖 ≤ 2048（可用兩組 A/B 貼圖）；`python art/blender/check_soul_glb.py` 必須 OK。

## 品質標準（審查依此判定）
1. **比例**：與 specs 比例表逐項比對（以身高為 1 的相對直徑／長度），誤差 ≤ 10%。手臂、手腕、腰、胸、大腿、小腿、頭、肩寬都要量。
2. **材質區分**：每個部位的材質與 specs 材質表一致，近看能分辨布（織紋、毛邊、破洞、垂墜）、皮（皺褶、縫線）、鎖子甲（環）、板甲（錘紋、刮痕、邊緣磨亮）、鏽、骨、紙（纖維、焦邊）、冰。不同材質的粗糙度／金屬度要明顯不同。
3. **紋理**：法線貼圖要有可見細節（縫線、鉚釘、刻紋、凹痕、布紋）；不可是一片平滑的單色。
4. **布料**：布要有厚度與垂墜皺褶，不是一塊平板或圓錐；披風、袍擺要分層、破邊。
5. **壓迫感**：剪影寬厚、重心低、肩背厚重、頭小身大的比例感、武器尺寸有份量；姿勢（Idle）前傾帶威脅。
6. **與參考圖相符**：並排渲染（同視角、同光線）看得出是同一個角色。
7. 遊戲內：載入正常、動作正常、無 console error，暗場地中輪廓可讀。

## 審查流程
建模完成第一版 → 在 `art/v3/reviews/<id>.md` 寫「待審」並通知 lead → 審查做並排渲染＋比例實測（Blender 量 bounding box／截面直徑）→ 寫出具體問題清單（含數值與截圖）→ 建模修改 → 審查複查。最多三輪，直到 7 項全部通過。

## 交付
建模：`art/v3/reports/<id>.md`（三角面、大小、比例實測表、材質表、預覽路徑、遊戲截圖、已知問題）。審查：`art/v3/reviews/<id>.md`（每輪問題清單與結論：通過／不通過）。
