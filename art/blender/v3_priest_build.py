"""v3 Boss：霜冠祭司 boss_priest（重建）。依 art/v3/specs/boss_priest.md、art/reference/v2/priest_p1.jpg／p2.jpg。
所有尺寸以 HH（＝冰冠最高尖到腳底，1.00H）為單位寫在規格表上，直接照表建。
  - 袍：外袍（前襟敞開、兩條金帶、縱向大皺褶、下擺撕成長條＋成簇冰柱）＋內袍（中央細金繡）＋披肩（連續一片、破邊、冰柱密）
  - 兜帽：貼頭尖拱軟帽；骷髏化凹陷臉、露齒、閉眼覆薄冰；放射扇形冰冠 12 根
  - 大袖：鐘形袖＋下垂袖尾（各 2 節布料骨 Sleeve1/2，動作時以擺錘模擬自然下垂）
  - 長槍 1.05H：銀柄細環、銀銎座、冰質葉形槍頭＋側倒鉤＋垂冰柱
  - 二階：P2_CrownHalo（7 段粗冰荊棘、下方開口、外徑 0.62H）、P2_CrownGrow、P2_FloatingBook（腰間只留空書扣，書只在二階出現）、
          P2_IceShards（長在袍面上的冰晶裙）、P2_Veins*
用法：blender --background --factory-startup --python v3_priest_build.py -- [--quick] [--nobake] [--noanim] [--only A,B]
"""
import bpy, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector, Quaternion, Matrix
from mathutils.kdtree import KDTree
from soul_humanoid_lib import *
from soul_humanoid_parts import angn, box, sabaton, hand, chain_links
import v3_priest_bake as BK
from soul_humanoid_anim import Rig, W, HW
import v2a_lib as VL

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOBAKE = "--nobake" in argv
NOANIM = "--noanim" in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
MODEL = "boss_priest"
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v3_" + MODEL + ".blend")
ROOT = os.path.dirname(os.path.dirname(HERE))
TMP = os.path.join(ROOT, "art", "v3", "tmp", "priest")
TEXDIR = os.path.join(TMP, "baked")
os.makedirs(TMP, exist_ok=True)

reset_scene()
HH = 2.66                      # 1.00H（冰冠尖→腳底）；遊戲縮放到 3.2 m
rnd = random.Random(31)


def h(x):
    return x * HH


def J(x, y, z):
    return V(x * HH, y * HH, z * HH)


# ---------------------------------------------------------------- 骨架比例（照規格表 §1）
body = Body(H=2.3, bulk=0.80, wf=0.84, head=0.25, hz=0.48 * HH / 2.3, arm_a=62, elbow=15, limb=0.84)
U = body.U
j = body.j
j["Hips"] = J(0, 0, 0.48); j["Spine"] = J(0, 0.002, 0.555); j["Spine2"] = J(0, 0.004, 0.645)
j["Neck"] = J(0, 0.008, 0.765); j["Head"] = J(0, 0.006, 0.795); j["HeadTop"] = J(0, 0.0, 0.875)
j["ShoulderL"] = J(0.02, 0.004, 0.738); j["UpperArmL"] = J(0.075, 0.004, 0.72)
_a = math.radians(62); _e = math.radians(15)
ud = V(math.cos(_a), 0, -math.sin(_a)); fd = (ud * math.cos(_e) + FWD * math.sin(_e)).normalized()
body.ud, body.fd = ud, fd
body.ua_len, body.fa_len, body.hand_len = h(0.13), h(0.11), h(0.045)
j["ForearmL"] = j["UpperArmL"] + ud * body.ua_len
j["HandL"] = j["ForearmL"] + fd * body.fa_len
j["HandTipL"] = j["HandL"] + fd * body.hand_len
j["ThighL"] = J(0.045, 0, 0.465); j["ShinL"] = J(0.05, -0.008, 0.27); j["FootL"] = J(0.054, 0.006, 0.036); j["ToeL"] = J(0.056, -0.046, 0.008)
for k in list(j):
    if k.endswith("L"):
        p = j[k]; j[k[:-1] + "R"] = V(-p.x, p.y, p.z)
body.hzv = j["Hips"].z; body.head_base = j["Head"].z; body.nz = j["Neck"].z
body.span = body.nz - body.hzv
body.tz = lambda t: body.hzv + body.span * t
body.th_len = (j["ShinL"] - j["ThighL"]).length; body.sh_len = (j["FootL"] - j["ShinL"]).length
body.hand_a = fd.copy()
_v = fd.cross(Z); body.hand_v = (_v if _v.dot(FWD) > 0 else -_v).normalized()   # 握持軸水平：靜止姿勢的長槍水平，不影響包圍盒高度
_hu = body.hand_v.cross(fd); body.hand_u = -_hu if _hu.x < 0 else _hu
body.RL = 1.10                   # 手（骨感大手，掌寬約 0.045H）
SHAFT_R = h(0.0055)
body.set_grip(SHAFT_R)
B = Builder()
BD = Builder()                    # 只進高模的細節（刺繡、縫線、浮雕）
BD.HIRES = False


class WMap:
    """依頂點位置找最近取樣點的權重（自訂曲面在 fn 裡記下權重）。"""

    def __init__(self):
        self.p = []; self.w = []; self.kd = None

    def add(self, p, w):
        self.p.append(p.copy()); self.w.append(w); self.kd = None
        return p

    def __call__(self, co):
        if self.kd is None:
            self.kd = KDTree(len(self.p))
            for i, q in enumerate(self.p):
                self.kd.insert(q, i)
            self.kd.balance()
        return self.w[self.kd.find(co)[1]]


def prof(tab, z):
    return tab_eval(tab, z)


def ell(tab, z, a, off=0.0):
    rx, ry, dv = prof(tab, z)
    s, c = math.sin(math.radians(a)), math.cos(math.radians(a))
    return V((rx + off) * s, -((ry + off) * c + dv), z)


def T(rows):
    """(z, rx, ry, dv)（H 單位）→ 公尺查表。"""
    return [(h(z), h(rx), h(ry), h(dv)) for z, rx, ry, dv in rows]


def soft(ob):
    ob["soft"] = 1
    return ob


def frost_attr(ob, fn):
    BK.set_attr(ob, fn)
    return ob


# ---------------------------------------------------------------- 材質
D = BK.define_mat
FROST_ROBE = dict(z0=0.04 * HH, z1=0.40 * HH, lo=0.16, hi=0.62, up=0.35, cav=0.55, attr=0.8, col=(0.80, 0.85, 0.88), rough=0.62)
# 法線：亞麻／羊毛平織紋（線距約 0.0024H），霜粒；顏色：#b4b8bb 底、#6c7176 凹處
D("robe", "A", tex="Fabric030", size=0.18, U=1, color=(0.40, 0.42, 0.44), tint=(0.62, 0.64, 0.66), sat=0.0, val=1.35, rough=0.9, metal=0.0, bump=0.9,
  bump_dist=0.0018, weave=(h(0.0024), 0.75), dirt=0.7, dirt_col=(0.10, 0.11, 0.12), ao_shade=0.55, seed=1.0,
  frost=FROST_ROBE)
D("robe_in", "A", tex="Fabric030", size=0.14, U=1, color=(0.31, 0.33, 0.35), tint=(0.50, 0.53, 0.55), sat=0.0, val=1.3, rough=0.9, metal=0.0, bump=0.8,
  bump_dist=0.0014, weave=(h(0.0017), 0.75), dirt=0.55, dirt_col=(0.11, 0.12, 0.13), ao_shade=0.45, seed=4.0,
  frost=dict(FROST_ROBE, lo=0.08, hi=0.45))
D("cape", "A", tex="Fabric030", size=0.16, U=1, color=(0.40, 0.42, 0.44), tint=(0.64, 0.66, 0.68), sat=0.0, val=1.35, rough=0.88, metal=0.0, bump=0.9,
  bump_dist=0.0018, weave=(h(0.0024), 0.75), dirt=0.7, dirt_col=(0.10, 0.11, 0.12), ao_shade=0.55, seed=6.0,
  frost=dict(FROST_ROBE, z0=0.60 * HH, z1=0.78 * HH, lo=0.04, hi=0.10, up=0.12, cav=-0.25, opac=0.6))
D("hood", "A", tex="Fabric030", size=0.20, U=1, color=(0.37, 0.39, 0.41), tint=(0.58, 0.60, 0.62), sat=0.0, val=1.3, rough=0.92, metal=0.0, bump=1.0,
  bump_dist=0.0022, weave=(h(0.0030), 0.8), dirt=0.55, dirt_col=(0.12, 0.13, 0.14), ao_shade=0.4, seed=8.0,
  frost=dict(FROST_ROBE, z0=0.74 * HH, z1=0.80 * HH, lo=0.10, hi=0.14, up=0.25, cav=0.35))
D("scarf", "A", tex="Fabric030", size=0.10, U=1, color=(0.068, 0.074, 0.08), tint=(0.24, 0.25, 0.26), sat=0.0, val=1.2, rough=0.92, metal=0.0, bump=0.9,
  bump_dist=0.0014, weave=(h(0.0014), 0.8), dirt=0.6, dirt_col=(0.05, 0.05, 0.055), ao_shade=0.6, seed=9.0,
  frost=dict(FROST_ROBE, lo=0.05, hi=0.05, up=0.25, cav=0.1))
D("band", "A", tex="Fabric030", size=0.10, U=1, color=(0.15, 0.15, 0.135), tint=(0.36, 0.36, 0.34), sat=0.0, val=1.2, rough=0.88, metal=0.0, bump=0.8,
  bump_dist=0.0012, weave=(h(0.0014), 0.6), dirt=0.6, dirt_col=(0.08, 0.08, 0.08), ao_shade=0.5, seed=12.0,
  frost=dict(FROST_ROBE, lo=0.12, hi=0.40))
D("void", "A", color=(0.020, 0.022, 0.025), flat_rough=1.0, dirt=0, ao_shade=0.0, bump=0.2)
# 金線（只出現在高模細節上）：#b89a55，被霜蓋掉約 30%
D("gthread", "A", color=(0.48, 0.33, 0.10), flat_rough=0.45, metal=0.7, dirt=0.3, dirt_col=(0.10, 0.08, 0.04), ao_shade=0.3, bump=0.6,
  bump_dist=0.0008, hnoise=900, frost=dict(FROST_ROBE, lo=0.18, hi=0.40, up=0.3, cav=0.4, rough=0.6))
D("stitch", "B", color=(0.22, 0.21, 0.19), flat_rough=0.8, dirt=0.3, ao_shade=0.3, bump=0.5)


def skin_fx(g, c):
    """乾皮：細皺紋（橫向波紋）＋凍裂（Voronoi 邊緣細線）。"""
    wav = g.N.new("ShaderNodeTexWave"); wav.wave_type = "BANDS"; wav.bands_direction = "Z"
    wav.inputs["Scale"].default_value = 260.0; wav.inputs["Distortion"].default_value = 6.0
    wav.inputs["Detail"].default_value = 3.0
    g.L.new(g.tc.outputs["Object"], wav.inputs["Vector"])
    wr = g.mul(wav.outputs["Fac"], 0.35)
    crack = g.voronoi(90.0, "DISTANCE_TO_EDGE", "Distance", 3.0)
    cm = g.mul(g.math("SUBTRACT", 1.0, g.ramp(crack, 0.0, 0.02)), g.ramp(g.noise(30.0, 3, 0.6, 7.0), 0.5, 0.7))
    c["h"] = g.add(g.add(g.mul(c["h"], 0.5), wr), g.mul(cm, -0.5))
    c["col"] = g.mix(g.mul(cm, 0.55), c["col"], (0.13, 0.12, 0.13))
    blot = g.ramp(g.noise(70.0, 5, 0.65, 13.0), 0.45, 0.75)
    c["col"] = g.mix(g.mul(blot, 0.35), c["col"], (0.20, 0.18, 0.19))          # 屍斑／暗斑
    c["col"] = g.mix(g.mul(g.ramp(g.noise(140.0, 3, 0.6, 29.0), 0.55, 0.8), 0.25), c["col"], (0.55, 0.54, 0.53))
    c["rough"] = g.add(c["rough"], g.mul(g.add(g.noise(90.0, 3, 0.6, 31.0), -0.5), 0.35))
    c["h"] = g.add(c["h"], g.mul(blot, -0.25))


