"""v3 sentinel 預覽渲染（Blender 內）：與參考圖同視角的全身、正／側／背／3/4、近景特寫、材質抽查、動作連拍。
光：左上主光＋弱冷色補光＋背光，背景 #3a3a38（審查方法 §7）。輸出 PNG 到 tiles，再由 v3_sentinel_sheet.py 拼圖。"""
import bpy, os, math
from mathutils import Vector
import v3_sentinel_util as VL


def lin(hx):
    hx = hx.lstrip("#")
    return tuple(((int(hx[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4))


def setup(h):
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*lin("#3a3a38"), 1); bg.inputs[1].default_value = 0.55
    try:
        sc.eevee.use_shadows = True
        sc.eevee.use_gtao = True
        sc.eevee.taa_render_samples = 32
    except Exception:
        pass
    s = h / 1.8

    def area(loc, energy, size, color=(1, 1, 1)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.data.energy = energy; l.data.size = size; l.data.color = color
        d = Vector((0, 0, h * 0.55)) - l.location
        l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return l
    area((-2.6 * s, -3.0 * s, 3.6 * s), 210 * s * s, 2.2 * s, (1.0, 0.98, 0.95))     # 左上主光（從正面看在左）
    area((3.2 * s, -2.4 * s, 1.5 * s), 45 * s * s, 3.5 * s, (0.80, 0.88, 1.0))       # 冷色補光
    area((1.0 * s, 3.6 * s, 3.2 * s), 170 * s * s, 2.0 * s, (0.9, 0.95, 1.0))        # 背光（輪廓）
    bpy.ops.mesh.primitive_plane_add(size=60)
    gp = bpy.context.object
    gm = bpy.data.materials.new("PreviewGround"); gm.use_nodes = True
    b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*lin("#2c2c2a"), 1); b.inputs["Roughness"].default_value = 0.95
    gp.data.materials.append(gm)
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    sc.camera = cam
    sc.render.image_settings.file_format = "PNG"
    return cam


def aim(cam, az, tgt, dist, elev=0.0, lens=50, pitch_tgt=None):
    a = math.radians(az)
    cam.location = Vector((math.sin(a) * dist + tgt.x, -math.cos(a) * dist + tgt.y, tgt.z + elev))
    d = (pitch_tgt or tgt) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


def shot(cam, path, res):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def pose(arm, action, frame):
    ad = arm.animation_data
    if action and ad and action in bpy.data.actions:
        ad.action = bpy.data.actions[action]
        bpy.context.scene.frame_set(frame)
    else:
        if ad:
            ad.action = None
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()


def bpos(arm, name, tail=False):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def render_all(arm, mesh, p2objs, h, tiles, anim=True, only=None):
    os.makedirs(tiles, exist_ok=True)
    for f in os.listdir(tiles):
        if f.endswith(".png"):
            os.remove(os.path.join(tiles, f))
    cam = setup(h)
    P = os.path.join
    idle = "Idle" if anim else None
    if not only:
        # 一階：與 p1 同視角（3/4，相機在角色右前方 35°）、正／側／背／3/4
        VL.show_p2(p2objs, False)
        pose(arm, idle, 0)
        tgt = Vector((0, -0.05 * h, 0.50 * h))
        for name, az, el in (("cmp_p1", -35, 0.10), ("v_front", 0, 0.05), ("v_side", -90, 0.05), ("v_back", 180, 0.08), ("v_34", 35, 0.05)):
            aim(cam, az, tgt, 1.85 * h, elev=el * h, lens=50)
            shot(cam, P(tiles, name + ".png"), (720, 960))
        # 二階：與 p2 同視角（近正面、略俯）
        VL.show_p2(p2objs, True)
        pose(arm, "IdleAggro" if anim else None, 0)
        for name, az, el in (("cmp_p2", -18, 0.10), ("v_p2_34", 35, 0.05), ("v_p2_back", 160, 0.10)):
            aim(cam, az, Vector((0, -0.04 * h, 0.55 * h)), 2.15 * h, elev=el * h, lens=50)
            shot(cam, P(tiles, name + ".png"), (720, 960))
        # 近景特寫（一階 Idle）
        VL.show_p2(p2objs, False)
        pose(arm, idle, 0)
        head = bpos(arm, "Head"); hl = bpos(arm, "ForearmL"); hr = bpos(arm, "HandR"); hips = bpos(arm, "Hips")
        sp2 = bpos(arm, "Spine2"); tip = bpos(arm, "Tip_Weapon")
        wpn = bpos(arm, "Weapon")
        shots = [("close_hat", -25, head + Vector((0, 0, 0.06 * h)), 0.75 * h, 0.04 * h),
                 ("close_hatfront", 0, head + Vector((0, 0, 0.03 * h)), 0.55 * h, -0.02 * h),
                 ("close_armL", 55, hl, 0.62 * h, 0.03 * h),
                 ("close_armR", -60, bpos(arm, "ForearmR"), 0.62 * h, 0.03 * h),
                 ("close_waist", -20, hips + Vector((0, 0, -0.06 * h)), 0.85 * h, 0.02 * h),
                 ("close_hem", -10, Vector((0, -0.05 * h, 0.17 * h)), 0.55 * h, 0.05 * h),
                 ("close_door", 165, sp2 + Vector((0, 0.1 * h, -0.10 * h)), 0.95 * h, 0.05 * h),
                 ("close_doorlow", 150, sp2 + Vector((0.03 * h, 0.12 * h, -0.36 * h)), 0.45 * h, 0.06 * h),
                 ("close_halberd", -75, tip.lerp(wpn, 0.25), 0.62 * h, 0.12 * h),
                 ("close_pauld", -40, bpos(arm, "UpperArmR") + Vector((0, 0, 0.03 * h)), 0.40 * h, 0.06 * h),
                 ("close_legs", -20, Vector((0, -0.05 * h, 0.22 * h)), 0.8 * h, 0.02 * h)]
        for name, az, t, dist, el in shots:
            aim(cam, az, t, dist, elev=el, lens=50)
            shot(cam, P(tiles, name + ".png"), (800, 800))
        # 二階特寫：心臟、背後根
        VL.show_p2(p2objs, True)
        pose(arm, "IdleAggro" if anim else None, 0)
        aim(cam, -15, bpos(arm, "Spine2") + Vector((0, -0.05 * h, 0.05 * h)), 0.6 * h, elev=0.02 * h)
        shot(cam, P(tiles, "close_p2heart.png"), (800, 800))
        aim(cam, -30, bpos(arm, "WeaponTip") if "WeaponTip" in arm.pose.bones else bpos(arm, "Tip_Weapon"), 0.7 * h, elev=0.1 * h)
        shot(cam, P(tiles, "close_p2halberd.png"), (800, 800))
        VL.show_p2(p2objs, False)
    if anim:
        try:
            bpy.context.scene.eevee.taa_render_samples = 12
        except Exception:
            pass
        VL.render_actions(arm, h, tiles, cam, p2objs, n=8, only=only, p2_from=1.13, width=1.75, tgt=Vector((0, -0.12 * h, 0.48 * h)), elev=0.18)
    pose(arm, None, 0)
