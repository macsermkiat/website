"""Glühwein stand goods: the counter (copper kettle, ladle, mugs), the back shelf (bottles, spices)
and the wine shelf above it.

prop_gluehwein_counter  -> slot_counter of stall_gluehwein (origin on the counter top, centred)
prop_gluehwein_shelf    -> slot_shelf_1 of stall_gluehwein (origin on the lower back shelf, centred)
prop_gluehwein_wine     -> slot_shelf_2 of stall_gluehwein (origin on the upper back shelf, centred)

Clickable goods are their own nodes with the origin at their base: act_mug_0..15 (0-9 on the counter,
10-15 spare on the shelf), act_bottle_0..11 (wine shelf) and act_bottle_12..17 (Glühwein shelf),
act_wineglass_0..4. Round 6: every wine bottle carries a back label with a blank writing strip,
write_label_<n> (n = the bottle's number), and cam_read_label_<n> behind it. The back shelves are 0.3 m deep with a 5 cm front lip, so shelf goods keep to
y -0.12..0.14.
"""
import math

from mathutils import Vector

import goods as G
import vlib
import vprint
from vlib import C, T, WHITE, drng, lite, rng, seg

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
    liquid_z = z0 + 0.315
    pot.disc(0.19, n, "sw_wet", T(0, 0, liquid_z), C("4a0610"), "liquid")
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
    # the lid: hinged at the back rim, just ajar (14 degrees) so the steam gets out. The engine's pour
    # swings it 0.35 rad further open and back. Ajar, it stays 7 cm inside the counter's back edge.
    hinge = (0, 0.212, z0 + 0.358)
    lid = s.node("act_pot_lid", hinge, parent="act_pot", rot=(-0.25, 0, 0))
    s.item("act_pot_lid", "Kettle lid", "lid")
    lid_prof = [(0.214, -0.004), (0.216, 0.0), (0.2, 0.02), (0.15, 0.05), (0.08, 0.068), (0.0, 0.075)]
    nl = n if not lite() else 12            # a multiple of 4 keeps the lid's front and back edge where the full one has them
    lid.lathe(lid_prof, nl, vlib.RW("copper"), T(0, -0.212, 0), WHITE, "atlas")
    lid.lathe([(0.0, 0.07), (0.2, 0.014), (0.21, -0.002)], nl, "copper", T(0, -0.212, 0), C("8a5a48"), "atlas")
    lid.sphere(0.022, seg(10, 6), seg(6, 4), vlib.RW("wood"), T(0, -0.212, 0.09), C("5a3622"), scale=(1, 1, 0.8))
    lid.cyl(0.008, 0.012, 0.018, 8, "brass", T(0, -0.212, 0.07), WHITE)
    lid.box((0.04, 0.03, 0.006), T(0, -0.005, 0.0), "brass", WHITE)
    s.empty("act_steam", (0, 0, liquid_z + 0.02), parent="act_pot")
    s.item("act_steam", "Steam over the kettle", "effect")
    return pot


