"""魂系模式競技場：無頂哥德教堂廢墟（靜態場景）。
用法：blender --background --factory-startup --python build_arena_cathedral.py -- <out.glb> <preview_dir> <out.blend>
造型依據：art/reference/scene_soul_cathedral.jpg
座標：中心在原點、地面 z=0；玩家鏡頭從 -Y 往 +Y 看，玫瑰窗山牆在 +Y。12 m 半徑內只有貼地物件。
貼圖：CC0（ambientCG／Poly Haven），第一次執行時從來源資料夾縮成 1024 JPEG 存到 textures/cathedral/。
"""
import bpy, bmesh, math, sys, os, json, struct, random
import numpy as np
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = argv[0] if len(argv) > 0 else os.path.join(ROOT, "public", "models", "arena_cathedral.glb")
OUT_PREV = argv[1] if len(argv) > 1 else os.path.join(HERE, "preview")
OUT_BLEND = argv[2] if len(argv) > 2 else os.path.join(HERE, "source", "arena_cathedral.blend")
OUT_GLB, OUT_PREV, OUT_BLEND = (os.path.abspath(p) for p in (OUT_GLB, OUT_PREV, OUT_BLEND))
TEX = os.path.join(HERE, "textures", "cathedral")
SRC = r"D:\Documents\ThorWorkSpace\TAI game\素材\blender\textures_src"  # 只讀
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT_PREV, exist_ok=True)

random.seed(20261126)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
TAU = math.tau


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


# ───────────────────────── 貼圖前處理 ─────────────────────────
def prep_tex(key, folder, color, normal, rough, metal=None, size=1024, gain=(1, 1, 1), desat=0.0, q=(82, 80, 78), rmin=0.0, contrast=1.0):
    """把來源 2K 貼圖縮成 size²：<key>_color.jpg、<key>_normal.jpg、<key>_orm.jpg（G=粗糙度、B=金屬度）。"""
    outs = [os.path.join(TEX, f"{key}_{s}.jpg") for s in ("color", "normal", "orm")]
    if all(os.path.exists(p) for p in outs):
        return outs

    def load(fn, cs):
        im = bpy.data.images.load(os.path.join(SRC, folder, fn))
        im.colorspace_settings.name = cs
        im.scale(size, size)
        return im, np.array(im.pixels[:], dtype=np.float32).reshape(size, size, 4)

    def save(arr, path, quality):
        im = bpy.data.images.new("tmp", size, size, alpha=False)
        im.pixels.foreach_set(arr.reshape(-1))
        im.filepath_raw = path
        im.file_format = "JPEG"
        im.save(quality=quality)
        bpy.data.images.remove(im)

    im, c = load(color, "sRGB")
    lum = c[..., :3].mean(axis=2, keepdims=True)
    c[..., :3] = c[..., :3] * (1 - desat) + lum * desat
    mean = c[..., :3].mean()
    c[..., :3] = ((c[..., :3] - mean) * contrast + mean) * np.array(gain, dtype=np.float32)
    c[..., 3] = 1
    save(np.clip(c, 0, 1), outs[0], q[0])
    bpy.data.images.remove(im)
    im, n = load(normal, "Non-Color")
    n[..., 3] = 1
    save(n, outs[1], q[1])
    bpy.data.images.remove(im)
    im, r = load(rough, "Non-Color")
    orm = np.ones((size, size, 4), dtype=np.float32)
    orm[..., 1] = rmin + (1 - rmin) * r[..., 0]
    orm[..., 2] = 0.0
    bpy.data.images.remove(im)
    if metal:
        im, m = load(metal, "Non-Color")
        orm[..., 2] = m[..., 0]
        bpy.data.images.remove(im)
    save(orm, outs[2], q[2])
    return outs


TEXSETS = {
    "stone": prep_tex("stone", "acg_Concrete020", "Concrete020_2K-JPG_Color.jpg", "Concrete020_2K-JPG_NormalGL.jpg",
                      "Concrete020_2K-JPG_Roughness.jpg", gain=(0.60, 0.62, 0.66), desat=0.25, rmin=0.35, contrast=2.2),
    "masonry": prep_tex("masonry", "ph_white_sandstone_bricks", "white_sandstone_bricks_Diffuse_2k.jpg",
                        "white_sandstone_bricks_nor_gl_2k.jpg", "white_sandstone_bricks_Rough_2k.jpg",
                        gain=(0.56, 0.60, 0.66), desat=0.45),
    "ground": prep_tex("ground", "acg_Ground023", "Ground023_2K-JPG_Color.jpg", "Ground023_2K-JPG_NormalGL.jpg",
                       "Ground023_2K-JPG_Roughness.jpg", gain=(0.62, 0.64, 0.62), desat=0.35, rmin=0.6),
    "iron": prep_tex("iron", "acg_Metal028", "Metal028_2K-JPG_Color.jpg", "Metal028_2K-JPG_NormalGL.jpg",
                     "Metal028_2K-JPG_Roughness.jpg", "Metal028_2K-JPG_Metalness.jpg", size=512),
}


