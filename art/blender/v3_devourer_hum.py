"""v3 噬語魔王：組裝／烘焙／型態部件分離／匯出（由 v2b_hum.py 複製後大改；共用 lib 不動）。

和 v2b 的差別：
  - define_mat3()：BK.define_mat 的擴充版，多了
      pat    ：盒狀投影的浮雕高度圖（卷草紋）→ 凹處上暗色、凸處磨亮，並加進法線
      streak ：縱向墨流（從接縫往下流的條紋＋末端滴狀），濕亮黑墨（粗糙 0.3）
      crack  ：Voronoi 細裂紋（骨面、角）
      srcfn  ：以第二組 UV「src」（零件自己的長度座標）做的圖樣：角的環節紋＋米黃→黑尖漸層、劍面刮痕
  - 紙（P 組）：書頁不烘焙，直接用 4×2 書頁圖集（字跡、焦邊）＋法線，最終材質 Paper（粗糙 0.9、金屬 0）
  - X3_*：三階要消失的原部件，烘焙後拆成獨立的蒙皮網格（保留權重），phaseShow 在三階設 visible=false
  - P2_／P3_ 部件：剛體掛骨；可指定原點（例如光環原點放在頭骨，避免 scale 0 的點跑到角尖上方影響遊戲端的身高縮放）
"""
import bpy, bmesh, os, math, json, struct
from mathutils import Vector, Matrix
import soul_humanoid_bake as BK

OFF = Vector((30.0, 0.0, 0.0))
TEXV3 = None   # 由主腳本設定：art/v3/tmp/devourer/tex


def _img(path, cs):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = cs
    return im


