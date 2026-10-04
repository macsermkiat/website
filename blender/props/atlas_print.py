"""Round 6 print atlas: everything printed around the market's writing surfaces (docs/adr/0003).

    python3 blender/props/atlas_print.py      # blender/out/vendor/print_{color,rm,normal}.png + print_regions.json

Plain numpy + PIL, like vendor_atlas.py, and shipped once as prop_tex_print_*.webp. A separate atlas, so the
main and books atlases (and every set that uses them) keep their packing.

Regions (all names start with "pr_"):
    pr_coaster_front_<cw>, pr_coaster_back_<cw>   Bierdeckel faces, one per colourway (content_projects.COLOURWAYS):
                       printed rim band with lettering, the Nachtmarkt-Bräu brewer's star, blank card in the
                       middle (the write_ face covers the writing rectangle; the ring mesh maps the rest)
    pr_coaster_edge    the grey board edge of a coaster
    pr_marktblatt      the printed market paper the Bratwurst is wrapped in: masthead, border of stars, firs and
                       stalls, blank middle for the write_writing_paper face
    pr_back_<label>    a back label for each wine (atlas_goods.WINE_LABELS keys): estate, small print, blank
                       middle for write_label_<n>
    pr_cloth, pr_paper, pr_page_edge, pr_headband, pr_ribbon   the open hardback (book_open.glb)

The blank middles are the same colour as the plain write_ materials (WRITE_COLOURS), so the seam between the
printed ring and the writing face does not show.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import vendor_atlas as va  # noqa: E402
from vendor_atlas import Tex, fbm, hexc, mix, shape_mask, smooth, text_mask, fit_size  # noqa: E402
import atlas_goods  # noqa: E402
import atlas_books  # noqa: E402
import content_projects  # noqa: E402

OUT = va.OUT
SIZE = 2048

# sRGB colours of the plain writing faces (vlib uses the same values for the write_ materials)
WRITE_COLOURS = {"card": "f1eadb", "paper": "efe7d4", "label": "f5f0e3", "page": "f0e8d4"}

# coaster colourways: (band colour, lettering on the band, thin rules and the star on the card)
COASTER_INKS = {
    "gold": ("c99a22", "3a220e", "8a5e12"),
    "brown": ("4e2814", "f1e2c0", "4e2814"),
    "green": ("1f4a33", "efe4c4", "1f4a33"),
    "blue": ("1d4d8f", "f1ead6", "1d4d8f"),
    "red": ("a3201c", "f6ecd6", "a3201c"),
}

# coaster geometry (mm, coaster 107 mm across) shared with set_bier
COASTER_D = 107.0
BAND_OUT, BAND_IN, RULE_R = 51.5, 40.0, 38.0       # rim band radii and the thin rule inside it
FRONT_RECT = (60.0, 44.0)                           # writing rectangle on the front (w, h)
BACK_RULES = (51.0, 49.2)
BACK_RECT = (70.0, 62.0)

# alcohol, volume for the back labels
WINE_SMALL = {
    "wl_riesling_mosel": ("10,5", "0,75 l"), "wl_riesling_rheingau": ("9,0", "0,75 l"),
    "wl_riesling_pfalz": ("12,0", "0,75 l"), "wl_spaet_baden": ("13,5", "0,75 l"), "wl_spaet_ahr": ("13,0", "0,75 l"),
    "wl_dornfelder_rh": ("11,5", "0,75 l"), "wl_dornfelder_pfalz": ("12,5", "0,75 l"),
    "wl_silvaner_franken": ("12,5", "0,75 l"), "wl_silvaner_rh": ("12,0", "0,75 l"),
    "wl_riesling_eiswein": ("7,5", "0,375 l"), "wl_weissherbst_baden": ("12,0", "0,75 l"),
    "wl_riesling_nahe": ("8,5", "0,75 l"),
}
# the back label's writing area as a fraction of the label (u0, v0, u1, v1), v up; set_gluehwein maps the same
BACK_LABEL_WRITE = (0.1, 0.2, 0.9, 0.76)
# the Marktblatt's writing area (fraction of the sheet, v up)
MARKTBLATT_WRITE = (0.11, 0.1, 0.89, 0.72)


def arc_text(w, h, text, fn, size, wght, cx, cy, R, top=True, ss=3, spacing=1.0):
    """Text along a circle of radius R (px) round (cx, cy): on the top arc reading clockwise with the letters'
    feet toward the centre, on the bottom arc reading left to right with their heads toward the centre."""
    im = Image.new("L", (w * ss, h * ss), 0)
    f = va.font(fn, size * ss, wght)
    widths = [f.getlength(c) * spacing for c in text]
    tot = sum(widths)
    Rs = R * ss
    ang_tot = tot / Rs
    a = (-math.pi / 2 - ang_tot / 2) if top else (math.pi / 2 + ang_tot / 2)
    for c, cw in zip(text, widths):
        da = cw / Rs
        mid = a + (da / 2 if top else -da / 2)
        g = Image.new("L", (int(size * ss * 2), int(size * ss * 2)), 0)
        ImageDraw.Draw(g).text((g.width / 2, g.height / 2), c, fill=255, font=f, anchor="mm")
        rot = -math.degrees(mid + math.pi / 2) if top else -math.degrees(mid - math.pi / 2)
        g = g.rotate(rot, resample=Image.BICUBIC)
        px = cx * ss + Rs * math.cos(mid) - g.width / 2
        py = cy * ss + Rs * math.sin(mid) - g.height / 2
        im.paste(255, (int(px), int(py)), g)
        a += da if top else -da
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, float) / 255.0


def brewer_star(d, ss, cx, cy, R, width):
    """The brewer's star (Brauerstern / Zoiglstern): two interlaced triangles, outlined."""
    for rot in (-math.pi / 2, math.pi / 2):
        pts = [((cx + R * math.cos(rot + k * 2 * math.pi / 3)) * ss, (cy + R * math.sin(rot + k * 2 * math.pi / 3)) * ss)
               for k in range(3)]
        d.line(pts + [pts[0]], fill=255, width=max(1, int(width * ss)), joint="curve")


