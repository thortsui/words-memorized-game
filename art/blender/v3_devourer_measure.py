"""v3 噬語魔王：在 Blender 內實測比例（rest pose，讀 source/v3_devourer.blend），對照 spec §1 比例表，輸出 markdown 表。
blender --background --python v3_devourer_measure.py -- [blend] [out.md]
量法：H＝所有非 P2_/P3_ 網格的 bbox 高；水平截面用 bmesh bisect，取包住身體中心的那一圈（外輪廓含甲／衣，不含書頁）；
四肢在骨中點切垂直於骨軸的平面，取截面頂點到骨軸距離最大值 ×2（外輪廓）。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend = next((a for a in argv if a.endswith(".blend")), os.path.join(HERE, "source", "v3_devourer.blend"))
out_md = next((a for a in argv if a.endswith(".md")), os.path.join(ROOT, "art", "v3", "tmp", "devourer", "measure.md"))
bpy.ops.wm.open_mainfile(filepath=blend)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def world_bm(objs, skip_paper=True, bones=None, skip_cls=(1, 3)):
    """合併成世界座標 bmesh。skip_cls：略過的部位分類（mcls：1 書頁／內襯、3 配件、8 布腰帶、9 肩甲）；
    bones：只留主導權重骨在此集合內的頂點。"""
    bm = bmesh.new()
    for o in objs:
        b2 = bmesh.new(); b2.from_mesh(o.data)
        b2.transform(o.matrix_world)
        cl = b2.verts.layers.int.get("mcls")
        dl = b2.verts.layers.deform.active
        names = {g.index: g.name for g in o.vertex_groups}
        kill = set()
        for v in b2.verts:
            if skip_paper and cl is not None and v[cl] in skip_cls:
                kill.add(v); continue
            if bones is not None:
                if dl is None or not v[dl]:
                    kill.add(v); continue
                gi, wgt = max(v[dl].items(), key=lambda kv: kv[1])
                if names.get(gi) not in bones:
                    kill.add(v)
        if skip_paper:
            pm = [i for i, s in enumerate(o.material_slots) if s.material and s.material.name.startswith(("Paper", "P3_Ink"))]
            kill |= {v for f in b2.faces if f.material_index in pm for v in f.verts}
        bmesh.ops.delete(b2, geom=list(kill), context="VERTS")
        tmp = bpy.data.meshes.new("tmp"); b2.to_mesh(tmp); b2.free()
        bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    return bm


main = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith(("P2_", "P3_", "Preview"))]
allv = []
for o in main:
    allv += [o.matrix_world @ v.co for v in o.evaluated_get(dg).data.vertices]
H = max(v.z for v in allv) - min(v.z for v in allv)
z0 = min(v.z for v in allv)
BM = world_bm(main)
BMP = world_bm(main, skip_paper=False)
TORSO = {"Hips", "Spine", "Spine2", "Neck", "ShoulderL", "ShoulderR"}
BMT = world_bm(main, bones=TORSO | {"ThighL", "ThighR"}, skip_cls=(1, 3, 9))
BMW = world_bm(main, bones=TORSO, skip_cls=(1, 3, 9))
BMH = world_bm(main, bones={"Head", "Neck"})
LIMB = {b: world_bm(main, bones={b}, skip_cls=(1, 3, 9)) for b in ("UpperArmL", "ForearmL", "HandL", "ThighL", "ShinL", "FootL")}


def hsection(z, cx=0.0, cy=0.0, src=None):
    b = (src or BM).copy()
    geom = b.verts[:] + b.edges[:] + b.faces[:]
    r = bmesh.ops.bisect_plane(b, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1), clear_outer=False, clear_inner=False)
    pts = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    # 依相連邊分組
    adj = {}
    for e in pts:
        a, c = e.verts
        adj.setdefault(a, []).append(c); adj.setdefault(c, []).append(a)
    seen = set(); comps = []
    for v in adj:
        if v in seen:
            continue
        st = [v]; comp = []
        seen.add(v)
        while st:
            x = st.pop(); comp.append(x.co.copy())
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); st.append(y)
        comps.append(comp)
    b.free()
    return comps


def torso_outer(z, rmax=0.75, src=None):
    comps = hsection(z, src=src or BMT)
    pts = []
    for c in comps:
        cxm = sum(p.x for p in c) / len(c); cym = sum(p.y for p in c) / len(c)
        if abs(cxm) < rmax and abs(cym) < 0.6:
            pts += [p for p in c if abs(p.x) < rmax and abs(p.y) < 0.65]
    if not pts:
        return 0, 0
    return max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts)


def limb_outer(b0, b1, frac=0.5, rmax=0.35, src=None):
    bn = arm.data.bones[b0]
    a = arm.matrix_world @ bn.head_local; c = arm.matrix_world @ (arm.data.bones[b1].head_local if b1 else bn.tail_local)
    ax = (c - a).normalized(); p = a + (c - a) * frac
    b = (src or LIMB[b0]).copy()
    r = bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=p, plane_no=ax, clear_outer=False, clear_inner=False)
    d = []
    for g in r["geom_cut"]:
        if isinstance(g, bmesh.types.BMVert):
            q = g.co - p
            q = q - ax * q.dot(ax)
            if q.length < rmax:
                d.append(q.length)
    b.free()
    return 2 * max(d) if d else 0


rows = []


def row(name, val, target, rng=None, unit="H"):
    v = val / H
    if rng:
        ok = rng[0] * 0.999 <= v <= rng[1] * 1.001
        err = 0.0 if ok else min(abs(v - rng[0]), abs(v - rng[1])) / ((rng[0] + rng[1]) / 2) * 100
        tgt = f"{rng[0]:.3f}–{rng[1]:.3f}"
    else:
        err = (v - target) / target * 100; ok = abs(err) <= 10
        tgt = f"{target:.3f}"
    rows.append((name, f"{v:.3f}", tgt, f"{err:+.1f}%", "OK" if ok else "超出"))


cw, cd = torso_outer(z0 + 0.65 * H)
ww, wd = torso_outer(z0 + 0.555 * H, src=world_bm(main, bones=TORSO, skip_cls=(1, 3, 9)))
hw, hd = torso_outer(z0 + 0.45 * H, rmax=0.8)
row("胸寬（外，含甲）@0.65H", cw, 0.26); row("胸厚（外）", cd, 0.18)
row("腰寬（外，含布腰帶）@0.555H", ww, 0.20); row("腰厚（外）", wd, 0.15)
row("臀寬（外，含腿甲片）@0.45H", hw, 0.26)
rows.append(("胸／腰 比", f"{cw / max(ww, 1e-6):.2f}", "≈1.30", f"{(cw / ww / 1.3 - 1) * 100:+.1f}%", "OK" if abs(cw / ww / 1.3 - 1) <= 0.1 else "超出"))
# 肩寬：肩甲外緣（0.70–0.80H 的 X 範圍，排除手與角）
sv = [v for v in BM.verts if z0 + 0.68 * H < v.co.z < z0 + 0.80 * H and abs(v.co.y) < 0.6]
row("肩寬（肩甲外緣）", max(v.co.x for v in sv) - min(v.co.x for v in sv), 0.40, (0.38, 0.42))
row("上臂直徑（外，上臂甲）", limb_outer("UpperArmL", "ForearmL", 0.62), 0.075)
row("前臂直徑（外）", limb_outer("ForearmL", "HandL", 0.40), 0.068)
row("手腕直徑（外）", limb_outer("ForearmL", "HandL", 0.97, rmax=0.2), 0.055)
row("大腿直徑（外）", limb_outer("ThighL", "ShinL", 0.45), 0.115)
row("小腿直徑（外，脛甲）", limb_outer("ShinL", "FootL", 0.45), 0.085)
row("腳踝直徑（外）", limb_outer("ShinL", "FootL", 0.90, rmax=0.2), 0.065)
# 頭
hv = [v.co for v in BMH.verts if z0 + 0.77 * H < v.co.z < z0 + 0.805 * H and abs(v.co.x) < 0.24 and v.co.y < 0.25]   # 頰甲高度（排除角根與墨滴）
hs = [v.co for v in BMH.verts if z0 + 0.79 * H < v.co.z < z0 + 0.835 * H and abs(v.co.x) < 0.17 and v.co.y < -0.13]   # 骨面（頰甲在 y>-0.13）
row("頭寬（含頰甲）", max(p.x for p in hv) - min(p.x for p in hv), 0.10)
row("骷髏寬（眼高）", max(p.x for p in hs) - min(p.x for p in hs), 0.075)
# 角冠：顱頂以上的點
cv = [v.co for v in BM.verts if v.co.z > z0 + 0.865 * H and abs(v.co.y) < 0.5 and abs(v.co.x) < 0.9]
row("角冠展開寬", max(p.x for p in cv) - min(p.x for p in cv), 0.315, (0.30, 0.33))
row("角冠高（顱頂→最高角尖）", H - 0.86 * H, 0.14)
# 劍
wb = arm.data.bones["Weapon"]
wa = (wb.tail_local - wb.head_local).normalized()
gi = None
wv = []
for o in main:
    if o.name.endswith("_mesh") and "Weapon" in o.vertex_groups:
        gi = o.vertex_groups["Weapon"].index
        for v in o.data.vertices:
            if any(g.group == gi and g.weight > 0.5 for g in v.groups):
                wv.append((o.matrix_world @ v.co - wb.head_local).dot(wa))
if wv:
    row("巨劍全長", max(wv) - min(wv), 0.80, (0.76, 0.84))
# 披風地面寬（0.05H 截面，含書頁）
gp = [v.co for v in BMP.verts]
comps = hsection(z0 + 0.05 * H, src=BMP)
xs = [p.x for c in comps for p in c]
row("披風地面寬 @0.05H", max(xs) - min(xs), 0.685, (0.65, 0.72))
# 二階紙翼
for side in ("L", "R"):
    pass
wl = bpy.data.objects.get("P2_PageWingL"); wr_ = bpy.data.objects.get("P2_PageWingR")
if wl and wr_:
    xl = max((wl.matrix_world @ v.co).x for v in wl.data.vertices); xr = min((wr_.matrix_world @ v.co).x for v in wr_.data.vertices)
    zt = max((wl.matrix_world @ v.co).z for v in wl.data.vertices); zb = min((wl.matrix_world @ v.co).z for v in wl.data.vertices)
    row("紙翼總展寬（二階）", xl - xr, 1.40)
    row("翼頂最高", zt - z0, 1.05)
    row("翼尖下緣", zb - z0, 0.45, (0.30, 0.50))
cr = bpy.data.objects.get("P3_Crown")
if cr:
    vs = [cr.matrix_world @ v.co for v in cr.data.vertices]
    row("三階光環直徑", max(p.x for p in vs) - min(p.x for p in vs) - 0.03, 0.26)
md = ["| 項目 | 實測（H） | spec | 誤差 | 判定 |", "|---|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
txt = f"H（角尖→靴底）＝{H:.3f} m\n\n" + "\n".join(md) + "\n"
open(out_md, "w", encoding="utf-8").write(txt)
print(txt)
print("MEASURE DONE")
