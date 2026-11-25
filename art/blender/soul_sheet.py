"""Compose preview tiles into sheets (system Python + Pillow).
usage: python soul_sheet.py <tiles_dir> <preview_dir> <model>
"""
import sys, os, glob, re
from PIL import Image, ImageDraw

tiles, outdir, model = sys.argv[1], sys.argv[2], sys.argv[3]
views = sorted(glob.glob(os.path.join(tiles, "view_*.png")))
if views:
    ims = [Image.open(p).convert("RGB") for p in views]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * len(ims), h), (15, 15, 16))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * w, 0))
    sheet.save(os.path.join(outdir, f"{model}_views.jpg"), quality=90)
cl = sorted(glob.glob(os.path.join(tiles, "close_*.png")))
if cl:
    ims = [Image.open(p).convert("RGB") for p in cl]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * len(ims), h), (15, 15, 16))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * w, 0))
    sheet.save(os.path.join(outdir, f"{model}_closeup.jpg"), quality=90)
acts = {}
for p in sorted(glob.glob(os.path.join(tiles, "act_*.png"))):
    m = re.match(r"act_(\d+)_(.+)_(\d)_f(\d+)\.png", os.path.basename(p))
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
        d.text((i * w + 6, h - 16), f"f{lst[i][1]}", fill=(200, 200, 200))
    d.text((6, 4), name, fill=(255, 220, 120))
    strip.save(os.path.join(tiles, f"strip_{name}.jpg"), quality=88)
    rows.append(strip)
if rows:
    sc = 0.6
    rs = [r.resize((int(r.width * sc), int(r.height * sc)), Image.LANCZOS) for r in rows]
    sheet = Image.new("RGB", (rs[0].width, sum(r.height for r in rs)), (15, 15, 16))
    y = 0
    for r in rs:
        sheet.paste(r, (0, y)); y += r.height
    sheet.save(os.path.join(outdir, f"{model}_actions.jpg"), quality=85)
print("sheets ok", len(views), len(rows))
