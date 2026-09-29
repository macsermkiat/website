"""Markers (named empties), glb export, web optimisation and checks."""
import json
import os
import subprocess
import sys
import time

import bpy
from mathutils import Vector

from . import state

sys.path.insert(0, state.LIB_DIR)
import glb_tools  # noqa: E402

OPTIMIZE_JS = os.path.join(state.LIB_DIR, "optimize.mjs")


# ------------------------------------------------------------------ markers
def empty(name, loc, rot=(0, 0, 0), size=0.15, look_at=None):
    """Named empty in the export collection. `look_at` turns its -Z axis toward a point."""
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = 'PLAIN_AXES'
    ob.empty_display_size = size
    ob.location = loc
    if look_at is not None:
        d = Vector(look_at) - Vector(loc)
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    else:
        ob.rotation_euler = rot
    state.export_collection().objects.link(ob)
    if ob.name != name:
        raise RuntimeError(f"marker name clash: wanted {name}, got {ob.name}")
    return ob


def stall_markers(counter_top, counter_y, shelf_1, shelf_2, vendor, sign, front,
                  cam_view, cam_target, lights):
    """All the empties a stall must provide (see docs/BUILD.md, Scene conventions).
    Positions are Blender coordinates (Z up, front toward -Y)."""
    empty("slot_counter", (0, counter_y, counter_top))
    empty("slot_shelf_1", shelf_1)
    empty("slot_shelf_2", shelf_2)
    empty("slot_vendor", vendor)
    empty("slot_sign", sign)
    empty("slot_front", front)
    empty("cam_target", cam_target)
    empty("cam_view", cam_view, look_at=cam_target)
    for i, p in enumerate(lights):
        empty(f"light_{i}", p)


# ------------------------------------------------------------------ export
def export_objects():
    return list(state.export_collection().all_objects)


def triangles(objs=None):
    t = 0
    for o in objs or export_objects():
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            t += len(o.data.loop_triangles)
    return t


def export_glb(name, texture_size=1024, externalize=None, keep_raw=True):
    """Export the Export collection to site/public/models/<name>.glb via optimize.mjs.

    externalize: optional (match(name)->bool, uri_for(name)->str) that moves shared kit
    textures out of the glb into sibling files (deco kit)."""
    t0 = time.time()
    raw_dir = os.path.join(state.OUT_DIR, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    raw = os.path.join(raw_dir, f"{name}.glb")
    out = os.path.join(state.MODELS_DIR, f"{name}.glb")
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    objs = export_objects()
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=raw, export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False,
        export_image_format='AUTO', export_texcoords=True, export_normals=True,
        export_cameras=False, export_lights=False, export_extras=False)
    cmd = ["node", OPTIMIZE_JS, raw, out, "--texture-size", str(texture_size)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise RuntimeError("optimize failed")
    written = {}
    if externalize:
        match, uri_for = externalize
        written = glb_tools.externalize_images(out, match, uri_for, state.MODELS_DIR)
    rep = glb_tools.report(out)
    rep["external"] = written
    rep["blender_triangles"] = triangles(objs)
    ext_bytes = sum(os.path.getsize(os.path.join(state.MODELS_DIR, u)) for u in written)
    print(f"[nmlib] exported {name}: {rep['bytes'] / 1e6:.2f} MB (+{ext_bytes / 1e6:.2f} MB shared), "
          f"{rep['triangles']} tris in {time.time() - t0:.1f}s")
    if not keep_raw:
        os.remove(raw)
    return rep


def write_report(reports, path):
    with open(path, "w") as f:
        json.dump(reports, f, indent=1)
