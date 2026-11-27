"""v3 暗影行刑者 boss_executioner（依 art/v3/specs/boss_executioner.md 重建）。
比例以 HT（頭罩尖到靴底）=1 定義；材質用 CC0 貼圖＋程序化節點（v3_executioner_mats），縫線／扣孔／纏皮紋等細節件只進高模烘到法線。
左右：本腳本的 L／R 是「角色自己的」左右。spec 的左右是看圖的左右（圖左＝角色右手），對照見報告。
用法：blender --background --factory-startup --python v3_executioner.py -- [--quick] [--noanim] [--only A,B]
"""
import bpy, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from soul_humanoid_lib import *
from soul_humanoid_parts import angn, rag_profile, box, _tri
import soul_humanoid_bake as BK
from soul_humanoid_anim import Rig, W, HW
import v3_executioner_hum as VH
import v3_executioner_mats as MT
from v3_executioner_body import ExBody

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOANIM = "--noanim" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_executioner"
BAKEKEY = "v3_executioner"
ROOT = os.path.dirname(os.path.dirname(HERE))
TMP = os.path.join(ROOT, "art", "v3", "tmp", "executioner")
BK.BAKED = os.path.join(TMP, "baked")
os.makedirs(BK.BAKED, exist_ok=True)
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v3_executioner.blend")
TEXS = int(os.environ.get("BOSS_TEX", "2048"))

reset_scene()
HT = 2.4
body = ExBody(HT)
U = body.U; j = body.j


def h(x):
    return x * HT


def g(x, c, w):
    return math.exp(-((x - c) / w) ** 2)


B = Builder()           # 低模（最終網格）
BD = Builder()          # 只進高模的細節件
rnd = random.Random(21)
PURPLE = (0.43, 0.19, 1.0)

# ================================================================ 材質
D = MT.define
# A 組：皮膚、皮革、布
D("skin", "A", "#7a5a4e", tex="Leather026", tex_size=0.10, contrast=0.6, rough=0.62, rough_var=0.08, bump=0.5, bump_dist=0.0025,
  dirt=0.55, dirt_col="#3a2a22", veins=0.55, scars=0.25, stain=0.2, stain_col="#3a2a22", seed=1.0, light="#86604e", dark="#5a3c30")
D("skinInk", "A", "#7a5a4e", tex="Leather026", tex_size=0.10, contrast=0.6, rough=0.62, rough_var=0.08, bump=0.5, bump_dist=0.0025,
  dirt=0.55, dirt_col="#3a2a22", veins=0.55, scars=0.2, seed=2.0, light="#86604e", dark="#5a3c30",
  ink=(Body.mir(j["ForearmL"]), Body.mir(body.fd), body.fa_len))
D("leatherBk", "A", "#1e1a18", tex="Leather026", tex_size=0.25, contrast=1.2, rough=0.66, rough_var=0.12, bump=0.8, wrinkle=0.6,
  wear=0.6, wear_col="#3e352e", dirt=0.5, stain=0.35, stain_scale=0.7, seed=3.0, light="#2a2420", dark="#161311")
D("strap", "A", "#4a3528", tex="Leather026", tex_size=0.22, contrast=1.1, rough=0.62, rough_var=0.1, bump=0.7, wrinkle=0.35,
  wear=0.9, wear_col="#7a5c44", dirt=0.6, seed=4.0, light="#56402f", dark="#3a2a20")
D("strapDk", "A", "#2a201a", tex="Leather026", tex_size=0.22, contrast=1.1, rough=0.68, bump=0.7, wrinkle=0.35,
  wear=0.7, wear_col="#55402f", dirt=0.6, seed=5.0)
D("pants", "A", "#151412", tex="Leather026", tex_size=0.3, contrast=1.2, rough=0.7, bump=0.9, wrinkle=0.9, wrinkle_stretch=(1.0, 1.0, 5.0),
  wear=0.4, wear_col="#2e2a26", dirt=0.6, stain=0.2, seed=6.0, light="#1c1a17", dark="#100f0d")
D("boot", "A", "#1a1714", tex="Leather026", tex_size=0.3, contrast=1.2, rough=0.7, bump=0.9, wrinkle=0.8, wrinkle_stretch=(1.0, 3.0, 1.0),
  wear=0.5, wear_col="#4a4038", dirt=0.7, stain=0.35, stain_z=(0.0, 0.12 * HT), stain_col="#2a2018", seed=7.0)
D("burlap", "A", "#5a4a36", tex="Fabric030", tex_size=0.18, contrast=0.7, rough=0.9, rough_var=0.05, bump=1.0, bump_dist=0.0035,
  weave=(0.0096, 0.45), dirt=0.55, dirt_col="#2a2219", stain=0.15, stain_col="#3a2a1c", seed=8.0, light="#6e5c44", dark="#3e3326")
D("burlapM", "A", "#4e4030", tex="Fabric030", tex_size=0.18, contrast=0.7, rough=0.92, bump=1.0, bump_dist=0.0035,
  weave=(0.0096, 0.45), dirt=0.65, dirt_col="#241c14", stain=0.18, stain_col="#3a2418", seed=9.0, light="#5e4c38", dark="#3a2f22")
D("burlapA", "A", "#4e4333", tex="Fabric030", tex_size=0.18, contrast=0.7, rough=0.92, bump=1.0, bump_dist=0.0035,
  weave=(0.0096, 0.45), dirt=0.6, dirt_col="#241c14", stain=0.75, stain_col="#3a2418", stain_z=(0.17 * HT, 0.40 * HT), seed=10.0,
  light="#5c4f3c", dark="#3a3126")
D("thread", "A", "#2a2016", rough=0.85, bump=0.4, dirt=0.2, seed=11.0)
D("void", "A", "#050406", rough=1.0, bump=0.0, dirt=0.0, ao_shade=0.0)
# B 組：鐵、刃、木、金
IRON = dict(tex="Metal024", tex_size=0.5, contrast=0.45, rough=0.58, rough_var=0.1, metal=0.92, bump=1.0, bump_dist=0.005,
            hammer=(0.026, 0.38), scratch=0.25, wear=1.0, wear_col="#7a746c", rust=0.5, rust_col="#4a2e20", dirt=0.6,
            dirt_col="#120e0c", light="#323234", dark="#222224")
D("iron", "B", "#2a2a2c", seed=12.0, stain=0.2, **IRON)
D("ironP", "B", "#2a2a2c", seed=13.0, stain=0.45, stain_scale=0.7, **IRON)        # 胸板（污漬多）
D("ironR", "B", "#4a3c34", tex="Metal024", tex_size=0.4, rough=0.6, metal=0.8, bump=0.8, hammer=(0.02, 0.5), rust=0.8,
  rust_col="#5a3a28", wear=0.8, wear_col="#7a6a60", dirt=0.7, seed=14.0)
D("chain", "B", "#4a4846", tex="Metal024", tex_size=0.3, rough=0.5, metal=0.9, bump=0.7, rust=0.45, rust_col="#5a3a28",
  wear=0.9, wear_col="#7a7672", dirt=0.6, seed=15.0)
D("blade", "B", "#5e5954", tex="Metal024", tex_size=0.6, contrast=0.6, rough=0.55, rough_var=0.08, metal=1.0, bump=0.6,
  scratch=0.25, wear=0.0, wear_col="#7a7670", rust=0.15, dirt=0.5, stain=0.75, stain_scale=0.8, seed=16.0)
D("bladeEdge", "B", "#b8b4ac", tex="Metal024", tex_size=0.4, contrast=0.4, rough=0.22, rough_var=0.05, metal=1.0, bump=0.4,
  scratch=1.0, wear_col="#d8d4cc", dirt=0.2, stain=0.3, seed=17.0)
D("wood", "B", "#2b2019", tex="Wood066", tex_size=0.35, contrast=1.2, rough=0.6, bump=0.8, wear=0.6, wear_col="#4a3a2e", dirt=0.5, seed=18.0)
D("wrap", "B", "#3a2420", tex="Leather026", tex_size=0.15, rough=0.7, bump=0.8, wrinkle=0.4, wear=0.8, wear_col="#5a3c30", dirt=0.6, seed=19.0)
D("gold", "B", "#d4a64a", tex="Metal024", tex_size=0.3, contrast=0.5, rough=0.3, rough_var=0.06, metal=1.0, bump=0.5, rings=60.0,
  wear=0.8, wear_col="#f0cc78", dirt=0.6, dirt_col="#3a2a10", seed=20.0)
D("strapB", "B", "#2a201a", tex="Leather026", tex_size=0.22, rough=0.68, bump=0.7, wrinkle=0.35, wear=0.7, wear_col="#55402f", dirt=0.6, seed=21.0)
D("threadB", "B", "#2a2016", rough=0.85, bump=0.4, dirt=0.2, seed=22.0)
D("voidB", "B", "#050406", rough=1.0, bump=0.0, dirt=0.0, ao_shade=0.0)
# 發光／墨影
VH.define_glow("g_eye", PURPLE, 3.0, final="Glow_Eye")
VH.define_glow("g_weapon", PURPLE, 1.6, final="Glow_Weapon")
gr = VH.define_glow("g_rune", PURPLE, 0.2, final="Glow_Rune", base=(0.012, 0.006, 0.022))
gr["alpha"] = 0.22
VH.define_ink("ink", color=(0.0034, 0.0030, 0.0048), alpha=0.86, emit=(0.30, 0.12, 0.60), emit_strength=0.0, final="Ink")
VH.define_ink("ink2", color=(0.0034, 0.0030, 0.0048), alpha=0.55, emit=(0.30, 0.12, 0.60), emit_strength=0.0, final="InkThin")
VH.define_glow("p2_edge", PURPLE, 2.4, final="P2_Glow_Edge")
ps = VH.define_glow("p2_shadow", PURPLE, 0.3, final="P2_Glow_Shadow", base=(0.012, 0.006, 0.024))
ps["alpha"] = 0.25
VH.define_glow("p2_vein", PURPLE, 2.2, final="P2_Glow_Vein")
VH.define_ink("p2_ink", color=(0.0034, 0.0030, 0.0048), alpha=0.78, emit=(0.30, 0.12, 0.65), emit_strength=0.02, final="P2_InkShadow")


def make_void_tex(path, S=256):
    """紫色漩渦（emissive 貼圖）：外圈暗、往中心旋入發亮——畫成凹陷的洞。"""
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = (x + 0.5) / S * 2 - 1; cy = (y + 0.5) / S * 2 - 1
    r = np.sqrt(cx * cx + cy * cy); th = np.arctan2(cy, cx)
    arm = (0.5 + 0.5 * np.sin(3 * (th + 6.0 * r))) ** 2.0
    depth = np.clip(1 - r, 0, 1)
    inten = arm * depth ** 0.8 * 1.6 + 0.9 * np.exp(-(r / 0.16) ** 2)
    inten *= np.clip((1.0 - r) / 0.25, 0, 1)        # 外緣全黑（洞口陰影）
    inten = np.clip(inten, 0, 1)
    col = np.stack([0.43 * inten + 0.55 * inten ** 4, 0.19 * inten + 0.5 * inten ** 4, 1.0 * inten, np.ones_like(inten)], -1)
    im = bpy.data.images.new("v3_void", S, S, alpha=True)
    im.pixels.foreach_set(np.clip(col, 0, 1).astype(np.float32).ravel())
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)
    return path


VOID_TEX = make_void_tex(os.path.join(BK.BAKED, "v3_exe_void.png"))
VH.define_glow("p2_void", PURPLE, 2.6, final="P2_Glow_Void", tex=VOID_TEX, base=(0.0, 0.0, 0.0))

DETAIL_OF = {"iron": "metal", "ironP": "metal", "ironR": "metal", "blade": "metal", "bladeEdge": None, "gold": None, "chain": None,
             "leatherBk": "leather", "strap": "leather", "strapDk": "leather", "strapB": "leather", "pants": "leather", "boot": "leather",
             "burlap": "cloth", "burlapM": "cloth", "burlapA": "cloth", "wood": "wood", "wrap": None, "skin": None, "skinInk": None}.get


# ================================================================ 小工具
def rot_about(v, axis, ang):
    return Quaternion(axis, ang) @ v


def stitches(name, pts, nrm_fn, mat="thread", w="Hips", step=None, ln=None, r=None, B_=None):
    """沿點列的縫線（每針一小段管），只進高模。nrm_fn(p)->表面法線。"""
    B_ = B_ or BD
    step = step or h(0.008); ln = ln or h(0.005); r = r or h(0.0012)
    # 重新取樣
    acc = [0.0]
    for k in range(1, len(pts)):
        acc.append(acc[-1] + (pts[k] - pts[k - 1]).length)
    out = []
    s = step * 0.5
    while s < acc[-1]:
        k = max(0, min(len(pts) - 2, int(np.searchsorted(acc, s) - 1)))
        f = (s - acc[k]) / max(1e-6, acc[k + 1] - acc[k])
        p = pts[k].lerp(pts[k + 1], f)
        d = (pts[k + 1] - pts[k]).normalized()
        n = nrm_fn(p)
        sd = n.cross(d).normalized()
        a = p - d * ln * 0.5 + sd * ln * 0.25 + n * r * 0.6
        b = p + d * ln * 0.5 - sd * ln * 0.25 + n * r * 0.6
        out.append((a, b, n))
        s += step
    obs = []
    for i, (a, b, n) in enumerate(out):
        obs.append(B_.tube(f"{name}{i}", [a, b], [r, r], 4, mat, w, flat=n, stack_uv=True))
    return obs


def chain(name, pts, mat, w, link=None, wire=None, nu=6, nv=3, B_=None, twist0=0):
    """沿折線的鍛鐵鍊（每節一個獨立的環，相鄰兩節轉 90 度）。link：環外長；wire：線徑（直徑）。"""
    B_ = B_ or B
    link = link or h(0.025); wire = wire or h(0.005)
    wr = wire * 0.5
    stepl = link - 2 * wire * 0.9
    acc = [0.0]
    for k in range(1, len(pts)):
        acc.append(acc[-1] + (pts[k] - pts[k - 1]).length)
    cs = []
    s = 0.0
    while s <= acc[-1] + 1e-6:
        k = max(0, min(len(pts) - 2, int(np.searchsorted(acc, s) - 1)))
        f = (s - acc[k]) / max(1e-6, acc[k + 1] - acc[k])
        cs.append(pts[k].lerp(pts[k + 1], min(1.0, f)))
        s += stepl
    obs = []
    hl = link * 0.5 - wr
    lr = link * 0.30 - wr
    prev = None
    for k in range(len(cs) - 1):
        a, b = cs[k], cs[k + 1]
        dvec = b - a
        if dvec.length < 1e-6:
            continue
        e2 = dvec.normalized()
        ref = prev if prev is not None else (Z if abs(e2.dot(Z)) < 0.9 else X)
        e1 = (ref - e2 * ref.dot(e2)).normalized()
        if (k + twist0) % 2:
            e1 = e2.cross(e1).normalized()
        prev = e1 if (k + twist0) % 2 == 0 else e2.cross(e1).normalized()
        c = (a + b) / 2
        n3 = e1.cross(e2)

        def fn(u, v, c=c, e1=e1, e2=e2, n3=n3):
            A = 2 * math.pi * u; Bv = 2 * math.pi * v
            # 跑道形：兩端半圓＋直邊
            ca, sa = math.cos(A), math.sin(A)
            ring = e2 * (ca * hl) + e1 * (sa * lr)
            rn = (e2 * ca * lr + e1 * sa * hl).normalized()
            return c + ring + (rn * math.cos(Bv) + n3 * math.sin(Bv)) * wr
        ww = w(c) if callable(w) else w
        obs.append(B_.grid(f"{name}{k}", nu, nv, fn, mat, ww, [c + e2 * hl * 0.5, c - e2 * hl * 0.5, c + e1 * lr * 0.5, c - e1 * lr * 0.5],
                           closed_u=True, closed_v=True, stack_uv=True, sharp=70))
    return obs, cs


