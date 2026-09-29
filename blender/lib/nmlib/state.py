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
_lod = {"level": 0}
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


def reset(seed_value=1, lite_mode=False):
    """Empty the Blender file and set the random seed and LOD for a fresh build."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from . import geo, mats
    mats.forget()
    geo._fonts.clear()
    seed(seed_value)
    set_lite(lite_mode)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(KIT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    export_collection()
    return scene
