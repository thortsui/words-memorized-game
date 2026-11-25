"""回合制模式的可愛勇者（約 2.5 頭身的少年劍士，原創造型）。
用法：blender --background --factory-startup --python build_cute_hero.py -- [out.glb] [out.blend] [preview_dir] [strip_dir] [只渲染的動作,逗號分隔]
造型依據：art/reference/cute_hero_sheet.jpg
朝向：臉朝 -Y（匯出 glTF 後為 +Z），角色左手在 +X，原點在腳底。
動作：Idle、Run、Slash、Combo、Cast、Hit、Faint、Victory（各自一條靜音的 NLA track）。
"""
import sys, os, math, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cute_common import *  # noqa

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PROJ = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT_GLB = os.path.abspath(argv[0]) if len(argv) > 0 else os.path.join(PROJ, "public", "models", "hero_cute.glb")
OUT_BLEND = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, "source", "hero_cute.blend")
PREVIEW_DIR = os.path.abspath(argv[2]) if len(argv) > 2 else os.path.join(HERE, "preview")
STRIP_DIR = os.path.abspath(argv[3]) if len(argv) > 3 and argv[3] != "-" else None
ONLY = argv[4].split(",") if len(argv) > 4 else None

scene = reset_scene()
random.seed(7)

# ───────────────────────── 材質 ─────────────────────────
M_SKIN = mat("Skin", "#FFD3A8", rough=0.55, glow=0.14)
M_SKIN_D = mat("SkinShade", "#F2A77E", rough=0.6, glow=0.12)
M_HAIR = mat("Hair", "#F6B62B", rough=0.32, glow=0.14)
M_HAIR_D = mat("HairDark", "#C98212", rough=0.4, glow=0.10)
M_WHITE = mat("EyeWhite", "#FFFFFF", rough=0.25, glow=0.25)
M_IRIS = mat("Iris", "#2F7FE0", rough=0.2, glow=0.2)
M_IRIS_L = mat("IrisLight", "#7CC4FF", rough=0.2, glow=0.3)
M_PUPIL = mat("Pupil", "#0E2452", rough=0.15, glow=0.05)
M_LINE = mat("EyeLine", "#1A2038", rough=0.5, glow=0.0)
M_SHINE = mat("Shine", "#FFFFFF", rough=0.05, emit="#FFFFFF", emit_strength=0.9)
M_MOUTH = mat("Mouth", "#9A3F2C", rough=0.6, glow=0.05)
M_BLUSH = mat("Blush", "#FF7D86", rough=0.8, glow=0.1, alpha=0.5)
M_BLUE = mat("Tunic", "#2F86EA", rough=0.5, glow=0.12)
M_CAPE = mat("Cape", "#1F6AD4", rough=0.55, glow=0.12)
M_ARMOR = mat("Armor", "#CDD6E0", rough=0.22, metal=0.35, glow=0.10)
M_STEEL_D = mat("SteelDark", "#8B97A8", rough=0.3, metal=0.35, glow=0.08)
M_BLADE = mat("Blade", "#E3EBF4", rough=0.18, metal=0.3, glow=0.16)
M_BROWN = mat("Leather", "#8E5632", rough=0.55, glow=0.10)
M_BROWN_L = mat("LeatherLight", "#A86B3F", rough=0.55, glow=0.10)
M_BROWN_D = mat("LeatherDark", "#5E3820", rough=0.6, glow=0.08)
M_GOLD = mat("Gold", "#F3C335", rough=0.25, metal=0.35, glow=0.14)

# ───────────────────────── 尺寸 ─────────────────────────
HC = Vector((0, 0, 0.80))                # 頭中心
HR = (0.212, 0.198, 0.192)               # 頭半徑


def head_warp(p):
    """下半部臉頰鼓一點。"""
    k = 1 + 0.07 * math.exp(-((p.z / HR[2] + 0.45) / 0.35) ** 2)
    return Vector((p.x * k, p.y * k, p.z))


HEAD = Ellip(HC, HR, head_warp)
CAP = Ellip(HC + Vector((0, 0.034, 0.030)), (0.221, 0.208, 0.202))

SHOULDER_Z, SHOULDER_X = 0.555, 0.165
HIP_X, HIP_Z, KNEE_Z, ANKLE_Z = 0.075, 0.33, 0.21, 0.07
UPPER, FORE = 0.105, 0.100


def arm_dir(s):
    return Vector((s * 0.423, 0, -0.906)).normalized()


def shoulder(s):
    return Vector((s * SHOULDER_X, 0, SHOULDER_Z))


def hand_center(s):
    return shoulder(s) + arm_dir(s) * (UPPER + FORE + 0.05)


# ───────────────────────── 頭 ─────────────────────────
head = ellipsoid("Head", HC, HR, M_SKIN, segs=28, rings=16)
for v in head.data.vertices:
    v.co = HC + head_warp(v.co - HC)
head_parts = [head]

for s in (-1, 1):
    th = s * 23
    ith = th - s * 1.5
    head_parts += [
        HEAD.patch("EyeLine", th, -5.0, (0.047, 0.064), M_LINE, push=-0.004, segs=14, rings=8),
        HEAD.patch("EyeWhite", th, -6.5, (0.042, 0.057), M_WHITE, push=-0.001, segs=14, rings=8),
        HEAD.patch("Iris", ith, -7.5, (0.034, 0.049), M_IRIS, push=0.0025, segs=14, rings=8),
        HEAD.patch("IrisLight", ith, -13.5, (0.024, 0.022), M_IRIS_L, push=0.0048, segs=12, rings=6),
        HEAD.patch("Pupil", ith, -7.0, (0.019, 0.031), M_PUPIL, push=0.0068, segs=12, rings=6),
        HEAD.patch("Glint", ith - 4.0, -2.5, (0.012, 0.014), M_SHINE, push=0.0105, segs=10, rings=6),
        HEAD.patch("Glint2", ith + 3.5, -13.0, (0.006, 0.007), M_SHINE, push=0.0105, segs=8, rings=6),
        HEAD.patch("Brow", s * 22, 16.0, (0.036, 0.0085), M_HAIR_D, push=0.004, thick=0.01, roll=s * -12, segs=10, rings=6),
        HEAD.patch("Blush", s * 43, -24, (0.030, 0.017), M_BLUSH, push=0.004, thick=0.006, segs=10, rings=6),
    ]
    ec = HEAD.pt(s * 90, -14, -0.004)
    head_parts.append(ellipsoid("Ear", ec, (0.034, 0.022, 0.046), M_SKIN, rot=(0, s * 0.25, s * -0.25), segs=10, rings=6))
    head_parts.append(ellipsoid("EarInner", ec + Vector((s * 0.012, -0.013, 0.0)), (0.018, 0.012, 0.028), M_SKIN_D, rot=(0, s * 0.25, s * -0.25), segs=10, rings=6))

