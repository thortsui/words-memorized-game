"""v3 sentinel 來源材質（烘焙前）：CC0 掃描貼圖（acg_*）＋ Blender 程序化節點。
每個材質輸出 emitC（底色＋烘入的 AO）、emitO（AO／粗糙度／金屬度）、bsdf（含 bump 的法線），
登記到 v3_sentinel_bake.SRC，由 assemble() 烘成兩組 2048 圖集（A：甲冑＋斗笠＋手腳；B：布、皮、木、根、戟）。

座標：Object（＝rest 世界座標，公尺）用於鐵、鏽、苔、鎖子甲；UV "src"（建模時的公尺 UV，烘焙前先複製保存）
用於有方向性的材質：麻布經緯、木紋、樹皮縱紋、皮帶縫線。
規格色值見 art/v3/specs/boss_sentinel.md §2。"""
import bpy, math
import v3_sentinel_bake as BK
from v3_sentinel_bake import NG, tex_path, load_img

AVG = {"Metal024": 0.1976, "Rust009": 0.111, "Moss002": 0.1162, "Bark012": 0.2075, "Chainmail004": 0.1281,
       "Fabric030": 0.1115, "Leather026": 0.0097, "Wood066": 0.0513}


def lin(h):
    h = h.lstrip("#")
    o = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        o.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(o)


