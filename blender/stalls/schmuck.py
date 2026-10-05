"""Christbaumschmuck: the ornament shop (ADR 0004), replacing deco_schmuck at the deco-schmuck place.

A 4.5 m white-painted hut, richly trimmed in red and gold: a carved pediment (Ziergiebel) on the
front eave carries the sign "Christbaumschmuck" in Fraktur on a glowing cream cartouche, outlined
by fairy bulbs and topped by a gold star; a scalloped valance with star cut-outs runs under the
eave, carved scallops edge the red bargeboards, fretwork corbels sit under the header and turned
finials crown the gables. The front has three bays:

    left bay   a red pedestal cupboard with a glazed display case on top (slot_cabinet, inside)
    centre     the counter (top at 1.05 m) with tiered shelves on the back wall
    right bay  a low stepped dais for the small display tree (slot_tree), open down to 0.42 m

Four brass hanging rails (slot_rail_1..4) carry the vendor's ornaments: one in front of the
counter, one inside over the counter's back edge, one across each bay. A fir garland with
baubles hangs from the header. The vendor's goods are separate sets (prop_schmuck_<group>.glb).

    /home/claude/tools/bpy-venv/bin/python blender/stalls/schmuck.py [--no-render] [--no-lite]
Outputs site/public/models/stall_schmuck.glb + stall_schmuck.lite.glb and
blender/stalls/schmuck_slots.json (rail lengths, tree dais, glass case, shelf tiers).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import export, geo, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_schmuck"
HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS_JSON = os.path.join(HERE, "schmuck_slots.json")
W, D = 4.5, 2.6
EAVE, RIDGE = 2.85, 4.0
X_BAY = 1.28                 # inner front posts (bay | counter | bay)
OPEN_TOP = 2.2
# left bay: pedestal cupboard + glass case
PED_TOP = 0.86               # pedestal top board's upper surface
CASE_W, CASE_D = 0.80, 0.46
CASE_H = 0.62                # glass case height above the pedestal top
CASE_SHELF = 0.30            # inner glass shelf height above the case floor
# right bay: tree dais
DAIS_TOP = 0.42
TREE_MAX_H = 1.45            # tallest tree that clears rail_4's ornaments
# tiered shelves on the back wall (top surface z, depth from the back wall)
TIERS = ((1.24, 0.42), (1.54, 0.33), (1.84, 0.24))
TIER_X = 1.36                # half length
RAIL_R = 0.011
SLOTS = {}


RX = Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()


def face_M(x, y, z):
    """Frame of a carved board facing -Y: local XY -> world XZ, extrusion toward -Y."""
    return Matrix.Translation((x, y, z)) @ RX


# ------------------------------------------------------------------------------- the pediment
def arch_pts(half, z_shoulder, z_peak, n):
    """Points of a segmental arch from (-half, z_shoulder) over (0, z_peak) to (half, z_shoulder)."""
    s = z_peak - z_shoulder
    R = (half * half + s * s) / (2 * s)
    cz = z_peak - R
    a0 = math.atan2(z_shoulder - cz, -half)
    a1 = math.atan2(z_shoulder - cz, half)
    return [(R * math.cos(a0 + (a1 - a0) * i / n), cz + R * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)], (R, cz)


def pediment_outline(lite):
    """2D outline (u, v) of the carved pediment, v up from its base; counter-clockwise."""
    n = 10 if lite else 22
    arch, _ = arch_pts(1.24, 0.52, 0.94, n)
    sc = 4 if lite else 9
    right = []                                             # concave scroll at the right end
    for i in range(sc + 1):
        a = math.radians(270 - 90 * i / sc)
        right.append((1.62 + 0.32 * math.cos(a), 0.44 + 0.32 * math.sin(a)))
    pts = [(-1.62, 0.0), (1.62, 0.0)] + right[1:] + [(1.30, 0.52), (1.24, 0.52)]
    pts += list(reversed(arch))[1:-1]
    pts += [(-1.24, 0.52), (-1.30, 0.52)]
    pts += [(-u, v) for (u, v) in reversed(right[1:])]
    return pts


def pediment(h, T, SL, snow, lite):
    """Carved red pediment on the front eave with a cream cartouche, gold beads, star cut-outs,
    a gold star finial, braces back to the roof, a bulb outline and a snow strip on its coping.
    Returns the sign centre."""
    sl = h.front_slope
    e = sl.point(0, 0)
    zb = e.z + 0.005
    yp = e.y - 0.065                                       # just in front of the fascia
    dep = 0.045
    M = face_M(0, yp, zb)
    holes = [] if lite else [geo.star_polygon(s * 1.43, 0.2, 0.075, 0.032, 5) for s in (-1, 1)]
    T.shape(pediment_outline(lite), holes, depth=dep, M=M, band="red", bevel=0.003)
    # gold bead along the arch and scrolls (a thin tube just proud of the face)
    edge = [p for p in pediment_outline(lite) if p[1] > 0.02]
    edge = [p for p in edge if abs(p[0]) <= 1.6]
    edge.sort(key=lambda p: p[0])
    bead = [Vector((u * 0.985, yp - dep / 2 - 0.004, zb + v - 0.022)) for (u, v) in edge]
    T.tube(bead, 0.009, tseg=4 if lite else 6, band="gold")
    T.box((0, yp - dep / 2 - 0.006, zb + 0.03), (3.2, 0.014, 0.05), band="gold", grain=0)      # base moulding
    T.box((0, yp + 0.005, zb - 0.012), (3.3, dep + 0.05, 0.03), band="red", grain=0)          # base ledge
    # cream cartouche (paint_lit: it glows like a lit board) with an arched top
    arch, (R, cz) = arch_pts(1.06, 0.40, 0.76, 8 if lite else 18)
    cart = [(-1.06, 0.1), (1.06, 0.1)] + [p for p in reversed(arch)]
    Mc = face_M(0, yp - dep / 2 - 0.008, zb)
    SL.shape(cart, depth=0.014, M=Mc, band="cream", bevel=0.002)
    # carved letters (raised, deep green) on the cartouche
    Mt = face_M(0, yp - dep / 2 - 0.02, zb + 0.30)
    T.flat_text = True          # painted-on carved letters: one face each (the budget leaves room for goods)
    tw, th = T.text("Christbaumschmuck", state.font("fraktur_bold"), 0.40, 0.012, M=Mt, band="green",
                    tint=(0.5, 0.62, 0.5), max_width=1.94, resolution=1, bevel=0.0)
    T.flat_text = False
    print(f"[schmuck] sign letters {tw:.2f} x {th:.2f} m")
    # little gold stars either side of the lettering
    for s in (-1, 1):
        T.shape(geo.star_polygon(0, 0, 0.045, 0.019, 5), depth=0.008,
                M=face_M(s * 0.93, yp - dep / 2 - 0.018, zb + 0.53), band="gold")
    # finial: turned post and an eight-point gold star on the peak
    top = zb + 0.94
    h.frame.cyl((0, yp, top + 0.07), 0.035, 0.045, 0.14, seg=8 if lite else 12, tint="walnut")
    h.frame.sphere((0, yp, top + 0.16), 0.045, seg=8 if lite else 12, rings=5 if lite else 8, tint="walnut")
    T.shape(geo.star_polygon(0, 0, 0.17, 0.075, 8), depth=0.03, M=face_M(0, yp, top + 0.36), band="gold",
            bevel=0.003)
    # braces from the pediment's back to the roof
    for u in (-0.85, 0.85):
        a = Vector((u, yp + dep / 2, zb + 0.62))
        s = 0.42
        b = sl.point(u, s, 0.04)
        h.frame.slab(a, b, 0.05, 0.04, up=(1, 0, 0), tint="walnut")
    # bulbs along the arch, a little in front of the face
    anchors = [Vector((u, yp - 0.05, zb + v + 0.035)) for (u, v) in arch_pts(1.24, 0.52, 0.94, 8)[0]]
    cp.bulb_string(h.bulbs, h.wire, anchors, sag=0.006, spacing=0.17, seg=h.bulb_detail[0],
                   rings=h.bulb_detail[1], drop=0.03)
    # snow strip along the coping (arch top), a soft half-round mound
    pts = arch_pts(1.24, 0.52, 0.94, 10 if lite else 24)[0]
    rings = []
    th_s, wd = 0.035, dep + 0.025
    prof = [(-wd / 2, -0.004), (-wd / 2 + 0.008, th_s * 0.6), (0, th_s), (wd / 2 - 0.008, th_s * 0.62),
            (wd / 2, -0.004)]
    for i, (u, v) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        nrm = Vector((-t.y, t.x))                             # outward (up) in the face plane
        k = 0.8 + 0.4 * math.sin(i * 1.7) * 0.5
        rings.append([Vector((u + nrm.x * hh * k, yp + yy, zb + v + nrm.y * hh * k)) for (yy, hh) in prof])
    snow.loft(rings, closed=False)
    return Vector((0, yp - dep / 2 - 0.03, zb + 0.32))


# ------------------------------------------------------------------------------- carving helpers
def corbel(T, x, side, y, z_top, size=0.22, lite=False):
    """Fretwork corbel under the header beside a post: the corner between post and header filled
    by a board with a concave quarter-circle edge and a small round cut-out, in the XZ plane,
    reaching `side` (+1 right / -1 left) from the post."""
    n = 4 if lite else 9
    pts = [(0.0, 0.0), (0.0, -size)]
    for i in range(1, n):
        a = math.radians(180 - 90 * i / n)
        pts.append((size + size * math.cos(a), -size + size * math.sin(a)))
    pts.append((size, 0.0))
    pts = list(reversed(pts))                              # counter-clockwise
    if side < 0:
        pts = [(-u, v) for (u, v) in reversed(pts)]
    holes = [] if lite else [geo.circle_polygon(side * size * 0.19, -size * 0.19, size * 0.08, 8)]
    T.shape(pts, holes, depth=0.03, M=face_M(x, y, z_top), band="red")


def rake_scallops(T, sl, lite):
    """Carved scalloped edge under the bargeboard at both rake ends of a slope."""
    for a_end, sgn in ((sl.a0, -1), (sl.a1, 1)):
        Mv = Matrix.Translation(sl.point(a_end + sgn * 0.003, 0.12, -0.11)) @ \
            Matrix((sl.U, sl.N, sl.A)).transposed().to_4x4()
        cp.valance(T, 0, sl.L - 0.32, 0, 0, 0.055, 0.065, 7, style="scallop", depth=0.022, band="red", M=Mv)
        p = sl.point(a_end + sgn * 0.033, sl.L / 2, 0.03)
        T.mbox(Matrix.Translation(p) @ sl.basis(), (0.012, sl.L, 0.03), grain=1, band="gold")


def gable_finials(h, T, lite):
    """Turned finial with a gold ball at the apex of each gable, plus a carved star board in the
    gable triangle (both side walls)."""
    for s in (-1, 1):
        x = s * (W / 2 + 0.28 + 0.03)
        h.frame.cyl((x, 0, RIDGE + 0.05), 0.04, 0.05, 0.42, seg=8 if lite else 12, tint="walnut")
        h.frame.cyl((x, 0, RIDGE + 0.29), 0.055, 0.03, 0.06, seg=8 if lite else 12, tint="walnut")
        T.sphere((x, 0, RIDGE + 0.37), 0.05, seg=8 if lite else 10, rings=5 if lite else 7, band="gold")
        # gable star board on the wall face, under the apex
        xw = s * (W / 2 + 0.005)
        M = Matrix.Translation((xw, 0, RIDGE - 0.62)) @ Euler((math.pi / 2, 0, s * math.pi / 2)).to_matrix().to_4x4()
        T.shape(geo.circle_polygon(0, 0, 0.24, 12 if lite else 18),
                [] if lite else [geo.star_polygon(0, 0, 0.17, 0.07, 6)], depth=0.025, M=M, band="red")
        T.torus((xw + s * 0.014, 0, RIDGE - 0.62), 0.235, 0.008, seg=12 if lite else 18, tseg=3,
                rot=(0, math.pi / 2, 0), band="gold")


# ------------------------------------------------------------------------------- furniture
def panel_front(P, x0, x1, y, z0, z1, band="red", bead="gold", lite=False):
    """Raised-panel door front: frame boards and a proud panel with a gold bead."""
    w, hh = x1 - x0, z1 - z0
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    P.box((cx, y, cz), (w, 0.022, hh), band=band, grain=2)
    P.box((cx, y - 0.014, cz), (w - 0.12, 0.014, hh - 0.12), band=band, grain=2)
    if not lite:
        for (xx, zz, sx, sz) in ((cx, z1 - 0.06, w - 0.12, 0.008), (cx, z0 + 0.06, w - 0.12, 0.008),
                                 (x0 + 0.06, cz, 0.008, hh - 0.12), (x1 - 0.06, cz, 0.008, hh - 0.12)):
            P.box((xx, y - 0.016, zz), (sx, 0.01, sz), band=bead, bevel=0, grain=0 if sx > sz else 2)


def glass_case(h, glass, velvet, lite):
    """Red pedestal cupboard and a glazed display case on it in the left bay (front flush with
    the hut front). slot_cabinet is on the case's velvet floor, centred."""
    P, T = h.paint, h.trim
    xc = -(X_BAY + (W / 2 - 0.1 - X_BAY) / 2) - 0.02
    y0 = h.yF - 0.02                                      # case / pedestal front
    yc = y0 + CASE_D / 2
    w, d = CASE_W, CASE_D
    # pedestal cupboard: carcass, plinth, two panelled doors, top board
    P.box((xc, yc + 0.01, (0.1 + PED_TOP - 0.03) / 2 + 0.0), (w, d - 0.02, PED_TOP - 0.03 - 0.1), band="red",
          grain=2)
    h.frame.box((xc, yc - 0.005, 0.13), (w + 0.04, d + 0.02, 0.07), tint="walnut")
    for (a, b) in ((xc - w / 2 + 0.02, xc - 0.006), (xc + 0.006, xc + w / 2 - 0.02)):
        panel_front(P, a, b, y0 - 0.012, 0.19, PED_TOP - 0.06, lite=lite)
    for x in (xc - 0.04, xc + 0.04):
        h.brass.sphere((x, y0 - 0.04, 0.55), 0.012, seg=8, rings=5)
    h.frame.box((xc, yc - 0.01, PED_TOP - 0.015), (w + 0.05, d + 0.04, 0.03), tint="walnut", bevel_segments=2)
    # glass case: corner posts, rails, glazing, inner shelf, crest
    z0, z1 = PED_TOP, PED_TOP + CASE_H
    cw, cd = w - 0.04, d - 0.06
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((xc + sx * (cw / 2 - 0.015), yc + sy * (cd / 2 - 0.015), (z0 + z1) / 2), (0.03, 0.03, z1 - z0),
                  band="red", grain=2)
            T.sphere((xc + sx * (cw / 2 - 0.015), yc + sy * (cd / 2 - 0.015), z1 + 0.045), 0.022,
                     seg=8 if lite else 10, rings=5 if lite else 7, band="gold")
    for z in (z0 + 0.025, z1 - 0.02):
        for sy in (-1, 1):
            P.box((xc, yc + sy * (cd / 2 - 0.015), z), (cw, 0.03, 0.04 if z < z1 - 0.1 else 0.035), band="red")
        for sx in (-1, 1):
            P.box((xc + sx * (cw / 2 - 0.015), yc, z), (0.03, cd, 0.04 if z < z1 - 0.1 else 0.035), band="red")
    P.box((xc, yc, z1 + 0.01), (cw + 0.04, cd + 0.04, 0.025), band="red")           # top frame / cornice
    T.box((xc, yc - cd / 2 - 0.022, z1 + 0.012), (cw + 0.03, 0.008, 0.012), band="gold", bevel=0)
    # glass: front, back, sides and top
    gz = (z0 + 0.045 + z1 - 0.04) / 2
    gh = z1 - z0 - 0.085
    glass.box((xc, yc - cd / 2 + 0.012, gz), (cw - 0.05, 0.005, gh), bevel=0, var=0.0)
    glass.box((xc, yc + cd / 2 - 0.012, gz), (cw - 0.05, 0.005, gh), bevel=0, var=0.0)
    for sx in (-1, 1):
        glass.box((xc + sx * (cw / 2 - 0.012), yc, gz), (0.005, cd - 0.05, gh), bevel=0, var=0.0)
    glass.box((xc, yc, z1 + 0.024), (cw - 0.02, cd - 0.02, 0.004), bevel=0, var=0.0)
    glass.box((xc, yc, z0 + CASE_SHELF), (cw - 0.07, cd - 0.07, 0.008), bevel=0, var=0.0)   # inner shelf
    for sx in (-1, 1):
        for sy in (-1, 1):
            h.brass.box((xc + sx * (cw / 2 - 0.04), yc + sy * (cd / 2 - 0.04), z0 + CASE_SHELF - 0.008),
                        (0.012, 0.012, 0.01), bevel=0)
    velvet.box((xc, yc, z0 + 0.004), (cw - 0.06, cd - 0.06, 0.008), bevel=0, var=0.03)
    # carved crest on top of the case: arched board with a star cut-out
    crest = [(-0.24, 0.0), (0.24, 0.0)] + [(0.24 * math.cos(math.pi * i / 12), 0.13 * math.sin(math.pi * i / 12))
                                         for i in range(1, 12)]
    T.shape(crest, [] if lite else [geo.star_polygon(0, 0.06, 0.04, 0.017, 5)], depth=0.02,
            M=face_M(xc, yc - cd / 2 + 0.01, z1 + 0.022), band="red")
    # a small warm bulb under the case top lights the goods
    h.wire.cyl((xc, yc + cd / 2 - 0.08, z1 - 0.03), 0.01, 0.01, 0.025, seg=8)
    h.bulbs.sphere((xc, yc + cd / 2 - 0.08, z1 - 0.06), 0.018, seg=8 if not lite else 5, rings=5 if not lite else 3,
                   scale=(1, 1, 1.3))
    pos = (round(xc, 4), round(yc, 4), round(z0 + 0.008, 4))
    export.empty("slot_cabinet", pos)
    SLOTS["slot_cabinet"] = {"position": list(pos), "inner_size": [round(cw - 0.06, 3), round(cd - 0.06, 3),
                                                                     round(CASE_H - 0.06, 3)],
                             "shelf_height": CASE_SHELF - 0.004,
                             "about": "on the velvet floor of the glass case (built into the hut), centred; a "
                                      "glass shelf runs at shelf_height above it. The case front is glass."}


