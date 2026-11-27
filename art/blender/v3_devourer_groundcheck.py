"""v3 噬語魔王：逐片段、逐格檢查各部件最低點（rest 地面 z=0），輸出 markdown 表。
blender --background --python v3_devourer_groundcheck.py -- [blend] [out.md] [--step 1]
分類：
  本體（蒙皮主網格，不含書頁、武器、前擺）、書頁（Paper 材質：披風、左臂頁、地上散頁，含 X3_CapeLower）、武器（主導骨 Weapon 的頂點）、
  前擺（主導骨 TabardF*）、X3 甲件、P3_InkBody、P3_SwordWords*、P2_PageWing*、P2_SwordCracks（剛體部件以骨變換計算）。
合格：每類最低點 ≥ −0.02 m（PhaseShift2 的武器是插劍設計，列出但標註）。
"""
import bpy, sys, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend = next((a for a in argv if a.endswith(".blend")), os.path.join(HERE, "source", "v3_devourer.blend"))
out_md = next((a for a in argv if a.endswith(".md")), os.path.join(ROOT, "art", "v3", "tmp", "devourer", "ground.md"))
STEP = int(argv[argv.index("--step") + 1]) if "--step" in argv else 1
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
ad = arm.animation_data
skinned = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and any(m.type == "ARMATURE" for m in o.modifiers)]
rigid = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and o.parent_type == "BONE"]


def classes(o):
    """每個頂點的分類索引陣列。"""
    me = o.data
    n = len(me.vertices)
    cls = np.full(n, "本體", dtype=object)
    if o.name.startswith("X3_"):
        cls[:] = "X3 甲件"
    paper = [i for i, s in enumerate(o.material_slots) if s.material and s.material.name.startswith("Paper")]
    if paper:
        for p in me.polygons:
            if p.material_index in paper:
                for v in p.vertices:
                    cls[v] = "書頁"
    names = {g.index: g.name for g in o.vertex_groups}
    for v in me.vertices:
        if cls[v.index] == "書頁" or not v.groups:
            continue
        g = max(v.groups, key=lambda x: x.weight)
        nm = names.get(g.group, "")
        if nm == "Weapon":
            cls[v.index] = "武器"
        elif nm.startswith("TabardF"):
            cls[v.index] = "前擺"
    return cls


CL = {o.name: classes(o) for o in skinned}
CATS = ["本體", "書頁", "武器", "前擺", "X3 甲件", "P3_InkBody", "P3_SwordWords", "P2_PageWing", "P2_SwordCracks"]
rows = []
worst = {}
for tr in ad.nla_tracks:
    act = bpy.data.actions[tr.name]
    ad.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    mins = {c: (9.0, -1) for c in CATS}
    for f in range(f0, f1 + 1, STEP):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for o in skinned:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
            z = co[2::3] + o.matrix_world.translation.z
            cl = CL[o.name]
            for c in set(cl):
                m = z[cl == c].min()
                if m < mins[c][0]:
                    mins[c] = (float(m), f)
            ev.to_mesh_clear()
        for o in rigid:
            key = next((c for c in CATS if o.name.startswith(c)), None)
            if key is None:
                continue
            M = np.array(o.matrix_world)
            co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            z = co @ M[2, :3] + M[2, 3]
            m = z.min()
            if m < mins[key][0]:
                mins[key] = (float(m), f)
    rows.append((tr.name, mins))
    for c, (m, f) in mins.items():
        if m < worst.get(c, (9, "", 0))[0]:
            worst[c] = (m, tr.name, f)
    print("GC", tr.name, {c: round(m, 3) for c, (m, f) in mins.items() if m < 8}, flush=True)
ad.action = None
hdr = "| 片段 | " + " | ".join(CATS) + " |"
sep = "|---|" + "---|" * len(CATS)
lines = [hdr, sep]
bad = 0
for nm, mins in rows:
    cells = []
    for c in CATS:
        m, f = mins[c]
        if m > 8:
            cells.append("–"); continue
        ok = m >= -0.02 or (nm == "PhaseShift2" and c in ("武器", "P2_SwordCracks"))
        bad += 0 if ok else 1
        cells.append(f"{m:+.3f}@f{f}" + ("" if ok else " ✗"))
    lines.append(f"| {nm} | " + " | ".join(cells) + " |")
txt = f"逐格（每 {STEP} 格）最低點，單位 m；✗＝低於 −0.02 m。PhaseShift2 的劍是插地設計，不計。\n\n" + "\n".join(lines) + f"\n\n不合格格子數：{bad}\n"
open(out_md, "w", encoding="utf-8").write(txt)
print(txt)
print("GROUNDCHECK DONE bad=", bad)
