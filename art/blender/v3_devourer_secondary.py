"""v3 噬語魔王：逐格的次級動作與「不入地」處理（在 Rig 產生主動作之後執行，直接改寫各片段的骨頭關鍵格）。

  - 披風 3 條鏈（CapeL／CapeC／CapeR，各 4 節）與前擺鏈（TabardF1–3）：自寫 Verlet——跟隨錨骨的剛性目標＋慣性＋輕重力，
    骨長約束、身體／腿的膠囊碰撞、地面約束（關節 z ≥ 地面高度），所以下蹲、前傾時下段會折起貼地而不是整片旋轉插進地裡。
  - InkTide（三階墨潮的骨）：跟骨盆水平位置與偏航，但高度最多只下降到墨潮最低點貼地（墨潮永不入地）。
  - WordsA/B/C（劍外符字環）：跟著劍身中心移動，但保持世界水平；環的最低點 ≥ 地面。
  - WingL/WingR（二階紙翼）：根部跟 Spine2，方向保持世界固定（左右對稱張開），只加緩慢開合；轉階段爆發時從收攏彈開。
  - 最後逐格算網格最低點，剩下的小穿地（≤ LIFT_MAX）用骨盆整體抬高修正。
"""
import bpy, math
import numpy as np
from mathutils import Vector, Quaternion, Matrix

FPS = 30
LIFT_MAX = 0.18          # 只在網格最低點 < 0 的格才抬（實際只有 Die 倒地需要 >6 cm）


def _set_curve(act, path, idx, vals, group, f0):
    fc = act.fcurves.find(path, index=idx)
    if fc is not None:
        act.fcurves.remove(fc)
    fc = act.fcurves.new(path, index=idx, action_group=group)
    n = len(vals)
    fc.keyframe_points.add(n)
    co = np.empty(n * 2)
    co[0::2] = np.arange(n, dtype=float) + f0
    co[1::2] = vals
    fc.keyframe_points.foreach_set("co", co)
    fc.keyframe_points.foreach_set("interpolation", [1] * n)
    fc.update()


def _write_quats(act, bn, qs, f0):
    arr = np.array([[q.w, q.x, q.y, q.z] for q in qs])
    for k in range(1, len(arr)):
        if np.dot(arr[k], arr[k - 1]) < 0:
            arr[k] *= -1
    for c in range(4):
        _set_curve(act, f'pose.bones["{bn}"].rotation_quaternion', c, arr[:, c], bn, f0)


def _write_locs(act, bn, ls, f0):
    arr = np.array([list(v) for v in ls])
    for c in range(3):
        _set_curve(act, f'pose.bones["{bn}"].location', c, arr[:, c], bn, f0)


def _cap_push(p, a, b, r):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    q = a + ab * t
    d = p - q
    if d.length < r:
        if d.length < 1e-6:
            d = Vector((0, 1, 0))
        return q + d.normalized() * r
    return p


class Chain:
    def __init__(self, arm, names, anchor, stiff, zmin, gravity=0.004, damp=0.86, zfollow=None):
        self.names = names; self.anchor = anchor
        bones = arm.data.bones
        self.Ar = bones[anchor].matrix_local.copy()
        self.Br = [bones[n].matrix_local.copy() for n in names]
        self.J = [bones[n].head_local.copy() for n in names] + [bones[names[-1]].tail_local.copy()]
        self.L = [(self.J[k + 1] - self.J[k]).length for k in range(len(names))]
        self.stiff = stiff; self.zmin = zmin; self.g = gravity; self.damp = damp
        self.zf = zfollow or [1.0] * len(self.J)

    def targets(self, MA):
        """剛性跟隨錨骨；但下段關節的高度只跟一部分（身體下蹲時拖地的下段留在原高度，而不是整片插進地裡）。"""
        Ai = self.Ar.inverted()
        out = []
        for j, zf in zip(self.J, self.zf):
            t = (MA @ Ai @ j.to_4d()).to_3d()
            if zf < 1.0:
                t.z = j.z + (t.z - j.z) * zf if t.z < j.z else t.z
            out.append(t)
        return out

    def step(self, p, pp, T, colliders, iters=4):
        n = len(p)
        new = [T[0].copy()]
        for k in range(1, n):
            vel = (p[k] - pp[k]) * self.damp
            q = p[k] + vel + Vector((0, 0, -self.g))
            q += (T[k] - q) * self.stiff[k - 1]
            new.append(q)
        for _ in range(iters):
            for k in range(1, n):
                d = new[k] - new[k - 1]
                if d.length > 1e-6:
                    new[k] = new[k - 1] + d.normalized() * self.L[k - 1]
                for a, b, r in colliders:
                    new[k] = _cap_push(new[k], a, b, r)
                if new[k].z < self.zmin[k]:
                    new[k].z = self.zmin[k]
        return new

    def rotations(self, MA, pts):
        P, Pr = MA, self.Ar
        out = []
        for k, Br in enumerate(self.Br):
            M0 = P @ Pr.inverted() @ Br
            head = M0.to_translation()
            R0 = M0.to_3x3().normalized()
            Rr = Br.to_3x3().normalized()
            yr = Rr.col[1]
            d = pts[k + 1] - head
            if d.length < 1e-6:
                d = R0.col[1]
            # 以「靜止時的世界方向」做最小旋轉（不繼承父骨的扭轉，側邊遠離鏈軸的書頁才不會被扭到地下）
            qw = yr.rotation_difference(d.normalized())
            ql = (R0.inverted() @ qw.to_matrix() @ Rr).to_quaternion()
            out.append(ql)
            P = M0 @ ql.to_matrix().to_4x4()
            Pr = Br
        return out


