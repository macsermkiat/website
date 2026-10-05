"""Round 8 (ADR 0004): the ornament shop's goods, prop_schmuck_<group>.glb (+ lite), at the slots of the
carpenter's stall_schmuck.glb (blender/stalls/schmuck_slots.json; it replaces deco_schmuck at deco-schmuck):

    prop_schmuck_rail_1   slot_rail_1   front rail over the counter: 16 glass baubles (two octaves) and the
                                        lit Herrnhut star in the middle
    prop_schmuck_rail_2   slot_rail_2   inner rail over the counter's back edge: figure ornaments (the pickle
                                        among green baubles, pine cone, clip-on bird, mushroom, icicles),
                                        straw stars, carved stars, angels, six more baubles
    prop_schmuck_rail_3   slot_rail_3   rail over the glass case: straw and carved stars, an angel, an icicle
    prop_schmuck_rail_4   slot_rail_4   short drop over the tree: clip-on birds and small straw stars
    prop_schmuck_counter  slot_counter  nutcracker (jaw), Räuchermännchen (smoke), Schwibbogen (candles),
                                        trays of baubles, boxes
    prop_schmuck_shelf    slot_shelf_1  the three shelf tiers (offsets from schmuck_slots.json): boxes, standing
                                        angels, straw stars, a pair of soldier nutcrackers, the menu board
    prop_schmuck_case     slot_cabinet  the glass case: a velvet tray of mirror baubles, angels on the glass shelf
    prop_schmuck_tree     slot_tree     the little display tree on the dais with hook_tree_<n> empties

Node rules (BUILD.md, "Ornament shop"): every ornament is act_orn_<kind>_<n> with its origin at its hanging
point (the ribbon's knot or the clip); standing pieces (nutcracker, smoker, Schwibbogen) at their base.
act_orn_herrnhut has an emissive bulb_warm core; act_orn_nutcracker_jaw is a child of the nutcracker, its
origin on the jaw's hinge (rotate about local X, negative opens); act_orn_smoker carries fx_smoke_1 at its
mouth; act_orn_schwibbogen carries act_orn_candle_<n>, each a flame with its origin at the wick.
items.json: name, label, action (ring | light | jaw | smoke | candles | hang | find), baubles a "note".
"""
import math

from mathutils import Matrix, Vector

import vlib
from vlib import C, T, WHITE, drng, jit, seg
import set_decofill as F
from set_deco import ROD_Y, ROD_Z, irng, nutcracker, rod, star_poly

TWO_PI = 2 * math.pi
MK, MG = "market", "market_glaze"
W = 3.4
STALL = "deco-schmuck"
# stall_schmuck.glb slot data (schmuck_slots.json): rail lengths and drops, shelf tiers relative to slot_shelf_1
SLOTS = __import__("json").load(open(__import__("os").path.join(vlib.REPO, "blender", "stalls", "schmuck_slots.json")))["slots"]
RAIL_R = 0.011
KNOT_Z = -(RAIL_R + 0.008)          # the ribbon's knot just under the brass rail (clear of it)
NOTES = ["C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6", "D6", "E6", "F6", "G6", "A6", "B6", "C7", "D7",
         "E7", "F7", "G7", "A7", "B7", "C8"]
COLOUR_NAME = {"a8161d": "deep red", "d8b048": "gold", "1d3a78": "midnight blue", "eeeae2": "snow white",
               "1f5a3a": "fir green", "6a1f52": "plum", "c8ccd0": "silver", "d8782a": "amber", "b01e24": "red",
               "8ab8d8": "ice blue", "e8a0b0": "rose", "1e6a6a": "teal", "f2f0ea": "white", "2a2a5a": "night blue"}


def orn(s, name, origin, display, label, action, detail, pivot="hang", **extra):
    from set_deco import item
    pv = "hang: the ribbon's knot or the clip; the ornament swings or turns about it" if pivot == "hang" else pivot
    return item(s, name, origin, display, detail, pivot=pv, label=label, action=action, **extra)


def ribbon(m, top, drop, col=C("d8b048"), r=0.0011):
    x, y, z = top
    m.tube([(x, y, z - 0.006), (x, y, z - drop)], r, 3, "sw_satin", None, col)
    if not vlib.lite():
        m.box((0.007, 0.016, 0.005), T(x, y, z + 0.004), "sw_satin", col, skip=("nz",))
    return Vector((x, y, z - drop))


def cap(m, p, r):
    """A gold cap with a wire loop at p (the top of the ornament)."""
    m.cyl(r * 0.3, r * 0.26, r * 0.32, 6 if not vlib.lite() else 4, "sw_metal", T(p.x, p.y, p.z - r * 0.3),
          C("d8c080"), caps=False)


def bauble(m, top, r, region, n=None, rings=None, scale=(1, 1, 1)):
    """A glass bauble hanging from `top` (the cap's loop): its own painted wrap from the market atlas."""
    n = n or (9 if not vlib.lite() else 7)
    rings = rings or (6 if not vlib.lite() else 5)
    c = Vector((top.x, top.y, top.z - r * 0.28 - r * scale[2]))
    m.sphere(r, n, rings, region, T(c.x, c.y, c.z, rz=math.pi / 2), WHITE, MG, scale=scale, v_by="z")
    cap(m, top, r)


def dome(m, M, r, h, region, n, rings, col=WHITE, mat=MK):
    """A dome (mushroom cap) with planar UVs from above, so the spots land as round spots."""
    reg = vlib.R(region)
    verts = [(0.0, 0.0, h)]
    for i in range(1, rings + 1):
        a = (math.pi / 2) * i / rings
        rr, zz = r * math.sin(a), h * math.cos(a)
        verts += [(rr * math.cos(TWO_PI * j / n), rr * math.sin(TWO_PI * j / n), zz) for j in range(n)]
    faces = [(0, 1 + j, 1 + (j + 1) % n) for j in range(n)]
    for i in range(rings - 1):
        a0, b0 = 1 + i * n, 1 + (i + 1) * n
        faces += [(a0 + j, b0 + j, b0 + (j + 1) % n, a0 + (j + 1) % n) for j in range(n)]
    uvs = [[reg.uv(0.5 + 0.5 * verts[i][0] / r, 0.5 + 0.5 * verts[i][1] / r) for i in f] for f in faces]
    m.add(verts, faces, uvs, M, col, mat, True)


