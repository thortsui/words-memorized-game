"""回合制模式的可愛蝙蝠（橘色書頁蝙蝠／暗影蝙蝠，原創造型）。
用法：blender --background --factory-startup --python build_cute_bat.py -- <orange|shadow> [out.glb] [out.blend] [preview_dir] [strip_dir] [只渲染的動作,逗號分隔]
造型依據：art/reference/cute_monster_lineup.jpg
朝向：臉朝 -Y（匯出 glTF 後為 +Z），原點在地面，身體飄在離地約 0.9 m。
動作：Idle、Enter、Attack、Hit、Faint、Victory（各自一條靜音的 NLA track）。兩個變體共用同一套骨架與動作。
"""
import sys, os, math, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cute_common import *  # noqa

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
VARIANT = argv[0] if argv else "orange"
NAME = f"bat_{VARIANT}"
PROJ = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT_GLB = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(PROJ, "public", "models", NAME + ".glb")
OUT_BLEND = os.path.abspath(argv[2]) if len(argv) > 2 else os.path.join(HERE, "source", NAME + ".blend")
PREVIEW_DIR = os.path.abspath(argv[3]) if len(argv) > 3 else os.path.join(HERE, "preview")
STRIP_DIR = os.path.abspath(argv[4]) if len(argv) > 4 and argv[4] != "-" else None
ONLY = argv[5].split(",") if len(argv) > 5 else None
SHADOW = VARIANT == "shadow"

scene = reset_scene()
random.seed(11)

# ───────────────────────── 材質 ─────────────────────────
if SHADOW:
    M_FUR = mat("Fur", "#4A3478", rough=0.55, glow=0.16)
    M_FUR_D = mat("FurDark", "#33235A", rough=0.6, glow=0.14)
    M_BELLY = mat("Belly", "#5E4696", rough=0.55, glow=0.16)
    M_EAR_IN = mat("EarInner", "#7A5BB8", rough=0.6, glow=0.14)
    M_WING = mat("WingMembrane", "#3A2A66", rough=0.6, glow=0.16)
    M_WING_ARM = mat("WingArm", "#2A1D4C", rough=0.5, glow=0.12)
    M_EYE = mat("EyeGlow", "#FFD21F", rough=0.3, emit="#FFC400", emit_strength=2.2)
else:
    M_FUR = mat("Fur", "#F68A1E", rough=0.42, glow=0.14)
    M_FUR_D = mat("FurDark", "#DB6A12", rough=0.5, glow=0.12)
    M_BELLY = mat("Belly", "#FDBE6A", rough=0.5, glow=0.14)
    M_EAR_IN = mat("EarInner", "#FBDDB0", rough=0.6, glow=0.14)
    M_WING = mat("WingPage", "#F8EACB", rough=0.7, glow=0.16)
    M_WING_ARM = mat("WingArm", "#E57818", rough=0.45, glow=0.12)
    M_INK = mat("PageInk", "#B88A58", rough=0.8, glow=0.10)
    M_GLASS = mat("GlassFrame", "#1B1A22", rough=0.25, glow=0.0)
    M_LENS = mat("GlassLens", "#EAF6FF", rough=0.05, glow=0.3, alpha=0.22)
M_WHITE = mat("EyeWhite", "#FFFFFF", rough=0.25, glow=0.25)
M_PUPIL = mat("Pupil", "#1A1210", rough=0.15, glow=0.0)
M_SHINE = mat("Shine", "#FFFFFF", rough=0.05, emit="#FFFFFF", emit_strength=0.9)
M_MOUTH = mat("Mouth", "#6A1E22" if not SHADOW else "#1A0F2E", rough=0.6, glow=0.05)
M_FANG = mat("Fang", "#FFFDF2", rough=0.3, glow=0.25)
M_BLUSH = mat("Blush", "#FF6F7D" if not SHADOW else "#B05CFF", rough=0.8, glow=0.1, alpha=0.5)

# ───────────────────────── 身體 ─────────────────────────
BC = Vector((0, 0, 0.90))
BR = (0.265, 0.238, 0.275) if not SHADOW else (0.250, 0.226, 0.250)
BOT, TOP = BC.z - BR[2], BC.z + BR[2]


def body_warp(p):
    """梨形：下半身胖一點、頭頂收一點。"""
    k = 1 + 0.10 * max(-1.0, min(1.0, -p.z / BR[2])) - 0.05 * sstep(0.4, 1.0, p.z / BR[2])
    return Vector((p.x * k, p.y * k, p.z))


