"""魂系 Boss（非人形生物）共用工具：放樣建模、體素融合高模→減面低模、權重轉移、
程序材質烘焙成單一 PBR 圖集、手刻關鍵影格動作（各一條靜音 NLA track）、匯出與預覽。
只在背景模式的獨立 Blender 4.2 使用。朝向：臉朝 -Y、原點在腳底。
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_SRC = os.path.join(HERE, "textures", "boss")


# ------------------------------------------------------------------ 基本
def reset(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    sc.world = w
    return sc


def activate(ob, others=()):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in others:
        o.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def dup(ob, name):
    o = ob.copy()
    o.data = ob.data.copy()
    o.name = name
    bpy.context.scene.collection.objects.link(o)
    return o


def join(objs, name):
    objs = [o for o in objs if o]
    activate(objs[0], objs[1:])
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    return ob


def _finish_mesh(name, bm, mat=None, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat.mat if hasattr(mat, "mat") else mat)
    return ob


def hard(ob, angle=35):
    """依角度標記硬邊（板甲、武器等硬表面）。"""
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    ob.data.set_sharp_from_angle(angle=math.radians(angle))
    return ob


def _sst(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# 抵達某關鍵格那一段的緩動（與人形動作相同的寫法）：in＝加速抵達（爆發）、out＝減速抵達（跟隨）、io＝平滑
EASE = {"lin": lambda s: s, "in": lambda s: s * s, "in3": lambda s: s ** 3, "out": lambda s: 1 - (1 - s) ** 2,
        "out3": lambda s: 1 - (1 - s) ** 3, "io": _sst}
# Blender 關鍵格內插（設在「前一格」上）
BL_EASE = {"lin": ("LINEAR", None), "in": ("QUAD", "EASE_IN"), "in3": ("CUBIC", "EASE_IN"), "out": ("QUAD", "EASE_OUT"),
           "out3": ("CUBIC", "EASE_OUT"), "io": ("SINE", "EASE_IN_OUT")}


def assign(ob, bones, tvals=None, blend=0.15):
    """bones: 'Bone' | [(bone, t起點), ...]（沿 t 混合）| callable(co, t)->{bone:w}。"""
    n = len(ob.data.vertices)
    if tvals is None:
        tvals = [0.0] * n
    groups = {}

    def g(name):
        if name not in groups:
            groups[name] = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
        return groups[name]

    if isinstance(bones, str):
        g(bones).add(range(n), 1.0, "REPLACE")
        return
    for i, v in enumerate(ob.data.vertices):
        t = tvals[i]
        if callable(bones):
            w = bones(v.co, t)
        else:
            w = {}
            for k, (bn, t0) in enumerate(bones):
                a = 1.0 if k == 0 else _sst((t - t0) / blend + 0.5)
                b = 0.0 if k == len(bones) - 1 else _sst((t - bones[k + 1][1]) / blend + 0.5)
                if a - b > 1e-4:
                    w[bn] = w.get(bn, 0) + a - b
        s = sum(w.values()) or 1.0
        for bn, x in w.items():
            if x > 1e-4:
                g(bn).add([i], x / s, "REPLACE")


# ------------------------------------------------------------------ 放樣
def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def resample(pts, rad, sub):
    n = len(pts)
    out = []
    for i in range(n - 1):
        a, b, c, d = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        ra, rb, rc, rd = rad[max(i - 1, 0)], rad[i], rad[i + 1], rad[min(i + 2, n - 1)]
        for k in range(sub):
            t = k / sub
            r = _cr(ra, rb, rc, rd, t)
            r = Vector((min(max(r[0], min(rb[0], rc[0])), max(rb[0], rc[0])), min(max(r[1], min(rb[1], rc[1])), max(rb[1], rc[1]))))
            out.append((_cr(a, b, c, d, t), r, (i + t) / (n - 1)))
    out.append((pts[-1].copy(), rad[-1].copy(), 1.0))
    return out


def loft(name, pts, radii, segs=12, sub=4, ref=(1, 0, 0), caps=("round", "round"), bones=None, blend=0.15,
         shape=None, mat=None, caplen=1.0, smooth=True):
    """沿路徑放樣橢圓截面管。radii: r 或 (沿 ref 方向半徑, 另一方向半徑)。
    caps: round/point/flat/open。shape(a, t)->半徑倍率。UVMap=公制比例，puv=正規化(u 繞圈, v 沿長度)。"""
    pts = [Vector(p) for p in pts]
    rad = [Vector((r, r)) if isinstance(r, (int, float)) else Vector(r) for r in radii]
    sm = resample(pts, rad, sub)
    m = len(sm)
    rings = []
    N = Vector(ref)
    for i, (c, r, t) in enumerate(sm):
        T = (sm[min(i + 1, m - 1)][0] - sm[max(i - 1, 0)][0]).normalized()
        N = N - T * N.dot(T)
        if N.length < 1e-5:
            N = T.orthogonal()
        N.normalize()
        rings.append([c, T, N.copy(), T.cross(N), r[0], r[1], t])
    full = []
    c, T, Nn, B, ra, rb, t = rings[0]
    pole0 = pole1 = None
    if caps[0] == "round":
        L = min(ra, rb) * caplen
        for k in (3, 2, 1):
            a = k / 4 * math.pi / 2
            full.append([c - T * L * math.sin(a), T, Nn, B, ra * math.cos(a), rb * math.cos(a), 0.0])
        pole0 = c - T * L
    elif caps[0] in ("flat", "point"):
        pole0 = c.copy()
    full += rings if caps[0] != "point" else rings[1:]
    c, T, Nn, B, ra, rb, t = rings[-1]
    if caps[1] == "round":
        L = min(ra, rb) * caplen
        for k in (1, 2, 3):
            a = k / 4 * math.pi / 2
            full.append([c + T * L * math.sin(a), T, Nn, B, ra * math.cos(a), rb * math.cos(a), 1.0])
        pole1 = c + T * L
    elif caps[1] == "flat":
        pole1 = c.copy()
    elif caps[1] == "point":
        full.pop()
        pole1 = c.copy()
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    puv = bm.loops.layers.uv.new("puv")
    tv = []
    vr = []
    length = [0.0]
    for i, (c, T, Nn, B, ra, rb, t) in enumerate(full):
        if i:
            length.append(length[-1] + (c - full[i - 1][0]).length)
        row = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            k = shape(a, t) if shape else 1.0
            row.append(bm.verts.new(c + Nn * (ra * k * math.cos(a)) + B * (rb * k * math.sin(a))))
            tv.append(t)
        vr.append(row)
    circ = sum(math.pi * (r[4] + r[5]) for r in full) / len(full)
    tot = length[-1] or 1.0

    def setuv(f, coords):
        for lp, (u, v, pv) in zip(f.loops, coords):
            lp[uv].uv = (u * circ, v)
            lp[puv].uv = (u, pv)

    for i in range(len(full) - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            f = bm.faces.new((vr[i][j], vr[i][j2], vr[i + 1][j2], vr[i + 1][j]))
            u0, u1 = j / segs, (j + 1) / segs
            setuv(f, [(u0, length[i], full[i][6]), (u1, length[i], full[i][6]), (u1, length[i + 1], full[i + 1][6]), (u0, length[i + 1], full[i + 1][6])])
    for pole, row, tt, ll, flip in ((pole0, vr[0], 0.0, -0.02, True), (pole1, vr[-1], 1.0, tot + 0.02, False)):
        if pole is None:
            continue
        pv = bm.verts.new(pole)
        tv.append(tt)
        l0 = 0.0 if flip else tot
        for j in range(segs):
            j2 = (j + 1) % segs
            f = bm.faces.new((row[j2], row[j], pv) if flip else (row[j], row[j2], pv))
            a, b = ((j + 1) / segs, j / segs) if flip else (j / segs, (j + 1) / segs)
            setuv(f, [(a, l0, tt), (b, l0, tt), ((a + b) / 2, ll, tt)])
    ob = _finish_mesh(name, bm, mat, smooth)
    if bones:
        assign(ob, bones, tv, blend)
    return ob


def ellipsoid(name, loc, scale, rot=(0, 0, 0), bones=None, mat=None, segs=14, rings=9):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    s = sum(scale) / 3
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        us = []
        for lp in f.loops:
            c = lp.vert.co
            us.append(math.atan2(c.y, c.x) / (2 * math.pi) % 1.0)
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.5 else u for u in us]
        pole = [abs(lp.vert.co.z) > 0.999 for lp in f.loops]
        mean = sum(u for u, p in zip(us, pole) if not p) / max(1, sum(1 for p in pole if not p))
        for lp, u, p in zip(f.loops, us, pole):
            lp[uv].uv = ((mean if p else u) * s * 6.28, math.acos(max(-1, min(1, lp.vert.co.z))) * s)
    M = Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bm.loops.layers.uv.new("puv")
    ob = _finish_mesh(name, bm, mat)
    if bones:
        assign(ob, bones)
    return ob


def box(name, loc, size, rot=(0, 0, 0), bones=None, mat=None, bevel=0.0, taper=None):
    """taper=(sx, sy)：+Z 端的縮放。"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if taper:
        for v in bm.verts:
            if v.co.z > 0:
                v.co.x *= taper[0]
                v.co.y *= taper[1]
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect="EDGES")
    M = Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()
    bm.loops.layers.uv.new("UVMap")
    bm.loops.layers.uv.new("puv")
    ob = _finish_mesh(name, bm, mat, smooth=False)
    box_uv(ob)
    ob.data.transform(M)
    if bones:
        assign(ob, bones)
    return ob


