"""v3 sentinel 比例實測（Blender 背景）：讀 GLB，rest pose（或 --idle 用 Idle 第 0 格量站距／前傾），
只取「甲冑組 A 材質」＋依主要權重骨頭分群，避免長擺、根鬚、另一條腿、門板混進截面。輸出 JSON＋表格。
用法：blender -b --factory-startup --python v3_sentinel_measure.py -- <glb> <out.json>"""
import bpy, sys, json, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
path, out = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
A_KEYS = ("boss_sentinel_A", "plate", "pauld", "arm", "glove", "legp", "knee", "greave", "boot", "hat", "crown", "gold", "mail", "void",
          "hatin", "burlap", "gambeson")


def hidden(o):
    p = o
    while p:
        if p.name.startswith(("P2_", "P3_")):
            return True
        p = p.parent
    return False


def collect():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    V = []
    for o in bpy.data.objects:
        if o.type != "MESH" or hidden(o) or o.name.startswith("Icosphere") or not o.vertex_groups:
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        mats = [m.name if m else "" for m in o.data.materials]
        groups = {g.index: g.name for g in o.vertex_groups}
        vmat = {}
        for p in me.polygons:
            for vi in p.vertices:
                vmat[vi] = mats[p.material_index] if p.material_index < len(mats) else ""
        src = o.data.vertices
        for v in me.vertices:
            w = max(src[v.index].groups, key=lambda g: g.weight, default=None) if v.index < len(src) else None
            bone = groups.get(w.group) if w else None
            m = vmat.get(v.index, "")
            isA = any(k in m for k in A_KEYS) and "Glow" not in m
            V.append((o.matrix_world @ v.co, bone, isA, m))
        oe.to_mesh_clear()
    return V


def set_pose(action=None, frame=0):
    ad = arm.animation_data
    if action and ad:
        ad.action = bpy.data.actions.get(action) or next((a for a in bpy.data.actions if a.name.startswith(action)), None)
        bpy.context.scene.frame_set(frame)
    else:
        if ad:
            ad.action = None
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def bone_ws(name, tail=False):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


set_pose(None)
V = collect()
zs = [p.z for p, b, a, m in V]
z0, z1 = min(zs), max(zs); H = z1 - z0
res = {"H": H}
print("MEAS H", H, z0, z1, min(V, key=lambda q: q[0].z)[1:], max(V, key=lambda q: q[0].z)[1:])
rows = []
TOR = {"Hips", "Spine", "Spine2", "Neck", "Head"}


def zslice(h, sel, label, axis="x"):
    zc = z0 + h * H
    pts = [p for p, b, a, m in V if abs(p.z - zc) < 0.006 * H and sel(p, b, a, m)]
    if not pts:
        return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    w = (max(xs) - min(xs)) / H; d = (max(ys) - min(ys)) / H
    rows.append((label, h, round(w, 3), round(d, 3)))
    return w, d


zslice(0.90, lambda p, b, a, m: True, "斗笠直徑 @0.90")
zslice(0.935, lambda p, b, a, m: True, "斗笠直徑 @0.935（簷緣高度）")
zslice(0.82, lambda p, b, a, m: a and p.y < 0.09 * H, "肩外寬 @0.82（甲）")
zslice(0.80, lambda p, b, a, m: a and p.y < 0.09 * H, "肩外寬 @0.80（甲）")
zslice(0.775, lambda p, b, a, m: a and p.y < 0.09 * H, "肩外寬 @0.775（甲）")
zslice(0.81, lambda p, b, a, m: a and b in TOR, "頸／護喉 @0.81")
zslice(0.865, lambda p, b, a, m: b == "Head" and abs(p.x) < 0.07 * H and "hat" not in m, "頭（兜帽）@0.865")
zslice(0.71, lambda p, b, a, m: a and b in TOR, "胸 @0.71")
zslice(0.58, lambda p, b, a, m: b in TOR and abs(p.y) < 0.093 * H, "腰（含腰帶）@0.58")
zslice(0.50, lambda p, b, a, m: abs(p.x) < 0.2 * H and abs(p.y) < 0.12 * H and (b in TOR or (b or "").startswith(("Thigh", "Robe"))), "臀（含裙甲長擺）@0.50")
zslice(0.15, lambda p, b, a, m: not a, "長擺外擴 @0.15")


def limb(bn, child, label, tvals=(0.3, 0.5, 0.7), allowed=None, Aonly=True):
    A = bone_ws(bn); C = bone_ws(child) if child else bone_ws(bn, tail=True)
    ax = C - A; L = ax.length; u = ax / L
    allowed = allowed or {bn}
    out = []
    for t in tvals:
        P = A + ax * t
        pts = []
        for p, b, a, m in V:
            if b not in allowed or (Aonly and not a):
                continue
            w = p - P
            al = w.dot(u)
            if abs(al) < 0.01 * H:
                pts.append(w - u * al)
        if not pts:
            continue
        n1 = u.cross(Vector((0, 1, 0)))
        if n1.length < 1e-3:
            n1 = u.cross(Vector((1, 0, 0)))
        n1.normalize(); n2 = u.cross(n1).normalized()
        a1 = [q.dot(n1) for q in pts]; a2 = [q.dot(n2) for q in pts]
        w1 = (max(a1) - min(a1)) / H; w2 = (max(a2) - min(a2)) / H
        out.append((t, round(w1, 3), round(w2, 3)))
        rows.append((f"{label} t={t}", None, round(w1, 3), round(w2, 3)))
    res[label] = dict(len=round(L / H, 3), sec=out)


