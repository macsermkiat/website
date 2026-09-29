"""Bierstand goods: the tap counter and the back shelf.

prop_bier_counter -> slot_counter of stall_bier: chrome tap tower with three tap handles
                     (act_tap_0..2, pivot at the handle base), a drip tray, pints and Maßkrüge
                     (act_glass_0..n, each with a separate foam mesh foam_<n>), coasters, pretzels.
prop_bier_back    -> slot_shelf_1 of stall_bier: small oak casks on cradles, a chalkboard price board,
                     two stoneware steins.
"""
import math

from mathutils import Matrix, Vector

import goods as G
import vlib
from vlib import C, T, WHITE, jit, rng, seg

TWO_PI = 2 * math.pi


def tap_tower(s, x, y):
    m = s.static
    chrome = C("ffffff")
    n = seg(16, 8)
    # drip tray with a slotted steel grate
    m.box((0.56, 0.15, 0.022), T(x, y - 0.09, 0.011), "steel", chrome, faces={"pz": vlib.RW("grate")})
    # column: a polished steel pillar on a round foot, T-bar head
    m.lathe([(0.07, 0.0), (0.072, 0.006), (0.05, 0.02), (0.036, 0.03), (0.034, 0.4), (0.04, 0.42)], n, "steel",
            T(x, y + 0.06, 0), chrome)
    m.cyl(0.042, 0.042, 0.56, n, "steel", T(x - 0.28, y + 0.06, 0.44, ry=math.pi / 2), chrome)
    for sx in (-1, 1):
        m.sphere(0.042, n, seg(8, 4), "steel", T(x + sx * 0.28, y + 0.06, 0.44), chrome, scale=(0.5, 1, 1))
    badges = [("Helles", C("e8c050")), ("Dunkles", C("5a2a14")), ("Weißbier", C("2a5aa8"))]
    for i, dx in enumerate((-0.16, 0.0, 0.16)):
        tx = x + dx
        # faucet: body out of the bar toward the front, spout down
        m.cyl(0.016, 0.016, 0.075, 12, "steel", T(tx, y + 0.06, 0.44, rx=math.pi / 2), chrome)
        m.cyl(0.018, 0.018, 0.034, 12, "steel", T(tx, y - 0.02, 0.425), chrome)
        m.cyl(0.009, 0.007, 0.05, 10, "steel", T(tx, y - 0.02, 0.38), chrome)
        m.cyl(0.007, 0.007, 0.004, 10, "sw_matte", T(tx, y - 0.02, 0.379), C("101010"), caps=True)
        # the handle pivots at its base on top of the faucet body
        h = s.node(f"act_tap_{i}", (tx, y - 0.02, 0.46))
        h.cyl(0.012, 0.012, 0.012, 12, "steel", None, chrome)                     # ferrule
        h.lathe([(0.0, 0.012), (0.011, 0.012), (0.013, 0.03), (0.016, 0.09), (0.02, 0.13), (0.021, 0.15),
                 (0.017, 0.165), (0.0, 0.168)], seg(14, 8), vlib.RW("wood"), None,
                [C("3a2012"), C("2a1a10"), C("5a3822")][i], "glaze")
        # enamel badge on the front of the handle
        bm = T(0, -0.0205, 0.115, rx=math.pi / 2)
        h.lathe([(0.0, 0.0), (0.017, 0.0), (0.018, 0.004), (0.0, 0.005)], seg(16, 8), "sw_gloss", bm, badges[i][1],
                "glaze")
        h.disc(0.013, seg(16, 8), "coaster", bm @ T(0, 0, 0.0052), WHITE, "atlas")
    return m


