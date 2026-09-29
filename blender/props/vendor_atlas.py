"""Vendor texture atlas: every painted, printed or textured surface of the goods in one 2048 px atlas.

Plain numpy + PIL (no bpy), so it runs with any Python 3 that has numpy, scipy and Pillow:

    python3 blender/props/vendor_atlas.py            # writes blender/out/vendor/atlas_*.png + regions.json

Maps (glTF conventions):
    atlas_color.png   base colour, sRGB, no lighting
    atlas_rm.png      G = roughness, B = metallic (R unused, 255)
    atlas_normal.png  tangent-space normal map (OpenGL / glTF +Y), from per-region height fields
    coal_color.png / coal_emit.png   256 px pair for the coal_glow material (UV 0..1)

Regions are packed on shelves; regions.json maps name -> [u0, v0, u1, v1] in UV space (v up).
Everything is generated from seeded noise, drawn text (OFL fonts in blender/props/fonts/ and
blender/lib/fonts/) and simple shapes. No third-party images.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "blender", "out", "vendor")
FONTS = os.path.join(HERE, "fonts")
LIBFONTS = os.path.join(REPO, "blender", "lib", "fonts")
SIZE = 2048
PAD = 4

FONT_FILES = {
    "oswald": (FONTS, "Oswald[wght].ttf"), "garamond": (FONTS, "EBGaramond[wght].ttf"),
    "playfair": (FONTS, "PlayfairDisplay[wght].ttf"), "caveat": (FONTS, "Caveat[wght].ttf"),
    "bebas": (FONTS, "BebasNeue-Regular.ttf"), "josefin": (FONTS, "JosefinSans[wght].ttf"),
    "cinzel": (FONTS, "Cinzel[wght].ttf"), "pacifico": (FONTS, "Pacifico-Regular.ttf"),
    "baskerville": (FONTS, "LibreBaskerville[wght].ttf"),
    "fraktur": (LIBFONTS, "UnifrakturCook-Bold.ttf"), "fell": (LIBFONTS, "IMFeENit28P.ttf"),
    "fellsc": (LIBFONTS, "IMFeENsc28P.ttf"), "alegreya": (LIBFONTS, "AlegreyaSC-ExtraBold.ttf"),
}


def font(name, size, wght=None):
    d, f = FONT_FILES[name]
    ft = ImageFont.truetype(os.path.join(d, f), max(4, int(size)))
    if wght is not None:
        try:
            ft.set_variation_by_axes([wght])
        except Exception:
            pass
    return ft


# ============================================================ noise helpers
def noise(h, w, cell, seed):
    """Smooth value noise in [0,1] with features about `cell` px across."""
    cell = max(1.0, float(cell))
    rng = np.random.default_rng(seed)
    gh, gw = int(h / cell) + 4, int(w / cell) + 4
    g = rng.random((gh, gw))
    z = ndimage.zoom(g, cell, order=3, mode="reflect")
    return np.clip(z[:h, :w], 0, 1)


def fbm(h, w, cell, seed, oct=4, gain=0.5):
    tot, amp, s = np.zeros((h, w)), 1.0, 0.0
    for o in range(oct):
        tot += amp * noise(h, w, max(1.0, cell / 2 ** o), seed + 17 * o)
        s += amp
        amp *= gain
    return tot / s


def voronoi(h, w, n, seed, periodic_x=False):
    """F1 distance, F2-F1 and cell id for n random sites."""
    rng = np.random.default_rng(seed)
    pts = rng.random((n, 2)) * [h, w]
    ids = np.arange(n)
    if periodic_x:
        pts = np.concatenate([pts, pts + [0, w], pts - [0, w]])
        ids = np.concatenate([ids, ids, ids])
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    d, i = tree.query(np.stack([yy.ravel(), xx.ravel()], 1), k=2)
    return (d[:, 0].reshape(h, w), (d[:, 1] - d[:, 0]).reshape(h, w), ids[i[:, 0]].reshape(h, w))


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2 and np.ndim(a) >= 1 and np.shape(a)[-1:] == (3,):
        t = t[..., None]
    return a * (1 - t) + b * t


def rgb(h, w, c):
    return np.ones((h, w, 3)) * np.array(c, float)


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def text_mask(w, h, lines, ss=3, rotate=None):
    """Draw text into a float mask of (h, w). lines: [(text, fontname, size_px, wght, (x, y), anchor)].
    Coordinates in output px. rotate: None | 'cw' (text runs top->bottom)."""
    W, H = (h, w) if rotate == "cw" else (w, h)
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    for t, fn, size, wght, (x, y), anchor in lines:
        f = font(fn, size * ss, wght)
        d.text((x * ss, y * ss), t, fill=255, font=f, anchor=anchor)
    im = im.resize((W, H), Image.LANCZOS)
    m = np.asarray(im, float) / 255.0
    if rotate == "cw":
        m = np.rot90(m, k=-1)
    return m


def fit_size(text, fn, size, wght, max_w):
    """Largest size <= size so that text fits max_w px."""
    s = size
    while s > 5:
        f = font(fn, s * 3, wght)
        if f.getlength(text) / 3 <= max_w:
            return s
        s -= 0.5
    return s


def shape_mask(w, h, draw_fn, ss=3):
    im = Image.new("L", (w * ss, h * ss), 0)
    draw_fn(ImageDraw.Draw(im), ss)
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, float) / 255.0


class Tex:
    """One region's layers: colour (sRGB 0..1), roughness, metal, height (mm-ish units)."""

    def __init__(self, w, h, col=(0.8, 0.8, 0.8), rough=0.6, metal=0.0):
        self.w, self.h = w, h
        self.col = rgb(h, w, col)
        self.rough = np.full((h, w), float(rough))
        self.metal = np.full((h, w), float(metal))
        self.height = np.zeros((h, w))
        self.hscale = 1.0          # normal strength: slope per height unit per px

    def paint(self, mask, col, rough=None, metal=None, height=None):
        m = np.clip(mask, 0, 1)
        self.col = mix(self.col, np.array(col, float), m)
        if rough is not None:
            self.rough = mix(self.rough, rough, m)
        if metal is not None:
            self.metal = mix(self.metal, metal, m)
        if height is not None:
            self.height = self.height + height * m


# ============================================================ region generators
def g_swatch(rough, metal):
    def f(w, h, seed):
        t = Tex(w, h, (1, 1, 1), rough, metal)
        return t
    return f


def g_copper(w, h, seed):
    t = Tex(w, h, hexc("f2a987"), 0.26, 1.0)
    d1, d21, cid = voronoi(h, w, int(w * h / 60), seed)
    dome = 1 - np.clip(d1 / 5.5, 0, 1) ** 2          # hammer dimples, about 8 mm across
    t.height = -dome * 0.6 + fbm(h, w, 40, seed + 1) * 0.3
    tarn = smooth(0.4, 0.75, fbm(h, w, 60, seed + 2))
    t.col = mix(t.col, np.array(hexc("9a5238")), tarn * 0.7)
    t.col = mix(t.col, np.array(hexc("6a3424")), smooth(0.7, 0.9, fbm(h, w, 18, seed + 4)) * 0.45)
    t.col = mix(t.col, np.array(hexc("ffd2b8")), smooth(0.85, 1.0, dome) * 0.2)
    t.rough = 0.24 + tarn * 0.22 + fbm(h, w, 10, seed + 3) * 0.14
    t.hscale = 0.9
    return t


def g_brass(w, h, seed):
    t = Tex(w, h, hexc("f0cf8c"), 0.3, 1.0)
    streak = noise(h, w * 0 + 1, 2, seed)[:, :1] * np.ones((1, w))
    t.col = mix(t.col, np.array(hexc("b08a4a")), smooth(0.5, 0.9, fbm(h, w, 60, seed + 1)) * 0.6)
    t.rough = 0.25 + streak * 0.12
    t.height = streak * 0.2
    return t


def g_steel(w, h, seed):
    t = Tex(w, h, hexc("d5d8da"), 0.28, 1.0)
    rng = np.random.default_rng(seed)
    streak = ndimage.uniform_filter1d(rng.random((h, w)), 40, axis=1)
    t.rough = 0.18 + (streak - 0.5) * 0.25 + fbm(h, w, 50, seed) * 0.1
    t.col = mix(t.col, np.array(hexc("a9adb0")), fbm(h, w, 60, seed + 1) * 0.4)
    t.height = streak * 0.3
    return t


def g_iron(w, h, seed):
    t = Tex(w, h, hexc("2c2a28"), 0.72, 0.55)
    n = fbm(h, w, 30, seed)
    rust = smooth(0.62, 0.8, fbm(h, w, 45, seed + 1))
    t.col = mix(t.col, np.array(hexc("141312")), n * 0.6)
    t.col = mix(t.col, np.array(hexc("6b3b22")), rust * 0.7)
    t.metal = 0.6 - rust * 0.5
    t.rough = 0.6 + rust * 0.3 + n * 0.1
    t.height = fbm(h, w, 6, seed + 3) * 0.6 + rust * 0.4
    return t


