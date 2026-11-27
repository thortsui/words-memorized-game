"""v4 石像鬼新片段檢查（Blender headless）＋拼圖（系統 Python）。
  Blender：blender -b --factory-startup --python v4_gargoyle_check.py -- dev    只做新片段（模型 blend＋新動作）→ 檢查＋渲染
           blender -b --factory-startup --python v4_gargoyle_check.py -- final  開 source/v2a_boss_gargoyle.blend（完整版）→ 全片段逐格穿地／滑步檢查＋渲染新片段
  拼圖：   python v4_gargoyle_check.py sheet
輸出全部在 art/v4/tmp/gargoyle/。
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "v4", "tmp", "gargoyle")
TILES = os.path.join(OUT, "tiles")
NEW = ["Sweep", "Smash", "Leap", "ComboB", "Special"]
P2CLIPS = {"Smash", "Leap", "ComboB", "Special", "IdleAggro"}

try:
    import bpy
except ImportError:
    bpy = None

if bpy is None:
    from PIL import Image, ImageDraw
    import glob, re
    kf = json.load(open(os.path.join(OUT, "keyframes.json"), encoding="utf-8"))
    for name in NEW:
        for view in ("q", "s", "f"):
            ps = sorted(glob.glob(os.path.join(TILES, f"{name}_{view}_*.png")))
            if not ps:
                continue
            ims = [Image.open(p).convert("RGB") for p in ps]
            w, h = ims[0].size
            cols = min(len(ims), 7)
            rows = (len(ims) + cols - 1) // cols
            sh = Image.new("RGB", (w * cols, h * rows), (15, 15, 16))
            d = ImageDraw.Draw(sh)
            for i, (im, p) in enumerate(zip(ims, ps)):
                x, y = (i % cols) * w, (i // cols) * h
                sh.paste(im, (x, y))
                f = int(re.search(r"_f(\d+)", p).group(1))
                d.text((x + 6, y + 6), f"{name} f{f} {f / 30:.2f}s", fill=(255, 220, 120))
            sh.save(os.path.join(OUT, f"sheet_{name}_{view}.jpg"), quality=88)
            print("sheet", name, view)
    sys.exit(0)

import numpy as np
from mathutils import Vector
sys.path.insert(0, HERE)
import soul_creature_lib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "dev"
ARGS = [a for a in argv[1:] if not a.startswith("--")]
os.makedirs(TILES, exist_ok=True)
HEIGHT = 2.95

if MODE == "dev":
    import v4_gargoyle_actions as V4
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "source", "v2a_boss_gargoyle_model.blend"))
    arm = bpy.data.objects["Gargoyle"]
    L.clear_actions(arm)
    A = L.Animator(arm, base=None)
    A.ground_r = {"*": 0.04, "Hips": 0.20, "Spine1": 0.22, "Spine2": 0.24, "Neck": 0.14, "Head": 0.12, "Jaw": 0.03, "Fingers.L": 0.02, "Fingers.R": 0.02,
                  "Hand.L": 0.03, "Hand.R": 0.03}
    A.ground_skip = {b.name for b in arm.data.bones if b.name.startswith(("Tail", "Wing"))}
    for sx in (".L", ".R"):
        A.add_leg("Thigh" + sx, "Shin" + sx, ["Foot" + sx, "Toe" + sx], "Foot" + sx + ":ik")
    only = ARGS or NEW
    V4.setup_front_ik(A)
    fn = {"Sweep": V4.sweep, "Smash": V4.smash, "Leap": V4.leap, "ComboB": V4.combob, "Special": V4.special}
    for nm in NEW:
        if nm in only:
            fn[nm](A)
    json.dump(V4.KEYFRAMES, open(os.path.join(OUT, "keyframes.json"), "w"))
    print("META", json.dumps({k: A.meta[k] for k in A.meta}, ensure_ascii=False), flush=True)
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "source", "v2a_boss_gargoyle.blend"))
    arm = bpy.data.objects["Gargoyle"]

acts = {a.name: a for a in bpy.data.actions}
mesh = bpy.data.objects["GargoyleMesh"]
p2 = [o for o in bpy.data.objects if o.name.startswith("P2_")]
if not arm.animation_data:
    arm.animation_data_create()
dg = bpy.context.evaluated_depsgraph_get()
CHECK = list(acts) if MODE == "final" else [n for n in NEW if n in acts]
report = {}
for name in CHECK:
    a = acts[name]
    arm.animation_data.action = a
    last = int(round(a.frame_range[1]))
    minz, worst, wbone, bad = 9, -1, "", []
    pts = {b: [] for b in ("Fingers.L", "Fingers.R", "Toe.L", "Toe.R")}
    for f in range(0, last + 1):
        bpy.context.scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        me = mesh.evaluated_get(dg).to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        zz = (np.array(mesh.matrix_world) @ np.c_[co.reshape(-1, 3), np.ones(len(me.vertices))].T)[2]
        vi = int(zz.argmin())
        z = zz[vi]
        mesh.evaluated_get(dg).to_mesh_clear()
        if z < minz:
            gs = sorted(mesh.data.vertices[vi].groups, key=lambda g: -g.weight)
            minz, worst, wbone = z, f, (mesh.vertex_groups[gs[0].group].name if gs else "?")
        if z < -0.04:
            gs = sorted(mesh.data.vertices[vi].groups, key=lambda g: -g.weight)
            bad.append((f, mesh.vertex_groups[gs[0].group].name if gs else "?", round(z * 100, 1)))
        for b in pts:
            pts[b].append(arm.matrix_world @ arm.pose.bones[b].tail)
    slide = {}
    sf = []
    for b, arr in pts.items():
        tot, mx = 0.0, 0.0
        for f in range(len(arr) - 1):
            if arr[f].z < 0.06 and arr[f + 1].z < 0.06:
                d = (Vector((arr[f + 1].x - arr[f].x, arr[f + 1].y - arr[f].y))).length
                tot += d
                mx = max(mx, d)
                if d > 0.01:
                    sf.append((b, f, round(d * 100, 1)))
        slide[b] = (round(tot * 100, 1), round(mx * 100, 2))
    report[name] = dict(frames=last, min_z_cm=round(minz * 100, 1), worst_frame=worst, worst_bone=wbone, frames_below_4cm=len(bad), slide_cm_total_max=slide)
    print(f"CHECK {name:10s} 0-{last} minZ={minz * 100:6.1f}cm@f{worst}({wbone}) <-4cm:{len(bad)}f  slide(cm total/max per frame)={slide}", flush=True)
    if "--verbose" in argv:
        print("   below:", bad, flush=True)
        print("   slide:", sf, flush=True)
arm.animation_data.action = None
json.dump(report, open(os.path.join(OUT, f"check_{MODE}.json"), "w"), ensure_ascii=False, indent=1)

if "--norender" not in argv:
    kf = json.load(open(os.path.join(OUT, "keyframes.json")))
    cam = bpy.data.objects.get("Cam")
    if cam is None:
        cam, _ = L.studio(HEIGHT)
    sc = bpy.context.scene
    sc.camera = cam
    try:
        sc.eevee.taa_render_samples = 12
    except Exception:
        pass
    for f in os.listdir(TILES):
        if any(f.startswith(n + "_") for n in (ARGS or NEW)):
            os.remove(os.path.join(TILES, f))
    for name in NEW:
        if name not in acts or (ARGS and name not in ARGS and MODE == "dev"):
            continue
        for o in p2:
            o.hide_render = name not in P2CLIPS
        arm.animation_data.action = acts[name]
        for view, az, el, dist in (("q", -40, 10, 3.2), ("s", 80, 6, 3.4), ("f", 0, 8, 3.2)):
            L.aim(cam, (0, -0.4, HEIGHT * 0.42), HEIGHT * dist, az, el, rig=False)
            for f in kf.get(name, []):
                sc.frame_set(f)
                L.render(os.path.join(TILES, f"{name}_{view}_f{f:03d}.png"), (360, 360))
    arm.animation_data.action = None
print("DONE check", MODE, flush=True)
