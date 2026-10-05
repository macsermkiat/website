"""Round 9 (ADR 0004 revision, Mac 2026-10-05): the ornament shop's goods, prop_schmuck_<group>.glb (+ lite), at
the slots of the carpenter's stall_schmuck.glb (blender/stalls/schmuck_slots.json).

    "Ornament shop should have more sparkle decoration and goods. No need to be interactive in everything,
     but the one that interactive must be wow. not slop."

Only three things are interactive (BUILD.md, ornament shop round 9):
    act_orn_harmonica_0..11   prop_schmuck_harmonica, slot_harmonica_rail: twelve glass baubles in one row,
                              graded in size like the bowls of a glass harmonica (largest, lowest note, on the
                              left), mercury silver and champagne alternating with clear glass orbs that hold a
                              small gold core. Each node's origin is its ribbon's knot under the rail.
    act_orn_mirrorball        prop_schmuck_mirrorball, slot_mirrorball: one 18 cm mercury-glass ball, origin at
                              its knot, with cam_dive / cam_dive_target empties in front of it (set root, so the
                              camera does not swing with the ball).
    act_orn_schwibbogen       on the counter, with its seven act_orn_candle_<n> flames (origin at each wick).
Everything else is decoration: plain names, no items.json entry. The smoker keeps fx_smoke_1 at its mouth; the
pickle hides among the teal baubles on the inner rail.

Sparkle, in three tiers with dark wood left between the clusters:
    hero     the harmonica row, the mirror ball, the turning Erzgebirge candle pyramid (prop_schmuck_pyramid at
             slot_pyramid; its turning part is rot_pyramid; flames are the emissive `flame` material)
    medium   mercury-glass (metallic, roughness 0.05) and high-gloss baubles in silver, gold, copper and deep
             teal in five sizes, twisted glass icicles, glass pine cones, three Lametta swags (tinsel_0..2:
             two crinkled foil strips twisted round each other with a fringe of kinked loose strands; the tree's
             are kinked strands), glass bead garlands sagging across the front rail and the back
             wall, four Rauschgoldengel (crinkled vendor_foil) on plinths on the top shelf and a large one on the
             display tree, warm fairy lights in loops under the shelf lips
    subtle   four snow globes, spun-glass birds with fine tails, three lit Herrnhut stars at different heights
Repeated baubles are instanced: one mesh per size and colour, placed as inst_* copies that instance.mjs folds
into EXT_mesh_gpu_instancing nodes (vlib.PropSet.proto / inst).

Slots the carpenter has not yet published fall back to the stand-ins in STANDIN (stall frame, Blender axes);
props.json carries them as "standin_position" so the engine can place the sets until the hut has the empties.
"""
import contextlib
import json
import math
import os
import random

from mathutils import Matrix, Vector

import vlib
from vlib import C, T, WHITE, seg
import set_decofill as F
from set_deco import nutcracker, price_tag, star_poly

TWO_PI = 2 * math.pi
MK, MG = "market", "market_glaze"
STALL = "deco-schmuck"
SLOTS = json.load(open(os.path.join(vlib.REPO, "blender", "stalls", "schmuck_slots.json")))["slots"]
RAIL_R = 0.011
KNOT_Z = -(RAIL_R + 0.008)          # the ribbon's knot just under the brass rail (clear of it)

# Stand-ins (stall frame) for the round 9 slots until stall_schmuck.glb carries them. The harmonica hangs from the
# front rail over the counter (BUILD.md: "in one row on the front rail"), so its stand-in is slot_rail_1; the
# mirror ball hangs from the middle of the rail over the glass case; the pyramid stands right of centre on the
# counter (0.40 m right of slot_counter, 0.06 m back).
_r1, _r3, _ct = SLOTS["slot_rail_1"], SLOTS["slot_rail_3"], SLOTS["slot_counter"]["position"]
STANDIN = {
    "slot_harmonica_rail": {"position": list(_r1["position"]), "length": _r1["length"], "rail_radius": RAIL_R,
                            "clear_drop": _r1["clear_drop"],
                            "about": "stand-in: the front rail (slot_rail_1); the row runs along +X from here"},
    "slot_mirrorball": {"position": [round(_r3["position"][0] + _r3["length"] / 2, 3), _r3["position"][1],
                                     _r3["position"][2]],
                        "about": "stand-in: the hanging point at the middle of the rail over the glass case"},
    "slot_pyramid": {"position": [round(_ct[0] + 0.40, 3), round(_ct[1] + 0.06, 3), _ct[2]],
                     "about": "stand-in: on the counter top, 0.40 m right of slot_counter and 0.06 m back"},
}


def slot(name):
    return SLOTS.get(name) or STANDIN[name]


def lv(full, lite):
    return lite if vlib.lite() else full


# ------------------------------------------------------------------ palette
MERC = {"silver": C("eef0f2"), "gold": C("f2cf86"), "copper": C("e9a27c"), "teal": C("3b9aa2"),
        "champagne": C("ece0c4")}
GLOSS = {"teal": C("0e5560"), "ivory": C("efe7d6"), "copper": C("8a3a22")}
CAP = C("e2c27e")
SIZES = {"xs": 0.022, "s": 0.028, "m": 0.036, "l": 0.045, "xl": 0.055}
SEGS = {"xs": ((6, 4), (5, 3)), "s": ((8, 5), (6, 4)), "m": ((8, 6), (6, 4)), "l": ((10, 7), (7, 5)),
        "xl": ((12, 8), (8, 5))}


def bauble_key(finish, colour, size):
    return f"{finish}_{colour}_{size}"


def bauble_proto(s, finish, colour, size):
    """A bauble with its gold cap as an instanced piece; origin at the top of the cap (the hanging point), the
    ball below it along -Z. finish: merc (mercury glass), gloss (lacquered), clear (clear glass, gold core)."""
    key = bauble_key(finish, colour, size)
    r = SIZES[size]
    (n, rings), (nl, rl) = SEGS[size]

    def build(m):
        nn, rr = lv(n, nl), lv(rings, rl)
        cz = -r * 0.28 - r
        if finish == "merc":
            m.sphere(r, nn, rr, "sw_satin", T(0, 0, cz), MERC[colour], "mercury")
        elif finish == "gloss":
            m.sphere(r, nn, rr, "sw_satin", T(0, 0, cz), GLOSS[colour], "gloss")
        else:
            m.sphere(r, nn, rr, "sw_satin", T(0, 0, cz), C("f4f0e6"), "glass")
            m.sphere(r * 0.42, lv(8, 6), lv(5, 4), "sw_satin", T(0, 0, cz), MERC["gold"], "mercury")
        m.cyl(r * 0.3, r * 0.26, r * 0.34, lv(6, 4), "sw_satin", T(0, 0, -r * 0.34), CAP, "mercury", caps=False)
    s.proto(key, build)
    return key, r


def place_bauble(s, finish, colour, size, centre, rx=0.0, ry=0.0, rz=0.0):
    """An instanced bauble whose ball centre is at `centre`, the cap turned by (rx, ry, rz) from straight up."""
    key, r = bauble_proto(s, finish, colour, size)
    s.inst(key, T(*centre, rx=rx, ry=ry, rz=rz) @ T(0, 0, r * 1.28))
    return r


def hang_bauble(s, m, knot, drop, finish, colour, size, ribbon_col=C("d8b048"), sway=0.0):
    """A bauble hanging `drop` below `knot` on a satin ribbon (ribbon in the static mesh `m`)."""
    x, y, z = knot
    key, r = bauble_proto(s, finish, colour, size)
    top = Vector((x + sway, y, z - drop))
    m.tube([(x, y, z - 0.004), tuple(top)], 0.0010, 3, "sw_satin", None, ribbon_col)
    s.inst(key, T(top.x, top.y, top.z, rz=random.Random(hash((x, y, z))).uniform(0, TWO_PI)))
    return top, r


def ribbon(m, top, drop, col=C("d8b048"), r=0.0011, knot=True):
    x, y, z = top
    m.tube([(x, y, z - 0.004), (x, y, z - drop)], r, 3, "sw_satin", None, col)
    if knot:
        m.box((0.007, 0.012, 0.005), T(x, y, z + 0.002), "sw_satin", col, skip=("nz",))
    return Vector((x, y, z - drop))


# ------------------------------------------------------------------ small helpers
@contextlib.contextmanager
def plain(s, name, origin, parent=None):
    """A decoration node with its own name (no act_, no items.json entry): geometry built in set coordinates
    inside the `with` lands in the node, its origin at `origin` (set frame; relative to the parent's origin
    when a parent node is given)."""
    po = (0.0, 0.0, 0.0)
    if parent:
        po = next(loc for _, nm, loc, _ in s.nodes if nm == parent)
    m = s.node(name, tuple(o - p for o, p in zip(origin, po)), parent=parent)
    yield m
    ox, oy, oz = origin
    m.V[:] = [(x - ox, y - oy, z - oz) for x, y, z in m.V]


def sag(a, b, depth, n):
    """Points on a hanging curve from a to b sagging `depth` at the middle (a parabola is close enough)."""
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / n) - Vector((0, 0, depth * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]


def along(pts, step, start=0.0):
    """Stations every `step` metres along a polyline: (point, unit tangent)."""
    out, carry = [], start
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a
        L = d.length
        t = d / L
        s_ = carry
        while s_ < L:
            out.append((a + t * s_, t))
            s_ += step
        carry = s_ - L
    return out


def frame(t):
    up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    n1 = t.cross(up).normalized()
    return n1, t.cross(n1).normalized()


def beads(m, pts, step=0.027, r=0.0064, cols=("gold", "clear")):
    """A glass bead garland along a polyline: faceted beads (octahedra, 8 triangles) alternating mercury gold
    and clear glass. Lite keeps every second bead (larger)."""
    st = along(pts, step * lv(1, 2))
    rr = r * lv(1.0, 1.2)
    for i, (p, t) in enumerate(st):
        n1, n2 = frame(t)
        a = 0.7 * i
        e1 = (n1 * math.cos(a) + n2 * math.sin(a)) * rr
        e2 = t.cross(e1.normalized()) * rr
        ax = t * rr * 1.15
        V = [p + e1, p + e2, p - e1, p - e2, p + ax, p - ax]
        Fc = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)]
        c = cols[i % len(cols)]
        mat, col = ("glass", C("f6f2ea")) if c == "clear" else ("mercury", MERC[c])
        m.add([tuple(v) for v in V], Fc, [[(0, 0)] * 3] * 8, None, col, mat, False)


