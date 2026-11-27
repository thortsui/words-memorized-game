"""v3 暗影行刑者：來源材質（CC0 掃描貼圖＋程序化節點），烘焙前的「真材質」。
每個材質 = 目標色（spec hex）× 貼圖明暗變化 ＋ 程序化圖樣（織紋、錘痕、刮痕、皺褶、青筋、污漬、墨影漸層…），
圖樣同時寫進 Base Color／Roughness／Metallic 與 Bump（烘到法線貼圖）。
介面與 soul_humanoid_bake.define_mat 相同（登錄在 BK.SRC），可直接用 assemble 烘焙。
UV：圖樣用第二組 UV「srcuv」（建模時的公尺單位 UV，打包圖集前複製），尺度才會是真實尺寸。
"""
import bpy, math, os
import numpy as np
import soul_humanoid_bake as BK

_MEAN = {}


def lin(hexs):
    hexs = hexs.lstrip("#")
    c = [int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def tex_mean(asset):
    if asset in _MEAN:
        return _MEAN[asset]
    p = BK.tex_path(asset, "Color")
    im = bpy.data.images.load(p, check_existing=True)
    im.colorspace_settings.name = "sRGB"
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(-1, 4)[:, :3]
    lum = (a * np.array([0.2126, 0.7152, 0.0722])).sum(1).mean()
    _MEAN[asset] = float(max(lum, 0.02))
    return _MEAN[asset]


class G(BK.NG):
    """不清空節點的 NG（建自己的材質）。"""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.N = self.nt.nodes
        self.L = self.nt.links
        self.N.clear()
        self.tc = self.N.new("ShaderNodeTexCoord")
        self.geo = self.N.new("ShaderNodeNewGeometry")
        self._uv = None

    # ---- 基本
    def sep(self, vec):
        s = self.N.new("ShaderNodeSeparateXYZ")
        self.L.new(vec, s.inputs[0])
        return s.outputs[0], s.outputs[1], s.outputs[2]

    def uv(self):
        if self._uv is None:
            n = self.N.new("ShaderNodeUVMap"); n.uv_map = "srcuv"
            self._uv = n.outputs[0]
        return self._uv

    def vmath(self, op, a, b=None, scale=None):
        n = self.N.new("ShaderNodeVectorMath"); n.operation = op
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if scale is not None:
            self.put(n.inputs["Scale"], scale)
        return n.outputs[1] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs[0]

    def mapping(self, vec, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
        mp = self.N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        mp.inputs["Rotation"].default_value = rot
        mp.inputs["Location"].default_value = loc
        self.L.new(vec, mp.inputs["Vector"])
        return mp.outputs[0]

    def noisev(self, vec, scale, detail=4.0, rough=0.55, distort=0.0):
        n = self.N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distort
        self.L.new(vec, n.inputs["Vector"])
        return n.outputs["Fac"]

    def voronoi(self, vec, scale, feature="F1", rand=1.0, out="Distance"):
        n = self.N.new("ShaderNodeTexVoronoi")
        n.feature = feature
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rand
        self.L.new(vec, n.inputs["Vector"])
        return n.outputs[out]

    def white(self, vec):
        n = self.N.new("ShaderNodeTexWhiteNoise"); n.noise_dimensions = "3D"
        self.L.new(vec, n.inputs["Vector"])
        return n.outputs["Value"]

    def comb(self, x, y, z):
        n = self.N.new("ShaderNodeCombineXYZ")
        self.put(n.inputs[0], x); self.put(n.inputs[1], y); self.put(n.inputs[2], z)
        return n.outputs[0]

    def smoothstep(self, x, lo, hi):
        return self.ramp(x, lo, hi)

    def add(self, *xs):
        out = xs[0]
        for x in xs[1:]:
            out = self.math("ADD", out, x)
        return out

    def mul(self, a, b, clamp=False):
        return self.math("MULTIPLY", a, b, clamp=clamp)

    def inv(self, a):
        return self.math("SUBTRACT", 1.0, a, clamp=True)

    def line(self, field, width):
        """field 在 0.5 附近的細線：1 在線上、0 在外。"""
        return self.inv(self.ramp(self.math("ABSOLUTE", self.math("SUBTRACT", field, 0.5)), width * 0.3, width))

    # ---- 圖樣
    def weave(self, pitch, jitter=0.25):
        """平織：回傳 (高度 0~1, 紗線亮度變化, 孔隙遮罩)。pitch：格距（公尺）。"""
        u, v, _ = self.sep(self.uv())
        # 紗線輕微彎曲
        wob = self.math("MULTIPLY", self.math("SUBTRACT", self.noisev(self.uv(), 1.0 / (pitch * 6), 2.0), 0.5), jitter)
        uu = self.math("ADD", self.math("DIVIDE", u, pitch), wob)
        vv = self.math("ADD", self.math("DIVIDE", v, pitch), self.math("MULTIPLY", wob, -0.7))
        a = self.math("FRACT", uu); b = self.math("FRACT", vv)
        cu = self.math("FLOOR", uu); cv = self.math("FLOOR", vv)
        chk = self.math("FLOORED_MODULO", self.math("ADD", cu, cv), 2.0)
        pa = self.math("POWER", self.math("SINE", self.math("MULTIPLY", a, math.pi)), 0.55)
        pb = self.math("POWER", self.math("SINE", self.math("MULTIPLY", b, math.pi)), 0.55)
        hw = self.mul(pa, self.math("ADD", 0.45, self.mul(pb, 0.55)))
        hf = self.mul(pb, self.math("ADD", 0.45, self.mul(pa, 0.55)))
        h = self.mixf(chk, hw, hf)
        # 每根紗線的明暗（沿紗方向一致、跨紗不同）
        tw = self.white(self.comb(cu, 0.0, 3.1)); tf = self.white(self.comb(0.0, cv, 7.7))
        shade = self.mixf(chk, tw, tf)
        gap = self.mul(self.inv(pa), self.inv(pb))
        return h, shade, self.ramp(gap, 0.25, 0.7)

    def hammer(self, cell, seed=0.0):
        """錘紋凹點：cell 為凹點間距（公尺）。回傳高度（凹點中心低）。"""
        vec = self.mapping(self.tc.outputs["Object"], loc=(seed, seed * 1.3, seed * 0.7))
        d = self.voronoi(vec, 1.0 / cell, "SMOOTH_F1", 0.9)
        d2 = self.voronoi(vec, 2.3 / cell, "F1", 1.0)
        return self.add(self.math("POWER", self.math("MINIMUM", self.mul(d, 1.6), 1.0), 0.6), self.mul(self.math("POWER", self.math("MINIMUM", self.mul(d2, 1.6), 1.0), 0.6), 0.35))

    def scratches(self, density=0.5, scale=1.0, seed=0.0):
        """細長刮痕：兩組不同方向拉長的雜訊線，用遮罩打散。回傳 0~1（1=刮痕）。"""
        out = None
        for k, (rot, sx) in enumerate((((0.3, 0.9, 0.2), 60.0), ((1.1, 0.2, 1.4), 45.0), ((0.0, 1.5, 0.7), 80.0))):
            vec = self.mapping(self.tc.outputs["Object"], scale=(sx * scale, 2.2 * scale, 2.2 * scale), rot=rot, loc=(seed + k, seed * 2, k * 0.37))
            n = self.noisev(vec, 3.0, 1.0, 0.5)
            ln = self.line(n, 0.025)
            m = self.ramp(self.noisev(self.mapping(self.tc.outputs["Object"], loc=(k * 3.1 + seed, 0, 0)), 4.0 / scale, 2.0), 0.62 - density * 0.2, 0.72 - density * 0.2)
            s = self.mul(ln, m)
            out = s if out is None else self.math("MAXIMUM", out, s)
        return out

    def wrinkles(self, scale=1.0, stretch=(1.0, 1.0, 4.0), seed=0.0):
        """皮革／布的皺褶：拉長的脊線＋細碎龜裂。回傳高度（皺褶處低）。"""
        vec = self.mapping(self.tc.outputs["Object"], scale=stretch, loc=(seed, seed * 0.3, 0))
        n = self.noisev(vec, 9.0 / scale, 3.0, 0.5, 0.4)
        ridge = self.line(n, 0.06)
        crack = self.voronoi(self.tc.outputs["Object"], 160.0 / scale, "DISTANCE_TO_EDGE", 1.0)
        cr = self.ramp(crack, 0.0, 0.05)
        return self.add(self.mul(self.inv(ridge), 0.7), self.mul(cr, 0.3)), ridge

    def veins(self, scale=1.0, seed=0.0):
        vec = self.mapping(self.tc.outputs["Object"], scale=(1.0, 1.0, 2.5), loc=(seed, 0, 0))
        n = self.noisev(vec, 14.0 / scale, 2.0, 0.5, 0.3)
        ln = self.line(n, 0.035)
        m = self.ramp(self.noisev(self.mapping(self.tc.outputs["Object"], loc=(seed + 5, 0, 0)), 5.0 / scale, 2.0), 0.5, 0.62)
        return self.mul(ln, m)

    def scars(self, scale=1.0, seed=0.0):
        vec = self.mapping(self.tc.outputs["Object"], scale=(1.0, 1.0, 1.0), rot=(0.4, 0.9, 0.3), loc=(seed, seed, 0))
        wv = self.N.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
        wv.inputs["Scale"].default_value = 3.0 / scale; wv.inputs["Distortion"].default_value = 3.0
        wv.inputs["Detail"].default_value = 2.0
        self.L.new(vec, wv.inputs["Vector"])
        ln = self.ramp(wv.outputs["Fac"], 0.92, 0.985)
        m = self.ramp(self.noisev(self.mapping(self.tc.outputs["Object"], loc=(seed + 9, 0, 0)), 6.0 / scale, 1.0), 0.6, 0.66)
        return self.mul(ln, m)

    def splatter(self, amount=0.5, scale=1.0, seed=0.0, drip=True):
        """乾涸污漬：濺點＋往下流的痕跡。回傳 0~1。"""
        sp = self.ramp(self.add(self.noisev(self.mapping(self.tc.outputs["Object"], loc=(seed, 0, 0)), 18.0 / scale, 6.0, 0.7),
                                self.mul(self.noisev(self.mapping(self.tc.outputs["Object"], loc=(0, seed, 0)), 4.0 / scale, 2.0), 0.4)),
                       0.98 - amount * 0.35, 1.04 - amount * 0.35)
        if not drip:
            return sp
        dv = self.mapping(self.tc.outputs["Object"], scale=(40.0 / scale, 40.0 / scale, 2.0 / scale), loc=(seed * 2, 0, 0))
        dr = self.ramp(self.noisev(dv, 1.0, 2.0, 0.5), 0.66 - amount * 0.1, 0.72 - amount * 0.1)
        dm = self.ramp(self.noisev(self.mapping(self.tc.outputs["Object"], loc=(seed + 3, 1, 0)), 3.0 / scale, 2.0), 0.55 - amount * 0.15, 0.62 - amount * 0.15)
        return self.math("MAXIMUM", sp, self.mul(dr, dm))


def define(key, group, color, tex=None, tex_size=0.4, contrast=1.0, rough=0.7, rough_var=0.15, metal=0.0,
           bump=0.6, bump_dist=0.003, dirt=0.6, dirt_col="#0e0b09", ao_shade=0.6, wear=0.0, wear_col=None,
           rust=0.0, rust_col="#4a2e20", stain=0.0, stain_col="#3a2418", stain_scale=1.0, stain_z=None,
           weave=None, hammer=None, scratch=0.0, wrinkle=0.0, wrinkle_stretch=(1.0, 1.0, 4.0), veins=0.0, scars=0.0,
           ink=None, light=None, dark=None, seed=0.0, rings=None, grain=0.0, sheen=0.0, U=1.2):
    """color／light／dark：spec 的 hex。回傳 BK.SRC 相容的 dict。"""
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    g = G(m)
    N, L = g.N, g.L
    out = N.new("ShaderNodeOutputMaterial")
    C = lin(color)
    d = dict(mat=m, group=group, out=out, key=key, tint=C, emit=None, emit_strength=1.0)
    BK.SRC[key] = d
    # ---- 明暗變化（0~2，平均 1）
    if tex:
        tc = g.image(tex, "Color", tex_size, cs="sRGB", offs=(0.13 + seed, 0.37, 0.21))
        lum = g.lum(tc)
        var = g.math("POWER", g.math("DIVIDE", lum, tex_mean(tex)), contrast)
        h_img = g.image(tex, "Displacement", tex_size, offs=(0.13 + seed, 0.37, 0.21)) or lum
        r_img = g.image(tex, "Roughness", tex_size, offs=(0.13 + seed, 0.37, 0.21))
    else:
        var = g.math("ADD", 0.85, g.mul(g.noisev(g.tc.outputs["Object"], 8.0, 4.0), 0.3))
        h_img = g.noisev(g.tc.outputs["Object"], 60.0, 4.0)
        r_img = None
    big = g.noisev(g.mapping(g.tc.outputs["Object"], loc=(seed * 3, 1, 2)), 2.2 / U, 3.0)
    var = g.mul(var, g.math("ADD", 0.8, g.mul(big, 0.4)))
    col = g.mix(1.0, (1, 1, 1), C, "MIX")
    col = g.mix(1.0, col, g.comb(var, var, var), "MULTIPLY")
    if light and dark:
        # 用大尺度雜訊在 dark↔light 之間擺動（色相變化，不只是明暗）
        t = g.ramp(g.noisev(g.mapping(g.tc.outputs["Object"], loc=(seed, 4, 0)), 5.0 / U, 4.0), 0.3, 0.7)
        cl = g.mix(t, lin(dark), lin(light))
        col = g.mix(0.45, col, g.mix(1.0, cl, g.comb(var, var, var), "MULTIPLY"))
    rsock = g.math("ADD", rough, 0.0)
    if r_img is not None:
        rsock = g.math("ADD", g.mul(g.math("SUBTRACT", r_img, 0.5), rough_var * 2), rough, clamp=True)
    msock = g.math("ADD", metal, 0.0)
    hsock = g.mul(h_img, 0.35)
    cav = g.math("SUBTRACT", 1.0, g.ao(0.05 * U), clamp=True)
    aofar = g.ao(0.30 * U)
    # ---- 粗麻平織
    if weave:
        pitch, wamp = weave
        wh, wshade, wgap = g.weave(pitch)
        col = g.mix(1.0, col, g.comb(*([g.math("ADD", 0.85, g.mul(wshade, 0.3))] * 3)), "MULTIPLY")
        col = g.mix(g.mul(wgap, 0.45), col, lin("#1a140e"))
        col = g.mix(1.0, col, g.comb(*([g.math("ADD", 0.80, g.mul(wh, 0.28))] * 3)), "MULTIPLY")
        hsock = g.add(g.mul(hsock, 0.4), g.mul(wh, wamp))
        rsock = g.mixf(wgap, rsock, 1.0)
    # ---- 錘紋
    if hammer:
        cell, hamp = hammer
        hh = g.hammer(cell, seed)
        hsock = g.add(hsock, g.mul(hh, hamp))
        col = g.mix(1.0, col, g.comb(*([g.math("ADD", 0.78, g.mul(hh, 0.3))] * 3)), "MULTIPLY")
    # ---- 皺褶
    if wrinkle > 0:
        wr, ridge = g.wrinkles(1.0, wrinkle_stretch, seed)
        hsock = g.add(hsock, g.mul(wr, wrinkle))
        col = g.mix(g.mul(ridge, 0.35), col, g.mix(1.0, col, (0.55, 0.55, 0.55), "MULTIPLY"))
    # ---- 青筋、疤
    if veins > 0:
        vn = g.veins(1.0, seed)
        hsock = g.add(hsock, g.mul(vn, veins))
        col = g.mix(g.mul(vn, 0.35), col, lin("#5a4048"))
    if scars > 0:
        sc_ = g.scars(1.0, seed)
        hsock = g.add(hsock, g.mul(sc_, scars))
        col = g.mix(g.mul(sc_, 0.8), col, lin("#8e6a5c"))
    # ---- 鏽（積在凹處）
    if rust > 0:
        n1 = g.noise(5.0 / U, 8, 0.65, seed)
        rm = g.ramp(g.add(g.mul(n1, 0.7), g.mul(cav, 0.9 * rust + 0.2)), 0.85 - 0.35 * rust, 1.0 - 0.35 * rust)
        rc = g.image("Rust009", "Color", 0.4, cs="sRGB", offs=(0.4, 0.1, 0.7))
        rl = g.math("DIVIDE", g.lum(rc), tex_mean("Rust009"))
        rcol = g.mix(1.0, g.mix(1.0, (1, 1, 1), lin(rust_col)), g.comb(rl, rl, rl), "MULTIPLY")
        col = g.mix(rm, col, rcol)
        rsock = g.mixf(rm, rsock, 0.88)
        msock = g.mixf(rm, msock, 0.15)
        rh = g.image("Rust009", "Displacement", 0.4, offs=(0.4, 0.1, 0.7))
        hsock = g.add(hsock, g.mul(rm, g.mul(rh, 0.5)))
    # ---- 刮痕（亮金屬／淺色刮擦）
    if scratch > 0:
        s = g.scratches(scratch, 1.0, seed)
        col = g.mix(g.mul(s, 0.85), col, lin(wear_col or "#6e6a64"))
        rsock = g.mixf(s, rsock, g.mul(rsock, 0.55))
        hsock = g.math("SUBTRACT", hsock, g.mul(s, 0.25))
    # ---- 邊緣磨亮
    if wear > 0:
        e = g.mul(g.edge(0.005 * U), 16.0, clamp=True)
        e = g.mul(e, g.ramp(g.noise(22.0 / U, 5, 0.7, seed + 7), 0.25, 0.6))
        e = g.mul(e, wear, clamp=True)
        col = g.mix(e, col, lin(wear_col or "#6e6a64"))
        rsock = g.mixf(e, rsock, g.mul(rsock, 0.5))
    # ---- 污漬
    if stain > 0:
        st = g.splatter(stain, stain_scale, seed + 11)
        if stain_z:
            z0, z1 = stain_z
            st = g.mul(st, g.inv(g.ramp(g.zcoord(), z0, z1)))
            st = g.math("MAXIMUM", st, g.mul(g.inv(g.ramp(g.zcoord(), z0 - (z1 - z0) * 0.6, z1)), 0.55))
        col = g.mix(g.mul(st, 0.85), col, lin(stain_col))
        rsock = g.mixf(st, rsock, 0.75)
        msock = g.mixf(st, msock, 0.0)
        hsock = g.add(hsock, g.mul(st, 0.05))
    # ---- 墨影漸層（ink=(起點, 方向, 長度)：沿前臂從皮膚漸變到全黑）
    if ink:
        p0, dirv, ln = ink
        rel = g.vmath("SUBTRACT", g.tc.outputs["Object"], tuple(p0))
        t = g.math("DIVIDE", g.vmath("DOT_PRODUCT", rel, tuple(dirv)), ln)
        streak = g.noisev(g.mapping(g.tc.outputs["Object"], scale=(30.0, 30.0, 3.0)), 1.0, 3.0, 0.6)
        tt = g.add(t, g.mul(g.math("SUBTRACT", streak, 0.5), 0.9))
        mk = g.ramp(tt, 0.05, 0.75)
        col = g.mix(mk, col, lin("#0b0a0f"))
        rsock = g.mixf(mk, rsock, 0.9)
        hsock = g.mul(hsock, g.inv(g.mul(mk, 0.7)))
    # ---- 金環刻紋
    if rings:
        wv = N.new("ShaderNodeTexWave"); wv.wave_type = "RINGS"; wv.inputs["Scale"].default_value = rings
        wv.inputs["Distortion"].default_value = 0.5
        L.new(g.tc.outputs["Object"], wv.inputs["Vector"])
        r = g.ramp(wv.outputs["Fac"], 0.75, 0.95)
        hsock = g.math("SUBTRACT", hsock, g.mul(r, 0.5))
        col = g.mix(g.mul(r, 0.7), col, lin("#8a6a2a"))
    # ---- 凹處積垢
    if dirt > 0:
        dm = g.mul(g.math("POWER", cav, 1.2), dirt, clamp=True)
        col = g.mix(dm, col, lin(dirt_col))
        rsock = g.mixf(dm, rsock, 0.95)
        msock = g.mul(msock, g.inv(g.mul(dm, 0.7)))
    # ---- 環境遮蔽烘入
    shade = g.mixf(ao_shade, 1.0, aofar)
    mulc = N.new("ShaderNodeVectorMath"); mulc.operation = "SCALE"
    L.new(col, mulc.inputs[0]); L.new(shade, mulc.inputs["Scale"])
    colout = mulc.outputs[0]
    bmp = N.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump; bmp.inputs["Distance"].default_value = bump_dist * U
    L.new(hsock, bmp.inputs["Height"])
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    L.new(colout, bsdf.inputs["Base Color"]); L.new(rsock, bsdf.inputs["Roughness"]); L.new(msock, bsdf.inputs["Metallic"])
    L.new(bmp.outputs[0], bsdf.inputs["Normal"])
    emC = N.new("ShaderNodeEmission"); L.new(colout, emC.inputs[0])
    cmb = N.new("ShaderNodeCombineColor")
    L.new(aofar, cmb.inputs[0]); L.new(rsock, cmb.inputs[1]); L.new(msock, cmb.inputs[2])
    emO = N.new("ShaderNodeEmission"); L.new(cmb.outputs[0], emO.inputs[0])
    L.new(bsdf.outputs[0], out.inputs[0])
    tgt = N.new("ShaderNodeTexImage"); tgt.name = "BAKE_TARGET"
    d.update(emitC=emC, emitO=emO, bsdf=bsdf, target=tgt, rough=rough, metal=metal)
    return d
