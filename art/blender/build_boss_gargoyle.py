"""Boss 2 教堂石像鬼（原創造型）。站高約 2.4 m、駝背壯碩、半收石翼、鎚頭尾、裂縫透餘燼橘光。
用法：blender --background --factory-startup --python build_boss_gargoyle.py -- [model|anim|all]
  model：建模→體素融合高模→減面→權重→烘焙圖集→存 source/boss_gargoyle_model.blend
  anim ：讀 model.blend→手刻 9 個動作→匯出 public/models/boss_gargoyle.glb→渲染預覽
造型依據：art/reference/boss2_cathedral_gargoyle.jpg。臉朝 -Y、原點在腳底。
"""
import bpy, sys, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soul_creature_lib as L

ROOT = os.path.dirname(os.path.dirname(HERE))
NAME = "boss_gargoyle"
MODEL_BLEND = os.path.join(HERE, "source", NAME + "_model.blend")
OUT_BLEND = os.path.join(HERE, "source", NAME + ".blend")
OUT_GLB = os.path.join(ROOT, "public", "models", NAME + ".glb")
PREV = os.path.join(HERE, "preview")
TMP = os.path.join(PREV, "_frames")
BAKED = os.path.join(HERE, "textures", "baked", NAME)
HEIGHT = 2.75  # 含翼尖
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = argv[0] if argv else "all"


# ================================================================== 材質
def stone_mat():
    m = L.PMat("Stone")
    co = m.coord()
    rock = m.scan("Rock042L", 0.9)
    rock2 = m.scan("Rock023", 0.6)
    moss = m.scan("Moss002", 1.6, maps=("Color",))
    col = m.mix(m.ramp(m.noise(1.3, 3), [(0.4, 0), (0.6, 1)]), rock["Color"], rock2["Color"])
    col = m.hsv(col, s=0.5, v=0.95)
    col = m.mix(1.0, col, (0.80, 0.80, 0.74), "MULTIPLY")
    # 凹處積垢、稜線磨亮
    pt = m.ramp(m.geom("Pointiness"), [(0.44, 0.35), (0.5, 1.0), (0.56, 1.45)])
    col = m.mix(1.0, col, pt, "MULTIPLY")
    # 雨痕：垂直方向拉長的雜訊
    streak = m.ramp(m.noise(1.0, 3, vec=m.mapping(scale=(7, 7, 0.9))), [(0.35, 0.72), (0.65, 1.0)])
    col = m.mix(1.0, col, streak, "MULTIPLY")
    # 地衣與苔：偏向朝上的面
    up = m.sep(m.geom("Normal"))[2]
    mm = m.math("ADD", m.math("MULTIPLY", m.noise(2.4, 5, 0.65), 0.8), m.math("MULTIPLY", up, 0.22))
    mossmask = m.ramp(mm, [(0.50, 0), (0.60, 1)])
    col = m.mix(m.math("MULTIPLY", mossmask, 0.8), col, m.mix(1.0, moss["Color"], (0.55, 0.60, 0.40), "MULTIPLY"))
    lich = m.math("MULTIPLY", m.ramp(m.noise(9, 2), [(0.66, 0), (0.71, 1)]), m.ramp(m.noise(1.2, 2, vec=m.mapping(loc=(3, 1, 7))), [(0.45, 0), (0.6, 1)]))
    col = m.mix(m.math("MULTIPLY", lich, 0.55), col, (0.60, 0.47, 0.12))
    # 裂縫：扭曲的 Voronoi 邊緣
    wv = m.mix(0.35, co, m.noise(2.2, 2, out="Color"), "ADD")
    ed = m.voronoi(2.1, "DISTANCE_TO_EDGE", vec=wv)
    pres = m.ramp(m.noise(1.5, 2, vec=m.mapping(loc=(5, 2, 9))), [(0.50, 0), (0.60, 1)])
    wide = m.math("MULTIPLY", m.ramp(ed, [(0.0, 1), (0.008, 1), (0.026, 0)]), pres)
    core = m.math("MULTIPLY", m.ramp(ed, [(0.0, 1), (0.004, 1), (0.013, 0)]), pres)
    col = m.mix(wide, col, (0.035, 0.03, 0.028))
    # 餘燼光：胸口／肩背較集中，其他地方零星
    ln = m.node("ShaderNodeVectorMath", operation="LENGTH")
    m.set(ln.inputs[0], m.mapping(loc=(0, 0.12, -1.80), scale=(0.9, 1.0, 1.0)))
    chest = m.ramp(ln.outputs["Value"], [(0.25, 1), (0.75, 0)])
    spots = m.ramp(m.noise(0.9, 2, vec=m.mapping(loc=(11, 4, 2))), [(0.58, 0), (0.68, 0.8)])
    spots = m.math("MULTIPLY", spots, m.ramp(m.math("MULTIPLY", m.sep(co)[2], 0.4), [(0.52, 0), (0.64, 1)]))  # z 1.3~1.6 m 以上才有零星餘燼
    glow = m.math("MULTIPLY", core, m.math("MAXIMUM", chest, spots))
    halo = m.math("MULTIPLY", m.math("MULTIPLY", wide, m.math("MAXIMUM", chest, spots)), 0.35)
    emit = m.ramp(m.math("ADD", glow, halo, clamp=True), [(0.0, (0, 0, 0)), (0.35, (0.75, 0.10, 0.0)), (0.8, (1.0, 0.42, 0.05)), (1.0, (1.0, 0.75, 0.3))])
    rough = m.ramp(rock["Roughness"], [(0.0, 0.72), (1.0, 0.97)])
    n = m.bump(rock["Displacement"], 1.0, 0.022)
    n = m.bump(m.voronoi(13, "SMOOTH_F1", vec=wv), 0.35, 0.012, normal=n)
    n = m.bump(m.math("SUBTRACT", 1.0, wide), 1.0, 0.014, normal=n)
    return m.finish(col, rough, 0.0, n, emit=emit, emit_strength=4.0)


