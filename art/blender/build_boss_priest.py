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
OUT_GLB = os.path.join(HERE, "export_raw", NAME + ".glb")   # 未壓縮原檔；public/models 的壓縮版由 run_anim2.sh 產生
PREV = os.path.join(HERE, "preview")
TMP = os.path.join(PREV, "_frames")
BAKED = os.path.join(HERE, "textures", "baked", NAME)
HEIGHT = 2.6
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = argv[0] if argv else "all"
SX, SY = 0.47, -0.33  # 權杖軸位置
GRIP = 1.36
TEX = int(os.environ.get("BOSS_TEX", "2048"))  # 烘焙圖集邊長


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


def leather_mat():
    m = L.PMat("FrostLeather")
    le = m.scan("Leather028", 3.0)
    col = m.hsv(le["Color"], s=0.3, v=0.5)
    frost = m.ramp(m.noise(6, 4), [(0.45, 0), (0.62, 0.9)])
    col = m.mix(frost, col, (0.80, 0.87, 0.94))
    return m.finish(col, m.mix(frost, 0.7, 0.4), 0.0, m.bump(le["Displacement"], 0.6, 0.004))


# ================================================================== 建模（第二版：重新建模）
# 祭袍、披肩、毛領、兜帽、袖子、手都改成「體素融合的高模」→ 減面低模，皺褶是真的幾何（不是貼圖畫出來的），
# 高模的皺褶與霜紋烘焙成法線貼圖。誇張特徵：頭後方放射狀的巨大冰晶光環。
PROFILE = [(1.86, 0.085, 0.08), (1.80, 0.20, 0.115), (1.62, 0.20, 0.135), (1.32, 0.165, 0.125), (1.06, 0.215, 0.165), (0.60, 0.30, 0.255), (0.10, 0.40, 0.36)]


def robe_r(z):
    for (z0, a0, b0), (z1, a1, b1) in zip(PROFILE, PROFILE[1:]):
        if z >= z1:
            t = (z0 - z) / (z0 - z1)
            t = max(0.0, min(1.0, t))
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return PROFILE[-1][1], PROFILE[-1][2]


def robe_pt(a, z, off=0.0):
    rx, ry = robe_r(z)
    return Vector((math.sin(a) * (rx + off), -math.cos(a) * (ry + off), z))


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


def sculpt_mask(ob, c, sc):
    """把蛋形銀面具雕成五官：眉弓、深陷的眼窩、顴骨、凹頰、閉合的薄唇與下巴（只動朝前的半邊）。"""
    def g(x, z, cx, cz, wx, wz):
        return math.exp(-(((x - cx) / wx) ** 2 + ((z - cz) / wz) ** 2))
    for v in ob.data.vertices:
        q = Vector(((v.co.x - c.x) / sc[0], (v.co.y - c.y) / sc[1], (v.co.z - c.z) / sc[2]))
        front = max(0.0, min(1.0, -q.y * 1.6))
        if front <= 0:
            continue
        x, z = q.x, q.z
        d = 0.0
        d += 0.10 * math.exp(-((z - 0.30) / 0.09) ** 2) * max(0.0, 1 - (abs(x) / 0.85) ** 2)
        for sx in (-1, 1):
            d -= 0.17 * g(x, z, sx * 0.47, 0.12, 0.20, 0.13)
            d += 0.06 * g(x, z, sx * 0.62, -0.18, 0.18, 0.12)
            d -= 0.07 * g(x, z, sx * 0.50, -0.45, 0.17, 0.16)
        d += 0.035 * g(x, z, 0, -0.58, 0.30, 0.05) - 0.05 * g(x, z, 0, -0.64, 0.33, 0.022)
        d += 0.03 * g(x, z, 0, -0.70, 0.26, 0.05)
        d += 0.06 * g(x, z, 0, -0.88, 0.30, 0.10)
        d -= 0.04 * g(x, z, 0, 0.55, 0.12, 0.25)
        k = 1 + d * front
        v.co = Vector((c.x + q.x * sc[0] * k, c.y + q.y * sc[1] * k, c.z + q.z * sc[2] * k))
    ob.data.update()


def wool_mat(name, base, frost=0.5, trim=None, hem_frost=0.35):
    """厚羊毛祭袍（物體座標，可用在體素高模上）：深色底、凹處更暗、凸起的皺褶頂端磨亮、靠下襬與朝上的面結霜。
    trim=(z0, z1)：這段高度是銀線刺繡飾帶。"""
    m = L.PMat(name)
    co = m.coord()
    fab = m.scan("Fabric045", 3.2)
    z = m.sep(co)[2]
    col = m.mix(1.0, m.ramp(fab["Color"], [(0.1, 0.75), (0.9, 1.08)]), base, "MULTIPLY")
    col = m.mix(m.ramp(m.noise(1.8, 4), [(0.3, 0.0), (0.75, 0.35)]), col, m.mix(1.0, col, (0.55, 0.62, 0.74), "MULTIPLY"))
    pt = m.geom("Pointiness")
    col = m.mix(1.0, col, m.ramp(pt, [(0.44, 0.75), (0.5, 0.97), (0.57, 1.15)]), "MULTIPLY")
    rough = m.ramp(fab["Roughness"], [(0.0, 0.82), (1.0, 0.97)])
    n = m.bump(fab["Displacement"], 0.45, 0.003)
    metal = 0.0
    if trim:
        band = m.math("MULTIPLY", m.ramp(z, [(trim[0] - 0.004, 0), (trim[0], 1)]), m.ramp(z, [(trim[1], 1), (trim[1] + 0.004, 0)]))
        pat = m.voronoi(70.0, "F1", rand=0.15)
        dia = m.ramp(pat, [(0.18, 1.0), (0.32, 0.25), (0.45, 0.85)])
        tcol = m.ramp(dia, [(0.25, (0.16, 0.17, 0.20)), (1.0, (0.62, 0.64, 0.66))])
        col = m.mix(band, col, tcol)
        n = m.bump(m.math("MULTIPLY", dia, band), 0.6, 0.004, normal=n)
        rough = m.mix(band, rough, 0.45)
        metal = m.math("MULTIPLY", band, m.math("MULTIPLY", dia, 0.7))
    up = m.sep(m.geom("Normal"))[2]
    hem = m.ramp(z, [(0.10, 1.0), (0.10 + max(hem_frost, 0.01), 0.0)])
    # 霜：細碎的結晶（高頻雜訊）只長在朝上的面、皺褶凸起處與下襬，不再是一大片一大片的白斑
    ridge = m.ramp(pt, [(0.5, 0.0), (0.56, 1.0)])
    fr = m.math("ADD", m.math("ADD", m.math("MULTIPLY", m.noise(11, 6, 0.75), 0.6), m.math("MULTIPLY", up, 0.08)),
                m.math("ADD", m.math("MULTIPLY", hem, 0.40 if hem_frost else 0.0), m.math("MULTIPLY", ridge, 0.15)))
    frost_m = m.math("MULTIPLY", m.ramp(fr, [(0.74 - frost * 0.22, 0), (0.86 - frost * 0.2, 1)]), 0.85)
    col = m.mix(frost_m, col, m.mix(m.noise(25, 2), (0.50, 0.58, 0.70), (0.80, 0.86, 0.94)))
    rough = m.mix(frost_m, rough, m.ramp(m.noise(14, 2), [(0.3, 0.25), (0.7, 0.55)]))
    n = m.bump(m.math("MULTIPLY", frost_m, m.noise(40, 2)), 0.4, 0.003, normal=n)
    return m.finish(col, rough, metal, n, emit=m.mix(frost_m, (0, 0, 0), (0.01, 0.025, 0.04)), emit_strength=1.0)