BODY = Ellip(BC, BR, body_warp)


def bw(co):
    """身體下半跟 Body、上半（臉）跟 Head，中間平滑過渡。"""
    w = sstep(0.12, 0.42, (co.z - BOT) / (TOP - BOT))
    return {"Body": 1 - w, "Head": w}


body = ellipsoid("Body", BC, BR, M_FUR, segs=32, rings=20)
for v in body.data.vertices:
    v.co = BC + body_warp(v.co - BC)
skin_fn(body, bw)


def belly_pt(u, v):
    a = 2 * math.pi * u
    return BODY.pt(math.cos(a) * 36 * v, -40 + math.sin(a) * 27 * v, 0.006 * (1 - v ** 4))


skin_fn(surface("Belly", belly_pt, 20, 5, M_BELLY), bw)

for s in (-1, 1):
    skin(ellipsoid("Foot", (s * 0.085, -0.035, BOT + 0.012), (0.050, 0.064, 0.040), M_FUR_D, segs=12, rings=8), "Body")
    for k in (-1, 0, 1):
        skin(ellipsoid("Toe", (s * 0.085 + k * 0.026, -0.090, BOT - 0.004), (0.016, 0.022, 0.016), M_FUR_D, segs=8, rings=6), "Body")


def tuft(theta, phi, length, radius, lean=(0, 0, 0), material=None):
    base, nrm = BODY.pt(theta, phi), BODY.normal(theta, phi)
    d = (nrm + Vector(lean)).normalized()
    pts = [base - d * 0.02 + d * (length + 0.02) * t for t in (0, 0.35, 0.7, 1.0)]
    ob = sweep("Tuft", pts, [radius, radius * 0.85, radius * 0.5, 0], material or M_FUR, segs=7)
    w = bw(base)
    skin_fn(ob, lambda co: w)


if SHADOW:
    for s in (-1, 1):
        for ph, ln in ((30, 0.08), (10, 0.11), (-10, 0.11), (-30, 0.09)):
            tuft(s * 84, ph, ln, 0.042, lean=(s * 0.2, 0, -0.45))
            tuft(s * 112, ph - 10, ln * 0.8, 0.038, lean=(s * 0.1, 0.2, -0.45))
        tuft(s * 150, 10, 0.08, 0.04, lean=(0, 0, -0.3))
        tuft(s * 150, -25, 0.08, 0.04, lean=(0, 0, -0.3))
        tuft(s * 30, -62, 0.06, 0.035, lean=(0, 0, -0.3))
    for th in (-9, 0, 9):
        tuft(th, 80, 0.08 if th == 0 else 0.06, 0.035, lean=(th * 0.03, -0.2, 0.2))
else:
    for s in (-1, 1):
        tuft(s * 80, 2, 0.06, 0.038, lean=(0, 0, -0.5))
        tuft(s * 80, -14, 0.065, 0.040, lean=(0, 0, -0.5))
    for th in (-8, 0, 8):
        tuft(th, 82, 0.07 if th == 0 else 0.05, 0.03, lean=(th * 0.04, -0.3, 0.2))

# ───────────────────────── 臉 ─────────────────────────
face = []
EYE_TH, EYE_PH = 19.5, 15.0
if SHADOW:
    for s in (-1, 1):
        for nm, size, m, push, cut in (("EyeRim", (0.070, 0.056), M_PUPIL, 0.000, 0.016), ("EyeGlow", (0.060, 0.046), M_EYE, 0.004, 0.008)):
            ob = BODY.patch(nm, s * EYE_TH, EYE_PH, size, m, push=push, thick=0.014, segs=16, rings=8)
            c, nrm = BODY.pt(s * EYE_TH, EYE_PH), BODY.normal(s * EYE_TH, EYE_PH)
            side = Vector((0, 0, 1)).cross(nrm).normalized() * s      # 往外側
            up = nrm.cross(Vector((0, 0, 1)).cross(nrm)).normalized()
            pn = (up * math.cos(math.radians(24)) - side * math.sin(math.radians(24))).normalized()  # 內側低、外側高的斜切
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=c + up * cut, plane_no=pn, clear_outer=True)
            edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            bm.to_mesh(ob.data)
            bm.free()
            face.append(ob)
        # 壓低的眉骨（蓋住切口，表情更兇）
        c = BODY.pt(s * EYE_TH, EYE_PH)
        p_in = BODY.pt(s * (EYE_TH - 15), EYE_PH - 1.5, 0.012)
        p_mid = BODY.pt(s * EYE_TH, EYE_PH + 6.5, 0.016)
        p_out = BODY.pt(s * (EYE_TH + 16), EYE_PH + 14, 0.008)
        face.append(sweep("Brow", [p_in, p_mid, p_out], [0.011, 0.018, 0.009], M_FUR_D, segs=8))
        face.append(BODY.patch("Glint", s * EYE_TH - 5, EYE_PH - 4, (0.008, 0.007), M_SHINE, push=0.016, segs=8, rings=6))
        face.append(BODY.patch("Blush", s * 40, -6, (0.030, 0.016), M_BLUSH, push=0.004, thick=0.006, segs=10, rings=6))
    pts = [BODY.pt(u * 11, -9 - 3.5 * u * u, 0.002) for u in (-1, -0.66, -0.33, 0, 0.33, 0.66, 1)]
    face.append(sweep("Mouth", pts, [0.003, 0.0045, 0.005, 0.005, 0.005, 0.0045, 0.003], M_MOUTH, segs=6))
    fang_at, fang_len = (6.5, -10.5), 0.045
