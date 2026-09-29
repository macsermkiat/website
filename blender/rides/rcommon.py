"""Shared helpers for the ride builder's landmarks (Riesenrad, Karussell, bandstand, instruments).

Builds on the carpenter's nmlib (blender/lib/nmlib). Adds:
  * `rsteel`: a tiling kit texture of painted steel (orange-peel paint, grime along the
    member, chips down to red-oxide primer and rust), 0.5 m tile, tinted by COLOR_0 like the
    other kits;
  * simple materials for instruments and fairground trim (chrome, mirror, enamel, gilt,
    ebony, ivory, bronze, lacquered brass, drum head, felt, leather, black metal, paper,
    strings);
  * geometry helpers (rods between points, polygon-side frames, low-poly bulbs);
  * node helpers: pivot empties and re-parenting with the mesh origin baked to the pivot,
    so gondolas, horses and act_ nodes animate about the right point;
  * a build -> AO -> export pipeline for full and lite, and the Cycles preview step.

Run the landmark scripts with the team's bpy:
    ~/nachtmarkt-tools/bpy-venv/bin/python blender/rides/ferris.py [--no-render] [--no-lite]
    (renders honour NM_DEVICE=METAL|CPU and NM_THREADS; previews default to 1920x1080, 128
    samples, with a 1280 px JPEG in review/round-1/rides/)
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import bpy  # noqa: E402,F401  (must precede bmesh and mathutils)
import bmesh  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

from nmlib import bake, export, geo, mats, render, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

REVIEW = os.path.join(state.REPO, "review", "round-1", "rides")
TAU = 2 * math.pi


# =================================================================== materials
def _rsteel_graph(nb):
    """Light neutral painted steel; COLOR_0 gives the colour (cream, red, green, blue ...)."""
    peel = nb.noise(70, 70, detail=3, rough=0.55, off=(0.7, 2.1, 3.3, 1.2))
    roller = nb.noise(3, 40, detail=2, off=(4.4, 0.3, 1.9, 2.8))
    dirt = nb.noise(3, 3, detail=5, rough=0.6, off=(2.2, 5.1, 0.4, 3.9))
    streak = nb.smooth(0.52, 0.80, nb.noise(34, 2, detail=3, off=(1.6, 3.2, 4.1, 0.5)))
    chipn = nb.noise(16, 16, detail=6, rough=0.68, off=(5.3, 1.1, 2.9, 4.4))
    chip = nb.smooth(0.672, 0.688, chipn)
    halo = nb.smooth(0.60, 0.672, chipn)
    rust_n = nb.noise(40, 40, detail=4, off=(3.1, 4.7, 0.9, 1.6))
    col = nb.mix(nb.mul(peel, 0.10), nb.rgb((0.80, 0.79, 0.76)), nb.rgb((0.66, 0.65, 0.62)))
    col = nb.mix(nb.mul(roller, 0.08), col, nb.rgb((0.70, 0.69, 0.66)))
    col = nb.mix(nb.mul(dirt, 0.42), col, nb.rgb((0.50, 0.47, 0.42)))
    col = nb.mix(nb.mul(streak, 0.36), col, nb.rgb((0.38, 0.34, 0.29)))
    col = nb.mix(nb.mul(halo, 0.35), col, nb.rgb((0.42, 0.30, 0.22)))          # rust bleeding
    chipcol = nb.mix(rust_n, nb.rgb((0.20, 0.07, 0.035)), nb.rgb((0.11, 0.055, 0.03)))
    col = nb.mix(chip, col, chipcol)
    rough = nb.add(0.30, nb.mul(peel, 0.08), nb.mul(streak, 0.16), nb.mul(dirt, 0.08),
                   nb.mul(chip, 0.42))
    metal = nb.mul(chip, 0.15)
    height = nb.add(nb.mul(peel, 0.22), nb.mul(roller, 0.1), nb.mul(chip, -0.9), nb.mul(rust_n, nb.mul(chip, 0.3)))
    return col, rough, metal, height


def register_materials():
    mats.GRAPHS.setdefault("rsteel", _rsteel_graph)
    mats.BUMP.setdefault("rsteel", (0.7, 0.0008))
    mats.KIT_RES.setdefault("rsteel", 512)
    geo.TILE.setdefault("rsteel", 0.5)
    bake.AO_MATS.add("rsteel")
    extra = {
        # key: (base colour linear, roughness, metallic, emission colour, strength, alpha)
        "chrome":     ((0.90, 0.90, 0.90), 0.14, 1.0, None, 0.0, 1.0),
        # old fairground mirror glass: warm silvering, slightly soft, so it spreads the bulbs'
        # glow instead of showing a black night sky
        "mirror":     ((0.97, 0.84, 0.64), 0.16, 1.0, None, 0.0, 1.0),
        "enamel":     ((0.86, 0.84, 0.79), 0.26, 0.0, None, 0.0, 1.0),
        "gilt":       ((0.93, 0.68, 0.30), 0.30, 1.0, None, 0.0, 1.0),
        "ebony":      ((0.016, 0.014, 0.013), 0.32, 0.0, None, 0.0, 1.0),
        "ivory":      ((0.80, 0.76, 0.64), 0.30, 0.0, None, 0.0, 1.0),
        "bronze":     ((0.74, 0.50, 0.24), 0.42, 1.0, None, 0.0, 1.0),
        "saxbrass":   ((0.90, 0.66, 0.30), 0.20, 1.0, None, 0.0, 1.0),
        "drumhead":   ((0.80, 0.78, 0.72), 0.58, 0.0, None, 0.0, 1.0),
        "felt":       ((0.30, 0.02, 0.03), 0.92, 0.0, None, 0.0, 1.0),
        "leather":    ((0.11, 0.05, 0.025), 0.55, 0.0, None, 0.0, 1.0),
        "blackmetal": ((0.035, 0.034, 0.033), 0.42, 0.7, None, 0.0, 1.0),
        "paper":      ((0.80, 0.77, 0.68), 0.85, 0.0, None, 0.0, 1.0),
        "strings":    ((0.72, 0.70, 0.66), 0.25, 1.0, None, 0.0, 1.0),
        "hole":       ((0.004, 0.003, 0.003), 0.95, 0.0, None, 0.0, 1.0),
        "canvas":     ((0.76, 0.72, 0.64), 0.88, 0.0, None, 0.0, 1.0),
    }
    for k, v in extra.items():
        mats.SIMPLE.setdefault(k, v)


register_materials()


# =================================================================== geometry helpers
def rod(part, a, b, r, seg=6, r2=None, caps=False, **kw):
    """Cylinder from point a to point b (UV grain along it)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    if L < 1e-6:
        return
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=L)
    q = d.normalized().to_track_quat('Z', 'Y' if abs(d.normalized().y) < 0.95 else 'X')
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    kw.setdefault("smooth", True)
    part.from_bmesh(bm, M, grain=2, **kw)