def box_uv(ob):
    """依面法線主軸做公制方盒投影 UV（硬表面零件用）。"""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[a] + ax * 31.0, co[b] + (1 if n[ax] > 0 else 0) * 53.0)


def sheet(name, grid, thick=0.0, bones=None, blend=0.15, mat=None, wrap=False, smooth=True, inner_scale=0.4):
    """grid[i][j] 點陣曲面；v=i 方向、u=j 方向。thick>0 會加厚成封閉實體。wrap: u 方向頭尾相接。"""
    rows, cols = len(grid), len(grid[0])
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    puv = bm.loops.layers.uv.new("puv")
    vs = [[bm.verts.new(Vector(p)) for p in row] for row in grid]
    if callable(bones):  # callable 會收到 (co, (u, v))
        tv = [(j / (cols - 1), i / (rows - 1)) for i in range(rows) for j in range(cols)]
    else:
        tv = [i / (rows - 1) for i in range(rows) for _ in range(cols)]
    mid = cols // 2
    lv = [0.0]
    for i in range(1, rows):
        lv.append(lv[-1] + (Vector(grid[i][mid]) - Vector(grid[i - 1][mid])).length)
    mr = rows // 2
    lu = [0.0]
    for j in range(1, cols + (1 if wrap else 0)):
        lu.append(lu[-1] + (Vector(grid[mr][j % cols]) - Vector(grid[mr][j - 1])).length)
    nc = cols if wrap else cols - 1
    for i in range(rows - 1):
        for j in range(nc):
            j2 = (j + 1) % cols
            f = bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
            cc = [(j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1)]
            for lp, (jj, ii) in zip(f.loops, cc):
                lp[uv].uv = (lu[jj], lv[ii])
                lp[puv].uv = (jj / nc, ii / (rows - 1))
    ob = _finish_mesh(name, bm, mat, smooth)
    if bones:
        assign(ob, bones, tv, blend)
    if thick > 0:
        nf = len(ob.data.polygons)
        m = ob.modifiers.new("s", "SOLIDIFY")
        m.thickness = thick
        m.offset = 0
        apply_mods(ob)
        # 加厚後正反兩面 UV 會重疊：把朝內（朝向 Z 軸）那一面縮小並移到旁邊，避免烘焙互相覆蓋
        me = ob.data
        uvl = me.uv_layers["UVMap"]
        side = [sum(me.polygons[i].normal.x * me.polygons[i].center.x + me.polygons[i].normal.y * me.polygons[i].center.y for i in rng) for rng in (range(0, nf), range(nf, 2 * nf))]
        inner = range(0, nf) if side[0] < side[1] else range(nf, 2 * nf)
        for i in inner:
            for li in me.polygons[i].loop_indices:
                u, v = uvl.data[li].uv
                uvl.data[li].uv = (u * inner_scale + lu[-1] * 1.5 + 0.5, v * inner_scale)
        for i in range(2 * nf, len(me.polygons)):
            for li in me.polygons[i].loop_indices:
                uvl.data[li].uv = (-0.5, -0.5)
    return ob


def lerp_line(a, b, n):
    """兩條折線（同點數）之間內插出 n+1 條，回傳 grid（列=沿線、欄=跨線）。"""
    return [[Vector(pa).lerp(Vector(pb), k / n) for k in range(n + 1)] for pa, pb in zip(a, b)]


def polyline(pts, n):
    """把折線依長度重取樣成 n+1 點（Catmull-Rom 平滑）。"""
    pts = [Vector(p) for p in pts]
    if len(pts) > 2:
        sm = [p for p, _, _ in resample(pts, [Vector((0, 0))] * len(pts), 8)]
    else:
        sm = pts
    d = [0.0]
    for i in range(1, len(sm)):
        d.append(d[-1] + (sm[i] - sm[i - 1]).length)
    out = []
    k = 0
    for i in range(n + 1):
        s = d[-1] * i / n
        while k < len(sm) - 2 and d[k + 1] < s:
            k += 1
        f = (s - d[k]) / max(d[k + 1] - d[k], 1e-9)
        out.append(sm[k].lerp(sm[k + 1], min(1, max(0, f))))
    return out


