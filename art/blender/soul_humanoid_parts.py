"""魂系人形角色的共用盔甲／衣物分件產生器。全部以左側建模，再鏡射到右側。"""
import math, random
from mathutils import Vector
from soul_humanoid_lib import *


def angn(a):
    """角度正規化到 -180~180（0 為正前方）。"""
    return ((a + 180) % 360) - 180


# ---------------------------------------------------------------- 內層（鎖子甲／襯衣）
def under_torso(B, body, mat, texel=0.4, off=0.0):
    return B.shell("UnderTorso", body.torso, body.tz(-0.135), body.tz(1.12), 0, 360, 20, 16, mat, body.w_torso(),
                   off=off, cap0=True, texel=texel)


def under_arm(B, body, mat, texel=0.8, off=0.0):
    a = B.shell("UnderUArm", body.uarm, -0.02, body.ua_len + 0.012, 0, 360, 12, 5, mat, body.w_elbow(), off=off, texel=texel)
    b = B.shell("UnderFArm", body.farm, -0.012, body.fa_len, 0, 360, 12, 5, mat, body.w_elbow(), off=off, texel=texel)
    return B.both([a, b])


def under_leg(B, body, mat_thigh, mat_shin=None, texel=0.8, off=0.0):
    a = B.shell("UnderThigh", body.thigh, -0.03, body.th_len + 0.015, 0, 360, 12, 6, mat_thigh, body.w_knee(), off=off, texel=texel)
    b = B.shell("UnderShin", body.shin, -0.015, body.sh_len, 0, 360, 12, 5, mat_shin or mat_thigh, body.w_knee(), off=off, texel=texel)
    return B.both([a, b])


def w_skirt(body, z_hi, z_lo, maxw=0.7):
    """裙狀分件：上緣跟骨盆，下緣依左右分給兩條大腿。"""
    def f(co):
        s = smooth((z_hi - co.z) / (z_hi - z_lo)) * maxw
        l = smooth(0.5 + co.x / (0.20 * body.U))
        front = 0.55 + 0.45 * smooth(0.5 - co.y / (0.16 * body.U))
        s *= front
        return {"Hips": 1 - s, "ThighL": s * l, "ThighR": s * (1 - l)}
    return f


def mail_skirt(B, body, mat, z_top, z_bot, flare=0.03, rag=0.02, seed=3, texel=0.9):
    rnd = random.Random(seed)
    nu = 28
    cut = [rnd.random() for _ in range(nu)]
    R = body.R

    def t0(u):
        k = int(round(u * nu)) % nu
        return z_bot + rag * cut[k] * (1 if k % 2 else 0.3)

    def off(u, v, ang, t):
        return 0.014 * R + flare * R * (1 - v) + 0.004 * math.sin(ang * 0.21) * (1 - v)
    return B.shell("MailSkirt", body.torso, t0, z_top, 0, 360, nu, 5, mat, w_skirt(body, body.hzv + 0.02, z_bot, 0.75),
                   off=off, texel=texel)


# ---------------------------------------------------------------- 軀幹板甲
def cuirass(B, body, mat, off=0.014, keel=0.012, globe=0.018, t0=0.30, t_neck=0.90, t_arm=0.70, rim=0.006,
            w="Spine2", belly=0.0, rivet_mat=None):
    R = body.R

    def t1(u):
        a = angn(u * 360)
        hole = math.exp(-((abs(a) - 90) / 40) ** 2)
        return body.tz(lerp(t_neck, t_arm, hole))

    def offn(u, v, ang, t):
        a = angn(ang)
        front = math.exp(-(a / 62) ** 2)
        k = keel * R * math.exp(-(a / 8) ** 2) * math.sin(math.pi * clamp(v * 1.05))
        g = globe * R * front * math.sin(math.pi * clamp((v - 0.02) / 0.85)) ** 1.2
        bl = belly * R * front * math.sin(math.pi * clamp(v / 0.6))
        flare = 0.014 * R * (1 - smooth(v / 0.14))
        return off * R + k + g + bl + flare
    ob = B.shell("Cuirass", body.torso, body.tz(t0), t1, 0, 360, 28, 10, mat, w, off=offn, rim=rim * R)
    if rivet_mat:
        pts = []
        for a in range(-150, 181, 30):
            t = body.tz(t0) + 0.022 * body.U
            o = off * R + 0.014 * R * 0.6 + 0.002
            pts.append((body.torso.pt(t, a, o), body.torso.nrm(t, a)))
        B.rivets("CuirassRivets", pts, rivet_mat, w, r=0.006 * body.U)
    return ob


