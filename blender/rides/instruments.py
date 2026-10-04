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


def register_art():
    import art
    # the double bass's spruce top: straight fine grain under amber varnish (round 2 judges: the kit
    # wood read as wavy walnut on the top)
    rc.IMAGE_MATS["spruce_top"] = (art.spruce(), 0.38)


register_art()


def Rx(a):
    return Euler((a, 0, 0)).to_matrix().to_4x4()


def Ry(a):
    return Euler((0, a, 0)).to_matrix().to_4x4()


def Rz(a):
    return Euler((0, 0, a)).to_matrix().to_4x4()


class FinePart(Part):
    """A Part whose kit texture repeats `uv_scale` times finer by default: instrument wood has
    a grain line every few millimetres, not the stall kit's plank scale."""

    def __init__(self, *a, uv_scale=1.0, **kw):
        super().__init__(*a, **kw)
        self.uv_scale = uv_scale

    def _emit(self, bm, M, uv_scale=None, **kw):
        super()._emit(bm, M, uv_scale=self.uv_scale if uv_scale is None else uv_scale, **kw)


class Group:
    """Parts that end up under one node (the instrument root or an act_ pivot).

    wood_scale: kit repeat for the wood (0.35 = grain about three times finer than the stalls').
    warp: optional function applied to every vertex in the build frame before M (the sax uses
    it to lengthen its body without moving each key by hand)."""

    def __init__(self, prefix, node_name=None, pivot=(0, 0, 0), M=None, wood_scale=1.0, warp=None):
        self.prefix = prefix
        self.node_name = node_name
        self.pivot = Vector(pivot)
        self.M = M or Matrix()          # local build frame -> instrument frame
        self.parts = {}
        self.wood_scale = wood_scale
        self.warp = warp

    def __getitem__(self, mat):
        if mat not in self.parts:
            nm = f"{self.prefix}_{mat}" if not mat.startswith("bulb_") else f"bulbs_{self.prefix}"
            kw = {}
            if mat in ("wood", "rsteel", "paint"):
                kw["bevel"] = 0.0015
            if mat == "wood_veneer":
                # veneer wrapped round a drum shell: the lathe maps the grain along the drum's
                # axis (it reads as barrel staves), so the UVs are turned a quarter after finish()
                kw["bevel"] = 0.0015
                self.parts[mat] = FinePart(nm, "wood", var=0.03, uv_scale=self.wood_scale, **kw)
                self.parts[mat].swap_uv = True
            elif mat == "spruce_top":
                # an image material mapped flat across the front (u across, v along the body)
                self.parts[mat] = Part(nm, mat, var=0.0)
                self.parts[mat].planar_uv = True
            elif mat == "wood" and self.wood_scale != 1.0:
                self.parts[mat] = FinePart(nm, mat, var=0.03, uv_scale=self.wood_scale, **kw)
            else:
                self.parts[mat] = Part(nm, mat, var=0.03, **kw)
        return self.parts[mat]

    def finish(self, coll=None):
        objs = []
        for p in self.parts.values():
            ob = p.finish(coll)
            if ob is not None:
                if getattr(p, "planar_uv", False):
                    uv = ob.data.uv_layers["UVMap"].data
                    for poly in ob.data.polygons:
                        for li, vi in zip(poly.loop_indices, poly.vertices):
                            co = ob.data.vertices[vi].co
                            uv[li].uv = (co.x / 0.72 + 0.5, (co.z - 0.14) / 1.11)
                if getattr(p, "swap_uv", False):
                    uv = ob.data.uv_layers["UVMap"].data
                    for l in uv:
                        u, v = l.uv
                        l.uv = (v, u)
                if self.warp is not None:
                    for v in ob.data.vertices:
                        v.co = self.warp(v.co)
                ob.data.transform(self.M)
                objs.append(ob)
        return objs


# =================================================================== tenor saxophone
# Tenor proportions: a 0.64 m straight body from the neck socket to the bow, the bell rim at 54 %
# of the body height, a 15 cm bell, and a neck with the tenor's rise-and-hump.
SAX_TOP, SAX_BOW = 0.78, 0.14
SAX_R_TOP, SAX_R_BOW = 0.0145, 0.041


def sax_body_r(z):
    t = min(max((z - SAX_BOW) / (SAX_TOP - SAX_BOW), 0.0), 1.0)
    return SAX_R_BOW + (SAX_R_TOP - SAX_R_BOW) * t


SAX_STRETCH = 1.10   # round 2: the body, bow and bell tube 10 % longer (a 0.70 m tenor body)


