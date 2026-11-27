"""單字魂 v3 主角：把預覽圖塊拼成對照圖（系統 Python + Pillow）。
用法：python v3_hero_sheet.py [tiles_dir]
輸出 art/blender/preview/：
  v3_hero_compare.jpg   參考圖｜渲染（正面、左側面）＋ 背面、3/4 前、3/4 後
  v3_hero_closeups.jpg  頭盔、左肩甲、胸腰皮件、罩袍下緣＋鎖子甲、披風背面、靴、劍
  v3_hero_dark.jpg      暗場（過肩視角、正面、背面）
  v3_hero_actions.jpg   17 個動作連拍
"""
import sys, os, glob, re
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
tiles = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "art", "v3", "tmp", "hero", "tiles")
out = os.path.join(HERE, "preview")
ref = Image.open(os.path.join(ROOT, "art", "reference", "hero_knight_sheet.jpg")).convert("RGB")


def T(name):
    p = os.path.join(tiles, name)
    return Image.open(p).convert("RGB") if os.path.exists(p) else None


def label(im, text, col=(30, 30, 30)):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 9 * len(text) + 12, 18), fill=(235, 235, 235))
    d.text((6, 3), text, fill=col)
    return im


def refcrop(cx):
    # 參考圖 726px 高；人物 668px（頭頂 y=38、腳底 y=706）。取 560:800 比例
    h = ref.height; w = int(round(h * 560 / 800))
    return ref.crop((cx - w // 2, 0, cx - w // 2 + w, h)).resize((560, 800), Image.LANCZOS)


pairs = [(label(refcrop(430), "REF front"), label(T("view_front.png"), "v3 front")),
         (label(refcrop(1012), "REF side (L)"), label(T("view_side.png"), "v3 side (L)"))]
row2 = [label(T(f"view_{k}.png"), "v3 " + k) for k in ("back", "threeq", "threeqback") if T(f"view_{k}.png")]
if all(p[1] for p in pairs):
    W = 560 * 4; Hh = 800 * 2
    sheet = Image.new("RGB", (max(W, 560 * len(row2)), Hh), (200, 200, 200))
    x = 0
    for a, b in pairs:
        sheet.paste(a, (x, 0)); sheet.paste(b, (x + 560, 0)); x += 1120
    for i, im in enumerate(row2):
        sheet.paste(im, (i * 560, 800))
    # 比例格線（0.05H），只畫在上排
    d = ImageDraw.Draw(sheet)
    for k in range(0, 21):
        y = int(round(706 * 800 / 726 - k * 0.05 * 668 * 800 / 726))
        d.line((0, y, W, y), fill=(120, 150, 200) if k % 2 else (90, 120, 190), width=1)
        d.text((W - 34, y - 10), f"{k * 0.05:.2f}", fill=(60, 80, 140))
    sheet.save(os.path.join(out, "v3_hero_compare.jpg"), quality=88)
cl = [(k, T(f"close_{k}.png")) for k in ("helm", "lshoulder", "chest", "hem", "capeback", "boots", "sword")]
cl = [(k, im) for k, im in cl if im]
if cl:
    w, h = cl[0][1].size
    cols = 4
    rows = (len(cl) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), (40, 40, 40))
    for i, (k, im) in enumerate(cl):
        sheet.paste(label(im, k), ((i % cols) * w, (i // cols) * h))
    sheet.save(os.path.join(out, "v3_hero_closeups.jpg"), quality=88)
dk = [T(n) for n in ("dark_overshoulder.png", "dark_front.png", "dark_back.png")]
dk = [im for im in dk if im]
if dk:
    hh = max(im.height for im in dk)
    sheet = Image.new("RGB", (sum(im.width for im in dk), hh), (5, 5, 6))
    x = 0
    for im in dk:
        sheet.paste(im, (x, 0)); x += im.width
    sheet.save(os.path.join(out, "v3_hero_dark.jpg"), quality=88)
acts = {}
for p in sorted(glob.glob(os.path.join(tiles, "act_*.png"))):
    m = re.match(r"act_(\d+)_(.+)_(\d+)_f(\d+)\.png", os.path.basename(p))
    if m:
        acts.setdefault((int(m.group(1)), m.group(2)), []).append((int(m.group(3)), int(m.group(4)), p))
rows = []
for (r, name), lst in sorted(acts.items()):
    lst.sort()
    ims = [Image.open(p).convert("RGB") for _, _, p in lst]
    w, h = ims[0].size
    strip = Image.new("RGB", (w * len(ims), h), (15, 15, 16))
    d = ImageDraw.Draw(strip)
    for i, im in enumerate(ims):
        strip.paste(im, (i * w, 0))
        d.text((i * w + 6, h - 16), f"f{lst[i][1]}", fill=(40, 40, 40))
    d.text((6, 4), name, fill=(150, 30, 20))
    rows.append(strip)
if rows:
    sc = 0.55
    rs = [r.resize((int(r.width * sc), int(r.height * sc)), Image.LANCZOS) for r in rows]
    half = (len(rs) + 1) // 2
    for part, chunk in (("a", rs[:half]), ("b", rs[half:])):
        if not chunk:
            continue
        sheet = Image.new("RGB", (chunk[0].width, sum(r.height for r in chunk)), (15, 15, 16))
        y = 0
        for r in chunk:
            sheet.paste(r, (0, y)); y += r.height
        sheet.save(os.path.join(out, f"v3_hero_actions_{part}.jpg"), quality=85)
print("sheets ok", len(cl), len(rows))
