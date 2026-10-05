"""Round 10: small printed labels added to the print atlas (print_*.png -> prop_tex_print_*.webp).

    python3 blender/props/atlas_labels.py      # patch the new regions into blender/out/vendor/print_*

What it adds (all names start with "pr_"):
    pr_beer_<brewery>        body labels for the Bierstand's decorative bottles, six invented breweries
    pr_beerneck_<brewery>    the matching neck labels
    pr_stoneware             a salt-glazed stoneware band with a cobalt brewery stamp (the Steinkrug bottles)
    pr_crate_<brewery>       a burnt-in brand on a pine crate board
    pr_sauce_<kind>          the Bratwurst stand's squeeze-bottle labels (Senf, Ketchup, Currysauce)
    pr_shaker_curry          the curry powder shaker's label
    pr_smoked_casing         the Krakauer's smoked casing (round 10 pass 2)

The breweries are invented (Nachtmarkt-Bräu is the market's own brew, as on the Bierdeckel). No third-party
artwork: everything is drawn here from noise, shapes and the bundled OFL fonts.

The print atlas is shared by every set that prints something (coasters, Marktblatt, wine back labels, the open
book). To leave all of their UVs untouched, the new regions are not packed with the others: they are rendered
on their own and pasted into the free rows under the existing ones (print_regions.json "used_rows_px"), and
their rects are added to print_regions.json. Running it again re-renders them in the same place. A full
rebuild of the print atlas (atlas_print.build) calls patch() at its end, so the regions always exist.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import vendor_atlas as va  # noqa: E402
from vendor_atlas import Tex, fbm, fit_size, hexc, mix, shape_mask, smooth, text_mask  # noqa: E402

OUT = va.OUT
PAD = va.PAD

# key, brewery line, style (big), small line, bg, ink, accent, shape, motif
BREWERIES = [
    ("nachtmarkt", "Nachtmarkt-Bräu", "Helles", "0,5 l · 4,9 % vol", "f2e6c8", "7a1418", "c8a040", "rect", "star"),
    ("kloster", "Klosterbräu St. Nikolaus", "Dunkel", "0,5 l · 5,2 % vol", "1f3a2a", "e2c46a", "b8963a", "oval", "cross"),
    ("tannenhof", "Brauerei Tannenhof", "Pils", "0,5 l · 4,8 % vol", "f4f2ea", "1f5a32", "2a7a44", "rect", "fir"),
    ("sternwirt", "Sternwirt", "Weißbier", "0,5 l · 5,4 % vol", "2a4a8a", "f4f0e6", "e8c860", "rect", "stars"),
    ("laterne", "Laternen-Bräu", "Märzen", "0,5 l · 5,6 % vol", "c8862a", "2a1408", "f2e2b0", "oval", "lantern"),
    ("eichwald", "Brauerei Eichwald", "Kellerbier", "0,5 l · 5,0 % vol", "cfb284", "3a2010", "8a2a18", "rect", "oak"),
]
BREWERY_KEYS = [b[0] for b in BREWERIES]


def _motif(kind, cx, cy, R):
    """A small emblem drawn into a mask: brewer's star, cross, fir, stars, lantern, oak leaf."""
    def draw(d, ss):
        S = lambda x, y: (x * ss, y * ss)
        if kind == "star":
            for rot in (-math.pi / 2, math.pi / 2):
                pts = [S(cx + R * math.cos(rot + k * 2 * math.pi / 3), cy + R * math.sin(rot + k * 2 * math.pi / 3))
                       for k in range(3)]
                d.line(pts + [pts[0]], fill=255, width=max(1, int(1.6 * ss)), joint="curve")
        elif kind == "cross":
            w = R * 0.32
            d.rectangle([*S(cx - w / 2, cy - R), *S(cx + w / 2, cy + R)], fill=255)
            d.rectangle([*S(cx - R * 0.7, cy - R * 0.45 - w / 2), *S(cx + R * 0.7, cy - R * 0.45 + w / 2)], fill=255)
        elif kind == "fir":
            for k in range(3):
                y0 = cy - R + k * R * 0.55
                hw = R * (0.4 + 0.25 * k)
                d.polygon([S(cx, y0), S(cx - hw, y0 + R * 0.75), S(cx + hw, y0 + R * 0.75)], fill=255)
            d.rectangle([*S(cx - R * 0.1, cy + R * 0.85), *S(cx + R * 0.1, cy + R * 1.1)], fill=255)
        elif kind == "stars":
            for dx, r in ((-R * 0.9, R * 0.45), (0, R * 0.7), (R * 0.9, R * 0.45)):
                pts = [S(cx + dx + (r if k % 2 == 0 else r * 0.42) * math.cos(-math.pi / 2 + math.pi * k / 5),
                         cy + (r if k % 2 == 0 else r * 0.42) * math.sin(-math.pi / 2 + math.pi * k / 5)) for k in range(10)]
                d.polygon(pts, fill=255)
        elif kind == "lantern":
            d.rectangle([*S(cx - R * 0.45, cy - R * 0.55), *S(cx + R * 0.45, cy + R * 0.7)], outline=255,
                        width=max(1, int(1.4 * ss)))
            d.polygon([S(cx - R * 0.6, cy - R * 0.55), S(cx + R * 0.6, cy - R * 0.55), S(cx, cy - R)], fill=255)
            d.ellipse([*S(cx - R * 0.18, cy - R * 0.15), *S(cx + R * 0.18, cy + R * 0.35)], fill=255)
            d.rectangle([*S(cx - R * 0.55, cy + R * 0.7), *S(cx + R * 0.55, cy + R * 0.85)], fill=255)
        elif kind == "oak":
            pts = []
            for k in range(41):
                t = k / 40
                a = t * 2 * math.pi
                lob = 1 + 0.22 * math.cos(a * 4)
                pts.append(S(cx + R * 0.48 * math.sin(a) * lob, cy - R * 0.95 * math.cos(a) * (0.92 + 0.08 * lob)))
            d.polygon(pts, fill=255)
    return draw


