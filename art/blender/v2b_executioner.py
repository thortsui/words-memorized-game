"""建模 B（v2）：暗影行刑者 executioner 重建。依 art/v2/design.md §2.4、art_guide.md §4、art/reference/v2/executioner_p1/p2.jpg。
魁梧倒三角＋尖頂粗麻頭罩（一條眼縫）＋雙手巨斧（斧面比頭大、頂端矛尖、柄末金封印環）＋腰間鐵鍊與掛鎖；前臂與腳踝墨影化。
二階部件（匯出後 scale 0，遊戲在 PhaseShift 爆發時彈出）：
  P2_HoodTorn（頭罩撕開＋紫色漩渦）、P2_ShadowArmL/R（背後墨影手臂＋影斧）、P2_ChainHalo（浮起繞身的鐵鍊環）、
  P2_AxeBlade2（雙刃＋刃口紫光）、P2_InkArmL/R、P2_InkLegL/R（墨影擴大）。
用法：blender --background --factory-startup --python v2b_executioner.py -- [--quick] [--noanim] [--only A,B] [--noviews]
"""
import bpy, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from soul_humanoid_lib import *
from soul_humanoid_parts import *
import soul_humanoid_bake as BK
from soul_humanoid_anim import Rig, W, HW
import v2b_hum as VH

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOANIM = "--noanim" in argv
NOVIEWS = "--noviews" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_executioner"
BAKEKEY = "v2b_executioner"
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v2b_executioner.blend")
TILES = os.path.join(HERE, "preview", "_tiles", "v2b_executioner")
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

reset_scene()
body = Body(H=2.2, bulk=1.30, wf=1.22, head=0.30, hz=0.47, neck=0.052, limb=1.14, arm_a=60)
U = body.U; R = body.R; RL = body.RL; j = body.j; hs = body.head; H = body.H
B = Builder()
rnd = random.Random(21)

# ---------------------------------------------------------------- 材質（底色偏亮一點：遊戲場地暗，靠明度與磨亮邊緣讀形）
D = BK.define_mat
IRON = dict(tex="Metal024", size=0.6, U=U, val=0.58, sat=0.5, tint=(0.82, 0.82, 0.88), rust=0.32, rust_tint=(0.30, 0.20, 0.15),
            wear=1.0, wear_col=(0.66, 0.66, 0.70), dirt=0.7, bump=0.7)
D("iron", "A", **IRON)
D("leatherBk", "A", tex="Leather026", size=0.30, U=U, val=1.7, sat=0.45, tint=(0.22, 0.19, 0.18), rough=0.62, metal=0.0, dirt=0.7,
  wear=0.8, wear_col=(0.34, 0.29, 0.25), bump=0.7, stain=0.30, stain_col=(0.06, 0.03, 0.018))
D("leather", "A", tex="Leather026", size=0.32, U=U, val=2.0, tint=(0.34, 0.22, 0.13), rough=0.7, metal=0.0, dirt=0.9, wear=0.6,
  wear_col=(0.42, 0.31, 0.21), bump=0.6)
D("skin", "A", tex="Leather026", size=0.18, U=U, val=2.3, sat=0.25, tint=(0.62, 0.45, 0.37), rough=0.62, metal=0.0, dirt=0.9,
  dirt_col=(0.07, 0.05, 0.04), bump=0.35, stain=0.35, stain_col=(0.10, 0.06, 0.05), ao_shade=0.75)
D("pants", "A", tex="Fabric030", size=0.24, U=U, tint=(0.10, 0.092, 0.088), rough=0.95, metal=0.0, dirt=0.7, bump=0.8,
  mud=(0.05, 0.55, 0.7), mud_col=(0.08, 0.06, 0.045))
D("void", "A", color=(0.004, 0.003, 0.005), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("burlap", "B", tex="Fabric030", size=0.22, U=U, val=2.3, sat=0.55, tint=(0.62, 0.49, 0.33), rough=0.95, metal=0.0, dirt=0.7, wear=0.4,
  wear_col=(0.55, 0.45, 0.32), bump=1.0, stain=0.55, stain_col=(0.050, 0.022, 0.012), mud=(0.25, 0.75, 0.5),
  mud_col=(0.10, 0.07, 0.045), ao_shade=0.72)
D("blade", "B", tex="Metal024", size=0.7, U=U, val=0.85, sat=0.4, rust=0.26, rust_tint=(0.30, 0.20, 0.15), wear=1.0,
  wear_col=(0.78, 0.78, 0.80), dirt=0.5, bump=0.6, seed=4.0, stain=0.45, stain_col=(0.07, 0.035, 0.02))
D("ironB", "B", seed=9.0, **IRON)
D("wood", "B", tex="Wood066", size=0.4, U=U, val=1.1, tint=(0.40, 0.30, 0.22), rough=0.75, metal=0.0, dirt=0.8, wear=0.5,
  wear_col=(0.45, 0.35, 0.25), bump=0.6)
D("leatherB", "B", tex="Leather026", size=0.30, U=U, val=1.8, tint=(0.24, 0.15, 0.10), rough=0.72, metal=0.0, dirt=0.9, wear=0.5,
  wear_col=(0.32, 0.23, 0.16), bump=0.6)
D("gold", "B", tex="Metal024", size=0.5, U=U, val=1.7, sat=0.0, tint=(1.0, 0.70, 0.30), rough=0.32, metal=1.0, dirt=0.6,
  dirt_col=(0.06, 0.04, 0.015), wear=0.6, wear_col=(1.0, 0.85, 0.5), bump=0.3)
PURPLE = (0.43, 0.19, 1.0)          # #b07aff（線性）
VH.define_glow("g_eye", PURPLE, 3.0, final="Glow_Eye")
VH.define_glow("g_rune", PURPLE, 0.9, final="Glow_Rune")
VH.define_glow("g_weapon", PURPLE, 1.1, final="Glow_Weapon")
VH.define_ink("ink", color=(0.012, 0.008, 0.02), alpha=0.88, emit=(0.30, 0.12, 0.60), emit_strength=0.06, final="Ink")
# 二階
VH.define_glow("p2_edge", PURPLE, 2.2, final="P2_Glow_Edge")
VH.define_glow("p2_shadow", PURPLE, 1.6, final="P2_Glow_Shadow")
VH.define_ink("p2_ink", color=(0.02, 0.01, 0.035), alpha=0.85, emit=(0.30, 0.12, 0.65), emit_strength=0.12, final="P2_InkShadow")


def make_void_tex(path, S=256):
    """紫色漩渦（emissive 貼圖）：中心黑、旋臂發亮。"""
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = (x + 0.5) / S * 2 - 1; cy = (y + 0.5) / S * 2 - 1
    r = np.sqrt(cx * cx + cy * cy); th = np.arctan2(cy, cx)
    arm = 0.5 + 0.5 * np.sin(3 * (th + 5.5 * r))
    arm = arm ** 2.2
    k = np.clip(1 - r, 0, 1)
    inten = arm * np.clip(r * 2.2, 0, 1) * k ** 0.6 + 0.35 * np.exp(-((r - 0.85) / 0.12) ** 2)
    inten = np.clip(inten * 2.2 + 0.08, 0, 1)
    col = np.stack([0.43 * inten + 0.5 * inten ** 4, 0.19 * inten + 0.45 * inten ** 4, 1.0 * inten, np.ones_like(inten)], -1)
    im = bpy.data.images.new("v2b_void", S, S, alpha=True)
    im.colorspace_settings.name = "sRGB"
    im.pixels.foreach_set(np.clip(col, 0, 1).astype(np.float32).ravel())
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)
    return path


