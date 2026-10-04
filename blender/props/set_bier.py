"""Bierstand goods: the tap counter, the back shelf and the upper shelf.

prop_bier_counter -> slot_counter of stall_bier: chrome tap tower with three tap handles
                     (act_tap_0..2, pivot at the handle base), a drip tray, full Maßkrüge, Willibecher and
                     a Weizenglas (act_glass_0..7, each with a separate foam head node foam_<n>: a soft,
                     uneven head inside the rim, a spill on the glass just pulled), pretzels, and (round 6)
                     one Bierdeckel per project in content/projects.md plus two spares: act_coaster_<n>, each
                     with write_coaster_<n>_front and write_coaster_<n>_back.
prop_bier_back    -> slot_shelf_1 of stall_bier: oak casks on a rack, a chalkboard price board, stoneware
                     steins, a crate of bottles and a stack of coasters.
prop_bier_shelf   -> slot_shelf_2 of stall_bier: clean Maßkrüge (act_glass_10..12), Willibecher
                     (act_glass_13..15) and Weizengläser (act_glass_16..18) upside down on towels,
                     two stoneware steins, folded tea towels.
The stall and its props share a 60k triangle budget (check_props wants 2k of it left over).
"""
import math

from mathutils import Matrix

import content_projects
import goods as G
import vlib
import vprint
from vlib import C, T, WHITE, drng, jit, lite, rng, seg

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


