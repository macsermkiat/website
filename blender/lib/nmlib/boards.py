"""Writing surfaces for the in-market text (docs/adr/0003, BUILD.md `write_` / `cam_read_`).

A board is built in its own face frame F (a 4x4 matrix): local +X runs right along the
writing, +Y up the writing, +Z out of the face toward the reader. `face_frame()` makes one
from a centre, a yaw and a lean. The blank writing area is its own mesh object
`write_<name>` (one flat quad, UVs 0-1 over the area with +V up the text, material
`chalk_slate` or `paper_card`), never merged with anything; the engine draws the text on it.

    F = boards.face_frame((0.98, -0.5, 1.83), yaw=0.0)
    out = boards.chalkboard("about", F, 1.10, 0.80, frame=frame_part, back=wood_part,
                            iron=iron_part, chalk=chalk_part)
    boards.read_camera("about", F, 1.10, 0.80)      # cam_read_about + cam_read_about_target

The slate texture is a small numpy image (no bake) named `kit_slate_color`, so the stall
pipeline's shared-kit externalising moves it to `deco_kit_slate_color.webp` and every board in
the market shares one file.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from . import export, state

SLATE_VERSION = "s2"
SLATE_RES = 512
# desktop camera (site/src/main.js): 42 degree vertical field of view; reading views are 16:9
READ_FOV_V = 42.0
READ_ASPECT = 16 / 9


# ------------------------------------------------------------------ frames
def face_frame(center, yaw=0.0, lean=0.0):
    """Face frame of a board centred at `center` (Blender coordinates). yaw (radians, about +Z)
    turns the face from -Y toward +X for positive values; lean tips the top back (radians)."""
    return (Matrix.Translation(Vector(center)) @ Euler((0, 0, yaw)).to_matrix().to_4x4()
            @ Euler((-lean, 0, 0)).to_matrix().to_4x4() @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4())


def at(F, x, y, z=0.0):
    """World point of local (x, y, z) in face frame F."""
    return F @ Vector((x, y, z))


def frame_axes(F):
    R = F.to_3x3()
    return R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))


def local_box(part, F, cx, cy, cz, sx, sy, sz, **kw):
    """Box centred at local (cx, cy, cz) with local size (sx, sy, sz)."""
    part.mbox(F @ Matrix.Translation((cx, cy, cz)), (sx, sy, sz), **kw)


# ------------------------------------------------------------------ materials
def _slate_pixels(res=SLATE_RES, seed=5):
    """A well-used blackboard, blank: dark green-black slate, a cloudy haze of old chalk, broad
    eraser wipes (cleaner centres, chalk pushed to their edges), faint scratches and dust
    settling toward the chalk tray. Kept dark (sRGB below ~70) so drawn chalk reads on it."""
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) / res      # y = 0 at the top row
    base = np.array([0.020, 0.027, 0.024], np.float32)           # linear slate
    haze = gaussian_filter(rng.normal(0, 1, (res, res)).astype(np.float32), res / 14)
    haze = (haze - haze.min()) / (np.ptp(haze) + 1e-6)
    fine = gaussian_filter(rng.normal(0, 1, (res, res)).astype(np.float32), 1.6)
    fine = fine / (np.abs(fine).max() + 1e-6)
    chalk = 0.010 + 0.022 * haze ** 1.6 + 0.003 * fine
    # eraser wipes: long, gently bowed swaths at slight angles; inside cleaner, the edges keep
    # a chalky rim
    for _ in range(9):
        yc = rng.uniform(0.06, 0.94)
        hw = rng.uniform(0.04, 0.085)
        x0, x1 = sorted(rng.uniform(-0.2, 1.2, 2))
        if x1 - x0 < 0.45:
            x1 = min(1.25, x0 + 0.45)
        xm = (x0 + x1) / 2
        bow, tilt = rng.uniform(-0.25, 0.25), rng.uniform(-0.06, 0.06)
        d = np.abs(y - (yc + bow * (x - xm) ** 2 + tilt * (x - xm))) / hw
        along = np.clip((x - x0) / 0.08, 0, 1) * np.clip((x1 - x) / 0.08, 0, 1)
        inside = np.clip(1.0 - d, 0, 1) ** 0.5 * along
        rim = np.exp(-((d - 1.0) / 0.22) ** 2) * along
        chalk = chalk * (1 - 0.5 * inside) + 0.008 * rim
    # faint scratches
    img = np.zeros((res, res), np.float32)
    for _ in range(60):
        cx, cy = rng.uniform(0, res, 2)
        ang = rng.uniform(-0.5, 0.5) if rng.random() < 0.7 else rng.uniform(0, 3.14)
        L = rng.uniform(res * 0.03, res * 0.18)
        t = np.linspace(-L / 2, L / 2, int(L))
        px = np.clip((cx + t * np.cos(ang)).astype(int), 0, res - 1)
        py = np.clip((cy + t * np.sin(ang)).astype(int), 0, res - 1)
        img[py, px] += rng.uniform(0.3, 1.0)
    chalk += 0.010 * np.clip(gaussian_filter(img, 0.7), 0, 1.5)
    # dust settling toward the tray (bottom rows)
    chalk += 0.014 * np.clip((y - 0.86) / 0.14, 0, 1) ** 2 * (0.6 + 0.4 * haze)
    col = base[None, None, :] + chalk[..., None] * np.array([0.95, 1.0, 0.97], np.float32)
    return np.clip(col, 0, 1)


def _save_image(name, rgb):
    """Write a linear RGB array as an sRGB PNG in the kit cache, stamped with SLATE_VERSION."""
    path = os.path.join(state.KIT_DIR, f"{name}.png")
    stamp = path + ".version"
    if True:
        os.makedirs(state.KIT_DIR, exist_ok=True)
        res = rgb.shape[0]
        img = bpy.data.images.new(f"{name}_tmp", res, res)
        img.colorspace_settings.name = "sRGB"
        srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
        px = np.ones((res, res, 4), np.float32)
        px[..., :3] = srgb[::-1]                 # Blender rows run bottom-up
        img.pixels.foreach_set(px.ravel())
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        bpy.data.images.remove(img)
        with open(stamp, "w") as f:
            f.write(SLATE_VERSION)
    return path


def slate_material():
    """Material `chalk_slate`: base colour = the shared `kit_slate_color` image, roughness 0.9,
    no normal map, no vertex colour, no AO (a writing surface stays plain)."""
    m = bpy.data.materials.get("chalk_slate")
    if m is not None:
        return m
    path = os.path.join(state.KIT_DIR, "kit_slate_color.png")
    stamp = path + ".version"
    if not (os.path.exists(path) and os.path.exists(stamp) and open(stamp).read().strip() == SLATE_VERSION):
        _save_image("kit_slate_color", _slate_pixels())
    m = bpy.data.materials.new("chalk_slate")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = bpy.data.images.get("kit_slate_color") or bpy.data.images.load(path)
    img.name = "kit_slate_color"
    img.colorspace_settings.name = "sRGB"
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(uv.outputs[0], tex.inputs[0])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def card_material():
    """Material `paper_card`: plain warm card (flat values) for paper or card writing surfaces."""
    m = bpy.data.materials.get("paper_card")
    if m is not None:
        return m
    m = bpy.data.materials.new("paper_card")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.72, 0.66, 0.53, 1)
    b.inputs["Roughness"].default_value = 0.85
    return m


SURFACES = {"slate": slate_material, "card": card_material}


# ------------------------------------------------------------------ the writing surface
def write_surface(name, F, w, h, z=0.0, surface="slate"):
    """The blank writing area: object `write_<name>`, one flat quad of w x h metres centred on
    the face frame's origin (pushed `z` along the face normal), UVs 0-1 across it with +V up
    the text. Returns the object. It is never merged with other parts."""
    full = name if name.startswith("write_") else f"write_{name}"
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    me = bpy.data.meshes.new(full)
    me.from_pydata([tuple(F @ Vector((x, y, z))) for x, y in pts], [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", [c for t in uvs for c in t])
    me.update()
    ob = bpy.data.objects.new(full, me)
    state.export_collection().objects.link(ob)
    if ob.name != full:
        raise RuntimeError(f"name clash: wanted {full}, got {ob.name}")
    me.materials.append(SURFACES[surface]())
    ob["nm_mat"] = f"write_{surface}"
    return ob


def read_distance(w, h, fill=0.88, fov_v=READ_FOV_V, aspect=READ_ASPECT):
    """Distance at which a w x h area fills `fill` of a 16:9 frame on its limiting axis."""
    t = math.tan(math.radians(fov_v) / 2)
    return max(h / (fill * 2 * t), w / (fill * 2 * t * aspect))


def read_camera(name, F, w, h, fill=0.76, lift=0.06, side=0.0, z=0.0, fov_v=READ_FOV_V):
    """Empties `cam_read_<name>` (looking at its target, -Z forward like cam_view) and
    `cam_read_<name>_target` on the writing area's centre. The camera stands on the face
    normal at read_distance() (default: the writing area fills 76% of the frame height, so the
    frame, tray and crest of the board stay in the picture); `lift` raises it (metres) for a slight downward look, `side`
    slides it along the face's X. Returns (camera position, target position)."""
    t = at(F, 0, 0, z)
    d = read_distance(w, h, fill, fov_v)
    ex, ey, ez = frame_axes(F)
    p = t + ez * d + Vector((0, 0, lift)) + ex * side
    base = name[len("write_"):] if name.startswith("write_") else name
    export.empty(f"cam_read_{base}_target", tuple(t))
    export.empty(f"cam_read_{base}", tuple(p), look_at=tuple(t))
    return p, t


