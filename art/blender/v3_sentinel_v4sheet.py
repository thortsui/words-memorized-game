"""v1.3.0 sentinel 新招拼圖（系統 Python＋Pillow）：python v3_sentinel_v4sheet.py <outdir> [hits.json]
每個片段一張：上排 3/4 視角、下排側面，每格標格號（命中格標紅）。"""
import os, sys, json
from PIL import Image, ImageDraw

d = sys.argv[1]
info = json.load(open(os.path.join(d, "frames.json")))
meta = {}
mp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_raw", "boss_sentinel.clipmeta.json")
if len(sys.argv) > 2:
    mp = sys.argv[2]
if os.path.exists(mp):
    meta = json.load(open(mp, encoding="utf-8"))
for name, frames in info.items():
    hits = [round(t * 30) for t in meta.get(name, {}).get("hits", [])]
    ims = [[Image.open(os.path.join(d, f"{name}_{f:03d}_{v}.png")).convert("RGB") for f in frames] for v in (0, 1)]
    w, hh = ims[0][0].size
    per = 7
    rows = (len(frames) + per - 1) // per
    sheet = Image.new("RGB", (w * min(per, len(frames)), hh * 2 * rows), (15, 15, 15))
    dr = ImageDraw.Draw(sheet)
    for i, f in enumerate(frames):
        r, c = divmod(i, per)
        for v in (0, 1):
            sheet.paste(ims[v][i], (c * w, (r * 2 + v) * hh))
        col = (255, 80, 80) if any(abs(f - x) <= 1 for x in hits) else (255, 220, 120)
        dr.rectangle((c * w, r * 2 * hh, c * w + 70, r * 2 * hh + 16), fill=(0, 0, 0))
        dr.text((c * w + 4, r * 2 * hh + 2), f"f{f} {f / 30:.2f}s", fill=col)
    sheet.save(os.path.join(d, f"sheet_{name}.jpg"), quality=85)
    print("sheet", name, sheet.size)