def card_base(w, h, seed, col):
    t = Tex(w, h, hexc(col), 0.92)
    t.col = mix(t.col, t.col * 0.93, fbm(h, w, 14, seed) * 0.5)          # pressed pulp board mottling
    rng = np.random.default_rng(seed)
    fib = rng.random((h, w))
    t.col = mix(t.col, t.col * 0.9, (fib > 0.985) * 0.6)                 # specks of fibre
    t.height = fbm(h, w, 2.5, seed + 1) * 0.35
    return t


def g_coaster_front(cw):
    band, letter, rule = (hexc(c) for c in COASTER_INKS[cw])

    def f(w, h, seed):
        t = card_base(w, h, seed, WRITE_COLOURS["card"])
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        px = w / COASTER_D
        cx, cy = w / 2, h / 2
        r = np.hypot(xx - cx, yy - cy) / px                              # mm from the centre
        aa = 0.8 / px
        ring = smooth(BAND_OUT + aa, BAND_OUT - aa, r) * smooth(BAND_IN - aa, BAND_IN + aa, r)
        # the print has a slightly uneven ink lay-down
        ink_var = 0.88 + 0.12 * fbm(h, w, 10, seed + 4)
        t.paint(ring * ink_var, band, 0.75, height=0.08)
        t.paint(smooth(0.45, 0.0, np.abs(r - RULE_R) - 0.3) * 0.95, rule, 0.75)
        t.paint(smooth(0.35, 0.0, np.abs(r - (BAND_OUT + 0.9)) - 0.15) * 0.8, band, 0.75)
        Rt = (BAND_OUT + BAND_IN) / 2 * px
        sz = (BAND_OUT - BAND_IN) * px * 0.62
        lt = arc_text(w, h, "NACHTMARKT-BRÄU", "oswald", sz, 600, cx, cy, Rt - sz * 0.02, top=True, spacing=1.12)
        lb = arc_text(w, h, "· FRISCH VOM FASS ·", "oswald", sz * 0.82, 500, cx, cy, Rt + sz * 0.05, top=False,
                      spacing=1.1)
        t.paint((lt + lb).clip(0, 1) * 0.97, letter, 0.7)
        # two small stars on the band where the lettering stops
        def stars(d, ss):
            for side in (-1, 1):
                a = math.pi * (0.06 if side > 0 else 0.94)
                x, y = cx + Rt * math.cos(a), cy + Rt * math.sin(a) * -1
                for k in range(10):
                    pass
                pts = [((x + (sz * 0.32 if k % 2 == 0 else sz * 0.13) * math.cos(-math.pi / 2 + k * math.pi / 5)) * ss,
                        (y + (sz * 0.32 if k % 2 == 0 else sz * 0.13) * math.sin(-math.pi / 2 + k * math.pi / 5)) * ss)
                       for k in range(10)]
                d.polygon(pts, fill=255)
        t.paint(shape_mask(w, h, stars), letter, 0.7)
        # the brewery mark above the writing rectangle: a brewer's star with an N inside, a line under the rect
        ry = FRONT_RECT[1] / 2
        my = cy - (ry + (RULE_R - ry) * 0.5) * px
        sr = (RULE_R - ry) * 0.36 * px
        t.paint(shape_mask(w, h, lambda d, ss: brewer_star(d, ss, cx, my, sr, 1.6)), rule, 0.7)
        t.paint(text_mask(w, h, [("N", "fraktur", sr * 0.95, None, (cx, my + sr * 0.04), "mm")]), rule, 0.7)
        by = cy + (ry + (RULE_R - ry) * 0.42) * px
        t.paint(text_mask(w, h, [("seit dem ersten Advent", "fell", (RULE_R - ry) * px * 0.3, None, (cx, by), "mm")]),
                rule, 0.7)
        # a faint old beer ring on the band side, and soft wear at the very edge
        ring2 = smooth(1.2, 0.0, np.abs(np.hypot(xx - cx * 1.18, yy - cy * 0.86) / px - 33.0)) * \
            smooth(0.4, 0.8, fbm(h, w, 12, seed + 7))
        t.col = mix(t.col, t.col * np.array([0.86, 0.8, 0.68]), ring2 * 0.35 * (r > RULE_R))
        t.col = mix(t.col, t.col * 0.85, smooth(52.3, 53.5, r))
        return t
    return f


