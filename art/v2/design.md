# 單字魂 v2 設計規格（Design）

> 給：美術、建模 A/B、特效、畫面、感覺、動畫。遵守 `art/v2/TEAM_BRIEF.md`。
> 本文件定規格與數值目標；實作細節由各負責人決定，但**數值與時間點要對得上**。有衝突以本文件為準，並在自己的報告中註明。

---

## 0. 整體美術方向

**「墨與鏽」——黑暗寫實奇幻 × 東方水墨 × 金箔點綴。**
世界是「詞語之火熄滅後」的王國：所有東西都在剝落、生鏽、被遺忘。Boss 是寫實比例、重量感十足的實體（鏽鐵、碎石、冰、皮革、紙），
但**能量與魔法一律用水墨語彙表現**：墨霧、墨滴飛濺、筆觸狀的刀光、宣紙碎片、印章紋、金箔裂紋。
「答對＝詞語回來」：玩家的力量是**金色**（金箔、燙金筆觸、金色字粒子）；Boss 的力量是**墨＋該 Boss 主色**。整個畫面就是金與墨的拉鋸。

識別三規則：
1. **剪影優先**：每隻 Boss 在全黑剪影下一眼可辨（見各 Boss 輪廓關鍵字）。
2. **三層色**：底色（低彩度、暗、寫實材質）70%／主色（Boss 識別色，只出現在 `Glow` 與特效）20%／金與墨（點綴、裂紋、文字）10%。
3. **字是武器也是傷口**：Boss 身上的發光處盡量做成「刻痕、符紋、筆畫」形狀，而非單純亮塊（原創符紋，不用可讀真實文字、不用既有遊戲符號）。

禁止：複製任何既有遊戲的角色造型、名稱、武器、招式動作、UI；卡通比例；高彩度霓虹純色。

---

## 1. 共通規格（所有 Boss）

- 身高（遊戲內）：sentinel 3.1／gargoyle 3.0／priest 3.2／executioner 3.4／devourer 3.9。
- 部件命名：二階 `P2_*`、三階 `P3_*`，匯出預設隱藏；發光材質名含 `Glow`（例 `Glow_Eye`、`Glow_Rune`、`P2_Glow_Core`）。
- 每隻至少 3 種 `Glow`：眼（`Glow_Eye`）、身上符紋（`Glow_Rune`）、武器（`Glow_Weapon`）。一階 emissive 弱（程式 glow 0–0.5），二階起由程式拉到 0.7–1.6。
- 武器刃口方向明確，方便刀光與 hit 對齊；可行的話在武器尖端放空物件 `Tip_Weapon`。
- PhaseShift 片段 2.0–2.6 秒，三拍：**蓄力（0–約 45%）→ 爆發（hit，約 45–55%）→ 新姿態（剩下，結尾等於 IdleAggro 起始姿勢）**。
- 二階造型原則：**不換模型，是「長出／破出／點燃」**——部件從身體長出、外殼裂開露出內核、武器變形。動畫只需在爆發那一格遮掩一次。

---

## 2. Boss 規格

### 2.1 腐朽守門騎士 sentinel（綠）
- **定位**：被樹根吞沒仍站崗的門衛。第一隻，教玩家「看蓄力、閃避」。慢、重、可預測。
- **輪廓關鍵字**：寬簷鐵盔＋背上直立的巨大門板盾＋單手長戟斜指地面＋破爛長擺。剪影像「一扇會走的門」。
- **材質與配色**：鏽鐵（橙褐 #6b3a22）、黑綠青苔 #2f4a2a、濕木門板、麻布。主色 **苔綠 #7dffb0**。金：盔簷一圈褪色金邊。
- **一階**：盔下黑暗中只有兩點綠眼（`Glow_Eye`）；樹根細細纏在手腳；門板盾背在背後（保留現有特色，但重做得更厚重：門鉸、鐵釘、裂縫透微光 `Glow_Rune`）。
- **二階「根鬚暴走」**：
  - `P2_RootArms`：背後門板裂開，6–8 條粗樹根像觸手從裂縫伸出、向上張開（剪影從「門」變成「開花的樹」）。
  - `P2_RootSpikes`：肩甲、膝甲被樹根頂破長出尖刺。
  - `P2_Glow_Heart`：胸甲裂口露出綠光「樹心」。
  - 長戟刃纏滿根，戟尖 `Glow_Weapon` 點亮。
- **招牌特效**：根鬚沿攻擊線一排破土竄出、苔綠孢子飄散、木屑＋鏽屑。
- **PhaseShift 分鏡（2.4 s，爆發 hit 1.1 s）**：
  - 0.0–0.5 長戟插地、單膝跪下、頭垂下（像要倒下）。
  - 0.5–1.0 背後門板震動、縫隙透綠光，身體被「吊」起（樹根把他拉起來）。
  - **1.1 爆發**：門板炸開，樹根向四方甩開，戟從地上拔起高舉。
  - 1.1–2.4 樹根在背後收攏成扇形，戟橫放胸前，重心壓低進 IdleAggro。
