"""Materials: the tiling kit textures (baked once from Blender procedurals) and simple materials.

Kit keys (textured, tiling, tinted by COLOR_0):
    wood   1 m tile, light neutral spruce; tints in geo.TINTS make pine/honey/dark/grey/soot
    oak    1 m tile, ring-porous oak for counter tops: pores, rays, scratches, mug rings
    paint  8 colour bands (geo.PAINT_BANDS) of chipped paint over wood, gold band is metallic
    iron   0.5 m tile, forged iron: hammer dents, rust blooms and streaks, soot, pitting
Simple keys (no texture, still multiplied by COLOR_0):
    snow, bulb_warm, bulb_cold, wire, glass, fir, brass, copper, ember, ash, ornament_red,
    ornament_gold, fabric_red, fabric_white, fabric_green, lamp_glass

The kit bakes are cached in blender/out/kit/ and reused by every stall, so all
glb files that use the kit embed byte-identical textures (see export.externalize).
"""
import math
import os

import bpy
import numpy as np

from . import state

KIT_VERSION = "v11"  # v11: gold paint half metallic (was 1.0, went black in three.js); v10: iron rust in smaller, browner blooms; v9: oak with more figure and contrast; v8: metal of constant-valued kits bakes to 0 (was the roughness); new wood/iron/oak
KIT_RES = {"wood": 1024, "oak": 1024, "paint": 1024, "iron": 512}
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
    strength = nb.remap(nb.noise(30, 1.5, detail=1, off=(2.2, 0.1, 5.5, 1.0)), 0.35, 0.65, 0.45, 1.0)
    # latewood: a hard dark band per ring (about a quarter of the ring), sharp on the outer side
    late = nb.mul(nb.smooth(0.52, 0.93, ring), strength)
    phase2 = nb.add(nb.mul(nb.u, 11.0), nb.mul(d1, 3.0))
    zone = nb.add(nb.mul(nb.m('SINE', nb.mul(phase2, 2 * math.pi)), 0.5), 0.5)
    # fibre: fine streaks along the grain, stretched noise remapped to full contrast
    fib = nb.remap(nb.noise(150, 4, detail=3, rough=0.65, off=(1.1, 3.3, 0.5, 1.9)), 0.36, 0.64, 0.0, 1.0)
    # pores / resin canals: short dark dashes along the grain, a few px long
    pore = nb.smooth(0.60, 0.70, nb.noise(230, 14, detail=1, off=(6.1, 0.7, 3.3, 2.9)))
    fleck = nb.smooth(0.63, 0.72, nb.noise(90, 40, detail=1, off=(2.9, 5.1, 0.8, 7.3)))
    streak = nb.smooth(0.55, 0.72, nb.noise(7, 1, detail=3, off=(8.8, 4.1, 2.0, 0.3)))
    tone = nb.remap(nb.noise(2, 1.5, detail=3, off=(9.2, 1.4, 3.3, 0.8)), 0.35, 0.65, 0.0, 1.0)
    weather = nb.smooth(0.54, 0.70, nb.noise(5, 2, detail=5, rough=0.6, off=(2.7, 8.1, 1.2, 4.4)))
    dents = nb.remap(nb.noise(38, 30, detail=3, rough=0.6, off=(0.9, 0.4, 6.6, 3.1)), 0.3, 0.7, 0.0, 1.0)
    speck = nb.smooth(0.72, 0.80, nb.noise(260, 180, detail=0, off=(5.5, 2.2, 7.7, 1.1)))
    crack = nb.smooth(0.74, 0.79, nb.noise(120, 1.5, detail=1, off=(3.9, 6.2, 2.5, 8.8)))

    early = nb.rgb((0.62, 0.52, 0.40))
    latec = nb.rgb((0.20, 0.135, 0.08))
    col = nb.mix(nb.add(nb.mul(late, 0.9), nb.mul(zone, 0.15)), early, latec)
    col = nb.mix(nb.mul(tone, 0.30), col, nb.rgb((0.40, 0.31, 0.22)))
    col = nb.mix(nb.mul(streak, 0.30), col, nb.rgb((0.30, 0.21, 0.14)))
    col = nb.mix(nb.mul(fib, 0.38), col, nb.rgb((0.26, 0.20, 0.14)))
    col = nb.mix(nb.mul(pore, 0.55), col, nb.rgb((0.14, 0.10, 0.07)))
    col = nb.mix(nb.mul(fleck, 0.25), col, nb.rgb((0.66, 0.58, 0.47)))
    col = nb.mix(nb.mul(weather, 0.30), col, nb.rgb((0.44, 0.43, 0.41)))       # silvering
    col = nb.mix(nb.mul(knot_halo, 0.50), col, nb.rgb((0.30, 0.18, 0.10)))
    col = nb.mix(knot_core, col, nb.rgb((0.09, 0.05, 0.03)))
    col = nb.mix(nb.mul(speck, 0.5), col, nb.rgb((0.10, 0.08, 0.06)))
    col = nb.mix(nb.mul(crack, 0.9), col, nb.rgb((0.05, 0.035, 0.025)))
    rough = nb.add(0.56, nb.mul(fib, 0.16), nb.mul(weather, 0.14), nb.mul(late, -0.10),
                   nb.mul(knot_core, -0.15), nb.mul(pore, 0.08))
    height = nb.add(nb.mul(late, -0.55), nb.mul(fib, 0.40), nb.mul(dents, 0.30), nb.mul(pore, -0.45),
                    nb.mul(crack, -1.0), nb.mul(knot_core, 0.25), nb.mul(weather, -0.2))
    return col, rough, 0.0, height