# ------------------------------------------------------------------ figure ornaments
def pickle(m, top):
    """The Weihnachtsgurke: a warty green glass gherkin hanging nose down, slightly bent."""
    n = 8 if not vlib.lite() else 6
    L, r = 0.11, 0.017
    prof = [(0.004, 0.0), (r * 0.8, 0.012), (r, 0.035), (r * 1.05, 0.06), (r * 0.95, 0.085), (r * 0.6, 0.104), (0.0, L)]
    if vlib.lite():
        prof = [prof[0], prof[2], prof[4], prof[6]]
    M = T(top.x, top.y, top.z - r * 0.3, rx=math.pi, ry=0.12)
    m.lathe(prof, n, "pickle", M, WHITE, MG, v_by="z")
    cap(m, top, r * 1.4)


def pinecone(m, top):
    n = 8 if not vlib.lite() else 6
    prof = [(0.008, 0.0), (0.02, 0.012), (0.024, 0.03), (0.021, 0.055), (0.013, 0.075), (0.0, 0.088)]
    if vlib.lite():
        prof = [prof[0], prof[2], prof[4], prof[5]]
    m.lathe(prof, n, "pinecone", T(top.x, top.y, top.z - 0.006, rx=math.pi), WHITE, MG, v_by="z")
    cap(m, top, 0.03)


def icicle(m, top, L=0.13):
    n = 6 if not vlib.lite() else 5
    m.lathe([(0.0085, 0.0), (0.006, L * 0.4), (0.003, L * 0.8), (0.0, L)], n, "sw_vgloss",
            T(top.x, top.y, top.z - 0.005, rx=math.pi, rz=0.4), C("e2eef4"), "glaze")
    cap(m, top, 0.02)


def mushroom(m, top):
    """A glass fly agaric: white stem, red spotted cap, hanging on a short ribbon from the cap's top."""
    n = 8 if not vlib.lite() else 6
    zc = top.z - 0.004
    dome(m, T(top.x, top.y, zc - 0.022), 0.028, 0.022, "mushroom", n, 3 if not vlib.lite() else 2, mat=MG)
    m.lathe([(0.026, 0.0), (0.0, 0.002)], n, "sw_satin", T(top.x, top.y, zc - 0.022), C("f0e8d8"), "atlas")
    m.lathe([(0.011, -0.035), (0.013, -0.018), (0.009, 0.0)], n, "sw_gloss", T(top.x, top.y, zc - 0.022), C("f4f0e8"),
            "glaze", cap0=True)


def bird(m, clip):
    """A clip-on glass bird sitting on the rod: blue and white body, spun-glass tail, the clip under it."""
    n = 8 if not vlib.lite() else 6
    x, y, z = clip
    m.box((0.01, 0.008, 0.02), T(x, y, z), "sw_metal", C("d8c080"))
    M = T(x, y, z + 0.024, ry=math.pi / 2 + 0.15)
    m.lathe([(0.0, -0.045), (0.012, -0.03), (0.017, -0.008), (0.016, 0.012), (0.01, 0.028), (0.0, 0.036)], n, "bird",
            M, WHITE, MG, v_by="z")
    m.lathe([(0.003, 0.036), (0.0, 0.046)], 4, "sw_satin", M, C("e0a030"), "glaze")
    tail = [(-0.04, 0.0, 0.0), (-0.085, -0.016, 0.02), (-0.085, 0.016, 0.02)]
    m.add([(x + a, y + b, z + 0.024 + c) for a, b, c in tail], [(0, 1, 2), (0, 2, 1)],
          [[(0, 0), (1, 0), (0.5, 1)]] * 2, None, C("f4f6f8"), "atlas", False)


def straw_star(m, top, r=0.06):
    """A Strohstern: eight split-straw strips crossed at the centre, a red thread through the middle."""
    strips = 8 if not vlib.lite() else 4
    reg = vlib.R("straw")
    c = Vector((top.x, top.y, top.z - r - 0.01))
    for k in range(strips):
        a = math.pi * k / strips
        L = r * (1.0 if k % 2 == 0 else 0.72)
        w = 0.0045
        d = Vector((math.cos(a), 0, math.sin(a)))
        nrm = Vector((-math.sin(a), 0, math.cos(a))) * w / 2
        p = [c - d * L - nrm, c + d * L - nrm, c + d * L + nrm, c - d * L + nrm]
        yy = -0.0006 * (k % 2)
        quad = [(v.x, v.y + yy, v.z) for v in p]
        m.add(quad, [(0, 1, 2, 3), (3, 2, 1, 0)], [[reg.uv(0, 0), reg.uv(1, 0), reg.uv(1, 1), reg.uv(0, 1)]] * 2,
              None, C("e8c880"), "atlas", False)
    m.cyl(0.006, 0.006, 0.003, 6, "sw_satin", T(c.x, c.y - 0.0015, c.z, rx=math.pi / 2), C("b0282a"))


def wood_star(m, top, r=0.055):
    """A carved wooden star (Erzgebirge): a five-point star with a bevelled face and a gold-painted edge."""
    m.extrude(star_poly(r, r * 0.45, 5), 0.008, T(top.x, top.y + 0.004, top.z - r - 0.006, rx=math.pi / 2),
              vlib.RW("wood"), "sw_metal", C("d8b07a"), back=True, bevel=0.0 if vlib.lite() else 0.002)