def g_beer_label(spec):
    """A body label: paper with a little mottling, a double rule (rect) or an oval panel, the brewery on top,
    the style big in the middle, an emblem, and the small print below."""
    key, brewery, style, small, bg, ink, accent, shape, motif = spec

    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.62)
        t.col = mix(t.col, t.col * 0.9, fbm(h, w, 14, seed) * 0.45)
        t.height = fbm(h, w, 2, seed + 1) * 0.15
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        a, k = hexc(accent), hexc(ink)
        if shape == "oval":
            r = np.hypot((xx - w / 2) / (w * 0.47), (yy - h / 2) / (h * 0.46))
            t.paint(smooth(1.0, 0.97, r) - smooth(0.93, 0.9, r), a, 0.5)
            t.paint(smooth(0.86, 0.84, r) - smooth(0.83, 0.81, r), a, 0.5)
        else:
            for m in (3, 7):
                b = (((xx > m) & (xx < w - m - 1) & (yy > m) & (yy < h - m - 1)) &
                     ~((xx > m + 1.6) & (xx < w - m - 2.6) & (yy > m + 1.6) & (yy < h - m - 2.6))).astype(float)
                t.paint(b, a, 0.5)
        # gold foil band behind the style name on the rect labels
        if shape == "rect":
            t.paint(((yy > h * 0.42) & (yy < h * 0.7) & (xx > 9) & (xx < w - 10)).astype(float) * 0.18, a, 0.4)
        t.paint(shape_mask(w, h, _motif(motif, w / 2, h * 0.2, h * 0.095)), a, 0.45, 0.2)
        rows = [(brewery, "fellsc", fit_size(brewery, "fellsc", h * 0.11, None, w * 0.74), None, (w / 2, h * 0.36), "mm"),
                (style, "fraktur", fit_size(style, "fraktur", h * 0.26, None, w * 0.7), None, (w / 2, h * 0.57), "mm"),
                (small, "garamond", fit_size(small, "garamond", h * 0.085, 500, w * 0.6), 500, (w / 2, h * 0.8), "mm")]
        t.paint(text_mask(w, h, rows), k, 0.6)
        return t
    return f


