"""單字魂 v3 主角：逐片段、逐格量「模型最低點」「劍尖高度」「披風是否穿進軀幹」。
用法：blender --background art/blender/source/v3_hero_knight.blend --python v3_hero_ground.py -- [--step 1] [--out json]
判定：最低點與劍尖都 ≥ -0.02 m（Die 片段倒地後劍貼地屬設計，仍要求 ≥ -0.02）；
披風頂點轉到骨盆／胸腔座標後，若落在軀幹橢圓柱內側（背面再往內 2 cm）就算穿身。
"""
import bpy, sys, json, os
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STEP = int(argv[argv.index("--step") + 1]) if "--step" in argv else 1
OUT = argv[argv.index("--out") + 1] if "--out" in argv else None
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm)
me = mesh.data
gi = {g.name: g.index for g in mesh.vertex_groups}
W = np.zeros((len(me.vertices), len(gi)))
for v in me.vertices:
    for g in v.groups:
        W[v.index, g.group] = g.weight
wpn = np.where(W[:, gi["Weapon"]] > 0.5)[0]
cape = np.where(W[:, [gi[n] for n in ("Cape1", "Cape2", "Cape3") if n in gi]].sum(axis=1) > 0.5)[0]
gname = {i: n for n, i in gi.items()}
rest = np.array([v.co[:] for v in me.vertices])
# 劍尖：武器頂點中離武器骨原點最遠的那顆（rest）
wb = arm.data.bones["Weapon"]
d = np.linalg.norm(rest[wpn] - np.array(wb.head_local), axis=1)
tip_i = wpn[np.argmax(d)]
res = {}
dg = bpy.context.evaluated_depsgraph_get()
ad = arm.animation_data
names = [t.name for t in ad.nla_tracks if not t.name.startswith("_")]
for name in names:
    act = bpy.data.actions[name]
    ad.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    cdep = 0.0; zmin = (9, -1, ''); tipmin = (9, -1); capein = (0, -1)
    for f in range(f0, f1 + 1, STEP):
        bpy.context.scene.frame_set(f)
        dg.update()
        ev = mesh.evaluated_get(dg)
        m2 = ev.to_mesh()
        P = np.empty(len(m2.vertices) * 3); m2.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
        ev.to_mesh_clear()
        P = P @ np.array(mesh.matrix_world)[:3, :3].T + np.array(mesh.matrix_world)[:3, 3]
        zi = int(np.argmin(P[:, 2])); z = P[zi, 2]
        if z < zmin[0]:
            zmin = (float(z), f, gname[int(np.argmax(W[zi]))] + str(np.round(rest[zi], 2).tolist()))
        if P[tip_i, 2] < tipmin[0]:
            tipmin = (float(P[tip_i, 2]), f)
        # 披風穿身：以 Spine（腰）與 Spine2（胸）的骨架座標判斷
        n_in = 0
        depth = 0.0
        for bn, z0, z1, rx, ry in (("Hips", -0.10, 0.20, 0.17, 0.10), ("Spine2", -0.12, 0.25, 0.19, 0.09)):
            pb = arm.pose.bones[bn]
            M = np.array((arm.matrix_world @ pb.matrix).inverted())
            Q = P[cape] @ M[:3, :3].T + M[:3, 3]           # 骨頭座標：y 沿骨頭（往上），x 左右，z 前後（Blender 骨頭 local）
            x = Q[:, 0]; zz = Q[:, 2]; yy = Q[:, 1]
            rr = np.sqrt((x / rx) ** 2 + (zz / ry) ** 2)
            inside = (yy > z0) & (yy < z1) & (rr < 1.0)
            n_in += int(inside.sum())
            if inside.any():
                depth = max(depth, float(((1 - rr[inside]) * ry).max()))
        if n_in > capein[0]:
            capein = (n_in, f)
        cdep = max(cdep, depth)
    res[name] = dict(frames=f1 - f0 + 1, zmin=round(zmin[0], 3), zmin_f=zmin[1], zmin_bone=zmin[2], tip=round(tipmin[0], 3), tip_f=tipmin[1],
                     cape_in=capein[0], cape_in_f=capein[1], cape_depth=round(cdep, 3))
    ok = zmin[0] >= -0.02 and tipmin[0] >= -0.02
    print(f"GROUND {name:11s} zmin {zmin[0]:+.3f} @f{zmin[1]:<3d}({zmin[2]:28s}) tip {tipmin[0]:+.3f} @f{tipmin[1]:<3d} cape_in {capein[0]:4d} @f{capein[1]:<3d} depth {cdep * 100:.1f}cm {'OK' if ok else 'FAIL'}",
          flush=True)
ad.action = None
if OUT:
    json.dump(res, open(OUT, "w"), indent=1)
