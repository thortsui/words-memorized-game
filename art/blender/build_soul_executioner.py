"""魂系 Boss 4：暗影行刑者（原創造型）。身高 2.2 m、寬厚；黑鐵板甲＋長皮圍裙、鉚釘鐵面罩＋兜帽、
前臂纏鐵鏈、寬刃巨劍，甲縫透出淡紫色光（獨立的 Glow 材質，遊戲可調強度）。
用法：blender --background --factory-startup --python build_soul_executioner.py -- [--quick] [--nobake] [--noanim] [--only A,B]
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
MODEL = "boss_executioner"
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")   # 未壓縮原檔；遊戲用的壓縮版由 run_soul.sh 以 gltf-transform 產生
OUT_BLEND = os.path.join(HERE, "source", MODEL + ".blend")
TILES = os.path.join(HERE, "preview", "_tiles", MODEL)
NOVIEWS = "--noviews" in argv

reset_scene()
body = Body(H=2.2, bulk=1.24, wf=1.16, head=0.275, hz=0.52, neck=0.036, limb=1.06, arm_a=56)
U = body.U; R = body.R; RL = body.RL; j = body.j; hs = body.head
B = Builder()
rnd = random.Random(13)

# ---------------------------------------------------------------- 材質
D = BK.define_mat
IRON = dict(tex="Metal024", size=0.6, U=U, val=0.30, sat=0.6, tint=(0.80, 0.80, 0.88), rust=0.30, rust_tint=(0.22, 0.15, 0.12),
            wear=0.9, wear_col=(0.34, 0.34, 0.37), dirt=0.9, bump=0.7)
D("iron", "A", **IRON)
D("mail", "A", tex="Chainmail004", size=0.26, U=U, tint=(0.22, 0.22, 0.25), metal=0.8, rough=0.55, rust=0.2, rust_tint=(0.2, 0.14, 0.11),
  dirt=1.0, bump=1.0, bump_dist=0.006, ao_shade=0.75)
D("leather", "A", tex="Leather026", size=0.32, U=U, val=2.2, tint=(0.30, 0.20, 0.13), rough=0.75, metal=0.0, dirt=0.9, wear=0.5,
  wear_col=(0.30, 0.22, 0.16), bump=0.6)
D("gambeson", "A", tex="Fabric030", size=0.22, U=U, tint=(0.06, 0.058, 0.056), rough=0.95, metal=0.0, dirt=0.8, bump=0.7)
D("void", "A", color=(0.003, 0.003, 0.004), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("apron", "B", tex="Leather026", size=0.45, U=U, val=2.4, tint=(0.25, 0.20, 0.165), rough=0.78, metal=0.0, dirt=0.8, wear=0.7,
  wear_col=(0.33, 0.27, 0.21), bump=0.8, mud=(0.15, 0.80, 0.6), mud_col=(0.10, 0.07, 0.05), stain=0.55, stain_col=(0.10, 0.035, 0.025),
  ao_shade=0.7)
D("hood", "B", tex="Fabric030", size=0.28, U=U, tint=(0.055, 0.052, 0.058), rough=0.95, metal=0.0, dirt=0.6, wear=0.5,
  wear_col=(0.14, 0.13, 0.14), bump=0.9, ao_shade=0.75)
D("blade", "B", tex="Metal024", size=0.7, U=U, val=0.55, sat=0.5, rust=0.35, rust_tint=(0.25, 0.17, 0.13), wear=1.0,
  wear_col=(0.62, 0.62, 0.66), dirt=0.6, bump=0.6, seed=4.0)
D("ironB", "B", seed=9.0, **IRON)
D("leatherB", "B", tex="Leather026", size=0.30, U=U, val=2.0, tint=(0.26, 0.17, 0.11), rough=0.75, metal=0.0, dirt=0.9, wear=0.4,
  wear_col=(0.28, 0.2, 0.14), bump=0.6)
D("glow", "G", emit=(0.42, 0.20, 1.0), emit_strength=1.3)

# ---------------------------------------------------------------- 內層與軀幹
under_torso(B, body, "mail", texel=0.4)
under_arm(B, body, "mail")
under_leg(B, body, "gambeson", texel=0.6)
mail_skirt(B, body, "mail", body.tz(0.22), body.tz(-0.46), flare=0.03, rag=0.03, seed=6)
cuirass(B, body, "iron", rivet_mat="iron", belly=0.02, globe=0.02)
gorget(B, body, "iron", off=0.016)
_, zf = fauld(B, body, "iron", n=3, h=0.05, rivet_mat="iron")
B.both(tasset(B, body, "iron", zf + 0.03 * U, length=0.24, a0=52, a1=118, off=0.036, rivet_mat="iron"))
# 甲縫的紫光：腰（胸甲與裙甲之間）、頸
B.shell("GlowWaist", body.torso, body.tz(0.285), body.tz(0.325), 0, 360, 24, 1, "glow", {"Spine": 0.5, "Spine2": 0.5}, off=0.017 * R)
B.shell("GlowNeck", body.torso, body.tz(0.985), body.tz(1.03), 0, 360, 16, 1, "glow", {"Spine2": 0.6, "Neck": 0.4}, off=0.012 * R)

# 皮圍裙：胸片＋肩帶＋前後長片
zb = body.tz(0.27)


def bib_off(u, v, ang, t):
    a = angn(ang)
    front = math.exp(-(a / 62) ** 2)
    return (0.036 + 0.022 * front * math.sin(math.pi * clamp((v + 0.05) / 0.95)) ** 1.1) * R + 0.004 * R * math.sin(ang * 0.25 + v * 5)


B.shell("ApronBib", body.torso, zb - 0.01 * U, lambda u: body.tz(0.80) - 0.02 * U * abs(u - 0.5) * 2, -56, 56, 14, 8, "apron",
        {"Spine2": 1.0}, off=bib_off, rim=0.004 * R)
for sx in (-1, 1):
    p0 = body.torso.pt(body.tz(0.79), sx * 44, 0.056 * R)
    p1 = body.torso.pt(body.tz(0.955), sx * 62, 0.046 * R)
    p2 = body.torso.pt(body.tz(0.93), sx * 125, 0.040 * R)
    p3 = body.torso.pt(body.tz(0.66), sx * 165, 0.034 * R)
    B.tube(f"ApronStrap{sx}", [p0, p1, p2, p3], [(0.022 * U, 0.005 * U)] * 4, 6, "leather", "Spine2", exp=4, flat=X * sx)
af_pts = [V(0, -0.125 * R - 0.04, zb), V(0, -0.21 * R, zb - 0.33 * U), V(0, -0.24 * R, zb - 0.66 * U), V(0, -0.26 * R, zb - 0.98 * U)]
ab_pts = [V(0, 0.13 * R + 0.04, zb), V(0, 0.23 * R, zb - 0.36 * U), V(0, 0.27 * R, zb - 0.72 * U)]
af_names = chain_names("ApronF", 3); ab_names = chain_names("ApronB", 2)
cloth_panel(B, "ApronFront", lambda u: body.torso.pt(zb, lerp(-66, 66, u), 0.040 * R), lambda u: V(math.sin(math.radians(lerp(-66, 66, u))) * 0.5, -1, 0).normalized(),
            0.98 * U, "apron", w_chain_pts("Hips", af_names, af_pts), nu=22, nv=16, flare=0.05, rag=0.12, deep=0.10, fold_amp=0.014 * U,
            fold_n=2.0, holes=0.05, seed=31, spread=0.06 * U)
cloth_panel(B, "ApronBack", lambda u: body.torso.pt(zb, lerp(112, 248, u), 0.040 * R), lambda u: Y.copy(), 0.74 * U, "apron",
            w_chain_pts("Hips", ab_names, ab_pts), nu=18, nv=12, flare=0.09, rag=0.16, deep=0.12, fold_amp=0.02 * U, fold_n=2.5, holes=0.06,
            seed=32, spread=-0.12 * U)
belt(B, body, zb, "leather", {"Spine": 0.5, "Hips": 0.5}, h=0.07, thick=0.009, off=0.048)
buckle(B, body, zb, 4, "iron", {"Spine": 0.5, "Hips": 0.5}, off=0.062, size=1.5)
strap_hang(B, body, zb - 0.02, 14, "leather", length=0.34, width=0.028, off=0.062)
pouch(B, body, zb - 0.03, -78, "leather", off=0.056, size=1.25)
rp = [(body.torso.pt(zb, a, 0.060 * R), body.torso.nrm(zb, a)) for a in range(30, 360, 24) if abs(angn(a)) > 20]
B.rivets("BeltStuds", rp, "iron", {"Spine": 0.5, "Hips": 0.5}, r=0.008 * U)

# ---------------------------------------------------------------- 手臂
pauldron(B, body, "iron", size=1.20, lames=4, haute=0.055, rivet_mat="iron", tilt=0.6)
B.mirror_only(pauldron(B, body, "iron", size=1.10, lames=4, haute=0.0, rivet_mat="iron", tilt=0.6))
B.both(arm_armor(B, body, "iron", rivet_mat="iron", cuff=0.034))
body.set_grip(0.021 * U)
B.mirror_only(hand(B, body, "iron"))
hand(B, body, "iron", open_amt=0.3)
B.both(B.shell("GlowArm", body.uarm, body.ua_len * 0.455, body.ua_len * 0.50, 0, 360, 10, 1, "glow", "UpperArmL", off=0.004 * RL))
B.both(B.shell("GlowElbow", body.farm, body.fa_len * 0.165, body.fa_len * 0.20, 0, 360, 10, 1, "glow", "ForearmL", off=0.004 * RL))
# 前臂纏鐵鏈（兩圈半）＋垂下的一段（各有一根擺動骨）
Lf = body.fa_len
cp = []
nlink = 30
for q in range(nlink + 1):
    s = q / nlink
    t = lerp(0.20, 0.90, s) * Lf
    ang = 40 + 2.5 * 360 * s
    off = (0.016 + 0.030 * smooth((s - 0.55) / 0.15) * (1 - 0.6 * smooth((s - 0.75) / 0.25))) * RL + 0.012 * U
    cp.append(body.farm.pt(t, ang, off))
B.both(chain_links(B, cp, "iron", "ForearmL", link_r=0.016 * U, wire=0.0048 * U, name="ArmChain"))
ch0 = body.farm.pt(0.88 * Lf, 250, 0.03 * RL)
ch_pts = [ch0, ch0 - Z * 0.24 * U]
dangle = [ch0 - Z * (0.24 * U * q / 6) for q in range(7)]
B.both(chain_links(B, dangle, "iron", "ChainL", link_r=0.016 * U, wire=0.0048 * U, name="HangChain"))

# ---------------------------------------------------------------- 腿
B.both(leg_armor(B, body, "iron", rivet_mat="iron"))
B.both(sabaton(B, body, "iron", pointed=0.4))
B.both(strap_ring(B, body.shin, body.sh_len * 0.32, "leather", "ShinL", width=0.026 * U, off=0.017 * RL, name="GreaveStrapA", rivet_mat="iron", rivet_ang=95))
B.both(strap_ring(B, body.shin, body.sh_len * 0.74, "leather", "ShinL", width=0.024 * U, off=0.017 * RL, name="GreaveStrapB", rivet_mat="iron", rivet_ang=95))
B.both(B.shell("GlowKnee", body.shin, body.sh_len * 0.095, body.sh_len * 0.125, 0, 360, 10, 1, "glow", "ShinL", off=0.006 * RL))

# ---------------------------------------------------------------- 頭：兜帽＋鉚釘鐵面罩
hc = V(0, -0.008 * U, body.H - hs * 0.52)
B.ellipsoid("HeadVoid", hc, (X, Y, Z), (0.33 * hs, 0.39 * hs, 0.46 * hs), 14, 8, "void", "Head", texel=0.3)
face = Surf(V(0, -0.012 * U, body.H - hs * 1.02), Z, [(0.0, 0.25 * hs, 0.31 * hs, 0, 0), (0.25 * hs, 0.335 * hs, 0.40 * hs, 0, 0),
                                                       (0.55 * hs, 0.35 * hs, 0.415 * hs, 0, 0), (0.80 * hs, 0.30 * hs, 0.36 * hs, 0, 0)])


def mask_off(u, v, ang, t):
    a = angn(ang)
    return 0.012 * hs + 0.028 * hs * math.exp(-(a / 9) ** 2) + 0.012 * hs * math.exp(-(a / 40) ** 2) * math.sin(math.pi * v)


B.shell("Mask", face, lambda u: (0.02 + 0.10 * (abs(u - 0.5) * 2) ** 2) * hs, 0.80 * hs, -62, 62, 16, 8, "iron", "Head", off=mask_off,
        rim=0.006 * hs, texel=1.4)
mp = []
for q in range(7):
    t = (0.07 + q * 0.105) * hs
    for sx in (-1, 1):
        mp.append((face.pt(t, sx * 7, mask_off(0, 0, sx * 7, t) + 0.002), face.nrm(t, sx * 7)))
for q in range(6):
    t = (0.20 + q * 0.11) * hs
    for sx in (-1, 1):
        mp.append((face.pt(t, sx * 56, mask_off(0, 0.5, sx * 56, t) + 0.002), face.nrm(t, sx * 56)))
B.rivets("MaskRivets", mp, "iron", "Head", r=0.0075 * U)
# 眼縫：一短橫一短直的狹縫，裡面透紫光
for sx in (-1, 1):
    t = 0.50 * hs; a = sx * 27
    p = face.pt(t, a, mask_off(0, 0.6, a, t) + 0.0015)
    n = face.nrm(t, a)
    sd = Z.cross(n).normalized()
    box(B, f"EyeSlitH{sx}", p, sd, Z, n, 0.040 * hs, 0.009 * hs, 0.003 * hs, "glow", "Head", exp=3, segs=8)
    box(B, f"EyeSlitV{sx}", p - Z * 0.03 * hs, sd, Z, n, 0.008 * hs, 0.034 * hs, 0.003 * hs, "glow", "Head", exp=3, segs=8)
# 兜帽：後腦與兩側包住，前緣不規則
hood = Surf(V(0, 0.004 * U, body.H - hs * 1.08), Z, [(0.0, 0.34 * hs, 0.36 * hs, 0, 0.0), (0.30 * hs, 0.40 * hs, 0.46 * hs, 0, 0.01 * U),
                                                     (0.62 * hs, 0.42 * hs, 0.50 * hs, 0, 0.012 * U), (0.86 * hs, 0.38 * hs, 0.46 * hs, 0, 0.016 * U),
                                                     (1.02 * hs, 0.26 * hs, 0.33 * hs, 0, 0.03 * U), (1.11 * hs, 0.10 * hs, 0.13 * hs, 0, 0.045 * U),
                                                     (1.135 * hs, 0.004, 0.005, 0, 0.05 * U)])
hr_ = random.Random(5)
hcut = [hr_.uniform(-1, 1) for _ in range(40)]


def hood_fn(u, v):
    # u：0~1 從右臉頰繞後腦到左臉頰；頂部在 v 接近 1 時收攏並往前蓋住額頭
    t = lerp(0.0, 1.1349 * hs, v)
    open_a = lerp(50, 4, smooth((v - 0.62) / 0.26))             # 臉部開口：往頭頂收合
    k = min(int(u * 39), 39)
    open_a += 3.0 * hcut[k] * (1 - smooth((v - 0.6) / 0.2))
    ang = lerp(open_a, 360 - open_a, u)
    fold = 0.010 * hs * math.sin(ang * 0.09 + v * 7) * (1 - v)
    brim = 0.030 * hs * math.exp(-(min(ang, 360 - ang) / 60) ** 2) * math.exp(-((v - 0.72) / 0.14) ** 2)   # 額前帽緣前伸
    return hood.pt(t, ang, fold + brim)


B.grid("Hood", 26, 12, hood_fn, "hood", {"Head": 0.9, "Neck": 0.1}, [hc, hc - Z * 0.15], sharp=50, texel=1.2)
mantle(B, body, "hood", t0=0.70, t1=1.14, off=0.040, rag=0.10, drop=0.06, front_drop=0.05, asym=0.04, back_drop=0.08, seed=17,
       collar=0.045, folds=8, fold_amp=0.016, w={"Spine2": 0.75, "Neck": 0.25})

# ---------------------------------------------------------------- 寬刃巨劍
gcR = Body.mir(body.grip_c); bladeR = Body.mir(body.hand_v); edgeR = Body.mir(body.hand_a)
ST = [(0.0, 0.80, 1.0), (0.035, 1.0, 1.0), (0.50, 1.0, 1.0), (0.90, 1.0, 0.95), (0.955, 0.92, 0.8), (1.0, 0.50, 0.25)]
GRIP = 0.50
sword(B, gcR, bladeR, edgeR, "blade", "ironB", "leatherB", U=U, blade_len=1.30, width=0.072, grip=GRIP, guard=0.16, thick=0.011, st=ST,
      grip_r=0.0185, guard_r=2.0, pommel=1.6)
# 刃上的缺口與中脊
g0 = gcR + bladeR * (GRIP * 0.5 * U)
edn = (edgeR - bladeR * edgeR.dot(bladeR)).normalized()
B.tube("BladeSpine", [g0 + bladeR * 0.03 * U, g0 + bladeR * 0.9 * U, g0 + bladeR * 1.2 * U], [(0.016 * U, 0.016 * U), (0.013 * U, 0.014 * U), (0.004 * U, 0.008 * U)],
       4, "blade", "Weapon", flat=edn, sharp=10)
B.tube("Ricasso", [g0 + bladeR * 0.014 * U, g0 + bladeR * 0.12 * U, g0 + bladeR * 0.16 * U], [(0.078 * U, 0.016 * U), (0.078 * U, 0.016 * U), (0.070 * U, 0.008 * U)],
       6, "ironB", "Weapon", flat=edn, exp=4, sharp=30)

# ---------------------------------------------------------------- 骨架、烘焙、動作
arm = build_armature("BossExecutioner", body, weapon=(gcR, gcR + bladeR * 0.30 * U),
                     chains=[("ApronF", "Hips", af_pts), ("ApronB", "Hips", ab_pts), ("ChainL", "ForearmL", ch_pts),
                             ("ChainR", "ForearmR", [Body.mir(p) for p in ch_pts])])
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)
mesh = BK.assemble(B, MODEL, size=(1024, 1024), bake=not (QUICK or NOBAKE), quick=QUICK)
BK.bind(mesh, arm)

legs = [("ThighL", "ShinL", 0.15 * U), ("ThighR", "ShinR", 0.15 * U), ("ShinL", "FootL", 0.12 * U), ("ShinR", "FootR", 0.12 * U)]
rig = Rig(arm, body, chains=[
    dict(names=af_names, anchor="Hips", pts=af_pts, stiff=0.06, damp=0.90, colliders=legs, out=(0, -1, 0)),
    dict(names=ab_names, anchor="Hips", pts=ab_pts, stiff=0.05, damp=0.92, colliders=legs + [("Hips", "Spine", 0.2 * U)], out=(0, 1, 0)),
    dict(names=["ChainL"], anchor="ForearmL", pts=ch_pts, stiff=0.0, damp=0.97, colliders=[], planar=False),
    dict(names=["ChainR"], anchor="ForearmR", pts=[Body.mir(p) for p in ch_pts], stiff=0.0, damp=0.97, colliders=[], planar=False)])
rig.tip_len = (GRIP * 0.5 + 1.31) * U
rig.lie_dz = 0.07
GL = -0.20


def two(Pd, g, d, edge_, hintR=None, elL=None):
    Pd["ikL"] = 1.0; Pd["gripL"] = GL
    Pd["elL"] = elL or (0.6, 0.3, -0.7)
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))


def one(Pd, g, d, edge_, left, hintR=None, hintL=None):
    Pd["ikL"] = 0.0
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))
    rig.reach(Pd, "L", left, hintL)


WP = {
    "idle": lambda p: one(p, (-0.32, -0.10, 1.44), (-0.08, 0.80, 0.58), (0, -0.6, 0.8), (0.42, -0.10, 0.84), hintR=(-0.6, 0.2, -0.8)),
    "o_up": lambda p: two(p, (-0.06, 0.02, 1.90), (0.0, 0.70, 0.70), (0, -0.7, 0.7), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
    "o_up2": lambda p: two(p, (-0.06, 0.06, 1.93), (0.0, 0.82, 0.56), (0, -0.7, 0.7), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
    "o_hit": lambda p: two(p, (0.0, -0.76, 0.76), (0.02, -0.92, -0.38), (0, 0, -1), hintR=(-0.8, 0.4, -0.3)),
    "o_low": lambda p: two(p, (0.0, -0.76, 0.64), (0.02, -0.90, -0.44), (0, 0, -1), hintR=(-0.8, 0.4, -0.3)),
    "o_rec": lambda p: two(p, (-0.10, -0.50, 0.92), (0.1, -0.9, 0.1), (0, -0.5, -0.8)),
    "s_wind": lambda p: two(p, (-0.48, 0.10, 1.26), (-0.57, 0.82, 0.20), (-0.82, -0.57, 0), hintR=(-0.3, 0.9, -0.4)),
    "s_wind2": lambda p: two(p, (-0.50, 0.14, 1.28), (-0.45, 0.88, 0.22), (-0.88, -0.45, 0), hintR=(-0.3, 0.9, -0.4)),
    "s_hit": lambda p: two(p, (-0.02, -0.62, 1.14), (0.37, -0.93, -0.05), (0.93, 0.37, 0), hintR=(-0.8, 0.3, -0.5)),
    "s_follow": lambda p: two(p, (0.28, -0.36, 1.08), (0.91, 0.42, -0.12), (-0.42, 0.91, 0), hintR=(-0.5, -0.2, -0.8)),
    "s_settle": lambda p: two(p, (0.25, -0.38, 1.04), (0.95, 0.28, -0.16), (-0.28, 0.95, 0), hintR=(-0.5, -0.2, -0.8)),
    "enter0": lambda p: one(p, (-0.38, -0.20, 0.76), (0.10, 0.84, -0.52), (0, -0.52, -0.84), (0.42, -0.10, 0.76)),
    "enter1": lambda p: one(p, (-0.38, -0.20, 0.84), (0.10, 0.86, -0.46), (0, -0.46, -0.86), (0.42, -0.08, 0.84)),
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
}

if not NOANIM:
    import soul_boss_actions
    soul_boss_actions.build(rig, lambda key, p: WP[key](p), primary="over", slow=1.12, only=ONLY, wide=1.25)

if not ONLY:
    BK.export_glb(arm, mesh, OUT_GLB)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("TRIS_FINAL", BK.tri_count(mesh), flush=True)
if NOVIEWS:
    cam = BK.setup_preview(body.H)
else:
    cam = BK.render_views(arm, body.H, TILES)
if not NOANIM:
    BK.render_actions(arm, body.H, TILES, cam, n=10, only=ONLY)
print("DONE", MODEL, flush=True)