def gorget(B, body, mat, off=0.012, rim=0.004, t0=0.88, t1=1.10):
    R = body.R

    def offn(u, v, ang, t):
        return off * R + 0.016 * R * (1 - v) ** 2 + 0.006 * R * smooth((v - 0.8) / 0.2)
    return B.shell("Gorget", body.torso, body.tz(t0), body.tz(t1), 0, 360, 18, 4, mat, {"Spine2": 0.65, "Neck": 0.35},
                   off=offn, rim=rim * R)


def fauld(B, body, mat, n=3, t_top=0.31, h=0.045, off=0.022, step=0.004, flare=0.012, rim=0.004, rivet_mat=None):
    R = body.R; U = body.U
    obs = []
    zt = body.tz(t_top)
    pts = []
    for k in range(n):
        z1 = zt - k * h * U + 0.012 * U
        z0 = zt - (k + 1) * h * U

        def offn(u, v, ang, t, k=k):
            return (off + k * step) * R + flare * R * (1 - v)
        wk = {"Spine": 0.6, "Hips": 0.4} if k == 0 else w_skirt(body, zt - h * U, zt - n * h * U - 0.05 * U, 0.35)
        obs.append(B.shell(f"Fauld{k}", body.torso, z0, z1, 0, 360, 28, 2, mat, wk, off=offn, rim=rim * R))
        if rivet_mat:
            for a in (-150, -90, -30, 30, 90, 150):
                t = z0 + h * U * 0.55
                pts.append((body.torso.pt(t, a + k * 12, (off + k * step) * R + flare * R * 0.45 + 0.002), body.torso.nrm(t, a + k * 12)))
    if rivet_mat and pts:
        B.rivets("FauldRivets", pts, rivet_mat, "Hips", r=0.005 * U)
    return obs, zt - n * h * U


def tasset(B, body, mat, z_top, length=0.20, a0=10, a1=64, off=0.036, rim=0.005, w=None, point=0.035, rivet_mat=None,
           name="Tasset"):
    R = body.R; U = body.U
    w = w or {"Hips": 0.5, "ThighL": 0.5}

    def t0(u):
        return z_top - length * U + point * U * abs(u - 0.5) * 2

    def offn(u, v, ang, t):
        return off * R + 0.02 * R * (1 - v) + 0.006 * R * math.exp(-((u - 0.5) / 0.12) ** 2)
    ob = B.shell(name, body.torso, t0, z_top, a0, a1, 6, 4, mat, w, off=offn, rim=rim * R)
    obs = [ob]
    if rivet_mat:
        pts = []
        for u in (0.15, 0.5, 0.85):
            a = lerp(a0, a1, u); t = z_top - 0.02 * U
            pts.append((body.torso.pt(t, a, off * R + 0.003), body.torso.nrm(t, a)))
        obs.append(B.rivets(name + "Rivets", pts, rivet_mat, w, r=0.006 * U))
    return obs


def belt(B, body, z, mat, w, h=0.045, thick=0.007, off=0.02, tilt=0.0, tilt_dir=90, name="Belt", nu=28):
    """繞軀幹的皮帶。tilt：朝 tilt_dir 方向下斜的高度差。"""
    U = body.U

    def fn(u, v):
        ang = u * 360
        zz = z + tilt * U * math.cos(math.radians(ang - tilt_dir)) * -1
        k = int(round(v * 3))
        dz = (-h / 2, -h / 2, h / 2, h / 2)[k] * U
        o = (off - 0.004, off + thick, off + thick, off - 0.004)[k] * body.R
        return body.torso.pt(zz + dz, ang, o)
    return B.grid(name, nu, 3, fn, mat, w, [V(0, 0, z - 0.1), V(0, 0, z), V(0, 0, z + 0.1)], closed_u=True, sharp=30)


def box(B, name, c, ax, ay, az, sx, sy, sz, mat, w, exp=5.0, segs=12, **kw):
    """圓角方塊：中心 c，三軸方向與半尺寸。沿 az 擠出。"""
    az = az.normalized()
    pts = [c - az * sz, c - az * (sz * 0.92), c + az * (sz * 0.92), c + az * sz]
    k = 0.86
    radii = [(sx * k, sy * k), (sx, sy), (sx, sy), (sx * k, sy * k)]
    return B.tube(name, pts, radii, segs, mat, w, exp=exp, flat=ax, **kw)


