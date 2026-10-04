"""Round 6: book_open.glb, the open hardback the engine shows when a visitor clicks a book (docs/adr/0003,
"a clicked book opens in front of the camera with its summary and key ideas on its pages").

    site/public/models/book_open.glb (+ book_open.lite.glb), root node "book_open"

Frame (Blender, Z up; glTF turns it Y up): the book stands open and upright facing the reader at -Y (three.js
+Z), the spine vertical along Z at x = 0, the left half toward -X. The origin is the foot of the spine, on the
plane the boards stand on. Each half leans back by OPEN_V (10 degrees), so the spread is a shallow V.

Nodes
    write_page_left, write_page_right   the writing faces on the two pages (UVs 0..1 across the writing area,
                                        +V up the text), plain write_page material
    act_page_turn                       the leaf that turns, hinged at the spine: an empty on the spine axis.
                                        At rest the leaf lies 0.4 mm under the right page (hidden); rotating
                                        act_page_turn about its local Z (three.js: Y) by TURN (-(pi - 2 V),
                                        about -2.79 rad) lays it 0.4 mm under the left page, so it shows only
                                        while it turns. It carries write_page_turn_front (the right page's text
                                        as it lifts) and write_page_turn_back (the next left page as it lands).
    cam_read_book, cam_read_book_target the reading camera, square to the spread, which fills about 80 % of a
                                        16:9 frame at the engine's 42 degree field of view
    book_open_cover                     the outside of the left board (the front cover): UVs 0..1 across the
                                        cover (u from the spine to the fore-edge seen from outside, v up) on
                                        material book_cover_open, so the engine can show the clicked book's own
                                        cover (prop_tex_books_color.webp with that book's cover_uv from items.json)
Everything else (page block, gutter, fore-edge, squares, cloth boards and backstrip, headbands, ribbon)
is static.
"""
import math

from mathutils import Matrix, Vector

import vlib
import vprint
from vlib import C, T, WHITE, lite

PW, PH = 0.15, 0.22            # page width and height
SQ = 0.004                     # the board's squares round the pages
BT = 0.0032                    # board thickness
TB = 0.011                     # page block thickness per half, over the board
H0 = 0.0016                    # the pages' depth at the very gutter
GUT = 0.008                    # the gutter: the pages rise from H0 to TB within this distance of the spine
OPEN_V = math.radians(10.0)    # each half leans back by this much
WR = (0.03, 0.137, 0.03, 0.2)  # writing area on each page: x0, x1 (from the spine), z0, z1 (from the foot)
ZP0 = SQ                       # pages start above the board's foot
TURN = -(math.pi - 2 * OPEN_V)
LEAF_GAP = 0.0004


def h_at(x):
    """The page surface's height over the board at distance x from the spine (flat from the gutter out)."""
    if x >= GUT:
        return H0 + TB
    k = (1 - math.exp(-x / (GUT * 0.28))) / (1 - math.exp(-1 / 0.28))
    return H0 + TB * k


def xs_page():
    xs = sorted(set([0.0, 0.0008, 0.002, 0.0035, 0.0055, GUT, WR[0], WR[1], PW]))
    return xs


def page_surface(m, side, region="pr_paper"):
    """The top of one half's page block (in that half's frame: x out from the spine, -y toward the reader),
    with the writing rectangle left open. side: +1 right page, -1 left page (mirrored in x)."""
    xs = xs_page()
    zs = [ZP0, WR[2], WR[3], ZP0 + PH]
    reg = vlib.R(region)
    verts, faces, uvs = [], [], []
    idx = {}
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            idx[(i, j)] = len(verts)
            verts.append((side * x, -h_at(x), z))
    for j in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            if xs[i] >= WR[0] - 1e-9 and xs[i + 1] <= WR[1] + 1e-9 and j == 1:
                continue
            q = [idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]]
            if side < 0:
                q = q[::-1]
            faces.append(tuple(q))
            uvs.append([reg.uv(abs(verts[k][0]) / PW, (verts[k][2] - ZP0) / PH) for k in q])
    m.add(verts, faces, uvs, None, WHITE, "print", smooth=True)