else:
    for s in (-1, 1):
        th = s * EYE_TH
        face += [
            BODY.patch("EyeWhite", th, EYE_PH, (0.054, 0.058), M_WHITE, push=-0.001, segs=16, rings=8),
            BODY.patch("Pupil", th - s * 3.0, EYE_PH - 1.0, (0.026, 0.031), M_PUPIL, push=0.004, segs=14, rings=8),
            BODY.patch("Glint", th - s * 3.0 - 3.0, EYE_PH + 2.5, (0.010, 0.011), M_SHINE, push=0.008, segs=8, rings=6),
            BODY.patch("Glint2", th - s * 3.0 + 3.0, EYE_PH - 4.5, (0.005, 0.005), M_SHINE, push=0.008, segs=8, rings=6),
            BODY.patch("Blush", s * 41, -3, (0.032, 0.018), M_BLUSH, push=0.004, thick=0.006, segs=10, rings=6),
        ]
        # 圓眼鏡
        gc, gn = BODY.pt(th, EYE_PH, 0.020), BODY.normal(th, EYE_PH)
        gq = gn.to_track_quat("Z", "Y")
        face.append(torus("GlassRing", gc, 0.071, 0.0085, M_GLASS, segs=24, rsegs=6, rot=gq))
        face.append(ellipsoid("GlassLens", gc, (0.066, 0.066, 0.003), M_LENS, rot=gq, segs=16, rings=4))
        face.append(BODY.patch("LensGlare", th + 6.5, EYE_PH + 6.5, (0.016, 0.006), M_SHINE, push=0.0235, thick=0.002, roll=-40, segs=8, rings=4))
        tip = BODY.pt(s * 62, EYE_PH + 2, 0.004)
        face.append(sweep("GlassArm", [gc + (tip - gc).normalized() * 0.071, tip], 0.006, M_GLASS, segs=6))
    bridge = [BODY.pt(u * 4.8, EYE_PH + 2.5 + 1.5 * (1 - u * u), 0.024) for u in (-1, -0.5, 0, 0.5, 1)]
    face.append(sweep("GlassBridge", bridge, 0.007, M_GLASS, segs=6))
    face.append(BODY.patch("Nose", 0, 2.5, (0.011, 0.008), M_FUR_D, push=0.002, thick=0.010, segs=8, rings=6))
    pts = [BODY.pt(u * 9, -8.5 + 3.5 * u * u - (1.6 if abs(u) < 0.1 else 0) * -1, 0.002) for u in (-1, -0.66, -0.33, 0, 0.33, 0.66, 1)]
    face.append(sweep("Mouth", pts, [0.0028, 0.0042, 0.0048, 0.0042, 0.0048, 0.0042, 0.0028], M_MOUTH, segs=6))
    fang_at, fang_len = (5.0, -9.0), 0.034
for s in (-1, 1):
    b = BODY.pt(s * fang_at[0], fang_at[1], -0.004)
    face.append(sweep("Fang", [b, b + Vector((0, -0.006, -fang_len * 0.5)), b + Vector((0, -0.008, -fang_len))], [0.012, 0.008, 0], M_FANG, segs=8))
skin(face, "Head")

