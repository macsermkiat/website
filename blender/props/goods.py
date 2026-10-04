"""Reusable goods: mugs, bottles, jars, glasses, barrels, bowls, crates, sausages, rolls...

Every builder draws into a vlib.Mesh `m` in that mesh's local frame, at matrix M
(so the same mug can be a static piece or its own act_ node with its pivot at the origin).
"""
import math

from mathutils import Matrix, Vector

import vlib
from vlib import C, T, WHITE, drng, jit, lite, rng, seg

TWO_PI = 2 * math.pi

# ------------------------------------------------------------------ Glühwein mugs
MUG_STYLES = {
    # wrap region, inside / handle glaze colour
    "red": ("mug_red", "9c1a1f"), "blue": ("mug_blue", "1d3a78"), "cream": ("mug_cream", "efe4cc"),
    "green": ("mug_green", "1f4a33"), "brown": ("mug_brown", "6b3b22"), "white": ("mug_white", "f4f0e8"),
    "santa": ("mug_santa", "a3161b"), "bluestar": ("mug_bluestar", "243f7d"),
}
MUG_RIM = 0.094         # rim height of the classic mug (for steam empties)


def mug_classic(m, M, style="red", filled=False, handle_angle=0.0):
    """Classic Glühwein mug, 9.6 cm tall, handle toward local +X rotated by handle_angle."""
    M = M or Matrix()
    wrap, inside = MUG_STYLES[style]
    ic = C(inside)
    n = seg(12, 7)
    outer = [(0.029, 0.0), (0.034, 0.005), (0.036, 0.025), (0.038, 0.06), (0.0425, 0.094)]
    if lite():
        outer = [outer[0], outer[2], outer[4]]
    m.lathe(outer, n, wrap, M, WHITE, "glaze", v_by="z", u0=handle_angle + math.pi)
    # rolled rim and the inside wall, glazed in the inside colour
    rim = [(0.0425, 0.094), (0.0412, 0.0968), (0.0372, 0.093)]
    m.lathe(rim if not lite() else [rim[0], rim[2]], n, "ceramic", M, ic, "glaze")
    inner = [(0.0372, 0.093), (0.0335, 0.05), (0.029, 0.014), (0.0, 0.012)]
    m.lathe(inner if not lite() else [inner[0], inner[2], inner[3]], n, "ceramic", M, jit(ic, 0.03), "glaze")
    # unglazed foot ring and bottom
    if not lite():
        m.lathe([(0.029, 0.0), (0.0, 0.002)], n, "bisque", M, C("d8c8ae"), "atlas")
    _handle(m, M, 0.037, handle_angle, ic)
    if filled:
        r = 0.0355
        m.disc(r, n, "sw_wet", M @ T(0, 0, 0.078), C("3a0508"), "liquid")


def _handle(m, M, r, ang, col, z0=0.022, z1=0.078, reach=0.03, thick=0.0065):
    M = M or Matrix()
    pts = []
    k = seg(6, 3)
    for i in range(k + 1):
        t = i / k
        a = math.pi * t
        x = r - 0.002 + reach * math.sin(a) * (1.0 - 0.15 * t)
        z = z1 - (z1 - z0) * (0.5 - 0.5 * math.cos(a))
        pts.append(Vector((x, 0, z)))
    R = Matrix.Rotation(ang, 4, 'Z')
    m.tube([R @ p for p in pts], thick, seg(6, 4), "ceramic", M, col, "glaze")


def mug_boot(m, M, style="santa", filled=False, toe_angle=-math.pi / 2):
    """Boot-shaped mug (Glühweinstiefel): a shaft with a toe pointing along toe_angle, handle at the heel."""
    M = M or Matrix()
    wrap, inside = MUG_STYLES[style]
    ic = C(inside)
    n = seg(12, 7)
    shaft = [(0.033, 0.0), (0.035, 0.004), (0.0345, 0.05), (0.036, 0.1), (0.037, 0.106)]
    m.lathe(shaft, n, wrap, M, WHITE, "glaze", v_by="z", u0=toe_angle + math.pi)
    rim = [(0.037, 0.106), (0.0355, 0.1088), (0.0318, 0.105)]
    m.lathe(rim if not lite() else [rim[0], rim[2]], n, "ceramic", M, ic, "glaze")
    m.lathe([(0.0318, 0.105), (0.029, 0.04), (0.0, 0.016)] if not lite() else [(0.0318, 0.105), (0.0, 0.016)], n,
            "ceramic", M, jit(ic, 0.03), "glaze")
    if not lite():
        m.lathe([(0.033, 0.0), (0.0, 0.001)], n, "bisque", M, C("d8c8ae"), "atlas")
    # toe: ellipse rings along a path from inside the shaft forward, rising to a rounded cap
    base = C(inside) if style != "santa" else C("a3161b")
    ring_n = seg(8, 5)
    rings = []
    steps = [(0.0, 0.034, 0.034, 0.0), (0.03, 0.033, 0.031, 0.0), (0.05, 0.03, 0.027, 0.002),
             (0.064, 0.025, 0.022, 0.004), (0.073, 0.017, 0.016, 0.006), (0.078, 0.006, 0.007, 0.008)]
    for d, wy, hz, lift in steps:
        ring = []
        for j in range(ring_n):
            a = TWO_PI * j / ring_n
            y = wy * math.cos(a)
            z = hz * (0.5 + 0.5 * math.sin(a)) * 1.0 + lift
            ring.append(Vector((d, y, z)))
        rings.append(ring)
    Rz = Matrix.Rotation(toe_angle, 4, 'Z')
    rings = [[tuple(Rz @ p) for p in r] for r in rings]
    m.loft(rings, "ceramic", M, base, "glaze", cap1=True)
    # black sole band under the toe
    sole = [[tuple(Rz @ Vector((d, wy * 1.02 * math.cos(TWO_PI * j / ring_n), 0.004 + 0.002 * math.sin(TWO_PI * j / ring_n))))
             for j in range(ring_n)] for d, wy, hz, lift in steps[:-1]]
    if not lite():
        m.loft(sole, "sw_gloss", M, C("1a1a1a"), "glaze")
    _handle(m, M, 0.035, toe_angle + math.pi, ic if style != "santa" else C("a3161b"), z0=0.03, z1=0.09)
    if filled:
        m.disc(0.0315, n, "sw_wet", M @ T(0, 0, 0.09), C("3a0508"), "liquid")


