"""Bücherstand (section: Reading).

An antiquarian bookshop hut: bottle-green painted boards with cream trim, a dark shingled roof,
two tall glazed display cabinets flanking the counter (glass doors with cream glazing bars and
inner shelves), a small projecting bay window with a copper-hooded roof on the left wall, an
iron wall lantern, and a hand-painted swallow-tail sign "Bücher" hung on chains.

    /home/claude/tools/bpy-venv/bin/python blender/stalls/buecher.py [--no-render] [--no-lite]
Outputs site/public/models/stall_buecher.glb and stall_buecher.lite.glb.
Extra nodes: slot_cabinet_l / slot_cabinet_r (bottom shelf of each cabinet, for books).
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
from nmlib import export, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_buecher"
W, D = 3.7, 2.5
EAVE, RIDGE = 2.9, 3.9
CAB_W = 0.66          # cabinet width
CAB_D = 0.36          # cabinet depth (protrudes in front of the wall)


def glazed_door(P, glass, x0, x1, z0, z1, y, cols=2, rows=3, frame_band="cream", lite=False):
    """Door frame with glazing bars (paint) and one glass pane (glass) in the XZ plane at y."""
    fw = 0.045
    w, h = x1 - x0, z1 - z0
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    P.box((cx, y, z1 - fw / 2), (w, 0.03, fw), band=frame_band)
    P.box((cx, y, z0 + fw * 0.75), (w, 0.03, fw * 1.5), band=frame_band)
    P.box((x0 + fw / 2, y, cz), (fw, 0.03, h), band=frame_band, grain=2)
    P.box((x1 - fw / 2, y, cz), (fw, 0.03, h), band=frame_band, grain=2)
    for i in range(1, cols):
        x = x0 + fw + (w - 2 * fw) * i / cols
        P.box((x, y - 0.004, cz), (0.018, 0.02, h - 2 * fw), band=frame_band, grain=2)
    for j in range(1, rows):
        z = z0 + 1.5 * fw + (h - 2.5 * fw) * j / rows
        P.box((cx, y - 0.004, z), (w - 2 * fw, 0.02, 0.018), band=frame_band, grain=0)
    glass.box((cx, y + 0.004, cz), (w - 2 * fw + 0.01, 0.006, h - 2.5 * fw + 0.01), bevel=0, var=0.0)


def cabinet(h, glass, xc, lite):
    """Tall glazed display cabinet standing at the front, centred at x = xc."""
    P = h.paint
    yF = h.yF
    y0, y1 = yF - CAB_D + 0.05, yF + 0.05
    x0, x1 = xc - CAB_W / 2, xc + CAB_W / 2
    zb, zt = 0.12, 2.18
    # carcass: sides, top, plinth, cornice
    for x in (x0 + 0.015, x1 - 0.015):
        P.box((x, (y0 + y1) / 2, (zb + zt) / 2), (0.03, y1 - y0, zt - zb), band="green", grain=2)
    P.box((xc, (y0 + y1) / 2, zt - 0.015), (CAB_W, y1 - y0, 0.03), band="green")
    P.box((xc, (y0 + y1) / 2 - 0.01, zb + 0.06), (CAB_W + 0.02, y1 - y0 + 0.02, 0.12), band="green")
    P.box((xc, (y0 + y1) / 2 - 0.02, zt + 0.03), (CAB_W + 0.06, y1 - y0 + 0.05, 0.06), band="cream")
    P.box((xc, (y0 + y1) / 2 - 0.025, zt + 0.075), (CAB_W + 0.09, y1 - y0 + 0.07, 0.03), band="green")
    # shelves inside (wood) and back
    for z in (0.62, 1.05, 1.48, 1.9):
        h.frame.box((xc, (y0 + y1) / 2 + 0.01, z), (CAB_W - 0.06, y1 - y0 - 0.05, 0.022), tint="walnut")
    # two glazed doors
    mid = xc
    glazed_door(P, glass, x0 + 0.03, mid - 0.004, zb + 0.13, zt - 0.03, y0 - 0.01, cols=2, rows=4, lite=lite)
    glazed_door(P, glass, mid + 0.004, x1 - 0.03, zb + 0.13, zt - 0.03, y0 - 0.01, cols=2, rows=4, lite=lite)
    # brass knobs and escutcheon
    for x in (mid - 0.04, mid + 0.04):
        h.extra_brass.sphere((x, y0 - 0.035, 1.15), 0.013, seg=8, rings=6)
    cabinet_books(h, x0 + 0.035, x1 - 0.035, (y0 + y1) / 2 + 0.035, lite)
    # a small warm bulb under the cabinet top lights the spines behind the glass
    h.wire.cyl((xc, (y0 + y1) / 2, zt - 0.05), 0.012, 0.012, 0.03, seg=8)
    h.bulbs.sphere((xc, (y0 + y1) / 2, zt - 0.085), 0.022, seg=8 if not lite else 5, rings=6 if not lite else 3,
                   scale=(1, 1, 1.3))
    return (xc, (y0 + y1) / 2 + 0.01, 0.62 + 0.011)


# cloth and leather bindings (linear RGB tints of the 'bookcloth' material)
# (lifted about 1.6x in round 2: behind the glass, with no engine light inside the cabinet, the
# darker round-1 cloths read as an empty cabinet in three.js)
BINDINGS = [(0.46, 0.06, 0.05), (0.07, 0.23, 0.11), (0.06, 0.10, 0.30), (0.33, 0.15, 0.06),
            (0.66, 0.44, 0.14), (0.74, 0.66, 0.50), (0.07, 0.07, 0.065), (0.28, 0.045, 0.10),
            (0.06, 0.26, 0.26), (0.54, 0.25, 0.08)]


def cabinet_books(h, xa, xb, yc, lite):
    """Low-poly book spines behind the cabinet glass (the vendor's props fill the counter and
    back shelves, not the cabinets): the upper three shelves full, the bottom shelf with a lying
    stack at each end, its middle left free at slot_cabinet_<l|r>."""
    if not hasattr(h, "books"):
        h.books = h.part("books", "bookcloth", var=0.12)
    B, R = h.books, state.rng
    drop = ("-z", "+y")                      # never seen: the underside and the back
    for z, room in ((1.05, 0.40), (1.48, 0.40), (1.9, 0.23)):
        zt = z + 0.011
        x = xa + R.uniform(0.0, 0.02)
        while x < xb - 0.03:
            bw = R.uniform(0.022, 0.055)
            bh = min(room - 0.02, R.uniform(0.17, 0.29))
            bd = R.uniform(0.14, 0.2)
            lean = 0.0
            if R.random() < 0.08 and x + bw + 0.06 < xb:
                lean = R.uniform(0.12, 0.22)          # a leaning book: it rests on its neighbour
            cx = x + bw / 2 + bh * math.sin(lean) / 2
            B.box((cx, yc - (0.2 - bd) / 2, zt + bh * math.cos(lean) / 2), (bw - 0.003, bd, bh),
                  rot=(0, lean, 0), tint=R.choice(BINDINGS), bevel=0, drop=drop, grain=2)
            x += bw + (bh * math.sin(lean) if lean else 0.0)
    zt = 0.62 + 0.011
    for xe in (xa + 0.13, xb - 0.13):                 # lying stacks on the bottom shelf
        zz = zt
        for k in range(R.randint(3, 5)):
            t = R.uniform(0.025, 0.045)
            B.box((xe + R.uniform(-0.01, 0.01), yc, zz + t / 2), (0.22, 0.16, t), rot=(0, 0, R.uniform(-0.1, 0.1)),
                  tint=R.choice(BINDINGS), bevel=0, drop=drop, grain=0)
            zz += t


def bay_window(h, glass, lite):
    """Small canted bay window projecting from the left wall (faces -X)."""
    P = h.paint
    xw = h.x0 + 0.0
    yc, zc = 0.05, 1.5
    fw, dp, sw = 0.72, 0.3, 0.26          # front width, projection, side run
    z0, z1 = 1.05, 1.95
    # plan: wall points A (y-), B (y+); front points C, D
    A = Vector((xw, yc - fw / 2 - sw * 0.7, 0))
    B = Vector((xw, yc + fw / 2 + sw * 0.7, 0))
    C = Vector((xw - dp, yc - fw / 2, 0))
    Dd = Vector((xw - dp, yc + fw / 2, 0))
    plan = [A, C, Dd, B]
    # sill / base block and apron
    def ring(z, grow=0.0):
        out = []
        for p in plan:
            q = Vector((p.x - (grow if p.x < xw - 1e-3 else 0), p.y + (-grow if p.y < yc else grow) *
                        (1 if p.x < xw - 1e-3 else 1.0), z))
            out.append(q)
        return out
    P.loft([ring(z0 - 0.3), ring(z0 - 0.06), ring(z0 - 0.06, 0.03), ring(z0, 0.03)], closed=False,
           band="green", smooth=False)
    P.loft([ring(z0, 0.03), ring(z0, 0.0)], closed=False, band="cream", smooth=False)
    P.shape([(p.x, p.y) for p in ring(z0, 0.03)], depth=0.03, M=Matrix.Translation((0, 0, z0 - 0.015)),
            band="cream")
    # corbel brackets under the sill
    for p in (C, Dd):
        h.frame.slab((xw, p.y, z0 - 0.45), (p.x + 0.03, p.y, z0 - 0.08), 0.05, 0.05, up=(0, 0, 1),
                     tint="walnut")
    # glazed faces
    for p, q in ((A, C), (C, Dd), (Dd, B)):
        d = (q - p)
        L = d.length
        ang = math.atan2(d.y, d.x)
        mid = (p + q) / 2
        Rz = Euler((0, 0, ang)).to_matrix().to_4x4()
        nrm = Vector((d.y, -d.x, 0)).normalized()
        # posts and rails (cream) in the face's own frame
        for (u, v, sx, sz) in ((0, z1 - 0.03, L, 0.06), (0, z0 + 0.03, L, 0.06), (-L / 2 + 0.025, (z0 + z1) / 2, 0.05, z1 - z0),
                               (L / 2 - 0.025, (z0 + z1) / 2, 0.05, z1 - z0), (0, (z0 + z1) / 2, L - 0.05, 0.018)):
            c = mid + (Rz.to_3x3() @ Vector((u, 0, 0))) + Vector((0, 0, v))
            P.mbox(Matrix.Translation(c) @ Rz, (sx, 0.035, sz), band="cream", grain=0 if sx > sz else 2)
        if L > 0.4:
            c = mid + Vector((0, 0, (z0 + z1) / 2))
            P.mbox(Matrix.Translation(c) @ Rz, (0.018, 0.03, z1 - z0 - 0.08), band="cream", grain=2)
        c = mid + Vector((0, 0, (z0 + z1) / 2)) - nrm * 0.0
        glass.mbox(Matrix.Translation(c) @ Rz, (L - 0.05, 0.006, z1 - z0 - 0.1), bevel=0, var=0.0)
    # little hipped roof sheathed in copper, plus its fascia
    top0 = ring(z1, 0.05)
    peak = [Vector((xw, p.y * 0.6 + yc * 0.4, z1 + 0.3)) if p.x < xw - 1e-3 else Vector((p.x, p.y, z1 + 0.3))
            for p in top0]
    peak = [Vector((xw - 0.02, yc - fw / 2 * 0.5, z1 + 0.32)), Vector((xw - 0.05, yc - fw / 2 * 0.4, z1 + 0.32)),
            Vector((xw - 0.05, yc + fw / 2 * 0.4, z1 + 0.32)), Vector((xw - 0.02, yc + fw / 2 * 0.5, z1 + 0.32))]
    h.extra_copper.loft([top0, peak], closed=False, smooth=False)
    P.loft([ring(z1 - 0.06, 0.05), ring(z1, 0.05)], closed=False, band="cream", smooth=False)
    # a lamp glow inside the bay (goods/books go on the sill inside)
    h.bulbs.sphere((xw - 0.12, yc, z1 - 0.18), 0.04, seg=10, rings=7, scale=(1, 1, 1.3))
    h.wire.tube([(xw - 0.12, yc, z1 + 0.02), (xw - 0.12, yc, z1 - 0.12)], 0.004, tseg=4)


def lantern(h, pos, lite):
    """Iron wall lantern on a scroll bracket."""
    x, y, z = pos
    iron = h.iron
    iron.box((x, y + 0.2, z + 0.25), (0.02, 0.4, 0.02), bevel=0)
    iron.torus((x, y + 0.12, z + 0.16), 0.08, 0.008, seg=12, tseg=4, rot=(0, math.pi / 2, 0), arc=math.pi * 1.2)
    iron.box((x, y, z + 0.14), (0.012, 0.012, 0.2), bevel=0)
    iron.cyl((x, y, z + 0.02), 0.11, 0.03, 0.08, seg=4, rot=(0, 0, math.pi / 4))       # hood
    for dx in (-0.06, 0.06):
        for dy in (-0.06, 0.06):
            iron.box((x + dx, y + dy, z - 0.15), (0.012, 0.012, 0.28), bevel=0)
    iron.cyl((x, y, z - 0.3), 0.07, 0.09, 0.04, seg=4, rot=(0, 0, math.pi / 4))
    glow = Part("buecher_lantern_glass", "lamp_glass", var=0.0)
    glow.box((x, y, z - 0.15), (0.11, 0.11, 0.25), bevel=0)
    h.extra.append(glow)


def build(lite):
    h = Hut("buecher", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='x', ov_eave=0.4, ov_gable=0.25,
            wall="vertical", wall_band="green", frame_tint="walnut", roof_tint="walnut", inner_tint="oak",
            counter_tint="walnut", plank_w=0.13, bulb_spacing=0.21, counter_depth=0.55, counter_over=0.2,
            front_posts=[-W / 2 + 0.05, W / 2 - 0.05])
    h.extra_brass = h.part("brass", "brass", var=0.02)
    # old copper sheet (iron kit dents and streaks, copper-brown colour, metal 0.6): the flat
    # 'copper' material rendered as a salmon plane in three.js (round 1)
    h.extra_copper = h.part("copper", "copper_old", var=0.05)
    glass = h.part("glass", "glass", var=0.0)
    yF = h.yF
    P = h.paint
    xin = W / 2 - 0.1 - CAB_W          # inner edge of each cabinet
    h.build_carcass()
    h.build_counter(x0=-xin + 0.02, x1=xin - 0.02, brackets=3)
    h.build_shelves(x0=-xin + 0.05, x1=xin - 0.05, band=None)
    h.build_roof(cover="shingles", fascia_band="cream", barge_band="cream")
    h.build_snow(drifts=3)
    # cream trim: corner boards, rails, counter lip
    for x in (h.x0 + 0.05, h.x1 - 0.05):
        for y in (yF + 0.0, h.yB - 0.0):
            P.box((x, y, EAVE / 2), (0.13, 0.13, EAVE), band="cream", grain=2)
    for z in (0.28, 0.82):
        P.box((0, yF - 0.032, z), (2 * xin, 0.022, 0.09), band="cream")
    P.box((0, yF - h.counter_over - 0.026, COUNTER_TOP - 0.05), (2 * xin, 0.02, 0.06), band="cream")
    # ------------------------------------------------------------ cabinets, bay window, lantern
    cab_l = cabinet(h, glass, -W / 2 + 0.1 + CAB_W / 2, lite)
    cab_r = cabinet(h, glass, W / 2 - 0.1 - CAB_W / 2, lite)
    bay_window(h, glass, lite)
    lantern(h, (W / 2 + 0.03, yF - 0.3, 2.1), lite)
    # ------------------------------------------------------------ hand-painted hanging sign
    sl = h.front_slope
    ye = yF - 0.22
    sign_c = Vector((0, ye, 2.16))
    cp.sign(P, P, "Bücher", state.font("fell_italic"), sign_c, 1.6, 0.36, depth=0.03,
            board_band="cream", text_band="green", frame_band=None, board_shape="banner",
            text_size=0.32, text_depth=0.005, max_fill=0.7, text_dy=0.01, resolution=1)
    # painted flourishes either side of the lettering (gold)
    for s in (-1, 1):
        for i, (dx, dz, ww) in enumerate(((0.52, 0.0, 0.12), (0.47, 0.05, 0.05), (0.47, -0.05, 0.05))):
            P.box((s * dx, ye - 0.02, sign_c.z + dz), (ww, 0.004, 0.012), band="gold", bevel=0)
    for x in (-0.6, 0.6):
        top = Vector((x, ye, RIDGE - abs(ye) * math.tan(h.pitch) - 0.03))
        bot = Vector((x, ye, sign_c.z + 0.18))
        n = 5 if not lite else 3
        for i in range(n):
            p = top.lerp(bot, (i + 0.5) / n)
            h.iron.torus(p, 0.016, 0.004, seg=8, tseg=4, rot=(0, 0, 0) if i % 2 else (0, math.pi / 2, 0))
    # ------------------------------------------------------------ bulbs
    h.eave_bulbs(sides=False)
    h.interior_bulbs(xs=(-0.6, 0.6), z=2.35)
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.04, 0))),
              lights=[(0, 0.15, 2.4), (0, yF - 0.7, 2.2)], cam_dist=3.4, cam_h=1.7)
    export.empty("slot_cabinet_l", cab_l)
    export.empty("slot_cabinet_r", cab_r)
    return h.finish()


def preview(objs):
    env = state.env_collection()
    yF = -D / 2
    if pipeline.vendor_props([("prop_books_shelf_1", "slot_shelf_1"), ("prop_books_shelf_2", "slot_shelf_2"),
                              ("prop_books_counter", "slot_counter")]):
        return _lights_and_camera(yF)
    books = Part("env_books", "paint", var=0.1)
    bands = ["red", "green", "blue", "black", "cream", "red", "gold"]
    R = state.rng
    shelves = [(z, D / 2 - 0.2, -1.0, 1.0) for z in (1.38, 1.78)]
    for z, y, xa, xb in shelves:
        x = xa
        while x < xb - 0.03:
            bw = R.uniform(0.025, 0.06)
            bh = R.uniform(0.18, 0.3)
            books.box((x + bw / 2, y, z + bh / 2), (bw - 0.003, 0.18, bh), band=R.choice(bands), grain=2,
                      rot=(0, R.uniform(-0.03, 0.03), 0))
            x += bw
    for i in range(6):
        cx = -0.8 + i * 0.32
        zz = COUNTER_TOP
        for k in range(R.randint(2, 5)):
            t = R.uniform(0.03, 0.05)
            books.box((cx, yF - 0.05, zz + t / 2), (0.24, 0.17, t), band=R.choice(bands),
                      rot=(0, 0, R.uniform(-0.2, 0.2)))
            zz += t
    books.finish(env)
    return _lights_and_camera(yF)


def _lights_and_camera(yF):
    render.lights_at_markers(energy=100)
    render.add_light("env_fill", 'AREA', (0, 0.2, 2.5), 200, size=2.0)
    render.add_light("env_lantern", 'POINT', (W / 2 + 0.03, yF - 0.3, 1.95), 30, size=0.08)
    # the small bulb under each cabinet top: light the spines behind the glass
    cab_y = yF - CAB_D / 2 + 0.05
    for xc in (-W / 2 + 0.1 + CAB_W / 2, W / 2 - 0.1 - CAB_W / 2):
        render.add_light("env_cabinet", 'POINT', (xc, cab_y, 2.07), 7, size=0.03)
        render.add_light("env_cabinet_low", 'POINT', (xc, cab_y + 0.02, 1.3), 3, size=0.05)
    render.add_light("env_neighbour", 'POINT', (-5.0, -1.2, 2.6), 170, size=0.6)
    return render.camera((-4.5, -6.9, 2.0), (0.0, -0.4, 1.8), lens=30)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=51)
