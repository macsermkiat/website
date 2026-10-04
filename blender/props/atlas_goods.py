"""Round-1 pass-2 regions of the main vendor atlas: grilled sausage skin, charcoal, beer foam,
oak barrel staves and heads, German wine labels, price cards, bookmarks, a tea towel and the
Bratwurst chalk sign. Plain numpy + PIL, like vendor_atlas.py (which imports these).
"""
import math

import numpy as np
from scipy import ndimage

import vendor_atlas as va
from vendor_atlas import Tex, fbm, fit_size, hexc, mix, noise, shape_mask, smooth, text_mask, voronoi


# ------------------------------------------------------------ Bratwurst
def g_sausage(dark):
    """Grilled Bratwurst skin. U runs AROUND the sausage (w px = one circumference), V ALONG it
    (h px = its length), matching goods.sausage's loft. Browned skin with a sheen, diagonal
    char marks from the grate on two sides (turned once), blistered and darker tied ends."""
    def f(w, h, seed):
        base = hexc("4a1e0c") if dark else hexc("72361a")
        t = Tex(w, h, base, 0.3)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        brown = fbm(h, w, 22, seed)
        t.col = mix(t.col, np.array(hexc("38160a")), smooth(0.3, 0.85, brown) * 0.8)
        t.col = mix(t.col, np.array(hexc("a8602e")), smooth(0.62, 0.95, fbm(h, w, 40, seed + 9)) * 0.3)
        # char marks: the grate bars cross the sausage at about 35 degrees. In UV they run diagonally
        # across the contact side (u ~ 0.25 and, after one turn, u ~ 0.75).
        marks = np.zeros((h, w))
        halo = np.zeros((h, w))
        spacing = h / 5.5
        for side in (0.25, 0.75):
            du = (xx - side * w) / (w * 0.2)
            band = np.clip(1 - du ** 2, 0, 1) ** 0.6
            ph = (yy + (xx - side * w) * 0.7) / spacing
            d = np.abs(ph - np.round(ph)) * spacing
            marks = np.maximum(marks, smooth(13.0, 4.0, d) * band)
            halo = np.maximum(halo, smooth(26.0, 9.0, d) * band)
        marks *= 0.75 + 0.25 * fbm(h, w, 5, seed + 1)
        t.paint(halo * 0.6, hexc("2a1006"), 0.4)
        t.paint(marks, hexc("080403"), 0.7, height=-0.8)
        # black char flecks where fat dripped and flared
        fl = smooth(0.8, 0.9, fbm(h, w, 7, seed + 11))
        t.paint(fl * 0.8, hexc("0c0604"), 0.75, height=-0.3)
        # blisters: small raised, glossier bubbles of fat in the skin
        d1, _, _ = voronoi(h, w, int(w * h / 900), seed + 3)
        sites = smooth(0.62, 0.78, fbm(h, w, 6, seed + 2))
        bl = smooth(4.0, 0.5, d1) * sites
        t.paint(bl * 0.5, hexc("c07a44"), 0.12, height=0.8)
        # tied / twisted ends: darker, crinkled, a little burnt
        ends = smooth(h * 0.09, 0, np.minimum(yy, h - 1 - yy))
        t.col = mix(t.col, np.array(hexc("2e1408")), ends * 0.55)
        t.height += ends * np.sin(xx / w * 2 * math.pi * 6) * 0.6
        t.rough = t.rough + ends * 0.25
        t.height += fbm(h, w, 5, seed + 4) * 0.25
        t.col = np.clip(t.col, 0, 1)
        t.hscale = 1.2
        return t
    return f


