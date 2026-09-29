"""Materials: the tiling kit textures (baked once from Blender procedurals) and simple materials.

Kit keys (textured, tiling, tinted by COLOR_0):
    wood   1 m tile, light neutral spruce; tints in geo.TINTS make pine/honey/dark/grey/soot
    paint  8 colour bands (geo.PAINT_BANDS) of chipped paint over wood, gold band is metallic
    iron   0.5 m tile, dark forged iron with rust and soot
Simple keys (no texture, still multiplied by COLOR_0):
    snow, bulb_warm, bulb_cold, wire, glass, fir, brass, copper, ember, ornament_red,
    ornament_gold, fabric_red, fabric_white, fabric_green

The kit bakes are cached in blender/out/kit/ and reused by every stall, so all
glb files that use the kit embed byte-identical textures (see export.externalize).
"""
import math
import os

import bpy
import numpy as np

from . import state

KIT_VERSION = "v7"
KIT_RES = {"wood": 1024, "paint": 1024, "iron": 512}
_mats = {}


def forget():
    _mats.clear()


# ============================================================ node helper
class NB:
    """Tiny node-graph helper: numbers or sockets are accepted wherever a value goes."""

    def __init__(self, nt):
        self.nt, self.N, self.L = nt, nt.nodes, nt.links
        tc = self.N.new("ShaderNodeTexCoord")
        sep = self.N.new("ShaderNodeSeparateXYZ")
        self.L.new(tc.outputs["UV"], sep.inputs[0])
        self.u, self.v = sep.outputs[0], sep.outputs[1]

    def _in(self, sock, val):
        if isinstance(val, (int, float)):
            sock.default_value = val
        else:
            self.L.new(val, sock)

    def m(self, op, a, b=None, c=None, clamp=False):
        n = self.N.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        self._in(n.inputs[0], a)
        if b is not None:
            self._in(n.inputs[1], b)
        if c is not None:
            self._in(n.inputs[2], c)
        return n.outputs[0]

    def add(self, *xs):
        r = xs[0]
        for x in xs[1:]:
            r = self.m('ADD', r, x)
        return r

    def mul(self, a, b):
        return self.m('MULTIPLY', a, b)

    def smooth(self, e0, e1, x):
        n = self.N.new("ShaderNodeMapRange")
        n.interpolation_type = 'SMOOTHSTEP'
        self._in(n.inputs["Value"], x)
        n.inputs["From Min"].default_value = e0
        n.inputs["From Max"].default_value = e1
        return n.outputs["Result"]

    def remap(self, x, a0, a1, b0, b1, clamp=True):
        n = self.N.new("ShaderNodeMapRange")
        n.clamp = clamp
        self._in(n.inputs["Value"], x)
        n.inputs["From Min"].default_value = a0
        n.inputs["From Max"].default_value = a1
        n.inputs["To Min"].default_value = b0
        n.inputs["To Max"].default_value = b1
        return n.outputs["Result"]

    def torus(self, nu, nv, off=(0, 0, 0, 0), v_linear=None):
        """4D point on a torus so that noise is periodic in u (and v unless v_linear).
        nu, nv ~ number of features across one texture repeat."""
        ru, rv = nu / (2 * math.pi), nv / (2 * math.pi)
        au = self.m('MULTIPLY', self.u, 2 * math.pi)
        x = self.add(self.mul(self.m('COSINE', au), ru), off[0])
        y = self.add(self.mul(self.m('SINE', au), ru), off[1])
        if v_linear is None:
            av = self.m('MULTIPLY', self.v, 2 * math.pi)
            z = self.add(self.mul(self.m('COSINE', av), rv), off[2])
            w = self.add(self.mul(self.m('SINE', av), rv), off[3])
        else:
            z = self.add(self.mul(self.v, v_linear), off[2])
            w = off[3] + 0.0
        comb = self.N.new("ShaderNodeCombineXYZ")
        self._in(comb.inputs[0], x)
        self._in(comb.inputs[1], y)
        self._in(comb.inputs[2], z)
        return comb.outputs[0], w

    def noise(self, nu, nv, detail=2.0, rough=0.5, distortion=0.0, off=(0, 0, 0, 0), v_linear=None):
        vec, w = self.torus(nu, nv, off, v_linear)
        n = self.N.new("ShaderNodeTexNoise")
        n.noise_dimensions = '4D'
        self.L.new(vec, n.inputs["Vector"])
        self._in(n.inputs["W"], w)
        n.inputs["Scale"].default_value = 1.0
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distortion
        return n.outputs["Fac"]

    def voronoi(self, nu, nv, off=(0, 0, 0, 0)):
        vec, w = self.torus(nu, nv, off)
        n = self.N.new("ShaderNodeTexVoronoi")
        n.voronoi_dimensions = '4D'
        self.L.new(vec, n.inputs["Vector"])
        self._in(n.inputs["W"], w)
        n.inputs["Scale"].default_value = 1.0
        return n.outputs["Distance"], n.outputs["Color"]

    def rgb(self, c):
        n = self.N.new("ShaderNodeRGB")
        n.outputs[0].default_value = (*c, 1)
        return n.outputs[0]

    def mix(self, fac, a, b):
        n = self.N.new("ShaderNodeMix")
        n.data_type = 'RGBA'
        self._in(n.inputs[0], fac)
        self.L.new(a, n.inputs[6]) if not isinstance(a, tuple) else setattr(n.inputs[6], "default_value", (*a, 1))
        self.L.new(b, n.inputs[7]) if not isinstance(b, tuple) else setattr(n.inputs[7], "default_value", (*b, 1))
        return n.outputs[2]

    def sepr(self, col):
        n = self.N.new("ShaderNodeSeparateColor")
        self.L.new(col, n.inputs[0])
        return n.outputs[0]