def g_neck_label(spec):
    key, brewery, style, small, bg, ink, accent, shape, motif = spec

    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.62)
        t.col = mix(t.col, t.col * 0.9, fbm(h, w, 10, seed) * 0.4)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.paint(((yy < 3) | (yy > h - 4)).astype(float), hexc(accent), 0.5)
        word = brewery.split()[-1].upper() if key != "nachtmarkt" else "NACHTMARKT"
        t.paint(text_mask(w, h, [(word, "fellsc", fit_size(word, "fellsc", h * 0.5, None, w * 0.42), None,
                                  (w / 4, h / 2), "mm"),
                                 (word, "fellsc", fit_size(word, "fellsc", h * 0.5, None, w * 0.42), None,
                                  (w * 3 / 4, h / 2), "mm")]), hexc(ink), 0.6)
        return t
    return f


def g_stoneware(w, h, seed):
    """Salt-glazed stoneware (cream under an orange-peel glaze) with a cobalt brewery stamp in the middle: the
    lower body of the Steinkrug bottles (their dipped brown shoulders are plain glaze)."""
    t = Tex(w, h, hexc("d8c8a4"), 0.32)
    t.col = mix(t.col, np.array(hexc("b89a70")), fbm(h, w, 9, seed) * 0.5)
    t.col = mix(t.col, np.array(hexc("e8dcc0")), smooth(0.6, 0.9, fbm(h, w, 3, seed + 3)) * 0.4)
    t.height = fbm(h, w, 1.6, seed + 5) * 0.6                     # orange peel
    t.hscale = 1.4
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    cob = hexc("2a3a7a")
    r = np.hypot((xx - w / 2) / (w * 0.22), (yy - h / 2) / (h * 0.36))
    t.paint((smooth(1.0, 0.95, r) - smooth(0.9, 0.85, r)) * 0.9, cob, 0.3, height=-0.4)
    rows = [("EICHWALD", "fellsc", fit_size("EICHWALD", "fellsc", h * 0.16, None, w * 0.3), None, (w / 2, h * 0.4), "mm"),
            ("1874", "garamond", fit_size("1874", "garamond", h * 0.14, 600, w * 0.2), 600, (w / 2, h * 0.62), "mm")]
    t.paint(text_mask(w, h, rows) * 0.9, cob, 0.3, height=-0.4)
    # a cobalt line round the body, above and below the stamp
    t.paint(((np.abs(yy - h * 0.08) < 1.5) | (np.abs(yy - h * 0.92) < 1.5)).astype(float) * 0.8, cob, 0.3)
    return t


def g_smoked_casing(w, h, seed):
    """Round 10 pass 2: the Krakauer's own smoked casing (pr_smoked_casing), so it no longer borrows the grilled
    Bratwurst skin. U runs around (w px = one circumference), V along (h px = its length), as goods.sausage lofts it.
    Mahogany red-brown under a glossy smoke film, darker on the side that faced the smoke, fine wrinkles running
    along, pale specks of the coarse fat grind showing through, the string tie and its pinch at each end. Drawn at
    the casing's true proportions (12.6 cm round, 17 cm long) and squeezed to the region, so features stay round."""
    from PIL import Image as _I
    H = int(round(w * 17.0 / 12.6))
    t = Tex(w, H, hexc("7a2a14"), 0.26)
    yy, xx = np.mgrid[0:H, 0:w].astype(float)
    u = xx / w
    # smoke: one side darker (where it hung toward the smoke), streaky along the length
    side = 0.5 + 0.5 * np.cos((u - 0.3) * 2 * math.pi)
    streak = fbm(H, w, 10, seed + 1)
    t.col = mix(t.col, np.array(hexc("3e140a")), np.clip(side * 0.55 + (streak - 0.5) * 0.5, 0, 1))
    t.col = mix(t.col, np.array(hexc("9a3c1c")), smooth(0.55, 0.9, fbm(H, w, 24, seed + 2)) * 0.35)
    # coarse grind: pale fat and darker lean showing through the thin casing
    d1, _, _ = va.voronoi(H, w, int(w * H / 60), seed + 3)
    fat = smooth(2.2, 0.6, d1) * smooth(0.45, 0.7, fbm(H, w, 4, seed + 4))
    t.paint(fat * 0.45, hexc("c88a6a"), 0.3, height=0.25)
    lean = smooth(0.62, 0.8, fbm(H, w, 3, seed + 5))
    t.paint(lean * 0.35, hexc("4a120a"), None, height=-0.1)
    # fine wrinkles along the length (the casing shrank in the smoke)
    wr = np.sin(xx / w * 2 * math.pi * 26 + fbm(H, w, 14, seed + 6) * 7.0)
    wr = smooth(0.55, 1.0, wr) * (0.5 + 0.5 * fbm(H, w, 12, seed + 7))
    t.paint(wr * 0.25, hexc("2e0e06"), 0.4, height=-0.5)
    # glossy fat sheen patches
    t.rough = t.rough - smooth(0.5, 0.85, fbm(H, w, 16, seed + 8)) * 0.12
    # the ends: pinched and tied with string, darker
    e = np.minimum(yy, H - 1 - yy)
    ends = smooth(H * 0.08, 0, e)
    t.col = mix(t.col, np.array(hexc("2a0c06")), ends * 0.6)
    t.height += ends * np.sin(u * 2 * math.pi * 9) * 0.7
    string = (np.abs(e - H * 0.035) < 1.6).astype(float) * (0.8 + 0.2 * np.sin(u * 2 * math.pi * 14))
    t.paint(string * 0.85, hexc("d8ccb0"), 0.85, height=0.6)
    t.height += fbm(H, w, 4, seed + 9) * 0.2
    t.col = np.clip(t.col, 0, 1)
    t.hscale = 1.1
    # squeeze to the region's height
    def rs(a, mode=_I.BILINEAR):
        if a.ndim == 3:
            return np.stack([rs(a[..., c]) for c in range(a.shape[-1])], -1)
        return np.asarray(_I.fromarray(a.astype(np.float32), mode="F").resize((w, h), _I.BOX), float)
    out = Tex(w, h)
    out.col, out.rough, out.metal, out.height = rs(t.col), rs(t.rough), rs(t.metal), rs(t.height)
    out.hscale = t.hscale
    return out