def pretzel(m, M, s=1.0, col=WHITE, seed=0):
    """Laugenbrezel: one dough rope - thick belly, thin arms crossing in a twist - in a matte lye crust.

    Round 6 pass 2 (judges: "glossy brown plastic with white dots"): the rope is skinned here with its own
    UVs into the atlas's `pretzel` region (atlas_goods.g_pretzel): u runs once round the rope from underneath
    (u 0 and 1, the seam) over the top (u 0.5, measured from world up, so the crust's dark top and pale
    underside stay put) and v along it,
    remapped so the belly always lands on v 0.3..0.7, where the texture tears the crust open along the top
    (the pale "Ausbund"). It is on the plain atlas material, matte-satin from the region's roughness, not
    vendor_glaze. Coarse salt sits on the top of the rope as irregular crystals (full build; the lite build
    keeps the salt flecks in the texture)."""
    from mathutils import Vector
    # the arms run from the twist down onto the belly and end pressed into its top (round 6 pass 2: they
    # stopped 3 cm short of it, open tube ends in the air)
    ctrl = [(0.036, -0.034, 0.02), (0.026, -0.006, 0.019), (0.012, 0.022, 0.022), (-0.02, 0.046, 0.014),
            (-0.052, 0.046, 0.011), (-0.07, 0.012, 0.011), (-0.052, -0.03, 0.012), (0.0, -0.046, 0.013),
            (0.052, -0.03, 0.012), (0.07, 0.012, 0.011), (0.052, 0.046, 0.011), (0.02, 0.046, 0.016),
            (-0.012, 0.022, 0.03), (-0.026, -0.006, 0.019), (-0.036, -0.034, 0.02)]
    per = 2 if not lite() else 1
    pts = [Vector(p) for p in G.spline(ctrl, per)]
    # thickness along the rope by its place in the knot: the belly (ctrl 6..8) full, tapering over one control
    # span each side into the thin arms; the very ends thin out and sink into the belly
    def belly_w(i):
        c = i / per
        return max(0.0, min(1.0, min(c - 5.0, 9.0 - c)))
    belly = [belly_w(i) for i in range(len(pts))]
    radii = [0.0072 + 0.0078 * b for b in belly]
    for e in (0, len(pts) - 1):
        radii[e] = 0.0045
        pts[e] = pts[e] - Vector((0, 0, 0.004))
    ls = [0.0]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        ls.append(ls[-1] + (p1 - p0).length)
    vs = [l / ls[-1] for l in ls]
    # the belly's span along the rope (where it is at least half thick) -> v 0.3..0.7
    bi = [i for i, b in enumerate(belly) if b >= 0.5]
    b0, b1 = vs[bi[0]], vs[bi[-1]]
    vmap = lambda v: (0.3 * v / b0 if v < b0 else 0.3 + 0.4 * (v - b0) / (b1 - b0) if v <= b1
                      else 0.7 + 0.3 * (v - b1) / (1 - b1))
    n = seg(8, 6)
    up = Vector((0, 0, 1))
    frames = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n2 = (up - t * up.dot(t)).normalized()          # "up" across the rope
        n1 = t.cross(n2).normalized()
        frames.append((n1, n2))
    reg = vlib.R("pretzel")
    verts, faces, uvs = [], [], []
    for i, p in enumerate(pts):
        n1, n2 = frames[i]
        for j in range(n + 1):
            a = -math.pi / 2 - math.tau * j / n         # j = 0 underneath (the seam), j = n / 2 on top (u 0.5)
            # the belly is a little flattened underneath where it baked on the tray
            sq = 0.82 if math.sin(a) < 0 else 1.0
            verts.append(tuple(p + radii[i] * (math.cos(a) * n1 + math.sin(a) * sq * n2)))
    W = n + 1
    for i in range(len(pts) - 1):
        for j in range(n):
            q = (i * W + j, i * W + j + 1, (i + 1) * W + j + 1, (i + 1) * W + j)
            faces.append(q)
            uvs.append([reg.uv(j / n, vmap(vs[i])), reg.uv((j + 1) / n, vmap(vs[i])),
                        reg.uv((j + 1) / n, vmap(vs[i + 1])), reg.uv(j / n, vmap(vs[i + 1]))])
    S = M @ Matrix.Diagonal((s, s, s, 1))
    m.add(verts, faces, uvs, S, col, "atlas", True)
    if lite():
        return
    # coarse pretzel salt: irregular, chunky crystals (squashed, skewed octahedra) on the top of the rope,
    # most of them on the belly, sunk a little into the crust
    import random
    r_ = random.Random(77 + seed)
    k = 0
    tries = 0
    while k < 24 and tries < 300:
        tries += 1
        i = r_.randrange(1, len(pts) - 1)
        if belly[i] < 0.2 and r_.random() < 0.6:
            continue
        n1, n2 = frames[i]
        ang = math.pi / 2 + r_.uniform(-0.75, 0.75)
        nrm = (math.cos(ang) * n1 + math.sin(ang) * n2).normalized()
        c = pts[i] + nrm * (radii[i] + 0.0006)
        sz = r_.uniform(0.0017, 0.0029)
        ax = [Vector((r_.uniform(-1, 1), r_.uniform(-1, 1), r_.uniform(-1, 1))).normalized() for _ in range(3)]
        e0 = ax[0]
        e1 = (ax[1] - e0 * ax[1].dot(e0)).normalized()
        e2 = e0.cross(e1)
        sc = (sz * r_.uniform(0.95, 1.3), sz * r_.uniform(0.8, 1.1), sz * r_.uniform(0.65, 0.9))
        cv = [c + e0 * sc[0], c - e0 * sc[0] * r_.uniform(0.7, 1.0), c + e1 * sc[1], c - e1 * sc[1] * r_.uniform(0.7, 1.0),
              c + e2 * sc[2], c - e2 * sc[2]]
        cf = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
        # keep the winding outward
        ff = []
        for f in cf:
            a_, b_, c_ = (cv[x] for x in f)
            ff.append(f if (b_ - a_).cross(c_ - a_).dot((a_ + b_ + c_) / 3 - c) > 0 else (f[0], f[2], f[1]))
        sw = vlib.R("sw_satin")
        m.add([tuple(v) for v in cv], ff, [[sw.uv(0.5, 0.5)] * 3 for _ in ff], S, jit(C("f3f1ec"), 0.03), "atlas", False)
        k += 1


