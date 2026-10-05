"""Bratwurst stand goods: a round swinging charcoal grill (Schwenkgrill) and the serving counter.

prop_wurst_counter -> slot_counter of stall_bratwurst
  act_grill        three-legged fire bowl with glowing coals (material coal_glow) and the gallows post;
                   origin at the grill's base, on the carpenter's slot_grill under the hood (read from the
                   stall glb at build time by grill_probe.mjs).
  act_grill_swing  the round grate on three chains, pivot at the hook (the engine swings it gently); its child
                   sausages_grill is the merged scenery of ten Bratwürste on the grate (round 10: no act_ names)
  act_smoke        where smoke should rise
  act_writing_paper + write_writing_paper   the Marktblatt pad (the Writing section, unchanged)
  Round 10 (Mac, 2026-10-05; ADR 0004 revision "Bratwurst plate"): the rows of clickable sausages and rolls are
  merged scenery now (warming tray, raw tray, roll basket). Clickable, on a two-step board at the counter front:
  act_wurst_thueringer, act_wurst_nuernberger (a trio), act_wurst_krakauer, act_wurst_curry (sliced, on a paper
  tray), act_roll; right of the board three squeeze bottles act_sauce_senf / _ketchup / _curry, each with
  fx_sauce_<key> at its nozzle tip, and the curry shaker act_shaker_curry (fx_shaker_curry at its lid); left of
  the board the empty paper plate act_plate with plate_spot_0..3 on its floor. Every one has its origin at its
  base and an items.json entry with name, label and action (plate, sauce, dust, clear).
  Scenery: charcoal sack and ash bucket, mustard and ketchup pots, fork cup, paper trays, napkins, tip jar,
  bread board and a chalk price sign.

check_props runs seat_check.mjs, which fails if any triangle cuts into the stall.
"""
import math
import os

import bmesh
from mathutils import Matrix, Vector, noise

