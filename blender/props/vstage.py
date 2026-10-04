"""Vendor render and bake stage: Cycles device setup, the per-set AO bake and the review previews
(render-only counter or shelf at night, camera shots, automatic framing for the deco frames).
Nothing here is exported; it works on the objects vlib.PropSet.finish() created."""
import math
import os

import bpy

from vlib import ATLAS_DIR, MODELS, state, world_bbox

# the vendor's own working files (AO maps, preview PNGs) live under blender/out/vendor/, never in the shared
# blender/out/renders/, where the carpenter's deco.py writes deco_<key>.png for the empty stalls
VENDOR_OUT = ATLAS_DIR
RENDERS = os.path.join(VENDOR_OUT, "renders")


def setup_device(scene=None, var="NM_DEVICE"):
    """Cycles device and threads from NM_DEVICE / NM_THREADS, as nmlib.render does for renders.
    The AO bake reads NM_BAKE_DEVICE first (falls back to NM_DEVICE): on the M3 a 256-512 px AO bake
    is about 4x faster on the CPU than on Metal, whose per-bake start-up dominates at that size."""
    scene = scene or bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    dev = os.environ.get(var, os.environ.get('NM_DEVICE', 'CPU')).upper()
    if dev in ('METAL', 'CUDA', 'OPTIX', 'HIP', 'ONEAPI'):
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = dev
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    threads = int(os.environ.get('NM_THREADS', '2'))
    if threads > 0:
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = threads
    else:
        scene.render.threads_mode = 'AUTO'


# materials that get no occlusion texture: see-through or self-lit
AO_SKIP = ("vendor_glass", "flame", "lamp_glow", "bulb_warm", "coal_glow", "vendor_beer", "vendor_liquid", "vendor_lamp_shade")


def bake_ao(name, res, samples=32, distance=0.12, floor=0.4):
    """Bake Cycles AO for every mesh of the set into one image on a second UV map "AO", and wire it
    as the glTF occlusion texture (TEXCOORD_1). Uses the carpenter's unwrap / post-process helpers
    from nmlib.bake; the target list and material filter are the vendor's own. The counter or shelf
    top is a temporary plane at z = 0 so goods get contact shading where they stand."""
    import time
    from nmlib import bake as nb
    t0 = time.time()
    targets = [o for o in state.export_collection().all_objects if o.type == 'MESH' and o.data.polygons]
    if not targets:
        return None
    scene = bpy.context.scene
    setup_device(scene, "NM_BAKE_DEVICE")
    tiny = nb.unwrap_ao(targets, res=res, margin_px=1.5 if res >= 512 else 1.0, tiny_area=2e-5)
    img = bpy.data.images.new(f"{name}_ao", res, res)
    img.colorspace_settings.name = "Non-Color"
    me = bpy.data.meshes.new("ao_ground")
    s = 4.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("ao_ground", me)
    scene.collection.objects.link(ground)
    world = scene.world or bpy.data.worlds.new("bakeworld")
    scene.world = world
    world.light_settings.distance = distance
    scene.cycles.samples = samples
    scene.render.bake.margin = 2
    mats = []
    for o in targets:
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
    nodes = {}
    for m in mats:
        tn = m.node_tree.nodes.new("ShaderNodeTexImage")
        tn.image = img
        m.node_tree.nodes.active = tn
        nodes[m] = tn
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in targets:
        o.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    bpy.ops.object.bake(type='AO', margin=2, use_clear=True)
    mask = nb._coverage_mask(targets, tiny, res)
    raw_mean, out_mean = nb._postprocess(img, mask, res, floor=floor)
    path = os.path.join(VENDOR_OUT, "ao", f"{name}_ao.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    grp = nb._gltf_output_group()
    for m, tn in nodes.items():
        nt = m.node_tree
        if m.name.startswith(AO_SKIP):
            nt.nodes.remove(tn)
            continue
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "AO"
        nt.links.new(uv.outputs[0], tn.inputs[0])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tn.outputs["Color"], sep.inputs[0])
        gn = nt.nodes.new("ShaderNodeGroup")
        gn.node_tree = grp
        nt.links.new(sep.outputs[0], gn.inputs[0])
    bpy.data.objects.remove(ground, do_unlink=True)
    print(f"[props] AO {name} {res}px, {len(targets)} meshes in {time.time() - t0:.1f}s: "
          f"islands cover {mask.mean():.0%}, mean {raw_mean:.2f} -> {out_mean:.2f}")
    return img


