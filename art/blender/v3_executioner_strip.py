"""把預覽圖拼成一列（系統 Python）。用法：python v3_executioner_strip.py <out.jpg> <scale> <png...>"""
import sys
from PIL import Image
out, sc = sys.argv[1], float(sys.argv[2])
ims = [Image.open(f).convert("RGB") for f in sys.argv[3:]]
H = max(i.height for i in ims)
ims = [i.resize((int(i.width * H / i.height), H)) for i in ims]
s = Image.new("RGB", (sum(i.width for i in ims), H))
x = 0
for i in ims:
    s.paste(i, (x, 0)); x += i.width
s = s.resize((int(s.width * sc), int(s.height * sc)), Image.LANCZOS)
s.save(out, quality=88)
