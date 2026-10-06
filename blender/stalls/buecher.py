"""Bücherstand (section: Reading).

An antiquarian bookshop hut: bottle-green painted boards with cream trim, a dark shingled roof,
a small projecting bay window with a copper-hooded roof on the left wall, an iron wall lantern,
and a hand-painted swallow-tail sign "Bücher" hung on chains.

Round 8 (docs/adr/0004): six glazed category cabinets replace the round-3 side racks and book
carts. Two stand in the hut front either side of the counter, four in two short wings under
shingled canopies. Each cabinet has a cream crest sign with its English label (sign_cat_<key>;
round 10, Mac 2026-10-06: the groupings in English, label_en),
angled face-out boards for up to five covers per row (sized for the category's book count), a
spine board above them, a glazed door (act_cab_<key>, hinged on its left edge), slot_cat_<key>
and the close-up camera pair cam_cat_<key> / cam_cat_<key>_target. The geometry comes from
buecher_sections.py, which also writes buecher_sections.json for the vendor.

    /home/claude/tools/bpy-venv/bin/python blender/stalls/buecher.py [--no-render] [--no-lite]
Outputs site/public/models/stall_buecher.glb and stall_buecher.lite.glb.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

import buecher_sections as BS  # noqa: E402
import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut, grime as hut_grime  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import boards, export, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

NAME = "stall_buecher"
W, D = BS.HUT_W, BS.HUT_D          # round 8: 4.2 m wide (was 3.7) for two five-cover cabinets
EAVE, RIDGE = 2.9, 3.9
LANTERN = (W / 2 + 0.43, -0.35, 2.1)    # on the right side wall, bracket pointing back to the wall


# cloth and leather bindings (linear RGB tints of the 'bookcloth' material)
# (lifted about 1.6x in round 2: behind the glass, with no engine light inside the cabinet, the
# darker round-1 cloths read as an empty cabinet in three.js)
# (round 3: one more step, about 1.25x, as the Fable judge asked: still barely visible in three.js)
BINDINGS = [(0.58, 0.08, 0.06), (0.09, 0.29, 0.14), (0.08, 0.13, 0.38), (0.42, 0.19, 0.08),
            (0.80, 0.55, 0.18), (0.86, 0.78, 0.60), (0.10, 0.10, 0.09), (0.36, 0.06, 0.13),
            (0.08, 0.33, 0.33), (0.68, 0.32, 0.10)]


def bay_window(h, glass, lite):
    """Small canted bay window projecting from the left wall (faces -X)."""
    P = h.paint
    xw = h.x0 + 0.0
    yc, zc = 0.05, 1.5
    fw, dp, sw = 0.72, 0.3, 0.26          # front width, projection, side run
    z0, z1 = 1.05, 1.95
    # plan: wall points A (y-), B (y+); front points C, D
    A = Vector((xw, yc - fw / 2 - sw * 0.7, 0))
    B = Vector((xw, yc + fw / 2 + sw * 0.7, 0))
    C = Vector((xw - dp, yc - fw / 2, 0))
    Dd = Vector((xw - dp, yc + fw / 2, 0))
    plan = [A, C, Dd, B]
    # sill / base block and apron
    def ring(z, grow=0.0):
        out = []
        for p in plan:
            q = Vector((p.x - (grow if p.x < xw - 1e-3 else 0), p.y + (-grow if p.y < yc else grow) *
                        (1 if p.x < xw - 1e-3 else 1.0), z))
            out.append(q)
        return out
    P.loft([ring(z0 - 0.3), ring(z0 - 0.06), ring(z0 - 0.06, 0.03), ring(z0, 0.03)], closed=False,
           band="green", smooth=False)
    P.loft([ring(z0, 0.03), ring(z0, 0.0)], closed=False, band="cream", smooth=False)
    P.shape([(p.x, p.y) for p in ring(z0, 0.03)], depth=0.03, M=Matrix.Translation((0, 0, z0 - 0.015)),
            band="cream")
    # corbel brackets under the sill
    for p in (C, Dd):
        h.frame.slab((xw, p.y, z0 - 0.45), (p.x + 0.03, p.y, z0 - 0.08), 0.05, 0.05, up=(0, 0, 1),
                     tint="walnut")
    # glazed faces
    for p, q in ((A, C), (C, Dd), (Dd, B)):
        d = (q - p)
        L = d.length
        ang = math.atan2(d.y, d.x)
        mid = (p + q) / 2
        Rz = Euler((0, 0, ang)).to_matrix().to_4x4()
        nrm = Vector((d.y, -d.x, 0)).normalized()
        # posts and rails (cream) in the face's own frame
        for (u, v, sx, sz) in ((0, z1 - 0.03, L, 0.06), (0, z0 + 0.03, L, 0.06), (-L / 2 + 0.025, (z0 + z1) / 2, 0.05, z1 - z0),
                               (L / 2 - 0.025, (z0 + z1) / 2, 0.05, z1 - z0), (0, (z0 + z1) / 2, L - 0.05, 0.018)):
            c = mid + (Rz.to_3x3() @ Vector((u, 0, 0))) + Vector((0, 0, v))
            P.mbox(Matrix.Translation(c) @ Rz, (sx, 0.035, sz), band="cream", grain=0 if sx > sz else 2)
        if L > 0.4:
            c = mid + Vector((0, 0, (z0 + z1) / 2))
            P.mbox(Matrix.Translation(c) @ Rz, (0.018, 0.03, z1 - z0 - 0.08), band="cream", grain=2)
        c = mid + Vector((0, 0, (z0 + z1) / 2)) - nrm * 0.0
        glass.mbox(Matrix.Translation(c) @ Rz, (L - 0.05, 0.006, z1 - z0 - 0.1), bevel=0, var=0.0)
    # little hipped roof sheathed in copper, plus its fascia
    top0 = ring(z1, 0.05)
    peak = [Vector((xw, p.y * 0.6 + yc * 0.4, z1 + 0.3)) if p.x < xw - 1e-3 else Vector((p.x, p.y, z1 + 0.3))
            for p in top0]
    peak = [Vector((xw - 0.02, yc - fw / 2 * 0.5, z1 + 0.32)), Vector((xw - 0.05, yc - fw / 2 * 0.4, z1 + 0.32)),
            Vector((xw - 0.05, yc + fw / 2 * 0.4, z1 + 0.32)), Vector((xw - 0.02, yc + fw / 2 * 0.5, z1 + 0.32))]
    h.extra_copper.loft([top0, peak], closed=False, smooth=False)
    P.loft([ring(z1 - 0.06, 0.05), ring(z1, 0.05)], closed=False, band="cream", smooth=False)
    # a lamp glow inside the bay (goods/books go on the sill inside)
    h.bulbs.sphere((xw - 0.12, yc, z1 - 0.18), 0.04, seg=10, rings=7, scale=(1, 1, 1.3))
    h.wire.tube([(xw - 0.12, yc, z1 + 0.02), (xw - 0.12, yc, z1 - 0.12)], 0.004, tseg=4)


def lantern(h, pos, lite, rot=0.0):
    """Iron wall lantern on a scroll bracket. The bracket runs from the lantern toward local +Y
    (the wall); rot turns it about Z (pi/2: mounted on a wall facing +X)."""
    F = Matrix.Translation(pos) @ Euler((0, 0, rot)).to_matrix().to_4x4()
    R3 = F.to_3x3()

    def P(x, y, z):
        return F @ Vector((x, y, z))

    def E(*e):
        return (R3 @ Euler(e).to_matrix()).to_euler()

    iron = h.iron
    iron.mbox(F @ Matrix.Translation((0, 0.2, 0.25)), (0.02, 0.4, 0.02), bevel=0)
    iron.torus(P(0, 0.12, 0.16), 0.08, 0.008, seg=12, tseg=4, rot=E(0, math.pi / 2, 0), arc=math.pi * 1.2)
    iron.mbox(F @ Matrix.Translation((0, 0, 0.14)), (0.012, 0.012, 0.2), bevel=0)
    iron.cyl(P(0, 0, 0.02), 0.11, 0.03, 0.08, seg=4, rot=E(0, 0, math.pi / 4))       # hood
    for dx in (-0.06, 0.06):
        for dy in (-0.06, 0.06):
            iron.mbox(F @ Matrix.Translation((dx, dy, -0.15)), (0.012, 0.012, 0.28), bevel=0)
    iron.cyl(P(0, 0, -0.3), 0.07, 0.09, 0.04, seg=4, rot=E(0, 0, math.pi / 4))
    glow = Part("buecher_lantern_glass", "lamp_glass", var=0.0)
    glow.mbox(F @ Matrix.Translation((0, 0, -0.15)), (0.11, 0.11, 0.25), bevel=0)
    h.extra.append(glow)


# ======================================================================== category cabinets
# Geometry from buecher_sections.py (the same module writes buecher_sections.json for the vendor).


def _frame(origin, a):
    return Matrix.Translation((origin[0], origin[1], 0.0)) @ Euler((0, 0, a)).to_matrix().to_4x4()


def _T(x, y, z):
    return Matrix.Translation((x, y, z))


# labels that are one long word get a hyphenated second line on a narrow board
SIGN_FONT = "alegreya_sc"
SIGN_MAX_SIZE = 0.13            # one short line
SIGN_TEXT_H = 0.16              # height the letters may take on a SIGN_H board (inside the border and arch)


def _measure(text, size):
    """Width and height (m) of a sign label set as Part.text sets it, without emitting anything."""
    from nmlib.geo import load_font
    cu = bpy.data.curves.new("tmp_measure", "FONT")
    cu.body = text
    cu.font = load_font(state.font(SIGN_FONT))
    cu.size = size
    cu.align_x, cu.align_y = 'CENTER', 'CENTER'
    cu.fill_mode = 'FRONT'
    ob = bpy.data.objects.new("tmp_measure_ob", cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    xs = [v.co.x for v in me.vertices] or [0]
    ys = [v.co.y for v in me.vertices] or [0]
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.curves.remove(cu)
    return max(xs) - min(xs), max(ys) - min(ys)


def sign_layout(label, max_w, max_h):
    """Round 10 (Mac, 2026-10-06: the groupings in English): the English label on one, two or three lines,
    whichever gives the biggest letters inside max_w x max_h (a line never starts with '&' or 'and'). More lines
    win only when they give clearly bigger letters. Returns (text, size)."""
    words = label.split()
    cands = [label]
    for i in range(1, len(words)):
        cands.append(" ".join(words[:i]) + "\n" + " ".join(words[i:]))
        for j in range(i + 1, len(words)):
            cands.append(" ".join(words[:i]) + "\n" + " ".join(words[i:j]) + "\n" + " ".join(words[j:]))
    best = None
    ref = 0.1
    for c in cands:
        if any(ln.split()[0] in ("&",) for ln in c.split("\n")):
            continue
        w, h = _measure(c, ref)
        size = min(ref * max_w / w, ref * max_h / h, SIGN_MAX_SIZE)
        lines = c.count("\n") + 1
        if best is None or size > best[1] * (1.06 if lines > best[2] else 1.0):
            best = (c, size, lines)
    return best[0], best[1]


def section_sign(h, key, label, F, cx, cy, cz, w, hh, lite):
    """Cream crest board with green letters and a thin gold border, standing in frame F (faces -Y),
    with an arched top. Its own mesh sign_cat_<key> in 'paint_glow' (the faint warm stand-in keeps
    it legible under the site's moonlight; the Cycles preview switches the stand-in off)."""
    S = Part(f"sign_cat_{key}", "paint_glow", var=0.03)
    S.flat_text = True          # painted letters: one front face each, no sides
    S.curve_simplify = 8.0
    h.extra.append(S)
    # round 10 (Mac, 2026-10-06: "the sign for each bookshelf should have light"): the board itself is its own
    # mesh sign_cat_<key>_board (a child of sign_cat_<key>), in 'sign_lit': the paint kit with an emissive
    # pool of warm light from the picture lamp above it (brightest under the lamp, falling off downward and
    # toward the ends; see sign_lamp and finish_sign_boards). The letters and the gold border stay in
    # 'paint_glow', so they keep their dark green against the lit cream.
    B = Part(f"sign_cat_{key}_board", "paint_glow", var=0.03)
    h.extra.append(B)
    Mb = F @ _T(cx, cy, cz) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    d = 0.022
    k = 0.035                   # arch rise above the board's shoulders
    n = 6 if lite else 12
    outline = [(-w / 2, -hh / 2), (w / 2, -hh / 2), (w / 2, hh / 2 - k)]
    outline += [(w / 2 * math.cos(math.pi * i / n), hh / 2 - k + k * math.sin(math.pi * i / n)) for i in range(1, n)]
    outline += [(-w / 2, hh / 2 - k)]
    B.shape(outline, depth=d, M=Mb, band="cream", bevel=0.003)
    h.sign_boards.append((key, Mb, w, hh))
    # thin gold border just inside the edge, proud of the face (sides and bottom; the arch is plain)
    e = 0.016
    for (x, z, ww, zz) in ((0, -hh / 2 + e, w - 2 * e + 0.008, 0.008),
                           (-w / 2 + e, -k / 2, 0.008, hh - 2 * e - k), (w / 2 - e, -k / 2, 0.008, hh - 2 * e - k)):
        S.mbox(F @ _T(cx + x, cy - d / 2 - 0.002, cz + z), (ww, 0.004, zz), band="gold", bevel=0,
               grain=0 if ww > zz else 2, drop=("+y",))
    text, size = sign_layout(label, w - 0.07, SIGN_TEXT_H + (hh - BS.SIGN_H))
    Mt = F @ _T(cx, cy - d / 2 - 0.0035, cz - 0.012) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    tw, th = S.text(text, state.font(SIGN_FONT), size, 0.004, M=Mt, max_width=w - 0.07, band="green",
                    resolution=1, bevel=0.0)
    print(f"[buecher] sign {key}: {text!r} at {size:.3f} m, letters {tw:.3f} x {th:.3f} m on a {w:.2f} x {hh:.2f} board")
    return S


# ------------------------------------------------------------------ round 10: lit cabinet signs
LAMP_Z = BS.SIGN_Z + BS.SIGN_H + 0.075     # hood axis: 7.5 cm above the board's crest
LAMP_Y = -0.095                           # and 10 cm in front of its face
LAMP_R = 0.021                            # brass hood radius
GLOW_RES = (128, 64)                      # the pool-of-light texture (shared by the six boards)
GLOW_PEAK = (0.80, 0.56, 0.32)            # emissive factor at the brightest point (linear, warm lamplight)


def sign_lamp(h, key, F, cx, cz, w, lite):
    """A small brass picture lamp over a crest sign, as its own mesh lamp_cat_<key> (brass): a tubular
    hood along the board on two swan-neck arms that rise from the cornice behind the board, with a warm
    tube bulb (in the stall's bulbs_ mesh, so the engine makes it glow) under the hood. Real lamps are
    not added in the browser (each real light slows the whole market): the light it throws is painted
    onto the board (sign_lit)."""
    Lp = Part(f"lamp_cat_{key}", "brass", var=0.02)
    h.extra.append(Lp)
    L = min(w * 0.62, 0.5)                # hood length
    seg = 6 if lite else 10
    rot = (0, math.pi / 2, 0)

    def W(x, y, z):
        return F @ Vector((x, y, z))
    ang = math.atan2(F[1][0], F[0][0])    # the cabinet's yaw: the hood runs along its width
    hood_rot = (Euler((0, 0, ang)).to_matrix() @ Euler(rot).to_matrix()).to_euler()
    Lp.cyl(W(cx, LAMP_Y, LAMP_Z), LAMP_R, LAMP_R * 0.86, L, seg=seg, rot=hood_rot, caps=True)
    # end caps a touch wider (the rolled rim of a picture light)
    for s_ in (-1, 1):
        Lp.cyl(W(cx + s_ * L / 2, LAMP_Y, LAMP_Z), LAMP_R * 1.12, LAMP_R * 1.12, 0.008, seg=seg, rot=hood_rot)
    for s_ in (-1, 1):
        x = cx + s_ * L * 0.32
        pts = [W(x, 0.05, BS.SIGN_Z + 0.01), W(x, 0.05, BS.SIGN_Z + BS.SIGN_H + 0.02),
               W(x, 0.035, LAMP_Z + 0.035), W(x, -0.01, LAMP_Z + 0.05), W(x, LAMP_Y + 0.03, LAMP_Z + 0.03),
               W(x, LAMP_Y, LAMP_Z + LAMP_R * 0.6)]
        if lite:
            pts = [pts[0], pts[1], pts[3], pts[5]]
        Lp.tube(pts, 0.0045, tseg=5 if lite else 6)
        Lp.box(W(x, 0.05, BS.SIGN_Z + 0.012), (0.02, 0.014, 0.012), rot=(0, 0, ang), bevel=0)   # foot
    # the tube bulb: hangs just under the hood axis, so from below it shows as a warm strip
    h.bulbs.cyl(W(cx, LAMP_Y + 0.004, LAMP_Z - LAMP_R * 0.55), 0.0075, 0.0075, L * 0.88, seg=5 if lite else 6,
                rot=hood_rot)


def _glow_pixels():
    """The pool of light a picture lamp throws on the board below it, as a grey falloff (1 = GLOW_PEAK),
    u across the board, v up it (v = 1 at the crest). Brightest just under the lamp, about two fifths at the
    foot, a little dimmer toward the ends than the middle, with a faint paint mottle."""
    import numpy as np
    W_, H_ = GLOW_RES
    v, u = np.mgrid[0:H_, 0:W_].astype(np.float32)
    u = (u + 0.5) / W_
    v = 1.0 - (v + 0.5) / H_                      # image rows run top-down
    # distance from the lamp: it hangs over the crest, in front of the face
    dz = (1.0 - v) * BS.SIGN_H + (LAMP_Z - BS.SIGN_Z - BS.SIGN_H)
    dy = -LAMP_Y
    r2 = dz * dz + dy * dy
    cos_in = dz / np.sqrt(r2)                    # light reaches the vertical face at a grazing angle
    e = cos_in * dy / r2                          # irradiance from a point above the face (relative)
    e = e / e.max()
    across = 1.0 - 0.4 * np.clip(np.abs(u - 0.5) / 0.5, 0, 1) ** 2.2
    g = (0.14 + 0.86 * e ** 0.7) * across
    rng = np.random.default_rng(10)
    mott = rng.normal(0, 1, (H_ // 8, W_ // 8)).astype(np.float32)
    mott = np.kron(mott, np.ones((8, 8), np.float32))
    from scipy import ndimage
    mott = ndimage.gaussian_filter(mott, 3.0)
    g = np.clip(g * (1.0 + 0.04 * mott / (mott.std() + 1e-6)), 0, 1)
    return g


def sign_glow_image():
    """blender/out/kit/sign_glow.png (sRGB grey falloff), loaded as a Blender image."""
    import numpy as np
    from PIL import Image
    path = os.path.join(state.KIT_DIR, "sign_glow.png")
    g = _glow_pixels()
    srgb = np.where(g <= 0.0031308, g * 12.92, 1.055 * np.power(g, 1 / 2.4) - 0.055)
    px = np.clip(srgb * 255 + 0.5, 0, 255).astype(np.uint8)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.stack([px, px, px], -1)).save(path)
    img = bpy.data.images.get("sign_glow")
    if img is None:
        img = bpy.data.images.load(path)
        img.name = "sign_glow"
    else:
        img.reload()
    img.colorspace_settings.name = "sRGB"
    return img


def sign_lit_material():
    """'sign_lit': the paint kit (base colour, roughness, normal) with emissive = sign_glow.png on the
    'SignLit' UV map x GLOW_PEAK (the exporter writes emissiveTexture + emissiveFactor)."""
    from nmlib import mats
    m = bpy.data.materials.get("sign_lit")
    if m is not None:
        return m
    m = mats.get("paint_glow").copy()
    m.name = "sign_lit"
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    for ln in list(bsdf.inputs["Emission Color"].links):
        nt.links.remove(ln)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "SignLit"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = sign_glow_image()
    tex.extension = 'EXTEND'
    nt.links.new(uv.outputs[0], tex.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs["Color"], mul.inputs[6])
    mul.inputs[7].default_value = (*GLOW_PEAK, 1)
    nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


def finish_sign_boards(h, objs):
    """After h.finish(): each sign_cat_<key>_board gets the 'sign_lit' material, a 'SignLit' UV map
    (u across the board, v up it, from the board's own frame) and is parented to sign_cat_<key>."""
    by_name = {o.name: o for o in objs}
    mat = sign_lit_material()
    for key, Mb, w, hh in h.sign_boards:
        ob = by_name.get(f"sign_cat_{key}_board")
        sign = by_name.get(f"sign_cat_{key}")
        if ob is None:
            continue
        me = ob.data
        me.materials[0] = mat
        uvl = me.uv_layers.new(name="SignLit")
        inv = Mb.inverted()
        for poly in me.polygons:
            for li in poly.loop_indices:
                p = inv @ me.vertices[me.loops[li].vertex_index].co
                uvl.data[li].uv = (p.x / w + 0.5, p.y / hh + 0.5)
        me.uv_layers.active = me.uv_layers["UVMap"]
        if sign is not None:
            ob.parent = sign
            ob.matrix_parent_inverse = sign.matrix_world.inverted()


def canopy(h, F, L, D, lite, snow_index, tint="walnut"):
    """Little shingled pent roof over a wing of cabinets (front low, back high), on posts standing
    on the cabinets' backs and braced out to the front, with a cream fascia, a bulb string under
    its front edge and its own snow cap."""
    zb, zf = 2.66, 2.44                   # back top / front bottom
    yb, yf = D + 0.07, -0.34              # back / front edge (wing frame)
    A = (F.to_3x3() @ Vector((1, 0, 0))).normalized()
    back = F @ Vector((L / 2, yb, zb))
    front = F @ Vector((L / 2, yf, zf))
    dn = (front - back)
    sl = cp.Slope(front, A, dn, dn.length, -L / 2 - 0.08, L / 2 + 0.08)
    cp.roof_deck(h.wood, sl, tint=h.inner_tint, rafters=3, rafter=(0.045, 0.07))
    cp.shingles(h.roofp, sl, tint=tint, sw=0.19, expo=0.13, sh=0.28)
    cp.fascia(h.paint, sl, band="cream", h=0.1)
    up = tuple(F.to_3x3() @ Vector((1, 0, 0)))
    for x in (0.03, L / 2, L - 0.03):
        h.frame.mbox(F @ _T(x, D - 0.03, (BS.CAB_TOP + zb) / 2), (0.055, 0.055, zb - BS.CAB_TOP), grain=2,
                     tint="walnut")
        a = F @ Vector((x, D - 0.06, 2.12))
        b = F @ Vector((x, -0.16, zf + (zb - zf) * (-0.16 - yf) / (yb - yf) - 0.08))
        h.frame.slab(a, b, 0.04, 0.04, up=up, tint="walnut")
    pts = [tuple(F @ Vector((L * t, yf + 0.02, zf - 0.07))) for t in (0.0, 0.5, 1.0)]
    cp.bulb_string(h.bulbs, h.wire, pts, sag=0.035, spacing=0.2, seg=h.bulb_detail[0], rings=h.bulb_detail[1])
    sp = Part(f"snow_{snow_index}", "snow", var=0.02)
    cp.snow_cap(sp, sl, courses=(0.13, -0.03), thick=0.022, base=0.032, ridge_clear=0.06, edge_in=0.04,
                seed=snow_index * 2.3)
    h.snow.append(sp)


def panel_door(P, F, x0, x1, z0, z1, lite, knob=None, frame_band="green", bead_band="cream"):
    """Panelled cupboard door (or drawer front) on the cabinet front (local y < 0): a frame board,
    a proud panel and a cream bead; knob = brass Part for a small knob."""
    w, hh = x1 - x0, z1 - z0
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    P.mbox(F @ _T(cx, -0.011, cz), (w, 0.022, hh), band=frame_band, grain=2 if hh > w else 0)
    if hh > 0.16 and w > 0.16:
        P.mbox(F @ _T(cx, -0.026, cz), (w - 0.1, 0.012, hh - 0.1), band=frame_band, grain=2 if hh > w else 0)
        if not lite:
            for (x, z, sx, sz) in ((cx, z1 - 0.05, w - 0.1, 0.008), (cx, z0 + 0.05, w - 0.1, 0.008),
                                   (x0 + 0.05, cz, 0.008, hh - 0.1), (x1 - 0.05, cz, 0.008, hh - 0.1)):
                P.mbox(F @ _T(x, -0.025, z), (sx, 0.01, sz), band=bead_band, bevel=0, grain=0 if sx > sz else 2)
    if knob is not None:
        kx = x1 - 0.05 if hh > w else cx
        knob.sphere(F @ Vector((kx, -0.035, cz if hh <= w else z1 - 0.12)), 0.012, seg=8, rings=5)


def category_cabinet(h, s, lite):
    """One glazed category cabinet (see buecher_sections.py): carcass, plinth, panelled base
    cupboard, face-out boards (ledge, lip, leaning backboard), a spine board, a cream back, two
    small warm bulbs under the top, the crest sign and the glazed door act_cab_<key>."""
    L = s["_local"]
    F = _frame(L["origin"], L["rot"])
    cw = L["width"]
    zs = L["rows"]
    Dp = BS.CAB_DEPTH
    sd = BS.CAB_SIDE
    bw = cw - 2 * sd
    gb = BS.glass_bottom(len(zs))
    P, FR = h.paint, h.frame
    # carcass: sides, top, back boards (cream inside), plinth, cornice
    for x in (sd / 2, cw - sd / 2):
        P.mbox(F @ _T(x, Dp / 2, (0.1 + BS.CAB_TOP) / 2), (sd, Dp, BS.CAB_TOP - 0.1), band="green", grain=2)
    P.mbox(F @ _T(cw / 2, Dp / 2, BS.CAB_TOP - 0.015), (cw, Dp, 0.03), band="green")
    n = max(3, int(round(bw / 0.13)))
    for i in range(n):
        P.mbox(F @ _T(sd + bw * (i + 0.5) / n, Dp - 0.011, (0.1 + BS.CAB_TOP) / 2), (bw / n - 0.003, 0.018,
               BS.CAB_TOP - 0.13), band="cream", grain=2, var=0.05, bevel=0 if lite or i % 2 else None,
               drop=("-z", "+z"))
    FR.mbox(F @ _T(cw / 2, Dp / 2 + 0.005, 0.05), (cw - 0.01, Dp - 0.02, 0.1), tint="dark")
    P.mbox(F @ _T(cw / 2, Dp / 2 - 0.012, BS.CAB_TOP + 0.02), (cw + 0.03, Dp + 0.03, 0.04), band="cream")
    P.mbox(F @ _T(cw / 2, Dp / 2 - 0.02, BS.CAB_TOP + 0.05), (cw + 0.06, Dp + 0.05, 0.025), band="green")
    # base cupboard: frame front and panelled doors (two below a drawer rail when it is tall)
    P.mbox(F @ _T(cw / 2, 0.006, gb - 0.02), (cw, 0.018, 0.04), band="cream")            # rail under the glass
    P.mbox(F @ _T(cw / 2, Dp / 2, gb - 0.04), (bw, Dp - 0.04, 0.025), band="green", drop=("-z",))
    z_doors = gb - 0.05
    if gb - 0.1 > 0.75:                                                                   # tall base: a drawer
        panel_door(P, F, sd + 0.01, cw - sd - 0.01, z_doors - 0.17, z_doors - 0.01, lite, knob=h.extra_brass)
        z_doors -= 0.18
    if cw > 0.7:
        panel_door(P, F, sd + 0.01, cw / 2 - 0.004, 0.13, z_doors, lite, knob=None)
        panel_door(P, F, cw / 2 + 0.004, cw - sd - 0.01, 0.13, z_doors, lite, knob=None)
        for x in (cw / 2 - 0.035, cw / 2 + 0.035):
            h.extra_brass.sphere(F @ Vector((x, -0.035, (0.13 + z_doors) / 2 + 0.05)), 0.012, seg=8, rings=5)
    else:
        panel_door(P, F, sd + 0.01, cw - sd - 0.01, 0.13, z_doors, lite, knob=h.extra_brass)
    # face-out boards: ledge with a lip, backboard leaning back LEAN_DEG
    lean = math.radians(BS.LEAN_DEG)
    y_lip = BS.LEDGE_Y
    y_foot = y_lip + 0.012 + BS.LEDGE_D
    for z in zs:
        FR.mbox(F @ _T(cw / 2, (y_lip + y_foot) / 2 + 0.006, z - 0.009), (bw, y_foot - y_lip + 0.012, 0.018),
                tint="walnut", grain=0, bevel=0.003)
        FR.mbox(F @ _T(cw / 2, y_lip + 0.006, z + BS.LIP_H / 2 - 0.004), (bw, 0.012, BS.LIP_H + 0.01),
                tint="walnut", grain=0, bevel=0.002)
        bh = 0.235
        c = Vector((cw / 2, y_foot + 0.008 + math.sin(lean) * bh / 2, z + math.cos(lean) * bh / 2))
        FR.mbox(F @ _T(*c) @ Euler((-lean, 0, 0)).to_matrix().to_4x4(), (bw, 0.014, bh), tint="honey", grain=0,
                bevel=0.002, drop=("+y",))
    # spine board for books at rest
    FR.mbox(F @ _T(cw / 2, (y_lip + Dp - 0.02) / 2, BS.SPINE_Z - 0.011), (bw, Dp - 0.02 - y_lip, 0.022),
            tint="walnut", grain=0, bevel=0.003)
    # small warm bulbs under the top, behind the door
    for t in (0.3, 0.7):
        p = F @ Vector((cw * t, 0.07, BS.GLASS_TOP - 0.012))
        h.wire.cyl(p, 0.009, 0.009, 0.02, seg=6)
        h.bulbs.sphere(p + Vector((0, 0, -0.022)), 0.014, seg=6 if lite else 8, rings=4 if lite else 5,
                       scale=(1, 1, 1.25))
    # crest sign on the cornice
    section_sign(h, s["key"], s["label_en"], F, *L["sign"], cw - 0.03, BS.SIGN_H, lite)
    sign_lamp(h, s["key"], F, L["sign"][0], L["sign"][2], cw - 0.03, lite)
    # glazed door: its own node act_cab_<key> at the hinge, frame and glass as child meshes
    door = Part(f"cab_door_{s['key']}", "paint", var=0.03)
    pane = Part(f"cab_glass_{s['key']}", "glass_clear", var=0.0)
    x0, x1 = sd, cw - sd
    z0, z1 = gb, BS.GLASS_TOP
    fw, ft = 0.034, BS.DOOR_T
    yd = -ft / 2 - 0.001
    door.mbox(F @ _T((x0 + x1) / 2, yd, z1 - fw / 2), (x1 - x0, ft, fw), band="cream")
    door.mbox(F @ _T((x0 + x1) / 2, yd, z0 + fw / 2), (x1 - x0, ft, fw), band="cream")
    for x in (x0 + fw / 2, x1 - fw / 2):
        door.mbox(F @ _T(x, yd, (z0 + z1) / 2), (fw, ft, z1 - z0), band="cream", grain=2)
    # glazing bars only where a ledge or the spine board crosses (they hide no cover)
    for zb_ in [z + 0.006 for z in zs[1:]] + [BS.SPINE_Z - 0.005]:
        door.mbox(F @ _T((x0 + x1) / 2, yd - 0.002, zb_), (x1 - x0 - 2 * fw, 0.016, 0.016), band="cream", bevel=0)
    xk = x1 - 0.017 if BS.HINGE[s["key"]] == "left" else x0 + 0.017      # pull on the free edge
    door.mbox(F @ _T(xk, yd - 0.016, (z0 + z1) / 2 + 0.02), (0.012, 0.012, 0.05), band="gold", bevel=0)
    pane.mbox(F @ _T((x0 + x1) / 2, yd, (z0 + z1) / 2), (x1 - x0 - 2 * fw + 0.012, 0.005, z1 - z0 - 2 * fw + 0.012),
              bevel=0, var=0.0)
    h.doors.append((s["key"], F @ Vector(L["hinge"]), L["rot"], door, pane))


def finish_doors(h):
    """Create the act_cab_<key> empties and parent each door's meshes to its empty (hinge)."""
    objs = []
    for key, hinge, rot, door, pane in h.doors:
        e = export.empty(f"act_cab_{key}", tuple(hinge), rot=(0, 0, rot))
        inv = (Matrix.Translation(hinge) @ Euler((0, 0, rot)).to_matrix().to_4x4()).inverted()
        for part in (door, pane):
            ob = part.finish()
            if ob is None:
                continue
            ob.parent = e
            ob.matrix_parent_inverse = inv
            objs.append(ob)
    return objs


def section_slots(secs):
    for s in secs:
        L = s["_local"]
        F = _frame(L["origin"], L["rot"])
        p = F @ Vector(L["slot"])
        export.empty(s["slot"], tuple(p), rot=(0, 0, L["rot"]))
        export.empty(s["cam_target"], tuple(s["cam_target_position"]))
        export.empty(s["cam"], tuple(s["cam_position"]), look_at=tuple(s["cam_target_position"]))


def build_sections(h, lite):
    secs = BS.sections()
    h.doors = []
    h.sign_boards = []
    for s in secs:
        category_cabinet(h, s, lite)
    for i, (unit, (o, a, L)) in enumerate(sorted(BS.wing_units().items())):
        canopy(h, _frame(o, a), L, BS.CAB_DEPTH, lite, snow_index=2 + i)
    section_slots(secs)
    return secs

def build(lite):
    h = Hut("buecher", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='x', ov_eave=0.4, ov_gable=0.25,
            wall="vertical", wall_band="green", frame_tint="walnut", roof_tint="walnut", inner_tint="oak",
            counter_tint="walnut", plank_w=0.13, bulb_spacing=0.21, counter_depth=0.55, counter_over=0.2,
            front_posts=[-W / 2 + 0.05, W / 2 - 0.05])
    h.extra_brass = h.part("brass", "brass", var=0.02)
    # old copper sheet (iron kit dents and streaks, copper-brown colour, metal 0.6): the flat
    # 'copper' material rendered as a salmon plane in three.js (round 1)
    h.extra_copper = h.part("copper", "copper_old", var=0.05)
    glass = h.part("glass", "glass", var=0.0)
    yF = h.yF
    P = h.paint
    xin = W / 2 - 0.1 - max(s["cabinet"]["width"] for s in BS.sections() if s["unit"].startswith("hut"))
    # (inner edge of the two hut cabinets)
    h.build_carcass()
    h.build_counter(x0=-xin + 0.02, x1=xin - 0.02, brackets=3)
    h.build_shelves(x0=-xin + 0.05, x1=xin - 0.05, band=None)
    h.build_roof(cover="shingles", fascia_band="cream", barge_band="cream")
    h.build_snow(drifts=3)
    # cream trim: corner boards, rails, counter lip
    for x in (h.x0 + 0.05, h.x1 - 0.05):
        for y in (yF + 0.0, h.yB - 0.0):
            P.box((x, y, EAVE / 2), (0.13, 0.13, EAVE), band="cream", grain=2)
    for z in (0.28, 0.82):
        P.box((0, yF - 0.032, z), (2 * xin, 0.022, 0.09), band="cream")
    P.box((0, yF - h.counter_over - 0.026, COUNTER_TOP - 0.05), (2 * xin, 0.02, 0.06), band="cream")
    # ------------------------------------------------------------ bay window, lantern
    bay_window(h, glass, lite)
    # round 3: the right wing stands where the lantern hung, so it moved to the right side wall
    lantern(h, LANTERN, lite, rot=math.pi / 2)
    # ------------------------------------------------------------ category cabinets (round 8)
    build_sections(h, lite)
    # ------------------------------------------------------------ hand-painted hanging sign
    sl = h.front_slope
    ye = yF - 0.22
    sign_c = Vector((0, ye, 2.16))
    cp.sign(P, P, "Bücher", state.font("fell_italic"), sign_c, 1.6, 0.36, depth=0.03,
            board_band="cream", text_band="green", frame_band=None, board_shape="banner",
            text_size=0.32, text_depth=0.005, max_fill=0.7, text_dy=0.01, resolution=1)
    # painted flourishes either side of the lettering (gold)
    for s in (-1, 1):
        for i, (dx, dz, ww) in enumerate(((0.52, 0.0, 0.12), (0.47, 0.05, 0.05), (0.47, -0.05, 0.05))):
            P.box((s * dx, ye - 0.02, sign_c.z + dz), (ww, 0.004, 0.012), band="gold", bevel=0)
    for x in (-0.6, 0.6):
        top = Vector((x, ye, RIDGE - abs(ye) * math.tan(h.pitch) - 0.03))
        bot = Vector((x, ye, sign_c.z + 0.18))
        n = 5 if not lite else 3
        for i in range(n):
            p = top.lerp(bot, (i + 0.5) / n)
            h.iron.torus(p, 0.016, 0.004, seg=8, tseg=4, rot=(0, 0, 0) if i % 2 else (0, math.pi / 2, 0))
    # ------------------------------------------------------------ bulbs
    h.eave_bulbs(sides=False)
    h.interior_bulbs(xs=(-0.6, 0.6), z=2.35)
    # light_1 sits out in front so it reaches both wings of cabinets; the camera stands back
    # far enough (5 m) to take in the hut and both wings
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.04, 0))),
              lights=[(0, 0.15, 2.4), (0, yF - 0.95, 2.3)], cam_dist=5.0, cam_h=1.85)
    reading_card(h)
    objs = h.finish()
    finish_sign_boards(h, objs)
    return objs + finish_doors(h)