# ------------------------------------------------------------------ bottles and jars
BOTTLE_KINDS = {
    # profile [(r, z)], label band (z0, z1), label arc (fraction of a full turn), xy scale
    "bordeaux": ([(0.0, 0.0), (0.036, 0.0), (0.0375, 0.004), (0.0375, 0.2), (0.034, 0.215), (0.02, 0.235),
                  (0.0145, 0.25), (0.0142, 0.3), (0.0155, 0.302), (0.015, 0.306)], (0.05, 0.14), 0.45, 1.0),
    "burgundy": ([(0.0, 0.0), (0.038, 0.0), (0.0395, 0.004), (0.0395, 0.12), (0.036, 0.16), (0.026, 0.205),
                  (0.016, 0.24), (0.0145, 0.292), (0.0158, 0.295), (0.015, 0.299)], (0.035, 0.115), 0.42, 1.0),
    "schlegel": ([(0.0, 0.0), (0.0385, 0.0), (0.0395, 0.004), (0.039, 0.13), (0.035, 0.17), (0.024, 0.22),
                  (0.0155, 0.27), (0.0145, 0.325), (0.0158, 0.328), (0.015, 0.333)], (0.04, 0.12), 0.42, 1.0),
    "half": ([(0.0, 0.0), (0.031, 0.0), (0.0318, 0.003), (0.0314, 0.105), (0.028, 0.137), (0.019, 0.177),
              (0.0125, 0.217), (0.0117, 0.262), (0.0128, 0.265), (0.0121, 0.269)], (0.03, 0.095), 0.42, 1.0),
    "bocksbeutel": ([(0.0, 0.0), (0.03, 0.0), (0.05, 0.008), (0.066, 0.04), (0.07, 0.075), (0.064, 0.115),
                     (0.046, 0.148), (0.021, 0.172), (0.0152, 0.182), (0.0145, 0.225), (0.0158, 0.228),
                     (0.015, 0.232)], (0.05, 0.115), 0.34, 0.62),
    "flask": ([(0.0, 0.0), (0.042, 0.0), (0.044, 0.005), (0.044, 0.15), (0.04, 0.165), (0.018, 0.19),
               (0.014, 0.23), (0.0152, 0.232), (0.0145, 0.236)], (0.035, 0.12), 0.45, 1.0),
}


def bottle(m, M, label="label_wine", glass=C("1e3a22"), kind="bordeaux", foil=C("8a1a1a"), liquid=None, n=None):
    """A bottle standing on its base (origin), label facing -Y, foil capsule over the neck."""
    M = M or Matrix()
    n = seg(n or 12, 6)
    prof, lab, arc, sy = BOTTLE_KINDS[kind]
    if sy != 1.0:
        M = M @ Matrix.Diagonal((1.0, sy, 1.0, 1.0))
    if lite():
        prof = [p for i, p in enumerate(prof) if i in (0, 1, 3, 5, len(prof) - 3, len(prof) - 1)]
    m.lathe(prof, n, "sw_vgloss", M, glass, "glass", v_by="z")
    if liquid and not lite():
        lp = [(0.0, 0.005)] + [(max(0.0, prof[i][0] - 0.0035), prof[i][1]) for i in range(1, 4)] + [(0.0, prof[3][1])]
        m.lathe(lp, n, "sw_wet", M, liquid, "liquid")
    # label band just outside the glass, centred on the front (-Y)
    def r_at(z):
        for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
            if z0 <= z <= z1 and z1 > z0:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return prof[3][0]
    zs = [lab[0], (lab[0] + lab[1]) / 2, lab[1]] if kind == "bocksbeutel" else [lab[0], lab[1]]
    band = [(r_at(z) + 0.0008, z) for z in zs]
    m.lathe(band, n, label, M, WHITE, "atlas", v_by="z", arc=TWO_PI * arc, u0=-math.pi / 2 - math.pi * arc)
    # foil capsule over the neck
    top = prof[-1][1]
    cap = [(0.0158, top - 0.05), (0.016, top - 0.004), (0.012, top + 0.001), (0.0, top + 0.002)]
    m.lathe(cap if not lite() else [cap[0], cap[1], cap[3]], seg(8, 6), "sw_metal", M, foil, "atlas")


BACK_ARC = 0.17          # a back label's width as a fraction of a full turn (round 6)


