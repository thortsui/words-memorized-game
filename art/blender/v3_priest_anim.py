"""v3 霜冠祭司：長槍握法（各關鍵姿勢的雙手位置）＋ PhaseShift 分鏡＋光環擺動。由 v3_priest_build.py 呼叫。
座標為主角比例（身高 1.8）單位，Rig 會乘上 U。
Idle（規格 §4）：右手高（約 0.64H、身體右前方）、左手低（約 0.44H、身體左前方），槍在身前斜 35–40°，槍頭在右上、槍尾在左下。
"""
import math
import bpy
from mathutils import Vector, Quaternion
import v3_priest_actions


def _sim_chain(self, ch, data, loop):
    """複製自 soul_humanoid_anim.Rig._sim_chain，加上 ch["floor"]（地面高度，袍擺用）與多一輪約束。"""
    from soul_humanoid_lib import clamp
    from soul_humanoid_anim import rot_min
    names = ch["names"]; anchor = ch["anchor"]; pts0 = ch["pts"]
    r = self.rest
    n = len(pts0)
    seg = [(pts0[i + 1] - pts0[i]).length for i in range(n - 1)]
    d0 = [(pts0[i + 1] - pts0[i]).normalized() for i in range(n - 1)]
    stiff = ch.get("stiff", 0.05); damp = ch.get("damp", 0.90); grav = ch.get("grav", 9.8)
    cols = ch.get("colliders", ()); planar = ch.get("planar", True); floor = ch.get("floor", 0.02)
    sub = 4
    dt = 1.0 / self.fps / sub
    F = len(data)
    seq = [0] * 24 + (list(range(F)) * 3 if loop else list(range(F)))
    start_out = len(seq) - F
    Rt, pos, _ = data[0]

    def tgt(Rt, pos, i):
        return pos[anchor] + Rt[anchor] @ (pts0[i] - r[anchor])
    p = [tgt(Rt, pos, i) for i in range(n)]
    prev = [q.copy() for q in p]
    res = []
    for si, fi in enumerate(seq):
        Rt, pos, _ = data[fi]
        for _s in range(sub):
            p[0] = tgt(Rt, pos, 0); prev[0] = p[0].copy()
            for i in range(1, n):
                vel = (p[i] - prev[i]) * damp
                prev[i] = p[i].copy()
                q = p[i] + vel + Vector((0, 0, -grav * dt * dt))
                q += (tgt(Rt, pos, i) - q) * stiff
                p[i] = q
            for _it in range(4):
                for i in range(1, n):
                    d = p[i] - p[i - 1]
                    L = d.length
                    if L > 1e-6:
                        p[i] = p[i - 1] + d * (seg[i - 1] / L)
                    for (ja, jb, rad) in cols:
                        a = pos[ja].copy(); b = pos[jb].copy()
                        if planar:
                            a.x = p[i].x; b.x = p[i].x
                        ab = b - a
                        t = clamp((p[i] - a).dot(ab) / max(ab.length_squared, 1e-8))
                        c = a + ab * t
                        dd = p[i] - c
                        if dd.length < rad:
                            if dd.length < 1e-6:
                                dd = Rt[anchor] @ Vector(ch.get("out", (0, 1, 0)))
                            p[i] = c + dd.normalized() * rad
                    if p[i].z < floor:
                        p[i].z = floor
        if si >= start_out:
            A = Rt[anchor]
            out = {}
            for i in range(n - 1):
                d = (p[i + 1] - p[i]).normalized()
                out[names[i]] = rot_min(A @ d0[i], d) @ A
            res.append(out)
    return res


