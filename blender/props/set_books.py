"""Bücherstand goods: Mac's 55 books in six category sections, the back shelves and the counter.

prop_books_<key>   -> slot_cat_<key> of stall_buecher, one per category in content/books/categories.json
                      (physics, lives, mind, people, decisions, craft). The carpenter's
                      blender/stalls/buecher_sections.json gives each section's boards (offset from the slot:
                      left end, front edge, top surface; width, depth, clear height). Every book of the category
                      stands spine-out on those boards as its own node act_book_<nn> (nn = 00..54 in
                      categories.json order, books_catalog), among untitled filler books (static, not clickable).
prop_books_shelf_1 -> slot_shelf_1 (lower back shelf): untitled secondhand stock, stacks, bookends
prop_books_shelf_2 -> slot_shelf_2 (upper back shelf): the same
prop_books_counter -> slot_counter: the open guest book on a reading stand, two face-out copies of Mac's books
                      on easels (static display copies, not act_ nodes: each title is clickable once, on its
                      category shelf), untitled stacks, bookmarks, price cards, a banker's lamp with an emissive
                      bulb_warm bulb (no light_ empty: the stall has its two), a cash box.

Every act_book_<nn> has its origin at the middle of its spine's foot (where it stands), the spine toward -Y
(the visitor), and one material book_cover_<nn> reading the books atlas; its front cover (the +X board, spine on
its left as you look at it) carries the cover art whose UV rect items.json gives as cover_uv. items.json also
carries name (title), author, slug and category. No invented titles anywhere: filler spines carry no lettering.
"""
import json
import math
import os

from mathutils import Matrix, Vector

import atlas_books
import books_catalog
import goods as G
import vlib
from vlib import C, T, WHITE, drng, jit, lite, rng, seg

TWO_PI = 2 * math.pi
SECTIONS_JSON = os.path.join(vlib.REPO, "blender", "stalls", "buecher_sections.json")
SHELF_X = 0.925          # the back shelves: diagonal braces stand at x = +-0.95
SPINE_Y = -0.118
LOW_ZONES = {"prop_books_shelf_1": [(-0.04, 0.04, 0.205)], "prop_books_shelf_2": []}
SPINE_SET = 0.012        # titled spines stand this far behind a section board's front edge


def sections():
    """{key: section} from the carpenter's buecher_sections.json (raises if it is missing: the vendor does
    not invent a layout)."""
    with open(SECTIONS_JSON) as f:
        js = json.load(f)
    return {s["key"]: s for s in js["sections"]}


def catalog():
    return books_catalog.load()


# ------------------------------------------------------------ one book
def book(m, w, h, d, spine, front, kind, mat, M=None, page_col=C("efe6d0")):
    """A book standing on its tail: origin at the middle of the spine's foot, spine toward -Y, fore-edge
    toward +Y, thickness w along X. Front cover on the +X board (spine on its left). `spine` and `front`
    are books-atlas region names (front None: a plain board cut from the spine's cloth)."""
    M = M or Matrix()
    sreg = vlib.R(spine)
    plain = vlib.R(sreg.rect, sub=(0.04, 0.25, 0.12, 0.75))
    front = vlib.R(front) if front else plain
    edge = vlib.R("pages_edge")
    if lite():
        m.box((w, d, h), M @ T(0, d / 2, h / 2), plain, WHITE, mat,
              faces={"ny": sreg, "px": front, "pz": edge}, skip=("nz", "py"))
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
              C(drng.choice(["a8261e", "e8d8a8", "2a3a6a", "d8b048"])), mat, skip=("nz", "ny"))
    else:
        # paperback: flush soft covers, a square spine
        m.box((w, d, h), M @ T(0, d / 2, h / 2), plain, WHITE, mat,
              faces={"ny": sreg, "px": front, "pz": edge, "py": edge, "nz": edge})


def book_dims(b, clear=None, depth=None):
    """A book's (w, h, d) in metres, kept under a board's clear height and inside its depth."""
    w, h, d = b["dims"]
    if clear:
        h = min(h, clear - 0.012)
    if depth:
        d = min(d, depth - SPINE_SET - 0.006)
    return w, h, d


