"""Market square: cobbled plaza (fan pattern), gutters, ring street, curbs, sidewalk, puddles,
cast-iron street lamps, string-light poles with swagged bulb wires, benches, bins, bollards and a
snow layer.  Exports site/public/models/square.glb (and square.lite.glb with LITE=1).

Round 1 pass 2: worn relief (settled hollows and a trodden low line) displaces the plaza on a denser
mesh; puddles lie in the hollows with soft, see-through edges; the kerb's riser now runs under the
kerbstones (a sliver of the ground's riser, with a degenerate UV, poked through every other stone and
rendered black); the tree benches stand 6.6 m from the fir; the string-light poles clear the tree
(blender/square/check_clash.py tests it); lamps, poles, benches, bins, bollards and kerbs carry
per-vertex occlusion through a ramp stored in the ground's AO image; light_ empties are ranked by name.

Run:  /home/claude/tools/bpy-venv/bin/python blender/square/square.py
      (full + AO bake; build the town first so its houses shade the sidewalk)
      LITE=1 (same command) for square.lite.glb (reuses the ground AO, bakes its own part occlusion)
"""
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import architect_common as C
import architect_plan as P
import architect_tex as TX

LITE = bool(os.environ.get("LITE"))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
random.seed(3)
scene = C.reset()
col = C.collection("Square")
occ = C.collection("Occluders")

# ------------------------------------------------------------------ textures & materials
T_COB = C.make_texture_set("square", "cobble_fan", lambda: TX.cobble_fan(1024, 3.2), normal_strength=5.0)
T_SETT = C.make_texture_set("square", "setts", lambda: TX.setts(1024, 2.4), normal_strength=5.0)
T_WALK = C.make_texture_set("square", "setts_warm", lambda: TX.setts(1024, 2.4, row_m=0.16, len_range=(0.16, 0.26), seed=27, warm=True), normal_strength=4.0)
T_GRAN = C.make_texture_set("square", "granite", lambda: TX.granite(512), normal_strength=2.0)
T_WOOD = C.make_texture_set("square", "timber", lambda: TX.timber(512), normal_strength=3.0)

AO_PATH = os.path.join(C.tex_dir("square"), "square_ao.png")
AO_X0, AO_SIZE = -80.0, 160.0      # the lightmap covers the whole ground mesh (r <= 78)
ao_img = None
REUSE_AO = bool(os.environ.get("REUSE_AO")) and os.path.exists(AO_PATH)
if (LITE or REUSE_AO) and os.path.exists(AO_PATH):
    ao_img = C.load_img(AO_PATH, True)
elif not LITE:
    ao_img = bpy.data.images.new("square_ao", 8, 8)   # placeholder, replaced by the bake

if LITE:
    # Round 1 pass 3, lite budget: the cobble fan keeps 512 px; the setts (gutter, street, sidewalk and
    # bands all share one set, the sidewalk and bands through a warm factor) drop to 256 px, the kerb
    # granite to 256 px without a normal map, and the bench and pole timber to 256 px colour only.
    T_SETT = C.lite_texture_set(T_SETT, 256)
    T_WALK = dict(T_SETT)
    T_GRAN = C.lite_texture_set(T_GRAN, 256, keep=("color", "rough"))
    T_WOOD = C.lite_texture_set(T_WOOD, 256, keep=("color",))
WARM = (1.08, 0.98, 0.86) if LITE else None
M = {}
M["cobble"] = C.pbr("cobble_fan", tex=T_COB, vcol="grime", ao_img=ao_img, normal_strength=1.0)
M["gutter"] = C.pbr("setts_gutter", tex=T_SETT, vcol="grime", ao_img=ao_img, factor=(0.85, 0.85, 0.88))
M["street"] = C.pbr("setts_street", tex=T_SETT, vcol="grime", ao_img=ao_img)
M["walk"] = C.pbr("setts_sidewalk", tex=T_WALK, vcol="grime", ao_img=ao_img, factor=WARM)
M["curb"] = C.pbr("granite_curb", tex=T_GRAN, factor=(0.95, 0.93, 0.9))
M["iron"] = C.solid("cast_iron", (0.018, 0.024, 0.021), rough=0.42, metal=0.75)
M["wood"] = C.pbr("bench_wood", tex=T_WOOD, factor=(1.25, 1.1, 1.0), rough=0.7)
M["pole"] = C.pbr("pole_wood", tex=T_WOOD, factor=(0.8, 0.75, 0.7), rough=0.75)
M["wire"] = C.solid("wire_black", (0.01, 0.01, 0.01), rough=0.5)
M["bulb"] = C.solid("bulb_warm", (1.0, 0.8, 0.55), rough=0.3, emit=(1.0, 0.62, 0.28), strength=6.0)
M["snow"] = C.solid("snow", (0.82, 0.85, 0.92), rough=0.75)
M["puddle"] = C.pbr("puddle_water", color=(0.035, 0.034, 0.032), rough=0.05, vcol="puddle")
M["bands"] = C.pbr("granite_bands", tex=T_WALK, factor=(1.0, 0.98, 0.93) if not LITE else (1.08, 0.98, 0.86), ao_img=ao_img)
for m in M.values():
    m.use_backface_culling = True
# the puddle's vertex alpha (0 at the rim) drives its opacity: a thin film over the wet cobbles
_pn = M["puddle"].node_tree
_vc = next(n for n in _pn.nodes if n.type == "VERTEX_COLOR")
_pn.links.new(_vc.outputs["Alpha"], _pn.nodes["Principled BSDF"].inputs["Alpha"])
M["puddle"].surface_render_method = "BLENDED"

