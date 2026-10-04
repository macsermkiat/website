"""Make the round-2 review JPEGs from the raw screenshots (shoot.mjs / shoot-market.mjs).

    python3 site/src/lighting/compose.py   # from the repo root
Env: RAW (this round's test-bench PNGs), MARKET (this round's market PNGs), BEFORE (the market PNGs
with round 1's lighting). Every image is at most 1280 px wide (BUILD.md).
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'review/round-2/lighting')
RAW = os.environ.get('RAW') or os.path.join(OUT, 'raw')
MARKET = os.environ.get('MARKET') or os.path.join(OUT, 'raw_market')
BEFORE = os.environ.get('BEFORE') or os.path.join(OUT, 'raw_before')
R1 = os.path.join(ROOT, 'review/round-1/lighting')
REF = os.path.join(ROOT, 'review/reference/gluehwein_preview.png')
MAXW = 1280


def font(size):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def label(im, text, size=18):
    d = ImageDraw.Draw(im, 'RGBA')
    f = font(size)
    w = d.textlength(text, font=f)
    d.rectangle((8, 8, 8 + w + 16, 8 + size + 12), fill=(0, 0, 0, 160))
    d.text((16, 13), text, font=f, fill=(245, 230, 205, 255))
    return im


def load(path, size=None, crop=None):
    if not path or not os.path.exists(path):
        return None
    im = Image.open(path).convert('RGB')
    if crop:
        im = im.crop(crop)
    return im.resize(size, Image.LANCZOS) if size else im


def save(im, name):
    if im.width > MAXW:
        im = im.resize((MAXW, round(im.height * MAXW / im.width)), Image.LANCZOS)
    p = os.path.join(OUT, name)
    im.save(p, quality=88)
    print(name, im.size)


def grid(cells, cols, cell, name, size=18):
    """cells: [(image or None, label)], laid out in `cols` columns of `cell` (w, h)."""
    cells = [(im, t) for im, t in cells if im is not None]
    if not cells:
        return
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGB', (cell[0] * min(cols, len(cells)), cell[1] * rows), (12, 12, 16))
    for i, (im, t) in enumerate(cells):
        im = label(im.resize(cell, Image.LANCZOS), t, size)
        sheet.paste(im, ((i % cols) * cell[0], (i // cols) * cell[1]))
    save(sheet, name)


def main():
    raw = lambda n: os.path.join(RAW, n + '.png')
    mk = lambda n: os.path.join(MARKET, n + '.png')
    bf = lambda n: os.path.join(BEFORE, n + '.png')
    half = (640, 360)

    # the test bench
    after = load(raw('after'))
    if after:
        save(label(after.copy(), 'Round 2, full (test bench)'), 'after.jpg')
    lite = load(raw('lite'))
    if lite:
        save(label(lite.copy(), 'Round 2, lite (test bench)'), 'after_lite.jpg')
    r1 = load(os.path.join(R1, 'after.jpg'))
    if r1:
        save(label(r1.copy(), 'Round 1 (pass 4), full: before'), 'before.jpg')
    grid([(load(REF), 'Cycles reference'), (r1, 'Round 1, full'), (after, 'Round 2, full'), (lite, 'Round 2, lite')],
         2, half, 'side_by_side.jpg')
    ref = load(REF)
    if ref and after:
        grid([(ref, 'Cycles reference'), (after, 'Round 2, full')], 2, half, 'side_by_side_pair.jpg')
    # the sign lamp on the bench: board without and with it (crop around the "Glühwein" board)
    box = (470, 440, 990, 700)
    nosign = load(raw('nosign'), crop=box)
    if nosign and after:
        grid([(load(REF, crop=box), 'Cycles'), (nosign, 'No sign lamp'), (after.crop(box), 'Sign lamp')], 3, (426, 213), 'sign_lamp_bench.jpg', 14)
    snow = load(raw('snow'))
    if snow:
        grid([(after, 'Snow off'), (snow, 'Snow on (setSnow(true))')], 2, half, 'snow_toggle.jpg')
    if lite:
        # the lite roof and gable (the round-1 leak) and the lite back wall
        grid([(load(REF, crop=(250, 20, 650, 260)), 'Cycles'), (lite.crop((250, 20, 650, 260)), 'Lite: gable and eave')], 2, (640, 384), 'lite_gable.jpg')

    # the market
    pairs = [
        ('market', 'Home view, full'),
        ('market_lite', 'Home view, lite'),
        ('market_snow', 'Home view, snow'),
        ('glueh', 'Glühwein entered, full'),
        ('wurst', 'Bratwurst entered, full'),
        ('lite_glueh', 'Glühwein entered, lite'),
        ('lite_band', 'Bandstand entered, lite'),
        ('sign_glueh', 'Glühwein stand from the square, full'),
        ('sign_wurst', 'Bratwurst stand from the square, full'),
    ]
    for n, t in pairs:
        a = load(mk(n))
        if a:
            save(label(a.copy(), f'Round 2: {t}'), f'market_{n}.jpg' if not n.startswith('market') else f'{n}.jpg')
        b = load(bf(n))
        if a and b:
            grid([(b, f'Round 1: {t}'), (a, f'Round 2: {t}')], 2, half, f'before_after_{n}.jpg', 14)
    # the signs from the home view: the Glühwein and Bratwurst stands at 2x
    a, b = load(mk('market')), load(bf('market'))
    crop = (230, 360, 590, 540)
    if a:
        cells = ([(b.crop(crop), 'Round 1: home view, left stalls (2x)')] if b else []) + [(a.crop(crop), 'Round 2: home view, left stalls (2x)')]
        grid(cells, 1, (720, 360), 'home_signs.jpg', 14)
    # the two section signs from a visitor's approach (6.5-7.5 m in front of each stand, @cam=)
    g, w = load(mk('sign_glueh')), load(mk('sign_wurst'))
    if g and w:
        grid([(g, 'Glühwein stand, 6.5 m'), (w, 'Bratwurst stand, 7.5 m')], 2, half, 'market_signs.jpg', 14)

    # round 2, fix pass: the Ferris hub on the bench (?glb=/models/ferris.glb&tune=1&own=landmark), the
    # pass-3 settings against the hub fade and the farther wash, and the hub in the home view
    wb, wa = load(raw('wheel_before')), load(raw('wheel_after'))
    if wb and wa:
        box = (300, 60, 980, 600)
        grid([(wb.crop(box), 'Pass 3: wash 6.2 m out, hub bulbs full'), (wa.crop(box), 'Fix pass: wash 9.2 m out, hub bulbs fade')], 2, (640, 508), 'wheel_hub_bench.jpg', 14)
    p3 = load(os.path.join(OUT, 'raw_pass3', 'market.png'))
    if p3 and a:
        hub = (240, 120, 460, 300)
        grid([(p3.crop(hub), 'Pass 3: home view, hub (3x)'), (a.crop(hub), 'Fix pass: home view, hub (3x)')], 2, (640, 524), 'market_hub.jpg', 14)
    # baked AO in the glows and interior lamps, on the shipped Glühwein stall (the carpenter's AO map)
    ao0, ao1 = load(raw('ao_off')), load(raw('ao_on'))
    if ao0 and ao1:
        grid([(ao0, 'Shipped Glühwein stall: AO for hemisphere only'), (ao1, 'AO also in glows and interior lamps')], 2, half, 'ao_stall.jpg', 14)
        box = (420, 150, 1100, 330)
        grid([(ao0.crop(box), 'Bulb row, AO off in the glows'), (ao1.crop(box), 'Bulb row, AO on')], 1, (680, 180), 'ao_bulb_row.jpg', 14)


if __name__ == '__main__':
    main()
