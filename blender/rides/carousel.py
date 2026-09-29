"""Karussell (landmark: Contact). A classic two-tier galloper carousel, 10.5 m across.

Rotating (rot_platform): a plank platform with a painted skirt, 12 carved horses on brass
barley-twist poles (horse_0..11, six outer and six inner), two chariot benches, the centre
column with mirrors and painted panels, the sweeps, a painted rounding board with oval
mirrors, gilt pilasters, shell cresting and two rows of bulbs, a striped canopy with a
scalloped fabric edge and bulbs on its ribs, and a second tier (a small drum with mirrors,
its own striped roof and a gilt finial with a pennant).
Static: a plank step ring round the platform and an iron outer rail with an entrance and
two gate lamps at the front (-Y).

Nodes: rot_platform (spins about three.js Y), horse_0..11 (children of rot_platform; each
horse is its own node so the engine can move it up and down its pole), horse_seat_2 (ride
camera, inside horse_2), bulbs_*, snow_canopy, light_0/1, cam_view/cam_target.
The horses face clockwise travel seen from above, which is the engine's default spin.

    /home/claude/tools/bpy-venv/bin/python blender/rides/carousel.py [--no-render] [--no-lite]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rcommon as rc  # noqa: E402
from rcommon import TAU, Part, node, rod, side_M, state  # noqa: E402
from mathutils import Euler, Matrix, Vector, noise  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import geo, render  # noqa: E402

NAME = "carousel"
PT = 0.42            # platform top
RP = 4.6             # platform radius
R_OUT, R_IN = 3.75, 2.6
Z_H = 1.30           # horse node height (middle of its travel)
Z_SW = 3.33          # underside of the sweeps (pole tops)
RB = 5.0             # rounding board apothem
RB0, RB1 = 3.40, 4.22
NB = 16              # rounding board sides
RC = 1.0             # centre column apothem
CAN0 = (5.3, 4.30)   # canopy eave (r, z)
CAN1 = (1.78, 5.56)  # canopy top (r, z)
TIER = (1.78, 5.56, 6.26)
CREAM_T = (1.0, 0.94, 0.82)
RED_T = (0.62, 0.05, 0.06)

HORSE_COATS = [
    # (coat tint, mane in gilt?, saddle tint, dapple)
    ((1.0, 0.99, 0.96), True, (0.55, 0.03, 0.04), False),
    ((0.55, 0.55, 0.57), False, (0.05, 0.12, 0.45), True),
    ((0.95, 0.93, 0.88), True, (0.05, 0.30, 0.12), False),
    ((0.40, 0.16, 0.07), False, (0.55, 0.03, 0.04), False),
    ((0.05, 0.045, 0.045), True, (0.55, 0.40, 0.08), False),
    ((0.86, 0.62, 0.30), False, (0.05, 0.12, 0.45), False),
]


# ------------------------------------------------------------------ geometry helpers
def sweep(part, pts, ws, hs, n=12, cap0=True, cap1=True, side=(0, 1, 0), **kw):
    """Loft elliptic rings along a path. ws/hs: half width (along `side`) and half height."""
    pts = [Vector(p) for p in pts]
    sv = Vector(side)
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()
        y = (sv - t * sv.dot(t)).normalized()
        z = t.cross(y).normalized()
        rings.append([p + y * (ws[i] * math.cos(TAU * j / n)) + z * (hs[i] * math.sin(TAU * j / n))
                      for j in range(n)])
    part.loft(rings, closed=True, cap_start=cap0, cap_end=cap1, smooth=True, **kw)


def smooth_path(ctrl, per=3):
    """Catmull-Rom through control points (x, y, z, r...) -> denser list of the same tuples."""
    out = []
    m = len(ctrl)
    for i in range(m - 1):
        p0 = ctrl[max(i - 1, 0)]
        p1, p2 = ctrl[i], ctrl[i + 1]
        p3 = ctrl[min(i + 2, m - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(len(p1))))
    out.append(tuple(ctrl[-1]))
    return out


def limb(part, ctrl, n=8, per=2, tint=None, cap1=True):
    """Tapered round limb through control points (x, y, z, r)."""
    pts = smooth_path(ctrl, per)
    sweep(part, [p[:3] for p in pts], [p[3] for p in pts], [p[3] for p in pts], n=n, cap0=False,
          cap1=cap1, tint=tint)


# ------------------------------------------------------------------ the horse
BODY = [  # x, z, half width, half height (tail root -> muzzle)
    (-0.67, 0.07, 0.04, 0.05), (-0.63, 0.06, 0.12, 0.13), (-0.56, 0.04, 0.17, 0.19),
    (-0.45, 0.02, 0.19, 0.215), (-0.31, 0.00, 0.185, 0.205), (-0.13, -0.02, 0.175, 0.195),
    (0.05, -0.02, 0.175, 0.200), (0.21, 0.01, 0.17, 0.21), (0.33, 0.06, 0.15, 0.20),
    (0.41, 0.13, 0.12, 0.17), (0.47, 0.23, 0.10, 0.14), (0.52, 0.34, 0.085, 0.12),
    (0.56, 0.45, 0.075, 0.10), (0.61, 0.54, 0.07, 0.09), (0.67, 0.60, 0.068, 0.085),
    (0.76, 0.60, 0.064, 0.08), (0.85, 0.55, 0.055, 0.068), (0.93, 0.49, 0.047, 0.058),
    (0.98, 0.45, 0.041, 0.050), (1.01, 0.43, 0.030, 0.036),
]


def body_at(x):
    """Interpolated (z, half width, half height) of the barrel at x (trunk only)."""
    for a, b in zip(BODY[:-1], BODY[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * t for i in (1, 2, 3))
    return BODY[-1][1:]


def build_horse(k, lite, var):
    coat, gilt_mane, saddle_t, dapple = HORSE_COATS[var % len(HORSE_COATS)]
    R = state.rng
    if dapple:
        def shade(p):
            nn = noise.noise(Vector((p.x * 11, p.y * 11, p.z * 11)))
            return 0.72 + 0.5 * max(0.0, nn)
    else:
        def shade(p):
            return 1.0 + 0.05 * noise.noise(Vector((p.x * 5, p.y * 5, p.z * 5)))
    en = Part(f"h{k}_enamel", "enamel", shade=shade, var=0.02)
    gl = Part(f"h{k}_gilt", "gilt", var=0.03)
    n = 6 if lite else 11
    body = BODY[::2] + [BODY[-1]] if lite else BODY
    # trunk, neck and head in one loft
    sweep(en, [(x, 0, z) for x, z, w, h in body], [w for *_, w, h in body], [h for *_, w, h in body],
          n=n, tint=coat)
    # jaw / cheek bulk and the forehead
    en.sphere((0.74, 0, 0.555), 0.07, seg=6 if lite else 12, rings=4 if lite else 8, scale=(1.3, 0.95, 0.85),
              tint=coat, rot=(0, 0.5, 0))
    # legs: jumper pose, front legs tucked, hind legs stretched back
    ln = 5 if lite else 7
    wob = [R.uniform(-0.03, 0.03) for _ in range(4)]
    legs = [
        [(0.27, 0.085, -0.06, 0.085), (0.33, 0.085, -0.26, 0.055), (0.50 + wob[0], 0.085, -0.31, 0.040),
         (0.47 + wob[0], 0.085, -0.46, 0.030), (0.50 + wob[0], 0.085, -0.51, 0.032)],
        [(0.27, -0.085, -0.06, 0.085), (0.31, -0.085, -0.28, 0.055), (0.45 + wob[1], -0.085, -0.40, 0.040),
         (0.43 + wob[1], -0.085, -0.55, 0.030), (0.46 + wob[1], -0.085, -0.60, 0.032)],
        [(-0.44, 0.10, -0.03, 0.105), (-0.39, 0.10, -0.24, 0.07), (-0.58 + wob[2], 0.10, -0.35, 0.042),
         (-0.71 + wob[2], 0.10, -0.48, 0.030), (-0.77 + wob[2], 0.10, -0.53, 0.032)],
        [(-0.44, -0.10, -0.03, 0.105), (-0.37, -0.10, -0.26, 0.07), (-0.54 + wob[3], -0.10, -0.39, 0.042),
         (-0.66 + wob[3], -0.10, -0.53, 0.030), (-0.72 + wob[3], -0.10, -0.58, 0.032)],
    ]
    for L in legs:
        limb(en, L[:-1], n=ln, per=1 if lite else 3, tint=coat, cap1=False)
        a, b = Vector(L[-2][:3]), Vector(L[-1][:3])
        d = (b - a).normalized()
        rod(en, a - d * 0.01, b + d * 0.04, 0.034, r2=0.042, seg=ln, caps=True, tint=(0.05, 0.04, 0.035))
    # ears, eyes, nostrils
    for s in (-1, 1):
        rod(en, (0.66, s * 0.035, 0.66), (0.62, s * 0.05, 0.76), 0.022, r2=0.004, seg=5 if lite else 7,
            caps=True, tint=coat)
        en.sphere((0.79, s * 0.058, 0.60), 0.014, seg=6, rings=4, tint=(0.02, 0.02, 0.02))
        if not lite:
            en.sphere((1.005, s * 0.022, 0.415), 0.009, seg=6, rings=4, tint=(0.05, 0.03, 0.03))
    # tail: carved, sweeping down
    tail = [(-0.64, 0, 0.07, 0.045), (-0.74, 0, 0.04, 0.055), (-0.81, 0, -0.10, 0.05),
            (-0.82, 0, -0.27, 0.04), (-0.77, 0, -0.40, 0.022)]
    limb(gl if gilt_mane else en, tail, n=ln, per=1 if lite else 3,
         tint=None if gilt_mane else (0.18, 0.12, 0.08))
    # mane: carved locks along the crest, falling to the outer side (+y)
    mp = gl if gilt_mane else en
    mt = None if gilt_mane else (0.2, 0.13, 0.08)
    locks = 3 if lite else 6
    for i in range(locks):
        t = i / (locks - 1)
        x = 0.40 + 0.25 * t
        z = 0.20 + 0.40 * t + 0.08
        mp.sphere((x - 0.02, 0.05, z), 0.06, seg=6, rings=4,
                  scale=(1.0, 0.45, 1.6), rot=(0.35, 0.9 - 0.4 * t, 0), tint=mt)
    mp.sphere((0.70, 0.0, 0.67), 0.05, seg=6, rings=4, scale=(1.2, 0.6, 0.6), rot=(0, 0.6, 0), tint=mt)  # forelock
    # saddle cloth, saddle, cantle and pommel
    en.sphere((-0.05, 0, -0.02), 1.0, seg=8 if lite else 14, rings=5 if lite else 8,
              scale=(0.26, 0.192, 0.218), tint=saddle_t)
    en.sphere((-0.04, 0, 0.17), 1.0, seg=8 if lite else 12, rings=4 if lite else 6, scale=(0.22, 0.17, 0.07),
              tint=(0.16, 0.06, 0.03))
    en.sphere((-0.21, 0, 0.21), 1.0, seg=8, rings=5, scale=(0.05, 0.13, 0.06), tint=(0.16, 0.06, 0.03))
    gl.sphere((0.13, 0, 0.22), 0.045, seg=8, rings=6)
    if not lite:
        # gilt edging on the saddle cloth, stirrups, bridle, reins and a jewelled breast collar
        gl.torus((-0.05, 0, -0.02), 0.2, 0.012, seg=16, tseg=4, rot=(math.pi / 2, 0, 0), arc=math.pi)
        for s in (-1, 1):
            gl.box((-0.02, s * 0.19, -0.12), (0.02, 0.008, 0.2), rot=(0, 0, 0))
            gl.torus((-0.02, s * 0.2, -0.26), 0.035, 0.006, seg=8, tseg=3, rot=(math.pi / 2, 0, 0))
        for x, z, w, h in ((0.95, 0.47, 0.05, 0.06), (0.80, 0.585, 0.069, 0.086)):
            sweep(gl, [(x - 0.008, 0, z), (x + 0.008, 0, z)], [w + 0.006] * 2, [h + 0.006] * 2,
                  n=12, cap0=False, cap1=False)
        for s in (-1, 1):
            rc_pts = [(0.96, s * 0.045, 0.44), (0.60, s * 0.09, 0.40), (0.30, s * 0.12, 0.30), (0.13, s * 0.03, 0.22)]
            gl.tube([Vector(p) for p in smooth_path(rc_pts, 3)], 0.006, tseg=4)
        for i in range(7):
            a = -0.9 + 1.8 * i / 6
            z0, w0, h0 = body_at(0.33)
            p = Vector((0.36 + 0.03 * math.cos(a), (w0 + 0.01) * math.sin(a), z0 - 0.02 - 0.08 * math.cos(a)))
            gl.sphere(p, 0.024, seg=6, rings=4)
        gl.sphere((0.40, 0, -0.08), 0.04, seg=10, rings=6, scale=(0.6, 1, 1))
    return [en, gl]


# ------------------------------------------------------------------ rotating structure
def barley_pole(part, x, y, z0, z1, lite):
    if lite:
        rod(part, (x, y, z0), (x, y, z1), 0.032, seg=8)
        return
    n = 8
    rings = []
    steps = int((z1 - z0) / 0.17)
    for i in range(steps + 1):
        z = z0 + (z1 - z0) * i / steps
        tw = z * 4.2
        rings.append([Vector((x + (0.030 if j % 2 == 0 else 0.022) * math.cos(tw + TAU * j / n),
                              y + (0.030 if j % 2 == 0 else 0.022) * math.sin(tw + TAU * j / n), z))
                      for j in range(n)])
    part.loft(rings, closed=True, smooth=True)
    for z in (z0 + 0.03, z1 - 0.05):
        part.cyl((x, y, z), 0.045, 0.045, 0.06, seg=12)


def build_rotating(lite, rot):
    paint = Part("car_paint", "paint", bevel=0.0)
    wood = Part("car_floor", "wood", tint="honey")
    gilt = Part("car_gilt", "gilt", var=0.03)
    mirror = Part("car_mirror", "mirror", var=0.02)
    brass = Part("car_poles", "brass", var=0.02)
    canvas = Part("car_canopy", "canvas", var=0.03)
    bulbs = Part("bulbs_carousel", "bulb_warm")
    snow = Part("snow_canopy", "snow")
    frame = Part("car_frame", "rsteel", tint=(0.15, 0.12, 0.10), bevel=0.0)

    # platform: radial planks, painted skirt, brass nosing
    nw = 36 if lite else 60
    for i in range(nw):
        a0, a1 = TAU * i / nw, TAU * (i + 1) / nw
        am = (a0 + a1) / 2
        h = (a1 - a0) / 2 - 0.0015
        poly = [(RC, -RC * math.tan(h)), (RP, -RP * math.tan(h)), (RP, RP * math.tan(h)), (RC, RC * math.tan(h))]
        M = Matrix.Translation((0, 0, PT - 0.02)) @ Euler((0, 0, am)).to_matrix().to_4x4()
        wood.shape(poly, depth=0.04, M=M, grain=0)
    frame.cyl((0, 0, 0.26), RP - 0.05, RP - 0.05, 0.3, seg=24 if lite else 48)
    ns = 24 if lite else 40
    for i in range(ns):
        a = TAU * (i + 0.5) / ns
        L = 2 * (RP + 0.02) * math.tan(math.pi / ns) + 0.01
        c = Vector(((RP + 0.02) * math.cos(a), (RP + 0.02) * math.sin(a), 0.27))
        paint.mbox(side_M(c, a), (L, 0.28, 0.03), band="red", grain=0)
        if not lite:
            paint.mbox(side_M(c + Vector((0, 0, 0.1)) + Vector((math.cos(a), math.sin(a), 0)) * 0.018, a),
                       (L, 0.02, 0.008), band="gold", grain=0)
    gilt.torus((0, 0, PT), RP + 0.02, 0.025, seg=48 if lite else 72, tseg=4 if lite else 5)

    # centre column: mirrors and painted panels between gilt pilasters
    nc = 12
    Lc = 2 * RC * math.tan(math.pi / nc)
    for j in range(nc):
        a = TAU * j / nc
        c = Vector((RC * math.cos(a), RC * math.sin(a), 0))
        H0, H1 = PT, Z_SW
        Mside = side_M(c + Vector((0, 0, (H0 + H1) / 2)), a)
        paint.mbox(Mside, (Lc + 0.01, H1 - H0, 0.03), band="blue" if j % 2 else "cream", grain=1)
        Mo = Mside @ Matrix.Translation((0, 0, 0.02))
        if j % 2 == 0:
            mirror.shape([(-0.17, -0.8), (0.17, -0.8), (0.17, 0.7), (0, 0.85), (-0.17, 0.7)], depth=0.01, M=Mo)
            gilt.shape([(-0.2, -0.83), (0.2, -0.83), (0.2, 0.72), (0, 0.9), (-0.2, 0.72)],
                       holes=[[(-0.17, -0.8), (0.17, -0.8), (0.17, 0.7), (0, 0.85), (-0.17, 0.7)]],
                       depth=0.02, M=Mo)
        else:
            gilt.shape([(0, -0.3), (0.14, 0), (0, 0.3), (-0.14, 0)],
                       holes=[[(0, -0.2), (0.08, 0), (0, 0.2), (-0.08, 0)]], depth=0.015, M=Mo)
            if not lite:
                gilt.shape(geo.star_polygon(0, 0.72, 0.09, 0.04, 6), depth=0.015, M=Mo)
                gilt.shape(geo.star_polygon(0, -0.72, 0.09, 0.04, 6), depth=0.015, M=Mo)
        # pilaster at the corner
        ac = a + math.pi / nc
        pc = Vector((RC / math.cos(math.pi / nc) * math.cos(ac), RC / math.cos(math.pi / nc) * math.sin(ac), 0))
        gilt.box(pc + Vector((0, 0, (H0 + H1) / 2)), (0.06, 0.06, H1 - H0), rot=(0, 0, ac + math.pi / 4))
    rc.lathe_poly(paint, [(RC + 0.12, PT), (RC + 0.12, PT + 0.18), (RC + 0.04, PT + 0.22)], nc, band="red")
    rc.lathe_poly(paint, [(RC + 0.02, Z_SW - 0.25), (RC + 0.14, Z_SW - 0.15), (RC + 0.14, Z_SW + 0.05)], nc,
                  band="red")
    for j in range(24):
        a = TAU * (j + 0.5) / 24
        rc.bulb(bulbs, (1.18 * math.cos(a), 1.18 * math.sin(a), Z_SW - 0.1), 0.035)

    # sweeps and pole rings under the canopy
    for j in range(NB):
        a = TAU * j / NB
        d = Vector((math.cos(a), math.sin(a), 0))
        paint.slab(d * RC + Vector((0, 0, Z_SW + 0.08)), d * RB + Vector((0, 0, Z_SW + 0.08)), 0.16, 0.08,
                   up=(0, 0, 1), band="cream")
    for R in (R_IN, R_OUT):
        m = 16 if lite else 24
        for j in range(m):
            a0, a1 = TAU * j / m, TAU * (j + 1) / m
            rod(frame, (R * math.cos(a0), R * math.sin(a0), Z_SW + 0.02), (R * math.cos(a1), R * math.sin(a1), Z_SW + 0.02),
                0.04, seg=6)
    # ceiling: radial boards under the canopy, visible from the platform
    nce = 32 if lite else 48
    for i in range(nce):
        a = TAU * (i + 0.5) / nce
        d = Vector((math.cos(a), math.sin(a), 0))
        h = math.pi / nce
        r0, r1 = RC, RB
        poly = [(r0, -r0 * math.tan(h)), (r1, -r1 * math.tan(h)), (r1, r1 * math.tan(h)), (r0, r0 * math.tan(h))]
        M = Matrix.Translation((0, 0, Z_SW + 0.19)) @ Euler((0, 0, a)).to_matrix().to_4x4()
        paint.shape(poly, depth=0.02, M=M, band="cream" if i % 2 else "red", grain=0)

    # poles
    for k in range(12):
        phi, r = horse_place(k)
        barley_pole(brass, r * math.cos(phi), r * math.sin(phi), PT, Z_SW, lite)
    # chariot benches
    for phi in (math.radians(-60), math.radians(120)):
        chariot(paint, gilt, wood, 3.95, phi, lite)

    # rounding board
    L = 2 * RB * math.tan(math.pi / NB)
    for j in range(NB):
        a = TAU * j / NB - math.pi / 2          # j = 0 faces the front (-Y)
        c = Vector((RB * math.cos(a), RB * math.sin(a), 0))
        zc = (RB0 + RB1) / 2
        Ms = side_M(c + Vector((0, 0, zc)), a)
        paint.mbox(Ms, (L + 0.02, RB1 - RB0, 0.05), band="red", grain=0)
        hh = (RB1 - RB0) / 2
        for yy in (hh - 0.05, -hh + 0.05):
            paint.mbox(Ms @ Matrix.Translation((0, yy, 0.035)), (L - 0.1, 0.035, 0.022), band="gold", grain=0)
        Mo = Ms @ Matrix.Translation((0, 0, 0.03))
        if j in (0, NB // 2):
            paint.text("Karussell", state.font("fraktur_bold"), 0.40, 0.02,
                       M=Mo @ Matrix.Translation((0, -0.02, 0.01)), max_width=L * 0.86, band="gold")
        else:
            ne = 10 if lite else 16
            ell = [(0.26 * math.cos(TAU * i / ne), 0.19 * math.sin(TAU * i / ne)) for i in range(ne)]
            ell2 = [(0.31 * math.cos(TAU * i / ne), 0.235 * math.sin(TAU * i / ne)) for i in range(ne)]
            mirror.shape(ell, depth=0.012, M=Mo)
            gilt.shape(ell2, holes=[ell], depth=0.03, M=Mo)
            if not lite:
                for sx in (-1, 1):
                    gilt.shape(geo.star_polygon(sx * 0.6, 0, 0.1, 0.045, 6), depth=0.015, M=Mo)
                    gilt.shape([(sx * 0.38, 0), (sx * 0.47, 0.05), (sx * 0.8, 0.0), (sx * 0.47, -0.05)],
                               depth=0.012, M=Mo)
        # shell cresting on top
        if not lite or j % 2 == 0:
            shell = [(0.0, 0.0)]
            m = 11
            for i in range(m + 1):
                t = math.pi * i / m
                r = 0.26 if i % 2 == 0 else 0.21
                shell.append((-r * math.cos(t), r * math.sin(t)))
            shell.append((0.0, 0.0))
            gilt.shape(shell[1:], depth=0.03, M=side_M(c + Vector((0, 0, RB1 - 0.02)), a))
        # scalloped valance under the board
        cp.valance(paint, -L / 2, L / 2, 0, RB0 + 0.01, 0.1, 0.09, 4, style="scallop", depth=0.022,
                   band="red", M=side_M(c, a))
        # pilaster and bulbs
        ac = a + math.pi / NB
        Rc = RB / math.cos(math.pi / NB) + 0.04
        pc = Vector((Rc * math.cos(ac), Rc * math.sin(ac), (RB0 + RB1) / 2))
        gilt.box(pc, (0.08, 0.07, RB1 - RB0 + 0.06), rot=(0, 0, ac))
        rc.bulb(bulbs, pc + Vector((math.cos(ac), math.sin(ac), 0)) * 0.06 + Vector((0, 0, 0.0)), 0.05)
        for yy, nbl in ((hh + 0.07, 5 if lite else 8), (-hh - 0.02, 0 if lite else 5)):
            for i in range(nbl):
                x = -L / 2 + L * (i + 0.5) / nbl
                p = Ms @ Vector((x, yy, 0.06))
                rc.bulb(bulbs, p, 0.04)

    # canopy gores with a little droop, alternating red and cream
    ng = NB
    rows = 4 if lite else 7
    cols = 3 if lite else 5
    for g in range(ng):
        a0 = TAU * g / ng - math.pi / 2 - math.pi / NB
        a1 = a0 + TAU / ng
        rings = []
        for i in range(rows + 1):
            v = i / rows
            r = CAN0[0] + (CAN1[0] - CAN0[0]) * v
            z = CAN0[1] + (CAN1[1] - CAN0[1]) * v
            ring = []
            for j in range(cols + 1):
                u = j / cols
                a = a0 + (a1 - a0) * u
                droop = 0.10 * math.sin(math.pi * u) * math.sin(math.pi * min(1.0, v * 1.15)) * (1 - 0.6 * v)
                ring.append(Vector((r * math.cos(a), r * math.sin(a), z - droop)))
            rings.append(ring)
        canvas.loft(rings, closed=False, smooth=True, grain=2, tint=RED_T if g % 2 == 0 else CREAM_T)
        # fabric scallop along the eave
        am = (a0 + a1) / 2
        Lg = 2 * CAN0[0] * math.sin(math.pi / ng)
        ce = Vector((CAN0[0] * math.cos(am) * math.cos(math.pi / ng), CAN0[0] * math.sin(am) * math.cos(math.pi / ng), 0))
        cp.valance(canvas, -Lg / 2, Lg / 2, 0, CAN0[1] + 0.01, 0.07, 0.12, 3, style="scallop", depth=0.01,
                   tint=CREAM_T if g % 2 == 0 else RED_T, M=side_M(ce, am))
        # rib with bulbs
        rib_a = a0
        p0 = Vector((CAN0[0] * math.cos(rib_a), CAN0[0] * math.sin(rib_a), CAN0[1] + 0.02))
        p1 = Vector((CAN1[0] * math.cos(rib_a), CAN1[0] * math.sin(rib_a), CAN1[1] + 0.02))
        rod(gilt, p0, p1, 0.022, seg=5)
        nr = 3 if lite else 5
        for i in range(nr):
            rc.bulb(bulbs, p0.lerp(p1, (i + 0.5) / nr) + Vector((0, 0, 0.05)), 0.04)
    # second tier: drum with mirrors, its own striped roof and a finial
    r_t, z0, z1 = TIER
    nt = 16
    Lt = 2 * r_t * math.tan(math.pi / nt)
    for j in range(nt):
        a = TAU * j / nt - math.pi / 2
        c = Vector((r_t * math.cos(a), r_t * math.sin(a), (z0 + z1) / 2))
        Ms = side_M(c, a)
        paint.mbox(Ms, (Lt + 0.01, z1 - z0, 0.04), band="cream" if j % 2 else "red", grain=0)
        if j % 2 == 0:
            e = [(0.16 * math.cos(TAU * i / 14), 0.2 * math.sin(TAU * i / 14)) for i in range(14)]
            e2 = [(0.2 * math.cos(TAU * i / 14), 0.25 * math.sin(TAU * i / 14)) for i in range(14)]
            mirror.shape(e, depth=0.01, M=Ms @ Matrix.Translation((0, 0, 0.025)))
            gilt.shape(e2, holes=[e], depth=0.025, M=Ms @ Matrix.Translation((0, 0, 0.025)))
        ac = a + math.pi / nt
        rc.bulb(bulbs, Vector(((r_t + 0.08) * math.cos(ac), (r_t + 0.08) * math.sin(ac), z1 - 0.05)), 0.04)
    rc.lathe_poly(gilt, [(r_t + 0.04, z1), (r_t + 0.1, z1 + 0.03), (r_t + 0.1, z1 + 0.06), (r_t, z1 + 0.07)], nt)
    for g in range(nt):
        a0 = TAU * g / nt - math.pi / 2 - math.pi / nt
        a1 = a0 + TAU / nt
        rings = []
        for i in range(4):
            v = i / 3
            r = (r_t + 0.25) + (0.12 - r_t - 0.25) * v
            z = z1 + 0.07 + 0.75 * v ** 0.8
            rings.append([Vector((r * math.cos(a0 + (a1 - a0) * u / 2), r * math.sin(a0 + (a1 - a0) * u / 2),
                                  z - 0.04 * math.sin(math.pi * u / 2) * (1 - v))) for u in range(3)])
        canvas.loft(rings, closed=False, smooth=True, tint=CREAM_T if g % 2 else RED_T)
    ztop = z1 + 0.82
    gilt.sphere((0, 0, ztop + 0.08), 0.13, seg=12 if lite else 20, rings=8 if lite else 12)
    rod(gilt, (0, 0, ztop + 0.15), (0, 0, ztop + 0.95), 0.025, r2=0.008, seg=8, caps=True)
    gilt.sphere((0, 0, ztop + 0.45), 0.06, seg=10, rings=6)
    pen = [(0, 0), (0.55, -0.1), (0.42, -0.18), (0.55, -0.26), (0, -0.28)]
    canvas.shape(pen, depth=0.008, M=Matrix.Translation((0.03, 0, ztop + 0.9)) @ Euler((math.pi / 2, 0, 0.3)).to_matrix().to_4x4(),
                 tint=RED_T)
    # snow on both canopies
    rc.lathe_poly(snow, [(CAN0[0] + 0.02, CAN0[1] + 0.04), (CAN0[0] - 0.3, CAN0[1] + 0.2),
                         ((CAN0[0] + CAN1[0]) / 2, (CAN0[1] + CAN1[1]) / 2 + 0.08),
                         (CAN1[0] + 0.05, CAN1[1] + 0.06), (CAN1[0] - 0.05, CAN1[1] + 0.04)], 16 if lite else 32,
                  flat=False)
    rc.lathe_poly(snow, [(r_t + 0.27, z1 + 0.1), (r_t * 0.6, z1 + 0.45), (0.2, z1 + 0.8), (0.001, z1 + 0.84)],
                  16, flat=False)
    return rc.finish_all([paint, wood, gilt, mirror, brass, canvas, bulbs, snow, frame], rot)


def chariot(paint, gilt, wood, r, phi, lite):
    """A two-seat chariot bench facing the direction of travel (clockwise from above)."""
    yaw = math.atan2(-math.cos(phi), math.sin(phi))
    M = Matrix.Translation((r * math.cos(phi), r * math.sin(phi), PT)) @ Euler((0, 0, yaw)).to_matrix().to_4x4()
    side = [(-0.55, 0.0), (0.5, 0.0), (0.62, 0.12), (0.6, 0.36), (0.48, 0.44), (0.42, 0.34), (0.48, 0.24),
            (0.2, 0.26), (-0.3, 0.42), (-0.52, 0.72), (-0.62, 0.9), (-0.72, 0.84), (-0.66, 0.5)]
    for s in (-1, 1):
        Ms = M @ Matrix.Translation((0, s * 0.36, 0)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
        paint.shape(side, depth=0.04, M=Ms, band="green", bevel=0.004)
        if not lite:
            gilt.shape(geo.star_polygon(-0.1, 0.22, 0.1, 0.045, 5), depth=0.012,
                       M=Ms @ Matrix.Translation((0, 0, s * 0.025)))
            gilt.shape([(0.4, 0.3), (0.55, 0.33), (0.5, 0.39), (0.44, 0.36)], depth=0.012,
                       M=Ms @ Matrix.Translation((0, 0, s * 0.025)))
    seat = M @ Matrix.Translation((-0.2, 0, 0.36))
    wood.mbox(seat, (0.45, 0.7, 0.05), grain=1)
    wood.mbox(M @ Matrix.Translation((-0.5, 0, 0.62)) @ Euler((0, -0.35, 0)).to_matrix().to_4x4(), (0.05, 0.7, 0.45),
              grain=1)
    wood.mbox(M @ Matrix.Translation((0.05, 0, 0.05)), (1.0, 0.68, 0.04), grain=0)          # floor
    paint.mbox(M @ Matrix.Translation((0.52, 0, 0.28)) @ Euler((0, 0.35, 0)).to_matrix().to_4x4(),
               (0.03, 0.68, 0.42), band="red")                                                  # dash board
    paint.mbox(M @ Matrix.Translation((-0.2, 0, 0.2)), (0.4, 0.62, 0.3), band="cream")       # seat box


def horse_place(k):
    phi = -math.pi / 2 + TAU * k / 12
    return phi, (R_OUT if k % 2 == 0 else R_IN)


# ------------------------------------------------------------------ static parts
def build_static(lite):
    wood = Part("car_step", "wood", tint="oak")
    iron = Part("car_rail", "rsteel", tint=(0.05, 0.18, 0.10), bevel=0.0)
    gilt = Part("car_rail_gilt", "gilt")
    bulbs = Part("bulbs_gate", "bulb_warm")
    stone = Part("car_kerb", "rsteel", tint=(0.28, 0.27, 0.26), bevel=0.0)
    n = 40 if lite else 64
    for i in range(n):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        am = (a0 + a1) / 2
        h = (a1 - a0) / 2 - 0.002
        r0, r1 = RP + 0.06, RP + 0.95
        poly = [(r0, -r0 * math.tan(h)), (r1, -r1 * math.tan(h)), (r1, r1 * math.tan(h)), (r0, r0 * math.tan(h))]
        M = Matrix.Translation((0, 0, 0.19)) @ Euler((0, 0, am)).to_matrix().to_4x4()
        wood.shape(poly, depth=0.04, M=M, grain=0)
    stone.cyl((0, 0, 0.085), RP + 0.97, RP + 0.97, 0.17, seg=32 if lite else 64)
    # outer rail with an entrance at the front
    Rr = 6.3
    gap = math.radians(9)
    posts = 28 if lite else 44
    front = -math.pi / 2
    angs = []
    for i in range(posts):
        a = front + gap + (TAU - 2 * gap) * i / (posts - 1)
        angs.append(a)
        p = Vector((Rr * math.cos(a), Rr * math.sin(a), 0))
        rod(iron, p, p + Vector((0, 0, 1.0)), 0.028, seg=6)
        gilt.sphere(p + Vector((0, 0, 1.04)), 0.04, seg=6, rings=4)
    for z, rr in ((0.95, 0.03), (0.5, 0.02), (0.12, 0.02)):
        iron.torus((0, 0, z), Rr, rr, seg=40 if lite else 72, tseg=4, arc=TAU - 2 * gap,
                   rot=(0, 0, front + gap))
    if not lite:
        for a0, a1 in zip(angs[:-1], angs[1:]):
            p0 = Vector((Rr * math.cos(a0), Rr * math.sin(a0), 0.5))
            p1 = Vector((Rr * math.cos(a1), Rr * math.sin(a1), 0.5))
            m = (p0 + p1) / 2
            iron.torus(m + Vector((0, 0, 0.22)), 0.16, 0.012, seg=8, tseg=3,
                       rot=(math.pi / 2, 0, (a0 + a1) / 2 + math.pi / 2))
    for s in (-1, 1):
        a = front + s * gap
        p = Vector((Rr * math.cos(a), Rr * math.sin(a), 0))
        iron.box(p + Vector((0, 0, 0.8)), (0.16, 0.16, 1.6))
        gilt.box(p + Vector((0, 0, 1.62)), (0.22, 0.22, 0.05))
        rc.bulb(bulbs, p + Vector((0, 0, 1.8)), 0.13, lite=False)
    return rc.finish_all([wood, iron, gilt, bulbs, stone])


def build(lite):
    rot = node("rot_platform", (0, 0, 0))
    build_rotating(lite, rot)
    for k in range(12):
        phi, r = horse_place(k)
        yaw = math.atan2(-math.cos(phi), math.sin(phi))
        pos = (r * math.cos(phi), r * math.sin(phi), Z_H)
        h = node(f"horse_{k}", pos, parent=rot)
        parts = build_horse(k, lite, k)
        objs = rc.finish_all(parts)
        M = Matrix.Translation(pos) @ Euler((0, 0, yaw)).to_matrix().to_4x4() @ \
            Euler((0, 0.04 * math.sin(k * 1.7), 0)).to_matrix().to_4x4()
        for ob in objs:
            ob.data.transform(M)
            rc.attach(ob, h)
        if k == 2:
            seat = M @ Vector((-0.04, 0, 0.24 + 0.75))
            node("horse_seat_2", tuple(seat), parent=h)
    build_static(lite)
    node("light_0", (0, -3.2, 3.0))
    node("light_1", (0, 3.2, 3.0))
    node("cam_target", (0, 0, 2.3))
    cv = node("cam_view", (-7.8, -10.8, 3.1))
    cv.rotation_euler = (Vector((0, 0, 2.3)) - Vector((-7.8, -10.8, 3.1))).to_track_quat('-Z', 'Y').to_euler()
    return rc.mesh_objs()


def preview(objs):
    for o in objs:
        if o.name.startswith("snow_"):
            o.hide_render = True
    render.lights_at_markers(energy=220)
    render.add_light("env_inner", 'POINT', (0, 0, 3.0), 300, size=0.8)
    render.add_light("env_front", 'POINT', (-3.5, -8.5, 3.5), 380, size=1.0)
    render.add_light("env_rim", 'AREA', (8, 9, 9), 1400, color=(0.55, 0.65, 1.0), size=6,
                     rot=(math.radians(-50), 0, math.radians(35)))
    return render.camera((-9.6, -12.8, 3.4), (0.2, 0, 2.6), lens=30)


if __name__ == "__main__":
    rc.run(NAME, build, preview, seed=12, ground=60)
