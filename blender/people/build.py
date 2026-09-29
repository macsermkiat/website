"""Build the organizer's figures: skinned glb + lite glb per figure, and the shared clip library.

    NM_DEVICE=METAL NM_THREADS=0 NPM_CONFIG_PREFIX=~/nachtmarkt-tools/npm \
        ~/nachtmarkt-tools/bpy-venv/bin/python blender/people/build.py [--only name,name] [--no-lite] [--no-anims]

Writes site/public/models/people_*.glb and *.lite.glb via blender/lib/optimize.mjs,
site/public/models/people_anims.glb (every crowd and vendor clip on one skeleton, no mesh), and a
report to blender/out/people/report.json.

Each figure file carries only the clips its role uses (CLIPSETS), because in glTF every animation
channel costs about 200 bytes of JSON whatever its length: the clips were 60 % of a lite file.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))

import bpy  # noqa: E402

import rig  # noqa: E402
import pao  # noqa: E402
import figures  # noqa: E402
import pmats  # noqa: E402
import anims  # noqa: E402
import specs  # noqa: E402

MODELS = os.path.join(REPO, "site", "public", "models")
OUT = os.path.join(REPO, "blender", "out", "people")
RAW = os.path.join(OUT, "raw")
OPT = os.path.join(REPO, "blender", "lib", "optimize.mjs")
SLIM = os.path.join(HERE, "slim_anims.mjs")
FPS = 24


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    coll = bpy.data.collections.new("Export")
    scene.collection.children.link(coll)
    return scene, coll


# Which clips each figure file carries. The four the brief checks (idle, walk, chat, drink) are in every file.
# Crowd lite drops laugh and chat_free (the engine falls back to idle) and sit: crowd.json lists the bench
# sitters after the lite cap, so the lite market never needs it. laugh_free and sit_free are not shipped at
# all: crowd.json gives laughers and sitters a mug.
CLIPSETS = {
    ("crowd", False): ["idle", "walk", "chat", "drink", "laugh", "sit", "idle_free", "walk_free", "chat_free"],
    ("crowd", True): ["idle", "walk", "chat", "drink", "idle_free", "walk_free"],
    ("band", False): ["play", "rest", "idle", "walk", "chat", "drink"],
    ("band", True): ["play", "rest", "idle", "walk", "chat", "drink"],
    ("vendor", False): ["serve", "wipe", "idle", "walk", "chat", "drink"],
    ("vendor", True): ["serve", "wipe", "idle", "walk", "chat", "drink"],
}
# the shared library (people_anims.glb): every crowd and vendor clip on the reference skeleton
LIBRARY = ["idle", "walk", "chat", "drink", "laugh", "sit", "idle_free", "walk_free", "chat_free", "laugh_free",
           "sit_free", "serve", "wipe"]
LIBRARY_REF = "people_man_coat"


def clip_list(fig, spec):
    """Every clip this figure can play, as (name, fn(t) -> pose, duration). Baking picks from it by CLIPSETS."""
    c, out = anims.crowd_clips(fig)
    role = spec.get("role")
    if role == "band":
        inst = spec["inst"]
        out = [("play", lambda t: c.band_play(t, inst), 8.0)] + out
        seated = inst in ("piano", "drums")
        if seated:
            seat = 0.5175 if inst == "piano" else 0.54
            out.append(("rest", lambda t: dict(c.sit(t, mug=False, seat=seat, lean=0.0), _mug=0.0), 6.0))
        else:
            out.append(("rest", lambda t: dict(c.idle(t, mug=False), _mug=0.0), 6.0))
    elif role == "vendor":
        out = [("serve", lambda t: c.serve(t), 6.0), ("wipe", lambda t: dict(c.wipe(t), _mug=0.0), 4.0)] + out
    # clips named *_free, play, wipe and rest hide the mug; so does serve for vendors who sell no drinks
    no_serve_mug = spec.get("serve_mug", True) is False
    wrapped = []
    for name, fn, dur in out:
        hide = name.endswith("_free") or name in ("play", "rest", "wipe") or (name == "serve" and no_serve_mug)
        if hide:
            wrapped.append((name, (lambda fn: lambda t: dict(fn(t), _mug=0.0))(fn), dur))
        else:
            wrapped.append((name, fn, dur))
    return c, wrapped


def assemble(spec, lite, coll, bake=True, name=None, ao=False, clips_wanted=None):
    fig = figures.Figure(spec, lite).build()
    mats = pmats.make(spec, lite)
    arm = rig.make_armature(name or spec["name"], fig.J, coll)
    body = fig.m.to_object("body", mats, arm, coll)
    mug = fig.mug.to_object("mug", mats, arm, coll) if fig.mug.V else None
    if ao:
        # rest pose, before any NLA track exists
        pao.bake([body, mug], spec["name"] + (".lite" if lite else ""), 128 if lite else 256, os.path.join(OUT, "ao"))
    clips = []
    if bake:
        want = clips_wanted or CLIPSETS[(spec.get("role", "crowd"), lite)]
        c, allc = clip_list(fig, spec)
        by = {n: (n, f, d) for n, f, d in allc}
        clips = [by[n] for n in want]
        for cname, fn, dur in clips:
            step = 2 if cname.startswith("walk") else 3
            rig.bake_clip(arm, cname, fn, dur, fps=FPS, step=step)
        rig.clear_pose(arm)
    return fig, arm, body, mug, clips


def trim_glb(path):
    """Drop JSON defaults the optimiser writes (accessor "normalized": false), then re-pad the chunks."""
    import struct
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    for a in j.get("accessors", []):
        if a.get("normalized") is False:
            del a["normalized"]
        if a.get("byteOffset") == 0:
            del a["byteOffset"]
    js = json.dumps(j, separators=(",", ":"), ensure_ascii=False).encode()
    js += b" " * (-len(js) % 4)
    rest = b[20 + n:]
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(rest)) + struct.pack("<II", len(js), 0x4E4F534A) + js + rest
    open(path, "wb").write(out)


def export(fname, coll, lite, texture_size=None):
    os.makedirs(RAW, exist_ok=True)
    raw = os.path.join(RAW, fname + ".glb")
    out = os.path.join(MODELS, fname + ".glb")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in coll.all_objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=raw, export_format='GLB', use_selection=True, export_apply=False, export_yup=True,
        export_texcoords=True, export_normals=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False,
        export_skins=True, export_def_bones=False, export_animations=True, export_animation_mode='ACTIONS',
        export_nla_strips=True, export_force_sampling=True, export_frame_step=1, export_anim_single_armature=True,
        export_optimize_animation_size=True, export_reset_pose_bones=True, export_rest_position_armature=True,
        export_morph=False, export_cameras=False, export_lights=False, export_extras=False,
        export_image_format='AUTO', export_influence_nb=4)
    slim = os.path.join(RAW, fname + ".slim.glb")
    r = subprocess.run(["node", SLIM, raw, slim], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise RuntimeError("slim_anims failed")
    size = texture_size or ("128" if lite else "256")
    r = subprocess.run(["node", OPT, slim, out, "--texture-size", str(size)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise RuntimeError("optimize failed")
    trim_glb(out)
    return out


def build_library(report):
    """people_anims.glb: the reference skeleton with every crowd and vendor clip and no mesh. Bone names are
    shared by all figures, so three.js can play these clips on any figure by name (see NOTES.md)."""
    scene, coll = reset()
    spec = dict(specs.BY_NAME[LIBRARY_REF])
    fig = figures.Figure(spec, False).build()
    arm = rig.make_armature("people_anims", fig.J, coll)
    c, allc = clip_list(fig, dict(spec, role="vendor", serve_mug=True))
    by = {n: (n, f, d) for n, f, d in allc}
    for cname in LIBRARY:
        n_, fn, dur = by[cname]
        rig.bake_clip(arm, cname, fn, dur, fps=FPS, step=2 if cname.startswith("walk") else 3)
    rig.clear_pose(arm)
    path = export("people_anims", coll, False)
    info = glb_info(path)
    info["reference"] = LIBRARY_REF
    info["hips_rest"] = [round(v, 4) for v in (fig.J["pelvis"].x, fig.J["pelvis"].z, -fig.J["pelvis"].y)]
    report["people_anims"] = info
    print(f"[people] people_anims: {info['bytes'] / 1e3:.0f} kB, {len(info['animations'])} clips")


def glb_info(path):
    import struct
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    tris = 0
    for m in j.get("meshes", []):
        for p in m["primitives"]:
            if "indices" in p:
                tris += j["accessors"][p["indices"]]["count"] // 3
    return {
        "bytes": len(b), "triangles": tris,
        "animations": [a.get("name") for a in j.get("animations", [])],
        "materials": [m.get("name") for m in j.get("materials", [])],
        "occlusion": [m.get("name") for m in j.get("materials", []) if "occlusionTexture" in m],
        "nodes": len(j.get("nodes", [])),
        "skins": len(j.get("skins", [])),
        "joints": len(j["skins"][0]["joints"]) if j.get("skins") else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-anims", action="store_true")
    ap.add_argument("--no-ao", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    want = [x for x in a.only.split(",") if x]
    os.makedirs(OUT, exist_ok=True)
    rep_path = os.path.join(OUT, "report.json")
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}
    for spec in specs.ALL:
        if want and spec["name"] not in want:
            continue
        for lite in ((False,) if a.no_lite else (False, True)):
            t0 = time.time()
            scene, coll = reset()
            fig, arm, body, mug, clips = assemble(spec, lite, coll, ao=not a.no_ao)
            fname = spec["name"] + (".lite" if lite else "")
            path = export(fname, coll, lite)
            info = glb_info(path)
            info["blender_tris"] = fig.m.tris + fig.mug.tris
            info["hips_rest"] = [round(v, 4) for v in (fig.J["pelvis"].x, fig.J["pelvis"].z, -fig.J["pelvis"].y)]
            report[fname] = info
            print(f"[people] {fname}: {info['triangles']} tris, {info['bytes'] / 1e3:.0f} kB, "
                  f"{len(info['animations'])} clips, {time.time() - t0:.1f}s")
    if not a.no_anims and not want:
        build_library(report)
    json.dump(report, open(rep_path, "w"), indent=1)


if __name__ == "__main__":
    main()