- **Gemini 提示詞**：
  - P1：`Original dark fantasy boss concept art, "Rotting Gate Sentinel": a towering rusted knight in a wide-brimmed iron helm with only two faint green eyes in the darkness beneath, a massive wooden castle-gate door strapped vertically on his back as a shield, a single long halberd angled toward the ground, thin tree roots and black-green moss creeping over corroded plate armor, tattered long tabard. Realistic weathered materials, subtle faded gold trim on the helm, faint ink-wash mist at the feet. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, consistent soft lighting, original design, not based on any existing game.`
  - P2：`Same character, second form "Root Frenzy": the gate-door on his back has split open and 6-8 thick living tree roots burst out like tentacles fanning upward, roots piercing through pauldrons and knee plates as spikes, a glowing jade-green heart visible through a cracked breastplate, halberd blade wrapped in roots with a glowing green tip, green spores and ink-wash smoke drifting. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`

### 2.2 教堂石像鬼 gargoyle（橘）
- **定位**：教堂屋頂的石像活了過來。快、跳躍、從上方來。教玩家「節奏變化、連擊」。
- **輪廓關鍵字**：四肢著地的蹲伏＋巨大石翼（展開寬度 ≥ 身高 1.5 倍）＋長尾＋頭上兩根彎角。剪影是「張開翅膀的駝背」。
- **材質與配色**：風化灰石 #5d5a57、苔斑、口部是鉛灰排水口、斷裂的鐵鏈。主色 **熔岩橘 #ff8a3a**（石頭內部在燒）。金：額頭殘留的金箔徽記（原創圖形）。
- **一階**：翅膀完整但有缺角；石縫內微弱橘光（`Glow_Rune` 沿石縫）；嘴是排水口造型。
- **二階「石翼狂嘯」**：
  - `P2_WingMolten`：石翼外層剝落，翼膜露出熔岩紋路（橘色發光裂網）。
  - `P2_Horns`：角變長、分岔。
  - `P2_Glow_Maw`：嘴撕裂到頰邊，內部熔光（配合「碎石吐息」）。
  - `P2_SpineShards`：背脊冒出一排碎石尖片。
- **招牌特效**：碎石雨＋石塵；俯衝時翼尖拖兩道橘色殘痕；碎石吐息＝錐形噴出的燒紅碎石＋煙。
- **PhaseShift 分鏡（2.2 s，爆發 hit 1.0 s）**：
  - 0.0–0.5 翅膀包住全身縮成一團（像變回雕像）。
  - 0.5–0.95 表面龜裂，裂縫橘光一閃一閃，輕微顫抖。
  - **1.0 爆發**：翅膀猛然展開、石殼碎片外噴，仰頭咆哮（嘴張到最大）。
  - 1.0–2.2 拍兩下翅膀半騰空，重重落地四肢著地，尾巴甩一圈。
- **Gemini 提示詞**：
  - P1：`Original dark fantasy boss concept art, "Cathedral Gargoyle": a hunched weathered-stone gargoyle crouching on all fours, enormous chipped stone wings half-spread, long segmented tail, two curved horns, a mouth shaped like an old cathedral drain spout, faint ember-orange light glowing inside the stone cracks, broken iron chains on the wrists, a worn gold-leaf emblem on the forehead (original symbol). Realistic stone and moss textures, ink-wash dust around. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`
  - P2：`Same gargoyle, second form "Stone-Wing Howl": the outer stone of the wings has shed away revealing molten orange lava veins across the wing membranes, horns grown longer and forked, jaw torn open to the cheeks with molten glow inside, a row of jagged stone shards erupting along the spine, embers and ink-black smoke streaming. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`

### 2.3 霜冠祭司 priest（冰藍）
- **定位**：在冰封禮拜堂為死者唸禱的祭司。施法型、中距離長槍突刺、會「封住」空間。
- **輪廓關鍵字**：高瘦＋拖地長袍（下擺像冰柱垂落）＋頭頂高聳放射狀冰晶冠＋一手長槍、腰間一本經書。剪影是「細長三角形加一頂王冠」。
- **材質與配色**：白灰麻袍、結霜皮革、半透明冰（要有折射感，不要過亮）、銀器。主色 **霜藍 #8fe3ff**。金：經書金扣、袍邊燙金原創符紋。面部蒼白、雙眼被薄冰覆蓋。
- **一階**：冰冠小（3–5 根尖晶）；經書闔著掛腰間；銀柄冰尖長槍。
- **二階「永凍禱詞」**：
  - `P2_CrownHalo`：冰冠擴成頭後一圈冰晶光環（直徑約 1.6 m），緩慢旋轉。
  - `P2_FloatingBook`：經書翻開懸浮在左手上方，書頁發藍光（`Glow`）。
  - `P2_IceShards`：袍擺外一圈貼地冰刺。
  - `P2_Glow_Veins`：臉頰與手出現冰藍血管紋。
