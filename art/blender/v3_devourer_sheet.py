"""v3 噬語魔王：把預覽圖塊拼成比對圖（系統 Python＋Pillow）。
輸出 art/blender/preview/v3_devourer_cmp_p1/p2/p3.jpg（參考圖｜本模型鏡像渲染＋半透明疊圖）、_views_p1/p2/p3.jpg、_close_*.jpg、_sil.jpg
"""
import os, glob
from PIL import Image, ImageOps, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TILES = os.path.join(ROOT, "art", "v3", "tmp", "devourer", "tiles")
OUT = os.path.join(HERE, "preview")
REF = os.path.join(ROOT, "art", "reference", "v2")


def lab(im, t):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8 * len(t) + 12, 20], fill=(0, 0, 0))
    d.text((6, 4), t, fill=(255, 220, 120))
    return im


for f in (1, 2, 3):
    p = os.path.join(TILES, f"cmp_p{f}.png")
    if os.path.exists(p):
        ours0 = ImageOps.mirror(Image.open(p).convert("RGB"))
        ours = Image.new("RGB", ours0.size, ours0.getpixel((5, 5)))
        ours.paste(ours0, (-40, 0))
        ref = Image.open(os.path.join(REF, f"devourer_p{f}.jpg")).convert("RGB").resize(ours.size)
        over = Image.blend(ref, ours, 0.5)
        W, H = ours.size
        sheet = Image.new("RGB", (W * 2, H * 2), (10, 10, 12))
        sheet.paste(lab(ref.copy(), f"reference p{f}"), (0, 0))
        sheet.paste(lab(ours.copy(), f"v3 model p{f} (mirrored render, ortho 25deg)"), (W, 0))
        sheet.paste(lab(over, "overlay 50%"), (0, H))
        vs = [os.path.join(TILES, f"view_p{f}_{n}.png") for n in ("front", "side", "back", "sideR")]
        vs = [Image.open(v).convert("RGB") for v in vs if os.path.exists(v)]
        if vs:
            strip = Image.new("RGB", (sum(v.width for v in vs), vs[0].height), (10, 10, 12))
            x = 0
            for v, n in zip(vs, ("front", "side(L)", "back", "side(R)")):
                strip.paste(lab(v, n), (x, 0)); x += v.width
            strip = strip.resize((W, int(strip.height * W / strip.width)))
            sheet.paste(strip, (W, H + (H - strip.height) // 2))
        sheet.save(os.path.join(OUT, f"v3_devourer_cmp_p{f}.jpg"), quality=88)
        print("cmp", f)
cl = [("head", "close_head"), ("chest", "close_chest"), ("cape", "close_cape"), ("sword", "close_sword"), ("p2chest", "close_p2chest"), ("p3head", "close_p3head")]
for nm, t in cl:
    p = os.path.join(TILES, t + ".png")
    if os.path.exists(p):
        Image.open(p).convert("RGB").save(os.path.join(OUT, f"v3_devourer_close_{nm}.jpg"), quality=90)
p = os.path.join(TILES, "sil_side.png")
if os.path.exists(p):
    Image.open(p).convert("RGB").save(os.path.join(OUT, "v3_devourer_sil.jpg"), quality=90)
rs = sorted(glob.glob(os.path.join(TILES, "rest_*.png")))
if rs:
    ims = [Image.open(r).convert("RGB") for r in rs]
    s = Image.new("RGB", (sum(i.width for i in ims), ims[0].height))
    x = 0
    for i in ims:
        s.paste(i, (x, 0)); x += i.width
    s.save(os.path.join(ROOT, "art", "v3", "tmp", "devourer", "rest.jpg"), quality=85)
print("sheet ok")