# ============================================================ procedural kit shaders
def _wood_graph(nb, along_u=False):
    """Returns (colour, roughness, metallic, height) sockets of light neutral spruce.
    Grain runs along V (or along U when along_u; used under paint)."""
    if along_u:  # swap roles: rings depend on v, periodic along u only
        d1 = nb.noise(1, 3, detail=3, off=(3, 1, 2, 0), v_linear=3)
        ring_phase = nb.add(nb.mul(nb.v, 9.0), nb.mul(d1, 1.6))
        fib = nb.noise(6, 0, detail=2, off=(1, 7, 0, 3), v_linear=160)
        tone = nb.noise(2, 0, detail=2, off=(5, 5, 5, 0), v_linear=2)
        ring = nb.m('POWER', nb.add(nb.mul(nb.m('SINE', nb.mul(ring_phase, 2 * math.pi)), 0.5), 0.5), 5.0)
        col = nb.mix(nb.add(nb.mul(ring, 0.55), nb.mul(tone, 0.35)),
                     nb.rgb((0.50, 0.42, 0.33)), nb.rgb((0.26, 0.19, 0.13)))
        col = nb.mix(nb.mul(fib, 0.25), col, nb.rgb((0.20, 0.15, 0.10)))
        height = nb.add(nb.mul(ring, -0.4), nb.mul(fib, 0.3))
        return col, ring, fib, height

    d1 = nb.noise(2, 1.2, detail=3, rough=0.5, off=(0.3, 1.7, 2.1, 0.4))
    d2 = nb.noise(9, 2, detail=2, off=(4.1, 0.2, 1.3, 2.2))
    dist, cell = nb.voronoi(9, 5, off=(7.3, 2.1, 0.7, 5.5))
    sel = nb.smooth(0.86, 0.88, nb.sepr(cell))                     # ~12 % of cells hold a knot
    knot_core = nb.mul(nb.m('SUBTRACT', 1.0, nb.smooth(0.03, 0.10, dist)), sel)
    knot_halo = nb.mul(nb.m('SUBTRACT', 1.0, nb.smooth(0.0, 0.45, dist)), sel)
    # growth rings: integer multiples of u keep the pattern periodic; big low-frequency
    # distortion makes the lines drift and bunch like flat-sawn figure
    phase = nb.add(nb.mul(nb.u, 38.0), nb.mul(d1, 4.5), nb.mul(d2, 0.3), nb.mul(knot_halo, 2.5))
    ring = nb.add(nb.mul(nb.m('SINE', nb.mul(phase, 2 * math.pi)), 0.5), 0.5)
    strength = nb.remap(nb.noise(30, 1.5, detail=1, off=(2.2, 0.1, 5.5, 1.0)), 0.3, 0.7, 0.25, 1.0)
    late = nb.mul(nb.m('POWER', ring, 5.0), strength)
    phase2 = nb.add(nb.mul(nb.u, 11.0), nb.mul(d1, 3.0))
    zone = nb.add(nb.mul(nb.m('SINE', nb.mul(phase2, 2 * math.pi)), 0.5), 0.5)
    fib = nb.noise(150, 4, detail=3, rough=0.65, off=(1.1, 3.3, 0.5, 1.9))
    streak = nb.smooth(0.55, 0.75, nb.noise(7, 1, detail=3, off=(8.8, 4.1, 2.0, 0.3)))
    tone = nb.noise(2, 1.5, detail=3, off=(9.2, 1.4, 3.3, 0.8))
    weather = nb.smooth(0.52, 0.72, nb.noise(5, 2, detail=5, rough=0.6, off=(2.7, 8.1, 1.2, 4.4)))
    dents = nb.noise(38, 30, detail=3, rough=0.6, off=(0.9, 0.4, 6.6, 3.1))
    speck = nb.smooth(0.76, 0.83, nb.noise(260, 180, detail=0, off=(5.5, 2.2, 7.7, 1.1)))
    crack = nb.smooth(0.76, 0.80, nb.noise(120, 1.5, detail=1, off=(3.9, 6.2, 2.5, 8.8)))

    early = nb.rgb((0.56, 0.48, 0.38))
    latec = nb.rgb((0.24, 0.18, 0.12))
    col = nb.mix(nb.add(nb.mul(late, 0.85), nb.mul(zone, 0.18)), early, latec)
    col = nb.mix(nb.mul(tone, 0.45), col, nb.rgb((0.36, 0.29, 0.21)))
    col = nb.mix(nb.mul(streak, 0.35), col, nb.rgb((0.30, 0.22, 0.15)))
    col = nb.mix(nb.mul(fib, 0.30), col, nb.rgb((0.28, 0.23, 0.17)))
    col = nb.mix(nb.mul(weather, 0.40), col, nb.rgb((0.46, 0.45, 0.43)))       # silvering
    col = nb.mix(nb.mul(knot_halo, 0.45), col, nb.rgb((0.30, 0.19, 0.11)))
    col = nb.mix(knot_core, col, nb.rgb((0.10, 0.06, 0.035)))
    col = nb.mix(nb.mul(speck, 0.4), col, nb.rgb((0.10, 0.08, 0.06)))
    col = nb.mix(nb.mul(crack, 0.85), col, nb.rgb((0.06, 0.045, 0.03)))
    rough = nb.add(0.58, nb.mul(fib, 0.18), nb.mul(weather, 0.14), nb.mul(late, -0.10),
                   nb.mul(knot_core, -0.15))
    height = nb.add(nb.mul(late, -0.5), nb.mul(fib, 0.45), nb.mul(dents, 0.35),
                    nb.mul(crack, -1.0), nb.mul(knot_core, 0.25), nb.mul(weather, -0.2))
    return col, rough, 0.0, height