def g_coaster_back(cw):
    band, letter, rule = (hexc(c) for c in COASTER_INKS[cw])

    def f(w, h, seed):
        t = card_base(w, h, seed + 3, WRITE_COLOURS["card"])
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        px = w / COASTER_D
        cx, cy = w / 2, h / 2
        r = np.hypot(xx - cx, yy - cy) / px
        for R0, wd in ((BACK_RULES[0], 0.45), (BACK_RULES[1], 0.22)):
            t.paint(smooth(wd + 0.35, wd - 0.05, np.abs(r - R0)) * 0.95, rule, 0.75)
        t.col = mix(t.col, t.col * 0.85, smooth(52.3, 53.5, r))
        return t
    return f


def g_coaster_edge(w, h, seed):
    t = Tex(w, h, hexc("cfc6b4"), 0.95)
    t.col = mix(t.col, np.array(hexc("a89f8c")), fbm(h, w, 3, seed) * 0.5)
    rng = np.random.default_rng(seed)
    layers = np.repeat(rng.random((h, 1)), w, 1)
    t.col = mix(t.col, t.col * 0.85, (layers > 0.7) * 0.4)
    t.height = layers * 0.2
    return t


def g_marktblatt(w, h, seed):
    """Market paper (Marktblatt): off-white greaseproof sheet printed in brick red, a masthead across the top,
    a border of stars, firs and little stalls, and a blank middle where the engine prints the piece."""
    t = Tex(w, h, hexc(WRITE_COLOURS["paper"]), 0.6)
    t.col = mix(t.col, t.col * 0.94, fbm(h, w, 30, seed) * 0.5)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    ink = hexc("a8322a")
    u0, v0, u1, v1 = MARKTBLATT_WRITE
    # double frame inside the margins
    def frame(d, ss):
        for ins, wd in ((0.035, 2.2), (0.05, 1.0)):
            d.rectangle([w * ins * ss, h * ins * ss * 1.33, w * (1 - ins) * ss, h * (1 - ins * 1.33) * ss],
                        outline=255, width=int(wd * ss))
    t.paint(shape_mask(w, h, frame) * 0.9, ink, 0.55)
    # masthead (image y down: the top of the sheet is v = 1)
    top_y = h * (1 - v1)
    mh = h * 0.1
    t.paint(text_mask(w, h, [("Nachtmarkt-Blatt", "fraktur", mh, None, (w / 2, top_y * 0.5 + h * 0.025), "mm")]),
            ink, 0.55)
    t.paint(text_mask(w, h, [("Bratwurst  ·  Currywurst  ·  frische Brötchen  ·  Senf vom Fass", "fell", h * 0.03,
                              None, (w / 2, top_y * 0.5 + h * 0.105), "mm")]), ink, 0.55)
    # border motifs along both sides and the foot: stars, firs and stalls in turn
    def motifs(d, ss):
        def star(x, y, R):
            d.polygon([((x + (R if k % 2 == 0 else R * 0.42) * math.cos(-math.pi / 2 + k * math.pi / 5)) * ss,
                        (y + (R if k % 2 == 0 else R * 0.42) * math.sin(-math.pi / 2 + k * math.pi / 5)) * ss)
                       for k in range(10)], fill=255)

        def fir(x, y, R):
            for k in range(3):
                yy0 = y - R + k * R * 0.55
                d.polygon([(x * ss, yy0 * ss), ((x - R * (0.45 + 0.2 * k)) * ss, (yy0 + R * 0.7) * ss),
                           ((x + R * (0.45 + 0.2 * k)) * ss, (yy0 + R * 0.7) * ss)], fill=255)
            d.rectangle([(x - R * 0.1) * ss, (y + R * 0.75) * ss, (x + R * 0.1) * ss, (y + R * 1.0) * ss], fill=255)

        def stall(x, y, R):
            d.polygon([((x - R) * ss, (y - R * 0.1) * ss), (x * ss, (y - R * 0.8) * ss), ((x + R) * ss, (y - R * 0.1) * ss)],
                      fill=255)
            d.rectangle([(x - R * 0.8) * ss, (y - R * 0.1) * ss, (x + R * 0.8) * ss, (y + R * 0.8) * ss], outline=255,
                        width=int(1.4 * ss))
            d.rectangle([(x - R * 0.8) * ss, (y + R * 0.15) * ss, (x + R * 0.8) * ss, (y + R * 0.3) * ss], fill=255)
        kinds = [star, fir, stall]
        R = h * 0.022
        # left and right columns
        x_l, x_r = w * (u0 * 0.5 + 0.02), w * (1 - u0 * 0.5 - 0.02)
        ys = np.linspace(h * (1 - v1) + R * 2, h * (1 - v0) - R, 9)
        for k, y in enumerate(ys):
            kinds[k % 3](x_l, y, R)
            kinds[(k + 1) % 3](x_r, y, R)
        xs = np.linspace(w * u0 + R * 2, w * u1 - R * 2, 13)
        for k, x in enumerate(xs):
            kinds[k % 3](x, h * (1 - v0 * 0.45) - R * 0.6, R)
    t.paint(shape_mask(w, h, motifs) * 0.88, ink, 0.55)
    # a grease spot creeping in from a corner (outside the writing area)
    g = smooth(0.7, 0.55, np.hypot(xx / w - 0.96, yy / h - 0.08) * 3.2) * smooth(0.3, 0.6, fbm(h, w, 18, seed + 5))
    t.paint(g * 0.35, hexc("d8bf8e"), 0.35)
    t.height = fbm(h, w, 3, seed + 2) * 0.25
    return t