D("skin", "B", color=(0.36, 0.35, 0.355), flat_rough=0.7, metal=0.0, dirt=1.0, dirt_col=(0.11, 0.10, 0.105), ao_shade=0.45,
  bump=1.3, bump_dist=0.0014, hnoise=400, fx=skin_fx, seed=3.0,
  frost=dict(z0=0, z1=1, lo=0.0, hi=0.0, up=0.15, cav=0.15, attr=0.9, col=(0.78, 0.82, 0.85), rough=0.6))
D("teeth", "B", color=(0.48, 0.44, 0.36), flat_rough=0.55, dirt=0.8, dirt_col=(0.10, 0.08, 0.06), ao_shade=0.6, bump=0.4, hnoise=600)
D("leather", "B", tex="Leather026", size=0.20, U=1, color=(0.085, 0.084, 0.078), tex_mean=0.010, val=2.2, sat=0.2, tint=(0.11, 0.11, 0.105), rough=0.75, metal=0.0, dirt=0.8,
  wear=0.7, wear_col=(0.15, 0.16, 0.17), bump=0.9, bump_dist=0.0015, frost=dict(FROST_ROBE, lo=0.10, hi=0.35, up=0.4))
D("boot", "B", tex="Leather026", size=0.16, U=1, color=(0.17, 0.18, 0.19), tex_mean=0.010, val=2.4, sat=0.2, tint=(0.17, 0.175, 0.185), rough=0.75, metal=0.0, dirt=0.8,
  wear=0.6, wear_col=(0.28, 0.29, 0.31), bump=1.0, bump_dist=0.0015, frost=dict(FROST_ROBE, lo=0.15, hi=0.30, up=0.3))
D("silver", "B", tex="Metal024", size=0.25, U=1, color=(0.40, 0.42, 0.45), tex_mean=0.20, tint=(0.40, 0.43, 0.46), sat=0.0, val=1.1, metal=0.92, rough=0.34, wear=0.6,
  wear_col=(0.70, 0.73, 0.76), dirt=0.9, dirt_col=(0.05, 0.05, 0.055), bump=0.6, bump_dist=0.0012, seed=8.0,
  frost=dict(z0=0, z1=1, lo=0.06, hi=0.06, up=0.05, cav=0.45, attr=0.9, col=(0.80, 0.85, 0.88), rough=0.6))
D("gold", "B", tex="Metal024", size=0.25, U=1, color=(0.32, 0.19, 0.045), tex_mean=0.20, tint=(0.55, 0.40, 0.14), sat=0.4, val=1.0, metal=0.9, rough=0.40, wear=0.6,
  wear_col=(0.72, 0.58, 0.28), dirt=1.0, dirt_col=(0.06, 0.045, 0.02), bump=0.6, bump_dist=0.0012, seed=11.0)
D("bookleather", "B", tex="Leather026", size=0.10, U=1, color=(0.042, 0.024, 0.014), tex_mean=0.010, rough=0.7, metal=0.0, dirt=0.8,
  wear=0.7, wear_col=(0.10, 0.07, 0.045), bump=1.0, bump_dist=0.0015, frost=dict(FROST_ROBE, lo=0.08, hi=0.25, up=0.4))
D("paper", "B", color=(0.55, 0.50, 0.38), flat_rough=0.85, dirt=0.8, dirt_col=(0.12, 0.10, 0.07), ao_shade=0.6, bump=0.8, bump_dist=0.0008, hnoise=1500)
D("nail", "B", color=(0.13, 0.14, 0.15), flat_rough=0.45, dirt=0.6, dirt_col=(0.04, 0.04, 0.045), ao_shade=0.4, bump=0.4, hnoise=800)
D("bookcov", "B", tex="Leather026", size=0.12, U=1, color=(0.027, 0.042, 0.039), tex_mean=0.010, val=2.0, sat=0.5, tint=(0.08, 0.13, 0.12), rough=0.7, metal=0.0, dirt=0.9,
  wear=0.6, wear_col=(0.16, 0.22, 0.20), bump=1.0, bump_dist=0.0015)


def ice_fx(g, c):
    """冰：內部裂紋（白色細線＋法線凹痕）、稜面明暗（深處 #8fb0c0）。"""
    cr = g.voronoi(55.0, "DISTANCE_TO_EDGE", "Distance", 5.0, stretch=(1, 1, 0.35))
    cm = g.math("SUBTRACT", 1.0, g.ramp(cr, 0.0, 0.02))
    cr2 = g.voronoi(160.0, "DISTANCE_TO_EDGE", "Distance", 9.0)
    cm2 = g.math("SUBTRACT", 1.0, g.ramp(cr2, 0.0, 0.025))
    deep = g.ramp(g.noise(9.0, 4, 0.6, 21.0), 0.35, 0.7)
    c["col"] = g.mix(g.mul(deep, 0.55), c["col"], (0.20, 0.33, 0.42))
    c["col"] = g.mix(g.mul(cm, 0.7), c["col"], (0.80, 0.90, 0.96))
    c["col"] = g.mix(g.mul(cm2, 0.35), c["col"], (0.75, 0.86, 0.93))
    c["h"] = g.add(g.mul(c["h"], 0.3), g.add(g.mul(cm, -0.8), g.mul(cm2, -0.3)))
    c["rough"] = g.mixf(cm, c["rough"], 0.45)


D("ice", "C", color=(0.58, 0.74, 0.84), flat_rough=0.18, metal=0.0, dirt=0.25, dirt_col=(0.20, 0.32, 0.42), ao_shade=0.25,
  bump=0.6, bump_dist=0.0015, hnoise=120, fx=ice_fx, seed=2.0,
  frost=dict(z0=0, z1=1, lo=0.0, hi=0.0, up=0.10, cav=0.25, attr=1.0, col=(0.86, 0.91, 0.94), rough=0.55, gh=0.6))
