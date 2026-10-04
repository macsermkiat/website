"""Vendor prop library: mesh builder with atlas UVs, materials, prop-set nodes, export and previews.

A prop set is one glb (site/public/models/prop_<set>.glb, plus .lite.glb). Its root node is an
empty named after the set, at the set's origin = the stall slot it belongs to (slot_counter,
slot_shelf_1, ...). Everything inside is in slot-local metres, Blender Z up, front toward -Y.

    from vlib import *
    s = PropSet("prop_demo", slot="slot_counter", stall="gluehwein")
    m = s.static                                   # merged static geometry (one node)
    m.lathe([(0.04, 0), (0.045, 0.1)], region="ceramic", mat="glaze", col=C("9c1a1f"))
    mug = s.node("act_mug_0", (0.2, 0, 0))         # an animated node, origin at its pivot
    ...
    s.finish()                                     # creates the Blender objects

All surfaces read from one texture atlas (blender/props/vendor_atlas.py). Colours are sRGB hex
strings or linear tuples; they go to COLOR_0, which glTF multiplies into the base colour.
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
sys.path.insert(0, HERE)

import bpy  # noqa: E402  (must precede bmesh / mathutils)
import bmesh  # noqa: E402,F401
from mathutils import Euler, Matrix, Vector  # noqa: E402
from mathutils.geometry import tessellate_polygon  # noqa: E402

from nmlib import state  # noqa: E402

TWO_PI = 2 * math.pi
ATLAS_DIR = os.path.join(REPO, "blender", "out", "vendor")
MODELS = os.path.join(REPO, "site", "public", "models")
REVIEW = os.path.join(REPO, "review", "round-4", "vendor")
_REG = None
LITE = {"on": False}
# Two random streams. `rng` is the layout stream: where goods stand, their sizes and which book is which.
# It must be drawn identically in the full and the lite build, so lite sets match the full ones node for
# node (check_props fails otherwise). `drng` is the detail stream (colour jitter, scattered garnish,
# coal lumps, salt grains): anything whose count or presence depends on lite() draws from drng.
rng = random.Random(1)
drng = random.Random(1001)


def lite():
    return LITE["on"]


def seg(n, lo=6):
    """Segment count, reduced for the lite build (lite aims at about a third of the triangles): a third
    of the full count, but never under 6 sides for a round thing, or `lo` when that is lower."""
    return max(min(lo, 6), int(round(n * 0.34))) if lite() else n


def regions():
    global _REG
    if _REG is None:
        path = os.path.join(ATLAS_DIR, "regions.json")
        if not os.path.exists(path):
            import vendor_atlas
            vendor_atlas.build()
        with open(path) as f:
            meta = json.load(f)
        _REG = dict(meta["regions"])
        _REG.update(meta["books"]["regions"])      # books_* atlas (spines, covers, pages)
    return _REG


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def C(hexstr, k=1.0):
    """sRGB hex -> linear RGB tuple (COLOR_0 is linear)."""
    h = hexstr.lstrip("#")
    return tuple(min(1.0, srgb_to_lin(int(h[i:i + 2], 16) / 255) * k) for i in (0, 2, 4))


WHITE = (1.0, 1.0, 1.0)


def jit(col, v=0.06):
    """Colour with a little random brightness / hue variation."""
    k = 1 + drng.uniform(-v, v)
    return tuple(min(1.0, c * k * (1 + drng.uniform(-v, v) * 0.3)) for c in col)


# ============================================================ region mapping
class Reg:
    """A UV window in the atlas: rect [u0, v0, u1, v1], optional physical size for world-scaled mapping."""

    def __init__(self, name, sub=None, phys=None, rand=True):
        self.rect = regions()[name] if isinstance(name, str) else name
        if sub:
            u0, v0, u1, v1 = self.rect
            a, b, c, d = sub
            self.rect = [u0 + (u1 - u0) * a, v0 + (v1 - v0) * b, u0 + (u1 - u0) * c, v0 + (v1 - v0) * d]
        self.phys = phys          # (metres across u, metres across v) of the whole window
        self.rand = rand

    def uv(self, s, t):
        u0, v0, u1, v1 = self.rect
        return (u0 + (u1 - u0) * min(1, max(0, s)), v0 + (v1 - v0) * min(1, max(0, t)))

    def window(self, a, b):
        """Sub-window for a face a x b metres (world-scaled, random offset) -> Reg."""
        if not self.phys:
            return self
        fa, fb = min(1.0, a / self.phys[0]), min(1.0, b / self.phys[1])
        oa = drng.uniform(0, 1 - fa) if self.rand else 0
        ob = drng.uniform(0, 1 - fb) if self.rand else 0
        r = Reg(self.rect)
        r.rect = list(self.rect)
        u0, v0, u1, v1 = self.rect
        r.rect = [u0 + (u1 - u0) * oa, v0 + (v1 - v0) * ob, u0 + (u1 - u0) * (oa + fa), v0 + (v1 - v0) * (ob + fb)]
        return r


def R(name, sub=None, phys=None):
    if isinstance(name, Reg):
        return name
    return Reg(name, sub, phys)


# Physical sizes of the tiling-style regions (metres covered by the region window)
PHYS = {"stave": (0.3, 0.4), "wood": (1.0, 0.25), "copper": (0.35, 0.35), "iron": (0.4, 0.4), "brass": (0.15, 0.15),
        "steel": (0.2, 0.2), "burlap": (0.3, 0.3), "straw": (0.05, 0.05), "paper": (0.25, 0.25),
        "kraft": (0.25, 0.25), "grate": (0.12, 0.06), "ceramic": (0.2, 0.2), "wax": (0.15, 0.15), "honeycomb": (0.12, 0.12),
        "cheese_rind": (0.3, 0.3), "coal": (0.35, 0.35), "cinnamon": (0.03, 0.1)}


def RW(name, sub=None):
    """World-scaled region (random window per face, like the carpenter's tiling kit)."""
    return Reg(name, sub, PHYS.get(name, (0.3, 0.3)))


# ============================================================ mesh builder
class Mesh:
    """Accumulates primitives into one mesh (several materials allowed). Coordinates are node-local."""

    def __init__(self, name):
        self.name = name
        self.V, self.F, self.UV, self.C, self.S, self.MI = [], [], [], [], [], []
        self.mats = []

    @property
    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def _mat(self, key):
        if key not in self.mats:
            self.mats.append(key)
        return self.mats.index(key)

    def add(self, verts, faces, uvs, M=None, col=WHITE, mat="atlas", smooth=True, cols=None):
        """verts: [Vector-like]; faces: [(i, j, k, ...)]; uvs: per face a list of (u, v) per corner."""
        M = M or Matrix()
        off = len(self.V)
        for v in verts:
            self.V.append(tuple(M @ Vector(v)))
        mi = self._mat(mat)
        for fi, f in enumerate(faces):
            self.F.append([off + i for i in f])
            self.UV.append(list(uvs[fi]))
            c = cols[fi] if cols else col
            self.C.append([tuple(c) + (1.0,)] * len(f) if len(c) == 3 else [tuple(c)] * len(f))
            self.S.append(smooth)
            self.MI.append(mi)
        return self

    # ------------------------------------------------------------ primitives
    def lathe(self, prof, seg_n=24, region="sw_satin", M=None, col=WHITE, mat="atlas", smooth=True,
              cap0=False, cap1=False, v_by="len", u_span=1.0, cap_region=None, arc=TWO_PI, u0=0.0):
        """Revolve [(r, z), ...] around local Z. u runs around (seam duplicated), v along the profile."""
        reg = R(region)
        n = seg_n
        closed = abs(arc - TWO_PI) < 1e-6
        verts, faces, uvs = [], [], []
        if v_by == "len":
            ls = [0.0]
            for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
                ls.append(ls[-1] + math.hypot(r1 - r0, z1 - z0))
            tot = ls[-1] or 1.0
            vs = [l / tot for l in ls]
        else:
            zs = [p[1] for p in prof]
            lo, hi = min(zs), max(zs)
            vs = [(z - lo) / ((hi - lo) or 1) for z in zs]
        cols_n = n + 1
        for i, (r, z) in enumerate(prof):
            for j in range(cols_n):
                a = arc * j / n + u0
                verts.append((r * math.cos(a), r * math.sin(a), z))
        for i in range(len(prof) - 1):
            for j in range(n):
                a, b = i * cols_n + j, i * cols_n + j + 1
                c, d = (i + 1) * cols_n + j + 1, (i + 1) * cols_n + j
                faces.append((a, b, c, d))
                su0, su1 = j / n * u_span, (j + 1) / n * u_span
                uvs.append([reg.uv(su0, vs[i]), reg.uv(su1, vs[i]), reg.uv(su1, vs[i + 1]), reg.uv(su0, vs[i + 1])])
        self.add(verts, faces, uvs, M, col, mat, smooth)
        creg = R(cap_region) if cap_region else None
        for flag, idx, flip in ((cap0, 0, True), (cap1, len(prof) - 1, False)):
            if not flag or prof[idx][0] < 1e-5:
                continue
            r, z = prof[idx]
            ring = [(r * math.cos(arc * j / n + u0), r * math.sin(arc * j / n + u0), z) for j in range(n)]
            if flip:
                ring = ring[::-1]
            if creg:
                uv = [creg.uv(0.5 + 0.5 * p[0] / r, 0.5 + 0.5 * p[1] / r) for p in ring]
            else:
                uv = [reg.uv(0.5, vs[idx])] * n
            self.add(ring, [tuple(range(n))], [uv], M, col, mat, False)
        return self

    def cyl(self, r1, r2, h, seg_n=16, region="sw_satin", M=None, col=WHITE, mat="atlas", caps=True,
            cap_region=None, smooth=True, z0=0.0):
        return self.lathe([(r1, z0), (r2, z0 + h)], seg_n, region, M, col, mat, smooth, cap0=caps, cap1=caps,
                          cap_region=cap_region)

    def sphere(self, r, seg_n=16, rings=10, region="sw_satin", M=None, col=WHITE, mat="atlas", scale=(1, 1, 1),
               v_by="z", smooth=True):
        prof = []
        for i in range(rings + 1):
            a = -math.pi / 2 + math.pi * i / rings
            prof.append((max(1e-5, r * math.cos(a)), r * math.sin(a)))
        S = Matrix.Diagonal((*scale, 1))
        return self.lathe(prof, seg_n, region, (M or Matrix()) @ S, col, mat, smooth, v_by=v_by)

    def box(self, size, M=None, region="sw_satin", col=WHITE, mat="atlas", faces=None, smooth=False,
            skip=()):
        """Axis box centred at the local origin. faces: {'px','nx','py','ny','pz','nz': region} overrides."""
        sx, sy, sz = (s / 2 for s in size)
        # (face key, 4 corners CCW seen from outside, (s-axis length, t-axis length))
        F = {
            "ny": ([(-sx, -sy, -sz), (sx, -sy, -sz), (sx, -sy, sz), (-sx, -sy, sz)], (2 * sx, 2 * sz)),
            "py": ([(sx, sy, -sz), (-sx, sy, -sz), (-sx, sy, sz), (sx, sy, sz)], (2 * sx, 2 * sz)),
            "px": ([(sx, -sy, -sz), (sx, sy, -sz), (sx, sy, sz), (sx, -sy, sz)], (2 * sy, 2 * sz)),
            "nx": ([(-sx, sy, -sz), (-sx, -sy, -sz), (-sx, -sy, sz), (-sx, sy, sz)], (2 * sy, 2 * sz)),
            "pz": ([(-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)], (2 * sx, 2 * sy)),
            "nz": ([(-sx, sy, -sz), (sx, sy, -sz), (sx, -sy, -sz), (-sx, -sy, -sz)], (2 * sx, 2 * sy)),
        }
        faces = faces or {}
        base = R(region)
        verts, fl, uvs = [], [], []
        for k, (pts, (a, b)) in F.items():
            if k in skip:
                continue
            reg = R(faces.get(k, base))
            reg = reg.window(a, b)
            o = len(verts)
            verts.extend(pts)
            fl.append((o, o + 1, o + 2, o + 3))
            uvs.append([reg.uv(0, 0), reg.uv(1, 0), reg.uv(1, 1), reg.uv(0, 1)])
        return self.add(verts, fl, uvs, M, col, mat, smooth)

    def loft(self, rings, region="sw_satin", M=None, col=WHITE, mat="atlas", closed=True, cap0=False, cap1=False,
             smooth=True, cap_region=None):
        """Skin rings of points (equal counts). u around the ring, v along the rings (by length)."""
        reg = R(region)
        n = len(rings[0])
        cols_n = n + 1 if closed else n
        verts, faces, uvs = [], [], []
        cent = [Vector(tuple(sum(p[i] for p in r) / n for i in range(3))) for r in rings]
        ls = [0.0]
        for a, b in zip(cent[:-1], cent[1:]):
            ls.append(ls[-1] + (b - a).length)
        tot = ls[-1] or 1
        vs = [l / tot for l in ls]
        for r in rings:
            pts = list(r) + ([r[0]] if closed else [])
            verts.extend(pts)
        m = n if closed else n - 1
        for i in range(len(rings) - 1):
            for j in range(m):
                a, b = i * cols_n + j, i * cols_n + j + 1
                c, d = (i + 1) * cols_n + j + 1, (i + 1) * cols_n + j
                faces.append((a, b, c, d))
                uvs.append([reg.uv(j / m, vs[i]), reg.uv((j + 1) / m, vs[i]), reg.uv((j + 1) / m, vs[i + 1]),
                            reg.uv(j / m, vs[i + 1])])
        self.add(verts, faces, uvs, M, col, mat, smooth)
        creg = R(cap_region) if cap_region else reg
        for flag, r, flip in ((cap0, rings[0], True), (cap1, rings[-1], False)):
            if flag and closed:
                pts = list(r)[::-1] if flip else list(r)
                c = sum((Vector(p) for p in pts), Vector()) / len(pts)
                rad = max((Vector(p) - c).length for p in pts) or 1
                # fan to a centre vertex for nicer shading on round caps
                vv = [tuple(c)] + pts
                ff = [(0, k + 1, (k + 1) % len(pts) + 1) for k in range(len(pts))]
                uv = []
                for f in ff:
                    uv.append([creg.uv(0.5 + 0.5 * (Vector(vv[i]) - c).x / rad, 0.5 + 0.5 * (Vector(vv[i]) - c).y / rad)
                               for i in f])
                self.add(vv, ff, uv, M, col, mat, smooth)
        return self

    def tube(self, pts, radius, tseg=8, region="sw_satin", M=None, col=WHITE, mat="atlas", caps=False, radii=None):
        pts = [Vector(p) for p in pts]
        rings = []
        prev_n1 = None
        for i, p in enumerate(pts):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, len(pts) - 1)]
            t = (b - a).normalized()
            if prev_n1 is None:
                up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                n1 = t.cross(up).normalized()
            else:
                n1 = (prev_n1 - t * prev_n1.dot(t)).normalized()
            n2 = t.cross(n1).normalized()
            prev_n1 = n1
            r = radii[i] if radii else radius
            rings.append([tuple(p + r * (math.cos(TWO_PI * j / tseg) * n1 + math.sin(TWO_PI * j / tseg) * n2))
                          for j in range(tseg)])
        return self.loft(rings, region, M, col, mat, closed=True, cap0=caps, cap1=caps)

    def torus(self, Rr, r, seg_n=24, tseg=8, region="sw_satin", M=None, col=WHITE, mat="atlas", arc=TWO_PI, a0=0.0):
        closed = abs(arc - TWO_PI) < 1e-6
        n = seg_n if closed else seg_n + 1
        pts = [Vector((Rr * math.cos(a0 + arc * i / seg_n), Rr * math.sin(a0 + arc * i / seg_n), 0)) for i in range(n)]
        rings = []
        for i, c in enumerate(pts):
            a = a0 + arc * i / seg_n
            radial = Vector((math.cos(a), math.sin(a), 0))
            rings.append([tuple(c + r * (math.cos(TWO_PI * j / tseg) * radial + math.sin(TWO_PI * j / tseg) * Vector((0, 0, 1))))
                          for j in range(tseg)])
        if closed:
            rings.append(rings[0])
        return self.loft(rings, region, M, col, mat, closed=True)

    def extrude(self, poly, depth, M=None, face_region="sw_satin", side_region=None, col=WHITE, mat="atlas",
                back=True, smooth_sides=False, face_col=None, bevel=0.0, back_region=None):
        """Extrude a 2D polygon (local XY, CCW) along +Z from 0 to depth. Front face (z=depth) gets
        face_region mapped by the polygon's bounding box; sides get side_region along the outline."""
        freg, sreg = R(face_region), R(side_region or face_region)
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        tris = tessellate_polygon([[Vector((x, y, 0)) for x, y in poly]])
        n = len(poly)
        top = [(x, y, depth) for x, y in poly]
        uvt = [freg.uv((x - x0) / ((x1 - x0) or 1), (y - y0) / ((y1 - y0) or 1)) for x, y in poly]
        fc = face_col or col
        if bevel > 0:
            # a small chamfer ring: inset top face, sloped band
            cx, cy = sum(xs) / n, sum(ys) / n
            ins = []
            for i in range(n):
                p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
                e0 = (p1 - p0).normalized()
                e1 = (p2 - p1).normalized()
                n0, n1 = Vector((e0.y, -e0.x)), Vector((e1.y, -e1.x))
                nn = (n0 + n1)
                nn = nn.normalized() if nn.length > 1e-6 else n0
                ins.append(p1 - nn * bevel / max(0.3, nn.dot(n0)))
            top_in = [(p.x, p.y, depth) for p in ins]
            uvi = [freg.uv((p.x - x0) / ((x1 - x0) or 1), (p.y - y0) / ((y1 - y0) or 1)) for p in ins]
            self.add(top_in, [tuple(t[::-1]) if False else tuple(t) for t in tris],
                     [[uvi[i] for i in t] for t in tris], M, fc, mat, False)
            ring_o = [(x, y, depth - bevel) for x, y in poly]
            vv = top_in + ring_o
            ff = [(n + i, n + (i + 1) % n, (i + 1) % n, i) for i in range(n)]
            uu = [[uvt[i], uvt[(i + 1) % n], uvi[(i + 1) % n], uvi[i]] for i in range(n)]
            self.add(vv, ff, uu, M, fc, mat, True)
            zt = depth - bevel
        else:
            self.add(top, [tuple(t) for t in tris], [[uvt[i] for i in t] for t in tris], M, fc, mat, False)
            zt = depth
        if back:
            bot = [(x, y, 0) for x, y in poly]
            breg = R(back_region) if back_region else freg
            uvb = [breg.uv(1 - (x - x0) / ((x1 - x0) or 1), (y - y0) / ((y1 - y0) or 1)) for x, y in poly]
            self.add(bot, [tuple(t[::-1]) for t in tris], [[uvb[i] for i in t[::-1]] for t in tris], M, col, mat, False)
        per = [0.0]
        for i in range(n):
            per.append(per[-1] + (Vector(poly[(i + 1) % n]) - Vector(poly[i])).length)
        verts, faces, uvs = [], [], []
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            o = len(verts)
            verts += [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], zt), (a[0], a[1], zt)]
            faces.append((o, o + 1, o + 2, o + 3))
            s0, s1 = per[i] / per[-1], per[i + 1] / per[-1]
            uvs.append([sreg.uv(s0, 0), sreg.uv(s1, 0), sreg.uv(s1, 1), sreg.uv(s0, 1)])
        self.add(verts, faces, uvs, M, col, mat, smooth_sides)
        return self

    def quad(self, pts, region="sw_satin", col=WHITE, mat="atlas", M=None, uvq=None, smooth=False):
        reg = R(region)
        uvq = uvq or [(0, 0), (1, 0), (1, 1), (0, 1)]
        return self.add(pts, [(0, 1, 2, 3)], [[reg.uv(*q) for q in uvq]], M, col, mat, smooth)

    def disc(self, r, seg_n=16, region="sw_satin", M=None, col=WHITE, mat="atlas", scale=(1, 1)):
        """Flat disc facing +Z, planar mapped into the region."""
        reg = R(region)
        ring = [(r * scale[0] * math.cos(TWO_PI * j / seg_n), r * scale[1] * math.sin(TWO_PI * j / seg_n), 0)
                for j in range(seg_n)]
        vv = [(0, 0, 0)] + ring
        ff = [(0, k + 1, (k + 1) % seg_n + 1) for k in range(seg_n)]
        uv = [[reg.uv(0.5 + 0.5 * vv[i][0] / (r * scale[0]), 0.5 + 0.5 * vv[i][1] / (r * scale[1])) for i in f] for f in ff]
        return self.add(vv, ff, uv, M, col, mat, False)

    def merge(self, other, M=None):
        """Append another Mesh's geometry (e.g. a reusable part) transformed by M."""
        M = M or Matrix()
        for f, uv, c, s, mi in zip(other.F, other.UV, other.C, other.S, other.MI):
            key = other.mats[mi]
            vv = [other.V[i] for i in f]
            o = len(self.V)
            for v in vv:
                self.V.append(tuple(M @ Vector(v)))
            self.F.append(list(range(o, o + len(vv))))
            self.UV.append(list(uv))
            self.C.append(list(c))
            self.S.append(s)
            self.MI.append(self._mat(key))
        return self

    # ------------------------------------------------------------ to Blender
    def to_object(self, name=None, loc=(0, 0, 0), parent=None, coll=None):
        name = name or self.name
        if not self.F:
            ob = bpy.data.objects.new(name, None)
            ob.empty_display_size = 0.05
        else:
            me = bpy.data.meshes.new(name)
            me.from_pydata(self.V, [], self.F)
            uvl = me.uv_layers.new(name="UVMap")
            uvl.data.foreach_set("uv", [c for f in self.UV for uv in f for c in uv])
            ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
            ca.data.foreach_set("color", [c for f in self.C for col in f for c in col])
            me.polygons.foreach_set("use_smooth", self.S)
            me.polygons.foreach_set("material_index", self.MI)
            for k in self.mats:
                me.materials.append(material(k))
            me.validate(clean_customdata=False)
            me.update()
            ob = bpy.data.objects.new(name, me)
        (coll or state.export_collection()).objects.link(ob)
        ob.location = loc
        if parent is not None:
            ob.parent = parent
        if ob.name != name:
            raise RuntimeError(f"name clash: {name} -> {ob.name}")
        return ob


