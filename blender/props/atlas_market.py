"""Round 8 (ADR 0004): the market-goods atlas, market_*.png -> prop_tex_market_*.webp.

The main goods atlas (vendor_atlas, 1944 of 2048 rows used) and the print atlas are full, so the goods
that fill the deco stalls' shelves and the ornament shop get their own atlas: jar and box prints, cheese
labels, sacks, chalk menu boards, painted glass baubles (one wrap per bauble), the pickle, pine cone, bird,
mushroom, Herrnhut paper and the Räuchermännchen's face. Plain numpy + PIL, no bpy:

    python3 blender/props/atlas_market.py     # writes blender/out/vendor/market_*.png + market_regions.json

Same conventions as vendor_atlas (colour sRGB without lighting, rm: G roughness B metal, normal from height).
Everything is drawn here from noise, shapes and the bundled OFL fonts. No third-party images.
"""
import json
import math
import os

import numpy as np

import vendor_atlas as va
from vendor_atlas import Tex, fbm, fit_size, hexc, mix, noise, shape_mask, smooth, text_mask

OUT = va.OUT
SIZE = 2048
META = os.path.join(OUT, "market_regions.json")


# ------------------------------------------------------------------ printed labels and boxes
def g_label(title, sub, bg, ink, fn="fell", fn2="garamond", accent=None, shape="rect"):
    """A paper jar / box label: mottled paper, a ruled border, title and a smaller line."""
    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.72)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.col = mix(t.col, t.col * 0.86, fbm(h, w, 18, seed) * 0.5)
        if shape == "oval":
            r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
            t.paint(smooth(0.86, 0.83, r) - smooth(0.80, 0.77, r), hexc(accent or ink), 0.6)
        else:
            b = (((xx > 3) & (xx < w - 4) & (yy > 3) & (yy < h - 4)) &
                 ~((xx > 5) & (xx < w - 6) & (yy > 5) & (yy < h - 6))).astype(float)
            t.paint(b, hexc(accent or ink), 0.6)
        if accent:
            t.paint(((yy > h * 0.74) & (yy < h * 0.8)).astype(float), hexc(accent), 0.6)
        s1 = fit_size(title, fn, h * 0.34, 600, w * 0.8)
        rows = [(title, fn, s1, 600, (w / 2, h * (0.42 if sub else 0.5)), "mm")]
        if sub:
            rows.append((sub, fn2, fit_size(sub, fn2, h * 0.16, 500, w * 0.78), 500, (w / 2, h * 0.66), "mm"))
        t.paint(text_mask(w, h, rows), hexc(ink), 0.6)
        return t
    return f


def g_box(title, sub, bg, ink, gold="d8b048", fn="fraktur", motif="stars"):
    """A printed card carton front: coloured ground, gold ornament border, a motif row, Fraktur title."""
    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.55)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.col = mix(t.col, t.col * 0.85, fbm(h, w, 30, seed) * 0.4)
        g = hexc(gold)
        frame = (((xx > 5) & (xx < w - 6) & (yy > 5) & (yy < h - 6)) &
                 ~((xx > 8) & (xx < w - 9) & (yy > 8) & (yy < h - 9))).astype(float)
        t.paint(frame, g, 0.3, 0.9)

        def mot(d, s):
            n = max(4, int(w / 28))
            for i in range(n):
                cx = (i + 0.5) * w / n
                for cy in (h * 0.16, h * 0.86):
                    if motif == "stars":
                        pts = [(cx + (7 if k % 2 == 0 else 3) * math.cos(-math.pi / 2 + math.pi * k / 5),
                                cy + (7 if k % 2 == 0 else 3) * math.sin(-math.pi / 2 + math.pi * k / 5)) for k in range(10)]
                        d.polygon([(x * s, y * s) for x, y in pts], fill=255)
                    elif motif == "hearts":
                        d.ellipse([(cx - 5) * s, (cy - 4) * s, (cx) * s, (cy + 1) * s], fill=255)
                        d.ellipse([(cx) * s, (cy - 4) * s, (cx + 5) * s, (cy + 1) * s], fill=255)
                        d.polygon([((cx - 5) * s, (cy - 1) * s), ((cx + 5) * s, (cy - 1) * s), (cx * s, (cy + 6) * s)], fill=255)
                    else:  # dots
                        d.ellipse([(cx - 3) * s, (cy - 3) * s, (cx + 3) * s, (cy + 3) * s], fill=255)
        t.paint(shape_mask(w, h, mot), g, 0.3, 0.9)
        rows = [(title, fn, fit_size(title, fn, h * 0.3, None, w * 0.8), None, (w / 2, h * 0.45), "mm")]
        if sub:
            rows.append((sub, "garamond", fit_size(sub, "garamond", h * 0.13, 500, w * 0.75), 500, (w / 2, h * 0.67), "mm"))
        t.paint(text_mask(w, h, rows), hexc(ink), 0.4)
        return t
    return f


