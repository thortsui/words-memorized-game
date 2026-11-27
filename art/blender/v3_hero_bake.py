"""單字魂 v3 主角：來源材質（CC0 掃描貼圖＋程序遮罩）、烘焙成圖集、最終材質、匯出與預覽渲染。
從 soul_humanoid_bake.py 複製再改：烘焙圖輸出 textures/baked/v3_hero_knight_*、detail UV（縫線／織紋）、define_v3 程序化材質。"""
import bpy, os, glob, math, sys
import numpy as np
from mathutils import Vector
from soul_humanoid_lib import TEXDIR, HERE

BAKED = os.path.join(TEXDIR, "baked")
_imgcache = {}


def tex_path(asset, kind):
    for d in (os.path.join(TEXDIR, "acg_" + asset), os.path.join(TEXDIR, asset)):
        g = glob.glob(os.path.join(d, f"*_{kind}.jpg")) + glob.glob(os.path.join(d, f"*_{kind}.png"))
        if g:
            return g[0]
    return None


def load_img(path, cs):
    key = (path, cs)
    if key not in _imgcache:
        im = bpy.data.images.load(path)
        im.colorspace_settings.name = cs
        _imgcache[key] = im
    return _imgcache[key]


class NG:
    """節點圖小工具。socket 可用數值、顏色 tuple 或節點輸出。"""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.N = self.nt.nodes
        self.L = self.nt.links
        self.N.clear()
        self.tc = self.N.new("ShaderNodeTexCoord")
        self.geo = self.N.new("ShaderNodeNewGeometry")

    def put(self, sock, val):
        if hasattr(val, "is_linked") or isinstance(val, bpy.types.NodeSocket):
            self.L.new(val, sock)
        elif isinstance(val, (tuple, list)):
            sock.default_value = (*val[:3], 1.0) if len(sock.default_value) == 4 else val[:3]
        else:
            sock.default_value = val

    def math(self, op, a, b=None, clamp=False):
        n = self.N.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        return n.outputs[0]

    def mix(self, fac, a, b, kind="MIX"):
        n = self.N.new("ShaderNodeMixRGB"); n.blend_type = kind
        self.put(n.inputs[0], fac); self.put(n.inputs[1], a); self.put(n.inputs[2], b)
        return n.outputs[0]

    def mixf(self, fac, a, b):
        # a*(1-fac)+b*fac
        n = self.N.new("ShaderNodeMapRange")
        self.put(n.inputs[0], fac); n.inputs[1].default_value = 0; n.inputs[2].default_value = 1
        self.put(n.inputs[3], a); self.put(n.inputs[4], b)
        return n.outputs[0]

    def ramp(self, x, lo, hi):
        n = self.N.new("ShaderNodeMapRange"); n.interpolation_type = "SMOOTHSTEP"
        self.put(n.inputs[0], x); n.inputs[1].default_value = lo; n.inputs[2].default_value = hi
        n.inputs[3].default_value = 0; n.inputs[4].default_value = 1
        return n.outputs[0]

    def image(self, asset, kind, size, cs="Non-Color", offs=(0.13, 0.37, 0.21), rot=(0.3, 0.2, 0.5)):
        p = tex_path(asset, kind)
        if not p:
            return None
        n = self.N.new("ShaderNodeTexImage")
        n.image = load_img(p, cs)
        n.projection = "BOX"; n.projection_blend = 0.25
        mp = self.N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / size,) * 3
        mp.inputs["Location"].default_value = offs
        mp.inputs["Rotation"].default_value = rot
        self.L.new(self.tc.outputs["Object"], mp.inputs["Vector"])
        self.L.new(mp.outputs[0], n.inputs[0])
        return n.outputs["Color"]

    def noise(self, scale, detail=6.0, rough=0.6, offs=0.0):
        n = self.N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        mp = self.N.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (offs, offs * 1.7, offs * 0.6)
        self.L.new(self.tc.outputs["Object"], mp.inputs["Vector"])
        self.L.new(mp.outputs[0], n.inputs["Vector"])
        return n.outputs["Fac"]

    def lum(self, col):
        n = self.N.new("ShaderNodeRGBToBW")
        self.L.new(col, n.inputs[0])
        return n.outputs[0]

    def ao(self, dist, samples=8):
        n = self.N.new("ShaderNodeAmbientOcclusion")
        n.inputs["Distance"].default_value = dist; n.samples = samples
        return n.outputs["AO"]

    def edge(self, radius):
        b = self.N.new("ShaderNodeBevel"); b.samples = 4; b.inputs["Radius"].default_value = radius
        d = self.N.new("ShaderNodeVectorMath"); d.operation = "DOT_PRODUCT"
        self.L.new(b.outputs[0], d.inputs[0]); self.L.new(self.geo.outputs["Normal"], d.inputs[1])
        return self.math("SUBTRACT", 1.0, d.outputs["Value"], clamp=True)

    def zcoord(self):
        s = self.N.new("ShaderNodeSeparateXYZ")
        self.L.new(self.tc.outputs["Object"], s.inputs[0])
        return s.outputs[2]

    def nz(self):
        s = self.N.new("ShaderNodeSeparateXYZ")
        self.L.new(self.geo.outputs["Normal"], s.inputs[0])
        return s.outputs[2]


SRC = {}   # 材質 key -> dict(mat, group, emitC, emitO, bsdf, out)


