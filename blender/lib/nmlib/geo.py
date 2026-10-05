"""Part: accumulate many primitives into one mesh with tiling UVs and per-part tints.

Every primitive gets
  * UVMap (TEXCOORD_0): a box projection in the primitive's own frame, in metres, with the
    wood grain along the primitive's long axis and a random offset into the tiling kit
    texture, so neighbouring planks show different grain;  for `paint` the board is mapped
    into one colour band of the paint atlas instead;
  * Col (COLOR_0): tint x random per-part variation x shade(world position) (grime, soot).
    glTF multiplies COLOR_0 into the base colour, three.js does the same.
AO lives in a second UV map that nmlib.bake adds at export time.
"""
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import state

TWO_PI = 2 * math.pi

# Paint atlas: 8 horizontal bands, each tiling along U. Order is part of the kit contract.
PAINT_BANDS = ["red", "gold", "blue", "white", "green", "cream", "black", "rauten"]
BAND_PHYS = 0.125          # metres of board height one band covers without stretching
BAND_LEN = 1.0             # metres along the board per U unit
BAND_PAD = 6 / 1024        # UV padding inside a band against bleeding

# Tiling textures: metres covered by one texture repeat.
TILE = {"wood": 1.0, "oak": 1.0, "iron": 0.5, "iron_matte": 0.5, "copper_old": 0.5, "rauten": 0.26,
        "mirror_foxed": 0.85}
# materials mapped into the paint atlas bands (band=...)
BAND_MATS = {"paint", "paint_glow", "paint_lit"}

# Named tints (linear multipliers of the light neutral kit wood).
TINTS = {
    "pine":    (1.00, 0.86, 0.66),
    "honey":   (0.95, 0.72, 0.46),
    "oak":     (0.72, 0.52, 0.34),
    "dark":    (0.42, 0.28, 0.18),
    "walnut":  (0.30, 0.19, 0.12),
    "grey":    (0.70, 0.66, 0.60),
    "soot":    (0.22, 0.18, 0.15),
    "shingle": (0.55, 0.42, 0.30),
    "white":   (1.0, 1.0, 1.0),
}


def resolve_tint(t):
    if t is None:
        return (1.0, 1.0, 1.0)
    if isinstance(t, str):
        return TINTS[t]
    return tuple(t)


def rng():
    return state.rng


