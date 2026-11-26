"""魂系人形角色共用函式庫（Blender 4.2 背景模式）。

內容：
  1. 幾何產生器：以參數曲面（grid／shell／tube）產生盔甲分件，自帶 UV（公尺為單位）、邊框捲邊、銳邊標記
  2. Body：人體比例與關節位置、軀幹與四肢的表面函式（盔甲 = 身體表面往外偏移的曲面片）
  3. 骨架：標準人形 Root/Hips/Spine/Spine2/Neck/Head、左右 Shoulder/UpperArm/Forearm/Hand、Thigh/Shin/Foot、Weapon、布料鏈
  4. 蒙皮：程序化權重（剛體分件＋關節處平滑混合）
  5. 動作：高階姿勢參數 → 單調三次插值 → 自製 FK／兩節 IK（腳掌定地、雙手握持）→ 逐格寫入四元數
     布料鏈用 Verlet 擺錘模擬自動產生次級動作
  6. 材質：CC0 掃描貼圖（box 投影）＋鏽蝕／磨損／污垢／青苔遮罩 → Cycles 烘焙成每組一張 baseColor／ORM／normal
  7. 匯出 GLB（NLA_TRACKS）與存 .blend

座標：+Z 向上、臉朝 -Y、角色左手在 +X。骨頭名稱不用 "."（three.js 會去掉），左右以 L／R 結尾。
"""
import bpy, bmesh, math, os, sys, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion

X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1)); FWD = Vector((0, -1, 0))
HERE = os.path.dirname(os.path.abspath(__file__))
TEXDIR = os.path.join(HERE, "textures")


def V(*a):
    return Vector(a)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def tab_eval(tab, t):
    """單調三次（非等距）查表。tab：[(t, v1, v2, ...)]，回傳 list。"""
    n = len(tab)
    if t <= tab[0][0]:
        return list(tab[0][1:])
    if t >= tab[-1][0]:
        return list(tab[-1][1:])
    k = 0
    while tab[k + 1][0] < t:
        k += 1
    t0, t1 = tab[k][0], tab[k + 1][0]
    h = t1 - t0
    s = (t - t0) / h
    out = []
    for c in range(1, len(tab[0])):
        y0, y1 = tab[k][c], tab[k + 1][c]
        d = (y1 - y0) / h
        if k > 0:
            dp = (y0 - tab[k - 1][c]) / (t0 - tab[k - 1][0])
            m0 = 0.0 if dp * d <= 0 else (dp + d) / 2
        else:
            m0 = d
        if k < n - 2:
            dn = (tab[k + 2][c] - y1) / (tab[k + 2][0] - t1)
            m1 = 0.0 if dn * d <= 0 else (dn + d) / 2
        else:
            m1 = d
        if d != 0:
            lim = 3 * abs(d)
            m0 = math.copysign(min(abs(m0), lim), m0); m1 = math.copysign(min(abs(m1), lim), m1)
        s2, s3 = s * s, s * s * s
        out.append((2 * s3 - 3 * s2 + 1) * y0 + (s3 - 2 * s2 + s) * h * m0 + (-2 * s3 + 3 * s2) * y1 + (s3 - s2) * h * m1)
    return out


def E(x=0.0, y=0.0, z=0.0):
    """模型軸歐拉角（度）→ 四元數。x 正＝前傾、y 正＝向左側傾、z 正＝向左轉。順序：先轉 z、再 x、再 y。"""
    return Quaternion(Z, math.radians(z)) @ Quaternion(X, math.radians(x)) @ Quaternion(Y, math.radians(y))


def _basis(a, b):
    a = a.normalized()
    b = b - a * b.dot(a)
    if b.length < 1e-6:
        b = a.orthogonal()
    b.normalize()
    c = a.cross(b)
    return Matrix((a, b, c)).transposed()


def frame_rot(a0, b0, a, b):
    """把（a0,b0）座標架轉到（a,b）座標架的旋轉。"""
    return (_basis(a, b) @ _basis(a0, b0).transposed()).to_quaternion()


def rot_min(a, b):
    return a.normalized().rotation_difference(b.normalized())