UV = {"cobble": (3.2, 3.2), "gutter": (2.4, 2.4), "street": (2.4, 2.4), "walk": (2.4, 2.4)}

# ------------------------------------------------------------------ ground profile
NTH = 96 if LITE else 176
K_ARC = round(2 * math.pi * 42 / 2.4) * 2.4 / (2 * math.pi)      # arc-length scale so the texture closes
grime_noise = TX.pnoise(256, 6, 5, 0.55, seed=5)                    # covers 160 m
mid_noise = TX.pnoise(256, 22, 3, 0.5, seed=17)                     # ~7 m patches of damp and dry


def grime_at(x, y):
    u = ((x + 80) / 160 * 256) % 256; v = ((y + 80) / 160 * 256) % 256
    i, j = int(u), int(v)
    fu, fv = u - i, v - j
    a = grime_noise[j % 256, i % 256]; b = grime_noise[j % 256, (i + 1) % 256]
    c = grime_noise[(j + 1) % 256, i % 256]; d = grime_noise[(j + 1) % 256, (i + 1) % 256]
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


relief_noise = TX.pnoise(256, 28, 3, 0.5, seed=12)                 # ~6 m features over 160 m
random.seed(31)
# settled hollows (x, y, radius, depth).  Round 1 pass 3: the first three sit where the home camera
# (three.js [3, 9, 33]) looks at the paving between itself and the section stalls, so their puddles show
# in the home view; the rest are scattered over the plaza.
HOME_HOLLOWS = [(-3.2, -12.5, 3.4, 0.03), (5.8, -8.2, 2.8, 0.026), (0.8, -17.0, 2.4, 0.024)]
HOLLOWS = list(HOME_HOLLOWS)
while len(HOLLOWS) < 19:
    tt = random.uniform(0, 2 * math.pi); rr = 30 * math.sqrt(random.random())
    HOLLOWS.append((rr * math.cos(tt), rr * math.sin(tt), random.uniform(1.6, 3.6), random.uniform(0.012, 0.03)))
random.seed(3)


def _bilin(a, x, y):
    n = a.shape[0]
    u = ((x + 80) / 160 * n) % n; v = ((y + 80) / 160 * n) % n
    i, j = int(u), int(v); fu, fv = u - i, v - j
    return ((a[j % n, i % n] * (1 - fu) + a[j % n, (i + 1) % n] * fu) * (1 - fv)
            + (a[(j + 1) % n, i % n] * (1 - fu) + a[(j + 1) % n, (i + 1) % n] * fu) * fv)


def relief(x, y):
    """Worn relief of the plaza (m, added to the camber): gentle settling, hollows where water
    stands, and a trodden low line along the main walk from the home view to the bandstand.
    Fades out 1.5 m before the gutter so the edge profile stays clean."""
    r = math.hypot(x, y)
    Rp = P.plaza_r(math.atan2(y, x) % (2 * math.pi))
    fade = min(1.0, max(0.0, (Rp - 1.5 - r) / 3.0))
    if fade <= 0:
        return 0.0
    h = 0.016 * (_bilin(relief_noise, x, y) - 0.5)
    for hx, hy, hr, hd in HOLLOWS:
        d2 = ((x - hx) ** 2 + (y - hy) ** 2) / (hr * hr)
        if d2 < 4:
            h -= hd * math.exp(-d2 * 1.6)
    h -= 0.012 * trodden(x, y)                                                   # the trodden walk
    return h * fade


def trodden(x, y):
    """0..1: how worn the paving is by feet.  The main walk runs from the home view (three.js z = 33)
    to the bandstand; a cross lane runs in front of the four section stalls."""
    w = math.exp(-((x + 0.35 * math.sin(y * 0.21)) / 3.2) ** 2) * min(1.0, max(0.0, (4 - y) / 3.0)) * min(1.0, max(0.0, (y + 34) / 4.0))
    lane = math.exp(-((y + 5.0 + 0.004 * x * x) / 2.6) ** 2) * min(1.0, max(0.0, (16 - abs(x)) / 4.0))
    return max(w, 0.8 * lane)


def profile(t):
    """Radial samples for angle t: list of (r, z, zone) from the centre outward."""
    Rp = P.plaza_r(t)
    ex = P.exit_at(t, P.house_r(t), pad=0.5) >= 0
    pts = []
    # a ring every ~1.9 m so the relief reads (the lite ground keeps the camber only)
    inner = [0.04 + 0.92 * k / 18 for k in range(19)] + [0.975] if not LITE else [0.2, 0.45, 0.7, 0.88]
    for f in inner:
        r = Rp * f
        pts.append((r, -0.06 * f * f, "cobble"))     # relief is added per vertex (build_ground)
    pts.append((Rp, -0.06, "cobble"))
    # gutter: shallow V of three rows of setts
    pts += [(Rp + 0.25, -0.1, "gutter"), (Rp + GW, -0.075, "gutter")]
    # street with a crown
    nst = 5 if not LITE else 3
    for k in range(1, nst + 1):
        s = GW + P.STREET_W * k / nst
        z = -0.075 + 0.06 * math.sin(math.pi * (s - GW) / P.STREET_W)
        pts.append((Rp + s, z, "street"))
    if ex:
        # the street runs out between the houses
        pts += [(Rp + P.CURB_S, -0.07, "street"), (Rp + P.CURB_S + 4, -0.04, "street"),
                (Rp + P.CURB_S + 14, 0.0, "street"), (78, 0.02, "street")]
    else:
        # the riser up to the sidewalk sits in the middle of the kerbstones (which span CURB_S..+0.3),
        # so no sliver of it can poke out in front of a stone
        pts += [(Rp + P.CURB_S - 0.25, -0.11, "gutter"), (Rp + P.CURB_S + 0.12, -0.08, "gutter"),
                (Rp + P.CURB_S + 0.16, P.SIDEWALK_Z, "walk"),
                (Rp + P.CURB_S + 3, P.SIDEWALK_Z + 0.02, "walk"), (78, P.SIDEWALK_Z + 0.05, "walk")]
    return pts