def g_sack(text, sub, base="a88b5e", ink="2a2018"):
    """Burlap sack with a stencilled name."""
    def f(w, h, seed):
        t = va.g_burlap(w, h, seed)
        t.col = mix(t.col, np.array(hexc(base)), 0.35)
        rows = [(text, "alegreya", fit_size(text, "alegreya", h * 0.2, None, w * 0.8), None, (w / 2, h * 0.42), "mm")]
        if sub:
            rows.append((sub, "oswald", fit_size(sub, "oswald", h * 0.11, 500, w * 0.7), 500, (w / 2, h * 0.62), "mm"))
        m = text_mask(w, h, rows) * (0.6 + 0.4 * fbm(h, w, 3, seed + 3))
        t.paint(m, hexc(ink), 0.9)
        return t
    return f


def g_crate_stencil(text, ink="3a2a1c"):
    """A pine crate side board with a stencilled origin."""
    def f(w, h, seed):
        t = va.g_wood(w, h, seed, base="c9a06a")
        m = text_mask(w, h, [(text, "oswald", fit_size(text, "oswald", h * 0.5, 600, w * 0.8), 600, (w / 2, h * 0.52), "mm")])
        t.paint(m * (0.55 + 0.45 * noise(h, w, 2, seed)), hexc(ink), 0.85)
        return t
    return f


def g_menu(title, items, foot=None, doodle=None):
    """A small chalk menu board with baked lettering (deco stalls have no write_ faces)."""
    def f(w, h, seed):
        t = Tex(w, h, hexc("23282a"), 0.88)
        t.col = mix(t.col, np.array(hexc("4a5152")), smooth(0.45, 0.8, fbm(h, w, 40, seed)) * 0.5)
        rows = [(title, "caveat", fit_size(title, "caveat", h * 0.16, 700, w * 0.85), 700, (w / 2, h * 0.13), "mm")]
        n = len(items)
        for k, (a, b) in enumerate(items):
            y = h * (0.32 + k * (0.52 / max(1, n - 1) if n > 1 else 0))
            rows.append((a, "caveat", fit_size(a, "caveat", h * 0.105, 600, w * 0.62), 600, (w * 0.07, y), "lm"))
            rows.append((b, "caveat", h * 0.105, 600, (w * 0.93, y), "rm"))
        if foot:
            rows.append((foot, "caveat", fit_size(foot, "caveat", h * 0.08, 500, w * 0.8), 500, (w / 2, h * 0.93), "mm"))
        grain = 0.55 + 0.45 * fbm(h, w, 1.5, seed + 5)
        t.paint(text_mask(w, h, rows) * grain, hexc("eeeae0"), 0.95, height=0.2)
        if doodle:
            t.paint(shape_mask(w, h, lambda d, s: d.line([(w * 0.25 * s, h * 0.21 * s), (w * 0.75 * s, h * 0.205 * s)],
                                                         fill=255, width=int(2 * s))) * grain, hexc(doodle), 0.95)
        return t
    return f


def g_cheese_labels(w, h, seed):
    """Four round paper labels (a 4 x 1 strip) for the cheese wheels' tops."""
    t = Tex(w, h, hexc("f1e6c8"), 0.7)
    names = [("Bergkäse", "Allgäu", "2a5a2a"), ("Emmentaler", "Allgäu", "a8161d"),
             ("Tilsiter", "würzig", "1d3a78"), ("Rahmkäse", "mild", "8a5a1a")]
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    rows = []
    for i, (a, b, c) in enumerate(names):
        cx, cy = (i + 0.5) * w / 4, h / 2
        r = np.hypot(xx - cx, yy - cy) / (h / 2)
        t.paint(smooth(0.96, 0.92, r) * smooth(0.0, 0.0001, 1), hexc("f1e6c8"), 0.7)
        t.paint((smooth(0.86, 0.83, r) - smooth(0.78, 0.75, r)).clip(0, 1), hexc(c), 0.6)
        t.paint(smooth(1.0, 0.97, r) * (r > 0.97), hexc("c8b890"), 0.7)
        rows.append((a, "fell", fit_size(a, "fell", h * 0.2, None, w / 4 * 0.62), None, (cx, cy - h * 0.04), "mm"))
        rows.append((b, "garamond", h * 0.12, 500, (cx, cy + h * 0.17), "mm"))
    t.paint(text_mask(w, h, rows), hexc("2a1a10"), 0.6)
    return t