def angel(m, top, s=1.0):
    """A small turned and painted Erzgebirge angel hanging from a loop on her head: white gown with gold dots,
    golden wings, a rosy face (market atlas 'angel')."""
    n = 6 if not vlib.lite() else 5
    S = T(top.x, top.y, top.z - 0.012) @ Matrix.Diagonal((s, s, s, 1))
    face = vlib.R("angel", (0.0, 0.62, 1.0, 1.0))
    gown = vlib.R("angel", (0.0, 0.0, 1.0, 0.55))
    m.lathe([(0.026, -0.09), (0.02, -0.06), (0.011, -0.03), (0.008, -0.022)], n, gown, S @ T(0, 0, 0, rz=-math.pi / 2),
            WHITE, MG, v_by="z", cap0=True)
    m.sphere(0.011, n, 4, face, S @ T(0, 0, -0.012, rz=-math.pi / 2), WHITE, MG)
    for sx in (-1, 1):
        wing = [(0.0, 0.0), (0.03, 0.012), (0.034, -0.012), (0.012, -0.03)]
        m.extrude([(sx * x, y) for x, y in wing][::sx], 0.002, S @ T(0, 0.006, -0.03, rx=math.pi / 2),
                  "sw_metal", "sw_metal", C("d8b048"), back=True)
    m.torus(0.009, 0.0012, 6, 3, "sw_metal", S @ T(0, 0, 0.0, rx=0.2), C("d8b048"))


def herrnhut(m, glow, c, R=0.12):
    """A 26-point Herrnhut star (18 square-based and 8 triangular points) with a warm bulb_warm core in
    `glow`. Points are pyramids of red paper; the core shows through the gaps."""
    lite = vlib.lite()
    dirs = []
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                if (x, y, z) == (0, 0, 0):
                    continue
                k = abs(x) + abs(y) + abs(z)
                if k <= 2:
                    dirs.append((Vector((x, y, z)).normalized(), 4))      # 6 face + 12 edge points
                else:
                    dirs.append((Vector((x, y, z)).normalized(), 3))      # 8 corner points
    base_r = R * 0.36
    for d, sides in dirs:
        if d.z < -0.9:                                                   # the bottom point is a short cone
            pass
        L = R if sides == 4 else R * 0.9
        q = d.to_track_quat('Z', 'Y')
        M = T(*c) @ q.to_matrix().to_4x4() @ T(0, 0, base_r * 0.9)
        b = base_r * (0.62 if sides == 4 else 0.5)
        pts = [(b * math.cos(TWO_PI * j / sides + math.pi / sides), b * math.sin(TWO_PI * j / sides + math.pi / sides), 0.0)
               for j in range(sides)]
        verts = pts + [(0.0, 0.0, L - base_r * 0.9)]
        faces = [(j, (j + 1) % sides, sides) for j in range(sides)]
        reg = vlib.R("herrnhut")
        uvs = [[reg.uv(0, 0), reg.uv(1, 0), reg.uv(0.5, 1)] for _ in faces]
        m.add(verts, faces, uvs, M, WHITE if (d.z > -0.5 or lite) else C("f2e8d8"), MK, False)
    glow.sphere(base_r * 1.15, 8 if not lite else 6, 5 if not lite else 4, "sw_satin", T(*c), WHITE, "bulb_warm")


# ================================================================== the sets
def rail_1():
    """Front rail over the counter (slot_rail_1, along +X): 16 baubles (two octaves of a scale) and the
    Herrnhut star in the middle. Knots sit under the rail (z = -rail radius)."""
    L = SLOTS["slot_rail_1"]["length"]
    s = vlib.PropSet("prop_schmuck_rail_1", "slot_rail_1", STALL, footprint=(L, 0.12))
    meta = __import__("atlas_market").BAUBLES
    step = (L - 0.16) / 16
    xs = [0.08 + step * k for k in range(17)]
    mid = xs.pop(8)
    kz = KNOT_Z
    for i, x in enumerate(xs):
        name, base, paint, kind, finish = meta[i]
        r = (0.032, 0.038, 0.045, 0.036)[i % 4]
        drop = 0.08 + 0.2 * ((i * 5) % 7) / 6
        cname = COLOUR_NAME.get(base, "glass")
        what = __import__("atlas_market").BAUBLE_LABELS[kind]
        fin = {"gloss": "glossy", "matte": "satin matt", "mirror": "mirror-silvered"}[finish]
        with orn(s, f"act_orn_bauble_{i}", (x, 0.0, kz), f"Glass bauble, {cname}",
                 f"Glaskugel, {cname} · {round(r * 200)} cm", "ring",
                 f"A mouth-blown Lauscha glass bauble, {fin} {cname} with {what}, {round(r * 200)} cm across. "
                 f"Tap it and it rings a soft {NOTES[i]}. 5 to 9 €.", note=NOTES[i], hangable=True, region=name) as bm:
            top = ribbon(bm, (x, 0.0, kz), drop, C(("d8b048", "b0282a", "e8e4dc")[i % 3]))
            bauble(bm, top, r, name)
    with orn(s, "act_orn_herrnhut", (mid, 0.0, kz), "Herrnhut star", "Herrnhuter Stern · 29 €", "light",
             "A paper Herrnhut star with 26 points, folded by hand in Herrnhut in Saxony since the 1850s: it "
             "lights from inside. Click it and it glows.", lit_material="bulb_warm") as hm:
        top = ribbon(hm, (mid, 0.0, kz), 0.05, C("e8e4dc"), 0.0016)
        hm.cyl(0.004, 0.004, 0.05, 5, "sw_matte", T(mid, 0.0, top.z - 0.05), C("f2ead8"), caps=False)
        glow = s.node("herrnhut_core", (mid, 0.0, top.z - 0.05 - 0.12), parent="act_orn_herrnhut")
        herrnhut(hm, glow, (mid, 0.0, top.z - 0.05 - 0.12), 0.11)
    # the core's mesh was built in set coordinates: move it into its node's frame
    _localise(s, "herrnhut_core", "act_orn_herrnhut")
    s.finish()
    return s