def g_crate_brand(name, sub):
    def f(w, h, seed):
        t = Tex(w, h, hexc("c09060"), 0.8)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        grain = fbm(h, w, 6, seed)
        streak = 0.5 + 0.5 * np.sin(yy / h * 9 + grain * 6 + xx / w * 0.8)
        t.col = mix(t.col, np.array(hexc("8a5a34")), streak * 0.35 + grain * 0.2)
        t.height = streak * 0.3
        ink = hexc("2a1408")
        m = text_mask(w, h, [(name, "fellsc", fit_size(name, "fellsc", h * 0.42, None, w * 0.86), None,
                              (w / 2, h * 0.42), "mm"),
                             (sub, "garamond", fit_size(sub, "garamond", h * 0.2, 600, w * 0.6), 600, (w / 2, h * 0.8), "mm")])
        m = m * (0.75 + 0.25 * fbm(h, w, 3, seed + 2))                 # burnt in unevenly
        t.paint(m, ink, 0.9, height=-0.5)
        return t
    return f


def g_sauce(title, sub, bg, ink, accent, motif):
    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.45)
        t.col = mix(t.col, t.col * 0.94, fbm(h, w, 12, seed) * 0.4)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        a = hexc(accent)
        t.paint(((yy < h * 0.14) | (yy > h * 0.86)).astype(float), a, 0.45)

        def mot(d, ss):
            cx, cy, R = w * 0.18, h * 0.5, h * 0.2
            if motif == "seed":            # mustard seeds
                for k in range(5):
                    ang = k * 1.26
                    d.ellipse([(cx + R * 0.6 * math.cos(ang) - R * 0.32) * ss, (cy + R * 0.6 * math.sin(ang) - R * 0.32) * ss,
                               (cx + R * 0.6 * math.cos(ang) + R * 0.32) * ss, (cy + R * 0.6 * math.sin(ang) + R * 0.32) * ss],
                              fill=255)
            elif motif == "tomato":
                d.ellipse([(cx - R) * ss, (cy - R * 0.85) * ss, (cx + R) * ss, (cy + R * 0.95) * ss], fill=255)
            else:                          # a chili
                d.polygon([((cx - R) * ss, (cy - R * 0.3) * ss), ((cx + R) * ss, (cy - R * 0.1) * ss),
                           ((cx - R * 0.2) * ss, (cy + R * 0.9) * ss)], fill=255)
        t.paint(shape_mask(w, h, mot), a, 0.45)
        rows = [(title, "oswald", fit_size(title, "oswald", h * 0.36, 600, w * 0.6), 600, (w * 0.6, h * 0.44), "mm"),
                (sub, "garamond", fit_size(sub, "garamond", h * 0.15, 600, w * 0.6), 600, (w * 0.6, h * 0.7), "mm")]
        t.paint(text_mask(w, h, rows), hexc(ink), 0.45)
        return t
    return f