- **招牌特效**：霜霧貼地流動、冰晶碎片、地面結霜擴散圈；冰棺降臨＝四根冰柱從天而降框住主角，0.6 s 後碎裂。
- **PhaseShift 分鏡（2.5 s，爆發 hit 1.2 s）**：
  - 0.0–0.6 槍立身側、雙手合十，頭微仰禱念。
  - 0.6–1.1 緩緩升空 0.3 m，袍擺結冰下垂、冰冠逐根變長。
  - **1.2 爆發**：雙手向兩側張開，冰冠擴成光環，地面冰刺一圈炸出。
  - 1.2–2.5 經書從腰間飛起翻開到左手，緩降落地，槍尖指向玩家。
- **Gemini 提示詞**：
  - P1：`Original dark fantasy boss concept art, "Frost-Crown Priest": a tall gaunt priest in long frost-covered grey-white robes whose hem hangs like icicles, a tall crown of radiating ice crystals, eyes sealed under thin ice, pale face, holding a slender silver spear with an ice spearhead, a closed prayer book with gold clasps hanging at the waist, gold-stitched original glyphs along the robe edge. Realistic cloth, frost and translucent ice, soft ink-wash frost mist on the floor. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`
  - P2：`Same priest, second form "Eternal-Frost Litany": the ice crown has expanded into a large rotating halo of ice shards behind the head, the prayer book floats open above the left hand with glowing blue pages, a ring of ice spikes erupts around the robe hem, glowing ice-blue veins on cheeks and hands, hovering slightly above the ground, swirling frost and ink mist. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`

### 2.4 暗影行刑者 executioner（紫）
- **定位**：處刑場的劊子手，身體由無數被處刑者的影子拼成。最快、連擊多、會分身。
- **輪廓關鍵字**：魁梧倒三角上身＋尖頂麻布頭罩（只露一條眼縫）＋雙手巨斧（斧面比頭大）＋腰間吊一排鐵鍊與鎖頭。剪影是「巨斧＋尖頭罩」。
- **材質與配色**：黑皮革、黑鐵、粗麻頭罩、乾涸暗褐污漬（不要鮮紅）。主色 **影紫 #b07aff**。金：斧柄末端金色封印環、眼縫內一道細金線。手肘以下、腳踝是半透明墨影，邊緣像墨在水中暈開。
- **一階**：以實體為主，只有前臂與腳踝墨影化；斧刃有紫色紋（`Glow_Weapon`）。
- **二階「處刑之舞」**：
  - `P2_ShadowArms`：背後多一對半透明墨影手臂，握著影子斧（紫 `Glow`）。
  - `P2_HoodTorn`：頭罩撕開一半，底下是紫光漩渦（沒有臉）。
  - `P2_ChainHalo`：腰間鎖鍊浮起，繞身體一圈慢轉。
  - `P2_AxeBlade2`：斧刃變形為雙刃。
- **招牌特效**：墨影殘像（每次移動留 2–3 個紫色半透明殘影）、地面紫色斬痕、影分身處刑＝左右各一個墨影分身同步揮斧後散成墨滴。
- **PhaseShift 分鏡（2.3 s，爆發 hit 1.0 s）**：
  - 0.0–0.5 斧頭拖地轉身一圈（處刑前的儀式），身體前傾。
  - 0.5–0.95 雙手舉斧過頭，頭罩被內部紫光撐裂，身後墨影翻湧。
  - **1.0 爆發**：斧砍進地面，頭罩撕開，背後墨影手臂一口氣伸出。
  - 1.0–2.3 拔斧，四臂擺出交叉架勢，鎖鍊浮起繞身。
- **Gemini 提示詞**：
  - P1：`Original dark fantasy boss concept art, "Shadow Executioner": a massive broad-shouldered executioner wearing a pointed burlap hood with a single narrow eye slit, black leather and black iron armor, wielding a huge two-handed axe with a blade bigger than his head, rows of chains and padlocks hanging from the belt, forearms and ankles dissolving into translucent ink-like shadow that bleeds like ink in water, faint violet runes on the axe, a gold seal ring at the axe pommel. Realistic leather and iron, dried dark stains. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`
  - P2：`Same executioner, second form "Dance of Execution": the hood is torn half open revealing a swirling violet void instead of a face, a second pair of translucent ink-shadow arms grows from his back holding a shadow axe, the chains float and orbit around his body, the axe has become double-bladed with violet glowing edges, violet afterimages and ink droplets around him. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`

