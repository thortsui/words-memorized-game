"""v3 行刑者：比例實測（在建模腳本裡、合併前呼叫；用各分件的 rest 幾何切截面）。
measure(B, body, HT, parts_p2_names) -> dict，並寫成 JSON。
"""
import bpy, bmesh, math, json, re
from mathutils import Vector


def _verts(obs):
    out = []
    for o in obs:
        out += [v.co.copy() for v in o.data.vertices]
    return out


def _section(obs, co, no):
    """平面 (co, no) 與分件的交線頂點。"""
    pts = []
    for o in obs:
        bm = bmesh.new(); bm.from_mesh(o.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=1e-6)
        for g in r["geom_cut"]:
            if isinstance(g, bmesh.types.BMVert):
                pts.append(g.co.copy())
        bm.free()
    return pts


def _horiz(obs, z):
    p = _section(obs, Vector((0, 0, z)), Vector((0, 0, 1)))
    if not p:
        return None, None
    xs = [q.x for q in p]; ys = [q.y for q in p]
    return max(xs) - min(xs), max(ys) - min(ys)


def _limb(obs, a, b, frac, side_x=None):
    ax = (b - a).normalized()
    c = a.lerp(b, frac)
    p = _section(obs, c, ax)
    if side_x is not None:
        p = [q for q in p if (q.x > 0) == (side_x > 0)]
    if not p:
        return None
    # 截面點到骨軸距離的最大值 ×2（spec §7），另給平均直徑
    ds = []
    for q in p:
        d = q - c
        d = d - ax * d.dot(ax)
        ds.append(d.length)
    # 平均：用截面面積等效直徑太繁，取 (最大+中位) / 2 當「平均直徑」
    ds.sort()
    return max(ds) * 2, (ds[len(ds) // 2] + ds[-1]) / 2 * 2 / 1.0


def measure(B, body, HT, path, p2_marked=True):
    j = body.j
    P = [o for o in B.parts if not o.get("pmark")]
    def sel(*pat):
        rx = re.compile("|".join(pat))
        return [o for o in P if rx.match(o.name)]
    allv = _verts(P)
    H = max(v.z for v in allv) - min(v.z for v in allv)
    R = {"H_m": H}
    def n(x):
        return None if x is None else round(x / H, 4)
    torso_body = sel(r"^Tunic")
    torso_out = [o for o in P if not re.match(r"^(UpperArm|Forearm|Pauldron|PdLame|Bracer|Spike|RingSpike|Finger|Thumb|HandBack|Knuckle|Ink|Axe|Haft|Wrap|Collar|Gold|Seal|Ring|Socket|Ferrule|Spear|Hood$|EyeSl|EyeG|HeadVoid)", o.name)
                 and not re.search(r"(Thigh|Pants|Knee|Greave|Boot|Veil|Pool|Ankle)", o.name)]
    for nm, z in (("chest", 0.68), ("waist", 0.53), ("waist_belt", 0.555), ("hip", 0.45)):
        bw, bd = _horiz(torso_body, z * HT)
        ow, od = _horiz(torso_out, z * HT)
        R[nm] = dict(body_w=n(bw), body_d=n(bd), out_w=n(ow), out_d=n(od))
    # 肩寬：三角肌外緣（上臂皮膚最外 X）×2、肩甲外緣
    R["shoulder_body"] = n(2 * max(v.x for v in _verts(sel(r"^UpperArmSkin")) if v.z > j["UpperArmL"].z - 0.06 * HT))
    R["shoulder_out"] = n(2 * max(v.x for v in _verts(sel(r"^(Pauldron|PdLame)"))))
    pd = _verts(sel(r"^Pauldron$"))
    R["pauldron"] = dict(w=n(max(v.x for v in pd) - min(v.x for v in pd)), h=n(max(v.z for v in pd) - min(v.z for v in pd)),
                         d=n(max(v.y for v in pd) - min(v.y for v in pd)), top_z=n(max(v.z for v in pd)))
    hood = sel(r"^Hood$")
    hw, hd = _horiz(hood, 0.86 * HT)
    R["head_hood_w_eye"] = n(hw); R["head_hood_d_eye"] = n(hd)
    R["head_body_w"] = n(hw - 2 * 0.004 * HT - 2 * 0.006 * HT) if hw else None
    R["hood_tip_z"] = n(max(v.z for v in _verts(hood)))
    R["chin_z"] = 0.80
    ua = sel(r"^UpperArmSkin$"); fa = sel(r"^ForearmSkin$")
    UA0, FA0, HA0 = j["UpperArmL"], j["ForearmL"], j["HandL"]
    R["upper_arm_d"] = n(_limb(ua, UA0, FA0, 0.4)[0])
    R["forearm_d"] = n(_limb(fa, FA0, HA0, 0.5)[0])
    R["wrist_d"] = n(_limb(fa, FA0, HA0, 0.95)[0])
    R["upper_arm_bare_d"] = [n(_limb(ua, UA0, FA0, t)[0]) for t in (0.65, 0.72, 0.8)]
    br = sel(r"^BracerIron")
    R["bracer_out_d"] = n(_limb(br, Vector((-FA0.x, FA0.y, FA0.z)), Vector((-HA0.x, HA0.y, HA0.z)), 0.6)[0]) if br else None
    th = sel(r"^Pants$"); sh = sel(r"^PantsShin$")
    T0, S0, F0 = j["ThighL"], j["ShinL"], j["FootL"]
    R["thigh_d"] = n(_limb(th, T0, S0, 0.4)[0])
    legout = [o for o in P if re.match(r"^(Pants|ThighStrap|ThStrap)", o.name) and not o.name.endswith("_R")]
    R["thigh_out_d"] = n(_limb(legout, T0, S0, 0.38)[0])
    R["calf_d"] = n(_limb(sh, S0, F0, 0.4)[0])
    gv = [o for o in P if re.match(r"^(Greave)", o.name) and not o.name.endswith("_R")]
    R["greave_out_d"] = n(_limb(gv + sh, S0, F0, 0.4)[0])
    R["greave_out_d_low"] = [n(_limb(gv + sh, S0, F0, t)[0]) for t in (0.55, 0.7)]
    bt = sel(r"^Boot$")
    bv = _verts(bt)
    R["boot_len"] = n(max(v.y for v in bv) - min(v.y for v in bv)); R["boot_w"] = n(max(v.x for v in bv) - min(v.x for v in bv))
    R["upper_arm_len"] = n((FA0 - UA0).length); R["forearm_len"] = n((HA0 - FA0).length)
    hand = sel(r"^(Finger|HandBack|Thumb)")
    tipd = max((v - HA0).dot(body.hand_a) for v in _verts(hand))
    R["hand_len"] = n(tipd)
    R["arm_total"] = n((FA0 - UA0).length + (HA0 - FA0).length + tipd)
    R["leg_len"] = n(T0.z)
    R["thigh_len"] = n((S0 - T0).length); R["shin_len"] = n((F0 - S0).length)
    R["torso_len"] = n(UA0.z - 0.40 * HT)
    kc = sel(r"^KneeCop$")
    kv = _verts(kc)
    R["knee_cop_d"] = n(max(max(v.x for v in kv) - min(v.x for v in kv), max(v.z for v in kv) - min(v.z for v in kv)))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    print("MEASURE", json.dumps(R, ensure_ascii=False), flush=True)
    return R
