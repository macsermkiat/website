"""Bratwurst stand goods: a round swinging charcoal grill (Schwenkgrill) and the serving counter.

prop_wurst_counter -> slot_counter of stall_bratwurst
  act_grill        three-legged fire bowl with glowing coals (material coal_glow) and the gallows post;
                   origin at the grill's base, on the carpenter's slot_grill under the hood (read from the
                   stall glb at build time by grill_probe.mjs). The engine's grill flare pulses every mesh
                   under this node, so its iron uses grill_iron (a whisper of emission keeps the flare off it).
  act_grill_swing  the round grate on three chains, pivot at the hook (the engine swings it gently)
  act_sausage_0..9 Bratwürste on the grate, children of act_grill_swing so they ride the swing.
  act_sausage_10..15  done ones keeping warm in a steel tray on the counter right of the grill.
                   Every sausage has its origin at its base (where it rests), long axis along X; the axis
                   the engine should turn it about is SAUSAGE_R above that (items.json "turn_axis").
  act_roll_0..15   Brötchen in the basket and the paper bag, origin at the base of each roll
  act_served_0/1   a Bratwurst im Brötchen and a Currywurst on paper trays
  act_smoke        where smoke should rise
  Charcoal sack and ash bucket, a tray of raw sausages, mustard and ketchup pots, fork cup, paper trays,
  squeeze bottles, napkins, tip jar, bread board and a chalk price sign.

The serving goods keep their design spacing and start right of the grill and the warming tray (squeezed if
the counter is shorter). check_props runs seat_check.mjs, which fails if any triangle cuts into the stall.
"""
import math
import os

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


def irregular(bm, r, seed, rough, squash):
    """Charcoal-chunk vertices from an icosphere: broad low-frequency lumps plus finer bumps, its own stretch
    per lump, and one or two flat broken faces (vertices past a random plane are pushed onto it), so the
    lumps read as split wood charcoal, not pebbles."""
    import random
    rr = random.Random(int(seed * 1000) + 7)
    sx, sy = rr.uniform(0.8, 1.45), rr.uniform(0.7, 1.05)
    cuts = []
    for _ in range(rr.choice((1, 2, 2))):
        nrm = Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-0.4, 0.6))).normalized()
        cuts.append((nrm, r * rr.uniform(0.45, 0.75)))
    out = []
    off = Vector((seed, seed * 1.7, 0))
    for v in bm.verts:
        p = v.co.copy()
        k = 1 + rough * 0.8 * noise.noise(p * (1.4 / r) + off) + rough * 0.45 * noise.noise(p * (4.0 / r) + off * 2)
        q = Vector((p.x * k * sx, p.y * k * 0.9 * sy, p.z * k * squash))
        for nrm, d in cuts:
            e = q.dot(nrm) - d
            if e > 0:
                q -= nrm * e
        out.append((q.x, q.y, q.z))
    return out


