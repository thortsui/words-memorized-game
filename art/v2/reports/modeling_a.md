# 建模 A 報告：sentinel／gargoyle／priest 重建

## 做了什麼
三隻 Boss 都照 `art/reference/v2/*` 與 design.md／art_guide.md 重建：模型、二階 `P2_*` 部件、17 個動作片段（PhaseShift 依分鏡重做）、匯出、壓縮、clipmeta 合併，也在遊戲裡驗證過。
所有 Blender 都用 headless（`--background --factory-startup`）跑，沒有用 Blender MCP。沒有改 build_* 舊腳本、共用 lib，也沒碰 executioner／devourer 的檔案。

### 新檔（全部是建模 A 的）
| 檔案 | 用途 |
|---|---|
| `art/blender/v2a_lib.py` | P2 部件標記與拆分（剛體掛骨頭）、獨立的 Glow 材質、匯出、動作預覽（P2 依片段顯示或隱藏） |
| `art/blender/v2a_hactions.py` | 複製自 `soul_boss_actions.py`，加了 `phase=` 參數，讓各 Boss 自訂 PhaseShift |
| `art/blender/v2a_sentinel.py`／`v2a_priest.py` | 人形 Boss：沿用 soul_humanoid_* 的骨架、烘焙與動作系統（只 import，沒改） |
| `art/blender/v2a_gargoyle.py` | 生物 Boss：沿用 soul_creature_lib（只 import）。動作 import 自 `build_boss_gargoyle.define_actions`，用包裝器套到新的蹲伏骨架，PhaseShift 換成 v2 版 |
| `art/blender/v2a_post.py` | GLB 後處理。`--pre`：壓縮前把剛體 P2 拆成「群組節點＋`_mesh` 子節點」。壓縮後：群組節點 scale 設 0，並寫 extras `{form:2, hiddenByDefault:true}` |
| `art/blender/v2a_run.sh` | 一鍵流程：Blender → 預覽拼圖 → `--pre` → gltf-transform（meshopt、webp 1536；flatten／join／palette／instance 都關掉，保留節點）→ 後處理 |
| `art/v2/tmp/pt/v2a_shots.mjs` | 實機截圖腳本（每 1.4 秒截一張） |

輸出：`public/models/boss_{sentinel,gargoyle,priest}.glb`、`art/blender/export_raw/boss_*.clipmeta.json`。已執行 `merge_clipmeta.py`，`src/battle/view3d/clipmeta.json` 已更新。

### 重要技術注意（給動畫／程式）
- 剛體 P2 的結構是：群組節點 `P2_X`（掛在骨頭下，scale 0）底下接一個子節點 `P2_X_mesh`。
  - 原因：gltf-transform 的 meshopt 量化會把反量化用的縮放寫進掛網格那個節點的 scale。
  - 如果把 P2 直接 scale 0，phaseShow 彈出時會把 scale 設回 1，網格就變得巨大。第一輪實機測試真的出現這個問題，改成群組節點後已修好。
  - 建模 B 如果也是 meshopt＋剛體 P2，可能會碰到同樣的問題。
- gargoyle 的 `P2_WingMolten_L/R` 是 **SkinnedMesh**。
  - 翼膜由多根骨頭一起變形，做成剛體會和翼膜分離，所以改成蒙皮。
  - 節點維持 scale 1，extras 加 `skinned:true`。phaseShow 載入時會把它設成不可見，爆發那一格再切成可見（沒有彈出效果）。
- gargoyle 的主體石材材質名是 `GargoyleStone_Glow_Rune`。石縫熔光在 emissive 貼圖上，材質名含 Glow，轉階段時會一起變亮。
- priest 光環掛在額外骨頭 `HaloSpin`（Head 的子骨）上。IdleAggro 每個循環轉 30°；光環 12 段對稱，所以首尾無縫。

## 各 Boss 數據（`check_soul_glb.py` 三隻都 OK）
| | sentinel | gargoyle | priest |
|---|---|---|---|
| 三角面（壓縮後） | 37,832 | 39,445 | 23,887 |
| GLB | 2.45 MB | 1.54 MB | 2.24 MB |
| 貼圖 | 2048 烘焙 → webp 1536 | 2048 → 1536 | 2048 → 1536 |
| Glow 材質 | Glow_Eye／Rune／Weapon、P2_Glow_Heart／Root／Weapon | GargoyleStone_Glow_Rune、Glow_Eye／Weapon、P2_Glow_Maw／Wing | Glow_Eye／Rune／Weapon、P2_Glow_Halo／Book／Veins |
| Tip_Weapon | 有（骨頭，在戟尖） | 無（爪擊型，bossfx 會改用武器骨或手） | 有（在槍尖） |

### P2 節點
- **sentinel**（9 個）
  - `P2_RootArms`：門板裂縫、7 條粗根扇形張開，寬約 1.2H，掛 Spine2
  - `P2_RootSpikes_ShoulderL/R`、`_ForearmL/R`、`_KneeL/R`：木刺
  - `P2_Heart`：胸口綠光樹心＋放射裂紋
  - `P2_HalberdRoots`：戟纏根＋綠光戟尖棘
