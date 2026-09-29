"""Goods for the nine deco stalls. Every set goes on slot_counter of its deco stall.

Deco counters are 0.48 m deep at 1.05 m (y -0.237..0.243 from slot_counter); the front opening runs from
1.05 to 2.2 m. Goods keep inside that depth (check_props' seat check). Each deco stall plus its goods must
stay under 20k triangles, so the goods of the two biggest stalls (Spielzeug, Schmuck) are held near 3k. Sets that hang goods
(Lebkuchen hearts, dipped candles, baubles, straw stars) carry their own thin rod at z = +1.08 above the
counter, just under the stall's front header (relative y = -0.03).
"""
import math

import bmesh  # noqa: F401
from mathutils import Matrix, Vector

import goods as G
import vlib
from set_wurst import lump
from vlib import C, T, WHITE, drng, jit, rng, seg

TWO_PI = 2 * math.pi
ROD_Z, ROD_Y = 1.08, -0.03


def heart_poly(s, n=18):
    pts = []
    for i in range(n):
        a = TWO_PI * i / n
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((x * s / 32, y * s / 32))
    return pts[::-1] if _area(pts) < 0 else pts


def _area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def star_poly(r1, r2, n=5, rot=math.pi / 2):
    return [((r1 if i % 2 == 0 else r2) * math.cos(rot + math.pi * i / n),
             (r1 if i % 2 == 0 else r2) * math.sin(rot + math.pi * i / n)) for i in range(2 * n)]


def rod(m, x0, x1, col=C("6a4a2c")):
    m.cyl(0.008, 0.008, x1 - x0, 10, vlib.RW("wood"), T(x0, ROD_Y, ROD_Z, ry=math.pi / 2), col)
    for x in (x0 + 0.05, x1 - 0.05):
        m.box((0.02, 0.02, 0.07), T(x, ROD_Y, ROD_Z + 0.035), vlib.RW("wood"), col)


def hang(m, x, drop, col=C("b0282a"), r=0.0018):
    """A ribbon / string from the rod down `drop` metres, returns the attach point."""
    top = (x, ROD_Y, ROD_Z - 0.008)
    bot = (x + rng.uniform(-0.004, 0.004), ROD_Y, ROD_Z - drop)
    m.tube([top, bot], r, 4 if not vlib.lite() else 3, "sw_satin", None, col)
    if not vlib.lite():
        m.box((0.008, 0.02, 0.006), T(x, ROD_Y, ROD_Z + 0.006), "sw_satin", col, skip=("nz",))   # knot over the rod
    return Vector(bot)


# ------------------------------------------------------------------ Lebkuchen
def lebkuchen_heart(m, M, size, k):
    poly = heart_poly(size, 18 if size >= 0.14 and not vlib.lite() else 12)
    reg = f"lebkuchen_{k % 6}"
    dough = vlib.R(reg, sub=(0.0, 0.0, 0.08, 0.08))
    # heart polygon spans x +-size/2, y from -size*0.53 to +size*0.36 roughly; face UVs by bbox
    m.extrude(poly, 0.012, M, reg, dough, WHITE, "glaze", bevel=0.0 if (vlib.lite() or size < 0.17) else 0.003,
              back_region=dough)