def ladle(s, x, y):
    """Steel ladle (act_ladle) with its bowl on the ladle-rest plate, a last drop of Glühwein in it, the
    handle leaning on the kettle's side. Origin under the bowl, on the plate."""
    lad = s.node("act_ladle", (x, y, 0.004))
    s.item("act_ladle", "Ladle", "ladle")
    n = seg(14, 7)
    outer = [(0.0, 0.0), (0.028, 0.004), (0.042, 0.016), (0.048, 0.034)]
    inner = [(0.0455, 0.035), (0.039, 0.019), (0.026, 0.008), (0.0, 0.0055)]
    if lite():
        outer, inner = [outer[0], outer[2], outer[3]], [inner[0], inner[2], inner[3]]
    lad.lathe(outer + [(0.049, 0.036)] + inner, n, "steel", None, WHITE)
    lad.disc(0.036, n, "sw_wet", T(0, 0, 0.016), C("3a0508"), "liquid")
    # handle: from the rim toward the kettle, rising to lean on its side, a hook at the end
    ctrl = [Vector((0.046, -0.004, 0.034)), Vector((0.09, -0.016, 0.075)), Vector((0.17, -0.034, 0.16)),
            Vector((0.228, -0.046, 0.232)), Vector((0.236, -0.05, 0.25))]
    pts = G.spline(ctrl, 1 if lite() else 2)
    lad.tube(pts, 0.0055, seg(6, 4), "steel", None, WHITE, radii=[0.007 - 0.0022 * i / (len(pts) - 1) for i in range(len(pts))])
    # the hook at the handle's end (lite: a coarser one, so the ladle keeps its full reach)
    lad.torus(0.012, 0.0035, 8 if not lite() else 6, 4 if not lite() else 3, "steel", T(0.24, -0.052, 0.262, ry=1.2),
              WHITE)


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
    copper_kettle(s, 0.74, 0.0)
    ladle(s, 0.3, 0.12)
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
    # the ladle rest under the ladle: a small glazed plate
    m.disc(0.06, seg(16, 8), "ceramic", T(0.3, 0.12, 0.004), C("f4efe6"), "glaze")
    m.lathe([(0.06, 0.004), (0.066, 0.01), (0.0, 0.0)], seg(16, 8), "ceramic", T(0.3, 0.12, 0), C("f4efe6"), "glaze")
    s.finish()
    return s


SHELF_BOTTLES = [
    # label, glass, bottle, capsule, liquid, display name, extra item fields
    ("label_wine", C("1c3320"), "bordeaux", C("8a1a1a"), None, "Winzer-Glühwein, red",
     dict(grape="Dornfelder", region="Pfalz")),
    ("label_wine", C("1c3320"), "bordeaux", C("8a1a1a"), None, "Winzer-Glühwein, red",
     dict(grape="Dornfelder", region="Pfalz")),
    ("label_white", C("d8e4d0"), "schlegel", C("c8a040"), C("d8b048"), "White Glühwein from Riesling",
     dict(grape="Riesling", region="Mosel")),
    ("label_berry", C("141a38"), "bordeaux", C("2a2a6a"), None, "Blueberry Glühwein", dict(fruit="Heidelbeere")),
    ("label_rum", C("5a3010"), "flask", C("1a1a1a"), C("6a2a08"), "Rum, for a Schuss", {}),
    ("label_punsch", C("e0e8e0"), "schlegel", C("b0282a"), C("8a0a10"), "Kinderpunsch, alcohol-free", {}),
]