def add_real_book(s, nn, b, loc, rz=0.0, clear=None, depth=None, where="section"):
    """Mac's book nn as act_book_<nn>, standing at loc (the middle of its spine's foot)."""
    name = f"act_book_{nn:02d}"
    k = books_catalog.key(nn)
    w, h, d = book_dims(b, clear, depth)
    node = s.node(name, loc, rot=(0, 0, rz) if rz else None)
    book(node, w, h, d, "spine_" + k, "cover_" + k, "paper" if b["binding"] == "paper" else "hard",
         f"book:{nn:02d}", None, C("efe6d0") if b["binding"] != "cloth" else C("e2d6b8"))
    s.item(name, b["title"], "book", title=b["title"], author=b["author"], slug=b["slug"], category=b["category"],
           category_de=b["label_de"], cover_material=f"book_cover_{nn:02d}", cover_uv=cover_uv_gltf("cover_" + k),
           cover_texture="prop_tex_books_color.webp", where=where,
           size_m=[round(w, 3), round(h, 3), round(d, 3)])
    return w


def cover_uv_gltf(region):
    """A region's rect in glTF texture space (origin top-left): [u_min, v_min, u_max, v_max]."""
    u0, v0, u1, v1 = vlib.regions()[region]
    return [round(u0, 5), round(1 - v1, 5), round(u1, 5), round(1 - v0, 5)]


FILLER_KINDS = atlas_books.filler_kinds()


def filler(m, M, w, h, d, k):
    """An untitled filler book (merged into the set's static mesh, not clickable). k picks its spine."""
    key = f"spine_f{k % atlas_books.N_FILLER}"
    kind = FILLER_KINDS[key]
    book(m, w, h, d, key, None, "paper" if kind == "paper" else "hard", "books", M,
         C("efe6d0") if kind != "leather" else C("d8c8a0"))


def filler_dims(clear, depth, kind):
    w = rng.uniform(0.018, 0.042)
    h = rng.uniform(0.19, 0.25) if kind != "leather" else rng.uniform(0.22, 0.28)
    if clear:
        h = min(h, clear - 0.015)
    d = min(depth - SPINE_SET - 0.008, max(0.12, h * rng.uniform(0.62, 0.72)))
    return w, h, d


def filler_run(m, x, x_end, y0, z0, clear, depth, k0):
    """Untitled books standing from x to (at most) x_end; returns (new x, next filler index)."""
    k = k0
    while True:
        kind = FILLER_KINDS[f"spine_f{k % atlas_books.N_FILLER}"]
        w, h, d = filler_dims(clear, depth, kind)
        if x + w > x_end:
            return x, k
        filler(m, T(x + w / 2, y0 + rng.uniform(0.0, 0.01), z0), w, h, d, k)
        x += w + rng.uniform(0.0005, 0.0025)
        k += 7


def filler_stack(m, x, y0, z0, clear, depth, k0, n=3):
    """A short stack of untitled books lying flat, spines to the front; returns the x it ends at."""
    z = 0.0
    hmax = 0.0
    for i in range(n):
        w, h, d = rng.uniform(0.022, 0.038), rng.uniform(0.19, 0.23), rng.uniform(0.13, 0.16)
        d = min(d, depth - SPINE_SET - 0.01)
        if clear and z + w > clear - 0.02:
            break
        Ml = T(x + 0.12 + rng.uniform(-0.006, 0.006), y0, z0 + z, rz=rng.uniform(-0.05, 0.05)) @ \
            T(0, 0, w / 2) @ Matrix.Rotation(-math.pi / 2, 4, 'Y') @ T(0, 0, -h / 2)
        filler(m, Ml, w, h, d, k0 + i * 5)
        hmax = max(hmax, h)
        z += w
    return x + 0.25


def bookend(m, M, col=C("8a6a3a"), side=1):
    """Cast-brass bookend: a base plate under the books and an upright with a rounded top."""
    m.box((0.1, 0.12, 0.004), M @ T(side * 0.05, 0.06, 0.002), "brass", col)
    pts = [(0.0, 0.0), (0.12, 0.0), (0.12, 0.12), (0.09, 0.15), (0.03, 0.15), (0.0, 0.12)]
    R = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    m.extrude(pts, 0.006, M @ T(-0.003, 0, 0) @ R, "brass", "brass", col)


def shelf_set(name, slot, start, named):
    s = vlib.PropSet(name, slot, "buecherstand", footprint=(2.08, 0.28))
    fill_shelf(s, -SHELF_X + 0.012, SHELF_X - 0.012, start, named, LOW_ZONES.get(name, ()), shelf_pools()[name])
    bookend(s.static, T(-SHELF_X, SPINE_Y, 0), side=1)
    bookend(s.static, T(SHELF_X, SPINE_Y, 0), side=-1)
    s.finish()
    return s


