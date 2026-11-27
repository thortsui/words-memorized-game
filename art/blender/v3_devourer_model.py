"""v3 噬語魔王 boss_devourer（最終 Boss，三階）重建。依 art/v3/specs/boss_devourer.md（比例表、材質表、細節、型態部件、X3_ 清單）。
參考圖：art/reference/v2/devourer_p1/p2/p3.jpg（左右鏡像：本模型左手符紋、右手握劍）。
建模單位：公尺，H（角尖到靴底）＝3.9 m（＝遊戲縮放身高，載入後縮放約 1.0）。顱頂 0.86H。

用法：blender --background --factory-startup --python v3_devourer_model.py -- [--quick] [--noanim] [--only A,B]
  --quick：不烘焙（代表色），用來快速看造型。
輸出：art/blender/export_raw/boss_devourer.glb、.clipmeta.json、art/blender/source/v3_devourer.blend
"""
import bpy, bmesh, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from soul_humanoid_lib import *
from soul_humanoid_parts import *
import soul_humanoid_bake as BK
from soul_humanoid_anim import Rig, W, HW
import v3_devourer_hum as VH

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOANIM = "--noanim" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_devourer"
BAKEKEY = "v3_devourer"
ROOT = os.path.dirname(os.path.dirname(HERE))
TMP = os.path.join(ROOT, "art", "v3", "tmp", "devourer")
VH.TEXV3 = os.path.join(TMP, "tex")
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v3_devourer.blend" if not QUICK else "v3_devourer_quick.blend")
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

HT = 3.9                      # 全高（角尖）
HB = 0.86 * HT                # 顱頂（Body 的 H）


def h(x):
    return x * HT


reset_scene()
body = Body(H=HB, bulk=1.0, wf=1.357, head=0.321, hz=0.55, neck=0.0408, limb=1.07, arm_a=55, arm_len=1.0924)
U = body.U; R = body.R; RL = body.RL; j = body.j
# ---- 依 spec §1 比例表改寫軀幹與四肢截面（半徑，公尺）
TOR = [(0.40, 0.29, 0.22, 0.0, 0.010), (0.43, 0.40, 0.27, 0.0, 0.010), (0.47, 0.425, 0.285, 0.0, 0.0), (0.51, 0.375, 0.262, 0.0, -0.005),
       (0.555, 0.332, 0.252, 0.0, -0.010), (0.60, 0.400, 0.272, 0.0, -0.015), (0.65, 0.468, 0.292, 0.0, -0.020),
       (0.70, 0.470, 0.276, 0.0, -0.012), (0.735, 0.405, 0.236, 0.0, 0.0), (0.755, 0.200, 0.170, 0.0, 0.010), (0.79, 0.118, 0.118, 0.0, 0.015)]
body.torso = Surf(V(0, 0, 0), Z, [(h(z), rx, ry, du, dv) for z, rx, ry, du, dv in TOR])
La, Lf = body.ua_len, body.fa_len
body.uarm = Surf(j["UpperArmL"], body.ud, [(-0.02, 0.118, 0.118, 0, 0), (La * 0.4, 0.107, 0.107, 0, 0), (La, 0.095, 0.092, 0, 0)])
body.farm = Surf(j["ForearmL"], body.fd, [(0, 0.100, 0.100, 0, 0), (Lf * 0.28, 0.114, 0.110, 0, 0), (Lf * 0.75, 0.098, 0.094, 0, 0), (Lf, 0.074, 0.074, 0, 0)])
# ↑ 前臂肉身略粗於 spec 0.048H，讓外輪廓（護臂）達 0.068H（第 1 輪審查：前臂外輪廓細 12–21%）
Lt, Ls = body.th_len, body.sh_len
body.thigh = Surf(j["ThighL"], (j["ShinL"] - j["ThighL"]), [(-0.03, 0.19, 0.19, 0, 0), (Lt * 0.3, 0.192, 0.192, 0, 0), (Lt * 0.6, 0.19, 0.19, 0, 0), (Lt * 0.85, 0.165, 0.168, 0, 0), (Lt, 0.145, 0.145, 0, 0)])
body.shin = Surf(j["ShinL"], (j["FootL"] - j["ShinL"]), [(0, 0.13, 0.13, 0, 0), (Ls * 0.26, 0.135, 0.145, 0, -0.03), (Ls * 0.62, 0.10, 0.11, 0, -0.01),
                                                       (Ls * 0.9, 0.088, 0.09, 0, 0), (Ls, 0.088, 0.092, 0, 0)])
body.set_grip(0.043)
print("JOINTS", {k: tuple(round(c, 3) for c in v) for k, v in j.items() if k in ("Hips", "UpperArmL", "ForearmL", "HandL", "ThighL", "ShinL", "FootL", "Head", "Neck")}, flush=True)

Builder.HIRES = False          # 面數預算：關掉共用 lib 的自動加倍細分（細節靠烘焙法線）
B = Builder()
rnd = random.Random(7)
TX = VH.TEXV3


def T(n):
    return os.path.join(TX, n)


