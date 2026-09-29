"""Reusable goods: mugs, bottles, jars, glasses, barrels, bowls, crates, sausages, rolls...

Every builder draws into a vlib.Mesh `m` in that mesh's local frame, at matrix M
(so the same mug can be a static piece or its own act_ node with its pivot at the origin).
"""
import math

from mathutils import Matrix, Vector

import vlib
from vlib import C, T, WHITE, jit, rng, seg

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
    n = seg(14, 8)
    outer = [(0.029, 0.0), (0.033, 0.002), (0.035, 0.008), (0.036, 0.025), (0.038, 0.06), (0.041, 0.088),
             (0.0425, 0.094)]
    m.lathe(outer, n, wrap, M, WHITE, "glaze", v_by="z", u0=handle_angle + math.pi)
    # rolled rim and the inside wall, glazed in the inside colour
    rim = [(0.0425, 0.094), (0.0418, 0.0968), (0.039, 0.0965), (0.0372, 0.093)]
    m.lathe(rim, n, "ceramic", M, ic, "glaze")
    inner = [(0.0372, 0.093), (0.035, 0.07), (0.032, 0.03), (0.029, 0.014), (0.0, 0.012)]
    m.lathe(inner, n, "ceramic", M, jit(ic, 0.03), "glaze")
    # unglazed foot ring and bottom
    m.lathe([(0.029, 0.0), (0.022, 0.0), (0.0, 0.002)], n, "bisque", M, C("d8c8ae"), "atlas")
    _handle(m, M, 0.037, handle_angle, ic)
    if filled:
        r = 0.0355
        m.disc(r, n, "sw_wet", M @ T(0, 0, 0.078), C("3a0508"), "liquid")


def _handle(m, M, r, ang, col, z0=0.022, z1=0.078, reach=0.03, thick=0.0065):
    M = M or Matrix()
    pts = []
    k = seg(7, 5)
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
    n = seg(14, 8)
    shaft = [(0.033, 0.0), (0.035, 0.004), (0.0345, 0.03), (0.034, 0.07), (0.036, 0.1), (0.037, 0.106)]
    m.lathe(shaft, n, wrap, M, WHITE, "glaze", v_by="z", u0=toe_angle + math.pi)
    m.lathe([(0.037, 0.106), (0.0362, 0.1088), (0.0335, 0.1085), (0.0318, 0.105)], n, "ceramic", M, ic, "glaze")
    m.lathe([(0.0318, 0.105), (0.03, 0.06), (0.028, 0.02), (0.0, 0.016)], n, "ceramic", M, jit(ic, 0.03), "glaze")
    m.lathe([(0.033, 0.0), (0.0, 0.001)], n, "bisque", M, C("d8c8ae"), "atlas")
    # toe: ellipse rings along a path from inside the shaft forward, rising to a rounded cap
    base = C(inside) if style != "santa" else C("a3161b")
    ring_n = seg(10, 6)
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
    m.loft(sole, "sw_gloss", M, C("1a1a1a"), "glaze")
    _handle(m, M, 0.035, toe_angle + math.pi, ic if style != "santa" else C("a3161b"), z0=0.03, z1=0.09)
    if filled:
        m.disc(0.0315, n, "sw_wet", M @ T(0, 0, 0.09), C("3a0508"), "liquid")


# ------------------------------------------------------------------ bottles and jars
def bottle(m, M, label="label_wine", glass=C("1e3a22"), kind="bordeaux", foil=C("8a1a1a"), liquid=None):
    M = M or Matrix()
    n = seg(16, 8)
    if kind == "bordeaux":
        prof = [(0.0, 0.0), (0.036, 0.0), (0.0375, 0.004), (0.0375, 0.2), (0.034, 0.215), (0.02, 0.235),
                (0.0145, 0.25), (0.0142, 0.3), (0.0155, 0.302), (0.015, 0.306)]
        lab = (0.05, 0.14)
    elif kind == "schlegel":
        prof = [(0.0, 0.0), (0.0385, 0.0), (0.0395, 0.004), (0.039, 0.13), (0.035, 0.17), (0.024, 0.22),
                (0.0155, 0.27), (0.0145, 0.325), (0.0158, 0.328), (0.015, 0.333)]
        lab = (0.04, 0.11)
    else:   # flask for spirits: shorter, wider
        prof = [(0.0, 0.0), (0.042, 0.0), (0.044, 0.005), (0.044, 0.15), (0.04, 0.165), (0.018, 0.19),
                (0.014, 0.23), (0.0152, 0.232), (0.0145, 0.236)]
        lab = (0.035, 0.12)
    m.lathe(prof, n, "sw_vgloss", M, glass, "glass", v_by="z")
    if liquid:
        lp = [(0.0, 0.005)] + [(max(0.0, prof[i][0] - 0.0035), prof[i][1]) for i in range(1, 4)] + [(0.0, prof[3][1])]
        m.lathe(lp, n, "sw_wet", M, liquid, "liquid")
    # label band just outside the glass, facing -Y (u centred on the front)
    r = prof[3][0] + 0.0008
    m.lathe([(r, lab[0]), (r, lab[1])], n, label, M, WHITE, "atlas", v_by="z", arc=math.pi * 0.9,
            u0=-math.pi / 2 - math.pi * 0.45)
    # foil capsule over the neck
    top = prof[-1][1]
    m.lathe([(0.0158, top - 0.05), (0.016, top - 0.004), (0.012, top + 0.001), (0.0, top + 0.002)], n, "sw_metal",
            M, foil, "atlas")