# ───────────────────────── 材質 ─────────────────────────
def make_mat(name, texkey=None, color=(1, 1, 1), rough=0.9, metal=0.0, emit=None, emit_strength=1.0, double=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Base Color"].default_value = (*color, 1)
    m.use_backface_culling = not double
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (*color, 1)
    nt.links.new(vc.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    m["_tex"] = None
    if texkey:
        cp, npth, op = TEXSETS[texkey]
        tc = nt.nodes.new("ShaderNodeTexImage")
        tc.image = bpy.data.images.load(cp, check_existing=True)
        tc.name = "TexColor"
        nt.links.new(tc.outputs["Color"], mix.inputs[6])
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = bpy.data.images.load(npth, check_existing=True)
        tn.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nm.inputs["Strength"].default_value = 1.6 if texkey == "stone" else 1.2
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        to = nt.nodes.new("ShaderNodeTexImage")
        to.image = bpy.data.images.load(op, check_existing=True)
        to.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(to.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], b.inputs["Roughness"])
        nt.links.new(sep.outputs[2], b.inputs["Metallic"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m


MATS = {
    "stone": make_mat("Cath_Stone", "stone"),
    "masonry": make_mat("Cath_Masonry", "masonry"),
    "ground": make_mat("Cath_Ground", "ground"),
    "iron": make_mat("Cath_Iron", "iron"),
    "paper": make_mat("Cath_Paper", None, rough=0.85, double=True),
    "grass": make_mat("Cath_Grass", None, rough=0.9, double=True),
    "ember": make_mat("Cath_Ember", None, color=(0.9, 0.25, 0.05), rough=0.8, emit=(1.0, 0.32, 0.05), emit_strength=5.0),
}
UVS = {"stone": 2.6, "masonry": 3.2, "ground": 3.0, "iron": 0.6, "paper": 1.0, "grass": 1.0, "ember": 1.0}
ACC = {k: bmesh.new() for k in MATS}
MOSS = (0.50, 0.66, 0.34)


def vcol(co, n, tint, moss):
    """頂點色：高度污漬＋大塊苔蘚＋小雜訊（線性空間，匯出為 COLOR_0 乘在 baseColor 上）。"""
    n1 = noise.noise(co * 0.22) * 0.5 + 0.5
    n2 = noise.noise(co * 1.4 + Vector((7.1, 3.3, 1.7))) * 0.5 + 0.5
    low = clamp(1 - co.z / 2.2)
    m = moss * clamp((n1 - 0.47) * 2.4 + 0.28 * low + 0.22 * max(n.z, 0.0)) * 0.85
    b = (0.70 + 0.30 * n2) * (1 - 0.32 * low * low)
    return (tint[0] * b * (1 - m + MOSS[0] * m), tint[1] * b * (1 - m + MOSS[1] * m), tint[2] * b * (1 - m + MOSS[2] * m), 1.0)


def emit(bm, mat, M=None, tint=(1, 1, 1), smooth=False, moss=1.0, weld=True, recalc=True, keep_uv=False, keep_col=False, uvs=None):
    """把一個零件（區域座標的 bmesh）做盒狀 UV、轉到世界座標、上頂點色後併入該材質的累積網格。"""
    if weld:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if smooth == "auto":
        sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(42)]
        if sharp:
            bmesh.ops.split_edges(bm, edges=sharp)
    bm.normal_update()
    uv = bm.loops.layers.uv.verify()
    col = bm.loops.layers.float_color.get("Col") or bm.loops.layers.float_color.new("Col")
    s = uvs or UVS[mat]
    if not keep_uv:
        ou, ov = random.random(), random.random()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                u, v = (c.x, c.y) if ax == 2 else ((c.x, c.z) if ax == 1 else (c.y, c.z))
                l[uv].uv = (u / s + ou, v / s + ov)
    if M is not None:
        bm.transform(M)
        bm.normal_update()
    for f in bm.faces:
        f.smooth = bool(smooth)
        if not keep_col:
            for l in f.loops:
                l[col] = vcol(l.vert.co, f.normal, tint, moss)
    me = bpy.data.meshes.new("tmp")
    bm.to_mesh(me)
    bm.free()
    ACC[mat].from_mesh(me)
    bpy.data.meshes.remove(me)


def join(dst, src, M=None):
    if M is not None:
        src.transform(M)
    me = bpy.data.meshes.new("tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def RZ(a):
    return Matrix.Rotation(a, 4, "Z")


def RX(a):
    return Matrix.Rotation(a, 4, "X")


def RY(a):
    return Matrix.Rotation(a, 4, "Y")


def polar(r, a, z=0.0):
    return Vector((r * math.cos(a), r * math.sin(a), z))


def tangent_frame(r, a, z=0.0):
    """區域 +X 沿切線、+Y 朝外（-Y 面向場地中心）。"""
    return T(*polar(r, a, z)) @ RZ(a - math.pi / 2)


# ───────────────────────── 基本形狀 ─────────────────────────
def bm_box(sx, sy, sz, jit=0.0, base=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx + random.uniform(-jit, jit), v.co.y * sy + random.uniform(-jit, jit),
                       (v.co.z + (0.5 if base else 0.0)) * sz + random.uniform(-jit, jit)))
    return bm


def bm_cyl(r1, r2, h, seg, caps=True, base=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r1, radius2=max(r2, 1e-4), depth=h)
    if base:
        bm.transform(T(0, 0, h / 2))
    return bm


def bm_rock(sx, sy, sz, sub=1, rough=0.32):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    o = Vector((random.uniform(0, 99), random.uniform(0, 99), random.uniform(0, 99)))
    for v in bm.verts:
        d = 1 + rough * noise.noise(v.co * 1.3 + o) + random.uniform(-0.08, 0.08)
        v.co = Vector((v.co.x * sx * d, v.co.y * sy * d, max(v.co.z * sz * d, -0.35 * sz)))
    return bm


def bm_sweep(path, depth, thick, closed=False, cap=True):
    """沿 XZ 平面路徑掃出矩形斷面（depth 沿 Y、thick 沿路徑法線）。"""
    bm = bmesh.new()
    n = len(path)
    rings = []
    for i, (x, z) in enumerate(path):
        a = path[(i - 1) % n] if (closed or i > 0) else path[i]
        b = path[(i + 1) % n] if (closed or i < n - 1) else path[i]
        t = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        nx, nz = -t.y, t.x
        rings.append([bm.verts.new((x + nx * s * thick / 2, yy * depth / 2, z + nz * s * thick / 2))
                      for s, yy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for i in range(n if closed else n - 1):
        A, B = rings[i], rings[(i + 1) % n]
        for k in range(4):
            bm.faces.new((A[k], A[(k + 1) % 4], B[(k + 1) % 4], B[k]))
    if not closed and cap:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    return bm


def arch_fn(w, spring, k):
    R = k * w
    c = -w / 2 + R
    return lambda x: spring + math.sqrt(max(R * R - (abs(x) + c) ** 2, 0.0))


def arch_pts(w, spring, k=1.0, n=7):
    """尖拱路徑（左起拱點→拱頂→右起拱點）。"""
    R = k * w
    c = -w / 2 + R
    a1 = math.acos(-c / R)
    left = [(c + R * math.cos(math.pi + (a1 - math.pi) * i / n), spring + R * math.sin(math.pi + (a1 - math.pi) * i / n)) for i in range(n + 1)]
    return left + [(-x, z) for x, z in reversed(left[:-1])]


def circle_pts(r, cx, cz, n, a0=0.0, a1=TAU):
    full = abs(a1 - a0 - TAU) < 1e-6
    m = n if full else n + 1
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cz + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(m)]


def ragged(h, amp, seed, q=0.42, extra=None, lo=0.0):
    def f(x):
        v = h + amp * noise.noise(Vector((x * 0.33, seed * 13.7, 0.5))) + 0.5 * amp * noise.noise(Vector((x * 1.1, seed * 5.1, 9.0)))
        if extra:
            v = extra(x, v)
        return max(lo, round(v / q) * q)
    return f


def sym_diff(A, B):
    pts = sorted(set([z for iv in A + B for z in iv]))
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        if b - a < 1e-5:
            continue
        m = (a + b) / 2
        ina = any(lo <= m <= hi for lo, hi in A)
        inb = any(lo <= m <= hi for lo, hi in B)
        if ina != inb:
            out.append((a, b))
    return out


def bm_arch_wall(width, thick, top_fn, opening=None, step=0.55, base=0.0):
    """階梯狀殘牆，可開一個尖拱洞。opening=(cx, w, sill, spring, k)。區域座標：X 寬、Y 厚、Z 高。"""
    bm = bmesh.new()
    n = max(2, int(round(width / step)))
    xs = [-width / 2 + width * i / n + (random.uniform(-0.3, 0.3) * step if 0 < i < n else 0.0) for i in range(n + 1)]
    smooth_top = getattr(top_fn, "smooth", False)
    az = None
    if opening:
        cx, w, sill, spring, k = opening
        f = arch_fn(w, spring, k)
        az = lambda x: f(x - cx)
        o0, o1 = cx - w / 2, cx + w / 2
        xs = [x for x in xs if not (o0 - 0.2 < x < o0 + 0.2 or o1 - 0.2 < x < o1 + 0.2 or abs(x - cx) < 0.15)]
        m = max(2, int(round(w / 2 / 0.45)))
        xs = sorted([x for x in xs if not (o0 < x < o1)] + [o0 + w * i / (2 * m) for i in range(2 * m + 1)])
    h = thick / 2
    Ls, Rs = [], []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        t = top_fn((x0 + x1) / 2)
        ta, tb = (top_fn(x0 + 1e-4), top_fn(x1 - 1e-4)) if smooth_top else (t, t)
        t = min(ta, tb)
        parts = []
        if opening and x0 >= o0 - 1e-6 and x1 <= o1 + 1e-6:
            if sill > base and t > base:
                parts.append((base, base, min(sill, t), min(sill, t)))
            z0, z1 = az(x0), az(x1)
            if t > max(z0, z1) + 0.2:
                parts.append((z0, z1, ta, tb))
        elif t > base:
            parts.append((base, base, ta, tb))
        for zb0, zb1, zt0, zt1 in parts:
            v = [bm.verts.new(p) for p in ((x0, -h, zb0), (x1, -h, zb1), (x1, -h, zt1), (x0, -h, zt0),
                                           (x0, h, zb0), (x1, h, zb1), (x1, h, zt1), (x0, h, zt0))]
            bm.faces.new((v[0], v[1], v[2], v[3]))
            bm.faces.new((v[5], v[4], v[7], v[6]))
            bm.faces.new((v[3], v[2], v[6], v[7]))
            if zb0 > base or zb1 > base:
                bm.faces.new((v[0], v[4], v[5], v[1]))
        Ls.append([(p[0], p[2]) for p in parts])
        Rs.append([(p[1], p[3]) for p in parts])
    for i in range(len(xs)):
        A = Rs[i - 1] if i > 0 else []
        B = Ls[i] if i < len(Ls) else []
        for a, b in sym_diff(A, B):
            v = [bm.verts.new(p) for p in ((xs[i], -h, a), (xs[i], h, a), (xs[i], h, b), (xs[i], -h, b))]
            bm.faces.new(v)
    return bm


# ───────────────────────── 地面 ─────────────────────────
def build_ground():
    bm = bmesh.new()
    radii = [0.0, 3.0, 6.0, 9.0, 10.6, 11.6, 12.6, 14.0, 16.0, 18.5, 21.5, 25.0, 30.0]
    seg = 56
    uv = bm.loops.layers.uv.verify()
    col = bm.loops.layers.float_color.new("Col")

    def gz(r, a):
        if r < 10.7:
            return -0.03
        if r < 12.7:
            return 0.0
        p = polar(r, a)
        k = clamp((r - 12.7) / 3.0)
        return k * (0.22 * noise.noise(p * 0.18) + 0.08 * noise.noise(p * 0.6)) + clamp((r - 20) / 10) ** 2 * 2.2

    rings = []
    for r in radii:
        if r == 0:
            rings.append([bm.verts.new((0, 0, -0.03))])
        else:
            rings.append([bm.verts.new(polar(r, TAU * j / seg, gz(r, TAU * j / seg))) for j in range(seg)])
    for j in range(seg):
        bm.faces.new((rings[0][0], rings[1][j], rings[1][(j + 1) % seg]))
    for i in range(1, len(radii) - 1):
        for j in range(seg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % seg], rings[i][(j + 1) % seg]))
    bm.normal_update()
    for f in bm.faces:
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.x / UVS["ground"], c.y / UVS["ground"])
            r = c.xy.length
            n1 = noise.noise(c * 0.3) * 0.5 + 0.5
            g = 0.55 + 0.45 * n1
            fade = 1 - 0.55 * clamp((r - 17) / 10)
            l[col] = (g * 0.92 * fade, g * (0.95 + 0.1 * n1) * fade, g * 0.86 * fade, 1)
    emit(bm, "ground", smooth=True, weld=False, recalc=False, keep_uv=True, keep_col=True)


