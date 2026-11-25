# 產生合成的單字書頁測試圖（python tests/fixtures/make_pages.py）
# 輸出 page1.png（單欄）、page2.png（兩欄＋側邊單元標籤＋片語）、page3.jpg（模擬手機拍照：陰影、雜訊、微傾斜，
# 並且故意印錯一個字 recieve），以及 truth.json（每頁的正確條目，量測正確率用）。
# 字型用 Windows 內建的 Times New Roman／Georgia 與微軟正黑體／標楷體。
import json, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
F = "C:/Windows/Fonts/"
W, H = 1240, 1754
CJK = lambda ch: "\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" or ch in "…—"


def fonts(en, zh, size):
    return ImageFont.truetype(F + en, size), ImageFont.truetype(F + zh, size)


def runs(text):
    out = []
    for ch in text:
        k = CJK(ch)
        if out and out[-1][0] == k:
            out[-1][1] += ch
        else:
            out.append([k, ch])
    return out


def draw_text(d, x, y, text, fen, fzh, fill=(20, 20, 20)):
    for k, s in runs(text):
        f = fzh if k else fen
        d.text((x, y + (2 if k else 0)), s, font=f, fill=fill)
        x += d.textlength(s, font=f)
    return x


def width(d, text, fen, fzh):
    return sum(d.textlength(s, font=(fzh if k else fen)) for k, s in runs(text))


def wrap(d, text, fen, fzh, maxw):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and width(d, t, fen, fzh) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def entry(d, x, y, maxw, e, size, en_font="times.ttf", bold="timesbd.ttf", zh_font="msjh.ttc"):
    fb, fz = fonts(bold, zh_font, size)
    fe, _ = fonts(en_font, zh_font, size)
    fs, fzs = fonts(en_font, zh_font, size - 3)
    cx = draw_text(d, x, y, e["en"], fb, fz)
    if e["pos"] != "片語":
        cx = draw_text(d, cx + size * 0.7, y, e["pos"], fe, fz)
    draw_text(d, cx + size * 0.7, y, e["zh"], fe, fz)
    y += int(size * 1.55)
    for line in wrap(d, e["ex"], fs, fzs, maxw - 30):
        draw_text(d, x + 30, y, line, fs, fzs, fill=(45, 45, 45))
        y += int(size * 1.35)
    if e.get("tr"):
        draw_text(d, x + 30, y, e["tr"], fs, fzs, fill=(90, 90, 90))
        y += int(size * 1.35)
    return y + int(size * 0.75)


P1 = [
    dict(en="abandon", pos="v.", zh="放棄；拋棄", ex="The sailors abandoned the damaged ship.", blank="abandoned", tr="船員們拋棄了那艘受損的船。"),
    dict(en="dye", pos="v.", zh="染色", ex="Mary dyed her hair red last week.", blank="dyed", tr="瑪麗上星期把頭髮染成紅色。"),
    dict(en="fluent", pos="adj.", zh="流利的", ex="She is fluent in three languages.", blank="fluent", tr="她能流利地說三種語言。"),
    dict(en="immediately", pos="adv.", zh="立刻；馬上", ex="Please call me immediately if anything changes.", blank="immediately", tr="如果有任何變化，請立刻打電話給我。"),
    dict(en="recycle", pos="v.", zh="回收利用", ex="David recycles bottles and old newspapers every weekend.", blank="recycles", tr="大衛每個週末都回收瓶子和舊報紙。"),
    dict(en="record", pos="v., n.", zh="記錄；唱片", ex="The scientist recorded the temperature of the water every hour during the long experiment.", blank="recorded", tr="科學家在漫長的實驗中每小時記錄水溫。"),
    dict(en="generous", pos="adj.", zh="慷慨的；大方的", ex="It was generous of him to share his lunch.", blank="generous", tr="他很大方地分享午餐。"),
    dict(en="opportunity", pos="n.", zh="機會", ex="This job is a great opportunity for young people.", blank="opportunity", tr="這份工作對年輕人是很好的機會。"),
]
P2L = [
    dict(en="ancient", pos="adj.", zh="古代的", ex="They visited an ancient temple in the mountains.", blank="ancient"),
    dict(en="borrow", pos="v.", zh="借入", ex="May I borrow your umbrella for a while?", blank="borrow"),
    dict(en="climate", pos="n.", zh="氣候", ex="The climate here is warm and wet in summer.", blank="climate"),
    dict(en="damage", pos="n., v.", zh="損害；毀壞", ex="The storm damaged many houses near the coast.", blank="damaged"),
    dict(en="effort", pos="n.", zh="努力", ex="With a little more effort, you will pass the test.", blank="effort"),
    dict(en="familiar", pos="adj.", zh="熟悉的", ex="His voice sounded familiar to me.", blank="familiar"),
]
P2R = [
    dict(en="give away", pos="片語", zh="贈送、分送", ex="The store is giving away free samples today.", blank="giving away"),
    dict(en="pick up", pos="片語", zh="撿起；接（某人）", ex="She picked up the coins from the floor.", blank="picked up"),
    dict(en="look forward to", pos="片語", zh="期待", ex="We look forward to seeing you again soon.", blank="look forward to"),
    dict(en="run out of", pos="片語", zh="用完", ex="The car ran out of gas on the highway.", blank=""),
    dict(en="take care of", pos="片語", zh="照顧", ex="Nurses take care of patients in the hospital.", blank="take care of"),
]
P3 = [
    dict(en="recieve", pos="v.", zh="收到；接受", ex="Did you recieve my letter yesterday?", blank="recieve"),  # 故意印錯（正確是 receive）
    dict(en="harvest", pos="n.", zh="收穫；收成", ex="Farmers celebrate after a good harvest.", blank="harvest"),
    dict(en="journey", pos="n.", zh="旅程", ex="The journey across the desert took five days.", blank="journey"),
    dict(en="knowledge", pos="n.", zh="知識", ex="Reading is a good way to gain knowledge.", blank="knowledge"),
    dict(en="polite", pos="adj.", zh="有禮貌的", ex="It is polite to say thank you.", blank="polite"),
    dict(en="quarrel", pos="v.", zh="爭吵", ex="The brothers quarreled over a toy.", blank="quarreled"),
    dict(en="struggle", pos="v.", zh="奮鬥；掙扎", ex="He struggled to carry the heavy box upstairs.", blank="struggled"),
]