head_parts.append(HEAD.patch("Nose", 0, -19, (0.009, 0.007), M_SKIN_D, push=0.0, thick=0.010, segs=8, rings=6))
mouth_pts = []
for i in range(9):
    u = i / 8 * 2 - 1
    mouth_pts.append(HEAD.pt(u * 9.0, -34 + 4.5 * u * u, 0.0015))
head_parts.append(sweep("Mouth", mouth_pts, [0.0022 + 0.0024 * (1 - abs(i / 4 - 1) ** 2) for i in range(9)], M_MOUTH, segs=6))

# 頭髮：髮帽 + 大尖刺 + 瀏海
head_parts.append(ellipsoid("HairCap", CAP.c, CAP.r, M_HAIR, segs=24, rings=12))


def spike(theta, phi, length, radius, lean=(0, 0.2, 0.4), droop=0.0, n=4):
    base, nrm = CAP.pt(theta, phi), CAP.normal(theta, phi)
    d = (nrm + Vector(lean)).normalized()
    length *= random.uniform(0.93, 1.08)
    pts, radii = [], []
    for i in range(n + 1):
        t = i / n
        pts.append(base - d * 0.04 + d * (length + 0.04) * t + Vector((0, 0, -1)) * droop * length * t * t)
        r = radius * (1 - t) ** 0.8 * (1 + 0.18 * math.sin(math.pi * t))
        radii.append((r * 0.82, r) if i < n else 0)
    head_parts.append(sweep("Spike", pts, radii, M_HAIR, segs=8, up=(0, 0, 1)))


spike(0, 84, 0.14, 0.070, lean=(0.05, -0.35, 0.5))
for s in (-1, 1):
    spike(s * 30, 62, 0.17, 0.078, lean=(s * 0.30, -0.25, 0.45))
    spike(s * 78, 56, 0.18, 0.082, lean=(s * 0.25, 0.0, 0.5))
    spike(s * 135, 55, 0.18, 0.080, lean=(s * 0.1, 0.3, 0.45))
    spike(s * 88, 26, 0.18, 0.078, lean=(s * 0.35, 0.05, 0.30))
    spike(s * 125, 26, 0.18, 0.076, lean=(s * 0.15, 0.25, 0.25))
    spike(s * 160, 30, 0.18, 0.076, lean=(0, 0.3, 0.30))
    spike(s * 108, -2, 0.14, 0.066, lean=(s * 0.2, 0.2, 0.0), droop=0.25)
    spike(s * 145, -4, 0.15, 0.066, lean=(0, 0.3, 0.0), droop=0.25)
    spike(s * 152, -26, 0.09, 0.050, lean=(0, 0.2, -0.3), droop=0.3)
spike(180, 58, 0.17, 0.080, lean=(0, 0.3, 0.5))
spike(180, 2, 0.15, 0.068, lean=(0, 0.3, 0.05), droop=0.25)
spike(180, -26, 0.09, 0.052, lean=(0, 0.2, -0.3), droop=0.3)


def lock(th0, ph0, th1, ph1, width, thick=0.020, push=0.017, n=5):
    """沿著頭的表面垂下來的一綹瀏海。"""
    pts, radii = [], []
    for i in range(n + 1):
        t = i / n
        pts.append(HEAD.pt(lerp(th0, th1, t), lerp(ph0, ph1, t), push + 0.006 * t))
        k = 1 - t ** 1.7
        radii.append((thick * (0.45 + 0.55 * k), width * k) if i < n else 0)
    head_parts.append(sweep("Bang", pts, radii, M_HAIR, segs=8, up=HEAD.normal(th0, ph0)))


lock(2, 50, -3, 4, 0.050)
for s in (-1, 1):
    lock(s * 19, 50, s * 16, 13, 0.052)
    lock(s * 38, 48, s * 44, 9, 0.056)
    lock(s * 58, 42, s * 63, -6, 0.056)
    lock(s * 78, 36, s * 80, -20, 0.050)
skin(head_parts, "Head")

# ───────────────────────── 軀幹 ─────────────────────────
skin(lathe("Neck", [(0.052, 0.575), (0.050, 0.635)], M_SKIN, segs=12), "Spine")
skin(lathe("Plate", [(0, 0.398), (0.10, 0.400), (0.140, 0.412), (0.153, 0.445), (0.157, 0.490), (0.149, 0.530),
                     (0.128, 0.565), (0.100, 0.590), (0.072, 0.604), (0, 0.610)], M_ARMOR, segs=28, sy=0.88), "Spine")
skin(torus("PlateRim", (0, 0, 0.420), 0.146, 0.011, M_STEEL_D, segs=24, rsegs=5, sy=0.88), "Spine")
skin(torus("Collar", (0, 0, 0.607), 0.074, 0.019, M_BLUE, segs=20, rsegs=8, sy=0.92), "Spine")
for s in (-1, 1):
    skin(ellipsoid("Strap", (s * 0.092, -0.052, 0.583), (0.030, 0.034, 0.016), M_BLUE, rot=(0.5, s * -0.5, 0), segs=12, rings=8), "Spine")
    skin(ellipsoid("StrapStud", (s * 0.094, -0.068, 0.578), 0.011, M_GOLD, segs=8, rings=6), "Spine")
skin_fn(ellipsoid("Waist", (0, 0, 0.42), (0.132, 0.116, 0.06), M_BLUE, segs=16, rings=8), lambda co: {"Hips": 0.5, "Spine": 0.5})
skin(torus("Belt", (0, 0, 0.402), 0.141, 0.017, M_BROWN_D, segs=24, rsegs=6, sy=0.90), "Hips")
skin(ellipsoid("Buckle", (0, -0.140, 0.402), (0.024, 0.010, 0.022), M_GOLD, segs=10, rings=6), "Hips")

skirt = lathe("Skirt", [(0, 0.300), (0.12, 0.296), (0.182, 0.262), (0.204, 0.248), (0.208, 0.256), (0.194, 0.300),
                        (0.168, 0.355), (0.146, 0.400), (0.12, 0.425), (0, 0.43)], M_BLUE, segs=32, sy=0.90)
for v in skirt.data.vertices:  # 下襬做一點波浪
    k = sstep(0.36, 0.25, v.co.z)
    a = math.atan2(v.co.y, v.co.x)
    f = 1 + 0.035 * k * math.cos(8 * a)
    v.co.x *= f
    v.co.y *= f


def skirt_w(co):
    h = sstep(0.40, 0.27, co.z)
    wl = 0.5 * h * sstep(-0.05, 0.08, co.x)
    wr = 0.5 * h * sstep(0.05, -0.08, co.x)
    return {"Hips": 1 - wl - wr, "Thigh_L": wl, "Thigh_R": wr}


skin_fn(skirt, skirt_w)