def sax_warp(co):
    """Lengthen everything below the neck socket; the neck, mouthpiece and octave key move up."""
    z = co.z
    if SAX_BOW < z <= SAX_TOP:
        z = SAX_BOW + (z - SAX_BOW) * SAX_STRETCH
    elif z > SAX_TOP:
        z = z + (SAX_TOP - SAX_BOW) * (SAX_STRETCH - 1)
    return Vector((co.x, co.y, z))


def build_sax(lite, held=True):
    # sax frame: body axis +Z, bell and pearls toward -Y (away from the player)
    tip = sax_warp(Vector((0, 0.272, 0.896)))
    beta = 0.36
    Mh = Ry(beta)
    t = Mh @ tip
    M = Matrix.Translation(Vector((0.0, -0.10, 1.53)) - t) @ Mh
    strap = M @ sax_warp(Vector((0, 0.04, 0.60)))
    g = Group("sax", "act_sax" if held else None, pivot=strap, M=M, warp=sax_warp)
    br, iv, eb, ch = g["saxbrass"], g["ivory"], g["ebony"], g["chrome"]
    lea = g["leather"]
    n = 10 if lite else 16
    # one continuous tube: body, bow, bell tube and a short flare
    ctrl = [(0, 0, SAX_TOP, SAX_R_TOP), (0, 0, 0.66, 0.0195), (0, 0, 0.52, 0.0253), (0, 0, 0.38, 0.031),
            (0, 0, 0.24, 0.0366), (0, 0, SAX_BOW, SAX_R_BOW), (0, -0.012, 0.075, 0.043), (0, -0.065, 0.047, 0.044),
            (0, -0.118, 0.075, 0.045), (0, -0.131, 0.14, 0.047), (0, -0.134, 0.24, 0.050), (0, -0.137, 0.31, 0.054),
            (0, -0.141, 0.36, 0.059), (0, -0.144, 0.39, 0.064), (0, -0.147, 0.408, 0.069), (0, -0.150, 0.42, 0.075)]
    pipe(br, ctrl, n=n, per=1 if lite else 2, side=(1, 0, 0))
    br.torus((0, -0.1505, 0.4215), 0.075, 0.0045, seg=n + 6, tseg=4 if lite else 6, rot=(0.06, 0, 0))
    # bow guard band and the ring where body meets bow
    if not lite:
        br.torus((0, 0, 0.15), sax_body_r(0.15) + 0.002, 0.003, seg=16, tseg=4)
        br.torus((0, -0.131, 0.15), 0.048, 0.003, seg=16, tseg=4)
    # neck (crook) with the tenor's hump, cork, mouthpiece, ligature, reed
    neck = [(0, 0, 0.775, 0.0148), (0, 0.004, 0.82, 0.0142), (0, 0.025, 0.872, 0.013), (0, 0.07, 0.903, 0.0118),
            (0, 0.13, 0.911, 0.0106), (0, 0.185, 0.905, 0.0097)]
    pipe(br, neck, n=6 if lite else 12, per=1 if lite else 3, side=(1, 0, 0))
    br.torus((0, 0, 0.772), 0.0165, 0.0025, seg=12, tseg=4)                       # neck receiver
    rod(lea, (0, 0.18, 0.906), (0, 0.206, 0.9035), 0.0108, seg=8, tint=(0.62, 0.48, 0.32))    # cork
    rod(eb, (0, 0.20, 0.904), (0, 0.272, 0.896), 0.0152, r2=0.0092, seg=12, caps=True)
    rod(ch, (0, 0.214, 0.9025), (0, 0.229, 0.901), 0.0162, seg=12)
    if not lite:
        g["canvas"].box((0, 0.246, 0.886), (0.012, 0.058, 0.002), rot=(0.1, 0, 0), tint=(0.85, 0.72, 0.45))
        # octave key along the top of the neck, with its pad cup and ring
        rod(br, (0, 0.03, 0.887), (0, 0.118, 0.924), 0.0026, seg=4)
        rod(br, (0, 0.118, 0.924), (0, 0.131, 0.926), 0.0065, seg=8, caps=True)
        br.torus((0, 0.045, 0.894), 0.006, 0.0018, seg=8, tseg=3, rot=(math.pi / 2, 0, 0))

    def surf(z, a, off=0.0):
        r = sax_body_r(z) + off
        return Vector((r * math.cos(a), r * math.sin(a), z))

    def cup(z, a, rad, rod_a=None):
        """A tone hole with its chimney, the pad and a flat domed cup lying on the body; an arm
        joins it to the hinge rod at angle rod_a."""
        p = surf(z, a)
        d = Vector((math.cos(a), math.sin(a), 0))
        rod(br, p - d * 0.012, p + d * 0.004, rad * 0.82, seg=8 if lite else 12)           # chimney
        if not lite:
            rod(lea, p + d * 0.0035, p + d * 0.0058, rad * 0.97, seg=12, tint=(0.62, 0.50, 0.36))   # pad edge
        rod(br, p + d * 0.0055, p + d * 0.0105, rad, seg=8 if lite else 12)                  # cup wall
        br.sphere(p + d * 0.0105, rad, seg=8 if lite else 12, rings=2 if lite else 3, scale=(1, 1, 0.16),
                  rot=(0, math.pi / 2, a))                                                    # domed top
        if rod_a is not None and not lite:
            rod(br, p + d * 0.009, surf(z, rod_a, 0.012), 0.0022, seg=4)
        return p + d * 0.012

    front = -math.pi / 2
    rods = (front + 0.95, front - 1.05, 0.55)
    # hinge rods along the body on posts
    if not lite:
        for a, z0, z1 in ((rods[0], 0.27, 0.72), (rods[1], 0.22, 0.70), (rods[2], 0.30, 0.74)):
            rod(br, surf(z0, a, 0.012), surf(z1, a, 0.012), 0.0024, seg=5)
            for z in (z0, (z0 + z1) / 2, z1):
                rod(br, surf(z, a, 0.0), surf(z, a, 0.0125), 0.0032, seg=5)
                br.sphere(surf(z, a, 0.013), 0.004, seg=6, rings=4)
    # left-hand stack (B, A, G) and right-hand stack (F, E, D): cups on the front, pearls on arms
    for zs, a0, ra in (((0.665, 0.615, 0.565), front, rods[0]), ((0.42, 0.37, 0.32), front - 0.5, rods[1])):
        for z in zs:
            rad = 0.62 * sax_body_r(z) + 0.004
            top = cup(z, a0 + 0.42, rad, ra)
            pearl = surf(z - 0.014, a0 - 0.1, 0.026)
            rod(br, top, pearl, 0.0024, seg=4)
            iv.sphere(pearl, 0.0068, seg=6 if lite else 10, rings=4 if lite else 6, scale=(1, 1, 0.55),
                      rot=(0, math.pi / 2, a0 - 0.1))
            if not lite:
                br.sphere(pearl - Vector((0, 0, 0.0015)), 0.0088, seg=10, rings=4, scale=(1, 1, 0.42),
                          rot=(0, math.pi / 2, a0 - 0.1))
    # side, trill and auxiliary cups round the body
    cups = [(0.73, 0.95, rods[2]), (0.59, 1.45, rods[2]), (0.535, -0.35, rods[0]), (0.49, 0.75, rods[2]),
            (0.29, -0.25, rods[1]), (0.255, 1.15, rods[2]), (0.21, -2.35, rods[1]), (0.185, 0.45, rods[2])]
    for z, a, ra in cups[::2] if lite else cups:
        cup(z, a, 0.55 * sax_body_r(z) + 0.004, ra)
    # palm keys near the top on the player's left
    for i, z in enumerate((0.705, 0.73, 0.755)):
        p = surf(z, 0.25 + 0.2 * i, 0.02)
        br.box(p, (0.012, 0.024, 0.006), rot=(0, 0.3, 0.25 + 0.2 * i))
        iv.sphere(p + Vector((0, 0, 0.004)), 0.0062, seg=6, rings=4, scale=(1, 1, 0.5))
    if not lite:
        # low C and E-flat on the front near the bow, with wire guards
        for z, a, r in ((0.175, front - 0.3, 0.030), (0.205, front + 0.9, 0.024)):
            cup(z, a, r, None)
            gp = [surf(z - 0.05, a, 0.006), surf(z - 0.045, a, 0.042), surf(z + 0.045, a, 0.042), surf(z + 0.05, a, 0.006)]
            br.tube(gp, 0.0022, tseg=4)
        # low B and B-flat on the bell tube, facing the player's left
        for z in (0.23, 0.31):
            c = Vector((0, -0.134 - 0.003 * (z - 0.23) / 0.08, z))
            d = Vector((-1, 0, 0))
            rbt = 0.050 + 0.004 * (z - 0.23) / 0.08
            p = c + d * rbt
            rod(br, p - d * 0.01, p + d * 0.004, 0.024, seg=14)
            rod(br, p + d * 0.0055, p + d * 0.011, 0.029, seg=14)
            br.sphere(p + d * 0.011, 0.029, seg=14, rings=5, scale=(1, 1, 0.16), rot=(0, math.pi / 2, math.pi))
            rod(br, p + d * 0.009, surf(z, math.pi * 0.9, 0.012), 0.0024, seg=4)
        # thumb rest and octave thumb key (left hand), thumb hook (right hand), strap ring
        rod(br, surf(0.63, math.pi / 2, 0), surf(0.63, math.pi / 2, 0.014), 0.007, seg=10, caps=True)
        iv.sphere(surf(0.66, math.pi / 2, 0.016), 0.006, seg=8, rings=5, scale=(1, 1, 0.5), rot=(math.pi / 2, 0, 0))
        rod(br, surf(0.43, math.pi / 2, 0), surf(0.43, math.pi / 2, 0.025), 0.004, seg=5)
        br.box(surf(0.425, math.pi / 2, 0.028), (0.03, 0.006, 0.012))
        br.torus(surf(0.60, math.pi / 2, 0.012), 0.008, 0.0022, seg=10, tseg=4, rot=(0, math.pi / 2, 0))
    return [g]