### 2.5 噬語魔王 devourer（紅，最終 Boss，三階）
- **定位**：吞掉王國所有詞語的魔王，身上掛滿被吃掉的書頁。三個型態逐步「把吃下的字吐出來當武器」。
- **輪廓關鍵字**：左右不對稱的多重彎角＋骷髏面＋寬大肩甲＋鋸齒巨劍（拄地）＋書頁堆成的長披風。剪影是「角＋巨劍＋往下擴散的紙披風」。保留現有參考圖 boss5 的精神，但更巨大、層次更多。
- **材質與配色**：暗金浮雕甲（舊金 #8a6a2a，帶墨污）、骨、泛黃書頁、黑鐵鍊。主色 **噬紅 #ff3a2a**＋墨黑。金：本隻金最多，但到三階被墨吞掉一部分。
- **一階（王者）**：甲冑完整；左手掌心紅色符紋（`Glow_Rune`）；劍鋸齒內暗紅細線（`Glow_Weapon`）；書頁披風安靜下垂。
- **二階「吞噬詞語」**：
  - `P2_PageWings`：披風書頁飛起，在背後組成一對紙之翼（數十片書頁片，邊緣燃紅）。
  - `P2_ChestMaw`：胸甲中央裂成一張豎直的嘴（有牙），內部紅光＝正在吞字。
  - `P2_Glow_Script`：盔甲金紋轉紅發光，像字在血管裡流。
  - 劍身裂縫 `Glow_Weapon` 全亮。
- **三階「終焉咒言」**：
  - `P3_Crown`：一根角斷掉，頭頂浮起一圈破碎紅黑光環（像燒穿的印章）。
  - `P3_InkBody`：下半身與披風化為翻湧墨潮（腳不可見，懸浮約 0.2 m）；`P3_ArmorCracked` 取代約 30% 甲片（剝落、露出暗色裂肉）。
  - `P3_SwordWords`：巨劍刃外纏繞一圈圈漂浮的發光原創符字（紅＋金），劍長 +20%。
  - `P3_Glow_Eyes`：眼窩噴出紅焰。
- **招牌特效**：書頁旋風（詞語風暴）、墨潮貼地蔓延、金色字粒子從主角身上被吸向胸口的嘴、終焉之言＝全畫面墨色收縮＋一圈巨大紅色符字環從 Boss 擴出橫掃。
- **PhaseShift 分鏡**：
  - 二階（2.5 s，爆發 hit 1.15 s）：0.0–0.5 劍拄地、左手按胸；0.5–1.1 書頁從披風一張張剝離飄起、胸甲出現紅光裂痕；**1.15 爆發**：胸口嘴裂開，書頁瞬間組成紙翼；1.15–2.5 雙手握劍斜指地面，紙翼緩慢開合。
  - 三階（2.6 s，爆發 hit 1.25 s）：0.0–0.6 單膝跪、劍插地、全身痙攣；0.6–1.2 墨從甲縫噴出包住下半身，一根角斷裂飛出；**1.25 爆發**：仰天張開雙臂，紅黑光環在頭頂成形，墨潮向外推；1.25–2.6 懸浮起身、拔劍，劍上符字一圈圈點亮。
  - 若只能做一條 `PhaseShift`，以二階版本為準，三階差異由程式（特效＋`P3_*` 顯示＋鏡頭）補足；有餘力可加 `PhaseShift2` 片段（動畫負責判斷是否存在）。
- **Gemini 提示詞**：
  - P1：`Original dark fantasy final boss concept art, "Word-Devouring Demon King": a towering armored demon king with an asymmetric crown of multiple curved horns, skull-like face with dim red eyes, heavy dark-gold engraved plate armor stained with black ink, wide pauldrons, a long cape made of hundreds of torn yellowed book pages, chains at the waist, resting a huge jagged serrated greatsword on the ground, glowing red original glyphs on the left palm. Realistic metal, bone and paper materials, ink-wash smoke at the feet. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`
  - P2：`Same demon king, second form "Devouring Words": the page cape has lifted into a pair of wings made of floating book pages with burning red edges, the center of the breastplate split open into a vertical fanged maw glowing red inside, all gold engravings now glowing red like script flowing through veins, sword cracks glowing red, golden letter-like particles being sucked into the chest maw. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`
  - P3：`Same demon king, final form "Final Incantation": one horn broken off, a shattered red-black halo like a burnt seal floating above the head, lower body and cape dissolved into a churning black ink tide, hovering, about a third of the gold armor flaked away revealing dark cracked flesh, red flames pouring from the eye sockets, the greatsword longer and wrapped in rings of floating glowing red-and-gold original glyphs. Dramatic but readable silhouette. Full body, 3/4 view, neutral dark background, concept art turnaround-ready, original design, not based on any existing game.`