# ------------------------------------------------------------------ a framed chalkboard
def chalkboard(name, F, w, h, frame, back, chalk=None, iron=None, rail=0.065, depth=0.034,
               tray=True, frame_band=None, frame_tint="walnut", bead=None, nails=True):
    """A framed blackboard around the writing area `write_<name>` (w x h, at F's origin).

    frame: Part for the four rails and the tray (wood kit, or a paint Part with frame_band).
    back: wood Part for the backing board (seen from behind). chalk: optional Part
    ('fabric_white') for chalk sticks and the felt of the eraser on the tray. iron: optional
    Part for nail heads and screw eyes. bead: optional (Part, band) for a thin painted inner
    bead (e.g. gold on red). Rails get a little irregularity (length, twist, tint) so the frame
    is visibly hand-made. Returns a dict: write (object), outer (W, H), top (local y of the top
    edge), eyes (two local points on the top rail for hanging)."""
    R = state.rng
    lite = state.lite()
    W, H = w + 2 * rail, h + 2 * rail
    kw = dict(band=frame_band) if frame_band else dict(tint=frame_tint)
    fz = depth / 2 - 0.006                                   # rails stand proud of the slate
    # top and bottom rails run the full width; stiles sit between them (butt joints)
    for sgn in (1, -1):
        local_box(frame, F, R.uniform(-0.004, 0.004), sgn * (h / 2 + rail / 2), fz,
                  W + R.uniform(-0.006, 0.01), rail, depth, grain=0, var=0.1, **kw)
        local_box(frame, F, sgn * (w / 2 + rail / 2), 0, fz + R.uniform(-0.002, 0.002),
                  rail * R.uniform(0.94, 1.0), h, depth * 0.94, grain=1, var=0.1, **kw)
    if bead is not None:
        bp, band = bead
        for sgn in (1, -1):
            local_box(bp, F, 0, sgn * (h / 2 + 0.006), depth - 0.004, w + 0.012, 0.010, 0.006, grain=0, band=band)
            local_box(bp, F, sgn * (w / 2 + 0.006), 0, depth - 0.004, 0.010, h, 0.006, grain=1, band=band)
    # backing board behind the slate (closes the back; seen from inside the hut)
    local_box(back, F, 0, 0, -0.012, W - 0.02, H - 0.02, 0.016, grain=1, tint="dark", var=0.05, bevel=0)
    # slate panel: the write quad lies 2 mm in front of the backing, inside the rails
    write = write_surface(name, F, w, h, z=-0.002)
    if nails and iron is not None and not lite:
        for sx in (-1, 1):
            for sy in (-1, 1):
                for k in (0.33, 0.67):
                    p = at(F, sx * (w / 2 + rail * k), sy * (h / 2 + rail * 0.5), depth - 0.004)
                    iron.cyl(p, 0.006, 0.005, 0.004, seg=6, rot=_face_rot(F), var=0.2)
    eyes = [(-W * 0.36, H / 2), (W * 0.36, H / 2)]
    if tray:
        ty = -H / 2 - 0.006
        local_box(frame, F, 0, ty, 0.03, W * 0.94, 0.02, 0.075, grain=0, var=0.08, **kw)     # shelf
        local_box(frame, F, 0, ty + 0.014, 0.064, W * 0.94, 0.012, 0.008, grain=0, var=0.08, **kw)  # lip
        if chalk is not None:
            for i, (x, ln) in enumerate(((-w * 0.30, 0.07), (-w * 0.24, 0.045), (w * 0.12, 0.06))):
                p = at(F, x, ty + 0.018, 0.035 + 0.008 * (i % 2))
                rot = (F.to_3x3() @ Euler((0, math.pi / 2, R.uniform(-0.3, 0.3))).to_matrix()).to_euler()
                chalk.cyl(p, 0.0055, 0.0055, ln, seg=6 if lite else 8, rot=rot, var=0.05)
            # felt eraser on a wooden back
            local_box(chalk, F, w * 0.3, ty + 0.022, 0.036, 0.13, 0.022, 0.05, bevel=0.004, var=0.02,
                      tint=(0.30, 0.27, 0.22))
            local_box(back, F, w * 0.3, ty + 0.045, 0.036, 0.125, 0.024, 0.046, grain=0, tint="honey")
    if iron is not None:
        for ex, ey in eyes:
            p = at(F, ex, ey + 0.022, 0.0)
            iron.torus(p, 0.016, 0.0035, seg=8 if lite else 12, tseg=4,
                       rot=(F.to_3x3() @ Euler((0, 0, 0)).to_matrix()).to_euler())
    return {"write": write, "outer": (W, H), "top": H / 2, "eyes": eyes, "F": F}