# =================================================================== upright piano
def build_piano(lite):
    g = Group("piano", wood_scale=0.3)
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
    # (the lite piano keeps them too, with fewer segments: the lit candles are part of the scene)
    cs = 6 if lite else 10
    for sx in (-1, 1):
        base = Vector((sx * 0.6, yF + 0.035, 1.02))
        brass.cyl(base, 0.035, 0.035, 0.012, seg=cs, rot=(math.pi / 2, 0, 0))
        arm = [base + Vector((0, 0.01, 0)), base + Vector((0, 0.07, -0.02)), base + Vector((0, 0.13, 0.02))]
        brass.tube(arm, 0.006, tseg=4 if lite else 5)
        cupc = base + Vector((0, 0.13, 0.03))
        brass.lathe([(0.001, -0.01), (0.03, 0.0), (0.035, 0.01), (0.015, 0.012), (0.014, 0.03)], seg=cs,
                    M=Matrix.Translation(cupc))
        g["ivory"].cyl(cupc + Vector((0, 0, 0.09)), 0.011, 0.011, 0.12, seg=cs, tint=(1.0, 0.97, 0.9))
        g["bulb_warm"].sphere(cupc + Vector((0, 0, 0.165)), 0.009, seg=cs, rings=4 if lite else 5, scale=(1, 1, 1.9))
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
def bmesh_tri(bm):
    rc.bmesh.ops.triangulate(bm, faces=bm.faces[:])


