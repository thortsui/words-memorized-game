"""回合制模式可愛角色（勇者／蝙蝠）共用的建模、骨架、動作與預覽工具。
由 build_cute_hero.py、build_cute_bat.py 匯入；只能在 Blender（背景模式）內執行。
座標約定：臉朝 -Y（glTF 匯出後 +Z）、角色左手在 +X、原點在腳底地面。
動作約定：旋轉一律用「骨架空間的 XYZ 尤拉角（度）」描述，再換算到各骨頭的本地四元數：
  X 正值＝直立的骨頭往前傾／下垂的肢體往後擺；Z 正值＝往角色左邊轉；Y 正值＝頂端往 +X 倒。
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion

PARTS = []


# ───────────────────────── 基本 ─────────────────────────
def reset_scene(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PARTS.clear()
    bpy.context.scene.render.fps = fps
    return bpy.context.scene


def srgb(h):
    """#RRGGBB（螢幕上看到的顏色）→ 線性 RGB。"""
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mat(name, color, rough=0.4, metal=0.0, glow=0.10, emit=None, emit_strength=1.0, alpha=1.0):
    """純色 Principled 材質。glow：用本身顏色加一點自發光，讓暗面不會髒（卡通感）。"""
    col = srgb(color) if isinstance(color, str) else color
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        e = srgb(emit) if isinstance(emit, str) else emit
        b.inputs["Emission Color"].default_value = (*e, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    elif glow > 0:
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = glow
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    return m


def sstep(a, b, x):
    """smoothstep：x 從 a 到 b 時 0→1（a 可大於 b）。"""
    if a == b:
        return 0.0 if x < a else 1.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def sph(theta_deg, phi_deg):
    """方向向量：theta 0＝正前方(-Y)，正值往 +X；phi＝仰角。"""
    a, p = math.radians(theta_deg), math.radians(phi_deg)
    return Vector((math.sin(a) * math.cos(p), -math.cos(a) * math.cos(p), math.sin(p)))


def finish(name, bm, mats, smooth=True, recalc=True):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        me.materials.append(m)
    PARTS.append(ob)
    return ob


def _rot_matrix(rot):
    if rot is None:
        return Matrix.Identity(4)
    if isinstance(rot, Matrix):
        return rot.to_4x4()
    if isinstance(rot, (Quaternion, Euler)):
        return rot.to_matrix().to_4x4()
    return Euler(rot, "XYZ").to_matrix().to_4x4()


def align(z_dir, y_hint=(0, -1, 0)):
    """回傳把本地 Z 對到 z_dir 的旋轉矩陣（本地 Y 盡量朝 y_hint）。"""
    z = Vector(z_dir).normalized()
    y = Vector(y_hint)
    y = y - z * y.dot(z)
    if y.length < 1e-5:
        y = Vector((1, 0, 0)) - z * z.x
    y.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()


# ───────────────────────── 形狀 ─────────────────────────
def ellipsoid(name, loc, scale, material, rot=None, segs=16, rings=10):
    if isinstance(scale, (int, float)):
        scale = (scale,) * 3
    bm = bmesh.new()
    M = Matrix.Translation(Vector(loc)) @ _rot_matrix(rot) @ Matrix.Diagonal((*scale, 1))
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0, matrix=M)
    return finish(name, bm, material)


def lathe(name, profile, material, segs=24, sx=1.0, sy=1.0, center=(0, 0, 0), xform=None, smooth=True):
    """沿 Z 軸旋轉成形。profile：[(半徑, z)]，半徑 0 表示收成一個點。"""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((math.cos(2 * math.pi * j / segs) * r * sx, math.sin(2 * math.pi * j / segs) * r * sy, z)) for j in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            k = (j + 1) % segs
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[k], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[j], a[k], b[0]))
            else:
                bm.faces.new((a[j], a[k], b[k], b[j]))
    M = Matrix.Translation(Vector(center)) @ (xform.to_4x4() if xform is not None else Matrix.Identity(4))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    return finish(name, bm, material, smooth=smooth)


