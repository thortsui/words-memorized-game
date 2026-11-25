# 貼圖來源（魂系 Boss 與場景）

全部是 CC0 1.0（公眾領域貢獻）的 PBR 掃描／程序材質，可商用、不需署名；這裡留紀錄方便追溯。
Boss 的掃描材質只當作「烘焙來源」：在 Blender 以方盒投影混合後，烘成每隻 Boss 一組 1024² 圖集
（`textures/baked/<model>_basecolor|normal|orm|emissive.jpg`），GLB 內只有烘好的圖集。

## Boss 用（`textures/boss/<ID>/`，ambientCG 1K-JPG，2026-11-26 下載）

下載網址格式：`https://ambientcg.com/get?file=<ID>_1K-JPG.zip`；資產頁：`https://ambientcg.com/view?id=<ID>`。
zip 只解出 jpg；NormalDX／NormalGL／IdMask／Opacity 沒有用到，已刪除。

| ID | 用在 |
| --- | --- |
| Rock042L、Rock023 | 石像鬼石灰岩身體（顏色、粗糙度、凹凸） |
| Moss002 | 石像鬼苔蘚 |
| Fabric045、Fabric036 | 霜冠祭司內袍、外披、聖帶 |
| Ice003 | 祭司冰柱、冰晶王冠、提燈冰面 |
| Metal046B | 祭司銀面具、魔王黑鋼 |
| Metal013 | 祭司鐵權杖、魔王巨劍 |
| Leather028 | 祭司皮帶與靴、魔王腰帶與劍柄 |
| Metal042B | 魔王暗金板甲 |
| Chainmail002 | 魔王鎖子甲 |
| Fabric029 | 魔王披風底布、前擋布 |
| Paper006 | 魔王書頁披風 |
| Rock048、Fabric043、Snow006、Paper004、Metal025、Rust005 | 已下載作候選，目前腳本沒有用到 |

## 教堂競技場（`textures/cathedral/`，處理後各 ≤1024² JPEG）

來源檔取自另一個專案的 CC0 材質庫（`TAI game/素材/blender/textures_src`，只讀），沒有另外下載。

| 本專案組名 | 資產 | 來源 | 處理 |
| --- | --- | --- | --- |
| stone | Concrete020 | ambientCG https://ambientcg.com/view?id=Concrete020 | 壓暗、去飽和、加對比，1024² |
| masonry | white_sandstone_bricks（Rob Tuytel） | Poly Haven https://polyhaven.com/a/white_sandstone_bricks | 壓暗、偏冷灰，1024² |
| ground | Ground023 | ambientCG https://ambientcg.com/view?id=Ground023 | 壓暗、粗糙度下限 0.6，1024² |
| iron | Metal028 | ambientCG https://ambientcg.com/view?id=Metal028 | 縮到 512² |

## 草原戰場

`arena_meadow.glb` 沒有使用任何貼圖（全部是頂點色）。