# Right half of the body outline, (half width, z), bottom to top, as three smooth runs joined at
# sharp corners: the lower bout up to the lower corner, the C-bout, the upper bout with the
# viol-like sloping shoulders into the neck heel. Real proportions for a 3/4 bass: lower bout
# 0.69 m, waist 0.37 m, upper bout 0.54 m, body 1.11 m long.
BASS_RUNS = [
    [(0.0, 0.14), (0.14, 0.152), (0.25, 0.19), (0.32, 0.25), (0.345, 0.33), (0.342, 0.41),
     (0.325, 0.49), (0.305, 0.545), (0.296, 0.575)],                        # lower bout -> corner tip
    [(0.262, 0.566), (0.222, 0.590), (0.196, 0.632), (0.186, 0.68), (0.192, 0.73), (0.214, 0.768),
     (0.250, 0.786)],                                                        # C-bout (inside the corners)
    [(0.282, 0.776), (0.291, 0.80), (0.290, 0.85), (0.279, 0.905), (0.255, 0.965), (0.215, 1.03),
     (0.168, 1.095), (0.122, 1.155), (0.086, 1.200), (0.060, 1.232), (0.0, 1.25)],   # corner tip -> shoulders
]
BASS_CORNERS = [(0.296, 0.575), (0.262, 0.566), (0.250, 0.786), (0.282, 0.776)]


def _bass_dense():
    pts = []
    for run in BASS_RUNS:
        d = rc.smooth_path([(w, z) for w, z in run], 6)
        pts += d
    return pts