def sweep(name, pts, radii, material, segs=10, up=None, cap=True, smooth=True):
    """沿折線掃出管狀／尖刺。radii：單一半徑，或每點一個「半徑 / (法線向半徑, 副法線向半徑)」的 list；0 表示收尖。"""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    if not isinstance(radii, list):
        radii = [radii] * n
    tan = []
    for i in range(n):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tan.append(t.normalized())
    nrm = Vector(up) if up is not None else Vector((0, 0, 1))
    nrm = nrm - tan[0] * nrm.dot(tan[0])
    if nrm.length < 1e-4:
        nrm = Vector((1, 0, 0)) - tan[0] * tan[0].x
    nrm.normalize()
    bm = bmesh.new()
    rings = []
    for i in range(n):
        nrm = nrm - tan[i] * nrm.dot(tan[i])
        nrm.normalize()
        bn = tan[i].cross(nrm)
        r = radii[i]
        rn, rb = (r if isinstance(r, (list, tuple)) else (r, r))
        if rn <= 1e-6 and rb <= 1e-6:
            rings.append([bm.verts.new(pts[i])])
        else:
            rings.append([bm.verts.new(pts[i] + nrm * math.cos(2 * math.pi * j / segs) * rn + bn * math.sin(2 * math.pi * j / segs) * rb) for j in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            k = (j + 1) % segs
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[k], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[j], a[k], b[0]))
            else:
                bm.faces.new((a[j], a[k], b[k], b[j]))
    if cap:
        for ring in (rings[0], rings[-1]):
            if len(ring) > 2:
                bm.faces.new(ring)
    return finish(name, bm, material, smooth=smooth)


def torus(name, center, R, r, material, segs=24, rsegs=8, rot=None, sx=1.0, sy=1.0):
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        c = Vector((math.cos(a) * R * sx, math.sin(a) * R * sy, 0))
        out = Vector((math.cos(a), math.sin(a), 0))
        rings.append([bm.verts.new(c + out * math.cos(2 * math.pi * j / rsegs) * r + Vector((0, 0, 1)) * math.sin(2 * math.pi * j / rsegs) * r) for j in range(rsegs)])
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % segs]
        for j in range(rsegs):
            k = (j + 1) % rsegs
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ _rot_matrix(rot), verts=bm.verts[:])
    return finish(name, bm, material)


def surface(name, fn, nu, nv, materials, mat_fn=None):
    """參數曲面：fn(u, v)→座標；nu、nv 可為分段數或明確的參數 list；mat_fn(i, j)→材質索引。"""
    bm = bmesh.new()
    us = nu if isinstance(nu, (list, tuple)) else [i / nu for i in range(nu + 1)]
    vs = nv if isinstance(nv, (list, tuple)) else [j / nv for j in range(nv + 1)]
    grid = [[bm.verts.new(fn(u, v)) for u in us] for v in vs]
    for j in range(len(vs) - 1):
        for i in range(len(us) - 1):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            if mat_fn:
                f.material_index = mat_fn(i, j)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    return finish(name, bm, materials)


class Ellip:
    """橢球表面定位（放五官用）。warp：可選的變形函式，建模與定位共用。"""

    def __init__(self, center, radii, warp=None):
        self.c = Vector(center)
        self.r = Vector(radii)
        self.warp = warp

    def _p(self, theta, phi):
        d = sph(theta, phi)
        return d / math.sqrt((d.x / self.r.x) ** 2 + (d.y / self.r.y) ** 2 + (d.z / self.r.z) ** 2)

    def pt(self, theta, phi, push=0.0):
        p = self._p(theta, phi)
        if self.warp:
            p = self.warp(p)
        return self.c + p + self.normal(theta, phi) * push

    def normal(self, theta, phi):
        p = self._p(theta, phi)
        return Vector((p.x / self.r.x ** 2, p.y / self.r.y ** 2, p.z / self.r.z ** 2)).normalized()

    def rot(self, theta, phi, roll=0.0):
        """把薄片的本地 -Y 對到表面法線、本地 Z 朝上；roll：繞法線轉（度）。"""
        q = self.normal(theta, phi).to_track_quat("-Y", "Z")
        if roll:
            q = q @ Quaternion((0, 1, 0), math.radians(roll))
        return q

    def patch(self, name, theta, phi, size, material, push=0.0, thick=0.012, roll=0.0, segs=14, rings=8):
        """貼在表面上的扁橢圓片（眼睛、腮紅…）。size＝(半寬, 半高)。"""
        return ellipsoid(name, self.pt(theta, phi, push), (size[0], thick, size[1]), material, rot=self.rot(theta, phi, roll), segs=segs, rings=rings)


