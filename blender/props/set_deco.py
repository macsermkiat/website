"""Goods for the nine deco stalls. Every set goes on slot_counter of its deco stall.

Deco counters are 0.48 m deep at 1.05 m (y -0.237..0.243 from slot_counter); the front opening runs from
1.05 to 2.2 m. Goods keep inside that depth (check_props' seat check). Each deco stall plus its goods must
stay under 20k triangles, so the goods of the two biggest stalls (Spielzeug, Schmuck) are held near 3k. Sets that hang goods
(Lebkuchen hearts, dipped candles, baubles, straw stars) carry their own thin rod at z = +1.08 above the
counter, just under the stall's front header (relative y = -0.03).
"""
import math
import random
from contextlib import contextmanager

import bmesh  # noqa: F401
from mathutils import Matrix, Vector

import goods as G
import vlib
from set_wurst import lump
from vlib import C, T, WHITE, drng, jit, rng, seg

TWO_PI = 2 * math.pi
ROD_Z, ROD_Y = 1.08, -0.03


# ------------------------------------------------------------------ clickable goods (round 4)
# Every deco set now carries its own act_ nodes, so the engine (site/src/actions/items/deco.js) can drop its
# code-made stand-in hearts. Each item is its own node with its origin at its pivot: "base" (the point it
# rests on, for goods on the counter) or "hang" (the ribbon's knot on the rod, for goods hanging from it, so
# the engine's click swing turns it about the knot). items.json carries kind "deco", a display name and a
# `detail` line for the paper tag. Items exist in the lite glb too, at the same places: their placement and
# jitter come from their own seeded generator (`irng`), never from the shared stream that lite runs
# differently.
@contextmanager
def item(s, name, origin, label, detail, pivot="base", **extra):
    """Build an item in set coordinates inside the `with`; it lands in its own node, origin at `origin`."""
    m = s.node(name, tuple(origin))
    yield m
    ox, oy, oz = origin
    m.V[:] = [(x - ox, y - oy, z - oz) for x, y, z in m.V]
    if pivot == "hang":
        pivot = "hang: the ribbon's knot on the rod; the item swings about it"
    s.item(name, label, "deco", pivot=pivot, detail=detail, **extra)


def irng(*key):
    """A generator of its own for one item, the same in the full and the lite build."""
    return random.Random(hash_key(key))


def hash_key(key):
    h = 2166136261
    for ch in repr(key):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def hang_item(m, x, drop, col, r=0.0018, jx=0.0):
    """hang() for an item: the same ribbon and knot, with the jitter given (from the item's own generator)."""
    top = (x, ROD_Y, ROD_Z - 0.008)
    bot = (x + jx, ROD_Y, ROD_Z - drop)
    m.tube([top, bot], r, 4 if not vlib.lite() else 3, "sw_satin", None, col)
    m.box((0.008, 0.02, 0.006), T(x, ROD_Y, ROD_Z + 0.006), "sw_satin", col, skip=("nz",))
    return Vector(bot)


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


def price_tag(m, M, k):
    """A small folded kraft price tag (tent card); k picks one of the eight in the deco_tags region."""
    c, r = k % 4, k // 4
    reg = vlib.R("deco_tags", sub=(c / 4, 0.5 - r * 0.5, (c + 1) / 4, 1.0 - r * 0.5))
    w, h, a = 0.07, 0.05, 0.3
    front = [(-w / 2, -h * math.sin(a), 0), (w / 2, -h * math.sin(a), 0), (w / 2, 0, h * math.cos(a)),
             (-w / 2, 0, h * math.cos(a))]
    m.quad(front, reg, WHITE, "atlas", M)
    back = [(w / 2, h * math.sin(a), 0), (-w / 2, h * math.sin(a), 0), (-w / 2, 0, h * math.cos(a)),
            (w / 2, 0, h * math.cos(a))]
    m.quad(back, "kraft", C("c8a070"), "atlas", M)


def lk_tin(m, M, r=0.07, h=0.05):
    """A round Lebkuchen tin: red sides with a gold rim, the printed lid on top."""
    n = seg(12, 8)
    m.cyl(r, r, h, n, "sw_gloss", M, C("8e1b1d"), "glaze", caps=False)
    m.cyl(r + 0.002, r + 0.002, 0.012, n, "sw_metal", M @ T(0, 0, h - 0.01), C("d8b048"), caps=False)
    m.disc(r + 0.002, n, "lk_tin", M @ T(0, 0, h + 0.002), WHITE, "glaze")


def gift_box(m, M, w, d, h, col, ribbon=C("b0282a")):
    """A card box with a ribbon cross and a flat bow."""
    m.box((w, d, h), M @ T(0, 0, h / 2), "kraft", col, skip=("nz",))
    m.box((w + 0.002, 0.012, h + 0.002), M @ T(0, 0, h / 2), "sw_satin", ribbon, skip=("nz",))
    m.box((0.012, d + 0.002, h + 0.002), M @ T(0, 0, h / 2), "sw_satin", ribbon, skip=("nz",))
    if not vlib.lite():
        for a in (0.6, -0.6):
            m.box((0.04, 0.014, 0.004), M @ T(0, 0, h + 0.004, rz=a), "sw_satin", ribbon)


# ------------------------------------------------------------------ Lebkuchen
def lebkuchen_heart(m, M, size, k):
    poly = heart_poly(size, 18 if size >= 0.14 and not vlib.lite() else (12 if not vlib.lite() else 10))
    reg = f"lebkuchen_{k % 6}"
    dough = vlib.R(reg, sub=(0.0, 0.0, 0.08, 0.08))
    # heart polygon spans x +-size/2, y from -size*0.53 to +size*0.36 roughly; face UVs by bbox. Lite drops
    # the back face (every heart faces the visitor: hanging, leaning on the board or lying in the basket)
    m.extrude(poly, 0.012, M, reg, dough, WHITE, "glaze", bevel=0.0 if (vlib.lite() or size < 0.17) else 0.003,
              back_region=dough, back=not vlib.lite())


HEART_TEXTS = [  # the icing on the six heart faces (vendor_atlas: lebkuchen_0..5)
    ("Ich liebe Dich", "“Ich liebe Dich” (I love you), piped in white icing inside a scalloped border, with sugar flowers."),
    ("Frohe Weihnachten", "“Frohe Weihnachten” (Merry Christmas), white lettering in a yellow piped border."),
    ("Für Dich", "“Für Dich” (for you), white icing in a pink scalloped border, with sugar roses."),
    ("Schatz", "“Schatz” (sweetheart), white icing in a blue piped border."),
    ("Prost!", "“Prost!” (cheers!), in yellow icing: a heart for the Glühwein crowd."),
    ("Nachtmarkt", "“Nachtmarkt” (night market), in white icing in a pink border: a souvenir of the evening."),
]


@contextmanager
def heart_item(s, n, x, size, k, base=None):
    """act_heart_<n>: a hanging heart (origin at the ribbon's knot on the rod) or, with `base`, one leaning
    on the display board (origin at its lowest point). k picks the icing face (lebkuchen_<k % 6>)."""
    text, detail = HEART_TEXTS[k % 6]
    cm = round(size * 100)
    origin = base if base else (x, ROD_Y, ROD_Z)
    label = f"Lebkuchen heart “{text}”"
    where = ("Leaning on the display board, ribbon tucked behind." if base else
             "It hangs on a ribbon, to wear around your neck.")
    with item(s, f"act_heart_{n}", origin, label, f"{detail} About {cm} cm across. {where}",
              pivot="base" if base else "hang", icing=text, size_cm=cm) as hm:
        yield hm


