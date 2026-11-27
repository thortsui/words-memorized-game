"""v3 霜冠祭司：逐片段逐格檢查最低點（穿地）。開 source/v3_boss_priest.blend（與匯出的 GLB 同一套骨架與權重）。
用法：blender --background --factory-startup --python v3_priest_ground.py -- [step=1（半格為單位）] [out.txt]
每個片段列出：最低點 z（原始公尺；遊戲內 ×1.20）、哪一格、最低頂點的主要骨頭；P2 部件只在可見的片段段落計入（IdleAggro、PhaseShift 爆發後）。
"""
import bpy, sys, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STEP = int(argv[0]) if argv else 1
OUT = argv[1] if len(argv) > 1 else None
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "source", "v3_boss_priest.blend"))
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith("_mesh"))
rigid = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and o.parent_type == "BONE"]
gn = {g.index: g.name for g in body.vertex_groups}
dom = np.array([gn[max(v.groups, key=lambda g: g.weight).group] if v.groups else "" for v in body.data.vertices])
rco = {}
for o in rigid:
    c = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", c); rco[o.name] = c.reshape(-1, 3)
lines = []
worst_all = 0.0
for tr in arm.animation_data.nla_tracks:
    ac = bpy.data.actions[tr.name]
    arm.animation_data.action = ac
    f0, f1 = map(int, ac.frame_range)
    worst = (9.0, None, None)
    for ff in range(f0 * 2, f1 * 2 + 1, STEP):       # 每半格取樣（遊戲是連續時間）
        f = ff / 2
        sc.frame_set(int(f), subframe=f - int(f))
        dg = bpy.context.evaluated_depsgraph_get()
        oe = body.evaluated_get(dg); me = oe.to_mesh()
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3); oe.to_mesh_clear()
        M = np.array(body.matrix_world)
        z = co @ M[2, :3] + M[2, 3]
        i = int(np.argmin(z))
        if z[i] < worst[0]:
            worst = (float(z[i]), f, dom[i])
        for o in rigid:
            vis = o.name.startswith("X2_") or (o.name.startswith("P2_") and (tr.name == "IdleAggro" or (tr.name == "PhaseShift" and f >= 36)))
            if o.name.startswith("X2_") and (tr.name == "IdleAggro" or (tr.name == "PhaseShift" and f >= 36)):
                vis = False
            if not vis:
                continue
            Mw = np.array(o.matrix_world)
            zz = rco[o.name] @ Mw[2, :3] + Mw[2, 3]
            if zz.min() < worst[0]:
                worst = (float(zz.min()), f, o.name)
    ok = "OK" if worst[0] >= -0.01 else "穿地"
    worst_all = min(worst_all, worst[0])
    lines.append(f"GROUND {tr.name:<12} min z {worst[0]:+.3f} m  f{worst[1]:<5} {worst[2]:<14} {ok}")
lines.append(f"GROUND 全部最低 {worst_all:+.3f} m（門檻 −0.01）")
print("\n".join(lines), flush=True)
if OUT:
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
