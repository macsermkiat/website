"""Musikpavillon (landmark: Music). An octagonal Victorian bandstand, 7.4 m across.

A raised plank deck on a painted plinth with diamond lattice panels, front steps with iron
hand rails, eight cast-iron columns with flared capitals, fretwork spandrels between them,
iron railings on seven sides, a frieze with a scalloped valance and a gilt lyre over the
steps, a boarded ceiling, a striped bell roof with a louvred lantern, gilt finial and lyre
vane, bulbs on the eaves and hips, and fir garlands with baubles across the front.

Nodes: slot_sax, slot_piano, slot_bass, slot_drums (on the deck; each slot's local -Y is the
way the player faces, which matches the instr_* files), light_0/1 (stage wash), bulbs_*,
snow_roof, cam_view/cam_target. Front (the steps) faces -Y.

    /home/claude/tools/bpy-venv/bin/python blender/rides/bandstand.py [--no-render] [--no-lite]
The preview places the four instruments (blender/rides/instruments.py) at the slots.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rcommon as rc  # noqa: E402
from rcommon import TAU, Part, node, rod, side_M, state  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import render  # noqa: E402

NAME = "bandstand"
RC0 = 3.7                       # deck corner radius
A = RC0 * math.cos(math.pi / 8)  # deck apothem (3.42)
DECK = 0.95
RCOL = 3.45                     # column corner radius
ZC = 3.35                       # column top
GREEN = (0.05, 0.19, 0.10)
CREAM = (0.92, 0.86, 0.72)
RED = (0.58, 0.05, 0.05)
FRONT = -math.pi / 2

SLOTS = {  # name: (x, y, facing direction)
    "slot_sax": (0.9, -1.0, (-0.25, -1.0)),
    "slot_piano": (-2.05, 0.35, (-1.0, 0.0)),
    "slot_bass": (-0.55, 1.35, (0.25, -1.0)),
    "slot_drums": (1.45, 1.35, (-0.35, -1.0)),
}


def corner(k, r=RC0):
    a = math.pi / 8 + TAU * k / 8
    return Vector((r * math.cos(a), r * math.sin(a), 0))


def side_angle(k):
    """Outward normal angle of side k (between corner k and k+1)."""
    return math.pi / 4 + TAU * k / 8   # sides face 45, 90, ... ; side 5 faces -Y (front)


FRONT_SIDE = 5   # side_angle(5) = 45 + 225 = 270 deg = -Y


def slot_yaw(d):
    return math.atan2(d[0], -d[1])


def x_extent(y, a=A):
    return min(a, a * math.sqrt(2) - abs(y))


def build(lite):
    paint = Part("bs_paint", "paint", bevel=0.0)
    floor = Part("bs_floor", "wood", tint="honey", bevel=0.0)
    ceil = Part("bs_ceiling", "wood", tint="pine", bevel=0.0)
    iron = Part("bs_iron", "rsteel", tint=GREEN, bevel=0.0)
    fret = Part("bs_fret", "rsteel", tint=CREAM, bevel=0.0)
    roof = Part("bs_roof", "rsteel", bevel=0.0)
    gilt = Part("bs_gilt", "gilt")
    bulbs = Part("bulbs_bandstand", "bulb_warm")
    fir = Part("bs_fir", "fir")
    beads = {"ornament_red": Part("bs_beads_red", "ornament_red"), "ornament_gold": Part("bs_beads_gold", "ornament_gold")}
    snow = Part("snow_roof", "snow")
    wire = Part("bs_wire", "wire")

    # ------------------------------------------------ plinth with lattice panels
    for k in range(8):
        a = side_angle(k)
        c0, c1 = corner(k), corner(k + 1)
        mid = (c0 + c1) / 2
        L = (c1 - c0).length
        Ms = side_M(mid + Vector((0, 0, (DECK - 0.1) / 2)), a)
        h = DECK - 0.1
        # dark backing, frame
        paint.mbox(Ms @ Matrix.Translation((0, 0, -0.06)), (L, h, 0.02), band="black")
        for yy in (h / 2 - 0.05, -h / 2 + 0.05):
            paint.mbox(Ms @ Matrix.Translation((0, yy, 0)), (L, 0.1, 0.05), band="green", grain=0)
        for xx in (-L / 2 + 0.05, 0.0, L / 2 - 0.05):
            paint.mbox(Ms @ Matrix.Translation((xx, 0, 0)), (0.1, h, 0.05), band="green", grain=1)
        if k == FRONT_SIDE:
            continue
        if lite:
            paint.mbox(Ms @ Matrix.Translation((0, 0, -0.03)), (L - 0.1, h - 0.1, 0.01), band="white", grain=0)
            continue
        # diamond lattice inside each half panel
        sp = 0.26 if lite else 0.19
        for half in (-1, 1):
            x0, x1 = (-L / 2 + 0.1, -0.05) if half < 0 else (0.05, L / 2 - 0.1)
            z0, z1 = -h / 2 + 0.1, h / 2 - 0.1
            for sgn in (-1, 1):
                cmin = min(x0 - z1, x0 + z0, x0 - z0, x0 + z1)
                cmax = max(x1 - z0, x1 + z1, x1 - z1, x1 + z0)
                c = cmin + sp / 2
                while c < cmax:
                    # line x = c + sgn*z clipped to the box
                    pts = []
                    for z in (z0, z1):
                        x = c + sgn * z
                        if x0 <= x <= x1:
                            pts.append((x, z))
                    for x in (x0, x1):
                        z = (x - c) * sgn
                        if z0 <= z <= z1:
                            pts.append((x, z))
                    if len(pts) >= 2:
                        p0, p1 = pts[0], pts[1]
                        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 0.05:
                            P0 = Ms @ Vector((p0[0], p0[1], -0.02 + 0.012 * sgn))
                            P1 = Ms @ Vector((p1[0], p1[1], -0.02 + 0.012 * sgn))
                            n = Vector((math.cos(a), math.sin(a), 0))
                            paint.slab(P0, P1, 0.035, 0.012, up=n.cross(P1 - P0), band="white")
                    c += sp
    # ------------------------------------------------ deck
    y = -A
    while y < A - 1e-4:
        w = min(0.14, A - y)
        yc = y + w / 2
        xe = min(x_extent(y), x_extent(y + w))
        floor.box((0, yc, DECK - 0.02), (2 * xe, w - 0.006, 0.04), grain=0, jitter=0.02)
        y += w
    for k in range(8):
        a = side_angle(k)
        c0, c1 = corner(k, RC0 + 0.03), corner(k + 1, RC0 + 0.03)
        mid = (c0 + c1) / 2
        L = (c1 - c0).length + 0.03
        paint.mbox(side_M(mid + Vector((0, 0, DECK - 0.07)), a), (L, 0.14, 0.03), band="cream", grain=0)
        paint.mbox(side_M(mid + Vector((0, 0, DECK - 0.05)) + Vector((math.cos(a), math.sin(a), 0)) * 0.02, a),
                   (L, 0.02, 0.01), band="gold", grain=0)
    # ------------------------------------------------ steps at the front
    nst = 5
    rise = DECK / nst
    yfront = -A
    for i in range(nst):
        z = DECK - (i + 1) * rise
        yy = yfront - 0.28 * (i + 0.5) - 0.02
        floor.box((0, yy, z + rise - 0.02), (1.9, 0.3, 0.04), grain=0, tint="oak")
        paint.box((0, yy + 0.13, z + rise / 2), (1.86, 0.02, rise), band="cream")
    for sx in (-1, 1):
        a = Vector((sx * 0.98, yfront - 0.02, DECK))
        b = Vector((sx * 0.98, yfront - 0.28 * nst - 0.02, 0.0))
        paint.slab(a + Vector((0, 0, -0.12)), b + Vector((0, 0.1, 0.06)), 0.26, 0.05, up=(0, 0, 1), band="green")
        # iron hand rails with a scroll at the bottom
        top0 = Vector((sx * 0.98, yfront + 0.05, DECK + 0.9))
        top1 = Vector((sx * 0.98, yfront - 0.28 * nst + 0.05, 0.9))
        rod(iron, top0, top1, 0.022, seg=6)
        for t in (0.0, 0.5, 1.0):
            p = top0.lerp(top1, t)
            rod(iron, p, Vector((p.x, p.y, DECK - (DECK * t))), 0.016, seg=6)
        sc = [top1 + Vector((0, -0.05 * math.sin(u), -0.05 + 0.05 * math.cos(u))) for u in [i * 0.6 for i in range(9)]]
        iron.tube(sc, 0.016, tseg=5)
        gilt.sphere(top0 + Vector((0, 0, 0.03)), 0.035, seg=8, rings=6)
    # ------------------------------------------------ columns, spandrels, railings
    for k in range(8):
        c = corner(k, RCOL)
        prof = [(0.14, DECK), (0.14, DECK + 0.10), (0.11, DECK + 0.13), (0.085, DECK + 0.2), (0.075, DECK + 0.3),
                (0.068, ZC - 0.45), (0.075, ZC - 0.36), (0.09, ZC - 0.33), (0.08, ZC - 0.28), (0.11, ZC - 0.16),
                (0.15, ZC - 0.06), (0.16, ZC)]
        iron.lathe(prof, seg=8 if lite else 12, M=Matrix.Translation(c), smooth=True)
        iron.box(c + Vector((0, 0, ZC + 0.03)), (0.34, 0.34, 0.06), rot=(0, 0, math.pi / 8 + TAU * k / 8))
        if not lite:
            gilt.lathe([(0.078, ZC - 0.36), (0.093, ZC - 0.345), (0.078, ZC - 0.33)], seg=14, M=Matrix.Translation(c))
            gilt.lathe([(0.12, DECK + 0.12), (0.13, DECK + 0.135), (0.11, DECK + 0.15)], seg=14, M=Matrix.Translation(c))
    for k in range(8):
        a = side_angle(k)
        c0, c1 = corner(k, RCOL), corner(k + 1, RCOL)
        mid = (c0 + c1) / 2
        L = (c1 - c0).length - 0.16
        # cast fretwork spandrel: segmental arch with round cut-outs
        Ms = side_M(mid, a)
        top, bot = ZC - 0.02, ZC - 0.55
        outer = [(-L / 2, top), (-L / 2, bot)]
        n = 10 if lite else 18
        for i in range(n + 1):
            t = i / n
            x = -L / 2 + L * t
            z = bot + 0.06 + 0.32 * math.sin(math.pi * t) ** 0.6
            outer.append((x, z))
        outer += [(L / 2, bot), (L / 2, top)]
        outer = [outer[0]] + outer[1:]
        holes = []
        if not lite:
            for i in range(6):
                x = -L / 2 + L * (i + 0.5) / 6
                t = (x + L / 2) / L
                zlow = bot + 0.06 + 0.32 * math.sin(math.pi * t) ** 0.6
                r = min(0.065, (top - zlow) * 0.32)
                if r > 0.03:
                    holes.append([(x + r * math.cos(TAU * j / 10), (top + zlow) / 2 + r * math.sin(TAU * j / 10))
                                  for j in range(10)])
        fret.shape(list(reversed(outer)), holes=holes, depth=0.03, M=Ms)
        # frieze board above, valance below the eave
        paint.mbox(side_M(mid + Vector((0, 0, ZC + 0.14)) + Vector((math.cos(a), math.sin(a), 0)) * 0.1, a),
                   ((corner(k, RCOL + 0.1) - corner(k + 1, RCOL + 0.1)).length + 0.1, 0.24, 0.04), band="red", grain=0)
        # railing (not across the steps)
        if k != FRONT_SIDE:
            h0, h1 = DECK + 0.08, DECK + 0.9
            p0, p1 = c0 + Vector((0, 0, 0)), c1
            dirv = (p1 - p0).normalized()
            q0, q1 = p0 + dirv * 0.12, p1 - dirv * 0.12
            paint.slab(q0 + Vector((0, 0, h1)), q1 + Vector((0, 0, h1)), 0.09, 0.05, up=(0, 0, 1), band="green")
            rod(iron, q0 + Vector((0, 0, h0)), q1 + Vector((0, 0, h0)), 0.018, seg=6)
            rod(iron, q0 + Vector((0, 0, h1 - 0.12)), q1 + Vector((0, 0, h1 - 0.12)), 0.012, seg=5)
            nb = 8 if lite else 14
            for i in range(nb):
                p = q0.lerp(q1, (i + 0.5) / nb)
                rod(iron, p + Vector((0, 0, h0)), p + Vector((0, 0, h1 - 0.02)), 0.009, seg=4)
                if not lite and i % 2 == 0:
                    iron.torus(p + Vector((0, 0, (h0 + h1) / 2 + 0.05)), 0.045, 0.007, seg=8, tseg=3,
                               rot=(math.pi / 2, 0, a + math.pi / 2))
    # ------------------------------------------------ eave, ceiling, roof, lantern
    RE = 4.35
    ZE = ZC + 0.26
    for k in range(8):
        a = side_angle(k)
        c0, c1 = corner(k, RE), corner(k + 1, RE)
        mid = (c0 + c1) / 2
        L = (c1 - c0).length
        # fascia and scalloped valance with round cut-outs
        paint.mbox(side_M(mid + Vector((0, 0, ZE - 0.08)), a), (L, 0.2, 0.035), band="cream", grain=0)
        cp.valance(paint, -L / 2, L / 2, 0, ZE - 0.18, 0.12, 0.1, 6, style="scallop", holes="circle", depth=0.02,
                   band="cream", M=side_M(mid, a))
        paint.mbox(side_M(mid + Vector((0, 0, ZE - 0.02)) + Vector((math.cos(a), math.sin(a), 0)) * 0.02, a),
                   (L, 0.02, 0.012), band="gold", grain=0)
        nbul = 6 if lite else 11
        for i in range(nbul):
            p = c0.lerp(c1, (i + 0.5) / nbul) + Vector((math.cos(a), math.sin(a), 0)) * 0.05
            rc.bulb(bulbs, p + Vector((0, 0, ZE - 0.3)), 0.04)
    # boarded ceiling (radial) under the roof
    nce = 24 if lite else 40
    for i in range(nce):
        am = TAU * (i + 0.5) / nce
        h = math.pi / nce
        r1 = RE - 0.05
        poly = [(0.0, 0.0), (r1, -r1 * math.tan(h)), (r1, r1 * math.tan(h))]
        ceil.shape(poly, depth=0.025, M=Matrix.Translation((0, 0, ZE - 0.02)) @ Euler((0, 0, am)).to_matrix().to_4x4(),
                   grain=0, tint="pine" if i % 2 else "honey")
    # striped bell roof: each of the 8 facets split into 4 strips of red and cream
    prof = [(RE + 0.05, ZE), (RE - 0.2, ZE + 0.10), (RE - 0.65, ZE + 0.30), (RE - 1.2, ZE + 0.62),
            (RE - 1.8, ZE + 1.02), (RE - 2.4, ZE + 1.46), (RE - 2.95, ZE + 1.9), (RE - 3.35, ZE + 2.22)]
    strips = 4
    for k in range(8):
        c0a = math.pi / 8 + TAU * k / 8
        for s in range(strips):
            rings = []
            for (r, z) in prof:
                rr = r / math.cos(math.pi / 8)
                p0 = Vector((rr * math.cos(c0a), rr * math.sin(c0a), z))
                p1 = Vector((rr * math.cos(c0a + TAU / 8), rr * math.sin(c0a + TAU / 8), z))
                rings.append([p0.lerp(p1, s / strips), p0.lerp(p1, (s + 1) / strips)])
            roof.loft(rings, closed=False, smooth=False, grain=2, tint=RED if s % 2 == 0 else CREAM)
        # hip rib with bulbs
        hip = [Vector((r / math.cos(math.pi / 8) * math.cos(c0a), r / math.cos(math.pi / 8) * math.sin(c0a), z + 0.03))
               for r, z in prof]
        gilt.tube(hip, 0.03, tseg=5)
        nb = len(hip) - 1
        for i in range(nb):
            rc.bulb(bulbs, hip[i].lerp(hip[i + 1], 0.5) + Vector((0, 0, 0.06)), 0.04)
        if not lite:
            for i in range(0, len(hip) - 1, 2):
                rc.bulb(bulbs, hip[i] + Vector((0, 0, 0.06)), 0.04)
    # snow on the roof
    snow_prof = [(r - 0.02, z + 0.07) for r, z in prof[1:]]
    snow_prof[0] = (snow_prof[0][0], snow_prof[0][1] - 0.02)
    rc.lathe_poly(snow, snow_prof + [(0.001, prof[-1][1] + 0.12)], 8, flat=False)
    # lantern: octagonal louvred drum, small roof, gilt finial and a lyre vane
    zl0 = ZE + 2.22
    rl = RE - 3.35
    rc.lathe_poly(paint, [(rl, zl0), (rl - 0.05, zl0 + 0.05), (rl - 0.05, zl0 + 0.55), (rl + 0.08, zl0 + 0.6)], 8,
                  band="cream")
    for k in range(8):
        a = side_angle(k)
        rr = (rl - 0.03)
        mid = Vector((rr * math.cos(a), rr * math.sin(a), 0))
        for j in range(4 if lite else 6):
            zz = zl0 + 0.12 + 0.07 * j
            paint.mbox(side_M(mid + Vector((0, 0, zz)), a) @ Euler((0.5, 0, 0)).to_matrix().to_4x4(),
                       (0.55, 0.05, 0.012), band="green", grain=0)
    rc.lathe_poly(roof, [(rl + 0.2, zl0 + 0.6), (rl * 0.5, zl0 + 0.9), (0.05, zl0 + 1.05)], 8, tint=RED)
    ztop = zl0 + 1.05
    gilt.sphere((0, 0, ztop + 0.06), 0.09, seg=12 if lite else 16, rings=8 if lite else 10)
    rod(gilt, (0, 0, ztop + 0.1), (0, 0, ztop + 0.95), 0.018, r2=0.01, seg=8, caps=True)
    lyre(gilt, Vector((0, 0, ztop + 0.55)), 0.9, facing=0.0)
    # gilt lyre over the steps on the frieze
    a = side_angle(FRONT_SIDE)
    lyre(gilt, Vector((0, -(RCOL * math.cos(math.pi / 8) + 0.13), ZC + 0.16)), 0.42, facing=0.0)
    # ------------------------------------------------ fir garlands and bows on the three front sides
    for k in (4, 5, 6):
        c0, c1 = corner(k, RCOL + 0.12), corner(k + 1, RCOL + 0.12)
        z = ZC - 0.1
        cp.fir_garland(fir, beads, c0 + Vector((0, 0, z)), c1 + Vector((0, 0, z)), sag=0.38, radius=0.07,
                       tufts_per_m=6 if lite else 16, bead_every=0.5 if lite else 0.34)
    for k in (4, 5, 6, 7):
        c = corner(k, RCOL + 0.16)
        n = c.normalized()
        Mb = rc.frame_at(c + Vector((0, 0, ZC - 0.1)), Vector((-n.y, n.x, 0)), (0, 0, 1)) @ \
            Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
        beads["ornament_red"].shape([(0, 0), (0.14, 0.07), (0.15, -0.07)], depth=0.02, M=Mb)
        beads["ornament_red"].shape([(0, 0), (-0.15, -0.07), (-0.14, 0.07)], depth=0.02, M=Mb)
        for sx in (-1, 1):
            beads["ornament_red"].shape([(0, 0), (sx * 0.05, -0.25), (sx * 0.09, -0.22)], depth=0.015, M=Mb)
    objs = rc.finish_all([paint, floor, ceil, iron, fret, roof, gilt, bulbs, fir, *beads.values(), snow, wire])
    # ------------------------------------------------ markers
    for name, (x, y, d) in SLOTS.items():
        node(name, (x, y, DECK), rot=(0, 0, slot_yaw(d)))
    node("light_0", (-1.3, -2.3, ZC - 0.25))
    node("light_1", (1.3, -2.3, ZC - 0.25))
    node("cam_target", (0, 0.2, 2.0))
    cv = node("cam_view", (3.0, -9.6, 2.7))
    cv.rotation_euler = (Vector((0, 0.2, 2.0)) - Vector((3.0, -9.6, 2.7))).to_track_quat('-Z', 'Y').to_euler()
    return rc.mesh_objs()


def lyre(part, base, h, facing=0.0):
    """Gilt lyre (arms, crossbar, strings) standing in a vertical plane facing -Y."""
    Rz = Euler((0, 0, facing)).to_matrix()

    def P(x, z):
        return base + Rz @ Vector((x * h, 0, z * h))
    for s in (-1, 1):
        arm = [P(s * 0.04, 0.0), P(s * 0.22, 0.12), P(s * 0.26, 0.42), P(s * 0.18, 0.66), P(s * 0.22, 0.8),
               P(s * 0.3, 0.78)]
        part.tube(arm, 0.035 * h, tseg=5)
    part.tube([P(-0.2, 0.62), P(0.2, 0.62)], 0.03 * h, tseg=5)
    part.tube([P(-0.08, 0.0), P(0.08, 0.0)], 0.04 * h, tseg=5)
    for x in (-0.09, -0.03, 0.03, 0.09):
        rod(part, P(x, 0.03), P(x * 1.4, 0.62), 0.006 * h, seg=4)


def preview(objs):
    import instruments
    for o in objs:
        if o.name.startswith("snow_"):
            o.hide_render = True
    for name, (x, y, d) in SLOTS.items():
        M = Matrix.Translation((x, y, DECK)) @ Euler((0, 0, slot_yaw(d))).to_matrix().to_4x4()
        if name == "slot_sax":      # no player in the preview: the sax rests on a stand
            instruments.sax_on_stand(M)
        else:
            instruments.place_in(name.replace("slot_", ""), M)
    render.lights_at_markers(energy=160)
    render.add_light("env_ceiling", 'AREA', (0, 0, ZC + 0.1), 120, size=2.5, rot=(math.pi, 0, 0))
    spot = render.add_light("env_spot_l", 'SPOT', (-2.5, -6.5, 5.0), 900, color=(1.0, 0.78, 0.55), size=0.3)
    spot.data.spot_size = math.radians(38)
    spot.data.spot_blend = 0.6
    spot.rotation_euler = (Vector((-0.2, 0.3, 1.5)) - spot.location).to_track_quat('-Z', 'Y').to_euler()
    spot2 = render.add_light("env_spot_r", 'SPOT', (3.5, -6.0, 5.0), 600, color=(1.0, 0.65, 0.7), size=0.3)
    spot2.data.spot_size = math.radians(34)
    spot2.data.spot_blend = 0.6
    spot2.rotation_euler = (Vector((0.8, 0.8, 1.4)) - spot2.location).to_track_quat('-Z', 'Y').to_euler()
    render.add_light("env_rim", 'AREA', (6, 7, 7), 900, color=(0.55, 0.65, 1.0), size=5,
                     rot=(math.radians(-50), 0, math.radians(40)))
    return render.camera((-4.8, -11.0, 3.3), (0.1, 0.3, 2.55), lens=26)


if __name__ == "__main__":
    rc.run(NAME, build, preview, seed=8, ground=50)
