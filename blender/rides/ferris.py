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
HUB = 14.55         # axle height
RO = 11.2           # outer ring = gondola axles
RI = 10.05          # inner ring
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


def gondola_angle(i):
    return -math.pi / 2 + TAU * i / N


# ------------------------------------------------------------------ wheel (rotating)
def build_wheel(lite, wheel):
    st = Part("wheel_steel", "rsteel", tint=CREAM, bevel=0.0, var=0.05)
    gilt = Part("wheel_gilt", "gilt", var=0.03)
    bulbs = Part("bulbs_wheel", "bulb_warm")
    dark = Part("wheel_hub", "rsteel", tint=(0.55, 0.06, 0.05), bevel=0.0)
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
        # spokes: radial main spokes to each gondola axle, crossing tension rods between
        yf = math.copysign(YR + 0.62, y)
        for i in range(N):
            a = gondola_angle(i)
            rod(st, P(1.05, a, yf), P(RI, a, y), 0.06, seg=rs)
            am = a + math.pi / N
            if not lite or i % 2 == 0:
                rod(st, P(1.05, a + 0.22, yf), P(RI, am, y), 0.026, seg=4)
                rod(st, P(1.05, a + TAU / N - 0.22, yf), P(RI, am, y), 0.026, seg=4)
        # bulbs: outer rail and along each main spoke (the star seen from the market)
        nb = 36 if lite else 96
        for k in range(nb):
            a = TAU * (k + 0.5) / nb
            rc.bulb(bulbs, P(RO + 0.17, a, y), 0.05)
        per = 4 if lite else 13
        for i in range(N):
            a = gondola_angle(i)
            for j in range(per):
                r = 1.8 + (RI - 2.3) * j / (per - 1)
                t = (r - 1.05) / (RI - 1.05)
                yy = yf + (y - yf) * t
                p = P(r, a, yy) + Vector((0, math.copysign(0.07, y), 0))
                rc.bulb(bulbs, p, 0.042)
    # transverse members: gondola axles, inner ties, X braces on the outer ring
    for i in range(N):
        a = gondola_angle(i)
        a2 = gondola_angle(i + 1)
        rod(st, P(RO, a, -YR - 0.05), P(RO, a, YR + 0.05), 0.075, seg=rs + 2)
        rod(st, P(RI, a, -YR), P(RI, a, YR), 0.05, seg=rs)
        am = (a + a2) / 2
        rod(st, P(RO, am, -YR), P(RO, am, YR), 0.04, seg=rs)
        if not lite:
            rod(st, P(RO, a, -YR), P(RO, am, YR), 0.028, seg=4)
            rod(st, P(RO, a, YR), P(RO, am, -YR), 0.028, seg=4)
            rod(st, P(RO, am, -YR), P(RO, a2, YR), 0.028, seg=4)
            rod(st, P(RO, am, YR), P(RO, a2, -YR), 0.028, seg=4)
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
        # gilt sunburst on the hub face
        Ms = Matrix.Translation((0, s * (hl + 0.03), HUB)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
        gilt.shape(geo.star_polygon(0, 0, 1.12, 0.52, 16), depth=0.04, M=Ms)
        gilt.shape(geo.star_polygon(0, 0, 0.62, 0.34, 8, rot=math.pi / 8),
                   depth=0.06, M=Ms @ Matrix.Translation((0, 0, -s * 0.03)))
        for k in range(12 if lite else 24):
            a = TAU * k / (12 if lite else 24)
            rc.bulb(bulbs, P(1.35, a, s * (hl + 0.05)), 0.05)
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
    glass = Part(f"gond{i}_glass", "glass")
    wood = Part(f"gond{i}_wood", "wood", tint="honey", bevel=0.0)
    bulbs = Part(f"bulbs_g{i}", "bulb_warm")
    snow = Part(f"snow_g{i}", "snow")
    # hanger yoke from the axle down to the roof
    rod(trim, O + Vector((0, -YR / GS + 0.05, 0)), O + Vector((0, YR / GS - 0.05, 0)), 0.062, seg=8)
    for s in (-1, 1):
        rod(trim, O + Vector((0, s * 0.62, 0)), O + Vector((0, s * 0.16, -0.30)), 0.028, seg=5)
    rod(trim, O + Vector((0, 0, -0.02)), O + Vector((0, 0, -0.30)), 0.03, seg=5)
    # roof (ogee, octagonal), header, glass band, sill, lower body
    roof = [(0.10, -0.25), (0.20, -0.29), (0.44, -0.39), (0.68, -0.49), (0.88, -0.60),
            (0.935, -0.645), (0.935, -0.685), (0.80, -0.70)]
    if lite:
        roof = [(0.10, -0.25), (0.44, -0.39), (0.88, -0.60), (0.935, -0.685), (0.80, -0.70)]
    rc.lathe_poly(body, roof, seg, M=T)
    rc.lathe_poly(trim, [(0.80, -0.70), (0.80, -0.82)], seg, M=T)
    rc.lathe_poly(gilt, [(0.815, -0.80), (0.822, -0.81), (0.815, -0.825)], seg, M=T)
    rc.lathe_poly(glass, [(0.775, -0.82), (0.775, -1.42)], seg, M=T)
    rc.lathe_poly(trim, [(0.84, -1.42), (0.84, -1.47), (0.80, -1.47)], seg, M=T)
    lower = [(0.80, -1.47), (0.80, -1.95), (0.75, -2.08), (0.62, -2.20), (0.40, -2.29), (0.001, -2.33)]
    rc.lathe_poly(body, lower, seg, M=T)
    if not lite:
        rc.lathe_poly(gilt, [(0.805, -1.70), (0.81, -1.71), (0.805, -1.72)], seg, M=T)
    gilt.sphere(O + Vector((0, 0, -0.22)), 0.07, seg=6 if lite else 12, rings=4 if lite else 8)
    gilt.cyl(O + Vector((0, 0, -2.36)), 0.05, 0.001, 0.08, seg=8)
    # window posts at the octagon corners (corner angles: k*45 deg + 22.5)
    Rc = 0.80 / math.cos(math.pi / seg)
    for k in range(seg):
        a = TAU * k / seg + math.pi / seg
        trim.box(O + Vector((Rc * math.cos(a), Rc * math.sin(a), -1.12)), (0.055, 0.055, 0.62),
                 rot=(0, 0, a))
    # cabin interior: floor, two benches facing each other, ceiling lamp
    wood.cyl(O + Vector((0, 0, -1.99)), 0.76, 0.76, 0.03, seg=8, rot=(0, 0, math.pi / 8))
    if not lite:
        for s in (-1, 1):
            wood.box(O + Vector((0, s * 0.50, -1.62)), (0.95, 0.34, 0.05), grain=0)
            wood.box(O + Vector((0, s * 0.70, -1.40)), (0.95, 0.05, 0.40), rot=(s * 0.12, 0, 0), grain=0)
            body.box(O + Vector((0, s * 0.50, -1.82)), (0.9, 0.3, 0.32))
        # door on the +X face: gilt frame and handle
        for dy in (-0.26, 0.26):
            gilt.box(O + Vector((0.805, dy, -1.72)), (0.012, 0.022, 0.46))
        gilt.box(O + Vector((0.805, 0, -1.96)), (0.012, 0.52, 0.02))
        gilt.cyl(O + Vector((0.83, 0.18, -1.62)), 0.012, 0.012, 0.06, seg=6, rot=(0, math.pi / 2, 0))
        # gilt stars on the front, back and outer panels
        for a in (math.pi / 2, -math.pi / 2, math.pi):
            n = Vector((math.cos(a), math.sin(a), 0))
            Ms = Matrix.Translation(O + n * 0.81 + Vector((0, 0, -1.72))) @ \
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
    for sx in (-1, 1):
        darks.box((sx * 7.6, 0, 0.62), (0.22, 2 * FY, 0.30))
        rod(st, feet[(sx, -1)] + Vector((0, 0.3, 0.2)), Vector((sx * 4.2, 0, 7.6)), 0.05, seg=6)
        rod(st, feet[(sx, 1)] + Vector((0, -0.3, 0.2)), Vector((sx * 4.2, 0, 7.6)), 0.05, seg=6)
    # axle and bearing blocks at the apex
    darks.cyl((0, 0, HUB), 0.3, 0.3, 2 * ay + 0.5, seg=12 if lite else 20, rot=(math.pi / 2, 0, 0))
    for sy in (-1, 1):
        darks.box((0, sy * ay, HUB - 0.12), (0.95, 0.5, 0.7))
        red.cyl((0, sy * (ay + 0.3), HUB), 0.42, 0.42, 0.1, seg=16, rot=(math.pi / 2, 0, 0))
        rc.bulb(bulbs, (0, sy * (ay + 0.4), HUB + 0.62), 0.07)

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
    # railings on the deck sides and the stair
    for sx in (-1, 1):
        xx = sx * (x1 - 0.05)
        for yy in (y0 + 0.05, (y0 + y1) / 2, y1 - 0.05):
            rod(red, (xx, yy, DECK), (xx, yy, DECK + 1.0), 0.03, seg=6)
        for z in (DECK + 0.5, DECK + 1.0):
            rod(red, (xx, y0 + 0.05, z), (xx, y1 - 0.05, z), 0.022 if z < 1 else 0.028, seg=6)
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
    # snow on the booth roof
    bm = bmesh.new()
    sv = [bm.verts.new(v + Vector((0, 0, 0.05))) for v in eaves] + [bm.verts.new(apex + Vector((0, 0, 0.05)))]
    for k in range(4):
        bm.faces.new((sv[k], sv[(k + 1) % 4], sv[4]))
    snow.from_bmesh(bm, grain=2)
    return rc.finish_all([st, darks, red, wood, sleepers, paint, gilt, bulbs, gpane, roofp, snow])


def build(lite):
    wheel = node("rot_wheel", (0, 0, HUB))
    build_wheel(lite, wheel)
    for i in range(N):
        a = gondola_angle(i)
        g = node(f"gondola_{i}", tuple(P(RO, a, 0)), parent=wheel)
        build_gondola(i, g, lite)
        if i == 0:
            node("gondola_seat_0", tuple(P(RO, a, 0) + Vector((0, -0.3, -1.45))), parent=g)
    build_frame(lite)
    node("light_0", (0, -3.4, 3.2))
    node("light_1", (-4.1, -5.2, 2.6))
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


def preview(objs):
    for o in objs:
        if o.name.startswith("snow_"):
            o.hide_render = True
    market_strings()
    render.lights_at_markers(energy=260)
    render.add_light("env_hubglow", 'POINT', (0, -3.2, HUB), 900, size=1.5)
    render.add_light("env_warm_l", 'POINT', (-9, -9, 3.0), 700, size=1.0)
    render.add_light("env_warm_r", 'POINT', (8, -10, 3.5), 500, size=1.0, color=(1.0, 0.55, 0.3))
    render.add_light("env_rim", 'AREA', (6, 14, 18), 3000, color=(0.55, 0.65, 1.0), size=10,
                     rot=(math.radians(-60), 0, math.radians(20)))
    return render.camera((13.8, -30.5, 1.8), (-0.8, 0, 11.9), lens=24)


if __name__ == "__main__":
    rc.run(NAME, build, preview, seed=26, ground=160)
