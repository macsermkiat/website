"""Make the review JPEGs from the raw screenshots (shoot.mjs / shoot-market.mjs).

    python3 site/src/lighting/compose.py   # from the repo root
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RAW = os.environ.get('RAW') or os.path.join(ROOT, 'review/round-1/lighting/raw')
PASS1 = os.environ.get('PASS1')  # the pass-1 'after' PNG, for the pass-1 vs pass-2 sheet
PASS2 = os.environ.get('PASS2')  # a folder with the pass-2 'after.png' and 'lite.png', for the pass-3 sheets
PASS2_MARKET = os.environ.get('PASS2_MARKET')  # a folder with the pass-2 market_home*.jpg
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


def crops(cells, box, scale, out):
    w, h = box[2] - box[0], box[3] - box[1]
    sheet = Image.new('RGB', (w * scale * len(cells), h * scale), (8, 10, 18))
    for i, (name, text) in enumerate(cells):
        im = load(name)
        if im is None:
            continue
        im = im.resize((1280, 720), Image.LANCZOS).crop(box).resize((w * scale, h * scale), Image.LANCZOS)
        sheet.paste(label(im, text, 15), (i * w * scale, 0))
    sheet.save(os.path.join(OUT, out), quality=92)
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
if PASS1:
    grid([(REF, 'Cycles reference'), (PASS1, 'Pass 1'), ('after', 'Pass 2 (full)'), ('lite', 'Pass 2 (lite)')], 2, (640, 360), 'pass1_vs_pass2.jpg', 92)
    crops([(REF, 'Cycles'), (PASS1, 'Pass 1'), ('after', 'Pass 2'), ('lite', 'Pass 2 lite')], (620, 350, 800, 470), 2, 'pot_closeup.jpg')
    crops([(REF, 'Cycles'), (PASS1, 'Pass 1'), ('after', 'Pass 2')], (430, 200, 1030, 330), 1, 'bulbs_garland.jpg')
if PASS2:
    p2 = lambda n: os.path.join(PASS2, n + '.png')
    grid([(REF, 'Cycles reference'), (p2('after'), 'Pass 2 (full)'), ('after', 'Pass 3 (full)'), ('lite', 'Pass 3 (lite)')], 2, (640, 360), 'pass2_vs_pass3.jpg', 92)
    # the ground left of the stall: dashed streaks and the pale strip at the wall base (pass 2) against pass 3
    crops([(REF, 'Cycles'), (p2('after'), 'Pass 2: streaks, strip'), ('after', 'Pass 3')], (0, 540, 480, 720), 1, 'ground_artifacts.jpg')
    # the counter top on lite: rows of dots (pass 2, no MSAA) against pass 3 (2x MSAA)
    crops([(p2('lite'), 'Pass 2 lite: dots'), ('lite', 'Pass 3 lite')], (460, 425, 700, 485), 3, 'lite_counter.jpg')
    # the fascia and bulbs: pass 2 lit the board behind the bulbs to lightness 0.44 (Cycles 0.26)
    crops([(REF, 'Cycles'), (p2('after'), 'Pass 2'), ('after', 'Pass 3')], (430, 200, 1030, 330), 1, 'bulbs_garland.jpg')
    # the moon-side wall: near-black in Cycles; pass 2's rim lit it blue
    crops([(REF, 'Cycles'), (p2('after'), 'Pass 2'), ('after', 'Pass 3')], (300, 300, 480, 620), 1, 'left_wall.jpg')
if PASS2_MARKET:
    m2 = lambda n: os.path.join(PASS2_MARKET, n + '.jpg')
    grid([(m2('market_home'), 'Pass 2, full'), ('market', 'Pass 3, full'), (m2('market_home_snow'), 'Pass 2, snow'), ('market_snow', 'Pass 3, snow')], 2, (640, 360), 'market_pass2_vs_pass3.jpg', 90)
save('capture', 'after_capture.jpg', 'Full, ?capture=1 (environment captured from the scene)')
grid([('sky', 'Sky, full (bloom at full resolution)'), ('sky_lite', 'Sky, lite (half-resolution bloom, own weights)')], 2, (640, 360), 'bloom_full_vs_lite.jpg', 92)
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