def shelf():
    s = vlib.PropSet("prop_gluehwein_shelf", "slot_shelf_1", "gluehwein", footprint=(2.4, 0.3))
    m = s.static
    x = -1.12
    for k, (lab, gcol, kind, foil, liq, name, extra) in enumerate(SHELF_BOTTLES):
        idx = 12 + k
        node = s.node(f"act_bottle_{idx}", (x, 0.02 + rng.uniform(-0.03, 0.03), 0), rot=(0, 0, rng.uniform(-0.25, 0.25)))
        G.bottle(node, None, lab, gcol, kind, foil, liq, n=10)
        s.item(f"act_bottle_{idx}", name, "bottle", where="Glühwein shelf", **extra)
        x += 0.1
    # spice jars in a row
    jars = [("jar_zimt", C("8a4b26"), "cinnamon"), ("jar_nelken", C("4a2412"), "almonds"),
            ("jar_anis", C("7a3a1a"), "almonds"), ("jar_orange", C("e07a20"), "peel"),
            ("jar_kardamom", C("8aa060"), "almonds")]
    x = -0.45
    for k, (lab, col, reg) in enumerate(jars):
        G.jar(m, T(x, -0.03 + (k % 2) * 0.05, 0, rz=drng.uniform(-0.2, 0.2)), lab, col, reg,
              h=0.11 + (k % 3) * 0.015, r=0.036)
        x += 0.09
    # a low crate of dried orange slices (stacked, overlapping)
    G.crate(m, T(0.2, 0.0, 0), 0.3, 0.2, 0.08, C("c89e70"))
    for k in range(9 if not lite() else 4):
        dx, dy = drng.uniform(-0.12, 0.12), drng.uniform(-0.08, 0.08)
        G.orange_slice(m, T(0.2 + dx, dy, 0.03 + drng.uniform(0, 0.05), rx=drng.uniform(-0.5, 0.5),
                            ry=drng.uniform(-0.5, 0.5), rz=drng.uniform(0, 6)), r=drng.uniform(0.026, 0.034))
    # bundles of cinnamon sticks tied with twine
    for b, by in enumerate((-0.03, 0.03)):
        for k in range(4 if not lite() else 2):
            a = TWO_PI * k / 4
            rr = 0.011
            G.cinnamon_stick(m, T(0.5, by + rr * math.cos(a), 0.0222 + rr * math.sin(a), rz=math.pi / 2 + 0.05 * b),
                             L=0.14, r=0.0065)
        if not lite():
            n = 8
            G.twine(m, [(0.5, by + 0.019 * math.cos(TWO_PI * j / n), 0.0222 + 0.019 * math.sin(TWO_PI * j / n))
                        for j in range(n + 1)])
    # a small bowl of star anise
    G.bowl(m, T(0.66, 0.0, 0), r=0.07, h=0.035, seg_n=14)
    for k in range(4 if not lite() else 2):
        G.star_anise(m, T(0.66 + drng.uniform(-0.035, 0.035), drng.uniform(-0.035, 0.035), 0.022 + k * 0.002,
                          rx=drng.uniform(-0.3, 0.3), rz=drng.uniform(0, 6)))
    # spare mugs on the right: a back row of four classic mugs and a front row of three with a boot
    styles = ["red", "blue", "cream", "green", "white", "bluestar"]
    spots = [(0.82, 0.07), (0.93, 0.075), (1.04, 0.07), (0.86, -0.055), (0.97, -0.06), (1.09, -0.05)]
    for k, (x, y) in enumerate(spots):
        mug(s, 10 + k, (x, y, 0), styles[k], boot=k == 5, where="spare, on the back shelf")
    s.finish()
    return s


# (label region, bottle, glass, capsule, wine, grape, region, vintage, producer, colour). Fictional estates.
WINES = [
    ("wl_riesling_mosel", "schlegel", C("35602c"), C("2a5a2a"), "Riesling Kabinett feinherb", "Riesling", "Mosel",
     2022, "Weingut am Laternenberg", "white"),
    ("wl_riesling_rheingau", "schlegel", C("5a3410"), C("c8a040"), "Riesling Spätlese", "Riesling", "Rheingau", 2021,
     "Weinhaus Glockenhof", "white"),
    ("wl_riesling_pfalz", "schlegel", C("46662a"), C("c8ccd0"), "Riesling trocken", "Riesling", "Pfalz", 2023,
     "Kellerei Sternschnuppe", "white"),
    ("wl_spaet_baden", "burgundy", C("1c2a18"), C("6a1020"), "Spätburgunder trocken", "Spätburgunder (Pinot Noir)",
     "Baden", 2020, "Weingut Mondscheinhang", "red"),
    ("wl_spaet_ahr", "burgundy", C("24301c"), C("141414"), "Spätburgunder", "Spätburgunder (Pinot Noir)", "Ahr", 2019,
     "Winzerhof Tannenleite", "red"),
    ("wl_dornfelder_rh", "bordeaux", C("1a2a1a"), C("4a1a48"), "Dornfelder halbtrocken", "Dornfelder", "Rheinhessen",
     2022, "Weingut Schneehang", "red"),
    ("wl_dornfelder_pfalz", "bordeaux", C("1e2c1c"), C("9a1a18"), "Dornfelder trocken", "Dornfelder", "Pfalz", 2021,
     "Kellerei Kerzenschein", "red"),
    ("wl_silvaner_franken", "bocksbeutel", C("2e5a2a"), C("8a9a3a"), "Silvaner Kabinett trocken, in a Bocksbeutel",
     "Silvaner", "Franken", 2022, "Weingut zum Weihnachtsstern", "white"),
    ("wl_silvaner_rh", "schlegel", C("9ab488"), C("ece8e0"), "Silvaner trocken", "Silvaner", "Rheinhessen", 2023,
     "Hof Nachtigallenruh", "white"),
    ("wl_riesling_nahe", "schlegel", C("3e5a26"), C("b8922e"), "Riesling Auslese", "Riesling", "Nahe", 2020,
     "Weingut Rauhreif", "white"),
    ("wl_weissherbst_baden", "burgundy", C("e6ece0"), C("d87a8a"), "Spätburgunder Weißherbst (rosé)",
     "Spätburgunder (Pinot Noir)", "Baden", 2023, "Winzerkeller Lichterglanz", "rosé"),
    ("wl_riesling_eiswein", "half", C("6a4012"), C("c8a040"), "Riesling Eiswein, 0.375 l", "Riesling", "Rheingau",
     2018, "Weingut Eiszapfen", "white"),
]
ROSE = C("e8a098")
# preview-only stand-ins for the tasting notes the engine prints on the back labels (the writer owns the real ones)
PREVIEW_NOTES = ["Green apple, lime zest and a touch of honey; slate in the finish. Lovely with the Flammkuchen.",
                 "Ripe peach and apricot, gently sweet and lifted by bright acidity.",
                 "Dry and crisp: grapefruit, white flowers, a salty mineral edge.",
                 "Red cherry and a little smoke; silky, with soft tannins."]


