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

import buecher_sections as BS  # noqa: E402
import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut, grime as hut_grime  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import boards, export, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_buecher"
W, D = 3.7, 2.5
EAVE, RIDGE = 2.9, 3.9
CAB_W = 0.66          # cabinet width
CAB_D = 0.36          # cabinet depth (protrudes in front of the wall)
LANTERN = (W / 2 + 0.43, -0.35, 2.1)    # on the right side wall, bracket pointing back to the wall


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
# (round 3: one more step, about 1.25x, as the Fable judge asked: still barely visible in three.js)
BINDINGS = [(0.58, 0.08, 0.06), (0.09, 0.29, 0.14), (0.08, 0.13, 0.38), (0.42, 0.19, 0.08),
            (0.80, 0.55, 0.18), (0.86, 0.78, 0.60), (0.10, 0.10, 0.09), (0.36, 0.06, 0.13),
            (0.08, 0.33, 0.33), (0.68, 0.32, 0.10)]


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


def lantern(h, pos, lite, rot=0.0):
    """Iron wall lantern on a scroll bracket. The bracket runs from the lantern toward local +Y
    (the wall); rot turns it about Z (pi/2: mounted on a wall facing +X)."""
    F = Matrix.Translation(pos) @ Euler((0, 0, rot)).to_matrix().to_4x4()
    R3 = F.to_3x3()

    def P(x, y, z):
        return F @ Vector((x, y, z))

    def E(*e):
        return (R3 @ Euler(e).to_matrix()).to_euler()

    iron = h.iron
    iron.mbox(F @ Matrix.Translation((0, 0.2, 0.25)), (0.02, 0.4, 0.02), bevel=0)
    iron.torus(P(0, 0.12, 0.16), 0.08, 0.008, seg=12, tseg=4, rot=E(0, math.pi / 2, 0), arc=math.pi * 1.2)
    iron.mbox(F @ Matrix.Translation((0, 0, 0.14)), (0.012, 0.012, 0.2), bevel=0)
    iron.cyl(P(0, 0, 0.02), 0.11, 0.03, 0.08, seg=4, rot=E(0, 0, math.pi / 4))       # hood
    for dx in (-0.06, 0.06):
        for dy in (-0.06, 0.06):
            iron.mbox(F @ Matrix.Translation((dx, dy, -0.15)), (0.012, 0.012, 0.28), bevel=0)
    iron.cyl(P(0, 0, -0.3), 0.07, 0.09, 0.04, seg=4, rot=E(0, 0, math.pi / 4))
    glow = Part("buecher_lantern_glass", "lamp_glass", var=0.0)
    glow.mbox(F @ Matrix.Translation((0, 0, -0.15)), (0.11, 0.11, 0.25), bevel=0)
    h.extra.append(glow)


# ======================================================================== category sections
# Geometry from buecher_sections.py (the same module writes buecher_sections.json for the vendor).
GREEN_SHADE = None


def _frame(origin, a):
    return Matrix.Translation((origin[0], origin[1], 0.0)) @ Euler((0, 0, a)).to_matrix().to_4x4()


def _T(x, y, z):
    return Matrix.Translation((x, y, z))


def sign_label(label):
    """Two lines for a label with ' & ' (keeps the letters large), one line otherwise."""
    if " & " in label:
        a, b = label.split(" & ", 1)
        return a + " &\n" + b
    return label


