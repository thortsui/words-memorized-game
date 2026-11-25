"""回合制（可愛）模式的草原戰場 arena_meadow。
用法：blender --background --factory-startup --python build_arena_meadow.py -- <out.glb> <preview_dir> <out.blend>
造型依據：art/reference/scene_meadow.jpg（構圖）、cute_monster_lineup.jpg（風格）。
約定：中心在原點、地面 z=0、8 m 半徑內淨空；玩家鏡頭由 -Y 往 +Y 看，城堡與遠景在 +Y。
上色：全部用頂點色（COLOR_0），單一材質、無貼圖；靜態無動畫。
"""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix, Euler, noise

argv = sys.argv[sys.argv.index("--") + 1:]
OUT_GLB, PREVIEW_DIR, OUT_BLEND = argv[0], argv[1], argv[2]
random.seed(11)
R = random.uniform

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ---------- 小工具 ----------
def sst(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def mul(a, k):
    return tuple(min(1.0, c * k) for c in a)


def lin(c):
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)


def nz(x, y, s, o=0.0):
    return noise.noise(Vector((x * s + o, y * s - o * 0.7, o * 1.3)))


# ---------- 調色盤（sRGB） ----------
G_LIGHT, G_MID, G_DARK = (0.60, 0.88, 0.28), (0.40, 0.78, 0.22), (0.25, 0.64, 0.22)
G_FAR = (0.62, 0.88, 0.62)
DIRT, DIRT_D, DIRT_L = (0.84, 0.66, 0.40), (0.70, 0.50, 0.30), (0.92, 0.77, 0.52)
TRUNK, TRUNK_D = (0.62, 0.40, 0.22), (0.42, 0.26, 0.15)
LEAF = [((0.14, 0.52, 0.22), (0.50, 0.86, 0.26)), ((0.10, 0.50, 0.30), (0.36, 0.82, 0.40)), ((0.26, 0.56, 0.14), (0.68, 0.88, 0.24))]
STONES = [(0.70, 0.66, 0.58), (0.60, 0.58, 0.56), (0.76, 0.68, 0.54), (0.54, 0.52, 0.50)]
MOSS = (0.50, 0.78, 0.30)
WOOD, WOOD_D = (0.76, 0.52, 0.28), (0.50, 0.32, 0.17)
C_WALL, C_WALL_D = (0.90, 0.83, 0.68), (0.72, 0.62, 0.50)
C_TRIM = (0.62, 0.50, 0.42)
C_ROOF, C_ROOF_D = (0.95, 0.32, 0.26), (0.72, 0.18, 0.20)
C_BLUE = (0.25, 0.52, 0.96)
C_DOOR = (0.42, 0.25, 0.15)
C_WIN = (0.22, 0.26, 0.42)
FLOWERS = [(1.0, 0.86, 0.16), (1.0, 1.0, 1.0), (1.0, 0.50, 0.72), (0.68, 0.48, 0.98), (1.0, 0.36, 0.30), (0.40, 0.72, 1.0)]
STEM = (0.25, 0.62, 0.20)

# ---------- 幾何收集 ----------
BUCKETS = {}
XF = [Matrix.Identity(4)]


def emit(bn, verts, faces, cols, smooth=True):
    b = BUCKETS.setdefault(bn, dict(v=[], c=[], f=[], s=[]))
    o = len(b["v"])
    M = XF[-1]
    b["v"] += [tuple(M @ Vector(v)) for v in verts]
    b["c"] += cols
    b["f"] += [tuple(o + i for i in f) for f in faces]
    b["s"] += [smooth] * len(faces)


_ICO = {}


def ico(sub):
    if sub not in _ICO:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        bm.verts.index_update()
        _ICO[sub] = ([v.co.copy() for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces])
        bm.free()
    return _ICO[sub]


_CUBE = {}


def cube(sub):
    if sub not in _CUBE:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        if sub:
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=sub, use_grid_fill=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.verts.index_update()
        _CUBE[sub] = ([v.co.copy() for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces])
        bm.free()
    return _CUBE[sub]


def blob(bn, c, s, lo, hi, sub=2, rz=0.0, wob=0.0, flat_bottom=None):
    """圓球團：下暗上亮的頂點色漸層。"""
    vs, fs = ico(sub)
    seed = Vector((R(0, 50), R(0, 50), R(0, 50)))
    cr, sr = math.cos(rz), math.sin(rz)
    out, cols = [], []
    for v in vs:
        d = 1 + wob * noise.noise(v * 1.6 + seed)
        z = v.z
        if flat_bottom is not None and z < flat_bottom:
            z = flat_bottom + (z - flat_bottom) * 0.25
        x, y = v.x * s[0] * d, v.y * s[1] * d
        out.append((c[0] + x * cr - y * sr, c[1] + x * sr + y * cr, c[2] + z * s[2] * d))
        t = sst(-0.9, 0.9, v.z * 0.8 + 0.25 * v.x - 0.2 * v.y)
        cols.append(mix(lo, hi, t))
    emit(bn, out, fs, cols, True)