# ------------------------------------------------------------------ glass baubles (u round, v from foot to cap)
BAUBLES = [  # (name, base, paint, kind, finish)   finish: gloss | matte | mirror
    ("bauble_0", "a8161d", "d8b048", "band_stars", "gloss"),
    ("bauble_1", "d8b048", "a8161d", "dots", "mirror"),
    ("bauble_2", "1d3a78", "e8ecf0", "snowflakes", "gloss"),
    ("bauble_3", "eeeae2", "d8b048", "stripes", "matte"),
    ("bauble_4", "1f5a3a", "f2ead8", "swirl", "gloss"),
    ("bauble_5", "6a1f52", "d8b048", "lattice", "gloss"),
    ("bauble_6", "c8ccd0", "8a8e92", "hammered", "mirror"),
    ("bauble_7", "d8782a", "f6efe0", "zigzag", "gloss"),
    ("bauble_8", "b01e24", "f6efe0", "text", "matte"),
    ("bauble_9", "8ab8d8", "f6f6f2", "firs", "matte"),
    ("bauble_10", "e8a0b0", "d8b048", "lattice", "matte"),
    ("bauble_11", "1e6a6a", "c87a3a", "band_stars", "gloss"),
    ("bauble_12", "d8b048", "d8b048", "hammered", "mirror"),
    ("bauble_13", "f2f0ea", "b01e24", "hearts", "matte"),
    ("bauble_14", "2a2a5a", "d8b048", "comet", "gloss"),
    ("bauble_15", "a8161d", "e8ecf0", "glitter", "matte"),
]
BAUBLE_LABELS = {
    "band_stars": "a band of painted stars", "dots": "painted dots", "snowflakes": "white snowflakes",
    "stripes": "gold stripes", "swirl": "a white swirl", "lattice": "a gold lattice", "hammered": "a hammered mirror finish",
    "zigzag": "a white zigzag", "text": "“Frohe Weihnachten” in white script", "firs": "a winter forest band",
    "hearts": "little red hearts", "comet": "a gold comet", "glitter": "a frosted glitter band",
}