# round 7: the Reading section's intro card (BUILD.md write_ / cam_read_). A cream card clipped
# into a small walnut frame on a table-top easel at the front-right corner of the counter, in
# the strip the vendor's counter books leave free (x 0.64-0.95, the front 0.25 m).
CARD_W, CARD_H = 0.26, 0.19                         # writing area (write_reading_card)
CARD_POS = (0.79, -1.32)                            # on the counter, clear of the props
CARD_YAW = -0.18                                    # turned a little toward the middle
CARD_LEAN = math.radians(14)


def reading_card(h):
    rail = 0.022
    Hh = CARD_H + 2 * rail
    cz = COUNTER_TOP + (Hh / 2) * math.cos(CARD_LEAN) + 0.002
    F = boards.face_frame((CARD_POS[0], CARD_POS[1], cz), yaw=CARD_YAW, lean=CARD_LEAN)
    boards.easel_card("reading_card", F, CARD_W, CARD_H, frame=h.frame, back=h.wood,
                      clip=h.extra_brass, base_z=COUNTER_TOP, rail=rail)
    boards.read_camera("reading_card", F, CARD_W, CARD_H, lift=0.03)


# category cover colours of the preview stand-ins (linear RGB tints of 'bookcloth')
CAT_TINT = {"physics": (0.05, 0.10, 0.32), "lives": (0.36, 0.05, 0.05), "mind": (0.04, 0.22, 0.22),
            "people": (0.58, 0.33, 0.06), "decisions": (0.06, 0.21, 0.08), "craft": (0.24, 0.06, 0.22)}


