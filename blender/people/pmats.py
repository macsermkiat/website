"""Materials and the two small fabric normal maps (knit and woollen twill) for the figures.

The textures are drawn with numpy into blender/out/people/ and embedded in each glb (they are a
few kB as WebP). Base colour: material factor x vertex colour (COLOR_0), so the engine can
recolour coat, scarf and hat by setting material.color.
"""
import os

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TEX_DIR = os.path.join(REPO, "blender", "out", "people")


def _normal_from_height(h, strength):
    gy, gx = np.gradient(h)
    nx, ny = -gx * strength, gy * strength
    nz = np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / L, ny / L, nz / L], -1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def _tile_noise(N, cells, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((cells, cells))
    x = np.linspace(0, cells, N, endpoint=False)
    i0 = np.floor(x).astype(int)
    f = x - i0
    f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells
    a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
    b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def knit_height(N=128, cols=8, rows=10):
    """Stockinette: columns of V-shaped stitches, each leg a slanted soft ellipse."""
    y, x = np.mgrid[0:N, 0:N] / N
    cw, ch = 1 / cols, 1 / rows
    u = (x % cw) / cw           # 0..1 across the column
    v = (y % ch) / ch           # 0..1 along the stitch
    h = np.zeros_like(x)
    for side, cx in ((-1, 0.28), (1, 0.72)):
        du = u - cx
        dv = v - 0.5
        # slanted leg of the V
        a = side * 0.9
        ru = du * np.cos(a) - dv * np.sin(a) * 0.55
        rv = du * np.sin(a) + dv * np.cos(a)
        h = np.maximum(h, np.clip(1 - (ru / 0.2) ** 2 - (rv / 0.62) ** 2, 0, 1) ** 0.6)
    h += 0.15 * _tile_noise(N, 16, 3)
    return h


def twill_height(N=128):
    y, x = np.mgrid[0:N, 0:N] / N
    h = 0.5 + 0.5 * np.sin(2 * np.pi * (x * 12 + y * 12))
    h = h * 0.6 + 0.4 * _tile_noise(N, 32, 5) + 0.35 * _tile_noise(N, 8, 9)
    return h


def ensure_textures():
    from PIL import Image
    os.makedirs(TEX_DIR, exist_ok=True)
    out = {}
    for name, fn, st in (("people_knit_normal", knit_height, 5.0), ("people_wool_normal", twill_height, 2.2)):
        p = os.path.join(TEX_DIR, name + ".png")
        if not os.path.exists(p):
            Image.fromarray(_normal_from_height(fn(), st)).save(p)
        out[name] = p
    return out


def _img(path, name):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(path)
        img.name = name
        img.colorspace_settings.name = "Non-Color"
    return img


def _mat(name, color, rough, normal=None, nstrength=1.0, double=False, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    vc = N.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = N.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (*color, 1)
    L.new(vc.outputs["Color"], mix.inputs[7])
    L.new(mix.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if sheen:
        try:
            b.inputs["Sheen Weight"].default_value = sheen
        except KeyError:
            pass
    if normal:
        uv = N.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        t = N.new("ShaderNodeTexImage")
        t.image = normal
        L.new(uv.outputs[0], t.inputs[0])
        nm = N.new("ShaderNodeNormalMap")
        nm.uv_map = "UVMap"
        nm.inputs["Strength"].default_value = nstrength
        L.new(t.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs[0], b.inputs["Normal"])
    m.use_backface_culling = not double
    return m


def make(spec):
    tex = ensure_textures()
    knit = _img(tex["people_knit_normal"], "people_knit_normal")
    wool = _img(tex["people_wool_normal"], "people_wool_normal")
    from figures import lin
    hat = spec.get("hat") or {"color": "#444444", "style": "beanie"}
    felt = hat["style"] in ("trilby", "flatcap", "beret")
    coat_n = knit if spec["coat"].get("knit") else wool
    return {
        "body": _mat("body", (1, 1, 1), 0.72),
        "coat": _mat("coat", lin(spec["coat"]["color"]), spec["coat"].get("rough", 0.86), coat_n,
                     0.9 if spec["coat"].get("knit") else 0.6, double=True),
        "scarf": _mat("scarf", lin(spec.get("scarf", {}).get("color", "#882222")), 0.93, knit, 0.9, double=True),
        "hat": _mat("hat", lin(hat["color"]), 0.9 if not felt else 0.8, wool if felt else knit,
                    0.35 if felt else 0.9, double=True),
        "mug": _mat("mug", (1, 1, 1), 0.28),
    }