GW = P.GUTTER_W


def ground_height(x, y):
    t = math.atan2(y, x) % (2 * math.pi); r = math.hypot(x, y)
    pr = profile(t)
    rel = 0.0 if LITE else relief(x, y)
    if r <= pr[0][0]:
        return pr[0][1] + rel
    for (r0, z0, _), (r1, z1, _) in zip(pr, pr[1:]):
        if r0 <= r <= r1:
            return z0 + (z1 - z0) * (r - r0) / max(r1 - r0, 1e-6) + rel
    return pr[-1][1]


def build_ground():
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    cl = bm.loops.layers.color.new("grime")
    zones = ["cobble", "gutter", "street", "walk"]
    cols = []
    for i in range(NTH + 1):
        t = 2 * math.pi * i / NTH
        cols.append((t, profile(t)))
    # profiles may have different lengths (exits); build per column pair by matching radii indices
    centre = bm.verts.new((0, 0, 0.0 if LITE else relief(0, 0)))
    vcols = []
    for t, pr in cols:
        vcols.append([bm.verts.new((r * math.cos(t), r * math.sin(t),
                                    z + (0.0 if LITE else relief(r * math.cos(t), r * math.sin(t))))) for r, z, _ in pr])

    def uv_of(zone, x, y, t, r, Rp):
        if zone == "cobble":
            return (x / UV["cobble"][0], y / UV["cobble"][1])
        s = r - Rp
        arc = t * K_ARC
        if zone == "gutter":
            return (arc / 2.4, s / 2.4)
        if zone == "street":
            return (s / 2.4, arc / 2.4)
        return (arc / 2.4, s / 2.4)

    def shade(x, y, zone, r, Rp):
        """Large-scale grime and wetness (COLOR_0, multiplied into the base colour).  Round 1 pass 3:
        stronger contrast so the paving never reads as one repeating tile from the home view: dry,
        dusty patches against damp ones (7 m noise over 27 m noise), a dark, wet trodden walk and lane,
        damp hollows and wet gutters."""
        g = grime_at(x, y)
        m = _bilin(mid_noise, x, y)
        v = 0.34 + 0.62 * g ** 1.2 + 0.34 * (m - 0.5)
        s = r - Rp
        if -1.2 < s < GW + 0.3 or (P.CURB_S - 0.6 < s < P.CURB_S + 0.05):
            v *= 0.72                      # wet, dirty edges along the gutters
        if zone == "walk":
            v *= 1.05
        if zone == "cobble":
            v *= 1.0 - 0.36 * trodden(x, y)                               # the walk: wet and dark
            if not LITE:
                v *= 1.0 + 12.0 * min(0.0, relief(x, y) + 0.004)          # damp, darker hollows
        return min(max(v, 0.22), 1.0)

    faces = 0
    for i in range(NTH):
        (t0, p0), (t1, p1) = cols[i], cols[i + 1]
        v0, v1 = vcols[i], vcols[i + 1]
        # centre fan
        f = bm.faces.new((centre, v0[0], v1[0]))
        f.material_index = 0
        for l in f.loops:
            co = l.vert.co
            l[uvl].uv = (co.x / 3.2, co.y / 3.2)
            g = shade(co.x, co.y, "cobble", co.length, 36)
            l[cl] = (g, g, g, 1)
        n = min(len(p0), len(p1))
        for k in range(n - 1):
            zone = p0[k + 1][2] if len(p0) == len(p1) else p0[min(k + 1, len(p0) - 1)][2]
            a, b, c, d = v0[k], v0[k + 1], v1[k + 1], v1[k]
            try:
                f = bm.faces.new((a, b, c, d))
            except ValueError:
                continue
            f.material_index = zones.index(zone)
            for l, (tt, pr) in zip(f.loops, [(t0, p0), (t0, p0), (t1, p1), (t1, p1)]):
                co = l.vert.co
                r = math.hypot(co.x, co.y)
                Rp = P.plaza_r(tt)
                l[uvl].uv = uv_of(zone, co.x, co.y, tt, r, Rp)
                g = shade(co.x, co.y, zone, r, Rp)
                l[cl] = (g, g, g, 1)
        # if one profile is longer (exit edge), close with the extra outer ring as walk/street
        if len(p0) != len(p1):
            lo, hi = (v0, v1) if len(p0) < len(p1) else (v1, v0)
            for k in range(len(lo) - 1, len(hi) - 1):
                try:
                    f = bm.faces.new((lo[-1], hi[k], hi[k + 1]) if len(p0) < len(p1) else (hi[k + 1], hi[k], lo[-1]))
                except ValueError:
                    continue
                f.material_index = 2
                for l in f.loops:
                    co = l.vert.co; tt = math.atan2(co.y, co.x) % (2 * math.pi)
                    l[uvl].uv = uv_of("street", co.x, co.y, tt, math.hypot(co.x, co.y), P.plaza_r(tt))
                    g = shade(co.x, co.y, "street", math.hypot(co.x, co.y), P.plaza_r(tt)); l[cl] = (g, g, g, 1)
    bmesh.ops.remove_doubles(bm, verts=[vcols[0][k] for k in range(len(vcols[0]))] + [vcols[-1][k] for k in range(len(vcols[-1]))], dist=1e-5)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    me = bpy.data.meshes.new("ground")
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("ground", me)
    col.objects.link(ob)
    for z in zones:
        me.materials.append(M[z])
    for p in me.polygons: p.use_smooth = True
    return ob


