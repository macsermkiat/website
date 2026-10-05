"""Round 8 (ADR 0004, "Deco stalls are full and worth a click"): the rest of each deco stall.

Every deco stall now has three prop sets, each authored at the slot it is parented to:

    prop_deco_<key>          slot_counter   the counter goods (set_deco.py) plus a hanging rail over the counter
    prop_deco_<key>_shelf    slot_shelf_1   both back shelves: goods on shelf 1 (z 0) and shelf 2 (z +0.40)
    prop_deco_<key>_front    slot_front     a crate or sack on the ground at the counter's corner

The nine deco huts share one carpentry (blender/stalls/deco.py, Hut): shelves 0.30 m deep at 1.40 and 1.80 m
with a 5 cm lip at the front edge (y -0.14 from slot_shelf_1) and the back wall at y +0.15; the board runs
x = +-(W / 2 - 0.15); slot_front is 2.2 m in front of the hut centre, 0.9 m in front of the counter's edge.
The carpenter has no slot_rail_ in the deco huts yet, so each counter set carries its own thin rod under the
front header (set_deco.ROD_Z), as the Lebkuchen, Kerzen and Christbaumschmuck sets already did.

Budget: a deco stall with all its goods stays under 20k triangles (BUILD.md). The huts are 13.3k to 16k, so
the goods of the fullest stalls get 3.7k to 6.7k. Shelf goods are seen through the front opening from 3 m
and more: printed cartons (8 triangles), six-sided jars, menu boards with baked chalk lettering, low wheels.

Clickable goods follow BUILD.md: act_<stall>_<item>_<n>, each with name, label and action in items.json, and
fx_steam_<n> / fx_flame_<n> empties where something steams or burns (finish_deco below names and fills them).
"""
import math

from mathutils import Matrix, Vector

import goods as G
import vlib
from vlib import C, T, WHITE, drng, jit, seg

TWO_PI = 2 * math.pi
MK = "market"
SHELF2 = 0.40              # shelf 2's top above shelf 1's (1.80 - 1.40)
SHELF_Y = (-0.115, 0.125)  # usable depth behind the lip, in front of the back wall
WIDTH = {"lebkuchen": 3.0, "mandeln": 3.4, "kerzen": 2.6, "spielzeug": 3.2, "schmuck": 3.4, "kaese": 2.8,
         "crepes": 2.8, "maroni": 2.6, "puffer": 3.2}
STALL_ID = {k: "deco-" + ("kartoffelpuffer" if k == "puffer" else k) for k in WIDTH}


# ------------------------------------------------------------------ naming, labels and actions
# action vocabulary (items.json "action"; the engine picks the animation and sound):
#   lift     lift and turn in the hand            swing   swing on its ribbon or string (hanging goods)
#   steam    steam rises from its fx_steam_<n>     flame   a candle flame flickers up at its fx_flame_<n>
#   spin     spins about its vertical axis         roll    rolls forward a little and back
#   rock     rocks on its rockers                  cut     a wedge is cut from the wheel
#   open     a lid or flap opens                   (ornament shop: ring, light, jaw, smoke, candles, hang, find)
DE = {  # act base -> German label stem
    "heart": "Lebkuchenherz", "cone": "Tüte", "candle": "Kerze", "nutcracker": "Nussknacker",
    "train": "Holzeisenbahn", "top": "Kreisel", "rockinghorse": "Schaukelpferd", "cheese": "Käse",
    "jar": "Glas", "crepe": "Crêpe", "shaker": "Streuer", "bag": "Tüte heiße Maroni", "scale": "Krämerwaage",
    "puffer": "Kartoffelpuffer", "plate": "Teller Kartoffelpuffer",
}


def rename_acts(s, key):
    """act_<item>_<n> -> act_<key>_<item>_<n> everywhere in the set (nodes, parents, empties, items)."""
    pre = f"act_{key}_"

    def nm(n):
        return n if (not n or not n.startswith("act_") or n.startswith(pre)) else pre + n[4:]
    s.nodes = [(m, nm(name), loc, nm(par)) for m, name, loc, par in s.nodes]
    for m, name, *_ in s.nodes:
        m.name = name
    s.empties = [(nm(name), loc, nm(par)) for name, loc, par in s.empties]
    s.rot = {nm(k): v for k, v in s.rot.items()}
    s.items = {nm(k): v for k, v in s.items.items()}


def finish_deco(s, key, fx=None, free=(), actions=None):
    """Rename the set's act_ nodes to act_<key>_..., give every item a label and an action, add the fx_
    empties named in `fx` ({act node (old or new name): ("steam"|"flame", (x, y, z) offset from its origin)})
    and the free ones in `free` ([("steam"|"flame", (x, y, z) in the set)]: steam over a kettle, a flame on a
    lantern), then build the Blender objects."""
    fx = dict(fx or {})
    free = list(free) + list(getattr(s, "free_fx", []))
    rename_acts(s, key)
    pre = f"act_{key}_"
    fx = {(k if k.startswith(pre) else pre + k[4:]): v for k, v in fx.items()}
    base_n = {"slot_counter": 0, "slot_shelf_1": 50, "slot_front": 80}.get(s.slot, 0)   # unique within a stall
    counts = {"steam": base_n, "flame": base_n}
    for name, it in s.items.items():
        if not name.startswith("act_"):
            continue
        base = name[len(pre):].rsplit("_", 1)[0]
        it.setdefault("label", default_label(base, it))
        hang = str(it.get("pivot", "")).startswith("hang")
        if actions and (base in actions or name in actions):
            it.setdefault("action", actions.get(name, actions.get(base)))
        it.setdefault("action", "swing" if hang else "lift")
        if name in fx:
            kind, off = fx[name]
            e = f"fx_{kind}_{counts[kind]}"
            counts[kind] += 1
            s.empty(e, off, parent=name)
            it["fx"] = e
            it["action"] = kind
    for kind, loc in free:
        s.empty(f"fx_{kind}_{counts[kind]}", loc)
        counts[kind] += 1
    s.finish()
    return s


def default_label(base, it):
    stem = DE.get(base)
    name = it.get("name", "")
    if base == "heart" and it.get("icing"):
        return f"Lebkuchenherz „{it['icing']}“"
    if base == "cone":
        return name.replace("Paper cone of ", "Tüte ")
    if base == "candle":
        return "Kerze: " + name
    if stem:
        return f"{stem}: {name}" if stem.lower() not in name.lower() else name
    return name


def item(s, key, name, origin, label, action, detail, pivot="base", **extra):
    """A clickable good built in set coordinates: returns (mesh, finalize). The node is act_<key>_<name>."""
    from set_deco import item as _item
    return _item(s, f"act_{key}_{name}", origin, label_name(label, extra), detail, pivot=pivot,
                 label=label, action=action, **extra)


def label_name(label, extra):
    return extra.pop("display", label)


# ------------------------------------------------------------------ cheap shelf goods
def mreg(name, sub=None):
    return vlib.R(name, sub=sub)