# 背上的小圓盾（中間隔著披風，用皮帶座撐開）
SHIELD_C = Vector((0, 0.218, 0.500))
back = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))  # 本地 Z → +Y（背後）
shield = [
    lathe("ShieldFace", [(0, -0.006), (0.140, -0.006), (0.150, 0.006), (0.140, 0.020), (0.090, 0.034), (0, 0.042)], M_ARMOR, segs=28, center=SHIELD_C, xform=back),
    torus("ShieldRim", SHIELD_C + Vector((0, 0.008, 0)), 0.146, 0.015, M_BROWN, segs=24, rsegs=6, rot=back),
    ellipsoid("ShieldBoss", SHIELD_C + Vector((0, 0.040, 0)), (0.040, 0.020, 0.040), M_GOLD, segs=14, rings=8),
    sweep("ShieldMount", [(0, 0.12, 0.50), (0, 0.215, 0.50)], 0.03, M_BROWN_D, segs=8),
]
skin(shield, "Spine")

# 披風
CAPE_TOP, CAPE_BOT, CAPE_PIVOT = 0.605, 0.185, 0.36


def cape_pt(u, v):
    a = math.radians((u * 2 - 1) * lerp(62, 58, v))
    rx = lerp(0.115, 0.275, v ** 0.85) + 0.012 * math.sin(u * math.pi * 5) * v
    ry = lerp(0.108, 0.175, v ** 0.9) + 0.012 * math.sin(u * math.pi * 5) * v
    z = lerp(CAPE_TOP, CAPE_BOT, v) + 0.03 * v * (1 - abs(2 * u - 1) ** 2) - 0.015 * v
    return Vector((math.sin(a) * rx, math.cos(a) * ry + 0.022, z))


cape = surface("Cape", cape_pt, 12, 10, M_CAPE)


def cape_w(co):
    w1 = sstep(CAPE_TOP - 0.02, CAPE_TOP - 0.12, co.z)
    w2 = sstep(CAPE_PIVOT + 0.07, CAPE_PIVOT - 0.07, co.z)
    return {"Spine": 1 - w1, "Cape1": w1 * (1 - w2), "Cape2": w1 * w2}


skin_fn(cape, cape_w)

# ───────────────────────── 手臂 ─────────────────────────
for s, side in ((1, "L"), (-1, "R")):
    S, d = shoulder(s), arm_dir(s)
    A = align(d)
    skin(ellipsoid("Sleeve", S + d * 0.022, (0.074, 0.072, 0.082), M_BLUE, rot=A, segs=14, rings=8), f"UpperArm_{side}")
    skin(torus("SleeveHem", S + d * 0.070, 0.058, 0.012, M_CAPE, segs=12, rsegs=5, rot=A), f"UpperArm_{side}")
    n = 12
    arm = sweep("Arm", [S + d * lerp(0.03, UPPER + FORE + 0.01, i / n) for i in range(n + 1)], 0.044, M_SKIN, segs=10)
    skin_fn(arm, lambda co, S=S, d=d, side=side: (lambda w: {f"UpperArm_{side}": 1 - w, f"ForeArm_{side}": w})(sstep(UPPER - 0.04, UPPER + 0.04, (co - S).dot(d))))
    cuff = lathe("Cuff", [(0.046, 0.132), (0.070, 0.128), (0.074, 0.140), (0.060, 0.190), (0.052, 0.212), (0.03, 0.216)], M_BROWN_L, segs=14, center=S, xform=A)
    skin(cuff, f"ForeArm_{side}")
    Hc = hand_center(s)
    skin(ellipsoid("Glove", Hc, (0.060, 0.066, 0.068), M_BROWN, rot=A, segs=14, rings=8), f"Hand_{side}")
    skin(ellipsoid("Thumb", Hc + Vector((s * -0.020, -0.050, 0.012)), (0.026, 0.034, 0.030), M_BROWN, segs=10, rings=6), f"Hand_{side}")

# 劍（右手）
HAND_R = hand_center(-1)
SW_F = Vector((-0.10, -0.90, -0.42)).normalized()      # 劍尖方向
SW_U = (Vector((0, 0, 1)) - SW_F * SW_F.z).normalized()  # 刃寬方向
SW_S = SW_F.cross(SW_U)                                  # 刃厚方向
SW_M = Matrix((SW_S, SW_U, SW_F)).transposed()
sword = [
    sweep("Grip", [HAND_R - SW_F * 0.065, HAND_R + SW_F * 0.075], 0.017, M_BROWN_D, segs=8),
    ellipsoid("Pommel", HAND_R - SW_F * 0.078, 0.027, M_GOLD, segs=10, rings=6),
    ellipsoid("Guard", HAND_R + SW_F * 0.082, (0.030, 0.080, 0.018), M_GOLD, rot=SW_M, segs=14, rings=8),
]
BL0, BLEN, BW, BT = 0.090, 0.40, 0.050, 0.014
bm = bmesh.new()
secs = []
for t, w, th in ((0.0, 0.92, 1.0), (0.10, 1.0, 1.0), (0.74, 0.90, 0.9)):
    c = HAND_R + SW_F * (BL0 + BLEN * t)
    secs.append([bm.verts.new(c + SW_U * BW * w), bm.verts.new(c + SW_S * BT * th), bm.verts.new(c - SW_U * BW * w), bm.verts.new(c - SW_S * BT * th)])
tip = bm.verts.new(HAND_R + SW_F * (BL0 + BLEN))
for a, b in zip(secs, secs[1:]):
    for j in range(4):
        bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
for j in range(4):
    bm.faces.new((secs[-1][j], secs[-1][(j + 1) % 4], tip))
bm.faces.new(secs[0])
sword.append(finish("Blade", bm, M_BLADE, smooth=False))
skin(sword, "Sword")

# ───────────────────────── 腿 ─────────────────────────
for s, side in ((1, "L"), (-1, "R")):
    x = s * HIP_X
    n = 10
    leg = sweep("Leg", [(x, 0, lerp(HIP_Z + 0.01, 0.13, i / n)) for i in range(n + 1)], 0.058, M_SKIN, segs=10, up=(0, -1, 0))
    skin_fn(leg, lambda co, side=side: (lambda w: {f"Thigh_{side}": 1 - w, f"Shin_{side}": w})(sstep(KNEE_Z + 0.04, KNEE_Z - 0.04, co.z)))
    boot = lathe("Boot", [(0, 0.035), (0.066, 0.040), (0.071, 0.10), (0.074, 0.168), (0.091, 0.172), (0.097, 0.192),
                          (0.095, 0.214), (0.083, 0.225), (0.054, 0.221)], M_BROWN, segs=14, center=(x, 0, 0))
    skin(boot, f"Shin_{side}")
    cuff = torus("BootCuff", (x, 0, 0.196), 0.090, 0.012, M_BROWN_L, segs=12, rsegs=5)
    skin(cuff, f"Shin_{side}")
    foot = ellipsoid("Foot", (x * 1.05, -0.045, 0.052), (0.076, 0.120, 0.056), M_BROWN, segs=14, rings=8)
    sole = ellipsoid("Sole", (x * 1.05, -0.045, 0.014), (0.080, 0.124, 0.016), M_BROWN_D, segs=14, rings=5)
    for ob in (foot, sole):
        for v in ob.data.vertices:
            v.co.z = max(v.co.z, 0.0)
    heel = ellipsoid("Heel", (x, 0.0, 0.068), 0.070, M_BROWN, segs=10, rings=6)
    skin([foot, sole, heel], f"Foot_{side}")