limb("UpperArmL", "ForearmL", "上臂", (0.5,))
limb("ForearmL", "HandL", "前臂", (0.3, 0.5))
limb("ForearmL", "HandL", "手腕／袖口", (0.97,), allowed={"ForearmL", "HandL"})
limb("HandL", None, "手套（掌）", (0.35,), allowed={"HandL"})
limb("ThighL", "ShinL", "大腿", (0.5,))
limb("ThighL", "ShinL", "膝", (0.98,), allowed={"ThighL", "ShinL"})
limb("ShinL", "FootL", "小腿", (0.35,))
limb("ShinL", "FootL", "腳踝", (0.95,), allowed={"ShinL", "FootL"})
# 手（左手全部頂點的 bbox，沿手的軸）
hp = [p for p, b, a, m in V if b == "HandL"]
fp = [p for p, b, a, m in V if b == "FootL"]
if fp:
    ys = [p.y for p in fp]; xs = [p.x for p in fp]
    rows.append(("鐵靴 長×寬", None, round((max(ys) - min(ys)) / H, 3), round((max(xs) - min(xs)) / H, 3)))
# 門板（B 組、Spine2、背後）：沿門板自身軸量
dp = [p for p, b, a, m in V if b == "Spine2" and not a and p.y > 0.09 * H]
if dp:
    zs_ = [p.z for p in dp]; xs = [p.x for p in dp]
    rows.append(("門板 z 範圍（含頂角）", None, round((min(zs_) - z0) / H, 3), round((max(zs_) - z0) / H, 3)))
# 戟：Weapon→Tip 直線 0.02H 內
Wp = bone_ws("Weapon"); Tp = bone_ws("Tip_Weapon")
ax = (Tp - Wp).normalized()
wv = [p for p, b, a, m in V if b == "Weapon"]
proj = [(p - Wp).dot(ax) for p in wv]
perp = [((p - Wp) - ax * (p - Wp).dot(ax)).length for p in wv]
on = [s for s, d in zip(proj, perp) if d < 0.02 * H]
rows.append(("戟 全長（尾→尖）／握點→尖", None, round((max(on) - min(on)) / H, 3), round(max(on) / H, 3)))
rows.append(("戟 斧刃深（離桿最大距離）", None, round(max(perp) / H, 3), None))
for k in ("UpperArmL", "ForearmL", "HandL", "ThighL", "ShinL", "FootL", "Neck", "Head", "Hips"):
    rows.append((f"關節 {k} z", None, round((bone_ws(k).z - z0) / H, 3), round(bone_ws(k).x / H, 3)))
# Idle 第 0 格：站距、前傾
if arm.animation_data and any(a.name.startswith("Idle") for a in bpy.data.actions):
    set_pose("Idle", 0)
    fl, fr = bone_ws("FootL"), bone_ws("FootR")
    hip, sp2 = bone_ws("Hips"), bone_ws("Neck")
    lean = math.degrees(math.atan2(-(sp2.y - hip.y), sp2.z - hip.z))
    hd = bone_ws("Head"); ht = bone_ws("Head", tail=True)
    hlean = math.degrees(math.atan2(-(ht.y - hd.y), ht.z - hd.z))
    th, sh, ft = bone_ws("ThighL"), bone_ws("ShinL"), bone_ws("FootL")
    knee = math.degrees((sh - th).angle(ft - sh))
    rows.append(("Idle 雙腳中心距（3D／橫向）", None, round((fl - fr).length / H, 3), round(abs(fl.x - fr.x) / H, 3)))
    rows.append(("Idle 上身前傾°／頭前傾°", None, round(lean, 1), round(hlean, 1)))
    th, sh, ft = bone_ws("ThighR"), bone_ws("ShinR"), bone_ws("FootR")
    kneeR = math.degrees((sh - th).angle(ft - sh))
    rows.append(("Idle 膝彎°（左／右）", None, round(knee, 1), round(kneeR, 1)))
    tip = bone_ws("Tip_Weapon"); wp = bone_ws("Weapon")
    ang = math.degrees(math.asin(max(-1, min(1, (wp.z - tip.z) / (tip - wp).length))))
    rows.append(("Idle 戟與地面夾角°／戟尖高", None, round(ang, 1), round((tip.z - z0) / H, 3)))
res["rows"] = rows
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print("MEAS", r)
