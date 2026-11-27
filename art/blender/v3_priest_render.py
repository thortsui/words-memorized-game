"""v3 霜冠祭司：開 source/v3_boss_priest.blend 渲染預覽（不重建模型）。
用法：blender --background --factory-startup --python v3_priest_render.py -- <out_dir> [set]
  set：views（p1 正／側／背／3/4＋對照視角 A/B）、close（近景特寫）、p2（二階正面＋3/4）、acts（17 片段各 8 格）、all
燈光照規格 §7：頂部偏左冷白主光、背景 #1a1a1c。
"""
import bpy, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(argv[0])
SET = argv[1] if len(argv) > 1 else "all"
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "source", "v3_boss_priest.blend"))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
HH = 2.66
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
p2 = [o for o in bpy.data.objects if o.name.startswith("P2_")]


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def setup(res=(560, 800)):
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    g = lin(0x1a / 255)
    bg.inputs[0].default_value = (g, g, lin(0x1c / 255), 1); bg.inputs[1].default_value = 1.0

    def area(loc, energy, size, color):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.data.energy = energy; l.data.size = size; l.data.color = color
        d = Vector((0, 0, HH * 0.6)) - l.location
        l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return l
    s = HH / 1.8
    area((-2.0 * s, -2.6 * s, 4.2 * s), 260 * s * s, 2.0 * s, (0.90, 0.95, 1.0))     # 主光：頂部偏左、冷白
    area((3.0 * s, -2.4 * s, 1.6 * s), 45 * s * s, 3.5 * s, (0.80, 0.86, 1.0))       # 補光
    area((1.0 * s, 3.6 * s, 3.2 * s), 150 * s * s, 2.0 * s, (0.75, 0.85, 1.0))       # 背光（輪廓）
    bpy.ops.mesh.primitive_plane_add(size=60)
    gp = bpy.context.object
    gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
    b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1); b.inputs["Roughness"].default_value = 0.85
    gp.data.materials.append(gm)
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.eevee.taa_render_samples = 32
    except Exception:
        pass
    return cam


def aim(cam, az, target, dist, elev=0.0, lens=60):
    a = math.radians(az)
    cam.location = Vector((math.sin(a) * dist, -math.cos(a) * dist, target.z + elev))
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


def pose(action=None, frame=0):
    ad = arm.animation_data
    if action and action in bpy.data.actions:
        ad.action = bpy.data.actions[action]
        sc.frame_set(frame)
    else:
        if ad:
            ad.action = None
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        sc.frame_set(0)


X2 = [o for o in bpy.data.objects if o.name.startswith("X2_")]


def show_p2(on):
    for o in p2:
        o.hide_render = not on
    for o in X2:                 # 一階經書：二階起由遊戲隱藏
        o.hide_render = on


def shot(cam, name, az, tz, dist, elev=0.0, lens=60, res=None):
    if res:
        sc.render.resolution_x, sc.render.resolution_y = res
    aim(cam, az, Vector((0, 0, tz)), dist, elev, lens)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("SHOT", name, flush=True)


cam = setup()
if SET in ("views", "all"):
    show_p2(False)
    pose("Idle", 0)
    for nm, az in (("front", 0), ("side", 90), ("back", 180), ("threeq", -35), ("refA", -15), ("refB", -35)):
        shot(cam, "p1_" + nm, az, HH * 0.5, HH * 2.35, HH * 0.10, 50, (560, 800))
    pose(None)
    shot(cam, "rest_front", 0, HH * 0.5, HH * 2.35, HH * 0.10, 50, (560, 800))
    shot(cam, "rest_side", 90, HH * 0.5, HH * 2.35, HH * 0.10, 50, (560, 800))
if SET in ("close", "all"):
    show_p2(False)
    pose("Idle", 0)
    shot(cam, "c_face", -12, HH * 0.825, HH * 0.30, -HH * 0.01, 60, (700, 700))
    shot(cam, "c_crown", -25, HH * 0.90, HH * 0.50, HH * 0.03, 60, (700, 700))
    shot(cam, "c_hood", -30, HH * 0.74, HH * 0.75, HH * 0.03, 60, (700, 700))
    shot(cam, "c_sleeve", 55, HH * 0.52, HH * 0.80, HH * 0.03, 60, (700, 700))
    shot(cam, "c_hem", -20, HH * 0.12, HH * 0.75, HH * 0.10, 60, (700, 700))
    shot(cam, "c_band", -8, HH * 0.45, HH * 0.42, HH * 0.0, 60, (700, 700))
    m = arm.matrix_world
    tip = None
    pb = arm.pose.bones.get("Tip_Weapon")
    if pb:
        tip = m @ pb.head
        cam.data.lens = 60
        a = math.radians(-20)
        cam.location = tip + Vector((math.sin(a) * HH * 0.45, -math.cos(a) * HH * 0.45, -HH * 0.02)) - (tip - (m @ arm.pose.bones["Weapon"].head)).normalized() * HH * 0.08
        d = (tip - (tip - (m @ arm.pose.bones["Weapon"].head)).normalized() * HH * 0.10) - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(OUT, "c_spear.png")
        bpy.ops.render.render(write_still=True)
if SET in ("p2", "all"):
    show_p2(True)
    pose("PhaseShift", 46)
    shot(cam, "p2_front", 0, HH * 0.58, HH * 2.5, HH * 0.06, 50, (700, 800))
    shot(cam, "p2_threeq", -35, HH * 0.58, HH * 2.5, HH * 0.06, 50, (700, 800))
    pose("IdleAggro", 0)
    shot(cam, "p2_aggro", -20, HH * 0.55, HH * 2.5, HH * 0.06, 50, (700, 800))
    show_p2(False)
if SET in ("acts", "all"):
    sc.render.resolution_x, sc.render.resolution_y = (360, 400)
    try:
        sc.eevee.taa_render_samples = 12
    except Exception:
        pass
    aim(cam, -32, Vector((0, -HH * 0.10, HH * 0.48)), HH * 2.4, HH * 0.20, 45)
    names = [t.name for t in arm.animation_data.nla_tracks]
    for r, name in enumerate(names):
        act = bpy.data.actions[name]
        arm.animation_data.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        for k in range(8):
            f = int(round(f0 + (f1 - f0) * k / 7))
            show_p2(name == "IdleAggro" or (name == "PhaseShift" and f >= 36))
            sc.frame_set(f)
            sc.render.filepath = os.path.join(OUT, f"act_{r:02d}_{name}_{k}_f{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    show_p2(False)
print("RENDER DONE", flush=True)