def tree_dais(h, lite):
    """Low two-step dais in the right bay for the display tree; slot_tree on its top, centred."""
    P, T = h.paint, h.trim
    xc = X_BAY + (W / 2 - 0.1 - X_BAY) / 2 + 0.02
    yc = h.yF + 0.46
    P.box((xc, yc, 0.21), (0.82, 0.66, 0.2), band="red")
    T.box((xc, yc - 0.333, 0.29), (0.80, 0.008, 0.014), band="gold", bevel=0)
    h.frame.box((xc, yc, 0.33), (0.62, 0.5, 0.06), tint="walnut", bevel_segments=2)
    h.frame.box((xc, yc, DAIS_TOP - 0.015), (0.5, 0.4, 0.03), tint="honey")
    pos = (round(xc, 4), round(yc, 4), DAIS_TOP)
    export.empty("slot_tree", pos)
    SLOTS["slot_tree"] = {"position": list(pos), "top_size": [0.5, 0.4], "max_height": TREE_MAX_H,
                          "about": "top of the dais in the right bay; the bay's lower front wall is 0.42 m, so the "
                                   "tree shows from the lane down to its pot."}


def tiered_shelves(h, lite):
    """Three stepped shelves on the back wall behind the counter: honey boards on stepped side
    cheeks, red front edges with a gold bead. slot_shelf_1..3 on each tier's centre."""
    P, T = h.paint, h.trim
    yb = h.yB - 0.04
    zs = [t[0] for t in TIERS]
    ds = [t[1] for t in TIERS]
    # stepped cheek outline in (distance in front of the back wall, z), counter-clockwise
    cheek = [(0.0, 0.95), (ds[0], 1.07), (ds[0], zs[0] - 0.03), (ds[1], zs[0] - 0.03), (ds[1], zs[1] - 0.03),
             (ds[2], zs[1] - 0.03), (ds[2], zs[2] - 0.03), (0.0, zs[2] + 0.02)]
    for xs in (-TIER_X, 0.0, TIER_X):
        # local x -> -Y (out from the wall), local y -> +Z
        M = Matrix.Translation((xs, yb, 0)) @ Euler((math.pi / 2, 0, -math.pi / 2)).to_matrix().to_4x4()
        h.frame.shape(cheek, depth=0.03, M=M, tint="honey")
    for i, (z, dpt) in enumerate(TIERS):
        h.frame.box((0, yb - dpt / 2, z - 0.014), (2 * TIER_X + 0.06, dpt, 0.028), tint="honey", grain=0)
        P.box((0, yb - dpt - 0.006, z - 0.005), (2 * TIER_X + 0.08, 0.016, 0.06), band="red", grain=0)
        T.box((0, yb - dpt - 0.016, z - 0.0), (2 * TIER_X + 0.07, 0.006, 0.01), band="gold", bevel=0)
        pos = (0.0, round(yb - dpt / 2, 4), z)
        export.empty(f"slot_shelf_{i + 1}", pos)
        SLOTS[f"slot_shelf_{i + 1}"] = {"position": list(pos), "length": round(2 * TIER_X, 3), "depth": dpt,
                                        "clear_height": round((TIERS[i + 1][0] if i + 1 < len(TIERS) else 2.3) - z, 3)}