MISSING = []  # 缺石板的位置（長草）
GAPS = []     # 石板縫的位置（縫隙草）


def slab_piece(bm, ri, ro, a0i, a0o, a1i, a1o, ztop, tilt, shade, depth=0.07, tint=(1, 1, 1)):
    uv = bm.loops.layers.uv.verify()
    col = bm.loops.layers.float_color.get("Col") or bm.loops.layers.float_color.new("Col")
    m = max(1, int(math.ceil(abs((a1i + a1o) - (a0i + a0o)) / 2 / math.radians(9))))
    am = (a0i + a0o + a1i + a1o) / 4
    c = polar((ri + ro) / 2, am)
    ins, outs = [], []
    for j in range(m + 1):
        t = j / m
        ins.append(polar(ri, a0i + (a1i - a0i) * t))
        outs.append(polar(ro, a0o + (a1o - a0o) * t))

    def top(p):
        return Vector((p.x, p.y, ztop + tilt[0] * (p.x - c.x) + tilt[1] * (p.y - c.y)))

    ti = [bm.verts.new(top(p)) for p in ins]
    to = [bm.verts.new(top(p)) for p in outs]
    faces = []
    for j in range(m):
        faces.append(bm.faces.new((ti[j], to[j], to[j + 1], ti[j + 1])))
    per = to + ti[::-1]
    perb = [bm.verts.new((v.co.x * 1.0, v.co.y * 1.0, -depth)) for v in per]
    side = []
    for k in range(len(per)):
        k2 = (k + 1) % len(per)
        if (per[k].co - per[k2].co).length < 1e-4:
            continue
        side.append(bm.faces.new((perb[k], perb[k2], per[k2], per[k])))
    ou, ov, ang = random.random(), random.random(), random.choice((0, 1, 2, 3)) * math.pi / 2
    ca, sa = math.cos(ang), math.sin(ang)
    s = UVS["stone"]
    for f in faces:
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = ((p.x * ca - p.y * sa) / s + ou, (p.x * sa + p.y * ca) / s + ov)
            n1 = noise.noise(p * 0.5) * 0.5 + 0.5
            mo = clamp((n1 - 0.5) * 2.5) * 0.7
            b = shade * (0.82 + 0.18 * (noise.noise(p * 2.0) * 0.5 + 0.5))
            l[col] = (tint[0] * b * (1 - mo + MOSS[0] * mo), tint[1] * b * (1 - mo + MOSS[1] * mo), tint[2] * b * (1 - mo + MOSS[2] * mo), 1)
    for f in side:
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = ((p.x + p.y) / s + ou, p.z / s + ov)
            l[col] = (shade * 0.35, shade * 0.36, shade * 0.34, 1)


def build_floor():
    bm = bmesh.new()
    radii = [0.0, 0.95, 2.05, 3.15, 4.25, 5.35, 6.45, 6.85, 7.95, 9.0, 10.0, 10.55]
    gap = 0.014
    for k in range(len(radii) - 1):
        ri, ro = radii[k] + gap, radii[k + 1] - gap
        rm = (ri + ro) / 2
        band = (ro - ri) < 0.5
        kerb = k == len(radii) - 2
        if k == 0:
            nseg, ri = 4, 0.0005
        else:
            nseg = max(6, int(round(TAU * rm / (0.75 if band else (1.1 if kerb else 1.55)))))
        a_off = random.uniform(0, TAU)
        for j in range(nseg):
            a0 = a_off + TAU * j / nseg
            a1 = a_off + TAU * (j + 1) / nseg
            ga = gap / max(rm, 0.5)
            a0 += ga
            a1 -= ga
            am = (a0 + a1) / 2
            c = polar(rm, am)
            nz = noise.noise(c * 0.33 + Vector((3.1, 8.2, 0)))
            if not kerb and not band and k > 0 and rm < 8.2 and nz > 0.33 and random.random() < 0.8:
                MISSING.append((rm, am, (ro - ri) * 0.42, (a1 - a0) * 0.42))
                continue
            if kerb and random.random() < 0.08:
                continue
            shade = random.uniform(0.5, 1.0) * (0.8 if band else 1.0)
            sink = -random.uniform(0.0, 0.03) if random.random() < 0.2 else 0.0
            zt = (0.045 if kerb else 0.0) + random.uniform(-0.006, 0.004) + sink
            tl = (random.uniform(-0.012, 0.012), random.uniform(-0.012, 0.012))
            if random.random() < 0.12:
                GAPS.append((ro, am))
            if not kerb and not band and k > 0 and random.random() < 0.26:
                # 裂成兩塊：斜向裂縫
                f1, f2 = random.uniform(0.3, 0.7), random.uniform(0.3, 0.7)
                ci, co_ = a0 + (a1 - a0) * f1, a0 + (a1 - a0) * f2
                cg = 0.02 / rm
                slab_piece(bm, ri, ro, a0, a0, ci - cg, co_ - cg, zt, tl, shade)
                tl2 = (tl[0] + random.uniform(-0.015, 0.015), tl[1] + random.uniform(-0.015, 0.015))
                slab_piece(bm, ri, ro, ci + cg, co_ + cg, a1, a1, zt - random.uniform(0.0, 0.018), tl2, shade * random.uniform(0.85, 1.0))
                if random.random() < 0.5:
                    GAPS.append((rm, (ci + co_) / 2))
            else:
                slab_piece(bm, ri, ro, a0, a0, a1, a1, zt, tl, shade, depth=0.07)
    emit(bm, "stone", weld=False, recalc=False, keep_uv=True, keep_col=True)
    # 圈外散落的不規則鋪石（貼地）
    for i in range(46):
        r, a = random.uniform(10.9, 12.6), random.uniform(0, TAU)
        b = bm_box(random.uniform(0.5, 1.2), random.uniform(0.4, 0.9), 0.05, jit=0.012, base=True)
        emit(b, "stone", T(*polar(r, a, -0.012)) @ RZ(random.uniform(0, TAU)) @ RX(random.uniform(-0.02, 0.02)), tint=(random.uniform(0.6, 0.95),) * 3)


# ───────────────────────── 建築 ─────────────────────────
PIER_R = 13.6
SPRING = 6.7