def page_block_sides(m, side):
    """Fore-edge, head and tail of one half's page block: many fine page lines (pr_page_edge)."""
    xs = xs_page()
    reg = vlib.R("pr_page_edge")
    top = ZP0 + PH
    # fore-edge at x = PW (lines run up the edge, stacked in depth)
    d = h_at(PW)
    pts = [(side * PW, 0.0, ZP0), (side * PW, -d, ZP0), (side * PW, -d, top), (side * PW, 0.0, top)]
    if side > 0:
        pts = pts[::-1]
    m.add(pts, [(0, 1, 2, 3)], [[reg.uv((p[2] - ZP0) / PH, -p[1] / d) for p in pts]], None, WHITE, "print")
    # head (+Z) and tail (-Z): the block's cross-section, a strip along x
    for z, up in ((top, True), (ZP0, False)):
        verts, faces, uvs = [], [], []
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            q = [(side * x0, 0.0, z), (side * x1, 0.0, z), (side * x1, -h_at(x1), z), (side * x0, -h_at(x0), z)]
            # counter-clockwise seen from +Z for the head on the right half; flip for the tail / the left half
            if (side > 0) == up:
                q = q[::-1]
            o = len(verts)
            verts.extend(q)
            faces.append((o, o + 1, o + 2, o + 3))
            uvs.append([reg.uv(abs(p[0]) / PW, -p[1] / (H0 + TB)) for p in q])
        m.add(verts, faces, uvs, None, WHITE, "print")


def board(m, side, cover_node=None):
    """One board behind a half, in book cloth. The left
    board's outside goes to `cover_node` (the swappable front cover) instead of the static mesh."""
    x0, x1 = 0.0045, PW + SQ
    zb0, zb1 = 0.0, PH + 2 * SQ
    cx = side * (x0 + x1) / 2
    w = x1 - x0
    Mb = T(cx, BT / 2, (zb0 + zb1) / 2)
    skip = ("py",) if cover_node is not None else ()
    # cloth all round: the squares beyond the pages show the cloth's turn-ins (the marbled pastedown is inset
    # further than the squares, so it never shows on an open book and is not modelled)
    m.box((w, BT, zb1 - zb0), Mb, "pr_cloth", WHITE, "print", skip=skip)
    if cover_node is not None:
        # outside of the left board seen from behind: u from the spine (x = -x0) to the fore-edge (x = -x1)
        pts = [(-x0, BT, zb0), (-x1, BT, zb0), (-x1, BT, zb1), (-x0, BT, zb1)]
        # normal +Y: seen from +Y, -X is to the right, so this order is counter-clockwise
        cover_node.add(pts, [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]], None, C("6a1c20"), "book_cover_open")


def spine_strip(m):
    """The cloth backstrip behind the gutter, joining the two boards' inner edges in a shallow curve."""
    n = 6 if not lite() else 3
    zb0, zb1 = 0.0, PH + 2 * SQ
    R_ = Matrix.Rotation(-OPEN_V, 4, 'Z')
    L_ = Matrix.Rotation(OPEN_V, 4, 'Z')
    p_r = R_ @ Vector((0.0045, BT / 2, 0))
    p_l = L_ @ Vector((-0.0045, BT / 2, 0))
    ctrl = Vector((0.0, 0.017, 0))
    pts = []
    for k in range(n + 1):
        t = k / n
        p = (1 - t) ** 2 * p_l + 2 * (1 - t) * t * ctrl + t * t * p_r
        pts.append(p)
    reg = vlib.R("pr_cloth")
    verts, faces, uvs = [], [], []
    for k, p in enumerate(pts):
        a = pts[max(0, k - 1)]
        b = pts[min(n, k + 1)]
        tng = (b - a).normalized()
        nrm = Vector((tng.y, -tng.x, 0))               # toward the back (+Y) for a left-to-right curve
        if nrm.y < 0:
            nrm = -nrm
        for off in (BT / 2, -BT / 2):
            q = p + nrm * off
            verts.append((q.x, q.y, zb0))
            verts.append((q.x, q.y, zb1))
    # rows: per sample k: [outer bottom, outer top, inner bottom, inner top]
    for k in range(n):
        o, nx = 4 * k, 4 * (k + 1)
        for a, b, flip in ((0, 1, True), (2, 3, False)):
            q = (o + a, nx + a, nx + b, o + b)
            if flip:
                q = q[::-1]
            faces.append(q)
            uvs.append([reg.uv(k / n, 0), reg.uv((k + 1) / n, 0), reg.uv((k + 1) / n, 1), reg.uv(k / n, 1)])
    m.add(verts, faces, uvs, None, WHITE, "print", smooth=True)
    # caps at the head and tail of the strip
    for z_i, up in ((1, True), (0, False)):
        for k in range(n):
            o, nx = 4 * k, 4 * (k + 1)
            q = (o + z_i, nx + z_i, nx + 2 + z_i, o + 2 + z_i)
            if not up:
                q = q[::-1]
            m.add([verts[i] for i in q], [(0, 1, 2, 3)], [[reg.uv(0.5, 0.5)] * 4], None, WHITE, "print")