def catenary(p0, p1, sag, n=24, out=None, out_amt=0.0):
    pts = []
    for q in range(n + 1):
        s = q / n
        p = p0.lerp(p1, s) - Z * (sag * 4 * s * (1 - s))
        if out is not None:
            p += out(s) * (out_amt * 4 * s * (1 - s))
        pts.append(p)
    return pts


def cone(name, base, d, ln, r0, mat, w, segs=6, B_=None):
    B_ = B_ or B
    d = d.normalized()
    return B_.tube(name, [base - d * r0 * 0.4, base + d * ln * 0.45, base + d * ln], [r0, r0 * 0.5, 0.0006 * U], segs, mat, w, sharp=35)


def wisp(name, base, d, length, side, mat, w, width=0.016, thick=0.003, curl=0.35, n=6, seed=0, up=0.0, rim=None, B_=None, twist=1.3):
    """墨煙：從 base 往 d 飄散的扭轉帶狀煙（先變寬再收細、沿長度扭轉），可加一層較寬的紫邊殼＝邊緣 fresnel 的替代。"""
    B_ = B_ or B
    r_ = random.Random(seed)
    d = d.normalized(); side = (side - d * side.dot(d))
    if side.length < 1e-4:
        side = d.orthogonal()
    side.normalize(); nrm = d.cross(side)
    ph = r_.uniform(0, 6.28)
    pts = []
    for k in range(n):
        s = k / (n - 1)
        p = base + d * (length * s) + side * (curl * length * math.sin(s * 2.8 + ph) * s) + nrm * (0.35 * curl * length * math.sin(s * 4.2 + ph * 2) * s) + Z * (up * length * s * s)
        pts.append(p)
    tw = twist * (1 if r_.random() > 0.5 else -1)

    def mk(scale, extra):
        def fn(u, v):
            k = min(int(v * (n - 1)), n - 2); f = v * (n - 1) - k
            p = pts[k].lerp(pts[k + 1], f)
            tg = (pts[k + 1] - pts[k]).normalized()
            a = tw * math.pi * v + ph
            e1 = side * math.cos(a) + nrm * math.sin(a)
            e1 = (e1 - tg * e1.dot(tg)).normalized(); e2 = tg.cross(e1)
            wd = h(width) * (0.55 + 0.9 * math.sin(math.pi * min(1.0, v * 1.25 + 0.1))) * (1 - v) ** 0.5 + h(0.0008)
            th = h(thick) * (1 - 0.6 * v) + h(0.0005)
            A = 2 * math.pi * u
            return p + e1 * (math.cos(A) * (wd * scale + extra)) + e2 * (math.sin(A) * (th * scale + extra * 0.6))
        return fn
    obs = [B_.grid(name, 6, n - 1, mk(1.0, 0.0), mat, w, pts, closed_u=True, sharp=80)]
    if rim:
        obs.append(B_.grid(name + "Rim", 6, n - 1, mk(1.3, h(0.001)), rim, w, pts, closed_u=True, sharp=80))
    return obs


def surf_grid(name, surf, t0, t1, a0, a1, nu, nv, mat, w, offf, **kw):
    return B.shell(name, surf, t0, t1, a0, a1, nu, nv, mat, w, off=offf, **kw)


TS = body.torso
WT = body.w_torso()

# ================================================================ 軀幹：黑皮革胸甲＋鐵胸板＋腹部三片皮甲
B.shell("Tunic", TS, h(0.375), h(0.815), 0, 360, 28, 16, "leatherBk", WT, off=h(0.004), cap0=True, texel=1.0)


def pec_t0(u):
    return h(0.648) - h(0.012) * math.sin(math.pi * u)


for sx in (1, -1):
    a0, a1 = (5, 78)

    def pec_off(u, v, ang, t):
        pv = min(v / 0.30, 1.0, (1 - v) / 0.22)                  # 上緣平、下緣收（倒角）
        pu = min(u / 0.16, 1.0, (1 - u) / 0.28)                  # 中線凹、外側收
        ridge = 0.004 * max(0.0, 1 - abs(v - 0.42) / 0.06)       # 中段一道橫稜
        return h(0.012) + h(0.015) * max(0.0, min(pv, pu)) ** 0.7 + h(ridge) * pu

    ob = B.shell("PecPlate", TS, pec_t0, lambda u: h(0.772) - h(0.03) * u, a0, a1, 14, 8, "ironP", "Spine2", off=pec_off, rim=h(0.004))
    if sx < 0:
        B.mirror_only([ob])
    else:
        # 胸板外緣鉚釘
        pts = []
        for q in range(6):
            u = 0.08 + 0.84 * q / 5
            a = lerp(a0, a1, u)
            t = pec_t0(u) + h(0.008)
            pts.append((TS.pt(t, a, pec_off(u, 0.06, a, t) + h(0.002)), TS.nrm(t, a)))
        for q in range(3):
            t = lerp(h(0.66), h(0.75), q / 2)
            pts.append((TS.pt(t, a0 + 4, h(0.013)), TS.nrm(t, a0 + 4)))
        B.both(B.rivets("PecRivet", pts, "iron", "Spine2", r=h(0.0045)))
        # 胸板捲邊（下緣＋中線側）
        rl = [TS.pt(pec_t0(u), lerp(a0, a1, u), pec_off(u, 0.0, 0, 0) + h(0.003)) for u in np.linspace(0.0, 1.0, 14)]
        ri = [TS.pt(lerp(pec_t0(0.0), h(0.772), v), a0, pec_off(0.0, v, 0, 0) + h(0.003)) for v in np.linspace(0.0, 1.0, 8)]
        B.both([B.tube("PecRoll", rl, [h(0.0035)] * 14, 5, "iron", "Spine2"), B.tube("PecRollIn", ri, [h(0.0035)] * 8, 5, "iron", "Spine2")])
# 中央垂直皮帶、胸下水平束帶
B.shell("ChestStrapV", TS, h(0.57), h(0.80), -5.0, 5.0, 2, 12, "strapDk", WT, off=lambda u, v, a, t: h(0.020) + h(0.012) * math.sin(math.pi * min(1.0, (t - h(0.57)) / h(0.2))), rim=h(0.003))
B.shell("ChestStrapH", TS, h(0.625), h(0.643), 0, 360, 36, 1, "strapDk", "Spine2", off=lambda u, v, a, t: h(0.012) + (h(0.010) if abs(angn(a)) < 80 else 0) * math.exp(-(angn(a) / 70) ** 2), rim=h(0.002))
B.rivets("ChestStrapRiv", [(TS.pt(h(0.634), a, h(0.0245)), TS.nrm(h(0.634), a)) for a in (-60, -30, 30, 60, 100, -100, 140, -140, 180)], "iron", "Spine2", r=h(0.004))
for k in range(3):
    z0 = h(0.566 + 0.021 * k)

    def ab_off(u, v, a, t, k=k):
        return h(0.009 + 0.0025 * (2 - k)) + h(0.004) * (1 - v)
    B.shell(f"AbBand{k}", TS, z0, z0 + h(0.027), -105, 105, 18, 2, "leatherBk", {"Spine": 0.6, "Hips": 0.2, "Spine2": 0.2}, off=ab_off, rim=h(0.003))
    B.rivets(f"AbRiv{k}", [(TS.pt(z0 + h(0.012), a, ab_off(0, 0.5, a, 0) + h(0.0015)), TS.nrm(z0 + h(0.012), a)) for a in (-92, -45, 45, 92)], "iron", "Spine", r=h(0.0035))
# 背後：交叉皮帶＋背板
for sx in (1, -1):
    pts = []
    for q in range(9):
        s = q / 8
        a = sx * lerp(140, 205, s)
        z = lerp(h(0.79), h(0.57), s)
        pts.append(TS.pt(z, a, h(0.014)))
    B.tube(f"BackStrap{sx}", pts, [(h(0.012), h(0.003))] * len(pts), 4, "strapDk", WT, flat=None, up=Z, exp=4.0)
B.shell("BackPlate", TS, h(0.64), h(0.76), 150, 210, 10, 6, "iron", "Spine2", off=lambda u, v, a, t: h(0.020) + h(0.006) * math.sin(math.pi * u), rim=h(0.003))
B.rivets("BackRiv", [(TS.pt(z, a, h(0.024)), TS.nrm(z, a)) for z in (h(0.65), h(0.75)) for a in (155, 205)], "iron", "Spine2", r=h(0.004))
# 皮革縫線（雙行）：腹甲上下緣、胸帶兩側
for k in range(3):
    z0 = h(0.566 + 0.021 * k)
    for dz in (h(0.004), h(0.023)):
        pts = [TS.pt(z0 + dz, a, h(0.009 + 0.0025 * (2 - k)) + h(0.004) * 0.5 + h(0.0015)) for a in np.linspace(-100, 100, 30)]
        stitches(f"AbSt{k}{int(dz * 1000)}", pts, lambda p: Vector((p.x, p.y, 0)).normalized(), w="Spine")
for sx in (1, -1):
    pts = [TS.pt(z, sx * 3.5, h(0.0185)) for z in np.linspace(h(0.58), h(0.79), 20)]
    stitches(f"CSt{sx}", pts, lambda p: TS.nrm(p.z, 0), w="Spine2")
for z in (h(0.629), h(0.639)):
    pts = [TS.pt(z, a, h(0.0135)) for a in np.linspace(80, 280, 30)]
    stitches(f"CHSt{int(z * 1000)}", pts, lambda p: Vector((p.x, p.y, 0)).normalized(), w="Spine2")
# 腋下與腹側的皺褶（細節件：折痕脊）
for sx in (1, -1):
    for q in range(4):
        a = sx * (95 + q * 8)
        p0 = TS.pt(h(0.70 - 0.01 * q), a, h(0.0055)); p1 = TS.pt(h(0.66 - 0.012 * q), a + sx * 12, h(0.0055))
        BD.tube(f"Crease{sx}{q}", [p0, p0.lerp(p1, 0.5) + TS.nrm(h(0.68), a) * h(0.002), p1], [h(0.002), h(0.003), h(0.0015)], 5, "leatherBk", "Spine2")

# ================================================================ 皮帶 ×2、方框鐵扣、扣孔
def belt_fn(z, wd, off0, thick, tilt=0.0, tdir=-60):
    def fn(u, v):
        ang = u * 360
        zz = z - tilt * math.cos(math.radians(ang - tdir))
        k = int(round(v * 3))
        dz = (-wd / 2, -wd / 2, wd / 2, wd / 2)[k]
        o = (off0 - h(0.003), off0 + thick, off0 + thick, off0 - h(0.003))[k]
        return TS.pt(zz + dz, ang, o)
    return fn


ZB1, ZB2 = h(0.555), h(0.52)
B.grid("Belt1", 40, 3, belt_fn(ZB1, h(0.03), h(0.011), h(0.006)), "strap", {"Spine": 0.35, "Hips": 0.65}, [V(0, 0, ZB1)], closed_u=True, sharp=30)
B.grid("Belt2", 40, 3, belt_fn(ZB2, h(0.03), h(0.016), h(0.006), tilt=h(0.012), tdir=-70), "strap", "Hips", [V(0, 0, ZB2)], closed_u=True, sharp=30)


def belt_pt(z, a, off, tilt=0.0, tdir=-70):
    return TS.pt(z - tilt * math.cos(math.radians(a - tdir)), a, off)


def buckle_frame(name, c, n, up, size, w, mat="iron"):
    side = up.cross(n).normalized()
    s = size * 0.5
    corners = [c + side * s + up * s, c - side * s + up * s, c - side * s - up * s, c + side * s - up * s]
    obs = []
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        obs.append(B.tube(f"{name}F{k}", [a, b], [(h(0.0045), h(0.003))] * 2, 6, mat, w, flat=n, exp=3.0))
    obs.append(B.tube(f"{name}Tongue", [c + up * s * 0.9 + n * h(0.003), c + n * h(0.004), c - up * s * 0.2 + n * h(0.004)], [h(0.0025)] * 3, 5, mat, w))
    return obs


for (z, a, off, tilt, nm) in ((ZB1, 0.0, h(0.018), 0.0, "Buckle1"), (ZB2, -24.0, h(0.023), h(0.012), "Buckle2")):
    c = belt_pt(z, a, off, tilt)
    n = TS.nrm(z, a)
    wgt = {"Spine": 0.35, "Hips": 0.65} if nm == "Buckle1" else "Hips"
    buckle_frame(nm, c + n * h(0.002), n, Z, h(0.04), wgt)
    # 扣孔（細節：凹孔）＋皮帶尾
    for q in range(4):
        aa = a + 9 + q * 4.5
        p = belt_pt(z, aa, off + h(0.0015), tilt)
        BD.ellipsoid(f"{nm}Hole{q}", p, (Z.cross(TS.nrm(z, aa)), Z, TS.nrm(z, aa)), (h(0.003), h(0.003), h(0.0015)), 8, 4, "void", wgt)
    tail = [belt_pt(z, a - 6 - 5 * q, off + h(0.005), tilt) + TS.nrm(z, a - 6 - 5 * q) * h(0.001) - Z * h(0.004 * q * q) for q in range(4)]
    B.tube(f"{nm}Tail", tail, [(h(0.014), h(0.003))] * 4, 4, "strap", wgt, up=Z, exp=4)
B.both(B.rivets("BeltStuds", [(belt_pt(ZB1, a, h(0.0175)), TS.nrm(ZB1, a)) for a in (40, 70, 110, 150)], "iron", {"Spine": 0.35, "Hips": 0.65}, r=h(0.0045)))
for nm_, z, off, tilt in (("B1", ZB1, h(0.017), 0.0), ("B2", ZB2, h(0.022), h(0.012))):
    for dz in (-h(0.012), h(0.012)):
        pts = [belt_pt(z + dz, a, off, tilt) for a in np.linspace(0, 360, 80)]
        stitches(f"BeltSt{nm_}{int(dz * 1e4)}", pts, lambda p: Vector((p.x, p.y, 0)).normalized(), w="Hips", step=h(0.006))


