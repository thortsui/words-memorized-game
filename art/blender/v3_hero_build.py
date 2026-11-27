"""單字魂 v3 主角騎士 hero_knight（規格：art/v3/specs/hero_knight.md；參考：art/reference/hero_knight_sheet.jpg）。
用法（headless）：
  blender --background --factory-startup --python v3_hero_build.py -- [--quick] [--nobake] [--reusebake] [--noanim] [--only A,B] [--noviews]
輸出：art/blender/export_raw/hero_knight.glb（未壓縮）、export_raw/hero_knight.clipmeta.json、
      art/blender/source/v3_hero_knight.blend、預覽圖塊 art/v3/tmp/hero/tiles/
壓縮到 public/models 由 v3_hero_run.sh 用 gltf-transform 做。
"""
import bpy, sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector, Quaternion
from soul_humanoid_lib import *
from soul_humanoid_parts import w_skirt
import v3_hero_parts as HP
import v3_hero_bake as BK
from v3_hero_rig import V3Rig as Rig

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
NOBAKE = "--nobake" in argv
NOANIM = "--noanim" in argv
NOVIEWS = "--noviews" in argv
REUSE = "--reusebake" in argv          # v4：沿用 textures/baked 既有烘焙圖（不重烘），照常匯出
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
TEX = int(argv[argv.index("--tex") + 1]) if "--tex" in argv else 2048
MODEL = "hero_knight"
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = os.path.join(HERE, "export_raw", MODEL + ".glb")
OUT_BLEND = os.path.join(HERE, "source", "v3_" + MODEL + ".blend")
TMP = os.environ.get("HERO_TMP") or os.path.join(ROOT, "art", "v3", "tmp", "hero")
TILES = os.path.join(TMP, "tiles")

reset_scene()
Builder.HIRES = True
body = Body(H=1.8, bulk=1.0, wf=1.0, head=0.235)
HP.tune_body(body)
body.set_grip(0.0150)
U = body.U; j = body.j
B = HP.V3Builder()
L = HP.Layers(body)

# ---------------------------------------------------------------- 材質（spec 第 2 節）
D = BK.define_v3
MUD = 0.15 * 1.8
D("steel", "A", "steel", "#7a7c78", dark="#4c4d48", rough=0.56, metal=0.9, bump=0.6, seed=0.0, rust=0.055, dirt=1.0, scratch=1.6)
D("steelD", "A", "steel", "#71736f", dark="#474843", rough=0.58, metal=0.9, bump=0.6, seed=3.0, rust=0.06, dirt=1.0, scratch=1.6)
D("greave", "A", "steel", "#6d6f6a", dark="#464742", rough=0.6, metal=0.9, bump=0.5, seed=6.0, rust=0.05, mud_z=MUD, mud_amt=0.85,
  dents=0.6, dirt=1.0, scratch=1.5)
D("mail", "A", "mail", "#4a4a45", rough=0.55, metal=0.9, bump=1.0, seed=1.0, rust=0.03, mud_z=0.40 * 1.8 * 0.5, mud_amt=0.3, tex_size=0.12)
D("rivet", "A", "iron", "#6e706b", rough=0.42, metal=0.9, bump=0.3, seed=2.0, rust=0.07, scratch=0.0, dents=0.0, hammer=0.0)
D("linen", "B", "linen", "#5f6769", dark="#4d5354", rough=0.93, metal=0.0, bump=0.8, seed=4.0, stain=1.25, mud_z=0.80, mud_amt=0.45,
  mud_col="#4a463d", holes_z=(1.18, 1.40), dirt=0.35, ao_shade=0.35)
D("wool", "B", "wool", "#27324a", dark="#161c28", rough=0.92, metal=0.0, bump=0.7, seed=5.0, stain=0.25, fade_z=0.62, fade_col="#3a4252",
  mud_z=0.50, mud_amt=0.55, mud_col="#2f2b27")