def rbox(bn, c, size, col, rnd=0.4, rot=(0, 0, 0), sub=1, smooth=True, top=None, bottom=None):
    """圓角方塊；top／bottom 可指定頂面／底面顏色做漸層。"""
    vs, fs = cube(sub)
    M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
    out, cols = [], []
    for v in vs:
        p = v.lerp(v.normalized() * 1.12, rnd) if rnd else v
        out.append(M @ Vector((p.x * size[0] / 2, p.y * size[1] / 2, p.z * size[2] / 2)))
        cc = col
        if top and v.z > 0.5:
            cc = top
        elif bottom and v.z < -0.5:
            cc = bottom
        cols.append(cc)
    emit(bn, out, fs, cols, smooth)


def cyl(bn, p0, p1, r0, r1, n, c0, c1, cap0=False, cap1=True, smooth=True):
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    u = ax.orthogonal().normalized()
    w = ax.cross(u)
    vs, cs, fs = [], [], []
    for p, r, c in ((p0, r0, c0), (p1, r1, c1)):
        for i in range(n):
            a = 2 * math.pi * i / n
            vs.append(p + (u * math.cos(a) + w * math.sin(a)) * r)
            cs.append(c)
    for i in range(n):
        j = (i + 1) % n
        fs.append((i, j, n + j, n + i))
    for cap, base, p, r, c, flip in ((cap0, 0, p0, r0, c0, True), (cap1, n, p1, r1, c1, False)):
        if cap:
            o = len(vs)
            for i in range(n):
                vs.append(vs[base + i].copy())
                cs.append(c)
            vs.append(p.copy())
            cs.append(c)
            for i in range(n):
                j = (i + 1) % n
                fs.append((o + j, o + i, o + n) if flip else (o + i, o + j, o + n))
    emit(bn, vs, fs, cs, smooth)


def prism(bn, pts, th, M, col, col2=None):
    """XZ 平面上的多邊形（從 -Y 看為逆時針），沿 Y 擠出厚度（平面著色）。"""
    n = len(pts)
    vs = [M @ Vector((x, -th / 2, z)) for x, z in pts] + [M @ Vector((x, th / 2, z)) for x, z in pts]
    cs = [col] * n + [col2 or col] * n
    fs = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    for i in range(n):
        j = (i + 1) % n
        fs.append((j, i, n + i, n + j))
    emit(bn, vs, fs, cs, False)


# ---------- 地形 ----------
HILLS = [(12, 57, 6.5, 11.0, True), (-32, 52, 10, 14, False), (40, 40, 6.5, 12, False), (-50, 12, 5.5, 12, False),
         (50, -6, 5.5, 12, False), (-36, -42, 6.5, 13, False), (30, -46, 6.5, 13, False), (-2, -62, 5.5, 14, False),
         (-8, 68, 7, 13, False), (62, 20, 6, 12, False)]
CASTLE = (12.0, 57.0)
PATHS = [[(1.0, 7.0), (3.5, 14.0), (1.5, 22.0), (6.0, 30.0), (9.5, 38.0), (10.5, 46.0), (11.4, 51.5)],
         [(-7.0, 0.5), (-15.0, 1.5), (-25.0, -1.5), (-40.0, 2.0), (-58.0, -1.0)]]


def hgt(x, y):
    r = math.hypot(x, y)
    k = sst(9.0, 22.0, r)
    if k <= 0:
        return 0.0
    h = k * (0.55 * nz(x, y, 0.07, 0.3) + 0.22 * nz(x, y, 0.17, 5.1)) * (1 + r / 40)
    for cx, cy, hh, sg, plateau in HILLS:
        g = math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sg * sg))
        h += k * (min(hh, hh * 1.6 * g) if plateau else hh * g)
    h -= sst(68, 84, r) * 7
    return h


def seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - dx * t, py - ay - dy * t)


def path_dist(x, y):
    return min(seg_dist(x, y, p[i], p[i + 1]) for p in PATHS for i in range(len(p) - 1))


def arena_edge(a):
    return 8.6 + 0.45 * noise.noise(Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, 2.0))) + 0.18 * noise.noise(Vector((math.cos(a) * 5, math.sin(a) * 5, 7.0)))


def dirt_mask(x, y):
    r = math.hypot(x, y)
    a = math.atan2(y, x)
    e = arena_edge(a)
    m = 1 - sst(e - 0.45, e + 0.45, r)
    w = 1.25 + 0.35 * nz(x, y, 0.3, 9.0) + r * 0.012
    m2 = 1 - sst(w - 0.5, w + 0.6, path_dist(x, y))
    return max(m, m2 * 0.95)


SHADOWS = []  # (x, y, 半徑)：樹下把草地頂點色壓暗，讓物件「坐」在地上