# ------------------------------------------------------------------ 骨架
def make_armature(name, bones):
    """bones: [(name, head, tail, parent|None)]"""
    ad = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(arm)
    activate(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for bn, h, t, par in bones:
        b = ad.edit_bones.new(bn)
        b.head, b.tail = Vector(h), Vector(t)
        b.roll = 0
        if par:
            b.parent = ad.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def bind(mesh, arm):
    mesh.parent = arm
    m = mesh.modifiers.new("Armature", "ARMATURE")
    m.object = arm
    names = {b.name for b in arm.data.bones}
    for vg in list(mesh.vertex_groups):
        if vg.name not in names:
            print("WARN 權重群組沒有對應骨頭:", vg.name)
            mesh.vertex_groups.remove(vg)
    normalize_weights(mesh, fallback=arm.data.bones[0].name)


def _get_w(ob):
    names = [g.name for g in ob.vertex_groups]
    W = np.zeros((len(ob.data.vertices), max(len(names), 1)), np.float32)
    for v in ob.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return names, W


def _set_w(ob, names, W, limit=4):
    ob.vertex_groups.clear()
    gs = [ob.vertex_groups.new(name=n) for n in names]
    if W.shape[1] > limit:
        idx = np.argsort(-W, axis=1)[:, limit:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-8)
    for i, j in zip(*np.nonzero(W > 0.004)):
        gs[j].add([int(i)], float(W[i, j]), "REPLACE")


def normalize_weights(ob, fallback):
    names, W = _get_w(ob)
    if fallback not in names:
        names.append(fallback)
        W = np.hstack([W, np.zeros((len(W), 1), np.float32)])
    W[W.sum(1) < 1e-5, names.index(fallback)] = 1.0
    _set_w(ob, names, W)


def transfer_weights(src, dst, k=3):
    names, W = _get_w(src)
    kd = KDTree(len(src.data.vertices))
    for v in src.data.vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    out = np.zeros((len(dst.data.vertices), W.shape[1]), np.float32)
    for v in dst.data.vertices:
        for co, i, d in kd.find_n(v.co, k):
            out[v.index] += W[i] / (d + 1e-3)
    _set_w(dst, names, out, limit=8)


def smooth_weights(ob, iters=4, lam=0.6):
    names, W = _get_w(ob)
    e = np.array([tuple(x.vertices) for x in ob.data.edges], np.int64)
    deg = np.zeros(len(W), np.float32)
    np.add.at(deg, e[:, 0], 1)
    np.add.at(deg, e[:, 1], 1)
    deg = np.maximum(deg, 1)[:, None]
    for _ in range(iters):
        acc = np.zeros_like(W)
        np.add.at(acc, e[:, 0], W[e[:, 1]])
        np.add.at(acc, e[:, 1], W[e[:, 0]])
        W = (1 - lam) * W + lam * acc / deg
    _set_w(ob, names, W)


# ------------------------------------------------------------------ 有機體：體素融合→高模→減面低模
def organic(name, parts, mat, voxel=0.01, tris=15000, smooth=6, post=None, wsmooth=5, uv_angle=66):
    src = join(parts, name + "_src")
    high = dup(src, name + "_high")
    high.vertex_groups.clear()
    m = high.modifiers.new("rm", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.use_smooth_shade = True
    if smooth:
        s = high.modifiers.new("sm", "SMOOTH")
        s.factor = 0.5
        s.iterations = smooth
    apply_mods(high)
    if post:
        post(high)
        apply_mods(high)
    high.data.materials.clear()
    high.data.materials.append(mat.mat)
    low = dup(high, name + "_low")
    nt = sum(len(p.vertices) - 2 for p in low.data.polygons)
    d = low.modifiers.new("d", "DECIMATE")
    d.ratio = min(1.0, tris / nt)
    apply_mods(low)
    # 減面後薄片（披風、袖子）的面法線可能翻向內側，烘焙時射線會往錯的方向打而漏烘（出現黑斑）：一律重算成朝外
    bm = bmesh.new()
    bm.from_mesh(low.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(low.data)
    bm.free()
    low.data.polygons.foreach_set("use_smooth", [True] * len(low.data.polygons))
    transfer_weights(src, low)
    smooth_weights(low, wsmooth)
    low.data.uv_layers.new(name="UVMap")
    activate(low)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(uv_angle), island_margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    src.hide_render = True
    print(f"[organic] {name}: high {len(high.data.polygons)} faces -> low {sum(len(p.vertices) - 2 for p in low.data.polygons)} tris")
    return high, low, src


def displace(ob, kind="CLOUDS", strength=0.01, scale=0.2, depth=2, mid=0.5):
    t = bpy.data.textures.new("disp", kind)
    t.noise_scale = scale
    if kind == "CLOUDS":
        t.noise_depth = depth
    m = ob.modifiers.new("disp", "DISPLACE")
    m.texture = t
    m.strength = strength
    m.mid_level = mid
    m.texture_coords = "GLOBAL"
    return m


# ------------------------------------------------------------------ 程序材質（烘焙來源）
class PMat:
    """節點材質小工具。finish() 後可用 set_mode 切換輸出：full / color / orm / emit。"""

    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self._tc = None

    def node(self, typ, **kw):
        n = self.nt.nodes.new(typ)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def set(self, sock, x):
        if x is None:
            return
        if isinstance(x, bpy.types.NodeSocket):
            self.nt.links.new(x, sock)
        elif isinstance(x, (int, float)):
            sock.default_value = x if sock.type == "VALUE" else ((x, x, x, 1) if sock.type == "RGBA" else (x, x, x))
        else:
            sock.default_value = (*x[:3], 1) if sock.type == "RGBA" else tuple(x[:3])

    def coord(self, kind="Object"):
        if not self._tc:
            self._tc = self.node("ShaderNodeTexCoord")
        return self._tc.outputs[kind]

    def puv(self):
        return self.node("ShaderNodeUVMap", uv_map="puv").outputs[0]

    def mapping(self, vec=None, scale=1.0, loc=(0, 0, 0), rot=(0, 0, 0)):
        n = self.node("ShaderNodeMapping")
        self.set(n.inputs["Vector"], vec if vec is not None else self.coord())
        n.inputs["Scale"].default_value = (scale,) * 3 if isinstance(scale, (int, float)) else scale
        n.inputs["Location"].default_value = loc
        n.inputs["Rotation"].default_value = [math.radians(a) for a in rot]
        return n.outputs[0]

    def scan(self, set_id, scale=1.0, vec=None, blend=0.3, maps=("Color", "Roughness", "Displacement"), box=True):
        """ambientCG 掃描材質（方盒投影到物體座標）。回傳 {map: socket}。"""
        d = os.path.join(TEX_SRC, set_id)
        v = self.mapping(vec, scale)
        out = {}
        for mp in maps:
            fn = next((f for f in os.listdir(d) if f.endswith(f"_{mp}.jpg")), None)
            if not fn:
                continue
            img = bpy.data.images.load(os.path.join(d, fn), check_existing=True)
            if mp != "Color":
                img.colorspace_settings.name = "Non-Color"
            n = self.node("ShaderNodeTexImage", image=img)
            if box:
                n.projection = "BOX"
                n.projection_blend = blend
            self.nt.links.new(v, n.inputs[0])
            out[mp] = n.outputs[0]
        return out

    def noise(self, scale, detail=3.0, rough=0.55, dist=0.0, vec=None, out="Fac"):
        n = self.node("ShaderNodeTexNoise")
        self.set(n.inputs["Vector"], vec if vec is not None else self.coord())
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = dist
        return n.outputs[out]

    def voronoi(self, scale, feature="F1", vec=None, out="Distance", rand=1.0):
        n = self.node("ShaderNodeTexVoronoi", feature=feature)
        self.set(n.inputs["Vector"], vec if vec is not None else self.coord())
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rand
        return n.outputs[out]

    def wave(self, scale, vec=None, dist=0.0, bands="X", detail=2.0, profile="SIN"):
        n = self.node("ShaderNodeTexWave", bands_direction=bands, wave_profile=profile)
        self.set(n.inputs["Vector"], vec if vec is not None else self.coord())
        n.inputs["Scale"].default_value = scale
        n.inputs["Distortion"].default_value = dist
        n.inputs["Detail"].default_value = detail
        return n.outputs["Fac"]

    def ramp(self, fac, stops, interp="LINEAR"):
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p
            e.color = (c, c, c, 1) if isinstance(c, (int, float)) else (*c[:3], 1)
        self.set(n.inputs[0], fac)
        return n.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMixRGB", blend_type=blend)
        self.set(n.inputs[0], fac)
        self.set(n.inputs[1], a)
        self.set(n.inputs[2], b)
        return n.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs[0]

    def sep(self, vec):
        n = self.node("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], vec)
        return n.outputs

    def comb(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        for i, s in enumerate((x, y, z)):
            self.set(n.inputs[i], s)
        return n.outputs[0]

    def geom(self, out="Pointiness"):
        return self.node("ShaderNodeNewGeometry").outputs[out]

    def hsv(self, col, h=0.5, s=1.0, v=1.0):
        n = self.node("ShaderNodeHueSaturation")
        n.inputs["Hue"].default_value = h
        n.inputs["Saturation"].default_value = s
        n.inputs["Value"].default_value = v
        self.set(n.inputs["Color"], col)
        return n.outputs[0]

    def bump(self, height, strength=0.5, dist=0.01, normal=None):
        n = self.node("ShaderNodeBump")
        n.inputs["Strength"].default_value = strength
        n.inputs["Distance"].default_value = dist
        self.set(n.inputs["Height"], height)
        if normal is not None:
            self.set(n.inputs["Normal"], normal)
        return n.outputs[0]

    def finish(self, color, rough=0.8, metal=0.0, normal=None, emit=None, emit_strength=1.0):
        p = self.node("ShaderNodeBsdfPrincipled", name="M_full")
        self.set(p.inputs["Base Color"], color)
        self.set(p.inputs["Roughness"], rough)
        self.set(p.inputs["Metallic"], metal)
        self.set(p.inputs["Normal"], normal)
        if emit is not None:
            self.set(p.inputs["Emission Color"], emit)
            p.inputs["Emission Strength"].default_value = emit_strength
        ec = self.node("ShaderNodeEmission", name="M_color")
        self.set(ec.inputs[0], color)
        cb = self.node("ShaderNodeCombineColor")
        cb.inputs[0].default_value = 1.0
        self.set(cb.inputs[1], rough)
        self.set(cb.inputs[2], metal)
        eo = self.node("ShaderNodeEmission", name="M_orm")
        self.nt.links.new(cb.outputs[0], eo.inputs[0])
        ee = self.node("ShaderNodeEmission", name="M_emit")
        self.set(ee.inputs[0], emit if emit is not None else (0, 0, 0))
        self.node("ShaderNodeOutputMaterial", name="M_out")
        self.node("ShaderNodeTexImage", name="M_bake")
        set_mode(self.mat, "full")
        return self


def set_mode(mat, mode, image=None):
    nt = mat.node_tree
    if "M_out" not in nt.nodes:
        return
    nt.links.new(nt.nodes["M_" + mode].outputs[0], nt.nodes["M_out"].inputs[0])
    bk = nt.nodes["M_bake"]
    if image:
        bk.image = image
    for n in nt.nodes:
        n.select = False
    bk.select = True
    nt.nodes.active = bk


# ------------------------------------------------------------------ 組裝、圖集烘焙、最終材質
def pack_uv(ob, margin=0.008, hide=None):
    """hide: 每個面一個 bool，True 的面不參與這次打包（給第二組圖集用）。"""
    activate(ob)
    ob.data.uv_layers.active = ob.data.uv_layers["UVMap"]
    if hide is not None:
        ob.data.polygons.foreach_set("hide", hide)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=margin, rotate=True, merge_overlap=True)
    if hide is not None:
        bpy.ops.mesh.reveal()
    bpy.ops.object.mode_set(mode="OBJECT")


def _subset(final, mats, name):
    t = dup(final, name)
    keep = {i for i, s in enumerate(t.material_slots) if s.material in mats}
    bm = bmesh.new()
    bm.from_mesh(t.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in keep], context="FACES")
    bm.to_mesh(t.data)
    bm.free()
    return t


def _px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def use_gpu():
    """有 NVIDIA 顯卡就用 GPU 烘焙（快很多）；沒有就維持 CPU。"""
    sc = bpy.context.scene
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                pr.compute_device_type = kind
            except TypeError:
                continue
            pr.get_devices()
            devs = [d for d in pr.devices if d.type == kind]
            if devs:
                for d in pr.devices:
                    d.use = d.type == kind
                sc.cycles.device = "GPU"
                return kind
    except Exception as e:
        print("[gpu] 無法啟用：", e)
    sc.cycles.device = "CPU"
    return "CPU"


def bake_atlas(final, organics, out_prefix, size=1024, ao_mix=0.75, extrusion=0.025, emit_size=512, quality=88, ao_dist=0.5, only=None):
    """final: 已合併且 UV 已打包的低模；organics: [(high物件, PMat)]。其餘材質槽自我烘焙。
    產生 <prefix>_basecolor.jpg / _normal.jpg / _orm.jpg / _emissive.jpg 並回傳路徑 dict。"""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    print("[bake] device", use_gpu())
    sc.world.light_settings.distance = ao_dist
    fills = dict(color=(0.2, 0.2, 0.2, 1), orm=(1, 0.8, 0, 1), emit=(0, 0, 0, 1), normal=(0.5, 0.5, 1, 1), ao=(1, 1, 1, 1))
    imgs = {}
    for k, c in fills.items():
        im = bpy.data.images.new(f"bake_{k}", size, size, alpha=False)
        im.generated_color = c
        im.colorspace_settings.name = "sRGB" if k in ("color", "emit") else "Non-Color"
        imgs[k] = im
    omats = [m.mat for _, m in organics]
    allm = [s.material for s in final.material_slots]
    inc = [m for m in allm if only is None or m in only]
    temps = [(_subset(final, [m.mat], "bk_" + m.mat.name), [h]) for h, m in organics if m.mat in inc]
    dm = [m for m in inc if m not in omats]
    if dm:
        temps.append((_subset(final, dm, "bk_direct"), None))
    rest = [m for m in allm if m not in inc]
    occ = _subset(final, rest, "bk_occluder") if rest else None  # 另一組圖集的面只當 AO 遮擋物
    final.hide_render = True
    bk = sc.render.bake
    bk.margin = 3
    bk.margin_type = "EXTEND"
    bk.use_clear = False
    bk.cage_extrusion = extrusion
    bk.max_ray_distance = extrusion * 3
    bk.normal_space = "TANGENT"
    for t, highs in temps:
        for o, hh in temps:
            o.hide_render = (o is not t) and hh is not None
        for chan, btype, mode, smp in (("color", "EMIT", "color", 4), ("orm", "EMIT", "orm", 2), ("emit", "EMIT", "emit", 6),
                                       ("normal", "NORMAL", "full", 2), ("ao", "AO", "full", 24)):
            sc.cycles.samples = smp
            for m in allm:
                set_mode(m, mode, imgs[chan])
            # AO 直接在低模上算（高模彼此、與其他零件重疊的地方，從籠面打出的射線會落在幾何內部，烘出一片片黑三角）
            ao_low = chan == "ao"
            hs_all = [h for h, _ in organics]
            for h in hs_all:
                h.hide_render = ao_low
            if ao_low:
                for o, _ in temps:
                    o.hide_render = False
            activate(t, () if ao_low else (highs or ()))
            bk.use_selected_to_active = bool(highs) and not ao_low
            bpy.ops.object.bake(type=btype)
            for h in hs_all:
                h.hide_render = False
            if ao_low:
                for o, hh in temps:
                    o.hide_render = (o is not t) and hh is not None
        print("[bake]", t.name, "done")
    for m in allm:
        set_mode(m, "full")
    for t, _ in temps:
        bpy.data.objects.remove(t)
    if occ:
        bpy.data.objects.remove(occ)
    final.hide_render = False
    col, ao, orm = _px(imgs["color"]), _px(imgs["ao"]), _px(imgs["orm"])
    col[..., :3] *= (1 - ao_mix) + ao_mix * ao[..., :1]
    orm[..., 0] = ao[..., 0]
    imgs["color"].pixels.foreach_set(col.ravel())
    imgs["orm"].pixels.foreach_set(orm.ravel())
    imgs["emit"].scale(emit_size, emit_size)
    os.makedirs(os.path.dirname(out_prefix), exist_ok=True)
    paths = {}
    for k, suf in (("color", "basecolor"), ("normal", "normal"), ("orm", "orm"), ("emit", "emissive")):
        p = f"{out_prefix}_{suf}.jpg"
        imgs[k].filepath_raw = p
        imgs[k].file_format = "JPEG"
        imgs[k].save(quality=quality if k != "normal" else min(95, quality + 4))
        paths[k] = p
    for im in imgs.values():
        bpy.data.images.remove(im)
    return paths


def final_material(name, paths, emit_strength=1.0, has_emit=True, normal_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(k, cs):
        im = bpy.data.images.load(paths[k])
        im.colorspace_settings.name = cs
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = im
        return n

    c = tex("color", "sRGB")
    nt.links.new(c.outputs[0], p.inputs["Base Color"])
    o = tex("orm", "Non-Color")
    sp = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(o.outputs[0], sp.inputs[0])
    nt.links.new(sp.outputs[1], p.inputs["Roughness"])
    nt.links.new(sp.outputs[2], p.inputs["Metallic"])
    ng = bpy.data.node_groups.get("glTF Material Output")
    if not ng:
        ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        ng.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        ng.nodes.new("NodeGroupInput")
    g = nt.nodes.new("ShaderNodeGroup")
    g.node_tree = ng
    nt.links.new(sp.outputs[0], g.inputs[0])
    n = tex("normal", "Non-Color")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = normal_strength
    nt.links.new(n.outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], p.inputs["Normal"])
    if has_emit:
        e = tex("emit", "sRGB")
        nt.links.new(e.outputs[0], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit_strength
    return m


def assemble(name, arm, organics, directs, out_prefix, size=1024, emit_strength=3.0, uv_margin=0.008, normal_strength=1.0, atlas2=None, **bake_kw):
    """organics: [(high, low, src, PMat)]；directs: 已有 UVMap／權重／PMat 的零件。回傳最終蒙皮網格。"""
    lows = [o[1] for o in organics]
    # 每個零件的 UV 先錯開，只有同一個 "uvg" 群組（例如共用版面的書頁）會重疊並在打包時合併成同一塊
    for i, o in enumerate(lows + directs):
        g = o.get("uvg")
        du = 10.0 * (i + 1) if g is None else 9000.0 + 10.0 * g
        uvl = o.data.uv_layers["UVMap"]
        arr = np.empty(len(uvl.data) * 2, np.float32)
        uvl.data.foreach_get("uv", arr)
        arr[0::2] += du
        uvl.data.foreach_set("uv", arr)
    base = directs[0] if directs else lows[0]
    final = join([base] + [o for o in directs + lows if o is not base], name)
    final.data.uv_layers.active = final.data.uv_layers["UVMap"]
    mats2 = [m.mat for m in (atlas2 or [])]
    is2 = [final.material_slots[p.material_index].material in mats2 for p in final.data.polygons]
    org = [(o[0], o[3]) for o in organics]
    if mats2:
        # atlas2 內的材質（例如板甲）獨占第二組圖集
        pack_uv(final, uv_margin, hide=is2)
        pack_uv(final, uv_margin, hide=[not f for f in is2])
        m1 = [sl.material for sl in final.material_slots if sl.material not in mats2]
        pa = bake_atlas(final, org, out_prefix, size=size, only=m1, **bake_kw)
        pb = bake_atlas(final, org, out_prefix + "_b", size=size, only=mats2, **bake_kw)
        fms = [final_material(name + "_mat", pa, emit_strength, normal_strength=normal_strength),
               final_material(name + "_mat_b", pb, emit_strength, normal_strength=normal_strength)]
    else:
        pack_uv(final, uv_margin)
        fms = [final_material(name + "_mat", bake_atlas(final, org, out_prefix, size=size, **bake_kw), emit_strength, normal_strength=normal_strength)]
    final.data.materials.clear()
    for fm in fms:
        final.data.materials.append(fm)
    final.data.polygons.foreach_set("material_index", [1 if f else 0 for f in is2])
    if "puv" in final.data.uv_layers:
        final.data.uv_layers.remove(final.data.uv_layers["puv"])
    for o in organics:
        for ob in (o[0], o[2]):
            bpy.data.objects.remove(ob)
    bind(final, arm)
    tris = sum(len(p.vertices) - 2 for p in final.data.polygons)
    print(f"[assemble] {name}: {tris} tris, {len(final.data.vertices)} verts")
    return final


# ------------------------------------------------------------------ 動畫
def sym(d):
    """{'UpperArm': (rx,ry,rz)} → 左右對稱展開（.R 的 Y、Z 反號）。"""
    out = {}
    for k, v in d.items():
        out[k + ".L"] = v
        out[k + ".R"] = (v[0], -v[1], -v[2]) + tuple(v[3:])
    return out


class Animator:
    """姿勢以「骨架空間世界軸」歐拉角（度，XYZ）描述：+X 前彎／手臂後擺、+Z 向左轉、+Y 向左傾。
    位移鍵用 'Bone:loc'（骨架空間公尺）。每個動作建立一條靜音 NLA track。"""

    def __init__(self, arm, base=None, always=("Hips:loc",)):
        self.arm = arm
        self.base = base or {}
        self.M = {b.name: b.matrix_local.to_3x3() for b in arm.data.bones}
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
        if not arm.animation_data:
            arm.animation_data_create()
        self.actions = {}
        self.legs = []
        self.plants = []
        self.always = always
        self.meta = {}
        self.ground_r = {"*": 0.04}
        self.ground_skip = set()

    def add_leg(self, upper, lower, feet, key):
        """腿部 IK（烘成 FK 關鍵格）：腳踝預設釘在靜止位置，可用 key（例如 'Foot.L:ik'）給
        (dx, dy, dz[, 俯仰度]) 位移；feet 內的骨頭維持世界朝向（腳掌貼地）。"""
        b = self.arm.data.bones
        P0, K0, A0 = b[upper].head_local.copy(), b[lower].head_local.copy(), b[feet[0]].head_local.copy()
        ax = (A0 - P0).normalized()
        pole = (K0 - P0) - ax * (K0 - P0).dot(ax)
        self.legs.append(dict(upper=upper, lower=lower, feet=feet, key=key, P0=P0, K0=K0, A0=A0, pole=pole.normalized(),
                              l1=(K0 - P0).length, l2=(A0 - K0).length, parent=b[upper].parent.name))

    def add_plant(self, bone, key):
        """拄地：bone（頭=握點、尾朝上）的底端自動落在地面，並朝靜止時的落點方向傾斜。
        key（例如 'Staff:plant'）的值 0~1 = FK 與拄地之間的混合。"""
        b = self.arm.data.bones[bone]
        d = (b.tail_local - b.head_local).normalized()
        L0 = b.head_local.z / max(d.z, 1e-3)
        self.plants.append(dict(bone=bone, key=key, parent=b.parent.name, dir=d, length=L0, P0=b.head_local - d * L0))

    def _solve_plants(self, act, keys, last):
        arm = self.arm
        rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
        arm.animation_data.action = act
        out = {pl["bone"]: [] for pl in self.plants}
        for f in range(0, last + 1):
            bpy.context.scene.frame_set(f)
            for pl in self.plants:
                bn = pl["bone"]
                w = self._ik_val(keys, pl["key"], f)[0]
                PM = arm.pose.bones[pl["parent"]].matrix.copy()
                base = PM @ rest[pl["parent"]].inverted() @ rest[bn]
                G = base.translation
                fk = arm.pose.bones[bn].matrix.to_3x3()
                Lh, P0 = pl["length"], pl["P0"]
                hz = Vector((P0.x - G.x, P0.y - G.y, 0))
                if G.z >= Lh:
                    T = Vector((P0.x, P0.y, 0))
                else:
                    hz = hz.normalized() if hz.length > 1e-4 else Vector((0, -1, 0))
                    T = Vector((G.x, G.y, 0)) + hz * math.sqrt(max(Lh * Lh - G.z * G.z, 0))
                up = (G - T).normalized()
                aim = pl["dir"].rotation_difference(up).to_matrix() @ rest[bn].to_3x3()
                q = fk.to_quaternion().slerp(aim.to_quaternion(), min(1.0, max(0.0, w)))
                M = q.to_matrix().to_4x4()
                M.translation = G
                ql = (base.inverted() @ M).to_quaternion()
                if out[bn] and out[bn][-1].dot(ql) < 0:
                    ql.negate()
                out[bn].append(ql)
        for bn, qs in out.items():
            path = f'pose.bones["{bn}"].rotation_quaternion'
            for fc in [c for c in act.fcurves if c.data_path == path]:
                act.fcurves.remove(fc)
            for i in range(4):
                fc = act.fcurves.new(path, index=i, action_group=bn)
                for f, q in enumerate(qs, 0):
                    fc.keyframe_points.insert(f, q[i], options={"FAST"}).interpolation = "LINEAR"
                fc.update()
        arm.animation_data.action = None

    def _ik_val(self, keys, key, f):
        pts = [(k[0], k[1].get(key, self.base.get(key, (0, 0, 0, 0)))) for k in keys]
        pts = [(fr, (v,) if isinstance(v, (int, float)) else tuple(v)) for fr, v in pts]
        pts = [(fr, tuple(v) + (0,) * (4 - len(v))) for fr, v in pts]
        if f <= pts[0][0]:
            return pts[0][1]
        for i, ((f0, v0), (f1, v1)) in enumerate(zip(pts, pts[1:])):
            if f <= f1:
                s = min(1.0, max(0.0, (f - f0) / max(f1 - f0, 1e-6)))
                lin = len(keys[i]) > 2 and keys[i][2] == "L"
                md = keys[i + 1][2] if len(keys[i + 1]) > 2 else None
                t = s if lin else EASE.get(md, _sst)(s)
                return tuple(a + (c - a) * t for a, c in zip(v0, v1))
        return pts[-1][1]

    def _solve_legs(self, act, keys, last):
        arm = self.arm
        rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
        arm.animation_data.action = act
        curves = {}
        prevq = {}
        for f in range(0, last + 1):
            bpy.context.scene.frame_set(f)
            for lg in self.legs:
                par = arm.pose.bones[lg["parent"]].matrix.copy()
                D = par @ rest[lg["parent"]].inverted()
                D3 = D.to_3x3()
                off = self._ik_val(keys, lg["key"], f)
                P = D @ lg["P0"]
                A = lg["A0"] + Vector(off[:3])
                l1, l2 = lg["l1"], lg["l2"]
                v = A - P
                d = min(max(v.length, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
                dr = v.normalized()
                pole = D3 @ lg["pole"]
                pole = pole - dr * pole.dot(dr)
                pole = pole.normalized() if pole.length > 1e-5 else dr.orthogonal().normalized()
                a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
                h = math.sqrt(max(l1 * l1 - a * a, 0.0))
                K = P + dr * a + pole * h
                A = K + (P + dr * d - K).normalized() * l2
                S = (D3 @ (lg["K0"] - lg["P0"])).rotation_difference(K - P).to_matrix()
                Mu = (S @ D3 @ rest[lg["upper"]].to_3x3()).to_4x4()
                Mu.translation = P
                S2 = (S @ D3 @ (lg["A0"] - lg["K0"])).rotation_difference(A - K).to_matrix()
                Ml = (S2 @ S @ D3 @ rest[lg["lower"]].to_3x3()).to_4x4()
                Ml.translation = K
                chain = [(lg["upper"], Mu, par, lg["parent"]), (lg["lower"], Ml, Mu, lg["upper"])]
                Rp = Euler((math.radians(off[3]), 0, 0)).to_matrix()
                pm, pn, pos = Ml, lg["lower"], A
                for i, fb in enumerate(lg["feet"]):
                    Mf = ((Rp if i == 0 else Matrix.Identity(3)) @ rest[fb].to_3x3()).to_4x4()
                    Mf.translation = pos
                    chain.append((fb, Mf, pm, pn))
                    if i + 1 < len(lg["feet"]):
                        pos = pos + Rp @ (rest[lg["feet"][i + 1]].translation - rest[fb].translation)
                    pm, pn = Mf, fb
                for bn, M, PM, pname in chain:
                    basis = (PM @ rest[pname].inverted() @ rest[bn]).inverted() @ M
                    q = basis.to_quaternion()
                    if bn in prevq and prevq[bn].dot(q) < 0:
                        q.negate()
                    prevq[bn] = q.copy()
                    if bn not in curves:
                        curves[bn] = [act.fcurves.new(f'pose.bones["{bn}"].rotation_quaternion', index=i, action_group=bn) for i in range(4)]
                    for i, fc in enumerate(curves[bn]):
                        fc.keyframe_points.insert(f, q[i], options={"FAST"}).interpolation = "LINEAR"
        for fcs in curves.values():
            for fc in fcs:
                fc.update()
        arm.animation_data.action = None

    def _q(self, bone, e):
        R = Euler([math.radians(a) for a in e[:3]], e[3] if len(e) > 3 else "XYZ").to_matrix()
        M = self.M[bone]
        return (M.inverted() @ R @ M).to_quaternion()

    def _keyed_curves(self, act, keys, lag, last, loop, ikb):
        chans = set(self.base)
        for k in keys:
            chans |= set(k[1])
        chans |= set(self.M) | set(self.always)
        chans = {c for c in chans if not c.endswith(":ik") and not c.endswith(":plant") and c not in ikb}
        for ch in sorted(chans):
            isloc = ch.endswith(":loc")
            bn = ch[:-4] if isloc else ch
            if bn not in self.M:
                raise KeyError(f"{act.name}: 沒有骨頭 {bn}")
            d = lag.get(bn, 0)
            path = f'pose.bones["{bn}"].' + ("location" if isloc else "rotation_quaternion")
            fcs = [act.fcurves.new(path, index=i, action_group=bn) for i in range(3 if isloc else 4)]
            prev = None
            kps = [[] for _ in fcs]
            for k in keys:
                if loop:
                    f = k[0] + d
                else:
                    f = min(k[0] + d, last - 1) if 0 < k[0] < last else k[0]
                v = k[1].get(ch, self.base.get(ch, (0, 0, 0)))
                if isloc:
                    val = self.M[bn].inverted() @ Vector(v)
                else:
                    val = self._q(bn, v)
                    if prev is not None and prev.dot(val) < 0:
                        val.negate()
                    prev = val.copy()
                for i, fc in enumerate(fcs):
                    kp = fc.keyframe_points.insert(f, val[i], options={"FAST"})
                    kp.interpolation = "LINEAR" if (len(k) > 2 and k[2] == "L") else "BEZIER"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
                    kps[i].append(k)
            # 抵達緩動：設在前一個關鍵格（keyframe_points 依格號排序）
            for i, fc in enumerate(fcs):
                pts = list(fc.keyframe_points)
                ks = kps[i]
                if len(pts) != len(ks):
                    continue
                for j in range(len(pts) - 1):
                    k0, k1 = ks[j], ks[j + 1]
                    md = k1[2] if len(k1) > 2 else None
                    if md in BL_EASE and not (len(k0) > 2 and k0[2] == "L"):
                        it, ea = BL_EASE[md]
                        pts[j].interpolation = it
                        if ea:
                            pts[j].easing = ea
            for fc in fcs:
                if loop:
                    # 循環：先用 Cycles 修飾讓延遲（lag）的鍵繞回開頭、切線也循環，再烘成 0..last 的逐格鍵，
                    # 確保片段長度正好一個週期、首尾同值（匯出時不會多出延遲的尾巴）
                    fc.modifiers.new("CYCLES")
                    fc.update()
                    vals = [fc.evaluate(f) for f in range(0, last + 1)]
                    vals[-1] = vals[0]
                    fc.modifiers.remove(fc.modifiers[0])
                    fc.keyframe_points.clear()
                    fc.keyframe_points.add(last + 1)
                    co = np.empty((last + 1) * 2)
                    co[0::2] = np.arange(last + 1)
                    co[1::2] = vals
                    fc.keyframe_points.foreach_set("co", co)
                    fc.keyframe_points.foreach_set("interpolation", [1] * (last + 1))
                fc.update()

    def _measure(self, act, last, pts):
        """逐格量出骨頭位置：pts = [(骨名, 'head'|'tail')]，回傳 {pt: [Vector...]}。"""
        arm = self.arm
        arm.animation_data.action = act
        out = {p: [] for p in pts}
        for f in range(0, last + 1):
            bpy.context.scene.frame_set(f)
            for p in pts:
                pb = arm.pose.bones[p[0]]
                out[p].append(arm.matrix_world @ (pb.head if p[1] == "head" else pb.tail))
        arm.animation_data.action = None
        return out

    def action(self, name, keys, lag=None, loop=False, hits=None, ground=True):
        """keys: [(frame, pose_dict[, mode])]；mode 'L' = 從這格到下一格用線性；
        in/in3/out/out3/io = 抵達這格那一段的緩動。片段一律從第 0 格開始。lag: {bone: 延遲格數}（骨頭逐節延遲＝overlap）。
        hits: [(標記格, 骨名)]，在標記附近找該骨尾端速度峰值當命中格。ground：身體低於地面就抬高骨盆。"""
        lag = lag or {}
        off = keys[0][0]
        keys = [(k[0] - off,) + tuple(k[1:]) for k in keys]
        act = bpy.data.actions.new(name)
        ikb = {b for lg in self.legs for b in [lg["upper"], lg["lower"]] + lg["feet"]}
        last = keys[-1][0]
        self._keyed_curves(act, keys, lag, last, loop, ikb)
        if self.plants:
            self._solve_plants(act, keys, last)
        if self.legs:
            self._solve_legs(act, keys, last)
        lowers = [lg["lower"] for lg in self.legs]
        if ground:
            skip = set(ikb) - set(lowers)
            gb = [b.name for b in self.arm.data.bones if b.name not in skip and b.name != "Root" and b.name not in self.ground_skip]
            pts = [(b, "head") for b in gb] + [(b, "tail") for b in gb if b not in lowers]
            P = self._measure(act, last, pts)
            lift = np.zeros(last + 1)
            worst = {}
            for p, arr in P.items():
                r = self.ground_r.get(p[0], self.ground_r.get("*", 0.04))
                for f, v in enumerate(arr):
                    if r - v.z > lift[f]:
                        lift[f] = r - v.z
                        worst[f] = p
            if lift.max() > 0.005:
                n = len(lift)
                dl = np.array([lift[max(0, i - 2):i + 3].max() for i in range(n)])
                kk = np.exp(-0.5 * (np.arange(-4, 5) / 1.6) ** 2)
                kk /= kk.sum()
                lift = np.maximum(np.convolve(np.pad(dl, 4, mode="edge"), kk, mode="valid"), lift)
                if loop:
                    lift[-1] = lift[0]
                path = 'pose.bones["Hips"].location'
                old = sorted([c for c in act.fcurves if c.data_path == path], key=lambda c: c.array_index)
                vals = np.array([[c.evaluate(f) for f in range(n)] for c in old]) if len(old) == 3 else np.zeros((3, n))
                for c in old:
                    act.fcurves.remove(c)
                dz = self.M["Hips"].inverted() @ Vector((0, 0, 1))
                for i in range(3):
                    fc = act.fcurves.new(path, index=i, action_group="Hips")
                    fc.keyframe_points.add(n)
                    co = np.empty(n * 2)
                    co[0::2] = np.arange(n)
                    co[1::2] = vals[i] + lift * dz[i]
                    fc.keyframe_points.foreach_set("co", co)
                    fc.keyframe_points.foreach_set("interpolation", [1] * n)
                    fc.update()
                drop = set(ikb) | {pl["bone"] for pl in self.plants}
                for c in [c for c in act.fcurves if any(c.data_path == f'pose.bones["{b}"].rotation_quaternion' for b in drop)]:
                    act.fcurves.remove(c)
                if self.plants:
                    self._solve_plants(act, keys, last)
                if self.legs:
                    self._solve_legs(act, keys, last)
                fw = int(np.argmax(lift))
                print(f"  ground {name}: 骨盆抬高最多 {lift.max() * 100:.1f}cm（第 {fw} 格，{worst.get(fw)}）", flush=True)
        hit_t = []
        if hits:
            P = self._measure(act, last, [(b, "tail") for _, b in hits])
            for m, b in hits:
                m = m - off
                arr = P[(b, "tail")]
                best, bf = -1.0, m
                for f in range(max(1, m - 2), min(last - 1, m + 3) + 1):
                    v = (arr[f + 1] - arr[f - 1]).length
                    if v > best:
                        best, bf = v, f
                hit_t.append(round(bf / 30.0, 3))
        self.meta[name] = dict(dur=round(last / 30.0, 3), loop=bool(loop), **({"hits": hit_t} if hits else {}))
        tr = self.arm.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 0, act)
        tr.mute = True
        self.actions[name] = (act, last)
        print(f"ACTION {name}: 0-{last} ({last / 30:.2f}s) hits={hit_t}", flush=True)
        return act

    def show(self, name, frame):
        self.arm.animation_data.action = self.actions[name][0] if name else None
        if not name:
            for pb in self.arm.pose.bones:
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.location = (0, 0, 0)
        bpy.context.scene.frame_set(frame)


def clear_actions(arm):
    if arm.animation_data:
        arm.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)


def export_glb(path, arm, mesh, frame_step=1):
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.scene.frame_set(0)
    activate(arm, [mesh])
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_yup=True, export_skins=True,
                              export_image_format="AUTO", export_optimize_animation_size=True,
                              export_force_sampling=True, export_frame_step=frame_step, export_tangents=False,
                              export_def_bones=False)
    print(f"[export] {path} {os.path.getsize(path) / 1048576:.2f} MB")


# ------------------------------------------------------------------ 預覽
cam_rig = [None]


def studio(height, floor=True):
    """深色中性背景＋三點打光。"""
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "CYCLES"
    sc.eevee.taa_render_samples = 32
    sc.view_settings.view_transform = "Standard"
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.037, 0.042, 1)
    bg.inputs[1].default_value = 1.0
    H = height

    def area(name, loc, energy, size, color):
        d = bpy.data.lights.new(name, "AREA")
        d.energy, d.size, d.color = energy, size, color
        o = bpy.data.objects.new(name, d)
        sc.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, H * 0.55)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o

    ls = [area("Key", (-H * 1.1, -H * 1.5, H * 1.5), 95 * H * H, H * 0.9, (1.0, 0.95, 0.88)),
          area("Fill", (H * 1.6, -H * 1.0, H * 0.6), 22 * H * H, H * 1.4, (0.75, 0.85, 1.0)),
          area("Rim", (H * 0.6, H * 1.7, H * 1.5), 120 * H * H, H * 0.8, (0.85, 0.92, 1.0))]
    rig = bpy.data.objects.new("LightRig", None)
    sc.collection.objects.link(rig)
    for o in ls:
        o.parent = rig
    cam_rig[0] = rig
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=60)
        fl = bpy.context.object
        fl.name = "PreviewFloor"
        m = bpy.data.materials.new("PreviewFloor")
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.02, 0.021, 0.023, 1)
        b.inputs["Roughness"].default_value = 0.85
        fl.data.materials.append(m)
        ls.append(fl)
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cd.lens = 60
    return cam, ls