def build_pier(a, h, capital=True, r=PIER_R):
    M = T(*polar(r, a)) @ RZ(a + math.pi / 8)
    bm = bmesh.new()
    join(bm, bm_cyl(1.05, 1.0, 0.32, 8))
    join(bm, bm_cyl(0.9, 0.82, 0.3, 8), T(0, 0, 0.32))
    sh = min(h, SPRING - 0.5) if capital else h
    core = bm_cyl(0.56, 0.54, sh - 0.6, 12, caps=True)
    if h < SPRING - 0.5 or not capital:
        for v in core.verts:
            if v.co.z > sh - 0.7:
                v.co.z += random.uniform(-0.55, 0.1)
    join(bm, core, T(0, 0, 0.6))
    for i in range(4):
        hh = sh - 0.6 - (random.uniform(0.0, 1.2) if not capital or h < SPRING - 0.5 else 0.0)
        join(bm, bm_cyl(0.17, 0.165, hh, 7), T(0.56 * math.cos(i * TAU / 4 + TAU / 8), 0.56 * math.sin(i * TAU / 4 + TAU / 8), 0.6))
    for z in (2.6, 4.4):
        if z < sh - 0.5:
            join(bm, bm_cyl(0.66, 0.66, 0.12, 12), T(0, 0, z))
    if capital and h >= SPRING - 0.5:
        join(bm, bm_cyl(0.6, 0.98, 0.42, 8), T(0, 0, SPRING - 0.62))
        join(bm, bm_cyl(1.04, 1.04, 0.2, 8), T(0, 0, SPRING - 0.2))
    emit(bm, "stone", M, smooth="auto", weld=False, recalc=False)
    if capital and h > SPRING + 0.3:
        up = bm_arch_wall(1.5, 1.3, ragged(h - SPRING, 0.5, a * 3 + 1, q=0.4))
        emit(up, "masonry", T(*polar(r, a, SPRING)) @ RZ(a - math.pi / 2))
    return polar(r, a)


def build_arcade(a0, a1, top_h, mode="full", seed=1.0):
    """兩根墩柱之間的尖拱；mode: full／left（只剩 a0 側半拱）／right。"""
    p0, p1 = polar(PIER_R, a0), polar(PIER_R, a1)
    mid = (p0 + p1) / 2
    d = p1 - p0
    L = d.length
    M = T(mid.x, mid.y, SPRING) @ RZ(math.atan2(d.y, d.x))
    w = L - 1.5
    k = 0.82
    path = arch_pts(w - 0.36, 0.0, k, n=7)
    if mode == "left":
        path = path[:random.choice((5, 6))]
    elif mode == "right":
        path = path[-random.choice((5, 6)):]
    rib = bm_sweep(path, 0.95, 0.42)
    if mode != "full":
        ends = sorted(rib.verts, key=lambda v: v.co.z)[-4:]
        for v in ends:
            v.co += Vector((random.uniform(-0.25, 0.25), 0, random.uniform(-0.3, 0.2)))
    emit(rib, "stone", M)
    rib2 = bm_sweep([(x * 0.86, z * 0.86) for x, z in path], 0.6, 0.2)
    emit(rib2, "stone", M, tint=(0.8, 0.8, 0.82))
    if mode == "full":
        apex = arch_fn(w, 0, k)(0)
        wall = bm_arch_wall(L - 1.3, 0.7, ragged(top_h, 0.9, seed, lo=0.0, extra=lambda x, v: max(v, apex + 0.5 - abs(x) * 0.25)), opening=(0, w, -1.0, 0.0, k))
        emit(wall, "masonry", M)
        # 拱上方的小飾帶
        sc = bm_box(L - 1.3, 0.86, 0.16)
        emit(sc, "stone", M @ T(0, 0, apex + 0.42), tint=(0.85, 0.85, 0.88))


def build_rose(M, w, sill, spring, k):
    """玫瑰窗石花格（破損）＋下方尖拱窗櫺。區域 XZ 平面。"""
    f = arch_fn(w, spring, k)
    q = w / 6.4
    cz = spring + 2.75 * q
    R = 2.55 * q
    bm = bmesh.new()
    join(bm, bm_sweep(circle_pts(R, 0, cz, 30, math.radians(78), math.radians(378)), 0.34, 0.24))
    join(bm, bm_sweep(circle_pts(R - 0.33, 0, cz, 26, math.radians(86), math.radians(372)), 0.2, 0.1))
    join(bm, bm_sweep(circle_pts(0.5 * q, 0, cz, 12), 0.3, 0.16, closed=True))
    join(bm, bm_sweep(circle_pts(1.25 * q, 0, cz, 20, math.radians(120), math.radians(340)), 0.2, 0.1))
    for i in range(12):
        a = TAU * i / 12 + TAU / 24
        deg = math.degrees(a) % 360
        if 15 < deg < 80:
            continue
        r0 = 0.58 * q
        ln = (R - r0) if not (80 < deg < 115) else 0.9
        sp = bm_box(ln, 0.2, 0.11)
        join(bm, sp, T(math.cos(a) * (r0 + ln / 2), 0, cz + math.sin(a) * (r0 + ln / 2)) @ RY(-a))
        a2 = TAU * i / 12
        if not (5 < math.degrees(a2) % 360 < 95):
            join(bm, bm_sweep(circle_pts(0.36 * q, math.cos(a2) * 1.86 * q, cz + math.sin(a2) * 1.86 * q, 8), 0.18, 0.09, closed=True))
    # 窗櫺
    for x, top in ((-1.6 * q, spring - 1.1), (0.0, spring - 1.1), (1.6 * q, 3.9)):
        mu = bm_box(0.2, 0.3, top - sill, base=True)
        if top < 5:
            for v in mu.verts:
                if v.co.z > 1:
                    v.co.z += random.uniform(-0.4, 0.2)
        join(bm, mu, T(x, 0, sill))
    for i, cx in enumerate((-2.4 * q, -0.8 * q, 0.8 * q, 2.4 * q)):
        pts = arch_pts(1.42 * q, spring - 1.2, 0.9, n=4)
        if i == 2:
            pts = pts[:4]
        if i == 3:
            continue
        join(bm, bm_sweep(pts, 0.26, 0.16), T(cx, 0, 0))
    join(bm, bm_box(w, 0.5, 0.22), T(0, 0, sill))
    # 大拱內緣線腳
    join(bm, bm_sweep(arch_pts(w - 0.3, spring, k * w / (w - 0.3), n=9), 1.5, 0.3))
    for s in (-1, 1):
        join(bm, bm_box(0.3, 1.5, spring - sill, base=True), T(s * (w / 2 - 0.15), 0, sill))
    emit(bm, "stone", M, tint=(0.9, 0.9, 0.95))


