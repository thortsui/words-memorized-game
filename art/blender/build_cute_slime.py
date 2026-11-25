"""回合制模式的可愛史萊姆（綠／冰晶／魔王）。
用法：blender --background --python build_cute_slime.py -- <variant> <out.glb> <preview.png> <out.blend>
造型依據：art/reference/cute_monster_lineup.jpg
朝向：臉朝 -Y（匯出 glTF 後為 +Z）。動作：Idle、Enter、Attack、Hit、Faint、Victory。
"""
import bpy, bmesh, math, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
VARIANT, OUT_GLB, OUT_PNG, OUT_BLEND = argv[0], argv[1], argv[2], argv[3]

CFG = {
    "green": dict(color=(0.16, 0.72, 0.18), dark=(0.05, 0.38, 0.08), size=1.0, mood="happy"),
    "ice":   dict(color=(0.55, 0.80, 0.97), dark=(0.25, 0.50, 0.80), size=1.12, mood="angry"),
    "king":  dict(color=(0.86, 0.10, 0.10), dark=(0.50, 0.03, 0.05), size=1.75, mood="smug"),
}[VARIANT]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30


def mat(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=1.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    return m


M_BODY = mat("SlimeBody", CFG["color"], rough=0.12, emit=CFG["dark"], emit_strength=0.12)
M_SHINE = mat("Shine", (1, 1, 1), rough=0.05, emit=(1, 1, 1), emit_strength=0.9)
M_WHITE = mat("EyeWhite", (1, 1, 1), rough=0.25)
M_PUPIL = mat("Pupil", (0.03, 0.05, 0.04) if VARIANT != "king" else (0.25, 0.06, 0.03), rough=0.15)
M_MOUTH = mat("Mouth", (0.35, 0.03, 0.05), rough=0.6)
M_TONGUE = mat("Tongue", (0.95, 0.42, 0.48), rough=0.5)
M_LEAF = mat("Leaf", (0.20, 0.62, 0.12), rough=0.5)
M_STEM = mat("Stem", (0.30, 0.50, 0.10), rough=0.6)
M_ICE = mat("IceSpike", (0.80, 0.93, 1.0), rough=0.08, emit=(0.3, 0.6, 1.0), emit_strength=0.3)
M_GOLD = mat("Gold", (1.0, 0.72, 0.12), rough=0.25, metal=1.0)
M_GEM_R = mat("GemRed", (0.9, 0.05, 0.15), rough=0.05, emit=(0.9, 0.05, 0.15), emit_strength=0.6)
M_GEM_B = mat("GemBlue", (0.1, 0.3, 0.95), rough=0.05, emit=(0.1, 0.3, 0.95), emit_strength=0.6)
M_CAPE = mat("Cape", (0.75, 0.05, 0.08), rough=0.7)
M_BLUSH = mat("Blush", (1.0, 0.45, 0.5), rough=0.8, alpha=0.55)

S = CFG["size"]
H = 0.86 * S  # 身高
W = 0.60 * S  # 半徑


def profile_radius(t):
    """t: 0(底)~1(頂) 的輪廓半徑（正規化）。底部外擴成裙邊，頂端圓。"""
    dome = math.sqrt(max(0.0, 1 - (max(t - 0.22, 0) / 0.78) ** 2.0))
    skirt = 1.0 + 0.05 * math.exp(-(t / 0.10) ** 2)
    base = min(1.0, (t / 0.05) ** 0.5) if t < 0.05 else 1.0
    return dome * skirt * (0.80 + 0.20 * base)


def make_body():
    bm = bmesh.new()
    rings, segs = 40, 56
    cols = []
    for i in range(rings):
        t = i / rings
        r = profile_radius(t) * W
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            wob = 1 + 0.025 * math.sin(3 * a + 1.0) * (1 - t) + 0.02 * math.sin(5 * a) * (1 - t) ** 2
            ring.append(bm.verts.new((math.cos(a) * r * wob, math.sin(a) * r * wob * 0.94, t * H)))
        cols.append(ring)
    apex = bm.verts.new((0, 0, H))
    for i in range(rings - 1):
        for j in range(segs):
            bm.faces.new((cols[i][j], cols[i][(j + 1) % segs], cols[i + 1][(j + 1) % segs], cols[i + 1][j]))
    for j in range(segs):
        bm.faces.new((cols[-1][j], cols[-1][(j + 1) % segs], apex))
    bm.faces.new(list(reversed(cols[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("SlimeBody")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("SlimeBody", me)
    scene.collection.objects.link(ob)
    ob.data.materials.append(M_BODY)
    return ob


def surf(theta_deg, t, push=0.0):
    """身體表面上的點：theta 0 = 正前方(-Y)，正值往 +X。"""
    a = math.radians(theta_deg)
    r = profile_radius(t) * W + push
    return Vector((math.sin(a) * r, -math.cos(a) * r * 0.94, t * H))


def ellipsoid(name, loc, scale, material, rot=(0, 0, 0), segs=24, rings=14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(material)
    return ob


def cone(name, loc, r, h, material, rot=(0, 0, 0), verts=10):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0, depth=h, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    return ob


def face_rot(theta_deg):
    return (0, 0, math.radians(theta_deg))


body = make_body()
parts_body, parts_top = [], []

eye_t, eye_th = 0.50, 21
mood = CFG["mood"]
for sgn in (-1, 1):
    e = ellipsoid(f"EyeWhite{sgn}", surf(sgn * eye_th, eye_t, -0.03 * S), (0.115 * S, 0.06 * S, 0.14 * S), M_WHITE, rot=face_rot(sgn * eye_th))
    pu = ellipsoid(f"Pupil{sgn}", surf(sgn * (eye_th - 2), eye_t - 0.005, 0.012 * S), (0.062 * S, 0.035 * S, 0.085 * S), M_PUPIL, rot=face_rot(sgn * eye_th))
    gl = ellipsoid(f"Glint{sgn}", surf(sgn * (eye_th - 2) + 3, eye_t + 0.045, 0.04 * S), (0.022 * S, 0.014 * S, 0.026 * S), M_SHINE, rot=face_rot(sgn * eye_th), segs=12, rings=8)
    bl = ellipsoid(f"Blush{sgn}", surf(sgn * 38, eye_t - 0.15, 0.004 * S), (0.07 * S, 0.012 * S, 0.04 * S), M_BLUSH, rot=face_rot(sgn * 38), segs=12, rings=8)
    parts_body += [e, pu, gl, bl]
    if mood in ("angry", "smug"):
        tilt = (-0.45 if mood == "angry" else 0.22) * sgn
        br = ellipsoid(f"Brow{sgn}", surf(sgn * eye_th, eye_t + 0.16, 0.02 * S), (0.10 * S, 0.02 * S, 0.022 * S), M_PUPIL, rot=(0, tilt, math.radians(sgn * eye_th)), segs=12, rings=8)
        parts_body.append(br)

if mood == "happy":
    parts_body.append(ellipsoid("Mouth", surf(0, 0.29, -0.012 * S), (0.125 * S, 0.02 * S, 0.10 * S), M_MOUTH, rot=(math.radians(-8), 0, 0)))
    parts_body.append(ellipsoid("Tongue", surf(0, 0.235, -0.002 * S), (0.075 * S, 0.018 * S, 0.042 * S), M_TONGUE, rot=(math.radians(-8), 0, 0)))
else:
    n = 9
    for k in range(n):
        u = k / (n - 1) * 2 - 1
        up = (u * u * 0.05) if mood == "smug" else (-u * u * 0.04)
        parts_body.append(ellipsoid(f"Mouth{k}", surf(u * 15, 0.31 + up, 0.006 * S), (0.022 * S, 0.014 * S, 0.016 * S), M_MOUTH, segs=10, rings=6))

for th, t, sx, sz in ((-38, 0.80, 0.085, 0.05), (-50, 0.68, 0.035, 0.03)):
    parts_body.append(ellipsoid("Shine", surf(th, t, 0.004 * S), (sx * S, 0.008 * S, sz * S), M_SHINE, rot=(math.radians(-35), 0, math.radians(th)), segs=14, rings=8))

top = Vector((0, 0, H))
if VARIANT == "green":
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.018 * S, depth=0.16 * S, location=top + Vector((0, 0, 0.06 * S)))
    stem = bpy.context.object
    stem.name = "Stem"
    stem.data.materials.append(M_STEM)
    parts_top.append(stem)
    for sgn in (-1, 1):
        parts_top.append(ellipsoid(f"Leaf{sgn}", top + Vector((sgn * 0.085 * S, 0, 0.175 * S)), (0.095 * S, 0.05 * S, 0.02 * S), M_LEAF, rot=(0, -sgn * 0.5, 0), segs=16, rings=10))
elif VARIANT == "ice":
    spikes = [(0, 0.999, 0.30, 0)] + [(th, 0.80, 0.22, 40) for th in range(0, 360, 60)] + [(th, 0.52, 0.17, 78) for th in (75, 130, 180, 230, 285)]
    for th, t, h, lean in spikes:
        p = surf(th, t, 0)
        a = math.radians(th)
        l = math.radians(lean)
        d = Vector((math.sin(a) * math.sin(l), -math.cos(a) * math.sin(l), math.cos(l)))
        c = cone("Spike", p + d * (h * S * 0.38), 0.075 * S, h * S, M_ICE, rot=d.to_track_quat("Z", "Y").to_euler(), verts=6)
        (parts_top if t > 0.7 else parts_body).append(c)
elif VARIANT == "king":
    cz = H * 0.985
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.20 * S, depth=0.09 * S, location=(0, 0, cz + 0.03 * S))
    band = bpy.context.object
    band.name = "CrownBand"
    band.data.materials.append(M_GOLD)
    bpy.ops.object.shade_smooth()
    parts_top.append(band)
    for k in range(5):
        a = 2 * math.pi * k / 5
        px, py = math.sin(a) * 0.18 * S, -math.cos(a) * 0.18 * S
        parts_top.append(cone("CrownPoint", (px, py, cz + 0.14 * S), 0.065 * S, 0.17 * S, M_GOLD, verts=8))
        parts_top.append(ellipsoid("CrownBall", (px, py, cz + 0.235 * S), (0.026 * S,) * 3, M_GOLD, segs=10, rings=6))
        parts_top.append(ellipsoid("CrownGem", (math.sin(a) * 0.205 * S, -math.cos(a) * 0.205 * S, cz + 0.035 * S), (0.028 * S, 0.028 * S, 0.034 * S), M_GEM_R if k == 0 else M_GEM_B, segs=10, rings=6))
    bm = bmesh.new()
    segs, rows, grid = 18, 8, []
    for i in range(rows + 1):
        t = 0.62 - i / rows * 0.60
        row = []
        for j in range(segs + 1):
            th = 95 + (j / segs) * 170
            flare = 0.04 + (i / rows) ** 1.4 * 0.20 + 0.012 * math.sin(j * 1.7) * (i / rows)
            row.append(bm.verts.new(surf(th, max(t, 0.02), flare * S)))
        grid.append(row)
    for i in range(rows):
        for j in range(segs):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Cape")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    cape = bpy.data.objects.new("Cape", me)
    scene.collection.objects.link(cape)
    cape.data.materials.append(M_CAPE)
    sol = cape.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.02 * S
    parts_body.append(cape)

# 骨架
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.object
arm.name = f"Slime_{VARIANT}"
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
root = eb[0]
root.name = "Root"
root.head = (0, 0, 0)
root.tail = (0, 0, 0.15 * S)
bb = eb.new("Body")
bb.head = (0, 0, 0)
bb.tail = (0, 0, 0.5 * H)
bb.parent = root
tb = eb.new("Top")
tb.head = (0, 0, 0.5 * H)
tb.tail = (0, 0, H)
tb.parent = bb
for b in (root, bb, tb):
    b.roll = 0
bpy.ops.object.mode_set(mode="OBJECT")


def bake(objs):
    for o in objs:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def tag(objs, group):
    for o in objs:
        vg = o.vertex_groups.new(name=group)
        vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")


bake([body] + parts_body + parts_top)
gb = body.vertex_groups.new(name="Body")
gt = body.vertex_groups.new(name="Top")
for v in body.data.vertices:
    t = v.co.z / H
    w = min(1.0, max(0.0, (t - 0.30) / 0.60))
    w = w * w * (3 - 2 * w)
    gt.add([v.index], w, "REPLACE")
    gb.add([v.index], 1 - w, "REPLACE")
tag(parts_body, "Body")
tag(parts_top, "Top")
bpy.ops.object.select_all(action="DESELECT")
for o in [body] + parts_body + parts_top:
    o.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
mesh = bpy.context.object
mesh.name = f"SlimeMesh_{VARIANT}"
mod = mesh.modifiers.new("Armature", "ARMATURE")
mod.object = arm
mesh.parent = arm

# 動作
P = arm.pose.bones
ML = {n: arm.data.bones[n].matrix_local.to_3x3().inverted() for n in ("Root", "Body", "Top")}


def w2b(bone, v):
    return ML[bone] @ Vector(v)


def action(name, keys, length):
    """keys: {bone: [(frame, 世界座標位移|None, 高度倍率|None, 世界軸旋轉|None)]}；寬度依體積守恆自動算。"""
    if not arm.animation_data:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    for bn in ("Root", "Body", "Top"):
        pb = P[bn]
        pb.rotation_mode = "XYZ"
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
        pb.rotation_euler = (0, 0, 0)
    for bn, ks in keys.items():
        pb = P[bn]
        for f, loc, sq, rot in ks:
            if loc is not None:
                pb.location = w2b(bn, loc)
                pb.keyframe_insert("location", frame=f)
            if sq is not None:
                wd = (1 / sq) ** 0.5
                pb.scale = (wd, sq, wd)
                pb.keyframe_insert("scale", frame=f)
            if rot is not None:
                r = w2b(bn, rot)
                pb.rotation_euler = (r.x, r.y, r.z)
                pb.keyframe_insert("rotation_euler", frame=f)
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    tr.mute = True
    arm.animation_data.action = None
    return act


Z = (0, 0, 0)
action("Idle", {
    "Body": [(1, None, 1.0, None), (11, None, 0.90, None), (22, None, 1.06, None), (31, None, 0.97, None), (41, None, 1.0, None)],
    "Top": [(1, Z, None, Z), (11, (0.02 * S, 0, 0), None, (0, 0.05, 0)), (22, Z, None, Z), (31, (-0.02 * S, 0, 0), None, (0, -0.05, 0)), (41, Z, None, Z)],
}, 41)
action("Enter", {
    "Root": [(1, (0, 0, 3.2 * S), None, None), (10, Z, None, None), (16, (0, 0, 0.35 * S), None, None), (22, Z, None, None), (30, Z, None, None)],
    "Body": [(1, None, 1.25, None), (9, None, 1.3, None), (11, None, 0.55, None), (16, None, 1.15, None), (22, None, 0.8, None), (26, None, 1.05, None), (30, None, 1.0, None)],
}, 30)
action("Attack", {
    "Root": [(1, Z, None, Z), (8, (0, 0.18 * S, 0), None, Z), (14, (0, -0.9 * S, 0.7 * S), None, (-0.5, 0, 0)), (19, (0, -1.7 * S, 0.05 * S), None, (0.25, 0, 0)), (23, (0, -1.6 * S, 0), None, Z), (32, (0, -0.4 * S, 0.45 * S), None, Z), (38, Z, None, Z), (42, Z, None, Z)],
    "Body": [(1, None, 1.0, None), (8, None, 0.6, None), (13, None, 1.35, None), (19, None, 1.2, None), (21, None, 0.55, None), (26, None, 1.1, None), (32, None, 1.1, None), (38, None, 0.8, None), (42, None, 1.0, None)],
}, 42)
action("Hit", {
    "Root": [(1, Z, None, Z), (3, (0, 0.35 * S, 0.1 * S), None, (0.35, 0, 0)), (8, (0.06 * S, 0.2 * S, 0), None, (0.1, 0, 0.1)), (12, (-0.05 * S, 0.1 * S, 0), None, (0, 0, -0.08)), (18, Z, None, Z)],
    "Body": [(1, None, 1.0, None), (3, None, 0.72, None), (8, None, 1.15, None), (12, None, 0.93, None), (18, None, 1.0, None)],
}, 18)
action("Faint", {
    "Root": [(1, Z, None, Z), (6, (0, 0.2 * S, 0.5 * S), None, (0.3, 0, 0)), (14, (0, 0.3 * S, 0), None, Z), (36, (0, 0.3 * S, 0), None, Z)],
    "Body": [(1, None, 1.0, None), (6, None, 1.2, None), (14, None, 0.45, None), (20, None, 0.6, None), (36, None, 0.16, None)],
    "Top": [(1, Z, None, Z), (20, Z, None, (0, 0.5, 0)), (36, Z, None, (0, 1.1, 0))],
}, 36)
action("Victory", {
    "Root": [(1, Z, None, Z), (8, (0, 0, 0.6 * S), None, Z), (14, Z, None, Z), (22, (0, 0, 0.6 * S), None, (0, 0, 3.1416)), (28, Z, None, (0, 0, 6.2832)), (34, Z, None, (0, 0, 6.2832))],
    "Body": [(1, None, 0.7, None), (8, None, 1.25, None), (14, None, 0.7, None), (22, None, 1.25, None), (28, None, 0.7, None), (34, None, 1.0, None)],
}, 34)

bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True, export_animations=True,
                          export_animation_mode="NLA_TRACKS", export_yup=True, export_skins=True)

# 預覽圖
bpy.ops.object.light_add(type="SUN", location=(3, -4, 6))
sun = bpy.context.object
sun.data.energy = 2.2
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
bpy.ops.object.light_add(type="AREA", location=(-3 * S, -3 * S, 2 * S))
fill = bpy.context.object
fill.data.energy = 120 * S * S
fill.data.size = 4
fill.rotation_euler = (math.radians(65), 0, math.radians(-45))
bpy.ops.mesh.primitive_plane_add(size=40)
bpy.context.object.data.materials.append(mat("Ground", (0.93, 0.95, 0.9), rough=0.9))
w = bpy.data.worlds.new("W")
scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.92, 1.0, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.ops.object.camera_add(location=(1.9 * S, -3.6 * S, 1.25 * S))
cam = bpy.context.object
scene.camera = cam
d = Vector((0, 0, 0.55 * H)) - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
scene.render.resolution_x, scene.render.resolution_y = 900, 760
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "CYCLES"
scene.view_settings.view_transform = "Standard"
scene.render.filepath = OUT_PNG
scene.frame_set(1)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("DONE", VARIANT, "verts", len(mesh.data.vertices), "actions", [a.name for a in bpy.data.actions])
