"""The market's Christmas tree: a 15 m Nordmann fir built from alpha-tested needle fronds on
branch whorls, glass baubles, straw stars, a bead garland, warm fairy lights (bulbs_tree),
a glowing star (bulbs_star), a low picket fence and a snow_ layer on the upper boughs.
Exports site/public/models/tree.glb (tree.lite.glb with LITE=1).

Run: /home/claude/tools/bpy-venv/bin/python blender/square/tree.py   (LITE=1 for the lite model)
"""
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix, Euler, Quaternion
import architect_common as C
import architect_tex as TX

LITE = bool(os.environ.get("LITE"))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
random.seed(9)
scene = C.reset()
col = C.collection("Tree")

# ------------------------------------------------------------------ textures
TD = C.tex_dir("square")
FROND = os.path.join(TD, "fir_frond.png"); SNOWF = os.path.join(TD, "fir_frond_snow.png")
if os.environ.get("FORCE_TEX") or not os.path.exists(FROND):
    fr = TX.fir_frond(1024, 512, seed=101)
    # bleed colour into transparent pixels so mipmaps don't fringe dark
    from scipy import ndimage
    a = fr[..., 3] > 0.5
    idx = ndimage.distance_transform_edt(~a, return_distances=False, return_indices=True)
    rgb = fr[..., :3][idx[0], idx[1]]
    fr[..., :3] = rgb
    TX.save_png(FROND, np.concatenate([fr[..., :3] ** (1 / 2.2), fr[..., 3:]], -1))
    sn = TX.snow_frond(TX.fir_frond(512, 256, seed=101))
    TX.save_png(SNOWF, np.concatenate([sn[..., :3] ** (1 / 2.2), sn[..., 3:]], -1))
T_BARK = C.make_texture_set("square", "bark", lambda: TX.bark(256), normal_strength=4.0)
T_WOOD = C.make_texture_set("square", "timber", lambda: TX.timber(512), normal_strength=3.0)

M = {}
M["needles"] = C.pbr("fir_needles", base_tex=FROND, alpha_tex=True, rough=0.65)
M["snowcard"] = C.pbr("snow_needles", base_tex=SNOWF, alpha_tex=True, rough=0.8)
M["bark"] = C.pbr("bark", tex=T_BARK)
M["red"] = C.solid("bauble_red", (0.5, 0.02, 0.03), rough=0.12, coat=1.0)
M["gold"] = C.solid("bauble_gold", (0.95, 0.66, 0.25), rough=0.2, metal=1.0)
M["champ"] = C.solid("bauble_champagne", (0.85, 0.8, 0.7), rough=0.15, metal=1.0)
M["matte"] = C.solid("bauble_matte_red", (0.35, 0.03, 0.04), rough=0.55)
M["straw"] = C.solid("straw", (0.78, 0.6, 0.3), rough=0.6)
M["bead"] = C.solid("bead_gold", (0.9, 0.7, 0.35), rough=0.25, metal=1.0)
M["bulb"] = C.solid("bulb_warm", (1.0, 0.8, 0.55), rough=0.3, emit=(1.0, 0.62, 0.28), strength=6.0)
M["wood"] = C.pbr("fence_wood", tex=T_WOOD, factor=(1.1, 1.0, 0.9))
M["snow"] = C.solid("snow", (0.82, 0.85, 0.92), rough=0.75)
for k, m in M.items():
    m.use_backface_culling = k not in ("needles", "snowcard", "straw")

HT = 15.0          # to the star
Z0 = 1.5           # lowest whorl
ZT = 14.0          # top of the foliage


def R(z):
    """Crown radius envelope."""
    t = np.clip((ZT - z) / (ZT - Z0), 0, 1)
    return 0.25 + 4.1 * t ** 0.95


needles = C.Geo("tree_needles", M["needles"], (1, 1))
snowc = C.Geo("snow_tree", M["snowcard"], (1, 1))