def build_gable():
    Y = 16.4
    W, TH = 15.0, 1.3
    w, sill, spring, k = 7.6, 2.3, 8.2, 1.0

    def top(x, v):
        g = 11.6 + (1 - abs(x) / (W / 2)) * 8.6
        if x > 1.0:
            g = min(g, 18.9 - (x - 1.0) * 1.3 + 0.9 * noise.noise(Vector((x * 0.7, 2.2, 0))))
        if x < -5.2:
            g = min(g, 12.9 + (x + 5.2) * 0.9)
        return g

    def gtop(x):
        g = top(x, 0)
        if x > 1.0 or x < -5.2:
            g = round(g / 0.45) * 0.45 + (0.45 if noise.noise(Vector((x * 2.3, 4.0, 1.0))) > 0.25 else 0.0)
        return g
    gtop.smooth = True
    wall = bm_arch_wall(W, TH, gtop, opening=(0, w, sill, spring, k), step=0.6)
    # 完好一側的山牆壓頂石
    x0, x1 = -5.15, 1.0
    cop = bm_sweep([(x0, top(x0, 0) + 0.12), (x1, top(x1, 0) + 0.12)], TH + 0.35, 0.3)
    emit(cop, "stone", T(0, Y, 0), tint=(0.85, 0.85, 0.9))
    M = T(0, Y, 0)
    emit(wall, "masonry", M)
    build_rose(M, w, sill, spring, k)
    # 山牆上方的小尖拱通風窗框
    emit(bm_sweep(arch_pts(1.1, 16.9, 1.0, n=4) , TH + 0.1, 0.2), "stone", T(-1.2, Y, 0))
    # 底座與飾帶
    emit(bm_box(W + 0.4, TH + 0.5, 0.9, base=True), "stone", M, tint=(0.8, 0.8, 0.82))
    emit(bm_box(W + 0.1, TH + 0.3, 0.2), "stone", M @ T(0, 0, sill - 0.25))
    # 兩側扶壁塔與小尖塔
    for s, hgt, spire in ((-1, 14.6, True), (1, 12.6, False)):
        bx = s * (W / 2 + 0.75)
        bm = bmesh.new()
        join(bm, bm_box(2.0, 2.4, 4.5, base=True))
        join(bm, bm_box(1.7, 2.0, hgt - 4.5, base=True), T(0, 0, 4.5))
        join(bm, bm_box(1.95, 2.3, 0.25), T(0, 0, 4.5))
        join(bm, bm_box(1.95, 2.3, 0.25), T(0, 0, 8.8))
        emit(bm, "masonry", T(bx, Y - 0.3, 0))
        if spire:
            sp = bmesh.new()
            join(sp, bm_box(1.3, 1.3, 1.6, base=True))
            join(sp, bm_cyl(0.92, 0.06, 3.4, 4, caps=True), T(0, 0, 1.6) @ RZ(math.pi / 4))
            for cx, cy in ((-0.65, -0.65), (0.65, -0.65), (0.65, 0.65), (-0.65, 0.65)):
                join(sp, bm_cyl(0.18, 0.02, 0.9, 4), T(cx, cy, 1.6))
            emit(sp, "stone", T(bx, Y - 0.3, hgt))
        else:
            for i in range(5):
                emit(bm_box(random.uniform(0.4, 0.9), random.uniform(0.4, 0.9), random.uniform(0.3, 0.6), jit=0.05),
                     "masonry", T(bx + random.uniform(-0.5, 0.5), Y - 0.3 + random.uniform(-0.6, 0.6), hgt + 0.15) @ RZ(random.uniform(0, 3)))
    # 飛扶壁（從扶壁塔斜向後排墩柱）
    for s in (-1, 1):
        p_from = Vector((s * (W / 2 + 0.75), Y - 1.2, 9.6))
        p_to = polar(PIER_R, math.radians(90 - s * 30), 10.6 if s < 0 else 9.4)
        d = p_to - p_from
        L = d.xy.length
        pts = []
        for i in range(9):
            t = i / 8
            pts.append((-L / 2 + L * t, d.z * t + math.sin(t * math.pi) * 1.5))
        if s > 0:
            pts = pts[:6]
        fb = bm_sweep(pts, 0.55, 0.5)
        mid = (p_from + p_to) / 2
        emit(fb, "stone", T(mid.x, mid.y, p_from.z) @ RZ(math.atan2(d.y, d.x)))


def build_outer_wall(a, h, amp, opening, seed, r=17.6, width=7.05, thick=1.0, slope=None):
    M = tangent_frame(r, a)
    wall = bm_arch_wall(width, thick, ragged(h, amp, seed, extra=slope), opening=opening)
    emit(wall, "masonry", M)
    if opening:
        cx, w, sill, spring, k = opening
        if ragged(h, amp, seed, extra=slope)(cx) > arch_fn(w, spring, k)(0) + 0.3:
            rib = bm_sweep(arch_pts(w - 0.24, spring, k * w / (w - 0.24), n=6), thick + 0.24, 0.26)
            for s in (-1, 1):
                join(rib, bm_box(0.26, thick + 0.24, spring - sill, base=True), T(cx * 0 + s * (w / 2 - 0.13), 0, sill))
            emit(rib, "stone", M @ T(cx, 0, 0))
            # 壁龕背板（深色，讓拱洞有深度而不是直接透空）
            if sill < 0.5:
                back = bm_arch_wall(w + 0.2, 0.25, lambda x: arch_fn(w, spring, k)(x) + 0.1)
                emit(back, "masonry", M @ T(cx, thick / 2 + 0.6, 0), tint=(0.32, 0.33, 0.36))
    if h > 3:
        emit(bm_box(width, thick + 0.3, 0.7, base=True), "stone", M, tint=(0.78, 0.78, 0.8))


def build_architecture():
    D = math.radians
    piers = {0: 9.6, 30: 10.4, 60: 11.0, 120: 11.4, 150: 10.2, 180: 8.2, 210: 4.3, 240: 1.3, 300: 0.9, 330: 5.2}
    for deg, h in piers.items():
        build_pier(D(deg), h, capital=h >= SPRING - 0.5)
    build_arcade(D(0), D(30), 5.6, "full", 1.3)
    build_arcade(D(30), D(60), 6.2, "full", 2.1)
    build_arcade(D(120), D(150), 6.4, "full", 3.7)
    build_arcade(D(150), D(180), 5.0, "full", 4.4)
    build_arcade(D(330), D(360), 0, "right", 5.0)
    build_arcade(D(180), D(210), 0, "left", 6.0)
    build_gable()
    # 外牆（右側 -22.5~45、左側 135~202.5 較完整；前方只剩矮殘牆，270° 留缺口）
    build_outer_wall(D(0), 9.4, 1.2, (0, 3.0, 0.0, 4.6, 1.0), 1.0)
    build_outer_wall(D(22.5), 10.2, 1.0, (0, 2.6, 2.4, 5.4, 1.0), 2.0)
    build_outer_wall(D(45), 8.4, 1.6, (0.3, 3.0, 0.0, 4.4, 1.0), 3.0)
    build_outer_wall(D(67.5), 6.0, 2.0, (0, 2.4, 2.2, 4.8, 1.0), 4.0, slope=lambda x, v: v + x * 0.5)
    build_outer_wall(D(-22.5), 6.8, 1.8, (0, 3.0, 0.0, 4.4, 1.0), 5.0, slope=lambda x, v: v + x * 0.55)
    build_outer_wall(D(-45), 2.2, 1.3, None, 6.0, slope=lambda x, v: v + x * 0.3)
    build_outer_wall(D(180), 9.8, 1.2, (0, 3.0, 0.0, 4.6, 1.0), 7.0)
    build_outer_wall(D(157.5), 10.4, 1.0, (0, 2.6, 2.4, 5.4, 1.0), 8.0)
    build_outer_wall(D(135), 8.8, 1.5, (-0.3, 3.0, 0.0, 4.4, 1.0), 9.0)
    build_outer_wall(D(112.5), 6.4, 2.0, (0, 2.4, 2.2, 4.8, 1.0), 10.0, slope=lambda x, v: v - x * 0.5)
    build_outer_wall(D(202.5), 7.2, 1.8, (0, 3.0, 0.0, 4.4, 1.0), 11.0, slope=lambda x, v: v - x * 0.55)
    build_outer_wall(D(225), 2.4, 1.4, None, 12.0, slope=lambda x, v: v - x * 0.3)
    for deg, hb in ((11.25, 10.6), (33.75, 9.6), (-11.25, 7.6), (56.25, 6.4), (168.75, 10.8), (146.25, 9.8), (191.25, 7.9), (123.75, 6.6), (-33.75, 3.2), (213.75, 3.4)):
        Mb = tangent_frame(17.6 / math.cos(D(11.25)) - 0.15, D(deg))
        bt = bmesh.new()
        join(bt, bm_box(1.5, 1.9, hb * 0.45, base=True))
        join(bt, bm_box(1.3, 1.5, hb * 0.55, base=True), T(0, 0.1, hb * 0.45))
        join(bt, bm_box(1.6, 2.0, 0.22), T(0, 0, hb * 0.45))
        emit(bt, "masonry", Mb)
        if hb > 9:
            cap = bmesh.new()
            join(cap, bm_cyl(0.8, 0.05, 1.8, 4), RZ(math.pi / 4))
            emit(cap, "stone", Mb @ T(0, 0.1, hb))
        else:
            for i in range(3):
                emit(bm_box(random.uniform(0.4, 0.8), random.uniform(0.5, 0.9), random.uniform(0.3, 0.5), jit=0.04), "masonry",
                     Mb @ T(random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.4), hb + 0.15) @ RZ(random.uniform(0, 3)))
    build_outer_wall(D(247.5), 1.1, 0.9, None, 13.0, width=5.0)
    build_outer_wall(D(292.5), 1.3, 0.9, None, 14.0, width=5.0)


