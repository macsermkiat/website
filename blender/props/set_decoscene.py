"""Round 8, second pass (Mac, 2026-10-05: "There's no need to fully render object in side stores, because there
will be no interaction to save the loading time"): every deco stall's goods as cheap scenery.

    prop_deco_<key>   slot_counter of deco_<key>.glb   ONE glb per stall, ONE merged mesh (prop_deco_<key>_goods)

What is in it, all seen from the lane:
    counter      the stall's counter goods (set_deco.<key>)                       authored at slot_counter
    rail         goods hung from the carpenter's slot_rail_1 (deco_slots.json):   rail at (x, -0.18, +0.97)
                 the old in-set rod is dropped and every string hangs from the carpenter's rail
    shelves      both back shelves (set_decofill.<key>_shelf)                     slot_shelf_1 = (0, +1.96, +0.35)
    crate        the crate, sack or basket on the carpenter's slatted bench       slot_crate = (x, -0.51, -0.71)
                 (set_decofill.<key>_front with the stand left off: the bench is the stand)
(offsets are from slot_counter in the hut's frame; all nine huts share blender/stalls/deco.py's carpentry)

Scenery rules (BUILD.md, ADR 0004): no act_ nodes, no fx_ empties, no items.json entries; everything is merged
into one mesh on the shared atlases (prop_tex_atlas_*, prop_tex_market_*), no per-set AO texture, so a stall's
goods cost one small glb and no textures of its own. The geometry is built at the lite level of detail (seg()
a third of the sections) for both files; the full file is capped at 4k triangles and the lite file is the
same mesh decimated to at most 1.5k with 512 px textures.

The Christbaumschmuck set (prop_deco_schmuck) is built the same way for the old deco_schmuck hut, which the
ornament shop (stall_schmuck.glb, set_schmuck.py) replaces: props.json lists it under "retired".
"""
import math
import random
from contextlib import contextmanager

from mathutils import Euler, Matrix, Vector

import set_deco as D
import set_decofill as F
import vlib
from vlib import C, T, WHITE

FULL_CAP, LITE_CAP = 4000, 1500
# slot offsets from slot_counter (hut frame: counter (0,-1.05,1.05), shelf_1 (0,0.91,1.40), rail z 2.02 y -1.23,
# crate bench top z 0.34 y -1.56; deco_slots.json and deco_<key>.glb)
SHELF_OFF = Vector((0.0, 1.96, 0.35))
RAIL_Y, RAIL_Z = -0.18, 0.97
CRATE_Y, CRATE_Z = -0.51, -0.71
LIFT = 0.003                    # goods stand 3 mm proud of their boards (more than the web quantisation)
WALL_Y = 2.086                  # the hut's back wall (y 1.044 in the hut) less 8 mm
FRONT_Y = 0.62                  # the front builders put their crate at y +0.62 of slot_front
SLOTS = __import__("json").load(open(__import__("os").path.join(vlib.REPO, "blender", "stalls",
                                                               "deco_slots.json")))["variants"]
COUNTER_FN = {"lebkuchen": D.lebkuchen, "mandeln": D.mandeln, "kerzen": D.kerzen, "spielzeug": D.spielzeug,
              "kaese": D.kaese, "crepes": D.crepes, "maroni": D.maroni, "puffer": D.puffer, "schmuck": D.schmuck}
SHELF_FN = {k: getattr(F, f"{k}_shelf") for k in COUNTER_FN if hasattr(F, f"{k}_shelf")}
FRONT_FN = {k: getattr(F, f"{k}_front") for k in COUNTER_FN if hasattr(F, f"{k}_front")}
LABEL = {"lebkuchen": "Lebkuchen", "mandeln": "Gebrannte Mandeln", "kerzen": "Kerzen", "spielzeug": "Holzspielzeug",
         "kaese": "Käse", "crepes": "Crêpes", "maroni": "Heiße Maroni", "puffer": "Kartoffelpuffer",
         "schmuck": "Christbaumschmuck"}


