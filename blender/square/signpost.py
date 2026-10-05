"""The market signpost (Wegweiser): a tall weathered oak post on a granite plinth with seven painted
finger boards, one per place of the guided stroll (docs/adr/0003-guided-stroll-navigation.md).

Each board is its own clickable node `act_sign_<placeid>` (ids as in site/src/layout.json), with its
origin on the post axis at the board's height so the engine can wiggle it on hover.  The boards are
cream paint over oak, worn at the edges, with the German name in oxblood capitals and a small English
label in italics under it; both faces carry the lettering (painted into one atlas, 14 cells: each board
pointing left and pointing right).  The iron clamps that hold a board are children of its node.  On
top: a little shingled cap with a ball finial, an iron bracket with a lantern (bulbs_sign, bulb_warm,
and the empty light_sign_0 where the engine may place a warm light so the boards read at night), a fir
wreath with a red bow, and snow_sign on the cap, the board tops and the plinth.

Boards point left or right (toward the side of the market the place lies on), turned up to 25 degrees
toward it, so that every board reads from the home camera.

Front (the side that faces the home camera) is Blender -Y (three.js +Z).  Origin on the ground at the
post's foot.  Exports site/public/models/signpost.glb (signpost.lite.glb with LITE=1).

Run:  /home/claude/tools/bpy-venv/bin/python blender/square/signpost.py   (LITE=1 for the lite file)
      PREVIEW=1 also renders review/round-5/architect/signpost.jpg (close view at night)
"""
import os, sys, math, random, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import numpy as np
import bpy
from mathutils import Vector, Matrix, Euler
import architect_common as C
import architect_tex as TX

LITE = bool(os.environ.get("LITE"))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
FONTS = os.path.join(C.REPO, "blender", "lib", "fonts")
random.seed(5)
scene = C.reset()
col = C.collection("Signpost")

# the boards, top to bottom: (place id, German, English, points right?, turn toward it in degrees)
BOARDS = [
    ("riesenrad", "Riesenrad", "Big questions", False, 22),
    ("karussell", "Karussell", "Contact", True, 20),
    ("gluehwein", "Glühwein", "About", False, 12),
    ("bandstand", "Musikpavillon", "Music", True, 8),
    ("bratwurst", "Bratwurst", "Writing", False, 6),
    ("bierstand", "Bierstand", "Projects", True, 14),
    ("buecherstand", "Bücherstand", "Reading", True, 4),
]
LB, HB, TB = 1.6, 0.32, 0.04          # board length, height, thickness (m)
TIP = 0.22                            # length of the pointed end
NOTCH = 0.08                          # fishtail notch at the tail
POST_R = 0.09                         # half-width of the post
Z_TOP = 4.35                          # top edge of the highest board
GAP = 0.07
POST_H = 4.75

# ------------------------------------------------------------------ the board atlas
AN = 2048
CW, CH = 1024, 204                    # cell: 1.6 m x 0.32 m at 640 px/m
PXM = CW / LB
WOOD_Y0 = 7 * CH                      # rows 7..9: bare weathered oak for the board edges
TD = C.tex_dir("square")
ATLAS = {k: os.path.join(TD, f"signpost_{k}.png") for k in ("color", "rough", "normal")}