# ───────────────────────── 瓦礫、火盆、書頁、草、枯樹 ─────────────────────────
def scatter_rubble():
    D = math.radians
    piles = [(D(210), 13.9, 22, 1.5), (D(240), 13.8, 18, 1.4), (D(300), 13.7, 16, 1.3), (D(330), 14.0, 18, 1.4),
             (D(-45), 16.0, 16, 1.8), (D(225), 16.2, 16, 1.8), (D(75), 14.2, 12, 1.3), (D(100), 14.3, 12, 1.2),
             (D(180), 15.0, 10, 1.2), (D(10), 15.3, 10, 1.2), (D(262), 15.6, 9, 1.2), (D(282), 16.0, 9, 1.2)]
    for a, r, n, spread in piles:
        c = polar(r, a)
        for i in range(n):
            off = Vector((random.gauss(0, spread * 0.55), random.gauss(0, spread * 0.55), 0))
            p = c + off
            s = random.uniform(0.25, 0.75) * (1.25 - min(off.length / (spread * 1.6), 0.9))
            kind = random.random()
            mg = 0.95 if kind >= 0.85 else s * 1.2
            if p.xy.length - mg < 12.25:
                p.xy = p.xy.normalized() * (12.25 + mg)
            M = T(p.x, p.y, 0)
            if kind < 0.5:
                b = bm_box(s * random.uniform(1.0, 1.8), s * random.uniform(0.7, 1.1), s * random.uniform(0.5, 0.9), jit=s * 0.07)
                z = s * random.uniform(0.15, 0.5) + (random.uniform(0, 0.5) if off.length < spread * 0.4 else 0)
                emit(b, random.choice(("stone", "masonry", "stone")), M @ T(0, 0, z) @ RZ(random.uniform(0, TAU)) @ RX(random.uniform(-0.5, 0.5)) @ RY(random.uniform(-0.4, 0.4)),
                     tint=(random.uniform(0.6, 0.95),) * 3)
            elif kind < 0.85:
                b = bm_rock(s * random.uniform(0.9, 1.5), s * random.uniform(0.7, 1.1), s * random.uniform(0.5, 0.8))
                emit(b, "stone", M @ T(0, 0, s * 0.18) @ RZ(random.uniform(0, TAU)), tint=(random.uniform(0.55, 0.9),) * 3)
            else:
                b = bm_cyl(0.52, 0.52, random.uniform(0.5, 1.0), 10, base=False)
                emit(b, "stone", M @ T(0, 0, 0.45) @ RZ(random.uniform(0, TAU)) @ RX(math.pi / 2 + random.uniform(-0.25, 0.25)), smooth="auto",
                     tint=(random.uniform(0.7, 0.95),) * 3)
    # 倒下的整段柱身
    for a, r, rot, n in ((D(222), 14.6, D(20), 4), (D(318), 14.3, D(160), 3)):
        c = polar(r, a)
        for i in range(n):
            ax = Vector((math.cos(rot), math.sin(rot), 0))
            p = c + ax * (i - (n - 1) / 2) * 1.32
            b = bm_cyl(0.54, 0.54, 1.22, 12, base=False)
            emit(b, "stone", T(p.x, p.y, 0.5 + random.uniform(-0.03, 0.03)) @ RZ(rot + random.uniform(-0.08, 0.08)) @ RY(math.pi / 2 + random.uniform(-0.05, 0.05)), smooth="auto")
    # 小碎石
    for i in range(170):
        r, a = random.uniform(12.3, 18.5), random.uniform(0, TAU)
        s = random.uniform(0.07, 0.2)
        b = bmesh.new()
        bmesh.ops.create_icosphere(b, subdivisions=0, radius=1.0) if False else bmesh.ops.create_cube(b, size=1.6)
        for v in b.verts:
            v.co = Vector((v.co.x * s * random.uniform(0.7, 1.4), v.co.y * s * random.uniform(0.7, 1.4), v.co.z * s * random.uniform(0.5, 1.0)))
        emit(b, "stone", T(*polar(r, a, s * 0.3)) @ RZ(random.uniform(0, TAU)) @ RX(random.uniform(-0.6, 0.6)), tint=(random.uniform(0.5, 0.9),) * 3)


FIRE_POINTS = []


def build_brazier(a, r=12.85):
    M = T(*polar(r, a)) @ RZ(random.uniform(0, TAU))
    bm = bmesh.new()
    zb, zt = 0.5, 1.02
    rb, rt = 0.36, 0.56
    for z, rr, th in ((zb, rb, 0.045), ((zb + zt) / 2, (rb + rt) / 2, 0.035), (zt, rt, 0.055)):
        ring = bm_sweep(circle_pts(rr, 0, 0, 14), th * 1.3, th, closed=True)
        join(bm, ring, T(0, 0, z) @ RX(math.pi / 2))
    L = math.hypot(zt - zb, rt - rb)
    tilt = math.atan2(rt - rb, zt - zb)
    for i in range(12):
        ang = TAU * i / 12
        bar = bm_box(0.028, 0.028, L)
        join(bm, bar, RZ(ang) @ T((rb + rt) / 2, 0, (zb + zt) / 2) @ RY(tilt))
    join(bm, bm_cyl(rb, rb, 0.03, 12, base=False), T(0, 0, zb))
    for i in range(3):
        ang = TAU * i / 3 + 0.3
        leg = bm_box(0.05, 0.05, 0.62)
        join(bm, leg, RZ(ang) @ T(rb + 0.07, 0, 0.27) @ RY(0.3))
        foot = bm_box(0.14, 0.08, 0.03)
        join(bm, foot, RZ(ang) @ T(rb + 0.17, 0, 0.015))
    join(bm, bm_sweep(circle_pts(rb + 0.02, 0, 0, 12), 0.035, 0.03, closed=True), T(0, 0, 0.22) @ RX(math.pi / 2))
    emit(bm, "iron", M, tint=(0.75, 0.7, 0.68), moss=0.0)
    co = bmesh.new()
    for i in range(9):
        rr = random.uniform(0, 0.3)
        an = random.uniform(0, TAU)
        lump = bm_rock(random.uniform(0.09, 0.15), random.uniform(0.08, 0.13), random.uniform(0.07, 0.11), sub=0 if False else 1)
        join(co, lump, T(rr * math.cos(an), rr * math.sin(an), zb + 0.12 + random.uniform(0, 0.22)))
    col = co.loops.layers.float_color.new("Col")
    for f in co.faces:
        g = random.uniform(0.12, 1.0)
        for l in f.loops:
            l[col] = (g, g * g, g * g * g, 1)
    emit(co, "ember", M, keep_col=True)
    p = polar(r, a, zt + 0.05)
    FIRE_POINTS.append(p)


def scatter_pages():
    spots = [(-2.6, -4.2, 9, 1.0), (3.4, -6.3, 8, 1.1), (5.6, -8.4, 7, 1.0), (-5.5, -7.6, 6, 1.2), (2.2, 2.5, 5, 0.9),
             (-6.5, 2.0, 5, 1.2), (6.8, 1.0, 4, 1.0), (-1.0, 7.5, 5, 1.3), (0.5, -9.6, 6, 1.4), (-8.6, -3.4, 4, 0.9)]
    spots += [(random.uniform(-8, 8), random.uniform(-8, 8), 1, 0.1) for _ in range(16)]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    col = bm.loops.layers.float_color.new("Col")
    k = 0
    for sx, sy, n, sp in spots:
        for i in range(n):
            k += 1
            x, y = sx + random.gauss(0, sp), sy + random.gauss(0, sp)
            rr = math.hypot(x, y)
            if rr > 11.5 or 9.85 < rr < 10.75:
                continue
            w, h = random.uniform(0.24, 0.32), random.uniform(0.34, 0.44)
            rot = random.uniform(0, TAU)
            curl = random.uniform(0.0, 0.022)
            z0 = (0.02 if rr < 10 else 0.012) + k * 0.0003
            aa = math.atan2(y, x)
            for rm_, am_, dr_, da_ in MISSING:
                if abs(rr - rm_) < dr_ * 1.35 and abs((aa - am_ + math.pi) % TAU - math.pi) < da_ * 1.35:
                    z0 -= 0.035
                    break
            g = random.uniform(0.55, 1.0)
            c = (0.50 * g, 0.44 * g, 0.31 * g, 1)
            rows = []
            for j in range(3):
                t = j / 2
                zz = z0 + curl * (t - 0.4) ** 2 * 4 * (1 if j else 0.6)
                row = []
                for s in (-0.5, 0.5):
                    lx, ly = s * w, (t - 0.5) * h
                    row.append(bm.verts.new((x + lx * math.cos(rot) - ly * math.sin(rot), y + lx * math.sin(rot) + ly * math.cos(rot), zz)))
                rows.append(row)
            for j in range(2):
                f = bm.faces.new((rows[j][0], rows[j][1], rows[j + 1][1], rows[j + 1][0]))
                for l in f.loops:
                    l[col] = c
                    l[uv].uv = (0.5, 0.5)
    emit(bm, "paper", weld=False, recalc=False, keep_uv=True, keep_col=True, smooth=True)
    # 幾本書（闔上與攤開）
    for x, y, rot, opened in ((-3.1, -4.9, 0.4, False), (3.9, -6.0, 2.0, True), (-5.9, -7.0, 1.1, False), (6.0, -8.9, 5.0, True), (1.9, 3.0, 3.3, False)):
        M = T(x, y, 0.012) @ RZ(rot)
        if not opened:
            cv = bmesh.new()
            join(cv, bm_box(0.27, 0.36, 0.01, base=True))
            join(cv, bm_box(0.27, 0.36, 0.01, base=True), T(0, 0, 0.066))
            join(cv, bm_box(0.014, 0.36, 0.07, base=True), T(-0.13, 0, 0.003))
            emit(cv, "paper", M, tint=(0.10, 0.05, 0.035), moss=0.0)
            emit(bm_box(0.25, 0.34, 0.056, base=True), "paper", M @ T(0.004, 0, 0.01), tint=(0.5, 0.44, 0.31), moss=0.0)
        else:
            emit(bm_box(0.56, 0.37, 0.018, base=True), "paper", M, tint=(0.10, 0.05, 0.035), moss=0.0)
            for s in (-1, 1):
                emit(bm_box(0.25, 0.34, 0.035, base=True), "paper", M @ T(s * 0.135, 0, 0.016) @ RY(s * 0.10), tint=(0.52, 0.46, 0.33), moss=0.0)