def wine():
    """German reds, whites and a rosé on the upper shelf: eight bottles in a low rack, two standing in a straw-
    packed crate, two on a closed wine box, and five wine glasses on a tray. Every bottle and glass is its
    own node (act_bottle_0..11, act_wineglass_0..4) with its origin at its base."""
    s = vlib.PropSet("prop_gluehwein_wine", "slot_shelf_2", "gluehwein", footprint=(2.4, 0.3))
    m = s.static
    # a low slatted rack the bottles stand in (a board with a front rail)
    G.board(m, T(-0.56, 0.01, 0), 1.18, 0.2, 0.014, C("a8845c"))
    m.box((1.18, 0.012, 0.04), T(-0.56, -0.085, 0.034), vlib.RW("wood"), C("8a6440"))
    # an open wine crate packed with straw, and a closed wine box as a riser
    cx, bx = 0.2, 0.58
    G.crate(m, T(cx, 0.02, 0), 0.3, 0.2, 0.1, C("b08a5c"))
    m.box((0.27, 0.17, 0.004), T(cx, 0.02, 0.07), vlib.RW("straw"), C("e8d098"), faces={"pz": vlib.RW("straw")},
          skip=("nz",))
    m.box((0.34, 0.2, 0.12), T(bx, 0.015, 0.06), vlib.RW("wood"), C("b89266"), skip=("nz",))
    x = -1.13
    for i, (lab, kind, glass, cap, wname, grape, region, vint, prod, colour) in enumerate(WINES):
        w = 0.15 if kind == "bocksbeutel" else 0.1
        if i < 8:
            x += w / 2
            loc = (x, 0.01 + rng.uniform(-0.01, 0.01), 0.014)
            x += w / 2 + 0.018
        elif i < 10:
            loc = (cx - 0.065 + (i - 8) * 0.13, 0.02 + rng.uniform(-0.02, 0.02), 0.012)
        else:
            loc = (bx - 0.07 + (i - 10) * 0.14, 0.015, 0.12)
        node = s.node(f"act_bottle_{i}", loc, rot=(0, 0, rng.uniform(-0.15, 0.15)))
        G.bottle(node, None, lab, glass, kind, cap, liquid=ROSE if colour == "rosé" else None, n=10)
        # round 6: a back label on every bottle with a blank writing strip, write_label_<n>, for its tasting note
        # (docs/adr/0003: "wine bottles show their tasting note on the label when turned"), and a reading
        # camera behind the bottle, cam_read_label_<n>, a child of the bottle: once the engine turns the bottle
        # round (180 degrees about its base), the camera stands in front of the label
        wm = vprint.write_node(s, f"write_label_{i}", f"act_bottle_{i}")
        c, cw, ch = G.back_label(node, wm, None, kind, f"pr_back_{lab}", vlib.print_meta()["back_label_write"])
        d = vprint.reading_distance(cw, ch, fill=0.8)
        vprint.cam_read(s, f"label_{i}", c, (c[0], c[1] + d, c[2]), parent=f"act_bottle_{i}")
        s.item(f"act_bottle_{i}", f"{wname}, {region} {vint} ({prod})", "bottle", where="wine shelf",
               wine=wname, grape=grape, region=region, vintage=vint, producer=prod, colour=colour,
               country="Germany", write={"back_label": f"write_label_{i}"})
    if not lite():
        # straw tufts round the bottles in the crate
        for k in range(8):
            m.box((0.012, 0.004, 0.08), T(cx + drng.uniform(-0.12, 0.12), 0.02 + drng.uniform(-0.07, 0.07), 0.075,
                                             rx=drng.uniform(1.2, 1.9), rz=drng.uniform(0, 3)), "straw", C("e0c890"))
    # five wine glasses on a tray: a red, a white, a rosé and two clean ones
    tx = 0.98
    G.board(m, T(tx, 0.01, 0), 0.4, 0.22, 0.012, C("6a4228"))
    for k, (dx, dy, wcol, nm) in enumerate(((-0.13, -0.05, C("4a0612"), "Glass of Spätburgunder"),
                                            (-0.04, 0.05, C("e8d890"), "Glass of Riesling"),
                                            (0.05, -0.04, ROSE, "Glass of Weißherbst"),
                                            (0.13, 0.055, None, "Clean wine glass"),
                                            (0.145, -0.055, None, "Clean wine glass"))):
        g = s.node(f"act_wineglass_{k}", (tx + dx, 0.01 + dy, 0.012))
        G.wine_glass(g, None, wcol)
        s.item(f"act_wineglass_{k}", nm, "wineglass")
    # a corkscrew and two corks
    if not lite():
        m.box((0.11, 0.012, 0.008), T(0.78, -0.08, 0.004, rz=0.3), "steel", WHITE)
        for dx in (0.0, 0.03):
            m.cyl(0.011, 0.011, 0.045, 8, "cinnamon", T(0.8 + dx, -0.1, 0.011, ry=math.pi / 2, rz=dx * 20),
                  C("d8b890"))
    s.finish()
    return s