PAINT_COLORS = [  # (linear rgb, roughness, metallic), same order as geo.PAINT_BANDS
    ((0.26, 0.010, 0.014), 0.40, 0.0),   # red
    ((0.80, 0.55, 0.20), 0.30, 1.0),     # gold leaf
    ((0.025, 0.16, 0.50), 0.42, 0.0),    # Bavarian blue
    ((0.74, 0.72, 0.67), 0.48, 0.0),     # white
    ((0.018, 0.085, 0.045), 0.42, 0.0),  # fir green
    ((0.72, 0.58, 0.36), 0.48, 0.0),     # cream
    ((0.022, 0.019, 0.017), 0.38, 0.0),  # black
    ((0.74, 0.74, 0.72), 0.45, 0.0),     # rauten (white + blue lozenges)
]


def _paint_graph(nb):
    nbands = len(PAINT_COLORS)
    vb_raw = nb.mul(nb.v, nbands)
    vb = nb.m('FRACT', vb_raw)
    bidx = nb.m('FLOOR', vb_raw)                          # 0 = bottom band
    # band colour lookup via constant ramps (band k from top is PAINT_COLORS[k])
    def ramp(values_rgb):
        r = nb.N.new("ShaderNodeValToRGB")
        cr = r.color_ramp
        cr.interpolation = 'CONSTANT'
        while len(cr.elements) < nbands:
            cr.elements.new(0.5)
        for i in range(nbands):
            cr.elements[i].position = i / nbands
            cr.elements[i].color = (*values_rgb[nbands - 1 - i], 1)
        nb.L.new(nb.m('DIVIDE', nb.add(bidx, 0.5), nbands), r.inputs[0])
        return r.outputs[0]
    base = ramp([c for c, _, _ in PAINT_COLORS])
    rgh = nb.sepr(ramp([(r, r, r) for _, r, _ in PAINT_COLORS]))
    met = nb.sepr(ramp([(m, m, m) for _, _, m in PAINT_COLORS]))
    # Bavarian lozenges in the bottom band
    x = nb.mul(nb.u, 16.0)
    y = nb.mul(vb, 2.0)
    chk = nb.m('FLOORED_MODULO', nb.add(nb.m('FLOOR', nb.add(x, y)), nb.m('FLOOR', nb.m('SUBTRACT', x, y))), 2.0)
    is_rauten = nb.m('LESS_THAN', bidx, 0.5)
    blue = nb.rgb((0.02, 0.17, 0.52))
    base = nb.mix(nb.mul(chk, is_rauten), base, blue)
    # brush strokes along u, faded paint, chips showing wood near board edges
    strokes = nb.noise(90, 0, detail=2, off=(1, 2, 3, 0), v_linear=nbands * 30)
    fade = nb.noise(4, 0, detail=4, off=(5, 1, 0, 2), v_linear=nbands * 3)
    edge = nb.m('MINIMUM', vb, nb.m('SUBTRACT', 1.0, vb))
    edge_boost = nb.mul(nb.mul(nb.m('SUBTRACT', 1.0, nb.smooth(0.0, 0.14, edge)), 0.22),
                        nb.noise(8, 0, detail=2, off=(2, 9, 4, 1), v_linear=nbands * 2))
    chipn = nb.noise(22, 0, detail=5, rough=0.65, off=(7, 3, 1, 5), v_linear=nbands * 9)
    chip = nb.smooth(0.665, 0.685, nb.add(chipn, edge_boost))
    wcol, _, _, wh = _wood_graph(nb, along_u=True)
    col = nb.mix(nb.mul(nb.m('SUBTRACT', strokes, 0.5), 0.25), base, nb.rgb((0.05, 0.04, 0.03)))
    col = nb.mix(nb.mul(fade, 0.18), col, nb.rgb((0.55, 0.52, 0.47)))
    col = nb.mix(chip, col, nb.mix(0.35, wcol, nb.rgb((0.12, 0.09, 0.06))))
    rough = nb.add(nb.mul(rgh, nb.m('SUBTRACT', 1.0, chip)), nb.mul(chip, 0.8), nb.mul(fade, 0.08))
    metal = nb.mul(met, nb.m('SUBTRACT', 1.0, chip))
    height = nb.add(nb.mul(strokes, 0.25), nb.mul(chip, -0.8), nb.mul(nb.mul(wh, chip), 0.3))
    return col, rough, metal, height