def fix_weapon(arm, act, frames, tip_rest, margin=0.03, max_deg=35.0):
    """劍尖低於地面的格：繞握點把劍往外撥（手腕小轉），讓刃最低點 ≥ 0。回傳修正格數。"""
    sc = bpy.context.scene
    pb = arm.pose.bones["Weapon"]
    Wr = arm.data.bones["Weapon"].matrix_local
    tl = (Wr.inverted() @ tip_rest.to_4d()).to_3d()
    path = 'pose.bones["Weapon"].rotation_quaternion'
    fcs = [act.fcurves.find(path, index=c) for c in range(4)]
    if any(f is None for f in fcs):
        return 0
    nfix = 0
    for i, f in enumerate(frames):
        sc.frame_set(f)
        M = pb.matrix.copy()
        tip = (M @ tl.to_4d()).to_3d()
        if tip.z >= margin:
            continue
        g = M.to_translation()
        d = (tip - g).normalized()
        ax = d.cross(Vector((0, 0, 1)))
        if ax.length < 1e-4:
            ax = Vector((1, 0, 0))
        ax.normalize()
        best = None
        for deg in np.linspace(2, max_deg, 18):
            q = Quaternion(ax, math.radians(deg))
            t2 = g + q @ (tip - g)
            if t2.z >= margin:
                best = q; break
        if best is None:
            best = Quaternion(ax, math.radians(max_deg))
        R0 = M.to_3x3().normalized()
        ql = (R0.inverted() @ best.to_matrix() @ R0).to_quaternion()
        qo = Quaternion([fc.evaluate(f) for fc in fcs])
        qn = qo @ ql
        for c, fc in enumerate(fcs):
            kp = fc.keyframe_points[i]
            kp.co.y = qn[c]
        nfix += 1
    for fc in fcs:
        fc.update()
    return nfix