def card(g, base, d, up, L, W, curl=0.15, segs=2, snow=False):
    """Curved card from base along direction d; up = card normal-ish.  u runs along the frond."""
    d = d.normalized()
    side = d.cross(up).normalized()
    n = side.cross(d).normalized()
    verts, faces, uvs = [], [], []
    for k in range(segs + 1):
        t = k / segs
        p = base + d * (L * t) + n * (curl * L * t * t) - Vector((0, 0, 0.12 * L * t * t))
        verts += [tuple(p - side * W / 2), tuple(p + side * W / 2)]
    for k in range(segs):
        a = 2 * k
        faces.append((a, a + 1, a + 3, a + 2))
        uvs.append([(k / segs, 0.0), (k / segs, 1.0), ((k + 1) / segs, 1.0), ((k + 1) / segs, 0.0)])
    g.raw(verts, faces, uvs)


# ------------------------------------------------------------------ branches
fronds = 0
z = Z0
whorl = 0
branch_tips = []
while z < ZT - 0.5:
    rz = R(z)
    nb = int(np.clip(4 + rz * 1.3, 4, 10)) if not LITE else int(np.clip(3 + rz * 0.8, 3, 6))
    a0 = random.uniform(0, 2 * math.pi)
    for b in range(nb):
        ang = a0 + 2 * math.pi * b / nb + random.uniform(-0.25, 0.25)
        L = rz * random.uniform(0.85, 1.05)
        droop = math.radians(random.uniform(-14, -4) if z < 8 else random.uniform(-6, 6))
        dh = Vector((math.cos(ang), math.sin(ang), 0))
        d = (dh * math.cos(droop) + Vector((0, 0, math.sin(droop)))).normalized()
        base = Vector((0, 0, z)) + dh * 0.15
        step = 0.42 if not LITE else 0.8
        s = 0.25
        while s < L - 0.1:
            p = base + d * s + Vector((0, 0, 0.08 * (s / L) ** 2 * L))
            fl = max(0.35, min(1.05, (L - s) * 0.55 + 0.35))
            for sgn in (-1, 1):
                sd = (d + dh.cross(Vector((0, 0, 1))) * sgn * random.uniform(0.7, 1.1)).normalized()
                sd.z += random.uniform(-0.05, 0.12)
                up = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 1))
                card(needles, p, sd, up, fl, fl * 0.55, curl=0.12)
                fronds += 1
                if not LITE and random.random() < 0.5:
                    card(needles, p + Vector((0, 0, 0.04)), sd, (sd.cross(Vector((0, 0, 1)))).normalized() * 0.8 + Vector((0, 0, 0.6)), fl * 0.8, fl * 0.44, curl=0.1)
                    fronds += 1
                if z > 3.0 and random.random() < (0.5 if z > 6 else 0.3) and s > L * 0.3:
                    card(snowc, p + Vector((0, 0, 0.035)), sd, up, fl * 0.95, fl * 0.55, curl=0.12)
            s += step * random.uniform(0.85, 1.15)
        # the branch tip
        tipL = min(1.1, 0.5 + L * 0.2)
        tp = base + d * (L - 0.1)
        card(needles, tp, d + Vector((0, 0, 0.1)), Vector((0, 0, 1)), tipL, tipL * 0.55, curl=0.18)
        if not LITE:
            card(needles, tp, d + Vector((0, 0, 0.1)), d.cross(Vector((0, 0, 1))).normalized() + Vector((0, 0, 0.3)), tipL * 0.9, tipL * 0.45)
        if z > 2.5 and random.random() < 0.6:
            card(snowc, tp + Vector((0, 0, 0.04)), d + Vector((0, 0, 0.1)), Vector((0, 0, 1)), tipL * 0.9, tipL * 0.5, curl=0.18)
        branch_tips.append((tp + d * tipL * 0.6, ang, z))
        fronds += 2
    z += random.uniform(0.38, 0.5) if not LITE else random.uniform(0.6, 0.75)
    whorl += 1
# leader at the top
for k in range(5 if not LITE else 3):
    a = 2 * math.pi * k / 5
    card(needles, Vector((0, 0, ZT - 0.8)), Vector((0.15 * math.cos(a), 0.15 * math.sin(a), 1)), Vector((math.cos(a), math.sin(a), 0)), 1.3, 0.5, curl=0.05)
C.log("fronds", fronds)