def frame_at(p, x_axis, z_axis=(0, 0, 1)):
    """4x4 matrix at p with local X along x_axis and local Z as close to z_axis as possible."""
    x = Vector(x_axis).normalized()
    z = Vector(z_axis)
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    return Matrix.Translation(p) @ Matrix((x, y, z)).transposed().to_4x4()


def side_M(center, phi):
    """Frame for a board on a polygon side whose outward normal is at angle phi (XY plane):
    local X runs along the side, local Y is up, local Z points outward (valance / shape)."""
    return Matrix.Translation(center) @ Euler((0, 0, phi + math.pi / 2)).to_matrix().to_4x4() @ \
        Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()


def bulb(part, p, r=0.035, lite=None):
    """One low-poly lamp bulb (20 triangles, 8 in lite): the engine blooms them anyway."""
    lite = state.lite() if lite is None else lite
    if lite:
        # octahedron
        bm2 = bmesh.new()
        verts = [bm2.verts.new(v) for v in ((r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r * 1.2), (0, 0, -r * 1.2))]
        for f in ((0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)):
            bm2.faces.new([verts[i] for i in f])
        part.from_bmesh(bm2, Matrix.Translation(p), grain=2, smooth=True, var=0.04)
    else:
        part.ico(p, r, subd=1, scale=(1, 1, 1.15), var=0.04)