def open_book(m, M, w=0.36, d=0.24, thick=0.03, cover=C("6e1a22")):
    """An open book lying on its back: two curved page blocks and the case underneath."""
    k = seg(10, 4)
    reg = vlib.R("pages_open")
    m.box((w + 0.012, d + 0.012, 0.004), M @ T(0, 0, 0.002), vlib.R("spine_f3", sub=(0.05, 0.3, 0.12, 0.7)), cover,
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
    """Banker's lamp: brass base and stem, green cased-glass shade, an emissive bulb_warm bulb (no light_ empty)."""
    n = seg(20, 8)
    m.lathe([(0.0, 0.0), (0.085, 0.0), (0.09, 0.006), (0.085, 0.018), (0.06, 0.026), (0.02, 0.032), (0.0, 0.032)],
            n, "brass", T(x, y + 0.03, 0), WHITE)
    m.cyl(0.009, 0.009, 0.3, seg(10, 6), "brass", T(x, y + 0.03, 0.03), WHITE, caps=not lite())
    m.cyl(0.006, 0.006, 0.2, seg(8, 5), "brass", T(x - 0.1, y + 0.03, 0.33, ry=math.pi / 2), WHITE, caps=not lite())
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
    m.cyl(0.018, 0.02, 0.05, seg(10, 6), "brass", Ms @ T(0, 0, 0.03), WHITE)
    # the bulb: emissive bulb_warm (BUILD.md: a small glow in a stall that has its two light_ empties)
    m.sphere(0.024, seg(10, 6), seg(6, 3), "sw_satin", Ms @ T(0, 0, 0.012), WHITE, "bulb_warm", scale=(1.8, 1, 1))


def cash_box(m, M):
    col = C("2f4a3a")
    m.box((0.26, 0.18, 0.09), M @ T(0, 0, 0.045), "sw_satin", col, skip=("nz",))
    m.box((0.262, 0.182, 0.012), M @ T(0, 0, 0.096), "sw_satin", jit(col, 0.02))
    m.box((0.01, 0.002, 0.022), M @ T(0, -0.091, 0.07), "brass", WHITE)
    for sx in (-1, 1):
        m.box((0.03, 0.01, 0.006), M @ T(sx * 0.13, 0, 0.104), "brass", WHITE)
    m.tube([(-0.05, 0, 0.108), (-0.05, 0, 0.13), (0.05, 0, 0.13), (0.05, 0, 0.108)], 0.004, 5 if not lite() else 3,
           "brass", M, WHITE)
    if not lite():
        for k in range(6):
            m.cyl(0.012, 0.012, 0.002, 10, "brass", M @ T(0.18, -0.02, k * 0.0021), WHITE)
        for dx, dy in ((0.21, 0.03), (0.16, 0.05)):
            m.cyl(0.011, 0.011, 0.002, 10, "sw_metal", M @ T(dx, dy, 0), C("c8c8c8"))
    else:
        m.cyl(0.012, 0.012, 0.012, 6, "brass", M @ T(0.18, -0.02, 0), WHITE)
        for dx, dy in ((0.21, 0.03), (0.16, 0.05)):
            m.cyl(0.011, 0.011, 0.002, 6, "sw_metal", M @ T(dx, dy, 0), C("c8c8c8"))


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




def easel_copy(m, M, nn, b, scale=1.0):
    """A face-out display copy of Mac's book nn on a small wooden easel (static: the clickable copy of every
    title is the one on its category shelf). The book leans back 15 degrees, its front cover to the visitor."""
    k = books_catalog.key(nn)
    w, h, d = b["dims"]
    h, d = h * scale, d * scale
    wood = vlib.RW("wood")
    # easel: a back leg, a ledge and two front legs (the tilted legs' feet sit on the counter, not in it)
    m.box((0.012, 0.012, h * 0.8), M @ T(0, 0.06, h * 0.39 + 0.002, rx=-0.26), wood, C("6a4228"))
    m.box((d * 0.9, 0.03, 0.008), M @ T(0, -0.035, 0.012), wood, C("7a4a2c"))
    m.box((d * 0.9, 0.006, 0.02), M @ T(0, -0.048, 0.02), wood, C("7a4a2c"))
    for sx in (-1, 1):
        m.box((0.01, 0.01, h * 0.75), M @ T(sx * d * 0.38, -0.01, h * 0.365 + 0.002, rx=0.26), wood, C("6a4228"))
    # the book turned so its front cover (+X board) faces the visitor (-Y), spine on the left, centred on the
    # easel, standing on the ledge and leaning back against the back leg
    Mb = M @ T(0, -0.035 + w / 2, 0.016) @ Matrix.Rotation(-0.26, 4, 'X') @ T(-d / 2, 0, 0) @ \
        Matrix.Rotation(-math.pi / 2, 4, 'Z')
    book(m, w, h, d, "spine_" + k, "cover_" + k, "paper" if b["binding"] == "paper" else "hard", "books", Mb)


def counter():
    s = vlib.PropSet("prop_books_counter", "slot_counter", "buecherstand", footprint=(2.0, 0.45))
    m = s.static
    cat = dict(catalog())
    # reading stand with the bookseller's open guest book
    Ml = T(-0.45, 0.04, 0)
    m.box((0.3, 0.22, 0.012), Ml @ T(0, 0.02, 0.006), vlib.RW("wood"), C("6a4228"))
    m.box((0.38, 0.26, 0.012), Ml @ T(0, 0.02, 0.07, rx=0.45), vlib.RW("wood"), C("7a4a2c"))
    m.box((0.38, 0.02, 0.02), Ml @ T(0, -0.1, 0.022, rx=0.45), vlib.RW("wood"), C("6a4228"))
    m.box((0.02, 0.12, 0.1), Ml @ T(0, 0.1, 0.05), vlib.RW("wood"), C("6a4228"))
    open_book(m, Ml @ T(0, 0.02, 0.078, rx=0.45), w=0.36, d=0.25, cover=C("5a1a1e"))
    # a pencil on a ribbon beside the guest book, and a second open book (untitled) lying flat
    open_book(m, T(-0.08, -0.09, 0, rz=0.08), w=0.3, d=0.2, thick=0.022, cover=C("1f2f52"))
    m.cyl(0.0035, 0.0035, 0.17, 6, "sw_satin", T(-0.16, -0.13, 0.044, ry=math.pi / 2), C("d8a020"))
    # two face-out display copies of Mac's books on easels, at the counter's ends
    easel_copy(m, T(-0.84, 0.02, 0, rz=0.12), 8, cat[8])          # The Order of Time
    easel_copy(m, T(0.74, 0.04, 0, rz=-0.1), 53, cat[53])         # Atomic Habits
    # an untitled stack lying flat, and a short row between bookends (secondhand stock)
    z = 0.0
    for k, (w, h, d) in enumerate(((0.032, 0.24, 0.17), (0.028, 0.22, 0.15), (0.04, 0.25, 0.18))):
        Ms = T(-0.62 + rng.uniform(-0.01, 0.01), -0.1, z, rz=rng.uniform(-0.08, 0.08)) @ T(0, 0, w / 2) @ \
            Matrix.Rotation(-math.pi / 2, 4, 'Y') @ T(0, 0, -h / 2)
        filler(m, Ms, w, h, d, 2 + k * 5)
        z += w
    price_card(m, T(-0.62, -0.04, z), 2)
    x = 0.08
    for k in range(6):
        w = rng.uniform(0.025, 0.04)
        h = rng.uniform(0.2, 0.25)
        filler(m, T(x + w / 2, 0.05, 0), w, h, h * 0.68, 3 + k * 7)
        x += w + 0.002
    bookend(m, T(0.075, 0.05, 0), side=1)
    bookend(m, T(x + 0.004, 0.05, 0), side=-1)
    price_card(m, T(0.2, -0.05, 0), 3)
    bookmark_tray(m, T(0.34, -0.14, 0, rz=0.1))
    lamp(m, 0.52, 0.1)
    cash_box(m, T(0.95, 0.12, 0, rz=-0.15))
    price_card(m, T(0.62, -0.05, 0, rz=0.2), 0)     # round 8: clear of the stall's new counter frame at the front
    s.finish()
    return s


def shelf_set(name, slot, seed_k):
    """A back shelf of untitled secondhand stock: standing runs, a lying stack or two, brass bookends."""
    s = vlib.PropSet(name, slot, "buecherstand", footprint=(2.08, 0.28))
    m = s.static
    low = LOW_ZONES.get(name, ())
    x, k = -SHELF_X + 0.012, seed_k
    x1 = SHELF_X - 0.012
    stacks = [-0.55 + rng.uniform(-0.08, 0.08), 0.42 + rng.uniform(-0.08, 0.08)]
    while x < x1 - 0.02:
        if stacks and x >= stacks[0]:
            stacks.pop(0)
            x = filler_stack(m, x, SPINE_Y, 0.0, None, 0.26, k, n=rng.randint(3, 5)) + 0.01
            k += 11
            continue
        # a standing run up to the next stack (or the end), kept under the brace over the middle
        nxt = stacks[0] if stacks else x1
        kind = FILLER_KINDS[f"spine_f{k % atlas_books.N_FILLER}"]
        w, h, d = filler_dims(None, 0.26, kind)
        for z0, z1, hmax in low:
            if x - 0.02 < z1 and x + w + 0.02 > z0:
                h = min(h, hmax)
        if x + w > nxt:
            x = nxt
            continue
        filler(m, T(x + w / 2, SPINE_Y + rng.uniform(0.0, 0.012), 0), w, h, min(d, 0.2), k)
        x += w + rng.uniform(0.0005, 0.003)
        k += 7
    bookend(m, T(-SHELF_X, SPINE_Y, 0), side=1)
    bookend(m, T(SHELF_X, SPINE_Y, 0), side=-1)
    s.finish()
    return s


def cover_scale(b, cmax):
    """Round 8: a face-out copy keeps its proportions but is scaled down (never up) to the cabinet's largest
    cover (cover_max in buecher_sections.json); its thickness is capped at the ledge's limit."""
    t, h, d = b["dims"]
    k = min(1.0, cmax["width"] / d, cmax["height"] / h)
    return min(t * k, cmax["thickness"]), h * k, d * k


def add_face_out(s, nn, b, loc, lean, cmax):
    """Mac's book nn as act_book_<nn>, face-out on a cabinet's angled board: the front cover toward the visitor
    (-Y), the spine on the left (-X), leaning back `lean` rad against the backboard. The node's origin is the
    middle of the book's foot where it rests on the ledge (the back edge of the foot: leaning back, the book
    stands on that edge and its front edge lifts by thickness x sin(lean)); the node is rotated about X."""
    name = f"act_book_{nn:02d}"
    k = books_catalog.key(nn)
    w, h, d = cover_scale(b, cmax)
    node = s.node(name, loc, rot=(-lean, 0, 0))
    M = T(-d / 2, -w / 2, 0) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')
    book(node, w, h, d, "spine_" + k, "cover_" + k, "paper" if b["binding"] == "paper" else "hard",
         f"book:{nn:02d}", M, C("efe6d0"))
    s.item(name, b["title"], "book", title=b["title"], author=b["author"], slug=b["slug"], category=b["category"],
           category_de=b["label_de"], cover_material=f"book_cover_{nn:02d}", cover_uv=cover_uv_gltf("cover_" + k),
           cover_texture="prop_tex_books_color.webp", where="cabinet", face_out=True,
           lean_deg=round(math.degrees(lean), 2), size_m=[round(w, 3), round(h, 3), round(d, 3)],
           pivot="the middle of the foot's back edge, on the ledge; the cover faces -Y, the spine is on -X")
    return w


COVER_GLOW_MID, COVER_GLOW_RIGHT, COVER_GLOW_LEFT = 0.1, 0.14, 0.24    # added to vlib.BOOK_GLOW (0.3), round 9


def section_set(key):
    """prop_books_<key> (round 8, ADR 0004): Mac's books of one category face-out in the category's glazed
    cabinet (buecher_sections.json): one act_book_<nn> per title at the board's cover_slots_x, filled from the
    top board down (eye level first), so any empty place is at the bottom right. The spine board above carries
    a short row of untitled filler spines between bookends (scenery, static). Raises if the titles do not fit."""
    sec = sections()[key]
    books = [(nn, b) for nn, b in catalog() if b["category"] == key]
    boards = sorted(sec["boards"], key=lambda bd: -bd["index"])
    places = [(bd, x) for bd in boards for x in bd["cover_slots_x"]]
    if len(books) > len(places):
        raise RuntimeError(f"{key}: {len(books)} titles but the cabinet takes {len(places)}")
    W = max(bd["offset"][0] + bd["width"] for bd in sec["boards"])
    s = vlib.PropSet(f"prop_books_{key}", sec["slot"], "buecherstand", footprint=(W, sec["spine_board"]["depth"]))
    m = s.static
    cmax = sec["cover_max"]
    glow = {}
    for (nn, b), (bd, x) in zip(books, places):
        ox, oy, oz = bd["offset"]
        lean = math.radians(bd["lean_deg"])
        # round 9 (judges, round 8: the lives cabinet's left column still read dim at cam_cat): every cover glows
        # a little more than in round 8, and the outer columns more again, where the cabinet's stiles shade them
        # from its lamps (the left one most: the lamps sit right of centre in the cam_cat views)
        cols = sorted(bd["cover_slots_x"])
        glow[nn] = vlib.BOOK_GLOW + (COVER_GLOW_LEFT if x == cols[0] else COVER_GLOW_RIGHT if x == cols[-1]
                                     else COVER_GLOW_MID)
        # the foot's back edge 3 mm in front of the backboard's foot (ledge_depth behind the lip), so the cover
        # leans parallel to the backboard without touching it
        add_face_out(s, nn, b, (ox + x + rng.uniform(-0.002, 0.002), oy + bd["ledge_depth"] - 0.004, oz), lean, cmax)
    # the spine board: untitled stock at rest, a bookend at each end of the row, the right part left free
    sb = sec["spine_board"]
    ox, oy, oz = sb["offset"]
    k = 7 + 5 * len(key)
    x0 = ox + 0.03
    x1 = ox + sb["width"] * rng.uniform(0.55, 0.7)
    bookend(m, T(x0 - 0.004, oy + SPINE_SET + 0.012, oz), side=1)
    # the cabinet's bulb strip runs about 0.19 m over the spine board: the filler stays under it
    x, k = filler_run(m, x0, x1, oy + SPINE_SET + 0.012, oz, min(sb["clear_height"] - 0.06, 0.16), min(sb["depth"], 0.2), k)
    bookend(m, T(x + 0.003, oy + SPINE_SET + 0.012, oz), side=-1)
    s.finish()
    for nn, g in glow.items():
        b_ = vlib.material(f"book:{nn:02d}").node_tree.nodes["Principled BSDF"]
        b_.inputs["Emission Strength"].default_value = g
    s.report_extra = {"cover_glow": {f"book_cover_{nn:02d}": round(g, 2) for nn, g in glow.items()}}
    return s


def _slot_frame(sec):
    """The slot's frame in the stall: (position, rotation about Z in rad)."""
    return Vector(sec["slot_position"]), math.radians(sec["slot_rotation_z_deg"])


def _section_def(key, seed):
    sec = sections()[key]
    W = max(bd["offset"][0] + bd["width"] for bd in sec["boards"])
    top = max(bd["offset"][2] for bd in sec["boards"])
    zc = top / 2 + 0.12
    # the engine's close-up, cam_cat_<key> -> its target, as offsets from the slot in stall axes (shot_at); the
    # 42 degree vertical field of view of the site is a 26.4 mm lens on a 36 mm wide 16:9 sensor
    pos, _ = _slot_frame(sec)
    cam_cat = (tuple(Vector(sec["cam_position"]) - pos), tuple(Vector(sec["cam_target_position"]) - pos), 26.4)
    return dict(fn=lambda: section_set(key), slot=sec["slot"], stall="buecherstand", kind="section", section=True,
                seed=seed, width=W + 0.4, section_boards=None,
                cam=((W / 2, -1.0, zc + 0.1), (W / 2, 0.05, zc), 32), cam_fixed=True,
                hero=((W * 0.5, -0.75, top + 0.16), (W * 0.5, 0.05, top + 0.1), 40),
                in_stall="stall_buecher.glb", stall_cams={"cam_cat": cam_cat}, seat="lean",
                label=f"{sec['label_de']} ({sec['books']} books)")


SETS = {
    "prop_books_shelf_1": dict(fn=lambda: shelf_set("prop_books_shelf_1", "slot_shelf_1", 1),
                               slot="slot_shelf_1", stall="buecherstand", kind="shelf", section=True, seed=51,
                               width=2.1, cam=((0.0, -1.35, 0.2), (0.0, 0.0, 0.14), 32)),
    "prop_books_shelf_2": dict(fn=lambda: shelf_set("prop_books_shelf_2", "slot_shelf_2", 4),
                               slot="slot_shelf_2", stall="buecherstand", kind="shelf2", section=True, seed=52,
                               width=2.1, cam=((0.35, -1.1, 0.25), (0.1, 0.0, 0.14), 32)),
    "prop_books_counter": dict(fn=counter, slot="slot_counter", stall="buecherstand", kind="counter", section=True,
                               seed=53, width=2.2, cam=((-0.0, -1.95, 0.62), (0.0, 0.0, 0.1), 30),
                               hero=((0.3, -1.08, 0.5), (0.3, 0.0, 0.17), 36)),
}
for _i, _c in enumerate(books_catalog.categories()):
    SETS[f"prop_books_{_c['key']}"] = _section_def(_c["key"], 60 + _i)