def tinsel(m, pts, col, seed, step=0.012, ribbons=2, width=0.022, pitch=0.075, fringe=0.017, drip=(0.04, 0.11),
           fw=0.0022):
    """A Lametta swag (round 9 pass 2: denser, twisted, crinkled). Two strips of metal foil twisted round each
    other along polyline `pts` (each strip's width turns about the swag's line once every `pitch` metres, the two
    a quarter turn apart, so the section is a four-bladed spiral) and crinkled: every station kinks the strip by
    a few tens of degrees and nudges it off the line, so neighbouring facets face different ways and the foil
    glints in flecks instead of reading as one straw. Under it hangs a fringe of loose Lametta strands every
    `fringe` metres, each kinked twice and twisted between its three facets. All double-sided `tinsel`.
    Lite: one strip at twice the step; the fringe is drawn from the same seeded list in both builds and lite keeps
    every second strand plus the ones that set the bounds (full / lite bounds parity)."""
    lite = vlib.lite()
    # ---- twisted crinkled strips
    st = along(pts, step * lv(1, 2))
    st.append((pts[-1], (pts[-1] - pts[-2]).normalized()))
    for k in range(lv(ribbons, 1)):
        rk = random.Random(seed * 31 + k)
        V, Fc = [], []
        ph = math.pi / 2 * k
        for i, (p, t) in enumerate(st):
            n1, n2 = frame(t)
            dist = i * step * lv(1, 2)
            th = ph + TWO_PI * dist / pitch + (0.7 if i % 2 else -0.7) * rk.uniform(0.5, 1.0)
            wd = n1 * math.cos(th) + n2 * math.sin(th)
            off = (n1 * math.cos(th + 1.7) + n2 * math.sin(th + 1.7)) * rk.uniform(0.0, 0.003)
            half = width / 2 * rk.uniform(0.75, 1.0)
            c = p + off
            V += [tuple(c - wd * half), tuple(c + wd * half)]
            if i:
                o = 2 * i
                Fc.append((o - 2, o - 1, o + 1, o))
        m.add(V, Fc, [[(0, 0)] * 4] * len(Fc), None, vlib.jit(col, 0.08), "tinsel", False)
    # ---- the fringe: loose strands hanging under the swag, each kinked twice and twisted between its three
    # facets, so no strand catches the light along its whole length (pass 1's read as straws)
    rnd = random.Random(seed)
    strands = []
    for i, (p, t) in enumerate(along(pts, fringe, fringe / 2)):
        L = rnd.uniform(*drip) * (1.0 if i % 3 else 0.6)
        lean = Vector((rnd.uniform(-0.18, 0.18), rnd.uniform(-0.12, 0.12), -1)).normalized()
        a0 = rnd.uniform(0, TWO_PI)
        es = [Vector((math.cos(a0 + 1.05 * j), math.sin(a0 + 1.05 * j), 0)) * (fw / 2 * (1.0 - 0.1 * j)) for j in range(4)]
        k1 = Vector((rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008), 0))
        k2 = Vector((rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008), 0))
        cs = [p, p + lean * (L * 0.33) + k1, p + lean * (L * 0.67) + k2, p + lean * L + (k1 + k2) * 0.5]
        f = rnd.uniform(0.7, 1.0)
        V = []
        for c, e in zip(cs, es):
            V += [c - e, c + e]
        strands.append((V, vlib.jit(tuple(c * f for c in col), 0.12)))
    keep = set(range(0, len(strands), 2)) if lite else set(range(len(strands)))
    for ax in range(3):
        keep.add(min(range(len(strands)), key=lambda j: min(v[ax] for v in strands[j][0])))
        keep.add(max(range(len(strands)), key=lambda j: max(v[ax] for v in strands[j][0])))
    for j in sorted(keep):
        q, c = strands[j]
        m.add([tuple(v) for v in q], [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6)], [[(0, 0)] * 4] * 3, None, c,
              "tinsel", False)


def icicle(m, top, L=0.13, mat="mercury", col=None):
    """A twisted glass icicle: a three-fluted star section turning a half turn down its length, a gold cap."""
    col = col or (MERC["silver"] if mat == "mercury" else C("eef4f6"))
    rings, pts_n = lv(6, 4), 6
    R0 = 0.0085
    out = []
    for i in range(rings + 1):
        f = i / rings
        z = top[2] - 0.006 - L * f
        rad = R0 * (1 - f) ** 0.9 + 0.0004
        tw = math.pi * f
        out.append([(top[0] + rad * (1.0 if j % 2 == 0 else 0.45) * math.cos(tw + TWO_PI * j / pts_n),
                     top[1] + rad * (1.0 if j % 2 == 0 else 0.45) * math.sin(tw + TWO_PI * j / pts_n), z)
                    for j in range(pts_n)])
    m.loft(out, "sw_satin", None, col, mat, closed=True, smooth=False)
    m.cyl(0.0055, 0.0045, 0.007, 6, "sw_satin", T(top[0], top[1], top[2] - 0.007), CAP, "mercury", caps=False)


def pinecone(m, top, mat="mercury", col=None):
    """A blown-glass pine cone: a scalloped spindle (alternating rings of scales), gold or copper mercury glass."""
    col = col or MERC["gold"]
    n = lv(7, 5)
    prof = [(0.007, 0.0), (0.019, 0.012), (0.016, 0.02), (0.023, 0.032), (0.019, 0.042), (0.021, 0.054),
            (0.015, 0.064), (0.013, 0.074), (0.0, 0.088)]
    if vlib.lite():
        prof = [prof[0], prof[3], prof[5], prof[7], prof[8]]
    m.lathe(prof, n, "sw_satin", T(top[0], top[1], top[2] - 0.006, rx=math.pi), col, mat, v_by="z")
    m.cyl(0.0065, 0.0055, 0.007, 6, "sw_satin", T(top[0], top[1], top[2] - 0.007), CAP, "mercury", caps=False)


def pinecone_lying(m, foot, rz, col):
    """A glass pine cone lying on its side on a shelf (`foot`: where it touches the board)."""
    n = lv(7, 5)
    prof = [(0.007, 0.0), (0.019, 0.012), (0.016, 0.02), (0.023, 0.032), (0.019, 0.042), (0.021, 0.054),
            (0.015, 0.064), (0.013, 0.074), (0.0, 0.088)]
    if vlib.lite():
        prof = [prof[0], prof[3], prof[5], prof[7], prof[8]]
    M = T(foot[0], foot[1], foot[2] + 0.021, rz=rz) @ T(-0.044, 0, 0, ry=math.pi / 2)
    m.lathe(prof, n, "sw_satin", M, col, "mercury", v_by="z")


def pickle(m, top):
    """The Weihnachtsgurke: a warty green glass gherkin hanging nose down, slightly bent (decoration)."""
    n = lv(8, 6)
    L, r = 0.11, 0.017
    prof = [(0.004, 0.0), (r * 0.8, 0.012), (r, 0.035), (r * 1.05, 0.06), (r * 0.95, 0.085), (r * 0.6, 0.104), (0.0, L)]
    if vlib.lite():
        prof = [prof[0], prof[2], prof[4], prof[6]]
    m.lathe(prof, n, "pickle", T(top.x, top.y, top.z - r * 0.3, rx=math.pi, ry=0.12), WHITE, MG, v_by="z")
    m.cyl(r * 0.42, r * 0.36, r * 0.45, 6, "sw_satin", T(top.x, top.y, top.z - r * 0.45), CAP, "mercury", caps=False)


def bird(m, perch, facing=0.0, body=C("f2f4f6"), wing=C("d8b048")):
    """A clip-on spun-glass bird: silvered body, painted wing, and a long tail of spun-glass fibres (a fan of
    fine strands, double-sided). `perch` is the clip's foot."""
    n = lv(8, 6)
    x, y, z = perch
    R = T(x, y, z, rz=facing)
    m.box((0.008, 0.008, 0.016), R @ T(0, 0, 0.008), "sw_metal", C("d8c080"))
    M = R @ T(0, 0, 0.026, ry=math.pi / 2 + 0.12)
    m.lathe([(0.0, -0.04), (0.011, -0.027), (0.016, -0.006), (0.015, 0.012), (0.009, 0.026), (0.0, 0.034)], n,
            "sw_satin", M, body, "mercury", v_by="z")
    m.lathe([(0.0028, 0.034), (0.0, 0.044)], 4, "sw_satin", M, C("e0a030"), "gloss")
    for sx in (-1, 1):
        m.add([tuple(R @ Vector(v)) for v in ((0.012, sx * 0.012, 0.03), (-0.016, sx * 0.019, 0.034), (-0.004, sx * 0.016, 0.024))],
              [(0, 1, 2), (0, 2, 1)], [[(0, 0)] * 3] * 2, None, wing, "mercury", False)
    k = lv(9, 4)
    for i in range(k):
        a = (i / (k - 1) - 0.5) * 0.9
        L = 0.075 + 0.02 * math.cos(a * 3)
        base = R @ Vector((-0.036, 0, 0.026))
        tip = R @ Vector((-0.036 - L * math.cos(a), L * math.sin(a), 0.026 + 0.022 + 0.006 * (i % 2)))
        e = (R.to_3x3() @ Vector((0, 0.0012, 0)))
        m.add([tuple(base - e), tuple(base + e), tuple(tip + e * 0.3), tuple(tip - e * 0.3)], [(0, 1, 2, 3), (3, 2, 1, 0)],
              [[(0, 0)] * 4] * 2, None, C("f8faff"), "glass", False)


