"""Boss 3 霜冠祭司（原創造型）。身高約 2.2 m（冠尖約 2.45 m）、枯瘦；結冰僵硬的層疊祭袍、冰晶王冠、
無口銀面具、細長手指、左手持頂端有冰凍提燈的鐵權杖、袖口與下襬垂冰柱。
用法：blender --background --factory-startup --python build_boss_priest.py -- [model|anim|view|all]
造型依據：art/reference/boss3_frost_priest.jpg。臉朝 -Y、原點在腳底。
"""
import bpy, sys, os, math, random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soul_creature_lib as L

ROOT = os.path.dirname(os.path.dirname(HERE))
NAME = "boss_priest"
MODEL_BLEND = os.path.join(HERE, "source", NAME + "_model.blend")
OUT_BLEND = os.path.join(HERE, "source", NAME + ".blend")
OUT_GLB = os.path.join(ROOT, "public", "models", NAME + ".glb")
PREV = os.path.join(HERE, "preview")
TMP = os.path.join(PREV, "_frames")
BAKED = os.path.join(HERE, "textures", "baked", NAME)
HEIGHT = 2.6
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = argv[0] if argv else "all"
SX, SY = 0.47, -0.33  # 權杖軸位置
GRIP = 1.36


# ================================================================== 材質
def cloth_mat(name, tint, scan="Fabric045", frost=0.5, trim=None, fold=22, hem_ice=0.25):
    """結霜布料。trim=(v0, v1)：puv.v 落在區間內是銀灰刺繡飾帶；hem_ice：靠近下襬結冰的範圍。"""
    m = L.PMat(name)
    fab = m.scan(scan, 2.6)
    uv = m.puv()
    u, v = m.sep(uv)[0], m.sep(uv)[1]
    col = m.mix(1.0, m.ramp(fab["Color"], [(0.15, 0.72), (0.85, 1.04)]), tint, "MULTIPLY")
    col = m.mix(m.ramp(m.noise(2.2, 4), [(0.3, 0.0), (0.7, 0.45)]), col, m.mix(1.0, col, (0.62, 0.68, 0.78), "MULTIPLY"))
    # 垂直皺褶（沿 u 的波紋，受雜訊扭曲）
    wv = m.mix(0.06, uv, m.noise(3.0, 2, out="Color"), "ADD")
    folds = m.wave(fold, vec=wv, dist=2.6, detail=2.0)
    col = m.mix(0.14, col, m.ramp(folds, [(0.0, 0.6), (1.0, 1.08)]), "MULTIPLY")
    rough = m.ramp(fab["Roughness"], [(0.0, 0.8), (1.0, 0.95)])
    n = m.bump(fab["Displacement"], 0.5, 0.004)
    n = m.bump(folds, 0.4, 0.02, normal=n)
    if trim:
        band = m.math("MULTIPLY", m.ramp(v, [(trim[0] - 0.012, 0), (trim[0], 1)]), m.ramp(v, [(trim[1], 1), (trim[1] + 0.012, 0)]))
        pat = m.voronoi(1.0, "F1", vec=m.mapping(uv, scale=(trim[2], trim[3], 1)), rand=0.25)
        dia = m.ramp(pat, [(0.18, 1.0), (0.30, 0.35), (0.42, 0.9)])
        tcol = m.mix(1.0, m.ramp(dia, [(0.3, (0.30, 0.33, 0.38)), (1.0, (0.70, 0.72, 0.72))]), fab["Color"], "MULTIPLY")
        col = m.mix(band, col, tcol)
        n = m.bump(m.math("MULTIPLY", dia, band), 0.6, 0.006, normal=n)
        rough = m.mix(band, rough, 0.55)
        metal = m.math("MULTIPLY", band, m.math("MULTIPLY", dia, 0.55))
    else:
        metal = 0.0
    # 霜與結冰：雜訊＋靠下襬
    fr = m.math("ADD", m.math("MULTIPLY", m.noise(5.0, 5, 0.7), 0.75), m.math("MULTIPLY", m.ramp(v, [(1 - hem_ice * 2.2, 0), (1.0, 1)]), 0.45))
    frost_m = m.ramp(fr, [(0.62 - frost * 0.25, 0), (0.78 - frost * 0.2, 1)])
    col = m.mix(frost_m, col, m.mix(m.noise(18, 2), (0.66, 0.76, 0.88), (0.84, 0.90, 0.96)))
    rough = m.mix(frost_m, rough, m.ramp(m.noise(12, 2), [(0.3, 0.22), (0.7, 0.5)]))
    n = m.bump(m.math("MULTIPLY", frost_m, m.noise(30, 2)), 0.35, 0.004, normal=n)
    return m.finish(col, rough, metal, n, emit=m.mix(frost_m, (0, 0, 0), (0.02, 0.04, 0.06)), emit_strength=1.0)


def ice_mat(name="Ice", glow=0.10):
    m = L.PMat(name)
    ice = m.scan("Ice003", 3.0)
    col = m.mix(0.55, (0.74, 0.88, 0.97), m.hsv(ice["Color"], s=0.6, v=1.3))
    n = m.bump(ice["Displacement"], 0.6, 0.006)
    return m.finish(col, m.ramp(ice["Roughness"], [(0, 0.08), (1, 0.3)]), 0.0, n,
                    emit=m.mix(1.0, col, (glow, glow * 1.6, glow * 2.2), "MULTIPLY"), emit_strength=1.0)


