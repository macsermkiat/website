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
baubles hangs from the header over the bays. The vendor's goods are separate sets
(prop_schmuck_<group>.glb).

Round 9 (ADR 0004 revision, "the most dazzling stall in the market, not cluttered"): sparkle
comes from a few strong things against dark walnut, not from more stuff:
    mirror_0        an antique foxed pier glass on the upper back wall behind the tiers (material
                    mirror_foxed), walnut frame, gilt moulding and glazing bars; it doubles the
                    baubles and the canopy bulbs
    bulbs_1         three rows of small rice bulbs inside the canopy; light_0 near the ceiling centre
    bulbs_2         the glowing core of a large faceted eight-point star with gilt ribs on the ridge
    bulbs_0         the eave bulbs now run right round the roof edge (both eaves, all four rakes)
    rail 1          the glass-harmonica rail at 2.0 m with twelve brass rings (slot_harmonica_rail)
    bracket         a forged Ausleger on the left front post whose hook (slot_mirrorball) carries
                    the 18 cm mercury-glass bauble
    slot_pyramid    on the counter right of the Schwibbogen; slot_tinsel_1..3 anchor tinsel swags
The interior (lining, ceiling, tiers) is dark walnut so the goods read as points of light.

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
# round 9 (ADR 0004 revision): the sparkle pass
MIRROR_X = 1.50              # half width of the mirror glass on the back wall
MIRROR_Z = (1.10, 2.62)      # bottom and top of the glass (upper two thirds of the back wall)
HARM_Z = 2.00                # the glass-harmonica rail (also slot_rail_1)
HARM_N, HARM_PITCH = 12, 0.17
BALL_R = 0.09                # the 18 cm mercury-glass bauble on the corner bracket
CAM_DIST = 4.3               # cam_view distance in front of the hut front
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
    T.sphere((0, yp, top + 0.235), 0.032, seg=8 if lite else 10, rings=5 if lite else 7, band="gold")
    # (round 9: the star moved up to the ridge, see ridge_star; one hero star, not two stacked)
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
        h.frame.shape(cheek, depth=0.03, M=M, tint="dark")
    for i, (z, dpt) in enumerate(TIERS):
        h.frame.box((0, yb - dpt / 2, z - 0.014), (2 * TIER_X + 0.06, dpt, 0.028), tint="dark", grain=0)
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
    lite = state.lite()
    # 1: the glass-harmonica rail in front of the counter (round 9), on forged brackets from the
    # header: twelve brass curtain rings mark the hanging points of act_orn_harmonica_0..11
    y1, z1 = yF - 0.13, 2.08
    yh = yF - 0.15
    a, b = -X_BAY + 0.12, X_BAY - 0.12
    brass_rail(h, 1, a, b, yh, HARM_Z, [(x, (x, yh, 2.265)) for x in (-X_BAY + 0.2, 0.0, X_BAY - 0.2)])
    export.empty("slot_harmonica_rail", (a, yh, HARM_Z))
    span = (HARM_N - 1) * HARM_PITCH
    hooks = []
    for i in range(HARM_N):
        x = -span / 2 + i * HARM_PITCH
        h.brass.torus((x, yh, HARM_Z - 0.004), 0.016, 0.0022, seg=6, tseg=3,
                      rot=(0, math.pi / 2, 0))
        hooks.append(round(x - a, 4))
    SLOTS["slot_harmonica_rail"] = {
        "position": [round(a, 4), round(yh, 4), HARM_Z], "length": round(b - a, 3), "rail_radius": RAIL_R,
        "hooks_x": hooks, "hook_drop": 0.022, "clear_drop": round(HARM_Z - (COUNTER_TOP + 0.4), 3),
        "about": "the front rail at 2.0 m, the glass harmonica: hang act_orn_harmonica_0..11 left to right from "
                 "the bottoms of the twelve brass rings (x offsets hooks_x from this empty, along +X; ring "
                 "bottom hook_drop below the rail axis). The same rail is slot_rail_1 (kept for the round-8 set; "
                 "the harmonica set replaces prop_schmuck_rail_1)."}
    # 2: inside over the counter's back edge, hung from a tie beam between the side wall plates
    y2, z2 = yF + 0.52, 2.16
    h.frame.box((0, y2, 2.72), (W - 0.1, 0.09, 0.11), tint="walnut")
    brass_rail(h, 2, -X_BAY + 0.1, X_BAY - 0.1, y2, z2, [(x, (x, y2, 2.665)) for x in (-0.9, 0.9)])
    # 3, 4: across each bay, in front of the header
    for n, (a3, b3) in ((3, (-W / 2 + 0.22, -X_BAY - 0.1)), (4, (X_BAY + 0.1, W / 2 - 0.22))):
        brass_rail(h, n, a3, b3, y1, z1, [(x, (x, y1, 2.265)) for x in (a3 + 0.08, b3 - 0.08)])
    SLOTS["slot_rail_1"]["clear_drop"] = round(HARM_Z - (COUNTER_TOP + 0.4), 3)
    SLOTS["slot_rail_1"]["about"] = "same rail as slot_harmonica_rail"
    SLOTS["slot_rail_3"]["clear_drop"] = round(z1 - (PED_TOP + CASE_H + 0.08), 3)
    SLOTS["slot_rail_4"]["clear_drop"] = round(z1 - (DAIS_TOP + TREE_MAX_H), 3)
    SLOTS["slot_rail_2"]["clear_drop"] = round(z2 - 1.85, 3)
    # forged brackets of the front rails: a plate on the header and an arm out to the hanger
    for (x0, x1, yy) in ((a, b, yh), (-W / 2 + 0.22, -X_BAY - 0.1, y1), (X_BAY + 0.1, W / 2 - 0.22, y1)):
        for x in ([-X_BAY + 0.2, 0.0, X_BAY - 0.2] if x1 - x0 > 1.5 else [x0 + 0.08, x1 - 0.08]):
            h.iron.box((x, yF - 0.055, 2.29), (0.035, 0.008, 0.1), bevel=0)
            h.iron.slab((x, yF - 0.06, 2.27), (x, yy, 2.27), 0.014, 0.01, up=(0, 0, 1), bevel=0)


