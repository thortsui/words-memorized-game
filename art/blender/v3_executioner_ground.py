"""v3 行刑者：逐片段、逐 2 格量模型最低點（身體／武器／墨影分開）與 Tip_Weapon 高度，找穿地。
用法：blender --background <blend> --python v3_executioner_ground.py -- <out.json>
"""
import bpy, sys, json
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else None
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = bpy.data.objects["boss_executioner_mesh"]
tip = bpy.data.objects.get("Tip_Weapon")
parts = [o for o in bpy.data.objects if o.name.startswith("P2_") and o.type == "MESH"]
me0 = mesh.data
gi = mesh.vertex_groups["Weapon"].index
wpn = np.zeros(len(me0.vertices), bool)
for v in me0.vertices:
    for g in v.groups:
        if g.group == gi and g.weight > 0.5:
            wpn[v.index] = True
inkm = {i for i, s in enumerate(mesh.material_slots) if s.material and s.material.name.startswith(("Ink", "Glow_Rune"))}
ink = np.zeros(len(me0.vertices), bool)
for p in me0.polygons:
    if p.material_index in inkm:
        for vi in p.vertices:
            ink[vi] = True
body = ~wpn & ~ink
R = {}
for tr in arm.animation_data.nla_tracks:
    act = bpy.data.actions[tr.name]; arm.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    rec = dict(body=9.0, weapon=9.0, ink=9.0, tip=9.0, p2=9.0, bad=[])
    for f in range(f0, f1 + 1, 2):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(dg); me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        z = (np.array(mesh.matrix_world) @ np.c_[co, np.ones(len(co))].T)[2]
        ev.to_mesh_clear()
        b, w_, k = z[body].min(), z[wpn].min(), z[ink].min()
        t = tip.matrix_world.translation.z if tip else 9
        p2 = 9.0
        if True:   # 二階起所有片段都會顯示 P2
            for o in parts:
                mw = o.matrix_world
                p2 = min(p2, min((mw @ v.co).z for v in o.data.vertices))
        rec["body"] = min(rec["body"], b); rec["weapon"] = min(rec["weapon"], w_); rec["ink"] = min(rec["ink"], k); rec["tip"] = min(rec["tip"], t); rec["p2"] = min(rec["p2"], p2)
        if b < -0.02 or w_ < -0.02:
            rec["bad"].append((f, round(float(b), 3), round(float(w_), 3)))
    R[tr.name] = {k: (round(float(v), 3) if not isinstance(v, list) else v) for k, v in rec.items()}
    print("GROUND", tr.name, json.dumps(R[tr.name]), flush=True)
if OUT:
    json.dump(R, open(OUT, "w"), indent=1)
