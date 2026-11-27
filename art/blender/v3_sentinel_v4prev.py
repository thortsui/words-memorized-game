"""v1.3.0 sentinel 新招預覽（Blender 內）：開 blend 後渲染指定片段的關鍵影格（兩個視角），輸出 PNG 到 outdir。
用法：blender -b <blend> --python v3_sentinel_v4prev.py -- <outdir> [Sweep,Smash,...] [step]
之後用 python v3_sentinel_v4sheet.py <outdir> 拼圖。二階招（Smash/Leap/ComboB/Special）顯示 P2 部件。"""
import bpy, os, sys, json
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v3_sentinel_render as RD

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
clips = argv[1].split(",") if len(argv) > 1 else ["Sweep", "Smash", "Leap", "ComboB", "Special"]
step = int(argv[2]) if len(argv) > 2 else 6
P2 = {"Smash", "Leap", "ComboB", "Special", "IdleAggro"}
h = 2.4
os.makedirs(out, exist_ok=True)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
p2 = [o for o in bpy.data.objects if o.name.startswith("P2_")]
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA") or o.name.startswith("Plane"):
        bpy.data.objects.remove(o)
cam = RD.setup(h)
sc = bpy.context.scene
try:
    sc.eevee.taa_render_samples = 8
except Exception:
    pass
ad = arm.animation_data or arm.animation_data_create()
for t in ad.nla_tracks:
    t.mute = True
info = {}
for name in clips:
    act = bpy.data.actions.get(name)
    if not act:
        print("MISSING", name); continue
    ad.action = act
    for o in p2:
        o.hide_render = name not in P2
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    frames = sorted(set(list(range(f0, f1 + 1, step)) + [f1]))
    info[name] = frames
    for f in frames:
        sc.frame_set(f)
        for vi, (az, el) in enumerate(((-15, 0.16), (-100, 0.06))):
            RD.aim(cam, az, Vector((0, -0.25 * h, 0.45 * h)), 1.75 * h, elev=el * h, lens=40)
            RD.shot(cam, os.path.join(out, f"{name}_{f:03d}_{vi}.png"), (340, 380))
ad.action = None
json.dump(info, open(os.path.join(out, "frames.json"), "w"))
print("PREV DONE", flush=True)
