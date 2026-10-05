"""Session state shared by the nmlib modules: paths, random stream, level of detail."""
import os
import random

import bpy

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # blender/lib
BLENDER_DIR = os.path.dirname(LIB_DIR)                                     # blender/
REPO = os.path.dirname(BLENDER_DIR)
OUT_DIR = os.path.join(BLENDER_DIR, "out")          # scratch (gitignored)
KIT_DIR = os.path.join(OUT_DIR, "kit")              # cached kit texture bakes
MODELS_DIR = os.path.join(REPO, "site", "public", "models")
FONTS_DIR = os.path.join(LIB_DIR, "fonts")

rng = random.Random(1)
_lod = {"level": 0, "bevels": True}
EXPORT_COLL = "Export"


def font(name):
    """Path of a bundled font: 'fraktur', 'fraktur_bold', 'fell_sc', 'fell_italic', 'alegreya_sc'."""
    files = {
        "fraktur": "UnifrakturMaguntia-Book.ttf",
        "fraktur_bold": "UnifrakturCook-Bold.ttf",
        "fell_sc": "IMFeENsc28P.ttf",
        "fell_italic": "IMFeENit28P.ttf",
        "alegreya_sc": "AlegreyaSC-ExtraBold.ttf",
    }
    return os.path.join(FONTS_DIR, files.get(name, name))


def seed(n):
    rng.seed(n)


def set_lite(on):
    _lod["level"] = 1 if on else 0


def lite():
    return _lod["level"] > 0


def set_bevels(on):
    """Round 8: False turns off the edge chamfers under 1 cm of Part.box/mbox in a full build, as lite
    does, while keeping full plank widths, shingles, text and the larger rounds (a counter's worn
    front edge). For scenery seen only from a lane (the
    deco stalls): a 4 mm chamfer is invisible from 4 m and triples a board's triangles. reset() turns
    bevels back on."""
    _lod["bevels"] = bool(on)


def bevels():
    return _lod["bevels"] and not lite()


def export_collection():
    c = bpy.data.collections.get(EXPORT_COLL)
    if c is None:
        c = bpy.data.collections.new(EXPORT_COLL)
        bpy.context.scene.collection.children.link(c)
    return c


def env_collection():
    c = bpy.data.collections.get("Env")
    if c is None:
        c = bpy.data.collections.new("Env")
        bpy.context.scene.collection.children.link(c)
    return c


def configure_cycles(scene=None):
    """Cycles device and threads from the environment (docs/BUILD.md, "Where things run"):
    NM_DEVICE = CPU (default) or METAL / CUDA / OPTIX / HIP / ONEAPI for the GPU;
    NM_THREADS = CPU threads, 0 = all cores (default 2). Used by renders and bakes."""
    scene = scene or bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    dev = os.environ.get('NM_DEVICE', 'CPU').upper()
    if dev in ('METAL', 'CUDA', 'OPTIX', 'HIP', 'ONEAPI'):
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = dev
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    threads = int(os.environ.get('NM_THREADS', '2'))
    if threads > 0:
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = threads
    else:
        scene.render.threads_mode = 'AUTO'
    return scene


def reset(seed_value=1, lite_mode=False):
    """Empty the Blender file and set the random seed and LOD for a fresh build."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from . import geo, mats
    mats.forget()
    geo._fonts.clear()
    seed(seed_value)
    set_lite(lite_mode)
    set_bevels(True)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(KIT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    scene = configure_cycles(bpy.context.scene)
    export_collection()
    return scene