def define_mat(key, group="A", tex=None, size=0.5, tint=(1, 1, 1), sat=1.0, val=1.0, rough=None, rough_mul=1.0,
               metal=None, bump=0.4, bump_dist=0.004, rust=0.0, rust_size=0.45, rust_tint=(0.8, 0.75, 0.7), wear=0.0,
               wear_col=(0.60, 0.58, 0.55), dirt=0.5, dirt_col=(0.035, 0.03, 0.025), moss=0.0, mud=None,
               mud_col=(0.16, 0.13, 0.10), ao_shade=0.6, U=1.0, color=None, emit=None, emit_strength=1.0, seed=0.0,
               flat_rough=0.6, stain=0.0, stain_col=(0.12, 0.06, 0.04)):
    """定義來源材質。group：'A'／'B' 兩組圖集，'G' 為純自發光（不烘焙）。"""
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    g = NG(m)
    N, L = g.N, g.L
    out = N.new("ShaderNodeOutputMaterial")
    d = dict(mat=m, group=group, out=out, key=key, tint=tint, emit=emit, emit_strength=emit_strength)
    SRC[key] = d
    if group == "G":
        em = N.new("ShaderNodeEmission")
        em.inputs[0].default_value = (*emit, 1); em.inputs[1].default_value = emit_strength
        L.new(em.outputs[0], out.inputs[0])
        return d
    # 底色
    if tex:
        col = g.image(tex, "Color", size, cs="sRGB")
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = sat; hs.inputs["Value"].default_value = val
        L.new(col, hs.inputs["Color"])
        base = g.mix(1.0, hs.outputs[0], tint, "MULTIPLY")
        r_img = g.image(tex, "Roughness", size)
        m_img = g.image(tex, "Metalness", size)
        h_img = g.image(tex, "Displacement", size)
        if h_img is None:
            h_img = g.lum(col)
    else:
        base = g.mix(0.0, color or tint, color or tint)
        r_img = m_img = None
        h_img = g.noise(60 / U, 4, 0.7, seed + 3)
    if rough is not None:
        rsock = g.math("ADD", rough, 0.0)
        if r_img is not None:
            rsock = g.math("ADD", g.math("MULTIPLY", g.math("SUBTRACT", r_img, 0.5), 0.5), rough, clamp=True)
    elif r_img is not None:
        rsock = g.math("MULTIPLY", r_img, rough_mul, clamp=True)
    else:
        rsock = g.math("ADD", flat_rough, 0.0)
    if metal is not None:
        msock = g.math("ADD", metal, 0.0)
    elif m_img is not None:
        msock = g.math("ADD", m_img, 0.0)
    else:
        msock = g.math("ADD", 0.0, 0.0)
    hsock = h_img
    n1 = g.noise(5.0 / U, 8, 0.65, seed)
    n2 = g.noise(22.0 / U, 5, 0.7, seed + 7)
    cav = g.math("SUBTRACT", 1.0, g.ao(0.06 * U), clamp=True)
    aofar = g.ao(0.30 * U)
    col = base
    # 鏽
    if rust > 0:
        lo = 0.72 - 0.42 * rust
        rm = g.ramp(g.math("ADD", g.math("ADD", n1, g.math("MULTIPLY", n2, 0.25)), g.math("MULTIPLY", cav, 0.55 * rust + 0.15)), lo + 0.12, lo + 0.34)
        rcol = g.image("Rust009", "Color", rust_size, cs="sRGB", offs=(0.4, 0.1, 0.7))
        rcol = g.mix(1.0, rcol, rust_tint, "MULTIPLY")
        col = g.mix(rm, col, rcol)
        rsock = g.mixf(rm, rsock, 0.86)
        msock = g.mixf(rm, msock, g.math("MULTIPLY", msock, 0.25))
        rh = g.image("Rust009", "Displacement", rust_size, offs=(0.4, 0.1, 0.7))
        hsock = g.mixf(rm, hsock, g.math("ADD", g.math("MULTIPLY", rh, 1.4), 0.15))
    else:
        rm = None
    # 邊緣磨損（露出亮金屬／淺色纖維）
    if wear > 0:
        e = g.math("MULTIPLY", g.edge(0.006 * U), 14.0, clamp=True)
        e = g.math("MULTIPLY", e, g.ramp(n2, 0.30, 0.62))
        e = g.math("MULTIPLY", e, wear, clamp=True)
        if rm is not None:
            e = g.math("MULTIPLY", e, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", rm, 0.6)))
        col = g.mix(e, col, wear_col)
        rsock = g.mixf(e, rsock, 0.34)
    # 污漬（血鏽色，行刑者圍裙）
    if stain > 0:
        sm = g.ramp(g.math("ADD", n1, g.math("MULTIPLY", n2, 0.3)), 0.95 - stain * 0.6, 1.15 - stain * 0.6)
        col = g.mix(g.math("MULTIPLY", sm, 0.8), col, stain_col)
    # 凹處積垢
    if dirt > 0:
        dm = g.math("MULTIPLY", g.math("POWER", cav, 1.3), dirt, clamp=True)
        col = g.mix(dm, col, dirt_col)
        rsock = g.mixf(dm, rsock, 0.95)
        msock = g.math("MULTIPLY", msock, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", dm, 0.8)))
    # 青苔
    if moss > 0:
        n3 = g.noise(3.2 / U, 6, 0.7, seed + 21)
        up = g.math("MAXIMUM", g.nz(), 0.0)
        mm = g.math("ADD", g.math("ADD", n3, g.math("MULTIPLY", up, 0.22)), g.math("MULTIPLY", cav, 0.30))
        lo = 0.86 - 0.40 * moss
        mm = g.ramp(g.math("ADD", mm, g.math("MULTIPLY", n2, 0.12)), lo, lo + 0.10)
        mcol = g.image("Moss002", "Color", 0.35, cs="sRGB", offs=(0.2, 0.6, 0.1))
        mcol = g.mix(1.0, mcol, (0.50, 0.52, 0.30), "MULTIPLY")
        col = g.mix(mm, col, mcol)
        rsock = g.mixf(mm, rsock, 0.95)
        msock = g.math("MULTIPLY", msock, g.math("SUBTRACT", 1.0, mm))
        mh = g.image("Moss002", "Displacement", 0.35, offs=(0.2, 0.6, 0.1))
        hsock = g.mixf(mm, hsock, g.math("ADD", g.math("MULTIPLY", mh, 2.0), 0.3))
    # 下襬泥塵
    if mud:
        z0, z1, amt = mud
        mz = g.math("SUBTRACT", 1.0, g.ramp(g.zcoord(), z0, z1))
        mz = g.math("MULTIPLY", g.math("MULTIPLY", mz, g.math("ADD", 0.55, g.math("MULTIPLY", n1, 0.7))), amt, clamp=True)
        col = g.mix(mz, col, mud_col)
        rsock = g.mixf(mz, rsock, 0.95)
    # 烘入環境遮蔽
    shade = g.mixf(ao_shade, 1.0, aofar)
    colf = g.mix(1.0, col, g.mix(0.0, (1, 1, 1), (1, 1, 1)), "MULTIPLY")
    mulc = N.new("ShaderNodeVectorMath"); mulc.operation = "SCALE"
    L.new(colf, mulc.inputs[0]); L.new(shade, mulc.inputs["Scale"])
    colout = mulc.outputs[0]
    bmp = N.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump; bmp.inputs["Distance"].default_value = bump_dist * U
    L.new(hsock, bmp.inputs["Height"])
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    L.new(colout, bsdf.inputs["Base Color"]); L.new(rsock, bsdf.inputs["Roughness"]); L.new(msock, bsdf.inputs["Metallic"])
    L.new(bmp.outputs[0], bsdf.inputs["Normal"])
    emC = N.new("ShaderNodeEmission"); L.new(colout, emC.inputs[0])
    comb = N.new("ShaderNodeCombineColor")
    L.new(aofar, comb.inputs[0]); L.new(rsock, comb.inputs[1]); L.new(msock, comb.inputs[2])
    emO = N.new("ShaderNodeEmission"); L.new(comb.outputs[0], emO.inputs[0])
    L.new(bsdf.outputs[0], out.inputs[0])
    tgt = N.new("ShaderNodeTexImage"); tgt.name = "BAKE_TARGET"
    d.update(emitC=emC, emitO=emO, bsdf=bsdf, target=tgt)
    return d


def _join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


def _pack_uv(ob, margin=0.003):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(rotate=True, rotate_method="AXIS_ALIGNED", scale=True, merge_overlap=True,
                                margin_method="FRACTION", margin=margin, shape_method="AABB")
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def _new_img(name, size, cs):
    im = bpy.data.images.new(name, size, size, alpha=False, float_buffer=False)
    im.colorspace_settings.name = cs
    return im


def _save(im, path):
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()


def _apply_mod(ob, md):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)


def _resmooth(ob, sharp_deg):
    import bmesh as _bm
    bm = _bm.new(); bm.from_mesh(ob.data)
    lim = math.radians(sharp_deg)
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(0.0) < lim
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(ob.data); bm.free()


def polish(B):
    """細節處理：甲片邊緣倒角（兩段，讓稜線吃到高光）、布料加厚度（不再是零厚度的紙片）。"""
    nb = nc = 0
    for ob in B.parts:
        rim = ob.get("rim")
        th = ob.get("cloth")
        if th:
            md = ob.modifiers.new("Thick", "SOLIDIFY")
            md.thickness = th; md.offset = -1.0; md.use_rim = True; md.use_even_offset = False; md.thickness_clamp = 1.0
            _apply_mod(ob, md); _resmooth(ob, 60); nc += 1
        elif rim:
            md = ob.modifiers.new("Bevel", "BEVEL")
            md.width = min(rim * 0.45, 0.004); md.segments = 1; md.limit_method = "ANGLE"
            md.angle_limit = math.radians(40); md.profile = 0.6
            try:
                md.miter_outer = "MITER_ARC"
            except Exception:
                pass
            _apply_mod(ob, md); _resmooth(ob, 70); nb += 1
    print("POLISH bevel", nb, "cloth", nc, flush=True)



# ---------------------------------------------------------------- 高模細節（第二版）
# 低模零件 → 細分＋依材質位移（敲擊凹痕、鏽蝕坑洞、布料皺紋、皮革折痕、樹皮紋）成高模，
# 顏色／粗糙度／法線都從高模「烘到」低模的貼圖（selected to active），凹痕裡會積到髒污、稜線吃到高光。
DETAIL = {
    "metal": [("VORONOI", 0.0025, 0.05, "F1"), ("CLOUDS", 0.0009, 0.006, None), ("CLOUDS", 0.0012, 0.02, None)],
    "cloth": [("CLOUDS", 0.0035, 0.035, None), ("CLOUDS", 0.0012, 0.008, None)],
    "leather": [("CLOUDS", 0.0022, 0.02, None), ("VORONOI", 0.001, 0.008, "F2")],
    "bark": [("CLOUDS", 0.006, 0.03, None), ("VORONOI", 0.003, 0.012, "F1")],
    "bone": [("CLOUDS", 0.0015, 0.012, None)],
    "wood": [("CLOUDS", 0.002, 0.02, None)],
}


def _disp_tex(kind, scale, feat):
    t = bpy.data.textures.new("dt", kind)
    t.noise_scale = scale
    if kind == "CLOUDS":
        t.noise_depth = 3
    if kind == "VORONOI" and feat:
        t.distance_metric = "DISTANCE"
        t.color_mode = "INTENSITY"
        t.weight_1, t.weight_2 = (1.0, 0.0) if feat == "F1" else (0.0, 1.0)
    return t


def make_high(ob, detail_of, U=1.0):
    """detail_of: matkey -> DETAIL 類別（None＝不加位移）。回傳高模物件（與低模共用材質）。"""
    hi = ob.copy()
    hi.data = ob.data.copy()
    hi.name = ob.name + "_high"
    bpy.context.scene.collection.objects.link(hi)
    for g in list(hi.vertex_groups):
        hi.vertex_groups.remove(g)
    sub = hi.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 2
    _apply_mod(hi, sub)
    # 每一類材質一個頂點群組（材質邊界的頂點兩邊都算，位移量取各自的，接縫不會裂開太多）
    cats = {}
    me = hi.data
    for p in me.polygons:
        sl = hi.material_slots[p.material_index].material
        key = next((d["key"] for d in SRC.values() if d["mat"] == sl), None)
        c = detail_of(key)
        if c:
            cats.setdefault(c, set()).update(p.vertices)
    for c, vs in cats.items():
        gn = "det_" + c          # 只留名字：套用修改器後群組的 Python 參照會失效
        hi.vertex_groups.new(name=gn).add(list(vs), 1.0, "REPLACE")
        for kind, strength, scale, feat in DETAIL[c]:
            md = hi.modifiers.new("d", "DISPLACE")
            md.texture = _disp_tex(kind, scale * U, feat)
            md.texture_coords = "GLOBAL"
            md.strength = strength * U
            md.mid_level = 0.5
            md.vertex_group = gn
            _apply_mod(hi, md)
    print("HIGH", ob.name, len(me.polygons), "faces", flush=True)
    return hi


def assemble(B, model, size=(1024, 1024), bake=True, samples=24, quick=False, detail_of=None, U=1.0):
    """把分件依材質組別合併、展 UV、烘焙，回傳合併後的單一網格物件。"""
    sc = bpy.context.scene
    polish(B)
    os.makedirs(BAKED, exist_ok=True)
    groups = {}
    for ob in B.parts:
        d = SRC[ob["matkey"]]
        ob.data.materials.append(d["mat"])
        groups.setdefault(d["group"], []).append(ob)
    joined = {}
    for gk in sorted(groups):
        joined[gk] = _join(groups[gk], f"{model}_{gk}")
        uvl = joined[gk].data.uv_layers
        if "atlas" in uvl:
            uvl.active = uvl["atlas"]
            uvl["atlas"].active_render = True
    finals = []
    sc.render.engine = "CYCLES"
    try:
        import soul_creature_lib as _CL
        print("BAKE device", _CL.use_gpu(), flush=True)
    except Exception as e:
        print("BAKE device CPU", e, flush=True)
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.bake.margin = 6
    sc.render.bake.use_clear = True
    sc.render.bake.target = "IMAGE_TEXTURES"
    for gi, gk in enumerate(k for k in sorted(joined) if k != "G"):
        ob = joined[gk]
        sz = size[min(gi, len(size) - 1)]
        _pack_uv(ob)
        paths = {p: os.path.join(BAKED, f"v3_{model}_{gk}_{p}.png") for p in ("color", "orm", "normal")}
        if bake:
            imgs = {"color": _new_img(f"{model}_{gk}_color", sz, "sRGB"), "orm": _new_img(f"{model}_{gk}_orm", sz, "Non-Color"),
                    "normal": _new_img(f"{model}_{gk}_normal", sz, "Non-Color")}
            hi = make_high(ob, detail_of, U) if detail_of else None
            bpy.ops.object.select_all(action="DESELECT")
            if hi:
                hi.select_set(True)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            sc.render.bake.use_selected_to_active = bool(hi)
            sc.render.bake.cage_extrusion = 0.012 * U
            sc.render.bake.max_ray_distance = 0.04 * U
            mats = [s.material for s in ob.material_slots]
            for p in ("color", "orm", "normal"):
                for m in mats:
                    d = next(v for v in SRC.values() if v["mat"] == m)
                    nt = m.node_tree
                    d["target"].image = imgs[p]
                    for n in nt.nodes:
                        n.select = False
                    d["target"].select = True
                    nt.nodes.active = d["target"]
                    src = {"color": d["emitC"], "orm": d["emitO"], "normal": d["bsdf"]}[p]
                    for l in list(d["out"].inputs[0].links):
                        nt.links.remove(l)
                    nt.links.new(src.outputs[0], d["out"].inputs[0])
                bpy.ops.object.bake(type="NORMAL" if p == "normal" else "EMIT")
                _save(imgs[p], paths[p])
                print("BAKED", model, gk, p, flush=True)
            if hi:
                bpy.data.objects.remove(hi)
            sc.render.bake.use_selected_to_active = False
        if "detail" in ob.data.uv_layers:
            ob.data.uv_layers.remove(ob.data.uv_layers["detail"])
        # 最終材質
        fm = bpy.data.materials.new(f"{model}_{gk}")
        fm.use_nodes = True
        fm.use_backface_culling = False
        nt = fm.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if os.path.exists(paths["color"]) and not quick:
            ic = nt.nodes.new("ShaderNodeTexImage"); ic.image = bpy.data.images.load(paths["color"], check_existing=False)
            io = nt.nodes.new("ShaderNodeTexImage"); io.image = bpy.data.images.load(paths["orm"], check_existing=False)
            io.image.colorspace_settings.name = "Non-Color"
            inn = nt.nodes.new("ShaderNodeTexImage"); inn.image = bpy.data.images.load(paths["normal"], check_existing=False)
            inn.image.colorspace_settings.name = "Non-Color"
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(ic.outputs[0], bsdf.inputs["Base Color"])
            nt.links.new(io.outputs[0], sep.inputs[0])
            nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
            nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
            nt.links.new(inn.outputs[0], nm.inputs["Color"])
            nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
            for n in (ic, io, inn):
                n.image.pack()
            ob.data.materials.clear()
            ob.data.materials.append(fm)
        else:
            # 快速模式：沒有烘焙圖，改用各來源材質的代表色
            for s in ob.material_slots:
                d = next(v for v in SRC.values() if v["mat"] == s.material)
                qm = bpy.data.materials.new("quick_" + d["key"])
                qm.use_nodes = True
                qb = next(n for n in qm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                t = d["tint"]
                qb.inputs["Base Color"].default_value = (t[0] * 0.6, t[1] * 0.6, t[2] * 0.6, 1)
                qb.inputs["Roughness"].default_value = 0.6
                s.material = qm
        finals.append(ob)
    if "G" in joined:
        ob = joined["G"]
        d = SRC[ob.material_slots[0].material.name[4:]]
        gm = bpy.data.materials.new(f"{model}_Glow")
        gm.use_nodes = True
        gb = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        gb.inputs["Base Color"].default_value = (0.02, 0.01, 0.03, 1)
        gb.inputs["Emission Color"].default_value = (*d["emit"], 1)
        gb.inputs["Emission Strength"].default_value = d["emit_strength"]
        gb.inputs["Roughness"].default_value = 0.8
        ob.data.materials.clear()
        ob.data.materials.append(gm)
        finals.append(ob)
    mesh = _join(finals, model + "_mesh")
    for im in list(bpy.data.images):
        if im.users == 0:
            bpy.data.images.remove(im)
    return mesh


def bind(mesh, arm):
    mesh.parent = arm
    md = mesh.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    names = {b.name for b in arm.data.bones}
    for g in mesh.vertex_groups:
        if g.name not in names:
            print("WARN 權重群組沒有對應骨頭:", g.name)


def tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.data.polygons)


def export_glb(arm, mesh, path, jpeg_quality=88):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_animations=True,
              export_animation_mode="NLA_TRACKS", export_yup=True, export_skins=True, export_image_format="JPEG",
              export_force_sampling=True, export_optimize_animation_size=True, export_tangents=False)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties
    if "export_image_quality" in props:
        kw["export_image_quality"] = jpeg_quality
    if "export_jpeg_quality" in props:
        kw["export_jpeg_quality"] = jpeg_quality
    bpy.ops.export_scene.gltf(**kw)