def jar(m, M, label, content_col, content_region="almonds", h=0.12, r=0.038, lid=C("b89a5a")):
    M = M or Matrix()
    n = seg(12, 8)
    m.lathe([(0.0, 0.0), (r - 0.004, 0.0), (r, 0.006), (r, h - 0.012), (r - 0.006, h - 0.004), (r - 0.006, h)],
            n, "sw_vgloss", M, C("e8f0ec"), "glass")
    # contents fill most of the jar
    fh = h * rng.uniform(0.55, 0.85)
    m.lathe([(0.0, 0.004), (r - 0.003, 0.006), (r - 0.003, fh), (0.0, fh + 0.006)], n, content_region, M,
            content_col, "atlas")
    m.lathe([(r - 0.004, h - 0.012), (r - 0.002, h - 0.012), (r - 0.002, h + 0.012), (r - 0.012, h + 0.015),
             (0.0, h + 0.015)], n, "brass", M, lid, "atlas")
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
    m.sphere(r, seg(12, 8), seg(8, 5), "peel", M @ T(0, 0, r * 0.92), jit(WHITE, 0.08), "atlas", scale=(1, 1, 0.92))
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
def willi(m, M, glass_col=C("eef4f0")):
    """0.5 l Willi-Becher: glass shell (outer + inner wall), 20.5 cm."""
    M = M or Matrix()
    n = seg(16, 8)
    outer = [(0.0, 0.0), (0.03, 0.0), (0.032, 0.004), (0.031, 0.02), (0.036, 0.12), (0.038, 0.15),
             (0.0355, 0.19), (0.0365, 0.205)]
    inner = [(0.0345, 0.205), (0.0338, 0.19), (0.0358, 0.15), (0.034, 0.12), (0.029, 0.02), (0.0, 0.014)]
    m.lathe(outer + inner, n, "sw_vgloss", M, glass_col, "glass")
    return inner


def mass(m, M, glass_col=C("eef4f0")):
    """1 l Maßkrug: thick dimpled glass with a handle, 21 cm. Returns inner profile."""
    M = M or Matrix()
    n = seg(16, 8)
    outer = [(0.0, 0.0), (0.05, 0.0), (0.054, 0.006), (0.054, 0.03), (0.052, 0.2), (0.053, 0.21)]
    inner = [(0.047, 0.21), (0.046, 0.2), (0.047, 0.035), (0.042, 0.022), (0.0, 0.02)]
    m.lathe(outer[:3], n, "sw_vgloss", M, glass_col, "glass")
    m.lathe(outer[2:5], n, "dimples", M, glass_col, "glass", v_by="z")
    m.lathe(outer[4:] + inner, n, "sw_vgloss", M, glass_col, "glass")
    # handle: a thick D-shaped loop on +X
    k = seg(10, 6)
    pts = []
    for i in range(k + 1):
        a = math.pi * i / k
        pts.append((0.05 + 0.045 * math.sin(a), 0, 0.185 - 0.14 * (0.5 - 0.5 * math.cos(a))))
    m.tube(pts, 0.011, seg(8, 5), "sw_vgloss", M, glass_col, "glass")
    return inner