import goods as G
import vlib
import vprint
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
    # round 6 pass 2 (headroom): 30 larger lumps instead of 40, the same bed coverage for 25 % fewer triangles
    kn = 30 if not vlib.lite() else 12
    for i in range(kn):
        rr = 0.18 * math.sqrt(drng.random())
        a = drng.uniform(0, TWO_PI)
        z = 0.058 + (0.18 - rr) * 0.12 + drng.uniform(0, 0.012)
        coal_lump(coal, T(rr * math.cos(a), rr * math.sin(a), z, rz=drng.uniform(0, 6)), drng.uniform(0.023, 0.036),
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


def chalk_sign(m, M):
    """A small A-frame chalkboard with the prices."""
    w, h = 0.26, 0.2
    for side in (-1, 1):
        Ms = M @ T(0, side * 0.025, 0, rx=side * 0.2) @ T(0, 0, h / 2)
        m.box((w, 0.01, h), Ms, "wurst_sign", WHITE, faces={"ny" if side < 0 else "py": "wurst_sign"})
        m.box((w + 0.02, 0.014, 0.015), Ms @ T(0, 0, h / 2), vlib.RW("wood"), C("6a4228"))
        m.box((w + 0.02, 0.014, 0.015), Ms @ T(0, 0, -h / 2 + 0.008), vlib.RW("wood"), C("6a4228"))


def marktblatt(s, x0, x1, y=-0.128):
    """The Marktblatt pad: a stack of greaseproof sheets printed with the market's masthead and border, and the
    top sheet as its own node, act_writing_paper (origin at the middle of its underside, on the stack), with the
    plain writing face write_writing_paper over its blank middle and cam_read_writing_paper leaning over it
    from the front, as a visitor leans over the counter."""
    pm = vlib.print_meta()
    W = min(0.28, x1 - x0 - 0.012)
    H = W * 0.75
    cx = (x0 + x1) / 2
    m = s.static
    stack_h = 0.007
    Ms = T(cx - 0.004, y + 0.003, 0, rz=0.05)
    # the sheets under the top one: printed top (peeking out where the top sheet sits askew), edge of many sheets
    m.box((W * 0.995, H * 0.995, stack_h), Ms @ T(0, 0, stack_h / 2), "pr_page_edge", vlib.WHITE, mat="print",
          faces={"pz": "pr_marktblatt"}, skip=("nz",))
    node = s.node("act_writing_paper", (cx, y, stack_h), rot=(0, 0, -0.03))
    wr = pm["marktblatt_write"]
    lift = 0.0004
    vprint.rect_ring(node, W, H, wr, "pr_marktblatt", T(0, 0, lift))
    node.quad([(-W / 2, H / 2, 0.0), (W / 2, H / 2, 0.0), (W / 2, -H / 2, 0.0), (-W / 2, -H / 2, 0.0)],
              "pr_paper", vlib.WHITE, "print")                                      # the sheet's underside
    ww, wh = (wr[2] - wr[0]) * W, (wr[3] - wr[1]) * H
    wx, wy = ((wr[0] + wr[2]) / 2 - 0.5) * W, ((wr[1] + wr[3]) / 2 - 0.5) * H
    face = vprint.write_node(s, "write_writing_paper", "act_writing_paper", (wx, wy, lift))
    vprint.write_rect(face, ww, wh, kind="paper")
    d = vprint.reading_distance(ww, wh, fill=0.82)
    el = math.radians(62)
    vprint.cam_read(s, "writing_paper", (wx, wy, lift), (wx, wy - d * math.cos(el), lift + d * math.sin(el)),
                    parent="act_writing_paper")
    s.item("act_writing_paper", "Marktblatt (market paper for wrapping)", "paper",
           write={"main": "write_writing_paper"}, size_cm=[round(W * 100, 1), round(H * 100, 1)],
           detail="Greaseproof market paper printed with the Nachtmarkt-Blatt masthead; the Bratwurst is wrapped in it.")
    return node


DESIGN_X0, DESIGN_X1 = -0.13, 1.87      # the counter the layout was drawn for (round 1 stall, slot frame)
SAUSAGE_R = 0.0125
SCENERY_K, SCENERY_RING = 8, 8          # round 10: the merged scenery sausages (12 x 10 when they were clickable)


def scenery_sausage(m, M, L=0.14, bend=0.008, dark=False, seed=0.0, raw=False):
    """Round 10: a Bratwurst merged into scenery (no act_ node): lying along M's X, M at its base."""
    G.sausage(m, M @ T(0, 0, SAUSAGE_R), L=L, r=SAUSAGE_R, bend=bend, dark=dark, seed=seed, raw=raw,
              k=SCENERY_K, ring=SCENERY_RING)


# ------------------------------------------------------------------ round 10: the plate board
# Mac (2026-10-05): "too much interaction in sausages ... just few different kind is enough. But if it's able to
# mix on plate and put on sauce must be nice." One of each kind on a two-step board at the counter front, three
# squeeze bottles, a curry shaker and an empty paper plate (docs/adr/0004 revision, BUILD.md "Bratwurst plate").
BOARD_X, BOARD_W = 0.66, 0.62
FRONT_Y, BACK_Y = -0.205, -0.093       # the two steps' middle lines (the counter front is at y -0.3)
FRONT_Z, BACK_Z = 0.022, 0.062           # their tops
SAUCES = {   # key: (display name, label, bottle colour, cap colour, sauce colour for the engine's squiggle)
    "senf": ("Senf (mustard)", "Senf", "d8a81a", "c83020", "#d6a21c"),
    "ketchup": ("Ketchup", "Ketchup", "b0141a", "f0ece2", "#a8140e"),
    "curry": ("Currysauce", "Currysauce", "c4561a", "2a1a12", "#b4400e"),
}
PLATE_R = 0.115
PLATE_SPOTS = [(-0.042, 0.036), (0.042, 0.036), (-0.042, -0.036), (0.042, -0.036)]


def plate_board(m):
    """A two-step serving board (Auslage): the low front step on the counter, the back step raised on two
    battens, so the back row shows over the front one from the lane."""
    wood = C("9a6c46")
    G.board(m, T(BOARD_X, FRONT_Y, 0), BOARD_W, 0.11, FRONT_Z, wood)
    for sx in (-1, 1):
        m.box((0.03, 0.1, BACK_Z - 0.022), T(BOARD_X + sx * (BOARD_W / 2 - 0.04), BACK_Y, (BACK_Z - 0.022) / 2),
              vlib.RW("wood"), C("8a6240"), skip=("nz",))
    G.board(m, T(BOARD_X, BACK_Y, BACK_Z - 0.022), BOARD_W, 0.12, 0.022, wood)


def wurst_items(s):
    """The four clickable kinds and the Brötchen, each its own node with its origin at its base on the board."""
    hi = dict(k=14, ring=12)
    # back step: a long Thüringer, browned with grill marks, and a thick, reddish smoked Krakauer
    n = s.node("act_wurst_thueringer", (BOARD_X - 0.14, BACK_Y, BACK_Z), rot=(0, 0, 0.04))
    G.sausage(n, T(0, 0, 0.014), L=0.22, r=0.014, bend=0.012, dark=True, seed=3.1, **hi)
    s.item("act_wurst_thueringer", "Thüringer Rostbratwurst", "wurst", label="Thüringer", action="plate",
           wurst="thueringer", detail="Long, thin and browned over the charcoal, with the grate's marks.")
    n = s.node("act_wurst_krakauer", (BOARD_X + 0.16, BACK_Y, BACK_Z), rot=(0, 0, -0.05))
    G.sausage(n, T(0, 0, 0.02), L=0.17, r=0.02, bend=0.03, dark=False, seed=5.3, k=14, ring=14,
             region="pr_smoked_casing", mat="print")   # round 10 pass 2: its own smoked casing
    s.item("act_wurst_krakauer", "Krakauer, smoked", "wurst", label="Krakauer", action="plate", wurst="krakauer",
           detail="Thick, coarse and smoked, reddish brown.")
    # front step: three small Nürnberger, a sliced Currywurst on a paper tray and a crusty Brötchen
    n = s.node("act_wurst_nuernberger", (BOARD_X - 0.22, FRONT_Y, FRONT_Z))
    for k, (dx, dy, a) in enumerate(((0.004, -0.02, 0.06), (-0.003, 0.0, -0.04), (0.005, 0.02, 0.09))):
        G.sausage(n, T(dx, dy, 0.0095, rz=a), L=0.085, r=0.0095, bend=0.004, dark=k == 1, seed=11 + k, k=8, ring=10)
    s.item("act_wurst_nuernberger", "Drei Nürnberger Rostbratwürstchen", "wurst", label="3 Nürnberger", action="plate",
           wurst="nuernberger", count=3, detail="Three finger-sized sausages from Nuremberg, grilled crisp.")
    n = s.node("act_wurst_curry", (BOARD_X + 0.0, FRONT_Y, FRONT_Z), rot=(0, 0, 0.03))
    G.paper_tray(n, None, 0.15, 0.075, 0.026)
    for k in range(6):
        G.sausage(n, T(-0.052 + k * 0.021, 0.0, 0.012, ry=0.35, rz=math.pi / 2), L=0.016, r=0.0125, bend=0.0,
                  dark=k % 3 == 0, seed=30 + k, cut=True)
    # curry ketchup pooled between the slices (their tops stay above it) and drizzled over
    n.lathe([(0.0, 0.012), (0.056, 0.011), (0.062, 0.008), (0.0, 0.0205)], seg(14, 6), "sw_wet",
            Matrix.Diagonal((1.05, 0.46, 1.0, 1.0)), C("8a1a0c"), "liquid")
    n.tube([(-0.055 + k * 0.011, 0.006 * math.sin(k * 1.9), 0.0245 + 0.001 * (k % 2)) for k in range(11)], 0.0028,
           5, "sw_wet", None, C("7a1408"), "liquid")
    for k in range(9 if not vlib.lite() else 3):
        n.box((0.004, 0.004, 0.002), T(drng.uniform(-0.05, 0.05), drng.uniform(-0.016, 0.016), 0.027,
                                       rz=drng.uniform(0, 3)), "sw_matte", C("c8781a"))
    n.box((0.06, 0.008, 0.002), T(0.035, 0.018, 0.031, ry=-0.1, rz=0.5), vlib.RW("wood"), C("d8b890"))
    s.item("act_wurst_curry", "Currywurst, sliced", "wurst", label="Currywurst", action="plate", wurst="curry",
           detail="Sliced Bratwurst under curry ketchup and a dusting of curry powder, with a wooden fork.")
    n = s.node("act_roll", (BOARD_X + 0.21, FRONT_Y, FRONT_Z), rot=(0, 0, 0.12))
    G.roll(n, None, L=0.11, W=0.07, H=0.042, n_side=14, n_rings=5)
    s.item("act_roll", "Brötchen (crusty bread roll)", "roll", label="Brötchen", action="plate", wurst="roll",
           detail="A crusty white roll, split for a Bratwurst.")


def sauce_bottle(s, key, x, y, rz=0.0):
    """A soft squeeze bottle standing on its base (act_sauce_<key>), label to the lane, a screw cap and a
    pointed nozzle; fx_sauce_<key> sits at the nozzle's tip (it moves with the bottle when the engine tips it)."""
    name, label, body, cap, sauce = SAUCES[key]
    node = s.node(f"act_sauce_{key}", (x, y, 0), rot=(0, 0, rz))
    n = seg(14, 7)
    node.lathe([(0.0, 0.0), (0.027, 0.0), (0.0305, 0.008), (0.0305, 0.135), (0.0285, 0.15), (0.0215, 0.16)], n,
               "sw_gloss", None, C(body), "glaze")
    # the label round the front
    la = TWO_PI * 0.42
    node.lathe([(0.0313, 0.035), (0.0313, 0.11)], seg(5, 3), f"pr_sauce_{key}", None, WHITE, "print", v_by="z",
               arc=la, u0=-math.pi / 2 - la / 2)
    # screw cap with a ribbed skirt and the nozzle
    node.lathe([(0.0225, 0.157), (0.0228, 0.178), (0.012, 0.183)], n, "sw_satin", None, C(cap))
    node.lathe([(0.009, 0.183), (0.0035, 0.21), (0.0018, 0.216), (0.0, 0.2165)], seg(10, 6), "sw_satin", None, C(cap))
    s.empty(f"fx_sauce_{key}", (0, 0, 0.2165), parent=f"act_sauce_{key}")
    s.item(f"act_sauce_{key}", name, "sauce", label=label, action="sauce", sauce=key, colour=sauce,
           fx=f"fx_sauce_{key}", detail=f"A squeeze bottle of {name.split(' (')[0]}: tap it to put some on the plate.")


def curry_shaker(s, x, y):
    """A tin curry shaker with a printed label and a pierced domed lid (act_shaker_curry); fx_shaker_curry at the
    lid's top, where the powder comes out."""
    node = s.node("act_shaker_curry", (x, y, 0), rot=(0, 0, -0.1))
    n = seg(14, 7)
    node.lathe([(0.0, 0.0), (0.021, 0.0), (0.022, 0.004), (0.022, 0.08)], n, "steel", None, C("d8d8d8"))
    la = TWO_PI * 0.5
    node.lathe([(0.0225, 0.012), (0.0225, 0.07)], seg(6, 3), "pr_shaker_curry", None, WHITE, "print", v_by="z",
               arc=la, u0=-math.pi / 2 - la / 2)
    node.lathe([(0.0228, 0.078), (0.0228, 0.088), (0.018, 0.097), (0.006, 0.1), (0.0, 0.1)], n, "steel", None,
               C("c8c8c8"))
    if not vlib.lite():
        for k in range(7):                      # the holes in the lid
            a = TWO_PI * k / 7
            node.disc(0.0016, 5, "sw_matte", T(0.007 * math.cos(a), 0.007 * math.sin(a), 0.1003), C("2a2018"))
    s.empty("fx_shaker_curry", (0, 0, 0.1), parent="act_shaker_curry")
    s.item("act_shaker_curry", "Curry powder", "spice", label="Currypulver", action="dust", colour="#c8781a",
           fx="fx_shaker_curry", detail="A tin of curry powder: tap it to dust the plate.")


def paper_plate(s, x, y):
    """An empty white paper plate (act_plate, origin at the middle of its underside) with plate_spot_0..3 on its
    floor where the chosen items land (a 2 x 2 grid, items lying along X)."""
    node = s.node("act_plate", (x, y, 0))
    n = seg(28, 12)
    # lathe faces point down for a profile running outwards, up for one running inwards
    top = [(PLATE_R, 0.016), (0.1, 0.012), (0.075, 0.0016), (0.0005, 0.0016)]
    bot = [(0.0005, 0.0003), (0.075, 0.0003), (0.1, 0.0107), (PLATE_R, 0.0147)]
    node.lathe(top, n, "paper", None, C("f6f4ee"), "atlas")
    node.lathe(bot, n, "paper", None, C("e8e4da"), "atlas")
    node.torus(PLATE_R - 0.0008, 0.0012, n, 3, "paper", T(0, 0, 0.0155), C("f2efe6"))
    for i, (px, py) in enumerate(PLATE_SPOTS):
        s.empty(f"plate_spot_{i}", (px, py, 0.0016), parent="act_plate")
    s.item("act_plate", "Paper plate", "plate", label="Pappteller", action="clear",
           spots=[f"plate_spot_{i}" for i in range(len(PLATE_SPOTS))], max_items=len(PLATE_SPOTS),
           clear_note="Guten Appetit", detail="Pick sausages, a roll and sauces for the plate; tap it to clear.")


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
    # round 10: the sausages on the grate are scenery, one merged mesh riding the swinging grate (sausages_grill,
    # a child of act_grill_swing): five rows of two, as full as before
    grate = s.node("sausages_grill", (0, 0, 0), parent="act_grill_swing")
    i = 0
    for row, y in enumerate((-0.14, -0.07, 0.0, 0.07, 0.14)):
        for x in (-0.075, 0.075):
            L = rng.uniform(0.13, 0.145) if abs(y) < 0.1 else rng.uniform(0.125, 0.132)
            dx, dy, rz = rng.uniform(-0.01, 0.01), rng.uniform(-0.008, 0.008), rng.uniform(-0.12, 0.12)
            scenery_sausage(grate, T(x + dx, y + dy, gz + 0.003, rz=rz), L=L, bend=rng.uniform(0.004, 0.012),
                            dark=i % 3 != 2, seed=i * 1.7)
            i += 1
    # done ones keeping warm in a steel tray on the counter, right beside the grill under the hood (scenery)
    tx, ty = gx + BOWL_R + 0.17, 0.06
    m.lathe([(0.0, 0.0), (0.125, 0.0), (0.13, 0.034), (0.123, 0.034), (0.117, 0.004), (0.0, 0.004)], seg(18, 6),
            "steel", T(tx, ty, 0) @ Matrix.Diagonal((1.0, 0.62, 1.0, 1.0)), WHITE)
    for k in range(6):
        y, z = (ty - 0.052 + k * 0.026, 0.004) if k < 5 else (ty - 0.013, 0.004 + 2 * SAUSAGE_R - 0.004)
        scenery_sausage(m, T(tx + rng.uniform(-0.006, 0.006), y, z, rz=rng.uniform(-0.06, 0.06)), L=0.132, bend=0.005,
                        dark=True, seed=20 + k)
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
    bx, by = X(0.4), 0.075
    # between the warming tray and the rolls: a steel tray of raw Bratwurst waiting for the grill (scenery)
    rx0, rx1 = tx + 0.14, bx - 0.18
    if rx1 - rx0 > 0.3:
        rxm = (rx0 + rx1) / 2
        Mt = T(rxm, 0.09, 0, rz=-0.04)
        m.lathe([(0.0, 0.0), (0.13, 0.0), (0.138, 0.04), (0.132, 0.04), (0.125, 0.004), (0.0, 0.004)], seg(16, 6),
                "steel", Mt @ Matrix.Diagonal((1.0, 0.64, 1.0, 1.0)), C("d0d0d0"))
        import random
        rraw = random.Random(4242)
        for k in range(8):
            y, z = (-0.052 + k * 0.026, 0.004) if k < 5 else (-0.039 + (k - 5) * 0.026, 0.004 + 2 * SAUSAGE_R - 0.004)
            dx, jr = rraw.uniform(-0.008, 0.008), rraw.uniform(-0.06, 0.06)
            scenery_sausage(m, Mt @ T(dx, y, z, rz=jr), L=0.13, bend=0.005, seed=40 + k, raw=True)
    # the Marktblatt pad in front of the raw tray (act_writing_paper with write_writing_paper, unchanged)
    marktblatt(s, tx + 0.17, X(0.4) - 0.175)
    # round 10: the paper plate at the counter front between the Marktblatt and the board
    paper_plate(s, X(0.4) - 0.04, -0.148)
    # basket of rolls (scenery), set back behind the plate, stacked two deep
    G.crate(m, T(bx, by, 0), 0.34, 0.26, 0.07, C("b48c5c"), slats=2)
    m.box((0.3, 0.22, 0.004), T(bx, by, 0.014), "towel", WHITE, faces={"pz": "towel"}, skip=("nz",))
    for k in range(14):
        layer, j = divmod(k, 8)
        row, col = divmod(j, 4)
        if layer:
            row, col = divmod(j, 3)
        loc = (bx - 0.105 + col * 0.07 + (0.035 if layer else 0.0) + rng.uniform(-0.008, 0.008),
               by - 0.035 + row * 0.07 + rng.uniform(-0.008, 0.008), 0.016 + 0.028 * layer)
        G.roll(m, T(*loc, rz=math.pi / 2 + rng.uniform(-0.3, 0.3)), L=0.105, W=0.068, H=0.03)
    # round 10: the two-step board with one of each kind, at the counter front where the camera sees it
    plate_board(m)
    wurst_items(s)
    # mustard (salt-glazed stoneware) and ketchup pots with wooden spatulas, behind the board
    mustard_pot(m, T(X(0.7), 0.13, 0), C("8a9aa8"), C("c8961a"))
    mustard_pot(m, T(X(0.82), 0.14, 0), C("f0ece2"), C("8a0e0a"))
    for x, a in ((X(0.7), 0.3), (X(0.82), -0.4)):
        m.box((0.012, 0.004, 0.16), T(x + 0.02, 0.13, 0.1, rx=0.3, rz=a), vlib.RW("wood"), C("c8a070"))
    # a tin cup of wooden forks
    fy = 0.035
    m.lathe([(0.0, 0.0), (0.035, 0.0), (0.036, 0.1), (0.033, 0.1), (0.032, 0.006), (0.0, 0.006)], seg(12, 6), "steel",
            T(X(0.72), fy, 0), C("c8c8c8"))
    for k in range(9 if not vlib.lite() else 3):
        a = TWO_PI * k / 9
        m.box((0.006, 0.002, 0.09), T(X(0.72) + 0.015 * math.cos(a), fy + 0.015 * math.sin(a), 0.08,
                                      rx=0.15 * math.sin(a), ry=-0.15 * math.cos(a)), vlib.RW("wood"), C("d8b890"))
    # stack of nested paper trays behind the board
    for k in range(6 if not vlib.lite() else 2):
        G.paper_tray(m, T(X(1.12), 0.12, k * 0.0055, rz=drng.uniform(-0.05, 0.05)), 0.22, 0.1, 0.03)
    # round 10: the three squeeze bottles and the curry shaker right of the board, at the front
    sx0 = BOARD_X + BOARD_W / 2 + 0.07
    for k, key in enumerate(("senf", "ketchup", "curry")):
        sauce_bottle(s, key, sx0 + k * 0.078, -0.19 + (0.018 if k == 1 else 0.0), rz=rng.uniform(-0.15, 0.15))
    curry_shaker(s, sx0 + 3 * 0.078 - 0.005, -0.2)
    # a napkin dispenser, a tip jar and the price sign
    m.box((0.1, 0.07, 0.11), T(X(1.4), 0.11, 0.055), "steel", WHITE, skip=("nz",))
    m.box((0.09, 0.06, 0.012), T(X(1.4), 0.11, 0.116), "paper", C("f6f4ee"), skip=("nz",))
    tjx = sx0 + 3 * 0.078 + 0.09
    m.lathe([(0.0, 0.0), (0.04, 0.0), (0.042, 0.004), (0.042, 0.1), (0.045, 0.108), (0.038, 0.11)], seg(12, 6),
            "sw_vgloss", T(tjx, -0.08, 0), C("dfe8e4"), "glass")
    for k in range(5 if not vlib.lite() else 2):
        m.cyl(0.011, 0.011, 0.002, 10, "brass" if k % 2 else "sw_metal", T(tjx + drng.uniform(-0.02, 0.02),
              -0.08 + drng.uniform(-0.02, 0.02), 0.004 + k * 0.0022, rx=drng.uniform(-0.2, 0.2)), C("d8c8a8"))
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
                               # round 6: the Marktblatt pad in front, the warming tray and the grill behind
                               hero=((-0.1, -0.64, 0.4), (-0.26, -0.03, 0.05), 30),
                               preview_text=lambda: {"write_writing_paper": [
                                   ("Off the grill", 0.13, "garamond", "2a1810"),
                                   ("This is where short essays on research, music and ideas will go. Nothing is "
                                    "off the grill yet.", 0.065, "garamond", "2a1810")]},
                               in_stall="stall_bratwurst.glb",
                               # the coals' own glow does the work; a small ember light just over the bed lights the grate from below
                               stall_lights=(("env_ember", 'POINT', (-0.9, 0.0, 0.2), 6, (1.0, 0.36, 0.08), 0.15),),
                               stall_dim={"in_stall_grill": 0.2},
                               stall_cams={"in_stall": ((-0.1, -2.5, 0.75), (-0.15, 0.1, 0.35), 26),
                                           "in_stall_grill": ((-0.55, -1.05, 0.42), (-0.88, 0.05, 0.32), 32)}),
}
