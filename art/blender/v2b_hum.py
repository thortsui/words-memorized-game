"""建模 B（v2）共用：人形 Boss 的組裝／烘焙／型態部件（P2_／P3_）分離／匯出／GLB 後處理。
只 import 共用 lib（soul_humanoid_*），不修改它們。

型態部件做法：
  1. 建模時把部件標記 mark(ob, "P2_Xxx", bone)；烘焙前整批往 +X 平移 OFF（避免它們在本體上烘出 AO 陰影）。
  2. assemble2() 依材質組別合併、烘焙；Glow（G 組）與墨影（T 組）各自保留具名材質（名稱含 Glow 的才算發光）。
  3. split_parts() 把標記的頂點分離成獨立物件、移回原位、原點設在部件中心、剛體掛到骨頭（parent_type=BONE）。
  4. 匯出後 hide_parts_glb() 把 GLB 內 P2_／P3_ 節點的 scale 改成 0（遊戲端在 PhaseShift 爆發時彈出）。
"""
import bpy, bmesh, os, math, json, struct
from mathutils import Vector, Matrix
import soul_humanoid_bake as BK

OFF = Vector((30.0, 0.0, 0.0))


def define_ink(key, color=(0.02, 0.012, 0.03), alpha=0.82, emit=(0.30, 0.12, 0.55), emit_strength=0.25, final=None):
    """墨影材質（半透明黑紫，不烘焙）。"""
    m = bpy.data.materials.new("src_" + key)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Roughness"].default_value = 0.9
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
    """把分件標記成型態部件 name（之後分離成獨立物件）。"""
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


def _final_glow(d):
    gm = bpy.data.materials.new(d["final"])
    gm.use_nodes = True
    nt = gm.node_tree
    gb = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (*d.get("base", (0.02, 0.01, 0.03)), 1)
    gb.inputs["Emission Color"].default_value = (*d["emit"], 1)
    gb.inputs["Emission Strength"].default_value = d["emit_strength"]
    gb.inputs["Roughness"].default_value = 0.7
    if d.get("tex"):
        im = bpy.data.images.load(d["tex"], check_existing=True)
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = im
        im.pack()
        nt.links.new(ti.outputs[0], gb.inputs["Emission Color"])
    if d.get("alpha"):
        gb.inputs["Alpha"].default_value = d["alpha"]
        _blend(gm)
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
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Emission Color"].default_value = (*d["emit"], 1)
    b.inputs["Emission Strength"].default_value = d["emit_strength"]
    _blend(m)
    m.use_backface_culling = False
    return m


def assemble2(B, model, size=(2048, 2048), bake=True, samples=24, quick=False, detail_of=None, U=1.0):
    """BK.assemble 的變體：A／B 組烘焙成圖集；G（發光）與 T（墨影）組每個來源材質各自一個具名最終材質。"""
    sc = bpy.context.scene
    BK.polish(B)
    os.makedirs(BK.BAKED, exist_ok=True)
    # 標記：頂點群組（分離用）
    for ob in B.parts:
        pm = ob.get("pmark")
        if pm:
            g = ob.vertex_groups.new(name="__mk_" + pm)
            g.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
    groups = {}
    for ob in B.parts:
        d = BK.SRC[ob["matkey"]]
        ob.data.materials.append(d["mat"])
        groups.setdefault(d["group"], []).append(ob)
    joined = {gk: BK._join(groups[gk], f"{model}_{gk}") for gk in sorted(groups)}
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
    for k in ("G", "T"):
        if k in joined:
            joined[k].hide_render = True
    bk = [k for k in sorted(joined) if k not in ("G", "T")]
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
            sc.render.bake.cage_extrusion = 0.012 * U
            sc.render.bake.max_ray_distance = 0.04 * U
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
                qb.inputs["Base Color"].default_value = (min(1, t[0] * 1.4), min(1, t[1] * 1.4), min(1, t[2] * 1.4), 1)
                qb.inputs["Roughness"].default_value = 0.6
                s.material = qm
        finals.append(ob)
    for gk in ("G", "T"):
        if gk not in joined:
            continue
        ob = joined[gk]
        ob.hide_render = False
        cache = {}
        for s in ob.material_slots:
            d = BK.SRC[s.material.name[4:]]
            if d["final"] not in cache:
                cache[d["final"]] = _final_glow(d) if gk == "G" else _final_ink(d)
            s.material = cache[d["final"]]
        finals.append(ob)
    mesh = BK._join(finals, model + "_mesh")
    # 合併相同的材質槽
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


