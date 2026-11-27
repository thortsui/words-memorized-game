# hero_knight 主角騎士：v3 建模報告（第 1 版）

規格：`art/v3/specs/hero_knight.md`；參考圖：`art/reference/hero_knight_sheet.jpg`。

## 交付
| 項目 | 結果 |
|---|---|
| 遊戲檔 | `public/models/hero_knight.glb`：**3.50 MB**、**38,662 三角面**（Blender 內 43,494，gltf-transform 的 meshopt 簡化後）、25 骨、2 材質（A：板甲＋鎖子甲；B：布、皮、劍、鐵件） |
| 貼圖 | A、B 兩組各 2048²：basecolor／ORM／normal（webp） |
| 未壓縮原檔 | `art/blender/export_raw/hero_knight.glb`、`export_raw/hero_knight.clipmeta.json`（已跑 `merge_clipmeta.py`） |
| 檢查 | `python art/blender/check_soul_glb.py` → hero_knight **OK**（17 片段、骨頭齊全、時長與 clipmeta 一致） |
| .blend | `art/blender/source/v3_hero_knight.blend`（含不匯出的 `_RefPose` 對照站姿） |

## 腳本（重跑：`bash art/blender/v3_hero_run.sh`）
- `v3_hero_build.py` 主程式（材質表、組裝、骨架、動作、匯出、量測）
- `v3_hero_parts.py` 分件：頭盔、罩袍、皮件、肩甲、手臂、手套、腿甲、靴、圍巾、披風、劍；`V3Builder` 另產生 detail UV（縫線／織紋用）
- `v3_hero_bake.py` 烘焙（複製自共用版）＋ `define_v3` 程序化材質
- `v3_hero_actions.py` 動作（Idle 重做、Victory／Die 配合新劍長修正）；`v3_hero_rig.py`（V3Rig：披風鏈地板、劍鞘碰地往後擺、Roll 時披風改硬）
- `v3_hero_measure.py` 比例量測；`v3_hero_ground.py` 逐片段逐格量最低點、劍尖、披風穿身
- `v3_hero_preview.py`／`v3_hero_sheet.py` 預覽與並排圖
- 共用 lib 一律沒改。

## 骨架／動作相容
- 原有節點全部保留：Root、Hips、Spine、Spine2、Neck、Head、Shoulder/UpperArm/Forearm/Hand ×L/R、Thigh/Shin/Foot ×L/R、`Weapon`、`Cape1`–`Cape3`。**新增一根 `Scabbard`（掛在 Hips 下）**：劍鞘尖會低於地面時，逐格往後上擺（翻滾、跪地時不插地）。遊戲端不用這個名稱，不影響。
- 17 片段名稱與時長不變；命中時間 Slash 0.6、HeavySlash 0.933、Combo 0.333/0.667/1.4、Parry 0.2、Guard 0.233、Cast 1.067（劍尖速度峰值量出，跟原本一樣）。
- 劍光拖尾：`Weapon` 骨權重頂點的最遠點＝劍尖，遊戲內已確認拖尾跟著劍（`art/v3/tmp/hero/pt/herocheck/act2_*.jpg`）。

## 比例實測（rest pose，H=1.809 m；依 spec 第 7 節排除披風與劍）
| 項目 | spec | 實測 | 誤差 |
|---|---|---|---|
| 頭盔寬（0.93H） | 0.100H | 0.099H | −0.7% |
| 頭盔深 | 0.130H | 0.136H | +4.8% |
| 頭盔高 | 0.145H | 0.149H | +3.0% |
| 肩寬（0.80H） | 0.350H | 0.367H | +4.9% |
| 胸寬／胸厚（0.73H） | 0.24／0.14H | 0.225／0.146H | −6.4%／+4.6% |
| 腰寬／腰厚（0.60H） | 0.20／0.13H | 0.193／0.137H | −3.5%／+5.5% |
| 臀寬（0.52H） | 0.24H | 0.223H | −6.9% |
| 臀寬含皮袋 | 0.27H | 0.223H | **−17%**（皮袋沒有超出臀圍，見已知問題） |
| 上臂直徑 | 0.070H | 0.073H | +4.2% |
| 前臂直徑 | 0.060H | 0.061H | +1.4% |
| 手腕 | 0.050H | 0.048H | −4.9% |
| 手套袖口 | 0.075H | 0.080H | +7.3% |
| 大腿 | 0.100H | 0.094H | −5.7% |
| 膝 | 0.090H | 0.091H | +0.7% |
| 小腿 | 0.075H | 0.078H | +3.4% |
| 腳踝 | 0.065H | 0.061H | −6.7% |
| 腳長／腳寬 | 0.15／0.065H | 0.162／0.070H | +7.8%／+7.6% |
| 劍全長 | 0.60H | 0.585H | −2.6% |
| 護手 | 0.13H | 0.131H | +0.8% |
| Idle 站距（雙腳左右） | 0.18–0.21H | 0.196H | 範圍內 |