def g_wood(w, h, seed, base="c9a47a"):
    """Plank grain along U (x). Neutral light wood; tint with vertex colour."""
    t = Tex(w, h, hexc(base), 0.62, 0.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    warp = fbm(h, w, 60, seed) * 22 + fbm(h, w, 15, seed + 5) * 3
    rings = (yy + warp) / 7.0
    ring = np.abs(np.sin(rings * math.pi)) ** 6
    fibre = noise(h, w * 0 + 1, 1.5, seed + 2)[:, :1] * np.ones((1, w))
    fibre = ndimage.uniform_filter1d(np.random.default_rng(seed).random((h, w)), 60, axis=1) * 0.6 + fibre * 0.4
    t.col = mix(t.col, np.array(hexc("7d5534")), ring * 0.55 + fibre * 0.18)
    t.col = mix(t.col, np.array(hexc("5a3d26")), smooth(0.6, 0.9, fbm(h, w, 80, seed + 4)) * 0.3)
    t.height = -ring * 0.5 + fibre * 0.4
    t.rough = 0.55 + fibre * 0.2
    return t


def g_wood_end(w, h, seed):
    t = Tex(w, h, hexc("c09a70"), 0.75)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot(xx - w / 2 + fbm(h, w, 30, seed) * 6, yy - h / 2 + fbm(h, w, 30, seed + 1) * 6)
    ring = np.abs(np.sin(r / 3.2 * math.pi)) ** 4
    t.col = mix(t.col, np.array(hexc("80593a")), ring * 0.5)
    crack = smooth(0.985, 1.0, np.abs(np.sin(np.arctan2(yy - h / 2, xx - w / 2) * 3 + fbm(h, w, 20, seed) * 2)))
    t.col = mix(t.col, np.array(hexc("3a281a")), crack * smooth(10, 40, r) * 0.8)
    t.height = -ring * 0.4
    return t


def g_ceramic(w, h, seed):
    t = Tex(w, h, (0.97, 0.96, 0.94), 0.25)
    rng = np.random.default_rng(seed)
    speck = (rng.random((h, w)) > 0.996).astype(float)
    speck = ndimage.maximum_filter(speck, 2)
    t.col = mix(t.col, np.array((0.6, 0.58, 0.55)), speck * 0.5)
    t.height = fbm(h, w, 25, seed) * 0.35     # glaze ripple
    t.hscale = 0.5
    return t


def g_bisque(w, h, seed):
    """Unglazed stoneware foot / raw clay: rough, sandy."""
    t = Tex(w, h, hexc("cbb89c"), 0.85)
    rng = np.random.default_rng(seed)
    t.col = mix(t.col, np.array(hexc("9d8a70")), rng.random((h, w)) * 0.35)
    t.height = rng.random((h, w)) * 0.3
    return t


def g_mug(style):
    """Printed / painted wraps for Glühwein mugs; u runs around the mug, v up."""
    def f(w, h, seed):
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        base = {"red": "9c1a1f", "blue": "1d3a78", "cream": "efe4cc", "green": "1f4a33", "brown": "6b3b22",
                "white": "f4f0e8", "santa": "a3161b", "bluestar": "243f7d"}[style]
        t = Tex(w, h, hexc(base), 0.12)
        t.height = fbm(h, w, 30, seed) * 0.25
        # glaze pooling: darker near the bottom, lighter at the rim edge
        t.col = mix(t.col, t.col * 0.72, smooth(0.25, 0.0, yy / h) ** 1.5 * 0)
        t.col = mix(t.col, t.col * 0.8, smooth(h * 0.25, h, yy) * 0.35)
        white = np.array(hexc("f6f1e6"))
        gold = np.array(hexc("d9ae5c"))
        if style == "red":
            gs = fit_size("Glühwein", "pacifico", h * 0.34, None, w * 0.4)
            m = text_mask(w, h, [("Glühwein", "pacifico", gs, None, (w * 0.25, h * 0.5), "mm"),
                                 ("Glühwein", "pacifico", gs, None, (w * 0.75, h * 0.5), "mm")])
            t.paint(m, white, 0.2, height=0.3)
            for k in range(10):
                cx, cy = rng.uniform(0, w), rng.choice([h * 0.16, h * 0.84])
                s = rng.uniform(4, 7)
                sm = shape_mask(w, h, lambda d, ss, cx=cx, cy=cy, s=s: d.polygon(
                    [((cx + s * (1 if i % 2 == 0 else 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5)) * ss,
                      (cy + s * (1 if i % 2 == 0 else 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5)) * ss)
                     for i in range(10)], fill=255))
                t.paint(sm, gold, 0.3, 1.0, 0.2)
            t.paint(smooth(h * 0.08, h * 0.04, yy), gold, 0.3, 1.0)   # gold rim line (v top = row 0)
        elif style == "blue":
            for k in range(26):
                cx, cy, r = rng.uniform(0, w), rng.uniform(h * 0.12, h * 0.9), rng.uniform(3, 8)
                def fl(d, ss, cx=cx, cy=cy, r=r):
                    for a in range(6):
                        ang = a * math.pi / 3
                        d.line([(cx * ss, cy * ss), ((cx + r * math.cos(ang)) * ss, (cy + r * math.sin(ang)) * ss)],
                               fill=255, width=max(1, int(ss * 0.9)))
                t.paint(shape_mask(w, h, fl), white, 0.2, height=0.2)
            t.paint(smooth(h * 0.07, h * 0.03, yy), white, 0.15)
        elif style == "cream":
            # hand-painted skyline: stall roofs, a Ferris wheel and a church spire, in dark red line work
            def sky(d, ss):
                y0 = h * 0.72
                x = 0
                red = 255
                while x < w:
                    sw = rng.uniform(18, 30)
                    d.polygon([(x * ss, y0 * ss), ((x + sw / 2) * ss, (y0 - sw * 0.45) * ss),
                               ((x + sw) * ss, y0 * ss)], outline=red, width=int(1.3 * ss))
                    d.rectangle([(x + 2) * ss, y0 * ss, (x + sw - 2) * ss, (y0 + 12) * ss], outline=red, width=int(1.2 * ss))
                    x += sw + rng.uniform(2, 8)
                cx, cy, r = w * 0.62, h * 0.4, h * 0.26
                d.ellipse([(cx - r) * ss, (cy - r) * ss, (cx + r) * ss, (cy + r) * ss], outline=red, width=int(1.3 * ss))
                for a in range(12):
                    ang = a * math.pi / 6
                    d.line([(cx * ss, cy * ss), ((cx + r * math.cos(ang)) * ss, (cy + r * math.sin(ang)) * ss)],
                           fill=red, width=int(ss))
                d.polygon([(w * 0.2 * ss, h * 0.72 * ss), (w * 0.215 * ss, h * 0.18 * ss), (w * 0.23 * ss, h * 0.72 * ss)],
                          outline=red, width=int(1.2 * ss))
                d.line([(0, (h * 0.86) * ss), (w * ss, (h * 0.86) * ss)], fill=red, width=int(2 * ss))
            m = shape_mask(w, h, sky)
            t.paint(m, hexc("8e1c22"), 0.2, height=0.15)
            tm = text_mask(w, h, [("Nachtmarkt", "fraktur", h * 0.16, None, (w * 0.2, h * 0.93), "mm")])
            t.paint(tm, hexc("8e1c22"), 0.2)
            t.paint(smooth(h * 0.06, h * 0.03, yy), hexc("8e1c22"), 0.2)
        elif style == "green":
            for k in range(7):
                cx = (k + 0.5) * w / 7 + rng.uniform(-4, 4)
                s = rng.uniform(0.8, 1.1)
                def tree(d, ss, cx=cx, s=s):
                    for j in range(3):
                        top = h * (0.3 + 0.13 * j)
                        d.polygon([((cx - (8 + 4 * j) * s) * ss, (top + 16 * s) * ss), (cx * ss, top * ss),
                                   ((cx + (8 + 4 * j) * s) * ss, (top + 16 * s) * ss)], fill=255)
                t.paint(shape_mask(w, h, tree), white, 0.2, height=0.2)
            t.paint(((yy > h * 0.08) & (yy < h * 0.14)).astype(float), gold, 0.3, 1.0, 0.1)
            t.paint(((yy > h * 0.86) & (yy < h * 0.9)).astype(float), gold, 0.3, 1.0, 0.1)
        elif style == "brown":
            for k in range(5):
                cx = (k + 0.5) * w / 5
                def heart(d, ss, cx=cx):
                    pts = []
                    for i in range(40):
                        a = 2 * math.pi * i / 40
                        x = 16 * math.sin(a) ** 3
                        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
                        pts.append(((cx + x * 0.9) * ss, (h * 0.5 - y * 0.9) * ss))
                    d.polygon(pts, outline=255, width=int(2 * ss))
                t.paint(shape_mask(w, h, heart), hexc("f2d9a6"), 0.2, height=0.2)
            t.paint(smooth(h * 0.07, h * 0.03, yy), hexc("f2d9a6"), 0.2)
        elif style == "white":
            for k in range(6):
                cx, cy = (k + 0.5) * w / 6, h * 0.52 + (k % 2) * 6 - 3
                def star(d, ss, cx=cx, cy=cy):
                    r1, r2 = 14, 5.5
                    d.polygon([((cx + (r1 if i % 2 == 0 else r2) * math.cos(-math.pi / 2 + i * math.pi / 8)) * ss,
                                (cy + (r1 if i % 2 == 0 else r2) * math.sin(-math.pi / 2 + i * math.pi / 8)) * ss)
                               for i in range(16)], fill=255)
                t.paint(shape_mask(w, h, star), hexc("a8161d"), 0.15, height=0.2)
            t.paint(smooth(h * 0.12, h * 0.06, yy), hexc("a8161d"), 0.15)
        elif style == "santa":
            # red boot: white fluffy cuff at the top, a black belt band, gold buckle
            cuff = smooth(h * 0.3, h * 0.26, yy + fbm(h, w, 6, seed) * 6)
            t.paint(cuff, hexc("f1ede4"), 0.9, height=0.8)
            t.height += cuff * fbm(h, w, 3, seed + 3) * 1.2
            band = ((yy > h * 0.45) & (yy < h * 0.55)).astype(float)
            t.paint(band, hexc("141414"), 0.3)
            bx = ((xx > w * 0.44) & (xx < w * 0.56) & (yy > h * 0.43) & (yy < h * 0.57)).astype(float)
            bi = ((xx > w * 0.465) & (xx < w * 0.535) & (yy > h * 0.46) & (yy < h * 0.54)).astype(float)
            t.paint(bx - bi, gold, 0.3, 1.0, 0.3)
        elif style == "bluestar":
            for k in range(14):
                cx, cy, s = rng.uniform(0, w), rng.uniform(h * 0.15, h * 0.85), rng.uniform(4, 9)
                def st(d, ss, cx=cx, cy=cy, s=s):
                    d.polygon([((cx + s * (1 if i % 2 == 0 else 0.42) * math.cos(-math.pi / 2 + i * math.pi / 5)) * ss,
                                (cy + s * (1 if i % 2 == 0 else 0.42) * math.sin(-math.pi / 2 + i * math.pi / 5)) * ss)
                               for i in range(10)], fill=255)
                t.paint(shape_mask(w, h, st), gold, 0.3, 1.0, 0.2)
            t.paint(smooth(h * 0.07, h * 0.03, yy), gold, 0.3, 1.0)
        return t
    return f


def g_label(title, sub, bg, ink, fn="garamond", fn2="garamond", border=True, stripe=None):
    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.7)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.col = mix(t.col, t.col * 0.85, fbm(h, w, 20, seed) * 0.5)    # paper mottling
        if stripe:
            t.paint(((yy > h * 0.08) & (yy < h * 0.2)).astype(float), hexc(stripe), 0.6)
            t.paint(((yy > h * 0.8) & (yy < h * 0.92)).astype(float), hexc(stripe), 0.6)
        if border:
            b = (((xx > 4) & (xx < w - 4) & (yy > 4) & (yy < h - 4)) & ~((xx > 6) & (xx < w - 6) & (yy > 6) & (yy < h - 6))).astype(float)
            t.paint(b, hexc(ink), 0.6)
        s1 = fit_size(title, fn, h * 0.3, 600, w * 0.84)
        lines = [(title, fn, s1, 600, (w / 2, h * 0.45), "mm")]
        if sub:
            s2 = fit_size(sub, fn2, h * 0.14, 500, w * 0.8)
            lines.append((sub, fn2, s2, 500, (w / 2, h * 0.72), "mm"))
        t.paint(text_mask(w, h, lines), hexc(ink), 0.6)
        return t
    return f