def define_mat3(key, group="A", tex=None, size=0.5, tint=(1, 1, 1), sat=1.0, val=1.0, rough=None, rough_mul=1.0,
                metal=None, bump=0.4, bump_dist=0.004, rust=0.0, rust_size=0.45, rust_tint=(0.8, 0.75, 0.7), wear=0.0,
                wear_col=(0.60, 0.58, 0.55), dirt=0.5, dirt_col=(0.035, 0.03, 0.025), mud=None,
                mud_col=(0.16, 0.13, 0.10), ao_shade=0.6, U=1.0, color=None, seed=0.0,
                flat_rough=0.6, stain=0.0, stain_col=(0.12, 0.06, 0.04),
                pat=None, streak=None, crack=None, srcfn=None, weave=None, wear_r=0.006, hammer=None):
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    g = BK.NG(m)
    N, L = g.N, g.L
    out = N.new("ShaderNodeOutputMaterial")
    d = dict(mat=m, group=group, out=out, key=key, tint=tint, emit=None, emit_strength=1.0)
    BK.SRC[key] = d
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
    cav = g.math("SUBTRACT", 1.0, g.ao(0.05 * U), clamp=True)
    aofar = g.ao(0.30 * U)
    col = base
    # ---- 第二組 UV（src）的圖樣：回傳 (顏色, 高度, 粗糙度) 的覆寫
    if srcfn:
        uvn = N.new("ShaderNodeUVMap"); uvn.uv_map = "src"
        sp = N.new("ShaderNodeSeparateXYZ"); L.new(uvn.outputs[0], sp.inputs[0])
        r = srcfn(g, sp.outputs[0], sp.outputs[1], col, hsock, rsock)
        col, hsock, rsock = r
    # ---- 布紋（程序織紋：兩向正弦）
    if weave:
        sc_, depth = weave
        sx = N.new("ShaderNodeSeparateXYZ"); L.new(g.tc.outputs["Object"], sx.inputs[0])
        a = g.math("SINE", g.math("MULTIPLY", g.math("ADD", sx.outputs[0], sx.outputs[1]), sc_))
        b = g.math("SINE", g.math("MULTIPLY", sx.outputs[2], sc_))
        wv = g.math("MULTIPLY", g.math("ADD", g.math("ABSOLUTE", a), g.math("ABSOLUTE", b)), 0.5)
        hsock = g.math("ADD", g.math("MULTIPLY", hsock, 0.6), g.math("MULTIPLY", wv, depth))
        col = g.mix(g.math("MULTIPLY", g.math("SUBTRACT", 1.0, wv), 0.25), col, (0.0, 0.0, 0.0))
    # ---- 錘紋（Voronoi 淺凹坑）
    if hammer:
        sc_, dep = hammer
        vo = N.new("ShaderNodeTexVoronoi"); vo.feature = "F1"; vo.inputs["Scale"].default_value = sc_
        L.new(g.tc.outputs["Object"], vo.inputs["Vector"])
        dimple = g.math("POWER", g.math("MINIMUM", g.math("MULTIPLY", vo.outputs["Distance"], 2.2), 1.0), 0.6)
        hsock = g.math("ADD", g.math("MULTIPLY", hsock, 0.5), g.math("MULTIPLY", dimple, dep))
        col = g.mix(g.math("MULTIPLY", g.math("SUBTRACT", 1.0, dimple), 0.18), col, (0.0, 0.0, 0.0))
    # ---- 卷草浮雕
    if pat:
        if True:
            n = N.new("ShaderNodeTexImage"); n.image = _img(pat["img"], "Non-Color")
            n.projection = "BOX"; n.projection_blend = 0.3
            mp = N.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (1 / pat["size"],) * 3
            mp.inputs["Location"].default_value = (0.31, 0.17, 0.53)
            L.new(g.tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs[0], n.inputs[0])
            p = g.lum(n.outputs["Color"])
        raised = g.ramp(p, 0.35, 0.75)
        recess = g.math("SUBTRACT", 1.0, raised)
        col = g.mix(g.math("MULTIPLY", recess, pat.get("k", 0.75)), col, pat["recess"])
        top = g.ramp(p, 0.75, 0.98)
        col = g.mix(g.math("MULTIPLY", top, 0.30), col, pat["raised"])
        rsock = g.mixf(top, rsock, g.math("MULTIPLY", rsock, 0.6))
        hsock = g.math("ADD", g.math("MULTIPLY", hsock, 0.25), g.math("MULTIPLY", p, pat["depth"]))
    # ---- 裂紋
    if crack:
        sc_, wd, dep = crack
        vo = N.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"
        vo.inputs["Scale"].default_value = sc_
        L.new(g.tc.outputs["Object"], vo.inputs["Vector"])
        nz = g.noise(sc_ * 0.5, 4, 0.6, seed + 11)
        cr = g.math("SUBTRACT", 1.0, g.ramp(g.math("ADD", vo.outputs["Distance"], g.math("MULTIPLY", nz, wd * 1.5)), 0.0, wd))
        cr = g.math("MULTIPLY", cr, g.ramp(g.noise(3.0, 3, 0.5, seed + 13), 0.42, 0.6))
        col = g.mix(g.math("MULTIPLY", cr, 0.8), col, (0.05, 0.04, 0.03))
        hsock = g.math("SUBTRACT", hsock, g.math("MULTIPLY", cr, dep))
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
    if wear > 0:
        e = g.math("MULTIPLY", g.edge(wear_r * U), 14.0 * 0.006 / wear_r, clamp=True)
        e = g.math("MULTIPLY", e, g.ramp(n2, 0.30, 0.62))
        e = g.math("MULTIPLY", e, wear, clamp=True)
        col = g.mix(e, col, wear_col)
        rsock = g.mixf(e, rsock, 0.28)
    if stain > 0:
        sm = g.ramp(g.math("ADD", n1, g.math("MULTIPLY", n2, 0.3)), 0.95 - stain * 0.6, 1.15 - stain * 0.6)
        col = g.mix(g.math("MULTIPLY", sm, 0.8), col, stain_col)
    if dirt > 0:
        dm = g.math("MULTIPLY", g.math("POWER", cav, 1.3), dirt, clamp=True)
        col = g.mix(dm, col, dirt_col)
        rsock = g.mixf(dm, rsock, 0.92)
        msock = g.math("MULTIPLY", msock, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", dm, 0.8)))
    # ---- 墨流：縱向條紋（盒狀投影會在水平面上變成點，所以乘上「面朝側」）
    if streak:
        n = N.new("ShaderNodeTexImage"); n.image = _img(streak["img"], "Non-Color")
        n.projection = "BOX"; n.projection_blend = 0.2
        mp = N.new("ShaderNodeMapping")
        sz = streak["size"]
        mp.inputs["Scale"].default_value = (1 / sz, 1 / sz, 1 / (sz * 1.6))
        mp.inputs["Location"].default_value = (0.11, 0.47, 0.29)
        L.new(g.tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs[0], n.inputs[0])
        sm = g.lum(n.outputs["Color"])
        side = g.math("SUBTRACT", 1.0, g.math("ABSOLUTE", g.nz()), clamp=True)
        gate = g.ramp(g.math("ADD", g.noise(1.6 / U, 3, 0.5, seed + 31), g.math("MULTIPLY", cav, 0.35)), 1.0 - streak["amount"], 1.12 - streak["amount"])
        ink = g.math("MULTIPLY", g.math("MULTIPLY", g.ramp(sm, 0.25, 0.6), side), gate, clamp=True)
        col = g.mix(ink, col, streak["col"])
        rsock = g.mixf(ink, rsock, streak.get("rough", 0.3))
        msock = g.mixf(ink, msock, 0.0)
        hsock = g.math("ADD", hsock, g.math("MULTIPLY", ink, streak.get("depth", 0.25)))
    if mud:
        z0, z1, amt = mud
        mz = g.math("SUBTRACT", 1.0, g.ramp(g.zcoord(), z0, z1))
        mz = g.math("MULTIPLY", g.math("MULTIPLY", mz, g.math("ADD", 0.55, g.math("MULTIPLY", n1, 0.7))), amt, clamp=True)
        col = g.mix(mz, col, mud_col)
        rsock = g.mixf(mz, rsock, 0.95)
    shade = g.mixf(ao_shade, 1.0, aofar)
    colf = g.mix(1.0, col, (1, 1, 1), "MULTIPLY")
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


def define_paper(key="paper", tint=(1, 1, 1)):
    """書頁（P 組，不烘焙）：書頁圖集。"""
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    d = dict(mat=m, group="P", key=key, tint=(0.78, 0.70, 0.54), emit=None, emit_strength=1.0, final="Paper", ptint=tint)
    BK.SRC[key] = d
    return d


def _final_paper(d):
    fm = bpy.data.materials.new(d["final"])
    fm.use_nodes = True
    fm.use_backface_culling = False
    nt = fm.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    ic = nt.nodes.new("ShaderNodeTexImage"); ic.image = _img(os.path.join(TEXV3, "dv_pages_col.png"), "sRGB")
    inn = nt.nodes.new("ShaderNodeTexImage"); inn.image = _img(os.path.join(TEXV3, "dv_pages_nrm.png"), "Non-Color")
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.0
    nt.links.new(ic.outputs[0], b.inputs["Base Color"])
    nt.links.new(inn.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Metallic"].default_value = 0.0
    for n in (ic, inn):
        n.image.pack()
    return fm


def define_ink(key, color=(0.02, 0.012, 0.03), alpha=0.82, emit=(0.30, 0.12, 0.55), emit_strength=0.25, final=None):
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Alpha"].default_value = alpha
    d = dict(mat=m, group="T", key=key, tint=color, emit=emit, emit_strength=emit_strength, alpha=alpha, color=color,
             final=final or key)
    BK.SRC[key] = d
    return d


def define_glow(key, emit, strength=1.5, final=None, base=(0.02, 0.01, 0.03), tex=None):
    d = BK.define_mat(key, "G", emit=emit, emit_strength=strength)
    d["final"] = final or key
    d["base"] = base
    d["tex"] = tex
    return d


def mark(obs, name, offset=True):
    if not isinstance(obs, (list, tuple)):
        obs = [obs]
    for o in obs:
        if o is None:
            continue
        o["pmark"] = name
        if offset:
            for v in o.data.vertices:
                v.co += OFF
            o["poff"] = 1
    return obs


def xmark(obs, name):
    """三階要消失的原部件（烘焙時不偏移，之後拆成獨立蒙皮網格）。"""
    if not isinstance(obs, (list, tuple)):
        obs = [obs]
    for o in obs:
        if o is not None:
            o["xmark"] = name
    return obs


def src_uv(ob, B, fn=None):
    """第二組 UV「src」：預設複製 atlas UV（扣掉 Builder 的島嶼位移）；fn(co)->(x, y) 可自訂。"""
    me = ob.data
    at = me.uv_layers["atlas"]
    s = me.uv_layers.get("src") or me.uv_layers.new(name="src")
    du = getattr(B, "uv_slot", 0) * 20.0
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            if fn:
                s.data[li].uv = fn(me.vertices[vi].co)
            else:
                q = at.data[li].uv
                s.data[li].uv = (q.x - du, q.y)
    me.uv_layers.active = at
    at.active_render = True


def _final_glow(d):
    gm = bpy.data.materials.new(d["final"])
    gm.use_nodes = True
    nt = gm.node_tree
    gb = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (*d.get("base", (0.02, 0.01, 0.03)), 1)
    gb.inputs["Emission Color"].default_value = (*d["emit"], 1)
    gb.inputs["Emission Strength"].default_value = d["emit_strength"]
    gb.inputs["Roughness"].default_value = 0.7
    if d.get("tex"):          # 底色＝發光＝同一張貼圖（裂縫網：暗肉底＋熔紅裂縫）
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = _img(d["tex"], "sRGB"); ti.image.pack()
        nt.links.new(ti.outputs[0], gb.inputs["Base Color"])
        nt.links.new(ti.outputs[0], gb.inputs["Emission Color"])
        gb.inputs["Roughness"].default_value = 0.8
    gm.use_backface_culling = False
    return gm


def _blend(m):
    for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
        try:
            setattr(m, attr, val)
        except Exception:
            pass
    try:
        m.show_transparent_back = False
    except Exception:
        pass


def _final_ink(d):
    m = bpy.data.materials.new(d["final"])
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*d["color"], 1)
    b.inputs["Alpha"].default_value = d["alpha"]
    b.inputs["Roughness"].default_value = 0.92          # 霧面墨
    b.inputs["Specular IOR Level"].default_value = 0.15
    b.inputs["Emission Color"].default_value = (*d["emit"], 1)
    b.inputs["Emission Strength"].default_value = d["emit_strength"]
    if d["alpha"] < 0.999:
        _blend(m)
    m.use_backface_culling = False
    return m


def _ensure_atlas_active(ob):
    me = ob.data
    at = me.uv_layers.get("atlas")
    if at:
        me.uv_layers.active = at
        at.active_render = True


def assemble3(B, model, size=(2048, 2048), bake=True, samples=24, quick=False, detail_of=None, U=1.0):
    sc = bpy.context.scene
    BK.polish(B)
    os.makedirs(BK.BAKED, exist_ok=True)
    for ob in B.parts:
        for key, pre in (("pmark", "__mk_"), ("xmark", "__x3_")):
            pm = ob.get(key)
            if pm:
                g = ob.vertex_groups.new(name=pre + pm)
                g.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
        if "src" not in ob.data.uv_layers:
            ob.data.uv_layers.new(name="src")
        _ensure_atlas_active(ob)
    groups = {}
    for ob in B.parts:
        d = BK.SRC[ob["matkey"]]
        ob.data.materials.append(d["mat"])
        groups.setdefault(d["group"], []).append(ob)
    joined = {gk: BK._join(groups[gk], f"{model}_{gk}") for gk in sorted(groups)}
    for ob in joined.values():
        _ensure_atlas_active(ob)
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
    for k in ("G", "T", "P"):
        if k in joined:
            joined[k].hide_render = True
    bk = [k for k in sorted(joined) if k not in ("G", "T", "P")]
    for gi, gk in enumerate(bk):
        ob = joined[gk]
        sz = size[min(gi, len(size) - 1)]
        BK._pack_uv(ob)
        paths = {p: os.path.join(BK.BAKED, f"{model}_{gk}_{p}.png") for p in ("color", "orm", "normal")}
        if bake:
            imgs = {"color": BK._new_img(f"{model}_{gk}_color", sz, "sRGB"), "orm": BK._new_img(f"{model}_{gk}_orm", sz, "Non-Color"),
                    "normal": BK._new_img(f"{model}_{gk}_normal", sz, "Non-Color")}
            hi = BK.make_high(ob, detail_of, U) if detail_of else None
            bpy.ops.object.select_all(action="DESELECT")
            if hi:
                hi.select_set(True)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            sc.render.bake.use_selected_to_active = bool(hi)
            sc.render.bake.cage_extrusion = 0.010 * U
            sc.render.bake.max_ray_distance = 0.03 * U
            mats = [s.material for s in ob.material_slots]
            for p in ("color", "orm", "normal"):
                for m in mats:
                    d = next(v for v in BK.SRC.values() if v["mat"] == m)
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
                BK._save(imgs[p], paths[p])
                print("BAKED", model, gk, p, flush=True)
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
            for n in (ic, io, inn):
                n.image.pack()
            ob.data.materials.clear()
            ob.data.materials.append(fm)
        else:
            for s in ob.material_slots:
                d = next(v for v in BK.SRC.values() if v["mat"] == s.material)
                qm = bpy.data.materials.new("quick_" + d["key"])
                qm.use_nodes = True
                qb = next(n for n in qm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                t = d["tint"]
                qb.inputs["Base Color"].default_value = (min(1, t[0]), min(1, t[1]), min(1, t[2]), 1)
                qb.inputs["Roughness"].default_value = 0.6
                qb.inputs["Metallic"].default_value = d.get("qmetal", 0.0)
                s.material = qm
        finals.append(ob)
    for gk in ("G", "T", "P"):
        if gk not in joined:
            continue
        ob = joined[gk]
        ob.hide_render = False
        cache = {}
        for s in ob.material_slots:
            d = BK.SRC[s.material.name[4:]]
            if d["final"] not in cache:
                cache[d["final"]] = _final_glow(d) if gk == "G" else (_final_ink(d) if gk == "T" else _final_paper(d))
            s.material = cache[d["final"]]
        finals.append(ob)
    mesh = BK._join(finals, model + "_mesh")
    _ensure_atlas_active(mesh)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    try:
        bpy.ops.object.material_slot_remove_unused()
    except Exception:
        pass
    for im in list(bpy.data.images):
        if im.users == 0:
            bpy.data.images.remove(im)
    return mesh


def _separate_group(mesh, gname):
    gi = mesh.vertex_groups[gname].index
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(mesh.data)
    dl = bm.verts.layers.deform.active
    for v in bm.verts:
        v.select = bool(dl and gi in v[dl] and v[dl][gi] > 0.5)
    for e in bm.edges:
        e.select = all(v.select for v in e.verts)
    for f in bm.faces:
        f.select = all(v.select for v in f.verts)
    bmesh.update_edit_mesh(mesh.data)
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    return [o for o in bpy.context.selected_objects if o != mesh][0]


def split_parts(mesh, arm, bone_of, origin_of=None):
    """把 __mk_<名稱> 群組分離成獨立剛體物件，掛到骨頭。origin_of(名稱)->世界座標原點（None＝部件中心）。"""
    out = {}
    names = [g.name[5:] for g in mesh.vertex_groups if g.name.startswith("__mk_")]
    for nm in names:
        part = _separate_group(mesh, "__mk_" + nm)
        part.name = nm
        part.data.name = nm
        for g in list(part.vertex_groups):
            part.vertex_groups.remove(g)
        for md in list(part.modifiers):
            part.modifiers.remove(md)
        me = part.data
        cx = sum((v.co.x for v in me.vertices)) / max(1, len(me.vertices))
        if cx > OFF.x * 0.5:
            for v in me.vertices:
                v.co -= OFF
        c = (origin_of(nm) if origin_of else None)
        if c is None:
            c = sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
        for v in me.vertices:
            v.co -= c
        part.parent = None
        part.matrix_world = Matrix.Translation(c)
        bpy.context.view_layer.update()
        bn = bone_of(nm)
        mw = part.matrix_world.copy()
        part.parent = arm
        part.parent_type = "BONE"
        part.parent_bone = bn
        bpy.context.view_layer.update()
        part.matrix_world = mw
        bpy.context.view_layer.update()
        try:
            bpy.ops.object.select_all(action="DESELECT")
            part.select_set(True); bpy.context.view_layer.objects.active = part
            bpy.ops.object.material_slot_remove_unused()
        except Exception:
            pass
        out[nm] = part
        print("PART", nm, "->", bn, "tris", sum(len(p.vertices) - 2 for p in me.polygons), flush=True)
    for g in list(mesh.vertex_groups):
        if g.name.startswith("__mk_"):
            mesh.vertex_groups.remove(g)
    return out


def split_x3(mesh, arm):
    """__x3_<名稱> → 獨立蒙皮網格 X3_<名稱>（保留權重與骨架修改器）。在 BK.bind 之後呼叫。"""
    out = {}
    names = [g.name[5:] for g in mesh.vertex_groups if g.name.startswith("__x3_")]
    for nm in names:
        part = _separate_group(mesh, "__x3_" + nm)
        part.name = nm
        part.data.name = nm
        for g in list(part.vertex_groups):
            if g.name.startswith(("__x3_", "__mk_")):
                part.vertex_groups.remove(g)
        try:
            bpy.ops.object.select_all(action="DESELECT")
            part.select_set(True); bpy.context.view_layer.objects.active = part
            bpy.ops.object.material_slot_remove_unused()
        except Exception:
            pass
        out[nm] = part
        print("X3PART", nm, "tris", sum(len(p.vertices) - 2 for p in part.data.polygons), flush=True)
    for g in list(mesh.vertex_groups):
        if g.name.startswith("__x3_"):
            mesh.vertex_groups.remove(g)
    return out


def drop_src_uv(objs):
    for o in objs:
        if o.type != "MESH":
            continue
        s = o.data.uv_layers.get("src")
        if s:
            o.data.uv_layers.remove(s)
        _ensure_atlas_active(o)


def export_glb(arm, objs, path, jpeg_quality=88):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for o in objs:
        o.hide_set(False); o.hide_render = False; o.hide_viewport = False
        o.select_set(True)
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


def set_rest(arm):
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.scene.frame_set(1)