- **gargoyle**（8 個）
  - `P2_WingMolten_L/R`：蒙皮的熔岩裂網，翼膜兩面都有
  - `P2_Horns`：角加長、分岔
  - `P2_Maw`：口內熔光＋撕裂到頰邊
  - `P2_Fangs`：長牙
  - `P2_SpineShards_Spine2／Spine1／Hips`：背脊碎石尖片
- **priest**（7 個）
  - `P2_CrownHalo`：直徑約 1.1 m（約 0.5H），12 段荊棘冰環＋碎冰
  - `P2_CrownGrow`：冰冠變成 9 根長尖晶
  - `P2_FloatingBook`：翻開、發光的書頁，懸浮在左前方
  - `P2_IceShards`：袍擺外 46 根貼地冰刺
  - `P2_VeinsFace`、`P2_VeinsHandL/R`：冰藍血管紋

### 片段與命中時間（秒）
17 個片段都齊全，名稱與合約一致，都從第 0 秒開始。

| 片段 | sentinel | gargoyle | priest |
|---|---|---|---|
| Attack | 0.467 | 0.367 | 0.433 |
| Attack2 | 1.0 | 0.967 | 0.967 |
| Combo3 | 0.567／0.967／2.033 | 0.433／0.867／1.833 | 0.633／0.967／2.0 |
| Delayed | 1.767 | 1.867 | 1.767 |
| Dash | 0.3 | 0.4 | 0.3 |
| PhaseShift（長度／爆發 hit） | 2.4 s／1.133 | 2.2 s／1.033 | 2.5 s／1.233 |

- 命中時間取的是武器尖端（gargoyle 為爪或尾）在標記附近的速度峰值。
- PhaseShift 分鏡：
  - **sentinel**：戟插地、單膝跪下垂頭 → 被吊起 → 1.1 s 拔戟高舉 → 戟橫胸前 → 進 IdleAggro。
  - **gargoyle**：雙翼包住全身縮成雕像 → 顫抖 → 1.0 s 展翼仰頭咆哮 → 拍兩下翅膀半騰空 → 落地、尾巴甩動 → 進 IdleAggro。
  - **priest**：槍立身側、左手合於胸前禱念 → 升空 0.3 m → 1.2 s 雙手張開 → 緩降、槍尖指向玩家 → 進 IdleAggro。

## 預覽圖（`art/blender/preview/`）
| | 檔案 |
|---|---|
| 正面／側面／背面／3/4／P2 3/4／P2 背或正面 | `v2a_boss_sentinel_views.jpg`、`v2a_boss_gargoyle_views.jpg`、`v2a_boss_priest_views.jpg` |
| 17 片段連拍（每段 8 格） | `v2a_boss_*_actions.jpg` |
| 上半身特寫 | `v2a_boss_*_closeup.jpg` |
| 各片段單列 | `preview/_tiles/v2a_boss_*/strip_<片段>.jpg` |

舊的 `boss_*_views.jpg` 保留，方便對照。

## 遊戲內驗證
- dev server：5186 埠，已關閉。
- 實機截圖：`art/v2/reports/shots/sentinel_*.jpg`（22 張）、`gargoyle_*.jpg`（18 張）、`priest_*.jpg`（17 張）。檔名 `_p0` 是一階、`_p1` 是二階。
- 檢查結果：三隻都能載入，大小與朝向正確，動作正常。PhaseShift 時 P2 部件會彈出，二階剪影明顯改變（sentinel 的樹根扇形、gargoyle 的熔岩翼、priest 的光環＋冰刺）。
- `URL0=http://localhost:5186/ node verify.mjs soul`（腳本複製到 D: 的 `art/v2/tmp/pt/`）：五隻全部打完，pageerror 0，console error 0。
  - 注意：vite 預設只聽 localhost，用 127.0.0.1 會連不上。

## 已知問題／待決
1. **gargoyle 動作**：沿用舊版的姿勢，透過包裝器套到新的四足骨架，所以部分片段（Stagger、Die）的姿勢不夠精緻。前肢沒有 IK，身體大幅移動時手掌會在地上滑動。
2. **gargoyle 發光太亮**：二階的 `P2_Glow_Wing` 疊上程式的 Glow 倍率後偏亮。建議動畫端或畫面端把它的倍率壓低；我也可以把材質強度從 2.2 降到約 1.4（只需重跑 anim 階段）。
3. **gargoyle 沒有 `Tip_Weapon`**：特效會退回用武器骨或手的位置。
4. **priest 造型**：兜帽外形偏筒狀，寬口袖比參考圖大。袍子是單層外殼加上腿部權重，大步移動時腿會有些微穿出袍子。
5. **sentinel 穿插**：PhaseShift 的跪地與吊起段有幾格手臂伸到極限（reach 超出約 20 cm，系統會自動截斷）。背後門板在大幅揮擊時和後擺布料會有輕微穿插。
6. **經書重複**：priest 的 P2 浮書是新部件，腰間闔起的經書不會消失，所以二階時兩本書同時存在（P1 部件無法隱藏）。
7. 暫存檔都放在 `art/v2/tmp/`（D: 槽）。其中 log 與 `pt/` 腳本可以刪除。
