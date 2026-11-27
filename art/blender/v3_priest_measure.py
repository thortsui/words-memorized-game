"""v3 霜冠祭司：照規格 §7 量測（Blender headless，讀 export_raw GLB）。
用法：blender --background --factory-startup --python v3_priest_measure.py -- [glb]
輸出：比例表（目標／實測／誤差%）、Idle 第 0 格槍角度、頭低角度、袖尾最低點。
"""
import bpy, sys, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
path = argv[0] if argv else os.path.join(HERE, "export_raw", "boss_priest.glb")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc = bpy.context.scene


def hidden(o):
    p = o
    while p:
        if p.name.startswith(("P2_", "P3_", "X2_")):   # X2_HipBook（掛在右胯的經書）不算身體輪廓
            return True
        p = p.parent
    return False


def rest():
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def verts(groups=None, thr=0.3):
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH" or hidden(o) or o.name.startswith("Icosphere"):
            continue
        oe = o.evaluated_get(dg); me = oe.to_mesh()
        gi = None
        if groups:
            gi = {o.vertex_groups[g].index for g in groups if g in o.vertex_groups}
            vmesh = o.data
        if not groups:
            mw = o.matrix_world
            co = [mw @ v.co for v in me.vertices]
            gn = {g.index: g.name for g in o.vertex_groups}
            armv = [bool(v.groups) and gn[max(v.groups, key=lambda g: g.weight).group].startswith(ARMB) for v in o.data.vertices]                 if len(o.data.vertices) == len(me.vertices) else [False] * len(me.vertices)
            for e in me.edges:
                EDGES.append((co[e.vertices[0]], co[e.vertices[1]]))
                if not (armv[e.vertices[0]] or armv[e.vertices[1]]):
                    EDGES_B.append((co[e.vertices[0]], co[e.vertices[1]]))
        for v in me.vertices:
            if groups:
                ok = any(g.group in gi and g.weight > thr for g in vmesh.vertices[v.index].groups)
                if not ok:
                    continue
            out.append(o.matrix_world @ v.co)
        oe.to_mesh_clear()
    return out


def clusters(vals, gap):
    vals = sorted(vals)
    out = [[vals[0], vals[0]]]
    for x in vals[1:]:
        if x - out[-1][1] > gap:
            out.append([x, x])
        else:
            out[-1][1] = x
    return out


EDGES = []
EDGES_B = []          # 排除手臂／袖子主導頂點的邊（量袍身截面用；rest 姿勢手臂垂在兩側會黏進袍子的截面）
ARMB = ("UpperArm", "Forearm", "Hand", "Sleeve", "Shoulder")
rest()
V = verts()
z0 = min(v.z for v in V); z1 = max(v.z for v in V); H = z1 - z0
rows = []


def row(name, target, got):
    err = (got - target) / target * 100 if target else 0
    rows.append((name, target, got, err))


def slice_w(hf, xlim=None, allc=False, body=False):
    zc = z0 + hf * H
    # 水平截面：邊與平面的交點（布料網格垂直方向稀疏，只取頂點會漏掉）＋帶內頂點
    band = [] if body else [v for v in V if abs(v.z - zc) < 0.006 * H]
    for a, b in (EDGES_B if body else EDGES):
        if (a.z - zc) * (b.z - zc) < 0 and abs(a.z - b.z) > 1e-9:
            t = (zc - a.z) / (b.z - a.z)
            band.append(a.lerp(b, t))
    band = [v for v in band if xlim is None or abs(v.x) < xlim * H]
    if not band:
        return 0, 0
    cl = clusters([v.x for v in band], 0.012 * H)
    big = max(cl, key=lambda c: c[1] - c[0])
    # 取包含 x=0 的群（身體），沒有就取最寬的
    mid = [c for c in cl if c[0] <= 0 <= c[1]]
    c = mid[0] if mid else big
    if allc:
        c = [cl[0][0], cl[-1][1]]
    ys = [v.y for v in band if c[0] <= v.x <= c[1]]
    return (c[1] - c[0]) / H, (max(ys) - min(ys)) / H