@contextmanager
def scenery(key):
    """Build the old goods with: finish() a no-op (we take the meshes, not Blender objects), strings hung from
    the carpenter's rail (clamped to its length), no in-set rod, and crates without their stands."""
    rail = SLOTS[key]["slot_rail_1"]
    half = rail["length"] / 2 - 0.04
    saved = (vlib.PropSet.finish, D.ROD_Y, D.ROD_Z, D.rod, F.hang_string, F.stand_crate)
    orig_hang, orig_crate = F.hang_string, F.stand_crate

    def hang(m, x, drop, col=vlib.C("e8dcc0"), y=None):
        return orig_hang(m, max(-half, min(half, x)), drop, col, y)

    def crate(m, M, w=0.46, d=0.32, h_stand=0.28, h_crate=0.15, stencil="cr_markt", col=vlib.C("b48c5c"), tilt=0.22):
        # the bench is the stand: keep only a slim plinth (its stencilled board still shows under the crate)
        return orig_crate(m, M, min(w, 0.56), min(d, 0.38), 0.06, h_crate, stencil, col, tilt * 0.6)

    vlib.PropSet.finish = lambda self: {}
    F.SCENERY["on"] = True
    D.ROD_Y, D.ROD_Z = RAIL_Y, RAIL_Z - 0.019            # strings tie on just under the rail's 19 mm radius
    D.rod = lambda *a, **k: None
    F.hang_string, F.stand_crate = hang, crate
    try:
        yield
    finally:
        F.SCENERY["on"] = False
        vlib.PropSet.finish, D.ROD_Y, D.ROD_Z, D.rod, F.hang_string, F.stand_crate = saved


def node_matrices(s):
    """World (set-frame) matrix of every node of a PropSet, from its loc, parent chain and rot."""
    info = {name: (loc, par) for _m, name, loc, par in s.nodes}
    out = {}

    def mat(name):
        if name in out:
            return out[name]
        loc, par = info[name]
        M = Matrix.Translation(loc)
        if name in s.rot:
            M = M @ Euler(s.rot[name]).to_matrix().to_4x4()
        out[name] = (mat(par) if par else Matrix()) @ M
        return out[name]
    for n in info:
        mat(n)
    return out


def flatten(s, into, M):
    into.merge(s.static, M)
    mats = node_matrices(s)
    for m, name, *_ in s.nodes:
        into.merge(m, M @ mats[name])


def goods(key):
    """All of one stall's goods as one Mesh in slot_counter's frame."""
    W = F.WIDTH[key]
    out = vlib.Mesh(f"prop_deco_{key}_goods")
    with scenery(key):
        s = COUNTER_FN[key]()
        flatten(s, out, Matrix())
        if key in SHELF_FN:
            sh = vlib.PropSet("tmp_shelf", "slot_shelf_1", F.STALL_ID[key])
            SHELF_FN[key](sh, W / 2 - 0.22)
            flatten(sh, out, Matrix.Translation(SHELF_OFF))
        if key in FRONT_FN:
            fr = vlib.PropSet("tmp_front", "slot_front", F.STALL_ID[key])
            FRONT_FN[key](fr, 0.0)
            cx = SLOTS[key]["slot_crate"]["position"][0]
            # the front set's crate stands at (0, +0.62, 0) of slot_front; move it onto the bench top
            flatten(fr, out, Matrix.Translation((cx, CRATE_Y - FRONT_Y, CRATE_Z)))
        stock(key, out)
    # nothing goes through the back wall (y +2.094 from slot_counter behind the shelves): the backs of sacks,
    # wheels and leaning boards that would reach it are pressed flat against it
    # and everything sits 3 mm proud of its board, so no base is coplanar with the counter, a shelf or the bench
    out.V[:] = [(x, min(y, WALL_Y) if z > 0.3 else y, z + LIFT) for x, y, z in out.V]
    # and nothing reaches down through a board (old goods authored for an older hut: a pan's burner, a sack's foot)
    out.V[:] = [(x, y, floor_z(y, z)) for x, y, z in out.V]
    # and the shelf goods keep inside the outer braces (x +-(W/2 - 0.25)): an end sack is pressed flat against one
    xb = F.WIDTH[key] / 2 - 0.27
    out.V[:] = [(max(-xb, min(xb, x)) if (z > 0.3 and y > SH_Y - 0.16) else x, y, z) for x, y, z in out.V]
    return out