# ------------------------------------------------------------------------------- round 9: sparkle
def mirror_shade(x0, x1, z0, z1):
    """Vertex shade of the mirror glass: the silver has crept back from the frame (a ragged dark
    band along the edges, browner than the glass) and a few faint blotches; the tiling foxing
    texture does the rest."""
    from mathutils import noise as mn
    from hut import _smooth

    def f(p):
        d = min(p.x - x0, x1 - p.x, p.z - z0, z1 - p.z)
        n = mn.noise(Vector((p.x * 4.3, p.z * 4.3, 0.37)))
        edge = 1.0 - _smooth(0.0, 0.11 + 0.06 * n, d)
        blot = min(1.0, max(0.0, mn.noise(Vector((p.x * 1.6 + 3.1, p.z * 1.6, 1.1))) - 0.2) * 1.6)
        k = 1.0 - 0.55 * edge - 0.22 * blot
        return (k, k * 0.96, k * 0.9)
    return f


def back_mirror(h, lite):
    """An antique foxed pier glass on the upper two thirds of the back wall, behind the tiers: one
    flat mesh mirror_0 (material mirror_foxed) in a walnut frame with a gilt inner moulding, two
    gilt glazing bars where the old plates meet, and gilt rosettes. It doubles the baubles and
    catches the canopy bulbs."""
    T = h.trim
    yb = h.yB - 0.02 - 0.028 - 0.006 - 0.012      # just in front of the back wall's inner lining
    x0, x1 = -MIRROR_X, MIRROR_X
    z0, z1 = MIRROR_Z
    mir = Part("mirror_0", "mirror_foxed", var=0.0, shade=mirror_shade(x0, x1, z0, z1))
    h.extra.append(mir)
    nx, nz = (8, 4) if lite else (16, 8)
    mir.box((0, yb, (z0 + z1) / 2), (x1 - x0, 0.004, z1 - z0), bevel=0, segs=(nx, 1, nz), grain=0,
            drop=("+y", "+x", "-x", "+z", "-z"), uv_off=(0.13, 0.41))
    # walnut frame (proud of the glass) and the gilt inner moulding that laps over its edge
    fw, fd = 0.075, 0.035
    yf = yb - fd / 2 + 0.002
    for (cx, cz, sx, sz) in ((0, z1 + fw / 2 - 0.01, x1 - x0 + 2 * fw, fw), (0, z0 - fw / 2 + 0.01, x1 - x0 + 2 * fw, fw),
                             (x0 - fw / 2 + 0.01, (z0 + z1) / 2, fw, z1 - z0), (x1 + fw / 2 - 0.01, (z0 + z1) / 2, fw, z1 - z0)):
        h.frame.box((cx, yf, cz), (sx, fd, sz), tint="walnut", grain=0 if sx > sz else 2)
    gw = 0.03
    for (cx, cz, sx, sz) in ((0, z1 - 0.004, x1 - x0 + 0.02, gw), (0, z0 + 0.004, x1 - x0 + 0.02, gw),
                             (x0 + 0.004, (z0 + z1) / 2, gw, z1 - z0 + 0.02), (x1 - 0.004, (z0 + z1) / 2, gw, z1 - z0 + 0.02)):
        T.box((cx, yf - fd / 2 - 0.004, cz), (sx, 0.016, sz), band="gold", grain=0 if sx > sz else 2)
    # gilt glazing bars where the three old plates meet, with rosettes at their ends
    for x in (-0.5, 0.5):
        T.box((x, yb - 0.008, (z0 + z1) / 2), (0.026, 0.012, z1 - z0), band="gold", grain=2)
        for z in (z0 + 0.012, z1 - 0.012):
            T.sphere((x, yb - 0.02, z), 0.02, seg=6 if lite else 8, rings=4 if lite else 5, band="gold",
                     scale=(1, 0.6, 1))
    SLOTS["mirror_0"] = {"glass": [[round(x0, 3), round(yb, 4), z0], [round(x1, 3), round(yb, 4), z1]],
                         "about": "the back-wall mirror (mesh mirror_0, material mirror_foxed): its glass plane "
                                  "faces -Y; gilt glazing bars at x = -0.5 and 0.5."}