def lebkuchen():
    s = vlib.PropSet("prop_deco_lebkuchen", "slot_counter", "deco-lebkuchen")
    m = s.static
    rod(m, -1.1, 1.1)
    ribbons = [C("b0282a"), C("2a5aa8"), C("2a7a3a"), C("d8b048")]
    xs = [-0.98, -0.8, -0.62, -0.46, -0.3, 0.3, 0.46, 0.62, 0.8, 0.98]
    for i, x in enumerate(xs):
        size = rng.choice([0.14, 0.17, 0.2, 0.24]) if abs(x) > 0.5 else rng.choice([0.12, 0.15])
        drop = rng.uniform(0.18, 0.42)
        p = hang(m, x, drop, ribbons[i % 4])
        # heart hangs facing the front (-Y): its local XY plane -> world XZ, face toward -Y
        M = T(p.x, p.y + 0.006, p.z - size * 0.36 + 0.01, rx=math.pi / 2, ry=rng.uniform(-0.2, 0.2)) @ T(0, 0, -0.006)
        lebkuchen_heart(m, M @ T(0, 0, 0, rz=0), size, i)
    # on the counter: a basket of small hearts, round Elisenlebkuchen on paper, Pfeffernüsse
    G.crate(m, T(-0.6, 0.02, 0), 0.4, 0.3, 0.07, C("b48c5c"))
    for k in range(6 if not vlib.lite() else 3):
        size = 0.1
        lebkuchen_heart(m, T(-0.72 + (k % 4) * 0.08, -0.05 + (k // 4) * 0.12, 0.05 + (k % 2) * 0.01,
                             rx=-0.9 + rng.uniform(-0.1, 0.1), rz=rng.uniform(-0.2, 0.2)), size, k + 2)
    m.box((0.36, 0.26, 0.002), T(0.1, 0.0, 0.001), "paper", C("f6f2ea"))
    for k in range(9 if not vlib.lite() else 5):
        x, y = 0.0 + (k % 3) * 0.1, -0.08 + (k // 3) * 0.09
        Mc = T(x, y, 0.002 + (0.012 if k == 4 else 0))
        m.lathe([(0.0, 0.0), (0.042, 0.0), (0.044, 0.006), (0.04, 0.011), (0.0, 0.013)], seg(12, 6), "roll",
                Mc, C("9a5a2a"), "glaze")
        for j in range(2 if not vlib.lite() else 0):
            a = TWO_PI * j / 3 + k
            m.sphere(0.009, 5, 3, "sw_satin", Mc @ T(0.018 * math.cos(a), 0.018 * math.sin(a), 0.012, rz=a),
                     C("e8d0a0"), scale=(1.6, 0.8, 0.4))
    G.bowl(m, T(0.62, 0.0, 0), r=0.13, h=0.05)
    for k in range(14 if not vlib.lite() else 5):
        a, rr = rng.uniform(0, TWO_PI), 0.09 * math.sqrt(rng.random())
        m.sphere(0.017, 6, 4, "wax", T(0.62 + rr * math.cos(a), rr * math.sin(a), 0.03 + (0.09 - rr) * 0.25), C("f4efe6"),
                 scale=(1, 1, 0.75))
    s.finish()
    return s


# ------------------------------------------------------------------ Gebrannte Mandeln
def almond_heap(m, M, r, h, col=WHITE):
    k = seg(10, 6)
    prof = [(r, 0.0), (r * 0.85, h * 0.55), (r * 0.35, h * 0.95), (0.0, h * 1.02)]
    m.lathe(prof, k, "almonds", M, col, "glaze", v_by="z")


def mandeln():
    s = vlib.PropSet("prop_deco_mandeln", "slot_counter", "deco-mandeln")
    m = s.static
    # the copper roasting kettle on its stand with a stirring paddle
    Mk = T(-0.72, 0.0, 0)
    n = seg(24, 10)
    m.lathe([(0.2, 0.0), (0.21, 0.01), (0.21, 0.1), (0.2, 0.11)], n, vlib.RW("iron"), Mk, WHITE)
    m.lathe([(0.0, 0.1), (0.12, 0.1), (0.19, 0.14), (0.225, 0.22), (0.232, 0.232), (0.222, 0.23), (0.182, 0.15),
             (0.11, 0.115), (0.0, 0.112)], n, vlib.RW("copper"), Mk, WHITE)
    almond_heap(m, Mk @ T(0, 0, 0.12), 0.18, 0.085, C("f4e4d4"))
    m.box((0.36, 0.03, 0.01), Mk @ T(0, 0, 0.3, rz=0.6), "steel", WHITE)
    m.cyl(0.008, 0.008, 0.3, 8, "steel", Mk @ T(0, 0, 0.12), WHITE)
    m.cyl(0.02, 0.02, 0.02, 10, "brass", Mk @ T(0, 0, 0.42), WHITE)
    # a rack of paper cones filled with almonds
    Mr = T(0.15, 0.02, 0)
    m.box((0.62, 0.2, 0.02), Mr @ T(0, 0, 0.11), vlib.RW("wood"), C("a07448"))
    for sx in (-1, 1):
        m.box((0.02, 0.2, 0.11), Mr @ T(sx * 0.3, 0, 0.055), vlib.RW("wood"), C("a07448"))
    for k in range(10 if not vlib.lite() else 5):
        cx, cy = -0.24 + (k % 5) * 0.12, -0.05 + (k // 5) * 0.1
        Mc = Mr @ T(cx, cy, 0.0, rz=rng.uniform(0, 6))
        m.lathe([(0.004, 0.0), (0.042, 0.2), (0.044, 0.205)], seg(10, 5), "cone_paper", Mc, jit(WHITE, 0.04), "atlas")
        m.lathe([(0.0405, 0.2), (0.004, 0.02)], seg(10, 5), "paper", Mc, C("e8e0d0"))
        almond_heap(m, Mc @ T(0, 0, 0.19), 0.042, 0.045, jit(C("f4e0d0"), 0.08))
    # filled cones lying ready on a paper in front of the rack
    m.box((0.62, 0.1, 0.002), T(0.17, -0.18, 0.001), "paper", C("f4efe4"), skip=("nz",))
    for k in range(3 if not vlib.lite() else 2):
        Mc = T(-0.05 + k * 0.22, -0.185, 0.023, rz=0.12 * (k - 1), ry=math.pi / 2 - 0.2) @ T(0, 0, -0.1)
        m.lathe([(0.004, 0.0), (0.042, 0.2)], seg(8, 5), "cone_paper", Mc, jit(WHITE, 0.04), "atlas")
        almond_heap(m, Mc @ T(0, 0, 0.19), 0.04, 0.03, jit(C("f4e0d0"), 0.08))
    # a bowl of loose almonds with a steel scoop, a burlap sack of raw almonds at the back, a tray of
    # candied cashews and a stack of little striped bags
    G.bowl(m, T(0.66, -0.06, 0), r=0.12, h=0.05)
    almond_heap(m, T(0.66, -0.06, 0.012), 0.105, 0.075, C("f0dcc8"))
    m.lathe([(0.0, 0.0), (0.04, 0.0), (0.045, 0.03), (0.0, 0.035)], seg(12, 5), "steel", T(0.8, -0.16, 0.0125, rx=0.3), WHITE)
    Ms = T(0.66, 0.15, 0)
    sack = [(0.0, 0.0), (0.075, 0.0), (0.09, 0.03), (0.088, 0.1), (0.082, 0.135), (0.092, 0.15)]
    m.lathe(sack if not vlib.lite() else [sack[0], sack[1], sack[3], sack[5]], seg(10, 6), vlib.RW("burlap"), Ms,
            C("c8a878"), smooth=True)
    m.lathe([(0.092, 0.15), (0.084, 0.158), (0.078, 0.14)], seg(10, 6), "burlap", Ms, C("b09060"))
    almond_heap(m, Ms @ T(0, 0, 0.12), 0.08, 0.04, C("c89a70"))
    G.board(m, T(0.93, 0.13, 0), 0.2, 0.14, 0.012, C("8a6440"))
    for sx in (-1, 1):
        m.box((0.2, 0.01, 0.02), T(0.93, 0.13 + sx * 0.065, 0.02), vlib.RW("wood"), C("7a5434"))
    almond_heap(m, T(0.93, 0.13, 0.012) @ Matrix.Diagonal((1.3, 0.8, 1.0, 1.0)), 0.07, 0.03, C("e8c890"))
    for k in range(5 if not vlib.lite() else 2):
        m.box((0.07, 0.04, 0.11 - 0.004 * k), T(0.95 + (k % 2) * 0.004, -0.02 - k * 0.042, 0.055, rz=drng.uniform(-0.12, 0.12)),
              "cone_paper", WHITE, skip=("nz",))
    s.finish()
    return s


# ------------------------------------------------------------------ Kerzen
CANDLE_COLS = ["b0282a", "f2ead8", "2a6a3a", "d8b048", "2a4a8a", "7a3a7a", "e8d0a0", "c0562a", "f4f0e8", "5a8ab0"]


def candle(m, M, r, h, col, lit=False, kind="pillar"):
    n = seg(8, 5)
    region = "honeycomb" if kind == "beeswax" else vlib.RW("wax")
    m.lathe([(r, 0.0), (r, h - 0.006), (r * 0.92, h), (0.0, h - 0.004)], n, region, M, col, "atlas", v_by="z")
    if lit:
        m.cyl(0.0012, 0.0012, 0.012, 3, "sw_matte", M @ T(0, 0, h - 0.004), C("1a1410"), caps=False)
        m.lathe([(0.0, 0.0), (0.0038, 0.008), (0.0022, 0.02), (0.0, 0.03)], 6, "sw_satin",
                M @ T(0, 0, h + 0.006), WHITE, "flame")


def taper_pair(m, x, drop, col):
    top = hang(m, x, 0.02, C("e8e0d0"), 0.0012)
    for dx in (-0.012, 0.012):
        m.tube([(x, ROD_Y, ROD_Z - 0.01), (x + dx, ROD_Y, ROD_Z - 0.03)], 0.001, 3, "sw_matte", None, C("e8e0d0"))
        Mc = T(x + dx, ROD_Y, ROD_Z - 0.03, rx=math.pi)
        n = seg(7, 5)
        m.lathe([(0.0, 0.0), (0.0085, 0.05), (0.011, drop), (0.0, drop + 0.004)], n, vlib.RW("wax"),
                Mc, col, "atlas")


def kerzen():
    s = vlib.PropSet("prop_deco_kerzen", "slot_counter", "deco-kerzen")
    m = s.static
    rod(m, -1.05, 1.05)
    for i, x in enumerate((-0.95, -0.85, -0.75, 0.75, 0.85, 0.95) if not vlib.lite() else (-0.9, 0.8)):
        taper_pair(m, x, rng.uniform(0.22, 0.3), C(CANDLE_COLS[i % len(CANDLE_COLS)]))
    # stepped risers with candles of many sizes
    for k, (dz, dy) in enumerate(((0.0, -0.1), (0.07, 0.05), (0.14, 0.17))):
        m.box((1.6, 0.14, 0.02), T(-0.1, dy, dz + 0.01), vlib.RW("wood"), C("7a5230"))
        if k:
            m.box((1.6, 0.02, dz), T(-0.1, dy - 0.07, dz / 2), vlib.RW("wood"), C("6a4428"))
            m.box((1.6, 0.14, dz), T(-0.1, dy, dz / 2), vlib.RW("wood"), C("6a4428"), skip=("ny",))
    x = -0.85
    k = 0
    while x < 0.65:
        tier = k % 3
        dz, dy = ((0.02, -0.1), (0.09, 0.05), (0.16, 0.17))[tier]
        kind = rng.choice(["pillar", "pillar", "beeswax", "pillar", "short"])
        r = rng.uniform(0.022, 0.045) if kind != "short" else rng.uniform(0.035, 0.05)
        h = rng.uniform(0.07, 0.22) if kind != "short" else rng.uniform(0.05, 0.08)
        col = C(CANDLE_COLS[rng.randrange(len(CANDLE_COLS))]) if kind != "beeswax" else C("e8b050")
        candle(m, T(x, dy + rng.uniform(-0.02, 0.02), dz), r, h, jit(col, 0.05), lit=(k % 7 == 3), kind=kind)
        k += 1
        if tier == 2:
            x += 0.15 if not vlib.lite() else 0.36
    # a glass lantern with a lit candle and a cluster of tealights
    Ml = T(0.85, 0.0, 0)
    m.box((0.13, 0.13, 0.015), Ml @ T(0, 0, 0.0075), "iron", WHITE)
    m.box((0.12, 0.12, 0.02), Ml @ T(0, 0, 0.21), "iron", WHITE)
    m.lathe([(0.075, 0.22), (0.02, 0.27), (0.0, 0.275)], 4, "iron", Ml @ T(0, 0, 0, rz=math.pi / 4), WHITE)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((0.01, 0.01, 0.2), Ml @ T(sx * 0.058, sy * 0.058, 0.11), "iron", WHITE)
    m.box((0.11, 0.11, 0.19), Ml @ T(0, 0, 0.11), "sw_vgloss", C("f4f6f2"), "glass")
    candle(m, Ml @ T(0, 0, 0.015), 0.025, 0.09, C("f2ead8"), lit=True)
    for k in range(4 if not vlib.lite() else 2):
        a = TWO_PI * k / 4
        Mt = T(0.62 + 0.045 * math.cos(a), -0.14 + 0.045 * math.sin(a), 0)
        m.lathe([(0.019, 0.0), (0.019, 0.016), (0.0175, 0.016), (0.0175, 0.003)], seg(8, 5), "steel", Mt, WHITE)
        candle(m, Mt @ T(0, 0, 0.003), 0.0172, 0.011, C("f4f0e8"), lit=(k % 2 == 0))
    s.finish()
    return s


# ------------------------------------------------------------------ Holzspielzeug
def nutcracker(m, M, coat=C("a8181c"), trousers=C("f2ead8"), hat=C("141414"), s=1.0):
    S = M @ Matrix.Diagonal((s, s, s, 1))
    n = seg(7, 5)
    m.box((0.1, 0.07, 0.02), S @ T(0, 0, 0.01), vlib.RW("wood"), C("2a6a3a"))
    for sx in (-1, 1):
        m.cyl(0.017, 0.017, 0.03, n, "sw_gloss", S @ T(sx * 0.022, 0.0, 0.02), C("141414"), "glaze")
        m.cyl(0.016, 0.016, 0.07, n, "sw_gloss", S @ T(sx * 0.022, 0.0, 0.05), trousers, "glaze", caps=False)
    m.lathe([(0.0, 0.12), (0.044, 0.12), (0.046, 0.16), (0.04, 0.21), (0.0, 0.215)], n, "sw_gloss", S, coat, "glaze")
    if not vlib.lite():
        m.cyl(0.0465, 0.0465, 0.008, n, "sw_metal", S @ T(0, 0, 0.131), C("d8b048"), caps=False)     # belt
    for sx in (-1, 1):
        m.cyl(0.012, 0.011, 0.08, 6 if not vlib.lite() else 4, "sw_gloss", S @ T(sx * 0.05, 0, 0.13, ry=sx * 0.2), coat,
              "glaze")
    # head: face texture on the front
    m.cyl(0.03, 0.03, 0.055, n, "sw_gloss", S @ T(0, 0, 0.215), C("f0c8a0"), "glaze")
    m.box((0.05, 0.004, 0.05), S @ T(0, -0.0302, 0.243), "toy_face", WHITE, "glaze", faces={"ny": "toy_face"})
    m.lathe([(0.032, 0.268), (0.034, 0.275), (0.034, 0.33), (0.03, 0.335), (0.0, 0.336)], n, "sw_gloss", S, hat, "glaze")
    if not vlib.lite():
        m.cyl(0.0352, 0.0352, 0.006, n, "sw_metal", S @ T(0, 0, 0.282), C("d8b048"), caps=False)     # hat band
        m.box((0.012, 0.01, 0.012), S @ T(0, -0.034, 0.315), "sw_metal", C("d8b048"), skip=("py",))       # cockade


def train(m, M):
    cols = [C("b0282a"), C("2a6a3a"), C("2a4a8a")]
    for k in range(3 if not vlib.lite() else 2):
        Mw = M @ T(k * 0.13, 0, 0)
        body = cols[k]
        if k == 0:
            m.box((0.11, 0.06, 0.05), Mw @ T(0, 0, 0.035), "sw_gloss", body, "glaze")
            m.cyl(0.026, 0.026, 0.07, 12, "sw_gloss", Mw @ T(-0.065, 0, 0.045, ry=math.pi / 2), C("141414"), "glaze")
            m.box((0.045, 0.062, 0.05), Mw @ T(0.035, 0, 0.08), "sw_gloss", body, "glaze")
            m.cyl(0.01, 0.014, 0.035, 10, "sw_gloss", Mw @ T(-0.04, 0, 0.07), C("141414"), "glaze")
        else:
            m.box((0.11, 0.06, 0.04), Mw @ T(0, 0, 0.03), "sw_gloss", body, "glaze")
            for j in range(2):
                m.box((0.035, 0.035, 0.035), Mw @ T(-0.025 + j * 0.05, 0, 0.068, rz=j), vlib.RW("wood"),
                      C(["d8b048", "c8a070", "b0282a"][j + k - 1]), "atlas")
        for sx in (-1, 1) if not vlib.lite() or k == 0 else ():
            for sy in (-1,):                        # wheels on the visitor's side only
                m.cyl(0.015, 0.015, 0.008, seg(6, 5), "sw_satin", Mw @ T(sx * 0.035, sy * 0.034, 0.015, rx=math.pi / 2),
                      C("d8b048") if k == 0 else C("f2ead8"), "glaze")


def top(m, M, col):
    n = seg(8, 6)
    prof = [(0.0, 0.0), (0.035, 0.035), (0.033, 0.045), (0.006, 0.05), (0.006, 0.08), (0.0, 0.082)]
    m.lathe(prof if not vlib.lite() else [prof[0], prof[1], prof[3], prof[4], prof[5]], n, "sw_gloss", M, col, "glaze")
    if not vlib.lite():
        m.cyl(0.0352, 0.0352, 0.006, n, "sw_gloss", M @ T(0, 0, 0.036), C("f2ead8"), "glaze", caps=False)   # stripe


def pyramid(s, x, y):
    """A small Weihnachtspyramide: turned posts, two tiers of figures, a vane wheel on top (rot_pyramid)."""
    m = s.static
    n = seg(10, 6)
    for z, r in ((0.0, 0.1), (0.15, 0.085)):
        m.cyl(r, r, 0.012, n, vlib.RW("wood"), T(x, y, z), C("c89a64"))
    for k in range(4):
        a = TWO_PI * k / 4 + math.pi / 4
        m.cyl(0.006, 0.006, 0.3, 6 if not vlib.lite() else 4, vlib.RW("wood"),
              T(x + 0.09 * math.cos(a), y + 0.09 * math.sin(a), 0.012), C("c89a64"), caps=False)
        candle(m, T(x + 0.09 * math.cos(a), y + 0.09 * math.sin(a), 0.312), 0.006, 0.035, C("f2ead8"), lit=(k % 2 == 0))
    rot = s.node("rot_pyramid", (x, y, 0.0))
    rot.cyl(0.004, 0.004, 0.42, 6 if not vlib.lite() else 4, "sw_satin", None, C("c89a64"), caps=False)
    for z in (0.012, 0.162):
        rot.cyl(0.075, 0.075, 0.008, n, vlib.RW("wood"), T(0, 0, z), C("d8b078"))
        for k in range(4):
            a = TWO_PI * k / 4
            rot.cyl(0.009, 0.007, 0.05, 6 if not vlib.lite() else 4, "sw_gloss",
                    T(0.055 * math.cos(a), 0.055 * math.sin(a), z + 0.008), C(CANDLE_COLS[k]), "glaze", caps=False)
            if not vlib.lite():
                rot.cyl(0.0075, 0.0065, 0.014, 4, "sw_gloss", T(0.055 * math.cos(a), 0.055 * math.sin(a), z + 0.058),
                        C("f0c8a0"), "glaze", caps=False)
    nv = 8 if not vlib.lite() else 4
    for k in range(nv):
        a = TWO_PI * k / nv
        rot.box((0.07, 0.022, 0.002), T(0.045 * math.cos(a), 0.045 * math.sin(a), 0.41, rz=a, rx=0.5), vlib.RW("wood"),
                C("d8b078"))


def spanbaum(m, M, h=0.12, col=C("e8d0a0")):
    """Erzgebirge shaving tree (Spanbaum): a curled-shaving cone on a turned stem and a small foot."""
    n = seg(7, 5)
    m.cyl(0.005, 0.005, 0.03, 4, vlib.RW("wood"), M, C("b8864e"), caps=False)
    prof = [(0.036, 0.03), (0.021, 0.03 + h * 0.42), (0.026, 0.03 + h * 0.46), (0.0, 0.03 + h)]
    m.lathe(prof if not vlib.lite() else [prof[0], prof[3]], n, "straw", M, col, cap0=not vlib.lite())


def spielzeug():
    s = vlib.PropSet("prop_deco_spielzeug", "slot_counter", "deco-spielzeug")
    m = s.static
    # a stepped riser along the back of the left half, with a row of shaving trees on it
    m.box((1.22, 0.1, 0.07), T(-0.4, 0.18, 0.035), vlib.RW("wood"), C("8a5a34"), skip=("nz",))
    for k, x in enumerate((-0.94, -0.78, -0.62, -0.3, -0.14, 0.02)):
        if vlib.lite() and k % 2:
            continue
        spanbaum(m, T(x, 0.18, 0.07, rz=k), h=0.1 + (k % 3) * 0.03, col=C(["e8d0a0", "d8e0c0", "e0c8a0"][k % 3]))
    nutcracker(m, T(-0.93, 0.02, 0), C("a8181c"), C("f2ead8"), s=1.0)
    if not vlib.lite():
        nutcracker(m, T(-0.79, 0.05, 0, rz=0.2), C("1f3a78"), C("141414"), C("a8181c"), s=0.85)
        nutcracker(m, T(-0.66, -0.02, 0, rz=-0.15), C("2a6a3a"), C("f2ead8"), s=0.7)
    train(m, T(-0.46, -0.13, 0))
    for k, x in enumerate((-0.05, 0.04, 0.13) if not vlib.lite() else (0.04,)):
        top(m, T(x, -0.14, 0), C(["b0282a", "2a4a8a", "d8b048"][k]))
    # a tower of painted blocks
    for k in range(6 if not vlib.lite() else 3):
        m.box((0.04, 0.04, 0.04), T(0.25 + (k % 3) * 0.045 - (k // 3) * 0.02, 0.06, 0.02 + (k // 3) * 0.04,
                                    rz=drng.uniform(-0.2, 0.2)), vlib.RW("wood"), C(CANDLE_COLS[k]))
    pyramid(s, 0.55, 0.05)
    # a small rocking horse
    Mh = T(0.86, -0.02, 0)
    k = 5 if not vlib.lite() else 3
    for sy in (-1, 1):
        pts = [(-0.12 + 0.24 * i / (k - 1), sy * 0.03, 0.02 + 0.03 * (2 * i / (k - 1) - 1) ** 2) for i in range(k)]
        m.tube(pts, 0.006, 4, vlib.RW("wood"), Mh, C("7a4a28"))
    m.box((0.14, 0.05, 0.05), Mh @ T(0, 0, 0.1), "sw_gloss", C("f2ead8"), "glaze")
    m.box((0.03, 0.035, 0.08), Mh @ T(0.08, 0, 0.14, ry=-0.4), "sw_gloss", C("f2ead8"), "glaze")
    m.box((0.06, 0.03, 0.03), Mh @ T(0.11, 0, 0.18), "sw_gloss", C("f2ead8"), "glaze")
    for sx in (-0.05, 0.05):
        m.box((0.015, 0.05, 0.07), Mh @ T(sx, 0, 0.055), "sw_gloss", C("f2ead8"), "glaze")
    m.box((0.06, 0.052, 0.012), Mh @ T(0, 0, 0.128), "sw_gloss", C("a8181c"), "glaze")
    # wooden stars and hearts cut from plywood, leaning in a small crate at the right end
    G.crate(m, T(0.86, 0.17, 0), 0.2, 0.1, 0.05, C("b48c5c"), slats=1)
    for k in range(4 if not vlib.lite() else 2):
        poly = star_poly(0.04, 0.018, 5) if k % 2 == 0 else heart_poly(0.08, 10)
        m.extrude(poly, 0.006, T(0.8 + k * 0.04, 0.16, 0.05, rx=math.pi / 2 - 0.3, rz=drng.uniform(-0.15, 0.15)),
                  vlib.RW("wood"), vlib.RW("wood"), C(["c8a070", "b0282a", "d8b078", "2a6a3a"][k]), back=not vlib.lite())
    s.finish()
    return s


# ------------------------------------------------------------------ Christbaumschmuck
BAUBLE_COLS = ["a8161d", "d8b048", "1d3a78", "e8e4dc", "1f5a3a", "8a2a6a", "c0c4c8", "e07a2a"]


def bauble(m, M, r, col, shiny=True, cap=True, n=8, rings=4, upper=False):
    """A glass bauble hanging from its cap (origin at the top of the cap). upper: only the top half and a
    little more, for baubles sitting in an egg crate."""
    n, rings = seg(n, 5), seg(rings, 2)
    reg, mat = ("sw_metal_polish", "atlas") if shiny else ("sw_satin", "glaze")
    if upper:
        prof = [(r * math.cos(a), r * math.sin(a)) for a in (-0.3, 0.75)] + [(0.0, r)]
        m.lathe(prof, n, reg, M @ T(0, 0, -r), col, mat)
    else:
        m.sphere(r, n, rings, reg, M @ T(0, 0, -r), col, mat)
    if cap:
        m.cyl(r * 0.28, r * 0.25, r * 0.28, 6 if not vlib.lite() else 4, "sw_metal", M @ T(0, 0, -0.004), C("d8c080"),
              caps=False)


def tabletop_tree(m, M, h=0.34):
    """A little decorated fir on the counter: three stacked green cones, a pot, tiny baubles, a gold star."""
    n = seg(10, 6)
    m.lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.05), (0.0, 0.05)], n, "sw_satin", M, C("8a2a1a"))
    m.cyl(0.008, 0.008, 0.04, 5, vlib.RW("wood"), M @ T(0, 0, 0.05), C("5a3622"), caps=False)
    tiers = ((0.09, 0.07, 0.15), (0.07, 0.15, 0.24), (0.05, 0.22, h))
    for r, z0, z1 in tiers:
        m.lathe([(r, z0), (r * 0.55, (z0 + z1) / 2 + 0.01), (0.0, z1)], n, "straw", M, C("1f4a2a"), cap0=True)
    k = 0
    for r, z0, z1 in tiers:
        for j in range(3 if not vlib.lite() else 0):
            a = TWO_PI * j / 3 + k * 0.9 - 0.9
            rr = r * 0.78
            bauble(m, M @ T(rr * math.cos(a), rr * math.sin(a), z0 + 0.012), 0.011,
                   C(BAUBLE_COLS[(j + k) % len(BAUBLE_COLS)]), n=6, rings=3, cap=False)
        k += 1
    star = star_poly(0.028, 0.012, 5)
    m.extrude(star, 0.004, M @ T(0, 0.002, h + 0.022, rx=math.pi / 2), "sw_metal", "sw_metal", C("d8b048"))


def schmuck():
    s = vlib.PropSet("prop_deco_schmuck", "slot_counter", "deco-schmuck")
    m = s.static
    rod(m, -1.08, 1.08)
    xs = [-1.0, -0.9, -0.8, -0.7, -0.6, -0.5, -0.4, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for i, x in enumerate(xs):
        drop = rng.uniform(0.12, 0.4)
        p = hang(m, x, drop, C("d8b048"), 0.001)
        if i % 4 == 3:
            # straw star: two crossed layers
            Ms = T(p.x, p.y, p.z - 0.06, rx=math.pi / 2, ry=rng.uniform(-0.3, 0.3))
            for k in range(2 if not vlib.lite() else 1):
                sp = star_poly(0.06, 0.012, 4, rot=k * math.pi / 4)
                m.extrude(sp, 0.002, Ms @ T(0, 0, k * 0.002), "straw", "straw", C("e8c880"), back=not vlib.lite())
        elif i % 4 == 1:
            # glass icicle
            m.lathe([(0.0, 0.0), (0.009, -0.02), (0.006, -0.1), (0.0, -0.14)], seg(8, 5), "sw_vgloss", T(p.x, p.y, p.z),
                    C("e8f0f4"), "glass")
            m.cyl(0.004, 0.004, 0.008, 6 if not vlib.lite() else 4, "sw_metal", T(p.x, p.y, p.z - 0.002), C("d8c080"),
                  caps=False)
        else:
            bauble(m, T(p.x, p.y, p.z), rng.choice([0.03, 0.035, 0.045, 0.05]), C(BAUBLE_COLS[i % len(BAUBLE_COLS)]),
                   shiny=i % 3 != 2, n=9, rings=4)
    # egg-crate trays of baubles on the counter (only their tops show above the crate)
    for t, (tx, cols) in enumerate(((-0.5, BAUBLE_COLS[:4]), (0.02, BAUBLE_COLS[4:] + ["a8161d", "d8b048"]))):
        Mt = T(tx, -0.02, 0)
        m.box((0.44, 0.3, 0.035), Mt @ T(0, 0, 0.0175), "kraft", C("d8c8a8"), skip=("nz",))
        for k in range(12):
            if vlib.lite() and (k + k // 4) % 2:
                continue
            cx, cy = -0.165 + (k % 4) * 0.11, -0.1 + (k // 4) * 0.1
            r = 0.035
            bauble(m, Mt @ T(cx, cy, 0.035 + 2 * r - 0.008, rx=drng.uniform(-0.4, 0.4), ry=drng.uniform(-0.4, 0.4)),
                   r, C(cols[(k + t) % len(cols)]), shiny=(k % 5 != 2), n=7, cap=not vlib.lite(), upper=True)
    # a decorated tabletop tree, two loose baubles on their sides and a glass tree-top spire
    tabletop_tree(m, T(0.5, 0.06, 0))
    for x, y, r, col, a in ((0.34, -0.14, 0.04, "a8161d", 0.4), (0.66, -0.16, 0.034, "d8b048", 2.2)):
        bauble(m, T(x, y, r * (1 + math.cos(1.2)), rx=1.2, rz=a), r, C(col), n=9, rings=4)
    Mp = T(0.86, 0.02, 0)
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.02), (0.012, 0.04), (0.035, 0.09), (0.012, 0.13), (0.004, 0.3),
             (0.0, 0.31)], seg(8, 6), "sw_metal_polish", Mp, C("a8161d"))
    s.finish()
    return s


# ------------------------------------------------------------------ Käse
def cheese_wheel(m, M, r, h, cut=0.0, rind=C("ffffff"), wax=None):
    """A wheel; with cut (radians) a wedge is missing at the front showing the paste."""
    n = seg(28, 10)
    arc = TWO_PI - cut
    a0 = -math.pi / 2 + cut / 2
    region = "cheese_rind" if wax is None else "sw_gloss"
    col = rind if wax is None else wax
    prof = [(r - 0.01, 0.0), (r, 0.01), (r * 1.01, h / 2), (r, h - 0.01), (r - 0.01, h)]
    m.lathe(prof, n, vlib.RW(region) if wax is None else region, M, col, "atlas", arc=arc, u0=a0)
    # top and bottom caps (fans)
    for z, flip in ((h, False), (0.0, True)):
        k = n
        pts = [(0.0, 0.0, z)] + [((r - 0.01) * math.cos(a0 + arc * j / k), (r - 0.01) * math.sin(a0 + arc * j / k), z)
                                 for j in range(k + 1)]
        faces = [(0, j + 1, j + 2) for j in range(k)]
        if flip:
            faces = [f[::-1] for f in faces]
        reg = vlib.RW(region) if wax is None else vlib.R(region)
        uvs = [[reg.uv(0.5 + 0.5 * pts[i][0] / r, 0.5 + 0.5 * pts[i][1] / r) for i in f] for f in faces]
        m.add(pts, faces, uvs, M, col, "atlas", False)
    if cut:
        for a, flip in ((a0, True), (a0 + arc, False)):
            ca, sa = math.cos(a), math.sin(a)
            quad = [(0, 0, 0.0), (r * ca, r * sa, 0.0), (r * ca, r * sa, h), (0, 0, h)]
            if flip:
                quad = quad[::-1]
            m.quad(quad, "cheese_cut", WHITE, "atlas", M)


def kaese():
    s = vlib.PropSet("prop_deco_kaese", "slot_counter", "deco-kaese")
    m = s.static
    cheese_wheel(m, T(-0.78, 0.02, 0), 0.22, 0.11, cut=0.9)
    cheese_wheel(m, T(-0.3, 0.1, 0), 0.14, 0.09)
    cheese_wheel(m, T(-0.3, 0.1, 0.09, rz=0.5), 0.12, 0.08, rind=C("e0c080"))
    cheese_wheel(m, T(-0.3, 0.1, 0.17, rz=1.1), 0.1, 0.07, wax=C("a8161d"))
    # a cutting board with a wedge and the cheese harp / knife
    G.board(m, T(0.18, -0.04, 0), 0.4, 0.3, 0.025, C("c89e70"))
    wedge = T(0.12, -0.06, 0.025, rz=0.3)
    cheese_wheel(m, wedge @ T(-0.18, 0, 0), 0.18, 0.08, cut=TWO_PI - 0.5)
    m.box((0.22, 0.03, 0.002), T(0.28, 0.04, 0.03, rz=-0.3), "steel", WHITE)
    m.box((0.1, 0.022, 0.018), T(0.43, -0.01, 0.034, rz=-0.3), vlib.RW("wood"), C("3a2414"))
    # red-waxed rounds and small smoked cheeses in a crate
    G.crate(m, T(0.75, 0.04, 0), 0.4, 0.3, 0.06)
    for k in range(6):
        cx, cy = 0.63 + (k % 3) * 0.12, -0.03 + (k // 3) * 0.13
        if k % 2:
            m.sphere(0.055, seg(14, 8), seg(8, 5), "sw_gloss", T(cx, cy, 0.06), C("a8161d"), scale=(1, 1, 0.8))
        else:
            cheese_wheel(m, T(cx, cy, 0.015), 0.055, 0.05, rind=C("a86a2a"))
    s.finish()
    return s


# ------------------------------------------------------------------ Crêpes
def griddle(m, M, with_crepe=True):
    n = seg(32, 10)
    m.box((0.44, 0.44, 0.1), M @ T(0, 0, 0.05), "steel", WHITE)
    m.cyl(0.2, 0.2, 0.012, n, vlib.RW("iron"), M @ T(0, 0, 0.1), C("7a7a7a"), cap_region="iron")
    m.torus(0.2, 0.004, n, 4, "iron", M @ T(0, 0, 0.112), C("5a5a5a"))
    m.cyl(0.012, 0.012, 0.012, seg(10, 5), "sw_satin", M @ T(0.17, -0.225, 0.05, rx=math.pi / 2), C("1a1a1a"))
    if with_crepe:
        m.lathe([(0.0, 0.0), (0.16, 0.0), (0.175, -0.001)], n, "crepe", M @ T(0, 0, 0.1125), WHITE, v_by="len")
        m.disc(0.176, n, "crepe", M @ T(0, 0, 0.1128), WHITE, "atlas")


def crepes():
    s = vlib.PropSet("prop_deco_crepes", "slot_counter", "deco-crepes")
    m = s.static
    griddle(m, T(-0.75, 0.0, 0), True)
    griddle(m, T(-0.28, 0.0, 0), False)
    # batter on the second griddle being spread with the wooden rake
    m.disc(0.12, seg(24, 12), "sw_wet", T(-0.28, 0.0, 0.1128), C("f0dca0"), "liquid")
    m.box((0.02, 0.16, 0.006), T(-0.24, 0.02, 0.118, rz=0.5), vlib.RW("wood"), C("c8a070"))
    m.cyl(0.006, 0.006, 0.14, 5, vlib.RW("wood"), T(-0.24, 0.02, 0.12, ry=math.pi / 2 - 0.3, rz=0.5), C("c8a070"))
    # batter bowl with ladle, a jar of hazelnut spread, sugar shaker, a plate of folded crêpes
    Mb = T(0.12, 0.05, 0)
    m.lathe([(0.0, 0.0), (0.06, 0.0), (0.1, 0.06), (0.11, 0.09), (0.105, 0.09), (0.095, 0.06), (0.0, 0.01)],
            seg(20, 10), "steel", Mb, WHITE)
    m.disc(0.095, seg(20, 10), "sw_wet", Mb @ T(0, 0, 0.07), C("f0dca0"), "liquid")
    m.tube([(0.0, 0.0, 0.06), (0.03, 0.02, 0.1), (0.09, 0.06, 0.2)], 0.005, 5, "steel", Mb, WHITE)
    G.jar(m, T(0.34, 0.12, 0), "jar_orange", C("3a1a0a"), "sw_wet", h=0.1, r=0.04, lid=C("d8b048"))
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.09), (0.02, 0.12), (0.0, 0.125)], seg(12, 5), "sw_vgloss", T(0.44, 0.12, 0),
            C("f0f4f4"), "glass")
    m.lathe([(0.0, 0.002), (0.027, 0.002), (0.027, 0.06), (0.0, 0.06)], seg(10, 5), "wax", T(0.44, 0.12, 0), C("fbfaf6"))
    m.lathe([(0.0, 0.0), (0.12, 0.0), (0.13, 0.012), (0.0, 0.006)], seg(20, 10), "ceramic", T(0.35, -0.1, 0),
            C("f4f0e8"), "glaze")
    for k in range(4 if not vlib.lite() else 2):
        tri = [(0.0, 0.0), (0.16, 0.0), (0.0, 0.16)]
        m.extrude(tri, 0.006, T(0.3 + k * 0.012, -0.16 + k * 0.01, 0.012 + k * 0.006, rz=0.6 + k * 0.2), "crepe",
                  "crepe", WHITE)
    # paper cones for crêpes to go
    for k in range(5 if not vlib.lite() else 2):
        m.lathe([(0.004, 0.0), (0.04, 0.17)], seg(10, 5), "paper", T(0.72 + k * 0.06, 0.12, 0), C("f4f0e8"))
    s.finish()
    return s