def bass_outline(n):
    """Closed outline ring (x, z), counter-clockwise from the bottom point, about n points, with
    the four corner points kept exactly so the corners stay sharp."""
    import bisect
    dense = _bass_dense()
    L = [0.0]
    for i in range(1, len(dense)):
        L.append(L[-1] + math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]))
    half = n // 2
    right = []
    for k in range(half + 1):
        s_ = L[-1] * k / half
        i = min(max(bisect.bisect_left(L, s_), 1), len(L) - 1)
        t = (s_ - L[i - 1]) / max(L[i] - L[i - 1], 1e-9)
        right.append((dense[i - 1][0] + (dense[i][0] - dense[i - 1][0]) * t,
                      dense[i - 1][1] + (dense[i][1] - dense[i - 1][1]) * t))
    for c in BASS_CORNERS:            # snap the nearest samples onto the corners
        j = min(range(1, len(right) - 1), key=lambda j: (right[j][0] - c[0]) ** 2 + (right[j][1] - c[1]) ** 2)
        right[j] = c
    right[0] = (0.0, right[0][1])
    right[-1] = (0.0, right[-1][1])
    ring = [(w, z) for w, z in right] + [(-w, z) for w, z in reversed(right[1:-1])]
    return ring


_BASS_W = None


def bass_width(z):
    """Half width of the body at height z (the widest crossing of the outline)."""
    global _BASS_W
    if _BASS_W is None:
        _BASS_W = _bass_dense()
    best = 0.0
    for (w0, z0), (w1, z1) in zip(_BASS_W[:-1], _BASS_W[1:]):
        if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
            best = max(best, w0 + (w1 - w0) * (z - z0) / (z1 - z0))
    return best