# ============================================================ materials
_MATS = {}


def _img(name, file, non_color):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(os.path.join(ATLAS_DIR, file))
        img.name = name
        img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def _vcol_mult(nt, color_socket, bsdf):
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mixn = nt.nodes.new("ShaderNodeMix")
    mixn.data_type = 'RGBA'
    mixn.blend_type = 'MULTIPLY'
    mixn.inputs[0].default_value = 1.0
    if isinstance(color_socket, tuple):
        mixn.inputs[6].default_value = (*color_socket, 1)
    else:
        nt.links.new(color_socket, mixn.inputs[6])
    nt.links.new(vc.outputs["Color"], mixn.inputs[7])
    nt.links.new(mixn.outputs[2], bsdf.inputs["Base Color"])


def _atlas_nodes(m, color=True, rm=True, normal=True, normal_strength=1.0, atlas="atlas"):
    """Wire one of the two atlases ('atlas' = the goods, 'books' = the Bücherstand) into material m."""
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    if color:
        tc = N.new("ShaderNodeTexImage")
        tc.image = _img(f"vendor_{atlas}_color", f"{atlas}_color.png", False)
        L.new(uv.outputs[0], tc.inputs[0])
        _vcol_mult(nt, tc.outputs["Color"], b)
    else:
        _vcol_mult(nt, (1.0, 1.0, 1.0), b)
    if rm:
        tr = N.new("ShaderNodeTexImage")
        tr.image = _img(f"vendor_{atlas}_rm", f"{atlas}_rm.png", True)
        L.new(uv.outputs[0], tr.inputs[0])
        sep = N.new("ShaderNodeSeparateColor")
        L.new(tr.outputs["Color"], sep.inputs[0])
        L.new(sep.outputs[1], b.inputs["Roughness"])
        L.new(sep.outputs[2], b.inputs["Metallic"])
    if normal:
        tn = N.new("ShaderNodeTexImage")
        tn.image = _img(f"vendor_{atlas}_normal", f"{atlas}_normal.png", True)
        L.new(uv.outputs[0], tn.inputs[0])
        nm = N.new("ShaderNodeNormalMap")
        nm.uv_map = "UVMap"
        nm.inputs["Strength"].default_value = normal_strength
        L.new(tn.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs[0], b.inputs["Normal"])
    return b


