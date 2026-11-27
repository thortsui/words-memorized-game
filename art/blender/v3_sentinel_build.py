"""v3 Boss 1：腐朽守門騎士 sentinel（重建）。施工規格：art/v3/specs/boss_sentinel.md（比例表 §1、材質表 §2、細節 §3、壓迫感 §4、P2 §5）。
參考圖：art/reference/v2/sentinel_p1.jpg、sentinel_p2.jpg。
- 所有尺寸用 Ht（斗笠頂到腳底＝1）的比例寫：h(x)＝x·Ht。身體比例在 v3_sentinel_lib.SBody。
- 材質：v3_sentinel_mats（掃描貼圖＋程序節點）→ v3_sentinel_bake.assemble 烘成 A／B 兩組 2048 圖集。
- 二階 P2_*：剛體掛骨（v3_sentinel_util.split_p2），匯出後 v3_sentinel_post 拆成群組節點＋_mesh 子節點、scale 0。
- 動作：v3_sentinel_actions（複製自 v2a_hactions，加寬站距）＋本檔的武器握法表 WP（座標用 Ht 比例）。
用法：blender --background --factory-startup --python v3_sentinel_build.py -- [--quick] [--nobake] [--noanim] [--only A,B] [--norender]
"""
import bpy, bmesh, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector, Quaternion, Matrix
from v3_sentinel_lib import *
import v3_sentinel_bake as BK
import v3_sentinel_mats as MT
import v3_sentinel_util as VL

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOBAKE = "--nobake" in argv
NOANIM = "--noanim" in argv
NORENDER = "--norender" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_sentinel"
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v3_sentinel.blend")
TMP = os.path.join(HERE, "..", "v3", "tmp", "sentinel")
TILES = os.path.join(TMP, "tiles")
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

reset_scene()
Ht = 2.4
h = Ht
body = SBody(Ht)
j = body.j; U = body.U
B = Builder()
Builder.HIRES = False          # 段數都在這裡明確指定（不自動加倍）
rnd = random.Random(7)
mir = SBody.mir
torso = body.torso

# ---------------------------------------------------------------- 材質（§2 部位材質表）
MT.plate("plate", h, "A", base="#463a31", rust="#573a2a", edge="#6e665c", rlo=0.5, rhi=0.75, rust_amt=0.32, moss_amt=0.39, seed=1.0)
MT.plate("pauld", h, "A", base="#4d443b", rust="#5e4030", edge="#7a7064", rlo=0.45, rhi=0.75, rust_amt=0.45, moss_amt=0.42, seed=2.0)
MT.plate("arm", h, "A", base="#4a4037", rust="#573a2a", edge="#706a60", rlo=0.5, rhi=0.7, rust_amt=0.4, moss_amt=0.33, seed=3.0)
MT.plate("glove", h, "A", base="#3f3830", rust="#573a2a", edge="#6a645a", rlo=0.45, rhi=0.6, rust_amt=0.35, moss_amt=0.15, seed=4.0, hammer=0.012)
MT.plate("legp", h, "A", base="#433a32", rust="#573a2a", edge="#6e665c", rlo=0.55, rhi=0.75, rust_amt=0.45, moss_amt=0.39, seed=5.0)
MT.plate("knee", h, "A", base="#4f453b", rust="#573a2a", edge="#6e6458", rlo=0.4, rhi=0.7, rust_amt=0.4, moss_amt=0.42, seed=6.0)
MT.plate("greave", h, "A", base="#3e372f", rust="#573a2a", edge="#6a6258", rlo=0.55, rhi=0.8, rust_amt=0.5, moss_amt=0.33, seed=7.0,
         mud=(0.04, 0.13))
MT.plate("boot", h, "A", base="#3a332c", rust="#573a2a", edge="#655d52", rlo=0.6, rhi=0.85, metal=0.8, rust_amt=0.45, moss_amt=0.42,
         seed=8.0, mud=(0.0, 0.09))
MT.plate("hat", h, "A", base="#3d3630", rust="#5a3d2c", edge="#6e665c", rlo=0.55, rhi=0.75, rust_amt=0.4, moss_amt=0.24, seed=9.0,
         hammer=0.014, rings=((0.0, 0.0), 0.0035 * h), streak=1.4)
MT.plate("crown", h, "A", base="#34302b", rust="#5a3d2c", edge="#5e574e", rlo=0.55, rhi=0.7, rust_amt=0.3, moss_amt=0.20, seed=10.0)
MT.plate("gold", h, "A", base="#7a6440", rust="#5a3d2c", edge="#8a6a2a", rlo=0.4, rhi=0.5, metal=0.9, rust_amt=0.25, moss_amt=0.0,
         seed=11.0, flake="#3d3630", flake_amt=0.55, dent=0.4, edge_amt=0.6, grime=0.35)
MT.mail("mail", h, "A")
MT.flat("void", h, "A", "#0b0a0f", rough=1.0)
MT.flat("hatin", h, "A", "#14120f", rough=0.9, noise=0.2)
MT.linen("burlap", h, "A", base="#2b2a24", dark="#1c1b16", mold="#2a2f22", spacing=0.0045, wet=(0.70, 0.76), seed=2.0)
MT.linen("gambeson", h, "A", base="#29281f", dark="#1d1c16", mold="#2a2f22", spacing=0.004, wet=(0.40, 0.45), seed=3.0)

MT.linen("linen", h, "B", base="#33322a", dark="#22231a", mold="#2d3324", spacing=0.003, wet=(0.10, 0.25), seed=1.0, moss_amt=0.2)
MT.linen("linen2", h, "B", base="#2e2e26", dark="#20211a", mold="#2d3324", spacing=0.0032, wet=(0.12, 0.28), seed=4.0, moss_amt=0.2)
BELT_W, BELT_T = 0.025 * h, 0.006 * h
MT.leather("belt", h, "B", base="#3a2c22", stitch_rows=[BELT_T + 0.0035 * h, BELT_T + BELT_W - 0.0035 * h])
STRAP_W = 0.022 * h
MT.leather("strap", h, "B", base="#35281f", stitch_rows=[BELT_T * 0.6 + 0.003 * h, BELT_T * 0.6 + STRAP_W - 0.003 * h], seed=2.0)
MT.plate("buckle", h, "B", base="#4b4136", rust="#5a3d2c", edge="#6e665c", rlo=0.45, rhi=0.55, metal=0.9, rust_amt=0.35, moss_amt=0.0, seed=12.0)
MT.wood("wood", h, "B", base="#433a2e", wet="#2a261f", moss_amt=0.5, wet_z=(0.24, 0.40), seed=1.0)
MT.wood("woodback", h, "B", base="#443a2d", wet="#2e2a22", moss_amt=0.2, seed=3.0)
MT.plate("doorIron", h, "B", base="#4c3d30", rust="#6b3a22", edge="#6a5e50", rlo=0.6, rhi=0.8, metal=0.8, rust_amt=0.6, moss_amt=0.42, seed=13.0)
MT.plate("axe", h, "B", base="#4a443c", rust="#5a3d2c", edge="#7a746a", rlo=0.45, rhi=0.85, rust_amt=0.4, moss_amt=0.0, seed=14.0,
         edge_amt=1.0, scratch=1.5, grime=0.35, dent=0.25, blotch=0.22, edge_attr=True)