def section_sign(h, key, label, F, cx, cy, cz, w, hh, lite):
    """Cream board with green letters and a thin gold border, standing in frame F (faces -Y).
    Its own mesh sign_cat_<key> in 'paint_glow' (the faint warm stand-in keeps it legible under
    the site's moonlight; the Cycles preview switches the stand-in off)."""
    S = Part(f"sign_cat_{key}", "paint_glow", var=0.03)
    S.flat_text = True          # painted letters: one front face each, no sides
    S.curve_simplify = 8.0
    h.extra.append(S)
    Mb = F @ _T(cx, cy, cz) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    d = 0.022
    S.shape([(-w / 2, -hh / 2), (w / 2, -hh / 2), (w / 2, hh / 2), (-w / 2, hh / 2)], depth=d, M=Mb,
            band="cream", bevel=0.003)
    # thin gold border just inside the edge, proud of the face
    e = 0.016
    for (x, z, ww, zz) in ((0, hh / 2 - e, w - 2 * e + 0.008, 0.008), (0, -hh / 2 + e, w - 2 * e + 0.008, 0.008),
                           (-w / 2 + e, 0, 0.008, hh - 2 * e), (w / 2 - e, 0, 0.008, hh - 2 * e)):
        S.mbox(F @ _T(cx + x, cy - d / 2 - 0.002, cz + z), (ww, 0.004, zz), band="gold", bevel=0,
               grain=0 if ww > zz else 2, drop=("+y",))
    text = sign_label(label)
    two = "\n" in text
    size = 0.10 if two else 0.14       # one line: width-limited (max_width) for the long single word
    Mt = F @ _T(cx, cy - d / 2 - 0.0035, cz - (0.006 if two else 0.0)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    tw, th = S.text(text, state.font("alegreya_sc"), size, 0.004, M=Mt, max_width=w - 0.05, band="green",
                    resolution=1, bevel=0.0)
    print(f"[buecher] sign {key}: letters {tw:.3f} x {th:.3f} m on a {w:.2f} x {hh:.2f} board")
    return S


def canopy(h, F, L, D, lite, snow_index, tint="walnut"):
    """Little shingled pent roof over a rack (front low, back high), braced from the back posts,
    with a cream fascia, a bulb string under its front edge and its own snow cap."""
    zb, zf = 1.99, 1.80                   # back top / front bottom
    yb, yf = D + 0.06, -0.30              # back / front edge (rack frame)
    A = (F.to_3x3() @ Vector((1, 0, 0))).normalized()
    back = F @ Vector((L / 2, yb, zb))
    front = F @ Vector((L / 2, yf, zf))
    dn = (front - back)
    sl = cp.Slope(front, A, dn, dn.length, -L / 2 - 0.07, L / 2 + 0.07)
    cp.roof_deck(h.wood, sl, tint=h.inner_tint, rafters=3, rafter=(0.045, 0.07))
    cp.shingles(h.roofp, sl, tint=tint, sw=0.17, expo=0.12, sh=0.26)
    cp.fascia(h.paint, sl, band="cream", h=0.1)
    # back posts up from the rack top, knee braces out to the front
    for x in (0.03, L / 2, L - 0.03):
        h.frame.mbox(F @ _T(x, D - 0.03, (1.2 + zb) / 2 - 0.02), (0.055, 0.055, zb - 1.2 - 0.04), grain=2,
                     tint="walnut")
        a = F @ Vector((x, D - 0.06, 1.52))
        b = F @ Vector((x, -0.12, zf + (zb - zf) * (-0.12 - yf) / (yb - yf) - 0.08))
        h.frame.slab(a, b, 0.04, 0.04, up=tuple(F.to_3x3() @ Vector((1, 0, 0))), tint="walnut")
    # bulbs under the front edge
    pts = [tuple(F @ Vector((L * t, yf + 0.02, zf - 0.07))) for t in (0.0, 0.5, 1.0)]
    cp.bulb_string(h.bulbs, h.wire, pts, sag=0.035, spacing=0.2, seg=h.bulb_detail[0], rings=h.bulb_detail[1])
    sp = Part(f"snow_{snow_index}", "snow", var=0.02)
    cp.snow_cap(sp, sl, courses=(0.12, -0.03), thick=0.022, base=0.032, ridge_clear=0.06, edge_in=0.04,
                seed=snow_index * 2.3)
    h.snow.append(sp)


def wing(h, unit, secs, lite, snow_index):
    """An open bookcase with two bays standing at a front corner, splayed toward the visitor."""
    (ox, oy), a = BS.wing_frame(unit)
    F = _frame((ox, oy), a)
    L, D = BS.wing_length(unit), BS.WING_DEPTH
    P, FR = h.paint, h.frame
    top = BS.WING_TOP
    bays = BS.wing_bays(unit)
    # uprights (sides and the divider), full depth
    x = 0.0
    xs = [0.0]
    for _, w in bays:
        x += BS.UPRIGHT + w
        xs.append(x)
    for xu in xs:
        P.mbox(F @ _T(xu + BS.UPRIGHT / 2, D / 2, top / 2 + 0.01), (BS.UPRIGHT, D, top + 0.02), band="green", grain=2)
        # cream edge strip on the upright's front
        P.mbox(F @ _T(xu + BS.UPRIGHT / 2, -0.004, top / 2 + 0.2), (BS.UPRIGHT + 0.006, 0.01, top - 0.4),
               band="cream", grain=2, bevel=0, drop=("+y",))
    # top cap with a cream cornice
    P.mbox(F @ _T(L / 2, D / 2 - 0.012, top + 0.015), (L + 0.05, D + 0.035, 0.03), band="green")
    P.mbox(F @ _T(L / 2, -0.02, top - 0.02), (L + 0.02, 0.025, 0.045), band="cream")
    for (key, w), x0 in zip(bays, xs[:-1]):
        bx0 = x0 + BS.UPRIGHT
        cx = bx0 + w / 2
        # plinth: framed panel under the lowest board
        P.mbox(F @ _T(cx, 0.014, 0.21), (w + 0.004, 0.022, 0.38), band="green", grain=2)
        if not lite:
            P.mbox(F @ _T(cx, -0.0, 0.21), (w - 0.1, 0.012, 0.24), band="green", grain=0, drop=("+y",))
            for zz in (0.09, 0.33):
                P.mbox(F @ _T(cx, -0.002, zz), (w - 0.06, 0.012, 0.02), band="cream", grain=0, bevel=0,
                       drop=("+y",))
        # boards (walnut wood, worn front edge)
        for z in BS.WING_BOARDS:
            FR.mbox(F @ _T(cx, BS.BOARD_SET + BS.BOARD_D / 2 + 0.005, z - BS.BOARD_T / 2),
                    (w + 0.006, BS.BOARD_D + 0.01, BS.BOARD_T), grain=0, tint="walnut", bevel=0.005)
        # back boards: vertical planks behind the books, green outside and in
        n = max(3, int(round(w / 0.13)))
        pw = w / n
        for i in range(n):
            P.mbox(F @ _T(bx0 + pw * (i + 0.5), D - 0.012, (0.4 + top) / 2), (pw - 0.004, 0.018, top - 0.4),
                   band="green", grain=2, var=0.05, bevel=0 if lite or i % 2 else None, drop=("-z", "+z"))
        # a small foot block under each end of the sign
        for dx in (-w / 2 + 0.06, w / 2 - 0.06):
            FR.mbox(F @ _T(cx + dx, 0.02, top + 0.035), (0.04, 0.03, 0.012), tint="walnut", bevel=0)
    canopy(h, F, L, D, lite, snow_index)
    return F


def spoked_wheel(h, M, r, lite):
    """Wooden cart wheel in the local XZ plane of M (axle along local Y): felloe, iron tyre,
    hub and spokes."""
    seg = 12 if lite else 20
    rot = Euler((math.pi / 2, 0, 0))
    c = M.translation
    R3 = M.to_3x3() @ rot.to_matrix()
    e = R3.to_euler()
    h.frame.torus(c, r - 0.03, 0.024, seg=seg, tseg=4, rot=e, tint="dark")
    h.iron.torus(c, r - 0.004, 0.009, seg=seg, tseg=4, rot=e)
    ax = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    h.frame.cyl(c, 0.045, 0.045, 0.09, seg=8 if lite else 10, rot=(M.to_3x3() @ Euler((math.pi / 2, 0, 0)).to_matrix()).to_euler(),
                tint="dark")
    n = 6 if lite else 10
    for i in range(n):
        t = 2 * math.pi * i / n
        d = M.to_3x3() @ Vector((math.cos(t), 0, math.sin(t)))
        p0 = c + d * 0.04
        p1 = c + d * (r - 0.05)
        h.frame.slab(p0, p1, 0.022, 0.02, up=tuple(ax), tint="dark", bevel=0)


def book_cart(h, unit, sec, lite):
    """A wooden handcart for books: stepped two-tier body, two spoked wheels at the back, legs at
    the front, iron corner straps and a sign on two iron rods."""
    (ox, oy), a = BS.cart_frame(unit)
    F = _frame((ox, oy), a)
    W = BS.cart_width(unit)
    (z0, y0), (z1, y1) = BS.CART_TIERS
    Dc = y1 + 0.25                      # body depth
    C, FR, I = h.cart, h.frame, h.iron
    bot = 0.32
    # stepped side panels (front low, back high)
    side = [(0.0, bot), (Dc, bot), (Dc, z1 + 0.09), (y1 - 0.01, z1 + 0.09), (y1 - 0.01, z0 + 0.09), (0.0, z0 + 0.09)]
    Mside = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    for xs in (0.0, W - 0.03):
        C.shape(side, depth=0.03, M=F @ _T(xs + 0.015, 0, 0) @ Mside, tint=h.cart_tint, bevel=0.003, grain=0)
    # front, riser and back panels, bottom
    C.mbox(F @ _T(W / 2, 0.012, (bot + z0) / 2), (W - 0.06, 0.024, z0 - bot), tint=h.cart_tint, grain=0)
    C.mbox(F @ _T(W / 2, y1 - 0.0, (z0 + z1) / 2), (W - 0.06, 0.022, z1 - z0), tint=h.cart_tint, grain=0)
    C.mbox(F @ _T(W / 2, Dc - 0.012, (bot + z1) / 2), (W - 0.06, 0.024, z1 - bot), tint=h.cart_tint, grain=0)
    C.mbox(F @ _T(W / 2, Dc / 2, bot + 0.012), (W - 0.06, Dc - 0.04, 0.024), tint=h.cart_tint, grain=0)
    # the section's name board hangs on the front apron (section_sign builds it) from two iron
    # hooks over the apron's top edge; a green lining strip runs along that edge
    h.paint.mbox(F @ _T(W / 2, 0.008, z0 + 0.004), (W - 0.04, 0.02, 0.012), band="green", bevel=0.002)
    for xs in (0.11, W - 0.11):
        I.mbox(F @ _T(xs, -0.004, BS.CART_SIGN[0] + BS.CART_SIGN[1] / 2 + 0.008), (0.02, 0.034, 0.03), bevel=0)
    # tier boards
    for (z, y) in BS.CART_TIERS:
        FR.mbox(F @ _T(W / 2, y + (y1 - y0 - 0.01) / 2, z - BS.BOARD_T / 2), (W - 0.06, y1 - y0 - 0.01, BS.BOARD_T),
                grain=0, tint="walnut", bevel=0.004)
    # iron corner straps
    for xs in (0.0, W):
        for (y, z) in ((0.0, z0 + 0.05), (0.0, bot + 0.04), (Dc, z1 + 0.05), (Dc, bot + 0.04)):
            I.mbox(F @ _T(xs + (0.002 if xs else -0.002), y + (0.03 if y == 0 else -0.03), z), (0.034, 0.07, 0.02),
                   bevel=0)
    # wheels at the back, legs at the front
    r = 0.27
    for xs, sgn in ((-0.035, -1), (W + 0.035, 1)):
        M = F @ _T(xs, Dc - 0.2, r) @ Euler((0, 0, math.pi / 2)).to_matrix().to_4x4()
        spoked_wheel(h, M, r, lite)
        FR.mbox(F @ _T(xs - sgn * 0.02, Dc - 0.2, r + 0.02), (0.05, 0.06, 0.06), tint="dark", bevel=0)
    I.mbox(F @ _T(W / 2, Dc - 0.2, r), (W + 0.06, 0.02, 0.02), bevel=0)        # axle
    for xs in (0.05, W - 0.05):
        FR.mbox(F @ _T(xs, 0.06, bot / 2), (0.045, 0.045, bot), tint="dark", grain=2)
        FR.mbox(F @ _T(xs, 0.06, 0.012), (0.06, 0.06, 0.024), tint="dark", bevel=0.003)
    # push handle: an iron bar on two stays at the back
    for xs in (0.08, W - 0.08):
        I.slab(F @ Vector((xs, Dc, z1 - 0.02)), F @ Vector((xs, Dc + 0.12, z1 + 0.04)), 0.014, 0.014,
               up=(0, 0, 1), bevel=0)
    I.cyl(F @ Vector((W / 2, Dc + 0.12, z1 + 0.04)), 0.014, 0.014, W - 0.12, seg=8, rot=(0, math.pi / 2, a))
    # turned finials on the back corners of the side panels
    for xs in (0.015, W - 0.015):
        FR.cyl(F @ Vector((xs, Dc - 0.015, z1 + 0.115)), 0.012, 0.012, 0.05, seg=8, tint="dark")
        I.sphere(F @ Vector((xs, Dc - 0.015, z1 + 0.15)), 0.017, seg=8, rings=5)
    return F


def section_slots(secs):
    for s in secs:
        loc = s["_local"]
        F = _frame(loc["origin"], loc["rot"])
        p = F @ Vector(loc["slot"])
        export.empty(s["slot"], tuple(p), rot=(0, 0, loc["rot"]))
        # round 4: optional close-up camera per section (BUILD.md cam_cat_<key>), from buecher_sections.py
        export.empty(s["cam_target"], tuple(s["cam_target_position"]))
        export.empty(s["cam"], tuple(s["cam_position"]), look_at=tuple(s["cam_target_position"]))


def build_sections(h, lite):
    secs = BS.sections()
    h.cart = h.part("cart", "wood", shade=hut_grime(), var=0.1)
    h.cart_tint = "oak"
    wing(h, "wing_l", secs, lite, snow_index=2)
    wing(h, "wing_r", secs, lite, snow_index=3)
    for unit in ("cart_l", "cart_r"):
        book_cart(h, unit, [s for s in secs if s["unit"] == unit][0], lite)
    for s in secs:
        loc = s["_local"]
        F = _frame(loc["origin"], loc["rot"])
        w, hh = loc["sign_size"]
        section_sign(h, s["key"], s["label_de"], F, *loc["sign"], w, hh, lite)
    section_slots(secs)
    return secs


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
    # round 3: the right wing stands where the lantern hung, so it moved to the right side wall
    lantern(h, LANTERN, lite, rot=math.pi / 2)
    # ------------------------------------------------------------ category sections
    build_sections(h, lite)
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
    # light_1 sits a little further out than in round 2 so it reaches the carts and both wings;
    # the camera stands back far enough to take in the wings
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.04, 0))),
              lights=[(0, 0.15, 2.4), (0, yF - 0.85, 2.3)], cam_dist=4.2, cam_h=1.75)
    export.empty("slot_cabinet_l", cab_l)
    export.empty("slot_cabinet_r", cab_r)
    reading_card(h)
    return h.finish()