# ================================================================ 腰鍊（3 條 U 形垂鍊＋3 條直垂掛鎖）
def w_low(c):
    z_hi, z_lo = ZB2, h(0.28)
    s = smooth((z_hi - c.z) / (z_hi - z_lo)) * 0.55
    l = smooth(0.5 + c.x / h(0.10))
    return {"Hips": 1 - s, "ThighL": s * l, "ThighR": s * (1 - l)}


def padlock(name, top, face, s=1.0, mat="ironR", w=None, B_=None):
    B_ = B_ or B
    face = Vector((face.x, face.y, 0)).normalized()
    side = Z.cross(face).normalized()
    hw, hh, ht = h(0.020) * s, h(0.0225) * s, h(0.0075) * s
    c = top - Z * (hh + h(0.018) * s)
    w = w or w_low
    ww = w(c) if callable(w) else w
    obs = []
    sh = [c + Z * hh * 0.8 + side * hw * 0.62]
    for t in np.linspace(0, math.pi, 7):
        sh.append(c + Z * (hh * 0.9 + h(0.016) * s * math.sin(t)) + side * hw * 0.62 * math.cos(t))
    sh.append(c + Z * hh * 0.8 - side * hw * 0.62)
    obs.append(B_.tube(name + "Shackle", sh, [h(0.0035) * s] * len(sh), 6, "chain", ww))
    obs.append(box(B_, name + "Body", c, side, Z, face, hw, hh, ht, mat, ww, exp=3.0, segs=14))
    obs.append(B_.tube(name + "Frame", [c + face * ht * 0.98 + side * hw * 0.8 * math.cos(t) + Z * hh * 0.8 * math.sin(t) for t in np.linspace(0, 2 * math.pi, 13)],
                       [h(0.0022) * s] * 13, 4, mat, ww, cap=False))
    kh = c + face * (ht + h(0.0005))
    obs.append(B_.ellipsoid(name + "Key", kh + Z * h(0.004) * s, (side, Z, face), (h(0.0042) * s, h(0.0042) * s, h(0.0015) * s), 8, 4, "voidB", ww))
    obs.append(box(B_, name + "KeySlot", kh - Z * h(0.003) * s, side, Z, face, h(0.0018) * s, h(0.006) * s, h(0.0012) * s, "voidB", ww, exp=2.0, segs=8))
    return obs


