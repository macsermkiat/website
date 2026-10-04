"""The carousel's carved galloper: one sculpted master horse shared by all 12 horse nodes.

How the master is made (full and lite):
  1. A sculpt source is built from overlapping solids, each tagged with a paint region (coat,
     hoof, mane, tail, eye, nostril, mouth, saddle, cloth, collar): the barrel, neck and head
     loft; shoulder, forearm, quarter, gaskin, chest and crest muscles; brow ridges, cheeks,
     flared nostrils and an open jaw; tapered legs with knee, hock and fetlock bulges; flame
     locks of a carved mane falling to the outer side; a three-strand tail; a carved saddle
     cloth with a scalloped edge, a saddle and a breast collar.
  2. The solids are fused with a fine voxel remesh (~120k triangles), relaxed with a smoothing
     pass so every joint becomes a soft carved crease, and collapsed to the master (full 1.3k,
     lite 0.56k triangles). The sculpt is baked onto the master as a tangent-space normal map.
  3. Each vertex of the sculpt takes the region of the nearest source solid. Every coat is
     painted per region on the sculpt (coat colour with belly shading, dapples, blaze and socks
     where the coat has them; dark hooves; mane and tail in gilt or dark paint; glossy black
     eyes; a red mouth; the saddle cloth and breast collar in the coat's colours) and baked to a
     base-colour map on the master's UVs.
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
    # saddle: a seat that dips between a tall cantle and the pommel (the rider's seat), and a skirt
    # flap down each side over the cloth with a squared lower edge (round 2: it was a smooth blob)
    sd = P["saddle"]
    sd.sphere((-0.045, 0, 0.183), 1.0, seg=14, rings=8, scale=(0.20, 0.162, 0.052))          # seat, dipped
    sd.sphere((-0.205, 0, 0.240), 1.0, seg=12, rings=6, scale=(0.055, 0.135, 0.068), rot=(0, 0.35, 0))  # cantle
    sd.sphere((0.115, 0, 0.228), 1.0, seg=10, rings=6, scale=(0.05, 0.095, 0.062), rot=(0, -0.3, 0))    # pommel
    th = 0.016 if lite else 0.012
    for s in (-1, 1):
        # skirt flap: a flattened slab following the barrel's curve, its top tucked under the seat
        sd.sphere((-0.05, s * 0.172, 0.085), 1.0, seg=12, rings=6, scale=(0.135, th, 0.115), rot=(s * 0.33, 0, 0))
        # the seat's welted edge rolling over onto the flap
        sd.sphere((-0.045, s * 0.150, 0.180), 1.0, seg=10, rings=4, scale=(0.17, 0.018, 0.018), rot=(s * 0.5, 0, 0))
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
        pts = smooth_path([(0.965, s * 0.05, 0.44), (0.62, s * 0.10, 0.40), (0.32, s * 0.13, 0.30), (0.12, s * 0.04, 0.24)], 1 if lite else 2)
        gl.tube([Vector(p) for p in pts], 0.0065, tseg=3 if lite else 4)
        # stirrup leather and iron
        gl.box((-0.02, s * 0.205, -0.10), (0.022, 0.008, 0.22))
        gl.torus((-0.02, s * 0.212, -0.25), 0.036, 0.0065, seg=5 if lite else 8, tseg=3,
                 rot=(math.pi / 2, 0, 0))
    gl.sphere((0.13, 0, 0.27), 0.04, seg=5 if lite else 8, rings=3 if lite else 5)          # pommel knob
    # jewels along the breast collar and a medallion at the chest
    z0, w0, h0 = body_at(0.33)
    for i in range(0 if lite else 5):          # lite: no jewels (the medallion stays)
        a = -1.0 + 2.0 * i / (2 if lite else 4)
        p = Vector((0.355 + 0.06 * math.cos(a) + 0.02, (w0 + 0.05) * math.sin(a), z0 + 0.02 - 0.10 * math.cos(a)))
        gl.sphere(p, 0.02, seg=5, rings=3)
    gl.sphere((0.45, 0, -0.075), 0.042, seg=6 if lite else 8, rings=3 if lite else 5, scale=(0.55, 1, 1))
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


# ------------------------------------------------------------------ fuse, bake and paint
# Round 6 pass 2: the carved detail lives in maps. The fused sculpt (a fine voxel remesh, ~120k
# triangles) is baked onto a much lighter collapsed master: a tangent-space normal map carries the
# carving (muscles, creases, mane locks, the saddle's welt and flaps), and each coat is painted on
# the dense sculpt and baked to a base-colour map, so eyes, nostrils, blaze, socks and dapples stay
# crisp however few vertices the master has. Full 1,300 triangles (was 2,000), lite 560 (was 1,050).
FULL_TRIS, LITE_TRIS = 1300, 560
NRM_PX = {False: 1024, True: 512}
COL_PX = {False: 512, True: 256}
BAKE_EXT = {False: 0.03, True: 0.04}


def _scratch():
    coll = bpy.data.collections.get("HorseScratch")
    if coll is None:
        coll = bpy.data.collections.new("HorseScratch")
        bpy.context.scene.collection.children.link(coll)
    return coll


def _regions_of(me, trees):
    out = []
    for v in me.vertices:
        best, bd = "coat", 1e9
        for k, t in trees.items():
            hit = t.find_nearest(v.co)
            if hit[0] is not None and hit[3] < bd:
                best, bd = k, hit[3]
        out.append(best)
    return out


def _unwrap(ob, px):
    """UVMap on the collapsed master: smart islands, packed with a few texels between them."""
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=4.0 / px, area_weight=0.0,
                             scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def _bake(kind, high, low, img, extrusion, margin):
    """Cycles selected-to-active bake from `high` onto `low`'s UVMap into `img`."""
    scene = bpy.context.scene
    state.configure_cycles(scene)
    scene.cycles.samples = 4
    tm = bpy.data.materials.new("hbake_target")
    tm.use_nodes = True
    tn = tm.node_tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tm.node_tree.nodes.active = tn
    old = list(low.data.materials)
    low.data.materials.clear()
    low.data.materials.append(tm)
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    kw = dict(type=kind, use_selected_to_active=True, cage_extrusion=extrusion,
              max_ray_distance=extrusion * 2.5, margin=margin, use_clear=True)
    if kind == 'NORMAL':
        kw.update(normal_space='TANGENT')
    bpy.ops.object.bake(**kw)
    _fill_misses(img)
    low.data.materials.clear()
    for m in old:
        low.data.materials.append(m)
    bpy.data.materials.remove(tm)
    img.pack()


