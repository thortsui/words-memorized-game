"""把 v3_devourer_v4shots.py 的圖塊拼成每招一張（上排一個角度、下排另一個角度，標格號／秒）。
python v3_devourer_v4sheet.py [shots_dir] [out_dir]
"""
import os, sys, glob, re
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "art", "v4", "tmp", "devourer", "shots")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "art", "v4", "tmp", "devourer")
tiles = {}
for p in glob.glob(os.path.join(SH, "*_f*.png")):
    m = re.match(r"(\w+?)_(-?\d+)_f(\d+)\.png", os.path.basename(p))
    if m:
        tiles.setdefault(m.group(1), {}).setdefault(int(m.group(2)), {})[int(m.group(3))] = p
for clip, byaz in tiles.items():
    azs = sorted(byaz)
    frs = sorted(set().union(*[set(v) for v in byaz.values()]))
    im0 = Image.open(next(iter(byaz[azs[0]].values())))
    W, H = im0.size
    W2, H2 = W - 30, H
    NC = 6
    rows_per = (len(frs) + NC - 1) // NC
    sheet = Image.new("RGB", (W2 * min(NC, len(frs)), H2 * len(azs) * rows_per), (8, 8, 10))
    d = ImageDraw.Draw(sheet)
    for ai, az in enumerate(azs):
        for k, f in enumerate(frs):
            r, c = ai * rows_per + k // NC, k % NC
            p = byaz[az].get(f)
            if not p:
                continue
            t = Image.open(p).convert("RGB")
            t = t.crop((15, 0, W - 15, H))
            sheet.paste(t, (c * W2, r * H2))
            d.rectangle([c * W2, r * H2, c * W2 + 70, r * H2 + 14], fill=(0, 0, 0))
            d.text((c * W2 + 3, r * H2 + 2), f"f{f} {f / 30:.2f}s", fill=(255, 220, 120))
    out = os.path.join(OUT, f"sheet_{clip}.jpg")
    sheet.save(out, quality=85)
    print(out)