VOID_TEX = make_void_tex(os.path.join(BK.BAKED, "v2b_exe_void.png")) if os.path.isdir(BK.BAKED) else None
VH.define_glow("p2_void", PURPLE, 2.4, final="P2_Glow_Void", tex=VOID_TEX, base=(0.01, 0.0, 0.02))

# ---------------------------------------------------------------- 小工具


def wisp(name, base, d, length, side, mat, w, width=0.018, curl=0.25, n=7, seed=0, up=0.0):
    """墨影絲：從 base 往 d 方向飄、捲曲、尾端變細的扁帶。"""
    r_ = random.Random(seed)
    d = d.normalized(); side = (side - d * side.dot(d)).normalized(); nrm = d.cross(side)
    ph = r_.uniform(0, 6.28)
    pts = []; rad = []
    for k in range(n):
        s = k / (n - 1)
        p = base + d * (length * s) + side * (curl * length * math.sin(s * 2.6 + ph) * s) + nrm * (0.3 * curl * length * math.sin(s * 4 + ph * 2) * s) + Z * (up * length * s * s)
        pts.append(p)
        rad.append((width * U * (1 - s) ** 0.8 + 0.0015 * U, 0.0025 * U * (1 - 0.6 * s)))
    return B.tube(name, pts, rad, 4, mat, w, flat=side, cap=False, sharp=80)


def cone(name, base, d, ln, r0, mat, w, segs=6):
    d = d.normalized()
    return B.tube(name, [base - d * r0 * 0.3, base + d * ln * 0.55, base + d * ln], [r0, r0 * 0.45, 0.0008 * U], segs, mat, w, sharp=30)


def W_hood(co):
    k = smooth((co.z - (j["Neck"].z - 0.02)) / 0.16)
    return {"Head": k, "Spine2": 1 - k}


# ---------------------------------------------------------------- 軀幹
under_torso(B, body, "leatherBk", texel=0.4)
cuirass(B, body, "leatherBk", off=0.016, keel=0.010, globe=0.024, belly=0.03, rivet_mat="iron")
# 胸前鉚釘鐵板（左右胸、腹部三道橫帶）
for sx in (1, -1):
    a0, a1 = (8, 74) if sx > 0 else (-74, -8)

    def pec_off(u, v, ang, t, sx=sx):
        return 0.058 * R + 0.012 * R * math.sin(math.pi * v) * math.sin(math.pi * u)
    B.shell(f"PecPlate{sx}", body.torso, body.tz(0.60), lambda u, sx=sx: body.tz(0.86 - 0.08 * (u if sx > 0 else 1 - u)), a0, a1, 10, 5,
            "iron", "Spine2", off=pec_off, rim=0.006 * R)
    pts = []
    for q in range(5):
        a = lerp(a0 + 6, a1 - 6, q / 4)
        t = body.tz(0.615)
        pts.append((body.torso.pt(t, a, 0.064 * R), body.torso.nrm(t, a)))
    B.rivets(f"PecRivets{sx}", pts, "iron", "Spine2", r=0.008 * U)
for k in range(3):
    t0_ = 0.36 + k * 0.075
    B.shell(f"AbBand{k}", body.torso, body.tz(t0_), body.tz(t0_ + 0.055), -64, 64, 12, 2, "iron", {"Spine": 0.6, "Spine2": 0.4},
            off=lambda u, v, ang, t, k=k: (0.062 + 0.004 * k) * R + 0.004 * R * math.sin(math.pi * v), rim=0.005 * R)
# 胸口刻痕符紋（弱紫）：抽象筆畫
for sx in (1, -1):
    for q, (a, t, la, lt) in enumerate(((30, 0.74, 14, 0.06), (46, 0.70, -8, 0.05), (38, 0.66, 18, 0.0))):
        a *= sx; la *= sx
        p0 = body.torso.pt(body.tz(t), a, 0.0715 * R)
        p1 = body.torso.pt(body.tz(t + lt), a + la, 0.0715 * R)
        nn = body.torso.nrm(body.tz(t), a)
        B.tube(f"ChestRune{sx}{q}", [p0, p1], [(0.0012 * U, 0.0045 * U)] * 2, 4, "g_rune", "Spine2", flat=nn, cap=True)

# 腰帶兩條＋大扣
zb = body.tz(0.29)
belt(B, body, zb, "leather", {"Spine": 0.4, "Hips": 0.6}, h=0.075, thick=0.010, off=0.050, name="Belt1")
belt(B, body, zb - 0.085 * U, "leather", "Hips", h=0.06, thick=0.010, off=0.058, tilt=0.03, tilt_dir=90, name="Belt2")
buckle(B, body, zb, 0, "iron", {"Spine": 0.4, "Hips": 0.6}, off=0.068, size=1.7)
buckle(B, body, zb - 0.085 * U, 18, "iron", "Hips", off=0.074, size=1.3)
rp = [(body.torso.pt(zb, a, 0.064 * R), body.torso.nrm(zb, a)) for a in range(20, 360, 28) if abs(angn(a)) > 20]
B.rivets("BeltStuds", rp, "iron", {"Spine": 0.4, "Hips": 0.6}, r=0.009 * U)

# 腰前垂掛的鐵鍊（兩道垂弧）＋掛鎖
def swag(a0, a1, z0, sag, off0, link=0.055):
    raw = []
    for q in range(60):
        s = q / 59
        a = lerp(a0, a1, s)
        z = z0 - sag * U * math.sin(math.pi * s) ** 1.1
        o = off0 * R + 0.05 * R * math.sin(math.pi * s)
        raw.append(body.torso.pt(z, a, o))
    out = [raw[0]]; acc = 0.0
    for q in range(1, len(raw)):
        acc += (raw[q] - raw[q - 1]).length
        if acc >= link * U:
            out.append(raw[q]); acc = 0.0
    return out


def padlock(name, top, w="Hips", s=1.0, face=-Y):
    side = Z.cross(face).normalized()
    c = top - Z * 0.048 * U * s
    B.tube(f"{name}Shackle", [c + side * -0.020 * U * s + Z * 0.02 * U * s, c + side * -0.020 * U * s + Z * 0.05 * U * s, c + Z * 0.066 * U * s,
                              c + side * 0.020 * U * s + Z * 0.05 * U * s, c + side * 0.020 * U * s + Z * 0.02 * U * s], [0.0065 * U * s] * 5, 6, "ironB", w)
    box(B, f"{name}Body", c - Z * 0.012 * U * s, side, Z, face, 0.036 * U * s, 0.040 * U * s, 0.016 * U * s, "ironB", w, exp=3.5, segs=12)
    box(B, f"{name}Hole", c - Z * 0.012 * U * s + face * 0.016 * U * s, side, Z, face, 0.006 * U * s, 0.010 * U * s, 0.002 * U * s, "void", w, exp=2, segs=8)


