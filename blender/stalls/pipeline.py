"""Shared build pipeline for stall scripts: full model, lite model, preview render.

    python blender/stalls/<stall>.py [--no-render] [--no-lite] [--no-full] [--samples 48]

build(lite) must create everything in the Export collection and return the export objects.
preview(objs) adds render-only stand-ins, lights and the camera (Env collection).
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

from nmlib import bake, export, mats, render, state  # noqa: E402

REVIEW = os.path.join(state.REPO, "review", "round-1", "carpenter")


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--preview-name", default=None)
    ap.add_argument("--cam", default=None, help="x,y,z,tx,ty,tz,lens debug camera")
    a, _ = ap.parse_known_args(sys.argv[1:])
    return a


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
            if a.cam:
                v = [float(t) for t in a.cam.split(",")]
                render.camera(v[0:3], v[3:6], lens=v[6] if len(v) > 6 else 35)
            os.makedirs(REVIEW, exist_ok=True)
            w, h = (int(v) for v in a.res.split("x"))
            pn = a.preview_name or f"{name}_preview"
            render.render(os.path.join(state.OUT_DIR, "renders", f"{pn}.png"), samples=a.samples,
                          res=(w, h), jpeg=os.path.join(REVIEW, f"{pn}.jpg"))
    with open(rep_path, "w") as f:
        json.dump(reports, f, indent=1)
    for k, r in reports.items():
        print(f"[{name}] {k}: {r['bytes'] / 1e6:.2f} MB, {r['triangles']} tris")
    return reports
