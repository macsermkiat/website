"""Bücherstand goods: two shelves of individual books and the counter.

prop_books_shelf_1 -> slot_shelf_1 of stall_buecher (lower back shelf, eye level; the five named titles)
prop_books_shelf_2 -> slot_shelf_2 of stall_buecher (upper back shelf)
prop_books_counter -> slot_counter of stall_buecher (open books on a stand, a stack, a banker's lamp with
                      its light_lamp empty, a cash box)

Every book is its own node act_book_<n> (numbered across the whole stall: shelf 1 from 0, shelf 2 from
100, counter from 200) with its origin at the middle of its bottom edge, spine facing -Y (the visitor).
The Bücherstand shelves are 2.08 m wide (between the cabinets), so the shelf sets stay within x = +-1.0.
"""
import math

from mathutils import Matrix, Vector

import goods as G
import vendor_atlas
import vlib
from vlib import C, T, WHITE, jit, rng, seg

TWO_PI = 2 * math.pi
NAMED = ["order_of_time", "geb", "feynman_1", "feynman_2", "feynman_3", "being_you", "book_of_why"]
NAMED_SIZE = {"order_of_time": (0.036, 0.215, 0.145), "geb": (0.058, 0.245, 0.17), "feynman_1": (0.05, 0.285, 0.215),
              "feynman_2": (0.05, 0.285, 0.215), "feynman_3": (0.05, 0.285, 0.215), "being_you": (0.042, 0.24, 0.16),
              "book_of_why": (0.044, 0.245, 0.165)}
NAMED_KIND = {"order_of_time": "hard", "geb": "paper", "feynman_1": "hard", "feynman_2": "hard", "feynman_3": "hard",
              "being_you": "hard", "book_of_why": "hard"}


def spine_regions():
    gen = [f"spine_g{i}" for i in range(len(vendor_atlas.GENERIC_TITLES))]
    kinds = {f"spine_g{i}": t[2] for i, t in enumerate(vendor_atlas.GENERIC_TITLES)}
    return gen, kinds


def book(m, w, h, d, spine, kind="hard", M=None, page_col=C("efe6d0")):
    """A book standing on its tail, origin at the bottom-centre of the spine edge's line... centre of the
    footprint's front edge; spine faces -Y, fore-edge +Y, thickness w along X."""
    M = M or Matrix()
    sreg = vlib.R(spine)
    cover = vlib.R(sreg.rect, sub=(0.04, 0.25, 0.12, 0.75))
    edge = vlib.R("pages_edge")
    if vlib.lite():
        m.box((w, d, h), M @ T(0, d / 2, h / 2), cover, WHITE,
              faces={"ny": sreg, "pz": edge, "py": edge}, skip=("nz",))
        return
    if kind == "hard":
        bt = 0.0028                     # board thickness
        ov = 0.003                      # boards overhang the text block
        # boards
        for sx in (-1, 1):
            m.box((bt, d - 0.004, h), M @ T(sx * (w / 2 - bt / 2), d / 2 + 0.002, h / 2), cover, WHITE,
                  skip=("ny",))
        # text block, inset
        m.box((w - 2 * bt, d - ov - 0.006, h - 2 * ov), M @ T(0, d / 2 + 0.002 - ov / 2, h / 2), edge,
              page_col, faces={"pz": edge, "nz": edge, "py": edge}, skip=("ny", "px", "nx"))
        # rounded spine: an arc from board to board bulging toward -Y
        k = 5
        bulge = min(0.012, w * 0.22)
        cols = []
        for i in range(k + 1):
            t = i / k
            x = -w / 2 + w * t
            y = 0.002 - bulge * math.sin(math.pi * t)
            cols.append((x, y))
        verts, faces, uvs = [], [], []
        for i, (x, y) in enumerate(cols):
            verts += [(x, y, 0.0), (x, y, h)]
        for i in range(k):
            a, b = 2 * i, 2 * i + 2
            faces.append((a, b, b + 1, a + 1))
            uvs.append([sreg.uv(i / k, 0), sreg.uv((i + 1) / k, 0), sreg.uv((i + 1) / k, 1), sreg.uv(i / k, 1)])
        m.add(verts, faces, uvs, M, WHITE, "atlas", True)
        # headband: a thin coloured strip at the head of the spine
        m.box((w - 2 * bt, 0.004, 0.003), M @ T(0, 0.005, h - ov - 0.0015), "sw_satin",
              C(rng.choice(["a8261e", "e8d8a8", "2a3a6a", "d8b048"])), skip=("nz",))
    else:
        # paperback: flush soft covers, a square spine
        m.box((w, d, h), M @ T(0, d / 2, h / 2), cover, WHITE,
              faces={"ny": sreg, "pz": edge, "py": edge, "nz": edge}, skip=())


