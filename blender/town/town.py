"""Old town around the market square: a ring of German townhouses (half-timbered and plastered,
gable- and eaves-fronted, stepped and half-hipped gables, jetties, dormers, chimneys, shutters,
shopfronts with signs), houses down the side streets, a skyline of roofs beyond, and the
Marktkirche with its tower at three.js [8, -56].  Roofs carry snow_ caps.  Windows use the
emissive material window_warm (an atlas of lit and dark panes).

Round 1 pass 2: the church tower's openings and clock dials now sit on the stage faces (they were
buried inside the walls), the sandstone tiles at 2.4 m with real-size ashlar courses, the church has
two floodlight empties (light_church_*), wedge fillers close the gaps that open behind neighbouring
ring houses, and every material except the windows and bulbs has ambient occlusion in the glTF
occlusion slot: walls, roofs and stonework share a baked 2048 lightmap atlas; timbers, frames,
shutters, signs, ironwork and snow carry per-vertex occlusion through a ramp in the same image.

Round 1 pass 3: German slate courses (17 cm courses of 18-34 cm scale slates, blue- to purple-grey,
glossy and varied) on the church and the slate roofs, stronger tile relief and colour variation, three
slate dormers on the nave roof, leaded stained glass in the church lancets (two tall atlas regions,
mirrored, far dimmer than the house windows), mirrored and non-repeating window cells (shopfront panes
never repeat within a shop), shop-sign lettering in one small texture atlas instead of 9k triangles of
text, and no hidden end caps on posts, rails, braces, mullions and transoms.

Run:  /home/claude/tools/bpy-venv/bin/python blender/town/town.py
      LITE=1 (same command) for town.lite.glb
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
random.seed(42)
scene = C.reset()
col = C.collection("Town")

# ------------------------------------------------------------------ textures
T_PL = C.make_texture_set("town", "plaster", lambda: TX.plaster(1024), normal_strength=2.5)
T_TI = C.make_texture_set("town", "timber", lambda: TX.timber(512), normal_strength=3.0)
T_RO = C.make_texture_set("town", "roof_tiles", lambda: TX.roof_tiles(1024), normal_strength=8.0)
T_SL = C.make_texture_set("town", "slate", lambda: TX.slate_courses(1024, 2.4, 14, seed=77), normal_strength=8.0)
T_SR = C.make_texture_set("town", "sandstone_red", lambda: TX.sandstone(1024, 2.4, seed=81, red=True), normal_strength=3.0)
T_SY = C.make_texture_set("town", "sandstone_yellow", lambda: TX.sandstone(512, 2.4, seed=83, red=False), normal_strength=3.0)
T_PW = C.make_texture_set("town", "painted_wood", lambda: TX.painted_wood(512), normal_strength=3.0)
if LITE:
    # lite budget (round 1 pass 3): the small-scale sets drop to 256 px; roofs, red sandstone and the
    # window atlas keep 512 (they fill the view)
    T_TI = C.lite_texture_set(T_TI, 256)
    T_PW = C.lite_texture_set(T_PW, 256)
    T_SY = C.lite_texture_set(T_SY, 256)
    T_PL = C.lite_texture_set(T_PL, 256)
WIN_BASE = os.path.join(C.tex_dir("town"), "windows_base.png")
WIN_EMIT = os.path.join(C.tex_dir("town"), "windows_emit.png")
if os.environ.get("FORCE_TEX") or not os.path.exists(WIN_EMIT):
    b, e = TX.window_atlas(1024)
    TX.save_png(WIN_BASE, b ** (1 / 2.2)); TX.save_png(WIN_EMIT, np.clip(e, 0, 1) ** (1 / 2.2))

# ------------------------------------------------------------------ materials
PLASTER_TINTS = {
    "cream": (1.0, 0.93, 0.8), "ochre": (0.95, 0.78, 0.52), "rose": (0.95, 0.76, 0.7),
    "white": (0.97, 0.96, 0.93), "sage": (0.8, 0.86, 0.74), "blue": (0.78, 0.84, 0.9),
    "terracotta": (0.9, 0.62, 0.48), "yellow": (1.0, 0.88, 0.58),
}
MATS = {}
for k, c in PLASTER_TINTS.items():
    MATS["pl_" + k] = C.pbr("plaster_" + k, tex=T_PL, factor=c)
MATS["ti_brown"] = C.pbr("timber_brown", tex=T_TI, factor=(0.8, 0.75, 0.72))
MATS["ti_ox"] = C.pbr("timber_oxblood", tex=T_TI, factor=(1.2, 0.62, 0.5))
MATS["ti_black"] = C.pbr("timber_black", tex=T_TI, factor=(0.5, 0.48, 0.47))
MATS["roof_red"] = C.pbr("roof_tiles_red", tex=T_RO)
MATS["roof_brown"] = C.pbr("roof_tiles_brown", tex=T_RO, factor=(0.72, 0.66, 0.66))
MATS["slate"] = C.pbr("roof_slate", tex=T_SL)
MATS["stone_red"] = C.pbr("sandstone_red", tex=T_SR)
MATS["stone_yel"] = C.pbr("sandstone_yellow", tex=T_SY)
PAINT = {"frame": (0.95, 0.93, 0.88), "green": (0.28, 0.42, 0.3), "red": (0.62, 0.2, 0.16),
         "blue": (0.3, 0.4, 0.55), "grey": (0.55, 0.57, 0.56), "brown": (0.45, 0.3, 0.2),
         "sign": (0.12, 0.16, 0.13), "cream": (0.9, 0.85, 0.7)}
for k, c in PAINT.items():
    MATS["pw_" + k] = C.pbr("paint_" + k, tex=T_PW, factor=c)
MATS["window"] = C.pbr("window_warm", base_tex=WIN_BASE, emit_tex=WIN_EMIT, emit_strength=2.0, rough=0.12)
MATS["zinc"] = C.solid("zinc", (0.35, 0.36, 0.37), rough=0.35, metal=0.9)
MATS["iron"] = C.solid("wrought_iron", (0.02, 0.02, 0.02), rough=0.45, metal=0.7)
MATS["gilt"] = C.solid("gilt", (0.85, 0.62, 0.25), rough=0.25, metal=1.0)
MATS["copper"] = C.solid("copper_verdigris", (0.25, 0.45, 0.38), rough=0.5, metal=0.3)
MATS["snow"] = C.solid("snow", (0.82, 0.85, 0.92), rough=0.75)
MATS["bulb"] = C.solid("bulb_warm", (1.0, 0.8, 0.55), rough=0.3, emit=(1.0, 0.62, 0.28), strength=6.0)
MATS["dial"] = C.solid("clock_dial", (0.9, 0.85, 0.7), rough=0.5, emit=(1.0, 0.85, 0.6), strength=0.8)
MATS["dark"] = C.solid("dark_opening", (0.01, 0.01, 0.012), rough=0.9)
for m in MATS.values():
    if m:
        m.use_backface_culling = True

MATS["signs"] = None                 # the sign lettering atlas: made once every sign is known (see sign_texture())
UVM = {}
for k in MATS:
    if k.startswith("pl_"): UVM[k] = (2.5, 2.5)
    elif k.startswith("ti_"): UVM[k] = (1.0, 0.25)
    elif k.startswith("roof"): UVM[k] = (2.16, 2.10)
    elif k == "slate": UVM[k] = (2.4, 2.4)
    elif k.startswith("stone"): UVM[k] = (2.4, 2.4)
    elif k.startswith("pw_"): UVM[k] = (1.0, 1.0)
    else: UVM[k] = (1.0, 1.0)
G = C.GeoSet("town", MATS, UVM)

# ------------------------------------------------------------------ atlas cells
LIT_CELLS = [0, 1, 2, 3, 4, 5, 6, 7, 8]
DARK_CELLS = [10, 14, 12, 10, 14]            # 12 is a barely lit room; the others are dark
STAINED_COLS = (1, 3)                        # the two stained-glass regions: bottom half of columns 1 and 3


def cell_rect(c, pad=0.006, mirror=None):
    """UV rectangle of atlas cell c; mirror flips it left to right (None = at random), so neighbouring
    windows showing the same cell still differ."""
    cx, cy = c % 4, c // 4
    u0, v0, u1, v1 = (cx / 4 + pad, 1 - (cy + 1) / 4 + pad, (cx + 1) / 4 - pad, 1 - cy / 4 - pad)
    if mirror is None:
        mirror = random.random() < 0.5
    return (u1, v0, u0, v1) if mirror else (u0, v0, u1, v1)


def stained_rect(k, pad=0.004):
    """Lancet k's stained-glass region: variant k % 2, mirrored for k // 2 odd (four looks in turn)."""
    cx = STAINED_COLS[k % 2]
    u0, u1 = cx / 4 + pad, (cx + 1) / 4 - pad
    return (u1, pad, u0, 0.5 - pad) if (k // 2) % 2 else (u0, pad, u1, 0.5 - pad)


def pick_cell(lit_p):
    return random.choice(LIT_CELLS) if random.random() < lit_p else random.choice(DARK_CELLS)


# ------------------------------------------------------------------ facade elements (house-local coords, front plane y = yf, facing -y)

def window(x, zb, ww, wh, yf, lit_p, h, surround=None, shutters=None, mullion=True, cell=None, mirror=None):
    g = G["window"]
    c = pick_cell(lit_p) if cell is None else cell
    g.quad_rect((x, yf - 0.004, zb + wh / 2), ww, wh, "-y", uv_rect=cell_rect(c, mirror=mirror))
    fr = G["pw_frame"]
    fw, fd = 0.06, 0.045
    if not LITE or wh > 1.6:
        fr.frame_ring(x, zb, ww, wh, fw, fd, yf)
    if mullion and not LITE:
        fr.wall_beam((x, zb), (x, zb + wh), 0.045, 0.03, yf, ends=False)
        fr.wall_beam((x - ww / 2, zb + wh * 0.68), (x + ww / 2, zb + wh * 0.68), 0.045, 0.03, yf, ends=False)
    if surround:
        s = G[surround]
        sw, sd = 0.14, 0.035
        if not LITE:      # the lite town keeps the lintel and sill only (a phone can't see the jambs)
            s.wall_beam((x - ww / 2 - fw - sw / 2, zb - 0.02), (x - ww / 2 - fw - sw / 2, zb + wh + fw), sw, sd, yf)
            s.wall_beam((x + ww / 2 + fw + sw / 2, zb - 0.02), (x + ww / 2 + fw + sw / 2, zb + wh + fw), sw, sd, yf)
        s.wall_beam((x - ww / 2 - fw - sw, zb + wh + fw + 0.09), (x + ww / 2 + fw + sw, zb + wh + fw + 0.09), 0.2, sd + 0.02, yf)
        s.box((x, yf - 0.07, zb - fw - 0.05), (ww + 2 * fw + 2 * sw + 0.08, 0.14, 0.09), skip_back=True)
    else:
        G["pw_frame"].box((x, yf - 0.06, zb - fw - 0.03), (ww + 0.2, 0.1, 0.05), skip_back=True)   # sill board
    if shutters and not LITE:
        s = G[shutters]
        for sgn in (-1, 1):
            s.box((x + sgn * (ww / 2 + fw + ww / 4 + 0.02), yf - 0.03, zb + wh / 2), (ww / 2 - 0.02, 0.03, wh + 0.04), skip_back=True)
    # snow on the sill
    if not LITE and random.random() < 0.55:
        G["snow"].box((x, yf - 0.07, zb - fw + 0.01 + (0.02 if surround else 0)), (ww + 0.1, 0.1, 0.035), skip_back=True, skip_bottom=True)


def door(x, w, hgt, yf, paint, stone):
    G[paint].box((x, yf - 0.02, hgt / 2), (w, 0.05, hgt), skip_back=True)
    # panels
    if not LITE:
        for sgn in (-1, 1):
            for zc in (hgt * 0.3, hgt * 0.68):
                G[paint].box((x + sgn * w / 4, yf - 0.05, zc), (w / 2 - 0.16, 0.025, hgt * 0.28), skip_back=True)
    s = G[stone]
    s.wall_beam((x - w / 2 - 0.1, 0), (x - w / 2 - 0.1, hgt + 0.18), 0.2, 0.05, yf)
    s.wall_beam((x + w / 2 + 0.1, 0), (x + w / 2 + 0.1, hgt + 0.18), 0.2, 0.05, yf)
    s.wall_beam((x - w / 2 - 0.2, hgt + 0.12), (x + w / 2 + 0.2, hgt + 0.12), 0.25, 0.07, yf)
    s.box((x, yf - 0.2, 0.08), (w + 0.5, 0.4, 0.16))                    # step
    # transom light above the door
    G["window"].quad_rect((x, yf - 0.03, hgt - 0.22), w - 0.2, 0.3, "-y", uv_rect=cell_rect(random.choice(LIT_CELLS)))


FONT_DIR = os.path.join(C.REPO, "blender", "lib", "fonts")
FRAKTUR = ("Gasthaus", "Weinstube", "Bäckerei", "Metzgerei", "Konditorei", "Kaffeehaus")


def load_font(text):
    name = "UnifrakturCook-Bold.ttf" if any(text.startswith(f) for f in FRAKTUR) else "AlegreyaSC-ExtraBold.ttf"
    path = os.path.join(FONT_DIR, name)
    return bpy.data.fonts.load(path, check_existing=True) if os.path.exists(path) else None


SIGN_ROWS = []                 # (text, width_m) per atlas row
SIGN_ROW_PX, SIGN_ATLAS = 42, 1024
SIGN_FACE_H = 0.39             # the painted face between the two gilt rails
SIGN_PX_PER_M = SIGN_ROW_PX / SIGN_FACE_H


def sign_row(text, w):
    key = (text, round(w, 1))
    if key not in SIGN_ROWS:
        if len(SIGN_ROWS) >= SIGN_ATLAS // SIGN_ROW_PX:
            same = [k for k in SIGN_ROWS if k[0] == text] or SIGN_ROWS
            key = same[0]
            C.log("sign atlas full: reusing", key)
        else:
            SIGN_ROWS.append(key)
    return SIGN_ROWS.index(key), key[1]


def sign(x, zc, text, yf, w=None):
    """Shop sign: a painted board between two gilt rails; the lettering is a quad with its own row in
    the sign atlas (2 triangles instead of hundreds of font triangles)."""
    w = w or max(1.6, 0.26 * len(text))
    G["pw_sign"].box((x, yf - 0.04, zc), (w, 0.05, 0.42), skip_back=True)
    G["gilt"].wall_beam((x - w / 2, zc + 0.2), (x + w / 2, zc + 0.2), 0.025, 0.07, yf)
    G["gilt"].wall_beam((x - w / 2, zc - 0.2), (x + w / 2, zc - 0.2), 0.025, 0.07, yf)
    row, wa = sign_row(text, w)
    wpx = min(SIGN_ATLAS, round(wa * SIGN_PX_PER_M))
    pad = 0.5 / SIGN_ATLAS
    rect = (pad, 1 - (row + 1) * SIGN_ROW_PX / SIGN_ATLAS + pad, wpx / SIGN_ATLAS - pad, 1 - row * SIGN_ROW_PX / SIGN_ATLAS - pad)
    G["signs"].quad_rect((x, yf - 0.067, zc), w, SIGN_FACE_H, "-y", uv_rect=rect)


def sign_texture():
    """Paint the sign atlas once every sign is placed and give the signs mesh its material."""
    d = C.tex_dir("town")
    paths = {k: os.path.join(d, f"shop_signs{'_lite' if LITE else ''}_{k}.png") for k in ("color", "mr", "normal")}
    t = TX.sign_atlas(SIGN_ROWS, lambda text: os.path.join(FONT_DIR, "UnifrakturCook-Bold.ttf" if any(text.startswith(f) for f in FRAKTUR) else "AlegreyaSC-ExtraBold.ttf"),
                      n=SIGN_ATLAS, row_px=SIGN_ROW_PX, px_per_m=SIGN_PX_PER_M)
    TX.save_png(paths["color"], t["color"] ** (1 / 2.2))
    TX.save_png(paths["mr"], np.stack([np.ones_like(t["rough"]), t["rough"], t["metal"]], -1))
    TX.save_png(paths["normal"], TX.normal_from_height(t["height"], 2.5))
    m = C.pbr("shop_signs", tex={"color": paths["color"], "normal": paths["normal"]})
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N["Principled BSDF"]
    uvn = next(n for n in N if n.type == "UVMAP")
    mr = N.new("ShaderNodeTexImage"); mr.image = C.load_img(paths["mr"], True)
    sep = N.new("ShaderNodeSeparateColor")
    L.new(uvn.outputs["UV"], mr.inputs["Vector"]); L.new(mr.outputs["Color"], sep.inputs["Color"])
    L.new(sep.outputs["Green"], bsdf.inputs["Roughness"]); L.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    m.use_backface_culling = True
    MATS["signs"] = m
    for gs in (G_RING,):
        if "signs" in gs.g:
            gs.g["signs"].mat = m
    C.log("sign atlas rows", len(SIGN_ROWS))


def pretzel_sign(x, zc, yf):
    """Wrought-iron bracket sign with a gilt pretzel (Bäckerei)."""
    ir = G["iron"]
    ir.beam((x, yf, zc + 0.5), (x, yf - 1.1, zc + 0.5), 0.04, 0.04)
    ir.beam((x, yf, zc), (x, yf - 0.8, zc + 0.48), 0.03, 0.03)
    pts = []
    for k in range(41):
        t = 2 * math.pi * k / 40
        px = 0.32 * math.sin(t) * (1 + 0.35 * math.cos(t))
        pz = 0.28 * math.cos(t) - 0.12 * math.cos(2 * t)
        pts.append(Vector((x, yf - 0.75 + px, zc + pz)))
    G["gilt"].tube(pts, 0.035, tseg=6)
    ir.beam((x, yf - 0.75, zc + 0.5), (x, yf - 0.75, zc + 0.3), 0.012, 0.012)


def wall_lantern(x, z, yf):
    ir = G["iron"]
    ir.beam((x, yf, z + 0.25), (x, yf - 0.4, z + 0.25), 0.03, 0.03)
    ir.cyl((x, yf - 0.4, z + 0.2), 0.13, 0.03, 0.12, seg=6, bottom=False)
    ir.cyl((x, yf - 0.4, z - 0.22), 0.05, 0.09, 0.06, seg=6)
    WALL_BULBS.append((x, yf - 0.4, z, G._frame))


WALL_BULBS = []

# ------------------------------------------------------------------ timber framing


def timber_floor(ti, W, z0, z1, yf, wins, sill_z, lintel_z, parapet="x", corner_braces=True):
    g = G[ti]
    dp = 0.04
    g.wall_beam((-W / 2, z0 + 0.1), (W / 2, z0 + 0.1), 0.2, dp + 0.012, yf)            # sill beam
    g.wall_beam((-W / 2, z1 - 0.09), (W / 2, z1 - 0.09), 0.18, dp + 0.012, yf)         # top plate
    tw = 0.17
    posts = [-W / 2 + tw / 2, W / 2 - tw / 2]
    for x, ww in wins:
        posts += [x - ww / 2 - 0.06 - tw / 2, x + ww / 2 + 0.06 + tw / 2]
    posts = sorted(posts)
    # add intermediate posts in wide solid panels
    extra = []
    for a, b in zip(posts, posts[1:]):
        inside_window = any(abs((a + b) / 2 - x) < ww / 2 for x, ww in wins)
        if not inside_window and b - a > 1.3:
            extra.append((a + b) / 2)
    posts = sorted(posts + extra)
    for x in posts:
        g.wall_beam((x, z0 + 0.2), (x, z1 - 0.18), tw, dp, yf, ends=False)
    # rails at sill and lintel height
    g.wall_beam((-W / 2 + tw, sill_z - 0.07), (W / 2 - tw, sill_z - 0.07), 0.14, dp - 0.008, yf, ends=False)
    g.wall_beam((-W / 2 + tw, lintel_z + 0.07), (W / 2 - tw, lintel_z + 0.07), 0.14, dp - 0.008, yf, ends=False)
    if LITE:
        return
    # parapet ornaments under the windows
    for x, ww in wins:
        a, b = x - ww / 2 - 0.02, x + ww / 2 + 0.02
        lo, hi = z0 + 0.22, sill_z - 0.15
        if hi - lo < 0.3: continue
        if parapet == "x":
            g.wall_beam((a, lo), (b, hi), 0.12, dp - 0.014, yf, ends=False)
            g.wall_beam((a, hi), (b, lo), 0.12, dp - 0.016, yf, ends=False)
        elif parapet == "fb":   # "Feuerbock": two curved-looking struts meeting at the top
            m = (a + b) / 2
            g.wall_beam((a, lo), (m - 0.05, hi), 0.11, dp - 0.014, yf, ends=False)
            g.wall_beam((b, lo), (m + 0.05, hi), 0.11, dp - 0.016, yf, ends=False)
            g.wall_beam((m, lo), (m, hi), 0.1, dp - 0.012, yf)
        elif parapet == "rhombus":
            m = (a + b) / 2; c = (lo + hi) / 2
            for p0, p1 in (((a, c), (m, hi)), ((m, hi), (b, c)), ((b, c), (m, lo)), ((m, lo), (a, c))):
                g.wall_beam(p0, p1, 0.09, dp - 0.014, yf, ends=False)
    # braces ("Mann" figure) in solid panels
    for a, b in zip(posts, posts[1:]):
        inside_window = any(abs((a + b) / 2 - x) < ww / 2 + 0.1 for x, ww in wins)
        if inside_window or b - a < 0.45:
            continue
        mid = (z0 + z1) / 2
        if corner_braces and (a == posts[0] or b == posts[-1]):
            if a == posts[0]:
                g.wall_beam((a + 0.08, mid + 0.25), (b - 0.05, z0 + 0.22), 0.13, dp - 0.014, yf, ends=False)
                g.wall_beam((a + 0.08, mid - 0.25), (b - 0.05, z1 - 0.2), 0.13, dp - 0.016, yf, ends=False)
            else:
                g.wall_beam((b - 0.08, mid + 0.25), (a + 0.05, z0 + 0.22), 0.13, dp - 0.014, yf, ends=False)
                g.wall_beam((b - 0.08, mid - 0.25), (a + 0.05, z1 - 0.2), 0.13, dp - 0.016, yf, ends=False)
        elif b - a > 0.8:
            g.wall_beam((a + 0.05, z0 + 0.22), (b - 0.05, z1 - 0.2), 0.12, dp - 0.014, yf, ends=False)
            g.wall_beam((a + 0.05, z1 - 0.2), (b - 0.05, z0 + 0.22), 0.12, dp - 0.016, yf, ends=False)


def jetty_joists(ti, W, z, yf, overhang):
    """Row of joist ends under a jetty."""
    if LITE: return
    g = G[ti]
    n = int(W / 0.55)
    for k in range(n + 1):
        x = -W / 2 + 0.12 + k * (W - 0.24) / n
        g.box((x, yf - overhang / 2 + 0.02, z - 0.08), (0.13, overhang + 0.06, 0.15))


# ------------------------------------------------------------------ roofs


def slope(mat, a, b, c, d, thick=0.14):
    """Roof slab: quad a-b-c-d on the top surface (a,b along eaves, c,d at ridge), extruded down."""
    n = (Vector(b) - Vector(a)).cross(Vector(d) - Vector(a)).normalized()
    if n.z < 0: n = -n; a, b, c, d = b, a, d, c
    G[mat].prism([a, b, c, d], tuple(-n * thick))
    return n


def snow_on(a, b, c, d, n, inset=0.12, lift=0.05, thick=0.1):
    A, B, Cc, D = [Vector(p) for p in (a, b, c, d)]
    ex = (B - A).normalized(); up = (D - A).normalized()
    A2 = A + ex * inset + n * lift; B2 = B - ex * inset + n * lift
    C2 = Cc - ex * inset + n * lift - up * 0.03; D2 = D + ex * inset + n * lift - up * 0.03
    G["snow"].prism([tuple(A2), tuple(B2), tuple(C2), tuple(D2)], tuple(-n * thick))
    # rounded lip hanging over the eave
    if not LITE:
        G["snow"].beam(tuple(A2 - n * 0.02), tuple(B2 - n * 0.02), 0.12, 0.1, up=tuple(n))


def gable_roof_along_y(mat, W, y0, y1, ze, pitch, over_side=0.35, over_front=0.3, snow=True):
    """Ridge along local y (gable faces the square).  Returns ridge height."""
    rise = (W / 2) * math.tan(pitch)
    zr = ze + rise
    ov = over_side
    ez = ze - ov * math.tan(pitch)
    for sgn in (-1, 1):
        a = (sgn * (W / 2 + ov), y0 - over_front, ez)
        b = (sgn * (W / 2 + ov), y1 + 0.3, ez)
        c = (0, y1 + 0.3, zr + 0.08)
        d = (0, y0 - over_front, zr + 0.08)
        pts = (a, b, c, d) if sgn > 0 else (b, a, d, c)
        n = slope(mat, *pts)
        if snow:
            snow_on(*pts, n)
    # ridge cap
    G[mat].beam((0, y0 - over_front, zr + 0.1), (0, y1 + 0.3, zr + 0.1), 0.2, 0.1)
    return zr


def gable_roof_along_x(mat, W, yF, yB, ze, pitch, over=0.45, over_side=0.25, snow=True, xc=0.0):
    """Ridge along local x (eaves face the square)."""
    D = yB - yF
    rise = (D / 2) * math.tan(pitch)
    zr = ze + rise
    ym = (yF + yB) / 2
    ez = ze - over * math.tan(pitch)
    xa, xb = xc - W / 2 - over_side, xc + W / 2 + over_side
    front = ((xa, yF - over, ez), (xb, yF - over, ez), (xb, ym, zr + 0.08), (xa, ym, zr + 0.08))
    back = ((xb, yB + over, ez), (xa, yB + over, ez), (xa, ym, zr + 0.08), (xb, ym, zr + 0.08))
    for pts in (front, back):
        n = slope(mat, *pts)
        if snow: snow_on(*pts, n)
    G[mat].beam((xa, ym, zr + 0.1), (xb, ym, zr + 0.1), 0.2, 0.1)
    return zr


def gutter_and_pipe(W, y, z, x_pipe):
    if LITE: return
    G["zinc"].cyl((0, y - 0.08, z - 0.05), 0.07, 0.07, W, seg=6, rot=(0, math.pi / 2, 0), caps=False)
    G["zinc"].cyl((x_pipe, y - 0.1, z / 2), 0.045, 0.045, z, seg=6, caps=False)


def chimney(x, y, zr_at, h, mat):
    G[mat].box((x, y, zr_at + h / 2 - 0.6), (0.55, 0.7, h + 1.2))
    G["stone_red"].box((x, y, zr_at + h + 0.05), (0.7, 0.85, 0.1))
    if not LITE:
        G["dark"].box((x, y, zr_at + h + 0.11), (0.3, 0.4, 0.04))
    G["snow"].box((x, y, zr_at + h + 0.13), (0.62, 0.77, 0.06))


def dormer(x, yF_roof, z_base, pitch_main, wdw, mat_wall, mat_roof, lit_p, win_frame=True):
    """Gabled dormer sitting on a slope that rises toward +y from the eave line."""
    w, h, dpt = wdw, 1.35, 1.6
    y0 = yF_roof
    G[mat_wall].box((x, y0 + dpt / 2, z_base + h / 2), (w, dpt, h), skip_bottom=True)
    window(x, z_base + 0.25, w - 0.45, 0.85, y0, lit_p, h, mullion=False)
    rp = math.radians(50)
    ze = z_base + h
    rise = (w / 2 + 0.1) * math.tan(rp)
    for sgn in (-1, 1):
        a = (sgn * (w / 2 + 0.15) + x, y0 - 0.2, ze - 0.05)
        b = (sgn * (w / 2 + 0.15) + x, y0 + dpt + 0.5, ze - 0.05)
        c = (x, y0 + dpt + 0.5, ze + rise)
        d = (x, y0 - 0.2, ze + rise)
        pts = (a, b, c, d) if sgn > 0 else (b, a, d, c)
        n = slope(mat_roof, *pts, thick=0.1)
        snow_on(*pts, n, inset=0.05, lift=0.04, thick=0.07)
    # dormer gable triangle
    G[mat_wall].prism([(x - w / 2, y0, ze), (x + w / 2, y0, ze), (x, y0, ze + rise - 0.1)], (0, dpt, 0))


# ------------------------------------------------------------------ house builder

SHOPS = ["Bäckerei", "Buchhandlung", "Café am Markt", "Weinstube", "Metzgerei", "Uhren · Schmuck",
         "Spielwaren", "Konditorei", "Blumen", "Gasthaus Zum Hirsch", "Kaffeehaus", "Papeterie",
         "Hutmacher", "Feinkost", "Eisenwaren", "Goldschmied"]
random.shuffle(SHOPS)
TYPES = ["timber_gable", "timber_eaves", "plaster_stepped", "plaster_eaves", "plaster_halfhip", "timber_gable_tall"]


def make_spec(prev, W, idx):
    for _ in range(40):
        typ = random.choice(TYPES)
        if prev and typ == prev["typ"]:
            continue
        s = dict(typ=typ, W=W)
        timber = typ.startswith("timber")
        s["upper"] = random.choice([2, 2, 3, 3]) if typ != "timber_gable_tall" else 3
        if typ == "plaster_eaves": s["upper"] = random.choice([2, 3, 3])
        s["h0"] = random.uniform(3.4, 3.9)
        s["hf"] = random.uniform(2.75, 3.1)
        s["D"] = random.uniform(9.5, 12.0)
        s["jetty"] = random.uniform(0.18, 0.32) if timber else 0.0
        tints = list(PLASTER_TINTS)
        if timber:
            tints = ["cream", "white", "ochre", "rose", "yellow", "cream", "white"]
        s["tint"] = random.choice([t for t in tints if not prev or t != prev["tint"]])
        s["ti"] = random.choice(["ti_brown", "ti_brown", "ti_ox", "ti_black"])
        s["ground"] = random.choice(["stone_red", "stone_yel", "plaster"]) if timber else random.choice(["plaster", "stone_red", "plaster"])
        s["roof"] = random.choice(["roof_red", "roof_red", "roof_brown", "slate"]) if typ != "plaster_stepped" else random.choice(["roof_red", "roof_brown"])
        s["pitch"] = math.radians(random.uniform(52, 60) if "gable" in typ or "stepped" in typ or "halfhip" in typ else random.uniform(44, 52))
        s["shutters"] = random.choice([None, None, "pw_green", "pw_red", "pw_blue", "pw_grey"]) if not timber else random.choice([None, None, None, "pw_green", "pw_red"])
        s["surround"] = None if timber else random.choice(["stone_red", "stone_yel", "stone_yel"])
        s["shop"] = random.random() < 0.55
        s["lit"] = random.choice([0.25, 0.45, 0.6, 0.75])
        s["parapet"] = random.choice(["x", "fb", "rhombus", "x"])
        s["nwin"] = max(2, min(5, int(W / 1.75)))
        s["dormers"] = random.choice([1, 2, 2, 3]) if "eaves" in typ else 0
        if prev and all(s[k] == prev[k] for k in ("typ", "tint", "upper")):
            continue
        return s
    return s


def build_house(F, s, idx, open_sides=()):
    G.set_frame(F)
    W, D, typ = s["W"], s["D"], s["typ"]
    timber = typ.startswith("timber")
    wall = "pl_" + s["tint"]
    gmat = wall if s["ground"] == "plaster" else s["ground"]
    h0, hf, n_up = s["h0"], s["hf"], s["upper"]
    lit = s["lit"]
    nwin = s["nwin"]
    # ---- ground floor body (plinth below grade)
    G[gmat].box((0, D / 2, (h0 - 0.4) / 2), (W, D, h0 + 0.4), skip_bottom=True)
    if s["ground"] == "plaster" and not LITE:
        G["stone_red" if s["surround"] != "stone_yel" else "stone_yel"].box((0, -0.02, 0.2), (W + 0.02, 0.08, 0.5), skip_back=True)
    # ground floor openings
    if s["shop"]:
        shop = SHOPS[idx % len(SHOPS)]
        dw = 1.1
        dx = random.choice([-1, 1]) * (W / 2 - 1.0)
        door(dx, dw, 2.35, 0, "pw_" + random.choice(["green", "brown", "red", "blue"]), s["surround"] or "stone_yel")
        # display windows filling the rest
        xa, xb = (-W / 2 + 0.45, dx - dw / 2 - 0.4) if dx > 0 else (dx + dw / 2 + 0.4, W / 2 - 0.45)
        nd = 2 if xb - xa > 3.2 else 1
        panes = random.sample([0, 3, 6, 5, 2, 8], nd)      # never the same display twice in one shop
        for k in range(nd):
            seg = (xb - xa) / nd
            cx = xa + seg * (k + 0.5)
            window(cx, 0.6, seg - 0.35, 1.7, 0, 1.0, h0, surround=s["surround"] or "stone_yel", mullion=True,
                   cell=panes[k], mirror=k == 1)
        sign(0 if nd == 2 else (xa + xb) / 2, h0 - 0.42, shop, 0, w=min(W - 1.0, max(2.0, 0.25 * len(shop))))
        if "Bäck" in shop or "Kondi" in shop:
            pretzel_sign(-dx * 0.9, h0 + 0.9, 0)
        if not LITE:  # fir garland with bulbs over the shopfront
            GARLANDS.append((F, W, h0 - 0.2))
    else:
        dx = random.uniform(-W / 2 + 1.2, W / 2 - 1.2)
        door(dx, 1.05, 2.3, 0, "pw_" + random.choice(["green", "brown", "red", "brown"]), s["surround"] or ("stone_red" if s["ground"] != "stone_red" else "stone_yel"))
        k = 0
        for x in np.linspace(-W / 2 + W / (2 * nwin), W / 2 - W / (2 * nwin), nwin):
            if abs(x - dx) < 1.2: continue
            window(x, 1.05, 0.85, 1.35, 0, lit, h0, surround=s["surround"] or (None if s["ground"] == "plaster" else None),
                   shutters=s["shutters"])
        if random.random() < 0.5:
            wall_lantern(dx + 0.95, 2.5, 0)
    # ---- upper floors
    z = h0
    yf = 0.0
    xs = list(np.linspace(-W / 2 + W / (2 * nwin), W / 2 - W / (2 * nwin), nwin))
    ww = min(0.95, W / nwin - 0.8)
    for f in range(n_up):
        jet = s["jetty"]
        if jet:
            jetty_joists(s["ti"], W, z, yf, jet)
            yf -= jet
        G[wall].box((0, yf + (D - yf) / 2, z + hf / 2), (W, D - yf, hf))
        wh = min(1.4, hf - 1.35)
        sill = z + 0.85
        for x in xs:
            window(x, sill, ww, wh, yf, lit, hf, surround=s["surround"] if not timber else None,
                   shutters=s["shutters"])
        if timber:
            timber_floor(s["ti"], W, z, z + hf, yf, [(x, ww) for x in xs], sill, sill + wh, s["parapet"])
        elif not LITE:
            # string course and corner quoins
            G[s["surround"]].box((0, yf - 0.04, z + 0.03), (W + 0.04, 0.1, 0.16), skip_back=True)
            for sgn in (-1, 1):
                for q in range(int(hf / 0.45)):
                    qw = 0.42 if q % 2 == 0 else 0.3
                    G[s["surround"]].box((sgn * (W / 2 - qw / 2 + 0.01), yf - 0.015, z + 0.25 + q * 0.45), (qw, 0.05, 0.38), skip_back=True)
        z += hf
    ze = z
    yb = D
    # ---- roofs and gables
    roof = s["roof"]
    if typ in ("timber_gable", "timber_gable_tall", "plaster_halfhip"):
        rise = (W / 2) * math.tan(s["pitch"])
        half = typ == "plaster_halfhip"
        ztop = ze + rise * (0.72 if half else 1.0)
        wtop = W * (0.28 if half else 0.0)
        # gable wall
        pts = [(-W / 2, yf, ze), (W / 2, yf, ze)]
        pts += [(wtop / 2, yf, ztop), (-wtop / 2, yf, ztop)] if half else [(0, yf, ztop)]
        G[wall].prism(pts, (0, 0.3, 0))
        if timber:
            g = G[s["ti"]]
            gz = ze + rise * 0.45
            wg = W * (1 - 0.45)
            g.wall_beam((-wg / 2, gz), (wg / 2, gz), 0.16, 0.045, yf)
            g.wall_beam((0, ze), (0, ztop - 0.1), 0.16, 0.04, yf)
            if not LITE:
                for sgn in (-1, 1):
                    g.wall_beam((sgn * W * 0.25, ze), (sgn * W * 0.25, gz), 0.15, 0.04, yf)
                    g.wall_beam((sgn * (W / 2 - 0.3), ze + 0.1), (sgn * W * 0.22, gz - 0.05), 0.12, 0.034, yf)
                    g.wall_beam((sgn * wg * 0.35, gz), (sgn * 0.12, ze + rise * 0.8), 0.12, 0.034, yf)
            gw = [(-W * 0.14, 0.7), (W * 0.14, 0.7)] if W > 6.5 else [(0, 0.75)]
            for x, w_ in gw:
                window(x, ze + 0.55, w_, 1.0, yf, lit * 0.8, 2, mullion=False)
            window(0, gz + 0.35, 0.5, 0.7, yf, lit * 0.5, 1.5, mullion=False)
        else:
            for x in (-W * 0.16, W * 0.16):
                window(x, ze + 0.6, 0.75, 1.1, yf, lit * 0.8, 2, surround=s["surround"], shutters=s["shutters"])
            window(0, ze + rise * 0.5, 0.55, 0.8, yf, lit * 0.4, 2, surround=s["surround"])
        # roof slopes
        over = 0.35
        ez = ze - over * math.tan(s["pitch"])
        zr = ze + rise
        if half:
            # main slopes stop at the hip line; small hip triangle leans back
            yh = yf + (zr - ztop) / math.tan(s["pitch"])
            for sgn in (-1, 1):
                a = (sgn * (W / 2 + over), yf - 0.35, ez)
                b = (sgn * (W / 2 + over), yb + 0.3, ez)
                c = (0, yb + 0.3, zr + 0.08)
                d = (0, yh, zr + 0.08)
                e2 = (sgn * (wtop / 2 + 0.25), yf - 0.35, zr + 0.08 - (wtop / 2 + 0.25) * math.tan(s["pitch"]))
                pts5 = [a, b, c, d, e2] if sgn > 0 else [b, a, e2, d, c]
                nn = (Vector(pts5[1]) - Vector(pts5[0])).cross(Vector(pts5[-1]) - Vector(pts5[0])).normalized()
                if nn.z < 0: nn = -nn; pts5 = pts5[::-1]
                G[roof].prism(pts5, tuple(-nn * 0.14))
                snow_on(a if sgn > 0 else b, b if sgn > 0 else a, c if sgn > 0 else d, d if sgn > 0 else c,
                        nn, inset=0.4, lift=0.06)
            zh = zr + 0.08 - (wtop / 2 + 0.25) * math.tan(s["pitch"])
            hip = [(-wtop / 2 - 0.25, yf - 0.35, zh), (wtop / 2 + 0.25, yf - 0.35, zh), (0, yh, zr + 0.1)]
            nn = (Vector(hip[1]) - Vector(hip[0])).cross(Vector(hip[2]) - Vector(hip[0])).normalized()
            if nn.z < 0: hip = hip[::-1]; nn = -nn
            G[roof].prism(hip, tuple(-nn * 0.14))
            G["snow"].prism([tuple(Vector(p) + nn * 0.06) for p in hip], tuple(-nn * 0.08))
            G[roof].beam((0, yh, zr + 0.1), (0, yb + 0.3, zr + 0.1), 0.2, 0.1)
        else:
            zr = gable_roof_along_y(roof, W, yf, yb, ze, s["pitch"], over_side=over, over_front=0.35)
            if timber and not LITE:
                for sgn in (-1, 1):   # barge boards
                    G[s["ti"]].beam((sgn * (W / 2 + 0.3), yf - 0.3, ez + 0.02), (0, yf - 0.3, zr + 0.02), 0.22, 0.05,
                                    up=(0, -1, 0))
        # back gable
        G[wall].prism([(W / 2, yb, ze), (-W / 2, yb, ze), (0, yb, zr - 0.05)], (0, -0.3, 0))
        chimney(random.uniform(-W / 4, W / 4) * 0.3, yb - random.uniform(2, 4), zr - 0.6, 1.1, wall)
    elif typ == "plaster_stepped":
        rise = (W / 2) * math.tan(s["pitch"])
        zr = ze + rise
        steps = random.choice([4, 5, 6])
        pts = [(-W / 2, yf, ze), (W / 2, yf, ze)]
        right = []
        for k in range(steps):
            x_out = W / 2 - k * (W / 2) / steps
            z_top = ze + (k + 1) * rise / steps + 0.35
            right += [(x_out, yf, z_top)]
            right += [(x_out - (W / 2) / steps, yf, z_top)]
        right = right[:-1] + [(0.35, yf, zr + 0.6)]
        pts = [(-W / 2, yf, ze), (W / 2, yf, ze)] + right + [(-p[0], p[1], p[2]) for p in right[::-1]]
        # dedupe the apex
        clean = []
        for p in pts:
            if not clean or (Vector(p) - Vector(clean[-1])).length > 1e-4:
                clean.append(p)
        G[wall].prism(clean, (0, 0.45, 0))
        # stone copings on the steps
        cap = s["surround"] or "stone_yel"
        for k in range(steps):
            x_out = W / 2 - k * (W / 2) / steps
            z_top = ze + (k + 1) * rise / steps + 0.35
            wstep = (W / 2) / steps + 0.08
            for sgn in (-1, 1):
                xc = sgn * (x_out - wstep / 2 + 0.04)
                if abs(xc) < 0.3: continue
                G[cap].box((xc, yf + 0.2, z_top + 0.05), (wstep, 0.55, 0.1))
                G["snow"].box((xc, yf + 0.2, z_top + 0.13), (wstep - 0.04, 0.5, 0.06))
        G[cap].box((0, yf + 0.2, zr + 0.65), (0.8, 0.55, 0.12))
        # windows in the gable
        for x in (-W * 0.18, W * 0.18):
            window(x, ze + 0.6, 0.75, 1.15, yf, lit * 0.8, 2, surround=s["surround"], shutters=s["shutters"])
        window(0, ze + rise * 0.5, 0.6, 0.9, yf, lit * 0.5, 2, surround=s["surround"])
        if not LITE:
            G["iron"].beam((0, yf, zr + 0.7), (0, yf, zr + 1.4), 0.03, 0.03)     # finial rod
            G["gilt"].uvsphere((0, yf, zr + 1.45), 0.08, seg=8, rings=5)
        gable_roof_along_y(roof, W - 0.1, yf + 0.45, yb, ze, s["pitch"], over_side=0.3, over_front=0.0)
        G[wall].prism([(W / 2, yb, ze), (-W / 2, yb, ze), (0, yb, zr - 0.05)], (0, -0.3, 0))
        chimney(W * 0.2, yb - 2.5, zr - 1.0, 1.3, wall)
    else:  # eaves to the square, with dormers
        zr = gable_roof_along_x(roof, W, yf, yb, ze, s["pitch"], over=0.45, over_side=0.2)
        # side gables
        for sgn in (-1, 1):
            G[wall].prism([(sgn * W / 2, yf, ze), (sgn * W / 2, yb, ze), (sgn * W / 2, (yf + yb) / 2, zr - 0.05)][:: (1 if sgn > 0 else -1)],
                          (-sgn * 0.3, 0, 0))
        # eaves cornice
        if timber:
            G[s["ti"]].wall_beam((-W / 2 - 0.2, ze + 0.05), (W / 2 + 0.2, ze + 0.05), 0.22, 0.25, yf)
        else:
            G[s["surround"] or "stone_yel"].box((0, yf - 0.12, ze + 0.06), (W + 0.3, 0.3, 0.22))
        gutter_and_pipe(W + 0.3, yf - 0.4, ze - 0.2, W / 2 - 0.2)
        nd = s["dormers"]
        tanp = math.tan(s["pitch"])
        for k in range(nd):
            x = (k - (nd - 1) / 2) * (W / max(nd, 1)) * 0.9
            yb_d = yf + 0.9
            zb = ze + 0.9 * tanp - 0.05
            dormer(x, yb_d, zb, s["pitch"], 1.5, wall if not timber else wall, roof, lit * 0.8)
        chimney(random.choice([-1, 1]) * W * 0.3, (yf + yb) / 2 + 0.8, zr - 0.8, 1.2, wall)
    # windows on side walls left exposed by a gap (exit, church, side street corner)
    for side in open_sides:
        sgn = 1 if side == "right" else -1
        F2 = F @ Matrix.Translation((sgn * W / 2, D / 2, 0)) @ Matrix.Rotation(sgn * math.pi / 2, 4, "Z")
        G.set_frame(F2)
        span = D - 2.0
        ncol = max(1, min(3, int(span / 2.4)))
        xs2 = [(-span / 2 + span * (k + 0.5) / ncol) for k in range(ncol)]
        z = h0
        for f in range(n_up):
            for x2 in xs2:
                window(x2, z + 0.85, 0.8, min(1.3, hf - 1.35), 0.0, lit * 0.8, hf,
                       surround=s["surround"] if not timber else None, shutters=s["shutters"], mullion=False)
            z += hf
        if not s["shop"]:
            window(xs2[0], 1.05, 0.8, 1.3, 0.0, lit * 0.6, h0, surround=s["surround"] if not timber else None)
    G.set_frame(Matrix.Identity(4))
    return ze


GARLANDS = []


def garlands():
    """Fir garlands with warm bulbs swagged over the shopfronts."""
    fir = C.Geo("town_garland", MATS["ti_black"], (1, 1))
    bl = C.Geo("bulbs_town_garlands", MATS["bulb"], (1, 1))
    fir_m = C.solid("fir_garland", (0.03, 0.09, 0.04), rough=0.8)
    fir.mat = fir_m
    for F, W, z in GARLANDS:
        fir.frame = F; bl.frame = F
        n = 3
        for s_ in range(n):
            xa = -W / 2 + 0.3 + (W - 0.6) * s_ / n; xb = -W / 2 + 0.3 + (W - 0.6) * (s_ + 1) / n
            pts = [Vector((xa + (xb - xa) * t / 8, -0.12, z - 0.35 * math.sin(math.pi * t / 8))) for t in range(9)]
            fir.tube(pts, 0.06, tseg=4)
            for t in range(1, 8, 2):
                p = pts[t]
                bl.bulb((p.x, p.y - 0.06, p.z - 0.02), 0.025)
    return fir.finish(col), bl.finish(col)


# ------------------------------------------------------------------ the church (Marktkirche)

def build_church():
    tx, ty = P.CHURCH_POS
    t = math.atan2(ty, tx)
    Rt = math.hypot(tx, ty)
    # local frame: origin at the tower centre, -y faces the square, +x runs along the nave (clockwise)
    F = Matrix.Translation((tx, ty, 0.0)) @ Matrix.Rotation(t - math.pi / 2, 4, "Z")
    G.set_frame(F)
    st = "stone_red"
    TW = 8.0
    TH = 33.0
    # tower shaft in four stages, each a little narrower, with string courses
    stages = [(0, 11, TW), (11, 20, TW - 0.3), (20, 28, TW - 0.6), (28, TH, TW - 0.9)]
    for z0, z1, w in stages:
        G[st].box((0, 0, (z0 + z1) / 2 - (0.4 if z0 == 0 else 0)), (w, w, z1 - z0 + (0.8 if z0 == 0 else 0)), skip_bottom=True)
        G["stone_yel"].box((0, 0, z1 - 0.1), (w + 0.3, w + 0.3, 0.3))
    # corner buttresses at the base
    for sx in (-1, 1):
        for sy in (-1, 1):
            G[st].box((sx * (TW / 2 + 0.3), sy * (TW / 2 - 0.6), 5), (0.7, 1.2, 10), skip_bottom=True)
            G[st].box((sx * (TW / 2 - 0.6), sy * (TW / 2 + 0.3), 5), (1.2, 0.7, 10), skip_bottom=True)
    # portal (pointed) on the square side
    portal = [(-1.3, -TW / 2 - 0.02, 0), (1.3, -TW / 2 - 0.02, 0), (1.3, -TW / 2 - 0.02, 3.2), (0.8, -TW / 2 - 0.02, 4.3), (0, -TW / 2 - 0.02, 4.9),
              (-0.8, -TW / 2 - 0.02, 4.3), (-1.3, -TW / 2 - 0.02, 3.2)]
    G["pw_brown"].poly([(p[0], p[1] - 0.1, p[2]) for p in portal])
    for k, sc in enumerate((1.3, 1.15)):
        G["stone_yel"].prism([(p[0] * sc, p[1] - 0.03 * (k + 1), p[2] * (1 + 0.05 * (2 - k))) for p in portal], (0, 0.03 * (k + 1), 0))
    # windows: lancets on the lower stages, belfry openings with louvres, clocks
    lancet_k = [0]

    def lancet(x, y, zb, w, h, facing, lit=True):
        pts2 = [(-w / 2, 0), (w / 2, 0), (w / 2, h - w * 0.8), (w * 0.3, h - w * 0.22), (0, h), (-w * 0.3, h - w * 0.22), (-w / 2, h - w * 0.8)]
        pts = []
        for px, pz in pts2:
            if facing == "-y": pts.append((x + px, y, zb + pz))
            elif facing == "+y": pts.append((x - px, y, zb + pz))
            elif facing == "-x": pts.append((y, x - px, zb + pz))
            else: pts.append((y, x + px, zb + pz))
        if lit:
            G["window"].poly(pts, uv_rect=stained_rect(lancet_k[0]))
            lancet_k[0] += 1
        else:
            G["dark"].poly(pts)
        if lit and not LITE and w > 1.0:   # stone mullion (the tracery head is painted in the glass)
            nrm = {"-y": Vector((0, -1, 0)), "+y": Vector((0, 1, 0)), "-x": Vector((-1, 0, 0)), "+x": Vector((1, 0, 0))}[facing]
            def P3(px, pz):
                if facing == "-y": return Vector((x + px, y, zb + pz))
                if facing == "+y": return Vector((x - px, y, zb + pz))
                if facing == "-x": return Vector((y, x - px, zb + pz))
                return Vector((y, x + px, zb + pz))
            off = nrm * 0.04
            G["stone_yel"].beam(tuple(P3(0, 0) + off), tuple(P3(0, h - w * 0.55) + off), 0.1, 0.08, up=tuple(nrm), skip_ends=True)
        # stone surround
        if not LITE:
            n = len(pts)
            for i in range(n):
                a, b = Vector(pts[i]), Vector(pts[(i + 1) % n])
                if (b - a).length < 0.05: continue
                nrm = {"-y": (0, -1, 0), "+y": (0, 1, 0), "-x": (-1, 0, 0), "+x": (1, 0, 0)}[facing]
                off = Vector(nrm) * 0.06
                G["stone_yel"].beam(tuple(a + off), tuple(b + off), 0.14, 0.12, up=nrm)
    half = [TW / 2 + 0.02 - 0.15 * k for k in range(4)]     # stage k's face (full width shrinks 0.3 m per stage)
    lancet(0, -half[1] - 0.02, 13, 1.6, 4.2, "-y")
    for face, hw in (("-y", half[3]), ("+y", half[3]), ("-x", half[3]), ("+x", half[3])):
        sgn = -1 if face[0] == "-" else 1
        for dx in (-1.3, 1.3):
            lancet(dx, sgn * (hw + 0.02), 28.8, 1.2, 3.4, face, lit=False)
            if not LITE:  # louvres
                for q in range(6):
                    zq = 29.2 + q * 0.42
                    if face in ("-y", "+y"):
                        G["pw_brown"].box((dx, sgn * (hw + 0.05), zq), (1.1, 0.06, 0.08), rot=(sgn * 0.5, 0, 0))
                    else:
                        G["pw_brown"].box((sgn * (hw + 0.05), dx, zq), (0.06, 1.1, 0.08), rot=(0, -sgn * 0.5, 0))
    for face, hw in (("-y", half[2]), ("+y", half[2]), ("-x", half[2]), ("+x", half[2])):
        sgn = -1 if face[0] == "-" else 1
        if face in ("-y", "+y"):
            loc = (0, sgn * (hw + 0.06), 24.5); rot = (math.pi / 2, 0, 0)
        else:
            loc = (sgn * (hw + 0.06), 0, 24.5); rot = (0, math.pi / 2, 0)
        G["dial"].cyl(loc, 1.35, 1.35, 0.06, seg=32, rot=rot)
        G["gilt"].cyl(loc, 1.5, 1.5, 0.04, seg=32, rot=rot, caps=False)
        # hands at ten to five
        for ang, ln, wd in ((math.radians(150), 0.8, 0.09), (math.radians(-60), 1.15, 0.06)):
            if face in ("-y", "+y"):
                a = Vector((0, sgn * (hw + 0.1), 24.5)); b = a + Vector((math.sin(ang) * ln * (-sgn), 0, math.cos(ang) * ln))
            else:
                a = Vector((sgn * (hw + 0.1), 0, 24.5)); b = a + Vector((0, math.sin(ang) * ln * sgn, math.cos(ang) * ln))
            G["gilt"].beam(tuple(a), tuple(b), wd, 0.03, up=(0, sgn, 0) if face in ("-y", "+y") else (sgn, 0, 0))
    # octagonal spire with gablets and a gilt ball and cross
    sw = TW - 0.9
    zb = TH
    # four gablets (Wimperge) at the base of the spire
    for face in ("-y", "+y", "-x", "+x"):
        sgn = -1 if face[0] == "-" else 1
        if face in ("-y", "+y"):
            pts = [(-sw / 2, sgn * sw / 2, zb), (sw / 2, sgn * sw / 2, zb), (0, sgn * sw / 2, zb + 3.2)]
            if sgn > 0: pts = pts[::-1]
            G[st].prism(pts, (0, -sgn * 1.2, 0))
        else:
            pts = [(sgn * sw / 2, -sw / 2, zb), (sgn * sw / 2, sw / 2, zb), (sgn * sw / 2, 0, zb + 3.2)]
            if sgn < 0: pts = pts[::-1]
            G[st].prism(pts, (-sgn * 1.2, 0, 0))
    spire_h = 24.0
    G["slate"].cyl((0, 0, zb + spire_h / 2), sw / 2 * 1.02, 0.12, spire_h, seg=8, rot=(0, 0, math.pi / 8), bottom=False)
    G["snow"].cyl((0, 0, zb + 3.2), sw / 2 * 1.05, sw / 2 * 0.8, 0.9, seg=8, rot=(0, 0, math.pi / 8), caps=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            G[st].cyl((sx * (sw / 2 - 0.3), sy * (sw / 2 - 0.3), zb + 1.5), 0.35, 0.35, 3.0, seg=6)
            G["slate"].cyl((sx * (sw / 2 - 0.3), sy * (sw / 2 - 0.3), zb + 4.2), 0.42, 0.02, 2.4, seg=6, bottom=False)
    ztop = zb + spire_h
    G["gilt"].uvsphere((0, 0, ztop + 0.3), 0.4, seg=12, rings=8)
    G["gilt"].box((0, 0, ztop + 1.6), (0.12, 0.12, 2.2))
    G["gilt"].box((0, 0, ztop + 2.0), (1.0, 0.12, 0.12))
    # ---- nave: runs along +x from the tower, 30 m, walls 15 m, steep slate roof
    NL, NW, NH = 28.0, 13.0, 13.5
    x0 = TW / 2
    G[st].box((x0 + NL / 2, 0, NH / 2 - 0.4), (NL, NW, NH + 0.8), skip_bottom=True)
    # buttresses and tall windows along both long sides
    nb = 6
    for k in range(nb + 1):
        bx = x0 + 0.8 + k * (NL - 1.6) / nb
        for sgn in (-1, 1):
            G[st].box((bx, sgn * (NW / 2 + 0.6), 4.5), (1.0, 1.2, 9.0), skip_bottom=True)
            G[st].box((bx, sgn * (NW / 2 + 0.35), 10.5), (0.9, 0.7, 3.0))
            G["stone_yel"].box((bx, sgn * (NW / 2 + 0.6), 9.05), (1.1, 1.3, 0.2), rot=(0, 0, 0))
        if k < nb:
            wx = bx + (NL - 1.6) / nb / 2
            for sgn in (-1, 1):
                lancet(wx, sgn * (NW / 2 + 0.02), 3.5, 2.0, 8.5, "-y" if sgn < 0 else "+y")
    # polygonal choir (apse) at the far end
    ax = x0 + NL
    n_ap = 5
    ap = []
    for k in range(n_ap + 1):
        a = -math.pi / 2 + math.pi * k / n_ap
        ap.append((ax + (NW / 2 - 0.5) * math.cos(a) * 0.9, (NW / 2 - 0.5) * math.sin(a), 0))
    G[st].prism([(p[0], p[1], -0.4) for p in ap], (0, 0, NH - 0.6 + 0.4))
    # nave roof (ridge along x) and apse roof
    pitch = math.radians(58)
    zr = gable_roof_along_x("slate", NL, -NW / 2, NW / 2, NH, pitch, over=0.6, over_side=0.4, xc=x0 + NL / 2)
    G[st].prism([(x0 + NL, -NW / 2, NH), (x0 + NL, NW / 2, NH), (x0 + NL, 0, zr - 0.2)], (-0.4, 0, 0))
    G[st].prism([(x0 + 0.01, NW / 2, NH), (x0 + 0.01, -NW / 2, NH), (x0 + 0.01, 0, zr - 0.2)], (0.4, 0, 0))
    # apse roof: fan of triangles from the ridge end
    apex = Vector((ax, 0, zr))
    for k in range(n_ap):
        a0 = Vector(ap[k]) + Vector((0, 0, NH - 0.3)); a1 = Vector(ap[k + 1]) + Vector((0, 0, NH - 0.3))
        out0 = Vector((a0.x - ax, a0.y, 0)).normalized() * 0.5; out1 = Vector((a1.x - ax, a1.y, 0)).normalized() * 0.5
        tri = [tuple(a0 + out0), tuple(a1 + out1), tuple(apex)]
        nn = (Vector(tri[1]) - Vector(tri[0])).cross(Vector(tri[2]) - Vector(tri[0]))
        if nn.z < 0: tri = tri[::-1]
        G["slate"].poly(tri)
        G["snow"].poly([tuple(Vector(p) + Vector((0, 0, 0.12))) for p in tri])
    # three slate-hung dormers on the square side of the nave roof: they break up the big slate plane
    # and give its courses a scale
    tanp = math.tan(pitch)
    for fx in (0.22, 0.47, 0.8):
        dormer(x0 + NL * fx, -NW / 2 + 2.2, NH + 2.2 * tanp - 0.05, pitch, 1.4, "slate", "slate", 0.35)
    # ridge turret (Dachreiter) with a small copper spire
    G["pw_brown"].box((x0 + NL * 0.6, 0, zr + 1.2), (1.4, 1.4, 2.4))
    G["copper"].cyl((x0 + NL * 0.6, 0, zr + 4.2), 1.0, 0.05, 3.6, seg=8, rot=(0, 0, math.pi / 8), bottom=False)
    G["gilt"].uvsphere((x0 + NL * 0.6, 0, zr + 6.1), 0.18, seg=8, rings=5)
    # church door on the nave side facing the square
    dxp = x0 + NL * 0.45
    portal2 = [(dxp - 1.1, -NW / 2 - 0.03, 0), (dxp + 1.1, -NW / 2 - 0.03, 0), (dxp + 1.1, -NW / 2 - 0.03, 2.8),
               (dxp, -NW / 2 - 0.03, 4.0), (dxp - 1.1, -NW / 2 - 0.03, 2.8)]
    G["pw_brown"].poly([(p[0], p[1] - 0.1, p[2]) for p in portal2])
    G["stone_yel"].prism([(p[0] + (p[0] - dxp) * 0.25, p[1] - 0.05, p[2] * 1.1) for p in portal2], (0, 0.05, 0))
    G.set_frame(Matrix.Identity(4))
    # two floodlights at the tower foot on the square side, as German churches are lit at night
    for k, sx in enumerate((-3.2, 3.2)):
        C.empty(f"light_church_{k}", F @ Vector((sx, -TW / 2 - 3.5, 0.4)), col)
    # angular extent of the church block (for skipping houses)
    corners = [F @ Vector((-TW / 2 - 1, -TW / 2, 0)), F @ Vector((x0 + NL + NW / 2, -NW / 2, 0))]
    angs = [math.atan2(c.y, c.x) for c in corners]
    return min(angs), max(angs)


# ------------------------------------------------------------------ place the ring
t0_church, t1_church = build_church()
C.log("church spans", math.degrees(t0_church), math.degrees(t1_church))


def blocked(t, w):
    r = P.house_r(t)
    half = w / 2 / r
    for dt in (-half, 0, half):
        tt = (t + dt) % (2 * math.pi)
        if P.exit_at(tt, r, pad=0.3) >= 0:
            return True
        a = math.atan2(math.sin(tt), math.cos(tt))
        if t0_church - 0.02 < a < t1_church + 0.02:
            return True
    return False


houses = []
ring = []
t = math.radians(0.5)
prev = None
idx = 0
slots = []
while t < 2 * math.pi - 0.01:
    W = random.choice([6.2, 6.8, 7.4, 8.0, 8.6, 9.4, 10.2]) if not (prev and prev["W"] > 9) else random.uniform(6.0, 7.5)
    r = P.house_r(t)
    dth = W / r
    tm = t + dth / 2
    if blocked(tm, W):
        t += 0.4 / r
        continue
    s_ = make_spec(prev, W, idx)
    slots.append([t, t + dth, tm, s_])
    prev = s_
    idx += 1
    t += dth + 0.02 / r
for i, (ta, tb, tm, s_) in enumerate(slots):
    gap_before = i == 0 or ta - slots[i - 1][1] > 0.01
    gap_after = i == len(slots) - 1 or slots[i + 1][0] - tb > 0.01
    open_sides = (["right"] if gap_before else []) + (["left"] if gap_after else [])
    setback = random.uniform(-0.25, 0.35)
    rr = P.house_r(tm) + setback
    F = Matrix.Translation((rr * math.cos(tm), rr * math.sin(tm), 0.0)) @ Matrix.Rotation(tm - math.pi / 2, 4, "Z")
    ze_i = build_house(F, s_, i, open_sides)
    houses.append((tm, s_))
    ring.append(dict(F=F, W=s_["W"], D=s_["D"], ze=ze_i, tint=s_["tint"], gap_after="left" in open_sides))
C.log("ring houses", len(houses), "tris so far", G.tris())


def wedge_fillers():
    """Houses are rectangles on a ring, so a wedge opens between neighbours toward the back (about
    1.8 m wide at 11 m depth), visible from the Ferris wheel.  Fill each wedge with a back range:
    plastered walls up to just under the lower eave and a flat zinc roof with snow on it."""
    n = 0
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if a["gap_after"]:
            continue
        Fa, Fb = a["F"], b["F"]
        y0 = 1.0
        pts = [Fa @ Vector((-a["W"] / 2 + 0.06, y0, 0)), Fa @ Vector((-a["W"] / 2 + 0.06, a["D"] - 0.05, 0)),
               Fb @ Vector((b["W"] / 2 - 0.06, b["D"] - 0.05, 0)), Fb @ Vector((b["W"] / 2 - 0.06, y0, 0))]
        area = sum(p.x * q.y - q.x * p.y for p, q in zip(pts, pts[1:] + pts[:1])) / 2
        if area < 0:
            pts = pts[::-1]
        if abs(area) < 0.3:
            continue
        h = min(a["ze"], b["ze"]) - 0.35
        G.set_frame(Matrix.Identity(4))
        G["pl_" + a["tint"]].prism([(p.x, p.y, -0.3) for p in pts], (0, 0, h + 0.3), caps=False)
        G["zinc"].poly([(p.x, p.y, h) for p in pts])
        c = sum(pts, Vector()) / 4
        G["snow"].poly([(c.x + (p.x - c.x) * 0.9, c.y + (p.y - c.y) * 0.9, h + 0.05) for p in pts])
        n += 1
    C.log("wedge fillers", n)


wedge_fillers()

# ------------------------------------------------------------------ houses down the side streets (simpler)


def simple_house(F, W, D, floors, tint, roof, lit, eaves):
    G.set_frame(F)
    wall = "pl_" + tint
    h = 3.4 + (floors - 1) * 2.9
    G[wall].box((0, D / 2, h / 2 - 0.3), (W, D, h + 0.6), skip_bottom=True)
    n = max(2, int(W / 1.8))
    xs = np.linspace(-W / 2 + W / (2 * n), W / 2 - W / (2 * n), n)
    for f in range(floors):
        zb = 1.0 + f * 2.9 + (0.3 if f else 0)
        for x in xs:
            c = pick_cell(lit)
            G["window"].quad_rect((x, -0.01, zb + 0.65), 0.85, 1.3, "-y", uv_rect=cell_rect(c))
            if not LITE:
                G["pw_frame"].box((x, -0.05, zb - 0.03), (1.0, 0.1, 0.06), skip_back=True)
    if eaves:
        gable_roof_along_x(roof, W, 0, D, h, math.radians(48), over=0.4, over_side=0.15)
        for sgn in (-1, 1):
            zr = h + D / 2 * math.tan(math.radians(48))
            G[wall].prism([(sgn * W / 2, 0, h), (sgn * W / 2, D, h), (sgn * W / 2, D / 2, zr - 0.05)][:: (1 if sgn > 0 else -1)], (-sgn * 0.3, 0, 0))
    else:
        zr = gable_roof_along_y(roof, W, 0, D, h, math.radians(55), over_side=0.3, over_front=0.3)
        G[wall].prism([(-W / 2, 0, h), (W / 2, 0, h), (0, 0, zr - 0.05)], (0, 0.3, 0))
        window(0, h + 0.5, 0.7, 1.0, 0, lit * 0.6, 2, mullion=False)
    G.set_frame(Matrix.Identity(4))


tints = list(PLASTER_TINTS)
side_prev = None
for deg, w in P.EXITS:
    te = math.radians(deg)
    r0 = P.house_r(te)
    radial = Vector((math.cos(te), math.sin(te), 0)); tang = Vector((-math.sin(te), math.cos(te), 0))
    for side in (-1, 1):
        d = r0 + 1.0
        k = 0
        while d < r0 + 26 and k < (2 if not LITE else 2):
            W = random.uniform(6.5, 9.5); D = random.uniform(8, 10)
            centre = radial * (d + W / 2) + tang * side * (w / 2 + 0.2)
            face = -side * tang       # the house faces the side street
            F = Matrix.Translation(centre) @ Matrix.Rotation(math.atan2(face.x, -face.y), 4, "Z")
            if k == 0 and not LITE:
                sp = make_spec(side_prev, W, idx); sp["D"] = D; sp["shop"] = sp["shop"] and random.random() < 0.5
                xw = Vector((F[0][0], F[1][0], 0))
                toward_square = "right" if xw.dot(radial) < 0 else "left"
                build_house(F, sp, idx, (toward_square,)); idx += 1; side_prev = sp
            else:
                simple_house(F, W, D, random.choice([2, 3, 3, 4]), random.choice(tints), random.choice(["roof_red", "roof_brown", "slate"]),
                             random.choice([0.3, 0.5, 0.7]), random.random() < 0.5)
            d += W + 0.1
            k += 1
    # a house closing the view at the end of the street
    far = radial * (r0 + 30)
    F = Matrix.Translation(far) @ Matrix.Rotation(te - math.pi / 2, 4, "Z")
    sp = make_spec(side_prev, 9.0, idx); sp["shop"] = False; sp["upper"] = min(sp["upper"], 2)
    build_house(F, sp, idx); idx += 1; side_prev = sp
C.log("with side streets, tris", G.tris())

# ------------------------------------------------------------------ skyline: roofs of the town beyond the ring
G_RING = G
G = GS = C.GeoSet("sky", MATS, UVM)      # far roofs go in their own meshes (per-vertex occlusion, no atlas texels)
if not LITE:
    for k in range(48):
        tt = 2 * math.pi * k / 48 + random.uniform(-0.03, 0.03)
        r = random.uniform(70, 88)
        W = random.uniform(7, 11); D = random.uniform(8, 11); h = random.uniform(8, 13)
        F = Matrix.Translation((r * math.cos(tt), r * math.sin(tt), 0)) @ Matrix.Rotation(tt - math.pi / 2 + random.uniform(-0.2, 0.2), 4, "Z")
        G.set_frame(F)
        G["pl_" + random.choice(tints)].box((0, D / 2, h / 2), (W, D, h), skip_bottom=True)
        if random.random() < 0.6:
            for x in (-W / 4, W / 4):
                G["window"].quad_rect((x, -0.01, h - 2.2), 0.8, 1.2, "-y", uv_rect=cell_rect(pick_cell(0.4)))
        roof = random.choice(["roof_red", "roof_brown", "slate"])
        if random.random() < 0.5:
            gable_roof_along_x(roof, W, 0, D, h, math.radians(50), over=0.3, over_side=0.1)
        else:
            zr = gable_roof_along_y(roof, W, 0, D, h, math.radians(55), over_side=0.3, over_front=0.2)
            G["pl_" + random.choice(tints)].prism([(-W / 2, 0, h), (W / 2, 0, h), (0, 0, zr - 0.05)], (0, 0.3, 0))
    G.set_frame(Matrix.Identity(4))
G = G_RING

# ------------------------------------------------------------------ finish
sign_texture()
fir_ob, gb_ob = garlands() if not LITE else (None, None)
# wall lantern bulbs
wl = C.Geo("bulbs_town_lanterns", MATS["bulb"], (1, 1))
for x, y, z, F in WALL_BULBS:
    wl.frame = F
    for k in range(4):
        pass
    wl.bulb((x, y, z), 0.09, stretch=1.6, sides=6)
wl_ob = wl.finish(col)
objs = G.finish(col)
for k, ob in GS.finish(col).items():
    if k == "snow":
        ob.name = "snow_skyline"; ob.data.name = "snow_skyline"
    elif k == "window":
        ob.name = "town_windows_skyline"
# snow must be its own node named snow_*: rename
for k, ob in objs.items():
    if k == "snow":
        ob.name = "snow_roofs"; ob.data.name = "snow_roofs"
    elif k == "window":
        ob.name = "town_windows"
exported = list(col.objects)
tris = C.count_tris(exported)
C.log("TOWN TRIANGLES (before AO)", tris)
if os.environ.get("STATS_ONLY"):
    by = sorted(((o.name, C.count_tris([o])) for o in exported), key=lambda kv: -kv[1])
    C.log("BREAKDOWN", by[:14])
    sys.exit(0)

# ------------------------------------------------------------------ ambient occlusion
AO_RES = 512 if LITE else 2048
STRIP = 0.975                    # u >= STRIP: the ramp for per-vertex occlusion
AO_PATH = os.path.join(C.tex_dir("town"), f"town_ao{'_lite' if LITE else ''}.png")
scene.world = bpy.data.worlds.new("ao_world")
gme = bpy.data.meshes.new("ao_ground")          # the square and streets as an occluder (not exported)
gme.from_pydata([(-140, -140, 0.06), (140, -140, 0.06), (140, 140, 0.06), (-140, 140, 0.06)], [], [(0, 1, 2, 3)])
gob = bpy.data.objects.new("ao_ground", gme); scene.collection.objects.link(gob)
meshes = [o for o in exported if o.type == "MESH"]
ATLAS_KEYS = tuple("town_" + k for k in MATS if k.startswith(("pl_", "stone_", "roof_")) or k == "slate")
atlas = [o for o in meshes if o.name in ATLAS_KEYS]
skip = [o for o in meshes if o.name.startswith("bulbs_") or o.name.startswith("town_windows")]
small = [o for o in meshes if o not in atlas and o not in skip]
for o in skip:
    o.hide_render = True


def seen(p):
    """Faces worth atlas texels: not the floor slabs hidden inside the stacked storeys, and not the
    back walls of the ring that face away from the square (nobody walks behind the houses)."""
    n, c = p.normal, p.center
    if abs(n.z) > 0.99 and p.area > 3.0 and c.z > 0.5:
        return False
    if abs(n.z) < 0.3:
        r = math.hypot(c.x, c.y)
        if r > 45 and (n.x * c.x + n.y * c.y) / r > 0.8:
            return False
    return True


# per-corner occlusion for everything (small parts use it directly, and small faces of the atlas meshes too)
vao = C.bake_vertex_ao(atlas + small, samples=48, distance=1.2, lift=0.22)
for o in small:
    C.ramp_uv(o, vao[o.name], STRIP + 0.006, 0.996)
# atlas texels only for large visible faces: walls, gables, roofs, chimneys, the church's walls
C.lightmap_atlas(atlas, reserve_u=1 - STRIP, margin=0.003 if not LITE else 0.006,
                 face_filter=lambda p: p.area > 1.2 and seen(p), ramp=vao)
ao_img = C.bake_ao(atlas, "town_ao", AO_RES, AO_PATH, samples=48, distance=2.5, post=False,
                   margin=8 if not LITE else 4)
C.finish_ao_image(ao_img, AO_PATH, lift=0.2, strip=(STRIP, "ramp"))     # pass 3: more contrast (was 0.3)
for o in atlas + small:
    for m in o.data.materials:
        C.attach_ao(m, ao_img)
for o in skip:
    o.hide_render = False
bpy.data.objects.remove(gob)

C.log("TOWN TRIANGLES", tris, "lite" if LITE else "full")
by = sorted(((o.name, C.count_tris([o])) for o in exported), key=lambda kv: -kv[1])
C.log("BREAKDOWN", by[:14])
if os.environ.get("STATS_ONLY"):
    sys.exit(0)
name = "town.lite" if LITE else "town"
raw = C.export_glb(exported, os.path.join(OUT, f"{name}_raw.glb"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"))
final = C.optimize(raw, os.path.join(C.MODELS, f"{name}.glb"), tex_size=512 if LITE else 1024)
st = C.glb_stats(final)
C.log("FINAL", name, "tris", st["tris"], "bytes", st["size"])
C.log("NODES", [n for n in st["nodes"] if n.startswith(("light_", "bulbs_", "snow_"))])
C.log("MATERIALS", st["materials"])
