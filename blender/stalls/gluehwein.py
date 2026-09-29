"""Glühwein stand (section: About).

A tall front-gabled hut: steep shingled roof with a deep front overhang, red bargeboards with
a carved scalloped edge, a scalloped lambrequin with star cut-outs across the overhang, a red
star board closing the gable (lit from inside), red-and-gold posts, rails and counter lip, a
gold star finial and an arched sign "Glühwein" in gold Fraktur.

    /home/claude/tools/bpy-venv/bin/python blender/stalls/gluehwein.py [--no-render] [--no-lite]
Outputs site/public/models/stall_gluehwein.glb and stall_gluehwein.lite.glb.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

import hut  # noqa: E402
import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import geo, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_gluehwein"
W, D = 3.4, 2.5
EAVE, RIDGE = 2.55, 4.25


def build(lite):
    h = Hut("gluehwein", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='y', ov_eave=0.32,
            ov_gable=0.5, wall="batten", wall_tint="honey", frame_tint="walnut", roof_tint="shingle",
            inner_tint="pine", counter_tint="oak", plank_w=0.15, bulb_spacing=0.19,
            front_posts=[-W / 2 + 0.05, W / 2 - 0.05])
    yF = h.yF
    star_z = 3.22                                     # gable planks stop here, star board above
    # carcass, but the front upper planks stop below the star board
    h.build_carcass(front_upper=False)
    cp.plank_wall(h.wood, h.x0 + 0.1, h.x1 - 0.1, 2.36, lambda c: min(h.top_at('x', c), star_z + 0.02),
                  axis="x", at=yF + 0.03, pw=h.pw, tint="honey", var=0.12)
    h.build_counter()
    h.build_shelves()
    h.build_roof(cover="shingles", barge_band="red")
    # re-do shingles bigger for budget: build_roof used defaults; fine for a 3.4 m hut
    h.build_snow()

    P = h.paint
    # ---------------------------------------------------------- red star board in the gable
    apex = h.top_at('x', 0.0)
    hw = (apex - star_z)                              # 45 degree gable: half width == height
    outer = [(-hw, 0), (hw, 0), (0, hw)]
    holes = [geo.star_polygon(0, hw * 0.45, 0.17, 0.075, 5),
             geo.star_polygon(-hw * 0.48, hw * 0.17, 0.08, 0.035, 5),
             geo.star_polygon(hw * 0.48, hw * 0.17, 0.08, 0.035, 5)]
    M = Matrix.Translation((0, yF + 0.02, star_z)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    P.shape(outer, holes, depth=0.025, M=M, band="red")
    # gold edging strips along the star board
    for s in (-1, 1):
        a = Vector((s * hw, yF - 0.002, star_z))
        b = Vector((0, yF - 0.002, star_z + hw))
        P.slab(a, b, 0.035, 0.012, up=(0, -1, 0), band="gold")
    P.box((0, yF - 0.004, star_z + 0.01), (2 * hw, 0.014, 0.035), band="gold")

    # ---------------------------------------------------------- front overhang: tie beam + lambrequin
    yO = yF - 0.47
    zt = 2.66                                         # tie beam height, just under the rakes
    h.frame.box((0, yO + 0.04, zt), (W + 0.3, 0.1, 0.12), tint="walnut")
    for s in (-1, 1):  # knee braces from the posts to the tie beam
        a = Vector((s * (W / 2 - 0.05), yF + 0.02, 2.2))
        b = Vector((s * (W / 2 - 0.05), yO + 0.06, zt - 0.05))
        h.frame.slab(a, b, 0.08, 0.08, up=(1, 0, 0), tint="walnut")
    cp.valance(P, -W / 2 - 0.1, W / 2 + 0.1, yO - 0.02, zt - 0.05, 0.16, 0.13, 9, style="scallop",
               holes="star", band="red", depth=0.024)
    P.box((0, yO - 0.036, zt - 0.02), (W + 0.26, 0.012, 0.035), band="gold")
    # carved scalloped edge under each red bargeboard (front rakes)
    for sl in h.slopes:
        a_front = sl.a0 if sl.A.y > 0 else sl.a1
        Mv = Matrix.Translation(sl.point(a_front, 0.12, -0.10)) @ \
            Matrix((sl.U, sl.N, sl.A)).transposed().to_4x4()
        cp.valance(P, 0, sl.L - 0.35, 0, 0, 0.06, 0.07, 10, style="scallop", depth=0.022,
                   band="red", M=Mv)
        # gold strip on the bargeboard
        p = sl.point(a_front - 0.018 * (1 if sl.A.y > 0 else -1), sl.L / 2, 0.03)
        P.mbox(Matrix.Translation(p) @ sl.basis(), (0.012, sl.L, 0.03), grain=1, band="gold")
    # king post and gold star finial at the apex of the front rakes
    ap = Vector((0, yO - 0.03, RIDGE + 0.12))
    h.frame.box((0, yO - 0.03, RIDGE - 0.1), (0.09, 0.09, 0.55), tint="walnut")
    Ms = Matrix.Translation(ap + Vector((0, -0.05, 0.22))) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    P.shape(geo.star_polygon(0, 0, 0.2, 0.085, 8), depth=0.03, M=Ms, band="gold")

    # ---------------------------------------------------------- red and gold posts, rails, stars
    for x in h.front_posts:
        P.box((x, yF - 0.008, (COUNTER_TOP + 2.2) / 2), (0.115, 0.018, 2.2 - COUNTER_TOP), band="red")
        for z in (COUNTER_TOP + 0.04, 2.14):
            P.box((x, yF - 0.02, z), (0.13, 0.02, 0.035), band="gold")
    for z in (0.28, 0.82):
        P.box((0, yF - 0.032, z), (W - 0.12, 0.022, 0.1), band="red")
        P.box((0, yF - 0.045, z + 0.035), (W - 0.14, 0.008, 0.012), band="gold")
    for x in (-1.05, 0.0, 1.05):
        Ms = Matrix.Translation((x, yF - 0.04, 0.55)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
        P.shape(geo.star_polygon(0, 0, 0.13, 0.055, 5), depth=0.016, M=Ms, band="gold")
    # counter lip in red with a gold bead
    y_front = yF - h.counter_over
    P.box((0, y_front - 0.026, COUNTER_TOP - 0.06), (W - 0.1, 0.02, 0.08), band="red")
    P.box((0, y_front - 0.038, COUNTER_TOP - 0.03), (W - 0.12, 0.01, 0.014), band="gold")

    # ---------------------------------------------------------- sign on the lambrequin
    sign_c = Vector((0, yO - 0.075, zt - 0.07))
    cp.sign(P, P, "Glühwein", state.font("fraktur_bold"), sign_c, 1.55, 0.44, depth=0.035,
            board_band="red", text_band="gold", frame_band="gold", board_shape="arch",
            text_size=0.34, text_depth=0.014, text_dy=-0.035, max_fill=0.84)

    # ---------------------------------------------------------- garland, lights, bulbs
    anchors = [(-1.6, yF - 0.08, 2.2), (-0.55, yF - 0.08, 2.2), (0.55, yF - 0.08, 2.2), (1.6, yF - 0.08, 2.2)]
    for a, b in zip(anchors[:-1], anchors[1:]):
        cp.fir_garland(h.fir, h.beads, a, b, sag=0.16, radius=0.045)
    h.eave_bulbs(sides=False)
    # a string on the tie beam under the lambrequin
    cp.bulb_string(h.bulbs, h.wire, [(-W / 2, yO - 0.05, zt - 0.3), (0, yO - 0.05, zt - 0.3),
                                     (W / 2, yO - 0.05, zt - 0.3)], sag=0.07, spacing=0.21)
    h.interior_bulbs(xs=(-0.9, 0.0, 0.9), z=2.35)
    # iron: hooks for mugs under the tie beam, strap hinges on the side walls
    for x in (-1.2, -0.6, 0.0, 0.6, 1.2):
        h.iron.box((x, yF + 0.2, 2.05), (0.012, 0.012, 0.1))
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.05, 0))),
              lights=[(0, 0.1, 2.3), (0, yF - 0.7, 2.35)], cam_dist=3.6, cam_h=1.8)
    return h.finish()


def preview(objs):
    env = state.env_collection()
    yF = -D / 2
    # render-only stand-ins (the vendor ships the real goods)
    pot = Part("env_pot", "copper")
    pot.lathe([(0.001, 0), (0.2, 0.0), (0.22, 0.03), (0.23, 0.28), (0.24, 0.3), (0.2, 0.31)], seg=32,
              M=Matrix.Translation((0.55, yF + 0.05, COUNTER_TOP)))
    pot.torus((0.55, yF + 0.05, COUNTER_TOP + 0.34), 0.21, 0.012, seg=32)
    mugs = Part("env_mugs", "ornament_red")
    for i, x in enumerate((-1.3, -1.05, -0.8, -0.55, -0.3)):
        mugs.lathe([(0.001, 0), (0.04, 0), (0.044, 0.02), (0.045, 0.11), (0.04, 0.112), (0.036, 0.02), (0.001, 0.02)],
                   seg=16, M=Matrix.Translation((x, yF - 0.05 + 0.08 * (i % 2), COUNTER_TOP)))
    for z in (1.38, 1.78):
        for i in range(16):
            x = -1.35 + i * 0.18
            mugs.lathe([(0.001, 0), (0.035, 0), (0.038, 0.1), (0.001, 0.1)], seg=12,
                       M=Matrix.Translation((x, D / 2 - 0.2, z)))
    for p in (pot, mugs):
        p.finish(env)
    render.lights_at_markers(energy=110)
    render.add_light("env_fill", 'AREA', (0, 0.2, 2.45), 260, size=2.2, rot=(0, 0, 0))
    render.add_light("env_front", 'POINT', (-0.6, yF - 1.9, 2.4), 45, size=0.5)
    render.add_light("env_neighbour", 'POINT', (-4.8, -1.8, 2.6), 160, size=0.6)
    return render.camera((-4.3, -7.4, 2.1), (0.1, -0.6, 2.15), lens=30, dof=2.2)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=11)