def silver_mat(eye_z):
    m = L.PMat("SilverMask")
    met = m.scan("Metal046B", 3.0)
    tarn = m.ramp(m.noise(7, 4), [(0.35, 0), (0.7, 1)])
    col = m.mix(tarn, (0.80, 0.82, 0.85), (0.42, 0.46, 0.52))
    col = m.mix(0.25, col, met["Color"], "MULTIPLY")
    eyes = None
    for sx in (1, -1):
        ln = m.node("ShaderNodeVectorMath", operation="LENGTH")
        m.set(ln.inputs[0], m.mapping(loc=(-0.04 * sx * 44, 0, -eye_z * 95), scale=(44, 0, 95)))
        e = m.ramp(ln.outputs["Value"], [(0.8, 1), (1.0, 0)])
        eyes = e if eyes is None else m.math("MAXIMUM", eyes, e)
    col = m.mix(eyes, col, (0.005, 0.006, 0.01))
    frost = m.ramp(m.noise(9, 4), [(0.55, 0), (0.7, 0.8)])
    col = m.mix(frost, col, (0.86, 0.92, 0.98))
    rough = m.mix(frost, m.ramp(tarn, [(0, 0.22), (1, 0.45)]), 0.5)
    rough = m.mix(eyes, rough, 0.9)
    metal = m.math("MULTIPLY", m.math("SUBTRACT", 1.0, eyes), m.math("SUBTRACT", 1.0, m.math("MULTIPLY", frost, 0.7)))
    n = m.bump(met["Displacement"], 0.3, 0.003)
    n = m.bump(m.math("SUBTRACT", 1.0, eyes), 1.0, 0.01, normal=n)
    return m.finish(col, rough, metal, n)


def iron_mat():
    m = L.PMat("Iron")
    met = m.scan("Metal013", 2.5, maps=("Color", "Roughness", "Displacement"))
    col = m.mix(0.7, (0.10, 0.105, 0.115), m.hsv(met["Color"], s=0.35, v=0.45))
    frost = m.ramp(m.math("ADD", m.noise(8, 4), m.math("MULTIPLY", m.sep(m.geom("Normal"))[2], 0.12)), [(0.55, 0), (0.68, 0.9)])
    col = m.mix(frost, col, (0.82, 0.90, 0.97))
    rough = m.mix(frost, m.ramp(met["Roughness"], [(0, 0.4), (1, 0.7)]), 0.4)
    metal = m.math("SUBTRACT", 1.0, frost)
    return m.finish(col, rough, metal, m.bump(met["Displacement"], 0.7, 0.006))


def glow_mat():
    m = L.PMat("LanternGlow")
    ice = m.scan("Ice003", 9.0, maps=("Color",))
    pat = m.ramp(ice["Color"], [(0.15, 0.25), (0.8, 1.0)])
    col = m.mix(1.0, (0.60, 0.85, 1.0), pat, "MULTIPLY")
    return m.finish(m.mix(0.5, col, (0.75, 0.9, 1.0)), 0.2, 0.0, None, emit=col, emit_strength=6.0)


def skin_mat():
    m = L.PMat("FrostSkin")
    col = m.mix(m.noise(14, 3), (0.36, 0.41, 0.48), (0.56, 0.62, 0.70))
    return m.finish(col, 0.55, 0.0, m.bump(m.noise(40, 2), 0.2, 0.002))


def leather_mat():
    m = L.PMat("FrostLeather")
    le = m.scan("Leather028", 3.0)
    col = m.hsv(le["Color"], s=0.3, v=0.5)
    frost = m.ramp(m.noise(6, 4), [(0.45, 0), (0.62, 0.9)])
    col = m.mix(frost, col, (0.80, 0.87, 0.94))
    return m.finish(col, m.mix(frost, 0.7, 0.4), 0.0, m.bump(le["Displacement"], 0.6, 0.004))


# ================================================================== 建模
PROFILE = [(1.86, 0.085, 0.08), (1.80, 0.20, 0.115), (1.62, 0.20, 0.135), (1.32, 0.165, 0.125), (1.06, 0.215, 0.165), (0.60, 0.30, 0.255), (0.10, 0.40, 0.36)]


def robe_r(z):
    for (z0, a0, b0), (z1, a1, b1) in zip(PROFILE, PROFILE[1:]):
        if z >= z1:
            t = (z0 - z) / (z0 - z1)
            t = max(0.0, min(1.0, t))
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return PROFILE[-1][1], PROFILE[-1][2]


def body_w(co, t=None):
    """祭袍類零件的權重：上身沿脊椎，下襬分給前後裙骨。"""
    z = co.z
    w = {}
    sk = L._sst((1.12 - z) / 0.30)
    back = L._sst(co.y / 0.24 + 0.5)
    up = 1 - sk
    c = L._sst((z - 1.50) / 0.16)
    s = L._sst((z - 1.28) / 0.16) * (1 - c)
    h = max(0.0, 1 - c - s)
    w["Chest"], w["Spine"], w["Hips"] = up * c, up * s, up * h
    w["SkirtB"], w["SkirtF"] = sk * back, sk * (1 - back)
    return w