# ───────────────────────── 蒙皮 ─────────────────────────
def skin(obs, bone):
    for ob in (obs if isinstance(obs, (list, tuple)) else [obs]):
        ob.vertex_groups.new(name=bone).add(range(len(ob.data.vertices)), 1.0, "REPLACE")
    return obs


def skin_fn(obs, fn):
    """fn(座標)→{骨頭: 權重}，自動正規化。"""
    for ob in (obs if isinstance(obs, (list, tuple)) else [obs]):
        for v in ob.data.vertices:
            ws = {b: w for b, w in fn(v.co).items() if w > 1e-4}
            tot = sum(ws.values())
            for b, w in ws.items():
                g = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
                g.add([v.index], w / tot, "REPLACE")
    return obs


def join_parts(name):
    for ob in PARTS:
        if not ob.vertex_groups:
            raise RuntimeError(f"零件 {ob.name} 沒有權重")
    bpy.ops.object.select_all(action="DESELECT")
    for o in PARTS:
        o.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.join()
    mesh = bpy.context.object
    mesh.name = name
    mesh.data.name = name
    PARTS.clear()
    return mesh


# ───────────────────────── 骨架與動作 ─────────────────────────
class Rig:
    def __init__(self, name):
        ad = bpy.data.armatures.new(name)
        self.ob = bpy.data.objects.new(name, ad)
        bpy.context.scene.collection.objects.link(self.ob)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = self.ob
        self.ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        self.eb = ad.edit_bones

    def bone(self, name, head, tail, parent=None):
        b = self.eb.new(name)
        b.head, b.tail, b.roll = Vector(head), Vector(tail), 0
        if parent:
            b.parent = self.eb[parent]
        return b

    def done(self):
        bpy.ops.object.mode_set(mode="OBJECT")
        self.names = [b.name for b in self.ob.data.bones]
        self.R = {b.name: b.matrix_local.to_3x3() for b in self.ob.data.bones}
        self.Rq = {n: m.to_quaternion() for n, m in self.R.items()}
        for pb in self.ob.pose.bones:
            pb.rotation_mode = "QUATERNION"
        self.ob.animation_data_create()
        return self

    def bind(self, mesh):
        mod = mesh.modifiers.new("Armature", "ARMATURE")
        mod.object = self.ob
        mesh.parent = self.ob

    def reset(self):
        for pb in self.ob.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)

    def action(self, name, poses, base=None, extra=None, loop=False):
        """pose-to-pose 動作。
        poses：[(影格, {骨頭: 規格})]；每個關鍵格所有骨頭都下 key，沒寫的骨頭用 base（站姿）或歸零。
        規格：(rx, ry, rz) 度，或 dict(r=旋轉, l=骨架空間位移, s=本地縮放)。
        extra：{骨頭: [(影格, 規格)]}，整條取代該骨頭的 key（做披風、頭的延遲跟隨用）。
        loop：首尾相同的循環動作，會在範圍外補一輪 key 讓接縫的切線連續。
        影格用 1 起算來寫，實際存成 0 起算（匯出後動畫時間從 0 秒開始，循環不會卡一格）。
        """
        base = base or {}
        tracks = {bn: [(f - 1, pose.get(bn, base.get(bn))) for f, pose in poses] for bn in self.names}
        for bn, ks in (extra or {}).items():
            tracks[bn] = [(f - 1, sp) for f, sp in ks]
        first, last = poses[0][0] - 1, poses[-1][0] - 1
        L = last - first
        act = bpy.data.actions.new(name)
        self.ob.animation_data.action = act
        self.reset()
        for bn, ks in tracks.items():
            pb = self.ob.pose.bones[bn]
            parsed = []
            for f, s in ks:
                if s is None:
                    parsed.append((f, (0, 0, 0), None, None))
                elif isinstance(s, dict):
                    parsed.append((f, s.get("r", (0, 0, 0)), s.get("l"), s.get("s")))
                else:
                    parsed.append((f, tuple(s), None, None))
            has_loc = any(p[2] is not None and any(abs(c) > 1e-9 for c in p[2]) for p in parsed)
            has_scl = any(p[3] is not None for p in parsed)
            if loop:
                parsed = [(f - L, r, l, s) for f, r, l, s in parsed[:-1]] + parsed + [(f + L, r, l, s) for f, r, l, s in parsed[1:]]
            prev = None
            rq, rinv = self.Rq[bn], self.R[bn].inverted()
            for f, r, l, s in parsed:
                q = rq.inverted() @ Euler([math.radians(a) for a in r], "XYZ").to_quaternion() @ rq
                if prev is not None and prev.dot(q) < 0:
                    q.negate()
                prev = q.copy()
                pb.rotation_quaternion = q
                pb.keyframe_insert("rotation_quaternion", frame=f)
                if has_loc:
                    pb.location = rinv @ Vector(l or (0, 0, 0))
                    pb.keyframe_insert("location", frame=f)
                if has_scl:
                    pb.scale = s or (1, 1, 1)
                    pb.keyframe_insert("scale", frame=f)
        act.use_frame_range = True
        act.frame_start, act.frame_end = first, last
        tr = self.ob.animation_data.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, int(first), act)
        st.action_frame_start, st.action_frame_end = first, last
        st.frame_start, st.frame_end = first, last
        tr.mute = True
        self.ob.animation_data.action = None
        self.reset()
        return act


