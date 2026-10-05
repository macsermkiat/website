"""Round 8 previews: each deco stall (and the ornament shop) with all its prop sets standing at their slots.

    NM_DEVICE=CPU NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/props/render_stalls.py \
        lebkuchen,mandeln,... [--res 640x360] [--samples 32] [--cam view|close|shelf|tree|case] [--sheet]

Reads site/public/models/props.json, imports the stall glb (deco_<key>.glb) and every set listed for that
stall (full glbs, decoded), parents each set's root at its slot empty, lights the stall's light_ empties as
warm point lights with a soft fill from the lane, and renders from in front of the stall. Frames go to
blender/out/vendor/renders/stall_<key>[_<cam>].png and review/round-9/vendor/stall_<key>[_<cam>].jpg.
--sheet builds review/round-9/vendor/deco_goods_contact_sheet.jpg from the eight deco frames (view cam).
Render only: nothing in site/public/models changes.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vlib  # noqa: E402  (bpy, nmlib)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from nmlib import render, state  # noqa: E402

MODELS = vlib.MODELS
REVIEW = vlib.REVIEW
RENDERS = os.path.join(vlib.ATLAS_DIR, "renders")
LABEL = {"lebkuchen": "Lebkuchen", "mandeln": "Gebrannte Mandeln", "kerzen": "Kerzen", "spielzeug": "Holzspielzeug",
         "kaese": "Käse", "crepes": "Crêpes", "maroni": "Heiße Maroni", "puffer": "Kartoffelpuffer",
         "schmuck": "Christbaumschmuck (ornament shop)"}
# camera (location, target, lens) in the stall's frame (Blender, front toward -Y; counter top 1.05 at y -1.05)
CAMS = {
    "view": ((0.9, -4.6, 1.75), (0.0, -0.5, 1.35), 30),
    "close": ((0.55, -2.55, 1.6), (0.0, -0.6, 1.3), 30),
    "shelf": ((0.2, -2.1, 1.75), (0.0, 0.9, 1.62), 32),
    "tree": ((-0.2, -4.3, 1.2), (-1.0, -1.6, 0.75), 32),
}
# the ornament shop (stall_schmuck.glb) is 4.5 m wide: counter at y -1.22, glass case left, tree dais right
CAMS_SCHMUCK = {
    "view": ((0.6, -5.6, 1.8), (0.0, -0.7, 1.45), 30),
    "close": ((0.35, -3.4, 1.75), (0.0, -0.9, 1.7), 28),     # round 9: counter, harmonica and the valance's Lametta
    "shelf": ((0.2, -2.6, 1.8), (0.0, 1.0, 1.6), 30),
    "tree": ((0.9, -3.4, 1.35), (1.65, -0.9, 1.0), 32),
    "case": ((-1.2, -2.9, 1.35), (-1.73, -1.1, 1.05), 32),
}


def args():
    a = sys.argv[1:]
    keys = [k for k in (a[0].split(",") if a and not a[0].startswith("--") else [])]
    get = lambda f, d: a[a.index(f) + 1] if f in a else d
    return keys, tuple(int(v) for v in get("--res", "640x360").split("x")), int(get("--samples", "32")), \
        get("--cam", "view"), "--sheet" in a, "--lite" in a


def stage(key, lite=False):
    state.reset(1)
    render.night_scene(ground_size=30)
    with open(os.path.join(MODELS, "props.json")) as f:
        pj = json.load(f)
    stall_id = "deco-" + ("kartoffelpuffer" if key == "puffer" else key)
    sets = [e for e in pj["sets"] if e["stall"] == stall_id]
    asset = sets[0]["asset"] if sets else f"deco_{key}.glb"
    if lite:
        asset = asset.replace(".glb", ".lite.glb")
    objs = render.import_glb(os.path.join(MODELS, asset), at=(0, 0, 0))
    bpy.context.view_layer.update()
    slots = {o.name.split(".")[0]: o for o in objs if o.name.startswith("slot_")}
    for e in sets:
        slot = slots.get(e["slot"])
        if slot is None:
            print(f"[stalls] {asset} has no {e['slot']} for {e['set']}")
            continue
        new = render.import_glb(os.path.join(MODELS, e["lite"] if lite else e["model"]), at=(0, 0, 0))
        for o in new:
            if o.parent is None:
                o.matrix_world = slot.matrix_world @ o.matrix_world
        print(f"[stalls] {e['set']} at {e['slot']}")
    n = 0
    schmuck = key == "schmuck"
    for o in objs:
        if o.name.startswith("light_"):
            # round 9 pass 2, the ornament shop: the carpenter's own preview lighting for stall_schmuck (small
            # 150 W points at the light_ markers, sharp highlights on the glass; blender/stalls/schmuck.py)
            render.add_light(f"env_{o.name}", 'POINT', tuple(o.matrix_world.translation), 150 if schmuck else 55,
                             (1.0, 0.72, 0.45), size=0.06 if schmuck else 0.25)
            n += 1
    # a warm fill from the lane (the market's string lights and lamps), and a low one on the front crate
    render.add_light("env_fill", 'AREA', (0.6, -3.4, 2.6), 160, (1.0, 0.74, 0.5), size=2.2,
                     rot=(math.radians(58), 0, math.radians(8)))
    render.add_light("env_low", 'AREA', (0.0, -3.2, 0.7), 35, (1.0, 0.72, 0.48), size=1.5,
                     rot=(math.radians(80), 0, 0))
    if schmuck:
        # render-only, as the carpenter's preview does: the lane fill panels stand right in front of the back-wall
        # mirror, so they must not show in it (round 9 pass 1 rendered them as a white sheet behind the shelves,
        # which turned the shelf goods into silhouettes; the engine has no such panel), plus his soft fill inside
        # the canopy and the small lights in the glass case and over the tree
        render.add_light("env_fill_in", 'AREA', (0, 0.2, 2.55), 45, (1.0, 0.72, 0.45), size=2.4)
        sl = json.load(open(os.path.join(vlib.REPO, "blender", "stalls", "schmuck_slots.json")))["slots"]
        cp, tp = Vector(sl["slot_cabinet"]["position"]), Vector(sl["slot_tree"]["position"])
        render.add_light("env_case", 'POINT', tuple(cp + Vector((0, 0.05, 0.5))), 12, (1.0, 0.72, 0.45), size=0.05)
        render.add_light("env_tree", 'POINT', tuple(tp + Vector((0, -0.45, 0.8))), 9, (1.0, 0.72, 0.45), size=0.3)
        mirrors = [ob for ob in bpy.data.objects if ob.name.startswith("mirror_") and ob.type == 'MESH']
        excl = bpy.data.collections.new("env_mirror_excl")
        for ob in mirrors:
            excl.objects.link(ob)
        for ob in bpy.data.objects:
            if ob.name.startswith("env_fill_in"):
                ob.visible_glossy = False
            elif ob.name.startswith(("env_fill", "env_low")) and mirrors:
                # the lane panels still light (and glint in) the goods, the tinsel and the angels' foil, but the
                # mirror does not receive them (Cycles light linking), so they do not show in it
                ob.light_linking.receiver_collection = excl
                for c in excl.collection_objects:
                    c.light_linking.link_state = 'EXCLUDE'
        print(f"[stalls] schmuck: lane fill kept out of {[o.name for o in mirrors]}")
    return n


def main():
    keys, res, samples, cam, sheet, lite = args()
    os.makedirs(RENDERS, exist_ok=True)
    for key in keys:
        stage(key, lite)
        loc, tgt, lens = (CAMS_SCHMUCK if key == "schmuck" else CAMS)[cam]
        render.camera(loc, tgt, lens=lens, dof=None)
        tag = ("" if cam == "view" else f"_{cam}") + ("_lite" if lite else "")
        png = os.path.join(RENDERS, f"stall_{key}{tag}.png")
        render.render(png, samples=samples, res=res, jpeg=os.path.join(REVIEW, f"stall_{key}{tag}.jpg"), jpeg_width=1280)
    if sheet:
        deco = ["lebkuchen", "mandeln", "kerzen", "spielzeug", "kaese", "crepes", "maroni", "puffer", "schmuck"]
        frames = [(os.path.join(RENDERS, f"stall_{k}.png"), LABEL[k]) for k in deco
                  if os.path.exists(os.path.join(RENDERS, f"stall_{k}.png"))]
        out = os.path.join(REVIEW, "deco_goods_contact_sheet.jpg")
        render.contact_sheet(frames, out, cols=3, tile=(416, 234),
                             title="Deco stalls stocked from the lane: counter, rail, both shelves, front crate (vendor, round 8)")
        print(f"[stalls] wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