def herrnhut(m, c, R=0.12, region="herrnhut", col=WHITE):
    """A 26-point Herrnhut star (18 square-based and 8 triangular points) round a warm bulb_warm core."""
    dirs = []
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                if (x, y, z) == (0, 0, 0):
                    continue
                k = abs(x) + abs(y) + abs(z)
                dirs.append((Vector((x, y, z)).normalized(), 4 if k <= 2 else 3))
    base_r = R * 0.36
    reg = vlib.R(region)
    for d, sides in dirs:
        L = R if sides == 4 else R * 0.9
        q = d.to_track_quat('Z', 'Y')
        M = T(*c) @ q.to_matrix().to_4x4() @ T(0, 0, base_r * 0.9)
        b = base_r * (0.62 if sides == 4 else 0.5)
        pts = [(b * math.cos(TWO_PI * j / sides + math.pi / sides), b * math.sin(TWO_PI * j / sides + math.pi / sides), 0.0)
               for j in range(sides)]
        verts = pts + [(0.0, 0.0, L - base_r * 0.9)]
        faces = [(j, (j + 1) % sides, sides) for j in range(sides)]
        m.add(verts, faces, [[reg.uv(0, 0), reg.uv(1, 0), reg.uv(0.5, 1)] for _ in faces], M, col, MK, False)
    m.sphere(base_r * 1.15, lv(8, 6), lv(5, 4), "sw_satin", T(*c), WHITE, "bulb_warm")


def hang_herrnhut(m, knot, drop, R, region="herrnhut", col=WHITE):
    top = ribbon(m, knot, drop, C("e8e4dc"), 0.0016)
    m.cyl(0.004, 0.004, 0.04, 5, "sw_matte", T(top.x, top.y, top.z - 0.04), C("f2ead8"), caps=False)
    herrnhut(m, (top.x, top.y, top.z - 0.04 - R), R, region, col)


def rauschgold(m, M, s=1.0):
    """A Rauschgoldengel (Nuremberg gold-foil angel), about 22 cm at s = 1, origin at the hem's centre, facing
    -Y: a pleated gold-foil skirt, foil bodice and sleeves, a wax face with golden hair, a zigzag crown and two
    large pleated foil wings fanned behind."""
    S = M @ Matrix.Diagonal((s, s, s, 1))
    gold, pale = C("e8c066"), C("f4dc96")
    P = lv(9, 6)
    rings = []
    for z, r in ((0.0, 0.058), (0.07, 0.042), (0.13, 0.02)):
        rings.append([((r * (1.0 if j % 2 == 0 else 0.84)) * math.cos(math.pi * j / P),
                       (r * (1.0 if j % 2 == 0 else 0.84)) * math.sin(math.pi * j / P), z) for j in range(2 * P)])
    m.loft(rings, "sw_metal", S, gold, "foil", closed=True, smooth=False)
    m.lathe([(0.02, 0.13), (0.015, 0.155), (0.009, 0.165)], lv(6, 5), "sw_metal", S, pale, "foil")
    m.sphere(0.017, lv(6, 5), lv(4, 3), "sw_satin", S @ T(0, 0, 0.183), C("f4dcc6"), "glaze")
    m.sphere(0.019, lv(5, 4), 3, "sw_metal", S @ T(0, 0.006, 0.188), C("d8a848"), "foil", scale=(1.0, 0.9, 0.95))
    cr = 10
    band = [(0.012 * math.cos(TWO_PI * j / cr), 0.012 * math.sin(TWO_PI * j / cr)) for j in range(cr)]
    for j in range(cr):
        a, b = band[j], band[(j + 1) % cr]
        z0 = 0.2
        ztip = z0 + (0.014 if j % 2 == 0 else 0.006)
        m.add([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z0 + 0.008), (a[0], a[1], ztip)], [(0, 1, 2, 3)],
              [[(0, 0)] * 4], S, gold, "foil", False)
    for sx in (-1, 1):
        m.tube([(sx * 0.016, 0.0, 0.15), (sx * 0.02, -0.012, 0.12), (sx * 0.006, -0.026, 0.11)], 0.0055, 4, "sw_metal",
               S, pale, "foil")
        k = lv(6, 3)
        hinge = Vector((sx * 0.006, 0.014, 0.15))
        fan = [hinge]
        for i in range(k + 1):
            a = math.radians(5 + 95 * i / k)
            L = 0.105 * (1 - 0.25 * (i / k - 0.6) ** 2)
            fan.append(Vector((sx * L * math.cos(a) * 0.95, 0.018 + 0.012 * (i % 2), 0.15 + L * math.sin(a) * 0.9 - 0.03)))
        faces = [(0, i, i + 1) if sx > 0 else (0, i + 1, i) for i in range(1, k + 1)]
        m.add([tuple(v) for v in fan], faces, [[(0, 0)] * 3] * len(faces), S, gold, "foil", False)
    m.cyl(0.0012, 0.0012, 0.05, 4, "sw_metal", S @ T(0.0, -0.03, 0.09, rx=0.3), pale)


def snow_globe(m, M, scene=0, s=1.0):
    """A snow globe, about 12 cm at s = 1: a turned walnut base, a clear glass ball, a snowy ground with a fir and
    a little half-timbered house (or a church), flakes floating in the water."""
    S = M @ Matrix.Diagonal((s, s, s, 1))
    m.lathe([(0.05, 0.0), (0.052, 0.008), (0.046, 0.02), (0.04, 0.034), (0.034, 0.036)], lv(9, 6), vlib.RW("wood"),
            S, C("4a2a18"), cap1=True)
    m.cyl(0.044, 0.044, 0.004, lv(9, 6), "sw_metal", S @ T(0, 0, 0.012), CAP, caps=False)
    c = 0.036 + 0.042
    m.sphere(0.046, lv(10, 8), lv(6, 5), "sw_satin", S @ T(0, 0, c), C("f6f6f2"), "glass")
    m.disc(0.036, lv(10, 6), "sw_matte", S @ T(0, 0, 0.042), C("f4f6f8"))
    m.cyl(0.004, 0.003, 0.012, 4, vlib.RW("wood"), S @ T(-0.014, 0.008, 0.042), C("4a3020"), caps=False)
    m.lathe([(0.016, 0.0), (0.0, 0.046)], lv(7, 5), "sw_satin", S @ T(-0.014, 0.008, 0.052), C("1f4a30"), "glaze")
    if scene == 0:
        m.box((0.022, 0.016, 0.016), S @ T(0.012, -0.004, 0.05), "sw_satin", C("efe2c8"))
        m.extrude([(-0.013, 0.0), (0.013, 0.0), (0.0, 0.012)], 0.018, S @ T(0.012, 0.005, 0.058, rx=math.pi / 2),
                  "sw_satin", None, C("8a2a1a"))
        m.box((0.006, 0.001, 0.006), S @ T(0.012, -0.0125, 0.05), "sw_satin", C("f2b040"), "bulb_warm")
    else:
        m.box((0.014, 0.014, 0.02), S @ T(0.012, 0.0, 0.052), "sw_satin", C("f2ead8"))
        m.lathe([(0.0085, 0.0), (0.0, 0.022)], 4, "sw_satin", S @ T(0.012, 0.0, 0.062), C("5a2a1a"))
    rnd = random.Random(31 + scene)
    for i in range(lv(10, 5)):
        a, rr, z = rnd.uniform(0, TWO_PI), 0.033 * math.sqrt(rnd.random()), rnd.uniform(0.05, 0.11)
        p = (rr * math.cos(a), rr * math.sin(a), z)
        f = 0.0016
        m.add([(p[0] - f, p[1], p[2] - f), (p[0] + f, p[1], p[2] - f), (p[0], p[1], p[2] + f)], [(0, 1, 2), (0, 2, 1)],
              [[(0, 0)] * 3] * 2, S @ T(rz=a), C("ffffff"), "atlas", False)


# ------------------------------------------------------------------ figures (decoration)
def smoker(m, M):
    """A Räuchermännchen (incense smoker), about 23 cm, in a green coat and a fur hat."""
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
    m.tube([(0.0, -0.027, 0.165), (0.012, -0.05, 0.14), (0.018, -0.06, 0.11)], 0.003, 4, vlib.RW("wood"), M,
           C("3a2414"))
    m.cyl(0.009, 0.008, 0.018, 6, vlib.RW("wood"), M @ T(0.018, -0.06, 0.1), C("3a2414"))


