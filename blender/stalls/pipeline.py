"""Shared build pipeline for stall scripts: full model, lite model, preview render.

    python blender/stalls/<stall>.py [--no-render] [--no-lite] [--no-full] [--samples 48]

build(lite) must create everything in the Export collection and return the export objects.
preview(objs) adds render-only stand-ins, lights and the camera (Env collection).
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

from nmlib import bake, export, mats, render, state  # noqa: E402

ROUND = os.environ.get("NM_ROUND", "6")
REVIEW = os.path.join(state.REPO, "review", f"round-{ROUND}", "carpenter")


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--preview-name", default=None)
    ap.add_argument("--cam", default=None, help="x,y,z,tx,ty,tz,lens debug camera")
    ap.add_argument("--read-views", action="store_true",
                    help="after the preview, render the view from every cam_read_<name> empty")
    ap.add_argument("--read-only", action="store_true",
                    help="render only the cam_read views (skip the 3/4 preview)")
    ap.add_argument("--extra-only", action="store_true",
                    help="render only the --extra-view cameras (skip the preview and read views)")
    ap.add_argument("--read-res", default="960x540")
    ap.add_argument("--extra-view", action="append", default=[],
                    help="name=x,y,z,tx,ty,tz[,lens]: one more render at --read-res (repeatable)")
    ap.add_argument("--read-samples", type=int, default=32)
    ap.add_argument("--bloom", type=float, default=0.0,
                    help="round 9: soft glow round the brightest pixels in the review JPEGs (the site's bloom)")
    a, _ = ap.parse_known_args(sys.argv[1:])
    return a


def vendor_props(pairs, rotate=False):
    """Import the vendor's shipped prop glbs [(name, slot), ...] into the preview (render-only),
    so the Cycles preview shows the stall as the site assembles it. Returns True when at least
    one set was found (callers fall back to simple stand-ins otherwise). rotate=True also applies
    the slot's rotation (the Bücherstand's slot_cat_<key> on the angled racks)."""
    got = []
    for name, slot in pairs:
        got += render.import_glb(os.path.join(state.MODELS_DIR, name + ".glb"), at=slot, rotate=rotate)
    return bool(got)


def vendor_sets(asset, rotate=True):
    """Round 8: import every vendor set that props.json places on `asset` (e.g. "stall_schmuck.glb")
    at its slot, for the Cycles preview. Returns True when at least one set was imported."""
    path = os.path.join(state.MODELS_DIR, "props.json")
    if not os.path.exists(path):
        return False
    with open(path) as f:
        sets = json.load(f).get("sets", [])
    pairs = [(s["set"], s["slot"]) for s in sets if s.get("asset") == asset and s.get("slot")]
    import bpy
    pairs = [(n, sl) for (n, sl) in pairs if sl in bpy.data.objects]
    return vendor_props(pairs, rotate=rotate) if pairs else False


def is_hidden_for_ao(o):
    return o.name.startswith(("snow_", "bulbs_"))


def kit_uri(lite):
    """URI of a shared kit texture next to the glb files (deco_kit_*.webp / *.lite.webp)."""
    return lambda name: "deco_" + name + (".lite" if lite else "") + ".webp"


def shared_kit(lite):
    """externalize= value that moves every kit_* texture out of the glb into the shared files."""
    return (lambda n: n.startswith("kit_"), kit_uri(lite))


def build_and_export(name, build, seed, lite, texture_size=None, externalize=None, ao_res=None):
    """ao_res defaults to 768 (full) / 384 (lite). When it equals a kit texture's size the
    glTF exporter packs AO into that roughness/metal image (ORM), which makes the image unique
    to this asset; the defaults avoid every kit size so all kit maps stay shareable.
    externalize: None, "kit" (shared kit files, see shared_kit) or an explicit pair."""
    if externalize == "kit":
        externalize = shared_kit(lite)
    state.reset(seed, lite_mode=lite)
    mats.ensure_kit()
    t0 = time.time()
    objs = build(lite)
    print(f"[{name}] built {'lite' if lite else 'full'} in {time.time() - t0:.1f}s, "
          f"{export.triangles()} tris")
    for o in objs:
        if o.type == 'MESH':
            print(f"     {o.name:30s} {export.triangles([o]):7d}")
    out = name + (".lite" if lite else "")
    bake.bake_ao(objs, out, res=ao_res or (384 if lite else 768), samples=12 if lite else 20,
                 hide=[o for o in objs if is_hidden_for_ao(o)])
    rep = export.export_glb(out, texture_size or (512 if lite else 1024), externalize=externalize)
    return objs, rep


def read_views(name, a):
    """Render the engine's reading view from every cam_read_<name> empty: the desktop camera's
    42 degree vertical field of view at 16:9 (lens 26.4 mm on a 36 mm sensor), no depth of field.
    Saves review/round-N/carpenter/<stall>_read_<name>.jpg."""
    import bpy
    from mathutils import Vector
    w, h = (int(v) for v in a.read_res.split("x"))
    lens = 18.0 / (math.tan(math.radians(21.0)) * w / h)
    out = []
    # only the stall's own reading cameras (the vendor's imported props carry their own)
    for ob in list(state.export_collection().all_objects):
        if not ob.name.startswith("cam_read_") or ob.name.endswith("_target"):
            continue
        key = ob.name[len("cam_read_"):]
        tgt = bpy.data.objects.get(f"cam_read_{key}_target")
        if tgt is None:
            continue
        render.camera(tuple(ob.matrix_world.translation), tuple(tgt.matrix_world.translation), lens=lens)
        pn = f"{name}_read_{key}"
        render.render(os.path.join(state.OUT_DIR, "renders", f"{pn}.png"), samples=a.read_samples,
                      res=(w, h), jpeg=os.path.join(REVIEW, f"{pn}.jpg"), jpeg_width=w)
        out.append(pn)
    return out


def run(name, build, preview=None, seed=1, externalize="kit"):
    a = args()
    reports = {}
    rep_path = os.path.join(state.OUT_DIR, f"{name}_report.json")
    if os.path.exists(rep_path):
        with open(rep_path) as f:
            reports = json.load(f)
    if not a.no_lite:
        _, reports["lite"] = build_and_export(name, build, seed, True, externalize=externalize)
    if not a.no_full:
        objs, reports["full"] = build_and_export(name, build, seed, False, externalize=externalize)
        if preview and not a.no_render:
            render.night_scene()
            cam = preview(objs)
            # the emissive stand-ins (paint_glow, iron_matte, rauten) stand in for light the
            # engine does not cast; the Cycles preview has that light, so switch them off
            mats.standin_emission(False)
            if a.cam:
                v = [float(t) for t in a.cam.split(",")]
                render.camera(v[0:3], v[3:6], lens=v[6] if len(v) > 6 else 35)
            os.makedirs(REVIEW, exist_ok=True)
            if not (a.read_only or a.extra_only):
                w, h = (int(v) for v in a.res.split("x"))
                pn = a.preview_name or f"{name}_preview"
                render.render(os.path.join(state.OUT_DIR, "renders", f"{pn}.png"), samples=a.samples,
                              res=(w, h), jpeg=os.path.join(REVIEW, f"{pn}.jpg"), bloom=a.bloom)
            if (a.read_views or a.read_only) and not a.extra_only:
                read_views(name, a)
            for ev in a.extra_view:
                key, vals = ev.split("=", 1)
                v = [float(t) for t in vals.split(",")]
                render.camera(v[0:3], v[3:6], lens=v[6] if len(v) > 6 else 35)
                w, h = (int(t) for t in a.read_res.split("x"))
                render.render(os.path.join(state.OUT_DIR, "renders", f"{name}_{key}.png"),
                              samples=a.read_samples, res=(w, h),
                              jpeg=os.path.join(REVIEW, f"{name}_{key}.jpg"), jpeg_width=w, bloom=a.bloom)
    with open(rep_path, "w") as f:
        json.dump(reports, f, indent=1)
    for k, r in reports.items():
        print(f"[{name}] {k}: {r['bytes'] / 1e6:.2f} MB, {r['triangles']} tris")
    return reports
