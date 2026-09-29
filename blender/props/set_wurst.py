"""Bratwurst stand goods: a round swinging charcoal grill (Schwenkgrill) and the serving counter.

prop_wurst_counter -> slot_counter of stall_bratwurst
  act_grill        fire bowl with glowing coals (material coal_glow) and the gallows; origin at the bowl
                   centre on the counter. The engine's grill flare pulses every mesh under this node, so
                   its iron uses grill_iron (a whisper of emission keeps the flare off the iron).
  act_grill_swing  the round grate on three chains, pivot at the hook (for a gentle swing)
  act_sausage_0..7 Bratwürste on the grate, origin at each sausage's centre, long axis X
  act_smoke        where smoke should rise
  Rolls in a basket, mustard and ketchup pots, a stack of paper trays and one served Bratwurst im Brötchen.

On stall_bratwurst the grill sits over the carpenter's built-in firebox (x -1.75..-0.15 from the slot):
the set puts the fire bowl at x = -0.9, so it rests on that grate.
"""
import math

import bmesh
from mathutils import Matrix, Vector, noise

import goods as G
import vlib
from vlib import C, T, WHITE, jit, rng, seg

TWO_PI = 2 * math.pi
GX = -0.9


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


def chain(m, a, b, link=0.022, r=0.0026, mat="grill_iron", col=WHITE):
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
        m.torus(link * 0.5, r, 8, 4, "iron", M, col, mat)


def grill(s):
    iron = WHITE
    g = s.node("act_grill", (GX, 0.0, 0.0))
    n = seg(36, 16)
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
    k = 46 if not vlib.lite() else 16
    for i in range(k):
        rr = 0.165 * math.sqrt(rng.random())
        a = rng.uniform(0, TWO_PI)
        z = 0.052 + (0.165 - rr) * 0.12 + rng.uniform(0, 0.012)
        lump(coal, T(rr * math.cos(a), rr * math.sin(a), z, rz=rng.uniform(0, 6)), rng.uniform(0.02, 0.032),
             full, jit(WHITE, 0.2), "coal_glow", subd=1, seed=i * 1.3)
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
    bars = 13
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
    return gz + hook[2]


def mustard_pot(m, M, col=C("8a9aa8"), fill=C("c8961a"), label=None):
    n = seg(18, 10)
    m.lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.02), (0.052, 0.08), (0.047, 0.1), (0.048, 0.106),
             (0.043, 0.104), (0.043, 0.09)], n, "bisque", M, col, "glaze")
    m.torus(0.051, 0.003, n, 5, "ceramic", M @ T(0, 0, 0.05), C("1d3a78"), "glaze")
    m.disc(0.043, n, "sw_wet", M @ T(0, 0, 0.09), fill, "liquid")


def served(m, M):
    """One Bratwurst im Brötchen with a stripe of mustard, in a paper tray."""
    G.paper_tray(m, M, 0.22, 0.1, 0.03)
    G.roll(m, M @ T(0, 0, 0.004), L=0.13, W=0.07, H=0.04)
    G.sausage(m, M @ T(0, -0.004, 0.036), L=0.21, r=0.0125, bend=0.01, dark=False)
    pts = [(-0.08 + i * 0.016, -0.004 + 0.004 * math.sin(i * 1.7), 0.05) for i in range(11)]
    m.tube(pts, 0.004, 5, "sw_wet", M, C("d8a01a"), "liquid")


def counter():
    s = vlib.PropSet("prop_wurst_counter", "slot_counter", "bratwurst")
    m = s.static
    gz = grill(s)
    # sausages on the grate: two per row, four rows, each its own node with its pivot at its centre
    i = 0
    for y in (-0.11, -0.037, 0.037, 0.11):
        for x in (-0.075, 0.075):
            L = rng.uniform(0.13, 0.145)
            node = s.node(f"act_sausage_{i}", (GX + x + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.01, 0.01),
                                               gz + 0.003 + 0.0125))
            G.sausage(node, T(0, 0, 0, rz=rng.uniform(-0.12, 0.12)), L=L, r=0.0125, bend=rng.uniform(0.004, 0.012),
                      dark=i % 3 == 1)
            i += 1
    # grill tongs resting beside the grill
    for dy in (-0.006, 0.006):
        m.box((0.3, 0.012, 0.003), T(-0.45, -0.15 + dy * 1.4, 0.004, rz=0.25 + dy * 2), "steel", WHITE)
    # basket of rolls
    G.crate(m, T(0.05, 0.02, 0), 0.34, 0.26, 0.07, C("b48c5c"), slats=2)
    m.box((0.3, 0.22, 0.004), T(0.05, 0.02, 0.014), "sw_matte", C("e8e2d4"))
    for k in range(12 if not vlib.lite() else 6):
        row, col = divmod(k, 4)
        G.roll(m, T(0.05 - 0.105 + col * 0.07 + rng.uniform(-0.01, 0.01), 0.02 - 0.07 + row * 0.07 + rng.uniform(-0.01, 0.01),
                    0.016 + (0.03 if k >= 8 else 0.0), rz=math.pi / 2 + rng.uniform(-0.3, 0.3)),
               L=0.105, W=0.068, H=0.03)
    # mustard (salt-glazed stoneware) and ketchup pots with wooden spatulas
    mustard_pot(m, T(0.33, 0.12, 0), C("8a9aa8"), C("c8961a"))
    mustard_pot(m, T(0.45, 0.13, 0), C("f0ece2"), C("8a0e0a"))
    for x, a in ((0.33, 0.3), (0.45, -0.4)):
        m.box((0.012, 0.004, 0.16), T(x + 0.02, 0.12, 0.1, rx=0.3, rz=a), vlib.RW("wood"), C("c8a070"))
    # stack of nested paper trays and one served Bratwurst
    for k in range(9):
        G.paper_tray(m, T(0.88, 0.1, k * 0.0045), 0.22, 0.1, 0.03)
    served(m, T(0.64, -0.12, 0, rz=0.25))
    # a napkin dispenser
    m.box((0.1, 0.07, 0.11), T(1.05, -0.12, 0.055), "steel", WHITE)
    m.box((0.09, 0.06, 0.012), T(1.05, -0.12, 0.116), "paper", C("f6f4ee"))
    s.finish()
    return s


SETS = {
    "prop_wurst_counter": dict(fn=counter, slot="slot_counter", stall="bratwurst", kind="counter", section=True,
                               seed=41, cam=((-0.3, -1.7, 0.62), (-0.15, 0.0, 0.2), 25)),
}
