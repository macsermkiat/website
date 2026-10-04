"""Bierstand goods: the tap counter, the back shelf and the upper shelf.

prop_bier_counter -> slot_counter of stall_bier: chrome tap tower with three tap handles
                     (act_tap_0..2, pivot at the handle base), a drip tray, full Maßkrüge, Willibecher and
                     a Weizenglas (act_glass_0..8, each with a separate foam head node foam_<n>: domed
                     crown inside the rim, a spill running down every other glass), coasters, pretzels.
prop_bier_back    -> slot_shelf_1 of stall_bier: oak casks on a rack, a chalkboard price board, stoneware
                     steins, a crate of bottles and a stack of coasters.
prop_bier_shelf   -> slot_shelf_2 of stall_bier: clean Maßkrüge (act_glass_10..12), Willibecher
                     (act_glass_13..15) and Weizengläser (act_glass_16..18) upside down on towels,
                     two stoneware steins, folded tea towels.
The stall and its props share a 60k triangle budget (check_props wants 2k of it left over).
"""
import math

from mathutils import Matrix

import goods as G
import vlib
from vlib import C, T, WHITE, drng, lite, rng, seg

TWO_PI = 2 * math.pi


def tap_tower(s, x, y):
    m = s.static
    chrome = C("ffffff")
    n = seg(12, 6)
    # drip tray with a slotted steel grate
    m.box((0.56, 0.15, 0.022), T(x, y - 0.09, 0.011), "steel", chrome, faces={"pz": vlib.RW("grate")}, skip=("nz",))
    # column: a polished steel pillar on a round foot, T-bar head with domed end caps
    m.lathe([(0.07, 0.0), (0.072, 0.006), (0.05, 0.02), (0.034, 0.03), (0.034, 0.4), (0.04, 0.42)], n, "steel",
            T(x, y + 0.06, 0), chrome)
    m.cyl(0.042, 0.042, 0.56, n, "steel", T(x - 0.28, y + 0.06, 0.44, ry=math.pi / 2), chrome, caps=False)
    for sx in (-1, 1):
        m.lathe([(0.042, 0.0), (0.03, 0.012), (0.0, 0.016)], n, "steel",
                T(x + sx * 0.28, y + 0.06, 0.44, ry=sx * math.pi / 2), chrome)
    badges = [("Helles", C("e8c050")), ("Dunkles", C("5a2a14")), ("Weißbier", C("2a5aa8"))]
    for i, dx in enumerate((-0.16, 0.0, 0.16)):
        tx = x + dx
        # faucet: body out of the bar toward the front, spout down
        m.cyl(0.016, 0.016, 0.075, 10, "steel", T(tx, y + 0.06, 0.44, rx=math.pi / 2), chrome, caps=False)
        m.cyl(0.018, 0.018, 0.034, 10, "steel", T(tx, y - 0.02, 0.425), chrome)
        m.cyl(0.009, 0.007, 0.05, 8, "steel", T(tx, y - 0.02, 0.38), chrome, caps=False)
        # the handle pivots at its base on top of the faucet body
        h = s.node(f"act_tap_{i}", (tx, y - 0.02, 0.46))
        s.item(f"act_tap_{i}", f"{badges[i][0]} tap", "tap")
        h.cyl(0.012, 0.012, 0.012, 10, "steel", None, chrome)                     # ferrule
        h.lathe([(0.0, 0.012), (0.011, 0.012), (0.013, 0.03), (0.016, 0.09), (0.02, 0.13), (0.021, 0.15),
                 (0.017, 0.165), (0.0, 0.168)], seg(10, 6), vlib.RW("wood"), None,
                [C("3a2012"), C("2a1a10"), C("5a3822")][i], "glaze")
        if not lite():
            # enamel badge on the front of the handle
            bm = T(0, -0.0205, 0.115, rx=math.pi / 2)
            h.lathe([(0.0, 0.0), (0.017, 0.0), (0.018, 0.004), (0.0, 0.005)], 12, "sw_gloss", bm, badges[i][1],
                    "glaze")
            h.disc(0.013, 12, "coaster", bm @ T(0, 0, 0.0052), WHITE, "atlas")
    return m


