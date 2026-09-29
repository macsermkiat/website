"""Glühwein stand goods: the counter (copper kettle, ladle, mugs) and the back shelf (bottles, spices).

prop_gluehwein_counter  -> slot_counter of stall_gluehwein (origin on the counter top, centred)
prop_gluehwein_shelf    -> slot_shelf_1 of stall_gluehwein (origin on the lower back shelf, centred)
"""
import math

from mathutils import Matrix, Vector

import goods as G
import vlib
from vlib import C, T, WHITE, jit, rng, seg

TWO_PI = 2 * math.pi


def copper_kettle(s, x, y):
    """Riveted copper Glühwein kettle on an iron burner ring, hinged lid (act_pot_lid), ladle (act_ladle)."""
    pot = s.node("act_pot", (x, y, 0))
    n = seg(32, 14)
    iron = C("ffffff")
    # burner: a squat black ring with vent holes suggested by the iron texture, three stubby feet
    pot.lathe([(0.15, 0.0), (0.16, 0.004), (0.16, 0.05), (0.15, 0.06), (0.14, 0.06), (0.14, 0.05)], n,
              vlib.RW("iron"), None, iron, "atlas", smooth=False)
    for k in range(3):
        a = TWO_PI * k / 3 + 0.3
        pot.box((0.03, 0.02, 0.012), T(0.155 * math.cos(a), 0.155 * math.sin(a), 0.006, rz=a), "iron", C("888888"))
    for k in range(10):
        a = TWO_PI * k / 10
        pot.box((0.02, 0.004, 0.012), T(0.161 * math.cos(a), 0.161 * math.sin(a), 0.03, rz=a + math.pi / 2),
                "sw_matte", C("0a0908"))
    # kettle body: hammered copper, bellied, with a rolled rim
    z0 = 0.06
    body = [(0.0, z0), (0.13, z0), (0.16, z0 + 0.012), (0.185, z0 + 0.05), (0.2, z0 + 0.13), (0.203, z0 + 0.25),
            (0.2, z0 + 0.33), (0.206, z0 + 0.345)]
    pot.lathe(body, n, vlib.RW("copper"), None, WHITE, "atlas")
    pot.torus(0.206, 0.009, n, seg(8, 5), "copper", T(0, 0, z0 + 0.35), C("e8d0c0"))
    inner = [(0.198, z0 + 0.35), (0.195, z0 + 0.3), (0.19, z0 + 0.26)]
    pot.lathe(inner, n, "copper", None, C("9a6a58"), "atlas")
    # Glühwein surface with a few floating orange slices, star anise and a cinnamon stick
    liquid_z = z0 + 0.262
    pot.disc(0.19, n, "sw_wet", T(0, 0, liquid_z), C("3a0508"), "liquid")
    for k, (dx, dy, a) in enumerate(((-0.07, -0.05, 0.3), (0.06, 0.06, 1.2), (0.09, -0.07, 2.2), (-0.03, 0.09, 0.8))):
        G.orange_slice(pot, T(dx, dy, liquid_z - 0.002, rx=0.05, rz=a), r=0.032, t=0.004)
    G.star_anise(pot, T(0.0, -0.02, liquid_z - 0.001, rz=0.4))
    G.star_anise(pot, T(-0.11, 0.04, liquid_z - 0.001, rz=1.4))
    G.cinnamon_stick(pot, T(0.02, 0.11, liquid_z + 0.002, rz=0.5), L=0.09)
    # riveted seam band and two brass drop-ring handles
    pot.lathe([(0.2035, z0 + 0.2), (0.2045, z0 + 0.21), (0.2035, z0 + 0.22)], n, "copper", None, C("c89080"))
    for sx in (-1, 1):
        pot.box((0.02, 0.04, 0.03), T(sx * 0.2, 0, z0 + 0.3), "brass", WHITE)
        pot.torus(0.035, 0.006, seg(18, 8), seg(6, 4), "brass", T(sx * 0.215, 0, z0 + 0.265, rx=math.pi / 2, rz=0),
                  WHITE)
    # brass spigot low on the front with a T handle and a drip lip
    pot.cyl(0.013, 0.011, 0.05, 12, "brass", T(0, -0.19, z0 + 0.06, rx=math.pi / 2), WHITE)
    pot.cyl(0.009, 0.008, 0.035, 10, "brass", T(0, -0.235, z0 + 0.06), WHITE)
    pot.box((0.06, 0.01, 0.01), T(0, -0.236, z0 + 0.1), "brass", WHITE)
    pot.cyl(0.006, 0.006, 0.03, 8, "brass", T(0, -0.235, z0 + 0.03, rx=math.pi), WHITE)
    # hinge knuckles at the back rim
    for sx in (-0.05, 0.05):
        pot.cyl(0.007, 0.007, 0.03, 8, "brass", T(sx - 0.015, 0.212, z0 + 0.358, ry=math.pi / 2), WHITE)
    # the lid: hinged at the back rim, propped open
    hinge = (0, 0.212, z0 + 0.358)
    lid = s.node("act_pot_lid", hinge, parent="act_pot")
    lid_prof = [(0.214, -0.004), (0.216, 0.0), (0.2, 0.02), (0.15, 0.05), (0.08, 0.068), (0.025, 0.074), (0.0, 0.075)]
    lid.lathe(lid_prof, n, vlib.RW("copper"), T(0, -0.212, 0), WHITE, "atlas")
    lid.lathe([(0.0, 0.07), (0.2, 0.014), (0.21, -0.002)], n, "copper", T(0, -0.212, 0), C("8a5a48"), "atlas")
    lid.sphere(0.022, seg(12, 8), seg(8, 5), vlib.RW("wood"), T(0, -0.212, 0.09), C("5a3622"), scale=(1, 1, 0.8))
    lid.cyl(0.008, 0.012, 0.018, 10, "brass", T(0, -0.212, 0.07), WHITE)
    lid.box((0.04, 0.03, 0.006), T(0, -0.005, 0.0), "brass", WHITE)
    s.objs_rot = getattr(s, "objs_rot", {})
    s.objs_rot["act_pot_lid"] = (-0.62, 0, 0)
    # ladle standing in the kettle, handle over the front rim
    lad = s.node("act_ladle", (0.07, -0.08, z0 + 0.18), parent="act_pot")
    lad.lathe([(0.0, -0.05), (0.03, -0.045), (0.043, -0.03), (0.046, -0.012), (0.047, 0.0), (0.044, 0.0),
               (0.04, -0.028), (0.0, -0.042)], seg(18, 10), "steel", T(0, 0, -0.02), WHITE)
    pts = [Vector((0.03, 0.0, -0.02)), Vector((0.045, -0.02, 0.08)), Vector((0.06, -0.06, 0.19)),
           Vector((0.07, -0.12, 0.26)), Vector((0.08, -0.17, 0.28)), Vector((0.09, -0.19, 0.265))]
    lad.tube(pts, 0.006, seg(8, 5), "steel", None, WHITE)
    s.empty("act_steam", (0, 0, liquid_z + 0.02), parent="act_pot")
    return pot