def _fill_misses(img, iters=24):
    """Texels whose rays found no sculpt come back black: grow the neighbouring baked texels into
    them (a few texels; it also widens the islands' outer margin, which is harmless)."""
    import numpy as np
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[..., :3]
    ok = rgb.max(axis=2) > 0.02
    n0 = int((~ok).sum())
    for _ in range(iters):
        if ok.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros((h, w), np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            m = np.roll(ok, (dy, dx), axis=(0, 1))
            acc += np.roll(rgb, (dy, dx), axis=(0, 1)) * m[..., None]
            cnt += m
        grow = (~ok) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        ok = ok | grow
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    img.update()
    print(f"[horse] {img.name}: filled {n0 - int((~ok).sum())} unbaked texels of {w * h}")


def master(lite, voxel=None, target=None):
    """Returns (low mesh with UVMap, its per-vertex regions, dense sculpt object, the dense
    per-vertex regions, harness [(name, mesh, material)], normal-map image). The dense object
    stays in the scratch collection for the coat bakes; Herd removes it."""
    coll = _scratch()
    P = _source(False)                     # the fine sculpt for both LODs (it is only baked)
    srcs = {k: p.finish(coll) for k, p in P.items()}
    srcs = {k: o for k, o in srcs.items() if o is not None}
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
    r.voxel_size = voxel or 0.0085
    r.adaptivity = 0.0
    r.use_smooth_shade = True
    sm = ob.modifiers.new("smooth", 'SMOOTH')
    sm.factor = 0.6
    sm.iterations = 4
    dg = bpy.context.evaluated_depsgraph_get()
    dense = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    nf = len(dense.polygons)
    ob.modifiers.clear()
    ob.data = dense
    hi = bpy.data.objects.new("horse_dense", dense.copy())
    coll.objects.link(hi)
    dec = ob.modifiers.new("decimate", 'DECIMATE')
    dec.decimate_type = 'COLLAPSE'
    goal = target or (LITE_TRIS if lite else FULL_TRIS)
    dec.ratio = min(1.0, goal / (2.0 * nf))
    dec.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    low = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    low.name = "horse_low"
    # the collapse can leave zero-area faces, which the glTF exporter flags ("not valid"): clean them
    # before anything is computed per vertex
    low.validate(clean_customdata=False)
    print(f"[horse] remesh {nf} quads -> {len(low.polygons)} tris ({'lite' if lite else 'full'})")
    ob.modifiers.clear()
    ob.data = low
    ob.name = "horse_low"
    low.polygons.foreach_set("use_smooth", [True] * len(low.polygons))
    trees = {}
    for k, o in srcs.items():
        bmk = bmesh.new()
        bmk.from_mesh(o.data)
        trees[k] = BVHTree.FromBMesh(bmk)
        bmk.free()
    regions = _regions_of(low, trees)
    dregions = _regions_of(hi.data, trees)
    for o in list(srcs.values()):
        bpy.data.objects.remove(o)
    px = NRM_PX[lite]
    _unwrap(ob, px)
    nrm = bpy.data.images.new(f"horse_nrm{'_lite' if lite else ''}", px, px)
    nrm.colorspace_settings.name = "Non-Color"
    nrm.generated_color = (0.5, 0.5, 1.0, 1.0)
    # the cage starts this far outside the master, so mane locks and ears that the collapse
    # flattened are still found on the sculpt; rays stop at 2.5x that (no hits on the next leg)
    ext = BAKE_EXT[lite]
    _bake('NORMAL', hi, ob, nrm, ext, 4 if lite else 6)
    low = ob.data
    bpy.data.objects.remove(ob)            # the mesh lives on in the horse objects
    harness = []
    for p in _harness(lite):
        o = p.finish(coll)
        if o is not None:
            harness.append((o.name, o.data, p.mat))
            bpy.data.objects.remove(o)
    return low, regions, hi, dregions, harness, nrm


def coat_color(p, reg, coat_idx):
    """Painted colour (linear) of a point of the sculpt in region `reg` for one coat."""
    coat, mane, cloth, collar, ex = COATS[coat_idx % len(COATS)]
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
        return c * shade
    if reg == "hoof":
        return Vector(HOOF)
    if reg in ("mane", "tail"):
        return Vector((0.90, 0.60, 0.21)) if mane == "gilt" else Vector(mane)
    if reg == "eye":
        return Vector(EYE)
    if reg == "nostril":
        return Vector(NOSTRIL)
    if reg == "mouth":
        return Vector(MOUTH)
    if reg == "saddle":
        return Vector(LEATHER)
    if reg == "cloth":
        return Vector(cloth)
    return Vector(collar)


def _emit_material():
    m = bpy.data.materials.new("hbake_emit")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "Col"
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(at.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _horse_material(name, nrm, base_img=None, base=(1, 1, 1), rough=0.26, metal=0.0):
    """Principled with the shared normal map; base colour from the coat map (or a flat colour).
    No vertex-colour multiply: the masters carry no colour attribute."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    bsdf = nt.nodes["Principled BSDF"]
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    if base_img is not None:
        tc = nt.nodes.new("ShaderNodeTexImage")
        tc.image = base_img
        L.new(uv.outputs[0], tc.inputs[0])
        L.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = nrm
    L.new(uv.outputs[0], tn.inputs[0])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    L.new(tn.outputs["Color"], nm.inputs["Color"])
    L.new(nm.outputs[0], bsdf.inputs["Normal"])
    return m


class Herd:
    """Builds the master once per LOD, bakes its normal map and one colour map per coat, and
    hands out horse objects that share meshes."""

    def __init__(self, lite, coats=range(6)):
        self.lite = lite
        self.low, self.regions, hi, dregions, self.harness, self.nrm = master(lite)
        sfx = "_lite" if lite else ""
        self.gilt = _horse_material(f"horse_gilt{sfx}", self.nrm, base=(0.90, 0.60, 0.21), rough=0.30, metal=0.5)
        # every coat painted on the dense sculpt, then baked onto the master's UVs
        coll = _scratch()
        low_ob = bpy.data.objects.new("horse_bake_low", self.low)
        coll.objects.link(low_ob)
        emit = _emit_material()
        hi.data.materials.clear()
        hi.data.materials.append(emit)
        ca = hi.data.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
        verts = hi.data.vertices
        self.coats = {}
        px = COL_PX[lite]
        for ci in coats:
            cols = []
            for v, reg in zip(verts, dregions):
                c = coat_color(v.co, reg, ci)
                cols.extend((c.x, c.y, c.z, 1.0))
            ca.data.foreach_set("color", cols)
            hi.data.update()
            img = bpy.data.images.new(f"horse_coat{ci}{sfx}", px, px)
            _bake('EMIT', hi, low_ob, img, BAKE_EXT[lite], 3 if lite else 4)
            mat = _horse_material(f"horse_coat{ci}{sfx}", self.nrm, base_img=img)
            self.coats[ci] = self._painted(ci, mat)
        bpy.data.objects.remove(low_ob)
        bpy.data.objects.remove(hi)
        bpy.data.materials.remove(emit)

    def _painted(self, ci, mat):
        coat, mane, *_ = COATS[ci % len(COATS)]
        me = self.low.copy()
        me.name = f"horse_coat{ci}"
        me.materials.clear()
        me.materials.append(mat)
        me.materials.append(self.gilt)
        if mane == "gilt":
            for f in me.polygons:
                rs = [self.regions[i] for i in f.vertices]
                f.material_index = 1 if sum(r in ("mane", "tail") for r in rs) >= 2 else 0
        me.update()
        return me

    def horse(self, k, coat_idx, parent, coll=None):
        coll = coll or state.export_collection()
        objs = []
        ob = bpy.data.objects.new(f"h{k}_carved", self.coats[coat_idx % 6])
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
