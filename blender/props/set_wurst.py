"""Bratwurst stand goods: a round swinging charcoal grill (Schwenkgrill) and the serving counter.

prop_wurst_counter -> slot_counter of stall_bratwurst
  act_grill        fire bowl with glowing coals (material coal_glow) and the gallows; origin at the bowl's
                   foot, which stands on the carpenter's firebox grate (2.6 cm above the counter top).
                   The engine's grill flare pulses every mesh under this node, so its iron uses
                   grill_iron (a whisper of emission keeps the flare off the iron).
  act_grill_swing  the round grate on three chains, pivot at the hook (the engine swings it gently)
  act_sausage_0..7 Bratwürste on the grate. They are children of act_grill_swing, so they ride the swing.
                   Origin at each sausage's centre, long axis X: the engine turns them about that axis
                   (stalls.js turnSausages), which a base pivot would turn into a hop round the underside.
                   items.json says so in each sausage's "pivot".
  act_sausage_8..11  four done ones keeping warm in a steel tray on the counter, just right of the firebox
  act_roll_0..9    Brötchen in the basket, origin at the base of each roll (all ten in full and lite)
  act_smoke        where smoke should rise
  Mustard and ketchup pots, squeeze bottles, a stack of paper trays, one served Bratwurst im Brötchen
  (act_served_0), a napkin dispenser and a chalk price sign.

On stall_bratwurst the grill sits over the carpenter's built-in firebox (x -1.75..-0.15 from the slot, its
rim tube to -0.13, hearth plate top 2.6 cm up): the set puts the fire bowl at x = -0.9 on that plate, and
everything else on the plain counter from x = -0.11 to its end at 1.89. check_props runs seat_check.mjs,
which fails if any triangle of the set cuts into the stall (counter, firebox, rim, hearth plate).
"""
import math

import bmesh
from mathutils import Matrix, Vector, noise

import goods as G
import vlib
from vlib import C, T, WHITE, drng, jit, rng, seg

TWO_PI = 2 * math.pi
GX = -0.9
GZ = 0.026          # top of the firebox grate bars, from the slot