# ───────────────────────── 骨架 ─────────────────────────
rig = Rig("Hero")
rig.bone("Root", (0, 0, 0), (0, 0, 0.15))
rig.bone("Hips", (0, 0, 0.34), (0, 0, 0.44), "Root")
rig.bone("Spine", (0, 0, 0.44), (0, 0, 0.60), "Hips")
rig.bone("Head", (0, 0, 0.61), (0, 0, 0.86), "Spine")
for s, side in ((1, "L"), (-1, "R")):
    S, d = shoulder(s), arm_dir(s)
    rig.bone(f"UpperArm_{side}", S, S + d * UPPER, "Spine")
    rig.bone(f"ForeArm_{side}", S + d * UPPER, S + d * (UPPER + FORE), f"UpperArm_{side}")
    rig.bone(f"Hand_{side}", S + d * (UPPER + FORE), S + d * (UPPER + FORE + 0.09), f"ForeArm_{side}")
    x = s * HIP_X
    rig.bone(f"Thigh_{side}", (x, 0, HIP_Z), (x, 0, KNEE_Z), "Hips")
    rig.bone(f"Shin_{side}", (x, 0, KNEE_Z), (x, 0, ANKLE_Z), f"Thigh_{side}")
    rig.bone(f"Foot_{side}", (x, 0, ANKLE_Z), (x, -0.13, 0.03), f"Shin_{side}")
rig.bone("Sword", HAND_R, HAND_R + SW_F * 0.30, "Hand_R")
rig.bone("Cape1", (0, 0.135, CAPE_TOP - 0.02), (0, 0.185, CAPE_PIVOT), "Spine")
rig.bone("Cape2", (0, 0.185, CAPE_PIVOT), (0, 0.215, CAPE_BOT), "Cape1")
rig.done()

mesh = join_parts("HeroMesh")
rig.bind(mesh)

# ───────────────────────── 動作 ─────────────────────────
STANCE = {
    "UpperArm_R": (-14, 8, 0), "ForeArm_R": (-30, 0, 0), "Hand_R": (8, 0, 0),
    "UpperArm_L": (6, -3, 0), "ForeArm_L": (-22, 0, 0),
    "Cape1": (3, 0, 0), "Cape2": (6, 0, 0),
}


def L(x=0.0, y=0.0, z=0.0, r=(0, 0, 0)):
    return dict(l=(x, y, z), r=r)


def mirror(pose):
    out = {}
    for bn, s in pose.items():
        nb = bn[:-2] + ("_R" if bn.endswith("_L") else "_L") if bn[-2:] in ("_L", "_R") else bn
        if isinstance(s, dict):
            o = dict(s)
            if "r" in o:
                o["r"] = (o["r"][0], -o["r"][1], -o["r"][2])
            if "l" in o and o["l"] is not None:
                o["l"] = (-o["l"][0], o["l"][1], o["l"][2])
            out[nb] = o
        else:
            out[nb] = (s[0], -s[1], -s[2])
    return out


# Idle：呼吸、重心微微起伏、披風輕擺
rig.action("Idle", [
    (1, {"Hips": L()}),
    (16, {"Hips": L(z=-0.004), "Spine": (1.2, 0, 0.8), "Head": (-1.0, 0, 2.0), "UpperArm_R": (-14, 9.5, 0), "ForeArm_R": (-32, 0, 0),
          "UpperArm_L": (6, -4.5, 0), "Thigh_L": (-4, 0, 0), "Shin_L": (8, 0, 0), "Foot_L": (-4, 0, 0), "Thigh_R": (-4, 0, 0), "Shin_R": (8, 0, 0), "Foot_R": (-4, 0, 0)}),
    (31, {"Hips": L(z=-0.007), "Spine": (2.4, 0, 0), "Head": (-2.0, 0, 0), "UpperArm_R": (-13, 11, 0), "ForeArm_R": (-34, 0, 0),
          "UpperArm_L": (7, -6, 0), "ForeArm_L": (-25, 0, 0), "Thigh_L": (-6, 0, 0), "Shin_L": (12, 0, 0), "Foot_L": (-6, 0, 0), "Thigh_R": (-6, 0, 0), "Shin_R": (12, 0, 0), "Foot_R": (-6, 0, 0)}),
    (46, {"Hips": L(z=-0.004), "Spine": (1.2, 0, -0.8), "Head": (-1.0, 0, -2.0), "UpperArm_R": (-14, 9.5, 0), "ForeArm_R": (-32, 0, 0),
          "UpperArm_L": (6, -4.5, 0), "Thigh_L": (-4, 0, 0), "Shin_L": (8, 0, 0), "Foot_L": (-4, 0, 0), "Thigh_R": (-4, 0, 0), "Shin_R": (8, 0, 0), "Foot_R": (-4, 0, 0)}),
    (61, {"Hips": L()}),
], base=STANCE, loop=True, extra={
    "Cape1": [(1, (3, 0, 0)), (16, (5, 0, 1.5)), (31, (4, 0, 0)), (46, (2.5, 0, -1.5)), (61, (3, 0, 0))],
    "Cape2": [(1, (6, 0, 0)), (16, (4, 0, -3)), (31, (10, 0, 0)), (46, (8, 0, 3)), (61, (6, 0, 0))],
})

# Run：16 格循環（接觸→經過→接觸→經過）
run_contact = {
    "Hips": L(z=-0.022, r=(6, 0, -8)), "Spine": (13, 0, 12), "Head": (-12, 0, -4),
    "Thigh_L": (-50, 0, 0), "Shin_L": (14, 0, 0), "Foot_L": (-16, 0, 0),
    "Thigh_R": (40, 0, 0), "Shin_R": (38, 0, 0), "Foot_R": (28, 0, 0),
    "UpperArm_R": (-22, 10, 0), "ForeArm_R": (-58, 0, 0), "Hand_R": (4, 0, 0),
    "UpperArm_L": (48, -10, 0), "ForeArm_L": (-50, 0, 0),
}
run_pass = {
    "Hips": L(z=0.018, r=(5, 0, 0)), "Spine": (11, 0, 0), "Head": (-10, 0, 0),
    "Thigh_L": (-4, 0, 0), "Shin_L": (10, 0, 0), "Foot_L": (-2, 0, 0),
    "Thigh_R": (-20, 0, 0), "Shin_R": (88, 0, 0), "Foot_R": (12, 0, 0),
    "UpperArm_R": (2, 10, 0), "ForeArm_R": (-58, 0, 0), "Hand_R": (4, 0, 0),
    "UpperArm_L": (4, -8, 0), "ForeArm_L": (-58, 0, 0),
}
run_contact2 = mirror(run_contact)
run_contact2.update({"UpperArm_R": (26, 12, 0), "ForeArm_R": (-58, 0, 0), "Hand_R": (4, 0, 0), "UpperArm_L": (-48, -10, 0), "ForeArm_L": (-62, 0, 0)})
run_pass2 = mirror(run_pass)
run_pass2.update({"UpperArm_R": (2, 10, 0), "ForeArm_R": (-58, 0, 0), "Hand_R": (4, 0, 0), "UpperArm_L": (4, -8, 0), "ForeArm_L": (-58, 0, 0)})
rig.action("Run", [(1, run_contact), (5, run_pass), (9, run_contact2), (13, run_pass2), (17, run_contact)], base=STANCE, loop=True, extra={
    "Cape1": [(1, (16, 0, 2)), (5, (20, 0, 0)), (9, (16, 0, -2)), (13, (20, 0, 0)), (17, (16, 0, 2))],
    "Cape2": [(1, (40, 0, -5)), (5, (28, 0, 0)), (9, (40, 0, 5)), (13, (28, 0, 0)), (17, (40, 0, -5))],
})