D("leather", "B", "leather", "#4a3e33", rough=0.75, bump=0.6, seed=7.0, edge_col="#6e5d4c")
D("bald", "B", "leather", "#4f4236", rough=0.75, bump=0.6, seed=8.0, edge_col="#74624f")
D("swordbelt", "B", "leather", "#3f342a", rough=0.78, bump=0.6, seed=9.0, edge_col="#62523f")
D("pouch", "B", "leather", "#4a3e38", rough=0.8, bump=0.7, seed=10.0, edge_col="#76665a", crack=0.6)
D("scab", "B", "leather", "#3d3127", rough=0.7, bump=0.6, seed=11.0, edge_col="#5e4c3b")
D("boot", "B", "leather", "#5e5148", rough=0.8, bump=0.7, seed=12.0, edge_col="#7b6c5f", mud_z=MUD, mud_amt=0.9, stitch=False)
D("sole", "B", "leather", "#2e2620", rough=0.85, bump=0.5, seed=13.0, mud_z=MUD, mud_amt=0.9, stitch=False, crack=0.0)
D("glove", "B", "leather", "#4a3e33", rough=0.8, bump=0.5, seed=14.0, stitch=False)
D("grip", "B", "grip", "#483e35", rough=0.8, bump=0.8, seed=15.0, crack=0.0)
D("blade", "B", "blade", "#7a7772", dark="#5f5c58", rough=0.36, metal=0.95, bump=0.35, seed=16.0, rust=0.03, edge_col="#c0beb8",
  hammer=0.0, dents=0.0, scratch=0.6)
D("iron", "B", "iron", "#6a6a66", dark="#4e4e4a", rough=0.45, metal=0.9, bump=0.4, seed=17.0, rust=0.07, hammer=0.4, dents=0.0, scratch=0.4)
D("guard", "B", "iron", "#5e5a55", dark="#46423e", rough=0.45, metal=0.9, bump=0.4, seed=18.0, rust=0.08, hammer=0.4, dents=0.0, scratch=0.4)
D("linenFray", "B", "linen", "#6a7072", dark="#5a6062", rough=0.95, bump=0.3, seed=4.5, stain=0.0, dirt=0.0, ao_shade=0.05, wear=0.0)
D("woolFray", "B", "wool", "#2e3a52", dark="#222b3c", rough=0.95, bump=0.3, seed=5.5, stain=0.0, dirt=0.0, ao_shade=0.05, wear=0.0)
D("void", "B", "void", "#010101")

# ---------------------------------------------------------------- 內層：鎖子甲
HP.mail_layers(B, body, L, "mail")
from soul_humanoid_parts import under_arm, under_leg
under_arm(B, body, "mail", texel=1.0, off=0.006)
under_leg(B, body, "mail", texel=1.0, off=0.008)
HP.cuirass(B, body, L, "steelD", "rivet")
HP.tabard(B, body, L, "linen")
HP.belts(B, body, L, "leather", "swordbelt", "iron", "bald")
HP.pouch(B, body, L, "pouch", "iron")                  # 右胯（角度 -62，直接建在右側）
scab_obs, scab_top, scab_dir = HP.scabbard(B, body, L, "scab", "iron", "swordbelt")
B.both(HP.tasset(B, body, L, "steelD", "rivet", "leather"))

# ---------------------------------------------------------------- 肩、手臂
HP.pauldron_left(B, body, "steel", "rivet", "leather")
B.mirror_only(HP.pauldron_right(B, body, "steel", "rivet", "leather"))
B.both(HP.arm_armor(B, body, "steelD", "rivet", "leather"))
B.mirror_only(HP.hand(B, body, "steelD", "glove"))            # 右手握劍
HP.hand(B, body, "steelD", "glove", open_amt=0.35)              # 左手半握

# ---------------------------------------------------------------- 腿
B.both(HP.leg_armor(B, body, "steelD", "steel", "greave", "rivet", "leather"))
B.both(HP.boot(B, body, "boot", "steelD", "sole", "leather"))

# ---------------------------------------------------------------- 頭盔
HP.helmet(B, body, "steel", "void", "rivet")

# ---------------------------------------------------------------- 披風：圍巾段＋別針＋背後兩層
HP.scarf(B, body, "wool")
HP.ring_brooch(B, body, "iron")
cape_pts = [V(0, 0.150, 1.445), V(0, 0.215, 1.05), V(0, 0.255, 0.66), V(0, 0.285, 0.26)]
cape_names = chain_names("Cape", 3)
cw = w_chain_pts("Spine2", cape_names, cape_pts)


def cape_top(off):
    def f(u):
        return body.torso.pt(body.tz(0.905), lerp(122, 238, u), off) + V(0, 0.012, 0)
    return f


