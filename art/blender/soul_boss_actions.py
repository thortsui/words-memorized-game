"""魂系 Boss 共用的 9 個手刻動作：Idle、Enter、Telegraph、Attack、Attack2、Hit、Stagger、PhaseShift、Die。
軀幹與腳步的關鍵姿勢共用，武器握法由各 Boss 提供 weapon(key, Pd)。全部原地播放。
位置以主角比例（身高 1.8）為單位，套用時自動乘上 U。

約定：
  Telegraph：f1 由 Idle 進入，f15 到達蓄力姿勢，f15~f45 是可循環保持的顫動（f15 與 f45 姿勢相同）
  Attack／Attack2：第一格就是 Telegraph 的蓄力姿勢，結束回到 Idle
"""
import math
from mathutils import Vector
from soul_humanoid_anim import W, HW


def build(rig, weapon, primary="sweep", slow=1.0, only=None, wide=1.0):
    P = rig.P
    FL, FLr, FR, FRr = (0.10 * wide, -0.22, 0), (10, 0, 0), (-0.12 * wide, 0.24, 0), (-45, 0, 0)

    def T(hips=(0, 0, 0), hr=(0, 0, 0), sp=(0, 0, 0), ch=(0, 0, 0), look=0.0, nod=0.0, **kw):
        yaw = max(-75, min(75, look - (hr[2] + sp[2] + ch[2])))
        pit = nod - 0.7 * (hr[0] + sp[0] + ch[0])
        rol = -0.6 * (hr[1] + sp[1] + ch[1])
        d = dict(fL=FL, fLr=FLr, fR=FR, fRr=FRr)
        d.update(kw)
        return P(hips=hips, hips_r=hr, spine=sp, chest=ch, neck=(pit * 0.4, rol * 0.4, yaw * 0.4),
                 head=(pit * 0.6, rol * 0.6, yaw * 0.6), **d)

    def K(key, *a, **kw):
        p = T(*a, **kw)
        weapon(key, p)
        return p

    def A(name, keys, loop=False):
        if only and name not in only:
            return
        keys = [(1 + round((f - 1) * slow), p) for f, p in keys]
        rig.action(name, keys, loop)

    def idle(dz=0.0, lean=0.0, key="idle"):
        return K(key, hips=(0, 0, -0.05 + dz), hr=(4 + lean, 0, -18), sp=(3 + lean * 0.5, 0, -5), ch=(3 + lean * 0.5, 0, -4))
    I = idle()
    rig.base = I

    # 兩套攻擊的軀幹姿勢
    def sweep(tag):
        wind = K("s_wind", hips=(-0.05, 0.08, -0.12), hr=(4, 0, -44), sp=(2, 0, -12), ch=(0, 0, -12))
        wind2 = K("s_wind2", hips=(-0.06, 0.10, -0.14), hr=(4, 0, -49), sp=(2, 0, -13), ch=(0, 0, -13))
        hit = K("s_hit", hips=(0.03, -0.14, -0.15), hr=(8, 0, 10), sp=(4, 0, 8), ch=(2, 0, 10),
                fL=(0.10 * wide, -0.34, 0), fR=(-0.12 * wide, 0.24, 0.03), fRr=(-34, 16, 0))
        fol = K("s_follow", hips=(0.06, -0.16, -0.16), hr=(8, 0, 34), sp=(4, 0, 12), ch=(2, 0, 14),
                fL=(0.10 * wide, -0.34, 0), fR=(-0.12 * wide, 0.23, 0.04), fRr=(-24, 24, 0))
        setl = K("s_settle", hips=(0.05, -0.14, -0.15), hr=(7, 0, 27), sp=(3, 0, 10), ch=(2, 0, 11),
                 fL=(0.10 * wide, -0.34, 0), fR=(-0.12 * wide, 0.23, 0.02), fRr=(-28, 14, 0))
        return wind, wind2, hit, fol, setl

    def over(tag):
        up = K("o_up", hips=(0, 0.07, -0.03), hr=(-8, 0, -6), sp=(-6, 0, -2), ch=(-8, 0, -2), nod=6)
        up2 = K("o_up2", hips=(0, 0.10, -0.02), hr=(-11, 0, -6), sp=(-7, 0, -2), ch=(-9, 0, -2), nod=6,
                fL=(0.10 * wide, -0.26, 0.07), fLr=(10, -8, 0))
        hit = K("o_hit", hips=(0, -0.28, -0.28), hr=(28, 0, 4), sp=(13, 0, 2), ch=(11, 0, 2), nod=8,
                fL=(0.10 * wide, -0.56, 0), fR=(-0.12 * wide, 0.24, 0.03), fRr=(-34, 22, 0))
        low = K("o_low", hips=(0, -0.29, -0.32), hr=(32, 0, 4), sp=(14, 0, 2), ch=(12, 0, 2), nod=10,
                fL=(0.10 * wide, -0.56, 0), fR=(-0.12 * wide, 0.24, 0.03), fRr=(-34, 22, 0))
        rec = K("o_rec", hips=(0, -0.18, -0.20), hr=(16, 0, -8), sp=(8, 0, -3), ch=(6, 0, -2), fL=(0.10 * wide, -0.56, 0))
        return up, up2, hit, low, rec

    if primary == "sweep":
        tele, tele2, a_hit, a_fol, a_set = sweep("atk")
        b_up, b_up2, b_hit, b_low, b_rec = over("atk2")
        atk_keys = [(1, tele), (4, tele2), (8, a_hit), (11, a_fol), (19, a_set), (48, I)]
        atk2_keys = [(1, tele), (13, b_up), (20, b_up2), (24, b_hit), (27, b_low), (40, b_rec), (62, I)]
        tele_hold = tele2
    else:
        tele, tele2, a_hit, a_low, a_rec = over("atk")
        b_wind, b_wind2, b_hit, b_fol, b_set = sweep("atk2")
        atk_keys = [(1, tele), (6, tele2), (10, a_hit), (13, a_low), (26, a_rec), (52, I)]
        atk2_keys = [(1, tele), (12, b_wind), (17, b_wind2), (21, b_hit), (24, b_fol), (32, b_set), (62, I)]
        tele_hold = tele2

    # ---------------------------------------------------------------- Idle
    A("Idle", [(1, I), (30, idle(-0.010, 0.8)), (56, idle(-0.022, 2.2)), (84, idle(-0.008, 0.6)), (101, I)], loop=True)

    # ---------------------------------------------------------------- Enter：垂首佇立 → 抬頭 → 提起武器
    e0 = K("enter0", hips=(0, 0.04, -0.13), hr=(20, 0, -6), sp=(12, 0, 0), ch=(14, 0, 0), nod=52,
           fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e0b = K("enter0", hips=(0, 0.04, -0.14), hr=(21, 0, -6), sp=(13, 0, 0), ch=(15, 0, 0), nod=54,
            fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e1 = K("enter0", hips=(0, 0.03, -0.10), hr=(14, 0, -8), sp=(8, 0, -2), ch=(8, 0, -2), nod=-4, look=0,
           fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e2 = K("enter1", hips=(0, 0.02, -0.02), hr=(0, 0, -10), sp=(-2, 0, -3), ch=(-4, 0, -3), nod=-6,
           fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e3 = K("enter2", hips=(0, -0.04, -0.09), hr=(8, 0, -16), sp=(4, 0, -5), ch=(4, 0, -4), fL=(0.10 * wide, -0.30, 0.0))
    e3b = K("enter2", hips=(0, -0.05, -0.12), hr=(10, 0, -16), sp=(5, 0, -5), ch=(5, 0, -4), fL=(0.10 * wide, -0.30, 0.0))
    A("Enter", [(1, e0), (22, e0b), (40, e0), (58, e1), (76, e2), (88, e3), (92, e3b), (112, I)])

    # ---------------------------------------------------------------- Telegraph
    A("Telegraph", [(1, I), (15, tele), (23, tele_hold), (30, tele), (38, tele_hold), (45, tele)])
    A("Attack", atk_keys)
    A("Attack2", atk2_keys)

    # ---------------------------------------------------------------- Hit
    h1 = K("hit1", hips=(-0.03, 0.14, -0.09), hr=(-12, -3, -30), sp=(-6, 0, -8), ch=(-8, 0, -8), nod=16,
           fR=(-0.13 * wide, 0.34, 0.04), fRr=(-45, 8, 0))
    h2 = K("hit2", hips=(-0.03, 0.16, -0.16), hr=(10, -2, -24), sp=(6, 0, -6), ch=(6, 0, -5), nod=6, fR=(-0.13 * wide, 0.40, 0))
    A("Hit", [(1, I), (4, h1), (11, h2), (20, idle(-0.03, 2.0)), (28, I)])

    # ---------------------------------------------------------------- Stagger：被彈反，武器被震開、踉蹌後退、單膝跪地再起身
    s1 = K("stag1", hips=(-0.02, 0.16, -0.04), hr=(-18, -4, -26), sp=(-9, 0, -8), ch=(-12, 0, -8), nod=22,
           fL=(0.10 * wide, -0.16, 0.05), fLr=(10, -14, 0), fR=(-0.13 * wide, 0.30, 0))
    s2 = K("stag2", hips=(-0.04, 0.30, -0.12), hr=(-8, -5, -34), sp=(-4, 0, -8), ch=(-6, 0, -6), nod=10,
           fL=(0.10 * wide, -0.12, 0), fR=(-0.15 * wide, 0.56, 0.03), fRr=(-45, 8, 0))
    s3 = K("stag3", hips=(-0.03, 0.26, -0.44), hr=(18, -3, -20), sp=(12, 0, -4), ch=(12, 0, -2), nod=24,
           fL=(0.10 * wide, -0.14, 0), fR=(-0.14 * wide, 0.62, -0.03), fRr=(-30, 68, 0))
    s3b = K("stag3", hips=(-0.03, 0.26, -0.46), hr=(21, -3, -20), sp=(13, 0, -4), ch=(14, 0, -2), nod=30,
            fL=(0.10 * wide, -0.14, 0), fR=(-0.14 * wide, 0.62, -0.03), fRr=(-30, 68, 0))
    s4 = K("stag4", hips=(-0.02, 0.14, -0.22), hr=(16, 0, -18), sp=(8, 0, -5), ch=(8, 0, -4), nod=6,
           fL=(0.10 * wide, -0.14, 0), fR=(-0.13 * wide, 0.40, 0.0))
    A("Stagger", [(1, I), (4, s1), (13, s2), (24, s3), (38, s3b), (52, s3), (66, s4), (82, I)])

    # ---------------------------------------------------------------- PhaseShift：蜷身蓄力 → 仰天怒吼
    g1 = K("roar_gather", hips=(0, 0.02, -0.24), hr=(26, 0, -10), sp=(16, 0, -2), ch=(16, 0, -2), nod=36)
    r1 = K("roar", hips=(0, 0.05, -0.02), hr=(-14, 0, -4), sp=(-10, 0, 0), ch=(-14, 0, 0), nod=-22 - 0.7 * 38)
    r2 = K("roar2", hips=(0.01, 0.06, -0.03), hr=(-16, 2, -2), sp=(-11, 0, 2), ch=(-15, 0, 2), nod=-26 - 0.7 * 42, look=6)
    r3 = K("roar2", hips=(-0.01, 0.06, -0.03), hr=(-16, -2, -6), sp=(-11, 0, -2), ch=(-15, 0, -2), nod=-26 - 0.7 * 42, look=-6)
    r4 = K("roar_end", hips=(0, -0.04, -0.16), hr=(14, 0, -14), sp=(8, 0, -4), ch=(8, 0, -4), nod=4)
    A("PhaseShift", [(1, I), (16, g1), (22, g1), (27, r1), (33, r2), (39, r3), (45, r2), (51, r3), (58, r1), (68, r4), (88, I)])

    # ---------------------------------------------------------------- Die：後仰、跪倒、向前倒下
    d1 = K("die1", hips=(-0.02, 0.12, -0.10), hr=(-16, 0, -18), sp=(-8, 0, -4), ch=(-10, 0, -4), nod=22, fR=(-0.13 * wide, 0.32, 0))
    kn = K("kneel", hips=(0, 0.02, -0.47), hr=(8, 0, -4), sp=(12, 0, 0), ch=(14, 0, 0), nod=34,
           fL=(0.04 * wide, 0.36, -0.03), fLr=(4, 72, 0), fR=(-0.04 * wide, 0.42, -0.03), fRr=(-8, 72, 0), kL=(0.25, 0, 0), kR=(-0.25, 0, 0))
    kn2 = K("kneel2", hips=(0.01, 0.0, -0.49), hr=(15, 2, -2), sp=(16, 0, 0), ch=(18, 0, 0), nod=46,
            fL=(0.04 * wide, 0.36, -0.03), fLr=(4, 72, 0), fR=(-0.04 * wide, 0.42, -0.03), fRr=(-8, 72, 0), kL=(0.25, 0, 0), kR=(-0.25, 0, 0))
    lie = dict(fL=(0.08 * wide, 0.46, 0.02), fLr=(10, 62, 0), fR=(-0.08 * wide, 0.52, 0.02), fRr=(-14, 62, 0), kL=(0.3, 1.5, 0), kR=(-0.3, 1.5, 0))
    fall = K("fall", hips=(0.02, -0.34, -0.80 + rig.lie_dz), hr=(84, 0, 6), sp=(2, 0, 0), ch=(0, 0, 0), look=40, nod=-6, **lie)
    bnc = K("fall", hips=(0.02, -0.34, -0.76 + rig.lie_dz), hr=(80, 0, 6), sp=(3, 0, 0), ch=(1, 0, 0), look=30, nod=-10, **lie)
    A("Die", [(1, I), (6, d1), (22, kn), (40, kn2), (52, fall), (56, bnc), (61, fall), (80, fall)])
