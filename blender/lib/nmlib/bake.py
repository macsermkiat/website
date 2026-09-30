"""Ambient-occlusion bake into a second UV map, wired as the glTF occlusion texture.

Kit textures carry base colour, roughness/metal and normal on UVMap (TEXCOORD_0, tiling).
Occlusion is unique per asset, so it gets its own non-overlapping UV map "AO" (TEXCOORD_1)
and one AO atlas per asset. No lighting goes into base colour.

Round-2 layout rules (the round-1 atlas used 4 % of its pixels and averaged 0.08):
  * smart_project with no island margin, then pack_islands with a margin of `margin_px`
    pixels ADDED (not scaled), so ~20k small islands still fill ~40-60 % of the atlas;
  * islands smaller than `tiny_area` m2 (nail heads, rivets, bevel slivers, letters, bulb
    sockets) are not given texels: they point at a reserved light patch in the top-right
    corner, so they can never pick up black from a neighbouring island;
  * after the bake every texel outside the islands is filled with its nearest island value
    (no black background to bleed in through mipmaps or bilinear filtering), the islands are
    lightly denoised, and the result is remapped to [floor, 1] so no visible surface goes
    fully black under the site's hemisphere and environment light.
"""
import math
import os
import time

import bpy
import bmesh
import numpy as np

from . import state

AO_MATS = {"wood", "oak", "paint", "iron"}
AO_FLOOR = 0.32          # darkest AO the atlas may contain after the remap
AO_GAMMA = 0.85          # <1 lifts the mid-tones a little
PATCH_VALUE = 0.92       # AO of the tiny pieces that got no texels


def _gltf_output_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    return g


def ao_targets(objs):
    from . import mats
    keys = AO_MATS | set(mats.KIT_VARIANTS) | set(mats.PATTERNS)
    return [o for o in objs if o.type == 'MESH' and o.get("nm_mat") in keys]