def pouch(B, body, z, ang, mat, w="Hips", size=1.0, off=0.03, flap_mat=None):
    U = body.U * size
    S = body.torso
    n = S.nrm(z, ang)
    side = Z.cross(n).normalized()
    c = S.pt(z, ang, off * body.R) + n * 0.028 * U - Z * 0.055 * U
    a = box(B, "Pouch", c, side, Z, n, 0.055 * U, 0.06 * U, 0.030 * U, mat, w, exp=4)
    b = box(B, "PouchFlap", c + Z * 0.028 * U + n * 0.006 * U, side, Z, n, 0.058 * U, 0.036 * U, 0.030 * U, flap_mat or mat, w, exp=4)
    return [a, b]


def buckle(B, body, z, ang, mat, w="Hips", off=0.03, size=1.0):
    U = body.U * size
    S = body.torso
    n = S.nrm(z, ang)
    side = Z.cross(n).normalized()
    c = S.pt(z, ang, off * body.R)
    return box(B, "Buckle", c, side, Z, n, 0.032 * U, 0.030 * U, 0.006 * U, mat, w, exp=4)


def strap_hang(B, body, z, ang, mat, length=0.22, width=0.02, off=0.03, w=None, name="StrapEnd"):
    """腰帶垂下的皮帶尾。"""
    U = body.U
    S = body.torso
    n = S.nrm(z, ang)
    side = Z.cross(n).normalized()
    p0 = S.pt(z, ang, off * body.R) + n * 0.004
    pts = [p0, p0 - Z * length * 0.5 * U + n * 0.01 * U, p0 - Z * length * U + n * 0.018 * U + side * 0.015 * U]
    return B.tube(name, pts, [(width * U, 0.004 * U)] * 3, 6, mat, w or w_skirt(body, z, z - length * U, 0.4), exp=4, flat=side)