def floor_z(y, z):
    """Raise a vertex that sits under the counter top or a shelf board inside that board's footprint."""
    for (y0, y1, top, depth) in ((-0.25, 0.26, 0.0, 0.2), (SH_Y - 0.15, WALL_Y + 0.01, SH1_Z, 0.065),
                                 (SH_Y - 0.15, WALL_Y + 0.01, SH2_Z, 0.035)):
        if y0 < y < y1 and top - depth < z < top + LIFT:
            return top + LIFT
    return z


# ================================================================== stocking: fill every bare stretch
# The old goods leave bare board between them (they were spaced for clicking). From the lane a stall reads as
# stocked when its boards are covered, so after the old goods are merged, every free stretch of each shelf, the
# rail and the back of the counter is filled with the stall's own cheap stock (8-40 triangles a piece).
BIN = 0.03
SH1_Z, SH2_Z = SHELF_OFF.z, SHELF_OFF.z + F.SHELF2
SH_Y = SHELF_OFF.y


def occupancy(mesh, x0, x1, y0, y1, z0, z1, pad=1):
    """Bins of BIN metres along x in [x0, x1]: True where a face centroid of `mesh` lies inside the box."""
    n = max(1, int(round((x1 - x0) / BIN)))
    occ = [False] * n
    V = mesh.V
    for f in mesh.F:
        cx = sum(V[i][0] for i in f) / len(f)
        cy = sum(V[i][1] for i in f) / len(f)
        cz = sum(V[i][2] for i in f) / len(f)
        if y0 <= cy <= y1 and z0 <= cz <= z1 and x0 <= cx <= x1:
            occ[min(n - 1, int((cx - x0) / BIN))] = True
    out = list(occ)
    for i, o in enumerate(occ):
        if o:
            for j in range(max(0, i - pad), min(n, i + pad + 1)):
                out[j] = True
    return out


def free_spans(occ, x0, min_w):
    spans, start = [], None
    for i, o in enumerate(occ + [True]):
        if not o and start is None:
            start = i
        elif o and start is not None:
            a, b = x0 + start * BIN, x0 + i * BIN
            if b - a >= min_w:
                spans.append((a, b))
            start = None
    return spans


def pack(span, items, rnd, gap=0.012):
    """Lay items [(width, fn)] side by side across span, cycling with a little shuffle; returns [(x, fn)]."""
    a, b = span
    out, x, k = [], a + gap, rnd.randrange(len(items))
    while True:
        w, fn = items[k % len(items)]
        if x + w > b - gap:
            # try the narrowest item before giving up
            w, fn = min(items, key=lambda it: it[0])
            if x + w > b - gap:
                break
        out.append((x + w / 2, fn))
        x += w + gap * rnd.uniform(0.6, 1.6)
        k += 1 + (rnd.random() < 0.3)
    return out


# ---- standing stock (fn(m, M, rnd), origin at the item's base, front toward -Y)
def ctn(region, w, d, h, side=(0.04, 0.45, 0.07, 0.55)):
    return w, lambda m, M, r: F.carton(m, M @ T(rz=r.uniform(-0.06, 0.06)), w, d, h, region, side)


def ctn_stack(region, w, d, h, n=2):
    def fn(m, M, r):
        for k in range(n):
            F.carton(m, M @ T(r.uniform(-0.01, 0.01), 0, k * h, rz=r.uniform(-0.08, 0.08)), w, d, h, region)
    return w, fn


def jar(label, fill, lid, h=0.11, rad=0.035):
    return 2 * rad + 0.004, lambda m, M, r: F.jar(m, M, label, vlib.jit(fill, 0.05),
                                                h=h * r.uniform(0.92, 1.08), r=rad, lid=lid)