def fix_weapon_ground(arm, zmin=0.03):
    """逐片段逐格：長槍槍尾／槍尖低於地面時，繞握點把槍抬起（改寫 Weapon 骨該格的旋轉關鍵格）。"""
    import bpy
    from mathutils import Matrix
    sc = bpy.context.scene
    pb = arm.pose.bones["Weapon"]
    tip = arm.pose.bones["Tip_Weapon"]
    ad = arm.animation_data
    BUTT, TIPS = arm["spear"]
    n_fix = 0
    for tr in ad.nla_tracks:
        act = bpy.data.actions[tr.name]
        ad.action = act
        f0, f1 = map(int, act.frame_range)
        fcs = sorted([c for c in act.fcurves if c.data_path == 'pose.bones["Weapon"].rotation_quaternion'], key=lambda c: c.array_index)
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            M = arm.matrix_world @ pb.matrix
            g = M.translation.copy()
            dvec = ((arm.matrix_world @ tip.head) - g).normalized()
            zb = g.z + dvec.z * BUTT; zt = g.z + dvec.z * TIPS
            if min(zb, zt) >= zmin:
                continue
            hi = (g.z - zmin) / (-BUTT); lo = (zmin - g.z) / TIPS
            dz = (lo + hi) / 2 if lo > hi else min(max(dvec.z, lo), hi)
            hz = Vector((dvec.x, dvec.y, 0.0))
            if hz.length < 1e-6:
                hz = Vector((0, -1, 0))
            dn = (hz.normalized() * math.sqrt(max(0.0, 1 - dz * dz)) + Vector((0, 0, dz))).normalized()
            R = dvec.rotation_difference(dn).to_matrix().to_4x4()
            Mn = Matrix.Translation(g) @ R @ Matrix.Translation(-g) @ M
            pb.matrix = arm.matrix_world.inverted() @ Mn
            bpy.context.view_layer.update()
            q = pb.rotation_quaternion.copy()
            pb.location = (0, 0, 0)
            for c in range(4):
                for k in fcs[c].keyframe_points:
                    if abs(k.co[0] - f) < 0.01:
                        k.co[1] = q[c]
                        break
            n_fix += 1
        for c in fcs:
            c.update()
    ad.action = None
    print("WEAPON ground fix frames", n_fix, flush=True)