# ---------------------------------------------------------------- 預覽
def setup_preview(H, res=(560, 800)):
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.06, 0.062, 0.066, 1); bg.inputs[1].default_value = 1.0

    def area(loc, energy, size, color=(1, 1, 1)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.data.energy = energy; l.data.size = size; l.data.color = color
        d = Vector((0, 0, H * 0.55)) - l.location
        l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return l
    s = H / 1.8
    area((-2.4 * s, -3.4 * s, 3.2 * s), 130 * s * s, 2.5 * s, (1.0, 0.96, 0.9))
    area((3.2 * s, -2.2 * s, 1.4 * s), 40 * s * s, 3.5 * s, (0.85, 0.9, 1.0))
    area((1.2 * s, 3.6 * s, 3.0 * s), 160 * s * s, 2.0 * s, (0.9, 0.95, 1.0))
    area((-3.0 * s, 2.0 * s, 1.0 * s), 30 * s * s, 3.0 * s)
    bpy.ops.mesh.primitive_plane_add(size=60)
    gp = bpy.context.object
    gm = bpy.data.materials.new("PreviewGround"); gm.use_nodes = True
    b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.07, 0.07, 0.075, 1); b.inputs["Roughness"].default_value = 0.9
    gp.data.materials.append(gm)
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.eevee.taa_render_samples = 24
    except Exception:
        pass
    return cam