def _oak_graph(nb):
    """Ring-porous oak for counter tops: wide rings with a band of open pores at the start of
    each ring, silver-grain ray flecks, oiled sheen, fine scratches across the grain and the
    odd mug ring. Grain along V, like the spruce tile."""
    d1 = nb.noise(2, 1.2, detail=3, rough=0.5, off=(5.3, 0.7, 1.1, 2.4))
    d2 = nb.noise(7, 2.5, detail=2, off=(2.9, 4.1, 0.6, 7.7))
    phase = nb.add(nb.mul(nb.u, 17.0), nb.mul(d1, 6.0), nb.mul(d2, 0.8))
    ringf = nb.m('FRACT', phase)                                   # 0 at the start of a ring
    porezone = nb.m('SUBTRACT', 1.0, nb.smooth(0.0, 0.30, ringf))  # earlywood pore band
    pores = nb.mul(nb.smooth(0.56, 0.66, nb.noise(260, 20, detail=1, off=(0.3, 4.4, 2.2, 6.1))), porezone)
    latepores = nb.smooth(0.66, 0.74, nb.noise(200, 24, detail=1, off=(7.7, 1.9, 4.8, 0.2)))
    rays = nb.smooth(0.62, 0.70, nb.noise(60, 26, detail=2, off=(1.4, 6.6, 3.0, 5.2)))
    fib = nb.remap(nb.noise(140, 5, detail=3, rough=0.6, off=(4.2, 2.8, 7.1, 0.9)), 0.36, 0.64, 0.0, 1.0)
    tone = nb.remap(nb.noise(2, 1.5, detail=3, off=(3.6, 8.2, 1.7, 4.0)), 0.35, 0.65, 0.0, 1.0)
    # scratches: thin marks running across the grain (along u), short in v
    scr = nb.smooth(0.70, 0.76, nb.noise(4, 320, detail=1, off=(2.4, 0.6, 9.1, 3.7)))
    scr = nb.mul(scr, nb.smooth(0.5, 0.62, nb.noise(12, 6, detail=1, off=(8.1, 3.3, 0.4, 1.8))))
    # mug rings: a few faint circles where hot mugs stood
    dist, cell = nb.voronoi(5, 5, off=(3.2, 7.4, 2.6, 0.9))
    ring_sel = nb.smooth(0.50, 0.55, nb.sepr(cell))
    mug = nb.mul(nb.m('SUBTRACT', 1.0, nb.smooth(0.0, 0.028, nb.m('ABSOLUTE', nb.m('SUBTRACT', dist, 0.2)))), ring_sel)
    stain = nb.smooth(0.55, 0.75, nb.noise(6, 4, detail=4, rough=0.6, off=(6.6, 2.1, 5.4, 3.3)))

    light = nb.rgb((0.60, 0.45, 0.28))
    dark = nb.rgb((0.28, 0.18, 0.095))
    col = nb.mix(nb.add(nb.mul(nb.smooth(0.25, 0.9, ringf), 0.62), nb.mul(tone, 0.40)), light, dark)
    col = nb.mix(nb.mul(fib, 0.30), col, nb.rgb((0.30, 0.20, 0.11)))
    col = nb.mix(nb.mul(pores, 0.85), col, nb.rgb((0.10, 0.065, 0.035)))
    col = nb.mix(nb.mul(latepores, 0.45), col, nb.rgb((0.16, 0.10, 0.06)))
    col = nb.mix(nb.mul(rays, 0.35), col, nb.rgb((0.66, 0.52, 0.34)))
    col = nb.mix(nb.mul(stain, 0.30), col, nb.rgb((0.20, 0.13, 0.07)))
    col = nb.mix(nb.mul(mug, 0.45), col, nb.rgb((0.15, 0.09, 0.05)))
    col = nb.mix(nb.mul(scr, 0.35), col, nb.rgb((0.70, 0.58, 0.42)))
    rough = nb.add(0.42, nb.mul(fib, 0.10), nb.mul(pores, 0.25), nb.mul(scr, 0.25), nb.mul(stain, -0.08),
                   nb.mul(mug, 0.12))
    height = nb.add(nb.mul(pores, -0.9), nb.mul(latepores, -0.35), nb.mul(fib, 0.35), nb.mul(scr, -0.6),
                    nb.mul(rays, 0.15))
    return col, rough, 0.0, height