def _face_rot(F):
    """Euler that turns a +Z cylinder to the face normal of F."""
    return F.to_3x3().to_euler()


def chain(iron, a, b, link=0.035, wire=0.0035):
    """Hanging chain from a to b (straight; links alternate by 90 degrees). Lite: a thin rod."""
    a, b = Vector(a), Vector(b)
    d = b - a
    if state.lite():
        iron.tube([a, b], 0.004, tseg=3)
        return
    n = max(2, int(d.length / (link * 0.78)))
    q = d.normalized().to_track_quat('Y', 'Z').to_matrix().to_4x4()
    for i in range(n):
        p = a + d * ((i + 0.5) / n)
        M = Matrix.Translation(p) @ q @ Euler((0, (i % 2) * math.pi / 2, 0)).to_matrix().to_4x4()
        _link(iron, M, link, wire)


def _link(iron, M, link, wire, seg=8, tseg=3):
    """One oval chain link, long along local Y, lying in the local XY plane, placed by M."""
    import bmesh
    bm = bmesh.new()
    R, r = link / 2, wire
    rings = []
    for i in range(seg):
        ang = 2 * math.pi * i / seg
        c = Vector((0.62 * R * math.cos(ang), R * math.sin(ang), 0))
        nrm = Vector((math.cos(ang), math.sin(ang), 0))
        rings.append([bm.verts.new(c + nrm * (r * math.cos(2 * math.pi * j / tseg))
                                   + Vector((0, 0, r * math.sin(2 * math.pi * j / tseg))))
                      for j in range(tseg)])
    for i in range(seg):
        r0, r1 = rings[i], rings[(i + 1) % seg]
        for j in range(tseg):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % tseg], r0[(j + 1) % tseg]))
    iron.from_bmesh(bm, M, grain=1, var=0.1)


