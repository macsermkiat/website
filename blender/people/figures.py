"""Organizer's figure builder: realistic-miniature people in winter clothes, built as skinned meshes.

A figure = proportions (body kind + height) + a wardrobe spec. The geometry is lofted from rings
around the skeleton and every vertex gets skin weights from the part it belongs to. Materials:
  body  - skin, hair, trousers, boots, gloves, buttons, eyes (vertex colour, white factor)
  coat  - the outer garment (factor = coat colour, vertex colour = seams/shading detail)
  scarf - scarf or neckerchief (factor = scarf colour, vertex colour = stripes)
  hat   - hat (factor = hat colour)
  mug   - the Gluehwein mug in the right hand (separate node `mug`, the engine may hide it)
"""
import math
import random

from mathutils import Vector, Matrix, Quaternion

from pmesh import Mesh, smoothstep, lerp, TAU
import rig


def lin(h):
    """sRGB hex (or 0-255 tuple) to linear RGB."""
    if isinstance(h, str):
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    else:
        c = [x / 255 for x in h]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mul(c, k):
    return tuple(min(1.0, x * k) for x in c)


# ------------------------------------------------------------------ proportions
MAN = dict(H=1.78, s=1.0, z_pelvis=0.975, z_waist=1.09, z_chest=1.29, z_neck=1.49, z_headbase=1.575,
           sh_x=0.178, z_sh=1.415, l_upper=0.30, l_fore=0.262, l_hand=0.185, hip_x=0.09, z_hip=0.925,
           z_knee=0.51, z_ankle=0.085, l_foot=0.265,
           head=(0.076, 0.098, 0.118), neck_r=0.058,
           chest=(0.168, 0.118), waist=(0.155, 0.11), hips=(0.17, 0.12),
           thigh_r=0.082, knee_r=0.058, calf_r=0.062, ankle_r=0.046, upper_r=0.05, elbow_r=0.043, wrist_r=0.034)
WOMAN = dict(MAN, H=1.78, s=1.0, sh_x=0.172, hip_x=0.092, head=(0.075, 0.096, 0.115), neck_r=0.052,
             chest=(0.158, 0.118), waist=(0.14, 0.104), hips=(0.182, 0.125),
             thigh_r=0.084, knee_r=0.057, calf_r=0.06, ankle_r=0.043, upper_r=0.046, elbow_r=0.04, wrist_r=0.031)
CHILD = dict(H=1.20, s=0.68, z_pelvis=0.61, z_waist=0.70, z_chest=0.835, z_neck=0.962, z_headbase=1.015,
             sh_x=0.122, z_sh=0.912, l_upper=0.205, l_fore=0.17, l_hand=0.125, hip_x=0.066, z_hip=0.57,
             z_knee=0.315, z_ankle=0.058, l_foot=0.18,
             head=(0.075, 0.093, 0.112), neck_r=0.04,
             chest=(0.125, 0.1), waist=(0.122, 0.097), hips=(0.128, 0.097),
             thigh_r=0.062, knee_r=0.046, calf_r=0.047, ankle_r=0.034, upper_r=0.042, elbow_r=0.035, wrist_r=0.027)
LEN_KEYS = ["H", "z_pelvis", "z_waist", "z_chest", "z_neck", "z_headbase", "sh_x", "z_sh", "l_upper", "l_fore",
            "l_hand", "hip_x", "z_hip", "z_knee", "z_ankle", "l_foot", "neck_r", "thigh_r", "knee_r", "calf_r",
            "ankle_r", "upper_r", "elbow_r", "wrist_r"]


def body_props(kind, H):
    base = {"man": MAN, "woman": WOMAN, "child": CHILD}[kind]
    k = H / base["H"]
    P = dict(base)
    for key in LEN_KEYS:
        P[key] = base[key] * k
    for key in ("head", "chest", "waist", "hips"):
        # heads scale less than bodies (smaller people have relatively larger heads)
        kk = k ** (0.55 if key == "head" else 1.0)
        P[key] = tuple(v * kk for v in base[key])
    P["s"] = base["s"] * k
    P["kind"] = kind
    return P