## 材質（spec 第 2 節）
| 部位 | 做法 |
|---|---|
| 板甲（頭盔、肩甲、膝甲） | 灰鋼 #868884（R 0.56／M 0.9），錘紋（Voronoi 淺碗）、3–5 個凹痕、以橫向為主的細刮痕、翻邊磨亮 #b0b2ad、鏽只在縫隙（AO 遮罩）暗褐 #5a4a3a，約 5% |
| 胸甲、護臂、腿甲 | 同上偏暗 #7c7e7a；脛甲 #777974，下緣 0.15H 內有泥 |
| 鎖子甲 | `acg_Chainmail004`（環約 1 cm），金屬環＋黑縫隙：護頸、上臂到肘、前臂內、腰下鋸齒鎖子甲裙、大腿 |
| 罩袍 | 灰藍亞麻 #5f6769，`acg_Fabric030` 織紋＋detail UV 經緯線、泥污水漬（暈開＋水痕邊）、褪色亮斑、胸口小破洞（貼圖）；前後兩片、側開衩、下擺 0.37H 撕成寬窄不一的布條（末端翻捲） |
| 披風 | 厚羊毛 #27324a（R 0.92），細絨法線＋粗織紋；下緣褪色 #3a4252、泥漬；外層＋略短內層，厚 1.1／0.9 cm，縱向皺褶，5＋2 個不規則圓破洞；胸前圍巾＋右胸圓環別針 |
| 皮件 | `acg_Leather026`＋皺褶＋龜裂＋detail UV 邊緣縫線（針距 0.004H）與邊緣磨淺：斜背帶、主腰帶（方扣＋垂尾）、斜劍帶、右胯皮袋、左胯劍鞘（鐵鞘口、中箍、包尾、兩條掛帶）、肘／前臂／大腿／脛甲皮帶扣 |
| 手套 | 手背甲＋每指 4 段指甲片＋拇指甲片（鋼）、手掌與手指底層皮革 |
| 劍 | 劍身 0.48H、菱形截面＋血槽（0.008H）、刃口磨亮、5 個小缺口；鐵護手兩端下彎；皮纏斜紋握柄；圓盤劍首 |

## 預覽
- `art/blender/preview/v3_hero_compare.jpg`：參考圖｜渲染（正面、左側面，同取景正交＋0.05H 格線），下排背面、3/4 前、3/4 後
- `art/blender/preview/v3_hero_closeups.jpg`：頭盔、左肩甲＋圍巾、胸腰皮件、罩袍下緣＋鎖子甲、披風背面、靴、劍
- `art/blender/preview/v3_hero_dark.jpg`：暗場（過肩視角、正面、背面）
- `art/blender/preview/v3_hero_actions_a.jpg`、`_b.jpg`：17 個動作各 8 格連拍

## 逐格穿地檢查（`v3_hero_ground.py`，17 片段、每一格）
全部片段的模型最低點與劍尖都 ≥ −0.02 m（最低：HitHeavy 披風角 −0.020、Die 左手 −0.018、Roll 右腳 −0.012；劍尖最低 Die +0.012、Victory +0.030，拄地）。結果在 `art/v3/tmp/hero/ground.txt`。
- 修掉的問題：劍鞘插地（Roll −0.36／HitHeavy −0.14 → 用 Scabbard 骨擺開）、披風下擺入地（Guard −0.14、Hit −0.09 → 鏈的地板高度遞增）、Die 劍尖 −0.34、Die 左手 −0.06。