sw1 = swag(-100, 100, zb - 0.04 * U, 0.20, 0.075)
chain_links(B, sw1, "iron", w_skirt(body, zb, zb - 0.3 * U, 0.35), link_r=0.018 * U, wire=0.0055 * U, name="Swag1")
sw2 = swag(-70, 115, zb - 0.10 * U, 0.12, 0.085)
chain_links(B, sw2, "iron", w_skirt(body, zb, zb - 0.3 * U, 0.35), link_r=0.016 * U, wire=0.005 * U, name="Swag2")
for q, (a, ln) in enumerate(((-38, 0.20), (6, 0.30), (44, 0.16), (78, 0.24))):
    top = body.torso.pt(zb - 0.07 * U, a, 0.080 * R)
    nn = body.torso.nrm(zb - 0.07 * U, a)
    pts = [top - Z * (ln * U * k / 4) + nn * 0.01 * k * U for k in range(5)]
    chain_links(B, pts, "iron", w_skirt(body, zb, zb - 0.4 * U, 0.4), link_r=0.016 * U, wire=0.005 * U, name=f"Hang{q}")
    padlock(f"Lock{q}", pts[-1] - Z * 0.01 * U, w_skirt(body, zb, zb - 0.4 * U, 0.4), s=1.15, face=nn)

# 撕裂粗麻腰擺（前長後短，帶暗褐污漬）
af_pts = [V(0, -0.135 * R - 0.05, zb), V(0, -0.20 * R, zb - 0.28 * U), V(0, -0.22 * R, zb - 0.56 * U), V(0, -0.23 * R, zb - 0.82 * U)]
ab_pts = [V(0, 0.13 * R + 0.05, zb), V(0, 0.22 * R, zb - 0.30 * U), V(0, 0.25 * R, zb - 0.60 * U)]
af_names = chain_names("ApronF", 3); ab_names = chain_names("ApronB", 2)
cloth_panel(B, "Loin", lambda u: body.torso.pt(zb - 0.03 * U, lerp(-48, 48, u), 0.062 * R), lambda u: V(math.sin(math.radians(lerp(-48, 48, u))) * 0.5, -1, 0).normalized(),
            0.84 * U, "burlap", w_chain_pts("Hips", af_names, af_pts), nu=20, nv=14, flare=0.05, rag=0.22, deep=0.25, fold_amp=0.012 * U,
            fold_n=2.2, holes=0.04, seed=31, spread=0.08 * U)
cloth_panel(B, "LoinBack", lambda u: body.torso.pt(zb - 0.02 * U, lerp(118, 242, u), 0.060 * R), lambda u: Y.copy(), 0.62 * U, "burlap",
            w_chain_pts("Hips", ab_names, ab_pts), nu=16, nv=10, flare=0.08, rag=0.22, deep=0.2, fold_amp=0.016 * U, fold_n=2.5, holes=0.05,
            seed=32, spread=-0.10 * U)
mail_skirt(B, body, "leatherBk", zb - 0.02 * U, body.tz(-0.06), flare=0.035, rag=0.03, seed=8)

# ---------------------------------------------------------------- 手臂：裸露上臂、大圓肩甲、尖刺護腕、墨影前臂
B.both(B.shell("UpperArmSkin", body.uarm, -0.02, body.ua_len + 0.012, 0, 360, 12, 5, "skin", body.w_elbow(), off=0.004 * RL, texel=0.8))
B.both(B.shell("ForearmSkin", body.farm, -0.012, body.fa_len, 0, 360, 12, 5, "leatherBk", body.w_elbow(), off=0.0, texel=0.8))
B.both(pauldron(B, body, "iron", size=1.20, lames=3, haute=0.0, rivet_mat="iron", tilt=0.50))
B.both(arm_armor(B, body, "iron", rivet_mat="iron", rerebrace=False, wing=False, cuff=0.040, ridge=0.006))
Lf = body.fa_len
for q, a in enumerate((50, 110, 170, 230, 290)):
    for tf in (0.40, 0.66):
        t = Lf * tf
        p = body.farm.pt(t, a + (25 if tf > 0.5 else 0), 0.030 * RL)
        nn = body.farm.nrm(t, a + (25 if tf > 0.5 else 0))
        B.both(cone(f"BracerSpike{q}{int(tf * 10)}", p, nn, 0.055 * U, 0.013 * U, "iron", "ForearmL"))
body.set_grip(0.026 * U)
B.mirror_only(hand(B, body, "leatherBk"))
hand(B, body, "leatherBk", open_amt=0.25)
# 墨影：手腕到手背飄散（一階，少量）
for q in range(5):
    a = 40 + q * 70
    p = body.farm.pt(Lf * (0.78 + 0.05 * (q % 2)), a, 0.03 * RL)
    nn = body.farm.nrm(Lf * 0.8, a)
    d = (nn * 0.8 - body.fd * 0.3 + Z * 0.25).normalized()
    B.both(wisp(f"ArmInk{q}", p, d, (0.16 + 0.05 * (q % 3)) * U, body.fd, "ink", "ForearmL", width=0.016, curl=0.35, seed=q + 3, up=0.3))

# ---------------------------------------------------------------- 腿：短粗、尖刺護膝、重靴、腳踝墨影
under_leg(B, body, "pants")
B.both(leg_armor(B, body, "iron", rivet_mat="iron", cuisse=False, wing=True))
B.both(cone("KneeSpike", j["ShinL"] + FWD * 0.09 * RL + Z * 0.01, (FWD + X * 0.35 + Z * 0.1), 0.075 * U, 0.016 * U, "iron", {"ShinL": 1.0}))
B.both(cone("KneeSpikeO", j["ShinL"] + X * 0.08 * RL, (X + FWD * 0.2), 0.05 * U, 0.012 * U, "iron", {"ShinL": 1.0}))
B.both(sabaton(B, body, "leatherBk", pointed=0.2, sole_mat="iron"))
B.both(strap_ring(B, body.shin, body.sh_len * 0.80, "leather", "ShinL", width=0.03 * U, off=0.020 * RL, name="BootStrap", rivet_mat="iron", rivet_ang=95))
for q in range(5):
    a = q * 72 + 20
    p = body.shin.pt(body.sh_len * 0.93, a, 0.03 * RL)
    nn = body.shin.nrm(body.sh_len * 0.93, a)
    d = (nn - Z * 0.35).normalized()
    B.both(wisp(f"AnkleInk{q}", p, d, (0.14 + 0.05 * (q % 2)) * U, Z, "ink", {"ShinL": 0.5, "FootL": 0.5}, width=0.014, curl=0.3, seed=q + 11, up=0.0))

# ---------------------------------------------------------------- 尖頂粗麻頭罩（垂到胸前成披肩、下緣破爛、一條眼縫）
nzv = j["Neck"].z
HB = j["Head"].z
HC = V(0, -0.006 * U, H - hs * 0.52)
PROF = [(HB + 0.01, 0.170, 0.190, -0.008), (H - hs * 0.52, 0.176, 0.200, -0.008), (H - hs * 0.18, 0.150, 0.168, 0.0),
        (H + 0.04, 0.100, 0.110, 0.010), (H + 0.15, 0.050, 0.055, 0.020), (H + 0.25, 0.018, 0.020, 0.030), (H + 0.31, 0.002, 0.002, 0.036)]
hcut = rag_profile(36, random.Random(7), 0.25)


def prof_at(s):
    x = s * (len(PROF) - 1); k = min(int(x), len(PROF) - 2); f = x - k
    f = f * f * (3 - 2 * f)
    return tuple(lerp(PROF[k][i], PROF[k + 1][i], f) for i in range(4))