SETS = {
    "prop_gluehwein_counter": dict(fn=counter, slot="slot_counter", stall="gluehwein", kind="counter", section=True,
                                   seed=21, cam=((-0.08, -1.75, 0.52), (-0.04, 0.0, 0.2), 25),
                                   hero=((0.3, -1.0, 0.62), (0.5, 0.0, 0.24), 27)),
    "prop_gluehwein_shelf": dict(fn=shelf, slot="slot_shelf_1", stall="gluehwein", kind="shelf", section=True, seed=22,
                                 cam=((0.0, -1.75, 0.22), (0.0, 0.0, 0.13), 32),
                                 hero=((-0.55, -0.75, 0.2), (-0.55, 0.0, 0.12), 40)),
    "prop_gluehwein_wine": dict(fn=wine, slot="slot_shelf_2", stall="gluehwein", kind="shelf2", section=True, seed=23,
                                cam=((0.0, -1.75, 0.25), (0.0, 0.0, 0.15), 32),
                                # round 6: the first four bottles turned round (as the engine turns one) to show
                                # the back labels' writing strips, with stand-in tasting notes
                                hero=((-0.9, -0.52, 0.17), (-0.9, 0.0, 0.085), 42),
                                preview_turn=[f"act_bottle_{i}" for i in range(4)],
                                preview_text=lambda: {f"write_label_{i}": [(t, 0.085, "garamond", "2a2420")]
                                                      for i, t in enumerate(PREVIEW_NOTES)}),
}