BLUE = "#8fe3ff"
VL.glow_mat("Glow_Eye", BLUE, 0.45)
VL.glow_mat("Glow_Rune", BLUE, 0.35)
VL.glow_mat("Glow_Weapon", BLUE, 0.28)
VL.glow_mat("P2_Glow_Halo", BLUE, 0.9)
VL.glow_mat("P2_Glow_Book", BLUE, 2.0)
VL.glow_mat("P2_Glow_BookDim", BLUE, 0.7)
VL.glow_mat("P2_Glow_Veins", BLUE, 1.2)
_ge = bpy.data.materials["Glow_Eye"]
next(n for n in _ge.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.30, 0.40, 0.46, 1)
next(n for n in _ge.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Roughness"].default_value = 0.15


# ---------------------------------------------------------------- 冰柱（不規則、成簇、根部有霜）
def icicle(name, root, ln, r, w, d=None, bend=None, segs=5):
    d = (d or V(0, 0, -1)).normalized()
    bend = bend if bend is not None else V(rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0) * 0.18
    p0 = root - d * r * 0.8
    p1 = root + d * ln * 0.40 + bend * ln * 0.10
    p2 = root + d * ln * 0.75 + bend * ln * 0.28
    p3 = root + d * ln + bend * ln * 0.45
    rr = [r * 1.05, r * rnd.uniform(0.55, 0.75), r * rnd.uniform(0.25, 0.4), h(0.0004)]
    ob = B.tube(name, [p0, p1, p2, p3], rr, segs, "ice", w, texel=0.9, sharp=30)
    L = ln
    frost_attr(ob, lambda co: clamp(1.0 - (co - root).dot(d) / (L * 0.35)))
    return ob


def cluster(name, root, n, lmin, lmax, rmin, rmax, w, out=None, maxlen=None, spread=None):
    obs = []
    side = spread if spread is not None else V(1, 0, 0)
    for q in range(n):
        ln = rnd.uniform(lmin, lmax)
        if maxlen is not None:
            ln = min(ln, maxlen * rnd.uniform(0.85, 1.0))
        if ln < h(0.006):
            continue
        p = root + side * rnd.uniform(-1, 1) * h(0.007) + (out or V(0, 0, 0)) * rnd.uniform(0, 0.004)
        d = V(0, 0, -1) + (out or V(0, 0, 0)) * rnd.uniform(0.0, 0.25)
        obs.append(icicle(f"{name}_{q}", p, ln, rnd.uniform(rmin, rmax), w, d))
    return obs


# ---------------------------------------------------------------- 權重
w_torso = body.w_torso()


# 袍擺布料骨：8 條（每 45°）× 2 節，錨在 Hips。動作時以擺錘模擬（重力、地面 z≥0.02、腿部膠囊碰撞把袍推開），
# 下擺不再直接跟著大腿／小腿，弓步時不會被腿帶進地面。
HEM_N = 8
HEM_Z0, HEM_Z1 = 0.46, 0.012


def hem_chain_pts(k):
    a = k * 360.0 / HEM_N
    return [ell(RT, h(z), a, h(0.004)) for z in (HEM_Z0, (HEM_Z0 + HEM_Z1) / 2, HEM_Z1)]


def w_robe(co):
    if co.z > h(HEM_Z0 + 0.02):
        return w_torso(co)
    a = math.degrees(math.atan2(co.x, -co.y)) % 360.0
    ci = a / (360.0 / HEM_N)
    k0 = int(ci) % HEM_N; k1 = (k0 + 1) % HEM_N; f = ci - int(ci)
    t = (h(HEM_Z0) - co.z) / h(HEM_Z0 - HEM_Z1)
    a1 = smooth(t / 0.30); a2 = smooth((t - 0.38) / 0.35)
    w = {"Hips": 1 - a1}
    for kk, fw in ((k0, 1 - f), (k1, f)):
        w[f"Hem{kk}A"] = w.get(f"Hem{kk}A", 0) + a1 * (1 - a2) * fw
        w[f"Hem{kk}B"] = w.get(f"Hem{kk}B", 0) + a1 * a2 * fw
    return w


def w_cape(co):
    base = w_torso(co)
    ax = abs(co.x)
    a = smooth((ax - h(0.075)) / h(0.06)) * 0.6
    if a < 1e-3:
        return base
    sd = "L" if co.x > 0 else "R"
    out = {k: v * (1 - a) for k, v in base.items()}
    out["Shoulder" + sd] = out.get("Shoulder" + sd, 0) + a * 0.45
    out["UpperArm" + sd] = out.get("UpperArm" + sd, 0) + a * 0.55
    return out


# ---------------------------------------------------------------- 外袍：前襟敞開、縱向皺褶、下擺長條
RT = T([(0.00, 0.177, 0.132, -0.012), (0.08, 0.170, 0.126, -0.010), (0.18, 0.157, 0.113, -0.008), (0.30, 0.142, 0.096, -0.006),
        (0.40, 0.120, 0.079, -0.003), (0.47, 0.098, 0.064, 0.0), (0.545, 0.070, 0.047, 0.002), (0.60, 0.083, 0.059, 0.003),
        (0.66, 0.090, 0.061, 0.002), (0.72, 0.084, 0.058, 0.0), (0.76, 0.050, 0.046, 0.0)])
XE = [(0.0, 0.052), (0.30, 0.045), (0.545, 0.032), (0.66, 0.027), (0.76, 0.018)]
Z_TOP = h(0.748)
PH = [rnd.uniform(0, 6.28) for _ in range(6)]


def xe(z):
    return h(tab_eval([(h(a), b) for a, b in XE], z)[0])


def a_edge(z):
    rx = prof(RT, z)[0]
    return math.degrees(math.asin(min(0.95, xe(z) / rx)))


def fold(a, z):
    """縱向大皺褶：每側 5 條左右（上窄下寬、略帶扭轉），H 單位的半徑偏移。"""
    amp = h(0.0035 + 0.013 * smooth((0.60 * HH - z) / (0.48 * HH)))
    ar = math.radians(a) + 0.25 * (z / HH)
    f = 0.55 * math.sin(10 * ar + PH[0]) + 0.30 * math.sin(17 * ar + PH[1]) + 0.18 * math.sin(29 * ar + PH[2])
    ridge = abs(math.sin(5 * ar + PH[3])) ** 4 - 0.35
    return amp * (f + 0.6 * ridge)


# 下擺長條：用整數欄切條（每條 3–8 欄、寬窄不一），尖端長短差到 0.12H、條與條之間撕開深淺不一
NU = 132
strips = []
c0 = 0
while c0 < NU:
    wdt = rnd.choice((3, 4, 5, 5, 6, 7, 8))
    if NU - c0 < 9:
        wdt = NU - c0
    strips.append((c0, c0 + wdt))
    c0 += wdt
tips = []
for k, (a0, a1) in enumerate(strips):
    front_panel = k == 0 or k == len(strips) - 1
    am = 16 + (360 - 32) * (a0 + a1) / 2 / NU
    side_ = 55 < am < 125 or 235 < am < 305                 # 兩側（正面剪影最寬處）的長條拖到地
    if front_panel:
        tz = rnd.uniform(0.10, 0.16)
    elif side_ or rnd.random() < 0.45:
        tz = 0.016 + rnd.random() * 0.010
    else:
        tz = 0.03 + rnd.random() ** 1.3 * 0.11
    tips.append((tz, rnd.uniform(0.25, 0.75)))
notch = [0.0] * (len(strips) + 1)
for k in range(len(strips) + 1):
    t_l = tips[k - 1][0] if k > 0 else tips[0][0]
    t_r = tips[k][0] if k < len(strips) else tips[-1][0]
    notch[k] = max(t_l, t_r) + (rnd.uniform(0.03, 0.12) if rnd.random() < 0.8 else rnd.uniform(0.006, 0.02))
HEMZ = []
for k, (a0, a1) in enumerate(strips):
    tz, sp = tips[k]
    for c in range(a0, a1):
        s = (c - a0) / (a1 - a0)
        if s < sp:
            z = tz + (notch[k] - tz) * (1 - s / sp) ** 1.7
        else:
            z = tz + (notch[k + 1] - tz) * ((s - sp) / (1 - sp)) ** 1.7
        HEMZ.append(h(z))
HEMZ.append(h(notch[-1]))


def hem_z(u):
    x = u * NU
    i = min(int(x), NU - 1); f = x - i
    return lerp(HEMZ[i], HEMZ[i + 1], f)


def robe_pt(u, z, off=0.0):
    ae = a_edge(z)
    a = ae + (360 - 2 * ae) * u
    return ell(RT, z, a, off + fold(a, z)), a


wm_robe = WMap()
NV = 20


def robe_fn(u, v):
    zb = hem_z(u)
    z = lerp(Z_TOP, zb, 1 - (1 - v) ** 1.25)
    p, a = robe_pt(u, z)
    return wm_robe.add(p, w_robe(p))


holes = set()
for _ in range(9):
    k = rnd.randrange(2, len(strips) - 2)
    a0, a1 = strips[k]
    if a1 - a0 >= 4:
        holes.add((rnd.randrange(a0 + 1, a1 - 1), NV - rnd.choice((2, 3))))
robe = soft(B.grid("Robe", NU, NV, robe_fn, "robe", wm_robe, [V(0, 0, h(z)) for z in (0.05, 0.3, 0.5, 0.7)],
                   holes=lambda i, jv: (i, jv) in holes, rim=h(0.006), texel=1.0, sharp=60))
frost_attr(robe, lambda co: 0.5 * smooth((h(0.10) - co.z) / h(0.08)))

# 前襟金帶（0.025H、凸出 0.0012H）＋原創捲草紋金線（只烘到貼圖）
BAND_W = h(0.025)


def band_pt(side, t, z, off=h(0.0014)):
    """side=+1 左襟（+X）、-1 右襟。t：0＝前緣、1＝往外 0.025H。"""
    ae = a_edge(z)
    rx = prof(RT, z)[0]
    a1 = math.degrees(math.asin(min(0.97, (xe(z) + BAND_W) / rx)))
    a = ae + (a1 - ae) * t
    if side < 0:
        a = 360 - a
    return ell(RT, z, a, off + fold(a, z))


def band_bottom(side):
    c = 1 if side > 0 else NU - 2
    return HEMZ[c] + h(0.004)


for side in (1, -1):
    wmb = WMap()
    zb = band_bottom(side)

    def bfn(u, v, side=side, zb=zb, wmb=wmb):
        z = lerp(Z_TOP - h(0.004), zb, v)
        p = band_pt(side, u, z)
        return wmb.add(p, w_robe(p))
    soft(B.grid(f"GoldBand{side}", 3, 40, bfn, "band", wmb, [V(0, 0, h(z)) for z in (0.1, 0.4, 0.7)], rim=h(0.0015), texel=1.4, sharp=60))
    # 捲草紋：中央波浪莖＋左右交替的螺旋捲鬚＋外側兩道細邊線
    n_c = int((Z_TOP - zb) / h(0.03))
    for edge_t in (0.1, 0.9):
        pts = [band_pt(side, edge_t, lerp(Z_TOP - h(0.01), zb + h(0.01), q / 60), h(0.0026)) for q in range(61)]
        BD.tube(f"BandEdge{side}{edge_t}", pts, [h(0.0009)] * 61, 4, "gthread", "Hips")
    stem = [band_pt(side, 0.5 + 0.22 * math.sin(q / 60 * n_c * math.pi), lerp(Z_TOP - h(0.012), zb + h(0.012), q / 60), h(0.0028)) for q in range(61)]
    BD.tube(f"BandStem{side}", stem, [h(0.0011)] * 61, 4, "gthread", "Hips")
    for q in range(n_c):
        zc = lerp(Z_TOP - h(0.025), zb + h(0.02), (q + 0.5) / n_c)
        sg = 1 if q % 2 else -1
        pts = []
        for i in range(12):
            th = i / 11 * 1.6 * math.pi
            rr = h(0.0085) * (1 - i / 13)
            pts.append(band_pt(side, 0.5 + sg * (rr * math.cos(th)) / BAND_W, zc + rr * math.sin(th) * sg, h(0.0028)))
        BD.tube(f"BandCurl{side}_{q}", pts, [h(0.0010)] * 12, 4, "gthread", "Hips")
        for sd in (-1, 1):
            BD.ellipsoid(f"BandDot{side}_{q}{sd}", band_pt(side, 0.5 + sd * 0.33, zc + h(0.012) * sg, h(0.0026)), (X, Y, Z),
                         (h(0.0016),) * 3, 6, 4, "gthread", "Hips")

# 下擺冰柱：隨機落在條的斜邊上（不是排一排），成簇 2–4 根、0.03–0.08H、長短粗細不一，貼地的尖端不掛
for k, (a0, a1) in enumerate(strips):
    if rnd.random() < 0.25:
        continue
    for _ in range(rnd.choice((1, 1, 2))):
        u = (rnd.uniform(a0, a1)) / NU
        zh = hem_z(u)
        if zh < h(0.04):
            continue
        p, a = robe_pt(u, zh + h(0.005), h(0.002))
        outv = (p - V(0, 0, p.z)).normalized()
        cluster(f"HemIce{k}_{int(u * 1000)}", p, rnd.choice((2, 2, 3, 4)), h(0.03), h(0.08), h(0.0025), h(0.0065), w_robe(p), out=outv,
                maxlen=zh - h(0.006), spread=outv.cross(Z))

# ---------------------------------------------------------------- 內袍（前襟縫中看到的那層）＋中央細金繡
RI = T([(0.01, 0.142, 0.110, -0.008), (0.15, 0.128, 0.098, -0.006), (0.30, 0.112, 0.082, -0.004), (0.47, 0.084, 0.057, 0.0),
        (0.545, 0.056, 0.039, 0.002), (0.60, 0.068, 0.051, 0.003), (0.66, 0.075, 0.053, 0.002), (0.72, 0.068, 0.050, 0.002),
        (0.77, 0.034, 0.036, 0.004)])
cut_in = [rnd.uniform(0, 1) for _ in range(29)]
wm_in = WMap()


def inner_fn(u, v):
    a = -80 + 160 * u
    k = int(round(u * 28))
    zb = h(0.012 + 0.03 * cut_in[k] ** 2)
    z = lerp(h(0.77), zb, v)
    p = ell(RI, z, a, 0.35 * fold(a * 1.7, z))
    return wm_in.add(p, w_robe(p))


soft(B.grid("InnerRobe", 28, 16, inner_fn, "robe_in", wm_in, [V(0, 0, h(z)) for z in (0.05, 0.3, 0.5, 0.7)], rim=h(0.004), texel=0.9, sharp=60))
for q in range(2):
    xo = (q - 0.5) * h(0.010)
    pts = [ell(RI, lerp(h(0.70), h(0.06), i / 50), math.degrees(xo / h(0.06)), h(0.0022)) for i in range(51)]
    BD.tube(f"InnerLine{q}", pts, [h(0.0008)] * 51, 4, "gthread", "Hips")
for i in range(16):
    z = lerp(h(0.68), h(0.08), i / 15)
    BD.ellipsoid(f"InnerKnot{i}", ell(RI, z, 0, h(0.0024)), (X, Y, Z), (h(0.004), h(0.0015), h(0.004)), 6, 4, "gthread", "Hips")

# ---------------------------------------------------------------- 腰帶：皮帶＋橢圓銀扣＋垂下帶尾；第二條細帶＋空書扣與書鏈（書只在二階出現）
ZB = h(0.545)
wm_belt = WMap()


def belt_fn(u, v):
    a = u * 360
    z = ZB + h(0.009) * (1 - 2 * v)
    p = ell(RI, z, a, h(0.0035))
    return wm_belt.add(p, {"Spine": 0.5, "Hips": 0.5})


belt = B.grid("Belt", 28, 2, belt_fn, "leather", wm_belt, [V(0, 0, ZB)], closed_u=True, rim=h(0.002), texel=1.5)
for sg in (1, -1):
    pts = [ell(RI, ZB + sg * h(0.0072), a, h(0.0046)) for a in range(-60, 61, 6)]
    BD.tube(f"BeltStitch{sg}", pts, [h(0.0007)] * len(pts), 4, "stitch", "Hips")
bkc = ell(RI, ZB, 0, h(0.0062))
B.ellipsoid("Buckle", bkc, (X, Z, -Y), (h(0.0125), h(0.0105), h(0.003)), 14, 4, "silver", {"Spine": 0.5, "Hips": 0.5}, rim=0, texel=2.0)
B.tube("BuckleRing", [bkc + V(math.cos(t) * h(0.0125), -h(0.003), math.sin(t) * h(0.0105)) for t in [i / 16 * 6.283 for i in range(17)]],
       [h(0.0018)] * 17, 5, "silver", {"Spine": 0.5, "Hips": 0.5}, cap=False)
tail = [bkc + V(h(0.004), -h(0.004), -h(0.006)), bkc + V(h(0.006), -h(0.006), -h(0.05)), bkc + V(h(0.004), -h(0.009), -h(0.09)),
        bkc + V(h(0.008), -h(0.012), -h(0.125))]
B.tube("BeltTail", tail, [(h(0.0060), h(0.0014))] * 4, 6, "leather", lambda co: w_robe(co), exp=4, flat=X, texel=1.5)
# 第二條細帶（往右胯斜下）
ZB2 = h(0.522)
wm_b2 = WMap()


def belt2_fn(u, v):
    a = u * 360
    z = ZB2 - h(0.018) * math.sin(math.radians(a)) * -1 * 0.5 + h(0.005) * (1 - 2 * v)
    p = ell(RI, z, a, h(0.006))
    return wm_b2.add(p, {"Spine": 0.3, "Hips": 0.7})


B.grid("Belt2", 28, 2, belt2_fn, "leather", wm_b2, [V(0, 0, ZB2)], closed_u=True, rim=h(0.0015), texel=1.2)
hook = ell(RI, ZB2 - h(0.012), -32, h(0.009))
B.tube("BookHook", [hook + V(0, 0, h(0.008)), hook, hook - V(0, h(0.004), h(0.012))], [h(0.003)] * 3, 6, "gold", "Hips")
chp = [hook - V(0, h(0.004), h(0.012)) - V(h(0.002) * q, h(0.002) * q, h(0.0095) * q) for q in range(7)]
chain_links(B, chp, "silver", "Hips", link_r=h(0.0035), wire=h(0.0010), name="BookChain")
cl = chp[-1] - V(0, 0, h(0.008))
box(B, "BookClaspPlate", cl, X, Z, -Y, h(0.007), h(0.010), h(0.0016), "gold", "Hips", exp=4)
B.tube("BookClaspRing", [cl + V(math.cos(t) * h(0.0045), -h(0.003), -h(0.010) + math.sin(t) * h(0.0045)) for t in [i / 12 * 6.2832 for i in range(13)]],
       [h(0.0011)] * 13, 5, "gold", "Hips", cap=False)

# ---------------------------------------------------------------- 袖子尺寸（披肩要避開上臂，先定義）
S_C = body.ua_len + body.fa_len - h(0.006)          # 袖口（沿手臂）
SLEEVE_TAB = [(0.0, 0.029), (0.04, 0.038), (0.065, 0.045), (0.13, 0.050), (0.19, 0.057), (S_C / HH, 0.066)]


def arm_axis(s):
    if s <= body.ua_len:
        return j["UpperArmL"] + ud * s
    return j["ForearmL"] + fd * (s - body.ua_len)


def arm_dir(s):
    t = smooth((s - body.ua_len + h(0.03)) / h(0.06))
    return ud.lerp(fd, t).normalized()


def sleeve_R(s):
    return h(tab_eval([(h(a), b) for a, b in SLEEVE_TAB], s)[0])


def arm_deficit(p, margin=h(0.003)):
    """p 離（左右）上臂袖表面不夠遠的量（>0 表示會穿進袖子）。"""
    worst = -1.0
    for sx in (1, -1):
        A = j["UpperArmL"].copy(); E = j["ForearmL"].copy()
        if sx < 0:
            A.x, E.x = -A.x, -E.x
        q = Vector((p.x, p.y, p.z))
        ab = E - A
        t = clamp((q - A).dot(ab) / ab.length_squared)
        d = (q - (A + ab * t)).length
        worst = max(worst, sleeve_R(t * body.ua_len) + margin - d)
    return worst


# ---------------------------------------------------------------- 披肩：連續一片、窄斜肩、前方 V、放射皺褶、下緣破爛＋密冰柱＋金刺繡邊
CT = T([(0.62, 0.136, 0.090, 0.0), (0.66, 0.126, 0.086, 0.0), (0.69, 0.116, 0.082, 0.0), (0.72, 0.093, 0.073, 0.0),
        (0.74, 0.082, 0.067, 0.001), (0.755, 0.071, 0.060, 0.002), (0.77, 0.052, 0.050, 0.004), (0.787, 0.037, 0.041, 0.005)])
NUC = 96
cape_rag = []
for i in range(NUC + 1):
    cape_rag.append(rnd.uniform(0, 0.010) + (rnd.uniform(0.012, 0.03) if rnd.random() < 0.25 else 0.0))
cape_rag[-1] = cape_rag[0]


def cape_base(a):
    a = angn(a)
    fr = math.exp(-(a / 34) ** 2); side = math.exp(-((abs(a) - 95) / 38) ** 2); bk = math.exp(-((abs(a) - 180) / 50) ** 2)
    return h(0.648 + 0.030 * fr + 0.004 * side - 0.010 * bk)


def cape_off(a, z):
    v = clamp((h(0.787) - z) / h(0.15))
    ar = math.radians(a)
    ridge = abs(math.sin(5 * ar + PH[4])) ** 2.5 - 0.3            # 前後各約 5 條放射皺褶
    return h(0.013) * ridge * v ** 1.0 + h(0.003) * math.sin(13 * ar + PH[5]) * v + h(0.002)


def cape_pt(a, z):
    off = cape_off(a, z)
    p = ell(CT, z, a, off)
    for _ in range(40):            # 沿肩斜垂下、蓋住上臂（局部撐開），不是整圈鼓起
        if arm_deficit(p) <= 0:
            break
        off += h(0.0015)
        p = ell(CT, z, a, off)
    return p


wm_cape = WMap()


def cape_fn(u, v):
    a = u * 360
    i = min(int(u * NUC), NUC - 1)
    zb = cape_base(a) - h(cape_rag[i])
    z = lerp(h(0.787), zb, v)
    p = cape_pt(a, z)
    return wm_cape.add(p, w_cape(p))


cape = soft(B.grid("Capelet", NUC, 10, cape_fn, "cape", wm_cape, [V(0, 0, h(z)) for z in (0.66, 0.70, 0.74, 0.78)], closed_u=True,
                   rim=h(0.006), texel=1.2, sharp=75))
frost_attr(cape, lambda co: 0.06 * smooth((co.z - h(0.74)) / h(0.04)))
# 金刺繡邊（寬 0.01H，在下緣上方）
for q in range(2):
    pts = []
    for i in range(121):
        a = i * 3
        z = cape_base(a) + h(0.010 + 0.007 * q)
        pts.append(cape_pt(a, z) + (cape_pt(a, z) - V(0, 0, z)).normalized() * h(0.0022))
    BD.tube(f"CapeTrim{q}", pts, [h(0.0009)] * 121, 4, "gthread", "Spine2")
for i in range(60):
    a = i * 6 + 3
    z = cape_base(a) + h(0.0135)
    p = cape_pt(a, z)
    p = p + (p - V(0, 0, z)).normalized() * h(0.0022)
    BD.ellipsoid(f"CapeTrimDot{i}", p, (X, Y, Z), (h(0.0022), h(0.0022), h(0.0022)), 6, 4, "gthread", "Spine2")
# 冰柱：間距約 0.012H、長 0.01–0.04H，長短粗細不一
for i in range(66):
    a = i * (360 / 66) + rnd.uniform(-2.5, 2.5)
    k = min(int(a / 360 * NUC), NUC - 1)
    z = cape_base(a) - h(cape_rag[k]) + h(0.004)
    p = cape_pt(a, z)
    if rnd.random() < 0.8:
        ln = h(rnd.uniform(0.008, 0.035) if rnd.random() < 0.75 else rnd.uniform(0.035, 0.055))
        icicle(f"CapeIce{i}", p, ln, h(rnd.uniform(0.002, 0.0048)), w_cape(p), segs=4)

# ---------------------------------------------------------------- 內圍巾（深灰毛料，纏兩圈）
NT = T([(0.735, 0.034, 0.036, 0.004), (0.76, 0.030, 0.032, 0.006), (0.785, 0.025, 0.028, 0.006), (0.797, 0.021, 0.024, 0.006)])
wm_sc = WMap()


def scarf_fn(u, v):
    a = u * 360
    z = lerp(h(0.735), h(0.797), v)
    roll = h(0.0045) * abs(math.sin(math.pi * (v * 2 + 0.15 * math.sin(math.radians(a)))))
    p = ell(NT, z, a, roll + h(0.001) * math.sin(math.radians(a) * 5))
    return wm_sc.add(p, w_torso(p))


B.grid("Scarf", 20, 10, scarf_fn, "scarf", wm_sc, [V(0, 0, h(z)) for z in (0.74, 0.79)], closed_u=True, texel=1.2)

# ---------------------------------------------------------------- 兜帽：貼頭的尖拱軟帽（頂往後收成鈍尖、背後有垂布與摺痕、冠壓出凹陷），下巴兩側收攏
# (z, rx, 前半徑, 後半徑, 中心往後)
HTF = [(0.745, 0.090, 0.075, 0.096, 0.010), (0.765, 0.074, 0.070, 0.090, 0.010), (0.79, 0.063, 0.067, 0.082, 0.008),
       (0.82, 0.060, 0.064, 0.076, 0.008), (0.845, 0.055, 0.060, 0.072, 0.010), (0.865, 0.046, 0.052, 0.068, 0.013),
       (0.885, 0.033, 0.038, 0.060, 0.018), (0.902, 0.019, 0.022, 0.048, 0.026), (0.915, 0.005, 0.006, 0.026, 0.036)]
HTFm = [(h(r[0]),) + tuple(h(x) for x in r[1:]) for r in HTF]
OPEN = [(0, 0.852), (20, 0.849), (34, 0.842), (44, 0.828), (50, 0.80), (58, 0.775), (70, 0.752), (85, 0.745), (180, 0.745)]
HANG = sorted(set([round(x) for x in list(range(-180, 181, 12)) + list(range(-76, 77, 4))]))[:-1]
Z_HOOD_TOP = h(0.915)


def hood_pt(z, a, off=0.0):
    rx, ryf, ryb, cy = tab_eval(HTFm, z)
    ar = math.radians(a)
    sn, cs = math.sin(ar), math.cos(ar)
    back = max(0.0, -cs)
    fold = h(0.0045) * math.sin(5 * ar + 0.7) * back * clamp((h(0.85) - z) / h(0.08))          # 背後垂布摺痕
    dent = -h(0.0035) * math.exp(-((z - h(0.874)) / h(0.008)) ** 2)                            # 冰冠壓出的凹陷
    o = off + fold + dent
    ry = ryf if cs >= 0 else ryb
    return V((rx + o) * sn, cy - (ry + o) * cs, z)


def hood_lo(a):
    return h(tab_eval([(x, y) for x, y in OPEN], abs(angn(a)))[0])


wm_hood = WMap()


def hood_fn(u, v):
    i = int(round(u * len(HANG))) % len(HANG)
    a = HANG[i]
    z0 = hood_lo(a)
    z = lerp(z0, Z_HOOD_TOP, v ** 1.05)
    fl = h(0.003) * math.sin(math.radians(a) * 6 + 1.0) * clamp((h(0.80) - z) / h(0.05))
    p = hood_pt(z, a, fl)
    return wm_hood.add(p, w_torso(p))


hood = soft(B.grid("Hood", len(HANG), 12, hood_fn, "hood", wm_hood, [V(0, h(0.01), h(z)) for z in (0.76, 0.80, 0.84, 0.88)], closed_u=True,
                   rim=h(0.006), texel=1.4, sharp=75))
frost_attr(hood, lambda co: 0.3 * smooth(1 - abs(co.z - hood_lo(math.degrees(math.atan2(co.x, -co.y)))) / h(0.010)))
wm_hl = WMap()


def hl_fn(u, v):
    a = -110 + 220 * u
    z = lerp(max(hood_lo(a) + h(0.004), h(0.77)), h(0.885), v)
    p = hood_pt(z, a, -h(0.0045))
    return wm_hl.add(p, w_torso(p))


B.grid("HoodLining", 20, 6, hl_fn, "void", wm_hl, [V(0, h(0.2), h(0.83))], texel=0.3)
for sx in (1, -1):
    for q in range(rnd.choice((3, 4, 5))):
        a = sx * (56 + q * 6 + rnd.uniform(-2, 2))
        z = hood_lo(a) + h(0.003)
        p = hood_pt(z, a, h(0.002))
        icicle(f"HoodIce{sx}{q}", p, h(rnd.uniform(0.010, 0.025)), h(rnd.uniform(0.0022, 0.0035)), w_torso(p), segs=4)

# ---------------------------------------------------------------- 臉：乾屍化（皮貼骨）、顴骨眼窩深陷、乾縮嘴唇微開露齒、閉眼覆薄冰（只有眼縫微光）
HC = J(0, -0.010, 0.828)
HR = (h(0.0305), h(0.0400), h(0.0460))
EYE_D = [Vector((sx * 0.40, -0.86, 0.17)).normalized() for sx in (-1, 1)]


def g_(d, e, sig):
    return math.exp(-((d - e).length / sig) ** 2)


def skull_dent(d, u=0, v=0):
    r = 1.0
    for sx in (-1, 1):
        r -= 0.25 * g_(d, Vector((sx * 0.40, -0.86, 0.17)).normalized(), 0.24)      # 眼窩
        r -= 0.30 * g_(d, Vector((sx * 0.70, -0.52, -0.42)).normalized(), 0.22)     # 凹頰（貼骨）
        r -= 0.13 * g_(d, Vector((sx * 0.92, -0.18, 0.28)).normalized(), 0.24)      # 太陽穴
        r += 0.13 * g_(d, Vector((sx * 0.64, -0.70, -0.08)).normalized(), 0.12)     # 顴骨（銳）
        r += 0.09 * g_(d, Vector((sx * 0.34, -0.86, 0.36)).normalized(), 0.12)      # 眉骨
        r += 0.04 * g_(d, Vector((sx * 0.30, -0.80, -0.78)).normalized(), 0.14)     # 下顎角
    if d.z < -0.12:
        r -= 0.24 * smooth((-d.z - 0.12) / 0.62) * (0.30 + 0.70 * abs(d.x))         # 下顎收窄
    r += 0.09 * g_(d, Vector((0, -0.95, -0.02)).normalized(), 0.09)                  # 鼻樑骨
    r += 0.06 * g_(d, Vector((0, -0.95, -0.18)).normalized(), 0.08)
    r -= 0.12 * g_(d, Vector((0, -0.92, -0.34)).normalized(), 0.09)                  # 鼻腔（鼻軟骨萎縮）
    r -= 0.05 * g_(d, Vector((0, -0.78, -0.60)).normalized(), 0.17)                  # 嘴唇乾縮
    r -= 0.10 * smooth((-d.z - 0.20) / 0.60) * max(0.0, -d.y)                       # 下半臉往後收
    r -= 0.14 * smooth((d.z - 0.40) / 0.50)                                          # 頭頂壓平（藏在兜帽裡、離冰冠環遠一點）
    return r


def skull_pt(d):
    d = d.normalized()
    r = skull_dent(d)
    return HC + V(d.x * HR[0], d.y * HR[1], d.z * HR[2]) * r


skull = B.ellipsoid("Skull", HC, (X, Y, Z), HR, 30, 20, "skin", "Head", dent=skull_dent, texel=3.4)
frost_attr(skull, lambda co: 0.30 * smooth((co.z - h(0.852)) / h(0.02)))
# 鼻孔：兩個小的深色凹洞（倒水滴形）
for sx in (-1, 1):
    np_ = skull_pt(V(sx * 0.06, -0.93, -0.36))
    B.ellipsoid(f"Nostril{sx}", np_ + V(0, h(0.0010), 0), (V(1, 0, 0.35 * sx).normalized(), Z, -Y), (h(0.0016), h(0.0036), h(0.0015)), 8, 4, "void",
                "Head", v0=0, v1=0.5)
# 嘴：乾縮唇線（皮）＋上下兩排牙微開，牙後一條細暗縫（不是圓洞）
mz = skull_pt(V(0, -0.82, -0.57))
for row, dz in ((0, h(0.0030)), (1, -h(0.0033))):
    for q in range(10):
        t = (q - 4.5) / 4.5
        d = V(t * 0.34, -0.88, -0.57 + (0.05 if row == 0 else -0.05)).normalized()
        p = skull_pt(d) + V(0, h(0.0012), 0)
        p.z = mz.z + dz
        nrm = V(t * 0.55, -1, 0).normalized()
        sz = h(0.0021) * (1.0 if abs(t) < 0.6 else 0.85) * rnd.uniform(0.85, 1.1)
        box(B, f"Tooth{row}_{q}", p, nrm.cross(Z).normalized(), Z, nrm, sz * 0.80, h(0.0030) * rnd.uniform(0.85, 1.1), sz * 0.65, "teeth", "Head",
            exp=3.0, segs=8)
slit = [skull_pt(V(t * 0.34, -0.88, -0.57)) + V(0, h(0.0030), 0) for t in (-1, -0.5, 0, 0.5, 1)]
for p in slit:
    p.z = mz.z
B.tube("MouthSlit", slit, [(h(0.0016), h(0.0010))] * 5, 6, "void", "Head", flat=Z)
for row, dz in ((0, h(0.0058)), (1, -h(0.0062))):
    lp = []
    for t in (-1.15, -0.6, 0, 0.6, 1.15):
        q = skull_pt(V(t * 0.36, -0.88, -0.57 + (0.09 if row == 0 else -0.09)))
        q.z = mz.z + dz * (1 - 0.25 * abs(t))
        lp.append(q)
    B.tube(f"Lip{row}", lp, [h(0.0008), h(0.0013), h(0.0014), h(0.0013), h(0.0008)], 6, "skin", "Head", texel=2.0)
# 閉眼：眼瞼（皮，填滿眼窩）＋貼著眼瞼的薄冰片＋眼縫一條微光（寬 ≤0.002H）
for k, e in enumerate(EYE_D):
    sx = -1 if k == 0 else 1
    p = skull_pt(e)
    ax_ = V(1, 0, 0.10 * sx).normalized()
    B.ellipsoid(f"Lid{sx}", p - e * h(0.0045), (ax_, Z, e), (h(0.0105), h(0.0068), h(0.0055)), 12, 4, "skin", "Head", v0=0, v1=0.5, texel=2.5)
    eice = B.ellipsoid(f"EyeIce{sx}", p + e * h(0.0002), (ax_, Z, e), (h(0.0080), h(0.0036), h(0.0008)), 12, 4, "ice", "Head", v0=0, v1=0.5)
    frost_attr(eice, lambda co: 0.08)
    B.tube(f"EyeSeam{sx}", [p + e * h(0.0013) + ax_ * h(0.0036) * t - Z * h(0.0007) * (1 - t * t) for t in (-1, -0.5, 0, 0.5, 1)],
           [h(0.0002), h(0.0005), h(0.0006), h(0.0005), h(0.0002)], 4, "Glow_Eye", "Head")

# ---------------------------------------------------------------- 冰冠：銀底環＋12 根放射扇形冰尖晶
CC = J(0, 0.012, 0.8675)
CRX, CRY = h(0.047), h(0.052)


def ring_pt(a, dz=0.0, off=0.0):
    ar = math.radians(a)
    return CC + V(math.sin(ar) * (CRX + off), -math.cos(ar) * (CRY + off), dz)


ring = B.tube("Circlet", [ring_pt(i * 15) for i in range(25)], [(h(0.0125), h(0.0042))] * 25, 6, "silver", "Head", flat=Z, exp=4.0, texel=2.0)
frost_attr(ring, lambda co: 0.6 * smooth((co.z - CC.z) / h(0.012)))
B.tube("CircletRune", [ring_pt(a, h(0.001), h(0.0045)) for a in range(-70, 71, 10)], [(h(0.0016), h(0.0009))] * 15, 4, "Glow_Rune", "Head", flat=Z)
CROWN = [(0, 1.000, 0.0115, 2), (-13, 0.965, 0.0095, 8), (13, 0.965, 0.0095, 8), (-27, 0.950, 0.0085, 16), (27, 0.950, 0.0085, 16),
         (-44, 0.944, 0.0080, 22), (44, 0.944, 0.0080, 22), (-63, 0.935, 0.0075, 30), (63, 0.935, 0.0075, 30),
         (180, 0.915, 0.0075, 12)]


def crystal(name, p, d, ln, r, w, mat="ice", segs=6, twist=None):
    d = d.normalized()
    ref = (d.cross(Z) if abs(d.z) < 0.98 else X).normalized()
    ref = (Quaternion(d, twist if twist is not None else rnd.uniform(0, 1)) @ ref)
    pts = [p - d * r * 1.2, p + d * ln * 0.16, p + d * ln * 0.66, p + d * ln]
    rr = [(r * 0.85, r * 0.75), (r, r * 0.86), (r * 0.74, r * 0.64), (h(0.0004), h(0.0004))]
    ob = B.tube(name, pts, rr, segs, mat, w, texel=1.4, sharp=20, flat=ref)
    L = ln
    frost_attr(ob, lambda co: clamp(1 - (co - p).dot(d) / (L * 0.28)) * 0.9)
    return ob


for q, (a, ztip, r0, lean) in enumerate(CROWN):
    p = ring_pt(a, h(0.010))
    ar = math.radians(a)
    out = V(math.sin(ar), -math.cos(ar), 0)
    d = (Z * math.cos(math.radians(lean)) + out * math.sin(math.radians(lean))).normalized()
    ln = (h(ztip) - p.z) / d.z
    crystal(f"Crown{q}", p, d, ln, h(r0), "Head")
    if q % 3 == 1:   # 根部的小碎晶（貼在環上，不算尖晶）
        crystal(f"CrownChip{q}", ring_pt(a + 7, h(0.006), h(0.002)), d + out * 0.6, h(0.016), h(0.004), "Head", segs=5)

# ---------------------------------------------------------------- 手臂（只露手腕）、乾枯骨感的手（指節突出、三節手指、指甲、指尖結霜）
farm = Surf(j["ForearmL"], fd, [(0, h(0.016), h(0.016), 0, 0), (body.fa_len * 0.6, h(0.0145), h(0.014), 0, 0),
                                 (body.fa_len, h(0.0128), h(0.0122), 0, 0)])
arms = [B.shell("Forearm", farm, body.fa_len * 0.35, body.fa_len + h(0.004), 0, 360, 10, 4, "skin", body.w_elbow(), off=0, texel=1.6)]
B.both(arms)


def bony_hand():
    R = body.RL
    Wr = j["HandL"]; a = body.hand_a; v = body.hand_v; u = body.hand_u
    obs = []
    K = body.knuckle
    pts = [Wr - a * 0.012 * R, Wr + a * 0.03 * R + u * 0.003 * R, K - a * 0.006 * R + u * 0.003 * R, K + a * 0.004 * R]
    obs.append(B.tube("HandBack", pts, [(0.030 * R, 0.019 * R), (0.040 * R, 0.019 * R), (0.044 * R, 0.017 * R), (0.040 * R, 0.013 * R)],
                      12, "skin", "HandL", exp=2.6, flat=v, texel=2.2))
    rc = body.grip_rc
    er = body.knuckle_dir
    et = (a - er * a.dot(er)).normalized()
    gc0 = K - er * rc
    fr = body.finger_r * 0.92
    for i, o in enumerate((-0.033, -0.011, 0.011, 0.031)):
        g = gc0 + v * o * R - a * (0.004 * R * abs(i - 1.3))
        ln = (1.0, 1.08, 1.0, 0.84)[i]
        fp = []
        for k in range(7):
            th = math.radians(238 * ln * k / 6)
            fp.append(g + (er * math.cos(th) + et * math.sin(th)) * rc)
        rad = [fr * 1.05, fr * 1.28, fr * 0.92, fr * 1.12, fr * 0.86, fr * 1.0, fr * 0.72]      # 指節突出
        f = B.tube(f"Finger{i}", fp, rad, 8, "skin", "HandL", texel=1.6)
        frost_attr(f, lambda co, tip=fp[-1]: clamp(1 - (co - tip).length / (fr * 4)))
        obs.append(f)
        nd = (fp[-1] - fp[-2]).normalized()
        nn = (fp[-1] - g).normalized()
        obs.append(B.ellipsoid(f"Nail{i}", fp[-1] - nd * fr * 0.9 + nn * fr * 0.55, (nd.cross(nn).normalized(), nd, nn), (fr * 0.62, fr * 0.85, fr * 0.22),
                               8, 4, "nail", "HandL", v0=0, v1=0.5))
        obs.append(B.ellipsoid(f"Knuckle{i}", fp[0] + er * fr * 0.55, (v, et, er), (fr * 0.9, fr * 0.9, fr * 0.6), 8, 4, "skin", "HandL", v0=0, v1=0.5))
        BD.tube(f"Tendon{i}", [Wr + u * 0.016 * R + v * o * R * 0.4, K + u * 0.010 * R + v * o * R - a * 0.012 * R], [0.0028 * R] * 2, 5, "skin", "HandL")
    g = gc0 + v * 0.058 * R
    tp = [Wr + a * 0.022 * R + v * 0.032 * R - u * 0.004 * R]
    for th in (150, 112, 75, 38):
        thr = math.radians(th)
        tp.append(g + (-er * math.cos(thr) + et * math.sin(thr)) * rc * 0.95 - v * 0.006 * R * (150 - th) / 110)
    obs.append(B.tube("Thumb", tp, [0.016 * R, 0.0150 * R, 0.0128 * R, 0.0138 * R, 0.0098 * R], 8, "skin", "HandL", texel=1.6))
    obs.append(B.ellipsoid("ThumbNail", tp[-1] + (tp[-1] - g).normalized() * 0.006 * R, (v, (tp[-1] - tp[-2]).normalized(), (tp[-1] - g).normalized()),
                           (0.0075 * R, 0.009 * R, 0.0025 * R), 8, 4, "nail", "HandL", v0=0, v1=0.5))
    return obs


B.mirror_only(bony_hand())
bony_hand()
BD.both([o for o in BD.parts if o.name.startswith("Tendon")])

# ---------------------------------------------------------------- 大袖：鐘形袖（從腋下撐開）＋下垂袖身與袖尾（兩節布料骨，從肘下到袖尾）
T_MAX = h(0.142)                                      # 袖尾長（動作時由布料骨下垂）
TAIL_D = (V(0, 0, -1) * 0.93 + V(0, 1, 0) * 0.30 + V(1, 0, 0) * 0.12).normalized()


def sleeve_pt(s, th, off=0.0):
    a = arm_dir(s)
    dn = V(0, 0, -1) - a * (-a.z)
    dn.normalize()
    sd = a.cross(dn)
    k = smooth(s / S_C)
    kc = smooth((s - S_C * 0.55) / (S_C * 0.45))
    R = sleeve_R(s) * (1 + 0.045 * math.sin(3 * th + 1.3) * k + 0.035 * math.sin(5 * th + 0.4) * kc) + off
    p = arm_axis(s) + dn * (R * math.cos(th)) + sd * (R * math.sin(th))
    p += V(0, 0, -1) * (h(0.024) * k ** 1.5 * max(0.0, math.cos(th)) ** 2)
    return p


def under_f(th):
    return smooth((math.cos(th) + 0.25) / 1.0)


def w_sleeve(s, th=math.pi):
    if s < h(0.03):
        t = smooth(s / h(0.03))
        base = {"ShoulderL": 0.35 * (1 - t), "UpperArmL": 0.65 + 0.35 * t}
    else:
        t = smooth((s - body.ua_len + h(0.035)) / h(0.07))
        base = {"UpperArmL": 1 - t, "ForearmL": t}
    tt = clamp((s - body.ua_len * 0.8) / (S_C - body.ua_len * 0.8))
    c = (0.38 + 0.47 * under_f(th)) * smooth(tt)         # 整圈袖身（下半 85%、上半約 40%）交給布料骨：手舉高時整片往下垂
    out = {k: w * (1 - c) for k, w in base.items()}
    if c > 1e-3:
        out["Sleeve1L"] = c
    return out


wm_sl = WMap()


def sleeve_fn(u, v):
    th = u * 2 * math.pi
    s = lerp(-h(0.012), S_C, v)
    return wm_sl.add(sleeve_pt(s, th), w_sleeve(s, th))


slv = soft(B.grid("Sleeve", 30, 13, sleeve_fn, "robe", wm_sl, [arm_axis(lerp(0, S_C, k / 6)) for k in range(7)], closed_u=True, rim=h(0.004),
                  texel=1.0, sharp=88))
wm_sll = WMap()


def lining_fn(u, v):
    th = u * 2 * math.pi
    s = lerp(S_C - h(0.07), S_C - h(0.004), v)
    return wm_sll.add(sleeve_pt(s, th, -h(0.004)), w_sleeve(s, th))


lining = B.grid("SleeveLining", 14, 3, lining_fn, "void", wm_sll, [arm_axis(S_C - h(0.03))], closed_u=True, texel=0.3)
wm_cf = WMap()


def cuff_fn(u, v):
    th = u * 2 * math.pi
    s = lerp(S_C - h(0.019), S_C - h(0.004), v)
    return wm_cf.add(sleeve_pt(s, th, h(0.0012)), w_sleeve(s, th))


cuff = soft(B.grid("SleeveCuff", 40, 2, cuff_fn, "band", wm_cf, [arm_axis(S_C - h(0.01))], closed_u=True, rim=h(0.0005), texel=1.4, sharp=88))
cuff_det = []
for q in range(2):
    cuff_det.append(BD.tube(f"CuffLine{q}", [sleeve_pt(S_C - h(0.0165 - 0.011 * q), i / 40 * 6.2832, h(0.0026)) for i in range(41)], [h(0.0008)] * 41, 4,
                            "gthread", "ForearmL"))
for i in range(18):
    th = i / 18 * 6.2832
    cuff_det.append(BD.ellipsoid(f"CuffDot{i}", sleeve_pt(S_C - h(0.011), th, h(0.0026)), (X, Y, Z), (h(0.0018),) * 3, 6, 4, "gthread", "ForearmL"))
BD.both(cuff_det)
# 布料骨：Sleeve1＝肘下（袖身下緣）→ 袖口下緣，Sleeve2＝袖口下緣 → 袖尾
P_ELB = sleeve_pt(body.ua_len, 0.0)
P_TAIL0 = sleeve_pt(S_C, 0.0)
SLV_PTS = [P_ELB, P_TAIL0, P_TAIL0 + TAIL_D * T_MAX]
NT_U = 32
tail_cut = []
for k in range(4):
    tail_cut += [rnd.uniform(0.0, 0.14)] * 8
tail_notch = {8: 0.35, 16: 0.5, 24: 0.30}


def tail_len(i):
    th = -110 + 220 * i / NT_U
    base = smooth(1 - abs(th) / 112) ** 0.55
    L = base * (1 - tail_cut[min(i, NT_U - 1)])
    if i in tail_notch:
        L *= 1 - tail_notch[i]
    return T_MAX * L


def w_tail(x, th=0.0):
    fa = (1 - (0.38 + 0.47 * under_f(th))) * (1 - smooth(x / (0.4 * T_MAX)))
    a2 = smooth((x - 0.10 * T_MAX) / (0.6 * T_MAX))
    return {"ForearmL": fa, "Sleeve1L": (1 - fa) * (1 - a2), "Sleeve2L": (1 - fa) * a2}


wm_tl = WMap()
AX_C = arm_axis(S_C)


def tail_fn(u, v):
    i = int(round(u * NT_U))
    th = math.radians(-110 + 220 * u)
    p0 = sleeve_pt(S_C, th)
    x = tail_len(i) * v
    a = arm_dir(S_C)
    rd = (p0 - AX_C).normalized()
    p = p0 + TAIL_D * x + a * (h(0.012) * math.sin(math.pi * v) * (0.5 + 0.5 * math.cos(th))) + (p0 - P_TAIL0) * (0.25 * v)
    p += rd * (h(0.013) * math.sin(3.5 * th + 1.1) + h(0.004) * math.sin(7 * th + 2.0 + 2 * v)) * smooth(v * 1.6)   # 縱向皺褶 3–4 條
    return wm_tl.add(p, w_tail(x, th))


stail = soft(B.grid("SleeveTail", NT_U, 10, tail_fn, "robe", wm_tl, [P_TAIL0 + TAIL_D * T_MAX * 0.5 - arm_dir(S_C) * h(0.2)], rim=h(0.005),
                    texel=1.0, sharp=80))
tail_ice = []
for i in sorted(rnd.sample(range(2, NT_U - 1), 7)):
    th = math.radians(-110 + 220 * i / NT_U)
    x = tail_len(i)
    rd = (sleeve_pt(S_C, th) - AX_C).normalized()
    p = sleeve_pt(S_C, th) + TAIL_D * x + (sleeve_pt(S_C, th) - P_TAIL0) * 0.25 + rd * (h(0.013) * math.sin(3.5 * th + 1.1) + h(0.004) * math.sin(7 * th + 4.0)) - V(0, 0, h(0.004))
    tail_ice += cluster(f"SlvIce{i}", p + V(0, 0, h(0.006)), rnd.choice((1, 2, 3)), h(0.02), h(0.06), h(0.0022), h(0.005), w_tail(x * 0.98, th))
B.both([slv, lining, cuff, stail] + tail_ice)

# ---------------------------------------------------------------- 腿與軟靴（只露靴尖）
shin = Surf(j["ShinL"], (j["FootL"] - j["ShinL"]), [(0, h(0.024), h(0.025), 0, 0), (body.sh_len * 0.5, h(0.021), h(0.023), 0, 0),
                                                       (body.sh_len, h(0.016), h(0.018), 0, 0)])
B.both([B.shell("Shin", shin, -h(0.02), body.sh_len, 0, 360, 10, 4, "boot", body.w_knee(), off=0, texel=0.8)])
_b, _u = body.B, body.U
body.B = 0.12
boot = sabaton(B, body, "boot", pointed=1.05, lames=False, name="Boot")
body.B = _b
B.both(boot)

# ---------------------------------------------------------------- 長槍 1.05H（銀柄、細環、銀銎座、冰質葉形槍頭、側倒鉤、垂冰柱）
gcR = Body.mir(body.grip_c); ax = Body.mir(body.hand_v); edge = Body.mir(body.hand_a)
edge = (edge - ax * edge.dot(ax)).normalized()
side = ax.cross(edge)
BUTT, TIPS = -h(0.64), h(0.41)
SOCK0, SOCK1 = TIPS - h(0.18) - h(0.05), TIPS - h(0.18)


def hp(s, e=0.0, sd=0.0):
    return gcR + ax * s + edge * e + side * sd


shaft = B.tube("Shaft", [hp(BUTT + h(0.045)), hp(-h(0.3)), hp(0), hp(h(0.1)), hp(SOCK0 + h(0.005))], [SHAFT_R] * 5, 8, "silver", "Weapon", texel=0.9)
frost_attr(shaft, lambda co: 0.0)
for q, s0 in enumerate([BUTT + h(0.06) + h(0.15) * i for i in range(6)]):
    if s0 > SOCK0 - h(0.02):
        break
    B.tube(f"ShaftRing{q}", [hp(s0 - h(0.004)), hp(s0), hp(s0 + h(0.004))], [SHAFT_R * 1.15, SHAFT_R * 1.32, SHAFT_R * 1.15], 8, "silver", "Weapon")
    for k in range(3):
        BD.tube(f"RingEngr{q}{k}", [hp(s0 + h(0.008) + h(0.003) * k) + (edge * math.cos(t) + side * math.sin(t)) * (SHAFT_R + h(0.0003)) for t in
                                     [i / 12 * 6.2832 for i in range(13)]], [h(0.0005)] * 13, 4, "stitch", "Weapon")
B.tube("ButtSpike", [hp(BUTT), hp(BUTT + h(0.02)), hp(BUTT + h(0.045)), hp(BUTT + h(0.05))], [h(0.0005), SHAFT_R * 1.1, SHAFT_R * 1.35, SHAFT_R * 1.2],
       6, "silver", "Weapon", sharp=25)
B.tube("Socket", [hp(SOCK0 - h(0.004)), hp(SOCK0 + h(0.006)), hp(SOCK1 - h(0.012)), hp(SOCK1 + h(0.004))],
       [SHAFT_R * 1.25, SHAFT_R * 1.55, SHAFT_R * 1.45, SHAFT_R * 1.9], 8, "silver", "Weapon", texel=1.4)
for k in range(4):
    sk = lerp(SOCK0 + h(0.012), SOCK1 - h(0.012), k / 3)
    B.tube(f"SocketBand{k}", [hp(sk - h(0.002)), hp(sk + h(0.002))], [SHAFT_R * 1.7] * 2, 8, "silver", "Weapon")
bl = [(0.0, 0.006, 0.0040), (0.10, 0.0165, 0.0045), (0.30, 0.0175, 0.0045), (0.55, 0.0145, 0.0040), (0.80, 0.0085, 0.0030), (1.0, 0.0004, 0.0004)]
blade = B.tube("IceBlade", [hp(SOCK1 + h(0.18) * t) for t, _, _ in bl], [(h(wd), h(th)) for _, wd, th in bl], 4, "ice", "Weapon", flat=edge, sharp=15, texel=1.6)
frost_attr(blade, lambda co: 0.9 * smooth(1 - (co - hp(SOCK1)).dot(ax) / h(0.03)))
for sg in (1, -1):
    B.tube(f"BladeRune{sg}", [hp(SOCK1 + h(0.015), 0, sg * h(0.0042)), hp(SOCK1 + h(0.07), 0, sg * h(0.0046)), hp(SOCK1 + h(0.13), 0, sg * h(0.0036))],
           [(h(0.0014), h(0.0006))] * 3, 4, "Glow_Weapon", "Weapon", flat=edge)
    crystal(f"Barb{sg}", hp(SOCK1 + h(0.006), sg * h(0.006)), edge * sg * 1.0 - ax * 0.55, h(0.034), h(0.0045), "Weapon", segs=4)
    crystal(f"Barb2{sg}", hp(SOCK1 + h(0.02), sg * h(0.012)), edge * sg * 1.0 - ax * 0.25, h(0.018), h(0.0030), "Weapon", segs=4)
for q in range(5):
    t = 0.05 + q * 0.13
    wd = h(0.0165) * (1 - t * 0.8)
    icicle(f"BladeIce{q}", hp(SOCK1 + h(0.18) * t, -wd * 0.8), h(rnd.uniform(0.01, 0.03)), h(0.0022), "Weapon", d=-edge * 0.8 - ax * 0.4, segs=4)
TIPP = hp(TIPS)

# ---------------------------------------------------------------- 一階經書 X2_HipBook（掛右胯書鏈上；二階起由遊戲隱藏，浮書出現）
bc0 = cl - Z * h(0.062)
a_b = math.degrees(math.atan2(bc0.x, -bc0.y))
rp = ell(RT, bc0.z, a_b, h(0.006) + fold(a_b, bc0.z))
bn = V(rp.x, rp.y, 0).normalized()
BOOK_C = rp + bn * h(0.019)
BOOK_C.z = bc0.z
bx_ = Z.cross(bn).normalized()
hipbook = []
hipbook.append(box(B, "HBCover", BOOK_C, bx_, Z, bn, h(0.0375), h(0.055), h(0.0150), "bookleather", "Hips", exp=7, texel=2.0))
hipbook.append(box(B, "HBPages", BOOK_C + bx_ * h(0.003), bx_, Z, bn, h(0.0350), h(0.0515), h(0.0125), "paper", "Hips", exp=9, texel=1.5))
for sx in (-1, 1):
    for sz in (-1, 1):
        c_ = BOOK_C + bx_ * h(0.0345) * sx + Z * h(0.052) * sz
        for sdn in (-1, 1):
            hipbook.append(box(B, f"HBCorner{sx}{sz}{sdn}", c_ + bn * h(0.0150) * sdn, bx_, Z, bn, h(0.0075), h(0.0075), h(0.0012), "gold", "Hips",
                               exp=3, segs=8))
for k in (-1, 1):
    zc_ = BOOK_C.z + h(0.026) * k
    pts = [BOOK_C + bx_ * h(0.020) + Z * (zc_ - BOOK_C.z) + bn * h(0.0158), BOOK_C + bx_ * h(0.0395) + Z * (zc_ - BOOK_C.z) + bn * h(0.010),
           BOOK_C + bx_ * h(0.0395) + Z * (zc_ - BOOK_C.z) - bn * h(0.010), BOOK_C + bx_ * h(0.020) + Z * (zc_ - BOOK_C.z) - bn * h(0.0158)]
    hipbook.append(B.tube(f"HBStrap{k}", pts, [(h(0.0045), h(0.0010))] * 4, 4, "gold", "Hips", flat=Z, exp=4))
    hipbook.append(box(B, f"HBClasp{k}", BOOK_C + bx_ * h(0.020) + Z * (zc_ - BOOK_C.z) + bn * h(0.0165), bx_, Z, bn, h(0.004), h(0.0055), h(0.0015),
                       "gold", "Hips", exp=4, segs=8))
for i in range(10):       # 封面原創浮雕（只烘到貼圖）
    t = i / 9
    pts = [BOOK_C + bn * h(0.0155) + bx_ * h(0.024) * math.cos(th) * (0.4 + 0.6 * t) + Z * h(0.036) * math.sin(th) * (0.4 + 0.6 * t)
           for th in [k_ / 10 * 6.2832 + t * 2 for k_ in range(11)]]
    if i in (0, 4, 9):
        BD.tube(f"HipBookEmb{i}", pts, [h(0.0011)] * 11, 4, "gold", "Hips")
BD.ellipsoid("HipBookEmbC", BOOK_C + bn * h(0.0155), (bx_, Z, bn), (h(0.008), h(0.012), h(0.002)), 10, 4, "gold", "Hips")
VL.tag_p2(hipbook, "HipBookX", "Hips", BOOK_C)

# ---------------------------------------------------------------- 二階部件
# P2_CrownHalo：頭後開口朝下的冰荊棘環（約 240°），7 段粗 S 形荊棘（不規則多稜截面、冰裂、霜），外徑約 0.62H
HALO_C = J(0, 0.065, 0.905)
HAX, HAZ = X, Z
R_HALO = h(0.272)
halo = []
NSEG = 7
span = 240.0
gap = 7.0
segw = (span - gap * (NSEG - 1)) / NSEG
for q in range(NSEG):
    a0 = -span / 2 + q * (segw + gap)
    pts = []; rr = []
    n = 11
    sgn = 1 if q % 2 else -1
    for i in range(n):
        t = i / (n - 1)
        a = math.radians(a0 + segw * t)
        rad = R_HALO + h(0.024) * math.sin(2 * math.pi * t) * sgn
        pts.append(HALO_C + HAX * (math.sin(a) * rad) + HAZ * (math.cos(a) * rad) + Y * h(0.014) * math.sin(math.pi * t * 2 + q))
        w0 = h(0.0145) * (0.55 + 0.45 * math.sin(math.pi * clamp(t * 1.05)) ** 0.4) * rnd.uniform(0.85, 1.15)
        rr.append((w0, w0 * rnd.uniform(0.8, 1.0)))
    rr[0] = (h(0.004), h(0.004)); rr[-1] = (h(0.0012), h(0.0012))
    seg = B.tube(f"HaloSeg{q}", pts, rr, 7, "ice", "HaloSpin", texel=1.2, sharp=28, flat=Y)
    frost_attr(seg, lambda co: 0.12)
    halo.append(seg)
    gl = [p + (p - HALO_C).normalized() * h(0.0115) - Y * h(0.003) for p in pts[2:-2]]
    halo.append(B.tube(f"HaloGlow{q}", gl, [h(0.0030)] * len(gl), 5, "P2_Glow_Halo", "HaloSpin"))
    for t_i in range(rnd.choice((4, 5, 6))):
        i = 1 + int((n - 3) * (t_i + 0.5) / 6)
        p = pts[i]
        o = (p - HALO_C).normalized()
        tg = (pts[i + 1] - pts[i - 1]).normalized()
        d = (o * rnd.choice((1.0, 1.0, 0.8, -0.6)) + tg * rnd.uniform(-0.7, 0.7) + Y * rnd.uniform(-0.35, 0.35)).normalized()
        halo.append(crystal(f"HaloThorn{q}_{t_i}", p + d * rr[i][0] * 0.4, d, h(rnd.uniform(0.022, 0.042)), h(rnd.uniform(0.005, 0.0075)), "HaloSpin", segs=5))
for q in range(34):
    a = math.radians(rnd.uniform(-150, 150))
    rad = R_HALO * rnd.uniform(1.10, 1.25) if q % 3 else R_HALO * rnd.uniform(0.72, 0.85)
    p = HALO_C + HAX * (math.sin(a) * rad) + HAZ * (math.cos(a) * rad) + Y * h(rnd.uniform(-0.03, 0.03))
    halo.append(crystal(f"HaloShard{q}", p, V(rnd.uniform(-1, 1), rnd.uniform(-0.4, 0.4), rnd.uniform(-1, 1)), h(rnd.uniform(0.008, 0.02)),
                        h(rnd.uniform(0.0025, 0.0045)), "HaloSpin", segs=4))
VL.tag_p2(halo, "CrownHalo", "HaloSpin", HALO_C)
# P2_CrownGrow：冰冠變成 16 根，最高 0.20H
cg = []
for q, (a, ztip, r0, lean) in enumerate([(0, 1.075, 0.013, 0), (-9, 1.035, 0.011, 6), (9, 1.035, 0.011, 6), (-21, 1.02, 0.0105, 14),
                                         (21, 1.02, 0.0105, 14), (-35, 1.005, 0.010, 22), (35, 1.005, 0.010, 22), (-52, 0.99, 0.0095, 32),
                                         (52, 0.99, 0.0095, 32), (-72, 0.97, 0.009, 42), (72, 0.97, 0.009, 42), (-100, 0.95, 0.008, 45),
                                         (100, 0.95, 0.008, 45), (160, 0.965, 0.009, 15), (-160, 0.965, 0.009, 15), (130, 0.95, 0.008, 28)]):
    ar = math.radians(a)
    p = ring_pt(a, h(0.008), -h(0.002))
    out = V(math.sin(ar), -math.cos(ar), 0)
    d = (Z * math.cos(math.radians(lean)) + out * math.sin(math.radians(lean))).normalized()
    cg.append(crystal(f"CrownBig{q}", p, d, (h(ztip) - p.z) / d.z, h(r0), "Head"))
VL.tag_p2(cg, "CrownGrow", "Head", CC)
# P2_FloatingBook：左手上方（+X 0.22H、0.78H），往外傾約 30°，翻開。暗青綠皮封面（厚 0.008H）＋金包角＋書頁堆疊＋翻起的單頁；
# 只有書頁表面發光，分兩層（中心亮、邊緣暗）
FB = J(0.22, -0.06, 0.78)
fbn = (V(0.5, -0.55, 0.85)).normalized()
fbx = (V(0.85, 0.45, 0.0) - fbn * V(0.85, 0.45, 0.0).dot(fbn)).normalized()
fby = fbn.cross(fbx).normalized()
book = []
for sg in (1, -1):
    tilt = (fbx * sg * 0.22 + fbn).normalized()
    hx = (fbx - tilt * fbx.dot(tilt)).normalized()
    pc = FB + hx * h(0.0335) * sg
    book.append(box(B, f"FBCover{sg}", pc - tilt * h(0.004), hx, fby, tilt, h(0.0345), h(0.047), h(0.0040), "bookcov", "Spine2", exp=7, texel=1.5))
    book.append(box(B, f"FBStack{sg}", pc + tilt * h(0.0035), hx, fby, tilt, h(0.0315), h(0.0435), h(0.0040), "paper", "Spine2", exp=9, texel=1.2))
    book.append(box(B, f"FBGlowEdge{sg}", pc + tilt * h(0.0078), hx, fby, tilt, h(0.0270), h(0.0390), h(0.0004), "P2_Glow_BookDim", "Spine2", exp=6, segs=12))
    book.append(box(B, f"FBGlowCore{sg}", pc + tilt * h(0.0084) - hx * sg * h(0.002), hx, fby, tilt, h(0.0180), h(0.0280), h(0.0004), "P2_Glow_Book",
                    "Spine2", exp=4, segs=12))
    for sz in (-1, 1):
        c_ = pc + hx * h(0.031) * sg + fby * h(0.043) * sz
        book.append(box(B, f"FBCorner{sg}{sz}", c_ - tilt * h(0.004), hx, fby, tilt, h(0.0075), h(0.0075), h(0.0048), "gold", "Spine2", exp=3, segs=8))
for q in range(3):     # 往上翻起的單頁
    sg = 1 if q != 1 else -1
    tilt = (fbx * sg * 0.22 + fbn).normalized()
    hx = (fbx - tilt * fbx.dot(tilt)).normalized()
    pa = FB + tilt * h(0.009)
    lift = (0.55, 0.85, 0.35)[q]
    pts = [pa + hx * sg * h(0.0205) * i * (1 - 0.25 * lift * i / 3) + tilt * h(0.022) * lift * math.sin(i / 3 * 1.9) for i in range(4)]
    book.append(B.tube(f"FBLeaf{q}", pts, [(h(0.0420), h(0.0007))] * 4, 4, "paper", "Spine2", flat=fby, exp=7))
book.append(B.tube("FBSpine", [FB - fby * h(0.048), FB + fby * h(0.048)], [h(0.0065)] * 2, 8, "bookcov", "Spine2"))
for q in range(8):
    p = FB + fbn * h(0.02 + q * 0.012) + fbx * h(rnd.uniform(-0.05, 0.05)) + fby * h(rnd.uniform(-0.04, 0.04))
    book.append(crystal(f"FBMote{q}", p, V(rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1), h(0.010), h(0.0018), "Spine2", mat="P2_Glow_BookDim", segs=4))
VL.tag_p2(book, "FloatingBook", "Spine2", FB)
# P2_IceShards：長在袍面（0.12–0.45H）的冰晶裙，成簇、交錯；側面最外圈加長，總外展約 0.85H
shards = []
NCL = 15
for c in range(NCL):
    u0 = (c + rnd.uniform(0.15, 0.85)) / NCL
    zc = rnd.uniform(0.14, 0.40)
    for q in range(rnd.choice((3, 4, 4, 5))):
        u = clamp(u0 + rnd.uniform(-0.022, 0.022), 0.01, 0.99)
        z = h(clamp(zc + rnd.uniform(-0.05, 0.05), 0.12, 0.45))
        p, a = robe_pt(u, z)
        outv = (p - V(0, 0, p.z)).normalized()
        sidef = abs(math.sin(math.radians(a)))
        el = -math.radians(rnd.uniform(30, 60) if rnd.random() < 0.75 else rnd.uniform(5, 25))
        d = (outv * math.cos(el) + Z * math.sin(el) + outv.cross(Z) * rnd.uniform(-0.3, 0.3)).normalized()
        ln = h(rnd.uniform(0.07, 0.17) + 0.20 * sidef ** 2 * rnd.uniform(0.6, 1.0) * (1.0 if q < 2 else 0.5))
        for _ in range(30):        # 冰刺尖端至少離地 0.08H（IdleAggro 骨盆下沉時也不插地）
            if (p + d * ln).z >= h(0.095):
                break
            el *= 0.85
            d = (outv * math.cos(el) + Z * math.sin(el) + outv.cross(Z) * rnd.uniform(-0.3, 0.3)).normalized()
            if el > -0.02:
                ln *= 0.92
        shards.append(crystal(f"Shard{c}_{q}", p - d * h(0.012), d, ln, h(rnd.uniform(0.010, 0.020)), "Hips"))
VL.tag_p2(shards, "IceShards", "Hips", V(0, 0, h(0.30)))
# P2_Glow_Veins：臉頰、額頭細藍裂紋；手背
veins = []
for sx in (-1, 1):
    for k, (d0, d1, d2) in enumerate([((0.55, -0.80, -0.20), (0.62, -0.72, -0.40), (0.50, -0.80, -0.60)),
                                      ((0.30, -0.90, 0.30), (0.20, -0.90, 0.55), (0.05, -0.88, 0.70)),
                                      ((0.72, -0.60, 0.05), (0.80, -0.50, -0.25), (0.78, -0.50, -0.45))]):
        pts = [skull_pt(V(sx * a, b, c)) + (skull_pt(V(sx * a, b, c)) - HC).normalized() * h(0.0012) for a, b, c in (d0, d1, d2)]
        mid = [pts[0].lerp(pts[1], 0.5) + V(0, 0, h(0.002)), pts[1].lerp(pts[2], 0.5) - V(0, 0, h(0.002))]
        veins.append(B.tube(f"VeinFace{sx}{k}", [pts[0], mid[0], pts[1], mid[1], pts[2]], [h(0.0010)] * 4 + [h(0.0004)], 4, "P2_Glow_Veins", "Head"))
VL.tag_p2(veins, "VeinsFace", "Head", HC)
hv = []
Wh = j["HandL"]; a_ = body.hand_a; u_ = body.hand_u; v_ = body.hand_v
for q in range(3):
    pts = [Wh - a_ * h(0.012) + u_ * h(0.016) + v_ * (q - 1) * h(0.003) + a_ * h(0.011) * i + v_ * (q - 1) * h(0.004) * i for i in range(4)]
    hv.append(B.tube(f"VeinHand{q}", pts, [h(0.0011)] * 3 + [h(0.0004)], 4, "P2_Glow_Veins", "HandL"))
VL.tag_p2(hv, "VeinsHandL", "HandL", Wh)
hvR = [B.mirror(o) for o in hv]
for o in hvR:
    o.vertex_groups.clear()
    o.vertex_groups.new(name="HandR").add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
VL.tag_p2(hvR, "VeinsHandR", "HandR", Body.mir(Wh))

# ---------------------------------------------------------------- 骨架、烘焙
tipd = ax.normalized()
ext = []
for sd in "LR":
    pts = SLV_PTS if sd == "L" else [Body.mir(p) for p in SLV_PTS]
    ext += [(f"Sleeve1{sd}", f"Forearm{sd}", pts[0], pts[1]), (f"Sleeve2{sd}", f"Sleeve1{sd}", pts[1], pts[2])]
for k in range(HEM_N):
    pts = hem_chain_pts(k)
    ext += [(f"Hem{k}A", "Hips", pts[0], pts[1]), (f"Hem{k}B", f"Hem{k}A", pts[1], pts[2])]
arm = build_armature("BossPriest", body, weapon=(gcR, gcR + ax * 0.30 * U),
                     extra=[("Tip_Weapon", "Weapon", TIPP, TIPP + tipd * h(0.04)), ("HaloSpin", "Head", HALO_C, HALO_C - Y * h(0.06))] + ext)
def reunwrap(ob, texel=1.0):
    import bmesh as _bm
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.seams_from_islands()
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = _bm.new(); bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.active
    a3 = sum(f.calc_area() for f in bm.faces)
    auv = 0.0
    for f in bm.faces:
        pts = [l[uv].uv for l in f.loops]
        auv += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) * 0.5
    k = math.sqrt(a3 / max(auv, 1e-9)) * texel
    B.uv_slot = getattr(B, "uv_slot", 0) + 1
    du = B.uv_slot * 20.0
    for f in bm.faces:
        for l in f.loops:
            q = l[uv].uv * k
            l[uv].uv = (q.x + du, q.y)
    bm.to_mesh(ob.data); bm.free()