def grass_tuft(bm, p, size=1.0, n=7, dry=0.5):
    uv = bm.loops.layers.uv.verify()
    col = bm.loops.layers.float_color.get("Col") or bm.loops.layers.float_color.new("Col")
    for i in range(n):
        a = random.uniform(0, TAU)
        h = random.uniform(0.16, 0.42) * size
        w = random.uniform(0.018, 0.03) * (0.7 + 0.3 * size)
        lean = random.uniform(0.05, 0.5)
        base = p + Vector((random.uniform(-0.07, 0.07), random.uniform(-0.07, 0.07), 0)) * size
        d = Vector((math.cos(a), math.sin(a), 0))
        s = Vector((-d.y, d.x, 0))
        m = base + d * (h * lean * 0.35) + Vector((0, 0, h * 0.55))
        t = base + d * (h * lean) + Vector((0, 0, h * (1 - 0.3 * lean)))
        v = [bm.verts.new(base - s * w), bm.verts.new(base + s * w), bm.verts.new(m + s * w * 0.6), bm.verts.new(m - s * w * 0.6), bm.verts.new(t)]
        dd = dry * random.uniform(0.6, 1.3)
        c0 = (0.045, 0.06, 0.03, 1)
        c1 = (0.16 + 0.22 * dd, 0.22 + 0.12 * dd, 0.07 + 0.05 * dd, 1)
        c2 = (0.25 + 0.3 * dd, 0.30 + 0.16 * dd, 0.10 + 0.08 * dd, 1)
        for f, cs in ((bm.faces.new((v[0], v[1], v[2], v[3])), (c0, c0, c1, c1)), (bm.faces.new((v[3], v[2], v[4])), (c1, c1, c2))):
            for l, c in zip(f.loops, cs):
                l[col] = c
                l[uv].uv = (0.5, 0.5)


def scatter_grass():
    bm = bmesh.new()
    for rm, am, dr, da in MISSING:
        for i in range(random.randint(5, 8)):
            p = polar(rm + random.uniform(-dr, dr), am + random.uniform(-da, da), -0.03)
            grass_tuft(bm, p, random.uniform(0.7, 1.25), n=random.randint(6, 9), dry=random.uniform(0.3, 0.9))
    for r, a in GAPS:
        if r < 9.6:
            grass_tuft(bm, polar(r, a + random.uniform(-0.03, 0.03), -0.02), random.uniform(0.45, 0.8), n=5, dry=0.6)
    for i in range(150):
        r, a = random.uniform(10.7, 19.0), random.uniform(0, TAU)
        if noise.noise(polar(r, a) * 0.25) < -0.1:
            continue
        grass_tuft(bm, polar(r, a, -0.02 if r < 12.7 else 0.05), random.uniform(0.7, 1.5), n=7, dry=random.uniform(0.2, 0.8))
    for v in bm.verts:
        if v.co.xy.length > 12.7 and v.co.z < 0.2:
            v.co.z -= 0.12
    emit(bm, "grass", weld=False, recalc=False, keep_uv=True, keep_col=True, smooth=True)


def build_tree(x, y, h, seed):
    rnd = random.Random(seed)
    bm = bmesh.new()

    def branch(p, d, ln, r, depth):
        d = d.normalized()
        q = p + d * ln
        r2 = r * 0.62
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u)
        n = 6 if depth == 0 else (5 if depth == 1 else 4)
        A = [bm.verts.new(p + (u * math.cos(TAU * i / n) + v * math.sin(TAU * i / n)) * r) for i in range(n)]
        B = [bm.verts.new(q + (u * math.cos(TAU * i / n) + v * math.sin(TAU * i / n)) * r2) for i in range(n)]
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))
        if depth >= 3:
            tip = bm.verts.new(q + d * ln * 0.5)
            for i in range(n):
                bm.faces.new((B[i], B[(i + 1) % n], tip))
            return
        for c in range(2 if depth else 3):
            nd = (d + Vector((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(-0.1, 0.5)))).normalized()
            branch(q - d * r2 * 0.5, nd, ln * rnd.uniform(0.55, 0.78), r2, depth + 1)

    branch(Vector((0, 0, -0.3)), Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 1)), h * 0.42, h * 0.035, 0)
    emit(bm, "ground", T(x, y, 0), tint=(0.22, 0.2, 0.19), smooth=True, moss=0.0, recalc=True, weld=False)


# ───────────────────────── 組裝 ─────────────────────────
build_ground()
build_floor()
build_architecture()
scatter_rubble()
for deg in (38, 142, 218, 322):
    build_brazier(math.radians(deg))
scatter_pages()
scatter_grass()
for x, y, h, sd in ((-21.5, 8.5, 10.5, 1), (22.5, 5.0, 9.0, 2), (-20.5, -6.0, 8.0, 3), (12.5, 21.5, 11.0, 4), (-11.5, 22.0, 9.5, 5), (21.0, -8.0, 7.5, 6)):
    build_tree(x, y, h, sd)

EXPORT = []
total_tris = 0
for key, bm in ACC.items():
    me = bpy.data.meshes.new(f"Arena_{key.capitalize()}")
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    scene.collection.objects.link(ob)
    me.materials.append(MATS[key])
    if "Col" in me.color_attributes:
        me.color_attributes.active_color = me.color_attributes["Col"]
        me.color_attributes.render_color_index = me.color_attributes.find("Col")
    EXPORT.append(ob)
    total_tris += len(me.polygons)
    print(f"  {me.name}: tris={len(me.polygons)} verts={len(me.vertices)}")
print("TOTAL TRIS", total_tris)