def canopy_bulbs(h, lite):
    """Three rows of small warm rice bulbs inside the canopy (bulbs_1): a tight fringe just under
    the header's inner edge across the counter bay (the row a visitor sees from the lane: from
    there the header hides everything inside above about 2.25 m, so this row is what lights the
    goods from above and shows as a line of points), a row swagged along the tie beam and one low
    across the top of the mirror (seen close up, and doubled in the glass)."""
    B = Part("bulbs_1", "bulb_warm", var=0.03)
    h.extra.append(B)
    xa, xb = h.x0 + 0.1, h.x1 - 0.1
    kw = dict(bulb_r=0.014, seg=5, rings=3, socket=False, wire_r=0.0025, wire_detail=1)
    fa, fb = -X_BAY + 0.08, X_BAY - 0.08
    cp.bulb_string(B, h.wire, [(fa + (fb - fa) * i / 4, h.yF + 0.1, OPEN_TOP - 0.012) for i in range(5)],
                   sag=0.012, spacing=0.16 if lite else 0.1, drop=0.006, **kw)
    for (y, z, sag) in ((h.yF + 0.52, 2.64, 0.14), (h.yB - 0.22, 2.68, 0.15)):
        anchors = [(xa + (xb - xa) * i / 4, y, z) for i in range(5)]
        cp.bulb_string(B, h.wire, anchors, sag=sag, spacing=0.26 if lite else 0.15, drop=0.022, **kw)
    return B


def pendant_lamp(h, p, lite):
    """A small brass pendant lamp at light_0, hung on a rod from the roof deck, so the warm light
    near the ceiling has a visible source (it shows in the mirror close up). Its bulb is bulbs_1."""
    x, y, z = p
    deck = RIDGE - abs(y) * (RIDGE - EAVE) / (D / 2) - 0.03
    seg = 8 if lite else 12
    h.brass.cyl((x, y, deck - 0.01), 0.03, 0.03, 0.02, seg=seg)
    h.brass.cyl((x, y, (deck + z + 0.1) / 2), 0.005, 0.005, deck - z - 0.1, seg=6)
    h.brass.cyl((x, y, z + 0.075), 0.018, 0.012, 0.05, seg=seg)
    h.brass.cyl((x, y, z + 0.02), 0.09, 0.022, 0.07, seg=seg, caps=False)
    B = next(pp for pp in h.extra if pp.name == "bulbs_1")
    B.sphere((x, y, z + 0.0), 0.026, seg=seg, rings=6 if lite else 8, scale=(1, 1, 1.25))


def roof_ring(h):
    """A ring of bulbs right round the roof edge: the front eave (Hut.eave_bulbs, with sockets),
    then both rakes of both slopes and the back eave as lighter strings (no sockets, a thin wire),
    so the roof outline reads at night from every lane."""
    h.eave_bulbs(sides=False)
    kw = dict(spacing=0.34 if state.lite() else 0.25, seg=h.bulb_detail[0], rings=h.bulb_detail[1], socket=False,
              wire_detail=1)
    for sl in h.slopes:
        front = sl is h.front_slope
        if not front:
            y = sl.point(0, 0).y + 0.02
            z = sl.point(0, 0, -0.08).z
            xa, xb = sl.a0 + 0.05, sl.a1 - 0.05
            cp.bulb_string(h.bulbs, h.wire, [(xa + (xb - xa) * i / 4, y, z) for i in range(5)], sag=0.04, **kw)
        for a in (sl.a0 - 0.02, sl.a1 + 0.02):
            cp.bulb_string(h.bulbs, h.wire, [sl.point(a, s, -0.06) for s in (0.05, sl.L * 0.5, sl.L - 0.05)],
                           sag=0.03, **kw)