def ring_pts(R, z, n, phase=0.0, cx=0.0, cy=0.0):
    return [Vector((cx + R * math.cos(phase + TAU * i / n), cy + R * math.sin(phase + TAU * i / n), z))
            for i in range(n)]


def lathe_poly(part, profile, seg, M=None, phase=None, flat=True, **kw):
    """Faceted lathe (polygon plan) with faces centred on the axes when phase is None."""
    if phase is None:
        phase = math.pi / seg
    R = Euler((0, 0, phase)).to_matrix().to_4x4()
    part.lathe(profile, seg=seg, M=(M or Matrix()) @ R, smooth=not flat, **kw)


# =================================================================== node helpers
def node(name, loc, parent=None, rot=(0, 0, 0)):
    """Named empty in the export collection (optionally parented, keeping its world place)."""
    ob = export.empty(name, loc, rot=rot)
    if parent is not None:
        set_parent(ob, parent)
    return ob


def set_parent(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = Matrix()
    child.matrix_world = mw


def attach(ob, parent):
    """Parent a mesh object (built in world coordinates) to `parent`, baking the offset into the
    mesh so the object's local transform is identity and its origin sits at the parent pivot."""
    if ob is None:
        return None
    bpy.context.view_layer.update()
    Mp = parent.matrix_world.copy()
    ob.data.transform(Mp.inverted() @ ob.matrix_world)
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix()
    ob.matrix_basis = Matrix()
    return ob


def finish_all(parts, parent=None):
    objs = []
    for p in parts:
        ob = p.finish()
        if ob is not None:
            if parent is not None:
                attach(ob, parent)
            objs.append(ob)
    return objs


class Parts:
    """A bag of Parts keyed by material (one mesh per material per group)."""

    def __init__(self, prefix, **defaults):
        self.prefix = prefix
        self.d = {}
        self.defaults = defaults

    def __getitem__(self, mat):
        if mat not in self.d:
            nm = f"{self.prefix}_{mat}"
            if mat in ("bulb_warm", "bulb_cold"):
                nm = f"bulbs_{self.prefix}"
            kw = dict(self.defaults.get(mat, {}))
            self.d[mat] = Part(nm, mat, **kw)
        return self.d[mat]

    def finish(self, parent=None):
        return finish_all(list(self.d.values()), parent)


# =================================================================== pipeline
def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--preview-only", action="store_true",
                    help="build the full model and render the preview, without AO bake or export")
    ap.add_argument("--only", default=None)
    ap.add_argument("--cam", default=None, help="x,y,z,tx,ty,tz,lens debug camera")
    ap.add_argument("--preview-name", default=None)
    a, _ = ap.parse_known_args(sys.argv[1:])
    return a


def hidden_for_ao(o):
    return o.name.startswith(("snow_", "bulbs_"))


def mesh_objs():
    return [o for o in state.export_collection().all_objects if o.type == 'MESH']


def build_and_export(name, build, seed, lite, ao_res=None, texture_size=None, ao_samples=None):
    state.reset(seed, lite_mode=lite)
    mats.ensure_kit()
    t0 = time.time()
    build(lite)
    objs = mesh_objs()
    print(f"[{name}] built {'lite' if lite else 'full'} in {time.time() - t0:.1f}s, "
          f"{export.triangles()} tris")
    for o in sorted(objs, key=lambda o: -len(o.data.polygons))[:int(os.environ.get("RC_TOP", "14"))]:
        print(f"     {o.name:30s} {export.triangles([o]):7d}")
    out = name + (".lite" if lite else "")
    bake.bake_ao(objs, out, res=ao_res or (512 if lite else 1024),
                 samples=ao_samples or (10 if lite else 16),
                 hide=[o for o in objs if hidden_for_ao(o)])
    rep = export.export_glb(out, texture_size or (512 if lite else 1024))
    return objs, rep