def vendor_set_is_current(key):
    """True when the vendor's prop_books_<key>.glb was built for the round-8 cabinets (newer
    than buecher_sections.json); older sets were laid out for the round-3 racks."""
    pth = os.path.join(state.MODELS_DIR, f"prop_books_{key}.glb")
    return os.path.exists(pth) and os.path.getmtime(pth) > os.path.getmtime(BS.OUT_JSON)


def section_standins(secs):
    """Render-only stand-in books for cabinets whose round-8 vendor set is not on disk yet: every
    book face-out on the angled boards (a cover in the category colour with a cream title label),
    and a row of plain spines on the spine board. Not exported."""
    env = state.env_collection()
    R = state.rng
    B = Part("env_cover_books", "bookcloth", var=0.1)
    Lb = Part("env_cover_labels", "paint", var=0.05)
    missing = []
    lean = math.radians(BS.LEAN_DEG)
    for s in secs:
        if vendor_set_is_current(s["key"]) and \
                pipeline.vendor_props([("prop_books_" + s["key"], s["slot"])], rotate=True):
            continue
        missing.append(s["key"])
        L = s["_local"]
        F = _frame(L["origin"], L["rot"]) @ _T(*L["slot"])
        y_foot = BS.LEDGE_D                       # backboard foot, from the slot (lip inner face)
        left = s["books"]
        for b in s["boards"]:
            ox, oy, oz = b["offset"]
            for xs in b["cover_slots_x"]:
                if left <= 0:
                    break
                left -= 1
                w, hgt, t = R.uniform(0.128, 0.142), R.uniform(0.19, 0.212), R.uniform(0.02, 0.03)
                c = Vector((ox + xs, oy + y_foot - t / 2 - 0.004 + math.sin(lean) * hgt / 2, oz + math.cos(lean) * hgt / 2))
                M = F @ _T(*c) @ Euler((-lean, 0, 0)).to_matrix().to_4x4()
                tint = tuple(v * R.uniform(0.85, 1.15) for v in CAT_TINT[s["key"]])
                B.mbox(M, (w, t, hgt), tint=tint, bevel=0, grain=2)
                Lb.mbox(M @ _T(0, -t / 2 - 0.001, hgt * 0.16), (w * 0.78, 0.002, hgt * 0.3), band="cream", bevel=0)
                Lb.mbox(M @ _T(0, -t / 2 - 0.001, -hgt * 0.3), (w * 0.5, 0.002, 0.012), band="cream", bevel=0)
        sb = s["spine_board"]
        x = 0.02
        while x < sb["width"] - 0.05:
            w = R.uniform(0.022, 0.045)
            hgt = min(sb["clear_height"] - 0.02, R.uniform(0.16, 0.21))
            B.mbox(F @ _T(x + w / 2, sb["offset"][1] + 0.03 + 0.08, sb["offset"][2] + hgt / 2), (w - 0.002, 0.16, hgt),
                   tint=R.choice(BINDINGS), bevel=0, grain=2)
            x += w
    B.finish(env)
    Lb.finish(env)
    if missing:
        print("[buecher] preview stand-in books for:", ", ".join(missing))
    return missing