print(f"H(raw) = {H:.3f} m  (遊戲縮放 3.2 m → x{3.2 / H:.3f})")
w, d = slice_w(0.93, 0.15, True); row("0.93H 冰冠展開寬", 0.14, w)
w, d = slice_w(0.83); row("0.83H 兜帽外寬", 0.12, w); row("0.83H 兜帽深", 0.13, d)
w, d = slice_w(0.72, 0.13); row("0.72H 肩寬（|x|<0.13H）", 0.22, w)
w, d = slice_w(0.66, 0.10); row("0.66H 胸寬（披肩下袍身）", 0.19, w)
w, d = slice_w(0.545, 0.15, body=True); row("0.545H 腰寬（袍身）", 0.14, w); row("0.545H 腰厚", 0.10, d)
w, d = slice_w(0.47, 0.2, body=True); row("0.47H 臀寬（袍身）", 0.20, w)
w, d = slice_w(0.30, 0.25, True, body=True); row("0.30H 袍寬（袍身）", 0.30, w)
w, d = slice_w(0.03, None, True, body=True); row("0.03H 下擺寬", 0.37, w); row("0.03H 下擺深", 0.28, d)
# 手腕：前臂骨 t=0.85，距骨 0.02H 內（排除袖子）
B = {b.name: (arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local) for b in arm.data.bones}
for s in "L":
    a = B["Forearm" + s][0]; b = B["Hand" + s][0]
    u = (b - a).normalized(); P = a + (b - a) * 0.85   # 0.95 處已進到手背（手背從腕前 0.005H 開始），改量 0.85
    pts = []
    for v in V:
        w_ = v - P; al = w_.dot(u)
        if abs(al) < 0.006 * H:
            pr = w_ - u * al
            if pr.length < 0.02 * H:
                pts.append(pr)
    if pts:
        row("手腕直徑（前臂 t=0.85）", 0.025, 2 * sum(p.length for p in pts) / len(pts) / H)
    row("上臂長", 0.13, (B["Forearm" + s][0] - B["UpperArm" + s][0]).length / H)      # 關節到關節（匯入器猜的骨尾不可靠）
    row("前臂長", 0.11, (B["Hand" + s][0] - B["Forearm" + s][0]).length / H)
    row("肩關節間距", 0.15, 2 * B["UpperArm" + s][0].x / H)
    row("膝高", 0.27, (B["Shin" + s][0].z - z0) / H)
# 長槍
a = B["Weapon"][0]; t = B["Tip_Weapon"][0]
u = (t - a).normalized()
pr = [(v - a).dot(u) for v in V if ((v - a) - u * (v - a).dot(u)).length < 0.015 * H]
row("長槍全長", 1.05, (max(pr) - min(pr)) / H)
print(f"{'項目':<22}{'目標':>8}{'實測':>8}{'誤差%':>8}")
for n, tg, g, e in rows:
    print(f"{n:<22}{tg:>8.3f}{g:>8.3f}{e:>+8.1f}{'  <-- 超過 10%' if abs(e) > 10 else ''}")
# Idle 第 0 格
act = next((a for a in bpy.data.actions if a.name in ("Idle", "Idle_BossPriest") or a.name.startswith("Idle_Boss")), None)
if act:
    arm.animation_data_create()
    arm.animation_data.action = act
    sc.frame_set(0)
    bpy.context.view_layer.update()
    m = arm.matrix_world
    wp = m @ arm.pose.bones["Weapon"].head; tp = m @ arm.pose.bones["Tip_Weapon"].head
    d = (tp - wp).normalized()
    ang = math.degrees(math.asin(abs(d.z)))
    hd = (m @ arm.pose.bones["Head"].tail - m @ arm.pose.bones["Head"].head).normalized()
    pitch = math.degrees(math.atan2(-hd.y, hd.z))
    sl = verts(["Sleeve2L", "Sleeve2R", "Sleeve1L", "Sleeve1R"], 0.2)
    lows = {}
    for side, sg in (("L", 1), ("R", -1)):
        q = [v for v in sl if v.x * sg > 0]
        if q:
            lows[side] = (min(v.z for v in q) - z0) / H
    Vi = verts()
    lo = min(Vi, key=lambda v: v.z)
    zi = lo.z
    print("Idle f0 最低頂點", tuple(round(c, 3) for c in lo))
    butt = None
    print(f"Idle f0：槍與水平夾角 {ang:.1f}°（目標 35–40）  頭前傾 {pitch:.1f}°（目標 5–8）  袖尾最低 {lows}（目標 0.27–0.33H）  最低點 z={zi:.3f}")
    fl = m @ arm.pose.bones["FootL"].head; fr = m @ arm.pose.bones["FootR"].head
    print(f"Idle f0：站距（左右）{abs(fl.x - fr.x) / H:.3f}H  （3D）{(fl - fr).length / H:.3f}H（目標 0.18–0.22）  槍尖高 {(tp.z - z0) / H:.3f}H")