def hood_fn(u, v):
    ang = u * 360
    a = angn(ang)
    VN = 0.36
    if v <= VN:
        s = v / VN
        fr = math.exp(-(a / 50) ** 2); bk = math.exp(-((abs(a) - 180) / 60) ** 2)
        k = min(int(round(u * 36)), 36)
        th = 0.68 * fr + 0.90 * (1 - fr) * (1 - bk) + 0.74 * bk + 0.05 * hcut[k]
        t = lerp(th, 1.02, s ** 0.9)
        o = (0.030 * (1 - s) + 0.034) * R + 0.008 * R * math.sin(math.radians(ang) * 7 + 1.3) * (1 - s)
        return body.torso.pt(body.tz(t), ang, o)
    s = (v - VN) / (1 - VN)
    p0 = body.torso.pt(body.tz(1.02), ang, 0.034 * R)
    z, rx, ry, yc = prof_at(s)
    lean = 0.04 * s * s
    ring = V(math.sin(math.radians(ang)) * rx, yc + lean - math.cos(math.radians(ang)) * ry, z)
    ring += V(math.sin(math.radians(ang)), -math.cos(math.radians(ang)), 0) * (0.006 * math.sin(ang * 0.11 + 7 * s)) * (1 - s)
    if s < 0.18:
        return p0.lerp(ring, smooth(s / 0.18))
    return ring


B.grid("Hood", 36, 24, hood_fn, "burlap", W_hood, [V(0, 0, z) for z in (body.tz(0.8), nzv, HC.z, H, H + 0.2)], closed_u=True, sharp=60, texel=1.1)
B.parts[-1]["cloth"] = 0.006
# 頭罩內部黑（萬一從下面看到）
B.ellipsoid("HeadVoid", HC, (X, Y, Z), (0.11, 0.125, 0.15), 12, 8, "void", "Head")
# 正面縫線（由頂到眼縫上方）
seam = [hood_fn(0.0, 0.36 + 0.64 * s) + V(0, -0.006, 0) for s in np.linspace(0.62, 0.96, 7)]
B.tube("HoodSeam", seam, [0.0045 * U] * len(seam), 5, "leatherB", "Head")
ez = H - hs * 0.50
ef = hood_fn(0.0, 0.36 + 0.64 * 0.29)
eye_c = V(0, ef.y - 0.004, ez)
box(B, "EyeSlitDark", eye_c + Y * 0.002, X, Z, -Y, 0.075 * U, 0.016 * U, 0.008 * U, "void", "Head", exp=3, segs=10)
box(B, "EyeSlitGlow", eye_c - Y * 0.004, X, Z, -Y, 0.060 * U, 0.0055 * U, 0.004 * U, "g_eye", "Head", exp=3, segs=10)
B.tube("EyeGold", [eye_c + V(-0.07 * U, -0.005, 0.0105 * U), eye_c + V(0, -0.008, 0.012 * U), eye_c + V(0.07 * U, -0.005, 0.0105 * U)],
       [0.0026 * U] * 3, 5, "gold", "Head")
for q in range(7):
    x = (q - 3) * 0.021 * U
    B.tube(f"EyeStitch{q}", [eye_c + V(x - 0.004, -0.009, 0.026 * U), eye_c + V(x + 0.004, -0.009, -0.024 * U)], [0.0022 * U] * 2, 4, "leatherB", "Head")

# ---------------------------------------------------------------- 巨斧（右手握；斧刃朝「刃口」方向；頂端矛尖；柄末金封印環）
gcR = Body.mir(body.grip_c)
AX = Body.mir(body.hand_v).normalized()                 # 斧柄軸
EG = Body.mir(body.hand_a); EG = (EG - AX * EG.dot(AX)).normalized()   # 斧刃朝向
SD = AX.cross(EG).normalized()


def P_ax(a, e, s=0.0):
    return gcR + AX * (a * U) + EG * (e * U) + SD * (s * U)


B.tube("Haft", [P_ax(-0.64, 0), P_ax(-0.2, 0), P_ax(0.4, 0), P_ax(1.08, 0)], [0.024 * U, 0.025 * U, 0.024 * U, 0.022 * U], 8, "wood", "Weapon", flat=EG)
for a0, a1 in ((-0.12, 0.16), (-0.56, -0.28)):
    n = 9
    B.tube(f"Wrap{a0}", [P_ax(lerp(a0, a1, q / (n - 1)), 0) for q in range(n)], [(0.0285 + (0.002 if q % 2 else 0)) * U for q in range(n)], 8, "leatherB", "Weapon", flat=EG)
for a in (-0.60, 0.18, 0.66, 0.74):
    B.tube(f"Collar{a}", [P_ax(a - 0.018, 0), P_ax(a + 0.018, 0)], [0.032 * U] * 2, 8, "ironB", "Weapon", flat=EG)
for q in range(6):
    ang = q * math.pi / 3
    dd = EG * math.cos(ang) + SD * math.sin(ang)
    cone(f"HaftSpike{q}", P_ax(0.70, 0) + dd * 0.03 * U, dd + AX * 0.3, 0.05 * U, 0.009 * U, "ironB", "Weapon")
# 金封印環＋柄尾
B.ellipsoid("PommelCap", P_ax(-0.67, 0), (EG, SD, AX), (0.034 * U, 0.034 * U, 0.03 * U), 10, 6, "gold", "Weapon")
rc = P_ax(-0.67 - 0.075, 0)
ring = [rc + (AX * math.cos(t) + EG * math.sin(t)) * 0.058 * U for t in np.linspace(0, 2 * math.pi, 17)]
B.tube("SealRing", ring, [(0.012 * U, 0.016 * U)] * 17, 6, "gold", "Weapon", flat=SD, cap=False)
# 斧頭套筒
box(B, "AxeSocket", P_ax(0.86, 0), EG, SD, AX, 0.045 * U, 0.036 * U, 0.13 * U, "ironB", "Weapon", exp=3.5, segs=12)


def blade_fn(sign=1.0, scale=1.0):
    """斧刃：u 繞截面一圈（上面→下面），v 從斧頸到刃口。回傳 (fn, 刃口點列函式)。"""
    def A_neck(q):
        return lerp(0.97, 0.74, q)

    def A_edge(q):
        return lerp(1.16, 0.46, q) * 1.0

    def E_edge(q):
        return 0.52 - 0.13 * (2 * q - 1) ** 2 - 0.05 * max(0, 2 * q - 1) ** 3

    def AE(q, v):
        vv = v ** 1.35
        a = lerp(A_neck(q), A_edge(q), vv)
        # 上緣兩個尖齒
        if q < 0.06:
            a += 0.045 * math.exp(-((v - 0.46) / 0.07) ** 2) + 0.03 * math.exp(-((v - 0.70) / 0.05) ** 2)
        e = lerp(0.04, E_edge(q), v)
        c = 0.86
        return c + (a - c) * scale, e * scale

    def T(q, v):
        return lerp(0.034, 0.004, v ** 0.6) * (math.sin(math.pi * q) ** 0.35 + 0.08)

    def fn(u, v):
        if u <= 0.5:
            q, sd = u * 2, 1.0
        else:
            q, sd = 2 - 2 * u, -1.0
        a, e = AE(q, v)
        return P_ax(a, e * sign, sd * T(q, v) * 0.5)

    def face(q, v, sd):
        a, e = AE(q, v)
        return P_ax(a, e * sign, sd * (T(q, v) * 0.5 + 0.0016))
    return fn, face, AE