MT.plate("band", h, "B", base="#3d362e", rust="#5a3d2c", edge="#6a645a", rlo=0.5, rhi=0.6, rust_amt=0.25, moss_amt=0.0, seed=15.0)
MT.bark("bark", h, "B", base="#3b2a1e", dry="#4a3d30", moss_amt=0.15)
MT.bark("barkP2", h, "B", base="#3d3e36", dry="#2b2620", moss_amt=0.28, seed=3.0, contrast=1.0)
MT.moss_strip("mossS", h, "B", base="#26301c")
GREEN = "#7dffb0"
VL.glow_mat("Glow_Eye", GREEN, 1.0)
VL.glow_mat("Glow_Rune", GREEN, 0.15)
VL.glow_mat("Glow_Weapon", GREEN, 0.05)
VL.glow_mat("P2_Glow_Heart", GREEN, 2.2)
_hs = VL.glow_mat("P2_Glow_HeartShell", "#3e9a6a", 0.55)          # 半透明綠晶外殼（有光澤，看得到明暗）
_b = next(n for n in _hs.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
_b.inputs["Base Color"].default_value = (*MT.lin("#2f7a52"), 1); _b.inputs["Roughness"].default_value = 0.12
_b.inputs["Alpha"].default_value = 0.62
for _att, _v in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
    try:
        setattr(_hs, _att, _v)
    except Exception:
        pass
VL.glow_mat("P2_Glow_Root", GREEN, 0.7)
VL.glow_mat("P2_Glow_Weapon", GREEN, 1.6)
SHAFT_C = mir(body.grip_c)
MT.wood("shaft", h, "B", base="#4b4436", wet="#2e2a22", moss_amt=0.0, grain=0.25, rough=(0.75, 0.85), seed=5.0,
        polish=(tuple(SHAFT_C), 0.07 * h))


# ---------------------------------------------------------------- 小工具
def H_(x, y, z):
    return V(x * h, y * h, z * h)


def to_r(surf, R, extra=None):
    """shell 的 off：讓外輪廓半徑＝R（h 比例，可為 t 的函式）。"""
    def f(u, v, ang, t):
        rx, ry, _, _ = surf.row(t)
        rr = (R(t, v, ang) if callable(R) else R) * h
        return rr - (rx + ry) * 0.5 + (extra(u, v, ang, t) if extra else 0.0)
    return f


def crv(name, pts, r0, r1, mat, w, segs=5, **kw):
    n = len(pts)
    return B.tube(name, pts, [lerp(r0, r1, (i / (n - 1)) ** 0.8) for i in range(n)], segs, mat, w, **kw)


def dangle(name, p, d, length, r0, seed, w, mat="bark", n=7, fork=True, segs=5, grav=0.55, jit=0.35):
    """垂掛的細根：受重力下彎、隨機扭動、末端分叉。"""
    rr = random.Random(seed)
    d = d.normalized()
    pts = [p.copy()]
    for i in range(1, n + 1):
        d = (d + V(rr.uniform(-jit, jit), rr.uniform(-jit, jit), rr.uniform(-jit, jit) * 0.4) - Z * grav * (i / n)).normalized()
        pts.append(pts[-1] + d * length / n)
    obs = [crv(name, pts, r0, max(r0 * 0.25, 0.0012 * h), mat, w, segs, texel=1.0)]
    if fork:
        for q in range(2):
            k = int(n * rr.uniform(0.55, 0.8))
            dd = (pts[k + 1] - pts[k]).normalized() + V(rr.uniform(-0.9, 0.9), rr.uniform(-0.9, 0.9), rr.uniform(-0.4, 0.2))
            dd.normalize()
            bp = [pts[k]]
            for i in range(3):
                dd = (dd - Z * 0.3 + V(rr.uniform(-0.3, 0.3), rr.uniform(-0.3, 0.3), 0)).normalized()
                bp.append(bp[-1] + dd * length * 0.09)
            obs.append(crv(name + f"f{q}", bp, r0 * 0.5, 0.001 * h, mat, w, 4, texel=1.0))
    return obs


def wrap(name, surf, t0, t1, turns, a0, r, off, seed, w, n=22, mat="bark"):
    """纏繞肢體的細根（螺旋＋小擺動），off＝離身體表面距離（h）。"""
    rr = random.Random(seed)
    ph = rr.uniform(0, 6.28)
    pts = []
    for k in range(n + 1):
        s = k / n
        t = lerp(t0, t1, s)
        ang = a0 + turns * 360 * s + 18 * math.sin(s * 7 + ph)
        o = off(t, ang) if callable(off) else off * h
        pts.append(surf.pt(t, ang, o + r * 0.8 + 0.0022 * h + 0.0015 * h * math.sin(s * 13 + ph)))   # 稍微浮離甲面
    knots = [rr.uniform(0.15, 0.45), rr.uniform(0.55, 0.85)]
    rad = [r * (1.0 - 0.5 * (k / n)) * (1 + 0.18 * math.sin(k * 1.7 + ph) + sum(0.55 * math.exp(-((k / n - kk) / 0.04) ** 2) for kk in knots))
           for k in range(n + 1)]
    return B.tube(name, pts, rad, 6, mat, w, texel=1.0)


# ---------------------------------------------------------------- 內層：襯衣、鎖子甲
wt = body.w_torso()
B.shell("UnderTorso", torso, 0.445 * h, 0.83 * h, 0, 360, 16, 9, "gambeson", wt, off=0.002 * h, cap0=True, texel=1.0)
B.both(B.shell("UnderUArm", body.uarm, -0.02 * h, body.ua_len + 0.006 * h, 0, 360, 10, 4, "mail", body.w_elbow(), off=0.002 * h))
B.both(B.shell("UnderFArm", body.farm, -0.008 * h, body.fa_len, 0, 360, 10, 4, "mail", body.w_elbow(), off=0.002 * h))
B.both(B.shell("UnderThigh", body.thigh, -0.03 * h, body.th_len + 0.01 * h, 0, 360, 10, 5, "mail", body.w_knee(), off=0.002 * h))
B.both(B.shell("UnderShin", body.shin, -0.01 * h, body.sh_len, 0, 360, 10, 4, "mail", body.w_knee(), off=0.002 * h))

# ---------------------------------------------------------------- 胸甲＋護喉（§2 胸甲：中央縱脊、左胸長刮痕在材質；外輪廓胸寬 0.22／厚 0.15）
CU_OFF = 0.018


def cu_t1(u):
    a = angn(u * 360)
    hole = math.exp(-((abs(a) - 90) / 38) ** 2)
    back = smooth((abs(a) - 100) / 60)
    return lerp(lerp(0.776, 0.784, back), 0.728, hole) * h


def cu_off(u, v, ang, t):
    a = angn(ang)
    keel = 0.007 * h * math.exp(-(a / 7) ** 2) * math.sin(math.pi * clamp(v * 1.02))
    flare = 0.010 * h * (1 - smooth(v / 0.12))
    rx, ry, _, _ = torso.row(t)
    slim = -0.006 * h * math.exp(-((abs(a) - 90) / 25) ** 2) * smooth((t / h - 0.66) / 0.08)
    return CU_OFF * h + keel + flare + slim


def angn(a):
    return ((a + 180) % 360) - 180


cuirass = B.shell("Cuirass", torso, 0.592 * h, cu_t1, 0, 360, 32, 12, "plate", w_zchain(["Spine", (0.64 * h, "Spine2")], 0.05 * h),
                  off=cu_off, rim=0.004 * h)
B.rivets("CuirassRivets", [(torso.pt(0.603 * h, a, CU_OFF * h + 0.0105 * h), torso.nrm(0.603 * h, a)) for a in range(-165, 180, 22)],
         "plate", "Spine", r=0.0045 * h)
for k, (z0, z1, o) in enumerate(((0.772, 0.806, 0.021), (0.798, 0.834, 0.017))):
    B.shell(f"Gorget{k}", torso, z0 * h, z1 * h, 0, 360, 20, 3, "plate", {"Spine2": 0.6 - 0.3 * k, "Neck": 0.4 + 0.3 * k},
            off=lambda u, v, ang, t, o=o: o * h + 0.006 * h * (1 - v) ** 2, rim=0.003 * h)
    B.rivets(f"GorgetRivets{k}", [(torso.pt((z0 + 0.007) * h, a, (o + 0.0062) * h), torso.nrm((z0 + 0.007) * h, a)) for a in (-36, -12, 12, 36)],
             "plate", {"Spine2": 0.5, "Neck": 0.5}, r=0.0035 * h)

# ---------------------------------------------------------------- 裙甲 3 段（壓在長擺上）
for k in range(3):
    zt = (0.578 - k * 0.026) * h
    B.shell(f"Fauld{k}", torso, zt - 0.034 * h, zt, 0, 360, 30, 2, "plate",
            {"Spine": 0.5, "Hips": 0.5} if k == 0 else {"Hips": 1.0},
            off=lambda u, v, ang, t, k=k: to_r(torso, 0.0)(u, v, ang, t) * 0 + (0.024 + 0.005 * k) * h + 0.008 * h * (1 - v), rim=0.003 * h)
    B.rivets(f"FauldRivets{k}", [(torso.pt(zt - 0.012 * h, a + 14 * k, (0.024 + 0.005 * k + 0.0035) * h), torso.nrm(zt - 0.012 * h, a + 14 * k))
                                 for a in range(-150, 180, 30)], "plate", "Hips", r=0.0035 * h)

# ---------------------------------------------------------------- 腰帶 2 條（皮＋縫線＋方形鐵扣），交叉
def belt(name, zc, off, tilt=0.0, tilt_dir=90, w=None, wid=BELT_W, thick=BELT_T, mat="belt", nu=36, surf=torso):
    def fn(u, v):
        ang = u * 360
        zz = zc - tilt * h * math.cos(math.radians(ang - tilt_dir))
        k = int(round(v * 3))
        dz = (-wid / 2, -wid / 2, wid / 2, wid / 2)[k]
        o = (off * h - 0.001 * h, off * h + thick, off * h + thick, off * h - 0.001 * h)[k]
        return surf.pt(zz + dz, ang, o)
    return B.grid(name, nu, 3, fn, mat, w or {"Spine": 0.4, "Hips": 0.6}, [V(0, 0, zc - 0.1), V(0, 0, zc), V(0, 0, zc + 0.1)],
                  closed_u=True, sharp=30)


belt("Belt1", 0.585 * h, 0.025)
belt("Belt2", 0.566 * h, 0.029, tilt=0.016, tilt_dir=-70)


def buckle(name, zc, ang, off, w):
    n = torso.nrm(zc, ang)
    side = Z.cross(n).normalized()
    c = torso.pt(zc, ang, off * h)
    s = 0.015 * h
    obs = []
    for q, (a, b) in enumerate(((V(-1, 0, -1), V(1, 0, -1)), (V(1, 0, -1), V(1, 0, 1)), (V(1, 0, 1), V(-1, 0, 1)), (V(-1, 0, 1), V(-1, 0, -1)))):
        pa = c + side * a.x * s + Z * a.z * s; pb = c + side * b.x * s + Z * b.z * s
        obs.append(B.tube(f"{name}B{q}", [pa, pb], [(0.0032 * h, 0.0022 * h)] * 2, 6, "buckle", w, flat=n))
    obs.append(B.tube(f"{name}Prong", [c - side * s * 0.9 + n * 0.001 * h, c + side * s * 0.2 + n * 0.003 * h], [0.0016 * h] * 2, 5, "buckle", w))
    return obs


buckle("Buckle1", 0.585 * h, -6, 0.035, {"Spine": 0.4, "Hips": 0.6})
buckle("Buckle2", 0.566 * h - 0.016 * h * math.cos(math.radians(-40 + 70)), -40, 0.039, {"Spine": 0.4, "Hips": 0.6})
# 皮帶尾垂下
for q, (ang, ln) in enumerate(((6, 0.07), (-30, 0.05))):
    n = torso.nrm(0.578 * h, ang); side = Z.cross(n).normalized()
    p0 = torso.pt(0.578 * h, ang, 0.036 * h)
    B.tube(f"BeltEnd{q}", [p0, p0 - Z * ln * 0.5 * h + n * 0.006 * h, p0 - Z * ln * h + n * 0.010 * h + side * 0.006 * h],
           [(0.011 * h, 0.0025 * h)] * 3, 6, "strap", "Hips", flat=side, exp=4)

# 背門板的斜背帶：左肩 → 右腰（在胸前），背後接到門板
def strap_path(s):
    return lerp(0.775, 0.600, s) * h, lerp(150, -105, s)


def guige_fn(u, v):
    zz, ang = strap_path(u)
    z2, a2 = strap_path(min(u + 0.01, 1.0)); z1, a1 = strap_path(max(u - 0.01, 0.0))
    r = (torso.row(zz)[0] + torso.row(zz)[1]) * 0.5 + 0.024 * h
    dz, darc = z2 - z1, math.radians(a2 - a1) * r
    L = math.hypot(dz, darc) or 1.0
    pz, parc = -darc / L, dz / L
    k = int(round(v * 3))
    wv = (-0.5, -0.5, 0.5, 0.5)[k] * STRAP_W
    o = (0.022 * h, 0.022 * h + BELT_T * 0.6, 0.022 * h + BELT_T * 0.6, 0.022 * h)[k] + 0.004 * h * math.sin(math.pi * u)
    return torso.pt(zz + pz * wv, ang + math.degrees(parc * wv / r), o)


B.grid("Guige", 40, 3, guige_fn, "strap", w_zchain(["Spine", (0.66 * h, "Spine2")], 0.05 * h), [V(0, 0, 0.6 * h), V(0, 0, 0.78 * h)],
       sharp=30)

# ---------------------------------------------------------------- 肩甲（3 片疊、上片往外翹、翻邊磨亮、上緣鉚釘、片間皮帶）
def pauldron():
    obs = []
    out = body.uarm.u
    pole = (out * 0.50 + Z * 0.86).normalized()
    ex = (FWD - pole * FWD.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["UpperArmL"] + Z * 0.036 * h + X * 0.018 * h
    rad = (0.072 * h, 0.070 * h, 0.054 * h)
    wd = {"ShoulderL": 0.6, "UpperArmL": 0.4}
    # 3 片疊：頂蓋＋兩圈往下疊的甲片，每片下緣捲邊、往外放大一點，最下片外翹
    for k, (v0_, v1_, sc_) in enumerate(((0.0, 0.31, 1.03), (0.27, 0.48, 1.005), (0.44, 0.64, 0.975))):   # 上片壓下片（瓦片式）
        obs.append(B.ellipsoid(f"Pauldron{k}", c, (ex, ey, pole), tuple(r_ * sc_ for r_ in rad), 22, 4 if k else 5, "pauld", wd, v0=v0_, v1=v1_,
                               rim=0.0045 * h, dent=lambda d, u, v, k=k: 1 + (0.12 * smooth((v - 0.4) / 0.6) ** 1.5 if k == 2 else 0.02 * v)))

    def fl(u, v):
        ph = math.radians(lerp(170, 370, u)); th = math.radians(42)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        p = c + ex * (d.x * rad[0]) + ey * (d.y * rad[1]) + pole * (d.z * rad[2])
        up = (Z * 0.96 + out * 0.27).normalized()      # 上片外翹 15°
        prof = math.sin(math.pi * u) ** 0.4
        return p + up * (0.016 * h * v * prof) + out * (0.010 * h * v * v) - pole * 0.001 * h
    # （第 2 輪：拿掉頂上的立片，讀起來像把手；改成肩甲下緣往外翹，見 dent）
    S = body.uarm
    pts = []
    for k in range(2):
        ta = (0.012 + k * 0.020) * h
        tb = ta + 0.030 * h
        obs.append(B.shell(f"PauldronLame{k}", S, ta, tb, 90 - 118, 90 + 118, 14, 2, "pauld",
                           {"ShoulderL": 0.3, "UpperArmL": 0.7} if k == 0 else "UpperArmL",
                           off=lambda u, v, ang, t, k=k: (0.033 - k * 0.004) * h + 0.007 * h * v, rim=0.0035 * h))
        for a in range(90 - 104, 90 + 105, 26):
            t = tb - 0.006 * h
            pts.append((S.pt(t, a, (0.033 - k * 0.004) * h + 0.0068 * h), S.nrm(t, a)))
    obs.append(B.shell("PauldronStrap", S, 0.010 * h, 0.065 * h, 90 - 50, 90 + 50, 6, 3, "strap", "UpperArmL", off=0.022 * h))
    for ph in range(200, 345, 18):
        th = math.radians(70)
        d = Vector((math.sin(th) * math.cos(math.radians(ph)), math.sin(th) * math.sin(math.radians(ph)), math.cos(th)))
        p = c + (ex * (d.x * rad[0]) + ey * (d.y * rad[1]) + pole * (d.z * rad[2])) * 1.02
        pts.append((p, (p - c)))
    obs.append(B.rivets("PauldronRivets", pts, "pauld", "UpperArmL", r=0.0040 * h))
    return obs


B.both(pauldron())

# ---------------------------------------------------------------- 手臂：上臂筒甲 2 節（外徑 0.09）、肘甲＋扇形翼、護臂（外徑 0.085，外側縱脊）、漏斗袖口（0.10）
def arm():
    obs = []
    S, F = body.uarm, body.farm
    La, Lf = body.ua_len, body.fa_len
    obs.append(B.shell("Rerebrace", S, La * 0.42, La * 0.93, 0, 360, 14, 4, "arm", "UpperArmL",
                       off=to_r(S, lambda t, v, ang: 0.0445 + 0.002 * math.sin(math.pi * v), lambda u, v, ang, t: 0.003 * h * math.exp(-(angn(ang - 90) / 16) ** 2)), rim=0.0035 * h))
    bend = (body.fd - body.ud * body.fd.dot(body.ud)).normalized()
    pole = (-bend * 0.75 + S.u * 0.5).normalized()
    ex = (body.ud + body.fd).normalized(); ex = (ex - pole * ex.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["ForearmL"] + bend * 0.006 * h
    we = {"UpperArmL": 0.5, "ForearmL": 0.5}
    obs.append(B.ellipsoid("Couter", c, (ex, ey, pole), (0.040 * h, 0.036 * h, 0.040 * h), 14, 6, "arm", we, v0=0, v1=0.54,
                           rim=0.003 * h, dent=lambda d, u, v: 1 + 0.12 * math.exp(-(v / 0.25) ** 2)))
    wo = S.u
    wc = j["ForearmL"] + wo * 0.036 * h + bend * 0.010 * h
    e1 = (body.ud + body.fd).normalized(); e2 = wo.cross(e1).normalized()
    obs.append(B.ellipsoid("CouterWing", wc, (e1, e2, wo), (0.032 * h, 0.028 * h, 0.008 * h), 12, 4, "arm", we, v0=0, v1=0.5, rim=0.002 * h))
    ridge = lambda u, v, ang, t: 0.004 * h * math.exp(-(angn(ang - 95) / 14) ** 2)
    obs.append(B.shell("Vambrace", F, Lf * 0.06, Lf * 0.84, 0, 360, 14, 6, "arm", "ForearmL",
                       off=to_r(F, lambda t, v, ang: lerp(0.045, 0.0372, smooth(v)), ridge), rim=0.003 * h))
    obs.append(B.shell("GauntletCuff", F, Lf * 0.84, Lf * 1.05, 0, 360, 14, 4, "glove", "ForearmL",
                       off=to_r(F, lambda t, v, ang: lerp(0.0385, 0.050, v ** 1.5)), rim=0.004 * h))
    pts = []
    for a in (40, 140, 220, 320):
        t = Lf * 0.20
        pts.append((F.pt(t, a, 0.0425 * h - F.row(t)[0] + 0.001 * h), F.nrm(t, a)))
    obs.append(B.rivets("ArmRivets", pts, "arm", "ForearmL", r=0.0035 * h))
    return obs


B.both(arm())


# ---------------------------------------------------------------- 鐵手套（長 0.10×寬 0.075×厚 0.05；指節分 4 段；手背 3 鉚釘）
def gauntlet(open_amt=0.0, name="Glove"):
    obs = []
    Wp = j["HandL"]; a = body.hand_a; v = body.hand_v; u = body.hand_u; K = body.knuckle
    # 手掌（內）＋手背甲 2 片疊（外側往指節方向一片壓一片）
    pts = [Wp - a * 0.006 * h - u * 0.004 * h, Wp + a * 0.024 * h - u * 0.002 * h, K - a * 0.010 * h - u * 0.004 * h]
    obs.append(B.tube(name + "Palm", pts, [(0.030 * h, 0.013 * h), (0.034 * h, 0.014 * h), (0.034 * h, 0.012 * h)], 10, "glove", "HandL",
                      exp=2.1, flat=v))
    for q, (s0, s1, lift) in enumerate(((-0.004, 0.034, 0.010), (0.028, 0.062, 0.011))):
        c0 = Wp + a * s0 * h + u * lift * h; c1 = Wp + a * s1 * h + u * (lift + 0.001) * h
        obs.append(B.tube(f"{name}Plate{q}", [c0, c0.lerp(c1, 0.5) + u * 0.003 * h, c1],
                          [(0.032 * h, 0.006 * h), (0.0375 * h, 0.007 * h), (0.036 * h, 0.006 * h)], 10, "glove", "HandL", exp=2.4, flat=v))
    rc = body.grip_rc * (1 + open_amt * 0.8)
    er = body.knuckle_dir
    et = (a - er * a.dot(er)).normalized()
    gc0 = K - er * rc
    sweep = 240 * (1 - open_amt * 0.55)
    fr = body.finger_r
    for i, o in enumerate((-0.0275, -0.009, 0.009, 0.0275)):
        g = gc0 + v * o * h - a * (0.003 * h * abs(i - 1.3))
        ln = (1.0, 1.06, 1.0, 0.86)[i]
        for sgi in range(4):          # 指節 4 段，每段前端略大（疊片）
            th0 = math.radians(sweep * ln * sgi / 4 - 4)
            th1 = math.radians(sweep * ln * (sgi + 1) / 4 + 2)
            fp = [g + (er * math.cos(th) + et * math.sin(th)) * rc for th in (th0, (th0 + th1) / 2, th1)]
            rr = fr * (1.08 - 0.06 * sgi)
            obs.append(B.tube(f"{name}F{i}{sgi}", fp, [rr * 1.06, rr, rr * 0.92], 6, "glove", "HandL", texel=1.0))
    g = gc0 + v * 0.045 * h
    tp = [Wp + a * 0.020 * h + v * 0.028 * h - u * 0.004 * h]
    for th in (150, 95, 40):
        thr = math.radians(th)
        tp.append(g + (-er * math.cos(thr) + et * math.sin(thr)) * rc * 0.95 - v * 0.005 * h * (150 - th) / 110)
    obs.append(B.tube(name + "Thumb", tp, [0.012 * h, 0.011 * h, 0.0095 * h, 0.008 * h], 6, "glove", "HandL", texel=1.0))
    obs.append(B.rivets(name + "Rivets", [(Wp + a * (0.012 + 0.016 * q) * h + u * 0.0185 * h + v * (0.012 * (q - 1)) * h, u) for q in range(3)],
                        "glove", "HandL", r=0.0035 * h))
    return obs


B.mirror_only(gauntlet(0.0, "GloveR"))
gauntlet(0.12, "GloveL")

# ---------------------------------------------------------------- 腿：大腿正面板（外徑 0.10）、膝甲（0.085）＋側扇、脛甲（上緣外擴 0.085→踝 0.065）、鐵靴
def legs():
    obs = []
    T, S = body.thigh, body.shin
    Lt, Ls = body.th_len, body.sh_len
    obs.append(B.shell("Cuisse", T, Lt * 0.10, Lt * 0.86, -110, 120, 14, 5, "legp", "ThighL",
                       off=to_r(T, lambda t, v, ang: lerp(0.053, 0.049, v), lambda u, v, ang, t: 0.003 * h * math.exp(-(angn(ang) / 12) ** 2)),
                       rim=0.004 * h))
    wk = {"ThighL": 0.5, "ShinL": 0.5}
    c = j["ShinL"] + FWD * 0.006 * h
    pole = (FWD * 0.97 + Z * 0.12).normalized()
    ex = X.copy(); ey = pole.cross(ex)
    obs.append(B.ellipsoid("Poleyn", c, (ex, ey, pole), (0.040 * h, 0.044 * h, 0.040 * h), 14, 6, "knee", wk, v0=0, v1=0.52, rim=0.003 * h,
                           dent=lambda d, u, v: 1 + 0.10 * math.exp(-(v / 0.3) ** 2)))
    wc = j["ShinL"] + X * 0.038 * h + FWD * 0.004 * h
    obs.append(B.ellipsoid("PoleynWing", wc, (FWD, Z, X), (0.026 * h, 0.030 * h, 0.007 * h), 12, 4, "knee", wk, v0=0, v1=0.5, rim=0.002 * h))
    obs.append(B.shell("PoleynUp", T, Lt * 0.84, Lt * 0.97, -85, 85, 10, 1, "knee", {"ThighL": 0.8, "ShinL": 0.2},
                       off=to_r(T, 0.046), rim=0.003 * h))
    obs.append(B.shell("PoleynLo", S, Ls * 0.06, Ls * 0.16, -85, 85, 10, 1, "knee", {"ThighL": 0.2, "ShinL": 0.8},
                       off=to_r(S, 0.046), rim=0.003 * h))
    ridge = lambda u, v, ang, t: 0.004 * h * math.exp(-(angn(ang) / 11) ** 2)
    obs.append(B.shell("Greave", S, Ls * 0.13, Ls * 0.97, 0, 360, 14, 7, "greave", "ShinL",
                       off=to_r(S, lambda t, v, ang: lerp(0.0455, 0.0325, smooth(v * 1.1)) + 0.004 * smooth((0.12 - v) / 0.12), ridge),
                       rim=0.003 * h))
    pts = [(T.pt(Lt * f, a, 0.050 * h - T.row(Lt * f)[0] + 0.0012 * h), T.nrm(Lt * f, a)) for a in (-70, 70) for f in (0.25, 0.7)]
    obs.append(B.rivets("CuisseRivets", pts, "legp", "ThighL", r=0.0035 * h))
    pts = [(S.pt(Ls * 0.22, a, 0.044 * h - S.row(Ls * 0.22)[0] + 0.001 * h), S.nrm(Ls * 0.22, a)) for a in (60, 120, 240, 300)]
    obs.append(B.rivets("GreaveRivets", pts, "greave", "ShinL", r=0.0035 * h))
    return obs


def sabaton():
    """鐵靴：長 0.14 × 寬 0.06；靴尖略尖、前端 3 片疊甲；厚鞋底。"""
    ank = j["FootL"]
    st = [(0.036, 0.020, 0.040), (0.024, 0.029, 0.060), (0.002, 0.031, 0.066), (-0.025, 0.031, 0.054), (-0.046, 0.030, 0.042),
          (-0.066, 0.027, 0.032), (-0.082, 0.020, 0.024), (-0.092, 0.008, 0.014)]
    obs = []
    pts = []; radii = []
    for y, wd, hh in st:
        pts.append(V(ank.x, ank.y + y * h, hh * h * 0.5 + 0.004 * h)); radii.append((wd * h, hh * h * 0.5))
    obs.append(B.tube("Sabaton", pts, radii, 14, "boot", "FootL", flat=X, exp=2.8, sharp=40))
    for k, (y0, s) in enumerate(((-0.036, 1.07), (-0.054, 1.06), (-0.070, 1.05))):
        yy = ank.y + y0 * h
        i = min(range(len(st)), key=lambda q: abs(st[q][0] - y0))
        wd, hh = st[i][1], st[i][2]
        c = V(ank.x, yy, hh * h * 0.5 + 0.004 * h)
        obs.append(B.tube(f"SabatonLame{k}", [c + Y * 0.006 * h, c - Y * 0.004 * h], [(wd * h * s, hh * h * 0.5 * s), (wd * h * (s - 0.03), hh * h * 0.5 * (s - 0.03))],
                          16, "boot", "FootL", flat=X, exp=2.3, cap=False, sharp=50))
    sole = [V(ank.x, ank.y + y * h, 0.005 * h) for y in (0.040, 0.02, -0.02, -0.055, -0.08, -0.094)]
    obs.append(B.tube("SabatonSole", sole, [(0.019 * h, 0.005 * h), (0.027 * h, 0.005 * h), (0.0285 * h, 0.005 * h), (0.0265 * h, 0.005 * h),
                                            (0.018 * h, 0.005 * h), (0.005 * h, 0.004 * h)], 8, "boot", "FootL", flat=X, exp=3.0, sharp=50))
    return obs


B.both(legs())
B.both(sabaton())

# ---------------------------------------------------------------- 頭：兜帽（暗粗麻）＋臉部黑洞＋兩點綠眼
HC = V(0, -0.004 * h, 0.862 * h)


def hood_pt(u, v):
    a = math.radians(lerp(40, 320, u))
    z = lerp(0.776, 0.925, v) * h
    bell = 1 - 0.55 * smooth((v - 0.70) / 0.30) ** 1.5
    rx = (lerp(0.050, 0.042, smooth(v * 1.4)) + 0.003 * math.sin(math.pi * v)) * h * bell
    ry = (lerp(0.053, 0.049, smooth(v * 1.4)) + 0.003 * math.sin(math.pi * v)) * h * bell
    fold = 0.0035 * h * math.sin(a * 7 + v * 3) * (1 - v) + 0.002 * h * math.sin(a * 13 + 1.1)
    return V(math.sin(a) * (rx + fold), -math.cos(a) * (ry + fold) + 0.006 * h, z)


B.grid("Hood", 22, 8, hood_pt, "burlap", {"Head": 0.7, "Neck": 0.3}, [HC, HC - Z * 0.05 * h], rim=0.002 * h, sharp=60)
hrng = random.Random(3)
cut = [hrng.uniform(0, 1) for _ in range(30)]


def cape_pt(u, v):
    a = math.radians(lerp(30, 330, u))
    k = int(u * 29)
    drop = 0.020 * h * cut[k] * v
    z = lerp(0.800, 0.765, v) * h - drop
    r = lerp(0.052, 0.078, v) * h
    fold = 0.004 * h * math.sin(a * 9 + 1.3) * v
    return V(math.sin(a) * (r + fold), -math.cos(a) * (r * 1.05 + fold) + 0.006 * h, z)


cape = B.grid("HoodCape", 30, 4, cape_pt, "burlap", {"Neck": 0.5, "Spine2": 0.5}, [V(0, 0.006 * h, 0.83 * h)], sharp=60)
cape["cloth"] = 0.004 * h
B.ellipsoid("FaceVoid", HC + V(0, -0.006 * h, 0.002 * h), (X, Y, Z), (0.036 * h, 0.038 * h, 0.050 * h), 12, 8, "void", "Head")
for sx in (-1, 1):
    p = HC + V(sx * 0.015 * h, -0.048 * h, 0.004 * h)
    B.ellipsoid(f"Eye{sx}", p, (X, Z, Y), (0.0045 * h, 0.0035 * h, 0.002 * h), 10, 5, "Glow_Eye", "Head")

# ---------------------------------------------------------------- 斗笠：平寬圓盤（直徑 0.36）＋中央低圓頂冠（0.13×0.035）＋冠根階梯環
KC = V(0, 0.000, 0.0)
HAT = [(0.000, 1.000), (0.022, 0.9988), (0.042, 0.995), (0.056, 0.988), (0.0635, 0.979), (0.065, 0.971), (0.0665, 0.968),
       (0.0745, 0.9665), (0.076, 0.963), (0.092, 0.958), (0.108, 0.953), (0.126, 0.948), (0.145, 0.9435), (0.163, 0.939), (0.180, 0.935)]
HV = [i / (len(HAT) - 1) for i in range(len(HAT))]
hrnd = random.Random(12)
hdent = [hrnd.uniform(-1, 1) for _ in range(10)]
CRACK_U = 0.875      # 前左（u=0 正前、u=0.25 角色左）


def hat_rz(v):
    k = min(int(v * (len(HAT) - 1)), len(HAT) - 2)
    s = v * (len(HAT) - 1) - k
    r = lerp(HAT[k][0], HAT[k + 1][0], s); z = lerp(HAT[k][1], HAT[k + 1][1], s)
    return r, z


def hat_pt(u, v, lift=0.0, shrink=0.0):
    r, z = hat_rz(v)
    a = 2 * math.pi * u
    edge = smooth((r - 0.12) / 0.06)
    wob = 0.004 * (hdent[int(u * 10) % 10] * (1 - abs(((u * 10) % 1) - 0.5) * 2)) * edge
    sag = -0.003 * math.sin(a * 3 + 0.7) * edge
    du = (u - CRACK_U + 0.5) % 1.0 - 0.5
    notch = 0.050 * math.exp(-(du / 0.006) ** 2) * smooth((r - 0.12) / 0.06)
    rr = max(r - shrink - notch, 0.0)
    return V(math.sin(a) * rr * h, -math.cos(a) * rr * h, (z + wob + sag + lift) * h)


wh = "Head"
nvh = len(HAT) - 1
B.grid("KasaTop", 48, nvh - 5, lambda u, v: hat_pt(u, 5 / nvh + v * (1 - 5 / nvh)), "hat", wh, V(0, 0, 0.8 * h), closed_u=True, texel=1.0, sharp=40)
B.grid("KasaCrown", 40, 5, lambda u, v: hat_pt(u, v * 5 / nvh), "crown", wh, V(0, 0, 0.8 * h), closed_u=True, texel=1.0, sharp=40)
B.grid("KasaUnder", 44, 5, lambda u, v: hat_pt(u, 0.55 + 0.45 * v, -0.008), "hatin", wh, V(0, 0, 1.2 * h), closed_u=True, texel=1.0)
B.tube("KasaRim", [hat_pt(i / 48, 1.0, -0.004, -0.0015) for i in range(49)], [(0.0045 * h, 0.0055 * h)] * 49, 5, "hat", wh, texel=1.0, cap=False)
BAND_V70 = None
for vv in HV:
    pass


def v_at_r(rt):
    lo, hi = 0.0, 1.0
    for _ in range(30):
        m = (lo + hi) / 2
        if hat_rz(m)[0] < rt:
            lo = m
        else:
            hi = m
    return lo


v_root, v70, v_rim = v_at_r(0.070), v_at_r(0.126), v_at_r(0.176)
bw = 0.006 * h
B.tube("KasaCrownBand", [hat_pt(i / 32, v_root, 0.0022) for i in range(33)], [(bw * 0.9, 0.0018 * h)] * 33, 4, "gold", wh, texel=1.0,
       flat=None, up=Z, cap=False)
B.tube("KasaBand70", [hat_pt(i / 40, v70, 0.0018) for i in range(41)], [(bw, 0.0016 * h)] * 41, 4, "gold", wh, texel=1.0, cap=False)
rivs = []
for q in range(4):
    a0 = q * 0.25
    vs = [v_root + (v_rim - v_root) * x / 10 for x in range(11)]
    pts = [hat_pt(a0, vv, 0.0020) for vv in vs]
    tang = V(math.cos(2 * math.pi * a0), math.sin(2 * math.pi * a0), 0)
    B.tube(f"KasaBand{q}", pts, [(bw, 0.0016 * h)] * len(pts), 8, "gold", wh, flat=tang, exp=4)
    rr = 0.085
    while rr < 0.176:
        rivs.append((hat_pt(a0, v_at_r(rr), 0.0036), Z + V(math.sin(2 * math.pi * a0), -math.cos(2 * math.pi * a0), 0) * 0.5))
        rr += 0.03
for q in range(16):
    rivs.append((hat_pt(q / 16 + 1 / 32, v70, 0.0034), Z))
B.rivets("KasaRivets", rivs, "gold", wh, r=0.0032 * h)
# 簷前左：2–4 條長短不一的苔條／細根（取代 v2 的一排木刺）
for q, (du_, ln) in enumerate(((-0.030, 0.055), (-0.012, 0.035), (0.010, 0.048))):
    p = hat_pt(CRACK_U + du_ + 0.02, 0.985, -0.006)
    side = V(math.cos(2 * math.pi * (CRACK_U + du_)), math.sin(2 * math.pi * (CRACK_U + du_)), 0)
    pts = [p - Z * ln * h * i / 5 + side * 0.003 * h * math.sin(i * 1.3 + q) for i in range(6)]
    B.tube(f"KasaMoss{q}", pts, [0.0035 * h * (1 - i / 5.5) ** 1.3 + 0.0004 * h for i in range(6)], 5, "mossS", wh, texel=1.0)
dangle("KasaRoot", hat_pt(CRACK_U + 0.04, 0.97, -0.006), -Z + V(0.2, -0.2, 0), 0.06 * h, 0.0035 * h, 31, wh, n=6)

# ---------------------------------------------------------------- 長擺：3 層厚麻布（前片／左右側片／後片），縱向撕條、破洞、毛邊、垂墜皺褶
def rag_panel(name, top, nrm, length, mat, w, nv=24, flare=0.05, fold_n=3.0, fold_amp=0.006, holes=5, seed=1, spread=0.0,
              side=None, strip=(0.015, 0.04), rag=0.10, slit=(0.35, 0.75), width=None, colw=0.011, asym=0.0):
    """自建 bmesh 的破麻布片（v3 第 2 版）：
    - 撕裂處（slit）下方的頂點左右各一份 → 縱向撕條；條寬 strip 隨機、各條長度差到 rag·H、末端收尖＋每欄長短不一（纖維毛邊）。
    - 破洞：不規則撕裂形（帶雜訊的橢圓，以面中心判定），洞緣頂點往外翻（捲邊）。
    - 縱向皺褶 fold_n 條（幅度 fold_amp·H）＋下緣捲邊；asym：下緣左右長度差（比例）。加厚由 cloth 屬性（solidify）做。"""
    rr = random.Random(seed)
    sd = side or X
    W = width or 0.12 * h
    bounds = [0.0]
    while bounds[-1] < 1.0 - 1e-6:
        bounds.append(min(1.0, bounds[-1] + rr.uniform(*strip) * h / W))
    if 1.0 - bounds[-2] < strip[0] * h / W * 0.6 and len(bounds) > 2:
        bounds.pop(-2)
    nS = len(bounds) - 1
    s_len = [rr.uniform(0, rag) * h / length for _ in range(nS)]
    s_top = [rr.uniform(*slit) for _ in range(nS + 1)]
    s_top[0] = s_top[-1] = 0.0
    s_sw = [V(rr.uniform(-1, 1), rr.uniform(-1, 1), 0) * 0.012 * h for _ in range(nS)]
    s_tip = [rr.uniform(0.25, 0.60) for _ in range(nS)]          # 末端收尖程度
    s_tw = [math.radians(rr.uniform(12, 28)) * rr.choice((-1, 1)) for _ in range(nS)]   # 撕條扭轉
    s_bd = [rr.uniform(-1, 1) for _ in range(nS)]                 # 撕條彎曲
    s_cut = [rr.uniform(0.02, 0.05) * h for _ in range(nS)]       # 末端 V 形尖的深度
    cols = []
    for s_ in range(nS):
        k = max(2, int(round((bounds[s_ + 1] - bounds[s_]) * W / (colw * h))))
        for q in range(k):
            cols.append((s_, bounds[s_] + (bounds[s_ + 1] - bounds[s_]) * q / k))
    cols.append((nS - 1, 1.0))
    nC = len(cols)
    ph = rr.uniform(0, 6.28)
    jag = [rr.uniform(-0.007, 0.006) * h for _ in range(nC)]
    # 破洞：中心（欄, 列）、半徑（欄數, 列數）、形狀雜訊
    hole_def = []
    for _ in range(holes):
        hole_def.append((rr.uniform(1.5, nC - 2.5), rr.uniform(nv * 0.30, nv * 0.82), rr.uniform(0.9, 1.9), rr.uniform(0.9, 1.6),
                         rr.uniform(0, 6.28), rr.uniform(0, 6.28)))

    def in_hole(x, y):
        for cx, cy, ra, rb, p1, p2 in hole_def:
            dx, dy = (x - cx) / ra, (y - cy) / rb
            r = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            if r < 1.0 + 0.32 * math.sin(3 * th + p1) + 0.18 * math.sin(5 * th + p2):
                return (cx, cy)
        return None
    hs = {}
    for ci in range(nC - 1):
        for jv in range(nv):
            c = in_hole(ci + 0.5, jv + 0.5)
            if c:
                hs[(ci, jv)] = c
    curl = {}
    for (ci, jv), c in hs.items():
        for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1)):
            curl[(ci + di, jv + dj)] = c

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("atlas")

    def pos(u, v, s_, ci, jv):
        st = max(s_top[s_], s_top[s_ + 1])
        free = smooth((v - st) / max(1e-3, 1 - st))
        uc = (bounds[s_] + bounds[s_ + 1]) * 0.5
        hw = max((bounds[s_ + 1] - bounds[s_]) * 0.5, 1e-4)
        tipv = smooth((v - 0.80) / 0.20) * free
        # 末端收成 V 形碎尖：離條帶中線愈遠愈短，加一點雜訊
        cut = s_cut[s_] * min(1.0, abs(u - uc) / hw) + jag[ci]
        L = length * (1 - s_len[s_] * free + asym * (u - 0.5)) - cut * tipv
        n = nrm(u)
        wave = math.sin(2 * math.pi * fold_n * u + ph) + 0.35 * math.sin(2 * math.pi * fold_n * 2.3 * u + ph * 2)
        wave = math.copysign(abs(wave) ** 0.75, wave)
        p = top(u) - Z * (L * v)
        # 鐘形：上段往外張、下段順重力垂直（不是一路斜插出去）
        p += n * (flare * length * smooth(v * 1.7) + fold_amp * h * wave * smooth(v * 3.5) * (0.75 + 0.35 * v))
        p += sd * ((u - 0.5) * spread * smooth(v * 1.7))
        p += s_sw[s_] * free * v
        # 撕條扭轉（繞自己中線）＋彎曲
        p += n * ((u - uc) * W * math.tan(s_tw[s_] * free))
        p += n * (s_bd[s_] * 0.012 * h * math.sin(math.pi * free)) + sd * (s_bd[s_] * 0.006 * h * free * free)
        p += sd * ((uc - u) * W * s_tip[s_] * tipv)
        p += n * 0.005 * h * smooth((v - 0.92) / 0.08)
        c = curl.get((ci, jv))
        if c:
            dx, dy = ci - c[0], jv - c[1]
            dl = math.hypot(dx, dy) or 1.0
            p += n * 0.0045 * h + (sd * (dx / dl) * 0.003 * h) - Z * (dy / dl) * 0.003 * h
            hr_ = random.Random(ci * 7919 + jv * 104729 + seed)          # 洞緣頂點在布面內亂移，打散格子階梯
            p += sd * (hr_.uniform(-0.45, 0.45) * colw * h) - Z * (hr_.uniform(-0.45, 0.45) * length / nv)
        return p
    verts = {}
    bnd_cols = {}
    for ci, (s_, u) in enumerate(cols):
        if ci > 0 and cols[ci - 1][0] != s_:
            bnd_cols[ci] = (cols[ci - 1][0], s_)
    for ci, (s_, u) in enumerate(cols):
        for jv in range(nv + 1):
            v = jv / nv
            if ci in bnd_cols:
                sl, sr = bnd_cols[ci]
                if v > s_top[sr] + 1e-6:
                    verts[(ci, jv, "L")] = bm.verts.new(pos(u, v, sl, ci, jv))
                    verts[(ci, jv, "R")] = bm.verts.new(pos(u, v, sr, ci, jv))
                    continue
                vv = bm.verts.new((pos(u, v, sl, ci, jv) + pos(u, v, sr, ci, jv)) * 0.5)
                verts[(ci, jv, "L")] = verts[(ci, jv, "R")] = vv
            else:
                verts[(ci, jv, "L")] = verts[(ci, jv, "R")] = bm.verts.new(pos(u, v, s_, ci, jv))
    ul = [c[1] * W for c in cols]
    for ci in range(nC - 1):
        for jv in range(nv):
            if (ci, jv) in hs:
                continue
            a = verts[(ci, jv, "R")]; b = verts[(ci + 1, jv, "L")]; c = verts[(ci + 1, jv + 1, "L")]; d = verts[(ci, jv + 1, "R")]
            try:
                f = bm.faces.new((a, b, c, d))
            except ValueError:
                continue
            for l, (x, y) in zip(f.loops, ((ci, jv), (ci + 1, jv), (ci + 1, jv + 1), (ci, jv + 1))):
                l[uvl].uv = (ul[x], y / nv * length)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    loose = [vv for vv in bm.verts if not vv.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.normal_update()
    inside = [top(0.5) - nrm(0.5) * 0.3 - Z * length * k / 4 for k in range(5)]
    sg = 0.0
    for f in bm.faces:
        cc = f.calc_center_median()
        ref = min(inside, key=lambda q: (q - cc).length_squared)
        sg += f.normal.dot(cc - ref) * f.calc_area()
    if sg < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = B.add_mesh(name, bm, mat, w, sharp=60, texel=1.0)
    ob["cloth"] = 0.006 * h
    return ob


ZT = 0.566 * h
rf_pts = [V(0, -0.088 * h, ZT), V(0, -0.096 * h, 0.40 * h), V(0, -0.102 * h, 0.23 * h), V(0, -0.108 * h, 0.07 * h)]
rb_pts = [V(0, 0.080 * h, ZT), V(0, 0.096 * h, 0.40 * h), V(0, 0.108 * h, 0.24 * h), V(0, 0.115 * h, 0.08 * h)]
rf_names = chain_names("RobeF", 3); rb_names = chain_names("RobeB", 3)
rl_pts = [V(0.100 * h, 0.004 * h, ZT), V(0.150 * h, 0.010 * h, 0.35 * h), V(0.185 * h, 0.016 * h, 0.14 * h)]
rr_pts = [mir(p_) for p_ in rl_pts]
rl_names = chain_names("RobeL", 2); rr_names = chain_names("RobeR", 2)
wF = w_chain_pts("Hips", rf_names, rf_pts)
wB = w_chain_pts("Hips", rb_names, rb_pts)


def front_top(u):
    x = lerp(-0.062, 0.062, u) * h
    return V(x, -(0.050 + 0.030 + 0.006 * (1 - (2 * u - 1) ** 2)) * h, ZT)


rag_panel("TabardF", front_top, lambda u: V(0, -1, 0), (0.566 - 0.062) * h, "linen", wF, nv=24, flare=0.030, fold_n=2.6, fold_amp=0.015,
          holes=4, seed=21, width=0.124 * h, rag=0.08, slit=(0.66, 0.80), asym=0.10, strip=(0.03, 0.06))


def side_w(sx):
    return w_chain_pts("Hips", rl_names if sx > 0 else rr_names, rl_pts if sx > 0 else rr_pts)


for sx, nm in ((1, "TabardSideL"), (-1, "TabardSideR")):
    a0, a1 = (38, 140) if sx > 0 else (-140, -38)
    rag_panel(nm, lambda u, a0=a0, a1=a1: torso.pt(ZT, lerp(a0, a1, u), 0.026 * h),
              lambda u, a0=a0, a1=a1: torso.nrm(ZT, lerp(a0, a1, u)), (0.566 - 0.125) * h, "linen2", side_w(sx), nv=22, flare=0.31, side=Y, colw=0.012, strip=(0.022, 0.045),
              fold_n=3.0, fold_amp=0.013, holes=4, seed=30 + sx, asym=0.07 * sx, width=0.17 * h, rag=0.10, slit=(0.45, 0.78), spread=0.02 * h * sx)
rag_panel("TabardB", lambda u: torso.pt(ZT, lerp(128, 232, u), 0.022 * h), lambda u: torso.nrm(ZT, lerp(128, 232, u)), (0.566 - 0.080) * h,
          "linen", wB, nv=22, flare=0.12, fold_n=4.0, fold_amp=0.013, holes=5, seed=40, width=0.20 * h, rag=0.10, slit=(0.45, 0.78), colw=0.012,
          strip=(0.022, 0.045),
          asym=-0.06)

# ---------------------------------------------------------------- 背後門板盾（高 0.62 × 寬 0.31 × 厚 0.035；直板 7 片）
DW, DH, PT = 0.31 * h, 0.62 * h, 0.020 * h
R_door = Matrix.Rotation(math.radians(12), 3, "Y") @ Matrix.Rotation(math.radians(-5), 3, "X")
dex, dez, ddn = R_door @ X, R_door @ Z, R_door @ Y
DC = V(0.040 * h, 0.122 * h, 0.545 * h)


def DP(x, z, d=0.0):
    return DC + dex * x + dez * z + ddn * d


drnd = random.Random(5)
NPL = 7
GAP = 0.004 * h
pw = (DW - GAP * (NPL - 1)) / NPL
plank_x = [-DW / 2 + pw / 2 + q * (pw + GAP) for q in range(NPL)]
rot_bot = {1: 0.05, 5: 0.07, 6: 0.035}        # 下緣腐爛缺角
for q, x in enumerate(plank_x):
    top = DH / 2 - drnd.uniform(0.0, 0.006) * h
    bot = -DH / 2 + drnd.uniform(0.0, 0.008) * h
    rb = rot_bot.get(q, 0.0)
    jg = [drnd.uniform(0, 1) for _ in range(14)]

    def pfn(u, v, x=x, top=top, bot=bot, rb=rb, jg=jg, q=q):
        a = 2 * math.pi * u
        cx, cy = math.cos(a), math.sin(a)
        sx = math.copysign(abs(cx) ** (2 / 6), cx); sy = math.copysign(abs(cy) ** (2 / 6), cy)
        k = int(u * 12) % 12
        b = bot + (rb * h * (0.4 + 0.6 * jg[k]) if rb else 0.006 * h * jg[k])
        z = lerp(top, b, v)
        bow = 0.002 * h * math.sin(math.pi * v) * (1 if q % 2 else -1)
        return DP(x + sx * pw / 2 * (1 - 0.06 * smooth((v - 0.9) / 0.1)), z, sy * PT / 2 + bow)
    B.grid(f"Plank{q}", 12, 6, pfn, "wood", "Spine2", [DP(x, (top + bot) / 2 * (k / 3), 0) for k in (-2, 0, 2)], closed_u=True,
           cap0=True, cap1=True, texel=1.0, sharp=40)
# 背面 2 條橫撐（朝身體那面）
for q, zz in enumerate((0.18 * h, -0.17 * h)):
    c = DP(0, zz, -PT / 2 - 0.009 * h)
    B.tube(f"DoorBrace{q}", [c - dex * DW * 0.47, c + dex * DW * 0.47], [(0.030 * h, 0.009 * h)] * 2, 8, "woodback", "Spine2", flat=dez,
           exp=6, texel=1.0)
OUTZ = PT / 2 + 0.003 * h


def iron_band(name, pa, pb, wid=0.025 * h, n=2):
    pts = [pa.lerp(pb, i / n) for i in range(n + 1)]
    d = (pb - pa).normalized()
    return B.tube(name, pts, [(wid / 2, 0.003 * h)] * len(pts), 8, "doorIron", "Spine2", flat=d.cross(ddn).normalized(), exp=5)


def nails(name, pa, pb, step=0.035 * h, off=0.0062 * h):
    L = (pb - pa).length
    n = max(2, int(L / step) + 1)
    return B.rivets(name, [(pa.lerp(pb, i / (n - 1)) + ddn * off, ddn) for i in range(n)], "doorIron", "Spine2", r=0.004 * h)


fx0, fx1 = -DW / 2 + 0.0125 * h, DW / 2 - 0.0125 * h
fz0, fz1 = -DH / 2 + 0.0125 * h + 0.03 * h, DH / 2 - 0.0125 * h
frame = [(DP(fx0, fz1, OUTZ), DP(fx1, fz1, OUTZ)), (DP(fx0, fz0, OUTZ), DP(fx1, fz0, OUTZ)),
         (DP(fx0, fz0, OUTZ), DP(fx0, fz1, OUTZ)), (DP(fx1, fz0, OUTZ), DP(fx1, fz1, OUTZ))]
for q, (a, b) in enumerate(frame):
    iron_band(f"DoorFrame{q}", a, b)
    nails(f"DoorFrameNails{q}", a, b)
# 上橫帶＋Z 形斜撐＋下橫帶
for q, (a, b) in enumerate(((DP(fx0, 0.14 * h, OUTZ), DP(fx1, 0.14 * h, OUTZ)), (DP(fx0, -0.15 * h, OUTZ), DP(fx1, -0.15 * h, OUTZ)),
                            (DP(fx0 + 0.01 * h, -0.14 * h, OUTZ), DP(fx1 - 0.01 * h, 0.13 * h, OUTZ)))):
    iron_band(f"DoorStrap{q}", a, b, wid=0.022 * h)
    nails(f"DoorStrapNails{q}", a, b, step=0.045 * h)
# 右側 2 條長鉸鏈（長 0.15、末端矛形）＋鉸鏈筒
for q, zz in enumerate((0.22 * h, -0.21 * h)):
    a = DP(DW / 2 + 0.004 * h, zz, OUTZ + 0.002 * h); b = DP(DW / 2 - 0.15 * h, zz, OUTZ + 0.002 * h)
    B.tube(f"Hinge{q}", [a, a.lerp(b, 0.5), b.lerp(a, 0.12), b], [(0.017 * h, 0.0035 * h), (0.013 * h, 0.0035 * h), (0.016 * h, 0.0035 * h),
                                                                 (0.001 * h, 0.002 * h)], 8, "doorIron", "Spine2", flat=dez, exp=4)
    B.tube(f"HingeBarrel{q}", [DP(DW / 2 + 0.006 * h, zz - 0.022 * h, 0), DP(DW / 2 + 0.006 * h, zz + 0.022 * h, 0)], [0.007 * h] * 2, 10,
           "doorIron", "Spine2")
    nails(f"HingeNails{q}", a.lerp(b, 0.15), a.lerp(b, 0.8), step=0.04 * h, off=0.0085 * h)
# 門把（垂環，環徑 0.05）＋鎖片
rc = DP(-0.065 * h, 0.0, OUTZ)
B.ellipsoid("RingPlate", rc, (dex, dez, ddn), (0.014 * h, 0.016 * h, 0.004 * h), 12, 4, "doorIron", "Spine2", v0=0, v1=0.5)
ring = [rc + ddn * 0.007 * h + dex * 0.025 * h * math.sin(2 * math.pi * i / 16) - dez * (0.025 * h - 0.025 * h * math.cos(2 * math.pi * i / 16))
        for i in range(17)]
B.tube("DoorRing", ring, [0.0035 * h] * 17, 6, "doorIron", "Spine2", cap=False)
lc = DP(-0.03 * h, -0.045 * h, OUTZ)
B.tube("LockPlate", [lc - dez * 0.02 * h, lc + dez * 0.02 * h], [(0.012 * h, 0.002 * h)] * 2, 8, "doorIron", "Spine2", flat=dex, exp=6)
# 一階：只 1–2 道真實板縫透出細綠光（寬 ≤ 0.003）
for q, (gi, z0, z1) in enumerate(((2, -0.06, 0.07), (4, 0.06, 0.15))):
    x = (plank_x[gi] + plank_x[gi + 1]) / 2
    pts = [DP(x, lerp(z0, z1, i / 5) * h, PT * 0.05) for i in range(6)]
    B.tube(f"DoorCrack{q}", pts, [(0.0012 * h, PT * 0.36)] * 6, 4, "Glow_Rune", "Spine2", flat=dex)
# 門板下緣垂掛根鬚
for q, x in enumerate((-0.12, -0.05, 0.03, 0.09, 0.13)):
    p = DP(x * h, -DH / 2 + 0.02 * h, PT * 0.4)
    dangle(f"DoorRoot{q}", p, -dez + ddn * 0.25, drnd.uniform(0.05, 0.11) * h, drnd.uniform(0.004, 0.0055) * h, 70 + q, "Spine2", n=7)
for q in range(2):
    pts = [DP((-0.11 + 0.17 * q + 0.02 * math.sin(i * 0.9 + q)) * h, (-0.29 + i * 0.035) * h, OUTZ + 0.004 * h) for i in range(11)]
    B.tube(f"DoorVine{q}", pts, [0.004 * h * (1 - 0.6 * i / 10) for i in range(11)], 5, "bark", "Spine2", texel=1.0)

# ---------------------------------------------------------------- 長戟（全長 0.80：握點→尖 0.70，握點→尾 0.10）
gcR = mir(body.grip_c); ax = mir(body.hand_v); edge = mir(body.hand_a)
edge = (edge - ax * edge.dot(ax)).normalized()
side = ax.cross(edge)
BUTT, SOCK0, SOCK1, TIP = -0.10 * h, 0.45 * h, 0.56 * h, 0.70 * h
SR = 0.009 * h


def hp(s, e=0.0, sd=0.0):
    return gcR + ax * s + edge * e + side * sd


B.tube("Shaft", [hp(BUTT + 0.01 * h), hp(0.1 * h), hp(0.3 * h), hp(SOCK1 - 0.02 * h)], [SR * 0.95, SR, SR, SR * 0.98], 8, "shaft", "Weapon", texel=1.0)
B.tube("ButtCap", [hp(BUTT - 0.004 * h), hp(BUTT + 0.002 * h), hp(BUTT + 0.03 * h)], [0.004 * h, 0.0115 * h, 0.010 * h], 8, "band", "Weapon")
for q, s0 in enumerate((0.10, 0.22, 0.34)):
    B.tube(f"ShaftBand{q}", [hp(s0 * h - 0.008 * h), hp(s0 * h - 0.006 * h), hp(s0 * h + 0.006 * h), hp(s0 * h + 0.008 * h)],
           [0.0105 * h, 0.012 * h, 0.012 * h, 0.0105 * h], 8, "band", "Weapon")
B.tube("Socket", [hp(SOCK0 - 0.01 * h), hp(SOCK0 + 0.02 * h), hp(SOCK1)], [0.0105 * h, 0.012 * h, 0.011 * h], 8, "band", "Weapon")
for sg in (1, -1):        # 固定刃的兩條長條（各 0.08）
    B.tube(f"Langet{sg}", [hp(SOCK0 - 0.08 * h, 0, sg * SR), hp(SOCK0, 0, sg * SR * 1.05)], [(0.0045 * h, 0.0015 * h), (0.0055 * h, 0.0015 * h)],
           6, "band", "Weapon", flat=edge, exp=4)
    B.rivets(f"LangetRivets{sg}", [(hp(SOCK0 - f * h, 0, sg * (SR + 0.0015 * h)), side * sg) for f in (0.065, 0.025)], "band", "Weapon", r=0.0028 * h)
B.tube("Spike", [hp(SOCK1 - 0.01 * h), hp(SOCK1 + 0.01 * h), hp(SOCK1 + 0.07 * h), hp(TIP)],
       [(0.0105 * h, 0.0105 * h), (0.0125 * h, 0.0125 * h), (0.008 * h, 0.008 * h), (0.0004 * h, 0.0004 * h)], 4, "axe", "Weapon", flat=edge + side,
       sharp=20)
B.tube("SpikeGlow", [hp(TIP - 0.03 * h), hp(TIP - 0.0005 * h)], [(0.0036 * h, 0.0036 * h), (0.0006 * h, 0.0006 * h)], 4, "Glow_Weapon", "Weapon",
       flat=edge + side, cap=True)
NOTCH = [(0.22, 0.011, 0.030, 1.0), (0.41, 0.007, 0.022, 0.5), (0.60, 0.010, 0.028, 1.0), (0.79, 0.008, 0.020, 0.6)]   # (位置, 深, 寬, 形：1＝V、0.5＝U)
C0, C1 = 0.425 * h, 0.605 * h       # 套筒段 0.18；刃口兩角再往外伸 → 刃弦 0.24


def blade_io(c):
    """新月斧刃：內緣（靠桿）與外緣（刃口）距桿的距離（h）。中段 45% 鑄在套筒上，兩端是往桿方向彎回的尖角（上下角）。"""
    attach = smooth((c - 0.22) / 0.12) * smooth((0.78 - c) / 0.12)
    e_in = SR / h + 0.001 + (1 - attach) * (0.028 + 0.020 * abs(c - 0.5) * 2)
    e_out = SR / h + 0.030 + 0.070 * math.sin(math.pi * c) ** 0.7
    for nc, nd, nw, sh in NOTCH:
        e_out -= nd * max(0.0, 1 - abs(c - nc) / nw) ** sh
    if c < 0.10 or c > 0.90:
        t = smooth(min(c, 1 - c) / 0.10)
        e_in = lerp(e_out - 0.001, e_in, t)
    return e_in * h, e_out * h


def blade_fn(a, c):
    if a < 0.5:
        vv, sg = a * 2, 1
    else:
        vv, sg = 2 - a * 2, -1
    vv = (1 - math.cos(math.pi * vv)) / 2
    ei, eo = blade_io(c)
    e = lerp(ei, eo, vv)
    s = lerp(C0, C1, c) + 0.12 * h * vv ** 2 * (c - 0.5)
    th = lerp(0.006, 0.0020, vv ** 0.9) * h
    return hp(s, e, sg * th)


blade_ob = B.grid("AxeBlade", 10, 40, blade_fn, "axe", "Weapon", [hp(lerp(C0, C1, k / 4), 0.04 * h) for k in range(5)], closed_u=True, cap0=True, cap1=True,
       texel=1.0, sharp=25)
B.tube("Fluke", [hp(0.505 * h, -SR), hp(0.508 * h, -0.028 * h), hp(0.500 * h, -0.048 * h), hp(0.482 * h, -0.063 * h), hp(0.458 * h, -0.070 * h)],
       [(0.011 * h, 0.0032 * h), (0.009 * h, 0.0028 * h), (0.0065 * h, 0.0024 * h), (0.0035 * h, 0.0018 * h), (0.0005 * h, 0.0008 * h)], 6, "axe", "Weapon",
       flat=ax, sharp=15)
TIPP = hp(TIP)
_ew = blade_ob.data.attributes.new("edgew", "FLOAT", "POINT")
for v_, d_ in zip(blade_ob.data.vertices, _ew.data):
    rel = v_.co - gcR
    sc_ = rel.dot(ax); ec_ = rel.dot(edge)
    c_ = clamp((sc_ - C0) / (C1 - C0))
    ei, eo = blade_io(c_)
    d_.value = clamp((ec_ - ei) / max(eo - ei, 1e-4))

# ---------------------------------------------------------------- 一階細根鬚（25–40 條：纏手臂、腰、大腿、脛；從肩甲、袖口、長擺下緣、門板下緣垂下）
roots_n = 0
# 胸甲：右肩 → 左腰斜纏
cp = []
for i in range(19):
    s = i / 18
    zz = lerp(0.765, 0.600, s) * h
    ang = lerp(-118, 70, s) + 10 * math.sin(s * 9)
    cp.append(torso.pt(zz, ang, (CU_OFF + 0.007 + 0.007 * math.sin(math.pi * s)) * h + 0.002 * h * math.sin(s * 23)))
B.tube("RootChest", cp, [0.0058 * h * (1 - 0.45 * i / 18) * (1 + 0.5 * math.exp(-((i - 6) / 1.2) ** 2) + 0.4 * math.exp(-((i - 13) / 1.0) ** 2)) for i in range(19)], 6, "bark", w_zchain(["Spine", (0.66 * h, "Spine2")], 0.05 * h), texel=1.0)
roots_n += 1
dangle("RootChestBr", cp[9], V(0.3, -0.5, -1), 0.05 * h, 0.003 * h, 5, "Spine2", n=5)
roots_n += 1
F, S = body.farm, body.uarm


def vamb_r(t):
    v = clamp((t / body.fa_len - 0.06) / 0.78)
    return lerp(0.045, 0.0372, smooth(v)) * h


obs = [wrap("RootFarm", F, body.fa_len * 0.12, body.fa_len * 0.70, 2.2, 40, 0.0058 * h, lambda t, a: vamb_r(t) - F.row(t)[0], 3, "ForearmL"),
       wrap("RootUArm", S, body.ua_len * 0.45, body.ua_len * 0.90, 1.0, 200, 0.0055 * h, lambda t, a: 0.0465 * h - S.row(t)[0], 6, "UpperArmL", n=14),
       wrap("RootThigh", body.thigh, body.th_len * 0.18, body.th_len * 0.80, 1.4, 60, 0.006 * h,
            lambda t, a: 0.053 * h - body.thigh.row(t)[0], 8, "ThighL", n=20),
       wrap("RootShin", body.shin, body.sh_len * 0.22, body.sh_len * 0.88, 1.2, 200, 0.0055 * h,
            lambda t, a: 0.045 * h - body.shin.row(t)[0] - 0.008 * h * t / body.sh_len, 9, "ShinL", n=18)]
# 肩甲外下緣垂 3 條、袖口 2 條（長 0.05–0.12H、末端分叉；在 3/4 剪影外側看得到）
for q, (ang, ln, rr0) in enumerate(((45, 0.11, 0.0055), (95, 0.08, 0.005), (145, 0.12, 0.0055))):
    obs += dangle(f"RootPauld{q}", S.pt(0.062 * h, ang, 0.040 * h), S.nrm(0.062 * h, ang) * 0.5 - Z, ln * h, rr0 * h, 11 + q, "UpperArmL", n=8)
for q, (ang, ln) in enumerate(((100, 0.08), (200, 0.06))):
    obs += dangle(f"RootCuff{q}", F.pt(body.fa_len * 1.0, ang, 0.050 * h - F.row(body.fa_len)[0]), F.nrm(body.fa_len, ang) * 0.4 - Z, ln * h,
                  0.0045 * h, 13 + q, "ForearmL", n=7)
B.both(obs)
roots_n += 2 * 9
# 腰：纏在腰帶上＋垂下
B.tube("RootWaist", [torso.pt(lerp(0.592, 0.55, s / 24) * h + 0.01 * h * math.sin(s * 0.9), -100 + s * 13, 0.033 * h + 0.004 * h * math.sin(s * 1.3))
                     for s in range(25)], [0.0042 * h * (1 - 0.35 * s / 24) for s in range(25)], 5, "bark", {"Spine": 0.3, "Hips": 0.7}, texel=1.0)
roots_n += 1
for q, (ang, ln) in enumerate(((-60, 0.09), (35, 0.07), (150, 0.10))):
    dangle(f"RootBelt{q}", torso.pt(0.556 * h, ang, 0.036 * h), torso.nrm(0.556 * h, ang) * 0.3 - Z, ln * h, 0.004 * h, 40 + q,
           {"Hips": 1.0}, n=7)
    roots_n += 1
print("ROOTS_P1", roots_n + 5 + 2 + 1, flush=True)

# ---------------------------------------------------------------- 二階部件（§5）
def grow(name, p, d, length, r0, seed, w, mat="barkP2", n=10, bends=2.5, bend_amt=0.5, forks=2, segs=8, r1=0.0025, up=0.0):
    """彎曲 2–3 次、分叉 2–3 次、漸細的主根。"""
    rr = random.Random(seed)
    d = d.normalized()
    side_ = d.cross(Z).normalized() if abs(d.z) < 0.95 else X.copy()
    ph = rr.uniform(0, 6.28)
    pts = [p.copy()]; rad = [r0]
    for i in range(1, n + 1):
        s = i / n
        bend = side_ * bend_amt * math.sin(2 * math.pi * bends * s * 0.5 + ph) + Z * (up - 0.25 * s)
        dd = (d + bend * 0.6).normalized()
        pts.append(pts[-1] + dd * length / n)
        rad.append(max(r0 * (1 - s) ** 1.1, r1 * h))
    obs = [B.tube(name, pts, rad, segs, mat, w, texel=1.0)]
    for q in range(forks):
        k = int(n * (0.35 + 0.45 * (q + rr.uniform(0, 0.6)) / forks))
        k = min(k, n - 2)
        dd = (pts[k + 1] - pts[k]).normalized() + side_ * rr.choice((-1, 1)) * rr.uniform(0.6, 1.1) + Z * rr.uniform(-0.3, 0.5)
        _, _, o2 = grow(f"{name}b{q}", pts[k], dd, length * rr.uniform(0.32, 0.48), rad[k] * 0.62, seed * 7 + q + 1, w, mat,
                        max(5, n // 2), bends * 0.8, bend_amt * 1.2, 1 if q == 0 and forks > 1 else 0, max(5, segs - 2), r1, up)
        obs += o2
    return pts, rad, obs


p2 = []


def catmull(P, n):
    """Catmull-Rom 平滑曲線（端點重複），回傳 n 個點。"""
    Q = [P[0]] + list(P) + [P[-1]]
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(P) - 1)
        k = min(int(t), len(P) - 2); u = t - k
        p0, p1, p2_, p3 = Q[k], Q[k + 1], Q[k + 2], Q[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2_) * u + (2 * p0 - 5 * p1 + 4 * p2_ - p3) * u * u + (-p0 + 3 * p1 - 3 * p2_ + p3) * u * u * u))
    return out


def root_r(s, r0, tip=0.0025):
    """主根粗細：到 75% 仍保持粗（≥ 0.55·r0），最後 25% 收成 0.005H 細尖。"""
    if s < 0.75:
        return r0 * (1 - 0.55 * s)
    t = (s - 0.75) / 0.25
    return lerp(r0 * 0.5875, tip * h, t ** 0.55)


rrnd = random.Random(101)
# (基點 x, z, y, 終點 x, z, 側彎, 上拱)：從兩肩後上方（x＝±0.12–0.18）與門板中縫長出，扇形往上、往兩側；最高 ≤ 0.98H
RA = [(0.125, 0.835, 0.115, 0.30, 0.975, 0.05, 0.06), (0.150, 0.815, 0.118, 0.46, 0.90, -0.04, 0.05), (0.175, 0.795, 0.112, 0.53, 0.70, 0.05, 0.03),
      (0.160, 0.770, 0.120, 0.47, 0.56, -0.04, -0.02)]
roots_def = []
for sx in (1, -1):
    for q, (bx, bz, by, ex_, ez_, bend, arch) in enumerate(RA):
        roots_def.append((V(sx * bx * h, by * h, bz * h), V(sx * ex_ * h, (by + 0.05 + 0.03 * q) * h, ez_ * h), bend, arch, sx, q))
for k, (P0, P3, bend, arch, sx, q) in enumerate(roots_def):
    d = P3 - P0
    nrm_ = d.cross(Y).normalized()
    c1 = P0 + d * 0.30 + Z * arch * h + nrm_ * bend * h + Y * 0.03 * h
    c2 = P0 + d * 0.62 - Z * arch * 0.6 * h - nrm_ * bend * 0.9 * h + Y * 0.05 * h
    c3 = P0 + d * 0.85 + Z * arch * 0.5 * h + nrm_ * bend * 0.5 * h + Y * 0.06 * h
    pts = catmull([P0 - Y * 0.01 * h, c1, c2, c3, P3], 41)
    zmax = max(p_.z for p_ in pts)
    if zmax > 0.975 * h:                 # 整條往下壓（不要用夾值把尖端壓扁）
        pts = [V(p_.x, p_.y, P0.z + (p_.z - P0.z) * (0.975 * h - P0.z) / (zmax - P0.z)) for p_ in pts]
    r0 = (0.029 - 0.002 * q) * h
    knots = [rrnd.uniform(0.12, 0.3), rrnd.uniform(0.35, 0.55), rrnd.uniform(0.58, 0.72)] + ([rrnd.uniform(0.2, 0.65)] if k % 2 else [])
    rad = [root_r(i / 40, r0) * (1 + 0.06 * math.sin(i * 0.9 + k) + sum(0.22 * math.exp(-((i / 40 - kk) / 0.025) ** 2) for kk in knots))
           for i in range(41)]
    p2.append(B.tube(f"RootArm{k}", pts, rad, 8, "barkP2", "Spine2", texel=1.0))
    # 中段分叉 1 條（彎曲）
    i = int(40 * rrnd.uniform(0.45, 0.65))
    t0 = (pts[i + 1] - pts[i]).normalized()
    side_ = t0.cross(Y).normalized() * rrnd.choice((-1, 1))
    L = (P3 - P0).length * rrnd.uniform(0.32, 0.42)
    bp = catmull([pts[i], pts[i] + (t0 * 0.6 + side_ * 0.6 + Z * 0.15).normalized() * L * 0.45,
                  pts[i] + (t0 * 0.9 + side_ * 0.3 - Z * 0.1).normalized() * L], 11)
    rb = rad[i] * 0.55
    p2.append(B.tube(f"RootArm{k}b", bp, [lerp(rb, 0.0022 * h, (j / 10) ** 0.8) for j in range(11)], 6, "barkP2", "Spine2", texel=1.0))
    # 末端碎成 2–3 根細枝（直徑 ≤ 0.01H）
    for b in range(2 + (k % 2)):
        i = 33 + b * 2
        t0 = (pts[min(i + 1, 40)] - pts[i]).normalized()
        sd_ = t0.cross(Z if abs(t0.z) < 0.9 else X).normalized()
        dd = (t0 + sd_ * (0.9 if b % 2 else -0.9) + Z * rrnd.uniform(-0.4, 0.4)).normalized()
        tw = [pts[i]]
        for _jj in range(4):
            dd = (dd + V(rrnd.uniform(-0.4, 0.4), rrnd.uniform(-0.4, 0.4), rrnd.uniform(-0.4, 0.2))).normalized()
            tw.append(tw[-1] + dd * 0.022 * h)
        p2.append(B.tube(f"RootArm{k}t{b}", tw, [0.0045 * h, 0.0035 * h, 0.0025 * h, 0.0015 * h, 0.0005 * h], 5, "barkP2", "Spine2", texel=1.0))
    p2.append(B.ellipsoid(f"RootBase{k}", P0, (X, Y, Z), (r0 * 1.5, r0 * 1.3, r0 * 1.4), 8, 5, "barkP2", "Spine2", texel=1.0))
    if q in (0, 1, 2) and k % 2 == 0 or q == 3:      # 掛在根上的苔條
        mp = pts[int(14 + q * 4)]
        mpts = [mp - Z * (0.016 * h * i_) + X * 0.002 * h * math.sin(i_) for i_ in range(6)]
        p2.append(B.tube(f"RootMoss{k}", mpts, [0.0045 * h * (1 - i_ / 6) + 0.0008 * h for i_ in range(6)], 5, "mossS", "Spine2", texel=1.0))
for k, (P0, P3, bend, arch, sx, q) in enumerate(roots_def):     # 根部縫隙弱光（根部 0.1H 內）
    if q < 3:
        dd = (P3 - P0).normalized()
        p2.append(B.ellipsoid(f"RootGlow{k}", P0 + dd * 0.02 * h - Y * 0.004 * h, (X, Y, Z), (0.010 * h, 0.010 * h, 0.010 * h), 8, 4,
                              "P2_Glow_Root", "Spine2"))
VL.tag_p2(p2, "RootArms", "Spine2", DP(0, 0.12 * h, PT / 2))


def thorns(tag, bone, items):
    obs = []
    for q, (p, d, ln) in enumerate(items):
        d = d.normalized()
        bend = (d.cross(Z) if abs(d.z) < 0.9 else X).normalized()
        out_ = (d + V(p.x, 0, 0).normalized() * 0.3 if abs(p.x) > 1e-4 else d).normalized()
        pts = [p - d * 0.006 * h, p + d * ln * 0.35, p + d * ln * 0.7 + out_ * ln * 0.08, p + d * ln + out_ * ln * 0.2]
        obs.append(B.tube(f"{tag}{q}", pts, [0.0065 * h, 0.0048 * h, 0.0026 * h, 0.0004 * h], 6, "barkP2", bone, texel=1.0))
        obs.append(B.ellipsoid(f"{tag}K{q}", p, (X, Y, Z), (0.008 * h, 0.008 * h, 0.008 * h), 8, 5, "barkP2", bone))
    return obs


uaL = j["UpperArmL"]
sh_items = [(uaL + H_(0.012, -0.012, 0.050), V(0.35, -0.2, 1.0), 0.075 * h), (uaL + H_(0.050, 0.010, 0.030), V(1.0, 0.3, 0.5), 0.06 * h),
            (uaL + H_(0.006, 0.040, 0.040), V(0.0, 0.8, 0.8), 0.055 * h)]
fa_items = [(F.pt(body.fa_len * 0.35, 85, 0.0425 * h - F.row(body.fa_len * 0.35)[0]), F.nrm(body.fa_len * 0.35, 85) + body.fd * 0.3, 0.06 * h),
            (F.pt(body.fa_len * 0.58, 135, 0.0425 * h - F.row(body.fa_len * 0.58)[0]), F.nrm(body.fa_len * 0.58, 135) + body.fd * 0.3, 0.05 * h)]
kn = j["ShinL"]
kn_items = [(kn + H_(0.010, -0.040, 0.012), V(0.15, -1.0, 0.4), 0.065 * h), (kn + H_(0.038, -0.016, -0.004), V(1.0, -0.4, 0.2), 0.05 * h)]
S2 = body.shin
sn_items = [(S2.pt(body.sh_len * 0.45, 20, 0.044 * h - S2.row(body.sh_len * 0.45)[0]), S2.nrm(body.sh_len * 0.45, 20) + Z * 0.3, 0.05 * h),
            (S2.pt(body.sh_len * 0.62, 100, 0.040 * h - S2.row(body.sh_len * 0.62)[0]), S2.nrm(body.sh_len * 0.62, 100) + Z * 0.3, 0.045 * h)]
for sgn, sfx in ((1, "L"), (-1, "R")):
    def mi(items):
        return items if sgn > 0 else [(mir(p), mir(d), l) for p, d, l in items]
    VL.tag_p2(thorns("ShSp" + sfx, "UpperArm" + sfx, mi(sh_items)), "RootSpikes_Shoulder" + sfx, "UpperArm" + sfx, mi(sh_items)[0][0])
    VL.tag_p2(thorns("FaSp" + sfx, "Forearm" + sfx, mi(fa_items)), "RootSpikes_Forearm" + sfx, "Forearm" + sfx, mi(fa_items)[0][0])
    VL.tag_p2(thorns("KnSp" + sfx, "Shin" + sfx, mi(kn_items)), "RootSpikes_Knee" + sfx, "Shin" + sfx, mi(kn_items)[0][0])
    VL.tag_p2(thorns("SnSp" + sfx, "Shin" + sfx, mi(sn_items)), "RootSpikes_Shin" + sfx, "Shin" + sfx, mi(sn_items)[0][0])

# P2_Heart：胸甲裂口（0.12×0.10，撕開的鐵）＋解剖心臟形綠核（寬 0.07）＋ 6–10 條放射根狀裂紋
HZ = 0.712 * h
hcn = torso.pt(HZ, 0, CU_OFF * h + 0.006 * h)
hp2 = []
hp2.append(B.ellipsoid("HeartHole", hcn + Y * 0.010 * h, (X, Z, -Y), (0.054 * h, 0.046 * h, 0.018 * h), 16, 6, "void", "Spine2", v0=0, v1=0.5))
prnd = random.Random(77)
for q in range(12):           # 撕開往外翻的鐵瓣（明顯外翻、長短不一）
    a = 2 * math.pi * q / 12 + prnd.uniform(-0.12, 0.12)
    r0x, r0z = 0.056 * h, 0.048 * h
    base = hcn + X * math.cos(a) * r0x + Z * math.sin(a) * r0z - Y * 0.002 * h
    outd = (X * math.cos(a) + Z * math.sin(a))
    ln = prnd.uniform(0.018, 0.034) * h
    mid = base - outd * ln * 0.15 - Y * ln * 0.55
    tipp = base + outd * ln * 0.25 - Y * ln * 0.95
    e1 = outd.cross(Y).normalized()
    hp2.append(B.tube(f"HeartPetal{q}", [base + outd * 0.006 * h, mid, tipp],
                      [(0.013 * h, 0.0028 * h), (0.009 * h, 0.0022 * h), (0.0012 * h, 0.001 * h)], 4, "plate", "Spine2", flat=e1, exp=3))
cc = hcn + Y * 0.004 * h
# 解剖心形：外殼＝半透明綠晶（P2_Glow_HeartShell，有光澤明暗），內核＝亮綠（P2_Glow_Heart）
SH = "P2_Glow_HeartShell"
hp2.append(B.ellipsoid("HeartVentricle", cc + V(0.004 * h, 0, -0.006 * h), (X, Y, Z), (0.030 * h, 0.021 * h, 0.034 * h), 14, 9, SH, "Spine2",
                       dent=lambda d, u, v: 1 - 0.12 * smooth(d.z * 2) * math.exp(-(d.x / 0.3) ** 2)))
hp2.append(B.ellipsoid("HeartAtriumR", cc + V(-0.016 * h, -0.002 * h, 0.019 * h), (X, Y, Z), (0.016 * h, 0.014 * h, 0.014 * h), 10, 6, SH, "Spine2"))
hp2.append(B.ellipsoid("HeartAtriumL", cc + V(0.020 * h, 0.002 * h, 0.022 * h), (X, Y, Z), (0.012 * h, 0.011 * h, 0.011 * h), 10, 6, SH, "Spine2"))
hp2.append(B.ellipsoid("HeartApex", cc + V(0.012 * h, -0.002 * h, -0.032 * h), (X, Y, Z), (0.013 * h, 0.012 * h, 0.015 * h), 10, 6, SH, "Spine2"))
hp2.append(B.ellipsoid("HeartCore", cc + V(0.002 * h, 0.002 * h, -0.004 * h), (X, Y, Z), (0.017 * h, 0.011 * h, 0.020 * h), 10, 6,
                       "P2_Glow_Heart", "Spine2"))
arch = [cc + V(0.004 * h, 0, 0.02 * h), cc + V(0.006 * h, -0.002 * h, 0.034 * h), cc + V(-0.004 * h, -0.004 * h, 0.044 * h),
        cc + V(-0.016 * h, -0.003 * h, 0.040 * h), cc + V(-0.022 * h, -0.002 * h, 0.030 * h)]
hp2.append(B.tube("HeartAorta", arch, [0.008 * h, 0.0075 * h, 0.007 * h, 0.006 * h, 0.0055 * h], 8, SH, "Spine2"))
for q, dv in enumerate((V(0.01, 0, 1), V(0.6, 0, 0.8), V(-0.5, 0, 0.9))):
    p0 = arch[2] if q == 0 else arch[1]
    hp2.append(B.tube(f"HeartVessel{q}", [p0, p0 + dv.normalized() * 0.012 * h], [0.004 * h, 0.003 * h], 6, SH, "Spine2"))
# 放射根狀裂紋：貼胸甲表面、寬 ≤ 0.004H、長 0.04–0.08H、會分叉；不往正上方（護喉）長
for q, a in enumerate((-170, -138, -105, -72, -40, -8, 22, 150, 178)):
    a += prnd.uniform(-8, 8)
    L = prnd.uniform(0.04, 0.08) * h
    pts = []
    for i in range(8):
        rr_ = 0.052 * h + L * i / 7
        ang = math.radians(a + 9 * math.sin(i * 0.7 + q) * (i / 7))
        zz = HZ + math.sin(ang) * rr_
        ad = math.degrees(math.cos(ang) * rr_ / (0.105 * h))
        pts.append(torso.pt(zz, ad, cu_off(0, 0.5, ad, zz) + 0.0010 * h))
    hp2.append(B.tube(f"HeartCrack{q}", pts, [0.0019 * h * (1 - i / 9) + 0.0004 * h for i in range(8)], 4, "P2_Glow_Heart", "Spine2"))
    k = 4
    a2 = a + prnd.choice((-1, 1)) * 28
    bp = [pts[k]]
    for i in range(1, 5):
        rr_ = 0.052 * h + L * (k / 7) + L * 0.12 * i
        ang = math.radians(a2)
        zz = HZ + math.sin(ang) * rr_
        ad = math.degrees(math.cos(ang) * rr_ / (0.105 * h))
        bp.append(torso.pt(zz, ad, cu_off(0, 0.5, ad, zz) + 0.0010 * h))
    hp2.append(B.tube(f"HeartCrackB{q}", bp, [0.0012 * h, 0.001 * h, 0.0008 * h, 0.0006 * h, 0.0003 * h], 4, "P2_Glow_Heart", "Spine2"))
VL.tag_p2(hp2, "Heart", "Spine2", hcn)

# P2_HalberdRoots：3–4 條、直徑 0.008–0.012、纏 4–6 圈，幾條越過斧刃；戟尖亮起
wr = []
for q in range(4):
    ph = q * 1.57
    turns = 4.5 + q * 0.4
    s0, s1 = 0.20 + 0.03 * q, 0.60 - 0.02 * q
    pts = []
    for i in range(25):
        s = lerp(s0, s1, i / 24)
        a = ph + 2 * math.pi * turns * i / 24
        rr_ = SR + 0.006 * h + (0.012 * h * math.sin(math.pi * (s - 0.40 * h / h) * 4) if (q == 1 and s > 0.42) else 0)
        pts.append(hp(s * h, math.cos(a) * rr_, math.sin(a) * rr_))
    wr.append(B.tube(f"HRoot{q}", pts, [(0.0045 + 0.0015 * math.sin(i * 0.5 + q)) * h for i in range(25)], 5, "barkP2", "Weapon", texel=1.0))
for q, (c, sg) in enumerate(((0.35, 1), (0.62, -1))):      # 越過斧刃
    s = lerp(C0, C1, c)
    ei, eo = blade_io(c)
    pts = [hp(s - 0.02 * h, SR, sg * 0.008 * h), hp(s, (ei + eo) * 0.5, sg * 0.007 * h), hp(s + 0.015 * h, eo * 0.95, sg * 0.004 * h),
           hp(s + 0.02 * h, eo * 0.9, -sg * 0.004 * h), hp(s + 0.01 * h, (ei + eo) * 0.5, -sg * 0.007 * h)]
    wr.append(B.tube(f"HRootBlade{q}", pts, [0.005 * h, 0.0045 * h, 0.004 * h, 0.0035 * h, 0.003 * h], 6, "barkP2", "Weapon", texel=1.0))
wr.append(B.tube("HGlowTip", [hp(SOCK1 + 0.02 * h), hp(SOCK1 + 0.07 * h), hp(TIP - 0.01 * h), hp(TIP + 0.012 * h)],
                 [(0.0135 * h, 0.0135 * h), (0.0095 * h, 0.0095 * h), (0.0035 * h, 0.0035 * h), (0.0005 * h, 0.0005 * h)], 4, "P2_Glow_Weapon",
                 "Weapon", flat=edge + side))
for q, c in enumerate((0.25, 0.5, 0.75)):          # 斧刃縫隙帶綠光
    s = lerp(C0, C1, c); ei, eo = blade_io(c)
    wr.append(B.tube(f"HBladeGlow{q}", [hp(s, ei + 0.004 * h, 0), hp(s + 0.012 * h, (ei + eo) * 0.5, 0)], [(0.0018 * h, 0.0065 * h)] * 2, 4,
                     "P2_Glow_Weapon", "Weapon", flat=side))
VL.tag_p2(wr, "HalberdRoots", "Weapon", hp(SOCK1))

# ---------------------------------------------------------------- 骨架、烘焙
tipd = ax.normalized()
arm = build_armature("BossSentinel", body, weapon=(gcR, gcR + ax * 0.12 * h),
                     chains=[("RobeF", "Hips", rf_pts), ("RobeB", "Hips", rb_pts), ("RobeL", "Hips", rl_pts), ("RobeR", "Hips", rr_pts)],
                     extra=[("Tip_Weapon", "Weapon", TIPP, TIPP + tipd * 0.05 * h)])
glows = VL.pull_glow(B)
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts) + VL.tri_count(glows)
print("PARTS", len(B.parts), "TRIS(pre-polish)", tri, flush=True)
for o in sorted(B.parts, key=lambda o: -len(o.data.polygons))[:40]:
    print("  PARTTRI", o.name, sum(len(p.vertices) - 2 for p in o.data.polygons), flush=True)