### 2.6 五隻並排比例圖提示詞
`Original dark fantasy boss lineup concept sheet, five bosses standing side by side on one ground line for scale comparison, left to right: Rotting Gate Sentinel (3.1 m rusted knight with a gate-door shield on his back and a halberd, green eyes), Cathedral Gargoyle (3.0 m crouching stone gargoyle with huge wings, ember-orange cracks), Frost-Crown Priest (3.2 m tall gaunt priest with an ice crown and spear, ice-blue), Shadow Executioner (3.4 m hooded executioner with a giant axe and ink-shadow limbs, violet), Word-Devouring Demon King (3.9 m horned dark-gold armored king with a book-page cape and serrated greatsword, red). A 1.8 m human knight silhouette at the far left for scale. Same realistic dark fantasy style with ink-wash and gold-leaf accents, each with a distinct silhouette and a single accent color, 3/4 view, neutral dark background, horizontal height lines, original designs, not based on any existing game.`

---

## 3. 階段轉換演出（給動畫：`bossPhase()`／`phaseShow.js`）

現況：`bossPhase()` 已有 banner、`phaseBurst`、仰拍、霧色漸變，但部件切換沒有遮掩、拍點未對齊爆發。
目標：**總長 ≤ 2.8 s**（含回到戰鬥）；期間玩家不可操作，但要感覺是「一段很爽的變身」而不是等待。

### 3.1 通用時間軸（T＝PhaseShift 爆發 hit，約 1.0–1.25 s；下表以 T＝1.1 為例）
| 時間 | 鏡頭 | 時間流速 | 模型 | 特效 | 字幕／UI | 聲音 |
|---|---|---|---|---|---|---|
| 0.00 | 0.35 s 從戰鬥機位移到「主角肩後仰拍」：低機位 y≈0.5、FOV 50→44、看 Boss 頭 | 1.0 | 播 PhaseShift（速度正規化到約 2.1–2.4 s） | 停威脅條；HUD 淡到 40% | — | 低頻嗡鳴起 |
| 0.00 → T−0.15 | 緩推（dolly in 0.6 m） | 1.0 | 蓄力 | 主色粒子由外向 Boss 吸入（≤ 60 顆）、地面主色符紋圈逐筆亮起、`glow` 0.5→1.0 | — | 嗡鳴漸強 |
| T−0.15 → T | 停推 | **0.35 慢放**（約 0.15 s 遊戲時間） | — | 暗角＋墨邊收縮到 0.6 | — | 靜音 80 ms |
| **T 爆發** | 震屏＋FOV 瞬間 +6 再回彈 | 1.0 | **同一格顯示 `P2_*`/`P3_*`**，scale 0→1.08→1.0（0.25 s） | 白→主色閃光 0.12 s、爆發環 2 圈、光柱、碎片 ≤ 120 顆、墨潑貼片 | 階段名水墨筆刷橫幅展開 0.3 s | 咆哮＋重擊 |
| T → T+0.9 | 繞 Boss 15° 並緩退 | 1.0 | 新姿態 | 霧色／火光 1.2 s 漸變到新階段（§5.3）、殘餘餘燼 | 橫幅共停留 1.4 s 後墨散 | 餘音 |
| T+0.9 → T+1.35 | 0.45 s 回到戰鬥機位（`csReset`） | 1.0 | 切 IdleAggro | 新階段常駐 aura 開始 | HUD 淡回 100% | — |
| ≤ 2.8 | — | — | 交還 AI（`AI.busyUntil=0`） | — | — | — |

規則：
- **遮掩**：部件顯示必須與閃光同一格，閃光至少蓋住 2 幀；部件用 scale 彈出，不用淡入（淡入會穿幫）。
- 主角在爆發時被風壓推退約 0.4 m 並播 Guard（保留現有行為）。
- 轉換後 Boss `glow` 底值：二階 0.7、三階 1.0。
- `eng.rm`（減少動態）：取消仰拍與慢放、震屏減半，其餘照常、時長不變。
- 不得延長答題計時或改變戰鬥規則。

### 3.2 各 Boss 差異
| Boss | 鏡頭 | 爆發特效重點 | 字幕樣式 |
|---|---|---|---|
| sentinel | 仰拍偏向背後門板（看樹根爆出） | 地面 6 方向樹根破土（各延遲 0–0.2 s）、木屑、苔綠孢子 | 綠墨筆刷 |
| gargoyle | 機位略高，隨它騰空上揚 8° | 石殼碎片外噴（一般池、有重力）、熔橘火星上竄 | 橘墨筆刷 |
| priest | 正面略低，看光環在頭後展開 | 地面結霜圈 0.4 s 擴到 r 8 m、冰刺一圈、雪粒在空中停 0.2 s 再落 | 冰藍細筆 |
| executioner | 爆發瞬間硬切側面 0.1 s 再切回（處刑感） | 斧落點紫色裂痕放射、影臂伸出拖墨絲、2 個殘影 | 紫墨粗筆，帶一道斧痕切口 |
| devourer 二階 | 推到胸口嘴特寫再退開 | 書頁貼片（≤ 40 片）飛旋成翼、金字粒子從主角被吸向胸口 | 紅字＋金邊 |
| devourer 三階 | 先拉遠看全身墨潮，爆發瞬間急推 | 全畫面墨收縮→紅光環炸開、墨潮貼地推到場邊、畫面去色（sat 0.3）0.4 s 後恢復 | 黑底紅字、放大 1.2 倍、帶震動 |