def build_model():
    L.reset()
    rnd = random.Random(11)
    M_robe = cloth_mat("UnderRobe", (0.56, 0.68, 0.84), "Fabric045", frost=0.45, trim=(0.90, 0.955, 60, 400), fold=11)
    M_mantle = cloth_mat("Mantle", (0.72, 0.78, 0.86), "Fabric036", frost=0.7, trim=(0.80, 0.92, 50, 80), fold=7, hem_ice=0.3)
    M_stole = cloth_mat("Stole", (0.72, 0.75, 0.80), "Fabric036", frost=0.35, trim=(0.02, 0.98, 26, 240), fold=1)
    M_ice = ice_mat()
    M_silver = silver_mat(2.006)
    M_iron = iron_mat()
    M_glow = glow_mat()
    M_skin = skin_mat()
    M_leather = leather_mat()
    D = []

    def add(o, sharp=None):
        if sharp:
            L.hard(o, sharp)
        D.append(o)
        return o

    def icicle(p, length, r, bones, lean=(0, 0)):
        p = Vector(p)
        tip = p + Vector((lean[0], lean[1], -length))
        o = L.loft("Icicle", [p + Vector((0, 0, r * 0.6)), p.lerp(tip, 0.45), tip], [r, r * 0.55, r * 0.05], segs=4, sub=1, caps=("flat", "point"), mat=M_ice, bones=None)
        w = bones(p, 0) if callable(bones) else {bones: 1.0}
        L.assign(o, lambda co, t: w)
        D.append(o)

    # --- 內袍（長袍到腳踝，垂直皺褶、下襬參差）
    def fold_shape(a, t):
        amp = 0.012 + 0.085 * t ** 2.2
        return 1 + amp * (0.5 * math.sin(7 * a + 1.3) + 0.3 * math.sin(13 * a + 0.4) + 0.2 * math.sin(4 * a + 2.0))

    robe = L.loft("Robe", [(0, 0, z) for z, _, _ in PROFILE], [(a, b) for _, a, b in PROFILE], segs=56, sub=5, caps=("round", "open"),
                  shape=fold_shape, bones=body_w, mat=M_robe)
    hem = robe.data.vertices[-57:-1] if len(robe.data.vertices) % 56 else robe.data.vertices[-56:]
    for i, v in enumerate(hem):
        v.co.z += rnd.choice([0.0, 0.02, 0.05, 0.11, 0.03]) + 0.03 * math.sin(i * 0.9)
        if i % 3 == 0:
            icicle(v.co, rnd.uniform(0.05, 0.13), 0.014, body_w)
    add(robe)

    # --- 外披（前開的祭披：背後長、兩側短、前襟垂片），下襬掛冰柱
    rows, cols = 18, 44
    grid = []
    for i in range(rows + 1):
        v = i / rows
        row = []
        for j in range(cols + 1):
            a = math.radians(26 + (360 - 52) * j / cols)
            fb = max(0.0, -math.cos(a)) ** 1.4
            ff = max(0.0, math.cos(a)) ** 2
            zh = 1.30 - 0.58 * fb - 0.30 * ff + 0.035 * math.sin(j * 1.7) + (0.05 if j % 4 == 0 else 0)
            z = 1.875 + (zh - 1.875) * v
            rx, ry = robe_r(z)
            sh = math.exp(-((z - 1.74) / 0.16) ** 2)  # 肩部外擴蓋住上臂
            rx = rx + 0.035 + 0.05 * sh + 0.10 * v * abs(math.sin(a)) ** 2
            ry = ry + 0.035 + 0.02 * v + 0.05 * v * fb
            rip = 1 + (0.01 + 0.05 * v ** 2) * (math.sin(9 * a + 0.5) * 0.6 + math.sin(17 * a) * 0.4)
            row.append(Vector((math.sin(a) * rx * rip, -math.cos(a) * ry * rip, z)))
        grid.append(row)

    def mantle_w(co, uvt):
        w = body_w(co)
        # 肩部分一些給上臂，讓抬手時披肩跟著動
        s = 1 if co.x > 0 else -1
        k = L._sst((abs(co.x) - 0.17) / 0.10) * L._sst((co.z - 1.45) / 0.2) * 0.65
        w = {b: x * (1 - k) for b, x in w.items()}
        w["UpperArm.L" if s > 0 else "UpperArm.R"] = k
        return w

    mantle = L.sheet("Mantle", grid, thick=0.014, bones=mantle_w, mat=M_mantle)
    add(mantle)
    for j in range(0, cols + 1, 1):
        p = grid[rows][j]
        if rnd.random() < 0.8:
            icicle(p + Vector((0, 0, 0.005)), rnd.uniform(0.06, 0.24) * (1.3 if j % 4 == 0 else 1), rnd.uniform(0.012, 0.02), lambda co, t: mantle_w(co, None))

    # --- 領圍與頭巾
    add(L.ellipsoid("Collar", (0, 0.0, 1.875), (0.15, 0.135, 0.055), bones="Chest", mat=M_mantle, segs=20, rings=8))
    add(L.loft("NeckWrap", [(0, 0, 1.86), (0, -0.005, 1.95)], [0.06, 0.055], segs=10, sub=2, caps=("open", "open"), bones=[("Chest", 0), ("Neck", 0.3)], blend=0.4, mat=M_robe))
    add(L.ellipsoid("Hood", (0, 0.012, 2.02), (0.112, 0.125, 0.135), bones="Head", mat=M_mantle, segs=20, rings=12))
    hood_back = [[Vector((math.sin(a) * (0.115 + 0.03 * v), 0.03 + math.cos(a) * (0.12 + 0.03 * v), 2.06 - 0.24 * v)) for a in [math.radians(x) for x in range(-100, 101, 20)]] for v in [0, 0.33, 0.66, 1.0]]
    add(L.sheet("HoodDrape", hood_back, thick=0.012, bones=[("Head", 0), ("Neck", 0.5), ("Chest", 0.9)], blend=0.3, mat=M_mantle))

    # --- 無口銀面具（鼻脊、眉弓）與冰晶王冠
    add(L.ellipsoid("Mask", (0, -0.075, 1.99), (0.083, 0.062, 0.125), rot=(-4, 0, 0), bones="Head", mat=M_silver, segs=20, rings=14))
    add(L.loft("Nose", [(0, -0.128, 2.04), (0, -0.139, 1.99), (0, -0.136, 1.945)], [(0.012, 0.01), (0.013, 0.012), (0.017, 0.008)], segs=6, sub=2, bones="Head", mat=M_silver))
    band = [[Vector((math.sin(a) * (0.117 + 0.006 * k), 0.012 - math.cos(a) * (0.13 + 0.006 * k), 2.085 + 0.055 * k)) for a in [2 * math.pi * j / 20 for j in range(20)]] for k in (0, 1)]
    add(L.sheet("CrownBand", band, thick=0.014, wrap=True, bones="Head", mat=M_silver), sharp=40)
    n_sp = 15
    for k in range(n_sp):
        a = 2 * math.pi * k / n_sp
        front = max(0.0, math.cos(a))
        h = 0.13 + 0.10 * rnd.random() + 0.17 * front ** 3
        base = Vector((math.sin(a) * 0.118, 0.012 - math.cos(a) * 0.131, 2.125))
        out = Vector((math.sin(a), -math.cos(a), 0))
        tip = base + out * (0.035 + 0.03 * rnd.random()) + Vector((0, 0, h))
        add(L.loft("CrownSpike", [base - Vector((0, 0, 0.03)), base.lerp(tip, 0.35) + out * 0.012, tip], [0.024, 0.02, 0.002], segs=5, sub=1, caps=("flat", "point"), bones="Head", mat=M_ice), sharp=30)
        if k % 2 == 0:
            b2 = base + Vector((math.cos(a) * 0.022, math.sin(a) * 0.022, 0))
            add(L.loft("CrownSpikeS", [b2 - Vector((0, 0, 0.02)), b2 + out * 0.05 + Vector((0, 0, h * 0.45))], [0.014, 0.002], segs=4, sub=1, caps=("flat", "point"), bones="Head", mat=M_ice), sharp=30)
    for k in range(7):  # 面具兩側與下緣的垂冰
        a = math.radians(-75 + 25 * k)
        icicle((math.sin(a) * 0.105, 0.0 - math.cos(a) * 0.105, 1.92 - 0.02 * abs(math.sin(a))), rnd.uniform(0.03, 0.07), 0.008, "Head")

    # --- 前垂聖帶（刺繡）與腰帶
    for s in (1, -1):
        g = []
        for i in range(15):
            z = 1.85 - (1.85 - 0.52) * i / 14
            rx, ry = robe_r(z)
            row = []
            for k in range(3):
                x = s * (0.045 + 0.036 * k)
                y = -ry * math.sqrt(max(0.05, 1 - (x / (rx + 0.02)) ** 2)) - 0.035 - 0.012 * (i / 14)
                if z > 1.78:
                    y = -0.07 - (1.86 - z) * 0.9
                row.append(Vector((x, y, z)))
            g.append(row)
        add(L.sheet("Stole", g, thick=0.012, bones=lambda co, uvt: body_w(co), mat=M_stole))
        for k in range(3):
            icicle(g[-1][k], rnd.uniform(0.05, 0.12), 0.011, body_w)
    belt = [[Vector((math.sin(a) * (robe_r(z)[0] + 0.03), -math.cos(a) * (robe_r(z)[1] + 0.03), z)) for a in [2 * math.pi * j / 28 for j in range(28)]] for z in (1.335, 1.27)]
    add(L.sheet("Belt", belt, thick=0.016, wrap=True, bones=lambda co, uvt: body_w(co), mat=M_leather))
    for x, ln in ((-0.10, 0.34), (-0.135, 0.22), (0.11, 0.28)):
        y = -robe_r(1.26)[1] - 0.045
        add(L.loft("Cord", [(x, y, 1.275), (x * 1.05, y - 0.02, 1.27 - ln * 0.5), (x * 1.1, y - 0.035, 1.27 - ln)], [0.009, 0.008, 0.008], segs=5, sub=2, bones=body_w, mat=M_leather))
        add(L.loft("Pendant", [(x * 1.1, y - 0.035, 1.275 - ln), (x * 1.1, y - 0.037, 1.25 - ln), (x * 1.1, y - 0.04, 1.27 - ln - 0.11)], [0.004, 0.022, 0.003], segs=5, sub=1, caps=("point", "point"), bones=body_w, mat=M_ice), sharp=30)

    # --- 手臂、寬袖、手
    def sleeve(sx, pts, radii, cuff_bone):
        s = L.loft("Sleeve" + sx, pts, radii, segs=18, sub=5, caps=("round", "open"),
                   bones=[("Chest", 0), ("UpperArm" + sx, 0.10), ("ForeArm" + sx, 0.55)], blend=0.14, mat=M_mantle,
                   shape=lambda a, t: 1 + 0.05 * t * math.sin(5 * a + 1))
        cuff = s.data.vertices[-18:]
        for i, v in enumerate(cuff):
            if v.co.z < min(c.co.z for c in cuff) + 0.12 and i % 2 == 0:
                icicle(v.co, rnd.uniform(0.06, 0.20), 0.013, cuff_bone)
        add(s)

    # 左臂：前臂前伸握杖
    Ls, Le, Lw = Vector((0.205, 0, 1.80)), Vector((0.33, 0.03, 1.49)), Vector((0.44, -0.20, 1.37))
    sleeve(".L", [Ls, Ls.lerp(Le, 0.5) + Vector((0.01, 0.01, 0)), Le, Le.lerp(Lw, 0.5) + Vector((0, 0, -0.03)), Lw + Vector((-0.005, 0.03, -0.045))],
           [0.085, 0.085, 0.09, (0.10, 0.12), (0.11, 0.16)], "ForeArm.L")
    add(L.loft("Wrist.L", [Le.lerp(Lw, 0.5), Lw, Lw + Vector((0.012, -0.05, 0))], [0.03, 0.026, 0.03], segs=8, sub=2, bones=[("ForeArm.L", 0), ("Hand.L", 0.7)], blend=0.3, mat=M_skin))
    add(L.ellipsoid("Palm.L", (0.455, -0.285, GRIP), (0.03, 0.05, 0.05), rot=(0, 0, -20), bones="Hand.L", mat=M_skin, segs=10, rings=6))
    for k in range(4):
        z = GRIP - 0.036 + 0.024 * k
        pts = [Vector((SX + 0.034 * math.cos(math.radians(a)), SY + 0.034 * math.sin(math.radians(a)), z + 0.004 * i)) for i, a in enumerate((110, 40, -30, -100, -165))]
        add(L.loft(f"FingerL{k}", pts, [0.0095, 0.009, 0.0085, 0.007, 0.003], segs=6, sub=2, caps=("round", "point"), bones=[("Hand.L", 0), ("Fingers.L", 0.2)], blend=0.2, mat=M_skin))
    pts = [Vector((SX + 0.034 * math.cos(math.radians(a)), SY + 0.034 * math.sin(math.radians(a)), GRIP + 0.062 + 0.006 * i)) for i, a in enumerate((130, 190, 250))]
    add(L.loft("ThumbL", pts, [0.013, 0.011, 0.004], segs=6, sub=2, caps=("round", "point"), bones="Hand.L", mat=M_skin))
    # 右臂：垂下，細長手指張開
    Rs, Re, Rw = Vector((-0.205, 0, 1.80)), Vector((-0.31, 0.03, 1.47)), Vector((-0.365, -0.05, 1.16))
    sleeve(".R", [Rs, Rs.lerp(Re, 0.5) + Vector((-0.01, 0.01, 0)), Re, Re.lerp(Rw, 0.55), Rw + Vector((0, 0.01, 0.03))],
           [0.085, 0.085, 0.09, (0.11, 0.12), (0.13, 0.15)], "ForeArm.R")
    add(L.loft("Wrist.R", [Re.lerp(Rw, 0.6), Rw, Rw + Vector((-0.004, -0.012, -0.06))], [0.03, 0.025, 0.03], segs=8, sub=2, bones=[("ForeArm.R", 0), ("Hand.R", 0.7)], blend=0.3, mat=M_skin))
    palm = Rw + Vector((-0.006, -0.02, -0.095))
    add(L.ellipsoid("Palm.R", palm, (0.045, 0.02, 0.055), rot=(8, 0, 0), bones="Hand.R", mat=M_skin, segs=10, rings=6))
    for k, dx in enumerate((-0.036, -0.012, 0.012, 0.035)):
        b = palm + Vector((dx, -0.006, -0.045))
        ln = (0.085, 0.10, 0.095, 0.075)[k]
        mid = b + Vector((dx * 0.35, -0.02, -ln))
        tip = mid + Vector((dx * 0.2, -0.045, -ln * 0.85))
        add(L.loft(f"FingerR{k}", [b, mid, mid.lerp(tip, 0.55) + Vector((0, -0.008, 0)), tip], [0.0125, 0.011, 0.009, 0.003], segs=6, sub=2, caps=("round", "point"),
                   bones=[("Hand.R", 0), ("Fingers.R", 0.25)], blend=0.2, mat=M_skin))
    tb = palm + Vector((0.045, -0.012, 0.01))
    add(L.loft("ThumbR", [tb, tb + Vector((0.03, -0.03, -0.05)), tb + Vector((0.035, -0.055, -0.11))], [0.013, 0.011, 0.003], segs=6, sub=2, caps=("round", "point"), bones="Hand.R", mat=M_skin))

    # --- 靴
    for s, sx in ((1, ".L"), (-1, ".R")):
        x = 0.115 * s
        add(L.loft("Boot" + sx, [(x, 0.03, 0.27), (x, 0.03, 0.15), (x, -0.02, 0.07), (x * 1.08, -0.13, 0.05), (x * 1.12, -0.23, 0.04)],
                   [0.055, 0.055, (0.058, 0.056), (0.058, 0.045), (0.05, 0.032)], segs=12, sub=4, bones=[("Shin" + sx, 0), ("Foot" + sx, 0.3)], blend=0.12, mat=M_leather))

    # --- 鐵權杖與冰凍提燈
    def st(o, sharp=None):
        L.assign(o, "Staff")
        return add(o, sharp)

    st(L.loft("Shaft", [(SX, SY, 0.10), (SX, SY, 0.9), (SX, SY, 1.6), (SX, SY, 2.14)], [0.021, 0.019, 0.019, 0.022], segs=8, sub=2, caps=("flat", "flat"), mat=M_iron))
    st(L.loft("Butt", [(SX, SY, 0.16), (SX, SY, 0.10), (SX, SY, 0.0)], [0.022, 0.034, 0.002], segs=6, sub=1, caps=("flat", "point"), mat=M_iron), 30)
    for z, r in ((0.20, 0.032), (1.22, 0.03), (1.52, 0.03), (1.95, 0.034), (2.06, 0.04)):
        st(L.ellipsoid("Collar", (SX, SY, z), (r, r, 0.018), mat=M_iron, segs=8, rings=5))
    st(L.loft("LBase", [(SX, SY, 2.12), (SX, SY, 2.155), (SX, SY, 2.17)], [0.035, 0.098, 0.098], segs=6, sub=1, caps=("flat", "flat"), mat=M_iron), 30)
    st(L.loft("LPane", [(SX, SY, 2.17), (SX, SY, 2.43)], [0.078, 0.078], segs=6, sub=1, caps=("open", "open"), mat=M_glow), 30)
    st(L.loft("LTop", [(SX, SY, 2.43), (SX, SY, 2.45), (SX, SY, 2.56), (SX, SY, 2.585)], [0.10, 0.105, 0.03, 0.022], segs=6, sub=1, caps=("flat", "flat"), mat=M_iron), 30)
    st(L.ellipsoid("LFinial", (SX, SY, 2.615), (0.028, 0.028, 0.034), mat=M_iron, segs=8, rings=6))
    st(L.loft("LSpike", [(SX, SY, 2.64), (SX, SY, 2.72)], [0.012, 0.001], segs=4, sub=1, caps=("flat", "point"), mat=M_iron), 30)
    for k in range(6):
        a = math.radians(60 * k)
        px, py = SX + 0.086 * math.cos(a), SY + 0.086 * math.sin(a)
        st(L.box("LPost", (px, py, 2.30), (0.016, 0.016, 0.27), rot=(0, 0, 60 * k), mat=M_iron))
        a2 = math.radians(60 * k + 30)
        st(L.box("LBar", (SX + 0.074 * math.cos(a2), SY + 0.074 * math.sin(a2), 2.30), (0.008, 0.086, 0.01), rot=(0, 0, 60 * k + 30), mat=M_iron))
        icicle((px, py, 2.155), rnd.uniform(0.05, 0.14), 0.011, "Staff")
        icicle((SX + 0.10 * math.cos(a2), SY + 0.10 * math.sin(a2), 2.44), rnd.uniform(0.03, 0.08), 0.008, "Staff")
    for z in (1.60, 1.25, 0.9, 0.5):
        icicle((SX + 0.02, SY, z), rnd.uniform(0.04, 0.09), 0.008, "Staff")

    # --- 骨架
    B = [("Root", (0, 0, 0), (0, 0.3, 0), None),
         ("Hips", (0, 0, 1.16), (0, 0, 1.32), "Root"),
         ("Spine", (0, 0, 1.32), (0, 0, 1.54), "Hips"),
         ("Chest", (0, 0, 1.54), (0, 0, 1.84), "Spine"),
         ("Neck", (0, 0, 1.84), (0, -0.005, 1.95), "Chest"),
         ("Head", (0, -0.005, 1.95), (0, -0.005, 2.14), "Neck"),
         ("SkirtF", (0, -0.14, 1.10), (0, -0.26, 0.20), "Hips"),
         ("SkirtB", (0, 0.14, 1.10), (0, 0.28, 0.20), "Hips"),
         ("UpperArm.L", Ls, Le, "Chest"), ("ForeArm.L", Le, Lw, "UpperArm.L"),
         ("Hand.L", Lw, (0.46, -0.29, GRIP), "ForeArm.L"), ("Fingers.L", (0.46, -0.29, GRIP), (0.47, -0.37, GRIP), "Hand.L"),
         ("Staff", (SX, SY, GRIP), (SX, SY, 2.2), "Hand.L"),
         ("UpperArm.R", Rs, Re, "Chest"), ("ForeArm.R", Re, Rw, "UpperArm.R"),
         ("Hand.R", Rw, Rw + Vector((-0.006, -0.02, -0.13)), "ForeArm.R"), ("Fingers.R", Rw + Vector((-0.006, -0.02, -0.13)), Rw + Vector((-0.006, -0.06, -0.30)), "Hand.R")]
    for s, sx in ((1, ".L"), (-1, ".R")):
        x = 0.115 * s
        B += [("Thigh" + sx, (x * 0.9, 0, 1.14), (x, -0.03, 0.64), "Hips"), ("Shin" + sx, (x, -0.03, 0.64), (x, 0.03, 0.12), "Thigh" + sx),
              ("Foot" + sx, (x, 0.03, 0.12), (x * 1.1, -0.22, 0.04), "Shin" + sx)]
    arm = L.make_armature("Priest", B)
    mesh = L.assemble("PriestMesh", arm, [], D, BAKED, size=1024, emit_strength=3.0, emit_size=512, ao_dist=0.35)
    bpy.ops.wm.save_as_mainfile(filepath=MODEL_BLEND)