def _iron_graph(nb):
    rust_n = nb.noise(9, 9, detail=6, rough=0.62, off=(1.2, 0.3, 4.4, 2.0))
    rust = nb.smooth(0.60, 0.70, rust_n)
    streak = nb.smooth(0.5, 0.8, nb.noise(30, 2, detail=3, off=(0.4, 2.2, 1.0, 3.0)))
    soot = nb.noise(3, 3, detail=4, off=(6.1, 1.9, 0.2, 3.3))
    hammer_d, _ = nb.voronoi(40, 40, off=(0.5, 0.9, 1.4, 2.2))
    fine = nb.noise(120, 120, detail=2, off=(3.3, 3.1, 0.8, 0.2))
    col = nb.mix(nb.mul(fine, 0.35), nb.rgb((0.05, 0.048, 0.045)), nb.rgb((0.022, 0.021, 0.02)))
    col = nb.mix(nb.mul(streak, 0.25), col, nb.rgb((0.07, 0.05, 0.04)))
    col = nb.mix(nb.mul(rust, 0.8), col, nb.mix(fine, nb.rgb((0.11, 0.045, 0.018)), nb.rgb((0.06, 0.03, 0.015))))
    col = nb.mix(nb.mul(soot, 0.5), col, nb.rgb((0.012, 0.011, 0.010)))
    rough = nb.add(0.45, nb.mul(rust, 0.35), nb.mul(fine, 0.12), nb.mul(streak, 0.08))
    metal = nb.remap(rust, 0, 1, 0.7, 0.15)
    height = nb.add(nb.mul(hammer_d, 0.6), nb.mul(rust_n, 0.4), nb.mul(fine, 0.2))
    return col, rough, metal, height