def fill_shelf(s, x0, x1, start, named=(), seed_shift=0, depth_front=-0.12):
    """Books standing along the shelf from x0 to x1, with a few horizontal stacks and a leaning book."""
    gen, kinds = spine_regions()
    order = list(gen)
    rng.shuffle(order)
    idx = start
    x = x0
    named = list(named)
    named_at = {}
    # decide where the named books go: a block near the middle of the run
    if named:
        named_at = {"x": (x0 + x1) / 2 - 0.15}
    gi = 0
    placed_named = False
    stack_at = [x1 - 0.42 + rng.uniform(-0.1, 0.1)] if named else [x0 + 0.5 + rng.uniform(-0.1, 0.1)]
    while x < x1 - 0.02:
        if named and not placed_named and x >= named_at["x"]:
            for key in named:
                w, h, d = NAMED_SIZE[key]
                node = s.node(f"act_book_{idx}", (x + w / 2, depth_front, 0))
                book(node, w, h, d, "spine_" + key, NAMED_KIND[key])
                s.titles[f"act_book_{idx}"] = key
                idx += 1
                x += w + 0.0015
            placed_named = True
            continue
        if stack_at and x >= stack_at[0]:
            # a short stack of books lying flat, spines to the front
            stack_at.pop(0)
            base = x + 0.13
            z = 0.0
            for k in range(rng.randint(3, 5)):
                reg = order[gi % len(order)]
                gi += 1
                w = rng.uniform(0.022, 0.04)
                h = rng.uniform(0.2, 0.25)
                d = rng.uniform(0.14, 0.18)
                if x + h + 0.02 > x1:
                    break
                node = s.node(f"act_book_{idx}", (base + rng.uniform(-0.01, 0.01), depth_front, z + w / 2))
                # lying: rotate so the book's height runs along X and its thickness along Z
                book(node, w, h, d, reg, "hard" if kinds[reg] != "paper" else "paper",
                     Matrix.Rotation(-math.pi / 2, 4, 'Y') @ T(0, 0, -h / 2))
                s.rot[f"act_book_{idx}"] = (0, 0, rng.uniform(-0.05, 0.05))
                s.titles[f"act_book_{idx}"] = reg
                idx += 1
                z += w
            x = base + 0.14
            continue
        reg = order[gi % len(order)]
        gi += 1
        w = rng.uniform(0.02, 0.045)
        aspect = 304 / 48
        h = min(0.3, max(0.17, w * aspect * rng.uniform(0.85, 1.25)))
        if kinds[reg] == "leather":
            h = min(0.3, max(h, 0.22))
        d = min(0.22, max(0.12, h * rng.uniform(0.62, 0.72)))
        if x + w > x1:
            break
        lean = 0.0
        node = s.node(f"act_book_{idx}", (x + w / 2, depth_front + rng.uniform(0.0, 0.015), 0))
        book(node, w, h, d, reg, "paper" if kinds[reg] == "paper" else "hard",
             page_col=C("efe6d0") if kinds[reg] != "leather" else C("d8c8a0"))
        s.titles[f"act_book_{idx}"] = reg
        idx += 1
        x += w + rng.uniform(0.0005, 0.003)
    return idx


def bookend(m, M, col=C("8a6a3a"), side=1):
    """Cast-brass bookend: a base plate under the books and an upright with a rounded top."""
    m.box((0.1, 0.12, 0.004), M @ T(side * 0.05, 0.06, 0.002), "brass", col)
    pts = [(0.0, 0.0), (0.12, 0.0), (0.12, 0.12), (0.09, 0.15), (0.03, 0.15), (0.0, 0.12)]
    R = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    m.extrude(pts, 0.006, M @ T(-0.003, 0, 0) @ R, "brass", "brass", col)


def shelf_set(name, slot, start, named, seed_bias):
    s = vlib.PropSet(name, slot, "buecherstand", footprint=(2.08, 0.3))
    s.titles, s.rot = {}, {}
    x0, x1 = -0.98, 0.98
    idx = fill_shelf(s, x0 + 0.03, x1 - 0.03, start, named)
    bookend(s.static, T(x0, -0.12, 0), side=1)
    bookend(s.static, T(x1, -0.12, 0), side=-1)
    s.finish()
    for k, r in s.rot.items():
        s.objs[k].rotation_euler = r
    return s