# ------------------------------------------------------------------ trunk, stand, fence
bark = C.Geo("tree_trunk", M["bark"], (1.0, 1.5))
bark.cyl((0, 0, ZT / 2 - 0.2), 0.32, 0.06, ZT + 0.4, seg=10 if not LITE else 6, bottom=False)
wood = C.Geo("tree_fence", M["wood"], (1.0, 0.25))
snowp = C.Geo("snow_tree_fence", M["snow"], (1, 1))
RF = 2.8
nside = 8
for k in range(nside):
    a0 = 2 * math.pi * k / nside + math.pi / 8; a1 = 2 * math.pi * (k + 1) / nside + math.pi / 8
    p0 = Vector((RF * math.cos(a0), RF * math.sin(a0), 0)); p1 = Vector((RF * math.cos(a1), RF * math.sin(a1), 0))
    wood.box((p0.x, p0.y, 0.45), (0.12, 0.12, 0.9), rot=(0, 0, a0))
    for zz in (0.25, 0.7):
        wood.beam(p0 + Vector((0, 0, zz)), p1 + Vector((0, 0, zz)), 0.05, 0.1)
    snowp.beam(p0 + Vector((0, 0, 0.765)), p1 + Vector((0, 0, 0.765)), 0.06, 0.03)
    npk = 6 if not LITE else 0
    for j in range(npk):
        t = (j + 0.5) / npk
        p = p0.lerp(p1, t)
        wood.box((p.x, p.y, 0.4), (0.07, 0.025, 0.8), rot=(0, 0, math.atan2(p1.y - p0.y, p1.x - p0.x)))
# greenery on the ground inside the fence
for k in range(24 if not LITE else 8):
    a = random.uniform(0, 2 * math.pi); r = random.uniform(0.5, 2.3)
    p = Vector((r * math.cos(a), r * math.sin(a), 0.1))
    d = Vector((math.cos(a + random.uniform(-0.5, 0.5)), math.sin(a + random.uniform(-0.5, 0.5)), 0.05))
    card(needles, p, d, Vector((0, 0, 1)), 0.9, 0.5, curl=0.2)

# ------------------------------------------------------------------ decorations
bal = {k: C.Geo(f"tree_baubles_{k}", M[k], (1, 1)) for k in ("red", "gold", "champ", "matte")}
caps = C.Geo("tree_bauble_caps", M["gold"], (1, 1))
nba = 170 if not LITE else 70
placed = []
tries = 0
while len(placed) < nba and tries < 5000:
    tries += 1
    zz = random.uniform(Z0 + 0.3, ZT - 1.0)
    # more baubles lower down where the tree is wider
    if random.random() > R(zz) / 4.3 + 0.15:
        continue
    a = random.uniform(0, 2 * math.pi)
    rr = R(zz) * random.uniform(0.72, 0.95)
    p = Vector((rr * math.cos(a), rr * math.sin(a), zz - 0.15))
    size = random.choice([0.07, 0.09, 0.09, 0.11, 0.14])
    if any((p - q).length < size + qs + 0.05 for q, qs in placed):
        continue
    placed.append((p, size))
    kind = random.choice(["red", "red", "gold", "champ", "matte"])
    seg = 8 if not LITE else 6
    bal[kind].uvsphere(tuple(p), size, seg=seg, rings=5 if not LITE else 4)
    if not LITE:
        caps.cyl((p.x, p.y, p.z + size + 0.012), size * 0.25, size * 0.25, 0.03, seg=4, bottom=False)
C.log("baubles", len(placed))

straw = C.Geo("tree_straw_stars", M["straw"], (1, 1))
if not LITE:
    for k in range(70):
        zz = random.uniform(Z0 + 0.5, ZT - 1.5)
        a = random.uniform(0, 2 * math.pi)
        rr = R(zz) * random.uniform(0.85, 1.0)
        c = Vector((rr * math.cos(a), rr * math.sin(a), zz - 0.1))
        rad = random.uniform(0.07, 0.11)
        # 8-point star in the plane facing outward
        out = Vector((math.cos(a), math.sin(a), 0)); side = Vector((-math.sin(a), math.cos(a), 0)); upv = Vector((0, 0, 1))
        pts = []
        for j in range(16):
            aa = 2 * math.pi * j / 16
            r_ = rad if j % 2 == 0 else rad * 0.35
            pts.append(tuple(c + side * (r_ * math.cos(aa)) + upv * (r_ * math.sin(aa)) + out * 0.01))
        straw.raw([tuple(c)] + pts, [(0, 1 + j, 1 + (j + 1) % 16) for j in range(16)])

