"""單字魂 v3 主角：依 spec 第 7 節量比例（rest pose，以分件名稱排除披風／劍等），輸出 MEASURE 行與 json。"""
import math, json
import numpy as np
from mathutils import Vector

SPEC = {"helm_w": 0.10, "helm_d": 0.13, "shoulder_w": 0.35, "chest_w": 0.24, "chest_d": 0.14, "waist_w": 0.20, "waist_d": 0.13,
        "hip_w": 0.24, "hip_w_pouch": 0.27, "uarm_d": 0.07, "farm_d": 0.06, "wrist_d": 0.05, "cuff_d": 0.075, "thigh_d": 0.10,
        "knee_d": 0.09, "shin_d": 0.075, "ankle_d": 0.065, "foot_l": 0.15, "foot_w": 0.065, "sword_l": 0.60, "guard_l": 0.13,
        "helm_h": 0.145}
NOT_TORSO = ("Cape", "Blade", "Guard", "Grip", "Pommel", "Scab", "UnderUArm", "UnderFArm", "Pauldron", "UArm", "Couter", "Vamb",
             "Gauntlet", "Hand", "Finger", "Thumb", "Palm", "ArmRivets")


def _verts(parts, keep):
    out = []
    for o in parts:
        if keep(o.name):
            me = o.data
            a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a)
            out.append(a.reshape(-1, 3))
    return np.concatenate(out) if out else np.zeros((0, 3))


def _band(P, z, tol):
    return P[np.abs(P[:, 2] - z) < tol]


def measure(parts, body, H, out_json=None):
    R = {}
    tol = 0.006 * H
    allv = _verts(parts, lambda n: True)
    z0 = allv[:, 2].min(); Hm = allv[:, 2].max() - z0
    R["H_m"] = round(float(Hm), 4)
    hv = _verts(parts, lambda n: n.startswith("Helm") and n != "HelmVoid")
    b = _band(hv, z0 + 0.93 * Hm, tol)
    R["helm_w"] = (b[:, 0].max() - b[:, 0].min()) / Hm; R["helm_d"] = (b[:, 1].max() - b[:, 1].min()) / Hm
    R["helm_h"] = (hv[:, 2].max() - hv[:, 2].min()) / Hm
    nc = _verts(parts, lambda n: not n.startswith(("Cape", "Blade", "Guard", "Grip", "Pommel")))
    b = _band(nc, z0 + 0.80 * Hm, tol)
    R["shoulder_w"] = (b[:, 0].max() - b[:, 0].min()) / Hm
    tv = _verts(parts, lambda n: not n.startswith(NOT_TORSO))
    tvw = _verts(parts, lambda n: not n.startswith(NOT_TORSO + ("Pouch",)))
    for k, h in (("chest", 0.73), ("waist", 0.60), ("hip", 0.52)):
        b = _band(tvw if k == "waist" else tv, z0 + h * Hm, tol)
        if k == "hip":
            R["hip_w_pouch"] = (b[:, 0].max() - b[:, 0].min()) / Hm
            b2 = _band(_verts(parts, lambda n: not n.startswith(NOT_TORSO + ("Pouch",))), z0 + h * Hm, tol)
            R["hip_w"] = (b2[:, 0].max() - b2[:, 0].min()) / Hm
        else:
            R[k + "_w"] = (b[:, 0].max() - b[:, 0].min()) / Hm
            R[k + "_d"] = (b[:, 1].max() - b[:, 1].min()) / Hm
    j = body.j

    def limb(names, a, c, t, tol=0.006):
        P = _verts(parts, lambda n: n.startswith(names) and not n.endswith("_R"))
        A, C = Vector(j[a]), Vector(j[c])
        ax = (C - A); L = ax.length; u = ax / L
        Pt = A + ax * t
        d = P - np.array(Pt)
        along = d @ np.array(u)
        sel = d[np.abs(along) < tol * Hm]
        if len(sel) == 0:
            return None
        perp = sel - np.outer(sel @ np.array(u), np.array(u))
        r = np.linalg.norm(perp, axis=1)
        sel = perp[r < 0.09 * Hm]
        e1 = np.array(u.orthogonal().normalized()); e2 = np.cross(np.array(u), e1)
        w1 = (sel @ e1).max() - (sel @ e1).min(); w2 = (sel @ e2).max() - (sel @ e2).min()
        return max(w1, w2) / Hm, min(w1, w2) / Hm
    arm_names = ("UnderUArm", "UArmStrap", "Couter", "UnderFArm", "Vambrace", "VambStrap", "GauntletCuff", "Rerebrace")
    R["uarm_d"] = limb(arm_names, "UpperArmL", "ForearmL", 0.5)
    R["farm_d"] = limb(arm_names, "ForearmL", "HandL", 0.45)
    R["wrist_d"] = limb(("UnderFArm", "GauntletCuff"), "ForearmL", "HandL", 0.97, 0.012)
    R["cuff_d"] = limb(("GauntletCuff",), "ForearmL", "HandL", 0.68, 0.012)
    leg = ("UnderThigh", "Cuisse", "Poleyn", "UnderShin", "Greave", "BootShaft")
    R["thigh_d"] = limb(leg, "ThighL", "ShinL", 0.45)
    R["knee_d"] = limb(leg, "ThighL", "ShinL", 0.985)
    R["shin_d"] = limb(leg, "ShinL", "FootL", 0.40)
    R["ankle_d"] = limb(leg, "ShinL", "FootL", 0.88, 0.012)
    fv = _verts(parts, lambda n: n.startswith(("Boot",)) and not n.endswith("_R"))
    R["foot_l"] = (fv[:, 1].max() - fv[:, 1].min()) / Hm; R["foot_w"] = (fv[:, 0].max() - fv[:, 0].min()) / Hm
    sv = _verts(parts, lambda n: n.startswith(("Blade", "Guard", "Grip", "Pommel")))
    c = sv.mean(axis=0); dd = sv - c
    _, _, vt = np.linalg.svd(dd, full_matrices=False)
    ax = vt[0]; pr = dd @ ax
    R["sword_l"] = (pr.max() - pr.min()) / Hm
    gv = _verts(parts, lambda n: n.startswith("Guard") and n != "GuardBlock")
    _, _, vt = np.linalg.svd(gv - gv.mean(axis=0), full_matrices=False)
    pr = (gv - gv.mean(axis=0)) @ vt[0]
    R["guard_l"] = (pr.max() - pr.min()) / Hm
    lines = []
    for k, sp in SPEC.items():
        v = R.get(k)
        if v is None:
            continue
        vv = v[0] if isinstance(v, tuple) else v
        err = (vv / sp - 1) * 100
        lines.append(f"MEASURE {k:12s} spec {sp:.3f}H  got {vv:.3f}H" + (f" x {v[1]:.3f}" if isinstance(v, tuple) else "") + f"  err {err:+.1f}%" + ("  !!" if abs(err) > 10 else ""))
    for l in lines:
        print(l, flush=True)
    if out_json:
        json.dump({k: (list(v) if isinstance(v, tuple) else v) for k, v in R.items()}, open(out_json, "w"), indent=1, default=float)
    return R


def stance(arm, action="Idle", frame=0):
    import bpy
    ad = arm.animation_data
    ad.action = bpy.data.actions[action]
    bpy.context.scene.frame_set(frame)
    pl = arm.matrix_world @ arm.pose.bones["FootL"].head
    pr = arm.matrix_world @ arm.pose.bones["FootR"].head
    ad.action = None
    return abs(pl.x - pr.x), (pl - pr).length