def cell_of(i, tip_left):
    c = 2 * i + (1 if tip_left else 0)
    return (c % 2) * CW, (c // 2) * CH            # pixel x0, y0 (image rows from the top)


def outline_m(tip_left):
    """Board outline in metres, x along the board from the tail, y up from the bottom edge."""
    pts = [(0, HB), (LB - TIP, HB), (LB, HB / 2), (LB - TIP, 0), (0, 0), (NOTCH, HB / 2)]
    if tip_left:
        pts = [(LB - x, y) for x, y in pts]
    return pts


def paint_atlas():
    from PIL import Image, ImageDraw, ImageFont
    from scipy import ndimage
    rng = np.random.default_rng(17)
    col = np.zeros((AN, AN, 3)); rough = np.full((AN, AN), 0.6); height = np.zeros((AN, AN))
    grain = TX.stretched_noise(AN, 3, 70, 4, 23)          # fine grain along u
    blot = TX.pnoise(AN, 12, 4, 0.55, 29)
    chips = TX.pnoise(AN, 40, 3, 0.6, 31)
    # bare oak: silver-grey weathered timber
    oak = np.array([0.20, 0.16, 0.12])
    wood_rgb = oak[None, None, :] * (0.65 + 0.7 * grain[..., None]) * (0.85 + 0.3 * blot[..., None])
    col[:] = wood_rgb
    height[:] = 0.5 * grain
    rough[:] = 0.8
    f_de = os.path.join(FONTS, "AlegreyaSC-ExtraBold.ttf")
    f_en = os.path.join(FONTS, "IMFeENit28P.ttf")
    cream = np.array([0.80, 0.72, 0.53])
    red = np.array([0.30, 0.035, 0.03])
    ink = np.array([0.035, 0.05, 0.04])
    S = 3                                              # supersampling for the masks
    for i, (pid, de, en, right, _) in enumerate(BOARDS):
        for tip_left in (False, True):
            x0, y0 = cell_of(i, tip_left)
            sl = (slice(y0, y0 + CH), slice(x0, x0 + CW))
            to_px = lambda p: (p[0] * PXM * S, (HB - p[1]) * PXM * S)
            shape = Image.new("L", (CW * S, CH * S), 0)
            ImageDraw.Draw(shape).polygon([to_px(p) for p in outline_m(tip_left)], fill=255)
            shape_m = np.asarray(shape.resize((CW, CH), Image.LANCZOS), float) / 255
            inside = ndimage.distance_transform_edt(shape_m > 0.5)          # px from the edge
            # the border line, 16 px in, following the outline
            ring = np.exp(-((inside - 15.0) / 2.3) ** 2) * (shape_m > 0.5)
            # lettering
            txt = Image.new("L", (CW * S, CH * S), 0)
            dr = ImageDraw.Draw(txt)
            tx0 = (0.13 if not tip_left else TIP + 0.05) * PXM * S
            tx1 = (LB - TIP - 0.05 if not tip_left else LB - 0.13) * PXM * S
            size = int(0.2 * PXM * S * 1.42)
            while True:
                fd = ImageFont.truetype(f_de, size)
                bb = dr.textbbox((0, 0), de, font=fd)
                if (bb[2] - bb[0] <= (tx1 - tx0) and bb[3] - bb[1] <= 0.14 * PXM * S) or size < 40:
                    break
                size -= 4
            cx = (tx0 + tx1) / 2
            dr.text((cx - (bb[0] + bb[2]) / 2, 0.032 * PXM * S - bb[1]), de, font=fd, fill=255)
            txt_en = Image.new("L", (CW * S, CH * S), 0)
            de2 = ImageDraw.Draw(txt_en)
            fe = ImageFont.truetype(f_en, int(0.062 * PXM * S * 1.5))
            be = de2.textbbox((0, 0), en, font=fe)
            de2.text((cx - (be[0] + be[2]) / 2, (HB - 0.03) * PXM * S - be[3]), en, font=fe, fill=255)
            # a small arrow head after the English label, pointing the board's way
            ah = 0.03 * PXM * S
            ax = cx + (be[2] - be[0]) / 2 + 0.05 * PXM * S if not tip_left else cx - (be[2] - be[0]) / 2 - 0.05 * PXM * S
            ay = (HB - 0.03) * PXM * S - 0.032 * PXM * S
            sgn = 1 if not tip_left else -1
            de2.polygon([(ax + sgn * ah, ay), (ax - sgn * ah * 0.4, ay - ah * 0.8), (ax - sgn * ah * 0.4, ay + ah * 0.8)], fill=255)
            m_de = np.asarray(txt.resize((CW, CH), Image.LANCZOS), float) / 255
            m_en = np.asarray(txt_en.resize((CW, CH), Image.LANCZOS), float) / 255
            # paint wear: chipped near the edges and in a few blotches, never across the letters' middles
            wear = np.clip((chips[sl] - 0.62) * 6, 0, 1) * np.clip(1.3 - inside / 22, 0, 1)
            wear = np.maximum(wear, np.clip((chips[sl] - 0.78) * 10, 0, 1) * np.clip((blot[sl] - 0.6) * 4, 0, 1) * 0.8)
            wear *= shape_m
            paint = shape_m * (1 - wear)
            tone = 0.94 + 0.12 * ((i * 0.37 + (0.5 if tip_left else 0)) % 1.0)      # each board repainted at a different time
            p_rgb = cream * (0.88 + 0.16 * blot[sl][..., None] + 0.06 * grain[sl][..., None]) * tone
            # dirt settles under the top edge and toward the tail; the lower edge is splashed
            vv = np.linspace(0, 1, CH)[:, None]
            grime = 1 - 0.12 * np.exp(-vv / 0.12) - 0.18 * np.exp(-(1 - vv) / 0.18)
            p_rgb = p_rgb * grime[..., None]
            c = col[sl]
            c = c * (1 - paint[..., None]) + p_rgb * paint[..., None]
            c = c * (1 - ring[..., None] * paint[..., None]) + red * ring[..., None] * paint[..., None]
            lt = np.clip(m_de * (1 - 0.6 * wear), 0, 1)
            c = c * (1 - lt[..., None]) + red * (0.9 + 0.2 * grain[sl][..., None]) * lt[..., None]
            le = np.clip(m_en * (1 - 0.6 * wear), 0, 1)
            c = c * (1 - le[..., None]) + ink * le[..., None]
            col[sl] = c
            rough[sl] = rough[sl] * (1 - paint) + (0.62 - 0.12 * lt - 0.08 * le) * paint
            # carved letters: the lettering is cut into the board and painted
            h = 0.5 * grain[sl] * (1 - paint) + (0.9 + 0.1 * grain[sl]) * paint
            h -= 0.9 * ndimage.gaussian_filter(np.maximum(m_de, m_en * 0.6), 0.9)
            height[sl] = h
    return dict(color=np.clip(col, 0, 1), rough=np.clip(rough, 0.2, 0.95), height=height)


if os.environ.get("FORCE_TEX") or not all(os.path.exists(p) for p in ATLAS.values()):
    t = paint_atlas()
    TX.save_png(ATLAS["color"], t["color"] ** (1 / 2.2))
    TX.save_png(ATLAS["rough"], t["rough"])
    TX.save_png(ATLAS["normal"], TX.normal_from_height(t["height"], 6.0))
    C.log("signpost atlas painted")
T_BOARD = ATLAS if not LITE else C.lite_texture_set(ATLAS, 512, keep=("color", "rough", "normal"))
T_WOOD = C.make_texture_set("square", "timber", lambda: TX.timber(512), normal_strength=3.0)
T_GRAN = C.make_texture_set("square", "granite", lambda: TX.granite(512), normal_strength=2.0)
if LITE:
    T_WOOD = C.lite_texture_set(T_WOOD, 256, keep=("color",))
    T_GRAN = C.lite_texture_set(T_GRAN, 256, keep=("color", "rough"))

M = {}
# Round 5 pass 3: in the browser the engine's light budget leaves light_sign_0 (kind "other", lowest
# priority) unlit, and the boards read as dark planks from home.  The lantern's spill is carried as a
# faint emissive of the boards' own paint (the atlas as emissive map, as the lighting designer's
# bulbBounce does for the Ferris wheel), so the names read at night with or without the real light.
SPILL = 0.22
M["board"] = C.pbr("sign_boards", tex=T_BOARD, normal_strength=1.0, emit_tex=T_BOARD["color"], emit_strength=SPILL)
M["post"] = C.pbr("sign_oak", tex=T_WOOD, factor=(0.95, 0.92, 0.9), rough=0.75, normal_strength=1.0)
M["stone"] = C.pbr("sign_granite", tex=T_GRAN, factor=(0.85, 0.85, 0.85), rough=0.7)
M["iron"] = C.solid("sign_iron", (0.035, 0.033, 0.03), rough=0.55, metal=0.85)
M["fir"] = C.solid("sign_fir", (0.03, 0.09, 0.04), rough=0.8)
M["ribbon"] = C.solid("sign_ribbon", (0.42, 0.02, 0.03), rough=0.45)
M["bulb"] = C.solid("bulb_warm", (1.0, 0.8, 0.55), rough=0.3, emit=(1.0, 0.62, 0.28), strength=6.0)
M["glass"] = C.solid("sign_lantern_glass", (0.9, 0.8, 0.6), rough=0.15, emit=(1.0, 0.7, 0.4), strength=0.6)
M["snow"] = C.solid("snow", (0.82, 0.85, 0.92), rough=0.75)

objs = []


def cell_uv(i, tip_left, x, y):
    """Atlas uv for board point (x along from the tail, y up) in the given cell."""
    x0, y0 = cell_of(i, tip_left)
    u = (x0 + x * PXM) / AN
    v = 1 - (y0 + (HB - y) * PXM) / AN
    return (u, v)


def wood_uv(a, b):
    return ((a * 300) / AN % 1.0, 1 - (WOOD_Y0 + 40 + b * 300) / AN)


# ------------------------------------------------------------------ boards
z = Z_TOP
board_obs = []
snow = C.Geo("snow_sign", M["snow"], (1, 1))
for i, (pid, de, en, right, turn) in enumerate(BOARDS):
    zc = z - HB / 2
    g = C.Geo(f"act_sign_{pid}", M["board"], (1, 1))
    sgn = 1 if right else -1
    base = [(0, HB), (LB - TIP, HB), (LB, HB / 2), (LB - TIP, 0), (0, 0), (NOTCH, HB / 2)]   # tip at +x
    tris = [(1, 2, 3), (0, 1, 5), (5, 1, 3), (5, 3, 4)]
    X0 = POST_R + 0.015

    def P(x, y, side):
        return (sgn * (X0 + x), side * TB / 2, y - HB / 2)

    verts, faces, uvs = [], [], []
    # front face (-Y, toward the camera) and back face (+Y)
    for side in (-1, 1):
        k0 = len(verts)
        verts += [P(x, y, side) for x, y in base]
        # the viewer's right on the front face is +x, on the back face -x
        tip_left_here = (sgn < 0) if side < 0 else (sgn > 0)
        for a, b, c in tris:
            # winding: front faces -Y
            tri = (a, b, c) if (side < 0) == (sgn > 0) else (a, c, b)
            tri = tri if side < 0 else tri[::-1]
            faces.append(tuple(k0 + t for t in tri))
            uu = []
            for t in tri:
                x, y = base[t]
                xx = (LB - x) if tip_left_here else x
                uu.append(cell_uv(i, tip_left_here, xx, y))
            uvs.append(uu)
    # edges: bare oak
    n = len(base)
    for k in range(n):
        a, b = k, (k + 1) % n
        f = (a, b, n + b, n + a)
        L = math.dist(base[a], base[b])
        faces.append(f if sgn > 0 else f[::-1])
        uvs.append([wood_uv(0, 0), wood_uv(L, 0), wood_uv(L, 0.13), wood_uv(0, 0.13)] if sgn > 0 else
                   [wood_uv(0, 0.13), wood_uv(L, 0.13), wood_uv(L, 0), wood_uv(0, 0)])
    g.raw(verts, faces, uvs)
    ob = g.finish(col, smooth=False)
    # Blender's face winding decides the normal; make sure the front faces point away from the post's
    # centre plane correctly by recalculating outward normals
    me = ob.data
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    yaw = math.radians(turn) * sgn                       # turn the tip toward the back (+Y)
    ob.rotation_euler = (0, 0, yaw)
    ob.location = (0, 0, zc)
    board_obs.append(ob)
    objs.append(ob)
    # iron clamps: two straps round the post, bolted through the board's tail
    ir = C.Geo(f"sign_clamp_{pid}", M["iron"], (1, 1))
    for dz in (-HB * 0.28, HB * 0.28):
        ir.box((sgn * (X0 + 0.05), 0, dz), (0.12, TB + 0.012, 0.035))
        if not LITE and dz > 0:                     # one iron band round the post per board
            ir.cyl((0, 0, dz), POST_R * 1.12, POST_R * 1.12, 0.03, seg=8, rot=(0, 0, math.pi / 8), caps=False)
        if not LITE:
            for sy in (-1, 1):
                ir.cyl((sgn * (X0 + 0.08), sy * (TB / 2 + 0.008), dz), 0.012, 0.012, 0.01, seg=6, rot=(math.pi / 2, 0, 0))
    co = ir.finish(col)
    co.parent = ob
    objs.append(co)
    # snow along the top edge of the board (in its own frame, then placed like the board)
    F = Matrix.Translation((0, 0, zc)) @ Euler((0, 0, yaw)).to_matrix().to_4x4()
    snow.frame = F
    L_s = LB - TIP - 0.05 - random.uniform(0.0, 0.25)
    x_s = X0 + 0.05 + random.uniform(0, 0.15)
    snow.box((sgn * (x_s + L_s / 2), 0, HB / 2 + 0.012), (L_s, TB + 0.01, 0.026 + random.uniform(0, 0.012)), rand_off=False)
    snow.frame = Matrix.Identity(4)
    z -= HB + GAP + random.uniform(-0.015, 0.02)
Z_LOW = z + GAP

# ------------------------------------------------------------------ post, plinth, cap, lantern, wreath
post = C.Geo("sign_post", M["post"], (0.6, 1.2))
seg = 8
post.cyl((0, 0, (POST_H + 0.42) / 2), POST_R * 1.08, POST_R * 0.98, POST_H - 0.42, seg=seg, rot=(0, 0, math.pi / 8), caps=False)
# a collar where the post meets the plinth, and the cap's little shingled roof
post.cyl((0, 0, 0.42), POST_R * 1.35, POST_R * 1.2, 0.12, seg=seg, rot=(0, 0, math.pi / 8), bottom=False)
RW, RD = 0.34, 0.34
ztop = POST_H
post.box((0, 0, ztop + 0.03), (0.26, 0.26, 0.06))
for sx in (-1, 1):     # two roof slopes, pitched along x
    post.box((sx * RW / 4, 0, ztop + 0.13), (RW / 2 + 0.04, RD, 0.025), rot=(0, sx * math.radians(32), 0))
stone = C.Geo("sign_plinth", M["stone"], (0.6, 0.6))
stone.box((0, 0, 0.18), (0.5, 0.5, 0.36), skip_bottom=True)
stone.box((0, 0, 0.38), (0.42, 0.42, 0.06), skip_bottom=True)
iron = C.Geo("sign_ironwork", M["iron"], (1, 1))
iron.uvsphere((0, 0, ztop + 0.33), 0.045, seg=8 if not LITE else 6, rings=5 if not LITE else 4)
iron.cyl((0, 0, ztop + 0.27), 0.012, 0.012, 0.08, seg=6)
# lantern bracket: a scrolled iron arm on the front-right, hanging the lantern in front of the boards
arm_y = -0.05
bz = Z_TOP + 0.18
iron.box((0.3, arm_y, bz), (0.5, 0.025, 0.025))
iron.box((0.16, arm_y, bz - 0.12), (0.025, 0.025, 0.3), rot=(0, math.radians(-40), 0))
if not LITE:
    sc = [(0.12 + 0.08 * math.cos(a), arm_y, bz + 0.07 + 0.06 * math.sin(a)) for a in np.linspace(math.pi * 1.2, math.pi * 3.0, 9)]
    iron.tube(sc, 0.008, tseg=4)
LX = 0.52
iron.cyl((LX, arm_y, bz - 0.07), 0.006, 0.006, 0.14, seg=4)
# lantern: iron cage with glass panes and a warm bulb inside
lz = bz - 0.32
iron.cyl((LX, arm_y, lz + 0.17), 0.1, 0.02, 0.09, seg=6)          # roof
iron.cyl((LX, arm_y, lz - 0.13), 0.075, 0.09, 0.04, seg=6)          # base
for k in range(6 if not LITE else 3):
    a = k * math.pi / 3 + math.pi / 6
    iron.box((LX + 0.075 * math.cos(a), arm_y + 0.075 * math.sin(a), lz + 0.02), (0.012, 0.012, 0.26))
glass = C.Geo("sign_lantern_glass", M["glass"], (1, 1))
glass.cyl((LX, arm_y, lz + 0.02), 0.07, 0.07, 0.26, seg=6, caps=False)
bulbs = C.Geo("bulbs_sign", M["bulb"], (1, 1))
bulbs.bulb((LX, arm_y, lz + 0.0), 0.035, sides=5)
light = C.empty("light_sign_0", (LX, arm_y - 0.25, lz), col)
# the fir wreath round the post just under the boards, with a red bow at the front
fir = C.Geo("sign_wreath", M["fir"], (1, 1))
wz = Z_LOW - 0.12
nseg = 14 if not LITE else 8
for k in range(nseg):
    a = 2 * math.pi * k / nseg
    r = POST_R + 0.07
    fir.uvsphere((r * math.cos(a), r * math.sin(a), wz + random.uniform(-0.02, 0.02)), 0.075, seg=6, rings=4,
                 scale=(1.0, 1.0, 0.8), rot=(0, 0, a))
rib = C.Geo("sign_bow", M["ribbon"], (1, 1))
rib.box((0, -POST_R - 0.15, wz), (0.07, 0.04, 0.07))
for sx in (-1, 1):
    rib.box((sx * 0.08, -POST_R - 0.16, wz + 0.01), (0.14, 0.02, 0.09), rot=(0, sx * 0.35, 0))
    rib.box((sx * 0.05, -POST_R - 0.16, wz - 0.12), (0.035, 0.012, 0.2), rot=(0, sx * 0.25, 0))
# snow: on the roof slopes, the plinth top and the wreath
for sx in (-1, 1):
    snow.box((sx * RW / 4, 0, ztop + 0.155), (RW / 2 + 0.02, RD - 0.02, 0.03), rot=(0, sx * math.radians(32), 0), rand_off=False)
snow.box((0, 0, 0.425), (0.4, 0.4, 0.03), rand_off=False)
snow.box((0.12, -0.12, 0.37), (0.24, 0.24, 0.025), rand_off=False)
for k in range(0, nseg, 2):
    a = 2 * math.pi * k / nseg
    snow.uvsphere(((POST_R + 0.08) * math.cos(a), (POST_R + 0.08) * math.sin(a), wz + 0.05), 0.05, seg=5, rings=3, scale=(1, 1, 0.45))

for g in (post, stone, iron, glass, bulbs, fir, rib, snow):
    ob = g.finish(col, smooth=g in (fir,))
    if ob:
        objs.append(ob)
    if g is post:            # the oak's grain runs along u in the timber texture: turn it up the post
        uvl = ob.data.uv_layers["UVMap"]
        a = np.zeros(len(uvl.data) * 2, np.float32); uvl.data.foreach_get("uv", a)
        a = a.reshape(-1, 2)[:, ::-1].copy().ravel(); uvl.data.foreach_set("uv", a)
objs.append(light)

tris = C.count_tris([o for o in objs if o.type == "MESH"])
C.log("SIGNPOST TRIANGLES", tris, "lite" if LITE else "full")

# ------------------------------------------------------------------ occlusion: per-vertex, through a ramp image
AO_PATH = os.path.join(TD, f"signpost_ao{'_lite' if LITE else ''}.png")
scene.world = bpy.data.worlds.new("ao_world")
gme = bpy.data.meshes.new("ao_ground")
gme.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)])
gob = bpy.data.objects.new("ao_ground", gme); scene.collection.objects.link(gob)
parts = [o for o in objs if o.type == "MESH" and not o.name.startswith(("bulbs_", "sign_lantern_glass"))]
for o in objs:
    if o.type == "MESH" and o.name.startswith(("bulbs_", "sign_lantern_glass")):
        o.hide_render = True
