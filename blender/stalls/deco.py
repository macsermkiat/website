"""Deco stall kit: nine scenery stalls from one parametric hut.

Each variant is a structure with its sign, slots, one light_ empty, eave bulbs and snow caps,
but no goods (the vendor supplies goods at the slot_ empties). All variants use the same kit
materials, and the kit textures are written once, outside the glb files, as
site/public/models/deco_kit_*.webp (and *.lite.webp); every deco glb references them by URI,
so the browser downloads them once. Only each variant's small AO map is embedded.

    /home/claude/tools/bpy-venv/bin/python blender/stalls/deco.py [--only lebkuchen,kaese] [--no-render]
Outputs site/public/models/deco_<key>.glb + deco_<key>.lite.glb, and a contact sheet in review/.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

import pipeline  # noqa: E402
from hut import COUNTER_TOP, Hut  # noqa: E402
from nmlib import carpentry as cp  # noqa: E402
from nmlib import render, state  # noqa: E402

# key: sign text, width, walls, trim colour, valance, sign style, roof, extras
VARIANTS = {
    "lebkuchen": dict(text="Lebkuchen", W=3.0, wall="batten", wall_tint="honey", trim="red", accent="white",
                      valance=("scallop", "heart"), sign="fascia", board=("arch", "red", "cream"),
                      font="fraktur_bold", roof="shingles", roof_tint="shingle"),
    "mandeln": dict(text="Gebrannte Mandeln", W=3.4, wall="vertical", wall_tint="pine", trim="green",
                    accent="cream", valance=("point", None), sign="crest", board=("rect", "cream", "green"),
                    font="alegreya_sc", roof="shingles", roof_tint="oak", awning="cream"),
    "kerzen": dict(text="Kerzen", W=2.6, wall="lap", wall_tint="dark", trim="cream", accent="gold",
                   valance=("wave", "circle"), sign="fascia", board=("oval", "cream", "black"),
                   font="fell_italic", roof="shingles", roof_tint="walnut"),
    "spielzeug": dict(text="Holzspielzeug", W=3.2, wall="batten", wall_tint="pine", trim="blue", accent="red",
                      valance=("step", None), sign="crest", board=("rect", "blue", "cream"),
                      font="alegreya_sc", roof="shingles", roof_tint="shingle", awning="blue"),
    "schmuck": dict(text="Christbaumschmuck", W=3.4, wall="vertical", wall_tint="oak", trim="green",
                    accent="gold", valance=("scallop", "star"), sign="crest", board=("arch", "cream", "green"),
                    font="alegreya_sc", roof="shingles", roof_tint="dark"),
    "kaese": dict(text="Käse", W=2.8, wall="lap", wall_tint="honey", trim="cream", accent="black",
                  valance=("point", "circle"), sign="fascia", board=("banner", "cream", "black"),
                  font="fraktur_bold", roof="boards", roof_tint="oak"),
    "crepes": dict(text="Crêpes", W=2.8, wall="vertical", wall_band="white", wall_tint="white", trim="blue",
                   accent="red", valance=("wave", None), sign="fascia", board=("rect", "blue", "white"),
                   font="fell_italic", roof="shingles", roof_tint="grey"),
    "maroni": dict(text="Heiße Maroni", W=2.6, wall="lap", wall_tint="soot", trim="black", accent="red",
                   valance=("step", None), sign="crest", board=("rect", "black", "cream"),
                   font="alegreya_sc", roof="boards", roof_tint="dark", stove=True),
    "puffer": dict(text="Kartoffelpuffer", W=3.2, wall="lap", wall_tint="oak", trim="red", accent="cream",
                   valance=("scallop", None), sign="crest", board=("banner", "cream", "red"),
                   font="alegreya_sc", roof="shingles", roof_tint="shingle", stove=True),
}
D, EAVE, RIDGE = 2.2, 2.62, 3.4
# AO atlas size of the full deco builds. It must differ from every kit texture size (1024, and
# 512 for iron): when the AO image has the same size as a kit roughness/metal map, the glTF
# exporter packs AO into that map (ORM) and the glb embeds its own copy instead of sharing
# deco_kit_iron_rm.webp. Lite: 256 (the lite kit maps are 512).
DECO_AO = 448
SEEDS = {k: 100 + i * 7 for i, k in enumerate(VARIANTS)}


lamp_spots = []   # sign-lamp positions of the last build, for the preview's spot lights


def build_variant(key, lite):
    lamp_spots.clear()
    v = VARIANTS[key]
    W = v["W"]
    h = Hut(f"deco_{key}", W=W, D=D, eave=EAVE, ridge=RIDGE, ridge_axis='x', ov_eave=0.32, ov_gable=0.2,
            wall=v["wall"], wall_tint=v["wall_tint"], frame_tint="walnut" if v["wall_tint"] != "walnut" else "dark",
            roof=v["roof"], roof_tint=v["roof_tint"], inner_tint="pine", counter_tint="oak",
            counter_depth=0.5, counter_over=0.2, shelves=(1.4, 1.8), bulb_spacing=0.22,
            wall_band=v.get("wall_band"), plank_w=0.15, plank_bevel=0.0, shingle_size=(0.26, 0.19),
            bulb_detail=(6, 4))
    yF = h.yF
    P = h.paint
    trim, accent = v["trim"], v["accent"]
    h.build_carcass()
    h.build_counter(brackets=3, grid=0.28)
    h.build_shelves()
    h.build_roof(fascia_band=trim, barge_band=trim)
    h.build_snow()
    # painted front posts, rails and counter lip in the trim colour
    for x in h.front_posts:
        P.box((x, yF - 0.008, (COUNTER_TOP + 2.2) / 2), (0.115, 0.018, 2.2 - COUNTER_TOP), band=trim, grain=2)
    for z in (0.28, 0.82):
        P.box((0, yF - 0.032, z), (W - 0.14, 0.022, 0.09), band=trim)
    P.box((0, yF - h.counter_over - 0.026, COUNTER_TOP - 0.05), (W - 0.1, 0.02, 0.07), band=accent)
    # valance under the front eave
    sl = h.front_slope
    ez = sl.point(0, 0, -0.03).z - 0.05
    style, holes = v["valance"]
    n = max(5, int((sl.a1 - sl.a0) / 0.36))
    cp.valance(P, sl.a0 + 0.02, sl.a1 - 0.02, sl.point(0, 0).y + 0.03, ez, 0.12, 0.09, n, style=style,
               holes=holes, band=trim, depth=0.02)
    # awning flap propped on iron stays
    if v.get("awning"):
        ang = math.radians(18)
        hinge = Vector((0, yF - 0.04, 2.3))
        L = 0.75
        d = Vector((0, -math.cos(ang), math.sin(ang)))
        c = hinge + d * (L / 2)
        M = Matrix.Translation(c) @ Matrix((Vector((1, 0, 0)), d, Vector((1, 0, 0)).cross(d))).transposed().to_4x4()
        nb = 6 if not lite else 3
        for i in range(nb):
            x = -(W - 0.3) / 2 + (i + 0.5) * (W - 0.3) / nb
            M_i = Matrix.Translation(Vector((x, 0, 0))) @ M
            P.mbox(M_i, ((W - 0.3) / nb - 0.006, L, 0.022), band=v["awning"], grain=1)
        for x in (-(W - 0.5) / 2, (W - 0.5) / 2):
            h.iron.slab((x, yF - 0.03, 1.75), tuple(hinge + d * (L * 0.85) + Vector((x, 0, -0.02))), 0.02, 0.012,
                        up=(1, 0, 0))
        tip = hinge + d * L
        cp.bulb_string(h.bulbs, h.wire, [(-(W - 0.3) / 2, tip.y, tip.z - 0.02), (0, tip.y, tip.z - 0.02),
                                         ((W - 0.3) / 2, tip.y, tip.z - 0.02)], sag=0.03, spacing=0.22, seg=6, rings=4)
    # small stove pipe for the hot-food stalls
    if v.get("stove"):
        x, y = W / 2 - 0.55, 0.35
        top = RIDGE + 0.55
        zr = RIDGE - abs(y) * math.tan(h.pitch)
        h.iron.cyl((x, y, (1.6 + top) / 2), 0.075, 0.075, top - 1.6, seg=12, caps=False)
        h.iron.cyl((x, y, top + 0.12), 0.17, 0.02, 0.1, seg=12)
        for a in range(3):
            ang = a * 2 * math.pi / 3
            h.iron.box((x + 0.06 * math.cos(ang), y + 0.06 * math.sin(ang), top + 0.04), (0.01, 0.01, 0.12), bevel=0)
        h.iron.cyl((x, y, zr + 0.06), 0.14, 0.09, 0.07, seg=12)
    # sign: big, high-contrast letters so the word reads from the lane
    shape, board_band, text_band = v["board"]
    fnt = state.font(v["font"])
    if v["sign"] == "crest":
        ys = -0.35
        z_roof = RIDGE - abs(ys) * math.tan(h.pitch) + 0.05
        sw = min(W + 0.1, 0.6 + 0.26 * len(v["text"]))
        sh = 0.56 if shape != "banner" else 0.6
        sign_c = Vector((0, ys, z_roof + sh / 2 + 0.12))
        cp.sign(P, P, v["text"], fnt, sign_c, sw, sh, depth=0.045, board_band=board_band, text_band=text_band,
                frame_band=accent if accent not in (board_band, text_band) else None, board_shape=shape,
                text_size=sh * 0.8, max_fill=0.9 if shape != "banner" else 0.76, text_depth=0.014, resolution=1,
                text_bevel=0.0, text_dy=-0.03 if shape == "arch" else 0.0)
        lamp_x = (-sw * 0.3, sw * 0.3)
        h.sign_lamps(lamp_x, ys - 0.03, sign_c.z + sh / 2 + 0.06, reach=0.3)
        lamp_spots.extend([((x, ys - 0.33, sign_c.z + sh / 2 + 0.2), (x * 0.4, ys, sign_c.z)) for x in lamp_x])
        for x in (-sw / 2 + 0.2, sw / 2 - 0.2):
            h.iron.box((x, ys + 0.03, z_roof + 0.05), (0.028, 0.028, 0.2), bevel=0)
            a = Vector((x, ys + 0.04, sign_c.z + 0.08))
            b = Vector((x, ys + 0.42, RIDGE - abs(ys + 0.42) * math.tan(h.pitch) + 0.06))
            h.iron.slab(a, b, 0.022, 0.012, up=(1, 0, 0))
    else:  # fascia sign: hung on the front of the valance at the eave, two small lamps above it
        sw = min(W - 0.2, 0.8 + 0.3 * len(v["text"]))
        sh = 0.54
        e = sl.point(0, 0)
        sign_c = Vector((0, e.y - 0.035, ez - 0.02))
        cp.sign(P, P, v["text"], fnt, sign_c, sw, sh, depth=0.032, board_band=board_band, text_band=text_band,
                frame_band=accent if shape == "rect" and accent not in (board_band, text_band) else None,
                board_shape=shape, text_size=sh * 0.82, max_fill=0.86 if shape != "banner" else 0.74,
                text_depth=0.014, resolution=1, text_bevel=0.0)
        lamp_x = (-sw * 0.28, sw * 0.28)
        h.sign_lamps(lamp_x, sign_c.y + 0.01, sign_c.z + sh / 2 + 0.03, reach=0.22)
        lamp_spots.extend([((x, sign_c.y - 0.25, sign_c.z + sh / 2 + 0.16), (x * 0.4, sign_c.y, sign_c.z))
                           for x in lamp_x])
    if v["sign"] == "crest" or v.get("awning"):
        h.eave_bulbs(sides=False)
    else:
        e = sl.point(0, 0, -0.08)
        y = sl.point(0, 0).y - 0.02
        for xa, xb in ((sl.a0 + 0.05, -sw / 2 - 0.05), (sw / 2 + 0.05, sl.a1 - 0.05)):
            cp.bulb_string(h.bulbs, h.wire, [(xa, y, e.z), ((xa + xb) / 2, y, e.z), (xb, y, e.z)], sag=0.04,
                           spacing=0.22, seg=6, rings=4)
    h.interior_bulbs(xs=(-0.6, 0.6), z=2.3)
    h.markers(sign_pos=tuple(sign_c + Vector((0, -0.05, 0))), lights=[(0, -0.2, 2.3)], cam_dist=3.2, cam_h=1.7)
    return h.finish()


def main():
    a = pipeline.args()
    only = None
    for i, t in enumerate(sys.argv):
        if t == "--only":
            only = sys.argv[i + 1].split(",")
    keys = [k for k in VARIANTS if not only or k in only]
    renders = []
    reports = {}
    for key in keys:
        name = f"deco_{key}"
        build = (lambda k: (lambda lite: build_variant(k, lite)))(key)
        for lite in (True, False):
            if (lite and a.no_lite) or (not lite and a.no_full):
                continue
            objs, rep = pipeline.build_and_export(
                name, build, SEEDS[key], lite, ao_res=256 if lite else DECO_AO,
                externalize="kit")
            reports[name + (".lite" if lite else "")] = rep
        if not a.no_render and not a.no_full:
            render.night_scene(ground_size=24)
            render.lights_at_markers(energy=120)
            render.add_light("env_fill", 'AREA', (0, 0.1, 2.35), 90, size=1.8)
            for p, t in lamp_spots:
                render.add_light("env_signlamp", 'SPOT', p, 60, size=0.1, spot_size=math.radians(110),
                                 spot_blend=1.0, target=t)
            render.add_light("env_neighbour", 'POINT', (-4.2, -1.4, 2.6), 120, size=0.6)
            render.camera((-3.0, -5.2, 2.15), (0.1, -0.5, 2.2), lens=30)
            png = os.path.join(state.OUT_DIR, "renders", f"{name}.png")
            render.render(png, samples=a.samples, res=(840, 600))
            renders.append((png, VARIANTS[key]["text"]))
    if renders and not only:
        os.makedirs(pipeline.REVIEW, exist_ok=True)
        render.contact_sheet(renders, os.path.join(pipeline.REVIEW, "deco_contact_sheet.jpg"), cols=3,
                             tile=(420, 300), title="Deco stall kit: nine variants, shared kit textures")
    import json
    with open(os.path.join(state.OUT_DIR, "deco_report.json"), "w") as f:
        json.dump(reports, f, indent=1)
    for k, r in reports.items():
        print(f"[deco] {k}: {r['bytes'] / 1e6:.2f} MB, {r['triangles']} tris")


if __name__ == "__main__":
    main()
