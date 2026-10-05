"""Printed and painted pictures for the rides, drawn with Pillow: posters and price boards.

Each function writes a PNG into blender/out/rides_art/ (gitignored) and returns its path. They
are drawn at build time so the glb and its pictures always come from the same script. Fonts are
the bundled OFL fonts in blender/lib/fonts (see CREDITS.md, carpenter section).

Everything is scenery text in German, in the style of an old travelling-fair print: aged paper,
a soft vignette, a torn corner. No lab, pathology or clinical imagery.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from nmlib import state

ART_DIR = os.path.join(state.OUT_DIR, "rides_art")


def _font(name, size):
    return ImageFont.truetype(state.font(name), size)


def _centered(d, y, text, font, fill, W, shadow=None):
    w = d.textlength(text, font=font)
    if shadow:
        d.text(((W - w) / 2 + 3, y + 3), text, font=font, fill=shadow)
    d.text(((W - w) / 2, y), text, font=font, fill=fill)


def _age(img, seed, torn=True, stains=5):
    """Aged paper: blotchy stains, darker edges, faded ink, a torn corner, paste marks."""
    rnd = random.Random(seed)
    W, H = img.size
    over = Image.new("L", (W // 8, H // 8), 0)
    od = ImageDraw.Draw(over)
    for _ in range(stains):
        x, y = rnd.uniform(0, W / 8), rnd.uniform(0, H / 8)
        r = rnd.uniform(3, 12)
        od.ellipse((x - r, y - r, x + r, y + r), fill=rnd.randint(30, 70))
    over = over.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
    brown = Image.new("RGB", (W, H), (120, 84, 40))
    img = Image.composite(brown, img, over.point(lambda v: int(v * 0.45)))
    # vignette toward the edges (dirt, sun fade)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    for k in range(24):
        t = k / 24
        vd.rectangle((t * W * 0.06, t * H * 0.05, W - t * W * 0.06, H - t * H * 0.05), fill=int(255 * t))
    vig = vig.filter(ImageFilter.GaussianBlur(14))
    dark = Image.new("RGB", (W, H), (40, 28, 16))
    img = Image.composite(img, dark, vig.point(lambda v: 150 + int(v * 105 / 255)))
    # fine paper grain
    noise = Image.effect_noise((W, H), 18).convert("L")
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.05)
    if torn:
        d = ImageDraw.Draw(img)
        # a torn lower-right corner showing the board behind (dark brown)
        pts = [(W, H - rnd.randint(50, 80))]
        x, y = W, pts[0][1]
        while x > W - 90:
            x -= rnd.randint(6, 14)
            y += rnd.randint(2, 9)
            pts.append((x, min(y, H)))
        pts += [(W - 90, H), (W, H)]
        d.polygon(pts, fill=(52, 34, 20))
        # paste marks at the top corners
        for cx in (18, W - 18):
            d.rectangle((cx - 10, 6, cx + 10, 22), fill=(205, 190, 150))
    return img


def poster_riesenrad():
    """Tall poster: the wheel lit at night over the roofs, 'Riesenrad' in Fraktur."""
    W, H = 512, 768
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(14 + 30 * t), int(22 + 26 * t), int(58 + 20 * t)))
    rnd = random.Random(3)
    for _ in range(70):
        x, y = rnd.uniform(10, W - 10), rnd.uniform(150, 470)
        r = rnd.choice((1, 1, 1.5, 2))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(240, 226, 180))
    # the wheel: rim, spokes, gondolas, bulbs along the rim
    cx, cy, R = W / 2, 400, 170
    cream, gold = (238, 222, 180), (232, 176, 72)
    for k in range(16):
        a = math.tau * k / 16
        d.line([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a))], fill=cream, width=3)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=cream, width=7)
    d.ellipse((cx - R + 16, cy - R + 16, cx + R - 16, cy + R - 16), outline=cream, width=3)
    for k in range(48):
        a = math.tau * k / 48
        x, y = cx + (R + 1) * math.cos(a), cy + (R + 1) * math.sin(a)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 236, 170))
    cols = [(178, 36, 30), (40, 70, 150), (30, 110, 60), (220, 150, 40)]
    for k in range(16):
        a = math.tau * k / 16 + math.pi / 16
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        d.rectangle((x - 13, y + 2, x + 13, y + 26), fill=cols[k % 4], outline=cream, width=2)
        d.polygon([(x - 15, y + 4), (x, y - 4), (x + 15, y + 4)], fill=cream)
    # hub star
    star = []
    for k in range(16):
        r = 34 if k % 2 == 0 else 14
        a = math.pi * k / 8
        star.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(star, fill=gold)
    # A-frame legs and the roofs of the town in silhouette
    for sx in (-1, 1):
        d.line([(cx, cy), (cx + sx * 150, 640)], fill=cream, width=8)
    roofs = [(0, 640), (0, 600), (40, 570), (80, 600), (110, 600), (150, 560), (190, 600), (330, 600),
             (360, 575), (395, 600), (420, 590), (460, 560), (500, 590), (512, 590), (512, 640)]
    d.polygon(roofs, fill=(20, 18, 26))
    for x, y in ((50, 610), (150, 585), (380, 605), (470, 590)):
        d.rectangle((x, y, x + 10, y + 12), fill=(250, 190, 90))
    # lettering: cream panel at the top, red band at the bottom
    d.rectangle((0, 0, W, 150), fill=(234, 220, 184))
    d.rectangle((0, 144, W, 152), fill=gold)
    _centered(d, 18, "Riesenrad", _font("fraktur_bold", 104), (150, 24, 20), W, shadow=(200, 170, 120))
    d.rectangle((0, 640, W, H), fill=(150, 26, 22))
    d.rectangle((0, 640, W, 648), fill=gold)
    _centered(d, 660, "Jeden Abend bis 22 Uhr", _font("alegreya_sc", 36), (244, 226, 184), W)
    _centered(d, 708, "Auf dem Nachtmarkt", _font("fell_italic", 32), (232, 190, 110), W)
    img = _age(img, 11)
    return _save(img, "poster_riesenrad")


def poster_nachtmarkt():
    """Tall poster: a lit fir tree and stars, 'Nachtmarkt' in Fraktur."""
    W, H = 512, 768
    img = Image.new("RGB", (W, H), (150, 28, 24))
    d = ImageDraw.Draw(img)
    gold, cream = (232, 178, 76), (240, 226, 190)
    d.rectangle((22, 22, W - 22, H - 22), outline=gold, width=6)
    d.rectangle((36, 36, W - 36, H - 36), outline=cream, width=2)
    _centered(d, 56, "Nachtmarkt", _font("fraktur_bold", 96), cream, W, shadow=(90, 14, 12))
    # the tree: stacked green tiers, garland of bulbs, a star on top
    cx = W / 2
    for k, (y0, hw) in enumerate(((250, 66), (318, 104), (392, 142), (466, 180))):
        d.polygon([(cx, y0 - 60), (cx - hw, y0 + 60), (cx + hw, y0 + 60)], fill=(24, 78, 44))
    d.rectangle((cx - 16, 520, cx + 16, 560), fill=(80, 46, 24))
    rnd = random.Random(8)
    for k in range(40):
        t = rnd.random()
        y = 215 + t * 300
        hw = 40 + t * 180
        x = cx + rnd.uniform(-hw * 0.8, hw * 0.8)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=rnd.choice(((255, 226, 150), (232, 60, 40), gold)))
    star = []
    for k in range(10):
        r = 34 if k % 2 == 0 else 14
        a = -math.pi / 2 + math.pi * k / 5
        star.append((cx + r * math.cos(a), 196 + r * math.sin(a)))
    d.polygon(star, fill=gold)
    _centered(d, 590, "Glühwein · Maronen · Musik", _font("alegreya_sc", 34), cream, W)
    _centered(d, 640, "Riesenrad und Karussell", _font("fell_italic", 34), gold, W)
    _centered(d, 690, "täglich ab 16 Uhr", _font("alegreya_sc", 30), cream, W)
    img = _age(img, 23)
    return _save(img, "poster_nachtmarkt")


def price_board():
    """Painted price board under the ticket window: cream letters on a black board."""
    W, H = 512, 224
    img = Image.new("RGB", (W, H), (22, 20, 18))
    d = ImageDraw.Draw(img)
    gold, cream = (214, 164, 70), (236, 222, 188)
    d.rectangle((6, 6, W - 6, H - 6), outline=gold, width=4)
    _centered(d, 14, "Fahrpreise", _font("fraktur_bold", 54), gold, W)
    rows = (("Erwachsene", "4,00 €"), ("Kinder bis 12", "2,50 €"), ("Familienkarte", "10,00 €"))
    f = _font("alegreya_sc", 32)
    for i, (a, b) in enumerate(rows):
        y = 84 + i * 42
        d.text((40, y), a, font=f, fill=cream)
        w = d.textlength(b, font=f)
        d.text((W - 40 - w, y), b, font=f, fill=cream)
        # dotted leader
        x0 = 40 + d.textlength(a, font=f) + 10
        x1 = W - 40 - w - 10
        x = x0
        while x < x1:
            d.ellipse((x, y + 24, x + 3, y + 27), fill=(150, 140, 120))
            x += 11
    img = _age(img, 5, torn=False, stains=3)
    return _save(img, "price_board")


def rug():
    """A worn oriental rug for the drum kit: red field, a navy medallion, borders, fringe."""
    W, H = 512, 384
    img = Image.new("RGB", (W, H), (122, 22, 20))
    d = ImageDraw.Draw(img)
    navy, ivory, gold, rust = (22, 30, 62), (214, 196, 158), (196, 140, 58), (150, 60, 30)
    fr = 16  # fringe at both short ends
    for y in range(0, H, 5):
        d.line([(0, y + 2), (fr, y + 2)], fill=ivory, width=2)
        d.line([(W - fr, y + 2), (W, y + 2)], fill=ivory, width=2)
    x0, x1 = fr, W - fr
    # borders: navy outer band with a gold running pattern, ivory guard stripes
    d.rectangle((x0, 0, x1, H), fill=navy)
    d.rectangle((x0 + 6, 6, x1 - 6, H - 6), outline=ivory, width=3)
    for k in range(0, int(x1 - x0), 22):
        d.polygon([(x0 + k + 11, 12), (x0 + k + 20, 21), (x0 + k + 11, 30), (x0 + k + 2, 21)], fill=gold)
        d.polygon([(x0 + k + 11, H - 30), (x0 + k + 20, H - 21), (x0 + k + 11, H - 12), (x0 + k + 2, H - 21)], fill=gold)
    for k in range(0, H - 60, 22):
        for xx in (x0 + 21, x1 - 21):
            d.polygon([(xx, 34 + k + 2), (xx + 9, 34 + k + 11), (xx, 34 + k + 20), (xx - 9, 34 + k + 11)], fill=gold)
    d.rectangle((x0 + 38, 38, x1 - 38, H - 38), fill=(128, 24, 22), outline=ivory, width=3)
    # field: small repeating flowers
    rnd = random.Random(4)
    for yy in range(56, H - 50, 26):
        for xx in range(int(x0) + 56, int(x1) - 50, 26):
            c = rnd.choice((navy, gold, rust, ivory))
            d.ellipse((xx - 3, yy - 3, xx + 3, yy + 3), fill=c)
    # central medallion and corner spandrels
    cx, cy = W / 2, H / 2
    for r, c in ((96, ivory), (90, navy), (70, gold), (62, rust), (40, navy), (18, gold)):
        pts = []
        for k in range(16):
            rr = r if k % 2 == 0 else r * 0.82
            a = math.pi * k / 8
            pts.append((cx + rr * 1.35 * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=c)
    for sx, sy in ((x0 + 40, 40), (x1 - 40, 40), (x0 + 40, H - 40), (x1 - 40, H - 40)):
        d.pieslice((sx - 60, sy - 50, sx + 60, sy + 50),
                   {(True, True): 0, (False, True): 90, (False, False): 180, (True, False): 270}[(sx < cx, sy < cy)],
                   {(True, True): 90, (False, True): 180, (False, False): 270, (True, False): 360}[(sx < cx, sy < cy)],
                   fill=navy)
    # wear: a lighter worn patch where the drummer's feet go, soft dirt
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    wear = Image.new("L", (W, H), 0)
    ImageDraw.Draw(wear).ellipse((W * 0.35, H * 0.62, W * 0.65, H * 0.98), fill=90)
    wear = wear.filter(ImageFilter.GaussianBlur(26))
    img = Image.composite(Image.new("RGB", (W, H), (150, 110, 90)), img, wear)
    noise = Image.effect_noise((W, H), 30).convert("L")
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.07)
    return _save(img, "rug")


def cork():
    """Cork board face: warm granules of two or three browns, a few darker flecks, old pin holes
    and the pale ghosts of notes that hung there before (the sun faded the cork round them)."""
    import numpy as np
    W = H = 512
    rnd = np.random.default_rng(31)
    base = np.array([150, 104, 62], np.float32)
    img = np.ones((H, W, 3), np.float32) * base
    # granules: blobs of 2-6 px in light and dark browns
    for _ in range(9000):
        x, y = rnd.integers(0, W), rnd.integers(0, H)
        r = int(rnd.integers(1, 4))
        c = rnd.choice([0.70, 0.82, 1.0, 1.12, 1.22], p=[0.12, 0.22, 0.3, 0.24, 0.12])
        img[max(0, y - r):y + r, max(0, x - r):x + r] *= c
    img = np.clip(img, 0, 255)
    pil = Image.fromarray(img.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    d = ImageDraw.Draw(pil, "RGBA")
    rs = random.Random(7)
    # sun-faded ghosts of old notes (lighter rectangles) and pin holes
    for _ in range(7):
        x, y = rs.uniform(0, W - 120), rs.uniform(0, H - 90)
        w, h = rs.uniform(60, 150), rs.uniform(50, 110)
        d.rectangle((x, y, x + w, y + h), fill=(205, 160, 110, 34))
    for _ in range(140):
        x, y = rs.uniform(0, W), rs.uniform(0, H)
        d.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=(40, 24, 12, 200))
    noise = Image.effect_noise((W, H), 26).convert("L")
    pil = Image.blend(pil, Image.merge("RGB", (noise, noise, noise)), 0.06)
    return _save(pil, "cork")


def spruce():
    """Spruce top of the double bass under amber varnish: straight, fine, slightly uneven grain
    lines running along the instrument (image V), wider and softer toward the edges (u = 0, 1),
    the way a book-matched top is cut, with a faint seam down the centre."""
    import numpy as np
    W, H = 256, 512
    rnd = np.random.default_rng(12)
    u = np.linspace(0, 1, W, dtype=np.float32)
    # book-matched: the grain is mirrored about the centre, narrow at the centre joint
    t = np.abs(u - 0.5) * 2
    pos = (t ** 1.25) * 70.0
    lines = np.zeros(W, np.float32)
    phase = rnd.uniform(0, 1, 200)
    frac = (pos + 0.15 * np.sin(pos * 0.7)) % 1.0
    lines = np.exp(-((frac - 0.5) / 0.13) ** 2)
    row = np.tile(lines[None, :], (H, 1))
    # slight run-out wander along the length
    wav = (np.sin(np.linspace(0, 3.1, H) * 2.0)[:, None] * 0.4)
    row = np.roll(row, 0, axis=1) * (0.9 + 0.1 * np.cos(wav))
    light = np.array([214, 138, 60], np.float32)      # varnished spruce (sRGB)
    dark = np.array([150, 82, 30], np.float32)
    img = light[None, None, :] * (1 - 0.55 * row[..., None]) + dark[None, None, :] * (0.55 * row[..., None])
    # varnish pooling: a touch darker toward the edges, and the centre seam
    edge = np.clip((t - 0.75) / 0.25, 0, 1) ** 2
    img *= (1 - 0.18 * edge)[None, :, None]
    seam = np.exp(-((u - 0.5) / 0.004) ** 2)
    img *= (1 - 0.25 * seam)[None, :, None]
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    noise = Image.effect_noise((W, H), 20).convert("L")
    pil = Image.blend(pil, Image.merge("RGB", (noise, noise, noise)), 0.04)
    return _save(pil, "spruce_top")


def paper_plain():
    """A plain sheet of warm card for the writing surfaces (write_*): faint fibres and a little
    unevenness, no marks. A texture (not a flat colour) so the web optimiser keeps the UVs the
    engine needs to find the writing area."""
    import numpy as np
    W = H = 128
    rnd = np.random.default_rng(3)
    base = np.array([232, 220, 196], np.float32)
    from scipy.ndimage import gaussian_filter
    cloud = gaussian_filter(rnd.normal(0, 1, (H, W)), 10)
    cloud = cloud / (np.abs(cloud).max() + 1e-6)
    fib = gaussian_filter(rnd.normal(0, 1, (H, W)), (0.6, 2.5))
    fib = fib / (np.abs(fib).max() + 1e-6)
    img = base[None, None, :] * (1 + 0.025 * cloud[..., None] + 0.02 * fib[..., None])
    return _save(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), "rides_paper")


# ------------------------------------------------------------------ the Karussell ticket (round 7)
TICKET_CREAM = (244, 222, 174)
TICKET_RED = (158, 40, 28)
TICKET_INK = (62, 36, 22)
TICKET_ORANGE = (230, 108, 34)


def _paper_grain(img, seed, amount=0.035, edge=True):
    """Faint fibres and cloudiness over a flat print (numpy, in place on a copy)."""
    import numpy as np
    from scipy.ndimage import gaussian_filter
    a = np.asarray(img, np.float32)
    H, W = a.shape[:2]
    rnd = np.random.default_rng(seed)
    cloud = gaussian_filter(rnd.normal(0, 1, (H, W)), 18)
    cloud /= np.abs(cloud).max() + 1e-6
    fib = gaussian_filter(rnd.normal(0, 1, (H, W)), (0.7, 3.0))
    fib /= np.abs(fib).max() + 1e-6
    a = a * (1 + amount * cloud[..., None] + 0.6 * amount * fib[..., None])
    # edges a touch darker, as a handled card
    yy, xx = np.mgrid[0:H, 0:W]
    e = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)).astype(np.float32)
    if edge:
        a *= (1 - 0.06 * np.exp(-e / 6.0))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def carousel_mark(d, cx, cy, s, ink, detail=True):
    """A little printed carousel: a pennant, a scalloped striped canopy, poles with horses, a
    platform. Centred on (cx, cy), about s px wide."""
    h = s * 0.5
    top = cy - s * 0.52
    # pennant on the finial
    d.line([(cx, top - s * 0.16), (cx, top)], fill=ink, width=max(1, int(s * 0.025)))
    d.polygon([(cx, top - s * 0.16), (cx + s * 0.13, top - s * 0.12), (cx, top - s * 0.08)], fill=ink)
    # canopy: a shallow cone, striped
    eave = cy - s * 0.18
    d.polygon([(cx, top), (cx + h, eave), (cx - h, eave)], fill=ink)
    if detail:
        n = 6
        for k in range(1, n, 2):
            x0, x1 = cx - h + 2 * h * k / n, cx - h + 2 * h * (k + 1) / n
            d.polygon([(cx, top + s * 0.05), (x1 - s * 0.015, eave - s * 0.015), (x0 + s * 0.015, eave - s * 0.015)],
                      fill=TICKET_CREAM if ink != TICKET_CREAM else TICKET_ORANGE)
    # scalloped valance
    sc = 7
    for k in range(sc):
        x0 = cx - h + 2 * h * k / sc
        d.pieslice([x0, eave - s * 0.05, x0 + 2 * h / sc, eave + s * 0.09], 0, 180, fill=ink)
    # poles and horses
    base = cy + s * 0.34
    for k, fx in enumerate((-0.32, 0.0, 0.32)):
        x = cx + fx * s
        d.line([(x, eave + s * 0.05), (x, base)], fill=ink, width=max(1, int(s * 0.022)))
        hy = cy + s * (0.08 if k != 1 else 0.14)
        if detail:
            w = s * 0.11
            # body, neck and head, legs: a rocking-horse silhouette
            d.ellipse([x - w, hy - w * 0.38, x + w, hy + w * 0.38], fill=ink)
            d.polygon([(x + w * 0.55, hy - w * 0.2), (x + w * 0.95, hy - w * 1.05), (x + w * 1.35, hy - w * 0.85),
                       (x + w * 1.0, hy - w * 0.55), (x + w * 0.9, hy)], fill=ink)
            lw = max(1, int(s * 0.02))
            d.line([(x - w * 0.7, hy), (x - w * 1.25, hy + w * 0.75)], fill=ink, width=lw)
            d.line([(x + w * 0.6, hy), (x + w * 1.15, hy + w * 0.75)], fill=ink, width=lw)
            d.line([(x - w * 0.95, hy - w * 0.1), (x - w * 1.35, hy + w * 0.35)], fill=ink, width=lw)
        else:
            d.ellipse([x - s * 0.06, hy - s * 0.03, x + s * 0.06, hy + s * 0.03], fill=ink)
    # platform
    d.ellipse([cx - h * 1.05, base - s * 0.04, cx + h * 1.05, base + s * 0.08], fill=ink)


def ticket_card(W=1024, H=648, margin_px=61):
    """The Karussell ticket's card (card_contact): warm cream card, a printed red double border,
    small carousel marks in the corners and a line of small print top and bottom, all inside the
    margin band; the middle stays plain for the engine's words (write_contact sits over it)."""
    img = Image.new("RGB", (W, H), TICKET_CREAM)
    d = ImageDraw.Draw(img)
    r = TICKET_RED
    d.rectangle([7, 7, W - 8, H - 8], outline=r, width=7)
    d.rectangle([19, 19, W - 20, H - 20], outline=r, width=2)
    m = margin_px - 6
    d.rectangle([m, m, W - 1 - m, H - 1 - m], outline=r, width=2)
    # corner marks in little boxes
    cs = m - 19
    for (x0, y0) in ((19, 19), (W - 20 - cs, 19), (19, H - 20 - cs), (W - 20 - cs, H - 20 - cs)):
        d.rectangle([x0, y0, x0 + cs, y0 + cs], fill=r)
        carousel_mark(d, x0 + cs / 2, y0 + cs / 2 + 1, cs * 0.82, TICKET_CREAM, detail=False)
    f = _font("alegreya_sc", 24)
    line = "Karussell  \u00b7  Fahrkarte  \u00b7  Nachtmarkt"
    _centered(d, 22, line, f, r, W)
    lw = d.textlength(line, font=f)
    for sx in (-1, 1):                                  # a printer's diamond each side
        x, y = W / 2 + sx * (lw / 2 + 22), 36
        d.polygon([(x - 8, y), (x, y - 6), (x + 8, y), (x, y + 6)], fill=r)
    f2 = _font("fell_italic", 22)
    _centered(d, H - 51, "Nr. 0427  \u00b7  Einmal rund  \u00b7  gilt f\u00fcr eine Fahrt", f2, TICKET_INK, W)
    # fine dotted rule inside the inner border
    for x in range(m + 10, W - m - 10, 9):
        d.point([(x, m + 5), (x, H - 1 - m - 5)], fill=r)
    return _save(_paper_grain(img, 71), "ticket_card")