for i, p in enumerate(FIRE_POINTS):
    e = bpy.data.objects.new(f"FirePoint_{i + 1}", None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.3
    e.location = p
    scene.collection.objects.link(e)
    EXPORT.append(e)

# 淨空檢查：12 m 內不得有高於 0.5 m 的東西（草與貼地物除外）
viol = 0
for ob in EXPORT:
    if ob.type != "MESH" or ob.name == "Arena_Grass":
        continue
    for v in ob.data.vertices:
        if v.co.z > 0.5 and v.co.xy.length < 12.0:
            viol += 1
            print("   viol", ob.name, [round(c, 2) for c in v.co])
print("CLEARANCE_VIOLATIONS(<12m, z>0.5):", viol)


# ───────────────────────── 預覽渲染 ─────────────────────────
def render_previews():
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "CYCLES"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 88
    try:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_shadows = True
        scene.eevee.use_volumetric_shadows = True
        scene.eevee.volumetric_end = 80
        scene.eevee.volumetric_tile_size = "4"
        scene.eevee.use_gtao = True
    except Exception as ex:
        print("eevee opt", ex)
    w = bpy.data.worlds.new("W")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.055, 0.10, 1)
    bg.inputs[1].default_value = 1.0
    prev = []
    # 霧：用體積方塊（世界體積會把太陽光完全吃掉）
    vm = bpy.data.materials.new("PreviewFog")
    vm.use_nodes = True
    vnt = vm.node_tree
    for n in list(vnt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            vnt.nodes.remove(n)
    vol = vnt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.62, 0.74, 0.92, 1)
    vol.inputs["Density"].default_value = 0.006
    vnt.links.new(vol.outputs[0], next(n for n in vnt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    fme = bpy.data.meshes.new("PreviewFog")
    fbm = bm_box(90, 90, 26, base=True)
    fbm.to_mesh(fme)
    fbm.free()
    fog = bpy.data.objects.new("PreviewFog", fme)
    fme.materials.append(vm)
    scene.collection.objects.link(fog)
    prev.append(fog)
    moon = bpy.data.objects.new("Moon", bpy.data.lights.new("Moon", "SUN"))
    moon.data.energy = 4.0
    moon.data.color = (0.55, 0.70, 1.0)
    moon.data.angle = math.radians(2)
    moon.rotation_euler = (math.radians(-52), 0, math.radians(14))  # 從 +Y 後上方照向 -Y（穿過玫瑰窗）
    scene.collection.objects.link(moon)
    prev.append(moon)
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))
    fill.data.energy = 1.1
    fill.data.color = (0.5, 0.6, 0.9)
    fill.rotation_euler = (math.radians(55), 0, math.radians(-20))
    fill.data.use_shadow = False
    scene.collection.objects.link(fill)
    prev.append(fill)
    fmat = bpy.data.materials.new("PreviewFlame")
    fmat.use_nodes = True
    fb = next(n for n in fmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    fb.inputs["Base Color"].default_value = (1, 0.4, 0.05, 1)
    fb.inputs["Emission Color"].default_value = (1, 0.42, 0.08, 1)
    fb.inputs["Emission Strength"].default_value = 30
    for p in FIRE_POINTS:
        l = bpy.data.objects.new("Fire", bpy.data.lights.new("Fire", "POINT"))
        l.data.energy = 1500
        l.data.color = (1.0, 0.48, 0.16)
        l.data.shadow_soft_size = 0.25
        l.location = p + Vector((0, 0, 0.35))
        scene.collection.objects.link(l)
        prev.append(l)
        me = bpy.data.meshes.new("Flame")
        b = bm_cyl(0.3, 0.02, 0.75, 8)
        b.to_mesh(me)
        b.free()
        fo = bpy.data.objects.new("PreviewFlame", me)
        fo.location = p - Vector((0, 0, 0.15))
        me.materials.append(fmat)
        scene.collection.objects.link(fo)
        fo.visible_shadow = False
        prev.append(fo)

    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.clip_end = 300

    def shot(name, loc, target, lens):
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(OUT_PREV, name)
        bpy.ops.render.render(write_still=True)

    shot("arena_cathedral_player.jpg", (0, -15.8, 2.4), (0, 6, 4.6), 20)
    shot("arena_cathedral_top.jpg", (0, -17, 26), (0, 0.5, 0), 26)
    shot("arena_cathedral_reverse.jpg", (0, 13.0, 3.2), (0, -6, 1.2), 20)
    shot("arena_cathedral_34.jpg", (17.5, -19, 11), (0, 2, 3), 24)
    shot("arena_cathedral_close.jpg", (-4.5, -8.5, 1.5), (1.5, 0, 0.6), 28)

    # 白模
    clay = bpy.data.materials.new("Clay")
    clay.use_nodes = True
    cb = next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    cb.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1)
    cb.inputs["Roughness"].default_value = 0.8
    for o in EXPORT:
        if o.type == "MESH":
            o.data.materials[0] = clay
    fog.hide_render = True
    bg.inputs[0].default_value = (0.5, 0.55, 0.62, 1)
    bg.inputs[1].default_value = 0.7
    moon.data.energy = 3.0
    moon.data.color = (1, 0.97, 0.92)
    moon.rotation_euler = (math.radians(50), 0, math.radians(-35))
    for o in prev:
        if o.name.startswith("Fire") or o.name.startswith("PreviewFlame") or o.name == "Fill":
            o.hide_render = True
    shot("arena_cathedral_clay.jpg", (16, -21, 13), (0, 2, 3), 24)
    shot("arena_cathedral_clay_top.jpg", (0, -0.01, 46), (0, 0, 0), 28)
    for o in EXPORT:
        if o.type == "MESH":
            o.data.materials[0] = MATS[o.name[6:].lower()]
    return prev


if "--noprev" not in argv:
    render_previews()
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

# ───────────────────────── 匯出 GLB ─────────────────────────
# 匯出前把 baseColor 貼圖直接接到 Principled（頂點色改由 COLOR_0 匯出，檢視器會自動相乘）。
for m in MATS.values():
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for l in list(b.inputs["Base Color"].links):
        nt.links.remove(l)
    tc = nt.nodes.get("TexColor")
    if tc:
        nt.links.new(tc.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (1, 1, 1, 1)
bpy.ops.object.select_all(action="DESELECT")
for o in EXPORT:
    o.select_set(True)
bpy.context.view_layer.objects.active = EXPORT[0]
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True, export_yup=True, export_animations=False,
                          export_image_format="JPEG", export_jpeg_quality=78, export_vertex_color="ACTIVE", export_all_vertex_colors=False,
                          export_active_vertex_color_when_no_material=True, export_tangents=False, export_apply=True, export_cameras=False, export_lights=False)


# ───────────────────────── GLB 檢查 ─────────────────────────
def check_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    jlen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + jlen])
    bin0 = 20 + jlen + 8
    tris = 0
    has_col = 0
    for me in js["meshes"]:
        for p in me["primitives"]:
            tris += js["accessors"][p["indices"]]["count"] // 3
            has_col += 1 if "COLOR_0" in p["attributes"] else 0
    print("CHECK file:", path)
    print("CHECK size_MB: %.2f" % (len(data) / 1048576))
    vtx = sum(js["accessors"][p["attributes"]["POSITION"]]["count"] for me in js["meshes"] for p in me["primitives"])
    ctypes = set(js["accessors"][p["attributes"]["COLOR_0"]]["componentType"] for me in js["meshes"] for p in me["primitives"] if "COLOR_0" in p["attributes"])
    print("CHECK vertices:", vtx, "COLOR_0 componentTypes:", ctypes, "bin_MB: %.2f" % ((len(data) - bin0) / 1048576))
    print("CHECK triangles:", tris, "| primitives:", sum(len(m["primitives"]) for m in js["meshes"]), "| with COLOR_0:", has_col)
    for i, im in enumerate(js.get("images", [])):
        bv = js["bufferViews"][im["bufferView"]]
        raw = data[bin0 + bv.get("byteOffset", 0): bin0 + bv.get("byteOffset", 0) + bv["byteLength"]]
        wh = None
        if raw[:2] == b"\xff\xd8":
            k = 2
            while k < len(raw):
                mk = raw[k + 1]
                ln = struct.unpack_from(">H", raw, k + 2)[0]
                if mk in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack_from(">HH", raw, k + 5)
                    wh = (w, h)
                    break
                k += 2 + ln
        elif raw[:4] == b"\x89PNG":
            wh = struct.unpack_from(">II", raw, 16)
        print("CHECK image:", im.get("name"), im.get("mimeType"), wh, "%.0f KB" % (len(raw) / 1024))
    print("CHECK materials:", [(m["name"], "tex" if "baseColorTexture" in m.get("pbrMetallicRoughness", {}) else "flat",
                                "N" if "normalTexture" in m else "-", "E" if "emissiveFactor" in m else "-") for m in js["materials"]])
    print("CHECK FirePoint nodes:", [(n["name"], [round(x, 2) for x in n.get("translation", [0, 0, 0])]) for n in js["nodes"] if n["name"].startswith("FirePoint")])
    print("CHECK animations:", len(js.get("animations", [])))


check_glb(OUT_GLB)
print("DONE arena_cathedral")