def env_section(boards, slot_z):
    """Render-only stand-in for one Bücherstand category bay (blender/stalls/buecher_sections.json): its boards
    at their offsets from slot_cat_<key> (left end, front edge, top surface), uprights at both ends and a back
    board, standing on a dark floor at the slot's real height. Returns the slot height."""
    from nmlib.geo import Part
    env = state.env_collection()
    frame = Part("env_section_frame", "wood")
    wood = Part("env_section_wood", "wood")
    x1 = max(b["offset"][0] + b["width"] for b in boards)
    y1 = max(b["offset"][1] + b["depth"] for b in boards)
    ztop = max(b["offset"][2] for b in boards) + 0.42
    for b in boards:
        ox, oy, oz = b["offset"]
        t = 0.025
        frame.box((ox + b["width"] / 2, oy + b["depth"] / 2, slot_z + oz - t / 2), (b["width"] + 0.08, b["depth"], t),
                  tint="pine")
        # back board, 42 cm tall, but no higher than a board stepped back behind it (a cart's upper tier):
        # a full-height back on the lower tier hid the upper tier's spines in the cart previews
        bh = 0.42
        for bb in boards:
            if bb["offset"][2] > oz and bb["offset"][1] >= oy + b["depth"] - 0.02:
                bh = min(bh, bb["offset"][2] - oz - 0.026)
        frame.box((ox + b["width"] / 2, oy + b["depth"] + 0.01, slot_z + oz - 0.01 + bh / 2),
                  (b["width"] + 0.08, 0.02, bh), tint="honey")
    for sx in (-0.02, x1 + 0.02):
        frame.box((sx, y1 / 2, (slot_z + ztop) / 2), (0.04, y1 + 0.02, slot_z + ztop), tint="pine")
    x = -1.6
    while x < x1 + 1.6:
        w = 0.15
        wood.box((x + w / 2, y1 + 0.35, 1.4), (w - 0.005, 0.02, 2.8), tint="honey", grain=2, var=0.1)
        x += w
    wood.box((x1 / 2, 0, 0.01), (x1 + 3.2, 4.0, 0.02), tint="dark")
    wood.finish(env)
    frame.finish(env)
    return slot_z


def env_counter(kind="counter", width=3.0):
    """Render-only surroundings: a plain wooden counter (or shelf) in a stall interior at night."""
    from nmlib import render
    from nmlib.geo import Part
    env = state.env_collection()
    wood = Part("env_counter_wood", "wood")
    frame = Part("env_counter_frame", "wood")
    top = 1.05
    if kind == "counter":
        for i, (y, t) in enumerate(((-0.17, "oak"), (0.0, "oak"), (0.17, "oak"))):
            frame.box((0, y, top - 0.025), (width, 0.166, 0.05), tint=t, bevel=0.005, bevel_segments=2, var=0.1)
        frame.box((0, -0.262, top - 0.06), (width + 0.02, 0.024, 0.09), tint="oak")
        x = -width / 2
        while x < width / 2:
            w = 0.14
            wood.box((x + w / 2, -0.22, top / 2 - 0.05), (w - 0.006, 0.02, top - 0.12), tint="honey", grain=2, var=0.08)
            x += w
        back_y = 1.1
    else:
        # shelf board at the slot height with the one above, brackets, a back wall right behind
        top = 1.38 if kind == "shelf" else 1.78          # "shelf2": the upper shelf, nothing above it
        for z in ((top, top + 0.4) if kind == "shelf" else (top,)):
            frame.box((0, 0, z - 0.015), (width, 0.3, 0.03), tint="pine")
            frame.box((0, -0.145, z + 0.02), (width, 0.015, 0.05), tint="pine")
        frame.box((0, -1.0, 1.05 - 0.025), (width, 0.5, 0.05), tint="oak")     # counter in the foreground
        back_y = 0.165
    x = -width / 2 - 0.5
    while x < width / 2 + 0.5:
        w = 0.15
        wood.box((x + w / 2, back_y + 0.01, 1.4), (w - 0.005, 0.02, 2.8), tint="honey", grain=2, var=0.1)
        x += w
    # floor and side walls to hold the light in
    wood.box((0, 0, 0.01), (width + 1.2, 3.0, 0.02), tint="dark")
    for sx in (-1, 1):
        wood.box((sx * (width / 2 + 0.6), 0.0, 1.4), (0.02, 3.0, 2.8), tint="honey", grain=2)
    wood.finish(env)
    frame.finish(env)
    return top