def run(rig, only=None):
    import numpy as np
    from soul_humanoid_anim import Rig as _Rig
    _Rig._sim_chain = _sim_chain

    def clampt(Pd, s, tgt, grip):
        """目標超出手臂可及範圍時，沿肩→目標方向拉回（手臂比 v2 短 17%，沿用的姿勢要收斂）。"""
        f = rig._unflatten(np.array(rig._flatten(Pd)))
        Rt, pos, _ = rig.solve(f)
        r = rig.rest
        sh = pos["Spine2"] + Rt["Spine2"] @ (r["UpperArm" + s] - r["Spine2"])
        t = Vector(tgt) * rig.U
        d = t - sh
        mx = (rig.La + rig.Lf) * 0.985 + (0.075 * rig.U if grip else 0.0)
        if d.length > mx:
            t = sh + d.normalized() * mx
        return tuple(t / rig.U)

    BUTT, TIPS = getattr(rig, "spear", (-0.8, 1.2))

    def ground_dir(g, d, zmin=0.05):
        """長槍不可插地：依握點高度限制槍的仰俯角（槍尾、槍尖都 ≥ zmin 公尺）。"""
        d = Vector(d).normalized()
        gz = Vector(g).z * rig.U
        hi = (gz - zmin) / (-BUTT)
        lo = (zmin - gz) / TIPS
        dz = (lo + hi) / 2 if lo > hi else min(max(d.z, lo), hi)
        dz = max(-1.0, min(1.0, dz))
        if abs(dz - d.z) < 1e-6:
            return d
        hz = Vector((d.x, d.y, 0.0))
        if hz.length < 1e-6:
            hz = Vector((0.0, -1.0, 0.0))
        return (hz.normalized() * math.sqrt(max(0.0, 1 - dz * dz)) + Vector((0, 0, dz))).normalized()

    def two(Pd, Rp, Lp, edge_=(0.3, -0.3, -0.9), hintR=None, elL=None):
        Rp = Vector(clampt(Pd, "R", Rp, True)); Lp = Vector(Lp)
        L0 = (Rp - Lp).length
        Lp = Rp - ground_dir(Rp, Rp - Lp) * L0
        d = Rp - Lp
        Pd["ikL"] = 1.0; Pd["gripL"] = -d.length
        if elL:
            Pd["elL"] = elL
        rig.reach(Pd, "R", tuple(Rp), hintR, d.normalized(), Vector(edge_))

    def one(Pd, g, d, edge_, left, hintR=None, hintL=None):
        Pd["ikL"] = 0.0
        g = clampt(Pd, "R", g, True)
        rig.reach(Pd, "R", g, hintR, ground_dir(g, d), Vector(edge_))
        rig.reach(Pd, "L", clampt(Pd, "L", left, False), hintL)

    WP = {
        "idle": lambda p: two(p, (-0.333, -0.24, 1.27), (0.087, -0.25, 0.928), (0.2, -0.5, -0.8), elL=(0.8, 0.3, -0.6)),
        "s_wind": lambda p: two(p, (-0.20, -0.04, 1.08), (-0.16, 0.30, 1.00), (1, 0, 0)),
        "s_wind2": lambda p: two(p, (-0.22, 0.02, 1.10), (-0.18, 0.36, 1.02), (1, 0, 0)),
        "s_hit": lambda p: two(p, (-0.06, -0.70, 1.14), (-0.08, -0.36, 1.10), (1, 0, 0)),
        "s_follow": lambda p: two(p, (-0.04, -0.76, 1.10), (-0.06, -0.42, 1.08), (1, 0, 0)),
        "s_settle": lambda p: two(p, (-0.08, -0.60, 1.08), (-0.08, -0.26, 1.02), (1, 0, 0)),
        "o_up": lambda p: two(p, (-0.10, -0.16, 1.74), (0.04, 0.14, 1.82), (1, 0, 0), elL=(0.8, -0.2, -0.2)),
        "o_up2": lambda p: two(p, (-0.10, -0.10, 1.78), (0.04, 0.20, 1.86), (1, 0, 0), elL=(0.8, -0.2, -0.2)),
        "o_hit": lambda p: two(p, (-0.02, -0.72, 1.00), (0.04, -0.40, 1.22), (1, 0, 0)),
        "o_low": lambda p: two(p, (-0.02, -0.76, 0.92), (0.04, -0.46, 1.16), (1, 0, 0)),
        "o_rec": lambda p: two(p, (-0.08, -0.50, 1.00), (0.10, -0.22, 0.92), (0.3, -0.3, -0.9)),
        "enter0": lambda p: one(p, (-0.28, -0.16, 0.86), (0.02, 0.0, 1), (0, -1, 0), (0.12, -0.22, 1.16)),
        "enter1": lambda p: one(p, (-0.30, -0.20, 0.98), (0.0, -0.1, 1), (0, -1, 0), (0.12, -0.24, 1.20)),
        "enter2": lambda p: two(p, (-0.30, -0.26, 1.26), (0.10, -0.26, 0.93), (0.2, -0.5, -0.8)),
        "hit1": lambda p: two(p, (-0.34, -0.20, 1.34), (-0.02, -0.20, 1.06), (0, -1, 0)),
        "hit2": lambda p: two(p, (-0.30, -0.26, 1.22), (0.20, -0.24, 0.90), (0.2, -0.5, -0.8)),
        "stag1": lambda p: one(p, (-0.50, 0.0, 1.62), (-0.3, 0.5, 0.8), (0, -1, 0), (0.46, -0.18, 1.30)),
        "stag2": lambda p: one(p, (-0.54, 0.16, 1.30), (-0.5, 0.6, 0.5), (0, -1, 0), (0.42, -0.05, 1.12)),
        "stag3": lambda p: one(p, (-0.40, 0.04, 0.80), (-0.12, -0.15, 1), (0, -1, 0), (0.30, -0.10, 0.42), hintL=(0.8, 0.4, 0.0)),
        "stag4": lambda p: two(p, (-0.24, -0.26, 1.10), (0.16, -0.16, 0.82), (0.2, -0.5, -0.8)),
        "roar_gather": lambda p: two(p, (-0.22, -0.30, 1.00), (0.12, -0.22, 0.76), (0.2, -0.5, -0.8)),
        "roar": lambda p: one(p, (-0.56, -0.10, 1.50), (-0.35, -0.25, 0.9), (0, -1, 0), (0.56, -0.12, 1.34), hintL=(0.3, 0.6, -0.7)),
        "roar2": lambda p: one(p, (-0.58, -0.06, 1.54), (-0.40, -0.20, 0.9), (0, -1, 0), (0.58, -0.08, 1.38), hintL=(0.3, 0.6, -0.7)),
        "roar_end": lambda p: two(p, (-0.28, -0.30, 1.20), (0.18, -0.26, 0.88), (0.2, -0.5, -0.8)),
        "die1": lambda p: one(p, (-0.48, -0.05, 1.18), (-0.3, -0.5, 0.6), (0, -1, 0), (0.40, -0.16, 1.20)),
        "kneel": lambda p: one(p, (-0.34, -0.26, 0.46), (0.25, -0.94, -0.03), (1, 0, 0), (0.30, -0.14, 0.46), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
        "kneel2": lambda p: one(p, (-0.36, -0.30, 0.34), (0.28, -0.95, 0.0), (1, 0, 0), (0.30, -0.18, 0.38), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
        "t_pull": lambda p: two(p, (-0.22, -0.26, 1.02), (0.00, 0.14, 1.04), (1, 0, 0)),
        "t_thrust": lambda p: two(p, (-0.06, -0.86, 1.16), (0.00, -0.44, 1.12), (1, 0, 0)),
        "fall": lambda p: one(p, (-0.44, -1.00, 0.10), (-0.2, -0.97, 0.16), (1, 0, 0), (0.36, -0.86, 0.07), hintR=(-0.9, 0.2, 0.3), hintL=(0.9, 0.2, 0.3)),
        # PhaseShift：槍立身側、左手合於胸前禱念 → 升空 → 雙手向兩側張開（掌心向上）→ 緩降、槍尖指向玩家
        "ps_pray": lambda p: one(p, (-0.30, -0.10, 1.08), (0.0, -0.05, 1), (0, -1, 0), (0.0, -0.28, 1.36), hintL=(0.8, 0.2, -0.5)),
        "ps_pray2": lambda p: one(p, (-0.30, -0.10, 1.12), (0.0, -0.05, 1), (0, -1, 0), (0.0, -0.29, 1.42), hintL=(0.8, 0.2, -0.5)),
        "ps_open": lambda p: one(p, (-0.64, -0.18, 1.48), (-0.25, -0.15, 1.0), (0, -1, 0), (0.66, -0.16, 1.52), hintL=(0.2, 0.6, -0.7)),
        "ps_open2": lambda p: one(p, (-0.66, -0.14, 1.52), (-0.30, -0.10, 1.0), (0, -1, 0), (0.68, -0.12, 1.58), hintL=(0.2, 0.6, -0.7)),
        "ps_point": lambda p: two(p, (-0.10, -0.56, 1.28), (-0.06, -0.18, 1.10), (1, 0, 0)),
    }
    FLOAT = 0.235

    def phase(K, T, I, IA, wide):
        fl = dict(legsp=1.0, fLr=(10, 30, 0), fRr=(-45, 30, 0))
        pr = K("ps_pray", hips=(0, 0.02, -0.02), hr=(-3, 0, -6), sp=(-2, 0, -2), ch=(-4, 0, -2), nod=-16)
        pr2 = K("ps_pray2", hips=(0, 0.02, 0.0), hr=(-5, 0, -6), sp=(-3, 0, -2), ch=(-6, 0, -2), nod=-24)
        up = K("ps_pray2", hips=(0, 0.02, FLOAT * 0.7), hr=(-4, 0, -6), sp=(-2, 0, -2), ch=(-5, 0, -2), nod=-26, **fl)
        up2 = K("ps_pray", hips=(0, 0.02, FLOAT), hr=(2, 0, -6), sp=(3, 0, -2), ch=(4, 0, -2), nod=6, **fl)
        op = K("ps_open", hips=(0, 0.03, FLOAT), hr=(-10, 0, -4), sp=(-8, 0, 0), ch=(-12, 0, 0), nod=-28, **fl)
        op2 = K("ps_open2", hips=(0, 0.03, FLOAT + 0.02), hr=(-12, 0, -4), sp=(-9, 0, 0), ch=(-14, 0, 0), nod=-32, **fl)
        op3 = K("ps_open2", hips=(0, 0.03, FLOAT * 0.9), hr=(-8, 0, -6), sp=(-6, 0, -2), ch=(-9, 0, -2), nod=-18, **fl)
        pt = K("ps_point", hips=(0, -0.02, FLOAT * 0.35), hr=(8, 0, -16), sp=(5, 0, -4), ch=(4, 0, -4), nod=-4, legsp=0.4)
        keys = [(0, I), (10, pr, "io"), (18, pr2, "io"), (27, up, "io"), (33, up2, "io"), (36, op, "in3"), (41, op2, "out3"), (50, op3, "io"),
                (62, pt, "io"), (75, IA, "io")]
        return keys, [36]

    def wp(key, p):
        print("WPKEY", key, flush=True)
        WP[key](p)
    v3_priest_actions.build(rig, wp, primary="sweep", slow=1.0, only=only, wide=0.95, phase=phase)
    # 光環在 IdleAggro 中左右緩擺 ±6°（開口朝下的環不能整圈轉），首尾無縫
    act = bpy.data.actions.get("IdleAggro")
    if act:
        fcs = sorted([c for c in act.fcurves if c.data_path == 'pose.bones["HaloSpin"].rotation_quaternion'], key=lambda c: c.array_index)
        if len(fcs) == 4:
            n = len(fcs[0].keyframe_points)
            for i in range(n):
                th = math.radians(6.0) * math.sin(2 * math.pi * i / (n - 1))
                q = Quaternion((0, 1, 0), th)
                for c in range(4):
                    fcs[c].keyframe_points[i].co[1] = q[c]
            for c in fcs:
                c.update()
            print("HALO wobble keyed", n, flush=True)
    rig.arm["spear"] = (BUTT, TIPS)
    fix_weapon_ground(rig.arm)
    fix_mesh_ground(rig.arm)


def fix_mesh_ground(arm, zmin=0.012, max_iter=30):
    """最後一道地面約束（逐片段逐格、看真正蒙皮後的網格）：頂點低於地面且主要權重是布料骨（袍擺 Hem*、袖尾 Sleeve*）時，
    把那根骨頭小步往上掀（骨頭方向轉向 +Z；快垂直時改往外掀），直到網格離地，改寫該格的旋轉關鍵格。
    遊戲是連續時間取樣：再檢查每個半格，半格仍低於地面時，把前後兩格用更高的門檻再抬一次（最多 3 輪）。"""
    import bpy
    import numpy as np
    from mathutils import Matrix
    sc = bpy.context.scene
    mesh = next(o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))
    gn = {g.index: g.name for g in mesh.vertex_groups}
    dom = np.array([gn[max(v.groups, key=lambda g: g.weight).group] if v.groups else "" for v in mesh.data.vertices])
    cloth = np.array([d.startswith(("Hem", "Sleeve")) for d in dom])
    ad = arm.animation_data
    Mw = np.array(mesh.matrix_world)
    tot = 0

    def zs():
        dg = bpy.context.evaluated_depsgraph_get()
        oe = mesh.evaluated_get(dg); me = oe.to_mesh()
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); oe.to_mesh_clear()
        return co.reshape(-1, 3) @ Mw[2, :3] + Mw[2, 3]

    def lift(b, deficit):
        pb = arm.pose.bones[b]
        M = arm.matrix_world @ pb.matrix
        head = M.translation.copy()
        dvec = (arm.matrix_world @ pb.tail) - head
        L = max(dvec.length, 0.15)
        dvec.normalize()
        axis = dvec.cross(Vector((0, 0, 1)))
        if axis.length < 0.15:
            hips = arm.matrix_world @ arm.pose.bones["Hips"].head
            rout = Vector((head.x - hips.x, head.y - hips.y, 0.0))
            if rout.length > 1e-4:
                axis = dvec.cross(rout.normalized())
        if axis.length < 1e-4:
            return
        axis.normalize()
        ang = min(max(deficit / L, 0.006), 0.05)
        R = Matrix.Translation(head) @ Matrix.Rotation(ang, 4, axis) @ Matrix.Translation(-head)
        pb.matrix = arm.matrix_world.inverted() @ R @ M
        pb.location = (0, 0, 0)

    def write(fcm, b, f):
        q = arm.pose.bones[b].rotation_quaternion
        fc4 = fcm.get(b)
        if not fc4 or None in fc4:
            return
        for c in range(4):
            for k in fc4[c].keyframe_points:
                if abs(k.co[0] - f) < 0.01:
                    k.co[1] = q[c]
                    break

    def fix_frame(fcm, f, zt):
        sc.frame_set(f)
        touched = set()
        for it in range(max_iter):
            z = zs()
            bad = (z < zt) & cloth
            if not bad.any():
                break
            for b in set(dom[bad]):
                lift(b, zt - float(z[bad & (dom == b)].min()) + 0.003)
                touched.add(b)
            bpy.context.view_layer.update()
        for b in touched:
            write(fcm, b, f)
        return touched

    for tr in ad.nla_tracks:
        act = bpy.data.actions[tr.name]
        ad.action = act
        f0, f1 = map(int, act.frame_range)
        fcm = {}
        for c in act.fcurves:
            if c.data_path.endswith(".rotation_quaternion"):
                fcm.setdefault(c.data_path.split('"')[1], [None] * 4)[c.array_index] = c
        touched = set()
        for f in range(f0, f1 + 1):
            touched |= fix_frame(fcm, f, zmin)
        for v in fcm.values():
            for c in v:
                if c:
                    c.update()
        for rnd_ in range(3):
            extra = 0.012 * (rnd_ + 1)
            hit = 0
            for f in range(f0, f1):
                sc.frame_set(f, subframe=0.5)
                z = zs()
                bad = (z < 0.0) & cloth
                if not bad.any():
                    continue
                hit += 1
                touched |= fix_frame(fcm, f, zmin + extra)
                touched |= fix_frame(fcm, f + 1, zmin + extra)
                for v in fcm.values():
                    for c in v:
                        if c:
                            c.update()
            if not hit:
                break
        tot += len(touched)
    ad.action = None
    print("CLOTH ground fix bones touched (sum over clips)", tot, flush=True)
