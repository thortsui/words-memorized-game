"""魂系人形角色：手刻關鍵姿勢 → 逐格動作。

姿勢以高階參數描述（世界／模型軸，-Y 為前、+X 為角色左、+Z 為上）：
  hips       骨盆位移（公尺，會乘上身高比例 U）
  hips_r     骨盆旋轉 (x 前傾, y 向左側傾, z 向左轉)，單位度
  spine/chest/neck/head   各節相對上一節的旋轉（同上）
  uaR/faR/uaL/faL         上臂／前臂的指向（預設在胸腔座標；用 W(...) 包起來表示世界座標）
  hR/hL      手的朝向：(握持物軸向, 指節方向)；None 表示順著前臂。HW(刃向, 刃口) 表示世界座標
  ikL        左手握在武器上的權重（0~1）；gripL：握點離武器骨原點的距離（公尺×U）；elL：左肘提示方向
  fL/fR      腳踝目標相對站姿的位移（世界；公尺×U）；fLr/fRr：(yaw, pitch 腳尖朝下為正, roll)
  legsp      0＝腳目標在世界座標（定地），1＝腳目標跟著骨盆（翻滾／倒地）
  kL/kR      膝蓋方向提示的附加向量（骨盆座標）
  wpn        武器骨相對手的旋轉
關鍵格之間用單調三次插值（PCHIP，極值處速度為零、通過點保持速度連續），每格解一次 FK／IK 後寫成四元數關鍵格。
"""
import bpy, math
import numpy as np
from mathutils import Vector, Quaternion
from soul_humanoid_lib import E, frame_rot, rot_min, FWD, X, Y, Z, clamp, lerp


class W(tuple):
    """世界座標的方向向量。"""
    def __new__(cls, *a):
        return super().__new__(cls, a[0] if len(a) == 1 else a)


class HW(tuple):
    """世界座標的手部朝向 (軸向, 指節方向)。"""
    def __new__(cls, a, b):
        return super().__new__(cls, (a, b))


