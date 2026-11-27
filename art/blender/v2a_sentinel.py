"""v2（建模 A）Boss 1：腐朽守門騎士 sentinel。依 art/v2/design.md §2.1、art_guide.md §1、art/reference/v2/sentinel_p1/p2.jpg。
寬簷斗笠鐵盔（簷下全黑只有兩點綠眼）＋背後直立的城門門板（鉸鏈、鐵釘、門環、縫隙透綠光）＋單手長戟斜指地面＋暗綠灰破爛長擺。
二階「根鬚暴走」：P2_RootArms（門板裂開、7 條粗根向上扇形張開）、P2_RootSpikes_*（肩甲／前臂／膝甲木刺）、
P2_Heart（胸甲裂口綠光樹心）、P2_HalberdRoots（戟纏根＋戟尖綠光）。
沿用 soul_humanoid_* 的骨架／烘焙／動作系統（不修改），PhaseShift 依 design.md 分鏡重做（2.4 s，爆發 1.1 s）。
用法：blender --background --factory-startup --python v2a_sentinel.py -- [--quick] [--nobake] [--noanim] [--only A,B]
"""
import bpy, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector, Quaternion, Matrix
from soul_humanoid_lib import *
from soul_humanoid_parts import *
import soul_humanoid_bake as BK
from soul_humanoid_anim import Rig, W, HW
import v2a_lib as VL

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOBAKE = "--nobake" in argv
NOANIM = "--noanim" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_sentinel"
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v2a_" + MODEL + ".blend")
TILES = os.path.join(HERE, "preview", "_tiles", "v2a_" + MODEL)
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

reset_scene()
body = Body(H=2.3, bulk=0.92, wf=0.96, head=0.255, hz=0.545, arm_len=1.06, limb=0.98)
U = body.U; R = body.R; j = body.j; hs = body.head
B = Builder()
rnd = random.Random(7)
k = U / 1.278

# ---------------------------------------------------------------- 材質
D = BK.define_mat
D("rust", "A", tex="Metal024", size=0.6, U=U, rust=0.62, wear=0.7, wear_col=(0.50, 0.48, 0.45), dirt=1.0, bump=0.8, val=0.48, sat=0.5,
  moss=0.34, rust_tint=(0.34, 0.20, 0.13), rust_size=0.32)
D("mail", "A", tex="Chainmail004", size=0.24, U=U, tint=(0.36, 0.33, 0.30), metal=0.7, rough=0.65, rust=0.6, dirt=1.0, bump=1.0,
  bump_dist=0.006, moss=0.3, ao_shade=0.75, rust_tint=(0.40, 0.27, 0.20))
D("gold", "A", tex="Metal024", size=0.4, U=U, tint=(0.62, 0.45, 0.17), sat=0.4, val=0.9, metal=0.85, rough=0.45, wear=0.6,
  wear_col=(0.70, 0.56, 0.26), dirt=1.0, bump=0.5, rust=0.25, rust_tint=(0.30, 0.20, 0.12), moss=0.10, seed=11.0)
D("bark", "A", tex="Bark012", size=0.22, U=U, tint=(0.24, 0.18, 0.13), rough=0.9, metal=0.0, dirt=0.6, bump=1.0, moss=0.42, seed=5.0)
D("leaf", "A", color=(0.05, 0.10, 0.035), flat_rough=0.7, dirt=0.3, bump=0.2, ao_shade=0.4)
D("leather", "A", tex="Leather026", size=0.30, U=U, val=2.6, tint=(0.36, 0.25, 0.16), rough=0.8, metal=0.0, dirt=0.9, wear=0.4,
  wear_col=(0.36, 0.26, 0.18), bump=0.6, moss=0.3)