def back_label(m, w, M, kind, region, wr):
    """Round 6: a back label on the bottle's back (+Y), in the same band as the front label, as five pieces: the
    printed surround (estate on top, small print below, side margins; region from the print atlas) drawn into
    the bottle's mesh `m`, and the blank writing strip into `w` (the write_label_<n> mesh, UVs 0..1, u to the
    right as seen from behind, v up). wr = (u0, v0, u1, v1), the writing area as fractions of the label.
    Returns (centre (x, y, z) of the writing strip on its surface, chord width, height) in the bottle's frame."""
    M = M or Matrix()
    prof, lab, arc, sy = BOTTLE_KINDS[kind]
    if sy != 1.0:
        M = M @ Matrix.Diagonal((1.0, sy, 1.0, 1.0))

    def r_at(z):
        for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
            if z0 <= z <= z1 and z1 > z0:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return prof[3][0]
    z0, z1 = lab[0] + 0.004, lab[1] - 0.006
    a_tot = TWO_PI * BACK_ARC
    a0 = math.pi / 2 - a_tot / 2
    u0, v0, u1, v1 = wr
    zs = lambda va, vb, k=2: [z0 + (z1 - z0) * (va + (vb - va) * i / (k - 1)) for i in range(k)]
    curved = kind == "bocksbeutel"
    full = lambda va, vb: [(r_at(z) + 0.0008, z) for z in zs(va, vb, 3 if curved else 2)]
    reg = lambda a, b, c, d: vlib.Reg(region, sub=(a, b, c, d))
    nb = seg(10, 4)
    # bottom and top bands across the whole width, the side margins between them
    for va, vb in ((0.0, v0), (v1, 1.0)):
        m.lathe(full(va, vb), nb, reg(0, va, 1, vb), M, WHITE, "print", v_by="z", arc=a_tot, u0=a0)
    for ua, ub in ((0.0, u0), (u1, 1.0)):
        m.lathe(full(v0, v1), 1, reg(ua, v0, ub, v1), M, WHITE, "print", v_by="z", arc=a_tot * (ub - ua),
                u0=a0 + a_tot * ua)
    nw = seg(6, 3)
    w.lathe(full(v0, v1), nw, vlib.Reg(list(vprint_uv01())), M, vprint_wcol("label"), "write_label", v_by="z",
            arc=a_tot * (u1 - u0), u0=a0 + a_tot * u0, smooth=True)
    zc = (zs(v0, v1)[0] + zs(v0, v1)[1]) / 2
    rc = r_at(zc) + 0.0008
    half = a_tot * (u1 - u0) / 2
    ry = rc * sy
    return (0.0, ry, zc), 2 * rc * math.sin(half), (z1 - z0) * (v1 - v0)


def vprint_uv01():
    return [0.0, 0.0, 1.0, 1.0]


def vprint_wcol(kind):
    return C(vlib.print_meta()["write_colours"][kind])


def wine_glass(m, M, wine=None, glass_col=C("f2f6f4")):
    """A stemmed wine glass (19 cm), optionally with a pour of wine. Origin at the foot. (10 sides since round 6:
    the Glühwein stall grew; lite keeps its 6.)"""
    M = M or Matrix()
    n = seg(10, 7)
    # round 6 pass 2 (headroom): the foot meets the stem in one step and the bowl's floor is one cone (two
    # profile rows fewer, 40 triangles a glass)
    outer = [(0.0, 0.0), (0.035, 0.0015), (0.0035, 0.012), (0.0035, 0.085),
             (0.012, 0.097), (0.034, 0.122), (0.041, 0.152), (0.037, 0.19)]
    inner = [(0.0362, 0.19), (0.0398, 0.152), (0.0328, 0.123), (0.0, 0.099)]
    if lite():
        outer = [outer[i] for i in (0, 1, 2, 3, 5, 7)]
        inner = [inner[i] for i in (0, 2, 3)]
    m.lathe(outer + inner, n, "sw_vgloss", M, glass_col, "glass")
    if wine:
        lvl = 0.128
        fill = [(0.0, 0.1), (0.031, 0.121), (0.0335, lvl), (0.0, lvl)]
        m.lathe(fill if not lite() else [fill[0], fill[2], fill[3]], n, "sw_wet", M, wine, "liquid")


def jar(m, M, label, content_col, content_region="almonds", h=0.12, r=0.038, lid=C("b89a5a"), n_lo=5):
    M = M or Matrix()
    n = seg(9, n_lo)
    body = [(0.0, 0.0), (r - 0.004, 0.0), (r, 0.006), (r, h - 0.012), (r - 0.006, h - 0.004), (r - 0.006, h)]
    m.lathe(body if not lite() else [body[0], body[2], body[3], body[5]], n, "sw_vgloss", M, C("e8f0ec"), "glass")
    # contents fill most of the jar
    fh = h * drng.uniform(0.55, 0.85)
    fill = [(0.0, 0.004), (r - 0.003, 0.006), (r - 0.003, fh), (0.0, fh + 0.006)]
    m.lathe(fill if not lite() else [fill[1], fill[2], fill[3]], n, content_region, M, content_col, "atlas")
    cap = [(r - 0.004, h - 0.012), (r - 0.002, h - 0.012), (r - 0.002, h + 0.012), (r - 0.012, h + 0.015),
           (0.0, h + 0.015)]
    m.lathe(cap if not lite() else [cap[1], cap[2], cap[4]], n, "brass", M, lid, "atlas")
    m.lathe([(r + 0.0006, h * 0.35), (r + 0.0006, h * 0.62)], n, label, M, WHITE, "atlas", v_by="z",
            arc=math.pi * 0.8, u0=-math.pi / 2 - math.pi * 0.4)


