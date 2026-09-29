"""The band's instruments, one glb each, placed by the engine at the bandstand slots.

    instr_sax    tenor saxophone as held by a standing player (keys, pearls, rods, guards,
                 neck with octave key, mouthpiece, ligature and reed); act_sax pivots at the
                 neck-strap ring so the engine can sway it.
    instr_piano  upright piano in walnut with 88 keys, fallboard, music desk with sheet music,
                 brass candle sconces (lit), turned legs, pedals, and a bench.
    instr_bass   double bass in playing position with f-holes, bridge, tailpiece, four strings,
                 fingerboard, scroll and brass machines; act_bass pivots at the endpin. A
                 floor stand beside it holds the bow.
    instr_drums  small jazz kit: 18" kick, 14" snare, 12" rack tom, 14" floor tom, hi-hat,
                 20" ride, throne and a pair of wire brushes resting on the snare
                 (act_brush_l / act_brush_r pivot at the handle ends).

Conventions: the origin is on the floor where the player stands (sax, bass) or sits (piano
bench, drum throne). The player faces -Y. The bandstand's slot_* empties carry the rotation
that turns this frame to face the right way on the stage.

    /home/claude/tools/bpy-venv/bin/python blender/rides/instruments.py [--only sax,piano] [--no-lite]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rcommon as rc  # noqa: E402
from rcommon import TAU, Part, basis, node, pipe, rod, state, sweep  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from nmlib import geo, render  # noqa: E402


def Rx(a):
    return Euler((a, 0, 0)).to_matrix().to_4x4()


def Ry(a):
    return Euler((0, a, 0)).to_matrix().to_4x4()


def Rz(a):
    return Euler((0, 0, a)).to_matrix().to_4x4()


class Group:
    """Parts that end up under one node (the instrument root or an act_ pivot)."""

    def __init__(self, prefix, node_name=None, pivot=(0, 0, 0), M=None):
        self.prefix = prefix
        self.node_name = node_name
        self.pivot = Vector(pivot)
        self.M = M or Matrix()          # local build frame -> instrument frame
        self.parts = {}

    def __getitem__(self, mat):
        if mat not in self.parts:
            nm = f"{self.prefix}_{mat}" if not mat.startswith("bulb_") else f"bulbs_{self.prefix}"
            kw = {}
            if mat in ("wood", "rsteel", "paint"):
                kw["bevel"] = 0.0015
            self.parts[mat] = Part(nm, mat, var=0.03, **kw)
        return self.parts[mat]

    def finish(self, coll=None):
        objs = []
        for p in self.parts.values():
            ob = p.finish(coll)
            if ob is not None:
                ob.data.transform(self.M)
                objs.append(ob)
        return objs


# =================================================================== tenor saxophone
def sax_body_r(z):
    return 0.044 + (0.016 - 0.044) * (z - 0.13) / (0.64 - 0.13)


def build_sax(lite):
    # sax frame: body axis +Z, bell and pearls toward -Y (away from the player)
    tip = Vector((0, 0.275, 0.79))
    beta = 0.36
    Mh = Ry(beta)
    t = Mh @ tip
    M = Matrix.Translation(Vector((0.0, -0.10, 1.53)) - t) @ Mh
    strap = M @ Vector((0, 0.05, 0.52))
    g = Group("sax", "act_sax", pivot=strap, M=M)
    br, iv, eb, ch = g["saxbrass"], g["ivory"], g["ebony"], g["chrome"]
    n = 8 if lite else 16
    # one continuous tube: body, bow and bell
    ctrl = [(0, 0, 0.645, 0.0165), (0, 0, 0.52, 0.024), (0, 0, 0.38, 0.031), (0, 0, 0.24, 0.038),
            (0, 0, 0.14, 0.044), (0, -0.018, 0.078, 0.046), (0, -0.07, 0.056, 0.047), (0, -0.124, 0.074, 0.048),
            (0, -0.146, 0.13, 0.05), (0, -0.152, 0.25, 0.052), (0, -0.158, 0.35, 0.056), (0, -0.163, 0.415, 0.064),
            (0, -0.168, 0.448, 0.076), (0, -0.175, 0.468, 0.092)]
    pipe(br, ctrl, n=n, per=1 if lite else 3, side=(1, 0, 0))
    br.torus((0, -0.176, 0.469), 0.092, 0.006, seg=n + 4, tseg=4 if lite else 6, rot=(0.05, 0, 0))
    # neck (crook), cork, mouthpiece, ligature, reed
    neck = [(0, 0, 0.64, 0.0168), (0, 0.004, 0.68, 0.016), (0, 0.03, 0.74, 0.0145), (0, 0.08, 0.782, 0.0128),
            (0, 0.14, 0.797, 0.0115), (0, 0.20, 0.797, 0.0105)]
    pipe(br, neck, n=6 if lite else 12, per=1 if lite else 3, side=(1, 0, 0))
    rod(g["leather"], (0, 0.195, 0.797), (0, 0.222, 0.796), 0.0108, seg=8)
    rod(eb, (0, 0.215, 0.796), (0, 0.275, 0.790), 0.0145, r2=0.009, seg=10, caps=True)
    rod(ch, (0, 0.226, 0.795), (0, 0.24, 0.795), 0.0155, seg=10)
    if not lite:
        g["canvas"].box((0, 0.25, 0.782), (0.011, 0.055, 0.002), rot=(0.08, 0, 0), tint=(0.85, 0.72, 0.45))
        # octave key along the top of the neck
        rod(br, (0, 0.03, 0.765), (0, 0.13, 0.812), 0.0028, seg=4)
        rod(br, (0, 0.13, 0.812), (0, 0.15, 0.813), 0.006, seg=6, caps=True)

    def surf(z, a, off=0.0):
        r = sax_body_r(z) + off
        return Vector((r * math.cos(a), r * math.sin(a), z))

    def cup(z, a, rad, h=0.01):
        p = surf(z, a, 0.002)
        d = Vector((math.cos(a), math.sin(a), 0))
        rod(br, p, p + d * h, rad, seg=8 if lite else 12, caps=True)
        if not lite:
            rod(g["leather"], p + d * (h - 0.001), p + d * (h + 0.0015), rad * 0.8, seg=8, caps=True,
                tint=(0.7, 0.6, 0.45))
        return p + d * h

    front = -math.pi / 2
    # left-hand stack (B, A, G) and right-hand stack (F, E, D) with pearl touches
    for zs, a0 in (((0.585, 0.545, 0.505), front), ((0.37, 0.33, 0.29), front - 0.55)):
        for z in zs:
            top = cup(z, a0 + 0.35, 0.015 + 0.012 * (0.6 - z))
            pearl = surf(z - 0.012, a0, 0.028)
            rod(br, top, pearl, 0.0022, seg=4)
            iv.sphere(pearl, 0.0075, seg=5 if lite else 8, rings=3 if lite else 6, scale=(1, 1, 0.55),
                      rot=(0, math.pi / 2, a0))
            if not lite:
                br.sphere(pearl - Vector((0, 0, 0.002)), 0.0095, seg=6, rings=4, scale=(1, 1, 0.4))
    # side and trill cups around the body
    cups = [(0.60, 0.9), (0.47, 1.4), (0.43, -0.3), (0.40, 0.7), (0.25, -0.2), (0.22, 1.1), (0.19, -2.4),
            (0.16, 0.4)]
    for z, a in cups[:4] if lite else cups:
        cup(z, a, 0.013 + 0.02 * (0.62 - z))
    # palm keys near the top on the player's left
    for i, z in enumerate((0.60, 0.625, 0.648)):
        p = surf(z, 0.25 + 0.2 * i, 0.02)
        br.box(p, (0.012, 0.022, 0.006), rot=(0, 0.3, 0.25 + 0.2 * i))
        iv.sphere(p + Vector((0, 0, 0.004)), 0.006, seg=6, rings=4, scale=(1, 1, 0.5))
    # key rods along the body with posts
    if not lite:
        for a in (front + 0.75, front - 1.0, 0.6):
            p0, p1 = surf(0.2, a, 0.013), surf(0.6, a, 0.013)
            rod(br, p0, p1, 0.0024, seg=5)
            for z in (0.2, 0.4, 0.6):
                rod(br, surf(z, a, 0.0), surf(z, a, 0.015), 0.003, seg=5)
        # low C / Eb near the bow, low B / Bb on the bell tube, with wire guards
        for z, a, r in ((0.16, front - 0.3, 0.028), (0.19, front + 0.9, 0.022)):
            top = cup(z, a, r, h=0.012)
            d = Vector((math.cos(a), math.sin(a), 0))
            gp = [surf(z - 0.045, a, 0.006), surf(z - 0.04, a, 0.04), surf(z + 0.04, a, 0.04), surf(z + 0.045, a, 0.006)]
            br.tube(gp, 0.0022, tseg=4)
        for z in (0.22, 0.31):
            c = Vector((0, -0.152, z))
            a = math.pi
            d = Vector((-1, 0, 0))
            p = c + d * (0.054 + 0.002)
            rod(br, p, p + d * 0.012, 0.028, seg=12, caps=True)
        # thumb rest, thumb hook and strap ring on the back
        rod(br, surf(0.34, math.pi / 2, 0), surf(0.34, math.pi / 2, 0.025), 0.004, seg=5)
        br.box(surf(0.335, math.pi / 2, 0.028), (0.03, 0.006, 0.012))
        br.torus(surf(0.52, math.pi / 2, 0.012), 0.008, 0.0022, seg=10, tseg=4, rot=(0, math.pi / 2, 0))
    return [g]


# =================================================================== upright piano
def build_piano(lite):
    g = Group("piano")
    wd = g["wood"]
    WAL = (0.34, 0.20, 0.12)
    W = 1.50
    yk = -0.30          # front edge of the keys
    zk = 0.715          # white key top
    yF = -0.47          # case front below/above the keys
    yB = -0.94
    H = 1.28
    # cheeks with keyboard arms (polygon in the YZ plane)
    cheek = [(yB, 0.0), (yF, 0.0), (yF, 0.60), (yk - 0.02, 0.60), (yk - 0.02, zk + 0.07), (yk - 0.05, zk + 0.10),
             (yF, zk + 0.12), (yF, H), (yB, H)]
    for s in (-1, 1):
        x = s * (W / 2 - 0.02)
        M = basis((0, 1, 0), (0, 0, 1), (1, 0, 0), (x, 0, 0))
        wd.shape(cheek, depth=0.045, M=M, tint=WAL, grain=1, bevel=0.003)
        # toe block and turned leg under the keyboard arm
        wd.box((x, (yk + yF) / 2 - 0.02, 0.03), (0.07, 0.3, 0.06), tint=WAL)
        wd.lathe([(0.03, 0.06), (0.036, 0.1), (0.022, 0.16), (0.03, 0.3), (0.034, 0.42), (0.026, 0.52),
                  (0.04, 0.56), (0.04, 0.6)], seg=8 if lite else 12,
                 M=Matrix.Translation((x, yk + 0.06, 0)), tint=WAL)
    # key bed, key slip, keys
    wd.box((0, (yk + yF) / 2, 0.635), (W - 0.09, yF - yk, 0.05), tint=WAL)
    wd.box((0, yk - 0.01, zk - 0.03), (W - 0.09, 0.02, 0.05), tint=WAL)
    ivory, ebony = g["ivory"], g["ebony"]
    kw = 1.225 / 52
    x0 = -1.225 / 2
    names = "ABCDEFG"
    if lite:
        ivory.box((0, yk - 0.075, zk - 0.011), (1.225, 0.145, 0.022))
    for i in range(52):
        x = x0 + kw * (i + 0.5)
        if not lite:
            ivory.box((x, yk - 0.075, zk - 0.011), (kw - 0.0012, 0.145, 0.022), var=0.03)
        n = names[i % 7]
        if n in "ACDFG" and i < 51:
            ebony.box((x + kw / 2, yk - 0.105, zk + 0.006), (0.0115, 0.09, 0.014))
    # fallboard (open), name board, upper front with panels, music desk, sheet music
    wd.box((0, yF + 0.01, zk + 0.07), (W - 0.09, 0.03, 0.12), tint=WAL)
    wd.box((0, yF + 0.015, 0.96), (W - 0.09, 0.03, 0.62 - 0.1), tint=WAL)
    for sx in (-1, 1):
        cx = sx * 0.36
        for dz, h in ((0.0, 0.36),):
            fz = 1.02
            for (px, pz, sw, sh) in ((cx, fz + h / 2, 0.5, 0.02), (cx, fz - h / 2, 0.5, 0.02),
                                     (cx - 0.25, fz, 0.02, h), (cx + 0.25, fz, 0.02, h)):
                wd.box((px, yF + 0.035, pz), (sw, 0.015, sh), tint=(0.26, 0.15, 0.09))
    wd.box((0, yF + 0.07, 0.862), (0.95, 0.09, 0.02), tint=WAL)      # music desk ledge
    wd.box((0, yF + 0.105, 0.875), (0.95, 0.012, 0.03), tint=WAL)
    pap = g["paper"]
    for i, (x, rz) in enumerate(((-0.15, 0.03), (0.13, -0.02), (0.02, 0.0))):
        M = Matrix.Translation((x, yF + 0.06 + 0.004 * i, 1.035)) @ Rz(rz) @ Rx(0.2)
        pap.mbox(M, (0.23, 0.003, 0.31), tint=(1.0, 0.97, 0.9) if i < 2 else (0.95, 0.9, 0.8))
    if not lite:
        ink = g["ebony"]
        for x in (-0.15, 0.13):
            for k in range(6):
                zz = 0.93 + 0.045 * k
                ink.box((x, yF + 0.064 - (zz - 1.035) * 0.2, zz), (0.19, 0.0015, 0.004), rot=(0.2, 0, 0))
    # lower front (knee board) with a moulded panel, plinth, pedals
    wd.box((0, yF + 0.015, 0.33), (W - 0.09, 0.03, 0.54), tint=WAL)
    for (px, pz, sw, sh) in ((0, 0.52, 1.1, 0.02), (0, 0.14, 1.1, 0.02), (-0.55, 0.33, 0.02, 0.4), (0.55, 0.33, 0.02, 0.4)):
        wd.box((px, yF + 0.035, pz), (sw, 0.015, sh), tint=(0.26, 0.15, 0.09))
    wd.box((0, yF + 0.02, 0.04), (W - 0.02, 0.05, 0.08), tint=(0.2, 0.12, 0.07))
    brass = g["brass"]
    for x in (-0.09, 0.0, 0.09):
        brass.box((x, yF + 0.08, 0.07), (0.035, 0.13, 0.012), rot=(-0.12, 0, 0))
    # top, back and lid
    wd.box((0, (yF + yB) / 2 - 0.02, H + 0.015), (W + 0.04, abs(yB - yF) + 0.1, 0.03), tint=WAL)
    wd.box((0, yB + 0.015, H / 2), (W - 0.06, 0.03, H), tint=(0.28, 0.2, 0.14))
    wd.box((0, yF + 0.015, 1.24), (W - 0.09, 0.03, 0.06), tint=WAL)
    # brass candle sconces with lit candles
    for sx in (() if lite else (-1, 1)):
        base = Vector((sx * 0.6, yF + 0.035, 1.02))
        brass.cyl(base, 0.035, 0.035, 0.012, seg=10, rot=(math.pi / 2, 0, 0))
        arm = [base + Vector((0, 0.01, 0)), base + Vector((0, 0.07, -0.02)), base + Vector((0, 0.13, 0.02))]
        brass.tube(arm, 0.006, tseg=5)
        cupc = base + Vector((0, 0.13, 0.03))
        brass.lathe([(0.001, -0.01), (0.03, 0.0), (0.035, 0.01), (0.015, 0.012), (0.014, 0.03)], seg=10,
                    M=Matrix.Translation(cupc))
        g["ivory"].cyl(cupc + Vector((0, 0, 0.09)), 0.011, 0.011, 0.12, seg=8, tint=(1.0, 0.97, 0.9))
        g["bulb_warm"].sphere(cupc + Vector((0, 0, 0.165)), 0.009, seg=6, rings=5, scale=(1, 1, 1.9))
    # bench
    seat_z = 0.50
    wd.box((0, 0.02, seat_z - 0.03), (0.92, 0.36, 0.05), tint=WAL)
    g["felt"].box((0, 0.02, seat_z), (0.88, 0.33, 0.035), tint=(0.5, 0.05, 0.06))
    for sx in (-1, 1):
        for sy in (-1, 1):
            rod(wd, (sx * 0.4, 0.02 + sy * 0.13, seat_z - 0.05), (sx * 0.42, 0.02 + sy * 0.15, 0.0), 0.022,
                seg=6 if lite else 8, tint=WAL, caps=True)
        wd.box((sx * 0.41, 0.02, 0.18), (0.03, 0.28, 0.03), tint=WAL)
    wd.box((0, 0.02, 0.18), (0.8, 0.03, 0.03), tint=WAL)
    return [g]


# =================================================================== double bass
BASS_OUTLINE = [  # (z, half width) of the body, bottom to top
    (0.14, 0.0), (0.155, 0.14), (0.19, 0.24), (0.26, 0.31), (0.36, 0.345), (0.46, 0.34), (0.55, 0.31),
    (0.62, 0.265), (0.68, 0.238), (0.745, 0.236), (0.80, 0.255), (0.87, 0.27), (0.95, 0.262),
    (1.02, 0.225), (1.09, 0.16), (1.16, 0.10), (1.22, 0.07), (1.25, 0.0)]


def bass_outline(n):
    pts = rc.smooth_path([(z, w) for z, w in BASS_OUTLINE], 3)
    zs = [p[0] for p in pts]
    ws = [max(0.0, p[1]) for p in pts]
    # resample to n/2 points per side, even in arc length
    import bisect
    L = [0.0]
    for i in range(1, len(pts)):
        L.append(L[-1] + math.hypot(zs[i] - zs[i - 1], ws[i] - ws[i - 1]))
    half = n // 2
    right = []
    for k in range(half + 1):
        s = L[-1] * k / half
        i = min(max(bisect.bisect_left(L, s), 1), len(L) - 1)
        t = (s - L[i - 1]) / max(L[i] - L[i - 1], 1e-9)
        right.append((ws[i - 1] + (ws[i] - ws[i - 1]) * t, zs[i - 1] + (zs[i] - zs[i - 1]) * t))
    ring = [(w, z) for w, z in right] + [(-w, z) for w, z in reversed(right[1:-1])]
    return ring   # (x, z), counter-clockwise from the bottom point


def bass_width(z):
    for (z0, w0), (z1, w1) in zip(BASS_OUTLINE[:-1], BASS_OUTLINE[1:]):
        if z0 <= z <= z1:
            return w0 + (w1 - w0) * (z - z0) / (z1 - z0)
    return 0.0


def build_bass(lite):
    Mh = Matrix.Translation((0.16, -0.30, 0)) @ Rz(-0.32) @ Rx(-0.26)
    g = Group("bass", "act_bass", pivot=(0.16, -0.30, 0), M=Mh)
    wd = g["wood"]
    VARN = (0.62, 0.30, 0.12)
    eb = g["ebony"]
    ring = bass_outline(28 if lite else 44)
    zc = 0.70

    def plate(s, y):
        return [Vector((x * s, y, zc + (z - zc) * s)) for x, z in ring]
    arch = 0.036
    front = [(1.0, -0.10), (0.86, -0.10 - arch * (1 - 0.86 ** 2)), (0.62, -0.10 - arch * (1 - 0.62 ** 2)),
             (0.36, -0.10 - arch * (1 - 0.36 ** 2))]
    back = [(0.4, 0.108), (0.75, 0.104), (1.0, 0.10)]
    rings = [plate(s, y) for s, y in back] + [plate(s, y) for s, y in front]
    wd.loft(rings, closed=True, cap_start=True, cap_end=True, smooth=True, grain=2, tint=VARN)
    # purfling line and the edge overhang of the top
    if not lite:
        eb.loft([plate(1.012, -0.098), plate(1.012, -0.104)], closed=True, smooth=True)

    def top_y(x, z):
        w = max(bass_width(z), 1e-3)
        s = min(1.0, abs(x) / w)
        return -0.10 - arch * (1 - s * s)
    # f-holes: slotted S curves with round eyes
    hole = g["hole"]
    for sx in (-1, 1):
        pts = [(0.0, 0.84), (0.014, 0.81), (0.022, 0.76), (0.01, 0.70), (-0.012, 0.645), (-0.02, 0.595), (-0.01, 0.565)]
        path = rc.smooth_path(pts, 1 if lite else 3)
        x0 = sx * 0.125
        band_l, band_r = [], []
        for i, (dx, z) in enumerate(path):
            a = path[max(i - 1, 0)]
            b = path[min(i + 1, len(path) - 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, tz) or 1
            nx, nz = -tz / ln, tx / ln
            wdt = 0.0065 if 2 < i < len(path) - 3 else 0.004
            band_l.append((x0 + sx * dx + nx * wdt * sx, z + nz * wdt))
            band_r.append((x0 + sx * dx - nx * wdt * sx, z - nz * wdt))
        poly = band_l + list(reversed(band_r))
        # orient polygon for the shape fill (any winding works for curves)
        yy = top_y(x0, 0.70) - 0.001
        M = basis((1, 0, 0), (0, 0, 1), (0, -1, 0), (0, yy, 0))
        hole.shape(poly, depth=0.004, M=M)
        for (dx, z) in (pts[0], pts[-1]):
            hole.shape(geo.circle_polygon(x0 + sx * dx, z, 0.013, 6 if lite else 10), depth=0.004, M=M)
    # neck, fingerboard, nut, pegbox, scroll, machines
    neck = [(0, 0.0, 1.20, 0.05), (0, -0.02, 1.35, 0.038), (0, -0.04, 1.55, 0.034), (0, -0.07, 1.73, 0.032)]
    pipe(wd, neck, n=8 if lite else 10, per=2, cap1=True, side=(1, 0, 0), tint=(0.7, 0.42, 0.2))
    fb = []
    for t in (0.0, 1.0):
        z = 0.80 + (1.735 - 0.80) * t
        y = -0.172 + (0.172 - 0.128) * t
        hw = 0.052 + (0.034 - 0.052) * t
        fb.append([Vector((-hw, y + 0.012, z)), Vector((hw, y + 0.012, z)), Vector((hw, y - 0.012, z)),
                   Vector((-hw, y - 0.012, z))])
    eb.loft(fb, closed=True, cap_start=True, cap_end=True, smooth=False)
    g["ivory"].box((0, -0.128, 1.738), (0.07, 0.024, 0.01), tint=(0.9, 0.85, 0.7))
    wd.box((0, -0.085, 1.82), (0.075, 0.075, 0.18), tint=(0.62, 0.36, 0.17))
    spiral = []
    for i in range(22 if not lite else 12):
        t = i / (21 if not lite else 11)
        a = -math.pi / 2 + t * 3.4 * math.pi
        r = 0.055 * (1 - 0.72 * t)
        spiral.append((0, -0.08 + r * math.sin(a) * -1, 1.935 + r * math.cos(a), 0.022 * (1 - 0.45 * t)))
    spiral = [(0, -0.085, 1.905, 0.035)] + spiral
    pts = [p[:3] for p in spiral]
    sweep(wd, pts, [0.036 * (1 - 0.5 * i / len(pts)) for i in range(len(pts))], [p[3] for p in spiral],
          n=8, cap0=True, cap1=True, side=(1, 0, 0), tint=(0.62, 0.36, 0.17))
    br = g["brass"]
    for sx in (-1, 1):
        br.box((sx * 0.04, -0.085, 1.81), (0.004, 0.06, 0.16))
        for z in (1.76, 1.86):
            rod(br, (sx * 0.04, -0.085, z), (sx * 0.085, -0.085, z), 0.005, seg=6)
            if not lite:
                br.sphere((sx * 0.1, -0.085, z), 0.022, seg=8, rings=5, scale=(0.4, 1, 1))
            rod(br, (sx * 0.042, -0.06, z + 0.02), (sx * 0.042, -0.035, z + 0.02), 0.012, seg=8, caps=True)
    # bridge standing on the top (maple, with heart and kidney cut-outs)
    zb = 0.705
    yb = top_y(0.0, zb)
    br_poly = [(-0.09, 0.0), (-0.05, 0.0), (-0.035, 0.035), (0.035, 0.035), (0.05, 0.0), (0.09, 0.0),
               (0.085, 0.03), (0.07, 0.10), (0.078, 0.125), (0.06, 0.137), (0.02, 0.143), (-0.02, 0.143),
               (-0.06, 0.137), (-0.078, 0.125), (-0.07, 0.10), (-0.085, 0.03)]
    br_poly.reverse()
    holes = [] if lite else [geo.circle_polygon(-0.033, 0.083, 0.011, 8), geo.circle_polygon(0.033, 0.083, 0.011, 8),
                             geo.heart_polygon(0.0, 0.108, 0.03, 12)]
    Mb = basis((1, 0, 0), (0, -1, 0), (0, 0, 1), (0, yb + 0.004, zb))
    wd.shape(br_poly, holes=holes, depth=0.014, M=Mb, tint=(0.95, 0.78, 0.55), grain=0)
    ytop = yb + 0.004 - 0.143
    # tailpiece and tail gut to the endpin
    tp = []
    for t in (0.0, 1.0):
        z = 0.27 + (0.55 - 0.27) * t
        y = top_y(0, z) - 0.02 - 0.035 * t
        hw = 0.035 + (0.065 - 0.035) * t
        tp.append([Vector((-hw, y + 0.01, z)), Vector((hw, y + 0.01, z)), Vector((hw, y - 0.01, z)),
                   Vector((-hw, y - 0.01, z))])
    eb.loft(tp, closed=True, cap_start=True, cap_end=True, smooth=False)
    rod(eb, (0, top_y(0, 0.27) - 0.015, 0.27), (0, -0.02, 0.15), 0.006, seg=5)
    # strings: tailpiece -> bridge -> nut -> pegbox
    st = g["strings"]
    ytp = top_y(0, 0.55) - 0.056
    for i, (xt, xb, xn, r) in enumerate(((-0.036, -0.045, -0.024, 0.0024), (-0.012, -0.016, -0.008, 0.0019),
                                         (0.012, 0.016, 0.008, 0.0015), (0.036, 0.045, 0.024, 0.0012))):
        a = Vector((xt, ytp, 0.54))
        b = Vector((xb, ytop, zb))
        c = Vector((xn, -0.142, 1.74))
        d = Vector((xn * 0.5, -0.095, 1.80))
        for p, q in ((a, b), (b, c), (c, d)):
            rod(st, p, q, r, seg=4 if lite else 5)
    # endpin
    rod(g["chrome"], (0, 0, 0.0), (0, 0, 0.16), 0.006, seg=6, caps=True)
    rod(eb, (0, 0, 0.13), (0, 0, 0.16), 0.022, seg=10, caps=True)
    groups = [g]

    # the stand with the bow in its holder (static, to the player's right)
    s = Group("bassstand", None, M=Matrix.Translation((-0.66, -0.12, 0)) @ Rz(0.4))
    bm = s["blackmetal"]
    for a in (0.0, 2.3, -2.3):
        rod(bm, (0, 0, 0.12), (0.34 * math.cos(a), 0.34 * math.sin(a), 0.01), 0.012, seg=6)
        s["ebony"].sphere((0.34 * math.cos(a), 0.34 * math.sin(a), 0.012), 0.02, seg=6, rings=4)
    rod(bm, (0, 0, 0.08), (0, 0, 0.95), 0.015, seg=8)
    # cradle and yoke with padding
    for z, w, h in ((0.3, 0.2, 0.12), (0.95, 0.1, 0.1)):
        pts = [(-w, -0.12, z + h), (-w, -0.1, z), (0, -0.04, z - 0.03), (w, -0.1, z), (w, -0.12, z + h)]
        s["leather"].tube([Vector(p) for p in pts], 0.018, tseg=6, tint=(0.25, 0.25, 0.25))
        rod(bm, (0, 0, z), (0, -0.05, z - 0.02), 0.012, seg=6)
    # bow holder cup and the bow standing in it
    rod(s["leather"], (0.07, 0.02, 0.45), (0.07, 0.02, 0.60), 0.022, seg=10)
    rod(bm, (0, 0, 0.55), (0.07, 0.02, 0.55), 0.008, seg=5)
    bw = s["wood"]
    bow0 = Vector((0.07, 0.02, 0.46))
    bow1 = Vector((0.08, 0.03, 1.16))
    mid = bow0.lerp(bow1, 0.5) + Vector((0.012, -0.006, 0))
    pipe(bw, [(bow0.x, bow0.y, bow0.z, 0.0055), (mid.x, mid.y, mid.z, 0.0048), (bow1.x, bow1.y, bow1.z, 0.004)],
         n=6, per=3, tint=(0.42, 0.14, 0.06))
    s["ebony"].box(bow0 + Vector((-0.012, 0, 0.05)), (0.016, 0.02, 0.06))
    s["canvas"].box((bow0 + bow1) / 2 + Vector((-0.017, 0, 0.01)), (0.002, 0.012, 0.64), tint=(1.1, 1.05, 0.95))
    s["ivory"].box(bow1 + Vector((-0.01, 0, 0.0)), (0.02, 0.012, 0.02))
    groups.append(s)
    return groups


# =================================================================== drums
def cymbal(part, c, R, rot, lite, tint=None):
    prof = [(0.001, 0.028), (0.018, 0.028), (0.03, 0.024), (0.05, 0.014), (0.07, 0.009),
            (R * 0.55, 0.005), (R * 0.85, 0.001), (R, -0.003)]
    part.lathe(prof, seg=12 if lite else 24, M=Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4(), tint=tint)


def drum(g, c, r, h, M_axis, lite, shell_tint, lugs=8, heads=(True, True)):
    """Drum with shell, two heads, hoops and lugs. M_axis turns local Z into the drum axis."""
    seg = 14 if lite else 32
    M = Matrix.Translation(c) @ M_axis
    g["wood"].lathe([(r, -h / 2), (r, h / 2)], seg=seg, M=M, tint=shell_tint)
    if heads[0]:
        g["drumhead"].lathe([(0.001, h / 2 + 0.004), (r - 0.004, h / 2 + 0.004), (r + 0.002, h / 2 - 0.004)], seg=seg, M=M)
    if heads[1]:
        g["drumhead"].lathe([(r + 0.002, -h / 2 + 0.004), (r - 0.004, -h / 2 - 0.004), (0.001, -h / 2 - 0.004)], seg=seg, M=M,
                            tint=(0.9, 0.88, 0.84))
    for z in (h / 2, -h / 2):
        g["chrome"].lathe([(r + 0.002, z - 0.012), (r + 0.01, z - 0.008), (r + 0.01, z + 0.008), (r + 0.002, z + 0.012)],
                          seg=seg, M=M)
    if not lite or lugs <= 8:
        for k in range(lugs if not lite else lugs // 2):
            a = TAU * (k + 0.5) / lugs
            p = M @ Vector(((r + 0.012) * math.cos(a), (r + 0.012) * math.sin(a), 0))
            d = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
            q = (M.to_3x3() @ Vector((math.cos(a), math.sin(a), 0))).normalized()
            g["chrome"].mbox(basis(q, d.cross(q), d, p), (0.014, 0.018, min(0.07, h * 0.45)))
            if not lite:
                for s in (-1, 1):
                    rod(g["chrome"], p + d * (s * h * 0.25), p + d * (s * (h / 2 + 0.014)), 0.0035, seg=4)


def build_drums(lite):
    g = Group("drums")
    SHELL = (0.66, 0.22, 0.12)
    ch, bm = g["chrome"], g["blackmetal"]
    rs = 4 if lite else 6

    def tripod(x, y, z_top, spread=0.3, h_legs=0.25):
        for k in range(3):
            a = TAU * k / 3 + 0.5
            rod(ch, (x, y, h_legs), (x + spread * math.cos(a), y + spread * math.sin(a), 0.01), 0.008, seg=rs)
            if not lite:
                g["ebony"].sphere((x + spread * math.cos(a), y + spread * math.sin(a), 0.012), 0.013, seg=6, rings=4)
        rod(ch, (x, y, 0.1), (x, y, z_top), 0.012, seg=rs + 2)
    # throne
    tripod(0, 0, 0.46, 0.28, 0.2)
    g["leather"].cyl((0, 0, 0.5), 0.175, 0.17, 0.08, seg=16 if lite else 24, tint=(0.25, 0.25, 0.25))
    bm.cyl((0, 0, 0.455), 0.1, 0.1, 0.02, seg=12)
    # kick drum 18x14 lying on its side, front head with a painted emblem
    kc = Vector((-0.02, -0.80, 0.235))
    drum(g, kc, 0.23, 0.36, Rx(math.pi / 2), lite, SHELL, lugs=8)
    for s in (-1, 1):
        g["wood"].lathe([(0.232, -0.02), (0.245, -0.02), (0.245, 0.02), (0.232, 0.02)], seg=20 if lite else 32,
                        M=Matrix.Translation(kc + Vector((0, s * 0.19, 0))) @ Rx(math.pi / 2), tint=(0.3, 0.1, 0.05))
    Mf = Matrix.Translation(kc + Vector((0, -0.187, 0))) @ Rx(math.pi / 2)
    g["enamel"].shape(geo.circle_polygon(0, 0, 0.12, 24), depth=0.003, M=Mf @ Rx(math.pi), tint=(0.45, 0.03, 0.04))
    g["gilt"].shape(geo.star_polygon(0, 0, 0.085, 0.035, 8), depth=0.003, M=Mf @ Rx(math.pi) @
                    Matrix.Translation((0, 0, -0.003)))
    g["gilt"].shape(geo.circle_polygon(0, 0, 0.13, 24), holes=[geo.circle_polygon(0, 0, 0.118, 24)], depth=0.003,
                    M=Mf @ Rx(math.pi) @ Matrix.Translation((0, 0, -0.002)))
    for s in (-1, 1):
        rod(ch, kc + Vector((s * 0.2, -0.05, -0.08)), kc + Vector((s * 0.36, -0.22, -0.235)), 0.008, seg=rs)
    # pedal and beater
    bm.box((kc.x, kc.y + 0.36, 0.02), (0.08, 0.26, 0.012), rot=(0.12, 0, 0))
    rod(ch, (kc.x, kc.y + 0.25, 0.04), (kc.x, kc.y + 0.2, 0.2), 0.004, seg=4)
    g["felt"].sphere((kc.x, kc.y + 0.2, 0.22), 0.028, seg=8, rings=5, tint=(0.8, 0.78, 0.7))
    # snare 14x5.5 on its stand, tilted toward the drummer
    sc = Vector((0.03, -0.36, 0.60))
    Ms = Rx(-0.12)
    drum(g, sc, 0.178, 0.135, Ms, lite, SHELL, lugs=10)
    tripod(sc.x, sc.y, sc.z - 0.1, 0.26, 0.22)
    for k in range(3):
        a = TAU * k / 3 + 0.3
        rod(ch, (sc.x, sc.y, sc.z - 0.1), (sc.x + 0.16 * math.cos(a), sc.y + 0.16 * math.sin(a), sc.z - 0.07), 0.006, seg=4)
    # rack tom 12x8 on the kick, floor tom 14x14 on legs
    tc = Vector((0.16, -0.66, 0.64))
    drum(g, tc, 0.152, 0.2, Rx(-0.25) @ Ry(0.12), lite, SHELL, lugs=6)
    rod(ch, kc + Vector((0.08, 0.02, 0.22)), tc + Vector((-0.02, 0.0, -0.12)), 0.011, seg=rs)
    fc = Vector((-0.46, -0.30, 0.43))
    drum(g, fc, 0.178, 0.36, Matrix(), lite, SHELL, lugs=8)
    for k in range(3):
        a = TAU * k / 3 + 1.0
        p = fc + Vector((0.2 * math.cos(a), 0.2 * math.sin(a), 0.06))
        rod(ch, p, Vector((fc.x + 0.28 * math.cos(a), fc.y + 0.28 * math.sin(a), 0.01)), 0.007, seg=rs)
    # hi-hat on the left, ride on the right
    hx, hy = 0.47, -0.42
    tripod(hx, hy, 0.9, 0.28, 0.3)
    rod(ch, (hx, hy, 0.9), (hx, hy, 1.0), 0.004, seg=4)
    cymbal(g["bronze"], (hx, hy, 0.885), 0.178, (math.pi, 0, 0), lite)
    cymbal(g["bronze"], (hx, hy, 0.905), 0.178, (0, 0, 0), lite)
    bm.box((hx, hy + 0.18, 0.03), (0.08, 0.24, 0.012), rot=(0.18, 0, 0))
    rx, ry = -0.52, -0.78
    tripod(rx, ry, 0.9, 0.32, 0.3)
    top = Vector((-0.34, -0.68, 1.02))
    rod(ch, (rx, ry, 0.88), top - Vector((0, 0, 0.03)), 0.009, seg=rs)
    cymbal(g["bronze"], top, 0.255, (-0.2, 0.12, 0), lite, tint=(0.8, 0.72, 0.6))
    # brushes resting across the snare head
    groups = [g]
    head_z = sc.z + 0.072
    for name, a, dx in (("act_brush_l", 0.5, 0.05), ("act_brush_r", -0.55, -0.05)):
        d = Vector((math.sin(a), -math.cos(a), 0))
        h0 = Vector((sc.x + dx, sc.y + 0.28, head_z + 0.06))
        h1 = h0 + d * 0.22 + Vector((0, 0, -0.035))
        b = Group(name.replace("act_", ""), name, pivot=h0)
        rod(b["ebony"], h0, h1, 0.008, seg=6, caps=True)
        rod(b["chrome"], h1, h1 + d * 0.06, 0.005, seg=5)
        base = h1 + d * 0.06
        wires = 7 if lite else 14
        side = d.cross(Vector((0, 0, 1)))
        for k in range(wires):
            f = (k / (wires - 1) - 0.5) * 0.09
            tipp = base + d * 0.13 + side * f + Vector((0, 0, -0.01 - 0.004 * abs(f) * 10))
            rod(b["strings"], base + side * f * 0.15, tipp, 0.0009, seg=3)
        groups.append(b)
    return groups


INSTRUMENTS = {"sax": build_sax, "piano": build_piano, "bass": build_bass, "drums": build_drums}


def export_build(key):
    def build(lite):
        root = node(f"instr_{key}", (0, 0, 0))
        for grp in INSTRUMENTS[key](lite):
            parent = root
            if grp.node_name:
                parent = node(grp.node_name, tuple(grp.pivot), parent=root)
            for ob in grp.finish():
                rc.attach(ob, parent)
        return rc.mesh_objs()
    return build


def place_in(key, M_slot, lite=False):
    """Render-only copy of an instrument at a slot matrix (bandstand preview)."""
    env = state.env_collection()
    objs = []
    for grp in INSTRUMENTS[key](lite):
        for ob in grp.finish(env):
            ob.matrix_world = M_slot
            objs.append(ob)
    return objs


def sax_on_stand(M_slot):
    """Render-only: the sax resting upright on a floor stand (the band on a break)."""
    env = state.env_collection()
    grp = build_sax(False)[0]
    # undo the held pose: stand the sax upright, bell forward, bow resting in the cradle
    grp.M = M_slot @ Matrix.Translation((0.05, -0.35, 0.14)) @ Rz(0.5) @ Rx(-0.12)
    objs = grp.finish(env)
    for ob in objs:
        ob.matrix_world = Matrix()
    st = Group("saxstand", M=M_slot @ Matrix.Translation((0.05, -0.35, 0.0)) @ Rz(0.5))
    bm = st["blackmetal"]
    for k in range(3):
        a = TAU * k / 3 + 0.3
        rod(bm, (0, -0.07, 0.1), (0.2 * math.cos(a), -0.07 + 0.2 * math.sin(a), 0.01), 0.007, seg=5)
    rod(bm, (0, -0.07, 0.02), (0, -0.07, 0.62), 0.009, seg=6)
    rod(bm, (0, -0.07, 0.62), (0, 0.0, 0.64), 0.008, seg=5)
    st["leather"].tube([Vector((-0.05, -0.1, 0.16)), Vector((-0.05, -0.05, 0.08)), Vector((0.05, -0.05, 0.08)),
                        Vector((0.05, -0.1, 0.16))], 0.012, tseg=5, tint=(0.3, 0.3, 0.3))
    for ob in st.finish(env):
        ob.matrix_world = Matrix()
    return objs


def preview_one(key):
    def pv(objs):
        f = -1 if key == "piano" else 1
        render.add_light("env_key", 'AREA', (1.2, -2.2 * f, 2.4), 90, size=1.2,
                         rot=(math.radians(55 * f), 0, math.radians(30 if f > 0 else 150)))
        render.add_light("env_warm", 'POINT', (-1.2, -1.5 * f, 1.8), 60, size=0.4)
        render.add_light("env_rim", 'AREA', (-1.0, 1.8, 2.2), 70, color=(0.6, 0.7, 1.0), size=1.5,
                         rot=(math.radians(-60), 0, math.radians(200)))
        cams = {"sax": ((0.75, -1.9, 1.4), (-0.12, -0.3, 1.15), 40),
                "piano": ((1.25, 1.35, 1.55), (0.0, -0.55, 0.85), 34),
                "bass": ((-0.9, -2.4, 1.3), (-0.05, -0.3, 0.95), 34),
                "drums": ((0.9, -2.6, 1.7), (-0.05, -0.55, 0.6), 36)}
        loc, tgt, lens = cams[key]
        return render.camera(loc, tgt, lens=lens)
    return pv


if __name__ == "__main__":
    a = rc.args()
    keys = a.only.split(",") if a.only else list(INSTRUMENTS)
    for k in keys:
        rc.run(f"instr_{k}", export_build(k), preview_one(k), seed=40 + len(k), ao_full=512, ao_lite=256,
               tex_full=512, tex_lite=256, ground=12)
