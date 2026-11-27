# 動畫（Animation）報告：Boss 階段轉換演出

## 做了什麼
- 新檔 `src/battle/view3d/phaseShow.js`：整段轉換演出（時間軸、鏡頭、慢放、閃光遮掩、`P2_*`/`P3_*` 型態節點切換、Glow 變亮、各 Boss 差異）。
- `src/battle/view3d/soulScene.js`：
  - `bossPhase()` 改成只提供掛鉤，呼叫 `pshow.run()`；`finally` 保證交還 AI（`AI.busyUntil=0`）、清掉 cine 鏡頭、關掉借用的點光、設好 phaseTint／IdleAggro。
  - 另加 2 行掛鉤：`import { createPhaseShow }`、`const pshow=createPhaseShow({eng,fx,bfx,getBoss:()=>boss})`（在 `bfx` 下一行；型態節點必須在模型載入時就隱藏，不能等到 bossPhase）。
- `src/style.css`：**只改 `.v3-banner.soul.phase` 相關**——原本一行 `.v3-banner.soul.phase span{color:#ff8a70}` 換成水墨筆刷橫幅（內嵌 SVG 筆刷底、0.3 s 由左展開），加 `ph-<boss>` 主色、priest 細筆、executioner 斧痕切口、devourer 紅字金邊、`p3` 放大 1.2 倍＋震動；新增 keyframes `v3phIn`／`v3phCut`／`v3phShake` 與一條 reduced-motion 規則（p3 不震）。

## 時間軸（遊戲時間；T＝爆發）
片段速度 `sp=clamp(max(hit/1.02, 片長/2.5), .75, 2.4)`，T＝`clamp(hit/sp, .75, 1.02)`（現有 GLB 的 PhaseShift 沒有 clipmeta hit，用 IMPACT 表 30% → T=0.75；新 GLB 標了 hit 會自動對齊）。
| 時間 | 內容 |
|---|---|
| 0 | 停威脅條、HUD 淡到 40%、低頻嗡鳴、地面主色符紋圈、播 PhaseShift；cine 鏡頭移到低機位仰拍（約 0.35 s 收斂） |
| 0→T−0.15 | 緩推 0.6 m、FOV 50→44、主色粒子向 Boss 吸入（≤60）、glow 0.5→1、Glow 材質 ×1→×1.5、爆發點光漸亮（借 `danger` 點光，用完歸零）、注視點 0.5→0.62 身高（Boss 跪下時不出框） |
| T−0.15→T | `eng.slowmo(.35, 323ms)`＝約 0.15 s 遊戲時間；`eng.screen.inkSqueeze` 墨邊收縮（沒有 screen API 時用自己的 DOM 墨邊） |
| **T** | 同一格：`P*` 節點 scale 0→1.08→1（0.25 s）、Boss 身上加色閃光精靈（滿亮 0.05 s≈3 幀，再白→主色淡出）、`eng.screen.flash(白,.15,120)`、震屏 .16/.9/11、FOV +6 回彈、`bfx.phaseBurst`、主角擊退 0.4 m＋Guard、水墨橫幅、霧色／火光 1.2 s 漸變、常駐 aura、`setPhaseMood` |
| T→T+0.85 | 鏡頭繞 Boss 15° 並退 0.5 m、注視點抬到頭部；Glow 由 ×1.8 回到新階段底值（二階 ×1.7、三階 ×2.3） |
| T+0.85 | 解除 cine，`csReset(.45)` 回戰鬥機位 |
| T+0.8–1.2 | 片段快播完時切 IdleAggro |
| T+1.3 | 結束：交還 AI、glow 底值（二階 .7、三階 1.0） |
實測（screencast 錄影中，真實時間）：一般 2.22–2.25 s；devourer 三階（有 PhaseShift2）2.68 s；全部 ≤ 2.8 s。遊戲時間 2.05–2.41 s。
`eng.rm`：不用 cine 鏡頭、不慢放（引擎本來就關）、震屏由引擎關掉；其餘照常、時長相同（實測 2.06–2.69 s）。

## 各 Boss 差異（design §3.2）
| Boss | 鏡頭 | 爆發特效 |
|---|---|---|
| sentinel | 偏側 50°、看頭頂上方 | 6 方向樹根破土（延遲 0–0.2 s）、木屑、苔綠孢子 |
| gargoyle | 機位 0.85 m、爆發後上揚 8° | 石殼碎片（有重力）、熔橘火星上竄 |
| priest | 正面 28°、低機位 0.35 m | 結霜圈 0.4 s 擴到 r 8、12 根冰刺一圈、雪粒停頓再落 |
| executioner | 爆發瞬間硬切側面 0.14 s 再切回（直接設鏡頭位置，不經彈簧） | 斧落點 7 道紫色放射裂痕、影臂墨絲、左右 2 道殘影 |
| devourer 二階 | 爆發前 0.38 s 推到胸口特寫，之後退開 1.6 m | ≤36 片書頁飛旋組成背後紙翼、金字粒子從主角被吸向胸口 |
| devourer 三階 | 先拉遠（R≈7）看全身，爆發瞬間急推 | 墨邊強收縮、紅光環炸開、墨潮環推到場邊、`eng.screen.desaturate(.3,400,500)`（沒有就退回直接調 post uSat）；有 `PhaseShift2` 就用，沒有就 PhaseShift＋顫抖 |
直式畫面（水平視角窄）鏡頭半徑自動 ×1.22；鏡頭與主角水平距離至少 1.7 m、最遠半徑 9.3 m（不穿牆／石柱）。

