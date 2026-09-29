"""Bücherstand goods: two shelves of individual books and the counter.

prop_books_shelf_1 -> slot_shelf_1 of stall_buecher (lower back shelf, eye level; the five named titles)
prop_books_shelf_2 -> slot_shelf_2 of stall_buecher (upper back shelf)
prop_books_counter -> slot_counter of stall_buecher (open books on a stand, stacks, a row between
                      bookends, a tray of bookmarks, price cards, a banker's lamp, a cash box)

Every book is its own node act_book_<n> (numbered across the whole stall: shelf 1 from 0, shelf 2 from
100, counter from 200) with its origin at the foot of its spine (standing) or under the middle of its
lowest face (lying), spine facing -Y (the visitor). Each book has one material, book_cover_<n>, that
reads the books atlas; its front cover (the +X board of a standing book, spine on the left as you look
at it) carries the cover art, whose UV rect items.json gives as cover_uv.

The Bücherstand shelves are 2.08 m wide, but diagonal braces stand at x = +-0.95 from 0.22 m up, so the
shelf sets keep to x = +-0.925. Each shelf has a 5 cm front lip at y = -0.14; spines stand just behind it.
The lamp has no light_ empty: the stall already has its two (light_0, light_1). Its bulb is emissive.
"""
import math

from mathutils import Matrix, Vector

import atlas_books
import goods as G
import vendor_atlas
import vlib
from vlib import C, T, WHITE, jit, lite, rng, seg

TWO_PI = 2 * math.pi
NAMED = ["order_of_time", "geb", "feynman_1", "feynman_2", "feynman_3", "being_you", "book_of_why"]
NAMED_SIZE = {"order_of_time": (0.036, 0.215, 0.145), "geb": (0.058, 0.245, 0.17), "feynman_1": (0.05, 0.285, 0.215),
              "feynman_2": (0.05, 0.285, 0.215), "feynman_3": (0.05, 0.285, 0.215), "being_you": (0.042, 0.24, 0.16),
              "book_of_why": (0.044, 0.245, 0.165)}
NAMED_KIND = {"order_of_time": "hard", "geb": "paper", "feynman_1": "hard", "feynman_2": "hard", "feynman_3": "hard",
              "being_you": "hard", "book_of_why": "hard"}
SHELF_X = 0.925
SPINE_Y = -0.118


def spine_kinds():
    return {f"spine_g{i}": t[2] for i, t in enumerate(vendor_atlas.GENERIC_TITLES)}


def book(m, w, h, d, spine, kind, mat, M=None, page_col=C("efe6d0")):
    """A book standing on its tail: origin at the middle of the spine's foot, spine toward -Y,
    fore-edge toward +Y, thickness w along X. Front cover on the +X board (spine on its left)."""
    M = M or Matrix()
    sreg = vlib.R(spine)
    front = vlib.R("cover_" + spine[len("spine_"):])
    plain = vlib.R(sreg.rect, sub=(0.04, 0.25, 0.12, 0.75))
    edge = vlib.R("pages_edge")
    if lite():
        m.box((w, d, h), M @ T(0, d / 2, h / 2), plain, WHITE, mat,
              faces={"ny": sreg, "px": front, "pz": edge, "py": edge}, skip=("nz",))
        return
    if kind == "hard":
        bt = 0.0028                     # board thickness
        ov = 0.003                      # boards overhang the text block
        for sx in (-1, 1):
            m.box((bt, d - 0.004, h), M @ T(sx * (w / 2 - bt / 2), d / 2 + 0.002, h / 2), plain, WHITE, mat,
                  faces={"px": front} if sx > 0 else None, skip=("ny",))
        m.box((w - 2 * bt, d - ov - 0.006, h - 2 * ov), M @ T(0, d / 2 + 0.002 - ov / 2, h / 2), edge,
              page_col, mat, faces={"pz": edge, "nz": edge, "py": edge}, skip=("ny", "px", "nx"))
        # rounded spine: an arc from board to board bulging toward -Y
        k = 4
        bulge = min(0.01, w * 0.2)
        verts, faces, uvs = [], [], []
        for i in range(k + 1):
            t = i / k
            x, y = -w / 2 + w * t, 0.002 - bulge * math.sin(math.pi * t)
            verts += [(x, y, 0.0), (x, y, h)]
        for i in range(k):
            a, b = 2 * i, 2 * i + 2
            faces.append((a, b, b + 1, a + 1))
            uvs.append([sreg.uv(i / k, 0), sreg.uv((i + 1) / k, 0), sreg.uv((i + 1) / k, 1), sreg.uv(i / k, 1)])
        m.add(verts, faces, uvs, M, WHITE, mat, True)
        # headband: a thin coloured strip at the head of the spine
        m.box((w - 2 * bt, 0.004, 0.003), M @ T(0, 0.005, h - ov - 0.0015), "bk_satin",
              C(rng.choice(["a8261e", "e8d8a8", "2a3a6a", "d8b048"])), mat, skip=("nz", "ny"))
    else:
        # paperback: flush soft covers, a square spine
        m.box((w, d, h), M @ T(0, d / 2, h / 2), plain, WHITE, mat,
              faces={"ny": sreg, "px": front, "pz": edge, "py": edge, "nz": edge})


