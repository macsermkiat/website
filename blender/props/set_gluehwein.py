"""Glühwein stand goods: the counter (copper kettle, ladle, mugs), the back shelf (bottles, spices)
and the wine shelf above it.

prop_gluehwein_counter  -> slot_counter of stall_gluehwein (origin on the counter top, centred)
prop_gluehwein_shelf    -> slot_shelf_1 of stall_gluehwein (origin on the lower back shelf, centred)
prop_gluehwein_wine     -> slot_shelf_2 of stall_gluehwein (origin on the upper back shelf, centred)

Clickable goods are their own nodes with the origin at their base: act_mug_0..12 (0-9 on the counter,
10-12 spare on the shelf), act_bottle_0..9 (wine shelf) and act_bottle_12..17 (Glühwein shelf),
act_wineglass_0..2. The back shelves are 0.3 m deep with a 5 cm front lip, so shelf goods keep to
y -0.12..0.14.
"""
import math

from mathutils import Vector

import goods as G
import vlib
from vlib import C, T, WHITE, lite, rng, seg

TWO_PI = 2 * math.pi

MUG_NAMES = {
    "red": "Red Glühwein mug with gold stars", "blue": "Blue mug with white snowflakes",
    "cream": "Cream mug with a painted market skyline", "green": "Green mug with white fir trees",
    "brown": "Brown mug with iced hearts", "white": "White mug with red stars",
    "santa": "Red boot mug with a white cuff", "bluestar": "Blue boot mug with gold stars",
}