def F_area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def schwibbogen(s, m, M, origin, n_candles=7):
    """A Schwibbogen: a fretwork candle arch, 46 cm, dark-stained, with firs, a church and two miners cut out,
    and seven candles on the arch, each flame an act_orn_candle_<n> node (origin at the wick)."""
    Wd, H, band = 0.46, 0.27, 0.03
    dark = C("4a2e1a")
    m.box((Wd + 0.04, 0.07, 0.022), M @ T(0, 0, 0.011), vlib.RW("wood"), C("5a3a22"), skip=("nz",))
    nseg = lv(14, 8)
    outer = [(Wd / 2 * math.cos(math.pi * i / nseg), 0.022 + (H - 0.03) * math.sin(math.pi * i / nseg)) for i in range(nseg + 1)]
    inner = [((Wd / 2 - band) * math.cos(math.pi * i / nseg), 0.022 + (H - 0.03 - band) * math.sin(math.pi * i / nseg))
             for i in range(nseg + 1)]
    poly = outer + inner[::-1]
    m.extrude(poly[::-1] if F_area(poly) < 0 else poly, 0.012, M @ T(0, 0.006, 0, rx=math.pi / 2), vlib.RW("wood"),
              vlib.RW("wood"), dark, back=True)
    scene = [
        [(-0.17, 0.022), (-0.11, 0.022), (-0.14, 0.13)],
        [(-0.19, 0.022), (-0.15, 0.022), (-0.17, 0.09)],
        [(0.11, 0.022), (0.17, 0.022), (0.14, 0.12)],
        [(-0.05, 0.022), (0.05, 0.022), (0.05, 0.09), (0.0, 0.13), (-0.05, 0.09)],
        [(0.025, 0.09), (0.04, 0.09), (0.04, 0.17), (0.0325, 0.19), (0.025, 0.17)],
        [(-0.1, 0.022), (-0.075, 0.022), (-0.078, 0.08), (-0.087, 0.095), (-0.097, 0.08)],
        [(0.075, 0.022), (0.1, 0.022), (0.097, 0.08), (0.087, 0.095), (0.078, 0.08)],
    ]
    for poly2 in scene:
        p = poly2 if F_area(poly2) > 0 else poly2[::-1]
        m.extrude(p, 0.008, M @ T(0, 0.004, 0, rx=math.pi / 2), vlib.RW("wood"), vlib.RW("wood"), C("3a2414"),
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
        # the candles light from the outside in (ADR 0004 revision): order 0 for the two outer candles
        order = min(i, n_candles - 1 - i)
        s.item(name, f"Schwibbogen candle {i + 1}", "deco", pivot="the wick: the flame's foot",
               label=f"Kerze {i + 1} am Schwibbogen", action="light", order=order,
               detail="One of the seven candles on the Schwibbogen. They light from the outside in.")


def _tier(n):
    """Offset of shelf tier n (1..3) from slot_shelf_1 (schmuck_slots.json): the tiers step back and up."""
    p0, p = SLOTS["slot_shelf_1"]["position"], SLOTS[f"slot_shelf_{n}"]["position"]
    return p[0] - p0[0], p[1] - p0[1], p[2] - p0[2]


# ================================================================== hero: the glass harmonica
HARMONICA_ROW = (0.17, 0.25)      # spacing between baubles (m, stand-in only), centre line below the knot (m)


def harmonica():
    """Twelve baubles in one row (act_orn_harmonica_0..11, left to right), centred on the rail, their ball centres
    on one level line HARMONICA_ROW[1] under the knots so the row reads as an instrument; radii graded from 4.7
    to 3.3 cm (left = largest = lowest note, like the bowls of a glass harmonica). Even ones are mercury glass
    (silver and champagne in turn), odd ones clear glass with a small gold core."""
    sl = slot("slot_harmonica_rail")
    L = sl["length"]
    s = vlib.PropSet("prop_schmuck_harmonica", "slot_harmonica_rail", STALL, footprint=(L, 0.12))
    step, below = HARMONICA_ROW
    # the carpenter's twelve brass rings (hooks_x along the rail, ring bottoms hook_drop under the axis)
    xs = sl.get("hooks_x") or [L / 2 - step * 5.5 + step * i for i in range(12)]
    kz = -sl.get("hook_drop", -KNOT_Z)
    for i in range(12):
        x = xs[i]
        r = 0.047 - 0.014 * i / 11
        knot = (x, 0.0, kz)
        clear = i % 2 == 1
        tone = ("silver", "champagne")[(i // 2) % 2]
        name = f"act_orn_harmonica_{i}"
        node = s.node(name, knot)
        cz = -below                                   # ball centre, node frame
        top = cz + r * 1.28
        node.tube([(0, 0, -0.002), (0, 0, top)], 0.0011, 4, "sw_satin", None, C("e8e2d4"))
        node.box((0.007, 0.006, 0.004), T(0, 0, -0.001), "sw_satin", C("e8e2d4"), skip=("nz",))
        n, rings = lv(10, 7), lv(8, 6)
        if clear:
            node.sphere(r, n, rings, "sw_satin", T(0, 0, cz), C("f6f2e8"), "glass")
            node.sphere(r * 0.4, lv(6, 5), lv(4, 3), "sw_satin", T(0, 0, cz), MERC["gold"], "mercury")
        else:
            node.sphere(r, n, rings, "sw_satin", T(0, 0, cz), MERC[tone], "mercury")
        node.lathe([(r * 0.3, cz + r * 0.94), (r * 0.31, cz + r * 1.12), (r * 0.26, top - 0.002), (r * 0.08, top)],
                   lv(6, 5), "sw_satin", None, CAP, "mercury")
        what = "a clear glass orb with a small gold core" if clear else f"a {tone} mercury-glass bauble"
        s.item(name, f"Glass harmonica, bauble {i + 1}", "deco", label=f"Glasharmonika · Kugel {i + 1} von 12",
               action="harmonica", index=i, radius_m=round(r, 4), finish="clear" if clear else "mercury",
               pivot="hang: the ribbon's knot at the bottom of its brass ring; the bauble swings about it",
               detail=f"One of twelve baubles tuned like a glass harmonica: {what}, {round(r * 200, 1)} cm across. "
                      "Brush across the row to play the tune.")
    s.finish()
    return s


# ================================================================== hero: the mirror ball
MIRROR_R = 0.09
DIVE = 0.15        # cam_dive distance from the ball's centre (see mirrorball())
DIVE_DIR = Vector((0.34, -0.94, 0.0)).normalized()     # toward the lane, a little toward the market's centre


def mirrorball():
    """One 18 cm mercury-glass ball (act_orn_mirrorball, origin at its ribbon's knot) with a fluted crown cap.
    It hangs by a short brass wire loop straight from the hook (slot_mirrorball, the forged bracket on the left
    front post), its centre about 0.12 m below the hook. cam_dive stands DIVE from the ball's centre, level with
    it, toward the lane (DIVE_DIR: -Y and a little +X), and cam_dive_target on the centre: at the site's 42 degree
    vertical field of view a 16:9 frame's corners are 36.6 degrees off axis, and the ball (r = 9 cm) spans
    asin(0.09 / 0.15) = 36.9 degrees there, so its reflection fills the frame. cam_dive_approach, 0.7 m out on
    the same line, is where the dive can start (the carpenter's suggested framing)."""
    s = vlib.PropSet("prop_schmuck_mirrorball", "slot_mirrorball", STALL, footprint=(0.2, 0.2))
    R = MIRROR_R
    knot = (0.0, 0.0, 0.0)
    node = s.node("act_orn_mirrorball", knot)
    top = -0.012
    cz = top - 0.02 - R * 0.97
    node.torus(0.007, 0.0014, lv(10, 6), 4, "sw_satin", T(0, 0, -0.006, rx=math.pi / 2), CAP, "mercury")
    node.sphere(R, lv(24, 16), lv(16, 10), "sw_satin", T(0, 0, cz), MERC["silver"], "mercury")
    fl = lv(16, 8)
    crown = []
    for zf, rf in ((0.0, 0.29), (0.6, 0.31), (1.0, 0.22)):
        crown.append([(R * rf * (1.0 if j % 2 == 0 else 0.9) * math.cos(TWO_PI * j / fl),
                       R * rf * (1.0 if j % 2 == 0 else 0.9) * math.sin(TWO_PI * j / fl),
                       cz + R * 0.95 + (top - cz - R * 0.95) * zf) for j in range(fl)])
    node.loft(crown, "sw_satin", None, CAP, "mercury", closed=True, cap1=True, smooth=False)
    ball = (knot[0], knot[1], knot[2] + cz)
    bc = Vector(ball)
    s.empty("cam_dive", tuple(bc + DIVE_DIR * DIVE))
    s.empty("cam_dive_target", ball)
    s.empty("cam_dive_approach", tuple(bc + DIVE_DIR * 0.7))
    s.item("act_orn_mirrorball", "Mercury-glass ball", "deco", label="Spiegelkugel · 18 cm", action="dive",
           cam="cam_dive", cam_target="cam_dive_target", radius_m=R,
           pivot="hang: the top of its wire loop, on the bracket's hook; the ball's centre is "
                 f"{round(-cz, 3)} m below it",
           detail="A big mercury-glass ball, silvered inside by hand. Tap it and look into the reflection.")
    s.report_extra = {"cam_dive_distance_m": DIVE, "ball_centre_local": [round(v, 3) for v in ball]}
    s.finish()
    return s


# ================================================================== hero: the Erzgebirge pyramid
def pyramid():
    """A three-tier Erzgebirge candle pyramid, 0.55 m to the tip of its propeller, origin on the counter at the
    centre of its base. Static: the hexagonal base, six slanted posts with a top bearing ring, and six candles
    on brass cups at the posts' feet (emissive `flame`). rot_pyramid (origin on the axis; the engine spins it
    about three.js Y = Blender Z): the shaft, three tier discs with turned figures (the nativity, shepherds with
    sheep, angels) and the eight-bladed propeller on top that the candles' heat turns."""
    s = vlib.PropSet("prop_schmuck_pyramid", "slot_pyramid", STALL, footprint=(0.36, 0.36))
    m = s.static
    dark, light, red = C("4a2c1a"), C("c89a62"), C("9a2420")
    hexp = [(0.165 * math.cos(TWO_PI * j / 6 + math.pi / 6), 0.165 * math.sin(TWO_PI * j / 6 + math.pi / 6)) for j in range(6)]
    m.extrude(hexp, 0.022, T(0, 0, 0), vlib.RW("wood"), vlib.RW("wood"), dark, back=False, bevel=lv(0.004, 0.0))
    top_r, top_z = 0.07, 0.43
    for j in range(6):
        a = TWO_PI * j / 6 + math.pi / 6
        p0 = (0.145 * math.cos(a), 0.145 * math.sin(a), 0.022)
        p1 = (top_r * math.cos(a), top_r * math.sin(a), top_z)
        m.tube([p0, p1], 0.0065, lv(5, 4), vlib.RW("wood"), None, light)
        m.cyl(0.011, 0.009, 0.012, 6, "sw_metal", T(*p0), CAP, caps=False)
        # the candle on a brass cup at the post's foot, just outside it
        cx, cy = 0.13 * math.cos(a + 0.52), 0.13 * math.sin(a + 0.52)
        m.cyl(0.011, 0.0095, 0.01, 6, "sw_metal", T(cx, cy, 0.022), CAP, caps=False)
        m.cyl(0.0058, 0.0058, 0.07, lv(6, 5), vlib.RW("wax"), T(cx, cy, 0.032), C("c8302a") if j % 2 else C("f4ecdc"))
        m.lathe([(0.0, 0.0), (0.0042, 0.008), (0.0024, 0.02), (0.0, 0.031)], 5, "sw_satin", T(cx, cy, 0.104), WHITE, "flame")
    m.torus(top_r, 0.006, lv(16, 8), 4, vlib.RW("wood"), T(0, 0, top_z), light)
    for j in range(3):
        a = TWO_PI * j / 3
        m.tube([(top_r * math.cos(a), top_r * math.sin(a), top_z), (0, 0, top_z + 0.004)], 0.004, 4, vlib.RW("wood"), None, light)
    m.cyl(0.012, 0.012, 0.012, lv(8, 6), "sw_metal", T(0, 0, top_z - 0.004), CAP)
    rot = s.node("rot_pyramid", (0.0, 0.0, 0.0))
    rot.cyl(0.004, 0.004, 0.52, lv(6, 4), vlib.RW("wood"), T(0, 0, 0.024), light, caps=False)
    tiers = [(0.05, 0.105, 0.07), (0.19, 0.092, 0.058), (0.31, 0.066, 0.048)]
    rnd = random.Random(77)
    for ti, (z, r, h) in enumerate(tiers):
        rot.cyl(r, r, 0.008, lv(12, 8), vlib.RW("wood"), T(0, 0, z), red if ti == 0 else light)
        figs = [5, 6, 4][ti] if not vlib.lite() else [3, 3, 3][ti]
        for k in range(figs):
            a = TWO_PI * k / figs + 0.3 * ti
            fx, fy = r * 0.72 * math.cos(a), r * 0.72 * math.sin(a)
            Mf = T(fx, fy, z + 0.008, rz=a + math.pi / 2)
            if ti == 1 and k % 2 == 1:
                # a sheep: a woolly body and a dark head
                rot.sphere(0.013, lv(7, 5), lv(4, 3), "sw_matte", Mf @ T(0, 0, 0.016), C("f2ece0"), scale=(1.5, 1.0, 1.0))
                rot.sphere(0.006, 5, 3, "sw_matte", Mf @ T(0.021, 0, 0.022), C("2a2220"))
                continue
            coat = [C("2a4a8a"), C("8a2a22"), C("c8a050"), C("3a5a2a"), C("6a3a5a"), C("efe6d2")][(k + ti * 2) % 6]
            if ti == 2:
                coat = C("f4eee2")
            hh = h * rnd.uniform(0.9, 1.05)
            rot.lathe([(0.012, 0.0), (0.011, hh * 0.3), (0.007, hh * 0.72), (0.0, hh * 0.76)], lv(5, 4),
                      "sw_gloss", Mf, coat, "glaze")
            rot.sphere(0.0075, 4, 3, "sw_satin", Mf @ T(0, 0, hh * 0.86), C("f0c8a0"), "glaze")
            if ti == 2:
                for sx in (-1, 1):
                    rot.add([(0, 0.004, hh * 0.6), (sx * 0.02, 0.008, hh * 0.85), (sx * 0.012, 0.006, hh * 0.45)],
                            [(0, 1, 2), (0, 2, 1)], [[(0, 0)] * 3] * 2, Mf, C("d8b048"), "atlas", False)
            elif ti == 1:
                rot.cyl(0.0015, 0.0015, hh * 1.05, 3, vlib.RW("wood"), Mf @ T(0.014, 0, 0), C("6a4a2c"), caps=False)
    # the crib on the bottom tier's centre: a manger with the child
    rot.box((0.03, 0.018, 0.012), T(0, 0.0, 0.064), vlib.RW("wood"), C("8a5a34"))
    rot.sphere(0.006, 5, 3, "sw_satin", T(0, 0, 0.074), C("f2ead8"), "glaze", scale=(1.6, 1, 0.8))
    # the propeller: eight pitched blades on a hub
    hub_z = 0.53
    rot.cyl(0.016, 0.012, 0.014, lv(10, 6), vlib.RW("wood"), T(0, 0, hub_z), light)
    nb = 8
    for k in range(nb):
        a = TWO_PI * k / nb
        Mb = T(0, 0, hub_z + 0.007, rz=a) @ T(0, 0, 0, rx=math.radians(28))
        blade = [(0.016, -0.012, 0.0), (0.155, -0.024, 0.0), (0.16, 0.024, 0.0), (0.016, 0.012, 0.0)]
        rot.add(blade, [(0, 1, 2, 3), (3, 2, 1, 0)], [[(0, 0)] * 4] * 2, Mb, light if k % 2 else C("d8b48a"), "atlas", False)
    rot.lathe([(0.006, 0.0), (0.0, 0.014)], 6, "sw_metal", T(0, 0, hub_z + 0.014), CAP)
    s.finish()
    return s


# ================================================================== rails
def _anchors(slot_name, fallback):
    """The carpenter's swag anchors for a slot_tinsel_<n>, relative to the slot (its first anchor), and the sag."""
    sl = SLOTS.get(slot_name)
    if not sl:
        return fallback
    p = Vector(sl["position"])
    return [Vector(a) - p for a in sl["anchors"]], sl.get("sag", 0.08)


def swag_set(name, slot_name, n, colour, seed, fallback, label, off=(0.0, -0.035, -0.012), rosette=0.012,
             rosette_seg=(8, 5), **kw):
    """A Lametta swag tinsel_<n> hung between the carpenter's anchors (slot_tinsel_<k>), sagging as the slot says,
    with a small gilt rosette at each anchor."""
    s = vlib.PropSet(name, slot_name, STALL, footprint=(2.6, 0.1))
    anchors, sg = _anchors(slot_name, fallback)
    anchors = [a + Vector(off) for a in anchors]       # hung just in front of the beam or valance it is pinned to
    with plain(s, f"tinsel_{n}", (0.0, 0.0, 0.0)) as tm:
        for a, b in zip(anchors[:-1], anchors[1:]):
            tinsel(tm, sag(a, b, sg, 16), colour, seed + int(a.x * 10), **kw)
    for a in anchors:
        s.static.sphere(rosette, lv(rosette_seg[0], 6), lv(rosette_seg[1], 4), "sw_satin", T(a.x, a.y, a.z + 0.004), MERC["gold"], "mercury")
    s.finish()
    return s


def tinsel_canopy():
    """tinsel_0: gold Lametta under the scalloped valance across the counter bay (slot_tinsel_1)."""
    return swag_set("prop_schmuck_tinsel_1", "slot_tinsel_1", 0, MERC["gold"], 11,
                    ([Vector((0, 0, 0)), Vector((1.28, 0, 0)), Vector((2.56, 0, 0))], 0.13), "canopy",
                    step=0.015, width=0.016, pitch=0.045, fringe=0.024, drip=(0.035, 0.11))


def tinsel_beam():
    """tinsel_1: silver Lametta along the tie beam inside the canopy (slot_tinsel_3), doubled in the mirror."""
    return swag_set("prop_schmuck_tinsel_3", "slot_tinsel_3", 1, MERC["silver"], 23,
                    ([Vector((0.95 * k, 0, 0)) for k in range(5)], 0.07), "beam", off=(0.0, -0.05, -0.02),
                    rosette=0.01, rosette_seg=(6, 4), step=0.024, width=0.018, pitch=0.06, fringe=0.045,
                    drip=(0.04, 0.09))


def garland():
    """The front bead garland (slot_tinsel_2): faceted glass beads, mercury gold and clear, draped over the
    harmonica rail between its three hangers in two shallow curves above the baubles' rings, with a few longer
    loose strands hanging at the hangers."""
    s = vlib.PropSet("prop_schmuck_garland", "slot_tinsel_2", STALL, footprint=(2.2, 0.06))
    m = s.static
    anchors, sg = _anchors("slot_tinsel_2", ([Vector((1.08 * k, 0, 0)) for k in range(3)], 0.05))
    for a, b in zip(anchors[:-1], anchors[1:]):
        a2, b2 = a + Vector((0, -0.026, -0.006)), b + Vector((0, -0.026, -0.006))
        beads(m, sag(a2, b2, sg + 0.025, 18), cols=("gold", "clear", "gold", "silver"))
    for k, a in enumerate(anchors):
        tail = [a + Vector((0, -0.026, -0.014)), a + Vector((0.01 * (k - 1), -0.028, -0.08 - 0.02 * (k % 2)))]
        beads(m, tail, step=0.02, cols=("clear", "gold"))
        m.sphere(0.01, lv(8, 6), lv(5, 4), "sw_satin", T(a.x, a.y - 0.026, a.z - 0.004), MERC["gold"], "mercury")
    s.finish()
    return s


def rail_2():
    """The inner rail over the counter's back edge (slot_rail_2, 0.31 m clear drop): four clusters of mercury and
    high-gloss baubles with bare rail between them (the gaps line up with the four top-shelf angels seen from the
    close-up camera, so the angels show between the clusters), two lit Herrnhut stars at different heights (red, 22 cm, and
    yellow, 16 cm), two spun-glass birds clipped on the rail, icicles, a pine cone, and the pickle hidden among
    the teal baubles (decoration)."""
    L = SLOTS["slot_rail_2"]["length"]
    s = vlib.PropSet("prop_schmuck_rail_2", "slot_rail_2", STALL, footprint=(L, 0.12))
    m = s.static
    clusters = [
        (0.2, [("merc", "silver", "l", 0.12), ("gloss", "teal", "m", 0.2), ("icicle", 0, 0, 0.04),
                ("merc", "copper", "s", 0.17)]),
        (1.33, [("gloss", "teal", "m", 0.1), ("merc", "teal", "s", 0.19), ("pickle", 0, 0, 0.09),
                ("merc", "teal", "l", 0.14), ("gloss", "teal", "s", 0.05)]),
        (0.935, [("merc", "copper", "m", 0.08), ("pine", 0, 0, 0.13), ("merc", "silver", "xl", 0.12)]),
        (2.17, [("merc", "gold", "m", 0.17), ("icicle", 0, 0, 0.03), ("merc", "silver", "m", 0.08)]),
    ]
    for cx, items in clusters:
        n = len(items)
        for k, (kind, a, b, drop) in enumerate(items):
            x = cx + (k - (n - 1) / 2) * 0.062
            y = 0.012 * ((k % 2) * 2 - 1)
            knot = (x, y, KNOT_Z)
            if kind in ("merc", "gloss"):
                hang_bauble(s, m, knot, drop, kind, a, b, C("e8e2d4") if kind == "merc" else C("d8b048"))
            elif kind == "icicle":
                icicle(m, ribbon(m, knot, drop, C("e8e2d4")), 0.15, "glass")
            elif kind == "pine":
                pinecone(m, ribbon(m, knot, drop, C("b0282a")))
            elif kind == "pickle":
                pickle(m, ribbon(m, knot, drop, C("2a6a3a")))
    hang_herrnhut(m, (0.5, 0.0, KNOT_Z), 0.03, 0.105)
    hang_herrnhut(m, (1.72, 0.0, KNOT_Z), 0.1, 0.075, "sw_satin", C("f2c64a"))
    for x, f in ((0.36, 0.3), (1.9, math.pi - 0.3)):
        bird(m, (x, 0.0, RAIL_R + 0.001), facing=f)
    s.finish()
    return s


def rail_3():
    """The rail over the glass case (slot_rail_3) around the mirror ball: an icicle and a small mercury bauble at
    each end, and a short bead swag between."""
    L = SLOTS["slot_rail_3"]["length"]
    s = vlib.PropSet("prop_schmuck_rail_3", "slot_rail_3", STALL, footprint=(L, 0.12))
    m = s.static
    for x, col in ((0.05, "gold"), (L - 0.05, "copper")):
        icicle(m, ribbon(m, (x, 0.0, KNOT_Z), 0.03, C("e8e2d4")), 0.18)
        hang_bauble(s, m, (x + (0.06 if x < L / 2 else -0.06), 0.0, KNOT_Z), 0.13, "merc", col, "s")
    beads(m, sag((0.02, -0.024, KNOT_Z - 0.002), (L - 0.02, -0.024, KNOT_Z - 0.002), 0.05, 10), cols=("silver", "clear"))
    s.finish()
    return s


def rail_4():
    """The short drop over the tree (slot_rail_4, 0.21 m clear): a small white Herrnhut star, lit, between two
    silver icicles."""
    L = SLOTS["slot_rail_4"]["length"]
    s = vlib.PropSet("prop_schmuck_rail_4", "slot_rail_4", STALL, footprint=(L, 0.12))
    m = s.static
    hang_herrnhut(m, (L / 2, 0.0, KNOT_Z), 0.02, 0.06, "sw_satin", C("f6f2ea"))
    for x in (0.08, L - 0.08):
        icicle(m, ribbon(m, (x, 0.0, KNOT_Z), 0.02, C("e8e2d4")), 0.14)
    s.finish()
    return s


# ================================================================== counter, shelves, case, tree
def counter():
    """The counter (slot_counter): the nutcracker and the smoker (fx_smoke_1 at his mouth) at the left end, the
    Schwibbogen (act_orn_schwibbogen, the one interactive piece here) left of centre, two snow globes, a velvet
    tray of mercury baubles and a footed glass bowl heaped with them at the right, a short carton stack and two
    price tags. The pyramid is its own set (slot_pyramid, 0.12 m right of and 0.10 m behind slot_counter); its 0.34 m
    circle is left clear."""
    s = vlib.PropSet("prop_schmuck_counter", "slot_counter", STALL)
    m = s.static
    nx, ny, sc = -1.06, 0.07, 1.15
    with plain(s, "nutcracker", (nx, ny, 0.0)) as nm:
        nutcracker(nm, T(nx, ny, 0.0), C("a8181c"), C("f2ead8"), C("d8b048"), s=sc)
    sx_, sy_ = -0.84, -0.06
    with plain(s, "smoker", (sx_, sy_, 0.0)) as rm:
        smoker(rm, T(sx_, sy_, 0.0))
    s.empty("fx_smoke_1", (0.0, -0.03, 0.172), parent="smoker")
    bx, by = -0.42, 0.11
    node = s.node("act_orn_schwibbogen", (bx, by, 0.0))
    schwibbogen(s, node, T(0, 0, 0), (0.0, 0.0, 0.0))      # built in the arch node's own frame
    s.item("act_orn_schwibbogen", "Schwibbogen", "deco", pivot="base", label="Schwibbogen · 45 €", action="candles",
           candles=[f"act_orn_candle_{i}" for i in range(7)],
           detail="A Schwibbogen, the candle arch of the Erzgebirge mining towns, with firs, a church and two "
                  "miners cut in fretwork. Light it and its seven candles wake the town, from the outside in.")
    snow_globe(m, T(0.42, -0.13, 0.0, rz=0.3), 0, 1.15)
    snow_globe(m, T(-0.11, -0.18, 0.0, rz=-0.4), 1, 0.85)
    # velvet tray with eight nested mercury baubles
    tx, ty = 0.86, -0.05
    m.box((0.28, 0.25, 0.03), T(tx, ty, 0.015), "sw_matte", C("123a44"), skip=("nz",))
    m.box((0.24, 0.21, 0.002), T(tx, ty, 0.031), "sw_matte", C("0c2a32"))
    cols = ["silver", "gold", "teal", "copper"]
    for k in range(4):
        cx, cy = tx - 0.055 + (k % 2) * 0.11, ty - 0.05 + (k // 2) * 0.1
        place_bauble(s, "merc", cols[k], "m", (cx, cy, 0.032 + 0.032), rx=math.radians(70), rz=k * 0.8 + 0.4)
    # footed glass bowl with a heap of small baubles
    gx, gy = 0.56, 0.15
    m.lathe([(0.045, 0.0), (0.04, 0.006), (0.008, 0.012), (0.007, 0.06), (0.03, 0.075), (0.075, 0.11), (0.08, 0.116)],
            lv(10, 7), "sw_satin", T(gx, gy, 0), C("f4f2ec"), "glass", cap0=True)
    heap = [(0.036, 0.018, 0.112, "silver"), (-0.036, 0.022, 0.112, "copper"), (0.0, -0.036, 0.112, "teal"),
            (0.0, 0.0, 0.138, "gold")]
    for k, (hx, hy, hz, col) in enumerate(heap):
        place_bauble(s, "merc", col, "s", (gx + hx, gy + hy, hz), rx=1.2 + k, rz=k * 1.3)
    for j in range(2):
        F.carton(m, T(1.1, 0.17, j * 0.08, rz=0.05 * (j - 0.5)), 0.18, 0.13, 0.08, "bx_schmuck")
    for k, (x, y) in enumerate(((0.86, -0.22), (-0.84, -0.2))):
        price_tag(m, T(x, y + 0.01, 0), 4 + k)
    s.finish()
    return s


def bauble_stand(s, m, x, y, z, cols, h=0.26):
    """A brass bauble stand: a turned foot, a rod and three tiers of curled arms, a bauble hanging from each."""
    m.cyl(0.04, 0.034, 0.012, lv(10, 6), "sw_metal", T(x, y, z), CAP)
    m.cyl(0.0035, 0.0035, h, 4, "sw_metal", T(x, y, z + 0.012), CAP, caps=False)
    k = 0
    for ti, (zz, reach, arms) in enumerate(((0.11, 0.07, 3), (0.19, 0.05, 2))):
        for a in range(arms):
            ang = TWO_PI * a / arms + ti * 0.6
            p0 = (x, y, z + zz)
            p1 = (x + reach * math.cos(ang), y + reach * math.sin(ang), z + zz + 0.012)
            m.tube([p0, p1], 0.0018, 3, "sw_metal", None, CAP)
            col = cols[k % len(cols)]
            size = ("s", "xs", "xs")[ti]
            r = SIZES[size]
            hang_bauble(s, m, (p1[0], p1[1], p1[2] + 0.004), 0.012 + 0.01 * (a % 2), "merc", col, size, C("e8e2d4"))
            k += 1


def fairy_loops(m, x0, x1, y, z, spans, depth, bulb_step=0.07):
    """A string of warm fairy lights pinned under a shelf's front lip at `spans` + 1 points from x0 to x1, sagging
    `depth` between pins: a fine dark wire (a flat strip facing the lane) with a small faceted bulb_warm bulb every
    `bulb_step` metres, the bulbs glowing among the goods (bloom in the engine). Lite: half the bulbs."""
    pins = [Vector((x0 + (x1 - x0) * k / spans, y, z)) for k in range(spans + 1)]
    pts = []
    for a, b in zip(pins[:-1], pins[1:]):
        pts += sag(a, b, depth, lv(4, 3))[(1 if pts else 0):]
    V, Fc = [], []
    for i, p in enumerate(pts):
        V += [(p.x, p.y, p.z + 0.0009), (p.x, p.y, p.z - 0.0009)]
        if i:
            o = 2 * i
            Fc.append((o - 2, o, o + 1, o - 1))
    m.add(V, Fc, [[(0, 0)] * 4] * len(Fc), None, C("1c2418"), "atlas", False)
    r = 0.0045
    for i, (p, t) in enumerate(along(pts, bulb_step * lv(1, 2), bulb_step / 2)):
        c = p + Vector((0, -0.002, -0.0055))
        ex, ey, ez = Vector((r, 0, 0)), Vector((0, r, 0)), Vector((0, 0, r * 1.3))
        Vb = [c + ex, c + ey, c - ex, c - ey, c + ez, c - ez]
        Fb = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)]
        m.add([tuple(v) for v in Vb], Fb, [[(0, 0)] * 3] * 8, None, C("ffd89a"), "bulb_warm", False)


def shelf():
    """The three tiers behind the counter (one set at slot_shelf_1; tiers 2 and 3 by their offsets), dressed in
    dense clusters with dark wood between, so each tier reads as a band of glints against the carpenter's foxed
    mirror rather than as a few silhouettes (round 9 pass 2):
      tier 1: two open boxes of six mercury baubles with their lids leaning behind, two footed glass bowls heaped
              with six baubles each, the big snow globe
      tier 2: two spun-glass birds on a birch log, five large mercury baubles on brass rings, glass pine cones and
              two baubles lying on a velvet runner, the menu board under tier 3 at the right end
      tier 3: four Rauschgoldengel (gold-foil angels, 31 cm) raised on turned walnut plinths so they stand clear
              above the harmonica row and between the inner rail's clusters from the lane; a glass bead garland
              sags across the back-wall mirror above in three curves, so the mirror doubles it.
    Warm fairy lights hang in shallow loops under the front lips of tiers 2 and 3, glowing among the goods of the
    tier below."""
    L = SLOTS["slot_shelf_1"]["length"]
    s = vlib.PropSet("prop_schmuck_shelf", "slot_shelf_1", STALL, footprint=(L, SLOTS["slot_shelf_1"]["depth"]))
    m = s.static
    hw = L / 2 - 0.12
    # ---- tier 1
    _, y1, _ = _tier(1)
    for bx, cols in ((-hw + 0.14, ("silver", "gold", "copper", "teal", "gold", "silver")),
                     (hw - 0.14, ("teal", "silver", "gold", "silver", "copper", "gold"))):
        m.box((0.23, 0.15, 0.03), T(bx, y1 + 0.02, 0.015), "kraft", C("d8c8a8"), skip=("nz",))
        m.box((0.21, 0.13, 0.002), T(bx, y1 + 0.02, 0.031), "sw_matte", C("7a1820"))
        F.carton(m, T(bx, y1 + 0.12, 0.0, rx=-0.25), 0.23, 0.02, 0.16, "bx_schmuck")
        for k in range(6):
            cx, cy = bx - 0.068 + (k % 3) * 0.068, y1 - 0.012 + (k // 3) * 0.064
            place_bauble(s, "merc", cols[k], "s", (cx, cy, 0.032 + 0.026), rx=math.radians(80), rz=k * 1.1)
    for gx, cols in ((-0.54, ("gold", "silver", "teal", "copper", "gold", "silver")),
                     (0.6, ("silver", "copper", "gold", "teal", "silver", "gold"))):
        gy = y1 + 0.03
        m.lathe([(0.05, 0.0), (0.044, 0.006), (0.009, 0.014), (0.008, 0.07), (0.035, 0.085), (0.085, 0.125), (0.09, 0.131)],
                lv(10, 7), "sw_satin", T(gx, gy, 0), C("f4f2ec"), "glass", cap0=True)
        heap = [(0.05 * math.cos(TWO_PI * j / 5 + 0.3), 0.05 * math.sin(TWO_PI * j / 5 + 0.3), 0.124) for j in range(5)]
        heap.append((0.004, -0.006, 0.158))
        for k, (hx, hy, hz) in enumerate(heap):
            place_bauble(s, "merc" if k != 2 else "gloss", cols[k] if k != 2 else "teal", "s", (gx + hx, gy + hy, hz),
                         rx=1.0 + k, rz=k * 1.7)
    snow_globe(m, T(-0.2, y1 - 0.02, 0.0, rz=0.2), 1, 1.35)
    # ---- tier 2
    x2, y2, z2 = _tier(2)
    m.cyl(0.028, 0.03, 0.3, lv(8, 6), vlib.RW("wood"), T(-1.07, y2 - 0.04, z2 + 0.028, ry=math.pi / 2, rz=0.06), C("e8e2d6"))
    for k, x in enumerate((-1.0, -0.84)):
        bird(m, (x, y2 - 0.04 + 0.006 * k, z2 + 0.052), facing=-math.pi / 2 + 0.35 * (k - 1),
             body=(MERC["silver"], MERC["gold"], C("cfe6f0"))[k], wing=(C("d8b048"), C("b8242a"), C("1e5a8a"))[k])
    for k, x in enumerate((-0.6, -0.48, -0.355, -0.23, -0.11)):
        m.torus(0.016, 0.003, lv(10, 6), 3, "sw_metal", T(x, y2 - 0.02, z2 + 0.003), CAP)
        size = ("l", "m", "xl", "m", "l")[k]
        r = SIZES[size]
        place_bauble(s, "merc" if k != 3 else "gloss", ("teal", "gold", "silver", "copper", "copper")[k], size,
                     (x, y2 - 0.02, z2 + 0.003 + r * 0.92), rx=-0.25, rz=0.3 * k)
    m.box((0.42, 0.1, 0.004), T(0.66, y2 - 0.03, z2 + 0.002), "sw_matte", C("123a44"))
    for k, x in enumerate((0.5, 0.74)):
        pinecone_lying(m, (x, y2 - 0.04 + 0.015 * (k % 2), z2 + 0.004), 0.4 * k - 0.4, (MERC["gold"], MERC["copper"])[k])
    for k, x in enumerate((0.62, 0.84)):
        r = SIZES["m"]
        place_bauble(s, ("gloss", "merc")[k], ("teal", "silver")[k], "m", (x, y2 - 0.035, z2 + 0.004 + r * 0.97),
                     rx=math.radians(84), rz=(1.2, -2.0)[k])
    F.menu_board(m, T(1.08, y2 + 0.03, z2), 0.26, 0.2, "mn_schmuck", lean=0.08)
    # ---- tier 3: four large gold-foil angels on plinths
    x3, y3, z3 = _tier(3)
    for k, x in enumerate((-1.0, -0.36, 0.36, 1.0)):
        m.lathe([(0.05, 0.0), (0.046, 0.045), (0.0, 0.045)], lv(8, 6), vlib.RW("wood"), T(x, y3 - 0.005, z3), C("4a2c1a"))
        m.cyl(0.047, 0.047, 0.004, lv(8, 6), "sw_metal", T(x, y3 - 0.005, z3 + 0.045), CAP, caps=False)
        rauschgold(m, T(x, y3 - 0.005, z3 + 0.049, rz=0.12 * (1 if x < 0 else -1)), 1.36 + 0.06 * (k % 2))
    # ---- warm fairy lights in loops under the front lips of tiers 2 and 3 (the lip's bottom edge; just in front
    # of its gold bead)
    for (tx, ty, tz), n in ((_tier(2), 2), (_tier(3), 3)):
        dpt = SLOTS[f"slot_shelf_{n}"]["depth"]
        fairy_loops(m, -L / 2 + 0.04, L / 2 - 0.04, ty - dpt / 2 - 0.026, tz - 0.036, 8, 0.03, 0.095)
    # the back garland hangs in front of the mirror (mirror_0) from its frame and its two glazing bars, so the
    # mirror doubles it; it stays under the canopy's sight line from the lane
    mir = SLOTS.get("mirror_0", {}).get("glass", [[-1.5, 1.234, 1.1], [1.5, 1.234, 2.62]])
    p0 = SLOTS["slot_shelf_1"]["position"]
    back = mir[0][1] - p0[1] - 0.024     # the gilt glazing bars stand about 1.4 cm proud of the glass
    gz = 2.44 - p0[2]
    nails = [mir[0][0] + 0.02, -0.5, 0.5, mir[1][0] - 0.02]
    for a, b in zip(nails[:-1], nails[1:]):
        beads(m, sag((a, back, gz), (b, back, gz), 0.085, 18), step=0.036, cols=("gold", "clear", "silver", "clear"))
    for i, x in enumerate(nails):
        # the outer nails go into the frame at the glass; the gilt glazing bars stand proud, so those nails are short
        # (the cylinder runs from its origin toward -Y): outer nails from the glass, bar nails from the bar face
        tail = 0.022 if i in (0, len(nails) - 1) else 0.008
        m.cyl(0.004, 0.004, tail + 0.004, 5, "sw_metal", T(x, back + tail, gz, rx=math.pi / 2), CAP)
    s.finish()
    return s


def case():
    """The glass case (slot_cabinet, on its velvet floor; a glass shelf at shelf_height): a deep blue velvet tray
    of ten large mercury baubles below; on the glass shelf a Rauschgoldengel between two spun-glass birds and a
    small pyramid of gold and silver baubles."""
    sw, sd, sh = SLOTS["slot_cabinet"]["inner_size"]
    gz = SLOTS["slot_cabinet"]["shelf_height"]
    s = vlib.PropSet("prop_schmuck_case", "slot_cabinet", STALL, footprint=(sw, sd))
    m = s.static
    m.box((0.54, 0.22, 0.026), T(0.0, -0.02, 0.013), "sw_matte", C("14244a"), skip=("nz",))
    cols = ["silver", "teal", "gold", "copper", "silver", "gold", "copper", "silver", "teal", "gold"]
    for k in range(6):
        cx, cy = -0.12 + (k % 3) * 0.12, -0.07 + (k // 3) * 0.1
        place_bauble(s, "merc", cols[k], "m" if k % 3 else "l", (cx, cy, 0.026 + 0.026), rx=math.radians(75), rz=0.7 * k)
    m.cyl(0.04, 0.04, 0.01, lv(10, 6), vlib.RW("wood"), T(-0.03, 0.02, gz), C("4a2c1a"))
    rauschgold(m, T(-0.03, 0.02, gz + 0.01), 0.95)
    pyr = [(-0.03, 0.0), (0.03, 0.0), (0.0, 0.05)]
    for k, (px, py) in enumerate(pyr):
        place_bauble(s, "merc", ("gold", "silver", "copper")[k], "s", (0.15 + px, -0.04 + py * 0.4, gz + 0.026),
                     rx=1.3, rz=k * 2.0)
    place_bauble(s, "merc", "gold", "s", (0.15, -0.03, gz + 0.072), rx=0.2, rz=0.5)
    s.finish()
    return s


def tree():
    """The display tree on the dais in the right bay (slot_tree, top 0.5 x 0.4, 1.45 m max): a 1.15 m fir in a
    wooden tub, a large Rauschgoldengel on top, thirteen mercury and gloss baubles, a spiral of gold glass beads
    and silver Lametta strands hanging from the tier skirts (tinsel_2). The
    hook_tree_<n> empties stay (decoration, BUILD.md round 9)."""
    s = vlib.PropSet("prop_schmuck_tree", "slot_tree", STALL, footprint=tuple(SLOTS["slot_tree"]["top_size"]))
    m = s.static
    n = 12
    m.lathe([(0.14, 0.0), (0.17, 0.2), (0.18, 0.22), (0.0, 0.22)], lv(12, 8), vlib.RW("stave"), T(0, 0, 0), C("8a5a34"))
    for z in (0.05, 0.17):
        m.cyl(0.145 + z * 0.15, 0.145 + z * 0.15, 0.015, lv(n, 8), "sw_metal_rough", T(0, 0, z), C("3a3a3a"), caps=False)
    m.cyl(0.025, 0.02, 0.2, 6, vlib.RW("wood"), T(0, 0, 0.2), C("4a3020"), caps=False)
    tiers = [(0.34, 0.3, 0.56), (0.29, 0.48, 0.74), (0.23, 0.64, 0.9), (0.16, 0.8, 1.04), (0.1, 0.94, 1.14)]
    if vlib.lite():
        tiers = [tiers[0], tiers[2], tiers[4]]
    for r, z0, z1 in tiers:
        rr = [r * (1 + 0.12 * ((j * 7) % 3 - 1)) for j in range(n)]
        ring0 = [(rr[j] * math.cos(TWO_PI * j / n), rr[j] * math.sin(TWO_PI * j / n), z0 - 0.02 * (j % 2)) for j in range(n)]
        mid = [(rr[j] * 0.55 * math.cos(TWO_PI * (j + 0.5) / n), rr[j] * 0.55 * math.sin(TWO_PI * (j + 0.5) / n),
                (z0 + z1) / 2) for j in range(n)]
        m.loft([ring0, mid, [(0, 0, z1)] * n], "garland", None, C("ffffff"), MK, closed=True, cap0=True)
    rauschgold(m, T(0, 0, 1.1), 1.35)

    def surface(z):
        """Radius of the tree's outline at height z (the tier skirts)."""
        best = 0.0
        for r, z0, z1 in [(0.34, 0.3, 0.56), (0.29, 0.48, 0.74), (0.23, 0.64, 0.9), (0.16, 0.8, 1.04), (0.1, 0.94, 1.14)]:
            if z0 - 0.02 <= z <= z1:
                best = max(best, r * (z1 - z) / (z1 - z0 + 0.02))
        return best

    # gold bead spiral from the bottom tier up to the angel, a little off the branch tips
    pts = []
    for i in range(61):
        f = i / 60
        z = 0.34 + 0.72 * f
        a = -math.pi / 2 + 2.4 * TWO_PI * f
        r = surface(z) * 0.93 + 0.012
        pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    beads(m, pts, step=0.04, r=0.0058, cols=("gold", "gold", "clear"))
    hooks = []
    for ti, (r, z0, z1) in enumerate([(0.34, 0.3, 0.56), (0.29, 0.48, 0.74), (0.23, 0.64, 0.9), (0.16, 0.8, 1.04)]):
        for j in range(3 if ti < 3 else 2):
            a = -math.pi / 2 + (j - (1 if ti < 3 else 0.5)) * 0.85 + 0.3 * (ti % 2)
            hooks.append((r * 0.82 * math.cos(a), r * 0.82 * math.sin(a), z0 + 0.03))
    hooks += [(0.28 * math.cos(a), 0.28 * math.sin(a), 0.36) for a in (0.6, 2.5)]
    for i, h in enumerate(hooks):
        s.empty(f"hook_tree_{i}", h)
    cols = ["silver", "teal", "gold", "copper", "silver", "gold", "teal", "copper", "gold", "silver", "teal", "gold", "copper", "silver"]
    for i, (hx, hy, hz) in enumerate(hooks):
        size = ("m", "s", "m", "l")[i % 4] if hz < 0.7 else "s"
        if i % 2 == 1:
            size = "xs" if hz > 0.7 else "s"
        r = SIZES[size]
        top = (hx * 1.04, hy * 1.04, hz - 0.01)
        m.tube([(hx, hy, hz + 0.004), top], 0.001, 3, "sw_satin", None, C("e8e2d4"))
        key, r = bauble_proto(s, "merc" if i % 5 else "gloss", cols[i] if i % 5 else "teal", size)
        s.inst(key, T(*top, rz=i))
    # Lametta: silver foil strands hanging from the tier skirts (tinsel_2, the engine's glint shader)
    rnd = random.Random(5)
    # the strands are drawn from one seeded list; lite keeps every third plus the ones that set the bounds
    strands = []
    for ti, (r, z0, z1) in enumerate([(0.34, 0.3, 0.56), (0.29, 0.48, 0.74), (0.23, 0.64, 0.9), (0.16, 0.8, 1.04)]):
        k = (44, 36, 28, 18)[ti]
        for j in range(k):
            a = -math.pi / 2 + (j / k - 0.5) * 4.4 + rnd.uniform(-0.05, 0.05)    # the front 250 degrees
            rr = r * rnd.uniform(0.86, 1.04)
            p = Vector((rr * math.cos(a), rr * math.sin(a), z0 + rnd.uniform(0.0, 0.03)))
            L = rnd.uniform(0.05, 0.11)
            tip = p + Vector((rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01), -L))
            e = Vector((-math.sin(a + rnd.uniform(-1, 1)), math.cos(a), 0)).normalized() * 0.0016
            # kinked once and twisted between its two facets, so the strand glints in flecks (round 9 pass 2)
            tw = rnd.uniform(0.7, 1.4)
            e2 = Vector((e.x * math.cos(tw) - e.y * math.sin(tw), e.x * math.sin(tw) + e.y * math.cos(tw), 0))
            mid = p.lerp(tip, 0.5) + Vector((rnd.uniform(-0.005, 0.005), rnd.uniform(-0.005, 0.005), 0))
            strands.append(([p - e, p + e, mid + e2, mid - e2, tip + e * 0.8, tip - e * 0.8],
                            vlib.jit(MERC["silver"], 0.12)))
    keep = set(range(0, len(strands), 3)) if vlib.lite() else set(range(len(strands)))
    for ax in range(3):
        keep.add(min(range(len(strands)), key=lambda i: min(v[ax] for v in strands[i][0])))
        keep.add(max(range(len(strands)), key=lambda i: max(v[ax] for v in strands[i][0])))
    with plain(s, "tinsel_2", (0.0, 0.0, 0.0)) as tm:
        for i in sorted(keep):
            q, col = strands[i]
            tm.add([tuple(v) for v in q], [(0, 1, 2, 3), (3, 2, 4, 5)], [[(0, 0)] * 4] * 2, None, col, "tinsel", False)
    s.report_extra = {"hooks": len(hooks)}
    s.finish()
    return s


def _def(fn, slot_name, seed, kind, label, seat=None):
    d = dict(fn=fn, slot=slot_name, stall=STALL, kind=kind, section=False, seed=seed, label=label, width=4.5,
             cam=None, fill=True, ao_size=(256, 128),
             seat=seat or ("hang" if "rail" in slot_name or "tinsel" in slot_name or slot_name == "slot_mirrorball" else
                           "stand" if slot_name == "slot_tree" else "tiers" if fn is shelf else "board"))
    if slot_name not in SLOTS:
        d["standin"] = STANDIN[slot_name]
    return d


SETS = {
    "prop_schmuck_harmonica": _def(harmonica, "slot_harmonica_rail", 89, "rail", "Ornament shop: glass harmonica"),
    "prop_schmuck_mirrorball": _def(mirrorball, "slot_mirrorball", 90, "rail", "Ornament shop: mirror ball"),
    "prop_schmuck_pyramid": _def(pyramid, "slot_pyramid", 91, "counter", "Ornament shop: candle pyramid"),
    "prop_schmuck_garland": _def(garland, "slot_tinsel_2", 81, "rail", "Ornament shop: front bead garland", "hang"),
    "prop_schmuck_tinsel_1": _def(tinsel_canopy, "slot_tinsel_1", 92, "rail", "Ornament shop: gold Lametta", "hang"),
    "prop_schmuck_tinsel_3": _def(tinsel_beam, "slot_tinsel_3", 93, "rail", "Ornament shop: silver Lametta", "hang"),
    "prop_schmuck_rail_2": _def(rail_2, "slot_rail_2", 82, "rail", "Ornament shop: inner rail"),
    "prop_schmuck_rail_3": _def(rail_3, "slot_rail_3", 86, "rail", "Ornament shop: rail over the case"),
    "prop_schmuck_rail_4": _def(rail_4, "slot_rail_4", 87, "rail", "Ornament shop: rail over the tree"),
    "prop_schmuck_counter": _def(counter, "slot_counter", 83, "counter", "Ornament shop: counter"),
    "prop_schmuck_shelf": _def(shelf, "slot_shelf_1", 84, "shelf", "Ornament shop: shelves"),
    "prop_schmuck_case": _def(case, "slot_cabinet", 88, "case", "Ornament shop: glass case"),
    "prop_schmuck_tree": _def(tree, "slot_tree", 85, "front", "Ornament shop: display tree"),
}