def _blend(m, alpha):
    m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = alpha
    for attr, val in (("blend_method", 'BLEND'), ("surface_render_method", 'BLENDED')):
        try:
            setattr(m, attr, val)
        except Exception:
            pass


def material(key):
    """Materials by key. Names are what the glb carries (coal_glow is named by the build contract)."""
    if key in _MATS and _MATS[key].name in bpy.data.materials:
        return _MATS[key]
    if key.startswith("book:") or key == "books":
        # one material per book, book_cover_<n>, so the engine can find a book's cover by name
        m = bpy.data.materials.new(f"book_cover_{key[5:]}" if key != "books" else "vendor_books")
        m.use_nodes = True
        _atlas_nodes(m, atlas="books")
        _MATS[key] = m
        return m
    names = {"atlas": "vendor_atlas", "glaze": "vendor_glaze", "glass": "vendor_glass", "liquid": "vendor_liquid",
             "beer": "vendor_beer", "coal_glow": "coal_glow", "flame": "flame", "lamp": "lamp_glow",
             "grill_iron": "grill_iron", "lamp_shade": "vendor_lamp_shade", "foam": "vendor_foam",
             "bulb_warm": "bulb_warm"}
    m = bpy.data.materials.new(names[key])
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    if key == "atlas":
        _atlas_nodes(m)
    elif key == "foam":
        # beer head: the atlas's bubbles and wet edge, plus a little subsurface scatter so light glows through
        # the thin crown (Cycles previews) and a soft sheen (exported as KHR_materials_sheen) for the creamy
        # velvet look the engine can show
        _atlas_nodes(m, normal_strength=0.8)
        for k, v in (("Subsurface Weight", 0.15), ("Subsurface Scale", 0.004), ("Sheen Weight", 0.35),
                     ("Sheen Roughness", 0.4)):
            if k in b.inputs:
                b.inputs[k].default_value = v
        if "Subsurface Radius" in b.inputs:
            b.inputs["Subsurface Radius"].default_value = (1.0, 0.75, 0.45)
    elif key == "grill_iron":
        _atlas_nodes(m)
        # a whisper of emission so the engine's grill flare (which tints black emissive orange) leaves it dark
        b.inputs["Emission Color"].default_value = (0.012, 0.004, 0.001, 1)
        b.inputs["Emission Strength"].default_value = 1.0
    elif key == "glaze":
        _atlas_nodes(m)
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat Roughness"].default_value = 0.04
        b.inputs["Coat IOR"].default_value = 1.5
    elif key == "glass":
        _atlas_nodes(m, color=False, rm=False, normal=True, normal_strength=0.6)
        b.inputs["Roughness"].default_value = 0.03
        b.inputs["IOR"].default_value = 1.5
        if lite():
            _blend(m, 0.28)
            b.inputs["Roughness"].default_value = 0.08
        else:
            b.inputs["Transmission Weight"].default_value = 1.0
    elif key == "beer":
        _vcol_mult(m.node_tree, (1.0, 1.0, 1.0), b)
        b.inputs["Roughness"].default_value = 0.05
        b.inputs["IOR"].default_value = 1.33
        if not lite():
            b.inputs["Transmission Weight"].default_value = 0.65
    elif key == "liquid":
        # a little roughness so a wide surface (the kettle) does not mirror the copper walls and read as empty
        _vcol_mult(m.node_tree, (1.0, 1.0, 1.0), b)
        b.inputs["Roughness"].default_value = 0.14
        b.inputs["IOR"].default_value = 1.34
    elif key == "coal_glow":
        nt = m.node_tree
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        tc = nt.nodes.new("ShaderNodeTexImage")
        tc.image = _img("vendor_coal_color", "coal_color.png", False)
        te = nt.nodes.new("ShaderNodeTexImage")
        te.image = _img("vendor_coal_emit", "coal_emit.png", False)
        for t in (tc, te):
            nt.links.new(uv.outputs[0], t.inputs[0])
        _vcol_mult(nt, tc.outputs["Color"], b)
        nt.links.new(te.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = 4.0
        # dry char: fully rough, not metallic, very little specular (round 2 read as glossy orange facets)
        b.inputs["Roughness"].default_value = 1.0
        b.inputs["Metallic"].default_value = 0.0
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = 0.2
    elif key == "flame":
        b.inputs["Base Color"].default_value = (1.0, 0.75, 0.35, 1)
        b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.22, 1)
        b.inputs["Emission Strength"].default_value = 12.0
    elif key in ("lamp", "bulb_warm"):
        b.inputs["Base Color"].default_value = (1.0, 0.9, 0.7, 1)
        b.inputs["Emission Color"].default_value = (1.0, 0.78, 0.48, 1)
        b.inputs["Emission Strength"].default_value = 8.0
    elif key == "lamp_shade":
        # banker's lamp shade: cased green glass, glossy outside
        _vcol_mult(m.node_tree, (1.0, 1.0, 1.0), b)
        b.inputs["Roughness"].default_value = 0.08
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat Roughness"].default_value = 0.03
    _MATS[key] = m
    return m