# ------------------------------------------------------------------ wood: bowls, crates, trays, boards
def bowl(m, M, r=0.12, h=0.06, col=C("b08058"), region="wood", seg_n=24):
    M = M or Matrix()
    n = seg(seg_n, 10)
    prof = [(0.0, 0.0), (r * 0.55, 0.0), (r * 0.85, h * 0.35), (r, h), (r - 0.008, h + 0.002),
            (r * 0.82, h * 0.45), (r * 0.5, 0.012), (0.0, 0.01)]
    m.lathe(prof, n, vlib.RW(region), M, col, "atlas")


def crate(m, M, w, d, h, col=C("c89e70"), slats=2):
    """Open wooden crate: slatted sides, solid ends, board bottom (origin at bottom centre)."""
    M = M or Matrix()
    t = 0.012
    for side in (-1, 1):
        for k in range(slats):
            z = (k + 0.5) * h / slats
            m.box((w, t, h / slats - 0.01), M @ T(0, side * (d / 2 - t / 2), z), vlib.RW("wood"), jit(col, 0.1))
        m.box((t * 1.5, d, h), M @ T(side * (w / 2 - t * 0.75), 0, h / 2), vlib.RW("wood"), jit(col, 0.1))
    m.box((w - 0.02, d - 0.01, t), M @ T(0, 0, t / 2), vlib.RW("wood"), jit(col, 0.1))


def board(m, M, w, d, t=0.02, col=C("c89e70")):
    M = M or Matrix()
    m.box((w, d, t), M @ T(0, 0, t / 2), vlib.RW("wood"), jit(col, 0.08))


def orange(m, M, r=0.036):
    M = M or Matrix()
    m.sphere(r, seg(10, 6), seg(7, 4), "peel", M @ T(0, 0, r * 0.92), jit(WHITE, 0.08), "atlas", scale=(1, 1, 0.92))
    if not lite():
        m.cyl(0.004, 0.003, 0.006, 5, "sw_matte", M @ T(0, 0, r * 1.8), C("3a4a1a"), caps=False)


def orange_slice(m, M, r=0.03, t=0.005):
    """Dried orange slice lying flat (both faces textured)."""
    M = M or Matrix()
    n = seg(10, 6)
    m.disc(r, n, "orange_slice", M @ T(0, 0, t), WHITE, "atlas")
    m.disc(r, n, "orange_slice", M @ T(0, 0, 0, rx=math.pi), C("d9d0c0"), "atlas")
    m.lathe([(r, 0), (r, t)], n, "orange_slice", M, C("b8480f"), "atlas", u_span=0.02)


def cinnamon_stick(m, M, L=0.1, r=0.006):
    """Cinnamon quill along local X: a rolled bark tube with the rolled end visible."""
    M = M or Matrix()
    n = seg(7, 5)
    Mx = M @ T(-L / 2, 0, 0, ry=math.pi / 2)
    m.lathe([(r, 0), (r * 1.02, L * 0.5), (r, L)], n, "cinnamon", Mx, jit(WHITE, 0.1), "atlas")
    for end in (0, L):
        m.disc(r * 0.95, n, "cinnamon", Mx @ T(0, 0, end, rx=0 if end else math.pi), C("5a2e14"), "atlas")


def star_anise(m, M, r=0.016):
    M = M or Matrix()
    pts = []
    for i in range(16):
        a = math.pi * i / 8
        rr = r if i % 2 == 0 else r * 0.35
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    m.extrude(pts, 0.005, M, "cinnamon", "cinnamon", C("7a3a1a"))


def twine(m, pts, r=0.0022):
    m.tube(pts, r, 5, "burlap", None, C("c8a870"))


# ------------------------------------------------------------------ beer glasses
def willi(m, M, glass_col=C("eef4f0"), n=None, lo=7, mat="glass"):
    """0.5 l Willi-Becher, 20.5 cm: 2.5 mm walls, a rounded rim and a thick base. Returns
    (inner profile, rim z, outer rim radius)."""
    M = M or Matrix()
    n = seg(n or 12, lo)
    outer = [(0.0, 0.0), (0.029, 0.0), (0.031, 0.004), (0.031, 0.02), (0.036, 0.12), (0.038, 0.15),
             (0.0355, 0.19), (0.0365, 0.2025)]
    rim = [(0.0362, 0.2048), (0.0348, 0.2058), (0.0336, 0.2045)]
    inner = [(0.0338, 0.2025), (0.0332, 0.19), (0.0355, 0.15), (0.0335, 0.12), (0.0285, 0.026), (0.0, 0.014)]
    if lite():
        outer = [outer[i] for i in (0, 1, 3, 4, 5, 7)]
        rim = [rim[1]]
        inner = [inner[i] for i in (0, 2, 4, 5)]
    m.lathe(outer + rim + inner, n, "sw_vgloss", M, glass_col, mat)
    return inner, 0.2058, 0.0365