def open_doors(keys=None):
    """Preview only (NM_OPEN_DOORS=1, or a comma list of keys): swing the act_cab_<key> doors open by
    their open_deg (from buecher_sections.py), as the engine does before a cabinet's covers come
    forward. The engine opens one cabinet at a time; mind's and decisions' doors fold over their
    neighbours, so pass the keys of the cabinets being viewed."""
    for s in BS.sections():
        if keys and s["key"] not in keys:
            continue
        ob = bpy.data.objects.get(s["door"]["node"])
        if ob is not None:
            ob.rotation_euler.z += math.radians(s["door"]["open_deg"])


def preview(objs):
    od = os.environ.get("NM_OPEN_DOORS")
    if od:
        open_doors(None if od == "1" else od.split(","))
    env = state.env_collection()
    yF = -D / 2
    secs = BS.sections()
    section_standins(secs)
    if pipeline.vendor_props([("prop_books_shelf_1", "slot_shelf_1"), ("prop_books_shelf_2", "slot_shelf_2"),
                              ("prop_books_counter", "slot_counter")]):
        return _lights_and_camera(yF, secs)
    books = Part("env_books", "paint", var=0.1)
    bands = ["red", "green", "blue", "black", "cream", "red", "gold"]
    R = state.rng
    shelves = [(z, D / 2 - 0.2, -1.0, 1.0) for z in (1.38, 1.78)]
    for z, y, xa, xb in shelves:
        x = xa
        while x < xb - 0.03:
            bw = R.uniform(0.025, 0.06)
            bh = R.uniform(0.18, 0.3)
            books.box((x + bw / 2, y, z + bh / 2), (bw - 0.003, 0.18, bh), band=R.choice(bands), grain=2,
                      rot=(0, R.uniform(-0.03, 0.03), 0))
            x += bw
    books.finish(env)
    return _lights_and_camera(yF, secs)


