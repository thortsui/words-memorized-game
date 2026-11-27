# 設計報告（Design）

## 做了什麼
- 撰寫 `art/v2/design.md`（約 330 行）：
  - 整體美術方向「墨與鏽」：黑暗寫實＋東方水墨＋金箔點綴；玩家力量＝金、Boss 力量＝墨＋主色。
  - 5 隻 Boss：定位、剪影關鍵字、材質配色（含主色 hex）、一／二階（devourer 三階）的 `P2_*`/`P3_*` 部件與 `Glow`、招牌特效、PhaseShift 逐拍分鏡與爆發時間點。
  - Gemini 英文提示詞 11 段（每隻每型態）＋五隻比例圖 1 段。
  - 階段轉換通用時間軸（≤ 2.8 s）與各 Boss 差異表。
  - 特效清單 24 項（P0/P1/P2）＋手機粒子預算與降級規則。
  - 畫面基準（bloom、色調、暗角、霧、rim 光）、場地主色表、階段壓迫規則。
  - 打擊感分級表 S0–S7。
  - 驗收標準（美術、建模、特效、畫面、感覺、動畫、整體完成定義）。

## 讀過的現況
- `src/battle/data.js` SOUL_BOSSES；`soulScene.js` 的 ARENA、`bossPhase()`、hitStop／shake／slowmo 現值；`fx.js` 粒子池上限；`post.js` 與 bloom 現值。
- 圖：`art/reference/boss5_word_devourer_king.jpg`、`art/blender/preview/boss_sentinel_views.jpg`。

## 改了哪些檔
- 新增 `art/v2/design.md`、`art/v2/reports/design.md`。未改任何程式碼。

## 已知問題／待決
- devourer 若只做一條 PhaseShift，三階差異靠程式補足（可選加 `PhaseShift2`，需動畫判斷是否存在）。
- hitstop／bloom 等為目標值，手機實測不足時可下修，請在各自報告註明。