def preview_scene(ps, kind="counter", width=3.0, extra_lights=(), section=None):
    """Render-only surroundings and lights for a set; returns the counter / shelf top height.
    kind "section": a Bücherstand category bay; `section` = (boards, slot_z) from buecher_sections.json."""
    from nmlib import render
    render.night_scene(ground_size=30)
    if kind == "section":
        top = env_section(*section)
        ps.objs[ps.name].location = (0, 0, top)
        bpy.context.view_layer.update()
        x1 = max(b["offset"][0] + b["width"] for b in section[0])
        render.add_light("env_light_0", 'POINT', (x1 / 2, -0.9, top + 1.3), 90, size=0.25)
        render.add_light("env_light_1", 'POINT', (x1 / 2 - 1.2, -1.6, top + 0.9), 60, size=0.25)
        render.add_light("env_fill", 'AREA', (x1 / 2 - 0.3, -1.3, top + 0.5), 40, (1.0, 0.72, 0.48), size=1.2,
                         rot=(math.radians(70), 0, math.radians(-12)))
        render.add_light("env_rim", 'POINT', (x1 + 0.6, -0.3, top + 0.8), 10, (1.0, 0.7, 0.45), size=0.2)
        return top
    top = env_counter(kind, width)
    ps.objs[ps.name].location = (0, 0, top)
    bpy.context.view_layer.update()
    # the stall's two real-time light spots (light_0 inside above the vendor, light_1 on the front beam),
    # given relative to this slot, plus a soft warm fill from the visitor's side
    if kind == "counter":
        l0, l1 = (0, 1.27, 1.25), (0, -0.78, 1.3)
    else:
        l0, l1 = (0, -0.96, 0.92), (0, -3.0, 0.97)
    render.add_light("env_light_0", 'POINT', (l0[0], l0[1], top + l0[2]), 110, size=0.25)
    render.add_light("env_light_1", 'POINT', (l1[0], l1[1], top + l1[2]), 110, size=0.25)
    render.add_light("env_fill", 'AREA', (-0.4, -1.3, top + 0.7), 45, (1.0, 0.72, 0.48), size=1.2,
                     rot=(math.radians(62), 0, math.radians(-15)))
    render.add_light("env_rim", 'POINT', (1.4, 0.2, top + 0.9), 14, (1.0, 0.7, 0.45), size=0.2)
    for L in extra_lights:
        render.add_light(*L)
    return top


def shot(cam, top, out_jpg, samples=128, res=(1920, 1080), png_name=None):
    """Render one camera (loc, target, lens) given relative to the slot. The PNG goes to the vendor's own
    blender/out/vendor/renders/<png_name or the jpeg's name>.png, the JPEG to review/."""
    from nmlib import render
    loc, tgt, lens = cam
    render.camera((loc[0], loc[1], loc[2] + top), (tgt[0], tgt[1], tgt[2] + top), lens=lens, dof=None)
    os.makedirs(RENDERS, exist_ok=True)
    png = os.path.join(RENDERS, (png_name or os.path.basename(out_jpg).replace(".jpg", "")) + ".png")
    beer_preview()
    glass_no_shadow()
    render.render(png, samples=samples, res=res, jpeg=out_jpg, jpeg_width=1280)
    return png


def beer_preview():
    """Preview only (round 4): the beer is opaque in the glb, because a three.js transmissive glass cannot
    show a transmissive liquid behind it. Cycles can, so the previews let a part of the light through the
    column (Transmission 0.6): the lit golden body the browser shows, with the depth and the refracted
    counter of a clear lager behind it. Full transmission went dark olive here (the column refracts the
    unlit wall behind it and the stall has no back light); round 3's 0.65 on an orange base read as opaque
    orange. The meshes it is on stop casting shadows with the glass (glass_no_shadow). Nothing exported
    changes: the previews render after the glbs are written."""
    mt = bpy.data.materials.get("vendor_beer")
    if not mt or mt.get("preview_clear"):
        return
    b = mt.node_tree.nodes.get("Principled BSDF")
    for k, v in (("Transmission Weight", 0.6), ("Roughness", 0.03)):
        if k in b.inputs:
            b.inputs[k].default_value = v
    mt["preview_clear"] = True