# Slash：蓄勢→踏步→下劈→收招
rig.action("Slash", [
    (1, {"Root": L(), "Hips": L()}),
    (7, {"Root": L(y=0.03), "Hips": L(z=-0.035, r=(-4, 0, -14)), "Spine": (-10, 0, -24), "Head": (6, 0, 30),
         "UpperArm_R": (-118, 18, 0), "ForeArm_R": (-50, 0, 0), "Hand_R": (0, 0, 0),
         "UpperArm_L": (-48, -18, 0), "ForeArm_L": (-35, 0, 0),
         "Thigh_L": (-14, 0, 0), "Shin_L": (26, 0, 0), "Foot_L": (-10, 0, 0), "Thigh_R": (-6, 0, 0), "Shin_R": (26, 0, 0), "Foot_R": (-18, 0, 0),
         "Cape1": (8, 0, 0), "Cape2": (14, 0, 0)}),
    (11, {"Root": L(y=0.05), "Hips": L(z=-0.045, r=(-6, 0, -18)), "Spine": (-14, 0, -30), "Head": (10, 0, 38),
          "UpperArm_R": (-128, 22, 0), "ForeArm_R": (-58, 0, 0), "Hand_R": (-6, 0, 0),
          "UpperArm_L": (-55, -20, 0), "ForeArm_L": (-30, 0, 0),
          "Thigh_L": (-18, 0, 0), "Shin_L": (32, 0, 0), "Foot_L": (-12, 0, 0), "Thigh_R": (-6, 0, 0), "Shin_R": (30, 0, 0), "Foot_R": (-22, 0, 0),
          "Cape1": (4, 0, 0), "Cape2": (8, 0, 0)}),
    (14, {"Root": L(y=-0.22), "Hips": L(z=-0.03, r=(8, 0, 4)), "Spine": (10, 0, 10), "Head": (-8, 0, -6),
          "UpperArm_R": (-78, 6, 0), "ForeArm_R": (-18, 0, 0), "Hand_R": (0, 0, 0),
          "UpperArm_L": (10, -30, 0), "ForeArm_L": (-40, 0, 0),
          "Thigh_L": (-52, 0, 0), "Shin_L": (30, 0, 0), "Foot_L": (-12, 0, 0), "Thigh_R": (30, 0, 0), "Shin_R": (20, 0, 0), "Foot_R": (20, 0, 0),
          "Cape1": (22, 0, 0), "Cape2": (40, 0, 0)}),
    (16, {"Root": L(y=-0.34), "Hips": L(z=-0.06, r=(12, 0, 14)), "Spine": (22, 0, 26), "Head": (-18, 0, -22),
          "UpperArm_R": (-52, -14, 0), "ForeArm_R": (-8, 0, 0), "Hand_R": (0, 0, 0),
          "UpperArm_L": (40, -34, 0), "ForeArm_L": (-45, 0, 0),
          "Thigh_L": (-58, 0, 0), "Shin_L": (52, 0, 0), "Foot_L": (-6, 0, 0), "Thigh_R": (26, 0, 0), "Shin_R": (26, 0, 0), "Foot_R": (24, 0, 0),
          "Cape1": (26, 0, 0), "Cape2": (48, 0, 0)}),
    (22, {"Root": L(y=-0.36), "Hips": L(z=-0.07, r=(13, 0, 16)), "Spine": (24, 0, 30), "Head": (-20, 0, -26),
          "UpperArm_R": (-46, -20, 0), "ForeArm_R": (-8, 0, 0), "Hand_R": (2, 0, 0),
          "UpperArm_L": (44, -34, 0), "ForeArm_L": (-48, 0, 0),
          "Thigh_L": (-60, 0, 0), "Shin_L": (58, 0, 0), "Foot_L": (-6, 0, 0), "Thigh_R": (24, 0, 0), "Shin_R": (30, 0, 0), "Foot_R": (26, 0, 0),
          "Cape1": (10, 0, 0), "Cape2": (16, 0, 0)}),
    (30, {"Root": L(y=-0.14), "Hips": L(z=-0.02, r=(4, 0, 4)), "Spine": (6, 0, 8), "Head": (-5, 0, -6),
          "UpperArm_R": (-16, 4, 0), "ForeArm_R": (-24, 0, 0), "Hand_R": (12, 0, 0),
          "Thigh_L": (-20, 0, 0), "Shin_L": (24, 0, 0), "Foot_L": (-4, 0, 0), "Thigh_R": (6, 0, 0), "Shin_R": (10, 0, 0),
          "Cape1": (-2, 0, 0), "Cape2": (0, 0, 0)}),
    (36, {"Root": L(), "Hips": L()}),
], base=STANCE)