def page1():
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fz = fonts("timesbd.ttf", "msjhbd.ttc", 34)
    draw_text(d, 110, 90, "NO.307 Unit 5", ft, fz)
    d.line((110, 140, W - 110, 140), fill=(60, 60, 60), width=2)
    y = 175
    for e in P1:
        y = entry(d, 110, y, W - 220, e, 30)
    fp, _ = fonts("times.ttf", "msjh.ttc", 22)
    d.text((W / 2 - 10, H - 90), "42", font=fp, fill=(60, 60, 60))
    im.save(os.path.join(HERE, "page1.png"))
    return [dict(e, unit="NO.307 Unit 5") for e in P1]


def page2():
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fz = fonts("georgiab.ttf", "msjhbd.ttc", 28)
    colw = 500
    xl, xr = 90, 680
    draw_text(d, xl, 100, "Unit 6", ft, fz)
    draw_text(d, xr, 100, "Key Phrases", ft, fz)
    y = 170
    for e in P2L:
        y = entry(d, xl, y, colw, e, 26, "georgia.ttf", "georgiab.ttf", "kaiu.ttf")
    y = 170
    for e in P2R:
        y = entry(d, xr, y, colw, e, 26, "georgia.ttf", "georgiab.ttf", "kaiu.ttf")
    d.line((W / 2 + 15, 160, W / 2 + 15, H - 400), fill=(170, 170, 170), width=1)
    im.save(os.path.join(HERE, "page2.png"))
    return [dict(e, unit="Unit 6") for e in P2L] + [dict(e, unit="Key Phrases") for e in P2R]


def page3():
    random.seed(7)
    im = Image.new("RGB", (W, H), (250, 248, 242))
    d = ImageDraw.Draw(im)
    ft, fz = fonts("timesbd.ttf", "msjhbd.ttc", 34)
    draw_text(d, 130, 110, "Unit 7", ft, fz)
    y = 190
    for e in P3:
        y = entry(d, 130, y, W - 260, e, 32)
    im = im.rotate(0.7, resample=Image.BICUBIC, fillcolor=(250, 248, 242))
    # 陰影：左上亮、右下暗，再加一道斜的暗帶
    sh = Image.new("L", (W, H))
    px = sh.load()
    for yy in range(H):
        for xx in range(W):
            v = 255 - int(70 * (xx / W * 0.6 + yy / H * 0.4)) - (35 if abs(xx - yy * 0.5 - 300) < 120 else 0)
            px[xx, yy] = max(0, v)
    sh = sh.filter(ImageFilter.GaussianBlur(40))
    im = Image.composite(im, Image.new("RGB", (W, H), (0, 0, 0)), sh)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    nz = Image.effect_noise((W, H), 9).convert("RGB")
    im = Image.blend(im, nz, 0.06)
    im.save(os.path.join(HERE, "page3.jpg"), quality=82)
    return [dict(e, unit="Unit 7") for e in P3]


if __name__ == "__main__":
    truth = {"page1.png": page1(), "page2.png": page2(), "page3.jpg": page3()}
    for v in truth.values():
        for e in v:
            e.pop("tr", None)
    with open(os.path.join(HERE, "truth.json"), "w", encoding="utf-8") as f:
        json.dump(truth, f, ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in truth.items()})
