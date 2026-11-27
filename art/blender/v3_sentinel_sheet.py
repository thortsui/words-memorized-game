"""v3 sentinel 預覽拼圖（系統 Python＋Pillow）：參考圖｜渲染 並排、各視角、特寫、動作連拍 → art/blender/preview/v3_sentinel_*.jpg
用法：python v3_sentinel_sheet.py"""
import os, glob, re
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "..", "v3", "tmp", "sentinel", "tiles")
OUT = os.path.join(HERE, "preview")
REF = os.path.join(HERE, "..", "reference", "v2")


def crop_char(im):
    """背景不透明：用背景色差找角色範圍再留邊。"""
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int)
    bg = a[2, 2]
    m = (abs(a - bg).sum(2) > 24)
    ys, xs = m.any(1).nonzero()[0], m.any(0).nonzero()[0]
    if len(xs) == 0:
        return im
    return im


def fit_h(im, H):
    return im.resize((int(im.width * H / im.height), H), Image.LANCZOS)


def label(im, txt):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 9 * len(txt) + 12, 20), fill=(0, 0, 0))
    d.text((6, 4), txt, fill=(255, 220, 120))
    return im


def row(ims, H, gap=8):
    ims = [fit_h(i, H) for i in ims]
    W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    s = Image.new("RGB", (W, H), (20, 20, 20))
    x = 0
    for i in ims:
        s.paste(i, (x, 0)); x += i.width + gap
    return s


def tile(name):
    p = os.path.join(T, name + ".png")
    return Image.open(p).convert("RGB") if os.path.exists(p) else None


def main():
    os.makedirs(OUT, exist_ok=True)
    for ref, crop, name in (("sentinel_p1.jpg", (330, 0, 1290, 768), "cmp_p1"), ("sentinel_p2.jpg", (420, 0, 1340, 768), "cmp_p2")):
        r = Image.open(os.path.join(REF, ref)).convert("RGB").crop(crop)
        t = tile(name)
        if t:
            row([label(r, "reference " + ref), label(t, "v3 render")], 900).save(os.path.join(OUT, f"v3_sentinel_{name}.jpg"), quality=90)
    vs = [tile(n) for n in ("v_front", "v_side", "v_back", "v_34", "v_p2_34", "v_p2_back")]
    vs = [label(v, n) for v, n in zip(vs, ("front", "side", "back", "3/4", "P2 3/4", "P2 back")) if v]
    if vs:
        row(vs, 800).save(os.path.join(OUT, "v3_sentinel_views.jpg"), quality=88)
    cl = sorted(glob.glob(os.path.join(T, "close_*.png")))
    if cl:
        ims = [label(Image.open(p).convert("RGB"), os.path.basename(p)[6:-4]) for p in cl]
        n = 4
        rows = [row(ims[i:i + n], 560) for i in range(0, len(ims), n)]
        W = max(r.width for r in rows)
        s = Image.new("RGB", (W, sum(r.height for r in rows) + 8 * (len(rows) - 1)), (20, 20, 20))
        y = 0
        for r in rows:
            s.paste(r, (0, y)); y += r.height + 8
        s.save(os.path.join(OUT, "v3_sentinel_closeups.jpg"), quality=88)
    acts = {}
    for p in sorted(glob.glob(os.path.join(T, "act_*.png"))):
        m = re.match(r"act_(\d+)_(.+)_(\d+)_f(\d+)\.png", os.path.basename(p))
        if m:
            acts.setdefault((int(m.group(1)), m.group(2)), []).append((int(m.group(3)), int(m.group(4)), p))
    rows = []
    for (r_, name), lst in sorted(acts.items()):
        lst.sort()
        ims = [Image.open(p).convert("RGB") for _, _, p in lst]
        w, hh = ims[0].size
        strip = Image.new("RGB", (w * len(ims), hh), (15, 15, 16))
        d = ImageDraw.Draw(strip)
        for i, im in enumerate(ims):
            strip.paste(im, (i * w, 0))
            d.text((i * w + 6, hh - 16), f"f{lst[i][1]}", fill=(200, 200, 200))
        d.text((6, 4), name, fill=(255, 220, 120))
        strip.save(os.path.join(T, f"strip_{name}.jpg"), quality=86)
        rows.append(strip)
    if rows:
        sc = 0.5
        rs = [r.resize((int(r.width * sc), int(r.height * sc)), Image.LANCZOS) for r in rows]
        half = (len(rs) + 1) // 2
        for k, part in enumerate((rs[:half], rs[half:])):
            if not part:
                continue
            s = Image.new("RGB", (part[0].width, sum(r.height for r in part)), (15, 15, 16))
            y = 0
            for r in part:
                s.paste(r, (0, y)); y += r.height
            s.save(os.path.join(OUT, f"v3_sentinel_actions{k + 1}.jpg"), quality=84)
    print("sheets ok", len(vs), len(cl), len(rows))


main()