def g_orange_slice(w, h, seed):
    """Dried orange slice seen face-on (planar mapped): rind ring, segments, pith."""
    t = Tex(w, h, hexc("d9731c"), 0.55)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
    a = np.arctan2(yy - h / 2, xx - w / 2)
    seg = np.abs(np.sin(a * 5.5 + 0.3))
    flesh = mix(np.array(hexc("e0801e")), np.array(hexc("f3b24a")), fbm(h, w, 6, seed) * 0.8)
    t.col = rgb(h, w, (0, 0, 0)) + flesh
    walls = smooth(0.08, 0.0, seg) * smooth(0.1, 0.2, r)
    t.paint(walls, hexc("f7d9a0"), 0.5, height=0.5)
    t.paint(smooth(0.8, 0.84, r), hexc("f4e1b5"), 0.6, height=0.3)       # pith
    t.paint(smooth(0.9, 0.93, r), hexc("b8480f"), 0.45, height=0.6)       # rind
    t.paint(smooth(0.12, 0.05, r), hexc("f7e1b0"), 0.6)
    t.height += fbm(h, w, 4, seed + 1) * 0.3
    return t


def g_peel(w, h, seed):
    t = Tex(w, h, hexc("e8741a"), 0.45)
    d1, _, _ = voronoi(h, w, int(w * h / 12), seed)
    t.height = -np.clip(d1 / 3, 0, 1) * 0.5
    t.col = mix(t.col, np.array(hexc("c85a10")), fbm(h, w, 20, seed) * 0.5)
    return t


def g_cinnamon(w, h, seed):
    t = Tex(w, h, hexc("8a4b26"), 0.8)
    rng = np.random.default_rng(seed)
    fib = ndimage.uniform_filter1d(rng.random((h, w)), 30, axis=0)
    t.col = mix(t.col, np.array(hexc("5c2f16")), fib * 0.6 + fbm(h, w, 12, seed) * 0.3)
    t.height = fib * 0.8
    return t


def g_pages_edge(w, h, seed):
    """Fore-edge / head of a text block: cream with fine page lines along U."""
    t = Tex(w, h, hexc("ece2c9"), 0.85)
    rng = np.random.default_rng(seed)
    lines = np.repeat(rng.random((h, 1)), w, 1)
    lines = ndimage.uniform_filter1d(lines, 2, axis=0)
    t.col = mix(t.col, np.array(hexc("b9ab8a")), (lines > 0.6) * 0.35 + fbm(h, w, 25, seed) * 0.2)
    t.col = mix(t.col, np.array(hexc("8f7f5d")), smooth(0.7, 0.95, fbm(h, w, 40, seed + 3)) * 0.3)  # foxing
    t.height = lines * 0.3
    return t


FAUST = ("Habe nun, ach! Philosophie, Juristerei und Medizin, und leider auch Theologie durchaus "
         "studiert, mit heißem Bemühn. Da steh ich nun, ich armer Tor! Und bin so klug als wie zuvor; "
         "heiße Magister, heiße Doktor gar und ziehe schon an die zehen Jahr herauf, herab und quer und "
         "krumm meine Schüler an der Nase herum und sehe, daß wir nichts wissen können! Das will mir "
         "schier das Herz verbrennen. Zwar bin ich gescheiter als all die Laffen, Doktoren, Magister, "
         "Schreiber und Pfaffen; mich plagen keine Skrupel noch Zweifel, fürchte mich weder vor Hölle "
         "noch Teufel. Dafür ist mir auch alle Freud entrissen, bilde mir nicht ein, was Rechts zu wissen.")


def g_pages_open(w, h, seed):
    """Two-page spread: left page text, right page a woodcut-style star map and a caption."""
    t = Tex(w, h, hexc("efe6cf"), 0.9)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, np.array(hexc("d9cba8")), smooth(0.04 * w, 0.0, np.abs(xx - w / 2)) * 0.6)   # gutter
    t.col = mix(t.col, np.array(hexc("d9cba8")), fbm(h, w, 60, seed) * 0.25)
    im = Image.new("L", (w * 3, h * 3), 0)
    d = ImageDraw.Draw(im)
    f = font("garamond", 8.2 * 3, 450)
    words = (FAUST + " " + FAUST).split()
    x0, x1 = w * 0.07, w * 0.44
    y = h * 0.1
    k = 0
    while y < h * 0.9 and k < len(words):
        line = ""
        while k < len(words) and f.getlength(line + words[k] + " ") / 3 < (x1 - x0):
            line += words[k] + " "
            k += 1
        d.text((x0 * 3, y * 3), line, fill=255, font=f)
        y += 10.5
    fd = font("fraktur", 30 * 3)
    d.text((w * 0.56 * 3, h * 0.1 * 3), "Faust.", fill=255, font=fd)
    # right page: an engraved circle of stars (a star chart), caption lines
    cx, cy, r = w * 0.75, h * 0.47, h * 0.28
    d.ellipse([(cx - r) * 3, (cy - r) * 3, (cx + r) * 3, (cy + r) * 3], outline=255, width=4)
    d.ellipse([(cx - r * 0.96) * 3, (cy - r * 0.96) * 3, (cx + r * 0.96) * 3, (cy + r * 0.96) * 3], outline=255, width=2)
    rng = np.random.default_rng(seed)
    # degree ticks around the ring, like an engraved celestial chart
    for i in range(72):
        a = 2 * math.pi * i / 72
        l = r * (0.08 if i % 6 == 0 else 0.04)
        d.line([((cx + (r * 0.96) * math.cos(a)) * 3, (cy + (r * 0.96) * math.sin(a)) * 3),
                ((cx + (r * 0.96 - l) * math.cos(a)) * 3, (cy + (r * 0.96 - l) * math.sin(a)) * 3)], fill=255, width=2)

    def star(px, py, R, n=5):
        pts = []
        for k in range(2 * n):
            rr_ = R if k % 2 == 0 else R * 0.42
            a = -math.pi / 2 + k * math.pi / n
            pts.append(((px + rr_ * math.cos(a)) * 3, (py + rr_ * math.sin(a)) * 3))
        d.polygon(pts, fill=255)
    # two constellations: pointed stars joined by thin lines
    for shape in ([(-0.5, -0.35), (-0.3, -0.45), (-0.1, -0.3), (0.05, -0.5), (0.25, -0.38)],
                  [(-0.35, 0.2), (-0.15, 0.35), (0.1, 0.25), (0.3, 0.42), (0.15, 0.05)]):
        pts = [(cx + u * r, cy + v * r) for u, v in shape]
        d.line([(x * 3, y * 3) for x, y in pts], fill=200, width=2)
        for x, y in pts:
            star(x, y, rng.uniform(2.6, 3.8))
    # scattered small stars
    for i in range(18):
        a, rr = rng.uniform(0, 2 * math.pi), r * math.sqrt(rng.random()) * 0.8
        star(cx + rr * math.cos(a), cy + rr * math.sin(a), rng.uniform(1.2, 2.0), 4)
    # a crescent moon
    mx, my, mr = cx + r * 0.45, cy - r * 0.02, r * 0.16
    d.ellipse([(mx - mr) * 3, (my - mr) * 3, (mx + mr) * 3, (my + mr) * 3], fill=255)
    d.ellipse([(mx - mr + mr * 0.45) * 3, (my - mr - mr * 0.1) * 3, (mx + mr + mr * 0.45) * 3, (my + mr - mr * 0.1) * 3], fill=0)
    for j in range(3):
        d.line([(w * 0.6 * 3, (h * 0.83 + j * 9) * 3), (w * (0.9 - 0.08 * j) * 3, (h * 0.83 + j * 9) * 3)], fill=150, width=5)
    im = im.resize((w, h), Image.LANCZOS)
    m = np.asarray(im, float) / 255.0
    t.paint(m * 0.9, hexc("2a2420"), 0.8, height=-0.1)
    t.height += fbm(h, w, 5, seed + 2) * 0.15
    return t