def copper_kettle(s, x, y):
    """Riveted copper Glühwein kettle on an iron burner ring, hinged lid (act_pot_lid), ladle (act_ladle)."""
    pot = s.node("act_pot", (x, y, 0))
    s.item("act_pot", "Copper Glühwein kettle", "kettle")
    n = seg(28, 10)
    iron = C("ffffff")
    # burner: a squat black ring with vent slots, three stubby feet
    pot.lathe([(0.15, 0.0), (0.16, 0.004), (0.16, 0.05), (0.15, 0.06), (0.14, 0.06)], n,
              vlib.RW("iron"), None, iron, "atlas", smooth=False)
    for k in range(3):
        a = TWO_PI * k / 3 + 0.3
        pot.box((0.03, 0.02, 0.012), T(0.155 * math.cos(a), 0.155 * math.sin(a), 0.006, rz=a), "iron", C("888888"))
    if not lite():
        for k in range(8):
            a = TWO_PI * k / 8
            pot.box((0.02, 0.004, 0.012), T(0.161 * math.cos(a), 0.161 * math.sin(a), 0.03, rz=a + math.pi / 2),
                    "sw_matte", C("0a0908"), skip=("nz", "pz"))
    # kettle body: hammered copper, bellied, with a rolled rim
    z0 = 0.06
    body = [(0.0, z0), (0.13, z0), (0.17, z0 + 0.02), (0.2, z0 + 0.13), (0.203, z0 + 0.25), (0.2, z0 + 0.33),
            (0.206, z0 + 0.345)]
    pot.lathe(body, n, vlib.RW("copper"), None, WHITE, "atlas")
    pot.torus(0.206, 0.009, n, seg(6, 4), "copper", T(0, 0, z0 + 0.35), C("e8d0c0"))
    pot.lathe([(0.198, z0 + 0.35), (0.19, z0 + 0.26)], n, "copper", None, C("9a6a58"), "atlas")
    # Glühwein surface with a few floating orange slices, star anise and a cinnamon stick
    liquid_z = z0 + 0.262
    pot.disc(0.19, n, "sw_wet", T(0, 0, liquid_z), C("3a0508"), "liquid")
    for k, (dx, dy, a) in enumerate(((-0.07, -0.05, 0.3), (0.06, 0.06, 1.2), (0.09, -0.07, 2.2))):
        G.orange_slice(pot, T(dx, dy, liquid_z - 0.002, rx=0.05, rz=a), r=0.032, t=0.004)
    G.star_anise(pot, T(0.0, -0.02, liquid_z - 0.001, rz=0.4))
    G.cinnamon_stick(pot, T(0.02, 0.11, liquid_z + 0.002, rz=0.5), L=0.09)
    # riveted seam band and two brass drop-ring handles
    if not lite():
        pot.lathe([(0.2035, z0 + 0.2), (0.2045, z0 + 0.21), (0.2035, z0 + 0.22)], n, "copper", None, C("c89080"))
    for sx in (-1, 1):
        pot.box((0.02, 0.04, 0.03), T(sx * 0.2, 0, z0 + 0.3), "brass", WHITE)
        pot.torus(0.035, 0.006, seg(14, 6), seg(5, 3), "brass", T(sx * 0.215, 0, z0 + 0.265, rx=math.pi / 2),
                  WHITE)
    # brass spigot low on the front with a T handle
    pot.cyl(0.013, 0.011, 0.05, 10, "brass", T(0, -0.19, z0 + 0.06, rx=math.pi / 2), WHITE)
    pot.cyl(0.009, 0.008, 0.035, 8, "brass", T(0, -0.235, z0 + 0.06), WHITE)
    pot.box((0.06, 0.01, 0.01), T(0, -0.236, z0 + 0.1), "brass", WHITE)
    pot.cyl(0.006, 0.006, 0.03, 6, "brass", T(0, -0.235, z0 + 0.03, rx=math.pi), WHITE)
    for sx in (-0.05, 0.05):
        pot.cyl(0.007, 0.007, 0.03, 6, "brass", T(sx - 0.015, 0.212, z0 + 0.358, ry=math.pi / 2), WHITE)
    # the lid: hinged at the back rim, propped open
    hinge = (0, 0.212, z0 + 0.358)
    lid = s.node("act_pot_lid", hinge, parent="act_pot", rot=(-0.62, 0, 0))
    s.item("act_pot_lid", "Kettle lid", "lid")
    lid_prof = [(0.214, -0.004), (0.216, 0.0), (0.2, 0.02), (0.15, 0.05), (0.08, 0.068), (0.0, 0.075)]
    lid.lathe(lid_prof, n, vlib.RW("copper"), T(0, -0.212, 0), WHITE, "atlas")
    lid.lathe([(0.0, 0.07), (0.2, 0.014), (0.21, -0.002)], n, "copper", T(0, -0.212, 0), C("8a5a48"), "atlas")
    lid.sphere(0.022, seg(10, 6), seg(6, 4), vlib.RW("wood"), T(0, -0.212, 0.09), C("5a3622"), scale=(1, 1, 0.8))
    lid.cyl(0.008, 0.012, 0.018, 8, "brass", T(0, -0.212, 0.07), WHITE)
    lid.box((0.04, 0.03, 0.006), T(0, -0.005, 0.0), "brass", WHITE)
    # ladle standing in the kettle, handle over the front rim
    lad = s.node("act_ladle", (0.07, -0.08, z0 + 0.18), parent="act_pot")
    s.item("act_ladle", "Ladle", "ladle")
    lad.lathe([(0.0, -0.05), (0.03, -0.045), (0.046, -0.012), (0.047, 0.0), (0.044, 0.0),
               (0.04, -0.028), (0.0, -0.042)], seg(12, 7), "steel", T(0, 0, -0.02), WHITE)
    pts = [Vector((0.03, 0.0, -0.02)), Vector((0.045, -0.02, 0.08)), Vector((0.06, -0.06, 0.19)),
           Vector((0.07, -0.12, 0.26)), Vector((0.08, -0.17, 0.28)), Vector((0.09, -0.19, 0.265))]
    lad.tube(pts, 0.006, seg(7, 4), "steel", None, WHITE)
    s.empty("act_steam", (0, 0, liquid_z + 0.02), parent="act_pot")
    s.item("act_steam", "Steam over the kettle", "effect")
    return pot


def mug(s, i, loc, style, boot=False, filled=False, upside_down=False, where="on the counter"):
    """One clickable mug, act_mug_<i>, origin at the point it rests on."""
    name = f"act_mug_{i}"
    rot = (math.pi, 0, rng.uniform(0, TWO_PI)) if upside_down else None
    node = s.node(name, loc, rot=rot)
    if boot:
        G.mug_boot(node, None, style, filled=filled, toe_angle=-math.pi / 2 + rng.uniform(-0.5, 0.5))
        top = 0.108
    elif upside_down:
        G.mug_classic(node, T(0, 0, -0.0968), style, handle_angle=0)
        top = None
    else:
        G.mug_classic(node, None, style, filled=filled, handle_angle=rng.uniform(-0.5, 0.5))
        top = G.MUG_RIM
    if filled:
        s.empty(f"act_steam_{i}", (0, 0, top - 0.015), parent=name)
        s.item(f"act_steam_{i}", f"Steam over mug {i}", "effect")
    label = MUG_NAMES[style] + (", full and steaming" if filled else "") + (", upside down to dry" if upside_down else "")
    s.item(name, label, "mug", style=style, shape="boot" if boot else "classic", where=where)