def weizen(m, M, glass_col=C("eef4f0"), n=None, lo=7, mat="glass"):
    """0.5 l Weizenglas, 25 cm: a narrow waist low down, a tall tulip belly, thin walls on a heavy foot.
    Returns (inner profile, rim z, outer rim radius)."""
    M = M or Matrix()
    n = seg(n or 12, lo)
    outer = [(0.0, 0.0), (0.03, 0.0), (0.032, 0.006), (0.027, 0.025), (0.024, 0.06), (0.03, 0.12), (0.038, 0.19),
             (0.0385, 0.225), (0.035, 0.248)]
    rim = [(0.0352, 0.2505), (0.0338, 0.2512), (0.0327, 0.2498)]
    inner = [(0.0329, 0.248), (0.0364, 0.225), (0.0358, 0.19), (0.0282, 0.12), (0.0218, 0.06), (0.0, 0.028)]
    if lite():
        outer = [outer[i] for i in (0, 1, 3, 4, 6, 8)]
        rim = [rim[1]]
        inner = [inner[i] for i in (0, 2, 4, 5)]
    m.lathe(outer + rim + inner, n, "sw_vgloss", M, glass_col, mat)
    return inner, 0.2512, 0.0352


def mass(m, M, glass_col=C("eef4f0"), n=None, lo=7, mat="glass"):
    """1 l Maßkrug, 21 cm: thick dimpled glass (4.5 mm walls, 2 cm base) with a handle.
    Returns (inner profile, rim z, outer rim radius)."""
    M = M or Matrix()
    n = seg(n or 12, lo)
    outer = [(0.0, 0.0), (0.05, 0.0), (0.054, 0.006), (0.054, 0.03), (0.052, 0.2), (0.053, 0.207)]
    rim = [(0.0528, 0.2095), (0.0505, 0.2108), (0.0484, 0.2095)]
    inner = [(0.0484, 0.207), (0.0475, 0.2), (0.0492, 0.036), (0.043, 0.022), (0.0, 0.02)]
    m.lathe(outer[:3], n, "sw_vgloss", M, glass_col, mat)
    m.lathe(outer[2:5], n, "dimples", M, glass_col, mat, v_by="z")
    m.lathe(outer[4:] + (rim if not lite() else [rim[1]]) + inner, n, "sw_vgloss", M, glass_col, mat)
    # handle: a thick D-shaped loop on +X
    k = seg(8, 4)
    pts = []
    for i in range(k + 1):
        a = math.pi * i / k
        pts.append((0.05 + 0.045 * math.sin(a), 0, 0.185 - 0.14 * (0.5 - 0.5 * math.cos(a))))
    m.tube(pts, 0.011, seg(7, 4), "sw_vgloss", M, glass_col, mat)
    return inner, 0.2108, 0.053


