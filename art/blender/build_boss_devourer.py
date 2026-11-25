"""Boss 5 噬語魔王（最終 Boss，原創造型）。頭頂約 3.0 m、角尖約 3.45 m。扭曲黑角王冠、骷髏臉寬顎、
失去光澤的金黑華麗板甲、破書頁與羊皮紙層疊的長披風、右手鋸齒巨劍、左手琥珀符文光的爪形護手。
用法：blender --background --factory-startup --python build_boss_devourer.py -- [model|anim|view|all]
造型依據：art/reference/boss5_word_devourer_king.jpg。臉朝 -Y、原點在腳底。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soul_creature_lib as L

ROOT = os.path.dirname(os.path.dirname(HERE))
NAME = "boss_devourer"
MODEL_BLEND = os.path.join(HERE, "source", NAME + "_model.blend")
OUT_BLEND = os.path.join(HERE, "source", NAME + ".blend")
OUT_GLB = os.path.join(ROOT, "public", "models", NAME + ".glb")
PREV = os.path.join(HERE, "preview")
TMP = os.path.join(PREV, "_frames")
BAKED = os.path.join(HERE, "textures", "baked", NAME)
HEIGHT = 3.5
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = argv[0] if argv else "all"
SWX, SWY, GRIP = -0.78, -0.36, 2.08   # 巨劍軸與握點
GLOW = (0.86, -0.44, 1.92)            # 左手符文光中心


# ================================================================== 材質
def armor_mat():
    """失去光澤的金黑板甲：黑鋼為底，稜線與大片區域露出暗金，凹縫積垢；左手附近有琥珀符文光。"""
    m = L.PMat("Armor")
    co = m.coord()
    gold = m.scan("Metal042B", 1.6)
    steel = m.scan("Metal046B", 1.4)
    pt = m.geom("Pointiness")
    gcol = m.mix(1.0, m.hsv(gold["Color"], s=0.85, v=0.75), (0.58, 0.40, 0.16), "MULTIPLY")
    gcol = m.mix(m.ramp(m.noise(5, 4), [(0.35, 0), (0.75, 0.8)]), gcol, (0.13, 0.085, 0.04))
    bcol = m.mix(0.6, (0.028, 0.028, 0.033), m.hsv(steel["Color"], s=0.3, v=0.3))
    patch = m.ramp(m.noise(1.3, 2, 0.45), [(0.40, 0), (0.56, 1)])                                  # 1 = 黑鋼區（邊界柔和）
    edge = m.ramp(pt, [(0.53, 0), (0.60, 1)])                                                     # 稜線磨出金色
    cav = m.ramp(pt, [(0.40, 1), (0.475, 0)])                                                     # 凹縫積垢
    isblack = m.math("MULTIPLY", patch, m.math("SUBTRACT", 1.0, m.math("MULTIPLY", edge, 0.9)))
    col = m.mix(isblack, gcol, bcol)
    col = m.mix(m.math("MULTIPLY", edge, 0.3), col, (0.72, 0.55, 0.26))
    scr = m.ramp(m.noise(2.0, 4, 0.8, vec=m.mapping(scale=(26, 26, 3))), [(0.60, 0), (0.68, 1)])  # 刮痕
    col = m.mix(m.math("MULTIPLY", scr, 0.35), col, (0.42, 0.33, 0.18))
    col = m.mix(cav, col, (0.022, 0.018, 0.014))
    rough = m.mix(isblack, m.ramp(gold["Roughness"], [(0, 0.56), (1, 0.74)]), m.ramp(steel["Roughness"], [(0, 0.60), (1, 0.78)]))
    rough = m.mix(cav, rough, 0.9)
    metal = m.math("SUBTRACT", 1.0, m.math("MULTIPLY", cav, 0.6))
    n = m.bump(gold["Displacement"], 0.3, 0.004)
    n = m.bump(m.noise(34, 2), 0.12, 0.003, normal=n)
    wv = m.mix(0.10, co, m.noise(4, 2, out="Color"), "ADD")
    ln = m.node("ShaderNodeVectorMath", operation="LENGTH")
    m.set(ln.inputs[0], m.mapping(loc=tuple(-c for c in GLOW)))
    near = m.ramp(ln.outputs["Value"], [(0.14, 1), (0.40, 0)])
    glyph = m.math("MULTIPLY", m.ramp(m.voronoi(24, "DISTANCE_TO_EDGE", vec=wv), [(0.0, 1), (0.06, 1), (0.12, 0)]), m.ramp(m.noise(9, 2), [(0.44, 0), (0.50, 1)]))
    rune = m.math("MULTIPLY", glyph, near)
    emit = m.ramp(m.math("ADD", rune, m.math("MULTIPLY", near, 0.10), clamp=True), [(0, (0, 0, 0)), (0.10, (0.22, 0.07, 0.0)), (0.6, (1.0, 0.50, 0.06)), (1, (1.0, 0.82, 0.35))])
    return m.finish(col, rough, metal, n, emit=emit, emit_strength=4.0)


def bone_mat(dark_pts):
    """dark_pts: [(x, y, z, 半徑)]：眼窩、鼻腔等要壓黑的位置。"""
    m = L.PMat("Skull")
    pt = m.geom("Pointiness")
    col = m.mix(m.noise(7, 4), (0.22, 0.18, 0.12), (0.42, 0.37, 0.27))
    col = m.mix(m.ramp(m.noise(2.5, 3), [(0.40, 0), (0.7, 0.7)]), col, (0.17, 0.12, 0.07))
    wv = m.mix(0.1, m.coord(), m.noise(6, 2, out="Color"), "ADD")
    crack = m.ramp(m.voronoi(13, "DISTANCE_TO_EDGE", vec=wv), [(0.0, 1), (0.012, 1), (0.03, 0)])
    crack = m.math("MULTIPLY", crack, m.ramp(m.noise(3, 2), [(0.48, 0), (0.56, 1)]))
    col = m.mix(crack, col, (0.04, 0.03, 0.02))
    col = m.mix(m.ramp(pt, [(0.40, 1), (0.50, 0)]), col, (0.02, 0.014, 0.01))
    col = m.mix(m.math("MULTIPLY", m.ramp(pt, [(0.53, 0), (0.60, 1)]), 0.3), col, (0.56, 0.51, 0.40))
    dark = None
    for x, y, z, r in dark_pts:
        ln = m.node("ShaderNodeVectorMath", operation="LENGTH")
        m.set(ln.inputs[0], m.mapping(loc=(-x, -y, -z)))
        d = m.ramp(m.math("DIVIDE", ln.outputs["Value"], r * 2), [(0.34, 1), (0.5, 0)])
        dark = d if dark is None else m.math("MAXIMUM", dark, d)
    col = m.mix(dark, col, (0.008, 0.006, 0.005))
    n = m.bump(m.noise(40, 3), 0.25, 0.003)
    n = m.bump(m.math("SUBTRACT", 1.0, crack), 0.8, 0.006, normal=n)
    return m.finish(col, m.mix(dark, m.ramp(m.noise(9, 2), [(0.3, 0.55), (0.7, 0.8)]), 0.95), 0.0, n)


def horn_mat():
    m = L.PMat("Horn")
    pt = m.geom("Pointiness")
    z = m.sep(m.coord())[2]
    col = m.mix(m.noise(5, 4), (0.018, 0.016, 0.015), (0.06, 0.048, 0.04))
    col = m.mix(m.math("MULTIPLY", m.ramp(pt, [(0.53, 0), (0.60, 1)]), 0.4), col, (0.20, 0.16, 0.12))
    col = m.mix(m.ramp(pt, [(0.42, 1), (0.48, 0)]), col, (0.01, 0.01, 0.01))
    grain = m.noise(3.0, 3, vec=m.mapping(scale=(40, 40, 6)))
    n = m.bump(grain, 0.5, 0.006)
    return m.finish(col, m.ramp(grain, [(0.3, 0.55), (0.7, 0.8)]), 0.0, n)


def chain_mat():
    m = L.PMat("Chain")
    ch = m.scan("Chainmail002", 5.0, maps=("Color", "Roughness", "Displacement"))
    col = m.mix(1.0, ch["Color"], (0.42, 0.40, 0.38), "MULTIPLY")
    return m.finish(col, m.ramp(ch["Roughness"], [(0, 0.4), (1, 0.7)]), 0.85, m.bump(ch["Displacement"], 1.0, 0.01))


def cloth_mat():
    m = L.PMat("DarkCloth")
    fab = m.scan("Fabric029", 2.2)
    col = m.mix(1.0, m.ramp(fab["Color"], [(0.0, 0.5), (0.5, 1.2)]), (0.10, 0.05, 0.045), "MULTIPLY")
    col = m.mix(m.ramp(m.noise(3, 4), [(0.4, 0), (0.7, 0.7)]), col, (0.04, 0.03, 0.03))
    return m.finish(col, 0.9, 0.0, m.bump(fab["Displacement"], 0.8, 0.006))


def leather_mat():
    m = L.PMat("Leather")
    le = m.scan("Leather028", 2.5)
    col = m.hsv(le["Color"], s=0.7, v=0.55)
    return m.finish(col, 0.6, 0.0, m.bump(le["Displacement"], 0.8, 0.005))


def paper_mat():
    """書頁：只用 puv，才能讓同版面的書頁共用同一塊貼圖。puv 的整數部分是版面編號。"""
    m = L.PMat("Pages")
    uv = m.puv()
    u, v = m.math("FRACT", m.sep(uv)[0]), m.math("FRACT", m.sep(uv)[1])
    pap = m.scan("Paper006", 1.0, vec=m.mapping(uv, scale=(0.9, 0.9, 1)), maps=("Color", "Displacement"), box=False)
    base = m.mix(1.0, m.ramp(pap["Color"], [(0.2, 0.75), (0.8, 1.05)]), (0.80, 0.66, 0.43), "MULTIPLY")
    stain = m.ramp(m.noise(3.0, 4, vec=uv), [(0.35, 0), (0.7, 1)])
    base = m.mix(m.math("MULTIPLY", stain, 0.55), base, (0.42, 0.29, 0.14))
    # 文字行
    lines = m.ramp(m.math("FRACT", m.math("MULTIPLY", v, 19.0)), [(0.30, 0), (0.42, 1), (0.72, 1), (0.84, 0)])
    words = m.ramp(m.noise(1.0, 2, 0.8, vec=m.mapping(uv, scale=(34, 190, 1))), [(0.40, 0), (0.48, 1)])
    marg = m.math("MULTIPLY", m.math("MULTIPLY", m.ramp(u, [(0.10, 0), (0.14, 1)]), m.ramp(u, [(0.84, 1), (0.90, 0)])),
                  m.math("MULTIPLY", m.ramp(v, [(0.08, 0), (0.10, 1)]), m.ramp(v, [(0.88, 1), (0.92, 0)])))
    ink = m.math("MULTIPLY", m.math("MULTIPLY", lines, words), marg)
    ink = m.math("MULTIPLY", ink, m.ramp(m.noise(2.0, 2, vec=uv), [(0.25, 0.3), (0.6, 1.0)]))
    col = m.mix(m.math("MULTIPLY", ink, 0.82), base, (0.10, 0.07, 0.05))
    # 焦黑破邊
    d = m.math("MINIMUM", m.math("MINIMUM", u, m.math("SUBTRACT", 1.0, u)), m.math("MINIMUM", v, m.math("SUBTRACT", 1.0, v)))
    burn = m.ramp(m.math("ADD", d, m.math("MULTIPLY", m.noise(9, 3, vec=uv), 0.10)), [(0.05, 1), (0.13, 0)])
    col = m.mix(burn, col, (0.16, 0.09, 0.04))
    char = m.ramp(m.math("ADD", d, m.math("MULTIPLY", m.noise(14, 3, vec=uv), 0.05)), [(0.015, 1), (0.04, 0)])
    col = m.mix(char, col, (0.03, 0.02, 0.015))
    return m.finish(col, 0.88, 0.0, m.bump(pap["Displacement"], 0.4, 0.004))


def blade_mat():
    m = L.PMat("Blade")
    met = m.scan("Metal013", 1.8)
    uv = m.puv()
    u = m.sep(uv)[0]
    col = m.mix(0.5, (0.16, 0.16, 0.17), m.hsv(met["Color"], s=0.5, v=0.55))
    edge = m.ramp(m.math("ABSOLUTE", m.math("SUBTRACT", u, 0.5)), [(0.33, 0), (0.46, 1)])
    col = m.mix(m.math("MULTIPLY", edge, 0.6), col, (0.46, 0.46, 0.47))
    rust = m.ramp(m.noise(5, 5, 0.7), [(0.52, 0), (0.66, 1)])
    col = m.mix(m.math("MULTIPLY", rust, 0.7), col, (0.20, 0.09, 0.04))
    rough = m.mix(rust, m.mix(edge, 0.55, 0.3), 0.85)
    metal = m.math("SUBTRACT", 1.0, m.math("MULTIPLY", rust, 0.7))
    n = m.bump(met["Displacement"], 1.0, 0.008)
    return m.finish(col, rough, metal, n)


def amber_mat():
    m = L.PMat("AmberEye")
    return m.finish((0.8, 0.35, 0.05), 0.4, 0.0, None, emit=(1.0, 0.42, 0.04), emit_strength=5.0)


# ================================================================== 建模
def cloak_pt(a, z, off=0.0):
    """披風基準面：a=0 在正後方(+Y)，a>0 往 +X。"""
    t = max(0.0, (2.50 - z) / 2.25)
    rx = 0.56 + 0.44 * t + off
    ry = 0.36 + 0.60 * t ** 0.9 + off
    return Vector((math.sin(a) * rx, 0.06 + math.cos(a) * ry, z))


def cloak_w(co, uvt=None):
    z = co.z
    w = {}
    c0 = L._sst((z - 2.20) / 0.25)
    c1 = L._sst((z - 1.65) / 0.35) * (1 - c0)
    c2 = L._sst((z - 0.95) / 0.35) * (1 - c0 - c1)
    c3 = max(0.0, 1 - c0 - c1 - c2)
    w["Chest"], w["Cloak1"], w["Cloak2"], w["Cloak3"] = c0, c1, c2, c3
    return w


def build_model():
    L.reset()
    rnd = random.Random(5)
    _p = lambda x, y, z: tuple(Vector((0, 0, 2.68)) + (Vector((x, y, z)) - Vector((0, 0, 2.68))) * 0.80)
    M_armor, M_horn = armor_mat(), horn_mat()
    M_bone = bone_mat([(*_p(0.095, -0.17, 2.825), 0.078), (*_p(-0.095, -0.17, 2.825), 0.078), (*_p(0, -0.225, 2.76), 0.04)])
    M_chain, M_cloth, M_leather, M_paper, M_blade, M_amber = chain_mat(), cloth_mat(), leather_mat(), paper_mat(), blade_mat(), amber_mat()
    AR, SK, HN, D = [], [], [], []

    # ------------------------------------------------ 板甲（體素融合成高模）
    def lamed(name, pts, radii, lames, step=0.085, **kw):
        """沿路徑做出一片片向下疊的甲片（半徑鋸齒階梯）。"""
        sm = L.resample([Vector(q) for q in pts], [Vector((r, r)) if isinstance(r, (int, float)) else Vector(r) for r in radii], 12)
        P2, R2 = [], []
        for q, r, t in sm:
            f = 1 + step * (1 - (t * lames) % 1.0)
            P2.append(q)
            R2.append((r[0] * f, r[1] * f))
        return L.loft(name, P2, R2, sub=1, **kw)

    def keel(a, t):  # 胸甲中央稜線（-Y 方向）與背脊
        return 1 + 0.075 * math.exp(-((a - 1.5 * math.pi) / 0.22) ** 2) * math.sin(min(1, t * 1.3) * math.pi) + 0.03 * math.exp(-((a - 0.5 * math.pi) / 0.3) ** 2)

    AR.append(L.loft("Cuirass", [(0, 0.02, 1.86), (0, 0, 2.08), (0, -0.01, 2.30), (0, 0, 2.46), (0, 0.01, 2.57)],
                     [(0.345, 0.265), (0.44, 0.305), (0.50, 0.335), (0.44, 0.30), (0.21, 0.20)], segs=28, sub=6, shape=keel,
                     bones=[("Spine", 0), ("Chest", 0.3)], blend=0.2))
    AR.append(lamed("Faulds", [(0, 0.02, 1.98), (0, 0.02, 1.80), (0, 0.02, 1.64), (0, 0.02, 1.48)], [(0.355, 0.275), (0.37, 0.285), (0.42, 0.32), (0.46, 0.35)], 5, 0.07, segs=28,
                    bones=[("Spine", 0), ("Hips", 0.45)], blend=0.2))
    for s in (1, -1):
        AR.append(L.ellipsoid("PecPlate", (0.20 * s, -0.20, 2.29), (0.24, 0.13, 0.19), rot=(6, 0, 10 * s), bones="Chest"))
        AR.append(L.ellipsoid("BackPlate", (0.2 * s, 0.22, 2.24), (0.24, 0.13, 0.26), bones="Chest"))
    AR.append(lamed("Gorget", [(0, 0, 2.47), (0, 0, 2.56), (0, -0.005, 2.64)], [(0.30, 0.27), (0.22, 0.21), (0.17, 0.17)], 3, 0.10, segs=20, caps=("flat", "flat"), bones=[("Chest", 0), ("Neck", 0.7)], blend=0.3))
    col = [[cloak_pt(math.radians(a), 2.52 + 0.20 * v) * 1.0 for a in range(-115, 116, 23)] for v in (0, 0.5, 1.0)]
    for row, v in zip(col, (0, 0.5, 1.0)):
        for q in row:
            q.x *= 0.50 + 0.10 * v
            q.y = (q.y - 0.06) * 0.72 + 0.02 + 0.03 * v
    AR.append(L.sheet("CollarGuard", col, thick=0.03, bones="Chest"))
    for s, sx in ((1, ".L"), (-1, ".R")):
        ua, fa, hd = "UpperArm" + sx, "ForeArm" + sx, "Hand" + sx
        Sh = Vector((0.52 * s, 0, 2.42))
        El = Vector((0.71 * s, 0.03, 1.92))
        Wr = Vector((0.84, -0.32, 1.86)) if s > 0 else Vector((-0.75, -0.25, 2.02))
        # 肩甲：扁平大蓋＋向下疊的甲片＋立領鰭
        AR.append(L.ellipsoid("PauldronTop" + sx, (0.56 * s, 0, 2.50), (0.26, 0.27, 0.13), rot=(0, -22 * s, 0), bones=lambda co, t, ua=ua: {"Chest": 0.45, ua: 0.55}, segs=18, rings=10))
        AR.append(lamed("PauldronLames" + sx, [(0.60 * s, 0, 2.48), (0.70 * s, 0.005, 2.34), (0.755 * s, 0.01, 2.14)], [(0.20, 0.25), (0.185, 0.235), (0.15, 0.19)], 4, 0.10, segs=18,
                        bones=[("Chest", 0), (ua, 0.15)], blend=0.2))
        AR.append(L.loft("PauldronRidge" + sx, [(0.42 * s, 0, 2.60), (0.60 * s, 0, 2.625), (0.76 * s, 0, 2.50)], [(0.03, 0.05), (0.03, 0.05), (0.02, 0.03)], segs=8, ref=(0, 1, 0), bones=ua))
        AR.append(L.loft("PauldronFin" + sx, [(0.36 * s, 0.0, 2.58), (0.39 * s, 0.0, 2.74), (0.45 * s, 0.0, 2.88)], [(0.03, 0.16), (0.022, 0.11), (0.006, 0.02)], segs=10, sub=3,
                         caps=("flat", "round"), bones="Chest"))
        AR.append(L.loft("Rerebrace" + sx, [Sh + Vector((0.04 * s, 0, -0.10)), Sh.lerp(El, 0.55), El], [0.15, 0.135, 0.12], segs=14, bones=ua))
        AR.append(L.ellipsoid("Couter" + sx, El + Vector((0.02 * s, 0.03, 0)), (0.135, 0.15, 0.135), bones=[(fa, 0)], segs=14, rings=8))
        AR.append(L.loft("CouterSpike" + sx, [El + Vector((0.06 * s, 0.10, 0)), El + Vector((0.13 * s, 0.30, 0.03))], [0.055, 0.006], segs=6, sub=2, caps=("flat", "point"), bones=fa))
        AR.append(lamed("Vambrace" + sx, [El.lerp(Wr, 0.12), El.lerp(Wr, 0.5), Wr], [0.115, 0.125, 0.105], 3, 0.08, segs=14, bones=[(fa, 0), (hd, 0.97)], blend=0.08))
        AR.append(L.loft("VambraceRidge" + sx, [El.lerp(Wr, 0.15) + Vector((0.11 * s, 0.02, 0.02)), Wr + Vector((0.10 * s, 0.0, 0.02))], [(0.02, 0.035), (0.015, 0.03)], segs=6, sub=3, bones=fa))
        # 腿甲
        th, shn, ft = "Thigh" + sx, "Shin" + sx, "Foot" + sx
        Hp, Kn, An = Vector((0.20 * s, 0, 1.58)), Vector((0.24 * s, -0.05, 0.86)), Vector((0.24 * s, 0.03, 0.16))
        AR.append(L.loft("Cuisse" + sx, [Hp, Hp.lerp(Kn, 0.45) + Vector((0.02 * s, -0.03, 0)), Kn], [(0.19, 0.21), (0.175, 0.20), 0.14], segs=14, bones=[("Hips", 0), (th, 0.12)], blend=0.12,
                         shape=lambda a, t: 1 + 0.06 * math.exp(-((a - 1.5 * math.pi) / 0.3) ** 2)))
        AR.append(L.ellipsoid("Tasset" + sx, (0.25 * s, -0.225, 1.33), (0.18, 0.045, 0.23), rot=(-8, 0, -6 * s), bones=lambda co, t, th=th: {"Hips": 0.4, th: 0.6}, segs=14, rings=8))
        AR.append(L.ellipsoid("TassetSide" + sx, (0.44 * s, 0.02, 1.35), (0.05, 0.20, 0.22), rot=(0, 8 * s, 0), bones=lambda co, t, th=th: {"Hips": 0.4, th: 0.6}, segs=14, rings=8))
        AR.append(L.ellipsoid("Poleyn" + sx, Kn + Vector((0, -0.06, 0.0)), (0.15, 0.14, 0.165), bones=shn, segs=14, rings=8))
        AR.append(L.loft("PoleynFin" + sx, [Kn + Vector((0.12 * s, -0.02, 0.0)), Kn + Vector((0.26 * s, 0.06, 0.04))], [(0.03, 0.10), (0.004, 0.01)], segs=8, sub=2, caps=("flat", "round"), bones=shn))
        AR.append(L.loft("Greave" + sx, [Kn, Kn.lerp(An, 0.35) + Vector((0, 0.03, 0)), Kn.lerp(An, 0.8), An], [0.135, (0.14, 0.16), 0.11, 0.115], segs=14, bones=[(th, 0), (shn, 0.1), (ft, 0.97)], blend=0.1,
                         shape=lambda a, t: 1 + 0.09 * math.exp(-((a - 1.5 * math.pi) / 0.2) ** 2)))
        x = 0.24 * s
        AR.append(lamed("Sabaton" + sx, [(x, 0.05, 0.22), (x, 0.01, 0.105), (x * 1.06, -0.18, 0.085), (x * 1.09, -0.33, 0.065), (x * 1.10, -0.42, 0.04)],
                        [0.12, (0.125, 0.10), (0.125, 0.085), (0.095, 0.06), (0.02, 0.015)], 6, 0.09, segs=12, bones=[(shn, 0), (ft, 0.2)], blend=0.15))
    # 右手握拳（握劍）
    gc = Vector((SWX, SWY, GRIP))
    AR.append(L.ellipsoid("Fist.R", gc + Vector((0.01, 0.01, 0)), (0.10, 0.11, 0.095), bones="Hand.R", segs=14, rings=8))
    for k in range(4):
        AR.append(L.ellipsoid(f"Knuckle{k}", gc + Vector((-0.035, -0.09, -0.066 + 0.044 * k)), (0.05, 0.035, 0.024), bones="Hand.R", segs=8, rings=5))
    AR.append(L.ellipsoid("ThumbR", gc + Vector((0.07, -0.06, 0.07)), (0.04, 0.06, 0.035), bones="Hand.R", segs=8, rings=5))
    # 左手爪形護手（掌心朝上，五爪上勾）
    palm = Vector((0.87, -0.46, 1.875))
    AR.append(L.ellipsoid("Palm.L", palm, (0.10, 0.11, 0.045), rot=(-10, 0, 0), bones="Hand.L", segs=14, rings=8))
    for k, ang in enumerate((-150, -105, -60, -15, 60)):
        a = math.radians(ang)
        d = Vector((math.cos(a), math.sin(a), 0))
        b = palm + d * 0.085
        ln = 0.9 if k == 4 else 1.0
        p1 = b + d * 0.08 * ln + Vector((0, 0, 0.07))
        p2 = b + d * 0.07 * ln + Vector((0, 0, 0.17 * ln))
        p3 = b - d * 0.02 + Vector((0, 0, 0.29 * ln))
        AR.append(L.loft(f"Claw{k}", [b, p1, p2, p3], [0.038, 0.034, 0.026, 0.004], segs=8, sub=3, caps=("round", "point"), bones=[("Hand.L", 0), ("Fingers.L", 0.25)], blend=0.2))

    armor = L.organic("ArmorBody", AR, M_armor, voxel=0.008, tris=17800, smooth=8, uv_angle=80)

    # ------------------------------------------------ 骷髏頭（寬顎）
    SK.append(L.ellipsoid("Cranium", (0, 0.035, 2.85), (0.19, 0.20, 0.185), bones="Head", segs=20, rings=12))
    SK.append(L.loft("Brow", [(-0.19, -0.10, 2.90), (-0.11, -0.195, 2.905), (0, -0.215, 2.885), (0.11, -0.195, 2.905), (0.19, -0.10, 2.90)], [0.024, 0.026, 0.022, 0.026, 0.024], segs=8, ref=(0, 0, 1), bones="Head"))
    SK.append(L.loft("Nasal", [(0, -0.225, 2.86), (0, -0.25, 2.815), (0, -0.242, 2.79)], [0.03, 0.024, 0.014], segs=8, bones="Head"))
    for s in (1, -1):
        SK.append(L.loft("Cheek", [(0.205 * s, -0.06, 2.78), (0.18 * s, -0.16, 2.755), (0.10 * s, -0.21, 2.73)], [0.032, 0.03, 0.026], segs=8, ref=(0, 0, 1), bones="Head"))
        SK.append(L.ellipsoid("Temple", (0.185 * s, -0.02, 2.80), (0.04, 0.10, 0.07), bones="Head", segs=8, rings=6))
    mx = [(-0.155, -0.07, 2.705), (-0.12, -0.195, 2.70), (0, -0.258, 2.70), (0.12, -0.195, 2.70), (0.155, -0.07, 2.705)]
    SK.append(L.loft("Maxilla", mx, [(0.026, 0.036)] * 5, segs=8, ref=(0, 0, 1), bones="Head"))
    for i, p in enumerate(L.polyline(mx, 18)[1:-1]):
        SK.append(L.loft("ToothU", [p + Vector((0, -0.008, -0.015)), p + Vector((0, -0.012, -0.07 - 0.03 * (i % 3 == 0)))], [0.013, 0.004], segs=5, sub=1, caps=("flat", "point"), bones="Head"))
    md = [(-0.205, 0.02, 2.745), (-0.21, -0.04, 2.60), (-0.165, -0.19, 2.555), (0, -0.275, 2.54), (0.165, -0.19, 2.555), (0.21, -0.04, 2.60), (0.205, 0.02, 2.745)]
    SK.append(L.loft("Mandible", md, [(0.024, 0.04), (0.028, 0.045), (0.03, 0.036), (0.036, 0.042), (0.03, 0.036), (0.028, 0.045), (0.024, 0.04)], segs=8, sub=5, ref=(0, 0, 1), bones="Jaw"))
    SK.append(L.ellipsoid("Chin", (0, -0.262, 2.525), (0.07, 0.04, 0.045), bones="Jaw", segs=10, rings=6))
    for i, p in enumerate(L.polyline(md[1:-1], 22)[3:-3]):
        SK.append(L.loft("ToothL", [p + Vector((0, 0.004, 0.015)), p + Vector((0, 0.01, 0.07 + 0.03 * (i % 4 == 1)))], [0.013, 0.004], segs=5, sub=1, caps=("flat", "point"), bones="Jaw"))
    PIV, HS = Vector((0, 0, 2.68)), 0.80

    def rescale(objs, f):
        Mx = Matrix.Translation(PIV) @ Matrix.Scale(f, 4) @ Matrix.Translation(-PIV)
        for o in objs:
            o.data.transform(Mx)

    rescale(SK, HS)
    skull = L.organic("SkullHead", SK, M_bone, voxel=0.005, tris=4200, smooth=4)

    # ------------------------------------------------ 扭曲黑角王冠
    def twist(a, t):
        return 1 + 0.085 * math.sin(2 * a + 30 * t) * (1 - t * 0.6)

    for s in (1, -1):
        HN.append(L.loft("HornBig", [(0.15 * s, 0.02, 2.90), (0.36 * s, 0.05, 2.87), (0.55 * s, 0.03, 2.97), (0.62 * s, -0.02, 3.17), (0.54 * s, -0.07, 3.36), (0.41 * s, -0.10, 3.47)],
                         [0.09, 0.085, 0.075, 0.058, 0.036, 0.005], segs=12, sub=6, caps=("flat", "point"), shape=twist, bones="Head"))
        HN.append(L.loft("HornMid", [(0.09 * s, 0.05, 2.98), (0.15 * s, 0.08, 3.15), (0.24 * s, 0.06, 3.30), (0.21 * s, -0.02, 3.43)], [0.055, 0.046, 0.032, 0.004], segs=10, sub=5,
                         caps=("flat", "point"), shape=twist, bones="Head"))
        HN.append(L.loft("HornSmall", [(0.05 * s, -0.09, 2.99), (0.055 * s, -0.12, 3.10), (0.04 * s, -0.17, 3.19)], [0.032, 0.024, 0.004], segs=8, sub=4, caps=("flat", "point"), bones="Head"))
        HN.append(L.loft("HornBack", [(0.12 * s, 0.15, 2.92), (0.20 * s, 0.26, 3.02), (0.22 * s, 0.30, 3.16)], [0.04, 0.03, 0.004], segs=8, sub=4, caps=("flat", "point"), shape=twist, bones="Head"))
    rescale(HN, 0.93)
    horns = L.organic("Horns", HN, M_horn, voxel=0.006, tris=2800, smooth=3)

    # ------------------------------------------------ 直接建模的零件
    def add(o, sharp=None):
        if sharp:
            L.hard(o, sharp)
        D.append(o)
        return o

    for s in (1, -1):
        ep = PIV + (Vector((0.092 * s, -0.150, 2.825)) - PIV) * HS
        add(L.ellipsoid("Eye", ep, (0.012, 0.01, 0.011), bones="Head", mat=M_amber, segs=8, rings=5))
    # 鎖子甲：頸、腰裙、肘彎
    add(L.loft("Coif", [(0, 0.01, 2.52), (0, 0.01, 2.64), (0, 0.02, 2.76)], [0.15, 0.125, 0.135], segs=14, sub=3, caps=("open", "open"), bones=[("Chest", 0), ("Neck", 0.3), ("Head", 0.85)], blend=0.3, mat=M_chain))

    def skirt_w(co, t):
        k = L._sst((1.50 - co.z) / 0.3) * 0.6
        return {"Hips": 1 - k, ("Thigh.L" if co.x > 0 else "Thigh.R"): k}

    add(L.loft("MailSkirt", [(0, 0.02, 1.58), (0, 0.02, 1.40), (0, 0.02, 1.12)], [(0.40, 0.31), (0.44, 0.34), (0.47, 0.37)], segs=28, sub=4, caps=("open", "open"), bones=skirt_w, mat=M_chain,
               shape=lambda a, t: 1 + 0.03 * t * math.sin(9 * a)))
    # 腰帶、扣環、鐵鍊、前擋布
    belt = [[Vector((math.sin(a) * (0.425 + 0.004 * k), 0.02 - math.cos(a) * (0.325 + 0.004 * k), z)) for a in [2 * math.pi * j / 28 for j in range(28)]] for k, z in enumerate((1.685, 1.59))]
    add(L.sheet("Belt", belt, thick=0.03, wrap=True, bones="Hips", mat=M_leather))
    add(L.box("Buckle", (0, -0.335, 1.637), (0.13, 0.035, 0.12), bones="Hips", mat=M_blade, bevel=0.012), 40)
    for pts in ([(-0.36, -0.19, 1.60), (-0.20, -0.36, 1.36), (0.05, -0.40, 1.24), (0.30, -0.30, 1.42), (0.40, -0.12, 1.60)],
                [(-0.20, -0.30, 1.60), (-0.12, -0.38, 1.20), (0.0, -0.40, 1.02), (0.16, -0.36, 1.26), (0.24, -0.29, 1.60)]):
        add(L.loft("ChainLoop", pts, [0.017] * 5, segs=5, sub=4, bones=skirt_w, mat=M_chain))
    tab = []
    for i in range(9):
        v = i / 8
        z = 1.60 - 0.88 * v
        tab.append([Vector((x * (1 + 0.15 * v), -0.345 - 0.07 * v - 0.02 * math.cos(x * 9), z)) for x in (-0.17, -0.085, 0, 0.085, 0.17)])
    for j in range(5):
        tab[-1][j].z += rnd.uniform(-0.10, 0.08)
        tab[-2][j].z += rnd.uniform(-0.03, 0.03)
    add(L.sheet("Tabard", tab, bones=[("Hips", 0), ("Tabard", 0.12)], blend=0.2, mat=M_cloth))
    # 披風底布（暗色破布）
    rows, cols = 10, 16
    cape = []
    for i in range(rows + 1):
        z = 2.42 - (2.42 - 0.30) * i / rows
        cape.append([cloak_pt(math.radians(-118 + 236 * j / cols), z, -0.035) for j in range(cols + 1)])
    for j in range(cols + 1):
        cape[-1][j].z += rnd.uniform(-0.05, 0.22)
    add(L.sheet("CapeBase", cape, bones=cloak_w, mat=M_cloth))
    # 書頁：一排排像瓦片一樣疊在披風上；同版面的書頁共用 UV
    PW, PH, NT = 0.25, 0.35, 12
    n_pages = 0
    z = 2.44
    while z > 0.42:
        arc = math.radians(236) * (0.56 + 0.44 * (2.50 - z) / 2.25)
        n = int(arc / 0.185)
        for k in range(n):
            a = math.radians(-116 + 232 * (k + 0.5 + rnd.uniform(-0.3, 0.3)) / n)
            zz = z + rnd.uniform(-0.05, 0.05)
            O = cloak_pt(a, zz, 0.01 + rnd.uniform(0, 0.03))
            e = 0.01
            T = (cloak_pt(a + e, zz) - cloak_pt(a - e, zz)).normalized()
            Dn = (cloak_pt(a, zz - e) - cloak_pt(a, zz + e)).normalized()
            N = T.cross(Dn).normalized()
            if N.dot(Vector((O.x, O.y - 0.06, 0))) < 0:
                N = -N
            yaw = math.radians(rnd.uniform(-24, 24))
            tilt = math.radians(rnd.uniform(5, 20))
            w, h = PW * rnd.uniform(0.85, 1.15), PH * rnd.uniform(0.8, 1.15)
            T2 = T * math.cos(yaw) + Dn * math.sin(yaw)
            D2 = (Dn * math.cos(yaw) - T * math.sin(yaw)) * math.cos(tilt) + N * math.sin(tilt)
            curl = rnd.uniform(-0.02, 0.05)
            tpl = rnd.randrange(NT)
            g = [[O + T2 * ((u - 0.5) * w) + D2 * (v * h) + N * (curl * math.sin(math.pi * v) + 0.012 * (u - 0.5) ** 2) for u in (0, 0.5, 1)] for v in (0, 0.5, 1)]
            pg = L.sheet("Page", g, mat=M_paper, bones=cloak_w)
            uvl, puv = pg.data.uv_layers["UVMap"], pg.data.uv_layers["puv"]
            flip = rnd.random() < 0.3
            for li in range(len(uvl.data)):
                pu, pv = puv.data[li].uv
                if flip:
                    pu, pv = 1 - pu, 1 - pv
                uvl.data[li].uv = (pu * PW, pv * PH)
                puv.data[li].uv = (pu * 0.998 + 0.001 + tpl, pv * 0.998 + 0.001 + tpl * 3)
            pg["uvg"] = tpl
            D.append(pg)
            n_pages += 1
        z -= 0.150
    print("pages", n_pages)

    # 鋸齒巨劍
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    puv = bm.loops.layers.uv.new("puv")
    secs = []
    n = 44
    for i in range(n + 1):
        t = i / n
        zc = 1.85 * (1 - t)
        w = 0.14 + 0.045 * math.sin(t * 2.6)
        if t > 0.86:
            w *= max(0.0, (1 - t) / 0.14) ** 0.8
        tooth = 0.045 if i % 3 == 0 else 0.0
        wl = w + (tooth if 0.06 < t < 0.9 else 0) + rnd.uniform(-0.008, 0.008)
        wr = w + (0.03 if (i % 5 == 2 and 0.1 < t < 0.9) else 0) - (0.05 if i in (13, 14, 27) else 0) + rnd.uniform(-0.008, 0.008)
        th = 0.024 * (1 if t < 0.9 else max(0.1, (1 - t) / 0.1))
        if i == n:
            wl = wr = 0.002
        secs.append([bm.verts.new((SWX - wl, SWY, zc)), bm.verts.new((SWX, SWY - th, zc)), bm.verts.new((SWX + wr, SWY, zc)), bm.verts.new((SWX, SWY + th, zc))])
    for i in range(n):
        for k in range(4):
            f = bm.faces.new((secs[i][k], secs[i][(k + 1) % 4], secs[i + 1][(k + 1) % 4], secs[i + 1][k]))
            for lp in f.loops:
                c = lp.vert.co
                lp[uv].uv = (c.x - SWX + (0.4 if k >= 2 else 0), c.z)
                lp[puv].uv = ((c.x - SWX) / 0.42 + 0.5, c.z / 1.85)
    bm.faces.new(secs[0])
    blade = L._finish_mesh("Blade", bm, M_blade, smooth=False)
    L.assign(blade, "Sword")
    add(blade)

    def sw(o, sharp=None):
        L.assign(o, "Sword")
        return add(o, sharp)

    sw(L.box("Guard", (SWX, SWY, 1.875), (0.56, 0.085, 0.075), mat=M_blade, bevel=0.015), 40)
    for s in (1, -1):
        sw(L.loft("GuardProng", [(SWX + 0.27 * s, SWY, 1.875), (SWX + 0.33 * s, SWY, 1.80)], [0.035, 0.006], segs=5, sub=1, caps=("flat", "point"), mat=M_blade), 30)
    sw(L.loft("GripM", [(SWX, SWY, 1.90), (SWX, SWY, 2.10), (SWX, SWY, 2.30)], [0.036, 0.04, 0.034], segs=8, sub=2, caps=("flat", "flat"), mat=M_leather))
    sw(L.ellipsoid("Pommel", (SWX, SWY, 2.345), (0.065, 0.065, 0.06), mat=M_blade, segs=10, rings=6))

    # ------------------------------------------------ 骨架
    B = [("Root", (0, 0, 0), (0, 0.4, 0), None),
         ("Hips", (0, 0.02, 1.60), (0, 0.02, 1.80), "Root"), ("Spine", (0, 0.02, 1.80), (0, 0, 2.08), "Hips"), ("Chest", (0, 0, 2.08), (0, 0, 2.50), "Spine"),
         ("Neck", (0, 0, 2.52), (0, -0.01, 2.68), "Chest"), ("Head", (0, -0.01, 2.68), (0, -0.02, 2.95), "Neck"), ("Jaw", (0, 0.016, 2.72), (0, -0.216, 2.576), "Head"),
         ("UpperArm.R", (-0.52, 0, 2.42), (-0.71, 0.03, 1.92), "Chest"), ("ForeArm.R", (-0.71, 0.03, 1.92), (-0.75, -0.25, 2.02), "UpperArm.R"),
         ("Hand.R", (-0.75, -0.25, 2.02), (SWX, SWY, GRIP), "ForeArm.R"), ("Sword", (SWX, SWY, GRIP), (SWX, SWY, 2.40), "Hand.R"),
         ("UpperArm.L", (0.52, 0, 2.42), (0.71, 0.03, 1.92), "Chest"), ("ForeArm.L", (0.71, 0.03, 1.92), (0.84, -0.32, 1.86), "UpperArm.L"),
         ("Hand.L", (0.84, -0.32, 1.86), (0.87, -0.46, 1.88), "ForeArm.L"), ("Fingers.L", (0.87, -0.46, 1.88), (0.88, -0.50, 2.06), "Hand.L"),
         ("Cloak1", (0, 0.42, 2.40), (0, 0.58, 1.75), "Chest"), ("Cloak2", (0, 0.58, 1.75), (0, 0.76, 1.05), "Cloak1"), ("Cloak3", (0, 0.76, 1.05), (0, 0.92, 0.35), "Cloak2"),
         ("Tabard", (0, -0.35, 1.50), (0, -0.42, 0.78), "Hips")]
    for s, sx in ((1, ".L"), (-1, ".R")):
        B += [("Thigh" + sx, (0.20 * s, 0, 1.58), (0.24 * s, -0.05, 0.86), "Hips"), ("Shin" + sx, (0.24 * s, -0.05, 0.86), (0.24 * s, 0.03, 0.16), "Thigh" + sx),
              ("Foot" + sx, (0.24 * s, 0.03, 0.16), (0.26 * s, -0.36, 0.05), "Shin" + sx)]
    arm = L.make_armature("Devourer", B)
    orgs = [(armor[0], armor[1], armor[2], M_armor), (skull[0], skull[1], skull[2], M_bone), (horns[0], horns[1], horns[2], M_horn)]
    L.assemble("DevourerMesh", arm, orgs, D, BAKED, size=1024, emit_strength=4.0, emit_size=512, extrusion=0.02, ao_dist=0.6, uv_margin=0.006, normal_strength=0.6)
    bpy.ops.wm.save_as_mainfile(filepath=MODEL_BLEND)


# ================================================================== 動作
def define_actions(A, sym):
    """9 個手刻動作。'Sword:plant'=1 時巨劍劍尖自動拄地；Telegraph 首尾相同可循環；Attack／Attack2 第 1 格 = Telegraph 姿勢。"""
    for sx in (".L", ".R"):
        A.add_leg("Thigh" + sx, "Shin" + sx, ["Foot" + sx], "Foot" + sx + ":ik")
    A.add_plant("Sword", "Sword:plant")

    def P(*ds):
        out = {}
        for d in ds:
            out.update(d)
        return out

    S = {}
    LAG = {"Head": 2, "Neck": 1, "Cloak1": 2, "Cloak2": 5, "Cloak3": 8, "Tabard": 4, "Fingers.L": 3, "Hand.L": 2, "Jaw": 2}

    # ---------------- Idle：沉重呼吸、左爪符文手緩緩開合、披風微擺（循環）
    i1 = {"Hips:loc": (0, 0, -0.025), "Spine": (2, 0, 0), "Chest": (-4, 0, 1.5), "Neck": (2, 0, 0), "Head": (3, 0, 5), "Jaw": (5, 0, 0),
          "UpperArm.L": (-3, -3, 0), "ForeArm.L": (-6, 0, 0), "Fingers.L": (-14, 0, 0), "Cloak1": (2, 0, 0), "Cloak2": (2, 0, 2), "Cloak3": (3, 0, 3), "Tabard": (2, 0, 0)}
    i2 = {"Hips:loc": (0, 0, 0.006), "Chest": (1.5, 0, -1), "Head": (-2, 0, -5), "Fingers.L": (12, 0, 0), "UpperArm.L": (2, 2, 0), "Cloak2": (-1, 0, -2), "Cloak3": (-2, 0, -3), "Tabard": (-1, 0, 0)}
    A.action("Idle", [(1, S), (38, i1), (76, i2), (110, S)], lag=LAG)

    # ---------------- Enter：垂首佇立→緩緩抬頭、符文手亮起→拔劍→重重頓劍怒吼
    bow = {"Hips:loc": (0, 0.02, -0.10), "Spine": (14, 0, 0), "Chest": (18, 0, 0), "Neck": (16, 0, 0), "Head": (26, 0, 0),
           "UpperArm.L": (22, 8, 0), "ForeArm.L": (55, 0, 0), "Fingers.L": (25, 0, 0), "Cloak1": (-14, 0, 0), "Cloak2": (-6, 0, 0)}
    look = {"Hips:loc": (0, 0.01, -0.03), "Spine": (4, 0, 0), "Chest": (2, 0, 0), "Neck": (2, 0, 0), "Head": (-4, 0, 0), "Jaw": (6, 0, 0),
            "UpperArm.L": (-8, -6, 0), "ForeArm.L": (-10, 0, 0), "Fingers.L": (-24, 0, 0)}
    draw = {"Hips:loc": (0, 0.04, 0.03), "Spine": (-5, 0, -4), "Chest": (-8, 0, -6), "Head": (-6, 0, 6), "Jaw": (10, 0, 0),
            "UpperArm.R": (-42, 12, 0), "ForeArm.R": (-12, 0, 0), "Sword": (52, 0, 0), "Sword:plant": 0.0,
            "UpperArm.L": (-14, -24, 0), "ForeArm.L": (-18, 0, 0), "Fingers.L": (-30, 0, 0), "Cloak1": (6, 0, 0)}
    slam = {"Hips:loc": (0, -0.02, -0.14), "Spine": (8, 0, 0), "Chest": (8, 0, 0), "Neck": (-8, 0, 0), "Head": (-20, 0, 0), "Jaw": (38, 0, 0),
            "UpperArm.L": (10, -46, 0), "ForeArm.L": (-30, 0, 0), "Hand.L": (-20, 0, 0), "Fingers.L": (-36, 0, 0),
            "Cloak1": (20, 0, 0), "Cloak2": (16, 0, 0), "Cloak3": (12, 0, 0), "Tabard": (-14, 0, 0)}
    roar2 = P(slam, {"Head": (-23, 0, 6), "Chest": (6, 0, 3), "Jaw": (32, 0, 0), "Hips:loc": (0, -0.02, -0.11)})
    A.action("Enter", [(1, bow), (30, bow), (62, look), (74, draw), (77, draw, "L"), (80, slam), (88, roar2), (96, slam), (104, roar2), (124, S)], lag=LAG)

    # ---------------- Telegraph：巨劍高舉過右肩、左爪前伸鎖定（可循環保持）
    TG = {"Hips:loc": (0, 0.10, -0.08), "Hips": (0, 0, -8), "Spine": (-5, 0, -10), "Chest": (-8, 0, -14), "Neck": (4, 0, 10), "Head": (6, 0, 14), "Jaw": (12, 0, 0),
          "UpperArm.R": (-122, 22, 0), "ForeArm.R": (-40, 0, 0), "Sword": (-46, 0, 0), "Sword:plant": 0.0,
          "UpperArm.L": (-48, -10, 0), "ForeArm.L": (-14, 0, 0), "Hand.L": (-30, 0, 0), "Fingers.L": (-30, 0, 0),
          "Cloak1": (8, 0, 0), "Cloak2": (4, 0, 0), "Tabard": (4, 0, 0)}
    TG2 = P(TG, {"Hips:loc": (0, 0.12, -0.10), "Chest": (-10, 0, -16), "UpperArm.R": (-128, 24, 0), "Sword": (-52, 0, 0), "Jaw": (18, 0, 0), "Fingers.L": (-16, 0, 0)})
    A.action("Telegraph", [(1, TG), (10, TG2), (20, TG), (30, TG2), (40, TG)], lag={"Fingers.L": 2, "Cloak2": 2, "Cloak3": 4})

    # ---------------- Attack：過肩重劈（左腳前踏，劍砸地）
    ant = P(TG2, {"Chest": (-14, 0, -20), "Spine": (-8, 0, -12), "UpperArm.R": (-136, 26, 0), "Sword": (-62, 0, 0), "Hips:loc": (0, 0.16, -0.06), "Foot.L:ik": (0, -0.15, 0.14)})
    hitp = {"Hips:loc": (0, -0.40, -0.30), "Hips": (6, 0, 8), "Spine": (16, 0, 10), "Chest": (20, 0, 14), "Neck": (-10, 0, -8), "Head": (-18, 0, -10), "Jaw": (30, 0, 0),
            "UpperArm.R": (-62, -12, 0), "ForeArm.R": (22, 0, 0), "Sword": (-40, 0, 0), "Sword:plant": 0.0,
            "UpperArm.L": (30, -30, 0), "ForeArm.L": (-10, 0, 0), "Fingers.L": (20, 0, 0),
            "Cloak1": (-20, 0, 0), "Cloak2": (10, 0, 0), "Cloak3": (14, 0, 0), "Tabard": (-18, 0, 0), "Foot.L:ik": (0, -0.5, 0)}
    reb = P(hitp, {"Sword": (-46, 0, 0), "Hips:loc": (0, -0.40, -0.26), "Chest": (17, 0, 14)})
    hold = P(hitp, {"Sword": (-41, 0, 0), "Hips:loc": (0, -0.39, -0.29), "Jaw": (14, 0, 0), "Cloak2": (0, 0, 0), "Cloak3": (0, 0, 0)})
    A.action("Attack", [(1, TG), (8, ant, "L"), (13, hitp), (17, reb), (21, hold), (34, hold),
                        (50, {"Hips:loc": (0, -0.18, -0.10), "Spine": (6, 0, 0), "Chest": (6, 0, 0), "UpperArm.R": (-30, 4, 0), "Sword:plant": 0.7, "Foot.L:ik": (0, -0.25, 0.10)}), (66, S)], lag=LAG)

    # ---------------- Attack2：符文爪高舉→跪砸地面（右手拄劍支撐）
    lift = {"Hips:loc": (0, 0.10, 0.02), "Spine": (-8, 0, 6), "Chest": (-12, 0, 10), "Head": (-4, 0, -6), "Jaw": (16, 0, 0),
            "UpperArm.L": (-172, -22, 0), "ForeArm.L": (-30, 0, 0), "Hand.L": (-30, 0, 0), "Fingers.L": (-36, 0, 0),
            "UpperArm.R": (-10, 6, 0), "Sword:plant": 1.0, "Cloak1": (10, 0, 0)}
    smash = {"Hips:loc": (0, -0.36, -0.74), "Hips": (16, 0, 0), "Spine": (26, 0, -8), "Chest": (26, 0, -12), "Neck": (-16, 0, 0), "Head": (-30, 0, 8), "Jaw": (30, 0, 0),
             "UpperArm.L": (-52, 10, 0), "ForeArm.L": (58, 0, 0), "Hand.L": (30, 0, 0), "Fingers.L": (-10, 0, 0),
             "UpperArm.R": (-30, 20, 0), "ForeArm.R": (-10, 0, 0), "Sword:plant": 1.0,
             "Cloak1": (-40, 0, 0), "Cloak2": (10, 0, 0), "Cloak3": (16, 0, 0), "Tabard": (-30, 0, 0), "Foot.L:ik": (0, -0.42, 0), "Foot.R:ik": (0, 0.50, 0.02, 40)}
    smash2 = P(smash, {"Hips:loc": (0, -0.36, -0.69), "Chest": (22, 0, -12), "Cloak2": (0, 0, 0), "Cloak3": (0, 0, 0)})
    A.action("Attack2", [(1, TG), (12, P(lift, {"Foot.L:ik": (0, -0.12, 0.12)}), "L"), (18, smash), (22, smash2), (26, smash), (40, smash),
                         (56, {"Hips:loc": (0, -0.15, -0.25), "Spine": (10, 0, 0), "Chest": (8, 0, 0), "UpperArm.L": (-20, 0, 0), "Foot.L:ik": (0, -0.2, 0.06), "Foot.R:ik": (0, 0.2, 0.10)}), (70, S)], lag=LAG)

    # ---------------- Hit
    hit = {"Hips:loc": (0, 0.10, -0.04), "Spine": (-6, 0, 5), "Chest": (-9, 0, 8), "Neck": (4, 0, -5), "Head": (10, 0, -14), "Jaw": (18, 0, 0),
           "UpperArm.L": (14, -14, 0), "Fingers.L": (-24, 0, 0), "Cloak1": (10, 0, 0), "Cloak2": (6, 0, 0), "Tabard": (-8, 0, 0)}
    A.action("Hit", [(1, S, "L"), (4, hit), (10, {"Chest": (3, 0, -2), "Head": (-3, 0, 4), "Cloak1": (-4, 0, 0)}), (20, S)], lag={"Cloak2": 2, "Cloak3": 4, "Tabard": 2})

    # ---------------- Stagger：被彈反，劍被震開、後仰→單膝跪地拄劍喘息→撐起
    rec = {"Hips:loc": (0, 0.36, -0.14), "Hips": (-6, 0, -6), "Spine": (-14, 0, 0), "Chest": (-18, 0, 6), "Neck": (-10, 0, 0), "Head": (-22, 0, 10), "Jaw": (34, 0, 0),
           "UpperArm.R": (-40, 78, 0), "ForeArm.R": (-20, 0, 0), "Sword": (0, 70, 0), "Sword:plant": 0.0,
           "UpperArm.L": (-30, -66, 0), "ForeArm.L": (-30, 0, 0), "Fingers.L": (-36, 0, 0),
           "Cloak1": (26, 0, 0), "Cloak2": (16, 0, 0), "Cloak3": (10, 0, 0), "Tabard": (-20, 0, 0), "Foot.R:ik": (0, 0.3, 0.14)}
    kneel = {"Hips:loc": (0, 0.34, -0.70), "Hips": (6, 0, 0), "Spine": (16, 0, 0), "Chest": (20, 0, -6), "Neck": (10, 0, 0), "Head": (26, 0, -6), "Jaw": (20, 0, 0),
             "UpperArm.R": (-34, 8, 0), "ForeArm.R": (-10, 0, 0), "Sword:plant": 1.0,
             "UpperArm.L": (10, 4, 0), "ForeArm.L": (50, 0, 0), "Fingers.L": (24, 0, 0),
             "Cloak1": (-22, 0, 0), "Cloak2": (-6, 0, 0), "Tabard": (-10, 0, 0), "Foot.R:ik": (0, 0.72, 0.02, 45), "Foot.L:ik": (0, 0.06, 0)}
    pant = P(kneel, {"Hips:loc": (0, 0.34, -0.66), "Chest": (16, 0, -6), "Head": (20, 0, 6), "Jaw": (10, 0, 0)})
    A.action("Stagger", [(1, S, "L"), (7, rec), (12, P(rec, {"Hips:loc": (0, 0.44, -0.2), "Head": (-14, 0, 12)})), (26, kneel), (38, pant), (50, kneel), (60, pant),
                         (72, {"Hips:loc": (0, 0.2, -0.25), "Spine": (10, 0, 0), "Chest": (8, 0, 0), "Foot.R:ik": (0, 0.36, 0.12)}), (84, S)], lag=LAG)

    # ---------------- PhaseShift：蜷身蓄力→爆發，雙臂大張、舉劍、仰首怒吼、披風揚起→顫抖維持→頓劍
    curl = {"Hips:loc": (0, 0.02, -0.22), "Spine": (16, 0, 0), "Chest": (22, 0, 0), "Neck": (12, 0, 0), "Head": (24, 0, 0),
            "UpperArm.L": (10, 20, 0), "ForeArm.L": (30, 0, 0), "Fingers.L": (34, 0, 0), "Cloak1": (-20, 0, 0), "Cloak2": (-8, 0, 0)}
    burst = {"Hips:loc": (0, 0.08, 0.05), "Spine": (-10, 0, 0), "Chest": (-16, 0, 0), "Neck": (-12, 0, 0), "Head": (-26, 0, 0), "Jaw": (44, 0, 0),
             "UpperArm.R": (-30, 70, 0), "ForeArm.R": (-10, 0, 0), "Sword": (0, 98, 0), "Sword:plant": 0.0,
             "UpperArm.L": (-34, -78, 0), "ForeArm.L": (-34, 0, 0), "Hand.L": (-20, 0, 0), "Fingers.L": (-40, 0, 0),
             "Cloak1": (34, 0, 0), "Cloak2": (24, 0, 0), "Cloak3": (16, 0, 0), "Tabard": (-22, 0, 0)}
    q1 = P(burst, {"Head": (-23, 0, 5), "Chest": (-14, 0, 2), "Jaw": (38, 0, 0), "Fingers.L": (-28, 0, 0), "Cloak2": (18, 0, 4), "Cloak3": (10, 0, 6)})
    q2 = P(burst, {"Head": (-27, 0, -5), "Chest": (-17, 0, -2), "Cloak2": (26, 0, -4), "Cloak3": (20, 0, -6), "Sword": (0, 104, 0)})
    A.action("PhaseShift", [(1, S), (18, curl), (28, P(curl, {"Hips:loc": (0, 0.02, -0.26), "Chest": (25, 0, 0)}), "L"), (34, burst), (40, q1), (46, q2), (52, q1), (58, q2), (64, q1), (70, q2), (76, burst),
                            (88, {"UpperArm.R": (-40, 14, 0), "Sword": (50, 0, 0), "Sword:plant": 0.0, "Chest": (-4, 0, 0)}, "L"), (92, {"Hips:loc": (0, 0, -0.10), "Chest": (6, 0, 0), "Cloak1": (10, 0, 0)}), (104, S)],
             lag={"Fingers.L": 2, "Cloak2": 2, "Cloak3": 4, "Tabard": 2})

    # ---------------- Die：受創→拄劍硬撐→雙膝跪地、垂首→向前撲倒（最後一格停住）
    d1 = P(hit, {"Hips:loc": (0, 0.2, -0.08), "Head": (-18, 0, -12), "Jaw": (36, 0, 0), "Chest": (-14, 0, 8)})
    d2 = {"Hips:loc": (0, -0.04, -0.18), "Spine": (10, 0, -3), "Chest": (14, 0, -4), "Head": (18, 0, 6), "Jaw": (16, 0, 0), "UpperArm.L": (16, 6, 0), "ForeArm.L": (40, 0, 0), "Fingers.L": (20, 0, 0),
          "Cloak1": (-14, 0, 0)}
    knees = {"Hips:loc": (0, -0.02, -0.78), "Hips": (4, 0, 0), "Spine": (10, 0, 0), "Chest": (14, 0, 0), "Neck": (12, 0, 0), "Head": (28, 0, 0), "Jaw": (18, 0, 0),
             "UpperArm.R": (-36, 6, 0), "ForeArm.R": (-12, 0, 0), "UpperArm.L": (24, 8, 0), "ForeArm.L": (62, 0, 0), "Fingers.L": (30, 0, 0),
             "Cloak1": (-14, 0, 0), "Cloak2": (-4, 0, 0), "Tabard": (-8, 0, 0), "Foot.R:ik": (0, 0.62, 0.02, 45), "Foot.L:ik": (0, 0.56, 0.02, 45)}
    sway = P(knees, {"Hips:loc": (0.04, -0.02, -0.76), "Chest": (10, 3, 3), "Head": (22, 0, 8)})
    prone = {"Hips:loc": (0, -0.78, -1.22), "Hips": (66, 0, 0), "Spine": (12, 0, 0), "Chest": (8, 0, 0), "Neck": (-16, 0, 0), "Head": (-24, 0, 28), "Jaw": (14, 0, 0),
             "UpperArm.R": (-70, 30, 0), "ForeArm.R": (-20, 0, 0), "UpperArm.L": (-80, -30, 0), "ForeArm.L": (20, 0, 0), "Fingers.L": (30, 0, 0),
             "Cloak1": (-52, 0, 0), "Cloak2": (-22, 0, 0), "Cloak3": (-8, 0, 0), "Tabard": (-50, 0, 0), "Foot.R:ik": (0, 0.62, 0.02, 70), "Foot.L:ik": (0, 0.56, 0.02, 70)}
    A.action("Die", [(1, S, "L"), (6, d1), (22, d2), (48, knees), (60, sway), (72, knees), (82, P(knees, {"Hips": (16, 0, 0), "Hips:loc": (0, -0.14, -0.80), "Head": (34, 0, 0)}), "L"),
                     (96, prone), (100, P(prone, {"Hips:loc": (0, -0.78, -1.17), "Head": (-18, 0, 28)})), (106, prone), (124, prone)],
             lag={"Cloak2": 3, "Cloak3": 6, "Fingers.L": 2})


def render_all(A=None):
    cam, _ = L.studio(HEIGHT)
    if A:
        A.show(None, 1)
    L.render_views(cam, TMP, NAME, HEIGHT, center=(0, 0.1, HEIGHT * 0.49), extra=0.95)
    L.aim(cam, (0.05, 0, 2.55), 3.6, -25, 4)
    L.render(os.path.join(TMP, NAME + "_close.png"), (900, 760))
    return cam


def build_anim():
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    arm = bpy.data.objects["Devourer"]
    mesh = bpy.data.objects["DevourerMesh"]
    L.clear_actions(arm)
    A = L.Animator(arm, base={"Sword:plant": 1.0})
    define_actions(A, L.sym)
    L.export_glb(OUT_GLB, arm, mesh)
    cam = render_all(A)
    FM = {"Enter": [1, 40, 70, 80, 124], "Attack": [1, 8, 13, 17, 66], "Attack2": [1, 12, 18, 30, 70], "Hit": [1, 4, 9, 14, 20],
          "Stagger": [1, 7, 22, 44, 84], "PhaseShift": [1, 22, 34, 58, 104], "Die": [1, 22, 48, 96, 124]}
    L.render_actions(cam, A, TMP, NAME, HEIGHT, extra=1.0, res=(480, 480), center=(0, 0.0, HEIGHT * 0.42), frames_map=FM)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


if STAGE in ("model", "all"):
    build_model()
if STAGE == "view":
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    render_all()
if STAGE in ("anim", "all"):
    build_anim()
print("DONE", NAME, STAGE)