# ───────────────────────── 耳朵 ─────────────────────────
EAR = {}
for s, side in ((1, "L"), (-1, "R")):
    base = BODY.pt(s * 90, 56, -0.03) + Vector((0, 0.01, 0))
    d = Vector((s * (0.42 if not SHADOW else 0.5), 0.05, 1)).normalized()
    ln, wd = (0.33, 0.105) if not SHADOW else (0.30, 0.085)
    n = 7
    pts, r_out, r_in, pts_in = [], [], [], []
    for i in range(n + 1):
        t = i / n
        p = base + d * ln * t + Vector((s * 0.03, 0, 0)) * math.sin(math.pi * t)
        k = math.sin(math.pi * (0.16 + 0.84 * t)) ** 0.75 if i < n else 0
        if SHADOW:
            k *= (1 - 0.35 * t)
        pts.append(p)
        r_out.append((0.034 * (0.5 + 0.5 * k), wd * k) if i < n else 0)
        if 0 < i:
            pts_in.append(base + d * ln * (0.10 + 0.82 * t) + Vector((s * 0.03, 0, 0)) * math.sin(math.pi * t) + Vector((0, -0.016, 0)))
            r_in.append((0.022 * k, wd * 0.66 * k) if i < n else 0)
    ear = [sweep("Ear", pts, r_out, M_FUR, segs=10, up=(0, -1, 0)), sweep("EarInner", pts_in, r_in, M_EAR_IN, segs=10, up=(0, -1, 0))]
    skin(ear, f"Ear_{side}")
    EAR[side] = (base + d * 0.04, base + d * ln)

# ───────────────────────── 翅膀 ─────────────────────────
WX0, WSPAN, WZ = 0.19, 0.53, 0.965
if SHADOW:
    WX0, WSPAN = 0.18, 0.54


def wing_top(u):
    return WZ + 0.30 * math.sin(math.pi * max(u, 0.0) ** 0.7) * (1 - 0.10 * u)


def wing_bot(u):
    z = WZ - 0.235 + 0.235 * u ** 3 + 0.080 * abs(math.sin(3 * math.pi * u)) * (1 - u ** 3)
    if SHADOW:  # 破損的翅緣：鋸齒缺口
        z += 0.030 * (1 - u ** 2) * (abs(((u * 13) % 1.0) - 0.5) * 2) - 0.012
        z += 0.05 * math.exp(-((u - 0.52) / 0.035) ** 2) + 0.04 * math.exp(-((u - 0.2) / 0.03) ** 2)
    return z


def wing_pt(s, u, v):
    zt, zb = wing_top(u), wing_bot(u)
    return Vector((s * (WX0 + WSPAN * u), 0.025 - 0.035 * u + 0.02 * math.sin(math.pi * v) * (1 - u), lerp(zt, min(zb, zt), v)))


def wing_w(side):
    def fn(co):
        u = (abs(co.x) - WX0) / WSPAN
        w2, w3 = sstep(0.26, 0.46, u), sstep(0.60, 0.80, u)
        return {f"Wing1_{side}": 1 - w2, f"Wing2_{side}": w2 * (1 - w3), f"Wing3_{side}": w2 * w3}
    return fn


NU = 26 if SHADOW else 20
# 書頁翅膀：橫列固定在世界高度上（超出翅膀輪廓的頂點夾到邊緣），細列當作一行行的「字」
ZS, LINE_ROWS = [WZ + 0.32], set()
z = WZ + 0.245
while z > WZ - 0.21:
    LINE_ROWS.add(len(ZS))
    ZS += [z, z - 0.015]
    z -= 0.052
ZS.append(WZ - 0.26)
LINE_END = [0.62, 0.80, 0.70, 0.84, 0.66, 0.78, 0.58, 0.72, 0.50, 0.60, 0.44, 0.5]


def page_pt(s, u, z):
    zt, zb = wing_top(u), min(wing_bot(u), wing_top(u))
    zc = min(zt, max(zb, z))
    v = (zt - zc) / max(zt - zb, 1e-6)
    return Vector((s * (WX0 + WSPAN * u), 0.025 - 0.035 * u + 0.02 * math.sin(math.pi * v) * (1 - u), zc))


def page_mat(i, j):
    if j not in LINE_ROWS:
        return 0
    u, zc = (i + 0.5) / NU, (ZS[j] + ZS[j + 1]) / 2
    k = sorted(LINE_ROWS).index(j)
    inside = all(wing_top(uu) - zc > 0.035 and zc - wing_bot(uu) > 0.028 for uu in (i / NU, (i + 1) / NU))
    return 1 if inside and 0.06 < u < LINE_END[k % len(LINE_END)] else 0