# ---------------------------------------------------------------- 材質（spec §2）
def srgb(hx):
    c = [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


D3 = VH.define_mat3
INKC = srgb("#0b0a0f")
STREAK = dict(img=T("dv_streak.png"), size=0.9, amount=0.55, col=INKC, rough=0.28, depth=0.45)
# 舊金浮雕板甲：底 #8a6a2a、亮邊 #c9a24a、凹處 #2a2010；粗糙 0.35–0.55、金屬 0.95
# 素板（錘紋、暗金、板緣 0.01H 寬的磨亮金邊、黑墨流）
D3("gold", "A", tex="Metal024", size=0.5, U=1.0, val=0.55, sat=0.0, tint=srgb("#6e5424"), rough=0.5, metal=0.9, wear=1.0, wear_r=0.022,
   wear_col=srgb("#c9a24a"), dirt=0.9, dirt_col=srgb("#120d06"), bump=0.8, bump_dist=0.006, ao_shade=0.65, hammer=(9.0, 0.5), streak=STREAK)
BK.SRC["gold"]["qmetal"] = 0.9
# 嵌板（胸甲中央、肩甲圓牌、護膝圓飾、護臂帶、大腿甲前片）：長 S 形卷草浮雕
D3("goldP", "A", tex="Metal024", size=0.5, U=1.0, val=0.6, sat=0.0, tint=srgb("#7a5e28"), rough=0.42, metal=0.95, wear=1.0, wear_r=0.012,
   wear_col=srgb("#d6b05a"), dirt=0.9, dirt_col=srgb("#120d06"), bump=1.0, bump_dist=0.006, ao_shade=0.65,
   pat=dict(img=T("dv_vine_h.png"), size=0.30, depth=1.6, recess=srgb("#1e170b"), raised=srgb("#d0a84e"), k=0.55), streak=dict(STREAK, amount=0.3))
BK.SRC["goldP"]["qmetal"] = 0.9
# 甲內層：暗鐵鎖子甲（腋下、肘窩、膝窩）
D3("chainD", "A", tex="Chainmail004", size=0.20, U=1.0, tint=srgb("#2a2a2a"), metal=0.9, rough=0.6, rust=0.15, rust_tint=(0.2, 0.14, 0.11),
   dirt=1.0, bump=1.0, bump_dist=0.008, ao_shade=0.75)
D3("ironD", "A", tex="Metal024", size=0.5, U=1.0, val=0.35, sat=0.2, tint=srgb("#3a3a3a"), metal=0.9, rough=0.5, wear=1.0,
   wear_col=srgb("#6a6a68"), dirt=0.8, bump=0.6)
D3("void", "A", color=(0.004, 0.003, 0.003), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.0)
# 骨（骷髏）：#b8ac90，凹處 #3a3024，骨面孔洞、裂紋
D3("bone", "B", color=srgb("#a89c80"), rough=0.6, metal=0.0, dirt=1.0, dirt_col=srgb("#3a3024"), wear=0.5, wear_col=srgb("#d8ceb4"),
   bump=0.8, bump_dist=0.004, ao_shade=0.75, crack=(14.0, 0.035, 0.6), seed=3.0)


def horn_src(g, sx, sy, col, hs, rs):
    """角：src.x＝根(0)→尖(1)，src.y＝沿角長度（公尺）。環節紋往尖端漸密；米黃→褐→黑尖。"""
    c0, c1, c2 = srgb("#6e6452"), srgb("#3e3428"), srgb("#0a0908")
    ca = g.mix(g.ramp(sx, 0.0, 0.30), c0, c1)
    cc = g.mix(g.ramp(sx, 0.30, 0.66), ca, c2)          # 下 1/3 之後明確漸黑
    freq = g.math("MULTIPLY", g.math("ADD", 1.0, g.math("MULTIPLY", sx, 1.2)), 2 * math.pi / 0.026)
    ph = g.math("MULTIPLY", sy, freq)
    ring = g.math("POWER", g.math("ABSOLUTE", g.math("SINE", ph)), 0.45)          # 1＝環脊、0＝環溝
    groove = g.math("SUBTRACT", 1.0, ring)
    col = g.mix(g.math("MULTIPLY", groove, 0.35), cc, srgb("#2a2218"))
    nz = g.noise(40.0, 4, 0.6, 5.0)
    hs = g.math("ADD", g.math("MULTIPLY", ring, 1.0), g.math("MULTIPLY", nz, 0.25))
    rs = g.math("ADD", 0.55, g.math("MULTIPLY", sx, 0.15))
    return col, hs, rs


D3("horn", "B", color=(0.5, 0.45, 0.36), rough=0.6, metal=0.0, dirt=0.6, dirt_col=srgb("#1a1410"), bump=1.0, bump_dist=0.006, ao_shade=0.7,
   srcfn=horn_src, crack=(9.0, 0.02, 0.4), streak=dict(STREAK, amount=0.25))
BK.SRC["horn"]["tint"] = srgb("#a09070")


def blade_src(g, sx, sy, col, hs, rs):
    """劍：src.x＝截面周長方向、src.y＝沿劍長。細刮痕（兩組斜向拉長雜訊）、縱向細紋。"""
    N, L = g.N, g.L
    out = []
    for k, (a, b) in enumerate(((260.0, 9.0), (9.0, 260.0))):
        cmb = N.new("ShaderNodeCombineXYZ")
        L.new(g.math("ADD", g.math("MULTIPLY", sx, a), g.math("MULTIPLY", sy, b * 0.4)), cmb.inputs[0])
        L.new(g.math("ADD", g.math("MULTIPLY", sy, b), g.math("MULTIPLY", sx, a * 0.05)), cmb.inputs[1])
        nn = N.new("ShaderNodeTexNoise"); nn.inputs["Scale"].default_value = 1.0; nn.inputs["Detail"].default_value = 2.0
        L.new(cmb.outputs[0], nn.inputs["Vector"])
        out.append(g.ramp(nn.outputs["Fac"], 0.62, 0.70))
    scr = g.math("MAXIMUM", out[0], out[1])
    scr = g.math("MULTIPLY", scr, g.ramp(g.noise(4.0, 3, 0.5, 21.0), 0.45, 0.6))
    col = g.mix(g.math("MULTIPLY", scr, 0.35), col, srgb("#d0d0c8"))
    hs = g.math("SUBTRACT", hs, g.math("MULTIPLY", scr, 0.5))
    rs = g.mixf(scr, rs, 0.22)
    return col, hs, rs


D3("blade", "B", tex="Metal024", size=0.6, U=1.0, val=1.25, sat=0.1, tint=srgb("#a8a8a2"), metal=1.0, rough=0.38, rust=0.14,
   rust_tint=(0.30, 0.17, 0.10), wear=1.0, wear_r=0.012, wear_col=srgb("#e0e0d8"), dirt=0.4, bump=0.7, seed=4.0, srcfn=blade_src)
BK.SRC["blade"]["qmetal"] = 0.9
# 髒亞麻（腰帶 #a89a7c、前擺 #b8a987 較白＋縱向黑墨垂流）
D3("linen", "B", tex="Fabric030", size=0.16, U=1.0, val=2.9, sat=0.25, tint=srgb("#a89a7c"), rough=0.92, metal=0.0, dirt=0.6, bump=1.0,
   stain=0.3, stain_col=srgb("#5a4a36"), weave=(900.0, 0.5))
D3("tabard", "B", tex="Fabric030", size=0.16, U=1.0, val=3.3, sat=0.2, tint=srgb("#b8a987"), rough=0.92, metal=0.0, dirt=0.5, bump=1.0,
   stain=0.2, stain_col=srgb("#5a4a36"), weave=(900.0, 0.5), mud=(0.3, 1.2, 0.6), mud_col=srgb("#3a3026"),
   streak=dict(img=T("dv_streak.png"), size=0.7, amount=0.55, col=INKC, rough=0.35, depth=0.2))
D3("lining", "B", tex="Fabric030", size=0.2, U=1.0, val=1.2, sat=0.6, tint=srgb("#3a1410"), rough=0.92, metal=0.0, dirt=0.5, bump=0.9,
   weave=(700.0, 0.5))
# 棕皮（皮帶、劍柄纏皮）＃3a2a1e／#4a2a1e
D3("leather", "B", tex="Leather026", size=0.25, U=1.0, val=1.6, tint=srgb("#4a3424"), rough=0.68, metal=0.0, dirt=0.9, wear=0.5,
   wear_col=srgb("#6a4a32"), bump=0.9)
D3("iron", "B", tex="Metal024", size=0.5, U=1.0, val=0.40, sat=0.3, tint=srgb("#3a3a3a"), rough=0.5, metal=0.9, rust=0.25, rust_tint=(0.25, 0.17, 0.12),
   wear=1.0, wear_col=srgb("#5a5a58"), dirt=0.8, bump=0.6, seed=7.0)
BK.SRC["iron"]["qmetal"] = 0.9
D3("redcord", "B", tex="Fabric030", size=0.08, U=1.0, val=1.4, sat=1.0, tint=srgb("#7a1e18"), rough=0.85, metal=0.0, dirt=0.4, bump=0.8)
D3("scrollp", "B", tex="Fabric030", size=0.3, U=1.0, val=3.6, sat=0.1, tint=srgb("#d2c3a0"), rough=0.86, metal=0.0, dirt=0.7, bump=0.4)
# 符紋手：鐵手套 #2a2420＋紅皮手心 #5a1a14
D3("glove", "B", tex="Leather026", size=0.2, U=1.0, val=0.8, tint=srgb("#2a2420"), rough=0.6, metal=0.3, dirt=0.8, bump=0.8)
D3("palm", "B", tex="Leather026", size=0.12, U=1.0, val=1.4, sat=0.8, tint=srgb("#5a1a14"), rough=0.65, metal=0.0, dirt=0.6, bump=0.8)
D3("claw", "B", color=srgb("#141210"), rough=0.35, metal=0.0, dirt=0.2, bump=0.3)
# 三階裂肉 #2a1414
D3("mawflesh", "B", tex="Leather026", size=0.12, U=1.0, val=0.9, sat=0.8, tint=srgb("#5a1410"), rough=0.55, metal=0.0, dirt=1.0, dirt_col=(0.01, 0.0, 0.0), bump=1.0, ao_shade=1.0)
D3("flesh", "B", tex="Leather026", size=0.15, U=1.0, val=0.9, sat=0.6, tint=srgb("#3a1a16"), rough=0.8, metal=0.0, dirt=1.0, bump=1.0)
VH.define_paper("paper")
RED = srgb("#ff3a2a")
VH.define_glow("g_eye", RED, 4.0, final="Glow_Eye")
VH.define_glow("g_rune", RED, 3.5, final="Glow_Rune")
VH.define_glow("g_weapon", (0.55, 0.02, 0.01), 0.8, final="Glow_Weapon")
VH.define_glow("p2_script", RED, 2.2, final="P2_Glow_Script")
VH.define_glow("p2_maw", (0.75, 0.03, 0.01), 2.4, final="P2_Glow_Maw", base=(0.10, 0.0, 0.0))
VH.define_glow("p2_page", (1.0, 0.16, 0.03), 4.0, final="P2_Glow_PageEdge")
VH.define_glow("p2_blade", RED, 2.6, final="P2_Glow_Blade")
VH.define_glow("p3_halo", RED, 3.4, final="P3_Glow_Halo")
VH.define_glow("p3_cracks", RED, 2.6, final="P3_Glow_Cracks")
VH.define_glow("p3_fleshnet", RED, 2.2, final="P3_Glow_FleshNet", tex=T("dv_cracks.png"))
VH.define_glow("p3_glyph", RED, 3.0, final="P3_Glow_Glyph")
VH.define_glow("p3_glyphG", (1.0, 0.62, 0.18), 2.6, final="P3_Glow_GlyphGold")
VH.define_glow("p3_eyes", (1.0, 0.10, 0.03), 3.8, final="P3_Glow_Eyes")
VH.define_ink("p3_ink", color=INKC, alpha=1.0, emit=(0.0, 0.0, 0.0), emit_strength=0.0, final="P3_Ink")
VH.define_glow("p3_inkedge", (0.23, 0.008, 0.005), 1.2, final="P3_Glow_InkEdge")
VH.define_ink("p3_inkcore", color=(0.004, 0.003, 0.004), alpha=1.0, emit=(0.0, 0.0, 0.0), emit_strength=0.0, final="P3_InkCore")


# ---------------------------------------------------------------- 小工具
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


def ribbon(name, pts, nrms, width, raise_, mat, w, segs=4, lift=0.0):
    """貼在表面上的扁平浮起條（卷草浮雕、墨流痕、紅紋）。"""
    P = [p + n * (lift + raise_ * 0.5) for p, n in zip(pts, nrms)]
    return B.tube(name, P, [(width * 0.5, raise_ * 0.5)] * len(P) if not callable(width) else [(width(k) * 0.5, raise_ * 0.5) for k in range(len(P))],
                  segs, mat, w, flat=None, up=nrms[len(nrms) // 2], cap=True, sharp=60)


def flat_tube(name, pts, nrms, widths, thick, mat, w):
    """扁平帶：截面寬方向＝沿表面（垂直於法線）。"""
    n = len(pts)
    obs_pts = []
    radii = []
    for k in range(n):
        radii.append((thick * 0.5, widths[k] * 0.5))
    # flat 參數給「寬」方向 = 法線（tube 的 e1 是 rx 方向），所以 rx＝厚度、ry＝寬度
    return B.tube(name, pts, radii, 4, mat, w, flat=nrms[n // 2], cap=True, sharp=60)


def cone(name, base, d, ln, r0, mat, w, segs=6, bend=None):
    d = d.normalized()
    mid = base + d * ln * 0.55 + (bend * ln * 0.12 if bend is not None else V(0, 0, 0))
    return B.tube(name, [base - d * r0 * 0.3, mid, base + d * ln], [r0, r0 * 0.5, 0.0012], segs, mat, w, sharp=30)


# ================================================================ 軀幹
Z_WAIST = h(0.555)


def cu_off(ang, v):
    a = angn(ang)
    front = math.exp(-(a / 62) ** 2)
    keel = 0.026 * math.exp(-(a / 7) ** 2) * math.sin(math.pi * clamp(v * 1.05))
    globe = 0.020 * front * math.sin(math.pi * clamp((v - 0.10) / 0.80)) ** 1.2
    flare = 0.016 * (1 - smooth(v / 0.12))
    return 0.034 + keel + globe + flare


CU_NU, CU_NV = 30, 10
CU_T0 = h(0.548)
CU_TN = h(0.735); CU_TA = h(0.69)


def cu_t1(ang):
    a = angn(ang)
    hole = math.exp(-((abs(a) - 90) / 40) ** 2)
    return lerp(CU_TN, CU_TA, hole)


def cu_pt(ang, z, lift=0.0):
    t1 = cu_t1(ang)
    v = clamp((z - CU_T0) / (t1 - CU_T0))
    p = body.torso.pt(z, ang, cu_off(ang, v) + lift)
    n = (body.torso.pt(z, ang, cu_off(ang, v) + lift + 0.01) - p).normalized()
    return p, n


def cuirass_shell(name, mat, w, holes=None, off_add=0.0, rim=0.012):
    def fn(u, v):
        ang = u * 360
        t1 = cu_t1(ang)
        z = lerp(CU_T0, t1, v)
        return body.torso.pt(z, ang, cu_off(ang, v) + off_add)
    inside = [V(0, 0, z) for z in np.linspace(CU_T0, CU_TN, 6)]
    return B.grid(name, CU_NU, CU_NV, fn, mat, w, inside, closed_u=True, rim=rim, holes=holes, sharp=45)


B.shell("UnderTorso", body.torso, h(0.41), h(0.79), 0, 360, 14, 8, "chainD", body.w_torso(), off=0.0, cap0=True, texel=0.4)
CUI = cuirass_shell("Cuirass", "gold", "Spine2")
chest_x3 = [CUI]
GOR = gorget(B, body, "gold", off=0.014)
# 高領（護頸外翻的板，包住下顎兩側，前方開口）
def collar_fn(u, v):
    a = math.radians(lerp(-140, 140, u))
    z = lerp(h(0.735), h(0.795), v)
    r0 = lerp(0.21, 0.27, v ** 1.4)
    ry = lerp(0.19, 0.25, v ** 1.4)
    return V(math.sin(a) * r0, 0.03 + math.cos(a) * ry, z + 0.025 * math.cos(a) * v)


COL = B.grid("Collar", 20, 3, collar_fn, "gold", {"Spine2": 0.6, "Neck": 0.4}, [V(0, 0.03, h(0.76))], rim=0.012, sharp=45)
# 腰：fauld（甲裙）
_, zf = fauld(B, body, "gold", n=2, t_top=(h(0.535) - body.hzv) / body.span, h=0.048, off=0.040, step=0.008, rivet_mat="gold")
B.both(tasset(B, body, "gold", zf + 0.02, length=0.22, a0=12, a1=66, off=0.046, rivet_mat="gold"))
B.both(tasset(B, body, "gold", zf + 0.02, length=0.20, a0=72, a1=124, off=0.048, rivet_mat="gold", name="TassetSide"))
B.both(tasset(B, body, "gold", zf + 0.01, length=0.16, a0=130, a1=170, off=0.046, name="TassetBack"))
mail_skirt(B, body, "chainD", zf + 0.02, h(0.385), flare=0.035, rag=0.04, seed=8)

# ---- 卷草浮雕主線（幾何）：胸甲兩側 S 形渦卷＋縱稜旁的邊框；二階沿同一路徑疊紅光
SCROLLS = []          # (名稱, 點列, 法線列, 骨, 是否胸甲)


def spiral_path(c_ang, c_z, r_m, turns, ccw, a0, n=17, tail=None):
    """在胸甲表面上的渦卷：中心（角度, 高度）、半徑（公尺）。回傳 [(ang, z)]。"""
    out = []
    rad_per_m = 180 / math.pi / 0.47
    for k in range(n):
        t = k / (n - 1)
        a = a0 + (1 if ccw else -1) * t * turns * 2 * math.pi
        r = r_m * (1 - 0.82 * t) ** 1.05
        out.append((c_ang + math.cos(a) * r * rad_per_m, c_z + math.sin(a) * r))
    if tail:
        out = tail + out
    return out


PANEL_LIFT = 0.009


def add_scroll_on_cuirass(name, pts_az, width=0.013, raise_=0.010):
    P = []; Nn = []
    for a, z in pts_az:
        p, n = cu_pt(a, z, lift=PANEL_LIFT)
        P.append(p); Nn.append(n)
    P = catmull(P, max(len(P), 7))
    Nn2 = []
    for p in P:
        a = math.degrees(math.atan2(p.x, -p.y))
        Nn2.append(cu_pt(a, p.z)[1])
    P2 = []
    for p, n in zip(P, Nn2):
        a = math.degrees(math.atan2(p.x, -p.y))
        q, _ = cu_pt(a, p.z, lift=PANEL_LIFT)
        P2.append(q)
    ob = ribbon(name, P2, Nn2, width, raise_, "goldP", "Spine2", segs=4)
    SCROLLS.append((name, P2, Nn2, "Spine2"))
    chest_x3.append(ob)
    return ob


# 胸甲中央嵌板（盾形，卷草只在這裡；板緣有亮邊框）
PZ0, PZ1, PA = h(0.585), h(0.718), 30.0


def panel_fn(u, v):
    z = lerp(PZ0, PZ1, v)
    half = PA * (0.55 + 0.45 * smooth(v / 0.45))
    a = lerp(-half, half, u)
    return cu_pt(a, z, lift=PANEL_LIFT * 0.6)[0]


chest_x3.append(B.grid("ChestPanel", 12, 8, panel_fn, "goldP", "Spine2", [V(0, 0, z) for z in (PZ0, PZ1)], rim=0.010, sharp=45))
# 腹部疊片（分片感）
for k, (z0, z1) in enumerate(((CU_T0 + 0.01, CU_T0 + 0.10), (CU_T0 + 0.085, CU_T0 + 0.175))):
    def ab_fn(u, v, z0=z0, z1=z1, k=k):
        a = lerp(-75, 75, u)
        z = lerp(z0, z1, v)
        return cu_pt(a, z, lift=0.006 + 0.006 * (1 - k) + 0.004 * (1 - v))[0]
    chest_x3.append(B.grid(f"AbLame{k}", 14, 2, ab_fn, "gold", "Spine2", [V(0, 0, z0)], rim=0.008, sharp=45))
for sx in (1, -1):
    s = "L" if sx > 0 else "R"
    add_scroll_on_cuirass(f"ScrA{s}", spiral_path(sx * 15, h(0.677), 0.058, 1.6, sx > 0, math.radians(200 if sx > 0 else -20)))
    add_scroll_on_cuirass(f"ScrC{s}", spiral_path(sx * 11, h(0.612), 0.040, 1.4, sx < 0, math.radians(-90)))
    add_scroll_on_cuirass(f"ScrStem{s}", [(sx * 5, h(0.712)), (sx * 14, h(0.705)), (sx * 24, h(0.69)), (sx * 26, h(0.655)), (sx * 21, h(0.63)),
                                          (sx * 22, h(0.605)), (sx * 18, h(0.595))], width=0.010)
# 胸甲中央縱稜旁兩條細線
for sx in (1, -1):
    add_scroll_on_cuirass(f"ScrKeel{sx}", [(sx * 4.5, z) for z in np.linspace(PZ0 + 0.03, PZ1 - 0.02, 5)], width=0.008, raise_=0.007)
# 胸甲鉚釘（腰緣）
pts = []
for a in range(-150, 181, 25):
    p, n = cu_pt(a, CU_T0 + 0.022)
    pts.append((p + n * 0.006, n))
chest_x3.append(B.rivets("CuirassRivets", pts, "gold", "Spine2", r=0.012))
VH.xmark(chest_x3, "X3_ChestPlate")

# ---- 腰：亞麻腰帶繞兩圈＋結、斜跨皮帶、垂鍊＋三角墜、卷軸束
def sash(name, z, hh, off, tilt, tdir, w, seed):
    """繞腰的亞麻布：鼓起的截面＋斜向褶痕＋上下緣起伏（不是平帶）。"""
    rs = random.Random(seed)
    ph = rs.uniform(0, 6.28)

    def fn(u, v):
        ang = u * 360
        a = math.radians(ang)
        fold = math.sin(a * 6 + ph + v * 1.6) * 0.6 + math.sin(a * 13 + ph * 2) * 0.4
        zz = z - tilt * math.cos(a - math.radians(tdir)) + (v - 0.5) * hh * (1 - 0.18 * abs(fold)) + 0.008 * fold * (v - 0.5)
        o = off + 0.012 * math.sin(math.pi * v) + 0.006 * fold * math.sin(math.pi * v)
        return body.torso.pt(zz, ang, o)
    ob = B.grid(name, 30, 3, fn, "linen", w, [V(0, 0, z)], closed_u=True, sharp=50)
    ob["cloth"] = 0.006
    return ob


sash("Sash1", Z_WAIST + 0.02, 0.105, 0.040, 0.0, 0, {"Spine": 0.5, "Hips": 0.5}, 3)
sash("Sash2", Z_WAIST - 0.07, 0.095, 0.046, 0.022, 60, {"Spine": 0.3, "Hips": 0.7}, 4)
# 結（左前）＋兩條垂下的布尾
kn = body.torso.pt(Z_WAIST - 0.02, 38, 0.075)
knn = body.torso.nrm(Z_WAIST - 0.02, 38)
B.ellipsoid("SashKnot", kn, (Z.cross(knn).normalized(), Z, knn), (0.055, 0.045, 0.035), 10, 5, "linen", "Hips")
for q, (dx, ln) in enumerate(((-0.03, 0.34), (0.035, 0.27))):
    side = Z.cross(knn).normalized()
    top = kn + side * dx
    pts_ = [top, top - Z * ln * 0.4 + knn * 0.03 + side * 0.01, top - Z * ln + knn * 0.05 + side * (0.03 * (1 if q else -1))]
    ob = B.tube(f"SashTail{q}", pts_, [(0.045, 0.006), (0.05, 0.006), (0.055, 0.005)], 6, "linen", w_skirt(body, Z_WAIST, Z_WAIST - 0.4, 0.5), flat=knn, exp=4)
    ob["cloth"] = 0.004
belt(B, body, Z_WAIST - 0.13, "leather", "Hips", h=0.032, thick=0.009, off=0.062, tilt=0.05, tilt_dir=110, name="Belt2", nu=32)
# 鐵扣（環形，不是方塊）
bkc = body.torso.pt(Z_WAIST - 0.13 + 0.05 * U * math.cos(math.radians(-20 - 110)) * -1, -20, 0.068 * R + 0.012)
bkn = body.torso.nrm(Z_WAIST - 0.13, -20); bke = Z.cross(bkn).normalized()
B.tube("Buckle", [bkc + (bke * math.cos(t) * 0.034 + Z * math.sin(t) * 0.028) for t in np.linspace(0, 2 * math.pi, 13)], [0.006] * 13, 5, "iron", "Hips", cap=False)
B.tube("BuckleTongue", [bkc - bke * 0.03, bkc + bke * 0.03 + bkn * 0.004], [0.004, 0.003], 4, "iron", "Hips")
# 垂鍊：從腰帶右前垂到 0.30H，末端三角墜
WSK = w_skirt(body, Z_WAIST, h(0.28), 0.45)
ch_top = body.torso.pt(Z_WAIST - 0.10, -24, 0.07)
ch_pts = [ch_top + V(0.01 * math.sin(k * 0.7), -0.03 * math.sin(math.pi * k / 14), -k * (ch_top.z - h(0.30)) / 14) for k in range(15)][::2]
chain_links(B, ch_pts, "iron", WSK, link_r=0.030, wire=0.0085, name="HangChain")
pend = ch_pts[-1]
B.tube("Pendant", [pend + V(0, 0, -0.005), pend + V(0, 0, -0.06), pend + V(0, 0, -0.115)], [(0.06, 0.012), (0.04, 0.012), (0.004, 0.006)], 3, "iron", WSK, flat=X, exp=2)
# 斜掛垂弧鍊（腰前）
sw = []
for q in range(16):
    s_ = q / 15
    a = lerp(-70, 55, s_)
    sw.append(body.torso.pt(Z_WAIST - 0.12 - 0.20 * math.sin(math.pi * s_), a, 0.09 + 0.05 * math.sin(math.pi * s_)))
pass  # （垂弧鍊移除：面數預算給書頁）
# 卷軸 ×4（左腰，被鍊子綁成一束；紙卷＋紅繩，卷口有螺旋紙層）
SCW = w_skirt(body, Z_WAIST, Z_WAIST - 0.5, 0.35)
bc = body.torso.pt(Z_WAIST - 0.18, 62, 0.14)
bn_ = body.torso.nrm(Z_WAIST - 0.18, 62)
bside = Z.cross(bn_).normalized()
for q, (ox, oy, tilt, ln) in enumerate(((-0.045, 0.0, 6, 0.36), (0.04, 0.01, -8, 0.33), (0.0, 0.05, 3, 0.38), (0.075, 0.045, -14, 0.30))):
    c = bc + bside * ox + bn_ * oy
    ax = (Z * math.cos(math.radians(tilt)) + bside * math.sin(math.radians(tilt))).normalized()
    r_ = 0.039
    B.tube(f"Scroll{q}", [c - ax * ln * 0.5, c + ax * ln * 0.5], [r_, r_], 12, "scrollp", SCW, cap=True)
    for e in ((1,) if q % 2 == 0 else ()):
        endc = c + ax * (e * (ln * 0.5 + 0.002))
        e1 = ax.orthogonal().normalized(); e2 = ax.cross(e1)
        sp = [endc + (e1 * math.cos(t) + e2 * math.sin(t)) * (r_ * 0.95 * (1 - t / (2.6 * 2 * math.pi))) for t in np.linspace(0, 2.6 * 2 * math.pi, 14)]
        B.tube(f"ScrollSpiral{q}{e}", sp, [(0.0035, 0.002)] * 14, 3, "leather", SCW, cap=False)
    for k in (((-0.22,) if q % 2 else (0.2,)) if q < 2 else ()):
        cc = c + ax * ln * k
        e1 = ax.orthogonal().normalized(); e2 = ax.cross(e1)
        ring = [cc + (e1 * math.cos(t) + e2 * math.sin(t)) * (r_ + 0.006) + ax * (0.006 * t) for t in np.linspace(0, 4 * math.pi, 15)]
        B.tube(f"ScrollCord{q}{k}", ring, [0.0055] * 15, 3, "redcord", SCW, cap=False)
bund = [bc + bside * (0.11 * math.cos(t)) + bn_ * (0.05 + 0.06 * math.sin(t)) + Z * 0.02 for t in np.linspace(-1.7 * math.pi, 0.3 * math.pi, 6)]
chain_links(B, bund, "iron", SCW, link_r=0.018, wire=0.006, name="ScrollChain")
# 前擺（髒亞麻，0.555H→0.08H，寬 0.10H，縱褶，撕裂下緣）
zb = Z_WAIST - 0.04
tf_pts = [V(0, -0.30, zb), V(0, -0.36, zb - 0.55), V(0, -0.37, zb - 1.15), V(0, -0.35, zb - 1.80)]
tf_names = chain_names("TabardF", 3)
cloth_panel(B, "Tabard", lambda u: body.torso.pt(zb, lerp(-24, 24, u), 0.095), lambda u: V(math.sin(math.radians(lerp(-24, 24, u))) * 0.5, -1, 0).normalized(),
            zb - h(0.08), "tabard", w_chain_pts("Hips", tf_names, tf_pts), nu=10, nv=11, flare=0.035, rag=0.10, deep=0.25, fold_amp=0.02,
            fold_n=1.3, holes=0.03, seed=41, spread=0.08)

# ================================================================ 手臂
def _horn_param(co, P, L_):
    best = (1e9, 0.0)
    acc = 0.0
    for k in range(len(P) - 1):
        d = P[k + 1] - P[k]
        s = clamp((co - P[k]).dot(d) / max(d.length_squared, 1e-9))
        q = P[k] + d * s
        dist = (co - q).length
        if dist < best[0]:
            best = (dist, acc + s * d.length)
        acc += d.length
    return (best[1] / max(L_, 1e-6), best[1])


for _nm, _sf, _t0, _t1, _w in (("UnderUArm", body.uarm, -0.02, La + 0.012, body.w_elbow()), ("UnderFArm", body.farm, -0.012, Lf, body.w_elbow())):
    B.both(B.shell(_nm, _sf, _t0, _t1, 0, 360, 8, 4, "chainD", _w, off=0.0, texel=0.8))
PSIZE = 1.04
pl = pauldron(B, body, "gold", size=PSIZE, lames=0, haute=0.10, rivet_mat="gold", tilt=0.6)
# 肩甲 3 層疊片（自建）：往外、往下蓋住上臂到 0.69H，每層有亮邊
for k in range(3):
    ta, tb = 0.0 + k * 0.075, 0.13 + k * 0.075
    pl.append(B.shell(f"PauldronLame{k}", body.uarm, ta, tb, 90 - 128, 90 + 128, 14, 2, "gold", {"ShoulderL": 0.3, "UpperArmL": 0.7} if k == 0 else "UpperArmL",
                      off=lambda u, v, ang, t, k=k: 0.085 - k * 0.014 + 0.028 * v + 0.012 * math.exp(-((ang - 90) / 60) ** 2), rim=0.012))
B.both(pl)
arm_parts = arm_armor(B, body, "gold", rivet_mat="gold", cuff=0.052, ridge=0.006, rerebrace=False)
arm_parts.append(B.shell("VambraceBand", body.farm, Lf * 0.36, Lf * 0.52, 0, 360, 12, 2, "goldP", "ForearmL", off=0.030, rim=0.008))
REREOFF = lambda u, v, ang, t: 0.036 + 0.008 * abs(v - 0.5) * 2          # 上臂甲外徑 0.075H
arm_parts.append(B.shell("Rerebrace", body.uarm, La * 0.45, La * 0.90, 0, 360, 12, 3, "gold", "UpperArmL", off=REREOFF, rim=0.010))
B.both(arm_parts)
VH.xmark([o for o in B.parts if o.name == "Rerebrace"], "X3_ArmPlateL")
# 肩甲圓牌（同心圓＋渦紋）、後掠刺（左 2 右 1）
pole = (body.uarm.u * 0.75 + Z * 0.6).normalized()
for sx in (1, -1):
    s = "L" if sx > 0 else "R"
    pp = (pole * 0.75 + FWD * 0.45).normalized()
    mc = j["UpperArmL"] + pp * 0.125 * RL * PSIZE + Z * 0.01
    m = V(mc.x * sx, mc.y, mc.z)
    pn = V(pp.x * sx, pp.y, pp.z)
    e1 = pn.orthogonal().normalized(); e2 = pn.cross(e1)
    wb = {"ShoulderL" if sx > 0 else "ShoulderR": 0.5, "UpperArmL" if sx > 0 else "UpperArmR": 0.5}
    B.ellipsoid(f"Medal{s}", m, (e1, e2, pn), (0.0975, 0.0975, 0.030), 18, 5, "goldP", wb, v0=0, v1=0.5, rim=0.008)
    for rr in (0.088, 0.055):
        ring = [m + pn * (0.028 * (1 - (rr / 0.1) ** 2) + 0.006) + (e1 * math.cos(t) + e2 * math.sin(t)) * rr for t in np.linspace(0, 2 * math.pi, 17)]
        B.tube(f"MedalRing{s}{rr}", ring, [(0.008, 0.006)] * 17, 3, "gold", wb, cap=False, flat=pn)
    sp = [m + pn * 0.03 + (e1 * math.cos(t) + e2 * math.sin(t)) * (0.035 * (1 - t / 13)) for t in np.linspace(0, 12, 18)]
    B.tube(f"MedalSpiral{s}", sp, [(0.0035, 0.004)] * 18, 3, "gold", wb, cap=False, flat=pn)
    spikes = ((0.27, 0.0), (0.24, 0.10)) if sx > 0 else ((0.26, 0.05),)
    for q, (ln, off_) in enumerate(spikes):
        base = V((j["UpperArmL"].x - 0.02 - off_) * sx, 0.06 + off_ * 0.5, j["UpperArmL"].z + 0.20 - off_ * 0.3)
        d = V(0.25 * sx, 0.55, 0.80).normalized()
        P = catmull([base, base + d * ln * 0.5 + V(0, 0.02, 0.0), base + d * ln + V(0, 0.08, -0.03)], 8)
        rad = [0.05 * (1 - 0.95 * (k / 7) ** 1.2) for k in range(8)]
        ob = B.tube(f"ShSpike{s}{q}", P, rad, 8, "horn", wb, cap=True)
        L_ = sum((P[k + 1] - P[k]).length for k in range(7))
        VH.src_uv(ob, B, fn=lambda co, P=P, L_=L_: _horn_param(co, P, L_))
body.set_grip(0.043)


# 鐵手套：右手握劍
RH = B.mirror_only(hand(B, body, "gold", mat_finger="iron"))
# 左手：符紋手（鐵手套＋紅皮手心、4 根黑爪、手腕紅環紋）
LH = hand(B, body, "glove", mat_finger="glove", open_amt=0.85)
Wl = j["HandL"]; ha, hv, hu = body.hand_a, body.hand_v, body.hand_u
pc = Wl + ha * 0.052 * RL - hu * 0.022 * RL
palm = B.ellipsoid("PalmPad", pc - hu * 0.004, (ha, hv, -hu), (0.06, 0.055, 0.010), 12, 4, "palm", "HandL", v0=0, v1=0.5)
GLYPHS = [[((0.0, 0.0), (0.0, 1.0)), ((0.0, 0.6), (0.6, 0.95))], [((0.0, 1.0), (0.5, 0.0)), ((0.5, 0.0), (0.8, 0.7))],
          [((0.1, 0.0), (0.1, 0.9)), ((0.1, 0.9), (0.7, 0.6)), ((0.4, 0.3), (0.8, 0.1))], [((0.0, 0.5), (0.8, 0.5)), ((0.4, 0.0), (0.3, 1.0))],
          [((0.0, 0.0), (0.4, 1.0)), ((0.4, 1.0), (0.8, 0.0))], [((0.2, 0.0), (0.2, 1.0)), ((0.6, 0.2), (0.6, 0.8))],
          [((0.0, 0.2), (0.8, 0.2)), ((0.0, 0.8), (0.8, 0.8)), ((0.4, 0.2), (0.4, 0.8))], [((0.1, 1.0), (0.1, 0.2)), ((0.1, 0.2), (0.5, 0.0)), ((0.5, 0.0), (0.8, 0.4))],
          [((0.0, 0.3), (0.4, 0.0)), ((0.4, 0.0), (0.8, 0.3)), ((0.4, 0.0), (0.4, 1.0))], [((0.0, 1.0), (0.8, 1.0)), ((0.8, 1.0), (0.2, 0.0))]]


def glyph(prefix, c, xd, yd, size, mat, w, gi, width=0.006, th=0.003, segs=4, cap=True):
    xd = xd.normalized(); yd = yd.normalized(); nd = xd.cross(yd)
    obs = []
    for si, (p0, p1) in enumerate(GLYPHS[gi % len(GLYPHS)]):
        pa = c + xd * ((p0[0] - 0.4) * size) + yd * ((p0[1] - 0.5) * size)
        pb = c + xd * ((p1[0] - 0.4) * size) + yd * ((p1[1] - 0.5) * size)
        obs.append(B.tube(f"{prefix}{si}", [pa, pb], [(th, width)] * 2, segs, mat, w, flat=nd, cap=cap))
    return obs


for gi in range(3):
    glyph(f"Palm{gi}", pc + hv * (gi - 1) * 0.034 - hu * 0.013, ha, hv, 0.030, "g_rune", "HandL", gi + 3, width=0.0035, th=0.0015)
B.tube("PalmRing", [pc + (ha * math.cos(t) + hv * math.sin(t)) * 0.052 - hu * 0.012 for t in np.linspace(0, 2 * math.pi, 17)], [(0.0015, 0.0035)] * 17, 4,
       "g_rune", "HandL", flat=hu, cap=False)
# 手腕紅環紋
WR = j["HandL"] - ha * 0.02
e1 = ha.orthogonal().normalized(); e2 = ha.cross(e1)
B.tube("WristRune", [WR + (e1 * math.cos(t) + e2 * math.sin(t)) * 0.092 for t in np.linspace(0, 2 * math.pi, 21)], [(0.006, 0.0025)] * 21, 4, "g_rune", "ForearmL",
       flat=ha, cap=False)
# 4 根黑爪（指尖）
for o in LH:
    if o.name.startswith("Finger"):
        vs = o.data.vertices
        tip = max(vs, key=lambda v: (v.co - j["HandL"]).dot(ha + hu * 0.3)).co.copy()
        cone(f"Claw{o.name}", tip - ha * 0.004, (ha * 0.7 - hu * 0.6).normalized(), 0.13, 0.016, "claw", "HandL", segs=5, bend=-hu)

# ================================================================ 腿
for _nm, _sf, _t0, _t1 in (("UnderThigh", body.thigh, -0.03, Lt + 0.015), ("UnderShin", body.shin, -0.015, Ls)):
    B.both(B.shell(_nm, _sf, _t0, _t1, 0, 360, 8, 4, "chainD", body.w_knee(), off=0.0, texel=0.8))
B.both(leg_armor(B, body, "gold", rivet_mat="gold", cuisse=True, wing=True))
B.both(sabaton(B, body, "gold", pointed=1.35, sole_mat="iron"))
for s, sfx in (("L", ""), ("R", "_R")):
    VH.xmark([o for o in B.parts if o.name in ("Greave" + sfx, "GreaveRivets" + sfx)], "X3_Greave" + s)
    VH.xmark([o for o in B.parts if o.name.startswith("Sabaton") and o.name.endswith(sfx) and (sfx or not o.name.endswith("_R"))], "X3_Sabaton" + s)
# 護膝（外徑 0.10H）＋渦紋圓飾嵌板；大腿甲前片、脛甲前片嵌板
for sx in (1, -1):
    s = "L" if sx > 0 else "R"
    wk = {"Thigh" + s: 0.5, "Shin" + s: 0.5}
    kc = V(j["ShinL"].x * sx, j["ShinL"].y - 0.085, j["ShinL"].z + 0.015)
    n = V(0, -1, 0.12).normalized()
    e1 = X.copy(); e2 = n.cross(e1).normalized()
    B.ellipsoid(f"KneeCop{s}", kc, (e1, e2, n), (0.195, 0.16, 0.10), 16, 6, "gold", wk, v0=0, v1=0.5, rim=0.012)
    rc = kc + n * 0.10
    B.ellipsoid(f"KneeDisc{s}", rc, (e1, e2, n), (0.075, 0.075, 0.018), 14, 4, "goldP", wk, v0=0, v1=0.5, rim=0.006)
    sp = [rc + n * 0.016 + (e1 * math.cos(t) + e2 * math.sin(t)) * (0.06 * (1 - t / 15)) for t in np.linspace(0, 14, 20)]
    B.tube(f"KneeSpiral{s}", sp, [(0.004, 0.006)] * 20, 3, "gold", wk, cap=False, flat=n)
for o in [B.shell("ThighPanel", body.thigh, Lt * 0.32, Lt * 0.74, -38, 38, 6, 4, "goldP", "ThighL",
                  off=lambda u, v, ang, t: 0.012 * RL + 0.012, rim=0.008),
          B.shell("GreavePanel", body.shin, Ls * 0.22, Ls * 0.62, -30, 30, 5, 4, "goldP", "ShinL",
                  off=lambda u, v, ang, t: 0.011 * RL + 0.016, rim=0.007)]:
    B.both(o)
VH.xmark([o for o in B.parts if o.name in ("GreavePanel",)], "X3_GreaveL")
VH.xmark([o for o in B.parts if o.name in ("GreavePanel_R",)], "X3_GreaveR")

# ================================================================ 頭：骷髏＋融合頭盔＋不對稱角冠
HC = V(0, -0.02, h(0.825))
HEADW = "Head"
B.ellipsoid("Cranium", V(0, 0.02, h(0.826)), (X, Y, Z), (0.142, 0.175, 0.138), 20, 10, "bone", HEADW)
B.ellipsoid("Brow", V(0, -0.115, h(0.828)), (X, Y, Z), (0.126, 0.065, 0.052), 18, 8, "bone", HEADW)
for sx in (1, -1):
    s = "L" if sx > 0 else "R"
    B.ellipsoid(f"Cheek{s}", V(0.074 * sx, -0.118, h(0.806)), (X, Y, Z), (0.032, 0.048, 0.024), 14, 8, "bone", HEADW)
    B.ellipsoid(f"Socket{s}", V(0.048 * sx, -0.128, h(0.815)), (X, Y, Z), (0.028, 0.042, 0.024), 14, 8, "void", HEADW)
    B.ellipsoid(f"Eye{s}", V(0.049 * sx, -0.166, h(0.813)), (X, Y, Z), (0.0075, 0.006, 0.0065), 8, 5, "g_eye", HEADW)
    # 眉骨下壓（怒目）
    B.tube(f"BrowRidge{s}", [V(0.015 * sx, -0.180, h(0.829)), V(0.055 * sx, -0.178, h(0.826)), V(0.095 * sx, -0.160, h(0.832))],
           [(0.014, 0.012), (0.017, 0.013), (0.012, 0.010)], 6, "bone", HEADW)
B.ellipsoid("Nose", V(0, -0.182, h(0.797)), (X, Y, Z), (0.020, 0.012, 0.028), 8, 5, "void", HEADW)
B.ellipsoid("Maxilla", V(0, -0.135, h(0.782)), (X, Y, Z), (0.084, 0.060, 0.035), 16, 8, "bone", HEADW)
B.ellipsoid("Mandible", V(0, -0.118, h(0.763)), (X, Y, Z), (0.076, 0.088, 0.034), 16, 8, "bone", HEADW)
B.ellipsoid("MouthDark", V(0, -0.175, h(0.773)), (X, Y, Z), (0.060, 0.020, 0.018), 10, 5, "void", HEADW)
for q in range(10):
    x = (q - 4.5) * 0.0125
    yb = -0.198 + 0.0016 * (q - 4.5) ** 2
    lnU = 0.026 + (0.018 if q in (2, 7) else 0.0)
    B.tube(f"ToothU{q}", [V(x, yb, h(0.780)), V(x * 0.96, yb + 0.002, h(0.780) - lnU)], [0.0058, 0.0018], 5, "bone", HEADW)
    lnL = 0.024 + (0.014 if q in (1, 8) else 0.0)
    B.tube(f"ToothL{q}", [V(x, yb + 0.006, h(0.764)), V(x * 0.96, yb + 0.006, h(0.764) + lnL)], [0.0055, 0.0018], 5, "bone", HEADW)


def helm_fn(u, v):
    th = math.pi * lerp(0.0, 0.72, v)
    ph = 2 * math.pi * u
    d = Vector((math.sin(th) * math.sin(ph), math.sin(th) * math.cos(ph), math.cos(th)))
    return V(0, 0.03, h(0.826)) + V(d.x * 0.150, d.y * 0.185, d.z * 0.150)


def helm_holes(i, jv):
    # 前方（臉）開口：u≈0.5 為 -Y，只留頭頂中央一條冠脊
    u = (i + 0.5) / 24; v = (jv + 0.5) / 9
    a = abs(u - 0.5)
    return a < 0.20 and v > 0.25


HELM = B.grid("Helm", 24, 9, helm_fn, "gold", HEADW, [V(0, 0.03, h(0.826))], closed_u=True, holes=helm_holes, rim=0.008, sharp=45)
# 頰甲（舊金，與骨融合，外寬 0.10H）
for sx in (1, -1):
    s = "L" if sx > 0 else "R"

    def cg(u, v, sx=sx):
        z = lerp(h(0.835), h(0.768), v)
        y = lerp(-0.13, 0.05, u)
        x = (0.132 + 0.032 * math.sin(math.pi * v) ** 0.8 - 0.035 * v * v + 0.01 * u) * sx
        return V(x, y - 0.02 * v, z)
    B.grid(f"CheekGuard{s}", 5, 6, cg, "gold", HEADW, [V(0, -0.02, h(0.80))], rim=0.007, sharp=45)
# 冠脊（頭盔中央往後的縱稜）
B.tube("HelmCrest", [V(0, -0.10, h(0.858)), V(0, 0.02, h(0.868)), V(0, 0.14, h(0.852)), V(0, 0.21, h(0.815))], [(0.016, 0.022)] * 4, 6, "gold", HEADW, flat=X)

HORNS = {}


def horn(name, pts, r0, n=13, segs=8, w=HEADW):
    P = catmull([V(*p) for p in pts], n)
    rad = [r0 * (1 - 0.93 * (k / (n - 1)) ** 1.5) + 0.0015 for k in range(n)]
    ob = B.tube(name, P, rad, segs, "horn", w, cap=True)
    L_ = sum((P[k + 1] - P[k]).length for k in range(n - 1))
    VH.src_uv(ob, B, fn=lambda co, P=P, L_=L_: _horn_param(co, P, L_))
    HORNS[name] = (ob, P, rad, L_)
    return ob


ZS = h(0.86)
# 中央直角＋兩側各 3 根 S 形；右側整體比左側長（最長右 vs 左 ≥15%）
# 5 根粗主角：中央直角＋兩側各 2 根 S 形；右側明顯又高又長（正面剪影不對稱）
horn("HornC", [(0, -0.06, ZS - 0.02), (0.0, -0.075, ZS + 0.16), (0.03, -0.05, ZS + 0.34), (-0.01, -0.02, ZS + 0.47), (0.0, -0.03, HT - 0.002)], 0.062)
horn("HornL2", [(0.10, -0.02, ZS - 0.05), (0.22, 0.01, ZS + 0.02), (0.27, 0.02, ZS + 0.13), (0.23, 0.0, ZS + 0.22), (0.28, -0.05, ZS + 0.28)], 0.060)
horn("HornR2", [(-0.10, -0.02, ZS - 0.05), (-0.25, 0.01, ZS + 0.04), (-0.34, 0.02, ZS + 0.20), (-0.29, 0.0, ZS + 0.36), (-0.37, -0.06, ZS + 0.47)], 0.066)
horn("HornOuterL", [(0.14, 0.02, ZS - 0.11), (0.30, 0.05, ZS - 0.13), (0.44, 0.05, ZS - 0.06), (0.50, 0.0, ZS + 0.04), (0.53, -0.05, ZS + 0.12)], 0.066)
horn("HornLongR", [(-0.14, 0.02, ZS - 0.11), (-0.34, 0.06, ZS - 0.13), (-0.53, 0.06, ZS - 0.01), (-0.63, 0.0, ZS + 0.20), (-0.66, -0.06, ZS + 0.38),
                   (-0.60, -0.10, ZS + 0.50)], 0.074, n=15)
VH.xmark(HORNS["HornLongR"][0], "X3_HornLongR")
VH.xmark(HORNS["HornOuterL"][0], "X3_HornOuterL")
VH.xmark(HORNS["HornR2"][0], "X3_HornR2")
# 角根部黑墨下滴（幾何）
for q, (hn, k0) in enumerate((("HornOuterL", 1), ("HornLongR", 1), ("HornL2", 1), ("HornR2", 1))):
    ob, P, rad, L_ = HORNS[hn]
    p = P[k0]
    for e in range(2):
        a = rnd.uniform(0, 6.28)
        d = (P[k0 + 1] - P[k0]).normalized()
        e1 = d.orthogonal().normalized(); e2 = d.cross(e1)
        sd = (e1 * math.cos(a) + e2 * math.sin(a))
        if sd.z > 0:
            sd = -sd
        base = p + sd * rad[k0] * 0.95
        ln = rnd.uniform(0.10, 0.20)
        pts_ = [base, base - Z * ln * 0.5 + sd * 0.006, base - Z * ln + sd * 0.004]
        B.tube(f"HornDrip{q}{e}", pts_, [(0.014, 0.006), (0.009, 0.005), (0.013, 0.010)], 5, "void", HEADW, cap=True)

# 墨流痕（幾何）：從胸甲上緣、肩甲下緣往下流
drips = []
for q in range(10):
    a = rnd.uniform(-70, 70) if q < 6 else rnd.choice((-1, 1)) * rnd.uniform(95, 150)
    z0 = cu_t1(a) - 0.01
    ln = rnd.uniform(0.12, 0.30)
    P = []; Nn = []
    for k in range(5):
        p, n = cu_pt(a + 2 * math.sin(k * 1.3 + q), z0 - ln * k / 4, lift=0.012)
        P.append(p); Nn.append(n)
    wd = [0.020, 0.016, 0.013, 0.011, 0.022]
    drips.append(flat_tube(f"InkDrip{q}", P, Nn, wd, 0.006, "void", "Spine2"))
VH.xmark(drips, "X3_ChestPlate")

# ================================================================ 書頁
PAGE_VAR_LIGHT = list(range(6))
PAGE_VAR_DARK = [6, 7]


def page(name, top, T_, D_, N_, w_, h_, wgt, var, tilt=10.0, yaw=0.0, cup=0.12, lift=0.10, nu=2, nv=2, rg=None, thick=0.006, floor=True, bend=0.0, rim_all=False):
    """一張書頁：上緣中心 top；T 沿寬、D 往下、N 朝外。tilt：下緣往外翹（度）；yaw：繞 N 轉；cup：橫向捲曲；lift：下緣捲起。"""
    rg = rg or rnd
    T_ = T_.normalized(); D_ = (D_ - T_ * D_.dot(T_)).normalized()
    Nn_ = T_.cross(D_)
    N_ = Nn_ if Nn_.dot(N_) >= 0 else -Nn_
    ya = math.radians(yaw)
    T2 = T_ * math.cos(ya) + D_ * math.sin(ya)
    D2 = D_ * math.cos(ya) - T_ * math.sin(ya)
    ta = math.radians(tilt)
    D3_ = D2 * math.cos(ta) + N_ * math.sin(ta)
    N3 = T2.cross(D3_).normalized()
    if N3.dot(N_) < 0:
        N3 = -N3
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("atlas")
    vv = []
    jit = {}
    for i in range(nu + 1):
        row = []
        for k in range(nv + 1):
            u = i / nu; v = k / nv
            du = 0.0; dv = 0.0
            if i in (0, nu) or k == nv:
                du = rg.uniform(-0.07, 0.07) * (1 if k > 0 else 0.3)
                dv = rg.uniform(-0.10, 0.04) if k == nv else rg.uniform(-0.04, 0.04)
            p = top + T2 * ((u - 0.5 + du) * w_) + D3_ * ((v + dv) * h_) + N3 * (cup * ((u - 0.5) * 2) ** 2 * w_ * 0.5 + lift * v * v * h_ + bend * math.sin(math.pi * v) * h_)
            if floor and p.z < 0.012:
                p.z = 0.012 + rg.uniform(0, 0.006)
            row.append(bm.verts.new(p))
        vv.append(row)
    c, r_ = var % 4, var // 4
    u0, u1 = c / 4 + 0.004, (c + 1) / 4 - 0.004
    for i in range(nu):
        for k in range(nv):
            f = bm.faces.new((vv[i][k], vv[i + 1][k], vv[i + 1][k + 1], vv[i][k + 1]))
            for l, (a, b) in zip(f.loops, ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1))):
                l[uvl].uv = (lerp(u0, u1, a / nu) - 50.0 * 0, 1 - r_ / 2 - 0.004 - (b / nv) * (0.5 - 0.008))
    bm.normal_update()
    s = sum(f.normal.dot(N3) for f in bm.faces)
    if s < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    # 紙厚：邊緣往內擠出一圈（單面頁＋厚度邊，比 solidify 省一半面數）
    vuv = {}
    for f in bm.faces:
        for l in f.loops:
            vuv[l.vert] = l[uvl].uv.copy()
    border = [e for e in bm.edges if len(e.link_faces) == 1]
    if not rim_all:                     # 只在下緣（最常被看到翹起的那一邊）做紙厚，省面數
        bot = set(vv[i][nv] for i in range(nu + 1))
        border = [e for e in border if all(x in bot for x in e.verts)]
    pos0 = {v: v.co.copy() for v in bm.verts}
    ret = bmesh.ops.extrude_edge_only(bm, edges=border)
    newv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    src = {}
    for v in newv:
        src[v] = min(pos0, key=lambda q: (pos0[q] - v.co).length_squared)
        v.co = v.co - N3 * thick
    for f in [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]:
        for l in f.loops:
            o = l.vert if l.vert in vuv else src.get(l.vert)
            if o in vuv:
                l[uvl].uv = vuv[o]
    bm.normal_update()
    ob = B.add_mesh(name, bm, "paper", wgt, sharp=80, stacked=True)
    for l in ob.data.uv_layers["atlas"].data:
        l.uv.x += 50.0
    return ob


# ---- 披風（spec：10–14 排錯開的書頁，往後、往左拖地；上段有暗紅內襯）
ZTOP = 2.86


def cape_frame(a, v):
    cx = 0.42 * v ** 2
    cy = 0.10 + 0.55 * v ** 1.6
    side = smooth(0.5 + math.sin(a) * 0.9)          # +X（左側，符紋手那側）拖得更遠
    rx = 0.60 + (0.46 + 0.36 * side) * v ** 1.25
    ry = 0.40 + 0.50 * v ** 1.25
    fold = 1 + 0.045 * math.sin(5 * a + 2.3 * v) * v + 0.02 * math.sin(11 * a) * v
    z = ZTOP * (1 - v) + 0.03 * v
    return V(cx + math.sin(a) * rx * fold, cy + math.cos(a) * ry * fold, z)


def cape_A(v):
    return math.radians(68 + 50 * smooth(v * 1.1))


def cape_AR(v):
    """右側（握劍側）範圍：從右肩後方包到大腿外側。"""
    return math.radians(92 + 22 * smooth(v * 1.1))


def cape_basis(a, v):
    e = 1e-3
    p = cape_frame(a, v)
    Ta = (cape_frame(a + e, v) - cape_frame(a - e, v)).normalized()
    Dv = (cape_frame(a, min(1, v + e)) - cape_frame(a, max(0, v - e))).normalized()
    N_ = Dv.cross(Ta).normalized()
    out_ = V(p.x - 0.42 * v * v, p.y - (0.10 + 0.55 * v ** 1.6), 0)
    if N_.dot(out_) < 0:
        N_ = -N_
    return p, Ta, Dv, N_


# 披風骨：5 條鏈 × 4 節（右前、右、中、左、左前；錨在 Spine2）＋貼地骨 CapeGround
CV = (0.0, 0.25, 0.50, 0.75, 0.985)
CAPE_FR = (("CapeRF", -0.93), ("CapeR", -0.48), ("CapeC", 0.0), ("CapeL", 0.48), ("CapeLF", 0.93))
CAPE_CH = {}
for cn, af in CAPE_FR:
    pts_ = [cape_frame((af * (cape_A(v_) if af > 0 else cape_AR(v_))), v_) for v_ in CV]
    CAPE_CH[cn] = (chain_names(cn, 4), pts_)
_WCH = {cn: w_chain_pts("Spine2", nm, pts_) for cn, (nm, pts_) in CAPE_CH.items()}


def W_CAPE(co):
    """依角度在 5 條鏈之間線性分配，再沿各鏈分配到各節；貼地的下段改綁 CapeGround。"""
    v_ = clamp((ZTOP - co.z) / (ZTOP - 0.03))
    cx = 0.42 * v_ ** 2; cy = 0.10 + 0.55 * v_ ** 1.6
    a = math.atan2((co.x - cx) / (0.6 + 0.7 * v_ ** 1.25), (co.y - cy) / (0.40 + 0.50 * v_ ** 1.25))
    sN = a / cape_A(v_) if a > 0 else a / cape_AR(v_)
    sN = max(-0.93, min(0.93, sN))
    ws = {}
    for i in range(len(CAPE_FR) - 1):
        (c0, f0_), (c1, f1_) = CAPE_FR[i], CAPE_FR[i + 1]
        if f0_ <= sN <= f1_:
            t = (sN - f0_) / (f1_ - f0_)
            ws = {c0: 1 - t, c1: t}
            break
    gw = smooth((0.85 - co.z) / 0.62)
    out = {}
    for cn, wgt in ws.items():
        if wgt < 1e-3:
            continue
        for k, x in _WCH[cn](co).items():
            out[k] = out.get(k, 0.0) + x * wgt * (1 - gw)
    if gw > 1e-3:
        out["CapeGround"] = gw
    return out


cape_len = sum((cape_frame(0, (k + 1) / 40) - cape_frame(0, k / 40)).length for k in range(40))
# 暗紅內襯（只在上段，0–0.45，下緣破碎）
cut = rag_profile(20, random.Random(3), 0.3)


def lin_fn(u, v):
    vv = v * 0.46 * (1 - 0.12 * cut[min(int(round(u * 20)), 20)])
    a = lerp(-cape_AR(vv), cape_A(vv), u)
    p, Ta, Dv, N_ = cape_basis(a, vv)
    return p - N_ * 0.035


lin = B.grid("CapeLining", 18, 6, lin_fn, "lining", W_CAPE, [V(0, 0, z) for z in (1.6, 2.2, 2.8)], sharp=60)
lin["cloth"] = 0.012
# 書頁排：直長頁（長寬比 1.7–2.4），上段每頁重疊 ≥30% 不透底；下段 3–4 排是兩張相連的長條垂頁，拖地散開
cape_rows = 0
n_pages = 0
x3_cape = []
v = 0.0
row = 0
LOWZ = h(0.35)
while v < 0.985:
    hh = 0.23 + 0.12 * v
    upper = v < 0.45
    ww = hh / 2.05
    AL, AR = cape_A(v), cape_AR(v)
    arc = sum((cape_frame(lerp(-AR, AL, (k + 1) / 30), v) - cape_frame(lerp(-AR, AL, k / 30), v)).length for k in range(30))
    n = max(6, int(arc / (ww * (0.60 if upper else 0.74))))
    strip = v > 0.70
    for k in range(n):
        a = lerp(-AR, AL, (k + 0.5 + rnd.uniform(-0.3, 0.3)) / n)
        vv = clamp(v + rnd.uniform(-0.02, 0.025), 0, 0.99)
        p, Ta, Dv, N_ = cape_basis(a, vv)
        top = p + N_ * (0.010 + 0.006 * (row % 2) + 0.004 * (k % 2))
        asp = rnd.uniform(1.7, 2.4)
        hk = hh * rnd.uniform(0.85, 1.15)
        wk = hk / asp
        ob = page(f"Page{n_pages}", top, Ta, Dv, N_, wk, hk, W_CAPE, rnd.choice(PAGE_VAR_LIGHT),
                  tilt=rnd.uniform(4, 14) if upper else rnd.uniform(5, 22), yaw=rnd.uniform(-10, 10), cup=rnd.uniform(0.10, 0.30),
                  lift=rnd.uniform(0.05, 0.25), nv=3, bend=rnd.uniform(-0.06, 0.08))
        n_pages += 1
        lst = [ob]
        if strip and k % 4 == 0:
            D2 = (Dv * 0.9 + N_ * 0.15).normalized()
            lst.append(page(f"PageS{n_pages}", top + D2 * hk * 0.82 + N_ * 0.012, Ta, Dv, N_, wk * 0.95, hk * rnd.uniform(0.9, 1.2), W_CAPE,
                            rnd.choice(PAGE_VAR_LIGHT), tilt=rnd.uniform(6, 20), yaw=rnd.uniform(-14, 14), cup=0.2, lift=0.3, nv=3, bend=0.05))
            n_pages += 1
        if top.z < LOWZ:
            x3_cape += lst
    v += (0.66 if upper else 0.86) * hh / cape_len
    row += 1
cape_rows = row
# 地上散頁（往後、往左拖散）
for q in range(8):
    a = math.radians(rnd.uniform(-100, 150))
    p = cape_frame(a, 1.0)
    out_ = V(math.sin(a), math.cos(a), 0).normalized()
    c = p + out_ * rnd.uniform(0.05, 0.35)
    c.z = 0.015
    yaw = rnd.uniform(0, 6.28)
    Tg = V(math.cos(yaw), math.sin(yaw), 0); Dg = V(-math.sin(yaw), math.cos(yaw), 0)
    ob = page(f"GroundPage{q}", c - Dg * 0.15, Tg, Dg, Z, 0.16, 0.32, W_CAPE, rnd.choice(PAGE_VAR_LIGHT), tilt=rnd.uniform(-4, 6), cup=0.15, lift=0.2)
    x3_cape.append(ob)
    n_pages += 1
VH.xmark(x3_cape, "X3_CapeLower")
print("CAPE rows", cape_rows, "pages", n_pages, "lower", len(x3_cape), flush=True)

# ---- 左臂書頁：上臂、前臂外側 3–4 排，長頁往下垂（左右不對稱：右臂乾淨）
arm_pages = 0
for rowi, (surf, Lx, bn, t0_, t1_) in enumerate(((body.uarm, La, "UpperArmL", 0.15, 0.55), (body.uarm, La, "UpperArmL", 0.55, 0.95),
                                                  (body.farm, Lf, "ForearmL", 0.05, 0.45), (body.farm, Lf, "ForearmL", 0.45, 0.9))):
    for q in range(3):
        a = 75 + q * 50 + rnd.uniform(-10, 10)
        t = Lx * lerp(t0_, t1_, rnd.random())
        top = surf.pt(t, a, 0.045)
        n = surf.nrm(t, a)
        Dd = (-Z * 0.85 + surf.a * 0.3).normalized()
        Tt = n.cross(Dd).normalized()
        hh = rnd.uniform(0.20, 0.33)
        page(f"ArmPage{arm_pages}", top, Tt, Dd, n, hh * 0.5, hh, bn, rnd.choice(PAGE_VAR_LIGHT), tilt=rnd.uniform(5, 20), yaw=rnd.uniform(-15, 15),
             cup=0.1, lift=0.15, nv=2)
        arm_pages += 1
        if rowi >= 2 and q in (1, 2):      # 長條：再掛一張，垂得更低
            top2 = top + Dd * hh * 0.85 + n * 0.01
            page(f"ArmPage{arm_pages}", top2, Tt, Dd, n, hh * 0.48, hh * 1.05, bn, rnd.choice(PAGE_VAR_LIGHT), tilt=rnd.uniform(8, 22),
                 yaw=rnd.uniform(-20, 20), cup=0.12, lift=0.25, nv=2)
            arm_pages += 1
# 鬆脫往外飄的一兩頁
for q in range(2):
    t = Lf * (0.6 + 0.2 * q)
    top = body.farm.pt(t, 130, 0.12 + 0.06 * q)
    n = body.farm.nrm(t, 130)
    page(f"ArmPageLoose{q}", top, n.cross(-Z).normalized(), (-Z + n * 0.6).normalized(), n, 0.16, 0.22, "ForearmL", 0, tilt=30, yaw=25, cup=0.2, lift=0.3)
    arm_pages += 1
print("ARM pages", arm_pages, flush=True)

# ================================================================ 巨劍（右手；0.80H、兩側稀疏大倒鉤）
gcR = Body.mir(body.grip_c)
AX = Body.mir(body.hand_v).normalized()
EG = Body.mir(body.hand_a); EG = (EG - AX * EG.dot(AX)).normalized()
SD = AX.cross(EG).normalized()
BL0, BL1 = 0.16, 0.16 + 0.58 * HT          # 劍刃起訖（從握點中心沿劍軸，公尺）
GRIP0 = -0.50                                # 握柄末端


def P_sw(a, e, s=0.0):
    return gcR + AX * a + EG * e + SD * s


def bw(v):
    """半寬（公尺）：近護手 0.065H → 近劍尖 0.04H → 尖。少數缺口。"""
    b = lerp(0.127, 0.080, smooth(v / 0.86))
    if v > 0.86:
        b *= max(0.0, (1 - v) / 0.14) ** 0.8
    for vc, dep in ((0.31, 0.012), (0.57, 0.009), (0.74, 0.010)):
        b -= dep * math.exp(-((v - vc) / 0.008) ** 2)
    return b


def th_(v, q):
    return 0.0235 * (1 - 0.65 * v) * (math.sin(math.pi * q) ** 0.6 + 0.04)


def sword_fn(u, v):
    if u <= 0.5:
        q, sd = u * 2, 1.0
    else:
        q, sd = 2 - 2 * u, -1.0
    b = bw(v)
    e = lerp(-b, b, q)
    ridge = 0.006 * (1 - v) * math.exp(-((q - 0.5) / 0.06) ** 2)
    return P_sw(lerp(BL0, BL1, v), e, sd * (th_(v, q) + ridge))


blade_ob = B.grid("SwordBlade", 8, 40, sword_fn, "blade", "Weapon", [P_sw(lerp(BL0, BL1, k / 6), 0) for k in range(7)], closed_u=True, cap0=True, sharp=35)
VH.src_uv(blade_ob, B)
# 倒鉤：兩側各 9 個，間距不規則，鉤尖朝劍柄
r2 = random.Random(12)
for side in (1, -1):
    vb = 0.06
    q = 0
    while vb < 0.84 and q < 10:
        ln = r2.uniform(0.065, 0.12)
        b = bw(vb)
        base0 = P_sw(lerp(BL0, BL1, vb) + 0.03, side * (b - 0.01))
        base1 = P_sw(lerp(BL0, BL1, vb) - 0.03, side * (b - 0.01))
        mid = P_sw(lerp(BL0, BL1, vb) - 0.01, side * (b + ln * 0.55))
        tip = P_sw(lerp(BL0, BL1, vb) - ln * 0.75, side * (b + ln * 0.85))
        pts_ = [P_sw(lerp(BL0, BL1, vb) + 0.035, side * (b - 0.02)), P_sw(lerp(BL0, BL1, vb) + 0.005, side * (b + ln * 0.35)), mid, tip]
        thk = th_(vb, 0.5) * 0.7
        ob = B.tube(f"Barb{side}{q}", pts_, [(0.038, thk), (0.028, thk * 0.85), (0.016, thk * 0.6), (0.002, 0.002)], 4, "blade", "Weapon",
                    flat=AX, cap=True, sharp=30)
        VH.src_uv(ob, B)
        # 倒鉤內側暗紅細線
        B.tube(f"BarbGlow{side}{q}", [P_sw(lerp(BL0, BL1, vb) - 0.02, side * (b - 0.022), s * 0) for s in (0,)] +
               [P_sw(lerp(BL0, BL1, vb) - 0.06, side * (b - 0.026))], [(0.0035, 0.0025)] * 2, 4, "g_weapon", "Weapon", flat=SD)
        vb += r2.uniform(0.07, 0.11) * (0.95 if q % 2 else 1.1)
        q += 1
# 中稜＋縱向裂痕（一階是暗縫，二階發光覆蓋）
for sd in (1, -1):
    crack_pts = []
    e = 0.02
    for k in range(14):
        vv = 0.05 + 0.75 * k / 13
        e += r2.uniform(-0.012, 0.012)
        e = clamp(e, -0.04, 0.05)
        crack_pts.append((vv, e))
    P = [P_sw(lerp(BL0, BL1, vv), ee, sd * (th_(vv, 0.5 + ee / (2 * bw(vv))) + 0.0012)) for vv, ee in crack_pts]
    B.tube(f"BladeCrack{sd}", P, [(0.0012, 0.0035)] * len(P), 4, "void", "Weapon", flat=SD)
# 護手（寬 0.165H，兩端彎鉤朝劍尖）
gp = [P_sw(0.12 + 0.10, -0.33), P_sw(0.14, -0.30), P_sw(0.13, -0.16), P_sw(0.13, 0.0), P_sw(0.13, 0.16), P_sw(0.14, 0.30), P_sw(0.12 + 0.10, 0.33)]
gp = catmull(gp, 13)
B.tube("Guard", gp, [(0.035, 0.03) if 3 < k < 9 else (0.026 - 0.004 * abs(k - 6) / 6 * 3, 0.022) for k in range(13)], 8, "iron", "Weapon", flat=AX)
for sx in (1, -1):
    B.tube(f"GuardHook{sx}", [P_sw(0.21, 0.325 * sx), P_sw(0.29, 0.345 * sx), P_sw(0.36, 0.31 * sx)], [0.020, 0.012, 0.002], 6, "iron", "Weapon")
B.ellipsoid("GuardBoss", P_sw(0.135, 0), (EG, SD, AX), (0.06, 0.045, 0.05), 12, 6, "iron", "Weapon")
# 握柄（長 0.17H＝0.66 m、直徑 0.022H、螺旋纏皮）
gpts = [P_sw(0.12 - (0.12 - GRIP0) * k / 10, 0) for k in range(11)]
B.tube("Grip", gpts, [0.040] * 11, 8, "leather", "Weapon", flat=EG)
wrap = [P_sw(0.11 - (0.11 - GRIP0 - 0.02) * t, 0) + (EG * math.cos(t * 2 * math.pi * 11) + SD * math.sin(t * 2 * math.pi * 11)) * 0.040 for t in np.linspace(0, 1, 46)]
B.tube("GripWrap", wrap, [(0.006, 0.010)] * 46, 3, "leather", "Weapon", cap=False)
# 柄頭：叉狀爪
B.ellipsoid("Pommel", P_sw(GRIP0 - 0.03, 0), (EG, SD, AX), (0.05, 0.045, 0.045), 10, 6, "iron", "Weapon")
for sx in (1, -1):
    B.tube(f"PommelClaw{sx}", [P_sw(GRIP0 - 0.05, 0.03 * sx), P_sw(GRIP0 - 0.11, 0.075 * sx), P_sw(GRIP0 - 0.17, 0.05 * sx)], [0.022, 0.014, 0.002], 6, "iron", "Weapon")
SWORD_TIP = P_sw(BL1, 0)
print("SWORD len", round(BL1 - (GRIP0 - 0.17), 3), "=", round((BL1 - (GRIP0 - 0.17)) / HT, 3), "H", flush=True)

# ================================================================ 二階部件 P2_*
# P2_ChestMaw：胸甲中央豎直巨口（中心 0.64H，高 0.12H、寬 0.085H），16–20 顆尖牙，唇緣甲片外翻
MZ = h(0.64)
MH, MW = h(0.12) * 0.5, h(0.085) * 0.5
mloc, mn = cu_pt(0, MZ)
maw = []


LIPH = 0.075        # 唇甲往外凸的高度＝嘴的可見深度


def maw_xy(u, r):
    a = 2 * math.pi * u
    z = math.cos(a) * MH * r
    lens = math.sqrt(max(0.0, 1 - (math.cos(a)) ** 2 * 0.0))
    x = math.sin(a) * MW * r * (0.55 + 0.45 * abs(math.sin(a)))
    return x, z


def throat_fn(u, v):
    """嘴內：從唇緣（v=1，凸出 LIPH）往中心收、往內沉到胸甲面（肉色漸暗）。"""
    x, z = maw_xy(u, 0.25 + 0.75 * v)
    return mloc + mn * (0.006 + LIPH * v ** 1.6) + X * x + Z * z


maw.append(B.grid("MawThroat", 20, 5, throat_fn, "mawflesh", "Spine2", mloc - mn * 0.4, closed_u=True))
maw.append(B.grid("MawCore", 14, 2, lambda u, v: mloc + mn * 0.008 + X * maw_xy(u, 0.27 * v)[0] + Z * maw_xy(u, 0.27 * v)[1], "p2_maw", "Spine2",
                  mloc - mn * 0.4, closed_u=True))
for sx in (1, -1):
    lip = [throat_fn(0.0 + (0.5 * k / 12 if sx > 0 else 1 - 0.5 * k / 12), 1.0) for k in range(13)]
    # 外翻唇甲（有厚度的舊金板）
    maw.append(B.tube(f"MawLip{sx}", [p + mn * 0.006 + X * 0.022 * sx for p in lip], [(0.030, 0.024)] * 13, 6, "gold", "Spine2", flat=mn))
    for k in range(1, 12):
        p = lip[k]
        inward = mloc + mn * 0.02 - p
        ln = (0.04 + 0.08 * math.sin(math.pi * k / 12) ** 1.3) * (0.75 + 0.5 * rnd.random())
        d = (inward.normalized() * 0.85 - mn * 0.35).normalized()
        maw.append(cone(f"MawTooth{sx}{k}", p - inward.normalized() * 0.004, d, ln, 0.017, "bone", "Spine2", segs=5, bend=-mn))
    # 第二排內牙（較短，在喉內一半深處）：牙列層次
    for k in range(2, 11, 2):
        u_ = (0.5 * k / 12) if sx > 0 else (1 - 0.5 * k / 12)
        p = throat_fn(u_, 0.62)
        inward = mloc + mn * 0.01 - p
        maw.append(cone(f"MawTooth2{sx}{k}", p, (inward.normalized() * 0.8 - mn * 0.3).normalized(), 0.035 + 0.02 * rnd.random(), 0.012, "bone", "Spine2", segs=4, bend=-mn))
VH.mark(maw, "P2_ChestMaw")
# P2_Glow_Script：浮雕主線轉紅（胸甲、肩甲、腿甲）
scr = []
for nm, P, Nn, bn in SCROLLS:
    scr.append(ribbon("Script" + nm, P, Nn, 0.006, 0.004, "p2_script", bn, segs=3, lift=0.0105))
VH.mark(scr, "P2_ScriptChest")
for sx, sfx in ((1, "L"), (-1, "R")):
    obs = []
    S_ = body.uarm
    for k in range(3):
        pts_ = []; nn_ = []
        for s_ in np.linspace(0, 1, 12):
            ang = lerp(40, 160, s_)
            t = (0.06 + 0.05 * k) * U * PSIZE + 0.04 + 0.03 * math.sin(s_ * 6 + k)
            off_ = (0.034 - k * 0.006) * RL * PSIZE + 0.010 * RL * PSIZE + 0.012
            p = S_.pt(t, ang, off_); n = S_.nrm(t, ang)
            if sx < 0:
                p = Body.mir(p); n = Body.mir(n)
            pts_.append(p); nn_.append(n)
        obs.append(ribbon(f"ScriptP{sfx}{k}", pts_, nn_, 0.007, 0.004, "p2_script", "UpperArm" + sfx, segs=3))
    VH.mark(obs, "P2_Script" + sfx)
    legs_ = []
    for k in range(2):
        pts_ = []; nn_ = []
        for s_ in np.linspace(0, 1, 10):
            t = body.th_len * lerp(0.25, 0.85, s_)
            ang = (lerp(-35, 35, s_) + 70 * k - 20) + 25 * math.sin(s_ * 7)
            p = body.thigh.pt(t, ang, 0.012 * RL + 0.012); n = body.thigh.nrm(t, ang)
            if sx < 0:
                p = Body.mir(p); n = Body.mir(n)
            pts_.append(p); nn_.append(n)
        legs_.append(ribbon(f"ScriptT{sfx}{k}", pts_, nn_, 0.007, 0.004, "p2_script", "Thigh" + sfx, segs=3))
    VH.mark(legs_, "P2_ScriptLeg" + sfx)
# P2_SwordCracks：劍身樹枝狀裂紋（3–4 主裂＋分支，從護手到劍尖）
crk = []
r_ = random.Random(9)
for sd in (1, -1):
    for b in range(2):
        e = lerp(-0.035, 0.035, b)
        vv = 0.03 + 0.05 * b
        path = [(vv, e)]
        while vv < 0.93:
            vv += r_.uniform(0.04, 0.07)
            e = clamp(e + r_.uniform(-0.03, 0.03), -0.7 * bw(min(vv, 0.95)), 0.7 * bw(min(vv, 0.95)))
            path.append((min(vv, 0.95), e))
        P = [P_sw(lerp(BL0, BL1, a), ee, sd * (th_(a, 0.5 + ee / (2 * max(bw(a), 1e-3))) + 0.0022)) for a, ee in path]
        crk.append(B.tube(f"Crack{sd}{b}", P, [(0.0016, 0.006)] * len(P), 3, "p2_blade", "Weapon", flat=SD))
        for kb in range(2, len(path) - 2, 5):
            a, ee = path[kb]
            sg = 1 if r_.random() < 0.5 else -1
            br = [(a, ee), (a + 0.025, ee + sg * 0.03), (a + 0.05, ee + sg * 0.05)]
            P = [P_sw(lerp(BL0, BL1, aa), clamp(e2_, -0.9 * bw(aa), 0.9 * bw(aa)), sd * (th_(aa, 0.5) * 0.9 + 0.0022)) for aa, e2_ in br]
            crk.append(B.tube(f"CrackB{sd}{b}{kb}", P, [(0.0016, 0.0045)] * 3, 3, "p2_blade", "Weapon", flat=SD))
VH.mark(crk, "P2_SwordCracks")
# P2_PageWingL/R：實心扇面翼。13 根「飛羽列」從肩胛後方的翼根往外放射（上 72° 到下外 −38°），
# 每列從內到外 6–9 張書頁、越外越長越寬、彼此重疊成不透的翼面；上緣與末端頁緣燃紅；最外 4 片脫離飄出。
WING = {}


def wing_len(th):
    return 2.45 - 1.05 * (th / 72.0) ** 2 if th > 0 else 2.45 - 0.50 * (th / 38.0) ** 2


for sx in (1, -1):
    s = "L" if sx > 0 else "R"
    root = V(0.26 * sx, 0.42, 2.80)
    obs = []
    npg = 0
    wr = random.Random(30 + sx)
    NC = 13
    for ci in range(NC):
        th = lerp(72.0, -38.0, ci / (NC - 1))
        t = math.radians(th)
        d = V(math.cos(t) * sx, 0.10 + 0.06 * math.cos(t), math.sin(t)).normalized()
        Lc = wing_len(th)
        side = V(-math.sin(t) * sx, 0.0, math.cos(t)).normalized()          # 扇面內、垂直於飛羽的方向
        Nw = d.cross(side).normalized()
        if Nw.y < 0:
            Nw = -Nw
        r = 0.22 + wr.uniform(-0.03, 0.03)
        q = 0
        while r < Lc - 0.12:
            frac = r / 2.45
            hh = 0.24 + 0.16 * frac + wr.uniform(-0.02, 0.03)
            ww = max(0.12, min(0.28, r * 0.165 * 1.15))
            top = root + d * r + side * wr.uniform(-0.03, 0.03) + Nw * (0.010 * (ci % 2) + 0.006 * q)
            loose = (ci in (5, 7, 9) and r + hh > Lc - 0.2 and q % 2 == 0)
            if loose:
                top = top + d * 0.35 + Nw * 0.12 - Z * 0.15
            pg = page(f"Wing{s}{ci}_{q}", top, side, d, Nw, ww, hh, "Wing" + s, wr.choice(PAGE_VAR_LIGHT), tilt=wr.uniform(3, 12),
                      yaw=wr.uniform(-8, 8) + (28 if loose else 0), cup=wr.uniform(0.08, 0.22), lift=wr.uniform(0.08, 0.25),
                      rg=wr, floor=False, nu=2, nv=2, bend=wr.uniform(-0.04, 0.05))
            obs.append(pg); npg += 1
            # 頁緣燃紅：最上面兩列、每列的末端頁
            if ci <= 1 or r + hh * 0.7 >= Lc - 0.12:
                vs = [v_.co for v_ in pg.data.vertices]
                ed = sorted(sorted(vs, key=lambda c: c.dot(d))[-3:], key=lambda c: c.dot(side))
                obs.append(B.tube(f"WingEdge{s}{ci}_{q}", [ed[0] + Nw * 0.005, ed[-1] + Nw * 0.005], [(0.018, 0.003)] * 2, 3, "p2_page", "Wing" + s,
                                  flat=d, cap=False))
            r += hh * 0.70
            q += 1
    for o in obs:
        for g in list(o.vertex_groups):
            o.vertex_groups.remove(g)
        g = o.vertex_groups.new(name="Wing" + s)
        g.add([vv_.index for vv_ in o.data.vertices], 1.0, "REPLACE")
    WING[sx] = root
    VH.mark(obs, "P2_PageWing" + s)
    print("WING", s, "pages", npg, flush=True)

# ================================================================ 三階部件 P3_*
# P3_Crown：直徑 0.26H 的斷環光環（3–4 段弧，前傾 12°，中心 1.02H），黑芯＋紅光緣＋原創符字＋火焰卡
crown = []
CC = V(0, 0.03, h(0.985))
CR = h(0.26) * 0.5
tilt = Matrix.Rotation(math.radians(-12), 4, "X")
segs_ = ((10, 95), (112, 185), (200, 268), (284, 345))
for k, (a0, a1) in enumerate(segs_):
    arc = []
    for s_ in np.linspace(0, 1, 11):
        a = math.radians(lerp(a0, a1, s_))
        arc.append(CC + (tilt @ V(math.cos(a) * CR, math.sin(a) * CR, 0.0)))
    nrm = (tilt @ Z.to_4d()).to_3d().normalized()
    crown.append(B.tube(f"HaloCore{k}", arc, [(0.006 * 2, 0.039)] * 11, 4, "p3_inkcore", "Head", flat=nrm, exp=4))
    for e in (1,):
        crown.append(B.tube(f"HaloRim{k}{e}", [p + (p - CC).normalized() * 0.040 * e for p in arc], [(0.007, 0.007)] * 11, 3, "p3_halo", "Head", cap=False))
    for g_ in range(3):
        s_ = (g_ + 0.5) / 3
        a = math.radians(lerp(a0, a1, s_))
        p = CC + (tilt @ V(math.cos(a) * CR, math.sin(a) * CR, 0.0)) + nrm * 0.008
        tang = (tilt @ V(-math.sin(a), math.cos(a), 0)).normalized()
        crown += glyph(f"HaloGlyph{k}{g_}", p, tang, (p - CC).normalized(), 0.05, "p3_halo", "Head", k * 3 + g_, width=0.004, th=0.003, segs=3, cap=False)
    for e in range(3):
        a = math.radians(lerp(a0, a1, rnd.random()))
        p = CC + (tilt @ V(math.cos(a) * CR, math.sin(a) * CR, 0.0))
        crown.append(cone(f"HaloFlame{k}{e}", p, nrm + (p - CC).normalized() * 0.2, rnd.uniform(0.08, 0.16), 0.016, "p3_halo", "Head", segs=4,
                          bend=(p - CC).normalized()))
    # 斷口焦黑（兩端）
    for a in (a0, a1):
        p = CC + (tilt @ V(math.cos(math.radians(a)) * CR, math.sin(math.radians(a)) * CR, 0.0))
        crown.append(B.ellipsoid(f"HaloChar{k}{a}", p, (X, Y, Z), (0.03, 0.03, 0.03), 6, 4, "p3_inkcore", "Head"))
VH.mark(crown, "P3_Crown")


# P3_HornBrokenR／L：斷角殘根（原長 30–40%，鋸齒斷口，斷面紅色餘燼）
def broken(hn, frac, part):
    ob, P, rad, L_ = HORNS[hn]
    nb = max(3, int(len(P) * frac))
    stub = B.tube(part + "Stub", P[:nb], [rad[k] * 1.04 for k in range(nb)], 10, "horn", HEADW, cap=False)
    Ls_ = sum((P[k + 1] - P[k]).length for k in range(nb - 1))
    VH.src_uv(stub, B, fn=lambda co, P=P[:nb], L_=L_: _horn_param(co, P, L_))
    d = (P[nb - 1] - P[nb - 2]).normalized()
    e1 = d.orthogonal().normalized(); e2 = d.cross(e1)
    obs = [stub]
    for k in range(7):
        a = 2 * math.pi * k / 7
        p = P[nb - 1] + (e1 * math.cos(a) + e2 * math.sin(a)) * rad[nb - 1] * 0.75
        obs.append(cone(f"{part}Jag{k}", p, d + (e1 * math.cos(a) + e2 * math.sin(a)) * 0.25, (0.025 + 0.03 * (k % 2)), rad[nb - 1] * 0.4, "horn", HEADW, segs=4))
    obs.append(B.ellipsoid(f"{part}Ember", P[nb - 1] + d * 0.006, (e1, e2, d), (rad[nb - 1] * 0.92, rad[nb - 1] * 0.92, 0.014), 10, 4, "p3_cracks", HEADW, v0=0, v1=0.5))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        p0 = P[nb - 1] + (e1 * math.cos(a) + e2 * math.sin(a)) * rad[nb - 1] * 1.02
        obs.append(B.tube(f"{part}Crack{k}", [p0, p0 - d * 0.06 + (e1 * math.cos(a + 0.3) + e2 * math.sin(a + 0.3)) * rad[nb - 1] * 0.06],
                          [(0.003, 0.004)] * 2, 4, "p3_cracks", HEADW))
    VH.mark(obs, part)


broken("HornLongR", 0.38, "P3_HornBrokenR")
broken("HornOuterL", 0.34, "P3_HornBrokenL")
# 另外兩根中角也斷（多根斷角）
broken("HornR2", 0.45, "P3_HornBrokenR2")


def wisp(name, base, d, length, side, mat, w, width=0.018, curl=0.25, n=7, seed=0, up=0.0):
    r__ = random.Random(seed)
    d = d.normalized(); side = (side - d * side.dot(d)).normalized(); nrm = d.cross(side)
    ph = r__.uniform(0, 6.28)
    pts_ = []; rad = []
    for k in range(n):
        s_ = k / (n - 1)
        p = base + d * (length * s_) + side * (curl * length * math.sin(s_ * 2.6 + ph) * s_) + nrm * (0.3 * curl * length * math.sin(s_ * 4 + ph * 2) * s_) + Z * (up * length * s_ * s_)
        pts_.append(p)
        rad.append((width * (1 - s_) ** 0.8 + 0.002, 0.004 * (1 - 0.6 * s_)))
    return B.tube(name, pts_, rad, 4, mat, w, flat=side, cap=False, sharp=80)


fl = []
for sx in (1, -1):
    for q in range(3):
        p = V(0.052 * sx, -0.172, h(0.816))
        dd = V(0.12 * sx + 0.12 * (q - 1), -0.18, 1.0)
        fl.append(wisp(f"EyeFlame{sx}{q}", p, dd, (0.16 + 0.07 * (q == 1)), X, "p3_eyes", HEADW, width=0.022, curl=0.35, seed=90 + q + (sx > 0) * 5, up=0.2))
VH.mark(fl, "P3_EyeFlames")
# P3_InkBody：從 0.50H 往下的墨潮裙，往左後捲成漩渦，4–6 條墨浪，夾殘頁，懸浮 0.2 m
ink = []
ZI0, ZI1 = h(0.50), 0.32


def ink_fn(u, v):
    a = 2 * math.pi * u
    z = lerp(ZI0, ZI1, v)
    r = lerp(0.46, 1.05, v ** 1.2) * (1 + 0.16 * math.sin(5 * a + 4 * v) * v + 0.09 * math.sin(11 * a - 6 * v) * v)
    swirl = 1.7 * v ** 1.5
    aa = a + swirl
    x = math.sin(aa) * r * (1 + 0.35 * max(0.0, math.sin(aa)) * v) + 0.85 * v ** 1.8
    y = -math.cos(aa) * r * 0.85 + 0.45 * v ** 1.6
    return V(x, y, z + 0.16 * math.sin(7 * a + 6 * v) * v + 0.10 * math.sin(3 * a) * v)


_ir = random.Random(55)
_inkholes = set((i, jv) for i in range(26) for jv in (8, 9) if _ir.random() < (0.35 if jv == 9 else 0.18))   # 下緣墨濺破碎
ink.append(B.grid("InkTide", 26, 10, ink_fn, "p3_ink", "InkTide", [V(0, 0, z) for z in (0.4, 1.0, 1.6)], closed_u=True, sharp=70,
                  holes=lambda i, jv: (i, jv) in _inkholes))
# 墨濺碎片（下緣甩出的墨滴）
for q in range(9):
    a = _ir.uniform(0, 6.28); r = _ir.uniform(1.0, 1.55)
    c = V(math.sin(a) * r + 0.45, -math.cos(a) * r * 0.85 + 0.35, _ir.uniform(0.22, 0.6))
    d = V(math.sin(a), -math.cos(a), _ir.uniform(-0.2, 0.4)).normalized()
    ink.append(cone(f"InkSplash{q}", c, d, _ir.uniform(0.12, 0.3), _ir.uniform(0.025, 0.05), "p3_ink", "InkTide", segs=5))
# 下緣暗紅餘燼（≤10%）
hem = [ink_fn(u, 0.93) + V(0, 0, 0.01) for u in np.linspace(0, 1, 27)]
ink.append(B.tube("InkEmber", hem, [(0.006, 0.006)] * 27, 3, "p3_inkedge", "InkTide", cap=False))
for k in range(3):
    a0 = math.radians(60 + k * 90)
    pts_ = []; rad = []
    for s_ in np.linspace(0, 1, 12):
        a = a0 + s_ * 2.4
        r = 0.7 + 0.75 * s_
        z = lerp(1.25 - 0.12 * k, 0.25, s_ ** 0.8) + 0.12 * math.sin(s_ * 9 + k)
        pts_.append(V(math.sin(a) * r + 0.35 * s_, -math.cos(a) * r * 0.8 + 0.35 * s_, z))
        rad.append((lerp(0.03, 0.06, math.sin(math.pi * s_)), lerp(0.10, 0.22, math.sin(math.pi * s_))))
    ink.append(B.tube(f"InkWave{k}", pts_, rad, 6, "p3_ink", "InkTide", up=Z, cap=True))
for k in range(3):
    pts_ = []; rad = []
    a0 = math.radians(-40 + k * 90)
    for s_ in np.linspace(0, 1, 11):
        a = a0 + s_ * (1.6 + 0.25 * k)
        r = 0.45 + 1.05 * s_ ** 1.1
        z = lerp(1.55 - 0.1 * k, 0.22 + 0.05 * k, s_ ** 0.75)
        pts_.append(V(math.sin(a) * r + 0.75 * s_ ** 1.5, -math.cos(a) * r * 0.85 + 0.45 * s_, z))
        rad.append((lerp(0.04, 0.07, math.sin(math.pi * s_)), lerp(0.08, 0.34, math.sin(math.pi * min(1, s_ * 1.3))) + 0.02))
    ink.append(B.tube(f"InkTongue{k}", pts_, rad, 6, "p3_ink", "InkTide", up=Z, cap=True))
ip = random.Random(77)
for q in range(20):
    a = ip.uniform(0, 6.28)
    r = ip.uniform(0.7, 1.35)
    c = V(math.sin(a) * r + 0.3, -math.cos(a) * r * 0.8 + 0.3, ip.uniform(0.25, 1.4))
    yaw = ip.uniform(0, 6.28)
    Tq = V(math.cos(yaw), math.sin(yaw), ip.uniform(-0.3, 0.3)); Dq = V(ip.uniform(-0.4, 0.4), ip.uniform(-0.4, 0.4), -1)
    ink.append(page(f"InkPage{q}", c, Tq, Dq, Tq.cross(Dq), 0.17, 0.34, "InkTide", ip.randrange(6), tilt=ip.uniform(0, 40), cup=0.2, lift=0.3, rg=ip, floor=False))
VH.mark(ink, "P3_InkBody")
# P3_ArmorCrackedChest：約 30% 甲片剝落（同一胸甲曲面挖洞）＋底下裂肉＋熔紅裂縫網
cr = random.Random(31)
holeset = set()
seeds = [(cr.randrange(CU_NU), cr.randrange(2, CU_NV - 1)) for _ in range(10)]
for (si, sj) in seeds:
    rad_ = cr.uniform(1.5, 3.2)
    for i in range(CU_NU):
        for jv in range(CU_NV):
            di = min(abs(i - si), CU_NU - abs(i - si))
            if (di / 1.2) ** 2 + (jv - sj) ** 2 < rad_ ** 2 + cr.uniform(-1, 1):
                holeset.add((i, jv))
print("CRACK holes", len(holeset), "/", CU_NU * CU_NV, flush=True)
crk3 = [cuirass_shell("CrackedCuirass", "gold", "Spine2", holes=lambda i, jv: (i, jv) in holeset, rim=0.016)]
def _flesh_fn(u, v):
    ang = u * 360
    return body.torso.pt(lerp(CU_T0, cu_t1(ang), v), ang, cu_off(ang, v) - 0.018)


crk3.append(B.grid("CrackedFlesh", 20, 7, _flesh_fn, "p3_fleshnet", "Spine2", [V(0, 0, z) for z in np.linspace(CU_T0, CU_TN, 6)], closed_u=True))
for q in range(12):
    a = -8 + cr.uniform(-6, 6); z = h(0.66) + cr.uniform(-0.03, 0.03)          # 從心口往外放射的熔紅裂縫網
    da = cr.uniform(-1, 1); dz = cr.uniform(-1, 1)
    nn = math.hypot(da, dz) or 1
    da, dz = da / nn, dz / nn
    P = []
    for s_ in range(6):
        a += da * cr.uniform(6, 14) + cr.uniform(-4, 4); z += dz * cr.uniform(0.03, 0.06) + cr.uniform(-0.015, 0.015)
        z = clamp(z, CU_T0 + 0.03, cu_t1(a) - 0.03)
        p, n = cu_pt(a, z, lift=-0.010)
        P.append(p)
    crk3.append(B.tube(f"FleshCrack{q}", P, [(0.010 * (1 - k / 7), 0.005) for k in range(6)], 3, "p3_cracks", "Spine2"))
# 心口的熔紅核
p, n = cu_pt(-8, h(0.66), lift=-0.012)
crk3.append(B.ellipsoid("CrackCore", p, (X, Z, n), (0.09, 0.12, 0.025), 12, 4, "p3_cracks", "Spine2", v0=0, v1=0.5))
VH.mark(crk3, "P3_ArmorCrackedChest")
arm3 = []
hs3 = set((cr.randrange(12), cr.randrange(3)) for _ in range(5))
arm3.append(B.shell("CrackedRerebrace", body.uarm, La * 0.45, La * 0.90, 0, 360, 12, 3, "gold", "UpperArmL",
                    off=REREOFF, rim=0.012, holes=lambda i, jv: (i, jv) in hs3))
for c in range(5):
    a = 30 + c * 60
    t = La * (0.55 + 0.07 * (c % 3))
    arm3.append(B.tube(f"ArmCrack{c}", [body.uarm.pt(t - 0.04, a - 8, 0.022), body.uarm.pt(t + 0.0, a + 3, 0.022), body.uarm.pt(t + 0.05, a + 10, 0.022)],
                       [(0.005, 0.005)] * 3, 4, "p3_cracks", "UpperArmL"))
VH.mark(arm3, "P3_ArmorCrackedArm")
# P3_SwordWordsA/B/C：劍外 2 大 1 小的原創符字環（半徑 0.15／0.13／0.09H，劍身 30%／65%／47%）。
# 每個環掛在自己的骨（WordsA/B/C，Weapon 的子骨），動作中保持世界水平、跟著劍身中心移動，最低點不入地。
WORDS_C = {}
for k, (nm, af, rr) in enumerate((("A", 0.30, h(0.15)), ("B", 0.65, h(0.13)), ("C", 0.47, h(0.09)))):
    words = []
    cen = P_sw(lerp(BL0, BL1, af), 0)
    WORDS_C[nm] = cen
    ng = int(2 * math.pi * rr / 0.19)
    tl = math.radians(7 if k != 1 else -5)
    for q in range(ng):
        t = 2 * math.pi * q / ng
        outv = X * math.cos(t) + Y * math.sin(t)
        p = cen + outv * rr + Z * (math.sin(t) * math.tan(tl) * rr)
        tang = Z.cross(outv)
        mat = "p3_glyphG" if q % 5 == 0 else "p3_glyph"
        words += glyph(f"Word{nm}{q}", p, tang, Z, 0.085, mat, "Words" + nm, k * 40 + q, width=0.008, th=0.003, segs=3, cap=False)
    for e in (-1, 1):
        ring = [cen + (X * math.cos(t) + Y * math.sin(t)) * rr + Z * (math.sin(t) * math.tan(tl) * rr + e * 0.05) for t in np.linspace(0, 2 * math.pi, 25)]
        words.append(B.tube(f"WordRing{nm}{e}", ring, [(0.003, 0.003)] * 25, 3, "p3_glyph", "Words" + nm, cap=False))
    VH.mark(words, "P3_SwordWords" + nm)

# ================================================================ 骨架、烘焙
arm = build_armature("BossDevourer", body, weapon=(gcR, gcR + AX * 0.40),
                     chains=[(cn, "Spine2", pts_) for cn, (nm_, pts_) in CAPE_CH.items()] + [("TabardF", "Hips", tf_pts)],
                     extra=[("WingL", "Spine2", WING[1], WING[1] + V(0.4, 0.05, 0.1)), ("WingR", "Spine2", WING[-1], WING[-1] + V(-0.4, 0.05, 0.1)),
                            ("InkTide", "Root", V(0, 0, body.hzv), V(0, 0, body.hzv + 0.3)),
                            ("CapeGround", "Root", V(0, 0, body.hzv), V(0, 0, body.hzv + 0.3))] +
                           [("Words" + nm, "Weapon", c, c + Z * 0.2) for nm, c in WORDS_C.items()])
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS(before polish)", tri, flush=True)
if os.environ.get("V3_TALLY"):
    import re as _re
    tal = {}
    for o in B.parts:
        k = _re.sub(r"[0-9_\-.]+(R)?$", "", o.name)
        k = _re.sub(r"\d+", "", k)
        tal[k] = tal.get(k, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons) * (2 if o.get("cloth") else 1)
    print("TALLY", sorted(tal.items(), key=lambda x: -x[1])[:45], flush=True)
    if os.environ.get("V3_TALLY") == "exit":
        sys.exit(0)
DETAIL_OF = {"gold": "metal", "goldP": "metal", "mawflesh": "leather", "iron": "metal", "ironD": "metal", "blade": "metal", "bone": "bone", "horn": "bone",
             "linen": "cloth", "tabard": "cloth", "lining": "cloth", "leather": "leather", "flesh": "leather", "glove": "leather", "palm": "leather"}.get
# 量測用的部位分類（點屬性 mcls；匯出時不輸出）：1 披風書頁／內襯、3 配件、8 布腰帶、9 肩甲、0 其他
def _mcls(n):
    if n.startswith(("CapeLining", "Page", "PageIn", "GroundPage", "ArmPage", "Wing", "InkPage")):
        return 1
    if n.startswith(("Sash1", "Sash2")):
        return 8
    if n.startswith(("SashKnot", "SashTail", "Belt2", "Buckle", "HangChain", "Pendant", "Swag", "Scroll", "Tabard")):
        return 3
    if n.startswith(("Pauldron", "Medal", "ShSpike")):
        return 9
    return 0


for o in B.parts:
    at = o.data.attributes.new("mcls", "INT", "POINT")
    c = _mcls(o.name)
    at.data.foreach_set("value", [c] * len(o.data.vertices))
mesh = VH.assemble3(B, BAKEKEY, size=(TEXS, TEXS), bake=not QUICK, quick=QUICK, detail_of=DETAIL_OF, U=1.0)
BONE_OF = {"P2_ChestMaw": "Spine2", "P2_ScriptChest": "Spine2", "P2_ScriptL": "UpperArmL", "P2_ScriptR": "UpperArmR", "P2_ScriptLegL": "ThighL",
           "P2_ScriptLegR": "ThighR", "P2_SwordCracks": "Weapon", "P2_PageWingL": "WingL", "P2_PageWingR": "WingR", "P3_Crown": "Head",
           "P3_HornBrokenR": "Head", "P3_HornBrokenL": "Head", "P3_HornBrokenR2": "Head", "P3_EyeFlames": "Head", "P3_InkBody": "InkTide",
           "P3_ArmorCrackedChest": "Spine2", "P3_ArmorCrackedArm": "UpperArmL", "P3_SwordWordsA": "WordsA", "P3_SwordWordsB": "WordsB", "P3_SwordWordsC": "WordsC"}
ORIGIN_OF = {"P3_Crown": V(0, 0, h(0.80)), "P2_PageWingL": WING[1], "P2_PageWingR": WING[-1]}.get
parts = VH.split_parts(mesh, arm, lambda n: BONE_OF[n], origin_of=ORIGIN_OF)
BK.bind(mesh, arm)
mesh.name = MODEL + "_mesh"
x3 = VH.split_x3(mesh, arm)
for o in x3.values():
    if not any(m.type == "ARMATURE" for m in o.modifiers):
        md = o.modifiers.new("Armature", "ARMATURE"); md.object = arm
    o.parent = arm
VH.drop_src_uv([mesh] + list(parts.values()) + list(x3.values()))
# 劍尖空節點 Tip_Weapon（掛 Weapon 骨）
tipo = bpy.data.objects.new("Tip_Weapon", None)
bpy.context.scene.collection.objects.link(tipo)
tipo.location = SWORD_TIP
bpy.context.view_layer.update()
mw = tipo.matrix_world.copy()
tipo.parent = arm; tipo.parent_type = "BONE"; tipo.parent_bone = "Weapon"
bpy.context.view_layer.update()
tipo.matrix_world = mw
print("TRIS_MAIN", BK.tri_count(mesh), "TRIS_X3", sum(BK.tri_count(o) for o in x3.values()), "TRIS_P", sum(BK.tri_count(o) for o in parts.values()), flush=True)

# ================================================================ 動作
legs = [("ThighL", "ShinL", 0.15 * U), ("ThighR", "ShinR", 0.15 * U), ("ShinL", "FootL", 0.12 * U), ("ShinR", "FootR", 0.12 * U)]
rig = Rig(arm, body, chains=[])          # 披風／前擺鏈改由 v3_devourer_secondary 逐格模擬（含地面約束）
TIP = BL1 / U
rig.tip_len = BL1
rig.lie_dz = 0.16
import v3_devourer_actions as ACT
WP = ACT.weapon_poses(rig, TIP)
if not NOANIM:
    ACT.build(rig, lambda key, p: WP[key](p), primary="over", slow=1.1, only=ONLY, wide=1.55)
    import v3_devourer_secondary as SEC
    SEC.run(arm, rig, ink_obj=parts.get("P3_InkBody"), words={k: ("Words" + k[-1], parts[k]) for k in parts if k.startswith("P3_SwordWords")},
            log=lambda m: print(m, flush=True), tip_rest=SWORD_TIP)

all_objs = [mesh] + list(parts.values()) + list(x3.values()) + [tipo]
if not ONLY and not NOANIM:
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    VH.export_glb(arm, all_objs, OUT_GLB)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
for o in all_objs:
    o["v3kind"] = "x3" if o.name.startswith("X3_") else ("part" if o.name.startswith(("P2_", "P3_")) else "main")
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("TRIS_FINAL", BK.tri_count(mesh) + sum(BK.tri_count(o) for o in parts.values()) + sum(BK.tri_count(o) for o in x3.values()), flush=True)
print("DONE", MODEL, flush=True)