def aim(cam, target, dist, az, el=8, rig=True):
    """az=0 從正前方（-Y）看；az=90 從角色左側（+X）看。"""
    a, e = math.radians(az), math.radians(el)
    t = Vector(target)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    if cam_rig[0] and rig:
        cam_rig[0].rotation_euler = (0, 0, a)


def render(path, res=(640, 800)):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_views(cam, out_dir, prefix, height, extra=1.0, res=(600, 760), center=None):
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for nm, az in (("front", 0), ("side", 90), ("back", 180), ("q34", -35)):
        aim(cam, center or (0, 0, height * 0.5), height * 2.35 * extra, az)
        p = os.path.join(out_dir, f"{prefix}_{nm}.png")
        render(p, res)
        out.append(p)
    return out


def render_actions(cam, anim, out_dir, prefix, height, frames=5, extra=1.0, res=(400, 440), az=-40, center=None, frames_map=None):
    """每個動作平均取 frames 格，輸出 <prefix>__<Action>__<i>_<frame>.png（之後用 make_sheet.py 拼圖）。"""
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.startswith(prefix + "__"):
            os.remove(os.path.join(out_dir, f))
    aim(cam, center or (0, 0, height * 0.48), height * 3.0 * extra, az, 10, rig=False)
    for name, (act, last) in anim.actions.items():
        fl = (frames_map or {}).get(name) or [round(last * i / (frames - 1)) for i in range(frames)]
        for i, f in enumerate(fl):
            anim.show(name, f)
            render(os.path.join(out_dir, f"{prefix}__{name}__{i}_{f:03d}.png"), res)
    anim.show(None, 1)