# ------------------------------------------------------------ book spines
SPINE_COLS = ["6e1a22", "1f2f52", "24462f", "5a3a24", "1a1a1e", "b49a6a", "8a6a22", "3b5566", "2e5f63",
              "e8dfc8", "7a2e4a", "c05a2a", "4a4f58", "d8c9a2", "2f3a2a", "902020"]


def spine_base(w, h, seed, col, kind):
    """Cloth / leather / paper base with wear, in horizontal spine space (h = length)."""
    t = Tex(w, h, hexc(col), {"cloth": 0.8, "leather": 0.55, "paper": 0.45}[kind])
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    if kind == "cloth":
        weave = (np.sin(xx * 2.2) * np.sin(yy * 2.2)) * 0.5 + 0.5
        t.height = weave * 0.3
        t.col = mix(t.col, t.col * 0.85, weave * 0.25)
    elif kind == "leather":
        d1, d21, _ = voronoi(h, w, int(w * h / 30), seed)
        t.height = smooth(0, 2.5, d21) * 0.5
        t.col = mix(t.col, t.col * 0.7, smooth(2.0, 0, d21) * 0.5)
    else:
        t.height = fbm(h, w, 3, seed) * 0.1
    # sun fade and rubbed high spots
    fade = fbm(h, w, 50, seed + 1)
    light = np.array(hexc("d8cdb8"))
    t.col = mix(t.col, light, smooth(0.55, 0.85, fade) * (0.18 if kind != "paper" else 0.1))
    ends = smooth(h * 0.035, 0, np.minimum(yy, h - 1 - yy))        # frayed head and tail
    rub = ends * (0.5 + 0.5 * fbm(h, w, 3, seed + 2))
    t.col = mix(t.col, light * 0.8, rub * (0.55 if kind == "cloth" else 0.35))
    edge = smooth(w * 0.12, 0, np.minimum(xx, w - 1 - xx))           # rounded spine edges wear
    t.col = mix(t.col, t.col * 0.75, edge * 0.5)
    t.rough = t.rough + rub * 0.1
    scuff = smooth(0.78, 0.9, fbm(h, w, 7, seed + 4))
    t.col = mix(t.col, light * 0.85, scuff * 0.25)
    return t


def g_spine(spec):
    """spec: dict(col, kind, title, author, font, ink, gilt(bool), bands(int), label(col|None))."""
    def f(w, h, seed):
        # work in horizontal space: L = h (along spine), T = w (across)
        L, T = h, w
        th = spine_base(L, T, seed, spec["col"], spec["kind"])  # arrays (T, L)
        # draw in horizontal space then rotate at the end
        ink = hexc(spec.get("ink", "d9b25e"))
        metal = 1.0 if spec.get("gilt") else 0.0
        rough = 0.35 if spec.get("gilt") else 0.6
        xx = np.arange(L)[None, :] * np.ones((T, 1))
        yy = np.arange(T)[:, None] * np.ones((1, L))
        bands = spec.get("bands", 0)
        if bands:
            for k in range(bands):
                cx = L * (0.2 + 0.6 * k / max(1, bands - 1))
                ridge = smooth(3.2, 0, np.abs(xx - cx))
                th.height += ridge * 1.2
                th.paint(smooth(0.8, 0, np.abs(np.abs(xx - cx) - 3.6)), ink, rough, metal)
        if spec.get("rules", True) and spec["kind"] != "paper":
            for cx in (L * 0.06, L * 0.075, L * 0.925, L * 0.94):
                th.paint(smooth(0.9, 0.2, np.abs(xx - cx)), ink, rough, metal, 0.1)
        x_title = spec.get("x", 0.42)
        lab = spec.get("label")
        title = spec["title"]
        fn = spec.get("font", "garamond")
        wg = spec.get("wght", 600)
        lines = []
        if lab:
            lw = L * 0.3
            m = ((np.abs(xx - L * x_title) < lw / 2) & (yy > T * 0.14) & (yy < T * 0.86)).astype(float)
            th.paint(m, hexc(lab), 0.5, 0.0, 0.2)
            size = fit_size(title, fn, T * 0.5, wg, lw * 0.9)
            lines.append((title, fn, size, wg, (L * x_title, T * 0.5), "mm"))
        else:
            tl = title.split("\n")
            n = len(tl)
            size = min(fit_size(s, fn, T * (0.62 if n == 1 else 0.36) * spec.get("scale", 1), wg,
                                L * spec.get("span", 0.62)) for s in tl)
            for i, s in enumerate(tl):
                yc = T * (0.5 + (i - (n - 1) / 2) * 0.4)
                lines.append((s, fn, size, wg, (L * x_title, yc), "mm"))
        if spec.get("author"):
            afn = spec.get("afont", fn)
            asz = fit_size(spec["author"], afn, T * 0.34, 500, L * spec.get("aw", 0.2))
            lines.append((spec["author"], afn, asz, 500, (L * spec.get("ax", 0.83), T * 0.5), "mm"))
        m = text_mask(L, T, lines)
        th.paint(m, ink, rough, metal, -0.15 if spec["kind"] != "paper" else 0)
        extra = spec.get("extra")
        if extra:
            extra(th, L, T, xx, yy)
        # rotate the horizontal-space layers so the title reads top->bottom on a standing book
        t = Tex(w, h)
        t.col = np.rot90(th.col, k=-1)
        t.rough = np.rot90(th.rough, k=-1)
        t.metal = np.rot90(th.metal, k=-1)
        t.height = np.rot90(th.height, k=-1)
        t.hscale = 0.8
        return t
    return f


def named_spines():
    def band(col, x0, x1):
        def e(th, L, T, xx, yy):
            th.paint(((xx > L * x0) & (xx < L * x1)).astype(float), hexc(col), 0.45)
        return e

    def two(e1, e2):
        def e(*a):
            e1(*a)
            e2(*a)
        return e
    specs = {
        "order_of_time": dict(col="182a4f", kind="paper", title="THE ORDER OF TIME", font="oswald", wght=500,
                              ink="f3efe4", author="CARLO ROVELLI", afont="oswald", x=0.37, ax=0.8, span=0.56,
                              aw=0.2, extra=band("e5a33a", 0.94, 0.98)),
        "geb": dict(col="efe9dc", kind="paper", title="GÖDEL, ESCHER, BACH", font="playfair", wght=800,
                    ink="1b1b1b", author="HOFSTADTER", afont="playfair", x=0.4, ax=0.83, span=0.58, aw=0.2,
                    extra=band("9c1f24", 0.03, 0.1)),
        "feynman_1": dict(col="8e1b1d", kind="cloth", gilt=True, title="THE FEYNMAN LECTURES\nON PHYSICS",
                          font="cinzel", wght=700, ink="e2bd6a", author="VOL. I", afont="cinzel", x=0.42, ax=0.84,
                          span=0.66, scale=1.0),
        "feynman_2": dict(col="8e1b1d", kind="cloth", gilt=True, title="THE FEYNMAN LECTURES\nON PHYSICS",
                          font="cinzel", wght=700, ink="e2bd6a", author="VOL. II", afont="cinzel", x=0.42, ax=0.84,
                          span=0.66),
        "feynman_3": dict(col="8e1b1d", kind="cloth", gilt=True, title="THE FEYNMAN LECTURES\nON PHYSICS",
                          font="cinzel", wght=700, ink="e2bd6a", author="VOL. III", afont="cinzel", x=0.42, ax=0.84,
                          span=0.66),
        "being_you": dict(col="141414", kind="paper", title="BEING YOU", font="bebas", ink="f2c230",
                          author="ANIL SETH", afont="oswald", x=0.35, ax=0.78, span=0.48, scale=1.15,
                          aw=0.2, extra=band("e24a2a", 0.93, 0.97)),
        "book_of_why": dict(col="f4f1ea", kind="paper", title="THE BOOK OF WHY", font="josefin", wght=700,
                            ink="161616", author="PEARL & MACKENZIE", afont="josefin", x=0.37, ax=0.8, span=0.54, aw=0.24,
                            extra=band("2a5aa8", 0.93, 0.975)),
    }
    return specs