def jars(label, fills, lid, h=0.1, rad=0.032, n=3):
    def fn(m, M, r):
        for k in range(n):
            F.jar(m, M @ T((k - (n - 1) / 2) * (2 * rad + 0.004), 0, 0), label, fills[(k + r.randrange(9)) % len(fills)],
                  h=h, r=rad, lid=lid)
    return n * (2 * rad + 0.004), fn


def bottles(label, glass, n=3, h=0.24, rad=0.03):
    def fn(m, M, r):
        for k in range(n):
            F.bottle(m, M @ T((k - (n - 1) / 2) * (2 * rad + 0.006), 0.01 * (k % 2), 0), label, glass, h=h, r=rad)
    return n * (2 * rad + 0.006), fn


def candles(cols, n=3, h0=0.08, h1=0.2):
    def fn(m, M, r):
        for k in range(n):
            rad = r.choice((0.026, 0.032, 0.04))
            F.candle(m, M @ T((k - (n - 1) / 2) * 0.08, r.uniform(-0.02, 0.02), 0), rad, r.uniform(h0, h1),
                     C(r.choice(cols)))
    return n * 0.08, fn


def wheels(rinds, rad=0.11, h=0.08, n=2):
    def fn(m, M, r):
        for k in range(n):
            F.wheel(m, M @ T(r.uniform(-0.01, 0.01), 0, k * h, rz=r.uniform(0, 3)), rad * (1 - 0.08 * k), h,
                    C(r.choice(rinds)), label_k=(r.randrange(4) if k == n - 1 else None))
    return 2 * rad, fn


def sacks(region, heap=None, heap_region="chestnut", rad=0.08, h=0.2):
    return 2 * rad + 0.01, lambda m, M, r: F.sack(m, M @ T(rz=r.uniform(-0.3, 0.3)), rad, h * r.uniform(0.9, 1.1),
                                                   region, heap, heap_region)


def tins(n=2):
    def fn(m, M, r):
        for k in range(n):
            D.lk_tin(m, M @ T(0, 0, k * 0.052, rz=r.uniform(0, 3)), 0.07 - 0.006 * k, 0.05)
    return 0.15, fn


def figures(n=3, sc=1.1):
    coats = ["a8181c", "1f3a78", "2a6a3a", "d8b048", "f2ead8"]

    def fn(m, M, r):
        for k in range(n):
            F.figure(m, M @ T((k - (n - 1) / 2) * 0.065 * sc, r.uniform(-0.01, 0.02), 0, rz=r.uniform(-0.4, 0.4)),
                     C(r.choice(coats)), C(r.choice(("141414", "a8181c", "1f3a78"))), s=sc * r.uniform(0.85, 1.15))
    return n * 0.065 * sc, fn


def cars(n=2):
    cols = ["b0282a", "2a6a3a", "1f3a78", "d8b048"]

    def fn(m, M, r):
        for k in range(n):
            F.toy_car(m, M @ T((k - (n - 1) / 2) * 0.13, 0, 0, rz=r.uniform(-0.2, 0.2)), C(r.choice(cols)))
    return n * 0.13, fn


def hearts_lean(n=3, size=0.12):
    def fn(m, M, r):
        for k in range(n):
            sz = size * r.uniform(0.9, 1.1)
            D.lebkuchen_heart(m, M @ T((k - (n - 1) / 2) * size * 0.95, 0.02, sz * 0.53, rx=math.pi / 2 - 0.25), sz,
                              r.randrange(6))
    return n * size * 0.95, fn


def tray(heap_region, col, w=0.26, d=0.18, mat="glaze"):
    """A shallow wooden tray heaped with goods (for the back of a counter)."""
    def fn(m, M, r):
        m.box((w, d, 0.012), M @ T(0, 0, 0.006), vlib.RW("wood"), C("b48c5c"), skip=("nz",))
        for sx in (-1, 1):
            m.box((0.012, d, 0.04), M @ T(sx * (w / 2 - 0.006), 0, 0.02), vlib.RW("wood"), C("a07a4a"), skip=("nz",))
        m.box((w, 0.012, 0.04), M @ T(0, d / 2 - 0.006, 0.02), vlib.RW("wood"), C("a07a4a"), skip=("nz",))
        m.box((w, 0.012, 0.03), M @ T(0, -d / 2 + 0.006, 0.015), vlib.RW("wood"), C("a07a4a"), skip=("nz",))
        m.lathe([(0.5, 0.0), (0.35, 0.6), (0.0, 1.0)], 6, heap_region,
                M @ T(0, 0, 0.012) @ Matrix.Diagonal((w * 0.95, d * 0.95, 0.07, 1)), col, mat, v_by="z")
    return w, fn