def brass_rail(h, n, x0, x1, y, z, hangers):
    """A brass hanging rail (tube) from x0 to x1 with ball ends; hangers: [(x, (top point))]
    rods from the rail up to a support. slot_rail_<n> at the rail's left end."""
    lite = state.lite()
    h.brass.cyl(((x0 + x1) / 2, y, z), RAIL_R, RAIL_R, x1 - x0, seg=6 if lite else 8, rot=(0, math.pi / 2, 0))
    for x in (x0, x1):
        h.brass.sphere((x, y, z), RAIL_R * 2.1, seg=6 if lite else 8, rings=4 if lite else 5)
    for (x, top) in hangers:
        h.brass.slab((x, y, z + 0.005), top, 0.007, 0.007, up=(1, 0, 0), bevel=0)
    export.empty(f"slot_rail_{n}", (x0, y, z))
    SLOTS[f"slot_rail_{n}"] = {"position": [round(x0, 4), round(y, 4), round(z, 4)], "length": round(x1 - x0, 3),
                               "rail_radius": RAIL_R}


def rails(h):
    yF = h.yF
    # 1: in front of the counter, on forged brackets from the header
    y1, z1 = yF - 0.13, 2.08
    brass_rail(h, 1, -X_BAY + 0.12, X_BAY - 0.12, y1, z1,
               [(x, (x, y1, 2.265)) for x in (-X_BAY + 0.2, 0.0, X_BAY - 0.2)])
    # 2: inside over the counter's back edge, hung from a tie beam between the side wall plates
    y2, z2 = yF + 0.52, 2.16
    h.frame.box((0, y2, 2.72), (W - 0.1, 0.09, 0.11), tint="walnut")
    brass_rail(h, 2, -X_BAY + 0.1, X_BAY - 0.1, y2, z2, [(x, (x, y2, 2.665)) for x in (-0.9, 0.9)])
    # 3, 4: across each bay, in front of the header
    for n, (a, b) in ((3, (-W / 2 + 0.22, -X_BAY - 0.1)), (4, (X_BAY + 0.1, W / 2 - 0.22))):
        brass_rail(h, n, a, b, y1, z1, [(x, (x, y1, 2.265)) for x in (a + 0.08, b - 0.08)])
    for n in (1, 3, 4):
        SLOTS[f"slot_rail_{n}"]["clear_drop"] = round(z1 - (COUNTER_TOP + 0.45) if n == 1 else
                                                      z1 - (PED_TOP + CASE_H + 0.08) if n == 3 else
                                                      z1 - (DAIS_TOP + TREE_MAX_H), 3)
    SLOTS["slot_rail_2"]["clear_drop"] = round(z2 - 1.85, 3)
    # forged brackets of the front rails: a plate on the header and an arm out to the hanger
    for (x0, x1) in ((-X_BAY + 0.12, X_BAY - 0.12), (-W / 2 + 0.22, -X_BAY - 0.1), (X_BAY + 0.1, W / 2 - 0.22)):
        for x in ([x0 + 0.08, 0.0, x1 - 0.08] if x1 - x0 > 1.5 else [x0 + 0.08, x1 - 0.08]):
            h.iron.box((x, yF - 0.055, 2.29), (0.035, 0.008, 0.1), bevel=0)
            h.iron.slab((x, yF - 0.06, 2.27), (x, y1, 2.27), 0.014, 0.01, up=(0, 0, 1), bevel=0)