def run(name, build, preview=None, seed=1, ao_full=1024, ao_lite=512, tex_full=1024, tex_lite=512,
        ground=60):
    a = args()
    if a.preview_only:
        state.reset(seed, lite_mode=False)
        mats.ensure_kit()
        build(False)
        do_preview(name, mesh_objs(), preview, a, ground=ground)
        return {}
    rep_path = os.path.join(state.OUT_DIR, f"{name}_report.json")
    reports = {}
    if os.path.exists(rep_path):
        with open(rep_path) as f:
            reports = json.load(f)
    if not a.no_lite:
        _, reports["lite"] = build_and_export(name, build, seed, True, ao_lite, tex_lite)
    if not a.no_full:
        objs, reports["full"] = build_and_export(name, build, seed, False, ao_full, tex_full)
        if preview and not a.no_render:
            do_preview(name, objs, preview, a, ground=ground)
    with open(rep_path, "w") as f:
        json.dump(reports, f, indent=1)
    for k, r in reports.items():
        print(f"[{name}] {k}: {r['bytes'] / 1e6:.2f} MB, {r['triangles']} tris")
    return reports


def do_preview(name, objs, preview, a, ground=60):
    render.night_scene(ground_size=ground)
    cam = preview(objs)
    if a.cam:
        v = [float(t) for t in a.cam.split(",")]
        render.camera(v[0:3], v[3:6], lens=v[6] if len(v) > 6 else 35)
    os.makedirs(REVIEW, exist_ok=True)
    w, h = (int(v) for v in a.res.split("x"))
    pn = a.preview_name or f"{name}_preview"
    render.render(os.path.join(state.OUT_DIR, "renders", f"{pn}.png"), samples=a.samples,
                  res=(w, h), jpeg=os.path.join(REVIEW, f"{pn}.jpg"))
    return cam


def bulb_lights(objs, energy=1.0):
    """Cycles only: raise bulb emission a little for the preview (the engine uses bloom)."""
    for m in bpy.data.materials:
        if m.name.startswith(("bulb_warm", "bulb_cold")):
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Emission Strength"].default_value *= energy


# =================================================================== swept tubes
def sweep(part, pts, ws, hs, n=12, cap0=True, cap1=True, side=(0, 1, 0), smooth=True, **kw):
    """Loft elliptic rings along a path. ws/hs: half width (along `side`) and half height."""
    pts = [Vector(p) for p in pts]
    sv = Vector(side)
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()
        y = sv - t * sv.dot(t)
        if y.length < 1e-6:
            y = Vector((1, 0, 0)) - t * t.x
        y.normalize()
        z = t.cross(y).normalized()
        rings.append([p + y * (ws[i] * math.cos(TAU * j / n)) + z * (hs[i] * math.sin(TAU * j / n))
                      for j in range(n)])
    part.loft(rings, closed=True, cap_start=cap0, cap_end=cap1, smooth=smooth, **kw)


def smooth_path(ctrl, per=3):
    """Catmull-Rom through control tuples (x, y, z, extra...) -> denser list of the same tuples."""
    out = []
    m = len(ctrl)
    for i in range(m - 1):
        p0 = ctrl[max(i - 1, 0)]
        p1, p2 = ctrl[i], ctrl[i + 1]
        p3 = ctrl[min(i + 2, m - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(len(p1))))
    out.append(tuple(ctrl[-1]))
    return out


def pipe(part, ctrl, n=8, per=3, cap0=False, cap1=False, side=(0, 1, 0), **kw):
    """Round tube through control points (x, y, z, r) with a smooth path and tapering radius."""
    pts = smooth_path(ctrl, per)
    sweep(part, [p[:3] for p in pts], [p[3] for p in pts], [p[3] for p in pts], n=n, cap0=cap0,
          cap1=cap1, side=side, **kw)


def shape_on(part, poly, M, depth, holes=(), **kw):
    """2D polygon in the local XY plane of M, extruded along local Z."""
    part.shape(poly, holes=list(holes), depth=depth, M=M, **kw)


def basis(x, y, z, origin=(0, 0, 0)):
    """4x4 matrix with the given column axes at origin."""
    return Matrix.Translation(origin) @ Matrix((Vector(x), Vector(y), Vector(z))).transposed().to_4x4()
