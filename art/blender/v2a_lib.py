"""建模 A（v2）共用工具：P2 型態部件、分開的 Glow 材質、匯出、預覽。不修改共用 lib，只在其上包一層。
- P2 部件：建模時 tag_p2(objs, 名稱, 骨頭, 支點) → 合併烘焙後 split_p2() 拆成獨立網格、以「剛體」掛在骨頭上
  （遊戲端 phaseShow.js 會在爆發那一格 scale 0→1.08→1 彈出）。匯出後由 v2a_post.py 把 P2_* 節點 scale 設 0 並寫 extras。
- Glow 材質：每種發光各自一個材質（名稱含 Glow），不經過烘焙。
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

P2_PREFIX = "__P2__"
SPEC = {}   # P2 名稱 -> (骨頭, 支點)
GLOW = {}   # 材質名 -> (顏色, 強度)


def lin(hexstr):
    """#rrggbb → 線性 RGB。"""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def glow_mat(name, color, strength):
    """建立發光材質（名稱必須含 Glow）。color 可為 hex 或線性 tuple。"""
    assert "Glow" in name
    if isinstance(color, str):
        color = lin(color)
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (color[0] * 0.15, color[1] * 0.15, color[2] * 0.15, 1)
    b.inputs["Emission Color"].default_value = (*color, 1)
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Roughness"].default_value = 0.55
    GLOW[name] = (color, strength)
    return m


def tag_p2(obs, name, bone, pivot):
    """把零件標成二階部件 P2_<name>（剛體掛在 bone 上，pivot＝彈出縮放的中心）。"""
    if not isinstance(obs, (list, tuple)):
        obs = [obs]
    for o in obs:
        if o is None:
            continue
        g = o.vertex_groups.get(P2_PREFIX + name) or o.vertex_groups.new(name=P2_PREFIX + name)
        g.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
        o["p2"] = name
    SPEC[name] = (bone, Vector(pivot))
    return obs


def pull_glow(B):
    """從 Builder 的零件中取出 Glow 材質的零件（不參與烘焙），回傳清單。"""
    gl = [o for o in B.parts if o["matkey"] in GLOW]
    for o in gl:
        B.parts.remove(o)
        o.data.materials.clear()
        o.data.materials.append(bpy.data.materials[o["matkey"]])
    return gl


def join_into(mesh, objs):
    if not objs:
        return mesh
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    return mesh


def split_p2(mesh, arm):
    """把 __P2__* 頂點群組的面拆成獨立物件，剛體掛到骨頭上（骨架必須在靜止姿勢）。回傳物件清單。"""
    out = []
    for name, (bone, piv) in SPEC.items():
        g = mesh.vertex_groups.get(P2_PREFIX + name)
        if g is None:
            print("WARN P2 沒有找到", name)
            continue
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        mesh.vertex_groups.active_index = g.index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
        new = [o for o in bpy.context.selected_objects if o != mesh]
        mesh.vertex_groups.remove(mesh.vertex_groups[P2_PREFIX + name])
        if not new:
            print("WARN P2 拆分失敗", name)
            continue
        ob = new[0]
        ob.name = "P2_" + name
        ob.data.name = "P2_" + name
        ob.vertex_groups.clear()
        for md in list(ob.modifiers):
            ob.modifiers.remove(md)
        used = sorted({p.material_index for p in ob.data.polygons})
        ob.parent = None
        ob.matrix_world = Matrix()
        ob.data.transform(Matrix.Translation(-piv))
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = bone
        bpy.context.view_layer.update()
        ob.matrix_world = Matrix.Translation(piv)
        ob["p2form"] = 2
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print(f"P2 {ob.name} -> {bone} tris={tris} mats={[ob.material_slots[i].material.name for i in used]}", flush=True)
        out.append(ob)
    for g in list(mesh.vertex_groups):
        if g.name.startswith(P2_PREFIX):
            mesh.vertex_groups.remove(g)
    return out


def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


def export_glb(arm, objs, path, jpeg_quality=88):
    for o in bpy.data.objects:
        o.select_set(False)
    arm.select_set(True)
    for o in objs:
        o.hide_render = False
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.scene.frame_set(0)
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_animations=True,
              export_animation_mode="NLA_TRACKS", export_yup=True, export_skins=True, export_image_format="JPEG",
              export_force_sampling=True, export_optimize_animation_size=True, export_tangents=False, export_def_bones=False)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties
    if "export_image_quality" in props:
        kw["export_image_quality"] = jpeg_quality
    if "export_jpeg_quality" in props:
        kw["export_jpeg_quality"] = jpeg_quality
    bpy.ops.export_scene.gltf(**kw)
    print(f"EXPORT {path} {os.path.getsize(path) / 1048576:.2f} MB", flush=True)


def show_p2(objs, on):
    for o in objs:
        o.hide_render = not on


def render_actions(arm, H, tiles_dir, cam, p2objs, n=8, res=(400, 400), az=-32, only=None, width=2.15, p2_from=None,
                   aggro=("IdleAggro",), tgt=None, elev=0.22):
    """每個片段取 n 格；P2 部件在 aggro 片段顯示，PhaseShift 從 p2_from（秒）起顯示。"""
    from soul_humanoid_bake import aim
    sc = bpy.context.scene
    os.makedirs(tiles_dir, exist_ok=True)
    sc.render.resolution_x, sc.render.resolution_y = res
    try:
        sc.eevee.taa_render_samples = 12
    except Exception:
        pass
    aim(cam, az, tgt or Vector((0, -H * 0.12, H * 0.50)), H * width, elev=H * elev, lens=50)
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
            on = name in aggro or (name == "PhaseShift" and p2_from is not None and f >= p2_from * 30)
            show_p2(p2objs, on)
            sc.frame_set(f)
            sc.render.filepath = os.path.join(tiles_dir, f"act_{r:02d}_{name}_{k}_f{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    ad.action = None
    show_p2(p2objs, False)