fnA, faceA, AEA = blade_fn(1.0)
B.grid("AxeBlade", 28, 10, fnA, "blade", "Weapon", [P_ax(0.86, 0.0), P_ax(0.86, 0.3)], closed_u=True, cap1=True, sharp=50, texel=1.0)
# 矛尖
B.tube("SpearTip", [P_ax(1.05, 0), P_ax(1.14, 0), P_ax(1.26, 0), P_ax(1.36, 0)],
       [(0.026 * U, 0.012 * U), (0.034 * U, 0.013 * U), (0.020 * U, 0.008 * U), (0.0015 * U, 0.001 * U)], 4, "blade", "Weapon", flat=EG, sharp=20)
# 斧面符紋（原創抽象筆畫，兩面都有）
GLYPHS = [[((0.0, 0.0), (0.0, 1.0)), ((0.0, 0.6), (0.6, 0.95))], [((0.0, 1.0), (0.5, 0.0)), ((0.5, 0.0), (0.8, 0.7))],
          [((0.1, 0.0), (0.1, 0.9)), ((0.1, 0.9), (0.7, 0.6)), ((0.4, 0.3), (0.8, 0.1))], [((0.0, 0.5), (0.8, 0.5)), ((0.4, 0.0), (0.3, 1.0))],
          [((0.0, 0.0), (0.4, 1.0)), ((0.4, 1.0), (0.8, 0.0))], [((0.2, 0.0), (0.2, 1.0)), ((0.6, 0.2), (0.6, 0.8))]]


def runes(face, prefix, mat, w, mk=None):
    obs = []
    rows = [(0.30, 0.42, 4), (0.58, 0.62, 4)]
    gi = 0
    for (q0, v0, n) in rows:
        for k in range(n):
            g = GLYPHS[(gi * 5 + 2) % len(GLYPHS)]; gi += 1
            for sd in (1, -1):
                for si, (p0, p1) in enumerate(g):
                    qa, va = q0 + 0.11 * k + 0.07 * p0[0] - 0.035, v0 + 0.13 * (p0[1] - 0.5)
                    qb, vb = q0 + 0.11 * k + 0.07 * p1[0] - 0.035, v0 + 0.13 * (p1[1] - 0.5)
                    pa, pb = face(qa, va, sd), face(qb, vb, sd)
                    obs.append(B.tube(f"{prefix}{gi}{si}{sd}", [pa, pb], [(0.0012 * U, 0.0062 * U)] * 2, 4, mat, w, flat=SD))
    if mk:
        VH.mark(obs, mk)
    return obs


runes(faceA, "AxeRune", "g_weapon", "Weapon")
# 刃口上方的血鏽？（由材質 stain 處理）

# ---------------------------------------------------------------- 二階部件
P2 = {}
# P2_AxeBlade2：反側第二片斧刃＋兩邊刃口紫光
fnB, faceB, AEB = blade_fn(-1.0, 0.92)
P2["P2_AxeBlade2"] = [B.grid("AxeBlade2", 28, 10, fnB, "blade", "Weapon", [P_ax(0.86, 0.0), P_ax(0.86, -0.3)], closed_u=True, cap1=True, sharp=50)]
P2["P2_AxeBlade2"] += runes(faceB, "AxeRune2", "g_weapon", "Weapon")
for nm, AE, sg in (("EdgeGlowA", AEA, 1.0), ("EdgeGlowB", AEB, -1.0)):
    pts = []
    for q in np.linspace(0.02, 0.98, 14):
        a, e = AE(q, 1.0)
        pts.append(P_ax(a, e * sg + 0.006 * sg))
    P2["P2_AxeBlade2"].append(B.tube(nm, pts, [(0.012 * U, 0.004 * U)] * len(pts), 4, "p2_edge", "Weapon", flat=SD))
VH.mark(P2["P2_AxeBlade2"], "P2_AxeBlade2")

# P2_HoodTorn：臉部撕開露出紫色漩渦＋翻開的破布
VC = eye_c + V(0, -0.020, -0.01)
VR = 0.105 * U


def void_fn(u, v):
    a = 2 * math.pi * u
    r = VR * v
    return VC + V(math.cos(a) * r, -0.026 * U * v * v + 0.004, math.sin(a) * r * 1.15)


vo = B.grid("VoidDisc", 24, 6, void_fn, "p2_void", "Head", VC + Y * 0.2, closed_u=True, texel=1.0)
uvl = vo.data.uv_layers.active
for poly in vo.data.polygons:
    for li in poly.loop_indices:
        co = vo.data.vertices[vo.data.loops[li].vertex_index].co
        uvl.data[li].uv = (0.5 + (co.x - VC.x) / (2.05 * VR), 0.5 + (co.z - VC.z) / (2.05 * VR * 1.15))
torn = [vo]
rr = random.Random(4)
rim = []
for q in range(25):
    a = 2 * math.pi * q / 24
    r = VR * (1.0 + 0.10 * rr.uniform(-1, 1))
    rim.append(VC + V(math.cos(a) * r, -0.026 * U - 0.004 + 0.008 * rr.uniform(-1, 1), math.sin(a) * r * 1.15))
torn.append(B.tube("TornRim", rim, [(0.011 * U, 0.006 * U)] * 25, 5, "burlap", "Head", cap=False))
# 翻開的破布片（臉的左側往外下垂）
def flap_fn(u, v):
    a = math.radians(lerp(-40, 70, u))
    base = VC + V(math.cos(a) * VR, -0.03 * U, math.sin(a) * VR * 1.15)
    out = V(math.cos(a), -0.9, math.sin(a) * 0.4).normalized()
    cut = 0.6 + 0.4 * math.sin(u * 17.0) * math.sin(u * 5.0)
    return base + out * (0.11 * U * v * cut) - Z * (0.06 * U * v * v)


fl = B.grid("TornFlap", 10, 4, flap_fn, "burlap", "Head", VC + Y * 0.1)
fl["cloth"] = 0.005
torn.append(fl)
VH.mark(torn, "P2_HoodTorn")

# P2_ChainHalo：浮起繞身的鐵鍊環（半徑約 0.28H）＋掛鎖
CH_Z = zb - 0.04 * U
CH_R = 0.28 * H
halo = []
pts = []
NL = 30
for q in range(NL + 1):
    a = 2 * math.pi * q / NL
    pts.append(V(math.sin(a) * CH_R, -math.cos(a) * CH_R * 0.92, CH_Z + 0.05 * U * math.sin(3 * a)))
halo += chain_links(B, pts, "ironB", "ChainHalo", link_r=0.028 * U, wire=0.0075 * U, name="HaloLink")
for q, a in enumerate((0.6, 2.7, 4.6)):
    top = V(math.sin(a) * CH_R, -math.cos(a) * CH_R * 0.92, CH_Z + 0.05 * U * math.sin(3 * a))
    hp = [top - Z * 0.05 * U * k for k in range(3)]
    halo += chain_links(B, hp, "ironB", "ChainHalo", link_r=0.018 * U, wire=0.0055 * U, name=f"HaloHang{q}")
    nn = V(math.sin(a), -math.cos(a), 0)
    n0 = len(B.parts)
    padlock(f"HaloLock{q}", hp[-1] - Z * 0.01 * U, "ChainHalo", s=1.4, face=nn)
    halo += B.parts[n0:]
VH.mark(halo, "P2_ChainHalo")