---

## 4. 特效清單（給特效：`fx.js`／`bossfx.js`／`vfx2.js`）

### 4.1 手機效能預算
- 同時存活：**加色池 ≤ 500、一般池 ≤ 300、刀光條紋 ≤ 160**（現有池上限 700/400/260 是硬上限，常態要壓在預算內）。
- 單一事件新增 ≤ 120 顆；同時全螢幕貼片（閃光、暗角脈衝）≤ 2 層。
- 新貼圖用 canvas 生成或 ≤ 256² 小圖集；特效燈最多 2 盞（danger 點光＋爆發點光，用完歸零），不投影。
- 低效能降級（FPS < 40 持續 2 s）：粒子數 ×0.5，關掉墨潑貼片與殘影。
- 顏色集中在常數表 `PAL`：金 #ffd27a、墨 #0b0a0f、白熱 #fff2c0、受擊紅 #c0242a、預警紅 #ff2a1a，Boss 主色見 §2。

### 4.2 清單
| # | 事件 | 視覺描述 | 顏色 | 時長 | 優先 |
|---|---|---|---|---|---|
| 1 | 玩家一般斬 | 筆刷形刀光（頭粗尾細、帶飛白），命中點小金火花 15 顆＋短白閃 | 金＋白 | 刀光 0.25 s、火花 0.4 s | P0 |
| 2 | 連斬 2–5 段 | 各段刀光角度交錯；段數越高越粗；第 3 段起加墨滴飛濺；第 5 段畫出金色「收鋒」大弧 | 金→白熱 | 每段 0.22 s | P0 |
| 3 | 完美斬 | 刀光後 0.05 s 第二道金色細線「一閃」＋命中點金箔碎片 30 顆緩慢飄落＋「完美」字 | 金箔 | 0.6 s | P0 |
| 4 | 終結斬（擊殺） | 慢動作中一道貫穿畫面的金色墨筆橫劃，命中點金＋墨雙色粒子 100 顆，地面墨暈擴散 | 金＋墨 | 1.0 s | P0 |
| 5 | 彈反 | 交擊白金火花 60 顆＋細環＋瞬閃，Boss 武器迸出主色碎光；「彈反」金字 | 白金 | 0.35 s | P0 |
| 6 | 閃避翻滾 | 原位留 1 個墨色殘影淡出＋腳下塵土弧；完美閃避加金色時間漣漪圈 | 墨＋金 | 0.4 s | P1 |
| 7 | 玩家受擊 | 暗紅墨潑貼片（非寫實血）＋邊緣紅暗角脈衝＋主角閃紅 | #c0242a | 0.3 s | P0 |
| 8 | 硬擋／格擋 | 鐵灰火花＋短白環 | 灰白 | 0.25 s | P1 |
| 9 | 突襲預警 | 落點先出現地面主色墨圈（0.18 s）、眼睛紅閃、「！」 | 紅＋主色 | 0.2 s | P0 |
| 10 | 一般蓄力預警 | 紅粒子向武器聚集、武器 `Glow` 轉紅、地面細紅弧（現有，改成筆刷形粒子） | #ff2a1a | 0.5–0.7 s | P0 |
| 11 | 必殺預警（danger） | 全畫面泛紅暗角、Boss 背後主色光柱、地面大型墨紅符紋圈逐筆畫出、招式名水墨橫幅 | 紅＋墨＋主色 | 0.9 s | P0 |
| 12 | 延遲攻擊解鎖 | 武器尖端一點白光「叮」 | 白 | 0.18 s | P1 |
| 13 | sentinel 招牌 | 鏽戟橫掃：橫向鏽色弧＋鏽屑；根鬚纏擊：一排 3–5 根樹根破土（間隔 0.05 s）；盾牌衝撞：前方木屑＋塵牆 | 鏽橙＋苔綠 | 0.5–0.8 s | P0 |
| 14 | gargoyle 招牌 | 俯衝利爪：翼尖兩道橘殘痕；狂亂爪擊：三道平行爪痕；碎石吐息：錐形燒紅碎石 40 顆＋煙 | 熔橘＋石灰 | 0.4–1.0 s | P0 |
| 15 | priest 招牌 | 霜槍突刺：直線冰晶刀光＋冰屑；冰面滑襲：地面結霜軌跡；冰棺降臨：4 根冰柱框住主角，0.6 s 後碎裂 | 霜藍＋白 | 0.5–1.2 s | P0 |
| 16 | executioner 招牌 | 斷頭斧斬：垂直紫墨巨刃＋地面裂痕；影步突進：2–3 個紫殘影；影分身處刑：左右分身同步揮斧後散成墨滴 | 影紫＋墨 | 0.4–1.0 s | P0 |
| 17 | devourer 招牌 | 噬語巨劍：紅黑雙層刀光；詞語風暴：書頁貼片 30 片繞場旋轉；終焉之言：地面紅字環向外擴到場邊＋全畫面墨收縮 | 噬紅＋墨＋金 | 0.6–1.5 s | P0 |
| 18 | Boss 受擊 | 命中處主色碎光＋材質碎屑（鏽／石／冰／墨／紙）各 8–15 顆 | 主色＋材質 | 0.3 s | P1 |
| 19 | 弱點擊破／破綻 | Boss 身上金色裂紋擴散＋「擊破」 | 金 | 0.6 s | P1 |
| 20 | 階段轉換 | 見 §3 | 主色 | ≤ 2.8 s | P0 |
| 21 | 二階以上常駐 aura | 主色餘燼緩慢上飄（≤ 6 顆/秒）；三階加地面墨潮環 | 主色＋墨 | 常駐 | P1 |
| 22 | Boss 死亡 | 身體從邊緣化為墨與金色字粒子上飄（約 1.6 s），最後一顆金光點落到主角劍上；主色全部轉金 | 墨→金 | 2.0 s | P0 |
| 23 | 喝藥 | 主角身上淡綠＋金螺旋上升 | 淡綠＋金 | 0.6 s | P2 |
| 24 | 場地環境 | 灰燼（gate）、碎石塵（cathedral）、雪（chapel）、墨霧（yard）、飄浮書頁（throne） | 場地色 | 常駐 | P2 |

