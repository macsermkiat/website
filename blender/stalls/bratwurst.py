"""Bratwurst stand (section: Writing).

A low, broad, sooty hut: dark-stained overlapping lap siding blackened above the grill, a
board-and-batten roof, a riveted sheet-iron chimney hood over the grill end of the counter, a
stovepipe with a rain cap through the roof, a firewood stack under a lean-to on the right, and a
black board "Bratwurst" with cream letters on the front slope.

The grill is the vendor's (round 2): prop_wurst_counter at slot_counter stands its Schwenkgrill on
the counter under the hood. The stall has no firebox, grate, hearth plate or coals of its own;
the counter runs the full width, scorched and ash-dusted under the hood (the fire bowl sits at
x -0.9 from slot_counter, under the hood centre GX = -0.95).

    /home/claude/tools/bpy-venv/bin/python blender/stalls/bratwurst.py [--no-render] [--no-lite]
Outputs site/public/models/stall_bratwurst.glb and stall_bratwurst.lite.glb.
Extra nodes: smoke_origin (empty at the stovepipe top), slot_grill (empty on the counter top under
the hood centre: where the grill stands; the clear space under the hood skirt is 1.76 - 1.05 = 0.71 m).
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
GRILL_X0, GRILL_X1 = -1.75, -0.15          # grill end of the counter, under the hood
GX = (GRILL_X0 + GRILL_X1) / 2             # hood centre
BOWL_X = -0.9                              # the vendor's fire bowl (x from slot_counter, which is at x 0)
HOOD_D = 0.80                              # hood depth (front to back)


def soot_shade():
    """Walls and roof: splash grime near the ground plus a soot plume from the grill that
    blackens the siding above it, spreads under the eave and stains the whole front."""
    g = grime(0.5, 0.45)

    def f(p):
        k = g(p)
        dx = abs(p.x - GX)
        up = max(0.0, min(1.0, (p.z - 1.0) / 1.0))
        plume = math.exp(-(dx / (1.1 + 0.8 * up)) ** 2) * up
        eave = max(0.0, (p.z - 1.7) / 0.6) * 0.55
        front = 1.0 if p.y < 0.2 else 0.75
        streak = 0.12 * math.sin(p.x * 23.0 + math.sin(p.z * 3.1) * 2.0) ** 2   # soot runs down the boards
        s = min(0.9, (plume * 1.1 + eave + 0.2 + streak * up) * front)
        return (k * (1.0 - s), k * (1.0 - s * 1.02), k * (1.0 - s * 1.04))
    return f


def hood_shade(hc, gw):
    """Hood soot: heaviest on the skirt and its rolled lip where the smoke first hits, a
    heat-blued and straw band just above the skirt, soot again toward the stovepipe. Only the
    base colour: the hood's faint emissive stand-in keeps it readable in the browser."""
    STRAW, BLUE = (1.0, 0.82, 0.55), (0.55, 0.62, 1.0)

    def f(p):
        if p.z > 2.6:                                   # stovepipe: soot toward the top
            if abs(p.x - hc.x) < 0.3:
                k = 0.75 - 0.4 * max(0.0, min(1.0, (p.z - 3.0) / 1.2))
                return (k, k, k)
            return 1.0
        if p.z < 1.7 or abs(p.x - hc.x) > gw / 2 + 0.3:
            return 1.0
        t = max(0.0, min(1.0, (p.z - 1.76) / 0.84))      # 0 skirt bottom .. 1 hood top
        k = 0.38 + 0.32 * t - 0.12 * max(0.0, t - 0.75) / 0.25
        # heat tint band just above the skirt seam
        hb = max(0.0, 1.0 - abs(p.z - 1.97) / 0.09)
        sb = max(0.0, 1.0 - abs(p.z - 2.1) / 0.07)
        c = [k] * 3
        for i in range(3):
            c[i] *= (1 - 0.45 * hb) + 0.45 * hb * BLUE[i]
            c[i] *= (1 - 0.35 * sb) + 0.35 * sb * STRAW[i]
        # streaks: smoke runs up the hood faces in soft vertical bands
        c = [ci * (0.9 + 0.1 * math.sin(p.x * 31.0 + p.y * 17.0) ** 2) for ci in c]
        return tuple(c)
    return f