def _localise(s, child, parent):
    """A child node built in set coordinates: shift its verts into its own frame and make its loc relative to
    the parent node's origin (PropSet.finish parents without an inverse)."""
    locs = {name: loc for _, name, loc, _ in s.nodes}
    out = []
    for mm, name, loc, par in s.nodes:
        if name == child:
            mm.V[:] = [(x - loc[0], y - loc[1], z - loc[2]) for x, y, z in mm.V]
            p = locs[parent]
            loc = (loc[0] - p[0], loc[1] - p[1], loc[2] - p[2])
        out.append((mm, name, loc, par))
    s.nodes = out


def rail_2():
    """The inner rail over the counter's back edge (slot_rail_2, 0.31 m clear drop): the figure ornaments,
    straw and wooden stars, angels and six more baubles; the pickle hangs among the green ones."""
    L = SLOTS["slot_rail_2"]["length"]
    s = vlib.PropSet("prop_schmuck_rail_2", "slot_rail_2", STALL, footprint=(L, 0.12))
    RZ, RY = KNOT_Z, 0.0
    meta = __import__("atlas_market").BAUBLES
    plan = [("bauble", 16), ("strawstar", 0), ("angel", 0), ("pinecone", 0), ("bauble", 17), ("woodstar", 0),
            ("icicle", 0), ("bird", 0), ("strawstar", 1), ("bauble", 18), ("mushroom", 0), ("bauble", 19),
            ("pickle", None), ("bauble", 20), ("strawstar", 2), ("angel", 1), ("icicle", 1), ("woodstar", 1),
            ("bauble", 21), ("strawstar", 3)]
    xs = [0.07 + (L - 0.14) * i / (len(plan) - 1) for i in range(len(plan))]
    green = {18: 4, 19: 11, 20: 4, 21: 9}           # baubles round the pickle: fir green and teal wraps
    for i, ((kind, k), x) in enumerate(zip(plan, xs)):
        drop = 0.05 + 0.1 * ((i * 3) % 5) / 4
        knot = (x, RY, RZ)
        if kind == "bauble":
            j = green.get(k, k - 16 + 2) % len(meta)
            name, base, paint, kp, finish = meta[j]
            r = 0.03 + 0.006 * (i % 3)
            cname = COLOUR_NAME.get(base, "glass")
            with orn(s, f"act_orn_bauble_{k}", knot, f"Glass bauble, {cname}", f"Glaskugel, {cname}", "ring",
                     f"A smaller Lauscha bauble, {cname}, {round(r * 200)} cm. It rings a {NOTES[k]}.",
                     note=NOTES[k], hangable=True, region=name) as bm:
                bauble(bm, ribbon(bm, knot, drop), r, name)
        elif kind == "pickle":
            with orn(s, "act_orn_pickle", knot, "Christmas pickle", "Weihnachtsgurke · 6 €", "find",
                     "The Weihnachtsgurke, a green glass gherkin hidden among the green baubles. The legend says "
                     "whoever finds the pickle on the tree gets an extra present. You found it!", hangable=True,
                     reward=True) as pm:
                pickle(pm, ribbon(pm, knot, drop + 0.02, C("2a6a3a")))
        elif kind == "pinecone":
            with orn(s, f"act_orn_pinecone_{k}", knot, "Glass pine cone", "Tannenzapfen aus Glas", "hang",
                     "A blown-glass pine cone, brown with frosted gold tips, as the Thuringian glassblowers made "
                     "them before the round bauble. Click to hang it on the display tree.", hangable=True) as pm:
                pinecone(pm, ribbon(pm, knot, drop))
        elif kind == "icicle":
            with orn(s, f"act_orn_icicle_{k}", knot, "Glass icicle", "Eiszapfen aus Glas", "hang",
                     "A twisted clear-glass icicle with a gold cap: it catches every lamp in the shop.",
                     hangable=True) as im:
                icicle(im, ribbon(im, knot, drop * 0.6), 0.12 + 0.03 * k)
        elif kind == "mushroom":
            with orn(s, f"act_orn_mushroom_{k}", knot, "Glass mushroom", "Fliegenpilz aus Glas", "hang",
                     "A little glass fly agaric, red with white spots: a lucky charm on German trees.",
                     hangable=True) as mm:
                mushroom(mm, ribbon(mm, knot, drop))
        elif kind == "bird":
            clip = (x, RY, RAIL_R + 0.0105)
            with orn(s, f"act_orn_bird_{k}", clip, "Clip-on glass bird", "Vogel mit Klammer", "hang",
                     "A clip-on glass bird with a spun-glass tail, sitting on the rail: it clips to a branch.",
                     hangable=True, pivot="clip: the clip's foot on the rail; the bird sits above it") as bm:
                bird(bm, clip)
        elif kind == "strawstar":
            with orn(s, f"act_orn_strawstar_{k}", knot, "Straw star", "Strohstern · 1,50 €", "hang",
                     "A Strohstern of split straw strips crossed and tied with red thread: the oldest of German "
                     "tree ornaments, light enough for the thinnest twig.", hangable=True) as sm:
                straw_star(sm, ribbon(sm, knot, drop * 0.5, C("b0282a")), 0.055 + 0.01 * (k % 2))
        elif kind == "woodstar":
            with orn(s, f"act_orn_woodstar_{k}", knot, "Carved wooden star", "Holzstern, geschnitzt", "hang",
                     "A star carved from lime wood in the Erzgebirge, its edge painted gold.", hangable=True) as wm:
                wood_star(wm, ribbon(wm, knot, drop * 0.5, C("b0282a")))
        elif kind == "angel":
            with orn(s, f"act_orn_angel_{k}", knot, "Wooden angel", "Engel aus dem Erzgebirge", "hang",
                     "A turned and painted Erzgebirge angel in a white gown with golden dots and gold wings.",
                     hangable=True) as am:
                angel(am, ribbon(am, knot, drop * 0.4, C("d8b048")), 1.0)
    s.finish()
    return s


STRAW = ("Straw star", "Strohstern · 1,50 €", "A Strohstern of split straw strips crossed and tied with red thread: "
         "the oldest of German tree ornaments, light enough for the thinnest twig.")