for s, side in ((1, "L"), (-1, "R")):
    parts = []
    if SHADOW:
        parts.append(surface("Wing", lambda u, v, s=s: wing_pt(s, u, v), NU, 6, [M_WING]))
    else:
        parts.append(surface("Wing", lambda u, z, s=s: page_pt(s, u, z), NU, ZS, [M_WING, M_INK], mat_fn=page_mat))
    n = 14
    parts.append(sweep("WingArm", [wing_pt(s, lerp(-0.08, 1.0, i / n), 0) for i in range(n + 1)], [lerp(0.024, 0.008, i / n) for i in range(n)] + [0], M_WING_ARM, segs=8))
    UW = 0.36
    for ut in (1 / 3, 2 / 3):
        parts.append(sweep("WingRib", [wing_pt(s, lerp(UW, ut, t), t) for t in (0, 0.25, 0.5, 0.75, 1.0)], [0.011, 0.009, 0.008, 0.007, 0.004], M_WING_ARM, segs=6))
    parts.append(sweep("WingRib", [wing_pt(s, lerp(0.0, 0.0, t), t) for t in (0.1, 0.5, 1.0)], [0.010, 0.008, 0.004], M_WING_ARM, segs=6))
    wp = wing_pt(s, UW, 0)
    parts.append(sweep("WingClaw", [wp, wp + Vector((s * 0.01, -0.01, 0.035)), wp + Vector((s * 0.03, -0.015, 0.06))], [0.014, 0.010, 0], M_WING_ARM if SHADOW else M_FUR_D, segs=6))
    skin_fn(parts, wing_w(side))

# ───────────────────────── 骨架 ─────────────────────────
rig = Rig("BatShadow" if SHADOW else "BatOrange")
rig.bone("Root", (0, 0, 0), (0, 0, 0.2))
rig.bone("Body", BC, BC + Vector((0, 0, 0.12)), "Root")
rig.bone("Head", (0, 0, BOT + 0.30 * (TOP - BOT)), (0, 0, TOP), "Body")
for s, side in ((1, "L"), (-1, "R")):
    rig.bone(f"Ear_{side}", EAR[side][0], EAR[side][1], "Head")
    j = [Vector((s * (WX0 + WSPAN * u), 0.025 - 0.035 * u, z)) for u, z in ((0.0, WZ - 0.02), (0.36, WZ + 0.05), (0.70, WZ + 0.04), (1.0, WZ))]
    rig.bone(f"Wing1_{side}", j[0], j[1], "Body")
    rig.bone(f"Wing2_{side}", j[1], j[2], f"Wing1_{side}")
    rig.bone(f"Wing3_{side}", j[2], j[3], f"Wing2_{side}")
rig.done()
mesh = join_parts("BatMesh")
rig.bind(mesh)

# ───────────────────────── 動作 ─────────────────────────
def L(x=0.0, y=0.0, z=0.0, r=(0, 0, 0)):
    return dict(l=(x, y, z), r=r)


def wings(up1, up2=None, up3=None, sweep=0.0, fold=0.0):
    """翅膀姿勢：up＝往上抬的角度（三節），sweep＝往後收，fold＝第一節往前捲。"""
    up2 = up1 * 0.6 if up2 is None else up2
    up3 = up2 * 0.6 if up3 is None else up3
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"Wing1_{side}"] = (fold, -s * up1, s * sweep)
        out[f"Wing2_{side}"] = (0, -s * up2, s * sweep * 0.5)
        out[f"Wing3_{side}"] = (0, -s * up3, 0)
    return out


def flap(start, end, period, amp=1.0, phase=0.0, sweep=0.0, step=2, lift=6.0):
    """拍翅：三節依序延遲，做出柔軟的波動。回傳 {骨頭: [(影格, 旋轉)]}。"""
    tr = {}
    f = start
    while f <= end:
        ph = 2 * math.pi * ((f - start) / period + phase)
        w = wings(lift + 30 * amp * math.cos(ph), 26 * amp * math.cos(ph - 0.9), 22 * amp * math.cos(ph - 1.8), sweep=sweep + 8 * amp * math.sin(ph))
        for bn, r in w.items():
            tr.setdefault(bn, []).append((f, r))
        f += step
    return tr


def hold(frame, **kw):
    return {bn: [(frame, r)] for bn, r in wings(**kw).items()}