def counter():
    s = vlib.PropSet("prop_gluehwein_counter", "slot_counter", "gluehwein")
    m = s.static
    copper_kettle(s, 0.74, 0.03)
    # mugs: a front row ready to hand out (some filled, steaming), clean ones upside down on a tray
    styles = ["santa", "red", "blue", "cream", "green", "bluestar", "white", "brown", "red", "santa"]
    # three just filled beside the kettle, three clean ones at the left end
    row = [(0.44, -0.17), (0.33, -0.1), (-0.95, -0.12), (0.21, -0.17), (-0.8, -0.16), (-0.66, -0.11)]
    boot = {0, 5}
    filled = {0, 1, 3, 4}
    for i, (x, y) in enumerate(row):
        mug(s, i, (x, y, 0), styles[i], boot=i in boot, filled=i in filled)
    # tray with clean mugs upside down
    G.board(m, T(-0.62, 0.1, 0), 0.62, 0.2, 0.014, C("b88a5e"))
    m.box((0.6, 0.012, 0.022), T(-0.62, 0.005, 0.018), vlib.RW("wood"), C("a07448"))
    m.box((0.6, 0.012, 0.022), T(-0.62, 0.195, 0.018), vlib.RW("wood"), C("a07448"))
    for k, x in enumerate((-0.86, -0.7, -0.54, -0.38)):
        mug(s, 6 + k, (x, 0.1, 0.014), ["white", "cream", "brown", "red"][k], upside_down=True, where="on the tray")
    # a wooden bowl of oranges with cinnamon and anise, next to the kettle
    bx = -0.12
    G.bowl(m, T(bx, -0.02, 0), r=0.12, h=0.055, seg_n=20)
    for k, (dx, dy) in enumerate(((-0.04, -0.03), (0.045, -0.02), (0.0, 0.05), (0.05, 0.055))):
        G.orange(m, T(bx + dx, -0.02 + dy, 0.012 + (0.0 if k < 3 else 0.006), rz=k), r=0.033)
    G.orange_slice(m, T(bx - 0.03, -0.09, 0.05, rx=0.4, rz=0.3), r=0.03)
    for k in range(3 if not lite() else 1):
        G.cinnamon_stick(m, T(0.03 + k * 0.012, -0.14 + k * 0.01, 0.006 + k * 0.004, rz=0.4 + k * 0.1), L=0.1)
    G.star_anise(m, T(0.07, -0.05, 0.0, rz=0.2))
    # a ladle rest (small plate)
    m.disc(0.06, seg(16, 8), "ceramic", T(0.3, 0.12, 0.004), C("f4efe6"), "glaze")
    m.lathe([(0.06, 0.004), (0.066, 0.01), (0.0, 0.0)], seg(16, 8), "ceramic", T(0.3, 0.12, 0), C("f4efe6"), "glaze")
    s.finish()
    return s


SHELF_BOTTLES = [
    ("label_wine", C("1c3320"), "bordeaux", C("8a1a1a"), None, "Winzer-Glühwein, red"),
    ("label_wine", C("1c3320"), "bordeaux", C("8a1a1a"), None, "Winzer-Glühwein, red"),
    ("label_white", C("d8e4d0"), "schlegel", C("c8a040"), C("d8b048"), "White Glühwein from Riesling"),
    ("label_berry", C("141a38"), "bordeaux", C("2a2a6a"), None, "Blueberry Glühwein"),
    ("label_rum", C("5a3010"), "flask", C("1a1a1a"), C("6a2a08"), "Rum, for a Schuss"),
    ("label_punsch", C("e0e8e0"), "schlegel", C("b0282a"), C("8a0a10"), "Kinderpunsch, alcohol-free"),
]