def leaf(s):
    """The turning leaf: act_page_turn on the spine axis, the leaf hidden 0.4 mm under the right page at rest."""
    hq = (H0 + TB - LEAF_GAP) / math.cos(OPEN_V)
    node = s.node("act_page_turn", (0.0, -hq, 0.0))
    # leaf geometry in the act_page_turn frame: flat, from just off the spine to the fore-edge, leaning -OPEN_V
    Rl = T(rz=-OPEN_V)
    x_start = 0.006
    xs = [x_start, WR[0], WR[1], PW - 0.0015]
    zs = [ZP0 + 0.0015, WR[2], WR[3], ZP0 + PH - 0.0015]
    reg = vlib.R("pr_paper")
    # the leaf plane in the node frame: x along the page, y = 0 (its surface), facing -y
    for face_side in (-1, 1):                     # -1 front (toward the reader), +1 back
        verts, faces, uvs = [], [], []
        idx = {}
        for j, z in enumerate(zs):
            for i, x in enumerate(xs):
                idx[(i, j)] = len(verts)
                verts.append((x, face_side * 0.0001, z))
        for j in range(3):
            for i in range(3):
                if i == 1 and j == 1:
                    continue
                q = [idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]]
                if face_side > 0:
                    q = q[::-1]
                faces.append(tuple(q))
                uvs.append([reg.uv(verts[k][0] / PW, (verts[k][2] - ZP0) / PH) for k in q])
        node.add(verts, faces, uvs, Rl, WHITE, "print", smooth=False)
    ww, wh = WR[1] - WR[0], WR[3] - WR[2]
    cx, cz = (WR[0] + WR[1]) / 2, (WR[2] + WR[3]) / 2
    front = vprint.write_node(s, "write_page_turn_front", "act_page_turn")
    # front: facing -y (the reader): u along +x, v along +z
    front.add([(WR[0], -0.0001, WR[2]), (WR[1], -0.0001, WR[2]), (WR[1], -0.0001, WR[3]), (WR[0], -0.0001, WR[3])],
              [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]], Rl, vprint.wcol("page"), "write_page")
    back = vprint.write_node(s, "write_page_turn_back", "act_page_turn")
    # back: facing +y; once turned over to the left it reads with u along +X: here u runs along -x
    back.add([(WR[1], 0.0001, WR[2]), (WR[0], 0.0001, WR[2]), (WR[0], 0.0001, WR[3]), (WR[1], 0.0001, WR[3])],
             [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]], Rl, vprint.wcol("page"), "write_page")
    s.item("act_page_turn", "The page that turns", "page_turn", pivot="the spine (hinge) axis",
           turn={"axis_blender": "local Z", "axis_threejs": "local Y", "rest": 0.0, "turned": round(TURN, 4),
                 "note": "0.4 mm under the right page at rest and under the left page when turned"},
           write={"front": "write_page_turn_front", "back": "write_page_turn_back"})
    return node


def ribbon(m):
    """A red ribbon marker down the right page's gutter, out over the tail and lying on the stand."""
    w = 0.006
    x = 0.0028
    pts = []
    for z in (ZP0 + PH - 0.002, ZP0 + PH * 0.6, ZP0 + PH * 0.25, ZP0 + 0.004):
        pts.append(Vector((x, -h_at(x) - 0.0003, z)))
    pts += [Vector((x + 0.002, -h_at(x) - 0.003, ZP0 - 0.0005)), Vector((x + 0.006, -h_at(x) - 0.012, 0.0006)),
            Vector((x + 0.01, -h_at(x) - 0.03, 0.0006))]
    reg = vlib.R("pr_ribbon")
    verts, faces, uvs = [], [], []
    for k, p in enumerate(pts):
        verts.append(tuple(p + Vector((-w / 2, 0, 0))))
        verts.append(tuple(p + Vector((w / 2, 0, 0))))
    n = len(pts)
    for k in range(n - 1):
        q = (2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2)
        faces.append(q[::-1])
        uvs.append([reg.uv(0, k / (n - 1)), reg.uv(1, k / (n - 1)), reg.uv(1, (k + 1) / (n - 1)),
                    reg.uv(0, (k + 1) / (n - 1))][::-1])
    m.add(verts, faces, uvs, T(rz=-OPEN_V), WHITE, "print", smooth=True)