def _short_rail(name, slot, plan, seed_tag):
    """A short rail (slot_rail_3 over the glass case, slot_rail_4 over the tree): a few light ornaments."""
    L = SLOTS[slot]["length"]
    s = vlib.PropSet(name, slot, STALL, footprint=(L, 0.12))
    xs = [0.08 + (L - 0.16) * i / max(1, len(plan) - 1) for i in range(len(plan))]
    for i, ((kind, k, drop), x) in enumerate(zip(plan, xs)):
        knot = (x, 0.0, KNOT_Z)
        if kind == "strawstar":
            with orn(s, f"act_orn_strawstar_{k}", knot, *STRAW[:2], "hang", STRAW[2], hangable=True) as sm:
                straw_star(sm, ribbon(sm, knot, drop, C("b0282a")), 0.05 + 0.012 * (k % 2))
        elif kind == "woodstar":
            with orn(s, f"act_orn_woodstar_{k}", knot, "Carved wooden star", "Holzstern, geschnitzt", "hang",
                     "A star carved from lime wood in the Erzgebirge, its edge painted gold.", hangable=True) as wm:
                wood_star(wm, ribbon(wm, knot, drop, C("b0282a")))
        elif kind == "angel":
            with orn(s, f"act_orn_angel_{k}", knot, "Wooden angel", "Engel aus dem Erzgebirge", "hang",
                     "A turned and painted Erzgebirge angel in a white gown with golden dots and gold wings.",
                     hangable=True) as am:
                angel(am, ribbon(am, knot, drop, C("d8b048")), 1.0)
        elif kind == "icicle":
            with orn(s, f"act_orn_icicle_{k}", knot, "Glass icicle", "Eiszapfen aus Glas", "hang",
                     "A twisted clear-glass icicle with a gold cap: it catches every lamp in the shop.",
                     hangable=True) as im:
                icicle(im, ribbon(im, knot, drop), 0.15)
        elif kind == "bird":
            clip = (x, 0.0, RAIL_R + 0.0105)
            with orn(s, f"act_orn_bird_{k}", clip, "Clip-on glass bird", "Vogel mit Klammer", "hang",
                     "A clip-on glass bird with a spun-glass tail, sitting on the rail: it clips to a branch.",
                     hangable=True, pivot="clip: the clip's foot on the rail; the bird sits above it") as bm:
                bird(bm, clip)
    s.finish()
    return s


def rail_3():
    return _short_rail("prop_schmuck_rail_3", "slot_rail_3",
                       [("strawstar", 4, 0.12), ("angel", 2, 0.06), ("woodstar", 2, 0.16), ("icicle", 2, 0.05),
                        ("strawstar", 5, 0.09)], "r3")


def rail_4():
    return _short_rail("prop_schmuck_rail_4", "slot_rail_4",
                       [("bird", 1, 0), ("strawstar", 6, 0.04), ("woodstar", 3, 0.03), ("bird", 2, 0)], "r4")


def smoker(m, M):
    """A Räuchermännchen (incense smoker): a turned wooden pipe smoker, about 21 cm, in a green coat and a
    fur hat, the mouth a round hole where the smoke comes out."""
    n = seg(8, 6)
    m.cyl(0.045, 0.045, 0.015, n, vlib.RW("wood"), M, C("6a4a2c"))
    for sx in (-1, 1):
        m.cyl(0.013, 0.013, 0.055, n, "sw_gloss", M @ T(sx * 0.016, 0, 0.015), C("2a2a2a"), "glaze", caps=False)
    m.lathe([(0.0, 0.07), (0.036, 0.07), (0.038, 0.1), (0.032, 0.14), (0.026, 0.15)], n, "sw_gloss", M, C("2a5a3a"),
            "glaze")
    for sx in (-1, 1):
        m.cyl(0.009, 0.008, 0.06, 5, "sw_gloss", M @ T(sx * 0.036, -0.004, 0.142, ry=sx * 0.3), C("2a5a3a"), "glaze")
    m.cyl(0.025, 0.025, 0.045, n, "sw_gloss", M @ T(0, 0, 0.15), C("f0c8a0"), "glaze")
    m.box((0.04, 0.003, 0.04), M @ T(0, -0.0255, 0.172), "smoker_face", WHITE, MK, faces={"ny": "smoker_face"})
    m.lathe([(0.027, 0.193), (0.031, 0.2), (0.03, 0.225), (0.0, 0.232)], n, "sw_matte", M, C("5a3a22"), "atlas")
    # the long pipe from the mouth down to a bowl at his chest
    m.tube([(0.0, -0.027, 0.165), (0.012, -0.05, 0.14), (0.018, -0.06, 0.11)], 0.003, 4, vlib.RW("wood"), M,
           C("3a2414"))
    m.cyl(0.009, 0.008, 0.018, 6, vlib.RW("wood"), M @ T(0.018, -0.06, 0.1), C("3a2414"))