def open_book(m, M, w=0.36, d=0.24, thick=0.03, cover=C("6e1a22")):
    """An open book lying on its back: two curved page blocks and the case underneath."""
    k = seg(10, 5)
    reg = vlib.R("pages_open")
    # case (boards) under the pages, a little larger
    m.box((w + 0.012, d + 0.012, 0.004), M @ T(0, 0, 0.002), vlib.R("spine_g5", sub=(0.05, 0.3, 0.12, 0.7)), cover)
    for side in (-1, 1):
        # page block edge: a stack under each page surface
        m.box((w / 2 - 0.012, d - 0.004, thick * 0.6), M @ T(side * (w / 4 + 0.004), 0, 0.004 + thick * 0.3), "pages_edge",
              C("e8dcc0"), skip=("nz",))
    verts, faces, uvs = [], [], []
    rows = 2
    for i in range(2 * k + 1):
        t = i / (2 * k)
        x = -w / 2 + w * t
        u = abs(t - 0.5) * 2
        z = 0.004 + thick * 0.62 + 0.018 * math.sin(math.pi * min(1, u * 1.1)) ** 0.6 - 0.02 * (1 - u) ** 6
        for j in range(rows + 1):
            y = -d / 2 + d * j / rows
            verts.append((x, y, z))
    for i in range(2 * k):
        for j in range(rows):
            a = i * (rows + 1) + j
            b = (i + 1) * (rows + 1) + j
            faces.append((a, b, b + 1, a + 1))
            uvs.append([reg.uv(i / (2 * k), j / rows), reg.uv((i + 1) / (2 * k), j / rows),
                        reg.uv((i + 1) / (2 * k), (j + 1) / rows), reg.uv(i / (2 * k), (j + 1) / rows)])
    m.add(verts, faces, uvs, M, WHITE, "atlas", True)
    # a ribbon bookmark
    m.tube([(0.01, d / 2 - 0.01, 0.045), (0.02, d / 2 + 0.01, 0.02), (0.025, d / 2 + 0.03, 0.004)], 0.002, 4,
           "sw_satin", M, C("8a1a1a"))


def lamp(s, x, y):
    """Banker's lamp: brass base and stem, green cased-glass shade, a warm bulb and a light_lamp empty."""
    m = s.static
    n = seg(24, 12)
    m.lathe([(0.0, 0.0), (0.085, 0.0), (0.09, 0.006), (0.085, 0.018), (0.06, 0.026), (0.02, 0.032), (0.0, 0.032)],
            n, "brass", T(x, y + 0.03, 0), WHITE)
    m.cyl(0.009, 0.009, 0.3, 12, "brass", T(x, y + 0.03, 0.03), WHITE)
    m.cyl(0.006, 0.006, 0.2, 10, "brass", T(x - 0.1, y + 0.03, 0.33, ry=math.pi / 2), WHITE)
    # shade: half an elliptic cylinder, open at the bottom, tilted slightly toward the front
    Ms = T(x, y + 0.01, 0.315, rx=-0.18)
    k = seg(14, 8)
    L = 0.26
    shade_o = [[(xx, 0.075 * math.cos(math.pi * i / k), 0.055 * math.sin(math.pi * i / k)) for i in range(k + 1)]
               for xx in (-L / 2, L / 2)]
    m.loft(shade_o, "sw_gloss", Ms, C("0f4a2a"), "lamp_shade", closed=False)
    shade_i = [[(xx, 0.072 * math.cos(math.pi * i / k), 0.052 * math.sin(math.pi * i / k)) for i in range(k + 1)][::-1]
               for xx in (-L / 2, L / 2)]
    m.loft(shade_i, "sw_satin", Ms, C("f2eee0"), "atlas", closed=False)
    for xx in (-L / 2, L / 2):
        pts = [(xx, 0.075 * math.cos(math.pi * i / k), 0.055 * math.sin(math.pi * i / k)) for i in range(k + 1)]
        m.tube(pts, 0.004, 5, "brass", Ms, WHITE)
    m.cyl(0.018, 0.02, 0.05, 12, "brass", Ms @ T(0, 0, 0.03), WHITE)
    # bulb
    m.sphere(0.024, 12, 8, "sw_satin", Ms @ T(0, 0, 0.012), WHITE, "lamp", scale=(1.8, 1, 1))
    # pull chain
    m.tube([Ms @ Vector((0.05, -0.04, 0.01)), Ms @ Vector((0.05, -0.05, -0.08))], 0.0015, 4, "brass", None, WHITE)
    m.sphere(0.006, 8, 5, "brass", T(*(Ms @ Vector((0.05, -0.05, -0.085)))), WHITE)
    s.empty("light_lamp", tuple(Ms @ Vector((0, 0, -0.01))))