SW = [(-70, 8, ZB1 - h(0.012), h(0.18), 0.045), (5, 95, ZB2 - h(0.012), h(0.14), 0.040), (-120, -45, ZB2 - h(0.015), h(0.09), 0.035)]
lock_tops = []
for q, (a0, a1, z, sag, outk) in enumerate(SW):
    p0 = TS.pt(z, a0, h(0.020)); p1 = TS.pt(z, a1, h(0.020))
    am = (a0 + a1) / 2
    outv = TS.nrm(z, am)
    pts = catenary(p0, p1, sag, 32, out=lambda s: outv, out_amt=h(outk))
    # 沿身體外推（不要穿進大腿／腰擺）
    pts = [p + Vector((p.x, p.y, 0)).normalized() * max(0.0, (h(0.165) if p.z > h(0.40) else h(0.175)) - Vector((p.x, p.y, 0)).length) for p in pts]
    _, cs = chain(f"Swag{q}", pts, "chain", w_low, twist0=q)
    if q == 0:
        lock_tops.append((cs[len(cs) // 2] - Z * h(0.006), outv))
for q, (a, ln) in enumerate(((-14, 0.13), (32, 0.17), (-48, 0.10))):
    top = TS.pt(ZB2 - h(0.012), a, h(0.022))
    nn = TS.nrm(ZB2, a)
    pts = [top + nn * h(0.03) * (k / 6) ** 1.5 - Z * h(ln) * k / 6 for k in range(7)]
    pts = [p + Vector((p.x, p.y, 0)).normalized() * max(0.0, h(0.170) - Vector((p.x, p.y, 0)).length) for p in pts]
    _, cs = chain(f"Drop{q}", pts, "chain", w_low, twist0=q)
    lock_tops.append((cs[-1], nn))
for q, (top, nn) in enumerate(lock_tops):
    padlock(f"Lock{q}", top, nn, s=1.0)

# ================================================================ 前腰擺（粗麻，只在正前方）、側垂皮甲、後擺
AP_TOP = h(0.535); AP_BOT = h(0.17)
af_pts = [V(0, -h(0.135), AP_TOP), V(0, -h(0.145), h(0.42)), V(0, -h(0.15), h(0.30)), V(0, -h(0.155), h(0.17))]
ab_pts = [V(0, h(0.125), h(0.52)), V(0, h(0.135), h(0.44)), V(0, h(0.145), h(0.36))]
af_names = chain_names("ApronF", 3); ab_names = chain_names("ApronB", 2)
ar = random.Random(33)
NU_A, NV_A = 20, 18
# 下緣撕裂：V 形、寬窄高低都不同、撕口歪斜（u 中心, 撕到的高度比例, 底部半寬, 歪斜）
TEARS = [(0.15, 0.30, 0.040, 0.05), (0.33, 0.48, 0.022, -0.04), (0.52, 0.20, 0.050, 0.02), (0.70, 0.40, 0.030, 0.06), (0.86, 0.26, 0.035, -0.03)]
_rag = rag_profile(NU_A, ar, 0.25)
col_len = [1.0 - 0.07 * _rag[i] - 0.05 * _tri(i * 0.23 + 0.1) for i in range(NU_A + 1)]
holes_c = [(0.30, 0.40, 0.040, 1.3), (0.72, 0.60, 0.030, 0.8), (0.47, 0.76, 0.024, 2.1)]


def _tear_hit(u, v):
    for c, top, hw, sk in TEARS:
        t = (v - (1 - top)) / top
        if t > 0 and abs(u - c - sk * t) < hw * t ** 0.8 + 0.006 * math.sin(v * 40 + c * 9):
            return True
    return False


def apron_fn(u, v):
    x = lerp(-h(0.065), h(0.065), u) * (1 + 0.16 * v)
    L = (AP_TOP - AP_BOT) * col_len[int(round(u * NU_A))]
    z = AP_TOP - L * v
    top = TS.pt(AP_TOP, math.degrees(math.asin(max(-1, min(1, x / h(0.14))))), h(0.020))
    y = top.y - h(0.008) * v - h(0.025) * smooth(v * 1.6)
    fold = h(0.008) * math.sin(2 * math.pi * 2.4 * u + 0.6) * smooth(v * 2.5) + h(0.0015) * math.sin(2 * math.pi * 5.1 * u + 1.7) * v
    # 撕開的布條各自往外／往內翻、下緣捲起
    strip = sum(1 for c, top, hw, sk in TEARS if u > c)
    curl = h(0.010) * math.sin(strip * 2.3 + 0.5) * smooth((v - 0.72) / 0.28) + h(0.005) * smooth((v - 0.9) / 0.1) * math.sin(u * 31)
    return V(x, y + fold - curl, z + abs(curl) * 0.3)


def apron_holes(i, jv):
    u = (i + 0.5) / NU_A; v = (jv + 0.5) / NV_A
    if _tear_hit(u, v):
        return True
    for hu, hv, r, ph in holes_c:
        dx = (u - hu) * h(0.13); dz = (v - hv) * (AP_TOP - AP_BOT)
        a = math.atan2(dz, dx)
        rr = r * h(0.13) * (1 + 0.35 * math.sin(3 * a + ph) + 0.2 * math.sin(5 * a + ph * 2))
        if dx * dx + dz * dz < rr * rr:
            return True
    return False


apr = B.grid("ApronF", NU_A, NV_A, apron_fn, "burlapA", w_chain_pts("Hips", af_names, af_pts), [V(0, 0, h(0.35))], holes=apron_holes, sharp=55)
apr["cloth"] = h(0.004)
# 腰擺毛邊（抽紗）：下緣與破洞邊的細線
for i in range(0, NU_A + 1, 2):
    u = i / NU_A
    p = apron_fn(u, 1.0)
    ln = h(0.008 + 0.012 * ar.random())
    BD.tube(f"ApFray{i}", [p, p - Z * ln + V(ar.uniform(-1, 1) * h(0.003), -h(0.002), 0)], [h(0.0012), h(0.0006)], 4, "burlapA", "Hips")
# 側垂皮甲（每側 2 片）＋後擺
for sx in (1, -1):
    for q, (a0, a1, ln) in enumerate(((52, 88, 0.22), (86, 122, 0.20))):
        def tas_t0(u, ln=ln):
            return ZB2 - h(ln) - h(0.012) * math.sin(math.pi * u)

        def tas_off(u, v, a, t, q=q):
            return h(0.016 + 0.005 * q) + h(0.015) * (1 - v) ** 1.2
        ob = B.shell(f"Tasset{q}", TS, tas_t0, ZB2 + h(0.005), a0, a1, 6, 6, "leatherBk", w_low, off=tas_off, rim=h(0.003))
        rv = B.rivets(f"TasRiv{q}", [(TS.pt(ZB2 - h(0.01), a, tas_off(0, 0.97, a, 0) + h(0.003)), TS.nrm(ZB2, a)) for a in (a0 + 6, a1 - 6)], "iron", "Hips", r=h(0.004))
        if sx < 0:
            B.mirror_only([ob, rv])
for q, (a0_, a1_, zb_) in enumerate(((138, 168, 0.35), (165, 195, 0.33), (192, 222, 0.355))):
    B.shell(f"BackFlap{q}", TS, lambda u, zb_=zb_: h(zb_) - h(0.008) * math.sin(math.pi * u), h(0.525), a0_, a1_, 5, 8, "leatherBk",
            w_chain_pts("Hips", ab_names, ab_pts), off=lambda u, v, a, t, q=q: h(0.030 + 0.004 * (q == 1)) + h(0.045) * (1 - v) ** 1.3, rim=h(0.003))

# ================================================================ 腿：皮褲、綁帶、尖刺護膝、脛甲、厚皮靴
TH, SH = body.thigh, body.shin
Lt, Ls = body.th_len, body.sh_len


def w_leg(co):
    side = "L" if co.x >= 0 else "R"
    wk = body.w_knee()(co if side == "L" else Body.mir(co))
    wh = body.w_hipthigh()(co)
    out = {}
    th = wk.get("ThighL", 0)
    for k, v in wh.items():
        out[k] = v * th
    out["Shin" + side] = out.get("Shin" + side, 0) + wk.get("ShinL", 0)
    return out


pl = B.shell("Pants", TH, -h(0.05), Lt + h(0.02), 0, 360, 14, 9, "pants", w_leg, off=lambda u, v, a, t: h(0.003) + h(0.004) * math.exp(-((angn(a) - 180) / 40) ** 2) * math.exp(-((t - Lt) / h(0.03)) ** 2), texel=1.0)
ps_ = B.shell("PantsShin", SH, -h(0.01), Ls * 0.55, 0, 360, 14, 5, "pants", body.w_knee(), off=h(0.003))
B.both([pl, ps_])
# 膝窩皺褶（細節）
for q in range(3):
    BD.both([BD.tube(f"KneeCrease{q}", [TH.pt(Lt * 0.88 + h(0.008) * q, 150 + q * 10, h(0.006)), TH.pt(Lt * 0.92 + h(0.008) * q, 180, h(0.0075)),
                                        TH.pt(Lt * 0.88 + h(0.008) * q, 210 - q * 10, h(0.006))], [h(0.0015), h(0.0025), h(0.0015)], 5, "pants", "ThighL")])
# 大腿綁帶
for q, tf in enumerate((0.38, 0.72)):
    t = Lt * tf
    B.both([B.shell(f"ThighStrap{q}", TH, t - h(0.009), t + h(0.009), 0, 360, 14, 1, "strapDk", "ThighL", off=h(0.005), rim=h(0.002))])
    c = TH.pt(t, 95, h(0.0085))
    B.both(buckle_frame(f"ThStrapBk{q}", c, TH.nrm(t, 95), (TH.a).normalized() * -1, h(0.022), "ThighL"))
# 護膝：圓殼＋3–4 根刺
kc = j["ShinL"] + V(h(0.004), -h(0.040), h(0.006))
kn_ax = (V(0.25, -1, 0.05)).normalized()
ke1 = Z.cross(kn_ax).normalized(); ke2 = kn_ax.cross(ke1)
kn = B.ellipsoid("KneeCop", kc, (ke1, ke2, kn_ax), (h(0.058), h(0.060), h(0.034)), 14, 6, "iron", {"ShinL": 0.55, "ThighL": 0.45}, v0=0.0, v1=0.56, rim=h(0.004))
spk = []
for q, (dx, dz, ln) in enumerate(((0.0, 0.0, 0.034), (0.65, 0.35, 0.026), (-0.5, 0.55, 0.024), (0.55, -0.6, 0.022))):
    dvec = (kn_ax + ke1 * dx * 0.55 + ke2 * dz * 0.55).normalized()
    base = kc + (ke1 * dx * h(0.036) + ke2 * dz * h(0.036)) + kn_ax * h(0.034) * math.sqrt(max(0.05, 1 - 0.36 * (dx * dx + dz * dz) * 1.2))
    spk.append(cone(f"KneeSpike{q}", base, dvec, h(ln), h(0.008), "iron", {"ShinL": 0.55, "ThighL": 0.45}))
kr_ = B.rivets("KneeRiv", [(kc + (ke1 * math.cos(t) + ke2 * math.sin(t)) * h(0.050) + kn_ax * h(0.012), kn_ax) for t in np.linspace(0.3, 6.0, 5)], "iron", {"ShinL": 0.55, "ThighL": 0.45}, r=h(0.0035))
B.both([kn, kr_] + spk)
# 脛甲（前＋兩側）＋2 條皮帶扣
gr_off = lambda u, v, a, t: h(0.0215) + h(0.007) * (t / Ls) + h(0.004) * math.exp(-(angn(a) / 18) ** 2)
grv = B.shell("Greave", SH, Ls * 0.10, Ls * 0.86, -128, 128, 14, 7, "iron", "ShinL", off=gr_off, rim=h(0.004))
gst = [B.shell(f"GreaveStrap{q}", SH, Ls * tf - h(0.008), Ls * tf + h(0.008), 110, 250, 8, 1, "strapB", "ShinL", off=h(0.006), rim=h(0.002)) for q, tf in enumerate((0.3, 0.68))]
gbk = []
for q, tf in enumerate((0.3, 0.68)):
    c = SH.pt(Ls * tf, 125, h(0.016))
    gbk += buckle_frame(f"GrBk{q}", c, SH.nrm(Ls * tf, 125), (j["ShinL"] - j["FootL"]).normalized(), h(0.02), "ShinL")
grr = B.rivets("GreaveRiv", [(SH.pt(Ls * tf, a, gr_off(0, 0, a, Ls * tf) + h(0.002)), SH.nrm(Ls * tf, a)) for tf in (0.16, 0.8) for a in (-110, 110)], "iron", "ShinL", r=h(0.004))
B.both([grv, grr] + gst + gbk)
# 厚皮靴：靴身、厚底、靴筒、翻邊
ank = j["FootL"]


def boot_parts():
    obs = []
    st = [(0.050, 0.028, 0.050), (0.034, 0.036, 0.075), (0.0, 0.0375, 0.085), (-0.036, 0.0375, 0.070), (-0.068, 0.037, 0.055),
          (-0.090, 0.034, 0.045), (-0.101, 0.022, 0.034)]
    pts = [V(ank.x + h(0.003) * (k > 2), ank.y + h(y), h(0.020) + h(hh) * 0.5) for k, (y, wd, hh) in enumerate(st)]
    rad = [(h(wd), h(hh) * 0.5) for y, wd, hh in st]
    obs.append(B.tube("Boot", pts, rad, 16, "boot", "FootL", flat=X, exp=2.3, sharp=45))
    sole = [V(ank.x + h(0.003), ank.y + h(y), h(0.010)) for y in (0.054, 0.035, 0.0, -0.045, -0.08, -0.097, -0.104)]
    sr = [(h(w_) * 1.06, h(0.010)) for w_ in (0.026, 0.036, 0.038, 0.038, 0.035, 0.028, 0.016)]
    obs.append(B.tube("BootSole", sole, sr, 8, "strapDk", "FootL", flat=X, exp=5.0, sharp=50))
    shaft = [V(ank.x, ank.y + h(0.004), z) for z in (h(0.035), h(0.06), h(0.085), h(0.10))]
    obs.append(B.tube("BootShaft", shaft, [h(0.041), h(0.040), h(0.043), h(0.045)], 16, "boot", lambda co: {"FootL": 1 - smooth((co.z - h(0.05)) / h(0.05)), "ShinL": smooth((co.z - h(0.05)) / h(0.05))}, cap=False))
    cuff = [V(ank.x, ank.y + h(0.004), z) for z in (h(0.10), h(0.112), h(0.104), h(0.086))]
    obs.append(B.tube("BootCuff", cuff, [h(0.045), h(0.048), h(0.050), h(0.049)], 16, "boot", "ShinL", cap=False))
    # 腳背綁帶
    for q, y in enumerate((-0.015, -0.045)):
        c = V(ank.x + h(0.003), ank.y + h(y), h(0.020) + h(0.040))
        obs.append(B.tube(f"BootStrap{q}", [c + V(-h(0.040), 0, -h(0.03)), c + V(-h(0.03), 0, h(0.01)), c + V(0, 0, h(0.026)), c + V(h(0.03), 0, h(0.01)), c + V(h(0.040), 0, -h(0.03))],
                          [(h(0.008), h(0.002))] * 5, 4, "strapDk", "FootL", flat=Y, exp=4))
    return obs


B.both(boot_parts())
# 靴子皺褶（細節）
for q in range(4):
    BD.both([BD.tube(f"BootCrease{q}", [V(ank.x - h(0.03), ank.y - h(0.02) - h(0.006) * q, h(0.065) - h(0.004) * q), V(ank.x, ank.y - h(0.025) - h(0.006) * q, h(0.068) - h(0.004) * q),
                                         V(ank.x + h(0.03), ank.y - h(0.02) - h(0.006) * q, h(0.065) - h(0.004) * q)], [h(0.002), h(0.003), h(0.002)], 5, "boot", "FootL")])

# ================================================================ 手臂：裸露肌肉（二頭／三頭／三角／肱橈）、手、護腕
UA, FA = body.uarm, body.farm
La, Lf = body.ua_len, body.fa_len


def g(x, c, w):
    return math.exp(-((x - c) / w) ** 2)


def ua_off(u, v, a, t):
    s = t / La
    aa = angn(a)
    bic = 0.0042 * g(s, 0.55, 0.22) * g(aa, -10, 50)
    tri = 0.0040 * g(s, 0.35, 0.25) * g(abs(aa), 180, 55)
    dl = 0.0028 * g(s, 0.08, 0.15) * g(aa, 60, 70)
    groove = -0.0018 * g(s, 0.55, 0.3) * (g(aa, 100, 14) + g(aa, -100, 14))
    return h(bic + tri + dl + groove)


def fa_off(u, v, a, t):
    s = t / Lf
    aa = angn(a)
    br = 0.0042 * g(s, 0.18, 0.18) * g(aa, 70, 45)
    fl = 0.0030 * g(s, 0.28, 0.2) * g(aa, -40, 50)
    ex = 0.0022 * g(s, 0.3, 0.25) * g(abs(aa), 160, 40)
    return h(br + fl + ex)


uaS = B.shell("UpperArmSkin", UA, -h(0.02), La + h(0.012), 0, 360, 14, 11, "skin", body.w_elbow(), off=ua_off, texel=1.0)
faS = B.shell("ForearmSkin", FA, -h(0.008), Lf + h(0.004), 0, 360, 14, 9, "skin", lambda co: {**{k: v for k, v in body.w_elbow()(co).items()}}, off=fa_off, texel=1.0)
uaR = B.mirror(uaS); faR = B.mirror(faS)
faR["matkey"] = "skinInk"
# 青筋（細節件，烘到法線）
for q, (a0, a1, t0, t1) in enumerate(((-30, -55, 0.15, 0.92), (20, 5, 0.25, 0.85), (-80, -60, 0.4, 0.95))):
    pts = [FA.pt(Lf * lerp(t0, t1, s), lerp(a0, a1, s) + 8 * math.sin(s * 7 + q), fa_off(0, 0, lerp(a0, a1, s), Lf * lerp(t0, t1, s)) + h(0.0012)) for s in np.linspace(0, 1, 9)]
    v_ = BD.tube(f"Vein{q}", pts, [h(0.0018)] * 9, 4, "skin", "ForearmL")
    vr = BD.mirror(v_); vr["matkey"] = "skinInk"
for q, (a0, t0) in enumerate(((-15, 0.3), (-35, 0.55))):
    pts = [UA.pt(La * (t0 + 0.4 * s), a0 + 10 * math.sin(s * 5), ua_off(0, 0, a0, La * (t0 + 0.4 * s)) + h(0.0012)) for s in np.linspace(0, 1, 7)]
    BD.both([BD.tube(f"UVein{q}", pts, [h(0.0016)] * 7, 4, "skin", "UpperArmL")])
# 舊疤（細節：隆起的短線）
for q, (a, t, la) in enumerate(((40, 0.45, 25), (-60, 0.7, -20), (150, 0.5, 30))):
    p0 = UA.pt(La * t, a, ua_off(0, 0, a, La * t) + h(0.0008)); p1 = UA.pt(La * (t + 0.12), a + la, ua_off(0, 0, a + la, La * (t + 0.12)) + h(0.0008))
    BD.both([BD.tube(f"Scar{q}", [p0, p0.lerp(p1, 0.5), p1], [h(0.0012), h(0.0022), h(0.001)], 4, "skin", "UpperArmL")])

# 手（雙手握拳；有指節的四指＋拇指、手背肌腱；右手墨影材質）
body.set_grip(h(0.012))


def fist(mat="skin", details=True):
    Wp = j["HandL"]; a = body.hand_a; v = body.hand_v; u = body.hand_u
    K = body.knuckle
    obs = []
    # 手掌（圓的，不是方塊）：手腕→指根
    pts = [Wp - a * h(0.004), Wp + a * h(0.012) + u * h(0.002), K - a * h(0.012) + u * h(0.003), K - a * h(0.002) + u * h(0.001)]
    obs.append(B.tube("HandBack", pts, [(h(0.019), h(0.012)), (h(0.024), h(0.013)), (h(0.026), h(0.0115)), (h(0.025), h(0.010))], 12, mat, "HandL", flat=v, exp=2.2))
    # 手背肌腱（細節件）
    for q in range(4 if details else 0):
        o_ = (q - 1.5) * h(0.0105)
        BD.tube(f"Tendon{q}", [Wp + a * h(0.012) + v * o_ * 0.6 + u * h(0.0135), K - a * h(0.006) + v * o_ + u * h(0.0115)], [h(0.0016), h(0.0018)], 4, "skin", "HandL")
    rc = body.grip_rc
    er = body.knuckle_dir
    et = (a - er * a.dot(er)).normalized()
    gc0 = K - er * rc
    fr_ = h(0.0060)
    for i, o in enumerate((-0.0165, -0.0055, 0.0055, 0.0165)):
        g_ = gc0 + v * h(o) - a * h(0.002) * abs(i - 1.4)
        ln = (1.0, 1.06, 1.0, 0.86)[i]
        fp = []; rr = []
        for k in range(7):
            th = math.radians(235 * ln * k / 6)
            fp.append(g_ + (er * math.cos(th) + et * math.sin(th)) * rc)
            joint = k in (0, 3, 5)
            rr.append(fr_ * (1.18 if joint else 1.0) * (1 - 0.15 * k / 6) * (0.9 if i == 3 else 1.0))
        obs.append(B.tube(f"Finger{i}", fp, rr, 7, mat, "HandL", texel=1.0))
        if not details:
            continue
        # 指甲（細節件）
        tp, tq = fp[-1], fp[-2]
        nd = (tp - tq).normalized(); nn_ = (tp - gc0).normalized()
        BD.ellipsoid(f"Nail{i}", tq.lerp(tp, 0.6) + nn_ * fr_ * 0.8, (v, nd, nn_), (fr_ * 0.75, fr_ * 0.9, fr_ * 0.25), 6, 4, "thread", "HandL")
    # 拇指：從虎口繞到食指上方
    g_ = gc0 + v * h(0.026)
    tp_ = [Wp + a * h(0.010) + v * h(0.016) - u * h(0.002)]
    for th in (150, 110, 75, 40):
        thr = math.radians(th)
        tp_.append(g_ + (-er * math.cos(thr) + et * math.sin(thr)) * rc * 0.98 - v * h(0.003) * (150 - th) / 110)
    obs.append(B.tube("Thumb", tp_, [h(0.0095), h(0.0080), h(0.0075), h(0.0068), h(0.0055)], 7, mat, "HandL", texel=1.0))
    return obs


hl_ = fist()
hr_ = B.both(hl_)
for o in B.parts[-len(hl_):]:
    o["matkey"] = "skinInk"

# 右前臂（角色右手＝圖左）：黑鐵尖刺護腕（外徑 0.085H、5–7 根錐刺、2 條皮扣帶）
fa_ax = body.fd


def bracer_spiked():
    obs = []
    t0, t1 = Lf * 0.30, Lf * 0.97
    pts = [FA.center(t) for t in (t0, t0 + h(0.006), t1 - h(0.006), t1)]
    obs.append(B.tube("BracerIron", pts, [h(0.0395), h(0.041), h(0.0425), h(0.0412)], 18, "iron", "ForearmL", cap=False, rim=h(0.003)))
    for t in (t0 + h(0.004), t1 - h(0.004)):
        c = FA.center(t)
        e1 = fa_ax.orthogonal().normalized(); e2 = fa_ax.cross(e1)
        ring = [c + (e1 * math.cos(a) + e2 * math.sin(a)) * h(0.0435) for a in np.linspace(0, 2 * math.pi, 15)]
        obs.append(B.tube("BracerRoll", ring, [h(0.0035)] * 15, 5, "iron", "ForearmL", cap=False))
    for q, (tf, a) in enumerate(((0.45, 40), (0.45, 100), (0.45, 160), (0.75, 70), (0.75, 130), (0.75, 10), (0.62, 200))):
        t = Lf * tf
        c = FA.center(t)
        nn = FA.nrm(t, a)
        obs.append(cone(f"BracerSpike{q}", c + nn * h(0.041), nn, h(0.030), h(0.0065), "iron", "ForearmL"))
    for q, tf in enumerate((0.42, 0.85)):
        t = Lf * tf
        obs.append(B.shell(f"BracerStrap{q}", FA, t - h(0.007), t + h(0.007), 150, 320, 10, 1, "strapB", "ForearmL", off=lambda u, v, a, t: h(0.0435) - FA.row(t)[0], rim=h(0.0015)))
    obs.append(B.rivets("BracerRiv", [(FA.center(Lf * tf) + FA.nrm(Lf * tf, a) * h(0.0425), FA.nrm(Lf * tf, a)) for tf in (0.36, 0.92) for a in (0, 70, 140, 210, 280)], "iron", "ForearmL", r=h(0.0035)))
    return obs


B.mirror_only(bracer_spiked())


# 左前臂（角色左手＝圖右）：皮護腕＋綁帶，手腕一圈短刺環
def bracer_leather():
    obs = []
    t0, t1 = Lf * 0.42, Lf * 0.98
    obs.append(B.shell("BracerL", FA, t0, t1, 0, 360, 18, 4, "strapDk", "ForearmL", off=lambda u, v, a, t: h(0.035) - FA.row(t)[0] + h(0.002) * math.sin(math.pi * v), rim=h(0.002)))
    for q, tf in enumerate((0.55, 0.80)):
        t = Lf * tf
        obs.append(B.shell(f"BracerLStrap{q}", FA, t - h(0.006), t + h(0.006), 0, 360, 18, 1, "strap", "ForearmL", off=lambda u, v, a, t: h(0.0375) - FA.row(t)[0], rim=h(0.0015)))
    t = Lf * 1.0
    c = FA.center(t)
    obs.append(B.shell("SpikeRing", FA, Lf * 0.955, Lf * 1.005, 0, 360, 18, 1, "iron", "ForearmL", off=lambda u, v, a, t: h(0.034) - FA.row(min(t, Lf))[0], rim=h(0.002)))
    for q in range(9):
        a = q * 40
        nn = FA.nrm(Lf * 0.98, a)
        obs.append(cone(f"RingSpike{q}", FA.center(Lf * 0.98) + nn * h(0.034), (nn * 1.0 - fa_ax * 0.25), h(0.016), h(0.0045), "iron", "ForearmL", segs=5))
    for z in (0.47, 0.93):
        pts = [FA.pt(Lf * z, a, h(0.035) - FA.row(Lf * z)[0] + h(0.0012)) for a in np.linspace(0, 360, 40)]
        stitches(f"BrLSt{int(z * 100)}", pts, lambda p, z=z: (p - FA.center(Lf * z)).normalized(), w="ForearmL")
    return obs


bracer_leather()

# ================================================================ 肩甲：錘鍛黑鐵圓頂＋2 片疊板，捲邊、鉚釘
PC = V(h(0.140), h(0.002), h(0.772))
PP = (V(0.42, 0, 0.91)).normalized()
PEX = (FWD - PP * FWD.dot(PP)).normalized()
PEY = PP.cross(PEX).normalized()
if PEY.x < 0:
    PEY = -PEY
PR = (h(0.072), h(0.106), h(0.058))       # (前後, 外側, 極軸)


def pd_thmax(u):
    ph = 2 * math.pi * u
    lat = math.cos(ph - math.pi / 2)        # +1 外側、-1 內側（頸側）
    return math.radians(lerp(104, 62, smooth(-lat)))


def pd_fn(u, v):
    ph = 2 * math.pi * u
    th = pd_thmax(u) * v
    dvec = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
    dent = 1.0 + 0.04 * math.sin(th * 3) * (1 - v) - 0.03 * math.exp(-((th - 0.6) / 0.25) ** 2) * math.cos(ph * 2)
    return PC + (PEX * (dvec.x * PR[0]) + PEY * (dvec.y * PR[1]) + PP * (dvec.z * PR[2])) * dent


W_PD = {"ShoulderL": 0.45, "UpperArmL": 0.55}
pd = B.grid("Pauldron", 24, 8, pd_fn, "iron", W_PD, PC, rim=h(0.005), sharp=45)
rim_pts = [pd_fn(q / 28, 1.0) for q in range(29)]
pdr = B.tube("PauldronRoll", [p + (p - PC).normalized() * h(0.001) for p in rim_pts], [h(0.0042)] * 29, 4, "iron", W_PD, cap=False)
pdriv = B.rivets("PauldronRiv", [(pd_fn(u, 0.86), (pd_fn(u, 0.86) - PC).normalized()) for u in (0.08, 0.2, 0.32, 0.68, 0.80, 0.92)], "iron", W_PD, r=h(0.0045))
# 頂部鍛造稜線
pdk = B.tube("PauldronKeel", [pd_fn(0.25, s) + (pd_fn(0.25, s) - PC).normalized() * h(0.002) for s in np.linspace(0.05, 0.9, 8)] if False else
             [pd_fn(0.75, 0.6) + V(0, 0, h(0.001)), pd_fn(0.0, 0.05), pd_fn(0.25, 0.6)], [h(0.003), h(0.004), h(0.003)], 6, "iron", W_PD)
lames = []
for k in range(2):
    ta, tb = h(0.032 + 0.028 * k), h(0.066 + 0.028 * k)

    def lo(u, v, a, t, k=k):
        return h(0.030 - 0.004 * k) + h(0.006) * v + ua_off(0, 0, a, t) * 0.5
    _wl = {"ShoulderL": 0.2, "UpperArmL": 0.8} if k == 0 else "UpperArmL"
    lames.append(B.shell(f"PdLame{k}", UA, ta, tb, 90 - 125, 90 + 125, 14, 2, "iron", _wl, off=lo, rim=h(0.004)))
    lames.append(B.rivets(f"PdLameRiv{k}", [(UA.pt(tb - h(0.012), a, lo(0, 1, a, tb) + h(0.003)), UA.nrm(tb, a)) for a in (-10, 90, 190)], "iron", _wl, r=h(0.004)))
B.both([pd, pdr, pdriv, pdk] + lames)

# ================================================================ 頭罩：顱形（眉骨、鼻樑、下巴）、尖頂往後垂、縱向粗縫線、眼縫
# 截面：(z, 半寬, 半深, y 中心)
HPROF = [(0.792, 0.040, 0.050, 0.004), (0.805, 0.041, 0.054, -0.002), (0.83, 0.0445, 0.057, -0.002), (0.86, 0.0475, 0.058, 0.0),
         (0.885, 0.0465, 0.056, 0.002), (0.905, 0.0430, 0.054, 0.006), (0.922, 0.032, 0.040, 0.009), (0.95, 0.021, 0.026, 0.012),
         (0.975, 0.0115, 0.0135, 0.015), (0.994, 0.003, 0.0035, 0.019), (1.0, 0.0004, 0.0004, 0.020)]
EYE_Z = 0.86


def hprof(zh):
    zs = [p[0] for p in HPROF]
    zh = min(max(zh, zs[0]), zs[-1])
    k = max(0, min(len(HPROF) - 2, int(np.searchsorted(zs, zh) - 1)))
    f = (zh - zs[k]) / (zs[k + 1] - zs[k])
    f = f * f * (3 - 2 * f)
    return [lerp(HPROF[k][i], HPROF[k + 1][i], f) for i in range(1, 4)]


def face_mod(zh, aa):
    """臉部起伏（HT 單位，往外為正）：眉骨、鼻樑、顴骨、下巴、眼縫凹槽、尖頂的布折。"""
    fr = g(aa, 0, 55)
    m = 0.0
    m += 0.0075 * g(zh, 0.874, 0.008) * g(aa, 0, 40)               # 眉骨
    m += 0.0100 * g(zh, 0.842, 0.016) * g(aa, 0, 10)                # 鼻樑
    m -= 0.0030 * g(zh, 0.845, 0.012) * (g(aa, 22, 9) + g(aa, -22, 9))   # 鼻側凹
    m += 0.0040 * g(zh, 0.838, 0.012) * (g(aa, 42, 14) + g(aa, -42, 14))  # 顴骨
    m += 0.0070 * g(zh, 0.806, 0.009) * g(aa, 0, 24)               # 下巴
    m -= 0.0030 * g(zh, 0.818, 0.006) * g(aa, 0, 30)               # 嘴
    m -= 0.0100 * g(zh, EYE_Z, 0.0042) * (1 if abs(aa) < 29 else g(abs(aa), 29, 4))     # 眼縫凹槽（寬 0.045H）
    m += 0.0035 * math.sin(math.radians(aa) * 9 + 0.7) * g(zh, 0.80, 0.012)                 # 頸部收攏的皺褶
    m += 0.0025 * math.sin(math.radians(aa) * 4 + zh * 90) * g(zh, 0.89, 0.02) * (1 - g(aa, 0, 50))   # 頭頂側面的布鬆垂
    m += 0.0025 * g(zh, 0.868, 0.004) * g(aa, 0, 30)               # 眼縫上緣外翻
    m += 0.0030 * g(aa, 0, 3.5) * (1 if zh > 0.88 else g(zh, 0.88, 0.01)) * (1 if zh < 0.99 else 0) + 0.002 * g(aa, 0, 3.5)   # 正中縫線脊
    m += 0.0040 * math.sin(math.radians(aa) * 5 + zh * 60) * smooth((zh - 0.91) / 0.04) * (1 - smooth((zh - 0.985) / 0.015))   # 尖頂的布折
    return m


def hood_pt(u, v):
    """u：繞一圈（0＝正前），v：0 底（頸下）→1 尖。"""
    aa = angn(u * 360)
    zh = lerp(0.792, 1.0, v ** 0.95)
    rx, ry, yc = hprof(zh)
    s, c = math.sin(math.radians(aa)), math.cos(math.radians(aa))
    base = V(s * rx, yc - c * ry, zh)
    nrm = Vector((s / max(rx, 1e-4), -c / max(ry, 1e-4), 0)).normalized()
    p = base + nrm * face_mod(zh, aa)
    # 尖頂往後垂 15°（布的重量）
    if zh > 0.93:
        k = (zh - 0.93) / 0.07
        p = p + V(0, 0.010 * k * k, -0.004 * k * k)
    return p * HT


def w_head(co):
    k = smooth((co.z - h(0.79)) / h(0.02))
    return {"Head": k, "Neck": 1 - k}


_zs = np.linspace(0.792, 1.0, 400)
_dens = 1 + 3.5 * np.exp(-((_zs - EYE_Z) / 0.018) ** 2) + 1.2 * np.exp(-((_zs - 0.83) / 0.03) ** 2) - 0.5 * (_zs > 0.93)
_cum = np.concatenate([[0], np.cumsum((_dens[1:] + _dens[:-1]) * 0.5 * np.diff(_zs))]); _cum /= _cum[-1]


TORN_A, TORN_AH, TORN_Z, TORN_ZH = 19.0, 16.0, 0.870, 0.040     # 二階撕口（角色左臉 +X）：角度中心／半寬、高度中心／半高


def hood_cell(u, v):
    x = 2 * u - 1
    return 180 * (0.42 * x + 0.58 * x ** 3), float(np.interp(v, _cum, _zs))


def in_torn(aa, zh, k=1.0):
    return ((aa - TORN_A) / TORN_AH) ** 2 + ((zh - TORN_Z) / TORN_ZH) ** 2 < k


def hood_grid_fn(u, v):
    x = 2 * u - 1
    ang = 180 * (0.42 * x + 0.58 * x ** 3)
    zh = float(np.interp(v, _cum, _zs))
    vv = max(0.0, (zh - 0.792) / 0.208) ** (1 / 0.95)
    return hood_pt(ang / 360, vv)


_HIN = [V(0, 0, h(z)) for z in (0.80, 0.84, 0.88, 0.92, 0.96)]
hood = B.grid("Hood", 36, 34, hood_grid_fn, "burlap", w_head, _HIN, closed_u=True, sharp=70, texel=1.0,
              holes=lambda i, jv: in_torn(*hood_cell((i + 0.5) / 36, (jv + 0.5) / 34)))
# 一階時蓋住撕口的那塊臉（X2_：二階起隱藏），與頭罩同一組格子、互補
X2 = [B.grid("HoodFacePatch", 36, 34, hood_grid_fn, "burlap", w_head, _HIN, closed_u=True, sharp=70, texel=1.0,
             holes=lambda i, jv: not in_torn(*hood_cell((i + 0.5) / 36, (jv + 0.5) / 34)))]
B.ellipsoid("HeadVoid", V(0, 0, h(0.845)), (X, Y, Z), (h(0.036), h(0.045), h(0.05)), 10, 6, "void", "Head")
EYE_C = hood_pt(0.0, ((EYE_Z - 0.792) / 0.208) ** (1 / 0.95))
_EV = ((EYE_Z - 0.792) / 0.208) ** (1 / 0.95); _EVG = ((EYE_Z + 0.0045 - 0.792) / 0.208) ** (1 / 0.95)
for sx_, arr_ in ((1, (0, 9, 17, 26)), (-1, (0, -9, -17, -26))):      # sx_=-1 是 +X（角色左臉，二階撕開）
    _e = [box(B, f"EyeSlitDark{sx_}", hood_pt(-sx_ * 13.5 / 360, _EV) + Y * h(0.006), X, Z, -Y, h(0.0140), h(0.0034), h(0.004), "void", "Head", exp=3, segs=10),
          B.tube(f"EyeSlitGlow{sx_}", [hood_pt(-a / 360, _EV) + Y * h(0.0075) for a in arr_], [(h(0.0016), h(0.0012))] * 4, 5, "g_eye", "Head", flat=Z),
          B.tube(f"EyeGold{sx_}", [hood_pt(-a / 360, _EVG) + Y * h(0.0045) for a in arr_], [h(0.0011)] * 4, 5, "gold", "Head")]
    if sx_ < 0:
        X2 += _e
# 縱向粗縫線（尖→下巴，針距 0.008H）＋眼縫兩側短縫線
seam = [hood_pt(0.0, s) for s in np.linspace(0.02, 0.97, 40)]
seam = [p for p in seam if abs(p.z / HT - EYE_Z) > 0.008]


def hood_n(p):
    v_ = (p.z / HT - 0.792) / 0.208
    u_ = (math.degrees(math.atan2(p.x, -(p.y - h(0.0)))) / 360) % 1.0
    a = hood_pt(u_, max(0, min(1, v_)) ** (1 / 0.95)); b = hood_pt(u_ + 0.01, max(0, min(1, v_)) ** (1 / 0.95)); c = hood_pt(u_, min(1, max(0, v_) + 0.01) ** (1 / 0.95))
    n = (b - a).cross(c - a)
    if n.dot(Vector((p.x, p.y + h(0.002), 0))) < 0:
        n = -n
    return n.normalized()


# 主縫線用實體（看得到粗線），間距 0.008H
stitch_obs = stitches("HoodSeamSt", seam, hood_n, mat="thread", w="Head", step=h(0.008), ln=h(0.006), r=h(0.0016), B_=B)
for sx in (1, -1):
    for q in range(3):
        a = sx * (31 + q * 4)
        p0 = hood_pt(-a / 360, ((EYE_Z + 0.009 - 0.792) / 0.208) ** (1 / 0.95))
        p1 = hood_pt(-(a + sx * 2) / 360, ((EYE_Z - 0.008 - 0.792) / 0.208) ** (1 / 0.95))
        nn = hood_n(p0)
        _st = B.tube(f"EyeStitch{sx}{q}", [p0 + nn * h(0.0012), p1 + nn * h(0.0012)], [h(0.0014)] * 2, 4, "thread", "Head")
        if sx < 0:
            X2.append(_st)
# 汗漬／污痕由材質 stain 處理；眼縫下方另加一層暗污（細節件顏色）
for q in range(5):
    a = (q - 2) * 9
    p = hood_pt(-a / 360, ((0.845 - 0.792) / 0.208) ** (1 / 0.95))
    BD.ellipsoid(f"SweatStain{q}", p, (X, Z, -Y), (h(0.007), h(0.012), h(0.0008)), 8, 4, "thread", "Head")

# ================================================================ 頭罩披肩：粗麻、3–4 道縱褶、破邊＋抽紗，前到 0.69H、最低 0.66H
mr = random.Random(7)
NUM = 46
mcut = [0.0] * (NUM + 1)
for _q in range(11):                                      # 不規則撕口：位置、寬度、長度都不同
    c_ = mr.uniform(0, NUM); w_ = mr.uniform(0.8, 2.4); L_ = mr.uniform(0.010, 0.040)
    for _k in range(NUM + 1):
        d_ = min(abs(_k - c_), NUM - abs(_k - c_))
        if d_ < w_:
            mcut[_k] = max(mcut[_k], L_ * (1 - d_ / w_) ** 0.8)
_wv = [mr.uniform(-0.004, 0.004) for _ in range(NUM + 1)]


# 披覆高度表：每個方位角、每個高度，身體／胸板／肩甲的最大半徑（布從上往下蓋，只能往外不能往內）
_DR_NA, _DR_Z0, _DR_Z1, _DR_NZ = 90, 0.62, 0.82, 50
_DR = np.zeros((_DR_NA, _DR_NZ))
_drape_src = [o for o in B.parts if o.name.split("_")[0].rstrip("0123456789").startswith(
    ("Tunic", "PecPlate", "PecRoll", "PecRivet", "ChestStrap", "BackPlate", "BackStrap", "BackRiv", "Pauldron", "PdLame"))]
for o in _drape_src:
    for vv in o.data.vertices:
        zz = vv.co.z / HT
        if not (_DR_Z0 <= zz <= _DR_Z1):
            continue
        aa_ = math.degrees(math.atan2(vv.co.x, -vv.co.y))
        r_ = math.hypot(vv.co.x, vv.co.y) / HT
        ia = int(((aa_ + 180) / 360) * _DR_NA) % _DR_NA
        iz = min(_DR_NZ - 1, int((zz - _DR_Z0) / (_DR_Z1 - _DR_Z0) * _DR_NZ))
        _DR[ia, iz] = max(_DR[ia, iz], r_)
for _k in range(2):
    _DR = np.maximum(_DR, np.roll(_DR, 1, 0)); _DR = np.maximum(_DR, np.roll(_DR, -1, 0))       # 角度方向放寬一格（布不會卡進細縫）
_DRC = np.maximum.accumulate(_DR[:, ::-1], axis=1)[:, ::-1]                                  # 由上往下累積最大值＝布的披覆半徑


def drape_r(aa, zh):
    fa = ((aa + 180) / 360) * _DR_NA - 0.5
    i0 = int(math.floor(fa)) % _DR_NA; i1 = (i0 + 1) % _DR_NA; t = fa - math.floor(fa)
    fz = (zh - _DR_Z0) / (_DR_Z1 - _DR_Z0) * _DR_NZ - 0.5
    fz = min(max(fz, 0), _DR_NZ - 1.001); j0 = int(fz); tz = fz - j0
    a0 = lerp(_DRC[i0, j0], _DRC[i0, j0 + 1], tz); a1 = lerp(_DRC[i1, j0], _DRC[i1, j0 + 1], tz)
    return lerp(a0, a1, t)


def drape_free(aa, zh):
    """布離開身體、自由垂下的程度（0＝貼著、1＝懸空）。"""
    fa = int(((aa + 180) / 360) * _DR_NA) % _DR_NA
    fz = min(_DR_NZ - 1, max(0, int((zh - _DR_Z0) / (_DR_Z1 - _DR_Z0) * _DR_NZ)))
    return smooth((_DRC[fa, fz] - _DR[fa, fz]) / 0.02)


def fold_w(aa):
    """縱向垂墜褶：前片 4 道、後片 3 道，形狀不規則（波峰圓、波谷收尖）。"""
    fr = g(aa, 0, 48); bk = g(abs(aa), 180, 48)
    w1 = math.sin(math.radians(aa) * 11 + 0.9 + 0.6 * math.sin(math.radians(aa) * 3))
    w2 = math.sin(math.radians(abs(aa)) * 8 + 2.0)
    return fr * (0.5 + 0.5 * w1) ** 1.6 + bk * (0.5 + 0.5 * w2) ** 1.6


def mantle_bottom(u):
    aa = angn(u * 360)
    fr = g(aa, 0, 42); bk = g(abs(aa), 180, 50); sd = g(abs(aa), 92, 26)
    base = 0.69 * fr + 0.705 * bk + 0.792 * sd + 0.75 * max(0.0, 1 - fr - bk - sd)
    base = min(base, 0.795)
    k = int(round(u * NUM)) % NUM
    return base + mcut[k] + _wv[k] - 0.010 * g(aa, 8, 8) - 0.006 * fold_w(aa)


def mantle_fn(u, v):
    aa = angn(u * 360)
    zb = mantle_bottom(u)
    zh = lerp(zb, 0.815, v ** 0.85)
    s, c = math.sin(math.radians(aa)), math.cos(math.radians(aa))
    fw = fold_w(aa)
    free = drape_free(aa, zh)
    r = drape_r(aa, min(zh, 0.80)) + 0.010 + 0.003 * math.sin(math.radians(aa) * 23 + 1.3) * (1 - v)
    r += (0.009 + 0.008 * free) * fw * (1 - v) ** 0.5          # 褶：懸空的地方起伏 ≥0.008H
    p = V(s * r, -c * r, zh) * HT
    if zh > 0.785:
        rx, ry, yc = hprof(zh)
        top = V(s * (rx + 0.006), yc - c * (ry + 0.006), zh) * HT
        p = p.lerp(top, smooth((zh - 0.785) / 0.028))
    return p


mant = B.grid("HoodMantle", NUM, 10, mantle_fn, "burlapM", lambda co: {"Spine2": 1 - smooth((co.z - h(0.78)) / h(0.03)), "Neck": smooth((co.z - h(0.78)) / h(0.03)) * 0.6, "Head": smooth((co.z - h(0.79)) / h(0.02)) * 0.4},
              [V(0, 0, h(z)) for z in (0.70, 0.74, 0.78, 0.80)], closed_u=True, sharp=60, texel=1.0)
mant["cloth"] = h(0.004)
# 抽紗（披肩下緣垂下的線頭）
for q in range(0, NUM, 2):
    u = (q + 0.5) / NUM
    p = mantle_fn(u, 0.0)
    ln = h(0.006 + 0.022 * mr.random())
    out = (Vector((p.x, p.y, 0))).normalized()
    BD.tube(f"MantleFray{q}", [p, p - Z * ln * 0.5 + out * h(0.002), p - Z * ln + V(mr.uniform(-1, 1) * h(0.004), 0, 0)], [h(0.0013), h(0.001), h(0.0005)], 4, "burlapM", "Spine2")
# 披肩與頭罩的接縫（縫線一圈）
pts = [mantle_fn(u, 0.92) for u in np.linspace(0, 1, 50)]
stitches("MantleSt", pts, lambda p: Vector((p.x, p.y, 0)).normalized(), w="Neck", step=h(0.010))

# ================================================================ 巨斧（全長 0.90H；右手握點在 a=0；金環在柄末、矛尖在頂）
body.set_grip(h(0.012))
gcR = Body.mir(body.grip_c)
AX = Body.mir(body.hand_v).normalized()
EG = Body.mir(body.hand_a); EG = (EG - AX * EG.dot(AX)).normalized()
SD = AX.cross(EG).normalized()


def P_ax(a, e, s=0.0):
    return gcR + AX * h(a) + EG * h(e) + SD * h(s)


WPN = "Weapon"
# 柄（黑木）＋纏皮（下段 0.20、斧頭下 0.06）＋2 道鐵箍＋金套筒＋金封印環
B.tube("Haft", [P_ax(a, 0) for a in (-0.112, -0.05, 0.2, 0.45, 0.63)], [h(0.0105)] * 5, 10, "wood", WPN, flat=EG)
B.tube("WrapLow", [P_ax(a, 0) for a in np.linspace(-0.08, 0.12, 6)], [h(0.0122)] * 6, 10, "wrap", WPN, flat=EG)
B.tube("WrapHigh", [P_ax(a, 0) for a in np.linspace(0.395, 0.455, 3)], [h(0.0122)] * 3, 10, "wrap", WPN, flat=EG)
for a in (-0.08, 0.12, 0.395, 0.455):
    B.tube(f"WrapEnd{a}", [P_ax(a - 0.004, 0), P_ax(a + 0.004, 0)], [h(0.0128)] * 2, 10, "wrap", WPN, flat=EG)
for q in range(2):
    for (a0_, a1_) in ((-0.08, 0.12), (0.395, 0.455)):
        n = int((a1_ - a0_) / 0.004)
        pts = [P_ax(lerp(a0_, a1_, k / n), 0) + (EG * math.cos(k * 1.1 + q * math.pi) + SD * math.sin(k * 1.1 + q * math.pi)) * h(0.0122) for k in range(n + 1)]
        BD.tube(f"WrapHelix{q}{a0_}", pts, [h(0.0018)] * len(pts), 4, "wrap", WPN)
for a in (0.462, 0.478):
    B.tube(f"Collar{a}", [P_ax(a - 0.006, 0), P_ax(a + 0.006, 0)], [h(0.0135)] * 2, 10, "iron", WPN, flat=EG, rim=h(0.001))
B.tube("GoldSleeve", [P_ax(-0.115, 0), P_ax(-0.11, 0), P_ax(-0.09, 0), P_ax(-0.085, 0)], [h(0.0115), h(0.0135), h(0.0135), h(0.0122)], 10, "gold", WPN, flat=EG)
B.ellipsoid("GoldCap", P_ax(-0.117, 0), (EG, SD, AX), (h(0.011), h(0.011), h(0.007)), 10, 5, "gold", WPN)
RC = P_ax(-0.144, 0)
ring = [RC + (AX * math.cos(t) + EG * math.sin(t)) * h(0.024) for t in np.linspace(0, 2 * math.pi, 21)]
B.tube("SealRing", ring, [(h(0.006), h(0.0075))] * 21, 7, "gold", WPN, flat=SD, cap=False)
B.tube("RingLink", [P_ax(-0.118, 0), P_ax(-0.122, 0)], [h(0.006)] * 2, 6, "gold", WPN)
for q in range(16):
    t = q / 16 * 2 * math.pi
    p = RC + (AX * math.cos(t) + EG * math.sin(t)) * h(0.024)
    nn = SD
    for sgn in (1, -1):
        BD.tube(f"RingEngr{q}{sgn}", [p + nn * sgn * h(0.0074) + (AX * -math.sin(t) + EG * math.cos(t)) * h(0.002) * k for k in (-1, 1)], [h(0.0007)] * 2, 4, "voidB", WPN)
# 套筒（直徑 0.035、長 0.10）＋頂端矛尖（長 0.075、四稜）
box(B, "Socket", P_ax(0.585, 0), EG, SD, AX, h(0.0175), h(0.0165), h(0.05), "iron", WPN, exp=3.0, segs=12, rim=h(0.001))
B.tube("Ferrule", [P_ax(0.635, 0), P_ax(0.645, 0), P_ax(0.655, 0)], [h(0.0125), h(0.0135), h(0.010)], 8, "iron", WPN, flat=EG)
B.tube("SpearTip", [P_ax(0.655, 0), P_ax(0.668, 0), P_ax(0.70, 0), P_ax(0.73, 0)], [h(0.008), h(0.010), h(0.0055), h(0.0004)], 4, "blade", WPN, flat=(EG + SD).normalized(), sharp=25)
for q in range(4):
    BD.tube(f"SpearRidge{q}", [P_ax(0.668, 0) + (EG * math.cos(q * math.pi / 2 + math.pi / 4) + SD * math.sin(q * math.pi / 2 + math.pi / 4)) * h(0.0098),
                                P_ax(0.728, 0)], [h(0.0009), h(0.0003)], 4, "bladeEdge", WPN)

# 斧刃：上角 (0.655, 0.185)、下鬍尖 (0.385, 0.155)，刃口外凸弧高 0.03；刃身厚 0.012、刃口斜面 0.02（刃緣 0.002）；6–10 個缺口
UC = (0.655, 0.185); BT = (0.376, 0.150)
NOTCH = [(0.07, 0.008, 0.018), (0.19, 0.005, 0.012), (0.33, 0.012, 0.02), (0.47, 0.006, 0.012), (0.58, 0.015, 0.022),
         (0.70, 0.007, 0.014), (0.82, 0.010, 0.016), (0.93, 0.005, 0.012)]


def edge_pt(q):
    a = lerp(UC[0], BT[0], q); e = lerp(UC[1], BT[1], q)
    da, de = BT[0] - UC[0], BT[1] - UC[1]
    ln = math.hypot(da, de)
    na, ne = de / ln, -da / ln
    if ne < 0:
        na, ne = -na, -ne
    bul = 0.030 * 4 * q * (1 - q) * (1 + 0.15 * (q - 0.5))
    cut = sum(dep * math.exp(-((q - c) / (wd * 0.5)) ** 2) for c, dep, wd in NOTCH)
    return a + na * (bul - cut), e + ne * (bul - cut)


def root_pt(q):
    return lerp(0.625, 0.535, q), 0.016


def blade_ae(q, v):
    """v：0 刃根 → 1 刃口。上緣（q=0）微凹、鬍子內側（q=1）大幅內凹成月牙。"""
    ra, re = root_pt(q); ea, ee = edge_pt(q)
    a = lerp(ra, ea, v); e = lerp(re, ee, v)
    if q > 0.62:
        k = ((q - 0.62) / 0.38) ** 1.5
        a += 0.085 * k * math.sin(math.pi * v ** 0.8) * (1 - v * 0.25)
        e -= 0.010 * k * math.sin(math.pi * v)
    if q < 0.16:
        k = 1 - q / 0.16
        a -= 0.024 * k * math.sin(math.pi * min(1.0, v * 1.15))
    return a, e


VB = 0.89            # 斜面起點（v）


def blade_half(v):
    if v <= VB:
        return lerp(0.0075, 0.006, v / VB)
    s = (v - VB) / (1 - VB)
    return lerp(0.006, 0.001, s)


def qmap(x):
    return 0.5 - 0.5 * math.cos(math.pi * x)


def blade_grid(sign, v0, v1, mat, name, B_=None, scale=1.0, frame=None):
    B_ = B_ or B
    NQ = 24
    PF = frame or P_ax

    def fn(u, vv):
        v = lerp(v0, v1, vv)
        if u <= 0.5:
            q, sd = qmap(u * 2), 1.0
        else:
            q, sd = qmap(2 - 2 * u), -1.0
        a, e = blade_ae(q, v)
        a = 0.58 + (a - 0.58) * scale; e = e * scale
        th = blade_half(v) * scale
        if q < 0.02 or q > 0.98:
            th *= 0.85
        return PF(a, e * sign, sd * th)
    nv = 7 if v1 - v0 > 0.5 else 2
    return B_.grid(name, NQ * 2, nv, fn, mat, WPN, [PF(0.55, 0.05 * sign * scale), PF(0.6, 0.1 * sign * scale)], closed_u=True,
                   cap0=(v0 == 0), cap1=False, sharp=40, texel=1.0)


blade_grid(1, 0.0, VB, "blade", "AxeBlade")
blade_grid(1, VB, 1.0, "bladeEdge", "AxeEdge")
# 刃口封邊（刃緣 0.002 的窄面）
B.tube("AxeEdgeLip", [P_ax(*blade_ae(q, 1.0)) for q in np.linspace(0, 1, 30)], [(h(0.0012), h(0.0012))] * 30, 4, "bladeEdge", WPN, flat=SD, cap=True)
# 上緣兩個不規則尖角（高 0.04–0.05）
for q, (e0, e1, ht, lean) in enumerate(((0.050, 0.095, 0.045, 0.012), (0.115, 0.160, 0.040, -0.006))):
    em = (e0 + e1) / 2

    def horn_fn(u, v, e0=e0, e1=e1, ht=ht, lean=lean, em=em):
        if u <= 0.5:
            x, sd = u * 2, 1
        else:
            x, sd = 2 - 2 * u, -1
        e = lerp(e0, e1, x)
        a0_, _ = blade_ae(0.0, (e - 0.016) / 0.17)
        tip = ht * (1 - abs(2 * x - 1) ** 1.5) * (0.7 + 0.3 * math.sin(x * 9 + q))
        a = a0_ - 0.004 + (tip + 0.004) * v
        return P_ax(a, e + lean * v * v + (em - e) * v * 0.55, sd * 0.0055 * (1 - 0.7 * v))
    B.grid(f"AxeHorn{q}", 12, 3, horn_fn, "blade", WPN, P_ax(0.62, em), closed_u=True, cap0=False, sharp=40)
# 背側鋸齒小齒（矛尖下方的刃背）
# 符紋：上排 3、下排 4，抽象筆畫（短斜線、鉤、點）；凹刻（暗槽）＋紫光
# 只用短斜線、彎鉤、點；避免直立的筆畫（不像任何字母）
GL = [[((0.1, 0.2), (0.6, 0.75)), ((0.8, 0.3), (0.86, 0.36))],
      [((0.1, 0.7), (0.45, 0.4)), ((0.45, 0.4), (0.75, 0.62)), ((0.35, 0.9), (0.41, 0.96))],
      [((0.25, 0.8), (0.55, 0.3)), ((0.62, 0.68), (0.9, 0.48))],
      [((0.15, 0.3), (0.45, 0.72)), ((0.45, 0.72), (0.85, 0.62)), ((0.52, 0.15), (0.58, 0.21))],
      [((0.1, 0.62), (0.42, 0.2)), ((0.55, 0.85), (0.82, 0.58)), ((0.82, 0.58), (0.72, 0.32))],
      [((0.2, 0.48), (0.26, 0.54)), ((0.4, 0.82), (0.85, 0.38))],
      [((0.1, 0.25), (0.4, 0.58)), ((0.4, 0.58), (0.28, 0.88)), ((0.6, 0.3), (0.88, 0.75))]]


def rune_set(prefix, sign, mat_glow, mark=None, B_=None, frame=None, glow_only=False):
    B_ = B_ or B
    PF = frame or P_ax
    obs = []
    rows = [(0.26, 0.36, 3), (0.48, 0.56, 4)]           # (q 起點, v 中心, 數量)
    gi = 0
    for (q0, vc, n) in rows:
        for k in range(n):
            gl_ = GL[gi % len(GL)]; gi += 1
            for sd in (1, -1):
                for si, (p0, p1) in enumerate(gl_):
                    qa, va = q0 + 0.085 * k + 0.055 * p0[0], vc + 0.16 * (p0[1] - 0.5)
                    qb, vb = q0 + 0.085 * k + 0.055 * p1[0], vc + 0.16 * (p1[1] - 0.5)
                    aa, ea = blade_ae(qa, va); ab, eb = blade_ae(qb, vb)
                    ta, tb = blade_half(va), blade_half(vb)
                    pa = PF(aa, ea * sign, sd * (ta + 0.0006)); pb = PF(ab, eb * sign, sd * (tb + 0.0006))
                    if (pb - pa).length < h(0.004):
                        pb = pa + (pb - pa).normalized() * h(0.004) if (pb - pa).length > 1e-6 else pa + AX * h(0.004)
                    if not glow_only:
                        obs.append(B_.tube(f"{prefix}G{gi}{si}{sd}", [pa, pb], [(h(0.0005), h(0.0036))] * 2, 4, "voidB", WPN, flat=SD))
                    obs.append(B_.tube(f"{prefix}{gi}{si}{sd}", [pa + SD * sd * h(0.0007), pb + SD * sd * h(0.0007)], [(h(0.0004), h(0.0018))] * 2, 4, mat_glow, WPN, flat=SD))
    if mark:
        VH.mark(obs, mark)
    return obs


rune_set("AxeRune", 1, "g_weapon")
# 刃身磨痕、刃口細磨痕（細節件）
for q in range(14):
    qq = 0.05 + 0.9 * q / 13
    pa = P_ax(*blade_ae(qq, VB + 0.01), 0.0); pb = P_ax(*blade_ae(qq + 0.01, 0.985), 0.0)
    for sd in (1, -1):
        BD.tube(f"Hone{q}{sd}", [pa + SD * sd * h(0.0055), pb + SD * sd * h(0.0016)], [(h(0.0006), h(0.0003))] * 2, 4, "bladeEdge", WPN, flat=SD)
for q in range(10):
    qq = rnd.uniform(0.1, 0.9); vv = rnd.uniform(0.2, 0.8)
    pa = P_ax(*blade_ae(qq, vv), 0.0); pb = P_ax(*blade_ae(qq + rnd.uniform(-0.12, 0.12), vv + rnd.uniform(-0.15, 0.15)), 0.0)
    for sd in (1, -1):
        BD.tube(f"BScr{q}{sd}", [pa + SD * sd * h(0.0076), pb + SD * sd * h(0.0076)], [(h(0.0008), h(0.0004))] * 2, 4, "blade", WPN, flat=SD)

# ================================================================ 墨影（黑色煙墨；紫只在邊緣殼 Glow_Rune）
# 右前臂（圖左）：手肘下方開始，往手掌越來越濃，指尖散成 3–5 條往上飄的墨絲
inkR = []
hand_c = j["HandL"] + body.hand_a * h(0.035)
for q in range(5):
    p = body.knuckle + body.hand_v * ((q - 2) * h(0.011)) + body.hand_u * h(0.006)
    d = (body.hand_u * 0.6 + Z * 0.9 - body.hand_a * 0.2).normalized()
    inkR += wisp(f"InkFinger{q}", p, d, h(0.05 + 0.017 * q), body.hand_v, "ink", "HandL", width=0.004, thick=0.0015, curl=0.35, seed=q + 1, up=0.5, rim="g_rune" if q in (1, 3) else None)
for q in range(6):
    a = 30 + q * 55
    t = Lf * (0.55 + 0.07 * (q % 3))
    p = FA.pt(t, a, h(0.004))
    nn = FA.nrm(t, a)
    d = (nn * 0.7 - fa_ax * 0.35 + Z * 0.55).normalized()
    if q % 2 == 0:
        inkR += wisp(f"InkArm{q}", p, d, h(0.06 + 0.02 * (q % 3)), fa_ax, "ink2", "ForearmL", width=0.005, thick=0.0015, curl=0.45, seed=q + 9, up=0.5)
inkR = B.mirror_only(inkR)
# 左前臂：少量墨煙（手肘後方）
for q in range(3):
    a = 150 + q * 40
    p = UA.pt(La * 0.95, a, h(0.004))
    d = (UA.nrm(La * 0.95, a) + Z * 0.8).normalized()
    wisp(f"InkElbowL{q}", p, d, h(0.05 + 0.015 * q), body.ud, "ink2", "ForearmL", width=0.007, curl=0.45, seed=30 + q, up=0.6)
# 腳踝：從靴口往下暈開＋地面墨池（半徑 0.08H，墨絲往外延伸 0.1H）
ir = random.Random(5)
NI = 24
icut = [ir.uniform(0, 1) for _ in range(NI + 1)]


def veil_fn(u, v):
    a = u * 2 * math.pi
    k = int(round(u * NI)) % NI
    z = lerp(h(0.115), h(0.004), v)
    r = lerp(h(0.050), h(0.062 + 0.02 * icut[k]), v ** 1.5) + h(0.004) * math.sin(a * 6 + v * 5)
    c = V(ank.x, ank.y + h(0.004), 0)
    return c + V(math.cos(a) * r, math.sin(a) * r * 1.15 - h(0.01) * v, z)


veil = B.grid("InkVeil", NI, 5, veil_fn, "ink2", "FootL", V(ank.x, ank.y, h(0.06)), closed_u=True,
              holes=lambda i, jv: jv >= 3 and icut[i] > 0.62)
NP = 28
pr_ = [ir.uniform(0, 1) for _ in range(NP + 1)]


def pool_fn(u, v):
    a = u * 2 * math.pi
    k = int(round(u * NP)) % NP
    tend = (pr_[k] ** 3) * h(0.10)
    r = v * (h(0.08) + tend) * (1 + 0.1 * math.sin(a * 7))
    c = V(ank.x, ank.y - h(0.01), h(0.0025 + 0.0012 * (1 - v)))
    return c + V(math.cos(a) * r, math.sin(a) * r * 1.2, 0)


pool = B.grid("InkPool", NP, 2, pool_fn, "ink", "FootL", V(ank.x, ank.y, h(-0.1)), closed_u=True)
ank_w = []
for q in range(3):
    a = q * 120 + 20
    p = V(ank.x, ank.y, h(0.02)) + V(math.cos(math.radians(a)), math.sin(math.radians(a)), 0) * h(0.07)
    d = V(math.cos(math.radians(a)), math.sin(math.radians(a)), 0.05)
    pass
for q in range(3):
    a = q * 120 + 80
    p = V(ank.x, ank.y, h(0.10)) + V(math.cos(math.radians(a)), math.sin(math.radians(a)), 0) * h(0.05)
    ank_w += wisp(f"AnkleRise{q}", p, (V(math.cos(math.radians(a)) * 0.3, math.sin(math.radians(a)) * 0.3, 1)), h(0.05 + 0.02 * q), X, "ink2", "ShinL", width=0.008, curl=0.5, seed=50 + q, up=0.3)
B.both([veil, pool] + ank_w)

# ================================================================ 二階部件
P2 = {}
# ---- P2_AxeBlade2：反側第二片斧刃＋兩邊刃口斷續紫光（3–5 段，寬 0.006H）
ob2 = [blade_grid(-1, 0.0, VB, "blade", "AxeBlade2"), blade_grid(-1, VB, 1.0, "bladeEdge", "AxeEdge2")]
ob2.append(B.tube("AxeEdgeLip2", [P_ax(blade_ae(q, 1.0)[0], -blade_ae(q, 1.0)[1]) for q in np.linspace(0, 1, 30)], [(h(0.0012), h(0.0012))] * 30, 4, "bladeEdge", WPN, flat=SD))
ob2 += rune_set("AxeRune2", -1, "g_weapon")
for sgn, nm in ((1, "A"), (-1, "B")):
    for s_, (q0, q1) in enumerate(((0.03, 0.2), (0.27, 0.45), (0.52, 0.66), (0.74, 0.95))):
        pts = []
        for q in np.linspace(q0, q1, 8):
            a, e = blade_ae(q, 1.0)
            pts.append(P_ax(a, (e + 0.002) * sgn))
        ob2.append(B.tube(f"EdgeGlow{nm}{s_}", pts, [(h(0.0014), h(0.003))] * 8, 4, "p2_edge", WPN, flat=SD))
P2["P2_AxeBlade2"] = ob2
VH.mark(ob2, "P2_AxeBlade2")

# ---- P2_HoodTorn：頭罩臉部（角色左臉，+X 側）撕開 0.07×0.09，內部紫色漩渦（貼著頭罩、畫成凹洞），翻開的布片 0.06×0.05
TU0, TU1 = (TORN_A - TORN_AH) / 360, (TORN_A + TORN_AH) / 360     # +X（角色左臉）；hood_pt 的 u＝角度/360、正值在 +X
TV0, TV1 = ((TORN_Z - TORN_ZH - 0.792) / 0.208) ** (1 / 0.95), ((TORN_Z + TORN_ZH - 0.792) / 0.208) ** (1 / 0.95)
tr_ = random.Random(12)
NT = 28
tcut = [tr_.uniform(-1, 1) for _ in range(NT + 1)]


def torn_center():
    return hood_pt((TU0 + TU1) / 2, (TV0 + TV1) / 2)


def torn_rim(q):
    t = q / NT * 2 * math.pi
    k = q % NT
    uu = (TU0 + TU1) / 2 + math.cos(t) * (TU1 - TU0) / 2 * (1 + 0.12 * tcut[k])
    vv = (TV0 + TV1) / 2 + math.sin(t) * (TV1 - TV0) / 2 * (1 + 0.10 * tcut[(k + 7) % NT])
    return uu, vv


def void_fn(u, v):
    t = u * 2 * math.pi
    uu0, vv0 = torn_rim(int(round(u * NT)) % NT)
    uu = lerp((TU0 + TU1) / 2, uu0, v); vv = lerp((TV0 + TV1) / 2, vv0, v)
    p = hood_pt(uu % 1.0, vv)
    return p - hood_n(p) * h(0.014) * (1 - v * v)        # 凹進頭罩：中心深 0.014H、邊緣貼齊撕口


vo = B.grid("VoidDisc", NT, 6, void_fn, "p2_void", "Head", V(0, 0, h(0.85)), closed_u=True)
uvl = vo.data.uv_layers.active
TC = torn_center()
tn = hood_n(TC)
te1 = Z.cross(tn).normalized(); te2 = tn.cross(te1)
for poly in vo.data.polygons:
    for li in poly.loop_indices:
        co = vo.data.vertices[vo.data.loops[li].vertex_index].co
        d_ = co - TC
        uvl.data[li].uv = (0.5 + d_.dot(te1) / h(0.075), 0.5 + d_.dot(te2) / h(0.095))
torn = [vo]
rim = []
for q in range(NT + 1):
    uu, vv = torn_rim(q % NT)
    p = hood_pt(uu % 1.0, vv)
    rim.append(p + hood_n(p) * h(0.0025))
torn.append(B.tube("TornRim", rim, [(h(0.0035), h(0.0022))] * (NT + 1), 5, "burlap", "Head", cap=False))
for q in range(0, NT, 2):
    p = rim[q]
    d_ = (p - TC).normalized()
    torn.append(B.tube(f"TornFray{q}", [p, p + d_ * h(0.004 + 0.004 * abs(tcut[q])) + hood_n(p) * h(0.002)], [h(0.0012), h(0.0004)], 3, "burlap", "Head", cap=False))


def flap_fn(u, v):
    # 從撕口外側（+X）往外下翻開
    uu, vv = torn_rim(int(round(lerp(NT * 0.80, NT * 1.20, u))) % NT)
    base = hood_pt(uu % 1.0, vv)
    n = hood_n(base)
    out = (n * 0.30 + X * 0.15 - Z * 0.95).normalized()
    cut = 0.75 + 0.25 * math.sin(u * 13.0)
    return base + out * h(0.045) * v * cut + n * h(0.004) * math.sin(math.pi * v) + n * h(0.002)


fl = B.grid("TornFlap", 10, 4, flap_fn, "burlap", "Head", TC - tn * h(0.05))
fl["cloth"] = h(0.004)
torn.append(fl)
P2["P2_HoodTorn"] = torn
VH.mark(torn, "P2_HoodTorn")
VH.mark(X2, "X2_HoodFace")

# ---- P2_ChainHalo：腰高 0.52H 繞一圈、半徑 0.25H、波浪 ±0.03H、3 個掛鎖、2 段垂下的鬆鍊（0.15H）
CH_Z = h(0.52); CH_R = h(0.25)
halo = []
hp = []
for q in range(81):
    a = 2 * math.pi * q / 80
    hp.append(V(math.sin(a) * CH_R, -math.cos(a) * CH_R * 0.95, CH_Z + h(0.03) * math.sin(3 * a + 0.4)))
obs, hcs = chain("HaloLink", hp, "chain", "ChainHalo", link=h(0.062), wire=h(0.009), nu=6, nv=3)
halo += obs
for q, a in enumerate((0.7, 2.6, 4.5)):
    top = V(math.sin(a) * CH_R, -math.cos(a) * CH_R * 0.95, CH_Z + h(0.03) * math.sin(3 * a + 0.4))
    hp2 = [top - Z * h(0.012) * k for k in range(4)]
    o_, cs = chain(f"HaloHang{q}", hp2, "chain", "ChainHalo", link=h(0.025), wire=h(0.005))
    halo += o_
    n0 = len(B.parts)
    padlock(f"HaloLock{q}", cs[-1], V(math.sin(a), -math.cos(a), 0), s=1.25, w="ChainHalo")
    halo += B.parts[n0:]
for q, a in enumerate((1.6, 5.3)):
    top = V(math.sin(a) * CH_R, -math.cos(a) * CH_R * 0.95, CH_Z + h(0.03) * math.sin(3 * a + 0.4))
    hp2 = [top + V(math.sin(a), -math.cos(a), 0) * h(0.02) * s - Z * h(0.15) * s for s in np.linspace(0, 1, 6)]
    o_, _ = chain(f"HaloSlack{q}", hp2, "chain", "ChainHalo", link=h(0.035), wire=h(0.006))
    halo += o_
P2["P2_ChainHalo"] = halo
VH.mark(halo, "P2_ChainHalo")


# ---- P2_ShadowArmL/R：肩胛後方長出的墨影手臂（有肌肉起伏，0.45H），左影手握影斧
def ink_limb(name, pts, radii, mat, w, rim_mat, B_=None, segs=8):
    B_ = B_ or B
    o = [B_.tube(name, pts, radii, segs, mat, w)]
    if rim_mat:
        o.append(B_.tube(name + "Rim", pts, [r * 1.12 + h(0.0015) for r in radii], segs, rim_mat, w))
    return o


SA = {}
for sx in (1, -1):
    S0 = TS.pt(h(0.73), 150 * sx, h(0.02))
    El = S0 + V(h(0.17) * sx, h(0.08), h(0.10))
    Hd = El + V(h(0.05) * sx, -h(0.06), h(0.15))
    SA[sx] = (S0, El, Hd)
    nm = "P2_ShadowArmL" if sx > 0 else "P2_ShadowArmR"
    obs = []
    # 上臂（三角肌→二頭肌→手肘）、前臂（肱橈肌→手腕），直徑 0.07→0.04
    bend = (El - S0).cross(Hd - El).normalized()
    up_ = [S0 - (El - S0) * 0.15] + [S0.lerp(El, t) + bend * h(0.006) * math.sin(math.pi * t) for t in (0.15, 0.35, 0.55, 0.75, 0.92)] + [El]
    obs.append(B.tube("ShUpper", up_, [h(0.033), h(0.036), h(0.034), h(0.036), h(0.032), h(0.027), h(0.025)], 12, "p2_ink", "Spine2"))
    fo_ = [El] + [El.lerp(Hd, t) for t in (0.15, 0.32, 0.55, 0.8)] + [Hd]
    obs.append(B.tube("ShFore", fo_, [h(0.025), h(0.029), h(0.030), h(0.026), h(0.022), h(0.020)], 12, "p2_ink", "Spine2"))
    dH = (Hd - El).normalized()
    sp = (X * sx).cross(dH).normalized()
    pc = Hd + dH * h(0.032)
    nrm_ = dH.cross(sp)
    obs.append(B.ellipsoid("ShPalm", pc, (sp, nrm_, dH), (h(0.030), h(0.018), h(0.036)), 10, 6, "p2_ink", "Spine2"))
    for f in range(4):
        base = pc + dH * h(0.030) + sp * (f - 1.5) * h(0.015)
        pts_ = [base]
        for k in range(1, 4):
            ang = math.radians((70 if sx > 0 else 22) * k)          # 左手握拳、右手半張的爪
            pts_.append(pts_[-1] + (dH * math.cos(ang) - nrm_ * math.sin(ang)) * h(0.022 - 0.003 * k) + sp * (f - 1.5) * h(0.002) * (0 if sx > 0 else 1))
        obs.append(B.tube(f"ShFinger{f}", pts_, [h(0.0085), h(0.0078), h(0.0068), h(0.004)], 7, "p2_ink", "Spine2"))
    obs.append(B.tube("ShThumb", [pc - dH * h(0.01) + sp * h(0.026), pc + dH * h(0.012) + sp * h(0.034) - nrm_ * h(0.01), pc + dH * h(0.03) + sp * h(0.026) - nrm_ * h(0.022)],
                      [h(0.009), h(0.008), h(0.005)], 7, "p2_ink", "Spine2"))
    for k in range(3):
        off = (sp * math.cos(k * 0.8 - 0.8) + nrm_ * math.sin(k * 0.8 - 0.8))
        obs.append(B.tube(f"ShVein{k}", [El.lerp(Hd, 0.55) + off * h(0.0275), El.lerp(Hd, 0.8) + off * h(0.0235), Hd + off * h(0.0205)], [h(0.0016)] * 3, 4, "p2_vein", "Spine2"))
    # 手臂散成墨絲（肩胛根部、手肘）
    for k in range(4):
        p = (S0, S0.lerp(El, 0.5), El, El.lerp(Hd, 0.5))[k]
        obs += wisp(f"ShWisp{k}", p, V(0.25 * sx, 0.9, -0.2 + 0.25 * k), h(0.07 + 0.02 * (k % 2)), Z, "p2_ink", "Spine2", width=0.010, thick=0.004, curl=0.4, seed=40 + k + (0 if sx > 0 else 10), up=0.3)
    if sx > 0:
        ax = V(0.15 * sx, -0.35, 0.92).normalized()
        gc = pc + dH * h(0.03)
        eg = (X * sx - ax * (X * sx).dot(ax)).normalized()
        sd_ = ax.cross(eg).normalized()

        def FR(a, e, s=0.0, gc=gc, ax=ax, eg=eg, sd_=sd_):
            return gc + ax * h(a - 0.42) + eg * h(e) + sd_ * h(s)
        obs.append(B.tube("ShHaft", [FR(0.0, 0), FR(0.5, 0)], [h(0.011), h(0.010)], 8, "p2_ink", "Spine2"))
        obs.append(blade_grid(1, 0.0, 1.0, "p2_ink", "ShBlade", frame=lambda a, e, s=0.0: FR(a - 0.07, e, s)))
        ep = [FR(blade_ae(q, 1.0)[0] - 0.07, blade_ae(q, 1.0)[1] + 0.003) for q in np.linspace(0.02, 0.98, 14)]
        obs.append(B.tube("ShEdge", ep, [(h(0.0014), h(0.003))] * len(ep), 4, "p2_edge", "Spine2", flat=sd_))
    bn = "ShadowArmL" if sx > 0 else "ShadowArmR"
    for o in obs:
        for gg in list(o.vertex_groups):
            o.vertex_groups.remove(gg)
        gg = o.vertex_groups.new(name=bn)
        gg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    VH.mark(obs, nm)

# ---- P2_InkArmL/R、P2_InkLegL/R：手肘／膝蓋以下全被墨影覆蓋；角色右前臂（圖左）是整隻黑墨拳頭（直徑 0.10H）
for sx, sfx in ((1, "L"), (-1, "R")):
    obs = []
    big = (sx < 0)

    def sleeve(u, v, big=big):
        a = u * 360
        t = Lf * lerp(-0.02, 1.0, v)
        rr = (h(0.046) if big else h(0.040)) + h(0.004) * math.sin(math.radians(a) * 4 + v * 7)
        return FA.center(t) + FA.nrm(t, a) * rr
    obs.append(B.grid("InkSleeve", 12, 5, sleeve, "p2_ink", "ForearmL", [FA.center(Lf * 0.5)], closed_u=True))
    if big:
        fobs = fist("p2_ink", details=False)
        Wc = j["HandL"] + body.hand_a * h(0.03)
        for o in fobs:                       # 放大成直徑約 0.10H 的墨拳（以手掌中心縮放）
            for vv in o.data.vertices:
                vv.co = Wc + (vv.co - Wc) * 1.65
            o.name = "InkFist" + o.name
        obs += fobs
    for q in range(5):
        a = q * 72 + 10
        t = Lf * (0.25 + 0.09 * (q % 5))
        p = FA.center(t) + FA.nrm(t, a) * h(0.04)
        d = (FA.nrm(t, a) * 0.6 - fa_ax * 0.4 + Z * 0.5).normalized()
        obs += wisp(f"InkArmX{q}", p, d, h(0.07 + 0.025 * (q % 3)), fa_ax, "p2_ink", "ForearmL", width=0.008, thick=0.003, curl=0.4, seed=60 + q, up=0.5)
    for q in range(3):
        a = q * 120 + 30
        obs.append(B.tube(f"InkArmVein{q}", [FA.center(Lf * 0.5) + FA.nrm(Lf * 0.5, a) * h(0.041), FA.center(Lf * 0.95) + FA.nrm(Lf * 0.95, a + 20) * h(0.041)],
                          [(h(0.0022), h(0.0016))] * 2, 4, "p2_vein", "ForearmL"))
    if sx < 0:
        obs = B.mirror_only(obs)
    VH.mark(obs, "P2_InkArm" + sfx)
    obs = []

    def lsleeve(u, v):
        a = u * 360
        t = Ls * lerp(0.0, 0.80, v)
        rr = h(0.050) + h(0.004) * math.sin(math.radians(a) * 5 + v * 6)
        return SH.center(t) + SH.nrm(t, a) * rr
    obs.append(B.grid("InkLegSleeve", 12, 5, lsleeve, "p2_ink", "ShinL", [SH.center(Ls * 0.5)], closed_u=True))
    for q in range(4):
        a = q * 90 + 20
        t = Ls * (0.4 + 0.08 * (q % 4))
        p = SH.center(t) + SH.nrm(t, a) * h(0.05)
        d = (SH.nrm(t, a) * 0.6 + Z * 0.7 + V(0, 0.3, 0)).normalized()
        obs += wisp(f"InkLegX{q}", p, d, h(0.07 + 0.02 * (q % 3)), Z, "p2_ink", "ShinL", width=0.009, thick=0.003, curl=0.35, seed=80 + q, up=0.3)
    if sx < 0:
        obs = B.mirror_only(obs)
    VH.mark(obs, "P2_InkLeg" + sfx)

# ================================================================ 骨架、Tip_Weapon、烘焙
SL, EL_, _ = SA[1]; SR, ER, _ = SA[-1]
arm = build_armature("BossExecutioner", body, weapon=(gcR, gcR + AX * 0.30 * U),
                     chains=[("ApronF", "Hips", af_pts), ("ApronB", "Hips", ab_pts)],
                     extra=[("ShadowArmL", "Spine2", SL, SL + (EL_ - SL).normalized() * 0.3), ("ShadowArmR", "Spine2", SR, SR + (ER - SR).normalized() * 0.3),
                            ("ChainHalo", "Hips", V(0, 0, CH_Z), V(0, 0, CH_Z + 0.3))])
import v3_executioner_measure as XM
_MR = XM.measure(B, body, HT, os.path.join(TMP, "measure.json"))
_wp = [o for o in B.parts if not o.get("pmark") and (o.name.startswith(("Haft", "Wrap", "Collar", "Gold", "Seal", "Ring", "Socket", "Ferrule", "Spear", "Axe")))]
_av = [v.co for o in _wp for v in o.data.vertices]
_al = [(v - gcR).dot(AX) for v in _av]
_bl = [v.co for o in B.parts if o.name in ("AxeBlade", "AxeEdge") for v in o.data.vertices]
_be = [(v - gcR).dot(EG) for v in _bl]; _ba = [(v - gcR).dot(AX) for v in _bl]
_e0 = P_ax(*edge_pt(0.0)); _e1 = P_ax(*edge_pt(1.0))
_AXE = dict(total=(max(_al) - min(_al)) / HT, blade_depth=max(_be) / HT, blade_along=(max(_ba) - min(_ba)) / HT,
            edge_chord=(_e1 - _e0).length / HT, haft_d=0.021, head_vs_hood=((_e1 - _e0).length / HT) / 0.11)
print("AXE", {k: round(v, 3) for k, v in _AXE.items()}, flush=True)
import json as _json
_MR["axe"] = {k: round(v, 4) for k, v in _AXE.items()}
open(os.path.join(TMP, "measure.json"), "w", encoding="utf-8").write(_json.dumps(_MR, ensure_ascii=False, indent=1))
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS", tri, "DETAILS", len(BD.parts), flush=True)
if os.environ.get("TRIDBG"):
    import re as _re
    agg = {}
    for o in B.parts:
        k = _re.sub(r"[0-9.\-_]+(R)?$", "", o.name)[:14]
        agg[k] = agg.get(k, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons) * (2 if o.get("cloth") else 1)
    for k, v in sorted(agg.items(), key=lambda x: -x[1])[:45]:
        print("TRIDBG", k, v)
mesh = VH.assemble2(B, BAKEKEY, size=(TEXS, TEXS), bake=not QUICK and "--nobake" not in argv, quick=QUICK, detail_of=DETAIL_OF, U=U, details=BD.parts, samples=int(os.environ.get("BAKE_SAMPLES", "12")))
BONE_OF = {"X2_HoodFace": "Head", "P2_AxeBlade2": "Weapon", "P2_HoodTorn": "Head", "P2_ChainHalo": "ChainHalo", "P2_ShadowArmL": "ShadowArmL",
           "P2_ShadowArmR": "ShadowArmR", "P2_InkArmL": "ForearmL", "P2_InkArmR": "ForearmR", "P2_InkLegL": "ShinL", "P2_InkLegR": "ShinR"}
parts = VH.split_parts(mesh, arm, lambda n: BONE_OF[n])
BK.bind(mesh, arm)
mesh.name = MODEL + "_mesh"
# Tip_Weapon：刃口弧中心
tipp = P_ax(*edge_pt(0.5))
tip = bpy.data.objects.new("Tip_Weapon", None)
bpy.context.scene.collection.objects.link(tip)
tip.empty_display_size = 0.05
tip.matrix_world = Matrix.Translation(tipp)
bpy.context.view_layer.update()
mw = tip.matrix_world.copy()
tip.parent = arm; tip.parent_type = "BONE"; tip.parent_bone = "Weapon"
bpy.context.view_layer.update()
tip.matrix_world = mw
print("TRIS_MAIN", BK.tri_count(mesh), "TRIS_P2", sum(BK.tri_count(o) for o in parts.values()), flush=True)

# ================================================================ 動作
legs = [("ThighL", "ShinL", h(0.06)), ("ThighR", "ShinR", h(0.06)), ("ShinL", "FootL", h(0.05)), ("ShinR", "FootR", h(0.05))]
rig = Rig(arm, body, chains=[
    dict(names=af_names, anchor="Hips", pts=af_pts, stiff=0.08, damp=0.90, colliders=legs, out=(0, -1, 0)),
    dict(names=ab_names, anchor="Hips", pts=ab_pts, stiff=0.07, damp=0.92, colliders=legs + [("Hips", "Spine", h(0.10))], out=(0, 1, 0))])
rig.tip_len = h(0.60)
rig.lie_dz = 0.19
if not NOANIM:
    import v3_executioner_actions as XA
    XA.build(rig, body, HT, only=ONLY)
    XA.extra_bones(arm, rig)

if not ONLY:
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    VH.export_glb(arm, [mesh, tip] + list(parts.values()), OUT_GLB)
    if not NOANIM:
        BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND if not QUICK else os.path.join(TMP, "v3_executioner_quick.blend"))
print("TRIS_FINAL", BK.tri_count(mesh) + sum(BK.tri_count(o) for o in parts.values()), flush=True)
print("DONE", MODEL, flush=True)