for o in list(B.parts):
    if o.name.split("_")[0] in ("Robe", "InnerRobe", "Capelet", "Hood", "Sleeve", "SleeveTail", "Scarf"):
        reunwrap(o, {"Hood": 1.4, "Capelet": 1.2, "InnerRobe": 0.9}.get(o.name.split("_")[0], 1.0))
print("REUNWRAP done", flush=True)
glows = VL.pull_glow(B)
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts) + VL.tri_count(glows)
print("PARTS", len(B.parts), "TRIS", tri, "DETAIL", len(BD.parts), flush=True)
DETAIL_OF = {"silver": "metal", "gold": "metal", "leather": "leather", "boot": "leather", "bookcov": "leather", "bookleather": "leather",
             "robe": "cloth", "robe_in": "cloth", "cape": "cloth", "hood": "cloth", "scarf": "cloth", "band": "cloth",
             "skin": "skin", "ice": "ice"}.get
TEXS = {"A": 2048, "B": 2048, "C": 1024}
details = {"A": [], "B": []}
for o in BD.parts:
    # 刺繡金線烘到所在布料的圖集（A）；臉、手、槍、腰帶、經書的細節烘到 B
    tgt = "A" if o.name.startswith(("Band", "Inner", "Cape", "Cuff")) else "B"
    details[tgt].append(o)