def pretzel(m, M, s=1.0, col=C("6a3212")):
    """Laugenbrezel: one dough rope - thick belly, thin arms crossing in a twist - with salt grains."""
    ctrl = [(0.036, -0.004, 0.017), (0.012, 0.022, 0.022), (-0.02, 0.046, 0.014), (-0.052, 0.046, 0.011),
            (-0.07, 0.012, 0.011), (-0.052, -0.03, 0.012), (0.0, -0.046, 0.013), (0.052, -0.03, 0.012),
            (0.07, 0.012, 0.011), (0.052, 0.046, 0.011), (0.02, 0.046, 0.016), (-0.012, 0.022, 0.03),
            (-0.036, -0.004, 0.017)]
    pts = G.spline(ctrl, seg(3, 2))
    radii = []
    for p in pts:
        belly = max(0.0, (-p[1] - 0.005) / 0.04)
        radii.append(0.0075 + 0.0075 * min(1.0, belly))
    S = M @ Matrix.Diagonal((s, s, s, 1))
    m.tube(pts, 0.01, seg(7, 5), "roll", S, col, "glaze", radii=radii)
    if not vlib.lite():
        for j in range(16):
            p = pts[rng.randrange(len(pts))]
            m.box((0.004, 0.003, 0.003), S @ T(p[0], p[1], p[2] + 0.011, rz=rng.uniform(0, 3)), "sw_satin",
                  C("f4f2ee"))


def counter():
    s = vlib.PropSet("prop_bier_counter", "slot_counter", "bierstand")
    m = s.static
    tap_tower(s, 0.62, 0.02)
    # glasses: four half-litre Willibecher and three Maßkrüge, each full with a foam head
    beer = C("e0901c")
    dark = C("5a2208")
    weiss = C("f0b040")
    spots = [(-1.08, -0.1, "mass", beer), (-0.9, 0.08, "mass", beer), (-0.84, -0.12, "willi", dark),
             (-0.66, -0.06, "willi", beer), (-0.5, -0.14, "mass", beer), (-0.34, -0.08, "willi", weiss),
             (-0.2, 0.1, "willi", beer)]
    for i, (x, y, kind, bcol) in enumerate(spots):
        g = s.node(f"act_glass_{i}", (x, y, 0.004))
        s.node(f"foam_{i}", (0, 0, 0), parent=f"act_glass_{i}")
        foam = [n for n in s.nodes if n[1] == f"foam_{i}"][0][0]
        rz = rng.uniform(-math.pi, math.pi) if kind == "mass" else 0
        M = T(0, 0, 0, rz=rz)
        inner = G.mass(g, M) if kind == "mass" else G.willi(g, M)
        level = (0.17 if kind == "mass" else 0.172) - rng.uniform(0, 0.012)
        G.beer_fill(g, foam, M, inner, level, foam_h=0.028 if kind == "mass" else 0.03, beer_col=bcol)
        # beer coaster under each glass
        m.disc(0.054, seg(20, 10), "coaster", T(x, y, 0.0015, rz=rng.uniform(0, 6)), WHITE, "atlas")
        m.lathe([(0.054, 0.0), (0.054, 0.004)], seg(20, 10), "paper", T(x, y, 0), C("e8e2d6"))
    # a bar towel and a wooden board of pretzels between glasses and tap
    m.box((0.28, 0.16, 0.008), T(0.08, 0.07, 0.004, rz=-0.08), "sw_matte", C("dcd6c8"), skip=("nz",))
    for k in range(5):
        m.box((0.28, 0.008, 0.0085), T(0.08, 0.02 + k * 0.024 + 0.0, 0.004, rz=-0.08), "sw_matte", C("2a4a8a"),
              skip=("nz",))
    G.board(m, T(0.08, -0.12, 0), 0.34, 0.16, 0.018, C("c49a6c"))
    for k, (dx, dy, a) in enumerate(((-0.09, 0.0, 0.15), (0.075, 0.005, -0.2))):
        pretzel(m, T(0.08 + dx, -0.12 + dy, 0.018, rz=a), s=0.95)
    s.finish()
    return s