# P2_ShadowArmL/R：背後肩胛長出的墨影手臂（左握影斧、右張爪）
SA = {}
for sx in (1, -1):
    S0 = body.torso.pt(body.tz(0.80), 150 * sx, 0.03 * R)
    El = S0 + V(0.44 * sx, 0.30, 0.16)
    Hd = El + V(0.20 * sx, -0.10, 0.34)
    SA[sx] = (S0, El, Hd)
    nm = "P2_ShadowArmL" if sx > 0 else "P2_ShadowArmR"
    obs = []
    obs.append(B.tube("ShUpper", [S0 - (El - S0) * 0.1, S0.lerp(El, 0.5) + V(0, 0.03, 0.03), El], [0.10 * U, 0.088 * U, 0.072 * U], 8, "p2_ink", "Spine2"))
    obs.append(B.tube("ShFore", [El, El.lerp(Hd, 0.5), Hd], [0.074 * U, 0.066 * U, 0.054 * U], 8, "p2_ink", "Spine2"))
    obs.append(B.ellipsoid("ShHand", Hd + (Hd - El).normalized() * 0.04 * U, (X, Y, Z), (0.05 * U, 0.05 * U, 0.06 * U), 8, 6, "p2_ink", "Spine2"))
    dH = (Hd - El).normalized()
    for f in range(4):
        sp = (X * sx).cross(dH).normalized()
        base = Hd + dH * 0.07 * U + sp * (f - 1.5) * 0.026 * U
        if sx > 0:
            tip = base + dH * 0.05 * U - (Hd - S0).normalized().cross(sp) * 0.05 * U
        else:
            tip = base + dH * 0.13 * U + sp * (f - 1.5) * 0.03 * U - Y * 0.04 * U
        obs.append(B.tube(f"ShClaw{f}", [base, base.lerp(tip, 0.6) + dH * 0.02 * U, tip], [0.014 * U, 0.010 * U, 0.002 * U], 5, "p2_ink", "Spine2"))
    # 發光筋（沿手臂的紫線）與飄散墨絲
    for k in range(3):
        a = k * 2.1
        off = V(math.cos(a), math.sin(a) * 0.5, math.sin(a)).normalized()
        obs.append(B.tube(f"ShVein{k}", [S0 + off * 0.07 * U, El + off * 0.062 * U, Hd + off * 0.045 * U], [(0.004 * U, 0.004 * U)] * 3, 4, "p2_shadow", "Spine2"))
    for k in range(4):
        p = S0.lerp(Hd, 0.2 + 0.25 * k)
        obs.append(wisp(f"ShWisp{k}", p, (V(0.3 * sx, 0.8, -0.4)).normalized(), 0.22 * U, Z, "p2_ink", "Spine2", width=0.02, curl=0.3, seed=40 + k))
    if sx > 0:
        # 影斧：柄＋單刃（墨＋紫刃光）
        ax = V(0.28 * sx, -0.30, 0.90).normalized()
        gc = Hd + dH * 0.06 * U
        eg = (X * sx - ax * (X * sx).dot(ax)).normalized()
        sd_ = ax.cross(eg).normalized()
        obs.append(B.tube("ShHaft", [gc - ax * 0.45 * U, gc + ax * 0.80 * U], [0.02 * U, 0.018 * U], 6, "p2_ink", "Spine2"))
        bl = []
        def sh_fn(u, v, gc=gc, ax=ax, eg=eg, sd_=sd_):
            if u <= 0.5:
                q, s_ = u * 2, 1.0
            else:
                q, s_ = 2 - 2 * u, -1.0
            a = lerp(lerp(0.78, 0.58, q), lerp(0.98, 0.32, q), v ** 1.3)
            e = lerp(0.03, 0.44 - 0.12 * (2 * q - 1) ** 2, v)
            t = lerp(0.03, 0.004, v) * (math.sin(math.pi * q) ** 0.35 + 0.08)
            return gc + ax * (a * U) + eg * (e * U) + sd_ * (s_ * t * 0.5 * U)
        obs.append(B.grid("ShBlade", 20, 7, sh_fn, "p2_ink", "Spine2", [gc + ax * 0.65 * U], closed_u=True, cap1=True))
        ep = []
        for q in np.linspace(0.02, 0.98, 12):
            ep.append(sh_fn(0.25 * 0 + q * 0.5 * 0 + 0.0, 1.0) if False else gc + ax * (lerp(0.98, 0.32, q) * U) + eg * ((0.44 - 0.12 * (2 * q - 1) ** 2) * U + 0.004))
        obs.append(B.tube("ShEdge", ep, [(0.010 * U, 0.004 * U)] * len(ep), 4, "p2_edge", "Spine2", flat=sd_))
    for o in obs:
        for g in list(o.vertex_groups):
            o.vertex_groups.remove(g)
        bn = "ShadowArmL" if sx > 0 else "ShadowArmR"
        g = o.vertex_groups.new(name=bn)
        g.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    VH.mark(obs, nm)

# P2_InkArm／P2_InkLeg：墨影擴大（更多、更長的墨絲）
for sx, sfx in ((1, "L"), (-1, "R")):
    obs = []
    for q in range(8):
        a = q * 45 + 10
        t = Lf * (0.35 + 0.08 * (q % 5))
        p = body.farm.pt(t, a, 0.03 * RL)
        nn = body.farm.nrm(t, a)
        d = (nn * 0.7 - body.fd * 0.4 + Z * 0.3).normalized()
        o = wisp(f"InkArmX{q}", p, d, (0.26 + 0.07 * (q % 3)) * U, body.fd, "p2_ink", "ForearmL", width=0.022, curl=0.4, seed=60 + q, up=0.4)
        obs.append(o)
    for q in range(4):
        a = q * 90 + 45
        p = body.farm.pt(Lf * 0.6, a, 0.035 * RL)
        nn = body.farm.nrm(Lf * 0.6, a)
        obs.append(B.tube(f"InkArmVein{q}", [p, body.farm.pt(Lf * 0.95, a + 20, 0.03 * RL)], [(0.0035 * U, 0.003 * U)] * 2, 4, "p2_shadow", "ForearmL"))
    if sx < 0:
        obs = B.mirror_only(obs)
    VH.mark(obs, "P2_InkArm" + sfx)
    obs = []
    for q in range(7):
        a = q * 51
        p = body.shin.pt(body.sh_len * (0.72 + 0.04 * (q % 3)), a, 0.035 * RL)
        nn = body.shin.nrm(body.sh_len * 0.8, a)
        d = (nn - Z * 0.25 + V(0, 0.4, 0)).normalized()
        obs.append(wisp(f"InkLegX{q}", p, d, (0.24 + 0.08 * (q % 3)) * U, Z, "p2_ink", "ShinL", width=0.02, curl=0.35, seed=80 + q, up=0.15))
    if sx < 0:
        obs = B.mirror_only(obs)
    VH.mark(obs, "P2_InkLeg" + sfx)

# ---------------------------------------------------------------- 骨架、烘焙
SL, EL, _ = SA[1]; SR, ER, _ = SA[-1]
arm = build_armature("BossExecutioner", body, weapon=(gcR, gcR + AX * 0.30 * U),
                     chains=[("ApronF", "Hips", af_pts), ("ApronB", "Hips", ab_pts)],
                     extra=[("ShadowArmL", "Spine2", SL, SL + (EL - SL).normalized() * 0.3), ("ShadowArmR", "Spine2", SR, SR + (ER - SR).normalized() * 0.3),
                            ("ChainHalo", "Hips", V(0, 0, CH_Z), V(0, 0, CH_Z + 0.3))])
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)
DETAIL_OF = {"iron": "metal", "ironB": "metal", "blade": "metal", "gold": "metal", "leatherBk": "leather", "leather": "leather",
             "leatherB": "leather", "burlap": "cloth", "pants": "cloth", "wood": "wood", "skin": "leather"}.get
