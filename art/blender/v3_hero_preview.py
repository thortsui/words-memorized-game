"""單字魂 v3 主角：預覽渲染（與參考圖同視角的棚拍、近拍、暗場、動作連拍）。
可由 v3_hero_build.py 直接呼叫，也可單獨對存好的 .blend 重拍：
  blender --background art/blender/source/v3_hero_knight.blend --python v3_hero_preview.py -- [--noactions] [--only A,B] [--out DIR]
圖塊寫到 art/v3/tmp/hero/tiles/，再用 v3_hero_sheet.py 拼成 art/blender/preview/v3_hero_*.jpg。
"""
import bpy, os, sys, math
from mathutils import Vector

H = 1.817
STUDIO_BG = (0.578, 0.578, 0.578)        # #c8c8c8（線性）


def _clear_preview():
    for o in list(bpy.data.objects):
        if o.get("pv"):
            bpy.data.objects.remove(o, do_unlink=True)


def _light(kind, loc, energy, size, color=(1, 1, 1), target=(0, 0, H * 0.55)):
    bpy.ops.object.light_add(type=kind, location=loc)
    l = bpy.context.object
    l["pv"] = 1
    l.data.energy = energy
    if kind == "AREA":
        l.data.size = size
    l.data.color = color
    d = Vector(target) - l.location
    l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l


def studio(dark=False):
    sc = bpy.context.scene
    _clear_preview()
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.get("PV") or bpy.data.worlds.new("PV")
    sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    if dark:
        bg.inputs[0].default_value = (0.012, 0.013, 0.016, 1); bg.inputs[1].default_value = 1.0
        _light("AREA", (-1.6, -2.4, 3.0), 140, 2.0, (1.0, 0.92, 0.82))           # 暖色火光主光（前方）
        _light("AREA", (1.4, 2.6, 2.4), 260, 1.5, (0.55, 0.65, 1.0))             # 冷色輪廓光（後方）
        _light("AREA", (-2.4, 1.8, 1.2), 60, 2.0, (0.7, 0.75, 0.9))
        gc = (0.02, 0.02, 0.022)
    else:
        bg.inputs[0].default_value = (*STUDIO_BG, 1); bg.inputs[1].default_value = 0.55
        _light("AREA", (0.3, -0.8, 3.4), 260, 2.4, (1.0, 0.98, 0.95), target=(0, 0, H * 0.7))   # 柔和頂光
        _light("AREA", (-2.2, -3.0, 1.8), 120, 3.0, (1.0, 0.97, 0.93))
        _light("AREA", (2.6, -1.8, 1.4), 70, 3.0, (0.92, 0.95, 1.0))
        _light("AREA", (0.5, 3.2, 2.2), 110, 3.0, (0.95, 0.97, 1.0))
        gc = (0.30, 0.30, 0.30)
    bpy.ops.mesh.primitive_plane_add(size=40)
    gp = bpy.context.object; gp["pv"] = 1
    gm = bpy.data.materials.get("PVground") or bpy.data.materials.new("PVground")
    gm.use_nodes = True
    b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*gc, 1); b.inputs["Roughness"].default_value = 0.95
    gp.data.materials.append(gm)
    cam = bpy.data.objects.get("PVcam")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.object; cam.name = "PVcam"
    sc.camera = cam
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.eevee.taa_render_samples = 32
        sc.eevee.use_shadows = True
    except Exception:
        pass
    return cam


def aim(cam, az, target, dist, elev=0.0, lens=50, ortho=None):
    a = math.radians(az)
    cam.location = Vector((math.sin(a) * dist, -math.cos(a) * dist, target[2] + elev))
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens
    cam.data.clip_start = 0.02


def shot(path, res):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def pose(arm, act_name, frame=0):
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.get(act_name)
    ad.action = act
    if act is None:
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.scene.frame_set(frame)


def render_all(arm, tiles, actions=True, only=None):
    os.makedirs(tiles, exist_ok=True)
    cam = studio(False)
    pose(arm, "_RefPose", 1)
    # 與參考圖相同的取景：正交、畫面高 = 1.087H、中心在 0.513H（參考圖 726px 中人物 668px）
    oz = H * 0.513
    for label, az in (("front", 0), ("side", 90), ("back", 180)):
        aim(cam, az, (0, 0, oz), 6.0, 0.0, ortho=H * 1.087)
        shot(os.path.join(tiles, f"view_{label}.png"), (560, 800))
    for label, az in (("threeq", -35), ("threeqback", 150)):
        aim(cam, az, (0, 0, H * 0.50), H * 2.7, H * 0.06, lens=50)
        shot(os.path.join(tiles, f"view_{label}.png"), (560, 800))
    # 近拍（約 0.3H 距離感）
    closes = [("helm", -28, (0.0, -0.02, 1.68), 0.62, 0.02),
              ("lshoulder", 35, (0.16, 0.0, 1.45), 0.75, 0.05),
              ("chest", -18, (0.0, -0.05, 1.18), 0.95, 0.03),
              ("hem", 15, (0.0, -0.05, 0.72), 0.95, 0.05),
              ("capeback", 165, (0.0, 0.15, 0.95), 1.55, 0.15),
              ("boots", 25, (0.0, -0.08, 0.20), 0.85, 0.12),
              ("sword", -60, (-0.42, -0.05, 0.55), 1.30, 0.05)]
    for label, az, tg, dist, el in closes:
        aim(cam, az, tg, dist, el, lens=50)
        shot(os.path.join(tiles, f"close_{label}.png"), (520, 520))
    # 暗場（遊戲背景）：過肩視角與正面
    studio(True)
    pose(arm, "Idle", 0)
    aim(cam, 160, (0, 0.2, H * 0.62), H * 1.9, H * 0.42, lens=40)
    shot(os.path.join(tiles, "dark_overshoulder.png"), (640, 640))
    aim(cam, -25, (0, 0, H * 0.52), H * 2.6, H * 0.05, lens=50)
    shot(os.path.join(tiles, "dark_front.png"), (480, 640))
    pose(arm, "_RefPose", 1)
    aim(cam, 180, (0, 0, H * 0.52), H * 2.6, H * 0.05, lens=50)
    shot(os.path.join(tiles, "dark_back.png"), (480, 640))
    if actions:
        render_actions(arm, tiles, only=only)
    arm.animation_data.action = None


def render_actions(arm, tiles, n=8, only=None):
    cam = studio(False)
    try:
        bpy.context.scene.eevee.taa_render_samples = 12
    except Exception:
        pass
    ad = arm.animation_data
    names = [t.name for t in ad.nla_tracks if not t.name.startswith("_")]
    for r, name in enumerate(names):
        if only and name not in only:
            continue
        act = bpy.data.actions[name]
        ad.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        for k in range(n):
            f = int(round(f0 + (f1 - f0) * k / (n - 1)))
            bpy.context.scene.frame_set(f)
            aim(cam, -32, (0, -H * 0.10, H * 0.50), H * 2.25, H * 0.22, lens=50)
            shot(os.path.join(tiles, f"act_{r:02d}_{name}_{k}_f{f:03d}.png"), (360, 360))
    ad.action = None


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(root, "art", "v3", "tmp", "hero", "tiles")
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    if "--actionsonly" in argv:
        render_actions(arm, out, only=only)
    else:
        render_all(arm, out, actions="--noactions" not in argv, only=only)
    print("PREVIEW DONE", flush=True)