def build_bass(lite):
    Mh = Matrix.Translation((0.16, -0.30, 0)) @ Rz(-0.32) @ Rx(-0.26)
    g = Group("bass", "act_bass", pivot=(0.16, -0.30, 0), M=Mh)
    wd = g["wood"]
    VARN = (0.62, 0.30, 0.12)
    eb = g["ebony"]
    ring = bass_outline(24 if lite else 64)       # round 2: 44 points left the bouts faceted up close
    zc = 0.70

    def soften(r, passes):
        """Round the corners off an inner ring (neighbour averaging), so the arching of the top
        and back flattens out toward the corners instead of creasing from them."""
        for _ in range(passes):
            r = [((r[i - 1][0] + 2 * r[i][0] + r[(i + 1) % len(r)][0]) / 4,
                  (r[i - 1][1] + 2 * r[i][1] + r[(i + 1) % len(r)][1]) / 4) for i in range(len(r))]
        return r

    rings_by_s = {}

    def plate(s, y):
        if s not in rings_by_s:
            rings_by_s[s] = ring if s >= 0.999 else soften(ring, 1 if s > 0.8 else 3)
        return [Vector((x * s, y, zc + (z - zc) * s)) for x, z in rings_by_s[s]]
    arch = 0.036
    front = [(1.0, -0.10), (0.86, -0.10 - arch * (1 - 0.86 ** 2)), (0.62, -0.10 - arch * (1 - 0.62 ** 2)),
             (0.36, -0.10 - arch * (1 - 0.36 ** 2))]
    back = [(0.4, 0.108), (0.75, 0.104), (1.0, 0.10)]
    if lite:
        back, front = back[1:], front[::2]
    # back and ribs in the varnished kit wood (finer than the stalls' plank scale); the top is its
    # own loft in straight-grained spruce
    rings = [plate(s, y) for s, y in back] + [plate(*front[0])]
    wd.loft(rings, closed=True, cap_start=True, cap_end=False, smooth=True, grain=2, tint=VARN, uv_scale=0.35)
    g["spruce_top"].loft([plate(s, y) for s, y in front], closed=True, cap_start=False, cap_end=True, smooth=True)
    # purfling line and the edge overhang of the top
    if not lite:
        eb.loft([plate(1.012, -0.098), plate(1.012, -0.104)], closed=True, smooth=True)

    # the top's own surface (front rings and the flat cap inside the last one), for placing the
    # f-holes, bridge and tailpiece on it: cast a ray from in front
    from mathutils.bvhtree import BVHTree
    fr = [plate(s_, y_) for s_, y_ in front]
    tv = [v for r in fr for v in r]
    m_ = len(fr[0])
    tf = [(i * m_ + j, i * m_ + (j + 1) % m_, (i + 1) * m_ + (j + 1) % m_, (i + 1) * m_ + j)
          for i in range(len(fr) - 1) for j in range(m_)]
    tf.append(tuple((len(fr) - 1) * m_ + j for j in range(m_)))
    top_bvh = BVHTree.FromPolygons(tv, tf, all_triangles=False)

    def top_y(x, z):
        hit = top_bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        return hit[0].y if hit[0] is not None else -0.10
    # f-holes: an italic f each. The upper eye sits toward the centre line and the lower eye
    # toward the edge; the stem is an S that swells into a wing below the upper eye and above the
    # lower eye, with the two nicks cut at its waist. Each is laid on the arch of the top.
    hole = g["hole"]
    path_c = [(-0.022, 0.848), (-0.012, 0.826), (-0.002, 0.795), (0.006, 0.76), (0.011, 0.725),
              (0.014, 0.70), (0.018, 0.672), (0.024, 0.64), (0.033, 0.61), (0.042, 0.588), (0.050, 0.575)]
    path = rc.smooth_path(path_c, 1 if lite else 3)
    m = len(path)

    def wdt(i):
        t = i / (m - 1)
        wing = 0.0045 * math.exp(-((t - 0.24) / 0.1) ** 2) + 0.0055 * math.exp(-((t - 0.76) / 0.1) ** 2)
        return 0.0026 + 0.0022 * math.sin(math.pi * t) + wing
    def on_top(poly, depth=0.0012):
        """A flat f-hole piece following the top's arch: each vertex sits just in front of the top."""
        bm = rc.bmesh.new()
        vs = [bm.verts.new((x, top_y(x, z) - depth, z)) for x, z in poly]
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
        bmesh_tri(bm)
        hole.from_bmesh(bm, grain=0, smooth=False)

    for sx in (-1, 1):
        x0 = sx * 0.125
        band_l, band_r = [], []
        for i, (dx, z) in enumerate(path):
            a = path[max(i - 1, 0)]
            b = path[min(i + 1, m - 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, tz) or 1
            nx, nz = -tz / ln, tx / ln
            w = wdt(i)
            band_l.append((x0 + sx * (dx + nx * w), z + nz * w))
            band_r.append((x0 + sx * (dx - nx * w), z - nz * w))
        on_top(band_l + list(reversed(band_r)))
        seg = 8 if lite else 16
        (ux, uz), (lx, lz) = path_c[0], path_c[-1]
        # round eyes, the lower one larger (on a bass it is about 3 cm across)
        on_top(geo.circle_polygon(x0 + sx * ux, uz, 0.0115, seg), depth=0.0015)
        on_top(geo.circle_polygon(x0 + sx * lx, lz, 0.0155, seg), depth=0.0015)
        # the nicks at the waist, one each side, cut long enough to see from the stage edge
        k = m // 2
        dx, z = path[k]
        a, b = path[k - 1], path[k + 1]
        tx, tz = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, tz) or 1
        nx, nz = -tz / ln, tx / ln
        for sgn in (-1, 1):
            w = wdt(k) * 0.7
            cx, cz = x0 + sx * (dx + sgn * nx * w), z + sgn * nz * w
            tip = (x0 + sx * (dx + sgn * nx * (w + 0.013)), z + sgn * nz * (w + 0.013))
            on_top([(cx - sx * tx / ln * 0.0035, cz - tz / ln * 0.0035), tip,
                    (cx + sx * tx / ln * 0.0035, cz + tz / ln * 0.0035)], depth=0.0015)
    # neck, fingerboard, nut, pegbox, scroll, machines
    neck = [(0, 0.0, 1.20, 0.05), (0, -0.02, 1.35, 0.038), (0, -0.04, 1.55, 0.034), (0, -0.07, 1.73, 0.032)]
    pipe(wd, neck, n=6 if lite else 10, per=1 if lite else 2, cap1=True, side=(1, 0, 0), tint=(0.7, 0.42, 0.2))
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
    for i in range(22 if not lite else 7):
        t = i / (21 if not lite else 6)
        a = -math.pi / 2 + t * 3.4 * math.pi
        r = 0.055 * (1 - 0.72 * t)
        spiral.append((0, -0.08 + r * math.sin(a) * -1, 1.935 + r * math.cos(a), 0.022 * (1 - 0.45 * t)))
    spiral = [(0, -0.085, 1.905, 0.035)] + spiral
    pts = [p[:3] for p in spiral]
    sweep(wd, pts, [0.036 * (1 - 0.5 * i / len(pts)) for i in range(len(pts))], [p[3] for p in spiral],
          n=5 if lite else 8, cap0=True, cap1=True, side=(1, 0, 0), tint=(0.62, 0.36, 0.17))
    br = g["brass"]
    for sx in (-1, 1):
        br.box((sx * 0.04, -0.085, 1.81), (0.004, 0.06, 0.16))
        for z in (1.76, 1.86):
            rod(br, (sx * 0.04, -0.085, z), (sx * 0.085, -0.085, z), 0.005, seg=6)
            if not lite:
                br.sphere((sx * 0.1, -0.085, z), 0.022, seg=8, rings=5, scale=(0.4, 1, 1))
            rod(br, (sx * 0.042, -0.06, z + 0.02), (sx * 0.042, -0.035, z + 0.02), 0.012, seg=5 if lite else 8, caps=True)
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
            rod(st, p, q, r, seg=3 if lite else 5)
    # endpin
    rod(g["chrome"], (0, 0, 0.0), (0, 0, 0.16), 0.006, seg=6, caps=True)
    rod(eb, (0, 0, 0.13), (0, 0, 0.16), 0.022, seg=6 if lite else 10, caps=True)
    groups = [g]

    # the stand with the bow in its holder (static, to the player's right)
    s = Group("bassstand", None, M=Matrix.Translation((-0.66, -0.12, 0)) @ Rz(0.4))
    bm = s["blackmetal"]
    for a in (0.0, 2.3, -2.3):
        rod(bm, (0, 0, 0.12), (0.34 * math.cos(a), 0.34 * math.sin(a), 0.01), 0.012, seg=4 if lite else 6)
        if not lite:
            s["ebony"].sphere((0.34 * math.cos(a), 0.34 * math.sin(a), 0.012), 0.02, seg=6, rings=4)
    rod(bm, (0, 0, 0.08), (0, 0, 0.95), 0.015, seg=5 if lite else 8)
    # cradle and yoke with padding
    for z, w, h in ((0.3, 0.2, 0.12), (0.95, 0.1, 0.1)):
        pts = [(-w, -0.12, z + h), (-w, -0.1, z), (0, -0.04, z - 0.03), (w, -0.1, z), (w, -0.12, z + h)]
        s["leather"].tube([Vector(p) for p in pts], 0.018, tseg=4 if lite else 6, tint=(0.25, 0.25, 0.25))
        rod(bm, (0, 0, z), (0, -0.05, z - 0.02), 0.012, seg=6)
    # bow holder cup and the bow standing in it
    rod(s["leather"], (0.07, 0.02, 0.45), (0.07, 0.02, 0.60), 0.022, seg=6 if lite else 10)
    rod(bm, (0, 0, 0.55), (0.07, 0.02, 0.55), 0.008, seg=5)
    bw = s["wood"]
    bow0 = Vector((0.07, 0.02, 0.46))
    bow1 = Vector((0.08, 0.03, 1.16))
    mid = bow0.lerp(bow1, 0.5) + Vector((0.012, -0.006, 0))
    pipe(bw, [(bow0.x, bow0.y, bow0.z, 0.0055), (mid.x, mid.y, mid.z, 0.0048), (bow1.x, bow1.y, bow1.z, 0.004)],
         n=4 if lite else 6, per=1 if lite else 3, tint=(0.42, 0.14, 0.06))
    s["ebony"].box(bow0 + Vector((-0.012, 0, 0.05)), (0.016, 0.02, 0.06))
    s["canvas"].box((bow0 + bow1) / 2 + Vector((-0.017, 0, 0.01)), (0.002, 0.012, 0.64), tint=(1.1, 1.05, 0.95))
    s["ivory"].box(bow1 + Vector((-0.01, 0, 0.0)), (0.02, 0.012, 0.02))
    groups.append(s)
    return groups


