# 建模 B 報告：暗影行刑者 executioner、噬語魔王 devourer 重建

## 做了什麼
兩隻都依 `design.md` §2.4／§2.5、`art_guide.md` §4／§5 與 `art/reference/v2/*` 重建。用的是人形管線（Body／Builder／Rig，CC0 PBR 貼圖烘成 2048 圖集），型態部件做成**剛性綁骨的一般 Mesh**（parent 到 bone），匯出後節點 scale=0，所以遊戲可以用 scale 把它們彈出來。

### 共通做法
- 型態部件在烘焙時往旁邊移開（避免在本體上烘出 AO 陰影），烘完再分離成獨立物件，原點設在部件中心，掛到對應骨頭。
- 發光材質各自具名（`Glow_Eye`／`Glow_Rune`／`Glow_Weapon`／`P2_Glow_*`／`P3_Glow_*`）。gltf-transform 壓縮時關掉 `palette/join/flatten/instance`，材質名稱與節點階層都保留下來。
- 為了暗場地的可讀性，底色明度比舊版高；金屬加了磨亮邊緣；剪影上的主要部位放了 Glow（眼、斧／劍符紋）。

### executioner（主色 #b07aff）
- 一階：魁梧倒三角＋尖頂粗麻頭罩，一條眼縫（紫光＋細金線＋縫線），頭罩垂到胸前、下緣破爛。黑皮甲＋鉚釘鐵胸板、腹甲三道，胸口有抽象筆畫符紋（`Glow_Rune`）。大圓肩甲三層、裸露上臂、尖刺護腕、尖刺護膝、重靴。腰間兩條皮帶、兩道垂弧鐵鍊、4 個掛鎖，撕裂粗麻腰擺帶暗褐污漬（#3a2418，沒有用鮮紅）。巨斧：斧面比頭大、上緣兩個尖齒、頂端矛尖、柄末有金封印環，斧面兩側各 8 個原創抽象筆畫符紋（`Glow_Weapon`）。前臂和腳踝加了半透明墨影絲（`Ink`）。
- 二階節點（9 個）：`P2_HoodTorn`（Head：紫色漩渦貼圖面＋破口布緣＋翻開的布片）、`P2_ShadowArmL/R`（骨頭 ShadowArmL/R：背後墨影手臂，左手握影斧，右手張爪，帶紫色發光筋）、`P2_ChainHalo`（骨頭 ChainHalo：半徑 0.28H 的浮鍊環＋3 個掛鎖，所有片段裡都會慢轉）、`P2_AxeBlade2`（Weapon：反側第二片斧刃＋兩邊刃口紫光）、`P2_InkArmL/R`、`P2_InkLegL/R`（墨影變大）。
- 數據：**37,255 三角面**、**2.36 MB**、貼圖 1536（webp）。`check_soul_glb.py` 結果 OK。
- 片段與命中時間（秒）：Attack 0.533、Attack2 0.933、Combo3 0.6／1.0／2.133、Delayed 1.867、Dash 0.3、**PhaseShift 2.30 s，hit 1.0**（0–0.5 拖斧扭身 → 0.5–0.95 雙手舉斧後仰 → 1.0 砍進地面 → 拔斧、交叉架勢，結尾＝IdleAggro）。影臂會在命中前舉起、命中時劈下。

### devourer（主色 #ff3a2a）
- 一階：骷髏面（骨色、紅眼、牙列）＋金冠帶與後盔。角冠刻意做成**左右不對稱**：中央直角 1 根、左 3 根、右 2 根（右邊最長那根是獨立節點 `HornLongR`）、後掠 2 根長短不同，另外肩甲上有 2 根後掠尖刺。舊金浮雕板甲：胸前用 raycast 貼合的凸起捲紋，肩甲有圓徽章，墨污由材質處理。書頁披風是底布加上 177 張層疊書頁，往下擴散、拖地，地上也有散頁；左臂同樣披書頁。左掌心有紅色原創符紋與圓環。腰部有亞麻腰帶、鐵鍊、3 卷卷軸、長前擺。鋸齒巨劍拄地（齒朝劍柄），鋸齒內側有暗紅細線（`Glow_Weapon`），護手帶鉤。
- 二階節點：`P2_PageWingL/R`（骨頭 WingL/R：每側約 34 張書頁組成紙翼，頁緣燃紅 `P2_Glow_PageEdge`，會緩慢開合）、`P2_ChestMaw`（胸口豎直獠牙巨口，內部 `P2_Glow_Maw`）、`P2_ScriptChest`／`P2_ScriptL/R`／`P2_ScriptLegL/R`（浮雕紋轉紅 `P2_Glow_Script`）、`P2_SwordCracks`（劍身樹枝狀裂紋 `P2_Glow_Blade`）。
- 三階節點：`P3_Crown`（頭頂 4 段破碎紅黑光環）、`P3_HornBroken`（右長角斷根，鋸齒斷口加紅色斷面）、`P3_EyeFlames`（眼窩紅焰）、`P3_InkBody`（下半身墨潮＋往後捲的墨絲＋殘頁）、`P3_ArmorCrackedChest`／`P3_ArmorCrackedArm`（甲片剝落、暗色裂肉＋熔紅裂紋，位置在胸、腹、左上臂）、`P3_SwordWords`（劍外 3 圈漂浮原創符字環，紅＋金，另加劍尖延長段，劍長 +20%）。
- 數據：**38,201 三角面**、**2.13 MB**、貼圖 1536。
- 片段與命中時間：Attack 0.533、Attack2 1.0、Combo3 0.633／1.067／2.233、Delayed 1.967、Dash 0.4、**PhaseShift 2.50 s，hit 1.2**（劍拄地、左手按胸 → 前傾蓄力 → 挺胸仰首爆發 → 雙手握劍斜指地面）、**PhaseShift2 2.60 s，hit 1.233**（單膝跪、劍插地、痙攣 → 仰天張臂 → 起身拔劍）。