def g_bauble(base, paint, kind, finish):
    def f(w, h, seed):
        rough = {"gloss": 0.08, "matte": 0.42, "mirror": 0.06}[finish]
        metal = 1.0 if finish == "mirror" else 0.0
        t = Tex(w, h, hexc(base), rough, metal)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        v = 1 - yy / (h - 1)            # 0 at the foot, 1 at the cap
        u = xx / w
        t.col = mix(t.col, t.col * 0.82, fbm(h, w, 14, seed) * 0.25)
        pc = hexc(paint)
        pm = 0.9 if paint in ("d8b048", "c87a3a") else 0.0
        pr = 0.3 if pm else 0.45
        m = np.zeros((h, w))
        if kind == "band_stars" or kind == "comet":
            band = smooth(0.06, 0.03, np.abs(v - 0.62)) + smooth(0.06, 0.03, np.abs(v - 0.38))
            m = np.maximum(m, band.clip(0, 1) * (kind == "band_stars"))

            def st(d, s):
                n = 6 if kind == "band_stars" else 2
                for i in range(n):
                    cx, cy = (i + 0.5) * w / n, h * 0.5
                    rr = 7 if kind == "band_stars" else 9
                    pts = [(cx + (rr if k % 2 == 0 else rr * 0.42) * math.cos(-math.pi / 2 + math.pi * k / 5),
                            cy + (rr if k % 2 == 0 else rr * 0.42) * math.sin(-math.pi / 2 + math.pi * k / 5)) for k in range(10)]
                    d.polygon([(x * s, y * s) for x, y in pts], fill=255)
                    if kind == "comet":
                        d.line([((cx - 2) * s, cy * s), ((cx - 28) * s, (cy + 8) * s)], fill=255, width=int(2 * s))
            m = np.maximum(m, shape_mask(w, h, st))
        elif kind == "dots":
            m = shape_mask(w, h, lambda d, s: [d.ellipse([((i + 0.5 * (j % 2)) * w / 8 - 3) * s, ((j + 0.5) * h / 5 - 3) * s,
                                                          ((i + 0.5 * (j % 2)) * w / 8 + 3) * s, ((j + 0.5) * h / 5 + 3) * s], fill=255)
                                               for i in range(9) for j in range(1, 4)])
        elif kind == "snowflakes":
            def sf(d, s):
                for i in range(5):
                    for j, cy in enumerate((h * 0.32, h * 0.66)):
                        cx = (i + 0.5 + 0.5 * j) * w / 5 % w
                        for k in range(3):
                            a = math.pi * k / 3
                            d.line([((cx - 7 * math.cos(a)) * s, (cy - 7 * math.sin(a)) * s),
                                    ((cx + 7 * math.cos(a)) * s, (cy + 7 * math.sin(a)) * s)], fill=255, width=int(1.4 * s))
            m = shape_mask(w, h, sf)
        elif kind == "stripes":
            m = (smooth(0.03, 0.015, np.abs(((u * 8) % 1) - 0.5) - 0.42) * (v > 0.1) * (v < 0.9))
            m = np.maximum(m, smooth(0.03, 0.01, np.abs(v - 0.5)))
        elif kind == "swirl":
            m = smooth(0.08, 0.04, np.abs(((u * 3 + v * 1.4) % 1) - 0.5)) * (v > 0.12) * (v < 0.88)
        elif kind == "lattice":
            a = smooth(0.06, 0.02, np.abs(((u * 6 + v * 3) % 1) - 0.5))
            b = smooth(0.06, 0.02, np.abs(((u * 6 - v * 3) % 1) - 0.5))
            m = np.maximum(a, b) * (v > 0.1) * (v < 0.9)
        elif kind == "hammered":
            d1, d21, _ = va.voronoi(h, w, int(w * h / 40), seed, periodic_x=True)
            t.height = smooth(0, 3, d21) * 0.6
            t.col = mix(t.col, t.col * 1.15, smooth(2, 0, d21) * 0.4).clip(0, 1)
        elif kind == "zigzag":
            m = smooth(0.035, 0.015, np.abs(v - 0.5 - 0.1 * (np.abs(((u * 8) % 1) - 0.5) * 2 - 0.5)))
            m = np.maximum(m, smooth(0.025, 0.01, np.abs(v - 0.32)) + smooth(0.025, 0.01, np.abs(v - 0.68)))
        elif kind == "text":
            m = text_mask(w, h, [("Frohe Weihnachten", "pacifico", fit_size("Frohe Weihnachten", "pacifico", h * 0.2, None, w * 0.92),
                                  None, (w / 2, h * 0.5), "mm")])
            m = np.maximum(m, smooth(0.02, 0.008, np.abs(v - 0.3)) + smooth(0.02, 0.008, np.abs(v - 0.7)))
        elif kind == "firs":
            def fr(d, s):
                for i in range(10):
                    cx = (i + 0.5) * w / 10
                    hh = 12 + 6 * ((i * 7) % 3)
                    d.polygon([((cx - 5) * s, h * 0.6 * s), ((cx + 5) * s, h * 0.6 * s), (cx * s, (h * 0.6 - hh) * s)], fill=255)
                d.rectangle([0, h * 0.6 * s, w * s, h * 0.64 * s], fill=255)
            m = shape_mask(w, h, fr)
        elif kind == "hearts":
            def hr(d, s):
                for i in range(7):
                    for j, cy in enumerate((h * 0.35, h * 0.65)):
                        cx = (i + 0.5 * j) * w / 7 + 4
                        d.ellipse([(cx - 4) * s, (cy - 3) * s, cx * s, (cy + 1) * s], fill=255)
                        d.ellipse([cx * s, (cy - 3) * s, (cx + 4) * s, (cy + 1) * s], fill=255)
                        d.polygon([((cx - 4) * s, (cy - 0.5) * s), ((cx + 4) * s, (cy - 0.5) * s), (cx * s, (cy + 5) * s)], fill=255)
            m = shape_mask(w, h, hr)
        elif kind == "glitter":
            band = smooth(0.14, 0.08, np.abs(v - 0.5))
            sp = (np.random.default_rng(seed).random((h, w)) > 0.7) * band
            m = np.clip(band * 0.6 + sp * 0.4, 0, 1)
            t.paint(band, pc, 0.7)
            t.height = t.height + sp * 0.4
        t.paint(m, pc, pr, pm, height=0.25)
        # the pole near the cap: a little silvering where the glass meets the cap
        t.paint(smooth(0.9, 0.97, v), hexc("e8e4d8"), 0.15, 0.6)
        t.hscale = 0.6
        return t
    return f


