"""v3 噬語魔王：程序產生的來源貼圖（系統 Python＋numpy＋Pillow，不下載任何檔案）。
輸出到 art/v3/tmp/devourer/tex/：
  dv_scroll_h.png   可平鋪的密集卷草／渦紋浮雕高度圖（1024，凸起線＝白）
  dv_pages_col.png  書頁圖集 2048×1024（4×2 種頁面：泛黃紙、原創不可讀字跡、纖維、水漬、對折痕、焦黑捲邊、撕口；
                    第 7、8 格是披風內層的暗頁）
  dv_pages_nrm.png  對應法線（OpenGL，+Y 向上）
  dv_streak.png     可平鋪的縱向墨流條紋遮罩（512，白＝墨），條紋末端成滴狀
用法：python v3_devourer_tex.py
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "art", "v3", "tmp", "devourer", "tex")
os.makedirs(OUT, exist_ok=True)


def vnoise(n, cells, seed, octaves=4, wrap=True):
    """可平鋪的數值雜訊（0..1）。"""
    rng = np.random.default_rng(seed)
    acc = np.zeros((n, n)); amp = 1.0; tot = 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        g = rng.random((c, c))
        im = Image.fromarray((g * 255).astype(np.uint8))
        big = np.tile(np.asarray(im, float), (3, 3))
        bi = Image.fromarray(big.astype(np.uint8)).resize((n * 3, n * 3), Image.BICUBIC)
        a = np.asarray(bi, float)[n:2 * n, n:2 * n] / 255.0
        acc += a * amp; tot += amp; amp *= 0.5
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min() + 1e-9)


# ---------------------------------------------------------------- 卷草浮雕
def scroll_tex(N=1024, seed=3):
    rnd = random.Random(seed)
    im = Image.new("L", (N * 3, N * 3), 0)
    d = ImageDraw.Draw(im)
    lw = max(3, int(N * 0.017))        # 線寬約 1.1 cm（貼圖覆蓋約 0.36 m）

    def poly(pts, w):
        for ox in (0, N, 2 * N):
            for oy in (0, N, 2 * N):
                d.line([(x + ox, y + oy) for x, y in pts], fill=255, width=w, joint="curve")

    def spiral(cx, cy, r0, turns, ccw, ang0):
        pts = []
        steps = int(60 * turns)
        for k in range(steps + 1):
            t = k / steps
            a = ang0 + (1 if ccw else -1) * t * turns * 2 * math.pi
            r = r0 * (1 - 0.86 * t) ** 1.1
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts

    def leaf(x, y, a, ln, w):
        pts = []
        for k in range(12):
            t = k / 11
            s = math.sin(math.pi * t) * w
            pts.append((x + math.cos(a) * ln * t - math.sin(a) * s, y + math.sin(a) * ln * t + math.cos(a) * s))
        return pts

    centers = []
    tries = 0
    while len(centers) < 34 and tries < 6000:
        tries += 1
        x, y = rnd.uniform(0, N), rnd.uniform(0, N)
        r = rnd.uniform(0.05, 0.095) * N
        ok = True
        for (cx, cy, cr) in centers:
            dx = min(abs(x - cx), N - abs(x - cx)); dy = min(abs(y - cy), N - abs(y - cy))
            if math.hypot(dx, dy) < (r + cr) * 0.95:
                ok = False; break
        if ok:
            centers.append((x, y, r))
    for i, (x, y, r) in enumerate(centers):
        ccw = i % 2 == 0
        a0 = rnd.uniform(0, 6.28)
        poly(spiral(x, y, r, rnd.uniform(1.6, 2.3), ccw, a0), lw)
        # 渦心的小圓珠
        for ox in (0, N, 2 * N):
            for oy in (0, N, 2 * N):
                rr = lw * 0.9
                d.ellipse([x + ox - rr * 0.4, y + oy - rr * 0.4, x + ox + rr * 0.4, y + oy + rr * 0.4], fill=255)
        # 從外圈拉出的莖，連到鄰近渦紋（S 形卷草）
        nb = sorted(centers, key=lambda c: (min(abs(c[0] - x), N - abs(c[0] - x))) ** 2 + (min(abs(c[1] - y), N - abs(c[1] - y))) ** 2)[1:3]
        for (cx, cy, cr) in nb:
            dx = cx - x; dy = cy - y
            if abs(dx) > N / 2: dx -= math.copysign(N, dx)
            if abs(dy) > N / 2: dy -= math.copysign(N, dy)
            L = math.hypot(dx, dy)
            ux, uy = dx / L, dy / L
            px, py = -uy, ux
            sgn = rnd.choice((-1, 1))
            pts = []
            for k in range(25):
                t = k / 24
                bow = math.sin(math.pi * t) * 0.18 * L * sgn
                pts.append((x + ux * (r + (L - r - cr) * t) + px * bow, y + uy * (r + (L - r - cr) * t) + py * bow))
            poly(pts, int(lw * 0.85))
            # 莖上的葉片（兩三片）
            for t in (0.3, 0.55, 0.78):
                k = int(t * 24)
                lx, ly = pts[k]
                a = math.atan2(py * sgn, px * sgn) + rnd.uniform(-0.5, 0.5)
                poly(leaf(lx, ly, a, rnd.uniform(0.035, 0.06) * N, rnd.uniform(0.008, 0.013) * N), max(2, lw // 2))
    a = np.asarray(im, float)[N:2 * N, N:2 * N] / 255.0
    img = Image.fromarray((a * 255).astype(np.uint8))
    # 圓滑斷面（浮雕斜面）
    sm = img.filter(ImageFilter.GaussianBlur(lw * 0.22))
    h = np.asarray(sm, float) / 255.0
    h = np.clip(h * 1.25, 0, 1)
    # 錘紋細雜訊
    h = h * 0.92 + vnoise(N, 16, seed + 9, 3) * 0.08
    Image.fromarray((h * 255).astype(np.uint8)).save(os.path.join(OUT, "dv_scroll_h.png"))
    print("scroll ok", len(centers))


# ---------------------------------------------------------------- 書頁
def glyph_strokes(rnd, x, y, s):
    """一個原創不可讀字形（鉤、弧、點組成），回傳筆畫折線清單。"""
    strokes = []
    kind = rnd.randrange(7)
    if kind == 0:     # 鉤
        strokes.append([(x, y - s), (x, y + s * 0.6), (x + s * 0.5, y + s * 0.9)])
    elif kind == 1:   # 弧
        strokes.append([(x + s * 0.6 * math.cos(a), y + s * 0.7 * math.sin(a)) for a in np.linspace(0.6, 4.2, 7)])
    elif kind == 2:   # 斜交
        strokes.append([(x - s * 0.4, y + s), (x + s * 0.4, y - s)])
        strokes.append([(x - s * 0.5, y), (x + s * 0.6, y + s * 0.2)])
    elif kind == 3:   # 波
        strokes.append([(x - s * 0.6 + k * s * 0.3, y + (s * 0.35 if k % 2 else -s * 0.35)) for k in range(5)])
    elif kind == 4:   # 圈＋尾
        strokes.append([(x + s * 0.45 * math.cos(a), y - s * 0.3 + s * 0.45 * math.sin(a)) for a in np.linspace(0, 6.3, 9)])
        strokes.append([(x + s * 0.4, y - s * 0.2), (x + s * 0.3, y + s * 1.0)])
    elif kind == 5:   # 三折
        strokes.append([(x - s * 0.5, y - s * 0.6), (x + s * 0.3, y - s * 0.2), (x - s * 0.3, y + s * 0.3), (x + s * 0.5, y + s * 0.7)])
    else:             # 豎＋點
        strokes.append([(x, y - s), (x + s * 0.1, y + s)])
        strokes.append([(x + s * 0.5, y - s * 0.1), (x + s * 0.55, y)])
    return strokes


def page_cell(W, H, seed, dark=False):
    """一張頁面：回傳 (rgb float 0..1, height 0..1)。"""
    rnd = random.Random(seed)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    u = xx / (W - 1); v = yy / (H - 1)
    base = np.array([0xc8, 0xb4, 0x8a]) / 255.0
    light = np.array([0xdc, 0xca, 0xa0]) / 255.0
    old = np.array([0xa8, 0x8e, 0x5e]) / 255.0
    if dark:
        base = np.array([0x8a, 0x73, 0x50]) / 255.0; light = base * 1.12; old = base * 0.75
    n1 = vnoise(max(W, H), 6, seed, 4)[:H, :W]
    n2 = vnoise(max(W, H), 24, seed + 1, 3)[:H, :W]
    col = base[None, None, :] * np.ones((H, W, 1))
    col = col + (light - base)[None, None, :] * np.clip((n1 - 0.45) * 2.2, 0, 1)[..., None]
    col = col + (old - base)[None, None, :] * np.clip((0.5 - n1) * 2.0, 0, 1)[..., None]
    # 紙纖維：細長橫向條紋
    fib = rng.random((H, W // 6 + 1))
    fib = np.asarray(Image.fromarray((fib * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), float) / 255.0
    col *= (0.94 + 0.08 * fib)[..., None]
    height = 0.5 + 0.06 * (fib - 0.5) + 0.05 * (n2 - 0.5)
    # 水漬（環狀邊緣較深）
    for _ in range(rnd.randint(1, 3)):
        cx, cy, r = rnd.uniform(0.15, 0.85) * W, rnd.uniform(0.15, 0.85) * H, rnd.uniform(0.10, 0.28) * W
        dist = np.hypot(xx - cx, yy - cy) / r + (n2 - 0.5) * 0.5
        ring = np.exp(-((dist - 1.0) / 0.08) ** 2) * 0.22 + (dist < 1.0) * 0.07
        col *= (1 - ring)[..., None] * np.array([1.0, 0.97, 0.92])[None, None, :] + (ring * 0)[..., None]
    # 對折痕（橫向或縱向）
    if rnd.random() < 0.7:
        if rnd.random() < 0.6:
            fy = rnd.uniform(0.35, 0.65) * H
            dd = (yy - fy - (xx - W / 2) * rnd.uniform(-0.05, 0.05))
        else:
            fx = rnd.uniform(0.4, 0.6) * W
            dd = (xx - fx)
        crease = np.exp(-(dd / 2.2) ** 2)
        col *= (1 - 0.18 * crease)[..., None]
        height -= 0.12 * crease
        height += 0.05 * np.tanh(dd / 30.0) * np.sign(rnd.random() - 0.5)
    # 字跡：4–8 行波浪字
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    nl = rnd.randint(7, 10) if not dark else rnd.randint(5, 8)
    top = H * rnd.uniform(0.10, 0.16); bot = H * rnd.uniform(0.80, 0.88)
    gs = (bot - top) / nl * 0.22
    for li in range(nl):
        y0 = top + (bot - top) * (li + 0.5) / nl
        x = W * rnd.uniform(0.08, 0.14)
        xe = W * rnd.uniform(0.84, 0.92) if li < nl - 1 or rnd.random() < 0.5 else W * rnd.uniform(0.4, 0.7)
        ph = rnd.uniform(0, 6.28); wav = rnd.uniform(0.5, 1.6)
        while x < xe:
            wl = rnd.randint(2, 6)
            for _ in range(wl):
                yb = y0 + math.sin(x / W * 6 + ph) * gs * 0.6 * wav
                sz = gs * rnd.uniform(0.75, 1.15)
                sts = glyph_strokes(rnd, x, yb, sz)
                for st in sts:
                    dr.line(st, fill=255, width=max(2, int(gs * 0.24)), joint="curve")
                nx_ = x + sz * rnd.uniform(1.0, 1.3)
                # 連筆（草書感）
                dr.line([sts[0][-1], (nx_ - sz * 0.5, yb + sz * 0.6)], fill=200, width=max(1, int(gs * 0.14)))
                x = nx_
                if x > xe:
                    break
            x += gs * rnd.uniform(1.6, 2.6)
    ink = np.asarray(img.filter(ImageFilter.GaussianBlur(0.6)), float) / 255.0
    ink *= (0.75 + 0.25 * n2)
    inkc = np.array([0x2a, 0x1e, 0x14]) / 255.0
    col = col * (1 - ink[..., None] * 0.92) + inkc[None, None, :] * ink[..., None] * 0.92
    height -= 0.10 * ink
    # 焦黑捲邊：沿邊緣距離＋雜訊，只在 30–60% 的周長
    ed = np.minimum(np.minimum(u, 1 - u) * W, np.minimum(v, 1 - v) * H)
    ang = np.arctan2(v - 0.5, u - 0.5)
    burnmask = np.zeros_like(u)
    for _ in range(rnd.randint(2, 4)):
        a0 = rnd.uniform(-math.pi, math.pi); wa = rnd.uniform(0.5, 1.3)
        da = np.abs((ang - a0 + math.pi) % (2 * math.pi) - math.pi)
        burnmask = np.maximum(burnmask, np.clip(1 - da / wa, 0, 1) ** 0.6)
    depth = (0.05 + 0.10 * burnmask * (0.6 + 0.8 * n2)) * min(W, H)
    b = np.clip(1 - ed / np.maximum(depth, 1), 0, 1)
    scorch = np.clip((b - 0.0) * 1.4, 0, 1)
    c1 = np.array([0x3a, 0x24, 0x14]) / 255.0; c2 = np.array([0x0b, 0x0a, 0x0f]) / 255.0
    brown = np.clip(b * 2.2, 0, 1)[..., None]
    col = col * (1 - brown * 0.65) + c1[None, None, :] * brown * 0.65
    blk = np.clip((b - 0.55) * 3, 0, 1)[..., None]
    col = col * (1 - blk) + c2[None, None, :] * blk
    # 邊緣一圈極細焦痕（所有邊都有一點）
    rim = np.clip(1 - ed / (0.018 * min(W, H)), 0, 1)[..., None]
    col = col * (1 - rim * 0.7) + c1[None, None, :] * rim * 0.7
    height += 0.10 * scorch * (n2 - 0.3)
    # 撕口：2–5 個楔形暗口（幾何上邊緣也有鋸齒，這裡補上纖維暗影）
    for _ in range(rnd.randint(1, 3)):
        side = rnd.randrange(4)
        t = rnd.uniform(0.15, 0.85)
        dep = rnd.uniform(0.04, 0.10)
        wd = rnd.uniform(0.006, 0.016)
        if side == 0:   p, q = u - t, v
        elif side == 1: p, q = u - t, 1 - v
        elif side == 2: p, q = v - t, u
        else:           p, q = v - t, 1 - u
        wedge = np.clip(1 - (np.abs(p) / wd + q / dep), 0, 1)
        m = (wedge > 0).astype(float)
        col = col * (1 - m[..., None] * 0.6) + c1[None, None, :] * m[..., None] * 0.6
        height -= 0.15 * m
    # 紅墨一滴（少數頁）
    if rnd.random() < 0.25 and not dark:
        cx, cy = rnd.uniform(0.3, 0.7) * W, rnd.uniform(0.1, 0.3) * H
        drip = np.exp(-((xx - cx) / 5) ** 2) * (yy > cy) * np.exp(-np.clip(yy - cy, 0, None) / (0.15 * H))
        red = np.array([0x6a, 0x10, 0x0c]) / 255.0
        col = col * (1 - drip[..., None] * 0.8) + red[None, None, :] * drip[..., None] * 0.8
    return np.clip(col, 0, 1), np.clip(height, 0, 1)


def normal_from_height(h, strength):
    gy, gx = np.gradient(h)
    nx = -gx * strength; ny = gy * strength; nz = np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / L, ny / L, nz / L], -1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def pages_atlas():
    W, H = 512, 512
    col = np.zeros((H * 2, W * 4, 3)); hh = np.zeros((H * 2, W * 4))
    for k in range(8):
        r, c = divmod(k, 4)
        cc, h = page_cell(W, H, 100 + k * 17, dark=(k >= 6))
        col[r * H:(r + 1) * H, c * W:(c + 1) * W] = cc
        hh[r * H:(r + 1) * H, c * W:(c + 1) * W] = h
    Image.fromarray((col * 255).astype(np.uint8)).save(os.path.join(OUT, "dv_pages_col.png"))
    Image.fromarray(normal_from_height(hh, 9.0)).save(os.path.join(OUT, "dv_pages_nrm.png"))
    print("pages ok")


def streak_tex(N=512, seed=21):
    """縱向墨流條紋：從上方起始、往下漸細、末端滴狀。白＝墨。"""
    rnd = random.Random(seed)
    im = Image.new("L", (N * 3, N * 3), 0)
    d = ImageDraw.Draw(im)
    for _ in range(30):
        x = rnd.uniform(0, N); y = rnd.uniform(0, N)
        ln = rnd.uniform(0.30, 0.80) * N
        w0 = rnd.uniform(0.022, 0.045) * N
        for ox in (0, N, 2 * N):
            for oy in (0, N, 2 * N):
                pts = []
                steps = 14
                for k in range(steps + 1):
                    t = k / steps
                    pts.append((x + ox + math.sin(t * 3 + x) * 2.0, y + oy + ln * t))
                for k in range(steps):
                    t = k / steps
                    w = max(1, int(w0 * (1 - 0.6 * t)))
                    d.line([pts[k], pts[k + 1]], fill=255, width=w)
                rr = w0 * 0.75
                ex, ey = pts[-1]
                d.ellipse([ex - rr, ey - rr * 0.6, ex + rr, ey + rr * 1.4], fill=255)
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), float)[N:2 * N, N:2 * N]
    Image.fromarray(a.astype(np.uint8)).save(os.path.join(OUT, "dv_streak.png"))
    print("streak ok")


# ---------------------------------------------------------------- 長 S 形卷草（藤蔓＋葉，嵌板用）
def vine_tex(N=1024, seed=11):
    rnd = random.Random(seed)
    im = Image.new("L", (N * 3, N * 3), 0)
    d = ImageDraw.Draw(im)
    lw = max(3, int(N * 0.014))

    def poly(pts, w):
        for ox in (0, N, 2 * N):
            for oy in (0, N, 2 * N):
                d.line([(x + ox, y + oy) for x, y in pts], fill=255, width=w, joint="curve")

    def curl(x, y, r, a0, sgn, turns=1.3):
        pts = []
        for k in range(40):
            t = k / 39
            a = a0 + sgn * t * turns * 2 * math.pi
            rr = r * (1 - 0.85 * t)
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        return pts
    rows = 4
    for r in range(rows):
        y0 = (r + 0.5) * N / rows
        ph = rnd.uniform(0, 6.28)
        amp = N / rows * 0.30
        pts = [(x, y0 + amp * math.sin(2 * math.pi * 2 * x / N + ph)) for x in np.linspace(0, N, 120)]
        poly(pts, lw)
        # 每個波峰／波谷長出一個卷鬚渦＋兩片葉
        for k in range(4):
            xk = (k + 0.25) * N / 4 - ph / (2 * math.pi * 2) * N
            xk %= N
            yk = y0 + amp * math.sin(2 * math.pi * 2 * xk / N + ph)
            sgn = 1 if math.sin(2 * math.pi * 2 * xk / N + ph) > 0 else -1
            r_ = N / rows * rnd.uniform(0.17, 0.22)
            cx, cy = xk + r_ * 0.9, yk - sgn * r_ * 0.95
            stem = [(xk + t * r_ * 0.9, yk - sgn * t * r_ * 0.2) for t in np.linspace(0, 1, 8)]
            poly(stem, int(lw * 0.8))
            poly(curl(cx, cy, r_, math.pi + (0.3 if sgn > 0 else -0.3), -sgn), int(lw * 0.85))
            for side in (-1, 1):
                lx, ly = xk - r_ * 0.4, yk
                a = math.atan2(-sgn, -0.6 * side)
                L = r_ * rnd.uniform(0.7, 1.0); Wd = r_ * 0.22
                leaf = []
                for t in np.linspace(0, 1, 14):
                    s_ = math.sin(math.pi * t) * Wd
                    leaf.append((lx + math.cos(a) * L * t - math.sin(a) * s_, ly + math.sin(a) * L * t + math.cos(a) * s_))
                for t in np.linspace(1, 0, 14):
                    s_ = -math.sin(math.pi * t) * Wd * 0.4
                    leaf.append((lx + math.cos(a) * L * t - math.sin(a) * s_, ly + math.sin(a) * L * t + math.cos(a) * s_))
                for ox in (0, N, 2 * N):
                    for oy in (0, N, 2 * N):
                        d.polygon([(x + ox, y + oy) for x, y in leaf], fill=255)
    a = np.asarray(im, float)[N:2 * N, N:2 * N] / 255.0
    img = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(lw * 0.25))
    h = np.asarray(img, float) / 255.0
    h = np.clip(h * 1.2, 0, 1) * 0.92 + vnoise(N, 16, seed + 9, 3) * 0.08
    Image.fromarray((h * 255).astype(np.uint8)).save(os.path.join(OUT, "dv_vine_h.png"))
    print("vine ok")


# ---------------------------------------------------------------- 三階裂肉：熔紅裂縫網（可平鋪，發光貼圖）
def cracks_tex(N=512, seed=5):
    rnd = random.Random(seed)
    im = Image.new("L", (N * 3, N * 3), 0)
    d = ImageDraw.Draw(im)

    def walk(x, y, a, ln, w, depth):
        pts = [(x, y)]
        for _ in range(int(ln / 6)):
            a += rnd.uniform(-0.5, 0.5)
            x += math.cos(a) * 6; y += math.sin(a) * 6
            pts.append((x, y))
            if depth < 3 and rnd.random() < 0.06:
                walk(x, y, a + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.2), ln * 0.5, max(1, w - 1), depth + 1)
        for ox in (0, N, 2 * N):
            for oy in (0, N, 2 * N):
                d.line([(px + ox, py + oy) for px, py in pts], fill=255, width=w)
    for _ in range(14):
        walk(rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(0, 6.28), rnd.uniform(150, 320), rnd.randint(2, 4), 0)
    a = np.asarray(im, float)[N:2 * N, N:2 * N] / 255.0
    core = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), float) / 255.0
    halo = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5.0)), float) / 255.0
    n = vnoise(N, 8, seed + 3, 3)
    base = np.stack([0.10 + 0.06 * n, 0.04 + 0.02 * n, 0.04 + 0.02 * n], -1)     # 暗色裂肉 #2a1414 附近
    glow = np.clip(core * 1.2 + halo * 0.6, 0, 1)[..., None] * np.array([1.0, 0.25, 0.08])[None, None, :]
    col = np.clip(base + glow, 0, 1)
    Image.fromarray((col * 255).astype(np.uint8)).save(os.path.join(OUT, "dv_cracks.png"))
    print("cracks ok")


if __name__ == "__main__":
    scroll_tex()
    pages_atlas()
    streak_tex()
    vine_tex()
    cracks_tex()