def cape_n(u):
    a = math.radians(lerp(122, 238, u))
    return (V(math.sin(a) * 0.35, 0.94, 0)).normalized()


HP.cape_panel(B, "Cape", cape_top(0.052), cape_n, 1.23, "wool", cw, nu=40, nv=44, rag=0.11, fold_amp=0.026, fold_n=6.0,
              holes=[(0.28, 0.60, 0.070, 0.030, 0.20), (0.63, 0.77, 0.085, 0.026, 0.22), (0.80, 0.46, 0.055, 0.032, 0.18),
                     (0.46, 0.90, 0.060, 0.022, 0.22), (0.15, 0.84, 0.055, 0.028, 0.20)],
              seed=11, flare=0.09, sag=0.032, spread=-0.20, thick=0.011)
HP.cape_panel(B, "CapeInner", cape_top(0.040), cape_n, 1.12, "wool", cw, nu=28, nv=30, rag=0.09, fold_amp=0.020, fold_n=5.0,
              holes=[(0.55, 0.70, 0.075, 0.032, 0.20), (0.30, 0.86, 0.060, 0.028, 0.22)],
              seed=23, flare=0.075, sag=0.026, spread=-0.18, thick=0.009)

# ---------------------------------------------------------------- 長劍（右手）
gcR = Body.mir(body.grip_c); bladeR = Body.mir(body.hand_v); edgeR = Body.mir(body.hand_a)
_, TIP_LEN = HP.sword(B, gcR, bladeR, edgeR, "blade", "guard", "grip")

# ---------------------------------------------------------------- 骨架
arm = build_armature("HeroKnight", body, weapon=(gcR, gcR + bladeR * 0.30), chains=[("Cape", "Spine2", cape_pts)],
                     extra=[("Scabbard", "Hips", scab_top, scab_top + scab_dir * (0.48 * 1.8))])

tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in B.parts)
print("PARTS", len(B.parts), "TRIS(before polish)", tri, flush=True)
_top = sorted(((sum(len(p.vertices) - 2 for p in o.data.polygons), o.name) for o in B.parts), reverse=True)[:16]
print("TOPTRIS", " ".join(f"{n}:{t}" for t, n in _top), flush=True)

import v3_hero_measure as MS
MS.measure(B.parts, body, 1.8, os.path.join(TMP, "measure.json"))
mesh = BK.assemble(B, MODEL, size=(TEX, TEX), bake=not (QUICK or NOBAKE or REUSE), quick=QUICK, samples=16)
BK.bind(mesh, arm)

# ---------------------------------------------------------------- 動作
rig = Rig(arm, body, chains=[dict(names=cape_names, anchor="Spine2", pts=cape_pts, stiff=0.035, damp=0.93, floor=0.30,
                                  colliders=[("Hips", "Spine2", 0.24), ("ThighL", "ShinL", 0.14), ("ThighR", "ShinR", 0.14),
                                             ("ShinL", "FootL", 0.11), ("ShinR", "FootR", 0.11)])])
rig.tip_len = TIP_LEN
if not NOANIM:
    import v3_hero_actions
    v3_hero_actions.build(rig, ONLY)
    if QUICK or ONLY:
        import json
        os.makedirs(TMP, exist_ok=True)
        json.dump(rig.meta, open(os.path.join(TMP, "meta_quick.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if not (ONLY or QUICK or NOANIM or NOBAKE):
    BK.export_glb(arm, mesh, OUT_GLB)
    BK.write_meta(rig, MODEL, os.path.join(HERE, "export_raw"))
print("TRIS_FINAL", BK.tri_count(mesh), flush=True)
if not NOANIM and (not ONLY or "Idle" in ONLY):
    sx, sd = MS.stance(arm, "Idle", 0)
    print(f"MEASURE stance_idle  lateral {sx / 1.817:.3f}H  center-dist {sd / 1.817:.3f}H  (spec 0.18-0.21H)", flush=True)

# 參考圖對照用的站姿（不匯出）：A 字站、雙腳 0.20H、劍尖拄地
if not NOANIM:
    import v3_hero_actions
    v3_hero_actions.ref_pose(rig)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
if not NOVIEWS:
    import v3_hero_preview as PV
    PV.render_all(arm, TILES, actions=not NOANIM, only=ONLY)
print("DONE", MODEL, flush=True)