def split_parts(mesh, arm, bone_of):
    """把 __mk_<名稱> 群組分離成獨立剛體物件，掛到 bone_of[名稱] 骨頭。回傳 {名稱: 物件}。"""
    out = {}
    names = [g.name[5:] for g in mesh.vertex_groups if g.name.startswith("__mk_")]
    for nm in names:
        gi = mesh.vertex_groups["__mk_" + nm].index
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
        part = [o for o in bpy.context.selected_objects if o != mesh][0]
        part.name = nm
        part.data.name = nm
        for g in list(part.vertex_groups):
            part.vertex_groups.remove(g)
        for md in list(part.modifiers):
            part.modifiers.remove(md)
        # 移回原位（若有偏移）
        me = part.data
        cx = sum((v.co.x for v in me.vertices)) / max(1, len(me.vertices))
        if cx > OFF.x * 0.5:
            for v in me.vertices:
                v.co -= OFF
        # 原點設在部件中心
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


def add_rigid(name, obj, arm, bone):
    """直接建立的剛體部件（世界座標網格）掛到骨頭。"""
    me = obj.data
    c = sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
    for v in me.vertices:
        v.co -= c
    obj.matrix_world = Matrix.Translation(c)
    bpy.context.view_layer.update()
    mw = obj.matrix_world.copy()
    obj.parent = arm; obj.parent_type = "BONE"; obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = mw
    obj.name = name
    return obj


def export_glb(arm, objs, path, jpeg_quality=88):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for o in objs:
        o.hide_set(False); o.hide_render = False
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


def show_parts(parts, on, prefix=None):
    for n, o in parts.items():
        if prefix and not n.startswith(prefix):
            continue
        o.hide_render = not on
        o.hide_viewport = not on


# ---------------------------------------------------------------- 預覽（自訂打光：暗場、側逆光，接近遊戲）
def render_still(cam, az, tgt, dist, path, elev=0.0, lens=70, res=None):
    sc = bpy.context.scene
    if res:
        sc.render.resolution_x, sc.render.resolution_y = res
    BK.aim(cam, az, tgt, dist, elev=elev, lens=lens)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def set_rest(arm):
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.scene.frame_set(1)


# ---------------------------------------------------------------- GLB 後處理
def _read_glb(path):
    data = open(path, "rb").read()
    clen, ctype = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + clen])
    rest = data[20 + clen:]
    return js, rest


def _write_glb(path, js, rest):
    j = json.dumps(js, separators=(",", ":")).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    total = 12 + 8 + len(j) + len(rest)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(j), 0x4E4F534A))
        f.write(j)
        f.write(rest)


def hide_parts_glb(path, prefixes=("P2_", "P3_")):
    js, rest = _read_glb(path)
    n = 0
    for nd in js["nodes"]:
        if any((nd.get("name") or "").startswith(p) for p in prefixes):
            nd["scale"] = [0.0, 0.0, 0.0]
            n += 1
    _write_glb(path, js, rest)
    return n


def glb_info(path):
    js, rest = _read_glb(path)
    acc = js["accessors"]
    tris = sum(acc[p["indices"]]["count"] // 3 for m in js["meshes"] for p in m["primitives"])
    pn = [(nd["name"], nd.get("scale")) for nd in js["nodes"] if (nd.get("name") or "").startswith(("P2_", "P3_"))]
    return dict(tris=tris, mb=os.path.getsize(path) / 1048576, mats=[m["name"] for m in js["materials"]], parts=pn,
                anims=[a["name"] for a in js.get("animations", [])])