def aim(cam, az_deg, target, dist, elev=0.0, lens=70):
    a = math.radians(az_deg)
    cam.location = Vector((math.sin(a) * dist, -math.cos(a) * dist, target.z + elev))
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


def render_views(arm, H, tiles_dir, extra=0.0):
    os.makedirs(tiles_dir, exist_ok=True)
    sc = bpy.context.scene
    cam = setup_preview(H)
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    sc.frame_set(1)
    tgt = Vector((0, 0, H * 0.52))
    dist = H * (2.35 + extra)
    for k, (label, az) in enumerate((("front", 0), ("side", 90), ("back", 180), ("threeq", -35))):
        aim(cam, az, tgt, dist, elev=H * 0.05)
        sc.render.filepath = os.path.join(tiles_dir, f"view_{k}_{label}.png")
        bpy.ops.render.render(write_still=True)
    # 上半身特寫（檢查材質與分件）
    aim(cam, -28, Vector((0, 0, H * 0.78)), H * 1.15, elev=H * 0.06)
    sc.render.filepath = os.path.join(tiles_dir, "close_0.png")
    bpy.ops.render.render(write_still=True)
    aim(cam, 150, Vector((0, 0, H * 0.72)), H * 1.25, elev=H * 0.10)
    sc.render.filepath = os.path.join(tiles_dir, "close_1.png")
    bpy.ops.render.render(write_still=True)
    aim(cam, 25, Vector((0, 0, H * 0.25)), H * 1.2, elev=H * 0.10)
    sc.render.filepath = os.path.join(tiles_dir, "close_2.png")
    bpy.ops.render.render(write_still=True)
    return cam