# ============================================================ prop sets
# where an act_ node's origin sits, by kind, when it is not the base the item rests on
PIVOTS = {
    "grill": "act_grill: on the deck of the stall's grill opening, under the fire bowl's centre (the grill's "
             "base); act_grill_swing: the hook the grate hangs from",
    "lid": "hinge at the back rim of the kettle; rotating X negative opens it",
    "tap": "base of the handle on top of the faucet; rotating X tips the handle forward",
    "effect": "the point where steam or smoke starts",
    "kettle": "the burner's foot on the counter",
}


class PropSet:
    """One glb: a root empty at the slot origin, a merged static mesh and named nodes."""

    def __init__(self, name, slot, stall, footprint=(2.4, 0.5), note=""):
        self.name, self.slot, self.stall, self.note = name, slot, stall, note
        self.footprint = footprint
        self.static = Mesh(f"{name}_static")
        self.nodes = []              # (Mesh, name, loc, parent_name)
        self.empties = []            # (name, loc)
        self.rot = {}                # node name -> Euler XYZ applied after finish()
        self.items = {}              # act_ node -> display data for items.json

    def node(self, name, loc=(0, 0, 0), parent=None, rot=None):
        m = Mesh(name)
        self.nodes.append((m, name, tuple(loc), parent))
        if rot is not None:
            self.rot[name] = tuple(rot)
        return m

    def item(self, node, name, kind, pivot=None, **extra):
        """Register what a clickable act_ node is, for site/public/models/items.json. `pivot` says where
        the node's origin is: "base" (the point it rests on; the default for goods) unless given."""
        self.items[node] = {"name": name, "kind": kind, "pivot": pivot or PIVOTS.get(kind, "base"), **extra}

    def empty(self, name, loc, parent=None):
        self.empties.append((name, tuple(loc), parent))

    def finish(self):
        root = bpy.data.objects.new(self.name, None)
        root.empty_display_size = 0.2
        state.export_collection().objects.link(root)
        if root.name != self.name:
            raise RuntimeError("root name clash")
        objs = {self.name: root}
        if self.static.F:
            objs["static"] = self.static.to_object(parent=root)
        pending = list(self.nodes)
        # parents first
        while pending:
            rest = []
            for m, name, loc, par in pending:
                if par and par not in objs:
                    rest.append((m, name, loc, par))
                    continue
                p = objs[par] if par else root
                # named node = empty at the pivot; its mesh is a child. The web optimiser quantises
                # mesh nodes (rewrites their transforms), so the act_ transform must not carry a mesh.
                e = bpy.data.objects.new(name, None)
                e.empty_display_size = 0.05
                state.export_collection().objects.link(e)
                if e.name != name:
                    raise RuntimeError(f"name clash {name}")
                e.location = loc
                e.parent = p
                if m.F:
                    m.to_object(f"{name}_mesh", (0, 0, 0), e)
                objs[name] = e
            if len(rest) == len(pending):
                raise RuntimeError(f"missing parents: {[r[1] for r in rest]}")
            pending = rest
        for name, loc, par in self.empties:
            e = bpy.data.objects.new(name, None)
            e.empty_display_size = 0.05
            state.export_collection().objects.link(e)
            e.location = loc
            e.parent = objs[par] if par else root
            if e.name != name:
                raise RuntimeError(f"name clash {name}")
            objs[name] = e
        for k, r in self.rot.items():
            objs[k].rotation_euler = r
        self.objs = objs
        return objs

    def tris(self):
        return self.static.tris + sum(m.tris for m, *_ in self.nodes)