def g_back_label(spec):
    key, estate, grape, detail, region, vintage, bg, ink, accent, style = spec
    alc, vol = WINE_SMALL.get(key, ("12,0", "0,75 l"))
    k = hexc(ink)
    if sum(k) > 1.6:                       # a light ink (dark front label): print the back in the accent
        k = hexc(accent) if sum(hexc(accent)) < 1.6 else hexc("2a2420")
    a = hexc(accent)

    def f(w, h, seed):
        t = Tex(w, h, hexc(WRITE_COLOURS["label"]), 0.75)
        t.col = mix(t.col, t.col * 0.93, fbm(h, w, 16, seed) * 0.4)
        t.height = fbm(h, w, 2, seed + 1) * 0.12
        u0, v0, u1, v1 = BACK_LABEL_WRITE

        def frame(d, ss):
            d.rectangle([3 * ss, 3 * ss, (w - 4) * ss, (h - 4) * ss], outline=255, width=int(1.6 * ss))
        t.paint(shape_mask(w, h, frame), a, 0.7)
        top = h * (1 - v1)
        rows = [(estate, "fellsc", fit_size(estate, "fellsc", h * 0.055, None, w * 0.82), None, (w / 2, top * 0.38), "mm"),
                (f"{region} · {vintage}", "garamond", fit_size(f"{region} · {vintage}", "garamond", h * 0.05, 500, w * 0.8),
                 500, (w / 2, top * 0.72), "mm")]
        t.paint(text_mask(w, h, rows), k, 0.7)
        t.paint(((np.mgrid[0:h, 0:w][0] > top * 0.92) & (np.mgrid[0:h, 0:w][0] < top * 0.92 + 1.2) &
                 (np.mgrid[0:h, 0:w][1] > w * 0.3) & (np.mgrid[0:h, 0:w][1] < w * 0.7)).astype(float), a, 0.7)
        bot = h * (1 - v0)
        small = [("Gutsabfüllung · Qualitätswein", f"{vol} · {alc} % vol", "Enthält Sulfite · Deutschland")]
        lines = []
        for i, s in enumerate(small[0]):
            lines.append((s, "garamond", fit_size(s, "garamond", h * 0.04, 500, w * 0.84), 500,
                          (w / 2, bot + (h - bot) * (0.24 + 0.27 * i)), "mm"))
        t.paint(text_mask(w, h, lines), k, 0.7)
        return t
    return f