GENERIC_TITLES = [
    ("Faust", "Goethe", "leather"), ("Kritik der reinen Vernunft", "Kant", "leather"),
    ("Also sprach Zarathustra", "Nietzsche", "leather"), ("Der Zauberberg", "Mann", "cloth"),
    ("Siddhartha", "Hesse", "cloth"), ("Walden", "Thoreau", "cloth"), ("Moby-Dick", "Melville", "cloth"),
    ("Principia", "Newton", "leather"), ("Meditations", "Aurelius", "leather"), ("Flatland", "Abbott", "cloth"),
    ("A Brief History of Time", "Hawking", "paper"), ("Seven Brief Lessons on Physics", "Rovelli", "paper"),
    ("Helgoland", "Rovelli", "paper"), ("QED", "Feynman", "paper"), ("The Character of Physical Law", "Feynman", "paper"),
    ("I Am a Strange Loop", "Hofstadter", "paper"), ("The Mind's I", "Hofstadter & Dennett", "paper"),
    ("Consciousness Explained", "Dennett", "paper"), ("The Beginning of Infinity", "Deutsch", "paper"),
    ("The Fabric of Reality", "Deutsch", "paper"), ("Thinking, Fast and Slow", "Kahneman", "paper"),
    ("Causality", "Pearl", "cloth"), ("Tractatus", "Wittgenstein", "cloth"),
    ("Philosophical Investigations", "Wittgenstein", "cloth"),
    ("The Structure of Scientific Revolutions", "Kuhn", "paper"), ("Cosmos", "Sagan", "paper"),
    ("The Elegant Universe", "Greene", "paper"), ("Six Easy Pieces", "Feynman", "paper"),
    ("Gödel's Proof", "Nagel & Newman", "paper"), ("The Emperor's New Mind", "Penrose", "paper"),
    ("The Road to Reality", "Penrose", "cloth"), ("What Is Life?", "Schrödinger", "cloth"),
    ("Order out of Chaos", "Prigogine", "paper"), ("Probability Theory", "Jaynes", "cloth"),
    ("Buddenbrooks", "Mann", "cloth"), ("Der Steppenwolf", "Hesse", "cloth"), ("Grimms Märchen", "", "leather"),
    ("Die Verwandlung", "Kafka", "cloth"), ("The Selfish Gene", "Dawkins", "paper"),
    ("Surfaces and Essences", "Hofstadter", "paper"), ("The Waste Land", "Eliot", "cloth"),
    ("Mind and Cosmos", "Nagel", "paper"), ("Reality Is Not What It Seems", "Rovelli", "paper"),
    ("The Feeling of What Happens", "Damasio", "paper"), ("Critique of Judgment", "Kant", "leather"),
    ("Ethik", "Spinoza", "leather"), ("Die Welt als Wille", "Schopenhauer", "leather"),
    ("Der Prozess", "Kafka", "cloth"),
]


def generic_spine(i, title, author, kind, rng):
    col = SPINE_COLS[(i * 7 + 3) % len(SPINE_COLS)]
    if kind == "leather":
        col = ["5a3522", "3e2618", "6b2a1c", "2e2a22"][i % 4]
        return dict(col=col, kind="leather", gilt=True, title=title, font=["garamond", "fell", "cinzel"][i % 3],
                    wght=600, ink="d8b060", bands=4, label=["6e1a1a", "1e1e1e", "25402a"][i % 3], x=0.3)
    if kind == "cloth":
        light = col in ("e8dfc8", "d8c9a2", "b49a6a")
        return dict(col=col, kind="cloth", gilt=not light, title=title, author=author,
                    font=["garamond", "baskerville", "cinzel", "fell"][i % 4], wght=600,
                    ink="1c1a18" if light else "d9b25e", x=0.4, span=0.54, ax=0.81, aw=0.17)
    # paperback with printed blocks
    ink = "f4efe4" if col not in ("e8dfc8", "d8c9a2", "b49a6a") else "1c1a18"
    fnt = ["oswald", "josefin", "bebas", "playfair", "garamond"][i % 5]

    def extra(th, L, T, xx, yy, i=i):
        c2 = hexc(SPINE_COLS[(i * 5 + 1) % len(SPINE_COLS)])
        th.paint(((xx > L * 0.88) & (xx < L * 0.97)).astype(float), c2, 0.45)
        # publisher mark: a small circle
        m = smooth(T * 0.22, T * 0.18, np.hypot(xx - L * 0.925, yy - T * 0.5))
        th.paint(m, hexc(ink), 0.45)
    return dict(col=col, kind="paper", title=title.upper() if fnt in ("oswald", "bebas") else title, author=author.upper()
                if fnt in ("oswald", "bebas") else author, font=fnt, wght=600, ink=ink, x=0.36, ax=0.74, span=0.48, aw=0.18,
                extra=extra)


def g_chalkboard(w, h, seed):
    t = Tex(w, h, hexc("24292a"), 0.88)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    smear = fbm(h, w, 40, seed)
    t.col = mix(t.col, np.array(hexc("4a5152")), smooth(0.45, 0.8, smear) * 0.55)      # old wiped chalk
    t.col = mix(t.col, np.array(hexc("5b6263")), smooth(0.6, 0.9, fbm(h, w, 8, seed + 2)) * 0.15)
    rows = [("Bier vom Fass", "caveat", 50, 700, (w * 0.5, h * 0.12), "mm")]
    items = [("Helles", "0,5 l", "4,80"), ("Dunkles", "0,5 l", "5,00"), ("Weißbier", "0,5 l", "5,20"),
             ("Radler", "0,5 l", "4,50"), ("Maß Helles", "1 l", "9,50")]
    for k, (a, b, c) in enumerate(items):
        y = h * (0.3 + k * 0.118)
        rows.append((a, "caveat", 33, 600, (w * 0.07, y), "lm"))
        rows.append((b, "caveat", 27, 500, (w * 0.55, y), "lm"))
        rows.append((c + " €", "caveat", 33, 600, (w * 0.93, y), "rm"))
    rows.append(("Glaspfand 3,00 €", "caveat", 25, 500, (w * 0.5, h * 0.92), "mm"))
    m = text_mask(w, h, rows)
    grain = 0.55 + 0.45 * fbm(h, w, 1.5, seed + 5)
    t.paint(m * grain, hexc("eeeae0"), 0.95, height=0.2)
    # a hand-drawn underline and a doodled mug
    def doodle(d, ss):
        d.line([(w * 0.28 * ss, h * 0.2 * ss), (w * 0.72 * ss, h * 0.195 * ss)], fill=255, width=int(2 * ss))
        x, y = w * 0.86, h * 0.06
        d.rectangle([x * ss, y * ss, (x + 24) * ss, (y + 30) * ss], outline=255, width=int(2 * ss))
        d.arc([(x + 18) * ss, (y + 6) * ss, (x + 34) * ss, (y + 22) * ss], -90, 90, fill=255, width=int(2 * ss))
        for k in range(4):
            d.ellipse([(x - 2 + k * 7) * ss, (y - 6) * ss, (x + 8 + k * 7) * ss, (y + 3) * ss], outline=255, width=int(2 * ss))
    t.paint(shape_mask(w, h, doodle) * grain, hexc("eeeae0"), 0.95)
    t.paint(shape_mask(w, h, lambda d, ss: [d.ellipse([(w * 0.1 + k * 9) * ss, (h * 0.12 - 4 + (k % 2) * 3) * ss,
                                                       (w * 0.1 + k * 9 + 5) * ss, (h * 0.12 + 1 + (k % 2) * 3) * ss],
                                                      fill=255) for k in range(4)]) * grain, hexc("f2b8c0"), 0.95)
    t.height += fbm(h, w, 3, seed + 7) * 0.2
    return t