def counter():
    s = vlib.PropSet("prop_gluehwein_counter", "slot_counter", "gluehwein")
    m = s.static
    copper_kettle(s, 0.74, 0.03)
    # mugs: a front row ready to hand out (some filled, steaming), clean ones upside down on a tray
    styles = ["santa", "red", "blue", "cream", "green", "bluestar", "white", "brown", "red", "santa"]
    row = [(-1.08, -0.1), (-0.9, -0.14), (-0.72, -0.09), (-0.54, -0.14), (-0.36, -0.1), (-0.18, -0.13)]
    boot = {0, 5, 9}
    filled = {0, 1, 3, 4}
    i = 0
    for (x, y) in row:
        st = styles[i]
        mug = s.node(f"act_mug_{i}", (x, y, 0))
        ha = rng.uniform(-0.5, 0.5) + (0 if i % 2 else math.pi * 0.15)
        if i in boot:
            G.mug_boot(mug, None, st, filled=i in filled, toe_angle=-math.pi / 2 + rng.uniform(-0.5, 0.5))
            top = 0.108
        else:
            G.mug_classic(mug, None, st, filled=i in filled, handle_angle=ha)
            top = G.MUG_RIM
        if i in filled:
            s.empty(f"act_steam_{i}", (0, 0, top - 0.015), parent=f"act_mug_{i}")
        i += 1
    # tray with clean mugs upside down, and a folded linen tea towel
    G.board(m, T(-0.62, 0.1, 0), 0.62, 0.2, 0.014, C("b88a5e"))
    m.box((0.6, 0.012, 0.022), T(-0.62, 0.005, 0.018), vlib.RW("wood"), C("a07448"))
    m.box((0.6, 0.012, 0.022), T(-0.62, 0.195, 0.018), vlib.RW("wood"), C("a07448"))
    for k, x in enumerate((-0.86, -0.7, -0.54, -0.38)):
        mug = s.node(f"act_mug_{i}", (x, 0.1, 0.014))
        s.objs_rot = getattr(s, "objs_rot", {})
        s.objs_rot[f"act_mug_{i}"] = (math.pi, 0, rng.uniform(0, TWO_PI))
        G.mug_classic(mug, T(0, 0, -0.0968), styles[6 + k % 4] if k != 1 else "cream", handle_angle=0)
        i += 1
    # a wooden bowl of oranges with cinnamon and anise, next to the kettle
    G.bowl(m, T(0.26, -0.03, 0), r=0.12, h=0.055)
    for k, (dx, dy) in enumerate(((-0.04, -0.03), (0.045, -0.02), (0.0, 0.05), (0.05, 0.055))):
        G.orange(m, T(0.26 + dx, -0.03 + dy, 0.012 + (0.0 if k < 3 else 0.006), rz=k), r=0.033)
    G.orange_slice(m, T(0.23, -0.1, 0.05, rx=0.4, rz=0.3), r=0.03)
    for k in range(3):
        G.cinnamon_stick(m, T(0.34 + k * 0.012, -0.12 + k * 0.01, 0.006 + k * 0.004, rz=0.4 + k * 0.1), L=0.1)
    G.star_anise(m, T(0.42, -0.06, 0.0, rz=0.2))
    # two coasters-sized felt mats under the kettle feet line and a ladle rest (small plate)
    m.disc(0.06, seg(18, 10), "ceramic", T(0.43, 0.14, 0.004), C("f4efe6"), "glaze")
    m.lathe([(0.06, 0.004), (0.066, 0.01), (0.0, 0.0)], seg(18, 10), "ceramic", None, C("f4efe6"), "glaze")
    s.finish()
    for k, rot in getattr(s, "objs_rot", {}).items():
        s.objs[k].rotation_euler = rot
    return s