# ------------------------------------------------------------------ a standing barrel
def barrel(staves, hoops, center, height=0.92, r_end=0.27, r_belly=0.32, n=None, rings=None,
           lid=True, hoop_z=(0.08, 0.27, 0.65, 0.84), tints=("oak", "oak", "honey", "dark")):
    """A whole standing barrel of separate staves (small gaps) with iron hoops and a head of
    boards. staves: wood Part; hoops: iron Part. Lite: fewer staves and rings."""
    lite = state.lite()
    n = n or (10 if lite else 16)
    rings = rings or (4 if lite else 7)
    cx, cy, z0 = center
    gap = 0.008
    for k in range(n):
        t0 = 2 * math.pi * k / n
        t1 = 2 * math.pi * (k + 1) / n
        ring_pts = []
        for i in range(rings + 1):
            z = z0 + height * i / rings
            r = r_end + (r_belly - r_end) * math.sin(math.pi * i / rings)
            ga = gap / r / 2
            ring_pts.append([(cx + r * math.cos(t), cy + r * math.sin(t), z)
                             for t in (t0 + ga, (t0 + t1) / 2, t1 - ga)])
        staves.loft(ring_pts, closed=False, grain=2, smooth=False, tint=state.rng.choice(tints), var=0.12)
    for hz in hoop_z:
        r = r_end + (r_belly - r_end) * math.sin(math.pi * hz / height) + 0.005
        hoops.torus((cx, cy, z0 + hz), r, 0.008, seg=10 if lite else 16, tseg=4)
    if lid:
        nb = 4
        for i in range(nb):
            yy = -r_end + (i + 0.5) * 2 * r_end / nb
            half = math.sqrt(max(r_end ** 2 - yy ** 2, 0.0)) * 0.98
            staves.box((cx, cy + yy, z0 + height - 0.04), (2 * half, 2 * r_end / nb - 0.006, 0.025),
                       grain=0, tint="oak", var=0.1)


