"""建模 B（v2）：噬語魔王 devourer 重建（最終 Boss，三階）。依 art/v2/design.md §2.5、art_guide.md §5、art/reference/v2/devourer_p1/p2/p3.jpg。
左右不對稱多重彎角＋骷髏面＋舊金浮雕板甲＋寬大肩甲＋鋸齒巨劍（拄地）＋往下擴散的書頁披風；左手掌心紅色原創符紋。
二階（P2_*）：書頁紙翼（頁緣燃紅）、胸口豎直獠牙巨口、甲冑浮雕轉紅（Script）、劍身裂紋全亮。
三階（P3_*）：頭頂破碎紅黑光環、斷角殘根、下半身墨潮、甲片剝落裂肉、劍外符字環＋劍長 +20%、眼窩紅焰。
另有非型態節點 HornLongR（右側最長角，剛體掛在 Head）：三階時應由動畫端隱藏（P3_HornBroken 是它的斷角殘根）。
用法：blender --background --factory-startup --python v2b_devourer.py -- [--quick] [--noanim] [--only A,B] [--noviews]
"""
import bpy, bmesh, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree
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
MODEL = "boss_devourer"
BAKEKEY = "v2b_devourer"
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v2b_devourer.blend")
TILES = os.path.join(HERE, "preview", "_tiles", "v2b_devourer")
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

reset_scene()
body = Body(H=2.6, bulk=1.22, wf=1.15, head=0.33, hz=0.50, neck=0.045, limb=1.05, arm_a=55)
U = body.U; R = body.R; RL = body.RL; j = body.j; hs = body.head; H = body.H
B = Builder()
rnd = random.Random(5)

# ---------------------------------------------------------------- 材質
D = BK.define_mat
D("gold", "A", tex="Metal024", size=0.55, U=U, val=1.25, sat=0.0, tint=(0.80, 0.58, 0.26), rough=0.40, metal=1.0, wear=1.0,
  wear_col=(1.0, 0.80, 0.42), dirt=1.0, dirt_col=(0.018, 0.013, 0.01), bump=0.5, stain=0.55, stain_col=(0.012, 0.010, 0.012), ao_shade=0.7)
D("steel", "A", tex="Metal024", size=0.6, U=U, val=0.38, sat=0.4, tint=(0.75, 0.74, 0.78), rust=0.2, rust_tint=(0.25, 0.17, 0.12),
  wear=1.0, wear_col=(0.48, 0.48, 0.5), dirt=0.8, bump=0.6)
D("chainD", "A", tex="Chainmail004", size=0.24, U=U, tint=(0.25, 0.24, 0.26), metal=0.8, rough=0.55, rust=0.2, rust_tint=(0.2, 0.14, 0.11),
  dirt=1.0, bump=1.0, bump_dist=0.006, ao_shade=0.75)