PAINT_COLORS = [  # (linear rgb, roughness, metallic), same order as geo.PAINT_BANDS
    ((0.26, 0.010, 0.014), 0.40, 0.0),   # red
    ((0.80, 0.55, 0.20), 0.36, 0.5),     # gold paint (bronze-powder paint, half metallic: reads under warm lights without an env map)
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
    """Forged sheet iron: mid-grey hammered metal with dents, blooms of rust and rust runs,
    soot clouds and fine pitting. Neutral enough that COLOR_0 can heat-tint or blacken it."""
    ham_d, ham_c = nb.voronoi(26, 26, off=(0.5, 0.9, 1.4, 2.2))
    dent = nb.smooth(0.0, 0.55, ham_d)                              # 0 in a dent centre
    blotch = nb.remap(nb.noise(6, 6, detail=4, rough=0.6, off=(7.2, 3.1, 0.6, 1.5)), 0.32, 0.68, 0.0, 1.0)
    rust_n = nb.remap(nb.noise(9, 9, detail=6, rough=0.62, off=(1.2, 0.3, 4.4, 2.0)), 0.30, 0.70, 0.0, 1.0)
    rust = nb.smooth(0.62, 0.80, rust_n)                            # scattered blooms, not a coat
    rust_core = nb.smooth(0.78, 0.92, rust_n)
    runs = nb.mul(nb.smooth(0.55, 0.78, nb.noise(34, 2.5, detail=3, off=(0.4, 2.2, 1.0, 3.0))),
                  nb.smooth(0.35, 0.7, rust_n))
    soot = nb.smooth(0.45, 0.8, nb.remap(nb.noise(3, 3, detail=4, off=(6.1, 1.9, 0.2, 3.3)), 0.3, 0.7, 0.0, 1.0))
    pit = nb.smooth(0.70, 0.78, nb.noise(150, 150, detail=1, off=(3.3, 3.1, 0.8, 0.2)))
    fine = nb.remap(nb.noise(120, 120, detail=2, off=(9.3, 1.1, 2.8, 5.2)), 0.35, 0.65, 0.0, 1.0)
    base = nb.mix(nb.add(nb.mul(blotch, 0.6), nb.mul(fine, 0.25)), nb.rgb((0.125, 0.12, 0.115)),
                  nb.rgb((0.055, 0.052, 0.05)))
    col = nb.mix(nb.mul(nb.m('SUBTRACT', 1.0, dent), 0.25), base, nb.rgb((0.16, 0.155, 0.15)))   # dent rims catch wear
    rustc = nb.mix(fine, nb.rgb((0.17, 0.075, 0.035)), nb.rgb((0.10, 0.05, 0.025)))
    col = nb.mix(nb.mul(runs, 0.5), col, nb.rgb((0.13, 0.07, 0.04)))
    col = nb.mix(nb.mul(rust, 0.75), col, rustc)
    col = nb.mix(nb.mul(rust_core, 0.7), col, nb.rgb((0.08, 0.035, 0.015)))
    col = nb.mix(nb.mul(soot, 0.55), col, nb.rgb((0.018, 0.016, 0.015)))
    col = nb.mix(nb.mul(pit, 0.6), col, nb.rgb((0.03, 0.025, 0.02)))
    rough = nb.add(0.42, nb.mul(rust, 0.40), nb.mul(fine, 0.10), nb.mul(soot, 0.15), nb.mul(dent, -0.08))
    metal = nb.m('MAXIMUM', 0.0, nb.add(0.75, nb.mul(rust, -0.65), nb.mul(soot, -0.35)))
    height = nb.add(nb.mul(dent, 0.9), nb.mul(rust_core, 0.5), nb.mul(rust, 0.25), nb.mul(pit, -0.6),
                    nb.mul(fine, 0.15))
    return col, rough, metal, height


GRAPHS = {"wood": _wood_graph, "oak": _oak_graph, "paint": _paint_graph, "iron": _iron_graph}
BUMP = {"wood": (1.0, 0.0014), "oak": (0.9, 0.0010), "paint": (0.8, 0.0008), "iron": (1.0, 0.0025)}


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
    state.configure_cycles(scene)
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
            # a constant source (e.g. wood metal = 0.0) must not inherit the previous pass's link
            for l in list(emis.inputs["Color"].links):
                nt.links.remove(l)
            if isinstance(source, (int, float)):
                emis.inputs["Color"].default_value = (source, source, source, 1)
            else:
                nt.links.new(source, emis.inputs["Color"])
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
    "glass":         ((0.85, 0.92, 0.92), 0.04, 0.0, None, 0.0, 0.14),
    "fir":           ((0.030, 0.085, 0.035), 0.72, 0.0, None, 0.0, 1.0),
    "brass":         ((0.78, 0.56, 0.26), 0.32, 1.0, None, 0.0, 1.0),
    "copper":        ((0.80, 0.42, 0.26), 0.30, 1.0, None, 0.0, 1.0),
    "ember":         ((0.25, 0.05, 0.01), 0.9, 0.0, (1.0, 0.28, 0.05), 6.0, 1.0),
    "ash":           ((0.30, 0.29, 0.28), 0.95, 0.0, None, 0.0, 1.0),
    "ornament_red":  ((0.50, 0.015, 0.02), 0.18, 0.0, None, 0.0, 1.0),
    "ornament_gold": ((0.90, 0.64, 0.24), 0.22, 1.0, None, 0.0, 1.0),
    "fabric_red":    ((0.35, 0.02, 0.025), 0.85, 0.0, None, 0.0, 1.0),
    "fabric_white":  ((0.70, 0.68, 0.64), 0.85, 0.0, None, 0.0, 1.0),
    "fabric_green":  ((0.03, 0.12, 0.06), 0.85, 0.0, None, 0.0, 1.0),
    "lamp_glass":    ((1.0, 0.85, 0.6), 0.1, 0.0, (1.0, 0.7, 0.4), 4.0, 1.0),
    "bookcloth":     ((0.80, 0.78, 0.74), 0.78, 0.0, None, 0.0, 1.0),   # book spines; colour via tint
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


# ============================================================ kit variants
# A variant reuses a kit's (shared) textures with a different glTF factor, so it costs no
# texture bytes. metal: metallicFactor multiplied into the kit's metal channel (the exporter
# writes it as pbrMetallicRoughness.metallicFactor).
# color_gain: a lighter copy of the kit's base colour (linear gain with a soft shoulder), written
# as kit_<variant>_color.png: its own small image (the iron colour map is ~8 KB as WebP), shared
# like the kit maps (deco_kit_<variant>_color.webp) by every stall that uses the variant.
KIT_VARIANTS = {
    # sheet iron for hoods and fireboxes: lighter and far less metallic than the forged-iron kit,
    # so it reads as grey sooty metal under the site's point lights without an environment map
    # (the plain kit, base colour mean 84/255 at metal 0.65, renders as a black slab there)
    # emit: a faint warm emissive copy of the base colour (emissiveTexture = the colour map) that
    # stands in for the eave bulbs and the fire right beside the hood: the engine's bulbs glow but
    # light nothing, and no site light reaches a hood face that looks up and out under the eave
    "iron_matte": ("iron", dict(metal=0.35, color_gain=1.7, emit=(0.12, 0.08, 0.045))),
    # painted trim that faces out and down under the eaves (bargeboards, carved valances, a
    # gable star board): the plain paint kit with a faint warm emissive copy of its colour
    # (emissiveTexture = the shared paint colour map, so it costs no texture bytes). Under the
    # site's moonlight a red bargeboard facing down goes near-black; this keeps it red.
    "paint_glow": ("paint", dict(emit=(0.13, 0.09, 0.07))),
    # old copper sheet (small roofs, hoods): the iron kit's dents, streaks and pitting with a
    # copper-brown, part-oxidised colour (its own small colour copy), metal x0.6. Replaces the
    # flat untextured 'copper' on architecture, which renders as a salmon plane in three.js.
    "copper_old": ("iron", dict(metal=0.6, color_gain=1.35, tint=(1.25, 0.66, 0.42))),
}
# Variants whose emission is a stand-in for light the engine does not cast (bulbs, fire). Cycles
# previews switch it off (standin_emission(False)), so the render stays the lighting target.
STANDIN_EMIT = {"iron_matte", "paint_glow", "rauten"}


def standin_emission(on=True):
    """Switch the emissive stand-ins (materials flagged nm_standin_emit) on or off. Call it
    with False before a Cycles preview render; the glb export keeps them on."""
    n = 0
    for m in bpy.data.materials:
        if m.get("nm_standin_emit") and m.node_tree:
            for nd in m.node_tree.nodes:
                if nd.type == 'BSDF_PRINCIPLED':
                    nd.inputs["Emission Strength"].default_value = 1.0 if on else 0.0
                    n += 1
    return n


def _variant_color(key, base, gain, tint=None):
    """Path of the lighter (and optionally tinted) base-colour copy of kit `base` for variant
    `key` (made on demand)."""
    path = os.path.join(state.KIT_DIR, f"kit_{key}_color.png")
    stamp = path + ".version"
    tag = f"{KIT_VERSION}:{gain}:{tint}"
    if os.path.exists(path) and os.path.exists(stamp) and open(stamp).read().strip() == tag:
        return path
    from PIL import Image
    srgb = np.asarray(Image.open(kit_path(base, "color")).convert("RGB")).astype(np.float32) / 255.0
    lin = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    x = lin * gain
    if tint is not None:
        x = x * np.asarray(tint, np.float32)
    lin = np.where(x < 0.6, x, 0.6 + 0.4 * (1.0 - np.exp(-(x - 0.6) / 0.4)))     # soft shoulder
    out = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)).save(path)
    with open(stamp, "w") as f:
        f.write(tag)
    return path