GRAPHS = {"wood": _wood_graph, "paint": _paint_graph, "iron": _iron_graph}
BUMP = {"wood": (0.9, 0.0012), "paint": (0.8, 0.0008), "iron": (0.7, 0.0012)}


def kit_path(key, kind):
    """Stable file names (they become the glTF image names and the shared deco URIs)."""
    return os.path.join(state.KIT_DIR, f"kit_{key}_{kind}.png")


def _stamp(key):
    return os.path.join(state.KIT_DIR, f"kit_{key}.version")


def ensure_kit():
    """Bake any kit texture set whose files are missing or older than KIT_VERSION."""
    for key in GRAPHS:
        ok = all(os.path.exists(kit_path(key, k)) for k in ("color", "normal", "rm"))
        if ok and os.path.exists(_stamp(key)):
            with open(_stamp(key)) as f:
                ok = f.read().strip() == KIT_VERSION
        else:
            ok = False
        if not ok:
            bake_kit(key)
            with open(_stamp(key), "w") as f:
                f.write(KIT_VERSION)


def bake_kit(key):
    """Bake one tiling kit texture set from its procedural graph onto a unit plane."""
    import time
    t0 = time.time()
    res = KIT_RES[key]
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.cycles.samples = 4
    me = bpy.data.meshes.new("kitplane")
    me.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    ob = bpy.data.objects.new("kitplane", me)
    scene.collection.objects.link(ob)
    m = bpy.data.materials.new(f"kitbake_{key}")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nb = NB(nt)
    col, rough, metal, height = GRAPHS[key](nb)
    emis = nt.nodes.new("ShaderNodeEmission")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value, bump.inputs["Distance"].default_value = BUMP[key]
    nb._in(bump.inputs["Height"], height)
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    me.materials.append(m)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    imgs = {}

    def bake(kind, source, colorspace, float_buf=False):
        img = bpy.data.images.new(f"bake_{key}_{kind}", res, res, float_buffer=float_buf)
        img.colorspace_settings.name = colorspace
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = img
        nt.nodes.active = tn
        for l in list(out.inputs["Surface"].links):
            nt.links.remove(l)
        if kind == "normal":
            nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=0, use_clear=True)
        else:
            nb._in(emis.inputs["Color"], source) if not isinstance(source, (int, float)) else \
                setattr(emis.inputs["Color"], "default_value", (source, source, source, 1))
            nt.links.new(emis.outputs[0], out.inputs["Surface"])
            bpy.ops.object.bake(type='EMIT', margin=0, use_clear=True)
        nt.nodes.remove(tn)
        imgs[kind] = img
        return img

    bake("color", col, "sRGB")
    bake("normal", None, "Non-Color")
    r_img = bake("rough", rough, "Non-Color", True)
    m_img = bake("metal", metal, "Non-Color", True)
    # save colour + normal as PNG, combine roughness (G) and metallic (B)
    for kind in ("color", "normal"):
        img = imgs[kind]
        img.filepath_raw = kit_path(key, kind)
        img.file_format = 'PNG'
        img.save()
    rr = np.array(r_img.pixels[:], dtype=np.float32).reshape(res, res, 4)[..., 0]
    mm = np.array(m_img.pixels[:], dtype=np.float32).reshape(res, res, 4)[..., 0]
    rm = np.ones((res, res, 4), dtype=np.float32)
    rm[..., 1] = np.clip(rr, 0.03, 1.0)
    rm[..., 2] = np.clip(mm, 0.0, 1.0)
    rimg = bpy.data.images.new(f"bake_{key}_rm", res, res)
    rimg.colorspace_settings.name = "Non-Color"
    rimg.pixels.foreach_set(rm.ravel())
    rimg.filepath_raw = kit_path(key, "rm")
    rimg.file_format = 'PNG'
    rimg.save()
    for img in list(imgs.values()) + [rimg]:
        bpy.data.images.remove(img)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.materials.remove(m)
    print(f"[nmlib] baked kit '{key}' {res}px in {time.time() - t0:.1f}s")