def fur_mat():
    """結霜的毛領：一束束毛（沿向下方向拉長的雜訊）、根部暗、尖端霜白。"""
    m = L.PMat("FrostFur")
    co = m.coord()
    strands = m.noise(1.0, 3, 0.6, vec=m.mapping(co, scale=(90, 90, 9)))
    clump = m.noise(9, 2)
    col = m.ramp(m.math("ADD", m.math("MULTIPLY", strands, 0.7), m.math("MULTIPLY", clump, 0.3)),
                 [(0.25, (0.10, 0.12, 0.16)), (0.5, (0.34, 0.38, 0.45)), (0.72, (0.72, 0.78, 0.86)), (0.9, (0.92, 0.95, 0.99))])
    pt = m.geom("Pointiness")
    col = m.mix(1.0, col, m.ramp(pt, [(0.45, 0.35), (0.5, 0.9), (0.56, 1.25)]), "MULTIPLY")
    n = m.bump(strands, 0.9, 0.006)
    n = m.bump(clump, 0.4, 0.01, normal=n)
    return m.finish(col, 0.9, 0.0, n)


def skin_mat():
    m = L.PMat("FrostSkin")
    col = m.mix(m.noise(14, 3), (0.30, 0.34, 0.40), (0.50, 0.55, 0.62))
    pt = m.geom("Pointiness")
    col = m.mix(1.0, col, m.ramp(pt, [(0.46, 0.6), (0.5, 1.0), (0.55, 1.25)]), "MULTIPLY")
    veins = m.ramp(m.voronoi(30, "DISTANCE_TO_EDGE"), [(0.0, 0.0), (0.02, 1.0)])
    col = m.mix(m.math("SUBTRACT", 1.0, veins), col, (0.18, 0.22, 0.34))
    return m.finish(col, 0.5, 0.0, m.bump(m.noise(60, 2), 0.25, 0.0015))