---

## 5. 畫面（給畫面：`post.js`／`engine.js`／`screen2.js`）

現況 soul：bloom 0.6 / radius 0.55 / threshold 0.85；grade vig 0.36、grain 0.03、sat 0.94、contrast 1.05。

### 5.1 基準
- **Bloom**：strength 0.7、radius 0.55、threshold 0.82（只讓 `Glow` 與特效發光，盔甲高光不要爆）。完美斬／終結斬瞬間脈衝到 1.1，0.15 s 回落。
- **色調**：暗部偏冷青（shadow #dfe8ff），亮部偏暖金（high #ffe9c8）；sat 0.90、contrast 1.08。整體＝「冷墨底＋暖金光」。
- **暗角**：常態 0.38；P1：暗角邊緣用水墨筆刷遮罩取代圓形漸層。
- **顆粒**：0.03（低效能時 0）。
- **霧**：FogExp2；霧色永遠比場地主色暗。
- **光**：月光方向光（場地色）＋半球光；**Boss 背後加一盞弱主色輪廓光（rim）**，讓剪影從霧中跳出（P0）。

### 5.2 各場地主色（沿用現值，新增 rim）
| 場地 | Boss | 霧色 | 月光 | 霧密度 | Boss rim |
|---|---|---|---|---|---|
| gate_ruins | sentinel | #18211f | #9fc4b4 | 0.046 | #7dffb0 弱 |
| cathedral_roof | gargoyle | #151b28 | #8fb0e8 | 0.044 | #ff8a3a 弱 |
| frozen_chapel | priest | #1b2a37 | #a8dcff | 0.050 | #8fe3ff 弱 |
| execution_yard | executioner | #1d1727 | #a890d8 | 0.050 | #b07aff 弱 |
| throne_of_words | devourer | #24130f | #e2a284 | 0.050 | #ff3a2a 中 |

### 5.3 階段越高越壓迫
| 項目 | 一階 | 二階 | 三階（devourer） |
|---|---|---|---|
| 霧密度倍率 | ×1.00 | ×1.22 | ×1.44 |
| 霧色混入 Boss 主色 | 0% | 6% | 12% |
| 暗角 | 0.38 | 0.46 | 0.55＋墨邊 |
| 飽和度 | 0.90 | 0.86 | 0.80（主色保留不降） |
| Bloom strength | 0.70 | 0.78 | 0.85 |
| 火光／環境光 | 100% | 85%，偏主色 12% | 70%，偏主色 25% |
| 環境粒子 | ×1.0 | ×1.3＋主色餘燼 | ×1.5＋墨潮 |

全部在 PhaseShift 爆發後 1.2 s 內漸變完成。

### 5.4 螢幕閃光安全
白閃不透明度 ≤ 0.15、紅閃 ≤ 0.3；任何閃光 ≤ 3 次/秒。

---

## 6. 感覺（給感覺：`feel.js`）

現況：一般命中 hitStop 70–90 ms、重擊 120、擊殺 150＋slowmo 0.25/650；彈反 130＋slowmo 0.22/750；階段 shake 0.16/0.9。v2 統一為分級表（數值集中在 `feel.js` 一張表）：