# ------------------------------------------------------------------ figure ornaments and faces
def g_pickle(w, h, seed):
    """The Weihnachtsgurke: green glass, warty, a lighter belly and a dusting of glitter."""
    t = Tex(w, h, hexc("3f7a2a"), 0.1)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    d1, d21, _ = va.voronoi(h, w, int(w * h / 26), seed, periodic_x=True)
    bump = np.clip(1 - d1 / 3.2, 0, 1)
    t.height = bump * 1.0
    t.col = mix(t.col, np.array(hexc("8ab84a")), bump * 0.45 + smooth(0.6, 0.9, fbm(h, w, 20, seed)) * 0.2)
    t.col = mix(t.col, np.array(hexc("1f4a18")), smooth(0.4, 0.0, np.abs(xx / w - 0.5) * 2) * 0.0 + (1 - bump) * 0.25)
    sp = (np.random.default_rng(seed).random((h, w)) > 0.985).astype(float)
    t.paint(sp, hexc("e8f0c0"), 0.1, 0.6)
    t.hscale = 0.9
    return t


def g_pinecone(w, h, seed):
    """Glass pine cone: overlapping brown scales with frosted, gilded tips (u round, v up)."""
    t = Tex(w, h, hexc("6a3a1a"), 0.25)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    rows = 10
    v = yy / h * rows
    u = xx / w * 8 + (np.floor(v) % 2) * 0.5
    fu, fv = (u % 1) - 0.5, v % 1
    scale = np.clip(1 - (fu ** 2 * 3 + (fv - 0.15) ** 2 * 1.5), 0, 1)
    t.height = scale * 1.2
    t.col = mix(t.col, np.array(hexc("a8622a")), scale * 0.6)
    t.paint(smooth(0.25, 0.08, fv) * scale, hexc("e8d8a0"), 0.3, 0.7)
    return t


def g_bird(w, h, seed):
    """Clip-on bird (u round the body, v from tail to beak): blue back, white breast, painted wing."""
    t = Tex(w, h, hexc("2a5aa8"), 0.15)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    u, v = xx / w, 1 - yy / h
    breast = smooth(0.18, 0.1, np.abs(u - 0.5))
    t.paint(breast, hexc("f4efe4"), 0.2)
    t.paint(smooth(0.05, 0.02, np.abs(v - 0.55) + np.abs(np.abs(u - 0.5) - 0.3) * 0.5), hexc("d8b048"), 0.25, 0.9)
    t.paint(smooth(0.035, 0.015, np.hypot(np.abs(u - 0.5) - 0.12, v - 0.86)), hexc("101010"), 0.2)
    t.paint(smooth(0.86, 0.95, v), hexc("e0a030"), 0.3)
    sp = (np.random.default_rng(seed).random((h, w)) > 0.97) * smooth(0.6, 0.3, v)
    t.paint(sp, hexc("e8ecf0"), 0.2, 0.5)
    return t


def g_mushroom(w, h, seed):
    """Fly agaric cap seen from above (planar): red with white spots and a lighter rim."""
    t = Tex(w, h, hexc("c01a1a"), 0.12)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
    rng = np.random.default_rng(seed)
    spots = np.zeros((h, w))
    for _ in range(14):
        a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0.05, 0.8)
        cx, cy, s = w / 2 + rr * w / 2 * math.cos(a), h / 2 + rr * h / 2 * math.sin(a), rng.uniform(2.5, 4.5)
        spots = np.maximum(spots, smooth(s, s * 0.6, np.hypot(xx - cx, yy - cy)))
    t.paint(spots, hexc("f6f2ea"), 0.4, height=0.8)
    t.paint(smooth(0.85, 1.0, r), hexc("f0e8d8"), 0.4)
    return t


