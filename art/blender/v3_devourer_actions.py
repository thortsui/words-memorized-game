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

    def T(hips=(0, 0, 0), hr=(0, 0, 0), sp=(0, 0, 0), ch=(0, 0, 0), look=0.0, nod=0.0, **kw):
        yaw = max(-75, min(75, look - (hr[2] + sp[2] + ch[2])))
        pit = nod - 0.7 * (hr[0] + sp[0] + ch[0])
        rol = -0.6 * (hr[1] + sp[1] + ch[1])
        d = dict(fL=FL, fLr=FLr, fR=FR, fRr=FRr)
        d.update(kw)
        hips = (hips[0], hips[1], min(hips[2], -0.035))      # v3：腿較長，骨盆不可高過站姿，否則腳會被拉離地面
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
        hits = [round(h * k_) for h in hits] if hits else None
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