def stein(m, M, col=C("7a6a58"), lid=C("b0b0b0")):
    """Stoneware Bierkrug with a pewter lid and thumb lift."""
    n = seg(18, 10)
    m.lathe([(0.0, 0.0), (0.045, 0.0), (0.048, 0.01), (0.046, 0.03), (0.047, 0.15), (0.045, 0.17),
             (0.0, 0.17)], n, "bisque", M, col, "glaze")
    for z in (0.03, 0.145):
        m.torus(0.0475, 0.003, n, 5, "ceramic", M @ T(0, 0, z), C("2a4a8a"), "glaze")
    m.lathe([(0.049, 0.168), (0.05, 0.176), (0.035, 0.19), (0.012, 0.2), (0.0, 0.205)], n, "steel", M, lid)
    pts = [(0.045, 0, 0.14), (0.075, 0, 0.13), (0.08, 0, 0.08), (0.07, 0, 0.04), (0.046, 0, 0.035)]
    m.tube(pts, 0.009, seg(8, 5), "bisque", M, col, "glaze")
    m.box((0.02, 0.012, 0.02), M @ T(0.058, 0, 0.19), "steel", lid)


def back():
    s = vlib.PropSet("prop_bier_back", "slot_shelf_1", "bierstand", footprint=(2.4, 0.3))
    m = s.static
    # three small oak casks on wooden cradles, heads to the front with brass taps
    for k, x in enumerate((-1.05, -0.72, 0.75)):
        for dy in (-0.07, 0.07):
            m.box((0.18, 0.04, 0.035), T(x, dy, 0.0175), vlib.RW("wood"), C("8a6240"))
        G.barrel(m, T(x, 0.0, 0.012, rz=-math.pi / 2), L=0.28, r_end=0.1, r_belly=0.118, staves=16)
    # chalkboard price board leaning against the back wall
    bw, bh = 0.56, 0.34
    Mb = T(-0.1, 0.1, 0.0, rx=-0.12) @ T(0, 0, bh / 2 + 0.012)
    m.box((bw - 0.03, 0.012, bh - 0.03), Mb, "chalkboard", WHITE, faces={"ny": "chalkboard"})
    for dz, w, hh in ((bh / 2 - 0.012, bw, 0.024), (-bh / 2 + 0.012, bw, 0.024)):
        m.box((w, 0.022, hh), Mb @ T(0, 0, dz), vlib.RW("wood"), C("6a4228"))
    for dx in (bw / 2 - 0.012, -bw / 2 + 0.012):
        m.box((0.024, 0.022, bh), Mb @ T(dx, 0, 0), vlib.RW("wood"), C("6a4228"))
    # chalk and a sponge on the frame's ledge
    m.cyl(0.005, 0.005, 0.05, 6, "sw_matte", T(0.05, 0.04, 0.014, ry=math.pi / 2), C("f4f2ec"))
    # two stoneware steins
    stein(m, T(0.3, 0.0, 0, rz=2.4), C("8a7a64"))
    stein(m, T(0.43, -0.02, 0, rz=1.9), C("6a5a48"))
    # a stack of beer coasters
    for k in range(6):
        m.disc(0.054, seg(20, 10), "coaster", T(1.05, -0.03, 0.004 * (k + 1), rz=rng.uniform(0, 6)), WHITE, "atlas")
    m.lathe([(0.054, 0.0), (0.054, 0.024)], seg(20, 10), "paper", T(1.05, -0.03, 0), C("e8e2d6"))
    s.finish()
    return s


SETS = {
    "prop_bier_counter": dict(fn=counter, slot="slot_counter", stall="bierstand", kind="counter", section=True, seed=31,
                              cam=((-0.15, -1.75, 0.6), (-0.1, 0.0, 0.2), 26)),
    "prop_bier_back": dict(fn=back, slot="slot_shelf_1", stall="bierstand", kind="shelf", section=True, seed=32,
                           cam=((0.0, -2.05, 0.36), (0.0, 0.0, 0.15), 30)),
}