def cash_box(m, M):
    col = C("2f4a3a")
    m.box((0.26, 0.18, 0.09), M @ T(0, 0, 0.045), "sw_satin", col)
    m.box((0.262, 0.182, 0.012), M @ T(0, 0, 0.096), "sw_satin", jit(col, 0.02))
    m.box((0.01, 0.002, 0.022), M @ T(0, -0.091, 0.07), "brass", WHITE)
    m.cyl(0.006, 0.006, 0.003, 10, "brass", M @ T(0, -0.092, 0.07, rx=math.pi / 2), WHITE)
    for sx in (-1, 1):
        m.box((0.03, 0.01, 0.006), M @ T(sx * 0.13 - sx * 0.0, 0, 0.104), "brass", WHITE)
    m.tube([(-0.05, 0, 0.108), (-0.05, 0, 0.13), (0.05, 0, 0.13), (0.05, 0, 0.108)], 0.004, 5, "brass", M, WHITE)
    # a stack of coins and a few loose ones
    for k in range(6):
        m.cyl(0.012, 0.012, 0.002, 12, "brass", M @ T(0.18, -0.02, k * 0.0021), WHITE)
    for dx, dy in ((0.21, 0.03), (0.16, 0.05)):
        m.cyl(0.011, 0.011, 0.002, 12, "sw_metal", M @ T(dx, dy, 0), C("c8c8c8"))


def counter():
    s = vlib.PropSet("prop_books_counter", "slot_counter", "buecherstand", footprint=(2.1, 0.5))
    s.titles, s.rot = {}, {}
    m = s.static
    # reading stand with a big open book
    Ml = T(-0.45, 0.02, 0)
    m.box((0.3, 0.22, 0.012), Ml @ T(0, 0.02, 0.006), vlib.RW("wood"), C("6a4228"))
    m.box((0.38, 0.26, 0.012), Ml @ T(0, 0.02, 0.07, rx=0.45), vlib.RW("wood"), C("7a4a2c"))
    m.box((0.38, 0.02, 0.02), Ml @ T(0, -0.1, 0.022, rx=0.45), vlib.RW("wood"), C("6a4228"))
    m.box((0.02, 0.12, 0.1), Ml @ T(0, 0.1, 0.05), vlib.RW("wood"), C("6a4228"))
    open_book(m, Ml @ T(0, 0.02, 0.078, rx=0.45), w=0.36, d=0.25, cover=C("5a1a1e"))
    # a second open book lying flat, and a pencil across it
    open_book(m, T(0.08, -0.06, 0, rz=0.08), w=0.3, d=0.2, thick=0.022, cover=C("1f2f52"))
    m.cyl(0.0035, 0.0035, 0.17, 6, "sw_satin", T(0.0, -0.1, 0.044, ry=math.pi / 2, rx=0.0, rz=0) @ T(0, 0, 0),
          C("d8a020"))
    # a stack of books lying flat (each still an act_book), and one standing against the lamp
    gen, kinds = spine_regions()
    z = 0.0
    for k, (reg, w, h, d) in enumerate((("spine_g21", 0.032, 0.24, 0.17), ("spine_g4", 0.028, 0.22, 0.15),
                                         ("spine_g30", 0.04, 0.25, 0.18), ("spine_g8", 0.026, 0.2, 0.14))):
        idx = 200 + k
        node = s.node(f"act_book_{idx}", (-0.86 + rng.uniform(-0.01, 0.01), -0.12, z + w / 2))
        book(node, w, h, d, reg, "hard", Matrix.Rotation(-math.pi / 2, 4, 'Y') @ T(0, 0, -h / 2))
        s.rot[f"act_book_{idx}"] = (0, 0, rng.uniform(-0.08, 0.08))
        s.titles[f"act_book_{idx}"] = reg
        z += w
    lamp(s, 0.52, 0.06)
    cash_box(m, T(0.76, 0.02, 0, rz=-0.15))
    s.finish()
    for k, r in s.rot.items():
        s.objs[k].rotation_euler = r
    return s


SETS = {
    "prop_books_shelf_1": dict(fn=lambda: shelf_set("prop_books_shelf_1", "slot_shelf_1", 0, NAMED, 0),
                               slot="slot_shelf_1", stall="buecherstand", kind="shelf", section=True, seed=51,
                               width=2.1, cam=((0.0, -0.95, 0.2), (0.0, 0.0, 0.14), 32)),
    "prop_books_shelf_2": dict(fn=lambda: shelf_set("prop_books_shelf_2", "slot_shelf_2", 100, (), 1),
                               slot="slot_shelf_2", stall="buecherstand", kind="shelf", section=True, seed=52,
                               width=2.1, cam=((0.35, -1.1, 0.25), (0.1, 0.0, 0.14), 32)),
    "prop_books_counter": dict(fn=counter, slot="slot_counter", stall="buecherstand", kind="counter", section=True,
                               seed=53, width=2.2, cam=((-0.05, -1.95, 0.62), (0.0, 0.0, 0.1), 30)),
}
