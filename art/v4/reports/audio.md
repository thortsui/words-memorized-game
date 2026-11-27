# 音效報告（audio）— 2026-11-28

## 做了什麼
- 下載 7 個 **CC0** 音效包到 `art/v4/audio/raw/`（只用 ffmpeg 讀，沒執行任何下載物），沒有用到 CC-BY 素材。
- `art/v4/audio/tools/build_sfx.py`：疊層、變調（asetrate）、去開頭靜音、加殘響（aecho）、剪短淡出、峰值正規化到 -1 dB、轉 mono 44.1k mp3（短檔 80kbps、≥1.5 秒 64kbps）→ `public/sfx/`。
  **53 個檔、總共約 483 KB**（上限 2 MB）。另附 `public/sfx/CREDITS.md`。
- 改寫 `src/core/audio.js`：取樣用 AudioBuffer 播放（預載、快取、`v` 音量、`rate` 音高、每次隨機 ±5% 音高、同組多檔隨機挑且不連續重複、30 毫秒內同組不重疊、最多 28 聲同時）。
  取樣沒載好／載入失敗時退回舊的合成音。舊名字全部保留。檔頭有完整名字清單。
- 魂系配樂（theme `soul`）：保留原本旋律／低音，加了弦樂墊（微走音鋸齒波＋低通）、低鼓脈動（每 2 秒一下強弱）、偶爾的遠鐘（每 16 秒有 75% 機率，用 bell.mp3，沒有就合成）、每 32 秒一次很輕的低吟（共振峰合成）。
  音量 `VOL.bgmSoul=.015`，各聲部比例 `VOL.soulMel/soulBass/soulPad/soulDrum/soulBell/soulChoir`。打怪（bright）主題沒動（仍用 `VOL.bgm`）。
- `scripts/artifact-page.mjs`：建置後把 `dist-claude/sfx/*.mp3` 另外轉成 `*.mp3.b64.txt`（mp3 保留）。audio.js 先抓 mp3，失敗再抓 b64；第一個檔判斷出哪種可用後其餘直接走那條，不會每個檔都先失敗一次。
  路徑用 `import.meta.env.BASE_URL + "sfx/"`（vite base 是 `./`，跟模型同一套），GitHub Pages 子路徑可以載。

## 驗證
- ffprobe／ffmpeg 全部 53 檔可解碼、mono、44.1k，沒有錯誤。
- `npx vite --port 5191` + Playwright：
  - 40 個名字 × 4 種參數（`{}`、`{v,low}`、`{boss:'priest'}`、`{boss:'devourer',rate:.9}`）在「還沒載入（走合成）」和「載入後（走取樣）」都呼叫過，沒有丟例外；console 0 錯誤 0 警告。
  - 預載 53 檔約 0.18 秒（本機）。所有取樣組 `sfxReady` 都是 true。
  - b64 退路：把 .mp3 全部模擬成 404，只試了 1 次 mp3 就改走 b64，53 檔都解碼成功。
  - 實測輸出音量（在 destination 前掛分析器）：打怪配樂 RMS ≈ 0.0031；魂系配樂原本 .022 時 RMS ≈ 0.0055，已降到 .015（換算 ≈ 0.0037，跟打怪同級、峰值 ≈ 0.02）。音效 clash 峰值 ≈ 0.43、devourer 咆哮峰值 ≈ 0.54。
- 我沒辦法真的用耳朵聽，素材是照檔名、頻譜重心、低頻比例、包絡挑的；**請 lead 或使用者實際聽一輪**，不對的直接改 `build_sfx.py` 的配方重跑。

