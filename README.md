# words-memorized-game（單字魂）

## 🎮 立即遊玩

### 👉 **[https://thortsui.github.io/words-memorized-game/](https://thortsui.github.io/words-memorized-game/)** 👈

用瀏覽器開啟即可遊玩。

---

## 修改紀錄（由 Claude 協助修改）

- 2026-11-28：在標題後面加上遊戲名稱「單字魂」（取自網頁標題），並在標題下方加入「🎮 立即遊玩」連結（GitHub Pages：https://thortsui.github.io/words-memorized-game/ ，已確認可以開啟）；新增本「修改紀錄」段落。只改 README，沒有改動程式。
- 2026-11-28：在 GitHub 倉庫的 Website 欄位填上遊戲連結，倉庫名稱正下方會顯示 🔗 連結（跟 Mobile-shooting-game 一樣）。這是倉庫設定，不是程式改動。
- 2026-11-28（v1.3.0）：魂系模式大改版。
  - 音效：換成真實取樣，包括金屬碰撞、揮劍破風、砍中肉／石、格擋、翻滾、重砸地，每隻 Boss 都有自己的咆哮，另有判定音與喝藥音。素材都是 CC0，來源列在 `public/sfx/CREDITS.md`。取樣載入失敗時會改用原本的合成音。
  - 配樂：魂系背景音樂加入低鼓脈動、弦樂墊和遠鐘，維持小聲。
  - 連斬：每題判定分成完美（剩 ≥60% 時間答對）、普通（答對但花比較久）、錯誤三種。整套題目答完後，才一口氣播出一段連續動作；每一刀依判定挑華麗版或樸素版，最後一刀依判定組合分成三種終結技，答錯則接被彈開的動作。
  - 主角動畫：從 17 個增加到 42 個。
  - Boss 招式：每隻 Boss 新增 5 招（魔王新增 7 招）。一階有 5–6 種攻擊，二階再多 4 種新招，魔王三階再多 2 種。
  - 難度：模擬結果和上一版相同。
  - 遊戲連結沒有變更，https://thortsui.github.io/words-memorized-game/ 推送後已確認可以開啟。