def coal_lump(m, M, r, col, seed=0.0, hot_top=False, subd=1, rough=0.35, squash=0.7):
    """A burning charcoal lump on the coal_glow material. Its faces map into the two halves of the coal maps
    (atlas_goods.g_coal / coal_emit): the sides into a random window of the glowing left half (bright cracks,
    ember glow), the upward faces into a window of the ash right half (grey, dark), unless `hot_top`. Each lump
    gets its own windows, so the bed is a patchwork of bright, dull and ashy coals, not one stamped texture."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=r)
    verts, faces, uvs = [], [], []
    verts = irregular(bm, r, seed, rough, squash)
    win = 0.16 + 0.1 * drng.random()                        # window size in UV
    hu, hv = drng.uniform(0.0, 0.5 - win), drng.uniform(0.0, 1.0 - win)
    au, av = drng.uniform(0.5, 1.0 - win), drng.uniform(0.0, 1.0 - win)
    for f in bm.faces:
        ids = [v.index for v in f.verts]
        c = Vector((0, 0, 0))
        for i in ids:
            c += Vector(verts[i])
        c /= len(ids)
        e1 = Vector(verts[ids[1]]) - Vector(verts[ids[0]])
        e2 = Vector(verts[ids[2]]) - Vector(verts[ids[0]])
        nz = e1.cross(e2).normalized().z
        top = nz > 0.55 and not hot_top
        u0, v0 = (au, av) if top else (hu, hv)
        faces.append(tuple(ids))
        uvs.append([(u0 + win * (0.5 + 0.5 * verts[i][0] / r), v0 + win * (0.5 + 0.5 * verts[i][1] / r)) for i in ids])
    bm.free()
    m.add(verts, faces, uvs, M, col, "coal_glow", False)


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


def probe_stall():
    """Measure the Bratwurst stall's grill opening (grill_probe.mjs) in the slot_counter frame. The carpenter
    owns the stall and may move or rebuild the opening, so the grill is placed from the glb on disk."""
    import json
    import subprocess
    path = os.path.join(vlib.MODELS, "stall_bratwurst.glb")
    try:
        out = subprocess.run(["node", os.path.join(vlib.HERE, "grill_probe.mjs"), path, "slot_counter"],
                             capture_output=True, text=True, timeout=120, cwd=vlib.REPO)
        pr = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as ex:
        print(f"[wurst] grill probe failed ({ex}); using the round-1 opening")
        pr = {}
    PROBE.clear()
    PROBE.update(pr)
    return pr


PROBE = {}
BOWL_R = 0.23          # fire bowl radius (the grate is 0.21)


def seat():
    """(x, y, floor_z, counter_x0, counter_x1): where act_grill stands and the counter's ends, from the probe
    (slot frame, metres). The carpenter's slot_grill empty wins; else the hood's centre over the highest
    surface under it."""
    pr = PROBE or probe_stall()
    counter = pr.get("counter") or {"x0": -1.86, "x1": 1.86}
    sg, hood, floor = pr.get("slot_grill"), pr.get("hood"), pr.get("floor")
    if sg:
        x, y, fz = sg["x"], sg["y"], sg["z"]
    else:
        x = hood["cx"] if hood else -0.9
        fz = floor["z"] if floor else 0.0
        y = 0.0
        if floor:
            y = min(max(0.0, floor["y0"] + BOWL_R + 0.02), floor["y1"] - BOWL_R - 0.02)
    return x, y, fz, counter["x0"], counter["x1"]


def grill(s):
    """The Schwenkgrill, standing in the stall's grill opening: act_grill's origin is on the surface it
    stands on (the opening's deck or hearth, from the probe), under the fire bowl's centre."""
    iron = WHITE
    gx, gy, fz, _, _ = seat()
    g = s.node("act_grill", (gx, gy, fz))
    s.item("act_grill", "Schwenkgrill over the charcoal", "grill")
    n = seg(32, 12)
    # heights from the counter top (slot z 0) turned into the node's frame (origin on the deck)
    rim = 0.18                                           # fire bowl rim, 18 cm above the counter
    base = rim - 0.108 + 0.03                           # bowl profile runs 0.03..0.108 in its own frame
    zb = base - 0.03 - fz                               # bowl frame origin, above the deck
    # fire bowl: shallow iron dish with a rolled rim
    k_ = BOWL_R / 0.214
    bowl = [(0.0, 0.03), (0.14 * k_, 0.03), (0.19 * k_, 0.05), (0.21 * k_, 0.1), (0.214 * k_, 0.108),
            (0.205 * k_, 0.108), (0.182 * k_, 0.058), (0.135 * k_, 0.04), (0.0, 0.04)]
    g.lathe(bowl, n, vlib.RW("iron"), T(0, 0, zb), iron, "grill_iron", smooth=True)
    g.torus(0.214 * k_ - 0.002, 0.007, n, 6, "iron", T(0, 0, zb + 0.108), C("aaaaaa"), "grill_iron")
    # its stand: three splayed legs from the deck to the bowl's belly, a ring brace, and an ash pan
    leg_top = zb + 0.035
    for k in range(3):
        a = TWO_PI * k / 3 + 0.5
        top = Vector((0.13 * math.cos(a), 0.13 * math.sin(a), leg_top))
        foot = Vector((0.19 * math.cos(a), 0.19 * math.sin(a), 0.0))
        g.tube([foot + Vector((0, 0, 0.012)), top], 0.011, 6, "iron", None, iron, "grill_iron")
        g.box((0.05, 0.05, 0.012), T(foot.x, foot.y, 0.006, rz=a), "iron", iron, "grill_iron")
    if leg_top > 0.08:
        rz = leg_top * 0.45
        rr = 0.19 - (0.19 - 0.13) * (rz / leg_top)
        g.torus(rr, 0.006, seg(20, 10), 5, "iron", T(0, 0, rz), iron, "grill_iron")
        g.lathe([(0.0, rz - 0.004), (rr - 0.01, rz - 0.004), (rr - 0.006, rz + 0.018), (rr - 0.012, rz + 0.018),
                 (rr - 0.02, rz + 0.002), (0.0, rz + 0.002)], seg(20, 10), vlib.RW("iron"), None, C("8a8a8a"),
                "grill_iron")
        # grey ash that fell through into the pan
        g.disc(rr - 0.03, seg(16, 8), vlib.R("coal", sub=(0.55, 0.05, 0.95, 0.95)), T(0, 0, rz + 0.006),
               C("bdb8b0"), "atlas")
    # coal bed: glowing chunks with ash, piled in the bowl
    coal = s.node("coals", (0, 0, zb), parent="act_grill")
    coal.lathe([(0.0, 0.05), (0.17 * k_, 0.05), (0.185 * k_, 0.062), (0.0, 0.066)], 20 if not vlib.lite() else 8,
               vlib.Reg([0.0, 0.0, 1.0, 1.0]), None, C("6a6560"), "coal_glow")
    # burning lumps: each its own patch of the glow map (bright cracks on the sides, ash on most tops);
    # about one in five burns right through its top
    kn = 40 if not vlib.lite() else 12
    for i in range(kn):
        rr = 0.18 * math.sqrt(drng.random())
        a = drng.uniform(0, TWO_PI)
        z = 0.058 + (0.18 - rr) * 0.12 + drng.uniform(0, 0.012)
        coal_lump(coal, T(rr * math.cos(a), rr * math.sin(a), z, rz=drng.uniform(0, 6)), drng.uniform(0.02, 0.032),
                  jit(WHITE, 0.12), seed=i * 1.3, hot_top=drng.random() < 0.2)
    # a few dead, grey coals near the rim (burnt out, no glow: plain atlas charcoal under ash) and a fine
    # layer of pale ash drifted over the bed and against the bowl's wall
    for i in range(6 if not vlib.lite() else 2):
        a = drng.uniform(0, TWO_PI)
        rr = drng.uniform(0.14, 0.17) * k_
        lump(coal, T(rr * math.cos(a), rr * math.sin(a), 0.064 + drng.uniform(0, 0.006), rz=drng.uniform(0, 6)),
             drng.uniform(0.016, 0.024), vlib.R("coal", sub=(0.55, 0.05, 0.95, 0.95)), jit(C("a8a49e"), 0.1),
             "atlas", subd=1, seed=50 + i * 1.9)
    # the ash drift against the bowl wall: mottled grey ash over char (the coal map's ash half), not a flat
    # pale ring (round 2 read as a white plate)
    coal.lathe([(0.15 * k_, 0.062), (0.18 * k_, 0.066), (0.19 * k_, 0.072), (0.186 * k_, 0.074)],
               20 if not vlib.lite() else 8,
               vlib.R("coal", sub=(0.55, 0.05, 0.95, 0.95)), None, C("a8a49c"), "atlas")
    for i in range(7 if not vlib.lite() else 2):
        a = drng.uniform(0, TWO_PI)
        rr = 0.15 * math.sqrt(drng.random())
        z = 0.058 + (0.18 - rr) * 0.12 + 0.03
        lump(coal, T(rr * math.cos(a), rr * math.sin(a), z, rz=drng.uniform(0, 6)), drng.uniform(0.014, 0.022),
             vlib.R("coal", sub=(0.55, 0.05, 0.95, 0.95)), jit(C("b0aca4"), 0.08), "atlas", subd=1, rough=0.25,
             squash=0.22, seed=80 + i)
    # gallows: a square post from the deck on the left of the bowl, an arm over it, a hook
    post_top = 0.64 - fz
    px = -0.262
    g.box((0.034, 0.034, post_top), T(px, 0, post_top / 2), vlib.RW("iron"), iron, "grill_iron")
    g.box((0.08, 0.14, 0.014), T(px, 0, 0.007), vlib.RW("iron"), iron, "grill_iron")          # foot plate
    for sy in (-1, 1):                                                                       # foot gussets
        g.box((0.05, 0.006, 0.05), T(px - 0.02, sy * 0.02, 0.035, ry=0.6), "iron", iron, "grill_iron")
    g.box((0.28, 0.028, 0.028), T(px + 0.13, 0, post_top - 0.014), vlib.RW("iron"), iron, "grill_iron")
    brace = [Vector((px, 0, post_top - 0.17)), Vector((px + 0.11, 0, post_top - 0.03))]
    g.tube(brace, 0.008, 6, "iron", None, iron, "grill_iron")
    g.torus(0.014, 0.003, 10, 4, "iron", T(0, 0.0, post_top - 0.045, rx=math.pi / 2), iron, "grill_iron")
    # swinging grate on three chains, pivot at the hook
    hook = (0, 0.0, post_top - 0.058)
    sw = s.node("act_grill_swing", hook, parent="act_grill")
    gz = (rim + 0.05 - fz) - hook[2]                    # the grate hangs 5 cm over the rim
    rim_r = 0.21
    sw.torus(rim_r, 0.0065, n, 6, "iron", T(0, 0, gz), iron, "grill_iron")
    sw.torus(0.08, 0.004, seg(20, 10), 5, "iron", T(0, 0, gz), iron, "grill_iron")
    bars = 15 if not vlib.lite() else 7
    for i in range(bars):
        y = -rim_r + (i + 0.5) * 2 * rim_r / bars
        half = math.sqrt(max(0.0, rim_r ** 2 - y ** 2))
        sw.box((2 * half, 0.005, 0.005), T(0, y, gz), "iron", C("8a8a8a"), "grill_iron")
    for k in range(3):
        a = TWO_PI * k / 3 + math.pi / 2
        chain(sw, (0, 0, 0), (rim_r * 0.98 * math.cos(a), rim_r * 0.98 * math.sin(a), gz + 0.004))
    # a crank handle on the post's front (height adjuster), a poker leaning on the post
    cz = 0.42 - fz
    g.cyl(0.006, 0.006, 0.06, 6, "iron", T(px, -0.047, cz, rx=math.pi / 2), iron, "grill_iron")
    g.box((0.01, 0.01, 0.07), T(px, -0.077, cz + 0.03), "iron", iron, "grill_iron")
    g.tube([Vector((px - 0.03, -0.16, 0.0)), Vector((px - 0.02, -0.02, cz - 0.05))], 0.005, 5, "iron", None,
           iron, "grill_iron")
    s.empty("act_smoke", (0, 0, rim + 0.1 - fz), parent="act_grill")
    s.item("act_grill_swing", "Swinging grill grate", "grill")
    s.item("act_smoke", "Smoke from the grill", "effect")
    return gz


def mustard_pot(m, M, col=C("8a9aa8"), fill=C("c8961a"), label=None):
    n = seg(14, 8)
    m.lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.02), (0.052, 0.08), (0.047, 0.1), (0.048, 0.106),
             (0.043, 0.104), (0.043, 0.09)], n, "bisque", M, col, "glaze")
    m.torus(0.051, 0.003, n, 4, "ceramic", M @ T(0, 0, 0.05), C("1d3a78"), "glaze")
    m.disc(0.043, n, "sw_wet", M @ T(0, 0, 0.09), fill, "liquid")


def served(s, i, x, y, rz, curry=False):
    """A Bratwurst im Brötchen with a stripe of mustard, or a Currywurst in slices with sauce, curry powder
    and a wooden fork, in a paper tray: act_served_<i> (base pivot)."""
    node = s.node(f"act_served_{i}", (x, y, 0), rot=(0, 0, rz))
    G.paper_tray(node, None, 0.22, 0.1, 0.03)
    if not curry:
        G.roll(node, T(0, 0, 0.004), L=0.13, W=0.07, H=0.04)
        G.sausage(node, T(0, -0.004, 0.036), L=0.21, r=0.0125, bend=0.01, dark=False, seed=9.0)
        pts = [(-0.08 + k * 0.016, -0.004 + 0.004 * math.sin(k * 1.7), 0.05) for k in range(11)]
        node.tube(pts, 0.004, 5, "sw_wet", None, C("d8a01a"), "liquid")
        s.item(f"act_served_{i}", "Bratwurst im Brötchen with mustard", "served")
        return
    for k in range(7):
        # slices lying at a slant, overlapping, under a pool of curry ketchup
        G.sausage(node, T(-0.075 + k * 0.025, 0.0, 0.012, ry=0.35, rz=math.pi / 2), L=0.024, r=0.0125, bend=0.0,
                  dark=k % 3 == 0, seed=30 + k)
    node.lathe([(0.0, 0.02), (0.075, 0.018), (0.085, 0.012), (0.0, 0.028)], seg(14, 6), "sw_wet",
               Matrix.Diagonal((1.2, 0.42, 1.0, 1.0)), C("8a1a0c"), "liquid")
    for k in range(9 if not vlib.lite() else 3):
        node.box((0.004, 0.004, 0.002), T(drng.uniform(-0.07, 0.07), drng.uniform(-0.025, 0.025), 0.029,
                                          rz=drng.uniform(0, 3)), "sw_matte", C("c8781a"))
    node.box((0.075, 0.009, 0.002), T(0.04, 0.022, 0.034, ry=-0.1, rz=0.5), vlib.RW("wood"), C("d8b890"))
    s.item(f"act_served_{i}", "Currywurst with curry powder and a wooden fork", "served")


def charcoal_sack(m, M):
    """A paper sack of charcoal, rolled down at the top, lumps showing."""
    n = seg(12, 6)
    m.lathe([(0.0, 0.0), (0.1, 0.0), (0.12, 0.03), (0.12, 0.2), (0.115, 0.23), (0.125, 0.26), (0.11, 0.27),
             (0.1, 0.24)], n, vlib.RW("kraft"), M @ Matrix.Diagonal((1.0, 0.62, 1.0, 1.0)), C("b89868"))
    m.disc(0.1, n, "sw_matte", M @ T(0, 0, 0.235) @ Matrix.Diagonal((1.0, 0.62, 1.0, 1.0)), C("1a1816"), "atlas")
    for k in range(6 if not vlib.lite() else 2):
        a = TWO_PI * k / 6
        lump(m, M @ T(0.055 * math.cos(a), 0.03 * math.sin(a), 0.245, rz=k), 0.02, vlib.R("coal"),
             C("3a3a3a"), "atlas", subd=1, seed=k * 2.1)


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


DESIGN_X0, DESIGN_X1 = -0.13, 1.87      # the counter the layout was drawn for (round 1 stall, slot frame)
SAUSAGE_R = 0.0125


def sausage_node(s, name, loc, label, parent=None, L=0.14, bend=0.008, dark=False, seed=0.0, rz=0.0, raw=False):
    """One Bratwurst, act_sausage_<n>: its origin is at its base (the middle of its underside, where it
    rests), long axis along the node's X. The engine turns a sausage about its long axis, which is
    SAUSAGE_R above the origin (items.json: turn_axis)."""
    node = s.node(name, loc, parent=parent, rot=(0, 0, rz) if rz else None)
    G.sausage(node, T(0, 0, SAUSAGE_R), L=L, r=SAUSAGE_R, bend=bend, dark=dark, seed=seed, raw=raw)
    s.item(name, label, "sausage", raw=raw, turn_axis={"offset_blender_z": SAUSAGE_R, "offset_threejs_y": SAUSAGE_R,
                                              "axis": "node X"})
    return node


def counter():
    s = vlib.PropSet("prop_wurst_counter", "slot_counter", "bratwurst")
    m = s.static
    gz = grill(s)
    gx, gy, fz, cx0, cx1 = seat()
    # the serving goods keep their design spacing, shifted so they start right of the grill and the warming
    # tray beside it (and squeezed if the counter is shorter than the design)
    start = max(cx0 + 0.05, gx + BOWL_R + 0.32)
    k_ = min(1.0, (cx1 - 0.05 - start) / (DESIGN_X1 + 0.1 - DESIGN_X0))

    def X(x):
        return start + (x - DESIGN_X0) * k_
    # sausages on the grate: five rows of two, children of the swinging grate so they ride it
    i = 0
    for row, y in enumerate((-0.14, -0.07, 0.0, 0.07, 0.14)):
        for x in (-0.075, 0.075):
            L = rng.uniform(0.13, 0.145) if abs(y) < 0.1 else rng.uniform(0.125, 0.132)
            dx, dy, rz = rng.uniform(-0.01, 0.01), rng.uniform(-0.008, 0.008), rng.uniform(-0.12, 0.12)
            sausage_node(s, f"act_sausage_{i}", (x + dx, y + dy, gz + 0.003), "Bratwurst on the grill",
                         parent="act_grill_swing", L=L, bend=rng.uniform(0.004, 0.012), dark=i % 3 != 2,
                         seed=i * 1.7, rz=rz)
            i += 1
    # done ones keeping warm in a steel tray on the counter, right beside the grill under the hood
    tx, ty = gx + BOWL_R + 0.17, 0.06
    m.lathe([(0.0, 0.0), (0.125, 0.0), (0.13, 0.034), (0.123, 0.034), (0.117, 0.004), (0.0, 0.004)], seg(18, 6),
            "steel", T(tx, ty, 0) @ Matrix.Diagonal((1.0, 0.62, 1.0, 1.0)), WHITE)
    # the tray is long in x, so the sausages lie along x side by side (five rows), the sixth on top
    for k in range(6):
        y, z = (ty - 0.052 + k * 0.026, 0.004) if k < 5 else (ty - 0.013, 0.004 + 2 * SAUSAGE_R - 0.004)
        sausage_node(s, f"act_sausage_{10 + k}", (tx + rng.uniform(-0.006, 0.006), y, z),
                     "Bratwurst keeping warm", L=0.132, bend=0.005, dark=True, seed=20 + k,
                     rz=rng.uniform(-0.06, 0.06))
    # grill tongs lying in front of the tray
    for dy in (-0.006, 0.006):
        m.box((0.3, 0.012, 0.003), T(tx + 0.02, -0.17 + dy * 1.4, 0.0015, rz=0.2 + dy * 2), "steel", WHITE)
    # left of the grill, under the hood: a sack of charcoal and a steel ash bucket
    if gx - 0.62 > cx0:
        charcoal_sack(m, T(gx - 0.56, 0.05, 0, rz=0.25))
        m.lathe([(0.0, 0.0), (0.075, 0.0), (0.085, 0.16), (0.089, 0.165), (0.082, 0.165), (0.072, 0.008),
                 (0.0, 0.008)], seg(16, 8), "steel", T(gx - 0.4, -0.13, 0), C("9a9a9a"))
        m.disc(0.078, seg(14, 6), "sw_matte", T(gx - 0.4, -0.13, 0.11), C("8a847c"), "atlas")
        m.torus(0.08, 0.003, seg(12, 6), 3, "steel", T(gx - 0.4, -0.13, 0.168, rx=math.pi / 2),
                C("7a7a7a"), arc=math.pi, a0=0.0)  # handle up over the top
    bx, by = X(0.4), 0.03
    # between the warming tray and the rolls: a steel tray of raw Bratwurst waiting for the grill, set back so
    # the tongs keep the front
    rx0, rx1 = tx + 0.14, bx - 0.18
    if rx1 - rx0 > 0.3:
        rxm = (rx0 + rx1) / 2
        Mt = T(rxm, 0.09, 0, rz=-0.04)
        m.lathe([(0.0, 0.0), (0.13, 0.0), (0.138, 0.04), (0.132, 0.04), (0.125, 0.004), (0.0, 0.004)], seg(16, 6),
                "steel", Mt @ Matrix.Diagonal((1.0, 0.64, 1.0, 1.0)), C("d0d0d0"))
        # lying along the tray's long side: five side by side, three more on top. Round 3: each raw one is its
        # own clickable act_sausage_16..23 (base pivot, like the grilled ones), in full and lite alike
        # (own seeded generator: drng advances differently in full and lite, which moved these in lite)
        import random
        rraw = random.Random(4242)
        for k in range(8):
            y, z = (-0.052 + k * 0.026, 0.004) if k < 5 else (-0.039 + (k - 5) * 0.026, 0.004 + 2 * SAUSAGE_R - 0.004)
            dx, jr = rraw.uniform(-0.008, 0.008), rraw.uniform(-0.06, 0.06)
            drng.random(), drng.random()     # keep drng's stream for the goods after the tray as before
            sausage_node(s, f"act_sausage_{16 + k}", tuple(Mt @ Vector((dx, y, z))), "Raw Bratwurst, ready for the grill",
                         L=0.13, bend=0.005, seed=40 + k, rz=-0.04 + jr, raw=True)
    # basket of rolls, stacked two deep, each roll its own node
    G.crate(m, T(bx, by, 0), 0.34, 0.26, 0.07, C("b48c5c"), slats=2)
    m.box((0.3, 0.22, 0.004), T(bx, by, 0.014), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k in range(14):
        layer, j = divmod(k, 8)
        row, col = divmod(j, 4)
        if layer:
            row, col = divmod(j, 3)
        loc = (bx - 0.105 + col * 0.07 + (0.035 if layer else 0.0) + rng.uniform(-0.008, 0.008),
               by - 0.035 + row * 0.07 + rng.uniform(-0.008, 0.008), 0.016 + 0.028 * layer)
        node = s.node(f"act_roll_{k}", loc, rot=(0, 0, math.pi / 2 + rng.uniform(-0.3, 0.3)))
        G.roll(node, None, L=0.105, W=0.068, H=0.03)
        s.item(f"act_roll_{k}", "Brötchen (bread roll)", "roll")
    # a paper bag of more rolls lying behind the basket, two peeking out
    Mb = T(bx + 0.02, 0.175, 0, rz=0.06)
    m.box((0.26, 0.12, 0.05), Mb @ T(0, 0, 0.025), vlib.RW("kraft"), C("d8b890"), skip=("nz",))
    for k in range(2):
        node = s.node(f"act_roll_{14 + k}", (bx - 0.14 - k * 0.075, 0.18 - 0.01 * k, 0),
                      rot=(0, 0, 0.1 + rng.uniform(-0.2, 0.2)))
        G.roll(node, None, L=0.1, W=0.066, H=0.03)
        s.item(f"act_roll_{14 + k}", "Brötchen (bread roll)", "roll")
    # mustard (salt-glazed stoneware) and ketchup pots with wooden spatulas
    mustard_pot(m, T(X(0.7), 0.13, 0), C("8a9aa8"), C("c8961a"))
    mustard_pot(m, T(X(0.82), 0.14, 0), C("f0ece2"), C("8a0e0a"))
    for x, a in ((X(0.7), 0.3), (X(0.82), -0.4)):
        m.box((0.012, 0.004, 0.16), T(x + 0.02, 0.13, 0.1, rx=0.3, rz=a), vlib.RW("wood"), C("c8a070"))
    # a tin cup of wooden forks
    m.lathe([(0.0, 0.0), (0.035, 0.0), (0.036, 0.1), (0.033, 0.1), (0.032, 0.006), (0.0, 0.006)], seg(12, 6), "steel",
            T(X(0.72), -0.02, 0), C("c8c8c8"))
    for k in range(9 if not vlib.lite() else 3):
        a = TWO_PI * k / 9
        m.box((0.006, 0.002, 0.09), T(X(0.72) + 0.015 * math.cos(a), -0.02 + 0.015 * math.sin(a), 0.08,
                                      rx=0.15 * math.sin(a), ry=-0.15 * math.cos(a)), vlib.RW("wood"), C("d8b890"))
    # stack of nested paper trays, and two served portions in front
    for k in range(6 if not vlib.lite() else 2):
        G.paper_tray(m, T(X(1.12), 0.12, k * 0.0055, rz=drng.uniform(-0.05, 0.05)), 0.22, 0.1, 0.03)
    served(s, 0, X(0.95), -0.14, 0.25)
    served(s, 1, X(1.2), -0.12, -0.15, curry=True)
    # squeeze bottles, a napkin dispenser, a tip jar and the price sign
    squeeze_bottle(m, T(X(1.4), -0.12, 0), C("d8a820"), C("c83020"))
    squeeze_bottle(m, T(X(1.47), -0.09, 0), C("a8161a"), C("f0ece2"))
    m.box((0.1, 0.07, 0.11), T(X(1.4), 0.11, 0.055), "steel", WHITE, skip=("nz",))
    m.box((0.09, 0.06, 0.012), T(X(1.4), 0.11, 0.116), "paper", C("f6f4ee"), skip=("nz",))
    m.lathe([(0.0, 0.0), (0.04, 0.0), (0.042, 0.004), (0.042, 0.1), (0.045, 0.108), (0.038, 0.11)], seg(12, 6),
            "sw_vgloss", T(X(1.56), -0.1, 0), C("dfe8e4"), "glass")
    for k in range(5 if not vlib.lite() else 2):
        m.cyl(0.011, 0.011, 0.002, 10, "brass" if k % 2 else "sw_metal", T(X(1.56) + drng.uniform(-0.02, 0.02),
              -0.1 + drng.uniform(-0.02, 0.02), 0.004 + k * 0.0022, rx=drng.uniform(-0.2, 0.2)), C("d8c8a8"))
    # a bread board with a knife and two split rolls, then the price sign at the end
    G.board(m, T(X(1.74), 0.08, 0, rz=0.06), 0.3, 0.18, 0.02, C("c49a6c"))
    m.box((0.2, 0.022, 0.0015), T(X(1.72), 0.02, 0.021, rz=0.1), "steel", WHITE)
    m.box((0.1, 0.02, 0.016), T(X(1.72) + 0.145, 0.034, 0.028, rz=0.1), vlib.RW("wood"), C("3a2414"))
    for k in range(2):
        G.roll(m, T(X(1.68) + k * 0.11, 0.11, 0.02, rz=0.3 + k, rx=0.0), L=0.1, W=0.066, H=0.024)
    chalk_sign(m, T(min(X(1.98), cx1 - 0.16), 0.02, 0, rz=-0.2))
    s.report_extra = {"grill_seat": {"x": round(gx, 3), "y": round(gy, 3), "floor_z": round(fz, 3),
                                     "counter_x0": cx0, "probe": dict(PROBE)}}
    s.finish()
    return s


SETS = {
    "prop_wurst_counter": dict(fn=counter, slot="slot_counter", stall="bratwurst", kind="counter", section=True,
                               seed=41, cam=((0.2, -2.05, 0.68), (0.2, 0.0, 0.2), 25),
                               hero=((-0.55, -0.95, 0.58), (-0.62, 0.0, 0.2), 32),
                               in_stall="stall_bratwurst.glb",
                               # the coals' own glow does the work; a small ember light just over the bed lights the grate from below
                               stall_lights=(("env_ember", 'POINT', (-0.9, 0.0, 0.2), 6, (1.0, 0.36, 0.08), 0.15),),
                               stall_dim={"in_stall_grill": 0.2},
                               stall_cams={"in_stall": ((-0.1, -2.5, 0.75), (-0.15, 0.1, 0.35), 26),
                                           "in_stall_grill": ((-0.55, -1.05, 0.42), (-0.88, 0.05, 0.32), 32)}),
}