def g_coaster(w, h, seed):
    t = Tex(w, h, hexc("f1ece1"), 0.9)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
    t.paint(smooth(0.92, 0.9, r) - smooth(0.86, 0.84, r), hexc("1d4d8f"), 0.8)
    # Rauten diamonds in the middle band
    dia = ((np.abs(((xx + yy) / 10) % 2 - 1) < 0.5) ^ (np.abs(((xx - yy) / 10) % 2 - 1) < 0.5)).astype(float)
    t.paint(dia * ((yy > h * 0.56) & (yy < h * 0.74) & (r < 0.84)), hexc("2e6bb8"), 0.8)
    t.paint(text_mask(w, h, [("Prosit", "fraktur", h * 0.22, None, (w / 2, h * 0.38), "mm")]), hexc("1d3b6e"), 0.8)
    t.col = mix(t.col, np.array(hexc("c9a878")), smooth(0.6, 0.85, fbm(h, w, 25, seed)) * 0.35)   # beer rings
    t.height = fbm(h, w, 2, seed) * 0.3
    return t


def g_foam(w, h, seed):
    t = Tex(w, h, hexc("fbf6ea"), 0.55)
    d1, d21, _ = voronoi(h, w, int(w * h / 10), seed)
    t.height = np.clip(d1 / 3, 0, 1) * 0.8
    t.col = mix(t.col, np.array(hexc("e7d9bb")), smooth(0.6, 0.0, d21) * 0.25 + fbm(h, w, 30, seed) * 0.15)
    return t


def g_dimples(w, h, seed):
    """Maßkrug glass: rows of oval thumbprint dimples (height only, base white)."""
    t = Tex(w, h, (1, 1, 1), 0.05)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    cols, rows = 10, 5
    cw, rh = w / cols, h / (rows + 1.2)
    fy = (yy - rh * 0.6) / rh
    ry = np.round(fy)
    off = (ry % 2) * 0.5
    fx = xx / cw - off
    dx = fx - np.round(fx)
    dy = fy - ry
    d = np.sqrt((dx / 0.42) ** 2 + (dy / 0.46) ** 2)
    inside = (ry >= 0) & (ry < rows)
    t.height = np.where(inside, -np.clip(1 - d ** 2, 0, 1) * 3.0, 0)
    t.hscale = 1.0
    return t


def g_sausage(dark):
    """Grilled sausage skin along U (length), v around. Grill marks, blisters, char."""
    def f(w, h, seed):
        base = hexc("7a3a1c") if dark else hexc("a8653a")
        t = Tex(w, h, base, 0.32)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        brown = fbm(h, w, 18, seed)
        t.col = mix(t.col, np.array(hexc("6a2f16")), smooth(0.35, 0.8, brown) * 0.7)
        # diagonal grill marks, darker and slightly sunken, twice around (both sides grilled)
        marks = np.zeros((h, w))
        for k in range(9):
            c = (k + 0.5) * w / 9
            dd = np.abs((xx - c) + (yy - h * 0.25) * 0.35)
            marks = np.maximum(marks, smooth(5, 1.5, dd) * (smooth(h * 0.05, h * 0.2, yy) * smooth(h * 0.48, h * 0.32, yy)))
            dd2 = np.abs((xx - c) + (yy - h * 0.75) * 0.35)
            marks = np.maximum(marks, smooth(5, 1.5, dd2) * (smooth(h * 0.55, h * 0.7, yy) * smooth(h * 0.98, h * 0.82, yy)))
        marks *= 0.6 + 0.4 * fbm(h, w, 4, seed + 1)
        t.paint(marks, hexc("1d0f08"), 0.55, height=-0.6)
        blist = smooth(0.7, 0.85, fbm(h, w, 3, seed + 2))
        t.paint(blist * 0.6, hexc("e0a36b"), 0.18, height=0.5)
        # tied ends slightly paler
        ends = smooth(w * 0.05, 0, np.minimum(xx, w - 1 - xx))
        t.col = mix(t.col, t.col * 1.2, ends * 0.4)
        t.height += fbm(h, w, 6, seed + 3) * 0.3
        t.col = np.clip(t.col, 0, 1)
        return t
    return f


def g_roll(w, h, seed):
    """Bread roll seen from above (planar mapped): golden crust, a scored slash with pale crumb."""
    t = Tex(w, h, hexc("b0682a"), 0.7)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    t.col = mix(t.col, np.array(hexc("7a3e14")), smooth(0.3, 0.8, fbm(h, w, 14, seed)) * 0.6 * smooth(0.95, 0.2, r))
    t.col = mix(t.col, np.array(hexc("d8a060")), smooth(0.75, 1.0, r) * 0.6)
    slash = np.abs((yy - h / 2) - (xx - w / 2) * 0.15 + np.sin(xx / w * 6) * 2)
    cut = smooth(h * 0.06, h * 0.02, slash) * smooth(0.7, 0.5, r)
    t.paint(cut, hexc("f0dcb0"), 0.85, height=-1.0)
    flour = smooth(0.8, 0.95, fbm(h, w, 5, seed + 3))
    t.paint(flour * 0.35, hexc("f4efe6"), 0.9)
    t.height += fbm(h, w, 4, seed + 2) * 0.5
    return t


def g_paper(w, h, seed, grease=True):
    t = Tex(w, h, hexc("f2efe8"), 0.85)
    t.col = mix(t.col, np.array(hexc("d9d2c2")), fbm(h, w, 20, seed) * 0.3)
    if grease:
        g = smooth(0.62, 0.72, fbm(h, w, 25, seed + 1))
        t.paint(g * 0.6, hexc("d8b98a"), 0.45)
    t.height = fbm(h, w, 2, seed + 2) * 0.2
    return t


def g_kraft(w, h, seed, text=None):
    t = Tex(w, h, hexc("b98a57"), 0.85)
    rng = np.random.default_rng(seed)
    fib = ndimage.uniform_filter1d(rng.random((h, w)), 12, axis=1)
    t.col = mix(t.col, np.array(hexc("8f6538")), fib * 0.35 + fbm(h, w, 30, seed) * 0.2)
    if text:
        t.paint(text_mask(w, h, [(text, "alegreya", h * 0.16, None, (w / 2, h * 0.45), "mm")]), hexc("5a1a12"), 0.8)
    t.height = fib * 0.3
    return t


def g_coal(w, h, seed):
    """Charcoal bed: black, grey ash, glowing cracks (base colour; the glow is in atlas_emit)."""
    t = Tex(w, h, hexc("181614"), 0.9)
    d1, d21, cid = voronoi(h, w, int(w * h / 350), seed)
    crack = smooth(2.4, 0.0, d21) * smooth(0.3, 0.55, fbm(h, w, 30, seed + 6))
    ash = smooth(0.45, 0.75, fbm(h, w, 10, seed + 1))
    t.col = mix(t.col, np.array(hexc("8a8580")), ash * 0.75)
    t.col = mix(t.col, np.array(hexc("c85a1a")), crack * 0.6)
    t.height = -crack * 1.0 + np.clip(d1 / 12, 0, 1) * 0.8
    return t


def coal_emit(w, h, seed):
    d1, d21, cid = voronoi(h, w, int(w * h / 350), seed)
    crack = smooth(2.4, 0.0, d21) * smooth(0.3, 0.55, fbm(h, w, 30, seed + 6))
    hot = smooth(0.35, 0.7, fbm(h, w, 25, seed + 5))
    glow = np.clip(crack * 1.0 + hot * smooth(0.8, 0, np.clip(d1 / 12, 0, 1)) * 0.8, 0, 1)
    glow = ndimage.gaussian_filter(glow, 1.2)
    col = np.stack([glow, glow ** 1.6 * 0.42, glow ** 3 * 0.08], -1)
    return col


def g_lebkuchen(text, border_col, text_col, seed_flowers=True):
    """Lebkuchen heart face (planar): glossy brown dough, piped icing border, lettering, flowers."""
    def f(w, h, seed):
        t = Tex(w, h, hexc("7a3f1c"), 0.42)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.col = mix(t.col, np.array(hexc("5a2c12")), fbm(h, w, 20, seed) * 0.5)
        t.height = fbm(h, w, 6, seed + 1) * 0.4
        cx, cy = w / 2, h * 0.47
        s = w / 36

        def heart_pts(scale):
            pts = []
            for i in range(80):
                a = 2 * math.pi * i / 80
                x = 16 * math.sin(a) ** 3
                y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
                pts.append((cx + x * s * scale, cy - y * s * scale))
            return pts
        # scalloped piped border: a ring of dots along an inner heart
        def border(d, ss):
            pts = heart_pts(0.86)
            for i, (x, y) in enumerate(pts):
                if i % 2 == 0:
                    d.ellipse([(x - 3.2) * ss, (y - 3.2) * ss, (x + 3.2) * ss, (y + 3.2) * ss], fill=255)
            d.line([(x * ss, y * ss) for x, y in heart_pts(0.74)] + [(heart_pts(0.74)[0][0] * ss, heart_pts(0.74)[0][1] * ss)],
                   fill=255, width=int(2.2 * ss))
        bm = shape_mask(w, h, border)
        t.paint(bm, hexc(border_col), 0.5, height=1.5)
        lines = text.split("\n")
        rows = []
        for i, ln in enumerate(lines):
            sz = fit_size(ln, "pacifico", h * 0.13, None, w * 0.52)
            rows.append((ln, "pacifico", sz, None, (cx, cy - (len(lines) - 1) * h * 0.075 + i * h * 0.15), "mm"))
        tm = text_mask(w, h, rows)
        t.paint(tm, hexc(text_col), 0.5, height=1.4)
        if seed_flowers:
            rng = np.random.default_rng(seed)
            def flowers(d, ss):
                for fx, fy in ((cx - w * 0.2, cy + h * 0.2), (cx + w * 0.2, cy + h * 0.2), (cx, cy + h * 0.3)):
                    for k in range(5):
                        a = k * 2 * math.pi / 5
                        px, py = fx + 5 * math.cos(a), fy + 5 * math.sin(a)
                        d.ellipse([(px - 3) * ss, (py - 3) * ss, (px + 3) * ss, (py + 3) * ss], fill=255)
            fm = shape_mask(w, h, flowers)
            t.paint(fm, hexc(["e05a8a", "f2d23a", "5aa0e0"][seed % 3]), 0.5, height=1.2)
            t.paint(shape_mask(w, h, lambda d, ss: [d.ellipse([(x - 2) * ss, (y - 2) * ss, (x + 2) * ss, (y + 2) * ss], fill=255)
                                                    for x, y in ((cx - w * 0.2, cy + h * 0.2), (cx + w * 0.2, cy + h * 0.2),
                                                                 (cx, cy + h * 0.3))]), hexc("f7f2e8"), 0.5, height=1.3)
        # icing stays matte-ish, dough glaze shiny
        t.hscale = 0.8
        return t
    return f