# Combo：橫斬→反手橫斬→跳劈
rig.action("Combo", [
    (1, {"Root": L(), "Hips": L()}),
    # 第一斬蓄勢（劍拉到右後方）
    (5, {"Root": L(y=0.02), "Hips": L(z=-0.03, r=(0, 0, -16)), "Spine": (2, 0, -34), "Head": (0, 0, 44),
         "UpperArm_R": (-78, 0, -55), "ForeArm_R": (-30, 0, 0), "Hand_R": (50, 0, 0),
         "UpperArm_L": (-30, -25, 0), "ForeArm_L": (-40, 0, 0),
         "Thigh_L": (-10, 0, 0), "Shin_L": (20, 0, 0), "Foot_L": (-10, 0, 0), "Thigh_R": (-8, 0, 0), "Shin_R": (20, 0, 0), "Foot_R": (-12, 0, 0)}),
    # 第一斬掃過
    (9, {"Root": L(y=-0.12), "Hips": L(z=-0.04, r=(6, 0, 12)), "Spine": (10, 0, 36), "Head": (-6, 0, -40),
         "UpperArm_R": (-80, 0, 40), "ForeArm_R": (-6, 0, 0), "Hand_R": (52, 0, 0),
         "UpperArm_L": (30, -30, 0), "ForeArm_L": (-50, 0, 0),
         "Thigh_L": (-40, 0, 0), "Shin_L": (36, 0, 0), "Foot_L": (-4, 0, 0), "Thigh_R": (20, 0, 0), "Shin_R": (14, 0, 0), "Foot_R": (14, 0, 0),
         "Cape1": (10, 0, -8), "Cape2": (22, 0, -14)}),
    # 第二斬蓄勢（劍停在左邊）
    (13, {"Root": L(y=-0.14), "Hips": L(z=-0.045, r=(6, 0, 18)), "Spine": (8, 0, 44), "Head": (-4, 0, -52),
          "UpperArm_R": (-84, 0, 62), "ForeArm_R": (-34, 0, 0), "Hand_R": (56, 0, 0),
          "UpperArm_L": (36, -32, 0), "ForeArm_L": (-46, 0, 0),
          "Thigh_L": (-42, 0, 0), "Shin_L": (40, 0, 0), "Foot_L": (-4, 0, 0), "Thigh_R": (20, 0, 0), "Shin_R": (18, 0, 0), "Foot_R": (16, 0, 0),
          "Cape1": (6, 0, 4), "Cape2": (10, 0, 8)}),
    # 第二斬反手掃回
    (17, {"Root": L(y=-0.26), "Hips": L(z=-0.04, r=(6, 0, -14)), "Spine": (8, 0, -32), "Head": (-4, 0, 40),
          "UpperArm_R": (-82, 0, -50), "ForeArm_R": (-4, 0, 0), "Hand_R": (52, 0, 0),
          "UpperArm_L": (-20, -40, 0), "ForeArm_L": (-40, 0, 0),
          "Thigh_L": (22, 0, 0), "Shin_L": (16, 0, 0), "Foot_L": (14, 0, 0), "Thigh_R": (-42, 0, 0), "Shin_R": (38, 0, 0), "Foot_R": (-4, 0, 0),
          "Cape1": (10, 0, 8), "Cape2": (22, 0, 14)}),
    # 下蹲準備起跳
    (22, {"Root": L(y=-0.28), "Hips": L(z=-0.085, r=(14, 0, -6)), "Spine": (14, 0, -12), "Head": (-14, 0, 14),
          "UpperArm_R": (-40, 14, 0), "ForeArm_R": (-60, 0, 0), "Hand_R": (20, 0, 0),
          "UpperArm_L": (30, -20, 0), "ForeArm_L": (-50, 0, 0),
          "Thigh_L": (-44, 0, 0), "Shin_L": (84, 0, 0), "Foot_L": (-32, 0, 0), "Thigh_R": (-44, 0, 0), "Shin_R": (84, 0, 0), "Foot_R": (-32, 0, 0),
          "Cape1": (2, 0, 0), "Cape2": (4, 0, 0)}),
    # 跳到最高點，劍舉過頭
    (28, {"Root": L(y=-0.38), "Hips": L(z=0.30, r=(-10, 0, 0)), "Spine": (-14, 0, 0), "Head": (10, 0, 0),
          "UpperArm_R": (-150, 10, 0), "ForeArm_R": (-40, 0, 0), "Hand_R": (-5, 0, 0),
          "UpperArm_L": (-140, -12, 0), "ForeArm_L": (-40, 0, 0),
          "Thigh_L": (-50, 0, 0), "Shin_L": (80, 0, 0), "Foot_L": (10, 0, 0), "Thigh_R": (-10, 0, 0), "Shin_R": (70, 0, 0), "Foot_R": (20, 0, 0),
          "Cape1": (-6, 0, 0), "Cape2": (-10, 0, 0)}),
    # 下劈落地
    (32, {"Root": L(y=-0.50), "Hips": L(z=-0.09, r=(18, 0, 0)), "Spine": (30, 0, 6), "Head": (-28, 0, -4),
          "UpperArm_R": (-48, -8, 0), "ForeArm_R": (-6, 0, 0), "Hand_R": (4, 0, 0),
          "UpperArm_L": (-20, 4, 0), "ForeArm_L": (-20, 0, 0),
          "Thigh_L": (-62, 0, 0), "Shin_L": (80, 0, 0), "Foot_L": (-20, 0, 0), "Thigh_R": (-30, 0, 0), "Shin_R": (76, 0, 0), "Foot_R": (-30, 0, 0),
          "Cape1": (34, 0, 0), "Cape2": (56, 0, 0)}),
    (38, {"Root": L(y=-0.50), "Hips": L(z=-0.075, r=(16, 0, 0)), "Spine": (26, 0, 6), "Head": (-24, 0, -4),
          "UpperArm_R": (-44, -8, 0), "ForeArm_R": (-8, 0, 0), "Hand_R": (6, 0, 0),
          "UpperArm_L": (-10, 2, 0), "ForeArm_L": (-24, 0, 0),
          "Thigh_L": (-56, 0, 0), "Shin_L": (72, 0, 0), "Foot_L": (-18, 0, 0), "Thigh_R": (-28, 0, 0), "Shin_R": (68, 0, 0), "Foot_R": (-26, 0, 0),
          "Cape1": (8, 0, 0), "Cape2": (14, 0, 0)}),
    (48, {"Root": L(y=-0.20), "Hips": L(z=-0.02, r=(4, 0, 0)), "Spine": (6, 0, 0), "Head": (-5, 0, 0),
          "Thigh_L": (-16, 0, 0), "Shin_L": (22, 0, 0), "Foot_L": (-6, 0, 0), "Thigh_R": (4, 0, 0), "Shin_R": (10, 0, 0),
          "Cape1": (-2, 0, 0), "Cape2": (0, 0, 0)}),
    (56, {"Root": L(), "Hips": L()}),
], base=STANCE)

# Cast：收劍蓄力→舉劍向天→維持→放下
cast_up = {"Hips": L(z=0.0, r=(-3, 0, 0)), "Spine": (-9, 0, 4), "Head": (-14, 0, -3),
           "UpperArm_R": (-160, 12, 0), "ForeArm_R": (-8, 0, 0), "Hand_R": (52, 0, 0),
           "UpperArm_L": (-62, -34, 0), "ForeArm_L": (-28, 0, 0), "Hand_L": (-30, 0, 0),
           "Thigh_L": (-6, -6, 0), "Thigh_R": (2, 6, 0)}