def cat(*trs):
    out = {}
    for tr in trs:
        for bn, ks in tr.items():
            out.setdefault(bn, []).extend(ks)
    for ks in out.values():
        ks.sort(key=lambda k: k[0])
    return out


def bob(f, period, amp, phase=0.0):
    return amp * math.cos(2 * math.pi * ((f - 1) / period - phase))


def W0(frame):
    """Idle 第 1 格的翅膀姿勢（各動作的起點與終點）。"""
    return {bn: [(frame, ks[0][1])] for bn, ks in flap(1, 1, 16).items()}


def B0():
    return L(z=bob(1, 16, 0.035, 0.42), r=(3 * math.cos(2 * math.pi * -0.3), 0, 0))


H0 = (2 * math.cos(2 * math.pi * -0.55), 0, 0)
E0 = {"Ear_L": (7 * math.cos(2 * math.pi * -0.6), 0, 0), "Ear_R": (7 * math.cos(2 * math.pi * -0.7), 0, 0)}
START = {"Root": L(), "Body": B0(), "Head": H0, **E0}

# Idle：拍翅懸浮（16 格拍一次，32 格循環），身體上下起伏、耳朵跟著晃
idle = []
for f in range(1, 34, 2):
    idle.append((f, {
        "Body": L(z=bob(f, 16, 0.035, 0.42), r=(3 * math.cos(2 * math.pi * ((f - 1) / 16 - 0.3)), 2.5 * math.sin(2 * math.pi * (f - 1) / 32), 0)),
        "Head": (2 * math.cos(2 * math.pi * ((f - 1) / 16 - 0.55)), 3 * math.sin(2 * math.pi * (f - 1) / 32), 0),
        "Ear_L": (7 * math.cos(2 * math.pi * ((f - 1) / 16 - 0.6)), -4 * math.sin(2 * math.pi * (f - 1) / 32), 0),
        "Ear_R": (7 * math.cos(2 * math.pi * ((f - 1) / 16 - 0.7)), -4 * math.sin(2 * math.pi * (f - 1) / 32), 0),
    }))
rig.action("Idle", idle, loop=True, extra=flap(1, 33, 16))

# Enter：從後上方俯衝進場→張翅急煞→回到定位
rig.action("Enter", [
    (1, {"Root": L(y=1.5, z=1.5), "Body": (38, 0, 0), "Head": (-12, 0, 0), "Ear_L": (-25, 0, 0), "Ear_R": (-25, 0, 0)}),
    (9, {"Root": L(y=0.45, z=0.05), "Body": (30, 0, 0), "Head": (-14, 0, 0), "Ear_L": (-30, 0, 0), "Ear_R": (-30, 0, 0)}),
    (14, {"Root": L(y=0.0, z=-0.22), "Body": (4, 0, 0), "Head": (-4, 0, 0), "Ear_L": (-20, 0, 0), "Ear_R": (-20, 0, 0)}),
    (19, {"Root": L(y=-0.14, z=0.14), "Body": (-22, 0, 0), "Head": (10, 0, 0), "Ear_L": (16, 0, 0), "Ear_R": (16, 0, 0)}),
    (25, {"Root": L(y=0.03, z=-0.04), "Body": (6, 0, 0), "Head": (-3, 0, 0), "Ear_L": (-8, 0, 0), "Ear_R": (-8, 0, 0)}),
    (30, START),
], extra=cat(hold(1, up1=48, up2=20, up3=10, sweep=42), hold(9, up1=52, up2=24, up3=12, sweep=46), hold(14, up1=30, up2=10, up3=0, sweep=10),
             hold(17, up1=-22, up2=-30, up3=-20, sweep=-16), hold(20, up1=34, up2=14, up3=0, sweep=6), flap(22, 28, 8, phase=0.25), W0(30)))

