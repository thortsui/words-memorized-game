"""把預覽小圖拼成一張（系統 Python + Pillow）：
python make_sheet.py views <out.jpg> <img...>
python make_sheet.py actions <out.jpg> <frames_dir> <prefix> [Action,Action...]（每個動作一列，附名稱與影格）
"""
import sys, os, glob
from PIL import Image, ImageDraw, ImageFont

ORDER = ["Idle", "Enter", "Telegraph", "Attack", "Attack2", "Hit", "Stagger", "PhaseShift", "Die"]


def font(sz):
    try:
        return ImageFont.truetype("arial.ttf", sz)
    except Exception:
        return ImageFont.load_default()


mode, out = sys.argv[1], sys.argv[2]
if mode == "views":
    ims = [Image.open(p).convert("RGB") for p in sys.argv[3:]]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * len(ims), h))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * w, 0))
    sheet.save(out, quality=90)
else:
    d, prefix = sys.argv[3], sys.argv[4]
    only = sys.argv[5].split(",") if len(sys.argv) > 5 else ORDER
    rows = []
    for a in only:
        fs = sorted(glob.glob(os.path.join(d, f"{prefix}__{a}__*.png")))
        if fs:
            rows.append((a, fs))
    w, h = Image.open(rows[0][1][0]).size
    n = max(len(r[1]) for r in rows)
    sheet = Image.new("RGB", (w * n, h * len(rows)), (10, 10, 12))
    dr = ImageDraw.Draw(sheet)
    for r, (a, fs) in enumerate(rows):
        for c, p in enumerate(fs):
            sheet.paste(Image.open(p).convert("RGB"), (c * w, r * h))
            dr.text((c * w + 6, r * h + h - 20), "f" + os.path.basename(p)[:-4].split("_")[-1], fill=(190, 190, 190), font=font(14))
        dr.text((8, r * h + 6), a, fill=(255, 220, 120), font=font(22))
    sheet.save(out, quality=88)
print("sheet", out)