cast_up2 = dict(cast_up)
cast_up2.update({"Hips": L(z=0.006, r=(-4, 0, 0)), "Spine": (-11, 0, 4), "UpperArm_R": (-164, 10, 0), "UpperArm_L": (-68, -38, 0)})
rig.action("Cast", [
    (1, {"Hips": L()}),
    (9, {"Hips": L(z=-0.05, r=(8, 0, 0)), "Spine": (14, 0, -8), "Head": (-6, 0, 8),
         "UpperArm_R": (10, 16, 0), "ForeArm_R": (-80, 0, 0), "Hand_R": (-5, 0, 0),
         "UpperArm_L": (-20, -6, 0), "ForeArm_L": (-70, 0, 0),
         "Thigh_L": (-30, 0, 0), "Shin_L": (58, 0, 0), "Foot_L": (-26, 0, 0), "Thigh_R": (-30, 0, 0), "Shin_R": (58, 0, 0), "Foot_R": (-26, 0, 0)}),
    (16, cast_up2), (20, cast_up), (27, cast_up2), (34, cast_up),
    (41, {"Hips": L(z=-0.015, r=(3, 0, 0)), "Spine": (5, 0, 0), "Head": (-3, 0, 0),
          "UpperArm_R": (-40, 10, 0), "ForeArm_R": (-40, 0, 0), "Hand_R": (16, 0, 0),
          "Thigh_L": (-10, 0, 0), "Shin_L": (20, 0, 0), "Foot_L": (-10, 0, 0), "Thigh_R": (-10, 0, 0), "Shin_R": (20, 0, 0), "Foot_R": (-10, 0, 0)}),
    (48, {"Hips": L()}),
], base=STANCE, extra={
    "Cape1": [(1, (3, 0, 0)), (9, (0, 0, 0)), (16, (20, 0, 3)), (20, (26, 0, -3)), (24, (20, 0, 4)), (28, (27, 0, -4)), (32, (21, 0, 3)), (36, (24, 0, 0)), (42, (8, 0, 0)), (48, (3, 0, 0))],
    "Cape2": [(1, (6, 0, 0)), (9, (2, 0, 0)), (16, (30, 0, -6)), (20, (44, 0, 6)), (24, (32, 0, -8)), (28, (46, 0, 8)), (32, (34, 0, -6)), (36, (40, 0, 0)), (42, (16, 0, 0)), (48, (6, 0, 0))],
})

# Hit：受擊後仰→彈回
rig.action("Hit", [
    (1, {"Root": L(), "Hips": L()}),
    (4, {"Root": L(y=0.10), "Hips": L(z=-0.02, r=(-12, 0, 6)), "Spine": (-24, 0, 8), "Head": (-22, 0, 4),
         "UpperArm_R": (-50, 40, 0), "ForeArm_R": (-40, 0, 0), "Hand_R": (20, 0, 0),
         "UpperArm_L": (-55, -45, 0), "ForeArm_L": (-45, 0, 0),
         "Thigh_L": (-28, 0, 0), "Shin_L": (14, 0, 0), "Foot_L": (-10, 0, 0), "Thigh_R": (4, 0, 0), "Shin_R": (22, 0, 0), "Foot_R": (-10, 0, 0),
         "Cape1": (-4, 0, 0), "Cape2": (-8, 0, 0)}),
    (8, {"Root": L(y=0.15), "Hips": L(z=-0.035, r=(-8, 0, 4)), "Spine": (-14, 0, 5), "Head": (8, 0, 2),
         "UpperArm_R": (-30, 30, 0), "ForeArm_R": (-50, 0, 0), "Hand_R": (16, 0, 0),
         "UpperArm_L": (-30, -34, 0), "ForeArm_L": (-55, 0, 0),
         "Thigh_L": (-20, 0, 0), "Shin_L": (24, 0, 0), "Foot_L": (-6, 0, 0), "Thigh_R": (-4, 0, 0), "Shin_R": (30, 0, 0), "Foot_R": (-14, 0, 0),
         "Cape1": (14, 0, 0), "Cape2": (22, 0, 0)}),
    (13, {"Root": L(y=0.10), "Hips": L(z=-0.03, r=(6, 0, 0)), "Spine": (10, 0, 0), "Head": (4, 0, 0),
          "UpperArm_R": (-18, 14, 0), "ForeArm_R": (-40, 0, 0),
          "UpperArm_L": (0, -12, 0), "ForeArm_L": (-36, 0, 0),
          "Thigh_L": (-14, 0, 0), "Shin_L": (28, 0, 0), "Foot_L": (-12, 0, 0), "Thigh_R": (-12, 0, 0), "Shin_R": (28, 0, 0), "Foot_R": (-14, 0, 0),
          "Cape1": (0, 0, 0), "Cape2": (2, 0, 0)}),
    (20, {"Root": L(), "Hips": L()}),
], base=STANCE)

# Faint：踉蹌→膝蓋一軟→向後倒下→彈一下躺平
faint_down = {"Root": L(y=0.30), "Hips": L(z=-0.115, r=(-84, 0, 0)), "Spine": (-2, 0, 4), "Head": (4, 0, 12),
              "UpperArm_R": (34, 52, 0), "ForeArm_R": (-12, 0, 0), "Hand_R": (0, 0, 0),
              "UpperArm_L": (34, -58, 0), "ForeArm_L": (-16, 0, 0),
              "Thigh_L": (22, -10, 0), "Shin_L": (6, 0, 0), "Foot_L": (20, 0, 0), "Thigh_R": (26, 8, 0), "Shin_R": (4, 0, 0), "Foot_R": (24, 0, 0),
              "Cape1": (0, 0, 0), "Cape2": (-4, 0, 0)}
faint_bounce = dict(faint_down)
faint_bounce.update({"Hips": L(z=-0.075, r=(-76, 0, 0)), "Head": (16, 0, 8), "Thigh_L": (4, -8, 0), "Thigh_R": (8, 6, 0),
                     "UpperArm_R": (18, 44, 0), "UpperArm_L": (18, -48, 0)})
rig.action("Faint", [
    (1, {"Root": L(), "Hips": L()}),
    (7, {"Root": L(y=0.05), "Hips": L(z=-0.03, r=(-8, 0, 5)), "Spine": (-16, 0, 6), "Head": (-14, 6, 0),
         "UpperArm_R": (-30, 34, 0), "ForeArm_R": (-30, 0, 0), "UpperArm_L": (-36, -40, 0), "ForeArm_L": (-30, 0, 0),
         "Thigh_L": (-16, 0, 0), "Shin_L": (30, 0, 0), "Foot_L": (-8, 0, 0), "Thigh_R": (-4, 0, 0), "Shin_R": (26, 0, 0), "Foot_R": (-14, 0, 0)}),
    (13, {"Root": L(y=0.09), "Hips": L(z=-0.10, r=(-4, 0, -4)), "Spine": (8, 0, -6), "Head": (16, -8, 0),
          "UpperArm_R": (-10, 24, 0), "ForeArm_R": (-50, 0, 0), "Hand_R": (0, 0, 0), "UpperArm_L": (4, -18, 0), "ForeArm_L": (-14, 0, 0),
          "Thigh_L": (-48, 0, 0), "Shin_L": (96, 0, 0), "Foot_L": (-30, 0, 0), "Thigh_R": (-44, 0, 0), "Shin_R": (92, 0, 0), "Foot_R": (-30, 0, 0)}),
    (19, {"Root": L(y=0.18), "Hips": L(z=-0.13, r=(-42, 0, 0)), "Spine": (-8, 0, 0), "Head": (20, 0, 4),
          "UpperArm_R": (-40, 40, 0), "ForeArm_R": (-20, 0, 0), "UpperArm_L": (-44, -44, 0), "ForeArm_L": (-20, 0, 0),
          "Thigh_L": (-50, 0, 0), "Shin_L": (70, 0, 0), "Foot_L": (-10, 0, 0), "Thigh_R": (-40, 0, 0), "Shin_R": (60, 0, 0), "Foot_R": (-10, 0, 0),
          "Cape1": (-6, 0, 0), "Cape2": (-10, 0, 0)}),
    (24, faint_down), (28, faint_bounce), (33, faint_down), (44, faint_down),
], base=STANCE)

