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
    /home/claude/tools/bpy-venv/bin/python blender/rides/ferris.py [--no-render] [--no-lite]
    (renders honour NM_DEVICE and NM_THREADS; previews default to 1280x720, 48 samples, with a
    1280 px JPEG in review/round-$NM_ROUND/rides/ (default round 2); iterate with --res 960x540
    --samples 32)
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

REVIEW = os.path.join(state.REPO, "review", f"round-{os.environ.get('NM_ROUND', '2')}", "rides")
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
        # gilding as bronze-powder paint, half metallic like the carpenter's gold band (v11):
        # fully metallic gold went near-black in three.js wherever no bright reflection reached it
        "gilt":       ((0.90, 0.60, 0.21), 0.30, 0.5, None, 0.0, 1.0),
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
        # gondola windows: thinner and lighter than the kit glass, a little soft, so a pane seen
        # edge-on from the ride seat (or two panes behind each other) does not go dark
        "gondola_glass": ((0.80, 0.84, 0.86), 0.18, 0.0, None, 0.0, 0.08),
    }
    for k, v in extra.items():
        mats.SIMPLE.setdefault(k, v)


register_materials()


# ------------------------------------------------------------------ image materials
# key -> (png path, roughness): a printed or painted picture (posters, price boards) mapped 0..1
# on a quad made by `picture()`. Created on demand by mats.get like the other materials.
IMAGE_MATS = {}
_mats_get = mats.get


def image_material(key, png, rough=0.8, emit=0.0):
    """emit > 0: the picture also glows faintly in its own colours (glTF emissiveTexture), for a
    print lit by a lamp the browser has no real light for (the Karussell ticket, round 7)."""
    m, nt, bsdf, L = mats._node_mat(key)
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.get(key) or bpy.data.images.load(png)
    img.name = key
    tex.image = img
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    L.new(uv.outputs[0], tex.inputs[0])
    mats._vcol_multiply(nt, L, tex.outputs["Color"], bsdf)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    if emit > 0.0:
        L.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


def _get(key):
    if key in IMAGE_MATS and key not in mats._mats:
        mats._mats[key] = image_material(key, *IMAGE_MATS[key])
    return _mats_get(key)


mats.get = _get


