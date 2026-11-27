# 畫面 Screen 報告（v2）

## 做了什麼
- **後製（post.js）**：調色 pass 新增 6 個「預設關閉」的效果：暗部冷色抬升 `lift`、高彩度保留 `keep`（Boss 主色不被降飽和）、水墨筆刷邊 `ink`（雜訊打散的墨色邊，以畫面角落正規化，直式手機也看得到）、全畫面閃光 `flash`、徑向色差 `chroma`、徑向模糊 `blur`。色差／模糊只在數值 > 0 時才多取樣（uniform 分支）。新增 `setGrade / setBloom / setFx`。打怪模式、封面不傳這些參數 → 輸出與原本完全相同。
- **新檔 screen2.js（魂系畫面層）**：
  - 基準（design §5.1）：bloom 0.7 / 0.55 / 門檻 0.82；sat 0.90、contrast 1.08、暗部 #dfe8ff、亮部 #ffe9c8、暗部冷青抬升；暗角 0.38、顆粒 0.03；曝光 1.65→1.45（畫面整體壓暗，讓 Glow 與火光跳出來）。
  - **Boss 主色輪廓光**：不新增燈（不重編 shader），把既有 Boss 背後的 rim 平行光染成「冷色＋主色」（sentinel/gargoyle 0.5、priest 0.45、executioner 0.55、devourer 0.7，階段越高越多）；另在 Boss 身後放一張主色加色背光暈 sprite，讓剪影從霧中跳出。
  - **階段壓迫（§5.3）**：自動跟著 soulScene 的 `phaseTint`，1.2 秒內漸變：暗角 0.38/0.46/0.55、飽和 0.90/0.86/0.80（主色保留）、bloom 0.70/0.78/0.85、墨邊 0/0.2/0.55、環境光 100/85/70% 且偏主色 0/12/25%（只改 hemi 顏色，不和別人的強度補間打架）、環境粒子 ×1/×1.3/×1.5（多出的部分是主色餘燼）。
  - **霧色亮度上限**：轉階段後霧色可偏主色，但亮度不得超過該場地基準 ×1.1（原本二、三階霧色變亮，devourer 三階整片亮紅；現在是更暗的暗紅）。
  - **場地環境粒子（§4 #24）**：1 個 Points、1 次 draw call、位置全在 vertex shader 算：灰燼片＋零星火星（gate）、碎石塵（cathedral）、細雪（chapel）、上升墨粒（yard）、旋轉書頁碎片（throne）。換場地時淡出再換。
- **engine.js**：只加 `E.screen=null` 欄位（約定 API 位置）。
- **soulScene.js**：加 2 行（import＋`createScreen2(eng,{hemi,rim,boss:()=>boss,phase:()=>phaseTint})`），沒動 `bossPhase()`。

## API（`eng.screen`，時間單位 ms；phaseShow.js 使用）
| 函式 | 說明 |
|---|---|
| `flash(color, strength=.12, ms=120)` | 全畫面閃光。安全上限（§5.4）：白 ≤0.15、紅 ≤0.3、其他 ≤0.22；每秒最多 3 次，120 ms 內重複呼叫併入目前這次；reduced motion 減半。低畫質改用 DOM 疊層。也接受物件參數 `{color,opacity,dur(秒)}`。 |
| `pulseChromatic(k=.6, ms=160)` | 徑向色差，k 0–1.5（1≈邊緣 1.2%）。 |
| `pulseRadial(k=.5, ms=180, at)` | 徑向模糊（6 tap），at＝世界座標 Vector3 或畫面 [u,v]。 |
| `pulseBloom(peak=1.1, ms=150)` | 泛光強度脈衝到 peak（完美斬／終結斬）。 |
| `inkSqueeze(k=.6, inMs=150, holdMs=150, outMs=450)` | 墨邊收縮（§3 爆發前 T−0.15）。 |
| `desaturate(sat=.3, holdMs=400, outMs=500)` | 暫時去色（devourer 三階爆發）。 |
| `setPhaseMood(n, dur=1.2)` | 手動指定階段氛圍 0/1/2（dur 秒）；預設自動跟 phaseTint，換 Boss 或傳 null 恢復自動。 |
| `impact(level, at)` | §6 S3–S5 的組合包（色差＋閃光＋泛光＋徑向模糊）。 |
| `hurt(heavy)` | 玩家受擊紅閃＋色差。 |
| `state()` | 除錯：目前 mood、脈衝、粒子數。 |

**秒為單位的相容介面（feel.js 用）**：`eng.screen2.flash({color,opacity,dur})`、`eng.screen2.pulseChromatic(k,dur)`、`pulseRadial(k,dur,at)`、`pulseBloom(peak,dur)`、`setPhaseMood(n,dur)`；同名函式也從 `screen2.js` 具名匯出（轉給目前作用中的魂系場景，沒有魂系場景時什麼都不做）。**dur 一律是秒**。

## 效能與降級
- 不新增燈；粒子 1 draw call（high 260→最多 390 顆，low 91 顆，reduced motion ×0.6）；背光暈 1 張 sprite。
- engine 降成 low：後製整個關（原本行為），閃光／暗角改 DOM 疊層。FPS < 42（還沒降級前）：關顆粒、色差、模糊、墨邊。
- reduced motion：不做色差、模糊、泛光脈衝；閃光減半；粒子變慢。
- FPS（headless Chrome，DPR 2，鎖 high，整場五隻 Boss 中位數）：手機 390×844 **57 → 55**、桌機 1280×800 **43 → 42**（誤差範圍內，同機器 run-to-run 差距相近）。鎖 low 跑整場 0 pageerror。

## 驗證
- 前後對照（五隻 Boss 一階／二階／devourer 三階；手機直式＋桌機）：`art/v2/shots/screen/before-390x844/`、`after-390x844/`、`before-1280x800/`、`after-1280x800/`；拼圖 `compare-390x844.jpg`、`compare-1280x800.jpg`（上排前、下排後）。低畫質 `lowq-390x844/`；API 目視 `api-390x844/`、`api-sheet.jpg`（閃光上限、色差、徑向模糊、墨邊、去色、二／三階 mood）。
- 結果：整體更暗、冷墨底＋暖光；Boss 身後有主色背光、剪影清楚；二階起暗角＋墨邊＋霧更暗，壓迫感遞增（原本二階是整片亮綠／亮紫、三階亮紅平塗）。
- `URL0=http://127.0.0.1:5183/ node verify.mjs soul`：五隻 Boss 全打完、勝利，0 pageerror、0 console error。`monster`：打完 5/5、62/62，0 pageerror（第一次跑被別人存檔觸發的 HMR 整頁重載打斷，用同一腳本＋攔 HMR 的副本 `verify_nohmr.mjs` 重跑通過）。`node tests/check.mjs`：exit 0。
- 測試腳本：scratchpad `pt/scrshots.mjs`（截圖＋FPS，攔掉 vite HMR 避免別人存檔時整頁重載）、`pt/scrapi.mjs`。

## 已知問題／給別人
- 低畫質那次跑到 devourer 轉階段時 console 有一筆 warning：`phaseShow.js:206 at is not a function`（動畫的檔，不是我的；已被 engine 的 tween 保護吃掉，不是 pageerror）。
- 地板（月光＋主角聚光燈）仍偏亮偏藍，要再壓需要改 soulScene 的燈值或地板材質（共用檔，我沒動）。
- `bossPhase()`／phaseShow 的霧色混色比設計多；我用亮度上限兜住，色相保留。