bead = C.Geo("tree_bead_garland", M["bead"], (1, 1))
if not LITE:
    turns = 3.2
    pts = []
    for k in range(240):
        t = k / 239
        zz = Z0 + 0.6 + t * (ZT - Z0 - 2.5)
        a = t * turns * 2 * math.pi + 0.4 + 0.25 * math.sin(t * 60)
        rr = R(zz) * 0.93
        sag = 0.12 * abs(math.sin(t * turns * 2 * math.pi * 3))
        pts.append(Vector((rr * math.cos(a), rr * math.sin(a), zz - sag)))
    bead.tube(pts, 0.02, tseg=3)

bulbs = C.Geo("bulbs_tree", M["bulb"], (1, 1))
nbl = 460 if not LITE else 200
for k in range(nbl):
    t = (k + random.random()) / nbl
    zz = Z0 + 0.2 + (ZT - Z0 - 0.4) * (1 - math.sqrt(1 - t))   # more bulbs low down (wider)
    a = random.uniform(0, 2 * math.pi)
    rr = R(zz) * random.uniform(0.82, 1.0)
    bulbs.bulb((rr * math.cos(a), rr * math.sin(a), zz - 0.05), 0.028 if not LITE else 0.04, sides=4)

# the star
star = C.Geo("bulbs_star", M["bulb"], (1, 1))
cS = Vector((0, 0, HT - 0.35))
outer = []
for j in range(10):
    aa = math.pi / 2 + 2 * math.pi * j / 10
    r_ = 0.62 if j % 2 == 0 else 0.26
    outer.append(cS + Vector((r_ * math.cos(aa), 0, r_ * math.sin(aa))))
front = cS + Vector((0, -0.13, 0)); back = cS + Vector((0, 0.13, 0))
vs = [tuple(front), tuple(back)] + [tuple(p) for p in outer]
fs = []
for j in range(10):
    a, b = 2 + j, 2 + (j + 1) % 10
    fs.append((0, b, a)); fs.append((1, a, b))
star.raw(vs, fs)
starstem = C.Geo("tree_star_stem", M["gold"], (1, 1))
starstem.cyl((0, 0, HT - 1.0), 0.04, 0.04, 0.6, seg=6)

# snow caps on the lowest, outermost boughs are cards; plus snow on the ground ring inside the fence
snowp.cyl((0, 0, 0.02), RF - 0.1, RF - 0.1, 0.04, seg=16 if not LITE else 8, bottom=False)

objs = []
for g in [needles, snowc, bark, wood, snowp, caps, straw, bead, bulbs, star, starstem] + list(bal.values()):
    ob = g.finish(col, smooth=g in (bark,) or g in bal.values())
    if ob: objs.append(ob)
for p, (name, loc) in enumerate([("light_tree_0", (0, -4.2, 4.5)), ("light_tree_1", (0.5, 3.5, 8.5))]):
    objs.append(C.empty(name, loc, col))
tris = C.count_tris(objs)
by = sorted(((o.name, C.count_tris([o])) for o in objs), key=lambda kv: -kv[1])
C.log("TREE TRIANGLES", tris, by[:8])
if os.environ.get("STATS_ONLY"):
    sys.exit(0)
name = "tree.lite" if LITE else "tree"
raw = C.export_glb(objs, os.path.join(OUT, f"{name}_raw.glb"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"))
final = C.optimize(raw, os.path.join(C.MODELS, f"{name}.glb"), tex_size=512 if LITE else 1024)
st = C.glb_stats(final)
C.log("FINAL", name, "tris", st["tris"], "bytes", st["size"])
C.log("NODES", [n for n in st["nodes"] if n.startswith(("light_", "bulbs_", "snow_"))])
