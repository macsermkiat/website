"""Bierstand (section: Projects).

A wide Bavarian bar: light spruce board-and-batten walls, a broad low shingled roof with a
deep overhang, blue-and-white Rauten pennants all along the eaves, posts ringed blue and
white like a maypole, knee braces, a bar whose front is four half-barrels with iron hoops
under a thick oak top, and a crest sign "Bier vom Fass" standing on the front slope.

    /home/claude/tools/bpy-venv/bin/python blender/stalls/bier.py [--no-render] [--no-lite]
Outputs site/public/models/stall_bier.glb and stall_bier.lite.glb.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_bier"
W, D = 4.2, 2.6
EAVE, RIDGE = 2.62, 3.4
BARREL_H, R_END, R_BELLY = 0.98, 0.33, 0.39


def half_barrel(staves, hoops, cx, cy, lite):
    """Front half of a standing barrel (faces -Y) made of separate staves plus iron hoops."""
    n = 7 if lite else 11
    rings = 5 if lite else 9
    gap = 0.012
    for k in range(n):
        t0 = math.pi + math.pi * k / n
        t1 = math.pi + math.pi * (k + 1) / n
        ring_pts = []
        for i in range(rings + 1):
            z = BARREL_H * i / rings + 0.02
            r = R_END + (R_BELLY - R_END) * math.sin(math.pi * i / rings)
            ga = gap / r / 2
            row = []
            for t in (t0 + ga, (t0 + t1) / 2, t1 - ga):
                row.append((cx + r * math.cos(t), cy + r * math.sin(t), z))
            ring_pts.append(row)
        staves.loft(ring_pts, closed=False, grain=2, smooth=False,
                    tint=state.rng.choice(["oak", "oak", "honey", "dark"]), var=0.12)
    for z in (0.1, 0.32, 0.7, 0.9):
        r = R_END + (R_BELLY - R_END) * math.sin(math.pi * (z - 0.02) / BARREL_H) + 0.006
        hoops.torus((cx, cy, z), r, 0.009, seg=10 if lite else 16,
                    tseg=4, rot=(0, 0, math.pi), arc=math.pi)


# Rauten pattern UV offset: one lozenge centred at the top middle of every pennant
RAUTEN_UV = (0.125, 0.0)


def pennants(P, a, b, z, n, lite, drop=0.3, width=0.2):
    """Triangular Rauten pennants hung from a line a->b (points at the fascia bottom). P is the
    'rauten' pattern Part: three to four big lozenges per pennant that survive mipmapping."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    nrm = d.cross(Vector((0, 0, 1))).normalized()
    for i in range(n):
        p = a.lerp(b, (i + 0.5) / n)
        sw = state.rng.uniform(-0.06, 0.06)
        basis = Matrix((d, Vector((0, 0, 1)), -nrm)).transposed().to_4x4()
        # hung with the tips pulled a little in under the eave: the faces look slightly up, so
        # the sky fill and the bulbs above reach them
        M = Matrix.Translation((p.x, p.y, z)) @ basis @ Euler((sw - 0.22, 0, 0)).to_matrix().to_4x4()
        tri = [(-width / 2, 0), (0, -drop), (width / 2, 0)]
        P.shape(tri, depth=0.012, M=M, uv_off=RAUTEN_UV)