# ================================================================== 動作
def define_actions(A, sym):
    """9 個手刻動作。'Staff:plant'=1 時權杖自動拄地；Telegraph 首尾相同可循環；Attack／Attack2 第 1 格 = Telegraph 姿勢。"""
    for sx in (".L", ".R"):
        A.add_leg("Thigh" + sx, "Shin" + sx, ["Foot" + sx], "Foot" + sx + ":ik")
    A.add_plant("Staff", "Staff:plant")

    def P(*ds):
        out = {}
        for d in ds:
            out.update(d)
        return out

    S = {}
    LAG = {"Head": 2, "Neck": 1, "SkirtF": 3, "SkirtB": 3, "Fingers.R": 3, "Hand.R": 2, "ForeArm.R": 1}

    # ---------------- Idle：僵直佇立、緩慢呼吸、右手指緩緩收張（循環）
    i1 = {"Hips:loc": (0, 0, -0.012), "Spine": (1.5, 0, 0), "Chest": (-3, 0, 1.5), "Neck": (2, 0, 0), "Head": (3, 3, 6),
          "UpperArm.R": (2, 3, 0), "ForeArm.R": (-6, 0, 0), "Fingers.R": (16, 0, 0), "Hand.R": (6, 0, 0), "SkirtF": (1.5, 0, 0), "SkirtB": (-1, 0, 0),
          "UpperArm.L": (-2, 0, 0)}
    i2 = {"Hips:loc": (0, 0, 0.004), "Chest": (1, 0, -1), "Head": (-2, -2, -5), "Fingers.R": (-8, 0, 0), "UpperArm.R": (-1, -1, 0), "SkirtF": (-1, 0, 0)}
    A.action("Idle", [(1, S), (34, i1), (70, i2), (100, S)], lag=LAG)

    # ---------------- Enter：冰封低首→碎冰抽動→緩緩挺直→舉杖頓地
    bow = {"Hips:loc": (0, 0.02, -0.10), "Spine": (22, 0, 0), "Chest": (24, 0, 0), "Neck": (18, 0, 0), "Head": (24, 0, 0),
           "UpperArm.R": (-42, -24, 0), "ForeArm.R": (-96, 0, 0), "Hand.R": (-10, 0, 0), "Fingers.R": (30, 0, 0), "SkirtF": (-4, 0, 0)}
    twitch = P(bow, {"Head": (20, 4, 9), "Chest": (22, 0, 3), "Fingers.R": (10, 0, 0)})
    half = {"Hips:loc": (0, 0.01, -0.04), "Spine": (6, 0, 0), "Chest": (4, 0, 0), "Neck": (10, 0, 0), "Head": (14, 0, 0),
            "UpperArm.R": (-14, -6, 0), "ForeArm.R": (-40, 0, 0), "Fingers.R": (12, 0, 0)}
    lift = {"Hips:loc": (0, 0.02, 0.02), "Spine": (-4, 0, 0), "Chest": (-7, 0, 0), "Head": (-6, 0, 0), "UpperArm.L": (-38, -8, 0), "ForeArm.L": (-14, 0, 0),
            "UpperArm.R": (4, 22, 0), "ForeArm.R": (-12, 0, 0), "Fingers.R": (-18, 0, 0)}
    slam = {"Hips:loc": (0, 0, -0.07), "Spine": (5, 0, 0), "Chest": (6, 0, 0), "Head": (-10, 0, 0), "UpperArm.L": (6, 0, 0), "ForeArm.L": (4, 0, 0),
            "UpperArm.R": (6, 34, 0), "ForeArm.R": (-10, 0, 0), "Fingers.R": (-26, 0, 0), "Hand.R": (-14, 0, 0), "SkirtF": (5, 0, 0), "SkirtB": (-5, 0, 0)}
    A.action("Enter", [(1, bow), (20, bow), (24, twitch), (28, bow), (33, twitch), (38, bow), (66, half), (78, lift), (81, lift, "L"), (84, slam), (92, P(slam, {"Hips:loc": (0, 0, -0.03)})), (110, S)], lag=LAG)

    # ---------------- Telegraph：高舉提燈、右手前探（可循環保持）
    TG = {"Hips:loc": (0, 0.05, 0.0), "Spine": (-6, 0, -6), "Chest": (-9, 0, -8), "Neck": (4, 0, 4), "Head": (8, 0, 8),
          "UpperArm.L": (-100, -22, 0), "ForeArm.L": (-28, 0, 0), "Staff": (142, 0, 0), "Staff:plant": 0.0,
          "UpperArm.R": (-58, 8, 0), "ForeArm.R": (-46, 0, 0), "Hand.R": (-28, 0, 0), "Fingers.R": (-26, 0, 0),
          "SkirtF": (5, 0, 0), "SkirtB": (5, 0, 0)}
    TG2 = P(TG, {"Hips:loc": (0, 0.06, 0.015), "Chest": (-11, 0, -9), "UpperArm.L": (-106, -24, 0), "Staff": (150, 0, 0), "Fingers.R": (-10, 0, 0), "Head": (6, 0, 9)})
    A.action("Telegraph", [(1, TG), (10, TG2), (20, TG), (30, TG2), (40, TG)], lag={"Fingers.R": 2})

    # ---------------- Attack：提燈重砸地面
    ant = P(TG2, {"Chest": (-15, 0, -8), "Spine": (-9, 0, -6), "Staff": (128, 0, 0), "UpperArm.L": (-112, -24, 0), "Hips:loc": (0, 0.09, 0.02)})
    hitp = {"Hips:loc": (0, -0.22, -0.16), "Spine": (18, 0, 4), "Chest": (22, 0, 6), "Neck": (-8, 0, 0), "Head": (-16, 0, -4),
            "UpperArm.L": (-55, -8, 0), "ForeArm.L": (15, 0, 0), "Staff": (146, 0, 0), "Staff:plant": 0.0,
            "UpperArm.R": (36, 16, 0), "ForeArm.R": (-20, 0, 0), "Fingers.R": (20, 0, 0), "SkirtF": (-10, 0, 0), "SkirtB": (-14, 0, 0), "Foot.L:ik": (0, -0.22, 0)}
    reb = P(hitp, {"Staff": (138, 0, 0), "Hips:loc": (0, -0.22, -0.13), "Chest": (19, 0, 6)})
    hold = P(hitp, {"Staff": (145, 0, 0), "Hips:loc": (0, -0.21, -0.15), "SkirtF": (-4, 0, 0), "SkirtB": (-6, 0, 0)})
    A.action("Attack", [(1, TG), (7, P(ant, {"Foot.L:ik": (0, -0.08, 0.08)}), "L"), (12, hitp), (15, reb), (18, hold), (28, hold),
                        (42, {"Hips:loc": (0, -0.08, -0.04), "Spine": (6, 0, 0), "Chest": (4, 0, 0), "UpperArm.L": (-30, -6, 0), "Staff:plant": 0.6, "Foot.L:ik": (0, -0.1, 0.06)}), (54, S)], lag=LAG)

    # ---------------- Attack2：右手橫掃冰霜＋權杖頓地
    wind = P(TG, {"Spine": (-4, 0, -18), "Chest": (-6, 0, -24), "Head": (4, 0, 26), "UpperArm.R": (-40, 62, 0), "ForeArm.R": (-70, 0, 0), "Fingers.R": (24, 0, 0),
                  "Hips:loc": (0, 0.08, -0.02)})
    sweep = {"Hips:loc": (0, -0.14, -0.10), "Spine": (8, 0, 16), "Chest": (10, 0, 26), "Neck": (0, 0, -12), "Head": (-6, 0, -18),
             "UpperArm.R": (-84, -34, 0), "ForeArm.R": (-12, 0, 0), "Hand.R": (-20, 0, 0), "Fingers.R": (-34, 0, 0),
             "UpperArm.L": (4, 0, 0), "Staff:plant": 1.0, "SkirtF": (-6, 0, 8), "SkirtB": (-8, 0, 8), "Foot.R:ik": (0, -0.18, 0)}
    follow = P(sweep, {"Chest": (12, 0, 34), "UpperArm.R": (-70, -52, 0), "ForeArm.R": (-26, 0, 0), "Hips:loc": (0, -0.15, -0.12)})
    A.action("Attack2", [(1, TG), (8, P(wind, {"Foot.R:ik": (0, -0.05, 0.07)}), "L"), (14, sweep), (18, follow), (30, follow),
                         (46, {"Hips:loc": (0, -0.05, -0.03), "Chest": (3, 0, 8), "UpperArm.R": (-20, -8, 0), "ForeArm.R": (-20, 0, 0), "Foot.R:ik": (0, -0.08, 0.05)}), (60, S)], lag=LAG)

    # ---------------- Hit
    hit = {"Hips:loc": (0, 0.08, -0.03), "Spine": (-8, 0, 6), "Chest": (-11, 0, 9), "Neck": (4, 0, -6), "Head": (12, 0, -15),
           "UpperArm.R": (12, 14, 0), "ForeArm.R": (-18, 0, 0), "Fingers.R": (-22, 0, 0), "SkirtF": (-7, 0, 0), "SkirtB": (-7, 0, 0)}
    A.action("Hit", [(1, S, "L"), (4, hit), (9, {"Chest": (4, 0, -2), "Head": (-4, 0, 4), "SkirtF": (4, 0, 0), "SkirtB": (4, 0, 0)}), (18, S)], lag={"Fingers.R": 2, "SkirtF": 2, "SkirtB": 2})

    # ---------------- Stagger：被彈反，權杖被震開、後仰踉蹌→拄杖喘息→站穩
    rec = {"Hips:loc": (0, 0.30, -0.10), "Spine": (-14, 0, 4), "Chest": (-20, 0, 6), "Neck": (-10, 0, 0), "Head": (-22, 0, 10),
           "UpperArm.L": (-70, -55, 0), "ForeArm.L": (-10, 0, 0), "Staff": (60, 0, 0), "Staff:plant": 0.0,
           "UpperArm.R": (-50, 64, 0), "ForeArm.R": (-42, 0, 0), "Fingers.R": (-34, 0, 0), "SkirtF": (-16, 0, 0), "SkirtB": (-16, 0, 0), "Foot.R:ik": (0, 0.2, 0.1)}
    lean = {"Hips:loc": (0, 0.40, -0.24), "Spine": (20, 0, 0), "Chest": (24, 0, -4), "Neck": (10, 0, 0), "Head": (24, 0, -6),
            "UpperArm.L": (-30, -6, 0), "ForeArm.L": (-10, 0, 0), "Staff:plant": 1.0, "UpperArm.R": (-20, -8, 0), "ForeArm.R": (-30, 0, 0), "Fingers.R": (26, 0, 0),
            "SkirtF": (6, 0, 0), "SkirtB": (8, 0, 0), "Foot.R:ik": (0, 0.42, 0), "Foot.L:ik": (0, 0.2, 0)}
    pant = P(lean, {"Hips:loc": (0, 0.40, -0.21), "Chest": (20, 0, -4), "Head": (18, 0, 6)})
    A.action("Stagger", [(1, S, "L"), (6, rec), (10, P(rec, {"Hips:loc": (0, 0.36, -0.12), "Head": (-16, 0, 12)})), (20, lean), (32, pant), (44, lean),
                         (58, {"Hips:loc": (0, 0.2, -0.08), "Spine": (8, 0, 0), "Chest": (6, 0, 0), "Foot.R:ik": (0, 0.2, 0.06), "Foot.L:ik": (0, 0.1, 0.05)}), (70, S)], lag=LAG)

    # ---------------- PhaseShift：蜷身→爆發，雙臂大張、仰首、舉杖→顫抖維持→頓杖收
    curl = {"Hips:loc": (0, 0.02, -0.12), "Spine": (18, 0, 0), "Chest": (22, 0, 0), "Neck": (12, 0, 0), "Head": (22, 0, 0),
            "UpperArm.R": (-36, -22, 0), "ForeArm.R": (-98, 0, 0), "Fingers.R": (34, 0, 0), "UpperArm.L": (-6, 6, 0)}
    burst = {"Hips:loc": (0, 0.05, 0.05), "Spine": (-10, 0, 0), "Chest": (-17, 0, 0), "Neck": (-12, 0, 0), "Head": (-26, 0, 0),
             "UpperArm.R": (0, 80, 0), "ForeArm.R": (-24, 0, 0), "Hand.R": (-20, 0, 0), "Fingers.R": (-36, 0, 0),
             "UpperArm.L": (-58, -62, 0), "ForeArm.L": (-10, 0, 0), "Staff:plant": 1.0,
             "SkirtF": (-10, 0, 0), "SkirtB": (12, 0, 0)}
    q1 = P(burst, {"Head": (-23, 0, 5), "Chest": (-15, 0, 2), "Fingers.R": (-26, 0, 0), "Hips:loc": (0, 0.05, 0.035)})
    q2 = P(burst, {"Head": (-27, 0, -5), "Chest": (-18, 0, -2), "UpperArm.L": (-62, -64, 0)})
    A.action("PhaseShift", [(1, S), (16, curl), (25, P(curl, {"Hips:loc": (0, 0.02, -0.15), "Chest": (25, 0, 0)}), "L"), (30, burst), (36, q1), (42, q2), (48, q1), (54, q2), (60, q1), (66, burst),
                            (78, {"UpperArm.L": (-30, -10, 0), "Chest": (-4, 0, 0), "UpperArm.R": (0, 20, 0)}, "L"), (82, {"Hips:loc": (0, 0, -0.05), "Chest": (5, 0, 0)}), (92, S)], lag={"Fingers.R": 2, "SkirtF": 2, "SkirtB": 2})

    # ---------------- Die：受創→搖晃→像冰柱一樣僵直向後傾倒、落地反彈（最後一格停住）
    def fall(deg, lift=0.0):
        r = math.radians(deg)
        return {"Hips": (-deg, 0, 0), "Hips:loc": (0, 1.16 * math.sin(r), 1.16 * (math.cos(r) - 1) + lift)}

    d1 = P(hit, {"Head": (-14, 0, -12), "Chest": (-14, 0, 8)})
    d2 = {"Hips:loc": (0, -0.04, -0.06), "Spine": (10, 0, -3), "Chest": (12, 0, -4), "Head": (20, 0, 6), "UpperArm.R": (-4, 4, 0), "Fingers.R": (20, 0, 0)}
    limp = {"Spine": (-4, 0, 0), "Chest": (-6, 0, 0), "Neck": (-6, 0, 0), "Head": (-12, 0, 8), "UpperArm.R": (10, 16, 0), "ForeArm.R": (-8, 0, 0), "Fingers.R": (14, 0, 0),
            "UpperArm.L": (10, -10, 0), "ForeArm.L": (20, 0, 0)}
    down = P(limp, fall(84, 0.20), {"Head": (-4, 0, 14), "UpperArm.R": (30, 50, 0), "UpperArm.L": (20, -36, 0), "SkirtF": (4, 0, 0), "SkirtB": (-6, 0, 0),
                                   "Foot.L:ik": (0, 0, 0.06, -70), "Foot.R:ik": (0, 0, 0.06, -70)})
    A.action("Die", [(1, S, "L"), (5, d1), (22, d2), (38, P(limp, fall(6))), (48, P(limp, fall(22)), "L"), (58, down, "L"),
                     (61, P(down, fall(79, 0.24), {"Head": (-10, 0, 14)})), (66, down), (100, down)], lag={"Fingers.R": 2})


