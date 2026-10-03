"""The carousel's carved galloper: one sculpted master horse shared by all 12 horse nodes.

How the master is made (full and lite):
  1. A sculpt source is built from overlapping solids, each tagged with a paint region (coat,
     hoof, mane, tail, eye, nostril, mouth, saddle, cloth, collar): the barrel, neck and head
     loft; shoulder, forearm, quarter, gaskin, chest and crest muscles; brow ridges, cheeks,
     flared nostrils and an open jaw; tapered legs with knee, hock and fetlock bulges; flame
     locks of a carved mane falling to the outer side; a three-strand tail; a carved saddle
     cloth with a scalloped edge, a saddle and a breast collar.
  2. The solids are fused with a voxel remesh, relaxed with a smoothing pass so every joint
     becomes a soft carved crease, and collapsed to the triangle target (full 2.0k,
     lite 0.72k).
  3. Each vertex takes the region of the nearest source solid. Every coat is then painted per
     region (coat colour with belly shading, dapples, blaze and socks where the coat has them;
     dark hooves; mane and tail in gilt or dark paint; glossy black eyes; a red mouth; the
     saddle cloth and breast collar in the coat's colours).
Horses with the same coat share one mesh; the thin gilt harness (bridle, reins, stirrups,
jewels, cloth cord) is one mesh shared by all twelve. So the web file stores the master once
per coat, and the engine still gets twelve separate horse_ nodes to move up and down.

The horse is built in its own frame: nose toward +X, the pole at the origin, the saddle top
about 0.24 m above it.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

import rcommon as rc
from rcommon import TAU, Part, rod, smooth_path, state, sweep
from nmlib import mats

BODY = [  # x, z, half width, half height (tail root -> muzzle)
    (-0.67, 0.07, 0.04, 0.05), (-0.63, 0.06, 0.12, 0.13), (-0.56, 0.04, 0.17, 0.19),
    (-0.45, 0.02, 0.19, 0.215), (-0.31, 0.00, 0.185, 0.205), (-0.13, -0.02, 0.172, 0.195),
    (0.05, -0.02, 0.172, 0.200), (0.21, 0.01, 0.17, 0.21), (0.33, 0.06, 0.15, 0.20),
    (0.41, 0.13, 0.115, 0.17), (0.47, 0.23, 0.092, 0.14), (0.52, 0.34, 0.078, 0.12),
    (0.56, 0.45, 0.070, 0.10), (0.61, 0.54, 0.066, 0.09), (0.67, 0.60, 0.066, 0.085),
    (0.76, 0.60, 0.062, 0.08), (0.85, 0.55, 0.052, 0.068), (0.93, 0.49, 0.045, 0.058),
    (0.98, 0.45, 0.041, 0.050), (1.01, 0.43, 0.030, 0.036),
]

# (coat, mane/tail: "gilt" or a colour, saddle cloth, collar, extras)
COATS = [
    ((0.92, 0.90, 0.86), "gilt", (0.55, 0.03, 0.04), (0.05, 0.12, 0.45), {"blush": True}),
    ((0.58, 0.58, 0.60), (0.12, 0.12, 0.13), (0.05, 0.12, 0.45), (0.55, 0.03, 0.04), {"dapple": True, "socks": 2}),
    ((0.95, 0.93, 0.88), "gilt", (0.05, 0.30, 0.12), (0.55, 0.03, 0.04), {}),
    ((0.40, 0.15, 0.06), (0.06, 0.04, 0.03), (0.55, 0.03, 0.04), (0.05, 0.30, 0.12), {"blaze": True, "socks": 4}),
    ((0.045, 0.040, 0.040), "gilt", (0.55, 0.40, 0.08), (0.55, 0.03, 0.04), {"blaze": True}),
    ((0.84, 0.58, 0.26), (0.93, 0.88, 0.76), (0.05, 0.12, 0.45), (0.55, 0.40, 0.08), {"socks": 2}),
]

HOOF = (0.05, 0.04, 0.035)
EYE = (0.015, 0.014, 0.014)
MOUTH = (0.32, 0.03, 0.04)
NOSTRIL = (0.10, 0.03, 0.03)
LEATHER = (0.16, 0.06, 0.03)
WHITE = (0.93, 0.91, 0.87)


def body_at(x):
    """Interpolated (z, half width, half height) of the barrel at x (trunk only)."""
    for a, b in zip(BODY[:-1], BODY[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * t for i in (1, 2, 3))
    return BODY[-1][1:]


def limb(part, ctrl, n=10, per=3, cap1=True):
    pts = smooth_path(ctrl, per)
    sweep(part, [p[:3] for p in pts], [p[3] for p in pts], [p[3] for p in pts], n=n, cap0=True, cap1=cap1)


# ------------------------------------------------------------------ sculpt source
def _source(lite):
    """Overlapping solids per paint region (Parts in a scratch collection)."""
    P = {k: Part(f"hsrc_{k}", "enamel", var=0.0) for k in
         ("coat", "hoof", "mane", "tail", "eye", "nostril", "mouth", "saddle", "cloth", "collar")}
    co = P["coat"]
    n = 16
    sweep(co, [(x, 0, z) for x, z, w, h in BODY], [w for *_, w, h in BODY], [h for *_, w, h in BODY], n=n)
    # muscles (the carver's masses): shoulder blade, forearm, quarters, gaskin, chest, crest, belly
    for s in (-1, 1):
        co.sphere((0.29, s * 0.095, 0.06), 1.0, seg=12, rings=8, scale=(0.13, 0.07, 0.17), rot=(0, -0.45, 0))
        co.sphere((0.33, s * 0.09, -0.14), 1.0, seg=10, rings=6, scale=(0.07, 0.06, 0.12), rot=(0, 0.3, 0))
        co.sphere((-0.47, s * 0.105, 0.05), 1.0, seg=12, rings=8, scale=(0.18, 0.085, 0.16), rot=(0, 0.25, 0))
        co.sphere((-0.45, s * 0.095, -0.15), 1.0, seg=10, rings=6, scale=(0.08, 0.065, 0.12), rot=(0, -0.4, 0))
        # head: cheek (jowl) disc and brow ridge over the eye
        co.sphere((0.745, s * 0.05, 0.545), 1.0, seg=10, rings=6, scale=(0.065, 0.028, 0.06), rot=(0, 0.4, 0))
        co.sphere((0.785, s * 0.052, 0.622), 1.0, seg=8, rings=5, scale=(0.03, 0.018, 0.014), rot=(0, 0.35, 0))
        # flared nostrils at the muzzle
        co.sphere((0.995, s * 0.025, 0.445), 1.0, seg=8, rings=5, scale=(0.028, 0.02, 0.026), rot=(0, 0.5, 0))
        P["nostril"].sphere((1.012, s * 0.030, 0.447), 1.0, seg=8, rings=4, scale=(0.012, 0.009, 0.014), rot=(0, 0.5, 0))
        P["eye"].sphere((0.79, s * 0.056, 0.603), 1.0, seg=10, rings=6, scale=(0.018, 0.012, 0.014), rot=(0, 0.3, 0))
        # ears, pricked forward
        rod(co, (0.665, s * 0.036, 0.655), (0.635, s * 0.055, 0.775), 0.024, r2=0.004, seg=8, caps=True)
    co.sphere((0.37, 0, -0.03), 1.0, seg=12, rings=8, scale=(0.09, 0.13, 0.16))           # chest
    co.sphere((0.05, 0, -0.10), 1.0, seg=12, rings=6, scale=(0.30, 0.15, 0.10))           # belly
    co.sphere((0.74, 0, 0.555), 0.07, seg=14, rings=9, scale=(1.3, 0.95, 0.85), rot=(0, 0.5, 0))   # skull
    for i in range(5):                                                                     # neck crest
        t = i / 4
        co.sphere((0.43 + 0.22 * t, 0, 0.26 + 0.34 * t), 0.05, seg=10, rings=6, scale=(1.3, 0.7, 0.8),
                  rot=(0, -0.9 + 0.4 * t, 0))
    # open mouth: the lower jaw dropped, a dark mouth inside
    limb(co, [(0.80, 0, 0.50, 0.042), (0.88, 0, 0.44, 0.034), (0.95, 0, 0.388, 0.026), (0.99, 0, 0.368, 0.021)],
         n=10, per=2)
    P["mouth"].sphere((0.94, 0, 0.408), 1.0, seg=10, rings=6, scale=(0.065, 0.028, 0.024), rot=(0, 0.45, 0))
    # legs: jumper pose, front legs tucked, hind legs stretched back; knee, hock and fetlock bulges
    legs = [
        [(0.27, 0.085, -0.06, 0.085), (0.33, 0.085, -0.26, 0.055), (0.50, 0.085, -0.31, 0.041),
         (0.47, 0.085, -0.46, 0.029), (0.50, 0.085, -0.51, 0.033)],
        [(0.27, -0.085, -0.06, 0.085), (0.31, -0.085, -0.28, 0.055), (0.45, -0.085, -0.40, 0.041),
         (0.43, -0.085, -0.55, 0.029), (0.46, -0.085, -0.60, 0.033)],
        [(-0.44, 0.10, -0.03, 0.105), (-0.39, 0.10, -0.24, 0.068), (-0.58, 0.10, -0.35, 0.043),
         (-0.71, 0.10, -0.48, 0.029), (-0.77, 0.10, -0.53, 0.033)],
        [(-0.44, -0.10, -0.03, 0.105), (-0.37, -0.10, -0.26, 0.068), (-0.54, -0.10, -0.39, 0.043),
         (-0.66, -0.10, -0.53, 0.029), (-0.72, -0.10, -0.58, 0.033)],
    ]
    for L in legs:
        limb(co, L[:-1], n=10, per=3, cap1=True)
        for j in (2, 3):                                  # knee/hock and fetlock bulges
            x, y, z, r = L[j]
            co.sphere((x, y, z), r * 1.25, seg=10, rings=6)
        a, b = Vector(L[-2][:3]), Vector(L[-1][:3])
        d = (b - a).normalized()
        rod(P["hoof"], a + d * 0.005, b + d * 0.045, 0.033, r2=0.043, seg=12, caps=True)
    # tail: three twisted strands sweeping down
    base = [(-0.64, 0, 0.07), (-0.74, 0, 0.03), (-0.81, 0, -0.10), (-0.83, 0, -0.27), (-0.78, 0, -0.41)]
    for k in range(3):
        ph = TAU * k / 3
        ctrl = []
        for i, (x, y, z) in enumerate(base):
            t = i / (len(base) - 1)
            r = 0.022 * (1 - 0.5 * t)
            a = ph + t * 4.0
            ctrl.append((x + r * math.cos(a) * 0.6, y + r * math.sin(a) * 1.4, z, 0.032 * (1 - 0.55 * t) + 0.006))
        limb(P["tail"], ctrl, n=8, per=3)
    # mane: flame locks along the crest falling to the outer side (+y), smaller locks inside
    for i in range(9):
        t = i / 8
        x = 0.40 + 0.28 * t
        z = 0.20 + 0.42 * t + 0.07
        big = 1.0 if i % 2 == 0 else 0.82
        P["mane"].sphere((x - 0.02, 0.05 + 0.008 * (i % 2), z), 0.05 * big, seg=10, rings=7,
                         scale=(0.95, 0.42, 1.85), rot=(0.42 + 0.12 * (i % 2), 0.95 - 0.45 * t, 0))
        # the lock's tip curling out and down
        P["mane"].sphere((x - 0.07, 0.085, z - 0.075), 0.026 * big, seg=8, rings=5, scale=(1.2, 0.6, 1.4),
                         rot=(0.6, 1.0 - 0.4 * t, 0))
    for i in range(4):
        t = i / 3
        x = 0.44 + 0.22 * t
        z = 0.24 + 0.38 * t + 0.07
        P["mane"].sphere((x, -0.035, z), 0.036, seg=8, rings=5, scale=(0.9, 0.45, 1.5), rot=(-0.35, 0.9 - 0.4 * t, 0))
    P["mane"].sphere((0.70, 0.0, 0.672), 0.05, seg=10, rings=6, scale=(1.25, 0.62, 0.6), rot=(0, 0.6, 0))   # forelock
    # saddle cloth: a carved shell over the barrel with a scalloped lower edge
    xs = [-0.30 + 0.48 * i / 11 for i in range(12)]
    nt = 11

    def t_bottom(x):
        u = (x - xs[0]) / (xs[-1] - xs[0])
        return -0.62 + 0.11 * abs(math.sin(math.pi * u * 3))

    for off in (0.0,):
        outer, inner = [], []
        for x in xs:
            z, w, h = body_at(x)
            tb = t_bottom(x)
            ro, ri = [], []
            for j in range(nt):
                t = tb + (math.pi - 2 * tb) * j / (nt - 1)
                ro.append(Vector((x, (w + 0.016) * math.cos(t), z + (h + 0.016) * math.sin(t))))
                ri.append(Vector((x, (w - 0.01) * math.cos(t), z + (h - 0.01) * math.sin(t))))
            outer.append(ro)
            inner.append(ri)
        # closed shell: outer surface, inner surface, and the edges joined
        bm = bmesh.new()
        vo = [[bm.verts.new(p) for p in r] for r in outer]
        vi = [[bm.verts.new(p) for p in r] for r in inner]
        for a in range(len(xs) - 1):
            for j in range(nt - 1):
                bm.faces.new((vo[a][j], vo[a + 1][j], vo[a + 1][j + 1], vo[a][j + 1]))
                bm.faces.new((vi[a][j + 1], vi[a + 1][j + 1], vi[a + 1][j], vi[a][j]))
        for a in range(len(xs) - 1):
            for j in (0, nt - 1):
                bm.faces.new((vo[a][j], vi[a][j], vi[a + 1][j], vo[a + 1][j]))
        for a in (0, len(xs) - 1):
            for j in range(nt - 1):
                bm.faces.new((vo[a][j], vo[a][j + 1], vi[a][j + 1], vi[a][j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        P["cloth"].from_bmesh(bm, grain=0)
    sd = P["saddle"]
    sd.sphere((-0.04, 0, 0.19), 1.0, seg=14, rings=8, scale=(0.22, 0.165, 0.075))
    sd.sphere((-0.21, 0, 0.235), 1.0, seg=10, rings=6, scale=(0.05, 0.13, 0.065))           # cantle
    sd.sphere((0.12, 0, 0.225), 1.0, seg=10, rings=6, scale=(0.05, 0.10, 0.06))             # pommel
    # breast collar: a carved band round the chest
    z0, w0, h0 = body_at(0.33)
    ring = []
    for i in range(13):
        a = -1.25 + 2.5 * i / 12
        ring.append((0.355 + 0.06 * math.cos(a), (w0 + 0.035) * math.sin(a), z0 + 0.02 - 0.10 * math.cos(a), 0.022))
    limb(P["collar"], ring, n=8, per=2)
    return P


def _harness(lite):
    """Thin gilt and ivory pieces kept as modelled (not remeshed): bridle, reins, stirrups,
    jewels on the breast collar, the cloth cord, the pommel knob, teeth."""
    gl = Part("h_gilt", "gilt", var=0.03)
    iv = Part("h_teeth", "ivory", var=0.0)
    ts = 4 if lite else 6
    # bridle: noseband and browband rings, cheek pieces with rosettes
    for x, z, w, h in ((0.95, 0.47, 0.05, 0.062), (0.80, 0.588, 0.070, 0.088)):
        sweep(gl, [(x - 0.008, 0, z), (x + 0.008, 0, z)], [w + 0.008] * 2, [h + 0.008] * 2,
              n=8 if lite else 12, cap0=False, cap1=False)
    for s in (-1, 1):
        if not lite:
            gl.tube([Vector((0.95, s * 0.058, 0.47)), Vector((0.87, s * 0.066, 0.53)), Vector((0.80, s * 0.078, 0.588))],
                    0.006, tseg=4)
            gl.sphere((0.87, s * 0.07, 0.53), 0.018, seg=6, rings=4, scale=(1, 0.5, 1))
        # reins from the bit to the pommel
        pts = smooth_path([(0.965, s * 0.05, 0.44), (0.62, s * 0.10, 0.40), (0.32, s * 0.13, 0.30), (0.12, s * 0.04, 0.24)], 2)
        gl.tube([Vector(p) for p in pts], 0.0065, tseg=3 if lite else 4)
        # stirrup leather and iron
        gl.box((-0.02, s * 0.205, -0.10), (0.022, 0.008, 0.22))
        gl.torus((-0.02, s * 0.212, -0.25), 0.036, 0.0065, seg=6 if lite else 10, tseg=3,
                 rot=(math.pi / 2, 0, 0))
    gl.sphere((0.13, 0, 0.27), 0.04, seg=6 if lite else 10, rings=4 if lite else 6)          # pommel knob
    # jewels along the breast collar and a medallion at the chest
    z0, w0, h0 = body_at(0.33)
    for i in range(3 if lite else 5):
        a = -1.0 + 2.0 * i / (2 if lite else 4)
        p = Vector((0.355 + 0.06 * math.cos(a) + 0.02, (w0 + 0.05) * math.sin(a), z0 + 0.02 - 0.10 * math.cos(a)))
        gl.sphere(p, 0.02, seg=5 if lite else 6, rings=3 if lite else 4)
    gl.sphere((0.45, 0, -0.075), 0.042, seg=8 if lite else 10, rings=4 if lite else 6, scale=(0.55, 1, 1))
    if not lite:
        # gilt cord along the saddle cloth's scalloped edge
        xs = [-0.30 + 0.48 * i / 12 for i in range(13)]
        for side in (1, -1):
            edge = []
            for x in xs:
                z, w, h = body_at(x)
                u = (x - xs[0]) / (xs[-1] - xs[0])
                t = -0.62 + 0.11 * abs(math.sin(math.pi * u * 3))
                if side < 0:
                    t = math.pi - t
                edge.append(Vector((x, (w + 0.02) * math.cos(t), z + (h + 0.02) * math.sin(t) - 0.002)))
            gl.tube(edge, 0.0075, tseg=3)
        for zt, xt in ((0.424, 0.99), (0.384, 0.968)):
            iv.box((xt, 0, zt), (0.018, 0.036, 0.009), rot=(0, 0.45, 0))
    return [gl, iv]


# ------------------------------------------------------------------ fuse and paint
def _scratch():
    coll = bpy.data.collections.get("HorseScratch")
    if coll is None:
        coll = bpy.data.collections.new("HorseScratch")
        bpy.context.scene.collection.children.link(coll)
    return coll


def master(lite, voxel=None, target=None):
    """Returns (mesh of the fused master, per-vertex region names, [(name, mesh, material)] of the
    harness pieces). The caller links objects that use these meshes."""
    coll = _scratch()
    P = _source(lite)
    srcs = {k: p.finish(coll) for k, p in P.items()}
    srcs = {k: o for k, o in srcs.items() if o is not None}
    # join every region solid into one object for the remesh
    bm = bmesh.new()
    for o in srcs.values():
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new("horse_fuse")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("horse_fuse", me)
    coll.objects.link(ob)
    r = ob.modifiers.new("remesh", 'REMESH')
    r.mode = 'VOXEL'
    r.voxel_size = voxel or (0.016 if lite else 0.0085)
    r.adaptivity = 0.0
    r.use_smooth_shade = True
    sm = ob.modifiers.new("smooth", 'SMOOTH')
    sm.factor = 0.6
    sm.iterations = 2 if lite else 4
    dg = bpy.context.evaluated_depsgraph_get()
    dense = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    nf = len(dense.polygons)
    ob.modifiers.clear()
    ob.data = dense
    dec = ob.modifiers.new("decimate", 'DECIMATE')
    dec.decimate_type = 'COLLAPSE'
    goal = target or (720 if lite else 2000)
    dec.ratio = min(1.0, goal / (2.0 * nf))
    dec.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    low = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    print(f"[horse] remesh {nf} quads -> {len(low.polygons)} tris ({'lite' if lite else 'full'})")
    # region per vertex: the nearest source solid
    trees = {}
    for k, o in srcs.items():
        bmk = bmesh.new()
        bmk.from_mesh(o.data)
        trees[k] = BVHTree.FromBMesh(bmk)
        bmk.free()
    regions = []
    for v in low.vertices:
        best, bd = "coat", 1e9
        for k, t in trees.items():
            hit = t.find_nearest(v.co)
            if hit[0] is not None and hit[3] < bd:
                best, bd = k, hit[3]
        regions.append(best)
    for o in list(srcs.values()) + [ob]:
        bpy.data.objects.remove(o)
    harness = []
    for p in _harness(lite):
        o = p.finish(coll)
        if o is not None:
            harness.append((o.name, o.data, p.mat))
            bpy.data.objects.remove(o)
    return low, regions, harness


def paint(low, regions, coat_idx, name):
    """A painted copy of the master for one coat: vertex colours per region, and the mane and
    tail faces on the gilt material when the coat has a gilt mane."""
    coat, mane, cloth, collar, ex = COATS[coat_idx % len(COATS)]
    me = low.copy()
    me.name = name
    me.materials.clear()
    me.materials.append(mats.get("enamel"))
    me.materials.append(mats.get("gilt"))
    cols = []
    for v, reg in zip(me.vertices, regions):
        p = v.co
        if reg == "coat":
            c = Vector(coat)
            if ex.get("dapple"):
                nn = noise.noise(Vector((p.x * 13, p.y * 13, p.z * 13)))
                c = c * (0.78 + 0.55 * max(0.0, nn))
            if ex.get("blush"):     # a warm tint on the muzzle, as painted on white gallopers
                c = c.lerp(Vector((0.90, 0.62, 0.52)), max(0.0, min(1.0, (p.x - 0.90) / 0.08)) * 0.6)
            if ex.get("blaze") and p.x > 0.78 and abs(p.y) < 0.022 + 0.01 * (p.x - 0.78) and p.z > 0.40:
                c = Vector(WHITE)
            nsock = ex.get("socks", 0)
            if nsock and p.z < -0.38:
                legs = (p.x > 0.2, p.x < -0.2)
                if (nsock >= 4 and (legs[0] or legs[1])) or (nsock == 2 and legs[1]):
                    c = Vector(WHITE)
            # shading the carver's painter adds: darker under the belly and inside the legs
            shade = 0.82 + 0.18 * max(0.0, min(1.0, (p.z + 0.25) / 0.35))
            c = c * shade
        elif reg == "hoof":
            c = Vector(HOOF)
        elif reg in ("mane", "tail"):
            c = Vector((1, 1, 1)) if mane == "gilt" else Vector(mane)
        elif reg == "eye":
            c = Vector(EYE)
        elif reg == "nostril":
            c = Vector(NOSTRIL)
        elif reg == "mouth":
            c = Vector(MOUTH)
        elif reg == "saddle":
            c = Vector(LEATHER)
        elif reg == "cloth":
            c = Vector(cloth)
        else:
            c = Vector(collar)
        cols.append((c.x, c.y, c.z, 1.0))
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)
    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set("color", [x for c in cols for x in c])
    me.color_attributes.active_color = ca
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception:
        pass
    if mane == "gilt":
        for f in me.polygons:
            rs = [regions[i] for i in f.vertices]
            if sum(r in ("mane", "tail") for r in rs) >= 2:
                f.material_index = 1
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    return me


class Herd:
    """Builds the master once per LOD and hands out horse objects that share meshes."""

    def __init__(self, lite):
        self.lite = lite
        self.low, self.regions, self.harness = master(lite)
        self.coats = {}

    def horse(self, k, coat_idx, parent, coll=None):
        coll = coll or state.export_collection()
        if coat_idx not in self.coats:
            self.coats[coat_idx] = paint(self.low, self.regions, coat_idx, f"horse_coat{coat_idx}")
        objs = []
        ob = bpy.data.objects.new(f"h{k}_carved", self.coats[coat_idx])
        coll.objects.link(ob)
        ob["nm_mat"] = "enamel"
        objs.append(ob)
        for nm, data, mat in self.harness:
            o = bpy.data.objects.new(f"h{k}_{nm.split('_', 1)[1]}", data)
            coll.objects.link(o)
            o["nm_mat"] = mat
            objs.append(o)
        for o in objs:
            o.parent = parent
            o.matrix_parent_inverse = Matrix()
            o.matrix_basis = Matrix()
        return objs