# ------------------------------------------------------------------------------- build
def lower_walls(h):
    """Lower front walls per bay: none in the left bay (the pedestal is the front), counter
    height in the centre, 0.42 m in the right bay, each with painted rails."""
    P = h.paint
    yF = h.yF
    a, b = -X_BAY + 0.05, X_BAY - 0.05
    h._wall('x', a, b, yF + 0.02, lambda c: COUNTER_TOP - 0.07, outward=-1, z0=0.1)
    for z in (0.28, 0.82):
        P.box((0, yF - 0.032, z), (b - a, 0.022, 0.09), band="red")
        h.trim.box((0, yF - 0.045, z + 0.03), (b - a - 0.02, 0.008, 0.012), band="gold", bevel=0)
    a2, b2 = X_BAY + 0.05, W / 2 - 0.1
    h._wall('x', a2, b2, yF + 0.02, lambda c: DAIS_TOP - 0.01, outward=-1, z0=0.1)
    P.box(((a2 + b2) / 2, yF - 0.03, DAIS_TOP - 0.02), (b2 - a2 + 0.04, 0.05, 0.04), band="red")
    # carved gold stars on the counter front
    for x in (-0.8, 0.0, 0.8):
        h.trim.shape(geo.star_polygon(0, 0, 0.12, 0.05, 5), depth=0.016, M=face_M(x, yF - 0.04, 0.55), band="gold")