def build_model():
    L.reset()
    rnd = random.Random(11)
    M_robe = wool_mat("RobeWool", (0.085, 0.11, 0.21), frost=0.30, trim=(0.17, 0.25), hem_frost=0.30)
    M_mantle = wool_mat("MantleWool", (0.085, 0.095, 0.13), frost=0.35, hem_frost=0.0)
    M_fur = fur_mat()
    M_stole = cloth_mat("Stole", (0.40, 0.42, 0.48), "Fabric036", frost=0.12, trim=(0.02, 0.98, 26, 240), fold=1)
    M_ice = ice_mat(glow=0.16)
    M_silver = silver_mat(2.006)
    M_iron = iron_mat()
    M_glow = glow_mat()
    M_skin = skin_mat()
    M_leather = leather_mat()
    D = []
    ORG = []

    def add(o, sharp=None):
        if sharp:
            L.hard(o, sharp)
        D.append(o)
        return o

    def icicle(p, length, r, bones, lean=(0, 0), segs=5):
        p = Vector(p)
        tip = p + Vector((lean[0], lean[1], -length))
        o = L.loft("Icicle", [p + Vector((0, 0, r * 0.6)), p.lerp(tip, 0.4), tip], [r, r * 0.6, r * 0.04],
                   segs=segs, sub=1, caps=("flat", "point"), mat=M_ice)
        w = bones(p, 0) if callable(bones) else {bones: 1.0}
        L.assign(o, lambda co, t: w)
        L.hard(o, 30)
        o["uvg"] = 1          # 所有冰柱共用同一塊貼圖（不然幾百根冰柱會吃掉大半張圖集）
        D.append(o)

    def crystal(base, d, length, r, bones, sides=5):
        """多角柱冰晶（尖頂），沿 d 方向生長。"""
        base, d = Vector(base), Vector(d).normalized()
        tip = base + d * length
        o = L.loft("Crystal", [base - d * r, base + d * length * 0.72, tip], [r, r * 0.95, r * 0.03], segs=sides, sub=1, caps=("flat", "point"),
                   mat=M_ice, ref=d.orthogonal())
        L.assign(o, bones)
        L.hard(o, 25)
        o["uvg"] = 2          # 冰晶共用同一塊貼圖
        D.append(o)
        return o

    # ---------------------------------------------------------------- 祭袍（高模：本體＋直向深皺褶＋腰部鼓起）
    RP = []
    fold_shape = lambda a, t: 1 + (0.01 + 0.03 * t ** 2) * math.sin(9 * a + 1.3)
    RP.append(L.loft("RobeCore", [(0, 0, z) for z, _, _ in PROFILE], [(a * 0.97, b * 0.97) for _, a, b in PROFILE], segs=48, sub=5,
                     caps=("round", "flat"), shape=fold_shape, bones=body_w))
    n_f = 26
    for k in range(n_f):
        a = 2 * math.pi * (k + rnd.uniform(-0.25, 0.25)) / n_f
        z0 = rnd.uniform(1.02, 1.22) if abs(math.sin(a)) > 0.3 else rnd.uniform(0.85, 1.15)
        pts, rr = [], []
        for i in range(7):
            t = i / 6
            z = z0 + (0.09 - z0) * t
            sway = 0.05 * math.sin(t * 3.0 + k) * t
            pts.append(robe_pt(a + sway, z, -0.005 + 0.012 * t))
            rr.append(0.006 + 0.034 * t ** 1.3 * rnd.uniform(0.75, 1.25))
        RP.append(L.loft(f"RobeFold{k}", pts, rr, segs=8, sub=3, caps=("point", "flat"), bones=body_w))
    for k in range(16):  # 腰帶上方的布料鼓起
        a = 2 * math.pi * k / 16 + 0.1
        p = robe_pt(a, 1.37, 0.0)
        RP.append(L.ellipsoid(f"Blouse{k}", p, (0.045, 0.045, 0.06), rot=(0, 0, math.degrees(a)), bones=body_w, segs=10, rings=6))

    def robe_post(h):
        L.displace(h, "CLOUDS", 0.005, 0.04, 2)
    ORG.append(L.organic("Robe", RP, M_robe, voxel=0.0075, tris=10500, smooth=3, post=robe_post, uv_angle=70) + (M_robe,))

    # ---------------------------------------------------------------- 外披（寬肩、背後長、深垂褶），加厚後體素融合
    rows, cols = 20, 52
    grid = []
    for i in range(rows + 1):
        v = i / rows
        row = []
        for j in range(cols + 1):
            a = math.radians(30 + (360 - 60) * j / cols)
            fb = max(0.0, -math.cos(a)) ** 1.4
            ff = max(0.0, math.cos(a)) ** 2
            zh = 1.22 - 0.62 * fb - 0.20 * ff + 0.05 * math.sin(j * 1.7) + (0.06 if j % 5 == 0 else 0)
            z = 1.86 + (zh - 1.86) * v
            rx, ry = robe_r(z)
            sh = math.exp(-((z - 1.74) / 0.16) ** 2)
            rx = rx + 0.05 + 0.09 * sh + 0.14 * v * abs(math.sin(a)) ** 2
            ry = ry + 0.045 + 0.03 * v + 0.07 * v * fb
            rip = 1 + (0.012 + 0.11 * v ** 1.6) * (math.sin(11 * a + 0.5) * 0.6 + math.sin(19 * a) * 0.25 + math.sin(5 * a + 2) * 0.15)
            row.append(Vector((math.sin(a) * rx * rip, -math.cos(a) * ry * rip, z)))
        grid.append(row)

    def mantle_w(co, uvt=None):
        w = body_w(co)
        s = 1 if co.x > 0 else -1
        k = L._sst((abs(co.x) - 0.17) / 0.10) * L._sst((co.z - 1.45) / 0.2) * 0.65
        w = {b: x * (1 - k) for b, x in w.items()}
        w["UpperArm.L" if s > 0 else "UpperArm.R"] = k
        return w

    MP = [L.sheet("Mantle", grid, thick=0.026, bones=mantle_w)]
    ORG.append(L.organic("MantleO", MP, M_mantle, voxel=0.0065, tris=6500, smooth=2,
                         post=lambda h: L.displace(h, "CLOUDS", 0.004, 0.03, 2), uv_angle=70) + (M_mantle,))
    for j in range(0, cols + 1):
        p = grid[rows][j]
        if rnd.random() < 0.30:
            icicle(p + Vector((0, 0, 0.01)), rnd.uniform(0.05, 0.20) * (1.4 if j % 5 == 0 else 1), rnd.uniform(0.011, 0.02), mantle_w)

    # ---------------------------------------------------------------- 結霜毛領（誇張的寬肩輪廓）
    FP = []
    for ring, (z, n, sx, sy, ln) in enumerate(((1.86, 30, 0.20, 0.16, 0.10), (1.80, 34, 0.27, 0.19, 0.12), (1.73, 38, 0.33, 0.22, 0.13))):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * ring) / n
            if abs(((math.degrees(a) + 180) % 360) - 180) < 16 and ring < 2:   # 前面留給面具下的領口
                continue
            p = Vector((math.sin(a) * sx, -math.cos(a) * sy, z + rnd.uniform(-0.01, 0.015)))
            FP.append(L.ellipsoid(f"Fur{ring}_{k}", p, (0.04, 0.035, ln * rnd.uniform(0.85, 1.2)),
                                  rot=(-38 - 10 * ring + rnd.uniform(-8, 8), rnd.uniform(-10, 10), math.degrees(a)), bones=mantle_w, segs=10, rings=7))
    ORG.append(L.organic("FurCollar", FP, M_fur, voxel=0.006, tris=3000, smooth=2, post=lambda h: L.displace(h, "STUCCI", 0.006, 0.012), uv_angle=70) + (M_fur,))

    # ---------------------------------------------------------------- 兜帽（加厚後融合，帽沿深垂）
    HP = [L.ellipsoid("Hood", (0, 0.016, 2.02), (0.118, 0.13, 0.14), bones="Head", segs=24, rings=14)]
    cowl = []
    for i in range(13):
        th = 0.10 + 1.95 * i / 12
        row = []
        for j in range(29):
            a = math.radians(-146 + 292 * j / 28)
            edge = 1 - min(1.0, (146 - abs(math.degrees(a))) / 30)
            r = 1 + 0.09 * math.sin(7 * a + i * 0.8) * (i / 12) ** 1.5 + 0.12 * edge * math.sin(th) ** 2
            x = math.sin(a) * math.sin(th) * 0.150 * r
            y = 0.02 + math.cos(a) * math.sin(th) * 0.166 * r - 0.045 * edge * math.exp(-((th - 0.75) / 0.5) ** 2)
            z = 2.02 + math.cos(th) * 0.18 + 0.025 * math.exp(-((th - 0.3) / 0.25) ** 2) * (1 - edge) - 0.05 * (i / 12) ** 2
            row.append(Vector((x, y, z)))
        cowl.append(row)
    HP.append(L.sheet("Cowl", cowl, thick=0.02, bones=[("Head", 0), ("Neck", 0.85)], blend=0.25))
    hood_back = [[Vector((math.sin(a) * (0.12 + 0.04 * v), 0.04 + math.cos(a) * (0.125 + 0.04 * v), 2.06 - 0.26 * v)) for a in [math.radians(x) for x in range(-100, 101, 10)]] for v in [0, 0.25, 0.5, 0.75, 1.0]]
    HP.append(L.sheet("HoodDrape", hood_back, thick=0.02, bones=[("Head", 0), ("Neck", 0.5), ("Chest", 0.9)], blend=0.3))
    ORG.append(L.organic("HoodO", HP, M_mantle, voxel=0.005, tris=3000, smooth=2, post=lambda h: L.displace(h, "CLOUDS", 0.003, 0.025, 2)) + (M_mantle,))
    add(L.loft("NeckWrap", [(0, 0, 1.86), (0, -0.005, 1.95)], [0.06, 0.055], segs=12, sub=2, caps=("open", "open"), bones=[("Chest", 0), ("Neck", 0.3)], blend=0.4, mat=M_stole))

    # ---------------------------------------------------------------- 銀面具與冰晶王冠
    mask = L.ellipsoid("Mask", (0, -0.075, 1.99), (0.085, 0.064, 0.128), rot=(-4, 0, 0), bones="Head", mat=M_silver, segs=44, rings=34)
    sculpt_mask(mask, Vector((0, -0.075, 1.99)), (0.085, 0.064, 0.128))
    add(mask)
    add(L.loft("Nose", [(0, -0.130, 2.04), (0, -0.141, 1.99), (0, -0.138, 1.945)], [(0.012, 0.01), (0.013, 0.012), (0.017, 0.008)], segs=8, sub=2, bones="Head", mat=M_silver))
    band = [[Vector((math.sin(a) * (0.124 + 0.006 * k), 0.014 - math.cos(a) * (0.137 + 0.006 * k), 2.09 + 0.05 * k)) for a in [2 * math.pi * j / 28 for j in range(28)]] for k in (0, 1)]
    add(L.sheet("CrownBand", band, thick=0.016, wrap=True, bones="Head", mat=M_silver), sharp=40)
    for k in range(13):
        a = 2 * math.pi * k / 13
        front = max(0.0, math.cos(a))
        h = 0.10 + 0.07 * rnd.random() + 0.14 * front ** 3
        base = Vector((math.sin(a) * 0.125, 0.014 - math.cos(a) * 0.138, 2.13))
        out = Vector((math.sin(a), -math.cos(a), 0))
        crystal(base, out * 0.25 + Vector((0, 0, 1)), h, 0.016, "Head")

    # 誇張特徵：頭後的冰晶光環（放射狀的長冰晶，像結凍的日輪）
    hc = Vector((0, 0.17, 2.08))
    for k in range(17):
        ang = math.radians(-120 + 240 * k / 16)
        d = Vector((math.sin(ang), 0.18, math.cos(ang)))
        ln = 0.22 + 0.26 * math.cos(ang * 0.9) ** 2 + 0.06 * rnd.random()
        crystal(hc + d.normalized() * 0.10, d, ln, 0.022 + 0.01 * math.cos(ang) ** 2, "Head", sides=6)
        if k % 2 == 0:
            d2 = Vector((math.sin(ang + 0.1), 0.25, math.cos(ang + 0.1)))
            crystal(hc + d2.normalized() * 0.12, d2, ln * 0.5, 0.013, "Head", sides=5)
    add(L.loft("HaloRing", [hc + Vector((math.sin(math.radians(a)) * 0.115, 0, math.cos(math.radians(a)) * 0.115)) for a in range(-130, 131, 13)],
               [0.014] * 21, segs=6, sub=2, caps=("round", "round"), bones="Head", mat=M_silver), sharp=40)
    for k in range(7):
        a = math.radians(-75 + 25 * k)
        icicle((math.sin(a) * 0.11, 0.0 - math.cos(a) * 0.11, 1.915 - 0.02 * abs(math.sin(a))), rnd.uniform(0.03, 0.07), 0.008, "Head")
    # 左肩冰晶簇（不對稱，破除左右一樣的呆板）
    shw = lambda co, t: {"Chest": 0.4, "UpperArm.L": 0.6}
    for k in range(7):
        b = Vector((0.24 + rnd.uniform(-0.04, 0.05), rnd.uniform(-0.04, 0.08), 1.84 + rnd.uniform(-0.02, 0.03)))
        crystal(b, Vector((rnd.uniform(0.2, 1.0), rnd.uniform(-0.3, 0.5), rnd.uniform(0.6, 1.4))), rnd.uniform(0.10, 0.26), rnd.uniform(0.016, 0.03), shw)

    # ---------------------------------------------------------------- 前垂聖帶與腰帶
    for s in (1, -1):
        g = []
        for i in range(17):
            z = 1.84 - (1.84 - 0.46) * i / 16
            rx, ry = robe_r(z)
            row = []
            for k in range(3):
                x = s * (0.05 + 0.038 * k)
                y = -ry * math.sqrt(max(0.05, 1 - (x / (rx + 0.02)) ** 2)) - 0.045 - 0.015 * (i / 16)
                if z > 1.78:
                    y = -0.08 - (1.86 - z) * 0.9
                row.append(Vector((x, y, z + 0.006 * math.sin(i * 1.3 + k))))
            g.append(row)
        add(L.sheet("Stole", g, thick=0.012, bones=lambda co, uvt: body_w(co), mat=M_stole))
        for k in range(3):
            icicle(g[-1][k], rnd.uniform(0.05, 0.12), 0.011, body_w)
    belt = [[Vector((math.sin(a) * (robe_r(z)[0] + 0.045), -math.cos(a) * (robe_r(z)[1] + 0.045), z)) for a in [2 * math.pi * j / 36 for j in range(36)]] for z in (1.34, 1.27)]
    add(L.sheet("Belt", belt, thick=0.018, wrap=True, bones=lambda co, uvt: body_w(co), mat=M_leather))
    for x, ln in ((-0.10, 0.34), (-0.135, 0.22), (0.11, 0.28)):
        y = -robe_r(1.26)[1] - 0.06
        add(L.loft("Cord", [(x, y, 1.275), (x * 1.05, y - 0.02, 1.27 - ln * 0.5), (x * 1.1, y - 0.035, 1.27 - ln)], [0.009, 0.008, 0.008], segs=6, sub=2, bones=body_w, mat=M_leather))
        crystal((x * 1.1, y - 0.037, 1.265 - ln), (0, 0, -1), 0.10, 0.018, body_w, sides=6)

    # ---------------------------------------------------------------- 寬袖（加厚的管狀布＋皺褶，體素融合）、手
    def sleeve_parts(sx, pts, r0, r1):
        n_r = 14
        res = L.polyline(pts, n_r)
        g = []
        prevN = Vector((0, 0, 1))
        for i, c in enumerate(res):
            T = (res[min(i + 1, n_r)] - res[max(i - 1, 0)]).normalized()
            N = (prevN - T * prevN.dot(T)).normalized()
            prevN = N
            B2 = T.cross(N)
            t = i / n_r
            r = r0 + (r1 - r0) * t ** 1.6
            row = []
            for j in range(24):
                a = 2 * math.pi * j / 24
                k = 1 + (0.03 + 0.12 * t ** 2) * math.sin(5 * a + 1 + 3 * t) + 0.05 * t * math.sin(11 * a)
                row.append(c + N * (r * k * math.cos(a)) + B2 * (r * k * math.sin(a)))
            g.append(row)
        return [L.sheet("Sleeve" + sx, g, thick=0.02, wrap=True, bones=[("Chest", 0), ("UpperArm" + sx, 0.10), ("ForeArm" + sx, 0.55)], blend=0.14)], g

    Ls, Le, Lw = Vector((0.205, 0, 1.80)), Vector((0.33, 0.03, 1.49)), Vector((0.44, -0.20, 1.37))
    SPl, gL = sleeve_parts(".L", [Ls, Ls.lerp(Le, 0.5) + Vector((0.01, 0.01, 0)), Le, Le.lerp(Lw, 0.5) + Vector((0, 0, -0.03)), Lw + Vector((-0.01, 0.05, -0.05))], 0.088, 0.17)
    Rs, Re, Rw = Vector((-0.205, 0, 1.80)), Vector((-0.31, 0.03, 1.47)), Vector((-0.365, -0.05, 1.16))
    SPr, gR = sleeve_parts(".R", [Rs, Rs.lerp(Re, 0.5) + Vector((-0.01, 0.01, 0)), Re, Re.lerp(Rw, 0.55), Rw + Vector((0, 0.01, 0.05))], 0.088, 0.17)
    ORG.append(L.organic("SleeveL", SPl, M_mantle, voxel=0.0055, tris=2200, smooth=2, post=lambda h: L.displace(h, "CLOUDS", 0.003, 0.025, 2)) + (M_mantle,))
    ORG.append(L.organic("SleeveR", SPr, M_mantle, voxel=0.0055, tris=2200, smooth=2, post=lambda h: L.displace(h, "CLOUDS", 0.003, 0.025, 2)) + (M_mantle,))
    for g, bone in ((gL, "ForeArm.L"), (gR, "ForeArm.R")):
        cuff = g[-1]
        zmin = min(p.z for p in cuff)
        for i, p in enumerate(cuff):
            if p.z < zmin + 0.10 and i % 3 == 0:
                icicle(p, rnd.uniform(0.06, 0.20), 0.013, bone)

    # 手（掌、指節分明的細長手指，體素融合成一隻手）
    HL = [L.loft("Wrist.L", [Le.lerp(Lw, 0.5), Lw, Lw + Vector((0.012, -0.05, 0))], [0.03, 0.026, 0.03], segs=10, sub=2, bones=[("ForeArm.L", 0), ("Hand.L", 0.7)], blend=0.3),
          L.ellipsoid("Palm.L", (0.455, -0.285, GRIP), (0.03, 0.05, 0.05), rot=(0, 0, -20), bones="Hand.L", segs=12, rings=8)]
    for k in range(4):
        z = GRIP - 0.034 + 0.0225 * k
        ln = (1.0, 1.0, 0.95, 0.82)[k]
        angs = [110 - 210 * ln * q / 4 for q in range(5)]
        rr = [0.036, 0.040, 0.037, 0.034, 0.031]
        pts = [Vector((SX + r_ * math.cos(math.radians(a)), SY + r_ * math.sin(math.radians(a)), z + 0.002 * i)) for i, (a, r_) in enumerate(zip(angs, rr))]
        HL.append(L.loft(f"FingerL{k}", pts, [0.0118, 0.0128, 0.0105, 0.0112, 0.0072], segs=10, sub=3, caps=("round", "round"), bones=[("Hand.L", 0), ("Fingers.L", 0.2)], blend=0.2))
    pts = [Vector((SX + 0.034 * math.cos(math.radians(a)), SY + 0.034 * math.sin(math.radians(a)), GRIP + 0.062 + 0.006 * i)) for i, a in enumerate((130, 190, 250))]
    HL.append(L.loft("ThumbL", pts, [0.013, 0.011, 0.005], segs=8, sub=2, caps=("round", "round"), bones="Hand.L"))
    ORG.append(L.organic("HandL", HL, M_skin, voxel=0.0028, tris=1500, smooth=2) + (M_skin,))
    HR = [L.loft("Wrist.R", [Re.lerp(Rw, 0.6), Rw, Rw + Vector((-0.004, -0.012, -0.06))], [0.03, 0.025, 0.03], segs=10, sub=2, bones=[("ForeArm.R", 0), ("Hand.R", 0.7)], blend=0.3)]
    palm = Rw + Vector((-0.006, -0.02, -0.095))
    HR.append(L.ellipsoid("Palm.R", palm, (0.045, 0.02, 0.055), rot=(8, 0, 0), bones="Hand.R", segs=12, rings=8))
    for k, dx in enumerate((-0.036, -0.012, 0.012, 0.035)):
        b = palm + Vector((dx, -0.006, -0.045))
        ln = (0.085, 0.10, 0.095, 0.075)[k]
        mid = b + Vector((dx * 0.35, -0.02, -ln))
        tip = mid + Vector((dx * 0.2, -0.045, -ln * 0.85))
        HR.append(L.loft(f"FingerR{k}", [b, b.lerp(mid, 0.5), mid, mid.lerp(tip, 0.55) + Vector((0, -0.008, 0)), tip],
                         [0.012, 0.0108, 0.0122, 0.0095, 0.004], segs=10, sub=3, caps=("round", "point"), bones=[("Hand.R", 0), ("Fingers.R", 0.25)], blend=0.2))
    tb = palm + Vector((0.045, -0.012, 0.01))
    HR.append(L.loft("ThumbR", [tb, tb + Vector((0.03, -0.03, -0.05)), tb + Vector((0.035, -0.055, -0.11))], [0.013, 0.011, 0.003], segs=8, sub=2, caps=("round", "point"), bones="Hand.R"))
    ORG.append(L.organic("HandR", HR, M_skin, voxel=0.0028, tris=1500, smooth=2) + (M_skin,))

    # ---------------------------------------------------------------- 靴
    for s, sx in ((1, ".L"), (-1, ".R")):
        x = 0.115 * s
        add(L.loft("Boot" + sx, [(x, 0.03, 0.27), (x, 0.03, 0.15), (x, -0.02, 0.07), (x * 1.08, -0.13, 0.05), (x * 1.12, -0.23, 0.04)],
                   [0.055, 0.055, (0.058, 0.056), (0.058, 0.045), (0.05, 0.032)], segs=12, sub=4, bones=[("Shin" + sx, 0), ("Foot" + sx, 0.3)], blend=0.12, mat=M_leather))

    # ---------------------------------------------------------------- 鐵權杖與冰封聖物提燈（燈頂長出冰晶簇）
    def st(o, sharp=None):
        L.assign(o, "Staff")
        return add(o, sharp)

    st(L.loft("Shaft", [(SX, SY, 0.10), (SX, SY, 0.9), (SX, SY, 1.6), (SX, SY, 2.14)], [0.021, 0.019, 0.019, 0.022], segs=10, sub=2, caps=("flat", "flat"), mat=M_iron))
    st(L.loft("Butt", [(SX, SY, 0.16), (SX, SY, 0.10), (SX, SY, 0.0)], [0.022, 0.034, 0.002], segs=6, sub=1, caps=("flat", "point"), mat=M_iron), 30)
    for z, r in ((0.20, 0.032), (1.22, 0.03), (1.52, 0.03), (1.95, 0.034), (2.06, 0.04)):
        st(L.ellipsoid("Collar", (SX, SY, z), (r, r, 0.018), mat=M_iron, segs=10, rings=6))
    st(L.loft("LBase", [(SX, SY, 2.12), (SX, SY, 2.155), (SX, SY, 2.17)], [0.035, 0.098, 0.098], segs=6, sub=1, caps=("flat", "flat"), mat=M_iron), 30)
    st(L.loft("LPane", [(SX, SY, 2.17), (SX, SY, 2.43)], [0.078, 0.078], segs=6, sub=1, caps=("open", "open"), mat=M_glow), 30)
    st(L.loft("LTop", [(SX, SY, 2.43), (SX, SY, 2.45), (SX, SY, 2.56), (SX, SY, 2.585)], [0.10, 0.105, 0.03, 0.022], segs=6, sub=1, caps=("flat", "flat"), mat=M_iron), 30)
    st(L.ellipsoid("LFinial", (SX, SY, 2.615), (0.028, 0.028, 0.034), mat=M_iron, segs=8, rings=6))
    for k in range(6):
        a = math.radians(60 * k)
        px, py = SX + 0.086 * math.cos(a), SY + 0.086 * math.sin(a)
        st(L.box("LPost", (px, py, 2.30), (0.016, 0.016, 0.27), rot=(0, 0, 60 * k), mat=M_iron))
        a2 = math.radians(60 * k + 30)
        st(L.box("LBar", (SX + 0.074 * math.cos(a2), SY + 0.074 * math.sin(a2), 2.30), (0.008, 0.086, 0.01), rot=(0, 0, 60 * k + 30), mat=M_iron))
        icicle((px, py, 2.155), rnd.uniform(0.05, 0.14), 0.011, "Staff")
    for k in range(9):
        a = math.radians(40 * k + rnd.uniform(-10, 10))
        d = Vector((math.cos(a), math.sin(a), rnd.uniform(0.6, 1.8)))
        crystal((SX + 0.03 * math.cos(a), SY + 0.03 * math.sin(a), 2.60), d, rnd.uniform(0.10, 0.24), rnd.uniform(0.014, 0.024), "Staff")
    for z in (1.60, 1.25, 0.9, 0.5):
        icicle((SX + 0.02, SY, z), rnd.uniform(0.04, 0.09), 0.008, "Staff")

    # --- 骨架（與第一版完全相同）
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
    mesh = L.assemble("PriestMesh", arm, ORG, D, BAKED, size=TEX, emit_strength=3.0, emit_size=512, ao_dist=0.35, extrusion=0.035)
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
    A.action("Idle", [(1, S), (34, i1), (70, i2), (100, S)], lag=LAG, loop=True)

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
    A.action("Attack", [(1, TG), (10, P(ant, {"Foot.L:ik": (0, -0.08, 0.08)}), "io"), (14, hitp, "in3"), (17, reb, "out"), (20, hold, "io"), (30, hold),
                        (44, {"Hips:loc": (0, -0.08, -0.04), "Spine": (6, 0, 0), "Chest": (4, 0, 0), "UpperArm.L": (-30, -6, 0), "Staff:plant": 0.6, "Foot.L:ik": (0, -0.1, 0.06)}, "io"), (56, S, "io")],
             lag=LAG, hits=[(14, "Staff")])

    # ---------------- Attack2：右手橫掃冰霜＋權杖頓地
    wind = P(TG, {"Spine": (-4, 0, -18), "Chest": (-6, 0, -24), "Head": (4, 0, 26), "UpperArm.R": (-40, 62, 0), "ForeArm.R": (-70, 0, 0), "Fingers.R": (24, 0, 0),
                  "Hips:loc": (0, 0.08, -0.02)})
    sweep = {"Hips:loc": (0, -0.14, -0.10), "Spine": (8, 0, 16), "Chest": (10, 0, 26), "Neck": (0, 0, -12), "Head": (-6, 0, -18),
             "UpperArm.R": (-84, -34, 0), "ForeArm.R": (-12, 0, 0), "Hand.R": (-20, 0, 0), "Fingers.R": (-34, 0, 0),
             "UpperArm.L": (4, 0, 0), "Staff:plant": 1.0, "SkirtF": (-6, 0, 8), "SkirtB": (-8, 0, 8), "Foot.R:ik": (0, -0.18, 0)}
    follow = P(sweep, {"Chest": (12, 0, 34), "UpperArm.R": (-70, -52, 0), "ForeArm.R": (-26, 0, 0), "Hips:loc": (0, -0.15, -0.12)})
    A.action("Attack2", [(1, TG), (10, P(wind, {"Foot.R:ik": (0, -0.05, 0.07)}), "io"), (15, sweep, "in3"), (19, follow, "out3"), (30, follow, "io"),
                         (46, {"Hips:loc": (0, -0.05, -0.03), "Chest": (3, 0, 8), "UpperArm.R": (-20, -8, 0), "ForeArm.R": (-20, 0, 0), "Foot.R:ik": (0, -0.08, 0.05)}, "io"), (60, S, "io")],
             lag=LAG, hits=[(15, "Fingers.R")])

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


    # ================================================================ 第二版新增（壓迫感）：滑步逼近、繞行、二階段待機、三連擊、延遲杖擊、突進冰爪、尖嘯
    def glide(N, stride, lift, d, step=4, lean=6, dz=-0.04, side=0.0):
        keys = []
        for f in range(0, N + 1, step):
            ph = (f / N) % 1.0
            gl = L.gait(ph, stride, lift, 0.40, d, pitch=8)
            gr = L.gait(ph + 0.5, stride, lift, 0.40, d, pitch=8)
            s2 = math.sin(2 * math.pi * ph)
            c2 = math.cos(2 * math.pi * ph)
            pose = {"Hips:loc": (0.02 * math.sin(2 * math.pi * (ph - 0.15)), -0.02, dz - 0.012 * math.cos(4 * math.pi * ph)),
                    "Spine": (lean, side, 3 * s2), "Chest": (lean + 2, 0, -4 * s2), "Neck": (-4, 0, 0), "Head": (-6, 4 * c2 - side, 2 * s2),
                    "UpperArm.R": (-34 + 8 * s2, 10, 0), "ForeArm.R": (-52, 0, 0), "Hand.R": (-10, 0, 0), "Fingers.R": (8 * c2, 0, 0),
                    "UpperArm.L": (-8 - 6 * s2, -2, 0), "Staff:plant": 1.0,
                    "SkirtF": (-6 * s2 * abs(d[1]) + 3 * d[0] * s2, 0, 4 * s2 * abs(d[0])), "SkirtB": (6 * s2 * abs(d[1]), 0, -4 * s2 * abs(d[0])),
                    "Foot.L:ik": gl, "Foot.R:ik": gr}
            keys.append((f, pose))
        return keys
    A.action("Stalk", glide(48, 0.34, 0.05, (0, -1)), lag=LAG, loop=True)
    A.action("StrafeL", glide(44, 0.28, 0.045, (1, 0), lean=4, side=-4), lag=LAG, loop=True)
    A.action("StrafeR", glide(44, 0.28, 0.045, (-1, 0), lean=4, side=4), lag=LAG, loop=True)

    # ---------------- IdleAggro：佝僂前探、頭部神經質地抽搐歪斜、右手指爪緩緩收張、權杖微離地
    AG = {"Hips:loc": (0, -0.04, -0.10), "Spine": (12, 0, 0), "Chest": (14, 0, 0), "Neck": (-6, 0, 0), "Head": (-10, 0, 0),
          "UpperArm.R": (-50, 10, 0), "ForeArm.R": (-50, 0, 0), "Hand.R": (-20, 0, 0), "Fingers.R": (-30, 0, 0),
          "UpperArm.L": (-22, -6, 0), "ForeArm.L": (-8, 0, 0), "Staff:plant": 0.85, "SkirtF": (6, 0, 0), "SkirtB": (4, 0, 0)}
    tw1 = P(AG, {"Head": (-12, 18, 10), "Neck": (-6, 6, 0), "Fingers.R": (10, 0, 0)})
    tw2 = P(AG, {"Head": (-8, -14, -8), "Neck": (-6, -4, 0), "Fingers.R": (-36, 0, 0), "Chest": (16, 0, 3), "Hips:loc": (0.02, -0.04, -0.11)})
    A.action("IdleAggro", [(0, AG), (6, tw1, "in"), (14, tw1, "io"), (20, AG, "io"), (27, tw2, "in"), (36, tw2, "io"), (44, P(AG, {"Fingers.R": (6, 0, 0)}), "io"), (52, AG, "io")],
             lag=LAG, loop=True)

    # ---------------- Combo3：右手冰霜橫掃（快）→ 反手回掃（更快）→ 停頓高舉提燈 → 重砸（重）
    windP = P(wind, {"Hips:loc": (0, 0.10, -0.05), "Chest": (-6, 0, -28), "UpperArm.R": (-40, 68, 0)})
    back = P(sweep, {"Chest": (8, 0, -16), "Spine": (6, 0, -8), "Head": (-4, 0, 12), "UpperArm.R": (-72, 58, 0), "ForeArm.R": (-18, 0, 0), "Fingers.R": (-30, 0, 0),
                     "Foot.R:ik": (0, -0.12, 0)})
    back2 = P(back, {"Chest": (8, 0, -24), "UpperArm.R": (-60, 72, 0), "Hips:loc": (0, -0.12, -0.10)})
    antH = P(ant, {"Hips:loc": (0, 0.11, 0.03), "UpperArm.L": (-122, -26, 0), "Staff": (120, 0, 0), "Chest": (-17, 0, -8)})
    hrec = {"Hips:loc": (0, -0.08, -0.04), "Spine": (6, 0, 0), "Chest": (4, 0, 0), "UpperArm.L": (-30, -6, 0), "Staff:plant": 0.6, "Foot.L:ik": (0, -0.1, 0.06)}
    A.action("Combo3", [(0, S), (8, wind, "io"), (12, windP, "io"), (15, sweep, "in3"), (18, follow, "out3"), (21, follow, "io"), (24, back, "in"), (28, back2, "out3"),
                        (40, TG, "io"), (48, ant, "io"), (52, antH, "io"), (56, hitp, "in3"), (59, reb, "out"), (70, hold, "io"), (82, hrec, "io"), (98, S, "io")],
             lag=LAG, hits=[(15, "Fingers.R"), (24, "Fingers.R"), (56, "Staff")])

    # ---------------- Delayed：提燈舉過頭頂後懸停約 0.8 秒（燈微微再升）→ 猛砸
    A.action("Delayed", [(0, S), (14, TG, "io"), (22, TG2, "io"), (30, ant, "io"), (42, antH, "io"), (52, P(antH, {"Staff": (116, 0, 0), "Hips:loc": (0, 0.12, 0.04)}), "io"),
                         (56, hitp, "in3"), (59, reb, "out"), (72, hold, "io"), (86, hrec, "io"), (102, S, "io")], lag=LAG, hits=[(56, "Staff")])

    # ---------------- Dash：後縮（起手短）→ 貼地滑行突進、右爪冰刺前掃 → 收回
    pullD = P(wind, {"Hips:loc": (0, 0.12, -0.12), "Spine": (2, 0, -16), "Foot.R:ik": (0, 0.10, 0)})
    lungeD = P(sweep, {"Hips:loc": (0, -0.52, -0.18), "Spine": (14, 0, 16), "UpperArm.R": (-92, -20, 0), "Foot.R:ik": (0, -0.46, 0), "Foot.L:ik": (0, -0.08, 0)})
    lungeD2 = P(follow, {"Hips:loc": (0, -0.56, -0.20), "Foot.R:ik": (0, -0.46, 0), "Foot.L:ik": (0, -0.08, 0)})
    A.action("Dash", [(0, S), (6, pullD, "io"), (10, lungeD, "in3"), (14, lungeD2, "out3"), (28, lungeD2, "io"),
                      (42, {"Hips:loc": (0, -0.2, -0.05), "Chest": (3, 0, 8), "UpperArm.R": (-20, -8, 0), "Foot.R:ik": (0, -0.18, 0.05)}, "io"), (58, S, "io")],
             lag=LAG, hits=[(10, "Fingers.R")])

    # ---------------- Roar：蜷身 → 雙臂大張仰首尖嘯（顫抖）→ 頓杖
    A.action("Roar", [(0, S), (12, curl, "io"), (17, P(curl, {"Hips:loc": (0, 0.02, -0.15), "Chest": (25, 0, 0)}), "io"), (21, burst, "in3"), (27, q1, "out"), (33, q2, "io"),
                      (39, q1, "io"), (45, q2, "io"), (55, P(AG, {"Staff:plant": 1.0}), "io"), (72, S, "io")],
             lag={"Fingers.R": 2, "SkirtF": 2, "SkirtB": 2})

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
def build_anim2():
    """第二版動畫：讀 model.blend → 全部動作（含新增片段）→ 匯出 export_raw/ 未壓縮 GLB＋命中時間表 → 每片段 10 格預覽。"""
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    arm = bpy.data.objects["Priest"]
    mesh = bpy.data.objects["PriestMesh"]
    L.clear_actions(arm)
    A = L.Animator(arm, base={"Staff:plant": 1.0})
    A.ground_r = {"*": 0.04, "Hips": 0.15, "Spine": 0.16, "Chest": 0.17, "Neck": 0.08, "Head": 0.10, "SkirtF": 0.02, "SkirtB": 0.02}
    A.ground_skip = {"Staff", "SkirtF", "SkirtB"}   # 袍襬可貼地，不拿來抬骨盆
    define_actions(A, L.sym)
    L.export_glb(OUT_GLB, arm, mesh)
    L.write_meta(A, NAME, os.path.join(HERE, "export_raw"))
    cam, _ = L.studio(HEIGHT)
    A.show(None, 0)
    L.render_actions(cam, A, TMP, NAME, HEIGHT, frames=10, extra=0.9, res=(400, 420), center=(0.1, 0.0, HEIGHT * 0.45))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


if STAGE == "anim2":
    build_anim2()

print("DONE", NAME, STAGE)