def add_book(s, idx, loc, w, h, d, spine, kind, lying=False, rz=0.0, where="shelf", page_col=C("efe6d0")):
    """One act_book_<idx> node. Lying books rest on their back board with the spine still to the front."""
    name = f"act_book_{idx}"
    mat = f"book:{idx}"
    if lying:
        node = s.node(name, loc, rot=(0, 0, rz))
        # stand-up book turned onto its back cover (-X board down): height runs along X
        book(node, w, h, d, spine, kind, mat, T(0, 0, w / 2) @ Matrix.Rotation(-math.pi / 2, 4, 'Y') @ T(0, 0, -h / 2),
             page_col)
    else:
        node = s.node(name, loc, rot=(0, 0, rz) if rz else None)
        book(node, w, h, d, spine, kind, mat, None, page_col)
    title, author = atlas_books.book_meta(spine)
    s.item(name, title, "book", title=title, author=author, cover_material=f"book_cover_{idx}",
           cover_uv=cover_uv_gltf(spine),
           cover_texture="prop_tex_books_color.webp", where=where)


def cover_uv_gltf(spine):
    """The cover's rect in glTF texture space (origin top-left): [u_min, v_min, u_max, v_max]."""
    u0, v0, u1, v1 = vlib.regions()["cover_" + spine[len("spine_"):]]
    return [round(u0, 5), round(1 - v1, 5), round(u1, 5), round(1 - v0, 5)]


def fill_shelf(s, x0, x1, start, named=()):
    """Books standing along the shelf from x0 to x1, with a horizontal stack; the named block mid-run."""
    kinds = spine_kinds()
    order = list(kinds)
    rng.shuffle(order)
    idx, x, gi = start, x0, 0
    named = list(named)
    named_x = (x0 + x1) / 2 - 0.15
    placed_named = False
    stack_at = [x1 - 0.42 + rng.uniform(-0.1, 0.1)] if named else [x0 + 0.5 + rng.uniform(-0.1, 0.1)]
    while x < x1 - 0.02:
        if named and not placed_named and x >= named_x:
            for key in named:
                w, h, d = NAMED_SIZE[key]
                add_book(s, idx, (x + w / 2, SPINE_Y, 0), w, h, d, "spine_" + key, NAMED_KIND[key])
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
                w, h, d = rng.uniform(0.022, 0.04), rng.uniform(0.2, 0.25), rng.uniform(0.14, 0.18)
                if x + h + 0.02 > x1:
                    break
                add_book(s, idx, (base + rng.uniform(-0.01, 0.01), SPINE_Y, z), w, h, d, reg,
                         "paper" if kinds[reg] == "paper" else "hard", lying=True, rz=rng.uniform(-0.05, 0.05))
                idx += 1
                z += w
            x = base + 0.14
            continue
        reg = order[gi % len(order)]
        gi += 1
        w = rng.uniform(0.02, 0.045)
        h = min(0.3, max(0.17, w * (304 / 48) * rng.uniform(0.85, 1.25)))
        if kinds[reg] == "leather":
            h = min(0.3, max(h, 0.22))
        d = min(0.22, max(0.12, h * rng.uniform(0.62, 0.72)))
        if x + w > x1:
            break
        add_book(s, idx, (x + w / 2, SPINE_Y + rng.uniform(0.0, 0.012), 0), w, h, d, reg,
                 "paper" if kinds[reg] == "paper" else "hard",
                 page_col=C("efe6d0") if kinds[reg] != "leather" else C("d8c8a0"))
        idx += 1
        x += w + rng.uniform(0.0005, 0.003)
    return idx