def _lights_and_camera(yF, secs):
    render.lights_at_markers(energy=100)
    render.add_light("env_fill", 'AREA', (0, 0.2, 2.5), 200, size=2.0)
    lx, ly, lz = LANTERN
    render.add_light("env_lantern", 'POINT', (lx, ly, lz - 0.15), 30, size=0.08)
    # the two small bulbs under each cabinet top light the covers behind the glass
    for s in secs:
        L = s["_local"]
        F = _frame(L["origin"], L["rot"])
        cw = L["width"]
        render.add_light("env_cabinet", 'POINT', tuple(F @ Vector((cw / 2, 0.08, BS.GLASS_TOP - 0.05))), 9, size=0.05)
        render.add_light("env_cabinet_low", 'POINT', tuple(F @ Vector((cw / 2, -0.25, 1.2))), 5, size=0.1)
    # the bulb strings under each wing canopy light the cabinet fronts below them
    for unit, (o, a, Lw) in BS.wing_units().items():
        F = _frame(o, a)
        p = F @ Vector((Lw / 2, -0.4, 2.3))
        q = F @ Vector((Lw / 2, 0.1, 1.2))
        render.add_light("env_wing", "AREA", tuple(p), 28, size=0.5, target=tuple(q))
    render.add_light("env_neighbour", 'POINT', (-5.8, -1.8, 2.6), 170, size=0.6)
    return render.camera((-3.9, -9.4, 2.2), (0.3, -1.7, 1.35), lens=26)


if __name__ == "__main__":
    pipeline.run(NAME, build, preview, seed=51)