def run(arm, rig, ink_obj=None, words=None, wing_flap=True, log=print, tip_rest=None):
    sc = bpy.context.scene
    ad = arm.animation_data
    bones = arm.data.bones
    pbs = arm.pose.bones
    caps = [n for n in ("CapeRF", "CapeR", "CapeC", "CapeL", "CapeLF")]
    chains = []
    for c in caps:
        names = [f"{c}{k}" for k in range(1, 5) if f"{c}{k}" in bones]
        if names:
            chains.append(Chain(arm, names, "Spine2", stiff=[0.45, 0.22, 0.14, 0.10], zmin=[0, 0.05, 0.05, 0.05, 0.05],
                                zfollow=[1.0, 1.0, 0.55, 0.25, 0.05]))
    tnames = [n for n in ("TabardF1", "TabardF2", "TabardF3") if n in bones]
    if tnames:
        chains.append(Chain(arm, tnames, "Hips", stiff=[0.30, 0.15, 0.10], zmin=[0, 0.16, 0.16, 0.20], gravity=0.006, zfollow=[1.0, 1.0, 0.6, 0.3]))
    ink_drop = 0.0
    if ink_obj is not None:
        zs = [(ink_obj.matrix_world @ v.co).z for v in ink_obj.data.vertices]
        ink_drop = max(0.0, min(zs) - 0.01)
        log(f"SECONDARY ink min z {min(zs):.3f} → 骨盆下沉時墨潮最多下降 {ink_drop:.3f} m")
    wmargin = {}
    for nm, (bn, obj) in (words or {}).items():
        zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
        wmargin[bn] = bones[bn].head_local.z - min(zs) + 0.01
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and any(m.type == "ARMATURE" for m in o.modifiers)]
    report = []
    for tr in ad.nla_tracks:
        act = bpy.data.actions[tr.name]
        ad.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        N = f1 - f0 + 1
        loop = rig.meta.get(tr.name, {}).get("loop", False)
        frames = list(range(f0, f1 + 1))
        if tip_rest is not None:
            nf = fix_weapon(arm, act, frames, tip_rest)
            if nf:
                log(f"SECONDARY {tr.name}: 劍尖入地修正 {nf} 格")
        # 錨骨與碰撞體（每格）
        MA = {}
        col = []
        for f in frames:
            sc.frame_set(f)
            m = {n: pbs[n].matrix.copy() for n in ("Spine2", "Hips", "Weapon", "Spine")}
            MA[f] = m
            hp = m["Hips"].to_translation(); s2 = m["Spine2"].to_translation()
            cl = [(hp, s2, 0.40)]
            for s in "LR":
                t = pbs["Thigh" + s].head.copy(); kn = pbs["Shin" + s].head.copy(); ft = pbs["Foot" + s].head.copy()
                cl += [(t, kn, 0.22), (kn, ft, 0.17)]
            col.append(cl)
        # 鏈模擬（循環片段跑兩遍，取第二遍）
        res = {id(c): [None] * N for c in chains}
        for c in chains:
            T0 = c.targets(MA[f0][c.anchor])
            p = [t.copy() for t in T0]; pp = [t.copy() for t in T0]
            for _ in range(40):
                q = c.step(p, pp, T0, col[0]); pp, p = p, q
                pp = [x.copy() for x in p]
            for rep in range(2 if loop else 1):
                for i, f in enumerate(frames):
                    T = c.targets(MA[f][c.anchor])
                    q = c.step(p, pp, T, col[i]); pp, p = p, q
                    res[id(c)][i] = [x.copy() for x in p]
            if loop:     # 收尾 6 格往第一格靠，循環不跳
                for k in range(6):
                    w = (k + 1) / 7
                    i = N - 6 + k
                    res[id(c)][i] = [a.lerp(b, w) for a, b in zip(res[id(c)][i], res[id(c)][0])]
            qs = [c.rotations(MA[f][c.anchor], res[id(c)][i]) for i, f in enumerate(frames)]
            for k, bn in enumerate(c.names):
                _write_quats(act, bn, [q[k] for q in qs], f0)
        # 墨潮骨（高度最多降到貼地）與披風地面骨（高度固定）：跟骨盆的水平位置與偏航
        for gbn, drop in (("InkTide", ink_drop), ("CapeGround", 0.0)):
            if gbn not in bones:
                continue
            Br = bones[gbn].matrix_local
            Rr = Br.to_3x3().normalized(); h0 = Br.to_translation()
            Hr = bones["Hips"].matrix_local.to_3x3().normalized()
            hz0 = bones["Hips"].head_local.z
            locs, qs = [], []
            for f in frames:
                Mh = MA[f]["Hips"]
                hp = Mh.to_translation()
                Rw = Mh.to_3x3().normalized() @ Hr.inverted()
                fw = Rw @ Vector((0, -1, 0)); fw.z = 0
                yaw = math.atan2(-fw.x, -fw.y) if fw.length > 1e-6 else 0.0
                qy = Quaternion((0, 0, 1), yaw * (1.0 if gbn == "InkTide" else 0.6))
                tgt = Vector((hp.x, hp.y, h0.z + min(0.0, max(hp.z - hz0, -drop)) + max(0.0, hp.z - hz0) * (1 if gbn == "InkTide" else 0)))
                locs.append(Rr.inverted() @ (tgt - h0))
                qs.append((Rr.inverted() @ qy.to_matrix() @ Rr).to_quaternion())
            _write_locs(act, gbn, locs, f0); _write_quats(act, gbn, qs, f0)
        # 符字環骨：跟劍、保持水平、不入地
        for bn, mg in wmargin.items():
            Br = bones[bn].matrix_local; Wr = bones["Weapon"].matrix_local
            Rb = Br.to_3x3().normalized()
            locs, qs = [], []
            for f in frames:
                M0 = MA[f]["Weapon"] @ Wr.inverted() @ Br
                R0 = M0.to_3x3().normalized(); h0 = M0.to_translation()
                tgt = h0.copy(); tgt.z = max(tgt.z, mg)
                locs.append(R0.inverted() @ (tgt - h0))
                qs.append((R0.inverted() @ Rb).to_quaternion())
            _write_locs(act, bn, locs, f0); _write_quats(act, bn, qs, f0)
        # 紙翼：方向世界固定（左右對稱），緩慢開合；轉階段時從收攏彈開
        if wing_flap and "WingL" in bones:
            t = np.arange(N) / FPS
            dur = max((N - 1) / FPS, 1e-3)
            cyc = max(1, round(dur / 2.4)) if loop else dur / 2.4
            flap = 0.08 * np.sin(2 * math.pi * cyc * t / dur)
            if tr.name in ("PhaseShift", "PhaseShift2"):
                Tb = 1.15 if tr.name == "PhaseShift" else 1.25
                flap = flap - 0.9 * np.clip(1 - (t - Tb) / 0.3, 0, 1) * (t >= Tb)
            for side, bn in ((1, "WingL"), (-1, "WingR")):
                Br = bones[bn].matrix_local; Sr = bones["Spine2"].matrix_local
                Rb = Br.to_3x3().normalized()
                qs = []
                for i, f in enumerate(frames):
                    M0 = MA[f]["Spine2"] @ Sr.inverted() @ Br
                    R0 = M0.to_3x3().normalized()
                    fw = Quaternion((0, 1, 0), float(side * flap[i])) @ Quaternion((0, 0, 1), float(side * 0.5 * flap[i]))
                    qs.append((R0.inverted() @ fw.to_matrix() @ Rb).to_quaternion())
                _write_quats(act, bn, qs, f0)
                # 紙翼骨縮放：所有片段都 key 成 1；Die 在倒地前（約 1.25–1.75 秒）收成 0，二階一擊致死也不會翼尖入地
                sc_ = np.ones(N)
                if tr.name == "Die":
                    t0, t1 = 1.25, 1.75
                    k = np.clip((t - t0) / (t1 - t0), 0, 1)
                    sc_ = np.maximum(1e-3, 1 - k * k * (3 - 2 * k))
                for c in range(3):
                    _set_curve(act, f'pose.bones["{bn}"].scale', c, sc_, bn, f0)
        # 剩下的小穿地：逐格網格最低點 → 骨盆整體抬高（≤ LIFT_MAX）
        dg = bpy.context.evaluated_depsgraph_get()
        mins = []
        for f in frames:
            sc.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            mz = 9.0
            for o in meshes:
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
                if len(co):
                    mz = min(mz, co[2::3].min() + o.matrix_world.translation.z)
                ev.to_mesh_clear()
            mins.append(mz)
        mins = np.array(mins)
        lift = np.clip(-mins, 0, LIFT_MAX)
        if lift.max() > 1e-4:
            k = np.ones(5) / 5
            lift = np.maximum(lift, np.convolve(np.pad(lift, 2, mode="edge"), k, mode="valid"))
            Hr = bones["Hips"].matrix_local.to_3x3().normalized()
            dl = Hr.inverted() @ Vector((0, 0, 1))
            for c in range(3):
                fc = act.fcurves.find('pose.bones["Hips"].location', index=c)
                if fc is None:
                    continue
                vals = np.empty(len(fc.keyframe_points) * 2); fc.keyframe_points.foreach_get("co", vals)
                ys = vals[1::2]
                ys[:len(lift)] += lift[:len(ys)] * dl[c]
                vals[1::2] = ys
                fc.keyframe_points.foreach_set("co", vals); fc.update()
        report.append((tr.name, float(mins.min()), float(lift.max())))
        log(f"SECONDARY {tr.name}: frames {N} mesh-min {mins.min():+.3f} m, hips lift max {lift.max():.3f} m")
    ad.action = None
    return report
