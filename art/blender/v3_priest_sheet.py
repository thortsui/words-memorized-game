"""v3 霜冠祭司：拼預覽圖（系統 Python＋Pillow）。
用法：python v3_priest_sheet.py <tiles_dir> <out.jpg> name1 name2 ...
      python v3_priest_sheet.py --ref <tiles_dir> <out_dir>   產生「參考圖｜渲染」並排圖
"""
import sys, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(HERE), "reference", "v2")


def fit(im, hgt):
    return im.resize((max(1, int(im.width * hgt / im.height)), hgt), Image.LANCZOS)


def row(ims, hgt, labels=None):
    ims = [fit(i.convert("RGB"), hgt) for i in ims]
    s = Image.new("RGB", (sum(i.width for i in ims), hgt), (20, 20, 22))
    x = 0
    d = ImageDraw.Draw(s)
    for k, i in enumerate(ims):
        s.paste(i, (x, 0))
        if labels:
            d.text((x + 8, 8), labels[k], fill=(255, 220, 120))
        x += i.width
    return s


if sys.argv[1] == "--ref":
    T, O = sys.argv[2], sys.argv[3]
    p1 = Image.open(os.path.join(REF, "priest_p1.jpg"))
    p2 = Image.open(os.path.join(REF, "priest_p2.jpg"))
    L = p1.crop((90, 0, 720, 768)); R = p1.crop((660, 0, 1300, 768))
    P2 = p2.crop((380, 0, 1080, 768))
    pairs = [("v3_priest_cmp_p1A", L, "p1_refA"), ("v3_priest_cmp_p1B", R, "p1_refB"), ("v3_priest_cmp_p2", P2, "p2_front")]
    for name, ref, tile in pairs:
        f = os.path.join(T, tile + ".png")
        if os.path.exists(f):
            row([ref, Image.open(f)], 800, ["reference", "v3 render (" + tile + ")"]).save(os.path.join(O, name + ".jpg"), quality=90)
            print("wrote", name)
    sys.exit(0)
T, out = sys.argv[1], sys.argv[2]
names = sys.argv[3:]
ims = [Image.open(os.path.join(T, n + ".png")) for n in names if os.path.exists(os.path.join(T, n + ".png"))]
row(ims, 800, names).save(out, quality=88)
print("wrote", out)
