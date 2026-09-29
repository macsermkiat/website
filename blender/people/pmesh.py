"""Organizer's mesh accumulator: vertices with skin weights, per-corner UVs, vertex colour and
materials, turned into one Blender mesh object bound to an armature.

Everything here is plain Python + mathutils so a figure is built as data first and only becomes
a Blender object at the end (one object per figure part group: `body` and optional `mug`).
"""
import math

import bpy
from mathutils import Vector, Matrix

TAU = 2 * math.pi


def V(*a):
    if len(a) == 1:
        return Vector(a[0])
    return Vector(a)


def smoothstep(e0, e1, x):
    if e1 == e0:
        return 1.0 if x >= e1 else 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def norm_w(w):
    """Keep the 4 largest influences and normalise."""
    items = sorted(((k, v) for k, v in w.items() if v > 1e-4), key=lambda kv: -kv[1])[:4]
    s = sum(v for _, v in items) or 1.0
    return {k: v / s for k, v in items}


class Mesh:
    def __init__(self):
        self.V = []      # Vector
        self.C = []      # (r, g, b) linear
        self.W = []      # {bone: weight}
        self.F = []      # (idx tuple, uv tuple per corner, material, smooth)

    @property
    def tris(self):
        return sum(len(f[0]) - 2 for f in self.F)

    # ---------------------------------------------------------------- low level
    def vert(self, p, col=(1, 1, 1), w=None):
        self.V.append(Vector(p))
        self.C.append(tuple(col))
        self.W.append(norm_w(w or {}))
        return len(self.V) - 1

    def face(self, idx, uvs, mat, smooth=True):
        self.F.append((tuple(idx), tuple(uvs), mat, smooth))

    # ---------------------------------------------------------------- grids and lofts
    def grid(self, P, mat, wfn, col=(1, 1, 1), closed=True, uv_tile=(0.1, 0.1), smooth=True,
             cap_start=False, cap_end=False, flip=False, uvs=None):
        """P: rows (rings) of points. Rows run along the part; columns around it.
        wfn(p, i, j) -> weight dict; col is a tuple or fn(p, i, j) -> rgb.
        closed: wrap columns (tube). UV u = arc length / tile_u, v = row distance / tile_v."""
        R = len(P)
        Cn = len(P[0])
        idx = []
        for i, row in enumerate(P):
            r = []
            for j, p in enumerate(row):
                c = col(p, i, j) if callable(col) else col
                r.append(self.vert(p, c, wfn(p, i, j)))
            idx.append(r)
        # uv coordinates (per corner so closed tubes wrap without splitting normals)
        if uvs is None:
            U = []
            for i, row in enumerate(P):
                acc = [0.0]
                pts = row + ([row[0]] if closed else [])
                for a, b in zip(pts[:-1], pts[1:]):
                    acc.append(acc[-1] + (b - a).length)
                U.append([a / uv_tile[0] for a in acc])
            Vv = [0.0]
            for i in range(1, R):
                d = sum((P[i][j] - P[i - 1][j]).length for j in range(Cn)) / Cn
                Vv.append(Vv[-1] + d)
            Vv = [v / uv_tile[1] for v in Vv]
            uvs = lambda i, j: (U[i][j], Vv[i])  # noqa: E731
        ncols = Cn if closed else Cn - 1
        for i in range(R - 1):
            for j in range(ncols):
                j2 = (j + 1) % Cn
                jj2 = j + 1  # uv column index (may be Cn for the wrap)
                q = [idx[i][j], idx[i][j2], idx[i + 1][j2], idx[i + 1][j]]
                uv = [uvs(i, j), uvs(i, jj2), uvs(i + 1, jj2), uvs(i + 1, j)]
                if flip:
                    q.reverse(); uv.reverse()
                self.face(q, uv, mat, smooth)
        if closed:
            for (i, cap) in ((0, cap_start), (R - 1, cap_end)):
                if not cap:
                    continue
                ring = idx[i]
                cen = sum((P[i][j] for j in range(Cn)), Vector()) / Cn
                c = col(cen, i, 0) if callable(col) else col
                ci = self.vert(cen, c, wfn(cen, i, 0))
                for j in range(Cn):
                    j2 = (j + 1) % Cn
                    tri = [ring[j], ring[j2], ci]
                    if (i == 0) != flip:
                        tri.reverse()
                    self.face(tri, [(0.5, 0.5)] * 3, mat, smooth)
        return idx

    def loft(self, rings, mat, wfn, **kw):
        return self.grid(rings, mat, wfn, closed=True, **kw)

    def sphere(self, c, r, mat, wfn, seg=12, rings=8, scale=(1, 1, 1), M=None, col=(1, 1, 1),
               deform=None, uv_tile=(0.05, 0.05)):
        """UV sphere (poles as tiny rings). deform(p_local) -> p_local."""
        M = M or Matrix()
        P = []
        for i in range(rings + 1):
            ph = math.pi * (i / rings)
            ph = min(max(ph, 0.02), math.pi - 0.02)
            row = []
            for j in range(seg):
                th = TAU * j / seg
                p = Vector((math.sin(ph) * math.cos(th) * r * scale[0], math.sin(ph) * math.sin(th) * r * scale[1],
                            -math.cos(ph) * r * scale[2]))
                if deform:
                    p = deform(p)
                row.append(M @ (Vector(c) + p))
            P.append(row)
        return self.grid(P, mat, wfn, col=col, closed=True, cap_start=True, cap_end=True, uv_tile=uv_tile)

    def box(self, c, size, mat, wfn, M=None, col=(1, 1, 1), smooth=False):
        M = M or Matrix()
        hx, hy, hz = (s / 2 for s in size)
        c = Vector(c)
        pts = [M @ (c + Vector((sx * hx, sy * hy, sz * hz))) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
        ids = [self.vert(p, col(p, 0, 0) if callable(col) else col, wfn(p, 0, 0)) for p in pts]
        faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        for f in faces:
            self.face([ids[k] for k in f], [(0, 0), (1, 0), (1, 1), (0, 1)], mat, smooth)

    def cyl(self, a, b, r1, r2, mat, wfn, seg=8, col=(1, 1, 1), caps=True, smooth=True, up=None):
        a, b = Vector(a), Vector(b)
        d = (b - a).normalized()
        up = Vector(up) if up else (Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0)))
        x = d.cross(up).normalized()
        y = d.cross(x)
        P = []
        for p, r in ((a, r1), (b, r2)):
            P.append([p + (x * math.cos(TAU * j / seg) + y * math.sin(TAU * j / seg)) * r for j in range(seg)])
        return self.grid(P, mat, wfn, col=col, closed=True, cap_start=caps, cap_end=caps, smooth=smooth)

    def tube(self, pts, radii, mat, wfn, seg=8, col=(1, 1, 1), caps=True, up=(0, 0, 1), scale=(1, 1),
             uv_tile=(0.1, 0.1), twist=None):
        """Tube along a polyline. radii: float or list. scale: (along side, along up) ellipse."""
        pts = [Vector(p) for p in pts]
        n = len(pts)
        if not isinstance(radii, (list, tuple)):
            radii = [radii] * n
        P = []
        up = Vector(up)
        for i, p in enumerate(pts):
            if i == 0:
                d = pts[1] - pts[0]
            elif i == n - 1:
                d = pts[-1] - pts[-2]
            else:
                d = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
            d.normalize()
            u = up - d * up.dot(d)
            if u.length < 1e-6:
                u = Vector((1, 0, 0)) - d * d.x
            u.normalize()
            s = d.cross(u)
            ring = []
            for j in range(seg):
                a = TAU * j / seg + (twist(i) if twist else 0.0)
                ring.append(p + (s * math.cos(a) * scale[0] + u * math.sin(a) * scale[1]) * radii[i])
            P.append(ring)
        return self.grid(P, mat, wfn, col=col, closed=True, cap_start=caps, cap_end=caps, uv_tile=uv_tile)

    def merge(self, other):
        off = len(self.V)
        self.V += other.V
        self.C += other.C
        self.W += other.W
        for idx, uv, m, s in other.F:
            self.F.append((tuple(i + off for i in idx), uv, m, s))

    # ---------------------------------------------------------------- to Blender
    def to_object(self, name, materials, arm_ob, collection):
        """materials: {name: bpy material}. Returns the skinned mesh object."""
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.V], [], [f[0] for f in self.F])
        mat_names = []
        for f in self.F:
            if f[2] not in mat_names:
                mat_names.append(f[2])
        for mn in mat_names:
            me.materials.append(materials[mn])
        mi = {mn: i for i, mn in enumerate(mat_names)}
        uvl = me.uv_layers.new(name="UVMap")
        li = 0
        for pi, f in enumerate(self.F):
            poly = me.polygons[pi]
            poly.material_index = mi[f[2]]
            poly.use_smooth = f[3]
            for k in range(len(f[0])):
                uvl.data[poly.loop_start + k].uv = f[1][k]
            li += len(f[0])
        ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
        for i, c in enumerate(self.C):
            ca.data[i].color = (c[0], c[1], c[2], 1.0)
        me.color_attributes.active_color = ca
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        groups = {}
        for i, w in enumerate(self.W):
            for b, x in w.items():
                g = groups.get(b)
                if g is None:
                    g = groups[b] = ob.vertex_groups.new(name=b)
                g.add([i], x, 'REPLACE')
        ob.parent = arm_ob
        mod = ob.modifiers.new("Armature", 'ARMATURE')
        mod.object = arm_ob
        return ob