def carton(m, M, w, d, h, region, side=(0.04, 0.45, 0.07, 0.55), top=True):
    """A printed card carton standing on its base: the print on the front (-Y), the plain ground colour of
    the print on the sides and top; no back and no bottom (it stands against the wall). 6-8 triangles."""
    sreg = mreg(region, side)
    skip = ("nz", "py") + (() if top else ("pz",))
    m.box((w, d, h), M @ T(0, 0, h / 2), sreg, WHITE, MK, faces={"ny": region}, skip=skip)


def jar(m, M, label, fill, h=0.1, r=0.034, lid=C("b0282a"), n=None):
    """A filled jar seen from the lane: an opaque glossy body tinted by its contents, a paper label round the
    front and a coloured lid. About 50 triangles (lite: about 20)."""
    n = n or seg(6, 5)
    m.lathe([(r, 0.0), (r, h - 0.01), (r * 0.82, h)], n, "sw_vgloss", M, fill, "atlas")
    if not vlib.lite():
        m.lathe([(r + 0.0008, h * 0.28), (r + 0.0008, h * 0.7)], 3, label, M, WHITE, MK, v_by="z",
                arc=math.pi * 0.85, u0=-math.pi / 2 - math.pi * 0.425)
    else:
        m.quad([(-r * 0.8, -r - 0.001, h * 0.28), (r * 0.8, -r - 0.001, h * 0.28), (r * 0.8, -r - 0.001, h * 0.7),
                (-r * 0.8, -r - 0.001, h * 0.7)], label, WHITE, MK, M)
    m.lathe([(r * 0.86, h - 0.003), (r * 0.9, h + 0.012), (0.0, h + 0.014)], n, "sw_metal_rough", M, lid, "atlas")


def bottle(m, M, label, glass=C("3a4a1a"), h=0.26, r=0.034, cap=C("d8b048")):
    """A tall bottle: body, shoulder, neck, cap and a front label quad. About 40 triangles."""
    n = seg(7, 5)
    m.lathe([(r, 0.0), (r, h * 0.62), (r * 0.42, h * 0.8), (r * 0.36, h * 0.96)], n, "sw_vgloss", M, glass, "atlas")
    m.cyl(r * 0.38, r * 0.38, h * 0.05, n, "sw_metal", M @ T(0, 0, h * 0.96), cap, caps=False)
    m.quad([(-r * 0.78, -r - 0.001, h * 0.18), (r * 0.78, -r - 0.001, h * 0.18), (r * 0.78, -r - 0.001, h * 0.5),
            (-r * 0.78, -r - 0.001, h * 0.5)], label, WHITE, MK, M)


def menu_board(m, M, w=0.36, h=0.27, region="mn_crepes", lean=0.18, frame=C("6a4a2c")):
    """A framed chalk menu board leaning back against the wall (origin at its foot, front edge)."""
    Ml = M @ T(0, 0, 0, rx=-lean)
    m.box((w + 0.03, 0.015, h + 0.03), Ml @ T(0, 0.008, (h + 0.03) / 2), vlib.RW("wood"), frame, skip=("nz", "py"))
    m.quad([(-w / 2, -0.0005, 0.015), (w / 2, -0.0005, 0.015), (w / 2, -0.0005, 0.015 + h), (-w / 2, -0.0005, 0.015 + h)],
           region, WHITE, MK, Ml)


def candle(m, M, r, h, col, cap=True, n=None):
    n = n or seg(6, 5)
    m.lathe([(r, 0.0), (r, h - 0.004), (r * 0.85, h)], n, vlib.RW("wax"), M, col, "atlas", cap1=cap)


def wheel(m, M, r, h, rind, label_k=None, n=None):
    """A cheese wheel standing on the shelf: sides and top (no bottom); with label_k a round paper label."""
    n = n or seg(10, 6)
    m.lathe([(r * 0.96, 0.0), (r, h * 0.2), (r, h * 0.8), (r * 0.96, h)], n, vlib.RW("cheese_rind"), M, rind, "atlas",
            cap1=True)
    if label_k is not None:
        reg = mreg("cheese_labels", (label_k / 4, 0.0, (label_k + 1) / 4, 1.0))
        m.disc(r * 0.55, seg(10, 6), reg, M @ T(0, 0, h + 0.0012), WHITE, MK)


def sack(m, M, r=0.11, h=0.3, region="sk_maronen", heap=None, heap_region="chestnut", n=None):
    """A burlap sack, rolled down, its stencil to the front; with heap a mound of its contents in the mouth."""
    n = n or seg(8, 5)
    prof = [(r * 0.85, 0.0), (r, h * 0.12), (r * 1.02, h * 0.7), (r * 0.94, h * 0.92), (r * 1.06, h)]
    if vlib.lite():
        prof = [prof[0], prof[2], prof[4]]
    m.lathe(prof, n, region, M @ T(0, 0, 0, rz=math.pi / 2), WHITE, MK, v_by="z", u_span=1.0)
    if heap is not None:
        m.lathe([(r * 0.98, h * 0.9), (r * 0.6, h * 0.99), (0.0, h * 1.04)], n, heap_region, M, heap, "glaze",
                v_by="z")


def stand_crate(m, M, w=0.46, d=0.32, h_stand=0.28, h_crate=0.15, stencil="cr_markt", col=C("b48c5c"), tilt=0.22):
    """An upturned crate as a stand (its stencilled board to the front) with an open display crate on top,
    tilted toward the lane. Returns the display crate's bottom-centre matrix (goods go inside it)."""
    t = 0.012
    lite = vlib.lite()
    # the stand: two ends, a stencilled front board, a top
    for sx in (-1, 1):
        m.box((t * 1.5, d, h_stand), M @ T(sx * (w / 2 - t), 0, h_stand / 2), vlib.RW("wood"), jit(col, 0.1),
              skip=("nz",))
    m.box((w, t, h_stand * 0.8), M @ T(0, -d / 2 + t / 2, h_stand * 0.5), mreg(stencil), WHITE, MK, skip=("nz", "py"))
    if not lite:
        m.box((w, t, h_stand * 0.8), M @ T(0, d / 2 - t / 2, h_stand * 0.5), vlib.RW("wood"), jit(col, 0.1),
              skip=("nz", "ny"))
    m.box((w, d, t), M @ T(0, 0, h_stand - t / 2), vlib.RW("wood"), jit(col, 0.1), skip=("nz",))
    Mc = M @ T(0, 0.03, h_stand + 0.02) @ T(0, 0, 0, rx=-tilt)
    # the display crate: front slat, back board, ends, bottom
    m.box((w - 0.02, t, h_crate * 0.55), Mc @ T(0, -d / 2 + 0.02, h_crate * 0.3), vlib.RW("wood"), jit(col, 0.1))
    m.box((w - 0.02, t, h_crate * 1.5), Mc @ T(0, d / 2 - 0.03, h_crate * 0.75), vlib.RW("wood"), jit(col, 0.1),
          skip=("nz",))
    for sx in (-1, 1):
        m.box((t * 1.5, d - 0.04, h_crate), Mc @ T(sx * (w / 2 - 0.02), -0.005, h_crate / 2), vlib.RW("wood"),
              jit(col, 0.1), skip=("nz",))
    m.box((w - 0.04, d - 0.05, t), Mc @ T(0, -0.005, t / 2), vlib.RW("wood"), jit(col, 0.1), skip=("nz",))
    # the wedge under the tilted crate's back
    m.box((w - 0.06, 0.04, 0.05), M @ T(0, d / 2 - 0.06, h_stand + 0.022), vlib.RW("wood"), jit(col, 0.1), skip=("nz",))
    return Mc @ T(0, -0.005, t)