def build_anim():
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    arm = bpy.data.objects["Priest"]
    mesh = bpy.data.objects["PriestMesh"]
    L.clear_actions(arm)
    A = L.Animator(arm, base={"Staff:plant": 1.0})
    define_actions(A, L.sym)
    L.export_glb(OUT_GLB, arm, mesh)
    cam, _ = L.studio(HEIGHT)
    A.show(None, 1)
    L.render_views(cam, TMP, NAME, HEIGHT, center=(0.1, 0, HEIGHT * 0.5), extra=0.85)
    L.aim(cam, (0.05, 0, 1.85), 2.4, -25, 4)
    L.render(os.path.join(TMP, NAME + "_close.png"), (900, 760))
    FM = {"Enter": [1, 30, 60, 84, 110], "Attack": [1, 7, 12, 15, 54], "Attack2": [1, 8, 14, 18, 60], "Hit": [1, 4, 9, 14, 18],
          "Stagger": [1, 6, 16, 40, 70], "PhaseShift": [1, 20, 30, 50, 90], "Die": [1, 22, 50, 58, 100]}
    L.render_actions(cam, A, TMP, NAME, HEIGHT, extra=0.9, res=(480, 480), center=(0.1, 0.0, HEIGHT * 0.45), frames_map=FM)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


def view_only():
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    cam, _ = L.studio(HEIGHT)
    L.render_views(cam, TMP, NAME, HEIGHT, center=(0.1, 0, HEIGHT * 0.5))
    L.aim(cam, (0.05, 0, 1.85), 2.4, -25, 4)
    L.render(os.path.join(TMP, NAME + "_close.png"), (900, 760))


if STAGE in ("model", "all"):
    build_model()
if STAGE == "view":
    view_only()
if STAGE in ("anim", "all"):
    build_anim()
print("DONE", NAME, STAGE)