def scorch_shade(bowl, hood_x0, hood_x1):
    """Counter under the hood: charred round the vendor's fire bowl, ash-grey dusting and soot
    fading out to the ends of the hood."""
    def f(p):
        d = math.hypot(p.x - bowl[0], (p.y - bowl[1]) * 1.3)
        char = math.exp(-(d / 0.42) ** 2)
        under = 1.0 if hood_x0 < p.x < hood_x1 else math.exp(-((min(abs(p.x - hood_x0), abs(p.x - hood_x1))) / 0.2) ** 2)
        k = 1.0 - 0.72 * char - 0.22 * under
        ash = 0.25 * math.exp(-((d - 0.5) / 0.14) ** 2)   # a ring of pale ash round the char
        return (k + ash * 0.9, k + ash * 0.88, k + ash * 0.85)
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
            inner_tint="oak", counter_tint="dark", shade=sh, bulb_spacing=0.22, lap_segs=8,
            front_posts=[-W / 2 + 0.05, W / 2 - 0.05], shelves=(1.4, 1.8))
    h.roofp.shade = sh
    yF = h.yF
    gw = GRILL_X1 - GRILL_X0
    hc = Vector((GX, yF + 0.45, 0))                      # hood centre (plan)
    counter_y = yF - h.counter_over + h.counter_depth / 2
    bowl = (BOWL_X, counter_y)
    h.build_carcass()
    # one continuous counter; the grill end under the hood is scorched round the vendor's bowl
    h.build_counter(extra_shade=scorch_shade(bowl, GRILL_X0 - 0.08, GRILL_X1 + 0.08))
    h.build_shelves()
    h.build_roof(cover="boards")
    h.build_snow(drifts=3)

    # ------------------------------------------------------------ chimney hood + stovepipe
    # sheet iron (kit variant iron_matte: lighter, less metallic, with a faint warm emissive
    # stand-in for the fire and bulbs beside it); stovepipe, struts and fittings are plain iron
    iron = h.part("hood", "iron_matte")
    iron.shade = h.iron.shade = hood_shade(hc, gw)
    r0, r1 = frustum(iron, hc, gw + 0.16, HOOD_D, 0.34, 0.34, 1.9, 2.6, closed=True, smooth=False)
    # straight skirt, rolled lip around its lower edge
    frustum(iron, hc, gw + 0.16, HOOD_D, gw + 0.16, HOOD_D, 1.76, 1.9, closed=True, smooth=False)
    lip = [Vector(p) + Vector((0, 0, -0.14)) for p in r0] + [Vector(r0[0]) + Vector((0, 0, -0.14))]
    iron.tube(lip, 0.016, tseg=6)
    # riveted seams: two rows round the skirt, one up each corner of the hood
    if not lite:
        sx, sy = (gw + 0.16) / 2, HOOD_D / 2
        for z in (1.8, 1.875):
            for i in range(16):
                x = hc.x - sx + 0.05 + i * (2 * sx - 0.1) / 15
                iron.sphere((x, hc.y - sy - 0.006, z), 0.013, seg=8, rings=5)
            for i in range(6):
                y = hc.y - sy + 0.06 + i * (2 * sy - 0.12) / 5
                for xs in (-1, 1):
                    iron.sphere((hc.x + xs * (sx + 0.006), y, z), 0.013, seg=8, rings=5)
        for c0, c1 in zip(r0, r1):
            c0, c1 = Vector(c0), Vector(c1)
            for i in range(1, 8):
                p = c0.lerp(c1, i / 8)
                out = (p - Vector((hc.x, hc.y, p.z))).normalized() * 0.008
                iron.sphere(p + out, 0.011, seg=6, rings=4)
        # a horizontal seam strap across the hood front
        a0, a1 = Vector(r0[0]).lerp(Vector(r1[0]), 0.35), Vector(r0[1]).lerp(Vector(r1[1]), 0.35)
        iron.tube([a0 + Vector((0, -0.006, 0)), a1 + Vector((0, -0.006, 0))], 0.008, tseg=5)
    # hanging rods from the rafters
    for x in (hc.x - gw / 2 + 0.05, hc.x + gw / 2 - 0.05):
        h.iron.box((x, hc.y, 2.2), (0.012, 0.012, 0.5), bevel=0)
    pipe_top = RIDGE + 0.75
    h.iron.cyl((hc.x, hc.y, (2.6 + pipe_top) / 2), 0.11, 0.11, pipe_top - 2.6, seg=16, caps=False)
    for z in (3.0, 3.55, pipe_top - 0.25):
        h.iron.torus((hc.x, hc.y, z), 0.112, 0.008, seg=16, tseg=4)
    # rain cap on legs
    h.iron.cyl((hc.x, hc.y, pipe_top + 0.2), 0.24, 0.02, 0.13, seg=16, caps=True)
    for a in range(3):
        ang = a * 2 * math.pi / 3
        h.iron.box((hc.x + 0.1 * math.cos(ang), hc.y + 0.1 * math.sin(ang), pipe_top + 0.07),
                   (0.012, 0.012, 0.16), bevel=0)
    # flashing collar where the pipe meets the roof
    h.iron.cyl((hc.x, hc.y, RIDGE - 0.02 - abs(hc.y) * math.tan(h.pitch) + 0.03), 0.2, 0.13, 0.08, seg=16)
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
    SG = h.part("sign", "paint", var=0.02)   # the sign is not soot-shaded: cream letters stay light
    sl = h.front_slope
    y_eave = sl.point(0, 0).y
    ys = -0.55
    z_roof = RIDGE - abs(ys) * math.tan(h.pitch) + 0.05
    sign_c = Vector((0.45, ys, z_roof + 0.34))
    cp.sign(SG, SG, "Bratwurst", state.font("alegreya_sc"), sign_c, 1.9, 0.44, depth=0.045,
            board_band="black", text_band="cream", frame_band="gold", text_size=0.3, max_fill=0.88,
            text_depth=0.014, text_bevel=0.0)
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
    export.empty("slot_grill", (BOWL_X, counter_y, COUNTER_TOP))
    return h.finish()