# ---- hanging stock (fn(m, x, r) hangs one piece from the rail at x)
def h_bag(region, side=(0.0, 0.2, 0.1, 0.8), w=0.09, h=0.15, col=C("b0282a")):
    def fn(m, x, r):
        p = F.hang_string(m, x, r.uniform(0.1, 0.24), col)
        F.carton(m, T(p.x, p.y, p.z - h, rz=r.uniform(-0.25, 0.25)), w, 0.05, h, region, side)
    return w, fn


def h_heart():
    def fn(m, x, r):
        size = r.choice((0.12, 0.14, 0.17))
        p = F.hang_string(m, x, r.uniform(0.12, 0.3), C(r.choice(("b0282a", "2a6a3a", "d8b048", "f2ead8"))))
        D.lebkuchen_heart(m, T(p.x, p.y + 0.006, p.z - size * 0.36 + 0.01, rx=math.pi / 2, ry=r.uniform(-0.2, 0.2))
                          @ T(0, 0, -0.006), size, r.randrange(6))
    return 0.15, fn


def h_taper():
    cols = ["b0282a", "f2ead8", "2a6a3a", "d8b048", "2a4a8a", "7a3a7a"]
    return 0.06, lambda m, x, r: D.taper_pair(m, x, r.uniform(0.2, 0.3), C(r.choice(cols)))


def h_star():
    cols = ["d8b078", "b0282a", "2a6a3a", "d8b048", "1f3a78"]

    def fn(m, x, r):
        p = F.hang_string(m, x, r.uniform(0.08, 0.22))
        rad = r.choice((0.05, 0.06, 0.07))
        m.extrude(D.star_poly(rad, rad * 0.43, 5), 0.008, T(p.x, p.y, p.z - rad * 0.92, rx=math.pi / 2), vlib.RW("wood"),
                  vlib.RW("wood"), C(r.choice(cols)), back=False)
    return 0.13, fn


def h_pear():
    def fn(m, x, r):
        p = F.hang_string(m, x, r.uniform(0.08, 0.16))
        m.lathe([(0.0, -0.17), (0.045, -0.15), (0.05, -0.1), (0.03, -0.05), (0.012, -0.025), (0.0, 0.0)], 6,
                "cheese_rind", T(p.x, p.y, p.z), C(r.choice(("e8c070", "a86a2a", "c89048"))), "atlas")
    return 0.11, fn


def h_braid(col):
    def fn(m, x, r):
        p = F.hang_string(m, x, 0.03, C("c8b080"))
        n, rad = 4, 0.024
        for k in range(n):
            z = p.z - 0.03 - k * 0.055
            m.lathe([(0.0, -rad), (rad, -rad * 0.2), (rad * 0.6, rad * 0.6), (0.0, rad * 1.2)], 5, "sw_satin",
                    T(p.x + (0.018 if k % 2 else -0.018), p.y, z), vlib.jit(col, 0.06),
                    "atlas")
    return 0.09, fn


def h_kraft():
    def fn(m, x, r):
        p = F.hang_string(m, x, r.uniform(0.08, 0.18), C("c8a070"))
        m.box((0.08, 0.05, 0.14), T(p.x, p.y, p.z - 0.07, rz=r.uniform(-0.2, 0.2)), "kraft_maroni", WHITE,
              faces={"ny": "kraft_maroni"}, skip=("nz",))
    return 0.09, fn


