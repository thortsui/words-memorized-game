"""v3 噬語魔王：預覽渲染（讀 source/v3_devourer.blend）。
blender --background --python v3_devourer_preview.py -- [blend] [--set compare,views,close,actions,sil] [--pose Idle:0]
輸出圖塊到 art/v3/tmp/devourer/tiles/，再由 v3_devourer_sheet.py 拼成 art/blender/preview/v3_devourer_*.jpg。
相機：比對圖用正交相機、水平轉 25°（渲染後鏡像，對應參考圖的左右鏡像）、高度比例對齊參考圖（H＝727 px / 768）。
"""
import bpy, sys, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend = next((a for a in argv if a.endswith(".blend")), os.path.join(HERE, "source", "v3_devourer.blend"))
SETS = (argv[argv.index("--set") + 1] if "--set" in argv else "compare,views,close,sil").split(",")
POSE = argv[argv.index("--pose") + 1] if "--pose" in argv else "Idle:0"
TILES = os.path.join(ROOT, "art", "v3", "tmp", "devourer", "tiles")
os.makedirs(TILES, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
HT = 3.9
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA") or o.name.startswith("PreviewGround"):
        bpy.data.objects.remove(o)


def form(f):
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        n = o.name
        on = True
        if n.startswith(("P2_PageWing", "P2_ChestMaw", "P2_ScriptChest")):
            on = f == 2                     # 遊戲端子節點命名 X3_P2_*：三階隱藏
        elif n.startswith("P2_"):
            on = f >= 2
        elif n.startswith("P3_"):
            on = f >= 3
        elif n.startswith("X3_"):
            on = f < 3
        o.hide_render = not on
        o.hide_viewport = not on


def pose(spec):
    ad = arm.animation_data
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    if spec == "rest" or not ad:
        if ad:
            ad.action = None
        sc.frame_set(0)
        return
    nm, fr = spec.split(":")
    act = bpy.data.actions.get(nm)
    if act is None:
        ad.action = None; sc.frame_set(0); return
    ad.action = act
    for t in ad.nla_tracks:
        t.mute = True
    sc.frame_set(int(fr))


try:
    sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    sc.render.engine = "BLENDER_EEVEE"
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items] else "None"
try:
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_shadows = True
    sc.eevee.use_raytracing = True
except Exception:
    pass
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.035, 0.036, 0.04, 1); bg.inputs[1].default_value = 1.0


def light(kind, loc, energy, size, color=(1, 1, 1), tgt=(0, 0, 1.9)):
    bpy.ops.object.light_add(type=kind, location=loc)
    l = bpy.context.object
    l.data.energy = energy; l.data.color = color
    if kind == "AREA":
        l.data.size = size
    d = Vector(tgt) - l.location
    l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l


LIGHTS = [light("AREA", (-4.5, -6.0, 7.0), 2600, 3.0, (1.0, 0.95, 0.86)),       # 左上主光
          light("AREA", (5.0, -3.0, 2.5), 500, 5.0, (0.75, 0.82, 1.0)),          # 右側補光
          light("AREA", (2.5, 6.5, 6.0), 2400, 2.5, (0.95, 0.97, 1.0)),          # 背光（輪廓）
          light("AREA", (-5.0, 4.0, 2.0), 700, 4.0, (1.0, 0.9, 0.8))]
bpy.ops.mesh.primitive_plane_add(size=60)
gp = bpy.context.object; gp.name = "PreviewGround"
gm = bpy.data.materials.new("PG"); gm.use_nodes = True
b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.045, 0.045, 0.05, 1); b.inputs["Roughness"].default_value = 0.85
gp.data.materials.append(gm)
bpy.ops.object.camera_add()
cam = bpy.context.object; sc.camera = cam


def shoot(path, az, tgt, dist=12.0, elev_deg=0.0, ortho=None, lens=50, res=(1376, 768)):
    sc.render.resolution_x, sc.render.resolution_y = res
    a = math.radians(az); e = math.radians(elev_deg)
    tgt = Vector(tgt)
    cam.location = tgt + Vector((math.sin(a) * math.cos(e) * dist, -math.cos(a) * math.cos(e) * dist, math.sin(e) * dist))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens
    cam.data.clip_end = 200
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# 參考圖：H＝727 px（y 18→745），圖高 768 → 正交可視高 3.9*768/727；腳底在 y=745 → 畫面中心高度
OH = HT * 768 / 727
OW = OH * 1376 / 768
ZC = HT * (745 - 384) / 727
if "compare" in SETS:
    pose(POSE)
    for f in (1, 2, 3):
        form(f)
        shoot(os.path.join(TILES, f"cmp_p{f}.png"), -25, (0.0, 0.0, ZC), ortho=OW, elev_deg=0.0)
if "views" in SETS:
    pose(POSE)
    for f in (1, 2, 3):
        form(f)
        for nm, az in (("front", 0), ("side", 90), ("back", 180), ("sideR", -90)):
            shoot(os.path.join(TILES, f"view_p{f}_{nm}.png"), az, (0, 0, 2.05 if f == 1 else 2.25), ortho=5.2 if f == 1 else 6.4, res=(640, 760), elev_deg=4)
if "rest" in SETS:
    pose("rest")
    form(1)
    for nm, az in (("front", 0), ("side", 90), ("back", 180)):
        shoot(os.path.join(TILES, f"rest_{nm}.png"), az, (0, 0, 2.0), ortho=5.4, res=(640, 760))
if "close" in SETS:
    pose(POSE)
    form(1)
    shoot(os.path.join(TILES, "close_head.png"), -22, (0.0, -0.05, 3.42), dist=4.2, lens=50, res=(900, 900), elev_deg=6)
    shoot(os.path.join(TILES, "close_chest.png"), -18, (0.0, -0.2, 2.55), dist=3.6, lens=50, res=(900, 900), elev_deg=4)
    shoot(os.path.join(TILES, "close_cape.png"), 140, (0.35, 0.6, 0.95), dist=4.6, lens=45, res=(900, 900), elev_deg=10)
    shoot(os.path.join(TILES, "close_sword.png"), -55, (-0.75, -0.35, 1.45), dist=4.6, lens=40, res=(900, 900), elev_deg=4)
    form(2)
    shoot(os.path.join(TILES, "close_p2chest.png"), -15, (0.0, -0.2, 2.6), dist=3.6, lens=50, res=(900, 900), elev_deg=4)
    form(3)
    shoot(os.path.join(TILES, "close_p3head.png"), -20, (0.0, -0.05, 3.55), dist=4.8, lens=50, res=(900, 900), elev_deg=6)
    form(1)
if "sil" in SETS:
    # 背光剪影（側面正交）：檢查披風下段排與排之間的透光縫
    pose(POSE)
    form(1)
    for l in LIGHTS:
        l.hide_render = True
    bl = light("AREA", (0.0, 9.0, 1.2), 9000, 8.0, (1, 1, 1), tgt=(0, 0, 1.2))
    gp.hide_render = True
    shoot(os.path.join(TILES, "sil_side.png"), 90, (0.0, 0.3, 1.6), ortho=4.6, res=(760, 760))
    bl.hide_render = True
    for l in LIGHTS:
        l.hide_render = False
    gp.hide_render = False
print("PREVIEW DONE", flush=True)
