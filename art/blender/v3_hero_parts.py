"""單字魂 v3 主角騎士 hero_knight：專用分件（從 soul_humanoid_parts 複製再大改）。

規格：art/v3/specs/hero_knight.md。全部以 H=1.8 m 的公尺數寫（U=1）。
重點分件：
  - 小頭盔（寬 0.10H、深 0.13H、中脊、船頭形前突面罩、視縫、透氣孔）
  - 灰藍亞麻罩袍（前後兩片、側邊開衩、下擺撕成長條、胸口小破洞、腰帶處放射皺褶）
  - 斜背帶、主腰帶＋方扣＋垂尾、斜掛劍帶、右胯皮袋、左胯劍鞘（鐵口、包尾、兩條掛帶）
  - 左大圓肩甲（翻邊珠、一圈鉚釘、立起護頸翼）＋右 4 片疊甲（片間皮帶）
  - 鎖子甲：護頸、上臂、腰下鎖子甲裙（鋸齒下緣）、大腿
  - 平滑腿甲（大腿前片、圓頂膝甲＋側扇、平滑脛甲＋後側兩道皮帶）、皮靴＋鐵疊片
  - 厚羊毛披風：胸前圍巾＋圓環別針、背後兩層（不規則圓破洞、縱向皺褶）
  - 長劍（0.60H：血槽、刃口缺口、皮纏握柄、圓盤劍首）

V3Builder 另外產生一組 "detail" UV（烘焙用）：x＝沿著分件的長度（公尺），y＝公尺（+10 偏移）；
皮帶類分件（mode="strap"）的 y 改成「橫向 0~1」，材質用它畫縫線、邊緣磨損。
"""
import math, random
import bmesh
import numpy as np
from mathutils import Vector
from soul_humanoid_lib import *
from soul_humanoid_parts import angn, box, rag_profile, _tri


# ---------------------------------------------------------------- Builder：加 detail UV
class V3Builder(Builder):
    mode = "m"          # "m"：公尺；"strap_v"／"strap_u"：橫向在 v／u，正規化到 0~1；"none"：不畫縫線

    def add_mesh(self, name, bm, mat, w, sharp=35.0, texel=1.0, stacked=False):
        slot_before = getattr(self, "uv_slot", 0)
        ob = super().add_mesh(name, bm, mat, w, sharp=sharp, texel=texel, stacked=stacked)
        du = -50.0 if stacked else self.uv_slot * 20.0
        me = ob.data
        src = me.uv_layers[0]
        n = len(me.loops)
        a = np.empty(n * 2, np.float32)
        src.data.foreach_get("uv", a)
        a = a.reshape(-1, 2)
        a[:, 0] = (a[:, 0] - du) / texel
        a[:, 1] = a[:, 1] / texel
        mode = self.mode
        if mode in ("strap_v", "strap_u") and n:
            ax = 1 if mode == "strap_v" else 0
            lo, hi = float(a[:, ax].min()), float(a[:, ax].max())
            across = (a[:, ax] - lo) / max(hi - lo, 1e-6)
            along = a[:, 1 - ax].copy()
            a[:, 0] = along; a[:, 1] = across
        elif mode == "none":
            a[:, 1] += 30.0
        else:
            a[:, 1] += 10.0
        det = me.uv_layers.new(name="detail", do_init=False)
        det.data.foreach_set("uv", a.ravel())
        me.uv_layers.active_index = 0
        try:
            me.uv_layers[0].active_render = True
        except Exception:
            pass
        return ob

    def strap(self, mode="strap_v"):
        b = self

        class _Ctx:
            def __enter__(s):
                s.old = b.mode; b.mode = mode
            def __exit__(s, *e):
                b.mode = s.old
        return _Ctx()


# ---------------------------------------------------------------- 調整人體比例（照 spec 比例表）
def tune_body(body):
    """覆寫軀幹、大腿、小腿、前臂截面（Body 是共用 lib，不改原檔，在這裡重建表面函式）。"""
    R = body.R; RL = body.RL; U = body.U
    hzv, span = body.hzv, body.span
    tb = [(-0.135, 0.100, 0.085, 0, 0.004), (-0.05, 0.180, 0.108, 0, 0.004), (0.10, 0.176, 0.106, 0, 0.0),
          (0.28, 0.150, 0.088, 0, -0.004), (0.50, 0.168, 0.092, 0, -0.008), (0.70, 0.194, 0.095, 0, -0.010),
          (0.86, 0.184, 0.092, 0, -0.004), (0.95, 0.142, 0.086, 0, 0.004), (1.0, 0.078, 0.068, 0, 0.010),
          (1.12, 0.058, 0.058, 0, 0.004)]
    body.torso = Surf(V(0, 0, 0), Z, [(hzv + span * t, rx * R, ry * R, du, dv * U) for t, rx, ry, du, dv in tb])
    j = body.j
    Lt, Ls, Lf = body.th_len, body.sh_len, body.fa_len
    td = (j["ShinL"] - j["ThighL"]); sd = (j["FootL"] - j["ShinL"])
    body.thigh = Surf(j["ThighL"], td, [(-0.03, 0.090 * RL, 0.094 * RL, 0, 0), (Lt * 0.3, 0.088 * RL, 0.091 * RL, 0, 0),
                                        (Lt * 0.8, 0.070 * RL, 0.072 * RL, 0, 0), (Lt, 0.060 * RL, 0.062 * RL, 0, 0)])
    body.shin = Surf(j["ShinL"], sd, [(0, 0.056 * RL, 0.058 * RL, 0, 0), (Ls * 0.26, 0.056 * RL, 0.064 * RL, 0, -0.012 * RL),
                                      (Ls * 0.62, 0.044 * RL, 0.048 * RL, 0, -0.004 * RL), (Ls * 0.9, 0.040 * RL, 0.044 * RL, 0, 0),
                                      (Ls, 0.040 * RL, 0.045 * RL, 0, 0)])
    body.farm = Surf(j["ForearmL"], body.fd, [(0, 0.044 * RL, 0.044 * RL, 0, 0), (Lf * 0.28, 0.046 * RL, 0.047 * RL, 0, 0),
                                              (Lf * 0.75, 0.037 * RL, 0.039 * RL, 0, 0), (Lf, 0.032 * RL, 0.034 * RL, 0, 0)])
    body.uarm = Surf(j["UpperArmL"], body.ud, [(-0.02, 0.060 * RL, 0.060 * RL, 0, 0), (body.ua_len * 0.4, 0.057 * RL, 0.058 * RL, 0, 0),
                                               (body.ua_len, 0.049 * RL, 0.049 * RL, 0, 0)])
    return body


# ---------------------------------------------------------------- 軀幹層次（偏移量都是「離身體表面」的公尺數）
class Layers:
    """胸甲外形與其上各層（罩袍、皮帶）的偏移量，確保層層往外不互穿。"""

    def __init__(self, body):
        self.b = body
        self.zc0 = body.tz(0.30)        # 胸甲下緣（腰）
        self.zc1 = body.tz(0.92)
        self.zhip = body.tz(-0.02)      # 臀最寬處，再往下改成「垂掛」

    def cuirass(self, ang, z):
        a = angn(ang)
        front = math.exp(-(a / 62) ** 2)
        s = clamp((z - self.zc0) / (self.zc1 - self.zc0))
        keel = 0.007 * math.exp(-(a / 9) ** 2) * math.sin(math.pi * clamp(s * 1.05))
        globe = 0.012 * front * math.sin(math.pi * clamp((s - 0.02) / 0.85)) ** 1.2
        flare = 0.010 * (1 - smooth(s / 0.12))
        return 0.010 + keel + globe + flare

    def under(self, ang, z):
        """胸甲（腰以上）或鎖子甲裙（腰以下）的外表面。"""
        if z >= self.zc0 + 0.02:
            return self.cuirass(ang, z) + 0.003
        k = smooth((z - self.zc0 + 0.03) / 0.05)
        return lerp(0.016, self.cuirass(ang, z) + 0.003, k)

    def tabard(self, ang, z):
        return self.under(ang, z) + 0.008


def hang_pt(body, L, z, ang, off, flare=0.22):
    """軀幹表面，但臀部以下改成從臀圍往下垂掛、往外張（裙／罩袍／披掛用）。"""
    zh = L.zhip
    if z >= zh:
        return body.torso.pt(z, ang, off)
    d = zh - z
    n = body.torso.nrm(zh, ang)
    return body.torso.pt(zh, ang, off) + n * (flare * d) - Z * d