# =================================================================== drums
def cymbal(part, c, R, rot, lite, tint=None):
    prof = [(0.001, 0.028), (0.018, 0.028), (0.03, 0.024), (0.05, 0.014), (0.07, 0.009),
            (R * 0.55, 0.005), (R * 0.85, 0.001), (R, -0.003)]
    if lite:
        prof = [prof[0], prof[2], prof[4], prof[6], prof[7]]
    part.lathe(prof, seg=10 if lite else 24, M=Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4(), tint=tint)


def drum(g, c, r, h, M_axis, lite, shell_tint, lugs=8, heads=(True, True)):
    """Drum with shell, two heads, hoops and lugs. M_axis turns local Z into the drum axis."""
    seg = 10 if lite else 26
    M = Matrix.Translation(c) @ M_axis
    # veneer wrapped round the shell: the grain runs round the drum, not along it like staves
    g["wood_veneer"].lathe([(r, -h / 2), (r, h / 2)], seg=seg, M=M, tint=shell_tint)
    if heads[0]:
        g["drumhead"].lathe([(0.001, h / 2 + 0.004), (r - 0.004, h / 2 + 0.004), (r + 0.002, h / 2 - 0.004)], seg=seg, M=M)
    if heads[1]:
        g["drumhead"].lathe([(r + 0.002, -h / 2 + 0.004), (r - 0.004, -h / 2 - 0.004), (0.001, -h / 2 - 0.004)], seg=seg, M=M,
                            tint=(0.9, 0.88, 0.84))
    for z in (h / 2, -h / 2):
        hoop = [(r + 0.002, z - 0.012), (r + 0.01, z - 0.008), (r + 0.01, z + 0.008), (r + 0.002, z + 0.012)]
        g["chrome"].lathe(hoop[1:3] if lite else hoop, seg=seg, M=M)
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
    g = Group("drums", wood_scale=0.3)
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