def ember_mat():
    m = L.PMat("EmberEye")
    return m.finish((0.9, 0.35, 0.06), 0.4, 0.0, None, emit=(1.0, 0.5, 0.1), emit_strength=6.0)


# ================================================================== 建模
def build_model():
    L.reset()
    stone = stone_mat()
    ember = ember_mat()
    P = []  # 石身零件

    def add(o):
        P.append(o)
        return o

    # --- 軀幹（駝背前傾）
    add(L.loft("Torso", [(0, 0.16, 1.00), (0, 0.12, 1.18), (0, 0.06, 1.42), (0, 0.0, 1.65), (0, -0.04, 1.88), (0, -0.12, 2.08), (0, -0.28, 2.16)],
               [(0.24, 0.20), (0.34, 0.27), (0.30, 0.23), (0.40, 0.30), (0.52, 0.37), (0.46, 0.32), (0.22, 0.20)], segs=20, sub=5,
               bones=[("Hips", 0), ("Spine1", 0.30), ("Spine2", 0.56), ("Neck", 0.95)], blend=0.16))
    # 背脊隆起與棘
    add(L.ellipsoid("Hump", (0, 0.14, 1.98), (0.34, 0.20, 0.24), rot=(-20, 0, 0), bones="Spine2"))
    for i, (y, z, h) in enumerate([(0.24, 2.10, 0.13), (0.30, 1.88, 0.12), (0.30, 1.66, 0.10), (0.30, 1.44, 0.08)]):
        add(L.loft(f"Spike{i}", [(0, y - 0.10, z - 0.02), (0, y + h, z + h * 0.7)], [(0.05, 0.07), 0.008], segs=6, sub=2, caps=("flat", "point"),
                   bones="Spine2" if i < 2 else "Spine1"))
    # 胸、腹、斜方
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.ellipsoid("Pec" + sx, (0.21 * s, -0.27, 1.86), (0.26, 0.15, 0.19), rot=(8, 0, 12 * s), bones="Spine2"))
        add(L.ellipsoid("Trap" + sx, (0.30 * s, -0.04, 2.13), (0.28, 0.22, 0.14), rot=(0, -22 * s, 0), bones="Spine2"))
        add(L.ellipsoid("Lat" + sx, (0.40 * s, 0.14, 1.72), (0.15, 0.20, 0.28), bones="Spine2"))
        for k, (z, y) in enumerate([(1.40, -0.135), (1.53, -0.20), (1.66, -0.26)]):
            add(L.ellipsoid(f"Ab{k}" + sx, (0.095 * s, y, z), (0.09, 0.05, 0.062), bones="Spine1", segs=10, rings=6))
        add(L.ellipsoid("Rib" + sx, (0.26 * s, -0.14, 1.60), (0.10, 0.12, 0.16), bones="Spine1"))
        add(L.ellipsoid("Glute" + sx, (0.20 * s, 0.26, 1.12), (0.19, 0.18, 0.20), bones="Hips"))

    # --- 頸與頭（喙、角、耳鰭、眉脊）
    add(L.loft("NeckM", [(0, -0.20, 2.13), (0, -0.34, 2.14), (0, -0.46, 2.13)], [(0.19, 0.17), (0.15, 0.15), (0.14, 0.15)], segs=14,
               bones=[("Spine2", 0), ("Neck", 0.25), ("Head", 0.85)], blend=0.3))
    add(L.loft("Skull", [(0, -0.38, 2.15), (0, -0.50, 2.16), (0, -0.64, 2.11), (0, -0.79, 2.01), (0, -0.90, 1.91), (0, -0.94, 1.79)],
               [(0.17, 0.155), (0.195, 0.18), (0.175, 0.145), (0.11, 0.10), (0.058, 0.065), (0.014, 0.022)], segs=16, sub=5, ref=(1, 0, 0),
               caps=("round", "point"), bones="Head"))
    add(L.loft("JawM", [(0, -0.46, 2.00), (0, -0.61, 1.955), (0, -0.76, 1.89), (0, -0.85, 1.84)], [(0.14, 0.075), (0.115, 0.06), (0.07, 0.045), (0.012, 0.012)],
               segs=12, caps=("round", "point"), bones=[("Head", 0), ("Jaw", 0.15)], blend=0.2))
    add(L.ellipsoid("Crest", (0, -0.50, 2.27), (0.06, 0.16, 0.07), rot=(-12, 0, 0), bones="Head", segs=10, rings=6))
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.ellipsoid("Brow" + sx, (0.105 * s, -0.65, 2.18), (0.095, 0.08, 0.045), rot=(18, 0, -20 * s), bones="Head", segs=10, rings=6))
        add(L.ellipsoid("Cheek" + sx, (0.12 * s, -0.56, 2.05), (0.06, 0.09, 0.06), bones="Head", segs=10, rings=6))
        add(L.loft("Horn" + sx, [(0.12 * s, -0.47, 2.26), (0.20 * s, -0.43, 2.40), (0.24 * s, -0.33, 2.50), (0.21 * s, -0.21, 2.52)],
                   [0.072, 0.058, 0.036, 0.006], segs=8, caps=("flat", "point"), bones="Head"))
        add(L.loft("HornS" + sx, [(0.05 * s, -0.56, 2.25), (0.07 * s, -0.55, 2.33), (0.07 * s, -0.50, 2.37)], [0.03, 0.022, 0.005], segs=6,
                   caps=("flat", "point"), bones="Head"))
        ear = [L.polyline([(0.14 * s, -0.42, 2.17), (0.27 * s, -0.33, 2.22), (0.36 * s, -0.24, 2.20)], 5),
               L.polyline([(0.14 * s, -0.42, 2.06), (0.25 * s, -0.33, 2.08), (0.36 * s, -0.24, 2.20)], 5)]
        add(L.sheet("Ear" + sx, [[ear[0][i], ear[0][i].lerp(ear[1][i], 0.5), ear[1][i]] for i in range(5)], thick=0.035, bones="Head"))

    # --- 手臂（長臂、巨爪）
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.ellipsoid("Delt" + sx, (0.64 * s, -0.03, 2.00), (0.25, 0.23, 0.24), bones=[("UpperArm" + sx, 0)]))
        add(L.loft("Arm" + sx, [(0.62 * s, -0.04, 1.98), (0.77 * s, 0.0, 1.70), (0.86 * s, 0.04, 1.42), (0.90 * s, -0.07, 1.18), (0.88 * s, -0.19, 0.97), (0.87 * s, -0.25, 0.86)],
                   [0.20, (0.17, 0.19), 0.13, (0.15, 0.165), (0.095, 0.115), (0.13, 0.075)], segs=14, sub=5,
                   bones=[("UpperArm" + sx, 0), ("ForeArm" + sx, 0.42), ("Hand" + sx, 0.86)], blend=0.14))
        add(L.ellipsoid("Bicep" + sx, (0.79 * s, -0.07, 1.70), (0.13, 0.14, 0.22), rot=(5, 0, 15 * s), bones="UpperArm" + sx))
        add(L.ellipsoid("Elbow" + sx, (0.88 * s, 0.11, 1.41), (0.085, 0.09, 0.09), bones="ForeArm" + sx, segs=10, rings=6))
        palm = Vector((0.87 * s, -0.26, 0.85))
        for k, (dx, dy) in enumerate([(-0.095, -0.01), (-0.04, -0.075), (0.035, -0.08), (0.098, -0.03)]):
            b = palm + Vector((s * dx, dy, -0.04))
            mid = b + Vector((s * dx * 0.9, dy * 1.3, -0.16))
            tip = mid + Vector((s * dx * 0.1, 0.055, -0.20))
            add(L.loft(f"Finger{k}" + sx, [b, mid, mid.lerp(tip, 0.55) + Vector((0, -0.02, 0)), tip], [0.048, 0.042, 0.03, 0.005], segs=7, sub=3,
                       caps=("round", "point"), bones=[("Hand" + sx, 0), ("Fingers" + sx, 0.22)], blend=0.2))
        tb = palm + Vector((-0.11 * s, 0.035, 0.03))
        add(L.loft("Thumb" + sx, [tb, tb + Vector((-0.07 * s, -0.03, -0.09)), tb + Vector((-0.06 * s, -0.02, -0.21))], [0.045, 0.038, 0.005], segs=7, sub=3,
                   caps=("round", "point"), bones=[("Hand" + sx, 0), ("Fingers" + sx, 0.4)], blend=0.2))

    # --- 反關節腿
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.loft("Leg" + sx, [(0.24 * s, 0.10, 1.18), (0.31 * s, -0.08, 0.97), (0.36 * s, -0.25, 0.75), (0.355 * s, -0.06, 0.57), (0.335 * s, 0.15, 0.41),
                                (0.33 * s, 0.07, 0.22), (0.34 * s, -0.09, 0.085)],
                   [(0.22, 0.25), (0.21, 0.24), (0.145, 0.155), (0.15, 0.185), (0.115, 0.13), (0.105, 0.115), (0.135, 0.09)], segs=14, sub=5,
                   bones=[("Thigh" + sx, 0), ("Shin" + sx, 0.34), ("Foot" + sx, 0.67), ("Toe" + sx, 0.97)], blend=0.10))
        add(L.ellipsoid("Quad" + sx, (0.34 * s, -0.16, 0.98), (0.15, 0.15, 0.25), rot=(-35, 0, 0), bones="Thigh" + sx))
        add(L.ellipsoid("Knee" + sx, (0.365 * s, -0.33, 0.75), (0.08, 0.07, 0.09), bones="Shin" + sx, segs=10, rings=6))
        add(L.ellipsoid("Calf" + sx, (0.35 * s, 0.05, 0.60), (0.12, 0.14, 0.17), rot=(40, 0, 0), bones="Shin" + sx))
        add(L.loft("Hock" + sx, [(0.335 * s, 0.17, 0.42), (0.335 * s, 0.27, 0.47)], [0.06, 0.012], segs=6, sub=2, caps=("flat", "point"), bones="Foot" + sx))
        ball = Vector((0.34 * s, -0.10, 0.075))
        for k, a in enumerate((-28, 0, 28)):
            d = Vector((math.sin(math.radians(a)) * s, -math.cos(math.radians(a)), 0))
            add(L.loft(f"Toe{k}" + sx, [ball + d * 0.03, ball + d * 0.19 + Vector((0, 0, -0.005)), ball + d * 0.33 + Vector((0, 0, 0.0)), ball + d * 0.46 + Vector((0, 0, -0.065))],
                       [0.07, 0.062, 0.045, 0.005], segs=7, sub=3, caps=("round", "point"), bones=[("Foot" + sx, 0), ("Toe" + sx, 0.15)], blend=0.2))
        add(L.loft("Spur" + sx, [ball + Vector((0, 0.03, 0)), ball + Vector((0, 0.15, -0.02)), ball + Vector((0, 0.22, -0.065))], [0.05, 0.035, 0.004], segs=6, sub=2,
                   caps=("round", "point"), bones="Foot" + sx))

    # --- 尾巴與石鎚頭
    tail = [(0, 0.28, 1.08), (0, 0.60, 0.80), (0.05, 0.95, 0.45), (0.25, 1.25, 0.22), (0.55, 1.42, 0.15), (0.82, 1.42, 0.17)]
    add(L.loft("Tail", tail, [0.16, 0.135, 0.11, 0.095, 0.085, 0.08], segs=12, sub=5,
               bones=[("Hips", 0), ("Tail1", 0.06), ("Tail2", 0.28), ("Tail3", 0.52), ("Tail4", 0.74), ("Tail5", 0.95)], blend=0.14))
    hc = Vector((1.02, 1.40, 0.245))
    add(L.ellipsoid("Hammer", hc, (0.24, 0.23, 0.23), bones="Tail5", segs=16, rings=10))
    import random
    rnd = random.Random(7)
    for k in range(11):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.7, 1))).normalized()
        add(L.ellipsoid(f"Knob{k}", hc + d * 0.21, (0.085, 0.085, 0.085), bones="Tail5", segs=8, rings=5))

    # --- 石翼（半收）
    for s, sx in ((1, ".L"), (-1, ".R")):
        R = Vector((0.22 * s, 0.22, 2.00))
        E = Vector((0.62 * s, 0.50, 2.30))
        W = Vector((0.80 * s, 0.36, 2.74))
        T = [Vector((1.14 * s, 0.50, 1.30)), Vector((0.93 * s, 0.74, 0.93)), Vector((0.60 * s, 0.82, 0.84)), Vector((0.36 * s, 0.66, 1.05))]
        Rb = Vector((0.20 * s, 0.33, 1.40))
        w1, w2, wf = "Wing1" + sx, "Wing2" + sx, "WingF" + sx
        add(L.loft("WArm" + sx, [R, R.lerp(E, 0.5) + Vector((0, 0.03, 0.03)), E, E.lerp(W, 0.5) + Vector((0.03 * s, 0.03, 0)), W],
                   [0.10, 0.08, 0.085, 0.06, 0.06], segs=8, bones=[("Spine2", 0), (w1, 0.08), (w2, 0.55)], blend=0.12))
        add(L.loft("WThumb" + sx, [W, W + Vector((0.04 * s, -0.14, 0.11)), W + Vector((0.0, -0.26, 0.05))], [0.055, 0.04, 0.005], segs=7, caps=("round", "point"), bones=w2))
        F = [L.polyline([W, Vector((1.10 * s, 0.40, 2.20)), T[0]], 12),
             L.polyline([W, Vector((1.00 * s, 0.60, 1.92)), T[1]], 12),
             L.polyline([W, Vector((0.78 * s, 0.70, 1.76)), T[2]], 12),
             L.polyline([W, E, Vector((0.48 * s, 0.63, 1.62)), T[3]], 12)]
        for k in range(3):
            add(L.loft(f"WFinger{k}" + sx, F[k], [0.05] * 4 + [0.04] * 5 + [0.03, 0.025, 0.018, 0.006], segs=6, sub=1, caps=("round", "point"), bones=wf))
        add(L.loft("WFinger3" + sx, F[3][4:], [0.05, 0.045, 0.04, 0.035, 0.03, 0.025, 0.02, 0.014, 0.006], segs=6, sub=1, caps=("round", "point"), bones=w1))

        def panel(a, b, wfn, nm, n=6):
            g = L.lerp_line(a, b, n)[1:]
            rows = len(g)
            for i, row in enumerate(g):
                v = (i + 1) / rows
                for k in range(n + 1):
                    sag = 0.20 * math.sin(math.pi * k / n) * v ** 2.2
                    row[k] = row[k].lerp(W, sag) + Vector((0, 0.035 * math.sin(math.pi * k / n) * math.sin(v * 2.6), 0))
            add(L.sheet(nm + sx, g, thick=0.034, bones=wfn))

        panel(F[0], F[1], lambda co, uv: {wf: 1.0}, "Mem0")
        panel(F[1], F[2], lambda co, uv: {wf: 1.0}, "Mem1")
        panel(F[2], F[3], lambda co, uv: {wf: 1 - uv[0], w2: uv[0] * max(0, 1 - uv[1] * 2.5), w1: uv[0] * min(1, uv[1] * 2.5)}, "Mem2")
        back = L.polyline([W, E, R, Rb], 12)
        panel(F[3], back, lambda co, uv: {w1: 1 - uv[0] * 0.75, "Spine2": uv[0] * 0.75}, "Mem3")

    def post(high):
        L.displace(high, "CLOUDS", 0.030, 0.26, 2)
        L.displace(high, "CLOUDS", 0.008, 0.06, 2)

    org = L.organic("StoneBody", P, stone, voxel=0.0085, tris=27600, smooth=9, post=post)

    # --- 餘燼眼（獨立小件）
    eyes = []
    for s, sx in ((1, ".L"), (-1, ".R")):
        eyes.append(L.ellipsoid("Eye" + sx, (0.128 * s, -0.715, 2.118), (0.036, 0.03, 0.022), rot=(15, 0, -25 * s), bones="Head", mat=ember, segs=8, rings=5))

    # --- 骨架
    B = [("Root", (0, 0, 0), (0, 0.3, 0), None),
         ("Hips", (0, 0.12, 1.15), (0, 0.08, 1.38), "Root"),
         ("Spine1", (0, 0.08, 1.38), (0, 0.0, 1.68), "Hips"),
         ("Spine2", (0, 0.0, 1.68), (0, -0.12, 2.08), "Spine1"),
         ("Neck", (0, -0.20, 2.13), (0, -0.42, 2.13), "Spine2"),
         ("Head", (0, -0.42, 2.13), (0, -0.75, 2.02), "Neck"),
         ("Jaw", (0, -0.48, 2.00), (0, -0.80, 1.88), "Head"),
         ("Tail1", (0, 0.28, 1.08), (0, 0.60, 0.80), "Hips"),
         ("Tail2", (0, 0.60, 0.80), (0.05, 0.95, 0.45), "Tail1"),
         ("Tail3", (0.05, 0.95, 0.45), (0.25, 1.25, 0.22), "Tail2"),
         ("Tail4", (0.25, 1.25, 0.22), (0.55, 1.42, 0.15), "Tail3"),
         ("Tail5", (0.55, 1.42, 0.15), (1.02, 1.40, 0.24), "Tail4")]
    for s, sx in ((1, ".L"), (-1, ".R")):
        B += [("UpperArm" + sx, (0.62 * s, -0.04, 1.98), (0.86 * s, 0.04, 1.42), "Spine2"),
              ("ForeArm" + sx, (0.86 * s, 0.04, 1.42), (0.88 * s, -0.19, 0.97), "UpperArm" + sx),
              ("Hand" + sx, (0.88 * s, -0.19, 0.97), (0.87 * s, -0.27, 0.80), "ForeArm" + sx),
              ("Fingers" + sx, (0.87 * s, -0.27, 0.80), (0.87 * s, -0.30, 0.58), "Hand" + sx),
              ("Thigh" + sx, (0.24 * s, 0.10, 1.18), (0.36 * s, -0.25, 0.75), "Hips"),
              ("Shin" + sx, (0.36 * s, -0.25, 0.75), (0.335 * s, 0.15, 0.41), "Thigh" + sx),
              ("Foot" + sx, (0.335 * s, 0.15, 0.41), (0.34 * s, -0.09, 0.085), "Shin" + sx),
              ("Toe" + sx, (0.34 * s, -0.09, 0.085), (0.34 * s, -0.40, 0.03), "Foot" + sx),
              ("Wing1" + sx, (0.22 * s, 0.22, 2.00), (0.62 * s, 0.50, 2.30), "Spine2"),
              ("Wing2" + sx, (0.62 * s, 0.50, 2.30), (0.80 * s, 0.36, 2.74), "Wing1" + sx),
              ("WingF" + sx, (0.80 * s, 0.36, 2.74), (0.90 * s, 0.62, 1.60), "Wing2" + sx)]
    arm = L.make_armature("Gargoyle", B)
    mesh = L.assemble("GargoyleMesh", arm, [(org[0], org[1], org[2], stone)], eyes, BAKED, size=1024, emit_strength=4.0, emit_size=1024)
    os.makedirs(os.path.dirname(MODEL_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=MODEL_BLEND)
    return arm, mesh


# ================================================================== 動作
def define_actions(A, sym):
    """9 個手刻動作。Telegraph 首尾相同可循環；Attack／Attack2 的第 1 格就是 Telegraph 姿勢。"""
    for sx in (".L", ".R"):
        A.add_leg("Thigh" + sx, "Shin" + sx, ["Foot" + sx, "Toe" + sx], "Foot" + sx + ":ik")

    def P(*ds):
        out = {}
        for d in ds:
            out.update(d)
        return out

    LAG = {"Tail2": 2, "Tail3": 4, "Tail4": 6, "Tail5": 7, "Wing2.L": 1, "Wing2.R": 1, "WingF.L": 3, "WingF.R": 3, "Head": 1, "Jaw": 2}
    S = {}

    # ---------------- Idle：呼吸、尾巴擺動、翼微張（3 秒循環）
    b1 = P({"Hips:loc": (0, 0, -0.018), "Spine1": (-1.5, 0, 0), "Spine2": (-3.5, 0, 0), "Neck": (2, 0, 3), "Head": (2, 0, 5), "Jaw": (5, 0, 0),
            "Tail1": (0, 0, 7), "Tail2": (3, 0, 8), "Tail3": (0, 0, 8)},
           sym({"UpperArm": (0, -4, 0), "Fingers": (10, 0, 0), "Wing1": (-3, -5, 0), "WingF": (0, -7, 0)}))
    b2 = P({"Hips:loc": (0, 0, 0.004), "Spine2": (1.5, 0, 0), "Head": (0, 0, -6), "Neck": (0, 0, -3), "Tail1": (2, 0, -6), "Tail2": (0, 0, -7), "Tail3": (0, 0, -6)},
           sym({"UpperArm": (0, 2, 0), "Fingers": (-6, 0, 0), "WingF": (0, 3, 0)}))
    A.action("Idle", [(1, S), (30, b1), (62, b2), (90, S)], lag=LAG)

    # ---------------- Enter：石像蹲伏→甦醒→展翼怒吼→站定
    statue = P({"Hips:loc": (0, 0.05, -0.40), "Hips": (12, 0, 0), "Spine1": (18, 0, 0), "Spine2": (14, 0, 0), "Neck": (14, 0, 0), "Head": (26, 0, 0),
                "Tail1": (0, 0, -18), "Tail2": (0, 0, -24), "Tail3": (0, 0, -24), "Tail4": (0, 0, -18)},
               sym({"UpperArm": (-22, 14, 0), "ForeArm": (-62, 0, 0), "Fingers": (25, 0, 0), "Wing1": (6, 15, 0), "WingF": (0, 16, 0)}))
    crack = P(statue, {"Head": (22, 0, 9), "Spine2": (12, 0, 4), "Hips:loc": (0, 0.05, -0.37)})
    rise = P({"Hips:loc": (0, 0.02, -0.12), "Spine1": (4, 0, 0), "Spine2": (-4, 0, 0), "Head": (-8, 0, -6), "Jaw": (8, 0, 0), "Tail1": (15, 0, 0)},
             sym({"UpperArm": (-5, -14, 0), "ForeArm": (-25, 0, 0), "Wing1": (-6, -14, 0), "WingF": (0, -28, 0)}))
    roar = P({"Hips:loc": (0, 0.08, 0.02), "Hips": (-7, 0, 0), "Spine1": (-10, 0, 0), "Spine2": (-15, 0, 0), "Neck": (-16, 0, 0), "Head": (-28, 0, 0), "Jaw": (36, 0, 0),
              "Tail1": (38, 0, 0), "Tail2": (22, 0, 10), "Tail3": (16, 0, 10), "Tail4": (8, 0, 0)},
             sym({"UpperArm": (24, -42, 0), "ForeArm": (-28, 0, 0), "Hand": (-15, 0, 0), "Fingers": (-32, 0, 0),
                  "Wing1": (-14, -32, 10), "Wing2": (0, -16, 0), "WingF": (0, -62, 0)}))
    roar2 = P(roar, {"Head": (-25, 0, 6), "Spine2": (-13, 0, 3), "Jaw": (30, 0, 0)}, sym({"WingF": (0, -55, 0)}))
    A.action("Enter", [(1, statue), (14, statue), (18, crack), (22, statue), (26, crack), (40, rise), (48, rise, "L"), (53, roar), (62, roar2), (70, roar), (78, roar2), (100, S)], lag=LAG)

    # ---------------- Telegraph：右爪高舉過頭、身體右扭蓄力（可循環保持）
    TG = P({"Hips:loc": (0, 0.15, -0.12), "Hips": (-4, 0, -14), "Spine1": (-6, 0, -12), "Spine2": (-8, -4, -16), "Neck": (6, 0, 14), "Head": (4, 0, 18), "Jaw": (14, 0, 0),
            "UpperArm.R": (-205, 22, 0), "ForeArm.R": (-42, 0, 0), "Hand.R": (-20, 0, 0), "Fingers.R": (-34, 0, 0),
            "UpperArm.L": (-34, -8, 0), "ForeArm.L": (-48, 0, 0), "Fingers.L": (22, 0, 0),
            "Tail1": (22, 0, 10), "Tail2": (10, 0, 10)},
           sym({"Wing1": (-10, -22, 0), "WingF": (0, -42, 0)}))
    TG2 = P(TG, {"Hips:loc": (0, 0.17, -0.15), "Spine2": (-10, -5, -19), "UpperArm.R": (-212, 24, 0), "Jaw": (20, 0, 0), "Head": (2, 0, 20)},
            sym({"WingF": (0, -48, 0)}))
    A.action("Telegraph", [(1, TG), (10, TG2), (20, TG), (30, TG2), (40, TG)], lag={"Tail2": 2, "Tail3": 3})

    # ---------------- Attack：右爪下砸（左腳前踏）
    strike = P({"Hips:loc": (0, -0.42, -0.24), "Hips": (8, 0, 16), "Spine1": (8, 0, 14), "Spine2": (10, 6, 18), "Neck": (-12, 0, -12), "Head": (-18, 0, -14), "Jaw": (26, 0, 0),
                "UpperArm.R": (-58, -26, 0), "ForeArm.R": (-18, 0, 0), "Hand.R": (20, 0, 0), "Fingers.R": (30, 0, 0),
                "UpperArm.L": (36, -26, 0), "ForeArm.L": (-22, 0, 0),
                "Tail1": (32, 0, -10), "Tail2": (14, 0, -8), "Foot.L:ik": (0, -0.38, 0)},
               sym({"Wing1": (14, -10, 0), "WingF": (0, -18, 0)}))
    over = P(strike, {"Hips:loc": (0, -0.47, -0.30), "Spine2": (14, 6, 23), "UpperArm.R": (-40, -34, 0), "ForeArm.R": (-8, 0, 0), "Head": (-10, 0, -18)})
    settle = P(over, {"Hips:loc": (0, -0.45, -0.27), "Spine2": (12, 5, 20), "Jaw": (12, 0, 0)})
    A.action("Attack", [(1, TG), (6, P(TG2, {"Foot.L:ik": (0, -0.12, 0.16), "UpperArm.R": (-218, 26, 0)}), "L"), (10, strike), (13, over), (24, settle),
                        (36, P({"Hips:loc": (0, -0.2, -0.1), "Spine2": (6, 0, 6), "Foot.L:ik": (0, -0.2, 0.12)})), (48, S)], lag=LAG)

    # ---------------- Attack2：蠍尾式鎚擊（尾鎚越過左肩往前砸）
    coil = P({"Hips:loc": (0, -0.08, -0.30), "Hips": (20, 0, -6), "Spine1": (14, 0, -4), "Spine2": (10, 0, -6), "Neck": (-10, 0, 6), "Head": (-22, 0, 6), "Jaw": (10, 0, 0),
              "Tail1": (60, 0, 0), "Tail2": (40, 0, 0), "Tail3": (22, 0, 0), "Tail4": (12, 0, 20, "ZYX"), "Tail5": (5, 0, 25, "ZYX")},
             sym({"UpperArm": (-32, -12, 0), "ForeArm": (-22, 0, 0), "Fingers": (15, 0, 0), "Wing1": (0, -36, 0), "WingF": (0, -34, 0)}))
    apex = P(coil, {"Hips:loc": (0, -0.04, -0.34), "Tail1": (84, 0, 0), "Tail2": (30, 0, 0), "Tail3": (8, 0, 0), "Tail4": (0, 0, 22, "ZYX"), "Tail5": (-6, 0, 28, "ZYX"),
                    "Head": (-26, 0, 6), "Jaw": (22, 0, 0)})
    slam = P(coil, {"Hips:loc": (0, -0.24, -0.46), "Hips": (34, 0, -10), "Spine1": (18, 0, -4), "Spine2": (14, 0, -6), "Head": (-38, 0, 8), "Jaw": (30, 0, 0),
                    "Tail1": (100, 0, 0), "Tail2": (46, 0, 0), "Tail3": (28, 0, 0), "Tail4": (12, 0, 24, "ZYX"), "Tail5": (8, 0, 30, "ZYX")},
             sym({"UpperArm": (-44, -16, 0), "ForeArm": (-10, 0, 0), "Wing1": (6, -44, 0), "WingF": (0, -40, 0)}))
    reb = P(slam, {"Tail1": (93, 0, 0), "Tail4": (6, 0, 24, "ZYX"), "Tail5": (2, 0, 30, "ZYX"), "Hips:loc": (0, -0.22, -0.44)})
    A.action("Attack2", [(1, TG), (12, coil), (20, apex), (24, apex, "L"), (28, slam), (31, reb), (34, slam), (44, slam),
                         (56, P({"Hips:loc": (0, -0.05, -0.15), "Tail1": (40, 0, 0), "Tail2": (20, 0, 0), "Spine1": (6, 0, 0)})), (70, S)],
             lag={"Wing2.L": 1, "Wing2.R": 1, "WingF.L": 3, "WingF.R": 3})

    # ---------------- Hit：受擊後仰
    hit = P({"Hips:loc": (0, 0.14, -0.05), "Hips": (-6, 0, 8), "Spine1": (-10, 0, 10), "Spine2": (-12, 0, 12), "Neck": (4, 0, -8), "Head": (10, 0, -20), "Jaw": (20, 0, 0),
             "Tail1": (8, 0, 12)},
            sym({"UpperArm": (12, -16, 0), "Fingers": (-20, 0, 0), "Wing1": (-8, -12, 0), "WingF": (0, -18, 0)}))
    A.action("Hit", [(1, S, "L"), (4, hit), (10, P({"Spine2": (4, 0, -3), "Head": (-4, 0, 5), "Hips:loc": (0, 0.03, -0.03)})), (20, S)], lag={"Tail2": 2, "Tail3": 3, "WingF.L": 2, "WingF.R": 2})

    # ---------------- Stagger：被彈反，大幅後仰失衡→單膝跪地喘息→撐起
    rec = P({"Hips:loc": (0, 0.42, -0.20), "Hips": (-16, 0, -6), "Spine1": (-18, 0, 0), "Spine2": (-20, 0, 6), "Neck": (-14, 0, 0), "Head": (-26, 0, 10), "Jaw": (32, 0, 0),
             "Tail1": (22, 0, 8), "Foot.R:ik": (0, 0.25, 0.16)},
            sym({"UpperArm": (-40, -72, 0), "ForeArm": (-34, 0, 0), "Fingers": (-32, 0, 0), "Wing1": (-10, -36, 0), "WingF": (0, -62, 0)}))
    sink = P({"Hips:loc": (0, 0.52, -0.40), "Hips": (5, 0, -6), "Spine1": (10, 0, 0), "Spine2": (14, 0, 8), "Head": (20, 0, 0), "Jaw": (16, 0, 0), "Foot.R:ik": (0, 0.48, 0), "Tail1": (7, 0, 0)},
             sym({"UpperArm": (-10, -30, 0), "ForeArm": (-20, 0, 0), "Wing1": (8, -15, 0), "WingF": (0, -26, 0)}))
    kneel = P({"Hips:loc": (0, 0.46, -0.52), "Hips": (8, 0, -4), "Spine1": (18, 0, 0), "Spine2": (20, -6, 10), "Neck": (8, 0, 0), "Head": (26, 0, -8), "Jaw": (22, 0, 0),
               "UpperArm.L": (-34, -6, 0), "ForeArm.L": (-12, 0, 0), "UpperArm.R": (14, 12, 0), "ForeArm.R": (-30, 0, 0), "Foot.R:ik": (0, 0.48, 0),
               "Tail1": (8, 0, 0)},
              sym({"Wing1": (10, -6, 0), "WingF": (0, -10, 0)}))
    daze = P(kneel, {"Head": (18, 0, 12), "Spine2": (17, -4, 6), "Hips:loc": (0, 0.46, -0.49), "Jaw": (10, 0, 0)})
    A.action("Stagger", [(1, S, "L"), (6, rec), (14, sink), (26, kneel), (38, daze), (48, kneel),
                         (60, P({"Hips:loc": (0, 0.24, -0.2), "Spine2": (8, 0, 0), "Foot.R:ik": (0, 0.3, 0.14), "Head": (6, 0, 0), "Tail1": (6, 0, 0)})), (72, S)], lag=LAG)

    # ---------------- PhaseShift：蜷縮蓄力→爆發展翼怒吼→顫抖維持→收
    gather = P({"Hips:loc": (0, 0.05, -0.32), "Hips": (10, 0, 0), "Spine1": (20, 0, 0), "Spine2": (22, 0, 0), "Neck": (10, 0, 0), "Head": (22, 0, 0),
                "Tail1": (0, 0, -14), "Tail2": (0, 0, -18), "Tail3": (0, 0, -18)},
               sym({"UpperArm": (-30, 18, 0), "ForeArm": (-82, 0, 0), "Fingers": (30, 0, 0), "Wing1": (6, 14, 0), "WingF": (0, 16, 0)}))
    gather2 = P(gather, {"Hips:loc": (0, 0.05, -0.36), "Spine2": (25, 0, 0), "Head": (26, 0, 0)})
    burst = P({"Hips:loc": (0, 0.06, 0.05), "Hips": (-10, 0, 0), "Spine1": (-14, 0, 0), "Spine2": (-18, 0, 0), "Neck": (-18, 0, 0), "Head": (-30, 0, 0), "Jaw": (40, 0, 0),
               "Tail1": (46, 0, 0), "Tail2": (26, 0, 14), "Tail3": (20, 0, 14), "Tail4": (10, 0, 0)},
              sym({"UpperArm": (26, -58, 0), "ForeArm": (-32, 0, 0), "Hand": (-20, 0, 0), "Fingers": (-36, 0, 0),
                   "Wing1": (-18, -40, 12), "Wing2": (0, -18, 0), "WingF": (0, -72, 0)}))
    t1 = P(burst, {"Head": (-27, 0, 6), "Spine2": (-16, 0, 3), "Hips:loc": (0, 0.06, 0.03)}, sym({"WingF": (0, -66, 0)}))
    t2 = P(burst, {"Head": (-29, 0, -6), "Spine2": (-17, 0, -3), "Jaw": (34, 0, 0)}, sym({"WingF": (0, -74, 0)}))
    A.action("PhaseShift", [(1, S), (16, gather), (24, gather2, "L"), (29, burst), (35, t1), (41, t2), (47, t1), (53, t2), (59, t1), (65, burst), (90, S)],
             lag={"Tail2": 2, "Tail3": 3, "Tail4": 4, "WingF.L": 2, "WingF.R": 2})

    # ---------------- Die：受創→踉蹌→跪倒→前撲倒地（最後一格停住）
    d1 = P(hit, {"Hips:loc": (0, 0.2, -0.08), "Head": (-20, 0, -14), "Jaw": (34, 0, 0)})
    d2 = P({"Hips:loc": (0, -0.08, -0.18), "Hips": (6, 0, 4), "Spine1": (12, 0, 0), "Spine2": (14, 0, -6), "Head": (22, 0, 8), "Jaw": (18, 0, 0), "Tail1": (0, 0, 0)},
           sym({"UpperArm": (-8, -8, 0), "ForeArm": (-12, 0, 0), "Wing1": (10, 4, 0), "WingF": (0, 4, 0)}))
    d3 = P({"Hips:loc": (0, -0.14, -0.58), "Hips": (14, 0, 0), "Spine1": (16, 0, 0), "Spine2": (12, 0, 0), "Neck": (8, 0, 0), "Head": (24, 0, 0), "Jaw": (12, 0, 0), "Tail1": (4, 0, 0)},
           sym({"UpperArm": (-14, -6, 0), "ForeArm": (-8, 0, 0), "Fingers": (20, 0, 0), "Wing1": (12, 8, 0), "WingF": (0, 6, 0)}))
    d4 = P({"Hips:loc": (0, -0.50, -0.84), "Hips": (58, 0, 0), "Spine1": (14, 0, 0), "Spine2": (8, 0, 0), "Neck": (-14, 0, 0), "Head": (-22, 0, 26), "Jaw": (10, 0, 0),
            "Tail1": (-30, 0, 0), "Tail2": (7, 0, 0),
            "UpperArm.L": (-60, -36, 0), "ForeArm.L": (-40, 0, 0), "UpperArm.R": (-30, 30, 0), "ForeArm.R": (-50, 0, 0)},
           sym({"Fingers": (10, 0, 0), "Wing1": (22, -30, 0), "WingF": (0, -52, 0)}))
    d5 = P(d4, {"Hips:loc": (0, -0.50, -0.79), "Head": (-18, 0, 26)})
    A.action("Die", [(1, S, "L"), (5, d1), (18, d2), (34, d3), (42, P(d3, {"Head": (28, 0, 6), "Hips:loc": (0, -0.15, -0.60)}), "L"), (54, d4), (58, d5), (64, d4), (96, d4)],
             lag={"Tail2": 2, "Tail3": 4, "Tail4": 5, "WingF.L": 4, "WingF.R": 4})


def build_anim():
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    arm = bpy.data.objects["Gargoyle"]
    mesh = bpy.data.objects["GargoyleMesh"]
    L.clear_actions(arm)
    A = L.Animator(arm)
    sym = L.sym
    define_actions(A, sym)
    L.export_glb(OUT_GLB, arm, mesh)
    cam, _ = L.studio(HEIGHT)
    A.show(None, 1)
    views = L.render_views(cam, TMP, NAME, HEIGHT, center=(0, 0.25, HEIGHT * 0.48))
    L.aim(cam, (0, -0.3, 1.85), 2.6, -30, 5)
    L.render(os.path.join(TMP, NAME + "_close.png"), (900, 760))
    FM = {"Enter": [1, 26, 40, 53, 100], "Attack": [1, 6, 10, 13, 48], "Attack2": [1, 12, 22, 28, 70], "Hit": [1, 4, 10, 15, 20],
          "Stagger": [1, 6, 14, 38, 72], "PhaseShift": [1, 20, 29, 47, 90], "Die": [1, 5, 34, 54, 96]}
    L.render_actions(cam, A, TMP, NAME, HEIGHT, extra=1.0, res=(480, 480), center=(0, 0.0, HEIGHT * 0.40), frames_map=FM)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


def view_only():
    bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
    cam, _ = L.studio(HEIGHT)
    L.render_views(cam, TMP, NAME, HEIGHT, center=(0, 0.25, HEIGHT * 0.48))


if STAGE == "view":
    view_only()
if STAGE in ("model", "all"):
    build_model()
if STAGE in ("anim", "all"):
    build_anim()
print("DONE", NAME, STAGE)