## 遊戲內（vite 5195、Playwright）
- 封面（`coverScene`）主角剪影正常；魂系過肩視角大小正常、揮劍拖尾跟著劍、6 次攻擊動作正常，**0 pageerror、0 console error**（`art/v3/tmp/hero/pt/herocheck/`、`art/v3/tmp/hero/pt/game_sheet.jpg`）。
- `URL0=http://127.0.0.1:5195/ node verify.mjs soul`：**五隻全部打完（end=true）、0 pageerror、0 console error**（`art/v3/tmp/hero/pt/verify-soul/`）。注意：一般的 vite 開發伺服器會被其他建模師寫入 `public/models`／`clipmeta.json` 觸發整頁重新整理，造成驗證假失敗；我改用關掉 HMR 與監看的設定 `art/v3/tmp/hero/vite.nohmr.mjs` 來跑。

## 已知問題／待審
1. **Roll 第 17–20 格披風穿身**：倒立捲身那幾格，披風跟收起來的骨盆交疊，用我的軀幹橢圓柱近似量最深約 9.7 cm（畫面上看不太出來，但數字上未過）。試過加硬、加大碰撞半徑都沒改善，需要再改布料鏈或 Roll 姿勢。
2. 皮袋沒有超出臀圍（spec「含皮袋 0.27H」實測 0.223H）。
3. 左肩護頸翼偏薄，像一片立起的薄板；參考圖的比較厚。
4. 棚拍光下鋼甲還是比參考圖亮、乾淨一點（灰度在 spec 範圍內，但髒污可以再多）。
5. 腳長 +7.8%、手套袖口 +7.3%，在容許範圍內但偏大。

## 第 2 輪修改（回應 `art/v3/reviews/hero_knight.md` 第 1 輪）
- **罩袍（必修 1）**：拿掉長條，改成前後各一整片布，厚度 0.0072 m（0.004H，solidify）。只有最下緣 0.05H 撕成寬窄不一的鋸齒，每齒深度隨機，撕口微微翻捲。下緣長出毛邊線頭（`TabardFFray`／`TabardBFray`）。只留短裂口：前片 2 道、後片 1 道，長 0.05–0.08H，寬度不同。腰帶以下改成寬窄交錯的縱向垂墜皺褶。
- **披風（必修 2）**：破洞改成不規則撕裂形。輪廓是低頻不規則加高頻鋸齒，用較細的格子，洞緣頂點拉到輪廓上再往外翻捲 4–10 mm。洞緣和下緣加毛邊線頭（`CapeFray`／`CapeInnerFray`）。縱向皺褶外層約 6 條、內層約 5 條，一路垂到下緣。下緣撕口長短差提高到約 0.07H。
- **建議 3**：鋼甲凹處污垢從 0.75 加到 1.0，刮痕強度 ×1.5–1.6。罩袍泥污水漬範圍加大到約 35%（stain 1.25）。
- **建議 4**：脛甲正面依小腿形加前凸弧線（最大 1.2 cm），往腳踝收細。
- **低優先 Roll**：試過讓 Cape2／Cape3 沿背後外推 0.3 m（約 15–20°），穿身深度只從 9.6 降到 9.4 cm，而且披風角會入地 −0.025 m，所以撤回，維持第 1 版的狀態（審查判定為輕微）。
- 預算：41,515 面、3.70 MB；`check_soul_glb.py` OK。逐格穿地檢查 17 片段全過（最低 Die 左手 −0.018、Roll 右腳 −0.012、HitHeavy 右腳 −0.011）。HitHeavy 披風地板提高到 0.36。
- 遊戲內重測：載入正常，0 pageerror、0 console error。

## 第 2 輪後小修（lead 交辦，不需再審）
- 毛邊線頭：根部往布邊內縮 4 mm 接上布邊，長度縮短（罩袍 0.6–1.6 cm、披風 0.8–2.2 cm），改用不積垢、不壓 AO 的布本色材質（`linenFray`／`woolFray`），近看不再是懸空黑點。
- 靴子：加大體積（靴身高、寬加大），加 2.2 cm 方鞋跟與略翹的鞋頭硬殼；腳長 0.161H（+7.4%）、腳寬 0.070H（+7.2%），維持 ±10% 內。
- 鋼甲壓暗：#868884→#7a7c78、#7c7e7a→#71736f、脛甲 #777974→#6d6f6a。
- 結果：41,963 面、3.72 MB，check OK；逐格穿地 17/17 通過；遊戲內 0 pageerror／0 console error。