def kit_variant_material(key):
    base, opts = KIT_VARIANTS[key]
    m = kit_material(base, name=key)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if "color_gain" in opts:
        name = f"kit_{key}_color"
        img = bpy.data.images.get(name)
        if img is None:
            img = bpy.data.images.load(_variant_color(key, base, opts["color_gain"], opts.get("tint")))
            img.name = name
            img.colorspace_settings.name = "sRGB"
        for n in nt.nodes:
            if n.type == 'TEX_IMAGE' and n.image and n.image.name == f"kit_{base}_color":
                n.image = img
    if "emit" in opts:
        tc = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.endswith("_color"))
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        nt.links.new(tc.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = (*opts["emit"], 1)
        nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    if "metal" in opts:
        link = bsdf.inputs["Metallic"].links[0]
        src = link.from_socket
        nt.links.remove(link)
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = 'MULTIPLY'
        nt.links.new(src, mul.inputs[0])
        mul.inputs[1].default_value = opts["metal"]
        nt.links.new(mul.outputs[0], bsdf.inputs["Metallic"])
    m["nm_kit"] = base
    if key in STANDIN_EMIT:
        m["nm_standin_emit"] = True
    return m


# ============================================================ small dedicated pattern textures
# Generated with numpy (no bake), written to blender/out/kit/<key>.png and embedded in the glb
# of the stall that uses them. Each is a tiling texture mapped in metres like the kit tiles
# (see geo.TILE for the metres one repeat covers).
PATTERN_VERSION = "p2"  # p2: deeper blue (the p1 blue washed to pale grey-blue in three.js)


def _rauten_pixels(res=256, n=4):
    """Bavarian Rauten: n big blue and n white lozenges across one repeat, two flat colours
    with a faint cloth/paint mottle. Large on purpose: they must survive mipmapping at lane
    distance (64 px per lozenge at 256 px)."""
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) + 0.5
    u, v = x / res * n, y / res * n
    chk = (np.floor(u + v) + np.floor(u - v)) % 2.0
    blue = np.array([0.004, 0.14, 0.50], np.float32)       # Bavarian blue (sRGB ~ 12,105,188)
    white = np.array([0.83, 0.84, 0.80], np.float32)
    rng = np.random.default_rng(7)
    mott = rng.normal(0, 1, (res // 8, res // 8)).astype(np.float32)
    mott = np.kron(mott, np.ones((8, 8), np.float32))
    mott = (mott + np.roll(mott, 4, 0) + np.roll(mott, 4, 1) + np.roll(np.roll(mott, 4, 0), 4, 1)) / 4
    col = np.where(chk[..., None] > 0.5, blue, white) * (1.0 + 0.035 * mott[..., None])
    return np.clip(col, 0, 1)


PATTERNS = {
    # key: (pixel generator, roughness, emissive factor or None)
    # rauten: a faint warm emissive copy of the pattern stands in for the eave bulbs' light on
    # the pennants hanging right beside them (the engine's bulbs glow but light nothing), so the
    # blue and white read at night under the hemisphere light alone; exported as
    # emissiveTexture = the pattern, emissiveFactor = the colour below
    "rauten": (_rauten_pixels, 0.62, (0.22, 0.20, 0.17)),
}


def pattern_path(key):
    return os.path.join(state.KIT_DIR, f"{key}_pattern.png")


def pattern_material(key):
    gen, rough, emit = PATTERNS[key]
    path = pattern_path(key)
    stamp = path + ".version"
    fresh = os.path.exists(path) and os.path.exists(stamp) and open(stamp).read().strip() == PATTERN_VERSION
    if not fresh:
        os.makedirs(state.KIT_DIR, exist_ok=True)
        rgb = gen()
        res = rgb.shape[0]
        img = bpy.data.images.new(f"{key}_pattern_tmp", res, res)
        img.colorspace_settings.name = "sRGB"
        lin = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)  # store sRGB
        px = np.ones((res, res, 4), np.float32)
        px[..., :3] = lin[::-1]
        img.pixels.foreach_set(px.ravel())
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        bpy.data.images.remove(img)
        with open(stamp, "w") as f:
            f.write(PATTERN_VERSION)
    m, nt, bsdf, L = _node_mat(key)
    N = nt.nodes
    name = f"{key}_pattern"
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(path)
        img.name = name
        img.colorspace_settings.name = "sRGB"
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tc = N.new("ShaderNodeTexImage")
    tc.image = img
    L.new(uv.outputs[0], tc.inputs[0])
    _vcol_multiply(nt, L, tc.outputs["Color"], bsdf)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    if emit:
        mul = N.new("ShaderNodeMix")
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        L.new(tc.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = (*emit, 1)
        L.new(mul.outputs[2], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
        if key in STANDIN_EMIT:
            m["nm_standin_emit"] = True
    return m


def get(key):
    """Material for a key (created once per build): kit keys and kit variants are textured
    with the shared kit maps, pattern keys with their own small texture, others simple."""
    if key not in _mats:
        if key in GRAPHS:
            _mats[key] = kit_material(key)
        elif key in KIT_VARIANTS:
            _mats[key] = kit_variant_material(key)
        elif key in PATTERNS:
            _mats[key] = pattern_material(key)
        else:
            _mats[key] = simple_material(key)
    return _mats[key]