# ============================================================ runtime materials
def _node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes["Principled BSDF"], nt.links


def _load(key, kind):
    name = f"kit_{key}_{kind}"
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(kit_path(key, kind))
        img.name = name
        img.colorspace_settings.name = "sRGB" if kind == "color" else "Non-Color"
    return img


def _vcol_multiply(nt, L, color_socket_or_value, bsdf):
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    if isinstance(color_socket_or_value, tuple):
        mix.inputs[6].default_value = (*color_socket_or_value, 1)
    else:
        L.new(color_socket_or_value, mix.inputs[6])
    L.new(vc.outputs["Color"], mix.inputs[7])
    L.new(mix.outputs[2], bsdf.inputs["Base Color"])


def kit_material(key, name=None):
    ensure_kit()
    m, nt, bsdf, L = _node_mat(name or key)
    N = nt.nodes
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tc = N.new("ShaderNodeTexImage"); tc.image = _load(key, "color")
    tr = N.new("ShaderNodeTexImage"); tr.image = _load(key, "rm")
    tn = N.new("ShaderNodeTexImage"); tn.image = _load(key, "normal")
    for t in (tc, tr, tn):
        L.new(uv.outputs[0], t.inputs[0])
    _vcol_multiply(nt, L, tc.outputs["Color"], bsdf)
    sep = N.new("ShaderNodeSeparateColor")
    L.new(tr.outputs["Color"], sep.inputs[0])
    L.new(sep.outputs[1], bsdf.inputs["Roughness"])
    L.new(sep.outputs[2], bsdf.inputs["Metallic"])
    nm = N.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    L.new(tn.outputs["Color"], nm.inputs["Color"])
    L.new(nm.outputs[0], bsdf.inputs["Normal"])
    m["nm_kit"] = key
    return m


SIMPLE = {
    # key: (base colour linear, roughness, metallic, emission colour, emission strength, alpha)
    "snow":          ((0.82, 0.86, 0.93), 0.55, 0.0, None, 0.0, 1.0),
    "bulb_warm":     ((1.0, 0.86, 0.62), 0.3, 0.0, (1.0, 0.64, 0.30), 6.0, 1.0),
    "bulb_cold":     ((0.85, 0.92, 1.0), 0.3, 0.0, (0.75, 0.85, 1.0), 6.0, 1.0),
    "wire":          ((0.02, 0.02, 0.018), 0.45, 0.0, None, 0.0, 1.0),
    "glass":         ((0.85, 0.92, 0.92), 0.04, 0.0, None, 0.0, 0.22),
    "fir":           ((0.030, 0.085, 0.035), 0.72, 0.0, None, 0.0, 1.0),
    "brass":         ((0.78, 0.56, 0.26), 0.32, 1.0, None, 0.0, 1.0),
    "copper":        ((0.80, 0.42, 0.26), 0.30, 1.0, None, 0.0, 1.0),
    "ember":         ((0.25, 0.05, 0.01), 0.9, 0.0, (1.0, 0.28, 0.05), 3.0, 1.0),
    "ornament_red":  ((0.50, 0.015, 0.02), 0.18, 0.0, None, 0.0, 1.0),
    "ornament_gold": ((0.90, 0.64, 0.24), 0.22, 1.0, None, 0.0, 1.0),
    "fabric_red":    ((0.35, 0.02, 0.025), 0.85, 0.0, None, 0.0, 1.0),
    "fabric_white":  ((0.70, 0.68, 0.64), 0.85, 0.0, None, 0.0, 1.0),
    "fabric_green":  ((0.03, 0.12, 0.06), 0.85, 0.0, None, 0.0, 1.0),
    "lamp_glass":    ((1.0, 0.85, 0.6), 0.1, 0.0, (1.0, 0.7, 0.4), 4.0, 1.0),
}


def simple_material(key, name=None):
    col, rough, metal, emit, strength, alpha = SIMPLE[key]
    m, nt, bsdf, L = _node_mat(name or key)
    _vcol_multiply(nt, L, col, bsdf)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        for attr, val in (("blend_method", 'BLEND'), ("surface_render_method", 'BLENDED')):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    return m


def get(key):
    """Material for a key (created once per build). Kit keys are textured, others simple."""
    if key not in _mats:
        _mats[key] = kit_material(key) if key in GRAPHS else simple_material(key)
    return _mats[key]