# ------------------------------------------------------------------ a small hanging lantern
def lantern(iron, glass, top, size=0.1, yaw=0.0):
    """A small square iron lantern hanging from the point `top` (its ring): ring, pyramid hood,
    four corner bars, a base, and a glowing glass body (glass: a 'lamp_glass' Part, which is
    emissive, so the lantern glows in the browser too; it lights nothing there). Returns the
    centre of the glass, where a preview may put a point light."""
    t = Vector(top)
    Rz = Euler((0, 0, yaw)).to_matrix()
    s = size
    iron.torus(t + Vector((0, 0, -0.018)), 0.016, 0.0035, seg=8, tseg=4, rot=(math.pi / 2, 0, yaw))
    hood_z = t.z - 0.034 - s * 0.25
    iron.cyl((t.x, t.y, hood_z), s * 0.78, 0.012, s * 0.5, seg=4, rot=(0, 0, yaw + math.pi / 4))
    body_c = Vector((t.x, t.y, hood_z - s * 0.25 - s * 0.62))
    for dx in (-1, 1):
        for dy in (-1, 1):
            off = Rz @ Vector((dx * s * 0.47, dy * s * 0.47, 0))
            iron.box(body_c + off, (0.009, 0.009, s * 1.24), rot=(0, 0, yaw), bevel=0)
    iron.cyl(body_c + Vector((0, 0, -s * 0.64)), s * 0.62, s * 0.7, s * 0.08, seg=4, rot=(0, 0, yaw + math.pi / 4))
    glass.box(body_c, (s * 0.9, s * 0.9, s * 1.2), rot=(0, 0, yaw), bevel=0)
    return body_c