# ---------------------------------------------------------------- 鎖子甲
def mail_layers(B, body, L, mat):
    obs = []
    # 軀幹內層（整件鎖子甲衫）
    obs.append(B.shell("MailShirt", body.torso, body.tz(-0.135), body.tz(1.05), 0, 360, 22, 14, mat, body.w_torso(), off=0.0,
                       cap0=True, texel=1.0))
    # 腰下的鎖子甲裙：鋸齒下緣到 0.38H
    zt, zb = body.tz(0.36), 0.40 * 1.8
    nu = 36

    def fn(u, v):
        ang = u * 360
        k = int(round(u * nu))
        tooth = 0.022 * (1 if k % 2 else 0) + 0.008 * math.sin(k * 2.3)
        z = lerp(zb - tooth, zt, v)
        return hang_pt(body, L, z, ang, 0.012 + 0.004 * (1 - v), flare=0.20)
    from soul_humanoid_parts import w_skirt
    obs.append(B.grid("MailSkirt", nu, 6, fn, mat, w_skirt(body, L.zhip + 0.02, zb, 0.8),
                      [V(0, 0, zb - 0.1), V(0, 0, zt), V(0, 0, (zb + zt) / 2)], closed_u=True, texel=1.0))
    # 護頸（盔下垂到肩、往外張開成小披肩）
    def offn(u, v, ang, t):
        a = angn(ang)
        return 0.006 + 0.030 * (1 - v) ** 2.2 + 0.004 * math.sin(ang * 0.35) * (1 - v)
    obs.append(B.shell("MailCoif", body.torso, lambda u: body.tz(0.86) - 0.012 * math.exp(-(angn(u * 360) / 50) ** 2), body.tz(1.14),
                       0, 360, 24, 6, mat, {"Spine2": 0.45, "Neck": 0.55}, off=offn))
    return obs


# ---------------------------------------------------------------- 胸甲（大部分被罩袍蓋住）
def cuirass(B, body, L, mat, rivet_mat):
    R = body.R

    def t1(u):
        a = angn(u * 360)
        hole = math.exp(-((abs(a) - 90) / 40) ** 2)
        return body.tz(lerp(0.92, 0.70, hole))

    def offn(u, v, ang, t):
        return L.cuirass(ang, t)
    ob = B.shell("Cuirass", body.torso, L.zc0, t1, 0, 360, 28, 10, mat, "Spine2", off=offn, rim=0.006)
    pts = []
    for a in (-120, -90, -60, 60, 90, 120):
        t = L.zc0 + 0.03
        pts.append((body.torso.pt(t, a, L.cuirass(a, t) + 0.002), body.torso.nrm(t, a)))
    B.rivets("CuirassRivets", pts, rivet_mat, "Spine2", r=0.005)
    return ob


# ---------------------------------------------------------------- 罩袍
def tear_profile(nu, rnd, depth, teeth=(10, 16)):
    """撕破下緣：寬窄不一的鋸齒（每齒深度隨機），再加細碎抖動。回傳每欄的缺口深度（公尺，0＝最長）。"""
    k = rnd.randint(*teeth)
    w = [rnd.uniform(0.4, 1.9) for _ in range(k)]
    tot = sum(w); edges = [0.0]
    for x in w:
        edges.append(edges[-1] + x / tot)
    tips = [rnd.uniform(0.0, 0.35) for _ in range(k + 1)]          # 齒尖（長）
    vals = [rnd.uniform(0.45, 1.0) for _ in range(k)]               # 齒間缺口（短）
    out = []
    for i in range(nu + 1):
        u = i / nu
        j = min(k - 1, max(0, next((q for q in range(k) if edges[q + 1] >= u), k - 1)))
        s = (u - edges[j]) / max(edges[j + 1] - edges[j], 1e-6)
        s = clamp(s)
        tri = max(0.0, 1 - abs(2 * s - 1))
        dep = lerp(lerp(tips[j], tips[j + 1], s), vals[j], tri ** 0.7)
        dep += rnd.uniform(-0.08, 0.08)
        out.append(clamp(dep, 0, 1.1) * depth)
    return out