# Victory：下蹲→舉劍跳躍→落地→小跳→舉劍定格
vic_pose = {"Hips": L(z=0.0, r=(-3, 0, 0)), "Spine": (-8, 0, 6), "Head": (-8, 0, -6),
            "UpperArm_R": (-158, 14, 0), "ForeArm_R": (-10, 0, 0), "Hand_R": (50, 0, 0),
            "UpperArm_L": (14, -34, 0), "ForeArm_L": (-78, 0, 0),
            "Thigh_L": (0, -8, 0), "Thigh_R": (0, 8, 0), "Cape1": (4, 0, 0), "Cape2": (8, 0, 0)}
vic_crouch = {"Hips": L(z=-0.085, r=(12, 0, 0)), "Spine": (14, 0, 0), "Head": (-12, 0, 0),
              "UpperArm_R": (24, 14, 0), "ForeArm_R": (-70, 0, 0), "Hand_R": (-10, 0, 0),
              "UpperArm_L": (36, -14, 0), "ForeArm_L": (-40, 0, 0),
              "Thigh_L": (-44, 0, 0), "Shin_L": (84, 0, 0), "Foot_L": (-32, 0, 0), "Thigh_R": (-44, 0, 0), "Shin_R": (84, 0, 0), "Foot_R": (-32, 0, 0),
              "Cape1": (0, 0, 0), "Cape2": (2, 0, 0)}
vic_air = {"Hips": L(z=0.34, r=(-6, 0, 0)), "Spine": (-12, 0, 6), "Head": (-10, 0, -6),
           "UpperArm_R": (-164, 10, 0), "ForeArm_R": (-6, 0, 0), "Hand_R": (52, 0, 0),
           "UpperArm_L": (-150, -22, 0), "ForeArm_L": (-20, 0, 0),
           "Thigh_L": (-56, -8, 0), "Shin_L": (92, 0, 0), "Foot_L": (20, 0, 0), "Thigh_R": (-8, 8, 0), "Shin_R": (64, 0, 0), "Foot_R": (30, 0, 0),
           "Cape1": (-4, 0, 0), "Cape2": (-12, 0, 0)}
vic_land = {"Hips": L(z=-0.06, r=(8, 0, 0)), "Spine": (6, 0, 4), "Head": (-8, 0, -4),
            "UpperArm_R": (-140, 16, 0), "ForeArm_R": (-30, 0, 0), "Hand_R": (40, 0, 0),
            "UpperArm_L": (-30, -40, 0), "ForeArm_L": (-60, 0, 0),
            "Thigh_L": (-34, -6, 0), "Shin_L": (66, 0, 0), "Foot_L": (-26, 0, 0), "Thigh_R": (-34, 6, 0), "Shin_R": (66, 0, 0), "Foot_R": (-26, 0, 0),
            "Cape1": (24, 0, 0), "Cape2": (44, 0, 0)}
vic_air2 = dict(vic_air)
vic_air2.update({"Hips": L(z=0.16, r=(-4, 0, 0)), "UpperArm_L": (-30, -70, 0), "ForeArm_L": (-30, 0, 0),
                 "Thigh_L": (-30, -10, 0), "Shin_L": (60, 0, 0), "Thigh_R": (-20, 10, 0), "Shin_R": (56, 0, 0)})
vic_settle = dict(vic_pose)
vic_settle.update({"Hips": L(z=-0.012, r=(-2, 0, 0)), "UpperArm_R": (-154, 14, 0), "Thigh_L": (-8, -8, 0), "Shin_L": (16, 0, 0), "Foot_L": (-8, 0, 0),
                   "Thigh_R": (-8, 8, 0), "Shin_R": (16, 0, 0), "Foot_R": (-8, 0, 0), "Cape1": (10, 0, 0), "Cape2": (18, 0, 0)})
rig.action("Victory", [
    (1, {"Hips": L()}), (7, vic_crouch), (13, vic_air), (19, vic_land), (24, vic_crouch | {"UpperArm_R": (-120, 16, 0), "ForeArm_R": (-40, 0, 0), "Hand_R": (36, 0, 0), "Hips": L(z=-0.05, r=(8, 0, 0))}),
    (29, vic_air2), (34, vic_land | {"Hips": L(z=-0.04, r=(5, 0, 0))}), (40, vic_pose), (46, vic_settle), (54, vic_pose),
], base=STANCE)

# ───────────────────────── 匯出 ─────────────────────────
bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
print("HERO tris", tri_count(mesh), "verts", len(mesh.data.vertices),
      "size", [round(max(p[i] for p in bb) - min(p[i] for p in bb), 3) for i in range(3)], "top", round(max(p.z for p in bb), 3))
if not ONLY:
    export_glb(rig, mesh, OUT_GLB)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

VIEWS = [("Front", (0, -2.25, 0.62), (0, 0, 0.58)), ("Side", (-2.25, 0, 0.62), (0, 0, 0.58)),
         ("3/4", (-1.45, -1.75, 0.95), (0, 0, 0.56)), ("Back 3/4", (1.35, 1.85, 0.95), (0, 0, 0.56))]
ACTION_FRAMES = {
    "Idle": [1, 16, 31, 46], "Run": [1, 5, 9, 13],
    "Slash": [7, 11, 14, 18], "Combo": [5, 9, 17, 28],
    "Cast": [9, 16, 27, 41], "Hit": [1, 4, 8, 13],
    "Faint": [7, 13, 19, 40], "Victory": [7, 13, 19, 54],
}
render_previews(rig, "hero_cute", PREVIEW_DIR, VIEWS, ACTION_FRAMES, ((-1.7, -2.3, 1.05), (0, -0.12, 0.52)),
                per_action_cam={"Faint": ((-1.8, -2.2, 1.3), (0, 0.3, 0.35)), "Combo": ((-2.1, -2.6, 1.15), (0, -0.28, 0.6)), "Victory": ((-1.8, -2.5, 1.1), (0, 0, 0.7)), "Slash": ((-1.8, -2.4, 1.05), (0, -0.2, 0.52))},
                strip_dir=STRIP_DIR, only=ONLY)
print("DONE hero", [a.name for a in bpy.data.actions])