# ------------------------------------------------------------------ Heiße Maroni
def chestnut(m, M, r=0.016, col=WHITE):
    n, k = seg(7, 5), seg(4, 3)
    prof = []
    for i in range(k + 1):
        a = -math.pi / 2 + math.pi * i / k
        rr = r * math.cos(a)
        z = r * (1 + math.sin(a)) * 0.85
        prof.append((max(0.0005, rr), z))
    prof.append((0.0, r * 1.95))
    m.lathe(prof, n, "chestnut", M, col, "glaze", v_by="z")


def maroni():
    s = vlib.PropSet("prop_deco_maroni", "slot_counter", "deco-maroni")
    m = s.static
    # brazier drum with a fire door showing glowing coals; a perforated roasting pan on top
    Md = T(-0.7, 0.0, 0)
    n = seg(32, 14)
    m.lathe([(0.2, 0.0), (0.21, 0.01), (0.21, 0.2), (0.205, 0.21)], n, vlib.RW("iron"), Md, WHITE, arc=TWO_PI * 0.8,
            u0=-math.pi / 2 + TWO_PI * 0.1)
    m.lathe([(0.19, 0.0), (0.19, 0.2)], n, "iron", Md, C("4a4a4a"), arc=TWO_PI * 0.8, u0=-math.pi / 2 + TWO_PI * 0.1)
    m.disc(0.2, n, "iron", Md @ T(0, 0, 0.012), C("3a3a3a"))
    full = vlib.Reg([0.0, 0.0, 1.0, 1.0])
    for k in range(10 if not vlib.lite() else 4):
        a, rr = rng.uniform(0, TWO_PI), 0.16 * math.sqrt(rng.random())
        lump(m, Md @ T(rr * math.cos(a), rr * math.sin(a), 0.03 + rng.uniform(0, 0.02)), rng.uniform(0.025, 0.035), full,
             jit(WHITE, 0.2), "coal_glow", seed=k * 0.7)
    pan = [(0.0, 0.2), (0.16, 0.2), (0.22, 0.24), (0.23, 0.26), (0.222, 0.262), (0.212, 0.245), (0.155, 0.21),
           (0.0, 0.21)]
    m.lathe(pan, n, vlib.RW("iron"), Md, C("5a5a5a"))
    m.cyl(0.012, 0.012, 0.3, 8, "iron", Md @ T(0.22, 0, 0.245, ry=math.pi / 2), WHITE)
    m.cyl(0.016, 0.016, 0.12, 8, vlib.RW("wood"), Md @ T(0.5, 0, 0.245, ry=math.pi / 2), C("5a3622"))
    for k in range(24 if not vlib.lite() else 8):
        a, rr = rng.uniform(0, TWO_PI), 0.17 * math.sqrt(rng.random())
        chestnut(m, Md @ T(rr * math.cos(a), rr * math.sin(a), 0.212 + (0.17 - rr) * 0.08,
                           rx=rng.uniform(-0.6, 0.6), ry=rng.uniform(-0.6, 0.6), rz=rng.uniform(0, 6)),
                 rng.uniform(0.014, 0.018), jit(WHITE, 0.1))
    # a basket of roasted chestnuts, paper bags ready to fill, a scoop
    G.bowl(m, T(0.05, 0.0, 0), r=0.14, h=0.06, col=C("8a6a40"))
    for k in range(12 if not vlib.lite() else 4):
        a, rr = rng.uniform(0, TWO_PI), 0.1 * math.sqrt(rng.random())
        chestnut(m, T(0.05 + rr * math.cos(a), rr * math.sin(a), 0.02 + (0.1 - rr) * 0.3,
                      rx=rng.uniform(-0.8, 0.8), rz=rng.uniform(0, 6)), 0.016, jit(WHITE, 0.1))
    for k in range(4):
        Mb = T(0.38 + k * 0.1, 0.08 - (k % 2) * 0.04, 0, rz=rng.uniform(-0.2, 0.2))
        m.box((0.08, 0.05, 0.15), Mb @ T(0, 0, 0.075), "kraft_maroni", WHITE, faces={"ny": "kraft_maroni"})
        m.box((0.082, 0.052, 0.03), Mb @ T(0, 0, 0.16, rx=0.3), "kraft", WHITE)
    m.lathe([(0.0, 0.0), (0.05, 0.0), (0.055, 0.04), (0.0, 0.045)], 12, "steel", T(0.8, -0.1, 0, rz=0.9), WHITE)
    m.cyl(0.008, 0.008, 0.12, 6, vlib.RW("wood"), T(0.84, -0.14, 0.03, ry=math.pi / 2 - 0.2, rz=-0.6), C("5a3622"))
    s.finish()
    return s


