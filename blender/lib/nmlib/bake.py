"""Ambient-occlusion bake into a second UV map, wired as the glTF occlusion texture.

Kit textures carry base colour, roughness/metal and normal on UVMap (TEXCOORD_0, tiling).
Occlusion is unique per asset, so it gets its own non-overlapping UV map "AO" (TEXCOORD_1)
and one AO atlas per asset. No lighting goes into base colour.
"""
import math
import os
import time

import bpy

from . import state

AO_MATS = {"wood", "paint", "iron"}


def _gltf_output_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    return g


def ao_targets(objs):
    return [o for o in objs if o.type == 'MESH' and o.get("nm_mat") in AO_MATS]


def unwrap_ao(objs, margin=0.003):
    """Add the 'AO' UV map to every object and pack all of them into one shared layout."""
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_ao(objs, name, res=1024, samples=24, distance=0.5, ground=True, hide=()):
    """Bake AO for all kit-material objects in `objs` into one image and hook it up as occlusion.
    `hide`: objects excluded from the bake scene (snow caps, bulbs)."""
    t0 = time.time()
    targets = ao_targets(objs)
    if not targets:
        return None
    scene = bpy.context.scene
    unwrap_ao(targets)
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
    scene.render.bake.margin = 3
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
    bpy.ops.object.bake(type='AO', margin=3, use_clear=True)
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
    print(f"[nmlib] AO {name} {res}px for {len(targets)} objects in {time.time() - t0:.1f}s")
    return img