# ---------------------------------------------------------------- 肩甲與手臂
def pauldron(B, body, mat, size=1.0, lames=3, haute=0.0, rivet_mat=None, name="Pauldron", lame_arc=118, tilt=0.65):
    j = body.j; R = body.RL * size; U = body.U
    out = body.uarm.u
    pole = (out * 0.75 + Z * tilt).normalized()
    ex = (FWD - pole * FWD.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["UpperArmL"] + pole * (0.012 * R) - Z * 0.01 * R
    rad = (0.112 * R, 0.100 * R, 0.100 * R)
    wd = {"ShoulderL": 0.55, "UpperArmL": 0.45}
    obs = [B.ellipsoid(name, c, (ex, ey, pole), rad, 20, 7, mat, wd, v0=0.0, v1=0.54, rim=0.006 * R,
                       dent=lambda d, u, v: 1 + 0.07 * smooth((v - 0.75) / 0.25))]
    if haute > 0:
        def fn(u, v):
            ph = math.radians(lerp(188, 352, u)); th = math.radians(46)
            d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
            p = c + ex * (d.x * rad[0]) + ey * (d.y * rad[1]) + pole * (d.z * rad[2])
            up = (Z * 0.95 + out * 0.22).normalized()
            prof = math.sin(math.pi * u) ** 0.35
            return p + up * (haute * R * v * prof) + out * (0.012 * R * v * v) - pole * 0.004
        obs.append(B.grid(name + "Haute", 12, 3, fn, mat, wd, c - ey * 0.2, rim=0.004 * R))
    S = body.uarm
    pts = []
    for k in range(lames):
        ta = (0.045 + k * 0.042) * U * size + 0.02 * R
        tb = ta + 0.062 * U * size

        def offn(u, v, ang, t, k=k):
            return (0.034 - k * 0.006) * R + 0.010 * R * v
        wk = {"ShoulderL": 0.25, "UpperArmL": 0.75} if k == 0 else "UpperArmL"
        obs.append(B.shell(f"{name}Lame{k}", S, ta, tb, 90 - lame_arc, 90 + lame_arc, 10, 2, mat, wk, off=offn, rim=0.005 * R))
        if rivet_mat:
            for a in (90 - lame_arc + 14, 90 + lame_arc - 14):
                t = tb - 0.02 * U
                pts.append((S.pt(t, a, (0.034 - k * 0.006) * R + 0.008 * R + 0.002), S.nrm(t, a)))
    if rivet_mat:
        for ph in (25, 155, 90):
            d = Vector((math.sin(1.45) * math.cos(math.radians(ph)), math.sin(1.45) * math.sin(math.radians(ph)), math.cos(1.45)))
            p = c + (ex * (d.x * rad[0]) + ey * (d.y * rad[1]) + pole * (d.z * rad[2])) * 1.05
            pts.append((p, p - c))
        obs.append(B.rivets(name + "Rivets", pts, rivet_mat, "UpperArmL", r=0.006 * U))
    return obs


def arm_armor(B, body, mat, rivet_mat=None, rerebrace=True, wing=True, cuff=0.030, ridge=0.004):
    R = body.RL; U = body.U
    j = body.j
    obs = []
    if rerebrace:
        obs.append(B.shell("Rerebrace", body.uarm, body.ua_len * 0.50, body.ua_len * 0.90, 0, 360, 12, 3, mat, "UpperArmL",
                           off=lambda u, v, ang, t: 0.010 * R + 0.004 * R * abs(v - 0.5) * 2, rim=0.005 * R))
    # 肘甲
    bend = (body.fd - body.ud * body.fd.dot(body.ud)).normalized()
    pole = (-bend * 0.8 + body.uarm.u * 0.45 - (body.ud + body.fd) * 0.0).normalized()
    ex = (body.ud + body.fd).normalized(); ex = (ex - pole * ex.dot(pole)).normalized()
    ey = pole.cross(ex)
    c = j["ForearmL"] + bend * 0.012 * R
    we = {"UpperArmL": 0.5, "ForearmL": 0.5}
    obs.append(B.ellipsoid("Couter", c, (ex, ey, pole), (0.075 * R, 0.066 * R, 0.068 * R), 12, 5, mat, we, v0=0, v1=0.52,
                           rim=0.005 * R, dent=lambda d, u, v: 1 + 0.10 * math.exp(-((v - 0.0) / 0.25) ** 2)))
    if wing:
        wo = body.uarm.u
        wc = j["ForearmL"] + wo * 0.060 * R + bend * 0.02 * R
        e1 = (body.ud + body.fd).normalized(); e2 = wo.cross(e1).normalized()
        obs.append(B.ellipsoid("CouterWing", wc, (e1, e2, wo), (0.055 * R, 0.048 * R, 0.014 * R), 10, 4, mat, we, v0=0, v1=0.5,
                               rim=0.003 * R))
    Lf = body.fa_len
    obs.append(B.shell("Vambrace", body.farm, Lf * 0.20, Lf * 0.80, 0, 360, 12, 4, mat, "ForearmL",
                       off=lambda u, v, ang, t: 0.010 * R + ridge * R * math.exp(-(angn(ang - 130) / 14) ** 2), rim=0.005 * R))
    obs.append(B.shell("GauntletCuff", body.farm, Lf * 0.62, Lf * 1.0, 0, 360, 12, 3, mat, "ForearmL",
                       off=lambda u, v, ang, t: lerp(cuff, 0.012, v ** 0.8) * R, rim=0.005 * R))
    if rivet_mat:
        pts = []
        for a in (40, 140, 220, 320):
            t = Lf * 0.25
            pts.append((body.farm.pt(t, a, 0.012 * R), body.farm.nrm(t, a)))
            t = Lf * 0.66
            pts.append((body.farm.pt(t, a, cuff * R * 0.95), body.farm.nrm(t, a)))
        obs.append(B.rivets("ArmRivets", pts, rivet_mat, "ForearmL", r=0.005 * U))
    return obs


def hand(B, body, mat_plate, mat_finger=None, open_amt=0.0):
    """護手：掌背甲片＋四指握拳（繞握持軸捲曲）＋拇指。open_amt>0 手指張開一些。"""
    R = body.RL
    W = body.j["HandL"]; a = body.hand_a; v = body.hand_v; u = body.hand_u
    mf = mat_finger or mat_plate
    obs = []
    K = body.knuckle
    pts = [W - a * 0.012 * R, W + a * 0.03 * R + u * 0.004 * R, K - a * 0.004 * R + u * 0.004 * R, K + a * 0.006 * R]
    obs.append(B.tube("HandBack", pts, [(0.036 * R, 0.022 * R), (0.044 * R, 0.022 * R), (0.047 * R, 0.019 * R), (0.044 * R, 0.014 * R)],
                      10, mat_plate, "HandL", exp=3.0, flat=v))
    rc = body.grip_rc * (1 + open_amt * 0.8)
    er = body.knuckle_dir
    et = (a - er * a.dot(er)).normalized()
    gc0 = K - er * rc
    sweep = 235 * (1 - open_amt * 0.55)
    for i, o in enumerate((-0.034, -0.0115, 0.0115, 0.034)):
        g = gc0 + v * o * R - a * (0.004 * R * abs(i - 1.3))
        fp = []
        nseg = 5
        ln = (1.0, 1.08, 1.0, 0.86)[i]
        for k in range(nseg + 1):
            th = math.radians(sweep * ln * k / nseg)
            fp.append(g + (er * math.cos(th) + et * math.sin(th)) * rc)
        obs.append(B.tube(f"Finger{i}", fp, [body.finger_r * 1.08] + [body.finger_r] * (nseg - 1) + [body.finger_r * 0.8], 6, mf, "HandL",
                          texel=0.8))
    # 拇指：從虎口繞到食指上方
    g = gc0 + v * 0.058 * R
    tp = [W + a * 0.022 * R + v * 0.034 * R - u * 0.004 * R]
    for th in (150, 95, 40):
        thr = math.radians(th)
        tp.append(g + (-er * math.cos(thr) * 1.0 + et * math.sin(thr)) * rc * 0.95 - v * 0.006 * R * (150 - th) / 110)
    obs.append(B.tube("Thumb", tp, [0.016 * R, 0.0145 * R, 0.0125 * R, 0.010 * R], 6, mf, "HandL", texel=0.8))
    return obs


# ---------------------------------------------------------------- 腿甲
def leg_armor(B, body, mat, rivet_mat=None, cuisse=True, wing=True, greave_ridge=0.006, cuisse_arc=(-105, 125)):
    R = body.RL; U = body.U
    j = body.j
    Lt, Ls = body.th_len, body.sh_len
    obs = []
    if cuisse:
        obs.append(B.shell("Cuisse", body.thigh, Lt * 0.20, Lt * 0.88, cuisse_arc[0], cuisse_arc[1], 10, 4, mat, "ThighL",
                           off=lambda u, v, ang, t: 0.012 * R + 0.006 * R * math.exp(-(angn(ang) / 14) ** 2), rim=0.006 * R))
    wk = {"ThighL": 0.5, "ShinL": 0.5}
    c = j["ShinL"] + FWD * 0.010 * R
    pole = (FWD * 0.97 + Z * 0.12).normalized()
    ex = X.copy(); ey = pole.cross(ex)
    obs.append(B.ellipsoid("Poleyn", c, (ex, ey, pole), (0.074 * R, 0.082 * R, 0.082 * R), 12, 5, mat, wk, v0=0, v1=0.5, rim=0.006 * R,
                           dent=lambda d, u, v: 1 + 0.08 * math.exp(-(v / 0.3) ** 2)))
    if wing:
        wc = j["ShinL"] + X * 0.074 * R + FWD * 0.012 * R
        obs.append(B.ellipsoid("PoleynWing", wc, (FWD, Z, X), (0.050 * R, 0.058 * R, 0.014 * R), 10, 4, mat, wk, v0=0, v1=0.5, rim=0.003 * R))
    obs.append(B.shell("PoleynUp", body.thigh, Lt * 0.84, Lt * 0.96, -85, 85, 8, 1, mat, {"ThighL": 0.8, "ShinL": 0.2},
                       off=lambda u, v, ang, t: 0.020 * R + 0.006 * R * v, rim=0.004 * R))
    obs.append(B.shell("PoleynLo", body.shin, Ls * 0.04, Ls * 0.15, -85, 85, 8, 1, mat, {"ThighL": 0.2, "ShinL": 0.8},
                       off=lambda u, v, ang, t: 0.024 * R - 0.006 * R * v, rim=0.004 * R))
    obs.append(B.shell("Greave", body.shin, Ls * 0.12, Ls * 0.95, 0, 360, 12, 6, mat, "ShinL",
                       off=lambda u, v, ang, t: 0.011 * R + greave_ridge * R * math.exp(-(angn(ang) / 12) ** 2) + 0.006 * R * smooth((v - 0.85) / 0.15),
                       rim=0.005 * R))
    if rivet_mat:
        pts = []
        for a in (-70, 70):
            for tf in (0.3, 0.75):
                t = Lt * tf
                if cuisse:
                    pts.append((body.thigh.pt(t, a, 0.014 * R), body.thigh.nrm(t, a)))
        B_pts_shin = []
        for a in (60, 120, 240, 300):
            for tf in (0.2, 0.88):
                t = Ls * tf
                B_pts_shin.append((body.shin.pt(t, a, 0.013 * R), body.shin.nrm(t, a)))
        if pts:
            obs.append(B.rivets("CuisseRivets", pts, rivet_mat, "ThighL", r=0.005 * U))
        obs.append(B.rivets("GreaveRivets", B_pts_shin, rivet_mat, "ShinL", r=0.005 * U))
    return obs


def sabaton(B, body, mat, pointed=1.0, name="Sabaton", lames=True):
    U = body.U; RF = U * (0.55 + 0.45 * body.B)
    ank = body.j["FootL"]
    st = [(0.088, 0.028, 0.045), (0.060, 0.042, 0.090), (0.012, 0.048, 0.112), (-0.050, 0.051, 0.090), (-0.110, 0.053, 0.064),
          (-0.165, 0.047, 0.046), (-0.205 - 0.02 * (pointed - 1), 0.026, 0.028)]
    pts = []; radii = []
    for k, (y, wd, h) in enumerate(st):
        if lames and 2 <= k <= 5:
            # 疊片：每段前緣略縮，後緣略張
            pts.append(V(ank.x + 0.004 * U * (k - 2), ank.y + (y + 0.018) * RF, h * RF * 0.5 * 1.04))
            radii.append((wd * RF * 1.05, h * RF * 0.5 * 1.04))
        pts.append(V(ank.x + 0.004 * U * max(k - 2, 0), ank.y + y * RF, h * RF * 0.5))
        radii.append((wd * RF, h * RF * 0.5))
    return [B.tube(name, pts, radii, 14, mat, "FootL", flat=X, exp=2.2, sharp=40)]


# ---------------------------------------------------------------- 布料
def _tri(x):
    x = x % 1.0
    return 1 - abs(2 * x - 1)


def rag_profile(nu, rnd, deep=0.2):
    """破損下緣的輪廓（0=完整長度，愈大缺愈多）：兩組三角波＋抖動＋少數深裂口。"""
    f1 = rnd.uniform(2.2, 3.4); f2 = rnd.uniform(5.5, 8.5)
    p1 = rnd.random(); p2 = rnd.random()
    cut = []
    for i in range(nu + 1):
        u = i / nu
        c = 0.55 * _tri(u * f1 + p1) + 0.35 * _tri(u * f2 + p2) + rnd.uniform(-0.12, 0.12)
        if rnd.random() < deep:
            c += rnd.uniform(0.5, 1.3)
        cut.append(clamp(c, 0, 1.8))
    return cut


def cloth_panel(B, name, top, nrm, length, mat, w, nu=20, nv=14, flare=0.12, rag=0.18, fold_amp=0.02, fold_n=3.0,
                holes=0.05, seed=1, deep=0.2, texel=1.0, sag=0.0, spread=0.0, side=None):
    """由上緣曲線垂下的布片。top(u)->上緣點、nrm(u)->朝外法線。下緣不規則破損（rag：長度變化比例、holes：破洞機率）。
    spread：下襬比上緣多展開的寬度（沿 side 方向，預設 X）。"""
    rnd = random.Random(seed)
    cut = rag_profile(nu, rnd, deep)
    jit = [rnd.uniform(-0.3, 0.3) / nu for _ in range(nu + 1)]
    ph = rnd.uniform(0, 6.28)
    holeset = set()
    for i in range(nu):
        if rnd.random() < holes * 3:
            holeset.add((i, nv - 1 - rnd.randrange(0, 3)))
    for _ in range(int(nu * nv * holes * 0.25)):
        holeset.add((rnd.randrange(nu), rnd.randrange(nv // 3, nv)))
    sd = side or X

    def fn(u, v):
        i = min(int(round(u * nu)), nu)
        L = length * (1 - rag * cut[i])
        n = nrm(u)
        uu = u + jit[i] * smooth(v * 1.5)
        p = top(u) - Z * (L * v)
        wave = math.sin(2 * math.pi * fold_n * uu + ph) + 0.45 * math.sin(2 * math.pi * fold_n * 2.3 * uu + ph * 2)
        p = p + n * (flare * L * v ** 1.3 + fold_amp * wave * smooth(v * 3.0) * (0.5 + 0.5 * v) + sag * math.sin(math.pi * min(v * 1.2, 1)))
        p = p + sd * ((uu - 0.5) * spread * v ** 0.8)
        return p
    inside = [top(0.5) - nrm(0.5) * 0.5 - Z * length * k / 4 for k in range(5)]
    return B.grid(name, nu, nv, fn, mat, w, inside, holes=lambda i, jv: (i, jv) in holeset, texel=texel, sharp=50)


def mantle(B, body, mat, t0=0.74, t1=1.10, off=0.03, rag=0.03, seed=5, w=None, name="Mantle", drop=0.0, nu=40, nv=8,
           front_drop=0.0, asym=0.0, collar=0.018, folds=9, fold_amp=0.008, back_drop=0.0):
    """披在肩頸的布領：繞軀幹一圈，下緣不規則破損、有皺摺與捲起的領口。drop：肩部外側下垂量；asym：左低右高的斜度。"""
    rnd = random.Random(seed)
    cut = rag_profile(nu, rnd, 0.12)
    R = body.R; U = body.U
    ph = rnd.uniform(0, 6.28)

    def ta(u):
        k = int(round(u * nu)) % nu
        a = angn(u * 360)
        side = math.exp(-((abs(a) - 90) / 45) ** 2)
        fr = math.exp(-(a / 55) ** 2)
        bk = math.exp(-((abs(a) - 180) / 60) ** 2)
        return body.tz(t0) + rag * U * cut[k] - drop * U * side - front_drop * U * fr - back_drop * U * bk - asym * U * math.sin(math.radians(a)) * fr

    def offn(u, v, ang, t):
        a = angn(ang)
        side = math.exp(-((abs(a) - 90) / 42) ** 2)
        k = int(round(u * nu)) % nu
        fold = fold_amp * 1.8 * R * (math.sin(math.radians(ang) * folds + ph + 2.0 * v) + 0.5 * math.sin(math.radians(ang) * folds * 2.3 + ph * 3)) * (1 - v) ** 0.8
        roll = collar * R * math.exp(-((v - 0.90) / 0.09) ** 2)
        return (off + 0.035 * side * (1 - v) ** 0.7) * R + 0.006 * R * (cut[k] - 0.5) * (1 - v) + fold + roll + 0.022 * R * (1 - v) ** 2.5
    return B.shell(name, body.torso, ta, body.tz(t1), 0, 360, nu, nv, mat, w or {"Spine2": 0.8, "Neck": 0.2}, off=offn, sharp=50, rim=0.006 * R)


def strap_ring(B, surf, t, mat, w, width=0.02, off=0.014, name="Strap", rivet_mat=None, rivet_ang=90, segs=12):
    ob = [B.shell(name, surf, t - width / 2, t + width / 2, 0, 360, segs, 1, mat, w, off=off, rim=0.003)]
    if rivet_mat:
        pts = [(surf.pt(t, rivet_ang + d, off + 0.003), surf.nrm(t, rivet_ang + d)) for d in (-7, 7)]
        ob.append(B.rivets(name + "Buckle", pts, rivet_mat, w, r=width * 0.42))
    return ob


# ---------------------------------------------------------------- 武器
def sword(B, c, blade, edge, mat_blade, mat_guard, mat_grip, U=1.0, blade_len=0.92, width=0.026, grip=0.18, guard=0.115,
          w="Weapon", thick=0.0048, st=None, grip_r=0.0135, guard_r=1.0, pommel=1.0):
    """長劍。c：握點中心、blade：刃方向、edge：刃口方向。"""
    blade = blade.normalized(); edge = (edge - blade * edge.dot(blade)).normalized()
    g0 = c + blade * (grip * 0.5 * U)
    L = blade_len * U
    st = st or [(0.0, 1.0, 1.0), (0.04, 1.0, 1.0), (0.55, 0.86, 0.9), (0.85, 0.68, 0.75), (0.95, 0.42, 0.6), (1.0, 0.03, 0.2)]
    pts = [g0 + blade * (0.012 * U + L * t) for t, _, _ in st]
    radii = [(width * U * a, thick * U * b) for _, a, b in st]
    obs = [B.tube("Blade", pts, radii, 4, mat_blade, w, exp=2.0, flat=edge, sharp=10)]
    gp = [g0 - edge * guard * U, g0 - edge * guard * 0.9 * U, g0 - edge * 0.02 * U, g0 + edge * 0.02 * U, g0 + edge * guard * 0.9 * U, g0 + edge * guard * U]
    gr = [(0.013 * U * guard_r, 0.008 * U * guard_r), (0.015 * U * guard_r, 0.011 * U * guard_r), (0.011 * U * guard_r, 0.013 * U * guard_r), (0.011 * U * guard_r, 0.013 * U * guard_r), (0.015 * U * guard_r, 0.011 * U * guard_r), (0.013 * U * guard_r, 0.008 * U * guard_r)]
    obs.append(B.tube("Guard", [p + blade * 0.006 * U for p in gp], gr, 8, mat_guard, w, exp=3.5, flat=blade))
    n = 7
    hp = [c + blade * (grip * U * (0.5 - k / (n - 1))) for k in range(n)]
    hr = [(grip_r + 0.002 * math.sin(math.pi * k / (n - 1)) + (0.0012 if k % 2 else 0)) * U for k in range(n)]
    obs.append(B.tube("Grip", hp, hr, 8, mat_grip, w, flat=edge))
    pc = c - blade * (grip * 0.5 + 0.022 * pommel) * U
    side = blade.cross(edge)
    obs.append(B.ellipsoid("Pommel", pc, (edge, side, blade), (0.027 * U * pommel, 0.016 * U * pommel, 0.027 * U * pommel), 10, 6, mat_guard, w))
    return obs


def roots(B, body, surf, mat, w, t0, t1, turns=1.5, a_start=0, r=0.008, off=0.012, n=14, seed=1, name="Root", wobble=0.25,
          branch=True):
    """纏繞在肢體表面的樹根／藤蔓。"""
    rnd = random.Random(seed)
    ph = rnd.uniform(0, 6.28)
    pts = []; radii = []
    for k in range(n + 1):
        s = k / n
        t = lerp(t0, t1, s) + 0.01 * math.sin(s * 9 + ph)
        ang = a_start + turns * 360 * s + wobble * 60 * math.sin(s * 7 + ph)
        o = off + r * 0.6 + 0.004 * math.sin(s * 13 + ph)
        pts.append(surf.pt(t, ang, o))
        radii.append(r * (1.0 - 0.6 * s) * (1 + 0.2 * math.sin(s * 17 + ph)))
    obs = [B.tube(name, pts, radii, 5, mat, w, texel=0.9)]
    if branch:
        k = n // 2
        p = pts[k]
        nrm = surf.nrm(lerp(t0, t1, 0.5), a_start + turns * 180)
        d = (pts[k + 1] - pts[k]).normalized()
        side = d.cross(nrm).normalized()
        bp = [p, p + side * 0.03 + d * 0.02 - nrm * 0.003, p + side * 0.06 + d * 0.05 - nrm * 0.006, p + side * 0.075 + d * 0.09 - nrm * 0.01]
        obs.append(B.tube(name + "Br", bp, [r * 0.6, r * 0.5, r * 0.35, r * 0.15], 4, mat, w, texel=0.9))
    return obs


def chain_links(B, pts, mat, w, link_r=0.016, wire=0.0045, name="Chain"):
    """沿點列的鐵鏈（每節一個低面數環，相鄰兩節轉 90 度）。"""
    obs = []
    for k in range(len(pts) - 1):
        a = pts[k]; b = pts[k + 1]
        d = (b - a)
        if d.length < 1e-5:
            continue
        dn = d.normalized()
        e1 = dn.orthogonal().normalized()
        if k % 2:
            e1 = dn.cross(e1).normalized()
        e2 = dn
        c = (a + b) / 2
        hl = d.length * 0.5 + wire * 1.5

        def fn(u, v, c=c, e1=e1, e2=e2, hl=hl):
            A = 2 * math.pi * u; Bv = 2 * math.pi * v
            n3 = e1.cross(e2)
            ring = e2 * (math.cos(A) * hl) + e1 * (math.sin(A) * link_r)
            rn = (e2 * math.cos(A) * link_r + e1 * math.sin(A) * hl).normalized()
            return c + ring + (rn * math.cos(Bv) + n3 * math.sin(Bv)) * wire
        ww = w(c) if callable(w) else w
        obs.append(B.grid(f"{name}{k}", 8, 4, fn, mat, ww, [c + e2 * hl * 0.6, c - e2 * hl * 0.6, c + e1 * link_r * 0.7, c - e1 * link_r * 0.7],
                          closed_u=True, closed_v=True, stack_uv=True, sharp=60))
    return obs
