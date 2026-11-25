"""魂系 Boss 1：腐朽守門騎士（原創造型）。身高 2.3 m、瘦長；樹根與青苔纏繞的鏽甲、骷髏臉＋壺形盔、
酒紅破罩袍、雙手長戟、背後破塔盾。
用法：blender --background --factory-startup --python build_soul_sentinel.py -- [--quick] [--nobake] [--noanim] [--only A,B]
"""
import bpy, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector, Quaternion
from soul_humanoid_lib import *
from soul_humanoid_parts import *
import soul_humanoid_bake as BK
from soul_humanoid_anim import Rig, W, HW

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOBAKE = "--nobake" in argv
NOANIM = "--noanim" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_sentinel"
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = os.path.join(ROOT, "public", "models", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", MODEL + ".blend")
TILES = os.path.join(HERE, "preview", "_tiles", MODEL)

reset_scene()
body = Body(H=2.3, bulk=0.84, wf=0.90, head=0.255, hz=0.545, arm_len=1.06, limb=0.95)
U = body.U; R = body.R; j = body.j; hs = body.head
B = Builder()
rnd = random.Random(7)

# ---------------------------------------------------------------- 材質
D = BK.define_mat
D("rust", "A", tex="Metal024", size=0.6, U=U, rust=0.78, wear=0.5, dirt=0.9, bump=0.7, val=0.62, moss=0.40, rust_tint=(0.40, 0.29, 0.23))
D("mail", "A", tex="Chainmail004", size=0.24, U=U, tint=(0.40, 0.37, 0.34), metal=0.7, rough=0.65, rust=0.6, dirt=1.0, bump=1.0,
  bump_dist=0.006, moss=0.3, ao_shade=0.75, rust_tint=(0.40, 0.29, 0.23))
D("bone", "A", tex="Rust009", size=0.5, U=U, sat=0.15, val=0.85, tint=(0.60, 0.54, 0.40), rough=0.75, metal=0.0, dirt=1.0, bump=0.5,
  moss=0.22, dirt_col=(0.05, 0.035, 0.02), seed=3.0)
D("bark", "A", tex="Bark012", size=0.22, U=U, tint=(0.36, 0.30, 0.24), rough=0.9, metal=0.0, dirt=0.6, bump=1.0, moss=0.42, seed=5.0)
D("leaf", "A", color=(0.07, 0.15, 0.04), flat_rough=0.7, dirt=0.3, bump=0.2, ao_shade=0.4)
D("leather", "A", tex="Leather026", size=0.30, U=U, val=2.8, tint=(0.42, 0.27, 0.16), rough=0.8, metal=0.0, dirt=0.9, wear=0.4,
  wear_col=(0.36, 0.26, 0.18), bump=0.6, moss=0.3)
D("gambeson", "A", tex="Fabric030", size=0.22, U=U, tint=(0.12, 0.10, 0.08), rough=0.95, metal=0.0, dirt=0.8, bump=0.7, moss=0.2)
D("void", "A", color=(0.004, 0.004, 0.004), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("robe", "B", tex="Fabric030", size=0.30, U=U, tint=(0.30, 0.055, 0.07), rough=0.92, metal=0.0, dirt=0.7, wear=0.6,
  wear_col=(0.42, 0.22, 0.20), bump=0.9, mud=(0.15, 0.85, 0.7), mud_col=(0.11, 0.085, 0.07), moss=0.2, ao_shade=0.75, stain=0.5, stain_col=(0.07, 0.02, 0.025))
D("wood", "B", tex="Wood066", size=0.7, U=U, tint=(0.42, 0.36, 0.30), rough=0.85, metal=0.0, dirt=0.9, bump=0.8, moss=0.5, wear=0.3,
  wear_col=(0.5, 0.42, 0.33))
D("iron", "B", tex="Metal024", size=0.5, U=U, rust=0.95, wear=0.6, dirt=0.8, bump=0.7, val=0.62, moss=0.3, seed=9.0, rust_tint=(0.40, 0.29, 0.23))
D("barkB", "B", tex="Bark012", size=0.22, U=U, tint=(0.36, 0.30, 0.24), rough=0.9, metal=0.0, dirt=0.6, bump=1.0, moss=0.45, seed=6.0)
D("leafB", "B", color=(0.07, 0.15, 0.04), flat_rough=0.7, dirt=0.3, bump=0.2, ao_shade=0.4)
D("glow", "G", emit=(1.0, 0.55, 0.18), emit_strength=1.6)


def leaves(name, pts, mat, w, size=0.03):
    """小葉片（菱形面），pts：[(位置, 法線)]。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("atlas")
    for p, n in pts:
        n = n.normalized()
        e1 = n.orthogonal().normalized()
        e1 = (Quaternion(n, rnd.uniform(0, 6.28)) @ e1)
        e2 = n.cross(e1)
        s = size * rnd.uniform(0.7, 1.3) * U
        base = p + n * 0.004
        tilt = n * (s * rnd.uniform(0.2, 0.7))
        vs = [bm.verts.new(base), bm.verts.new(base + e1 * s * 0.55 + e2 * s * 0.38 + tilt * 0.5),
              bm.verts.new(base + e1 * s * 1.2 + tilt), bm.verts.new(base + e1 * s * 0.55 - e2 * s * 0.38 + tilt * 0.5)]
        f = bm.faces.new(vs)
        for l, q in zip(f.loops, ((0, 0), (0.01, 0.006), (0.02, 0), (0.01, -0.006))):
            l[uvl].uv = (0.012 + q[0], 0.012 + q[1])
    return B.add_mesh(name, bm, mat, w, sharp=80, stacked=True)


# ---------------------------------------------------------------- 內層、罩袍
under_torso(B, body, "robe", texel=0.9, off=0.004)
under_arm(B, body, "mail")
under_leg(B, body, "gambeson", texel=0.6)
mail_skirt(B, body, "mail", body.tz(0.22), body.tz(-0.50), flare=0.03, rag=0.05, seed=4)
zb = body.tz(0.27)
belt(B, body, zb, "leather", {"Spine": 0.5, "Hips": 0.5}, h=0.05, off=0.022)
buckle(B, body, zb, 6, "rust", {"Spine": 0.5, "Hips": 0.5}, off=0.032)
strap_hang(B, body, zb - 0.01, 14, "leather", length=0.30, off=0.032)
belt(B, body, body.tz(0.18), "leather", "Hips", h=0.036, off=0.03, tilt=0.04, tilt_dir=-80, name="Belt2")
pouch(B, body, zb - 0.02, 70, "leather", off=0.03)
# 斜背盾牌的皮帶
belt(B, body, body.tz(0.62), "leather", "Spine2", h=0.04, off=0.02, tilt=0.20, tilt_dir=-90, name="Guige", nu=24)
B.both(tasset(B, body, "rust", body.tz(0.20), length=0.26, a0=28, a1=96, off=0.03, rivet_mat="rust"))

# 罩袍前後片
zr = body.tz(0.25)
rf_pts = [V(0, -0.135 * R - 0.03, zr), V(0, -0.20 * R, zr - 0.42 * U), V(0, -0.22 * R, zr - 0.86 * U)]
rb_pts = [V(0, 0.135 * R + 0.04, zr), V(0, 0.22 * R, zr - 0.34 * U), V(0, 0.26 * R, zr - 0.68 * U), V(0, 0.28 * R, zr - 1.0 * U)]
rf_names = chain_names("RobeF", 2); rb_names = chain_names("RobeB", 3)
cloth_panel(B, "RobeFront", lambda u: body.torso.pt(zr, lerp(-36, 36, u), 0.026 * R), lambda u: FWD.copy(), 0.90 * U, "robe",
            w_chain_pts("Hips", rf_names, rf_pts), nu=14, nv=14, flare=0.06, rag=0.15, deep=0.1, fold_amp=0.016 * U, fold_n=2.0, holes=0.06, seed=21,
            spread=0.10 * U)
cloth_panel(B, "RobeBack", lambda u: body.torso.pt(zr, lerp(108, 252, u), 0.030 * R), lambda u: Y.copy(), 1.05 * U, "robe",
            w_chain_pts("Hips", rb_names, rb_pts), nu=22, nv=16, flare=0.09, rag=0.17, deep=0.1, fold_amp=0.028 * U, fold_n=3.0, holes=0.06, seed=22,
            spread=-0.22 * U)
# 兜帽領與披肩（破布）
mantle(B, body, "robe", t0=0.66, t1=1.12, off=0.022, rag=0.09, drop=0.05, front_drop=0.06, asym=-0.06, back_drop=0.05, seed=9,
       collar=0.035, folds=7, fold_amp=0.02)

# ---------------------------------------------------------------- 盔甲
pauldron(B, body, "rust", size=1.22, lames=3, haute=0.05, rivet_mat="rust", tilt=0.55)
B.mirror_only(pauldron(B, body, "rust", size=0.98, lames=2, haute=0.0, rivet_mat="rust"))
B.both(arm_armor(B, body, "rust", rivet_mat="rust", cuff=0.034))
body.set_grip(0.020 * U)
B.mirror_only(hand(B, body, "rust"))
hand(B, body, "rust")
B.both(leg_armor(B, body, "rust", rivet_mat="rust", cuisse_arc=(-95, 110)))
B.both(sabaton(B, body, "rust", pointed=1.6))
B.both(strap_ring(B, body.shin, body.sh_len * 0.32, "leather", "ShinL", width=0.024 * U, off=0.016 * R, name="GreaveStrapA"))
B.both(strap_ring(B, body.thigh, body.th_len * 0.40, "leather", "ThighL", width=0.026 * U, off=0.017 * R, name="CuisseStrapA"))

# ---------------------------------------------------------------- 頭：骷髏臉＋鎖子頭巾＋壺形盔
hc = V(0, -0.012 * U, body.H - hs * 0.50)


def skull_dent(d, u, v):
    r = 1.0
    for sx in (-1, 1):
        e = Vector((sx * 0.42, -0.88, 0.12)).normalized()
        r -= 0.25 * math.exp(-((d - e).length / 0.29) ** 2)
        e2 = Vector((sx * 0.78, -0.50, -0.42)).normalized()
        r -= 0.12 * math.exp(-((d - e2).length / 0.25) ** 2)
    e = Vector((0, -0.97, -0.26)).normalized()
    r -= 0.13 * math.exp(-((d - e).length / 0.15) ** 2)
    # 顴骨與下顎收窄
    if d.z < -0.2:
        r -= 0.20 * smooth((-d.z - 0.2) / 0.6) * (0.4 + 0.6 * abs(d.x))
    ck = Vector((0.62, -0.72, -0.30))
    for sx in (-1, 1):
        e = Vector((sx * ck.x, ck.y, ck.z)).normalized()
        r += 0.06 * math.exp(-((d - e).length / 0.22) ** 2)
    e = Vector((0, -0.95, 0.32)).normalized()
    r += 0.03 * math.exp(-((d - e).length / 0.4) ** 2)
    return r


rad = (0.325 * hs, 0.40 * hs, 0.44 * hs)
B.ellipsoid("Skull", hc, (X, Y, Z), rad, 24, 16, "bone", "Head", dent=skull_dent, texel=1.6)
# 上顎齒列與下顎
B.ellipsoid("MouthDark", hc + V(0, -0.17 * hs, -0.375 * hs), (X, Y, Z), (0.20 * hs, 0.16 * hs, 0.04 * hs), 10, 4, "void", "Head", texel=0.4)
jc = hc + V(0, -0.045 * hs, -0.475 * hs)
B.ellipsoid("Jaw", jc, (X, Y, Z), (0.215 * hs, 0.27 * hs, 0.115 * hs), 14, 8, "bone", "Head", texel=1.4,
            dent=lambda d, u, v: 1 - 0.25 * smooth((d.y - 0.1) / 0.6))
tp = []
for k in range(-4, 5):
    a = k * 9.5
    p = hc + V(math.sin(math.radians(a)) * 0.215 * hs, -0.02 * hs - math.cos(math.radians(a)) * 0.29 * hs, -0.335 * hs)
    tp.append((p, V(math.sin(math.radians(a)), -math.cos(math.radians(a)), -0.5)))
B.rivets("Teeth", tp, "bone", "Head", r=0.016 * hs)
# 眼窩與鼻孔的暗面
for sx in (-1, 1):
    e = Vector((sx * 0.42, -0.88, 0.12)).normalized()
    p = hc + V(e.x * rad[0], e.y * rad[1], e.z * rad[2]) * 0.76
    B.ellipsoid(f"Socket{sx}", p, (X, Z, e), (0.118 * hs, 0.098 * hs, 0.018 * hs), 10, 4, "void", "Head", v0=0, v1=0.5, texel=0.5)
    B.ellipsoid(f"EyeGlow{sx}", p + e * 0.012 * hs, (X, Z, e), (0.015 * hs, 0.015 * hs, 0.010 * hs), 8, 3, "glow", "Head", v0=0, v1=0.5)
e = Vector((0, -0.97, -0.26)).normalized()
p = hc + V(e.x * rad[0], e.y * rad[1], e.z * rad[2]) * 0.875
B.ellipsoid("NoseHole", p, (X, Z, e), (0.036 * hs, 0.075 * hs, 0.012 * hs), 8, 4, "void", "Head", v0=0, v1=0.5, texel=0.5)
# 鎖子頭巾
coif = Surf(V(0, 0.0, body.head_base - 0.06 * U), Z, [(0, 0.30 * hs, 0.33 * hs, 0, 0.01), (0.10 * U, 0.33 * hs, 0.40 * hs, 0, 0.012),
                                                      (0.22 * U, 0.36 * hs, 0.45 * hs, 0, 0.012), (0.34 * U, 0.34 * hs, 0.43 * hs, 0, 0.012)])
B.shell("Coif", coif, 0.0, 0.165 * U, 66, 294, 16, 4, "mail", {"Head": 0.8, "Neck": 0.2}, off=0.004, rim=0.004)
# 壺形盔
kz = body.H - hs * 0.43
kettle = Surf(V(0, -0.006 * U, kz), Z, [(0.0, 0.60 * hs, 0.66 * hs, 0, 0), (0.05 * hs, 0.50 * hs, 0.56 * hs, 0, 0), (0.085 * hs, 0.40 * hs, 0.47 * hs, 0, 0),
                                         (0.20 * hs, 0.375 * hs, 0.445 * hs, 0, 0), (0.34 * hs, 0.30 * hs, 0.36 * hs, 0, 0),
                                         (0.43 * hs, 0.17 * hs, 0.21 * hs, 0, 0), (0.465 * hs, 0.01 * hs, 0.012 * hs, 0, 0)])


def kettle_off(u, v, ang, t):
    a = angn(ang)
    mid = min(abs(a), 180 - abs(a))
    dentn = -0.012 * hs * math.exp(-(((a - 60) / 22) ** 2 + ((v - 0.05) / 0.08) ** 2))        # 帽緣的凹痕
    return 0.008 * hs * math.exp(-(mid / 6) ** 2) * smooth((v - 0.12) * 5) + dentn + 0.01 * hs * math.sin(ang * 0.05) * (1 - v) ** 6


B.shell("Kettle", kettle, 0.0, 0.4649 * hs, 0, 360, 32, 12, "rust", "Head", off=kettle_off, rim=0.006 * hs, texel=1.2)
B.shell("KettleBand", kettle, 0.09 * hs, 0.13 * hs, 0, 360, 24, 1, "rust", "Head", off=0.008 * hs, rim=0.004)
kp = [(kettle.pt(0.11 * hs, a, 0.013 * hs), kettle.nrm(0.11 * hs, a)) for a in range(0, 360, 30)]
B.rivets("KettleRivets", kp, "rust", "Head", r=0.007 * U)

# ---------------------------------------------------------------- 樹根、藤蔓與葉
wt = body.w_torso()
roots(B, body, body.torso, "bark", wt, body.tz(0.02), body.tz(0.88), turns=0.85, a_start=-70, r=0.016 * U, off=0.036 * R, n=22, seed=1)
roots(B, body, body.torso, "bark", wt, body.tz(0.30), body.tz(0.80), turns=-0.5, a_start=150, r=0.012 * U, off=0.040 * R, n=14, seed=2)
roots(B, body, body.thigh, "bark", "ThighL", body.th_len * 0.15, body.th_len * 0.92, turns=1.4, a_start=40, r=0.013 * U, off=0.022 * R, n=16, seed=3)
roots(B, body, body.shin, "bark", "ShinL", body.sh_len * 0.10, body.sh_len * 0.98, turns=1.7, a_start=200, r=0.014 * U, off=0.020 * R, n=16, seed=4)
B.mirror_only(roots(B, body, body.shin, "bark", "ShinL", body.sh_len * 0.30, body.sh_len * 0.98, turns=1.1, a_start=20, r=0.011 * U, off=0.020 * R, n=12, seed=5))
B.mirror_only(roots(B, body, body.thigh, "bark", "ThighL", body.th_len * 0.45, body.th_len * 0.95, turns=0.8, a_start=120, r=0.010 * U, off=0.022 * R, n=10, seed=8))
roots(B, body, body.uarm, "bark", "UpperArmL", body.ua_len * 0.35, body.ua_len * 0.95, turns=1.2, a_start=0, r=0.011 * U, off=0.040 * R, n=12, seed=6)
B.mirror_only(roots(B, body, body.farm, "bark", "ForearmL", body.fa_len * 0.10, body.fa_len * 0.85, turns=1.5, a_start=90, r=0.011 * U, off=0.022 * R, n=12, seed=7))
lp = []
for k in range(14):
    t = body.tz(rnd.uniform(0.05, 0.75)); a = rnd.uniform(0, 360)
    lp.append((body.torso.pt(t, a, 0.034 * R), body.torso.nrm(t, a)))
leaves("LeavesTorso", lp, "leaf", "Spine2")
lp = []
for k in range(12):
    t = rnd.uniform(0.2, 0.95) * body.sh_len; a = rnd.uniform(0, 360)
    lp.append((body.shin.pt(t, a, 0.03 * R), body.shin.nrm(t, a)))
leaves("LeavesShin", lp, "leaf", "ShinL")
lp = []
for k in range(6):
    c = j["UpperArmL"] + V(0.01, 0, 0.06) * U
    d = Vector((rnd.uniform(-0.6, 1), rnd.uniform(-1, 1), rnd.uniform(0.2, 1))).normalized()
    lp.append((c + d * 0.108 * R * 1.22, d))
# （肩上的葉片取消：會浮在空中）

# ---------------------------------------------------------------- 背後的破塔盾
k = U / 1.278
sh_c = V(0.03, 0.135 * R + 0.15 * k, body.tz(0.50))
sh_w, sh_h, sh_curve = 0.58 * k, 1.22 * k, 0.50 * k
sh_tilt = Quaternion(Y, math.radians(-10)) @ Quaternion(X, math.radians(5))
srnd = random.Random(3)
edge_cut = [srnd.random() for _ in range(40)]


def shield_fn(u, v, lift=0.0):
    x = (u - 0.5) * sh_w
    z = (v - 0.5) * sh_h
    y = -(sh_curve - math.sqrt(max(sh_curve ** 2 - x * x, 0))) + lift      # 向後凸
    # 右上角破損：往內縮
    return sh_c + sh_tilt @ V(x, -y, z)


def shield_hole(i, jv):
    u = (i + 0.5) / 14; v = (jv + 0.5) / 20
    brk = (u - 1.0) ** 2 * 1.2 + (v - 1.0) ** 2 * 0.55
    brk2 = (u - 0.0) ** 2 * 3 + (v - 0.0) ** 2 * 1.0
    return brk < 0.085 + 0.05 * edge_cut[(i * 3 + jv) % 40] or brk2 < 0.012 + 0.02 * edge_cut[(i + jv * 5) % 40]


B.grid("Shield", 14, 20, shield_fn, "wood", "Spine2", sh_c - Y * 0.5, holes=shield_hole, rim=0.022 * k, sharp=40)
# 鐵框與盾心
for name, pts_uv in (("ShieldRimL", [(0.02, v) for v in (0.12, 0.3, 0.5, 0.7, 0.98)]), ("ShieldRimB", [(u, 0.02) for u in (0.2, 0.4, 0.6, 0.8, 0.98)]),
                     ("ShieldRimR", [(0.98, v) for v in (0.02, 0.2, 0.4, 0.58, 0.70)]), ("ShieldRimT", [(u, 0.98) for u in (0.02, 0.2, 0.4, 0.6)]),
                     ("ShieldBar", [(u, 0.52) for u in (0.03, 0.25, 0.5, 0.75, 0.97)])):
    pts = [shield_fn(u, v) + sh_tilt @ V(0, 0.006 * k, 0) for u, v in pts_uv]
    B.tube(name, pts, [(0.024 * k, 0.008 * k)] * len(pts), 6, "iron", "Spine2", exp=4, flat=sh_tilt @ Y)
bc = shield_fn(0.5, 0.52) + sh_tilt @ V(0, 0.004, 0)
B.ellipsoid("ShieldBoss", bc, (sh_tilt @ X, sh_tilt @ Z, sh_tilt @ Y), (0.085 * k, 0.085 * k, 0.05 * k), 14, 5, "iron", "Spine2", v0=0, v1=0.5, rim=0.004)
rp = []
for u in (0.06, 0.94):
    for v in (0.1, 0.25, 0.4, 0.6):
        rp.append((shield_fn(u, v) + sh_tilt @ V(0, 0.014 * k, 0), sh_tilt @ Y))
for u in (0.2, 0.35, 0.65, 0.8):
    rp.append((shield_fn(u, 0.52) + sh_tilt @ V(0, 0.014 * k, 0), sh_tilt @ Y))
B.rivets("ShieldRivets", rp, "iron", "Spine2", r=0.010 * k)
# 爬在盾上的藤
for sd in range(3):
    vr = random.Random(30 + sd)
    u0 = vr.uniform(0.2, 0.8); pts = []; rr = []
    for q in range(12):
        v = 0.03 + q / 11 * vr.uniform(0.7, 0.92)
        u = clamp(u0 + 0.16 * math.sin(q * 0.9 + sd * 2) + 0.05 * vr.uniform(-1, 1), 0.04, 0.9)
        if shield_hole(int(u * 14), int(v * 20)):
            break
        pts.append(shield_fn(u, v) + sh_tilt @ V(0, 0.012 * k, 0))
        rr.append(0.010 * k * (1 - 0.6 * q / 11))
    if len(pts) > 3:
        B.tube(f"ShieldVine{sd}", pts, rr, 5, "barkB", "Spine2", texel=0.9)
        leaves(f"ShieldLeaves{sd}", [(p + sh_tilt @ V(vr.uniform(-0.03, 0.03), 0.008, vr.uniform(-0.03, 0.03)), sh_tilt @ Y + V(vr.uniform(-0.5, 0.5), 0, vr.uniform(-0.5, 0.5)))
                                     for p in pts[::2]], "leafB", "Spine2", size=0.03)

# ---------------------------------------------------------------- 長戟（右手為前手，握點即武器骨原點）
gcR = Body.mir(body.grip_c); ax = Body.mir(body.hand_v); edge = Body.mir(body.hand_a)
edge = (edge - ax * edge.dot(ax)).normalized()
side = ax.cross(edge)
BUTT, SOCK, TIP = -1.02 * k, 1.02 * k, 1.60 * k


def hp(s, e=0.0):
    return gcR + ax * s + edge * e


B.tube("Shaft", [hp(BUTT), hp(BUTT * 0.5), hp(0), hp(SOCK * 0.5), hp(SOCK)], [0.019 * k] * 5, 8, "wood", "Weapon", texel=0.8)
B.tube("ButtCap", [hp(BUTT - 0.10 * k), hp(BUTT - 0.03 * k), hp(BUTT + 0.05 * k)], [0.002 * k, 0.022 * k, 0.023 * k], 6, "iron", "Weapon")
B.tube("Socket", [hp(SOCK - 0.28 * k), hp(SOCK - 0.10 * k), hp(SOCK + 0.14 * k)], [0.023 * k, 0.026 * k, 0.022 * k], 8, "iron", "Weapon")
B.tube("Spike", [hp(SOCK + 0.10 * k), hp(SOCK + 0.16 * k), hp(SOCK + 0.36 * k), hp(TIP)], [(0.020 * k, 0.020 * k), (0.030 * k, 0.012 * k), (0.020 * k, 0.008 * k), (0.001, 0.001)],
       4, "iron", "Weapon", flat=edge, sharp=10)
# 斧刃：由柄往刃口方向展開的菱形截面
am = SOCK - 0.04 * k
B.tube("AxeBlade", [hp(am, 0.012 * k), hp(am, 0.07 * k), hp(am - 0.01 * k, 0.16 * k), hp(am - 0.02 * k, 0.24 * k), hp(am - 0.025 * k, 0.285 * k)],
       [(0.085 * k, 0.012 * k), (0.105 * k, 0.010 * k), (0.165 * k, 0.007 * k), (0.215 * k, 0.003 * k), (0.235 * k, 0.0006)], 4, "iron", "Weapon",
       flat=ax, sharp=10)
# 背鉤
B.tube("Fluke", [hp(am, -0.012 * k), hp(am, -0.07 * k), hp(am - 0.04 * k, -0.15 * k), hp(am - 0.11 * k, -0.19 * k)],
       [(0.05 * k, 0.010 * k), (0.035 * k, 0.008 * k), (0.022 * k, 0.005 * k), (0.002, 0.001)], 4, "iron", "Weapon", flat=ax, sharp=10)
B.rivets("HalberdRivets", [(hp(SOCK - 0.2 * k) + side * 0.024 * k, side), (hp(SOCK - 0.08 * k) + side * 0.026 * k, side),
                           (hp(SOCK - 0.2 * k) - side * 0.024 * k, -side), (hp(SOCK - 0.08 * k) - side * 0.026 * k, -side)], "iron", "Weapon", r=0.007 * k)
B.tube("ShaftVine", [hp(s, 0) + (edge * math.cos(s * 9) + side * math.sin(s * 9)) * 0.024 * k for s in [x * 0.07 * k for x in range(3, 13)]],
       [0.007 * k] * 10, 4, "barkB", "Weapon", texel=0.9)

# ---------------------------------------------------------------- 骨架、烘焙、動作
arm = build_armature("BossSentinel", body, weapon=(gcR, gcR + ax * 0.30 * U),
                     chains=[("RobeF", "Hips", rf_pts), ("RobeB", "Hips", rb_pts)])
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)
mesh = BK.assemble(B, MODEL, size=(1024, 1024), bake=not (QUICK or NOBAKE), quick=QUICK)
BK.bind(mesh, arm)

legs = [("ThighL", "ShinL", 0.12 * U), ("ThighR", "ShinR", 0.12 * U), ("ShinL", "FootL", 0.10 * U), ("ShinR", "FootR", 0.10 * U)]
rig = Rig(arm, body, chains=[
    dict(names=rf_names, anchor="Hips", pts=rf_pts, stiff=0.04, damp=0.92, colliders=legs, out=(0, -1, 0)),
    dict(names=rb_names, anchor="Hips", pts=rb_pts, stiff=0.035, damp=0.93, colliders=legs + [("Hips", "Spine", 0.17 * U)], out=(0, 1, 0))])
rig.tip_len = TIP
rig.lie_dz = 0.0


def two(Pd, Rp, Lp, edge_=(0, -1, 0), hintR=None, elL=None):
    Rp = Vector(Rp); Lp = Vector(Lp)
    d = Rp - Lp
    Pd["ikL"] = 1.0; Pd["gripL"] = -d.length
    if elL:
        Pd["elL"] = elL
    rig.reach(Pd, "R", tuple(Rp), hintR, d.normalized(), Vector(edge_))


def one(Pd, g, d, edge_, left, hintR=None, hintL=None):
    Pd["ikL"] = 0.0
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))
    rig.reach(Pd, "L", left, hintL)


WP = {
    "idle": lambda p: two(p, (-0.10, -0.42, 1.22), (0.16, -0.20, 0.92), (0.3, -0.9, 0)),
    "s_wind": lambda p: two(p, (-0.52, 0.05, 1.22), (-0.06, -0.26, 1.06), (-0.5, -0.85, 0)),
    "s_wind2": lambda p: two(p, (-0.55, 0.10, 1.25), (-0.08, -0.25, 1.07), (-0.5, -0.85, 0)),
    "s_hit": lambda p: two(p, (0.12, -0.62, 1.10), (0.10, -0.16, 1.00), (1, 0, 0)),
    "s_follow": lambda p: two(p, (0.40, -0.24, 1.12), (0.06, -0.22, 1.00), (0, 1, 0)),
    "s_settle": lambda p: two(p, (0.36, -0.26, 1.08), (0.04, -0.24, 0.98), (0, 1, 0)),
    "o_up": lambda p: two(p, (-0.12, -0.08, 1.92), (0.10, -0.22, 1.60), (0, -0.5, 0.85), elL=(0.8, -0.2, -0.2)),
    "o_up2": lambda p: two(p, (-0.12, -0.02, 1.95), (0.10, -0.20, 1.64), (0, -0.5, 0.85), elL=(0.8, -0.2, -0.2)),
    "o_hit": lambda p: two(p, (-0.02, -0.80, 0.80), (0.08, -0.38, 1.00), (0, 0, -1)),
    "o_low": lambda p: two(p, (-0.02, -0.80, 0.68), (0.08, -0.38, 0.90), (0, 0, -1)),
    "o_rec": lambda p: two(p, (-0.08, -0.55, 1.00), (0.14, -0.25, 0.90), (0, -0.6, -0.8)),
    "enter0": lambda p: one(p, (-0.30, -0.22, 0.72), (0.05, 0.0, 1), (0, -1, 0), (0.24, -0.12, 0.74)),
    "enter1": lambda p: one(p, (-0.32, -0.28, 0.95), (0.0, -0.1, 1), (0, -1, 0), (0.26, -0.05, 0.86)),
    "enter2": lambda p: two(p, (-0.10, -0.44, 1.15), (0.16, -0.22, 0.85), (0.3, -0.9, 0)),
    "hit1": lambda p: two(p, (-0.42, -0.22, 1.38), (-0.02, -0.26, 1.08), (0, -1, 0)),
    "hit2": lambda p: two(p, (-0.25, -0.36, 1.12), (0.10, -0.22, 0.88), (0, -1, 0)),
    "stag1": lambda p: one(p, (-0.55, 0.0, 1.70), (-0.3, 0.5, 0.8), (0, -1, 0), (0.50, -0.20, 1.30)),
    "stag2": lambda p: one(p, (-0.60, 0.20, 1.30), (-0.5, 0.6, 0.5), (0, -1, 0), (0.45, -0.05, 1.10)),
    "stag3": lambda p: one(p, (-0.42, 0.06, 0.78), (-0.12, -0.15, 1), (0, -1, 0), (0.30, -0.10, 0.36), hintL=(0.8, 0.4, 0.0)),
    "stag4": lambda p: two(p, (-0.14, -0.30, 1.05), (0.14, -0.10, 0.78), (0.3, -0.9, 0)),
    "roar_gather": lambda p: two(p, (-0.16, -0.36, 0.95), (0.12, -0.24, 0.72), (0.3, -0.9, 0)),
    "roar": lambda p: one(p, (-0.62, -0.10, 1.55), (-0.35, -0.25, 0.9), (0, -1, 0), (0.62, -0.12, 1.35), hintL=(0.3, 0.6, -0.7)),
    "roar2": lambda p: one(p, (-0.64, -0.06, 1.60), (-0.40, -0.20, 0.9), (0, -1, 0), (0.64, -0.08, 1.40), hintL=(0.3, 0.6, -0.7)),
    "roar_end": lambda p: two(p, (-0.10, -0.46, 1.10), (0.16, -0.22, 0.82), (0.3, -0.9, 0)),
    "die1": lambda p: one(p, (-0.52, -0.05, 1.20), (-0.3, -0.5, 0.6), (0, -1, 0), (0.42, -0.16, 1.22)),
    "kneel": lambda p: one(p, (-0.36, -0.26, 0.42), (0.25, -0.94, -0.03), (1, 0, 0), (0.30, -0.14, 0.42), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "kneel2": lambda p: one(p, (-0.38, -0.30, 0.30), (0.28, -0.95, 0.0), (1, 0, 0), (0.30, -0.18, 0.34), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "fall": lambda p: one(p, (-0.44, -1.00, 0.08), (-0.2, -0.97, 0.0), (1, 0, 0), (0.36, -0.86, 0.07), hintR=(-0.9, 0.2, 0.3), hintL=(0.9, 0.2, 0.3)),
}

if not NOANIM:
    import soul_boss_actions
    soul_boss_actions.build(rig, lambda key, p: WP[key](p), primary="sweep", slow=1.0, only=ONLY, wide=0.9)

if not ONLY:
    BK.export_glb(arm, mesh, OUT_GLB)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("TRIS_FINAL", BK.tri_count(mesh), flush=True)
cam = BK.render_views(arm, body.H, TILES)
if not NOANIM:
    BK.render_actions(arm, body.H, TILES, cam, only=ONLY)
print("DONE", MODEL, flush=True)