def g_almonds(w, h, seed):
    t = Tex(w, h, hexc("8a3e1a"), 0.35)
    d1, d21, cid = voronoi(h, w, int(w * h / 90), seed)
    lump = np.clip(1 - d1 / 7, 0, 1)
    t.height = lump * 1.2
    t.col = mix(t.col, np.array(hexc("4e1f0c")), smooth(1.5, 0, d21) * 0.7)
    sugar = smooth(0.75, 0.9, noise(h, w, 1.2, seed + 1))
    t.paint(sugar * 0.5, hexc("d69c63"), 0.25, height=0.3)
    return t


def g_cone_paper(w, h, seed):
    t = g_paper(w, h, seed, grease=False)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    stripes = ((xx + yy * 0.6) // 14 % 2 == 0).astype(float)
    t.paint(stripes * 0.9, hexc("b0282a"), 0.8)
    t.paint(text_mask(w, h, [("Mandeln", "fraktur", h * 0.17, None, (w / 2, h * 0.5), "mm")]) , hexc("f4efe4"), 0.8)
    return t


def g_wax(w, h, seed):
    t = Tex(w, h, (0.96, 0.94, 0.9), 0.45)
    t.col = mix(t.col, t.col * 0.88, fbm(h, w, 12, seed) * 0.5)
    rng = np.random.default_rng(seed)
    drips = ndimage.uniform_filter1d(rng.random((h, w)), 30, axis=0)
    t.height = drips * 0.4 + fbm(h, w, 4, seed) * 0.2
    return t


def g_honeycomb(w, h, seed):
    t = Tex(w, h, hexc("e0a63a"), 0.5)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    s = 6.0
    q = (xx * math.sqrt(3) / 3 - yy / 3) / s
    r = yy * 2 / 3 / s
    # hex distance
    x, z = q, r
    y = -x - z
    rx, ry, rz = np.round(x), np.round(y), np.round(z)
    dx, dy, dz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
    d = np.maximum(np.maximum(dx, dy), dz)
    t.height = smooth(0.25, 0.45, d) * 1.2
    t.col = mix(t.col, np.array(hexc("b27820")), smooth(0.3, 0.5, d) * 0.5)
    return t


def g_cheese_rind(w, h, seed):
    t = Tex(w, h, hexc("d9a24e"), 0.7)
    t.col = mix(t.col, np.array(hexc("a8692c")), fbm(h, w, 15, seed) * 0.6)
    t.col = mix(t.col, np.array(hexc("efe0b0")), smooth(0.7, 0.85, fbm(h, w, 6, seed + 2)) * 0.4)
    t.height = fbm(h, w, 3, seed + 3) * 0.6
    return t


def g_cheese_cut(w, h, seed):
    t = Tex(w, h, hexc("f2dc8a"), 0.55)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, np.array(hexc("e9c870")), fbm(h, w, 25, seed) * 0.4)
    for k in range(14):
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(3, 10)
        d = np.hypot(xx - cx, (yy - cy) * 1.2)
        hole = smooth(r, r * 0.8, d)
        t.paint(hole, hexc("d4b25a"), 0.3, height=-1.5 * hole)
    return t


def g_crepe(w, h, seed):
    """Crêpe on the griddle, face-on: pale batter with a lacy browned pattern and a darker rim."""
    t = Tex(w, h, hexc("f0d59a"), 0.55)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
    lace = fbm(h, w, 7, seed)
    t.col = mix(t.col, np.array(hexc("c2843a")), smooth(0.5, 0.7, lace) * 0.8)
    t.col = mix(t.col, np.array(hexc("8f5424")), smooth(0.66, 0.8, lace) * 0.6)
    t.col = mix(t.col, np.array(hexc("b77432")), smooth(0.85, 0.98, r) * 0.7)
    t.height = lace * 0.5
    return t


def g_chestnut(w, h, seed):
    """Roasted chestnut shell (spherical map: v from base to tip): glossy brown, pale base, a charred cross."""
    t = Tex(w, h, hexc("6b2e14"), 0.3)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, np.array(hexc("3c160a")), fbm(h, w, 10, seed) * 0.6)
    rng = np.random.default_rng(seed)
    stria = ndimage.uniform_filter1d(rng.random((h, w)), 25, axis=0)
    t.col = mix(t.col, t.col * 1.3, stria * 0.3)
    base = smooth(h * 0.72, h * 0.85, yy)       # row h = bottom (v=0)
    t.paint(base, hexc("c9a47a"), 0.8, height=0.2)
    t.paint(smooth(h * 0.12, 0, yy) * (np.abs(np.sin(xx / w * 4 * math.pi)) > 0.8), hexc("1a0c06"), 0.7)
    char = smooth(0.7, 0.85, fbm(h, w, 5, seed + 3))
    t.paint(char * 0.7, hexc("1a0c06"), 0.6)
    t.height += stria * 0.4
    return t


def g_puffer(w, h, seed):
    """Potato pancake, face-on: shredded potato, golden with crispy dark edges."""
    t = Tex(w, h, hexc("d9a24a"), 0.4)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    shreds = np.zeros((h, w))
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for k in range(700):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(6, 16)
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=int(rng.uniform(90, 255)), width=2)
    shreds = np.asarray(im.filter(ImageFilter.GaussianBlur(0.6)), float) / 255
    r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
    t.col = mix(t.col, np.array(hexc("f0cf7a")), shreds * 0.5)
    t.col = mix(t.col, np.array(hexc("8a4a18")), smooth(0.6, 0.95, r + fbm(h, w, 10, seed) * 0.3) * 0.8)
    t.col = mix(t.col, np.array(hexc("5a2a0c")), smooth(0.85, 1.0, fbm(h, w, 5, seed + 4)) * 0.4)
    t.height = shreds * 0.9
    return t


def g_straw(w, h, seed):
    t = Tex(w, h, hexc("e3c27a"), 0.5)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, np.array(hexc("b58a3e")), (np.sin(yy * 1.3) * 0.5 + 0.5) * 0.3)
    t.height = np.sin(yy * 1.3) * 0.3
    return t


def g_burlap(w, h, seed):
    t = Tex(w, h, hexc("a88b5e"), 0.9)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    weave = (np.sin(xx * 1.1) * 0.5 + 0.5) * (np.sin(yy * 1.1 + math.pi / 2) * 0.5 + 0.5)
    t.col = mix(t.col, np.array(hexc("6e5634")), (1 - weave) * 0.5 + fbm(h, w, 20, seed) * 0.2)
    t.height = weave * 0.8
    return t