def lebkuchen():
    s = vlib.PropSet("prop_deco_lebkuchen", "slot_counter", "deco-lebkuchen")
    m = s.static
    rod(m, -1.1, 1.1)
    ribbons = [C("b0282a"), C("2a5aa8"), C("2a7a3a"), C("d8b048")]
    xs = [-0.98, -0.8, -0.62, -0.46, -0.3, 0.3, 0.46, 0.62, 0.8, 0.98]
    for i, x in enumerate(xs):
        size = rng.choice([0.14, 0.17, 0.2, 0.24]) if abs(x) > 0.5 else rng.choice([0.12, 0.15])
        drop = rng.uniform(0.18, 0.42)
        jx, ry = rng.uniform(-0.004, 0.004), rng.uniform(-0.2, 0.2)
        with heart_item(s, i, x, size, i) as hm:
            p = hang_item(hm, x, drop, ribbons[i % 4], jx=jx)
            # heart hangs facing the front (-Y): its local XY plane -> world XZ, face toward -Y
            M = T(p.x, p.y + 0.006, p.z - size * 0.36 + 0.01, rx=math.pi / 2, ry=ry) @ T(0, 0, -0.006)
            lebkuchen_heart(hm, M, size, i)
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
    # two short hearts in the middle of the rod
    for i, x in enumerate((-0.14, 0.14)):
        with heart_item(s, 10 + i, x, 0.12, 7 + i) as hm:
            p = hang_item(hm, x, 0.12, ribbons[(i + 1) % 4], jx=irng("lk", i).uniform(-0.004, 0.004))
            lebkuchen_heart(hm, T(p.x, p.y + 0.006, p.z - 0.12 * 0.36 + 0.01, rx=math.pi / 2) @ T(0, 0, -0.006),
                            0.12, 7 + i)
    # a slanted display board along the back with big hearts leaning on it (each one an item, its origin
    # under the heart's lowest point on the board's foot rail)
    m.box((0.9, 0.012, 0.16), T(0.1, 0.2, 0.08, rx=-0.25), vlib.RW("wood"), C("7a5230"))
    m.box((0.9, 0.03, 0.02), T(0.1, 0.14, 0.01), vlib.RW("wood"), C("7a5230"))
    for k in range(5):
        size = 0.15 if k % 2 else 0.17
        M = T(-0.18 + k * 0.165, 0.175 - 0.006, 0.02 + 0.09, rx=math.pi / 2 - 0.25,
              rz=irng("lkb", k).uniform(-0.08, 0.08)) @ T(0, 0, -0.012)
        low = min((M @ Vector((px, py, pz)) for px, py in heart_poly(size, 18) for pz in (0.0, 0.012)),
                  key=lambda v: v.z)
        with heart_item(s, 12 + k, None, size, k + 3, base=(low.x, low.y, low.z)) as hm:
            lebkuchen_heart(hm, M, size, k + 3)
    # stacks of Elisenlebkuchen tins and ribboned gift boxes at the ends
    for k, (x, y) in enumerate(((0.95, -0.12), (0.95, 0.08), (-0.98, 0.14))):
        for j in range(3 - (k == 2)):
            lk_tin(m, T(x, y, j * 0.052, rz=drng.uniform(0, 6)), r=0.07 - j * 0.004)
    for j, (w, d, h, col) in enumerate(((0.2, 0.14, 0.06, C("e8dcc0")), (0.16, 0.12, 0.05, C("c8a878")),
                                        (0.12, 0.1, 0.04, C("f0e6d0")))):
        gift_box(m, T(-0.98, -0.1, sum((0.06, 0.05, 0.04)[:j]), rz=0.1 * (j - 1)), w, d, h, col,
                 ribbon=(C("b0282a"), C("2a6a3a"), C("d8b048"))[j])
    for k, (x, y) in enumerate(((-0.6, -0.2), (0.1, -0.17), (0.62, -0.17), (0.95, -0.21))):
        price_tag(m, T(x, y, 0), (0, 5, 1, 3)[k])
    s.finish()
    return s


# ------------------------------------------------------------------ Gebrannte Mandeln
def almond_heap(m, M, r, h, col=WHITE, k=None):
    k = k or seg(8, 5)
    prof = [(r, 0.0), (r * 0.85, h * 0.55), (r * 0.35, h * 0.95), (0.0, h * 1.02)]
    if vlib.lite():
        prof = [prof[0], prof[1], prof[3]]
    m.lathe(prof, k, "almonds", M, col, "glaze", v_by="z")


MANDEL_KINDS = [  # (name, tag text, colour of the heap)
    ("gebrannte Mandeln", "Gebrannte Mandeln: almonds turned in bubbling sugar, vanilla and cinnamon until they crackle, still warm.", "f4e0d0"),
    ("Zimtmandeln", "Zimtmandeln: the same almonds with an extra coat of cinnamon sugar.", "e8c8a8"),
    ("gebrannte Cashews", "Gebrannte Cashews: cashews in the same crackling sugar coat.", "f6e6cc"),
    ("Schokomandeln", "Schokomandeln: roasted almonds dipped in dark chocolate.", "8a5a3a"),
    ("gebrannte Erdnüsse", "Gebrannte Erdnüsse: peanuts in a crackling sugar coat, the cheapest bag on the counter.", "e8c890"),
]