# Attack：後仰蓄勢→俯衝→咬→回位
rig.action("Attack", [
    (1, START),
    (7, {"Root": L(y=0.22, z=0.20), "Body": (-20, 0, 0), "Head": (-10, 0, 0), "Ear_L": (18, 0, 0), "Ear_R": (18, 0, 0)}),
    (12, {"Root": L(y=0.28, z=0.24), "Body": (-26, 0, 0), "Head": (-14, 0, 0), "Ear_L": (10, 0, 0), "Ear_R": (10, 0, 0)}),
    (17, {"Root": L(y=-1.35, z=-0.24), "Body": (40, 0, 0), "Head": (-26, 0, 0), "Ear_L": (-38, 0, 0), "Ear_R": (-38, 0, 0)}),
    (19, {"Root": L(y=-1.68, z=-0.30), "Body": (20, 0, 0), "Head": (18, 0, 0), "Ear_L": (-10, 0, 0), "Ear_R": (-10, 0, 0)}),
    (22, {"Root": L(y=-1.62, z=-0.27), "Body": (16, 0, 0), "Head": (8, 0, 0), "Ear_L": (20, 0, 0), "Ear_R": (20, 0, 0)}),
    (26, {"Root": L(y=-1.40, z=-0.14), "Body": (-12, 0, 0), "Head": (-4, 0, 0), "Ear_L": (8, 0, 0), "Ear_R": (8, 0, 0)}),
    (34, {"Root": L(y=-0.45, z=0.16), "Body": (-16, 0, 0), "Head": (4, 0, 0), "Ear_L": (14, 0, 0), "Ear_R": (14, 0, 0)}),
    (40, {"Root": L(y=0.04, z=0.03), "Body": (-4, 0, 0)}),
    (44, START),
], extra=cat(W0(1), flap(3, 7, 8, amp=1.1, phase=0.25), hold(10, up1=56, up2=30, up3=16, sweep=20), hold(13, up1=60, up2=34, up3=18, sweep=28),
             hold(17, up1=40, up2=10, up3=0, sweep=52), hold(19, up1=-6, up2=-22, up3=-16, sweep=-34), hold(22, up1=10, up2=0, up3=0, sweep=-8),
             flap(24, 42, 10, amp=1.05, phase=0.2), W0(44)))

# Hit：被打飛→晃兩下→回位
rig.action("Hit", [
    (1, START),
    (4, {"Root": L(y=0.34, z=0.08), "Body": (-34, 0, 12), "Head": (-16, 0, 0), "Ear_L": (-34, 0, 0), "Ear_R": (-34, 0, 0)}),
    (8, {"Root": L(y=0.42, z=-0.02), "Body": (-12, 10, -14), "Head": (10, 0, 0), "Ear_L": (22, 0, 0), "Ear_R": (22, 0, 0)}),
    (13, {"Root": L(y=0.22, z=-0.05), "Body": (10, -6, 8), "Head": (4, 0, 0), "Ear_L": (-10, 0, 0), "Ear_R": (-10, 0, 0)}),
    (20, START),
], extra=cat(W0(1), hold(4, up1=30, up2=30, up3=24, sweep=-40), hold(8, up1=-28, up2=-20, up3=-12, sweep=-6),
             hold(12, up1=38, up2=16, up3=4, sweep=8), hold(16, up1=-18, up2=-14, up3=-8), W0(20)))

# Faint：彈起→旋轉墜地→彈一下→仰躺攤平
LAND = -(BC.z - BR[1] - 0.01)
faint, spin_frames = [(1, START)], [4, 7, 10, 13, 16, 19, 22, 25]
for i, f in enumerate(spin_frames):
    t = (i + 1) / len(spin_frames)
    z = 0.16 * math.sin(math.pi * min(1.0, t * 2.2)) * (1 if t < 0.45 else 0) + LAND * max(0.0, (t - 0.25) / 0.75) ** 1.8
    faint.append((f, {"Root": L(y=0.30 * t, z=z), "Body": (-80 * t ** 1.5, 0, 90 * (i + 1)), "Head": (-8, 0, 0),
                      "Ear_L": (-30 * t, 0, 0), "Ear_R": (-30 * t, 0, 0)}))
faint += [
    (28, {"Root": L(y=0.34, z=LAND + 0.11), "Body": (-70, 0, 720), "Head": (12, 0, 0), "Ear_L": (10, 0, 0), "Ear_R": (10, 0, 0)}),
    (32, {"Root": L(y=0.36, z=LAND), "Body": (-84, 0, 720), "Head": (-4, 0, 0), "Ear_L": (-24, 10, 0), "Ear_R": (-24, -10, 0)}),
    (42, {"Root": L(y=0.36, z=LAND), "Body": (-84, 0, 720), "Head": (-4, 0, 0), "Ear_L": (-26, 12, 0), "Ear_R": (-26, -12, 0)}),
]
rig.action("Faint", faint, extra=cat(W0(1), hold(5, up1=10, up2=30, up3=30, sweep=-20), hold(10, up1=58, up2=34, up3=26, sweep=10),
                                      hold(18, up1=64, up2=40, up3=30, sweep=16), hold(25, up1=40, up2=20, up3=10, sweep=20),
                                      hold(28, up1=22, up2=-10, up3=-10, sweep=30), hold(32, up1=4, up2=4, up3=6, sweep=30), hold(42, up1=2, up2=6, up3=8, sweep=31)))