def build(lite):
    SLOTS.clear()
    h = Hut("schmuck", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='x', ov_eave=0.38, ov_gable=0.28,
            wall="vertical", wall_band="white", frame_tint="walnut", roof_tint="dark", inner_tint="pine",
            counter_tint="walnut", plank_w=0.14, bulb_spacing=0.22, counter_depth=0.56, counter_over=0.2,
            front_posts=[-W / 2 + 0.05, -X_BAY, X_BAY, W / 2 - 0.05], shingle_size=(0.32, 0.21),
            bulb_detail=(5, 3), open_top=OPEN_TOP, plank_bevel=0.0)
    yF = h.yF
    P = h.paint
    # outward trim in 'paint_glow' (stays readable under the site's moonlight), sign board 'paint_lit'
    h.trim = T = h.part("trim", "paint_glow", var=0.04)
    SL = h.part("sign", "paint_lit", var=0.02)
    h.brass = h.part("brass", "brass", var=0.03)
    glass = h.part("glass", "glass_clear", var=0.0)
    velvet = h.part("velvet", "fabric_red", var=0.03)
    h.build_carcass(front_lower=False)
    lower_walls(h)
    h.build_counter(x0=-X_BAY + 0.06, x1=X_BAY - 0.06, brackets=3, grid=0.3)
    tiered_shelves(h, lite)
    h.build_roof(cover="shingles", fascia_band="red", barge_band="red", barge_part=T)
    h.build_snow(drifts=3, nx=None if lite else 16)
    for sl in h.slopes:
        rake_scallops(T, sl, lite)
    gable_finials(h, T, lite)
    # front eave: scalloped valance with star cut-outs and a gold strip
    sl = h.front_slope
    ez = sl.point(0, 0, -0.03).z - 0.05
    ye = sl.point(0, 0).y + 0.03
    cp.valance(T, sl.a0 + 0.02, sl.a1 - 0.02, ye, ez, 0.12, 0.09, 15, style="scallop", holes="star",
               band="red", depth=0.022, hole_r=0.042)
    T.box((0, ye - 0.016, ez - 0.012), (sl.a1 - sl.a0 - 0.06, 0.01, 0.022), band="gold", bevel=0)
    # pediment with the sign, its snow strip
    snow_p = Part("snow_2", "snow", var=0.02)
    sign_c = pediment(h, T, SL, snow_p, lite)
    h.snow.append(snow_p)
    # red-and-gold posts, corbels under the header
    for x in h.front_posts:
        z0 = COUNTER_TOP if abs(x) < X_BAY + 0.01 else 0.12
        P.box((x, yF - 0.008, (z0 + OPEN_TOP) / 2), (0.115, 0.018, OPEN_TOP - z0), band="red", grain=2)
        for z in (OPEN_TOP - 0.05,) + ((z0 + 0.04,) if z0 > 0.5 else ()):
            T.box((x, yF - 0.02, z), (0.13, 0.02, 0.035), band="gold")
        for side in (-1, 1):
            if abs(x + side * 0.06) > W / 2 - 0.05:
                continue
            corbel(T, x + side * 0.058, side, yF - 0.03, OPEN_TOP, size=0.22, lite=lite)
    # corner boards; red rails with a gold bead along the side walls
    for x in (h.x0 + 0.05, h.x1 - 0.05):
        P.box((x, h.yB, EAVE / 2), (0.13, 0.13, EAVE), band="red", grain=2)
    for sx in (-1, 1):
        for z in (0.28, 0.82, 2.05):
            P.box((sx * (W / 2 + 0.012), 0, z), (0.022, D - 0.16, 0.09), band="red")
            T.box((sx * (W / 2 + 0.025), 0, z + 0.03), (0.008, D - 0.18, 0.012), band="gold", bevel=0)
    # counter lip in red with a gold bead
    y_front = yF - h.counter_over
    P.box((0, y_front - 0.026, COUNTER_TOP - 0.06), (2 * X_BAY - 0.1, 0.02, 0.08), band="red")
    T.box((0, y_front - 0.038, COUNTER_TOP - 0.03), (2 * X_BAY - 0.12, 0.01, 0.014), band="gold", bevel=0)
    glass_case(h, glass, velvet, lite)
    tree_dais(h, lite)
    rails(h)
    # fir garland with red and gold baubles along the header, in three spans
    gy, gz = yF - 0.065, OPEN_TOP - 0.05      # below the valance's line of sight
    xs = [-W / 2 + 0.1, -X_BAY, X_BAY, W / 2 - 0.1]
    for a, b in zip(xs[:-1], xs[1:]):
        cp.fir_garland(h.fir, h.beads, (a, gy, gz), (b, gy, gz), sag=0.1 if b - a > 1.5 else 0.06, radius=0.04,
                       tufts_per_m=None if lite else 15, bead_every=0.2)
    # bulbs: front eave (and down the front rakes), inside
    h.eave_bulbs(sides=False)
    h.interior_bulbs(xs=(-1.7, 1.7), y=0.0, z=2.4)
    lights = [(0, 0.05, 2.5), (0, yF - 0.8, 2.45)]
    cam_t = (0.0, yF + 0.3, 1.62)
    cam_v = (0.0, yF - 4.05, 1.8)
    export.empty("slot_counter", (0, h.counter_y, COUNTER_TOP))
    export.empty("slot_vendor", (0, (h.yB - 0.45 + yF + h.counter_depth - h.counter_over) / 2, 0.13))
    export.empty("slot_sign", tuple(sign_c))
    export.empty("slot_front", (0, yF - h.counter_over - 0.9, 0.0))
    export.empty("cam_target", cam_t)
    export.empty("cam_view", cam_v, look_at=cam_t)
    for i, p in enumerate(lights):
        export.empty(f"light_{i}", p)
    SLOTS["slot_counter"] = {"position": [0.0, round(h.counter_y, 4), COUNTER_TOP],
                             "length": round(2 * X_BAY - 0.12, 3), "depth": h.counter_depth}
    objs = h.finish()
    if not lite:
        write_slots()
    return objs


