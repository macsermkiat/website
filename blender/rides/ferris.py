"""Riesenrad (landmark: Big questions). A 26 m travelling Ferris wheel.

Twin steel rims (outer and inner ring joined by a zig-zag truss) on 32 tension spokes per side,
a hub drum with a gilt sunburst, 16 enclosed octagonal gondolas with windows, benches, a
ceiling lamp and eave bulbs, two lattice A-frames on timber cribbing, a boarding deck with
steps and railings, an arched entrance sign and a ticket booth.

Nodes (docs/BUILD.md): rot_wheel (spins about the axle, three.js local Z), gondola_0..15
(empties at the hanging point, children of rot_wheel), gondola_seat_0 (ride camera, inside
gondola_0), bulbs_* (warm), snow_*, light_0/1, cam_view/cam_target.
Front (the entrance) faces -Y. gondola_0 hangs at the bottom, at the boarding deck.

    /home/claude/tools/bpy-venv/bin/python blender/rides/ferris.py [--no-render] [--no-lite]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rcommon as rc  # noqa: E402
from rcommon import TAU, Part, node, rod, state  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import geo, render  # noqa: E402

NAME = "ferris"


def register_art():
    import art
    rc.IMAGE_MATS["poster_riesenrad"] = (art.poster_riesenrad(), 0.75)
    rc.IMAGE_MATS["poster_nachtmarkt"] = (art.poster_nachtmarkt(), 0.75)
    rc.IMAGE_MATS["price_board"] = (art.price_board(), 0.6)


register_art()
HUB = 14.70         # axle height (lowest gondola clears the boarding deck by 9 cm)
RO = 11.2           # outer ring = gondola axles
RI = 10.05          # inner ring
RT = 7.40           # transverse tie ring: 3.8 m inside the gondola axles, outside every gondola's swing
YR = 1.42           # rim planes at y = +-YR
GS = 1.25           # gondola scale (modelled at 1.0: 1.87 m across, 2.33 m tall)
N = 16
CREAM = (0.93, 0.88, 0.76)
DARK = (0.30, 0.30, 0.31)
GONDOLA_COLS = [(0.60, 0.05, 0.05), (0.07, 0.16, 0.50), (0.06, 0.30, 0.14), (0.80, 0.52, 0.14)]
DECK = 0.42


def P(r, a, y):
    """Point on the wheel: radius r, angle a (0 = +X, counter-clockwise seen from the front), plane y."""
    return Vector((r * math.cos(a), y, HUB + r * math.sin(a)))


def spoke_y(r):
    """|y| of a main spoke at radius r (the spokes run from the hub flange at YR + 0.62 to the rim)."""
    return (YR + 0.62) + (YR - (YR + 0.62)) * (r - 1.05) / (RI - 1.05)


def gondola_angle(i):
    return -math.pi / 2 + TAU * i / N


def spoke_angle(i):
    return gondola_angle(i) + math.pi / N


# ------------------------------------------------------------------ wheel (rotating)
def build_wheel(lite, wheel):
    st = Part("wheel_steel", "rsteel", tint=CREAM, bevel=0.0, var=0.05)
    gilt = Part("wheel_gilt", "gilt", var=0.03)
    bulbs = Part("bulbs_wheel", "bulb_warm")
    dark = Part("wheel_hub", "rsteel", tint=(0.20, 0.19, 0.18), bevel=0.0)
    rs = 4 if lite else 6            # rod segments
    tor_seg = 64 if lite else 128
    rot_x = (math.pi / 2, 0, 0)
    for y in (-YR, YR):
        st.torus((0, y, HUB), RO, 0.085, seg=tor_seg, tseg=5 if lite else 8, rot=rot_x)
        st.torus((0, y, HUB), RI, 0.06, seg=tor_seg, tseg=4 if lite else 6, rot=rot_x)
        if not lite:
            st.torus((0, y, HUB), RO + 0.13, 0.022, seg=tor_seg, tseg=4, rot=rot_x)   # bulb rail
        # truss between the rings
        M = 2 * N
        for k in range(M):
            a0 = TAU * k / M
            a1 = TAU * (k + 1) / M
            rod(st, P(RI, a0, y), P(RO, a0, y), 0.045, seg=rs)
            if k % 2 == 0:
                rod(st, P(RI, a0, y), P(RO, a1, y), 0.034, seg=rs)
            else:
                rod(st, P(RO, a0, y), P(RI, a1, y), 0.034, seg=rs)
        # spokes: radial main spokes to the inner ring MIDWAY between the gondolas (so a rider
        # looking out of a gondola at the top does not have a spoke running down past the
        # window), and tension rods crossing from each spoke's hub end to the neighbouring spokes
        yf = math.copysign(YR + 0.62, y)
        for i in range(N):
            sa = spoke_angle(i)
            rod(st, P(1.05, sa, yf), P(RI, sa, y), 0.06, seg=rs)
            if not lite or i % 2 == 0:
                rod(st, P(1.05, sa + 0.10, yf), P(RI, spoke_angle(i + 1), y), 0.026, seg=4)
                rod(st, P(1.05, sa - 0.10, yf), P(RI, spoke_angle(i - 1), y), 0.026, seg=4)
        # bulbs: outer rail and along each main spoke (the star seen from the market)
        nb = 36 if lite else 96
        for k in range(nb):
            a = TAU * (k + 0.5) / nb
            rc.bulb(bulbs, P(RO + 0.17, a, y), 0.05)
        per = 4 if lite else 13
        for i in range(N):
            a = spoke_angle(i)
            for j in range(per):
                r = 1.8 + (RI - 2.3) * j / (per - 1)
                t = (r - 1.05) / (RI - 1.05)
                yy = yf + (y - yf) * t
                p = P(r, a, yy) + Vector((0, math.copysign(0.07, y), 0))
                rc.bulb(bulbs, p, 0.042)
    # transverse members. Each gondola swings through a disc of radius 3.0 m round its axle
    # between the rims (|y| < 1.25), so nothing may cross between the rims there: the rims are
    # tied only by the gondola axles themselves and, well inside the swing discs, by a tie ring
    # at RT with X braces between the two spoke planes (3.8 m from the nearest axle).
    ty = spoke_y(RT)
    for i in range(N):
        a = gondola_angle(i)
        rod(st, P(RO, a, -YR - 0.05), P(RO, a, YR + 0.05), 0.075, seg=rs + 2)
        s1, s2 = spoke_angle(i), spoke_angle(i + 1)      # the tie ring joins the spokes
        rod(st, P(RT, s1, -ty), P(RT, s1, ty), 0.05, seg=rs)
        for s in (-1, 1):
            rod(st, P(RT, s1, s * ty), P(RT, s2, s * ty), 0.04, seg=rs)
        if not lite or i % 2 == 0:
            rod(st, P(RT, s1, -ty), P(RT, s2, ty), 0.028, seg=4)
            rod(st, P(RT, s1, ty), P(RT, s2, -ty), 0.028, seg=4)
        # gilt bearing collars where each gondola hangs
        for s in (() if lite else (-1, 1)):
            gilt.cyl(P(RO, a, s * (YR - 0.12)), 0.1, 0.1, 0.06, seg=10, rot=rot_x)
    # hub drum and flanges
    hl = YR + 0.7
    dark.cyl((0, 0, HUB), 0.72, 0.72, 2 * hl, seg=12 if lite else 24, rot=rot_x)
    for s in (-1, 1):
        dark.cyl((0, s * (YR + 0.62), HUB), 1.18, 1.18, 0.09, seg=16 if lite else 32, rot=rot_x)
        if not lite:
            for k in range(16):
                a = TAU * k / 16
                gilt.cyl(P(1.02, a, s * (YR + 0.68)), 0.035, 0.035, 0.05, seg=6, rot=rot_x)
        # gilt sunburst on the hub face: a stepped 16-ray star (rays reach past the flange) with
        # a raised 8-point star, a bulb at every ray tip and along each ray
        Ms = Matrix.Translation((0, s * (hl + 0.03), HUB)) @ Euler((-s * math.pi / 2, 0, 0)).to_matrix().to_4x4()
        gilt.shape(geo.star_polygon(0, 0, 1.55, 0.62, 16), depth=0.04, M=Ms)
        gilt.shape(geo.star_polygon(0, 0, 1.30, 0.55, 16), depth=0.04, M=Ms @ Matrix.Translation((0, 0, 0.03)))
        gilt.shape(geo.star_polygon(0, 0, 0.70, 0.36, 8, rot=math.pi / 8),
                   depth=0.05, M=Ms @ Matrix.Translation((0, 0, 0.06)))
        rays = TAU / 16
        for k in range(16):
            a = math.pi / 2 + rays * k
            for r in ((1.58,) if lite else (0.95, 1.25, 1.58)):
                rc.bulb(bulbs, P(r, a, s * (hl + 0.13)), 0.045)
        for k in range(12 if lite else 24):
            a = TAU * (k + 0.5) / (12 if lite else 24)
            rc.bulb(bulbs, P(1.78, a, s * (hl + 0.03)), 0.045)
    objs = rc.finish_all([st, gilt, dark, bulbs], wheel)
    return objs


# ------------------------------------------------------------------ gondolas
def build_gondola(i, g, lite):
    """Octagonal cabin hanging from the axle at g (world pivot)."""
    col = GONDOLA_COLS[i % len(GONDOLA_COLS)]
    rc.bpy.context.view_layer.update()
    Ow = g.matrix_world.translation.copy()
    O = Vector((0, 0, 0))
    T = Matrix()
    seg = 8
    body = Part(f"gond{i}_body", "rsteel", tint=col, bevel=0.0, var=0.04)
    trim = Part(f"gond{i}_trim", "rsteel", tint=CREAM, bevel=0.0, var=0.04)
    gilt = Part(f"gond{i}_gilt", "gilt", var=0.03)
    glass = Part(f"gond{i}_glass", "gondola_glass")
    wood = Part(f"gond{i}_wood", "wood", tint="honey", bevel=0.0)
    bulbs = Part(f"bulbs_g{i}", "bulb_warm")
    snow = Part(f"snow_g{i}", "snow")
    # hanger yoke from the axle down to the roof
    yk = (YR - 0.17) / GS          # the yoke stops short of the gilt bearing collars on the axle
    rod(trim, O + Vector((0, -yk, 0)), O + Vector((0, yk, 0)), 0.062, seg=8)
    for s in (-1, 1):
        rod(trim, O + Vector((0, s * min(0.62, yk - 0.05), 0)), O + Vector((0, s * 0.16, -0.30)), 0.028, seg=5)
    rod(trim, O + Vector((0, 0, -0.02)), O + Vector((0, 0, -0.30)), 0.03, seg=5)
    # roof (ogee, octagonal), a thin header, a tall glass band (sill at bench height, so a
    # seated rider sees down over the market), sill, lower body
    roof = [(0.10, -0.25), (0.20, -0.29), (0.44, -0.39), (0.68, -0.49), (0.88, -0.60),
            (0.935, -0.645), (0.935, -0.685), (0.80, -0.70)]
    if lite:
        roof = [(0.10, -0.25), (0.44, -0.39), (0.88, -0.60), (0.935, -0.685), (0.80, -0.70)]
    rc.lathe_poly(body, roof, seg, M=T)
    rc.lathe_poly(trim, [(0.80, -0.70), (0.80, -0.76)], seg, M=T)
    rc.lathe_poly(gilt, [(0.815, -0.745), (0.822, -0.755), (0.815, -0.765)], seg, M=T)
    rc.lathe_poly(glass, [(0.775, -0.76), (0.775, -1.56)], seg, M=T)
    rc.lathe_poly(trim, [(0.84, -1.56), (0.84, -1.61), (0.80, -1.61)], seg, M=T)
    lower = [(0.80, -1.61), (0.80, -1.95), (0.75, -2.08), (0.62, -2.20), (0.40, -2.29), (0.001, -2.33)]
    rc.lathe_poly(body, lower, seg, M=T)
    if not lite:
        rc.lathe_poly(gilt, [(0.805, -1.77), (0.81, -1.78), (0.805, -1.79)], seg, M=T)
    gilt.sphere(O + Vector((0, 0, -0.22)), 0.07, seg=6 if lite else 12, rings=4 if lite else 8)
    gilt.cyl(O + Vector((0, 0, -2.36)), 0.05, 0.001, 0.08, seg=8)
    # window posts at the octagon corners (corner angles: k*45 deg + 22.5)
    Rc = 0.80 / math.cos(math.pi / seg)
    for k in range(seg):
        a = TAU * k / seg + math.pi / seg
        trim.box(O + Vector((Rc * math.cos(a), Rc * math.sin(a), -1.16)), (0.038, 0.038, 0.80),
                 rot=(0, 0, a))
    # cabin interior: floor, two benches facing each other across the cabin (along X), ceiling
    # lamp; the door is on the front (-Y) face, toward the boarding step
    wood.cyl(O + Vector((0, 0, -1.99)), 0.76, 0.76, 0.03, seg=8, rot=(0, 0, math.pi / 8))
    if not lite:
        for s in (-1, 1):
            wood.box(O + Vector((s * 0.50, 0, -1.62)), (0.34, 0.95, 0.05), grain=0)
            wood.box(O + Vector((s * 0.70, 0, -1.40)), (0.05, 0.95, 0.40), rot=(0, s * 0.12, 0), grain=0)
            body.box(O + Vector((s * 0.50, 0, -1.82)), (0.3, 0.9, 0.32))
        # door: its upper half is the cabin's glass band; gilt frame on the lower leaf, handle, hinges
        for dx in (-0.26, 0.26):
            gilt.box(O + Vector((dx, -0.805, -1.785)), (0.018, 0.012, 0.35))
        gilt.box(O + Vector((0, -0.805, -1.96)), (0.54, 0.012, 0.02))
        gilt.cyl(O + Vector((0.18, -0.83, -1.66)), 0.012, 0.012, 0.06, seg=6, rot=(math.pi / 2, 0, 0))
        for z in (-1.0, -1.8):
            gilt.cyl(O + Vector((-0.27, -0.815, z)), 0.014, 0.014, 0.08, seg=6)
        # gilt stars on the side and back panels
        for a in (0.0, math.pi / 2, math.pi):
            n = Vector((math.cos(a), math.sin(a), 0))
            Ms = Matrix.Translation(O + n * 0.81 + Vector((0, 0, -1.79))) @ \
                Euler((math.pi / 2, 0, a + math.pi / 2)).to_matrix().to_4x4()
            gilt.shape(geo.star_polygon(0, 0, 0.13, 0.055, 5), depth=0.012, M=Ms)
    rc.bulb(bulbs, O + Vector((0, 0, -0.80)), 0.06)
    for k in range(0, seg, 2 if lite else 1):
        a = TAU * k / seg + math.pi / seg
        r = 0.955 / math.cos(math.pi / seg)
        rc.bulb(bulbs, O + Vector((r * math.cos(a), r * math.sin(a), -0.70)), 0.038)
    # snow on the roof (engine shows it only when snow is on)
    rc.lathe_poly(snow, [(0.001, -0.20), (0.16, -0.235), (0.42, -0.345), (0.66, -0.45),
                         (0.84, -0.545), (0.90, -0.585), (0.86, -0.61)], seg, M=T)
    objs = rc.finish_all([body, trim, gilt, glass, wood, bulbs, snow])
    S = Matrix.Translation(Ow) @ Matrix.Diagonal((GS, GS, GS, 1.0))
    for ob in objs:
        ob.data.transform(S)
        rc.attach(ob, g)
    return objs


# ------------------------------------------------------------------ frame (static)
def truss_leg(st, A, B, w0, w1, lite):
    A, B = Vector(A), Vector(B)
    d = (B - A)
    L = d.length
    d.normalize()
    u = d.cross(Vector((0, 0, 1))).normalized()
    v = d.cross(u).normalized()
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]

    def c(t, k):
        w = (w0 + (w1 - w0) * t) / 2
        return A + d * (L * t) + u * (corners[k][0] * w) + v * (corners[k][1] * w)
    rs = 4 if lite else 6
    for k in range(4):
        rod(st, c(0, k), c(1, k), 0.075, seg=rs)
    n = int(L / (1.6 if lite else 0.9))
    for j in range(n):
        t0, t1 = j / n, (j + 1) / n
        for k in range(4):
            k2 = (k + 1) % 4
            if j % 2 == 0:
                rod(st, c(t0, k), c(t1, k2), 0.03, seg=4)
            else:
                rod(st, c(t0, k2), c(t1, k), 0.03, seg=4)
        if j % 4 == 0:
            for k in range(4):
                rod(st, c(t0, k), c(t0, (k + 1) % 4), 0.028, seg=4)


def build_frame(lite):
    st = Part("frame_steel", "rsteel", tint=CREAM, bevel=0.0, var=0.05)
    darks = Part("frame_dark", "rsteel", tint=DARK, bevel=0.0, var=0.05)
    red = Part("frame_red", "rsteel", tint=(0.55, 0.06, 0.05), bevel=0.0)
    wood = Part("frame_wood", "wood", tint="oak")
    sleepers = Part("frame_sleepers", "wood", tint="soot", var=0.15)
    paint = Part("frame_paint", "paint")
    gilt = Part("frame_gilt", "gilt")
    bulbs = Part("bulbs_base", "bulb_warm")
    snow = Part("snow_base", "snow")
    ay = YR + 1.2
    FY = 4.6
    feet = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            A = (0, sy * ay, HUB - 0.2)
            B = (sx * 7.6, sy * FY, 0.62)
            truss_leg(st, A, B, 0.42, 1.0, lite)
            feet[(sx, sy)] = Vector(B)
            # foot plate and timber cribbing
            darks.box((B[0], B[1], 0.52), (1.3, 1.3, 0.06))
            for layer in range(3):
                z = 0.08 + layer * 0.15
                for k in (-1, 0, 1):
                    if layer % 2 == 0:
                        sleepers.box((B[0] + k * 0.42, B[1], z), (0.24, 1.9, 0.14), jitter=0.05)
                    else:
                        sleepers.box((B[0], B[1] + k * 0.42, z), (1.9, 0.24, 0.14), jitter=0.05)
    # cross ties inside each A-frame and longitudinal ground beams
    for sy in (-1, 1):
        for z, half in ((5.4, 4.62), (9.4, 2.4)):
            t = (HUB - 0.2 - z) / (HUB - 0.2 - 0.62)
            y = sy * (ay + (FY - ay) * t)
            a = Vector((-half, y, z))
            b = Vector((half, y, z))
            for dz in (-0.28, 0.28):
                rod(st, a + Vector((0, 0, dz)), b + Vector((0, 0, dz)), 0.06, seg=4 if lite else 6)
            n = 8 if z < 6 else 4
            for k in range(n):
                p0 = a.lerp(b, k / n)
                p1 = a.lerp(b, (k + 1) / n)
                if k % 2 == 0:
                    rod(st, p0 + Vector((0, 0, -0.28)), p1 + Vector((0, 0, 0.28)), 0.03, seg=4)
                else:
                    rod(st, p0 + Vector((0, 0, 0.28)), p1 + Vector((0, 0, -0.28)), 0.03, seg=4)
    # ground beams between the A-frames, and raking stays from each beam up to the legs. The
    # stays stay outside the wheel (|y| >= 1.9, where the wheel reaches only 3 m from the hub).
    for sx in (-1, 1):
        darks.box((sx * 7.6, 0, 0.62), (0.22, 2 * FY, 0.30))
        for sy in (-1, 1):
            A = Vector((0, sy * ay, HUB - 0.2))
            leg = A.lerp(feet[(sx, sy)], (HUB - 0.2 - 4.4) / (HUB - 0.2 - 0.62))
            rod(st, Vector((sx * 7.6, sy * 1.9, 0.77)), leg - Vector((0, sy * 0.3, 0)), 0.05, seg=6)
    # axle and bearing blocks at the apex
    darks.cyl((0, 0, HUB), 0.3, 0.3, 2 * ay + 0.5, seg=12 if lite else 20, rot=(math.pi / 2, 0, 0))
    for sy in (-1, 1):
        darks.box((0, sy * ay, HUB - 0.12), (0.95, 0.5, 0.7))
        # gilt domed axle cap ringed with bulbs (it sits in the middle of the sunburst seen from the square)
        gilt.cyl((0, sy * (ay + 0.28), HUB), 0.40, 0.40, 0.06, seg=16 if lite else 24, rot=(math.pi / 2, 0, 0))
        gilt.sphere((0, sy * (ay + 0.31), HUB), 0.3, seg=12 if lite else 20, rings=6 if lite else 10,
                    scale=(1, 0.5, 1))
        for k in range(8 if lite else 12):
            a = TAU * k / (8 if lite else 12)
            rc.bulb(bulbs, (0.48 * math.cos(a), sy * (ay + 0.3), HUB + 0.48 * math.sin(a)), 0.045)

    # boarding deck under the lowest gondola, steps to the front, railings
    x0, x1, y0, y1 = -2.6, 2.6, -2.1, 1.7
    step = 0.15
    k = 0
    x = x0
    while x < x1 - 1e-3:
        w = min(0.15, x1 - x)
        wood.box((x + w / 2, (y0 + y1) / 2, DECK - 0.02), (w - 0.006, y1 - y0, 0.04), grain=1,
                 jitter=0.02)
        x += w
        k += 1
    darks.box((0, (y0 + y1) / 2, DECK / 2 - 0.03), (x1 - x0 - 0.1, y1 - y0 - 0.1, DECK - 0.06))
    for i in range(3):
        z = DECK - (i + 1) * 0.14
        yy = y0 - 0.3 * (i + 0.5)
        wood.box((0, yy, z + 0.07 - 0.02), (2.4, 0.3, 0.04), grain=0)
        darks.box((0, yy, z / 2 + 0.01), (2.3, 0.28, max(0.02, z)))
    # railings: the gondolas swing through the deck's middle band (|y| < 1.3) as they pass, so
    # the side rails stop either side of it and the back rail closes the far edge
    GAP = 1.38
    for sx in (-1, 1):
        xx = sx * (x1 - 0.05)
        for ya, yb in ((y0 + 0.05, -GAP), (GAP, y1 - 0.05)):
            for yy in (ya, yb):
                rod(red, (xx, yy, DECK), (xx, yy, DECK + 1.0), 0.03, seg=6)
            for z in (DECK + 0.5, DECK + 1.0):
                rod(red, (xx, ya, z), (xx, yb, z), 0.022 if z < 1 else 0.028, seg=6)
    for xx in (x0 + 0.05, 0.0, x1 - 0.05):
        rod(red, (xx, y1 - 0.05, DECK), (xx, y1 - 0.05, DECK + 1.0), 0.03, seg=6)
    for z in (DECK + 0.5, DECK + 1.0):
        rod(red, (x0 + 0.05, y1 - 0.05, z), (x1 - 0.05, y1 - 0.05, z), 0.022 if z < 1 else 0.028, seg=6)
    # boarding step up to the gondola floor (1.03 m), in front of the gondola path
    for k, (zt, yy) in enumerate(((DECK + 0.30, -1.28), (DECK + 0.15, -1.55))):
        wood.box((0, yy, zt - 0.02), (1.6, 0.34 if k == 0 else 0.22, 0.04), grain=0)
        darks.box((0, yy, (zt - 0.04 + DECK) / 2), (1.5, 0.3 if k == 0 else 0.2, zt - 0.04 - DECK))
        # stair rails
        rod(red, (sx * 1.25, y0, DECK + 1.0), (sx * 1.25, y0 - 0.9, 0.55 + 0.4), 0.028, seg=6)
        rod(red, (sx * 1.25, y0 - 0.9, 0.0), (sx * 1.25, y0 - 0.9, 0.95), 0.03, seg=6)
    # arched entrance sign over the steps, on two gilt-capped posts
    ys = y0 - 1.05
    for sx in (-1, 1):
        red.box((sx * 1.45, ys, 1.55), (0.14, 0.14, 3.1))
        gilt.sphere((sx * 1.45, ys, 3.18), 0.1, seg=12, rings=8)
    cp.sign(paint, paint, "Riesenrad", state.font("fraktur_bold"), (0, ys - 0.02, 2.75), 2.9, 0.78,
            depth=0.05, board_band="red", text_band="gold", frame_band="gold", board_shape="arch",
            text_size=0.46, text_depth=0.02, text_dy=-0.05, max_fill=0.82)
    for k in range(15):
        t = k / 14
        a = math.pi * t
        rc.bulb(bulbs, (-1.45 * math.cos(a), ys - 0.06, 2.39 + 0.6 * math.sin(a)), 0.045)
    for sx in (-1, 1):
        for z in (0.6, 1.2, 1.8, 2.4):
            rc.bulb(bulbs, (sx * 1.45, ys - 0.09, z), 0.04)

    # ticket booth (Kasse) at the front left
    bx, by = -4.1, -4.3
    W, D, H = 1.7, 1.35, 2.3
    for sy in (-1, 1):
        for xx in (-W / 2, W / 2):
            paint.box((bx + xx, by + sy * D / 2, H / 2), (0.1, 0.1, H), band="cream")
    # walls of vertical boards, front with a window
    for side in ("front", "back", "left", "right"):
        if side in ("front", "back"):
            yy = by + (-D / 2 if side == "front" else D / 2)
            nb = int(W / 0.12)
            for j in range(nb):
                xx = bx - W / 2 + (j + 0.5) * W / nb
                if side == "front" and abs(xx - bx) < 0.5:
                    paint.box((xx, yy, 0.5), (W / nb - 0.008, 0.03, 1.0), band="red", grain=2)
                    paint.box((xx, yy, 2.15), (W / nb - 0.008, 0.03, 0.3), band="red", grain=2)
                else:
                    paint.box((xx, yy, H / 2), (W / nb - 0.008, 0.03, H), band="red", grain=2)
        else:
            xx = bx + (-W / 2 if side == "left" else W / 2)
            nb = int(D / 0.12)
            for j in range(nb):
                yy = by - D / 2 + (j + 0.5) * D / nb
                paint.box((xx, yy, H / 2), (0.03, D / nb - 0.008, H), band="red", grain=2)
    # window frame, sill (counter), glass with a speaking hole, lamp inside
    paint.box((bx, by - D / 2 - 0.05, 1.0), (1.1, 0.24, 0.05), band="cream")
    for xx in (-0.52, 0.52):
        paint.box((bx + xx, by - D / 2 - 0.02, 1.5), (0.06, 0.05, 1.0), band="cream")
    paint.box((bx, by - D / 2 - 0.02, 2.0), (1.1, 0.05, 0.06), band="cream")
    gpane = Part("booth_glass", "glass")
    gpane.box((bx, by - D / 2 + 0.01, 1.62), (0.98, 0.01, 0.7))
    rc.bulb(bulbs, (bx, by, 2.05), 0.07)
    wood.box((bx, by - D / 2 + 0.2, 0.98), (1.0, 0.4, 0.04), grain=0)
    # pyramid roof with a gilt finial and bulbs on the eaves
    roofp = Part("booth_roof", "rsteel", tint=(0.06, 0.26, 0.12), bevel=0.0)
    hw, hd = W / 2 + 0.25, D / 2 + 0.25
    apex = Vector((bx, by, H + 0.9))
    eaves = [Vector((bx - hw, by - hd, H)), Vector((bx + hw, by - hd, H)), Vector((bx + hw, by + hd, H)),
             Vector((bx - hw, by + hd, H))]
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in eaves] + [bm.verts.new(apex)]
    lips = [bm.verts.new(v - Vector((0, 0, 0.06))) for v in eaves]
    for k in range(4):
        bm.faces.new((vs[k], vs[(k + 1) % 4], vs[4]))
        bm.faces.new((lips[k], lips[(k + 1) % 4], vs[(k + 1) % 4], vs[k]))
    roofp.from_bmesh(bm, grain=2)
    gilt.sphere(apex + Vector((0, 0, 0.08)), 0.08, seg=10, rings=6)
    gilt.cyl(apex + Vector((0, 0, 0.3)), 0.02, 0.002, 0.35, seg=6)
    for k in range(4):
        a, b = eaves[k], eaves[(k + 1) % 4]
        n = 7
        for j in range(n):
            rc.bulb(bulbs, a.lerp(b, (j + 0.5) / n) - Vector((0, 0, 0.1)), 0.04)
    cp.sign(paint, paint, "Kasse", state.font("alegreya_sc"), (bx, by - D / 2 - 0.05, 2.18), 0.9, 0.22,
            depth=0.03, board_band="cream", text_band="red", board_shape="rect", text_size=0.15,
            text_depth=0.01, max_fill=0.8)
    # ticket window grille: bars in front of the pane, a round speaking grille, a brass money dish
    iron = Part("booth_iron", "blackmetal")
    yg = by - D / 2 - 0.03
    for j in range(13):
        xx = bx - 0.46 + 0.92 * j / 12
        rod(iron, (xx, yg, 1.28), (xx, yg, 1.96), 0.0055, seg=4 if lite else 6)
    for z in (1.30, 1.94):
        iron.box((bx, yg, z), (0.96, 0.014, 0.02))
    if not lite:
        # arched top rail with short radial bars (the grille's crown)
        for j in range(9):
            a = math.pi * (j + 0.5) / 9
            p = Vector((bx + 0.44 * math.cos(a), yg, 1.72 + 0.2 * math.sin(a)))
            rod(iron, (bx, yg, 1.72), tuple(p), 0.004, seg=4)
    brass = Part("booth_brass", "brass")
    brass.torus((bx, by - D / 2 - 0.004, 1.45), 0.075, 0.009, seg=8 if lite else 16, tseg=4 if lite else 6,
                rot=(math.pi / 2, 0, 0))
    if not lite:
        for j in range(5):
            xx = bx - 0.05 + 0.1 * j / 4
            h = math.sqrt(max(0.0, 0.075 ** 2 - (xx - bx) ** 2))
            rod(brass, (xx, by - D / 2 - 0.004, 1.45 - h), (xx, by - D / 2 - 0.004, 1.45 + h), 0.003, seg=4)
    brass.lathe([(0.001, 1.030), (0.10, 1.030), (0.13, 1.045), (0.125, 1.05)], seg=8 if lite else 16,
                M=Matrix.Translation((bx, by - D / 2 - 0.08, 0)))
    # posters on both side walls and the painted price board under the window
    xl, xr = bx - W / 2 - 0.02, bx + W / 2 + 0.02
    rc.picture("booth_poster_l", "poster_riesenrad",
               [(xl, by + 0.3, 1.0), (xl, by - 0.3, 1.0), (xl, by - 0.3, 1.9), (xl, by + 0.3, 1.9)])
    rc.picture("booth_poster_r", "poster_nachtmarkt",
               [(xr, by - 0.3, 1.0), (xr, by + 0.3, 1.0), (xr, by + 0.3, 1.9), (xr, by - 0.3, 1.9)])
    yp = by - D / 2 - 0.022
    rc.picture("booth_prices", "price_board",
               [(bx - 0.42, yp, 0.46), (bx + 0.42, yp, 0.46), (bx + 0.42, yp, 0.83), (bx - 0.42, yp, 0.83)])
    # poster frames: thin dark battens round each picture
    for (x0, y0_, x1_, y1_, z0, z1) in ((xl, by - 0.31, xl, by + 0.31, 0.99, 1.91),
                                         (xr, by - 0.31, xr, by + 0.31, 0.99, 1.91)):
        for z in (z0, z1):
            wood.box((x0, by, z), (0.02, 0.64, 0.025), tint="dark", grain=1)
        for yy in (y0_, y1_):
            wood.box((x0, yy, (z0 + z1) / 2), (0.02, 0.025, z1 - z0), tint="dark", grain=2)

    # queue rails: a lane of red steel rails from the entrance sign out toward the square, and a
    # short rail that keeps the ticket queue along the booth front
    qx = 0.85
    y_s, y_e = -3.35, -7.2
    for sx in (-1, 1):
        xx = sx * qx
        posts = [y_s + (y_e - y_s) * k / 4 for k in range(5)]
        for yy in posts:
            rod(red, (xx, yy, 0.0), (xx, yy, 1.0), 0.028, seg=6)
            gilt.sphere((xx, yy, 1.03), 0.04, seg=6 if lite else 10, rings=4 if lite else 6)
            red.cyl((xx, yy, 0.012), 0.09, 0.09, 0.025, seg=8 if lite else 12)
        for z in (0.55, 0.98):
            rod(red, (xx, y_s, z), (xx, y_e, z), 0.022, seg=6)
    for xx in (bx - 0.95, bx - 0.1, bx + 0.75):
        rod(red, (xx, by - D / 2 - 0.95, 0.0), (xx, by - D / 2 - 0.95, 1.0), 0.028, seg=6)
        gilt.sphere((xx, by - D / 2 - 0.95, 1.03), 0.04, seg=6 if lite else 10, rings=4 if lite else 6)
        red.cyl((xx, by - D / 2 - 0.95, 0.012), 0.09, 0.09, 0.025, seg=8 if lite else 12)
    for z in (0.55, 0.98):
        rod(red, (bx - 0.95, by - D / 2 - 0.95, z), (bx + 0.75, by - D / 2 - 0.95, z), 0.022, seg=6)

    # snow on the booth roof
    bm = bmesh.new()
    sv = [bm.verts.new(v + Vector((0, 0, 0.05))) for v in eaves] + [bm.verts.new(apex + Vector((0, 0, 0.05)))]
    for k in range(4):
        bm.faces.new((sv[k], sv[(k + 1) % 4], sv[4]))
    snow.from_bmesh(bm, grain=2)
    return rc.finish_all([st, darks, red, wood, sleepers, paint, gilt, bulbs, gpane, roofp, snow, iron, brass])


def build(lite):
    wheel = node("rot_wheel", (0, 0, HUB))
    build_wheel(lite, wheel)
    for i in range(N):
        a = gondola_angle(i)
        g = node(f"gondola_{i}", tuple(P(RO, a, 0)), parent=wheel)
        build_gondola(i, g, lite)
        if i == 0:
            # a rider leaning to the front pane: eye 1.32 m above the floor and 0.20 m below the
            # window head, 0.20 m back from the pane on the line to the market (18.5 deg off the
            # front axis for this layout). From there the glass covers +45 deg to -76 deg of pitch
            # and +-63 deg round the pane centre, so the engine's 42 deg camera sees only glass and
            # the market from the bottom of the wheel to the top (-41 deg to the market centre).
            m = market_in_local()
            d = Vector((m.x, m.y, 0)).normalized()
            face = Vector((0, -0.775 * GS, 0))
            eye = face - d * 0.20
            node("gondola_seat_0", tuple(P(RO, a, 0) + Vector((eye.x, eye.y, -1.15))), parent=g)
    build_frame(lite)
    node("light_0", (0, -3.4, 3.2))
    node("light_1", (-4.1, -5.2, 2.6))
    # a warm wash on the wheel face from in front of the hub (the Cycles preview's hub glow):
    # without it the cream steel reads black against the night sky in the browser
    node("light_2", (0, -3.2, HUB))
    node("cam_target", (0, 0, 11.0))
    export_cam = node("cam_view", (9.0, -31.0, 4.5))
    d = Vector((0, 0, 11.0)) - Vector((9.0, -31.0, 4.5))
    export_cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return rc.mesh_objs()


def market_strings(y=-13.0, span=34.0, z=4.6):
    """Render-only: a couple of market light strings and posts in the foreground."""
    env = state.env_collection()
    bulbs = Part("env_bulbs", "bulb_warm")
    wire = Part("env_wire", "wire")
    posts = Part("env_posts", "rsteel", tint=(0.08, 0.08, 0.08), bevel=0.0)
    xs = [-span / 2 + span * k / 4 for k in range(5)]
    for x in xs:
        rod(posts, (x, y, 0), (x, y, z + 0.3), 0.06, seg=8)
    cp.bulb_string(bulbs, wire, [(x, y, z) for x in xs], sag=0.7, spacing=0.55, bulb_r=0.05)
    cp.bulb_string(bulbs, wire, [(x, y + 6.0, z + 0.4) for x in xs], sag=0.8, spacing=0.6, bulb_r=0.05)
    for p in (bulbs, wire, posts):
        p.finish(env)


# where the market centre lies in this model's frame (layout.json: Riesenrad at [-22, -17],
# rotY 0.65; the engine's ride camera looks at three.js (0, 1.5, -2))
PLACE = (-22.0, -17.0, 0.65)
MARKET_LOOK = (0.0, 1.5, -2.0)


def market_in_local():
    px, pz, ry = PLACE
    wx, wy, wz = MARKET_LOOK[0] - px, MARKET_LOOK[1], MARKET_LOOK[2] - pz
    lx = wx * math.cos(ry) - wz * math.sin(ry)
    lz = wx * math.sin(ry) + wz * math.cos(ry)
    return Vector((lx, -lz, wy))         # three.js local (x, y, z) -> Blender (x, -z, y)


def turn_wheel(angle):
    """Render-only pose: turn rot_wheel about the axle and keep every gondola hanging upright."""
    rc.bpy.data.objects["rot_wheel"].rotation_euler = (0, angle, 0)
    for i in range(N):
        rc.bpy.data.objects[f"gondola_{i}"].rotation_euler = (0, -angle, 0)
    rc.bpy.context.view_layer.update()


def market_standins():
    """Render-only: warm stall glows and light strings where the market is, for the ride view."""
    m = market_in_local()
    d = Vector((m.x, m.y, 0)).normalized()
    side = Vector((-d.y, d.x, 0))
    env = state.env_collection()
    bulbs = Part("env_mkt_bulbs", "bulb_warm")
    wire = Part("env_mkt_wire", "wire")
    roofs = Part("env_mkt_roofs", "wood", tint="soot")
    for k, off in enumerate((-9, -3, 3, 9)):
        c = Vector((m.x, m.y, 0)) + side * off + d * (2.0 * (k % 2))
        pts = [c + side * u - d * 6 + Vector((0, 0, 4.2)) for u in (-3, 3)]
        cp.bulb_string(bulbs, wire, [tuple(p) for p in pts], sag=0.5, spacing=0.5, bulb_r=0.06)
        for j, u in enumerate((-6, 0, 6)):
            b = c + d * u + side * 2.5
            roofs.box(tuple(b + Vector((0, 0, 1.3))), (3.0, 2.4, 2.6))
            render.add_light(f"env_mkt_{k}_{j}", 'POINT', tuple(b + Vector((0, 0, 1.8)) - d * 1.4), 350, size=0.6)
    for p in (bulbs, wire, roofs):
        p.finish(env)


def preview(objs):
    pose = os.environ.get("NM_POSE", "")
    for o in objs:
        if o.name.startswith("snow_"):
            o.hide_render = True
    render.lights_at_markers(energy=260)
    render.add_light("env_warm_l", 'POINT', (-9, -9, 3.0), 700, size=1.0)
    render.add_light("env_warm_r", 'POINT', (8, -10, 3.5), 500, size=1.0, color=(1.0, 0.55, 0.3))
    render.add_light("env_rim", 'AREA', (6, 14, 18), 3000, color=(0.55, 0.65, 1.0), size=10,
                     rot=(math.radians(-60), 0, math.radians(20)))
    if pose == "seat":
        # gondola_0 carried to the top; the camera sits at gondola_seat_0 and looks at the market
        turn_wheel(math.pi)
        market_standins()
        eye = rc.bpy.data.objects["gondola_seat_0"].matrix_world.translation.copy()
        return render.camera(tuple(eye), tuple(market_in_local()), lens=26)   # the engine camera: 42 deg vertical
    market_strings()
    render.add_light("env_hubglow", 'POINT', (0, -3.2, HUB), 900, size=1.5)
    if pose == "turned":
        # a quarter turn, seen from the side, to show the gondolas swinging clear between the rims
        turn_wheel(math.radians(-90))
        return render.camera((31.0, -21.0, 5.5), (0.0, 0.0, 12.8), lens=27)
    return render.camera((13.8, -30.5, 1.8), (-0.8, 0, 11.9), lens=24)


if __name__ == "__main__":
    rc.run(NAME, build, preview, seed=26, ground=160)