HONEY, NOUGAT, APPLE, CHERRY = C("c8861e"), C("5a3018"), C("d8b070"), C("7a1420")
RED, GOLD, GREEN = C("b0282a"), C("d8b048"), C("2a6a3a")
CANDLE_COLS = ["b0282a", "f2ead8", "2a6a3a", "d8b048", "2a4a8a", "7a3a7a", "e8d0a0", "c0562a"]
# per stall: back row (tall, against the wall), front row (low), rail pieces, counter-back pieces
KITS = {
    "lebkuchen": dict(crate=(0.25, [hearts_lean(3, 0.12)]), back=[ctn("bx_lebkuchen", 0.18, 0.05, 0.27), ctn_stack("bx_printen", 0.14, 0.07, 0.09, 3), hearts_lean(2, 0.19)],
                      front=[tins(3), jar("lb_honey", HONEY, GOLD), hearts_lean(2, 0.12)],
                      rail=[h_heart()], counter=[tins(2), tray("lebkuchen_1", WHITE, mat="atlas")],
                      mid=[ctn_stack("bx_lebkuchen", 0.2, 0.13, 0.05, 2)]),
    "mandeln": dict(back=[ctn("bag_mandeln", 0.11, 0.06, 0.24, (0.0, 0.2, 0.1, 0.8)), ctn_stack("bx_mandeln", 0.19, 0.08, 0.1, 2)],
                    front=[jars("lb_mandel", [C("c89a70"), C("f0e0e8"), C("8a3e1a")], RED, h=0.13, rad=0.038),
                           ctn("bag_mandeln", 0.09, 0.05, 0.17, (0.0, 0.2, 0.1, 0.8))],
                    rail=[h_bag("bag_mandeln")], counter=[tray("almonds", C("c89a70"))],
                    mid=[ctn_stack("bx_mandeln", 0.19, 0.13, 0.06, 2)]),
    "kerzen": dict(crate=(0.25, [candles(CANDLE_COLS, 3, 0.08, 0.16)]), back=[candles(CANDLE_COLS, 4, 0.16, 0.3), ctn_stack("bx_kerzen", 0.17, 0.08, 0.11, 2)],
                   front=[candles(CANDLE_COLS, 3, 0.07, 0.16), jar("lb_wachs", HONEY, GOLD)],
                   rail=[h_taper()], counter=[candles(CANDLE_COLS, 3, 0.1, 0.24)],
                   mid=[candles(CANDLE_COLS, 3, 0.06, 0.12)]),
    "spielzeug": dict(crate=(0.2, [figures(3, 1.2), cars(1)]), back=[ctn_stack("bx_baukasten", 0.22, 0.08, 0.1, 2), ctn("bx_puzzle", 0.2, 0.05, 0.22), figures(3, 1.6)],
                      front=[figures(3, 1.1), cars(2)], rail=[h_star()], counter=[figures(3, 1.4), cars(1)],
                      mid=[cars(2)]),
    "kaese": dict(crate=(0.18, [wheels(["e8c070", "f0d890", "d8a040"], 0.09, 0.07, 1)]), back=[wheels(["e8c070", "d8a040", "c87a30", "f0d890"], 0.13, 0.085, 3), ctn_stack("bx_kaese", 0.17, 0.08, 0.1, 2)],
                  front=[wheels(["e8c070", "f0d890"], 0.065, 0.06, 2), jar("lb_honey", HONEY, GOLD), jar("lb_senf", C("c8a020"), RED)],
                  rail=[h_pear()], counter=[wheels(["e8c070", "d8a040"], 0.11, 0.08, 2)],
                  mid=[wheels(["f0d890", "c87a30"], 0.09, 0.06, 1)]),
    "crepes": dict(crate=(0.22, [jars("lb_apfel", [APPLE], RED, n=2, h=0.12), jars("lb_nougat", [NOUGAT], GOLD, n=2, h=0.12)]), back=[sacks("sk_mehl", rad=0.085, h=0.27), bottles("lb_oel", C("6a7a2a"), 2, h=0.28),
                         ctn_stack("bx_printen", 0.14, 0.07, 0.09, 2)],
                   front=[jars("lb_nougat", [NOUGAT], GOLD, h=0.12, rad=0.036), jars("lb_apfel", [APPLE], RED, n=2, h=0.12),
                          jars("lb_kirsch", [CHERRY], RED, n=2, h=0.12), jar("lb_zucker", C("f4f0e8"), C("1f3a78"))],
                   rail=[], counter=[jars("lb_nougat", [NOUGAT], GOLD, n=2, h=0.13, rad=0.04)],
                   mid=[jars("lb_kirsch", [CHERRY], RED, n=2)]),
    "maroni": dict(back=[sacks("sk_maronen", C("6a3418"), "chestnut", 0.095, 0.28)],
                   front=[ctn_stack("kraft_maroni", 0.09, 0.05, 0.13, 1), sacks("sk_maronen", C("6a3418"), "chestnut", 0.07, 0.16)],
                   rail=[h_kraft()], counter=[tray("chestnut", C("6a3418"))],
                   mid=[ctn_stack("kraft_maroni", 0.09, 0.05, 0.12, 1)]),
    "puffer": dict(crate=(0.2, [jars("lb_apfel", [APPLE], RED, n=3, h=0.12)]), back=[sacks("sk_kartoffeln", C("c8a060"), "puffer", 0.095, 0.28), bottles("lb_oel", C("6a7a2a"), 2, h=0.28)],
                   front=[jars("lb_apfel", [APPLE], RED, h=0.13, rad=0.038), jar("lb_senf", C("c8a020"), RED)],
                   rail=[h_braid(C("c89a50")), h_braid(C("f0e8d8"))], counter=[jars("lb_apfel", [APPLE], RED, n=2)],
                   mid=[jars("lb_senf", [C("c8a020")], RED, n=2)]),
}