def preview(objs):
    """The vendor's shipped counter set (Schwenkgrill, sausages, rolls) at slot_counter, the
    fire's glow, the two gooseneck sign lamps and a neighbour's glow."""
    yF = -D / 2
    cy = yF - 0.22 + 0.3                                   # counter centre line (slot_counter y)
    props = render.import_glb(os.path.join(state.MODELS_DIR, "prop_wurst_counter.glb"), at="slot_counter")
    render.lights_at_markers(energy=90)
    # the fire in the vendor's bowl: glow up into the hood and onto the front
    render.add_light("env_ember", 'POINT', (BOWL_X, cy, COUNTER_TOP + 0.2), 30, (1.0, 0.36, 0.08), size=0.18)
    render.add_light("env_ember_front", 'POINT', (BOWL_X, cy - 0.45, COUNTER_TOP + 0.15), 14, (1.0, 0.4, 0.12),
                     size=0.3)
    render.add_light("env_fill", 'AREA', (0.4, 0.2, 2.3), 160, size=2.0)
    # the two gooseneck sign lamps: tight spots from the lamp heads onto the board, so the hotspot
    # lands on the lettering and not on the roof snow in front of it
    for x in (-0.1, 1.0):
        render.add_light("env_signlamp", 'SPOT', (x, -0.9, 3.83), 22, size=0.05, spot_size=math.radians(62),
                         spot_blend=0.6, target=(x * 0.6 + 0.18, -0.58, 3.52))
    render.add_light("env_neighbour", 'POINT', (-5.0, -1.5, 2.6), 150, size=0.6)
    if not props:
        print("[bratwurst] preview without the vendor's props")
    return render.camera((-4.4, -6.9, 2.35), (0.0, -0.5, 1.9), lens=30)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=23)