def gait(p, stride, lift, swing=0.38, d=(0.0, -1.0), pitch=12.0):
    """步態（原地循環）：p 為 0~1 相位；支撐期腳往移動反方向滑，擺動期抬腳前送。回傳 'Foot:ik' 用的 (dx, dy, dz, 俯仰度)。"""
    p %= 1.0
    if p < swing:
        t = p / swing
        x = -stride / 2 + stride * t * t * (3 - 2 * t)
        z = lift * math.sin(math.pi * t) ** 0.8
        pit = pitch * math.sin(math.pi * t) - 0.5 * pitch * math.sin(2 * math.pi * t)
    else:
        t = (p - swing) / (1 - swing)
        x = stride / 2 - stride * t
        z = 0.0
        pit = 0.0
    return (d[0] * x, d[1] * x, z, pit)


def mirror(d):
    """把姿勢左右鏡像：.L/.R 互換、旋轉的 Y/Z 反號、位移 X 反號。"""
    out = {}
    for k, v in d.items():
        nk = k.replace(".L", ".#").replace(".R", ".L").replace(".#", ".R")
        if k.endswith(":loc"):
            out[nk] = (-v[0], v[1], v[2])
        elif k.endswith(":ik"):
            out[nk] = (-v[0],) + tuple(v[1:])
        elif k.endswith(":plant") or isinstance(v, (int, float)):
            out[nk] = v
        else:
            out[nk] = (v[0], -v[1], -v[2]) + tuple(v[3:])
    return out


def write_meta(anim, model, out_dir):
    import json
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, model + ".clipmeta.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(anim.meta, f, ensure_ascii=False, indent=1)
    print("META", p, flush=True)