mesh = BK.assemble(B, MODEL, TEXS, bake=not (QUICK or NOBAKE), quick=QUICK, detail_of=DETAIL_OF, U=1.0, details=details, tex_dir=TEXDIR)
VL.join_into(mesh, glows)
p2objs = VL.split_p2(mesh, arm)
for o in list(p2objs):              # 一階經書：X2_*（二階起隱藏），不是 P2 部件
    if o.name == "P2_HipBookX":
        o.name = "X2_HipBook"; o.data.name = "X2_HipBook"
        if "p2form" in o:
            del o["p2form"]
# glTF 每個頂點最多 4 個骨頭權重：先在 Blender 裡限制成 4 並正規化，地面約束與預覽才會和匯出的 GLB 一致
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
BK.bind(mesh, arm)
print("TRIS_FINAL", BK.tri_count(mesh) + VL.tri_count(p2objs), "main", BK.tri_count(mesh), "p2+x2", VL.tri_count(p2objs), flush=True)

# ---------------------------------------------------------------- 動作
import soul_humanoid_anim as SA
# 地面檢查：寬袍＋長槍，骨盆／脊椎的接觸半徑要比盔甲角色大（倒地、跪地時袍身不插地）
SA.GROUND_BODY = [("Hips", 0.30), ("Spine", 0.24), ("Spine2", 0.20), ("Neck", 0.09), ("HeadC", 0.12),
                  ("UpperArmL", 0.12), ("UpperArmR", 0.12), ("ForearmL", 0.17), ("ForearmR", 0.17),
                  ("HandL", 0.17), ("HandR", 0.17), ("ShinL", 0.07), ("ShinR", 0.07)]       # 大袖：前臂處袖口半徑 0.066H
