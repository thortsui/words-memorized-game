"""v2（建模 A）Boss 2：教堂石像鬼 gargoyle。依 art/v2/design.md §2.2、art_guide.md §2、art/reference/v2/gargoyle_p1/p2.jpg。
四肢著地的蹲伏＋巨大石翼（展開寬 ≈ 1.5H，有缺角與鉤爪）＋分節長尾（背側小石鰭、末端捲起）＋往後上彎的雙角＋
鉛灰排水槽嘴＋手腕鏽鐵鐐銬與斷鏈＋額頭原創金箔徽記＋石縫透熔岩橘光。
二階「石翼狂嘯」：P2_WingMolten_L/R（翼膜熔岩裂網）、P2_Horns（角加長分岔）、P2_Maw（嘴撕裂到頰邊、內部熔光、長牙）、
P2_SpineShards_*（背脊一排碎石尖片）。
建模流程沿用 soul_creature_lib（體素融合高模→減面→烘焙圖集，不修改 lib）；動作沿用 build_boss_gargoyle.define_actions（不修改原檔，
以包裝器重新對應到新骨架的蹲伏靜止姿勢），PhaseShift 依 design.md 分鏡重做（2.2 s，爆發 1.0 s）。
用法：blender --background --factory-startup --python v2a_gargoyle.py -- [model|anim|all] [--quick]
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soul_creature_lib as L
import v2a_lib as VL

NAME = "boss_gargoyle"
MODEL_BLEND = os.path.join(HERE, "source", "v2a_" + NAME + "_model.blend")
OUT_BLEND = os.path.join(HERE, "source", "v2a_" + NAME + ".blend")
OUT_GLB = os.path.join(HERE, "export_raw", NAME + ".glb")
TILES = os.path.join(HERE, "preview", "_tiles", "v2a_" + NAME)
BAKED = os.path.join(HERE, "textures", "baked", "v2a_" + NAME)
HEIGHT = 2.95
TEX = int(os.environ.get("BOSS_TEX", "2048"))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = next((a for a in argv if not a.startswith("--")), "all")
QUICK = "--quick" in argv
ORANGE = "#ff8a3a"


# 石材：複製自 build_boss_gargoyle.stone_mat（胸口熔光中心改到新姿勢的位置）
def stone_mat():
    m = L.PMat("Stone")
    co = m.coord()
    rock = m.scan("Rock042L", 0.9)
    rock2 = m.scan("Rock023", 0.6)
    moss = m.scan("Moss002", 1.6, maps=("Color",))
    col = m.mix(m.ramp(m.noise(1.3, 3), [(0.4, 0), (0.6, 1)]), rock["Color"], rock2["Color"])
    col = m.hsv(col, s=0.5, v=0.95)
    col = m.mix(1.0, col, (0.56, 0.55, 0.52), "MULTIPLY")
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
    m.set(ln.inputs[0], m.mapping(loc=(0, 0.35, -1.42), scale=(0.9, 1.0, 1.0)))
    chest = m.ramp(ln.outputs["Value"], [(0.25, 1), (0.75, 0)])
    spots = m.ramp(m.noise(0.9, 2, vec=m.mapping(loc=(11, 4, 2))), [(0.58, 0), (0.68, 0.8)])
    spots = m.math("MULTIPLY", spots, m.ramp(m.math("MULTIPLY", m.sep(co)[2], 0.4), [(0.40, 0), (0.52, 1)]))  # z 1.3~1.6 m 以上才有零星餘燼
    glow = m.math("MULTIPLY", core, m.math("MAXIMUM", chest, spots))
    halo = m.math("MULTIPLY", m.math("MULTIPLY", wide, m.math("MAXIMUM", chest, spots)), 0.35)
    emit = m.ramp(m.math("ADD", glow, halo, clamp=True), [(0.0, (0, 0, 0)), (0.35, (0.75, 0.10, 0.0)), (0.8, (1.0, 0.42, 0.05)), (1.0, (1.0, 0.75, 0.3))])
    rough = m.ramp(rock["Roughness"], [(0.0, 0.72), (1.0, 0.97)])
    n = m.bump(rock["Displacement"], 1.0, 0.022)
    n = m.bump(m.voronoi(13, "SMOOTH_F1", vec=wv), 0.35, 0.012, normal=n)
    n = m.bump(m.math("SUBTRACT", 1.0, wide), 1.0, 0.014, normal=n)
    return m.finish(col, rough, 0.0, n, emit=emit, emit_strength=4.0)



def flat_mat(name, color, rough, metal, bump_scale=0.0, noise=0.0):
    m = L.PMat(name)
    col = color
    if noise:
        n = m.noise(6.0, 4, 0.6)
        col = m.mix(m.ramp(n, [(0.3, 0), (0.7, 1)]), color, tuple(c * (1 - noise) for c in color))
    nrm = m.bump(m.noise(30.0, 4, 0.6), bump_scale, 0.004) if bump_scale else None
    return m.finish(col, rough, metal, nrm)


def iron_mat():
    m = L.PMat("RustIron")
    rust = m.scan("Metal046B", 0.3)
    col = m.mix(1.0, rust["Color"], (0.55, 0.42, 0.35), "MULTIPLY")
    return m.finish(col, 0.85, 0.35, m.bump(rust["Displacement"], 0.8, 0.01))


# ================================================================== 小工具
P2IDS = {}


def tag(obs, name, bone, pivot):
    """creature 流程：bind() 會刪掉非骨頭的頂點群組，所以 P2 改用面屬性 p2id 標記。"""
    if not isinstance(obs, (list, tuple)):
        obs = [obs]
    idx = P2IDS.setdefault(name, len(P2IDS) + 1)
    VL.SPEC[name] = (bone, Vector(pivot))
    for o in obs:
        a = o.data.attributes.get("p2id") or o.data.attributes.new("p2id", "INT", "FACE")
        a.data.foreach_set("value", [idx] * len(o.data.polygons))
    return obs


def split_attr(mesh, arm):
    out = []
    for name, idx in P2IDS.items():
        bone, piv = VL.SPEC[name]
        a = mesh.data.attributes.get("p2id")
        vals = [0] * len(mesh.data.polygons)
        a.data.foreach_get("value", vals)
        if idx not in vals:
            print("WARN P2 沒有面", name)
            continue
        L.activate(mesh)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        sel = [v == idx for v in vals]
        mesh.data.polygons.foreach_set("select", sel)
        vs = [False] * len(mesh.data.vertices)
        for p, f in zip(mesh.data.polygons, sel):
            if f:
                for vi in p.vertices:
                    vs[vi] = True
        mesh.data.vertices.foreach_set("select", vs)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
        ob = [o for o in bpy.context.selected_objects if o != mesh][0]
        ob.name = ob.data.name = "P2_" + name
        if name.startswith("WingMolten"):
            # 翼膜會隨多根骨頭變形：熔岩裂網改成蒙皮（權重從主網格最近的翼膜頂點轉移），遊戲端在爆發那一格切成可見
            L.transfer_weights(mesh, ob, k=4)
            print(f"P2 {ob.name} skinned tris={VL.tri_count([ob])}", flush=True)
            out.append(ob)
            continue
        ob.vertex_groups.clear()
        for md in list(ob.modifiers):
            ob.modifiers.remove(md)
        ob.parent = None
        ob.matrix_world = Matrix()
        ob.data.transform(Matrix.Translation(-piv))
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = bone
        bpy.context.view_layer.update()
        ob.matrix_world = Matrix.Translation(piv)
        print(f"P2 {ob.name} -> {bone} tris={VL.tri_count([ob])} mats={[s.material.name for s in ob.material_slots]}", flush=True)
        out.append(ob)
    return out


def torus(name, c, axis, R, r, bones, mat, nu=16, nv=6):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    bm.loops.layers.uv.new("puv")
    ax = Vector(axis).normalized()
    e1 = ax.orthogonal().normalized()
    e2 = ax.cross(e1)
    vs = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        d = e1 * math.cos(a) + e2 * math.sin(a)
        row = []
        for j_ in range(nv):
            b = 2 * math.pi * j_ / nv
            row.append(bm.verts.new(Vector(c) + d * (R + r * math.cos(b)) + ax * (r * math.sin(b))))
        vs.append(row)
    for i in range(nu):
        for j_ in range(nv):
            f = bm.faces.new((vs[i][j_], vs[(i + 1) % nu][j_], vs[(i + 1) % nu][(j_ + 1) % nv], vs[i][(j_ + 1) % nv]))
            for lp, (a, b) in zip(f.loops, ((i, j_), (i + 1, j_), (i + 1, j_ + 1), (i, j_ + 1))):
                lp[uv].uv = (a / nu * 2 * math.pi * R, b / nv * 2 * math.pi * r)
    ob = L._finish_mesh(name, bm, mat)
    if bones:
        L.assign(ob, bones)
    return ob


def shard(name, p, d, ln, r, bones, mat, segs=5, seed=0):
    rr = random.Random(seed)
    d = Vector(d).normalized()
    side = d.orthogonal().normalized()
    pts = [Vector(p) - d * r * 0.6, Vector(p) + d * ln * 0.4 + side * ln * rr.uniform(-0.08, 0.08), Vector(p) + d * ln]
    return L.loft(name, pts, [(r, r * 0.6), (r * 0.6, r * 0.4), 0.003], segs=segs, sub=2, caps=("flat", "point"), bones=bones, mat=mat, smooth=False)


def line(name, pts, r, bones, mat, segs=5):
    return L.loft(name, [Vector(p) for p in pts], [r] * len(pts), segs=segs, sub=2, caps=("round", "round"), bones=bones, mat=mat)


# ================================================================== 建模
def build_model():
    L.reset()
    stone = stone_mat()
    lead = flat_mat("Lead", (0.16, 0.17, 0.19), 0.55, 0.7, 0.4, noise=0.4)
    gold = flat_mat("GoldLeaf", (0.55, 0.40, 0.14), 0.45, 0.9, 0.2, noise=0.5)
    iron = iron_mat()
    g_eye = VL.glow_mat("Glow_Eye", ORANGE, 2.5)
    g_wpn = VL.glow_mat("Glow_Weapon", ORANGE, 0.8)
    g_maw = VL.glow_mat("P2_Glow_Maw", ORANGE, 3.0)
    g_wing = VL.glow_mat("P2_Glow_Wing", ORANGE, 2.2)
    rnd = random.Random(3)
    P = []
    add = lambda o: (P.append(o), o)[1]
    D = []      # 直接烘焙的零件（非體素融合）
    GL = []     # 發光零件（不烘焙）

    # --- 軀幹（四足蹲伏，背往肩膀隆起）
    add(L.loft("Torso", [(0, 0.46, 1.02), (0, 0.26, 1.24), (0, 0.02, 1.42), (0, -0.22, 1.52), (0, -0.42, 1.50), (0, -0.56, 1.46)],
               [(0.25, 0.22), (0.31, 0.27), (0.36, 0.31), (0.44, 0.34), (0.40, 0.31), (0.22, 0.20)], segs=20, sub=5,
               bones=[("Hips", 0), ("Spine1", 0.32), ("Spine2", 0.62), ("Neck", 0.97)], blend=0.16))
    add(L.ellipsoid("Hump", (0, -0.02, 1.68), (0.36, 0.34, 0.20), rot=(10, 0, 0), bones="Spine2"))
    add(L.ellipsoid("Belly", (0, -0.05, 1.16), (0.24, 0.30, 0.16), rot=(-15, 0, 0), bones="Spine1"))
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.ellipsoid("Pec" + sx, (0.22 * s, -0.48, 1.36), (0.22, 0.16, 0.19), rot=(-20, 0, 12 * s), bones="Spine2"))
        add(L.ellipsoid("Trap" + sx, (0.26 * s, -0.36, 1.70), (0.26, 0.24, 0.13), rot=(-10, -18 * s, 0), bones="Spine2"))
        add(L.ellipsoid("Lat" + sx, (0.38 * s, -0.05, 1.40), (0.14, 0.26, 0.22), rot=(-20, 0, 0), bones="Spine1"))
        add(L.ellipsoid("Rib" + sx, (0.30 * s, -0.20, 1.24), (0.10, 0.16, 0.14), bones="Spine1"))
        add(L.ellipsoid("Glute" + sx, (0.20 * s, 0.44, 1.10), (0.20, 0.18, 0.20), bones="Hips"))
        for q, (y, z) in enumerate([(-0.30, 1.16), (-0.12, 1.06), (0.06, 1.00)]):
            add(L.ellipsoid(f"Ab{q}" + sx, (0.09 * s, y, z), (0.09, 0.07, 0.05), bones="Spine1", segs=10, rings=6))

    # --- 頸與頭：長吻、尖耳、眉脊、往後上彎的雙角
    add(L.loft("NeckM", [(0, -0.50, 1.50), (0, -0.66, 1.54), (0, -0.82, 1.55)], [(0.20, 0.18), (0.16, 0.16), (0.15, 0.15)], segs=14,
               bones=[("Spine2", 0), ("Neck", 0.25), ("Head", 0.9)], blend=0.3))
    add(L.loft("Skull", [(0, -0.76, 1.60), (0, -0.88, 1.62), (0, -1.00, 1.58), (0, -1.12, 1.52), (0, -1.22, 1.47), (0, -1.28, 1.43)],
               [(0.16, 0.15), (0.19, 0.17), (0.165, 0.14), (0.11, 0.10), (0.075, 0.07), (0.05, 0.05)], segs=16, sub=5, ref=(1, 0, 0),
               caps=("round", "round"), bones="Head"))
    add(L.loft("JawM", [(0, -0.86, 1.46), (0, -0.98, 1.40), (0, -1.10, 1.36), (0, -1.20, 1.34)], [(0.13, 0.07), (0.11, 0.06), (0.08, 0.045), (0.05, 0.03)],
               segs=12, caps=("round", "round"), bones=[("Head", 0), ("Jaw", 0.15)], blend=0.2))
    add(L.ellipsoid("Crest", (0, -0.90, 1.74), (0.07, 0.15, 0.06), rot=(-10, 0, 0), bones="Head", segs=10, rings=6))
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.ellipsoid("Brow" + sx, (0.10 * s, -1.02, 1.64), (0.09, 0.08, 0.045), rot=(18, 0, -20 * s), bones="Head", segs=10, rings=6))
        add(L.ellipsoid("Cheek" + sx, (0.12 * s, -0.94, 1.50), (0.06, 0.09, 0.06), bones="Head", segs=10, rings=6))
        ridge = lambda a, t: 1 + 0.10 * max(0.0, math.sin(5 * a)) * (1 - t)
        add(L.loft("Horn" + sx, [(0.11 * s, -0.90, 1.68), (0.19 * s, -0.86, 1.88), (0.26 * s, -0.74, 2.06), (0.32 * s, -0.56, 2.16), (0.36 * s, -0.38, 2.16),
                                 (0.38 * s, -0.26, 2.08), (0.42 * s, -0.22, 2.24)],
                   [0.105, 0.092, 0.078, 0.062, 0.046, 0.030, 0.006], segs=10, sub=4, caps=("flat", "point"), shape=ridge, bones="Head"))
        ear = [L.polyline([(0.13 * s, -0.84, 1.66), (0.26 * s, -0.78, 1.70), (0.37 * s, -0.70, 1.72)], 5),
               L.polyline([(0.13 * s, -0.84, 1.56), (0.24 * s, -0.78, 1.60), (0.37 * s, -0.70, 1.72)], 5)]
        add(L.sheet("Ear" + sx, [[ear[0][i], ear[0][i].lerp(ear[1][i], 0.5), ear[1][i]] for i in range(5)], thick=0.035, bones="Head"))

    # --- 前肢：粗長臂撐地、四指爪
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.ellipsoid("Delt" + sx, (0.50 * s, -0.42, 1.50), (0.22, 0.22, 0.24), bones=[("UpperArm" + sx, 0)]))
        add(L.loft("Arm" + sx, [(0.48 * s, -0.42, 1.52), (0.58 * s, -0.42, 1.20), (0.66 * s, -0.44, 0.90), (0.68 * s, -0.56, 0.56), (0.70 * s, -0.68, 0.24), (0.72 * s, -0.78, 0.10)],
                   [0.19, (0.16, 0.18), 0.13, (0.14, 0.15), (0.10, 0.11), (0.12, 0.07)], segs=14, sub=5,
                   bones=[("UpperArm" + sx, 0), ("ForeArm" + sx, 0.42), ("Hand" + sx, 0.88)], blend=0.14))
        add(L.ellipsoid("Bicep" + sx, (0.60 * s, -0.50, 1.20), (0.12, 0.13, 0.22), rot=(0, 0, 0), bones="UpperArm" + sx))
        add(L.ellipsoid("Elbow" + sx, (0.68 * s, -0.36, 0.90), (0.08, 0.09, 0.09), bones="ForeArm" + sx, segs=10, rings=6))
        add(L.ellipsoid("FArmM" + sx, (0.69 * s, -0.54, 0.62), (0.11, 0.12, 0.20), rot=(-20, 0, 0), bones="ForeArm" + sx))
        palm = Vector((0.72 * s, -0.80, 0.08))
        for q, (dx, dy) in enumerate([(-0.10, -0.02), (-0.04, -0.08), (0.03, -0.085), (0.10, -0.035)]):
            b = palm + Vector((s * dx, dy, 0.0))
            mid = b + Vector((s * dx * 0.8, dy * 1.2 - 0.06, 0.05))
            tip = mid + Vector((s * dx * 0.3, -0.10, -0.12))
            add(L.loft(f"Finger{q}" + sx, [b, mid, mid.lerp(tip, 0.55) + Vector((0, -0.02, 0.0)), tip], [0.048, 0.042, 0.03, 0.006], segs=7, sub=3,
                       caps=("round", "point"), bones=[("Hand" + sx, 0), ("Fingers" + sx, 0.25)], blend=0.2))
            GL.append(line(f"ClawGlow{q}" + sx, [mid.lerp(tip, 0.35) + Vector((0, 0, 0.028)), mid.lerp(tip, 0.75) + Vector((0, -0.005, 0.012))], 0.007,
                           "Fingers" + sx, g_wpn))
        tb = palm + Vector((-0.11 * s, 0.04, 0.03))
        add(L.loft("Thumb" + sx, [tb, tb + Vector((-0.08 * s, -0.04, 0.02)), tb + Vector((-0.10 * s, -0.12, -0.05))], [0.045, 0.036, 0.005], segs=7, sub=3,
                   caps=("round", "point"), bones=[("Hand" + sx, 0), ("Fingers" + sx, 0.4)], blend=0.2))
        # 手腕鏽鐵鐐銬＋斷鏈
        wc = Vector((0.70 * s, -0.69, 0.27))
        D.append(torus("Shackle" + sx, wc, (0.02 * s, -0.25, 1.0), 0.125, 0.028, "ForeArm" + sx, iron, nu=18, nv=6))
        D.append(torus("ShackleB" + sx, wc + Vector((0, 0.0, 0.05)), (0.02 * s, -0.25, 1.0), 0.128, 0.018, "ForeArm" + sx, iron, nu=18, nv=5))
        pts = [wc + Vector((0.11 * s, -0.04, -0.04))]
        for q in range(6):
            pts.append(pts[-1] + Vector((0.04 * s + rnd.uniform(-0.02, 0.02), 0.06 - 0.03 * q, -0.035 if pts[-1].z > 0.04 else 0.0)))
        for q in range(len(pts) - 1):
            a, b = pts[q], pts[q + 1]
            ax = (b - a).normalized()
            n = ax.orthogonal() if q % 2 else ax.cross(ax.orthogonal())
            D.append(torus(f"Link{q}" + sx, a.lerp(b, 0.5), n, 0.035, 0.010, "ForeArm" + sx, iron, nu=10, nv=4))

    # --- 後肢（反關節，蹲踞）
    for s, sx in ((1, ".L"), (-1, ".R")):
        add(L.loft("Leg" + sx, [(0.26 * s, 0.42, 1.08), (0.36 * s, 0.22, 0.85), (0.42 * s, 0.02, 0.62), (0.42 * s, 0.22, 0.46), (0.40 * s, 0.40, 0.33),
                                (0.40 * s, 0.26, 0.17), (0.40 * s, 0.14, 0.07)],
                   [(0.24, 0.27), (0.22, 0.25), (0.15, 0.16), (0.14, 0.16), (0.10, 0.11), (0.10, 0.10), (0.12, 0.08)], segs=14, sub=5,
                   bones=[("Thigh" + sx, 0), ("Shin" + sx, 0.38), ("Foot" + sx, 0.70), ("Toe" + sx, 0.97)], blend=0.10))
        add(L.ellipsoid("Quad" + sx, (0.38 * s, 0.18, 0.86), (0.16, 0.24, 0.18), rot=(35, 0, 0), bones="Thigh" + sx))
        add(L.ellipsoid("Knee" + sx, (0.43 * s, -0.02, 0.62), (0.08, 0.07, 0.09), bones="Shin" + sx, segs=10, rings=6))
        add(L.ellipsoid("Calf" + sx, (0.41 * s, 0.30, 0.46), (0.10, 0.13, 0.13), rot=(-45, 0, 0), bones="Shin" + sx))
        add(L.loft("Hock" + sx, [(0.40 * s, 0.42, 0.33), (0.40 * s, 0.52, 0.38)], [0.06, 0.012], segs=6, sub=2, caps=("flat", "point"), bones="Foot" + sx))
        ball = Vector((0.40 * s, 0.12, 0.07))
        for q, a in enumerate((-28, 0, 28)):
            d = Vector((math.sin(math.radians(a)) * s, -math.cos(math.radians(a)), 0))
            add(L.loft(f"Toe{q}" + sx, [ball + d * 0.03, ball + d * 0.16, ball + d * 0.28 + Vector((0, 0, 0.0)), ball + d * 0.38 + Vector((0, 0, -0.06))],
                       [0.07, 0.06, 0.045, 0.005], segs=7, sub=3, caps=("round", "point"), bones=[("Foot" + sx, 0), ("Toe" + sx, 0.15)], blend=0.2))
        add(L.loft("Spur" + sx, [ball + Vector((0, 0.03, 0)), ball + Vector((0, 0.14, -0.02)), ball + Vector((0, 0.20, -0.06))], [0.05, 0.035, 0.004], segs=6, sub=2,
                   caps=("round", "point"), bones="Foot" + sx))

    # --- 分節長尾（末端捲起）＋背側小石鰭
    TP = [(0, 0.60, 0.98), (0, 0.98, 0.70), (0.10, 1.34, 0.42), (0.30, 1.64, 0.24), (0.56, 1.84, 0.24), (0.80, 1.90, 0.40), (0.90, 1.80, 0.62), (0.84, 1.66, 0.74)]
    seg = lambda a, t: 1 + 0.07 * max(0.0, math.cos(t * math.pi * 28)) - 0.03
    add(L.loft("Tail", TP, [0.16, 0.135, 0.115, 0.10, 0.085, 0.07, 0.055, 0.035], segs=12, sub=5, shape=seg, caps=("round", "point"),
               bones=[("Hips", 0), ("Tail1", 0.04), ("Tail2", 0.20), ("Tail3", 0.38), ("Tail4", 0.55), ("Tail5", 0.72), ("Tail6", 0.88)], blend=0.12))
    tl = L.polyline(TP, 24)
    tbones = ["Tail1", "Tail1", "Tail2", "Tail2", "Tail2", "Tail3", "Tail3", "Tail3", "Tail4", "Tail4", "Tail4", "Tail5", "Tail5", "Tail5", "Tail5",
              "Tail6", "Tail6", "Tail6", "Tail6", "Tail6", "Tail6", "Tail6", "Tail6", "Tail6", "Tail6"]
    for q in range(1, 22):
        p, nx = tl[q], tl[q + 1]
        d = (nx - p).normalized()
        up = Vector((0, 0, 1))
        up = (up - d * up.dot(d)).normalized()
        if q > 15:
            up = (up + (Vector((0, 0, 0)) - Vector((p.x - 0.7, p.y - 1.75, 0))).normalized() * 0.0).normalized()
        rr = 0.16 * (1 - q / 26)
        fh = 0.12 - 0.003 * q
        add(L.loft(f"Fin{q}", [p + up * rr * 0.5 - d * 0.03, p + up * (rr + fh) + d * 0.05], [(0.04, 0.016), 0.003], segs=5, sub=1,
                   caps=("flat", "point"), bones=tbones[q], smooth=False))

    # --- 石翼（半展、超寬：翼展 ≈ 4.6 m）
    for s, sx in ((1, ".L"), (-1, ".R")):
        R0 = Vector((0.20 * s, 0.04, 1.70))
        E = Vector((0.72 * s, 0.32, 2.26))
        Wr = Vector((1.24 * s, 0.36, 2.78))
        T = [Vector((2.30 * s, 0.58, 1.70)), Vector((2.08 * s, 0.86, 1.00)), Vector((1.58 * s, 0.98, 0.74)), Vector((0.98 * s, 0.82, 0.86))]
        Rb = Vector((0.24 * s, 0.30, 1.30))
        w1, w2, wf = "Wing1" + sx, "Wing2" + sx, "WingF" + sx
        add(L.loft("WArm" + sx, [R0, R0.lerp(E, 0.5) + Vector((0, 0.02, 0.04)), E, E.lerp(Wr, 0.5) + Vector((0.02 * s, 0.03, 0)), Wr],
                   [0.11, 0.085, 0.09, 0.065, 0.065], segs=8, bones=[("Spine2", 0), (w1, 0.08), (w2, 0.55)], blend=0.12))
        add(L.loft("WClaw" + sx, [Wr, Wr + Vector((0.06 * s, -0.10, 0.12)), Wr + Vector((0.02 * s, -0.22, 0.10)), Wr + Vector((-0.02 * s, -0.26, 0.02))],
                   [0.055, 0.04, 0.02, 0.004], segs=7, caps=("round", "point"), bones=w2))
        F = [L.polyline([Wr, Vector((1.80 * s, 0.46, 2.36)), T[0]], 12),
             L.polyline([Wr, Vector((1.68 * s, 0.66, 1.84)), T[1]], 12),
             L.polyline([Wr, Vector((1.40 * s, 0.76, 1.66)), T[2]], 12),
             L.polyline([Wr, E.lerp(Wr, 0.25), Vector((1.0 * s, 0.70, 1.40)), T[3]], 12)]
        for q in range(3):
            add(L.loft(f"WFinger{q}" + sx, F[q], [0.055] * 4 + [0.045] * 5 + [0.034, 0.026, 0.018, 0.006], segs=6, sub=1, caps=("round", "point"), bones=wf))
            add(L.loft(f"WTalon{q}" + sx, [F[q][-1], F[q][-1] + (F[q][-1] - F[q][-3]).normalized() * 0.10 + Vector((0, 0, -0.04))], [0.02, 0.003], segs=5, sub=1,
                       caps=("flat", "point"), bones=wf))
        add(L.loft("WFinger3" + sx, F[3][4:], [0.05, 0.045, 0.04, 0.035, 0.03, 0.025, 0.02, 0.014, 0.006], segs=6, sub=1, caps=("round", "point"), bones=w1))
        wr = random.Random(10 + s)
        panels = []

        def panel(a, b, wfn, nm, n=7, notch=0.0):
            g = L.lerp_line(a, b, n)[1:]
            rows = len(g)
            for i, row in enumerate(g):
                v = (i + 1) / rows
                for kk in range(n + 1):
                    sag = 0.18 * math.sin(math.pi * kk / n) * v ** 2.0
                    row[kk] = row[kk].lerp(Wr, sag) + Vector((0, 0.05 * math.sin(math.pi * kk / n) * math.sin(v * 2.6), 0))
            if notch:     # 翼膜邊緣缺角（不規則地往內縮）
                for kk in range(1, n):
                    cut = notch * wr.random() ** 2
                    for i in range(rows - 3, rows):
                        w = (i - (rows - 4)) / 3
                        g[i][kk] = g[i][kk].lerp(Wr, cut * w)
            add(L.sheet(nm + sx, g, thick=0.034, bones=wfn))
            panels.append(g)

        panel(F[0], F[1], lambda co, uv: {wf: 1.0}, "Mem0", notch=0.22)
        panel(F[1], F[2], lambda co, uv: {wf: 1.0}, "Mem1", notch=0.18)
        panel(F[2], F[3], lambda co, uv: {wf: 1 - uv[0], w2: uv[0] * max(0, 1 - uv[1] * 2.5), w1: uv[0] * min(1, uv[1] * 2.5)}, "Mem2", notch=0.15)
        back = L.polyline([Wr, E, R0, Rb], 12)
        panel(F[3], back, lambda co, uv: {w1: 1 - uv[0] * 0.75, "Spine2": uv[0] * 0.75}, "Mem3")
        # P2：翼膜熔岩裂網（兩面）
        veins = []
        for gi in (0, 1):
            g = panels[gi]
            rows, cols = len(g), len(g[0])
            for side in (1, -1):
                def at(i, kk):
                    i = max(0, min(rows - 1, i)); kk = max(0, min(cols - 1, kk))
                    p = g[i][kk]
                    nrm = (g[min(i + 1, rows - 1)][kk] - g[max(i - 1, 0)][kk]).cross(g[i][min(kk + 1, cols - 1)] - g[i][max(kk - 1, 0)])
                    nrm = nrm.normalized() if nrm.length > 1e-6 else Vector((0, 1, 0))
                    return p + nrm * side * 0.024
                for kk in (2, 4, 6):
                    pts = [at(i, kk + (1 if (i + kk) % 3 == 0 else 0)) for i in range(0, rows - 1, 2)]
                    veins.append(line(f"Vein{gi}{kk}{side}" + sx, pts, 0.009, wf, g_wing))
                for i in (3, 7, 10):
                    if i < rows - 1:
                        pts = [at(i + (1 if kk % 3 == 0 else 0), kk) for kk in range(0, cols, 2)]
                        veins.append(line(f"VeinX{gi}{i}{side}" + sx, pts, 0.007, wf, g_wing))
        GL.extend(tag(veins, "WingMolten_" + sx[1], wf, Wr.lerp(T[1], 0.4)))

    # --- 鉛灰排水槽嘴（上顎前伸成 U 形槽）
    spout = []
    for i in range(7):
        t = i / 6
        c = Vector((0, -1.12 - 0.26 * t, 1.42 - 0.03 * t))
        spout.append([c + Vector((math.cos(a) * 0.075, 0, -math.sin(a) * 0.060 - 0.0)) for a in [math.radians(x) for x in range(0, 181, 30)]])
    D.append(L.sheet("Spout", spout, thick=0.016, bones="Head", mat=lead))
    D.append(torus("SpoutLip", Vector((0, -1.38, 1.39)), (0, 1, 0.1), 0.07, 0.012, "Head", lead, nu=14, nv=4))
    # 額頭原創金箔徽記（圓＋十字＋弧）
    ec = Vector((0, -1.03, 1.71))
    en = Vector((0, -0.55, 0.83)).normalized()
    D.append(torus("Emblem", ec, en, 0.045, 0.007, "Head", gold, nu=16, nv=4))
    ex = Vector((1, 0, 0)); ey = en.cross(ex)
    D.append(line("EmblemA", [ec - ex * 0.04 + en * 0.004, ec + ex * 0.04 + en * 0.004], 0.006, "Head", gold))
    D.append(line("EmblemB", [ec - ey * 0.04 + en * 0.004, ec + ey * 0.04 + en * 0.004], 0.006, "Head", gold))
    D.append(line("EmblemC", [ec + ey * 0.065 - ex * 0.05 + en * 0.002, ec + ey * 0.08, ec + ey * 0.065 + ex * 0.05 + en * 0.002], 0.005, "Head", gold))
    # 口內獠牙（一階）
    for s in (1, -1):
        for q in range(3):
            p = Vector((0.06 * s, -1.06 - 0.06 * q, 1.40))
            D.append(L.loft(f"Fang{q}{s}", [p, p + Vector((0, -0.01, -0.06))], [0.014, 0.002], segs=5, sub=1, caps=("flat", "point"), bones="Head", mat=stone))

    # --- 二階：背脊碎石尖片、加長分岔角、撕裂熔光的嘴
    sp = {"Spine2": [], "Spine1": [], "Hips": []}
    ridge = [(0, -0.50, 1.70), (0, -0.36, 1.82), (0, -0.20, 1.88), (0, -0.04, 1.88), (0, 0.12, 1.80), (0, 0.26, 1.62), (0, 0.38, 1.44), (0, 0.50, 1.28),
             (0, 0.60, 1.16), (0, 0.70, 1.04)]
    for q, p in enumerate(ridge):
        bn = "Spine2" if p[1] < -0.15 else ("Spine1" if p[1] < 0.22 else "Hips")
        h = 0.50 - 0.03 * abs(q - 3) * 1.2
        d = Vector((rnd.uniform(-0.15, 0.15), 0.25 + 0.05 * q, 1.0))
        sp[bn].append(shard(f"SpineShard{q}", Vector(p) - Vector((0, 0, 0.04)), d, h, 0.09, bn, stone, seed=q))
        for s in (1, -1):
            if 1 <= q <= 7:
                sp[bn].append(shard(f"SpineShardS{q}{s}", Vector(p) + Vector((0.13 * s, 0.02, -0.08)), Vector((0.5 * s, 0.3, 1.0)), h * 0.5, 0.045, bn, stone, seed=q * 3 + s))
    piv = {"Spine2": (0, -0.30, 1.84), "Spine1": (0, 0.10, 1.80), "Hips": (0, 0.55, 1.22)}
    for bn, obs in sp.items():
        D.extend(tag(obs, "SpineShards_" + bn, bn, piv[bn]))
    hn = []
    for s in (1, -1):
        base = [Vector((0.36 * s, -0.38, 2.16)), Vector((0.42 * s, -0.22, 2.24))]
        hn.append(L.loft(f"HornExt{s}", [base[1] - Vector((0, 0.02, 0.03)), base[1] + Vector((0.04 * s, 0.06, 0.12)), base[1] + Vector((0.06 * s, 0.02, 0.30)),
                                        base[1] + Vector((0.03 * s, -0.08, 0.40))], [0.03, 0.026, 0.016, 0.003], segs=8, sub=3, caps=("flat", "point"), bones="Head", mat=stone))
        for q, (p0, d, ln) in enumerate([((0.26 * s, -0.74, 2.06), (0.6 * s, -0.4, 0.7), 0.24), ((0.32 * s, -0.56, 2.16), (0.5 * s, 0.2, 1.0), 0.28),
                                          ((0.40 * s, -0.22, 2.40), (0.3 * s, 0.6, 0.6), 0.16)]):
            hn.append(shard(f"HornFork{q}{s}", Vector(p0), Vector(d), ln, 0.026, "Head", stone, segs=7, seed=20 + q))
    D.extend(tag(hn, "Horns", "Head", (0, -0.70, 1.95)))
    maw = []
    maw.append(L.ellipsoid("MawCore", (0, -1.05, 1.42), (0.07, 0.17, 0.04), bones="Head", mat=g_maw, segs=12, rings=6))
    for s in (1, -1):
        maw.append(line(f"MawTear{s}", [(0.07 * s, -1.10, 1.42), (0.12 * s, -1.00, 1.45), (0.15 * s, -0.92, 1.49), (0.16 * s, -0.86, 1.52)], 0.012, "Head", g_maw))
        maw.append(line(f"MawTearB{s}", [(0.12 * s, -1.00, 1.45), (0.17 * s, -0.98, 1.53), (0.19 * s, -0.94, 1.58)], 0.007, "Head", g_maw))
    GL.extend(tag(maw, "Maw", "Head", (0, -1.05, 1.44)))
    fangs = []
    for s in (1, -1):
        for q in range(3):
            p = Vector((0.08 * s, -0.98 - 0.08 * q, 1.42))
            fangs.append(L.loft(f"P2Fang{q}{s}", [p, p + Vector((0, -0.02, -0.12 + 0.02 * q))], [0.018, 0.002], segs=5, sub=1, caps=("flat", "point"), bones="Head", mat=stone))
    D.extend(tag(fangs, "Fangs", "Head", (0, -1.05, 1.42)))

    def post(high):
        L.displace(high, "CLOUDS", 0.030, 0.26, 2)
        L.displace(high, "CLOUDS", 0.008, 0.06, 2)
        L.displace(high, "VORONOI", 0.007, 0.045)
        L.displace(high, "STUCCI", 0.0025, 0.012)

    org = L.organic("StoneBody", P, stone, voxel=0.0072 if not QUICK else 0.02, tris=27000, smooth=7, post=post)
    for s, sx in ((1, ".L"), (-1, ".R")):
        GL.append(L.ellipsoid("Eye" + sx, (0.105 * s, -1.075, 1.585), (0.034, 0.026, 0.02), rot=(15, 0, -25 * s), bones="Head", mat=g_eye, segs=8, rings=5))

    # --- 骨架
    Bn = [("Root", (0, 0, 0), (0, 0.3, 0), None),
          ("Hips", (0, 0.42, 1.05), (0, 0.10, 1.32), "Root"),
          ("Spine1", (0, 0.10, 1.32), (0, -0.20, 1.48), "Hips"),
          ("Spine2", (0, -0.20, 1.48), (0, -0.52, 1.50), "Spine1"),
          ("Neck", (0, -0.52, 1.50), (0, -0.80, 1.55), "Spine2"),
          ("Head", (0, -0.80, 1.55), (0, -1.25, 1.46), "Neck"),
          ("Jaw", (0, -0.86, 1.44), (0, -1.20, 1.33), "Head")]
    tb = [TP[0], TP[1], TP[2], TP[3], TP[4], TP[5], TP[7]]
    for q in range(6):
        Bn.append((f"Tail{q + 1}", tb[q], tb[q + 1], "Hips" if q == 0 else f"Tail{q}"))
    for s, sx in ((1, ".L"), (-1, ".R")):
        Bn += [("UpperArm" + sx, (0.48 * s, -0.42, 1.52), (0.66 * s, -0.44, 0.90), "Spine2"),
               ("ForeArm" + sx, (0.66 * s, -0.44, 0.90), (0.70 * s, -0.70, 0.22), "UpperArm" + sx),
               ("Hand" + sx, (0.70 * s, -0.70, 0.22), (0.72 * s, -0.82, 0.08), "ForeArm" + sx),
               ("Fingers" + sx, (0.72 * s, -0.82, 0.08), (0.74 * s, -1.04, 0.04), "Hand" + sx),
               ("Thigh" + sx, (0.26 * s, 0.40, 1.04), (0.42 * s, 0.02, 0.62), "Hips"),
               ("Shin" + sx, (0.42 * s, 0.02, 0.62), (0.40 * s, 0.40, 0.33), "Thigh" + sx),
               ("Foot" + sx, (0.40 * s, 0.40, 0.33), (0.40 * s, 0.12, 0.07), "Shin" + sx),
               ("Toe" + sx, (0.40 * s, 0.12, 0.07), (0.40 * s, -0.20, 0.03), "Foot" + sx),
               ("Wing1" + sx, (0.20 * s, 0.04, 1.70), (0.72 * s, 0.32, 2.26), "Spine2"),
               ("Wing2" + sx, (0.72 * s, 0.32, 2.26), (1.24 * s, 0.36, 2.78), "Wing1" + sx),
               ("WingF" + sx, (1.24 * s, 0.36, 2.78), (1.90 * s, 0.75, 1.50), "Wing2" + sx)]
    arm = L.make_armature("Gargoyle", Bn)
    mesh = L.assemble("GargoyleMesh", arm, [(org[0], org[1], org[2], stone)], D, BAKED, size=TEX, emit_strength=4.0, emit_size=1024)
    mesh.data.materials[0].name = "GargoyleStone_Glow_Rune"     # 石縫熔光在 emissive 貼圖上：材質名含 Glow，程式轉階段時一起變亮
    for o in GL:
        for g in list(o.vertex_groups):
            pass
    VL.join_into(mesh, GL)
    L.normalize_weights(mesh, "Root")
    p2 = split_attr(mesh, arm)
    for o in p2:
        o["p2form"] = 2
    print("TRIS_FINAL", VL.tri_count([mesh] + p2), "main", VL.tri_count([mesh]), "p2", VL.tri_count(p2), flush=True)
    os.makedirs(os.path.dirname(MODEL_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=MODEL_BLEND)
    return arm, mesh, p2


# ================================================================== 動作
_argv = sys.argv
sys.argv = [_argv[0], "--", "noop"]          # 匯入原檔時不要觸發它的建模／匯出
import build_boss_gargoyle as G0     # 只讀取原本的 define_actions（不修改原檔）
sys.argv = _argv


class Wrap:
    """把原本為直立駝背骨架寫的姿勢套到新的蹲伏骨架：骨盆下沉量減半（靜止姿勢已經很低），PhaseShift 換成 v2 分鏡。"""

    def __init__(self, A):
        self.A = A

    def __getattr__(self, k):
        return getattr(self.A, k)

    def action(self, name, keys, **kw):
        if name == "PhaseShift":
            return None
        out = []
        for kk in keys:
            pose = dict(kk[1])
            if "Hips:loc" in pose:
                x, y, z = pose["Hips:loc"][:3]
                pose["Hips:loc"] = (x, y, z * 0.5 if z < 0 else z)
            out.append((kk[0], pose) + tuple(kk[2:]))
        return self.A.action(name, out, **kw)


def phase_shift(A, sym):
    P = lambda *ds: {k: v for d in ds for k, v in d.items()}
    LAG = {"Tail2": 2, "Tail3": 3, "Tail4": 4, "Tail5": 5, "Tail6": 6, "WingF.L": 2, "WingF.R": 2}
    S = {}
    # 0.0–0.5 翅膀包住全身縮成一團（像變回雕像）
    wrap = P({"Hips:loc": (0, 0.06, -0.14), "Hips": (8, 0, 0), "Spine1": (12, 0, 0), "Spine2": (10, 0, 0), "Neck": (10, 0, 0), "Head": (24, 0, 0), "Jaw": (0, 0, 0),
              "Tail1": (0, 0, -20), "Tail2": (0, 0, -30), "Tail3": (0, 0, -30), "Tail4": (0, 0, -25)},
             sym({"UpperArm": (-8, 10, 0), "ForeArm": (-20, 0, 0), "Wing1": (18, 10, -48), "Wing2": (0, 0, -30), "WingF": (0, 30, -20)}))
    tr1 = P(wrap, {"Hips:loc": (0, 0.06, -0.15), "Head": (22, 0, 3), "Spine2": (11, 2, 0)})
    tr2 = P(wrap, {"Hips:loc": (0, 0.06, -0.13), "Head": (25, 0, -3), "Spine2": (9, -2, 0)})
    # 1.0 爆發：翅膀猛然展開、仰頭咆哮（嘴張到最大）
    burst = P({"Hips:loc": (0, 0.08, 0.12), "Hips": (-14, 0, 0), "Spine1": (-14, 0, 0), "Spine2": (-16, 0, 0), "Neck": (-18, 0, 0), "Head": (-34, 0, 0), "Jaw": (44, 0, 0),
               "Tail1": (40, 0, 0), "Tail2": (24, 0, 14), "Tail3": (18, 0, 14), "Tail4": (10, 0, 0)},
              sym({"UpperArm": (30, -30, 0), "ForeArm": (-30, 0, 0), "Fingers": (-30, 0, 0), "Wing1": (-16, -30, 14), "Wing2": (0, -16, 0), "WingF": (0, -70, 0)}))
    burst2 = P(burst, {"Head": (-30, 0, 6), "Jaw": (40, 0, 0)}, sym({"WingF": (0, -64, 0)}))
    # 拍兩下翅膀半騰空
    up = lambda h, wd: P({"Hips:loc": (0, 0.04, h), "Hips": (-6, 0, 0), "Spine2": (-6, 0, 0), "Head": (-12, 0, 0), "Jaw": (16, 0, 0), "Tail1": (20, 0, 0),
                          "Foot.L:ik": (0, 0.05, h * 0.8), "Foot.R:ik": (0, 0.05, h * 0.8)},
                         sym({"UpperArm": (-30, -10, 0), "ForeArm": (-40, 0, 0), "Wing1": (-6, wd, 10), "WingF": (0, wd * 1.6, 0)}))
    land = P({"Hips:loc": (0, -0.04, -0.14), "Hips": (10, 0, 0), "Spine2": (8, 0, 0), "Head": (-14, 0, 0), "Jaw": (20, 0, 0), "Tail1": (20, 0, 30), "Tail2": (6, 0, 30),
              "Tail3": (0, 0, 30)},
             sym({"Wing1": (-6, -20, 0), "WingF": (0, -40, 0)}))
    AG = P({"Hips:loc": (0, -0.06, -0.11), "Hips": (16, 0, 0), "Spine1": (10, 0, 0), "Spine2": (8, 0, 0), "Neck": (-12, 0, 0), "Head": (-18, 0, 0), "Jaw": (16, 0, 0),
            "Tail1": (22, 0, 0), "Tail2": (8, 0, 0)},
           sym({"UpperArm": (-34, -18, 0), "ForeArm": (-42, 0, 0), "Fingers": (-24, 0, 0), "Wing1": (-10, -26, 0), "WingF": (0, -46, 0)}))
    A.action("PhaseShift", [(0, S), (12, wrap, "io"), (17, tr1, "io"), (21, tr2, "io"), (25, tr1, "io"), (28, tr2, "io"), (30, burst, "in3"), (35, burst2, "out3"),
                            (41, up(0.30, 20), "io"), (45, up(0.42, -50), "io"), (50, up(0.36, 18), "io"), (54, up(0.30, -46), "io"), (59, land, "in"),
                            (66, AG, "io")], lag=LAG, hits=[(30, "WingF.L")])


def build_anim(arm=None, mesh=None, p2=None):
    if arm is None:
        bpy.ops.wm.open_mainfile(filepath=MODEL_BLEND)
        arm = bpy.data.objects["Gargoyle"]
        mesh = bpy.data.objects["GargoyleMesh"]
        p2 = [o for o in bpy.data.objects if o.name.startswith("P2_")]
    L.clear_actions(arm)
    A = L.Animator(arm, base=None)
    A.ground_r = {"*": 0.04, "Hips": 0.20, "Spine1": 0.22, "Spine2": 0.24, "Neck": 0.14, "Head": 0.12, "Jaw": 0.03, "Fingers.L": 0.02, "Fingers.R": 0.02,
                  "Hand.L": 0.03, "Hand.R": 0.03}
    A.ground_skip = {b.name for b in arm.data.bones if b.name.startswith(("Tail", "Wing"))}
    G0.define_actions(Wrap(A), L.sym)
    phase_shift(A, L.sym)
    # 片段順序與合約一致
    VL.export_glb(arm, [mesh] + p2, OUT_GLB)
    L.write_meta(A, NAME, os.path.join(HERE, "export_raw"))
    cam, _ = L.studio(HEIGHT)
    A.show(None, 0)
    os.makedirs(TILES, exist_ok=True)
    c = (0, 0.25, HEIGHT * 0.45)
    VL.show_p2(p2, False)
    for k, (nm, az) in enumerate((("front", 0), ("side", 90), ("back", 180), ("q34", -35))):
        L.aim(cam, c, HEIGHT * 2.6, az)
        L.render(os.path.join(TILES, f"view_{k}_{nm}.png"), (600, 700))
    VL.show_p2(p2, True)
    L.aim(cam, c, HEIGHT * 2.6, -35)
    L.render(os.path.join(TILES, "view_4_p2.png"), (600, 700))
    L.aim(cam, c, HEIGHT * 2.6, 150)
    L.render(os.path.join(TILES, "view_5_p2back.png"), (600, 700))
    VL.show_p2(p2, False)
    L.aim(cam, (0, -0.3, 1.5), 2.4, -30, 5)
    L.render(os.path.join(TILES, "close_0.png"), (800, 700))
    VL.show_p2(p2, True)
    L.render(os.path.join(TILES, "close_1.png"), (800, 700))
    VL.show_p2(p2, False)
    L.aim(cam, (0, 0.2, HEIGHT * 0.42), HEIGHT * 3.0, -40, 10, rig=False)
    for r, (name, (act, last)) in enumerate(A.actions.items()):
        for i in range(8):
            f = round(last * i / 7)
            VL.show_p2(p2, name == "IdleAggro" or (name == "PhaseShift" and f >= 30))
            A.show(name, f)
            L.render(os.path.join(TILES, f"act_{r:02d}_{name}_{i}_f{f:03d}.png"), (400, 400))
    A.show(None, 0)
    VL.show_p2(p2, False)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


if STAGE in ("model", "all"):
    r = build_model()
    if STAGE == "all":
        build_anim(*r)
elif STAGE == "anim":
    build_anim()
print("DONE", NAME, STAGE, flush=True)