def render_actions(arm, H, tiles_dir, cam, n=6, res=(400, 400), az=-32, only=None, width=2.15):
    sc = bpy.context.scene
    os.makedirs(tiles_dir, exist_ok=True)
    sc.render.resolution_x, sc.render.resolution_y = res
    try:
        sc.eevee.taa_render_samples = 12
    except Exception:
        pass
    tgt = Vector((0, -H * 0.12, H * 0.50))
    aim(cam, az, tgt, H * width, elev=H * 0.22, lens=50)
    ad = arm.animation_data
    names = [t.name for t in ad.nla_tracks]
    for r, name in enumerate(names):
        if only and name not in only:
            continue
        act = bpy.data.actions[name]
        ad.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        for k in range(n):
            f = int(round(f0 + (f1 - f0) * k / (n - 1)))
            sc.frame_set(f)
            sc.render.filepath = os.path.join(tiles_dir, f"act_{r:02d}_{name}_{k}_f{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    ad.action = None


def write_meta(rig, model, out_dir):
    """把 rig.meta（各片段時長、命中時間、是否循環）寫成 <out_dir>/<model>.clipmeta.json。"""
    import json
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, model + ".clipmeta.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rig.meta, f, ensure_ascii=False, indent=1)
    print("META", p, flush=True)


# ================================================================ v3 主角材質（程序化＋本機 CC0 貼圖 → 烘焙）
def _hex(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def _vor(g, scale, feature="F1", rnd=1.0, offs=0.0, stretch=None):
    n = g.N.new("ShaderNodeTexVoronoi")
    n.feature = feature
    n.inputs["Scale"].default_value = scale
    n.inputs["Randomness"].default_value = rnd
    mp = g.N.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (offs, offs * 1.3, offs * 0.7)
    if stretch:
        mp.inputs["Scale"].default_value = stretch
    g.L.new(g.tc.outputs["Object"], mp.inputs["Vector"])
    g.L.new(mp.outputs[0], n.inputs["Vector"])
    return n


def _snoise(g, scale, sxyz=(1, 1, 1), rot=(0, 0, 0), detail=2.0, rough=0.5, offs=0.0):
    n = g.N.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    mp = g.N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = sxyz
    mp.inputs["Rotation"].default_value = rot
    mp.inputs["Location"].default_value = (offs, offs * 0.6, offs * 1.4)
    g.L.new(g.tc.outputs["Object"], mp.inputs["Vector"])
    g.L.new(mp.outputs[0], n.inputs["Vector"])
    return n.outputs["Fac"]


def _detail_uv(g):
    n = g.N.new("ShaderNodeUVMap"); n.uv_map = "detail"
    s = g.N.new("ShaderNodeSeparateXYZ")
    g.L.new(n.outputs["UV"], s.inputs[0])
    return s.outputs[0], s.outputs[1]


def _band(g, x, c, w):
    """1 - smoothstep(|x-c|, 0, w)：在 c 附近寬 w 的帶子。"""
    d = g.math("ABSOLUTE", g.math("SUBTRACT", x, c))
    return g.math("SUBTRACT", 1.0, g.ramp(d, 0.0, w), clamp=True)


def define_v3(key, group, kind, col, rough=0.5, metal=0.0, bump=0.5, seed=0.0, mud_z=None, mud_amt=0.8, mud_col="#4a443c",
              dark=None, edge_col=None, rust=0.06, tex_size=None, fade_z=None, fade_col=None, scratch=1.0, hammer=1.0, dents=1.0,
              stain=0.6, ao_shade=0.55, wear=1.0, stitch=True, crack=1.0, holes_z=None, dirt=0.75):
    """kind：steel／iron／blade／mail／linen／wool／leather／grip／void。顏色用 hex（sRGB）。"""
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    g = NG(m)
    N, L = g.N, g.L
    out = N.new("ShaderNodeOutputMaterial")
    d = dict(mat=m, group=group, out=out, key=key, tint=_hex(col), emit=None, emit_strength=1.0)
    SRC[key] = d
    C = _hex(col)
    Cd = _hex(dark) if dark else tuple(x * 0.55 for x in C)
    cav = g.math("SUBTRACT", 1.0, g.ao(0.045), clamp=True)
    aofar = g.ao(0.28)
    n1 = g.noise(3.5, 6, 0.6, seed)
    n2 = g.noise(18.0, 5, 0.65, seed + 7)
    h = g.math("ADD", 0.5, 0.0)
    rsock = g.math("ADD", rough, g.math("MULTIPLY", g.math("SUBTRACT", n2, 0.5), 0.16))
    msock = g.math("ADD", metal, 0.0)
    colr = g.mix(g.math("MULTIPLY", g.ramp(n1, 0.40, 0.78), 0.6), C, Cd)          # 大片明暗斑駁
    metallic_kind = kind in ("steel", "iron", "blade", "mail")
    if kind == "void":
        colr = g.mix(0.0, (0.004, 0.004, 0.005), (0.004, 0.004, 0.005))
        rsock = g.math("ADD", 1.0, 0.0); msock = g.math("ADD", 0.0, 0.0); ao_shade = 0.0
    if kind in ("steel", "iron", "blade"):
        mtex = g.image("Metal024", "Color", tex_size or 0.45, cs="sRGB", offs=(0.1 + seed, 0.3, 0.2))
        ml = g.lum(mtex)
        colr = g.mix(1.0, colr, g.mix(g.ramp(ml, 0.25, 0.65), (0.86, 0.86, 0.86), (1.08, 1.08, 1.08)), "MULTIPLY")
        mh = g.image("Metal024", "Displacement", tex_size or 0.45, offs=(0.1 + seed, 0.3, 0.2))
        h = g.math("ADD", h, g.math("MULTIPLY", g.math("SUBTRACT", mh, 0.5), 0.25))
        if hammer > 0:   # 錘紋：一顆顆淺碗
            vz = _vor(g, 42.0, "SMOOTH_F1", 1.0, seed + 0.3)
            h = g.math("ADD", h, g.math("MULTIPLY", vz.outputs["Distance"], 0.55 * hammer))
            colr = g.mix(g.math("MULTIPLY", g.ramp(vz.outputs["Distance"], 0.25, 0.9), 0.10 * hammer), colr, Cd)
        if dents > 0:    # 幾個明顯凹痕
            vd = _vor(g, 5.5, "F1", 1.0, seed + 4.1)
            sel = g.ramp(g.lum(vd.outputs["Color"]), 0.62, 0.66)
            dm = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.ramp(vd.outputs["Distance"], 0.02, 0.13), clamp=True), sel)
            h = g.math("SUBTRACT", h, g.math("MULTIPLY", dm, 1.6 * dents))
        if scratch > 0:  # 細刮痕：多半橫向（z 方向壓縮的噪聲 → 橫線）
            s1 = _snoise(g, 6.0, (1.0, 1.0, 34.0), (0.0, 0.0, 0.3), 2.0, 0.5, seed + 2)
            s2 = _snoise(g, 7.0, (1.0, 26.0, 1.0), (0.5, 0.2, 0.9), 2.0, 0.5, seed + 5)
            l1 = g.math("SUBTRACT", 1.0, g.ramp(g.math("ABSOLUTE", g.math("SUBTRACT", s1, 0.5)), 0.0, 0.010), clamp=True)
            l2 = g.math("SUBTRACT", 1.0, g.ramp(g.math("ABSOLUTE", g.math("SUBTRACT", s2, 0.5)), 0.0, 0.007), clamp=True)
            sm = g.math("MULTIPLY", g.math("MAXIMUM", l1, g.math("MULTIPLY", l2, 0.7)), g.ramp(g.noise(2.2, 3, 0.5, seed + 9), 0.42, 0.62))
            sm = g.math("MULTIPLY", sm, scratch, clamp=True)
            colr = g.mix(g.math("MULTIPLY", sm, 0.55), colr, _hex("#a4a6a1"))
            rsock = g.mixf(g.math("MULTIPLY", sm, 0.7), rsock, 0.28)
            h = g.math("SUBTRACT", h, g.math("MULTIPLY", sm, 0.35))
    if kind == "mail":
        S = tex_size or 0.12
        op = g.image("Chainmail004", "Opacity", S, offs=(0.2, 0.1, 0.4))
        cc = g.lum(g.image("Chainmail004", "Color", S, cs="sRGB", offs=(0.2, 0.1, 0.4)))
        ring = g.ramp(op, 0.35, 0.65)
        rc = g.mix(1.0, colr, g.mix(g.ramp(cc, 0.15, 0.85), (0.55, 0.55, 0.55), (1.35, 1.35, 1.35)), "MULTIPLY")
        colr = g.mix(ring, (0.006, 0.006, 0.0055), rc)
        msock = g.math("MULTIPLY", ring, metal)
        rsock = g.mixf(ring, 0.92, rsock)
        mh = g.image("Chainmail004", "Displacement", S, offs=(0.2, 0.1, 0.4))
        h = g.math("ADD", g.math("MULTIPLY", mh, 1.0), 0.0)
    if kind in ("linen", "wool"):
        S = tex_size or (0.20 if kind == "linen" else 0.42)
        ft = g.lum(g.image("Fabric030", "Color", S, cs="sRGB", offs=(0.3 + seed, 0.2, 0.6)))
        fh = g.image("Fabric030", "Displacement", S, offs=(0.3 + seed, 0.2, 0.6))
        colr = g.mix(1.0, colr, g.mix(g.ramp(ft, 0.25, 0.6), (0.80, 0.80, 0.80), (1.12, 1.12, 1.12)), "MULTIPLY")
        h = g.math("ADD", g.math("MULTIPLY", fh, 0.8), 0.1)
        if kind == "wool":   # 毛料細絨
            fz = g.noise(700.0, 2, 0.5, seed + 3)
            h = g.math("ADD", h, g.math("MULTIPLY", fz, 0.45))
            colr = g.mix(g.math("MULTIPLY", g.ramp(fz, 0.45, 0.75), 0.18), colr, _hex("#3a4560"))
        else:                # 亞麻：細織紋（detail UV 的經緯線）
            ux, uy = _detail_uv(g)
            wa = g.math("SINE", g.math("MULTIPLY", ux, 2 * math.pi / 0.0036))
            wb = g.math("SINE", g.math("MULTIPLY", uy, 2 * math.pi / 0.0036))
            wv = g.math("MULTIPLY", g.math("ADD", g.math("MULTIPLY", wa, wb), 1.0), 0.5)
            h = g.math("ADD", h, g.math("MULTIPLY", wv, 0.35))
        if stain > 0:        # 大片泥污、水漬（深色、邊緣暈開＋水痕邊）
            ns = g.noise(2.2, 5, 0.62, seed + 11)
            o = 0.08 * stain
            blot = g.ramp(ns, 0.56 - o, 0.66 - o)
            rim = g.math("MULTIPLY", g.ramp(ns, 0.54 - o, 0.57 - o), g.math("SUBTRACT", 1.0, g.ramp(ns, 0.58 - o, 0.62 - o)))
            colr = g.mix(g.math("MULTIPLY", blot, 0.75), colr, _hex("#3a3833"))
            colr = g.mix(g.math("MULTIPLY", rim, 0.45), colr, _hex("#2e2c28"))
            nf = g.noise(3.0, 4, 0.6, seed + 23)
            colr = g.mix(g.math("MULTIPLY", g.ramp(nf, 0.62, 0.78), 0.55), colr, _hex(fade_col or ("#6a6e6c" if kind == "linen" else "#3a4252")))
    if holes_z:             # 胸口小破洞（貼圖：黑洞＋毛邊淺色線頭），只在正面一段高度
        vh = _vor(g, 7.0, "F1", 1.0, seed + 8.8, stretch=(1.0, 1.0, 0.8))
        sel = g.ramp(g.lum(vh.outputs["Color"]), 0.70, 0.71)
        zz = g.zcoord()
        zin = g.math("MULTIPLY", g.ramp(zz, holes_z[0], holes_z[0] + 0.02), g.math("SUBTRACT", 1.0, g.ramp(zz, holes_z[1] - 0.02, holes_z[1])))
        sy = g.N.new("ShaderNodeSeparateXYZ"); L.new(g.tc.outputs["Object"], sy.inputs[0])
        front = g.math("SUBTRACT", 1.0, g.ramp(sy.outputs[1], -0.06, -0.02))
        jag = g.math("MULTIPLY", g.math("SUBTRACT", g.noise(140.0, 3, 0.7, seed + 4), 0.5), 0.02)
        dd = g.math("ADD", vh.outputs["Distance"], jag)
        sel = g.math("MULTIPLY", g.math("MULTIPLY", sel, zin), front)
        hole = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.ramp(dd, 0.030, 0.036), clamp=True), sel)
        fray = g.math("MULTIPLY", g.math("SUBTRACT", g.ramp(dd, 0.030, 0.036), g.ramp(dd, 0.040, 0.052)), sel)
        colr = g.mix(fray, colr, _hex("#7c807c"))
        colr = g.mix(hole, colr, (0.004, 0.004, 0.004))
        h = g.math("SUBTRACT", h, g.math("MULTIPLY", hole, 1.5))
    if kind in ("leather", "grip"):
        lh = g.image("Leather026", "Displacement", tex_size or 0.22, offs=(0.6 + seed, 0.2, 0.1))
        colr = g.mix(1.0, colr, g.mix(g.ramp(lh, 0.3, 0.7), (0.82, 0.82, 0.82), (1.15, 1.15, 1.15)), "MULTIPLY")
        h = g.math("ADD", g.math("MULTIPLY", lh, 0.6), 0.2)
        wr = _snoise(g, 9.0, (1.0, 1.0, 3.5), (0.3, 0.6, 0.1), 3.0, 0.6, seed + 13)       # 皺褶
        h = g.math("ADD", h, g.math("MULTIPLY", wr, 0.5))
        if crack > 0:        # 龜裂
            vc = _vor(g, 140.0, "DISTANCE_TO_EDGE", 1.0, seed + 1.7)
            cr = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.ramp(vc.outputs["Distance"], 0.0, 0.05), clamp=True), g.ramp(g.noise(4.0, 3, 0.5, seed + 31), 0.5, 0.62))
            cr = g.math("MULTIPLY", cr, crack, clamp=True)
            colr = g.mix(g.math("MULTIPLY", cr, 0.6), colr, tuple(x * 0.45 for x in C))
            h = g.math("SUBTRACT", h, g.math("MULTIPLY", cr, 0.5))
        ux, uy = _detail_uv(g)
        valid = g.math("SUBTRACT", 1.0, g.ramp(uy, 1.05, 1.1), clamp=True)
        if kind == "grip":   # 斜纏皮條（間距 0.004H）
            sp = g.math("FRACT", g.math("ADD", g.math("DIVIDE", ux, 0.0072), uy))
            tri = g.math("ABSOLUTE", g.math("SUBTRACT", g.math("MULTIPLY", sp, 2.0), 1.0))
            h = g.math("ADD", h, g.math("MULTIPLY", g.math("SUBTRACT", 1.0, tri), 1.4))
            colr = g.mix(g.math("MULTIPLY", g.ramp(tri, 0.75, 1.0), 0.6), colr, tuple(x * 0.5 for x in C))
        elif stitch:          # 邊緣縫線（針距 0.004H）＋邊緣磨淺
            lane = g.math("ADD", _band(g, uy, 0.14, 0.035), _band(g, uy, 0.86, 0.035))
            dash = g.ramp(g.math("SINE", g.math("MULTIPLY", ux, 2 * math.pi / 0.0072)), 0.1, 0.45)
            st = g.math("MULTIPLY", g.math("MULTIPLY", lane, dash), valid, clamp=True)
            hole = g.math("MULTIPLY", g.math("MULTIPLY", lane, g.math("SUBTRACT", 1.0, dash)), valid, clamp=True)
            h = g.math("ADD", g.math("SUBTRACT", h, g.math("MULTIPLY", hole, 0.5)), g.math("MULTIPLY", st, 0.9))
            colr = g.mix(g.math("MULTIPLY", st, 0.85), colr, _hex("#7a6a52"))
            ew = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.ramp(g.math("MINIMUM", uy, g.math("SUBTRACT", 1.0, uy)), 0.0, 0.09), clamp=True), valid)
            colr = g.mix(g.math("MULTIPLY", ew, 0.55 * wear), colr, _hex(edge_col) if edge_col else tuple(min(1, x * 1.9) for x in C))
            rsock = g.mixf(g.math("MULTIPLY", ew, 0.5), rsock, rough - 0.12)
    # 邊緣磨亮（板甲翻邊／皮件邊角）
    if wear > 0 and kind not in ("void", "mail"):
        e = g.math("MULTIPLY", g.edge(0.004), 14.0, clamp=True)
        e = g.math("MULTIPLY", e, g.ramp(n2, 0.28, 0.6))
        e = g.math("MULTIPLY", e, wear, clamp=True)
        ec = _hex(edge_col) if edge_col else (tuple(min(1, x * 1.7) for x in C) if not metallic_kind else _hex("#b0b2ad"))
        colr = g.mix(e, colr, ec)
        rsock = g.mixf(e, rsock, 0.28 if metallic_kind else rough - 0.15)
    # 鏽：只在縫隙／凹處、暗褐（≤8%）
    if rust > 0 and metallic_kind:
        rm = g.ramp(g.math("ADD", g.math("MULTIPLY", cav, 1.25), g.math("MULTIPLY", g.math("SUBTRACT", n2, 0.5), 0.5)), 0.78 - rust * 2.2, 0.92 - rust * 2.2)
        rt = g.lum(g.image("Rust009", "Color", 0.3, cs="sRGB", offs=(0.4, 0.1, 0.7)))
        rcol = g.mix(g.ramp(rt, 0.1, 0.6), _hex("#3e3228"), _hex("#5a4a3a"))
        colr = g.mix(rm, colr, rcol)
        rsock = g.mixf(rm, rsock, 0.85)
        msock = g.mixf(rm, msock, 0.25)
        rh = g.image("Rust009", "Displacement", 0.3, offs=(0.4, 0.1, 0.7))
        h = g.math("ADD", h, g.math("MULTIPLY", rm, g.math("MULTIPLY", rh, 0.6)))
    # 凹處積垢
    if kind != "void":
        dm = g.math("MULTIPLY", g.math("POWER", cav, 1.4), dirt, clamp=True)
        colr = g.mix(dm, colr, _hex("#2a2824"))
        rsock = g.mixf(g.math("MULTIPLY", dm, 0.6), rsock, 0.9)
    # 下緣泥（離地 0.15H 內）
    if mud_z:
        mz = g.math("SUBTRACT", 1.0, g.ramp(g.zcoord(), mud_z * 0.45, mud_z))
        mz = g.math("MULTIPLY", g.math("MULTIPLY", mz, g.math("ADD", 0.45, g.math("MULTIPLY", n1, 0.8))), mud_amt, clamp=True)
        colr = g.mix(mz, colr, _hex(mud_col))
        rsock = g.mixf(mz, rsock, 0.93)
        msock = g.mixf(mz, msock, 0.0)
        h = g.math("ADD", h, g.math("MULTIPLY", mz, g.math("MULTIPLY", g.noise(60.0, 4, 0.7, seed + 2), 0.6)))
    if fade_z:              # 披風下緣褪色
        fz = g.math("SUBTRACT", 1.0, g.ramp(g.zcoord(), fade_z * 0.5, fade_z))
        colr = g.mix(g.math("MULTIPLY", fz, 0.7), colr, _hex(fade_col or "#3a4252"))
    shade = g.mixf(ao_shade, 1.0, aofar)
    colf = g.mix(1.0, colr, g.mix(0.0, (1, 1, 1), (1, 1, 1)), "MULTIPLY")
    mulc = N.new("ShaderNodeVectorMath"); mulc.operation = "SCALE"
    L.new(colf, mulc.inputs[0]); L.new(shade, mulc.inputs["Scale"])
    colout = mulc.outputs[0]
    rsock = g.math("ADD", rsock, 0.0, clamp=True)
    bmp = N.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump; bmp.inputs["Distance"].default_value = 0.004
    L.new(h, bmp.inputs["Height"])
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    L.new(colout, bsdf.inputs["Base Color"]); L.new(rsock, bsdf.inputs["Roughness"]); L.new(msock, bsdf.inputs["Metallic"])
    L.new(bmp.outputs[0], bsdf.inputs["Normal"])
    emC = N.new("ShaderNodeEmission"); L.new(colout, emC.inputs[0])
    comb = N.new("ShaderNodeCombineColor")
    L.new(aofar, comb.inputs[0]); L.new(rsock, comb.inputs[1]); L.new(msock, comb.inputs[2])
    emO = N.new("ShaderNodeEmission"); L.new(comb.outputs[0], emO.inputs[0])
    L.new(bsdf.outputs[0], out.inputs[0])
    tgt = N.new("ShaderNodeTexImage"); tgt.name = "BAKE_TARGET"
    d.update(emitC=emC, emitO=emO, bsdf=bsdf, target=tgt)
    return d