def beer_fill(m, foam_m, M, glass, level, beer_col=C("d98a1a"), region_foam="foam", spill=0.0, seed=0.0, dome=None):
    """Beer up to `level` (m) in m, and in foam_m a separate foam head: one soft, continuous skin that rises
    from the beer up the inner wall, meets the glass along a wavy line a little under the rim and swells to a
    low, uneven dome (round 6 pass 2), and, when `spill` (radians) is given, a run of foam over the rim and
    down the outside."""
    from mathutils import noise
    inner, rim_z, rim_r = glass
    n = seg(14, 7)

    def r_at(z):
        pts = sorted([(p[1], p[0]) for p in inner if p[0] > 0])
        for (z0, r0), (z1, r1) in zip(pts[:-1], pts[1:]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / ((z1 - z0) or 1)
        return pts[-1][1] if z > pts[-1][0] else pts[0][1]
    zb = min(p[1] for p in inner if p[0] > 0) + 0.002
    prof = [(0.0, zb)]
    for z in (zb + 0.004, zb + (level - zb) * 0.5, level):
        prof.append((r_at(z) - 0.0008, z))
    # (round 6 pass 2: no top cap - the foam head closes the column, its wall ring starts 2 mm under `level`)
    f0 = len(m.F)
    m.lathe(prof, seg(12, 6), "sw_wet", M, beer_col, "beer")
    # round 4: a colour gradient up the column, per corner, so the beer reads as a clear liquid lit through
    # rather than a flat painted fill: deeper amber at the foot (more beer to look through), the named colour
    # in the middle, and a brighter, paler gold just under the head where the column is thinnest and lit
    # from above. The beer is opaque in the glb (see vlib.material("beer")), so this gradient carries the depth.
    # (no white mixed into the light end: under the warm stall light and the tone mapping a whitened gold
    # turns peach, like orange juice)
    deep = tuple(c * 0.6 for c in (beer_col[0], beer_col[1] * 0.82, beer_col[2] * 0.5))
    light = (min(1.0, beer_col[0] * 1.08), min(1.0, beer_col[1] * 1.22), beer_col[2] * 0.9)
    z_lo = (M @ Vector((0, 0, zb))).z
    z_hi = (M @ Vector((0, 0, level))).z
    for fi in range(f0, len(m.F)):
        cs = []
        for vi in m.F[fi]:
            t = max(0.0, min(1.0, (m.V[vi][2] - z_lo) / ((z_hi - z_lo) or 1.0)))
            k = t * t * (3 - 2 * t)
            a, b = (deep, beer_col) if k < 0.55 else (beer_col, light)
            u = k / 0.55 if k < 0.55 else (k - 0.55) / 0.45
            cs.append(tuple(a[j] + (b[j] - a[j]) * u for j in range(3)) + (1.0,))
        m.C[fi] = cs
    ri = r_at(rim_z - 0.003)
    cream = C("f3e6c8")
    reg = vlib.R(region_foam)
    # the foam region holds two textures (atlas_goods.g_foam): a wet edge strip along its bottom quarter
    # (v 0..0.25, used by the spill) and the dry head seen from above in the square over it (u, v 0.25..1)
    edge = lambda u, v: reg.uv(u, 0.02 + 0.21 * v)
    ext = rim_r * 1.15
    head_uv = lambda x, y: reg.uv(0.25 + 0.75 * (0.5 + x / (2 * ext)), 0.25 + 0.75 * (0.5 + y / (2 * ext)))
    # round 6 pass 2 (judges: "a hard cap with a band"): the head is now ONE soft, continuous skin. It rises from
    # the beer up the inner wall, meets the glass a little under the rim along a wavy line (higher where the
    # pour left it, lower where it has settled), rolls over a soft shoulder and swells to a low, uneven dome
    # whose top is pushed off centre. Nothing sits on or over the rim, there is no second "crown" mesh and no
    # texture or colour seam at the rim: one bubble texture, and a colour that runs from a beer-tinted cream
    # where the head meets the beer to pale cream on top. Every glass gets its own edge line, dome and lean.
    vr = 0.5 + 0.5 * noise.noise(Vector((seed * 0.37, 4.1, 0.0)))          # 0..1 per glass
    dome = dome if dome is not None else min(0.0095, rim_r * 0.17)
    dome *= 0.75 + 0.5 * vr
    lean = Vector((math.cos(seed * 2.3), math.sin(seed * 2.3))) * ri * 0.18 * (0.4 + vr)
    # the head's rings use the glass's own sides, vertex for vertex (mass/willi/weizen: seg(12, 7)), so its edge
    # follows the inner wall exactly; a 14-gon in a 12-sided glass left dark slits between them (the dashed
    # line round the rim in round 6 pass 1)
    n = seg(12, 7)
    wall_lo = level - 0.002
    # (kind, radius, base height, lump weight): "w" rings hug the wall at an absolute height, "d" rings are
    # the dome (height = fraction of the dome over the edge line)
    rings = [("w", r_at(level) - 0.0006, wall_lo, 0.0),
             ("e", ri - 0.0004, 0.0, 1.0),                  # the edge line against the glass, under the rim
             ("d", ri * 0.93, 0.30, 0.8), ("d", ri * 0.74, 0.62, 1.0), ("d", ri * 0.48, 0.86, 1.0),
             ("d", ri * 0.22, 0.97, 0.7)]
    keep = [0, 1, 2, 4] if lite() else list(range(len(rings)))
    light = (min(1.0, beer_col[0] * 1.08), min(1.0, beer_col[1] * 1.22), beer_col[2] * 0.9)
    lowc = tuple(0.5 * light[k] + 0.5 * cream[k] for k in range(3))        # where the head meets the beer
    top_c = C("f8eedb")
    verts, vcol = [], []

    def edge_z(a):
        # the line where the head meets the glass: 1-3.5 mm under the rim, wandering slowly round the glass,
        # pulled up to the lip where the spill runs over
        w = noise.noise(Vector((math.cos(a) * 0.9, math.sin(a) * 0.9, seed * 0.61 + 7.0)))
        w2 = noise.noise(Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, seed * 0.61 + 3.0)))
        z = rim_z - 0.0022 + 0.0012 * w + 0.0005 * w2
        if spill:
            d = abs(math.atan2(math.sin(a - spill), math.cos(a - spill)))
            z = max(z, rim_z + 0.0006 - 0.002 * d)
        return min(z, rim_z + 0.0006)
    for orig in keep:
        kind, rr, hz, lw = rings[orig]
        for j in range(n):
            a = TWO_PI * j / n
            p = Vector((math.cos(a) * 2.0, math.sin(a) * 2.0, seed + orig * 0.47))
            soft = noise.noise(p) * 0.65 + noise.noise(p * 2.6 + Vector((seed, 0, 0))) * 0.35     # broad, soft lumps
            ez = edge_z(a)
            if kind == "w":
                z, r = hz + (ez - rim_z) * 0.15 * lw, rr
            elif kind == "e":
                z, r = ez, rr
            else:
                z = ez + (rim_z + dome - ez) * hz + (0.0028 * soft) * lw
                r = rr * (1.0 + 0.06 * soft * lw)
            off = lean * (hz if kind == "d" else 0.0)
            verts.append((r * math.cos(a) + off.x, r * math.sin(a) + off.y, z))
            t = {"w": 0.0, "e": 0.85}.get(kind, 1.0)
            vcol.append(tuple(lowc[k] + (top_c[k] - lowc[k]) * t for k in range(3)))
    top = len(verts)
    verts.append((lean.x, lean.y, rim_z + dome + 0.0008 * noise.noise(Vector((seed, 1.3, 0.2)))))
    vcol.append(top_c)
    R_ = len(keep)
    faces, uvs = [], []
    # the wall rings take the head texture spread round the glass (fine bubbles against the glass); the
    # rest is planar-mapped from above, so the bubbles keep one size over the whole skin
    wall_uv = lambda j, z: reg.uv(0.25 + 0.75 * (j / n), 0.25 + 0.75 * min(1.0, max(0.0, (z - wall_lo) / 0.06)))
    for i in range(R_ - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            f = (a, b, b + n, a + n)
            faces.append(f)
            if rings[keep[i]][0] == "w":
                uvs.append([wall_uv(j, verts[a][2]), wall_uv(j + 1, verts[b][2]), wall_uv(j + 1, verts[b + n][2]),
                            wall_uv(j, verts[a + n][2])])
            else:
                uvs.append([head_uv(verts[k][0], verts[k][1]) for k in f])
    for j in range(n):
        f = ((R_ - 1) * n + j, (R_ - 1) * n + (j + 1) % n, top)
        faces.append(f)
        uvs.append([head_uv(verts[k][0], verts[k][1]) for k in f])
    f0 = len(foam_m.F)
    foam_m.add(verts, faces, uvs, M, cream, "foam", True)
    jj = jit((1.0, 1.0, 1.0), 0.02)
    for fi, f in zip(range(f0, len(foam_m.F)), faces):
        foam_m.C[fi] = [tuple(vcol[k][c] * jj[c] for c in range(3)) + (1.0,) for k in f]
    if spill:
        # round 3: a thin, flat run of foam that hugs the outside of the glass (1 mm off the wall), widest at the
        # lip and tapering to nothing about 3.5 cm down, with a soft wavy edge; it starts over the rim from the
        # crown. (Round 2's round tube with a bead stood off the glass like a peg.) Lite: fewer rows, same reach.
        wall = rim_r - ri
        rows = 7 if not lite() else 3
        cols_n = 4 if not lite() else 2
        drop, w0 = 0.03, 0.012                         # length down the glass and width at the lip (m)
        sv, sf, su = [], [], []
        for k in range(rows + 1):
            t = k / rows
            z = rim_z + 0.0015 - (drop + 0.0015) * t
            ro = (r_at(min(z, rim_z)) + wall if z < rim_z else rim_r) + 0.001 + 0.002 * (1 - t) ** 3
            half = 0.5 * w0 * (1 - t) ** 1.4 + 0.0003
            wob = 0.0015 * math.sin(t * 7.0 + seed) * (1 - t)
            for j in range(cols_n + 1):
                u = j / cols_n - 0.5
                a = spill + (2 * u * half + wob) / ro
                # the middle of the run stands a hair proud of its edges (a soft, rounded sheet)
                rr = ro + 0.0009 * (1 - (2 * u) ** 2) * (1 - t)
                sv.append((rr * math.cos(a), rr * math.sin(a), z))
        for k in range(rows):
            for j in range(cols_n):
                a0 = k * (cols_n + 1) + j
                sf.append((a0, a0 + 1, a0 + cols_n + 2, a0 + cols_n + 1))
                su.append([edge(j / cols_n, 1 - k / rows), edge((j + 1) / cols_n, 1 - k / rows),
                           edge((j + 1) / cols_n, 1 - (k + 1) / rows), edge(j / cols_n, 1 - (k + 1) / rows)])
        # flip so the faces point away from the glass
        sf = [tuple(reversed(f)) for f in sf]
        su = [list(reversed(u)) for u in su]
        foam_m.add(sv, sf, su, M, jit(cream, 0.015), "foam", True)


# ------------------------------------------------------------------ barrels
def barrel(m, M, L=0.36, r_end=0.12, r_belly=0.14, staves=16, lying=True, hoop_col=C("3a3c40"), tap=True):
    """Small oak cask lying along local X (origin at the bottom of the belly). Separate oak staves with a
    hairline gap, each bent across its width (two facets) so the silhouette stays round; forged iron hoops
    (dark, slightly specular metal) with a raised edge; a branded front head (+X end) and a brass tap low
    on that head, clear of the brand."""
    M = M or Matrix()
    n = seg(staves, 8)
    across = 2 if not lite() else 1
    k = seg(6, 4)
    prof = []
    for i in range(k + 1):
        t = i / k
        z = -L / 2 + L * t
        r = r_end + (r_belly - r_end) * math.sin(math.pi * t)
        prof.append((r, z))
    Mb = M @ T(0, 0, r_belly, ry=math.pi / 2) if lying else M @ T(0, 0, L / 2)
    stave = vlib.RW("stave")
    sw = TWO_PI * r_belly / n
    for j in range(n):
        a0 = TWO_PI * j / n
        m.lathe(prof, across, stave.window(sw, L), Mb, jit(C("c8b4a0"), 0.12), "atlas", smooth=True,
                arc=TWO_PI / n * 0.975, u0=a0)
    hn = n * across
    hoops = (-L / 2 + 0.03, -L / 2 + 0.075, L / 2 - 0.075, L / 2 - 0.03) if not lite() else (-L / 2 + 0.04, L / 2 - 0.04)
    for z in hoops:
        t = (z + L / 2) / L
        r = r_end + (r_belly - r_end) * math.sin(math.pi * t) + 0.0022
        hp = [(r - 0.0022, z - 0.011), (r + 0.0008, z - 0.002), (r - 0.0022, z + 0.011)]
        # blackened forged iron: a cool charcoal with a satin sheen (a metallic finish only mirrors the warm
        # wood around it and reads as another brown band)
        m.lathe(hp, hn, "sw_metal_rough", Mb, hoop_col, "atlas")
    for z in (-L / 2 + 0.012, L / 2 - 0.012):
        front = z > 0
        m.disc(r_end - 0.004, hn, "barrel_head" if front else "wood_end", Mb @ T(0, 0, z, rx=0 if front else math.pi,
               rz=math.pi / 2), C("c4b0a0") if front else C("a08060"), "atlas")
        # stave ends protrude a little beyond the heads (the chime)
        m.lathe([(r_end - 0.006, z), (r_end, z + (0.012 if front else -0.012))], hn, stave, Mb, C("9a8a78"))
    if tap:
        # low on the head (local +X of Mb is down): a short brass body, the spout down, a key on top
        tz, tx = L / 2 + 0.001, r_end * 0.7
        m.cyl(0.011, 0.0105, 0.026, seg(10, 6), "brass", Mb @ T(tx, 0, tz), WHITE)
        m.cyl(0.0075, 0.0065, 0.024, seg(8, 6), "brass", Mb @ T(tx, 0, tz + 0.02, ry=math.pi / 2), WHITE)
        m.box((0.022, 0.006, 0.009), Mb @ T(tx - 0.014, 0, tz + 0.02), "brass", WHITE)


# ------------------------------------------------------------------ sausages and bread
def sausage(m, M, L=0.2, r=0.013, bend=0.02, dark=False, seed=0.0, raw=False, cut=False):
    """Bratwurst along local X centred on the origin, gently curved in XY, slightly irregular in
    girth. Its skin region runs once around (u) and once along (v), see atlas_goods.g_sausage.
    raw=True: an uncooked one, raw-pork pink-beige satin skin, no browning or grate marks.
    cut=True: a short Currywurst slice, a straight drum with flat cut faces (round 6 pass 2: the slices
    were whole 12-segment sausages squeezed to 2.4 cm, 256 triangles each; now 36)."""
    from mathutils import noise
    M = M or Matrix()
    k = 1 if cut else seg(12, 5)
    ring_n = seg(10, 5)
    rings = []
    for i in range(k + 1):
        t = i / k
        x = -L / 2 + L * t
        y = bend * (1 - (2 * t - 1) ** 2)
        tip = 1.0 if cut else min(1.0, math.sin(math.pi * t) * 3.2) ** 0.7
        lumpy = 1.0 + 0.05 * noise.noise(Vector((t * 6.0, seed, 0.3)))
        rr = max(0.003, r * tip * lumpy)
        rings.append([(x, y + rr * math.cos(TWO_PI * j / ring_n), rr * math.sin(TWO_PI * j / ring_n))
                      for j in range(ring_n)])
    if raw:
        # raw pork pink-beige, greyed (round 2: #dcc4b0 read as white Weißwurst; round 3: #c99c8e as a hot dog)
        m.loft(rings, "sw_satin", M, jit(C("c89d90"), 0.035), "atlas", cap0=True, cap1=True)
        return
    m.loft(rings, "sausage_dark" if dark else "sausage", M, jit(WHITE, 0.05), "atlas", cap0=True, cap1=True)


def roll(m, M, L=0.12, W=0.07, H=0.045):
    """Brötchen: a squashed ellipsoid, top planar-mapped to the roll texture. Round 6 pass 2: four rings
    from the foot to the crown (was six, 156 -> 108 triangles; the outline from above keeps its 12 sides)."""
    M = M or Matrix()
    n, rings = seg(12, 8), seg(4, 3)
    verts, faces, uvs = [], [], []
    reg = vlib.R("roll")
    prof = []
    for i in range(rings + 1):
        a = -math.pi / 2 * 0.25 + (math.pi / 2 * 1.25) * i / rings
        prof.append((math.cos(a), math.sin(a)))
    for i, (c, s) in enumerate(prof):
        for j in range(n):
            a = TWO_PI * j / n
            x, y, z = L / 2 * c * math.cos(a), W / 2 * c * math.sin(a), H * max(0.0, s) ** 0.75 + 0.004 * s
            verts.append((x, y, max(0.0, z)))
    for i in range(rings):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c2, d = (i + 1) * n + (j + 1) % n, (i + 1) * n + j
            faces.append((a, b, c2, d))
    top = len(verts)
    verts.append((0, 0, H + 0.001))
    for j in range(n):
        faces.append((rings * n + j, rings * n + (j + 1) % n, top))
    for f in faces:
        uvs.append([reg.uv(0.5 + verts[i][0] / L, 0.5 + verts[i][1] / W) for i in f])
    m.add(verts, faces, uvs, M, jit(WHITE, 0.06), "atlas", True)


def paper_tray(m, M, L=0.2, W=0.1, H=0.03, col=C("f3efe6")):
    """Pappschale: a shallow boat-shaped cardboard tray with a rolled, slightly darker rim."""
    M = M or Matrix()
    n = seg(16, 8)
    rings = []
    for z, s in ((0.0, 0.8), (H, 1.0), (H - 0.001, 0.955), (0.004, 0.76)):
        rings.append([(L / 2 * s * math.cos(TWO_PI * j / n), W / 2 * s * math.sin(TWO_PI * j / n), z) for j in range(n)])
    m.loft(rings, vlib.RW("paper"), M, jit(col, 0.03), "atlas", cap1=True, smooth=False)
    m.disc(1.0, n, "paper", M @ T(0, 0, 0.0005, rx=math.pi) @ Matrix.Diagonal((L / 2 * 0.8, W / 2 * 0.8, 1, 1)),
           C("d8d0c0"), "atlas")
    if not lite():
        rim = [(L / 2 * 0.985 * math.cos(TWO_PI * j / n), W / 2 * 0.985 * math.sin(TWO_PI * j / n), H + 0.0005)
               for j in range(n + 1)]
        m.tube(rim, 0.0022, 3, "paper", M, C("cfc3aa"))


def spline(ctrl, n_per=4):
    """Catmull-Rom through control points -> list of points (tuples)."""
    P = [Vector(c) for c in ctrl]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            v = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(tuple(v))
    out.append(tuple(P[-1]))
    return out
