"""v4 噬語魔王新招：關鍵影格渲染＋逐格劍尖／網格最低點（讀 blend，預設 source/v3_devourer_quick.blend）。
blender --background --python v3_devourer_v4shots.py -- [blend] --clips Sweep,Smash --n 12 [--frames Sweep:0,10,33] [--az -35] [--out DIR]
輸出：<out>/<clip>_<az>_fNNN.png 與 <out>/diag_<clip>.txt；拼圖由 v3_devourer_v4sheet.py 做。
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend = next((a for a in argv if a.endswith(".blend")), os.path.join(HERE, "source", "v3_devourer_quick.blend"))
CLIPS = argv[argv.index("--clips") + 1].split(",") if "--clips" in argv else ["Sweep", "Smash", "Leap", "ComboB", "Special", "ComboC", "Special3"]
NSH = int(argv[argv.index("--n") + 1]) if "--n" in argv else 12
AZS = [float(a) for a in (argv[argv.index("--az") + 1].split(",") if "--az" in argv else ["-35", "80"])]
OUT = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(ROOT, "art", "v4", "tmp", "devourer", "shots")
FR = {}
if "--frames" in argv:
    for spec in argv[argv.index("--frames") + 1].split(";"):
        nm, fs = spec.split(":")
        FR[nm] = [int(x) for x in fs.split(",")]
NORENDER = "--norender" in argv
PHASE = {"Sweep": 1, "Smash": 2, "Leap": 2, "ComboB": 2, "Special": 2, "ComboC": 3, "Special3": 3}
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
ad = arm.animation_data
tip = bpy.data.objects.get("Tip_Weapon")
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA") or o.name.startswith("PreviewGround"):
        bpy.data.objects.remove(o)
skinned = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and any(m.type == "ARMATURE" for m in o.modifiers)]


def form(f):
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith("PreviewGround"):
            continue
        n = o.name
        on = True
        if n.startswith(("P2_PageWing", "P2_ChestMaw", "P2_ScriptChest")):
            on = f == 2
        elif n.startswith("P2_"):
            on = f >= 2
        elif n.startswith("P3_"):
            on = f >= 3
        elif n.startswith("X3_"):
            on = f < 3
        o.hide_render = not on


try:
    sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    sc.render.engine = "BLENDER_EEVEE"
sc.view_settings.view_transform = "AgX"
try:
    sc.eevee.taa_render_samples = 8
except Exception:
    pass
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)


def light(loc, energy, size, tgt=(0, 0, 1.9)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy = energy; l.data.size = size
    l.rotation_euler = (Vector(tgt) - l.location).to_track_quat("-Z", "Y").to_euler()


light((-4.5, -6.0, 7.0), 2600, 3.0); light((5.0, -3.0, 2.5), 600, 5.0); light((2.5, 6.5, 6.0), 2400, 2.5)
bpy.ops.mesh.primitive_plane_add(size=60)
gp = bpy.context.object; gp.name = "PreviewGround"
gm = bpy.data.materials.new("PG"); gm.use_nodes = True
b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1)
gp.data.materials.append(gm)
# 地面格線（1 m）方便看位置
bpy.ops.object.camera_add()
cam = bpy.context.object; sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 7.6; cam.data.clip_end = 200
sc.render.resolution_x, sc.render.resolution_y = 300, 340


def shoot(path, az):
    a = math.radians(az)
    tgt = Vector((0, -0.7, 2.2))
    cam.location = tgt + Vector((math.sin(a) * 14, -math.cos(a) * 14, 1.2))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


for nm in CLIPS:
    act = bpy.data.actions.get(nm)
    if act is None:
        print("NO ACTION", nm); continue
    ad.action = act
    for t in ad.nla_tracks:
        t.mute = True
    form(PHASE.get(nm, 1))
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    lines = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        mz = 9.0
        for o in skinned:
            if o.hide_render:
                continue
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
            mz = min(mz, co[2::3].min() + o.matrix_world.translation.z)
            ev.to_mesh_clear()
        tz = tip.matrix_world.translation.z if tip else 0
        hz = (arm.matrix_world @ arm.pose.bones["Hips"].head).z
        lines.append(f"f{f:3d} tip {tz:+.2f} hips {hz:.2f} meshmin {mz:+.3f}")
    open(os.path.join(OUT, f"diag_{nm}.txt"), "w").write("\n".join(lines))
    if NORENDER:
        continue
    frs = FR.get(nm) or [round(f0 + (f1 - f0) * k / (NSH - 1)) for k in range(NSH)]
    for f in frs:
        sc.frame_set(f)
        for az in AZS:
            shoot(os.path.join(OUT, f"{nm}_{int(az)}_f{f:03d}.png"), az)
    print("SHOTS", nm, frs, flush=True)
print("V4SHOTS DONE")
