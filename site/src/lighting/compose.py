"""Make the review JPEGs from the raw screenshots (shoot.mjs / shoot-market.mjs).

    python3 site/src/lighting/compose.py   # from the repo root
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RAW = os.path.join(ROOT, 'review/round-1/lighting/raw')
OUT = os.path.join(ROOT, 'review/round-1/lighting')
REF = os.path.join(ROOT, 'review/reference/gluehwein_preview.png')


def font(size):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def label(im, text, size=18):
    d = ImageDraw.Draw(im, 'RGBA')
    f = font(size)
    w = d.textlength(text, font=f)
    d.rectangle((8, 8, 8 + w + 16, 8 + size + 12), fill=(0, 0, 0, 150))
    d.text((16, 13), text, font=f, fill=(245, 230, 205, 255))
    return im


def load(name, size=None):
    p = name if os.path.isabs(name) else os.path.join(RAW, name + '.png')
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert('RGB')
    return im.resize(size, Image.LANCZOS) if size else im


def grid(cells, cols, cell, out, q=88):
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGB', (cell[0] * cols, cell[1] * rows), (8, 10, 18))
    for i, (name, text) in enumerate(cells):
        im = load(name, cell)
        if im is None:
            continue
        sheet.paste(label(im, text, 16), ((i % cols) * cell[0], (i // cols) * cell[1]))
    sheet.save(os.path.join(OUT, out), quality=q)
    print('wrote', out, sheet.size)


def save(name, out, text):
    im = load(name)
    if im is None:
        return
    if im.width > 1280:
        im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
    label(im, text).save(os.path.join(OUT, out), quality=90)
    print('wrote', out, im.size)


# the side-by-side against the Cycles reference (two 640x360 halves) and a full-width stack
grid([(REF, 'Cycles reference (AgX Punchy)'), ('after', 'three.js, lighting/index.js')], 2, (640, 360), 'side_by_side.jpg', 92)
stack = [(REF, 'Cycles reference'), ('after', 'three.js: lighting/index.js (full)')]
grid(stack, 1, (1280, 720), 'side_by_side_full.jpg', 90)
grid([('before', 'Before: engine stand-in lighting'), ('after', 'After: lighting/index.js')], 2, (640, 360), 'before_after.jpg', 92)
save('before', 'before.jpg', 'Before: engine stand-in lighting')
save('after', 'after.jpg', 'After: lighting/index.js (full)')
save('lite', 'after_lite.jpg', 'After: lite profile (4 lights, no shadows)')
save('snow', 'snow_on.jpg', 'setSnow(true)')
save('sky', 'sky_moon_stars.jpg', 'Sky: gradient, stars, clouds, haloed moon')
save('wide', 'wide.jpg', 'Wide: fog and ground mist')
grid([('wide', 'snow off'), ('wide_snow', 'snow on'), ('snow_lite', 'snow on, lite'), ('snow', 'snow on, close')], 2, (640, 360), 'snow_toggle.jpg', 90)
save('market', 'market_home.jpg', 'Market home view, full')
save('market_snow', 'market_home_snow.jpg', 'Market home view, snow on')
save('market_lite', 'market_home_lite.jpg', 'Market home view, lite')