def shelf():
    s = vlib.PropSet("prop_gluehwein_shelf", "slot_shelf_1", "gluehwein", footprint=(2.4, 0.3))
    m = s.static
    x = -1.12
    for k, (lab, gcol, kind, foil, liq, name) in enumerate(SHELF_BOTTLES):
        idx = 12 + k
        node = s.node(f"act_bottle_{idx}", (x, 0.02 + rng.uniform(-0.03, 0.03), 0), rot=(0, 0, rng.uniform(-0.25, 0.25)))
        G.bottle(node, None, lab, gcol, kind, foil, liq)
        s.item(f"act_bottle_{idx}", name, "bottle", where="Glühwein shelf")
        x += 0.1
    # spice jars in a row
    jars = [("jar_zimt", C("8a4b26"), "cinnamon"), ("jar_nelken", C("4a2412"), "almonds"),
            ("jar_anis", C("7a3a1a"), "almonds"), ("jar_orange", C("e07a20"), "peel"),
            ("jar_kardamom", C("8aa060"), "almonds")]
    x = -0.45
    for k, (lab, col, reg) in enumerate(jars):
        G.jar(m, T(x, -0.03 + (k % 2) * 0.05, 0, rz=rng.uniform(-0.2, 0.2)), lab, col, reg,
              h=0.11 + (k % 3) * 0.015, r=0.036)
        x += 0.09
    # a low crate of dried orange slices (stacked, overlapping)
    G.crate(m, T(0.2, 0.0, 0), 0.3, 0.2, 0.08, C("c89e70"))
    for k in range(9 if not lite() else 4):
        dx, dy = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.08)
        G.orange_slice(m, T(0.2 + dx, dy, 0.03 + rng.uniform(0, 0.05), rx=rng.uniform(-0.5, 0.5),
                            ry=rng.uniform(-0.5, 0.5), rz=rng.uniform(0, 6)), r=rng.uniform(0.026, 0.034))
    # bundles of cinnamon sticks tied with twine
    for b, by in enumerate((-0.03, 0.03)):
        for k in range(4 if not lite() else 2):
            a = TWO_PI * k / 4
            rr = 0.011
            G.cinnamon_stick(m, T(0.5, by + rr * math.cos(a), 0.018 + rr * math.sin(a), rz=math.pi / 2 + 0.05 * b),
                             L=0.14, r=0.0065)
        if not lite():
            n = 8
            G.twine(m, [(0.5, by + 0.019 * math.cos(TWO_PI * j / n), 0.018 + 0.019 * math.sin(TWO_PI * j / n))
                        for j in range(n + 1)])
    # a small bowl of star anise
    G.bowl(m, T(0.7, 0.0, 0), r=0.07, h=0.035, seg_n=14)
    for k in range(4 if not lite() else 2):
        G.star_anise(m, T(0.7 + rng.uniform(-0.035, 0.035), rng.uniform(-0.035, 0.035), 0.022 + k * 0.002,
                          rx=rng.uniform(-0.3, 0.3), rz=rng.uniform(0, 6)))
    # spare mugs on the right, two rows
    styles = ["red", "blue", "cream"]
    for k, (x, y) in enumerate(((0.95, 0.06), (1.05, 0.06), (1.0, -0.05))):
        mug(s, 10 + k, (x, y, 0), styles[k], where="spare, on the back shelf")
    s.finish()
    return s


WINES = [
    # label region, bottle, glass, capsule, display name
    ("wl_riesling_mosel", "schlegel", C("35602c"), C("2a5a2a"),
     "Riesling Kabinett feinherb, Mosel 2022 (Weingut am Laternenberg)"),
    ("wl_riesling_rheingau", "schlegel", C("5a3410"), C("c8a040"),
     "Riesling Spätlese, Rheingau 2021 (Weinhaus Glockenhof)"),
    ("wl_riesling_pfalz", "schlegel", C("46662a"), C("c8ccd0"), "Riesling trocken, Pfalz 2023 (Kellerei Sternschnuppe)"),
    ("wl_spaet_baden", "burgundy", C("1c2a18"), C("6a1020"),
     "Spätburgunder trocken, Baden 2020 (Weingut Mondscheinhang)"),
    ("wl_spaet_ahr", "burgundy", C("24301c"), C("141414"), "Spätburgunder, Ahr 2019 (Winzerhof Tannenleite)"),
    ("wl_dornfelder_rh", "bordeaux", C("1a2a1a"), C("4a1a48"),
     "Dornfelder halbtrocken, Rheinhessen 2022 (Weingut Schneehang)"),
    ("wl_dornfelder_pfalz", "bordeaux", C("1e2c1c"), C("9a1a18"), "Dornfelder trocken, Pfalz 2021 (Kellerei Kerzenschein)"),
    ("wl_silvaner_franken", "bocksbeutel", C("2e5a2a"), C("8a9a3a"),
     "Silvaner Kabinett trocken in a Bocksbeutel, Franken 2022 (Weingut zum Weihnachtsstern)"),
    ("wl_silvaner_rh", "schlegel", C("9ab488"), C("ece8e0"), "Silvaner trocken, Rheinhessen 2023 (Hof Nachtigallenruh)"),
    ("wl_riesling_eiswein", "half", C("6a4012"), C("c8a040"), "Riesling Eiswein, Rheingau 2018 (Weingut Eiszapfen)"),
]