def beer_fill(m, foam_m, M, inner, level, foam_h=0.03, beer_col=C("d98a1a"), region_foam="foam"):
    """Liquid inside a glass up to `level` (m) plus a separate foam head mesh (foam_m) above it."""
    n = seg(16, 8)
    def r_at(z):
        pts = sorted([(p[1], p[0]) for p in inner if p[0] > 0])
        for (z0, r0), (z1, r1) in zip(pts[:-1], pts[1:]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / ((z1 - z0) or 1)
        return pts[-1][1] if z > pts[-1][0] else pts[0][1]
    zb = min(p[1] for p in inner if p[0] > 0) + 0.002
    prof = [(0.0, zb)]
    for z in (zb + 0.004, zb + (level - zb) * 0.4, level):
        prof.append((r_at(z) - 0.0012, z))
    prof.append((0.0, level))
    m.lathe(prof, n, "sw_wet", M, beer_col, "beer")
    # foam: a slightly domed cap that bulges over the rim edge a little
    top = level + foam_h
    fr = r_at(level) - 0.0008
    fp = [(fr, level - 0.002), (r_at(top) - 0.0006, top - 0.004), (r_at(top) * 0.8, top + 0.004), (0.0, top + 0.006)]
    foam_m.lathe(fp, n, region_foam, M, WHITE, "atlas", v_by="z")


# ------------------------------------------------------------------ barrels
def barrel(m, M, L=0.36, r_end=0.12, r_belly=0.14, staves=16, lying=True, hoop_col=C("2a2826"), tap=True):
    """Small oak cask lying along local X (origin at the bottom of the belly)."""
    M = M or Matrix()
    n = seg(staves, 10)
    k = seg(8, 5)
    prof = []
    for i in range(k + 1):
        t = i / k
        z = -L / 2 + L * t
        r = r_end + (r_belly - r_end) * math.sin(math.pi * t)
        prof.append((r, z))
    Mb = M @ T(0, 0, r_belly, ry=math.pi / 2) if lying else M @ T(0, 0, L / 2)
    # staves: lathe with flat segments (smooth off) and per-stave tint variation
    wood = vlib.RW("wood")
    for j in range(n):
        a0 = TWO_PI * j / n
        m.lathe(prof, 1, wood.window(L, 0.07), Mb, jit(C("a07448"), 0.12), "atlas", smooth=True,
                arc=TWO_PI / n * 0.985, u0=a0)
    for z in (-L / 2 + 0.035, -L / 2 + 0.085, L / 2 - 0.085, L / 2 - 0.035):
        t = (z + L / 2) / L
        r = r_end + (r_belly - r_end) * math.sin(math.pi * t) + 0.003
        m.lathe([(r, z - 0.012), (r + 0.001, z), (r, z + 0.012)], n * 2, "iron", Mb, hoop_col, "atlas")
    for z in (-L / 2 + 0.012, L / 2 - 0.012):
        m.disc(r_end - 0.004, n, "wood_end", Mb @ T(0, 0, z, rx=0 if z > 0 else math.pi), C("b89068"), "atlas")
        # stave ends protrude a little beyond the heads (the chime)
        m.lathe([(r_end - 0.006, z), (r_end, z + (0.012 if z > 0 else -0.012))], n, vlib.RW("wood"), Mb, C("8a6240"))
    if tap:
        tz = L / 2 + 0.002
        m.cyl(0.012, 0.011, 0.04, 10, "brass", Mb @ T(0, -r_end * 0.55, tz), WHITE)
        m.cyl(0.008, 0.008, 0.035, 8, "brass", Mb @ T(0, -r_end * 0.55, tz + 0.03, rx=math.pi / 2), WHITE)
        m.box((0.012, 0.012, 0.035), Mb @ T(0, -r_end * 0.55, tz + 0.05), "brass", WHITE)


# ------------------------------------------------------------------ sausages and bread
def sausage(m, M, L=0.2, r=0.013, bend=0.02, dark=False):
    """Bratwurst along local X centred on the origin, gently curved in XY."""
    M = M or Matrix()
    k = seg(10, 6)
    ring_n = seg(10, 6)
    rings = []
    for i in range(k + 1):
        t = i / k
        x = -L / 2 + L * t
        y = bend * (1 - (2 * t - 1) ** 2)
        tip = min(1.0, math.sin(math.pi * t) * 3.2) ** 0.7
        rr = max(0.003, r * tip)
        rings.append([(x, y + rr * math.cos(TWO_PI * j / ring_n), rr * math.sin(TWO_PI * j / ring_n))
                      for j in range(ring_n)])
    m.loft(rings, "sausage_dark" if dark else "sausage", M, jit(WHITE, 0.05), "atlas", cap0=True, cap1=True)


def roll(m, M, L=0.12, W=0.07, H=0.045):
    """Brötchen: a squashed ellipsoid, top planar-mapped to the roll texture."""
    M = M or Matrix()
    n, rings = seg(14, 8), seg(8, 5)
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


def paper_tray(m, M, L=0.2, W=0.1, H=0.03):
    """Pappschale: a shallow boat-shaped cardboard tray."""
    M = M or Matrix()
    n = seg(16, 8)
    rings = []
    for z, s in ((0.0, 0.8), (H, 1.0), (H + 0.001, 0.97), (0.004, 0.77)):
        rings.append([(L / 2 * s * math.cos(TWO_PI * j / n), W / 2 * s * math.sin(TWO_PI * j / n), z) for j in range(n)])
    m.loft(rings, vlib.RW("paper"), M, jit(WHITE, 0.03), "atlas", cap1=True, smooth=False)
    m.disc(1.0, n, "paper", M @ T(0, 0, 0.0005) @ Matrix.Diagonal((L / 2 * 0.8, W / 2 * 0.8, 1, 1)),
           C("f0ece2"), "atlas")


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
