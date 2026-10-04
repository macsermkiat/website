"""Round 6 writing surfaces (docs/adr/0003, BUILD.md write_ / cam_read_): the builders shared by the sets.

A write_<name> node is an empty with one flat mesh child (<name>_mesh) on a plain write_* material. Its UVs run
0..1 across the writing area with +V up the text (Blender UV space; glTF flips V, which the engine expects).
The printed surround (a coaster's rim, the Marktblatt's masthead, a back label's small print, a page's
margins) is a separate mesh with a hole exactly where the writing face is, so the two never overlap or z-fight.
"""
import math

from mathutils import Matrix, Vector

import vlib
from vlib import C, T, lite, seg

TWO_PI = 2 * math.pi
UV01 = [0.0, 0.0, 1.0, 1.0]


def wcol(kind):
    """The sRGB colour of a plain writing face (atlas_print.WRITE_COLOURS) as a linear vertex colour."""
    return C(vlib.print_meta()["write_colours"][kind])


def write_rect(m, w, h, M=None, kind="card", down=False):
    """A w x h writing face centred on the node origin in its XY plane. Up (+Z normal): u along +X, v along +Y.
    down=True faces -Z and reads correctly once turned over about X: u along +X, v along -Y."""
    hw, hh = w / 2, h / 2
    if not down:
        pts = [(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    else:
        pts = [(-hw, hh, 0), (hw, hh, 0), (hw, -hh, 0), (-hw, -hh, 0)]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    m.add(pts, [(0, 1, 2, 3)], [uv], M, wcol(kind), f"write_{kind}", smooth=False)
    return m


def disc_ring(m, R, hw, hh, region, M=None, col=vlib.WHITE, mat="print", n=32, down=False, map_r=None, z=0.0):
    """The flat ring between a circle of radius R and a centred hw x hh-half-size rectangle (a coaster face
    with its writing face cut out). Planar mapped: the region holds the whole disc (diameter 2 * map_r)."""
    reg = vlib.R(region)
    mr = map_r or R
    corners = [math.atan2(hh, hw), math.atan2(hh, -hw), math.atan2(-hh, -hw), math.atan2(-hh, hw)]
    angs = sorted(set([TWO_PI * k / n for k in range(n)] + [a % TWO_PI for a in corners]))
    verts, faces, uvs = [], [], []

    def inner(a):
        c, s = math.cos(a), math.sin(a)
        t = min(hw / abs(c) if abs(c) > 1e-9 else 1e9, hh / abs(s) if abs(s) > 1e-9 else 1e9)
        return (t * c, t * s)

    def uvp(x, y):
        return reg.uv(0.5 + 0.5 * x / mr, 0.5 + 0.5 * (-y if down else y) / mr)
    N = len(angs)
    for a in angs:
        verts.append((R * math.cos(a), R * math.sin(a), z))
        ix, iy = inner(a)
        verts.append((ix, iy, z))
    for k in range(N):
        o0, i0, o1, i1 = 2 * k, 2 * k + 1, 2 * ((k + 1) % N), 2 * ((k + 1) % N) + 1
        f = (o0, o1, i1, i0) if not down else (o0, i0, i1, o1)
        faces.append(f)
        uvs.append([uvp(*verts[i][:2]) for i in f])
    m.add(verts, faces, uvs, M, col, mat, smooth=False)
    return m


def rect_ring(m, W, H, wr, region, M=None, col=vlib.WHITE, mat="print"):
    """A flat W x H sheet (centred, facing +Z) with the writing rectangle wr = (u0, v0, u1, v1) (fractions of the
    sheet, v up) cut out: eight quads round the hole, mapped into region by position."""
    reg = vlib.R(region)
    u0, v0, u1, v1 = wr
    xs = [0.0, u0, u1, 1.0]
    ys = [0.0, v0, v1, 1.0]
    verts, faces, uvs = [], [], []
    idx = {}
    for j, yv in enumerate(ys):
        for i, xv in enumerate(xs):
            idx[(i, j)] = len(verts)
            verts.append(((xv - 0.5) * W, (yv - 0.5) * H, 0.0))
    for j in range(3):
        for i in range(3):
            if i == 1 and j == 1:
                continue
            f = (idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)])
            faces.append(f)
            uvs.append([reg.uv(xs[a], ys[b]) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))])
    m.add(verts, faces, uvs, M, col, mat, smooth=False)
    return m


def write_node(s, name, parent, loc=(0, 0, 0), rot=None):
    """A write_<name> node (empty + mesh child) under `parent`; returns its Mesh."""
    return s.node(name, loc, parent=parent, rot=rot)


def cam_read(s, name, target, eye, parent=None):
    """cam_read_<name> at `eye` with cam_read_<name>_target at `target` (both in the parent's frame)."""
    s.empty(f"cam_read_{name}", eye, parent)
    s.empty(f"cam_read_{name}_target", target, parent)


def reading_distance(w, h, fill=0.8, fov_deg=42.0, aspect=16 / 9):
    """How far back a camera of the engine's vertical fov stands so a w x h area fills `fill` of a 16:9 frame."""
    t = math.tan(math.radians(fov_deg) / 2)
    return max(h / (2 * t * fill), w / (2 * t * aspect * fill))


# ------------------------------------------------------------------ the Bierdeckel
COASTER_T = 0.002


def coaster(s, n, loc, rz, colourway, label, project=None, z=0.0):
    """One Bierdeckel (10.7 cm, 2 mm board) lying flat: act_coaster_<n> (origin at the middle of its underside)
    with write_coaster_<n>_front on top and write_coaster_<n>_back underneath. The printed rim and the brewer's
    star come from the print atlas (pr_coaster_front_<colourway> / _back_<colourway>)."""
    pm = vlib.print_meta()
    D = pm["coaster_d_mm"] / 1000.0
    R = D / 2
    fw, fh = (v / 1000.0 for v in pm["front_rect_mm"])
    bw, bh = (v / 1000.0 for v in pm["back_rect_mm"])
    name = f"act_coaster_{n}"
    node = s.node(name, (loc[0], loc[1], z), rot=(0, 0, rz))
    k = seg(28, 12)
    # the board: printed top ring, printed bottom ring, grey pressed-board edge
    disc_ring(node, R, fw / 2, fh / 2, f"pr_coaster_front_{colourway}", T(0, 0, COASTER_T), n=k)
    disc_ring(node, R, bw / 2, bh / 2, f"pr_coaster_back_{colourway}", None, n=k, down=True)
    node.lathe([(R, 0.0), (R, COASTER_T)], k, "pr_coaster_edge", None, vlib.WHITE, "print", smooth=True)
    front = write_node(s, f"write_coaster_{n}_front", name, (0, 0, COASTER_T))
    write_rect(front, fw, fh, kind="card")
    back = write_node(s, f"write_coaster_{n}_back", name, (0, 0, 0))
    write_rect(back, bw, bh, kind="card", down=True)
    extra = {"project": project} if project else {}
    s.item(name, label, "coaster", colourway=colourway,
           write={"front": f"write_coaster_{n}_front", "back": f"write_coaster_{n}_back"},
           size_cm=round(D * 100, 1), **extra)
    return node