def reset_scene(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    return sc


# ---------------------------------------------------------------- 表面函式
class Surf:
    """沿軸線的橢圓（超橢圓）截面表面。ang=0 朝前（-Y 側）、90 朝外（左側 +X／手臂外側）。
    tab：[(t, rx, ry, du, dv)]，t 為沿軸距離（公尺）。"""

    def __init__(self, o, a, tab, v=FWD, exp=2.0):
        self.o = o.copy(); self.a = a.normalized()
        v = v - self.a * v.dot(self.a)
        self.v = v.normalized()
        u = self.v.cross(self.a)
        if u.x < -0.3:
            u = -u
        self.u = u
        self.tab = tab
        self.exp = exp

    def row(self, t):
        return tab_eval(self.tab, t)

    def center(self, t):
        rx, ry, du, dv = self.row(t)
        return self.o + self.a * t + self.u * du + self.v * dv

    def pt(self, t, ang, off=0.0):
        rx, ry, du, dv = self.row(t)
        s, c = math.sin(math.radians(ang)), math.cos(math.radians(ang))
        if self.exp != 2.0:
            p = 2.0 / self.exp
            s = math.copysign(abs(s) ** p, s); c = math.copysign(abs(c) ** p, c)
        return self.o + self.a * t + self.u * ((rx + off) * s + du) + self.v * ((ry + off) * c + dv)

    def nrm(self, t, ang):
        return (self.pt(t, ang, 0.01) - self.pt(t, ang, 0.0)).normalized()


# ---------------------------------------------------------------- 幾何
class Builder:
    def __init__(self):
        self.parts = []

    @staticmethod
    def _weights(w, co):
        if isinstance(w, str):
            return {w: 1.0}
        if isinstance(w, dict):
            return w
        return w(co)

    def add_mesh(self, name, bm, mat, w, sharp=35.0, texel=1.0, stacked=False):
        bm.normal_update()
        lim = math.radians(sharp)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < lim
        for f in bm.faces:
            f.smooth = True
        uv = bm.loops.layers.uv.active
        if stacked:
            du = -50.0
        else:
            self.uv_slot = getattr(self, "uv_slot", 0) + 1
            du = self.uv_slot * 20.0
        for f in bm.faces:
            for l in f.loops:
                q = l[uv].uv * texel
                q.x += du
                l[uv].uv = q
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        groups = {}
        for vtx in me.vertices:
            ws = self._weights(w, vtx.co)
            tot = sum(ws.values()) or 1.0
            for bn, val in ws.items():
                if val <= 1e-4:
                    continue
                g = groups.get(bn)
                if g is None:
                    g = groups[bn] = ob.vertex_groups.new(name=bn)
                g.add([vtx.index], val / tot, "REPLACE")
        ob["matkey"] = mat
        self.parts.append(ob)
        return ob

    HIRES = True

    def grid(self, name, nu, nv, fn, mat, w, inside, closed_u=False, closed_v=False, cap0=False, cap1=False,
             rim=0.0, sharp=35.0, texel=1.0, stack_uv=False, holes=None, vmul=1):
        """參數曲面網格。fn(u,v)->Vector，u、v 在 0~1。inside：位於曲面背面的參考點（或點列），用來決定法線朝外。
        holes(i,j)->True 的面不建（布料破洞）。
        細分：繞一圈的曲面（closed_u）段數 10–13 時自動加倍（細小的手指、鎖鏈不加）（holes 依原本的格子對應），vmul 可另外加倍 v 方向。"""
        fu = 2 if (closed_u and 10 <= nu < 14 and not stack_uv and Builder.HIRES) else 1
        fv = vmul if Builder.HIRES else 1
        if fu > 1 or fv > 1:
            nu, nv = nu * fu, nv * fv
            if holes:
                h0 = holes
                holes = lambda i, j: h0(i // fu, j // fv)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("atlas")
        nru = nu if closed_u else nu + 1
        nrv = nv if closed_v else nv + 1
        P = [[Vector(fn(i / nu, j / nv)) for j in range(nrv)] for i in range(nru)]
        VV = [[bm.verts.new(P[i][j]) for j in range(nrv)] for i in range(nru)]
        ul = [0.0] * (nu + 1)
        for i in range(nu):
            ul[i + 1] = ul[i] + sum((P[(i + 1) % nru][j] - P[i][j]).length for j in range(nrv)) / nrv
        vl = [0.0] * (nv + 1)
        for j in range(nv):
            vl[j + 1] = vl[j] + sum((P[i][(j + 1) % nrv] - P[i][j]).length for i in range(nru)) / nru
        if stack_uv:
            su, sv = (ul[-1] or 1), (vl[-1] or 1)
            ul = [x / su * 0.02 for x in ul]; vl = [x / sv * 0.02 for x in vl]
        for i in range(nu):
            for j in range(nv):
                if holes and holes(i, j):
                    continue
                i1, j1 = (i + 1) % nru, (j + 1) % nrv
                vs = (VV[i][j], VV[i1][j], VV[i1][j1], VV[i][j1])
                try:
                    f = bm.faces.new(vs)
                except ValueError:
                    continue
                for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    l[uvl].uv = (ul[a], vl[b])
        if closed_u and (cap0 or cap1):
            for flag, j in ((cap0, 0), (cap1, nrv - 1)):
                if not flag:
                    continue
                ring = [VV[i][j] for i in range(nru)]
                c = sum((v.co for v in ring), Vector()) / len(ring)
                e1 = (ring[0].co - c).normalized()
                nrm = e1.cross((ring[len(ring) // 4].co - c)).normalized()
                e2 = nrm.cross(e1)
                try:
                    f = bm.faces.new(ring)
                except ValueError:
                    continue
                rr = max((v.co - c).length for v in ring) + 0.01
                cu = ul[-1] + rr + 0.02
                cv = rr if j == 0 else 3 * rr + 0.02
                for l in f.loops:
                    d = l.vert.co - c
                    l[uvl].uv = (cu + d.dot(e1), cv + d.dot(e2))
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        ins = inside if isinstance(inside, (list, tuple)) else [inside]
        s = 0.0
        for f in bm.faces:
            c = f.calc_center_median()
            ref = min(ins, key=lambda q: (q - c).length_squared)
            s += f.normal.dot(c - ref) * f.calc_area()
        if s < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.normal_update()
        if rim > 0:
            self._rim(bm, uvl, rim)
        ob = self.add_mesh(name, bm, mat, w, sharp=sharp, texel=texel, stacked=stack_uv)
        if rim > 0:
            ob["rim"] = rim
        return ob

    @staticmethod
    def _rim(bm, uvl, rim):
        bm.normal_update()
        border = [e for e in bm.edges if len(e.link_faces) == 1]
        if not border:
            return
        vuv = {}
        for e in border:
            for l in e.link_faces[0].loops:
                if l.vert in e.verts:
                    vuv[l.vert] = l[uvl].uv.copy()
        vn = {v: v.normal.copy() for e in border for v in e.verts}
        ret = bmesh.ops.extrude_edge_only(bm, edges=border)
        newv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
        newf = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
        src = {}
        for f in newf:
            old = [v for v in f.verts if v in vn]
            for v in f.verts:
                if v not in vn and old:
                    src[v] = min(old, key=lambda q: (q.co - v.co).length_squared)
        for v in newv:
            o = src.get(v)
            if o is not None:
                v.co = o.co - vn[o] * rim
        for f in newf:
            for l in f.loops:
                o = l.vert if l.vert in vn else src.get(l.vert)
                if o in vuv:
                    l[uvl].uv = vuv[o]

    def shell(self, name, surf, t0, t1, a0, a1, nu, nv, mat, w, off=0.01, **kw):
        """身體表面往外偏移的曲面片。t0／t1 可為 u 的函式（讓邊緣高低起伏），off 可為 (u,v,ang,t) 的函式。"""
        closed = abs((a1 - a0) - 360) < 1e-6

        def tt(u):
            return (t0(u) if callable(t0) else t0), (t1(u) if callable(t1) else t1)

        def fn(u, v):
            ang = a0 + (a1 - a0) * u
            ta, tb = tt(u)
            t = ta + (tb - ta) * v
            o = off(u, v, ang, t) if callable(off) else off
            return surf.pt(t, ang, o)
        ta, tb = tt(0.5)
        inside = [surf.center(lerp(ta, tb, k / 6)) for k in range(7)]
        return self.grid(name, nu, nv, fn, mat, w, inside, closed_u=closed, **kw)

    def tube(self, name, pts, radii, segs, mat, w, cap=True, exp=2.0, flat=None, up=Z, **kw):
        """沿折線的管狀體（樹根、握柄、劍刃…）。radii：每點半徑或 (rx, ry)。flat：截面的參考「寬」方向。"""
        n = len(pts)
        frames = []
        prev = None
        for k in range(n):
            a = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
            if flat is not None:
                ref = flat
            elif prev is not None:
                ref = prev
            else:
                ref = up if abs(a.dot(up)) < 0.9 else X
            e1 = ref - a * ref.dot(a)
            if e1.length < 1e-6:
                e1 = a.orthogonal()
            e1.normalize()
            prev = e1
            frames.append((e1, a.cross(e1)))

        def fn(u, v):
            x = v * (n - 1)
            k = min(int(x), n - 2); s = x - k
            p = pts[k].lerp(pts[k + 1], s)
            e1 = frames[k][0].lerp(frames[k + 1][0], s).normalized()
            e2 = frames[k][1].lerp(frames[k + 1][1], s).normalized()
            ra, rb = radii[k], radii[k + 1]
            if not isinstance(ra, (tuple, list)):
                ra = (ra, ra)
            if not isinstance(rb, (tuple, list)):
                rb = (rb, rb)
            rx, ry = lerp(ra[0], rb[0], s), lerp(ra[1], rb[1], s)
            sn, cs = math.sin(2 * math.pi * u), math.cos(2 * math.pi * u)
            if exp != 2.0:
                p2 = 2.0 / exp
                sn = math.copysign(abs(sn) ** p2, sn); cs = math.copysign(abs(cs) ** p2, cs)
            return p + e1 * (rx * cs) + e2 * (ry * sn)
        return self.grid(name, segs, n - 1, fn, mat, w, list(pts), closed_u=True, cap0=cap, cap1=cap, **kw)

    def ellipsoid(self, name, c, axes, radii, nu, nv, mat, w, v0=0.0, v1=1.0, dent=None, **kw):
        """橢球（可只取一段緯度當圓頂）。axes：(ex, ey, ez)，極軸為 ez，v=0 在極點。dent(d,u,v)->半徑倍率。"""
        ex, ey, ez = axes

        def fn(u, v):
            th = math.pi * lerp(v0, v1, v)
            ph = 2 * math.pi * u
            d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
            r = dent(d, u, v) if dent else 1.0
            return c + (ex * (d.x * radii[0]) + ey * (d.y * radii[1]) + ez * (d.z * radii[2])) * r
        if nv <= 8 and nu >= 16 and "vmul" not in kw:
            kw["vmul"] = 2
        return self.grid(name, nu, nv, fn, mat, w, c, closed_u=True, **kw)

    def rivets(self, name, pts, mat, w, r=0.006):
        """一批鉚釘（六角圓頂，兩圈），UV 疊在同一個小島上。pts：[(位置, 法線)]。"""
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("atlas")
        N = 6
        for p, nrm in pts:
            nrm = nrm.normalized()
            e1 = nrm.orthogonal().normalized(); e2 = nrm.cross(e1)
            ring = []; mid = []
            for k in range(N):
                a = 2 * math.pi / N * k
                d = e1 * math.cos(a) + e2 * math.sin(a)
                ring.append(bm.verts.new(p + d * r - nrm * (r * 0.3)))
                mid.append(bm.verts.new(p + d * r * 0.72 + nrm * r * 0.45))
            top = bm.verts.new(p + nrm * r * 0.72)
            for k in range(N):
                k1 = (k + 1) % N
                a0, a1 = 2 * math.pi / N * k, 2 * math.pi / N * (k + 1)
                c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
                f = bm.faces.new((ring[k], ring[k1], mid[k1], mid[k]))
                for l, q in zip(f.loops, ((c0, s0), (c1, s1), (c1 * .7, s1 * .7), (c0 * .7, s0 * .7))):
                    l[uvl].uv = (0.012 + q[0] * 0.01, 0.012 + q[1] * 0.01)
                f = bm.faces.new((mid[k], mid[k1], top))
                for l, q in zip(f.loops, ((c0 * .7, s0 * .7), (c1 * .7, s1 * .7), (0, 0))):
                    l[uvl].uv = (0.012 + q[0] * 0.01, 0.012 + q[1] * 0.01)
        return self.add_mesh(name, bm, mat, w, sharp=80, stacked=True)

    def mirror(self, ob, name=None):
        """沿 X 鏡射複製（左→右），骨頭群組 L↔R。"""
        me = ob.data.copy()
        bm = bmesh.new(); bm.from_mesh(me)
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
        nob = bpy.data.objects.new(name or ob.name + "_R", me)
        bpy.context.scene.collection.objects.link(nob)
        # 頂點群組存在 mesh 資料裡，複製後已經帶著；這裡只改名（L↔R）
        ren = []
        for g in nob.vertex_groups:
            n = g.name
            if n.endswith("L"):
                n = n[:-1] + "R"
            elif n.endswith("R"):
                n = n[:-1] + "L"
            ren.append((g, n))
            g.name = "__tmp_" + g.name
        for g, n in ren:
            g.name = n
        # 群組索引順序相同，頂點權重已隨 mesh 資料複製
        nob["matkey"] = ob["matkey"]
        self.parts.append(nob)
        return nob

    def mirror_only(self, obs):
        """只留鏡射後的版本（左右不對稱的分件：先用左側參數建，再搬到右側）。"""
        import bpy as _b
        if not isinstance(obs, (list, tuple)):
            obs = [obs]
        out = []
        for o in obs:
            if o is None:
                continue
            out.append(self.mirror(o))
            self.parts.remove(o)
            _b.data.objects.remove(o)
        return out

    def both(self, obs):
        if not isinstance(obs, (list, tuple)):
            obs = [obs]
        for o in obs:
            if o is not None:
                self.mirror(o)
        return obs


def w_blend(a, b, joint, axis, width):
    """沿 axis 在 joint 附近從骨 a 平滑過渡到骨 b。"""
    axis = axis.normalized()

    def f(co):
        s = smooth(((co - joint).dot(axis) + width / 2) / width)
        return {a: 1 - s, b: s}
    return f


def w_zchain(chain, width):
    """chain：[bone0, (z1, bone1), (z2, bone2)...] 由下往上，依高度平滑混合。"""
    def f(co):
        ws = {chain[0]: 1.0}
        for z, bn in chain[1:]:
            s = smooth((co.z - z + width / 2) / width)
            if s <= 0:
                continue
            for k in list(ws):
                ws[k] *= (1 - s)
            ws[bn] = ws.get(bn, 0) + s
        return {k: v for k, v in ws.items() if v > 1e-3}
    return f


def w_chain_pts(anchor, names, pts, width_frac=0.6):
    """布料鏈權重：依最近的鏈段參數在 anchor → names[0] → names[1]… 之間平滑混合。pts 為鏈節點（rest）。"""
    seglen = [(pts[k + 1] - pts[k]).length for k in range(len(pts) - 1)]

    def f(co):
        # 沿鏈的累積參數
        best = None
        acc = 0.0
        for k in range(len(pts) - 1):
            d = pts[k + 1] - pts[k]
            s = (co - pts[k]).dot(d) / d.length_squared
            sc = clamp(s)
            q = pts[k] + d * sc
            dist = (co - q).length
            if best is None or dist < best[0]:
                if k == 0 and s < 0:
                    sc = s
                if k == len(pts) - 2 and s > 1:
                    sc = s
                best = (dist, acc + sc * seglen[k])
            acc += seglen[k]
        x = best[1]
        ws = {anchor: 1.0}
        acc = 0.0
        for k, n in enumerate(names):
            wd = seglen[k] * width_frac
            s = smooth((x - acc + wd * 0.5) / wd) if k > 0 else smooth((x - acc + wd * 0.2) / wd)
            if s > 0:
                for kk in list(ws):
                    ws[kk] *= (1 - s)
                ws[n] = ws.get(n, 0) + s
            acc += seglen[k]
        return {k: v for k, v in ws.items() if v > 1e-3}
    return f


# ---------------------------------------------------------------- 人體比例
class Body:
    def __init__(self, H=1.8, bulk=1.0, wf=1.0, head=0.235, hz=0.53, neck=0.05, arm_a=52.0, elbow=15.0,
                 arm_len=1.0, limb=1.0):
        self.H = H; self.U = U = H / 1.8; self.B = bulk; self.wf = wf
        self.head = head
        R = U * bulk
        self.R = R
        self.RL = RL = U * bulk * limb
        j = self.j = {}
        hzv = hz * H
        self.hzv = hzv
        self.head_base = H - 0.85 * head
        self.nz = nz = self.head_base - neck * H
        span = nz - hzv
        self.span = span
        self.tz = lambda t: hzv + span * t
        j["Root"] = V(0, 0, 0)
        j["Hips"] = V(0, 0, hzv)
        j["Spine"] = V(0, 0.005 * U, self.tz(0.20))
        j["Spine2"] = V(0, 0.008 * U, self.tz(0.42))
        j["Neck"] = V(0, 0.012 * U, nz)
        j["Head"] = V(0, 0.0, self.head_base)
        j["HeadTop"] = V(0, 0.0, H)
        sz = self.tz(0.93)
        sw = 0.105 * H * wf
        self.sw = sw
        j["ShoulderL"] = V(0.03 * U, 0.01 * U, sz + 0.012 * U)
        j["UpperArmL"] = V(sw, 0.005 * U, sz)
        a = math.radians(arm_a)
        ud = V(math.cos(a), 0, -math.sin(a))
        e = math.radians(elbow)
        fd = (ud * math.cos(e) + FWD * math.sin(e)).normalized()
        self.ua_len = 0.165 * H * arm_len; self.fa_len = 0.148 * H * arm_len; self.hand_len = 0.05 * H
        j["ForearmL"] = j["UpperArmL"] + ud * self.ua_len
        j["HandL"] = j["ForearmL"] + fd * self.fa_len
        j["HandTipL"] = j["HandL"] + fd * self.hand_len
        self.ud, self.fd = ud, fd
        hx = 0.048 * H * (0.5 + 0.5 * wf)
        j["ThighL"] = V(hx, 0, hzv - 0.015 * H)
        j["ShinL"] = V(hx + 0.004 * H, -0.014 * H, 0.285 * H)
        j["FootL"] = V(hx + 0.008 * H, 0.010 * H, 0.048 * H)
        j["ToeL"] = V(hx + 0.012 * H, -0.085 * H, 0.012 * H)
        for k in list(j):
            if k.endswith("L"):
                p = j[k]
                j[k[:-1] + "R"] = V(-p.x, p.y, p.z)
        # 軀幹截面（t：0=骨盆中心、1=頸根）
        tb = [(-0.135, 0.100, 0.085, 0, 0.004), (-0.05, 0.166, 0.116, 0, 0.004), (0.10, 0.170, 0.118, 0, 0.0),
              (0.28, 0.150, 0.106, 0, -0.004), (0.50, 0.168, 0.118, 0, -0.010), (0.70, 0.188, 0.130, 0, -0.012),
              (0.86, 0.180, 0.114, 0, -0.004), (0.95, 0.142, 0.092, 0, 0.004), (1.0, 0.078, 0.072, 0, 0.010),
              (1.12, 0.060, 0.062, 0, 0.004)]
        tab = [(hzv + span * t, rx * R * (wf if t > 0.4 else (0.5 + 0.5 * wf)), ry * R, du, dv * U) for t, rx, ry, du, dv in tb]
        self.torso = Surf(V(0, 0, 0), Z, tab)
        La, Lf = self.ua_len, self.fa_len
        self.uarm = Surf(j["UpperArmL"], ud, [(-0.02, 0.058 * RL, 0.058 * RL, 0, 0), (La * 0.4, 0.054 * RL, 0.056 * RL, 0, 0),
                                              (La, 0.046 * RL, 0.046 * RL, 0, 0)])
        self.farm = Surf(j["ForearmL"], fd, [(0, 0.046 * RL, 0.046 * RL, 0, 0), (Lf * 0.28, 0.049 * RL, 0.050 * RL, 0, 0),
                                             (Lf * 0.75, 0.038 * RL, 0.040 * RL, 0, 0), (Lf, 0.033 * RL, 0.036 * RL, 0, 0)])
        td = (j["ShinL"] - j["ThighL"]); Lt = td.length
        sd = (j["FootL"] - j["ShinL"]); Ls = sd.length
        self.th_len, self.sh_len = Lt, Ls
        self.thigh = Surf(j["ThighL"], td, [(-0.03, 0.092 * RL, 0.098 * RL, 0, 0), (Lt * 0.3, 0.088 * RL, 0.094 * RL, 0, 0),
                                            (Lt * 0.8, 0.068 * RL, 0.072 * RL, 0, 0), (Lt, 0.062 * RL, 0.064 * RL, 0, 0)])
        self.shin = Surf(j["ShinL"], sd, [(0, 0.062 * RL, 0.064 * RL, 0, 0), (Ls * 0.26, 0.063 * RL, 0.074 * RL, 0, -0.016 * RL),
                                          (Ls * 0.62, 0.048 * RL, 0.054 * RL, 0, -0.006 * RL), (Ls * 0.9, 0.039 * RL, 0.044 * RL, 0, 0), (Ls, 0.040 * RL, 0.046 * RL, 0, 0)])
        # 手的座標架
        self.hand_a = fd.copy()
        v = FWD - fd * FWD.dot(fd); self.hand_v = v.normalized()      # 拇指側（握持物的軸向）
        hu = self.hand_v.cross(fd)                                    # 手背方向（外）
        self.hand_u = -hu if hu.x < 0 else hu
        self.set_grip(0.017 * U)

    def set_grip(self, r):
        """握持物半徑 r：算出握拳中心（武器軸通過處）與指關節位置。"""
        RL = self.RL
        self.grip_r = r
        self.finger_r = 0.0115 * RL
        self.grip_rc = r + self.finger_r
        self.knuckle_dir = (self.hand_u * 0.8 + self.hand_a * 0.6).normalized()
        self.knuckle = self.j["HandL"] + self.hand_a * (0.088 * RL) + self.hand_u * (0.008 * RL)
        self.grip_c = self.knuckle - self.knuckle_dir * self.grip_rc

    @staticmethod
    def mir(p):
        return V(-p.x, p.y, p.z)

    def w_torso(self):
        j = self.j
        return w_zchain(["Hips", (j["Spine"].z, "Spine"), (j["Spine2"].z, "Spine2"), (j["Neck"].z + 0.01, "Neck"),
                         (j["Head"].z, "Head")], 0.07 * self.U)

    def w_elbow(self):
        return w_blend("UpperArmL", "ForearmL", self.j["ForearmL"], self.ud + self.fd, 0.10 * self.U)

    def w_knee(self):
        j = self.j
        return w_blend("ThighL", "ShinL", j["ShinL"],
                       (j["ShinL"] - j["ThighL"]).normalized() + (j["FootL"] - j["ShinL"]).normalized(), 0.12 * self.U)


# ---------------------------------------------------------------- 骨架
def build_armature(name, body, weapon=None, chains=(), extra=()):
    """weapon：(head, tail)（右手握點與刃方向）。chains：[(名稱前綴, 錨骨, [點0, 點1, ...])]。
    extra：[(name, parent, head, tail)]"""
    j = body.j
    bpy.ops.object.armature_add(location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = name
    arm.data.name = name
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    root = eb[0]
    root.name = "Root"; root.head = (0, 0, 0); root.tail = (0, 0.25 * body.U, 0)

    def bone(n, parent, head, tail):
        b = eb.new(n)
        b.head = head; b.tail = tail; b.parent = eb[parent]; b.use_connect = False
        return b
    bone("Hips", "Root", j["Hips"], j["Spine"])
    bone("Spine", "Hips", j["Spine"], j["Spine2"])
    bone("Spine2", "Spine", j["Spine2"], j["Neck"])
    bone("Neck", "Spine2", j["Neck"], j["Head"])
    bone("Head", "Neck", j["Head"], j["HeadTop"])
    for s in "LR":
        bone("Shoulder" + s, "Spine2", j["Shoulder" + s], j["UpperArm" + s])
        bone("UpperArm" + s, "Shoulder" + s, j["UpperArm" + s], j["Forearm" + s])
        bone("Forearm" + s, "UpperArm" + s, j["Forearm" + s], j["Hand" + s])
        bone("Hand" + s, "Forearm" + s, j["Hand" + s], j["HandTip" + s])
        bone("Thigh" + s, "Hips", j["Thigh" + s], j["Shin" + s])
        bone("Shin" + s, "Thigh" + s, j["Shin" + s], j["Foot" + s])
        bone("Foot" + s, "Shin" + s, j["Foot" + s], j["Toe" + s])
    if weapon:
        bone("Weapon", "HandR", weapon[0], weapon[1])
    for pre, anchor, pts in chains:
        par = anchor
        names = chain_names(pre, len(pts) - 1)
        for k in range(len(pts) - 1):
            bone(names[k], par, pts[k], pts[k + 1])
            par = names[k]
    for n, parent, head, tail in extra:
        bone(n, parent, head, tail)
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def chain_names(pre, n):
    return [f"{pre}{k + 1}" for k in range(n)] if n > 1 else [pre]