# ------------------------------------------------------------------ a small card on an easel
def easel_card(name, F, w, h, frame, back, clip=None, base_z=None, rail=0.022, depth=0.016,
               leg_angle=24.0, surface="card", tint="walnut"):
    """A small framed card standing on a table-top easel (round 7, the Bücherstand reading card).

    The writing area `write_<name>` (w x h, `surface` "card" = `paper_card`, or "slate") lies at
    F's origin inside a thin wooden frame (`frame`, wood Part: four rails with a little
    irregularity, a backing board in `back`). A ledge runs along the foot of the frame, a back
    leg props it on the surface at height `base_z` (default: where the frame's foot is), and an
    optional brass bulldog clip (`clip`, a metal Part) holds the card at the top. Build F with
    face_frame(..., lean=...) so the card leans back. Returns {"write", "outer": (W, H), "F"}."""
    R = state.rng
    W, H = w + 2 * rail, h + 2 * rail
    fz = depth / 2 - 0.004
    for sgn in (1, -1):
        local_box(frame, F, R.uniform(-0.002, 0.002), sgn * (h / 2 + rail / 2), fz,
                  W + R.uniform(-0.003, 0.004), rail, depth, grain=0, var=0.1, bevel=0.003, tint=tint)
        local_box(frame, F, sgn * (w / 2 + rail / 2), 0, fz, rail * R.uniform(0.94, 1.0), h,
                  depth * 0.94, grain=1, var=0.1, bevel=0.003, tint=tint)
    local_box(back, F, 0, 0, -0.006, W - 0.006, H - 0.006, 0.008, grain=1, tint="dark", var=0.05, bevel=0)
    write = write_surface(name, F, w, h, z=0.0015, surface=surface)
    # ledge along the foot (the card's bottom rail rests on it) and two small front feet
    local_box(frame, F, 0, -H / 2 + 0.006, depth + 0.006, W * 1.04, 0.014, 0.022, grain=0, var=0.08,
              bevel=0.002, tint=tint)
    ex, ey, ez = frame_axes(F)
    foot0 = at(F, 0, -H / 2, 0)
    bz = foot0.z if base_z is None else base_z
    # back leg: from behind the top rail down to the surface behind the card
    top = at(F, 0, H / 2 - 0.03, -0.012)
    bdir = Vector((-ez.x, -ez.y, 0))
    bdir = bdir.normalized() if bdir.length > 1e-6 else Vector((0, 1, 0))
    foot = Vector((top.x, top.y, bz + 0.004)) + bdir * ((top.z - bz) * math.tan(math.radians(leg_angle)))
    frame.slab(top, foot, 0.022, 0.012, up=tuple(ex), tint=tint, var=0.1)
    # a short hinge block where the leg meets the frame
    local_box(frame, F, 0, H / 2 - 0.03, -0.016, 0.034, 0.02, 0.01, grain=0, tint="dark", bevel=0)
    if clip is not None:
        ct = at(F, 0, h / 2 + rail * 0.4, depth * 0.5)
        local_box(clip, F, 0, h / 2 + rail * 0.45, depth + 0.003, 0.038, 0.022, 0.005, var=0.05, bevel=0.0015)
        local_box(clip, F, 0, h / 2 + rail * 0.45 + 0.012, depth + 0.006, 0.036, 0.005, 0.008, var=0.05, bevel=0)
        for sx in (-1, 1):     # the two wire handles
            clip.tube([ct + ex * sx * 0.012 + ez * 0.012, ct + ex * sx * 0.012 + ey * 0.026 + ez * 0.02],
                      0.0018, tseg=4)
    return {"write": write, "outer": (W, H), "F": F}