def mandeln():
    s = vlib.PropSet("prop_deco_mandeln", "slot_counter", "deco-mandeln")
    m = s.static
    # the copper roasting kettle on its stand with a stirring paddle
    Mk = T(-0.72, 0.0, 0)
    n = seg(20, 10) if not vlib.lite() else 8      # 8 sides: the lite kettle keeps the full one's width
    m.lathe([(0.2, 0.0), (0.21, 0.01), (0.21, 0.1), (0.2, 0.11)], n, vlib.RW("iron"), Mk, WHITE)
    m.lathe([(0.0, 0.1), (0.12, 0.1), (0.19, 0.14), (0.225, 0.22), (0.232, 0.232), (0.222, 0.23), (0.182, 0.15),
             (0.11, 0.115), (0.0, 0.112)], n, vlib.RW("copper"), Mk, WHITE)
    almond_heap(m, Mk @ T(0, 0, 0.12), 0.18, 0.085, C("f4e4d4"), k=seg(14, 8))
    m.box((0.36, 0.03, 0.01), Mk @ T(0, 0, 0.3, rz=0.6), "steel", WHITE)
    m.cyl(0.008, 0.008, 0.3, 8, "steel", Mk @ T(0, 0, 0.12), WHITE)
    m.cyl(0.02, 0.02, 0.02, 10, "brass", Mk @ T(0, 0, 0.42), WHITE)
    # a rack of paper cones filled with almonds
    Mr = T(0.15, 0.02, 0)
    m.box((0.62, 0.2, 0.02), Mr @ T(0, 0, 0.11), vlib.RW("wood"), C("a07448"))
    for sx in (-1, 1):
        m.box((0.02, 0.2, 0.11), Mr @ T(sx * 0.3, 0, 0.055), vlib.RW("wood"), C("a07448"))
    # each cone in the rack is an item (round 4), the same ten in the lite set (six sides there)
    for k in range(10):
        cx, cy = -0.24 + (k % 5) * 0.12, -0.05 + (k // 5) * 0.1
        Mc = Mr @ T(cx, cy, 0.0, rz=irng("md", k).uniform(0, 6))
        o = Mc.translation
        nut, grams = MANDEL_KINDS[k % len(MANDEL_KINDS)], (100, 200)[k // 5]
        with item(s, f"act_cone_{k}", (o.x, o.y, 0.0), f"Paper cone of {nut[0]}",
                  f"{nut[1]} {grams} g in a paper cone, {('3,50 €', '6 €')[k // 5]}.",
                  grams=grams) as cm:
            cm.lathe([(0.004, 0.0), (0.042, 0.2), (0.044, 0.205)], seg(8, 6), "cone_paper", Mc, jit(WHITE, 0.04),
                     "atlas")
            if not vlib.lite():
                cm.lathe([(0.0405, 0.2), (0.004, 0.02)], seg(8, 6), "paper", Mc, C("e8e0d0"))
            almond_heap(cm, Mc @ T(0, 0, 0.19), 0.042, 0.045, jit(C(nut[2]), 0.08), k=seg(8, 6))
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
    # between the kettle and the rack: a pile of filled striped bags, a flat crate of cones lying ready
    for k in range(7 if not vlib.lite() else 3):
        row = 0 if k < 4 else 1
        j = k if k < 4 else k - 4
        m.box((0.075, 0.045, 0.1), T(-0.42 + j * 0.08 + row * 0.04, 0.14 - row * 0.005, row * 0.1 + 0.05,
                                      rz=drng.uniform(-0.1, 0.1), rx=0.06 if row else 0.0), "cone_paper", WHITE,
              skip=("nz",))
    G.crate(m, T(-0.32, -0.1, 0), 0.26, 0.16, 0.05, C("b48c5c"), slats=1)
    for k in range(4 if not vlib.lite() else 2):
        Mc = T(-0.418 + k * 0.064, -0.1, 0.036, rx=-(math.pi / 2 - 0.1), ry=0.06 * (k - 1.5)) @ T(0, 0, -0.08)
        m.lathe([(0.004, 0.0), (0.034, 0.16)], seg(7, 5), "cone_paper", Mc, jit(WHITE, 0.04), "atlas")
    for k, (x, y) in enumerate(((-0.32, -0.21), (0.66, -0.21), (0.17, -0.225))):
        price_tag(m, T(x, y + 0.012, 0.0 if k != 2 else 0.002), (1, 6, 1)[k])
    s.finish()
    return s


# ------------------------------------------------------------------ Kerzen
CANDLE_COLS = ["b0282a", "f2ead8", "2a6a3a", "d8b048", "2a4a8a", "7a3a7a", "e8d0a0", "c0562a", "f4f0e8", "5a8ab0"]
CANDLE_NAMES = ["red", "ivory", "fir-green", "gold", "royal blue", "plum", "cream", "rust-orange", "white", "sky-blue"]


def candle(m, M, r, h, col, lit=False, kind="pillar", n=None):
    n = n or seg(8, 5)
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
    # ten columns of three candles (one per riser) every 15 cm; every third column's candles are items
    # (round 4: twelve in all, the same in lite, which keeps only those columns)
    n_item = 0
    for gi in range(10):
        x = -0.85 + 0.15 * gi
        is_item = gi % 3 == 0
        if vlib.lite() and not is_item:
            continue
        for tier in range(3):
            k = gi * 3 + tier
            g = irng("kz", k)
            dz, dy = ((0.02, -0.1), (0.09, 0.05), (0.16, 0.17))[tier]
            kind = g.choice(["pillar", "pillar", "beeswax", "pillar", "short"])
            r = g.uniform(0.022, 0.045) if kind != "short" else g.uniform(0.035, 0.05)
            h = g.uniform(0.07, 0.22) if kind != "short" else g.uniform(0.05, 0.08)
            ci = g.randrange(len(CANDLE_COLS))
            col = C(CANDLE_COLS[ci]) if kind != "beeswax" else C("e8b050")
            pos = (x, dy + g.uniform(-0.02, 0.02), dz)
            lit = k % 7 == 3
            if not is_item:
                candle(m, T(*pos), r, h, jit(col, 0.05), lit=lit, kind=kind)
                continue
            cname = "honey beeswax" if kind == "beeswax" else CANDLE_NAMES[ci]
            what = {"pillar": "pillar candle", "short": "block candle", "beeswax": "rolled beeswax candle"}[kind]
            extra = {"pillar": "Hand-dipped, layer on layer, in the Kerzenzieher's vat.",
                     "short": "A short, wide block for a windowsill; burns for about 40 hours.",
                     "beeswax": "Rolled from a honeycomb sheet of beeswax; it smells of honey."}[kind]
            label = f"{cname[0].upper() + cname[1:]} {what}"
            detail = (f"{label}, {round(h * 100)} cm tall, {round(r * 200)} cm across. {extra}"
                      f"{' Lit, to show the flame.' if lit else ''}")
            with item(s, f"act_candle_{n_item}", pos, label, detail, colour=cname, lit=lit) as cm:
                candle(cm, T(*pos), r, h, jit(col, 0.05), lit=lit, kind=kind, n=seg(8, 6))
            n_item += 1
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
    # a flat basket of rolled beeswax candles at the right end, and price tags
    G.crate(m, T(0.95, -0.145, 0), 0.22, 0.13, 0.04, C("b48c5c"), slats=1)
    for k in range(8 if not vlib.lite() else 3):
        layer, j = divmod(k, 4)
        m.cyl(0.012, 0.012, 0.19, seg(8, 5), "honeycomb", T(0.855, -0.185 + j * 0.026 + layer * 0.013,
                                                           0.022 + layer * 0.022, ry=math.pi / 2), C("e8b050"))
    # candle boxes: an open white card box of dinner candles at the left end with its lid leaning behind it,
    # and tied gift boxes of tealights stacked along the front of the risers
    Mb = T(-0.945, -0.08, 0, rz=0.05)
    m.box((0.1, 0.2, 0.04), Mb @ T(0, 0, 0.02), "paper", C("f4f0e6"), skip=("nz",))
    m.box((0.1, 0.008, 0.2), Mb @ T(0.0, 0.135, 0.108, rx=-0.18), "paper", C("ece6d8"))
    for k in range(4 if not vlib.lite() else 2):
        col = C(CANDLE_COLS[(k * 3) % len(CANDLE_COLS)])
        m.cyl(0.0105, 0.0105, 0.19, seg(8, 5), vlib.RW("wax"), Mb @ T(-0.033 + k * 0.022, -0.095, 0.044,
              rx=-math.pi / 2), jit(col, 0.04))
    for k, (x, dz) in enumerate(((-0.42, 0.0), (-0.42, 0.036), (0.32, 0.0), (0.42, 0.0), (0.37, 0.036))):
        if vlib.lite() and dz:
            continue
        gift_box(m, T(x, -0.212, dz, rz=drng.uniform(-0.06, 0.06)), 0.09, 0.055, 0.034,
                 C(("f2ead8", "b0282a", "2a5a3a", "f2ead8", "d8b048")[k]),
                 ribbon=C(("b0282a", "d8b048", "d8b048", "2a5a3a", "b0282a")[k]))
    for k, (x, y) in enumerate(((-0.6, -0.215), (0.2, -0.215), (0.95, 0.02))):
        price_tag(m, T(x, y, 0.0), (2, 2, 3)[k])
    s.finish()
    return s


# ------------------------------------------------------------------ Holzspielzeug
def nutcracker(m, M, coat=C("a8181c"), trousers=C("f2ead8"), hat=C("141414"), s=1.0):
    S = M @ Matrix.Diagonal((s, s, s, 1))
    n = seg(6, 5)
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
    for k in range(3):                      # three cars in lite too: the train is an item (same size)
        Mw = M @ T(k * 0.13, 0, 0)
        body = cols[k]
        if k == 0:
            m.box((0.11, 0.06, 0.05), Mw @ T(0, 0, 0.035), "sw_gloss", body, "glaze")
            m.cyl(0.026, 0.026, 0.07, 8, "sw_gloss", Mw @ T(-0.065, 0, 0.045, ry=math.pi / 2), C("141414"), "glaze")
            m.box((0.045, 0.062, 0.05), Mw @ T(0.035, 0, 0.08), "sw_gloss", body, "glaze")
            m.cyl(0.01, 0.014, 0.035, 6, "sw_gloss", Mw @ T(-0.04, 0, 0.07), C("141414"), "glaze")
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
    n = seg(6, 5)
    prof = [(0.0, 0.0), (0.035, 0.035), (0.033, 0.045), (0.006, 0.05), (0.006, 0.08), (0.0, 0.082)]
    m.lathe(prof if not vlib.lite() else [prof[0], prof[1], prof[3], prof[4], prof[5]], n, "sw_gloss", M, col, "glaze")
    if not vlib.lite():
        m.cyl(0.0352, 0.0352, 0.006, n, "sw_gloss", M @ T(0, 0, 0.036), C("f2ead8"), "glaze", caps=False)   # stripe


def pyramid(s, x, y):
    """A small Weihnachtspyramide: turned posts, two tiers of figures, a vane wheel on top (rot_pyramid)."""
    m = s.static
    n = seg(8, 6)
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
    nv = 5 if not vlib.lite() else 4
    for k in range(nv):
        a = TWO_PI * k / nv
        rot.box((0.07, 0.022, 0.002), T(0.045 * math.cos(a), 0.045 * math.sin(a), 0.41, rz=a, rx=0.5), vlib.RW("wood"),
                C("d8b078"))


def spanbaum(m, M, h=0.12, col=C("e8d0a0")):
    """Erzgebirge shaving tree (Spanbaum): a curled-shaving cone on a turned stem and a small foot."""
    n = seg(6, 5)
    m.cyl(0.005, 0.005, 0.03, 4, vlib.RW("wood"), M, C("b8864e"), caps=False)
    prof = [(0.036, 0.03), (0.021, 0.03 + h * 0.42), (0.026, 0.03 + h * 0.46), (0.0, 0.03 + h)]
    m.lathe(prof if not vlib.lite() else [prof[0], prof[3]], n, "straw", M, col, cap0=not vlib.lite())


def spielzeug():
    s = vlib.PropSet("prop_deco_spielzeug", "slot_counter", "deco-spielzeug")
    m = s.static
    # a stepped riser along the back of the left half, with a row of shaving trees on it
    m.box((1.22, 0.1, 0.07), T(-0.4, 0.18, 0.035), vlib.RW("wood"), C("8a5a34"), skip=("nz",))
    for k, x in enumerate((-0.94, -0.78, -0.62, -0.3, -0.14, 0.02)):
        if vlib.lite() and k != 2:
            continue
        spanbaum(m, T(x, 0.18, 0.07, rz=k), h=0.1 + (k % 3) * 0.03, col=C(["e8d0a0", "d8e0c0", "e0c8a0"][k % 3]))
    # round 4: the nutcrackers, the train, the spinning tops and the rocking horse are items (all of them in
    # lite too)
    for k, (x, y, rz, coat, trousers, hat, sc, who) in enumerate((
            (-0.93, 0.02, 0.0, "a8181c", "f2ead8", "141414", 1.0, "a king's guard in a red coat"),
            (-0.79, 0.05, 0.2, "1f3a78", "141414", "a8181c", 0.85, "a soldier in a blue coat and red shako"),
            (-0.66, -0.02, -0.15, "2a6a3a", "f2ead8", "141414", 0.7, "a forester in a green coat"))):
        with item(s, f"act_nutcracker_{k}", (x, y, 0.0), "Erzgebirge nutcracker",
                  f"A turned and painted nutcracker from the Erzgebirge: {who}, {round(34 * sc)} cm tall. "
                  "Lift the lever at his back and he cracks a walnut.") as tm:
            nutcracker(tm, T(x, y, 0, rz=rz), C(coat), C(trousers), C(hat), s=sc)
    with item(s, "act_train_0", (-0.46 + 0.13, -0.13, 0.0), "Wooden toy train",
              "A painted wooden train: a red engine with a black boiler and two wagons loaded with blocks.") as tm:
        train(tm, T(-0.46, -0.13, 0))
    for k, x in enumerate((-0.05, 0.04, 0.13)):
        with item(s, f"act_top_{k}", (x, -0.14, 0.0), "Spinning top",
                  f"A turned wooden spinning top in {['red', 'blue', 'yellow'][k]} lacquer with a cream stripe.") as tm:
            top(tm, T(x, -0.14, 0), C(["b0282a", "2a4a8a", "d8b048"][k]))
    # a tower of painted blocks
    for k in range(6 if not vlib.lite() else 3):
        m.box((0.04, 0.04, 0.04), T(0.25 + (k % 3) * 0.045 - (k // 3) * 0.02, 0.06, 0.02 + (k // 3) * 0.04,
                                    rz=drng.uniform(-0.2, 0.2)), vlib.RW("wood"), C(CANDLE_COLS[k]))
    pyramid(s, 0.55, 0.05)
    # a second little tower of blocks with letters' colours, three plywood stars standing at the front, tags
    for k in range(4 if not vlib.lite() else 2):
        m.box((0.04, 0.04, 0.04), T(0.3 + (k % 2) * 0.045, -0.13, 0.02 + (k // 2) * 0.04, rz=drng.uniform(-0.25, 0.25)),
              vlib.RW("wood"), C(CANDLE_COLS[(k + 3) % len(CANDLE_COLS)]))
    for k in range(3 if not vlib.lite() else 1):
        m.extrude(star_poly(0.05, 0.022, 5), 0.008, T(0.62 + k * 0.1, -0.17, 0.05, rx=math.pi / 2 - 0.1, rz=0.1 * (k - 1)),
                  vlib.RW("wood"), vlib.RW("wood"), C(["d8b078", "b0282a", "c8a070"][k]), back=False)
    for k, (x, y) in enumerate(((-0.93, -0.2), (-0.3, -0.21), (0.13, -0.215))):
        price_tag(m, T(x, y, 0), (3, 3, 7)[k])
    # a small rocking horse (an item: origin under the middle of its rockers)
    Mh = T(0.86, -0.02, 0)
    k = 5 if not vlib.lite() else 3
    rh = s.node("act_rockinghorse_0", (0.86, -0.02, 0.0))
    s.item("act_rockinghorse_0", "Little rocking horse", "deco", pivot="base",
           detail="A little white rocking horse with a red saddle on curved rockers. Give it a push.")
    m, m_set = rh, m
    Mh = T(0, 0, -0.014)          # round 3's horse floated 14 mm: its rockers now touch the counter
    for sy in (-1, 1):
        pts = [(-0.12 + 0.24 * i / (k - 1), sy * 0.03, 0.02 + 0.03 * (2 * i / (k - 1) - 1) ** 2) for i in range(k)]
        m.tube(pts, 0.006, 4, vlib.RW("wood"), Mh, C("7a4a28"))
    m.box((0.14, 0.05, 0.05), Mh @ T(0, 0, 0.1), "sw_gloss", C("f2ead8"), "glaze")
    m.box((0.03, 0.035, 0.08), Mh @ T(0.08, 0, 0.14, ry=-0.4), "sw_gloss", C("f2ead8"), "glaze")
    m.box((0.06, 0.03, 0.03), Mh @ T(0.11, 0, 0.18), "sw_gloss", C("f2ead8"), "glaze")
    for sx in (-0.05, 0.05):
        m.box((0.015, 0.05, 0.07), Mh @ T(sx, 0, 0.055), "sw_gloss", C("f2ead8"), "glaze")
    m.box((0.06, 0.052, 0.012), Mh @ T(0, 0, 0.128), "sw_gloss", C("a8181c"), "glaze")
    m = m_set
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
BAUBLE_NAMES = ["deep red", "gold", "midnight blue", "snow white", "fir green", "plum", "silver", "amber"]


def bauble(m, M, r, col, shiny=True, cap=True, n=8, rings=4, upper=False, n_lo=5):
    """A glass bauble hanging from its cap (origin at the top of the cap). upper: only the top half and a
    little more, for baubles sitting in an egg crate. n_lo: the fewest sides in lite (6 for items, whose
    lite bounds must match the full ones)."""
    n, rings = seg(n, n_lo), seg(rings, 2)
    reg, mat = ("sw_metal_polish", "atlas") if shiny else ("sw_satin", "glaze")
    if upper:
        prof = [(r * math.cos(a), r * math.sin(a)) for a in (-0.3, 0.75)] + [(0.0, r)]
        m.lathe(prof, n, reg, M @ T(0, 0, -r), col, mat)
    else:
        m.sphere(r, n, rings, reg, M @ T(0, 0, -r), col, mat)
    if cap:
        m.cyl(r * 0.28, r * 0.25, r * 0.28, (6 if not upper else 4) if not vlib.lite() else 4, "sw_metal",
              M @ T(0, 0, -0.004), C("d8c080"), caps=False)


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
        for j in range(2 if not vlib.lite() else 0):
            a = TWO_PI * j / 2 + k * 0.9 - 0.9
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
    xs = [-0.95, -0.84, -0.73, -0.62, -0.51, -0.4, 0.4, 0.51, 0.62, 0.73, 0.84, 0.95]
    # round 4: every hanging piece is an item, act_bauble_<i>, origin at its knot on the rod
    for i, x in enumerate(xs):
        drop = rng.uniform(0.12, 0.4)
        jx = rng.uniform(-0.004, 0.004)
        if i % 4 == 3:
            label, detail = "Straw star", ("A straw star (Strohstern) of two crossed layers of split straw, bound with "
                                          "thread: the oldest tree ornament on the stall.")
        elif i % 4 == 1:
            label, detail = "Glass icicle", "A blown-glass icicle, clear and tapering to a fine point, with a gold cap."
        else:
            cname = BAUBLE_NAMES[i % len(BAUBLE_NAMES)]
            label = f"{cname[0].upper() + cname[1:]} glass bauble"
            detail = (f"A mouth-blown glass bauble, {cname}, {'mirror-silvered inside' if i % 3 != 2 else 'satin matt'}, "
                      "with a gold cap: made in Lauscha in Thuringia, where glass baubles were first blown. 5 €.")
        with item(s, f"act_bauble_{i}", (x, ROD_Y, ROD_Z), label, detail, pivot="hang") as bm:
            p = hang_item(bm, x, drop, C("d8b048"), 0.001, jx=jx)
            if i % 4 == 3:
                # straw star: two crossed layers
                Ms = T(p.x, p.y, p.z - 0.06, rx=math.pi / 2, ry=rng.uniform(-0.3, 0.3))
                for k in range(2 if not vlib.lite() else 1):
                    sp = star_poly(0.06, 0.012, 4, rot=k * math.pi / 4)
                    bm.extrude(sp, 0.002, Ms @ T(0, 0, k * 0.002), "straw", "straw", C("e8c880"), back=not vlib.lite())
            elif i % 4 == 1:
                # glass icicle
                bm.lathe([(0.0, 0.0), (0.009, -0.02), (0.006, -0.1), (0.0, -0.14)], seg(6, 5), "sw_vgloss",
                         T(p.x, p.y, p.z), C("e8f0f4"), "glass")
                bm.cyl(0.004, 0.004, 0.008, 6 if not vlib.lite() else 4, "sw_metal", T(p.x, p.y, p.z - 0.002),
                       C("d8c080"), caps=False)
            else:
                bauble(bm, T(p.x, p.y, p.z), rng.choice([0.03, 0.035, 0.045, 0.05]),
                       C(BAUBLE_COLS[i % len(BAUBLE_COLS)]), shiny=i % 3 != 2, n=8, rings=4, n_lo=6)
    # egg-crate trays of baubles on the counter (only their tops show above the crate)
    for t, (tx, cols) in enumerate(((-0.62, BAUBLE_COLS[:4]), (-0.14, BAUBLE_COLS[4:] + ["a8161d", "d8b048"]),
                                    (0.34, ["d8b048", "c0c4c8", "a8161d", "e8e4dc"]))):
        Mt = T(tx, -0.02, 0)
        m.box((0.44, 0.3, 0.035), Mt @ T(0, 0, 0.0175), "kraft", C("d8c8a8"), skip=("nz",))
        for k in range(12):
            if vlib.lite() and k not in (0, 3, 5, 6, 9):
                continue
            cx, cy = -0.165 + (k % 4) * 0.11, -0.1 + (k // 4) * 0.1
            r = 0.035
            bauble(m, Mt @ T(cx, cy, 0.035 + 2 * r - 0.008, rx=drng.uniform(-0.4, 0.4), ry=drng.uniform(-0.4, 0.4)),
                   r, C(cols[(k + t) % len(cols)]), shiny=(k % 5 != 2), n=6, cap=False, upper=True)
        # the carton's lid, open and leaning against the back of the box
        m.box((0.44, 0.004, 0.14), Mt @ T(0, 0.155, 0.1, rx=-0.2), "kraft", C("d0bf9c"))
    # a decorated tabletop tree, two loose baubles on their sides and a glass tree-top spire
    tabletop_tree(m, T(0.96, 0.08, 0))
    for j, (x, y, r, col, a, cname) in enumerate(((0.66, -0.16, 0.04, "a8161d", 0.4, "deep red"),
                                                  (0.9, -0.17, 0.034, "d8b048", 2.2, "gold"),
                                                  (-0.92, -0.17, 0.03, "1d3a78", 1.0, "midnight blue"))):
        M = T(x, y, r * (1 + math.cos(1.2)), rx=1.2, rz=a)
        c = M @ Vector((0, 0, -r))                      # the ball's centre: it rests on the counter under it
        with item(s, f"act_bauble_{12 + j}", (c.x, c.y, 0.0), f"{cname[0].upper() + cname[1:]} glass bauble",
                  f"A mouth-blown Lauscha glass bauble, {cname}, lying on the counter where a customer put it down. "
                  "5 €.") as bm:
            bauble(bm, M, r, C(col), n=8, rings=4, n_lo=6)
    for k, (x, y) in enumerate(((-0.62, -0.21), (0.34, -0.21))):
        price_tag(m, T(x, y + 0.01, 0), 4)
    Mp = T(0.76, 0.06, 0)
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.02), (0.012, 0.04), (0.035, 0.09), (0.012, 0.13), (0.004, 0.3),
             (0.0, 0.31)], seg(8, 6), "sw_metal_polish", Mp, C("a8161d"))
    s.finish()
    return s


# ------------------------------------------------------------------ Käse
def cheese_wheel(m, M, r, h, cut=0.0, rind=C("ffffff"), wax=None, n_lo=10):
    """A wheel; with cut (radians) a wedge is missing at the front showing the paste. n_lo: fewest sides in
    lite (12 for items, so the lite wheel keeps the full one's bounds)."""
    n = seg(28, n_lo) if n_lo <= 6 else (max(n_lo, int(round(28 * 0.34))) if vlib.lite() else 28)
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
    # round 4: the wheels are items (origin at the middle of each wheel's underside)
    def wheel(n, at, label, detail, r, h, rz=0.0, **kw):
        with item(s, f"act_cheese_{n}", at, label, detail, **({"cut": True} if kw.get("cut") else {})) as cm:
            cheese_wheel(cm, T(*at, rz=rz), r, h, n_lo=12, **kw)
    wheel(0, (-0.78, 0.02, 0.0), "Allgäuer Bergkäse",
          "Allgäuer Bergkäse, a whole 44 cm wheel aged twelve months, opened at the front: nutty, a little "
          "crystalline. Cut to order, 100 g for 3,50 €.", 0.22, 0.11, cut=0.9)
    wheel(1, (-0.3, 0.1, 0.0), "Butterkäse",
          "Butterkäse: mild, soft and creamy, the cheese every child at the counter asks to taste.", 0.14, 0.09)
    wheel(2, (-0.3, 0.1, 0.09), "Tilsiter", "Tilsiter: a washed golden rind and a sharp, spicy paste.", 0.12, 0.08,
          rz=0.5, rind=C("e0c080"))
    wheel(3, (-0.3, 0.1, 0.17), "Edamer in red wax", "A small Edamer sealed in red wax, mild and firm.", 0.1, 0.07,
          rz=1.1, wax=C("a8161d"))
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
            with item(s, f"act_cheese_{7 + k}", (cx, cy, 0.06 - 0.055 * 0.8), "Mini Gouda in red wax",
                      "A round mini Gouda in red wax, about 400 g: a cheese to take home as a present.") as cm:
                cm.sphere(0.055, seg(14, 8), seg(8, 5), "sw_gloss", T(cx, cy, 0.06), C("a8161d"), scale=(1, 1, 0.8))
        else:
            with item(s, f"act_cheese_{7 + k}", (cx, cy, 0.015), "Räucherkäse",
                      "A small smoked cheese (Räucherkäse) with a brown, beech-smoked rind.") as cm:
                cheese_wheel(cm, T(cx, cy, 0.015), 0.055, 0.05, rind=C("a86a2a"), n_lo=12)
    # a tower of washed-rind wheels at the left end behind the big cut wheel
    for j, (nm, dt) in enumerate((("Weißlacker", "Weißlacker: an Allgäu beer cheese, soft, salty and strong."),
                                  ("Romadur", "Romadur: a washed-rind soft cheese, milder than it smells."),
                                  ("Limburger", "Limburger: a ripe washed-rind cheese with a big smell and a mild heart."))):
        wheel(4 + j, (-0.98, 0.15, j * 0.075), nm, dt, 0.09 - j * 0.006, 0.07, rz=j * 0.7,
              rind=C(["c8904a", "d8b070", "b87a3a"][j]))
    # a slate of tasting cubes with toothpicks, and wrapped wedges in a basket at the front
    m.box((0.2, 0.12, 0.008), T(-0.5, -0.17, 0.004, rz=0.05), "sw_matte", C("2a2c2e"))
    for k in range(8 if not vlib.lite() else 4):
        x, y = -0.57 + (k % 4) * 0.045, -0.19 + (k // 4) * 0.04
        m.box((0.02, 0.02, 0.02), T(x, y, 0.018, rz=drng.uniform(0, 1)), "cheese_cut", C("f4e0a0"))
        if not vlib.lite():
            m.cyl(0.0012, 0.0012, 0.045, 3, "sw_matte", T(x, y, 0.02, rx=0.15), C("e8d8b0"), caps=False)
    G.crate(m, T(0.18, 0.17, 0), 0.34, 0.12, 0.05, C("b48c5c"), slats=1)
    for k in range(4):
        Mw = T(0.06 + k * 0.08, 0.17, 0.028, rz=math.pi / 2 + 0.2 * (k - 1.5))
        m.extrude([(0.0, -0.035), (0.09, 0.0), (0.0, 0.035)], 0.035, Mw @ T(-0.045, 0, 0), "cheese_cut", "sw_gloss",
                  C(["f4e0a0", "e8c878", "f8ecc0", "e0c070"][k]))
    # the middle: wedges wrapped in wax paper (the paper folded up the rind, the cut face showing over it)
    # and a small round board with a piece of Bergkäse and a cheese knife
    for k, (x, y, z, rz, col) in enumerate(((-0.12, -0.1, 0.0, 1.35, "f0d890"), (-0.21, -0.17, 0.0, 0.25, "f6e8b8"),
                                            (0.03, -0.15, 0.025, -0.2, "e8c870"))):
        Mw = T(x, y, z, rz=rz) @ T(-0.05, 0, 0)
        m.extrude([(0.0, -0.036), (0.1, 0.0), (0.0, 0.036)], 0.046, Mw, "cheese_cut", "sw_gloss", C(col))
        m.extrude([(-0.003, -0.04), (0.106, 0.0), (-0.003, 0.04)], 0.032, Mw, "paper", "paper", C("efe6cc"))
    Mr = T(-0.075, 0.165, 0)
    m.cyl(0.075, 0.075, 0.018, seg(16, 8), vlib.RW("wood"), Mr, C("b88a5a"))
    cheese_wheel(m, Mr @ T(0.0, 0.0, 0.018, rz=2.4), 0.06, 0.055, cut=TWO_PI * 0.6, rind=C("c89a50"))
    m.box((0.12, 0.016, 0.0015), Mr @ T(0.02, -0.045, 0.02, rz=-0.5), "steel", WHITE)
    m.box((0.07, 0.016, 0.014), Mr @ T(0.105, -0.093, 0.026, rz=-0.5), vlib.RW("wood"), C("3a2414"))
    for k, (x, y) in enumerate(((-0.78, -0.225), (0.18, -0.215), (0.75, -0.2))):
        price_tag(m, T(x, y, 0 if k != 1 else 0.025), (1, 5, 3)[k])
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
    # round 4: the jars, the shakers and the folded crêpes are items. The jars wear plain kraft labels (round 3
    # reused the spice shelf's "Orangenschale" label, which a visitor reading the tag would find odd)
    with item(s, "act_jar_0", (0.34, 0.12, 0.0), "Jar of nut-nougat cream",
              "A big jar of nut-nougat cream (Nuss-Nougat-Creme), spread on with a palette knife: the most "
              "asked-for crêpe on the board.") as jm:
        G.jar(jm, T(0.34, 0.12, 0), "kraft", C("3a1a0a"), "sw_wet", h=0.1, r=0.04, lid=C("d8b048"), n_lo=6)
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.09), (0.02, 0.12), (0.0, 0.125)], seg(12, 5), "sw_vgloss", T(0.44, 0.12, 0),
            C("f0f4f4"), "glass")
    m.lathe([(0.0, 0.002), (0.027, 0.002), (0.027, 0.06), (0.0, 0.06)], seg(10, 5), "wax", T(0.44, 0.12, 0), C("fbfaf6"))
    m.lathe([(0.0, 0.0), (0.12, 0.0), (0.13, 0.012), (0.0, 0.006)], seg(20, 10), "ceramic", T(0.35, -0.1, 0),
            C("f4f0e8"), "glaze")
    for k, (nm, dt) in enumerate((("Crêpe mit Zucker und Zimt", "sugar and cinnamon, 3 €"),
                                  ("Crêpe mit Nuss-Nougat", "nut-nougat cream, 3,50 €"),
                                  ("Crêpe mit Apfelmus", "warm apple purée, 3,50 €"),
                                  ("Crêpe mit Zitrone und Zucker", "lemon juice and sugar, 3 €"))):
        tri = [(0.0, 0.0), (0.16, 0.0), (0.0, 0.16)]
        at = (0.3 + k * 0.012, -0.16 + k * 0.01, 0.012 + k * 0.006)
        with item(s, f"act_crepe_{k}", at, nm, f"A thin buttery crêpe folded in quarters, with {dt}.") as cm:
            cm.extrude(tri, 0.006, T(*at, rz=0.6 + k * 0.2), "crepe", "crepe", WHITE)
    # paper cones for crêpes to go, standing in a wire rack
    for k in range(5 if not vlib.lite() else 2):
        m.lathe([(0.004, 0.0), (0.04, 0.17)], seg(10, 5), "paper", T(0.72 + k * 0.06, 0.12, 0), C("f4f0e8"))
    # a bowl of bananas, a jar of apple purée, a stack of plates and a cup of wooden forks
    Mb = T(0.72, -0.1, 0)
    m.lathe([(0.0, 0.0), (0.07, 0.0), (0.12, 0.05), (0.125, 0.055), (0.115, 0.055), (0.065, 0.008), (0.0, 0.008)],
            seg(16, 8), "ceramic", Mb, C("2a4a8a"), "glaze")
    for k in range(4 if not vlib.lite() else 2):
        a = k * 0.5 - 0.7
        pts = [(-0.08, 0.0, 0.045), (-0.03, 0.02, 0.03), (0.03, 0.02, 0.03), (0.08, 0.0, 0.05)]
        m.tube(pts, 0.017, seg(6, 4), "sw_satin", Mb @ T(0, 0, k * 0.012, rz=a), C("e8c83a"),
               radii=[0.008, 0.017, 0.017, 0.007])
    with item(s, "act_jar_1", (0.53, 0.14, 0.0), "Jar of apple purée",
              "Homemade apple purée (Apfelmus) for the apple crêpes, a little cinnamon in it.") as jm:
        G.jar(jm, T(0.53, 0.14, 0), "kraft", C("d8b060"), "sw_wet", h=0.09, r=0.035, lid=C("b0282a"), n_lo=6)
    for k in range(6 if not vlib.lite() else 2):
        m.lathe([(0.0, k * 0.006), (0.1, k * 0.006), (0.11, k * 0.006 + 0.01)], seg(16, 8), "ceramic",
                T(0.98, -0.08, 0), C("f4f0e8"), "glaze")
    m.lathe([(0.0, 0.0), (0.032, 0.0), (0.034, 0.09), (0.0, 0.01)], seg(10, 6), "ceramic", T(0.54, 0.03, 0),
            C("b0282a"), "glaze")
    for k in range(6 if not vlib.lite() else 2):
        a = TWO_PI * k / 6
        m.box((0.008, 0.003, 0.11), T(0.54 + 0.012 * math.cos(a), 0.03 + 0.012 * math.sin(a), 0.085,
                                      rx=0.15 * math.sin(a), ry=-0.15 * math.cos(a)), vlib.RW("wood"), C("d8b890"))
    # front middle: a little board with sugar and cinnamon shakers and two lemon halves, and a stack of
    # paper napkins
    G.board(m, T(0.05, -0.165, 0, rz=0.04), 0.2, 0.1, 0.015, C("c49a6c"))
    for k, (x, col, cap) in enumerate(((-0.01, "f8f6f0", "c8c8c8"), (0.035, "8a4a22", "c8c8c8"))):
        nm, dt = (("Sugar shaker", "A glass shaker of fine sugar with a steel cap, for dusting the crêpes."),
                  ("Cinnamon shaker", "A glass shaker of ground cinnamon with a steel cap."))[k]
        with item(s, f"act_shaker_{k}", (x, -0.16, 0.015), nm, dt) as sm:
            sm.lathe([(0.0, 0.015), (0.02, 0.015), (0.021, 0.08), (0.0, 0.08)], seg(10, 6), "sw_vgloss",
                     T(x, -0.16, 0), C("f0f4f4"), "glass")
            sm.lathe([(0.0, 0.017), (0.019, 0.017), (0.019, 0.06), (0.0, 0.06)], seg(10, 6), "sw_matte",
                     T(x, -0.16, 0), C(col))
            sm.lathe([(0.021, 0.08), (0.021, 0.095), (0.012, 0.105), (0.0, 0.107)], seg(10, 6), "steel",
                     T(x, -0.16, 0), C(cap))
    for k in range(2):
        # lemon half lying cut face up on the board: a peel dome and a pale flesh disc
        Ml = T(0.1 + k * 0.05, -0.172 + k * 0.012, 0.015)
        m.lathe([(0.0, 0.0), (0.018, 0.004), (0.026, 0.015), (0.027, 0.024)], seg(10, 6), "sw_satin", Ml, C("e8c020"))
        m.disc(0.025, seg(10, 6), "sw_satin", Ml @ T(0, 0, 0.0238), C("f4eaa0"))
    for k in range(4 if not vlib.lite() else 1):
        m.box((0.09, 0.09, 0.004), T(-0.01, 0.18, 0.002 + k * 0.004, rz=0.06 * k), "paper", C("f6f2ea"))
    for k, (x, y) in enumerate(((-0.75, -0.235), (0.35, -0.215), (0.72, -0.225))):
        price_tag(m, T(x, y + 0.012, 0 if k else 0.1), (7, 3, 6)[k])
    s.finish()
    return s


# ------------------------------------------------------------------ Heiße Maroni
def chestnut(m, M, r=0.016, col=WHITE):
    """A roasted chestnut: flat pale base, rounded belly, a short pointed tip, flattened on one side
    (y 0.74). Six sides and three bands, smooth-shaded (about 40 triangles, half the old ribbed lathe)."""
    n = 5
    prof = [(0.62 * r, 0.0), (r, 0.62 * r), (0.6 * r, 1.45 * r), (0.0, 1.9 * r)]
    m.lathe(prof, n, "chestnut", M @ Matrix.Diagonal((1.0, 0.74, 1.0, 1.0)), col, "glaze", v_by="z", cap0=True)


def maroni():
    s = vlib.PropSet("prop_deco_maroni", "slot_counter", "deco-maroni")
    m = s.static
    # brazier drum with a fire door showing glowing coals; a perforated roasting pan on top
    Md = T(-0.7, 0.0, 0)
    n = seg(24, 12) if not vlib.lite() else 12
    m.lathe([(0.2, 0.0), (0.21, 0.01), (0.21, 0.2), (0.205, 0.21)], n, vlib.RW("iron"), Md, WHITE, arc=TWO_PI * 0.8,
            u0=-math.pi / 2 + TWO_PI * 0.1)
    m.lathe([(0.19, 0.0), (0.19, 0.2)], n, "iron", Md, C("4a4a4a"), arc=TWO_PI * 0.8, u0=-math.pi / 2 + TWO_PI * 0.1)
    m.disc(0.2, n, "iron", Md @ T(0, 0, 0.012), C("3a3a3a"))
    hot = vlib.Reg([0.0, 0.0, 0.5, 1.0])               # the glowing half of the coal maps (atlas_goods.coal_emit)
    for k in range(6 if not vlib.lite() else 3):
        a, rr = rng.uniform(0, TWO_PI), 0.16 * math.sqrt(rng.random())
        lump(m, Md @ T(rr * math.cos(a), rr * math.sin(a), 0.03 + rng.uniform(0, 0.02)), rng.uniform(0.025, 0.035), hot,
             jit(WHITE, 0.2), "coal_glow", seed=k * 0.7)
    pan = [(0.0, 0.2), (0.16, 0.2), (0.22, 0.24), (0.23, 0.26), (0.222, 0.262), (0.212, 0.245), (0.155, 0.21),
           (0.0, 0.21)]
    m.lathe(pan, n, vlib.RW("iron"), Md, C("5a5a5a"))
    m.cyl(0.012, 0.012, 0.3, 8, "iron", Md @ T(0.22, 0, 0.245, ry=math.pi / 2), WHITE)
    m.cyl(0.016, 0.016, 0.12, 8, vlib.RW("wood"), Md @ T(0.5, 0, 0.245, ry=math.pi / 2), C("5a3622"))
    for k in range(19 if not vlib.lite() else 7):
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
    # round 4: the four standing bags are items
    for k in range(4):
        x, y = 0.38 + k * 0.1, 0.08 - (k % 2) * 0.04
        Mb = T(x, y, 0, rz=irng("mb", k).uniform(-0.2, 0.2))
        with item(s, f"act_bag_{k}", (x, y, 0.0), "Bag of heiße Maroni",
                  "A kraft bag printed “Heiße Maroni”: sweet chestnuts roasted over charcoal until the shells "
                  "split, about 200 g for 4 €. Peel them while they are hot.") as bm:
            bm.box((0.08, 0.05, 0.15), Mb @ T(0, 0, 0.075), "kraft_maroni", WHITE, faces={"ny": "kraft_maroni"})
            bm.box((0.082, 0.052, 0.03), Mb @ T(0, 0, 0.16, rx=0.3), "kraft", WHITE)
    m.lathe([(0.0, 0.0), (0.05, 0.0), (0.055, 0.04), (0.0, 0.045)], 12, "steel", T(0.8, -0.1, 0, rz=0.9), WHITE)
    m.cyl(0.008, 0.008, 0.12, 6, vlib.RW("wood"), T(0.84, -0.14, 0.03, ry=math.pi / 2 - 0.2, rz=-0.6), C("5a3622"))
    # filled bags lying in a heap in front of the ready bags, rolled shut
    for k in range(6 if not vlib.lite() else 2):
        Mb = T(0.36 + k * 0.075, -0.13 + (k % 2) * 0.03, 0.036,
               rz=drng.uniform(-0.3, 0.3), rx=math.pi / 2 - 0.15)
        m.box((0.075, 0.05, 0.12), Mb, "kraft_maroni", WHITE, faces={"ny": "kraft_maroni"})
    # a burlap sack of raw chestnuts at the right end, rolled down, a scoop in it
    Ms = T(0.98, 0.09, 0)
    sack = [(0.0, 0.0), (0.09, 0.0), (0.11, 0.04), (0.108, 0.13), (0.1, 0.17), (0.115, 0.19), (0.1, 0.2), (0.092, 0.17)]
    m.lathe(sack if not vlib.lite() else [sack[0], sack[1], sack[3], sack[5]], seg(12, 6), vlib.RW("burlap"), Ms,
            C("c8a878"))
    for k in range(9 if not vlib.lite() else 3):
        a, rr = drng.uniform(0, TWO_PI), 0.07 * math.sqrt(drng.random())
        chestnut(m, Ms @ T(rr * math.cos(a), rr * math.sin(a), 0.155 + (0.07 - rr) * 0.25, rx=drng.uniform(-0.6, 0.6),
                           rz=drng.uniform(0, 6)), 0.017, C("c09070"))
    # the middle of the counter: a red-enamelled shop scale with a brass pan of chestnuts, a wooden stand of
    # filled kraft cones, and a stack of flat folded bags beside the bowl
    Mw = T(-0.27, 0.13, 0, rz=0.08)
    sc = s.node("act_scale_0", (-0.27, 0.13, 0.0))
    s.item("act_scale_0", "Shop scale", "deco", pivot="base",
           detail="An old red-enamelled shop scale with a brass pan: the chestnuts are sold by weight.")
    m, m_set = sc, m
    Mw = T(0, 0, 0, rz=0.08)
    m.box((0.16, 0.11, 0.05), Mw @ T(0, 0, 0.025), "sw_satin", C("8a1c18"), skip=("nz",))
    m.box((0.12, 0.07, 0.03), Mw @ T(0, 0.01, 0.06), "sw_satin", C("8a1c18"))
    m.disc(0.032, seg(14, 8), "sw_satin", Mw @ T(0, -0.0565, 0.034, rx=math.pi / 2), C("f2ecdc"))
    m.box((0.002, 0.0015, 0.026), Mw @ T(0.004, -0.058, 0.04, ry=0.5), "sw_matte", C("1a1a1a"))
    m.cyl(0.008, 0.008, 0.02, 6, "brass", Mw @ T(0, 0.01, 0.075), WHITE, caps=False)
    m.lathe([(0.0, 0.093), (0.085, 0.096), (0.098, 0.112), (0.093, 0.113), (0.082, 0.101), (0.0, 0.099)], seg(16, 8),
            "brass", Mw @ T(0, 0.01, 0), WHITE)
    for k in range(6 if not vlib.lite() else 2):
        a, rr = drng.uniform(0, TWO_PI), 0.05 * math.sqrt(drng.random())
        chestnut(m, Mw @ T(rr * math.cos(a), 0.01 + rr * math.sin(a), 0.099, rx=drng.uniform(-0.5, 0.5),
                           rz=drng.uniform(0, 6)), 0.016, jit(WHITE, 0.1))
    m = m_set
    Mc = T(-0.3, -0.13, 0, rz=-0.05)
    m.box((0.24, 0.07, 0.045), Mc @ T(0, 0, 0.0225), vlib.RW("wood"), C("9a6a40"), skip=("nz",))
    for k in range(4 if not vlib.lite() else 2):
        x = -0.09 + k * 0.06 if not vlib.lite() else -0.06 + k * 0.12
        Mk = Mc @ T(x, 0.0, 0.0, rx=drng.uniform(-0.06, 0.06))
        m.lathe([(0.004, 0.0), (0.036, 0.15), (0.039, 0.155)], seg(8, 5), vlib.RW("kraft"), Mk, C("c8a070"))
        for j in range(3 if not vlib.lite() else 1):
            a = TWO_PI * j / 3 + k
            chestnut(m, Mk @ T(0.014 * math.cos(a), 0.014 * math.sin(a), 0.135, rx=drng.uniform(-0.4, 0.4),
                               rz=drng.uniform(0, 6)), 0.015, jit(WHITE, 0.1))
    for k in range(5 if not vlib.lite() else 2):
        m.box((0.085, 0.13, 0.006), T(0.255 + drng.uniform(-0.004, 0.004), 0.14, 0.003 + k * 0.006,
                                      rz=drng.uniform(-0.08, 0.08)), "kraft_maroni", WHITE)
    # a charcoal bucket beside the brazier, and price tags
    m.lathe([(0.0, 0.0), (0.07, 0.0), (0.08, 0.13), (0.083, 0.135), (0.076, 0.135), (0.066, 0.006), (0.0, 0.006)],
            seg(14, 8), "steel", T(-1.0, 0.12, 0), C("7a7a7a"))
    for k in range(5 if not vlib.lite() else 2):
        lump(m, T(-1.0 + drng.uniform(-0.04, 0.04), 0.12 + drng.uniform(-0.04, 0.04), 0.12), 0.022, vlib.R("coal"),
             C("3a3a3a"), "atlas", seed=k * 1.9)
    for k, (x, y) in enumerate(((0.05, -0.215), (0.24, -0.21), (0.98, -0.1))):
        price_tag(m, T(x, y, 0.0), (6, 2, 1)[k])
    s.finish()
    return s


# ------------------------------------------------------------------ Kartoffelpuffer
def pancake(m, M, r, rand=None, n=None):
    """A Kartoffelpuffer: thick and bumpy in the middle, thinning to a ragged, lacy edge where strands of
    potato stick out (round 3; round 2's extruded discs read as tarts). The texture is mapped flat across it,
    so the golden middle and the crisp dark-brown rim of the puffer region land where they belong."""
    from mathutils import noise as mnoise
    rng_ = rand or rng                    # an item's own generator keeps its outline the same in lite
    n = n or seg(18, 8)
    reg = vlib.R("puffer")
    seed = rng_.uniform(0, 100)
    outer = []
    for j in range(n):
        a = TWO_PI * j / n
        k = 1 + 0.1 * mnoise.noise(Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, seed)))
        if rng_.random() < 0.3:
            k += rng_.uniform(0.08, 0.2)              # a strand of potato sticking out
        outer.append((r * k * math.cos(a), r * k * math.sin(a), 0.0015 + rng_.uniform(0, 0.0015)))
    rings = [outer]
    if not vlib.lite():
        rings.insert(0, [(r * 0.62 * math.cos(TWO_PI * j / n) * (1 + rng_.uniform(-0.05, 0.05)),
                          r * 0.62 * math.sin(TWO_PI * j / n) * (1 + rng_.uniform(-0.05, 0.05)),
                          0.0062 + rng_.uniform(-0.0012, 0.0012)) for j in range(n)])
    verts = [(0.0, 0.0, 0.0085)] + [v for ring in rings for v in ring] + [(0.0, 0.0, 0.0)]
    uv = lambda v: reg.uv(0.5 + 0.5 * v[0] / (r * 1.25), 0.5 + 0.5 * v[1] / (r * 1.25))
    faces = []
    for j in range(n):
        faces.append((0, 1 + j, 1 + (j + 1) % n))
    for i in range(len(rings) - 1):
        a0, b0 = 1 + i * n, 1 + (i + 1) * n
        for j in range(n):
            faces.append((a0 + j, b0 + j, b0 + (j + 1) % n, a0 + (j + 1) % n))
    last, bot = 1 + (len(rings) - 1) * n, len(verts) - 1
    for j in range(n):
        faces.append((bot, last + (j + 1) % n, last + j))
    m.add(verts, faces, [[uv(verts[i]) for i in f] for f in faces], M, jit(WHITE, 0.05), "atlas", True)


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
    # round 4: each finished Puffer on the tray is an item (the same nine in lite, 14 sides in both)
    for k in range(9):
        g = irng("pf", k)
        at = (-0.2 + (k % 3) * 0.1, -0.07 + (k // 3) * 0.09, 0.012 + (0.009 if k == 4 else 0))
        with item(s, f"act_puffer_{k}", at, "Kartoffelpuffer",
                  "A Kartoffelpuffer (Reibekuchen): grated potato and onion fried in hot oil until the lacy edge "
                  "goes crisp. Three with applesauce for 5 €.") as pm:
            pancake(pm, T(*at, rz=g.uniform(0, 6)), 0.045, rand=g, n=14)
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
    # a crate of potatoes at the back left, a bottle of oil, a salt shaker, jars of apple sauce, price tags
    G.crate(m, T(-1.0, 0.13, 0), 0.2, 0.2, 0.08, C("b48c5c"), slats=2)
    for k in range(10 if not vlib.lite() else 4):
        a, rr = drng.uniform(0, TWO_PI), 0.07 * math.sqrt(drng.random())
        lump(m, T(-1.0 + rr * math.cos(a), 0.13 + rr * math.sin(a), 0.055 + drng.uniform(0, 0.03), rz=drng.uniform(0, 6)),
             0.028, vlib.R("roll"), jit(C("c8a060"), 0.08), "atlas", subd=1, rough=0.15, squash=0.75, seed=k * 1.3)
    m.lathe([(0.0, 0.0), (0.035, 0.0), (0.036, 0.2), (0.02, 0.24), (0.014, 0.27), (0.0, 0.272)], seg(12, 6), "sw_vgloss",
            T(-0.34, 0.16, 0), C("d8c060"), "glass")
    m.lathe([(0.0, 0.0), (0.02, 0.0), (0.02, 0.07), (0.012, 0.085), (0.0, 0.088)], seg(10, 5), "sw_vgloss",
            T(0.1, 0.17, 0), C("f0f4f4"), "glass")
    for k in range(3):
        with item(s, f"act_jar_{2 + k}", (0.2 + k * 0.08, 0.2, 0.0), "Jar of applesauce",
                  "A jar of homemade applesauce (Apfelmus) to take home, 3 €.") as jm:
            G.jar(jm, T(0.2 + k * 0.08, 0.2, 0), "kraft", C("d8b060"), "sw_wet", h=0.09, r=0.034, lid=C("b0282a"),
                  n_lo=6)
    # front middle: a served paper plate of three Puffer with a dollop of applesauce, a wooden fork, and a
    # spatula resting beside the pan
    Ms = T(0.52, -0.125, 0)
    with item(s, "act_plate_0", (0.52, -0.125, 0.0), "Three Kartoffelpuffer with applesauce",
              "Three Kartoffelpuffer on a paper plate with a spoonful of applesauce and a wooden fork, 5 €.") as m_p:
        # 12 sides in lite: a hexagonal plate would change the item's bounds by more than a centimetre
        m_p.lathe([(0.0, 0.0), (0.075, 0.0), (0.09, 0.012), (0.0, 0.004)], 16 if not vlib.lite() else 12, "paper", Ms,
                  C("f6f2ea"))
        for k in range(3):
            a = TWO_PI * k / 3 + 0.4
            g = irng("pf_plate", k)
            pancake(m_p, Ms @ T(0.03 * math.cos(a), 0.03 * math.sin(a), 0.005 + k * 0.004, rz=g.uniform(0, 6),
                                rx=g.uniform(-0.06, 0.06)), 0.04, rand=g, n=14)
        m_p.lathe([(0.0, 0.0), (0.03, 0.0), (0.024, 0.012), (0.0, 0.018)], seg(10, 6), "sw_satin",
                  Ms @ T(-0.035, -0.03, 0.02), C("d8b060"), "liquid")
        m_p.box((0.1, 0.008, 0.002), Ms @ T(0.02, -0.06, 0.016, rz=0.3), vlib.RW("wood"), C("d8b890"))
    m.box((0.09, 0.06, 0.003), T(-0.37, -0.15, 0.012, rz=0.5, ry=0.1), "steel", WHITE)
    m.box((0.14, 0.02, 0.016), T(-0.29, -0.185, 0.008, rz=0.5), vlib.RW("wood"), C("3a2414"))
    for k, (x, y) in enumerate(((-0.1, -0.2), (0.28, -0.12), (0.85, -0.2))):
        price_tag(m, T(x, y, 0.0), (7, 5, 0)[k])
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
