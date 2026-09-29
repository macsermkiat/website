"""Clash test for the Riesenrad: do moving parts pass through steel as the wheel turns?

Builds ferris (full and lite) without exporting, samples every mesh edge every 4 cm, and checks
over a whole turn (1 degree steps):

  1. wheel steel vs gondolas: in the wheel's frame each gondola turns about its own axle, so
     the wheel's points near an axle are rotated through 360 degrees and tested against the
     gondola cabin's convex hull (everything more than 0.28 m below the axle; the yoke round
     the axle itself is coaxial with the bearing and cannot clash);
  2. gondolas vs the static frame, deck, sign and booth: one upright gondola is carried round
     the hub and the static points are tested against its hull;
  3. wheel steel vs the static frame: the wheel sweeps a solid of revolution about the axle, so
     static points (except the axle it turns on) must not share an (R, y) cell with wheel points.

    ~/nachtmarkt-tools/bpy-venv/bin/python blender/rides/check_clash.py [--lite-only | --full-only]

Exit status 0 when all three checks are clear for every variant built.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import rcommon as rc  # noqa: E402
from scipy.spatial import ConvexHull  # noqa: E402

import ferris  # noqa: E402
from nmlib import mats, state  # noqa: E402

STEP = 0.04          # edge sampling (m)
TOL = 0.005          # a point must be this far inside the hull to count
HULL_TOP = -0.28     # hull uses the gondola below this height relative to its axle
CELL = 0.02          # (R, y) grid for the wheel's solid of revolution


def edge_samples(ob):
    """World-space vertices plus points every STEP along each edge."""
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    ed = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ed)
    ed = ed.reshape(-1, 2)
    a, b = co[ed[:, 0]], co[ed[:, 1]]
    L = np.linalg.norm(b - a, axis=1)
    k = np.maximum(1, np.ceil(L / STEP).astype(int))
    out = [co]
    for m in np.unique(k):
        sel = k == m
        if m < 2:
            continue
        t = (np.arange(1, m) / m)[None, :, None]
        out.append((a[sel][:, None, :] + (b[sel] - a[sel])[:, None, :] * t).reshape(-1, 3))
    return np.concatenate(out)


def classify(ob):
    p = ob.parent
    while p is not None:
        if p.name.startswith("gondola_") and not p.name.startswith("gondola_seat"):
            return p.name
        if p.name == "rot_wheel":
            return "wheel"
        p = p.parent
    return "static"


def inside(eq, pts):
    """Depth inside the hull (positive = inside) for each point."""
    d = pts @ eq[:, :3].T + eq[:, 3]
    return -d.max(axis=1)


def rot_y(pts, ang):
    c, s = math.cos(ang), math.sin(ang)
    x, z = pts[:, 0], pts[:, 2]
    return np.stack([c * x + s * z, pts[:, 1], -s * x + c * z], axis=1)


def check(lite):
    state.reset(26, lite_mode=lite)
    mats.ensure_kit()
    ferris.build(lite)
    import bpy
    bpy.context.view_layer.update()
    groups = {}
    for ob in rc.mesh_objs():
        groups.setdefault(classify(ob), []).append(ob)
    hub = np.array([0.0, 0.0, ferris.HUB])
    g0 = bpy.data.objects["gondola_0"].matrix_world.translation
    g0 = np.array(g0)
    cabin = np.concatenate([np.array([ob.matrix_world @ v.co for v in ob.data.vertices])
                            for ob in groups["gondola_0"]]) - g0
    cabin = cabin[cabin[:, 2] < HULL_TOP]
    eq = ConvexHull(cabin).equations
    reach = np.linalg.norm(cabin[:, [0, 2]], axis=1).max()
    half_y = np.abs(cabin[:, 1]).max()
    print(f"[clash] {'lite' if lite else 'full'}: gondola hull reaches {reach:.2f} m from its axle, |y| <= {half_y:.2f}")

    def pts_of(obs):
        arr = [edge_samples(o) for o in obs]
        names = np.concatenate([np.full(len(a), i) for i, a in enumerate(arr)])
        return np.concatenate(arr), names

    wheel, wname = pts_of(groups["wheel"])
    static, sname = pts_of(groups["static"])
    axles = [np.array(bpy.data.objects[f"gondola_{i}"].matrix_world.translation) for i in range(ferris.N)]
    angs = np.radians(np.arange(0, 360, 1.0))
    report = {}

    # 1. wheel steel vs each gondola turning about its axle
    hits = {}
    for i, A in enumerate(axles):
        rel = wheel - A
        near = (np.abs(rel[:, 1]) < half_y + 0.05) & (np.linalg.norm(rel[:, [0, 2]], axis=1) < reach + 0.05)
        cand, cn = rel[near], wname[near]
        for a in angs:
            d = inside(eq, rot_y(cand, a))
            bad = d > TOL
            for j in np.unique(cn[bad]):
                nm = groups["wheel"][j].name
                hits[nm] = max(hits.get(nm, 0.0), float(d[bad & (cn == j)].max()))
    report["wheel_vs_gondolas"] = hits

    # 2. gondola carried round the hub vs static parts
    hits = {}
    r0 = A0 = axles[0] - hub
    Rg = np.linalg.norm(r0[[0, 2]])
    rel_hub = static - hub
    Rs = np.linalg.norm(rel_hub[:, [0, 2]], axis=1)
    near = (np.abs(rel_hub[:, 1]) < half_y + 0.05) & (np.abs(Rs - Rg) < reach + 0.05)
    cand, cn = static[near], sname[near]
    for a in np.radians(np.arange(0, 360, 0.5)):
        pos = hub + rot_y(A0[None, :], a)[0]
        d = inside(eq, cand - pos)
        bad = d > TOL
        for j in np.unique(cn[bad]):
            nm = groups["static"][j].name
            hits[nm] = max(hits.get(nm, 0.0), float(d[bad & (cn == j)].max()))
    report["gondolas_vs_static"] = hits

    # 3. wheel steel (solid of revolution about the axle) vs static parts
    def ry(p):
        rel = p - hub
        return np.linalg.norm(rel[:, [0, 2]], axis=1), rel[:, 1]
    Rw, yw = ry(wheel)
    occ = set(zip(np.floor(Rw / CELL).astype(int), np.floor(yw / CELL).astype(int)))
    Rs, ys = ry(static)
    hits = {}
    keep = Rs > 0.35             # the fixed axle the hub turns on
    iR, iy = np.floor(Rs / CELL).astype(int), np.floor(ys / CELL).astype(int)
    for k in np.nonzero(keep)[0]:
        if any((iR[k] + a, iy[k] + b) in occ for a in (-1, 0, 1) for b in (-1, 0, 1)):
            nm = groups["static"][sname[k]].name
            hits[nm] = hits.get(nm, 0) + 1
    report["wheel_vs_static"] = hits
    ok = not any(report.values())
    for k, v in report.items():
        print(f"[clash]   {k}: {'clear' if not v else v}")
    print(f"[clash] {'lite' if lite else 'full'}: {len(wheel)} wheel, {len(static)} static points, "
          f"{'CLEAR' if ok else 'CLASH'}")
    return ok


if __name__ == "__main__":
    variants = [False, True]
    if "--lite-only" in sys.argv:
        variants = [True]
    if "--full-only" in sys.argv:
        variants = [False]
    results = [check(v) for v in variants]
    sys.stdout.flush()
    os._exit(0 if all(results) else 1)