def star_outline(r_long, r_short, r_in):
    """Eight-point star (four long points on the axes, four short on the diagonals), CCW."""
    pts = []
    for i in range(16):
        a = math.pi / 2 + i * math.pi / 8
        r = (r_long if i % 4 == 0 else r_short) if i % 2 == 0 else r_in
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def ridge_star(h, lite):
    """The shop's crown: a large faceted eight-point star on a turned post at the middle of the
    ridge. Its glass core is emissive bulb_warm (mesh bulbs_2); gilt ribs run along every edge
    and from the centre to every point, so it reads as a lantern star, not a flat glow."""
    import bmesh
    rl, rs, ri, t = 0.30, 0.19, 0.075, 0.075
    zr = RIDGE + 0.05
    zS = zr + 0.26 + rl
    seg = 8 if lite else 12
    h.frame.cyl((0, 0, zr + 0.06), 0.045, 0.055, 0.12, seg=seg, tint="walnut")
    h.frame.cyl((0, 0, zr + 0.15), 0.03, 0.045, 0.07, seg=seg, tint="walnut")
    h.frame.sphere((0, 0, zr + 0.2), 0.04, seg=seg, rings=5 if lite else 7, tint="walnut")
    h.brass.cyl((0, 0, zr + 0.25), 0.011, 0.011, 0.08, seg=6)
    out = star_outline(rl, rs, ri)
    core = Part("bulbs_2", "bulb_warm", var=0.0)
    h.extra.append(core)
    bm = bmesh.new()
    rim = [bm.verts.new((u, 0.0, v)) for (u, v) in out]
    f_ap = bm.verts.new((0, -t, 0))
    b_ap = bm.verts.new((0, t, 0))
    n = len(rim)
    for i in range(n):
        a, b = rim[i], rim[(i + 1) % n]
        bm.faces.new((f_ap, a, b))
        bm.faces.new((b_ap, b, a))
    core.from_bmesh(bm, M=Matrix.Translation((0, 0, zS)), grain=0)
    # gilt ribs: the outline on both faces' rims, and centre-to-point ribs on the front and back
    ring = [Vector((u, 0.0, zS + v)) for (u, v) in out]
    h.brass.tube(ring + [ring[0]], 0.009, tseg=4)
    for k in range(0, n, 2):
        tip = ring[k]
        for sy in (-1, 1):
            h.brass.tube([Vector((0, sy * (t + 0.004), zS)), tip], 0.006, tseg=3)
    h.brass.sphere((0, -t - 0.006, zS), 0.016, seg=8, rings=5)
    h.brass.sphere((0, t + 0.006, zS), 0.016, seg=8, rings=5)
    return Vector((0, 0, zS))