## 型態節點合約（給建模 A/B）
- 名稱 `P2_*`＝二階、`P3_*`＝三階出現；只看最上層 P 節點，子節點跟著。
- 匯出時隱藏：建議 **scale 0**（glTF 沒有 visible）。scale 0 匯出的節點顯示後目標 scale 視為 1；不是 0 的以匯出值為準。就算沒藏好，載入後也會被藏（每幀在混合器之後套用）。
- **建議做成剛體**（一般 Mesh／Group parent 到骨頭）或名為 `P2_*` 的骨頭：才有 scale 彈出。SkinnedMesh 縮放無效，只能在爆發那格切可見（仍有閃光遮掩；已預先 compile shader 避免卡頓）。
- 片段裡若 key 了 P 節點的 scale（例如 IdleAggro 設為 1），以片段為準；隱藏期間會壓回 0。
- 材質名含 `Glow` 的會在蓄力／爆發／新階段調 emissiveIntensity 倍率。
- 新片段 `PhaseShift` 的 hit 請在 clipmeta 標（爆發瞬間）；devourer 可加 `PhaseShift2`（也標 hit）。

## 驗證
- 自己的 dev server `127.0.0.1:5185`（已關閉）。測試腳本：`art/v2/shots/phase/_test_phase.mjs`（Playwright＋CDP screencast，攔截 `/@vite/client` 防止別人改檔觸發整頁重載）、`_test_mkglb.mjs`（在現有 GLB 加測試用 `P2_TestHorns`(scale 0)、`P2_TestUnhidden`(scale 1 沒藏好)、devourer `P3_TestHalo` 與複製出的 `PhaseShift2`，由 Playwright 攔截換入，不動 public/models）。
- 三種跑法都 0 pageerror、0 console error：nodes（有節點，直式 430×900）、rm（reduced motion）、plain（現有 GLB，無節點、無 PhaseShift2，桌面 1280×800）。五隻 Boss＋devourer 二、三階共 6 段都觸發並回到戰鬥。
- 逐格檢查：P 節點在爆發前看不到，爆發格被閃光蓋住 ≥2 幀後才出現；沒藏好的 P2 在一階被藏起來；鏡頭沒有鑽進主角或穿牆；結束後 Boss 回 IdleAggro、AI 繼續走位。
- `URL0=http://127.0.0.1:5185/ node verify.mjs soul`：done、5 隻打完、errors []。`node tests/check.mjs`：exit 0。
- 截圖 `art/v2/shots/phase/`：`portrait_0N-<boss>-pK_overview.jpg`（爆發前 1.3 s～後 2.4 s 每 0.15 s 一格，含測試節點）、`portrait_*_burst.jpg`（爆發附近逐格）、`rm_04-executioner-p2_overview.jpg`、`plain_*`（現有 GLB）＋ `plain_*-after.png`（轉換後 1.2 s 的戰鬥畫面）。截圖裡頭上的白／橘色幾何是測試用假節點，不是正式模型。

## 已知問題／給其他人
- **特效**：`bossfx.phaseBurst` 的光柱在低機位近景會蓋滿畫面；演出期間我暫時把 `fx.pillar` 包成細 40%、最長 0.6 s（只在呼叫 phaseBurst 那一刻，呼叫後還原）。建議 phaseBurst 支援參數關掉／縮小光柱。
- **感覺**：沒有呼叫 `feel.phase()`——它在同一時刻同時做慢放與震屏，但規格是「爆發前慢放、爆發時震屏」，所以由 phaseShow 自己依 FEEL S6 的數值（0.35 倍、0.16/0.9/11）分兩拍做。若 feel 拆成 `phasePre()`／`phaseBurst()` 可再改為呼叫。
- `bossRecover()`（不是我的）收招時把 glow 設回 0.7，三階底值 1.0 只維持到第一次收招。
- 機器的 C: 磁碟一度滿了（0 byte），影響錄影輸出；原始逐格已刪除，只留拼圖。
- 新 GLB 交付後重跑 `_test_phase.mjs plain portrait`（不攔截）即可複驗。