def ik2(P, A, L1, L2, hint):
    d = A - P
    dist = d.length
    n = d / dist if dist > 1e-6 else Vector((0, 0, -1))
    dc = min(max(dist, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.9995)
    a = (L1 * L1 - L2 * L2 + dc * dc) / (2 * dc)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    perp = hint - n * hint.dot(n)
    if perp.length < 1e-5:
        perp = n.orthogonal()
    perp.normalize()
    return P + n * a + perp * h, P + n * dc, perp, n, dist - dc


def pchip(xs, Yv, xq, loop=False):
    xs = np.asarray(xs, float); Yv = np.asarray(Yv, float)
    K = len(xs)
    if K == 1:
        return np.repeat(Yv, len(xq), axis=0)
    h = np.diff(xs); d = np.diff(Yv, axis=0) / h[:, None]
    m = np.zeros_like(Yv)

    def slope(dl, dr, hl, hr):
        w1 = 2 * hr + hl; w2 = hr + 2 * hl
        with np.errstate(divide="ignore", invalid="ignore"):
            v = (w1 + w2) / (w1 / dl + w2 / dr)
        v[(dl * dr) <= 0] = 0.0
        return np.nan_to_num(v)
    for k in range(1, K - 1):
        m[k] = slope(d[k - 1], d[k], h[k - 1], h[k])
    if loop and K > 2:
        m[0] = m[-1] = slope(d[-1], d[0], h[-1], h[0])
    out = np.zeros((len(xq), Yv.shape[1]))
    for i, x in enumerate(xq):
        k = int(np.clip(np.searchsorted(xs, x, side="right") - 1, 0, K - 2))
        s = (x - xs[k]) / h[k]
        s = min(max(s, 0.0), 1.0)
        s2, s3 = s * s, s * s * s
        out[i] = ((2 * s3 - 3 * s2 + 1) * Yv[k] + (s3 - 2 * s2 + s) * h[k] * m[k] +
                  (-2 * s3 + 3 * s2) * Yv[k + 1] + (s3 - s2) * h[k] * m[k + 1])
    return out


LAYOUT = [("hips", 3, "v"), ("hips_r", 4, "q"), ("spine", 4, "q"), ("chest", 4, "q"), ("neck", 4, "q"), ("head", 4, "q"),
          ("uaR", 3, "d"), ("faR", 3, "d"), ("hR", 4, "q"), ("uaL", 3, "d"), ("faL", 3, "d"), ("hL", 4, "q"),
          ("ikL", 1, "s"), ("gripL", 1, "s"), ("elL", 3, "d"),
          ("fL", 3, "v"), ("fLr", 4, "q"), ("fR", 3, "v"), ("fRr", 4, "q"), ("legsp", 1, "s"),
          ("kL", 3, "v"), ("kR", 3, "v"), ("wpn", 4, "q")]


class Rig:
    def __init__(self, arm, body, chains=(), grip_default=0.4, fps=30):
        self.arm = arm; self.body = body; self.U = body.U; self.fps = fps
        bones = arm.data.bones
        self.names = [b.name for b in bones]
        self.rest = {b.name: b.head_local.copy() for b in bones}
        self.tailp = {b.name: b.tail_local.copy() for b in bones}
        self.Bq = {b.name: b.matrix_local.to_quaternion() for b in bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        r = self.rest
        self.ua0 = {}; self.fa0 = {}; self.h0 = {}; self.b0 = {}; self.e0 = {}
        self.t0 = {}; self.s0 = {}; self.hk0 = {}
        for s in "LR":
            self.ua0[s] = (r["Forearm" + s] - r["UpperArm" + s]).normalized()
            self.fa0[s] = (r["Hand" + s] - r["Forearm" + s]).normalized()
            self.h0[s] = self.ua0[s].cross(self.fa0[s]).normalized()
            hv, ha = body.hand_v.copy(), body.hand_a.copy()
            if s == "R":
                hv.x = -hv.x; ha.x = -ha.x
            self.b0[s] = hv; self.e0[s] = ha
            P0, K0, A0 = r["Thigh" + s], r["Shin" + s], r["Foot" + s]
            n0 = (A0 - P0).normalized()
            perp0 = (K0 - P0) - n0 * (K0 - P0).dot(n0)
            perp0.normalize()
            self.t0[s] = (K0 - P0).normalized(); self.s0[s] = (A0 - K0).normalized()
            self.hk0[s] = perp0.cross(n0).normalized()
        self.La = (r["ForearmL"] - r["UpperArmL"]).length
        self.Lf = (r["HandL"] - r["ForearmL"]).length
        self.Lt = (r["ShinL"] - r["ThighL"]).length
        self.Ls = (r["FootL"] - r["ShinL"]).length
        self.has_weapon = "Weapon" in r
        if self.has_weapon:
            self.w0 = (self.tailp["Weapon"] - r["Weapon"]).normalized()
        self.gripcL = body.grip_c.copy()
        self.toe0 = {s: body.j["Toe" + s].copy() for s in "LR"}
        self.chains = list(chains)
        self.tip_len = 1.0
        self.base = dict(hips=(0, 0, 0), hips_r=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), neck=(0, 0, 0), head=(0, 0, 0),
                         uaR=tuple(self.ua0["R"]), faR=tuple(self.fa0["R"]), hR=None,
                         uaL=tuple(self.ua0["L"]), faL=tuple(self.fa0["L"]), hL=None,
                         ikL=0.0, gripL=grip_default, elL=(0.5, 0.35, -1.0),
                         fL=(0, 0, 0), fLr=(0, 0, 0), fR=(0, 0, 0), fRr=(0, 0, 0), legsp=0.0,
                         kL=(0, 0, 0), kR=(0, 0, 0), wpn=(0, 0, 0))
        self.report = []

    def P(self, *a, **kw):
        d = dict(a[0]) if a else dict(self.base)
        d.update(kw)
        return d

    # ---- 編寫姿勢用的小工具：把手放到指定位置（兩節 IK），結果寫回姿勢參數
    def reach(self, Pd, s, target, hint=None, blade=None, edge=None):
        """target：世界座標（公尺×U）。有 blade／edge 時 target 是握點中心（武器骨原點），否則是手腕。"""
        r = self.rest
        f = self._unflatten(np.array(self._flatten(Pd)))
        Rt, pos, _ = self.solve(f)
        C = Rt["Spine2"]
        tgt = Vector(target) * self.U
        if hint is None:
            hint = (-0.5, 0.6, -0.6) if s == "R" else (0.5, 0.6, -0.6)
        hint = Vector(hint)
        if blade is not None:
            Rh = frame_rot(self.b0[s], self.e0[s], Vector(blade), Vector(edge))
            gc = self.gripcL.copy()
            if s == "R":
                gc.x = -gc.x
            wrist = tgt - Rh @ (gc - r["Hand" + s])
        else:
            wrist = tgt
        u = (pos["Forearm" + s] - pos["UpperArm" + s]).normalized()
        for _ in range(3):
            Rsh = C.slerp(rot_min(C @ self.ua0[s], u) @ C, 0.18)
            sh = pos["Spine2"] + C @ (r["Shoulder" + s] - r["Spine2"]) + Rsh @ (r["UpperArm" + s] - r["Shoulder" + s])
            K, A2, perp, n, ov = ik2(sh, wrist, self.La, self.Lf, hint)
            u = (K - sh).normalized()
        fd = (A2 - K).normalized()
        if ov > 0.02:
            print(f"  reach {s}: 目標超出手臂長度 {ov * 100:.0f}cm", flush=True)
        Pd["ua" + s] = W(*u); Pd["fa" + s] = W(*fd)
        if blade is not None:
            Pd["h" + s] = HW(tuple(blade), tuple(edge))
        return Pd

    # ---- 關鍵姿勢 → 數值向量
    def _arm_frames(self, s, u, f, C):
        u0, f0, h0 = self.ua0[s], self.fa0[s], self.h0[s]
        hraw = u.cross(f)
        hfb = rot_min(C @ u0, u) @ (C @ h0)
        h = hraw + hfb * 0.08
        h.normalize()
        return frame_rot(u0, h0, u, h), frame_rot(f0, h0, f, h)

    def _flatten(self, Pd):
        U = self.U
        qH = E(*Pd["hips_r"]); qS = E(*Pd["spine"]); qC = E(*Pd["chest"])
        C = qH @ qS @ qC
        Ci = C.inverted()
        out = {}
        out["hips"] = Vector(Pd["hips"]) * U
        out["hips_r"] = qH; out["spine"] = qS; out["chest"] = qC
        out["neck"] = E(*Pd["neck"]); out["head"] = E(*Pd["head"])
        for s in "RL":
            for k in ("ua", "fa"):
                v = Pd[k + s]
                vec = Vector(v).normalized()
                if isinstance(v, W):
                    vec = Ci @ vec
                out[k + s] = vec
            hsp = Pd["h" + s]
            if hsp is None:
                _, RF = self._arm_frames(s, out["ua" + s], out["fa" + s], Quaternion())
                out["h" + s] = RF
            else:
                a, b = Vector(hsp[0]), Vector(hsp[1])
                if isinstance(hsp, HW):
                    a = Ci @ a; b = Ci @ b
                out["h" + s] = frame_rot(self.b0[s], self.e0[s], a, b)
        out["ikL"] = Pd["ikL"]; out["gripL"] = Pd["gripL"] * U
        out["elL"] = Vector(Pd["elL"]).normalized()
        for s in "LR":
            out["f" + s] = Vector(Pd["f" + s]) * U
            yaw, pitch, roll = Pd[f"f{s}r"]
            out[f"f{s}r"] = E(pitch, roll, yaw)
            out["k" + s] = Vector(Pd["k" + s])
        out["legsp"] = Pd["legsp"]
        out["wpn"] = E(*Pd["wpn"])
        flat = []
        for n, size, kind in LAYOUT:
            v = out[n]
            if kind == "s":
                flat.append(float(v))
            else:
                flat.extend(list(v))
        return flat

    @staticmethod
    def _unflatten(row):
        d = {}
        i = 0
        for n, size, kind in LAYOUT:
            seg = [float(x) for x in row[i:i + size]]
            i += size
            if kind == "s":
                d[n] = float(seg[0])
            elif kind == "q":
                q = Quaternion(seg)
                q.normalize()
                d[n] = q
            elif kind == "d":
                v = Vector(seg)
                if v.length < 1e-6:
                    v = Vector((0, 0, -1))
                d[n] = v.normalized()
            else:
                d[n] = Vector(seg)
        return d

    # ---- 每格求解
    def solve(self, f):
        r = self.rest
        Rt = {"Root": Quaternion()}; pos = {"Root": Vector((0, 0, 0))}
        Rt["Hips"] = f["hips_r"]; pos["Hips"] = r["Hips"] + f["hips"]

        def child(b, p):
            pos[b] = pos[p] + Rt[p] @ (r[b] - r[p])
        child("Spine", "Hips"); Rt["Spine"] = Rt["Hips"] @ f["spine"]
        child("Spine2", "Spine"); Rt["Spine2"] = Rt["Spine"] @ f["chest"]
        child("Neck", "Spine2"); Rt["Neck"] = Rt["Spine2"] @ f["neck"]
        child("Head", "Neck"); Rt["Head"] = Rt["Neck"] @ f["head"]
        pos["HeadTop"] = pos["Head"] + Rt["Head"] @ (self.tailp["Head"] - r["Head"])
        C = Rt["Spine2"]
        over = 0.0
        for s in "RL":
            u = C @ f["ua" + s]; fo = C @ f["fa" + s]
            RU, RF = self._arm_frames(s, u, fo, C)
            RH = C @ f["h" + s]
            if s == "L" and f["ikL"] > 1e-3 and self.has_weapon:
                Rsh = C.slerp(rot_min(C @ self.ua0[s], u) @ C, 0.18)
                sh = pos["Spine2"] + C @ (r["ShoulderL"] - r["Spine2"]) + Rsh @ (r["UpperArmL"] - r["ShoulderL"])
                wd = Rt["Weapon"] @ self.w0
                Sg = pos["Weapon"] + wd * f["gripL"]
                elb = sh + RU @ (r["ForearmL"] - r["UpperArmL"])
                fe = (Sg - elb)
                fe = fe.normalized() if fe.length > 1e-5 else fo
                for _ in range(3):
                    hd = fe - wd * fe.dot(wd)
                    if hd.length < 1e-4:
                        hd = wd.orthogonal()
                    hd.normalize()
                    Rh = frame_rot(self.b0["L"], self.e0["L"], wd, hd)
                    wrist = Sg - Rh @ (self.gripcL - r["HandL"])
                    K, A2, perp, n, ov = ik2(sh, wrist, self.La, self.Lf, C @ f["elL"])
                    fe = (A2 - K).normalized()
                ui = (K - sh).normalized()
                RU2, RF2 = self._arm_frames(s, ui, fe, C)
                wgt = clamp(f["ikL"])
                RU = RU.slerp(RU2, wgt); RF = RF.slerp(RF2, wgt); RH = RH.slerp(Rh, wgt)
                u = RU @ self.ua0[s]
            Rsh = C.slerp(rot_min(C @ self.ua0[s], u) @ C, 0.18)
            Rt["Shoulder" + s] = Rsh
            child("Shoulder" + s, "Spine2")
            child("UpperArm" + s, "Shoulder" + s); Rt["UpperArm" + s] = RU
            child("Forearm" + s, "UpperArm" + s); Rt["Forearm" + s] = RF
            child("Hand" + s, "Forearm" + s); Rt["Hand" + s] = RH
            if s == "R" and self.has_weapon:
                child("Weapon", "HandR"); Rt["Weapon"] = RH @ f["wpn"]
                pos["WeaponTip"] = pos["Weapon"] + Rt["Weapon"] @ (self.w0 * self.tip_len)
        for s in "LR":
            child("Thigh" + s, "Hips")
            Pp = pos["Thigh" + s]
            A = r["Foot" + s] + f["f" + s]
            qf = f[f"f{s}r"]
            lw = clamp(f["legsp"])
            if lw > 1e-4:
                Ah = pos["Hips"] + Rt["Hips"] @ (r["Foot" + s] + f["f" + s] - r["Hips"])
                A = A.lerp(Ah, lw)
                qf = qf.slerp(Rt["Hips"] @ qf, lw)
            hint = (qf @ FWD) * 0.5 + (Rt["Hips"] @ FWD) * 0.5 + Rt["Hips"] @ f["k" + s]
            K, A2, perp, n, ov = ik2(Pp, A, self.Lt, self.Ls, hint)
            over = max(over, ov)
            hinge = perp.cross(n).normalized()
            Rt["Thigh" + s] = frame_rot(self.t0[s], self.hk0[s], (K - Pp), hinge)
            Rt["Shin" + s] = frame_rot(self.s0[s], self.hk0[s], (A2 - K), hinge)
            Rt["Foot" + s] = qf
            pos["Shin" + s] = K; pos["Foot" + s] = A2
            pos["Toe" + s] = A2 + qf @ (self.toe0[s] - r["Foot" + s])
        return Rt, pos, over

    # ---- 布料鏈模擬
    def _sim_chain(self, ch, data, loop):
        names = ch["names"]; anchor = ch["anchor"]; pts0 = ch["pts"]
        r = self.rest
        n = len(pts0)
        seg = [(pts0[i + 1] - pts0[i]).length for i in range(n - 1)]
        d0 = [(pts0[i + 1] - pts0[i]).normalized() for i in range(n - 1)]
        stiff = ch.get("stiff", 0.05); damp = ch.get("damp", 0.90); grav = ch.get("grav", 9.8)
        cols = ch.get("colliders", ()); planar = ch.get("planar", True)
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
                for _it in range(3):
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
                        if p[i].z < 0.02:
                            p[i].z = 0.02
            if si >= start_out:
                A = Rt[anchor]
                out = {}
                for i in range(n - 1):
                    d = (p[i + 1] - p[i]).normalized()
                    out[names[i]] = rot_min(A @ d0[i], d) @ A
                res.append(out)
        return res

    # ---- 產生動作
    def action(self, name, keys, loop=False, quiet=False):
        arm = self.arm
        xs = [k[0] for k in keys]
        rows = [self._flatten(k[1]) for k in keys]
        Yv = np.array(rows, float)
        # 四元數符號連續
        i = 0
        for n, size, kind in LAYOUT:
            if kind == "q":
                for k in range(1, len(rows)):
                    if np.dot(Yv[k, i:i + 4], Yv[k - 1, i:i + 4]) < 0:
                        Yv[k, i:i + 4] *= -1
            i += size
        f0, f1 = xs[0], xs[-1]
        frames = list(range(int(f0), int(f1) + 1))
        Fq = pchip(xs, Yv, frames, loop)
        data = []
        maxover = 0.0
        for row in Fq:
            Rt, pos, ov = self.solve(self._unflatten(row))
            maxover = max(maxover, ov)
            data.append((Rt, pos, ov))
        for ch in self.chains:
            res = self._sim_chain(ch, data, loop)
            for (Rt, pos, _), o in zip(data, res):
                Rt.update(o)
        # 其餘骨頭跟著父骨
        order = self.names
        quat = {b: [] for b in order if b != "Root"}
        hips_loc = []
        Bq = self.Bq
        for Rt, pos, _ in data:
            for b in order:
                if b == "Root":
                    continue
                if b not in Rt:
                    Rt[b] = Rt[self.parent[b]]
                q = Bq[b].inverted() @ Rt[self.parent[b]].inverted() @ Rt[b] @ Bq[b]
                quat[b].append(q)
            hips_loc.append(Bq["Hips"].inverted() @ (pos["Hips"] - self.rest["Hips"]))
        if not arm.animation_data:
            arm.animation_data_create()
        act = bpy.data.actions.new(name)
        nF = len(frames)
        fr = np.array(frames, float)

        def write(path, idx, vals, group):
            fc = act.fcurves.new(path, index=idx, action_group=group)
            fc.keyframe_points.add(nF)
            co = np.empty(nF * 2); co[0::2] = fr; co[1::2] = vals
            fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [1] * nF)
            fc.update()
        for b, qs in quat.items():
            arr = np.array([[q.w, q.x, q.y, q.z] for q in qs])
            for k in range(1, nF):
                if np.dot(arr[k], arr[k - 1]) < 0:
                    arr[k] *= -1
            if loop and np.dot(arr[-1], arr[0]) > 0.9999:
                arr[-1] = arr[0]
            for c in range(4):
                write(f'pose.bones["{b}"].rotation_quaternion', c, arr[:, c], b)
        hl = np.array([list(v) for v in hips_loc])
        for c in range(3):
            write('pose.bones["Hips"].location', c, hl[:, c], "Hips")
        tr = arm.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, int(f0), act)
        tr.mute = True
        arm.animation_data.action = None
        # 檢查：最低點、腿是否伸過頭
        zmin = {}
        for Rt, pos, _ in data:
            for k in ("ToeL", "ToeR", "FootL", "FootR", "ShinL", "ShinR", "HandL", "HandR", "Head", "Hips", "WeaponTip"):
                if k in pos:
                    zmin[k] = min(zmin.get(k, 9), pos[k].z)
        msg = f"ACTION {name}: frames {int(f0)}-{int(f1)} ({(f1 - f0) / self.fps:.2f}s) over={maxover * 100:.1f}cm " + \
              " ".join(f"{k}={v:.2f}" for k, v in zmin.items())
        self.report.append(msg)
        if not quiet:
            print(msg, flush=True)
        return act