def build_sax_stand(lite):
    """The sax resting upright on its floor stand (the band on a break): instr_sax_stand, placed
    at slot_sax like instr_sax when no player holds it."""
    grp = build_sax(lite, held=False)[0]
    grp.M = Matrix.Translation((0.05, -0.35, 0.14)) @ Rz(0.5) @ Rx(-0.12)
    st = Group("saxstand", M=Matrix.Translation((0.05, -0.35, 0.0)) @ Rz(0.5))
    bm = st["blackmetal"]
    for k in range(3):
        a = TAU * k / 3 + 0.3
        rod(bm, (0, -0.07, 0.1), (0.2 * math.cos(a), -0.07 + 0.2 * math.sin(a), 0.01), 0.007, seg=4 if lite else 5)
        if not lite:
            st["ebony"].sphere((0.2 * math.cos(a), -0.07 + 0.2 * math.sin(a), 0.01), 0.012, seg=6, rings=4)
    rod(bm, (0, -0.07, 0.02), (0, -0.07, 0.62), 0.009, seg=6)
    rod(bm, (0, -0.07, 0.62), (0, 0.0, 0.64), 0.008, seg=5)
    st["leather"].tube([Vector((-0.05, -0.1, 0.16)), Vector((-0.05, -0.05, 0.08)), Vector((0.05, -0.05, 0.08)),
                        Vector((0.05, -0.1, 0.16))], 0.012, tseg=4 if lite else 5, tint=(0.3, 0.3, 0.3))
    # the padded peg the neck socket rests on
    st["leather"].sphere((0, 0.0, 0.66), 0.018, seg=8, rings=5, tint=(0.3, 0.3, 0.3))
    return [grp, st]


INSTRUMENTS = {"sax": build_sax, "piano": build_piano, "bass": build_bass, "drums": build_drums,
               "sax_stand": build_sax_stand}


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
    """Render-only: instr_sax_stand at a slot matrix (the bandstand preview without a player)."""
    return place_in("sax_stand", M_slot)


def preview_one(key):
    def pv(objs):
        f = -1 if key == "piano" else 1
        render.add_light("env_key", 'AREA', (1.2, -2.2 * f, 2.4), 90, size=1.2,
                         rot=(math.radians(55 * f), 0, math.radians(30 if f > 0 else 150)))
        render.add_light("env_warm", 'POINT', (-1.2, -1.5 * f, 1.8), 60, size=0.4)
        render.add_light("env_rim", 'AREA', (-1.0, 1.8, 2.2), 70, color=(0.6, 0.7, 1.0), size=1.5,
                         rot=(math.radians(-60), 0, math.radians(200)))
        cams = {"sax": ((1.45, -1.75, 1.40), (-0.13, -0.40, 1.14), 40),
                "sax_stand": ((1.7, -2.9, 1.2), (0.05, -0.35, 0.5), 38),
                "piano": ((1.25, 1.35, 1.55), (0.0, -0.55, 0.85), 34),
                "bass": ((-1.0, -3.3, 1.25), (-0.1, -0.3, 1.0), 34),
                "drums": ((0.9, -2.6, 1.7), (-0.05, -0.55, 0.6), 36)}
        loc, tgt, lens = cams[key]
        return render.camera(loc, tgt, lens=lens)
    return pv


if __name__ == "__main__":
    a = rc.args()
    keys = a.only.split(",") if a.only else list(INSTRUMENTS)
    for k in keys:
        rc.run(f"instr_{k}", export_build(k), preview_one(k), seed=40 + len(k), ao_full=384, ao_lite=192,
               tex_full=512, tex_lite=256, ground=12)
