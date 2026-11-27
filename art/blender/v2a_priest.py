"""v2（建模 A）Boss 3：霜冠祭司 priest。依 art/v2/design.md §2.3、art_guide.md §3、art/reference/v2/priest_p1/p2.jpg。
高瘦＋拖地長袍（下擺冰柱垂落）＋兜帽披肩＋放射狀冰晶冠＋蒼白凹陷的臉（雙眼覆薄冰）＋銀柄冰尖長槍＋腰間闔起的經書（金扣）。
二階「永凍禱詞」：P2_CrownHalo（頭後冰晶光環，IdleAggro 中緩慢旋轉）、P2_CrownGrow（冰冠加長）、P2_FloatingBook（翻開的發光經書）、
P2_IceShards（袍擺外一圈貼地冰刺）、P2_Veins_*（臉頰與手背冰藍血管紋）。
改用 soul_humanoid_* 人形骨架（原本 build_boss_priest.py 是提燈法杖，與 v2 規格不符），PhaseShift 依分鏡（2.5 s，爆發 1.2 s）。
用法：blender --background --factory-startup --python v2a_priest.py -- [--quick] [--nobake] [--noanim] [--only A,B]
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
MODEL = "boss_priest"
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v2a_" + MODEL + ".blend")
TILES = os.path.join(HERE, "preview", "_tiles", "v2a_" + MODEL)
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

reset_scene()
body = Body(H=2.3, bulk=0.80, wf=0.84, head=0.245, hz=0.55, arm_len=1.08, limb=0.84)
U = body.U; R = body.R; j = body.j; hs = body.head
B = Builder()
rnd = random.Random(17)
k = U / 1.278

# ---------------------------------------------------------------- 材質
D = BK.define_mat
D("robe", "A", tex="Fabric030", size=0.32, U=U, tint=(0.80, 0.82, 0.85), sat=0.15, val=2.6, rough=0.9, metal=0.0, dirt=0.7, wear=0.5,
  wear_col=(0.80, 0.84, 0.88), bump=0.9, mud=(0.0, 0.5, 0.55), mud_col=(0.30, 0.33, 0.36), ao_shade=0.8, stain=0.35, stain_col=(0.36, 0.38, 0.40))
D("robe2", "A", tex="Fabric030", size=0.26, U=U, tint=(0.60, 0.62, 0.65), sat=0.15, val=2.2, rough=0.92, metal=0.0, dirt=0.8, wear=0.5,
  wear_col=(0.70, 0.74, 0.78), bump=0.9, ao_shade=0.8, seed=4.0)
D("leather", "A", tex="Leather026", size=0.30, U=U, val=2.4, sat=0.3, tint=(0.24, 0.25, 0.27), rough=0.75, metal=0.0, dirt=0.9, wear=0.5,
  wear_col=(0.55, 0.58, 0.62), bump=0.6)
D("skin", "A", tex="Rust009", size=0.5, U=U, sat=0.06, val=1.9, tint=(0.80, 0.80, 0.78), rough=0.7, metal=0.0, dirt=1.0, bump=0.5,
  dirt_col=(0.10, 0.11, 0.13), seed=3.0)
D("void", "A", color=(0.006, 0.007, 0.009), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("gold", "A", tex="Metal024", size=0.4, U=U, tint=(0.70, 0.52, 0.22), sat=0.45, val=0.95, metal=0.85, rough=0.4, wear=0.5,
  wear_col=(0.80, 0.66, 0.32), dirt=1.0, bump=0.5, seed=11.0)
D("silver", "B", tex="Metal024", size=0.4, U=U, tint=(0.62, 0.65, 0.68), sat=0.1, val=1.1, metal=0.9, rough=0.35, wear=0.6,
  wear_col=(0.85, 0.88, 0.9), dirt=1.0, bump=0.5, seed=8.0)
D("ice", "B", color=(0.50, 0.68, 0.78), flat_rough=0.18, dirt=0.25, dirt_col=(0.22, 0.33, 0.42), ao_shade=0.35, bump=0.25, seed=2.0)
D("book", "B", tex="Leather026", size=0.2, U=U, val=2.0, tint=(0.22, 0.14, 0.09), rough=0.7, metal=0.0, dirt=0.9, wear=0.6,
  wear_col=(0.42, 0.30, 0.20), bump=0.7)
D("paper", "B", color=(0.62, 0.58, 0.48), flat_rough=0.9, dirt=0.8, bump=0.3)
D("cloth", "B", tex="Fabric030", size=0.26, U=U, tint=(0.45, 0.47, 0.50), sat=0.15, val=1.8, rough=0.92, metal=0.0, dirt=0.8, bump=0.8, seed=6.0)
BLUE = "#8fe3ff"
VL.glow_mat("Glow_Eye", BLUE, 0.45)
VL.glow_mat("Glow_Rune", BLUE, 0.5)
VL.glow_mat("Glow_Weapon", BLUE, 0.6)
VL.glow_mat("P2_Glow_Halo", BLUE, 1.4)
VL.glow_mat("P2_Glow_Book", BLUE, 2.2)
VL.glow_mat("P2_Glow_Veins", BLUE, 1.6)


def icicle(name, p, ln, r, w, mat="ice", d=None):
    d = (d or -Z).normalized()
    return B.tube(name, [p - d * r * 0.5, p + d * ln * 0.45, p + d * ln], [r, r * 0.55, 0.0008], 5, mat, w, texel=0.6)


def crystal(name, p, d, ln, r, w, mat="ice", segs=6):
    d = d.normalized()
    return B.tube(name, [p - d * r, p + d * ln * 0.18, p + d * ln * 0.78, p + d * ln], [r * 0.8, r, r * 0.7, 0.001], segs, mat, w, texel=0.6, sharp=20)


# ---------------------------------------------------------------- 身體與內層
under_torso(B, body, "robe2", texel=0.9, off=0.004)
under_arm(B, body, "robe2")
under_leg(B, body, "cloth", texel=0.6)
B.both(sabaton(B, body, "leather", pointed=1.1, lames=False))
body.set_grip(0.018 * U)
B.mirror_only(hand(B, body, "skin"))
hand(B, body, "skin")

# 拖地長袍（下擺外擴成三角形剪影，破爛下緣掛冰柱）
Z_TOP = body.tz(0.30)
HEM = 0.035 * U
nu_s = 40
cut = rag_profile(nu_s, random.Random(4), 0.18)


def skirt_off(z, ang):
    v = clamp((Z_TOP - z) / (Z_TOP - HEM))
    a = angn(ang)
    front = 0.75 + 0.25 * math.cos(math.radians(a))
    return 0.020 * R + 0.30 * k * v ** 1.25 * front + 0.016 * k * math.sin(math.radians(ang) * 7 + 1.0) * v + 0.009 * k * math.sin(math.radians(ang) * 17) * v


def skirt_pt(z, ang, extra=0.0):
    return body.torso.pt(z, ang, skirt_off(z, ang) + extra)


def hem_z(u):
    kk = int(round(u * nu_s)) % nu_s
    return HEM + 0.14 * k * cut[kk] * (0.4 + 0.6 * ((kk * 7) % 3) / 2)


sk = B.shell("Skirt", body.torso, hem_z, Z_TOP, 0, 360, nu_s, 12, "robe", w_skirt(body, body.hzv + 0.02, HEM, 0.78),
             off=lambda u, v, ang, t: skirt_off(t, ang), texel=1.0)
sk["cloth"] = 0.008
for q in range(nu_s):
    u = (q + 0.5) / nu_s
    ang = u * 360
    z = hem_z(u)
    if q % 2 == 0 or rnd.random() < 0.4:
        p = skirt_pt(z + 0.01 * k, ang, -0.004)
        icicle(f"HemIce{q}", p, rnd.uniform(0.04, 0.11) * k, rnd.uniform(0.010, 0.016) * k, w_skirt(body, body.hzv + 0.02, HEM, 0.78)(p))
# 前襟兩條金色原創符紋帶（胸口到下擺）
for s in (1, -1):
    pts = []
    for q in range(16):
        z = lerp(body.tz(0.92), HEM + 0.10 * k, q / 15)
        ang = s * lerp(9, 13, q / 15)
        if z > Z_TOP:
            p = body.torso.pt(z, ang, 0.03 * R)
        else:
            p = skirt_pt(z, ang, 0.006)
        pts.append(p)
    wts = [w_skirt(body, body.hzv + 0.02, HEM, 0.78)(p) if p.z < Z_TOP else body.w_torso()(p) for p in pts]
    for q in range(len(pts) - 1):
        a, b2 = pts[q], pts[q + 1]
        ww = wts[q]
        nrm = (a - Vector((0, 0, a.z))).normalized()
        B.tube(f"GoldBand{s}_{q}", [a, b2], [(0.026 * k, 0.004 * k)] * 2, 4, "gold", ww, flat=nrm.cross(Z).normalized(), exp=4)
        # 原創符紋：帶上的短筆畫（深色刻痕）
        c = a.lerp(b2, 0.5) + nrm * 0.006
        B.tube(f"Glyph{s}_{q}", [c - Z * 0.02 * k + nrm.cross(Z) * 0.008 * s, c + Z * 0.018 * k - nrm.cross(Z) * 0.006 * s], [(0.004 * k, 0.002 * k)] * 2, 4, "void", ww)
# 腰帶與經書（右腰側，皮封金扣金角，用短鍊掛著）
zb = body.tz(0.30)
belt(B, body, zb, "leather", {"Spine": 0.5, "Hips": 0.5}, h=0.038, off=0.04)
buckle(B, body, zb, 0, "silver", {"Spine": 0.5, "Hips": 0.5}, off=0.05)
bn = body.torso.nrm(zb, -100)
bside = Z.cross(bn).normalized()
bc = body.torso.pt(zb, -100, 0.06 * R) + bn * 0.05 * k - Z * 0.17 * k
B.tube("BookChain", [body.torso.pt(zb, -100, 0.045 * R), bc + Z * 0.09 * k], [0.005 * k] * 2, 5, "silver", "Hips")
box(B, "BookCover", bc, bside, Z, bn, 0.085 * k, 0.115 * k, 0.040 * k, "book", "Hips", exp=6)
box(B, "BookPages", bc + bn * 0.002, bside, Z, bn, 0.080 * k, 0.108 * k, 0.034 * k, "paper", "Hips", exp=8)
for sx in (-1, 1):
    for sz in (-1, 1):
        B.ellipsoid(f"BookCorner{sx}{sz}", bc + bside * 0.08 * k * sx + Z * 0.11 * k * sz + bn * 0.035 * k, (bside, Z, bn), (0.018 * k, 0.018 * k, 0.012 * k),
                    8, 4, "gold", "Hips")
B.tube("BookClasp", [bc + bside * 0.09 * k + bn * 0.02 * k, bc + bside * 0.09 * k + bn * 0.044 * k, bc + bside * 0.02 * k + bn * 0.045 * k],
       [(0.012 * k, 0.004 * k)] * 3, 4, "gold", "Hips", flat=Z)
B.ellipsoid("BookSeal", bc + bn * 0.044 * k, (bside, Z, bn), (0.03 * k, 0.03 * k, 0.006 * k), 10, 3, "gold", "Hips")

# 寬口袖（掛冰柱）、披肩、兜帽
def sleeve():
    S = body.farm
    L = body.fa_len
    obs = [B.shell("Sleeve", S, -0.02 * U, L * 0.98, 0, 360, 20, 6, "robe", "ForearmL",
                   off=lambda u, v, ang, t: 0.035 * R + 0.06 * k * smooth(t / L) ** 1.6 + 0.03 * k * smooth(t / L) * max(0, math.cos(math.radians(ang - 180))),
                   texel=1.0)]
    obs[0]["cloth"] = 0.007
    for q in range(9):
        ang = q * 40 + 10
        t = L * 0.97
        p = S.pt(t, ang, 0.035 * R + 0.06 * k + 0.03 * k * max(0, math.cos(math.radians(ang - 180))))
        if p.z < S.center(t).z + 0.02:
            obs.append(icicle(f"SleeveIce{q}", p, rnd.uniform(0.03, 0.07) * k, 0.008 * k, "ForearmL"))
    obs.append(B.shell("SleeveCuff", S, L * 0.90, L * 0.97, 0, 360, 20, 1, "gold", "ForearmL",
                       off=lambda u, v, ang, t: 0.036 * R + 0.06 * k * smooth(t / L) ** 1.6 + 0.03 * k * smooth(t / L) * max(0, math.cos(math.radians(ang - 180))) + 0.004,
                       rim=0.003))
    return obs


B.both(sleeve())
B.both([B.shell("UArmRobe", body.uarm, -0.02, body.ua_len, 0, 360, 14, 4, "robe", body.w_elbow(), off=0.03 * R, texel=1.0)])
mt = mantle(B, body, "robe", t0=0.55, t1=1.12, off=0.030, rag=0.10, drop=0.06, front_drop=0.04, back_drop=0.10, seed=5, collar=0.05, folds=9, fold_amp=0.02)
mrnd = random.Random(8)
for q in range(22):
    ang = q * (360 / 22) + mrnd.uniform(-4, 4)
    a = angn(ang)
    side = math.exp(-((abs(a) - 90) / 45) ** 2); fr = math.exp(-(a / 55) ** 2); bk = math.exp(-((abs(a) - 180) / 60) ** 2)
    z = body.tz(0.55) - 0.06 * U * side - 0.04 * U * fr - 0.10 * U * bk + 0.02
    p = body.torso.pt(z, ang, (0.030 + 0.035 * side + 0.022) * R)
    icicle(f"MantleIce{q}", p, mrnd.uniform(0.03, 0.08) * k, 0.010 * k, {"Spine2": 0.8, "Spine": 0.2})
hood = Surf(V(0, 0.01 * U, body.head_base - 0.08 * U), Z, [(0, 0.66 * hs, 0.62 * hs, 0, 0.02 * U), (0.06 * U, 0.53 * hs, 0.55 * hs, 0, 0.026 * U),
                                                        (0.17 * U, 0.46 * hs, 0.54 * hs, 0, 0.030 * U), (0.23 * U, 0.36 * hs, 0.44 * hs, 0, 0.030 * U),
                                                        (0.265 * U, 0.16 * hs, 0.22 * hs, 0, 0.03 * U)])
hd = B.shell("Hood", hood, 0.0, 0.265 * U, 50, 310, 26, 8, "robe", {"Head": 0.85, "Neck": 0.15}, off=0.006, rim=0.006, texel=1.0)
B.shell("HoodLining", hood, 0.02 * U, 0.23 * U, 54, 306, 22, 6, "void", {"Head": 0.85, "Neck": 0.15}, off=-0.004)

# ---------------------------------------------------------------- 臉：蒼白凹陷的骷髏感，雙眼覆薄冰
hc = V(0, -0.010 * U, body.H - hs * 0.52)


def skull_dent(d, u, v):
    r = 1.0
    for sx in (-1, 1):
        e = Vector((sx * 0.42, -0.88, 0.12)).normalized()
        r -= 0.20 * math.exp(-((d - e).length / 0.27) ** 2)
        e2 = Vector((sx * 0.80, -0.48, -0.40)).normalized()
        r -= 0.16 * math.exp(-((d - e2).length / 0.25) ** 2)      # 凹頰
    e = Vector((0, -0.97, -0.26)).normalized()
    r -= 0.10 * math.exp(-((d - e).length / 0.15) ** 2)
    if d.z < -0.2:
        r -= 0.22 * smooth((-d.z - 0.2) / 0.6) * (0.4 + 0.6 * abs(d.x))
    for sx in (-1, 1):
        e = Vector((sx * 0.62, -0.72, -0.30)).normalized()
        r += 0.07 * math.exp(-((d - e).length / 0.2) ** 2)          # 顴骨
    return r


rad = (0.31 * hs, 0.38 * hs, 0.46 * hs)
B.ellipsoid("Skull", hc, (X, Y, Z), rad, 24, 16, "skin", "Head", dent=skull_dent, texel=1.6)
jc = hc + V(0, -0.05 * hs, -0.44 * hs)
B.ellipsoid("Jaw", jc, (X, Y, Z), (0.20 * hs, 0.26 * hs, 0.11 * hs), 14, 8, "skin", "Head", texel=1.4,
            dent=lambda d, u, v: 1 - 0.25 * smooth((d.y - 0.1) / 0.6))
B.ellipsoid("MouthLine", hc + V(0, -0.30 * hs, -0.36 * hs), (X, Z, -Y), (0.09 * hs, 0.010 * hs, 0.01 * hs), 10, 3, "void", "Head")
for sx in (-1, 1):
    e = Vector((sx * 0.42, -0.88, 0.12)).normalized()
    p = hc + V(e.x * rad[0], e.y * rad[1], e.z * rad[2]) * 0.80
    B.ellipsoid(f"Socket{sx}", p, (X, Z, e), (0.11 * hs, 0.085 * hs, 0.02 * hs), 10, 4, "void", "Head", v0=0, v1=0.5, texel=0.5)
    B.ellipsoid(f"EyeIce{sx}", p + e * 0.012 * hs, (X, Z, e), (0.105 * hs, 0.075 * hs, 0.022 * hs), 10, 4, "Glow_Eye", "Head", v0=0, v1=0.5)

# ---------------------------------------------------------------- 冰晶冠（一階 5 根大尖晶＋小尖晶，放射狀向上）
CC = V(0, 0.005 * U, body.H - 0.02 * U)
CR = 0.36 * hs
B.tube("Circlet", [CC + V(math.sin(a) * CR, -math.cos(a) * CR * 1.12, 0) for a in [i * 2 * math.pi / 24 for i in range(25)]], [(0.012 * k, 0.018 * k)] * 25, 6, "silver", "Head")
B.tube("CircletRune", [CC + V(math.sin(a) * (CR + 0.011 * k), -math.cos(a) * (CR + 0.011 * k) * 1.12, 0) for a in [math.radians(x) for x in range(-70, 75, 10)]],
       [(0.003 * k, 0.006 * k)] * 15, 4, "Glow_Rune", "Head")
crown = [(0, 0.30, 0.030, 0), (-24, 0.22, 0.024, 8), (24, 0.22, 0.024, 8), (-50, 0.16, 0.020, 18), (50, 0.16, 0.020, 18),
         (-12, 0.10, 0.013, 4), (12, 0.10, 0.013, 4), (-36, 0.09, 0.012, 12), (36, 0.09, 0.012, 12), (-75, 0.10, 0.014, 26), (75, 0.10, 0.014, 26),
         (180, 0.12, 0.016, -10), (150, 0.10, 0.014, -14), (-150, 0.10, 0.014, -14), (110, 0.09, 0.013, 20), (-110, 0.09, 0.013, 20)]
for q, (a, ln, r0, lean) in enumerate(crown):
    ar = math.radians(a)
    p = CC + V(math.sin(ar) * CR, -math.cos(ar) * CR * 1.12, 0.005)
    out = V(math.sin(ar), -math.cos(ar), 0)
    d = (Z + out * math.tan(math.radians(lean + 8))).normalized()
    crystal(f"Crown{q}", p, d, ln * k, r0 * k, "Head")

# ---------------------------------------------------------------- 長槍：銀細柄＋冰質葉形槍頭（側刺）
gcR = Body.mir(body.grip_c); ax = Body.mir(body.hand_v); edge = Body.mir(body.hand_a)
edge = (edge - ax * edge.dot(ax)).normalized()
side = ax.cross(edge)
BUTT, SOCK, TIP = -0.92 * k, 0.86 * k, 1.20 * k


def hp(s, e=0.0, sd=0.0):
    return gcR + ax * s + edge * e + side * sd


B.tube("Shaft", [hp(BUTT), hp(BUTT * 0.5), hp(0), hp(SOCK * 0.5), hp(SOCK)], [0.0165 * k] * 5, 8, "silver", "Weapon", texel=0.8)
for q, s0 in enumerate((BUTT + 0.02, -0.40, -0.08, 0.10, 0.45, SOCK - 0.05)):
    B.tube(f"ShaftRing{q}", [hp(s0 * k - 0.018 * k), hp(s0 * k), hp(s0 * k + 0.018 * k)], [0.019 * k, 0.022 * k, 0.019 * k], 8, "silver", "Weapon")
B.tube("ButtSpike", [hp(BUTT - 0.12 * k), hp(BUTT - 0.03 * k), hp(BUTT + 0.02 * k)], [0.001, 0.016 * k, 0.018 * k], 6, "silver", "Weapon")
B.tube("Grip", [hp(-0.12 * k), hp(0.12 * k)], [0.019 * k] * 2, 8, "leather", "Weapon")
B.tube("Socket", [hp(SOCK - 0.06 * k), hp(SOCK + 0.04 * k)], [0.022 * k, 0.026 * k], 8, "silver", "Weapon")
blade = [hp(SOCK + 0.02 * k), hp(SOCK + 0.08 * k), hp(SOCK + 0.16 * k), hp(SOCK + 0.24 * k), hp(TIP + 0.06 * k), hp(TIP + 0.18 * k)]
B.tube("IceBlade", blade, [(0.020 * k, 0.012 * k), (0.045 * k, 0.014 * k), (0.058 * k, 0.014 * k), (0.050 * k, 0.012 * k), (0.026 * k, 0.008 * k), (0.001, 0.001)],
       6, "ice", "Weapon", flat=edge, sharp=15)
for sg in (1, -1):
    b0 = hp(SOCK + 0.05 * k, sg * 0.03 * k)
    B.tube(f"Spur{sg}", [b0, hp(SOCK + 0.02 * k, sg * 0.09 * k), hp(SOCK + 0.05 * k, sg * 0.14 * k)], [(0.014 * k, 0.008 * k), (0.008 * k, 0.005 * k), (0.001, 0.001)],
           4, "ice", "Weapon", flat=ax)
    B.tube(f"BladeRune{sg}", [hp(SOCK + 0.06 * k, 0, sg * 0.0145 * k), hp(SOCK + 0.20 * k, 0, sg * 0.0150 * k), hp(TIP + 0.08 * k, 0, sg * 0.0085 * k)],
           [(0.0045 * k, 0.0015 * k)] * 3, 4, "Glow_Weapon", "Weapon", flat=edge)
for q in range(4):
    icicle(f"BladeIce{q}", hp(SOCK + (0.02 + q * 0.06) * k, (0.03 - q * 0.02) * k, 0.0), rnd.uniform(0.03, 0.06) * k, 0.006 * k, "Weapon")
TIPP = hp(TIP + 0.18 * k)

# ---------------------------------------------------------------- 二階部件
HC = V(0, 0.16 * k, body.H - 0.10 * U)     # 光環中心（頭後）
halo = []
HRAD = 0.56 * k
for q in range(12):
    a0 = q * 30 + rnd.uniform(-3, 3)
    pts = []
    for i in range(7):
        a = math.radians(a0 + i * 4.0)
        rr = HRAD * (1 + 0.03 * math.sin(i * 1.7 + q))
        pts.append(HC + V(math.cos(a) * rr, 0.02 * math.sin(i + q) * k, math.sin(a) * rr))
    halo.append(B.tube(f"Halo{q}", pts, [0.006 * k, 0.016 * k, 0.020 * k, 0.020 * k, 0.017 * k, 0.012 * k, 0.003 * k], 6, "ice", "HaloSpin", texel=0.6))
    halo.append(B.tube(f"HaloGlow{q}", [p - Y * 0.012 * k + (p - HC).normalized() * 0.006 * k for p in pts[1:-1]], [0.0055 * k] * 5, 5, "P2_Glow_Halo", "HaloSpin"))
    for t in range(3):
        p = pts[1 + t * 2]
        o = (p - HC).normalized()
        d = (o * (1 if t % 2 == 0 else -0.6) + Vector((0, rnd.uniform(-0.3, 0.3), 0)) + o.cross(Y) * rnd.uniform(-0.6, 0.6)).normalized()
        halo.append(crystal(f"HaloThorn{q}_{t}", p, d, rnd.uniform(0.06, 0.13) * k, 0.010 * k, "HaloSpin"))
for q in range(10):
    a = rnd.uniform(0, 6.28)
    rr = HRAD * rnd.uniform(0.75, 1.25)
    p = HC + V(math.cos(a) * rr, rnd.uniform(-0.05, 0.05), math.sin(a) * rr)
    halo.append(crystal(f"HaloShard{q}", p, V(rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3), rnd.uniform(-1, 1)), rnd.uniform(0.04, 0.07) * k, 0.010 * k, "HaloSpin"))
VL.tag_p2(halo, "CrownHalo", "HaloSpin", HC)
# 冰冠加長（7–9 根）
cg = []
for q, (a, ln, r0, lean) in enumerate([(0, 0.46, 0.036, 0), (-20, 0.34, 0.03, 10), (20, 0.34, 0.03, 10), (-44, 0.27, 0.026, 20), (44, 0.27, 0.026, 20),
                                        (-68, 0.20, 0.022, 30), (68, 0.20, 0.022, 30), (-95, 0.16, 0.02, 36), (95, 0.16, 0.02, 36)]):
    ar = math.radians(a)
    p = CC + V(math.sin(ar) * CR * 0.98, -math.cos(ar) * CR * 1.10, 0.0)
    d = (Z + V(math.sin(ar), -math.cos(ar), 0) * math.tan(math.radians(lean + 10))).normalized()
    cg.append(crystal(f"CrownBig{q}", p, d, ln * k, r0 * k, "Head"))
VL.tag_p2(cg, "CrownGrow", "Head", CC)
# 翻開懸浮的經書（左前方、約左手上方），書頁發藍光
FB = V(0.40 * k, -0.42 * k, 1.62 * k)
fbn = V(-0.25, -0.55, 0.80).normalized()
fbx = V(1, 0, 0.3).normalized()
fby = fbn.cross(fbx).normalized()
book = []
for sg in (1, -1):
    pc = FB + fbx * (0.085 * k * sg) + fbn * 0.012 * k * (1 - 0.0)
    tilt = (fbx * sg * 0.25 + fbn).normalized()
    book.append(box(B, f"FBCover{sg}", pc - tilt * 0.006 * k, fbx, fby, tilt, 0.090 * k, 0.12 * k, 0.008 * k, "book", "Spine2", exp=6))
    book.append(box(B, f"FBPage{sg}", pc + tilt * 0.012 * k, fbx, fby, tilt, 0.082 * k, 0.112 * k, 0.010 * k, "P2_Glow_Book", "Spine2", exp=8))
    for sz in (-1, 1):
        book.append(B.ellipsoid(f"FBCorner{sg}{sz}", pc + fbx * 0.082 * k * sg + fby * 0.112 * k * sz, (fbx, fby, tilt), (0.016 * k, 0.016 * k, 0.010 * k), 8, 4, "gold", "Spine2"))
book.append(B.tube("FBSpine", [FB - fby * 0.12 * k, FB + fby * 0.12 * k], [0.014 * k] * 2, 6, "book", "Spine2"))
for q in range(6):
    p = FB + fbn * (0.05 + q * 0.03) * k + fbx * rnd.uniform(-0.08, 0.08) * k + fby * rnd.uniform(-0.08, 0.08) * k
    book.append(crystal(f"FBMote{q}", p, V(rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1), 0.035 * k, 0.006 * k, "Spine2", mat="P2_Glow_Book", segs=4))
VL.tag_p2(book, "FloatingBook", "Spine2", FB)
# 袍擺外一圈貼地冰刺
shards = []
for q in range(46):
    a = q * (360 / 46) + rnd.uniform(-3, 3)
    ar = math.radians(a)
    rr = rnd.uniform(0.52, 0.74) * k
    p = V(math.sin(ar) * rr, -math.cos(ar) * rr, 0.0)
    out = V(math.sin(ar), -math.cos(ar), 0)
    el = math.radians(rnd.uniform(30, 62))
    d = (out * math.cos(el) + Z * math.sin(el)).normalized()
    shards.append(crystal(f"Shard{q}", p - d * 0.03 * k, d, rnd.uniform(0.12, 0.40) * k, rnd.uniform(0.022, 0.040) * k, "Root"))
for q in range(8):
    a = math.radians(q * 45 + 22)
    p = V(math.sin(a) * 0.62 * k, -math.cos(a) * 0.62 * k, 0.0)
    shards.append(B.tube(f"ShardGlow{q}", [p * 0.85 + Z * 0.004, p * 1.05 + Z * 0.004], [(0.010 * k, 0.003 * k)] * 2, 4, "P2_Glow_Veins", "Root", flat=Z.cross(p).normalized()))
VL.tag_p2(shards, "IceShards", "Root", V(0, 0, 0.02))
# 臉頰與手背的冰藍血管紋
veins = []
for sx in (-1, 1):
    base = hc + V(sx * 0.27 * hs, -0.25 * hs, -0.10 * hs)
    pts = [base + V(sx * 0.01 * i * hs, -0.004 * i * hs, (0.07 * i - 0.004 * i * i) * hs) for i in range(6)]
    veins.append(B.tube(f"VeinCheek{sx}", [p * 1.0 + V(sx * 0.012 * hs, -0.03 * hs, 0) for p in pts], [0.006 * hs] * 6, 4, "P2_Glow_Veins", "Head"))
    pts2 = [base + V(sx * 0.03 * hs, -0.02 * hs, -0.02 * hs * i) + V(0, -0.025 * hs, 0) for i in range(4)]
    veins.append(B.tube(f"VeinJaw{sx}", pts2, [0.005 * hs] * 4, 4, "P2_Glow_Veins", "Head"))
VL.tag_p2(veins, "VeinsFace", "Head", hc)
hv = []
Wh = j["HandL"]; a_ = body.hand_a; u_ = body.hand_u; v_ = body.hand_v
for q in range(3):
    pts = [Wh - a_ * 0.04 * R + u_ * 0.040 * R + v_ * (q - 1) * 0.006 * R + a_ * (0.035 * i) * R + v_ * (q - 1) * 0.012 * i * R for i in range(4)]
    hv.append(B.tube(f"VeinHand{q}", pts, [0.0045 * R] * 4, 4, "P2_Glow_Veins", "HandL"))
VL.tag_p2(hv, "VeinsHandL", "HandL", Wh)
hvR = [B.mirror(o) for o in hv]
for o in hvR:
    o.vertex_groups.clear()
    o.vertex_groups.new(name="HandR").add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
VL.tag_p2(hvR, "VeinsHandR", "HandR", Body.mir(Wh))

# ---------------------------------------------------------------- 骨架、烘焙
tipd = ax.normalized()
arm = build_armature("BossPriest", body, weapon=(gcR, gcR + ax * 0.30 * U),
                     extra=[("Tip_Weapon", "Weapon", TIPP, TIPP + tipd * 0.10 * k), ("HaloSpin", "Head", HC, HC - Y * 0.15 * k)])
glows = VL.pull_glow(B)
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts) + VL.tri_count(glows)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)
DETAIL_OF = {"silver": "metal", "gold": "metal", "leather": "leather", "book": "leather", "robe": "cloth", "robe2": "cloth", "cloth": "cloth",
             "skin": "bone"}.get
mesh = BK.assemble(B, MODEL, size=(TEXS, TEXS), bake=not (QUICK or NOBAKE), quick=QUICK, detail_of=DETAIL_OF, U=U)
VL.join_into(mesh, glows)
p2objs = VL.split_p2(mesh, arm)
BK.bind(mesh, arm)
print("TRIS_FINAL", BK.tri_count(mesh) + VL.tri_count(p2objs), "main", BK.tri_count(mesh), "p2", VL.tri_count(p2objs), flush=True)

rig = Rig(arm, body, chains=[])
rig.tip_len = TIP + 0.18 * k
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


# 長槍：右手在前（槍頭方向＝左手→右手）
WP = {
    "idle": lambda p: two(p, (-0.16, -0.36, 1.18), (0.10, -0.20, 0.92), (0.3, -0.3, -0.9)),
    "s_wind": lambda p: two(p, (-0.20, -0.02, 1.08), (-0.18, 0.34, 1.02), (1, 0, 0)),
    "s_wind2": lambda p: two(p, (-0.22, 0.04, 1.10), (-0.20, 0.40, 1.04), (1, 0, 0)),
    "s_hit": lambda p: two(p, (-0.06, -0.78, 1.16), (-0.10, -0.42, 1.12), (1, 0, 0)),
    "s_follow": lambda p: two(p, (-0.04, -0.84, 1.12), (-0.08, -0.48, 1.10), (1, 0, 0)),
    "s_settle": lambda p: two(p, (-0.08, -0.66, 1.10), (-0.10, -0.30, 1.04), (1, 0, 0)),
    "o_up": lambda p: two(p, (-0.10, -0.18, 1.86), (0.04, 0.16, 1.96), (1, 0, 0), elL=(0.8, -0.2, -0.2)),
    "o_up2": lambda p: two(p, (-0.10, -0.12, 1.90), (0.04, 0.22, 2.00), (1, 0, 0), elL=(0.8, -0.2, -0.2)),
    "o_hit": lambda p: two(p, (-0.02, -0.80, 0.88), (0.04, -0.46, 1.16), (1, 0, 0)),
    "o_low": lambda p: two(p, (-0.02, -0.84, 0.74), (0.04, -0.52, 1.04), (1, 0, 0)),
    "o_rec": lambda p: two(p, (-0.08, -0.55, 1.00), (0.10, -0.25, 0.92), (0.3, -0.3, -0.9)),
    "enter0": lambda p: one(p, (-0.30, -0.18, 0.80), (0.02, 0.0, 1), (0, -1, 0), (0.12, -0.24, 1.18)),
    "enter1": lambda p: one(p, (-0.32, -0.22, 0.95), (0.0, -0.1, 1), (0, -1, 0), (0.12, -0.26, 1.22)),
    "enter2": lambda p: two(p, (-0.16, -0.38, 1.15), (0.10, -0.22, 0.88), (0.3, -0.3, -0.9)),
    "hit1": lambda p: two(p, (-0.36, -0.22, 1.36), (-0.02, -0.20, 1.08), (0, -1, 0)),
    "hit2": lambda p: two(p, (-0.24, -0.34, 1.12), (0.08, -0.20, 0.88), (0.3, -0.3, -0.9)),
    "stag1": lambda p: one(p, (-0.55, 0.0, 1.70), (-0.3, 0.5, 0.8), (0, -1, 0), (0.50, -0.20, 1.30)),
    "stag2": lambda p: one(p, (-0.60, 0.20, 1.30), (-0.5, 0.6, 0.5), (0, -1, 0), (0.45, -0.05, 1.10)),
    "stag3": lambda p: one(p, (-0.42, 0.06, 0.78), (-0.12, -0.15, 1), (0, -1, 0), (0.30, -0.10, 0.36), hintL=(0.8, 0.4, 0.0)),
    "stag4": lambda p: two(p, (-0.14, -0.30, 1.05), (0.12, -0.12, 0.80), (0.3, -0.3, -0.9)),
    "roar_gather": lambda p: two(p, (-0.16, -0.34, 0.95), (0.10, -0.22, 0.74), (0.3, -0.3, -0.9)),
    "roar": lambda p: one(p, (-0.62, -0.10, 1.55), (-0.35, -0.25, 0.9), (0, -1, 0), (0.62, -0.12, 1.35), hintL=(0.3, 0.6, -0.7)),
    "roar2": lambda p: one(p, (-0.64, -0.06, 1.60), (-0.40, -0.20, 0.9), (0, -1, 0), (0.64, -0.08, 1.40), hintL=(0.3, 0.6, -0.7)),
    "roar_end": lambda p: two(p, (-0.16, -0.40, 1.10), (0.10, -0.24, 0.84), (0.3, -0.3, -0.9)),
    "die1": lambda p: one(p, (-0.52, -0.05, 1.20), (-0.3, -0.5, 0.6), (0, -1, 0), (0.42, -0.16, 1.22)),
    "kneel": lambda p: one(p, (-0.36, -0.26, 0.42), (0.25, -0.94, -0.03), (1, 0, 0), (0.30, -0.14, 0.42), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "kneel2": lambda p: one(p, (-0.38, -0.30, 0.30), (0.28, -0.95, 0.0), (1, 0, 0), (0.30, -0.18, 0.34), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "t_pull": lambda p: two(p, (-0.22, -0.30, 1.02), (0.02, 0.20, 1.06), (1, 0, 0)),
    "t_thrust": lambda p: two(p, (-0.06, -1.00, 1.18), (0.00, -0.50, 1.14), (1, 0, 0)),
    "fall": lambda p: one(p, (-0.44, -1.00, 0.08), (-0.2, -0.97, 0.0), (1, 0, 0), (0.36, -0.86, 0.07), hintR=(-0.9, 0.2, 0.3), hintL=(0.9, 0.2, 0.3)),
    # PhaseShift：槍立身側、左手合於胸前禱念 → 升空 → 雙手向兩側張開 → 緩降、槍尖指向玩家
    "ps_pray": lambda p: one(p, (-0.30, -0.10, 1.08), (0.0, -0.05, 1), (0, -1, 0), (0.0, -0.30, 1.40), hintL=(0.8, 0.2, -0.5)),
    "ps_pray2": lambda p: one(p, (-0.30, -0.10, 1.12), (0.0, -0.05, 1), (0, -1, 0), (0.0, -0.31, 1.46), hintL=(0.8, 0.2, -0.5)),
    "ps_open": lambda p: one(p, (-0.72, -0.18, 1.52), (-0.25, -0.15, 1.0), (0, -1, 0), (0.74, -0.16, 1.58), hintL=(0.2, 0.6, -0.7)),
    "ps_open2": lambda p: one(p, (-0.74, -0.14, 1.58), (-0.30, -0.10, 1.0), (0, -1, 0), (0.76, -0.12, 1.64), hintL=(0.2, 0.6, -0.7)),
    "ps_point": lambda p: two(p, (-0.10, -0.62, 1.30), (-0.06, -0.20, 1.12), (1, 0, 0)),
}

FLOAT = 0.235   # 0.3 m（以主角比例 1.8 為單位）


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


import v2a_hactions
if not NOANIM:
    v2a_hactions.build(rig, lambda key, p: WP[key](p), primary="sweep", slow=1.0, only=ONLY, wide=0.75, phase=phase)
    # 光環在 IdleAggro 中緩慢旋轉：每個循環轉 30°（12 段對稱，首尾無縫）
    act = bpy.data.actions.get("IdleAggro")
    if act:
        fcs = sorted([c for c in act.fcurves if c.data_path == 'pose.bones["HaloSpin"].rotation_quaternion'], key=lambda c: c.array_index)
        if len(fcs) == 4:
            n = len(fcs[0].keyframe_points)
            for i in range(n):
                th = math.radians(30.0 * i / (n - 1))
                q = Quaternion((0, 1, 0), th)
                for c in range(4):
                    fcs[c].keyframe_points[i].co[1] = q[c]
            for c in fcs:
                c.update()
            print("HALO spin keyed", n, flush=True)

if not ONLY:
    VL.export_glb(arm, [mesh] + p2objs, OUT_GLB)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
VL.show_p2(p2objs, False)
cam = BK.render_views(arm, body.H, TILES, extra=0.15)
VL.show_p2(p2objs, True)
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = (560, 800)
BK.aim(cam, -35, Vector((0, 0, body.H * 0.55)), body.H * 2.7, elev=body.H * 0.05)
bpy.context.scene.render.filepath = os.path.join(TILES, "view_4_p2.png")
bpy.ops.render.render(write_still=True)
BK.aim(cam, 0, Vector((0, 0, body.H * 0.55)), body.H * 2.7, elev=body.H * 0.05)
bpy.context.scene.render.filepath = os.path.join(TILES, "view_5_p2front.png")
bpy.ops.render.render(write_still=True)
VL.show_p2(p2objs, False)
if not NOANIM:
    VL.render_actions(arm, body.H, TILES, cam, p2objs, n=8, only=ONLY, p2_from=1.2)
print("DONE", MODEL, flush=True)
