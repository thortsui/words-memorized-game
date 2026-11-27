"""v3 噬語魔王的手刻動作（由 v2b_dev_actions.py 複製；骨架比例改變後重新調整）（由 soul_boss_actions.py 複製改寫；PhaseShift／PhaseShift2 依 design.md §2.5 分鏡）。
既有：Idle、Enter、Telegraph、Attack、Attack2、Hit、Stagger、PhaseShift、Die
新增：Stalk、StrafeL、StrafeR、IdleAggro（循環）；Combo3、Delayed、Dash、Roar
軀幹與腳步的關鍵姿勢共用，武器握法由各 Boss 提供 weapon(key, Pd)。全部原地播放，片段從第 0 格開始。
位置以主角比例（身高 1.8）為單位，套用時自動乘上 U。
重量感原則：預備拉長（壓縮、蓄力、停頓）→ 爆發很短（in／in3 加速抵達）→ 跟隨過頭（out3 減速）→ 回勢慢（io）。

約定：
  Telegraph：f0 由 Idle 進入，f14 到達蓄力姿勢，f14~f44 是可循環保持的顫動（f14 與 f44 姿勢相同）
  Attack／Attack2：第一格就是 Telegraph 的蓄力姿勢，結束回到 Idle
  其他新片段起訖都是 Idle（IdleAggro 起訖是自己的二階段待機姿勢）
"""
import math
from mathutils import Vector
from soul_humanoid_anim import W, HW, gait