class G(NG):
    def __init__(self, mat, h):
        super().__init__(mat)
        self.h = h
        self._uv = None

    @property
    def obj(self):
        return self.tc.outputs["Object"]

    @property
    def uv(self):
        if self._uv is None:
            n = self.N.new("ShaderNodeUVMap"); n.uv_map = "src"
            self._uv = n.outputs["UV"]
        return self._uv

    def mapv(self, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
        m = self.N.new("ShaderNodeMapping")
        m.inputs["Scale"].default_value = scale
        m.inputs["Location"].default_value = loc
        m.inputs["Rotation"].default_value = rot
        self.L.new(vec, m.inputs["Vector"])
        return m.outputs[0]

    def img(self, asset, kind, vec, cs="Non-Color", box=False):
        p = tex_path(asset, kind)
        if not p:
            return None
        n = self.N.new("ShaderNodeTexImage")
        n.image = load_img(p, cs)
        if box:
            n.projection = "BOX"; n.projection_blend = 0.3
        self.L.new(vec, n.inputs[0])
        return n.outputs["Color"]

    def ibox(self, asset, kind, size, cs="Non-Color", offs=(0.13, 0.37, 0.21), rot=(0.3, 0.2, 0.5)):
        return self.img(asset, kind, self.mapv(self.obj, (1 / size,) * 3, offs, rot), cs, box=True)

    def vor(self, vec, scale, feature="F1", rand=1.0):
        n = self.N.new("ShaderNodeTexVoronoi")
        n.feature = feature
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rand
        self.L.new(vec, n.inputs["Vector"])
        return n

    def nz3(self, vec, scale, detail=4.0, rough=0.6, dist=0.0):
        n = self.N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = dist
        self.L.new(vec, n.inputs["Vector"])
        return n.outputs["Fac"]

    def sep(self, vec):
        s = self.N.new("ShaderNodeSeparateXYZ")
        self.L.new(vec, s.inputs[0])
        return s.outputs

    def norm(self, asset, col, hexs, amt=1.0):
        """把掃描貼圖的亮度起伏套到目標色（保留紋理、換掉原本的色相）。"""
        v = self.math("DIVIDE", self.lum(col), AVG[asset])
        v = self.mixf(amt, 1.0, self.math("MINIMUM", v, 2.6))
        return self.scale(lin(hexs), v)

    def scale(self, colr, s):
        n = self.N.new("ShaderNodeVectorMath"); n.operation = "SCALE"
        self.put(n.inputs[0], colr)
        self.L.new(s, n.inputs["Scale"]) if not isinstance(s, (int, float)) else setattr(n.inputs["Scale"], "default_value", s)
        return n.outputs[0]

    def sstep(self, x, lo, hi):
        return self.ramp(x, lo, hi)

    def inv(self, x):
        return self.math("SUBTRACT", 1.0, x, clamp=True)

    def mul(self, a, b, clamp=False):
        return self.math("MULTIPLY", a, b, clamp=clamp)

    def add(self, a, b, clamp=False):
        return self.math("ADD", a, b, clamp=clamp)

    def finish(self, key, group, col, rough, metal, height, bump=1.0, bump_dist=0.004, ao_shade=0.45, tint=(0.3, 0.3, 0.3)):
        N, L = self.N, self.L
        out = N.new("ShaderNodeOutputMaterial")
        aofar = self.ao(0.12 * self.h)
        shade = self.mixf(ao_shade, 1.0, aofar)
        colout = self.scale(col, shade)
        bmp = N.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump; bmp.inputs["Distance"].default_value = bump_dist
        L.new(height, bmp.inputs["Height"])
        bsdf = N.new("ShaderNodeBsdfPrincipled")
        L.new(colout, bsdf.inputs["Base Color"]); L.new(rough, bsdf.inputs["Roughness"]); L.new(metal, bsdf.inputs["Metallic"])
        L.new(bmp.outputs[0], bsdf.inputs["Normal"])
        emC = N.new("ShaderNodeEmission"); L.new(colout, emC.inputs[0])
        comb = N.new("ShaderNodeCombineColor")
        L.new(aofar, comb.inputs[0]); L.new(rough, comb.inputs[1]); L.new(metal, comb.inputs[2])
        emO = N.new("ShaderNodeEmission"); L.new(comb.outputs[0], emO.inputs[0])
        L.new(bsdf.outputs[0], out.inputs[0])
        tgt = N.new("ShaderNodeTexImage"); tgt.name = "BAKE_TARGET"
        d = dict(mat=self.nt.id_data if hasattr(self.nt, "id_data") else None, group=group, out=out, key=key, tint=tint, emit=None,
                 emit_strength=1.0, emitC=emC, emitO=emO, bsdf=bsdf, target=tgt)
        return d


def _new(key, h):
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    return m, G(m, h)


def _reg(m, d):
    d["mat"] = m
    BK.SRC[d["key"]] = d
    return d


# ---------------------------------------------------------------- 錘鍛板甲（含鏽、苔、刮痕、磨亮邊）
def plate(key, h, group="A", base="#463a31", rust="#573a2a", edge="#6e665c", rlo=0.5, rhi=0.75, metal=0.85,
          rust_amt=0.5, moss_amt=0.15, moss="#3a3d26", dent=1.0, scratch=1.0, rings=None, flake=None, flake_amt=0.4,
          mud=None, mud_col="#2a2620", seed=0.0, hammer=0.012, streak=1.0, bump=1.0, edge_amt=1.0, tex_size=0.5, grime=0.8,
          grime_col="#32322c", blotch=0.0, edge_attr=False, cool=0.35):
    m, g = _new(key, h)
    o = g.mapv(g.obj, (1, 1, 1), (seed * 1.7, seed * 0.3, seed * 2.1))
    mc = g.ibox("Metal024", "Color", tex_size * h * 0.4, cs="sRGB", offs=(seed * 0.3, 0.37, 0.21))
    # 槍鐵：底色往冷灰拉（金屬度 0.85 時 albedo 就是反射色，暖色會讀成銅）
    bl = lin(base); gy = sum(bl) / 3
    base_c = tuple(c * (1 - cool) + gy * cool * 1.02 for c in bl)
    col = g.scale(base_c, g.mixf(0.55, 1.0, g.math("MINIMUM", g.math("DIVIDE", g.lum(mc), AVG["Metal024"]), 2.6)))
    big = g.nz3(o, 2.2 / h, 3, 0.5)
    col = g.scale(col, g.add(0.78, g.mul(big, 0.44)))
    rgh = g.mixf(g.nz3(o, 9 / h, 4, 0.6), rlo, rhi)
    met = g.add(metal, 0.0)
    # 高度：錘痕（密的淺碟）＋大凹痕＋旋壓紋
    hv = g.vor(o, 1.0 / (hammer * h))
    hgt = g.mul(g.math("POWER", hv.outputs["Distance"], 2.0), 0.42 * dent)
    mdisp = g.ibox("Metal024", "Displacement", tex_size * h * 0.4, offs=(seed * 0.3, 0.37, 0.21))
    hgt = g.add(hgt, g.mul(mdisp, 0.25))
    bd = g.vor(g.mapv(o, (1, 1, 1), (3.1, 1.2, seed)), 1.0 / (0.06 * h))
    bsel = g.sstep(g.sep(bd.outputs["Color"])[0], 0.80, 0.84)
    bdent = g.mul(bsel, g.inv(g.sstep(bd.outputs["Distance"], 0.0, 0.42)))
    hgt = g.math("SUBTRACT", hgt, g.mul(bdent, 0.9 * dent))
    if rings:
        c, period = rings
        w = g.N.new("ShaderNodeTexWave"); w.wave_type = "RINGS"; w.rings_direction = "SPHERICAL"
        w.inputs["Scale"].default_value = 1.0; w.inputs["Distortion"].default_value = 0.8
        w.inputs["Detail"].default_value = 1.0
        sc = 0.31416 / period
        g.L.new(g.mapv(g.obj, (sc, sc, sc), (-c[0] * sc, -c[1] * sc, -0.95 * h * sc)), w.inputs["Vector"])
        hgt = g.add(hgt, g.mul(w.outputs["Fac"], 0.22))
    # 刮痕：兩個方向的細長雜訊取 0.5 等高線，稀疏化
    scr = None
    for k, (sc, rot) in enumerate((((1.0, 1.0, 0.06), (0.4, 0.9, 0.2)), ((0.07, 1.0, 1.0), (1.1, 0.3, 0.7)))):
        n = g.nz3(g.mapv(o, (sc[0] / (0.03 * h), sc[1] / (0.03 * h), sc[2] / (0.03 * h)), (k * 4.1, seed, 1.3 * k), rot), 1.0, 2, 0.5)
        ln = g.inv(g.sstep(g.math("ABSOLUTE", g.math("SUBTRACT", n, 0.5)), 0.0, 0.012))
        sp = g.sstep(g.nz3(o, 3.0 / h, 2, 0.5), 0.56, 0.62)
        s1 = g.mul(ln, sp)
        scr = s1 if scr is None else g.math("MAXIMUM", scr, s1)
    scr = g.mul(scr, scratch, clamp=True)
    hgt = g.math("SUBTRACT", hgt, g.mul(scr, 0.25))
    cav = g.inv(g.ao(0.035 * h))
    cavs = g.inv(g.ao(0.010 * h, 12))         # 細縫（鉚釘周圍、疊片縫）
    cavf = g.inv(g.ao(0.12 * h))
    edg = g.mul(g.math("MULTIPLY", g.edge(0.004 * h), 12.0, clamp=True), g.sstep(g.nz3(o, 14 / h, 3, 0.6), 0.32, 0.6))
    edg = g.mul(edg, edge_amt, clamp=True)
    # 金帶剝落：露出底下的鐵
    if flake:
        fm = g.sstep(g.add(g.nz3(o, 26 / h, 5, 0.7), g.mul(edg, 0.2)), 0.62 - flake_amt * 0.25, 0.66 - flake_amt * 0.25)
        col = g.mix(fm, col, lin(flake))
        rgh = g.mixf(fm, rgh, 0.7)
        hgt = g.math("SUBTRACT", hgt, g.mul(fm, 0.25))
    # 凹處積垢
    col = g.mix(g.mul(g.math("POWER", cav, 1.2), 0.75, clamp=True), col, g.scale(col, 0.45))
    # 舊鐵的灰暗污膜（非金屬、粗糙）：讓鐵讀成「髒的槍鐵灰」而不是亮銅
    gn = g.add(g.mul(g.nz3(g.mapv(o, (1, 1, 1), (seed * 2.3, 1, 0)), 4.5 / h, 5, 0.65), 0.8), g.mul(cavf, 0.55))
    gm = g.mul(g.sstep(gn, 0.42, 0.70), grime)
    col = g.mix(gm, col, g.scale(lin(grime_col), g.add(0.8, g.mul(g.nz3(o, 30 / h, 3, 0.6), 0.4))))
    met = g.mixf(gm, met, 0.08); rgh = g.mixf(gm, rgh, 0.88)
    # 磨亮邊、刮痕亮線
    col = g.mix(edg, col, lin(edge)); rgh = g.mixf(edg, rgh, 0.35)
    col = g.mix(g.mul(scr, 0.8), col, g.scale(lin(edge), 0.9)); rgh = g.mixf(scr, rgh, 0.4)
    if edge_attr:                            # 戟刃刃口亮線（幾何屬性 edgew：0 脊 → 1 刃口）
        at = g.N.new("ShaderNodeAttribute"); at.attribute_name = "edgew"
        el = g.sstep(at.outputs["Fac"], 0.86, 0.97)
        col = g.mix(el, col, g.scale(lin(edge), 1.35)); rgh = g.mixf(el, rgh, 0.28); met = g.mixf(el, met, 0.95)
    # 鏽：只在縫隙、邊、流痕
    if rust_amt > 0:
        n1 = g.nz3(o, 18 / h, 6, 0.7)
        stn = g.nz3(g.mapv(o, (1 / (0.012 * h), 1 / (0.012 * h), 1 / (0.20 * h)), (seed, 0, 0)), 1.0, 3, 0.5)
        stk = g.mul(g.sstep(stn, 0.56, 0.72), g.sstep(cavf, 0.08, 0.35))
        r = g.add(g.add(g.mul(cavs, 1.6), g.mul(edg, 0.35)), g.mul(stk, 0.6 * streak))
        lo = 0.85 - 0.40 * rust_amt
        rm = g.mul(g.sstep(r, lo, lo + 0.16), g.sstep(n1, 0.36, 0.52))
        if blotch > 0:                       # 戟刃：大片紅褐鏽斑
            bm_ = g.sstep(g.add(g.nz3(o, 9 / h, 5, 0.7), g.mul(g.nz3(o, 40 / h, 3, 0.6), 0.25)), 0.62 - blotch * 0.3, 0.68 - blotch * 0.3)
            rm = g.math("MAXIMUM", rm, bm_)
        rc = g.ibox("Rust009", "Color", 0.18 * h, cs="sRGB", offs=(0.4, 0.1, 0.7))
        rcol = g.norm("Rust009", rc, rust, 0.7)
        if edge_attr:
            rm = g.mul(rm, g.inv(el))
        col = g.mix(rm, col, rcol)
        rgh = g.mixf(rm, rgh, 0.88)
        met = g.mixf(rm, met, 0.05)
        rh = g.ibox("Rust009", "Displacement", 0.18 * h, offs=(0.4, 0.1, 0.7))
        hgt = g.mixf(g.mul(rm, 0.8), hgt, g.add(g.mul(rh, 0.9), g.mul(g.vor(o, 1 / (0.003 * h)).outputs["Distance"], 0.35)))
    # 苔：朝上＋縫隙
    if moss_amt > 0:
        up = g.math("MAXIMUM", g.nz(), 0.0)
        n3 = g.nz3(o, 16 / h, 6, 0.75, 0.6)
        nf = g.nz3(o, 70 / h, 4, 0.7)
        mm = g.add(g.add(g.mul(up, 0.35), g.mul(cavs, 1.5)), g.add(g.mul(cav, 0.5), g.mul(g.add(g.mul(n3, 0.7), g.mul(nf, 0.35)), 0.36)))
        lo = 1.45 - 0.62 * moss_amt
        mm = g.sstep(mm, lo, lo + 0.06)
        mcol = g.ibox("Moss002", "Color", 0.12 * h, cs="sRGB", offs=(0.2, 0.6, 0.1))
        col = g.mix(mm, col, g.norm("Moss002", mcol, moss, 0.8))
        rgh = g.mixf(mm, rgh, 0.95)
        met = g.mul(met, g.inv(mm))
        mh = g.ibox("Moss002", "Displacement", 0.12 * h, offs=(0.2, 0.6, 0.1))
        hgt = g.mixf(mm, hgt, g.add(g.mul(mh, 1.1), 0.45))
    if mud:
        z0, z1 = mud
        mz = g.mul(g.inv(g.sstep(g.sep(g.obj)[2], z0 * h, z1 * h)), g.add(0.45, g.mul(g.nz3(o, 12 / h, 4, 0.6), 0.8)), clamp=True)
        col = g.mix(mz, col, lin(mud_col)); rgh = g.mixf(mz, rgh, 0.9); met = g.mul(met, g.inv(g.mul(mz, 0.8)))
    d = g.finish(key, group, col, rgh, met, hgt, bump=bump, bump_dist=0.0045 * h / 2.4, tint=lin(base))
    return _reg(m, d)


# ---------------------------------------------------------------- 粗麻／亞麻（經緯可辨）
def linen(key, h, group="B", base="#33322a", dark="#22231a", mold="#2d3324", spacing=0.003, wet=(0.09, 0.30), rough=0.95,
          seed=0.0, bump=1.0, moss_amt=0.0, cav_dark=0.7):
    m, g = _new(key, h)
    uv = g.uv
    s = g.sep(uv)
    p = spacing * h
    k = 2 * math.pi / p
    # 粗細不勻的紗（slub）：座標加一點低頻扭曲
    dist = g.mul(g.nz3(g.mapv(uv, (1, 1, 1), (seed, 0, 0)), 1.0 / (0.05 * h), 2, 0.5), 0.5 * p)
    u = g.add(s[0], dist); v = g.add(s[1], g.mul(dist, 0.7))
    su = g.math("SINE", g.mul(u, k)); sv = g.math("SINE", g.mul(v, k))
    a = g.add(0.5, g.mul(g.math("ABSOLUTE", su), 0.5)); b = g.add(0.5, g.mul(g.math("ABSOLUTE", sv), 0.5))
    par = g.math("GREATER_THAN", g.mul(g.math("SINE", g.mul(u, k * 0.5)), g.math("SINE", g.mul(v, k * 0.5))), 0.0)
    weave = g.mixf(par, g.mul(b, g.math("ABSOLUTE", sv)), g.mul(a, g.math("ABSOLUTE", su)))
    fab = g.img("Fabric030", "Color", g.mapv(uv, (1 / (0.15 * h),) * 3), cs="sRGB")
    col = g.norm("Fabric030", fab, base, 0.5)
    col = g.scale(col, g.add(0.86, g.mul(weave, 0.22)))
    o = g.obj
    big = g.nz3(o, 3.0 / h, 4, 0.6)
    col = g.scale(col, g.add(0.8, g.mul(big, 0.4)))
    # 霉斑
    mm = g.sstep(g.nz3(g.mapv(o, (1, 1, 1), (seed, 2, 1)), 9 / h, 5, 0.7), 0.58, 0.66)
    col = g.mix(g.mul(mm, 0.75), col, lin(mold))
    # 下 1/3 泥水漬（深色往上滲，邊緣不規則）
    z = g.sep(o)[2]
    wz = g.add(z, g.mul(g.nz3(o, 6 / h, 4, 0.6), 0.10 * h))
    wm = g.inv(g.sstep(wz, wet[0] * h, wet[1] * h))
    col = g.mix(g.mul(wm, 0.85), col, lin(dark))
    cav = g.inv(g.ao(0.03 * h))
    col = g.mix(g.mul(cav, cav_dark, clamp=True), col, g.scale(lin(dark), 0.6))
    # 破邊纖維：邊緣淡一點
    e = g.math("MULTIPLY", g.edge(0.003 * h), 8.0, clamp=True)
    col = g.mix(g.mul(e, 0.5), col, g.scale(lin(base), 1.35))
    rgh = g.add(rough, g.mul(g.math("SUBTRACT", weave, 0.5), 0.06))
    rgh = g.mixf(wm, rgh, min(1.0, rough + 0.03))
    hgt = g.add(g.mul(weave, 0.45), g.mul(big, 0.6))
    fd = g.img("Fabric030", "Displacement", g.mapv(uv, (1 / (0.15 * h),) * 3))
    hgt = g.add(hgt, g.mul(fd, 0.3))
    if moss_amt > 0:
        up = g.math("MAXIMUM", g.nz(), 0.0)
        mm2 = g.sstep(g.add(g.add(g.mul(cav, 0.9), g.mul(up, 0.3)), g.mul(g.nz3(o, 7 / h, 6, 0.7), 0.6)), 1.3 - 0.6 * moss_amt, 1.4 - 0.6 * moss_amt)
        mcol = g.ibox("Moss002", "Color", 0.12 * h, cs="sRGB", offs=(0.2, 0.6, 0.1))
        col = g.mix(mm2, col, g.norm("Moss002", mcol, "#3a3d26", 0.8))
        hgt = g.mixf(mm2, hgt, g.add(g.mul(g.ibox("Moss002", "Displacement", 0.12 * h), 1.0), 0.5))
    met = g.add(0.0, 0.0)
    d = g.finish(key, group, col, rgh, met, hgt, bump=bump, bump_dist=0.0025 * h / 2.4, ao_shade=0.55, tint=lin(base))
    return _reg(m, d)


# ---------------------------------------------------------------- 皮革（龜裂＋邊緣縫線）
def leather(key, h, group="B", base="#3a2c22", stitch_rows=None, pitch=0.004, rough=0.75, seed=0.0):
    m, g = _new(key, h)
    o = g.obj
    lc = g.ibox("Leather026", "Color", 0.10 * h, cs="sRGB", offs=(seed, 0.2, 0.4))
    col = g.norm("Leather026", lc, base, 0.6)
    col = g.scale(col, g.add(0.75, g.mul(g.nz3(o, 5 / h, 4, 0.6), 0.5)))
    cr = g.vor(o, 1 / (0.010 * h), "DISTANCE_TO_EDGE")
    crack = g.inv(g.sstep(cr.outputs["Distance"], 0.0, 0.05))
    crack = g.mul(crack, g.sstep(g.nz3(o, 6 / h, 3, 0.6), 0.45, 0.6))
    ld = g.ibox("Leather026", "Displacement", 0.10 * h, offs=(seed, 0.2, 0.4))
    hgt = g.math("SUBTRACT", g.add(g.mul(ld, 0.6), 0.3), g.mul(crack, 0.45))
    col = g.mix(g.mul(crack, 0.6), col, g.scale(lin(base), 0.45))
    e = g.mul(g.math("MULTIPLY", g.edge(0.003 * h), 10.0, clamp=True), g.sstep(g.nz3(o, 20 / h, 3, 0.6), 0.4, 0.6))
    col = g.mix(g.mul(e, 0.6), col, g.scale(lin(base), 1.6))
    if stitch_rows:
        s = g.sep(g.uv)
        dash = g.sstep(g.math("SINE", g.mul(s[0], 2 * math.pi / (pitch * h))), 0.1, 0.5)
        rowm = None
        for vr in stitch_rows:
            r = g.inv(g.sstep(g.math("ABSOLUTE", g.math("SUBTRACT", s[1], vr)), 0.0006 * h, 0.0012 * h))
            rowm = r if rowm is None else g.math("MAXIMUM", rowm, r)
        st = g.mul(dash, rowm)
        groove = g.mul(rowm, 0.5)
        hgt = g.add(g.math("SUBTRACT", hgt, g.mul(groove, 0.5)), g.mul(st, 0.55))
        col = g.mix(st, col, lin("#5a4a36"))
    cav = g.inv(g.ao(0.02 * h))
    col = g.mix(g.mul(cav, 0.7, clamp=True), col, g.scale(lin(base), 0.4))
    rgh = g.add(rough, g.mul(crack, 0.1))
    d = g.finish(key, group, col, rgh, g.add(0.0, 0.0), hgt, bump=1.0, bump_dist=0.003 * h / 2.4, tint=lin(base))
    return _reg(m, d)


# ---------------------------------------------------------------- 鎖子甲
def mail(key, h, group="A", base="#2f2c28", rust="#4e3628", ring=0.004):
    m, g = _new(key, h)
    size = ring * h * 16
    c = g.ibox("Chainmail004", "Color", size, cs="sRGB")
    col = g.norm("Chainmail004", c, base, 1.0)
    hgt = g.ibox("Chainmail004", "Displacement", size)
    rg = g.ibox("Chainmail004", "Roughness", size)
    rgh = g.add(0.45, g.mul(rg, 0.3))
    cav = g.inv(g.ao(0.03 * h))
    rm = g.sstep(g.add(g.mul(cav, 1.0), g.mul(g.nz3(g.obj, 14 / h, 5, 0.6), 0.5)), 0.6, 0.8)
    col = g.mix(rm, col, lin(rust)); rgh = g.mixf(rm, rgh, 0.85)
    met = g.mixf(rm, 0.9, 0.3)
    col = g.scale(col, g.mixf(hgt, 0.25, 1.15))
    d = g.finish(key, group, col, rgh, met, hgt, bump=1.0, bump_dist=0.004 * h / 2.4, tint=lin(base))
    return _reg(m, d)


# ---------------------------------------------------------------- 濕腐朽木（木紋沿 UV v）
def wood(key, h, group="B", base="#4a4032", wet="#2e2a22", moss_amt=0.30, grain=0.35, rough=(0.8, 0.95), wet_z=None, seed=0.0,
         polish=None):
    m, g = _new(key, h)
    uv = g.mapv(g.uv, (1, 1, 1), (seed, seed * 0.37, 0), (0, 0, math.pi / 2))
    wv = g.mapv(uv, (1 / (grain * h),) * 3)
    wc = g.img("Wood066", "Color", wv, cs="sRGB")
    col = g.norm("Wood066", wc, base, 0.9)
    o = g.obj
    col = g.scale(col, g.add(0.8, g.mul(g.nz3(o, 4 / h, 3, 0.6), 0.4)))
    wd = g.img("Wood066", "Displacement", wv)
    # 乾裂：沿木紋拉長的雜訊取細等高線
    s = g.sep(g.uv)
    crn = g.nz3(g.mapv(g.uv, (1 / (0.004 * h), 1 / (0.09 * h), 1), (seed, 0, 0)), 1.0, 2, 0.5)
    crack = g.mul(g.inv(g.sstep(g.math("ABSOLUTE", g.math("SUBTRACT", crn, 0.5)), 0.0, 0.03)),
                  g.sstep(g.nz3(o, 5 / h, 2, 0.5), 0.5, 0.58))
    hgt = g.math("SUBTRACT", g.add(g.mul(wd, 0.9), g.mul(g.nz3(g.mapv(g.uv, (1 / (0.002 * h), 1 / (0.05 * h), 1)), 1.0, 3, 0.6), 0.4)),
                 g.mul(crack, 0.7))
    cav = g.inv(g.ao(0.03 * h))
    wm = g.mul(cav, 1.0, clamp=True)
    if wet_z:
        z = g.sep(o)[2]
        wm = g.math("MAXIMUM", wm, g.mul(g.inv(g.sstep(g.add(z, g.mul(g.nz3(o, 5 / h, 3, 0.6), 0.08 * h)), wet_z[0] * h, wet_z[1] * h)), 0.8))
    col = g.mix(wm, col, lin(wet))
    col = g.mix(g.mul(crack, 0.85), col, g.scale(lin(wet), 0.5))
    rgh = g.mixf(g.nz3(o, 10 / h, 3, 0.6), rough[0], rough[1])
    if polish:
        c, rad = polish
        dn = g.N.new("ShaderNodeVectorMath"); dn.operation = "DISTANCE"
        g.L.new(o, dn.inputs[0]); dn.inputs[1].default_value = c
        pm = g.inv(g.sstep(dn.outputs["Value"], rad * 0.6, rad))
        rgh = g.mixf(pm, rgh, 0.6)
        col = g.mix(g.mul(pm, 0.5), col, g.scale(lin(base), 1.25))
    if moss_amt > 0:
        up = g.math("MAXIMUM", g.nz(), 0.0)
        z = g.sep(o)[2]
        low = g.inv(g.sstep(z, 0.30 * h, 0.45 * h)) if wet_z else g.add(0.0, 0.0)
        mm = g.add(g.add(g.mul(cav, 1.1), g.mul(low, 0.35)), g.add(g.mul(up, 0.25), g.mul(g.nz3(o, 7 / h, 6, 0.7, 0.3), 0.6)))
        lo = 1.30 - 0.70 * moss_amt
        mm = g.sstep(mm, lo, lo + 0.1)
        mcol = g.ibox("Moss002", "Color", 0.12 * h, cs="sRGB", offs=(0.2, 0.6, 0.1))
        col = g.mix(mm, col, g.norm("Moss002", mcol, "#3a3d26", 0.8))
        rgh = g.mixf(mm, rgh, 0.95)
        hgt = g.mixf(mm, hgt, g.add(g.mul(g.ibox("Moss002", "Displacement", 0.12 * h, offs=(0.2, 0.6, 0.1)), 1.1), 0.5))
    d = g.finish(key, group, col, rgh, g.add(0.0, 0.0), hgt, bump=1.0, bump_dist=0.004 * h / 2.4, tint=lin(base))
    return _reg(m, d)


# ---------------------------------------------------------------- 樹皮（根鬚；紋路沿 UV v）
def bark(key, h, group="B", base="#3b2a1e", dry="#4a3d30", tip=None, moss_amt=0.12, seed=0.0, contrast=0.0):
    m, g = _new(key, h)
    bv = g.mapv(g.uv, (1 / (0.06 * h), 1 / (0.12 * h), 1), (seed, 0, 0))
    bc = g.img("Bark012", "Color", bv, cs="sRGB")
    col = g.norm("Bark012", bc, base, 0.9)
    o = g.obj
    dm = g.sstep(g.nz3(o, 6 / h, 4, 0.6), 0.5, 0.7)
    col = g.mix(dm, col, g.norm("Bark012", bc, dry, 0.9))
    bd = g.img("Bark012", "Displacement", bv)
    knot = g.vor(o, 1 / (0.03 * h))
    kn = g.mul(g.inv(g.sstep(knot.outputs["Distance"], 0.0, 0.18)), g.sstep(g.sep(knot.outputs["Color"])[1], 0.82, 0.86))
    hgt = g.add(g.mul(bd, 1.0), g.mul(kn, 0.5))
    if contrast > 0:                     # 樹皮深溝：依高度把溝底壓暗、脊上提亮（albedo 看得到縱紋）
        col = g.scale(col, g.mixf(g.sstep(bd, 0.15, 0.75), 0.35, 1.0 + 0.35 * contrast))
        hgt = g.add(hgt, g.mul(g.nz3(g.mapv(g.uv, (1 / (0.006 * h), 1 / (0.08 * h), 1)), 1.0, 3, 0.6), 0.6))
    cav = g.inv(g.ao(0.02 * h))
    col = g.mix(g.mul(cav, 0.6, clamp=True), col, g.scale(lin(base), 0.4))
    if moss_amt > 0:
        up = g.math("MAXIMUM", g.nz(), 0.0)
        mm = g.sstep(g.add(g.mul(up, 0.5), g.mul(g.nz3(o, 8 / h, 5, 0.7), 0.8)), 1.15 - 0.5 * moss_amt, 1.22 - 0.5 * moss_amt)
        mcol = g.ibox("Moss002", "Color", 0.12 * h, cs="sRGB", offs=(0.2, 0.6, 0.1))
        col = g.mix(mm, col, g.norm("Moss002", mcol, "#3a3d26", 0.8))
        hgt = g.mixf(mm, hgt, g.add(g.mul(g.ibox("Moss002", "Displacement", 0.12 * h), 1.0), 0.5))
    rgh = g.add(0.90 if contrast else 0.88, g.mul(bd, 0.08))
    d = g.finish(key, group, col, rgh, g.add(0.0, 0.0), hgt, bump=1.0, bump_dist=(0.010 if contrast else 0.005) * h / 2.4, tint=lin(base))
    return _reg(m, d)


# ---------------------------------------------------------------- 濕苔條（垂掛）
def moss_strip(key, h, group="B", base="#2f3a22"):
    m, g = _new(key, h)
    mc = g.ibox("Moss002", "Color", 0.08 * h, cs="sRGB")
    col = g.norm("Moss002", mc, base, 0.9)
    hgt = g.ibox("Moss002", "Displacement", 0.08 * h)
    d = g.finish(key, group, col, g.add(0.92, 0.0), g.add(0.0, 0.0), hgt, bump=1.0, bump_dist=0.004 * h / 2.4, tint=lin(base))
    return _reg(m, d)


def flat(key, h, group, colhex, rough=0.95, metal=0.0, noise=0.0):
    m, g = _new(key, h)
    col = lin(colhex)
    hgt = g.nz3(g.obj, 40 / h, 3, 0.6)
    c = g.scale(col, g.add(1.0 - noise, g.mul(hgt, 2 * noise))) if noise else g.mix(0.0, col, col)
    d = g.finish(key, group, c, g.add(rough, 0.0), g.add(metal, 0.0), hgt, bump=0.3, bump_dist=0.002, ao_shade=0.6, tint=col)
    return _reg(m, d)
