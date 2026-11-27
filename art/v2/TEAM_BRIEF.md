# 單字魂 v2 美術／特效／Boss 重建：團隊合約

專案：`D:\Documents\ThorWorkSpace\Remamber word game`（Vite + vanilla JS + Three.js）。魂系模式＝答題驅動的 3D Boss 戰（主角騎士 vs 5 隻 Boss）。
使用者要求：畫面要有更多特效；所有 Boss 建模重建（**先做參考圖才能建模**）；Boss 切換型態（階段轉換）要有更好的動畫。

## 不可違反
- 角色全部原創。可參考黑暗奇幻／魂系的「感覺」，**不可複製**任何既有遊戲（黑神話、黑暗靈魂、艾爾登法環…）的角色、名稱、造型、招式或美術。
- Blender 只用 headless：`"/c/Program Files/Blender Foundation/Blender 4.2/blender.exe" --background --factory-startup --python <script> -- <args>`。**絕對不要用 Blender MCP。**
- 參考圖用使用者 Chrome 裡已登入的 Gemini 生成（claude-in-chrome 工具），存 `art/reference/v2/`。
- 不要 git commit / push（由 lead 統一提交）。不要改別人負責的檔案（見下表）。
- 回覆與文件用繁體中文（台灣用語）。
- 不要跑 `npm run build`（會互相覆蓋 dist）。驗證畫面請用自己的 dev server：`npx vite --port <你的埠> --strictPort`，結束時關掉。
- 遊戲邏輯／數值（`src/battle/soul.js`、`controller.js` 的規則）不准改，難度已定案。

## 角色與檔案所有權
| 角色 | 負責 | 擁有的檔案（只有你能改） | dev 埠 |
|---|---|---|---|
| 設計 Design | 總體規格：5 隻 Boss 定位、各階段型態、轉換分鏡、特效清單、手感目標 | `art/v2/design.md` | – |
| 美術 Art | 參考圖（每隻 Boss 一階／二階型態，噬語魔王含三階）＋風格指南 | `art/reference/v2/**`, `art/v2/art_guide.md` | – |
| 建模 A | 重建 sentinel、gargoyle、priest | `art/blender/v2a_*.py`, `public/models/boss_{sentinel,gargoyle,priest}.glb` | – |
| 建模 B | 重建 executioner、devourer | `art/blender/v2b_*.py`, `public/models/boss_{executioner,devourer}.glb` | – |
| 特效 VFX | 新增／升級粒子、刀光、命中、Boss 招牌特效 | `src/battle/view3d/fx.js`, `bossfx.js`, 新檔 `src/battle/view3d/vfx2.js` | 5182 |
| 畫面 Screen | 後製（bloom、色調、暗角、景深感）、打光、場地氛圍、螢幕閃光 | `src/battle/view3d/post.js`, `engine.js`, 新檔 `src/battle/view3d/screen2.js` | 5183 |
| 感覺 Feel | 打擊感：hitstop、震屏、鏡頭衝擊、慢動作、受擊反饋時序 | 新檔 `src/battle/view3d/feel.js`（可在 soulScene.js 加少量掛鉤） | 5184 |
| 動畫 Animation | 階段轉換（型態切換）演出：分鏡、鏡頭、型態節點切換、銜接 | `soulScene.js` 的 `bossPhase()` 一段、新檔 `src/battle/view3d/phaseShow.js` | 5185 |

`soulScene.js` 是共用檔：只有動畫可改 `bossPhase()`；其他人若必須掛鉤，只加**一兩行呼叫**到自己新檔的函式，改之前重新讀檔，用精確字串 Edit，不要整檔重寫。

## 模型合約（建模 ↔ 動畫 ↔ 程式）
- 檔名不變：`public/models/boss_<id>.glb`。身高（遊戲會縮放到）：sentinel 3.1、gargoyle 3.0、priest 3.2、executioner 3.4、devourer 3.9。
- **動作片段名稱與 hit 時間必須相容**：見 `src/battle/view3d/clipmeta.json` 各 boss 的 clips 清單（Idle, IdleAggro, Stalk, StrafeL, StrafeR, Enter, Telegraph, Attack, Attack2, Combo3, Delayed, Dash, Hit, Stagger, PhaseShift, Roar, Die）。片段長度可調，但重建後要用 `art/blender/merge_clipmeta.py` 更新 clipmeta（hits 要對準武器命中瞬間）。
- 型態節點：二階型態才出現的部件命名 `P2_*`（三階 `P3_*`），匯出時**預設隱藏**（visible=false 或 scale 0）；發光部位材質名含 `Glow`（emissive）。動畫負責在 PhaseShift 中途把它們顯示＋特效遮掩。
- `PhaseShift` 片段 2.0–2.6 秒，要有明確的「變身」肢體動作（蓄力→爆發→新姿態），在 clipmeta 標一個 hit（爆發瞬間）。
- 預算：每隻 ≤ 40k 三角面、貼圖 ≤ 2048，GLB ≤ 3 MB；用 `art/blender/check_soul_glb.py` 驗證。可參考現有 `build_boss_*.py`、`soul_creature_lib.py`、`soul_humanoid_*.py` 的做法，但**不要改共用 lib**，需要就複製成自己的 `v2a_/v2b_` 檔。
- 參考 Blender 輸出的預覽圖（`art/blender/preview/`）自行檢查造型與動作，必須跟參考圖相符。

## 交付
每個人完成時在 `art/v2/reports/<角色>.md` 寫：做了什麼、改了哪些檔、怎麼驗證（截圖路徑）、已知問題。