## 改了哪些檔（全部是新檔或建模 B 自己的檔）
- `art/blender/v2b_hum.py`：組裝／烘焙（具名 Glow／墨影材質）、型態部件分離與綁骨、匯出。
- `art/blender/v2b_executioner.py`、`v2b_devourer.py`：模型、骨架、武器姿勢、額外骨頭（影臂、鍊環、紙翼）的程序動作。
- `art/blender/v2b_exec_actions.py`、`v2b_dev_actions.py`：從 `soul_boss_actions.py` 複製後改寫，新的 PhaseShift 和 PhaseShift2 在這裡。
- `art/blender/v2b_glbpost.py`：把 GLB 裡的 P2_／P3_ 節點 scale 設成 0，並列出部件清單。`art/blender/v2b_run.sh`：一鍵跑完整流程（建模→預覽→壓縮→隱藏）。
- 輸出：`public/models/boss_executioner.glb`、`boss_devourer.glb`；`art/blender/export_raw/boss_{executioner,devourer}.glb/.clipmeta.json`；`src/battle/view3d/clipmeta.json`（用 `merge_clipmeta.py` 更新）；`art/blender/source/v2b_*.blend`。烘焙貼圖在 `art/blender/textures/baked/v2b_*`。
- 舊的 `build_*` 腳本和共用 lib 都沒有動。

## 驗證
- 預覽圖（`art/blender/preview/`）：
  - executioner：`v2b_executioner_views.jpg`（正、側、背、3/4、P2 的 3/4、P2 正面、P2 背面）、`v2b_executioner_closeup.jpg`、`v2b_executioner_actions.jpg`（17 個片段＋二階的 IdleAggro／Combo3）。
  - devourer：`v2b_devourer_views.jpg`（正、側、背、3/4、P2 的 3/4、P2 背面、P3 的 3/4、P3 正面）、`v2b_devourer_closeup.jpg`、`v2b_devourer_actions.jpg`（18 個片段＋二階 IdleAggro、三階 PhaseShift2／Combo3）。
- 遊戲內：dev server 開在 5187 埠，用 Playwright 打到這兩隻並截圖，存在 `art/v2/shots/modeling_b/`（`game_executioner_p1/phaseshift/p2.jpg`、`game_devourer_p1/phaseshift/phaseshift2/p3.jpg`）。
  - phaseShow 的紀錄：executioner 用 PhaseShift，彈出 9 個節點；devourer 二階用 PhaseShift（9 個節點），三階用 **PhaseShift2**（7 個節點）。console error 與 pageerror 都是 0。
- `verify.mjs soul`：5/5 Boss 打完（`verify_end.png` 顯示「噬語魔王被討伐了」），`console` 錯誤為空。這次執行我沒有保存 pageerror 欄位；前面兩次自己的測試裡 pageerror 都是 0。截圖：`verify_executioner.png`、`verify_devourer.png`。
- `check_soul_glb.py`：executioner OK。devourer 只被標「extra: PhaseShift2」，這是共用檢查表沒有列進這個新片段，其餘（三角面、大小、貼圖、骨頭、clipmeta 時長）都通過。

## 已知問題／交接
1. **devourer 三階斷角**：右邊最長的角是獨立剛體節點 `HornLongR`（不是 P 節點，預設顯示）。phaseShow 目前沒有「三階隱藏某節點」的機制，所以現在三階時 `P3_HornBroken` 斷根和原角會同時出現。**請動畫在 form≥3 的爆發那一格把 `HornLongR` 設成 visible=false（或 scale 0）**，只要加一行。
2. `check_soul_glb.py` 的 BOSS 清單沒有 `PhaseShift2`，所以 devourer 會被判 FAIL（共用檔，不是我負責的）。
3. 墨影材質（`Ink`／`P2_InkShadow`／`P3_Ink`）是 alpha blend。Blender EEVEE 預覽裡偏亮、偏彩色，遊戲內實際呈現是暗墨色，以遊戲截圖為準。
4. executioner 在遊戲裡仍然偏暗：主要靠頭罩尖、巨斧、紫色符紋和輪廓光來讀形。已經把底色明度調高一次，如果還想更亮，建議由畫面（screen2）調 Boss 輪廓光，模型這邊也可以再把 `val` 調高。
5. devourer 的亞麻前擺偏灰（Fabric030 本身偏暗），參考圖裡較白；書頁上沒有字跡紋理，只有紙質與污漬。
6. P3_InkBody 是剛性掛在 Hips 上的墨潮裙。腳在墨潮裡面，大動作（Attack 下蹲）時墨潮會穿進地面，因為是墨，可以接受。