def fringe(B, name, roots, mat, w, rnd, n_per=2, length=(0.006, 0.016), width=0.0035):
    """毛邊：沿撕口長出細細的線頭（每根一條雙面窄帶）。roots：[(位置, 往下方向, 側向)]。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("atlas")
    for p, dn, sd in roots:
        for _ in range(n_per):
            if rnd.random() < 0.35:
                continue
            L_ = rnd.uniform(*length)
            off = sd * rnd.uniform(-0.006, 0.006)
            d = (dn + sd * rnd.uniform(-0.35, 0.35) + Vector((0, 0, 0))).normalized()
            p0 = p + off - d * 0.004; p1 = p0 + d * (L_ * 0.5) + sd * rnd.uniform(-0.002, 0.002); p2 = p0 + d * L_ + sd * rnd.uniform(-0.004, 0.004)
            ww = width * rnd.uniform(0.6, 1.2)
            vs = [bm.verts.new(q + sd * (ww * k * t)) for q, t in ((p0, 1.0), (p1, 0.7), (p2, 0.2)) for k in (-0.5, 0.5)]
            for a_, b_ in ((0, 2), (2, 4)):
                f = bm.faces.new((vs[a_], vs[a_ + 1], vs[b_ + 1], vs[b_]))
                for l, q in zip(f.loops, ((0, a_), (1, a_), (1, b_), (0, b_))):
                    l[uvl].uv = (0.01 + q[0] * 0.004, 0.01 + q[1] * 0.004)
    with B.strap("none"):
        return B.add_mesh(name, bm, mat, w, sharp=80, stacked=True)


def tabard(B, body, L, mat, seed=7):
    """前後兩片，一整片有厚度的亞麻（0.004H）。上緣在肩頸，腰帶處收緊（放射皺褶），臀下垂掛；
    只在最下緣 0.05H 內撕成寬窄不一的鋸齒＋毛邊線頭，另外前片 2 道、後片 1 道短裂口（寬度不同）。下緣 0.37H。"""
    rnd = random.Random(seed)
    zbot = 0.37 * 1.8
    ztop = body.tz(1.02)
    zbelt = 0.60 * 1.8
    obs = []
    from soul_humanoid_parts import w_skirt
    wsk = w_skirt(body, L.zhip + 0.02, zbot - 0.05, 0.85)
    wt = body.w_torso()

    def wfun(co):
        if co.z > L.zhip + 0.04:
            return wt(co)
        if co.z < L.zhip - 0.02:
            return wsk(co)
        k = smooth((co.z - (L.zhip - 0.02)) / 0.06)
        a = wt(co); b = wsk(co)
        out = {}
        for d, f in ((a, k), (b, 1 - k)):
            for n_, x in d.items():
                out[n_] = out.get(n_, 0) + x * f
        return out
    for side, (a0, a1), nslit in (("F", (-56, 56), 2), ("B", (124, 236), 1)):
        nu, nv = 36, 16
        cut = tear_profile(nu, rnd, 0.05 * 1.8)
        fold_ph = rnd.uniform(0, 6.28)
        curl = [rnd.uniform(-1.0, 1.0) for _ in range(nu + 1)]
        # 短裂口：從下緣往上 0.05–0.08H，各自不同寬（1～2 欄）
        slits = set()
        for _ in range(nslit):
            i0 = rnd.randrange(6, nu - 8); wcol = rnd.choice((1, 1, 2))
            ln = rnd.uniform(0.05, 0.08) * 1.8
            for i in range(i0, i0 + wcol):
                slits.add((i, ln))

        def fn(u, v):
            x = u * nu; i = min(int(x), nu - 1); f = x - i
            ang = lerp(a0, a1, u)
            zb = zbot + lerp(cut[i], cut[i + 1], f)
            z = lerp(ztop, zb, v)
            off = L.tabard(ang, z)
            db = (z - zbelt)
            pinch = math.exp(-(db / 0.03) ** 2)
            folds = 0.006 * math.sin(math.radians(ang) * 11 + fold_ph) * math.exp(-(abs(db) / 0.10)) * (1 - pinch * 0.7)
            off = off - 0.004 * pinch + max(0.0, folds) + 0.002
            if z < L.zhip:          # 垂墜：寬窄不一的縱向皺褶
                d = L.zhip - z
                off += (0.009 * math.sin(math.radians(ang) * 7 + fold_ph * 1.3) + 0.005 * math.sin(math.radians(ang) * 17 + fold_ph)) * smooth(d / 0.15)
            p = hang_pt(body, L, z, ang, off, flare=0.16)
            if z < L.zhip:
                d = L.zhip - z
                nn = body.torso.nrm(L.zhip, ang)
                p = p + nn * (0.05 * d)
                tip = smooth((v - 0.93) / 0.07)                      # 撕口邊緣微微翻捲
                cl = lerp(curl[i], curl[i + 1], f)
                p = p + nn * (0.008 * cl * tip)
            return p
        ins = [body.torso.center(z) for z in (ztop, zbelt, L.zhip)] + [V(0, 0, zbot)]
        ob = B.grid(f"Tabard{side}", nu, nv, fn, mat, wfun, ins, holes=None, texel=1.0, sharp=60)
        # 裂口：該欄在下緣往上 ln 公尺內的格子刪掉
        sl = set()
        for (i, ln) in slits:
            zb = zbot + cut[i]
            for j in range(nv):
                zc = lerp(ztop, zb, (j + 0.5) / nv)
                if zc < zb + ln:
                    sl.add((i, j))
        _cut_tabard(ob, nu, nv, set(), sl)
        ob["cloth"] = 0.0072
        obs.append(ob)
        # 毛邊線頭：沿下緣
        roots = []
        for i in range(nu + 1):
            u = i / nu
            p = fn(u, 1.0)
            pu = fn(min(1, u + 0.01), 1.0) - fn(max(0, u - 0.01), 1.0)
            sd = pu.normalized()
            dn = (fn(u, 1.0) - fn(u, 0.97)).normalized()
            roots.append((p, dn, sd))
        obs.append(fringe(B, f"Tabard{side}Fray", roots, mat + "Fray", wfun, rnd, n_per=3))
    return obs


def _cut_tabard(ob, nu, nv, holes, slits):
    """依格子座標刪面。grid 的面順序是 i 外層、j 內層（可能有細分倍率），用面中心的 UV 反推格子。"""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv["atlas"]
    bm.faces.ensure_lookup_table()
    # 用每個面在 grid 中的 index 推回 (i, j)：Builder.grid 依序建立 nu×nv 個面（沒有 holes 時）
    kill = []
    for idx, f in enumerate(bm.faces):
        i, j = divmod(idx, nv)
        if (i, j) in holes:
            kill.append(f)
        elif (i, j) in slits:
            # 裂縫：把這一格縮成窄條（移除這一格，左右兩條布各自獨立）
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me); bm.free()


# ---------------------------------------------------------------- 皮帶類
def band(B, body, L, name, zfun, mat, w, h, extra=0.0, thick=0.005, nu=36, a0=0, a1=360, base=None):
    """繞軀幹的帶子：zfun(ang) 給中心高度，h 為帶寬；偏移在罩袍外面。"""
    base = base or L.tabard
    closed = abs(a1 - a0 - 360) < 1e-6

    def fn(u, v):
        ang = a0 + (a1 - a0) * u
        zz = zfun(ang)
        k = min(int(round(v * 3)), 3)
        dz = (-h / 2, -h / 2, h / 2, h / 2)[k]
        o0 = base(ang, zz) + 0.002 + extra
        o = (o0 - 0.002, o0 + thick, o0 + thick, o0 - 0.002)[k]
        return hang_pt(body, L, zz + dz, ang, o, flare=0.16)
    with B.strap("strap_v"):
        return B.grid(name, nu, 3, fn, mat, w, [V(0, 0, 0.5), V(0, 0, 1.0), V(0, 0, 1.5)], closed_u=closed, sharp=30)


def belts(B, body, L, mat_belt, mat_sword, mat_iron, mat_bald):
    obs = []
    zb = 0.60 * 1.8
    w_belt = {"Spine": 0.5, "Hips": 0.5}
    obs.append(band(B, body, L, "Belt", lambda a: zb, mat_belt, w_belt, 0.036, thick=0.006))
    # 方扣（0.025H）＋扣舌＋垂下的帶尾（0.06H）
    a = -6
    n = body.torso.nrm(zb, a); side = Z.cross(n).normalized()
    c = body.torso.pt(zb, a, L.tabard(a, zb) + 0.012)
    obs.append(_frame_buckle(B, "BeltBuckle", c, side, n, 0.024, 0.022, 0.0045, mat_iron, w_belt))
    with B.strap("strap_u"):
        p0 = body.torso.pt(zb, 8, L.tabard(8, zb) + 0.012)
        pts = [p0, p0 - Z * 0.05 + n * 0.006, p0 - Z * 0.11 + n * 0.010 + side * 0.006]
        obs.append(B.tube("BeltTail", pts, [(0.017, 0.0035)] * 3, 6, mat_belt, w_belt, exp=4, flat=side))
    # 斜掛劍帶：右高左低（0.58H → 0.55H）
    zs = 0.565 * 1.8
    tilt = 0.028
    zf = lambda a: zs + tilt * math.sin(math.radians(-a))
    obs.append(band(B, body, L, "SwordBelt", zf, mat_sword, "Hips", 0.030, extra=0.007, thick=0.005))
    a = -40
    c = body.torso.pt(zf(a), a, L.tabard(a, zf(a)) + 0.017)
    n = body.torso.nrm(zf(a), a); side = Z.cross(n).normalized()
    obs.append(_frame_buckle(B, "SwordBuckle", c, side, n, 0.020, 0.019, 0.004, mat_iron, "Hips"))
    # 斜背帶：右肩 → 左腰（平面切軀幹）
    # 在 ang=-90（右）最高 1.485，ang=90（左）最低 1.055
    bz = lambda ang: 1.27 + 0.215 * math.sin(math.radians(-ang)) * 1.0

    def bald_base(ang, z):
        return max(L.tabard(ang, z), 0.004 + 0.022 * smooth((z - 1.40) / 0.08)) + 0.004
    obs.append(band(B, body, L, "Baldric", bz, mat_bald, body.w_torso(), 0.032, thick=0.005, nu=44, base=bald_base))
    a = -20
    c = body.torso.pt(bz(a), a, bald_base(a, bz(a)) + 0.011)
    n = body.torso.nrm(bz(a), a)
    d = (body.torso.pt(bz(a + 5), a + 5, 0) - body.torso.pt(bz(a - 5), a - 5, 0)).normalized()
    obs.append(_frame_buckle(B, "BaldricBuckle", c, d, n, 0.019, 0.016, 0.004, mat_iron, "Spine2"))
    return obs


def _frame_buckle(B, name, c, side, n, sx, sz, th, mat, w):
    """方框扣：四邊框（中空）＋扣針。"""
    up = n.cross(side).normalized()
    side = up.cross(n).normalized()
    pts = []
    k = 0.82
    corners = [c + side * sx + up * sz, c - side * sx + up * sz, c - side * sx - up * sz, c + side * sx - up * sz]
    path = []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        path += [a.lerp(b, 0.12), a.lerp(b, 0.88)]
    path.append(path[0])
    with B.strap("none"):
        ob = B.tube(name, path, [th] * len(path), 6, mat, w, cap=False, up=n, sharp=50)
        B.tube(name + "Pin", [c + up * sz * 0.9 + n * th, c - up * sz * 0.2 + n * th * 1.6], [th * 0.55] * 2, 5, mat, w)
    return ob


def pouch(B, body, L, mat, mat_iron, w="Hips"):
    """右胯皮袋：0.07H×0.07H×0.035H，有蓋，一顆扣。"""
    zb = 0.60 * 1.8
    a = -74
    zc = 0.535 * 1.8
    n = body.torso.nrm(zc, a); n.z = 0; n.normalize()
    side = Z.cross(n).normalized()
    c = hang_pt(body, L, zc, a, L.tabard(a, zc) + 0.012) + n * 0.040
    hx, hz, hd = 0.063, 0.063, 0.031
    obs = []
    with B.strap("none"):
        # 袋身：上窄下寬、略鼓的圓角盒
        pts = [c + Z * hz, c + Z * hz * 0.85, c, c - Z * hz * 0.82, c - Z * hz]
        rad = [(hx * 0.86, hd * 0.70), (hx * 0.92, hd * 0.85), (hx, hd), (hx * 0.98, hd * 0.95), (hx * 0.84, hd * 0.72)]
        obs.append(B.tube("Pouch", pts, rad, 14, mat, w, exp=3.4, flat=side, sharp=50))
        # 袋蓋
        fpts = [c + Z * hz * 1.02 + n * 0.004, c + Z * hz * 0.4 + n * (hd * 0.95), c + Z * hz * 0.02 + n * (hd * 1.04)]
        frad = [(hx * 1.0, 0.006), (hx * 1.03, 0.006), (hx * 0.95, 0.005)]
    with B.strap("strap_u"):
        obs.append(B.tube("PouchFlap", fpts, frad, 10, mat, w, exp=4.0, flat=side, sharp=50))
    with B.strap("none"):
        obs.append(B.ellipsoid("PouchKnob", c + Z * hz * 0.06 + n * (hd * 1.06 + 0.004), (side, Z, n), (0.009, 0.009, 0.006), 8, 4,
                               mat_iron, w, v0=0, v1=0.55))
        # 掛在腰帶上的兩條皮環
        for dx in (-0.6, 0.6):
            p = c + side * hx * dx
            obs.append(B.tube("PouchLoop", [p + Z * (hz - 0.004) + n * 0.004, p + Z * (hz + 0.045) - n * 0.008],
                              [(0.008, 0.0025)] * 2, 6, mat, w, exp=4, flat=side))
    return obs


def scabbard(B, body, L, mat, mat_iron, mat_strap):
    """左胯劍鞘：長 0.48H、寬 0.035H，往後斜（側面看約 25°），鐵鞘口＋包尾＋兩條掛帶。"""
    zs = 0.552 * 1.8
    a = 84
    top = body.torso.pt(zs, a, L.tabard(a, zs) + 0.042)
    top.y -= 0.03
    d = V(0.13, 0.36, -0.92).normalized()
    Ln = 0.48 * 1.8
    flat = (X - d * X.dot(d)).normalized()       # 劍鞘的「寬」朝外側（側面看得到寬面）
    fl = d.cross(flat).normalized()
    flat = fl.cross(d).normalized()
    pts = [top - d * 0.02, top, top + d * Ln * 0.5, top + d * Ln * 0.92, top + d * Ln]
    w = "Scabbard"         # 獨立骨頭：碰地時往後擺（v3_hero_rig.V3Rig.solve）
    obs = []
    with B.strap("strap_u"):
        obs.append(B.tube("Scabbard", pts, [(0.031, 0.013), (0.032, 0.013), (0.029, 0.012), (0.022, 0.010), (0.010, 0.006)],
                          10, mat, w, flat=fl, exp=2.6))
    with B.strap("none"):
        obs.append(B.tube("ScabLocket", [top - d * 0.035, top + d * 0.045], [(0.035, 0.016), (0.034, 0.015)], 10, mat_iron, w, flat=fl, exp=2.6))
        obs.append(B.tube("ScabBand", [top + d * Ln * 0.32, top + d * Ln * 0.345], [(0.032, 0.0145)] * 2, 10, mat_iron, w, flat=fl, exp=2.6))
        obs.append(B.tube("ScabChape", [top + d * Ln * 0.84, top + d * Ln * 0.93, top + d * (Ln + 0.014)],
                          [(0.025, 0.0125), (0.021, 0.0115), (0.008, 0.006)], 10, mat_iron, w, flat=fl, exp=2.6))
    # 兩條掛帶：鞘口 → 劍帶
    zf = lambda aa: 0.565 * 1.8 + 0.028 * math.sin(math.radians(-aa))
    with B.strap("strap_u"):
        for k, (aa, s) in enumerate(((66, 0.0), (104, 0.30))):
            p0 = body.torso.pt(zf(aa), aa, L.tabard(aa, zf(aa)) + 0.016)
            p1 = top + d * (0.01 + s * 0.12) + fl * 0.0
            mid = p0.lerp(p1, 0.5) + V(0.012, 0, -0.01)
            obs.append(B.tube(f"ScabStrap{k}", [p0, mid, p1], [(0.011, 0.003)] * 3, 6, mat_strap, "Hips", exp=4))
    return obs, top, d


# ---------------------------------------------------------------- 肩甲
def rolled_edge(B, name, ring, mat, w, r=0.004):
    with B.strap("none"):
        return B.tube(name, ring + [ring[0]], [r] * (len(ring) + 1), 6, mat, w, cap=False)


def pauldron_left(B, body, mat, rivet_mat, mat_strap):
    """左大圓肩甲：寬 0.13H、高 0.12H（含下方 2 片上臂疊甲），護頸翼高出肩 0.04H，翻邊珠＋一圈鉚釘。"""
    j = body.j
    out = body.uarm.u
    pole = (out * 0.70 + Z * 0.72).normalized()
    ex = (FWD - pole * FWD.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["UpperArmL"] + pole * 0.010 - Z * 0.008 + X * 0.004
    rad = (0.118, 0.110, 0.106)
    wd = {"ShoulderL": 0.55, "UpperArmL": 0.45}
    V1 = 0.56
    obs = [B.ellipsoid("PauldronL", c, (ex, ey, pole), rad, 26, 9, mat, wd, v0=0.0, v1=V1, rim=0.005,
                       dent=lambda d, u, v: 1 + 0.06 * smooth((v - 0.72) / 0.28) - 0.025 * math.exp(-((v - 0.35) / 0.08) ** 2))]

    def sp(phd, v):
        th = math.pi * v; ph = math.radians(phd)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        rr = 1 + 0.06 * smooth((v - 0.72) / 0.28) - 0.025 * math.exp(-((v - 0.35) / 0.08) ** 2)
        return c + (ex * (d.x * rad[0]) + ey * (d.y * rad[1]) + pole * (d.z * rad[2])) * rr, (ex * d.x / rad[0] + ey * d.y / rad[1] + pole * d.z / rad[2]).normalized()
    ring = [sp(k * 360 / 40, V1 + 0.004)[0] for k in range(40)]
    obs.append(rolled_edge(B, "PauldronLRoll", ring, mat, wd, r=0.0055))
    # 一圈鉚釘（間距約 0.02H）
    pts = []
    for k in range(18):
        p, n = sp(k * 20 + 5, V1 - 0.07)
        pts.append((p + n * 0.002, n))
    obs.append(B.rivets("PauldronLRivets", pts, rivet_mat, wd, r=0.0055))
    # 護頸翼：靠脖子那一側往上立起（高出肩 0.04H）
    def fn(u, v):
        ph = lerp(205, 335, u)
        p, n = sp(ph, 0.40)
        up = (Z * 0.94 - out * 0.30).normalized()
        prof = math.sin(math.pi * u) ** 0.35
        return p + up * (0.070 * v * prof) + n * 0.003 - out * 0.012 * v
    obs.append(B.grid("PauldronLHaute", 16, 4, fn, mat, wd, c - out * 0.06 - Z * 0.04, rim=0.005))
    # 下方 2 片上臂疊甲
    S = body.uarm
    for k in range(2):
        ta = 0.070 + k * 0.040
        tb = ta + 0.055

        def offn(u, v, ang, t, k=k):
            return 0.030 - k * 0.005 + 0.010 * v
        obs.append(B.shell(f"PauldronLLame{k}", S, ta, tb, -10, 190, 14, 2, mat, {"ShoulderL": 0.2, "UpperArmL": 0.8} if k == 0 else "UpperArmL",
                           off=offn, rim=0.005))
    return obs


def pauldron_right(B, body, mat, rivet_mat, mat_strap):
    """右肩 4 片疊甲（寬 0.10H×高 0.10H）：肩頂一片小圓甲＋往下 3 片，片間露出皮帶（鏡射前以左側建）。"""
    j = body.j
    out = body.uarm.u
    pole = (out * 0.62 + Z * 0.78).normalized()
    ex = (FWD - pole * FWD.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["UpperArmL"] + pole * 0.006 - Z * 0.004
    rad = (0.086, 0.082, 0.070)
    wd = {"ShoulderL": 0.6, "UpperArmL": 0.4}
    obs = [B.ellipsoid("PauldronR", c, (ex, ey, pole), rad, 20, 6, mat, wd, v0=0.0, v1=0.46, rim=0.005)]
    S = body.uarm
    for k in range(3):
        ta = 0.022 + k * 0.032
        tb = ta + 0.046

        def offn(u, v, ang, t, k=k):
            return 0.034 - k * 0.004 + 0.010 * v
        wk = {"ShoulderL": 0.35, "UpperArmL": 0.65} if k == 0 else "UpperArmL"
        obs.append(B.shell(f"PauldronRLame{k}", S, ta, tb, -20, 200, 14, 2, mat, wk, off=offn, rim=0.0045))
    # 外側直的皮帶（把疊片串起來）＋鉚釘
    pts = []; rv = []
    for k in range(5):
        t = -0.01 + k * 0.030
        p = S.pt(t, 90, 0.046 - k * 0.002) if k else c + pole * (rad[2] * 0.70) + out * 0.03
        pts.append(p)
    with B.strap("strap_u"):
        obs.append(B.tube("PauldronRStrap", pts, [(0.010, 0.0025)] * len(pts), 6, mat_strap, {"ShoulderL": 0.3, "UpperArmL": 0.7}, exp=4,
                          flat=FWD))
    for k in range(3):
        t = 0.022 + k * 0.032 + 0.030
        rv.append((S.pt(t, 90, 0.046 - k * 0.004 + 0.004), S.nrm(t, 90)))
        for aa in (10, 170):
            rv.append((S.pt(t, aa, 0.040 - k * 0.004 + 0.003), S.nrm(t, aa)))
    obs.append(B.rivets("PauldronRRivets", rv, rivet_mat, "UpperArmL", r=0.005))
    return obs


# ---------------------------------------------------------------- 手臂
def arm_armor(B, body, mat, rivet_mat, mat_strap):
    R = body.RL
    j = body.j
    obs = []
    S = body.uarm
    # 上臂中段一圈皮帶壓住鎖子甲（寬 0.012H）
    with B.strap("strap_v"):
        obs.append(B.shell("UArmStrap", S, body.ua_len * 0.56 - 0.011, body.ua_len * 0.56 + 0.011, 0, 360, 14, 1, mat_strap, "UpperArmL",
                           off=0.010, rim=0.0025))
    obs.append(B.rivets("UArmStrapRivet", [(S.pt(body.ua_len * 0.56, 120, 0.010), S.nrm(body.ua_len * 0.56, 120))], rivet_mat, "UpperArmL", r=0.006))
    # 肘甲＋側扇
    bend = (body.fd - body.ud * body.fd.dot(body.ud)).normalized()
    pole = (-bend * 0.8 + S.u * 0.45).normalized()
    ex = (body.ud + body.fd).normalized(); ex = (ex - pole * ex.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["ForearmL"] + bend * 0.012
    we = {"UpperArmL": 0.5, "ForearmL": 0.5}
    obs.append(B.ellipsoid("Couter", c, (ex, ey, pole), (0.068, 0.062, 0.062), 14, 6, mat, we, v0=0, v1=0.52, rim=0.005,
                           dent=lambda d, u, v: 1 + 0.10 * math.exp(-((v - 0.0) / 0.25) ** 2)))
    wo = S.u
    wc = j["ForearmL"] + wo * 0.056 + bend * 0.018
    e1 = (body.ud + body.fd).normalized(); e2 = wo.cross(e1).normalized()
    obs.append(B.ellipsoid("CouterWing", wc, (e1, e2, wo), (0.050, 0.044, 0.013), 12, 4, mat, we, v0=0, v1=0.5, rim=0.003))
    # 前臂護甲（平滑）＋ 2 道皮帶扣
    Lf = body.fa_len
    F = body.farm
    obs.append(B.shell("Vambrace", F, Lf * 0.14, Lf * 0.74, 0, 360, 14, 4, mat, "ForearmL",
                       off=lambda u, v, ang, t: 0.009 + 0.003 * math.exp(-(angn(ang - 130) / 16) ** 2), rim=0.0045))
    for k, tf in enumerate((0.30, 0.60)):
        with B.strap("strap_v"):
            obs.append(B.shell(f"VambStrap{k}", F, Lf * tf - 0.008, Lf * tf + 0.008, 0, 360, 14, 1, mat_strap, "ForearmL",
                               off=lambda u, v, ang, t: 0.0135 + 0.003 * math.exp(-(angn(ang - 130) / 16) ** 2), rim=0.002))
        p = F.pt(Lf * tf, 200, 0.017); n = F.nrm(Lf * tf, 200)
        obs.append(_frame_buckle(B, f"VambBuckle{k}", p, F.a, n, 0.008, 0.007, 0.0022, rivet_mat, "ForearmL"))
    # 手套袖口：外翻漏斗（外徑 0.075H）
    obs.append(B.shell("GauntletCuff", F, Lf * 0.66, Lf * 1.0, 0, 360, 16, 3, mat, "ForearmL",
                       off=lambda u, v, ang, t: lerp(0.029, 0.010, v ** 0.75), rim=0.005))
    ring = [F.pt(Lf * 0.66, a, 0.029) for a in range(0, 360, 15)]
    obs.append(rolled_edge(B, "GauntletCuffRoll", ring, mat, "ForearmL", r=0.004))
    pts = []
    for a in (40, 140, 220, 320):
        pts.append((F.pt(Lf * 0.20, a, 0.011), F.nrm(Lf * 0.20, a)))
        pts.append((F.pt(Lf * 0.72, a, 0.024), F.nrm(Lf * 0.72, a)))
    obs.append(B.rivets("ArmRivets", pts, rivet_mat, "ForearmL", r=0.0045))
    return obs


def hand(B, body, mat_plate, mat_glove, open_amt=0.0):
    """鐵手套：手背甲＋指節 4 段（每指上有甲片）＋拇指；掌側皮革。"""
    R = body.RL
    W = body.j["HandL"]; a = body.hand_a; v = body.hand_v; u = body.hand_u
    obs = []
    K = body.knuckle
    pts = [W - a * 0.012, W + a * 0.03 + u * 0.004, K - a * 0.004 + u * 0.004, K + a * 0.006]
    obs.append(B.tube("HandBack", pts, [(0.034, 0.021), (0.041, 0.021), (0.044, 0.018), (0.041, 0.013)], 12, mat_plate, "HandL", exp=3.0, flat=v))
    # 掌（皮）
    pp = [W + a * 0.005 - u * 0.010, W + a * 0.045 - u * 0.014, K - a * 0.01 - u * 0.020]
    obs.append(B.tube("Palm", pp, [(0.030, 0.012), (0.036, 0.013), (0.034, 0.011)], 8, mat_glove, "HandL", exp=2.5, flat=v))
    rc = body.grip_rc * (1 + open_amt * 0.8)
    er = body.knuckle_dir
    et = (a - er * a.dot(er)).normalized()
    gc0 = K - er * rc
    sweep = 235 * (1 - open_amt * 0.55)
    for i, o in enumerate((-0.032, -0.011, 0.011, 0.032)):
        g = gc0 + v * o - a * (0.004 * abs(i - 1.3))
        fp = []
        nseg = 5
        ln = (1.0, 1.08, 1.0, 0.86)[i]
        for k in range(nseg + 1):
            th = math.radians(sweep * ln * k / nseg)
            fp.append(g + (er * math.cos(th) + et * math.sin(th)) * rc)
        obs.append(B.tube(f"Finger{i}", fp, [body.finger_r * 1.02] + [body.finger_r * 0.95] * (nseg - 1) + [body.finger_r * 0.78], 6, mat_glove, "HandL",
                          texel=0.8))
        # 指背甲片：4 段疊片（每段是半圈殼）
        for k in range(4):
            th0 = math.radians(sweep * ln * (k + 0.05) / 4.6); th1 = math.radians(sweep * ln * (k + 0.95) / 4.6)
            p0 = g + (er * math.cos(th0) + et * math.sin(th0)) * rc
            p1 = g + (er * math.cos(th1) + et * math.sin(th1)) * rc
            dn = (er * math.cos((th0 + th1) / 2) + et * math.sin((th0 + th1) / 2))
            obs.append(B.tube(f"FingerPlate{i}{k}", [p0 + dn * 0.0035, p1 + dn * 0.0035], [(body.finger_r * 1.08, body.finger_r * 0.62)] * 2, 6,
                              mat_plate, "HandL", flat=v, texel=0.8))
    g = gc0 + v * 0.056
    tp = [W + a * 0.022 + v * 0.032 - u * 0.004]
    for th in (150, 95, 40):
        thr = math.radians(th)
        tp.append(g + (-er * math.cos(thr) * 1.0 + et * math.sin(thr)) * rc * 0.95 - v * 0.006 * (150 - th) / 110)
    obs.append(B.tube("Thumb", tp, [0.015, 0.0135, 0.0118, 0.0095], 6, mat_glove, "HandL", texel=0.8))
    obs.append(B.tube("ThumbPlate", tp[:3], [(0.016, 0.011), (0.0150, 0.010), (0.013, 0.009)], 6, mat_plate, "HandL", flat=u, texel=0.8))
    return obs


# ---------------------------------------------------------------- 腿
def tasset(B, body, L, mat, rivet_mat, mat_strap):
    """胯部腿前甲（0.06H 寬 × 0.09H 高，0.43–0.52H），掛在鎖子甲裙外、罩袍下。"""
    z_top, z_bot = 0.52 * 1.8, 0.43 * 1.8
    a0, a1 = 54, 92

    def fn(u, v):
        ang = lerp(a0, a1, u)
        z = lerp(z_bot + 0.012 * abs(u - 0.5) * 2, z_top, v)
        return hang_pt(body, L, z, ang, 0.021 + 0.005 * math.exp(-((u - 0.5) / 0.15) ** 2), flare=0.20)
    from soul_humanoid_parts import w_skirt
    w = {"Hips": 0.45, "ThighL": 0.55}
    ob = B.grid("Tasset", 8, 4, fn, mat, w, [V(0.05, 0, z_bot), V(0.05, 0, z_top)], rim=0.005)
    pts = [(fn(u, 0.86) + body.torso.nrm(z_top, lerp(a0, a1, u)) * 0.003, body.torso.nrm(z_top, lerp(a0, a1, u))) for u in (0.2, 0.8)]
    rv = B.rivets("TassetRivets", pts, rivet_mat, w, r=0.005)
    return [ob, rv]


def leg_armor(B, body, mat, mat_knee, mat_greave, rivet_mat, mat_strap):
    R = body.RL
    j = body.j
    Lt, Ls = body.th_len, body.sh_len
    obs = []
    TH, SH = body.thigh, body.shin
    # 大腿前片（平滑、略有中脊）
    obs.append(B.shell("Cuisse", TH, Lt * 0.28, Lt * 0.86, -78, 92, 12, 5, mat, "ThighL",
                       off=lambda u, v, ang, t: 0.020 + 0.004 * math.exp(-(angn(ang) / 14) ** 2), rim=0.0055))
    # 側面兩道皮帶（後側繞一圈）
    for k, tf in enumerate((0.42, 0.72)):
        with B.strap("strap_v"):
            obs.append(B.shell(f"CuisseStrap{k}", TH, Lt * tf - 0.009, Lt * tf + 0.009, 92, 282, 10, 1, mat_strap, "ThighL", off=0.008, rim=0.002))
        p = TH.pt(Lt * tf, 100, 0.017); n = TH.nrm(Lt * tf, 100)
        obs.append(_frame_buckle(B, f"CuisseBuckle{k}", p, TH.a, n, 0.008, 0.008, 0.0022, rivet_mat, "ThighL"))
    # 膝甲（圓頂）＋側扇（2 道刻線）
    wk = {"ThighL": 0.5, "ShinL": 0.5}
    c = j["ShinL"] + FWD * 0.010
    pole = (FWD * 0.97 + Z * 0.12).normalized()
    ex = X.copy(); ey = pole.cross(ex)
    obs.append(B.ellipsoid("Poleyn", c, (ex, ey, pole), (0.066, 0.074, 0.074), 16, 6, mat_knee, wk, v0=0, v1=0.5, rim=0.0055,
                           dent=lambda d, u, v: 1 + 0.09 * math.exp(-(v / 0.3) ** 2)))
    wc = j["ShinL"] + X * 0.066 + FWD * 0.010
    obs.append(B.ellipsoid("PoleynWing", wc, (FWD, Z, X), (0.054, 0.056, 0.014), 14, 4, mat_knee, wk, v0=0, v1=0.5, rim=0.003))
    for k, s in enumerate((0.55, 0.80)):
        ring = []
        for i in range(13):
            ph = math.radians(lerp(-150, 150, i / 12))
            ring.append(wc + (FWD * math.cos(ph) * 0.054 + Z * math.sin(ph) * 0.056) * s + X * (0.014 * math.sqrt(max(0, 1 - s * s)) + 0.0012))
        with B.strap("none"):
            obs.append(B.tube(f"PoleynWingLine{k}", ring, [0.0018] * len(ring), 4, mat_knee, wk, cap=False))
    obs.append(B.shell("PoleynUp", TH, Lt * 0.84, Lt * 0.97, -80, 80, 10, 1, mat_knee, {"ThighL": 0.8, "ShinL": 0.2},
                       off=lambda u, v, ang, t: 0.018 + 0.005 * v, rim=0.004))
    obs.append(B.shell("PoleynLo", SH, Ls * 0.04, Ls * 0.15, -80, 80, 10, 1, mat_knee, {"ThighL": 0.2, "ShinL": 0.8},
                       off=lambda u, v, ang, t: 0.022 - 0.005 * v, rim=0.004))
    # 脛甲：平滑筒（只有很淡的前中脊），下緣外張
    obs.append(B.shell("Greave", SH, Ls * 0.12, Ls * 0.96, 0, 360, 16, 7, mat_greave, "ShinL",
                       off=lambda u, v, ang, t: 0.010 + 0.0025 * math.exp(-(angn(ang) / 14) ** 2) + 0.012 * math.exp(-(angn(ang) / 55) ** 2) * math.sin(math.pi * clamp(v * 1.15)) ** 1.5
                       + 0.004 * smooth((v - 0.90) / 0.10),
                       rim=0.0045))
    # 後側 2 道皮帶扣（0.19H、0.12H）
    for k, zt in enumerate((0.19 * 1.8, 0.12 * 1.8)):
        t = (j["ShinL"].z - zt) / (j["ShinL"].z - j["FootL"].z) * Ls
        vv = t / Ls
        off = 0.010 + 0.007 * smooth((vv - 0.86) / 0.14) + 0.002
        with B.strap("strap_v"):
            obs.append(B.shell(f"GreaveStrap{k}", SH, t - 0.009, t + 0.009, 110, 250, 10, 1, mat_strap, "ShinL", off=off, rim=0.002))
        p = SH.pt(t, 128, off + 0.004); n = SH.nrm(t, 128)
        obs.append(_frame_buckle(B, f"GreaveBuckle{k}", p, SH.a, n, 0.008, 0.008, 0.0022, rivet_mat, "ShinL"))
    pts = []
    for a in (-60, 60):
        pts.append((SH.pt(Ls * 0.22, a, 0.0125), SH.nrm(Ls * 0.22, a)))
    pts += [(TH.pt(Lt * 0.32, a, 0.016), TH.nrm(Lt * 0.32, a)) for a in (-60, 70)]
    obs.append(B.rivets("LegRivets", pts[:2], rivet_mat, "ShinL", r=0.0045))
    obs.append(B.rivets("CuisseRivets", pts[2:], rivet_mat, "ThighL", r=0.0045))
    return obs


def boot(B, body, mat_leather, mat_plate, mat_sole, mat_strap):
    """皮靴（長 0.15H、寬 0.065H）＋靴面 5 片鐵疊片＋腳背皮帶。"""
    ank = body.j["FootL"]
    RF = 1.0
    st = [(0.076, 0.036, 0.060), (0.054, 0.050, 0.108), (0.010, 0.054, 0.124), (-0.045, 0.053, 0.098), (-0.100, 0.053, 0.076),
          (-0.150, 0.054, 0.064), (-0.172, 0.048, 0.056), (-0.184, 0.034, 0.044)]
    pts = []; radii = []
    for k, (y, wd, h) in enumerate(st):
        pts.append(V(ank.x + 0.0012 * max(k - 2, 0), ank.y + y, h * 0.5))
        radii.append((wd, h * 0.5))
    obs = []
    with B.strap("none"):
        obs.append(B.tube("Boot", pts, radii, 14, mat_leather, "FootL", flat=X, exp=2.3, sharp=45))
        # 靴筒（包住腳踝，上緣在脛甲裡）
        obs.append(B.tube("BootShaft", [V(ank.x, ank.y + 0.012, 0.040), V(ank.x, ank.y + 0.012, 0.115), V(ank.x, ank.y + 0.010, 0.150)],
                          [(0.046, 0.054), (0.044, 0.050), (0.043, 0.048)], 12, mat_leather, {"FootL": 0.6, "ShinL": 0.4}, cap=False))
        sole = []; sr = []
        for y, wd in ((0.082, 0.038), (0.05, 0.053), (0.0, 0.056), (-0.06, 0.054), (-0.12, 0.054), (-0.165, 0.048), (-0.190, 0.030)):
            sole.append(V(ank.x, ank.y + y, 0.013)); sr.append((wd * 1.02, 0.013))
        obs.append(B.tube("BootSole", sole, sr, 10, mat_sole, "FootL", flat=X, exp=5.0, sharp=50))
        # 鞋跟（方塊、厚 2.2 cm）＋鞋頭硬殼（略翹）
        obs.append(B.tube("BootHeel", [V(ank.x, ank.y + 0.080, 0.012), V(ank.x, ank.y + 0.030, 0.012)],
                          [(0.040, 0.020), (0.044, 0.020)], 8, mat_sole, "FootL", flat=X, exp=4.5, sharp=50))
        obs.append(B.tube("BootToe", [V(ank.x + 0.010, ank.y - 0.140, 0.034), V(ank.x + 0.011, ank.y - 0.175, 0.031), V(ank.x + 0.011, ank.y - 0.188, 0.026)],
                          [(0.056, 0.034), (0.050, 0.031), (0.028, 0.020)], 12, mat_leather, "FootL", flat=X, exp=2.6, sharp=45))
    # 靴面鐵疊片（5 片，由腳踝往腳尖，每片後緣蓋住下一片）
    for k in range(5):
        y0 = -0.030 - k * 0.030
        y1 = y0 - 0.036
        def fn(u, v, y0=y0, y1=y1, k=k):
            yy = lerp(y0, y1, v)
            # 線性內插 st 表
            for q in range(len(st) - 1):
                if st[q][0] >= yy >= st[q + 1][0]:
                    s = (yy - st[q][0]) / (st[q + 1][0] - st[q][0])
                    wd = lerp(st[q][1], st[q + 1][1], s); h = lerp(st[q][2], st[q + 1][2], s)
                    break
            else:
                wd, h = st[-1][1], st[-1][2]
            ph = math.radians(lerp(-80, 80, u))
            lift = 0.0025 + 0.0015 * v
            x = ank.x + 0.0012 * k + math.sin(ph) * (wd + lift)
            z = h * 0.5 + math.cos(ph) * (h * 0.5 + lift)
            return V(x, ank.y + yy, z)
        obs.append(B.grid(f"BootLame{k}", 10, 2, fn, mat_plate, "FootL", V(ank.x, ank.y + (y0 + y1) / 2, 0.02), rim=0.003))
    # 腳背皮帶＋扣
    with B.strap("strap_v"):
        def fs(u, v):
            ph = math.radians(lerp(-100, 100, u))
            y = ank.y + 0.020 + lerp(-0.010, 0.010, v)
            wd, h = 0.052, 0.120
            return V(ank.x + math.sin(ph) * (wd + 0.009), y, h * 0.5 + math.cos(ph) * (h * 0.5 + 0.009))
        obs.append(B.grid("BootStrap", 12, 1, fs, mat_strap, "FootL", V(ank.x, ank.y + 0.02, 0.03), rim=0.002))
    obs.append(_frame_buckle(B, "BootBuckle", V(ank.x + 0.056, ank.y + 0.020, 0.064), Z, X, 0.008, 0.008, 0.0022, mat_plate, "FootL"))
    return obs


# ---------------------------------------------------------------- 頭盔
def helmet(B, body, mat, mat_void, rivet_mat):
    hz0 = 0.855 * 1.817 - 0.003
    helm = Surf(V(0, -0.004, hz0), Z, [(0.00, 0.071, 0.082, 0, 0.010), (0.05, 0.076, 0.090, 0, 0.009),
                                       (0.11, 0.079, 0.094, 0, 0.005), (0.16, 0.079, 0.094, 0, 0.002),
                                       (0.195, 0.074, 0.089, 0, -0.001), (0.222, 0.066, 0.078, 0, -0.004),
                                       (0.242, 0.046, 0.055, 0, -0.006), (0.254, 0.023, 0.028, 0, -0.007),
                                       (0.2585, 0.002, 0.003, 0, -0.007)])
    TOP = 0.2584
    obs = []
    with B.strap("none"):
        obs.append(B.ellipsoid("HelmVoid", V(0, -0.004, hz0 + 0.120), (X, Y, Z), (0.076, 0.088, 0.112), 14, 8, mat_void, "Head", texel=0.3))
    BROW = 0.174       # 視縫上緣（0.95H）
    VTOP = 0.160       # 面罩上緣

    def brow(u):
        a = abs(angn(u * 360))
        return lerp(BROW, 0.030, smooth((a - 66) / 46))

    def skull_off(u, v, ang, t):
        a = angn(ang)
        mid = min(abs(a), 180 - abs(a))
        ridge = 0.008 * math.exp(-(mid / 4.5) ** 2) * smooth(v * 3) + 0.003 * math.exp(-(mid / 12) ** 2) * smooth(v * 3)
        flare = 0.008 * (1 - v) ** 4
        back = 0.012 * (1 - v) ** 2 * smooth((abs(a) - 110) / 50)
        return 0.004 + ridge + flare + back
    obs.append(B.shell("HelmSkull", helm, brow, TOP, 0, 360, 40, 14, mat, "Head", off=skull_off, rim=0.0045))
    # 眉上加強帶
    obs.append(B.shell("HelmBrow", helm, lambda u: brow(0.5 + (u - 0.5) * 150 / 360) + 0.002, lambda u: brow(0.5 + (u - 0.5) * 150 / 360) + 0.022,
                       -72, 72, 16, 1, mat, "Head", off=0.011, rim=0.0035))

    def visor_off(u, v, ang, t):
        a = angn(ang)
        prow = 0.030 * (1 - min(abs(a), 60) / 60) ** 1.3 * math.sin(math.pi * clamp(v * 0.80 + 0.14)) ** 0.7
        keel = 0.016 * math.exp(-(a / 5.0) ** 2) * math.sin(math.pi * clamp(v * 0.88 + 0.08)) ** 0.8
        return 0.004 + prow + keel + 0.006 * (1 - v) ** 3
    obs.append(B.shell("HelmVisor", helm, -0.004, lambda u: VTOP - 0.008 * abs(u - 0.5) * 2, -88, 88, 26, 9, mat, "Head", off=visor_off, rim=0.0045))
    obs.append(B.shell("HelmChin", helm, -0.012, 0.028, 80, 280, 14, 2, mat, "Head", off=0.002, rim=0.0035))
    hp = []
    for sgn in (-1, 1):
        hp.append((helm.pt(0.120, sgn * 88, 0.006), helm.nrm(0.120, sgn * 88)))
    obs.append(B.rivets("HelmPivot", hp, rivet_mat, "Head", r=0.010))
    hp = []
    for a in (-150, -120, -95, 95, 120, 150, 180):
        hp.append((helm.pt(brow((a % 360) / 360) + 0.012, a, 0.012), helm.nrm(0.06, a)))
    for a in (-62, -40, 40, 62):
        hp.append((helm.pt(BROW + 0.012, a, 0.016), helm.nrm(BROW, a)))
    obs.append(B.rivets("HelmRivets", hp, rivet_mat, "Head", r=0.0045))
    # 面罩下半部右側（角色右 = 負角度）2 排透氣孔（各 5 個，孔徑 0.004H）
    hp = []
    for row in range(2):
        for col in range(5):
            a = -50 + col * 7.5 + row * 3
            t = (0.040 + row * 0.018)
            v = clamp((t + 0.004) / (VTOP + 0.004))
            o = visor_off(0, v, a, t)
            hp.append((helm.pt(t, a, o + 0.0004), helm.nrm(t, a)))
    obs.append(B.rivets("HelmBreaths", hp, mat_void, "Head", r=0.0036))
    return obs, helm


# ---------------------------------------------------------------- 羊毛披風：圍巾段＋背段兩層
def scarf(B, body, mat, seed=5):
    """先在肩上繞成圍巾（厚、橫向皺褶 3–4 條），胸前交疊，右胸別針；背面接披風。"""
    rnd = random.Random(seed)
    nu, nv = 48, 8
    cut = rag_profile(nu, rnd, 0.10)
    ph = rnd.uniform(0, 6.28)

    def ta(u):
        a = angn(u * 360)
        k = int(round(u * nu)) % nu
        side = math.exp(-((abs(a) - 90) / 40) ** 2)
        fr = math.exp(-((a + 22) / 38) ** 2)              # 前面在右胸往下垂成 V
        bk = math.exp(-((abs(a) - 180) / 70) ** 2)
        return body.tz(0.83) + 0.014 * cut[k] - 0.010 * side - 0.11 * fr - 0.03 * bk + 0.02 * math.exp(-((a - 50) / 30) ** 2)

    def offn(u, v, ang, t):
        a = angn(ang)
        side = math.exp(-((abs(a) - 90) / 40) ** 2)
        right = math.exp(-((a + 90) / 30) ** 2)
        # 橫向厚皺褶（沿 v 方向起伏）
        roll = 0.010 * math.sin(v * math.pi * 3.5 + ph + 0.6 * math.sin(ang * 0.05)) ** 2
        fold = 0.006 * math.sin(math.radians(ang) * 9 + ph + 2.0 * v) * (1 - v) ** 0.8
        top = 0.020 * math.exp(-((v - 0.92) / 0.10) ** 2)
        back = math.exp(-((abs(a) - 180) / 55) ** 2)
        return 0.036 + 0.026 * side * (1 - v) ** 0.7 + 0.018 * right * (1 - v) ** 0.5 + 0.030 * back + roll * 1.4 + fold + top + 0.016 * (1 - v) ** 2.5
    ob = B.shell("Scarf", body.torso, ta, body.tz(1.0), 0, 360, nu, nv, mat, {"Spine2": 0.85, "Neck": 0.15}, off=offn, sharp=60)
    ob["cloth"] = 0.010
    return ob


def ring_brooch(B, body, mat):
    a = -24
    z = body.tz(0.74)
    n = body.torso.nrm(z, a)
    c = body.torso.pt(z, a, 0.074)
    e1 = Z.cross(n).normalized(); e2 = n.cross(e1)
    ring = [c + (e1 * math.cos(2 * math.pi * k / 16) + e2 * math.sin(2 * math.pi * k / 16)) * 0.024 for k in range(16)]
    with B.strap("none"):
        ob = B.tube("Brooch", ring + [ring[0]], [0.0048] * 17, 7, mat, "Spine2", cap=False)
        B.tube("BroochPin", [c - e1 * 0.030 + e2 * 0.006 + n * 0.006, c + e1 * 0.030 - e2 * 0.004 + n * 0.004], [0.0028, 0.0022], 5, mat, "Spine2")
    return [ob]


def _hole_r(a, hu, hv, wob):
    """撕裂洞的半徑：低頻不規則＋高頻鋸齒（撕口）。"""
    return (1 + wob * math.sin(3 * a + hu * 17) + 0.5 * wob * math.sin(5 * a + hv * 9)
            + 0.16 * math.sin(13 * a + hu * 31) + 0.10 * math.sin(23 * a + hv * 41))


def cape_panel(B, name, top, nrm, length, mat, w, nu, nv, rag, fold_amp, fold_n, holes, seed, flare=0.10, sag=0.03, spread=-0.30,
               thick=0.010):
    """背後的披風片：下緣撕破（長短差 0.07H），縱向皺褶，不規則圓形破洞（用細格挖洞再把洞緣拉圓）。
    holes：[(u, v, ru, rv)] 參數空間的橢圓。"""
    rnd = random.Random(seed)
    cut = rag_profile(nu, rnd, 0.22)
    jit = [rnd.uniform(-0.3, 0.3) / nu for _ in range(nu + 1)]
    ph = rnd.uniform(0, 6.28)
    sd = X

    def fn(u, v):
        x = u * nu; i = min(int(x), nu - 1); f = x - i
        Lc = length * (1 - rag * lerp(cut[i], cut[i + 1], f))
        n = nrm(u)
        uu = u + lerp(jit[i], jit[i + 1], f) * smooth(v * 1.5)
        p = top(u) - Z * (Lc * v)
        wave = math.sin(2 * math.pi * fold_n * uu + ph) + 0.4 * math.sin(2 * math.pi * fold_n * 2.2 * uu + ph * 2)
        p = p + n * (flare * Lc * v ** 1.3 + fold_amp * wave * smooth(v * 2.5) * (0.4 + 0.6 * v) + sag * math.sin(math.pi * min(v * 1.2, 1)))
        p = p + sd * ((uu - 0.5) * spread * v ** 0.8)
        return p

    def inhole(i, j):
        u = (i + 0.5) / nu; v = (j + 0.5) / nv
        for (hu, hv, ru, rv, wob) in holes:
            a = math.atan2((v - hv) / rv, (u - hu) / ru)
            r = _hole_r(a, hu, hv, wob)
            if ((u - hu) / ru) ** 2 + ((v - hv) / rv) ** 2 < r * r:
                return True
        return False
    inside = [top(0.5) - nrm(0.5) * 0.5 - Z * length * k / 4 for k in range(5)]
    ob = B.grid(name, nu, nv, fn, mat, w, inside, holes=inhole, texel=1.0, sharp=60)
    rim = _round_holes(ob, nu, nv, holes, fn, inhole)
    ob["cloth"] = thick
    # 毛邊：洞緣（線頭往洞中心）＋下緣（往下）
    roots = [(p, -d, sd) for p, d, sd in rim]
    for i in range(nu + 1):
        u = i / nu
        p = fn(u, 1.0)
        sd = (fn(min(1, u + 0.01), 1.0) - fn(max(0, u - 0.01), 1.0)).normalized()
        dn = (fn(u, 1.0) - fn(u, 0.97)).normalized()
        roots.append((p, dn, sd))
    fringe(B, name + "Fray", roots, mat + "Fray", w, rnd, n_per=2, length=(0.008, 0.022), width=0.0045)
    return ob


def _round_holes(ob, nu, nv, holes, fn, inhole):
    """洞緣的頂點：拉到最近的洞（橢圓＋扭曲）邊界上，讓方洞變圓、變不規則。"""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv["atlas"]
    # 用頂點位置反查 (u,v)：建一個參數格子點的字典
    grid = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            p = fn(i / nu, j / nv)
            grid[(round(p.x, 5), round(p.y, 5), round(p.z, 5))] = (i, j)
    moved = 0
    rim = []
    for vtx in bm.verts:
        if not vtx.is_boundary:
            continue
        key = (round(vtx.co.x, 5), round(vtx.co.y, 5), round(vtx.co.z, 5))
        if key not in grid:
            continue
        gi, gj = grid[key]
        if not any(inhole(ci, cj) for ci in (gi - 1, gi) for cj in (gj - 1, gj) if 0 <= ci < nu and 0 <= cj < nv):
            continue
        u, v = gi / nu, gj / nv
        best = None
        for (hu, hv, ru, rv, wob) in holes:
            du, dv = (u - hu) / ru, (v - hv) / rv
            d = math.hypot(du, dv)
            if d < 1.8 and (best is None or d < best[0]):
                best = (d, hu, hv, ru, rv, wob)
        if not best:
            continue
        d, hu, hv, ru, rv, wob = best
        a = math.atan2((v - hv) / rv, (u - hu) / ru)
        r = _hole_r(a, hu, hv, wob)
        nu_ = hu + math.cos(a) * ru * r
        nv_ = hv + math.sin(a) * rv * r
        if 0.0 < nu_ < 1.0 and 0.0 < nv_ < 1.0:
            p = fn(nu_, nv_)
            du_ = fn(min(1, nu_ + 0.01), nv_) - fn(max(0, nu_ - 0.01), nv_)
            dv_ = fn(nu_, min(1, nv_ + 0.01)) - fn(nu_, max(0, nv_ - 0.01))
            nrm = du_.cross(dv_).normalized()
            curl = 0.004 + 0.006 * (0.5 + 0.5 * math.sin(7 * a + hu * 13))      # 洞緣往外翻捲
            vtx.co = p + nrm * curl
            rim.append((vtx.co.copy(), (vtx.co - fn(hu, hv)).normalized(), nrm.cross((vtx.co - fn(hu, hv)).normalized()).normalized()))
            moved += 1
    bm.to_mesh(me); bm.free()
    return rim


# ---------------------------------------------------------------- 長劍（0.60H）
def sword(B, c, blade, edge, mat_blade, mat_iron, mat_grip, seed=3):
    """c：握點中心。劍身 0.46H、寬 0.026H、厚 0.004H、血槽 0.008H、刃口小缺口；護手 0.13H 兩端下彎；握柄 0.09H；圓盤劍首 0.03H。"""
    H = 1.8
    rnd = random.Random(seed)
    blade = blade.normalized(); edge = (edge - blade * edge.dot(blade)).normalized()
    flat = blade.cross(edge).normalized()
    grip = 0.09 * H
    g0 = c + blade * (grip * 0.5)                # 護手位置
    Lb = 0.48 * H
    hw0 = 0.026 * H * 0.5
    th = 0.004 * H * 0.5
    fw = 0.008 * H * 0.5
    nicks = [(rnd.uniform(0.15, 0.85), rnd.choice((-1, 1)), rnd.uniform(0.002, 0.0035)) for _ in range(5)]

    def width(s):
        w = hw0 * (1 - 0.30 * s) * (1 if s < 0.86 else max(0.04, 1 - ((s - 0.86) / 0.14) ** 1.15))
        return w

    # 截面（寬向 px、厚向 py）：菱形刃＋中央血槽；("f", 位置比例, 深度) 是血槽上的點（寬度固定 0.008H，不隨劍身變窄）
    prof = [(1.0, 0.0), (0.8, 0.5), (0.5, 0.92), ("f", 1.0, 1.0), ("f", 0.45, 0.68), ("f", 0.0, 0.55), ("f", -0.45, 0.68), ("f", -1.0, 1.0),
            (-0.5, 0.92), (-0.8, 0.5), (-1.0, 0.0), (-0.8, -0.5), (-0.5, -0.92), ("f", -1.0, -1.0), ("f", -0.45, -0.68), ("f", 0.0, -0.55),
            ("f", 0.45, -0.68), ("f", 1.0, -1.0), (0.5, -0.92), (0.8, -0.5)]
    NS = 30

    def fn(u, v):
        k = int(round(u * len(prof))) % len(prof)
        q = prof[k]
        s = v
        w = width(s)
        fuller = clamp((0.78 - s) / 0.06) * clamp((s - 0.01) / 0.04)
        if q[0] == "f":
            fx = min(fw / max(w, 1e-4), 0.62)
            px = q[1] * fx
            py = math.copysign(lerp(1.0, abs(q[2]), fuller), q[2])
        else:
            px, py = q
        x = px * w
        for (ns, sg, dep) in nicks:
            if sg * px > 0.95:
                x -= sg * dep * math.exp(-((s - ns) / 0.012) ** 2)
        y = py * th * (1 - 0.6 * smooth((s - 0.85) / 0.15))
        p = g0 + blade * (0.010 + Lb * s)
        return p + edge * x + flat * y
    with B.strap("none"):
        ob = B.grid("Blade", len(prof), NS, fn, mat_blade, "Weapon", [g0 + blade * Lb * k / 4 for k in range(5)], closed_u=True, cap0=True,
                    cap1=True, sharp=25)
    obs = [ob]
    # 護手：長 0.13H，兩端往劍尖方向略彎
    gl = 0.13 * H * 0.5
    gp = []; gr = []
    for k in range(9):
        s = -1 + 2 * k / 8
        bend = 0.012 * abs(s) ** 2.2
        gp.append(g0 + edge * (gl * s) + blade * (0.004 + bend))
        r = 0.0062 * (1.0 + 0.25 * (1 - abs(s))) if abs(s) < 0.97 else 0.0075
        gr.append((r * 1.15, r))
    with B.strap("none"):
        obs.append(B.tube("Guard", gp, gr, 8, mat_iron, "Weapon", flat=blade))
        obs.append(B.ellipsoid("GuardBlock", g0 + blade * 0.004, (edge, flat, blade), (0.020, 0.011, 0.012), 10, 6, mat_iron, "Weapon"))
    # 握柄（皮纏，略呈紡錘）
    n = 7
    hp = [c + blade * (grip * (0.5 - k / (n - 1))) for k in range(n)]
    hr = [(0.0145 * H / 1.8) * (0.92 + 0.12 * math.sin(math.pi * k / (n - 1))) for k in range(n)]
    with B.strap("strap_u"):
        obs.append(B.tube("Grip", hp, hr, 10, mat_grip, "Weapon", flat=edge))
    # 圓盤劍首
    pc = c - blade * (grip * 0.5 + 0.011)
    with B.strap("none"):
        obs.append(B.tube("Pommel", [pc + blade * 0.011, pc + blade * 0.008, pc - blade * 0.008, pc - blade * 0.011],
                          [(0.022, 0.022), (0.027, 0.027), (0.027, 0.027), (0.021, 0.021)], 16, mat_iron, "Weapon"))
    return obs, Lb + 0.010 + grip * 0.5