# ------------------------------------------------------------------ figure
class Figure:
    def __init__(self, spec, lite=False):
        self.spec = spec
        self.lite = lite
        self.P = body_props(spec["body"], spec["H"])
        self.J = rig.joints(self.P)
        self.rest = rig.Rest(self.J)
        self.m = Mesh()
        self.mug = Mesh()
        self.rng = random.Random(spec["name"])
        P = self.P
        rx, ry, rz = P["head"]
        self.C = Vector((0, 0.004, P["H"] - rz))          # head centre
        self.skin = lin(spec.get("skin", "#e0b49a"))
        self.hair = lin(spec.get("hair_color", "#3a2a20"))
        # level of detail
        L = lite
        self.n_torso = 12 if L else 22
        self.n_limb = 6 if L else 10
        self.n_head = (10, 7) if L else (16, 11)
        # the mug: held by the handle in the right hand, axis along the thumb side
        W, d, n, t = self.hand_frame("R")
        kk = 0.85 if P["kind"] == "child" else 1.0
        self.mug_k = kk
        self.mug_center = W + d * 0.1 * (P["l_hand"] / 0.185) + n * 0.058 * kk
        self.mug_axis = t
        self.J["mug0"] = self.mug_center.copy()
        self.J["mug1"] = self.mug_center + t * 0.05
        self.rest = rig.Rest(self.J)

    # ============================================================ weights
    def w_chain1d(self, x, stops, bones, bw):
        """Partition of unity along a 1D coordinate: bone i covers [stops[i], stops[i+1]]."""
        w = {}
        n = len(bones)
        for i, b in enumerate(bones):
            lo = 1.0 if i == 0 else smoothstep(stops[i] - bw, stops[i] + bw, x)
            hi = 0.0 if i == n - 1 else smoothstep(stops[i + 1] - bw, stops[i + 1] + bw, x)
            v = lo - hi
            if v > 1e-4:
                w[b] = w.get(b, 0) + v
        return w

    def w_spine(self, p, zmax=None):
        J, s = self.J, self.P["s"]
        z = p.z if zmax is None else min(p.z, zmax)
        return self.w_chain1d(z, [0, J["waist"].z, J["chest"].z, J["neck"].z], ["hips", "spine", "chest", "neck"],
                              0.05 * s)

    def w_coat(self, p):
        P, J, s = self.P, self.J, self.P["s"]
        w = self.w_spine(p, zmax=J["neck"].z - 0.03 * s)
        ax = abs(p.x)
        side = "L" if p.x > 0 else "R"
        c = w.get("chest", 0.0)
        if c > 0:
            f_arm = smoothstep(P["sh_x"] - 0.06 * s, P["sh_x"] + 0.03 * s, ax) * \
                smoothstep(P["z_sh"] - 0.15 * s, P["z_sh"] - 0.02 * s, p.z) * 0.55
            f_sh = smoothstep(0.04 * s, P["sh_x"] * 0.9, ax) * smoothstep(J["chest"].z, P["z_sh"], p.z) * 0.6
            wa = c * f_arm
            ws = (c - wa) * f_sh
            w["chest"] = c - wa - ws
            w[f"upperarm.{side}"] = w.get(f"upperarm.{side}", 0) + wa
            w[f"shoulder.{side}"] = w.get(f"shoulder.{side}", 0) + ws
        zh = P["z_hip"]
        if p.z < zh + 0.04 * s:
            # The skirt is split at the hip line: below it every vertex rides the thigh on its side, front
            # and back, so a seated coat lies on the lap and is sat on at the back instead of stretching
            # between hips and thighs into a flat disc. The transition is short (0.20 m) because a long
            # hips/thigh blend collapses toward the hip joint when the thigh turns 90 degrees.
            f = smoothstep(zh + 0.04 * s, zh - 0.16 * s, p.z)
            lat = 0.5 + 0.5 * math.tanh(p.x / (0.045 * s))
            hw = w.get("hips", 0.0)
            w["hips"] = hw * (1 - f)
            # below the knee the hem drapes with the shins (over the knees when seated)
            zk = P["z_knee"] + 0.04 * s
            g = smoothstep(zk, zk - 0.12 * s, p.z) * (0.8 if p.y < 0.0 else 0.65)
            w["thigh.L"] = w.get("thigh.L", 0) + hw * f * lat * (1 - g)
            w["thigh.R"] = w.get("thigh.R", 0) + hw * f * (1 - lat) * (1 - g)
            if g > 0:
                w["shin.L"] = w.get("shin.L", 0) + hw * f * lat * g
                w["shin.R"] = w.get("shin.R", 0) + hw * f * (1 - lat) * g
        return w

    def chain(self, names):
        pts = [self.J[n] for n in names]
        cum = [0.0]
        for a, b in zip(pts[:-1], pts[1:]):
            cum.append(cum[-1] + (b - a).length)
        return pts, cum

    def chain_s(self, p, pts, cum):
        best = None
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
            d = (a + ab * t - p).length
            if best is None or d < best[0]:
                best = (d, cum[k] + t * ab.length)
        return best[1]

    def w_arm(self, p, side):
        pts, cum = self.chain([f"clav.{side}", f"shoulder.{side}", f"elbow.{side}", f"wrist.{side}", f"fingers.{side}"])
        x = self.chain_s(p, pts, cum)
        s = self.P["s"]
        w = self.w_chain1d(x, cum[:4], [f"shoulder.{side}", f"upperarm.{side}", f"forearm.{side}", f"hand.{side}"],
                           0.035 * s)
        # blend the very top of the sleeve into the chest
        sh = w.get(f"shoulder.{side}", 0)
        if sh:
            w["chest"] = sh * 0.5
            w[f"shoulder.{side}"] = sh * 0.5
        return w

    def w_leg(self, p, side):
        pts, cum = self.chain([f"hip.{side}", f"knee.{side}", f"ankle.{side}", f"toe.{side}"])
        s = self.P["s"]
        J = self.J
        if p.z > J[f"hip.{side}"].z:
            f = smoothstep(J[f"hip.{side}"].z - 0.02 * s, J[f"hip.{side}"].z + 0.07 * s, p.z)
            return {"hips": f, f"thigh.{side}": 1 - f}
        x = self.chain_s(p, pts, cum)
        return self.w_chain1d(x, cum[:3], [f"thigh.{side}", f"shin.{side}", f"foot.{side}"], 0.04 * s)

    def w_head(self, p):
        zc = self.C.z - self.P["head"][2] * 0.75
        f = smoothstep(zc - 0.03 * self.P["s"], zc + 0.02 * self.P["s"], p.z)
        return {"head": f, "neck": 1 - f} if f < 0.999 else {"head": 1.0}

    def rigid(self, b):
        return lambda p, i=0, j=0: {b: 1.0}

    # ============================================================ torso garment
    def torso_rows(self):
        P, s = self.P, self.P["s"]
        c = self.spec["coat"]
        style = c.get("style", "long")
        ease = c.get("ease", 0.016) * s
        (ca, cb), (wa, wb), (ha, hb) = P["chest"], P["waist"], P["hips"]
        zh, zw, zc, zs = P["z_hip"], P["z_waist"], P["z_chest"], P["z_sh"]
        rows = []
        flare = c.get("flare", 1.0)
        if style == "long":
            zhem = P["z_knee"] - c.get("below_knee", 0.10) * s
            for t, k in ((0.0, 1.20), (0.3, 1.14), (0.62, 1.08), (0.86, 1.03)):
                kk = 1 + (k - 1) * flare
                rows.append((lerp(zhem, zh, t), (ha + ease) * kk, (hb + ease) * (1 + (kk - 1) * 1.3), 0.015 * s))
        elif style == "mid":
            zhem = zh - 0.30 * s
            for t, k in ((0.0, 1.12), (0.45, 1.07), (0.8, 1.03)):
                kk = 1 + (k - 1) * flare
                rows.append((lerp(zhem, zh, t), (ha + ease) * kk, (hb + ease) * (1 + (kk - 1) * 1.3), 0.012 * s))
        else:  # short: hip length jacket
            zhem = zh - c.get("below_hip", 0.07) * s
            rows.append((zhem, (ha + ease) * 1.02, (hb + ease) * 1.03, 0.008 * s))
        rows.append((zh, ha + ease, hb + ease, 0.008 * s))
        rows.append((lerp(zh, zw, 0.55), lerp(ha, wa, 0.6) + ease, lerp(hb, wb, 0.6) + ease, 0.004 * s))
        rows.append((zw, wa + ease, wb + ease, 0.0))
        rows.append((lerp(zw, zc, 0.55), lerp(wa, ca, 0.7) + ease, lerp(wb, cb, 0.7) + ease, -0.004 * s))
        rows.append((zc, ca + ease, cb + ease, -0.008 * s))
        zap = zs - 0.07 * s
        rows.append((lerp(zc, zap, 0.55), ca * 0.985 + ease, cb * 0.97 + ease, -0.006 * s))
        rows.append((zap, ca * 0.95 + ease, cb * 0.9 + ease, 0.002 * s))
        self.zhem = zhem
        return rows

    def section(self, th, a, b, cy, n=2.4):
        c, sn = math.cos(th), math.sin(th)
        x = a * math.copysign(abs(c) ** (2 / n), c)
        y = b * math.copysign(abs(sn) ** (2 / n), sn)
        if y < 0:
            y *= 0.96    # flatter front
        return Vector((x, cy + y, 0))

    def thetas(self, n):
        # start at the back (+Y) so the UV seam hides behind; extra columns either side of the front centre
        out = [math.pi / 2 + TAU * j / n for j in range(n)]
        return out

    def coat_pt(self, th, z, off=0.0):
        """Point on the torso garment at angle th and height z (below the armpit), pushed out by off."""
        rows = self.rows
        if z <= rows[0][0]:
            r = rows[0]
            zz = z
            a, b, cy = r[1], r[2], r[3]
        elif z >= rows[-1][0]:
            r = rows[-1]
            a, b, cy = r[1], r[2], r[3]
        else:
            for r0, r1 in zip(rows[:-1], rows[1:]):
                if r0[0] <= z <= r1[0]:
                    t = (z - r0[0]) / (r1[0] - r0[0])
                    t = t * t * (3 - 2 * t) * 0.5 + t * 0.5
                    a, b, cy = (lerp(r0[k], r1[k], t) for k in (1, 2, 3))
                    break
        p = self.section(th, a + off, b + off, cy)
        p.z = z
        return p + self.quilt_offset(th, z)

    def quilt_offset(self, th, z):
        q = self.spec["coat"].get("quilt")
        if not q or self.lite:
            return Vector()
        pitch = q * self.P["s"]
        ph = (z - self.zhem) / pitch
        bulge = 0.011 * self.P["s"] * (math.sin(math.pi * (ph % 1.0)) ** 0.7)
        return Vector((math.cos(th), math.sin(th), 0)) * bulge

    def build_coat(self):
        P, J, s, spec = self.P, self.J, self.P["s"], self.spec["coat"]
        self.rows = rows = self.torso_rows()
        n = self.n_torso
        ths = self.thetas(n)
        G = []
        # main rows, extra rows between keys for quilting
        zlist = []
        for r0, r1 in zip(rows[:-1], rows[1:]):
            k = 2 if (spec.get("quilt") and not self.lite) else 1
            if spec.get("quilt") and not self.lite:
                k = max(2, int((r1[0] - r0[0]) / (spec["quilt"] * s / 2)))
            for i in range(k):
                zlist.append(lerp(r0[0], r1[0], i / k))
        zlist.append(rows[-1][0])
        if self.lite:
            zlist = [z for i, z in enumerate(zlist) if i % 2 == 0 or i == len(zlist) - 1]
        # hem turn-up (inner lip)
        hem_in = [self.coat_pt(th, zlist[0] + 0.03 * s, -0.012 * s) for th in ths]
        G.append(hem_in)
        for z in zlist:
            G.append([self.coat_pt(th, z) for th in ths])
        # shoulders: quadratic Bezier from the armpit ring to the neck ring
        zap = rows[-1][0]
        a_n, b_n = P["neck_r"] + 0.024 * s, P["neck_r"] + 0.02 * s
        z_n = P["z_neck"] + 0.012 * s
        tip = P["sh_x"] + 0.012 * s
        A = G[-1]
        Nr = [Vector((a_n * math.cos(th), 0.018 * s + b_n * math.sin(th), z_n)) for th in ths]
        K = []
        for p, th in zip(A, ths):
            side = abs(math.cos(th))
            kx = p.x * (tip / (rows[-1][1])) if side > 0.2 else p.x
            kx = lerp(p.x, p.x * tip / rows[-1][1], smoothstep(0.1, 0.6, side))
            K.append(Vector((kx, p.y * 1.02, P["z_sh"] + (0.03 + 0.03 * (1 - side)) * s)))
        ts = (0.3, 0.55, 0.75, 0.9, 1.0) if not self.lite else (0.45, 0.8, 1.0)
        for t in ts:
            G.append([A[j] * (1 - t) ** 2 + K[j] * 2 * t * (1 - t) + Nr[j] * t * t for j in range(n)])
        # collar
        collar = spec.get("collar", "turn")
        if collar == "turn":
            for sc, dz in (((1.03, 0.03), (1.12, 0.04), (1.36, 0.008), (1.52, -0.022)) if not self.lite else
                           ((1.1, 0.04), (1.5, -0.02))):
                G.append([Vector((q.x * sc, 0.018 * s + (q.y - 0.018 * s) * sc, q.z + dz * s)) for q in Nr])
        elif collar in ("stand", "hood"):
            for sc, dz in (((1.02, 0.035), (1.06, 0.052), (1.0, 0.048)) if not self.lite else ((1.04, 0.05),)):
                G.append([Vector((q.x * sc, 0.018 * s + (q.y - 0.018 * s) * sc, q.z + dz * s)) for q in Nr])
        detail = self.coat_detail_color()
        self.m.grid(G, "coat", lambda p, i, j: self.w_coat(p), col=detail, closed=True, uv_tile=(0.04, 0.04))
        self.coat_extras()

    def coat_detail_color(self):
        # subtle vertex shading: seams darker at the hem lip and collar underside; no lighting baked
        def f(p, i, j):
            return (0.93, 0.93, 0.93) if i == 0 else (1.0, 1.0, 1.0)
        return f

    def surface_patch(self, th0, th1, z0, z1, off0, off1, nu, nv, mat, col=(1, 1, 1), wfn=None, closed=False):
        rows = []
        for i in range(nv + 1):
            z = lerp(z0, z1, i / nv)
            off = lerp(off0, off1, i / nv)
            rows.append([self.coat_pt(lerp(th0, th1, j / nu), z, off) for j in range(nu + 1)])
        return self.m.grid(rows, mat, wfn or (lambda p, i, j: self.w_coat(p)), col=col, closed=False,
                           uv_tile=(0.04, 0.04))

    def coat_extras(self):
        P, s, spec = self.P, self.P["s"], self.spec["coat"]
        L = self.lite
        front = -math.pi / 2
        ztop = P["z_chest"] + 0.07 * s
        zbot = self.zhem + 0.005 * s
        # front placket (the closing edge), slightly proud of the surface
        if spec.get("placket", True):
            nz = 6 if L else 16
            w = 0.016 * s
            rows = []
            for i in range(nz + 1):
                z = lerp(zbot, ztop, i / nz)
                r = []
                for (dth, off) in ((-w, 0.0), (-w * 0.7, 0.004 * s), (w, 0.004 * s), (w * 1.2, 0.0)):
                    b = self.coat_pt(front, z)
                    th = front + dth / max(0.05, self.rows[0][1])
                    r.append(self.coat_pt(front + dth * 3.2, z, off))
                rows.append(r)
            self.m.grid(rows, "coat", lambda p, i, j: self.w_coat(p), col=(0.9, 0.9, 0.9), closed=False,
                        uv_tile=(0.04, 0.04))
        # buttons / toggles
        bcol = lin(spec.get("button_color", "#2a211c"))
        nb = spec.get("buttons", 5) if not L else 0
        cols = [0.0] if not spec.get("double") else [-0.2, 0.2]
        if nb:
            zb0 = lerp(zbot, P["z_hip"], 0.45) if spec.get("style") == "long" else P["z_hip"] + 0.02 * s
            zb1 = P["z_chest"] + 0.04 * s
            for k in range(nb):
                z = lerp(zb1, zb0, k / max(1, nb - 1))
                for dc in cols:
                    th = front + dc
                    p = self.coat_pt(th, z, 0.006 * s)
                    nrm = Vector((math.cos(th), math.sin(th), 0))
                    wv = self.w_coat(p)
                    if spec.get("toggles"):
                        a = p + nrm * 0.004 * s + Vector((-0.02 * s, 0, 0))
                        b = p + nrm * 0.004 * s + Vector((0.02 * s, 0, 0))
                        self.m.cyl(a, b, 0.006 * s, 0.006 * s, "body", lambda q, i, j, wv=wv: wv,
                                   seg=5 if L else 7, col=lin("#6b4a2e"))
                    else:
                        M = Matrix.Translation(p) @ Vector((0, 0, 1)).rotation_difference(nrm).to_matrix().to_4x4()
                        self.m.sphere((0, 0, 0), 0.0105 * s, "body", lambda q, i, j, wv=wv: wv, seg=5 if L else 7,
                                      rings=2, scale=(1, 1, 0.38), M=M, col=bcol)
        # pocket flaps
        if spec.get("pockets", True) and not L:
            zp = P["z_hip"] - 0.03 * s if spec.get("style") != "short" else P["z_hip"] + 0.02 * s
            for side in (-1, 1):
                thc = front + side * 0.85
                self.surface_patch(thc - 0.22, thc + 0.22, zp, zp + 0.05 * s, 0.009 * s, 0.004 * s,
                                   3 if L else 5, 1, "coat", col=(0.88, 0.88, 0.88))
        # belt
        if spec.get("belt"):
            zb = P["z_waist"] - 0.01 * s
            nu = 8 if L else 16
            rows = []
            for dz, off in ((-0.022, 0.0), (-0.02, 0.006), (0.02, 0.006), (0.022, 0.0)):
                rows.append([self.coat_pt(math.pi / 2 + TAU * j / nu, zb + dz * s, off * s) for j in range(nu)])
            self.m.grid(rows, "coat", lambda p, i, j: self.w_coat(p), col=(0.85, 0.85, 0.85), closed=True,
                        uv_tile=(0.04, 0.04))
            p = self.coat_pt(front + 0.12, zb, 0.012 * s)
            wv = self.w_coat(p)
            self.m.box(p, (0.04 * s, 0.01 * s, 0.05 * s), "body", lambda q, i, j: wv, col=lin("#8a6a3a"))
        # hood (parka): a soft bunched hood lying on the upper back
        if spec.get("collar") == "hood":
            c = Vector((0, 0.07 * s + self.P["chest"][1], self.P["z_neck"] - 0.03 * s))
            wv = {"chest": 0.8, "neck": 0.2}

            def hood_def(q):
                q = q.copy()
                if q.y < 0:
                    q.y *= 0.35
                return q
            self.m.sphere(c, 0.1 * s, "coat", lambda q, i, j: wv, seg=8 if L else 14, rings=5 if L else 8,
                          scale=(1.35, 0.75, 0.9), deform=hood_def, col=(0.92, 0.92, 0.92))
            if spec.get("fur"):
                ring = []
                for j in range(9 if L else 16):
                    a = math.pi * (0.1 + 0.8 * j / (8 if L else 15))
                    ring.append(c + Vector((math.cos(a) * 0.13 * s, -0.02 * s, 0.03 * s + math.sin(a) * 0.08 * s)))
                self.m.tube(ring, 0.022 * s, "body", lambda q, i, j: wv, seg=5 if L else 7, col=lin(spec["fur"]))

    # ============================================================ sleeves, legs, hands, feet
    def limb_path(self, names, fracs):
        out = []
        for a, b, t in fracs:
            out.append(self.J[a].lerp(self.J[b], t))
        return out

    def build_sleeves(self):
        P, s, spec = self.P, self.P["s"], self.spec["coat"]
        mat = spec.get("sleeve_mat", "coat")
        col = lin(spec["sleeve_color"]) if mat == "body" else (1, 1, 1)
        ease = spec.get("ease", 0.016) * s * 0.75
        ru = P["upper_r"] + ease
        re = P["elbow_r"] + ease
        rw = P["wrist_r"] + ease + 0.006 * s
        for side in "LR":
            k = rig.sgn(side)
            sh = self.J[f"shoulder.{side}"]
            el = self.J[f"elbow.{side}"]
            wr = self.J[f"wrist.{side}"]
            d_up = (el - sh).normalized()
            d_fo = (wr - el).normalized()
            start = sh + Vector((-k * 0.035 * s, 0, -0.02 * s))
            pts = [start, sh + d_up * 0.035 * s + Vector((-k * 0.006 * s, 0, -0.004 * s)), sh.lerp(el, 0.3),
                   sh.lerp(el, 0.7), el, el.lerp(wr, 0.4), el.lerp(wr, 0.8), wr + d_fo * 0.01 * s]
            rad = [ru * 0.7, ru * 1.02, ru, ru * 0.93, re, re * 0.98, rw * 0.97, rw]
            if self.lite:
                pts = [pts[i] for i in (0, 1, 3, 4, 6, 7)]
                rad = [rad[i] for i in (0, 1, 3, 4, 6, 7)]
            # cuff rim: fold back inside
            pts.append(wr + d_fo * 0.004 * s)
            rad.append(rw * 0.8)
            self.m.tube(pts, rad, mat, lambda p, i, j, side=side: self.w_arm(p, side), seg=self.n_limb, col=col,
                        caps=False, up=(0, -1, 0), uv_tile=(0.04, 0.04))
            # cap the start inside the shoulder
            cuff = spec.get("cuff")
            if cuff:
                c0 = wr - d_fo * 0.05 * s
                self.m.tube([c0, wr + d_fo * 0.012 * s], [rw * 1.05, rw * 1.08], "body",
                            lambda p, i, j, side=side: self.w_arm(p, side), seg=self.n_limb, col=lin(cuff), caps=False)

    def build_legs(self):
        P, s = self.P, self.P["s"]
        tro = lin(self.spec.get("trousers", "#23252b"))
        for side in "LR":
            k = rig.sgn(side)
            hp, kn, an = self.J[f"hip.{side}"], self.J[f"knee.{side}"], self.J[f"ankle.{side}"]
            top = hp + Vector((-k * 0.01 * s, 0.0, 0.08 * s))
            pts = [top, hp, hp.lerp(kn, 0.45), kn, kn.lerp(an, 0.3), kn.lerp(an, 0.75), an + Vector((0, 0, 0.012 * s))]
            rad = [P["thigh_r"] * 1.1, P["thigh_r"] * 1.08, P["thigh_r"] * 0.95, P["knee_r"] + 0.01 * s,
                   P["calf_r"] + 0.009 * s, P["ankle_r"] + 0.016 * s, P["ankle_r"] + 0.02 * s]
            if self.spec.get("tights"):
                rad = [r * 0.95 for r in rad[:4]] + [rad[4] * 0.97, P["ankle_r"] * 1.02, P["ankle_r"] * 1.05]
            if self.lite:
                pts = [pts[i] for i in (0, 2, 3, 5, 6)]
                rad = [rad[i] for i in (0, 2, 3, 5, 6)]
            self.m.tube(pts, rad, "body", lambda p, i, j, side=side: self.w_leg(p, side), seg=self.n_limb,
                        col=tro, caps=False, up=(0, -1, 0), scale=(1.0, 1.06))

    def build_feet(self):
        P, s = self.P, self.P["s"]
        spec = self.spec.get("boots", {})
        style = spec.get("style", "boot")
        col = lin(spec.get("color", "#3b2a20"))
        sole = lin(spec.get("sole", "#1a1614"))
        L = self.lite
        for side in "LR":
            k = rig.sgn(side)
            an = self.J[f"ankle.{side}"]
            lf = P["l_foot"]
            x0 = an.x + k * 0.006 * s
            yh, yt = an.y + 0.26 * lf, an.y - 0.74 * lf
            snow = style == "snow"
            wmul = 1.12 if snow else 1.0
            # rows along the foot: (y, half width, top height, toe-spring)
            prof = [(yh + 0.004, 0.026, 0.05), (yh - 0.01, 0.033, 0.08), (an.y, 0.037, an.z + 0.03 * s),
                    (lerp(an.y, yt, 0.45), 0.041, 0.07 * s + 0.012), (lerp(an.y, yt, 0.75), 0.042, 0.05 * s + 0.01),
                    (yt + 0.03 * s, 0.037, 0.042 * s + 0.008), (yt + 0.006, 0.024, 0.034 * s + 0.006), (yt, 0.01, 0.026 * s + 0.006)]
            if L:
                prof = [prof[i] for i in (0, 2, 3, 5, 7)]
            nc = 6 if L else 10
            rows = []
            for (y, hw, top) in prof:
                hw = hw * s * wmul
                top = top * (1.08 if snow else 1.0)
                ring = []
                for j in range(nc):
                    a = TAU * j / nc
                    cx, cz = math.cos(a), math.sin(a)
                    x = x0 + k * 0.004 * s + hw * math.copysign(abs(cx) ** 0.7, cx)
                    zc = top / 2
                    z = zc + (top / 2) * math.copysign(abs(cz) ** 0.6, cz)
                    z = max(z, 0.0)
                    ring.append(Vector((x, y, z)))
                rows.append(ring)

            def fcol(p, i, j):
                return sole if p.z < 0.012 * s + 0.004 else col
            self.m.grid(rows, "body", lambda p, i, j, side=side: self.w_leg(p, side), col=fcol, closed=True,
                        cap_start=True, cap_end=True)
            # shaft up the leg
            shaft_top = {"shoe": an.z + 0.045 * s, "boot": P["z_knee"] - 0.12 * s, "snow": an.z + 0.16 * s,
                         "tall": P["z_knee"] - 0.04 * s}[style]
            kn = self.J[f"knee.{side}"]
            b0 = Vector((x0, an.y + 0.004, 0.03 * s))
            b1 = an.lerp(kn, (shaft_top - an.z) / (kn.z - an.z))
            b1.x = lerp(x0, b1.x, 0.5)
            r0 = P["ankle_r"] + (0.018 if snow else 0.008) * s
            r1 = (P["ankle_r"] + 0.016 * s) if style in ("shoe", "snow") else (P["calf_r"] + 0.007 * s)
            mid = b0.lerp(b1, 0.5)
            self.m.tube([b0, an + Vector((0, 0.004, 0)), mid, b1], [r0, r0, lerp(r0, r1, 0.5) * 1.05, r1],
                        "body", lambda p, i, j, side=side: self.w_leg(p, side), seg=self.n_limb, col=col,
                        caps=False, up=(0, -1, 0))
            if snow and "cuff" in spec:
                self.m.tube([b1 - Vector((0, 0, 0.015 * s)), b1 + Vector((0, 0, 0.012 * s))], [r1 * 1.12, r1 * 1.08],
                            "body", lambda p, i, j, side=side: self.w_leg(p, side), seg=self.n_limb,
                            col=lin(spec["cuff"]))

    def hand_frame(self, side):
        k = rig.sgn(side)
        W = self.J[f"wrist.{side}"]
        d = self.rest.dir(f"hand.{side}")
        n0 = Vector((-k, 0, 0))                       # palm faces the body
        n = (n0 - d * n0.dot(d)).normalized()
        t = k * d.cross(n) * -1                        # thumb side (forward at rest)
        t = (Vector((0, -1, 0)) - d * d.y - n * n.y).normalized()
        return W, d, n, t

    def build_hands(self):
        s = self.P["s"]
        spec = self.spec
        col = lin(spec["gloves"]) if spec.get("gloves") else self.skin
        curl = spec.get("curl", 0.9)
        L = self.lite
        for side in "LR":
            W, d, n, t = self.hand_frame(side)
            lh = self.P["l_hand"]
            wv = lambda p, i, j, side=side: {f"hand.{side}": 1.0}

            def P3(a, b, c):
                return W + d * a + n * b + t * c
            rows = []
            nc = 5 if L else 8
            prof = [(0.0, 0.03, 0.022), (0.2, 0.038, 0.024), (0.45, 0.045, 0.024), (0.52, 0.045, 0.022)]
            fing = [(0.1, 0.043, 0.02), (0.35, 0.041, 0.019), (0.62, 0.039, 0.018), (0.85, 0.035, 0.016), (1.0, 0.02, 0.01)]
            if L:
                prof = [prof[0], prof[2]]
                fing = [fing[1], fing[3], fing[4]]
            kn = 0.52 * lh
            fl = 0.48 * lh
            for (a, w, th) in prof:
                rows.append([P3(a * lh, th * s * 0.55 * math.sin(TAU * j / nc), w * s * math.cos(TAU * j / nc))
                             for j in range(nc)])
            # fingers: an arc curling toward the palm
            for (f, w, th) in fing:
                ang = curl * f * 1.3
                # centreline of a circular arc of length fl*f bending toward +n
                if curl > 1e-3:
                    R = fl / (curl * 1.3)
                    ca = kn + R * math.sin(ang)
                    cb = R * (1 - math.cos(ang))
                else:
                    ca, cb = kn + fl * f, 0.0
                dd = d * math.cos(ang) + n * math.sin(ang)
                nn = n * math.cos(ang) - d * math.sin(ang)
                cen = W + d * ca + n * cb
                rows.append([cen + nn * th * s * 0.55 * math.sin(TAU * j / nc) + t * w * s * math.cos(TAU * j / nc)
                             for j in range(nc)])
            # the hand frame is mirrored for the right hand, which turns the winding inside out: flip it back
            self.m.grid(rows, "body", wv, col=col, closed=True, cap_start=False, cap_end=True, flip=side == "R")
            # thumb
            th_pts = [P3(0.1 * lh, 0.004 * s, 0.024 * s), P3(0.28 * lh, 0.012 * s, 0.042 * s),
                      P3(0.44 * lh, 0.026 * s, 0.047 * s), P3(0.55 * lh, (0.036 + curl * 0.01) * s, 0.038 * s)]
            if L:
                th_pts = [th_pts[0], th_pts[2], th_pts[3]]
            self.m.tube(th_pts, [0.012 * s, 0.011 * s, 0.008 * s][:len(th_pts)] if L else
                        [0.012 * s, 0.012 * s, 0.01 * s, 0.008 * s], "body", wv, seg=4 if L else 6, col=col)

    # ============================================================ head
    def head_pt(self, az, el, off=0.0):
        """Point on the (deformed) head at azimuth az (0 = +X, -90deg = front) and elevation el."""
        rx, ry, rz = self.P["head"]
        c = math.cos(el)
        p = Vector((c * math.cos(az) * rx, c * math.sin(az) * ry, math.sin(el) * rz))
        p = self.head_deform(p)
        if off:
            nrm = Vector((p.x / rx ** 2, p.y / ry ** 2, p.z / rz ** 2)).normalized()
            p = p + nrm * off
        return self.C + p

    def face_col(self):
        """Vertex colour for the head of a close-up figure (spec face_detail): warm cold-flushed cheeks and a
        slightly darker jaw shadow under the cheekbones, painted on the skin so no lighting is baked."""
        rx, ry, rz = self.P["head"]
        C, sk = self.C, self.skin
        fwd = -math.pi / 2

        def col(p, i, j):
            q = p - C
            az = math.atan2(q.y / ry, q.x / rx)
            el = math.asin(max(-1.0, min(1.0, q.z / rz)))
            c = list(sk)
            for k in (-1, 1):
                d2 = ((az - (fwd + k * 0.62)) / 0.34) ** 2 + ((el - math.radians(-14)) / 0.3) ** 2
                g = 0.95 * math.exp(-d2)
                tint = (1.04, 0.79, 0.73)
                c = [c[n] * (1 + (tint[n] - 1) * g) for n in range(3)]
            # a soft shadow under the cheekbones toward the jaw, the back of the head unchanged
            dfront = abs(((az - fwd + math.pi) % TAU) - math.pi)
            if dfront < 1.3 and -0.9 < el < -0.35:
                g = 0.12 * (1 - dfront / 1.3)
                c = [c[n] * (1 - g) for n in range(3)]
            return tuple(c)
        return col

    def head_deform(self, p):
        rx, ry, rz = self.P["head"]
        q = p.copy()
        zr = q.z / rz
        if zr < 0:
            low = (-zr) ** 1.4
            q.x *= 1 - 0.26 * low
            if q.y > 0:
                q.y *= 1 - 0.42 * low
            else:
                q.y *= 1 - 0.06 * low
        else:
            if q.y > 0:
                q.y *= 1 + 0.05 * (1 - zr)
        if q.y < 0:
            # flatten the face plane a little
            fy = -q.y / ry
            if fy > 0.8:
                q.y = -ry * (0.8 + (fy - 0.8) * 0.55)
        return q

    def build_head(self):
        P, s, C = self.P, self.P["s"], self.C
        L = self.lite
        seg, rings = self.n_head
        rx, ry, rz = P["head"]
        wv = lambda p, i, j: self.w_head(p)
        rows = []
        for i in range(rings + 1):
            el = -math.pi / 2 + math.pi * i / rings
            el = max(min(el, math.pi / 2 - 0.02), -math.pi / 2 + 0.02)
            rows.append([self.head_pt(math.pi / 2 + TAU * j / seg, el) for j in range(seg)])
        self.m.grid(rows, "body", wv, col=self.face_col() if self.spec.get("face_detail") else self.skin,
                    closed=True, cap_start=True, cap_end=True)
        # neck
        nb = Vector((0, 0.02 * s, P["z_neck"] - 0.03 * s))
        nt = C + Vector((0, 0.012 * s, -rz * 0.5))
        self.m.tube([nb, nb.lerp(nt, 0.5), nt], [P["neck_r"], P["neck_r"] * 0.95, P["neck_r"] * 0.92], "body",
                    lambda p, i, j: {"neck": 0.7, "chest": 0.3} if i == 0 else self.w_head(p), seg=self.n_limb,
                    col=self.skin, caps=False)
        # nose: a small faceted wedge
        f = -math.pi / 2
        br = self.head_pt(f, math.radians(8))
        tip = self.head_pt(f, math.radians(-22), 0.02 * s)
        base = self.head_pt(f, math.radians(-30), 0.006 * s)
        wl = self.head_pt(f - 0.2, math.radians(-26), 0.001)
        wr = self.head_pt(f + 0.2, math.radians(-26), 0.001)
        if self.spec.get("face_detail"):
            # cold-reddened tip, shaded underside and wings: the nose reads as a form, not a flat wedge
            sk = self.skin
            ncol = [sk, (sk[0] * 1.0, sk[1] * 0.84, sk[2] * 0.8), mul(sk, 0.62), mul(sk, 0.8), mul(sk, 0.8)]
        else:
            ncol = [mul(self.skin, 1.0)] * 5
        ids = [self.m.vert(q, c, {"head": 1.0}) for q, c in zip((br, tip, base, wl, wr), ncol)]
        for tri in ((0, 3, 1), (0, 1, 4), (3, 2, 1), (1, 2, 4)):
            self.m.face([ids[x] for x in tri], [(0, 0)] * 3, "body", smooth=False)
        # ears
        for k in (() if L else (-1, 1)):
            e = self.head_pt(math.pi if k < 0 else 0.0, math.radians(-8), -0.004 * s)
            e.y += 0.008 * s
            M = Matrix.Translation(e) @ Matrix.Rotation(k * 0.25, 4, "Z") @ Matrix.Rotation(-0.15, 4, "X")
            self.m.sphere((0, 0, 0), 1.0, "body", wv, seg=5 if L else 6, rings=3 if L else 4,
                          scale=(0.012 * s, 0.022 * s, 0.03 * s), M=M, col=mul(self.skin, 0.95))
        # eyes, brows, mouth
        if not L:
            eyec = lin(self.spec.get("eye_color", "#2a1d17"))
            fd = self.spec.get("face_detail")
            for k in (-1, 1):
                if fd:
                    # eye socket: a shallow lens of shaded skin around the eye, so the eye sits in a hollow
                    sc = self.head_pt(f + k * 0.42, math.radians(3), -0.0035 * s)
                    M = Matrix.Translation(sc) @ Matrix.Rotation(-k * 0.42, 4, "Z")
                    self.m.sphere((0, 0, 0), 1.0, "body", wv, seg=7, rings=3, M=M,
                                  scale=(0.0165 * s, 0.006 * s, 0.0125 * s),
                                  col=(self.skin[0] * 0.8, self.skin[1] * 0.7, self.skin[2] * 0.7))
                e = self.head_pt(f + k * 0.42, math.radians(2), (0.0005 if fd else -0.002) * s)
                self.m.sphere(e, 0.0075 * s, "body", wv, seg=6, rings=3, scale=(1.25, 0.6, 0.8), col=eyec)
                b = self.head_pt(f + k * 0.42, math.radians(15 if fd else 14), (0.0025 if fd else 0.001) * s)
                M = Matrix.Translation(b) @ Matrix.Rotation(-k * 0.42, 4, "Z") @ Matrix.Rotation(k * (0.03 if fd else 0.12), 4, "Y")
                bald = self.spec.get("hair") == "bald"
                self.m.box((0, 0, 0), ((0.029 if fd else 0.026) * s, 0.007 * s, (0.0065 if fd else 0.005) * s), "body", wv,
                           M=M, col=mul(self.hair, (0.6 if fd else 0.85) if not bald else (1.0 if fd else 1.4)))
            mth = self.head_pt(f, math.radians(-44), -0.001 * s)
            self.m.box(mth, (0.026 * s, 0.006 * s, 0.0045 * s), "body", wv,
                       col=lin(self.spec.get("lip", "#9b5a52")))
        if self.spec.get("glasses") and not L:
            gc = lin("#1c1a18")
            for k in (-1, 1):
                e = self.head_pt(f + k * 0.42, math.radians(2), 0.014 * s)
                M = Matrix.Translation(e) @ Matrix.Rotation(math.pi / 2, 4, "X")
                ring = [M @ Vector((math.cos(TAU * j / 8) * 0.017 * s, math.sin(TAU * j / 8) * 0.014 * s, 0))
                        for j in range(9)]
                self.m.tube(ring, 0.0022 * s, "body", wv, seg=3, col=gc, caps=False)
                ear = self.head_pt(math.pi if k < 0 else 0.0, math.radians(4), 0.004 * s)
                self.m.tube([ring[0 if k > 0 else 5], ear], 0.0018 * s, "body", wv, seg=3, col=gc)
            self.m.tube([self.head_pt(f - 0.2, math.radians(4), 0.016 * s), self.head_pt(f + 0.2, math.radians(4), 0.016 * s)],
                        0.002 * s, "body", wv, seg=3, col=gc)
        if self.spec.get("beard"):
            self.build_beard()
        self.build_hair()

    def build_beard(self):
        s = self.P["s"]
        rows = []
        n = 6 if self.lite else 10
        for i, t in enumerate((0.0, 0.3, 0.6, 1.0)):
            r = []
            for j in range(n + 1):
                u = j / n
                az = -math.pi / 2 + math.radians(-85 + 170 * u)
                side = abs(u - 0.5) * 2               # 0 at the chin, 1 at the ears
                top = lerp(-50, -8, side ** 1.5)      # leaves the mouth free, climbs to sideburns
                el = lerp(-82, top, t)
                off = (0.004 + 0.009 * (1 - t) * (1 - 0.5 * side)) * s if 0 < t < 1 else 0.002 * s
                r.append(self.head_pt(az, math.radians(el), off))
            rows.append(r)
        bc = mul(self.hair, 1.25)
        self.m.grid(rows, "body", lambda p, i, j: self.w_head(p), col=bc, closed=False)
        mo = self.head_pt(-math.pi / 2, math.radians(-36), 0.004 * s)
        self.m.sphere(mo, 0.02 * s, "body", lambda p, i, j: {"head": 1.0}, seg=8, rings=4, scale=(1.3, 0.35, 0.3),
                      col=bc)

    def build_hair(self):
        style = self.spec.get("hair", "short")
        s = self.P["s"]
        n = 9 if self.lite else 16
        col = self.hair

        def el_min(az, front, side, back):
            u = math.sin(az)       # -1 front, +1 back
            if u < 0:
                return math.radians(lerp(side, front, -u))
            return math.radians(lerp(side, back, u))
        prm = {"short": (30, 4, -32, 0.008), "bald": (30, 4, -30, 0.005), "bob": (22, -32, -45, 0.014),
               "long": (24, -32, -48, 0.014), "bun": (30, 0, -30, 0.01), "kid": (26, 0, -30, 0.01),
               "pigtails": (24, -8, -30, 0.01)}[style]
        fr, sd, bk, thick = prm
        ats = [math.pi / 2 + TAU * j / n for j in range(n)]
        nr = 3 if self.lite else 6
        rows = []
        for i in range(nr + 1):
            t = i / nr
            r = []
            for az in ats:
                e0 = el_min(az, fr, sd, bk)
                el = lerp(e0, math.radians(86), t ** 0.9)
                off = (0.002 if i == 0 else thick * (0.75 + 0.4 * t)) * s
                r.append(self.head_pt(az, el, off))
            rows.append(r)
        if style == "bald":
            # only a fringe of hair round the back and sides
            rows = rows[:3]
        if style in ("long", "bob"):
            drop = 0.2 if style == "long" else 0.035
            ext = []
            for k, dz in enumerate((0.3, 0.65, 1.0) if not self.lite else (0.6, 1.0)):
                r = []
                for q, az in zip(rows[0], ats):
                    u = max(0.0, (math.sin(az) + 0.35) / 1.35)       # 0 at the face, 1 at the back
                    out = Vector((q.x - self.C.x, q.y - self.C.y, 0)).normalized() * (0.012 + 0.012 * dz) * s
                    r.append(q + out * u + Vector((0, 0.02 * s * u * dz, -drop * s * dz * u ** 0.7)))
                ext.append(r)
            rows = list(reversed(ext)) + rows
        wv = (lambda p, i, j: self.w_head(p)) if style != "long" else \
            (lambda p, i, j: self.w_head(p) if p.z > self.P["z_neck"] + 0.03 * s else {"head": 0.4, "neck": 0.3, "chest": 0.3})
        self.m.grid(rows, "body", wv, col=col, closed=True, cap_end=True)
        if style == "bun":
            b = self.head_pt(math.pi / 2, math.radians(20), 0.03 * s)
            self.m.sphere(b, 0.035 * s, "body", lambda p, i, j: {"head": 1.0}, seg=8, rings=5, col=col)
        if style == "pigtails":
            for k in (-1, 1):
                a = self.head_pt(math.pi if k < 0 else 0.0, math.radians(-10), 0.012 * s)
                a.y += 0.025 * s
                pts = [a, a + Vector((k * 0.02 * s, 0.01 * s, -0.06 * s)), a + Vector((k * 0.025 * s, 0.015 * s, -0.13 * s)),
                       a + Vector((k * 0.024 * s, 0.018 * s, -0.17 * s))]
                self.m.tube(pts, [0.02 * s, 0.018 * s, 0.014 * s, 0.006 * s], "body",
                            lambda p, i, j: {"head": 0.6, "neck": 0.4}, seg=5 if self.lite else 7, col=col)

    # ============================================================ hats
    def hat_line(self, az):
        u = math.sin(az)
        return math.radians(12 - 14 * u + 2 * u * u)

    def build_hat(self):
        spec = self.spec.get("hat")
        if not spec:
            return
        style = spec["style"]
        s = self.P["s"]
        L = self.lite
        n = 9 if L else 16
        ats = [math.pi / 2 + TAU * j / n for j in range(n)]
        wv = lambda p, i, j: {"head": 1.0}
        getattr(self, "hat_" + style)(spec, s, n, ats, wv)

    def dome(self, ats, prof, extra=None, lift=0.0):
        """prof: [(t, off)] with t 0 = hat line, 1 = crown."""
        rows = []
        for t, off in prof:
            r = []
            for az in ats:
                el = lerp(self.hat_line(az) + lift, math.radians(88), t)
                q = self.head_pt(az, el, off)
                if extra:
                    q = extra(q, az, t)
                r.append(q)
            rows.append(r)
        return rows

    def hat_beanie(self, spec, s, n, ats, wv, pompom=None):
        pompom = spec.get("pompom") if pompom is None else pompom
        rib = spec.get("brim", True)
        prof = [(-0.05, 0.004 * s)]
        if rib:
            prof += [(-0.04, 0.02 * s), (0.2, 0.021 * s), (0.22, 0.012 * s)]
        else:
            prof += [(-0.03, 0.012 * s)]
        tops = (0.45, 0.7, 0.88, 1.0) if not self.lite else (0.6, 1.0)
        # knit sits loose over the crown: the gap to the scalp grows toward the top and the crown is a little
        # gathered and slouched back, so the hat reads as wool rather than a smooth helmet shell
        slouch = spec.get("slouch", 0.0 if pompom else 0.35)
        for t in tops:
            loose = 0.012 + 0.012 * math.sin(math.pi * min(t, 0.9) / 0.9 * 0.5) + 0.02 * slouch * t
            prof.append((t, loose * s))

        def extra(q, az, t):
            if slouch and t > 0.3:
                q = q + Vector((0, 0.03 * s * slouch * (t - 0.3), 0.01 * s * slouch * t))
            if t > 0.0:
                # soft irregular folds of the knit (about 3 mm), fading out at the cuff
                q = q + (q - self.C).normalized() * (0.003 * s * t * math.sin(3 * az + 1.3) * math.cos(2 * az))
            return q
        rows = self.dome(ats, prof, extra)
        col = lambda p, i, j: (0.86, 0.86, 0.86) if (rib and 1 <= i <= 3) else (1, 1, 1)
        self.m.grid(rows, "hat", wv, col=col, closed=True, cap_end=True, uv_tile=(0.05, 0.05))
        top = sum(rows[-1], Vector()) / len(rows[-1])
        if pompom:
            r = 0.042 * s

            def lump(q):
                return q * (1 + 0.12 * math.sin(q.x * 190) * math.sin(q.y * 170) * math.sin(q.z * 150))
            self.m.sphere(top + Vector((0, 0.004 * s, r * 0.8)), r, "hat", wv, seg=6 if self.lite else 10,
                          rings=4 if self.lite else 7, deform=lump, col=(1.05, 1.05, 1.05) if pompom is True else lin(pompom))
        return rows

    def hat_bobble(self, spec, s, n, ats, wv):
        return self.hat_beanie(spec, s, n, ats, wv, pompom=spec.get("pompom", True))

    def hat_earflap(self, spec, s, n, ats, wv):
        self.hat_beanie(dict(spec, brim=False), s, n, ats, wv, pompom=True)
        for k in (-1, 1):
            azc = 0.0 if k > 0 else math.pi
            rows = []
            for el in (self.hat_line(azc) - 0.02, math.radians(-18), math.radians(-42)):
                r = [self.head_pt(azc + math.radians(a), el, 0.014 * s) for a in (-34, -17, 0, 17, 34)]
                rows.append(r)
            rows[-1] = [rows[-1][2]] * 5
            self.m.grid(rows, "hat", wv, col=(0.92, 0.92, 0.92), closed=False)
            tip = rows[-1][0]
            end = tip + Vector((0, -0.01 * s, -0.09 * s))
            self.m.tube([tip, end], 0.004 * s, "hat", wv, seg=4)
            self.m.sphere(end, 0.013 * s, "hat", wv, seg=6, rings=4)

    def hat_flatcap(self, spec, s, n, ats, wv):
        C = self.C

        def extra(q, az, t):
            top = C.z + self.P["head"][2] * 0.78
            if q.z > top - 0.03 * s:
                q.z = top - 0.03 * s + (q.z - top + 0.03 * s) * 0.45
            q.y -= 0.03 * s * smoothstep(0.15, 1.0, t)
            q.x = C.x + (q.x - C.x) * (1 + 0.09 * t)
            return q
        prof = [(-0.04, 0.004 * s), (-0.03, 0.012 * s), (0.25, 0.015 * s), (0.55, 0.018 * s), (0.8, 0.017 * s), (1.0, 0.016 * s)]
        if self.lite:
            prof = [prof[0], prof[1], prof[3], prof[5]]
        rows = self.dome(ats, prof, extra)
        self.m.grid(rows, "hat", wv, closed=True, cap_end=True, uv_tile=(0.04, 0.04))
        self.brim_front(s, 0.068, 0.013, -0.018, wv, spec)

    def brim_front(self, s, depth, off, drop, wv, spec, span=62):
        nb = 6 if self.lite else 10
        inner, outer = [], []
        for j in range(nb + 1):
            az = -math.pi / 2 + math.radians(-span + 2 * span * j / nb)
            el = self.hat_line(az) - 0.03
            p = self.head_pt(az, el, off * s)
            f = math.cos(math.radians(-span + 2 * span * j / nb) * 1.25)
            dirv = Vector((p.x - self.C.x, p.y - self.C.y, 0)).normalized()
            inner.append(p)
            outer.append(p + dirv * depth * s * max(f, 0.15) + Vector((0, 0, drop * s * max(f, 0))))
        mid = [a.lerp(b, 0.55) + Vector((0, 0, 0.004 * s)) for a, b in zip(inner, outer)]
        self.m.grid([inner, mid, outer], "hat", wv, col=(0.94, 0.94, 0.94), closed=False)

    def hat_trilby(self, spec, s, n, ats, wv):
        C = self.C
        rx, ry, rz = self.P["head"]
        zb = C.z + rz * 0.34
        tilt = spec.get("tilt", 0.08)           # + tips the front brim down; the Bier vendor's is pushed back
        base = []
        for az in ats:
            base.append(Vector((math.cos(az) * (rx + 0.014 * s), math.sin(az) * (ry + 0.014 * s), 0)))

        def place(v, dz):
            q = Vector((v.x, v.y, dz))
            q = Matrix.Rotation(tilt, 3, "X") @ q
            return C + Vector((0, 0.004 * s, zb - C.z)) + q
        ch = spec.get("crown", 0.105) * s
        taper = spec.get("taper", 1.0)          # > 1 narrows the crown toward the top (a Tyrolean hat)
        pinch = spec.get("pinch", 0.0)          # front pinch: the crown's front sides pressed in near the top
        rows = []
        for sc, dz in ((1.0, -0.004 * s), (1.0, 0.0), (1 - 0.02 * taper, ch * 0.5), (1 - 0.08 * taper, ch * 0.95),
                       (1 - 0.14 * taper, ch)):
            t = max(dz, 0.0) / ch
            rows.append([place(Vector((v.x * sc * (1 - pinch * t * t * max(0.0, -math.sin(a)) * abs(math.cos(a)) * 2.2),
                                       v.y * sc, 0)), dz) for v, a in zip(base, ats)])
        # pinched top with a centre dent
        rows.append([place(Vector((v.x * (0.55 - 0.1 * pinch * max(0.0, -math.sin(a))), v.y * 0.62, 0)),
                           ch * 0.92 - 0.012 * s * abs(math.sin(a))) for v, a in zip(base, ats)])
        self.m.grid(rows, "hat", wv, closed=True, uv_tile=(0.05, 0.05))
        cen = place(Vector(), ch * 0.8)
        ring = self.m.V[-len(base):]
        ids = list(range(len(self.m.V) - len(base), len(self.m.V)))
        ci = self.m.vert(cen, (1, 1, 1), {"head": 1.0})
        for j in range(len(ids)):
            self.m.face([ids[j], ids[(j + 1) % len(ids)], ci], [(0, 0)] * 3, "hat")
        # brim
        bw = spec.get("brim_w", 0.055) * s
        brim = []
        for sc_in, up in ((1.0, 0.0), (1.0, 0.0)):
            pass
        r_in = [place(v, 0.0) for v in base]
        r_mid = []
        r_out = []
        for v, az in zip(base, ats):
            dv = Vector((v.x, v.y, 0)).normalized()
            side = abs(math.cos(az))
            curl = spec.get("curl", 0.014) * s * side ** 2
            # back_up: the brim turned up at the back and dipped at the front, as on a Bavarian felt hat
            back = math.sin(az)
            bu = spec.get("back_up", 0.0) * s
            lift = bu * max(back, 0.0) ** 2 - 0.35 * bu * max(-back, 0.0) ** 2
            r_mid.append(place(v + dv * bw * 0.5, 0.002 * s + curl * 0.3 + lift * 0.3))
            r_out.append(place(v + dv * bw * (1 - 0.15 * side), curl - 0.004 * s * (1 - side) + lift))
        self.m.grid([r_in, r_mid, r_out], "hat", wv, col=(0.95, 0.95, 0.95), closed=True, uv_tile=(0.05, 0.05))
        # band
        band = lin(spec.get("band", "#1b1714"))
        self.m.grid([[place(v * 1.01 + Vector((v.x, v.y, 0)).normalized() * 0.002 * s, dz) for v in base]
                     for dz in (0.001 * s, 0.026 * s)], "body", wv, col=band, closed=True)
        if spec.get("brush"):
            # a Gamsbart-style brush tucked in the band at the back left: a fan of thin tufts, pale at the tips
            root = place(Vector((-(rx + 0.016 * s) * 0.82, (ry + 0.014 * s) * 0.58, 0)), 0.014 * s)
            nt = 5 if self.lite else 9
            for k in range(nt):
                f = (k / (nt - 1)) - 0.5
                ang = TAU * k / nt * 2.0                     # two turns of a cone: a bushy brush, not a fan
                cone = 0.15 + 0.3 * abs(f) * 2
                d = Vector((-0.15 + cone * math.cos(ang), 0.2 + cone * math.sin(ang), 1.0)).normalized()
                ln = (0.075 - 0.02 * abs(f) * 2) * s
                mid = root + d * ln * 0.55
                tip = root + d * ln
                self.m.tube([root, mid, tip], [0.0025 * s, 0.0055 * s, 0.0035 * s], "body", wv, seg=3,
                            col=lin(spec["brush"]), caps=False)
            # the brush's clasp
            self.m.sphere(root + Vector((0, 0, 0.004 * s)), 0.007 * s, "body", wv, seg=6, rings=4,
                          col=lin(spec.get("clasp", "#b8a068")))
        elif spec.get("feather"):
            p = place(base[n // 4 * 3 if n >= 4 else 0] * 1.02, 0.02 * s)
            p = place(Vector((-(rx + 0.02 * s), 0.02 * s, 0)), 0.018 * s)
            self.m.sphere(p + Vector((0, 0.02 * s, 0.03 * s)), 1.0, "body", wv, seg=6, rings=4,
                          scale=(0.006 * s, 0.035 * s, 0.012 * s),
                          M=Matrix.Translation(Vector()) , col=lin(spec["feather"]))

    def hat_beret(self, spec, s, n, ats, wv):
        C = self.C
        rx, ry, rz = self.P["head"]
        M = Matrix.Translation(C + Vector((0.012 * s, 0.01 * s, rz * 0.55))) @ Matrix.Rotation(-0.28, 4, "Y") @ \
            Matrix.Rotation(-0.12, 4, "X")

        def flat(q):
            q = q.copy()
            if q.z < 0:
                q.z *= 0.35
            return q
        self.m.sphere((0, 0, 0), 1.0, "hat", wv, seg=10 if self.lite else 16, rings=5 if self.lite else 8,
                      scale=(rx * 1.55, ry * 1.4, 0.05 * s), M=M, deform=flat)
        self.m.cyl(M @ Vector((0, 0, 0.045 * s)), M @ Vector((0, 0, 0.06 * s)), 0.004 * s, 0.003 * s, "hat", wv, seg=5)
        # headband ring where it grips the head
        rows = self.dome(ats, [(-0.02, 0.004 * s), (0.05, 0.01 * s), (0.25, 0.012 * s)])
        self.m.grid(rows, "hat", wv, closed=True)

    # ============================================================ scarf
    def build_scarf(self):
        spec = self.spec.get("scarf")
        if not spec:
            return
        s, P = self.P["s"], self.P
        L = self.lite
        style = spec.get("style", "wrap")
        stripes = spec.get("stripes")
        zn = P["z_neck"]
        nl = 10 if L else 16
        seg = 4 if L else 6
        wv_loop = lambda p, i, j: {"neck": 0.35, "chest": 0.65}
        bulk = spec.get("bulk", 1.0)

        def stripe_col(k):
            if not stripes:
                return (1, 1, 1)
            return (1, 1, 1) if (k // stripes[0]) % 2 == 0 else mul((1, 1, 1), stripes[1])
        # loops around the neck: centreline ellipses, front dipping lower
        loops = ((0.005, 1.0, 0.0), (0.042, 0.93, 0.6)) if not L else ((0.02, 1.02, 0.0),)
        for li, (dz, rr, th) in enumerate(loops if style != "neckerchief" else ((0.0, 0.95, 0.0),)):
            pts = []
            for k in range(nl + 1):
                a = TAU * k / nl + math.pi / 2
                front = max(0.0, -math.sin(a))
                pts.append(Vector((math.cos(a) * (P["neck_r"] + 0.03 * s * bulk) * rr * 1.05,
                                   0.018 * s + math.sin(a) * (P["neck_r"] + 0.032 * s * bulk) * rr,
                                   zn + (dz - 0.02 * front - 0.004 * math.sin(3 * a + th)) * s)))
            r = 0.022 * s * bulk if style != "neckerchief" else 0.014 * s
            self.m.tube(pts, r, "scarf", wv_loop, seg=seg, col=lambda p, i, j: stripe_col(i // 2),
                        caps=False, scale=(1.0, 1.25), uv_tile=(0.056, 0.056))
        if style in ("wrap", "long"):
            ends = [(-1, 0.34, 0.0), (1, 0.27, 0.025)] if style == "wrap" else [(-1, 0.42, 0.0)]
            for k, length, dy in ends:
                x = k * 0.045 * s
                top = Vector((x, -(P["neck_r"] + 0.03 * s) + 0.01 * s, zn - 0.005 * s))
                pts = [top]
                nseg = 4 if L else 9
                for i in range(1, nseg + 1):
                    z = zn - 0.02 * s - length * s * i / nseg
                    th = -math.pi / 2 + k * 0.28
                    q = self.coat_pt(th, max(z, self.rows[0][0]), (0.016 + 0.004 * i / nseg + dy) * s)
                    q.x = x + k * 0.01 * s * i / nseg
                    pts.append(q)
                wv = lambda p, i, j: {"chest": 1.0} if p.z > self.P["z_chest"] - 0.05 * s else self.w_coat(p)
                self.m.tube(pts, 0.06 * s * bulk, "scarf", wv, seg=4, scale=(1.0, 0.16),
                            col=lambda p, i, j: stripe_col(i), twist=lambda i: math.pi / 4, up=(0, 1, 0),
                            uv_tile=(0.056, 0.056))
                # fringe
                if spec.get("fringe", True) and not L:
                    e = pts[-1]
                    for f in range(4):
                        fx = e.x + (f - 1.5) * 0.024 * s
                        self.m.box(Vector((fx, e.y - 0.002 * s, e.z - 0.02 * s)), (0.006 * s, 0.004 * s, 0.035 * s),
                                   "scarf", wv)
        if style == "long":
            # one end thrown back over the shoulder
            pts = []
            for i in range(7 if not L else 4):
                t = i / (6 if not L else 3)
                a = math.pi * (0.1 + 0.55 * t)
                pts.append(Vector((0.1 * s * math.cos(a) + 0.02 * s, 0.03 * s + 0.12 * s * math.sin(a) ** 0.8,
                                   zn - 0.01 * s - 0.25 * s * t ** 2)))
            self.m.tube(pts, 0.055 * s * bulk, "scarf", lambda p, i, j: {"chest": 1.0}, seg=4, scale=(1.0, 0.18),
                        col=lambda p, i, j: stripe_col(i), twist=lambda i: math.pi / 4, up=(0, 0, 1))
        if style == "neckerchief":
            tip = Vector((0, -(P["neck_r"] + 0.04 * s), zn - 0.07 * s))
            a = Vector((-0.05 * s, -(P["neck_r"] + 0.02 * s), zn + 0.0))
            b = Vector((0.05 * s, -(P["neck_r"] + 0.02 * s), zn + 0.0))
            ids = [self.m.vert(q, (1, 1, 1), {"chest": 1.0}) for q in (a, tip, b)]
            self.m.face(ids, [(0, 0), (0.5, 1), (1, 0)], "scarf")

    # ============================================================ extras
    def build_apron(self):
        spec = self.spec.get("apron")
        if not spec:
            return
        s, P = self.P["s"], self.P
        col = lin(spec["color"])
        front = -math.pi / 2
        nu = 4 if self.lite else 8
        z0, z1 = self.zhem, P["z_chest"] + 0.1 * s
        rows = []
        zs = [lerp(z0, z1, t) for t in ((0, 0.25, 0.5, 0.75, 1.0) if not self.lite else (0, 0.5, 1.0))]
        for z in zs:
            half = 0.55 if z < P["z_waist"] + 0.02 * s else 0.33
            rows.append([self.coat_pt(front + lerp(-half, half, j / nu), z, 0.008 * s) for j in range(nu + 1)])
        # skirt of the apron below the jacket hem, hanging to the knee
        hem = rows[0]
        low = []
        for k, dz in enumerate((0.15, 0.3, 0.45 if spec.get("long") else 0.36)):
            low.append([q + Vector((0, -0.01 * s * (k + 1), -dz * s)) for q in hem])
        rows = list(reversed(low)) + rows
        self.m.grid(rows, "body", lambda p, i, j: self.w_coat(p), col=lambda p, i, j: col if not spec.get("stripe") or (j % 2 == 0) else mul(col, 0.8),
                    closed=False)

    def build_bag(self):
        spec = self.spec.get("bag")
        if not spec:
            return
        s, P = self.P["s"], self.P
        col = lin(spec)
        pts = []
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            th = lerp(math.pi / 2 - 0.2, -math.pi / 2 - 0.6, t) if False else None
            z = lerp(P["z_sh"] + 0.04 * s, P["z_hip"] + 0.06 * s, t)
            x = lerp(0.12 * s, -0.16 * s, t)
            q = Vector((x, 0, z))
            th = math.atan2(-1.0, x / 0.2)
            p = self.coat_pt(th, min(z, self.rows[-1][0]), 0.01 * s) if z < self.rows[-1][0] else \
                Vector((0.13 * s, -0.02 * s, P["z_sh"] + 0.05 * s))
            pts.append(p)
        self.m.tube(pts, 0.006 * s, "body", lambda p, i, j: self.w_coat(p), seg=4, col=col, scale=(2.2, 0.6))
        c = self.coat_pt(math.radians(-150), P["z_hip"] + 0.0 * s, 0.045 * s)
        wv = self.w_coat(c)
        M = Matrix.Translation(c) @ Matrix.Rotation(math.radians(-60), 4, "Z")
        self.m.box((0, 0, 0), (0.22 * s, 0.07 * s, 0.17 * s), "body", lambda p, i, j: wv, M=M, col=col)
        self.m.box((0, -0.036 * s, 0.03 * s), (0.2 * s, 0.01 * s, 0.1 * s), "body", lambda p, i, j: wv, M=M,
                   col=mul(col, 0.8))

    def build_mug(self):
        W, d, n, t = self.hand_frame("R")
        k = self.mug_k
        c = self.mug_center
        axis = self.mug_axis      # the thumb side; upright when the forearm is level
        r, h = 0.037 * k, 0.095 * k
        seg = 6 if self.lite else 10
        wv = lambda p, i, j: {"mug": 1.0}
        body = lin(self.spec.get("mug_color", "#8e1b1f"))
        white = lin("#efe6d8")
        a = c - axis * h / 2
        b = c + axis * h / 2
        # outer wall with a white rim band, inner wall and wine surface
        up = n
        x = n.normalized()
        y = axis.cross(x).normalized()
        rows = []
        prof = [(0.0, r * 0.9), (0.06, r), (0.7, r * 1.02), (0.86, r * 1.04), (1.0, r * 1.05), (1.0, r * 0.93), (0.9, r * 0.9)]
        for f, rr in prof:
            cen = a + axis * h * f
            rows.append([cen + (x * math.cos(TAU * j / seg) + y * math.sin(TAU * j / seg)) * rr for j in range(seg)])
        col = lambda p, i, j: white if i in (3, 4) else (lin("#3a0a0e") if i >= 5 else body)
        self.mug.grid(rows, "mug", wv, col=col, closed=True, cap_start=True, cap_end=True)
        # the handle, on the hand side (-n)
        hp = []
        for j in range(6 if not self.lite else 4):
            ang = math.pi * j / (5 if not self.lite else 3)
            hp.append(c - x * (r + 0.004) + axis * (math.cos(ang) * h * 0.3) - x * math.sin(ang) * 0.028 * k)
        self.mug.tube(hp, 0.0065 * k, "mug", wv, seg=4 if self.lite else 5, col=body)

    # ============================================================ all
    def build(self):
        self.parts = {}
        for name in ("coat", "sleeves", "legs", "feet", "hands", "head", "hat", "scarf", "apron", "bag"):
            t0 = self.m.tris
            getattr(self, "build_" + name)()
            self.parts[name] = self.m.tris - t0
        if self.spec.get("mug", True):
            self.build_mug()
        self.parts["mug"] = self.mug.tris
        return self