def ticket_write(W=128, H=80):
    """The writing area of the ticket (write_contact): the same cream, plain."""
    img = Image.new("RGB", (W, H), TICKET_CREAM)
    return _save(_paper_grain(img, 72, 0.025, edge=False), "ticket_write")


def ticket_stub(W=176, H=512):
    """The perforated stub (deep ticket orange): a carousel mark and FAHRKARTE printed up its length."""
    img = Image.new("RGB", (W, H), TICKET_ORANGE)
    d = ImageDraw.Draw(img)
    ink = TICKET_INK
    d.rectangle([6, 6, W - 7, H - 7], outline=ink, width=3)
    d.rectangle([13, 13, W - 14, H - 14], outline=ink, width=1)
    carousel_mark(d, W / 2, 112, W * 0.72, ink)
    # vertical words: draw sideways then rotate
    txt = Image.new("RGBA", (300, 60), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    f = _font("alegreya_sc", 40)
    tw = td.textlength("Fahrkarte", font=f)
    td.text(((300 - tw) / 2, 4), "Fahrkarte", font=f, fill=ink)
    txt = txt.rotate(90, expand=True)
    img.paste(txt, (int(W / 2 - 30), 196), txt)
    f2 = _font("alegreya_sc", 26)
    _centered(d, H - 56, "0427", f2, ink, W)
    return _save(_paper_grain(img, 73), "ticket_stub")


def _save(img, name):
    os.makedirs(ART_DIR, exist_ok=True)
    p = os.path.join(ART_DIR, name + ".png")
    img.save(p, optimize=True)
    return p


if __name__ == "__main__":
    for fn in (poster_riesenrad, poster_nachtmarkt, price_board, rug):
        print(fn())