def schwibbogen(s, m, M, origin, n_candles=7):
    """A Schwibbogen: a fretwork candle arch, 46 cm, dark-stained: base plank, the arch band, a fretwork scene
    (firs, a church and two miners) and seven candles on the arch, each flame an act_orn_candle_<n> node."""
    Wd, H, band = 0.46, 0.27, 0.03
    dark = C("4a2e1a")
    m.box((Wd + 0.04, 0.07, 0.022), M @ T(0, 0, 0.011), vlib.RW("wood"), C("5a3a22"), skip=("nz",))
    nseg = 14 if not vlib.lite() else 8
    outer = [(Wd / 2 * math.cos(math.pi * i / nseg), 0.022 + (H - 0.03) * math.sin(math.pi * i / nseg)) for i in range(nseg + 1)]
    inner = [((Wd / 2 - band) * math.cos(math.pi * i / nseg), 0.022 + (H - 0.03 - band) * math.sin(math.pi * i / nseg))
             for i in range(nseg + 1)]
    poly = outer + inner[::-1]
    m.extrude(poly[::-1] if F_area(poly) < 0 else poly, 0.012, M @ T(0, 0.006, 0, rx=math.pi / 2), vlib.RW("wood"),
              vlib.RW("wood"), dark, back=True)
    scene = [  # (polygon in arch x/z, colour)
        ([(-0.17, 0.022), (-0.11, 0.022), (-0.14, 0.13)], C("3a2414")),
        ([(-0.19, 0.022), (-0.15, 0.022), (-0.17, 0.09)], C("3a2414")),
        ([(0.11, 0.022), (0.17, 0.022), (0.14, 0.12)], C("3a2414")),
        ([(-0.05, 0.022), (0.05, 0.022), (0.05, 0.09), (0.0, 0.13), (-0.05, 0.09)], C("3a2414")),
        ([(0.025, 0.09), (0.04, 0.09), (0.04, 0.17), (0.0325, 0.19), (0.025, 0.17)], C("3a2414")),
        ([(-0.1, 0.022), (-0.075, 0.022), (-0.078, 0.08), (-0.087, 0.095), (-0.097, 0.08)], C("3a2414")),
        ([(0.075, 0.022), (0.1, 0.022), (0.097, 0.08), (0.087, 0.095), (0.078, 0.08)], C("3a2414")),
    ]
    for poly2, col in scene:
        p = poly2 if F_area(poly2) > 0 else poly2[::-1]
        m.extrude(p, 0.008, M @ T(0, 0.004, 0, rx=math.pi / 2), vlib.RW("wood"), vlib.RW("wood"), col,
                  back=not vlib.lite())
    for i in range(n_candles):
        a = math.pi * (i + 0.5) / n_candles
        cx, cz = (Wd / 2 - band / 2) * math.cos(a), 0.022 + (H - 0.03 - band / 2) * math.sin(a)
        Mc = M @ T(cx, 0.0, cz)
        m.cyl(0.009, 0.009, 0.008, 6, "sw_metal", Mc @ T(0, 0, band / 2 - 0.004), C("d8b048"), caps=True)
        m.cyl(0.0055, 0.0055, 0.05, seg(6, 5), vlib.RW("wax"), Mc @ T(0, 0, band / 2 + 0.004), C("f6f0e2"), caps=True)
        wick = Mc @ Vector((0, 0, band / 2 + 0.054))
        name = f"act_orn_candle_{i}"
        fl = s.node(name, (wick.x - origin[0], wick.y - origin[1], wick.z - origin[2]), parent="act_orn_schwibbogen")
        fl.lathe([(0.0, 0.0), (0.0035, 0.007), (0.002, 0.017), (0.0, 0.026)], 6, "sw_satin", None, WHITE, "flame")
        s.item(name, f"Schwibbogen candle {i + 1}", "deco", pivot="the wick: the flame's foot",
               label=f"Kerze {i + 1} am Schwibbogen", action="light", order=i,
               detail="One of the seven candles on the Schwibbogen; they light one after another.")