def write_slots():
    doc = {"about": "Christbaumschmuck ornament shop (carpenter, blender/stalls/schmuck.py -> stall_schmuck.glb). "
                    "Slot data for the vendor's goods. slot_rail_<n> sits at the rail's LEFT end (visitor's view) on "
                    "the rail's centre line; the rail runs along +X for length metres; ornaments hang anywhere along "
                    "it (about 0.12 m apart reads well); clear_drop is the free height under the rail. Rails 1, 3 "
                    "and 4 hang in front of the header (1 over the counter, 3 over the glass case, 4 over the tree); "
                    "rail 2 hangs inside over the counter's back edge.",
           "frame": "Stall frame: Blender metres, Z up, origin on the ground at the footprint centre, front toward -Y "
                    "(three.js: x = x, y = z, z = -y). All slots have no rotation.",
           "footprint": [W, D], "slots": SLOTS}
    with open(SLOTS_JSON, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")


# ------------------------------------------------------------------------------- preview
def standin_goods():
    """Render-only stand-ins for the vendor's ornaments (used when no prop_schmuck_* set is on
    disk): baubles on the rails, a small lit tree on the dais, figures in the glass case and
    boxes of baubles on the tiers. Not exported."""
    env = state.env_collection()
    R = state.rng
    red = Part("env_orn_red", "ornament_red", var=0.08)
    gold = Part("env_orn_gold", "ornament_gold", var=0.08)
    thread = Part("env_orn_thread", "wire", var=0.0)
    caps = Part("env_orn_caps", "brass", var=0.05)
    fir = Part("env_tree", "fir", var=0.15)
    bulbs = Part("env_tree_bulbs", "bulb_warm", var=0.03)
    wood = Part("env_wood", "wood", var=0.1)
    tints = [None, (0.35, 0.55, 1.4), (0.5, 1.2, 0.6), (1.2, 1.15, 1.2)]
    for n, s in SLOTS.items():
        if not n.startswith("slot_rail_"):
            continue
        x0, y, z = s["position"]
        k = int(s["length"] / 0.11)
        for i in range(k):
            x = x0 + 0.05 + i * s["length"] / k
            drop = R.uniform(0.08, min(0.3, s["clear_drop"] - 0.06))
            r = R.uniform(0.028, 0.045)
            c = Vector((x, y, z - drop - r))
            thread.tube([(x, y, z), (x, y, c.z + r + 0.012)], 0.0012, tseg=3)
            caps.cyl((x, y, c.z + r + 0.006), 0.008, 0.008, 0.014, seg=8)
            part = red if R.random() < 0.45 else gold
            part.sphere(c, r, seg=14, rings=9, tint=None if part is red else R.choice(tints))
    # tree on the dais: stacked cones, a pot, baubles and bulbs
    tx, ty, tz = SLOTS["slot_tree"]["position"]
    wood.cyl((tx, ty, tz + 0.09), 0.13, 0.11, 0.18, seg=16, tint="walnut")
    hgt = 1.3
    for i in range(6):
        z = tz + 0.22 + i * hgt * 0.15
        r = 0.42 * (1 - i / 6.5)
        fir.lathe([(0.001, z + 0.32), (r, z), (r * 0.7, z - 0.02), (0.001, z)], seg=18,
                  M=Matrix.Translation((tx, ty, 0)))
    gold.shape(geo.star_polygon(0, 0, 0.08, 0.035, 5), depth=0.02, M=face_M(tx, ty - 0.02, tz + 0.22 + hgt * 0.83))
    for i in range(40):
        t = R.random()
        z = tz + 0.3 + t * hgt * 0.75
        r = 0.4 * (1 - (z - tz - 0.22) / (hgt * 0.95))
        a = R.uniform(-math.pi * 0.95, -math.pi * 0.05)
        p = (tx + math.cos(a) * r, ty + math.sin(a) * r, z)
        if i % 2:
            bulbs.sphere(p, 0.012, seg=6, rings=4)
        else:
            (red if i % 4 else gold).sphere(p, 0.024, seg=10, rings=6)
    # glass case: a nutcracker-like figure, a candle arch, small boxes
    cx, cy, cz = SLOTS["slot_cabinet"]["position"]
    for dx, col in ((-0.22, red), (0.2, red)):
        col.cyl((cx + dx, cy, cz + 0.08), 0.03, 0.03, 0.16, seg=12)
        wood.cyl((cx + dx, cy, cz + 0.2), 0.026, 0.026, 0.08, seg=12, tint=(1.2, 0.9, 0.7))
        wood.cyl((cx + dx, cy, cz + 0.26), 0.03, 0.022, 0.06, seg=12, tint="dark")
    arch = [(-0.16, 0.0), (0.16, 0.0)] + [(0.16 * math.cos(math.pi * i / 10), 0.15 * math.sin(math.pi * i / 10))
                                         for i in range(1, 10)]
    wood.shape(arch, [], depth=0.02, M=face_M(cx, cy + 0.08, cz + 0.004), tint="honey")
    for i in range(5):
        a = math.pi * (i + 1) / 6
        bulbs.sphere((cx + 0.16 * math.cos(a), cy + 0.06, cz + 0.15 * math.sin(a) + 0.02), 0.008, seg=6, rings=4)
    for i in range(3):
        gold.sphere((cx - 0.08 + i * 0.08, cy - 0.08, cz + 0.3 + 0.03), 0.026, seg=10, rings=6,
                    tint=tints[i % 4])
    # tiers: rows of boxed baubles
    for i in (1, 2, 3):
        s = SLOTS[f"slot_shelf_{i}"]
        x0 = -s["length"] / 2 + 0.1
        y, z = s["position"][1], s["position"][2]
        x = x0
        while x < s["length"] / 2 - 0.15:
            w = R.uniform(0.18, 0.26)
            wood.box((x + w / 2, y, z + 0.025), (w - 0.02, min(0.18, s["depth"] - 0.05), 0.05), tint="pine")
            for j in range(3):
                (red if (j + i) % 2 else gold).sphere((x + 0.04 + j * (w - 0.08) / 2, y, z + 0.075), 0.03,
                                                     seg=10, rings=6, tint=None if (j + i) % 2 else R.choice(tints))
            x += w
    for p in (red, gold, thread, caps, fir, bulbs, wood):
        p.finish(env)


def preview(objs):
    import glob
    got = False
    for path in sorted(glob.glob(os.path.join(state.MODELS_DIR, "prop_schmuck_*.glb"))):
        if path.endswith(".lite.glb"):
            continue
        got = True
    if got:
        got = pipeline.vendor_sets("stall_schmuck.glb")
    if not got:
        standin_goods()
    render.lights_at_markers(energy=110)
    render.add_light("env_fill", 'AREA', (0, 0.2, 2.55), 230, size=2.4)
    yF = -D / 2
    render.add_light("env_case", 'POINT', tuple(Vector(SLOTS["slot_cabinet"]["position"]) + Vector((0, 0.05, 0.5))),
                     12, size=0.05)
    tp = Vector(SLOTS["slot_tree"]["position"])
    render.add_light("env_tree", 'POINT', tuple(tp + Vector((0, -0.45, 0.8))), 18, size=0.3)
    # the pediment's bulb outline and a lamp in front light the sign board
    render.add_light("env_sign", 'SPOT', (0, yF - 2.0, 2.2), 70, size=0.1, spot_size=math.radians(30),
                     spot_blend=0.4, target=(0, yF - 0.45, 2.85))
    render.add_light("env_neighbour", 'POINT', (-5.2, -1.8, 2.6), 160, size=0.6)
    return render.camera((-4.6, -8.3, 2.15), (0.25, -0.9, 2.0), lens=28)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=83)