def g_cloth(w, h, seed):
    """Book cloth for the open hardback: deep red buckram, worn at the edges."""
    t = va.spine_base(w, h, seed, "6a1c20", "cloth")
    return t


def g_endpaper(w, h, seed):
    """Marbled endpaper (Kammmarmor): combed swirls in blue, ochre and red on cream."""
    t = Tex(w, h, hexc("e8dcc0"), 0.8)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    n1 = fbm(h, w, 40, seed, oct=3)
    warp = xx + 30 * np.sin(yy / 9.0 + n1 * 6) + n1 * 60
    bands = (warp / 14.0) % 3
    cols = [hexc("2a4a7a"), hexc("c8962a"), hexc("8a2a22")]
    for i, c in enumerate(cols):
        m = smooth(0.35, 0.0, np.abs(bands - i - 0.5) - 0.12)
        t.paint(m * 0.85, c, 0.8)
    comb = smooth(0.6, 0.0, np.abs(((yy + 8 * np.sin(xx / 21)) % 12) - 6) - 4.6)
    t.col = mix(t.col, np.array(hexc("efe6d0")), comb * 0.5)
    return t


def g_page_paper(w, h, seed):
    t = Tex(w, h, hexc(WRITE_COLOURS["page"]), 0.9)
    t.col = mix(t.col, t.col * 0.95, fbm(h, w, 24, seed) * 0.5)
    t.height = fbm(h, w, 2, seed + 1) * 0.1
    return t


