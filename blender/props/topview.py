"""Quick layout check: build one prop set (no AO, no export) and render a cheap orthographic view of it.

    /home/claude/tools/bpy-venv/bin/python blender/props/topview.py <set> <out.png> [top|front|persp]
        [--res 1000] [--samples 8] [--focus x,y,z,size]

Flat white world light, 8 samples, so it is quick on the CPU. Writes only the PNG you name (keep it in your
scratchpad). Not a review render.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import vlib  # noqa: E402
import vstage  # noqa: E402
import build_props  # noqa: E402


def main():
    argv = sys.argv[1:]
    name, out = argv[0], argv[1]
    view = argv[2] if len(argv) > 2 and not argv[2].startswith("--") else "top"
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    res = int(opt("--res", "1000"))
    samples = int(opt("--samples", "8"))
    focus = opt("--focus", None)
    sets = build_props.all_sets()
    d = sets[name]
    vlib.reset(d.get("seed", 1), "--lite" in argv)
    ps = d["fn"]()
    lo, hi = vlib.world_bbox(list(ps.objs.values()))
    scene = bpy.context.scene
    vstage.setup_device(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    # a mid-grey counter plane at z = 0
    me = bpy.data.meshes.new("tv_ground")
    me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("tv_ground", me)
    mat = bpy.data.materials.new("tv_ground")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.2, 0.16, 1)
    me.materials.append(mat)
    scene.collection.objects.link(g)
    cam = bpy.data.cameras.new("tv_cam")
    co = bpy.data.objects.new("tv_cam", cam)
    scene.collection.objects.link(co)
    scene.camera = co
    c = (lo + hi) / 2
    size = max(hi.x - lo.x, hi.y - lo.y) * 1.05
    if focus:
        fx, fy, fz, fs = (float(v) for v in focus.split(","))
        c, size = Vector((fx, fy, fz)), fs
    if view == "top":
        cam.type = 'ORTHO'
        cam.ortho_scale = size
        co.location = (c.x, c.y, 3.0)
        co.rotation_euler = (0, 0, 0)
        scene.render.resolution_x, scene.render.resolution_y = res, max(64, int(res * (hi.y - lo.y + 0.05) / size)) \
            if not focus else res
    elif view == "front":
        cam.type = 'ORTHO'
        cam.ortho_scale = size
        co.location = (c.x, -3.0, c.z if focus else (lo.z + hi.z) / 2)
        co.rotation_euler = (math.pi / 2, 0, 0)
        scene.render.resolution_x = res
        scene.render.resolution_y = max(64, int(res * ((hi.z - lo.z + 0.05) / size))) if not focus else int(res * 0.6)
    else:
        cam.type = 'PERSP'
        cam.lens = 50
        dist = size * 1.6
        sgn = 1 if view == "back" else -1
        side = dist * 0.6 if view == "side" else 0.0
        co.location = (c.x + side, c.y + sgn * dist * 0.8, c.z + dist * (0.25 if view == "back" else 0.55))
        dvec = c - co.location
        co.rotation_euler = dvec.to_track_quat('-Z', 'Y').to_euler()
        scene.render.resolution_x, scene.render.resolution_y = res, int(res * 9 / 16)
    scene.render.filepath = out
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print(f"[topview] {name} {view} -> {out}; bbox {tuple(round(v, 3) for v in lo)} .. {tuple(round(v, 3) for v in hi)}")


if __name__ == "__main__":
    main()