def picture(name, key, corners, tint=(1, 1, 1), coll=None):
    """A quad (4 world points: bottom-left, bottom-right, top-right, top-left seen from the front)
    showing image material `key` with UVs 0..1."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(c) for c in corners], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
    ca.data.foreach_set("color", [*tint, 1.0] * 4)
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or state.export_collection()).objects.link(ob)
    me.materials.append(mats.get(key))
    ob["nm_mat"] = key
    return ob


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


def needle_garland(fir, beads, a, b, sag=0.3, radius=0.07, sprigs_per_m=30, bead_every=0.7, lite=None):
    """Fir rope between a and b made of needle sprigs (thin cones fanning out from the rope,
    darker at the core, a few lighter new tips), with a few large glass baubles. Reads as fir
    at stage distance, where round tufts with many small baubles read as holly.
    beads: {"ornament_red": Part, "ornament_gold": Part}."""
    lite = state.lite() if lite is None else lite
    R = state.rng
    a, b = Vector(a), Vector(b)
    n = 8 if lite else 18
    pts = geo.catenary(a, b, sag, n)
    fir.tube(pts, radius * 0.38, tseg=4 if lite else 5, var=0.1, tint=(0.8, 0.8, 0.8))
    L = (b - a).length
    tang = (b - a).normalized()
    count = int(L * (sprigs_per_m * 0.4 if lite else sprigs_per_m))
    for k in range(count):
        t = (k + R.random()) / count
        p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        for j in range(2 if lite else 3):
            d = Vector((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(-0.8, 1)))
            d = (d - tang * d.dot(tang) * 0.6).normalized()
            ln = radius * R.uniform(1.05, 1.6)
            tip = R.random() < 0.18
            tint = (1.5, 1.45, 1.1) if tip else (R.uniform(0.75, 1.1),) * 3
            rod(fir, p + d * radius * 0.2, p + d * ln, radius * 0.24, r2=0.0, seg=3, tint=tint, smooth=False)
    nb = max(1, int(L / bead_every))
    keys = list(beads)
    for k in range(nb):
        t = (k + 0.5) / nb
        p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t))) + Vector((0, 0, -radius * 0.9))
        part = beads[keys[k % len(keys)]]
        rr = R.uniform(0.028, 0.036)
        part.sphere(p, rr, seg=6 if lite else 10, rings=4 if lite else 7, var=0.05)
        rod(part, p + Vector((0, 0, rr * 0.9)), p + Vector((0, 0, rr * 1.35)), rr * 0.3, seg=6)


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
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--preview-only", action="store_true",
                    help="build the full model and render the preview, without AO bake or export")
    ap.add_argument("--only", default=None)
    ap.add_argument("--cam", default=None, help="x,y,z,tx,ty,tz,lens debug camera")
    ap.add_argument("--preview-name", default=None)
    ap.add_argument("--count", action="store_true",
                    help="build lite and full and print triangle counts and named nodes, no bake or export")
    a, _ = ap.parse_known_args(sys.argv[1:])
    return a


def hidden_for_ao(o):
    return o.name.startswith(("snow_", "bulbs_"))


def mesh_objs():
    return [o for o in state.export_collection().all_objects if o.type == 'MESH']


def _webp_size(blob):
    try:
        import io
        from PIL import Image
        return Image.open(io.BytesIO(blob)).size[0]
    except Exception:
        return 0


def share_kit_textures(glb_path):
    """Move the kit textures (kit_*) out of an exported glb into shared files next to it.

    A kit map that is byte-identical to one of the carpenter's shared deco kit files
    (deco_kit_*.webp / *.lite.webp, which the market loads anyway) points at that file.
    Anything else (the ride builder's own rsteel kit, other sizes) goes to
    rides_kit_<name>_<px>.webp, shared by every ride file that uses the same map at the same
    size. Returns {uri: bytes}."""
    import hashlib
    sys.path.insert(0, os.path.join(state.REPO, "blender", "lib"))
    import glb_tools
    js, binc = glb_tools.read_glb(glb_path)
    bvs = js.get("bufferViews", [])
    uris = {}
    for im in js.get("images", []):
        nm = im.get("name", "")
        if "bufferView" not in im or not nm.startswith("kit_"):
            continue
        bv = bvs[im["bufferView"]]
        blob = binc[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        sha = hashlib.sha1(blob).hexdigest()
        choice = None
        for cand in (f"deco_{nm}.webp", f"deco_{nm}.lite.webp"):
            fp = os.path.join(state.MODELS_DIR, cand)
            if os.path.exists(fp):
                with open(fp, "rb") as f:
                    if hashlib.sha1(f.read()).hexdigest() == sha:
                        choice = cand
                        break
        uris[nm] = choice or f"rides_{nm}_{_webp_size(blob)}.webp"
    if not uris:
        return {}
    written = glb_tools.externalize_images(glb_path, lambda n: n in uris, lambda n: uris[n], state.MODELS_DIR)
    return {u: os.path.getsize(os.path.join(state.MODELS_DIR, u)) for u in written}


def check_uris(glb_path):
    """Every external image a ride glb points at (shared deco_kit_* / rides_kit_* maps) must exist
    next to it, or the market shows it untextured (round 2 judges). Raises on a missing file."""
    sys.path.insert(0, os.path.join(state.REPO, "blender", "lib"))
    import glb_tools
    js, _ = glb_tools.read_glb(glb_path)
    missing = [im["uri"] for im in js.get("images", []) if "uri" in im
               and not os.path.exists(os.path.join(os.path.dirname(glb_path), im["uri"]))]
    if missing:
        raise RuntimeError(f"{os.path.basename(glb_path)} points at missing textures: {missing}")
    return [im["uri"] for im in js.get("images", []) if "uri" in im]


def build_and_export(name, build, seed, lite, ao_res=None, texture_size=None, ao_samples=None):
    """ao_res defaults to 768 (full) / 384 (lite): an AO atlas the size of a kit roughness map
    (1024, or 512 for rsteel, iron and every lite kit map) is packed into that map by the glTF
    exporter (ORM), which makes the map unique to this file. At other sizes every kit map stays
    shareable (share_kit_textures)."""
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
    bake.bake_ao(objs, out, res=ao_res or (384 if lite else 768),
                 samples=ao_samples or (10 if lite else 16),
                 hide=[o for o in objs if hidden_for_ao(o)])
    rep = export.export_glb(out, texture_size or (512 if lite else 1024))
    ext = share_kit_textures(os.path.join(state.MODELS_DIR, out + ".glb"))
    rep["bytes"] = os.path.getsize(os.path.join(state.MODELS_DIR, out + ".glb"))
    rep["external"] = ext
    rep["uris"] = check_uris(os.path.join(state.MODELS_DIR, out + ".glb"))
    print(f"[{name}] {out}.glb {rep['bytes'] / 1e6:.2f} MB after sharing kit maps: {sorted(ext)}")
    return objs, rep


def run(name, build, preview=None, seed=1, ao_full=768, ao_lite=384, tex_full=1024, tex_lite=512,
        ground=60):
    a = args()
    if a.preview_only:
        state.reset(seed, lite_mode=False)
        mats.ensure_kit()
        build(False)
        do_preview(name, mesh_objs(), preview, a, ground=ground)
        return {}
    if a.count:
        for lite in ((True,) if a.no_full else (False,) if a.no_lite else (True, False)):
            state.reset(seed, lite_mode=lite)
            mats.ensure_kit()
            build(lite)
            objs = mesh_objs()
            print(f"[{name}] COUNT {'lite' if lite else 'full'}: {export.triangles()} tris")
            for o in sorted(objs, key=lambda o: -export.triangles([o]))[:int(os.environ.get("RC_TOP", "16"))]:
                print(f"     {o.name:30s} {export.triangles([o]):7d}")
            names = sorted(o.name for o in state.export_collection().all_objects
                           if o.name.startswith(("write_", "cam_", "slot_", "rot_", "light_", "gondola_seat", "horse_seat")))
            print(f"[{name}] nodes: {names}")
        return {}
    rep_path = os.path.join(state.OUT_DIR, f"{name}_report.json")
    reports = {}
    if os.path.exists(rep_path):
        with open(rep_path) as f:
            reports = json.load(f)
    if not a.no_lite:
        _, reports["lite"] = build_and_export(name, build, seed, True, ao_lite, tex_lite)
        with open(rep_path, "w") as f:
            json.dump(reports, f, indent=1)
    if not a.no_full:
        objs, reports["full"] = build_and_export(name, build, seed, False, ao_full, tex_full)
        with open(rep_path, "w") as f:
            json.dump(reports, f, indent=1)
        if preview and not a.no_render:
            do_preview(name, objs, preview, a, ground=ground)
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
    reads = [r for r in os.environ.get("NM_READ", "").split(",") if r]
    if reads:
        # reading views: the camera at cam_read_<name>, looking at its target, with the site's
        # 42 degree vertical field of view (26.3 mm on a 36 mm sensor at 16:9)
        for r in reads:
            bpy.context.view_layer.update()
            p = bpy.data.objects[f"cam_read_{r}"].matrix_world.translation
            t = bpy.data.objects[f"cam_read_{r}_target"].matrix_world.translation
            render.camera(tuple(p), tuple(t), lens=26.3)
            bpy.context.scene.camera.data.clip_start = 0.02
            render.render(os.path.join(state.OUT_DIR, "renders", f"{name}_read_{r}.png"), samples=a.samples,
                          res=(w, h), jpeg=os.path.join(REVIEW, f"{name}_read_{r}.jpg"))
        return cam
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