def specs():
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    for b in BREWERIES:
        add(f"pr_beer_{b[0]}", 192, 128, g_beer_label(b))
    add("pr_sauce_senf", 128, 80, g_sauce("SENF", "mittelscharf", "f6f0dc", "5a3a08", "d8a81a", "seed"))
    add("pr_sauce_ketchup", 128, 80, g_sauce("KETCHUP", "Tomate", "f6f2ea", "8a1410", "c8281c", "tomato"))
    add("pr_sauce_curry", 128, 80, g_sauce("CURRY", "Currysauce", "2a1a12", "f2a040", "d8641c", "chili"))
    add("pr_shaker_curry", 128, 64, g_sauce("CURRY", "Gewürz · edelsüß", "f2e4c0", "6a2a0a", "d86a1a", "chili"))
    add("pr_stoneware", 192, 96, g_stoneware)
    add("pr_crate_eichwald", 256, 64, g_crate_brand("BRAUEREI EICHWALD", "Kellerbier"))
    add("pr_crate_tannenhof", 256, 64, g_crate_brand("TANNENHOF PILS", "Brauerei Tannenhof"))
    for b in BREWERIES:
        add(f"pr_beerneck_{b[0]}", 128, 32, g_neck_label(b))
    # round 10 pass 2: appended last, so the shelf-packing above keeps every earlier rect where it was
    add("pr_smoked_casing", 192, 72, g_smoked_casing)
    return R


def patch(out=OUT):
    """Render the label regions and paste them into the free rows of the print atlas (see the module notes)."""
    meta_path = os.path.join(out, "print_regions.json")
    with open(meta_path) as f:
        meta = json.load(f)
    size, height = meta["size"], meta["height"]
    sp = specs()
    names = [s[0] for s in sp]
    regions = meta["regions"]
    base = meta.get("labels_rows_from", meta["used_rows_px"])
    # shelf-pack in the given order from the first free row
    x = 0
    y = base
    row_h = 0
    rects = {}
    for name, w, h, _ in sp:
        W, H = w + 2 * PAD, h + 2 * PAD
        if x + W > size:
            x, y, row_h = 0, y + row_h, 0
        rects[name] = (x + PAD, y + PAD, w, h)
        x += W
        row_h = max(row_h, H)
    end = y + row_h
    if end > height:
        raise RuntimeError(f"print atlas: labels need rows {base}..{end}, the atlas is {height} px tall")
    imgs = {k: np.asarray(Image.open(os.path.join(out, f"print_{k}.png")).convert("RGB"), float) / 255.0
            for k in ("color", "rm", "normal")}
    for i, (name, w, h, gen) in enumerate(sp):
        px, py, _, _ = rects[name]
        t = gen(w, h, 7000 + i * 13)
        n = va.normal_from_height(np.pad(t.height, 1, mode="edge"), t.hscale)[1:-1, 1:-1]
        layers = {"color": np.clip(t.col, 0, 1),
                  "rm": np.stack([np.ones((h, w)), np.clip(t.rough, 0.02, 1), np.clip(t.metal, 0, 1)], -1),
                  "normal": n}
        for k, src in layers.items():
            imgs[k][py - PAD:py + h + PAD, px - PAD:px + w + PAD] = np.pad(src, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        regions[name] = [(px + 0.5) / size, 1 - (py + h - 0.5) / height, (px + w - 0.5) / size, 1 - (py + 0.5) / height]
    for k, a in imgs.items():
        Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, f"print_{k}.png"))
    meta["labels_rows_from"] = base
    meta["used_rows_px"] = max(meta["used_rows_px"], end)
    meta["labels"] = names
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=0)
    print(f"[atlas_labels] {len(sp)} label regions in print atlas rows {base}..{end} of {height}")
    return meta


if __name__ == "__main__":
    patch()