class Part:
    """One output mesh object = one material. Add primitives, then finish()."""

    def __init__(self, name, mat, shade=None, smooth=False, tint=None, var=0.08, bevel=None):
        self.name = name
        self.mat = mat                      # material key, see nmlib.mats
        self.kind = "band" if mat in BAND_MATS else ("tile" if mat in TILE else "flat")
        self.shade = shade
        self.smooth = smooth
        self.default_tint = tint
        self.var = var
        self.default_bevel = bevel
        self.V, self.F, self.UV, self.C, self.S = [], [], [], [], []
        self.curve_simplify = 6.0      # degrees; outline points of text/shapes closer than this merge
        self.lite_flat_text = True     # lite: letters are a single front face (no depth)
        self.flat_text = False         # True: letters are a single front face in full builds too
                                       # (painted lettering; about a third of the triangles)

    # ------------------------------------------------------------------ emit
    def _emit(self, bm, M, grain=None, tint=None, band=None, var=None, smooth=None,
              uv_off=None, shade=True, uv_scale=1.0):
        R = rng()
        bm.verts.index_update()
        bm.normal_update()
        if not bm.faces:
            bm.free()
            return
        if grain is None:
            lo = [min(v.co[i] for v in bm.verts) for i in range(3)]
            hi = [max(v.co[i] for v in bm.verts) for i in range(3)]
            ext = [hi[i] - lo[i] for i in range(3)]
            grain = max(range(3), key=lambda i: ext[i])
        tint = resolve_tint(tint if tint is not None else self.default_tint)
        var = self.var if var is None else var
        k = 1.0 + R.uniform(-var, var)
        kc = (k * (1 + R.uniform(-var, var) * 0.25), k, k * (1 + R.uniform(-var, var) * 0.35))
        base = tuple(min(1.0, tint[i] * kc[i]) for i in range(3))
        smooth = self.smooth if smooth is None else smooth
        ou, ov = (R.random(), R.random()) if uv_off is None else uv_off

        # band mapping needs the across extent per dominant axis pair
        if self.kind == "band":
            bi = PAINT_BANDS.index(band or "red")
            b_lo = 1.0 - (bi + 1) / len(PAINT_BANDS)      # bands stacked from top (v=1)
            b_h = 1.0 / len(PAINT_BANDS)
            lo = [min(v.co[i] for v in bm.verts) for i in range(3)]
            hi = [max(v.co[i] for v in bm.verts) for i in range(3)]
            band_rand = R.random()

        off = len(self.V)
        MW = M
        for v in bm.verts:
            self.V.append(tuple(MW @ v.co))
        T = TILE.get(self.mat, 1.0) * uv_scale
        for f in bm.faces:
            n = f.normal
            a = max(range(3), key=lambda i: abs(n[i]))
            if a != grain:
                o = 3 - a - grain
                ia, ib = o, grain
            else:
                ia, ib = (grain + 1) % 3, (grain + 2) % 3
            self.F.append([off + l.vert.index for l in f.loops])
            self.S.append(smooth)
            for l in f.loops:
                p = l.vert.co
                if self.kind == "tile":
                    self.UV.append((p[ia] / T + ou, p[ib] / T + ov))
                elif self.kind == "band":
                    along = p[ib] / BAND_LEN + ou
                    across_axis = ia if a != grain else ia
                    amin, amax = lo[across_axis], hi[across_axis]
                    ext = max(amax - amin, 1e-6)
                    room = b_h - 2 * BAND_PAD
                    t = (p[across_axis] - amin) / ext
                    if ext <= BAND_PHYS:
                        span = room * ext / BAND_PHYS
                        vv = b_lo + BAND_PAD + band_rand * (room - span) + t * span
                    else:
                        vv = b_lo + BAND_PAD + t * room
                    self.UV.append((along, vv))
                else:
                    self.UV.append((p[ia] + ou, p[ib] + ov))
                c = base
                if shade and self.shade is not None:
                    s = self.shade(MW @ p)
                    if isinstance(s, (int, float)):
                        c = (c[0] * s, c[1] * s, c[2] * s)
                    else:
                        c = (c[0] * s[0], c[1] * s[1], c[2] * s[2])
                self.C.append((c[0], c[1], c[2], 1.0))
        bm.free()

    # ------------------------------------------------------------------ primitives
    def box(self, center, size, rot=(0, 0, 0), bevel=None, segs=1, grain=None, jitter=0.0,
            bevel_segments=1, **kw):
        """Axis box of `size` (metres) rotated by Euler `rot`, centred at `center`."""
        R = rng()
        sx, sy, sz = size
        if jitter:
            sx *= 1 + R.uniform(-jitter, jitter)
            sz *= 1 + R.uniform(-jitter * 0.3, jitter * 0.3)
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        self.mbox(M, (sx, sy, sz), bevel=bevel, segs=segs, grain=grain,
                  bevel_segments=bevel_segments, **kw)

    def mbox(self, M, size, bevel=None, segs=1, grain=None, bevel_segments=1, drop=None, **kw):
        """Box of `size` in the frame M. drop: local faces never seen, left out to save
        triangles, e.g. ("-z",) for the underside of a shingle lying on the deck."""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        g = grain if grain is not None else max(range(3), key=lambda i: size[i])
        # segs: int = pieces along the grain, or (nx, ny, nz) pieces along each local axis
        # (extra vertices for vertex shading such as the counter-edge wear)
        per_axis = tuple(segs) if isinstance(segs, (tuple, list)) else \
            tuple(segs if i == g else 1 for i in range(3))
        for ax, n in enumerate(per_axis):
            if n > 1:
                edges = [e for e in bm.edges if abs((e.verts[0].co - e.verts[1].co)[ax]) > 1e-6 and
                         all(abs((e.verts[0].co - e.verts[1].co)[k]) < 1e-6 for k in range(3) if k != ax)]
                bmesh.ops.subdivide_edges(bm, edges=edges, cuts=n - 1, use_grid_fill=True)
        if drop:
            bm.normal_update()
            axes = {"x": 0, "y": 1, "z": 2}
            dead = []
            for d in drop:
                sgn, ax = (-1.0 if d[0] == "-" else 1.0), axes[d[-1]]
                dead += [f for f in bm.faces if f.normal[ax] * sgn > 0.99]
            bmesh.ops.delete(bm, geom=list(set(dead)), context='FACES_ONLY')
        b = self.default_bevel if bevel is None else bevel
        if b is None:
            b = 0.004 if self.kind != "flat" else 0.0
        if state.lite() or (not state.bevels() and b < 0.01):
            b = 0.0                     # scenery builds (state.set_bevels(False)) keep only >= 1 cm rounds
        if b and min(size) > 2.6 * b:
            bm.normal_update()
            sharp = [e for e in bm.edges if len(e.link_faces) == 2 and
                     e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) > 0.5]
            bmesh.ops.bevel(bm, geom=sharp, offset=b, offset_type='OFFSET',
                            segments=bevel_segments, profile=0.5, affect='EDGES',
                            clamp_overlap=True)
        self._emit(bm, M, grain=g, **kw)

    def slab(self, p0, p1, width, thick, up=(0, 0, 1), **kw):
        """Board from p0 to p1 (grain along it), `width` across, `thick` along the face normal.
        `up` picks which way the board's width points (projected perpendicular to the axis)."""
        p0, p1 = Vector(p0), Vector(p1)
        ax = (p1 - p0)
        L = ax.length
        ax.normalize()
        upv = Vector(up)
        wv = (upv - ax * upv.dot(ax))
        if wv.length < 1e-6:
            wv = Vector((1, 0, 0)) - ax * ax.x
        wv.normalize()
        nv = ax.cross(wv)
        B = Matrix((ax, wv, nv)).transposed().to_4x4()
        M = Matrix.Translation((p0 + p1) / 2) @ B
        self.mbox(M, (L, width, thick), grain=0, **kw)

    def cyl(self, center, r1, r2, depth, seg=16, rot=(0, 0, 0), caps=True, grain=2, **kw):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg,
                              radius1=r1, radius2=r2, depth=depth)
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        kw.setdefault("smooth", True)
        self._emit(bm, M, grain=grain, **kw)

    def sphere(self, center, radius, seg=12, rings=8, scale=(1, 1, 1), rot=(0, 0, 0), **kw):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=radius)
        for v in bm.verts:
            v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        kw.setdefault("smooth", True)
        self._emit(bm, M, grain=2, **kw)

    def ico(self, center, radius, subd=1, scale=(1, 1, 1), **kw):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=radius)
        for v in bm.verts:
            v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
        kw.setdefault("smooth", True)
        self._emit(bm, Matrix.Translation(center), grain=2, **kw)

    def lathe(self, profile, seg=24, M=None, caps=False, **kw):
        """Revolve [(radius, z), ...] around local Z."""
        bm = bmesh.new()
        rings = []
        for r, z in profile:
            ring = [bm.verts.new((r * math.cos(TWO_PI * j / seg), r * math.sin(TWO_PI * j / seg), z))
                    for j in range(seg)]
            rings.append(ring)
        for i in range(len(rings) - 1):
            for j in range(seg):
                jj = (j + 1) % seg
                bm.faces.new((rings[i][j], rings[i][jj], rings[i + 1][jj], rings[i + 1][j]))
        if caps:
            bm.faces.new(list(reversed(rings[0])))
            bm.faces.new(rings[-1])
        kw.setdefault("smooth", True)
        self._emit(bm, M or Matrix(), grain=2, **kw)

    def loft(self, rings, closed=True, cap_start=False, cap_end=False, grain=2, **kw):
        """Skin consecutive rings of points (same count). closed: rings are loops."""
        bm = bmesh.new()
        vr = [[bm.verts.new(Vector(p)) for p in r] for r in rings]
        n = len(vr[0])
        m = n if closed else n - 1
        for i in range(len(vr) - 1):
            for j in range(m):
                jj = (j + 1) % n
                bm.faces.new((vr[i][j], vr[i][jj], vr[i + 1][jj], vr[i + 1][j]))
        if cap_start and closed:
            bm.faces.new(list(reversed(vr[0])))
        if cap_end and closed:
            bm.faces.new(vr[-1])
        self._emit(bm, Matrix(), grain=grain, **kw)

    def tube(self, pts, radius, tseg=6, **kw):
        bm = bmesh.new()
        pts = [Vector(p) for p in pts]
        rings = []
        for i, p in enumerate(pts):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, len(pts) - 1)]
            t = (b - a).normalized()
            up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n1 = t.cross(up).normalized()
            n2 = t.cross(n1).normalized()
            rings.append([bm.verts.new(p + radius * (math.cos(TWO_PI * j / tseg) * n1 +
                                                     math.sin(TWO_PI * j / tseg) * n2))
                          for j in range(tseg)])
        for i in range(len(rings) - 1):
            for j in range(tseg):
                jj = (j + 1) % tseg
                bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][jj], rings[i][jj]))
        kw.setdefault("smooth", True)
        self._emit(bm, Matrix(), grain=2, **kw)

    def torus(self, center, R, r, seg=16, tseg=8, rot=(0, 0, 0), arc=TWO_PI, **kw):
        bm = bmesh.new()
        closed = abs(arc - TWO_PI) < 1e-6
        n = seg if closed else seg + 1
        rings = []
        for i in range(n):
            a = arc * i / seg
            ring = []
            for j in range(tseg):
                b = TWO_PI * j / tseg
                ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a),
                                          (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
            rings.append(ring)
        pairs = [(i, (i + 1) % n) for i in range(n if closed else n - 1)]
        for i, k in pairs:
            for j in range(tseg):
                jj = (j + 1) % tseg
                bm.faces.new((rings[i][j], rings[k][j], rings[k][jj], rings[i][jj]))
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        kw.setdefault("smooth", True)
        self._emit(bm, M, grain=2, **kw)

    def shape(self, outer, holes=(), depth=0.02, M=None, bevel=None, grain=0, **kw):
        """Extrude a 2D polygon (local XY, metres) with optional holes by `depth` along Z (centred).
        Holes are cut out (even-odd fill)."""
        cu = bpy.data.curves.new("tmp_shape", "CURVE")
        cu.dimensions = '2D'
        cu.fill_mode = 'BOTH'
        cu.extrude = depth / 2
        b = 0.0 if bevel is None else bevel
        if state.lite():
            b = 0.0
        if b:
            cu.bevel_depth = b
            cu.bevel_resolution = 0
            cu.extrude = max(depth / 2 - b, 0.0005)
        for poly in [outer] + list(holes):
            sp = cu.splines.new('POLY')
            sp.points.add(len(poly) - 1)
            for i, (x, y) in enumerate(poly):
                sp.points[i].co = (x, y, 0, 1)
            sp.use_cyclic_u = True
        self._emit_curve(cu, M, grain, **kw)

    def text(self, body, font_path, size, depth, M=None, align='CENTER', resolution=2,
             bevel=None, spacing=1.0, max_width=None, grain=0, **kw):
        """3D text (Blender font curve) in local XY, extruded along Z. Returns (width, height)."""
        cu = bpy.data.curves.new("tmp_text", "FONT")
        cu.body = body
        cu.font = load_font(font_path)
        cu.size = size
        cu.extrude = depth / 2
        cu.space_character = spacing
        cu.align_x = align
        cu.align_y = 'CENTER'
        cu.resolution_u = max(1, resolution - (1 if state.lite() else 0))
        b = 0.0012 if bevel is None else bevel
        flat = False
        if self.flat_text:
            b = 0.0
            flat = True
            cu.extrude = 0.0
            cu.fill_mode = 'FRONT'
        elif state.lite():
            b = 0.0
            flat = self.lite_flat_text
            if flat:                    # lite: one front face per glyph, no sides or back
                cu.extrude = 0.0
                cu.fill_mode = 'FRONT'
        if b:
            cu.bevel_depth = b
            cu.bevel_resolution = 0
        if flat:
            M = (M or Matrix()) @ Matrix.Translation((0, 0, depth / 2))
        dims = self._emit_curve(cu, M, grain, max_width=max_width, **kw)
        return dims

    def _emit_curve(self, cu, M, grain, max_width=None, **kw):
        ob = bpy.data.objects.new("tmp_curve_ob", cu)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        bm = bmesh.new()
        bm.from_mesh(me)
        xs = [v.co.x for v in bm.verts] or [0]
        ys = [v.co.y for v in bm.verts] or [0]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if max_width and w > max_width:
            s = max_width / w
            for v in bm.verts:
                v.co.x *= s
                v.co.y *= s
            w, h = w * s, h * s
        # thin out the outline (fonts carry many near-colinear points) and merge the flat fill
        simp = self.curve_simplify * (2.0 if state.lite() else 1.0)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(simp), verts=list(bm.verts),
                                 edges=list(bm.edges), use_dissolve_boundaries=False)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4],
                              quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        bpy.data.curves.remove(cu)
        self._emit(bm, M or Matrix(), grain=grain, **kw)
        return w, h

    def from_bmesh(self, bm, M=None, grain=None, **kw):
        self._emit(bm, M or Matrix(), grain=grain, **kw)

    # ------------------------------------------------------------------ finish
    @property
    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def finish(self, coll=None):
        """Create the Blender object (or return None when empty)."""
        from . import mats
        if not self.F:
            return None
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.V, [], self.F)
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", [c for t in self.UV for c in t])
        ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
        ca.data.foreach_set("color", [c for t in self.C for c in t])
        me.polygons.foreach_set("use_smooth", self.S)
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        (coll or state.export_collection()).objects.link(ob)
        me.materials.append(mats.get(self.mat))
        ob["nm_mat"] = self.mat
        return ob


_fonts = {}


def load_font(path):
    if path not in _fonts:
        _fonts[path] = bpy.data.fonts.load(path, check_existing=True)
    return _fonts[path]


# ---------------------------------------------------------------------- helpers
def look_rot(direction, up=(0, 0, 1)):
    """Euler that turns local -Z toward `direction` (for cameras / cam_view empties)."""
    return Vector(direction).to_track_quat('-Z', 'Y').to_euler()


def catenary(a, b, sag, n):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]


def star_polygon(cx, cy, r_out, r_in, n=5, rot=math.pi / 2):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = rot + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle_polygon(cx, cy, r, n=12):
    return [(cx + r * math.cos(TWO_PI * i / n), cy + r * math.sin(TWO_PI * i / n)) for i in range(n)]


def heart_polygon(cx, cy, s, n=20):
    pts = []
    for i in range(n):
        t = TWO_PI * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 32, cy + y * s / 32))
    return pts