def wine():
    """German reds and whites on the upper shelf: a row of bottles in a low rack, three glasses."""
    s = vlib.PropSet("prop_gluehwein_wine", "slot_shelf_2", "gluehwein", footprint=(2.4, 0.3))
    m = s.static
    # a low slatted rack the bottles stand in (a board with a front rail), and a wine crate as a riser
    G.board(m, T(-0.5, 0.01, 0), 1.3, 0.2, 0.014, C("a8845c"))
    m.box((1.3, 0.012, 0.04), T(-0.5, -0.085, 0.034), vlib.RW("wood"), C("8a6440"))
    m.box((0.34, 0.22, 0.12), T(0.5, 0.03, 0.06), vlib.RW("wood"), C("b89266"), skip=("nz",))   # a closed wine box
    x = -1.1
    for i, (lab, kind, glass, cap, name) in enumerate(WINES):
        on_crate = i >= 8
        w = 0.15 if kind == "bocksbeutel" else 0.1
        if on_crate:
            loc = (0.43 + (i - 8) * 0.13, 0.03, 0.12)
        else:
            x += w / 2
            loc = (x, 0.01 + rng.uniform(-0.01, 0.01), 0.014)
            x += w / 2 + 0.018
        node = s.node(f"act_bottle_{i}", loc, rot=(0, 0, rng.uniform(-0.15, 0.15)))
        G.bottle(node, None, lab, glass, kind, cap)
        s.item(f"act_bottle_{i}", name, "bottle", where="wine shelf")
    # three wine glasses on a small tray: a red, a white and a clean one
    G.board(m, T(1.0, 0.0, 0), 0.34, 0.2, 0.012, C("6a4228"))
    for k, (dx, dy, wcol, nm) in enumerate(((-0.1, -0.03, C("4a0612"), "Glass of Spätburgunder"),
                                            (0.0, 0.04, C("e8d890"), "Glass of Riesling"),
                                            (0.1, -0.02, None, "Clean wine glass"))):
        g = s.node(f"act_wineglass_{k}", (1.0 + dx, dy, 0.012))
        G.wine_glass(g, None, wcol)
        s.item(f"act_wineglass_{k}", nm, "wineglass")
    # a corkscrew and two corks
    if not lite():
        m.box((0.11, 0.012, 0.008), T(0.75, -0.08, 0.004, rz=0.3), "steel", WHITE)
        for dx in (0.0, 0.03):
            m.cyl(0.011, 0.011, 0.045, 8, "cinnamon", T(0.8 + dx, -0.1, 0.011, ry=math.pi / 2, rz=dx * 20),
                  C("d8b890"))
    s.finish()
    return s


SETS = {
    "prop_gluehwein_counter": dict(fn=counter, slot="slot_counter", stall="gluehwein", kind="counter", section=True,
                                   seed=21, cam=((-0.2, -1.6, 0.5), (-0.12, 0.0, 0.17), 25),
                                   hero=((0.5, -0.8, 0.38), (0.52, 0.0, 0.15), 40)),
    "prop_gluehwein_shelf": dict(fn=shelf, slot="slot_shelf_1", stall="gluehwein", kind="shelf", section=True, seed=22,
                                 cam=((0.0, -1.75, 0.22), (0.0, 0.0, 0.13), 32),
                                 hero=((-0.55, -0.75, 0.2), (-0.55, 0.0, 0.12), 40)),
    "prop_gluehwein_wine": dict(fn=wine, slot="slot_shelf_2", stall="gluehwein", kind="shelf2", section=True, seed=23,
                                cam=((0.0, -1.75, 0.25), (0.0, 0.0, 0.15), 32),
                                hero=((-0.55, -0.7, 0.2), (-0.55, 0.0, 0.14), 40)),
}