def lump(m, M, r, region, col, mat, subd=1, rough=0.35, squash=0.7, seed=0.0):
    """Irregular chunk (charcoal, rock): a noisy icosphere, spherically mapped into region."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=r)
    verts, faces, uvs = [], [], []
    reg = vlib.R(region)
    for v in bm.verts:
        p = v.co.copy()
        k = 1 + rough * noise.noise(p * (3.0 / r) + Vector((seed, seed * 1.7, 0)))
        verts.append((p.x * k, p.y * k * 0.9, p.z * k * squash))
    for f in bm.faces:
        ids = [v.index for v in f.verts]
        faces.append(tuple(ids))
        uvs.append([reg.uv(0.5 + 0.5 * verts[i][0] / r, 0.5 + 0.5 * verts[i][1] / r) for i in ids])
    bm.free()
    m.add(verts, faces, uvs, M, col, mat, False)


def chain(m, a, b, link=0.042, r=0.0028, mat="grill_iron", col=WHITE):
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    n = max(2, int(L / (link * 0.72)))
    z = d.normalized()
    x = z.cross(Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))).normalized()
    y = z.cross(x)
    if vlib.lite():
        m.tube([a, b], r * 1.4, 4, "iron", None, col, mat)
        return
    for i in range(n):
        c = a + d * ((i + 0.5) / n)
        xx, yy = (x, y) if i % 2 == 0 else (y, -x)
        B = Matrix((xx, z, yy)).transposed().to_4x4()      # torus in its XY plane -> link along z
        M = Matrix.Translation(c) @ B @ Matrix.Diagonal((0.55, 1.0, 1.0, 1.0))
        m.torus(link * 0.5, r, 5, 3, "iron", M, col, mat)


def grill(s):
    iron = WHITE
    g = s.node("act_grill", (GX, 0.0, GZ))
    s.item("act_grill", "Schwenkgrill over the charcoal", "grill")
    n = seg(32, 12)
    # fire bowl: shallow iron dish on three stub legs
    bowl = [(0.0, 0.03), (0.14, 0.03), (0.19, 0.05), (0.21, 0.1), (0.214, 0.108), (0.205, 0.108),
            (0.182, 0.058), (0.135, 0.04), (0.0, 0.04)]
    g.lathe(bowl, n, vlib.RW("iron"), None, iron, "grill_iron", smooth=True)
    g.torus(0.212, 0.006, n, 6, "iron", T(0, 0, 0.108), C("aaaaaa"), "grill_iron")
    for k in range(3):
        a = TWO_PI * k / 3 + 0.5
        g.box((0.02, 0.02, 0.035), T(0.13 * math.cos(a), 0.13 * math.sin(a), 0.0175), "iron", iron, "grill_iron")
    # coal bed: glowing chunks with ash, piled in the bowl
    coal = s.node("coals", (0, 0, 0), parent="act_grill")
    full = vlib.Reg([0.0, 0.0, 1.0, 1.0])
    # a bed of grey ash under the lumps, then the charcoal: mostly black and ashen, glowing in the cracks
    coal.lathe([(0.0, 0.05), (0.17, 0.05), (0.185, 0.062), (0.0, 0.066)], seg(20, 8), vlib.Reg([0.0, 0.0, 1.0, 1.0]),
               None, C("6a6560"), "coal_glow")
    k = 34 if not vlib.lite() else 10
    for i in range(k):
        rr = 0.165 * math.sqrt(drng.random())
        a = drng.uniform(0, TWO_PI)
        z = 0.058 + (0.165 - rr) * 0.12 + drng.uniform(0, 0.012)
        ashy = drng.random() < 0.35
        lump(coal, T(rr * math.cos(a), rr * math.sin(a), z, rz=drng.uniform(0, 6)), drng.uniform(0.02, 0.032),
             full, jit(C("b0aca8") if ashy else WHITE, 0.15), "coal_glow", subd=1, seed=i * 1.3)
    # gallows: a square post at the back, an arm over the bowl, a hook
    post_top = 0.64
    g.box((0.03, 0.03, post_top), T(0, 0.228, post_top / 2), vlib.RW("iron"), iron, "grill_iron")
    g.box((0.12, 0.04, 0.015), T(0, 0.228, 0.0075), vlib.RW("iron"), iron, "grill_iron")
    g.box((0.028, 0.25, 0.028), T(0, 0.105, post_top - 0.014), vlib.RW("iron"), iron, "grill_iron")
    brace = [Vector((0, 0.228, post_top - 0.17)), Vector((0, 0.12, post_top - 0.03))]
    g.tube(brace, 0.008, 6, "iron", None, iron, "grill_iron")
    g.torus(0.014, 0.003, 10, 4, "iron", T(0, 0.0, post_top - 0.045, rx=math.pi / 2), iron, "grill_iron")
    # swinging grate on three chains, pivot at the hook
    hook = (0, 0.0, post_top - 0.058)
    sw = s.node("act_grill_swing", hook, parent="act_grill")
    gz = 0.17 - hook[2]
    rim_r = 0.19
    sw.torus(rim_r, 0.006, n, 6, "iron", T(0, 0, gz), iron, "grill_iron")
    sw.torus(0.07, 0.004, seg(20, 10), 5, "iron", T(0, 0, gz), iron, "grill_iron")
    bars = 13 if not vlib.lite() else 7
    for i in range(bars):
        y = -rim_r + (i + 0.5) * 2 * rim_r / bars
        half = math.sqrt(max(0.0, rim_r ** 2 - y ** 2))
        sw.box((2 * half, 0.005, 0.005), T(0, y, gz), "iron", C("8a8a8a"), "grill_iron")
    for k in range(3):
        a = TWO_PI * k / 3 + math.pi / 2
        chain(sw, (0, 0, 0), (rim_r * 0.98 * math.cos(a), rim_r * 0.98 * math.sin(a), gz + 0.004))
    # a crank handle on the post (height adjuster) for character
    g.cyl(0.006, 0.006, 0.06, 6, "iron", T(0.015, 0.228, 0.42, ry=math.pi / 2), iron, "grill_iron")
    g.box((0.01, 0.01, 0.07), T(0.075, 0.228, 0.45), "iron", iron, "grill_iron")
    s.empty("act_smoke", (0, 0, 0.22), parent="act_grill")
    s.item("act_grill_swing", "Swinging grill grate", "grill")
    s.item("act_smoke", "Smoke from the grill", "effect")
    return gz


def mustard_pot(m, M, col=C("8a9aa8"), fill=C("c8961a"), label=None):
    n = seg(14, 8)
    m.lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.02), (0.052, 0.08), (0.047, 0.1), (0.048, 0.106),
             (0.043, 0.104), (0.043, 0.09)], n, "bisque", M, col, "glaze")
    m.torus(0.051, 0.003, n, 4, "ceramic", M @ T(0, 0, 0.05), C("1d3a78"), "glaze")
    m.disc(0.043, n, "sw_wet", M @ T(0, 0, 0.09), fill, "liquid")


def served(s, x, y, rz):
    """One Bratwurst im Brötchen with a stripe of mustard, in a paper tray: act_served_0 (base pivot)."""
    node = s.node("act_served_0", (x, y, 0), rot=(0, 0, rz))
    G.paper_tray(node, None, 0.22, 0.1, 0.03)
    G.roll(node, T(0, 0, 0.004), L=0.13, W=0.07, H=0.04)
    G.sausage(node, T(0, -0.004, 0.036), L=0.21, r=0.0125, bend=0.01, dark=False, seed=9.0)
    pts = [(-0.08 + i * 0.016, -0.004 + 0.004 * math.sin(i * 1.7), 0.05) for i in range(11)]
    node.tube(pts, 0.004, 5, "sw_wet", None, C("d8a01a"), "liquid")
    s.item("act_served_0", "Bratwurst im Brötchen with mustard", "served")


def squeeze_bottle(m, M, col, cap):
    n = seg(12, 6)
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.032, 0.01), (0.031, 0.15), (0.024, 0.17), (0.0, 0.172)], n, "sw_gloss", M,
            col, "glaze")
    m.lathe([(0.02, 0.168), (0.02, 0.19), (0.006, 0.215), (0.0, 0.22)], n, "sw_satin", M, cap)


def chalk_sign(m, M):
    """A small A-frame chalkboard with the prices."""
    w, h = 0.26, 0.2
    for side in (-1, 1):
        Ms = M @ T(0, side * 0.025, 0, rx=side * 0.2) @ T(0, 0, h / 2)
        m.box((w, 0.01, h), Ms, "wurst_sign", WHITE, faces={"ny" if side < 0 else "py": "wurst_sign"})
        m.box((w + 0.02, 0.014, 0.015), Ms @ T(0, 0, h / 2), vlib.RW("wood"), C("6a4228"))
        m.box((w + 0.02, 0.014, 0.015), Ms @ T(0, 0, -h / 2 + 0.008), vlib.RW("wood"), C("6a4228"))


def counter():
    s = vlib.PropSet("prop_wurst_counter", "slot_counter", "bratwurst")
    m = s.static
    gz = grill(s)
    hook_z = 0.64 - 0.058
    # sausages on the grate: two per row, four rows. Children of the swinging grate (so they ride it),
    # each with its pivot at its centre so the engine can turn it about its long axis.
    i = 0
    for y in (-0.11, -0.037, 0.037, 0.11):
        for x in (-0.075, 0.075):
            L = rng.uniform(0.13, 0.145)
            node = s.node(f"act_sausage_{i}", (x + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.01, 0.01),
                                               gz + 0.003 + 0.0125), parent="act_grill_swing")
            G.sausage(node, T(0, 0, 0, rz=rng.uniform(-0.12, 0.12)), L=L, r=0.0125, bend=rng.uniform(0.004, 0.012),
                      dark=i % 3 == 1, seed=i * 1.7)
            s.item(f"act_sausage_{i}", "Bratwurst on the grill", "sausage")
            i += 1
    # done ones keeping warm in a steel tray on the counter, just right of the firebox rim (x -0.13)
    tx, ty = 0.0, 0.1
    m.lathe([(0.0, 0.0), (0.1, 0.0), (0.105, 0.03), (0.098, 0.03), (0.092, 0.004), (0.0, 0.004)], seg(16, 6), "steel",
            T(tx, ty, 0) @ Matrix.Diagonal((1.0, 0.55, 1.0, 1.0)), WHITE)
    for k in range(4):
        node = s.node(f"act_sausage_{8 + k}", (tx, ty - 0.03 + k * 0.02, 0.004 + 0.0125 + (0.008 if k % 2 else 0)))
        G.sausage(node, T(0, 0, 0, rz=rng.uniform(-0.1, 0.1)), L=0.14, r=0.0125, bend=0.006, dark=True, seed=20 + k)
        s.item(f"act_sausage_{8 + k}", "Bratwurst keeping warm", "sausage")
    # grill tongs lying in front of the tray
    for dy in (-0.006, 0.006):
        m.box((0.3, 0.012, 0.003), T(0.06, -0.16 + dy * 1.4, 0.0015, rz=0.2 + dy * 2), "steel", WHITE)
    # basket of rolls, each roll its own node (all ten in the lite set too, so both carry the same act_ nodes)
    bx, by = 0.36, 0.02
    G.crate(m, T(bx, by, 0), 0.34, 0.26, 0.07, C("b48c5c"), slats=2)
    m.box((0.3, 0.22, 0.004), T(bx, by, 0.014), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k in range(10):
        row, col = divmod(k, 4)
        loc = (bx - 0.105 + col * 0.07 + rng.uniform(-0.01, 0.01), by - 0.07 + row * 0.07 + rng.uniform(-0.01, 0.01),
               0.016 + (0.03 if k >= 8 else 0.0))
        node = s.node(f"act_roll_{k}", loc, rot=(0, 0, math.pi / 2 + rng.uniform(-0.3, 0.3)))
        G.roll(node, None, L=0.105, W=0.068, H=0.03)
        s.item(f"act_roll_{k}", "Brötchen (bread roll)", "roll")
    # mustard (salt-glazed stoneware) and ketchup pots with wooden spatulas
    mustard_pot(m, T(0.66, 0.12, 0), C("8a9aa8"), C("c8961a"))
    mustard_pot(m, T(0.78, 0.13, 0), C("f0ece2"), C("8a0e0a"))
    for x, a in ((0.66, 0.3), (0.78, -0.4)):
        m.box((0.012, 0.004, 0.16), T(x + 0.02, 0.12, 0.1, rx=0.3, rz=a), vlib.RW("wood"), C("c8a070"))
    # stack of nested paper trays and one served Bratwurst
    for k in range(5 if not vlib.lite() else 2):
        G.paper_tray(m, T(1.12, 0.1, k * 0.0055, rz=drng.uniform(-0.05, 0.05)), 0.22, 0.1, 0.03)
    served(s, 0.9, -0.13, 0.25)
    # squeeze bottles, a napkin dispenser and the price sign
    squeeze_bottle(m, T(1.26, -0.12, 0), C("d8a820"), C("c83020"))
    squeeze_bottle(m, T(1.34, -0.1, 0), C("a8161a"), C("f0ece2"))
    m.box((0.1, 0.07, 0.11), T(1.38, 0.1, 0.055), "steel", WHITE, skip=("nz",))
    m.box((0.09, 0.06, 0.012), T(1.38, 0.1, 0.116), "paper", C("f6f4ee"), skip=("nz",))
    chalk_sign(m, T(1.62, 0.0, 0, rz=-0.2))
    s.finish()
    return s


SETS = {
    "prop_wurst_counter": dict(fn=counter, slot="slot_counter", stall="bratwurst", kind="counter", section=True,
                               seed=41, cam=((0.2, -2.05, 0.68), (0.2, 0.0, 0.2), 25),
                               hero=((-0.72, -0.78, 0.52), (-0.86, 0.0, 0.2), 36)),
}