def cyc(frames, period, amp, phase=0.0, offset=0.0, axis=1, step=2, start=1, base=(0, 0, 0)):
    """循環擺動的關鍵格（拍翅用）：每 step 格一個 key，該軸的值 = offset + amp*cos(2π(t/period - phase))。"""
    out = []
    f = start
    while f <= start + frames:
        r = list(base)
        r[axis] += offset + amp * math.cos(2 * math.pi * ((f - start) / period - phase))
        out.append((f, tuple(r)))
        f += step
    return out


def export_glb(rig, mesh, path):
    rig.reset()
    bpy.ops.object.select_all(action="DESELECT")
    rig.ob.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = rig.ob
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_yup=True, export_skins=True,
                              export_texcoords=False)


def tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.data.polygons)


# ───────────────────────── 預覽 ─────────────────────────
def setup_stage(ground=(0.42, 0.52, 0.48)):
    scene = bpy.context.scene
    bpy.ops.object.light_add(type="SUN", location=(3, -4, 6))
    sun = bpy.context.object
    sun.data.energy = 2.4
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-32))
    bpy.ops.object.light_add(type="SUN", location=(-3, 4, 3))
    rim = bpy.context.object
    rim.data.energy = 0.7
    rim.data.use_shadow = False
    rim.rotation_euler = (math.radians(-60), 0, math.radians(20))
    bpy.ops.mesh.primitive_plane_add(size=60)
    bpy.context.object.data.materials.append(mat("PreviewGround", ground, rough=0.95, glow=0))
    w = bpy.data.worlds.new("W")
    scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.80, 0.88, 1.0, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.lens = 50
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = 16
    except Exception:
        pass
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    cu = bpy.data.curves.new("Label", "FONT")
    cu.size = 0.042
    lab = bpy.data.objects.new("Label", cu)
    scene.collection.objects.link(lab)
    lab.parent = cam
    lab.data.materials.append(mat("LabelInk", (0.01, 0.01, 0.02), rough=1, glow=0))
    try:
        lab.visible_shadow = False
    except Exception:
        pass
    return cam, lab