D("gambeson", "A", tex="Fabric030", size=0.22, U=U, tint=(0.10, 0.10, 0.08), rough=0.95, metal=0.0, dirt=0.8, bump=0.7, moss=0.2)
D("void", "A", color=(0.004, 0.005, 0.004), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("hatin", "A", color=(0.012, 0.011, 0.010), flat_rough=0.95, dirt=0.5, ao_shade=0.6, bump=0.2)
D("robe", "B", tex="Fabric030", size=0.30, U=U, tint=(0.135, 0.15, 0.105), rough=0.92, metal=0.0, dirt=0.7, wear=0.6,
  wear_col=(0.30, 0.30, 0.24), bump=0.9, mud=(0.15, 0.85, 0.7), mud_col=(0.09, 0.08, 0.06), moss=0.32, ao_shade=0.75, stain=0.45,
  stain_col=(0.035, 0.045, 0.03))
D("wood", "B", tex="Wood066", size=0.7, U=U, tint=(0.40, 0.33, 0.25), rough=0.85, metal=0.0, dirt=1.0, bump=1.0, moss=0.55, wear=0.35,
  wear_col=(0.48, 0.40, 0.31))
D("shaft", "B", tex="Wood066", size=0.5, U=U, tint=(0.30, 0.22, 0.15), rough=0.8, metal=0.0, dirt=0.8, bump=0.6, moss=0.15, seed=4.0)
D("iron", "B", tex="Metal024", size=0.5, U=U, rust=0.75, wear=0.7, wear_col=(0.50, 0.48, 0.45), dirt=0.9, bump=0.8, val=0.48, sat=0.5, moss=0.25,
  seed=9.0, rust_tint=(0.34, 0.20, 0.13), rust_size=0.32)
D("barkB", "B", tex="Bark012", size=0.22, U=U, tint=(0.30, 0.24, 0.18), rough=0.9, metal=0.0, dirt=0.6, bump=1.0, moss=0.45, seed=6.0)
D("leafB", "B", color=(0.05, 0.10, 0.035), flat_rough=0.7, dirt=0.3, bump=0.2, ao_shade=0.4)
GREEN = "#7dffb0"
VL.glow_mat("Glow_Eye", GREEN, 2.2)
VL.glow_mat("Glow_Rune", GREEN, 0.3)
VL.glow_mat("Glow_Weapon", GREEN, 0.45)
VL.glow_mat("P2_Glow_Heart", GREEN, 1.4)
VL.glow_mat("P2_Glow_Root", GREEN, 0.8)
VL.glow_mat("P2_Glow_Weapon", GREEN, 1.6)


def leaves(name, pts, mat, w, size=0.03):
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


def grow(name, p, d, length, r0, seed, w, mat="bark", n=9, curl=Vector((0, 0, 0)), jit=0.25, segs=8, r1=0.0025, branches=0, droop=0.0):
    """彎曲漸細的樹根（可分岔）。curl：每節加到方向上的偏移（讓根往某方向彎）。回傳 (點, 半徑, 物件清單)。"""
    rr = random.Random(seed)
    pts = [p.copy()]; rad = [r0]
    d = d.normalized()
    for i in range(1, n + 1):
        d = (d + curl + Vector((rr.uniform(-jit, jit), rr.uniform(-jit, jit), rr.uniform(-jit, jit) * 0.6)) - Z * droop * (i / n)).normalized()
        pts.append(pts[-1] + d * length / n)
        rad.append(max(r0 * (1 - i / (n + 0.4)) ** 0.9, r1 * U))
    obs = [B.tube(name, pts, rad, segs, mat, w, texel=0.8)]
    for q in range(branches):
        kk = int(n * rr.uniform(0.35, 0.7))
        dd = (d + Vector((rr.uniform(-1, 1), rr.uniform(-0.6, 0.6), rr.uniform(-0.3, 0.8)))).normalized()
        _, _, ob2 = grow(f"{name}b{q}", pts[kk], dd, length * rr.uniform(0.3, 0.45), rad[kk] * 0.6, seed * 13 + q, w, mat,
                         max(4, n // 2), curl, jit * 1.2, max(5, segs - 2), r1)
        obs += ob2
    return pts, rad, obs


# ---------------------------------------------------------------- 內層、長擺
under_torso(B, body, "gambeson", texel=0.9, off=0.004)
under_arm(B, body, "mail")
under_leg(B, body, "gambeson", texel=0.6)
mail_skirt(B, body, "mail", body.tz(0.22), body.tz(-0.50), flare=0.03, rag=0.05, seed=4)
cuirass(B, body, "rust", off=0.010, globe=0.016, keel=0.010, t0=0.31, t_neck=0.86, t_arm=0.68, rivet_mat="rust")
fauld(B, body, "rust", n=3, t_top=0.31, rivet_mat="rust")
zb = body.tz(0.27)
belt(B, body, zb, "leather", {"Spine": 0.5, "Hips": 0.5}, h=0.05, off=0.034)
buckle(B, body, zb, 6, "iron", {"Spine": 0.5, "Hips": 0.5}, off=0.044)
strap_hang(B, body, zb - 0.01, 14, "leather", length=0.30, off=0.044)
belt(B, body, body.tz(0.18), "leather", "Hips", h=0.036, off=0.04, tilt=0.04, tilt_dir=-80, name="Belt2")
pouch(B, body, zb - 0.02, 70, "leather", off=0.04)
# 背門板的兩條斜背帶（左右肩各一，在胸前交叉）
for s, td in ((1, -90), (-1, 90)):
    belt(B, body, body.tz(0.60), "leather", "Spine2", h=0.042, off=0.046, tilt=0.26, tilt_dir=td, name=f"Guige{s}", nu=24)
B.both(tasset(B, body, "rust", body.tz(0.20), length=0.26, a0=28, a1=96, off=0.04, rivet_mat="rust"))

zr = body.tz(0.25)
rf_pts = [V(0, -0.135 * R - 0.03, zr), V(0, -0.20 * R, zr - 0.42 * U), V(0, -0.22 * R, zr - 0.86 * U)]
rb_pts = [V(0, 0.135 * R + 0.04, zr), V(0, 0.20 * R, zr - 0.34 * U), V(0, 0.23 * R, zr - 0.68 * U), V(0, 0.25 * R, zr - 1.0 * U)]
rf_names = chain_names("RobeF", 2); rb_names = chain_names("RobeB", 3)
cloth_panel(B, "RobeFront", lambda u: body.torso.pt(zr, lerp(-38, 38, u), 0.036 * R), lambda u: FWD.copy(), 0.95 * U, "robe",
            w_chain_pts("Hips", rf_names, rf_pts), nu=16, nv=14, flare=0.06, rag=0.18, deep=0.25, fold_amp=0.018 * U, fold_n=2.2, holes=0.07, seed=21,
            spread=0.10 * U)
cloth_panel(B, "RobeBack", lambda u: body.torso.pt(zr, lerp(110, 250, u), 0.040 * R), lambda u: Y.copy(), 1.05 * U, "robe",
            w_chain_pts("Hips", rb_names, rb_pts), nu=22, nv=16, flare=0.06, rag=0.20, deep=0.25, fold_amp=0.026 * U, fold_n=3.0, holes=0.07, seed=22,
            spread=-0.14 * U)
mantle(B, body, "robe", t0=0.68, t1=1.12, off=0.024, rag=0.10, drop=0.05, front_drop=0.07, asym=-0.05, back_drop=0.06, seed=9,
       collar=0.035, folds=7, fold_amp=0.022)

# ---------------------------------------------------------------- 盔甲（層疊肩甲左右都 3 片）
pauldron(B, body, "rust", size=1.22, lames=3, haute=0.05, rivet_mat="rust", tilt=0.55)
B.mirror_only(pauldron(B, body, "rust", size=1.12, lames=3, haute=0.03, rivet_mat="rust", tilt=0.6))
B.both(arm_armor(B, body, "rust", rivet_mat="rust", cuff=0.034))
body.set_grip(0.022 * U)
B.mirror_only(hand(B, body, "rust"))
hand(B, body, "rust")
B.both(leg_armor(B, body, "rust", rivet_mat="rust", cuisse_arc=(-95, 110)))
B.both(sabaton(B, body, "rust", pointed=1.4))
B.both(strap_ring(B, body.shin, body.sh_len * 0.32, "leather", "ShinL", width=0.024 * U, off=0.016 * R, name="GreaveStrapA"))
B.both(strap_ring(B, body.thigh, body.th_len * 0.40, "leather", "ThighL", width=0.026 * U, off=0.017 * R, name="CuisseStrapA"))

# ---------------------------------------------------------------- 頭：簷下一片黑（無臉）＋兩點綠眼＋鎖子頭巾
hc = V(0, -0.012 * U, body.H - hs * 0.50)
B.ellipsoid("FaceVoid", hc, (X, Y, Z), (0.31 * hs, 0.38 * hs, 0.44 * hs), 18, 12, "void", "Head", texel=0.4)
for sx in (-1, 1):
    p = hc + V(sx * 0.085 * hs, -0.365 * hs, 0.06 * hs)
    B.ellipsoid(f"Eye{sx}", p, (X, Z, Y), (0.030 * hs, 0.018 * hs, 0.012 * hs), 10, 5, "Glow_Eye", "Head")
coif = Surf(V(0, 0.0, body.head_base - 0.06 * U), Z, [(0, 0.30 * hs, 0.33 * hs, 0, 0.01), (0.10 * U, 0.34 * hs, 0.41 * hs, 0, 0.012),
                                                      (0.22 * U, 0.37 * hs, 0.46 * hs, 0, 0.012), (0.34 * U, 0.35 * hs, 0.44 * hs, 0, 0.012)])
B.shell("Coif", coif, 0.0, 0.18 * U, 62, 298, 16, 4, "mail", {"Head": 0.8, "Neck": 0.2}, off=0.004, rim=0.004)

# 寬簷斗笠盔：低圓頂＋大而略下垂的扁簷（簷徑 ≈ 0.36H，比肩寬），兩條十字金帶＋簷緣金邊
KC = V(0, -0.015 * U, body.H - 0.05 * U)
HAT = [(0.0, 0.0, 0.118), (0.10, 0.055, 0.114), (0.22, 0.100, 0.094), (0.34, 0.128, 0.064), (0.40, 0.140, 0.050), (0.48, 0.175, 0.040),
       (0.62, 0.250, 0.016), (0.80, 0.345, -0.022), (0.93, 0.400, -0.046), (1.0, 0.418, -0.056)]
hrnd = random.Random(12)
hdent = [hrnd.uniform(-1, 1) for _ in range(8)]


def hat_pt(u, v, lift=0.0, shrink=0.0):
    r, z = tab_eval([(a, b, c) for a, b, c in HAT], v)
    a = 2 * math.pi * u
    wob = 0.006 * (hdent[int(u * 8) % 8] * (1 - abs(((u * 8) % 1) - 0.5) * 2)) * smooth((v - 0.5) * 3)     # 簷緣不平整的凹凸
    sag = -0.010 * math.sin(a * 3 + 0.7) * smooth((v - 0.55) * 2.5)
    rr = (r - shrink) * U * (1.0 + 0.04 * math.sin(a))                                                  # 前後略長
    return KC + V(math.sin(a) * rr, -math.cos(a) * rr * 1.04, (z + wob + sag + lift) * U)


B.grid("Kasa", 40, 12, lambda u, v: hat_pt(u, v), "rust", "Head", KC - Z * 0.4, closed_u=True, texel=1.2, sharp=50)
B.grid("KasaUnder", 40, 6, lambda u, v: hat_pt(u, 0.40 + 0.6 * v, -0.016, 0.006), "hatin", "Head", KC + Z * 0.4, closed_u=True, texel=1.0)
B.tube("KasaRim", [hat_pt(i / 48, 1.0, -0.006) for i in range(49)], [(0.010 * U, 0.008 * U)] * 49, 6, "gold", "Head", texel=1.0)
B.tube("KasaCrownBand", [hat_pt(i / 40, 0.40, 0.004) for i in range(41)], [(0.012 * U, 0.006 * U)] * 41, 6, "gold", "Head", texel=1.0)
for q in range(4):
    a0 = q * 0.25 + 0.125
    pts = [hat_pt(a0, v, 0.006) for v in [x / 10 for x in range(1, 11)]]
    tang = V(math.cos(2 * math.pi * a0), math.sin(2 * math.pi * a0), 0)
    B.tube(f"KasaBand{q}", pts, [(0.022 * U, 0.0045 * U)] * len(pts), 4, "gold", "Head", flat=tang, exp=4)
B.rivets("KasaRivets", [(hat_pt(q * 0.25 + 0.125, 0.40, 0.012), Z) for q in range(4)] + [(hat_pt(0.0, 0.0, 0.010), Z)], "gold", "Head", r=0.014 * U)
# 簷下垂掛的青苔
for q, u0 in enumerate((0.08, 0.31, 0.47, 0.66, 0.86)):
    p = hat_pt(u0, 0.97, -0.012)
    ln = hrnd.uniform(0.05, 0.12) * U
    B.tube(f"KasaMoss{q}", [p, p - Z * ln * 0.5 + V(0.004, 0, 0), p - Z * ln], [0.008 * U, 0.006 * U, 0.002 * U], 5, "barkB", "Head")

# ---------------------------------------------------------------- 一階細樹根、葉
wt = body.w_torso()
roots(B, body, body.torso, "bark", wt, body.tz(0.02), body.tz(0.70), turns=0.85, a_start=-70, r=0.013 * U, off=0.046 * R, n=22, seed=1)
roots(B, body, body.thigh, "bark", "ThighL", body.th_len * 0.15, body.th_len * 0.92, turns=1.4, a_start=40, r=0.012 * U, off=0.024 * R, n=16, seed=3)
roots(B, body, body.shin, "bark", "ShinL", body.sh_len * 0.10, body.sh_len * 0.98, turns=1.7, a_start=200, r=0.013 * U, off=0.022 * R, n=16, seed=4)
B.mirror_only(roots(B, body, body.shin, "bark", "ShinL", body.sh_len * 0.30, body.sh_len * 0.98, turns=1.1, a_start=20, r=0.011 * U, off=0.022 * R, n=12, seed=5))
B.mirror_only(roots(B, body, body.thigh, "bark", "ThighL", body.th_len * 0.45, body.th_len * 0.95, turns=0.8, a_start=120, r=0.010 * U, off=0.024 * R, n=10, seed=8))
roots(B, body, body.uarm, "bark", "UpperArmL", body.ua_len * 0.35, body.ua_len * 0.95, turns=1.2, a_start=0, r=0.010 * U, off=0.042 * R, n=12, seed=6)
B.mirror_only(roots(B, body, body.farm, "bark", "ForearmL", body.fa_len * 0.10, body.fa_len * 0.85, turns=1.5, a_start=90, r=0.010 * U, off=0.024 * R, n=12, seed=7))
lp = []
for q in range(12):
    t = body.tz(rnd.uniform(0.05, 0.70)); a = rnd.uniform(-80, 80)
    lp.append((body.torso.pt(t, a, 0.046 * R), body.torso.nrm(t, a)))
leaves("LeavesTorso", lp, "leaf", "Spine2")
lp = []
for q in range(12):
    t = rnd.uniform(0.2, 0.95) * body.sh_len; a = rnd.uniform(0, 360)
    lp.append((body.shin.pt(t, a, 0.03 * R), body.shin.nrm(t, a)))
leaves("LeavesShin", lp, "leaf", "ShinL")

# ---------------------------------------------------------------- 背後直立的城門門板
DW, DH, DT = 0.84 * k, 1.30 * k, 0.085 * k
tilt = math.radians(6)
DC = V(0.0, 0.135 * R + 0.20 * k, 1.36 * k)
ez = V(0, math.sin(tilt), math.cos(tilt))
dn = V(0, math.cos(tilt), -math.sin(tilt))          # 門外側法線（朝後）


def DP(x, z, d=0.0):
    return DC + X * x + ez * z + dn * d


drnd = random.Random(5)
NPL = 6
gap = 0.010 * k
pw = (DW - gap * (NPL - 1)) / NPL
plank_x = [-DW / 2 + pw / 2 + q * (pw + gap) for q in range(NPL)]
for q, x in enumerate(plank_x):
    top = DH / 2 - drnd.uniform(0.0, 0.05) * k - (0.06 * k if q == NPL - 1 else 0)
    bot = -DH / 2 + drnd.uniform(0.0, 0.07) * k
    zc, hz = (top + bot) / 2, (top - bot) / 2
    c = DP(x + drnd.uniform(-0.002, 0.002), zc, drnd.uniform(-0.006, 0.006) * k)
    B.tube(f"Plank{q}", [c - ez * hz, c - ez * hz * 0.96, c - ez * hz * 0.3, c + ez * hz * 0.3, c + ez * hz * 0.96, c + ez * hz],
           [(pw / 2 * 0.9, DT / 2 * 0.85), (pw / 2, DT / 2), (pw / 2, DT / 2), (pw / 2 * 0.98, DT / 2), (pw / 2, DT / 2), (pw / 2 * 0.9, DT / 2 * 0.85)],
           12, "wood", "Spine2", exp=6, flat=X, texel=1.0, sharp=40)
# 外側 Z 形斜撐、上下兩道鐵鉸鏈帶（左側有鉸鏈筒）、上下鐵框、門環、鐵釘
for q, zz in enumerate((0.40 * k, -0.40 * k)):
    B.tube(f"Hinge{q}", [DP(-DW / 2 - 0.03 * k, zz, DT / 2 + 0.006), DP(DW * 0.15, zz, DT / 2 + 0.007), DP(DW / 2 - 0.02 * k, zz + 0.01 * k, DT / 2 + 0.006)],
           [(0.034 * k, 0.007 * k), (0.030 * k, 0.007 * k), (0.022 * k, 0.006 * k)], 6, "iron", "Spine2", flat=ez, exp=5)
    B.tube(f"HingeBarrel{q}", [DP(-DW / 2 - 0.035 * k, zz - 0.07 * k, 0.0), DP(-DW / 2 - 0.035 * k, zz + 0.07 * k, 0.0)], [0.026 * k] * 2, 10, "iron", "Spine2")
    B.rivets(f"HingeNails{q}", [(DP(x, zz, DT / 2 + 0.013), dn) for x in plank_x], "iron", "Spine2", r=0.011 * k)
bA, bB = DP(-DW * 0.36, -0.34 * k, DT / 2 + 0.018), DP(DW * 0.36, 0.34 * k, DT / 2 + 0.018)
B.tube("Brace", [bA, bA.lerp(bB, 0.5), bB], [(0.055 * k, 0.017 * k)] * 3, 8, "wood", "Spine2", flat=(bB - bA).normalized().cross(dn), exp=6)
B.rivets("BraceNails", [(DP(-DW * 0.36 + t * DW * 0.72, -0.34 * k + t * 0.68 * k, DT / 2 + 0.037), dn) for t in (0.08, 0.5, 0.92)], "iron", "Spine2", r=0.010 * k)
for q, zz in enumerate((DH / 2 - 0.02 * k, -DH / 2 + 0.03 * k)):
    B.tube(f"DoorFrame{q}", [DP(-DW / 2 - 0.012, zz, 0), DP(DW / 2 + 0.012, zz, 0)], [(0.026 * k, DT / 2 + 0.008)] * 2, 8, "iron", "Spine2", flat=ez, exp=5)
    B.rivets(f"FrameNails{q}", [(DP(x, zz, DT / 2 + 0.010), dn) for x in plank_x], "iron", "Spine2", r=0.009 * k)
rc = DP(DW * 0.26, 0.02 * k, DT / 2 + 0.010)
B.ellipsoid("RingPlate", rc, (X, ez, dn), (0.05 * k, 0.06 * k, 0.012 * k), 12, 4, "iron", "Spine2", v0=0, v1=0.5)
ring = [rc + dn * 0.016 + X * 0.045 * k * math.sin(2 * math.pi * i / 16) - ez * (0.045 * k - 0.045 * k * math.cos(2 * math.pi * i / 16)) for i in range(17)]
B.tube("DoorRing", ring, [0.009 * k] * 17, 6, "iron", "Spine2", cap=False)
# 縫隙透出的弱綠光（細長裂縫，不是整片）
for q, (gx, z0, z1) in enumerate(((0, -0.30, 0.18), (2, -0.05, 0.42), (3, -0.52, -0.12), (4, 0.10, 0.50))):
    x = (plank_x[gx] + plank_x[gx + 1]) / 2
    pts = [DP(x + 0.002 * math.sin(i * 2.1), (z0 + (z1 - z0) * i / 6) * k, DT * 0.18) for i in range(7)]
    B.tube(f"DoorCrack{q}", pts, [(gap * 0.42, DT * 0.30)] + [(gap * 0.48, DT * 0.32)] * 5 + [(gap * 0.42, DT * 0.30)], 6, "Glow_Rune", "Spine2", flat=X)
# 門板下緣垂掛的根鬚與青苔
for q, x in enumerate((-0.30, -0.12, 0.05, 0.22, 0.33)):
    p = DP(x * k, -DH / 2 + 0.05 * k, DT * 0.3)
    _, _, _ = grow(f"DoorDangle{q}", p, -Z + dn * 0.3, drnd.uniform(0.12, 0.28) * k, 0.010 * k, 70 + q, "Spine2", "barkB", n=6, jit=0.3, segs=5)
leaves("DoorLeaves", [(DP(drnd.uniform(-0.38, 0.38) * k, drnd.uniform(-0.6, 0.6) * k, DT / 2 + 0.01), dn + V(drnd.uniform(-0.6, 0.6), 0, drnd.uniform(-0.6, 0.6)))
                      for _ in range(16)], "leafB", "Spine2", size=0.035)
for q in range(2):
    vr = random.Random(30 + q)
    pts = [DP((-0.3 + 0.55 * q + 0.08 * math.sin(i * 0.9 + q)) * k, (-0.62 + i * 0.085) * k, DT / 2 + 0.014) for i in range(12)]
    B.tube(f"DoorVine{q}", pts, [0.010 * k * (1 - 0.6 * i / 11) for i in range(12)], 5, "barkB", "Spine2", texel=0.9)

# ---------------------------------------------------------------- 長戟（右手前手；握點＝武器骨原點）
gcR = Body.mir(body.grip_c); ax = Body.mir(body.hand_v); edge = Body.mir(body.hand_a)
edge = (edge - ax * edge.dot(ax)).normalized()
side = ax.cross(edge)
BUTT, SOCK, TIP = -0.80 * k, 0.98 * k, 1.50 * k


def hp(s, e=0.0, sd=0.0):
    return gcR + ax * s + edge * e + side * sd


B.tube("Shaft", [hp(BUTT), hp(BUTT * 0.5), hp(0), hp(SOCK * 0.5), hp(SOCK)], [0.021 * k] * 5, 8, "shaft", "Weapon", texel=0.8)
B.tube("ButtCap", [hp(BUTT - 0.10 * k), hp(BUTT - 0.03 * k), hp(BUTT + 0.06 * k)], [0.002 * k, 0.024 * k, 0.025 * k], 6, "iron", "Weapon")
for q, s0 in enumerate((-0.12, 0.12, 0.55)):
    B.tube(f"ShaftBand{q}", [hp(s0 * k - 0.03 * k), hp(s0 * k + 0.03 * k)], [0.025 * k] * 2, 8, "leather", "Weapon")
B.tube("Socket", [hp(SOCK - 0.30 * k), hp(SOCK - 0.10 * k), hp(SOCK + 0.16 * k)], [0.025 * k, 0.028 * k, 0.024 * k], 8, "iron", "Weapon")
B.tube("Spike", [hp(SOCK + 0.12 * k), hp(SOCK + 0.18 * k), hp(SOCK + 0.36 * k), hp(TIP)], [(0.024 * k, 0.022 * k), (0.034 * k, 0.012 * k), (0.022 * k, 0.008 * k), (0.001, 0.001)],
       4, "iron", "Weapon", flat=edge, sharp=10)
am = SOCK - 0.02 * k
# 寬斧刃（刃口呈弧形，下緣有缺口）
B.tube("AxeBlade", [hp(am, 0.014 * k), hp(am, 0.08 * k), hp(am - 0.01 * k, 0.18 * k), hp(am - 0.02 * k, 0.27 * k), hp(am - 0.03 * k, 0.315 * k)],
       [(0.095 * k, 0.013 * k), (0.12 * k, 0.010 * k), (0.19 * k, 0.007 * k), (0.25 * k, 0.003 * k), (0.27 * k, 0.0006)], 4, "iron", "Weapon",
       flat=ax, sharp=10)
B.tube("Fluke", [hp(am, -0.014 * k), hp(am, -0.08 * k), hp(am - 0.04 * k, -0.16 * k), hp(am - 0.12 * k, -0.21 * k)],
       [(0.055 * k, 0.010 * k), (0.038 * k, 0.008 * k), (0.024 * k, 0.005 * k), (0.002, 0.001)], 4, "iron", "Weapon", flat=ax, sharp=10)
B.rivets("HalberdRivets", [(hp(SOCK - 0.2 * k) + side * 0.026 * k, side), (hp(SOCK - 0.08 * k) + side * 0.028 * k, side),
                           (hp(SOCK - 0.2 * k) - side * 0.026 * k, -side), (hp(SOCK - 0.08 * k) - side * 0.028 * k, -side)], "iron", "Weapon", r=0.008 * k)
B.tube("ShaftVine", [hp(s, 0) + (edge * math.cos(s * 9) + side * math.sin(s * 9)) * 0.026 * k for s in [x * 0.07 * k for x in range(3, 13)]],
       [0.007 * k] * 10, 4, "barkB", "Weapon", texel=0.9)
# 戟尖兩面的細刻紋（一階很弱的綠光）
for sg in (1, -1):
    B.tube(f"SpikeRune{sg}", [hp(SOCK + 0.20 * k, 0, sg * 0.0115 * k), hp(SOCK + 0.32 * k, 0.003 * k, sg * 0.0100 * k), hp(TIP - 0.05 * k, 0, sg * 0.004 * k)],
           [(0.0045 * k, 0.0016 * k)] * 3, 4, "Glow_Weapon", "Weapon", flat=edge)
TIPP = hp(TIP)

# ---------------------------------------------------------------- 二階部件
# P2_RootArms：門板中央裂開，7 條粗根從裂縫往上、往兩側扇形張開（寬 ≈ 1.2H）
p2 = []
base = DP(0.0, 0.10 * k, DT / 2)
fan = [(-80, 1.30, 0.085), (-55, 1.45, 0.095), (-28, 1.36, 0.090), (0, 1.15, 0.095), (28, 1.38, 0.090), (55, 1.46, 0.095), (80, 1.32, 0.085)]
for q, (ang, ln, r0) in enumerate(fan):
    a = math.radians(ang)
    sp = DP(math.sin(a) * 0.14 * k, (0.12 + 0.18 * math.cos(a)) * k - 0.12 * k, DT / 2 + 0.01)
    d = (X * math.sin(a) * 1.0 + ez * math.cos(a) * 1.25 + Z * 0.25 + dn * 0.40).normalized()
    curl = X * (0.06 * math.sin(a)) + Z * 0.03 * abs(math.sin(a)) + dn * 0.01
    _, _, obs = grow(f"RootArm{q}", sp, d, ln * k, r0 * k, 100 + q, "Spine2", "bark", n=9, curl=curl, jit=0.16, segs=7, branches=2)
    p2 += obs
for q in range(4):
    p2.append(B.ellipsoid(f"RootKnot{q}", DP((-0.15 + q * 0.10) * k, (0.05 + 0.08 * (q % 2)) * k, DT / 2 + 0.03), (X, ez, dn),
                          (0.12 * k, 0.14 * k, 0.08 * k), 12, 8, "bark", "Spine2", texel=0.8))
crack = [DP((0.015 * math.sin(i * 1.7) + 0.01 * ((i * 7) % 3 - 1)) * k, (-0.58 + i * 0.105) * k, DT / 2 + 0.008) for i in range(12)]
p2.append(B.tube("GateSplit", crack, [(0.016 * k, 0.010 * k)] * 12, 6, "P2_Glow_Root", "Spine2", flat=X))
for q, (x0, z0) in enumerate(((-0.25, 0.35), (0.22, -0.30), (-0.18, -0.42), (0.28, 0.30))):
    pts = [DP((x0 * (1 - i / 4)) * k + 0.01 * math.sin(i * 3), (z0 + (0.0 - z0) * i / 4) * k * 0.6 + 0.05 * k, DT / 2 + 0.008) for i in range(5)]
    p2.append(B.tube(f"GateSplitB{q}", pts, [(0.008 * k, 0.006 * k)] * 5, 5, "P2_Glow_Root", "Spine2"))
VL.tag_p2(p2, "RootArms", "Spine2", base)

# P2_RootSpikes_*：肩甲、前臂、膝甲被根頂破長出木刺
def spikes(tag, bone, base_pts, sgn):
    obs = []
    for q, (p, d, ln) in enumerate(base_pts):
        if sgn < 0:
            p = Body.mir(p); d = Body.mir(d)
        d = d.normalized()
        bend = (d.cross(Z) if abs(d.z) < 0.9 else X).normalized() * 0.15
        pts = [p - d * 0.02 * k, p + d * ln * 0.35 + bend * ln * 0.1, p + d * ln * 0.7 + bend * ln * 0.2, p + d * ln + bend * ln * 0.35]
        obs.append(B.tube(f"{tag}{q}", pts, [0.024 * k, 0.017 * k, 0.009 * k, 0.0015], 6, "bark", bone, texel=0.8))
        obs.append(B.ellipsoid(f"{tag}Knot{q}", p, (X, Y, Z), (0.03 * k, 0.03 * k, 0.03 * k), 8, 5, "bark", bone))
    return obs


uaL = j["UpperArmL"]
sh_pts = [(uaL + V(0.03, -0.02, 0.11) * U, V(0.35, 0.1, 1.0), 0.24 * k), (uaL + V(0.08, 0.05, 0.07) * U, V(0.9, 0.5, 0.5), 0.20 * k),
          (uaL + V(-0.02, 0.07, 0.10) * U, V(-0.1, 0.8, 0.8), 0.17 * k)]
fa_pts = [(body.farm.pt(body.fa_len * 0.40, 80, 0.05 * R), body.farm.nrm(body.fa_len * 0.40, 80) + body.fd * 0.2, 0.14 * k),
          (body.farm.pt(body.fa_len * 0.62, 120, 0.05 * R), body.farm.nrm(body.fa_len * 0.62, 120) + body.fd * 0.3, 0.11 * k)]
kn = j["ShinL"]
kn_pts = [(kn + V(0.01, -0.075, 0.03) * U, V(0.1, -1.0, 0.45), 0.17 * k), (kn + V(0.055, -0.05, 0.0) * U, V(0.9, -0.5, 0.2), 0.12 * k),
          (kn + V(-0.03, -0.07, -0.04) * U, V(-0.4, -0.9, -0.1), 0.10 * k)]
for sgn, sfx in ((1, "L"), (-1, "R")):
    VL.tag_p2(spikes("ShSpike" + sfx, "UpperArm" + sfx, sh_pts, sgn), "RootSpikes_Shoulder" + sfx, "UpperArm" + sfx,
              uaL + V(0, 0, 0.09) * U if sgn > 0 else Body.mir(uaL + V(0, 0, 0.09) * U))
    VL.tag_p2(spikes("FaSpike" + sfx, "Forearm" + sfx, fa_pts, sgn), "RootSpikes_Forearm" + sfx, "Forearm" + sfx,
              fa_pts[0][0] if sgn > 0 else Body.mir(fa_pts[0][0]))
    VL.tag_p2(spikes("KnSpike" + sfx, "Shin" + sfx, kn_pts, sgn), "RootSpikes_Knee" + sfx, "Shin" + sfx,
              kn + V(0, -0.07, 0.0) * U if sgn > 0 else Body.mir(kn + V(0, -0.07, 0.0) * U))

# P2_Heart：胸甲中央裂口露出心形綠核，周圍放射細裂紋
tH = body.tz(0.63)
hcn = body.torso.pt(tH, 0, 0.040 * R)
hp2 = []
hp2.append(B.ellipsoid("HeartHole", hcn + Y * 0.004, (X, Z, -Y), (0.075 * k, 0.095 * k, 0.03 * k), 14, 6, "void", "Spine2", v0=0, v1=0.5))
hp2.append(B.ellipsoid("HeartCore", hcn - Y * 0.012 * k, (X, Y, Z), (0.045 * k, 0.034 * k, 0.058 * k), 12, 8, "P2_Glow_Heart", "Spine2",
                       dent=lambda d, u, v: 1 - 0.25 * math.exp(-((d.x) / 0.25) ** 2) * smooth(d.z * 3)))
for q in range(7):
    a = -150 + q * 50 + rnd.uniform(-10, 10)
    pts = []
    for i in range(6):
        rr = 0.06 + i * 0.03
        ang = math.radians(a + 12 * math.sin(i * 2.3 + q))
        t = tH + math.sin(ang) * rr * k
        ad = math.degrees(math.cos(ang) * rr * k / (0.17 * R)) * 1.0
        pts.append(body.torso.pt(t, ad, 0.046 * R))
    hp2.append(B.tube(f"HeartCrack{q}", pts, [0.006 * k * (1 - i / 7) for i in range(6)], 5, "P2_Glow_Heart", "Spine2"))
for q in range(5):
    a = q * 72 + 20
    p = hcn + (X * math.cos(math.radians(a)) + Z * math.sin(math.radians(a))) * 0.07 * k - Y * 0.004
    hp2.append(B.tube(f"HeartRoot{q}", [p, p.lerp(hcn, 0.5) - Y * 0.015, hcn - Y * 0.02], [0.011 * k, 0.008 * k, 0.004 * k], 6, "bark", "Spine2"))
VL.tag_p2(hp2, "Heart", "Spine2", hcn)

# P2_HalberdRoots：戟頭與桿上段纏根、戟尖綠光棘刺
wr = []
for q in range(3):
    ph = q * 2.1
    pts = [hp(s * k) + (edge * math.cos(s * 14 + ph) + side * math.sin(s * 14 + ph)) * 0.032 * k for s in [0.25 + x * 0.06 for x in range(14)]]
    wr.append(B.tube(f"HRoot{q}", pts, [0.011 * k * (0.6 + 0.4 * math.sin(x * 0.7 + q)) + 0.004 * k for x in range(14)], 6, "bark", "Weapon", texel=0.8))
for q, sg in enumerate((1, -1)):
    pts = [hp((SOCK - 0.10 + 0.03 * i) * k, sg * 0.03 * k * i * 0.6, 0.014 * k * sg) for i in range(8)]
    wr.append(B.tube(f"HRootBlade{q}", pts, [0.010 * k * (1 - i / 10) for i in range(8)], 5, "bark", "Weapon"))
wr.append(B.tube("HGlowTip", [hp(SOCK + 0.20 * k), hp(SOCK + 0.32 * k), hp(TIP - 0.03 * k), hp(TIP + 0.09 * k)],
                 [(0.030 * k, 0.020 * k), (0.026 * k, 0.016 * k), (0.012 * k, 0.008 * k), (0.001, 0.001)], 6, "P2_Glow_Weapon", "Weapon", flat=edge))
for q in range(4):
    s0 = SOCK + (0.22 + q * 0.06) * k
    sg = 1 if q % 2 else -1
    wr.append(B.tube(f"HThorn{q}", [hp(s0, 0.0, 0.01 * k * sg), hp(s0 + 0.03 * k, 0.02 * k, 0.05 * k * sg), hp(s0 + 0.07 * k, 0.03 * k, 0.08 * k * sg)],
                     [0.008 * k, 0.005 * k, 0.001], 5, "P2_Glow_Weapon", "Weapon"))
VL.tag_p2(wr, "HalberdRoots", "Weapon", hp(SOCK))

# ---------------------------------------------------------------- 骨架、烘焙
tipd = ax.normalized()
arm = build_armature("BossSentinel", body, weapon=(gcR, gcR + ax * 0.30 * U),
                     chains=[("RobeF", "Hips", rf_pts), ("RobeB", "Hips", rb_pts)],
                     extra=[("Tip_Weapon", "Weapon", TIPP, TIPP + tipd * 0.12 * k)])
glows = VL.pull_glow(B)
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts) + VL.tri_count(glows)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)
DETAIL_OF = {"rust": "metal", "iron": "metal", "gold": "metal", "bark": "bark", "barkB": "bark", "leather": "leather",
             "gambeson": "cloth", "robe": "cloth", "wood": "wood", "shaft": "wood"}.get
mesh = BK.assemble(B, MODEL, size=(TEXS, TEXS), bake=not (QUICK or NOBAKE), quick=QUICK, detail_of=DETAIL_OF, U=U)
VL.join_into(mesh, glows)
p2objs = VL.split_p2(mesh, arm)
BK.bind(mesh, arm)
print("TRIS_FINAL", BK.tri_count(mesh) + VL.tri_count(p2objs), "main", BK.tri_count(mesh), "p2", VL.tri_count(p2objs), flush=True)

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
    "idle": lambda p: one(p, (-0.36, -0.26, 0.98), (-0.22, -0.60, -0.76), (-0.9, 0, 0.3), (0.30, -0.12, 0.96), hintL=(0.8, 0.4, -0.4)),
    "s_wind": lambda p: two(p, (-0.52, 0.05, 1.22), (-0.06, -0.26, 1.06), (-0.5, -0.85, 0)),
    "s_wind2": lambda p: two(p, (-0.55, 0.10, 1.25), (-0.08, -0.25, 1.07), (-0.5, -0.85, 0)),
    "s_hit": lambda p: two(p, (0.12, -0.62, 1.10), (0.10, -0.16, 1.00), (1, 0, 0)),
    "s_follow": lambda p: two(p, (0.40, -0.24, 1.12), (0.06, -0.22, 1.00), (0, 1, 0)),
    "s_settle": lambda p: two(p, (0.36, -0.26, 1.08), (0.04, -0.24, 0.98), (0, 1, 0)),
    "o_up": lambda p: two(p, (-0.12, -0.10, 1.92), (0.10, -0.24, 1.60), (0, -0.5, 0.85), elL=(0.8, -0.2, -0.2)),
    "o_up2": lambda p: two(p, (-0.12, -0.04, 1.95), (0.10, -0.22, 1.64), (0, -0.5, 0.85), elL=(0.8, -0.2, -0.2)),
    "o_hit": lambda p: two(p, (-0.02, -0.80, 0.80), (0.08, -0.38, 1.00), (0, 0, -1)),
    "o_low": lambda p: two(p, (-0.02, -0.80, 0.68), (0.08, -0.38, 0.90), (0, 0, -1)),
    "o_rec": lambda p: two(p, (-0.08, -0.55, 1.00), (0.14, -0.25, 0.90), (0, -0.6, -0.8)),
    "enter0": lambda p: one(p, (-0.32, -0.22, 0.72), (0.05, 0.0, 1), (0, -1, 0), (0.26, -0.12, 0.74)),
    "enter1": lambda p: one(p, (-0.34, -0.28, 0.95), (0.0, -0.1, 1), (0, -1, 0), (0.28, -0.05, 0.86)),
    "enter2": lambda p: two(p, (-0.12, -0.44, 1.15), (0.16, -0.24, 0.85), (0.3, -0.9, 0)),
    "hit1": lambda p: two(p, (-0.42, -0.22, 1.38), (-0.02, -0.26, 1.08), (0, -1, 0)),
    "hit2": lambda p: two(p, (-0.25, -0.36, 1.12), (0.10, -0.22, 0.88), (0, -1, 0)),
    "stag1": lambda p: one(p, (-0.55, 0.0, 1.70), (-0.3, 0.5, 0.8), (0, -1, 0), (0.50, -0.20, 1.30)),
    "stag2": lambda p: one(p, (-0.60, 0.20, 1.30), (-0.5, 0.6, 0.5), (0, -1, 0), (0.45, -0.05, 1.10)),
    "stag3": lambda p: one(p, (-0.42, 0.06, 0.78), (-0.12, -0.15, 1), (0, -1, 0), (0.30, -0.10, 0.36), hintL=(0.8, 0.4, 0.0)),
    "stag4": lambda p: two(p, (-0.14, -0.30, 1.05), (0.14, -0.10, 0.78), (0.3, -0.9, 0)),
    "roar_gather": lambda p: two(p, (-0.16, -0.36, 0.95), (0.12, -0.24, 0.72), (0.3, -0.9, 0)),
    "roar": lambda p: one(p, (-0.62, -0.10, 1.55), (-0.35, -0.25, 0.9), (0, -1, 0), (0.62, -0.12, 1.35), hintL=(0.3, 0.6, -0.7)),
    "roar2": lambda p: one(p, (-0.64, -0.06, 1.60), (-0.40, -0.20, 0.9), (0, -1, 0), (0.64, -0.08, 1.40), hintL=(0.3, 0.6, -0.7)),
    "roar_end": lambda p: two(p, (-0.12, -0.46, 1.10), (0.16, -0.24, 0.82), (0.3, -0.9, 0)),
    "die1": lambda p: one(p, (-0.52, -0.05, 1.20), (-0.3, -0.5, 0.6), (0, -1, 0), (0.42, -0.16, 1.22)),
    "kneel": lambda p: one(p, (-0.36, -0.26, 0.42), (0.25, -0.94, -0.03), (1, 0, 0), (0.30, -0.14, 0.42), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "kneel2": lambda p: one(p, (-0.38, -0.30, 0.30), (0.28, -0.95, 0.0), (1, 0, 0), (0.30, -0.18, 0.34), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "t_pull": lambda p: two(p, (-0.22, -0.34, 1.02), (0.04, 0.22, 1.08), (1, 0, 0)),
    "t_thrust": lambda p: two(p, (-0.06, -1.00, 1.20), (0.02, -0.46, 1.14), (1, 0, 0)),
    "fall": lambda p: one(p, (-0.44, -1.00, 0.08), (-0.2, -0.97, 0.0), (1, 0, 0), (0.36, -0.86, 0.07), hintR=(-0.9, 0.2, 0.3), hintL=(0.9, 0.2, 0.3)),
    # PhaseShift（v2 分鏡）：戟插地單膝跪 → 被樹根吊起 → 拔戟高舉 → 戟橫胸前
    "ps_plant": lambda p: two(p, (-0.22, -0.48, 0.86), (-0.21, -0.47, 0.66), (0.3, -1, 0)),
    "ps_kneel": lambda p: two(p, (-0.22, -0.50, 0.64), (-0.21, -0.49, 0.46), (0.3, -1, 0), hintR=(-0.8, 0.3, -0.5)),
    "ps_hang": lambda p: two(p, (-0.22, -0.46, 0.90), (-0.20, -0.45, 0.70), (0.3, -1, 0)),
    "ps_hang2": lambda p: two(p, (-0.24, -0.40, 0.98), (-0.20, -0.40, 0.78), (0.3, -1, 0)),
    "ps_burst": lambda p: one(p, (-0.42, -0.14, 1.98), (0.12, -0.20, 1.0), (0, -1, 0), (0.66, -0.12, 1.42), hintL=(0.3, 0.6, -0.7)),
    "ps_burst2": lambda p: one(p, (-0.44, -0.10, 2.02), (0.15, -0.15, 1.0), (0, -1, 0), (0.68, -0.08, 1.46), hintL=(0.3, 0.6, -0.7)),
    "ps_cross": lambda p: two(p, (-0.30, -0.42, 1.12), (0.22, -0.40, 1.06), (0, -0.6, 0.8)),
}


def phase(K, T, I, IA, wide):
    kn0 = K("ps_plant", hips=(0, 0.02, -0.20), hr=(16, 0, -10), sp=(9, 0, -3), ch=(9, 0, -2), nod=24)
    knee = dict(fL=(0.10 * wide, -0.26, 0), fLr=(10, 0, 0), fR=(-0.10 * wide, 0.36, -0.02), fRr=(-20, 70, 0), kR=(-0.25, 0, 0))
    kn = K("ps_kneel", hips=(0, 0.06, -0.46), hr=(12, 0, -8), sp=(12, 0, -2), ch=(14, 0, 0), nod=48, **knee)
    knb = K("ps_kneel", hips=(0, 0.06, -0.48), hr=(14, 0, -8), sp=(14, 0, -2), ch=(16, 0, 0), nod=56, **knee)
    hang = K("ps_hang", hips=(0, 0.04, -0.06), hr=(4, 0, -6), sp=(2, 0, 0), ch=(4, 0, 0), nod=50)
    hang2 = K("ps_hang2", hips=(0, 0.04, 0.0), hr=(-2, 0, -4), sp=(-2, 0, 0), ch=(0, 0, 0), nod=40, off=(0, 0, 0.02))
    st = dict(fL=(0.12 * wide, -0.32, 0), fR=(-0.14 * wide, 0.30, 0))
    bu = K("ps_burst", hips=(0, 0.06, -0.02), hr=(-12, 0, -4), sp=(-9, 0, 0), ch=(-13, 0, 0), nod=-36, **st)
    bu2 = K("ps_burst2", hips=(0, 0.07, -0.03), hr=(-15, 0, -2), sp=(-11, 0, 2), ch=(-15, 0, 2), nod=-42, **st)
    bu3 = K("ps_burst2", hips=(0, 0.06, -0.05), hr=(-12, 0, -6), sp=(-9, 0, -2), ch=(-12, 0, -2), nod=-34, **st)
    cr = K("ps_cross", hips=(0, -0.05, -0.14), hr=(12, 0, -14), sp=(7, 0, -4), ch=(6, 0, -4), nod=-2,
           fL=(0.11 * wide, -0.30, 0), fR=(-0.13 * wide, 0.30, 0))
    keys = [(0, I), (8, kn0, "io"), (15, kn, "io"), (22, knb, "io"), (27, hang, "io"), (31, hang2, "io"), (34, bu, "in3"), (39, bu2, "out3"),
            (48, bu3, "io"), (58, cr, "io"), (72, IA, "io")]
    return keys, [34]


import v2a_hactions
if not NOANIM:
    v2a_hactions.build(rig, lambda key, p: WP[key](p), primary="sweep", slow=1.0, only=ONLY, wide=0.9, phase=phase)

if not ONLY:
    VL.export_glb(arm, [mesh] + p2objs, OUT_GLB)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
VL.show_p2(p2objs, False)
cam = BK.render_views(arm, body.H, TILES, extra=0.15)
# 二階型態 3/4
VL.show_p2(p2objs, True)
BK.aim(cam, -35, Vector((0, 0, body.H * 0.55)), body.H * 2.7, elev=body.H * 0.05)
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = (560, 800)
bpy.context.scene.render.filepath = os.path.join(TILES, "view_4_p2.png")
bpy.ops.render.render(write_still=True)
BK.aim(cam, 150, Vector((0, 0, body.H * 0.62)), body.H * 2.5, elev=body.H * 0.10)
bpy.context.scene.render.filepath = os.path.join(TILES, "view_5_p2back.png")
bpy.ops.render.render(write_still=True)
VL.show_p2(p2objs, False)
if not NOANIM:
    VL.render_actions(arm, body.H, TILES, cam, p2objs, n=8, only=ONLY, p2_from=1.1)
print("DONE", MODEL, flush=True)