def glass_no_shadow():
    """Preview only: Cycles blocks shadow rays at transmission glass, so beer, foam and anything else behind a
    glass wall is lit only by noisy caustics and reads dark (the beer heads' band showed as a tan collar).
    Thin glass passes nearly all light, and the browser's transmission glass casts no shadow either, so meshes
    with a transmission glass material do not cast shadows in the previews. Nothing exported changes."""
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        for slot in o.material_slots:
            mt = slot.material
            b = mt and mt.use_nodes and mt.node_tree.nodes.get("Principled BSDF")
            if b and "Transmission Weight" in b.inputs and b.inputs["Transmission Weight"].default_value > 0.9:
                o.visible_shadow = False
                break


def frame_cam(ps, lens=35, elev=0.33, margin=1.12, aspect=16 / 9):
    """A front camera that frames the whole set (slot-relative), for the deco frames."""
    lo, hi = world_bbox([o for o in ps.objs.values()])
    top = ps.objs[ps.name].location.z
    c = (lo + hi) / 2
    half_w = (hi.x - lo.x) / 2 * margin
    half_h = (hi.z - lo.z) / 2 * margin
    tan_h = 18.0 / lens
    tan_v = tan_h / aspect
    d = max(half_w / tan_h, half_h / tan_v * 1.05) + (hi.y - lo.y) / 2
    loc = (c.x, c.y - d * math.cos(elev), c.z - top + d * math.sin(elev))
    return (loc, (c.x, c.y, c.z - top), lens)




def stall_scene(ps, stall_glb, extra_lights=()):
    """Render-only: the carpenter's shipped stall glb with this set at its slot (the slot_ empty named by
    ps.slot), the stall's light_ empties lit as warm Cycles point lights, a soft fill from the visitor's side.
    Returns the slot's world position (the set origin), for shot(..., origin=)."""
    from mathutils import Vector
    from nmlib import render
    env = state.env_collection()
    for o in list(env.all_objects):                          # drop the plain-counter stage and its lights
        bpy.data.objects.remove(o, do_unlink=True)
    render.night_scene(ground_size=30)
    objs = render.import_glb(os.path.join(MODELS, stall_glb), at=(0, 0, 0))
    bpy.context.view_layer.update()
    slot = next((o for o in objs if o.name.split(".")[0] == ps.slot), None)
    if slot is None:
        raise RuntimeError(f"{stall_glb} has no {ps.slot}")
    origin = slot.matrix_world.translation.copy()
    ps.objs[ps.name].location = origin
    bpy.context.view_layer.update()
    n = 0
    for o in objs:
        if o.name.startswith("light_"):
            render.add_light(f"env_{o.name}", 'POINT', tuple(o.matrix_world.translation), 70, (1.0, 0.72, 0.45),
                             size=0.2)
            n += 1
    render.add_light("env_fill", 'AREA', tuple(origin + Vector((-0.4, -1.6, 0.8))), 40, (1.0, 0.72, 0.48), size=1.4,
                     rot=(math.radians(62), 0, math.radians(-15)))
    for L in extra_lights:
        name, kind, loc, *rest = L
        render.add_light(name, kind, tuple(origin + Vector(loc)), *rest)
    print(f"[props] staged {ps.name} in {stall_glb} at {tuple(round(v, 3) for v in origin)} with {n} stall lights")
    return origin


def shot_at(cam, origin, out_jpg, samples=128, res=(1920, 1080), png_name=None):
    """Like shot(), with the camera given relative to a full 3D origin (the set's slot in a stall scene)."""
    from mathutils import Vector
    from nmlib import render
    loc, tgt, lens = cam
    render.camera(tuple(origin + Vector(loc)), tuple(origin + Vector(tgt)), lens=lens, dof=None)
    os.makedirs(RENDERS, exist_ok=True)
    png = os.path.join(RENDERS, (png_name or os.path.basename(out_jpg).replace(".jpg", "")) + ".png")
    beer_preview()
    glass_no_shadow()
    render.render(png, samples=samples, res=res, jpeg=out_jpg, jpeg_width=1280)
    return png