def ground_color(x, y):
    r = math.hypot(x, y)
    n1 = nz(x, y, 0.11, 1.0)
    n2 = nz(x, y, 0.45, 4.0)
    g = mix(G_MID, G_LIGHT, sst(-0.35, 0.45, n1))
    g = mix(g, G_DARK, sst(0.1, 0.6, n2) * 0.55)
    g = mix(g, G_FAR, sst(30, 75, r) * 0.55)
    for sx, sy, sr in SHADOWS:
        d = math.hypot(x - sx, y - sy)
        if d < sr:
            g = mul(g, 1 - 0.28 * (1 - sst(sr * 0.35, sr, d)))
    m = dirt_mask(x, y)
    if m > 0:
        d = mix(DIRT, DIRT_D, sst(-0.2, 0.5, nz(x, y, 0.5, 12.0)) * 0.6)
        d = mix(d, DIRT_L, (1 - sst(1.5, 7.0, r)) * 0.55 if r < 9 else 0)
        # 泥地邊緣一圈較深的土色，讓邊界讀得出來
        d = mix(d, DIRT_D, sst(0.15, 0.6, m) * (1 - sst(0.6, 0.98, m)) * 0.8)
        g = mix(g, d, sst(0.0, 0.6, m))
    return g


def build_ground():
    segs = 96
    radii, r, step = [], 0.0, 0.5
    while r < 10.0:
        r += 0.5
        radii.append(r)
    while r < 84:
        step *= 1.085
        r += step
        radii.append(r)
    vs, cs, fs = [(0, 0, 0)], [ground_color(0, 0)], []
    for ri, rr in enumerate(radii):
        for j in range(segs):
            a = 2 * math.pi * (j + 0.5 * (ri % 2)) / segs
            x, y = math.cos(a) * rr, math.sin(a) * rr
            vs.append((x, y, hgt(x, y)))
            cs.append(ground_color(x, y))
    for j in range(segs):
        fs.append((0, 1 + j, 1 + (j + 1) % segs))
    for ri in range(len(radii) - 1):
        a0, b0 = 1 + ri * segs, 1 + (ri + 1) * segs
        for j in range(segs):
            k = (j + 1) % segs
            if ri % 2 == 0:
                fs.append((a0 + k, a0 + j, b0 + j))
                fs.append((b0 + k, a0 + k, b0 + j))
            else:
                fs.append((a0 + k, a0 + j, b0 + k))
                fs.append((b0 + k, a0 + j, b0 + j))
    emit("Meadow_Ground", vs, fs, cs, True)


# ---------- 物件 ----------
def tree(x, y, s, style=0, detail=2):
    """圓滾滾的樹。detail 2=近景（主樹冠 sub3）、1=中景、0=遠景（單球）。"""
    z = hgt(x, y) - 0.1
    lo, hi = LEAF[style % 3]
    lean = (R(-0.12, 0.12) * s, R(-0.12, 0.12) * s)
    th = (1.9 if detail else 1.3) * s
    top = (x + lean[0], y + lean[1], z + th)
    if detail == 0:
        cyl("Meadow_Trees", (x, y, z), top, 0.22 * s, 0.16 * s, 5, TRUNK_D, TRUNK, cap1=False)
        blob("Meadow_Trees", (top[0], top[1], top[2] + 0.9 * s), (1.35 * s, 1.35 * s, 1.25 * s), lo, hi, sub=2, rz=R(0, 6))
        return
    n = 10 if detail == 2 else 7
    cyl("Meadow_Trees", (x, y, z), (x + lean[0] * 0.3, y + lean[1] * 0.3, z + 0.35 * s), 0.46 * s, 0.30 * s, n, TRUNK_D, mix(TRUNK_D, TRUNK, 0.6), cap1=False)
    cyl("Meadow_Trees", (x + lean[0] * 0.3, y + lean[1] * 0.3, z + 0.35 * s), top, 0.30 * s, 0.22 * s, n, mix(TRUNK_D, TRUNK, 0.6), TRUNK, cap1=False)
    cz = top[2] + 1.05 * s
    blob("Meadow_Trees", (top[0], top[1], cz), (1.75 * s, 1.75 * s, 1.5 * s), lo, hi, sub=3, rz=R(0, 6), wob=0.06)
    k = 4 if detail == 2 else 2
    a0 = R(0, 6.28)
    for i in range(k):
        a = a0 + 2 * math.pi * i / k + R(-0.3, 0.3)
        rr = R(1.0, 1.3) * s
        bs = R(0.95, 1.2) * s
        blob("Meadow_Trees", (top[0] + math.cos(a) * rr, top[1] + math.sin(a) * rr, cz - R(0.25, 0.6) * s), (bs, bs, bs * 0.88), lo, mix(lo, hi, 0.9), sub=3 if detail == 2 else 2, rz=R(0, 6), wob=0.05)
    if detail == 2:
        blob("Meadow_Trees", (top[0] + R(-0.3, 0.3) * s, top[1] + R(-0.3, 0.3) * s, cz + 1.0 * s), (1.1 * s, 1.1 * s, 0.9 * s), mix(lo, hi, 0.3), hi, sub=2, rz=R(0, 6))
    SHADOWS.append((x, y, 2.9 * s))