def F_area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def counter():
    s = vlib.PropSet("prop_schmuck_counter", "slot_counter", STALL)
    m = s.static
    # the big nutcracker at the left end, his jaw a node of its own
    nx, ny, sc = -1.08, 0.06, 1.15
    with orn(s, "act_orn_nutcracker", (nx, ny, 0.0), "Nutcracker", "Nussknacker, König · 39 €", "jaw",
             "A king nutcracker from the Erzgebirge, 39 cm, turned and painted: lift the lever at his back and his "
             "jaw opens for a walnut.", pivot="base", jaw="act_orn_nutcracker_jaw") as nm:
        nutcracker(nm, T(nx, ny, 0.0), C("a8181c"), C("f2ead8"), C("d8b048"), s=sc)
    jaw_z = 0.226 * sc
    jaw = s.node("act_orn_nutcracker_jaw", (0.0, -0.012 * sc, jaw_z), parent="act_orn_nutcracker")
    jaw.box((0.042 * sc, 0.03 * sc, 0.022 * sc), T(0, -0.008 * sc, -0.011 * sc), "sw_gloss", C("f4f1ea"), "glaze")
    jaw.box((0.03 * sc, 0.004, 0.006 * sc), T(0, -0.0235 * sc, -0.002 * sc), "sw_gloss", C("8a1a1a"), "glaze")
    s.item("act_orn_nutcracker_jaw", "Nutcracker's jaw", "deco", pivot="the jaw's hinge; rotate about local X "
           "(negative opens, about 0.5 rad)", label="Unterkiefer des Nussknackers", action="jaw",
           detail="The nutcracker's lower jaw and white beard.")
    # the Räuchermännchen, smoke at his mouth
    sx_, sy_ = -0.82, -0.08
    with orn(s, "act_orn_smoker", (sx_, sy_, 0.0), "Räuchermännchen", "Räuchermännchen · 32 €", "smoke",
             "A Räuchermännchen, the Erzgebirge incense smoker: lift off his top half, light a little cone of "
             "incense inside, and fir-scented smoke curls out of his mouth.", pivot="base", fx="fx_smoke_1") as rm:
        smoker(rm, T(sx_, sy_, 0.0))
    s.empty("fx_smoke_1", (0.0, -0.03, 0.172), parent="act_orn_smoker")
    # the Schwibbogen at the back left of centre
    bx, by = -0.38, 0.12
    with orn(s, "act_orn_schwibbogen", (bx, by, 0.0), "Schwibbogen", "Schwibbogen · 45 €", "candles",
             "A Schwibbogen, the candle arch of the Erzgebirge mining towns, with firs, a church and two miners "
             "cut in fretwork: its seven candles light one by one.", pivot="base",
             candles=[f"act_orn_candle_{i}" for i in range(7)]) as am:
        schwibbogen(s, am, T(bx, by, 0.0), (bx, by, 0.0))
    # trays of baubles in egg crates on the right half of the counter, boxes, price tags
    meta = __import__("atlas_market").BAUBLES
    for t, tx in enumerate((0.12, 0.6)):
        Mt = T(tx, -0.02, 0)
        m.box((0.44, 0.3, 0.035), Mt @ T(0, 0, 0.0175), "kraft", C("d8c8a8"), skip=("nz",))
        m.box((0.44, 0.004, 0.14), Mt @ T(0, 0.155, 0.1, rx=-0.2), "kraft", C("d0bf9c"))
        for k in range(12):
            if (vlib.lite() and k % 2) or k in (3, 6, 9):      # a few sold-out holes
                continue
            cx, cy = -0.165 + (k % 4) * 0.11, -0.1 + (k // 4) * 0.1
            r = 0.034
            reg = meta[(k * 5 + t * 7) % len(meta)][0]
            c = Mt @ Vector((cx, cy, 0.035 + r * 0.6))
            m.sphere(r, seg(7, 6), seg(5, 3), reg, T(c.x, c.y, c.z, rx=drng.uniform(-0.4, 0.4), rz=drng.uniform(0, 6)),
                     WHITE, MG)
    for j in range(3):
        F.carton(m, T(1.08, 0.08 - j * 0.004, j * 0.08, rz=0.05 * (j - 1)), 0.2, 0.14, 0.08, "bx_schmuck")
    from set_deco import price_tag
    for k, (x, y) in enumerate(((0.12, -0.21), (0.6, -0.21), (-0.82, -0.2))):
        price_tag(m, T(x, y + 0.01, 0), 4)
    s.finish()
    return s


def _tier(n):
    """Offset of shelf tier n (1..3) from slot_shelf_1 (schmuck_slots.json): the tiers step back and up."""
    p0, p = SLOTS["slot_shelf_1"]["position"], SLOTS[f"slot_shelf_{n}"]["position"]
    return p[0] - p0[0], p[1] - p0[1], p[2] - p0[2]


def shelf():
    """The three tiers behind the counter (one set at slot_shelf_1; tiers 2 and 3 by their offsets)."""
    L = SLOTS["slot_shelf_1"]["length"]
    s = vlib.PropSet("prop_schmuck_shelf", "slot_shelf_1", STALL, footprint=(L, SLOTS["slot_shelf_1"]["depth"]))
    m = s.static
    hw = L / 2 - 0.12
    # tier 1 (0.42 deep, 0.30 clear): stacked ornament cartons
    _, y1, _ = _tier(1)
    for k, x in enumerate((-hw + 0.1, -hw + 0.32, hw - 0.32, hw - 0.1)):
        for j in range(2 if k % 2 == 0 else 1):
            F.carton(m, T(x, y1 + 0.07, j * 0.08, rz=drng.uniform(-0.04, 0.04)), 0.2, 0.12, 0.08, "bx_schmuck")
    for x in (-0.55, -0.3, 0.3, 0.55):
        F.carton(m, T(x, y1 + 0.05, 0.0, rz=drng.uniform(-0.04, 0.04)), 0.22, 0.2, 0.05, "bx_schmuck")
        F.carton(m, T(x, y1 + 0.05, 0.05, rz=drng.uniform(-0.04, 0.04)), 0.22, 0.2, 0.05, "bx_schmuck")
    # tier 2 (0.33 deep): a row of standing angels and straw stars on little stands
    x2, y2, z2 = _tier(2)
    for k, x in enumerate((-0.95, -0.82, -0.69, 0.69, 0.82, 0.95)):
        angel(m, Vector((x, y2 + 0.02, z2 + 0.1 + 0.012)), 1.1)
        m.cyl(0.03, 0.03, 0.01, 6, vlib.RW("wood"), T(x, y2 + 0.02, z2), C("6a4a2c"))
    for k, x in enumerate((-0.4, 0.0, 0.4)):
        m.box((0.012, 0.012, 0.15), T(x, y2 + 0.06, z2 + 0.075), vlib.RW("wood"), C("6a4a2c"))
        straw_star(m, Vector((x, y2 + 0.05, z2 + 0.16)), 0.065)
    for x in (-hw + 0.12, hw - 0.12):
        for j in range(3):
            F.carton(m, T(x, y2 + 0.04, z2 + j * 0.04), 0.22, 0.2, 0.04, "bx_schmuck")
    # tier 3 (0.24 deep, 0.46 clear): the menu board and a pair of soldier nutcrackers guarding it
    x3, y3, z3 = _tier(3)
    F.menu_board(m, T(0.0, y3 + 0.05, z3), 0.38, 0.28, "mn_schmuck")
    for sx in (-1, 1):
        nutcracker(m, T(sx * 0.34, y3, z3), C("1d3a78") if sx < 0 else C("1f5a3a"), C("f2ead8"), C("141414"), s=0.62)
    for x in (-hw + 0.15, -hw + 0.42, hw - 0.42, hw - 0.15):
        F.carton(m, T(x, y3 + 0.03, z3), 0.2, 0.14, 0.14, "bx_schmuck")
    s.finish()
    return s


def case():
    """The glass case in the left bay (slot_cabinet, on its velvet floor; a glass shelf at shelf_height):
    a velvet tray of mirror and painted baubles below, standing angels and boxed stars on the glass shelf."""
    sw, sd, sh = SLOTS["slot_cabinet"]["inner_size"]
    gz = SLOTS["slot_cabinet"]["shelf_height"]
    s = vlib.PropSet("prop_schmuck_case", "slot_cabinet", STALL, footprint=(sw, sd))
    m = s.static
    meta = __import__("atlas_market").BAUBLES
    # floor: an open presentation box lined in cream satin, 2 x 5 baubles, and a lidded box leaning behind
    m.box((0.5, 0.2, 0.028), T(0.0, -0.03, 0.014), "kraft", C("e8dcc0"), skip=("nz",))
    for k in range(10):
        cx, cy, r = -0.2 + (k % 5) * 0.1, -0.075 + (k // 5) * 0.09, 0.034
        m.sphere(r, seg(7, 6), seg(5, 4), meta[(k * 7 + 3) % len(meta)][0], T(cx, cy, 0.028 + r * 0.7, rz=k), WHITE, MG)
    F.carton(m, T(0.0, 0.11, 0.0, rx=-0.12), 0.5, 0.03, 0.2, "bx_schmuck")
    # the glass shelf: three angels and two carved stars on stands
    for k, x in enumerate((-0.12, 0.0, 0.12)):
        m.cyl(0.028, 0.028, 0.01, 6, vlib.RW("wood"), T(x, 0.0, gz), C("6a4a2c"))
        angel(m, Vector((x, 0.0, gz + 0.1 + 0.022)), 1.15)
    for x in (-0.26, 0.26):
        m.box((0.012, 0.012, 0.1), T(x, 0.03, gz + 0.05), vlib.RW("wood"), C("6a4a2c"))
        wood_star(m, Vector((x, 0.024, gz + 0.17)), 0.06)
    s.finish()
    return s


def tree():
    """The display tree on the dais in the right bay (slot_tree, top 0.5 x 0.4, 1.45 m max): a 1.15 m fir in a
    wooden tub, a gold star on top, twelve hook_tree_<n> empties at branch tips where a clicked ornament can be
    hung (the engine hangs it by its own origin, the hanging point)."""
    s = vlib.PropSet("prop_schmuck_tree", "slot_tree", STALL, footprint=tuple(SLOTS["slot_tree"]["top_size"]))
    m = s.static
    x0, y0 = 0.0, 0.0
    n = seg(12, 7)
    m.lathe([(0.14, 0.0), (0.17, 0.2), (0.18, 0.22), (0.0, 0.22)], n, vlib.RW("stave"), T(x0, y0, 0), C("8a5a34"))
    for z in (0.05, 0.17):
        m.cyl(0.145 + z * 0.15, 0.145 + z * 0.15, 0.015, n, "sw_metal_rough", T(x0, y0, z), C("3a3a3a"), caps=False)
    m.cyl(0.025, 0.02, 0.2, 6, vlib.RW("wood"), T(x0, y0, 0.2), C("4a3020"), caps=False)
    tiers = [(0.34, 0.3, 0.56), (0.29, 0.48, 0.74), (0.23, 0.64, 0.9), (0.16, 0.8, 1.04), (0.1, 0.94, 1.14)]
    if vlib.lite():
        tiers = [tiers[0], tiers[2], tiers[4]]
    for r, z0, z1 in tiers:
        rr = [r * (1 + 0.12 * ((j * 7) % 3 - 1)) for j in range(n)]
        ring0 = [(x0 + rr[j] * math.cos(TWO_PI * j / n), y0 + rr[j] * math.sin(TWO_PI * j / n), z0 - 0.02 * (j % 2))
                 for j in range(n)]
        mid = [(x0 + rr[j] * 0.55 * math.cos(TWO_PI * (j + 0.5) / n), y0 + rr[j] * 0.55 * math.sin(TWO_PI * (j + 0.5) / n),
                (z0 + z1) / 2) for j in range(n)]
        top = [(x0, y0, z1)] * n
        m.loft([ring0, mid, top], "garland", None, C("ffffff"), MK, closed=True, cap0=True)
    m.extrude(star_poly(0.07, 0.03, 5), 0.01, T(x0, y0 + 0.004, 1.2, rx=math.pi / 2), "sw_metal", "sw_metal", C("d8b048"))
    meta = __import__("atlas_market").BAUBLES
    hooks = []
    for ti, (r, z0, z1) in enumerate([(0.34, 0.3, 0.56), (0.29, 0.48, 0.74), (0.23, 0.64, 0.9), (0.16, 0.8, 1.04)]):
        for j in range(3 if ti < 3 else 2):
            a = -math.pi / 2 + (j - (1 if ti < 3 else 0.5)) * 0.85 + 0.3 * (ti % 2)
            rr = r * 0.82
            hooks.append((x0 + rr * math.cos(a), y0 + rr * math.sin(a), z0 + 0.03))
    hooks += [(x0 + 0.28 * math.cos(a), y0 + 0.28 * math.sin(a), 0.36) for a in (0.6, 2.5)]
    for i, h in enumerate(hooks):
        s.empty(f"hook_tree_{i}", h)
    for i in (1, 4, 8):
        hx, hy, hz = hooks[i]
        bauble(m, Vector((hx, hy, hz)), 0.03, meta[(i * 3) % len(meta)][0], n=seg(8, 6), rings=seg(5, 4))
    s.report_extra = {"hooks": len(hooks)}
    s.finish()
    return s


def _def(fn, slot, seed, kind, cam, label):
    return dict(fn=fn, slot=slot, stall=STALL, kind=kind, section=False, seed=seed, label=label, width=4.5,
                cam=cam, fill=True, seat=("hang" if slot.startswith("slot_rail") else
                                          "stand" if slot == "slot_tree" else "board"))


SETS = {
    "prop_schmuck_rail_1": _def(rail_1, "slot_rail_1", 81, "rail", None, "Ornament shop: front rail"),
    "prop_schmuck_rail_2": _def(rail_2, "slot_rail_2", 82, "rail", None, "Ornament shop: inner rail"),
    "prop_schmuck_rail_3": _def(rail_3, "slot_rail_3", 86, "rail", None, "Ornament shop: rail over the case"),
    "prop_schmuck_rail_4": _def(rail_4, "slot_rail_4", 87, "rail", None, "Ornament shop: rail over the tree"),
    "prop_schmuck_counter": _def(counter, "slot_counter", 83, "counter", None, "Ornament shop: counter"),
    "prop_schmuck_shelf": _def(shelf, "slot_shelf_1", 84, "shelf", None, "Ornament shop: shelves"),
    "prop_schmuck_case": _def(case, "slot_cabinet", 88, "case", None, "Ornament shop: glass case"),
    "prop_schmuck_tree": _def(tree, "slot_tree", 85, "front", None, "Ornament shop: display tree"),
}