def aim(cam, pos, target):
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()


def shot(cam, lab, text, pos, target, res, path):
    scene = bpy.context.scene
    aim(cam, pos, target)
    scene.render.resolution_x, scene.render.resolution_y = res
    half_w = 0.36 if res[0] >= res[1] else 0.36 * res[0] / res[1]
    half_h = 0.36 if res[1] >= res[0] else 0.36 * res[1] / res[0]
    lab.data.body = text
    lab.location = (-half_w + 0.02, half_h - 0.06, -1.0)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    os.remove(path)
    return a.reshape(h, w, 4)


def save_grid(rows, out):
    """rows：[[影像陣列…]]（由上到下、由左到右）→ 存成一張 JPEG。"""
    ch, cw = rows[0][0].shape[:2]
    W, H = cw * max(len(r) for r in rows), ch * len(rows)
    canvas = np.ones((H, W, 4), np.float32)
    for j, row in enumerate(rows):
        y0 = H - (j + 1) * ch
        for i, a in enumerate(row):
            canvas[y0:y0 + ch, i * cw:(i + 1) * cw] = a
    img = bpy.data.images.new("sheet", W, H, alpha=False)
    img.pixels.foreach_set(canvas.ravel())
    img.filepath_raw = out
    img.file_format = "JPEG"
    img.save()
    bpy.data.images.remove(img)


def render_previews(rig, name, preview_dir, views, action_frames, action_cam, view_res=(480, 560), cell=(380, 340),
                    pose_action="Idle", per_action_cam=None, strip_dir=None, per_row=2, only=None):
    """轉身圖 <name>_sheet.jpg 與動作表 <name>_actions.jpg。
    views：[(標籤, 相機位置, 目標)]；action_frames：{動作: [影格…]}；action_cam：(位置, 目標)。
    strip_dir：另外把每個動作存成單獨一條（檢查用）；only：只渲染指定動作（不輸出總表）。"""
    scene = bpy.context.scene
    cam, lab = setup_stage()
    tmp = os.path.join(preview_dir, f"_tmp_{name}.png")
    arm = rig.ob
    if not only:
        arm.animation_data.action = bpy.data.actions[pose_action]
        scene.frame_set(0)
        row = [shot(cam, lab, label, pos, tgt, view_res, tmp) for label, pos, tgt in views]
        save_grid([row], os.path.join(preview_dir, f"{name}_sheet.jpg"))
    strips = []
    cam_env = os.environ.get("CUTE_CAM")  # 檢查用：x,y,z,tx,ty,tz 覆蓋動作相機
    if cam_env:
        c = [float(x) for x in cam_env.split(",")]
        action_cam, per_action_cam = (c[:3], c[3:]), None
    only_frames = {}
    for o in (only or []):  # "Slash" 或 "Slash:7:11:14"
        nm, *fr = o.split(":")
        only_frames[nm] = [int(x) for x in fr]
    for an, frames in action_frames.items():
        if only and an not in only_frames:
            continue
        frames = only_frames.get(an) or frames
        rig.reset()
        arm.animation_data.action = bpy.data.actions[an]
        pos, tgt = (per_action_cam or {}).get(an, action_cam)
        cells = []
        for f in frames:
            scene.frame_set(f - 1)
            cells.append(shot(cam, lab, f"{an}  f{f}", pos, tgt, cell, tmp))
        strips.append(cells)
        if strip_dir:
            save_grid([cells], os.path.join(strip_dir, f"{name}_{an}.jpg"))
    if not only:
        rows = []
        for i in range(0, len(strips), per_row):
            r = []
            for s in strips[i:i + per_row]:
                r += s
            rows.append(r)
        save_grid(rows, os.path.join(preview_dir, f"{name}_actions.jpg"))
    arm.animation_data.action = None
    rig.reset()
    scene.frame_set(0)