# Victory：下沉蓄力→轉一圈往上飛→落回→再小跳一下
rig.action("Victory", [
    (1, START),
    (6, {"Root": L(z=-0.10), "Body": (10, 0, 0), "Head": (6, 0, 0), "Ear_L": (-14, 0, 0), "Ear_R": (-14, 0, 0)}),
    (9, {"Root": L(z=0.12), "Body": (-8, 0, 90), "Head": (-8, 0, 0), "Ear_L": (-24, 0, 0), "Ear_R": (-24, 0, 0)}),
    (12, {"Root": L(z=0.34), "Body": (-10, 0, 180), "Head": (-10, 0, 0), "Ear_L": (-10, 0, 0), "Ear_R": (-10, 0, 0)}),
    (15, {"Root": L(z=0.40), "Body": (-6, 0, 270), "Head": (-6, 0, 0), "Ear_L": (8, 0, 0), "Ear_R": (8, 0, 0)}),
    (18, {"Root": L(z=0.30), "Body": (0, 0, 360), "Head": (0, -8, 0), "Ear_L": (16, 0, 0), "Ear_R": (16, 0, 0)}),
    (23, {"Root": L(z=-0.05), "Body": (8, 0, 360), "Head": (6, 8, 0), "Ear_L": (-12, 0, 0), "Ear_R": (-12, 0, 0)}),
    (28, {"Root": L(z=0.18), "Body": (-8, 0, 360), "Head": (-8, -8, 0), "Ear_L": (12, 0, 0), "Ear_R": (12, 0, 0)}),
    (33, {"Root": L(z=-0.02), "Body": (4, 0, 360), "Head": (3, 6, 0), "Ear_L": (-8, 0, 0), "Ear_R": (-8, 0, 0)}),
    (38, {**START, "Body": dict(l=B0()["l"], r=(B0()["r"][0], 0, 360))}),
], extra=cat(W0(1), hold(6, up1=-30, up2=-24, up3=-16, sweep=-10), hold(10, up1=50, up2=24, up3=12, sweep=16),
             hold(15, up1=62, up2=30, up3=14, sweep=4), hold(19, up1=40, up2=30, up3=22), hold(23, up1=-28, up2=-20, up3=-12), hold(28, up1=56, up2=28, up3=14),
             hold(33, up1=-20, up2=-16, up3=-10), W0(38)))

# ───────────────────────── 匯出 ─────────────────────────
bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
print("BAT", VARIANT, "tris", tri_count(mesh), "verts", len(mesh.data.vertices),
      "size", [round(max(p[i] for p in bb) - min(p[i] for p in bb), 3) for i in range(3)], "z", round(min(p.z for p in bb), 3), round(max(p.z for p in bb), 3))
if not ONLY:
    export_glb(rig, mesh, OUT_GLB)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

VIEWS = [("Front", (0, -3.0, 1.0), (0, 0, 0.98)), ("Side", (-3.0, 0, 1.0), (0, 0, 0.98)),
         ("3/4", (-1.9, -2.3, 1.35), (0, 0, 0.96)), ("Back 3/4", (1.8, 2.4, 1.35), (0, 0, 0.96))]
ACTION_FRAMES = {
    "Idle": [1, 5, 9, 13], "Enter": [5, 12, 17, 24],
    "Attack": [7, 12, 17, 19], "Hit": [4, 8, 13, 17],
    "Faint": [7, 16, 28, 42], "Victory": [6, 12, 18, 28],
}
render_previews(rig, NAME, PREVIEW_DIR, VIEWS, ACTION_FRAMES, ((-2.2, -3.0, 1.35), (0, 0, 0.85)), view_res=(560, 480),
                per_action_cam={"Attack": ((-3.4, -3.2, 1.3), (0, -0.75, 0.75)), "Enter": ((-2.8, -3.4, 1.6), (0, 0.3, 1.0)),
                                "Faint": ((-2.2, -3.0, 1.35), (0, 0.15, 0.55))},
                strip_dir=STRIP_DIR, only=ONLY)
print("DONE", NAME, [a.name for a in bpy.data.actions])