D("void", "A", color=(0.004, 0.003, 0.003), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
D("flesh", "A", tex="Leather026", size=0.2, U=U, val=0.9, sat=0.6, tint=(0.20, 0.07, 0.05), rough=0.55, metal=0.0, dirt=1.0, bump=1.0)
D("bone", "B", color=(0.60, 0.54, 0.42), rough=0.55, metal=0.0, dirt=1.0, wear=0.6, wear_col=(0.80, 0.75, 0.62),
  dirt_col=(0.08, 0.06, 0.04), bump=0.5, ao_shade=0.7)
D("hornD", "B", color=(0.10, 0.085, 0.075), rough=0.45, metal=0.0, dirt=0.6, bump=0.5,
  wear=0.6, wear_col=(0.35, 0.32, 0.28))
D("paper", "B", tex="boss/Paper006", size=0.35, U=U, val=1.25, sat=0.8, tint=(1.0, 0.90, 0.66), rough=0.85, metal=0.0, dirt=0.4,
  dirt_col=(0.25, 0.16, 0.07), bump=0.3, stain=0.45, stain_col=(0.30, 0.18, 0.07), mud=(0.0, 0.5, 0.6), mud_col=(0.14, 0.09, 0.05), ao_shade=0.75)
D("linen", "B", tex="Fabric030", size=0.22, U=U, val=2.6, sat=0.35, tint=(0.75, 0.68, 0.56), rough=0.92, metal=0.0, dirt=0.6, bump=0.9,
  stain=0.25, stain_col=(0.02, 0.018, 0.02), mud=(0.0, 0.6, 0.7), mud_col=(0.06, 0.05, 0.045))
D("capeCloth", "B", tex="Fabric030", size=0.25, U=U, tint=(0.14, 0.11, 0.09), rough=0.95, metal=0.0, dirt=0.6, bump=0.8)
D("blade", "B", tex="Metal024", size=0.7, U=U, val=0.85, sat=0.3, rust=0.15, rust_tint=(0.25, 0.16, 0.12), wear=1.0,
  wear_col=(0.85, 0.85, 0.88), dirt=0.6, bump=0.6, seed=4.0)
D("leather", "B", tex="Leather026", size=0.30, U=U, val=1.8, tint=(0.24, 0.15, 0.10), rough=0.72, metal=0.0, dirt=0.9, wear=0.5,
  wear_col=(0.32, 0.23, 0.16), bump=0.6)
D("steelB", "B", tex="Metal024", size=0.6, U=U, val=0.38, sat=0.4, tint=(0.75, 0.74, 0.78), rust=0.2, rust_tint=(0.25, 0.17, 0.12),
  wear=1.0, wear_col=(0.48, 0.48, 0.5), dirt=0.8, bump=0.6, seed=7.0)
RED = (1.0, 0.042, 0.023)            # #ff3a2a（線性）
GOLDE = (1.0, 0.62, 0.18)
VH.define_glow("g_eye", RED, 3.0, final="Glow_Eye")
VH.define_glow("g_rune", RED, 1.6, final="Glow_Rune")
VH.define_glow("g_weapon", RED, 0.9, final="Glow_Weapon")
VH.define_glow("p2_script", RED, 1.8, final="P2_Glow_Script")
VH.define_glow("p2_maw", RED, 3.0, final="P2_Glow_Maw", base=(0.15, 0.0, 0.0))
VH.define_glow("p2_page", (1.0, 0.18, 0.04), 2.2, final="P2_Glow_PageEdge")
VH.define_glow("p2_blade", RED, 2.2, final="P2_Glow_Blade")
VH.define_glow("p3_halo", RED, 3.2, final="P3_Glow_Halo")
VH.define_glow("p3_cracks", RED, 2.4, final="P3_Glow_Cracks")
VH.define_glow("p3_glyph", RED, 2.8, final="P3_Glow_Glyph")
VH.define_glow("p3_glyphG", GOLDE, 2.4, final="P3_Glow_GlyphGold")
VH.define_glow("p3_eyes", (1.0, 0.10, 0.03), 3.5, final="P3_Glow_Eyes")
VH.define_ink("p3_ink", color=(0.008, 0.006, 0.008), alpha=0.93, emit=(0.5, 0.03, 0.02), emit_strength=0.10, final="P3_Ink")


# ---------------------------------------------------------------- 小工具
def bvh_of(obs):
    bm = bmesh.new()
    for o in obs:
        bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    return BVHTree.FromBMesh(bm), bm


def hit_axis(tree, ang, z, cx=0.0, cy=0.0, far=3.0):
    """從外往 (cx,cy,z) 軸心射線，回傳 (位置, 法線)。ang：0＝正前（-Y），正值往 +X。"""
    a = math.radians(ang)
    d = V(math.sin(a), -math.cos(a), 0)
    o = V(cx, cy, z) + d * far
    loc, nrm, idx, dist = tree.ray_cast(o, -d)
    if loc is None:
        return V(cx, cy, z) + d * 0.2, d
    if nrm.dot(d) < 0:
        nrm = -nrm
    return loc, nrm


def path_on(tree, pts, lift, cx=0.0, cy=0.0):
    out = []
    for ang, z in pts:
        loc, n = hit_axis(tree, ang, z, cx, cy)
        out.append((loc + n * lift, n))
    return out


def resample(pts, n):
    L = [0.0]
    for k in range(1, len(pts)):
        L.append(L[-1] + (pts[k] - pts[k - 1]).length)
    out = []
    for q in range(n):
        s = L[-1] * q / (n - 1)
        k = 0
        while k < len(L) - 2 and L[k + 1] < s:
            k += 1
        f = (s - L[k]) / max(L[k + 1] - L[k], 1e-9)
        out.append(pts[k].lerp(pts[k + 1], f))
    return out


def catmull(pts, n):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for q in range(n):
        x = q / (n - 1) * (len(pts) - 1)
        k = min(int(x), len(pts) - 2); t = x - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        t2 = t * t; t3 = t2 * t
        out.append(p0 * (-0.5 * t3 + t2 - 0.5 * t) + p1 * (1.5 * t3 - 2.5 * t2 + 1) + p2 * (-1.5 * t3 + 2 * t2 + 0.5 * t) + p3 * (0.5 * t3 - 0.5 * t2))
    return out


def horn(name, pts, r0, w="Head", split=0.55, n=10, segs=8, mk=None):
    """角：沿曲線、漸細；根部骨色→尖端黑。"""
    P = catmull([V(*p) for p in pts], n)
    rad = [r0 * U * (1 - 0.93 * (k / (n - 1)) ** 0.9) for k in range(n)]
    ks = max(2, int(round(split * (n - 1))))
    a = B.tube(name + "Base", P[:ks + 1], rad[:ks + 1], segs, "bone", w, cap=True)
    b = B.tube(name + "Tip", P[ks:], rad[ks:], segs, "hornD", w, cap=True)
    obs = [a, b]
    # 環紋
    if mk:
        VH.mark(obs, mk)
    return obs, P, rad


def wisp(name, base, d, length, side, mat, w, width=0.018, curl=0.25, n=7, seed=0, up=0.0):
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


def page(name, c, xd, yd, w_, h_, w, curl=0.0, mat="paper", nu=2, nv=2):
    """一張書頁（中心 c、寬向 xd、往下 yd）。"""
    xd = xd.normalized(); yd = (yd - xd * yd.dot(xd)).normalized(); nd = xd.cross(yd)

    def fn(u, v):
        return c + xd * ((u - 0.5) * w_) + yd * ((v - 0.5) * h_) + nd * (curl * (math.sin(math.pi * u) - 0.5) * w_ * 0.25 + curl * 0.3 * (v - 0.5) ** 2 * h_)
    return B.grid(name, nu, nv, fn, mat, w, c - nd * 0.3, sharp=80, texel=1.0)


def cone(name, base, d, ln, r0, mat, w, segs=6):
    d = d.normalized()
    return B.tube(name, [base - d * r0 * 0.3, base + d * ln * 0.55, base + d * ln], [r0, r0 * 0.45, 0.0008 * U], segs, mat, w, sharp=30)


GLYPHS = [[((0.0, 0.0), (0.0, 1.0)), ((0.0, 0.6), (0.6, 0.95))], [((0.0, 1.0), (0.5, 0.0)), ((0.5, 0.0), (0.8, 0.7))],
          [((0.1, 0.0), (0.1, 0.9)), ((0.1, 0.9), (0.7, 0.6)), ((0.4, 0.3), (0.8, 0.1))], [((0.0, 0.5), (0.8, 0.5)), ((0.4, 0.0), (0.3, 1.0))],
          [((0.0, 0.0), (0.4, 1.0)), ((0.4, 1.0), (0.8, 0.0))], [((0.2, 0.0), (0.2, 1.0)), ((0.6, 0.2), (0.6, 0.8))],
          [((0.0, 0.2), (0.8, 0.2)), ((0.0, 0.8), (0.8, 0.8)), ((0.4, 0.2), (0.4, 0.8))], [((0.1, 1.0), (0.1, 0.2)), ((0.1, 0.2), (0.5, 0.0)), ((0.5, 0.0), (0.8, 0.4))]]


def glyph(prefix, c, xd, yd, size, mat, w, gi, width=0.0055, lift=None):
    xd = xd.normalized(); yd = yd.normalized(); nd = xd.cross(yd)
    obs = []
    for si, (p0, p1) in enumerate(GLYPHS[gi % len(GLYPHS)]):
        pa = c + xd * ((p0[0] - 0.4) * size) + yd * ((p0[1] - 0.5) * size)
        pb = c + xd * ((p1[0] - 0.4) * size) + yd * ((p1[1] - 0.5) * size)
        obs.append(B.tube(f"{prefix}{si}", [pa, pb], [(0.0012 * U, width * U)] * 2, 4, mat, w, flat=nd))
    return obs


# ---------------------------------------------------------------- 軀幹
under_torso(B, body, "chainD", texel=0.4)
cui = cuirass(B, body, "gold", off=0.018, keel=0.022, globe=0.030, belly=0.012, rivet_mat="gold")
gorget(B, body, "gold", off=0.016)
_, zf = fauld(B, body, "gold", n=3, h=0.055, rivet_mat="gold")
B.both(tasset(B, body, "gold", zf + 0.03 * U, length=0.26, a0=14, a1=68, off=0.040, rivet_mat="gold"))
B.both(tasset(B, body, "gold", zf + 0.03 * U, length=0.24, a0=74, a1=122, off=0.042, rivet_mat="gold", name="TassetSide"))
tree_c, _bm = bvh_of([cui])
# 胸甲浮雕紋（金，凸起細條）；二階同一路徑疊紅光
ENGR = []
for sx in (1, -1):
    ENGR.append([(sx * a, body.tz(t)) for a, t in ((6, 0.86), (24, 0.82), (44, 0.76), (52, 0.66), (40, 0.58), (24, 0.60), (20, 0.68), (32, 0.70))])
    ENGR.append([(sx * a, body.tz(t)) for a, t in ((60, 0.84), (70, 0.70), (66, 0.52), (50, 0.44), (30, 0.42), (12, 0.46))])
    ENGR.append([(sx * a, body.tz(t)) for a, t in ((14, 0.40), (30, 0.36), (46, 0.34))])
ENGR.append([(0, body.tz(t)) for t in (0.90, 0.80, 0.70)])
engr_paths = []
for q, pl in enumerate(ENGR):
    pp = path_on(tree_c, [(a, z) for a, z in pl], 0.0)
    pts = catmull([p for p, n in pp], 10)
    # 重新投影（catmull 之後）
    pts2 = []
    for p in pts:
        ang = math.degrees(math.atan2(p.x, -p.y)); loc, n = hit_axis(tree_c, ang, p.z)
        pts2.append((loc, n))
    engr_paths.append(pts2)
    B.tube(f"Engr{q}", [p + n * 0.004 * U for p, n in pts2], [(0.0065 * U, 0.004 * U)] * len(pts2), 4, "gold", "Spine2")

# 腰：亞麻腰帶、鐵鏈、卷軸、長前擺
zb = body.tz(0.27)
belt(B, body, zb, "linen", {"Spine": 0.4, "Hips": 0.6}, h=0.09, thick=0.016, off=0.07, name="Sash")
belt(B, body, zb - 0.07 * U, "leather", "Hips", h=0.045, thick=0.01, off=0.08, tilt=0.03, name="Belt2")
buckle(B, body, zb - 0.07 * U, 8, "gold", "Hips", off=0.095, size=1.6)
sw = []
for q in range(16):
    s = q / 15
    a = lerp(-95, 60, s)
    sw.append(body.torso.pt(zb - 0.07 * U - 0.20 * U * math.sin(math.pi * s), a, (0.10 + 0.05 * math.sin(math.pi * s)) * R))
chain_links(B, resample(catmull(sw, 40), 15), "steel", w_skirt(body, zb, zb - 0.3 * U, 0.35), link_r=0.024 * U, wire=0.0065 * U, name="Swag")
for q, (a, ln) in enumerate(((62, 0.20), (78, 0.24), (94, 0.18))):
    top = body.torso.pt(zb - 0.08 * U, a, 0.10 * R)
    c = top - Z * ln * 0.5 * U
    B.tube(f"Scroll{q}", [c - Z * ln * 0.5 * U, c + Z * ln * 0.5 * U], [0.032 * U, 0.032 * U], 10, "paper", w_skirt(body, zb, zb - 0.4 * U, 0.3))
    for e in (-1, 1):
        B.tube(f"ScrollCap{q}{e}", [c + Z * (e * ln * 0.5 * U), c + Z * (e * (ln * 0.5 + 0.012) * U)], [0.036 * U] * 2, 10, "leather", w_skirt(body, zb, zb - 0.4 * U, 0.3))
    B.tube(f"ScrollTie{q}", [c + V(0, -0.03 * U, 0), c + V(0, -0.034 * U, 0.003)], [(0.034 * U, 0.01 * U)] * 2, 10, "leather", w_skirt(body, zb, zb - 0.4 * U, 0.3))
tf_pts = [V(0, -0.14 * R - 0.06, zb), V(0, -0.20 * R, zb - 0.40 * U), V(0, -0.22 * R, zb - 0.80 * U), V(0, -0.20 * R, zb - 1.15 * U)]
tf_names = chain_names("TabardF", 3)
cloth_panel(B, "Tabard", lambda u: body.torso.pt(zb - 0.04 * U, lerp(-30, 30, u), 0.085 * R), lambda u: V(math.sin(math.radians(lerp(-30, 30, u))) * 0.5, -1, 0).normalized(),
            1.15 * U, "linen", w_chain_pts("Hips", tf_names, tf_pts), nu=14, nv=16, flare=0.03, rag=0.12, deep=0.25, fold_amp=0.012 * U,
            fold_n=1.6, holes=0.03, seed=41, spread=0.06 * U)
mail_skirt(B, body, "chainD", zb - 0.02 * U, body.tz(-0.12), flare=0.04, rag=0.03, seed=8)

# ---------------------------------------------------------------- 手臂
under_arm(B, body, "chainD")
pl = B.both(pauldron(B, body, "gold", size=1.36, lames=4, haute=0.07, rivet_mat="gold", tilt=0.55))
B.both(arm_armor(B, body, "gold", rivet_mat="gold", cuff=0.04, ridge=0.006))
# 肩甲圓形徽章＋後掠尖刺（左右長短不同）
pole = (body.uarm.u * 0.75 + Z * 0.55).normalized()
mc = j["UpperArmL"] + pole * 0.125 * RL * 1.36
for sx in (1, -1):
    m = V(mc.x * sx, mc.y, mc.z)
    pn = V(pole.x * sx, pole.y, pole.z)
    B.ellipsoid(f"Medal{sx}", m, (pn.orthogonal().normalized(), pn.cross(pn.orthogonal().normalized()), pn), (0.055 * U, 0.055 * U, 0.018 * U), 14, 5,
                "gold", {"ShoulderL" if sx > 0 else "ShoulderR": 0.55, "UpperArmL" if sx > 0 else "UpperArmR": 0.45}, v0=0, v1=0.5)
    sp_base = V(0.20 * sx, 0.12, body.tz(0.98))
    ln = 0.30 if sx > 0 else 0.22
    horn(f"ShSpike{sx}", [sp_base, sp_base + V(0.05 * sx, 0.10, 0.10) * (ln / 0.3), sp_base + V(0.08 * sx, 0.26, 0.20) * (ln / 0.3)], 0.030, w="Spine2", n=6, segs=6)
body.set_grip(0.022 * U)
B.mirror_only(hand(B, body, "gold"))
hand(B, body, "gold", open_amt=0.85)
# 左掌心紅色符紋
Wl = j["HandL"]; ha, hv, hu = body.hand_a, body.hand_v, body.hand_u
pc = Wl + ha * 0.052 * RL - hu * 0.026 * RL
for gi in range(2):
    glyph(f"Palm{gi}", pc + hv * (gi - 0.5) * 0.034 * RL - hu * 0.003, ha, hv, 0.032 * RL, "g_rune", "HandL", gi + 3, width=0.0035)
B.tube("PalmRing", [pc + (ha * math.cos(t) + hv * math.sin(t)) * 0.04 * RL - hu * 0.004 for t in np.linspace(0, 2 * math.pi, 15)], [(0.0012 * U, 0.003 * U)] * 15, 4,
       "g_rune", "HandL", flat=hu, cap=False)
# 左臂也披書頁
for q in range(12):
    a = 60 + q * 30 + rnd.uniform(-10, 10)
    surf, L, bn = (body.uarm, body.ua_len, "UpperArmL") if q < 6 else (body.farm, body.fa_len, "ForearmL")
    t = L * rnd.uniform(0.25, 0.75)
    c = surf.pt(t, a, 0.06 * RL)
    n = surf.nrm(t, a)
    page(f"ArmPage{q}", c - Z * 0.06 * U, n.cross(Z), -Z + n * 0.3, 0.13 * U, 0.17 * U, bn, curl=0.3)

# ---------------------------------------------------------------- 腿
under_leg(B, body, "chainD")
B.both(leg_armor(B, body, "gold", rivet_mat="gold", cuisse=True, wing=True))
B.both(sabaton(B, body, "gold", pointed=1.3, sole_mat="steel"))

# ---------------------------------------------------------------- 頭：骷髏面＋金冠帶＋不對稱角冠
HC = V(0, -0.012 * U, H - hs * 0.52)
B.ellipsoid("Cranium", HC + V(0, 0.012, 0.02), (X, Y, Z), (0.105 * U, 0.125 * U, 0.118 * U), 16, 10, "bone", "Head")
B.ellipsoid("Brow", HC + V(0, -0.072 * U, 0.03 * U), (X, Y, Z), (0.092 * U, 0.05 * U, 0.04 * U), 12, 6, "bone", "Head")
for sx in (1, -1):
    B.ellipsoid(f"Cheek{sx}", HC + V(0.062 * sx * U, -0.07 * U, -0.040 * U), (X, Y, Z), (0.035 * U, 0.045 * U, 0.030 * U), 10, 6, "bone", "Head")
    B.ellipsoid(f"Socket{sx}", HC + V(0.040 * sx * U, -0.105 * U, -0.002 * U), (X, Y, Z), (0.030 * U, 0.016 * U, 0.026 * U), 10, 6, "void", "Head")
    B.ellipsoid(f"Eye{sx}", HC + V(0.040 * sx * U, -0.118 * U, -0.004 * U), (X, Y, Z), (0.011 * U, 0.006 * U, 0.009 * U), 8, 5, "g_eye", "Head")
B.ellipsoid("Nose", HC + V(0, -0.118 * U, -0.050 * U), (X, Y, Z), (0.014 * U, 0.008 * U, 0.020 * U), 8, 5, "void", "Head")
B.ellipsoid("Maxilla", HC + V(0, -0.075 * U, -0.085 * U), (X, Y, Z), (0.070 * U, 0.052 * U, 0.028 * U), 12, 6, "bone", "Head")
B.ellipsoid("Mandible", HC + V(0, -0.060 * U, -0.140 * U), (X, Y, Z), (0.072 * U, 0.060 * U, 0.030 * U), 12, 6, "bone", "Head")
B.ellipsoid("MouthDark", HC + V(0, -0.098 * U, -0.112 * U), (X, Y, Z), (0.052 * U, 0.02 * U, 0.016 * U), 10, 5, "void", "Head")
for q in range(9):
    x = (q - 4) * 0.012 * U
    yb = -0.118 * U + 0.0012 * U * (q - 4) ** 2
    B.tube(f"ToothU{q}", [HC + V(x, yb, -0.098 * U), HC + V(x, yb, -0.118 * U)], [0.0055 * U, 0.003 * U], 5, "bone", "Head")
    B.tube(f"ToothL{q}", [HC + V(x, yb + 0.004, -0.128 * U), HC + V(x, yb + 0.004, -0.110 * U)], [0.0055 * U, 0.003 * U], 5, "bone", "Head")
# 金冠帶（頭盔與骷髏融合）
band = [HC + V(math.sin(a) * 0.112 * U, -math.cos(a) * 0.130 * U, 0.050 * U + 0.012 * U * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 25)]
B.tube("Circlet", band, [(0.014 * U, 0.024 * U)] * 25, 6, "gold", "Head", flat=Z, cap=False)
B.ellipsoid("HelmBack", HC + V(0, 0.03 * U, 0.03 * U), (X, Y, Z), (0.115 * U, 0.12 * U, 0.125 * U), 16, 8, "gold", "Head", v0=0.0, v1=0.62,
            dent=lambda d, u, v: 1.0 + 0.04 * (d.y > 0))
HB = HC + V(0, 0, 0.06 * U)
horn("HornC", [HB + V(0, -0.02, 0.02), HB + V(0, -0.01, 0.20), HB + V(0.02, 0.03, 0.40), HB + V(0.0, 0.02, 0.55)], 0.034)
horn("HornL1", [HB + V(0.09, 0.0, 0.0), HB + V(0.22, 0.02, 0.08), HB + V(0.30, 0.0, 0.26), HB + V(0.26, -0.04, 0.42), HB + V(0.19, -0.06, 0.48)], 0.040)
horn("HornL2", [HB + V(0.10, 0.05, -0.06), HB + V(0.25, 0.09, -0.04), HB + V(0.36, 0.07, 0.10), HB + V(0.41, 0.01, 0.26)], 0.032)
horn("HornL3", [HB + V(0.06, -0.05, 0.03), HB + V(0.10, -0.08, 0.15), HB + V(0.12, -0.10, 0.25)], 0.022)
horn("HornR2", [HB + V(-0.10, 0.05, -0.06), HB + V(-0.27, 0.10, -0.02), HB + V(-0.37, 0.08, 0.12)], 0.030)
horn("HornBkL", [HB + V(0.05, 0.10, -0.02), HB + V(0.09, 0.25, 0.04), HB + V(0.11, 0.40, 0.14)], 0.025)
horn("HornBkR", [HB + V(-0.05, 0.10, -0.02), HB + V(-0.08, 0.22, 0.03), HB + V(-0.10, 0.31, 0.10)], 0.022)
RLONG = [HB + V(-0.09, 0.0, 0.0), HB + V(-0.24, 0.03, 0.10), HB + V(-0.34, 0.02, 0.32), HB + V(-0.29, -0.05, 0.54), HB + V(-0.20, -0.08, 0.64)]
_, PR, RR = horn("HornR1", RLONG, 0.044, mk="HornLongR")

# ---------------------------------------------------------------- 書頁披風（底布＋層疊書頁，往下擴散拖地）
ztop = body.tz(0.96)


def cape_pt(a, v, off=0.0):
    v = max(0.0, min(1.0, v))
    z = lerp(ztop, 0.03, v)
    rx = lerp(0.44, 0.92, v ** 0.85) + off
    ry = lerp(0.27, 0.95, v ** 0.9) + off
    return V(math.sin(a) * rx, 0.05 + math.cos(a) * ry, z + 0.04 * v * v)


def arange(v):
    return math.radians(lerp(82, 120, v ** 0.7))


cp_pts = [cape_pt(0, v) for v in (0.0, 0.3, 0.62, 1.0)]
cp_names = chain_names("Cape", 3)
W_CAPE = w_chain_pts("Spine2", cp_names, cp_pts)
cape_cut = rag_profile(20, random.Random(3), 0.2)


def capefn(u, v):
    a = lerp(-arange(v), arange(v), u)
    k = min(int(round(u * 20)), 20)
    vv = v * (1 - 0.05 * cape_cut[k])
    return cape_pt(a, vv, -0.02) + V(0, 0, 0.0)


cp = B.grid("CapeBase", 20, 14, capefn, "capeCloth", W_CAPE, [V(0, 0, z) for z in (0.3, 1.0, 1.8)], sharp=60)
cp["cloth"] = 0.008
n_pages = 0
v = 0.0
row = 0
while v < 0.97:
    ar = arange(v)
    rx = lerp(0.44, 0.92, v ** 0.85)
    arc = 2 * ar * (rx + lerp(0.27, 0.95, v ** 0.9)) * 0.5
    n = max(5, int(arc / 0.15))
    for k in range(n):
        a = lerp(-ar, ar, (k + 0.5 + rnd.uniform(-0.3, 0.3)) / n)
        vv = max(0.0, min(0.99, v + rnd.uniform(-0.01, 0.02)))
        c = cape_pt(a, vv, 0.005 + 0.002 * row)
        e = 0.01
        T = (cape_pt(a + e, vv) - cape_pt(a - e, vv)).normalized()
        Dn = (cape_pt(a, min(1, vv + e)) - cape_pt(a, max(0, vv - e))).normalized()
        yaw = math.radians(rnd.uniform(-22, 22))
        T2 = T * math.cos(yaw) + Dn * math.sin(yaw)
        D2 = Dn * math.cos(yaw) - T * math.sin(yaw)
        w_ = 0.15 * U * rnd.uniform(0.85, 1.15); h_ = 0.20 * U * rnd.uniform(0.85, 1.2)
        page(f"Page{n_pages}", c + D2 * h_ * 0.35, T2, D2, w_, h_, W_CAPE, curl=rnd.uniform(-0.2, 0.4))
        n_pages += 1
    v += 0.075 + 0.02 * v
    row += 1
# 拖在地上的散頁
for q in range(10):
    a = math.radians(rnd.uniform(-130, 130))
    c = cape_pt(a, 1.0, 0.05 + rnd.uniform(0, 0.15))
    c.z = 0.015
    page(f"GroundPage{q}", c, V(math.cos(a), math.sin(a), 0), V(-math.sin(a), math.cos(a), -0.15), 0.15 * U, 0.2 * U, W_CAPE, curl=0.2)
print("pages", n_pages, flush=True)

# ---------------------------------------------------------------- 鋸齒巨劍（右手；劍尖在 +AX）
gcR = Body.mir(body.grip_c)
AX = Body.mir(body.hand_v).normalized()
EG = Body.mir(body.hand_a); EG = (EG - AX * EG.dot(AX)).normalized()
SD = AX.cross(EG).normalized()
BL0, BL1 = 0.13, 1.13          # 劍刃起訖（U）


def P_sw(a, e, s=0.0):
    return gcR + AX * (a * U) + EG * (e * U) + SD * (s * U)


def hw(v):
    """半寬（U）＋鋸齒：齒尖朝劍柄。"""
    base = 0.082 + 0.012 * math.sin(math.pi * min(1, v * 1.3))
    if v > 0.84:
        base *= max(0.0, (1 - v) / 0.16) ** 0.75
    x = v * 17.0
    tooth = 0.030 * (1 - (x % 1.0)) ** 1.8 if 0.05 < v < 0.86 else 0.0
    return base, tooth


def sword_fn(u, v):
    if u <= 0.5:
        q, sd = u * 2, 1.0
    else:
        q, sd = 2 - 2 * u, -1.0
    b, t = hw(v)
    side = 1 if q > 0.5 else -1
    e = lerp(-(b + t), b + t * 0.85, q)
    th = 0.020 * (1 - 0.8 * v) * (math.sin(math.pi * q) ** 0.4 + 0.05)
    return P_sw(lerp(BL0, BL1, v), e, sd * th * 0.5)


B.grid("SwordBlade", 8, 54, sword_fn, "blade", "Weapon", [P_sw(lerp(BL0, BL1, k / 6), 0) for k in range(7)], closed_u=True, cap0=True, sharp=40)
# 鋸齒內暗紅細線（兩面兩側）
for sd in (1, -1):
    for side in (1, -1):
        pts = [P_sw(lerp(BL0, BL1, v), side * (hw(v)[0] - 0.016), sd * (0.020 * (1 - 0.8 * v) * 0.5 + 0.0015)) for v in np.linspace(0.06, 0.84, 12)]
        B.tube(f"SwordGlow{sd}{side}", pts, [(0.0012 * U, 0.0028 * U)] * 12, 4, "g_weapon", "Weapon", flat=SD)
# 中脊
B.tube("Fuller", [P_sw(lerp(BL0, BL1, v), 0, 0) for v in (0.02, 0.5, 0.82)], [(0.004 * U, 0.013 * U), (0.003 * U, 0.012 * U), (0.002 * U, 0.009 * U)], 4, "blade", "Weapon", flat=SD)
# 護手（帶鉤）、握柄、柄頭
gp = [P_sw(0.10, -0.22), P_sw(0.12, -0.18), P_sw(0.11, -0.06), P_sw(0.11, 0.06), P_sw(0.12, 0.18), P_sw(0.10, 0.22)]
B.tube("Guard", gp, [(0.018 * U, 0.016 * U), (0.024 * U, 0.02 * U), (0.03 * U, 0.024 * U), (0.03 * U, 0.024 * U), (0.024 * U, 0.02 * U), (0.018 * U, 0.016 * U)],
       8, "steelB", "Weapon", flat=AX)
for sx in (1, -1):
    B.tube(f"GuardHook{sx}", [P_sw(0.10, 0.21 * sx), P_sw(0.16, 0.27 * sx), P_sw(0.24, 0.25 * sx)], [0.016 * U, 0.01 * U, 0.0015 * U], 6, "steelB", "Weapon")
B.tube("Grip", [P_sw(0.10 - 0.33 * k / 6, 0) for k in range(7)], [(0.023 + (0.003 if k % 2 else 0)) * U for k in range(7)], 8, "leather", "Weapon", flat=EG)
B.ellipsoid("Pommel", P_sw(-0.25, 0), (EG, SD, AX), (0.035 * U, 0.03 * U, 0.03 * U), 10, 6, "steelB", "Weapon")
for sx in (1, -1):
    B.tube(f"PommelClaw{sx}", [P_sw(-0.26, 0.02 * sx), P_sw(-0.31, 0.05 * sx), P_sw(-0.34, 0.03 * sx)], [0.012 * U, 0.008 * U, 0.0015 * U], 6, "steelB", "Weapon")

# ================================================================ 二階部件
# P2_ChestMaw：胸甲中央豎直獠牙巨口
MZ = body.tz(0.62)
mloc, mn = hit_axis(tree_c, 0, MZ)
MH, MW = 0.12 * H * 0.5, 0.075 * U
maw = []


def maw_fn(u, v):
    a = 2 * math.pi * u
    r = v
    x = math.sin(a) * MW * r * (1 - 0.0)
    z = math.cos(a) * MH * r
    lens = math.sqrt(max(0.0, 1 - (z / MH) ** 2)) if r > 0 else 1
    x *= lens
    return mloc + mn * (0.012 * U - 0.03 * U * (1 - r * r)) + X * x + Z * z


maw.append(B.grid("MawInner", 16, 5, maw_fn, "p2_maw", "Spine2", mloc - mn * 0.3, closed_u=True))
for sx in (1, -1):
    lip = [maw_fn(0.25 * sx % 1.0 if False else (0.0 + (0.5 * k / 10 if sx > 0 else 1 - 0.5 * k / 10)), 1.0) + mn * 0.006 * U for k in range(11)]
    maw.append(B.tube(f"MawLip{sx}", lip, [(0.016 * U, 0.020 * U)] * 11, 6, "flesh", "Spine2", flat=mn))
    for k in range(1, 10):
        p = lip[k]
        inward = (V(mloc.x, p.y, p.z) - p); inward.z = 0
        ln = (0.035 + 0.02 * math.sin(math.pi * k / 10)) * U
        maw.append(cone(f"MawTooth{sx}{k}", p + mn * 0.004, inward.normalized() * 1.0 + mn * 0.25, ln, 0.010 * U, "bone", "Spine2", segs=5))
VH.mark(maw, "P2_ChestMaw")

# P2_Glow_Script：浮雕紋轉紅（胸）＋肩甲／腿甲紅紋
scr = []
for q, pts2 in enumerate(engr_paths):
    scr.append(B.tube(f"ScriptC{q}", [p + n * 0.0085 * U for p, n in pts2], [(0.0045 * U, 0.003 * U)] * len(pts2), 3, "p2_script", "Spine2"))
VH.mark(scr, "P2_ScriptChest")
for sx, sfx in ((1, "L"), (-1, "R")):
    obs = []
    pl_obs = [o for o in B.parts if o.name.startswith("Pauldron") and (o.name.endswith("_R") == (sx < 0)) and "Rivets" not in o.name]
    tp, _ = bvh_of(pl_obs)
    shc = V(j["UpperArmL"].x * sx, j["UpperArmL"].y, j["UpperArmL"].z)
    for k in range(3):
        pts = []
        for s in np.linspace(0, 1, 10):
            ang = (lerp(-60, 60, s) + 180 * (k == 2)) * 1.0
            dz = 0.05 * U * k - 0.02 * U + 0.03 * U * math.sin(s * 6)
            o = shc + V(0, 0, 0.6) + V(math.sin(math.radians(ang)) * 0.12 * U * (1 + 0.5 * k), -math.cos(math.radians(ang)) * 0.12 * U * (1 + 0.5 * k), 0)
            loc, n, _, _ = tp.ray_cast(o, (shc + V(0, 0, dz) - o).normalized())
            if loc is not None:
                if n.dot(o - loc) < 0:
                    n = -n
                pts.append(loc + n * 0.006 * U)
        if len(pts) > 2:
            obs.append(B.tube(f"ScriptP{sfx}{k}", pts, [(0.004 * U, 0.003 * U)] * len(pts), 4, "p2_script", "UpperArm" + sfx))
    # 腿甲紅紋
    for k in range(2):
        pts = [body.thigh.pt(body.th_len * lerp(0.28, 0.82, s), (lerp(-30, 40, s) + 60 * k) * (1 if sx > 0 else -1) * 1.0, 0.024 * RL) for s in np.linspace(0, 1, 8)]
        if sx < 0:
            pts = [V(-p.x, p.y, p.z) for p in [body.thigh.pt(body.th_len * lerp(0.28, 0.82, s), (lerp(-30, 40, s) + 60 * k), 0.024 * RL) for s in np.linspace(0, 1, 8)]]
        VH.mark(B.tube(f"ScriptT{sfx}{k}", pts, [(0.004 * U, 0.003 * U)] * len(pts), 4, "p2_script", "Thigh" + sfx), "P2_ScriptLeg" + sfx)
    VH.mark(obs, "P2_Script" + sfx)

# P2_SwordCracks：劍身樹枝狀裂紋全亮
crk = []
r_ = random.Random(9)
for sd in (1, -1):
    for b in range(5):
        v0 = 0.08 + 0.16 * b
        p = [(v0, 0.0)]
        for s in range(5):
            v1 = p[-1][0] + r_.uniform(0.03, 0.06); e1 = p[-1][1] + r_.uniform(-0.03, 0.03)
            p.append((v1, max(-0.06, min(0.06, e1))))
        pts = [P_sw(lerp(BL0, BL1, vv), ee, sd * (0.020 * (1 - 0.8 * vv) * 0.5 + 0.0018)) for vv, ee in p]
        crk.append(B.tube(f"Crack{sd}{b}", pts, [(0.0012 * U, 0.0045 * U)] * len(pts), 4, "p2_blade", "Weapon", flat=SD))
        vb, eb = p[2]
        br = [(vb, eb), (vb + 0.03, eb + 0.035 * (1 if b % 2 else -1)), (vb + 0.05, eb + 0.05 * (1 if b % 2 else -1))]
        pts = [P_sw(lerp(BL0, BL1, vv), ee, sd * (0.020 * (1 - 0.8 * vv) * 0.5 + 0.0018)) for vv, ee in br]
        crk.append(B.tube(f"CrackB{sd}{b}", pts, [(0.0012 * U, 0.0035 * U)] * 3, 4, "p2_blade", "Weapon", flat=SD))
VH.mark(crk, "P2_SwordCracks")

# P2_PageWingL/R：背後書頁紙翼（頁緣燃紅），骨頭 WingL／WingR
WING = {}
for sx in (1, -1):
    base = V(0.16 * sx, 0.24, body.tz(0.86))
    obs = []
    for k, (th, ln) in enumerate(((2, 1.30), (20, 1.50), (38, 1.45), (56, 1.15))):
        thr = math.radians(th)
        d = V(math.cos(thr) * sx, 0.30, math.sin(thr)).normalized()
        npg = 7 + (k in (1, 2))
        for q in range(npg):
            s = (q + 0.8) / (npg + 0.3)
            c = base + d * (ln * s) + V(0, 0.04 * k, 0) - Z * 0.05 * math.sin(math.pi * s)
            perp = V(math.sin(thr) * sx, 0.0, -math.cos(thr))
            down = (perp * 0.55 - Z * 0.45 + d * 0.15).normalized()
            xd = d.normalized()
            h_ = (0.24 + 0.10 * s) * U * rnd.uniform(0.85, 1.1)
            w_ = 0.16 * U * rnd.uniform(0.85, 1.1)
            rot = rnd.uniform(-0.35, 0.35)
            xd2 = (xd * math.cos(rot) + down * math.sin(rot)).normalized()
            dn2 = (down * math.cos(rot) - xd * math.sin(rot)).normalized()
            pc_ = c + dn2 * h_ * 0.45
            obs.append(page(f"Wing{sx}{k}{q}", pc_, xd2, dn2, w_, h_, "Spine2", curl=rnd.uniform(-0.3, 0.3)))
            nd = xd2.cross(dn2)
            e0 = pc_ + dn2 * h_ * 0.5 - xd2 * w_ * 0.5; e1 = pc_ + dn2 * h_ * 0.5 + xd2 * w_ * 0.5
            obs.append(B.tube(f"WingEdge{sx}{k}{q}", [e0, e1], [(0.0028 * U, 0.010 * U)] * 2, 4, "p2_page", "Spine2", flat=nd, cap=False))
    for o in obs:
        for g in list(o.vertex_groups):
            o.vertex_groups.remove(g)
        g = o.vertex_groups.new(name="WingL" if sx > 0 else "WingR")
        g.add([vv.index for vv in o.data.vertices], 1.0, "REPLACE")
    WING[sx] = base
    VH.mark(obs, "P2_PageWingL" if sx > 0 else "P2_PageWingR")

# ================================================================ 三階部件
# P3_Crown：頭頂破碎紅黑光環（4 段）
crown = []
CC = HC + V(0, 0.05 * U, 0.50 * U)
CR = 0.10 * H
for k in range(4):
    a0 = k * 90 + 12 + rnd.uniform(-6, 6); a1 = a0 + 62 + rnd.uniform(-8, 8)
    arc = []
    for s in np.linspace(0, 1, 10):
        a = math.radians(lerp(a0, a1, s))
        arc.append(CC + V(math.cos(a) * CR, math.sin(a) * CR, 0.02 * math.sin(a * 2) + 0.03 * math.cos(a)))
    crown.append(B.tube(f"Halo{k}", arc, [(0.010 * U, 0.020 * U)] * 10, 4, "p3_halo", "Head", flat=Z))
    crown.append(B.tube(f"HaloCore{k}", [p + V(0, 0, 0.0) for p in arc], [(0.013 * U, 0.009 * U)] * 10, 4, "p3_ink", "Head", flat=Z))
    for e in range(3):
        a = math.radians(lerp(a0, a1, rnd.random()))
        p = CC + V(math.cos(a) * CR, math.sin(a) * CR, 0)
        crown.append(cone(f"HaloSpark{k}{e}", p, V(math.cos(a) * 0.3, math.sin(a) * 0.3, 1), 0.06 * U, 0.008 * U, "p3_halo", "Head", segs=4))
VH.mark(crown, "P3_Crown")
# P3_HornBroken：右長角斷根（鋸齒斷口＋紅色斷面）
nb = 4
stub = B.tube("HornStub", PR[:nb], [RR[k] * 1.03 for k in range(nb)], 8, "bone", "Head", cap=True)
d = (PR[nb - 1] - PR[nb - 2]).normalized()
jag = []
for k in range(7):
    a = 2 * math.pi * k / 7
    e1 = d.orthogonal().normalized(); e2 = d.cross(e1)
    p = PR[nb - 1] + (e1 * math.cos(a) + e2 * math.sin(a)) * RR[nb - 1] * 0.8
    jag.append(cone(f"HornJag{k}", p, d + (e1 * math.cos(a) + e2 * math.sin(a)) * 0.3, (0.03 + 0.03 * (k % 2)) * U, RR[nb - 1] * 0.35, "hornD", "Head", segs=4))
cap = B.ellipsoid("HornBreakGlow", PR[nb - 1] + d * 0.004, (d.orthogonal().normalized(), d.cross(d.orthogonal().normalized()), d), (RR[nb - 1] * 0.9, RR[nb - 1] * 0.9, 0.01 * U),
                  10, 4, "p3_cracks", "Head", v0=0, v1=0.5)
VH.mark([stub, cap] + jag, "P3_HornBroken")
# P3_Glow_Eyes：眼窩噴紅焰
fl = []
for sx in (1, -1):
    for q in range(3):
        p = HC + V(0.040 * sx * U, -0.112 * U, 0.004 * U)
        dd = V(0.15 * sx + 0.1 * (q - 1), -0.15, 1.0)
        fl.append(wisp(f"EyeFlame{sx}{q}", p, dd, (0.14 + 0.05 * (q == 1)) * U, X, "p3_eyes", "Head", width=0.014, curl=0.35, seed=90 + q + (sx > 0) * 5, up=0.2))
VH.mark(fl, "P3_EyeFlames")
# P3_InkBody：下半身墨潮（腳不可見）＋往後捲的漩渦＋殘頁
ink = []


def ink_fn(u, v):
    a = 2 * math.pi * u
    z = lerp(body.tz(0.22), 0.0, v)
    r = lerp(0.36, 0.78, v ** 1.2) * (1 + 0.10 * math.sin(5 * a + 3 * v) * v + 0.06 * math.sin(11 * a - 5 * v) * v)
    back = max(0.0, math.cos(a - math.pi / 2 * 0 - math.pi * 1.0 * 0 + 0)) if False else max(0.0, math.cos(a))
    y = -math.cos(a) * r * 0.9 + 0.55 * v ** 1.5 * max(0.0, -math.cos(a)) * 0
    x = math.sin(a) * r
    tail = 0.45 * v ** 1.6 * max(0.0, math.cos(a + math.pi)) * 0
    return V(x, -math.cos(a) * r * 0.85 + 0.25 * v ** 1.4, z + 0.06 * math.sin(7 * a + 6 * v) * v)


ink.append(B.grid("InkTide", 22, 8, ink_fn, "p3_ink", "Hips", [V(0, 0, z) for z in (0.2, 0.8, 1.2)], closed_u=True, sharp=70))
for k in range(6):
    a = math.radians(140 + k * 16)
    p = V(math.sin(a) * 0.5, 0.25 - math.cos(a) * 0.5, 0.25 + 0.08 * k)
    ink.append(wisp(f"InkCurl{k}", p, V(math.sin(a) * 0.4, 1.0, 0.3), (0.5 + 0.08 * k) * U, Z, "p3_ink", "Hips", width=0.06, curl=0.5, seed=120 + k, up=0.6))
for q in range(8):
    a = math.radians(rnd.uniform(90, 270))
    c = V(math.sin(a) * 0.65, 0.2 - math.cos(a) * 0.6, rnd.uniform(0.15, 0.7))
    ink.append(page(f"InkPage{q}", c, V(math.cos(a), math.sin(a), 0.3), V(0.2, 0.3, -1), 0.13 * U, 0.17 * U, "Hips", curl=0.4))
VH.mark(ink, "P3_InkBody")
# P3_ArmorCracked：約 30% 甲片剝落、露出暗色裂肉、裂縫熔紅（胸、腹、左上臂）
crk3 = []
r3 = random.Random(31)
for pi_, (a0, a1, t0, t1) in enumerate(((-34, 6, 0.50, 0.80), (8, 40, 0.34, 0.56), (-60, -36, 0.36, 0.52), (36, 66, 0.62, 0.80))):
    cut = [r3.uniform(0.0, 0.35) for _ in range(12)]

    def pfn(u, v, a0=a0, a1=a1, t0=t0, t1=t1, cut=cut):
        ang = lerp(a0, a1, u)
        k = min(int(u * 11), 11)
        vv = lerp(cut[k] * 0.5, 1 - cut[11 - k] * 0.5, v)
        loc, n = hit_axis(tree_c, ang, body.tz(lerp(t0, t1, vv)))
        return loc + n * 0.010 * U
    o = B.grid(f"Flesh{pi_}", 10, 6, pfn, "flesh", "Spine2", V(0, 0, body.tz(lerp(t0, t1, 0.5))))
    crk3.append(o)
    for c in range(3):
        u0 = r3.uniform(0.15, 0.85); v0 = r3.uniform(0.15, 0.85)
        pts = []
        for s in range(5):
            u0 = min(0.95, max(0.05, u0 + r3.uniform(-0.12, 0.12))); v0 = min(0.95, max(0.05, v0 + r3.uniform(0.05, 0.14) * (1 if c % 2 else -1)))
            ang = lerp(a0, a1, u0)
            loc, n = hit_axis(tree_c, ang, body.tz(lerp(t0, t1, v0)))
            pts.append(loc + n * 0.0135 * U)
        crk3.append(B.tube(f"FleshCrack{pi_}{c}", pts, [(0.004 * U, 0.004 * U)] * 5, 4, "p3_cracks", "Spine2"))
VH.mark(crk3, "P3_ArmorCrackedChest")
arm3 = []
for c in range(5):
    a = 40 + c * 50
    t = body.ua_len * (0.45 + 0.08 * (c % 3))
    p0 = body.uarm.pt(t, a, 0.040 * RL)
    arm3.append(B.shell(f"ArmFlesh{c}", body.uarm, t - 0.03 * U, t + 0.04 * U, a - 18, a + 18, 4, 2, "flesh", "UpperArmL", off=0.032 * RL))
    arm3.append(B.tube(f"ArmCrack{c}", [body.uarm.pt(t - 0.02 * U, a - 8, 0.038 * RL), body.uarm.pt(t + 0.01 * U, a + 3, 0.038 * RL), body.uarm.pt(t + 0.035 * U, a + 10, 0.038 * RL)],
                       [(0.004 * U, 0.004 * U)] * 3, 4, "p3_cracks", "UpperArmL"))
VH.mark(arm3, "P3_ArmorCrackedArm")
# P3_SwordWords：劍外 3 圈漂浮符字環（紅＋金）＋劍長 +20%
words = []
gi = 0
for k, (a, rr) in enumerate(((0.38, 0.085), (0.70, 0.075), (1.02, 0.065))):
    cen = P_sw(a, 0)
    for q in range(10):
        t = 2 * math.pi * q / 10
        rad = rr * H
        p = cen + (EG * math.cos(t) + SD * math.sin(t)) * rad
        outv = (EG * math.cos(t) + SD * math.sin(t))
        tang = outv.cross(AX)
        mat = "p3_glyphG" if q % 4 == 0 else "p3_glyph"
        words += glyph(f"Word{k}{q}", p, tang, AX, 0.05 * U, mat, "Weapon", gi, width=0.0045)
        gi += 1
    words.append(B.tube(f"WordRing{k}", [cen + (EG * math.cos(t) + SD * math.sin(t)) * (rr * H) - AX * 0.032 * U for t in np.linspace(0, 2 * math.pi, 17)],
                        [(0.0012 * U, 0.002 * U)] * 17, 4, "p3_glyph", "Weapon", cap=False))


def ext_fn(u, v):
    if u <= 0.5:
        q, sd = u * 2, 1.0
    else:
        q, sd = 2 - 2 * u, -1.0
    b = 0.06 * (1 - v) ** 0.8 + 0.002
    e = lerp(-b, b, q)
    th = 0.006 * (1 - v) * (math.sin(math.pi * q) ** 0.4 + 0.05)
    return P_sw(BL1 - 0.10 + v * 0.30, e, sd * th * 0.5)


words.append(B.grid("SwordExt", 8, 8, ext_fn, "blade", "Weapon", [P_sw(BL1, 0)], closed_u=True))
words.append(B.tube("SwordExtGlow", [P_sw(BL1 - 0.08 + 0.28 * s, 0, 0.004) for s in np.linspace(0, 1, 6)], [(0.0012 * U, 0.004 * U)] * 6, 4, "p3_glyph", "Weapon", flat=SD))
VH.mark(words, "P3_SwordWords")

# ---------------------------------------------------------------- 骨架、烘焙
arm = build_armature("BossDevourer", body, weapon=(gcR, gcR + AX * 0.30 * U),
                     chains=[("Cape", "Spine2", cp_pts), ("TabardF", "Hips", tf_pts)],
                     extra=[("WingL", "Spine2", WING[1], WING[1] + V(0.3, 0.05, 0.05)), ("WingR", "Spine2", WING[-1], WING[-1] + V(-0.3, 0.05, 0.05))])
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS", tri, flush=True)
if os.environ.get("V2B_TALLY"):
    import re as _re
    tal = {}
    for o in B.parts:
        k = _re.sub(r"[0-9_\-.]+(R)?$", "", o.name)
        tal[k] = tal.get(k, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons)
    print("TALLY", sorted(tal.items(), key=lambda x: -x[1])[:30], flush=True)
DETAIL_OF = {"gold": "metal", "steel": "metal", "steelB": "metal", "blade": "metal", "bone": "bone", "hornD": "bone",
             "linen": "cloth", "capeCloth": "cloth", "leather": "leather", "flesh": "leather"}.get
mesh = VH.assemble2(B, BAKEKEY, size=(TEXS, TEXS), bake=not QUICK, quick=QUICK, detail_of=DETAIL_OF, U=U)
BONE_OF = {"HornLongR": "Head", "P2_ChestMaw": "Spine2", "P2_ScriptChest": "Spine2", "P2_ScriptL": "UpperArmL", "P2_ScriptR": "UpperArmR", "P2_ScriptLegL": "ThighL", "P2_ScriptLegR": "ThighR",
           "P2_SwordCracks": "Weapon", "P2_PageWingL": "WingL", "P2_PageWingR": "WingR", "P3_Crown": "Head", "P3_HornBroken": "Head",
           "P3_EyeFlames": "Head", "P3_InkBody": "Hips", "P3_ArmorCrackedChest": "Spine2", "P3_ArmorCrackedArm": "UpperArmL", "P3_SwordWords": "Weapon"}
parts = VH.split_parts(mesh, arm, lambda n: BONE_OF[n])
# 腿甲紅紋分成左右兩個骨頭：ScriptL 裡腿部的線要跟大腿走 → 簡化：拆成獨立節點
BK.bind(mesh, arm)
mesh.name = MODEL + "_mesh"
print("TRIS_MAIN", BK.tri_count(mesh), "TRIS_P", sum(BK.tri_count(o) for o in parts.values()), flush=True)

# ---------------------------------------------------------------- 動作
legs = [("ThighL", "ShinL", 0.15 * U), ("ThighR", "ShinR", 0.15 * U), ("ShinL", "FootL", 0.12 * U), ("ShinR", "FootR", 0.12 * U)]
rig = Rig(arm, body, chains=[
    dict(names=cp_names, anchor="Spine2", pts=cp_pts, stiff=0.10, damp=0.88, colliders=legs + [("Hips", "Spine2", 0.30 * U)], out=(0, 1, 0)),
    dict(names=tf_names, anchor="Hips", pts=tf_pts, stiff=0.07, damp=0.90, colliders=legs, out=(0, -1, 0))])
TIP = BL1
rig.tip_len = TIP * U
rig.lie_dz = 0.08
GL = -0.20


def two(Pd, g, d, edge_, hintR=None, elL=None, gl=None):
    Pd["ikL"] = 1.0; Pd["gripL"] = GL if gl is None else gl
    Pd["elL"] = elL or (0.6, 0.3, -0.7)
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))