bpy.context.view_layer.update()
C.vertex_ao_to_ramp(parts, 0.1, 0.9, samples=48, distance=0.6, lift=0.3)
ao = bpy.data.images.new("signpost_ao", 16, 256)
C.finish_ao_image(ao, AO_PATH, lift=0.0, strip=(0.0, "ramp"), denoise=False)
for o in parts:
    for m in o.data.materials:
        C.attach_ao(m, ao)
for o in objs:
    o.hide_render = False
bpy.data.objects.remove(gob)

name = "signpost.lite" if LITE else "signpost"
if not os.environ.get("STATS_ONLY"):
    raw = C.export_glb(objs, os.path.join(OUT, f"{name}_raw.glb"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"))
    final = C.optimize(raw, os.path.join(C.MODELS, f"{name}.glb"), tex_size=512 if LITE else 1024)
    st = C.glb_stats(final)
    C.log("FINAL", name, "tris", st["tris"], "bytes", st["size"])
    C.log("NODES", [n for n in st["nodes"] if n.startswith(("act_", "light_", "bulbs_", "snow_"))])
    C.log("MATERIALS", st["materials"])

# ------------------------------------------------------------------ preview (close view, night)
if os.environ.get("PREVIEW") and not LITE:
    C.setup_cycles(samples=int(os.environ.get("SAMPLES", 48)), res=(1280, 720))
    C.night_world(0.6)
    gp = bpy.data.meshes.new("pv_ground")
    gp.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
    gpo = bpy.data.objects.new("pv_ground", gp); scene.collection.objects.link(gpo)
    gpo.data.materials.append(C.solid("pv_cobble", (0.06, 0.055, 0.05), rough=0.35))
    C.add_light("lantern", "POINT", (LX, arm_y - 0.25, lz), 60, (1.0, 0.72, 0.45), size=0.05)
    C.add_light("market_glow", "AREA", (-3, -6, 4), 400, (1.0, 0.7, 0.45), size=6, rot=(math.radians(60), 0, math.radians(-25)))
    C.add_light("moon", "SUN", (0, 0, 10), 0.25, (0.6, 0.7, 1.0), rot=(math.radians(50), 0, math.radians(30)))
    C.camera((1.6, -5.2, 2.6), (0, 0, 3.05), lens=40)
    C.compositor_fog_glare(near=8, far=60, fog_amount=0.2)
    C.render(os.path.join(C.REPO, "review", "round-5", "architect", "signpost.jpg"))
