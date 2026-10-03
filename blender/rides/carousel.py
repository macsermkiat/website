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
camera, inside horse_2), bulbs_*, snow_canopy, light_0/1, light_2 (a child of rot_platform,
so the canopy light turns with the horses), cam_view/cam_target.
The horses are one sculpted master (horse.py) in six coats.
The horses face clockwise travel seen from above, which is the engine's default spin.

    /home/claude/tools/bpy-venv/bin/python blender/rides/carousel.py [--no-render] [--no-lite]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rcommon as rc  # noqa: E402
import horse  # noqa: E402
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


# ------------------------------------------------------------------ rotating structure
def barley_pole(part, x, y, z0, z1, lite):
    if lite:
        rod(part, (x, y, z0), (x, y, z1), 0.032, seg=8)
        return
    n = 8
    rings = []
    steps = int((z1 - z0) / 0.22)
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
    ink = Part("car_cartouche", "enamel", var=0.02)

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
        rc.bulb(bulbs, (1.18 * math.cos(a), 1.18 * math.sin(a), Z_SW - 0.1), 0.035, lite=True)

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
        if j % 4 == 0:
            # the name on four sides, gilt on a dark green cartouche so it reads from the rail
            cw, chh = L * 0.93, 0.60
            ink.shape(rounded_rect(cw, chh, 0.08), depth=0.012, M=Mo @ Matrix.Translation((0, -0.01, 0.012)),
                      tint=(0.015, 0.075, 0.045))
            gilt.shape(rounded_rect(cw + 0.06, chh + 0.06, 0.11), holes=[rounded_rect(cw, chh, 0.08)],
                       depth=0.03, M=Mo @ Matrix.Translation((0, -0.01, 0.012)))
            paint.text("Karussell", state.font("fraktur_bold"), 0.52, 0.02,
                       M=Mo @ Matrix.Translation((0, -0.05, 0.026)), max_width=cw * 0.9, band="gold")
        else:
            ne = 10 if lite else 16
            ell = [(0.26 * math.cos(TAU * i / ne), 0.19 * math.sin(TAU * i / ne)) for i in range(ne)]
            ell2 = [(0.31 * math.cos(TAU * i / ne), 0.235 * math.sin(TAU * i / ne)) for i in range(ne)]
            bevelled_mirror(mirror, ell, Mo, lite)
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
            rc.bulb(bulbs, p0.lerp(p1, (i + 0.5) / nr) + Vector((0, 0, 0.05)), 0.04, lite=True)
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
            bevelled_mirror(mirror, e, Ms @ Matrix.Translation((0, 0, 0.025)), lite, rise=0.018)
            gilt.shape(e2, holes=[e], depth=0.025, M=Ms @ Matrix.Translation((0, 0, 0.025)))
        ac = a + math.pi / nt
        rc.bulb(bulbs, Vector(((r_t + 0.08) * math.cos(ac), (r_t + 0.08) * math.sin(ac), z1 - 0.05)), 0.04, lite=True)
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
    return rc.finish_all([paint, wood, gilt, mirror, brass, canvas, bulbs, snow, frame, ink], rot)


def bevelled_mirror(mirror, ell, M, lite, scale=0.8, rise=0.022):
    """An oval mirror with a ring of bevelled facets round a flat centre: the facets face
    different ways, so each catches a different bulb."""
    inner = [(x * scale, y * scale) for x, y in ell]
    mirror.shape(inner, depth=0.004, M=M @ Matrix.Translation((0, 0, rise - 0.002)))
    rings = [[M @ Vector((x, y, -0.004)) for x, y in ell], [M @ Vector((x, y, rise)) for x, y in inner]]
    mirror.loft(rings, closed=True, smooth=False)


def rounded_rect(w, h, r, n=4):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


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
        iron.torus((0, 0, z), Rr, rr, seg=40 if lite else 48, tseg=4, arc=TAU - 2 * gap,
                   rot=(0, 0, front + gap))
    if not lite:
        for a0, a1 in zip(angs[:-1], angs[1:]):
            p0 = Vector((Rr * math.cos(a0), Rr * math.sin(a0), 0.5))
            p1 = Vector((Rr * math.cos(a1), Rr * math.sin(a1), 0.5))
            m = (p0 + p1) / 2
            iron.torus(m + Vector((0, 0, 0.22)), 0.16, 0.012, seg=6, tseg=3,
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
    # one sculpted master horse (horse.py) shared by the 12 nodes, painted in six coats: horses
    # k and k + 6 share a mesh, and the gilt harness is one mesh for all twelve
    herd = horse.Herd(lite)
    for k in range(12):
        phi, r = horse_place(k)
        yaw = math.atan2(-math.cos(phi), math.sin(phi))
        pos = (r * math.cos(phi), r * math.sin(phi), Z_H)
        pitch = 0.04 * math.sin((k % 6) * 1.7)
        h = node(f"horse_{k}", pos, parent=rot, rot=(0, pitch, yaw))
        rc.bpy.context.view_layer.update()
        herd.horse(k, k % 6, h)
        if k == 2:
            seat = h.matrix_world @ Vector((-0.04, 0, 0.24 + 0.75))
            node("horse_seat_2", tuple(seat), parent=h)
    build_static(lite)
    node("light_0", (0, -3.2, 3.0))
    node("light_1", (0, 3.2, 3.0))
    # a canopy light that turns with the platform: it hangs from the sweeps between the inner and
    # outer horses, so the rider on horse_2 always has the horses around them lit
    node("light_2", ((R_IN + R_OUT) / 2 * math.cos(-math.pi / 2 + TAU * 2.5 / 12),
                     (R_IN + R_OUT) / 2 * math.sin(-math.pi / 2 + TAU * 2.5 / 12), Z_SW - 0.25), parent=rot)
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