def stock(key, mesh):
    """Fill the bare stretches of the shelves, the rail and the counter's back with KITS[key]."""
    kit = KITS.get(key)
    if not kit:
        return 0
    r = random.Random(1000 + len(key) * 7 + sum(map(ord, key)))
    W = F.WIDTH[key]
    add = vlib.Mesh("stock")
    hw = W / 2 - 0.2
    # shelves: a back row against the wall and a front row behind the lip, wherever the board is bare
    for z in (SH1_Z, SH2_Z):
        # the back row stands against the wall wherever nothing TALL stands back there yet (low goods in
        # front of it stay: the tall stock rises behind them); the front row only on bare board
        for row, (y0, y1, yy, zmin) in (("back", (SH_Y + 0.03, SH_Y + 0.15, SH_Y + 0.075, 0.12)),
                                        ("front", (SH_Y - 0.15, SH_Y + 0.0, SH_Y - 0.04, 0.004))):
            occ = occupancy(mesh, -hw, hw, y0, y1, z + zmin, z + 0.35)
            for bx in (0.0, -(W / 2 - 0.25), W / 2 - 0.25):      # the hut's shelf braces (blender/stalls/deco.py)
                for i in range(len(occ)):
                    if abs(-hw + (i + 0.5) * BIN - bx) < 0.06:
                        occ[i] = True
            for span in free_spans(occ, -hw, 0.07):
                for x, fn in pack(span, kit[row], r):
                    fn(add, T(x, yy + r.uniform(-0.01, 0.01), z), r)
    # the rail: one piece every 11-16 cm where nothing hangs yet
    if kit["rail"]:
        half = SLOTS[key]["slot_rail_1"]["length"] / 2 - 0.05
        occ = occupancy(mesh, -half, half, RAIL_Y - 0.1, RAIL_Y + 0.1, RAIL_Z - 0.5, RAIL_Z - 0.03, pad=2)
        for span in free_spans(occ, -half, 0.08):
            for x, fn in pack(span, kit["rail"], r, gap=0.015):
                fn(add, x, r)
    # the counter: the back row, then a low middle row (the front 12 cm stay clear for paying)
    for key_row, (y0, y1, yy) in (("counter", (0.03, 0.25, 0.13)), ("mid", (-0.12, 0.03, -0.04))):
        occ = occupancy(mesh, -hw, hw, y0, y1, 0.004, 0.45)
        for span in free_spans(occ, -hw, 0.12):
            for x, fn in pack(span, kit[key_row], r, gap=0.03):
                fn(add, T(x, yy, 0.0), r)
    # the display crate on the bench: a row of stock standing in it (front builders with stand_crate only)
    if "crate" in kit:
        tilt, items = kit["crate"]
        cx = SLOTS[key]["slot_crate"]["position"][0]
        Mc = (T(cx, CRATE_Y - FRONT_Y + FRONT_Y + 0.03, CRATE_Z + 0.06 + 0.02) @ T(rx=-tilt * 0.6)
              @ T(0, -0.005, 0.012))
        for x, fn in pack((-0.2, 0.2), items, r, gap=0.02):
            fn(add, Mc @ T(x, 0.03, 0.0), r)
    mesh.merge(add)
    return add.tris