ground = build_ground()
C.log("ground tris", C.count_tris([ground]))

places = P.layout_places()
TREE_B = next(((x, y) for (_id, kind, x, y, _r, _p) in places if _id == "tree"), (6.5, 15.0))

# ------------------------------------------------------------------ bands of granite slabs dividing the cobble field
bands = C.Geo("plaza_bands", M["bands"], (7.2, 7.2))


def strip(path, width):
    """Flat strip following a 2D polyline, draped on the ground."""
    L = 0.0
    prev = None
    left, right, us = [], [], []
    for i, (x, y) in enumerate(path):
        a = path[max(i - 1, 0)]; b = path[min(i + 1, len(path) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1
        nx, ny = -ty / ln * width / 2, tx / ln * width / 2
        if prev: L += math.hypot(x - prev[0], y - prev[1])
        prev = (x, y)
        for side, lst in ((1, left), (-1, right)):
            px, py = x + side * nx, y + side * ny
            lst.append((px, py, ground_height(px, py) + 0.008))
        us.append(L)
    verts = left + right
    n = len(path)
    faces, uvs = [], []
    for i in range(n - 1):
        faces.append((i, n + i, n + i + 1, i + 1))
        uvs.append([(us[i] / 7.2, 0), (us[i] / 7.2, width / 7.2), (us[i + 1] / 7.2, width / 7.2), (us[i + 1] / 7.2, 0)])
    bands.raw(verts, faces, uvs)


RB = 25.8
nseg = 96 if not LITE else 48
strip([(RB * math.cos(2 * math.pi * k / nseg), RB * math.sin(2 * math.pi * k / nseg)) for k in range(nseg + 1)], 0.6)
for k in range(8):
    t = math.radians(22.5 + 45 * k)
    r1 = P.plaza_r(t) - 0.05
    pts = [((RB + 0.3 + (r1 - RB - 0.3) * j / 6) * math.cos(t), (RB + 0.3 + (r1 - RB - 0.3) * j / 6) * math.sin(t)) for j in range(7)]
    strip(pts, 0.6)
# a ring of slabs round the tree
tpx, tpy = TREE_B
strip([(tpx + 3.4 * math.cos(2 * math.pi * k / 40), tpy + 3.4 * math.sin(2 * math.pi * k / 40)) for k in range(41)], 0.5)
bands_ob = bands.finish(col)

# ------------------------------------------------------------------ curbs (individual granite stones)
curb = C.Geo("curbs", M["curb"], (0.8, 0.8))
t = 0.0
while t < 2 * math.pi:
    Rp = P.plaza_r(t)
    r = Rp + P.CURB_S + 0.15
    L = random.uniform(0.8, 1.25) if not LITE else 2.0
    dt = L / r
    tm = t + dt / 2
    if P.exit_at(tm, P.house_r(tm), pad=0.5) < 0:
        rm = P.plaza_r(tm) + P.CURB_S + 0.15
        cx, cy = rm * math.cos(tm), rm * math.sin(tm)
        h = 0.3
        ztop = P.SIDEWALK_Z + 0.02 + random.uniform(-0.006, 0.006)
        # chord length of the stone, tangent orientation
        curb.box((cx, cy, ztop - h / 2), (L - 0.012, 0.3, h),
                 rot=(random.uniform(-0.006, 0.006), random.uniform(-0.008, 0.008), tm + math.pi / 2 + random.uniform(-0.01, 0.01)),
                 skip_bottom=True)
    t += dt
curb_ob = curb.finish(col)

# ------------------------------------------------------------------ puddles
# Water stands in the settled hollows and along the gutters.  Each puddle is a fan with an opaque-ish
# core and a rim that fades to nothing (vertex alpha), so it reads as a film over wet cobbles.
occupied = [(x, y, 3.2) for (_id, kind, x, y, _r, _p) in places if kind in ("section", "deco", "landmark")]
occupied.append((TREE_B[0], TREE_B[1], 3.5))


def free_spot(x, y, rad):
    return all(math.hypot(x - ox, y - oy) > orad + rad for ox, oy, orad in occupied)


pbm = bmesh.new()
p_uv = pbm.loops.layers.uv.new("UVMap")
p_col = pbm.loops.layers.color.new("puddle")


def puddle(x, y, rad, core=0.72):
    nv = 10 if LITE else 14
    ph = [random.uniform(0, 6.28) for _ in range(3)]
    stretch = random.uniform(1.0, 1.5); rot = random.uniform(0, math.pi)
    zc = ground_height(x, y) + 0.008
    c = pbm.verts.new((x, y, zc))
    inner, outer = [], []
    for k in range(nv):
        a = 2 * math.pi * k / nv
        rr = rad * (1 + 0.25 * math.sin(2 * a + ph[0]) + 0.15 * math.sin(3 * a + ph[1]) + 0.08 * math.sin(5 * a + ph[2]))
        lx, ly = rr * math.cos(a) * stretch, rr * math.sin(a) / stretch
        dx, dy = lx * math.cos(rot) - ly * math.sin(rot), lx * math.sin(rot) + ly * math.cos(rot)
        for f, lst in ((0.62, inner), (1.0, outer)):
            px_, py_ = x + dx * f, y + dy * f
            lst.append(pbm.verts.new((px_, py_, max(zc - 0.004, ground_height(px_, py_) + 0.006))))
    alpha = {c: core}
    alpha.update({v: core for v in inner}); alpha.update({v: 0.0 for v in outer})
    for k in range(nv):
        j = (k + 1) % nv
        for f in (pbm.faces.new((c, inner[k], inner[j])), pbm.faces.new((inner[k], outer[k], outer[j], inner[j]))):
            for l in f.loops:
                l[p_uv].uv = (l.vert.co.x / 2, l.vert.co.y / 2)
                l[p_col] = (1, 1, 1, alpha[l.vert])


npud = 0
for hi, (hx, hy, hr, hd) in enumerate(HOLLOWS):     # the home-view hollows first, then the deepest
    if LITE and npud >= 5:
        break
    if hd > 0.018 and free_spot(hx, hy, hr * 0.5) and math.hypot(hx, hy) > 4:
        big = hi < len(HOME_HOLLOWS)
        puddle(hx, hy, (1.25 if hi == 0 else 0.95) if big else min(0.9, hr * 0.3), core=0.5 if big else 0.62); npud += 1
# thin wet films along the trodden walk: nearly clear, they only catch the lights (glossy streaks)
nfilm = 0
if not LITE:
    for k in range(9):
        fy = -30 + k * 3.3 + random.uniform(-0.8, 0.8)
        fx = random.uniform(-2.2, 2.2) - 0.35 * math.sin(fy * 0.21)
        if free_spot(fx, fy, 1.5) and not any(math.hypot(fx - hx, fy - hy) < 2.2 for hx, hy, _, _ in HOME_HOLLOWS):
            puddle(fx, fy, random.uniform(1.0, 1.7), core=random.uniform(0.28, 0.4)); nfilm += 1
C.log("wet films", nfilm)
tries = 0
while npud < (10 if not LITE else 7) and tries < 500:        # along the gutters
    tries += 1
    t = random.uniform(0, 2 * math.pi)
    r = P.plaza_r(t) + random.choice([0.2, 0.3, P.CURB_S - 0.2])
    rad = random.uniform(0.3, 0.7)
    x, y = r * math.cos(t), r * math.sin(t)
    if free_spot(x, y, rad) and P.exit_at(t, P.house_r(t), pad=0.5) < 0:
        puddle(x, y, rad, core=0.6); npud += 1
pme = bpy.data.meshes.new("puddles"); pbm.normal_update(); pbm.to_mesh(pme); pbm.free()
pud_ob = bpy.data.objects.new("puddles", pme); col.objects.link(pud_ob)
pme.materials.append(M["puddle"])
C.log("puddles", npud)

# ------------------------------------------------------------------ street lamps
iron = C.Geo("street_iron", M["iron"], (1, 1))
snowp = C.Geo("snow_props", M["snow"], (1, 1))
bulb_objs, light_objs = [], []


def lamp(idx, x, y, rot):
    z0 = ground_height(x, y)
    F = Matrix.Translation((x, y, z0)) @ Matrix.Rotation(rot, 4, "Z")
    iron.frame = F; snowp.frame = F
    seg = 6 if LITE else 8
    iron.cyl((0, 0, 0.18), 0.2, 0.17, 0.36, seg=seg, bottom=False)
    if not LITE:
        iron.cyl((0, 0, 0.39), 0.15, 0.12, 0.06, seg=seg, bottom=False)
        iron.cyl((0, 0, 0.52), 0.12, 0.09, 0.22, seg=seg, bottom=False)
        iron.cyl((0, 0, 1.6), 0.092, 0.092, 0.07, seg=seg, caps=False)
    # fluted shaft (star section)
    nfl = 16 if not LITE else 6
    shaft = []
    for zz, rr in ((0.6, 0.085), (3.1, 0.058)):
        ring = []
        for k in range(nfl):
            a = 2 * math.pi * k / nfl
            rk = rr * (1.0 if k % 2 == 0 else 0.86) if not LITE else rr
            ring.append((rk * math.cos(a), rk * math.sin(a), zz))
        shaft.append(ring)
    verts = shaft[0] + shaft[1]
    faces = [(k, (k + 1) % nfl, nfl + (k + 1) % nfl, nfl + k) for k in range(nfl)]
    iron.raw(verts, faces)
    iron.cyl((0, 0, 3.12), 0.1, 0.085, 0.1, seg=seg, caps=False)
    # ladder rest bar with ball ends
    if not LITE:
        iron.beam((-0.34, 0, 3.02), (0.34, 0, 3.02), 0.028, 0.028)
        for sx in (-0.36, 0.36):
            iron.uvsphere((sx, 0, 3.02), 0.035, seg=6, rings=3)
    # lantern: base cup, six posts, roof, finial
    iron.cyl((0, 0, 3.26), 0.06, 0.17, 0.2, seg=6)
    ztop = 3.9
    bulbs = C.Geo(f"bulbs_lamp_{idx:02d}", M["bulb"], (1, 1)); bulbs.frame = F
    corners0, corners1 = [], []
    for k in range(6):
        a = 2 * math.pi * k / 6
        corners0.append((0.17 * math.cos(a), 0.17 * math.sin(a), 3.36))
        corners1.append((0.25 * math.cos(a), 0.25 * math.sin(a), ztop))
    for k in range(6 if not LITE else 0):          # the lite lantern is its glowing glass and roof
        iron.beam(corners0[k], corners1[k], 0.018, 0.018, up=(corners0[k][0], corners0[k][1], 0))
    iron.cyl((0, 0, 3.37), 0.18, 0.18, 0.025, seg=6, caps=False)
    iron.cyl((0, 0, ztop + 0.02), 0.27, 0.27, 0.04, seg=6)
    iron.cyl((0, 0, ztop + 0.18), 0.31, 0.06, 0.28, seg=6, bottom=False)
    if not LITE:
        iron.cyl((0, 0, ztop + 0.36), 0.06, 0.05, 0.08, seg=6, caps=False)
        iron.uvsphere((0, 0, ztop + 0.45), 0.045, seg=6, rings=3)
    # glowing frosted glass (bulbs_) slightly inside the frame
    for k in range(6):
        k2 = (k + 1) % 6
        s = 0.94
        a0 = Vector(corners0[k]) * 1; a1 = Vector(corners0[k2]) * 1
        b0 = Vector(corners1[k]) * 1; b1 = Vector(corners1[k2]) * 1
        for v in (a0, a1, b0, b1):
            v.x *= s; v.y *= s
        bulbs.poly([tuple(a0), tuple(a1), tuple(b1), tuple(b0)])
    bulbs.poly([tuple(Vector(c) * Vector((0.94, 0.94, 1))) for c in corners1][::-1])
    ob = bulbs.finish(col)
    bulb_objs.append(ob)
    lw = F @ Vector((0, 0, 3.62))
    # plaza-edge lamps first (light_lamp_00..11), then the street-corner lamps (light_lamp_street_*)
    nm = f"light_lamp_{idx:02d}" if idx < N_PLAZA_LAMPS else f"light_lamp_street_{idx - N_PLAZA_LAMPS:02d}"
    light_objs.append(C.empty(nm, lw, col))
    # snow on the lantern roof
    snowp.cyl((0, 0, ztop + 0.2), 0.3, 0.07, 0.24, seg=6, caps=False)
    iron.frame = Matrix.Identity(4); snowp.frame = Matrix.Identity(4)


lamp_spots = []
N_PLAZA_LAMPS = 12
for k in range(N_PLAZA_LAMPS):
    t = math.radians(15 + 30 * k + random.uniform(-4, 4))
    if P.exit_at(t, P.plaza_r(t) + 1, pad=1.0) >= 0:
        t += math.radians(6)
    r = P.plaza_r(t) - 1.1
    for _ in range(12):          # step clear of a ride's footprint (the Ferris wheel reaches the plaza edge)
        if not P.in_ride(r * math.cos(t), r * math.sin(t), pad=1.0):
            break
        t += math.radians(3)
        r = P.plaza_r(t) - 1.1
    lamp_spots.append((r * math.cos(t), r * math.sin(t), random.uniform(0, 6.28)))
# corner lamps on the sidewalk next to each exit
for deg, w in P.EXITS:
    t = math.radians(deg) + (w / 2 + 1.2) / P.house_r(math.radians(deg))
    r = P.plaza_r(t) + P.CURB_S + 0.9
    lamp_spots.append((r * math.cos(t), r * math.sin(t), random.uniform(0, 6.28)))
if LITE:
    lamp_spots = lamp_spots[:12]
for i, (x, y, rot) in enumerate(lamp_spots):
    lamp(i, x, y, rot)

# ------------------------------------------------------------------ string-light poles, wires and bulbs
wood = C.Geo("poles_wood", M["pole"], (1.0, 1.0))
wire = C.Geo("string_wire", M["wire"], (1, 1))
poles = [C.three_to_blender(x, z) for x, z in P.POLES_THREE]
for i, p in enumerate(poles):
    z0 = ground_height(p.x, p.y)
    H = P.pole_h(i)
    seg = 7 if LITE else 10
    rb = 0.11 if H < 8 else 0.14          # the tall poles behind the bandstand are stouter
    wood.cyl((p.x, p.y, z0 + H / 2), rb, rb * 0.68, H, seg=seg, rot=(0, 0, random.uniform(0, 6)), caps=False)
    iron.cyl((p.x, p.y, z0 + 0.35), 0.135, 0.13, 0.7, seg=seg, bottom=False)
    if not LITE:
        iron.cyl((p.x, p.y, z0 + H + 0.05), 0.09, 0.09, 0.1, seg=seg, caps=False)
    iron.cyl((p.x, p.y, z0 + H + 0.2), 0.12, 0.0, 0.22, seg=seg, bottom=False)
    if not LITE:
        iron.cyl((p.x, p.y, z0 + H - 0.3), 0.1, 0.1, 0.06, seg=seg, caps=False)       # hanging ring for the wires
        snowp.cyl((p.x, p.y, z0 + H + 0.22), 0.13, 0.02, 0.2, seg=seg, caps=False)


def catenary(a, b, sag, n):
    pts = []
    for k in range(n + 1):
        t = k / n
        p = a.lerp(b, t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    return pts


spacing = 0.55 if not LITE else 1.35
for si, (i, j) in enumerate(P.SPANS):
    a = poles[i].copy(); b = poles[j].copy()
    a.z = ground_height(a.x, a.y) + P.pole_h(i) - 0.3; b.z = ground_height(b.x, b.y) + P.pole_h(j) - 0.3
    L = (b - a).length
    sag = min(0.07 * L, 1.1) * random.uniform(0.85, 1.1)
    n = max(4, int(L / (0.7 if not LITE else 1.5)))
    pts = catenary(a, b, sag, n)
    wire.tube(pts, 0.008 if not LITE else 0.012, tseg=3)
    bl = C.Geo(f"bulbs_string_{si:02d}", M["bulb"], (1, 1))
    nb = max(2, int(L / spacing))
    for k in range(1, nb):
        t = k / nb
        p = a.lerp(b, t); p.z -= sag * 4 * t * (1 - t)
        bl.bulb((p.x, p.y, p.z - 0.075), 0.027 if not LITE else 0.034, sides=4 if not LITE else 3)
    bulb_objs.append(bl.finish(col))
    if si in P.STRING_LIGHT_SPANS and (not LITE or P.STRING_LIGHT_SPANS.index(si) < 3):
        mid = catenary(a, b, sag, 2)[1]
        light_objs.append(C.empty(f"light_string_{si:02d}", mid - Vector((0, 0, 0.25)), col))
wood_ob = wood.finish(col)
wire_ob = wire.finish(col)

# ------------------------------------------------------------------ benches, bins, bollards
bench_wood = C.Geo("benches_wood", M["wood"], (1.0, 0.25))


def bench(x, y, rot):
    z0 = ground_height(x, y)
    F = Matrix.Translation((x, y, z0)) @ Matrix.Rotation(rot, 4, "Z")
    bench_wood.frame = F; iron.frame = F; snowp.frame = F
    L = 1.9
    for sx in (-0.78, 0.78):
        iron.box((sx, -0.18, 0.22), (0.05, 0.05, 0.44))
        iron.box((sx, 0.2, 0.38), (0.05, 0.05, 0.76), rot=(-0.18, 0, 0))
        iron.box((sx, 0.0, 0.43), (0.05, 0.5, 0.04))
        if not LITE:
            iron.box((sx, -0.02, 0.64), (0.045, 0.46, 0.04))      # armrest
            iron.box((sx, -0.24, 0.53), (0.045, 0.04, 0.2))
    for k in range(4 if not LITE else 2):
        yy = -0.2 + k * 0.125 * (4 / (4 if not LITE else 2))
        bench_wood.box((0, yy, 0.46), (L, 0.105, 0.035))
    for k in range(3 if not LITE else 1):
        zz = 0.6 + k * 0.13
        bench_wood.box((0, 0.24 + 0.022 * k, zz), (L, 0.035, 0.1), rot=(-0.18, 0, 0))
    snowp.box((0, -0.02, 0.49), (L - 0.1, 0.44, 0.03))
    bench_wood.frame = Matrix.Identity(4); iron.frame = Matrix.Identity(4); snowp.frame = Matrix.Identity(4)


def binn(x, y):
    z0 = ground_height(x, y)
    seg = 8 if LITE else 14
    iron.cyl((x, y, z0 + 0.45), 0.23, 0.25, 0.9, seg=seg, bottom=False)
    iron.cyl((x, y, z0 + 0.93), 0.27, 0.27, 0.06, seg=seg)
    if not LITE:
        iron.cyl((x, y, z0 + 0.05), 0.24, 0.24, 0.1, seg=seg, caps=False)
        iron.cyl((x, y, z0 + 1.0), 0.22, 0.05, 0.1, seg=seg)
    snowp.cyl((x, y, z0 + 0.975), 0.26, 0.2, 0.035, seg=seg)


def bollard(x, y):
    z0 = ground_height(x, y)
    seg = 6 if LITE else 8
    iron.cyl((x, y, z0 + 0.42), 0.09, 0.075, 0.84, seg=seg, caps=False)
    if not LITE:
        iron.cyl((x, y, z0 + 0.7), 0.095, 0.095, 0.05, seg=seg, caps=False)
        iron.cyl((x, y, z0 + 0.06), 0.11, 0.11, 0.12, seg=seg, bottom=False)
    iron.uvsphere((x, y, z0 + 0.84), 0.078, seg=seg, rings=3, scale=(1, 1, 0.7))
    snowp.uvsphere((x, y, z0 + 0.88), 0.07, seg=seg, rings=3, scale=(1, 1, 0.45))


bench_spots = []
for k in range(7):
    t = math.radians(30 * (2 * k + 1) + 15 + random.uniform(-3, 3))
    if P.exit_at(t, P.plaza_r(t), pad=2.0) >= 0:
        continue
    r = P.plaza_r(t) - 2.4
    x, y = r * math.cos(t), r * math.sin(t)
    if free_spot(x, y, 1.2) and not P.in_ride(x, y, pad=1.2):
        bench_spots.append((x, y, t + math.pi / 2))
# two benches by the tree, backs to it, 6.6 m out so they sit clear of the lowest boughs (5.4 m)
for deg in (-140, -52):
    a = math.radians(deg)
    bench_spots.append((TREE_B[0] + P.TREE_BENCH_R * math.cos(a), TREE_B[1] + P.TREE_BENCH_R * math.sin(a), a + math.pi / 2))
for i, (x, y, rot) in enumerate(bench_spots):
    bench(x, y, rot)
    if i % 2 == 0:
        ox, oy = math.cos(rot) * 1.35, math.sin(rot) * 1.35
        binn(x + ox, y + oy)

for deg, w in P.EXITS:
    t = math.radians(deg)
    rr = P.plaza_r(t) + P.CURB_S + 0.6
    tang = Vector((-math.sin(t), math.cos(t), 0))
    base = Vector((rr * math.cos(t), rr * math.sin(t), 0))
    n = 4 if not LITE else 3
    for k in range(n):
        off = (k - (n - 1) / 2) * (w * 0.8 / (n - 1))
        p = base + tang * off
        bollard(p.x, p.y)

bench_ob = bench_wood.finish(col)
iron_ob = iron.finish(col)

# ------------------------------------------------------------------ snow cover over the ground (snow_ground)
def build_snow():
    bm = bmesh.new()
    nth = NTH // 2 if not LITE else 64
    uvl = bm.loops.layers.uv.new("UVMap")
    cols = []
    centre = bm.verts.new((0, 0, 0.04))
    for i in range(nth):
        t = 2 * math.pi * i / nth
        Rp = P.plaza_r(t)
        ex = P.exit_at(t, P.house_r(t), pad=0.5) >= 0
        rs = [Rp * f for f in ((0.25, 0.5, 0.75, 0.92) if not LITE else (0.4, 0.8))] + [Rp, Rp + 0.25, Rp + GW + 3.5, Rp + P.CURB_S - 0.2]
        if ex:
            rs += [Rp + P.CURB_S + 4, 66]
        else:
            rs += [Rp + P.CURB_S + 0.02, Rp + P.CURB_S + 0.3, 66]
        vs = []
        for r in rs:
            x, y = r * math.cos(t), r * math.sin(t)
            z = ground_height(x, y) + 0.035
            if not ex and Rp + P.CURB_S - 0.01 < r < Rp + P.CURB_S + 0.31:
                z = P.SIDEWALK_Z + 0.02 + 0.035
            vs.append(bm.verts.new((x, y, z)))
        cols.append(vs)
    for i in range(nth):
        a, b = cols[i], cols[(i + 1) % nth]
        bm.faces.new((centre, a[0], b[0]))
        for k in range(min(len(a), len(b)) - 1):
            bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
        if len(a) != len(b):
            lo, hi = (a, b) if len(a) < len(b) else (b, a)
            for k in range(len(lo) - 1, len(hi) - 1):
                try:
                    bm.faces.new((lo[-1], hi[k], hi[k + 1]))
                except ValueError:
                    pass
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x / 4, l.vert.co.y / 4)
    me = bpy.data.meshes.new("snow_ground"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("snow_ground", me); col.objects.link(ob)
    me.materials.append(M["snow"])
    for p in me.polygons: p.use_smooth = True
    return ob


snow_ob = build_snow()
snowp_ob = snowp.finish(col, smooth=False)

# ------------------------------------------------------------------ AO bake (full build) and export
exported = [o for o in col.objects]
tris = C.count_tris(exported)
C.log("SQUARE TRIANGLES", tris, "lite" if LITE else "full")
by = {}
for o in exported:
    k = o.name.split("_")[0] if o.name.startswith(("bulbs_", "light_")) else o.name
    by[k] = by.get(k, 0) + C.count_tris([o])
C.log("BREAKDOWN", sorted(by.items(), key=lambda kv: -kv[1]))
if os.environ.get("STATS_ONLY"):
    sys.exit(0)

# The ground's AO lightmap covers x, y in [-80, 80]; the ground ends at r = 78, so the image's
# corner beyond it (u > RAMP_U0, v < 0.32, i.e. x > 77, y < -29) is free.  A ramp stored there
# carries the per-vertex occlusion of the lamps, poles, benches, bins, bollards and kerbs.
RAMP_U0, RAMP_V0, RAMP_V1 = 0.982, 0.02, 0.30
parts = [o for o in (iron_ob, wood_ob, bench_ob, curb_ob, snowp_ob) if o]


def finish_square_ao(img):
    res = img.size[0]
    px = np.array(img.pixels[:], np.float32).reshape(res, res, 4)
    ao = np.clip(0.25 + 0.75 * px[..., 0], 0, 1)
    c0 = int(RAMP_U0 * res)
    rows = (np.arange(res) + 0.5) / res
    ramp = np.clip((rows - RAMP_V0) / (RAMP_V1 - RAMP_V0), 0, 1)
    band = rows < RAMP_V1 + 0.02
    ao[band, c0:] = ramp[band, None]
    px[..., 0] = px[..., 1] = px[..., 2] = ao; px[..., 3] = 1
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = AO_PATH; img.file_format = "PNG"; img.save()
    return img


C.add_lightmap_uv_planar(ground, AO_X0, AO_X0, AO_SIZE)
C.add_lightmap_uv_planar(bands_ob, AO_X0, AO_X0, AO_SIZE)
C.add_lightmap_uv_planar(snow_ob, AO_X0, AO_X0, AO_SIZE)
scene.world = bpy.data.worlds.new("w")
hidden = [o for o in col.objects if o.name.startswith(("snow_ground", "bulbs_", "puddles", "string_wire"))]
for o in hidden: o.hide_render = True
if not LITE and not REUSE_AO:
    # occluders: the town, if it has been built, darkens the sidewalk at the house fronts
    town_raw = os.path.join(C.REPO, "blender", "town", "out", "town_raw.glb")
    if os.path.exists(town_raw):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=town_raw)
        for o in set(bpy.data.objects) - before:
            for c in list(o.users_collection): c.objects.unlink(o)
            occ.objects.link(o)
    baked = finish_square_ao(C.bake_ao([ground], "square_ao", 1024, AO_PATH, samples=64, distance=2.5, post=False))
    # swap the placeholder for the baked image in the ground materials
    for m in list(ground.data.materials) + list(bands_ob.data.materials):
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and n.image.name == "square_ao":
                n.image = baked
    ao_img = baked
# the snow sheet shares the ground's lightmap; the parts point into the ramp
vao = C.bake_vertex_ao(parts, samples=48, distance=1.0, lift=0.3)
for o in parts:
    C.ramp_uv(o, vao[o.name], RAMP_U0 + 0.004, 0.996, RAMP_V0, RAMP_V1)
for o in parts + [snow_ob]:
    for m in o.data.materials:
        C.attach_ao(m, ao_img)
for o in list(occ.objects):
    bpy.data.objects.remove(o)
for o in hidden: o.hide_render = False

name = "square.lite" if LITE else "square"
raw = C.export_glb(exported, os.path.join(OUT, f"{name}_raw.glb"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"))
final = C.optimize(raw, os.path.join(C.MODELS, f"{name}.glb"), tex_size=512 if LITE else 1024)
st = C.glb_stats(final)
C.log("FINAL", name, "tris", st["tris"], "bytes", st["size"])
C.log("NODES", " ".join(n for n in st["nodes"] if n.startswith(("light_", "bulbs_", "snow_")))[:600])
C.log("MATERIALS", st["materials"])