## sfx 名字與建議掛法
| 名字 | 用途 | 建議掛在 |
|---|---|---|
| shot（→tick） | 介面小提示 | 照舊（gain/atb/chainStart/dodge） |
| hit（flesh＋輕 clash） | 一般砍中 | 照舊 `e.type==="hit"` 命中瞬間 |
| crit（clashBig＋flesh） | 重擊 | 照舊 |
| hurt | 主角受擊 | 照舊 playerHit 命中瞬間 |
| parry | 彈反「鏘」 | 照舊；完美彈反可再疊 `clashBig` |
| faint | 敵人失衡 | 照舊 |
| win（→gradePerfect 鈴） | 勝利／回血 | 照舊；喝藥建議改 `drink` |
| lose（遠鐘＋悶響） | 敗北 | 照舊 |
| step（→stomp） | Boss 踏步 | 照舊 |
| swoosh（→swingL／low:swingH） | 揮擊破風 | 照舊 |
| heavy（→slam） | 重擊落地 | 照舊 |
| roar | 咆哮 | 改成 `sfx("roar",{boss:b.data.id})`，或進戰鬥時呼叫一次 `setSfxBoss(id)`，舊呼叫不用改 |
| clash | 劍砍甲 | 主角砍中有甲的 Boss（sentinel、executioner）命中瞬間 |
| clashBig | 兵器相交、重金屬 | Boss 重擊被格擋、完美彈反、弱點擊破 |
| swingL / swingH | 輕／重揮劍 | 主角每一下連段 onSwing 用 swingL（終結技、ChainP 大招用 swingH）；Boss 用 swingH |
| flesh / stone | 砍中肉／石 | 依 Boss 材質：gargoyle、sentinel 的石部位用 stone；executioner、devourer 用 flesh |
| block | 格擋盾響 | 主角擋下 Boss 攻擊 |
| roll | 翻滾 | 主角閃避／翻滾動畫起手 |
| footstep | 主角腳步 | 主角移動／連段踏步（建議 v .4–.6） |
| stomp | Boss 重踏 | Boss 腳落地（取代 step） |
| slam | 重砸地、爆裂 | Boss 砸地、跳砸、衝擊波 |
| roar_sentinel / gargoyle / priest / executioner / devourer | 五隻 Boss 咆哮 | 開場、danger 招式預兆、階段轉換 |
| bossDie | Boss 死亡 | 擊殺演出（目前 soulScene 649 行用 heavy） |
| phase | 階段轉換轟鳴 | phaseShow 爆發瞬間（目前 roar+heavy，可改 phase＋roar_<id>） |
| drink | 喝藥 | `e.type==="drink"` 的 onImpact（目前用 win） |
| gradePerfect / gradeNormal / gradeWrong | 判定音 | 每題作答判定出來那一刻 |
| charge | 連段蓄勢 | ChainReady 開始／chainCharge |
| finisher | 終結重擊 | 連段最後一下命中瞬間（可再疊 slam） |
| ice / dark | 冰／暗屬性 | priest 的冰招命中；executioner、devourer 的暗招 |
| bell | 遠鐘 | 配樂用；也可當進魂系戰鬥／存檔點的儀式音 |

其他：`sfxPreload()` 建議在進魂系戰鬥（bgmStart('soul') 會自動觸發）或選 Boss 畫面時呼叫，第一刀就有取樣。

## 每個音檔
所有素材包授權都是 **CC0 1.0**（https://creativecommons.org/publicdomain/zero/1.0/）。