def g_herrnhut(w, h, seed):
    """Herrnhut star paper: a red paper point with ribbed creases and a lighter edge (planar on each cone)."""
    t = Tex(w, h, hexc("d8382a"), 0.7)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, np.array(hexc("f2a080")), smooth(0.4, 1.0, fbm(h, w, 12, seed)) * 0.25)
    t.height = np.sin(xx / w * math.pi * 6) * 0.3
    t.paint(smooth(h * 0.08, 0, yy), hexc("f4e2c0"), 0.7)
    return t


def g_smoker_face(w, h, seed):
    """Räuchermännchen face (planar): painted skin, round black eyes, rosy cheeks, the round mouth hole."""
    t = va.g_toy_face(w, h, seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.paint(smooth(5.5, 3.5, np.hypot(xx - w / 2, yy - h * 0.62)), hexc("2a1a10"), 0.6, height=-1.0)
    return t


def g_angel(w, h, seed):
    """Erzgebirge angel's face and gown front (planar): rosy face, golden hair, white gown with gold dots."""
    t = Tex(w, h, hexc("f6f2ea"), 0.3)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.paint(smooth(h * 0.33, h * 0.3, yy), hexc("f0c8a0"), 0.35)
    t.paint(smooth(h * 0.12, h * 0.1, yy) + smooth(4, 2, np.abs(xx - w * 0.2)) * (yy < h * 0.32), hexc("d8a838"), 0.4)
    t.paint(smooth(2.5, 1.2, np.hypot(xx - w * 0.38, yy - h * 0.2)) + smooth(2.5, 1.2, np.hypot(xx - w * 0.62, yy - h * 0.2)),
            hexc("1a1410"), 0.3)
    t.paint(smooth(4, 2, np.hypot(xx - w * 0.3, yy - h * 0.26)) * 0.5 + smooth(4, 2, np.hypot(xx - w * 0.7, yy - h * 0.26)) * 0.5,
            hexc("e07070"), 0.35)
    dots = shape_mask(w, h, lambda d, s: [d.ellipse([((i + 0.5) * w / 5 - 1.5) * s, ((j + 0.5) * h / 10 + h * 0.4 - 1.5) * s,
                                                     ((i + 0.5) * w / 5 + 1.5) * s, ((j + 0.5) * h / 10 + h * 0.4 + 1.5) * s],
                                                    fill=255) for i in range(5) for j in range(6)])
    t.paint(dots, hexc("d8b048"), 0.3, 0.9)
    return t


def g_toy_paint(w, h, seed):
    """Painted turned-wood toy colours: eight vertical colour bands (u picks the colour), glossy lacquer over grain."""
    t = va.g_wood(w, h, seed, base="d8b07a")
    cols = ["b0282a", "2a6a3a", "1f3a78", "d8b048", "f2ead8", "1a1a1a", "c0562a", "5a8ab0"]
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    for i, c in enumerate(cols):
        band = ((xx >= i * w / 8) & (xx < (i + 1) * w / 8)).astype(float)
        t.paint(band * 0.88, hexc(c), 0.25)
    return t


def g_cinnamon_bag(w, h, seed):
    """A striped paper bag print (Mandeln stall): red stripes, a white oval with 'Mandeln'."""
    t = va.g_paper(w, h, seed, grease=False)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.paint(((xx // 10) % 2 == 0).astype(float) * 0.85, hexc("b0282a"), 0.8)
    r = np.hypot((xx - w / 2) / (w * 0.36), (yy - h * 0.5) / (h * 0.2))
    t.paint(smooth(1.0, 0.95, r), hexc("f6f0e2"), 0.8)
    t.paint(text_mask(w, h, [("Gebrannte", "fraktur", h * 0.09, None, (w / 2, h * 0.45), "mm"),
                             ("Mandeln", "fraktur", h * 0.12, None, (w / 2, h * 0.56), "mm")]), hexc("7a1a14"), 0.8)
    return t


def g_garland(w, h, seed):
    """Fir garland needles (u along the garland, v round it)."""
    t = Tex(w, h, hexc("1f4a2a"), 0.6)
    rng = np.random.default_rng(seed)
    n = ndimage_filter(rng.random((h, w)))
    t.col = mix(t.col, np.array(hexc("3a6a3a")), n * 0.7)
    t.height = n * 0.8
    return t


def ndimage_filter(a):
    from scipy import ndimage
    return np.clip(ndimage.uniform_filter1d(a, 5, axis=0) * 1.6 - 0.3, 0, 1)


# ------------------------------------------------------------------ region list
def specs():
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    # jar and bottle labels (128 x 80)
    for n, a, b, bg, ink, acc in (
            ("lb_honey", "Waldhonig", "aus dem Erzgebirge", "f2e4b8", "4a2a0a", "c8902a"),
            ("lb_kirsch", "Kirsch", "Konfitüre extra", "f4ece0", "7a1018", "a8161d"),
            ("lb_pflaume", "Pflaumenmus", "nach Omas Art", "efe6d4", "3a1a4a", "6a2a6a"),
            ("lb_apfel", "Apfelmus", "hausgemacht", "f4efe0", "3a4a1a", "6a8a2a"),
            ("lb_mandel", "Zuckermandeln", "250 g", "f6efe2", "6a1a12", "b0282a"),
            ("lb_nougat", "Nuss-Nougat", "Creme", "efe2c8", "3a1a0a", "8a5a2a"),
            ("lb_zucker", "Zucker & Zimt", "zum Bestreuen", "f4f0e6", "5a3a1a", "c87a3a"),
            ("lb_oel", "Rapsöl", "kaltgepresst", "f2eccc", "4a4a10", "8a8a20"),
            ("lb_senf", "Feigensenf", "zum Käse", "f2e8c8", "4a3010", "b8862a"),
            ("lb_wachs", "Bienenwachs", "100 % rein", "f2e2b0", "5a3a0a", "c8902a"),
            ("lb_lavendel", "Lavendel", "Duftkerze", "ece6f2", "4a2a6a", "7a5aa8"),
            ("lb_tanne", "Tanne", "Duftkerze", "e6efe4", "1f4a2a", "2a6a3a")):
        add(n, 128, 80, g_label(a, b, bg, ink, accent=acc))
    # printed cartons (192 x 128)
    for n, a, b, bg, ink, gold, motif in (
            ("bx_lebkuchen", "Elisen-Lebkuchen", "Nürnberger Art · 200 g", "8e1b1d", "f6e8c0", "d8b048", "stars"),
            ("bx_printen", "Aachener Printen", "Kräuterprinten · 250 g", "1f3a5a", "f2ead8", "d8b048", "dots"),
            ("bx_kerzen", "Christbaumkerzen", "20 Stück · Bienenwachs", "f2ead8", "8e1b1d", "b8902a", "stars"),
            ("bx_baukasten", "Holzbaukasten", "Erzgebirge · 48 Steine", "2a5a8a", "f6efe0", "d8b048", "dots"),
            ("bx_puzzle", "Holzpuzzle", "Bauernhof · ab 3 Jahren", "2a6a3a", "f6efe0", "e8c860", "hearts"),
            ("bx_schmuck", "Christbaumschmuck", "Lauscha · mundgeblasen", "5a1a2a", "f6e8c0", "d8b048", "stars"),
            ("bx_kaese", "Käse-Präsent", "Allgäuer Auslese", "f2e8c8", "2a4a2a", "8a6a2a", "dots"),
            ("bx_mandeln", "Mandel-Präsent", "gebrannt & gezuckert", "6a1a14", "f6e8c0", "d8b048", "hearts")):
        add(n, 192, 128, g_box(a, b, bg, ink, gold, motif=motif))
    # sacks and crate boards
    add("sk_kartoffeln", 160, 160, g_sack("Kartoffeln", "festkochend · Linda"))
    add("sk_maronen", 160, 160, g_sack("Maronen", "aus dem Piemont"))
    add("sk_mehl", 160, 160, g_sack("Weizenmehl", "Type 405 · 25 kg", base="e8e0cc", ink="2a3a6a"))
    add("sk_mandeln", 160, 160, g_sack("Mandeln", "Kalifornien · roh"))
    for n, txt in (("cr_allgaeu", "ALLGÄU"), ("cr_erzgebirge", "ERZGEBIRGE"), ("cr_pfalz", "PFALZ"),
                   ("cr_lauscha", "LAUSCHA"), ("cr_markt", "NACHTMARKT")):
        add(n, 256, 64, g_crate_stencil(txt))
    # chalk menu boards (256 x 192)
    add("mn_crepes", 256, 192, g_menu("Crêpes", [("Zucker & Zimt", "3,00"), ("Nuss-Nougat", "3,50"), ("Apfelmus", "3,50"),
                                                ("Zitrone & Zucker", "3,00"), ("Grand Marnier", "4,50")], "frisch gebacken!", "f2b8c0"))
    add("mn_puffer", 256, 192, g_menu("Kartoffelpuffer", [("3 Puffer, Apfelmus", "5,00"), ("3 Puffer, Lachs", "7,50"),
                                                         ("mit Kräuterquark", "6,00"), ("Apfelmus extra", "1,00")], "wie bei Oma", "f2d880"))
    add("mn_maroni", 256, 192, g_menu("Heiße Maroni", [("kleine Tüte", "3,50"), ("große Tüte", "6,00"),
                                                      ("Maronen roh, 500 g", "4,00")], "frisch geröstet", "f2b8a0"))
    add("mn_mandeln", 256, 192, g_menu("Gebrannte Mandeln", [("100 g", "3,50"), ("200 g", "6,00"), ("Zimtmandeln", "3,80"),
                                                            ("Cashews", "4,20")], "noch warm!", "f2d880"))
    add("mn_kaese", 256, 192, g_menu("Käse", [("Bergkäse 100 g", "3,50"), ("Emmentaler", "2,90"), ("Tilsiter", "2,60"),
                                             ("Raclette-Brot", "6,50")], "zum Probieren", "f2e0a0"))
    add("mn_kerzen", 256, 192, g_menu("Kerzen", [("Bienenwachs", "ab 4,00"), ("Kerzenziehen", "2,00"),
                                                ("Duftkerzen", "6,50")], "handgezogen", "f2c880"))
    add("mn_lebkuchen", 256, 192, g_menu("Lebkuchen", [("Herz, klein", "3,00"), ("Herz, groß", "6,00"),
                                                      ("Elisen, 200 g", "7,50"), ("Pfeffernüsse", "3,50")], "frisch aus Nürnberg", "f2b8c0"))
    add("mn_spielzeug", 256, 192, g_menu("Holzspielzeug", [("Kreisel", "4,00"), ("Nussknacker", "ab 29,00"),
                                                          ("Eisenbahn", "24,00"), ("Bauklötze", "18,00")], "aus dem Erzgebirge", "a8d0f0"))
    add("mn_schmuck", 256, 192, g_menu("Schmuck", [("Glaskugel", "ab 5,00"), ("Strohstern", "1,50"),
                                                  ("Herrnhuter Stern", "29,00"), ("Gurke", "6,00")], "mundgeblasen in Lauscha", "f2d880"))
    add("cheese_labels", 256, 64, g_cheese_labels)
    # baubles: one wrap each
    for n, base, paint, kind, finish in BAUBLES:
        add(n, 128, 64, g_bauble(base, paint, kind, finish))
    add("pickle", 64, 128, g_pickle)
    add("pinecone", 64, 128, g_pinecone)
    add("bird", 128, 64, g_bird)
    add("mushroom", 64, 64, g_mushroom)
    add("herrnhut", 64, 64, g_herrnhut)
    add("smoker_face", 64, 64, g_smoker_face)
    add("angel", 64, 96, g_angel)
    add("toy_paint", 256, 64, g_toy_paint)
    add("bag_mandeln", 128, 160, g_cinnamon_bag)
    add("garland", 128, 64, g_garland)
    return R


def build(out=OUT):
    os.makedirs(out, exist_ok=True)
    sp = specs()
    regions, used = va._render_atlas(sp, SIZE, "market", out)
    meta = {"size": SIZE, "used_rows_px": used, "regions": regions,
            "baubles": {n: {"base": b, "paint": p, "kind": k, "finish": f} for n, b, p, k, f in BAUBLES}}
    with open(META, "w") as f:
        json.dump(meta, f, indent=0)
    print(f"[market atlas] {len(regions)} regions, {used}px of {SIZE} -> {out}")
    return meta


def load():
    if not os.path.exists(META):
        return build()
    with open(META) as f:
        return json.load(f)


if __name__ == "__main__":
    build()