# round 6 (judges, round 4: "muddy amber"): Helles is a lighter, yellower gold (round 4 e6a012, round 3 e0901c)
BEERS = {"helles": ("Helles", C("f5b71e")), "dunkles": ("Dunkles", C("5a2208")), "weiss": ("Weißbier", C("e8a232")),
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
             (0.22, -0.12, "mass", "helles"), (0.62, -0.075, "willi", "helles")]
    # (round 6 pass 2, headroom: the Willibecher of Dunkles that stood at (0.11, 0.10) behind the row is gone,
    # 8 full glasses now, act_glass_0..7, the last on the drip tray)
    tray = len(spots) - 1
    for i, (x, y, kind, beer) in enumerate(spots):
        on_tray = i == tray
        g = s.node(f"act_glass_{i}", (x, y, 0.022 if on_tray else 0.004))
        foam = s.node(f"foam_{i}", (0, 0, 0), parent=f"act_glass_{i}")
        rz = rng.uniform(-math.pi, math.pi) if kind == "mass" else 0
        M = T(0, 0, 0, rz=rz)
        # round 4: the full glasses on the counter wear vendor_glass_pint, a darker, fainter shell in lite (vlib)
        glass = {"mass": G.mass, "willi": G.willi, "weizen": G.weizen}[kind](g, M, mat="glass_pint")
        level = glass[1] - {"mass": 0.018, "willi": 0.016, "weizen": 0.03}[kind] - rng.uniform(0, 0.004)
        # round 6 pass 2: the heads sit inside the rim, so only the glass just pulled on the drip tray still has a
        # run of foam down the side facing the visitor (angle in the glass's own frame); the rng draw stays so
        # the glasses after it keep their levels
        spill = (-math.pi / 2 + rng.uniform(-0.7, 0.7) - rz) if i % 2 == 0 else 0
        spill = spill if on_tray else 0
        G.beer_fill(g, foam, M, glass, level, beer_col=BEERS[beer][1], spill=spill, seed=i * 1.7,
                    dome=0.013 if kind == "weizen" else None)
        short, gname = GLASS_NAMES[kind]
        s.item(f"act_glass_{i}", f"{short} of {BEERS[beer][0]}", "glass", glass=gname, beer=BEERS[beer][0])
        # beer coaster under each glass
        # (in lite too since round 6, as a plain disc: the lite set's bounds must match the full one's)
        if not on_tray:
            m.disc(0.054, seg(12, 8), "coaster", T(x, y, 0.0015, rz=drng.uniform(0, 6) if not lite() else 0.0), WHITE,
                   "atlas")
            if not lite():
                m.lathe([(0.054, 0.0), (0.054, 0.004)], 12, "paper", T(x, y, 0), C("e8e2d6"))
    # round 6: the Bierdeckel at the counter's left front, one per project in content/projects.md (one per ###
    # heading, read at build time) laid out side by side for the visitor to pick up, and the spares in a small
    # stack behind them. Each is act_coaster_<n> with write_coaster_<n>_front / _back (vprint.coaster).
    cs = content_projects.coasters()
    proj = [c for c in cs if c["project"]]
    spare = [c for c in cs if not c["project"]]
    xs = coaster_row(len(proj))
    for c, x in zip(proj, xs):
        j = c["i"]
        vprint.coaster(s, j, (x, -0.165 + 0.018 * ((j % 2) * 2 - 1) * 0.5), rng.uniform(-0.22, 0.22), c["colourway"],
                       f"Bierdeckel: {c['name']}", project=c["name"])
    for k, c in enumerate(spare):
        vprint.coaster(s, c["i"], (-1.125 + 0.004 * k, 0.168 - 0.003 * k), 0.4 + k * 0.9, c["colourway"],
                       c["name"], z=vprint.COASTER_T * k)
    # a wooden board of pretzels behind the coasters and a bar towel right of the tap tower
    G.board(m, T(-0.9, 0.06, 0), 0.32, 0.16, 0.018, C("c49a6c"))
    for k, (dx, dy, a) in enumerate(((-0.085, 0.0, 0.15), (0.07, 0.005, -0.2))):
        pretzel(m, T(-0.9 + dx, 0.06 + dy, 0.018, rz=a), s=0.95, seed=k)
    m.box((0.24, 0.15, 0.006), T(1.06, 0.1, 0.003, rz=-0.1), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    s.finish()
    return s


def coaster_texts():
    """Preview only: each project's name on its coaster's front and its summary on the back, in the engine's
    print style, to show the writing faces (vstage.preview_texts)."""
    out = {}
    for c in content_projects.coasters():
        if not c["project"]:
            continue
        out[f"write_coaster_{c['i']}_front"] = [(c["name"], 0.3, "oswald", "2a1c12"), (c["style"], 0.13, "garamond", "5a4030")]
        out[f"write_coaster_{c['i']}_back"] = [(c.get("summary", ""), 0.1, "garamond", "2a1c12")]
    return out


def coaster_row(n, x0=-1.13, x1=-0.75):
    """x of n coasters side by side at the left front of the counter (squeezed to overlap a little if many)."""
    if n <= 1:
        return [(x0 + x1) / 2] * n
    step = min(0.125, (x1 - x0) / (n - 1))
    w = step * (n - 1)
    c = (x0 + x1) / 2
    return [c - w / 2 + k * step for k in range(n)]


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
    # clean Maßkrüge upside down on a folded towel, ready for the next round (8-sided since round 6: the stall
    # grew and the clean glasses on the upper shelf are seen from a distance)
    m.box((0.5, 0.2, 0.012), T(-0.7, 0.01, 0.006), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k, x in enumerate((-0.86, -0.7, -0.54)):
        idx = 10 + k
        g = s.node(f"act_glass_{idx}", (x, 0.01 + (k % 2) * 0.03, 0.012), rot=(math.pi, 0, rng.uniform(0, TWO_PI)))
        G.mass(g, T(0, 0, -0.2108), n=8, lo=6)
        s.item(f"act_glass_{idx}", "Clean Maßkrug, upside down", "glass", glass="Maßkrug")
    # clean half-litre Willibecher upside down on a second towel
    m.box((0.36, 0.18, 0.01), T(-0.2, 0.02, 0.005), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k, x in enumerate((-0.3, -0.2, -0.1)):
        idx = 13 + k
        g = s.node(f"act_glass_{idx}", (x, 0.02 + (k % 2) * 0.04, 0.01), rot=(math.pi, 0, 0))
        G.willi(g, T(0, 0, -0.2058), n=8, lo=6)
        s.item(f"act_glass_{idx}", "Clean Willibecher, upside down", "glass", glass="Willibecher")
    # clean Weizengläser upside down on a third towel
    m.box((0.3, 0.16, 0.01), T(0.22, 0.02, 0.005), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k, x in enumerate((0.13, 0.22, 0.31)):
        idx = 16 + k
        g = s.node(f"act_glass_{idx}", (x, 0.02 + (k % 2) * 0.035, 0.01), rot=(math.pi, 0, 0))
        G.weizen(g, T(0, 0, -0.2512), n=8, lo=6)
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
                              # round 6: the Bierdeckel and the two full Maß of Helles
                              hero=((-0.93, -0.62, 0.34), (-0.84, -0.06, 0.06), 30), preview_text=lambda: coaster_texts(),
                              # round 6 pass 2: the heads of the Maß, Willibecher and Weizen from a visitor's eye
                              heroes={"foam": ((-0.42, -0.62, 0.46), (-0.42, -0.02, 0.17), 42)}),
    "prop_bier_back": dict(fn=back, slot="slot_shelf_1", stall="bierstand", kind="shelf", section=True, seed=32,
                           cam=((0.0, -2.05, 0.36), (0.0, 0.0, 0.15), 30),
                           hero=((-0.85, -0.8, 0.2), (-0.8, 0.0, 0.12), 38)),
    "prop_bier_shelf": dict(fn=shelf, slot="slot_shelf_2", stall="bierstand", kind="shelf2", section=True, seed=33,
                            cam=((0.0, -2.05, 0.3), (0.0, 0.0, 0.12), 30),
                            hero=((-0.35, -0.95, 0.3), (-0.35, 0.0, 0.1), 32)),
}