def one(Pd, g, d, edge_, left, hintR=None, hintL=None):
    Pd["ikL"] = 0.0
    rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))
    rig.reach(Pd, "L", left, hintL)


PLANT = (-0.48, -0.26, TIP * 0.985 + 0.05)
WP = {
    # 待機：巨劍拄地（劍尖觸地）、左手前伸掌心向上
    "idle": lambda p: one(p, PLANT, (-0.03, -0.12, -0.99), (0, -0.99, 0.12), (0.52, -0.50, 1.18), hintR=(-0.8, 0.3, -0.5), hintL=(0.6, 0.4, -0.7)),
    "o_up": lambda p: two(p, (-0.06, 0.02, 1.90), (0.0, 0.70, 0.70), (0, -0.7, 0.7), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
    "o_up2": lambda p: two(p, (-0.06, 0.06, 1.93), (0.0, 0.82, 0.56), (0, -0.7, 0.7), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
    "o_hit": lambda p: two(p, (0.0, -0.76, 0.86), (0.02, -0.92, -0.38), (0, 0, -1), hintR=(-0.8, 0.4, -0.3)),
    "o_low": lambda p: two(p, (0.0, -0.76, 0.74), (0.02, -0.90, -0.44), (0, 0, -1), hintR=(-0.8, 0.4, -0.3)),
    "o_rec": lambda p: two(p, (-0.10, -0.50, 0.92), (0.1, -0.9, 0.1), (0, -0.5, -0.8)),
    "s_wind": lambda p: two(p, (-0.48, 0.10, 1.26), (-0.57, 0.82, 0.20), (-0.82, -0.57, 0), hintR=(-0.3, 0.9, -0.4)),
    "s_wind2": lambda p: two(p, (-0.50, 0.14, 1.28), (-0.45, 0.88, 0.22), (-0.88, -0.45, 0), hintR=(-0.3, 0.9, -0.4)),
    "s_hit": lambda p: two(p, (-0.02, -0.62, 1.14), (0.37, -0.93, -0.05), (0.93, 0.37, 0), hintR=(-0.8, 0.3, -0.5)),
    "s_follow": lambda p: two(p, (0.28, -0.36, 1.08), (0.91, 0.42, -0.12), (-0.42, 0.91, 0), hintR=(-0.5, -0.2, -0.8)),
    "s_settle": lambda p: two(p, (0.25, -0.38, 1.04), (0.95, 0.28, -0.16), (-0.28, 0.95, 0), hintR=(-0.5, -0.2, -0.8)),
    "enter0": lambda p: one(p, (-0.40, -0.30, TIP * 0.98 + 0.02), (0.02, -0.15, -0.99), (0, -0.99, 0.15), (0.40, -0.10, 0.80)),
    "enter1": lambda p: one(p, (-0.40, -0.30, TIP * 0.98 + 0.06), (0.02, -0.15, -0.99), (0, -0.99, 0.15), (0.45, -0.20, 0.95)),
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
    # 轉階段
    "ps_chest": lambda p: one(p, PLANT, (-0.03, -0.12, -0.99), (0, -0.99, 0.12), (0.10, -0.38, 1.42), hintR=(-0.8, 0.3, -0.5), hintL=(0.7, -0.2, -0.6)),
    "ps_burst": lambda p: one(p, (-0.66, -0.10, 1.42), (-0.55, -0.25, 0.80), (0, -1, 0.3), (0.70, -0.14, 1.45), hintL=(0.3, 0.6, -0.7)),
    "ps_low2": lambda p: two(p, (-0.18, -0.42, 1.02), (0.30, -0.55, -0.78), (0, 0.82, -0.57), hintR=(-0.8, 0.2, -0.5)),
    "ps2_stab": lambda p: two(p, (-0.06, -0.52, 1.0), (0.0, -0.12, -0.99), (0, -0.99, 0.12), hintR=(-0.8, 0.3, -0.4), gl=0.14),
    "ps2_spread": lambda p: one(p, (-0.70, 0.02, 1.62), (-0.45, 0.10, 0.88), (0, -1, 0.1), (0.72, 0.0, 1.66), hintL=(0.3, 0.6, -0.6)),
}

if not NOANIM:
    import v2b_dev_actions
    v2b_dev_actions.build(rig, lambda key, p: WP[key](p), primary="over", slow=1.1, only=ONLY, wide=1.2)


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


def extra_bones():
    """紙翼：緩慢開合（循環片段整數週期）；PhaseShift 爆發時從收攏彈開。"""
    ad = arm.animation_data
    if not ad:
        return
    for tr in ad.nla_tracks:
        act = bpy.data.actions[tr.name]
        meta = rig.meta.get(tr.name, {})
        loop = meta.get("loop", False)
        f0, f1 = act.frame_range
        N = int(round(f1 - f0)) + 1
        dur = (N - 1) / 30
        t = np.arange(N) / 30.0
        cyc = max(1, round(dur / 2.4)) if loop else dur / 2.4
        flap = 0.10 * np.sin(2 * math.pi * cyc * t / max(dur, 1e-3))
        if tr.name in ("PhaseShift", "PhaseShift2"):
            T = 1.15 if tr.name == "PhaseShift" else 1.25
            flap = flap - 0.9 * np.clip(1 - (t - T) / 0.3, 0, 1) * (t >= T)
        for side, bn in ((1, "WingL"), (-1, "WingR")):
            qs = [Quaternion((0, 1, 0), float(side * flap[k])) @ Quaternion((0, 0, 1), float(side * 0.5 * flap[k])) for k in range(N)]
            _write(act, bn, qs)


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
HT = H + 0.45
os.makedirs(TILES, exist_ok=True)


def show_form(f):
    for n, o in parts.items():
        on = (n.startswith("P2_") and f >= 2) or (n.startswith("P3_") and f >= 3) or (n == "HornLongR" and f < 3) or not n.startswith(("P2_", "P3_", "HornLongR"))
        o.hide_render = not on; o.hide_viewport = not on


show_form(1)
if not NOVIEWS:
    cam = BK.render_views(arm, HT, TILES)
    VH.set_rest(arm)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 560, 800
    show_form(2)
    VH.render_still(cam, -35, Vector((0, 0, HT * 0.52)), HT * 2.6, os.path.join(TILES, "view_4_p2_threeq.png"), elev=HT * 0.05)
    VH.render_still(cam, 150, Vector((0, 0, HT * 0.55)), HT * 2.6, os.path.join(TILES, "view_5_p2_back.png"), elev=HT * 0.08)
    show_form(3)
    VH.render_still(cam, -35, Vector((0, 0, HT * 0.52)), HT * 2.6, os.path.join(TILES, "view_6_p3_threeq.png"), elev=HT * 0.05)
    VH.render_still(cam, 0, Vector((0, 0, HT * 0.52)), HT * 2.6, os.path.join(TILES, "view_7_p3_front.png"), elev=HT * 0.05)
    show_form(2)
    VH.render_still(cam, -20, Vector((0, -0.1, H * 0.62)), H * 1.0, os.path.join(TILES, "close_3_p2_chest.png"), elev=0)
    show_form(3)
    VH.render_still(cam, -25, Vector((0, -0.1, H * 0.92)), H * 0.9, os.path.join(TILES, "close_4_p3_head.png"), elev=0)
    show_form(1)
else:
    cam = BK.setup_preview(HT)
if not NOANIM:
    show_form(1)
    BK.render_actions(arm, HT, TILES, cam, n=10, only=ONLY)
    ad = arm.animation_data
    sc = bpy.context.scene
    for form, nm in ((2, "IdleAggro"), (3, "PhaseShift2"), (3, "Combo3")):
        if ONLY and nm not in ONLY:
            continue
        show_form(form)
        act = bpy.data.actions[nm]; ad.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        for k in range(10):
            f = int(round(f0 + (f1 - f0) * k / 9)); sc.frame_set(f)
            sc.render.filepath = os.path.join(TILES, f"act_9{form}_{nm}P{form}_{k}_f{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    ad.action = None
print("DONE", MODEL, flush=True)