def world_bbox(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    bpy.context.view_layer.update()
    allo = set()
    for o in objs:
        allo.add(o)
        allo.update(o.children_recursive)
    for o in allo:
        if o.type != 'MESH':
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


# ============================================================ common goods (reusable parts)
def mat_from(M_or_loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    if isinstance(M_or_loc, Matrix):
        return M_or_loc
    S = Matrix.Diagonal((scale, scale, scale, 1)) if not isinstance(scale, (tuple, list)) else Matrix.Diagonal((*scale, 1))
    return Matrix.Translation(M_or_loc) @ Euler(rot).to_matrix().to_4x4() @ S


def T(x=0, y=0, z=0, rx=0, ry=0, rz=0, s=1.0):
    return mat_from((x, y, z), (rx, ry, rz), s)


# ============================================================ build, export, preview
def reset(seed=1, lite_mode=False):
    state.reset(seed, lite_mode=lite_mode)
    LITE["on"] = lite_mode
    _MATS.clear()
    rng.seed(seed)
    drng.seed(seed + 1000)


def tex_uri(lite_mode):
    return lambda name: "prop_tex_" + name + (".lite" if lite_mode else "") + ".webp"


SHARED_TEX = ("atlas_", "coal_", "books_")   # images shipped once as prop_tex_*.webp for all sets
TEX_FULL, TEX_LITE = 2048, 512                # the contract: lite textures are 512 px
AO_FULL, AO_LITE = 512, 256                   # per-set AO atlas (occlusion texture, TEXCOORD_1)


def export_set(name, lite_mode, items=None):
    from nmlib import export as nexport
    out = name + (".lite" if lite_mode else "")
    size = TEX_LITE if lite_mode else TEX_FULL
    if name.startswith("prop_books"):
        # the books atlas is 2048 px wide and taller than that; the optimiser fits textures inside a square,
        # so raise the limit to keep its full width (lite: 512 px wide)
        with open(os.path.join(ATLAS_DIR, "regions.json")) as f:
            bh = json.load(f)["books"].get("height", 2048)
        size = int(size * bh / 2048)
    rep = nexport.export_glb(out, texture_size=size,
                             externalize=(lambda n: n.startswith(SHARED_TEX), tex_uri(lite_mode)))
    path = os.path.join(MODELS, out + ".glb")
    mats = split_book_materials(path)
    if mats:
        rep["materials"] = mats
    if items:
        add_node_extras(path, items)
    return rep


EXTRA_KEYS = ("name", "kind", "title", "author", "cover_material")


def add_node_extras(path, items):
    """Write each clickable act_ node's display data into its glTF node extras (three.js userData), so a
    clicked node identifies itself without items.json: {name, kind[, title, author, cover_material]}."""
    import glb_tools
    js, binchunk = glb_tools.read_glb(path)
    n = 0
    for nd in js.get("nodes", []):
        it = items.get(nd.get("name", ""))
        if not it:
            continue
        ex = {k: it[k] for k in EXTRA_KEYS if k in it}
        if nd.get("extras") != ex:
            nd["extras"] = ex
            n += 1
    if n:
        glb_tools.write_glb(path, js, binchunk)
    return n


def split_book_materials(path):
    """The web optimiser's dedup() merges the identical book_cover_<n> materials into one, so every
    book ends up on book_cover_0. Give each act_book_<n> back its own copy named book_cover_<n>
    (a few hundred bytes of JSON; the textures stay shared). Returns the new material list."""
    import copy
    import re
    import glb_tools
    js, binchunk = glb_tools.read_glb(path)
    nodes, meshes, mats = js.get("nodes", []), js.get("meshes", []), js.get("materials", [])
    if not any(m.get("name", "").startswith("book_cover_") for m in mats):
        return None
    by_name = {m.get("name"): i for i, m in enumerate(mats)}
    mesh_users = {}
    for nd in nodes:
        if "mesh" in nd:
            mesh_users[nd["mesh"]] = mesh_users.get(nd["mesh"], 0) + 1
    changed = False
    for nd in nodes:
        mt = re.match(r"^act_book_(\d+)$", nd.get("name", ""))
        if not mt:
            continue
        want = f"book_cover_{mt.group(1)}"
        for ci in nd.get("children", []):
            ch = nodes[ci]
            if "mesh" not in ch:
                continue
            mi = ch["mesh"]
            prims = meshes[mi]["primitives"]
            if not any(mats[p["material"]].get("name", "").startswith("book_cover_") and
                       mats[p["material"]].get("name") != want for p in prims if "material" in p):
                continue
            if mesh_users.get(mi, 1) > 1:              # shared mesh: give this node its own copy
                meshes.append(copy.deepcopy(meshes[mi]))
                mesh_users[mi] -= 1
                mi = ch["mesh"] = len(meshes) - 1
                prims = meshes[mi]["primitives"]
            for p in prims:
                src = mats[p.get("material", 0)] if "material" in p else None
                if not src or not src.get("name", "").startswith("book_cover_"):
                    continue
                if want not in by_name:
                    mats.append(dict(copy.deepcopy(src), name=want))
                    by_name[want] = len(mats) - 1
                p["material"] = by_name[want]
                changed = True
    if changed:
        glb_tools.write_glb(path, js, binchunk)
    return [m.get("name") for m in mats]


def pivot_report(ps):
    """For every act_/rot_ node: the bounds of its geometry in the node's own frame (pivot = origin)."""
    out = {}
    bpy.context.view_layer.update()
    for name, o in ps.objs.items():
        if not name.startswith(("act_", "rot_")) or o.type != 'EMPTY':
            continue
        inv = o.matrix_world.inverted()
        org = o.matrix_world.translation
        lo = Vector((1e9, 1e9, 1e9))
        hi = -lo
        wz = 1e9
        for c in o.children_recursive:
            if c.type != 'MESH' or c.name.startswith(("act_", "foam_")) and c.name != f"{name}_mesh":
                continue
            for v in c.data.vertices:
                w = c.matrix_world @ v.co
                p = inv @ w
                lo = Vector(map(min, lo, p))
                hi = Vector(map(max, hi, p))
                wz = min(wz, w.z - org.z)
        if lo.x < 1e8:
            out[name] = {"origin": [round(v, 3) for v in org],
                         "local_min": [round(v, 3) for v in lo], "local_max": [round(v, 3) for v in hi],
                         "rest_min_z": round(wz, 4)}
    return out


def set_report(ps, rep_full, rep_lite):
    lo, hi = world_bbox([o for o in ps.objs.values()])
    return {
        "slot": ps.slot, "stall": ps.stall,
        "bbox_min": [round(v, 3) for v in lo], "bbox_max": [round(v, 3) for v in hi],
        "size": [round(h - l, 3) for l, h in zip(lo, hi)],
        "full": {"bytes": rep_full["bytes"], "triangles": rep_full["triangles"]} if rep_full else None,
        "lite": {"bytes": rep_lite["bytes"], "triangles": rep_lite["triangles"]} if rep_lite else None,
        "act_nodes": [n for n in (rep_full or rep_lite)["nodes"] if n.startswith(("act_", "light_"))],
        "materials": (rep_full or rep_lite)["materials"],
        "pivots": pivot_report(ps),
    }