def mirrorball_bracket(h, lite):
    """A forged wrought-iron bracket (Ausleger) projecting forward from the left front corner
    post, the way an old shop hangs its sign: an arm with a curled end, a diagonal brace and a
    C-scroll between them. Its hook (slot_mirrorball) carries the 18 cm mercury-glass bauble,
    clear of every other ornament and close to the lane."""
    I = h.iron
    x = h.front_posts[0]
    y0 = h.yF - 0.03                       # the painted post's front face
    za, zb = 2.15, 1.80                    # arm, brace foot
    yE = h.yF - 0.74                       # arm end
    yH = h.yF - 0.64                       # hook
    I.box((x, y0 - 0.005, (za + zb) / 2 + 0.01), (0.055, 0.01, za - zb + 0.12), bevel=0)        # wall plate
    for z in (za + 0.04, zb - 0.03, (za + zb) / 2):
        I.sphere((x, y0 - 0.012, z), 0.009, seg=6, rings=4)                               # rivets
    I.slab((x, y0 - 0.01, za), (x, yE, za), 0.024, 0.016, up=(0, 0, 1), bevel=0)              # arm
    yb = h.yF - 0.46
    I.slab((x, y0 - 0.01, zb), (x, yb, za - 0.01), 0.016, 0.012, up=(1, 0, 0), bevel=0)       # brace
    tseg = 3 if lite else 4
    # C-scroll in the triangle, and a curl at the arm's end
    def spiral(cy, cz, r0, r1, a0, turns, n):
        return [Vector((x, cy + (r0 + (r1 - r0) * i / n) * math.cos(a0 + turns * 2 * math.pi * i / n),
                        cz + (r0 + (r1 - r0) * i / n) * math.sin(a0 + turns * 2 * math.pi * i / n)))
                for i in range(n + 1)]
    n = 10 if lite else 22
    I.tube(spiral(y0 - 0.13, za - 0.12, 0.10, 0.025, math.pi * 0.5, 1.15, n), 0.006, tseg=tseg)
    I.tube(spiral(yE + 0.035, za - 0.035, 0.035, 0.008, math.pi * 0.5, -1.25, n // 2 + 2), 0.006, tseg=tseg)
    # the hook: a small ring through the arm and an open S below it
    I.torus((x, yH, za - 0.022), 0.014, 0.0035, seg=8 if lite else 12, tseg=tseg, rot=(0, math.pi / 2, 0))
    hook = Vector((x, yH, za - 0.05))
    I.tube([Vector((x, yH, za - 0.036)), Vector((x, yH - 0.006, za - 0.044)), hook], 0.003, tseg=3)
    export.empty("slot_mirrorball", tuple(round(c, 4) for c in hook))
    SLOTS["slot_mirrorball"] = {
        "position": [round(c, 4) for c in hook], "ball_diameter": 2 * BALL_R,
        "clear_radius": 0.40,
        "about": "the open hook under the forged corner bracket (left front post); hang act_orn_mirrorball by its "
                 "cap here, ball centre about 0.12 m below (18 cm ball). No other ornament within clear_radius. "
                 "A camera for the dive fits in front of it, e.g. cam_dive about 0.7 m toward -Y and 0.25 m toward "
                 "+X of the ball, cam_dive_target on the ball centre: from there the ball mirrors the lane and "
                 "the lit market behind the camera."}


def tinsel_slots(h, sign_valance_z, sign_valance_y):
    """Anchors for the vendor's tinsel swags (tinsel_<n> meshes): slot_tinsel_<n> at a swag's left
    anchor; schmuck_slots.json lists every anchor and a suggested sag per span."""
    xs_c = [-X_BAY, 0.0, X_BAY]
    swags = {
        1: ("canopy edge: under the scalloped valance across the counter bay",
            [(x, sign_valance_y, sign_valance_z) for x in xs_c], 0.13),
        2: ("front rail: draped over the harmonica rail between its three hangers, above the baubles' rings",
            [(x, h.yF - 0.15, HARM_Z + 0.004) for x in (-X_BAY + 0.2, 0.0, X_BAY - 0.2)], 0.05),
        3: ("inside: along the tie beam under the canopy (doubled in the mirror)",
            [(x, h.yF + 0.52, 2.655) for x in (-1.9, -0.95, 0.0, 0.95, 1.9)], 0.07),
    }
    for n, (about, pts, sag) in swags.items():
        p0 = tuple(round(c, 4) for c in pts[0])
        export.empty(f"slot_tinsel_{n}", p0)
        SLOTS[f"slot_tinsel_{n}"] = {"position": list(p0), "anchors": [[round(c, 4) for c in p] for p in pts],
                                     "sag": sag, "about": about}



def side_vitrine(h, sx, glass, back, lite):
    """A glazed shop window (Schaukasten) on a side wall, between the red rails: a shallow red
    case with a gilt bead, a velvet back, two small warm bulbs under its top and a carved crest.
    The shop's sides face the lanes and (the right one) the home view, so each gets one lit
    window instead of a blank wall. Its back is a cream 'paint_lit' board, so in the browser the
    window glows like a lit display (the bulbs light nothing there). slot_window_<l|r> is on its
    sill, centred."""
    P, T = h.paint, h.trim
    xw = sx * (W / 2 + 0.03)                 # outer face of the side wall's red rails
    yc, w = -0.08, 0.86                      # centre and width along the wall
    z0, z1 = 0.98, 1.78
    d = 0.17
    xo = xw + sx * d                         # glass plane
    xm = (xw + xo) / 2
    back.box((xw + sx * 0.004, yc, (z0 + z1) / 2), (0.006, w - 0.06, z1 - z0 - 0.06), band="cream", grain=1)
    P.box((xm, yc, z1 - 0.015), (d, w, 0.03), band="red", grain=1, bevel=0)                          # top
    P.box((xm + sx * 0.012, yc, z0 + 0.02), (d + 0.024, w + 0.03, 0.04), band="red", grain=1)          # sill
    T.box((xo + sx * 0.026, yc, z0 + 0.03), (0.008, w + 0.02, 0.012), band="gold", bevel=0, grain=1)
    for yy in (yc - w / 2 + 0.015, yc + w / 2 - 0.015):
        P.box((xm, yy, (z0 + z1) / 2), (d, 0.03, z1 - z0), band="red", grain=2, bevel=0)              # sides
    # front frame round the glass, with a gilt bead inside it
    fw = 0.04
    for (cy, cz, sy, sz) in ((yc, z1 - fw / 2, w, fw), (yc, z0 + 0.04 + fw / 2, w, fw),
                             (yc - w / 2 + fw / 2, (z0 + z1) / 2, fw, z1 - z0), (yc + w / 2 - fw / 2, (z0 + z1) / 2, fw, z1 - z0)):
        P.box((xo + sx * 0.008, cy, cz), (0.018, sy, sz), band="red", grain=1 if sy > sz else 2, bevel=0)
    for (cy, cz, sy, sz) in ((yc, z1 - fw - 0.004, w - 2 * fw, 0.008), (yc, z0 + 0.08 + 0.004, w - 2 * fw, 0.008),
                             (yc - w / 2 + fw + 0.004, (z0 + z1) / 2 + 0.02, 0.008, z1 - z0 - 2 * fw - 0.04),
                             (yc + w / 2 - fw - 0.004, (z0 + z1) / 2 + 0.02, 0.008, z1 - z0 - 2 * fw - 0.04)):
        T.box((xo + sx * 0.018, cy, cz), (0.006, sy, sz), band="gold", bevel=0, grain=1 if sy > sz else 2)
    glass.box((xo, yc, (z0 + 0.08 + z1 - fw) / 2), (0.004, w - 2 * fw, z1 - fw - z0 - 0.08), bevel=0, var=0.0)
    # carved crest on the top: an arched red board with a gold star, facing out
    Mc = Matrix.Translation((xo + sx * 0.004, yc, z1)) @ Euler((math.pi / 2, 0, sx * math.pi / 2)).to_matrix().to_4x4()
    crest = [(-0.2, 0.0), (0.2, 0.0)] + [(0.2 * math.cos(math.pi * i / 10), 0.11 * math.sin(math.pi * i / 10))
                                       for i in range(1, 10)]
    T.shape(crest, depth=0.02, M=Mc, band="red")
    Ms = Matrix.Translation((xo + sx * 0.016, yc, z1 + 0.05)) @ Euler((math.pi / 2, 0, sx * math.pi / 2)).to_matrix().to_4x4()
    T.shape(geo.star_polygon(0, 0, 0.04, 0.017, 5), depth=0.008, M=Ms, band="gold")
    for yy in (yc - 0.22, yc + 0.22):
        h.bulbs.sphere((xw + sx * 0.06, yy, z1 - 0.05), 0.013, seg=5 if lite else 8, rings=3 if lite else 5,
                       scale=(1, 1, 1.3))
    key = "l" if sx < 0 else "r"
    pos = (round(xw + sx * (d / 2), 4), yc, round(z0 + 0.04, 4))
    export.empty(f"slot_window_{key}", pos)
    SLOTS[f"slot_window_{key}"] = {
        "position": list(pos), "inner_size": [round(d - 0.03, 3), round(w - 0.06, 3), round(z1 - z0 - 0.07, 3)],
        "faces": "+X" if sx > 0 else "-X",
        "about": "on the sill of the lit side window (Schaukasten), centred; inner_size is (depth out from the "
                 "wall, width along the wall, height). Optional: a few hanging baubles, a spun-glass bird or "
                 "a small angel read well; keep it sparse."}


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
            wall="vertical", wall_band="white", frame_tint="walnut", roof_tint="dark", inner_tint="walnut",
            counter_tint="walnut", plank_w=0.14, bulb_spacing=0.22, counter_depth=0.56, counter_over=0.2,
            front_posts=[-W / 2 + 0.05, -X_BAY, X_BAY, W / 2 - 0.05], shingle_size=(0.36, 0.23),
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
    # round 9: line the inside of the upper front wall in dark wood too (its white boards caught
    # light_0 and showed as a pale sheet in the mirror)
    h._lining('x', h.x0 + 0.1, h.x1 - 0.1, yF + 0.03 + 0.026, lambda c: h.top_at('x', c), OPEN_TOP + h.header_h)
    lower_walls(h)
    h.build_counter(x0=-X_BAY + 0.06, x1=X_BAY - 0.06, brackets=3, grid=0.3)
    tiered_shelves(h, lite)
    h.build_roof(cover="shingles", fascia_band="red", barge_band="red", barge_part=T)
    h.build_snow(drifts=3, nx=None if lite else 12)
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
    tinsel_slots(h, ez - 0.17, ye - 0.03)
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
    for sx in (-1, 1):
        side_vitrine(h, sx, glass, SL, lite)
    rails(h)
    # fir garland with red and gold baubles along the header over the two bays (round 9: the
    # counter bay's span gave way to the harmonica rail and the vendor's tinsel swag)
    gy, gz = yF - 0.065, OPEN_TOP - 0.05      # below the valance's line of sight
    for a, b in ((-W / 2 + 0.1, -X_BAY), (X_BAY, W / 2 - 0.1)):
        cp.fir_garland(h.fir, h.beads, (a, gy, gz), (b, gy, gz), sag=0.06, radius=0.04,
                       tufts_per_m=None if lite else 11, bead_every=0.2)
    # round 9 sparkle: the foxed mirror, bulbs inside the canopy and round the roof, the ridge
    # star, the mirror-ball bracket
    back_mirror(h, lite)
    canopy_bulbs(h, lite)
    roof_ring(h)
    ridge_star(h, lite)
    mirrorball_bracket(h, lite)
    # light_0 near the ceiling centre (a warm highlight on every bauble), high enough that its
    # reflection in the mirror stays behind the header from the lane; light_1 out front
    lights = [(0, -0.5, 2.8), (0, yF - 0.8, 2.45)]
    pendant_lamp(h, lights[0], lite)
    cam_t = (0.0, yF + 0.3, 1.62)
    cam_v = (0.0, yF - CAM_DIST, 1.8)
    pyr = (0.12, round(h.counter_y + 0.1, 4), COUNTER_TOP)
    export.empty("slot_pyramid", pyr)
    SLOTS["slot_pyramid"] = {"position": list(pyr), "max_diameter": 0.34, "max_height": 0.62,
                             "about": "on the counter top, right of the Schwibbogen (which stands at about x = -0.38 "
                                      "from slot_counter): the Erzgebirge candle pyramid; its turning part is the "
                                      "vendor's rot_pyramid. The harmonica's lowest baubles end about 0.3 m in front of "
                                      "and above its top."}
    export.empty("slot_counter", (0, h.counter_y, COUNTER_TOP))
    export.empty("slot_vendor", (0, (h.yB - 0.45 + yF + h.counter_depth - h.counter_over) / 2, 0.13))
    export.empty("slot_sign", tuple(sign_c))
    export.empty("slot_front", (0, yF - h.counter_over - 0.9, 0.0))
    export.empty("cam_target", cam_t)
    export.empty("cam_view", cam_v, look_at=cam_t)
    for i, p in enumerate(lights):
        export.empty(f"light_{i}", p)
    SLOTS["cam_view"] = {"position": list(cam_v), "target": list(cam_t)}
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
                    "it (about 0.12 m apart reads well); clear_drop is the free height under the rail. Round 9 (ADR "
                    "0004 revision): rail 1 is now the glass-harmonica rail at 2.0 m (slot_harmonica_rail, the same "
                    "rail, with twelve brass rings at hooks_x); rail 2 hangs inside over the counter's back edge; "
                    "rails 3 and 4 hang in front of the header over the glass case and the tree. slot_mirrorball is "
                    "the hook of the forged bracket on the left front post (the 18 cm mercury-glass bauble); "
                    "slot_pyramid is on the counter right of the Schwibbogen; slot_tinsel_1..3 are the left anchors "
                    "of three tinsel swags (all anchors and a sag per swag below; use two or three of them). "
                    "mirror_0 is the back-wall mirror's glass (not a slot). Keep dark wood showing between "
                    "clusters: the tiers, the frame and the canopy are dark walnut on purpose.",
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


NEW_SLOTS = ("slot_harmonica_rail", "slot_mirrorball", "slot_pyramid", "slot_window_l", "slot_window_r")


def env_mat(name, color, rough, metal, emit=None, strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def standin_sparkle(missing, tinsel=True):
    """Render-only stand-ins for the round-9 goods the vendor has not shipped yet: the twelve
    harmonica baubles, the mirror ball, a candle pyramid and tinsel swags. Not exported."""
    env = state.env_collection()
    R = state.rng
    looks = [("silver", (0.86, 0.86, 0.88), 0.04, 1.0), ("gold", (0.92, 0.66, 0.30), 0.06, 1.0),
             ("copper", (0.88, 0.45, 0.30), 0.07, 1.0), ("teal", (0.10, 0.42, 0.42), 0.05, 0.85)]
    parts = {k: Part(f"env_sp_{k}", "ornament_gold", var=0.0) for (k, *_r) in looks}
    caps = Part("env_sp_caps", "brass", var=0.05)
    thread = Part("env_sp_thread", "wire", var=0.0)
    wood = Part("env_sp_wood", "wood", var=0.1)
    flame = Part("env_sp_flame", "bulb_warm", var=0.0)
    tin = {"gold": Part("env_sp_tinsel_gold", "ornament_gold", var=0.0),
           "silver": Part("env_sp_tinsel_silver", "ornament_gold", var=0.0)}

    def hang(x, y, z, drop, r, look, seg=20):
        c = Vector((x, y, z - drop - r))
        thread.tube([(x, y, z), (x, y, c.z + r + 0.012)], 0.0012, tseg=3)
        caps.cyl((x, y, c.z + r + 0.007), 0.009 * r / 0.04, 0.009 * r / 0.04, 0.016 * r / 0.04, seg=10)
        parts[look].sphere(c, r, seg=seg, rings=seg * 2 // 3)
        return c
    if "slot_harmonica_rail" in missing:
        hs = SLOTS["slot_harmonica_rail"]
        x0, y, z = hs["position"]
        for i, dx in enumerate(hs["hooks_x"]):
            t = i / (len(hs["hooks_x"]) - 1)
            r = 0.05 - 0.016 * t                                   # big, low notes on the left
            drop = 0.07 + 0.05 * math.sin(math.pi * t)
            hang(x0 + dx, y, z - hs["hook_drop"], drop, r, ("silver", "gold", "silver", "teal", "silver", "copper")[i % 6])
    if "slot_mirrorball" in missing:
        x, y, z = SLOTS["slot_mirrorball"]["position"]
        hang(x, y, z, 0.03, BALL_R, "silver", seg=40)
    if "slot_pyramid" in missing:
        x, y, z = SLOTS["slot_pyramid"]["position"]
        wood.cyl((x, y, z + 0.015), 0.16, 0.16, 0.03, seg=8, tint="honey")
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            px, py = x + 0.13 * math.cos(a), y + 0.13 * math.sin(a)
            wood.cyl((px, py, z + 0.2), 0.008, 0.008, 0.37, seg=6, tint="honey")
            caps.cyl((px, py, z + 0.4), 0.01, 0.01, 0.012, seg=8)
            wood.cyl((px, py, z + 0.44), 0.009, 0.009, 0.07, seg=8, tint=(1.0, 0.95, 0.85))
            flame.sphere((px, py, z + 0.49), 0.007, seg=6, rings=4, scale=(1, 1, 1.8))
        for zz, rr in ((0.16, 0.12), (0.3, 0.09)):
            wood.cyl((x, y, z + zz), rr, rr, 0.012, seg=8, tint="honey")
            for k in range(5):
                a = k * 2 * math.pi / 5
                wood.cyl((x + rr * 0.7 * math.cos(a), y + rr * 0.7 * math.sin(a), z + zz + 0.03), 0.01, 0.012,
                         0.05, seg=6, tint=("walnut", "honey", (1.2, 0.5, 0.4))[k % 3])
        wood.cyl((x, y, z + 0.29), 0.006, 0.006, 0.55, seg=6, tint="walnut")
        for k in range(8):
            a = k * math.pi / 4
            M = Matrix.Translation((x + 0.09 * math.cos(a), y + 0.09 * math.sin(a), z + 0.57)) @ \
                Euler((0.5, 0, a + math.pi / 2)).to_matrix().to_4x4()
            wood.mbox(M, (0.03, 0.15, 0.003), tint="pine")
    for key in ("l", "r"):
        if f"slot_window_{key}" not in missing:
            continue
        ws = SLOTS[f"slot_window_{key}"]
        x, y, z = ws["position"]
        dpt, wid, hgt = ws["inner_size"]
        for j, dy in enumerate((-0.27, -0.09, 0.09, 0.27)):
            hang(x, y + dy, z + hgt - 0.01, 0.12 + 0.1 * (j % 2), 0.035 + 0.008 * ((j + 1) % 2),
                 ("silver", "gold", "teal", "copper")[j])
        parts["gold"].sphere((x, y, z + 0.06), 0.06, seg=20, rings=14)
    if tinsel:
        for n, look in ((1, "gold"), (2, "silver")):
            ts = SLOTS[f"slot_tinsel_{n}"]
            P = tin[look]
            for a, b in zip(ts["anchors"][:-1], ts["anchors"][1:]):
                a, b = Vector(a), Vector(b)
                L = (b - a).length
                k = int(L * 260)
                for j in range(k):
                    t = (j + R.random()) / k
                    p = a.lerp(b, t) - Vector((0, 0, ts["sag"] * 4 * t * (1 - t)))
                    d = Vector((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(-1, 1))).normalized()
                    q = p + d * R.uniform(0.012, 0.03)
                    P.slab(p, q, 0.006, 0.0006, up=(R.uniform(-1, 1), R.uniform(-1, 1), 1), bevel=0)
    ob_parts = list(parts.values()) + [caps, thread, wood, flame] + list(tin.values())
    obs = {}
    for p in ob_parts:
        ob = p.finish(env)
        if ob is not None:
            obs[p.name] = ob
    for (k, col, rough, metal) in looks:
        if f"env_sp_{k}" in obs:
            obs[f"env_sp_{k}"].data.materials[0] = env_mat(f"env_sp_{k}_m", col, rough, metal)
    for k, col in (("gold", (0.95, 0.72, 0.34)), ("silver", (0.9, 0.9, 0.92))):
        if f"env_sp_tinsel_{k}" in obs:
            obs[f"env_sp_tinsel_{k}"].data.materials[0] = env_mat(f"env_sp_tinsel_{k}_m", col, 0.12, 1.0)


def preview(objs):
    import glob
    sets = []
    path = os.path.join(state.MODELS_DIR, "props.json")
    if os.path.exists(path):
        with open(path) as f:
            sets = [s for s in json.load(f).get("sets", []) if s.get("asset") == "stall_schmuck.glb"]
    have = {s.get("slot") for s in sets}
    has_tinsel = any("tinsel" in s.get("set", "") or str(s.get("slot", "")).startswith("slot_tinsel") for s in sets)
    # the round-8 front-rail set hangs on the same rail as the harmonica: leave it out of the
    # preview until the harmonica set replaces it
    pairs = [(s["set"], s["slot"]) for s in sets if s.get("slot") in bpy.data.objects and
             os.path.exists(os.path.join(state.MODELS_DIR, s["set"] + ".glb")) and
             not (s["slot"] == "slot_rail_1" and "slot_harmonica_rail" not in have)]
    got = pipeline.vendor_props(pairs, rotate=True) if pairs else False
    if not got:
        standin_goods()
    has_tinsel = has_tinsel or any(o.name.startswith("tinsel_") for o in bpy.data.objects)
    standin_sparkle({n for n in NEW_SLOTS if n not in have}, tinsel=not has_tinsel)
    render.lights_at_markers(energy=150, size=0.06)        # small: sharp highlights on the glass
    fill = render.add_light("env_fill", 'AREA', (0, 0.2, 2.55), 45, size=2.4)
    # render-only: the fill panel must not show in the mirror, and the small bulbs (light_0's
    # pendant bulb among them) must not shadow the marker lights inside them
    for ob in bpy.data.objects:
        if ob.name.startswith("env_fill"):
            ob.visible_glossy = False
        if ob.name.startswith("bulbs_"):
            ob.visible_shadow = False
    yF = -D / 2
    render.add_light("env_case", 'POINT', tuple(Vector(SLOTS["slot_cabinet"]["position"]) + Vector((0, 0.05, 0.5))),
                     12, size=0.05)
    tp = Vector(SLOTS["slot_tree"]["position"])
    render.add_light("env_tree", 'POINT', tuple(tp + Vector((0, -0.45, 0.8))), 9, size=0.3)
    # the pediment's bulb outline and a lamp in front light the sign board
    render.add_light("env_sign", 'SPOT', (0, yF - 2.0, 2.2), 70, size=0.1, spot_size=math.radians(30),
                     spot_blend=0.4, target=(0, yF - 0.45, 2.85))
    render.add_light("env_star", 'POINT', (0, -0.15, RIDGE + 0.62), 25, size=0.15)
    for key in ("l", "r"):
        x, y, z = SLOTS[f"slot_window_{key}"]["position"]
        render.add_light(f"env_win_{key}", 'POINT', (x, y, z + 0.68), 5, size=0.05)
    render.add_light("env_neighbour", 'POINT', (-5.2, -1.8, 2.6), 160, size=0.6)
    return render.camera((-2.9, -6.9, 1.7), (0.15, -0.85, 2.38), lens=24)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=83)
