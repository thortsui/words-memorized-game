"""v3 行刑者預覽：開 .blend，在 Idle 姿勢（有動作時）渲染與參考圖同視角的圖、特寫、P2、動作連拍。
用法：blender --background --factory-startup --python v3_executioner_preview.py -- <blend> <out_dir> [--views] [--close] [--p2] [--acts] [--rest]
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT = argv[0], argv[1]
FLAGS = set(argv[2:]) or {"--views", "--close", "--p2"}
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
parts = [o for o in bpy.data.objects if o.name.startswith("P2_")]
mesh = next(o for o in bpy.data.objects if o.name.endswith("_mesh"))
for o in bpy.data.objects:
    if o.type == "MESH" and o not in parts and o != mesh and not o.name.startswith("X2_"):
        o.hide_render = True
HT = 2.4

try:
    sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    sc.render.engine = "CYCLES"
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.034, 0.034, 0.032, 1); bg.inputs[1].default_value = 1.0


def area(loc, energy, size, color=(1, 1, 1), tgt=(0, 0, 1.2)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy = energy; l.data.size = size; l.data.color = color
    d = Vector(tgt) - l.location
    l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l


# 主光左上 45°（參考圖）、補光、背光
area((-3.2, -3.4, 4.6), 750, 3.0, (1.0, 0.93, 0.85))
area((3.6, -2.4, 1.6), 110, 4.0, (0.85, 0.85, 0.95))
area((1.5, 4.2, 3.8), 1100, 2.5, (0.9, 0.9, 1.0))
area((-3.5, 2.5, 1.2), 300, 3.0)
bpy.ops.mesh.primitive_plane_add(size=40)
gp = bpy.context.object
gm = bpy.data.materials.new("G"); gm.use_nodes = True
b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.012, 0.012, 0.011, 1); b.inputs["Roughness"].default_value = 1.0
gp.data.materials.append(gm)
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam


def pose(name="Idle", frac=0.5):
    ad = arm.animation_data
    if "--rest" in FLAGS or not ad or name not in bpy.data.actions:
        if ad:
            ad.action = None
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        sc.frame_set(1)
        return
    act = bpy.data.actions[name]
    ad.action = act
    f0, f1 = act.frame_range
    sc.frame_set(int(round(f0 + (f1 - f0) * frac)))


def shoot(path, az, tgt, ortho=None, dist=7.0, elev=0.0, lens=60, res=(720, 1000)):
    sc.render.resolution_x, sc.render.resolution_y = res
    a = math.radians(az)
    t = Vector(tgt)
    cam.location = Vector((math.sin(a) * dist, -math.cos(a) * dist, t.z + math.tan(math.radians(elev)) * dist))
    d = t - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


X2 = [o for o in bpy.data.objects if o.name.startswith("X2_")]


def show_p2(on):
    for o in parts:
        o.hide_render = not on
    for o in X2:
        o.hide_render = on


show_p2(False)
pose("Idle", 0.0)
mid = (0, -0.25, HT * 0.50)
if "--views" in FLAGS:
    for k, (lab, az) in enumerate((("threeq", -28), ("front", 0), ("side", -90), ("back", 180))):
        shoot(os.path.join(OUT, f"view_{k}_{lab}.png"), az, mid, ortho=HT * 1.18, elev=5, res=(820, 1000))
if "--p2" in FLAGS:
    show_p2(True)
    pose("IdleAggro", 0.0)
    shoot(os.path.join(OUT, "view_4_p2_threeq.png"), -28, (0, -0.1, HT * 0.55), ortho=HT * 1.35, elev=5, res=(820, 1000))
    shoot(os.path.join(OUT, "view_5_p2_back.png"), 150, (0, -0.1, HT * 0.55), ortho=HT * 1.35, elev=10, res=(820, 1000))
    shoot(os.path.join(OUT, "close_9_p2_head.png"), -20, None or (0.0, -0.1, HT * 0.85), ortho=HT * 0.32, elev=3, res=(800, 800))
    show_p2(False)
    pose("Idle", 0.0)
if "--close" in FLAGS:
    hb = arm.pose.bones["Head"]
    hp = arm.matrix_world @ hb.head
    shoot(os.path.join(OUT, "close_0_hood.png"), -22, (hp.x, hp.y, hp.z + HT * 0.08), ortho=HT * 0.30, elev=4, res=(800, 800))
    ub = arm.pose.bones["UpperArmL"]
    up = arm.matrix_world @ ((ub.head + arm.pose.bones["HandL"].head) * 0.5)
    shoot(os.path.join(OUT, "close_1_armL.png"), 60, (up.x, up.y, up.z), ortho=HT * 0.36, elev=5, res=(800, 800))
    ub = arm.pose.bones["UpperArmR"]
    up = arm.matrix_world @ ((ub.head + arm.pose.bones["HandR"].head) * 0.5)
    shoot(os.path.join(OUT, "close_2_armR.png"), -60, (up.x, up.y, up.z), ortho=HT * 0.36, elev=5, res=(800, 800))
    hip = arm.matrix_world @ arm.pose.bones["Hips"].head
    shoot(os.path.join(OUT, "close_3_waist.png"), -15, (hip.x, hip.y, hip.z), ortho=HT * 0.42, elev=6, res=(800, 800))
    tipo = bpy.data.objects.get("Tip_Weapon")
    tp = tipo.matrix_world.translation if tipo else Vector((0.5, -0.5, 1.4))
    shoot(os.path.join(OUT, "close_4_axe.png"), -40, (tp.x, tp.y, tp.z), ortho=HT * 0.34, elev=5, res=(800, 800))
    kp = arm.matrix_world @ arm.pose.bones["ShinL"].head
    shoot(os.path.join(OUT, "close_5_leg.png"), 30, (kp.x, kp.y, kp.z - 0.15), ortho=HT * 0.36, elev=5, res=(800, 800))
if "--acts" in FLAGS and arm.animation_data:
    sc.render.resolution_x, sc.render.resolution_y = 360, 400
    try:
        sc.eevee.taa_render_samples = 12
    except Exception:
        pass
    show_p2(False)
    for r, tr in enumerate(arm.animation_data.nla_tracks):
        name = tr.name
        act = bpy.data.actions[name]
        arm.animation_data.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        show_p2(name in ("IdleAggro", "PhaseShift"))
        n = 8
        for k in range(n):
            f = int(round(f0 + (f1 - f0) * k / (n - 1)))
            if name == "PhaseShift" and k < 4:
                show_p2(False)
            elif name == "PhaseShift":
                show_p2(True)
            sc.frame_set(f)
            shoot(os.path.join(OUT, f"act_{r:02d}_{name}_{k}_f{f:03d}.png"), -32, (0, -0.5, HT * 0.45), dist=7.2, elev=12, lens=50, res=(360, 400))
print("PREVIEW DONE", flush=True)