def build(lite):
    h = Hut("bier", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='x', ov_eave=0.55, ov_gable=0.32,
            wall="batten", wall_tint="pine", frame_tint="honey", roof_tint="shingle", inner_tint="pine",
            counter_tint="oak", counter_depth=0.82, counter_over=0.46, plank_w=0.17, bulbs_sides=True,
            bulb_spacing=0.24, front_posts=[-W / 2 + 0.05, W / 2 - 0.05])
    yF = h.yF
    h.build_carcass()
    h.build_counter(brackets=0)
    h.build_shelves()
    RA = h.part("rauten", "rauten", var=0.03)      # dedicated two-colour lozenge texture
    h.build_roof(cover="shingles", fascia_part=RA)
    h.build_snow()
    P = h.paint

    # ------------------------------------------------------------ barrel front
    staves = h.part("barrels", "wood", var=0.12)
    for cx in (-1.44, -0.48, 0.48, 1.44):
        half_barrel(staves, h.iron, cx, yF - 0.06, lite)
    # plinth board the barrels stand on
    h.frame.box((0, yF - 0.2, 0.02), (W - 0.1, 0.48, 0.04), tint="dark")

    # ------------------------------------------------------------ maypole posts + knee braces
    for x in h.front_posts:
        z = COUNTER_TOP + 0.02
        k = 0
        while z < 2.18:
            hh = min(0.16, 2.2 - z)
            P.box((x, yF + 0.05, z + hh / 2), (0.112, 0.112, hh - 0.004), band="blue" if k % 2 == 0 else "white")
            z += hh
            k += 1
        s = 1 if x < 0 else -1
        h.frame.slab((x + s * 0.04, yF + 0.02, 1.85), (x + s * 0.45, yF + 0.02, 2.24), 0.09, 0.08,
                     up=(0, -1, 0), tint="honey")
    # ------------------------------------------------------------ pennants along the eaves
    sl = h.front_slope
    fz = sl.point(0, 0, -0.03).z - 0.07
    ye = sl.point(0, 0).y - 0.03
    n = int((sl.a1 - sl.a0) / 0.23)
    pennants(RA, (sl.a0 + 0.02, ye, 0), (sl.a1 - 0.02, ye, 0), fz, n, lite)
    # along the gable rakes (short run near the front eave on each side)
    Mr = Euler((0, 0, math.pi / 2)).to_matrix().to_4x4() @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    for sgn in (-1, 1):
        a = sl.a0 if sgn < 0 else sl.a1
        p0 = sl.point(a, 0.05, -0.1) + Vector((sgn * 0.035, 0, 0))
        p1 = sl.point(a, sl.L * 0.55, -0.1) + Vector((sgn * 0.035, 0, 0))
        for i in range(5):
            p = p0.lerp(p1, (i + 0.5) / 5)
            RA.shape([(-0.09, 0), (0, -0.24), (0.09, 0)], depth=0.012, M=Matrix.Translation(p) @ Mr,
                     uv_off=RAUTEN_UV)

    # ------------------------------------------------------------ crest sign on the front slope
    ys = -0.42
    z_roof = RIDGE - abs(ys) * math.tan(h.pitch) + 0.05
    sign_c = Vector((0, ys, z_roof + 0.42))
    cp.sign(P, P, "Bier vom Fass", state.font("fraktur_bold"), sign_c, 2.5, 0.52, depth=0.045,
            board_band="white", text_band="blue", frame_band="blue", board_shape="arch", text_size=0.3,
            max_fill=0.84, text_depth=0.012, text_dy=-0.05)
    h.sign_lamps((-0.7, 0.7), ys - 0.03, sign_c.z + 0.28)
    # Rauten strip under the sign and two small flags on poles
    RA.box((0, ys - 0.03, sign_c.z - 0.3), (2.5, 0.03, 0.1), grain=0, uv_off=RAUTEN_UV)
    for x in (-1.1, 1.1):
        h.iron.box((x, ys + 0.03, z_roof + 0.06), (0.03, 0.03, 0.26), bevel=0)
        a = Vector((x, ys + 0.04, sign_c.z + 0.1))
        b = Vector((x, ys + 0.5, RIDGE - (abs(ys + 0.5)) * math.tan(h.pitch) + 0.06))
        h.iron.slab(a, b, 0.025, 0.012, up=(1, 0, 0))
    for x in (-1.38, 1.38):
        h.frame.cyl((x, ys + 0.1, sign_c.z + 0.2), 0.02, 0.018, 1.0, seg=8, tint="honey")
        h.frame.sphere((x, ys + 0.1, sign_c.z + 0.72), 0.035, seg=10, rings=6, tint="honey")
        flag = [(0, 0), (0.42 * (1 if x > 0 else -1), -0.08), (0, -0.2)]
        M = Matrix.Translation((x, ys + 0.1, sign_c.z + 0.66)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
        if x < 0:
            flag = [(0, 0), (0, -0.2), (-0.42, -0.08)]
        RA.shape(flag, depth=0.01, M=M, uv_off=RAUTEN_UV)

    # ------------------------------------------------------------ wreath of fir with bulbs in the opening
    cp.fir_garland(h.fir, h.beads, (-W / 2 + 0.1, yF - 0.07, 2.2), (W / 2 - 0.1, yF - 0.07, 2.2), sag=0.1,
                   radius=0.04, bead_bands=("ornament_gold",), bead_every=0.22)
    h.eave_bulbs(sides=True)
    h.interior_bulbs(xs=(-1.2, 0.0, 1.2), z=2.3)
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.06, 0))),
              lights=[(0, 0.1, 2.35), (0, yF - 0.8, 2.3)], cam_dist=3.7, cam_h=1.75)
    return h.finish()


def preview(objs):
    env = state.env_collection()
    yF = -D / 2
    glass = Part("env_beer", "brass")
    foam = Part("env_foam", "fabric_white")
    for i, x in enumerate((-1.6, -1.35, -1.1, 0.9, 1.15, 1.4, 1.65)):
        y = yF - 0.25 + 0.1 * (i % 2)
        glass.cyl((x, y, COUNTER_TOP + 0.09), 0.045, 0.05, 0.18, seg=14)
        foam.cyl((x, y, COUNTER_TOP + 0.195), 0.047, 0.045, 0.03, seg=14)
    for p in (glass, foam):
        p.finish(env)
    render.lights_at_markers(energy=110)
    render.add_light("env_fill", 'AREA', (0, 0.2, 2.5), 280, size=2.6)
    for x in (-0.7, 0.7):   # the two sign lamps
        render.add_light("env_signlamp", 'SPOT', (x, -0.78, 4.08), 25, size=0.05, rot=(math.radians(62), 0, 0))
    render.add_light("env_neighbour", 'POINT', (-5.2, -1.6, 2.7), 170, size=0.6)
    return render.camera((-4.6, -7.4, 2.1), (0.1, -0.5, 2.05), lens=29)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=37)