def rod(m, x0, x1, col=C("6a4a2c")):
    from set_deco import rod as _rod
    _rod(m, x0, x1, col)


def hang_string(m, x, drop, col=C("e8dcc0"), y=None):
    from set_deco import ROD_Y, ROD_Z
    y = ROD_Y if y is None else y
    m.tube([(x, y, ROD_Z - 0.008), (x, y, ROD_Z - drop)], 0.0015, 3, "sw_satin", None, col)
    return Vector((x, y, ROD_Z - drop))


def heap(m, M, r, h, region, col, mat="glaze", n=None):
    n = n or seg(8, 5)
    m.lathe([(r, 0.0), (r * 0.7, h * 0.6), (0.0, h)], n, region, M, col, mat, v_by="z")


def side_x(key, front=True):
    """The front crate's x: at the right-hand corner of the counter, seen from the lane (+x)."""
    return WIDTH[key] / 2 - 0.34


def shelf_set(key, fn, seed):
    def build():
        s = vlib.PropSet(f"prop_deco_{key}_shelf", "slot_shelf_1", STALL_ID[key],
                         footprint=(WIDTH[key] - 0.3, 0.3))
        fn(s, WIDTH[key] / 2 - 0.22)
        return finish_deco(s, key, getattr(s, "fx", None))
    return dict(fn=build, slot="slot_shelf_1", stall=STALL_ID[key], kind="shelf", section=False, seed=seed,
                label=f"{key} shelves", width=WIDTH[key], fill=True)


def front_set(key, fn, seed):
    def build():
        s = vlib.PropSet(f"prop_deco_{key}_front", "slot_front", STALL_ID[key], footprint=(0.5, 0.4))
        fn(s, side_x(key))
        return finish_deco(s, key, getattr(s, "fx", None))
    return dict(fn=build, slot="slot_front", stall=STALL_ID[key], kind="front", section=False, seed=seed,
                label=f"{key} front", width=1.0, fill=True, seat="ground")


def row_x(hw, n, margin=0.0):
    return [-hw + margin + (2 * (hw - margin)) * (i + 0.5) / n for i in range(n)]


# ================================================================== Lebkuchen
def lebkuchen_shelf(s, hw):
    from set_deco import heart_poly, irng, lebkuchen_heart
    m = s.static
    y = 0.02
    # shelf 1: stacks of printed cartons (Elisen-Lebkuchen, Printen), a row of round tins, a basket of small
    # hearts in the middle
    for i, x in enumerate((-hw + 0.12, -hw + 0.34, -hw + 0.56, hw - 0.56, hw - 0.34, hw - 0.12)):
        reg = "bx_lebkuchen" if i < 3 else "bx_printen"
        for j in range(3 if i % 2 == 0 else 2):
            carton(m, T(x + drng.uniform(-0.01, 0.01), y + 0.02, j * 0.05, rz=drng.uniform(-0.05, 0.05)), 0.2, 0.13,
                   0.05, reg)
    with item(s, "lebkuchen", "box_0", (-0.35, -0.04, 0.0), "Elisen-Lebkuchen, 200 g · 7,50 €", "lift",
              "A red and gold carton of Elisen-Lebkuchen, Nuremberg style: soft round gingerbread with almonds and "
              "hazelnuts on a wafer, half of them glazed in chocolate.") as bm:
        carton(bm, T(-0.35, -0.04, 0.0, rz=0.12), 0.2, 0.13, 0.05, "bx_lebkuchen")
        carton(bm, T(-0.35, -0.04, 0.05, rz=0.05), 0.2, 0.13, 0.05, "bx_lebkuchen")
    with item(s, "lebkuchen", "box_1", (0.35, -0.04, 0.0), "Aachener Printen, 250 g · 6 €", "lift",
              "A blue carton of Aachener Printen: hard, spiced honey gingerbread bars from Aachen, with herbs and "
              "rock sugar baked in.") as bm:
        carton(bm, T(0.35, -0.04, 0.0, rz=-0.1), 0.2, 0.13, 0.05, "bx_printen")
    G.crate(m, T(0.0, 0.02, 0), 0.34, 0.22, 0.06, C("b48c5c"), slats=1)
    for k in range(5 if not vlib.lite() else 3):
        lebkuchen_heart(m, T(-0.12 + k * 0.06, 0.0 + (k % 2) * 0.05, 0.05, rx=-1.0, rz=drng.uniform(-0.2, 0.2)), 0.1, k)
    # shelf 2: the menu board in the middle, big hearts on ribbons leaning against the wall either side
    menu_board(m, T(0.0, 0.1, SHELF2), 0.38, 0.28, "mn_lebkuchen")
    for k, x in enumerate((-hw + 0.2, -hw + 0.5, hw - 0.5, hw - 0.2)):
        size = (0.26, 0.22, 0.22, 0.26)[k]
        M = T(x, 0.1, SHELF2 + size * 0.5 + 0.005, rx=math.pi / 2 - 0.15, rz=irng("lks", k).uniform(-0.05, 0.05))
        if k in (0, 3):
            low = (x, 0.1 - 0.02, SHELF2)
            with item(s, "lebkuchen", f"heart_{20 + k}", low, f"Großes Lebkuchenherz", "lift",
                      "A big Lebkuchen heart, 26 cm across, piped with a lace border and a greeting: the one to hang "
                      "by the door at home. 9 €.", icing=("Frohe Weihnachten", None, None, "Ich liebe Dich")[k],
                      size_cm=26) as hm:
                lebkuchen_heart(hm, M @ T(0, 0, -0.006), size, (1, 0, 0, 0)[k])
        else:
            lebkuchen_heart(m, M @ T(0, 0, -0.006), size, k + 2)
    from set_deco import gift_box
    for k, x in enumerate((-0.32, 0.32)):
        for j in range(2):
            gift_box(m, T(x, 0.04, SHELF2 + j * 0.06, rz=0.1 * (j - 0.5)), 0.16, 0.12, 0.06,
                     C(("e8dcc0", "c8a878")[j]), ribbon=C(("b0282a", "2a6a3a")[(k + j) % 2]))


def lebkuchen_front(s, x):
    from set_deco import lebkuchen_heart
    m = s.static
    Mc = stand_crate(m, T(x, 0.62, 0), stencil="cr_markt", tilt=0.25)
    for k in range(4 if not vlib.lite() else 2):
        carton(m, Mc @ T(-0.14 + k * 0.095, 0.03, 0.0, rx=-0.5, rz=drng.uniform(-0.1, 0.1)), 0.09, 0.03, 0.12,
               ("bx_lebkuchen", "bx_printen")[k % 2])
    with item(s, "lebkuchen", "heart_24", tuple(Mc @ Vector((0.1, -0.06, 0.0))), "Lebkuchenherz „Für Dich“", "lift",
              "A small Lebkuchen heart on a ribbon, “Für Dich” (for you) in white icing, lying in the crate at the "
              "front for passers-by. 3 €.", icing="Für Dich", size_cm=12) as hm:
        lebkuchen_heart(hm, Mc @ T(0.1, -0.06, 0.012, rx=0.0, rz=0.3), 0.12, 2)


