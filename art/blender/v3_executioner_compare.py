"""v3 行刑者：參考圖｜渲染 並排比較圖（系統 Python + Pillow）。
用法：python v3_executioner_compare.py <預覽 png 目錄> <輸出目錄>
"""
import sys, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(HERE), "reference", "v2")
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
p1 = Image.open(os.path.join(REF, "executioner_p1.jpg")).convert("RGB")
p2 = Image.open(os.path.join(REF, "executioner_p2.jpg")).convert("RGB")
PAIRS = [
    ("threeq", p1, (150, 10, 1010, 760), "view_0_threeq.png"),
    ("front", p1, (150, 10, 1010, 760), "view_1_front.png"),
    ("side", p1, (150, 10, 1010, 760), "view_2_side.png"),
    ("back", p1, (150, 10, 1010, 760), "view_3_back.png"),
    ("p2_threeq", p2, (100, 10, 1300, 760), "view_4_p2_threeq.png"),
    ("p2_back", p2, (100, 10, 1300, 760), "view_5_p2_back.png"),
    ("close_hood", p1, (370, 15, 560, 230), "close_0_hood.png"),
    ("close_armL", p1, (560, 200, 760, 470), "close_1_armL.png"),
    ("close_armR", p1, (160, 200, 380, 530), "close_2_armR.png"),
    ("close_waist", p1, (320, 300, 620, 640), "close_3_waist.png"),
    ("close_axe", p1, (680, 220, 1000, 480), "close_4_axe.png"),
    ("close_leg", p1, (240, 480, 520, 760), "close_5_leg.png"),
    ("close_p2_head", p2, (380, 20, 600, 260), "close_9_p2_head.png"),
]
H = 900
for name, ref, box, fn in PAIRS:
    p = os.path.join(src, fn)
    if not os.path.exists(p):
        continue
    a = ref.crop(box); b = Image.open(p).convert("RGB")
    a = a.resize((int(a.width * H / a.height), H), Image.LANCZOS)
    b = b.resize((int(b.width * H / b.height), H), Image.LANCZOS)
    s = Image.new("RGB", (a.width + b.width + 8, H), (20, 20, 20))
    s.paste(a, (0, 0)); s.paste(b, (a.width + 8, 0))
    d = ImageDraw.Draw(s)
    d.text((8, 8), "reference", fill=(255, 220, 120)); d.text((a.width + 16, 8), "v3 render", fill=(255, 220, 120))
    s.save(os.path.join(out, f"v3_executioner_{name}.jpg"), quality=88)
    print("wrote", name)