DETAIL_OF = {"plate": "metal", "pauld": "metal", "arm": "metal", "glove": "metal", "legp": "metal", "knee": "metal", "greave": "metal",
             "boot": "metal", "hat": "metal", "crown": "metal", "gold": "metal", "buckle": "metal", "doorIron": "metal", "axe": "metal",
             "band": "metal", "bark": "bark", "barkP2": "bark", "belt": "leather", "strap": "leather", "linen": "cloth", "linen2": "cloth",
             "burlap": "cloth", "gambeson": "cloth", "wood": "wood", "woodback": "wood", "shaft": "wood"}.get
mesh = BK.assemble(B, MODEL, size=(TEXS, TEXS), bake=not (QUICK or NOBAKE), quick=QUICK, detail_of=DETAIL_OF, U=U * 0.8)
VL.join_into(mesh, glows)
p2objs = VL.split_p2(mesh, arm)
BK.bind(mesh, arm)
print("TRIS_FINAL", BK.tri_count(mesh) + VL.tri_count(p2objs), "main", BK.tri_count(mesh), "p2", VL.tri_count(p2objs), flush=True)

# ---------------------------------------------------------------- 動作
from v3_sentinel_anim import Rig, W, HW
legsC = [("ThighL", "ShinL", 0.055 * h), ("ThighR", "ShinR", 0.055 * h), ("ShinL", "FootL", 0.048 * h), ("ShinR", "FootR", 0.048 * h)]
GZ = 0.066 * h      # 布料鏈關節離地下限：至少要大於布片半寬（鏈骨倒向前方時布寬會轉成垂直）
GZS = 0.130 * h     # 側片（寬 0.17H）
GZB = 0.118 * h
rig = Rig(arm, body, chains=[
    dict(names=rf_names, anchor="Hips", pts=rf_pts, stiff=0.05, damp=0.92, colliders=legsC, out=(0, -1, 0), ground=GZ),
    dict(names=rb_names, anchor="Hips", pts=rb_pts, stiff=0.045, damp=0.93, colliders=legsC + [("Hips", "Spine", 0.09 * h)], out=(0, 1, 0), ground=GZB, yaw=True, waxis=(1, 0, 0)),
    dict(names=rl_names, anchor="Hips", pts=rl_pts, stiff=0.05, damp=0.92, colliders=legsC, out=(1, 0, 0), ground=GZS, planar=False, lock=1, yaw=True),
    dict(names=rr_names, anchor="Hips", pts=rr_pts, stiff=0.05, damp=0.92, colliders=legsC, out=(-1, 0, 0), ground=GZS, planar=False, lock=1, yaw=True)])
rig.tip_ground = 0.025 * h
rig.tip_len = TIP
rig.lie_dz = 0.0
import v3_sentinel_poses as PO
PO.setup(rig, body, h)
import v3_sentinel_actions as ACT
if not NOANIM:
    ACT.build(rig, PO.weapon, primary="sweep", slow=1.0, only=ONLY, wide=1.0, phase=PO.phase)

if not ONLY:
    VL.export_glb(arm, [mesh] + p2objs, OUT_GLB)
    if not NOANIM:
        BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
if not NORENDER:
    import v3_sentinel_render as RD
    RD.render_all(arm, mesh, p2objs, h, TILES, anim=not NOANIM, only=ONLY)
print("DONE", MODEL, flush=True)