# ------------------------------------------------------------------ Kartoffelpuffer
def pancake(m, M, r):
    n = seg(14, 8)
    pts = [((r * (1 + rng.uniform(-0.08, 0.08))) * math.cos(TWO_PI * j / n),
            (r * (1 + rng.uniform(-0.08, 0.08))) * math.sin(TWO_PI * j / n)) for j in range(n)]
    m.extrude(pts, 0.009, M, "puffer", vlib.R("puffer", sub=(0.0, 0.0, 0.2, 0.2)), WHITE, back_region="puffer")


def puffer():
    s = vlib.PropSet("prop_deco_puffer", "slot_counter", "deco-kartoffelpuffer")
    m = s.static
    # big flat pan on a gas ring with oil and frying pancakes
    Mp = T(-0.65, 0.0, 0)
    n = seg(36, 14)
    m.lathe([(0.17, 0.0), (0.18, 0.01), (0.18, 0.06), (0.17, 0.07)], n, "iron", Mp, C("5a5a5a"))
    m.lathe([(0.0, 0.07), (0.2, 0.07), (0.235, 0.1), (0.24, 0.105), (0.232, 0.106), (0.2, 0.08), (0.0, 0.08)], n,
            vlib.RW("iron"), Mp, C("3a3a3a"))
    m.cyl(0.015, 0.015, 0.25, 8, "iron", Mp @ T(0.23, 0, 0.09, ry=math.pi / 2), WHITE)
    m.disc(0.2, n, "sw_wet", Mp @ T(0, 0, 0.083), C("c89a2a"), "liquid")
    for k in range(6):
        a = TWO_PI * k / 6 + 0.3
        pancake(m, Mp @ T(0.12 * math.cos(a), 0.12 * math.sin(a), 0.082, rz=rng.uniform(0, 6)), 0.045)
    pancake(m, Mp @ T(0, 0, 0.082), 0.042)
    # a steel tray of finished Puffer, applesauce bowl, batter bowl with ladle, paper plates
    m.box((0.36, 0.26, 0.012), T(-0.1, 0.02, 0.006), "steel", WHITE)
    for k in range(9 if not vlib.lite() else 5):
        pancake(m, T(-0.2 + (k % 3) * 0.1, -0.07 + (k // 3) * 0.09, 0.012 + (0.009 if k == 4 else 0),
                     rz=rng.uniform(0, 6)), 0.045)
    Ma = T(0.28, 0.05, 0)
    m.lathe([(0.0, 0.0), (0.05, 0.0), (0.09, 0.05), (0.095, 0.07), (0.088, 0.07), (0.0, 0.01)], seg(18, 10), "ceramic",
            Ma, C("f4f0e8"), "glaze")
    m.disc(0.085, seg(18, 10), "sw_satin", Ma @ T(0, 0, 0.058), C("d8b060"), "liquid")
    Mb = T(0.55, 0.08, 0)
    m.lathe([(0.0, 0.0), (0.1, 0.0), (0.12, 0.14), (0.115, 0.14), (0.0, 0.02)], seg(20, 10), "steel", Mb, WHITE)
    m.disc(0.112, seg(20, 10), "puffer", Mb @ T(0, 0, 0.11), C("f0e0b0"))
    m.tube([(0.0, 0.0, 0.1), (0.05, 0.05, 0.18), (0.1, 0.08, 0.26)], 0.006, 5, "steel", Mb, WHITE)
    for k in range(10 if not vlib.lite() else 3):
        m.lathe([(0.0, k * 0.004), (0.1, k * 0.004), (0.115, k * 0.004 + 0.012)], seg(18, 8), "paper",
                T(0.85, -0.05, 0), C("f6f2ea"))
    s.finish()
    return s


def _deco(key, fn, label, seed, stall_id, cam=((0.0, -1.45, 0.75), (0.0, 0.0, 0.25), 30)):
    return dict(fn=fn, slot="slot_counter", stall=stall_id, kind="counter", section=False, seed=seed, label=label,
                width=2.6, cam=cam)


HANG_CAM = ((0.0, -1.65, 0.85), (0.0, 0.0, 0.45), 28)
SETS = {
    "prop_deco_lebkuchen": _deco("lebkuchen", lebkuchen, "Lebkuchen", 61, "deco-lebkuchen", HANG_CAM),
    "prop_deco_mandeln": _deco("mandeln", mandeln, "Gebrannte Mandeln", 62, "deco-mandeln"),
    "prop_deco_kerzen": _deco("kerzen", kerzen, "Kerzen", 63, "deco-kerzen", HANG_CAM),
    "prop_deco_spielzeug": _deco("spielzeug", spielzeug, "Holzspielzeug", 64, "deco-spielzeug"),
    "prop_deco_schmuck": _deco("schmuck", schmuck, "Christbaumschmuck", 65, "deco-schmuck", HANG_CAM),
    "prop_deco_kaese": _deco("kaese", kaese, "Käse", 66, "deco-kaese"),
    "prop_deco_crepes": _deco("crepes", crepes, "Crêpes", 67, "deco-crepes"),
    "prop_deco_maroni": _deco("maroni", maroni, "Heiße Maroni", 68, "deco-maroni"),
    "prop_deco_puffer": _deco("puffer", puffer, "Kartoffelpuffer", 69, "deco-kartoffelpuffer"),
}
