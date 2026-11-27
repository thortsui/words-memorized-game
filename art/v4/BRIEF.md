# v1.3.0 團隊合約：連續連斬、Boss 每階段新招、真實音效（2026-11-28）

使用者要求（原話整理）：
1. 魂系要更好的音效：金屬碰撞、怪物吼叫等都要有；加一首簡單的背景音樂，小聲，但不要死氣沉沉。
2. 動畫長度不夠。連續答題不是「每題看一刀」，而是一整段連續動畫（參考動作遊戲輕攻擊連段：連按普攻，每一下動作都不同，串成一段完整流暢的動畫）。
3. 連段有很多版本：依每題判定組合不同（全完美一個版本、完美完美普通又是另一個版本……）。
   判定：答錯＝錯誤；答對但花很久＝普通；答對且剩餘時間 ≥ 60%＝完美。
4. 主角動畫總共要超過 25 種。
5. 每隻 Boss 攻擊方式至少 5 種，每個型態（階段）至少 2–3 種。
6. 可以用 Gemini（使用者 Windows Chrome 已登入，Browser 2）。只取設計原則，不可複製任何現有遊戲的角色、招式名、美術。

## 檔案所有權（只改自己的檔案；不准 npm run build；不准 git commit/push）
| 角色 | 可改 |
|---|---|
| hero 動畫 | art/blender/v3_hero_actions.py、v3_hero_rig.py／v3_hero_bake.py（只限 meta 欄位與片段相關）、public/models/hero_knight.glb、art/blender/export_raw/hero_knight.* |
| boss 動畫（每隻一人） | 該 Boss 的 *_actions.py／動作相關腳本、public/models/boss_<id>.glb、export_raw/boss_<id>.* |
| 音效 | src/core/audio.js、public/sfx/**、scripts/artifact-page.mjs（只加音檔 base64）、art/v4/audio/** |
| lead（主 session） | 其他全部：soul.js、data.js、soulScene.js、moves.js、controller.js、clipmeta.json、check_soul_glb.py |
- `merge_clipmeta.py` 可以跑（lead 最後會再跑一次）；`check_soul_glb.py` 的必備名單 lead 已更新，不要改。
- 既有片段名稱、時長、命中時間、骨頭名稱一律不動（遊戲在用）。只新增片段。
- C: 槽很滿：暫存（渲染、log、下載）一律放 D:（art/v4/tmp/<你的代號>/，不進 git）。
- 報告寫 art/v4/reports/<代號>.md：做了什麼、每個片段時長／命中時間／cancel、怎麼重跑、已知問題。

## 片段 meta 擴充
clipmeta 每個片段可多一個欄位 `"cancel": 秒`＝可以接下一招的時間（跟隨動作已完成、可交叉淡入下一段）。
連段片段與 Boss 新招都要給 cancel。命中時間 `hits` 照舊（由劍尖／攻擊部位速度峰值量測）。

## 主角新片段（25 個，總數 42）——全部原地播放（Root 不動，位移由遊戲做）
連段設計：每一下起手姿勢要能從上一下的結束姿勢自然接上（遊戲用 0.08–0.12 秒交叉淡入，在 cancel 時間切到下一段）。
第 i 下依該題判定選 P（完美，華麗、更大幅、更快爆發）或 N（普通，紮實但樸素）。最後一下用終結技。
| 名稱 | 說明 | 時長參考 | hits |
|---|---|---|---|
| ChainReady | 連段蓄勢（迴圈）：劍架在身側、重心低、等下一題時呼吸 | 2.0 loop | – |
| ChainP1 | 完美第 1 下：踏步斜劈（右上→左下）大幅 | 0.9–1.1 | 1 |
| ChainP2 | 完美第 2 下：轉身迴旋反手橫斬 | 0.9–1.1 | 1 |
| ChainP3 | 完美第 3 下：上挑斬（挑空、身體跟著起） | 0.9–1.1 | 1 |
| ChainP4 | 完美第 4 下：空中交叉雙斬（兩個命中） | 1.0–1.2 | 2 |
| ChainN1 | 普通第 1 下：直劈 | 0.8–1.0 | 1 |
| ChainN2 | 普通第 2 下：反手斬 | 0.8–1.0 | 1 |
| ChainN3 | 普通第 3 下：突刺 | 0.8–1.0 | 1 |
| ChainN4 | 普通第 4 下：水平掃斬 | 0.8–1.0 | 1 |
| FinishAll | 全部完美的終結：躍起旋身、雙手持劍下劈重擊（兩段：旋斬＋落地重劈） | 2.2–2.8 | 2 |
| FinishP | 最後一下完美：雙旋重斬 | 1.6–2.0 | 2 |
| FinishN | 最後一下普通：舉劍重劈 | 1.4–1.8 | 1 |
| ChainBreak | 答錯：被彈開、踉蹌後退、重新架劍 | 1.2–1.5 | – |
| ChainRecover | 連段結束收劍回戒備 | 0.8–1.0 | – |
| AssaultA / AssaultB | 突擊：快速兩連斬（兩套不同） | 0.9–1.1 | 2 |
| AssaultEnd | 突擊終結：衝刺突刺貫穿 | 1.3–1.6 | 1 |
| Execution | 弱點擊破處決：踏前刺入→拔劍迴斬 | 2.4–3.0 | 2 |
| Riposte | 彈反後完整反擊：彈開→踏入橫斬 | 1.1–1.3 | 1 |
| Deflect | 連擊中段彈刀：小幅格開 | 0.6–0.8 | 1 |
| SideL / SideR | 左右側閃（短步，比 Roll 快） | 0.6–0.8 | – |
| Drink | 喝藥壺：左手舉壺仰頭 | 1.4–1.8 | 1（喝下那格） |
| GetUp | 倒地後起身 | 1.2–1.6 | – |
| BattleCry | 回合開始架劍振臂 | 1.4–1.8 | – |

## Boss 新片段（每隻 5 個；魔王另加 2 個）
既有：Attack、Attack2、Combo3（3 hits）、Delayed、Dash。新增：
| 名稱 | 用途 | hits |
|---|---|---|
| Sweep | 一階起：大範圍橫掃（與 Attack／Attack2 明顯不同） | 1 |
| Smash | 二階：重砸地面／重擊，落地有衝擊 | 1 |
| Leap | 二階：躍起撲擊（突進類，拉近距離） | 1 |
| ComboB | 二階：與 Combo3 不同節奏的三連擊（例：快快慢、或慢快快） | 3 |
| Special | 二階必殺（對應 data.js 的階段招式名），最有壓迫感、預備最長 | 1–2 |
| ComboC（僅魔王） | 三階四連擊 | 4 |
| Special3（僅魔王） | 三階終極必殺 | 1–2 |
每招都要有清楚的預備（telegraph 姿勢 0.4–1.0 秒）→ 爆發 → 跟隨 → 回勢，起訖回到該 Boss 的戒備姿勢（Idle/IdleAggro 能淡入）。
招式名稱對照（lead 會寫進 data.js）：
- sentinel（鏽蝕守門者）：Sweep 鏽戟橫掃、Smash 門板震地、Leap 躍起戟擊、ComboB 根鬚三連、Special 根鬚纏擊
- gargoyle（石像鬼）：Sweep 石翼橫掃、Smash 俯衝砸地、Leap 飛撲、ComboB 撕咬連擊、Special 碎石吐息
- priest（冰霜祭司）：Sweep 寒杖橫掃、Smash 冰柱砸落、Leap 冰面滑步斬、ComboB 霜咒三連、Special 冰棺降臨
- executioner（影處刑者）：Sweep 斷頭橫掃、Smash 斷罪劈地、Leap 躍斬、ComboB 處刑亂舞、Special 影分身處刑
- devourer（噬語魔王）：Sweep 墨刃橫掃、Smash 魔劍震地、Leap 虛空躍擊、ComboB 吞字三連、Special 詞語風暴、ComboC 終焉四連、Special3 終焉之言

## 音效
遊戲現在全部 Web Audio 合成，聽起來像電子音。要換成（或疊上）真實取樣：金屬碰撞、劍揮破風、砍中肉／甲、格擋、翻滾布料、腳步、重砸地、各 Boss 咆哮（五隻要聽得出不同）、Boss 死亡、階段轉換、喝藥、判定音（完美／普通／錯誤）。
只能用可商用且可再散布的授權（CC0 最好；CC-BY 要在 public/sfx/CREDITS.md 標示）。音檔放 public/sfx/，單檔小（mono、44.1k 或 22k、mp3），總量 ≤ 2 MB。
`sfx(name, opts)` 介面保留；舊名字照樣能用；取樣載入失敗要退回合成音。
背景音樂（魂系）：簡單、小聲（現在 VOL.bgm=.02），但要有生命（緩慢的鼓或脈動、弦樂墊、偶爾的鐘）不要死寂。
Artifact 版（scripts/artifact-page.mjs 產生 dist-claude）載不到 .mp3 時要有退路（base64 文字檔，比照模型的 .b64.txt 做法）。