mesh = VH.assemble2(B, BAKEKEY, size=(TEXS, TEXS), bake=not QUICK, quick=QUICK, detail_of=DETAIL_OF, U=U)
BONE_OF = {"P2_AxeBlade2": "Weapon", "P2_HoodTorn": "Head", "P2_ChainHalo": "ChainHalo", "P2_ShadowArmL": "ShadowArmL",
           "P2_ShadowArmR": "ShadowArmR", "P2_InkArmL": "ForearmL", "P2_InkArmR": "ForearmR", "P2_InkLegL": "ShinL", "P2_InkLegR": "ShinR"}
parts = VH.split_parts(mesh, arm, lambda n: BONE_OF[n])
BK.bind(mesh, arm)
mesh.name = MODEL + "_mesh"
print("TRIS_MAIN", BK.tri_count(mesh), "TRIS_P2", sum(BK.tri_count(o) for o in parts.values()), flush=True)

# ---------------------------------------------------------------- 動作
legs = [("ThighL", "ShinL", 0.17 * U), ("ThighR", "ShinR", 0.17 * U), ("ShinL", "FootL", 0.13 * U), ("ShinR", "FootR", 0.13 * U)]
rig = Rig(arm, body, chains=[
    dict(names=af_names, anchor="Hips", pts=af_pts, stiff=0.07, damp=0.90, colliders=legs, out=(0, -1, 0)),
    dict(names=ab_names, anchor="Hips", pts=ab_pts, stiff=0.06, damp=0.92, colliders=legs + [("Hips", "Spine", 0.22 * U)], out=(0, 1, 0))])
rig.tip_len = 0.95 * U
rig.lie_dz = 0.08
GL = -0.40


def two(Pd, g, d, edge_, hintR=None, elL=None, gl=None):
    Pd["ikL"] = 1.0; Pd["gripL"] = GL if gl is None else gl
    Pd["elL"] = elL or (0.6, 0.3, -0.7)
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))


def one(Pd, g, d, edge_, left, hintR=None, hintL=None):
    Pd["ikL"] = 0.0
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))
    rig.reach(Pd, "L", left, hintL)