def prune_small(bm, cap, max_diag=0.09):
    """Lite: drop the smallest separate pieces (strings, tags, wicks, little jars far back) until the mesh is
    near `cap`, before the collapse has to eat into the shapes that read from the lane."""
    import bmesh
    bm.faces.ensure_lookup_table()
    seen, islands = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, isl = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        vs = {v for g in isl for v in g.verts}
        lo = [min(v.co[i] for v in vs) for i in range(3)]
        hi = [max(v.co[i] for v in vs) for i in range(3)]
        diag = sum((hi[i] - lo[i]) ** 2 for i in range(3)) ** 0.5
        islands.append((diag, sum(len(g.verts) - 2 for g in isl), isl))
    total = sum(t for _d, t, _i in islands)
    kill = []
    for diag, t, isl in sorted(islands, key=lambda it: it[0]):
        if total <= cap * 1.2 or diag > max_diag:
            break
        kill.extend(isl)
        total -= t
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    print(f"[scenery] pruned {len(kill)} faces of small pieces -> about {total} triangles")


def decimate(ob, cap, prune=False):
    """Collapse-decimate a mesh object down to at most `cap` triangles (UVs and colours kept)."""
    import bpy
    me = ob.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    if tris <= cap:
        return tris
    # merge the duplicated corners Mesh.merge leaves (each face has its own vertices) so collapse can work
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    if prune:
        prune_small(bm, cap)
    bm.to_mesh(me)
    bm.free()
    for _ in range(4):
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        if tris <= cap:
            break
        mod = ob.modifiers.new("dec", 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = max(0.05, cap / tris * 0.97)
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = ob
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    me.validate(clean_customdata=False)
    me.update()
    return sum(len(p.vertices) - 2 for p in me.polygons)


def scene_set(key, stall, seed):
    def build():
        full_export = not vlib.lite()
        vlib.LITE["on"] = True                       # the scenery is built at the lite level of detail
        try:
            m = goods(key)
        finally:
            vlib.LITE["on"] = not full_export
        s = vlib.PropSet(f"prop_deco_{key}", "slot_counter", stall, footprint=(F.WIDTH[key], 0.5),
                         note="scenery: one merged mesh, no act_ nodes")
        s.static = m
        objs = s.finish()
        print(f"[scenery] {s.name} {'full' if full_export else 'lite'}: {m.tris} triangles before the cap")
        tris = decimate(objs["static"], FULL_CAP if full_export else LITE_CAP, prune=not full_export)
        s.report_extra = {"scenery": True, "merged_meshes": 1, "goods_triangles": tris,
                          "covers": ["counter", "rail (slot_rail_1)", "shelf 1", "shelf 2", "crate on the bench (slot_crate)"]
                          if key in SHELF_FN else ["counter", "rail"]}
        return s
    return dict(fn=build, slot="slot_counter", stall=stall, kind="counter", section=False, seed=seed,
                label=LABEL[key], width=F.WIDTH[key], fill=True, no_ao=True, scenery=True, seat="span")


SETS = {f"prop_deco_{k}": scene_set(k, F.STALL_ID[k], 61 + i)
        for i, k in enumerate(("lebkuchen", "mandeln", "kerzen", "spielzeug", "kaese", "crepes", "maroni", "puffer"))}
RETIRED = {"prop_deco_schmuck": scene_set("schmuck", "deco-schmuck", 65)}
