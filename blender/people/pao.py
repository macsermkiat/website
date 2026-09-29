"""Ambient occlusion for the organizer's figures, baked into the glTF occlusion texture.

Each figure gets a second UV map "AO" (TEXCOORD_1, non-overlapping, packed for this figure only) and one
small AO image (256 px full, 128 px lite) shared by all its materials (body, coat, scarf, hat, mug). The
fabric normal maps keep tiling on "UVMap" (TEXCOORD_0). No lighting goes into base colour, so the engine
can still recolour coat, scarf and hat through material.color.

The bake is done in the rest pose before any clip is baked (NLA tracks would pose the mesh), on a ground
plane, with a short AO distance so it captures contact shading (collar, under the coat hem, arms against
the torso, the hat brim) rather than whole-body darkening. The result is remapped to [FLOOR, 1] and every
texel outside the islands takes its nearest island value, so mipmaps never pull in black.
"""
import os
import time

import bpy
import numpy as np

FLOOR = 0.42          # darkest occlusion after the remap
GAMMA = 0.8           # < 1 lifts the mid-tones
DISTANCE = 0.22       # m: contact shading, not whole-body darkening


def _gltf_output_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    return g


def _unwrap(objs, res, margin_px=2.0):
    """AO islands = the figure's own grid parts. "UVMap" already has one island per grid (tube, panel, sphere)
    with a single seam each, so copying it and packing the islands at their 3D size adds no new vertex splits.
    (smart_project cut the figure into many islands and grew the full mesh data from 40 to 71 kB.)"""
    for o in objs:
        me = o.data
        if "AO" not in me.uv_layers:
            me.uv_layers.new(name="AO")
        if "UVMap" in me.uv_layers:
            src = me.uv_layers["UVMap"].data
            co = np.empty(len(src) * 2, dtype=np.float32)
            src.foreach_get("uv", co)
            me.uv_layers["AO"].data.foreach_set("uv", co)
            me.uv_layers["UVMap"].active_render = True
        me.uv_layers["AO"].active = True
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method='ADD', margin=margin_px / res, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')


def _mask(objs, res):
    from PIL import Image, ImageDraw
    im = Image.new("L", (res, res), 0)
    d = ImageDraw.Draw(im)
    for o in objs:
        me = o.data
        uv = me.uv_layers["AO"].data
        co = np.empty(len(uv) * 2, dtype=np.float32)
        uv.foreach_get("uv", co)
        co = (co.reshape(-1, 2) * res).tolist()
        for p in me.polygons:
            d.polygon([tuple(co[i]) for i in range(p.loop_start, p.loop_start + p.loop_total)], fill=255)
    return np.asarray(im) > 0


def _post(img, mask, res):
    from scipy import ndimage
    px = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)
    ao = px[..., 0].copy()
    raw = float(ao[mask].mean()) if mask.any() else 1.0
    m = mask.astype(np.float32)
    num = ndimage.gaussian_filter(ao * m, 0.6)
    den = ndimage.gaussian_filter(m, 0.6)
    ao = np.where(mask, num / np.maximum(den, 1e-4), ao)
    if mask.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
        ao = ao[iy, ix]
    ao = FLOOR + (1.0 - FLOOR) * np.clip(ao, 0.0, 1.0) ** GAMMA
    px[..., 0] = px[..., 1] = px[..., 2] = ao
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    return raw, float(ao[mask].mean()) if mask.any() else 1.0


def _device(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    dev = os.environ.get('NM_DEVICE', 'CPU').upper()
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


def bake(objs, name, res, out_dir, samples=48):
    """Bake AO for the mesh objects `objs` (rest pose) into one image and wire it as occlusion."""
    t0 = time.time()
    objs = [o for o in objs if o is not None and o.type == 'MESH' and len(o.data.polygons)]
    scene = bpy.context.scene
    _device(scene)
    _unwrap(objs, res)
    img = bpy.data.images.new(f"{name}_ao", res, res)
    img.colorspace_settings.name = "Non-Color"
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
    ground = bpy.context.active_object
    world = scene.world or bpy.data.worlds.new("aoworld")
    scene.world = world
    world.light_settings.distance = DISTANCE
    scene.cycles.samples = samples
    mats = []
    for o in objs:
        for m in o.data.materials:
            if m and m not in mats:
                mats.append(m)
    nodes = {}
    for m in mats:
        tn = m.node_tree.nodes.new("ShaderNodeTexImage")
        tn.image = img
        tn.interpolation = 'Linear'
        m.node_tree.nodes.active = tn
        nodes[m] = tn
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='AO', margin=2, use_clear=True)
    bpy.data.objects.remove(ground, do_unlink=True)
    raw, out = _post(img, _mask(objs, res), res)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}_ao.png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    grp = _gltf_output_group()
    for m, tn in nodes.items():
        nt = m.node_tree
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "AO"
        nt.links.new(uv.outputs[0], tn.inputs[0])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tn.outputs["Color"], sep.inputs[0])
        gn = nt.nodes.new("ShaderNodeGroup")
        gn.node_tree = grp
        nt.links.new(sep.outputs[0], gn.inputs[0])
    print(f"[people] AO {name} {res}px in {time.time() - t0:.1f}s: mean {raw:.2f} -> {out:.2f}")
    return img