def pretzel(m, M, s=1.0, col=C("6a3212")):
    """Laugenbrezel: one dough rope - thick belly, thin arms crossing in a twist - with salt grains."""
    ctrl = [(0.036, -0.004, 0.017), (0.012, 0.022, 0.022), (-0.02, 0.046, 0.014), (-0.052, 0.046, 0.011),
            (-0.07, 0.012, 0.011), (-0.052, -0.03, 0.012), (0.0, -0.046, 0.013), (0.052, -0.03, 0.012),
            (0.07, 0.012, 0.011), (0.052, 0.046, 0.011), (0.02, 0.046, 0.016), (-0.012, 0.022, 0.03),
            (-0.036, -0.004, 0.017)]
    pts = G.spline(ctrl, 2 if not lite() else 1)
    radii = []
    for p in pts:
        belly = max(0.0, (-p[1] - 0.005) / 0.04)
        radii.append(0.0075 + 0.0075 * min(1.0, belly))
    S = M @ Matrix.Diagonal((s, s, s, 1))
    m.tube(pts, 0.01, seg(6, 4), "roll", S, col, "glaze", radii=radii)
    if not lite():
        for j in range(9):
            p = pts[drng.randrange(len(pts))]
            m.box((0.004, 0.003, 0.003), S @ T(p[0], p[1], p[2] + 0.011, rz=drng.uniform(0, 3)), "sw_satin",
                  C("f4f2ee"), skip=("nz",))


BEERS = {"helles": ("Helles", C("f2b52c")), "dunkles": ("Dunkles", C("5a2208")), "weiss": ("Weißbier", C("e8a232")),
         "radler": ("Radler", C("f0b848"))}
GLASS_NAMES = {"mass": ("Maß", "Maßkrug"), "willi": ("Half litre", "Willibecher"), "weizen": ("Weizenglas", "Weizenglas")}