# ================================================================== Gebrannte Mandeln
def mandeln_rail(s, W):
    """A rod under the header with striped paper bags of almonds tied on ribbons."""
    m = s.static
    rod(m, -W / 2 + 0.25, W / 2 - 0.25)
    xs = (-1.2, -1.02, -0.84, 0.84, 1.02, 1.2)
    for i, x in enumerate(xs):
        drop = 0.16 + (i % 3) * 0.05
        if i in (1, 4):
            with item(s, "mandeln", f"bag_{i}", (x, -0.03, 1.08), "Tüte gebrannte Mandeln, 200 g", "swing",
                      "A striped paper bag of gebrannte Mandeln tied to the rail with a red ribbon: 200 g, still "
                      "warm, 6 €.", pivot="hang") as bm:
                p = hang_string(bm, x, drop, C("b0282a"))
                carton(bm, T(p.x, p.y, p.z - 0.15), 0.09, 0.05, 0.15, "bag_mandeln", side=(0.0, 0.2, 0.1, 0.8))
        else:
            p = hang_string(m, x, drop, C("b0282a"))
            carton(m, T(p.x, p.y, p.z - 0.15, rz=drng.uniform(-0.2, 0.2)), 0.09, 0.05, 0.15, "bag_mandeln",
                   side=(0.0, 0.2, 0.1, 0.8))


def mandeln_shelf(s, hw):
    m = s.static
    # shelf 1: jars of Zuckermandeln, gift cartons, striped bags in a row
    for i, x in enumerate(row_x(hw, 8, 0.05)):
        if i in (3, 4):
            continue
        jar(m, T(x, 0.03, 0.0), "lb_mandel", C(("8a3e1a", "c89a70", "5a2a14")[i % 3]), h=0.12, r=0.04,
            lid=C(("b0282a", "d8b048")[i % 2]))
    with item(s, "mandeln", "jar_0", (-0.12, -0.02, 0.0), "Glas Zuckermandeln, 250 g", "lift",
              "A jar of Zuckermandeln: whole almonds in a smooth sugar shell, pastel and white, 250 g for 5 €.") as jm:
        jar(jm, T(-0.12, -0.02, 0.0), "lb_mandel", C("f0e0e8"), h=0.12, r=0.04, lid=C("d8b048"))
    for j in range(2):
        carton(m, T(0.12, 0.02, j * 0.06, rz=0.06 * (j - 0.5)), 0.19, 0.13, 0.06, "bx_mandeln")
    # shelf 2: the menu board, the striped bags stood up in rows, a copper pan hung on the wall
    menu_board(m, T(0.0, 0.1, SHELF2), 0.38, 0.28, "mn_mandeln")
    for side in (-1, 1):
        for k in range(5 if not vlib.lite() else 3):
            x = side * (0.36 + k * 0.1)
            carton(m, T(x, 0.03 + (k % 2) * 0.04, SHELF2, rz=drng.uniform(-0.1, 0.1)), 0.08, 0.05, 0.14, "bag_mandeln",
                   side=(0.0, 0.2, 0.1, 0.8))
    for k, x in enumerate((-hw + 0.1, hw - 0.1)):
        carton(m, T(x, 0.03, SHELF2), 0.18, 0.12, 0.07, "bx_mandeln")


def mandeln_front(s, x):
    m = s.static
    M = T(x, 0.62, 0)
    sack(m, M, 0.13, 0.36, "sk_mandeln", heap=C("c89a70"), heap_region="almonds")
    with item(s, "mandeln", "scoop_0", (x - 0.02, 0.6, 0.36), "Schaufel rohe Mandeln", "lift",
              "A steel scoop in the sack of raw Californian almonds, before the sugar and the copper kettle.") as sm:
        sm.lathe([(0.0, 0.0), (0.035, 0.0), (0.04, 0.03), (0.0, 0.035)], seg(8, 6), "steel", T(x - 0.02, 0.6, 0.36, rx=0.5),
                 WHITE)
        sm.cyl(0.006, 0.006, 0.1, 5, vlib.RW("wood"), T(x - 0.02, 0.575, 0.395, rx=-1.0), C("5a3622"))
    sack(m, T(x - 0.3, 0.7, 0, rz=0.4), 0.1, 0.26, "sk_mandeln")


# ================================================================== Kerzen
def kerzen_shelf(s, hw):
    m = s.static
    cols = ["b0282a", "f2ead8", "2a6a3a", "d8b048", "2a4a8a", "7a3a7a", "e8d0a0", "c0562a", "f4f0e8", "5a8ab0"]
    # shelf 1: three rows of pillar candles in colours, getting taller toward the back
    n = 9 if not vlib.lite() else 5
    for row in range(3 if not vlib.lite() else 2):
        for i, x in enumerate(row_x(hw, n, 0.04)):
            r = 0.03 + 0.01 * ((i + row) % 3)
            h = 0.09 + row * 0.05 + 0.03 * ((i * 7 + row) % 3)
            candle(m, T(x + drng.uniform(-0.01, 0.01), -0.07 + row * 0.08, 0.0), r, h,
                   jit(C(cols[(i * 3 + row) % len(cols)]), 0.04))
    with item(s, "kerzen", "candle_20", (0.0, -0.075, 0.0), "Kerze: Bienenwachs-Stumpen", "flame",
              "A thick beeswax pillar candle, honey-coloured, 15 cm: it burns slowly and smells of honey. 12 €.",
              colour="honey beeswax") as cm:
        cm.lathe([(0.04, 0.0), (0.04, 0.146), (0.035, 0.15)], seg(8, 6), "honeycomb", T(0.0, -0.075, 0.0), C("e8b050"),
                 "atlas", cap1=True)
    s.fx = {"act_kerzen_candle_20": ("flame", (0.0, 0.0, 0.165))}
    # shelf 2: boxed Christbaumkerzen, scented candles in jars, the menu
    menu_board(m, T(0.0, 0.1, SHELF2), 0.34, 0.26, "mn_kerzen")
    for k, x in enumerate((-hw + 0.12, -hw + 0.34, hw - 0.34, hw - 0.12)):
        for j in range(2 if k % 2 == 0 else 1):
            carton(m, T(x, 0.05, SHELF2 + j * 0.045, rz=drng.uniform(-0.05, 0.05)), 0.19, 0.1, 0.045, "bx_kerzen")
    for k, x in enumerate((-0.42, -0.32, 0.32, 0.42)):
        jar(m, T(x, 0.0, SHELF2), ("lb_lavendel", "lb_tanne")[k % 2], C(("c8b0e0", "4a7a4a")[k % 2]), h=0.09, r=0.036,
            lid=C("c8c8c8"))
    with item(s, "kerzen", "jar_0", (0.23, -0.02, SHELF2), "Duftkerze Tanne", "flame",
              "A fir-scented candle poured into a glass: the smell of a forest in December. 6,50 €.") as jm:
        jar(jm, T(0.23, -0.02, SHELF2), "lb_tanne", C("4a7a4a"), h=0.09, r=0.036, lid=C("c8c8c8"))
    s.fx["act_kerzen_jar_0"] = ("flame", (0.0, 0.0, 0.11))