# round 7: the Reading section's intro card (BUILD.md write_ / cam_read_). A cream card clipped
# into a small walnut frame on a table-top easel at the front-right corner of the counter, in
# the strip the vendor's counter books leave free (x 0.64-0.95, the front 0.25 m).
CARD_W, CARD_H = 0.26, 0.19                         # writing area (write_reading_card)
CARD_POS = (0.79, -1.32)                            # on the counter, clear of the props
CARD_YAW = -0.18                                    # turned a little toward the middle
CARD_LEAN = math.radians(14)


def reading_card(h):
    rail = 0.022
    Hh = CARD_H + 2 * rail
    cz = COUNTER_TOP + (Hh / 2) * math.cos(CARD_LEAN) + 0.002
    F = boards.face_frame((CARD_POS[0], CARD_POS[1], cz), yaw=CARD_YAW, lean=CARD_LEAN)
    boards.easel_card("reading_card", F, CARD_W, CARD_H, frame=h.frame, back=h.wood,
                      clip=h.extra_brass, base_z=COUNTER_TOP, rail=rail)
    boards.read_camera("reading_card", F, CARD_W, CARD_H, lift=0.03)


def section_standins(secs):
    """Render-only stand-in books for sections whose vendor set (prop_books_<key>) is not on disk
    yet: roughly the section's book count on the lowest board plus a few on the next, so the
    preview shows the intended fill. Not exported."""
    env = state.env_collection()
    R = state.rng
    B = Part("env_section_books", "bookcloth", var=0.12)
    G = Part("env_section_bands", "brass", var=0.05)
    missing = []
    for s in secs:
        if pipeline.vendor_props([("prop_books_" + s["key"], s["slot"])], rotate=True):
            continue
        missing.append(s["key"])
        loc = s["_local"]
        F = _frame(loc["origin"], loc["rot"]) @ _T(*loc["slot"])
        for bi, b in enumerate(s["boards"]):
            n = s["books"] if bi == 0 else max(2, s["books"] // 3)
            ox, oy, oz = b["offset"]
            x = ox + 0.02
            clear = b["clear_height"] or 0.32
            for k in range(n):
                w = R.uniform(0.026, 0.052)
                if x + w > ox + b["width"] - 0.02:
                    break
                hgt = min(clear - 0.02, R.uniform(0.19, 0.27))
                d = R.uniform(0.14, 0.2)
                tint = R.choice(BINDINGS)
                B.mbox(F @ _T(x + w / 2, oy + 0.008 + d / 2, oz + hgt / 2), (w - 0.002, d, hgt), tint=tint,
                       bevel=0, grain=2)
                for zz in (0.035, hgt - 0.04):
                    G.mbox(F @ _T(x + w / 2, oy + 0.006, oz + zz), (w - 0.004, 0.003, 0.006), bevel=0)
                x += w + (R.uniform(0.0, 0.004))
    B.finish(env)
    G.finish(env)
    if missing:
        print("[buecher] preview stand-in books for:", ", ".join(missing))
    return missing


def preview(objs):
    env = state.env_collection()
    yF = -D / 2
    secs = BS.sections()
    section_standins(secs)
    if pipeline.vendor_props([("prop_books_shelf_1", "slot_shelf_1"), ("prop_books_shelf_2", "slot_shelf_2"),
                              ("prop_books_counter", "slot_counter")]):
        return _lights_and_camera(yF, secs)
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
    books.finish(env)
    return _lights_and_camera(yF, secs)


def _lights_and_camera(yF, secs):
    render.lights_at_markers(energy=100)
    render.add_light("env_fill", 'AREA', (0, 0.2, 2.5), 200, size=2.0)
    lx, ly, lz = LANTERN
    render.add_light("env_lantern", 'POINT', (lx, ly, lz - 0.15), 30, size=0.08)
    # the small bulb under each cabinet top: light the spines behind the glass (round 3: brighter,
    # the round-2 Cycles preview showed the cabinets nearly empty)
    cab_y = yF - CAB_D / 2 + 0.05
    for xc in (-W / 2 + 0.1 + CAB_W / 2, W / 2 - 0.1 - CAB_W / 2):
        render.add_light("env_cabinet", 'POINT', (xc, cab_y, 2.07), 16, size=0.03)
        render.add_light("env_cabinet_mid", 'POINT', (xc, cab_y + 0.02, 1.68), 7, size=0.04)
        render.add_light("env_cabinet_low", 'POINT', (xc, cab_y + 0.02, 1.25), 6, size=0.05)
    # the bulb strings under each wing canopy light the books and signs below them
    for unit in ("wing_l", "wing_r"):
        (ox, oy), a = BS.wing_frame(unit)
        F = _frame((ox, oy), a)
        L = BS.wing_length(unit)
        p = F @ Vector((L / 2, -0.22, 1.66))
        q = F @ Vector((L / 2, 0.15, 0.6))
        render.add_light("env_wing", "AREA", tuple(p), 30, size=0.45, target=tuple(q))
        render.add_light("env_wing_low", 'POINT', tuple(F @ Vector((L / 2, -0.5, 0.9))), 9, size=0.3)
    # the carts sit under the eave bulbs and the front light
    for unit in ("cart_l", "cart_r"):
        (ox, oy), a = BS.cart_frame(unit)
        Wc = BS.cart_width(unit)
        render.add_light("env_cart", 'POINT', (ox + Wc / 2, oy - 0.55, 1.75), 14, size=0.25)
    render.add_light("env_neighbour", 'POINT', (-5.4, -1.6, 2.6), 170, size=0.6)
    return render.camera((-3.3, -7.9, 2.1), (0.25, -1.3, 1.3), lens=28)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=51)