| 等級 | 事件 | Hitstop (ms) | 震屏（幅度／秒／頻率） | 鏡頭 | 慢動作（倍率／ms） |
|---|---|---|---|---|---|
| S0 | 腳步、Boss 落地 | 0 | 0.012／0.20／9 | — | — |
| S1 | 一般斬、連斬 1–2 段、格擋 | 60 | 0.025／0.22／20 | 推 0.15 m 回彈 | — |
| S2 | 連斬 3–4 段、玩家輕受擊 | 80 | 0.045／0.28／18 | 推 0.25 m、FOV −1 | — |
| S3 | 完美斬、連斬第 5 段、玩家重受擊 | 110 | 0.07／0.35／14 | 推 0.4 m、FOV −2、偏向命中方向 | 0.5／200（只限完美斬） |
| S4 | 彈反、弱點擊破、突擊 | 130 | 0.06／0.30／24 | 側移 0.6、FOV −2 | 0.22／700（連擊中段 0.4／350） |
| S5 | 終結斬（擊殺 Boss） | 160 | 0.09／0.45／12 | 繞 20° 仰角、FOV −4 | 0.25／700 |
| S6 | 階段轉換爆發 | 0（用慢放代替） | 0.16／0.9／11 | 見 §3 | 爆發前 0.35／150 |
| S7 | Boss 死亡 | 200 | 0.05／0.5／10＋低頻 rumble | 拉高俯視主角 | 0.5／900 |

規則：
- Hitstop 不疊加：取最大值；同一 300 ms 內最多 2 次。5 連斬總 hitstop ≤ 450 ms。
- 玩家重受擊（必殺命中）＝S3＋紅暗角 0.3。
- 命中音效比特效早約 40 ms 預落（打擊更「實」），與特效協調。
- `eng.rm`：震屏 ×0.4、取消鏡頭推拉，慢動作保留。

---

## 7. 驗收標準

### 7.1 參考圖（美術）
- 每隻一階、二階（devourer 加三階）各 1 張 3/4 全身＋1 張正面或側面；另 1 張五隻比例圖。存 `art/reference/v2/`，命名 `<id>_p1.jpg`、`<id>_p2.jpg`、`devourer_p3.jpg`、`lineup.jpg`。
- 剪影測試：轉成全黑剪影並排，5 隻都能被認出；同一隻的一、二階剪影可分辨（新部件明顯突出外輪廓）。
- 無既有遊戲可辨識元素、無可讀真實文字。圖與本文件不符時以本文件為準重生成。

### 7.2 建模（每隻 Boss）
- [ ] 造型與參考圖相符：預覽 `art/blender/preview/<id>_views.jpg` 與參考圖並排，輪廓關鍵字全部做到。
- [ ] `check_soul_glb.py` 通過（≤ 40k 三角、貼圖 ≤ 2048、GLB ≤ 3 MB）。
- [ ] 17 個 clip 齊全；`merge_clipmeta.py` 更新後 hit 對準武器命中瞬間（抽查 Attack、Combo3、Delayed、Dash）。
- [ ] `P2_*`（devourer 加 `P3_*`）存在且預設隱藏；顯示後無明顯穿插。
- [ ] 至少 3 種 `Glow` 材質；一階發光不搶過盔甲主體。
- [ ] PhaseShift 2.0–2.6 s，蓄力→爆發→新姿態清楚，hit 在爆發格，結尾能接 IdleAggro。
- [ ] 遊戲內身高符合 §1。

### 7.3 特效
- [ ] §4 所有 P0 可在遊戲觸發並截圖；顏色走 `PAL`。
- [ ] 最重場景（devourer 三階＋詞語風暴＋連斬）在 Chrome DevTools 4× CPU 降速下 ≥ 40 FPS，粒子在預算內。

### 7.4 畫面
- [ ] 5 個場地各截一階、二階（devourer 三階）對照圖，壓迫感明顯遞增；Boss 剪影在霧中清楚（rim 生效）。
- [ ] 閃光符合 §5.4。

### 7.5 感覺
- [ ] §6 每級可觸發，數值集中一張表；連斬不拖慢節奏（5 連斬 hitstop 合計 ≤ 450 ms）。

### 7.6 動畫（階段轉換）
- [ ] 5 隻（devourer 2 次）轉換皆 ≤ 2.8 s，結束立即回到戰鬥。
- [ ] `P2_*`/`P3_*` 在閃光遮掩的那一格出現，逐格錄影看不到憑空出現。
- [ ] 階段名橫幅與爆發同步；`eng.rm` 下也正常結束。

### 7.7 每隻 Boss「完成」的定義
參考圖通過 7.1 → 模型通過 7.2 → 招牌特效與階段轉換在遊戲中跑過一次完整戰鬥（一階→二階（→三階）→死亡），截圖存 `art/v2/reports/shots/<id>_*.png`，主控台無錯誤。