def build(rig, weapon, primary="sweep", slow=1.0, only=None, wide=1.0, dash="thrust"):
    P = rig.P
    FL, FLr, FR, FRr = (0.10 * wide, -0.22, 0), (10, 0, 0), (-0.12 * wide, 0.24, 0), (-45, 0, 0)

    def T(hips=(0, 0, 0), hr=(0, 0, 0), sp=(0, 0, 0), ch=(0, 0, 0), look=0.0, nod=0.0, air=False, **kw):
        yaw = max(-75, min(75, look - (hr[2] + sp[2] + ch[2])))
        pit = nod - 0.7 * (hr[0] + sp[0] + ch[0])
        rol = -0.6 * (hr[1] + sp[1] + ch[1])
        d = dict(fL=FL, fLr=FLr, fR=FR, fRr=FRr)
        d.update(kw)
        if not air:                                            # v4：躍起／懸浮（air=True）的姿勢腳目標另外抬高
            hips = (hips[0], hips[1], min(hips[2], -0.035))  # v3：腿較長，骨盆不可高過站姿，否則腳會被拉離地面
        return P(hips=hips, hips_r=hr, spine=sp, chest=ch, neck=(pit * 0.4, rol * 0.4, yaw * 0.4),
                 head=(pit * 0.6, rol * 0.6, yaw * 0.6), **d)

    def K(key, *a, off=(0, 0, 0), **kw):
        p = T(*a, **kw)
        if key in ("idle", "ps_chest", "enter0", "enter1"):      # v3：拄地的劍尖不隨身體下沉而插進地面
            off = (off[0], off[1], max(off[2], 0.0))
        rig.reach_off = off
        weapon(key, p)
        rig.reach_off = (0.0, 0.0, 0.0)
        return p

    def A(name, keys, loop=False, hits=None, lag=None, sl=None):
        if only and name not in only:
            return
        k_ = slow if sl is None else sl
        keys = [(round(k[0] * k_),) + tuple(k[1:]) for k in keys]
        hits = [((round(h[0] * k_), h[1]) if isinstance(h, tuple) else round(h * k_)) for h in hits] if hits else None
        rig.action(name, keys, loop, hits=hits, lag=lag)

    def idle(dz=0.0, lean=0.0, key="idle", sx=0.0, yaw=0.0, roll=0.0, off=None):
        return K(key, hips=(sx, 0, -0.05 + dz), hr=(4 + lean, roll, -18 + yaw), sp=(3 + lean * 0.5, -roll * 0.5, -5), ch=(3 + lean * 0.5, 0, -4),
                 off=off or (sx * 0.7, 0, dz * 0.7))
    I = idle()
    rig.base = I

    # 兩套攻擊的軀幹姿勢
    def sweep():
        wind = K("s_wind", hips=(-0.05, 0.08, -0.12), hr=(4, 0, -44), sp=(2, 0, -12), ch=(0, 0, -12))
        wind2 = K("s_wind2", hips=(-0.06, 0.11, -0.16), hr=(5, 0, -51), sp=(3, 0, -14), ch=(1, 0, -14))
        hit = K("s_hit", hips=(0.03, -0.14, -0.15), hr=(8, 0, 10), sp=(4, 0, 8), ch=(2, 0, 10),
                fL=(0.10 * wide, -0.34, 0), fR=(-0.12 * wide, 0.24, 0.03), fRr=(-34, 16, 0))
        fol = K("s_follow", hips=(0.07, -0.17, -0.18), hr=(9, 0, 38), sp=(4, 0, 14), ch=(2, 0, 16),
                fL=(0.10 * wide, -0.34, 0), fR=(-0.12 * wide, 0.23, 0.05), fRr=(-24, 26, 0))
        setl = K("s_settle", hips=(0.05, -0.14, -0.16), hr=(7, 0, 27), sp=(3, 0, 10), ch=(2, 0, 11),
                 fL=(0.10 * wide, -0.34, 0), fR=(-0.12 * wide, 0.23, 0.02), fRr=(-28, 14, 0))
        return wind, wind2, hit, fol, setl

    def over():
        up = K("o_up", hips=(0, 0.07, -0.03), hr=(-8, 0, -6), sp=(-6, 0, -2), ch=(-8, 0, -2), nod=6)
        up2 = K("o_up2", hips=(0, 0.11, -0.04), hr=(-12, 0, -6), sp=(-8, 0, -2), ch=(-10, 0, -2), nod=6,
                fL=(0.10 * wide, -0.28, 0.08), fLr=(10, -8, 0))
        hit = K("o_hit", hips=(0, -0.28, -0.28), hr=(28, 0, 4), sp=(13, 0, 2), ch=(11, 0, 2), nod=8,
                fL=(0.10 * wide, -0.56, 0), fR=(-0.12 * wide, 0.24, 0.03), fRr=(-34, 22, 0))
        low = K("o_low", hips=(0, -0.30, -0.34), hr=(33, 0, 4), sp=(15, 0, 2), ch=(13, 0, 2), nod=10,
                fL=(0.10 * wide, -0.56, 0), fR=(-0.12 * wide, 0.24, 0.04), fRr=(-34, 24, 0))
        rec = K("o_rec", hips=(0, -0.18, -0.20), hr=(16, 0, -8), sp=(8, 0, -3), ch=(6, 0, -2), fL=(0.10 * wide, -0.56, 0))
        return up, up2, hit, low, rec

    sw_wind, sw_wind2, sw_hit, sw_fol, sw_set = sweep()
    ov_up, ov_up2, ov_hit, ov_low, ov_rec = over()
    # 蓄力時的下壓（壓縮）版本：同一武器姿勢、身體更低更扭
    sw_coil = K("s_wind2", hips=(-0.07, 0.13, -0.20), hr=(7, 0, -54), sp=(4, 0, -15), ch=(2, 0, -15), nod=4)
    ov_coil = K("o_up2", hips=(0, 0.13, -0.10), hr=(-9, 0, -7), sp=(-6, 0, -2), ch=(-8, 0, -2), nod=8,
                fL=(0.10 * wide, -0.22, 0.0), fLr=(10, 0, 0))

    if primary == "sweep":
        tele, tele2 = sw_wind, sw_wind2
        atk_keys = [(0, tele), (6, tele2, "io"), (10, sw_coil, "io"), (14, sw_hit, "in3"), (19, sw_fol, "out3"), (28, sw_set, "io"), (54, I, "io")]
        atk_hit = [14]
        atk2_keys = [(0, tele), (12, ov_up, "io"), (20, ov_up2, "out"), (26, ov_coil, "io"), (30, ov_hit, "in3"), (34, ov_low, "out3"),
                     (46, ov_low, "io"), (54, ov_rec, "io"), (72, I, "io")]
        atk2_hit = [30]
    else:
        tele, tele2 = ov_up, ov_up2
        atk_keys = [(0, tele), (6, tele2, "io"), (11, ov_coil, "io"), (15, ov_hit, "in3"), (19, ov_low, "out3"), (32, ov_low, "io"), (40, ov_rec, "io"), (62, I, "io")]
        atk_hit = [15]
        atk2_keys = [(0, tele), (12, sw_wind, "io"), (18, sw_wind2, "out"), (23, sw_coil, "io"), (27, sw_hit, "in3"), (32, sw_fol, "out3"),
                     (42, sw_set, "io"), (68, I, "io")]
        atk2_hit = [27]

    # ---------------------------------------------------------------- Idle：沉重呼吸、重心左右換腳、武器微晃（循環）
    A("Idle", [(0, I), (26, idle(-0.012, 1.0, sx=0.016, yaw=2.0, roll=1.5)), (52, idle(-0.024, 2.4)),
               (78, idle(-0.010, 0.8, sx=-0.016, yaw=-2.0, roll=-1.5)), (104, I)], loop=True)

    # ---------------------------------------------------------------- IdleAggro：二階段待機——更低、更前傾、呼吸急促、左右焦躁晃動（循環）
    def aggro(dz=0.0, lean=0.0, sx=0.0, yaw=0.0, roll=0.0, look=0.0):
        return K("idle", hips=(sx, -0.06, -0.15 + dz), hr=(12 + lean, roll, -22 + yaw), sp=(7 + lean * 0.5, -roll * 0.5, -6), ch=(6 + lean * 0.5, 0, -5),
                 look=look, nod=-4, fL=(0.11 * wide, -0.30, 0), fR=(-0.13 * wide, 0.30, 0), off=(sx * 0.8, -0.08, -0.10 + dz * 0.8))
    IA = aggro()
    A("IdleAggro", [(0, IA), (8, aggro(-0.02, 2.5, 0.03, 5, 2.5, 8), "io"), (16, aggro(0.0, 0.5, 0.0, 0, 0, 0), "io"),
                    (26, aggro(-0.025, 3.0, -0.035, -6, -3.0, -10), "io"), (34, aggro(-0.005, 1.0), "io"), (42, aggro(-0.02, 2.0, 0.02, 3, 1.5, 4), "io"),
                    (52, IA, "io")], loop=True)

    # ---------------------------------------------------------------- Stalk／StrafeL／StrafeR：持武器壓近、繞行（原地循環）
    def stalk_cycle(N, stride, lift, d, lean=6.0, dz=-0.10, sway=0.035, twist=6.0, swing=0.36):
        keys = []
        for f in range(0, N + 1, 3):
            ph = (f / N) % 1.0
            gl = gait(ph, stride, lift, swing, d, pitch=10)
            gr = gait(ph + 0.5, stride, lift, swing, d, pitch=10)
            b = -0.022 * math.cos(4 * math.pi * (ph - 0.06))
            s2 = math.sin(2 * math.pi * ph)
            sx = sway * math.sin(2 * math.pi * (ph - 0.15))
            k = K("idle", hips=(sx, -0.02, dz + b), hr=(4 + lean, 2.5 * s2, -18 + twist * s2), sp=(3 + lean * 0.5, -2 * s2, -5 - twist * 0.6 * s2),
                  ch=(3 + lean * 0.4, 0, -4 - twist * 0.4 * s2), nod=-2,
                  fL=(FL[0] + gl[0], FL[1] + gl[1], gl[2]), fLr=(10, gl[3], 0), fR=(FR[0] + gr[0], FR[1] + gr[1], gr[2]), fRr=(-45, gr[3], 0),
                  off=(sx * 0.7, -0.03, dz + 0.05 + b * 0.7))
            keys.append((f, k))
        return keys
    A("Stalk", stalk_cycle(48, 0.40, 0.08, (0, -1), lean=9.0, dz=-0.13), loop=True)
    A("StrafeL", stalk_cycle(42, 0.32, 0.07, (1, 0), lean=5.0, sway=0.045, twist=3.0, swing=0.40, dz=-0.12), loop=True)
    A("StrafeR", stalk_cycle(42, 0.34, 0.07, (-1, 0), lean=5.0, sway=0.045, twist=3.0, swing=0.40), loop=True)

    # ---------------------------------------------------------------- Enter：垂首佇立 → 抬頭 → 提起武器
    e0 = K("enter0", hips=(0, 0.04, -0.13), hr=(20, 0, -6), sp=(12, 0, 0), ch=(14, 0, 0), nod=52,
           fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e0b = K("enter0", hips=(0, 0.04, -0.145), hr=(21, 0, -6), sp=(13, 0, 0), ch=(15, 0, 0), nod=54,
            fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e1 = K("enter0", hips=(0, 0.03, -0.10), hr=(14, 0, -8), sp=(8, 0, -2), ch=(8, 0, -2), nod=-4, look=0,
           fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e2 = K("enter1", hips=(0, 0.02, -0.02), hr=(0, 0, -10), sp=(-2, 0, -3), ch=(-4, 0, -3), nod=-6,
           fL=(0.07 * wide, -0.06, 0), fR=(-0.07 * wide, 0.08, 0), fRr=(-20, 0, 0))
    e3 = K("enter2", hips=(0, -0.04, -0.09), hr=(8, 0, -16), sp=(4, 0, -5), ch=(4, 0, -4), fL=(0.10 * wide, -0.30, 0.0))
    e3b = K("enter2", hips=(0, -0.05, -0.13), hr=(10, 0, -16), sp=(5, 0, -5), ch=(5, 0, -4), fL=(0.10 * wide, -0.30, 0.0))
    A("Enter", [(0, e0), (21, e0b, "io"), (39, e0, "io"), (57, e1, "io"), (73, e2, "io"), (85, e3, "out"), (89, e3b, "in"), (112, I, "io")])

    # ---------------------------------------------------------------- Telegraph
    A("Telegraph", [(0, I), (14, tele, "io"), (22, tele2, "io"), (29, tele, "io"), (37, tele2, "io"), (44, tele, "io")], loop=False)
    A("Attack", atk_keys, hits=atk_hit)
    A("Attack2", atk2_keys, hits=atk2_hit)

    # ---------------------------------------------------------------- Combo3：橫掃（快）→ 反手回掃（更快）→ 停頓高舉 → 重劈（慢而重）
    A("Combo3", [(0, I), (9, sw_wind, "io"), (13, sw_coil, "io"), (17, sw_hit, "in3"), (21, sw_fol, "out3"),
                 (24, sw_set, "io"), (28, sw_hit, "in"), (32, sw_wind2, "out3"),
                 (42, ov_up, "io"), (52, ov_up2, "io"), (57, ov_coil, "io"), (61, ov_hit, "in3"), (65, ov_low, "out3"),
                 (78, ov_low, "io"), (88, ov_rec, "io"), (110, I, "io")], hits=[17, 28, 61])

    # ---------------------------------------------------------------- Delayed：舉起後刻意停頓（約 0.8 秒、微微再往上蓄）再爆發重砸
    up_hold = K("o_up2", hips=(0, 0.13, -0.05), hr=(-13, 0, -7), sp=(-9, 0, -2), ch=(-11, 0, -2), nod=4,
                fL=(0.10 * wide, -0.22, 0.0), fLr=(10, 0, 0), off=(0, 0.02, 0.03))
    up_hold2 = K("o_up2", hips=(0, 0.14, -0.06), hr=(-14, 0, -8), sp=(-9, 0, -3), ch=(-12, 0, -3), nod=3,
                 fL=(0.10 * wide, -0.22, 0.0), fLr=(10, 0, 0), off=(0, 0.03, 0.05))
    A("Delayed", [(0, I), (8, ov_coil, "io"), (20, ov_up, "out"), (28, ov_up2, "io"), (40, up_hold, "io"), (50, up_hold2, "io"),
                  (54, ov_hit, "in3"), (58, ov_low, "out3"), (74, ov_low, "io"), (84, ov_rec, "io"), (106, I, "io")], hits=[54])

    # ---------------------------------------------------------------- Dash：短起手突進（壓低→蹬地長踏步突刺／衝撞斬）
    pull = K("t_pull", hips=(-0.02, 0.10, -0.22), hr=(10, 0, -32), sp=(6, 0, -10), ch=(4, 0, -8), nod=-4,
             fL=(0.10 * wide, -0.18, 0), fR=(-0.12 * wide, 0.36, 0), fRr=(-50, 0, 0))
    lunge = K("t_thrust", hips=(0.02, -0.44, -0.34), hr=(16, 0, 8), sp=(8, 0, 4), ch=(6, 0, 4), nod=-6,
              fL=(0.10 * wide, -0.66, 0), fLr=(6, 0, 0), fR=(-0.12 * wide, 0.20, 0.04), fRr=(-40, 30, 0))
    lunge2 = K("t_thrust", hips=(0.02, -0.47, -0.37), hr=(19, 0, 9), sp=(9, 0, 4), ch=(7, 0, 4), nod=-6,
               fL=(0.10 * wide, -0.66, 0), fLr=(6, 0, 0), fR=(-0.12 * wide, 0.22, 0.05), fRr=(-40, 34, 0), off=(0, -0.05, -0.02))
    A("Dash", [(0, I), (6, pull, "io"), (10, lunge, "in3"), (14, lunge2, "out3"), (26, lunge2, "io"), (38, ov_rec if primary == "sweep" else sw_set, "io"),
               (60, I, "io")], hits=[10])

    # ---------------------------------------------------------------- Hit
    h1 = K("hit1", hips=(-0.03, 0.14, -0.09), hr=(-12, -3, -30), sp=(-6, 0, -8), ch=(-8, 0, -8), nod=16,
           fR=(-0.13 * wide, 0.34, 0.04), fRr=(-45, 8, 0))
    h2 = K("hit2", hips=(-0.03, 0.16, -0.16), hr=(10, -2, -24), sp=(6, 0, -6), ch=(6, 0, -5), nod=6, fR=(-0.13 * wide, 0.40, 0))
    A("Hit", [(0, I), (3, h1, "out"), (10, h2, "io"), (19, idle(-0.03, 2.0), "io"), (28, I, "io")])

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
    A("Stagger", [(0, I), (3, s1, "out"), (12, s2, "io"), (22, s3, "in"), (25, s3b, "out"), (38, s3b, "io"), (51, s3, "io"), (65, s4, "io"), (82, I, "io")])

    # ---------------------------------------------------------------- PhaseShift（二階，2.5 s，爆發 hit 1.15 s≈第 35 格）
    # 0.0–0.5 劍拄地、左手按胸 → 0.5–1.1 前傾蓄力（書頁剝離、胸甲裂紅光）→ 1.15 爆發：胸口嘴裂開、挺胸仰首
    # 1.15–2.5 雙手握劍斜指地面（紙翼緩慢開合），結尾＝IdleAggro
    c1 = K("ps_chest", hips=(0, 0.02, -0.06), hr=(6, 0, -10), sp=(4, 0, -3), ch=(4, 0, -3), nod=14)
    c2 = K("ps_chest", hips=(0, 0.04, -0.16), hr=(16, 0, -8), sp=(12, 0, -2), ch=(14, 0, -2), nod=30)
    c3 = K("ps_chest", hips=(0, 0.05, -0.19), hr=(19, 0, -8), sp=(14, 0, -2), ch=(17, 0, -2), nod=34, off=(0, 0, -0.02))
    b1 = K("ps_burst", hips=(0, 0.08, -0.02), hr=(-12, 0, -4), sp=(-10, 0, 0), ch=(-16, 0, 0), nod=-24,
           fL=(0.12 * wide, -0.30, 0), fR=(-0.13 * wide, 0.26, 0))
    b2 = K("ps_burst", hips=(0.01, 0.08, -0.03), hr=(-13, 2, -2), sp=(-11, 0, 2), ch=(-17, 0, 2), nod=-26, look=5,
           fL=(0.12 * wide, -0.30, 0), fR=(-0.13 * wide, 0.26, 0))
    lo2 = K("ps_low2", hips=(0, -0.06, -0.16), hr=(12, 0, -16), sp=(7, 0, -5), ch=(6, 0, -5), nod=-4,
            fL=(0.11 * wide, -0.30, 0), fR=(-0.13 * wide, 0.30, 0))
    A("PhaseShift", [(0, I), (12, c1, "io"), (24, c2, "io"), (31, c3, "io"), (35, b1, "in3"), (41, b2, "out"), (47, b1, "io"),
                     (54, b2, "io"), (63, lo2, "io"), (75, IA, "io")], hits=[35], sl=1.0)

    # ---------------------------------------------------------------- PhaseShift2（三階，2.6 s，爆發 hit 1.25 s≈第 37 格）
    # 0.0–0.6 單膝跪、劍插地、全身痙攣 → 0.6–1.2 墨包住下半身（角斷裂）→ 1.25 仰天張開雙臂
    # 1.25–2.6 懸浮起身、拔劍，結尾＝IdleAggro
    kn = dict(fL=(0.06 * wide, -0.30, 0.0), fLr=(10, 0, 0), fR=(-0.06 * wide, 0.40, -0.03), fRr=(-8, 70, 0), kR=(-0.2, 0, 0))
    k1 = K("ps2_stab", hips=(0, -0.04, -0.46), hr=(18, 0, -6), sp=(14, 0, 0), ch=(14, 0, 0), nod=30, **kn)
    k2 = K("ps2_stab", hips=(0.02, -0.04, -0.47), hr=(22, 3, -2), sp=(16, 4, 3), ch=(18, -3, 4), nod=40, look=12, **kn)
    k3 = K("ps2_stab", hips=(-0.02, -0.04, -0.46), hr=(15, -3, -9), sp=(11, -4, -3), ch=(12, 3, -4), nod=24, look=-12, **kn)
    k4 = K("ps2_stab", hips=(0, -0.04, -0.40), hr=(26, 0, -6), sp=(18, 0, 0), ch=(22, 0, 0), nod=46, **kn)
    sp1 = K("ps2_spread", hips=(0, 0.06, 0.02), hr=(-14, 0, -4), sp=(-12, 0, 0), ch=(-18, 0, 0), nod=-34,
            fL=(0.12 * wide, -0.20, 0), fR=(-0.13 * wide, 0.22, 0))
    sp2 = K("ps2_spread", hips=(0, 0.07, 0.04), hr=(-15, 0, -4), sp=(-13, 0, 0), ch=(-19, 0, 0), nod=-38,
            fL=(0.12 * wide, -0.20, 0), fR=(-0.13 * wide, 0.22, 0), off=(0, 0, 0.02))
    rise = K("o_up", hips=(0, 0.04, 0.04), hr=(-6, 0, -6), sp=(-4, 0, -2), ch=(-6, 0, -2), nod=-4)
    A("PhaseShift2", [(0, I), (8, k1, "io"), (13, k2, "io"), (18, k3, "io"), (23, k2, "io"), (30, k4, "io"), (37, sp1, "in3"), (44, sp2, "out"),
                      (52, sp1, "io"), (62, rise, "io"), (70, lo2, "io"), (78, IA, "io")], hits=[37], sl=1.0)

    # ---------------------------------------------------------------- Roar：威嚇咆哮（登場與轉階段用）——後縮、胸口張開前頂、搖頭怒吼、壓低回到戒備
    ro1 = K("roar_gather", hips=(0, 0.06, -0.18), hr=(18, 0, -12), sp=(12, 0, -2), ch=(12, 0, -2), nod=26)
    ro2 = K("roar", hips=(0, -0.10, -0.12), hr=(-4, 0, -4), sp=(-6, 0, 0), ch=(-10, 0, 0), nod=-14 - 0.7 * 20,
            fL=(0.10 * wide, -0.36, 0), fR=(-0.12 * wide, 0.28, 0))
    ro3 = K("roar2", hips=(0.015, -0.11, -0.13), hr=(-6, 3, -1), sp=(-7, 0, 3), ch=(-11, 0, 3), nod=-16 - 0.7 * 22, look=10,
            fL=(0.10 * wide, -0.36, 0), fR=(-0.12 * wide, 0.28, 0))
    ro4 = K("roar2", hips=(-0.015, -0.11, -0.13), hr=(-6, -3, -7), sp=(-7, 0, -3), ch=(-11, 0, -3), nod=-16 - 0.7 * 22, look=-10,
            fL=(0.10 * wide, -0.36, 0), fR=(-0.12 * wide, 0.28, 0))
    ro5 = K("roar_end", hips=(0, -0.06, -0.20), hr=(16, 0, -16), sp=(9, 0, -4), ch=(8, 0, -4), nod=2)
    A("Roar", [(0, I), (12, ro1, "io"), (16, ro2, "in3"), (22, ro3, "out"), (28, ro4, "io"), (34, ro3, "io"), (40, ro4, "io"), (46, ro2, "io"),
               (56, ro5, "io"), (72, I, "io")])

    # ---------------------------------------------------------------- Die：後仰、跪倒、向前倒下
    d1 = K("die1", hips=(-0.02, 0.12, -0.10), hr=(-16, 0, -18), sp=(-8, 0, -4), ch=(-10, 0, -4), nod=22, fR=(-0.13 * wide, 0.32, 0))
    kn = K("kneel", hips=(0, 0.02, -0.45), hr=(8, 0, -4), sp=(12, 0, 0), ch=(14, 0, 0), nod=34,
           fL=(0.04 * wide, 0.36, -0.03), fLr=(4, 72, 0), fR=(-0.04 * wide, 0.42, -0.03), fRr=(-8, 72, 0), kL=(0.25, 0, 0), kR=(-0.25, 0, 0))
    kn2 = K("kneel2", hips=(0.01, 0.0, -0.47), hr=(15, 2, -2), sp=(16, 0, 0), ch=(18, 0, 0), nod=46,
            fL=(0.04 * wide, 0.36, -0.03), fLr=(4, 72, 0), fR=(-0.04 * wide, 0.42, -0.03), fRr=(-8, 72, 0), kL=(0.25, 0, 0), kR=(-0.25, 0, 0))
    lie = dict(fL=(0.08 * wide, 0.46, 0.02), fLr=(10, 62, 0), fR=(-0.08 * wide, 0.52, 0.02), fRr=(-14, 62, 0), kL=(0.3, 1.5, 0), kR=(-0.3, 1.5, 0))
    fall = K("fall", hips=(0.02, -0.34, -0.80 + rig.lie_dz), hr=(84, 0, 6), sp=(2, 0, 0), ch=(0, 0, 0), look=40, nod=-6, **lie)
    bnc = K("fall", hips=(0.02, -0.34, -0.76 + rig.lie_dz), hr=(80, 0, 6), sp=(3, 0, 0), ch=(1, 0, 0), look=30, nod=-10, **lie)
    A("Die", [(0, I), (5, d1, "out"), (14, d1, "io"), (21, kn, "in"), (39, kn2, "io"), (50, fall, "in3"), (54, bnc, "out"), (59, fall, "in"), (80, fall, "io")])

    # ---------------------------------------------------------------- v4（v1.3.0）：Boss 新招 7 個（見 build_v4）
    build_v4(rig, T, A, I, IA, wide, FL, FLr, FR, FRr)


# ================================================================ v3：武器姿勢（握點目標，單位＝主角比例 ×U）與紙翼骨的程序動作
import numpy as _np
from mathutils import Quaternion as _Q


def weapon_poses(rig, TIP, GL=-0.20):
    """TIP：劍尖距握點（×U）。回傳 {key: fn(Pd)}。"""
    def two(Pd, g, d, edge_, hintR=None, elL=None, gl=None):
        Pd["ikL"] = 1.0; Pd["gripL"] = GL if gl is None else gl
        Pd["elL"] = elL or (0.6, 0.3, -0.7)
        rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))

    def one(Pd, g, d, edge_, left, hintR=None, hintL=None):
        Pd["ikL"] = 0.0
        rig.reach(Pd, "R", g, hintR, Vector(d).normalized(), Vector(edge_))
        rig.reach(Pd, "L", left, hintL)

    # 待機：劍尖插在右腳外側 0.15H（劍幾乎垂直），左手前伸、掌心朝前
    # 劍尖在 (-1.0, -0.40, 0) m（右腳外側約 0.15H），劍柄往外倒（握點更外、更高）
    PD = Vector((0.10, -0.05, -0.99)).normalized()
    U_ = rig.U
    TIPP = Vector((-1.0, -0.40, 0.03)) / U_
    PLANT = tuple(TIPP - PD * TIP)
    # 符紋手：掌心朝前（手背朝後 +Y），手指往前下、略向外
    bd = rig.body
    s_ = 1.0 if bd.hand_v.cross(bd.hand_a).dot(bd.hand_u) > 0 else -1.0
    fa = Vector((0.30, -0.50, -0.81)).normalized()
    ub = Vector((0, 1, 0)); ub = (ub - fa * ub.dot(fa)).normalized()
    PALM = HW(tuple(fa.cross(ub) * s_), tuple(fa))

    def idle_pose(p):
        one(p, PLANT, tuple(PD), (0, -0.99, 0.0), (0.50, -0.58, 1.22), hintR=(-0.8, 0.3, -0.5), hintL=(0.6, 0.4, -0.7))
        p["hL"] = PALM
        return p
    return {
        "idle": idle_pose,
        "o_up": lambda p: two(p, (-0.06, 0.04, 1.92), (0.0, 0.62, 0.78), (0, -0.78, 0.62), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
        "o_up2": lambda p: two(p, (-0.06, 0.08, 1.95), (0.0, 0.75, 0.66), (0, -0.66, 0.75), hintR=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
        "o_hit": lambda p: two(p, (0.0, -0.74, 0.96), (0.02, -0.88, -0.47), (0, 0.47, -0.88), hintR=(-0.8, 0.4, -0.3)),
        "o_low": lambda p: two(p, (0.0, -0.72, 0.90), (0.02, -0.84, -0.54), (0, 0.54, -0.84), hintR=(-0.8, 0.4, -0.3)),
        "o_rec": lambda p: two(p, (-0.10, -0.50, 0.98), (0.1, -0.9, 0.1), (0, -0.5, -0.8)),
        "s_wind": lambda p: two(p, (-0.48, 0.10, 1.30), (-0.57, 0.82, 0.20), (-0.82, -0.57, 0), hintR=(-0.3, 0.9, -0.4)),
        "s_wind2": lambda p: two(p, (-0.50, 0.14, 1.32), (-0.45, 0.88, 0.22), (-0.88, -0.45, 0), hintR=(-0.3, 0.9, -0.4)),
        "s_hit": lambda p: two(p, (-0.02, -0.62, 1.16), (0.37, -0.93, -0.05), (0.93, 0.37, 0), hintR=(-0.8, 0.3, -0.5)),
        "s_follow": lambda p: two(p, (0.28, -0.36, 1.10), (0.91, 0.42, -0.12), (-0.42, 0.91, 0), hintR=(-0.5, -0.2, -0.8)),
        "s_settle": lambda p: two(p, (0.25, -0.38, 1.06), (0.95, 0.28, -0.16), (-0.28, 0.95, 0), hintR=(-0.5, -0.2, -0.8)),
        "enter0": lambda p: one(p, (-0.44, -0.32, TIP * 0.985 + 0.03), (0.02, -0.12, -0.99), (0, -0.99, 0.12), (0.40, -0.10, 0.84)),
        "enter1": lambda p: one(p, (-0.44, -0.32, TIP * 0.985 + 0.07), (0.02, -0.12, -0.99), (0, -0.99, 0.12), (0.45, -0.20, 1.0)),
        "enter2": lambda p: two(p, (-0.16, -0.40, 1.04), (0.2, -0.55, 0.8), (0.1, -0.8, -0.6)),
        "hit1": lambda p: one(p, (-0.50, -0.10, 1.32), (-0.3, 0.4, 0.85), (0, -1, 0), (0.50, -0.20, 1.22)),
        "hit2": lambda p: one(p, (-0.36, -0.26, 1.08), (0.0, 0.3, 0.95), (0, -1, 0), (0.40, -0.22, 0.98)),
        "stag1": lambda p: one(p, (-0.58, 0.05, 1.70), (-0.3, 0.6, 0.75), (0, -1, 0), (0.55, -0.20, 1.32)),
        "stag2": lambda p: one(p, (-0.62, 0.22, 1.28), (-0.5, 0.7, 0.3), (0, -1, 0), (0.48, -0.05, 1.12)),
        "stag3": lambda p: one(p, (-0.46, 0.0, 0.90), (-0.25, -0.75, -0.62), (0, 0.6, -0.75), (0.32, -0.10, 0.42), hintL=(0.8, 0.4, 0.0)),
        "stag4": lambda p: two(p, (-0.16, -0.30, 1.0), (0.2, -0.6, 0.75), (0.1, -0.8, -0.6)),
        "roar_gather": lambda p: two(p, (-0.14, -0.40, 0.90), (0.3, -0.75, 0.55), (0.1, -0.8, -0.6)),
        "roar": lambda p: one(p, (-0.64, -0.08, 1.50), (-0.6, -0.2, 0.75), (0, -1, 0), (0.64, -0.10, 1.32), hintL=(0.3, 0.6, -0.7)),
        "roar2": lambda p: one(p, (-0.66, -0.04, 1.55), (-0.65, -0.15, 0.75), (0, -1, 0), (0.66, -0.06, 1.37), hintL=(0.3, 0.6, -0.7)),
        "roar_end": lambda p: two(p, (-0.14, -0.42, 1.02), (0.25, -0.6, 0.75), (0.1, -0.8, -0.6)),
        "die1": lambda p: one(p, (-0.52, -0.05, 1.17), (-0.2, -0.6, 0.5), (0, -1, 0), (0.44, -0.16, 1.22)),
        "kneel": lambda p: one(p, (-0.46, -0.30, 0.78), (0.15, -0.95, -0.27), (1, 0, 0), (0.32, -0.14, 0.46), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
        "kneel2": lambda p: one(p, (-0.48, -0.34, 0.72), (0.15, -0.96, -0.22), (1, 0, 0), (0.32, -0.18, 0.38), hintR=(-0.8, 0.5, -0.2), hintL=(0.8, 0.5, -0.2)),
        "t_pull": lambda p: two(p, (-0.34, 0.06, 1.04), (0.10, -1.0, 0.06), (0, 0, -1), hintR=(-0.7, 0.5, -0.5)),
        "t_thrust": lambda p: two(p, (-0.12, -0.80, 1.16), (0.06, -1.0, 0.0), (0, 0, -1), hintR=(-0.8, 0.3, -0.5)),
        "fall": lambda p: one(p, (-0.60, -0.90, 0.20), (-0.45, -0.89, 0.06), (1, 0, 0), (0.40, -0.86, 0.18), hintR=(-0.9, 0.2, 0.3), hintL=(0.9, 0.2, 0.3)),
        "ps_chest": lambda p: one(p, PLANT, tuple(PD), (0, -0.99, 0.0), (0.10, -0.40, 1.44), hintR=(-0.8, 0.3, -0.5), hintL=(0.7, -0.2, -0.6)),
        "ps_burst": lambda p: one(p, (-0.66, -0.10, 1.44), (-0.55, -0.25, 0.80), (0, -1, 0.3), (0.70, -0.14, 1.47), hintL=(0.3, 0.6, -0.7)),
        "ps_low2": lambda p: two(p, (-0.18, -0.42, 1.16), (0.30, -0.55, -0.78), (0, 0.82, -0.57), hintR=(-0.8, 0.2, -0.5)),
        "ps2_stab": lambda p: two(p, (-0.06, -0.56, TIP * 0.99 - 0.04), (0.0, -0.10, -0.99), (0, -0.99, 0.10), hintR=(-0.8, 0.3, -0.4), gl=0.14),
        "ps2_spread": lambda p: one(p, (-0.70, 0.02, 1.64), (-0.45, 0.10, 0.88), (0, -1, 0.1), (0.72, 0.0, 1.68), hintL=(0.3, 0.6, -0.6)),
    }


def _write(act, bn, qs):
    path = f'pose.bones["{bn}"].rotation_quaternion'
    arr = _np.array([[q.w, q.x, q.y, q.z] for q in qs])
    for k in range(1, len(arr)):
        if _np.dot(arr[k], arr[k - 1]) < 0:
            arr[k] *= -1
    for c in range(4):
        fc = act.fcurves.find(path, index=c)
        if fc is None:
            fc = act.fcurves.new(path, index=c, action_group=bn)
            fc.keyframe_points.add(len(arr))
        n = min(len(fc.keyframe_points), len(arr))
        co = _np.empty(n * 2)
        co[0::2] = _np.arange(n, dtype=float) + act.frame_range[0]
        co[1::2] = arr[:n, c]
        fc.keyframe_points.foreach_set("co", co)
        fc.update()


def wing_bones(arm, rig):
    """紙翼：緩慢開合（循環片段整數週期）；PhaseShift 爆發時從收攏彈開。"""
    import bpy
    ad = arm.animation_data
    if not ad:
        return
    for tr in ad.nla_tracks:
        act = bpy.data.actions[tr.name]
        meta = rig.meta.get(tr.name, {})
        loop = meta.get("loop", False)
        f0, f1 = act.frame_range
        N = int(round(f1 - f0)) + 1
        dur = (N - 1) / 30
        t = _np.arange(N) / 30.0
        cyc = max(1, round(dur / 2.4)) if loop else dur / 2.4
        flap = 0.09 * _np.sin(2 * math.pi * cyc * t / max(dur, 1e-3))
        if tr.name in ("PhaseShift", "PhaseShift2"):
            T = 1.15 if tr.name == "PhaseShift" else 1.25
            flap = flap - 0.9 * _np.clip(1 - (t - T) / 0.3, 0, 1) * (t >= T)
        for side, bn in ((1, "WingL"), (-1, "WingR")):
            qs = [_Q((0, 1, 0), float(side * flap[k])) @ _Q((0, 0, 1), float(side * 0.5 * flap[k])) for k in range(N)]
            _write(act, bn, qs)


# ================================================================ v4（v1.3.0）：噬語魔王新招 7 個
# 一階：Sweep 墨刃橫掃｜二階：Smash 魔劍震地、Leap 虛空躍擊、ComboB 吞字三連、Special 詞語風暴｜三階：ComboC 終焉四連、Special3 終焉之言
# 全部 30 fps 實格（sl=1.0），原地播放（Root 不動，Leap 的前進由遊戲位移）。Sweep 起訖＝Idle；其餘（二、三階才出）起訖＝IdleAggro。
# 每招 meta 多 "cancel"（秒）：跟隨動作完成、開始回戒備姿勢的那一格。
# rig.wing_keys[name]：紙翼額外開合（弧度，正＝張開、負＝收攏；secondary 疊在緩慢開合上）
# rig.spin_keys[name]：整身自轉角（度，+＝向左轉）；secondary 讓紙翼、墨潮、披風地面骨跟著轉，轉完回到原朝向。
V4_CLIPS = ("Sweep", "Smash", "Leap", "ComboB", "Special", "ComboC", "Special3")


def build_v4(rig, T, A, I, IA, wide, FL, FLr, FR, FRr):
    U = rig.U
    GL = -0.20
    rF = {s: Vector(rig.rest["Foot" + s]) / U for s in "LR"}
    rH = Vector(rig.rest["Hips"]) / U
    rH0 = Vector((rH.x, rH.y, 0.0))
    st = {"th": 0.0}
    orig_reach = rig.reach
    rig.wing_keys = getattr(rig, "wing_keys", {})
    rig.spin_keys = getattr(rig, "spin_keys", {})

    def rz(v, th):
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        v = Vector(v)
        return Vector((c * v.x - s * v.y, s * v.x + c * v.y, v.z))

    def reach(Pd, s, target, hint=None, blade=None, edge=None):
        th = st["th"]
        if th:
            if hint is None:
                hint = (-0.5, 0.6, -0.6) if s == "R" else (0.5, 0.6, -0.6)
            target = tuple(rz(target, th)); hint = tuple(rz(hint, th))
            if blade is not None:
                blade = rz(blade, th); edge = rz(edge, th)
        return orig_reach(Pd, s, target, hint, blade, edge)
    rig.reach = reach

    def nz(v):
        return Vector(v).normalized()

    def orth(e, d):
        e = Vector(e)
        e = e - d * e.dot(d)
        return e.normalized()

    def two(g, d, e, hint=None, elL=None, gl=None):
        def f(p):
            dd = nz(d)
            p["ikL"] = 1.0; p["gripL"] = GL if gl is None else gl
            p["elL"] = elL or (0.6, 0.3, -0.7)
            rig.reach(p, "R", g, hint, dd, orth(e, dd))
        return f

    def one(g, d, e, left, hint=None, hintL=None):
        def f(p):
            dd = nz(d)
            p["ikL"] = 0.0
            rig.reach(p, "R", g, hint, dd, orth(e, dd))
            rig.reach(p, "L", left, hintL)
        return f

    def KP(fn, th=0.0, hips=(0, 0, 0), **kw):
        """姿勢＋武器；th≠0 時整個姿勢（骨盆位置、骨盆朝向、雙腳、武器目標）繞世界 Z 轉 th 度。"""
        kw.setdefault("fL", FL); kw.setdefault("fLr", FLr); kw.setdefault("fR", FR); kw.setdefault("fRr", FRr)
        if th:
            hp = rz(Vector(hips) + rH0, th) - rH0
            hips = (hp.x, hp.y, hips[2])
            hr = list(kw.pop("hr", (0, 0, 0))); hr[2] += th; kw["hr"] = tuple(hr)
            kw["look"] = kw.get("look", 0.0) + th
            for s, fk, rk in (("L", "fL", "fLr"), ("R", "fR", "fRr")):
                base = Vector((rF[s].x, rF[s].y, 0.0))
                p_ = rz(base + Vector(kw[fk]), th) - base
                kw[fk] = (p_.x, p_.y, kw[fk][2])
                r_ = list(kw[rk]); r_[0] += th; kw[rk] = tuple(r_)
        p = T(hips=hips, **kw)
        st["th"] = th
        fn(p)
        st["th"] = 0.0
        return p

    def clip(name, keys, hits, cancel, wing, spin=None):
        A(name, keys, hits=hits, sl=1.0)
        if name in rig.meta:
            rig.meta[name]["cancel"] = round(cancel / rig.fps, 3)
            rig.wing_keys[name] = wing
            if spin:
                rig.spin_keys[name] = spin

    w = wide

    def rec(th=0.0):
        """共用回勢：重劍斜指前下。"""
        return KP(two((-0.10, -0.50, 0.98), (0.1, -0.9, 0.1), (0, -0.5, -0.8)), th=th, hips=(0, -0.15, -0.22), hr=(14, 0, -12),
                  sp=(7, 0, -4), ch=(6, 0, -3), fL=(0.11 * w, -0.40, 0), fR=(-0.13 * w, 0.30, 0))

    # ================================================================ Sweep 墨刃橫掃（一階）：劍收到左肩後（反手）→ 低位由左往右的大範圍掃擊（膝高）→ 甩到右後方
    # 與 Attack（直劈）、Attack2（右→左胸高橫斬）不同：方向相反、高度低、蓄力時身體往左扭
    lw = dict(fL=(0.11 * w, -0.30, 0), fR=(-0.13 * w, 0.28, 0), fRr=(-50, 0, 0))
    lw_wind = KP(two((0.30, 0.02, 1.42), (0.55, 0.72, 0.42), (-0.5, -0.7, 0), hint=(-0.3, -0.6, -0.8)),
                 hips=(0.05, 0.08, -0.16), hr=(6, 2, 32), sp=(3, 0, 12), ch=(1, 0, 12), nod=4, **lw)
    lw_coil = KP(two((0.36, 0.10, 1.36), (0.45, 0.82, 0.36), (-0.5, -0.7, 0), hint=(-0.3, -0.6, -0.8)),
                 hips=(0.06, 0.11, -0.23), hr=(8, 3, 40), sp=(4, 0, 14), ch=(2, 0, 14), nod=6, **lw)
    lw_coil2 = KP(two((0.37, 0.12, 1.34), (0.43, 0.84, 0.34), (-0.5, -0.7, 0), hint=(-0.3, -0.6, -0.8)),
                  hips=(0.06, 0.12, -0.25), hr=(9, 3, 43), sp=(4, 0, 15), ch=(2, 0, 15), nod=7, **lw)
    lwh = dict(fL=(0.12 * w, -0.50, 0), fR=(-0.13 * w, 0.26, 0.02), fRr=(-40, 20, 0))
    lw_hit = KP(two((0.02, -0.66, 0.92), (-0.20, -0.96, -0.28), (-1, 0.2, 0), hint=(-0.6, 0.2, -0.7)),
                hips=(-0.02, -0.20, -0.32), hr=(14, -2, -12), sp=(6, 0, -6), ch=(4, 0, -6), nod=4, **lwh)
    lw_fol = KP(two((-0.42, -0.36, 0.98), (-0.88, -0.30, -0.25), (0.2, 1, 0), hint=(-0.3, 0.5, -0.8)),
                hips=(-0.06, -0.20, -0.32), hr=(12, -4, -46), sp=(5, 0, -14), ch=(3, 0, -14), nod=4, **lwh)
    lw_fol2 = KP(two((-0.46, -0.10, 1.04), (-0.70, 0.62, -0.20), (0.6, 0.6, 0), hint=(-0.3, 0.5, -0.8)),
                 hips=(-0.06, -0.18, -0.30), hr=(11, -4, -58), sp=(5, 0, -17), ch=(3, 0, -16), nod=2, **lwh)
    lw_set = KP(two((-0.30, -0.35, 1.05), (-0.45, -0.55, -0.70), (0, 0.6, -0.5)),
                hips=(-0.03, -0.14, -0.24), hr=(10, 0, -30), sp=(4, 0, -9), ch=(3, 0, -8), **lwh)
    clip("Sweep", [(0, I), (10, lw_wind, "io"), (22, lw_coil, "io"), (28, lw_coil2, "io"), (33, lw_hit, "in3"), (38, lw_fol, "out3"),
                   (46, lw_fol2, "out"), (56, lw_set, "io"), (76, I, "io")], hits=[33], cancel=56,
         wing=[(0, 0), (14, -0.25), (30, -0.35), (33, 0.35), (44, 0.15), (76, 0)])

    # ================================================================ Smash 魔劍震地（二階）：雙手把劍直舉向天、抬左腳 → 跺腳深蹲、劍身平拍地面 → 低姿顫動 → 起身
    sm_f = dict(fL=(0.11 * w, -0.30, 0), fR=(-0.13 * w, 0.28, 0))
    sm_lift = KP(two((-0.04, -0.34, 1.50), (0, -0.12, 1.0), (0, -1, 0), hint=(-0.8, 0.2, -0.5)),
                 hips=(0, -0.02, -0.08), hr=(4, 0, -6), sp=(0, 0, -2), ch=(-2, 0, -2), **sm_f)
    sm_up = KP(two((-0.03, -0.10, 2.00), (0, 0.12, 1), (0, -1, 0), hint=(-1, 0.2, 0.1), elL=(0.9, 0.2, 0.0)),
               hips=(0, 0.02, -0.035), hr=(-8, 0, -4), sp=(-6, 0, -1), ch=(-10, 0, -1), nod=-14,
               fL=(0.11 * w, -0.30, 0.14), fLr=(10, -10, 0), fR=(-0.13 * w, 0.28, 0))
    sm_up2 = KP(two((-0.03, -0.04, 1.98), (0, 0.24, 0.97), (0, -1, 0), hint=(-1, 0.2, 0.1), elL=(0.9, 0.2, 0.0)),
                hips=(0, 0.03, -0.035), hr=(-10, 0, -4), sp=(-7, 0, -1), ch=(-12, 0, -1), nod=-16,
                fL=(0.11 * w, -0.32, 0.20), fLr=(10, -12, 0), fR=(-0.13 * w, 0.28, 0))
    smh = dict(fL=(0.11 * w, -0.52, 0), fR=(-0.13 * w, 0.30, 0), fRr=(-40, 30, 0))
    sm_hit = KP(two((0.0, -0.78, 0.60), (0.02, -0.94, -0.34), (0, 0.3, -1), hint=(-0.8, 0.4, -0.3)),
                hips=(0, -0.30, -0.50), hr=(34, 0, -2), sp=(15, 0, 0), ch=(13, 0, 0), nod=10, **smh)
    sm_low = KP(two((0.0, -0.78, 0.56), (0.02, -0.95, -0.31), (0, 0.3, -1), hint=(-0.8, 0.4, -0.3)),
                hips=(0, -0.31, -0.55), hr=(38, 0, -2), sp=(16, 0, 0), ch=(14, 0, 0), nod=14, **smh)
    sm_low2 = KP(two((0.0, -0.76, 0.58), (0.02, -0.95, -0.31), (0, 0.3, -1), hint=(-0.8, 0.4, -0.3)),
                 hips=(0.01, -0.30, -0.52), hr=(35, 1, 0), sp=(15, 0, 1), ch=(13, 0, 1), nod=6, look=6, **smh)
    clip("Smash", [(0, IA), (10, sm_lift, "io"), (20, sm_up, "out"), (27, sm_up2, "io"), (33, sm_up, "io"), (37, sm_hit, "in3"),
                   (41, sm_low, "out3"), (54, sm_low2, "io"), (64, rec(), "io"), (82, IA, "io")], hits=[37], cancel=64,
         wing=[(0, 0), (20, 0.55), (33, 0.6), (37, -0.35), (46, -0.2), (64, 0.05), (82, 0)])

    # ================================================================ Leap 虛空躍擊（二階）：伏低把劍拖在右後 → 躍起（劍舉過頭、雙腳收起、紙翼全開）→ 落地斜劈前下、弓步
    lp_c = dict(fL=(0.11 * w, -0.30, 0), fR=(-0.13 * w, 0.32, 0), fRr=(-45, 20, 0))
    lp_crouch = KP(two((-0.46, 0.26, 0.86), (-0.30, 0.88, -0.36), (0, -0.3, 1), hint=(-0.6, 0.6, -0.5)),
                   hips=(0, 0.08, -0.40), hr=(30, 0, -18), sp=(12, 0, -6), ch=(10, 0, -6), nod=-12, **lp_c)
    lp_crouch2 = KP(two((-0.47, 0.28, 0.82), (-0.30, 0.88, -0.36), (0, -0.3, 1), hint=(-0.6, 0.6, -0.5)),
                    hips=(0, 0.10, -0.46), hr=(34, 0, -20), sp=(13, 0, -6), ch=(11, 0, -6), nod=-16, **lp_c)
    lp_air = KP(two((-0.05, -0.10, 2.40), (0, 0.62, 0.78), (0, -0.78, 0.62), hint=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
                air=True, hips=(0, -0.20, 0.48), hr=(-12, 0, -6), sp=(-8, 0, -2), ch=(-12, 0, -2), nod=-6,
                fL=(0.11 * w, -0.18, 0.60), fLr=(10, 30, 0), fR=(-0.13 * w, 0.20, 0.42), fRr=(-45, 50, 0))
    lp_apex = KP(two((-0.05, -0.06, 2.46), (0, 0.75, 0.66), (0, -0.66, 0.75), hint=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)),
                 air=True, hips=(0, -0.28, 0.54), hr=(-14, 0, -6), sp=(-9, 0, -2), ch=(-13, 0, -2), nod=-2,
                 fL=(0.11 * w, -0.30, 0.56), fLr=(10, 20, 0), fR=(-0.13 * w, 0.16, 0.44), fRr=(-45, 45, 0))
    lph = dict(fL=(0.11 * w, -0.68, 0), fR=(-0.13 * w, 0.26, 0.03), fRr=(-40, 30, 0))
    lp_hit = KP(two((0.0, -0.90, 0.80), (0.02, -0.86, -0.50), (0, 0.5, -0.86), hint=(-0.8, 0.4, -0.3)),
                hips=(0, -0.46, -0.40), hr=(30, 0, 4), sp=(12, 0, 2), ch=(10, 0, 2), nod=6, **lph)
    lp_low = KP(two((0.0, -0.90, 0.76), (0.02, -0.88, -0.47), (0, 0.5, -0.86), hint=(-0.8, 0.4, -0.3)),
                hips=(0, -0.47, -0.46), hr=(34, 0, 4), sp=(13, 0, 2), ch=(11, 0, 2), nod=10, **lph)
    lp_low2 = KP(two((0.0, -0.88, 0.78), (0.02, -0.88, -0.47), (0, 0.5, -0.86), hint=(-0.8, 0.4, -0.3)),
                 hips=(0.01, -0.46, -0.44), hr=(32, 1, 2), sp=(12, 0, 2), ch=(10, 0, 2), nod=4, look=-6, **lph)
    clip("Leap", [(0, IA), (12, lp_crouch, "io"), (22, lp_crouch2, "io"), (25, lp_crouch, "io"), (32, lp_air, "out"), (40, lp_apex, "out"),
                  (46, lp_hit, "in3"), (50, lp_low, "out3"), (62, lp_low2, "io"), (72, rec(), "io"), (90, IA, "io")], hits=[46], cancel=72,
         wing=[(0, 0), (12, -0.25), (24, -0.32), (32, 0.7), (40, 0.55), (46, -0.3), (56, -0.15), (90, 0)])

    # ================================================================ ComboB 吞字三連（二階，慢—快—快）：低位右後蓄 → ① 右下往左上斜撩
    # → ② 左手符紋爪前抓（吞字；命中量左手）→ ③ 左上往右下斜劈
    cbf = dict(fL=(0.11 * w, -0.36, 0), fR=(-0.13 * w, 0.30, 0))
    cbl = dict(fL=(0.11 * w, -0.50, 0), fR=(-0.13 * w, 0.26, 0.03), fRr=(-40, 20, 0))
    cb_draw = KP(two((-0.42, 0.18, 0.86), (-0.35, 0.80, -0.48), (0.4, -0.5, 0.75), hint=(-0.6, 0.6, -0.5)),
                 hips=(-0.04, 0.06, -0.26), hr=(12, 0, -44), sp=(5, 0, -12), ch=(4, 0, -12), nod=-4, **cbf)
    cb_draw2 = KP(two((-0.44, 0.20, 0.84), (-0.35, 0.80, -0.48), (0.4, -0.5, 0.75), hint=(-0.6, 0.6, -0.5)),
                  hips=(-0.05, 0.08, -0.31), hr=(14, 0, -50), sp=(6, 0, -14), ch=(5, 0, -14), nod=-6, **cbf)
    cb_up = KP(two((0.22, -0.50, 1.70), (0.45, -0.55, 0.70), (0.6, -0.2, 0.75), hint=(-0.5, -0.3, -0.8)),
               hips=(0.04, -0.16, -0.10), hr=(2, 0, 24), sp=(-2, 0, 10), ch=(-4, 0, 10), nod=-6, **cbl)
    cb_upf = KP(two((0.22, -0.30, 1.86), (0.35, 0.25, 0.90), (0.3, 0.8, 0.3), hint=(-0.5, -0.3, -0.8)),
                hips=(0.04, -0.14, -0.08), hr=(-2, 0, 32), sp=(-3, 0, 12), ch=(-5, 0, 12), nod=-8, **cbl)
    cb_cw = KP(one((-0.40, -0.10, 1.62), (-0.2, 0.35, 0.92), (0, -1, 0), (0.42, 0.30, 1.14), hint=(-0.8, 0.2, -0.5), hintL=(0.7, 0.5, -0.4)),
               hips=(0.03, -0.08, -0.18), hr=(6, 0, 36), sp=(3, 0, 10), ch=(2, 0, 10), nod=-2, **cbl)
    cbc = dict(fL=(0.11 * w, -0.58, 0), fR=(-0.13 * w, 0.26, 0.03), fRr=(-40, 20, 0))
    cb_claw = KP(one((-0.42, -0.20, 1.55), (-0.25, 0.20, 0.95), (0, -1, 0), (0.20, -1.02, 1.32), hint=(-0.8, 0.2, -0.5), hintL=(0.6, 0.3, -0.7)),
                 hips=(0.0, -0.34, -0.24), hr=(18, 0, -28), sp=(8, 0, -10), ch=(6, 0, -10), nod=-4, **cbc)
    cb_claw2 = KP(one((-0.42, -0.18, 1.56), (-0.25, 0.20, 0.95), (0, -1, 0), (0.18, -0.86, 1.30), hint=(-0.8, 0.2, -0.5), hintL=(0.6, 0.3, -0.7)),
                  hips=(0.0, -0.32, -0.23), hr=(16, 0, -22), sp=(6, 0, -6), ch=(5, 0, -6), nod=2, **cbc)
    cb_dw = KP(two((0.16, -0.24, 1.80), (0.45, 0.35, 0.82), (-0.5, -0.6, -0.3), hint=(-0.5, -0.2, -0.8)),
               hips=(0.02, -0.22, -0.14), hr=(4, 0, 26), sp=(-2, 0, 8), ch=(-4, 0, 8), nod=-4, **cbc)
    cb_down = KP(two((-0.24, -0.62, 1.00), (-0.50, -0.72, -0.48), (-0.5, -0.3, -0.8), hint=(-0.7, 0.2, -0.6)),
                 hips=(-0.03, -0.32, -0.30), hr=(22, 0, -26), sp=(9, 0, -8), ch=(8, 0, -8), nod=6, **cbc)
    cb_downf = KP(two((-0.46, -0.34, 0.88), (-0.78, -0.30, -0.48), (-0.3, 0.3, -0.9), hint=(-0.4, 0.5, -0.7)),
                  hips=(-0.05, -0.32, -0.33), hr=(24, 0, -40), sp=(10, 0, -12), ch=(8, 0, -12), nod=6, **cbc)
    cb_downf2 = KP(two((-0.46, -0.32, 0.90), (-0.78, -0.30, -0.48), (-0.3, 0.3, -0.9), hint=(-0.4, 0.5, -0.7)),
                   hips=(-0.04, -0.31, -0.31), hr=(22, 1, -37), sp=(9, 0, -11), ch=(7, 0, -11), nod=2, **cbc)
    clip("ComboB", [(0, IA), (12, cb_draw, "io"), (22, cb_draw2, "io"), (27, cb_up, "in3"), (32, cb_upf, "out3"), (38, cb_cw, "io"),
                    (43, cb_claw, "in3"), (48, cb_claw2, "out"), (52, cb_dw, "io"), (57, cb_down, "in3"), (62, cb_downf, "out3"),
                    (76, cb_downf2, "io"), (86, rec(), "io"), (104, IA, "io")], hits=[27, (43, "HandL"), 57], cancel=86,
         wing=[(0, 0), (22, -0.3), (27, 0.3), (38, 0.1), (43, 0.35), (52, 0.0), (57, 0.3), (76, 0.1), (104, 0)])

    # ================================================================ Special 詞語風暴（二階必殺）：雙手橫舉巨劍過頂、紙翼全開、仰首（約 1.4 秒）
    # → 往右後扭身蓄力 → 向左原地兩圈旋風斬（劍水平伸出腰高；每圈正面一擊）→ 甩出減速 → 回正、低姿 → IdleAggro
    st_f = dict(fL=(0.12 * w, -0.28, 0), fR=(-0.14 * w, 0.28, 0), fRr=(-30, 0, 0))
    st_raise = KP(two((0.04, -0.12, 1.96), (-0.97, 0.1, 0.2), (0, -1, 0.1), hint=(-0.9, 0.1, 0.1), elL=(0.9, 0.1, 0.2)),
                  hips=(0, 0.02, -0.035), hr=(-8, 0, 0), sp=(-6, 0, 0), ch=(-10, 0, 0), nod=-18, **st_f)
    st_raise2 = KP(two((0.04, -0.10, 2.00), (-0.97, 0.1, 0.24), (0, -1, 0.1), hint=(-0.9, 0.1, 0.1), elL=(0.9, 0.1, 0.2)),
                   hips=(0, 0.03, -0.035), hr=(-10, 0, 0), sp=(-7, 0, 0), ch=(-13, 0, 0), nod=-22, **st_f)
    spf = dict(fL=(0.12 * w, -0.30, 0), fR=(-0.14 * w, 0.30, 0), fRr=(-35, 0, 0))

    def S(th, back=0.0, low=0.0, lean=6.0):
        """旋風斬姿勢：劍水平伸出、刃口朝轉動方向（左轉 → +X）；back＝劍往後拖的角度。"""
        d = rz((0.25, -0.97, -0.02), -back)
        g = rz((0.05, -0.62, 1.15 - low), -back * 0.5)
        return KP(two(tuple(g), tuple(d), tuple(rz((1, 0.25, 0), -back)), hint=(-0.6, 0.2, -0.7)), th=th,
                  hips=(0, -0.05, -0.20 - low * 0.5), hr=(10, lean, 0), sp=(3, 0, 6), ch=(2, 0, 8), **spf)
    st_coil = S(-100, back=40, low=0.05)
    st_coil2 = S(-108, back=48, low=0.08)
    sk = [(0, IA, None, 0), (12, st_raise, "io", 0), (24, st_raise2, "io", 0), (32, st_raise, "io", 0), (40, st_raise2, "io", 0),
          (46, st_coil, "io", -100), (49, st_coil2, "io", -108), (54, S(0), "in3", 0)]
    f_ = 54.0
    for th in (60, 120, 180, 240, 300):
        f_ += 2.5
        sk.append((round(f_), S(th), None, th))
    sk += [(69, S(360), None, 360), (73, S(420, back=-20), "out", 420), (79, S(450, back=-30, low=0.06, lean=2), "out3", 450),
           (92, rec(360), "io", 360), (112, IA, "io", 360)]
    clip("Special", [k[:3] if k[2] else k[:2] for k in sk], hits=[54, 69], cancel=92,
         wing=[(0, 0), (12, 0.6), (24, 0.75), (40, 0.8), (48, 0.3), (54, -0.4), (69, -0.45), (79, 0.3), (92, 0.2), (112, 0)],
         spin=[(k[0], k[3]) for k in sk])

    # ================================================================ ComboC 終焉四連（三階，4 擊）：① 收劍直刺 → ② 刺出後往上翻挑 → ③ 向右旋身一圈肩高斬
    # → 旋轉中把劍舉過頂、小跳 → ④ 落地重劈（劍身停在地面上方）
    cc_f = dict(fL=(0.11 * w, -0.30, 0), fR=(-0.13 * w, 0.32, 0))
    cct = dict(fL=(0.11 * w, -0.48, 0), fR=(-0.13 * w, 0.24, 0.02), fRr=(-40, 15, 0))
    cc_pull = KP(two((-0.32, 0.22, 1.12), (0.08, -1, 0.06), (0, 0, -1), hint=(-0.7, 0.5, -0.5)),
                 hips=(-0.02, 0.08, -0.22), hr=(10, 0, -36), sp=(5, 0, -10), ch=(4, 0, -8), nod=-4, **cc_f)
    cc_pull2 = KP(two((-0.34, 0.26, 1.10), (0.08, -1, 0.06), (0, 0, -1), hint=(-0.7, 0.5, -0.5)),
                  hips=(-0.02, 0.10, -0.26), hr=(11, 0, -41), sp=(5, 0, -11), ch=(4, 0, -9), nod=-6, **cc_f)
    cc_thr = KP(two((-0.06, -0.80, 1.28), (0.04, -1, 0.03), (0, 0, -1), hint=(-0.8, 0.3, -0.5)),
                hips=(0.02, -0.26, -0.18), hr=(8, 0, 10), sp=(4, 0, 4), ch=(2, 0, 4), nod=-2, **cct)
    cc_rip = KP(two((-0.04, -0.52, 1.86), (0.02, -0.40, 0.92), (0, 0.9, 0.4), hint=(-0.8, 0.0, -0.4)),
                hips=(0.02, -0.20, -0.08), hr=(-4, 0, 4), sp=(-4, 0, 2), ch=(-8, 0, 2), nod=-10, **cct)
    ccs = dict(fL=(0.11 * w, -0.34, 0), fR=(-0.13 * w, 0.30, 0), fRr=(-40, 0, 0))

    def C(th, back=0.0):
        """肩高旋斬（向右轉）：劍往外前上方伸出，刃口朝 -X。"""
        d = rz((-0.30, -0.94, 0.15), back)
        g = rz((-0.05, -0.60, 1.45), back * 0.5)
        return KP(two(tuple(g), tuple(d), tuple(rz((-1, 0.3, 0), back)), hint=(-0.6, 0.0, -0.8)), th=th,
                  hips=(0, -0.06, -0.18), hr=(8, -6, 0), sp=(3, 0, -6), ch=(2, 0, -8), **ccs)

    def R(th, hop):
        return KP(two((-0.05, 0.0, 2.02 + hop), (0, 0.70, 0.71), (0, -0.7, 0.7), hint=(-0.9, -0.2, -0.2), elL=(0.8, -0.2, -0.2)), th=th,
                  air=hop > 0, hips=(0, 0.0, hop - 0.04), hr=(-10, 0, 0), sp=(-7, 0, 0), ch=(-10, 0, 0), nod=-4,
                  fL=(0.11 * w, -0.30, hop * 0.9), fLr=(10, 25 * (hop > 0), 0), fR=(-0.13 * w, 0.26, hop * 0.8), fRr=(-40, 35 * (hop > 0), 0))
    cch = dict(fL=(0.11 * w, -0.56, 0), fR=(-0.13 * w, 0.30, 0), fRr=(-40, 25, 0))
    cc_crash = KP(two((0.0, -0.80, 0.72), (0.02, -0.90, -0.44), (0, 0.44, -0.9), hint=(-0.8, 0.4, -0.3)), th=-360,
                  hips=(0, -0.36, -0.44), hr=(32, 0, 0), sp=(14, 0, 0), ch=(12, 0, 0), nod=8, **cch)
    cc_low = KP(two((0.0, -0.80, 0.68), (0.02, -0.91, -0.41), (0, 0.44, -0.9), hint=(-0.8, 0.4, -0.3)), th=-360,
                hips=(0, -0.37, -0.50), hr=(36, 0, 0), sp=(15, 0, 0), ch=(13, 0, 0), nod=12, **cch)
    cc_low2 = KP(two((0.0, -0.78, 0.70), (0.02, -0.91, -0.41), (0, 0.44, -0.9), hint=(-0.8, 0.4, -0.3)), th=-360,
                 hips=(0.01, -0.36, -0.47), hr=(33, -1, 2), sp=(14, 0, 1), ch=(12, 0, 1), nod=4, look=-6, **cch)
    ck = [(0, IA, None, 0), (10, cc_pull, "io", 0), (20, cc_pull2, "io", 0), (24, cc_thr, "in3", 0), (28, cc_thr, "out", 0),
          (33, cc_rip, "in3", 0), (40, C(100, back=-30), "io", 100), (45, C(0), "in3", 0), (48, C(-75), None, -75),
          (51, C(-150, back=20), None, -150), (55, R(-225, 0.06), None, -225), (59, R(-290, 0.16), "out", -290),
          (62, R(-335, 0.18), "io", -335), (66, cc_crash, "in3", -360), (70, cc_low, "out3", -360), (84, cc_low2, "io", -360),
          (94, rec(-360), "io", -360), (112, IA, "io", -360)]
    clip("ComboC", [k[:3] if k[2] else k[:2] for k in ck], hits=[24, 33, 45, 66], cancel=94,
         wing=[(0, 0), (20, -0.2), (24, 0.25), (33, 0.35), (45, -0.3), (61, 0.5), (66, -0.3), (84, 0), (112, 0)],
         spin=[(k[0], k[3]) for k in ck])

    # ================================================================ Special3 終焉之言（三階終極必殺）：劍豎在面前低頭宣誓 → 懸浮升空、劍直指天（約 2.5 秒）
    # → 劍收到左肩後 → ① 俯衝落地斜劈（左上→右下）單膝跪地 → 跪姿顫動、劍拖到右後 → ② 起身反向大撩（右下→左上）雙臂高舉 → 定格 → IdleAggro
    f3o = dict(fL=(0.08 * w, -0.20, 0), fR=(-0.09 * w, 0.22, 0), fRr=(-25, 0, 0))
    f3_oath = KP(two((-0.02, -0.38, 1.42), (0, -0.08, 1), (0, -1, 0), hint=(-0.8, 0.3, -0.5)),
                 hips=(0, 0, -0.10), hr=(6, 0, -2), sp=(4, 0, 0), ch=(4, 0, 0), nod=22, **f3o)
    f3_oath2 = KP(two((-0.02, -0.36, 1.38), (0, -0.06, 1), (0, -1, 0), hint=(-0.8, 0.3, -0.5)),
                  hips=(0, 0, -0.13), hr=(8, 0, -2), sp=(5, 0, 0), ch=(6, 0, 0), nod=28, **f3o)

    def F(hz, gz, nod, bl=(0, 0.05, 1), arch=0.0):
        return KP(two((-0.02, -0.18, gz), bl, (0, -1, 0), hint=(-1, 0, 0.1), elL=(0.9, 0, 0.1)), air=True,
                  hips=(0, 0, hz), hr=(-4 - arch, 0, -2), sp=(-4 - arch * 0.5, 0, 0), ch=(-8 - arch, 0, 0), nod=nod,
                  fL=(0.07 * w, -0.12, hz * 0.95 + 0.02), fLr=(8, 35, 0), fR=(-0.08 * w, 0.12, hz * 0.9), fRr=(-20, 40, 0))
    f3_r1 = F(0.22, 2.18, -6)
    f3_r2 = F(0.36, 2.30, -16, bl=(0, 0.15, 0.99), arch=4)
    f3_r3 = F(0.40, 2.33, -18, bl=(0, 0.12, 0.99), arch=5)

    def FW(hz, k):
        return KP(two((0.28 + 0.02 * k, 0.02 + 0.03 * k, 1.86 + hz), (0.45, 0.55 + 0.1 * k, 0.70), (-0.5, -0.5, -0.5), hint=(-0.3, -0.6, -0.8)),
                  air=True, hips=(0, 0.05, hz), hr=(-6, 0, 26 + 4 * k), sp=(-4, 0, 8), ch=(-8, 0, 8 + 2 * k), nod=-10,
                  fL=(0.07 * w, -0.14, hz * 0.95 + 0.02), fLr=(8, 30, 0), fR=(-0.08 * w, 0.14, hz * 0.9), fRr=(-20, 40, 0))
    kn3 = dict(fL=(0.10 * w, -0.42, 0), fR=(-0.08 * w, 0.40, -0.03), fRr=(-10, 68, 0), kR=(-0.2, 0, 0))
    f3_h1 = KP(two((-0.30, -0.70, 0.72), (-0.62, -0.72, -0.30), (-0.5, -0.3, -0.8), hint=(-0.7, 0.3, -0.5)),
               hips=(-0.02, -0.20, -0.50), hr=(14, 0, -24), sp=(6, 0, -8), ch=(5, 0, -8), nod=10, **kn3)
    f3_h1f = KP(two((-0.52, -0.42, 0.64), (-0.86, -0.36, -0.30), (-0.3, 0.3, -0.9), hint=(-0.5, 0.5, -0.6)),
                hips=(-0.03, -0.20, -0.52), hr=(16, 0, -36), sp=(7, 0, -11), ch=(6, 0, -11), nod=12, **kn3)
    f3_h1f2 = KP(two((-0.52, -0.40, 0.66), (-0.86, -0.36, -0.30), (-0.3, 0.3, -0.9), hint=(-0.5, 0.5, -0.6)),
                 hips=(-0.02, -0.19, -0.50), hr=(14, 1, -33), sp=(6, 0, -10), ch=(5, 0, -10), nod=8, look=-5, **kn3)
    f3_g = KP(two((-0.48, 0.10, 0.74), (-0.50, 0.80, -0.30), (0.3, -0.4, 0.85), hint=(-0.6, 0.6, -0.5)),
              hips=(-0.03, -0.12, -0.50), hr=(12, 0, -44), sp=(5, 0, -12), ch=(4, 0, -12), nod=-2, **kn3)
    f3_g2 = KP(two((-0.50, 0.14, 0.72), (-0.50, 0.80, -0.30), (0.3, -0.4, 0.85), hint=(-0.6, 0.6, -0.5)),
               hips=(-0.03, -0.10, -0.53), hr=(14, 0, -50), sp=(6, 0, -14), ch=(5, 0, -14), nod=-4, **kn3)
    f3u = dict(fL=(0.11 * w, -0.42, 0), fR=(-0.13 * w, 0.26, 0.05), fRr=(-40, 25, 0))
    f3_h2 = KP(two((0.24, -0.42, 1.98), (0.40, -0.35, 0.85), (0.6, -0.1, 0.8), hint=(-0.5, -0.3, -0.8)),
               hips=(0.02, -0.18, -0.035), hr=(-6, 0, 30), sp=(-6, 0, 10), ch=(-10, 0, 10), nod=-14, **f3u)
    f3_h2f = KP(two((0.24, -0.16, 2.06), (0.30, 0.15, 0.94), (0.3, 0.9, 0.2), hint=(-0.5, -0.3, -0.8)),
                hips=(0.02, -0.14, -0.035), hr=(-9, 0, 34), sp=(-7, 0, 11), ch=(-12, 0, 11), nod=-18, **f3u)
    f3_h2f2 = KP(two((0.22, -0.18, 2.03), (0.30, 0.15, 0.94), (0.3, 0.9, 0.2), hint=(-0.5, -0.3, -0.8)),
                 hips=(0.02, -0.14, -0.05), hr=(-8, 0, 32), sp=(-6, 0, 10), ch=(-11, 0, 10), nod=-14, **f3u)
    clip("Special3", [(0, IA), (12, f3_oath, "io"), (22, f3_oath2, "io"), (34, f3_r1, "io"), (46, f3_r2, "io"), (56, f3_r3, "io"),
                      (64, FW(0.42, 0), "io"), (70, FW(0.44, 1), "io"), (76, f3_h1, "in3"), (81, f3_h1f, "out3"), (94, f3_h1f2, "io"),
                      (104, f3_g, "io"), (110, f3_g2, "io"), (115, f3_h2, "in3"), (121, f3_h2f, "out3"), (136, f3_h2f2, "io"),
                      (148, rec(), "io"), (166, IA, "io")], hits=[76, 115], cancel=148,
         wing=[(0, 0), (22, -0.3), (46, 0.7), (64, 0.85), (76, -0.4), (94, -0.3), (110, -0.4), (115, 0.8), (136, 0.6), (148, 0.1), (166, 0)])

    rig.__dict__.pop("reach", None)
