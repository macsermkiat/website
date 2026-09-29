"""Clips for the figures. Each clip is fn(t) -> pose dict (see rig.py for the rotation convention).

Crowd clips (every figure):
  idle, walk, chat, drink, laugh, sit            - holding the Gluehwein mug in the right hand
  idle_free, walk_free, chat_free, laugh_free, sit_free - no mug (hide the `mug` node)
Band (people_band_*): play (slow ballad loop, hands on the instrument), rest (standing/seated break)
Vendors (people_vendor_*): serve (hand a mug across the counter), wipe (idle behind the counter)

All clips loop: pose(0) == pose(duration).
"""
import math
import zlib

from mathutils import Vector, Matrix, Quaternion

import rig
from rig import Q, Poser, frame, sgn
from pmesh import smoothstep, lerp

TAU = 2 * math.pi
SEAT_BENCH = 0.475


def osc(t, T, k=1, ph=0.0):
    return math.sin(TAU * k * t / T + ph)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def env(t, keys):
    """Piecewise eased interpolation between (time, value) keys."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t0 <= t <= t1:
            f = ease((t - t0) / (t1 - t0))
            if isinstance(v0, (int, float)):
                return v0 + (v1 - v0) * f
            return v0.lerp(v1, f)
    return keys[-1][1]


def hand_rot(fig, side, d, n):
    """World rotation for a hand whose fingers point along d with the palm facing n."""
    W, d0, n0, t0 = fig.hand_frame(side)
    return (frame(d, n) @ frame(d0, n0).transposed()).to_quaternion()


def hand_rot_thumb(fig, side, d, thumb):
    """Hand rotation from finger direction and thumb direction."""
    d = Vector(d).normalized()
    thumb = Vector(thumb)
    thumb = (thumb - d * thumb.dot(d)).normalized()
    k = 1.0 if side == "R" else -1.0
    n = thumb.cross(d) * k
    return hand_rot(fig, side, d, n)


class Clips:
    def __init__(self, fig, seed=0.0):
        self.f = fig
        self.P = fig.P
        self.s = fig.P["s"]
        self.J = fig.J
        self.ph = seed          # per-figure phase so clips differ a little
        self.child = fig.P["kind"] == "child"

    def poser(self, pose=None):
        return Poser(self.f.rest, pose)

    # ------------------------------------------------------------------ building blocks
    def stance(self, pz, t, T, amt=1.0):
        """Relaxed standing: slight contrapposto, breathing, weight shift."""
        s = self.s
        shift = osc(t, T, 1, self.ph) * amt
        pz.set("hips", Q(0.0, 0.025 * shift, 0.03 * shift))
        pz.pose["_root"] = Vector((0.012 * s * shift, 0.0, -0.004 * s - 0.003 * s * abs(shift)))
        pz.set("spine", Q(0.02 + 0.01 * osc(t, T, 2), -0.02 * shift, -0.02 * shift))
        pz.set("chest", Q(0.015 * osc(t, T, 3, 0.4) * amt, -0.01 * shift, 0.0))
        # legs: the unweighted knee bends a little
        for side in "LR":
            k = sgn(side)
            w = 0.5 + 0.5 * shift * k           # 1 = weighted
            bend = 0.03 + 0.1 * (1 - w)
            pz.set(f"thigh.{side}", Q(-bend * 0.6, -k * 0.02 - 0.025 * shift, 0.04 * k))
            pz.set(f"shin.{side}", Q(bend, 0.0, 0.0))
            pz.set(f"foot.{side}", Q(-bend * 0.4, 0.0, -0.05 * k))
        # keep the head level: counter the hips tilt
        pz.set("neck", Q(0.02, 0.02 * shift, 0.0))

    def look(self, pz, yaw=0.0, pitch=0.0, roll=0.0):
        pz.set("head", Q(pitch, roll, yaw))

    def arm_hang(self, pz, side, fwd=0.05, out=0.08, bend=0.22, twist=0.0):
        k = sgn(side)
        pz.set(f"shoulder.{side}", Q(0.0, 0.0, 0.0))
        pz.set(f"upperarm.{side}", Q(-fwd, -k * out, 0.0))
        pz.set(f"forearm.{side}", Q(-bend, 0.0, -k * twist))
        pz.set(f"hand.{side}", Q(0.0, 0.0, 0.0))

    def chest_pt(self, pz, p):
        """A point given in rest coordinates that rides with the chest."""
        return pz.pt("chest", Vector(p))

    def spine_pt(self, pz, p):
        return pz.pt("spine", Vector(p))

    def mug_hold(self, pz, lift=0.0, sway=Vector()):
        """Right forearm level, mug in front of the belly, thumb up."""
        s, P = self.s, self.P
        tgt = Vector((-0.095 * s, -0.2 * s, P["z_waist"] + (0.05 + lift) * s)) + sway
        W = self.spine_pt(pz, tgt)
        R = pz.R("spine")
        d = R @ Vector((0.45, -1.0, 0.08))
        thumb = R @ Vector((0.0, 0.1, 1.0))
        pz.ik("upperarm.R", "forearm.R", W, R @ Vector((-0.3, 0.6, -1.0)), end="hand.R",
              end_rot=hand_rot_thumb(self.f, "R", d, thumb))

    def mug_mouth_target(self, pz, tilt=0.9):
        """Wrist position and hand rotation that put the mug rim at the lips."""
        f, s = self.f, self.s
        Rh = pz.R("head")
        mouth = pz.pt("head", f.head_pt(-math.pi / 2, math.radians(-44), 0.012 * s))
        # mug axis tilted back toward the face; fingers point across toward the left
        axis = Rh @ Vector((0.0, math.sin(tilt), math.cos(tilt)))
        d = Rh @ Vector((0.9, -0.35, 0.0))
        rot = hand_rot_thumb(f, "R", d, axis)
        # rim point in the rest hand frame -> offset from the wrist
        W0 = f.J["wrist.R"]
        c, ax = f.mug_center, f.mug_axis
        h = 0.095 * (0.85 if self.child else 1.0)
        r = 0.037 * (0.85 if self.child else 1.0)
        rim = c + ax * h * 0.5 + (Vector((0, 1, 0)) - ax * ax.y).normalized() * r   # rim edge toward the face
        off = rim - W0
        return mouth - rot @ off, rot

    def pocket(self, pz, side, depth=0.0):
        """Hand in the coat pocket."""
        f, s, P = self.f, self.s, self.P
        k = sgn(side)
        th = -math.pi / 2 + k * 0.85
        z = P["z_hip"] - (0.0 if f.spec["coat"].get("style") != "short" else -0.04) * s
        p = f.coat_pt(th, z, -0.035 * s)
        W = self.spine_pt(pz, p + Vector((0, 0, 0.085 * s)))
        R = pz.R("hips")
        d = R @ Vector((-k * 0.3, 0.25, -1.0))
        n = R @ Vector((-k, 0.1, 0.0))
        pz.ik(f"upperarm.{side}", f"forearm.{side}", W, R @ Vector((k * 0.8, 0.8, -0.3)), end=f"hand.{side}",
              end_rot=hand_rot(f, side, d, n))

    def gesture(self, pz, side, t, T, amp=1.0, ph=0.0):
        """An open hand moving in front of the chest while talking."""
        s, P, f = self.s, self.P, self.f
        k = sgn(side)
        a = osc(t, T, 2, ph) * amp
        b = osc(t, T, 3, ph + 1.1) * amp
        c = osc(t, T, 1, ph + 0.4)
        p = Vector((k * (0.16 + 0.05 * a) * s, (-0.26 - 0.05 * c) * s, P["z_waist"] + (0.2 + 0.06 * b) * s))
        W = self.spine_pt(pz, p)
        R = pz.R("spine")
        d = R @ Vector((-k * 0.3, -1.0, 0.25 + 0.2 * a))
        n = R @ Vector((-k * 0.5, -0.1 * c, 0.9))
        pz.ik(f"upperarm.{side}", f"forearm.{side}", W, R @ Vector((k * 0.7, 0.6, -1.0)), end=f"hand.{side}",
              end_rot=hand_rot(f, side, d, n))

    # ------------------------------------------------------------------ crowd clips
    def idle(self, t, mug=True, T=6.0):
        pz = self.poser()
        self.stance(pz, t, T)
        yaw = 0.25 * osc(t, T, 1, self.ph + 1.0) + 0.08 * osc(t, T, 3, 0.3)
        self.look(pz, yaw, 0.03 + 0.03 * osc(t, T, 2, 0.7), 0.03 * osc(t, T, 1))
        if mug:
            self.mug_hold(pz, lift=0.01 * osc(t, T, 2))
            self.pocket(pz, "L")
        else:
            self.pocket(pz, "L")
            self.pocket(pz, "R")
        return pz.pose

    def chat(self, t, mug=True, T=6.0):
        pz = self.poser()
        self.stance(pz, t, T, 0.6)
        # nods and turns while talking
        nod = 0.06 * max(0.0, osc(t, T, 4, self.ph)) + 0.03 * osc(t, T, 3, 0.5)
        self.look(pz, 0.18 * osc(t, T, 1, self.ph + 2.0), nod, 0.05 * osc(t, T, 2, 0.2))
        pz.set("chest", Q(0.04 + 0.02 * osc(t, T, 2, 1.0), 0.0, 0.05 * osc(t, T, 1, self.ph)))
        if mug:
            self.mug_hold(pz, lift=0.02 * osc(t, T, 2, 0.5))
            self.gesture(pz, "L", t, T, 1.0, self.ph)
        else:
            self.gesture(pz, "R", t, T, 1.0, self.ph)
            self.gesture(pz, "L", t, T, 0.6, self.ph + 2.4)
        return pz.pose

    def laugh(self, t, mug=True, T=4.0):
        pz = self.poser()
        self.stance(pz, t, T, 0.3)
        # a laugh: head back, shoulders shaking, settle
        k = env(t, [(0, 0.0), (0.5, 1.0), (2.4, 1.0), (3.4, 0.0), (T, 0.0)])
        shake = osc(t, T, 20) * 0.035 * k
        pz.set("spine", Q(-0.08 * k + 0.02, 0.0, 0.0))
        pz.set("chest", Q(-0.06 * k + shake, 0.0, 0.0))
        for side in "LR":
            pz.set(f"shoulder.{side}", Q(0.0, sgn(side) * (0.06 * k + shake), 0.0))
        self.look(pz, 0.1 * k, -0.28 * k + shake * 1.5, 0.05 * k)
        # left hand to the belly
        s, P, f = self.s, self.P, self.f
        p = f.coat_pt(-math.pi / 2 + 0.3, P["z_waist"] + 0.02 * s, 0.03 * s)
        free = self.spine_pt(pz, p)
        if mug:
            self.mug_hold(pz, lift=0.03 * k)
            R = pz.R("spine")
            pz.ik("upperarm.L", "forearm.L", free.lerp(self.spine_pt(pz, f.coat_pt(-math.pi / 2 + 0.85, P["z_hip"], -0.01)), 1 - k),
                  R @ Vector((0.8, 0.8, -0.5)), end="hand.L", end_rot=hand_rot(f, "L", R @ Vector((-0.9, -0.2, -0.3)), R @ Vector((0, 1, 0))))
        else:
            R = pz.R("spine")
            pz.ik("upperarm.L", "forearm.L", free, R @ Vector((0.8, 0.8, -0.5)), end="hand.L",
                  end_rot=hand_rot(f, "L", R @ Vector((-0.9, -0.2, -0.3)), R @ Vector((0, 1, 0))))
            self.gesture(pz, "R", t, T, 0.4 * k, 0.5)
        return pz.pose

    def drink(self, t, T=6.0):
        pz = self.poser()
        self.stance(pz, t, T, 0.4)
        k = env(t, [(0, 0.0), (0.6, 0.0), (1.6, 1.0), (3.4, 1.0), (4.4, 0.0), (T, 0.0)])
        sip = env(t, [(0, 0.0), (1.4, 0.0), (1.9, 1.0), (3.1, 1.0), (3.5, 0.0), (T, 0.0)])
        self.look(pz, 0.05 * (1 - k), -0.2 * sip - 0.04 * k, 0.0)
        pz.set("chest", Q(0.02 - 0.03 * sip, 0.0, 0.0))
        # blend: hold pose -> lips
        hold = self.poser(dict(pz.pose))
        self.mug_hold(hold)
        W1 = hold.G("forearm.R") @ self.f.rest.tail["forearm.R"]
        R1 = hold.R("hand.R")
        W2, R2 = self.mug_mouth_target(pz, tilt=0.35 + 0.65 * sip)
        W = W1.lerp(W2, k)
        R = R1.slerp(R2, k)
        pz.ik("upperarm.R", "forearm.R", W, pz.R("spine") @ Vector((-0.6, 0.6, -1.0)).lerp(Vector((-0.35, -0.15, -1.0)), k),
              end="hand.R", end_rot=R)
        self.pocket(pz, "L")
        return pz.pose

    def walk(self, t, mug=True, T=1.2):
        pz = self.poser()
        s = self.s
        ph = TAU * t / T
        A = 0.36 if not self.child else 0.42
        for side in "LR":
            k = sgn(side)
            p = ph if side == "L" else ph + math.pi
            th = A * math.sin(p)
            knee = 0.08 + 0.9 * max(0.0, math.cos(p + 0.45)) ** 2 + 0.12 * max(0.0, math.sin(p - 0.4)) ** 4
            pz.set(f"thigh.{side}", Q(-th - 0.03, 0.0, 0.03 * k))
            pz.set(f"shin.{side}", Q(knee, 0.0, 0.0))
            toe = -0.18 * max(0.0, math.sin(p)) ** 2 + 0.4 * max(0.0, -math.sin(p + 0.6)) ** 3
            pz.set(f"foot.{side}", Q(toe - 0.3 * knee * max(0.0, math.cos(p + 0.45)), 0.0, 0.0))
        pz.pose["_root"] = Vector((-0.012 * s * math.cos(ph), 0.0, (-0.022 + 0.014 * math.cos(2 * ph)) * s))
        pz.set("hips", Q(0.02, 0.03 * math.cos(ph), -0.08 * math.sin(ph)))
        pz.set("spine", Q(0.04, -0.02 * math.cos(ph), 0.05 * math.sin(ph)))
        pz.set("chest", Q(0.02 + 0.01 * math.cos(2 * ph), -0.01 * math.cos(ph), 0.05 * math.sin(ph)))
        pz.set("neck", Q(0.02, 0.02 * math.cos(ph), -0.02 * math.sin(ph)))
        self.look(pz, 0.06 * osc(t, T * 4 if False else T, 1, 1.0) * 0.3, 0.02, 0.0)
        for side in "LR":
            k = sgn(side)
            p = ph if side == "L" else ph + math.pi
            sw = 0.3 * math.sin(p)
            self.arm_hang(pz, side, fwd=-sw + 0.02, out=0.1, bend=0.22 + 0.2 * max(0.0, -math.sin(p)))
        if mug:
            self.mug_hold(pz, sway=Vector((0, 0, 0.008 * s * math.cos(2 * ph))))
        return pz.pose

    def sit(self, t, mug=True, T=6.0, seat=SEAT_BENCH, lean=-0.08, feet=None, hands="lap"):
        pz = self.poser()
        s, P, J = self.s, self.P, self.J
        breathe = osc(t, T, 2, self.ph)
        hip_z = seat + 0.075 * s
        pz.pose["_root"] = Vector((0.0, 0.06 * s, hip_z - P["z_hip"]))
        pz.set("hips", Q(lean * 0.5, 0.0, 0.0))
        pz.set("spine", Q(lean + 0.02 * breathe, 0.0, 0.0))
        pz.set("chest", Q(0.05 + 0.015 * breathe, 0.0, 0.03 * osc(t, T, 1, self.ph)))
        self.look(pz, 0.2 * osc(t, T, 1, self.ph + 2.0), 0.05 + 0.03 * osc(t, T, 2), 0.0)
        for side in "LR":
            k = sgn(side)
            hip = pz.pt("hips", J[f"hip.{side}"])
            lth = self.f.rest.length(f"thigh.{side}")
            tgt = feet(side) if feet else Vector((k * (P["hip_x"] + 0.03 * s), hip.y - lth * 0.95, P["z_ankle"]))
            pz.ik(f"thigh.{side}", f"shin.{side}", tgt, Vector((k * 0.15, -1.0, 0.4)), end=f"foot.{side}",
                  end_rot=Quaternion())
        if hands == "lap":
            for side in "LR":
                if mug and side == "R":
                    continue
                k = sgn(side)
                knee = pz.pt(f"thigh.{side}", J[f"hip.{side}"].lerp(J[f"knee.{side}"], 0.6))
                W = knee + Vector((k * 0.02 * s, 0.07 * s, P["thigh_r"] + 0.03 * s))
                R = pz.R(f"thigh.{side}")
                pz.ik(f"upperarm.{side}", f"forearm.{side}", W, Vector((k * 0.6, 0.8, -0.4)), end=f"hand.{side}",
                      end_rot=hand_rot(self.f, side, Vector((-k * 0.2, -1, -0.3)), Vector((0, 0, -1))))
            if mug:
                self.mug_hold(pz, lift=0.06 + 0.01 * breathe)
        return pz.pose

    # ------------------------------------------------------------------ band
    def band_play(self, t, inst, T=8.0):
        """Slow ballad loop at 60 bpm: 8 beats."""
        fn = getattr(self, "play_" + inst)
        return fn(t, T)

    def play_sax(self, t, T):
        pz = self.poser()
        s = self.s
        beat = osc(t, T, 8)
        phrase = osc(t, T, 1, 0.3)
        pz.pose["_root"] = Vector((0.01 * phrase, 0.012, -0.012 - 0.01 * max(0.0, beat) * 0.5))
        pz.set("hips", Q(0.0, 0.02 * phrase, 0.03 * phrase))
        pz.set("spine", Q(0.05 + 0.03 * osc(t, T, 2, 0.8), -0.02 * phrase, 0.0))
        pz.set("chest", Q(0.04, 0.0, -0.08))
        for side in "LR":
            k = sgn(side)
            b = 0.08 + 0.05 * max(0.0, beat) * (1 if side == "L" else 0.6)
            pz.set(f"thigh.{side}", Q(-b * 0.6, -0.03 * k, 0.08 * k))
            pz.set(f"shin.{side}", Q(b, 0, 0))
            pz.set(f"foot.{side}", Q(-b * 0.4, 0, -0.08 * k))
        # head toward the mouthpiece
        sx = SAX
        self.look(pz, -0.12, 0.2 + 0.03 * phrase, -0.1)
        pz.set("neck", Q(0.12, 0.0, 0.0))
        mouth = pz.pt("head", self.f.head_pt(-math.pi / 2, math.radians(-44), 0.012 * s))
        err = sx["tip"] - mouth
        # slide the body so the lips meet the mouthpiece; height is taken up by the knees / neck
        pz.pose["_root"] = pz.pose["_root"] + Vector((err.x, err.y, max(-0.06, min(0.0, err.z))))
        pz._G = {}
        if err.z > 0.0:
            pz.set("neck", Q(0.12 - min(0.35, err.z * 4.0), 0.0, 0.0))
        for side, key in (("L", "lh"), ("R", "rh")):
            W, d, n = sx[key]
            k = sgn(side)
            pz.ik(f"upperarm.{side}", f"forearm.{side}", W, Vector((k * 0.9, 0.5, -0.5)), end=f"hand.{side}",
                  end_rot=hand_rot(self.f, side, d, n))
        return pz.pose

    def play_piano(self, t, T):
        s, P = self.s, self.P
        chord = [0.0, 0.05, -0.03, 0.02][int(4 * t / T) % 4]
        nxt = [0.0, 0.05, -0.03, 0.02][(int(4 * t / T) + 1) % 4]
        u = (4 * t / T) % 1.0
        cl = lerp(chord, nxt, ease((u - 0.85) / 0.15))
        rh = 0.035 * osc(t, T, 3, 0.4) + 0.02 * osc(t, T, 5)
        press = [max(0.0, osc(t, T, 8, a)) for a in (0.0, 1.3)]

        def feet(side):
            if side == "R":
                return Vector((-0.1, -0.29, 0.1))
            return Vector((0.16, -0.24, P["z_ankle"]))
        pz = self.poser(self.sit(t, mug=False, T=T, seat=0.5175, lean=0.06, feet=feet, hands="none"))
        pz.set("chest", Q(0.1 + 0.02 * osc(t, T, 2), 0.0, 0.03 * osc(t, T, 1)))
        self.look(pz, 0.08 * osc(t, T, 1, 0.5), 0.3 + 0.04 * osc(t, T, 2, 0.2), 0.04 * osc(t, T, 1))
        pz.pose["_root"] = Vector((0.0, 0.1, 0.5175 + 0.075 * s - P["z_hip"]))
        pz._G = {}
        for side, x, pr in (("L", 0.2 + cl, press[0]), ("R", -0.17 + rh, press[1])):
            k = sgn(side)
            W = Vector((x, -0.235, 0.775 - 0.008 * pr))
            d = Vector((-k * 0.15, -1.0, -0.45))
            n = Vector((0.0, 0.0, -1.0))
            pz.ik(f"upperarm.{side}", f"forearm.{side}", W, Vector((k * 1.0, 0.4, -0.6)), end=f"hand.{side}",
                  end_rot=hand_rot(self.f, side, d, n))
        return pz.pose

    def play_bass(self, t, T):
        s = self.s
        pz = self.poser()
        beat = osc(t, T, 8)
        pz.pose["_root"] = Vector((-0.02, 0.03, -0.01 - 0.006 * max(0.0, beat)))
        pz.set("hips", Q(0.0, 0.0, 0.08))
        pz.set("spine", Q(0.08, 0.02 * osc(t, T, 2), 0.1))
        pz.set("chest", Q(0.06, 0.0, 0.05 + 0.02 * osc(t, T, 1)))
        for side in "LR":
            k = sgn(side)
            b = 0.1 + 0.05 * max(0.0, beat)
            pz.set(f"thigh.{side}", Q(-b * 0.6, -0.04 * k, 0.1 * k))
            pz.set(f"shin.{side}", Q(b, 0, 0))
            pz.set(f"foot.{side}", Q(-b * 0.4, 0, -0.1 * k))
        self.look(pz, 0.35, 0.15 + 0.04 * osc(t, T, 4), 0.1)
        slide = [0.0, -0.08, -0.03, -0.11][int(4 * t / T) % 4]
        W, d, n = BASS["lh"](slide)
        pz.ik("upperarm.L", "forearm.L", W, Vector((0.9, 0.3, -0.4)), end="hand.L", end_rot=hand_rot(self.f, "L", d, n))
        pl = max(0.0, osc(t, T, 8, 0.3)) ** 3
        W, d, n = BASS["rh"](pl)
        pz.ik("upperarm.R", "forearm.R", W, Vector((-0.9, 0.5, -0.4)), end="hand.R", end_rot=hand_rot(self.f, "R", d, n))
        return pz.pose

    def play_drums(self, t, T):
        s, P = self.s, self.P

        def feet(side):
            if side == "R":
                return Vector((-0.06, -0.33, 0.1 + 0.015 * max(0.0, osc(t, T, 8))))
            return Vector((0.36, -0.2, 0.095 + 0.02 * max(0.0, osc(t, T, 4, math.pi))))
        pz = self.poser(self.sit(t, mug=False, T=T, seat=0.54, lean=0.04, feet=feet, hands="none"))
        pz.pose["_root"] = Vector((0.0, 0.085, 0.54 + 0.075 * s - P["z_hip"]))
        pz.set("chest", Q(0.1, 0.0, 0.03 * osc(t, T, 2)))
        self.look(pz, 0.05 * osc(t, T, 1), 0.28 + 0.05 * max(0.0, osc(t, T, 4)), 0.03 * osc(t, T, 2))
        pz._G = {}
        # the right hand sweeps slow circles, the left taps on 2 and 4
        a = TAU * 4 * t / T
        for side in "LR":
            k = sgn(side)
            g = DRUMS["grip_" + side].copy()
            if side == "R":
                g += Vector((0.02 * math.cos(a), 0.018 * math.sin(a), 0.004 * math.sin(a)))
            else:
                g += Vector((0.0, 0.0, 0.02 * max(0.0, osc(t, T, 4, 1.2)) ** 2))
            d = DRUMS["dir_" + side]
            n = Vector((0, 0, -1))
            pz.ik(f"upperarm.{side}", f"forearm.{side}", g, Vector((k * 1.0, 0.5, -0.4)), end=f"hand.{side}",
                  end_rot=hand_rot(self.f, side, d, n))
        return pz.pose

    # ------------------------------------------------------------------ vendors
    def serve(self, t, T=6.0):
        pz = self.poser()
        s, P, f = self.s, self.P, self.f
        self.stance(pz, t, T, 0.3)
        k = env(t, [(0, 0.0), (1.0, 0.0), (2.2, 1.0), (3.0, 1.0), (4.2, 0.0), (T, 0.0)])
        pz.set("hips", Q(0.12 * k, 0.0, 0.0))
        pz.set("spine", Q(0.12 * k + 0.02, 0.0, 0.0))
        pz.set("chest", Q(0.06 * k, 0.0, 0.1 * k))
        self.look(pz, -0.1 * k, 0.15 * k + 0.03, 0.0)
        hold = self.poser(dict(pz.pose))
        self.mug_hold(hold)
        W1 = hold.G("forearm.R") @ f.rest.tail["forearm.R"]
        R1 = hold.R("hand.R")
        W2 = Vector((-0.14 * s, -0.62 * s, 1.02))
        W = W1.lerp(W2, k)
        pz.ik("upperarm.R", "forearm.R", W, Vector((-0.8, 0.6, -0.6)), end="hand.R", end_rot=R1)
        # left hand rests on the counter edge while leaning
        WL = Vector((0.2 * s, -0.5 * s, 1.0))
        pz.ik("upperarm.L", "forearm.L", WL.lerp(self.spine_pt(pz, f.coat_pt(-math.pi / 2 + 0.85, P["z_hip"], -0.01)), 1 - k),
              Vector((0.8, 0.6, -0.6)), end="hand.L", end_rot=hand_rot(f, "L", Vector((-0.2, -1, -0.2)), Vector((0, 0, -1))))
        return pz.pose

    def wipe(self, t, T=4.0):
        """Wiping the counter with the left hand, looking out at the square."""
        pz = self.poser()
        s, P, f = self.s, self.P, self.f
        self.stance(pz, t, T, 0.4)
        pz.set("hips", Q(0.08, 0.0, 0.0))
        pz.set("spine", Q(0.1, 0.0, 0.0))
        self.look(pz, 0.3 * osc(t, T, 1, 0.5), 0.12, 0.0)
        a = TAU * 2 * t / T
        WL = Vector(((0.12 + 0.07 * math.cos(a)) * s, (-0.5 + 0.04 * math.sin(a)) * s, 0.98))
        pz.ik("upperarm.L", "forearm.L", WL, Vector((0.8, 0.6, -0.6)), end="hand.L",
              end_rot=hand_rot(f, "L", Vector((-0.2, -1, -0.3)), Vector((0, 0, -1))))
        self.pocket(pz, "R")
        return pz.pose


# ------------------------------------------------------------------ instrument geometry (from blender/rides/instruments.py)
def _instrument_targets():
    Rx = lambda a: Matrix.Rotation(a, 4, "X")
    Ry = lambda a: Matrix.Rotation(a, 4, "Y")
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")
    # tenor sax: mouthpiece tip at (0,-0.10,1.53); body axis local +Z, tilted by Ry(0.36). Pass 2: the ride
    # builder's re-proportioned tenor (instruments.py build_sax) has its mouthpiece tip at (0, 0.272, 0.896) and the
    # key stacks centred at z 0.615 (left hand) and 0.37 (right hand); the wrists sit 4.5 and 6 cm below them
    tip = Vector((0, 0.272, 0.896))
    Mh = Ry(0.36)
    t = Mh @ tip
    M = Matrix.Translation(Vector((0.0, -0.10, 1.53)) - t) @ Mh
    ax = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
    lh_c = M @ Vector((0, 0, 0.57))
    rh_c = M @ Vector((0, 0, 0.31))
    sax = {
        "tip": Vector((0.0, -0.085, 1.535)),
        # wrists beside and behind the key stacks, fingers wrapping onto the pearls (front, -Y)
        "lh": (lh_c + Vector((0.075, 0.07, 0.03)), Vector((-0.8, -0.6, -0.2)), Vector((-0.55, -0.1, 0.2))),
        "rh": (rh_c + Vector((-0.06, 0.075, 0.035)), Vector((0.45, -0.85, -0.3)), Vector((0.5, -0.2, 0.2))),
    }
    # double bass
    Mb = Matrix.Translation((0.16, -0.30, 0)) @ Rz(-0.32) @ Rx(-0.26)

    def lh(slide):
        z = 1.47 + slide
        neck = Mb @ Vector((0, -0.04 + (z - 1.35) * -0.15, z))
        W = neck + (Mb.to_3x3() @ Vector((0.075, 0.075, -0.06)))
        d = Mb.to_3x3() @ Vector((-0.7, -0.6, 0.35))
        n = Mb.to_3x3() @ Vector((-0.6, -0.2, -0.1))
        return W, d, n

    def rh(pluck):
        p = Mb @ Vector((-0.02, -0.17, 0.86))
        W = p + (Mb.to_3x3() @ Vector((-0.13, 0.03 + 0.03 * pluck, 0.1)))
        d = Mb.to_3x3() @ Vector((0.6, -0.55, -0.6))
        n = Mb.to_3x3() @ Vector((0.4, 0.0, -0.3))
        return W, d, n
    bass = {"lh": lh, "rh": rh}
    # drums: brushes from their handle ends (pivots) toward the snare
    sc = Vector((0.03, -0.36, 0.60))
    head_z = sc.z + 0.072
    drums = {}
    for side, a, dx in (("L", 0.5, 0.05), ("R", -0.55, -0.05)):
        d = Vector((math.sin(a), -math.cos(a), 0))
        h0 = Vector((sc.x + dx, sc.y + 0.28, head_z + 0.06))
        h1 = h0 + d * 0.22 + Vector((0, 0, -0.035))
        drums["grip_" + side] = h0.lerp(h1, 0.35) + Vector((0, 0.035, 0.03))
        drums["dir_" + side] = (h1 - h0).normalized()
    return sax, bass, drums


SAX, BASS, DRUMS = _instrument_targets()


def crowd_clips(fig):
    # crc32, not hash(): str hashes are salted per process, so hash() gave every build different phases
    c = Clips(fig, seed=(zlib.crc32(fig.spec["name"].encode()) % 628) / 100.0)
    out = [
        ("idle", lambda t: c.idle(t, True), 6.0),
        ("walk", lambda t: c.walk(t, True), 1.2),
        ("chat", lambda t: c.chat(t, True), 6.0),
        ("drink", lambda t: c.drink(t), 6.0),
        ("laugh", lambda t: c.laugh(t, True), 4.0),
        ("sit", lambda t: c.sit(t, True), 6.0),
        ("idle_free", lambda t: c.idle(t, False), 6.0),
        ("walk_free", lambda t: c.walk(t, False), 1.2),
        ("chat_free", lambda t: c.chat(t, False), 6.0),
        ("laugh_free", lambda t: c.laugh(t, False), 4.0),
        ("sit_free", lambda t: c.sit(t, False), 6.0),
    ]
    return c, out