def _islands(bm, uvl):
    """Faces grouped by UV connectivity (faces sharing an edge whose two UVs coincide)."""
    parent = list(range(len(bm.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    bm.faces.index_update()
    for e in bm.edges:
        lf = e.link_loops
        if len(lf) != 2:
            continue
        l1, l2 = lf
        # l1 runs v0->v1 in face 1, l2 runs v1->v0 in face 2
        a1, b1 = l1[uvl].uv, l1.link_loop_next[uvl].uv
        a2, b2 = l2.link_loop_next[uvl].uv, l2[uvl].uv
        if (a1 - a2).length < 1e-6 and (b1 - b2).length < 1e-6:
            ra, rb = find(l1.face.index), find(l2.face.index)
            if ra != rb:
                parent[ra] = rb
    groups = {}
    for f in bm.faces:
        groups.setdefault(find(f.index), []).append(f)
    return list(groups.values())


def unwrap_ao(objs, res=1024, margin_px=1.5, tiny_area=0.0006, reserve_px=6):
    """Add the 'AO' UV map to every object and pack all of them into one shared layout.
    Returns {object name: [face indices of tiny islands]} (those point at the light patch)."""
    for o in objs:
        me = o.data
        if "AO" not in me.uv_layers:
            me.uv_layers.new(name="AO")
        me.uv_layers["AO"].active = True
        me.uv_layers["UVMap"].active_render = True
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # collapse tiny islands so the packer spends no area on them
    tiny = {}
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        uvl = bm.loops.layers.uv["AO"]
        idx = []
        for isl in _islands(bm, uvl):
            if sum(f.calc_area() for f in isl) < tiny_area:
                for f in isl:
                    idx.append(f.index)
                    for l in f.loops:
                        l[uvl].uv = (0.0, 0.0)
        bm.to_mesh(o.data)
        bm.free()
        tiny[o.name] = idx
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='ADD', margin=margin_px / res, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    # free a band along the top and right for the light patch, then park the tiny faces there
    s = 1.0 - reserve_px / res
    patch = 1.0 - reserve_px * 0.5 / res
    for o in objs:
        uv = o.data.uv_layers["AO"].data
        co = np.empty(len(uv) * 2, dtype=np.float32)
        uv.foreach_get("uv", co)
        co *= s
        co = co.reshape(-1, 2)
        polys = o.data.polygons
        for fi in tiny[o.name]:
            p = polys[fi]
            co[p.loop_start:p.loop_start + p.loop_total] = (patch, patch)
        uv.foreach_set("uv", co.ravel())
    return tiny


def _coverage_mask(objs, tiny, res):
    """Rasterise the AO islands (all faces except the tiny ones) into a boolean mask."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (res, res), 0)
    d = ImageDraw.Draw(im)
    for o in objs:
        me = o.data
        uv = me.uv_layers["AO"].data
        co = np.empty(len(uv) * 2, dtype=np.float32)
        uv.foreach_get("uv", co)
        co = (co.reshape(-1, 2) * res).tolist()
        skip = set(tiny.get(o.name, ()))
        for p in me.polygons:
            if p.index in skip:
                continue
            pts = [tuple(co[i]) for i in range(p.loop_start, p.loop_start + p.loop_total)]
            d.polygon(pts, fill=255)
    return np.asarray(im) > 0          # row = v * res (same orientation as Image.pixels rows)


def _postprocess(img, mask, res, floor=AO_FLOOR, gamma=AO_GAMMA, patch_value=PATCH_VALUE, reserve_px=6):
    from scipy import ndimage
    px = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)
    ao = px[..., 0].copy()
    raw_mean = float(ao[mask].mean()) if mask.any() else 1.0
    # masked denoise: blur inside the islands only (sigma 0.7 px) so islands never mix with background
    m = mask.astype(np.float32)
    num = ndimage.gaussian_filter(ao * m, 0.7)
    den = ndimage.gaussian_filter(m, 0.7)
    ao = np.where(mask, num / np.maximum(den, 1e-4), ao)
    # fill everything outside the islands with the nearest island texel
    if mask.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
        ao = ao[iy, ix]
    ao = floor + (1.0 - floor) * np.clip(ao, 0.0, 1.0) ** gamma
    ao[res - reserve_px:, :] = patch_value
    ao[:, res - reserve_px:] = patch_value
    px[..., 0] = px[..., 1] = px[..., 2] = ao
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    return raw_mean, float(ao[mask].mean()) if mask.any() else 1.0


def bake_ao(objs, name, res=1024, samples=24, distance=0.6, ground=True, hide=(), margin_px=None,
            tiny_area=0.0006, floor=AO_FLOOR):
    """Bake AO for all kit-material objects in `objs` into one image and hook it up as occlusion.
    `hide`: objects excluded from the bake scene (snow caps, bulbs). Returns the image."""
    t0 = time.time()
    targets = ao_targets(objs)
    if not targets:
        return None
    scene = bpy.context.scene
    margin_px = margin_px if margin_px is not None else (1.5 if res >= 512 else 1.0)
    tiny = unwrap_ao(targets, res=res, margin_px=margin_px, tiny_area=tiny_area)
    img = bpy.data.images.new(f"{name}_ao", res, res)
    img.colorspace_settings.name = "Non-Color"
    gp = None
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
        gp = bpy.context.active_object
    hidden = []
    for o in hide:
        if o and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
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
    mask = _coverage_mask(targets, tiny, res)
    raw_mean, out_mean = _postprocess(img, mask, res, floor=floor)
    path = os.path.join(state.OUT_DIR, "ao", f"{name}_ao.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    # wire occlusion for the glTF exporter
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
    if gp:
        bpy.data.objects.remove(gp, do_unlink=True)
    for o in hidden:
        o.hide_render = False
    ntiny = sum(len(v) for v in tiny.values())
    print(f"[nmlib] AO {name} {res}px for {len(targets)} objects in {time.time() - t0:.1f}s: "
          f"islands cover {mask.mean():.0%}, {ntiny} tiny faces on the patch, "
          f"island mean {raw_mean:.2f} -> {out_mean:.2f}")
    return img