def bookend(m, M, col=C("8a6a3a"), side=1):
    """Cast-brass bookend: a base plate under the books and an upright with a rounded top."""
    m.box((0.1, 0.12, 0.004), M @ T(side * 0.05, 0.06, 0.002), "brass", col)
    pts = [(0.0, 0.0), (0.12, 0.0), (0.12, 0.12), (0.09, 0.15), (0.03, 0.15), (0.0, 0.12)]
    R = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    m.extrude(pts, 0.006, M @ T(-0.003, 0, 0) @ R, "brass", "brass", col)


def shelf_set(name, slot, start, named):
    s = vlib.PropSet(name, slot, "buecherstand", footprint=(2.08, 0.28))
    fill_shelf(s, -SHELF_X + 0.012, SHELF_X - 0.012, start, named)
    bookend(s.static, T(-SHELF_X, SPINE_Y, 0), side=1)
    bookend(s.static, T(SHELF_X, SPINE_Y, 0), side=-1)
    s.finish()
    return s


def open_book(m, M, w=0.36, d=0.24, thick=0.03, cover=C("6e1a22")):
    """An open book lying on its back: two curved page blocks and the case underneath."""
    k = seg(10, 4)
    reg = vlib.R("pages_open")
    m.box((w + 0.012, d + 0.012, 0.004), M @ T(0, 0, 0.002), vlib.R("spine_g5", sub=(0.05, 0.3, 0.12, 0.7)), cover,
          "books")
    for side in (-1, 1):
        m.box((w / 2 - 0.012, d - 0.004, thick * 0.6), M @ T(side * (w / 4 + 0.004), 0, 0.004 + thick * 0.3),
              "pages_edge", C("e8dcc0"), "books", skip=("nz",))
    verts, faces, uvs = [], [], []
    rows = 2
    for i in range(2 * k + 1):
        t = i / (2 * k)
        x = -w / 2 + w * t
        u = abs(t - 0.5) * 2
        z = 0.004 + thick * 0.62 + 0.018 * math.sin(math.pi * min(1, u * 1.1)) ** 0.6 - 0.02 * (1 - u) ** 6
        for j in range(rows + 1):
            verts.append((x, -d / 2 + d * j / rows, z))
    for i in range(2 * k):
        for j in range(rows):
            a = i * (rows + 1) + j
            b = (i + 1) * (rows + 1) + j
            faces.append((a, b, b + 1, a + 1))
            uvs.append([reg.uv(i / (2 * k), j / rows), reg.uv((i + 1) / (2 * k), j / rows),
                        reg.uv((i + 1) / (2 * k), (j + 1) / rows), reg.uv(i / (2 * k), (j + 1) / rows)])
    m.add(verts, faces, uvs, M, WHITE, "books", True)
    m.tube([(0.01, d / 2 - 0.01, 0.045), (0.02, d / 2 + 0.01, 0.02), (0.025, d / 2 + 0.03, 0.004)], 0.002, 4,
           "sw_satin", M, C("8a1a1a"))


def lamp(m, x, y):
    """Banker's lamp: brass base and stem, green cased-glass shade, a warm emissive bulb (no light_ empty)."""
    n = seg(20, 8)
    m.lathe([(0.0, 0.0), (0.085, 0.0), (0.09, 0.006), (0.085, 0.018), (0.06, 0.026), (0.02, 0.032), (0.0, 0.032)],
            n, "brass", T(x, y + 0.03, 0), WHITE)
    m.cyl(0.009, 0.009, 0.3, 10, "brass", T(x, y + 0.03, 0.03), WHITE)
    m.cyl(0.006, 0.006, 0.2, 8, "brass", T(x - 0.1, y + 0.03, 0.33, ry=math.pi / 2), WHITE)
    Ms = T(x, y + 0.01, 0.315, rx=-0.18)
    k = seg(12, 6)
    L = 0.26
    shade_o = [[(xx, 0.075 * math.cos(math.pi * i / k), 0.055 * math.sin(math.pi * i / k)) for i in range(k + 1)]
               for xx in (-L / 2, L / 2)]
    m.loft(shade_o, "sw_gloss", Ms, C("0f4a2a"), "lamp_shade", closed=False)
    shade_i = [[(xx, 0.072 * math.cos(math.pi * i / k), 0.052 * math.sin(math.pi * i / k)) for i in range(k + 1)][::-1]
               for xx in (-L / 2, L / 2)]
    m.loft(shade_i, "sw_satin", Ms, C("f2eee0"), "atlas", closed=False)
    if not lite():
        for xx in (-L / 2, L / 2):
            pts = [(xx, 0.075 * math.cos(math.pi * i / k), 0.055 * math.sin(math.pi * i / k)) for i in range(k + 1)]
            m.tube(pts, 0.004, 5, "brass", Ms, WHITE)
        m.tube([Ms @ Vector((0.05, -0.04, 0.01)), Ms @ Vector((0.05, -0.05, -0.08))], 0.0015, 4, "brass", None, WHITE)
        m.sphere(0.006, 6, 4, "brass", T(*(Ms @ Vector((0.05, -0.05, -0.085)))), WHITE)
    m.cyl(0.018, 0.02, 0.05, 10, "brass", Ms @ T(0, 0, 0.03), WHITE)
    m.sphere(0.024, 10, 6, "sw_satin", Ms @ T(0, 0, 0.012), WHITE, "lamp", scale=(1.8, 1, 1))