WP = {
    # 待機：雙手斜持巨斧於身前（斧頭在左上、柄尾在右下），左手握在上段
    "idle": lambda p: two(p, (-0.34, -0.30, 0.98), (0.55, -0.42, 0.72), (-0.30, -0.86, -0.27), hintR=(-0.8, 0.1, -0.6), gl=0.36, elL=(0.8, 0.1, -0.6)),
    "o_up": lambda p: two(p, (-0.06, 0.02, 1.90), (0.0, 0.70, 0.70), (0, -0.7, 0.7), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
    "o_up2": lambda p: two(p, (-0.06, 0.06, 1.93), (0.0, 0.82, 0.56), (0, -0.7, 0.7), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
    "o_hit": lambda p: two(p, (0.0, -0.74, 0.80), (0.02, -0.92, -0.38), (0, 0.38, -0.92), hintR=(-0.8, 0.4, -0.3)),
    "o_low": lambda p: two(p, (0.0, -0.74, 0.66), (0.02, -0.88, -0.47), (0, 0.47, -0.88), hintR=(-0.8, 0.4, -0.3)),
    "o_rec": lambda p: two(p, (-0.10, -0.50, 0.92), (0.1, -0.9, 0.1), (0, -0.1, -0.99)),
    "s_wind": lambda p: two(p, (-0.48, 0.10, 1.26), (-0.57, 0.82, 0.20), (-0.82, -0.57, 0), hintR=(-0.3, 0.9, -0.4)),
    "s_wind2": lambda p: two(p, (-0.50, 0.14, 1.28), (-0.45, 0.88, 0.22), (-0.88, -0.45, 0), hintR=(-0.3, 0.9, -0.4)),
    "s_hit": lambda p: two(p, (-0.02, -0.62, 1.14), (0.37, -0.93, -0.05), (0.93, 0.37, 0), hintR=(-0.8, 0.3, -0.5)),
    "s_follow": lambda p: two(p, (0.28, -0.36, 1.08), (0.91, 0.42, -0.12), (-0.42, 0.91, 0), hintR=(-0.5, -0.2, -0.8)),
    "s_settle": lambda p: two(p, (0.25, -0.38, 1.04), (0.95, 0.28, -0.16), (-0.28, 0.95, 0), hintR=(-0.5, -0.2, -0.8)),
    "enter0": lambda p: one(p, (-0.40, -0.20, 0.98), (0.10, -0.10, -0.99), (0, -1, 0.1), (0.42, -0.10, 0.76)),
    "enter1": lambda p: one(p, (-0.40, -0.22, 1.04), (0.10, -0.20, -0.97), (0, -0.97, 0.2), (0.42, -0.08, 0.84)),
    "enter2": lambda p: two(p, (-0.16, -0.40, 1.02), (0.2, -0.55, 0.8), (0.1, -0.8, -0.6)),
    "hit1": lambda p: one(p, (-0.50, -0.10, 1.30), (-0.3, 0.4, 0.85), (0, -1, 0), (0.50, -0.20, 1.20)),
    "hit2": lambda p: one(p, (-0.36, -0.26, 1.05), (0.0, 0.3, 0.95), (0, -1, 0), (0.40, -0.22, 0.95)),
    "stag1": lambda p: one(p, (-0.58, 0.05, 1.68), (-0.3, 0.6, 0.75), (0, -1, 0), (0.55, -0.20, 1.30)),
    "stag2": lambda p: one(p, (-0.62, 0.22, 1.25), (-0.5, 0.7, 0.3), (0, -1, 0), (0.48, -0.05, 1.10)),
    "stag3": lambda p: one(p, (-0.44, 0.04, 0.66), (-0.25, -0.92, -0.28), (0, 0.3, -1), (0.32, -0.10, 0.38), hintL=(0.8, 0.4, 0.0)),
    "stag4": lambda p: two(p, (-0.16, -0.30, 0.98), (0.2, -0.6, 0.75), (0.1, -0.8, -0.6)),
    "roar_gather": lambda p: two(p, (-0.14, -0.40, 0.88), (0.3, -0.75, 0.55), (0.1, -0.8, -0.6)),
    "roar": lambda p: one(p, (-0.64, -0.08, 1.48), (-0.6, -0.2, 0.75), (0, -1, 0), (0.64, -0.10, 1.30), hintL=(0.3, 0.6, -0.7)),
    "roar2": lambda p: one(p, (-0.66, -0.04, 1.53), (-0.65, -0.15, 0.75), (0, -1, 0), (0.66, -0.06, 1.35), hintL=(0.3, 0.6, -0.7)),
    "roar_end": lambda p: two(p, (-0.14, -0.42, 1.00), (0.25, -0.6, 0.75), (0.1, -0.8, -0.6)),
    "die1": lambda p: one(p, (-0.52, -0.05, 1.15), (-0.2, -0.6, 0.5), (0, -1, 0), (0.44, -0.16, 1.2)),
    "kneel": lambda p: one(p, (-0.40, -0.26, 0.46), (0.2, -0.95, -0.2), (1, 0, 0), (0.32, -0.14, 0.44), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "kneel2": lambda p: one(p, (-0.42, -0.30, 0.36), (0.25, -0.95, -0.1), (1, 0, 0), (0.32, -0.18, 0.36), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
    "t_pull": lambda p: two(p, (-0.34, 0.06, 1.02), (0.10, -1.0, 0.06), (0, 0, -1), hintR=(-0.7, 0.5, -0.5)),
    "t_thrust": lambda p: two(p, (-0.12, -0.80, 1.14), (0.06, -1.0, 0.0), (0, 0, -1), hintR=(-0.8, 0.3, -0.5)),
    "fall": lambda p: one(p, (-0.48, -1.00, 0.12), (-0.2, -0.97, 0.0), (1, 0, 0), (0.40, -0.86, 0.10), hintR=(-0.9, 0.2, 0.3), hintL=(0.9, 0.2, 0.3)),
    # PhaseShift 專用
    "ps_drag": lambda p: one(p, (-0.46, 0.20, 0.72), (-0.25, 0.85, -0.46), (0, -0.48, -0.88), (0.46, -0.18, 1.0), hintR=(-0.8, 0.3, -0.4)),
    "ps_drag2": lambda p: one(p, (0.08, -0.55, 0.78), (0.70, -0.60, -0.39), (-0.27, 0.23, -0.93), (0.50, -0.25, 1.05), hintR=(-0.6, -0.3, -0.7)),
    "ps_slam": lambda p: two(p, (0.0, -0.70, 0.56), (0.02, -0.78, -0.62), (0, 0.62, -0.78), hintR=(-0.8, 0.4, -0.3)),
    "ps_cross": lambda p: two(p, (-0.30, -0.36, 1.08), (0.62, -0.30, 0.72), (-0.45, -0.85, 0.05), hintR=(-0.8, 0.0, -0.6), gl=0.36, elL=(0.8, 0.1, -0.6)),
}

if not NOANIM:
    import v2b_exec_actions
    v2b_exec_actions.build(rig, lambda key, p: WP[key](p), primary="over", slow=1.05, only=ONLY, wide=1.30)


# ---------------------------------------------------------------- 額外骨頭（影臂、鍊環）的程序動作
def extra_bones():
    ad = arm.animation_data
    if not ad:
        return
    fps = 30
    for tr in ad.nla_tracks:
        act = bpy.data.actions[tr.name]
        meta = rig.meta.get(tr.name, {})
        loop = meta.get("loop", False)
        f0, f1 = act.frame_range
        N = int(round(f1 - f0)) + 1
        dur = (N - 1) / fps
        hits = meta.get("hits", [])
        fr = np.arange(N, dtype=float)
        t = fr / fps
        # 鍊環：繞直立軸慢轉（循環片段轉整數圈）
        rev = max(1, round(0.22 * dur)) if loop else 0.22 * dur
        ang = 2 * math.pi * rev * (t / max(dur, 1e-3))
        qs = [Quaternion((0, 1, 0), a) for a in ang]
        _write(act, "ChainHalo", qs)
        # 影臂：呼吸擺動＋命中前舉起、命中時劈下
        for side, bn in ((1, "ShadowArmL"), (-1, "ShadowArmR")):
            cyc = max(1, round(dur / 1.6)) if loop else dur / 1.6
            sway = 0.10 * np.sin(2 * math.pi * cyc * t / max(dur, 1e-3) + (0 if side > 0 else 1.7))
            chop = np.zeros(N)
            for h in hits:
                chop += -0.55 * np.exp(-((t - (h - 0.22)) / 0.14) ** 2) + 0.75 * np.exp(-((t - (h + 0.02)) / 0.07) ** 2) * (t > h - 0.05) \
                    + 0.4 * np.exp(-((t - (h + 0.15)) / 0.18) ** 2)
            if tr.name == "PhaseShift":
                # 爆發瞬間伸出：從收攏（往前縮）彈開
                chop += -0.6 * np.clip(1 - (t - 1.0) / 0.25, 0, 1) * (t > 1.0)
            qs = [Quaternion((1, 0, 0), float(sway[k] + chop[k])) @ Quaternion((0, 0, 1), float(0.12 * side * sway[k])) for k in range(N)]
            _write(act, bn, qs)


def _write(act, bn, qs):
    path = f'pose.bones["{bn}"].rotation_quaternion'
    arr = np.array([[q.w, q.x, q.y, q.z] for q in qs])
    for k in range(1, len(arr)):
        if np.dot(arr[k], arr[k - 1]) < 0:
            arr[k] *= -1
    for c in range(4):
        fc = act.fcurves.find(path, index=c)
        if fc is None:
            fc = act.fcurves.new(path, index=c, action_group=bn)
            fc.keyframe_points.add(len(arr))
        n = min(len(fc.keyframe_points), len(arr))
        co = np.empty(n * 2)
        co[0::2] = np.arange(n, dtype=float) + act.frame_range[0]
        co[1::2] = arr[:n, c]
        fc.keyframe_points.foreach_set("co", co)
        fc.update()


if not NOANIM:
    extra_bones()

if not ONLY:
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    VH.export_glb(arm, [mesh] + list(parts.values()), OUT_GLB)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("TRIS_FINAL", BK.tri_count(mesh) + sum(BK.tri_count(o) for o in parts.values()), flush=True)

# ---------------------------------------------------------------- 預覽
os.makedirs(TILES, exist_ok=True)
VH.show_parts(parts, False)
if not NOVIEWS:
    cam = BK.render_views(arm, H, TILES)
    VH.show_parts(parts, True)
    VH.set_rest(arm)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 560, 800
    VH.render_still(cam, -35, Vector((0, 0, H * 0.55)), H * 2.55, os.path.join(TILES, "view_4_p2_threeq.png"), elev=H * 0.05)
    VH.render_still(cam, 20, Vector((0, 0, H * 0.55)), H * 2.55, os.path.join(TILES, "view_5_p2_front.png"), elev=H * 0.05)
    VH.render_still(cam, 150, Vector((0, 0, H * 0.6)), H * 2.55, os.path.join(TILES, "view_6_p2_back.png"), elev=H * 0.08)
    VH.render_still(cam, -25, Vector((0, -0.1, H * 0.85)), H * 1.0, os.path.join(TILES, "close_3_p2_head.png"), elev=H * 0.02)
    VH.show_parts(parts, False)
else:
    cam = BK.setup_preview(H)
if not NOANIM:
    VH.show_parts(parts, False)
    BK.render_actions(arm, H, TILES, cam, n=10, only=ONLY)
    # 二階型態的 PhaseShift／IdleAggro／Attack 連拍（顯示 P2）
    VH.show_parts(parts, True)
    ad = arm.animation_data
    sc = bpy.context.scene
    for nm in ("IdleAggro", "Combo3"):
        if ONLY and nm not in ONLY:
            continue
        act = bpy.data.actions[nm]; ad.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        for k in range(10):
            f = int(round(f0 + (f1 - f0) * k / 9)); sc.frame_set(f)
            sc.render.filepath = os.path.join(TILES, f"act_9{0 if nm == 'IdleAggro' else 1}_{nm}P2_{k}_f{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    ad.action = None
print("DONE", MODEL, flush=True)