def kerzen_front(s, x):
    m = s.static
    Mc = stand_crate(m, T(x, 0.62, 0), stencil="cr_markt", tilt=0.25)
    k = 0
    for i in range(4 if not vlib.lite() else 2):
        Mb = Mc @ T(-0.15 + i * 0.1, 0.02, 0.018, rx=-math.pi / 2 + 0.25)
        for j in range(4 if not vlib.lite() else 3):
            a = TWO_PI * j / 4
            m.cyl(0.009, 0.009, 0.24, 5, vlib.RW("wax"), Mb @ T(0.011 * math.cos(a), 0.011 * math.sin(a), -0.12),
                  jit(C(("e8b050", "f2ead8", "b0282a", "2a6a3a")[i % 4]), 0.05), caps=False)
            k += 1
        m.cyl(0.024, 0.024, 0.012, 6, "sw_satin", Mb @ T(0, 0, -0.01), C("b0282a"), caps=False)
    with item(s, "kerzen", "candle_21", tuple(Mc @ Vector((0.16, -0.05, 0.0))), "Kerze: gezogene Bienenwachskerzen",
              "lift", "A pair of hand-dipped beeswax tapers tied at the wick, ready to hang on the tree or a candle "
              "stick: 4 € the pair.") as cm:
        for dx in (-0.012, 0.012):
            cm.cyl(0.009, 0.007, 0.22, seg(6, 5), vlib.RW("wax"), Mc @ T(0.16 + dx, -0.05, 0.012, rx=-math.pi / 2 + 0.2)
                   @ T(0, 0, -0.11), C("e8b050"), caps=False)


# ================================================================== Holzspielzeug
def spielzeug_rail(s, W):
    from set_deco import star_poly
    m = s.static
    rod(m, -W / 2 + 0.25, W / 2 - 0.25)
    cols = ["d8b078", "b0282a", "2a6a3a", "d8b048", "1f3a78"]
    for i, x in enumerate((-1.15, -0.98, -0.8, 0.8, 0.98, 1.15)):
        drop = 0.12 + (i % 3) * 0.06
        if i in (1, 4):
            continue
        p = hang_string(m, x, drop)
        m.extrude(star_poly(0.06, 0.026, 5), 0.008, T(p.x, p.y, p.z - 0.055, rx=math.pi / 2), vlib.RW("wood"),
                  vlib.RW("wood"), C(cols[i % 5]), back=False)
    with item(s, "spielzeug", "plane_0", (-0.98, -0.03, 1.08), "Holzflugzeug", "spin",
              "A little wooden biplane painted red and cream, hanging from the rail on a string: give it a nudge "
              "and it turns. 12 €.", pivot="hang") as pm:
        p = hang_string(pm, -0.98, 0.14)
        Mp = T(p.x, p.y, p.z - 0.03)
        red, cream = vlib.R("toy_paint", (0.02, 0.1, 0.1, 0.9)), vlib.R("toy_paint", (0.52, 0.1, 0.6, 0.9))
        pm.box((0.16, 0.035, 0.035), Mp, red, WHITE, MK)
        for dz in (-0.022, 0.022):
            pm.box((0.05, 0.2, 0.006), Mp @ T(0.02, 0, dz), cream, WHITE, MK)
        pm.box((0.004, 0.07, 0.012), Mp @ T(-0.082, 0, 0), "sw_satin", C("1a1a1a"))


def figure(m, M, coat, hat, s=1.0):
    """A small turned wooden soldier / figure: base, body, head, hat (about 40 triangles)."""
    n = seg(6, 5)
    S = M @ Matrix.Diagonal((s, s, s, 1))
    m.cyl(0.03, 0.03, 0.012, n, vlib.RW("wood"), S, C("2a6a3a"), caps=False)
    m.lathe([(0.028, 0.012), (0.026, 0.09), (0.018, 0.1)], n, "sw_gloss", S, coat, "glaze")
    m.lathe([(0.018, 0.1), (0.02, 0.118), (0.016, 0.135)], n, "sw_gloss", S, C("f0c8a0"), "glaze")
    m.lathe([(0.018, 0.133), (0.018, 0.165), (0.0, 0.168)], n, "sw_gloss", S, hat, "glaze")


def toy_car(m, M, col):
    m.box((0.12, 0.05, 0.035), M @ T(0, 0, 0.032), "sw_gloss", col, "glaze", skip=("nz",))
    m.box((0.06, 0.046, 0.03), M @ T(-0.01, 0, 0.064), "sw_gloss", C("f2ead8"), "glaze", skip=("nz",))
    for sx in (-0.035, 0.035):
        m.disc(0.015, seg(6, 5), "sw_satin", M @ T(sx, -0.026, 0.015, rx=math.pi / 2), C("1a1a1a"))


def spielzeug_shelf(s, hw):
    m = s.static
    # shelf 1: boxed building blocks and puzzles, cars, a row of figures at the front
    for k, x in enumerate((-hw + 0.12, -hw + 0.34, hw - 0.34, hw - 0.12)):
        for j in range(2 if k % 2 == 0 else 1):
            carton(m, T(x, 0.06, j * 0.07, rz=drng.uniform(-0.04, 0.04)), 0.2, 0.12, 0.07,
                   ("bx_baukasten", "bx_puzzle")[(k + j) % 2])
    for k, x in enumerate((-0.5, 0.42)):
        toy_car(m, T(x, -0.05, 0.0, rz=0.15 * (k - 1)), C(("b0282a", "1f3a78", "d8b048")[k]))
    with item(s, "spielzeug", "car_0", (0.6, -0.05, 0.0), "Holzauto", "roll",
              "A turned wooden car in green lacquer with black wheels that really turn. 9 €.") as cm:
        toy_car(cm, T(0.6, -0.05, 0.0), C("2a6a3a"))
    for k, x in enumerate((-0.15, 0.0, 0.15)):
        figure(m, T(x, 0.02, 0.0, rz=0.2 * k), C(("a8181c", "1f3a78", "2a6a3a")[k % 3]), C("141414"), 1.2)
    # shelf 2: the menu, Spanbaum shaving trees, a box of blocks
    menu_board(m, T(0.0, 0.1, SHELF2), 0.36, 0.27, "mn_spielzeug")
    from set_deco import spanbaum
    for k, x in enumerate((-hw + 0.15, -hw + 0.33, hw - 0.33, hw - 0.15)):
        if vlib.lite() and k % 2:
            continue
        spanbaum(m, T(x, 0.03, SHELF2, rz=k), h=0.14 + (k % 3) * 0.04, col=C(["e8d0a0", "d8e0c0", "e0c8a0"][k % 3]))
    with item(s, "spielzeug", "figure_0", (0.25, 0.0, SHELF2), "Holzfigur: Bergmann", "lift",
              "A turned wooden miner (Bergmann) with a lamp, the figure every Erzgebirge window shows at "
              "Christmas. 18 €.") as fm:
        figure(fm, T(0.25, 0.0, SHELF2), C("1a1a1a"), C("1a1a1a"), 1.4)
        fm.cyl(0.008, 0.008, 0.01, 6, "sw_satin", T(0.25 + 0.032, -0.01, SHELF2 + 0.13), WHITE, "flame")