def shelf():
    s = vlib.PropSet("prop_gluehwein_shelf", "slot_shelf_1", "gluehwein", footprint=(2.4, 0.3))
    m = s.static
    # bottles on the left: red wine, white, berry, rum, amaretto, children's punch
    bottles = [("label_wine", C("1c3320"), "bordeaux", C("8a1a1a"), None),
               ("label_wine", C("1c3320"), "bordeaux", C("8a1a1a"), None),
               ("label_white", C("d8e4d0"), "schlegel", C("c8a040"), C("d8b048")),
               ("label_berry", C("141a38"), "bordeaux", C("2a2a6a"), None),
               ("label_rum", C("5a3010"), "flask", C("1a1a1a"), C("6a2a08")),
               ("label_amaretto", C("7a3808"), "flask", C("d0a040"), C("8a3a08")),
               ("label_punsch", C("e0e8e0"), "schlegel", C("b0282a"), C("8a0a10"))]
    x = -1.12
    for lab, gcol, kind, foil, liq in bottles:
        G.bottle(m, T(x, 0.02 + rng.uniform(-0.03, 0.03), 0, rz=rng.uniform(-0.25, 0.25)), lab, gcol, kind, foil, liq)
        x += 0.095
    # spice jars in a row
    jars = [("jar_zimt", C("8a4b26"), "cinnamon"), ("jar_nelken", C("4a2412"), "almonds"),
            ("jar_anis", C("7a3a1a"), "almonds"), ("jar_orange", C("e07a20"), "peel"),
            ("jar_kardamom", C("8aa060"), "almonds")]
    x = -0.4
    for k, (lab, col, reg) in enumerate(jars):
        G.jar(m, T(x, -0.03 + (k % 2) * 0.05, 0, rz=rng.uniform(-0.2, 0.2)), lab, col, reg,
              h=0.11 + (k % 3) * 0.015, r=0.036)
        x += 0.09
    # a low crate of dried orange slices (stacked, overlapping)
    G.crate(m, T(0.25, 0.0, 0), 0.3, 0.2, 0.08, C("c89e70"))
    for k in range(13 if not vlib.lite() else 7):
        dx, dy = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.08)
        G.orange_slice(m, T(0.25 + dx, dy, 0.03 + rng.uniform(0, 0.05), rx=rng.uniform(-0.5, 0.5),
                            ry=rng.uniform(-0.5, 0.5), rz=rng.uniform(0, 6)), r=rng.uniform(0.026, 0.034))
    # bundles of cinnamon sticks tied with twine
    for b, bx in enumerate((0.52, 0.6)):
        for k in range(5):
            a = TWO_PI * k / 5
            rr = 0.012 if k else 0.0
            G.cinnamon_stick(m, T(bx + 0.06 * 0, 0.0 + rr * math.cos(a) + b * 0.06 - 0.03,
                                  0.008 + 0.012 + rr * math.sin(a), rz=math.pi / 2 + 0.05 * b), L=0.14, r=0.0065)
        n = 10
        G.twine(m, [(bx + 0.021 * math.cos(TWO_PI * j / n) * 0, 0.0 + b * 0.06 - 0.03 + 0.021 * math.cos(TWO_PI * j / n),
                     0.02 + 0.021 * math.sin(TWO_PI * j / n)) for j in range(n + 1)])
    # a small bowl of star anise
    G.bowl(m, T(0.78, 0.0, 0), r=0.07, h=0.035, seg_n=18)
    for k in range(5 if not vlib.lite() else 3):
        G.star_anise(m, T(0.78 + rng.uniform(-0.035, 0.035), rng.uniform(-0.035, 0.035), 0.022 + k * 0.002,
                          rx=rng.uniform(-0.3, 0.3), rz=rng.uniform(0, 6)))
    # spare mugs on the right, two rows
    styles = ["red", "blue", "cream", "green", "white"]
    for k, (x, y) in enumerate(((0.9, 0.06), (0.99, 0.06), (1.08, 0.06), (0.945, -0.05), (1.035, -0.05))):
        G.mug_classic(m, T(x, y, 0, rz=rng.uniform(0, 6)), styles[k], handle_angle=0)
    s.finish()
    return s


SETS = {
    "prop_gluehwein_counter": dict(fn=counter, slot="slot_counter", stall="gluehwein", kind="counter", section=True, seed=21,
                                   cam=((-0.2, -1.6, 0.5), (-0.12, 0.0, 0.17), 25)),
    "prop_gluehwein_shelf": dict(fn=shelf, slot="slot_shelf_1", stall="gluehwein", kind="shelf", section=True, seed=22,
                                 cam=((0.0, -1.75, 0.22), (0.0, 0.0, 0.13), 32)),
}
