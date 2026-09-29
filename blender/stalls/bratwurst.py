"""Bratwurst stand (section: Writing).

A low, broad, sooty hut: dark-stained overlapping lap siding blackened above the grill, a
board-and-batten roof, a riveted sheet-iron chimney hood over a charcoal grill set into the
left of the counter, a stovepipe with a rain cap through the roof, a firewood stack under a
lean-to on the right, and a black board "Bratwurst" hung on iron chains.

    /home/claude/tools/bpy-venv/bin/python blender/stalls/bratwurst.py [--no-render] [--no-lite]
Outputs site/public/models/stall_bratwurst.glb and stall_bratwurst.lite.glb.
Extra nodes: grill_coals (emissive 'ember' bed the engine may pulse), smoke_origin (empty).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut, grime  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import export, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_bratwurst"
W, D = 3.9, 2.5
EAVE, RIDGE = 2.62, 3.5
GRILL_X0, GRILL_X1 = -1.75, -0.15          # grill section of the counter
GX = (GRILL_X0 + GRILL_X1) / 2


def soot_shade():
    g = grime(0.5, 0.4)

    def f(p):
        k = g(p)
        # soot plume: rises from the grill, spreads under the eave and around the hood
        dx = abs(p.x - GX)
        up = max(0.0, min(1.0, (p.z - 1.2) / 1.2))
        plume = math.exp(-(dx / (0.9 + 0.5 * up)) ** 2) * up
        eave = max(0.0, (p.z - 1.9) / 0.6) * 0.35
        front = 1.0 if p.y < 0.2 else 0.6
        s = min(0.75, (plume * 0.8 + eave) * front)
        return k * (1.0 - s)
    return f


def frustum(part, c, w0, d0, w1, d1, z0, z1, **kw):
    r0 = [(c.x - w0 / 2, c.y - d0 / 2, z0), (c.x + w0 / 2, c.y - d0 / 2, z0),
          (c.x + w0 / 2, c.y + d0 / 2, z0), (c.x - w0 / 2, c.y + d0 / 2, z0)]
    r1 = [(c.x - w1 / 2, c.y - d1 / 2, z1), (c.x + w1 / 2, c.y - d1 / 2, z1),
          (c.x + w1 / 2, c.y + d1 / 2, z1), (c.x - w1 / 2, c.y + d1 / 2, z1)]
    part.loft([r0, r1], **kw)
    return r0, r1


def build(lite):
    sh = soot_shade()
    h = Hut("bratwurst", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='x', ov_eave=0.36, ov_gable=0.25,
            wall="lap", wall_tint="dark", frame_tint="walnut", roof="boards", roof_tint="dark",
            inner_tint="oak", counter_tint="dark", shade=sh, bulb_spacing=0.22,
            front_posts=[-W / 2 + 0.05, W / 2 - 0.05], shelves=(1.4, 1.8))
    h.roofp.shade = sh
    yF = h.yF
    h.build_carcass(lower_top=lambda c: 0.78 if GRILL_X0 - 0.05 < c < GRILL_X1 + 0.05 else COUNTER_TOP - 0.07)
    h.build_counter(x0=GRILL_X1 + 0.02)
    # counter under the grill: brick-coloured dark wood box front, the grill sits on it
    h.build_shelves()
    h.build_roof(cover="boards")
    h.build_snow()

    # ------------------------------------------------------------ grill set into the counter
    iron = h.iron
    gy0, gy1 = yF - 0.22, yF + 0.38
    gcy = (gy0 + gy1) / 2
    gw, gd = GRILL_X1 - GRILL_X0, gy1 - gy0
    # firebox: iron trough with thick walls
    for (cx, cy, sx, sy) in ((GX, gy0, gw, 0.04), (GX, gy1, gw, 0.04),
                             (GRILL_X0, gcy, 0.04, gd), (GRILL_X1, gcy, 0.04, gd)):
        iron.box((cx, cy, COUNTER_TOP - 0.1), (sx, sy, 0.24), bevel=0.004)
    iron.box((GX, gcy, COUNTER_TOP - 0.22), (gw, gd, 0.02))
    # front apron and legs down to the floor
    iron.box((GX, gy0 - 0.03, 0.62), (gw + 0.04, 0.02, 0.62))
    for x in (GRILL_X0 + 0.05, GRILL_X1 - 0.05):
        iron.box((x, gy0 - 0.01, 0.35), (0.06, 0.06, 0.7))
    # draught door on the apron
    iron.box((GX, gy0 - 0.045, 0.55), (0.4, 0.012, 0.22))
    iron.cyl((GX + 0.16, gy0 - 0.06, 0.55), 0.015, 0.015, 0.03, seg=8, rot=(math.pi / 2, 0, 0))
    # grate bars
    n = 22
    for i in range(n):
        x = GRILL_X0 + 0.06 + i * (gw - 0.12) / (n - 1)
        iron.box((x, gcy, COUNTER_TOP + 0.02), (0.012, gd - 0.06, 0.012), bevel=0)
    for y in (gy0 + 0.05, gy1 - 0.05):
        iron.box((GX, y, COUNTER_TOP + 0.01), (gw - 0.06, 0.02, 0.02), bevel=0)
    coals = Part("grill_coals", "ember", var=0.25)
    for k in range(70 if not lite else 20):
        x = state.rng.uniform(GRILL_X0 + 0.07, GRILL_X1 - 0.07)
        y = state.rng.uniform(gy0 + 0.06, gy1 - 0.06)
        coals.ico((x, y, COUNTER_TOP - 0.17), state.rng.uniform(0.03, 0.05), subd=0,
                  scale=(1, 1, 0.6), smooth=False)
    h.extra.append(coals)

    # ------------------------------------------------------------ hood + stovepipe
    hc = Vector((GX, yF + 0.45, 0))
    r0, r1 = frustum(iron, hc, gw + 0.16, gd + 0.2, 0.34, 0.34, 1.9, 2.6, closed=True, smooth=False)
    # rolled lip around the hood's lower edge and a straight skirt
    frustum(iron, hc, gw + 0.16, gd + 0.2, gw + 0.16, gd + 0.2, 1.76, 1.9, closed=True, smooth=False)
    lip = [Vector(p) + Vector((0, 0, -0.14)) for p in r0] + [Vector(r0[0]) + Vector((0, 0, -0.14))]
    iron.tube(lip, 0.014, tseg=6)
    # rivets along the skirt
    if not lite:
        for i in range(12):
            x = hc.x - (gw + 0.16) / 2 + 0.06 + i * (gw + 0.04) / 11
            iron.sphere((x, hc.y - (gd + 0.2) / 2 - 0.004, 1.87), 0.009, seg=6, rings=4)
    # hanging rods from the rafters
    for x in (hc.x - gw / 2 + 0.05, hc.x + gw / 2 - 0.05):
        iron.box((x, hc.y, 2.2), (0.012, 0.012, 0.5), bevel=0)
    pipe_top = RIDGE + 0.75
    iron.cyl((hc.x, hc.y, (2.6 + pipe_top) / 2), 0.11, 0.11, pipe_top - 2.6, seg=16, caps=False)
    for z in (3.0, 3.55, pipe_top - 0.25):
        iron.torus((hc.x, hc.y, z), 0.112, 0.008, seg=16, tseg=4)
    # rain cap on legs
    iron.cyl((hc.x, hc.y, pipe_top + 0.2), 0.24, 0.02, 0.13, seg=16, caps=True)
    for a in range(3):
        ang = a * 2 * math.pi / 3
        iron.box((hc.x + 0.1 * math.cos(ang), hc.y + 0.1 * math.sin(ang), pipe_top + 0.07),
                 (0.012, 0.012, 0.16), bevel=0)
    # flashing collar where the pipe meets the roof
    iron.cyl((hc.x, hc.y, RIDGE - 0.02 - abs(hc.y) * math.tan(h.pitch) + 0.03), 0.2, 0.13, 0.08, seg=16)
    smoke = (hc.x, hc.y, pipe_top + 0.3)

    # ------------------------------------------------------------ firewood lean-to on the right side
    wood = h.wood
    lx0 = W / 2
    for y in (yF + 0.25, h.yB - 0.25):
        h.frame.box((lx0 + 0.55, y, 0.75), (0.08, 0.08, 1.5), tint="walnut")
    lt = cp.Slope((lx0 + 0.72, 0, 1.52), (0, 1, 0), (1, 0, -0.35), 0.8, -D / 2 + 0.05, D / 2 - 0.05)
    cp.board_roof(h.roofp, lt, bw=0.22, tint="dark")
    h.frame.box((lx0 + 0.3, 0, 0.06), (0.62, D - 0.3, 0.06), tint="dark")
    logs = Part("bratwurst_logs", "wood", var=0.18)
    for row in range(5):
        for k in range(6 - (row % 2)):
            r = state.rng.uniform(0.055, 0.075)
            y = yF + 0.28 + k * 0.33 + (0.165 if row % 2 else 0) + state.rng.uniform(-0.02, 0.02)
            x = lx0 + 0.3 + state.rng.uniform(-0.05, 0.05)
            z = 0.16 + row * 0.13
            logs.cyl((x, y, z), r, r * state.rng.uniform(0.9, 1.05), 0.52, seg=7 if not lite else 5,
                     rot=(0, math.pi / 2, state.rng.uniform(-0.08, 0.08)), smooth=False,
                     tint=state.rng.choice(["oak", "dark", "honey"]))
    h.extra.append(logs)
    # axe block by the stack
    logs.cyl((lx0 + 0.45, yF - 0.35, 0.22), 0.17, 0.18, 0.44, seg=10, tint="oak")

    # ------------------------------------------------------------ sign standing on the front slope
    P = h.paint
    sl = h.front_slope
    y_eave = sl.point(0, 0).y
    ys = -0.55
    z_roof = RIDGE - abs(ys) * math.tan(h.pitch) + 0.05
    sign_c = Vector((0.45, ys, z_roof + 0.34))
    cp.sign(P, P, "Bratwurst", state.font("alegreya_sc"), sign_c, 1.9, 0.44, depth=0.045,
            board_band="black", text_band="cream", frame_band="red", text_size=0.28, max_fill=0.86,
            text_depth=0.012)
    for x in (sign_c.x - 0.75, sign_c.x + 0.75):
        # iron struts: a post down to the roof and a raking brace back to the ridge
        h.iron.box((x, ys + 0.03, z_roof + 0.06), (0.03, 0.03, 0.22), bevel=0)
        a = Vector((x, ys + 0.04, sign_c.z + 0.12))
        b = Vector((x, ys + 0.45, RIDGE - (abs(ys + 0.45)) * math.tan(h.pitch) + 0.06))
        h.iron.slab(a, b, 0.025, 0.012, up=(1, 0, 0))
    h.sign_lamps((sign_c.x - 0.55, sign_c.x + 0.55), ys - 0.03, sign_c.z + 0.22)
    # stepped black fascia board along the front eave
    cp.valance(P, -W / 2 - 0.25, W / 2 + 0.25, y_eave - 0.035, sl.point(0, 0, -0.03).z + 0.02, 0.12, 0.05,
               13, style="step", band="black")

    # ------------------------------------------------------------ utensils rail and bulbs
    h.iron.box((0.6, h.yB - 0.1, 2.05), (1.6, 0.02, 0.02), bevel=0)
    for i in range(6):
        x = 0.0 + i * 0.25
        h.iron.box((x, h.yB - 0.12, 1.96), (0.01, 0.01, 0.16), bevel=0)
    h.eave_bulbs(sides=False)
    h.interior_bulbs(xs=(0.1, 1.2), z=2.05)
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.05, 0))),
              lights=[(0.6, 0.0, 2.1), (GX, yF - 0.3, 1.5)], cam_dist=3.5, cam_h=1.75)
    export.empty("smoke_origin", smoke)
    return h.finish()


def preview(objs):
    env = state.env_collection()
    yF = -D / 2
    gy0, gy1 = yF - 0.22, yF + 0.38
    wurst = Part("env_wurst", "copper")
    for i in range(10):
        x = GRILL_X0 + 0.15 + i * 0.14
        wurst.cyl((x, (gy0 + gy1) / 2 + (0.08 if i % 2 else -0.08), COUNTER_TOP + 0.05), 0.022, 0.022, 0.2,
                  seg=10, rot=(math.pi / 2, 0, 0.15 * (i % 3 - 1)))
    rolls = Part("env_rolls", "fabric_white")
    for i in range(8):
        rolls.sphere((0.25 + i * 0.16, yF - 0.05, COUNTER_TOP + 0.035), 0.07, seg=10, rings=6, scale=(1.1, 0.55, 0.45))
    wurst.finish(env)
    rolls.finish(env)
    render.lights_at_markers(energy=90)
    render.add_light("env_ember", 'AREA', (GX, yF + 0.08, COUNTER_TOP + 0.02), 90, (1.0, 0.35, 0.08), size=0.8,
                     rot=(0, 0, 0))
    render.add_light("env_ember_up", 'POINT', (GX, yF + 0.0, COUNTER_TOP + 0.25), 40, (1.0, 0.4, 0.12), size=0.4)
    render.add_light("env_fill", 'AREA', (0.4, 0.2, 2.3), 160, size=2.0)
    for x in (-0.1, 1.0):   # the two sign lamps
        render.add_light("env_signlamp", 'SPOT', (x, -0.95, 3.8), 70, size=0.05,
                         rot=(math.radians(62), 0, 0))
    render.add_light("env_neighbour", 'POINT', (-5.0, -1.5, 2.6), 150, size=0.6)
    return render.camera((-4.4, -6.9, 2.0), (0.0, -0.5, 1.95), lens=30)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=23)