def g_coal(w, h, seed):
    """Charcoal colour, two halves (goods map each coal face into one of them, set_wurst.coal_lump):
    left half (u < 0.5) the burning sides: matte black char with a faint grain, split by thin dark-red cracks
    (the glow itself is in coal_emit, only along the cracks and in a few small patches);
    right half (u >= 0.5) the ash-covered tops: mottled grey ash over black, a few dull cracks.
    Round 3: no orange across whole faces; the char between the cracks stays black."""
    t = Tex(w, h, hexc("0e0d0c"), 1.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    right = smooth(w * 0.48, w * 0.52, xx)
    d1, d21, _ = voronoi(h, w, int(w * h / 260), seed)
    crack = smooth(1.3, 0.0, d21)
    # charcoal keeps the wood's grain: faint parallel streaks, and a slightly lighter grey sheen on high spots
    grain = 0.5 + 0.5 * np.sin(yy * 0.9 + fbm(h, w, 10, seed + 9) * 6.0)
    t.col = mix(t.col, np.array(hexc("262422")), grain * 0.35 * (1 - right))
    ash = smooth(0.45, 0.75, fbm(h, w, 12, seed + 1)) * (0.15 + 0.85 * right)
    ash = np.maximum(ash, right * smooth(0.25, 0.55, fbm(h, w, 20, seed + 11)) * 0.8)
    t.col = mix(t.col, np.array(hexc("55524e")), ash * 0.8)
    t.col = mix(t.col, np.array(hexc("8e8a84")), smooth(0.6, 0.9, fbm(h, w, 5, seed + 2)) * ash * 0.6)
    hot = _hot(h, w, seed) * (1 - right)
    t.col = mix(t.col, np.array(hexc("5a1406")), crack * hot)
    t.rough = np.full((h, w), 1.0)
    t.height = -crack * 1.4 + np.clip(d1 / 10, 0, 1) * 0.6 + fbm(h, w, 3, seed + 3) * 0.35 + grain * 0.15
    return t


def _hot(h, w, seed):
    """How hot the burning half is, in patches: some lumps glow brightly, some only dully, some are nearly out."""
    return 0.2 + 0.8 * smooth(0.35, 0.7, fbm(h, w, 34, seed + 6))


def coal_emit(w, h, seed):
    """Glow. Left half: thin cracks, a bright orange-yellow core fading to deep red at their edges, brightness
    varying in patches (_hot), plus a few small dull-red ember spots; the char between them does not glow.
    Right half: the ash tops, dark, with only faint lines. (Coverage is measured into the build report.)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    right = smooth(w * 0.48, w * 0.52, xx)
    d1, d21, _ = voronoi(h, w, int(w * h / 260), seed)
    core = smooth(0.9, 0.0, d21)                       # the crack's hot centre line
    halo = smooth(2.2, 0.0, d21)                       # its red edges
    hot = _hot(h, w, seed)
    spots = smooth(0.74, 0.86, fbm(h, w, 6, seed + 7)) * hot
    r_l = np.clip(halo * 0.55 * hot + core * hot + spots * 0.35, 0, 1)
    g_l = np.clip(core * hot ** 1.5 * 0.55 + halo * 0.08 * hot, 0, 1)
    b_l = np.clip(core * hot ** 3 * 0.12, 0, 1)
    fr = smooth(1.0, 0.0, d21) * 0.1
    rgb = np.stack([r_l * (1 - right) + fr * right, g_l * (1 - right) + fr * 0.3 * right, b_l * (1 - right)], -1)
    return ndimage.gaussian_filter(rgb, (0.6, 0.6, 0))


# ------------------------------------------------------------ beer
def g_foam(w, h, seed):
    """Beer head, two textures in one region (goods.beer_fill maps them):
    - top three quarters (UV v 0.25..1): the head seen from above (round 6 pass 2): a soft, fine microfoam
      with small clusters of slightly larger, brighter bubbles and faint amber where it is thinnest.
    - bottom quarter (UV v 0..0.25): the wet edge against the glass. Darker, yellower cream, big glossy
      bubbles pressed against the glass and short vertical lacing streaks."""
    # round 6 pass 2 (judges: "a hard cap"): the dry head is now a soft, fine microfoam. Round 3's packed
    # bubbles had dark Voronoi rims and tan "burst" spots that read as cracked plaster under the stall lamps.
    # Now: a velvety cream with very fine bubbles, a few small clusters of slightly larger, brighter bubbles,
    # faint soft shading where the head swells and a hint of amber only where it is thinnest.
    t = Tex(w, h, hexc("f7efdd"), 0.62)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    height = ndimage.gaussian_filter(fbm(h, w, 40, seed + 11), 2.0) * 1.2          # broad soft swells
    fine = ndimage.gaussian_filter(rng.random((h, w)), 0.7)
    height += (fine - fine.mean()) * 1.6                                            # microfoam grain
    hl = np.zeros((h, w))
    rim = np.zeros((h, w))
    cluster = smooth(0.55, 0.8, fbm(h, w, 36, seed + 3))                            # where bigger bubbles gather
    for n, k in ((int(w * h / 30), 0.35), (int(w * h / 120), 1.0)):
        d1, d21, _ = voronoi(h, w, n, int(rng.integers(1 << 30)))
        r = np.sqrt(w * h / n) * 0.5
        bub = np.clip(1 - (d1 / r) ** 2, 0, 1) ** 0.5
        wgt = cluster * k if k == 1.0 else 0.6 + 0.4 * cluster
        height = height + bub * (r / 6.0) * wgt
        rim = np.maximum(rim, smooth(1.0, 0.0, d21) * wgt)
        hl = np.maximum(hl, smooth(0.3, 0.0, d1 / r) * wgt)
    t.col = mix(t.col, np.array(hexc("e6d6b4")), rim * 0.16)
    t.col = mix(t.col, np.array(hexc("fffbf3")), hl * 0.35)
    shade = ndimage.gaussian_filter(fbm(h, w, 24, seed + 9), 3.0)
    t.col = mix(t.col, np.array(hexc("ead9b6")), smooth(0.45, 0.75, shade) * 0.25)
    thin = smooth(0.7, 0.88, fbm(h, w, 30, seed + 1))
    t.col = mix(t.col, np.array(hexc("ecd29c")), thin * 0.18)
    t.rough = 0.64 - hl * 0.18
    t.height = height
    # the wet edge strip (image rows below 0.75 h)
    band = yy >= h * 0.75
    v = (yy - h * 0.75) / (h * 0.25)
    # round 3: a soft wet cream, not a glossy gold band (paler, matte-satin, little contrast)
    wet = Tex(w, h, hexc("ece0c2"), 0.5)
    d1, d21, _ = voronoi(h, w, int(w * h / 160), seed + 5)
    r = np.sqrt(w * h / (w * h / 160)) * 0.5
    bub = np.clip(1 - (d1 / r) ** 2, 0, 1) ** 0.5
    wet.col = mix(wet.col, np.array(hexc("d6c49c")), smooth(1.6, 0.0, d21) * 0.45)
    wet.col = mix(wet.col, np.array(hexc("fbf3e2")), smooth(0.3, 0.0, d1 / r) * 0.35)
    lace = smooth(0.55, 0.8, np.abs(np.sin(xx / w * 2 * math.pi * 23 + fbm(h, w, 12, seed + 6) * 4)))
    lace *= smooth(0.0, 0.6, 1 - v)                 # streaks hang below the head (low v = the beer side)
    wet.col = mix(wet.col, np.array(hexc("f2e4c0")), lace * 0.4)
    wet.col = mix(wet.col, np.array(hexc("d2b98a")), smooth(0.35, 0.0, v) * 0.25)   # beer-wet foot of the head
    wet.rough = 0.48 + 0.2 * (1 - bub) * (1 - smooth(0.3, 0.0, v))
    wet.height = bub * r / 5.0 + lace * 0.4
    t.col = np.where(band[..., None], wet.col, t.col)
    t.rough = np.where(band, wet.rough, t.rough)
    t.height = np.where(band, wet.height, t.height)
    t.col = np.clip(t.col, 0, 1)
    t.hscale = 0.9
    return t


# ------------------------------------------------------------ barrels
def g_stave(w, h, seed):
    """Oak cask staves: U across the stave, V along it. Fine straight grain, medullary flecks,
    darker wet-looking bands where the hoops sit, grey weathering. Natural colour (no tint needed)."""
    t = Tex(w, h, hexc("8a6440"), 0.66)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    rng = np.random.default_rng(seed)
    warp = fbm(h, w, 90, seed) * 10
    grain = np.abs(np.sin((xx + warp) / 2.6 * math.pi)) ** 3
    fib = ndimage.uniform_filter1d(rng.random((h, w)), 40, axis=0)
    t.col = mix(t.col, np.array(hexc("5a3c22")), grain * 0.45 + fib * 0.2)
    fleck = smooth(0.8, 0.9, noise(h, w, 2.5, seed + 3)) * smooth(0.5, 0.7, fbm(h, w, 12, seed + 4))
    t.col = mix(t.col, np.array(hexc("b89468")), fleck * 0.5)
    t.col = mix(t.col, np.array(hexc("7a7468")), smooth(0.55, 0.85, fbm(h, w, 50, seed + 5)) * 0.35)  # weathering
    t.height = -grain * 0.4 + fib * 0.3
    t.rough = 0.6 + fib * 0.2
    return t


def g_barrel_head(w, h, seed):
    """Cask head: three oak boards seen end-on (tight end-grain arcs, each board with its own heart
    far off-centre), dark joint lines between them, grey weathering, darker oiled rim where the
    chime holds it, and a fire-branded mark of a fictional house brewery. No drawn cracks."""
    t = Tex(w, h, hexc("7e5a38"), 0.72)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    seams = (0.0, w * 0.36, w * 0.66, float(w))
    rings = np.zeros((h, w))
    for i in range(3):
        x0, x1 = seams[i], seams[i + 1]
        inb = (xx >= x0) & (xx < x1)
        cx = (x0 + x1) / 2 + (w * 0.9 if i % 2 else -w * 0.9)       # heart far to one side: gentle arcs
        cy = h * (0.2 + 0.3 * i)
        r = np.hypot(xx - cx, (yy - cy) * 0.6) + fbm(h, w, 25, seed + i) * 5
        rg = np.abs(np.sin(r / (1.6 + 0.3 * i) * math.pi)) ** 5
        rings = np.where(inb, rg, rings)
        t.col = np.where(inb[..., None], mix(t.col, np.array(hexc(["86603c", "74522f", "7c5836"][i])), 0.6), t.col)
    t.col = mix(t.col, np.array(hexc("4e3420")), rings * 0.45)
    pores = smooth(0.72, 0.9, noise(h, w, 1.2, seed + 7))
    t.col = mix(t.col, np.array(hexc("3e2a18")), pores * 0.25)
    t.col = mix(t.col, np.array(hexc("8a8274")), smooth(0.5, 0.85, fbm(h, w, 40, seed + 5)) * 0.3)   # weathering
    for x in seams[1:3]:
        t.paint(smooth(1.6, 0.3, np.abs(xx - x + fbm(h, w, 30, seed + 11) * 1.5)), hexc("20140a"), 0.85, height=-0.6)
    r0 = np.hypot(xx - w / 2, yy - h / 2)
    t.paint(smooth(w * 0.4, w * 0.5, r0) * 0.55, hexc("3a2616"), 0.6)        # oiled, handled rim
    rows = [("Brauerei", "fraktur", h * 0.12, None, (w / 2, h * 0.37), "mm"),
            ("Laternengasse", "fraktur", h * 0.12, None, (w / 2, h * 0.52), "mm"),
            ("30 L", "fellsc", h * 0.11, None, (w / 2, h * 0.68), "mm")]
    m = text_mask(w, h, rows)
    burn = ndimage.gaussian_filter(m, 1.2)
    t.paint(burn * 0.5, hexc("3a2412"), 0.75)                                 # scorched halo of the brand
    t.paint(m * 0.9, hexc("1e1008"), 0.8, height=-0.35)
    t.paint(smooth(1.4, 0, np.abs(r0 - w * 0.38)) * 0.85, hexc("1e1008"), 0.8, height=-0.3)
    t.height += -rings * 0.35 + pores * 0.15
    t.rough = t.rough + rings * 0.08
    t.col = np.clip(t.col, 0, 1)
    return t


# ------------------------------------------------------------ wine
# Fictional estates only. key: (estate, grape line, detail, region, vintage, bg, ink, accent, style)
WINE_LABELS = [
    ("wl_riesling_mosel", "Weingut am Laternenberg", "Riesling", "Kabinett · feinherb", "Mosel", "2022",
     "f1e8d2", "1c1a18", "2d5a2a", "classic"),
    ("wl_riesling_rheingau", "Weinhaus Glockenhof", "Riesling", "Spätlese", "Rheingau", "2021",
     "fbf8f0", "2a2418", "b08a3a", "crest"),
    ("wl_riesling_pfalz", "Kellerei Sternschnuppe", "RIESLING", "trocken", "Pfalz", "2023",
     "ffffff", "1d2f5a", "3a6ac8", "modern"),
    ("wl_spaet_baden", "Weingut Mondscheinhang", "Spätburgunder", "Rotwein · trocken", "Baden", "2020",
     "f2e8d4", "3a0e14", "7a1624", "classic"),
    ("wl_spaet_ahr", "Winzerhof Tannenleite", "Spätburgunder", "Rotwein", "Ahr", "2019",
     "1c1a18", "e2c078", "e2c078", "crest"),
    ("wl_dornfelder_rh", "Weingut Schneehang", "DORNFELDER", "halbtrocken", "Rheinhessen", "2022",
     "3a1636", "f4ead8", "e2b0d8", "modern"),
    ("wl_dornfelder_pfalz", "Kellerei Kerzenschein", "Dornfelder", "Rotwein · trocken", "Pfalz", "2021",
     "efe4cc", "2a1410", "a8201c", "classic"),
    ("wl_silvaner_franken", "Weingut zum Weihnachtsstern", "Silvaner", "Kabinett · trocken", "Franken", "2022",
     "f4efe0", "1e3a22", "4a7a3a", "bocks"),
    ("wl_silvaner_rh", "Hof Nachtigallenruh", "SILVANER", "trocken", "Rheinhessen", "2023",
     "f8f6ee", "2a2a2a", "8aa84a", "modern"),
    ("wl_riesling_eiswein", "Weingut Eiszapfen", "Riesling Eiswein", "edelsüß · 0,375 l", "Rheingau", "2018",
     "eef3f6", "1a2a3a", "7aa0c0", "crest"),
    ("wl_weissherbst_baden", "Winzerkeller Lichterglanz", "Spätburgunder", "Weißherbst · Rosé", "Baden", "2023",
     "fbeee8", "5a1a24", "d87a8a", "classic"),
    ("wl_riesling_nahe", "Weingut Rauhreif", "RIESLING", "Auslese", "Nahe", "2020",
     "f6f1e4", "2a2a22", "b8922e", "modern"),
]


def g_wine_label(spec):
    _, estate, grape, detail, region, vintage, bg, ink, accent, style = spec

    def f(w, h, seed):
        t = Tex(w, h, hexc(bg), 0.72)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.col = mix(t.col, t.col * 0.9, fbm(h, w, 18, seed) * 0.4)          # laid paper
        t.height = fbm(h, w, 2, seed + 1) * 0.15
        a, k = hexc(accent), hexc(ink)
        rows = []
        if style == "modern":
            t.paint(((xx > w * 0.07) & (xx < w * 0.1) & (yy > h * 0.12) & (yy < h * 0.88)).astype(float), a, 0.6)
            s = fit_size(vintage, "bebas", h * 0.34, None, w * 0.5)
            rows.append((vintage, "bebas", s, None, (w * 0.16, h * 0.3), "lm"))
            s = fit_size(grape, "oswald", h * 0.16, 600, w * 0.76)
            rows.append((grape, "oswald", s, 600, (w * 0.16, h * 0.56), "lm"))
            rows.append((detail, "josefin", fit_size(detail, "josefin", h * 0.09, 500, w * 0.7), 500,
                         (w * 0.16, h * 0.7), "lm"))
            rows.append((estate + " · " + region, "josefin",
                         fit_size(estate + " · " + region, "josefin", h * 0.075, 500, w * 0.76), 500,
                         (w * 0.16, h * 0.84), "lm"))
        else:
            if style in ("classic", "bocks"):
                b = (((xx > 5) & (xx < w - 6) & (yy > 5) & (yy < h - 6)) &
                     ~((xx > 7) & (xx < w - 8) & (yy > 7) & (yy < h - 8))).astype(float)
                t.paint(b, a, 0.6)
                t.paint(smooth(1.0, 0.2, np.abs(yy - h * 0.62)) * ((xx > w * 0.25) & (xx < w * 0.75)), a, 0.6)
            if style == "crest":
                def crest(d, ss):
                    cx, cy = w / 2, h * 0.2
                    d.ellipse([(cx - 11) * ss, (cy - 11) * ss, (cx + 11) * ss, (cy + 11) * ss], outline=255,
                              width=int(1.6 * ss))
                    for i in range(6):          # a bunch of grapes
                        gx = cx + (i % 3 - 1) * 4.5 + (1 if i >= 3 else 0) * 2.2 - 1
                        gy = cy - 3 + (i // 3) * 4.5 + (4.5 if i == 5 else 0)
                        d.ellipse([(gx - 2.3) * ss, (gy - 2.3) * ss, (gx + 2.3) * ss, (gy + 2.3) * ss], fill=255)
                t.paint(shape_mask(w, h, crest), a, 0.4, 1.0 if style == "crest" and bg == "1c1a18" else 0.0)
            top = h * (0.36 if style == "crest" else 0.2)
            s = fit_size(estate, "fellsc", h * 0.09, None, w * 0.84)
            rows.append((estate, "fellsc", s, None, (w / 2, top), "mm"))
            gfn = "fraktur" if style in ("classic", "bocks") else "playfair"
            s = fit_size(grape, gfn, h * 0.22, 700, w * 0.84)
            rows.append((grape, gfn, s, 700, (w / 2, h * 0.47 if style != "crest" else h * 0.55), "mm"))
            rows.append((detail, "garamond", fit_size(detail, "garamond", h * 0.09, 500, w * 0.8), 500,
                         (w / 2, h * 0.72), "mm"))
            line = f"{region} · {vintage}"
            rows.append((line, "garamond", fit_size(line, "garamond", h * 0.1, 600, w * 0.8), 600,
                         (w / 2, h * 0.85), "mm"))
        t.paint(text_mask(w, h, rows), k, 0.6)
        return t
    return f


# ------------------------------------------------------------ stall dressing
def g_price_cards(w, h, seed):
    """Four folded price cards (each a quarter of the region), hand-lettered."""
    t = Tex(w, h, hexc("f4ecd8"), 0.85)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, t.col * 0.9, fbm(h, w, 14, seed) * 0.4)
    cards = [("Taschenbuch", "4 €"), ("Gebunden", "8 €"), ("Antiquarisch", "ab 6 €"), ("3 für", "10 €")]
    rows = []
    for i, (a, b) in enumerate(cards):
        cx, cy = (i % 2 + 0.5) * w / 2, (i // 2 + 0.5) * h / 2
        x0, y0 = (i % 2) * w / 2, (i // 2) * h / 2
        fr = (((xx > x0 + 3) & (xx < x0 + w / 2 - 3) & (yy > y0 + 3) & (yy < y0 + h / 2 - 3)) &
              ~((xx > x0 + 5) & (xx < x0 + w / 2 - 5) & (yy > y0 + 5) & (yy < y0 + h / 2 - 5))).astype(float)
        t.paint(fr, hexc("a8201c"), 0.8)
        rows.append((a, "caveat", fit_size(a, "caveat", h * 0.13, 600, w * 0.4), 600, (cx, cy - h * 0.08), "mm"))
        rows.append((b, "caveat", fit_size(b, "caveat", h * 0.2, 700, w * 0.4), 700, (cx, cy + h * 0.1), "mm"))
    t.paint(text_mask(w, h, rows), hexc("1e1a30"), 0.8)
    return t


def g_bookmarks(w, h, seed):
    """Six printed bookmarks side by side (U across, V along each strip)."""
    t = Tex(w, h, hexc("f2ead8"), 0.8)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    cols = ["8e1b1d", "1f2f52", "24462f", "d8b048", "3b5566", "7a2e4a"]
    n = len(cols)
    sw = w / n
    for i, c in enumerate(cols):
        x0 = i * sw
        body = ((xx > x0 + 1) & (xx < x0 + sw - 1)).astype(float)
        t.paint(body, hexc(c), 0.75)
        u = (xx - x0) / sw
        if i % 3 == 0:        # stars
            pat = (np.abs(((yy / 9) % 1) - 0.5) < 0.12) * (np.abs(u - 0.5) < 0.12)
        elif i % 3 == 1:      # stripes
            pat = ((yy / 7) % 2 < 0.5) * (np.abs(u - 0.5) < 0.3)
        else:                 # dots
            pat = (np.hypot(((yy / 12) % 1) - 0.5, u - 0.5) < 0.18)
        t.paint(pat.astype(float) * body * 0.8, hexc("efe2b8"), 0.6)
        t.paint(smooth(1.2, 0, np.abs(xx - x0 - 2)) + smooth(1.2, 0, np.abs(xx - x0 - sw + 2)), hexc("e8d8a8"), 0.6)
    return t


def g_towel(w, h, seed):
    """Linen tea towel with a red check (Geschirrtuch)."""
    t = Tex(w, h, hexc("ece6d8"), 0.9)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    weave = (np.sin(xx * 2.4) * np.sin(yy * 2.4)) * 0.5 + 0.5
    t.height = weave * 0.4
    band = lambda v: ((v % 32) < 6).astype(float)
    t.paint(np.maximum(band(xx), band(yy)) * 0.75, hexc("a8201c"), 0.9)
    t.paint(band(xx) * band(yy) * 0.5, hexc("7a1410"), 0.9)
    t.col = mix(t.col, t.col * 0.92, weave * 0.3)
    return t


def g_wurst_sign(w, h, seed):
    """Small chalkboard for the Bratwurst counter."""
    t = Tex(w, h, hexc("24292a"), 0.88)
    t.col = mix(t.col, np.array(hexc("4a5152")), smooth(0.45, 0.8, fbm(h, w, 30, seed)) * 0.5)
    rows = [("Rostbratwurst", "caveat", h * 0.16, 700, (w * 0.5, h * 0.17), "mm")]
    items = [("im Brötchen", "4,00"), ("Currywurst", "4,50"), ("Pommes", "3,50"), ("Senf · Ketchup", "gratis")]
    for k, (a, b) in enumerate(items):
        y = h * (0.37 + k * 0.155)
        rows.append((a, "caveat", h * 0.12, 600, (w * 0.07, y), "lm"))
        rows.append((b + (" €" if b[0].isdigit() else ""), "caveat", h * 0.12, 600, (w * 0.93, y), "rm"))
    grain = 0.55 + 0.45 * fbm(h, w, 1.5, seed + 5)
    t.paint(text_mask(w, h, rows) * grain, hexc("eeeae0"), 0.95, height=0.2)
    return t


def g_lk_tin(w, h, seed):
    """Lid of a round Elisenlebkuchen tin (Blechdose): deep red with a gold rim, a star wreath and lettering."""
    t = Tex(w, h, hexc("8e1b1d"), 0.4)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot(xx - w / 2, yy - h / 2) / (min(w, h) / 2)
    gold = hexc("d8b048")
    t.paint(smooth(0.9, 0.93, r), gold, 0.3, 1.0)
    t.paint(smooth(0.8, 0.81, r) * smooth(0.84, 0.83, r), gold, 0.3, 1.0)
    for k in range(16):
        a = 2 * np.pi * k / 16
        cx, cy = w / 2 + 0.7 * w / 2 * np.cos(a), h / 2 + 0.7 * h / 2 * np.sin(a)
        t.paint(smooth(4.5, 3.0, np.hypot(xx - cx, yy - cy)), gold, 0.3, 1.0)
    rows = [("Nürnberger", "fellsc", h * 0.1, None, (w / 2, h * 0.34), "mm"),
            ("Elisen", "fraktur", h * 0.2, 700, (w / 2, h * 0.5), "mm"),
            ("Lebkuchen", "fellsc", h * 0.1, None, (w / 2, h * 0.66), "mm")]
    t.paint(text_mask(w, h, rows), hexc("f4e2a8"), 0.35, 0.6)
    return t


def g_deco_tags(w, h, seed):
    """Eight small kraft price tags (a 4 x 2 grid), hand-lettered: one strip of U per tag."""
    t = Tex(w, h, hexc("c8a070"), 0.9)
    t.col = mix(t.col, t.col * 0.86, fbm(h, w, 10, seed) * 0.5)
    tags = [("Herz", "3 €"), ("100 g", "3,50"), ("Kerze", "ab 4 €"), ("Stück", "2 €"), ("Kugel", "5 €"),
            ("100 g", "2,90"), ("Tüte", "4 €"), ("6 Stück", "5 €")]
    rows = []
    for i, (a, b) in enumerate(tags):
        cx, cy = (i % 4 + 0.5) * w / 4, (i // 4 + 0.5) * h / 2
        rows.append((a, "caveat", fit_size(a, "caveat", h * 0.13, 600, w * 0.2), 600, (cx, cy - h * 0.09), "mm"))
        rows.append((b, "caveat", fit_size(b, "caveat", h * 0.2, 700, w * 0.21), 700, (cx, cy + h * 0.09), "mm"))
    t.paint(text_mask(w, h, rows), hexc("2a1a10"), 0.9)
    return t


# ------------------------------------------------------------ pretzel (round 6 pass 2)
def g_pretzel(w, h, seed):
    """Laugenbrezel crust, mapped round and along the rope by set_bier.pretzel: u (columns) once round the
    rope, underneath at the left and right edges and on top in the middle; v (rows, v up) along it, with the
    belly on v 0.3..0.7. A matte lye crust: deep mahogany on top, browner on the flanks, pale and floury
    underneath where it sat on the tray; fine blisters and crackle; small salt flecks on the top. Along the
    top of the belly the crust is torn open (the "Ausbund"): a jagged pale crumb split with a ragged brown
    edge. Roughness 0.62..0.75 (lye crust has a dull satin bloom, never a gloss); the crumb 0.9."""
    t = Tex(w, h, hexc("55260b"), 0.66)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    u = xx / (w - 1)
    v = 1 - yy / (h - 1)
    top = 1 - np.abs(u - 0.5) * 2                     # 1 on top, 0 underneath
    # colour round the rope: dark lye top, warmer flanks, pale floury underside
    t.col = mix(t.col, np.array(hexc("723a16")), smooth(0.75, 0.35, top) * 0.8)
    t.col = mix(t.col, np.array(hexc("b07a45")), smooth(0.3, 0.02, top) * 0.85)
    blot = fbm(h, w, 22, seed + 1)
    t.col = mix(t.col, np.array(hexc("3a1806")), smooth(0.5, 0.8, blot) * 0.6 * smooth(0.3, 0.7, top))
    t.col = mix(t.col, np.array(hexc("8a4a20")), smooth(0.45, 0.2, blot) * 0.3)
    # fine blisters and crackle in the crust
    d1, d21, _ = voronoi(h, w, int(w * h / 60), seed + 2, periodic_x=True)
    crack = smooth(1.2, 0.0, d21) * smooth(0.35, 0.7, fbm(h, w, 14, seed + 3))
    crack *= smooth(0.95, 0.5, top)                     # hairline crazing, mostly on the flanks
    t.col = mix(t.col, np.array(hexc("3a1a08")), crack * 0.14)
    blist = np.clip(1 - (d1 / 4.0) ** 2, 0, 1)
    height = blist * 0.3 - crack * 0.25 + fbm(h, w, 10, seed + 4) * 0.6
    # the Ausbund: a jagged split along the top of the belly, widest mid-belly, tapering out at both ends
    span = smooth(0.32, 0.42, v) * smooth(0.68, 0.58, v)
    wob = (fbm(h, w, 30, seed + 5)[:, :1] - 0.5) * 0.14 + (noise(h, w, 6, seed + 6)[:, :1] - 0.5) * 0.04
    off = np.abs(u - 0.5 - wob)
    half = 0.065 * span * (0.6 + 0.7 * noise(h, w, 24, seed + 7)[:, :1])
    split = smooth(half + 0.01, half - 0.02, off) * (span > 0.02)
    lip = smooth(half + 0.07, half + 0.005, off) * (1 - split) * (span > 0.02)
    crumb = mix(np.broadcast_to(np.array(hexc("d9b273")), (h, w, 3)).copy(), np.array(hexc("b98446")),
                smooth(0.35, 0.75, fbm(h, w, 6, seed + 8)) * 0.7)
    crumb = mix(crumb, np.array(hexc("ecd29a")), (rng.random((h, w)) > 0.93) * 0.35)        # open crumb
    crumb = mix(crumb, np.array(hexc("a8682e")), smooth(0.6, 1.0, off / np.maximum(half, 1e-3)) * 0.7)
    t.col = mix(t.col, np.array(hexc("9a5626")), lip * 0.55)            # the torn, lighter brown edge
    t.col = np.where(split[..., None] > 0, mix(t.col, crumb, split), t.col)
    height = height + lip * 1.2 - split * 1.6
    # salt flecks on the top (the lite build has no salt crystals; the full one adds them on top of these)
    flecks = (rng.random((h, w)) > 0.9965) * smooth(0.6, 0.9, top) * (1 - split)
    flecks = np.clip(ndimage.gaussian_filter(flecks.astype(float), 0.6) * 6, 0, 1)
    t.col = mix(t.col, np.array(hexc("ece6da")), flecks * 0.6)
    height = height + flecks * 1.0
    t.rough = 0.72 - 0.08 * smooth(0.4, 0.9, top) + split * 0.18 - flecks * 0.25
    t.height = height
    t.hscale = 0.8
    t.col = np.clip(t.col, 0, 1)
    return t


def main_specs():
    """[(name, w, h, generator)] added to the main atlas."""
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    add("sausage", 256, 448, g_sausage(False))
    add("sausage_dark", 256, 448, g_sausage(True))
    add("coal", 256, 256, g_coal)
    add("foam", 256, 256, g_foam)
    add("stave", 256, 256, g_stave)
    add("barrel_head", 192, 192, g_barrel_head)
    for spec in WINE_LABELS:
        add(spec[0], 176, 128, g_wine_label(spec))
    add("price_cards", 256, 160, g_price_cards)
    add("bookmarks", 192, 256, g_bookmarks)
    add("towel", 128, 128, g_towel)
    add("wurst_sign", 256, 192, g_wurst_sign)
    add("lk_tin", 192, 192, g_lk_tin)
    add("deco_tags", 256, 128, g_deco_tags)
    # round 6 pass 2: added last and packed on its own row (vendor_atlas.LATE), so no older region moves
    add("pretzel", 128, 384, g_pretzel)
    return R