| �ɮ� | ���� | �j�p | �ӷ������]�ɦW@�ܳt���v�^ | �����]���@�� |
|---|---|---|---|---|
| clash1.mp3 | 0.55s | 6.2KB | sword_clash.2.ogg | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas |
| clash2.mp3 | 0.55s | 6.2KB | sword_clash.4.ogg + impactPlate_medium_003.ogg@0.9 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| clash3.mp3 | 0.50s | 5.7KB | sword_clash.8.ogg@0.94 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas |
| clash4.mp3 | 0.55s | 6.2KB | sword_clash.7.ogg@1.05 + impactMetal_heavy_000.ogg | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| clashBig1.mp3 | 1.10s | 11.5KB | sword_clash.1.ogg@0.85 + impactPlate_heavy_001.ogg@0.8 + metal-ringing.wav@0.7 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| clashBig2.mp3 | 1.10s | 11.5KB | sword_clash.3.ogg@0.8 + impactMetal_heavy_001.ogg@0.75 + metal_08.ogg@0.8 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| parry1.mp3 | 0.80s | 8.5KB | sword_clash.5.ogg@1.08 + bell_02.ogg@1.2 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas |
| parry2.mp3 | 0.80s | 8.5KB | sword_clash.10.ogg@1.12 + metal-ringing.wav@1.15 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| swingL1.mp3 | 0.30s | 3.7KB | swing.wav | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| swingL2.mp3 | 0.25s | 3.2KB | swing2.wav@0.95 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| swingL3.mp3 | 0.25s | 3.2KB | swing3.wav@1.05 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| swingL4.mp3 | 0.35s | 4.1KB | sword.6.ogg@0.9 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas |
| swingL5.mp3 | 0.40s | 4.6KB | sword.4.ogg@0.85 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas |
| swingH1.mp3 | 0.50s | 5.7KB | swing.wav@0.62 + swing3.wav@0.7 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| swingH2.mp3 | 0.55s | 6.2KB | swing2.wav@0.55 + sword.5.ogg@0.8 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| swingH3.mp3 | 0.60s | 6.4KB | sword.3.ogg@0.62 + swing.wav@0.6 | [20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| flesh1.mp3 | 0.45s | 5.1KB | impactPunch_heavy_000.ogg + chop.ogg@0.9 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| flesh2.mp3 | 0.45s | 5.1KB | impactPunch_heavy_002.ogg@0.95 + knifeSlice.ogg@1.1 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| flesh3.mp3 | 0.45s | 5.1KB | impactPunch_heavy_004.ogg@0.9 + chop.ogg@0.8 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| stone1.mp3 | 0.70s | 7.4KB | bfh1_rock_breaking_02.ogg + impactMining_000.ogg@0.9 | [75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| stone2.mp3 | 0.70s | 7.4KB | bfh1_rock_breaking_03.ogg@0.9 + impactMining_004.ogg@0.85 | [75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| block1.mp3 | 0.60s | 6.4KB | impactPlate_heavy_001.ogg@0.85 + impactWood_heavy_000.ogg@0.8 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| block2.mp3 | 0.60s | 6.4KB | impactPlate_heavy_003.ogg@0.8 + impactWood_heavy_002.ogg@0.75 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| roll1.mp3 | 0.60s | 6.5KB | cloth-heavy.wav@0.9 + chainmail1.wav + impactSoft_heavy_001.ogg@0.8 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| roll2.mp3 | 0.60s | 6.4KB | cloth1.ogg@0.9 + chainmail2.wav + impactSoft_heavy_003.ogg@0.8 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| footstep1.mp3 | 0.25s | 3.1KB | footstep00.ogg | [Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| footstep2.mp3 | 0.25s | 3.1KB | footstep01.ogg | [Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| footstep3.mp3 | 0.25s | 3.1KB | footstep03.ogg | [Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| footstep4.mp3 | 0.25s | 3.1KB | footstep06.ogg | [Kenney RPG Audio](https://kenney.nl/assets/rpg-audio) / Kenney |
| stomp1.mp3 | 0.89s | 9.5KB | impactSoft_heavy_000.ogg@0.55 + slam_03.ogg@0.6 + bfh1_rock_falling_04.ogg@0.8 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| stomp2.mp3 | 0.89s | 9.5KB | impactSoft_heavy_002.ogg@0.5 + metal_10.ogg@0.6 + bfh1_rock_falling_07.ogg@0.8 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| slam1.mp3 | 1.60s | 13.1KB | explosion.ogg@0.6 + bfh1_rock_breaking_01.ogg@0.8 + impactSoft_heavy_004.ogg@0.5 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| slam2.mp3 | 1.50s | 12.3KB | slam_02.ogg@0.55 + bfh1_rock_breaking_02.ogg@0.75 + impactMining_002.ogg@0.6 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| roar_sentinel.mp3 | 2.00s | 16.2KB | giant2.wav@0.72 + giant5.wav@0.66 + bfh1_metal_falling_01.ogg@0.55 | [75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| roar_gargoyle.mp3 | 1.70s | 13.9KB | scream_01.ogg@0.86 + monster_02.ogg@0.8 + bfh1_rock_falling_01.ogg@0.7 | [75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) / rubberduck |
| roar_priest.mp3 | 2.60s | 20.9KB | shade8.wav@0.78 + shade9.wav@0.66 + shade12.wav@0.9 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| roar_executioner.mp3 | 1.80s | 14.6KB | mnstr14.wav@0.72 + mnstr5.wav@0.62 + troll_01.ogg@0.7 | [80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) / rubberduck�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| roar_devourer.mp3 | 2.60s | 20.9KB | monster_04.ogg@0.8 + roar_02.ogg@0.62 + monster_07.ogg@0.7 + scream_02.ogg@0.6 + giant2.wav@0.55 | [80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) / rubberduck�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| roar1.mp3 | 1.50s | 12.3KB | roar_02.ogg@0.8 + giant5.wav@0.75 | [80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) / rubberduck�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| bossDie.mp3 | 3.00s | 23.9KB | monster_07.ogg@0.6 + giant4.wav@0.5 + bfh1_rock_falling_04.ogg@0.7 + bfh1_metal_falling_02.ogg@0.7 | [75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) / rubberduck�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| phase.mp3 | 3.00s | 23.9KB | gong_02.ogg@0.62 + monster_04.ogg@0.6 + explosion.ogg@0.5 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) / rubberduck |
| drink.mp3 | 1.00s | 10.5KB | bottle.wav + bubble.wav@0.85 + bubble2.wav@0.8 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| gradePerfect.mp3 | 1.20s | 12.3KB | bell_01.ogg + impactBell_heavy_004.ogg@1.5 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| gradeNormal.mp3 | 0.25s | 3.1KB | impactMetal_light_002.ogg@1.1 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| gradeWrong.mp3 | 0.50s | 5.4KB | impactSoft_heavy_000.ogg@0.7 + metal_10.ogg@0.55 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| charge.mp3 | 1.00s | 10.5KB | sword-unsheathe3.wav@0.9 + magic1.wav@0.6 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| finisher.mp3 | 2.00s | 16.2KB | sword_clash.1.ogg@0.78 + explosion.ogg@0.55 + impactPunch_heavy_001.ogg@0.7 + metal-ringing.wav@0.6 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck�F[20 Sword SFX](https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes) / StarNinjas�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| ice.mp3 | 1.00s | 10.5KB | bfh1_glass_breaking_02.ogg@0.8 + impactGlass_heavy_001.ogg@0.7 | [75 CC0 breaking/falling/hit](https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx) / rubberduck�F[Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| dark.mp3 | 2.00s | 16.2KB | spell.wav@0.6 + shade6.wav@0.6 | [RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| hurt1.mp3 | 0.50s | 5.7KB | impactPunch_medium_000.ogg@0.9 + chainmail1.wav | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| hurt2.mp3 | 0.50s | 5.7KB | impactPunch_medium_003.ogg@0.85 + armor-light.wav | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney�F[RPG Sound Pack](https://opengameart.org/content/rpg-sound-pack) / artisticdude |
| tick.mp3 | 0.20s | 2.6KB | impactMetal_light_004.ogg@1.25 | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) / Kenney |
| bell.mp3 | 3.00s | 23.9KB | bell_03.ogg@0.5 + gong_01.ogg@0.5 | [100 CC0 SFX](https://opengameart.org/content/100-cc0-sfx) / rubberduck |

## 怎麼重跑
```
python -P art/v4/audio/tools/build_sfx.py            # 全部
python -P art/v4/audio/tools/build_sfx.py roar_priest  # 只重做某幾個
python -P art/v4/audio/tools/analyze.py public/sfx/*.mp3   # 看長度／頻譜重心
```
素材要重新下載的話：Kenney 兩包從頁面「Continue without donating」拿簽名連結；OpenGameArt 四包直接下載 zip（網址見上表），解到 `art/v4/audio/raw/<資料夾>/`（資料夾名稱：impact-sounds、rpg-audio、rpgpack、sword、creature、oga100、breaking）。

## 已知問題／待 lead 處理
- `.gitignore` 不在我的所有權內：請 lead 加上 `art/v4/audio/raw/` 和 `art/v4/audio/tmp/`（下載原檔約 20 MB、中間 wav）。要進 git 的只有 `public/sfx/**`、`art/v4/audio/tools/**`、這份報告。
- 沒有實際聽過（見上面驗證），尤其五隻 Boss 咆哮的區別、魂系配樂新聲部的比例，需要人耳確認。
- 遊戲事件還沒接新名字（soul.js／soulScene.js／controller.js 是 lead 的），建議掛法見上表。
- mp3 開頭有編碼器延遲約 26 毫秒，Chrome 會依 LAME 標頭去掉；其他瀏覽器最多晚 26 毫秒，可以忽略。