def bush(x, y, s, style=0):
    z = hgt(x, y)
    lo, hi = LEAF[style % 3]
    blob("Meadow_Props", (x, y, z + 0.38 * s), (0.75 * s, 0.75 * s, 0.6 * s), lo, hi, sub=2, rz=R(0, 6), wob=0.08, flat_bottom=-0.5)
    a = R(0, 6.28)
    blob("Meadow_Props", (x + math.cos(a) * 0.55 * s, y + math.sin(a) * 0.55 * s, z + 0.26 * s), (0.5 * s, 0.5 * s, 0.42 * s), lo, mix(lo, hi, 0.85), sub=1, rz=R(0, 6), flat_bottom=-0.5)


def rock(x, y, s, bn="Meadow_Props", sub=2):
    z = hgt(x, y)
    c = random.choice(STONES)
    rbox(bn, (x, y, z + 0.22 * s), (R(0.8, 1.2) * s, R(0.7, 1.0) * s, R(0.6, 0.8) * s), mul(c, 0.86), rnd=0.62, rot=(R(-0.15, 0.15), R(-0.15, 0.15), R(0, 3.14)), sub=sub,
         top=mix(c, MOSS, 0.5 if random.random() < 0.4 else 0.0))


def stone_wall(pts, courses=3):
    """乾砌矮石牆：沿折線一塊一塊疊，上層隨機缺塊。"""
    samples = []
    for i in range(len(pts) - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        L = (b - a).length
        m = max(2, int(L / 0.05))
        for k in range(m):
            p = a.lerp(b, k / m)
            samples.append((p.x, p.y, math.atan2(b.y - a.y, b.x - a.x)))
    total = len(samples) * 0.05
    for c in range(courses):
        d = R(0.0, 0.3) if c else 0.0
        while d < total - 0.15:
            ln = R(0.42, 0.72)
            if c == courses - 1 and (random.random() < 0.22 or d < 0.5 or d > total - 1.0):
                d += ln
                continue
            if c == courses - 2 and (d < 0.2 or d > total - 0.5):
                d += ln
                continue
            x, y, ang = samples[min(len(samples) - 1, int((d + ln / 2) / 0.05))]
            hh = R(0.24, 0.30)
            col = random.choice(STONES)
            col = mul(col, R(0.9, 1.05))
            top = mix(col, MOSS, R(0.4, 0.8)) if (c == courses - 1 and random.random() < 0.45) else mul(col, 1.06)
            off = R(-0.04, 0.04)
            rbox("Meadow_Wall", (x - math.sin(ang) * off, y + math.cos(ang) * off, hgt(x, y) + 0.10 + c * 0.235),
                 (ln * 1.04, R(0.42, 0.55), hh), col, rnd=0.55, rot=(R(-0.06, 0.06), R(-0.05, 0.05), ang + R(-0.08, 0.08)), sub=1,
                 top=top, bottom=mul(col, 0.72))
            d += ln
    # 牆腳散落的小石頭
    for _ in range(int(total / 1.6)):
        x, y, ang = random.choice(samples)
        o = random.choice((-1, 1)) * R(0.45, 0.8)
        rock(x - math.sin(ang) * o, y + math.cos(ang) * o, R(0.25, 0.4), "Meadow_Wall", 1)


def signpost(x, y, rz):
    z = hgt(x, y)
    XF.append(Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(0.06, 4, "Y"))
    cyl("Meadow_Props", (0, 0, -0.2), (0, 0, 2.05), 0.10, 0.085, 8, WOOD_D, WOOD)
    blob("Meadow_Props", (0, 0, 2.05), (0.11, 0.11, 0.09), WOOD, mul(WOOD, 1.15), sub=1)
    arrow = [(-0.55, -0.17), (0.42, -0.17), (0.68, 0.0), (0.42, 0.17), (-0.55, 0.17)]
    bar = lambda bx, bw, bz: [(bx - bw / 2, bz - 0.022), (bx + bw / 2, bz - 0.022), (bx + bw / 2, bz + 0.022), (bx - bw / 2, bz + 0.022)]
    for zz, ang, flip, tilt in ((1.68, 0.25, 1, 0.05), (1.26, -0.4, -1, -0.07)):
        M = Matrix.Translation((0, -0.12, zz)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y")
        pts = arrow if flip == 1 else [(-px, pz) for px, pz in reversed(arrow)]
        prism("Meadow_Props", pts, 0.07, M, mul(WOOD, 1.12), WOOD_D)
        # 假文字：三條深色小橫槓
        for k, (bx, bw) in enumerate(((-0.28, 0.34), (0.12, 0.26), (-0.12, 0.5))):
            prism("Meadow_Props", bar(bx * flip, bw, 0.05 if k < 2 else -0.06), 0.02, M @ Matrix.Translation((0, -0.04, 0)), WOOD_D)
    XF.pop()
    for a in range(5):
        tuft(x + R(-0.3, 0.3), y + R(-0.3, 0.3), 1.2)
    rock(x + 0.35, y + 0.15, 0.35)


def tuft(x, y, s=1.0, bn="Meadow_Flowers"):
    z = hgt(x, y) - 0.02
    vs, cs, fs = [], [], []
    for b in range(5):
        a = R(0, 6.28)
        r0 = R(0.0, 0.07) * s
        bx, by = x + math.cos(a) * r0, y + math.sin(a) * r0
        h = R(0.22, 0.42) * s
        o = len(vs)
        for k in range(3):
            aa = a + k * 2.094
            vs.append((bx + math.cos(aa) * 0.035 * s, by + math.sin(aa) * 0.035 * s, z))
            cs.append(G_DARK)
        vs.append((bx + math.cos(a) * h * 0.45, by + math.sin(a) * h * 0.45, z + h))
        cs.append(G_LIGHT)
        fs += [(o, o + 1, o + 3), (o + 1, o + 2, o + 3), (o + 2, o, o + 3)]
    emit(bn, vs, fs, cs, True)


OCTA_V = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
OCTA_F = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]


def flower(x, y, col, size, h):
    z = hgt(x, y)
    top = Vector((x + R(-0.05, 0.05), y + R(-0.05, 0.05), z + h))
    cyl("Meadow_Flowers", (x, y, z - 0.03), top, 0.014, 0.011, 3, G_DARK, STEM, cap1=False)
    n = Vector((R(-0.45, 0.45), -0.45 + R(-0.35, 0.35), 1)).normalized()
    u = n.orthogonal().normalized()
    w = n.cross(u)
    vs = [top + n * size * 0.22, top - n * size * 0.12]
    cs = [mix(col, (1, 1, 1), 0.35), mul(col, 0.8)]
    for i in range(6):
        a = 2 * math.pi * i / 6
        vs.append(top + (u * math.cos(a) + w * math.sin(a)) * size)
        cs.append(col)
    fs = []
    for i in range(6):
        j = (i + 1) % 6
        fs.append((0, 2 + i, 2 + j))
        fs.append((1, 2 + j, 2 + i))
    emit("Meadow_Flowers", vs, fs, cs, True)
    cc = (1.0, 0.62, 0.12) if col[2] < 0.5 and col[1] > 0.7 else (1.0, 0.85, 0.2)
    c = top + n * size * 0.28
    emit("Meadow_Flowers", [c + Vector(v) * size * 0.36 for v in OCTA_V], OCTA_F, [cc] * 6, True)


def flower_patch(x, y, col=None, n=7, rad=0.6):
    col = col or random.choice(FLOWERS)
    z = hgt(x, y)
    # 花叢底下的小草丘（圓滑矮丘，邊緣埋進地面）
    vs, cs, fs, n8 = [(x, y, z + 0.2)], [mix(G_MID, G_LIGHT, 0.6)], [], 9
    for ring, (rr, zz, cc) in enumerate(((0.6, 0.14, G_MID), (1.05, -0.04, G_DARK))):
        for i in range(n8):
            a = 2 * math.pi * (i + 0.5 * ring) / n8
            px, py = x + math.cos(a) * rad * rr, y + math.sin(a) * rad * rr
            vs.append((px, py, hgt(px, py) + zz))
            cs.append(cc)
    for i in range(n8):
        j = (i + 1) % n8
        fs += [(0, 1 + i, 1 + j), (1 + i, 1 + n8 + i, 1 + j), (1 + j, 1 + n8 + i, 1 + n8 + j)]
    emit("Meadow_Flowers", vs, fs, cs, True)
    for i in range(n):
        a = R(0, 6.28)
        r = rad * math.sqrt(R(0.02, 1.0))
        c = col if random.random() < 0.8 else random.choice(FLOWERS)
        flower(x + math.cos(a) * r, y + math.sin(a) * r, c, R(0.085, 0.13), R(0.26, 0.5))
    for i in range(2):
        tuft(x + R(-rad, rad), y + R(-rad, rad))


def box(bn, lo, hi, col, col_lo=None):
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    s = [hi[i] - lo[i] for i in range(3)]
    rbox(bn, c, s, col, rnd=0.0, sub=0, smooth=False, bottom=col_lo)


def castle(cx, cy, rz, s):
    """玩具感小城堡（遠景低面數）。本地座標：大門朝 -Y。"""
    z0 = hgt(cx, cy) - 0.3
    XF.append(Matrix.Translation((cx, cy, z0)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Scale(s, 4))
    bn = "Meadow_Castle"
    W, T, H = 6.5, 1.1, 4.6
    for sx, sy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        if sx == 0:
            box(bn, (-W, sy * W - T / 2, -3.5), (W, sy * W + T / 2, H), C_WALL, C_WALL_D)
        else:
            box(bn, (sx * W - T / 2, -W, -3.5), (sx * W + T / 2, W, H), C_WALL, C_WALL_D)
        for k in range(-3, 4):
            if sx == 0 and sy == -1 and abs(k) <= 1:
                continue
            p = k * 1.45
            if sx == 0:
                box(bn, (p - 0.4, sy * W - T / 2, H), (p + 0.4, sy * W + T / 2, H + 0.75), C_WALL)
            else:
                box(bn, (sx * W - T / 2, p - 0.4, H), (sx * W + T / 2, p + 0.4, H + 0.75), C_WALL)

    def tower(x, y, r, h, roof_h, roof_col, roof_col_d, n=12, flag=None, base=-3.5):
        cyl(bn, (x, y, base), (x, y, h), r * 1.06, r, n, C_WALL_D, C_WALL, cap1=False)
        cyl(bn, (x, y, h - 0.9), (x, y, h - 0.6), r, r * 1.2, n, C_WALL, C_TRIM, cap1=False)
        cyl(bn, (x, y, h - 0.6), (x, y, h + 0.2), r * 1.2, r * 1.2, n, C_TRIM, mul(C_WALL, 1.02))
        if roof_h > 0:
            cyl(bn, (x, y, h + 0.2), (x, y, h + 0.2 + roof_h * 0.45), r * 1.38, r * 0.62, n, roof_col_d, roof_col, cap0=True, cap1=False)
            cyl(bn, (x, y, h + 0.2 + roof_h * 0.45), (x, y, h + 0.2 + roof_h), r * 0.62, 0.04, n, roof_col, mul(roof_col, 1.1), cap1=False)
            tz = h + 0.2 + roof_h
            blob(bn, (x, y, tz), (0.22, 0.22, 0.22), (1.0, 0.78, 0.15), (1.0, 0.9, 0.3), sub=1)
            if flag:
                cyl(bn, (x, y, tz), (x, y, tz + 1.9), 0.06, 0.05, 4, WOOD_D, WOOD_D)
                prism(bn, [(0, 0), (1.5, 0.38), (0, 0.76)], 0.06, Matrix.Translation((x, y, tz + 1.05)) @ Matrix.Rotation(0.5, 4, "Z"), flag, mul(flag, 0.85))
            rbox(bn, (x, y - r, h - 2.2), (0.55, 0.3, 1.0), C_WIN, rnd=0.35, sub=1)

    for sx in (-1, 1):
        for sy in (-1, 1):
            tower(sx * W, sy * W, 1.85, 6.6 if sy < 0 else 7.6, 3.6, C_ROOF, C_ROOF_D, flag=C_BLUE if (sx, sy) in ((-1, -1), (1, 1)) else None)
    # 主樓
    tower(0, 1.0, 3.0, 9.6, 0, C_WALL, C_WALL_D, n=14, base=0.0)
    for k in range(8):
        a = 2 * math.pi * k / 8
        rbox(bn, (math.cos(a) * 3.3, 1.0 + math.sin(a) * 3.3, 10.15), (0.9, 0.7, 0.8), C_WALL, rnd=0.0, sub=0, smooth=False, rot=(0, 0, a + math.pi / 2))
    tower(0, 1.0, 1.7, 13.0, 4.2, C_ROOF, C_ROOF_D, n=12, flag=(1.0, 0.82, 0.15), base=9.5)
    for k, a in enumerate((-1.2, -1.94, -1.57)):
        rbox(bn, (math.cos(a) * 3.0, 1.0 + math.sin(a) * 3.0, 6.2 if k < 2 else 7.6), (0.6, 0.3, 1.1), C_WIN, rnd=0.35, sub=1, rot=(0, 0, a + math.pi / 2))
    # 門樓
    box(bn, (-2.1, -W - 1.3, -3.5), (2.1, -W + 0.3, 6.2), C_WALL, C_WALL_D)
    for k in (-1, 0, 1):
        box(bn, (k * 1.5 - 0.42, -W - 1.3, 6.2), (k * 1.5 + 0.42, -W + 0.3, 6.95), C_WALL)
    ts = [math.pi * i / 8 for i in range(9)]
    arch = [(-1.15, -0.2), (1.15, -0.2)] + [(math.cos(t) * 1.15, 2.1 + math.sin(t) * 1.15) for t in ts]
    prism(bn, arch, 0.2, Matrix.Translation((0, -W - 1.35, 0)), C_DOOR, C_DOOR)
    arch2 = [(-1.4, -0.2), (1.4, -0.2)] + [(math.cos(t) * 1.4, 2.1 + math.sin(t) * 1.4) for t in ts]
    prism(bn, arch2, 0.1, Matrix.Translation((0, -W - 1.32, 0)), mul(C_WALL_D, 0.85), C_WALL_D)
    rbox(bn, (0, -W - 1.4, 4.9), (0.7, 0.25, 0.9), C_BLUE, rnd=0.4, sub=1)
    XF.pop()


def mountain(x, y, H, Rr):
    bn = "Meadow_Mountains"
    n = 10
    lo, mid, snow = (0.52, 0.66, 0.90), (0.66, 0.76, 0.96), (1.0, 1.0, 1.0)
    cyl(bn, (x, y, -6), (x, y, H * 0.55), Rr, Rr * 0.48, n, lo, mid, cap1=False)
    cyl(bn, (x, y, H * 0.55), (x, y, H * 0.62), Rr * 0.48, Rr * 0.41, n, mid, snow, cap1=False)
    cyl(bn, (x, y, H * 0.62), (x, y, H * 0.9), Rr * 0.41, Rr * 0.16, n, snow, snow, cap1=False)
    cyl(bn, (x, y, H * 0.9), (x, y, H), Rr * 0.16, Rr * 0.02, n, snow, snow, cap1=True)


def cloud(x, y, z, s):
    bn = "Meadow_Clouds"
    lo, hi = (0.80, 0.90, 1.0), (1.0, 1.0, 1.0)
    for dx, rr in ((0, 1.0), (-1.1, 0.72), (1.15, 0.78), (2.0, 0.5), (-1.9, 0.45)):
        blob(bn, (x + dx * s, y + R(-0.2, 0.2) * s, z + rr * s * 0.35), (rr * s, rr * s * 0.8, rr * s * 0.75), lo, hi, sub=2, flat_bottom=-0.35)


# ---------- 佈景 ----------
def free(x, y, rmin, taken, gap):
    if math.hypot(x, y) < rmin or path_dist(x, y) < 2.6:
        return False
    if math.hypot(x - CASTLE[0], y - CASTLE[1]) < 16:
        return False
    return all(math.hypot(x - tx, y - ty) > gap + tr for tx, ty, tr in taken)


taken = []
# 近景大樹（手動擺，框住畫面但不擋城堡）
NEAR = [(-12.5, 7.0, 1.25, 0), (-15.5, -4.0, 1.05, 2), (15.0, 13.5, 1.15, 1), (-8.0, 15.5, 0.95, 1), (17.0, -2.5, 1.2, 0),
        (12.5, -11.0, 1.0, 2), (-11.5, -12.5, 1.1, 1)]
for x, y, s, st in NEAR:
    tree(x, y, s, st, 2)
    taken.append((x, y, 2.6 * s))
# 石牆（右側兩段、左後一段、左前一段）
WALLS = [[(10.3, -1.5), (11.0, 2.0), (12.4, 5.2), (14.6, 7.6)], [(16.0, 8.6), (19.5, 10.0), (23.0, 10.2)], [(-11.5, 11.5), (-14.5, 9.6), (-18.5, 9.0)],
         [(-10.6, -6.0), (-12.5, -8.5), (-13.0, -11.0)]]
for wpts in WALLS:
    for px, py in wpts:
        taken.append((px, py, 1.6))
# 中景樹
count = 0
while count < 11:
    a, r = R(0, 6.28), R(19, 44)
    x, y = math.cos(a) * r, math.sin(a) * r
    s = R(0.95, 1.5)
    if free(x, y, 18, taken, 2.4 * s) and not (-3 < x < 16 and 12 < y < 48):
        tree(x, y, s, random.randrange(3), 1)
        taken.append((x, y, 2.4 * s))
        count += 1
# 遠景小樹（成群種在山丘上）
count = 0
while count < 42:
    a, r = R(0, 6.28), R(34, 70)
    x, y = math.cos(a) * r, math.sin(a) * r
    s = R(1.0, 1.7)
    if free(x, y, 30, taken, 1.2 * s):
        tree(x, y, s, random.randrange(3), 0)
        taken.append((x, y, 1.2 * s))
        count += 1
        for _ in range(random.randrange(0, 3)):
            x2, y2 = x + R(-4, 4), y + R(-4, 4)
            s2 = s * R(0.7, 1.0)
            if free(x2, y2, 30, taken, 1.0 * s2):
                tree(x2, y2, s2, random.randrange(3), 0)
                taken.append((x2, y2, 1.2 * s2))
                count += 1

build_ground()
for wpts in WALLS:
    stone_wall(wpts)
signpost(9.6, -3.4, 0.5)
taken.append((9.6, -3.4, 0.8))
castle(CASTLE[0], CASTLE[1], math.radians(-10), 0.95)

# 灌木與石頭
for x, y, s, st in ((12.8, 8.6, 1.1, 0), (-10.5, 9.2, 1.0, 1), (-13.6, -7.2, 0.9, 2), (10.6, -8.6, 1.0, 0), (19.5, 7.5, 1.2, 1), (-17.0, 3.5, 1.1, 0), (5.5, 13.0, 0.8, 2), (-4.5, 12.5, 0.9, 0)):
    bush(x, y, s, st)
    taken.append((x, y, 0.9 * s))
for _ in range(16):
    a, r = R(0, 6.28), R(11, 40)
    x, y = math.cos(a) * r, math.sin(a) * r
    if free(x, y, 10, taken, 1.0):
        bush(x, y, R(0.7, 1.3), random.randrange(3))
        taken.append((x, y, 1.0))
for x, y, s in ((-9.6, 2.5, 0.9), (-9.3, 3.4, 0.5), (9.2, 9.0, 0.7), (-6.5, -9.6, 0.6), (4.0, -10.2, 0.8), (4.8, -10.5, 0.45)):
    rock(x, y, s)
    taken.append((x, y, 0.6))
for _ in range(22):
    a, r = R(0, 6.28), R(10.5, 45)
    x, y = math.cos(a) * r, math.sin(a) * r
    if free(x, y, 10, taken, 0.8):
        rock(x, y, R(0.4, 1.4))

# 花叢：沿泥地外圈與前景兩側
for i in range(22):
    a = 2 * math.pi * i / 22 + R(-0.1, 0.1)
    r = arena_edge(a) + R(1.0, 2.6)
    x, y = math.cos(a) * r, math.sin(a) * r
    if free(x, y, 9.4, taken, 0.7):
        flower_patch(x, y, n=random.randrange(5, 9), rad=R(0.5, 0.8))
        taken.append((x, y, 0.5))
cnt = 0
while cnt < 16:
    a, r = R(0, 6.28), R(11, 26)
    x, y = math.cos(a) * r, math.sin(a) * r
    if free(x, y, 10, taken, 0.6):
        flower_patch(x, y, n=random.randrange(4, 8), rad=R(0.5, 0.9))
        taken.append((x, y, 0.5))
        cnt += 1
# 散花與草叢
cnt = 0
while cnt < 64:
    a, r = R(0, 6.28), R(9.3, 22)
    x, y = math.cos(a) * r, math.sin(a) * r
    if free(x, y, 9.2, taken, 0.2) and dirt_mask(x, y) < 0.05:
        flower(x, y, random.choice(FLOWERS), R(0.07, 0.11), R(0.18, 0.36))
        cnt += 1
cnt = 0
while cnt < 125:
    a = R(0, 6.28)
    r = arena_edge(a) + (R(0.25, 1.4) if cnt < 95 else R(1.4, 16))
    x, y = math.cos(a) * r, math.sin(a) * r
    if r > 8.35 and (cnt < 95 or free(x, y, 8.35, taken, 0.1)):
        tuft(x, y, R(0.8, 1.3))
        cnt += 1

# 遠山與雲
for m in ((-70, 105, 42, 44), (-22, 122, 56, 50), (38, 116, 38, 42), (88, 92, 30, 36), (-112, 70, 30, 38)):
    mountain(*m)
for c in ((-30, 85, 38, 9), (25, 95, 46, 11), (62, 70, 34, 8), (-70, 50, 36, 9), (-5, 110, 60, 12), (85, 15, 40, 9), (-85, -10, 42, 10)):
    cloud(*c)

# ---------- 建立 Blender 物件 ----------
mat = bpy.data.materials.new("MeadowVertexColor")
mat.use_nodes = True
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
vc = mat.node_tree.nodes.new("ShaderNodeVertexColor")
vc.layer_name = "Col"
mat.node_tree.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.9
bsdf.inputs["Metallic"].default_value = 0.0
mat.use_backface_culling = True  # 預覽即可看出面朝向錯誤

objs, total = [], 0
for name, b in BUCKETS.items():
    me = bpy.data.meshes.new(name)
    me.from_pydata(b["v"], [], b["f"])
    me.polygons.foreach_set("use_smooth", b["s"])
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    flat = []
    for c in b["c"]:
        flat += [*lin(c), 1.0]
    ca.data.foreach_set("color", flat)
    me.color_attributes.active_color = ca
    me.materials.append(mat)
    me.update()
    me.validate()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    objs.append(ob)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    total += tris
    if name != "Meadow_Ground":
        chk = "minR %.3f" % min(math.hypot(v[0], v[1]) for v in b["v"])
    else:
        chk = "max|z| in 8m %.4f" % max(abs(v[2]) for v in b["v"] if math.hypot(v[0], v[1]) < 8.0)
    print(f"BUCKET {name}: verts {len(b['v'])} tris {tris} {chk}")
print("TOTAL TRIS", total)

bpy.ops.object.select_all(action="DESELECT")
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True, export_animations=False, export_yup=True,
                          export_vertex_color="MATERIAL", export_apply=True)
print("GLB bytes", os.path.getsize(OUT_GLB))

# ---------- 預覽 ----------
bpy.ops.object.light_add(type="SUN")
sun = bpy.context.object
sun.data.energy = 3.2
sun.data.color = (1.0, 0.96, 0.88)
sun.data.angle = math.radians(3)
sun.rotation_euler = (math.radians(52), 0, math.radians(-40))
w = bpy.data.worlds.new("Sky")
scene.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.45, 0.70, 1.0, 1)
bg.inputs[1].default_value = 1.1
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "CYCLES"
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 88
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.clip_end = 400
VIEWS = {"player": ((0, -15.5, 4.2), (1.0, 6, 3.4), 30), "top": ((0, -0.5, 46), (0, 0, 0), 35), "reverse": ((3, 17, 5.5), (0, -3, 1.0), 30),
         "threeq": ((19, -19, 11), (0, 1, 0.5), 32), "low": ((-4.5, -10.5, 1.5), (2, 6, 2.2), 28), "castle": ((4, 22, 5), (12, 57, 12), 50)}
for vn, (loc, tgt, lens) in VIEWS.items():
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.render.filepath = os.path.join(PREVIEW_DIR, f"arena_meadow_{vn}.jpg")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("DONE")