def g_grate(w, h, seed):
    """Drip tray grate: brushed steel with rows of slots."""
    t = g_steel(w, h, seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    slot = ((xx % 12) > 3) & ((xx % 12) < 9) & ((yy % 20) > 3) & ((yy % 20) < 17)
    t.paint(slot.astype(float), hexc("1a1c1d"), 0.6, 0.3, height=-1.5)
    return t


def g_toy_face(w, h, seed):
    """Nutcracker face (planar): painted skin, big eyes, white beard and moustache, red cheeks."""
    t = Tex(w, h, hexc("f0c8a0"), 0.35)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    def face(d, ss):
        for ex in (w * 0.33, w * 0.67):
            d.ellipse([(ex - 5) * ss, (h * 0.3 - 4) * ss, (ex + 5) * ss, (h * 0.3 + 4) * ss], fill=255)
    t.paint(shape_mask(w, h, face), hexc("f8f6f0"), 0.3)
    def pup(d, ss):
        for ex in (w * 0.33, w * 0.67):
            d.ellipse([(ex - 2.5) * ss, (h * 0.3 - 2.5) * ss, (ex + 2.5) * ss, (h * 0.3 + 2.5) * ss], fill=255)
        for ex in (w * 0.33, w * 0.67):
            d.arc([(ex - 7) * ss, (h * 0.2 - 3) * ss, (ex + 7) * ss, (h * 0.2 + 5) * ss], 200, 340, fill=255, width=int(2 * ss))
    t.paint(shape_mask(w, h, pup), hexc("151515"), 0.3)
    t.paint(smooth(8, 3, np.hypot(xx - w * 0.22, yy - h * 0.5)) + smooth(8, 3, np.hypot(xx - w * 0.78, yy - h * 0.5)),
            hexc("d8605a"), 0.35)
    beard = smooth(h * 0.55, h * 0.62, yy + fbm(h, w, 4, seed) * 6)
    t.paint(beard, hexc("f4f1ea"), 0.8, height=0.8)
    must = smooth(6, 2, np.abs(yy - h * 0.56 - np.abs(xx - w / 2) * -0.25)) * (np.abs(xx - w / 2) < w * 0.3)
    t.paint(must, hexc("f4f1ea"), 0.8, height=0.6)
    t.paint(smooth(4, 2, np.abs(yy - h * 0.66)) * (np.abs(xx - w / 2) < w * 0.12), hexc("8a1a1a"), 0.3)
    return t


# ============================================================ region list
def region_specs():
    """[(name, w, h, generator)] in atlas px."""
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    # flat swatches: white base, colour comes from COLOR_0
    for n, r, m in (("sw_matte", 0.88, 0), ("sw_satin", 0.5, 0), ("sw_gloss", 0.22, 0), ("sw_vgloss", 0.06, 0),
                    ("sw_metal_rough", 0.55, 1), ("sw_metal", 0.28, 1), ("sw_metal_polish", 0.1, 1),
                    ("sw_wax", 0.4, 0), ("sw_wet", 0.12, 0)):
        add(n, 16, 16, g_swatch(r, m))
    add("copper", 256, 256, g_copper)
    add("brass", 128, 128, g_brass)
    add("steel", 128, 128, g_steel)
    add("iron", 256, 256, g_iron)
    add("wood", 512, 128, g_wood)
    add("wood_end", 128, 128, g_wood_end)
    add("ceramic", 128, 128, g_ceramic)
    add("bisque", 64, 64, g_bisque)
    for s in ("red", "blue", "cream", "green", "brown", "white", "santa", "bluestar"):
        add("mug_" + s, 256, 112, g_mug(s))
    labels = [("label_wine", "Winzer-Glühwein", "rot · 11 % vol", "f0e6cc", "5a1218", "garamond", "garamond", True, None),
              ("label_white", "Glühwein", "weiß · Riesling", "f4efe0", "2d4a2a", "fraktur", "garamond", True, None),
              ("label_berry", "Heidelbeer", "Fruchtglühwein", "2a2350", "efe6cc", "playfair", "garamond", True, None),
              ("label_rum", "RUM", "Schuss · 54 %", "e8d9b0", "1a1a1a", "cinzel", "garamond", True, "8a1a1a"),
              ("label_amaretto", "Amaretto", "Mandellikör", "d9c08a", "4a1a0a", "pacifico", "garamond", True, None),
              ("label_punsch", "Kinderpunsch", "ohne Alkohol", "f2e4c8", "b0282a", "baskerville", "garamond", True, None)]
    for n, a, b, bg, ink, f1, f2, bd, st in labels:
        add(n, 160, 112, g_label(a, b, bg, ink, f1, f2, bd, st))
    for n, a in (("jar_zimt", "Zimt"), ("jar_nelken", "Nelken"), ("jar_anis", "Sternanis"),
                 ("jar_orange", "Orangenschale"), ("jar_kardamom", "Kardamom")):
        add(n, 112, 64, g_label(a, None, "f1e8d2", "3a2414", "fell", "fell", True, None))
    add("orange_slice", 128, 128, g_orange_slice)
    add("peel", 64, 64, g_peel)
    add("cinnamon", 64, 128, g_cinnamon)
    add("pages_edge", 256, 48, g_pages_edge)
    add("pages_open", 512, 352, g_pages_open)
    add("chalkboard", 512, 352, g_chalkboard)
    add("coaster", 128, 128, g_coaster)
    add("foam", 128, 128, g_foam)
    add("dimples", 256, 128, g_dimples)
    add("sausage", 256, 64, g_sausage(False))
    add("sausage_dark", 256, 64, g_sausage(True))
    add("roll", 128, 96, g_roll)
    add("paper", 128, 128, lambda w, h, s: g_paper(w, h, s, True))
    add("kraft", 128, 128, lambda w, h, s: g_kraft(w, h, s, None))
    add("kraft_maroni", 128, 128, lambda w, h, s: g_kraft(w, h, s, "Heiße Maroni"))
    add("coal", 256, 256, g_coal)
    for i, (txt, bc, tc) in enumerate((("Ich liebe\nDich", "f7f2e8", "f7f2e8"), ("Frohe\nWeihnachten", "f2d23a", "f7f2e8"),
                                       ("Für Dich", "e05a8a", "f7f2e8"), ("Schatz", "5aa0e0", "f7f2e8"),
                                       ("Prost!", "f7f2e8", "f2d23a"), ("Nacht-\nmarkt", "e05a8a", "f7f2e8"))):
        add(f"lebkuchen_{i}", 192, 176, g_lebkuchen(txt, bc, tc))
    add("almonds", 128, 128, g_almonds)
    add("cone_paper", 128, 128, g_cone_paper)
    add("wax", 128, 128, g_wax)
    add("honeycomb", 128, 128, g_honeycomb)
    add("cheese_rind", 128, 128, g_cheese_rind)
    add("cheese_cut", 128, 128, g_cheese_cut)
    add("crepe", 192, 192, g_crepe)
    add("chestnut", 128, 128, g_chestnut)
    add("puffer", 192, 192, g_puffer)
    add("straw", 64, 64, g_straw)
    add("burlap", 128, 128, g_burlap)
    add("grate", 128, 64, g_grate)
    add("toy_face", 64, 64, g_toy_face)
    # book spines
    for key, spec in named_spines().items():
        add("spine_" + key, 80, 448, g_spine(spec))
    rng = np.random.default_rng(3)
    for i, (title, author, kind) in enumerate(GENERIC_TITLES):
        add(f"spine_g{i}", 48, 304, g_spine(generic_spine(i, title, author, kind, rng)))
    return R


def pack(specs, size):
    """Shelf packing, tallest first. Returns {name: (x, y, w, h)} of the inner rect (px, y down)."""
    order = sorted(specs, key=lambda s: (-(s[2]), -s[1]))
    x = y = row_h = 0
    out = {}
    for name, w, h, _ in order:
        W, H = w + 2 * PAD, h + 2 * PAD
        if x + W > size:
            x, y, row_h = 0, y + row_h, 0
        if y + H > size:
            raise RuntimeError(f"atlas full at {name}")
        out[name] = (x + PAD, y + PAD, w, h)
        x += W
        row_h = max(row_h, H)
    return out, y + row_h


def normal_from_height(hgt, k):
    gy, gx = np.gradient(hgt)
    nx, ny = -gx * k, gy * k          # image rows go down, V goes up
    nz = np.ones_like(hgt)
    n = np.stack([nx, ny, nz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def build(size=SIZE, out=OUT):
    os.makedirs(out, exist_ok=True)
    specs = region_specs()
    rects, used = pack(specs, size)
    col = np.zeros((size, size, 3))
    col[:] = 0.5
    rm = np.ones((size, size, 3))
    nrm = np.zeros((size, size, 3))
    nrm[:] = (0.5, 0.5, 1.0)
    regions = {}
    for i, (name, w, h, gen) in enumerate(specs):
        x, y, _, _ = rects[name]
        t = gen(w, h, 1000 + i * 13)
        n = normal_from_height(np.pad(t.height, 1, mode="edge"), t.hscale)[1:-1, 1:-1]
        layers = [(col, np.clip(t.col, 0, 1)), (rm, np.stack([np.ones((h, w)), np.clip(t.rough, 0.02, 1),
                                                           np.clip(t.metal, 0, 1)], -1)), (nrm, n)]
        for dst, src in layers:
            padded = np.pad(src, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
            dst[y - PAD:y + h + PAD, x - PAD:x + w + PAD] = padded
        # UV rect with a half-texel inset (v up)
        regions[name] = [(x + 0.5) / size, 1 - (y + h - 0.5) / size, (x + w - 0.5) / size, 1 - (y + 0.5) / size]
    to8 = lambda a: Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    to8(col).save(os.path.join(out, "atlas_color.png"))
    to8(rm).save(os.path.join(out, "atlas_rm.png"))
    to8(nrm).save(os.path.join(out, "atlas_normal.png"))
    # coal_glow has its own small texture pair (UV 0..1): base colour and the glow of the cracks
    cseed = 1000 + [s[0] for s in specs].index("coal") * 13
    to8(g_coal(256, 256, cseed).col).save(os.path.join(out, "coal_color.png"))
    to8(coal_emit(256, 256, cseed)).save(os.path.join(out, "coal_emit.png"))
    meta = {"size": size, "used_rows_px": used, "regions": regions}
    with open(os.path.join(out, "regions.json"), "w") as f:
        json.dump(meta, f, indent=0)
    print(f"[atlas] {len(regions)} regions, {used}px of {size} used -> {out}")
    return meta


if __name__ == "__main__":
    build()