chains = []
for sd, sx in (("L", 1), ("R", -1)):
    pts = SLV_PTS if sd == "L" else [Body.mir(p) for p in SLV_PTS]
    chains.append(dict(names=[f"Sleeve1{sd}", f"Sleeve2{sd}"], anchor=f"Forearm{sd}", pts=pts, stiff=0.03, damp=0.88, grav=9.8, planar=False,
                       colliders=[("Root", "Hips", h(0.17)), ("Hips", "Spine2", h(0.10))]))
LEGC = [("ThighL", "ShinL", h(0.055)), ("ShinL", "FootL", h(0.050)), ("ThighR", "ShinR", h(0.055)), ("ShinR", "FootR", h(0.050))]
for k in range(HEM_N):
    chains.append(dict(names=[f"Hem{k}A", f"Hem{k}B"], anchor="Hips", pts=hem_chain_pts(k), stiff=0.30, damp=0.85, grav=9.8, planar=False,
                       colliders=LEGC, floor=h(0.02)))
rig = Rig(arm, body, chains=chains)
rig.tip_len = TIPS
rig.spear = (BUTT, TIPS)
rig.lie_dz = 0.10
import json as _json
_json.dump(dict(HH=HH, U=U, TIPS=TIPS, BUTT=BUTT), open(os.path.join(TMP, "dims.json"), "w"))

if not NOANIM:
    import v3_priest_anim
    v3_priest_anim.run(rig, ONLY)

if not ONLY:
    # 不用 v2a_lib.export_glb：它開了 export_optimize_animation_size，會把地面約束只改了幾格的布料骨關鍵格當成多餘而刪掉
    for o in bpy.data.objects:
        o.select_set(False)
    arm.select_set(True)
    for o in [mesh] + p2objs:
        o.hide_render = False; o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.scene.frame_set(0)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True, export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_yup=True, export_skins=True, export_image_format="JPEG",
                              export_image_quality=88, export_force_sampling=True, export_optimize_animation_size=False,
                              export_tangents=False, export_def_bones=False)
    print(f"EXPORT {OUT_GLB} {os.path.getsize(OUT_GLB) / 1048576:.2f} MB", flush=True)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("DONE", MODEL, flush=True)