def spielzeug_front(s, x):
    m = s.static
    Mc = stand_crate(m, T(x, 0.62, 0), stencil="cr_erzgebirge", tilt=0.2)
    cols = ["b0282a", "2a6a3a", "1f3a78", "d8b048", "f2ead8", "c0562a", "5a8ab0", "e8d0a0"]
    for k in range(8 if not vlib.lite() else 4):
        m.box((0.05, 0.05, 0.05), Mc @ T(-0.16 + (k % 4) * 0.075 + drng.uniform(-0.01, 0.01), -0.07 + (k // 4) * 0.08,
                                          0.025 + (k // 4) * 0.01, rz=drng.uniform(-0.4, 0.4)), vlib.RW("wood"),
              C(cols[k]), skip=("nz",))
    with item(s, "spielzeug", "top_3", tuple(Mc @ Vector((0.14, 0.06, 0.0))), "Kreisel", "spin",
              "A big turned spinning top in blue and yellow stripes, from the crate at the front: 6 €.") as tm:
        from set_deco import top as _top
        _top(tm, Mc @ T(0.14, 0.06, 0.0), C("1f3a78"))


# ================================================================== Käse
def kaese_rail(s, W):
    m = s.static
    rod(m, -W / 2 + 0.25, W / 2 - 0.25)
    for i, x in enumerate((-1.05, -0.9, -0.75, 0.75, 0.9, 1.05)):
        drop = 0.12 + (i % 2) * 0.04
        name = ("scamorza_0", None, "scamorza_1", None, "scamorza_2", None)[i]
        M = None

        def pear(mm, p):
            mm.lathe([(0.0, -0.17), (0.045, -0.15), (0.05, -0.1), (0.03, -0.05), (0.012, -0.025), (0.0, 0.0)],
                     6, "cheese_rind", T(p.x, p.y, p.z), C(("e8c070", "a86a2a")[i % 2]), "atlas")
            mm.tube([(p.x, p.y, p.z - 0.02), (p.x + 0.004, p.y - 0.01, p.z - 0.03), (p.x, p.y - 0.006, p.z - 0.045)],
                    0.003, 3, "sw_satin", None, C("e8dcc0"))
        if name:
            with item(s, "kaese", name, (x, -0.03, 1.08), ("Räucher-Scamorza", "Scamorza", "Räucher-Scamorza")[i // 2],
                      "swing", "A pear-shaped pasta-filata cheese tied with string, hung to dry; the brown ones "
                      "are smoked over beech. 4,50 €.", pivot="hang") as cm:
                pear(cm, hang_string(cm, x, drop))
        else:
            pear(m, hang_string(m, x, drop))


def kaese_shelf(s, hw):
    m = s.static
    # shelf 1: wheels stacked two high with their paper labels, a block of butter cheese under a cover
    rinds = [C("e8c070"), C("d8b070"), C("c8904a"), C("f0d890"), C("b87a3a")]
    for i, x in enumerate(row_x(hw, 7, 0.04)):
        if i == 3:
            continue
        r = 0.13 if i % 2 == 0 else 0.11
        wheel(m, T(x, 0.0, 0.0, rz=drng.uniform(0, 6)), r, 0.09, rinds[i % 5], label_k=i % 4)
        if i % 3 != 1:
            wheel(m, T(x + drng.uniform(-0.01, 0.01), 0.0, 0.09, rz=drng.uniform(0, 6)), r * 0.85, 0.08, rinds[(i + 2) % 5],
                  label_k=(i + 1) % 4)
    with item(s, "kaese", "cheese_20", (0.0, 0.0, 0.0), "Käse: Emmentaler-Laib", "cut",
              "A small Allgäuer Emmentaler loaf with its paper label: mild, nutty, with big holes. Cut to order, "
              "100 g for 2,90 €.") as cm:
        wheel(cm, T(0.0, 0.0, 0.0), 0.12, 0.1, C("f0d890"), label_k=1, n=10 if not vlib.lite() else 8)
    # shelf 2: the menu, jars of Feigensenf and honey, Käse-Präsent cartons
    menu_board(m, T(0.0, 0.1, SHELF2), 0.36, 0.27, "mn_kaese")
    for k, x in enumerate((-hw + 0.1, -hw + 0.2, -hw + 0.3, hw - 0.3, hw - 0.2, hw - 0.1)):
        jar(m, T(x, 0.0, SHELF2), ("lb_senf", "lb_honey")[k % 2], C(("6a3a1a", "d89a2a")[k % 2]), h=0.1, r=0.034,
            lid=C(("d8b048", "2a5a2a")[k % 2]))
    for k, x in enumerate((-0.35, 0.35)):
        carton(m, T(x, 0.04, SHELF2), 0.19, 0.12, 0.09, "bx_kaese")
    with item(s, "kaese", "jar_0", (-0.5, -0.03, SHELF2), "Glas Feigensenf", "lift",
              "A jar of fig mustard (Feigensenf), sweet and hot: what the Allgäu puts beside a strong cheese. "
              "4,50 €.") as jm:
        jar(jm, T(-0.5, -0.03, SHELF2), "lb_senf", C("6a3a1a"), h=0.1, r=0.034, lid=C("d8b048"))


def kaese_front(s, x):
    m = s.static
    Mc = stand_crate(m, T(x, 0.62, 0), stencil="cr_allgaeu", tilt=0.18)
    for k in range(2):
        wheel(m, Mc @ T(-0.11 + k * 0.2, 0.0, 0.0, rx=0.0), 0.09, 0.07, C(("e8c070", "c8904a")[k]), label_k=k * 2)
    with item(s, "kaese", "cheese_21", tuple(Mc @ Vector((0.0, -0.08, 0.07))), "Käse: Allgäuer Bergkäse, halber Laib",
              "cut", "Half a small Bergkäse wheel lying in the crate at the front, its label up: 600 g for 19 €.") as cm:
        wheel(cm, Mc @ T(0.0, -0.08, 0.07), 0.08, 0.06, C("d8b070"), label_k=0, n=10 if not vlib.lite() else 8)


# ================================================================== Crêpes
def crepes_rail(s, W):
    """Paper bunting along a string under the header, and the chalk menu hung in the middle."""
    from set_deco import ROD_Y, ROD_Z
    m = s.static
    x0, x1 = -W / 2 + 0.2, W / 2 - 0.2
    n = 16 if not vlib.lite() else 8
    pts = [(x0 + (x1 - x0) * i / n, ROD_Y, ROD_Z - 0.02 - 0.05 * math.sin(math.pi * i / n)) for i in range(n + 1)]
    m.tube(pts, 0.0015, 3, "sw_satin", None, C("e8dcc0"))
    cols = ["2a4a8a", "f4f0e8", "b0282a"]
    for i in range(n):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        c = (a + b) / 2
        m.add([(a.x + 0.01, a.y, a.z), (b.x - 0.01, b.y, b.z), (c.x, c.y, c.z - 0.09)], [(0, 1, 2)],
              [[(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]], None, C(cols[i % 3]), "atlas")
    for x in (-1.0, 1.0):
        m.box((0.02, 0.02, 0.07), T(x, ROD_Y, ROD_Z + 0.035), vlib.RW("wood"), C("6a4a2c"))


def crepes_shelf(s, hw):
    m = s.static
    # shelf 1: a flour sack, jars of nougat, apple purée and cinnamon sugar, stacked plates, egg cartons
    sack(m, T(-hw + 0.15, 0.02, 0.0), 0.11, 0.3, "sk_mehl")
    for k, x in enumerate((-hw + 0.38, -hw + 0.48, -hw + 0.58, -0.25, -0.15, 0.15, 0.25)):
        lab = ("lb_nougat", "lb_apfel", "lb_zucker")[k % 3]
        jar(m, T(x, 0.02, 0.0), lab, C(("3a1a0a", "d8b060", "c8905a")[k % 3]), h=0.11, r=0.036,
            lid=C(("d8b048", "b0282a", "2a4a8a")[k % 3]))
    for k, x in enumerate((hw - 0.42, hw - 0.18)):
        for j in range(6 if not vlib.lite() else 2):
            m.lathe([(0.1, j * 0.008), (0.115, j * 0.008 + 0.01)], seg(10, 6), "ceramic", T(x, 0.0, 0.0), C("f4f0e8"),
                    "glaze", cap1=(j == 5 or vlib.lite()))
    for j in range(2):
        m.box((0.3, 0.1, 0.06), T(0.0, 0.03, 0.03 + j * 0.06, rz=0.04 * j), "paper", C("c8b8a0"), skip=("nz", "py"))
    with item(s, "crepes", "jar_2", (0.45, -0.04, 0.0), "Glas Kirsch-Konfitüre", "lift",
              "A jar of sour-cherry jam (Kirsch-Konfitüre) for the jam crêpes. 3,50 € a crêpe, 4 € the jar.") as jm:
        jar(jm, T(0.45, -0.04, 0.0), "lb_kirsch", C("6a0a14"), h=0.1, r=0.036, lid=C("b0282a"))
    # shelf 2: the big menu board, jam jars, a stack of paper cones for the crêpes
    menu_board(m, T(0.0, 0.1, SHELF2), 0.44, 0.33, "mn_crepes", lean=0.14)
    for k, x in enumerate((-hw + 0.1, -hw + 0.2, -hw + 0.3, hw - 0.3, hw - 0.2)):
        jar(m, T(x, 0.0, SHELF2), ("lb_kirsch", "lb_pflaume")[k % 2], C(("6a0a14", "3a1a3a")[k % 2]), h=0.1, r=0.034,
            lid=C(("b0282a", "6a2a6a")[k % 2]))
    for k in range(5 if not vlib.lite() else 2):
        m.lathe([(0.004, 0.0), (0.04, 0.17)], seg(8, 5), "paper", T(hw - 0.1, 0.0, SHELF2 + k * 0.012), C("f4f0e8"))


def crepes_front(s, x):
    m = s.static
    Mc = stand_crate(m, T(x, 0.62, 0), stencil="cr_pfalz", tilt=0.22)
    for k in range(9 if not vlib.lite() else 4):
        col = C(("b8282a", "d8b030", "c8402a")[k % 3]) if k % 4 else C("e8d040")
        m.sphere(0.036, seg(7, 5), seg(4, 3), "sw_satin", Mc @ T(-0.15 + (k % 5) * 0.075, -0.07 + (k // 5) * 0.09,
                                                                  0.036 + (k // 5) * 0.012), jit(col, 0.06),
                 scale=(1, 1, 0.92))
    with item(s, "crepes", "lemon_0", tuple(Mc @ Vector((0.13, 0.06, 0.0))), "Zitrone", "lift",
              "A lemon from the crate at the front: half of it goes on a lemon-and-sugar crêpe.") as lm:
        lm.sphere(0.034, seg(8, 6), seg(5, 4), "sw_satin", Mc @ T(0.13, 0.06, 0.03), C("e8d040"), scale=(1.25, 1, 0.9))


# ================================================================== Heiße Maroni
def maroni_rail(s, W):
    m = s.static
    rod(m, -W / 2 + 0.25, W / 2 - 0.25)
    for i, x in enumerate((-0.98, -0.84, 0.84, 0.98)):
        p = hang_string(m, x, 0.1 + (i % 2) * 0.05, C("c8a070"))
        m.box((0.08, 0.05, 0.14), T(p.x, p.y, p.z - 0.07, rz=drng.uniform(-0.2, 0.2)), "kraft_maroni", WHITE,
              faces={"ny": "kraft_maroni"}, skip=("nz",))
    # a little tin lantern hung in the middle with a candle in it
    with item(s, "maroni", "lantern_0", (0.0, -0.03, 1.08), "Laterne", "flame",
              "A pierced tin lantern hung from the rail with a candle in it, so the chestnut man can see his "
              "change after dark.", pivot="hang") as lm:
        p = hang_string(lm, 0.0, 0.1, C("3a3a3a"))
        Ml = T(p.x, p.y, p.z - 0.17)
        lm.cyl(0.05, 0.05, 0.14, seg(8, 6), vlib.RW("iron"), Ml, C("5a5a5a"), caps=False)
        lm.lathe([(0.055, 0.14), (0.0, 0.18)], seg(8, 6), "iron", Ml, C("4a4a4a"))
        lm.cyl(0.053, 0.053, 0.008, seg(8, 6), "iron", Ml, C("4a4a4a"), caps=True)
        lm.cyl(0.012, 0.012, 0.04, 6, "sw_satin", Ml @ T(0, 0, 0.04), WHITE, "flame")
    s.fx = {"act_maroni_lantern_0": ("flame", (0.0, 0.0, -0.21))}


def maroni_shelf(s, hw):
    m = s.static
    # shelf 1: sacks of chestnuts, stacked kraft bags, a box of charcoal
    sack(m, T(-hw + 0.15, 0.02, 0.0), 0.12, 0.3, "sk_maronen", heap=C("c09070"))
    sack(m, T(hw - 0.15, 0.02, 0.0, rz=0.4), 0.12, 0.28, "sk_maronen")
    for k in range(8 if not vlib.lite() else 4):
        x = -0.3 + (k % 4) * 0.2
        for j in range(2):
            m.box((0.13, 0.085, 0.008), T(x, 0.0 + j * 0.002, 0.004 + (k // 4) * 0.02 + j * 0.008, rz=drng.uniform(-0.1, 0.1)),
                  "kraft_maroni", WHITE, skip=("nz",))
    for k, x in enumerate((-0.35, -0.15, 0.15, 0.35)):
        m.box((0.08, 0.05, 0.15), T(x, 0.07, 0.03, rz=drng.uniform(-0.15, 0.15)), "kraft_maroni", WHITE,
              faces={"ny": "kraft_maroni"}, skip=("nz", "py"))
    with item(s, "maroni", "sack_0", (hw - 0.45, 0.0, 0.0), "Sack Maronen aus dem Piemont", "lift",
              "A small sack of raw sweet chestnuts from Piedmont to roast at home: score the shells crosswise first. "
              "500 g for 4 €.") as sm:
        sack(sm, T(hw - 0.45, 0.0, 0.0), 0.075, 0.18, "sk_maronen", heap=C("c09070"), n=8)
    # shelf 2: the menu, a row of tins, a second lantern
    menu_board(m, T(0.0, 0.1, SHELF2), 0.36, 0.27, "mn_maroni")
    for k, x in enumerate((-hw + 0.12, -hw + 0.28, hw - 0.28, hw - 0.12)):
        carton(m, T(x, 0.04, SHELF2), 0.12, 0.1, 0.16, "sk_maronen", side=(0.0, 0.0, 0.2, 0.2))


def maroni_front(s, x):
    m = s.static
    M = T(x, 0.62, 0)
    sack(m, M, 0.15, 0.38, "sk_maronen", heap=C("c09070"))
    for k in range(6 if not vlib.lite() else 3):
        a = TWO_PI * k / 6
        m.cyl(0.035, 0.035, 0.36, 6, vlib.RW("wood"), T(x - 0.32 + 0.04 * math.cos(a), 0.62 + 0.04 * math.sin(a), 0.04,
                                                          ry=math.pi / 2, rz=0.4), C("8a6a44"), caps=True)
    with item(s, "maroni", "chestnut_0", (x + 0.03, 0.58, 0.4), "Eine Marone", "lift",
              "One roasted chestnut on top of the sack, its shell split along the cross the roaster cut into it. "
              "Hot!") as cm:
        from set_deco import chestnut
        chestnut(cm, T(x + 0.03, 0.58, 0.39), 0.02, WHITE)


# ================================================================== Kartoffelpuffer
def puffer_rail(s, W):
    m = s.static
    rod(m, -W / 2 + 0.25, W / 2 - 0.25)

    def braid(mm, x, drop, col, n, r):
        p = hang_string(mm, x, 0.03, C("c8b080"))
        for k in range(n):
            z = p.z - 0.02 - k * drop / n
            mm.lathe([(0.0, -r), (r, -r * 0.2), (r * 0.6, r * 0.6), (0.0, r * 1.2)], 5, "sw_satin",
                     T(p.x + (0.02 if k % 2 else -0.02), p.y, z), jit(col, 0.06), "atlas")
    braid(m, -1.15, 0.3, C("c89a50"), 6 if not vlib.lite() else 3, 0.028)
    braid(m, 1.15, 0.22, C("f0e8d8"), 5 if not vlib.lite() else 3, 0.022)
    with item(s, "puffer", "pan_0", (-0.95, -0.03, 1.08), "Gusseiserne Pfanne", "swing",
              "A small cast-iron pan hung on the rail, black from years of Puffer: it gets heavier every "
              "winter.", pivot="hang") as pm:
        p = hang_string(pm, -0.95, 0.04, C("3a3a3a"))
        pm.cyl(0.008, 0.008, 0.11, 5, "iron", T(p.x, p.y, p.z - 0.12), C("2a2a2a"), caps=False)
        pm.lathe([(0.0, 0.0), (0.09, 0.0), (0.1, 0.03)], 10, "iron", T(p.x, p.y - 0.015, p.z - 0.22, rx=-math.pi / 2),
                 C("2a2a2a"))


def puffer_shelf(s, hw):
    m = s.static
    # shelf 1: oil bottles, applesauce jars, plate stacks; shelf 2: menu, potato sack, cartons of plates
    for k, x in enumerate((-hw + 0.1, -hw + 0.2, -hw + 0.3)):
        bottle(m, T(x, 0.03, 0.0), "lb_oel", C("c8b040"), h=0.27, r=0.033, cap=C("2a5a2a"))
    for k, x in enumerate((-0.3, -0.2, 0.2, 0.3)):
        jar(m, T(x, 0.02, 0.0), "lb_apfel", C("d8b060"), h=0.1, r=0.035, lid=C("b0282a"))
    for x in (hw - 0.4, hw - 0.15):
        m.cyl(0.11, 0.11, 0.08, seg(10, 6), "paper", T(x, 0.0, 0.0), C("f6f2ea"), caps=False)
        m.disc(0.11, seg(10, 6), "paper", T(x, 0.0, 0.08), C("f6f2ea"))
    with item(s, "puffer", "jar_5", (0.0, -0.03, 0.0), "Glas Apfelmus", "lift",
              "A jar of homemade applesauce (Apfelmus), chunky and cinnamon-sweet: the only proper partner for a "
              "Kartoffelpuffer. 3 €.") as jm:
        jar(jm, T(0.0, -0.03, 0.0), "lb_apfel", C("d8b060"), h=0.1, r=0.035, lid=C("b0282a"))
    menu_board(m, T(0.0, 0.1, SHELF2), 0.38, 0.28, "mn_puffer")
    sack(m, T(-hw + 0.17, 0.02, SHELF2), 0.12, 0.3, "sk_kartoffeln")
    for k, x in enumerate((hw - 0.4, hw - 0.16)):
        carton(m, T(x, 0.04, SHELF2), 0.2, 0.12, 0.12, "sk_mehl", side=(0.0, 0.0, 0.15, 0.15))


def puffer_front(s, x):
    from set_wurst import lump
    m = s.static
    Mc = stand_crate(m, T(x, 0.62, 0), stencil="cr_pfalz", tilt=0.2)
    for k in range(7 if not vlib.lite() else 4):
        m.sphere(0.035, seg(6, 5), 3, vlib.R("roll"), Mc @ T(-0.15 + (k % 5) * 0.075 + drng.uniform(-0.01, 0.01),
                                                                      -0.07 + (k // 5) * 0.09, 0.03 + (k // 5) * 0.01,
                                                                      rz=drng.uniform(0, 6)),
                 jit(C("c8a060"), 0.08), scale=(1.25, 0.95, 0.8))
    sack(m, T(x - 0.36, 0.7, 0, rz=0.3), 0.12, 0.32, "sk_kartoffeln")
    with item(s, "puffer", "potato_0", tuple(Mc @ Vector((0.14, 0.06, 0.0))), "Kartoffel", "lift",
              "A floury Pfalz potato from the crate: grated with onion, an egg and a little flour, it becomes a "
              "Puffer.") as pm:
        pm.sphere(0.036, seg(7, 6), seg(4, 4), vlib.R("roll"), Mc @ T(0.14, 0.06, 0.03), C("c8a060"), scale=(1.3, 0.95, 0.8))


# ================================================================== the sets
SETS = {}
for _i, (_k, _sh, _fr) in enumerate((("lebkuchen", lebkuchen_shelf, lebkuchen_front),
                                     ("mandeln", mandeln_shelf, mandeln_front),
                                     ("kerzen", kerzen_shelf, kerzen_front),
                                     ("spielzeug", spielzeug_shelf, spielzeug_front),
                                     ("kaese", kaese_shelf, kaese_front),
                                     ("crepes", crepes_shelf, crepes_front),
                                     ("maroni", maroni_shelf, maroni_front),
                                     ("puffer", puffer_shelf, puffer_front))):
    SETS[f"prop_deco_{_k}_shelf"] = shelf_set(_k, _sh, 300 + _i)
    SETS[f"prop_deco_{_k}_front"] = front_set(_k, _fr, 320 + _i)

RAILS = {"mandeln": mandeln_rail, "spielzeug": spielzeug_rail, "kaese": kaese_rail, "crepes": crepes_rail,
         "maroni": maroni_rail, "puffer": puffer_rail}