def g_headband(w, h, seed):
    t = Tex(w, h, hexc("e8dcc0"), 0.7)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    stripe = ((xx // 3) % 2).astype(float)
    t.paint(stripe, hexc("8a1a1a"), 0.6)
    t.height = (np.sin(xx * 2.1) * 0.5 + 0.5) * 0.4
    return t


def g_ribbon(w, h, seed):
    t = Tex(w, h, hexc("7a1a22"), 0.45)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, t.col * 0.8, (np.sin(xx * 1.7) * 0.5 + 0.5) * 0.3)
    t.height = (np.sin(xx * 1.7) * 0.5 + 0.5) * 0.2
    return t


def specs():
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    for cw in content_projects.COLOURWAYS:
        add(f"pr_coaster_front_{cw}", 512, 512, g_coaster_front(cw))
    for cw in content_projects.COLOURWAYS:
        add(f"pr_coaster_back_{cw}", 320, 320, g_coaster_back(cw))
    add("pr_coaster_edge", 64, 32, g_coaster_edge)
    add("pr_marktblatt", 704, 528, g_marktblatt)
    for spec in atlas_goods.WINE_LABELS:
        add(f"pr_back_{spec[0]}", 176, 288, g_back_label(spec))
    add("pr_cloth", 256, 256, g_cloth)
    add("pr_paper", 128, 128, g_page_paper)
    add("pr_page_edge", 256, 64, va.g_pages_edge)
    add("pr_headband", 64, 16, g_headband)
    add("pr_ribbon", 32, 128, g_ribbon)
    return R


def build(out=OUT):
    os.makedirs(out, exist_ok=True)
    regions, used = va._render_atlas(specs(), SIZE, "print", out, grow=True)
    height = max(SIZE, -(-used // 256) * 256)          # _render_atlas grows from a square
    # the plain write_ faces take the printed surface's mean colour round their writing area, so the seam
    # between the printed ring and the writing face does not show (the mottling darkens the base a little)
    im = np.asarray(Image.open(os.path.join(out, "print_color.png")).convert("RGB"), float) / 255.0
    H_, W_ = im.shape[:2]

    def mean_hex(name, u0, v0, u1, v1):
        r = regions[name]
        x0 = int((r[0] + (r[2] - r[0]) * u0) * W_)
        x1 = int((r[0] + (r[2] - r[0]) * u1) * W_)
        y1 = int((1 - (r[1] + (r[3] - r[1]) * v0)) * H_)
        y0 = int((1 - (r[1] + (r[3] - r[1]) * v1)) * H_)
        c = im[y0:y1, x0:x1].reshape(-1, 3).mean(0)
        return "".join(f"{int(round(v * 255)):02x}" for v in c)
    wm = MARKTBLATT_WRITE
    bl = BACK_LABEL_WRITE
    means = {"card": mean_hex("pr_coaster_front_red", 0.3, 0.38, 0.7, 0.62),
             "paper": mean_hex("pr_marktblatt", wm[0] + 0.05, wm[1] + 0.05, wm[2] - 0.05, wm[3] - 0.05),
             "label": mean_hex(f"pr_back_{atlas_goods.WINE_LABELS[0][0]}", bl[0] + 0.05, bl[1] + 0.05, bl[2] - 0.05,
                               bl[3] - 0.05),
             "page": mean_hex("pr_paper", 0.1, 0.1, 0.9, 0.9)}
    meta = {"size": SIZE, "height": height, "used_rows_px": used, "regions": regions,
            "write_colours": means, "write_base_colours": WRITE_COLOURS, "front_rect_mm": FRONT_RECT, "back_rect_mm": BACK_RECT,
            "band_mm": [BAND_IN, BAND_OUT], "coaster_d_mm": COASTER_D, "back_label_write": BACK_LABEL_WRITE,
            "marktblatt_write": MARKTBLATT_WRITE}
    # write_grain.png: a faint paper grain (UV 0..1, near white, multiplied into the write_ faces' flat colour).
    # Without a texture on UV 0 the web optimiser prunes the write_ meshes' UVs, which the engine needs.
    g = 0.965 + 0.035 * fbm(128, 128, 6, 77)
    rng = np.random.default_rng(78)
    g = g - (rng.random((128, 128)) > 0.992) * 0.03
    Image.fromarray((np.clip(np.stack([g, g, g * 0.995], -1), 0, 1) * 255 + 0.5).astype(np.uint8)).save(
        os.path.join(out, "write_grain.png"))
    with open(os.path.join(out, "print_regions.json"), "w") as f:
        json.dump(meta, f, indent=0)
    print(f"[atlas_print] {len(regions)} regions, {used} px of {SIZE} wide (atlas {height} px tall) -> {out}")
    return meta


if __name__ == "__main__":
    build()