def cash_box(m, M):
    col = C("2f4a3a")
    m.box((0.26, 0.18, 0.09), M @ T(0, 0, 0.045), "sw_satin", col, skip=("nz",))
    m.box((0.262, 0.182, 0.012), M @ T(0, 0, 0.096), "sw_satin", jit(col, 0.02))
    m.box((0.01, 0.002, 0.022), M @ T(0, -0.091, 0.07), "brass", WHITE)
    for sx in (-1, 1):
        m.box((0.03, 0.01, 0.006), M @ T(sx * 0.13, 0, 0.104), "brass", WHITE)
    m.tube([(-0.05, 0, 0.108), (-0.05, 0, 0.13), (0.05, 0, 0.13), (0.05, 0, 0.108)], 0.004, 5, "brass", M, WHITE)
    for k in range(6 if not lite() else 2):
        m.cyl(0.012, 0.012, 0.002, 10, "brass", M @ T(0.18, -0.02, k * 0.0021), WHITE)
    for dx, dy in ((0.21, 0.03), (0.16, 0.05)):
        m.cyl(0.011, 0.011, 0.002, 10, "sw_metal", M @ T(dx, dy, 0), C("c8c8c8"))


def price_card(m, M, k):
    """A folded tent card; k picks one of the four hand-lettered cards in the price_cards region."""
    reg = vlib.R("price_cards", sub=((k % 2) * 0.5, 0.5 - (k // 2) * 0.5, (k % 2) * 0.5 + 0.5, 1.0 - (k // 2) * 0.5))
    w, h, a = 0.1, 0.064, 0.28
    for side in (-1, 1):
        pts = [(-w / 2, side * h * math.sin(a), 0), (w / 2, side * h * math.sin(a), 0),
               (w / 2, 0, h * math.cos(a)), (-w / 2, 0, h * math.cos(a))]
        if side > 0:
            pts = [pts[1], pts[0], pts[3], pts[2]]
        m.quad(pts, reg, WHITE, "atlas", M)


def bookmark_tray(m, M):
    """A shallow wooden tray with printed bookmarks fanned out in it."""
    G.board(m, M, 0.2, 0.14, 0.01, C("8a6440"))
    for sx, sy, w, d in ((0, -0.065, 0.2, 0.01), (0, 0.065, 0.2, 0.01), (-0.095, 0, 0.01, 0.14), (0.095, 0, 0.01, 0.14)):
        m.box((w, d, 0.02), M @ T(sx, sy, 0.02), vlib.RW("wood"), C("7a5434"))
    n = 6 if not lite() else 3
    for k in range(n):
        reg = vlib.R("bookmarks", sub=(k / 6, 0.0, (k + 1) / 6, 1.0))
        Mk = M @ T(-0.07 + k * 0.028, 0.0, 0.0105 + k * 0.0006, rz=0.25 - k * 0.1)
        m.quad([(-0.018, -0.055, 0), (0.018, -0.055, 0), (0.018, 0.055, 0), (-0.018, 0.055, 0)], reg, WHITE, "atlas",
               Mk, uvq=[(0, 0), (1, 0), (1, 1), (0, 1)])


def counter():
    s = vlib.PropSet("prop_books_counter", "slot_counter", "buecherstand", footprint=(2.0, 0.45))
    m = s.static
    kinds = spine_kinds()
    # reading stand with a big open book
    Ml = T(-0.45, 0.04, 0)
    m.box((0.3, 0.22, 0.012), Ml @ T(0, 0.02, 0.006), vlib.RW("wood"), C("6a4228"))
    m.box((0.38, 0.26, 0.012), Ml @ T(0, 0.02, 0.07, rx=0.45), vlib.RW("wood"), C("7a4a2c"))
    m.box((0.38, 0.02, 0.02), Ml @ T(0, -0.1, 0.022, rx=0.45), vlib.RW("wood"), C("6a4228"))
    m.box((0.02, 0.12, 0.1), Ml @ T(0, 0.1, 0.05), vlib.RW("wood"), C("6a4228"))
    open_book(m, Ml @ T(0, 0.02, 0.078, rx=0.45), w=0.36, d=0.25, cover=C("5a1a1e"))
    # a second open book lying flat, and a pencil across it
    open_book(m, T(-0.08, -0.09, 0, rz=0.08), w=0.3, d=0.2, thick=0.022, cover=C("1f2f52"))
    m.cyl(0.0035, 0.0035, 0.17, 6, "sw_satin", T(-0.16, -0.13, 0.044, ry=math.pi / 2), C("d8a020"))
    idx = 200
    # two stacks of books lying flat
    for sx, sy, specs in ((-0.84, -0.08, (("spine_g21", 0.032, 0.24, 0.17), ("spine_g4", 0.028, 0.22, 0.15),
                                          ("spine_g30", 0.04, 0.25, 0.18), ("spine_g8", 0.026, 0.2, 0.14))),
                          (0.76, -0.12, (("spine_g36", 0.03, 0.23, 0.16), ("spine_g2", 0.034, 0.21, 0.15),
                                         ("spine_g12", 0.024, 0.2, 0.13)))):
        z = 0.0
        for reg, w, h, d in specs:
            add_book(s, idx, (sx + rng.uniform(-0.01, 0.01), sy, z), w, h, d, reg,
                     "paper" if kinds[reg] == "paper" else "hard", lying=True, rz=rng.uniform(-0.08, 0.08),
                     where="counter")
            idx += 1
            z += w
    price_card(m, T(-0.84, -0.02, 0.126), 2)
    # a short row standing between two bookends at the back
    x = 0.08
    for reg in ("spine_g13", "spine_g40", "spine_g0", "spine_g26", "spine_g44", "spine_g19"):
        w = rng.uniform(0.025, 0.04)
        h = rng.uniform(0.2, 0.25)
        add_book(s, idx, (x + w / 2, 0.05, 0), w, h, h * 0.68, reg, "paper" if kinds[reg] == "paper" else "hard",
                 where="counter")
        x += w + 0.002
        idx += 1
    bookend(m, T(0.075, 0.05, 0), side=1)
    bookend(m, T(x + 0.004, 0.05, 0), side=-1)
    price_card(m, T(0.2, -0.05, 0), 3)
    bookmark_tray(m, T(0.34, -0.14, 0, rz=0.1))
    lamp(m, 0.56, 0.08)
    cash_box(m, T(0.86, 0.1, 0, rz=-0.15))
    price_card(m, T(0.64, -0.17, 0, rz=0.2), 0)
    s.finish()
    return s


SETS = {
    "prop_books_shelf_1": dict(fn=lambda: shelf_set("prop_books_shelf_1", "slot_shelf_1", 0, NAMED),
                               slot="slot_shelf_1", stall="buecherstand", kind="shelf", section=True, seed=51,
                               width=2.1, cam=((0.0, -1.35, 0.2), (0.0, 0.0, 0.14), 32),
                               hero=((0.03, -0.72, 0.17), (0.03, 0.0, 0.14), 36)),
    "prop_books_shelf_2": dict(fn=lambda: shelf_set("prop_books_shelf_2", "slot_shelf_2", 100, ()),
                               slot="slot_shelf_2", stall="buecherstand", kind="shelf2", section=True, seed=52,
                               width=2.1, cam=((0.35, -1.1, 0.25), (0.1, 0.0, 0.14), 32)),
    "prop_books_counter": dict(fn=counter, slot="slot_counter", stall="buecherstand", kind="counter", section=True,
                               seed=53, width=2.2, cam=((-0.0, -1.95, 0.62), (0.0, 0.0, 0.1), 30),
                               hero=((0.2, -0.85, 0.42), (0.22, 0.0, 0.1), 36)),
}