def book_open():
    s = vlib.PropSet("book_open", "", "", footprint=(0.32, 0.06))
    m = s.static
    right = vlib.Mesh("half_right")
    page_surface(right, 1)
    page_block_sides(right, 1)
    board(right, 1)
    # the left half: its board's outside is the swappable front cover (its own node)
    left = vlib.Mesh("half_left")
    page_surface(left, -1)
    page_block_sides(left, -1)
    cover = s.node("book_open_cover", (0, 0, 0))
    board(left, -1, cover_node=cover)
    m.merge(left, T(rz=OPEN_V))
    m.merge(right, T(rz=-OPEN_V))
    s.rot["book_open_cover"] = (0, 0, OPEN_V)
    spine_strip(m)
    # headbands at the head and tail of the gutter
    for z in (ZP0 + PH + 0.0012, ZP0 - 0.0012):
        m.cyl(0.0022, 0.0022, 0.016, 6 if not lite() else 4, "pr_headband", T(-0.008, -0.001, z, ry=math.pi / 2),
              WHITE, "print")
    ribbon(m)
    # the writing faces on the two pages
    ww, wh = WR[1] - WR[0], WR[3] - WR[2]
    for side, name in ((-1, "write_page_left"), (1, "write_page_right")):
        wm = vprint.write_node(s, name, None, (0, 0, 0), rot=(0, 0, -side * OPEN_V))
        x0, x1 = (WR[0], WR[1]) if side > 0 else (-WR[1], -WR[0])
        y = -h_at(WR[0])
        wm.add([(x0, y, WR[2]), (x1, y, WR[2]), (x1, y, WR[3]), (x0, y, WR[3])], [(0, 1, 2, 3)],
               [[(0, 0), (1, 0), (1, 1), (0, 1)]], None, vprint.wcol("page"), "write_page")
    leaf(s)
    # the reading camera, square to the spread
    spread_w = 2 * WR[1] * math.cos(OPEN_V)
    d = vprint.reading_distance(spread_w, wh, fill=0.8)
    zc = (WR[2] + WR[3]) / 2
    cxw = (WR[0] + WR[1]) / 2
    ys = -cxw * math.sin(OPEN_V) - (H0 + TB) * math.cos(OPEN_V)        # the write faces' centres, both halves
    vprint.cam_read(s, "book", (0.0, ys, zc), (0.0, ys - d, zc))
    s.finish()
    return s


def preview_text(slug="the-order-of-time"):
    """Preview only: one of Mac's books on the pages, the way the engine lays it out (title page left, summary
    right), to show the writing faces (vstage.preview_texts)."""
    import os
    import re
    path = os.path.join(vlib.REPO, "content", "books", f"{slug}.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    meta = dict(re.findall(r'^(title|author|one_line): "(.*)"$', text, re.M))
    body = text.split("## In short", 1)[-1].strip().split("\n\n")[0]
    return {"write_page_left": [(meta.get("title", ""), 0.075, "garamond", "1e1a16"),
                                (meta.get("author", ""), 0.045, "garamond", "4a3a2a"),
                                (meta.get("one_line", ""), 0.038, "garamond", "2a2420")],
            "write_page_right": [("In short", 0.05, "garamond", "1e1a16"), (body, 0.036, "garamond", "2a2420")]}


SETS = {
    "book_open": dict(fn=book_open, slot="", stall="", kind="counter", section=True, seed=61, standalone=True,
                      cam=((0.0, -0.62, 0.2), (0.0, 0.0, 0.11), 40), cam_fixed=True,
                      hero=((0.13, -0.52, 0.27), (0.0, -0.015, 0.112), 45), preview_text=preview_text),
}
