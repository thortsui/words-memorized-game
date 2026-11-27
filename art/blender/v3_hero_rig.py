"""單字魂 v3 主角：Rig 子類別（從 soul_humanoid_anim.Rig._sim_chain 複製再改）。
差異：布料鏈的地板高度依節點遞增（ch["floor"]），披風下擺離鏈末端還有一段（外張、破邊），鏈末端要停得比地面高才不會讓下擺穿地。"""
import math
import numpy as np
from mathutils import Vector, Quaternion
from soul_humanoid_anim import Rig, rot_min
from soul_humanoid_lib import clamp


class V3Rig(Rig):
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

        push = ch.get("push", 0.0)

        def tgt(Rt, pos, i):
            # push：目標點沿身體背後方向（+Y）外推，讓披風多往外甩
            return pos[anchor] + Rt[anchor] @ (pts0[i] - r[anchor] + Vector((0, push * i / (n - 1), 0)))
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
                        fl = ch.get("floor", 0.02) * (i / (n - 1))
                        if p[i].z < max(0.02, fl):
                            p[i].z = max(0.02, fl)
            if si >= start_out:
                A = Rt[anchor]
                out = {}
                for i in range(n - 1):
                    d = (p[i + 1] - p[i]).normalized()
                    out[names[i]] = rot_min(A @ d0[i], d) @ A
                res.append(out)
        return res


    def solve(self, f):
        """劍鞘骨：跟骨盆走，但劍鞘尖若會低於地面 4 cm，就以鞘口為支點往後上擺（像拖在地上被頂起）。"""
        Rt, pos, over = super().solve(f)
        if "Scabbard" in self.rest:
            Hq = Rt["Hips"]
            top = pos["Hips"] + Hq @ (self.rest["Scabbard"] - self.rest["Hips"])
            v = Hq @ (self.tailp["Scabbard"] - self.rest["Scabbard"])
            q = Hq
            Lv = v.length
            if (top + v).z < 0.04:
                back = Hq @ Vector((0, 1, 0))
                hd = Vector((v.x, v.y, 0.0))
                if hd.length < 0.15 * Lv:
                    hd = hd + Vector((back.x, back.y, 0.0)) * 0.3 * Lv
                hd.normalize()
                sz = max(-1.0, min(0.6, (0.04 - top.z) / Lv))
                nd = hd * math.sqrt(1 - sz * sz) + Vector((0, 0, sz))
                q = rot_min(v, nd) @ Hq
            Rt["Scabbard"] = q
            pos["Scabbard"] = top
        return Rt, pos, over

    CHAIN_OVERRIDE = {"HitHeavy": dict(floor=0.36), "Roll": dict(stiff=0.06, damp=0.90, floor=0.36, colliders=[("Hips", "Spine2", 0.34), ("ThighL", "ShinL", 0.16), ("ThighR", "ShinR", 0.16), ("ShinL", "FootL", 0.12), ("ShinR", "FootR", 0.12)])}

    def action(self, name, keys, *a, **kw):
        """翻滾時披風跟身體貼得較緊（布料模擬改硬），避免倒立那幾格穿身／入地。"""
        ov = self.CHAIN_OVERRIDE.get(name)
        saved = [dict(c) for c in self.chains]
        if ov:
            for c in self.chains:
                c.update(ov)
        try:
            return super().action(name, keys, *a, **kw)
        finally:
            for c, s in zip(self.chains, saved):
                c.clear(); c.update(s)
