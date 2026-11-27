"""v3 暗影行刑者：依 art/v3/specs/boss_executioner.md 比例表建的人體（取代共用 Body 的固定比例）。
所有高度／直徑以 HT（頭罩尖到靴底）為 1 定義，再乘上 HT（公尺）。屬性名稱與共用 Body 相同，Rig／build_armature 可直接使用。
"""
import math
from mathutils import Vector
from soul_humanoid_lib import Surf, V, FWD, X, Y, Z, w_blend, w_zchain, smooth, lerp


class ExBody:
    def __init__(self, HT=2.4):
        self.HT = HT
        h = lambda x: x * HT
        self.h = h
        self.H = h(0.91)          # 顱頂（共用函式把 H 當頭頂）
        self.U = U = HT / 2.0     # 動作座標單位（主角比例 1.8 m → U=1）
        self.B = 1.3              # 體寬倍率（地面檢查用）
        self.wf = 1.0
        self.R = U * 1.3
        self.RL = U * 1.2
        self.head = h(0.11)
        j = self.j = {}
        self.hzv = h(0.47)
        self.head_base = h(0.795)
        self.nz = h(0.755)
        span = self.nz - self.hzv
        self.span = span
        self.tz = lambda t: self.hzv + span * t
        j["Root"] = V(0, 0, 0)
        j["Hips"] = V(0, 0, h(0.47))
        j["Spine"] = V(0, h(0.002), h(0.535))
        j["Spine2"] = V(0, h(0.004), h(0.625))
        j["Neck"] = V(0, h(0.004), h(0.755))
        j["Head"] = V(0, 0.0, h(0.795))
        j["HeadTop"] = V(0, 0.0, h(0.93))
        j["ShoulderL"] = V(h(0.025), h(0.004), h(0.765))
        j["UpperArmL"] = V(h(0.138), h(0.004), h(0.772))
        self.sw = h(0.138)
        a = math.radians(66.0)
        ud = V(math.cos(a), 0, -math.sin(a))
        e = math.radians(16.0)
        fd = (ud * math.cos(e) + FWD * math.sin(e)).normalized()
        self.ua_len = h(0.17); self.fa_len = h(0.15); self.hand_len = h(0.075)
        j["ForearmL"] = j["UpperArmL"] + ud * self.ua_len
        j["HandL"] = j["ForearmL"] + fd * self.fa_len
        j["HandTipL"] = j["HandL"] + fd * self.hand_len
        self.ud, self.fd = ud, fd
        j["ThighL"] = V(h(0.075), 0, h(0.44))
        j["ShinL"] = V(h(0.100), h(-0.012), h(0.25))
        j["FootL"] = V(h(0.125), h(0.006), h(0.062))
        j["ToeL"] = V(h(0.128), h(-0.100), h(0.014))
        for k in list(j):
            if k.endswith("L"):
                p = j[k]
                j[k[:-1] + "R"] = V(-p.x, p.y, p.z)
        # 軀幹截面：（高度 HT, 半寬, 半厚, du, dv 往前為正）——身體（皮膚／肌肉）尺寸
        tb = [(0.375, 0.080, 0.062, 0, 0.008), (0.40, 0.118, 0.076, 0, 0.010), (0.44, 0.140, 0.083, 0, 0.010), (0.48, 0.135, 0.084, 0, 0.006),
              (0.53, 0.111, 0.080, 0, 0.002), (0.58, 0.124, 0.084, 0, 0.004), (0.63, 0.144, 0.093, 0, 0.008), (0.68, 0.155, 0.095, 0, 0.010),
              (0.73, 0.157, 0.090, 0, 0.006), (0.765, 0.135, 0.078, 0, 0.0), (0.79, 0.085, 0.062, 0, -0.002), (0.81, 0.040, 0.040, 0, 0.0),
              (0.84, 0.036, 0.038, 0, 0.0)]
        self.torso = Surf(V(0, 0, 0), Z, [(h(z), h(rx), h(ry), du, h(dv)) for z, rx, ry, du, dv in tb])
        La, Lf = self.ua_len, self.fa_len
        # 上臂直徑 0.065、前臂 0.055、手腕 0.042（身體）
        self.uarm = Surf(j["UpperArmL"], ud, [(-0.02, h(0.036), h(0.036), 0, 0), (La * 0.4, h(0.0305), h(0.0315), 0, 0),
                                              (La * 0.8, h(0.0300), h(0.0305), 0, 0), (La, h(0.029), h(0.029), 0, 0)])
        self.farm = Surf(j["ForearmL"], fd, [(0, h(0.028), h(0.028), 0, 0), (Lf * 0.3, h(0.029), h(0.0285), 0, 0),
                                             (Lf * 0.5, h(0.0275), h(0.026), 0, 0), (Lf * 0.95, h(0.021), h(0.019), 0, 0), (Lf, h(0.021), h(0.019), 0, 0)])
        td = (j["ShinL"] - j["ThighL"]); Lt = td.length
        sd = (j["FootL"] - j["ShinL"]); Ls = sd.length
        self.th_len, self.sh_len = Lt, Ls
        # 大腿直徑 0.11、小腿 0.08、腳踝 0.055
        self.thigh = Surf(j["ThighL"], td, [(-0.06, h(0.054), h(0.050), 0, 0), (Lt * 0.4, h(0.052), h(0.053), 0, 0),
                                            (Lt * 0.85, h(0.046), h(0.046), 0, 0), (Lt, h(0.043), h(0.044), 0, 0)])
        self.shin = Surf(j["ShinL"], sd, [(0, h(0.042), h(0.043), 0, 0), (Ls * 0.4, h(0.036), h(0.037), 0, h(-0.002)),
                                          (Ls * 0.75, h(0.030), h(0.030), 0, 0), (Ls * 0.95, h(0.0275), h(0.0275), 0, 0), (Ls, h(0.0275), h(0.0275), 0, 0)])
        self.hand_a = fd.copy()
        v = FWD - fd * FWD.dot(fd); self.hand_v = v.normalized()
        hu = self.hand_v.cross(fd)
        self.hand_u = -hu if hu.x < 0 else hu
        self.set_grip(h(0.012))

    def set_grip(self, r):
        RL = 1.45   # 手掌大小（拳 0.065×0.055 HT）
        self.grip_r = r
        self.finger_r = 0.0118 * RL
        self.grip_rc = r + self.finger_r
        self.knuckle_dir = (self.hand_u * 0.8 + self.hand_a * 0.6).normalized()
        self.knuckle = self.j["HandL"] + self.hand_a * (0.082 * RL) + self.hand_u * (0.008 * RL)
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

    def w_wrist(self):
        return w_blend("ForearmL", "HandL", self.j["HandL"], self.fd, 0.05 * self.U)

    def w_knee(self):
        j = self.j
        return w_blend("ThighL", "ShinL", j["ShinL"],
                       (j["ShinL"] - j["ThighL"]).normalized() + (j["FootL"] - j["ShinL"]).normalized(), 0.12 * self.U)

    def w_hipthigh(self):
        """骨盆→大腿：大腿上段平滑混入 Hips。"""
        j = self.j

        def f(co):
            ax = (j["ShinL"] - j["ThighL"]).normalized()
            side = "L" if co.x >= 0 else "R"
            P = j["Thigh" + side]
            a2 = Vector((ax.x if side == "L" else -ax.x, ax.y, ax.z))
            t = (co - P).dot(a2)
            s = smooth((t + 0.03 * self.U) / (0.10 * self.U))
            return {"Hips": 1 - s, "Thigh" + side: s}
        return f