def counter():
    s = vlib.PropSet("prop_bier_counter", "slot_counter", "bierstand")
    m = s.static
    tap_tower(s, 0.62, 0.02)
    # a row of full glasses: Maßkrüge, half-litre Willibecher and a tall Weizenglas, each with its own foam
    # head node; the last one stands on the drip tray under the middle tap, just pulled
    spots = [(-0.62, -0.12, "mass", "helles"), (-0.49, 0.09, "mass", "helles"), (-0.38, -0.14, "willi", "dunkles"),
             (-0.26, 0.03, "weizen", "weiss"), (-0.15, -0.13, "willi", "helles"), (-0.02, -0.04, "mass", "radler"),
             (0.11, 0.1, "willi", "dunkles"), (0.22, -0.12, "mass", "helles"), (0.62, -0.075, "willi", "helles")]
    tray = len(spots) - 1
    for i, (x, y, kind, beer) in enumerate(spots):
        on_tray = i == tray
        g = s.node(f"act_glass_{i}", (x, y, 0.022 if on_tray else 0.004))
        foam = s.node(f"foam_{i}", (0, 0, 0), parent=f"act_glass_{i}")
        rz = rng.uniform(-math.pi, math.pi) if kind == "mass" else 0
        M = T(0, 0, 0, rz=rz)
        glass = {"mass": G.mass, "willi": G.willi, "weizen": G.weizen}[kind](g, M)
        level = glass[1] - {"mass": 0.018, "willi": 0.016, "weizen": 0.03}[kind] - rng.uniform(0, 0.004)
        # foam runs down the side facing the visitor on every other glass (angle in the glass's own frame)
        spill = (-math.pi / 2 + rng.uniform(-0.7, 0.7) - rz) if i % 2 == 0 else 0
        G.beer_fill(g, foam, M, glass, level, beer_col=BEERS[beer][1], spill=spill, seed=i * 1.7,
                    dome=0.024 if kind == "weizen" else None)
        short, gname = GLASS_NAMES[kind]
        s.item(f"act_glass_{i}", f"{short} of {BEERS[beer][0]}", "glass", glass=gname, beer=BEERS[beer][0])
        # beer coaster under each glass
        if not lite() and not on_tray:
            m.disc(0.054, 12, "coaster", T(x, y, 0.0015, rz=drng.uniform(0, 6)), WHITE, "atlas")
            m.lathe([(0.054, 0.0), (0.054, 0.004)], 12, "paper", T(x, y, 0), C("e8e2d6"))
    # a bar towel and a wooden board of pretzels at the left end
    m.box((0.28, 0.16, 0.006), T(-0.9, 0.1, 0.003, rz=-0.08), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    G.board(m, T(-0.92, -0.1, 0), 0.34, 0.16, 0.018, C("c49a6c"))
    for k, (dx, dy, a) in enumerate(((-0.09, 0.0, 0.15), (0.075, 0.005, -0.2))):
        pretzel(m, T(-0.92 + dx, -0.1 + dy, 0.018, rz=a), s=0.95)
    s.finish()
    return s


def stein(m, M, col=C("7a6a58"), lid=C("b0b0b0")):
    """Stoneware Bierkrug with a pewter lid and thumb lift."""
    n = seg(10, 6)
    m.lathe([(0.0, 0.0), (0.045, 0.0), (0.048, 0.01), (0.046, 0.03), (0.047, 0.15), (0.045, 0.17),
             (0.0, 0.17)], n, "bisque", M, col, "glaze")
    if not lite():
        m.torus(0.0475, 0.003, n, 3, "ceramic", M @ T(0, 0, 0.145), C("2a4a8a"), "glaze")
    m.lathe([(0.049, 0.168), (0.05, 0.176), (0.035, 0.19), (0.0, 0.205)], n, "steel", M, lid)
    pts = [(0.045, 0, 0.14), (0.075, 0, 0.13), (0.08, 0, 0.08), (0.07, 0, 0.04), (0.046, 0, 0.035)]
    m.tube(pts, 0.009, seg(6, 4), "bisque", M, col, "glaze")
    m.box((0.02, 0.012, 0.02), M @ T(0.058, 0, 0.19), "steel", lid)


def bottle_crate(m, M):
    """A small wooden crate of six brown swing-top bottles (Bügelflaschen), porcelain stoppers up."""
    G.crate(m, M, 0.26, 0.18, 0.1, C("9a7048"), slats=1)
    n = seg(8, 5)
    for k in range(6):
        c, r = divmod(k, 2)
        Mb = M @ T(-0.08 + c * 0.08, -0.042 + r * 0.084, 0.004)
        # only the tops show above the crate: the body starts where the crate's sides end
        m.lathe([(0.031, 0.09), (0.031, 0.15), (0.026, 0.18), (0.014, 0.215), (0.0135, 0.235), (0.0, 0.236)], n,
                "sw_vgloss", Mb, C("4a2208"), "glass")
        m.lathe([(0.0, 0.236), (0.0145, 0.236), (0.0145, 0.25), (0.0, 0.254)], seg(6, 4), "ceramic", Mb,
                C("f2eee6"), "glaze")
        if not lite():
            m.lathe([(0.0318, 0.1), (0.0318, 0.14)], n, "coaster", Mb, WHITE, "atlas", v_by="z")


def back():
    s = vlib.PropSet("prop_bier_back", "slot_shelf_1", "bierstand", footprint=(2.4, 0.28))
    m = s.static
    # three small oak casks on a barrel rack (Fasslager): two squared rails front and back along the
    # shelf, a pair of chocks on each rail per cask. Heads to the front, taps low on the heads.
    L, r_end, r_belly, cy = 0.21, 0.1, 0.118, 0.012
    rail_z, rail_h = 0.0, 0.03
    lift = rail_z + rail_h - (r_belly - (r_end + (r_belly - r_end) * math.sin(math.pi * 0.84)))
    for x0, x1 in ((-1.18, -0.58), (0.61, 0.89)):
        for ry in (cy - 0.078, cy + 0.078):
            m.box((x1 - x0, 0.036, rail_h), T((x0 + x1) / 2, ry, rail_z + rail_h / 2), vlib.RW("wood"), C("5a3c24"),
                  skip=("nz",))
    for k, x in enumerate((-1.03, -0.73, 0.75)):
        for ry in (cy - 0.078, cy + 0.078):
            for sx in (-1, 1):
                m.box((0.03, 0.034, 0.04), T(x + sx * 0.088, ry, rail_z + rail_h + 0.012, ry=sx * 0.7), vlib.RW("wood"),
                      C("6a4a30"))
        G.barrel(m, T(x, cy, lift, rz=-math.pi / 2), L=L, r_end=r_end, r_belly=r_belly, staves=10)
    # chalkboard price board standing against the back wall, left of the middle brace (x -0.015..0.015)
    bw, bh = 0.5, 0.34
    Mb = T(-0.31, 0.085, 0.0, rx=-0.08) @ T(0, 0, bh / 2 + 0.004)
    m.box((bw - 0.03, 0.012, bh - 0.03), Mb, "chalkboard", WHITE, faces={"ny": "chalkboard"})
    for dz, w, hh in ((bh / 2 - 0.012, bw, 0.024), (-bh / 2 + 0.012, bw, 0.024)):
        m.box((w, 0.022, hh), Mb @ T(0, 0, dz), vlib.RW("wood"), C("6a4228"))
    for dx in (bw / 2 - 0.012, -bw / 2 + 0.012):
        m.box((0.024, 0.022, bh), Mb @ T(dx, 0, 0), vlib.RW("wood"), C("6a4228"))
    m.cyl(0.005, 0.005, 0.05, 6, "sw_matte", T(-0.2, 0.03, 0.014, ry=math.pi / 2), C("f4f2ec"))   # chalk
    # a row of stoneware steins with pewter lids, and a crate of swing-top bottles
    for k, (x, col) in enumerate(((0.16, C("8a7a64")), (0.28, C("6a5a48")), (0.4, C("9a8a70")))):
        stein(m, T(x, 0.0 + (k % 2) * 0.04, 0, rz=2.4 - k * 0.5), col)
    bottle_crate(m, T(1.02, 0.02, 0))
    # a stack of beer coasters beside the chalkboard
    for k in range(4 if not lite() else 1):
        m.disc(0.054, 12, "coaster", T(-0.5 + 0.0, -0.06, 0.006 * (k + 1), rz=drng.uniform(0, 6)), WHITE, "atlas")
    m.lathe([(0.054, 0.0), (0.054, 0.024)], 12, "paper", T(-0.5, -0.06, 0), C("e8e2d6"))
    s.finish()
    return s


def shelf():
    s = vlib.PropSet("prop_bier_shelf", "slot_shelf_2", "bierstand", footprint=(2.4, 0.28))
    m = s.static
    # clean Maßkrüge upside down on a folded towel, ready for the next round
    m.box((0.5, 0.2, 0.012), T(-0.7, 0.01, 0.006), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k, x in enumerate((-0.86, -0.7, -0.54)):
        idx = 10 + k
        g = s.node(f"act_glass_{idx}", (x, 0.01 + (k % 2) * 0.03, 0.012), rot=(math.pi, 0, rng.uniform(0, TWO_PI)))
        G.mass(g, T(0, 0, -0.2108), n=10, lo=5)
        s.item(f"act_glass_{idx}", "Clean Maßkrug, upside down", "glass", glass="Maßkrug")
    # clean half-litre Willibecher upside down on a second towel
    m.box((0.36, 0.18, 0.01), T(-0.2, 0.02, 0.005), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k, x in enumerate((-0.3, -0.2, -0.1)):
        idx = 13 + k
        g = s.node(f"act_glass_{idx}", (x, 0.02 + (k % 2) * 0.04, 0.01), rot=(math.pi, 0, 0))
        G.willi(g, T(0, 0, -0.2058), n=10, lo=5)
        s.item(f"act_glass_{idx}", "Clean Willibecher, upside down", "glass", glass="Willibecher")
    # clean Weizengläser upside down on a third towel
    m.box((0.3, 0.16, 0.01), T(0.22, 0.02, 0.005), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k, x in enumerate((0.13, 0.22, 0.31)):
        idx = 16 + k
        g = s.node(f"act_glass_{idx}", (x, 0.02 + (k % 2) * 0.035, 0.01), rot=(math.pi, 0, 0))
        G.weizen(g, T(0, 0, -0.2512), n=10, lo=5)
        s.item(f"act_glass_{idx}", "Clean Weizenglas, upside down", "glass", glass="Weizenglas")
    # two stoneware steins with pewter lids, two folded tea towels
    for k, (x, col) in enumerate(((0.44, C("6a5a48")), (0.56, C("8a7a64")))):
        stein(s.static, T(x, 0.02 + (k % 2) * 0.03, 0, rz=0.6 + k * 0.7), col)
    for k in range(2):
        m.box((0.26, 0.18, 0.03), T(0.82, 0.02, 0.015 + k * 0.03, rz=0.05 - k * 0.1), "towel", WHITE,
              faces={"pz": "towel", "ny": "towel"}, skip=("nz",))
    s.finish()
    return s


SETS = {
    "prop_bier_counter": dict(fn=counter, slot="slot_counter", stall="bierstand", kind="counter", section=True, seed=31,
                              cam=((-0.15, -1.75, 0.6), (-0.1, 0.0, 0.2), 26),
                              hero=((0.32, -1.2, 0.5), (0.36, 0.0, 0.3), 32)),
    "prop_bier_back": dict(fn=back, slot="slot_shelf_1", stall="bierstand", kind="shelf", section=True, seed=32,
                           cam=((0.0, -2.05, 0.36), (0.0, 0.0, 0.15), 30),
                           hero=((-0.85, -0.8, 0.2), (-0.8, 0.0, 0.12), 38)),
    "prop_bier_shelf": dict(fn=shelf, slot="slot_shelf_2", stall="bierstand", kind="shelf2", section=True, seed=33,
                            cam=((0.0, -2.05, 0.3), (0.0, 0.0, 0.12), 30),
                            hero=((-0.35, -0.95, 0.3), (-0.35, 0.0, 0.1), 32)),
}
