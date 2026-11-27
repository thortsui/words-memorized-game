"""v3 霜冠祭司：材質與烘焙（複製自 soul_humanoid_bake.py 後大改，不改共用檔）。
改動：
  - 程序化材質：三平面亞麻／羊毛平織紋（經緯線、上下交錯、粗細不均）、霜（由下往上漸減＋皺褶凹處＋朝上面＋頂點屬性 fr）、
    冰（內部裂紋、稜面、根部霜）、乾皮（皺紋、凍裂）。
  - 「只進高模」的細節幾何（金線捲草刺繡、縫線、浮雕）：烘焙時併進高模，只把顏色／法線烘到低模上，不增加遊戲面數。
  - 三組圖集：A 布料（2048）、B 皮／金屬／皮革（2048）、C 冰（1024，最終材質半透明＋自發光近似透光）。
  - 布料不加 Solidify（內外面會共用 UV 互相覆蓋），厚度改用邊緣捲邊（Builder rim）。
"""
import bpy, os, glob, math
from mathutils import Vector
from soul_humanoid_lib import TEXDIR

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
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.N = self.nt.nodes
        self.L = self.nt.links
        self.N.clear()
        self.tc = self.N.new("ShaderNodeTexCoord")
        self.geo = self.N.new("ShaderNodeNewGeometry")
        self._xyz = None
        self._nxyz = None

    def put(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
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

    def add(self, a, b, clamp=False):
        return self.math("ADD", a, b, clamp)

    def mul(self, a, b, clamp=False):
        return self.math("MULTIPLY", a, b, clamp)

    def mix(self, fac, a, b, kind="MIX"):
        n = self.N.new("ShaderNodeMixRGB"); n.blend_type = kind
        self.put(n.inputs[0], fac); self.put(n.inputs[1], a); self.put(n.inputs[2], b)
        return n.outputs[0]

    def mixf(self, fac, a, b):
        n = self.N.new("ShaderNodeMapRange")
        self.put(n.inputs[0], fac); n.inputs[1].default_value = 0; n.inputs[2].default_value = 1
        self.put(n.inputs[3], a); self.put(n.inputs[4], b)
        return n.outputs[0]

    def ramp(self, x, lo, hi):
        n = self.N.new("ShaderNodeMapRange"); n.interpolation_type = "SMOOTHSTEP"
        self.put(n.inputs[0], x); self.put(n.inputs[1], lo); self.put(n.inputs[2], hi)
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

    def noise(self, scale, detail=6.0, rough=0.6, offs=0.0, distort=0.0, color=False):
        n = self.N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distort
        mp = self.N.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (offs, offs * 1.7, offs * 0.6)
        self.L.new(self.tc.outputs["Object"], mp.inputs["Vector"])
        self.L.new(mp.outputs[0], n.inputs["Vector"])
        return n.outputs["Color" if color else "Fac"]

    def voronoi(self, scale, feature="F1", out="Distance", offs=0.0, rand=1.0, stretch=(1, 1, 1)):
        n = self.N.new("ShaderNodeTexVoronoi")
        n.feature = feature
        n.inputs["Scale"].default_value = scale
        if "Randomness" in n.inputs:
            n.inputs["Randomness"].default_value = rand
        mp = self.N.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (offs, offs * 1.3, offs * 0.7)
        mp.inputs["Scale"].default_value = stretch
        self.L.new(self.tc.outputs["Object"], mp.inputs["Vector"])
        self.L.new(mp.outputs[0], n.inputs["Vector"])
        return n.outputs[out]

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

    def xyz(self):
        if self._xyz is None:
            s = self.N.new("ShaderNodeSeparateXYZ")
            self.L.new(self.tc.outputs["Object"], s.inputs[0])
            self._xyz = s.outputs
        return self._xyz

    def nxyz(self):
        if self._nxyz is None:
            s = self.N.new("ShaderNodeSeparateXYZ")
            self.L.new(self.geo.outputs["Normal"], s.inputs[0])
            self._nxyz = s.outputs
        return self._nxyz

    def attr(self, name):
        n = self.N.new("ShaderNodeAttribute"); n.attribute_type = "GEOMETRY"; n.attribute_name = name
        return n.outputs["Fac"]

    # ---- 平織紋：a、b 為面上兩個方向的座標，s 為線距。回傳 0~1 高度（線中央高、縫隙低、上下交錯）
    def weave2(self, a, b, s, slub, wob):
        A = self.add(self.mul(a, 1.0 / s), wob)
        Bq = self.add(self.mul(b, 1.0 / s), self.mul(wob, 0.7))
        sa = self.math("SINE", self.mul(A, math.pi))
        sb = self.math("SINE", self.mul(Bq, math.pi))
        pa = self.math("POWER", self.math("ABSOLUTE", sa), 0.55)
        pb = self.math("POWER", self.math("ABSOLUTE", sb), 0.55)
        c = self.mul(self.mul(sa, sb), 3.0)
        c = self.math("MAXIMUM", self.math("MINIMUM", c, 1.0), -1.0)
        t = self.add(self.mul(c, 0.5), 0.5)
        h = self.mixf(t, pb, pa)
        return self.mul(h, slub)

    def weave(self, s, seed=0.0):
        """三平面平織紋（依法線混合 XZ／YZ／XY 平面）。"""
        x, y, z = self.xyz()[0], self.xyz()[1], self.xyz()[2]
        nx, ny, nz = [self.math("POWER", self.math("ABSOLUTE", c), 4.0) for c in self.nxyz()]
        tot = self.add(self.add(nx, ny), self.add(nz, 1e-4))
        wob = self.mul(self.add(self.noise(9.0, 3, 0.5, seed + 1.3), -0.5), 1.6)
        slub = self.add(0.72, self.mul(self.noise(1.0 / (s * 14), 2, 0.5, seed + 5.1), 0.55))
        hy = self.weave2(x, z, s, slub, wob)       # 面朝 ±Y
        hx = self.weave2(y, z, s, slub, wob)       # 面朝 ±X
        hz = self.weave2(x, y, s, slub, wob)       # 面朝 ±Z
        h = self.add(self.add(self.mul(hy, ny), self.mul(hx, nx)), self.mul(hz, nz))
        return self.math("DIVIDE", h, tot)


SRC = {}


def define_mat(key, group="A", tex=None, size=0.5, tint=(1, 1, 1), sat=1.0, val=1.0, rough=None, rough_mul=1.0,
               metal=None, bump=0.4, bump_dist=0.004, wear=0.0, wear_col=(0.60, 0.58, 0.55), dirt=0.5,
               dirt_col=(0.035, 0.03, 0.025), ao_shade=0.6, U=1.0, color=None, seed=0.0, flat_rough=0.6,
               weave=None, frost=None, fx=None, hnoise=None, tex_mean=0.105, tex_k=0.45):
    """weave=(線距, 高度權重)；frost=dict(z0, z1, lo, hi, up, cav, attr, col, rough, grain)；fx(g, ctx) 可再改 ctx（col/rough/metal/h）。"""
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    g = NG(m)
    N, L = g.N, g.L
    out = N.new("ShaderNodeOutputMaterial")
    d = dict(mat=m, group=group, out=out, key=key, tint=tint)
    SRC[key] = d
    if tex:
        col = g.image(tex, "Color", size, cs="sRGB")
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = sat; hs.inputs["Value"].default_value = val
        L.new(col, hs.inputs["Color"])
        base = g.mix(1.0, hs.outputs[0], tint, "MULTIPLY")
        if color is not None:      # 掃描貼圖只提供明暗變化，底色照規格 hex
            ln = g.math("DIVIDE", g.lum(col), tex_mean)
            f = g.add(1.0 - tex_k, g.mul(ln, tex_k))
            base = g.mix(0.0, color, color)
            mulb = N.new("ShaderNodeVectorMath"); mulb.operation = "SCALE"
            L.new(base, mulb.inputs[0]); L.new(f, mulb.inputs["Scale"])
            base = mulb.outputs[0]
        r_img = g.image(tex, "Roughness", size)
        m_img = g.image(tex, "Metalness", size)
        h_img = g.image(tex, "Displacement", size)
        if h_img is None:
            h_img = g.lum(col)
        h = g.mul(h_img, 1.0)
    else:
        base = g.mix(0.0, color or tint, color or tint)
        r_img = m_img = None
        h = g.noise(hnoise or 60 / U, 4, 0.7, seed + 3)
    if rough is not None:
        rs = g.add(rough, 0.0)
        if r_img is not None:
            rs = g.add(g.mul(g.math("SUBTRACT", r_img, 0.5), 0.5), rough, clamp=True)
    elif r_img is not None:
        rs = g.mul(r_img, rough_mul, clamp=True)
    else:
        rs = g.add(flat_rough, 0.0)
    ms = g.add(metal if metal is not None else 0.0, 0.0) if (metal is not None or m_img is None) else g.add(m_img, 0.0)
    n2 = g.noise(22.0 / U, 5, 0.7, seed + 7)
    cav = g.math("SUBTRACT", 1.0, g.ao(0.05 * U), clamp=True)
    aofar = g.ao(0.30 * U)
    col = base
    if weave:
        s, wgt = weave
        wv = g.weave(s * U, seed)
        col = g.mix(1.0, col, g.mix(g.mul(wv, 1.0), (0.78, 0.78, 0.78), (1.06, 1.06, 1.06)), "MULTIPLY")
        h = g.add(g.mul(h, 1.0 - wgt), g.mul(wv, wgt))
    ctx = dict(col=col, rough=rs, metal=ms, h=h, cav=cav, n2=n2)
    if fx:
        fx(g, ctx)
    col, rs, ms, h = ctx["col"], ctx["rough"], ctx["metal"], ctx["h"]
    if wear > 0:
        e = g.mul(g.edge(0.006 * U), 14.0, clamp=True)
        e = g.mul(g.mul(e, g.ramp(n2, 0.30, 0.62)), wear, clamp=True)
        col = g.mix(e, col, wear_col)
        rs = g.mixf(e, rs, 0.34) if metal and metal > 0.5 else rs
    if dirt > 0:
        dm = g.mul(g.math("POWER", cav, 1.3), dirt, clamp=True)
        col = g.mix(dm, col, dirt_col)
        rs = g.mixf(dm, rs, 0.95)
        ms = g.mul(ms, g.math("SUBTRACT", 1.0, g.mul(dm, 0.8)))
    if frost:
        f = frost
        U_ = U
        zf = g.math("SUBTRACT", 1.0, g.ramp(g.xyz()[2], f.get("z0", 0.0) * U_, f.get("z1", 1.0) * U_))
        amt = g.add(f.get("lo", 0.15), g.mul(zf, f.get("hi", 0.6) - f.get("lo", 0.15)))
        up = g.ramp(g.nxyz()[2], 0.15, 0.85)
        amt = g.add(amt, g.mul(up, f.get("up", 0.3)))
        amt = g.add(amt, g.mul(cav, f.get("cav", 0.6)))
        amt = g.add(amt, g.mul(g.attr("fr"), f.get("attr", 0.8)))
        # 霜＝點狀結晶：高頻斑點決定覆蓋（不是低頻雲斑），中頻只微調；顆粒法線＋亮點
        nlo = g.noise(f.get("ns", 40.0) / U_, 4, 0.6, seed + 11)
        pat = g.add(g.mul(nlo, 0.45), g.mul(g.voronoi(240.0 / U_, "F1", "Distance", seed + 5), 0.55))
        fm = g.ramp(g.add(amt, g.mul(g.add(pat, -0.50), 1.4)), 0.42, 0.62)
        fm_lo = g.ramp(g.add(amt, g.mul(g.add(nlo, -0.5), 1.2)), 0.35, 0.75)      # 粗糙度只跟低頻覆蓋走（貼圖好壓縮）
        grain = g.voronoi(f.get("grain", 700.0) / U_, "F1", "Distance", seed + 2)
        gr = g.math("SUBTRACT", 1.0, g.ramp(grain, 0.0, 0.40))
        fcol = f.get("col", (0.80, 0.85, 0.88))
        col = g.mix(g.mul(fm, f.get("opac", 0.78), clamp=True), col, fcol)
        col = g.mix(g.mul(g.mul(fm, gr), 0.5), col, (0.95, 0.98, 1.0))
        rs = g.mixf(fm_lo, rs, f.get("rough", 0.62))
        ms = g.mul(ms, g.math("SUBTRACT", 1.0, fm_lo))
        h = g.add(h, g.mul(g.mul(fm, gr), f.get("gh", 0.8)))
    shade = g.mixf(ao_shade, 1.0, aofar)
    mulc = N.new("ShaderNodeVectorMath"); mulc.operation = "SCALE"
    L.new(col, mulc.inputs[0]); L.new(shade, mulc.inputs["Scale"])
    colout = mulc.outputs[0]
    bmp = N.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump; bmp.inputs["Distance"].default_value = bump_dist * U
    L.new(h, bmp.inputs["Height"])
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    L.new(colout, bsdf.inputs["Base Color"]); L.new(rs, bsdf.inputs["Roughness"]); L.new(ms, bsdf.inputs["Metallic"])
    L.new(bmp.outputs[0], bsdf.inputs["Normal"])
    emC = N.new("ShaderNodeEmission"); L.new(colout, emC.inputs[0])
    comb = N.new("ShaderNodeCombineColor")
    L.new(aofar, comb.inputs[0]); L.new(rs, comb.inputs[1]); L.new(ms, comb.inputs[2])
    emO = N.new("ShaderNodeEmission"); L.new(comb.outputs[0], emO.inputs[0])
    L.new(bsdf.outputs[0], out.inputs[0])
    tgt = N.new("ShaderNodeTexImage"); tgt.name = "BAKE_TARGET"
    d.update(emitC=emC, emitO=emO, bsdf=bsdf, target=tgt)
    return d


# ---------------------------------------------------------------- 頂點屬性（霜遮罩）
def set_attr(ob, fn, name="fr"):
    me = ob.data
    a = me.attributes.get(name) or me.attributes.new(name, "FLOAT", "POINT")
    a.data.foreach_set("value", [float(fn(v.co)) for v in me.vertices])


def ensure_attr(ob, name="fr"):
    if ob.type == "MESH" and ob.data.attributes.get(name) is None:
        ob.data.attributes.new(name, "FLOAT", "POINT")


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


def _fix_degenerate_uv(ob):
    """捲邊（rim）面的 UV 是零面積（直接複製邊界 UV），烘出的法線會亂掉、看起來像鍍鉻邊。
    改成各自一小塊正方形（排在主島之外），讓它烘到該處材質的平均顏色與平坦法線。"""
    import bmesh as _bm
    bm = _bm.new(); bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.active
    n = 0
    for f in bm.faces:
        pts = [l[uv].uv for l in f.loops]
        a = 0.0
        for i in range(len(pts)):
            p0, p1 = pts[i], pts[(i + 1) % len(pts)]
            a += p0.x * p1.y - p1.x * p0.y
        if abs(a) < 1e-10:
            k = n % 400; r = n // 400
            x0, y0 = -300.0 - k * 0.012, r * 0.012
            sq = ((0, 0), (0.008, 0), (0.008, 0.008), (0, 0.008))
            for i, l in enumerate(f.loops):
                q = sq[min(i, 3)]
                l[uv].uv = (x0 + q[0], y0 + q[1])
            n += 1
    bm.to_mesh(ob.data); bm.free()
    print("UVFIX degenerate faces", ob.name, n, flush=True)


def _pack_uv(ob, margin=0.002):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(rotate=True, rotate_method="AXIS_ALIGNED", scale=True, merge_overlap=True,
                                margin_method="FRACTION", margin=margin, shape_method="CONCAVE")
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
    """金屬／皮革零件的邊緣倒角；布料（soft）只保留捲邊厚度，不倒角。"""
    nb = 0
    for ob in B.parts:
        rim = ob.get("rim")
        if rim and not ob.get("soft"):
            md = ob.modifiers.new("Bevel", "BEVEL")
            md.width = min(rim * 0.45, 0.004); md.segments = 1; md.limit_method = "ANGLE"
            md.angle_limit = math.radians(40); md.profile = 0.6
            _apply_mod(ob, md); _resmooth(ob, 70); nb += 1
    print("POLISH bevel", nb, flush=True)


DETAIL = {
    "metal": [("VORONOI", 0.0020, 0.05, "F1"), ("CLOUDS", 0.0008, 0.006, None)],
    "cloth": [("CLOUDS", 0.0040, 0.040, None), ("CLOUDS", 0.0012, 0.009, None)],
    "leather": [("CLOUDS", 0.0022, 0.02, None), ("VORONOI", 0.001, 0.008, "F2")],
    "skin": [("CLOUDS", 0.0010, 0.010, None), ("CLOUDS", 0.0005, 0.004, None)],
    "ice": [("VORONOI", 0.0012, 0.025, "F1")],
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


def make_high(ob, detail_of, U=1.0, levels=2):
    hi = ob.copy()
    hi.data = ob.data.copy()
    hi.name = ob.name + "_high"
    bpy.context.scene.collection.objects.link(hi)
    for g in list(hi.vertex_groups):
        hi.vertex_groups.remove(g)
    sub = hi.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = levels
    _apply_mod(hi, sub)
    cats = {}
    me = hi.data
    for p in me.polygons:
        sl = hi.material_slots[p.material_index].material
        key = next((d["key"] for d in SRC.values() if d["mat"] == sl), None)
        c = detail_of(key)
        if c:
            cats.setdefault(c, set()).update(p.vertices)
    for c, vs in cats.items():
        gn = "det_" + c
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


def assemble(B, model, sizes, bake=True, samples=24, quick=False, detail_of=None, U=1.0, details=None, tex_dir=None,
             ice_alpha=0.82, ice_emit=0.22):
    """依材質組別合併、展 UV、烘焙。details：{組別: [只進高模的物件]}。回傳合併後的網格。"""
    sc = bpy.context.scene
    polish(B)
    out_dir = tex_dir or BAKED
    os.makedirs(out_dir, exist_ok=True)
    details = details or {}
    groups = {}
    for ob in B.parts:
        ensure_attr(ob)
        d = SRC[ob["matkey"]]
        ob.data.materials.append(d["mat"])
        groups.setdefault(d["group"], []).append(ob)
    for gk, lst in details.items():
        for ob in lst:
            ensure_attr(ob)
            ob.data.materials.append(SRC[ob["matkey"]]["mat"])
    joined = {gk: _join(groups[gk], f"{model}_{gk}") for gk in sorted(groups)}
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
    sc.render.bake.margin = 8
    sc.render.bake.use_clear = True
    sc.render.bake.target = "IMAGE_TEXTURES"
    for gk in sorted(joined):
        ob = joined[gk]
        sz = sizes.get(gk, 1024)
        _fix_degenerate_uv(ob)
        _pack_uv(ob)
        paths = {p: os.path.join(out_dir, f"{model}_{gk}_{p}.png") for p in ("color", "orm", "normal")}
        if bake:
            imgs = {"color": _new_img(f"{model}_{gk}_color", sz, "sRGB"), "orm": _new_img(f"{model}_{gk}_orm", sz, "Non-Color"),
                    "normal": _new_img(f"{model}_{gk}_normal", sz, "Non-Color")}
            hi = make_high(ob, detail_of, U) if detail_of else None
            if hi and details.get(gk):
                cp = []
                for o in details[gk]:
                    c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c); cp.append(c)
                    for g in list(c.vertex_groups):
                        c.vertex_groups.remove(g)
                bpy.ops.object.select_all(action="DESELECT")
                for c in cp:
                    c.select_set(True)
                hi.select_set(True)
                bpy.context.view_layer.objects.active = hi
                bpy.ops.object.join()
                hi = bpy.context.view_layer.objects.active
            bpy.ops.object.select_all(action="DESELECT")
            if hi:
                hi.select_set(True)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            sc.render.bake.use_selected_to_active = bool(hi)
            sc.render.bake.cage_extrusion = 0.007 * U
            sc.render.bake.max_ray_distance = 0.018 * U
            mats = [s.material for s in hi.material_slots] if hi else []
            mats = list({m.name: m for m in mats + [s.material for s in ob.material_slots]}.values())
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
                print("BAKED", model, gk, p, sz, flush=True)
            if hi:
                bpy.data.objects.remove(hi)
            sc.render.bake.use_selected_to_active = False
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
            if gk == "C":       # 冰：半透明＋以底色貼圖當自發光（近似透光）
                bsdf.inputs["Alpha"].default_value = ice_alpha
                nt.links.new(ic.outputs[0], bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = ice_emit
                try:
                    fm.surface_render_method = "BLENDED"
                except Exception:
                    pass
                try:
                    fm.blend_method = "BLEND"
                except Exception:
                    pass
            for n in (ic, io, inn):
                n.image.pack()
            ob.data.materials.clear()
            ob.data.materials.append(fm)
        else:
            for s in ob.material_slots:
                d = next(v for v in SRC.values() if v["mat"] == s.material)
                qm = bpy.data.materials.new("quick_" + d["key"])
                qm.use_nodes = True
                qb = next(n for n in qm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                t = d["tint"]
                qb.inputs["Base Color"].default_value = (t[0] * 0.8, t[1] * 0.8, t[2] * 0.8, 1)
                qb.inputs["Roughness"].default_value = 0.6
                s.material = qm
        finals.append(ob)
    for gk, lst in details.items():
        for o in lst:
            bpy.data.objects.remove(o)
    mesh = _join(finals, model + "_mesh")
    if mesh.data.attributes.get("fr"):
        mesh.data.attributes.remove(mesh.data.attributes["fr"])
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


def write_meta(rig, model, out_dir):
    import json
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, model + ".clipmeta.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rig.meta, f, ensure_ascii=False, indent=1)
    print("META", p, flush=True)
