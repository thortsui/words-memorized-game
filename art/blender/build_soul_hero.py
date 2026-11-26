"""魂系主角：鏽蝕板甲騎士（原創造型）。
用法：blender --background --factory-startup --python build_soul_hero.py -- [--quick] [--nobake] [--noanim] [--only A,B]
輸出：public/models/hero_knight.glb、art/blender/source/hero_knight.blend、art/blender/preview/_tiles/hero_knight/
造型依據：art/reference/hero_knight_sheet.jpg（只取配置與氛圍，細節自行設計）
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
MODEL = "hero_knight"
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")   # 未壓縮原檔；遊戲用的壓縮版由 run_soul.sh 以 gltf-transform 產生
OUT_BLEND = os.path.join(HERE, "source", MODEL + ".blend")
TILES = os.path.join(HERE, "preview", "_tiles", MODEL)
NOVIEWS = "--noviews" in argv

reset_scene()
body = Body(H=1.8, bulk=1.0, wf=1.0, head=0.235)
U = body.U; R = body.R; j = body.j
B = Builder()

# ---------------------------------------------------------------- 材質
D = BK.define_mat
D("steel", "A", tex="Metal024", size=0.55, rust=0.42, wear=0.9, dirt=0.75, bump=0.5, val=0.95)
D("mail", "A", tex="Chainmail004", size=0.20, tint=(0.62, 0.62, 0.66), metal=0.85, rough=0.52, rust=0.22, dirt=0.9, bump=1.0,
  bump_dist=0.006, ao_shade=0.75)
D("leather", "A", tex="Leather026", size=0.30, val=3.2, tint=(0.60, 0.36, 0.20), rough=0.72, metal=0.0, dirt=0.7, wear=0.5,
  wear_col=(0.42, 0.30, 0.20), bump=0.6)
D("gambeson", "A", tex="Fabric030", size=0.22, tint=(0.16, 0.14, 0.12), rough=0.92, metal=0.0, dirt=0.7, bump=0.7)
D("void", "A", color=(0.004, 0.004, 0.005), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("cloth", "B", tex="Fabric030", size=0.30, tint=(0.085, 0.13, 0.27), rough=0.9, metal=0.0, dirt=0.5, wear=0.6,
  wear_col=(0.25, 0.30, 0.40), bump=0.8, mud=(0.25, 0.85, 0.85), mud_col=(0.13, 0.12, 0.11), ao_shade=0.7)
D("blade", "B", tex="Metal024", size=0.5, rust=0.25, wear=1.0, dirt=0.5, bump=0.35, val=1.05, seed=4.0)
D("leatherB", "B", tex="Leather026", size=0.30, val=3.0, tint=(0.50, 0.30, 0.17), rough=0.72, metal=0.0, dirt=0.7, wear=0.5,
  wear_col=(0.40, 0.28, 0.19), bump=0.6)
D("steelB", "B", tex="Metal024", size=0.5, rust=0.45, wear=0.9, dirt=0.7, bump=0.5, seed=9.0)

# ---------------------------------------------------------------- 內層與軀幹
under_torso(B, body, "mail")
under_arm(B, body, "mail")
under_leg(B, body, "gambeson", texel=0.6)
mail_skirt(B, body, "mail", body.tz(0.22), body.tz(-0.44), flare=0.035, rag=0.025)
cuirass(B, body, "steel", rivet_mat="steel")
gorget(B, body, "steel")
_, zf = fauld(B, body, "steel", n=4, rivet_mat="steel")
B.both(tasset(B, body, "steel", zf + 0.03 * U, length=0.21, rivet_mat="steel"))
zb = body.tz(0.285)
belt(B, body, zb, "leather", {"Spine": 0.5, "Hips": 0.5}, h=0.044, off=0.036)
buckle(B, body, zb, 8, "steel", {"Spine": 0.5, "Hips": 0.5}, off=0.046)
strap_hang(B, body, zb - 0.01, 16, "leather", length=0.26, off=0.046)
pouch(B, body, zb - 0.01, -72, "leather", off=0.046)
# 斜掛的劍帶與劍鞘（左腰）
belt(B, body, body.tz(0.20), "leather", "Hips", h=0.034, off=0.046, tilt=0.05, tilt_dir=80, name="SwordBelt")
sc0 = body.torso.pt(body.tz(0.12), 82, 0.075 * R)
sc1 = sc0 + V(0.07, 0.42, -0.62) * U
scd = (sc1 - sc0).normalized()
B.tube("Scabbard", [sc0 - scd * 0.03, sc0, sc0.lerp(sc1, 0.5), sc0.lerp(sc1, 0.93), sc1],
       [(0.030 * U, 0.014 * U), (0.031 * U, 0.014 * U), (0.027 * U, 0.012 * U), (0.021 * U, 0.010 * U), (0.010 * U, 0.006 * U)],
       8, "leatherB", "Hips", flat=X, exp=2.6)
B.tube("ScabbardChape", [sc0.lerp(sc1, 0.86), sc0.lerp(sc1, 0.94), sc1 + scd * 0.012],
       [(0.024 * U, 0.012 * U), (0.022 * U, 0.011 * U), (0.011 * U, 0.007 * U)], 8, "steelB", "Hips", flat=X, exp=2.6)
B.tube("ScabbardLocket", [sc0 - scd * 0.034, sc0 + scd * 0.03], [(0.033 * U, 0.016 * U)] * 2, 8, "steelB", "Hips", flat=X, exp=2.6)

# ---------------------------------------------------------------- 手臂
pauldron(B, body, "steel", size=1.16, lames=3, haute=0.075, rivet_mat="steel")                 # 左肩：大肩甲＋立領
B.mirror_only(pauldron(B, body, "steel", size=1.0, lames=3, haute=0.0, rivet_mat="steel"))     # 右肩：較小，方便揮劍
B.both(arm_armor(B, body, "steel", rivet_mat="steel"))
body.set_grip(0.0165 * U)
B.mirror_only(hand(B, body, "steel"))                 # 右手握劍
hand(B, body, "steel", open_amt=0.35)                 # 左手半握

# ---------------------------------------------------------------- 腿
B.both(leg_armor(B, body, "steel", rivet_mat="steel"))
B.both(sabaton(B, body, "steel"))
B.both(strap_ring(B, body.shin, body.sh_len * 0.30, "leather", "ShinL", width=0.022 * U, off=0.016 * R, name="GreaveStrapA", rivet_mat="steel", rivet_ang=95))
B.both(strap_ring(B, body.shin, body.sh_len * 0.72, "leather", "ShinL", width=0.020 * U, off=0.016 * R, name="GreaveStrapB", rivet_mat="steel", rivet_ang=95))
B.both(strap_ring(B, body.thigh, body.th_len * 0.36, "leather", "ThighL", width=0.024 * U, off=0.017 * R, name="CuisseStrapA", rivet_mat="steel", rivet_ang=100))
B.both(strap_ring(B, body.thigh, body.th_len * 0.70, "leather", "ThighL", width=0.022 * U, off=0.017 * R, name="CuisseStrapB", rivet_mat="steel", rivet_ang=100))

# ---------------------------------------------------------------- 頭盔（全罩、窄眼縫、尖吻面甲）
hz0 = body.H - body.head - 0.01 * U
helm = Surf(V(0, -0.006 * U, hz0), Z, [(0.00, 0.078 * U, 0.092 * U, 0, 0.010 * U), (0.05 * U, 0.092 * U, 0.107 * U, 0, 0.010 * U),
                                        (0.11 * U, 0.100 * U, 0.118 * U, 0, 0.006 * U), (0.16 * U, 0.100 * U, 0.119 * U, 0, 0.002 * U),
                                        (0.195 * U, 0.093 * U, 0.111 * U, 0, -0.002 * U), (0.222 * U, 0.078 * U, 0.094 * U, 0, -0.005 * U),
                                        (0.242 * U, 0.054 * U, 0.066 * U, 0, -0.007 * U), (0.254 * U, 0.026 * U, 0.032 * U, 0, -0.008 * U),
                                        (0.2585 * U, 0.002 * U, 0.003 * U, 0, -0.008 * U)])
B.ellipsoid("HelmVoid", V(0, -0.004 * U, hz0 + 0.125 * U), (X, Y, Z), (0.090 * U, 0.106 * U, 0.115 * U), 14, 8, "void", "Head", texel=0.3)


def brow(u):
    a = abs(angn(u * 360))
    return lerp(0.126, 0.028, smooth((a - 64) / 50)) * U


def skull_off(u, v, ang, t):
    a = angn(ang)
    mid = min(abs(a), 180 - abs(a))
    ridge = 0.007 * U * math.exp(-(mid / 6.5) ** 2) * smooth(v * 4)
    flare = 0.010 * U * (1 - v) ** 4
    back = 0.012 * U * (1 - v) ** 2 * smooth((abs(a) - 110) / 50)       # 後頸護片外翻
    return 0.004 * U + ridge + flare + back


B.shell("HelmSkull", helm, brow, 0.2584 * U, 0, 360, 32, 12, "steel", "Head", off=skull_off, rim=0.005 * U)
# 眉上的加強帶
B.shell("HelmBrow", helm, lambda u: brow(0.5 + (u - 0.5) * 150 / 360) + 0.004 * U, lambda u: brow(0.5 + (u - 0.5) * 150 / 360) + 0.026 * U, -75, 75, 12, 1, "steel", "Head", off=0.012 * U, rim=0.004 * U)


def visor_off(u, v, ang, t):
    a = angn(ang)
    snout = 0.030 * U * math.exp(-(a / 36) ** 2) * math.sin(math.pi * clamp(v * 0.85 + 0.12)) ** 0.8
    keel = 0.010 * U * math.exp(-(a / 8) ** 2) * math.sin(math.pi * clamp(v * 0.9 + 0.08))
    return 0.003 * U + snout + keel + 0.006 * U * (1 - v) ** 3


B.shell("HelmVisor", helm, -0.004 * U, lambda u: (0.113 - 0.006 * abs(u - 0.5) * 2) * U, -86, 86, 20, 7, "steel", "Head", off=visor_off, rim=0.005 * U)
B.shell("HelmChin", helm, -0.012 * U, 0.03 * U, 80, 280, 12, 2, "steel", "Head", off=0.002 * U, rim=0.004 * U)
hp = []
for sgn in (-1, 1):
    hp.append((helm.pt(0.118 * U, sgn * 86, 0.008 * U), helm.nrm(0.118 * U, sgn * 86)))
B.rivets("HelmPivot", hp, "steel", "Head", r=0.013 * U)
hp = []
for a in (-150, -120, -95, 95, 120, 150, 180):
    hp.append((helm.pt(brow((a % 360) / 360) + 0.014 * U, a, 0.013 * U), helm.nrm(0.06 * U, a)))
for a in (-60, -30, 30, 60):
    hp.append((helm.pt(0.012 * U, a, 0.012 * U + 0.012 * U * math.exp(-(a / 36) ** 2)), helm.nrm(0.02 * U, a)))
B.rivets("HelmRivets", hp, "steel", "Head", r=0.005 * U)
# 面甲右側的通氣孔（小黑點）
hp = []
for row in range(3):
    for col in range(4):
        a = -52 + col * 9 + row * 3
        t = (0.035 + row * 0.014) * U
        v = clamp((t + 0.004 * U) / (0.11 * U))
        o = visor_off(0, v, a, t)
        hp.append((helm.pt(t, a, o + 0.0005), helm.nrm(t, a)))
B.rivets("HelmBreaths", hp, "void", "Head", r=0.0035 * U)

# ---------------------------------------------------------------- 披風（深藍、破損）
mantle(B, body, "cloth", t0=0.78, t1=1.10, off=0.036, rag=0.06, drop=0.03, front_drop=0.07, asym=0.05, back_drop=0.03)
# 胸前的披風扣
bp = body.torso.pt(body.tz(0.86), 34, 0.052 * R)
bn = body.torso.nrm(body.tz(0.86), 34)
B.ellipsoid("Brooch", bp, (Z.cross(bn).normalized(), Z, bn), (0.020 * U, 0.020 * U, 0.008 * U), 10, 4, "steelB", "Spine2", v0=0, v1=0.5)
cape_pts = [V(0, 0.150, 1.445) * U, V(0, 0.215, 1.07) * U, V(0, 0.255, 0.70) * U, V(0, 0.285, 0.33) * U]
cape_names = chain_names("Cape", 3)


def cape_top(u):
    return body.torso.pt(body.tz(0.905), lerp(118, 242, u), 0.052 * R) + V(0, 0.012 * U, 0)


def cape_n(u):
    a = math.radians(lerp(118, 242, u))
    return (V(math.sin(a) * 0.35, 0.94, 0)).normalized()


cloth_panel(B, "Cape", cape_top, cape_n, 1.17 * U, "cloth", w_chain_pts("Spine2", cape_names, cape_pts), nu=30, nv=18, flare=0.10,
            rag=0.24, fold_amp=0.034 * U, fold_n=4.0, holes=0.04, seed=11, sag=0.035 * U, spread=-0.34 * U)

# ---------------------------------------------------------------- 長劍（右手）
gcR = Body.mir(body.grip_c); bladeR = Body.mir(body.hand_v); edgeR = Body.mir(body.hand_a)
sword(B, gcR, bladeR, edgeR, "blade", "steelB", "leatherB", U=U)

# ---------------------------------------------------------------- 骨架
arm = build_armature("HeroKnight", body, weapon=(gcR, gcR + bladeR * 0.30 * U), chains=[("Cape", "Spine2", cape_pts)])

tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)

mesh = BK.assemble(B, MODEL, size=(1024, 1024), bake=not (QUICK or NOBAKE), quick=QUICK)
BK.bind(mesh, arm)

# ---------------------------------------------------------------- 動作
rig = Rig(arm, body, chains=[dict(names=cape_names, anchor="Spine2", pts=cape_pts, stiff=0.035, damp=0.93,
                                  colliders=[("Hips", "Spine2", 0.20 * U), ("ThighL", "ShinL", 0.13 * U), ("ThighR", "ShinR", 0.13 * U),
                                             ("ShinL", "FootL", 0.10 * U), ("ShinR", "FootR", 0.10 * U)])])
rig.tip_len = 1.03 * U
if not NOANIM:
    import soul_hero_actions
    soul_hero_actions.build(rig, ONLY)

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
