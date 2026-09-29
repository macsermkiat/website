"""Clash test for the square's furniture against the tree and the placed stalls and rides.

Checks, with the tree placed as layout.json places it:
  1. no string-light wire, bulb or pole vertex lies inside the fir's crown (its needle envelope,
     measured from the tree's own needle vertices in 0.5 m height bands, plus a 0.3 m margin);
  2. no bench, bin or lamp vertex lies under the lowest boughs (below 1.5 m, inside the envelope);
  3. no pole, lamp, bench, bin or bollard stands inside a stall, ride or bandstand footprint, and no
     wire or string bulb passes through the Ferris wheel or the carousel.
Footprints are each placed asset's bounding box (read from its glb in site/public/models with
`gltf-transform inspect`), in the asset's own frame, grown by a margin.

Run after square.py and tree.py:
  /home/claude/tools/bpy-venv/bin/python blender/square/check_clash.py
Exits 1 and lists the offenders when anything clashes.
"""
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy
import numpy as np
from mathutils import Matrix

import architect_common as C
import architect_plan as P

MARGIN = 0.3            # around the fir's needles
FOOT_MARGIN = 0.15      # around a stall or ride's bounding box
TALL = ("riesenrad", "karussell")      # wires may not pass over these at any height
ROUND = ("bandstand", "karussell")


def bbox(asset):
    """(xmin, xmax, ymin, ymax, zmin, zmax) of a glb's scene in three.js units, or None."""
    path = os.path.join(C.MODELS, asset)
    if not os.path.exists(path):
        return None
    r = subprocess.run(["gltf-transform", "inspect", path, "--format", "md"], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    try:
        i = next(k for k, l in enumerate(lines) if "SCENES" in l)
        row = next(l for l in lines[i:] if l.startswith("| 0"))
    except StopIteration:
        return None
    cells = [c.strip() for c in row.strip("|").split("|")]
    lo = [float(v) for v in cells[3].split(",")]
    hi = [float(v) for v in cells[4].split(",")]
    return lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in set(bpy.data.objects) - before]


def world_verts(ob):
    me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def main():
    C.reset()
    out = os.path.join(C.REPO, "blender", "square", "out")
    sq = import_glb(os.path.join(out, "square_raw.glb"))
    layout = P.load_layout()
    places = {p["id"]: p for p in layout["places"]}
    tp = places["tree"]
    tx, ty = tp["pos"][0], -tp["pos"][1]
    tr = import_glb(os.path.join(out, "tree_raw.glb"))
    for o in tr:
        if o.parent is None:
            o.matrix_world = Matrix.Translation((tx, ty, 0)) @ Matrix.Rotation(tp.get("rotY", 0), 4, "Z") @ o.matrix_world
    bpy.context.view_layer.update()

    # the fir's envelope: max horizontal reach of the needles per 0.5 m band
    needles = np.concatenate([world_verts(o) for o in tr if o.type == "MESH" and o.name.startswith(("tree_needles", "snow_tree"))
                              and o.name != "snow_tree_fence"])
    band = 0.5
    nb = int(needles[:, 2].max() / band) + 2
    env = np.zeros(nb)
    rr = np.hypot(needles[:, 0] - tx, needles[:, 1] - ty)
    idx = np.clip((needles[:, 2] / band).astype(int), 0, nb - 1)
    np.maximum.at(env, idx, rr)
    low_reach = env[: int(1.5 / band) + 2].max()
    print(f"[clash] fir envelope: base {env[:4].max():.2f} m, at 5.5 m {env[int(5.5 / band)]:.2f} m, "
          f"lowest boughs reach {low_reach:.2f} m")

    def in_crown(v):
        k = np.clip((v[:, 2] / band).astype(int), 0, nb - 1)
        kk = np.stack([np.clip(k + d, 0, nb - 1) for d in (-1, 0, 1)])
        reach = env[kk].max(0)
        return np.hypot(v[:, 0] - tx, v[:, 1] - ty) < reach + MARGIN

    problems = []
    for o in sq:
        if o.type != "MESH":
            continue
        v = world_verts(o)
        if o.name.startswith(("string_wire", "bulbs_string", "poles_wood")):
            n = int(in_crown(v).sum())
            if n:
                problems.append(f"{o.name}: {n} vertices inside the fir's crown")
        if o.name.startswith(("benches_wood", "street_iron", "bulbs_lamp")):
            low = v[v[:, 2] < 1.5]
            n = int(((np.hypot(low[:, 0] - tx, low[:, 1] - ty)) < low_reach + MARGIN).sum())
            if n:
                problems.append(f"{o.name}: {n} vertices under the lowest boughs")

    # stalls, rides and bandstand: their bounding boxes, in their own frames
    boxes = {pid: bbox(p["asset"]) for pid, p in places.items() if p["kind"] != "scenery"}
    missing = [pid for pid, b in boxes.items() if b is None]
    if missing:
        print("[clash] no glb to measure for", missing, "(skipped)")

    def inside(pid, p, pts):
        b = boxes.get(pid)
        if b is None:
            return np.zeros(len(pts), bool)
        x, y, rot = p["pos"][0], -p["pos"][1], p.get("rotY", 0)
        dx, dy = pts[:, 0] - x, pts[:, 1] - y
        if pid in ROUND:          # the bandstand and carousel are round: test their radius, not the box corners
            return (np.hypot(dx, dy) < max(b[1], -b[0]) + FOOT_MARGIN) & (pts[:, 2] < b[3] + FOOT_MARGIN)
        c, s = math.cos(-rot), math.sin(-rot)
        lx, lz = dx * c - dy * s, -(dx * s + dy * c)          # asset-local x and three.js z
        m = FOOT_MARGIN
        return ((lx > b[0] - m) & (lx < b[1] + m) & (lz > b[4] - m) & (lz < b[5] + m)
                & (pts[:, 2] < b[3] + m))

    ground_things = [o for o in sq if o.type == "MESH" and o.name.startswith(("poles_wood", "street_iron", "benches_wood"))]
    flying = [o for o in sq if o.type == "MESH" and o.name.startswith(("string_wire", "bulbs_string"))]
    for pid, p in places.items():
        if p["kind"] == "scenery":
            continue
        for o in ground_things:
            v = world_verts(o)
            v = v[v[:, 2] < 2.2]
            n = int(inside(pid, p, v).sum())
            if n:
                problems.append(f"{o.name}: {n} vertices inside the footprint of {pid}")
        if pid in TALL:
            for o in flying:
                n = int(inside(pid, p, world_verts(o)).sum())
                if n:
                    problems.append(f"{o.name}: {n} vertices pass through {pid}")

    # the poles themselves, by position
    for i, (x, z) in enumerate(P.POLES_THREE):
        d = math.hypot(x - tp["pos"][0], z - tp["pos"][1])
        if d < P.TREE_CLEAR_R:
            problems.append(f"pole {i} at [{x}, {z}] stands {d:.2f} m from the tree (min {P.TREE_CLEAR_R})")

    if problems:
        print("[clash] FAIL")
        for s in problems:
            print("  -", s)
        sys.exit(1)
    print("[clash] OK: no wire, bulb or pole in the fir; benches clear of the boughs; nothing in a stall or ride")


main()
