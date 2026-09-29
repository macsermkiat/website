"""Compare patch colours of a bench screenshot against the Cycles reference (same camera).

    python3 site/src/lighting/measure.py [review/round-1/lighting/raw/after.png ...]   # from the repo root
Prints mean sRGB, hue and saturation per patch, and the difference to the reference; then the bulb
row: the width of each bright run along it (luma > 200), and the mean luma of the band under it.
Bloom is sized in pixels, so compare 1280x720 frames only.
"""
import colorsys
import os
import sys
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
REF = os.path.join(ROOT, 'review/reference/gluehwein_preview.png')
# (x0, y0, x1, y1) on the 1280x720 frame
PATCHES = {
    'counter_top': (700, 455, 790, 461),
    'counter_front': (500, 480, 620, 488),
    'sign_board': (610, 548, 655, 585),
    'front_planks': (505, 550, 575, 605),
    'back_wall': (760, 300, 810, 360),
    'shelf_wall': (500, 350, 560, 390),
    'lambrequin': (560, 225, 700, 238),
    'roof_strip': (500, 130, 900, 200),  # the front of the roof over the bulbs
    'ground_beside': (950, 560, 1250, 640),  # the cobbles right of the stall, in its moon shadow
    'pot': (690, 395, 745, 435),
    'left_wall': (360, 420, 420, 520),
    'ground_left': (60, 520, 220, 600),
    'ground_right': (1050, 620, 1250, 700),
    'sky': (40, 60, 240, 160),
}


def stats(im, box):
    px = list(im.crop(box).get_flattened_data()) if hasattr(im, 'get_flattened_data') else list(im.crop(box).getdata())
    n = len(px)
    r, g, b = (sum(p[i] for p in px) / n for i in range(3))
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return (r, g, b), h * 360, s, l


def bulb_row(im):
    """Bright runs along the bulb row (luma > 200, the brightest row of y 235-262) and the band under it."""
    px = im.load()
    luma = lambda x, y: 0.2126 * px[x, y][0] + 0.7152 * px[x, y][1] + 0.0722 * px[x, y][2]
    row = [max(luma(x, y) for y in range(235, 262)) for x in range(440, 1010)]
    runs, start = [], None
    for i, v in enumerate(row + [0]):
        if v > 200 and start is None:
            start = i
        elif v <= 200 and start is not None:
            if i - start > 3:
                runs.append(i - start)
            start = None
    band = [luma(x, y) for y in range(262, 272) for x in range(460, 1000, 2)]
    return sorted(runs), sum(band) / len(band)


def main(paths):
    ref = Image.open(REF).convert('RGB').resize((1280, 720))
    ims = [(os.path.basename(p), Image.open(p).convert('RGB').resize((1280, 720))) for p in paths]
    for name, box in PATCHES.items():
        (r, g, b), h, s, l = stats(ref, box)
        line = f'{name:14s} ref ({r:5.1f},{g:5.1f},{b:5.1f}) h{h:5.1f} s{s:4.2f} l{l:4.2f}'
        for n, im in ims:
            (r2, g2, b2), h2, s2, l2 = stats(im, box)
            line += f' | {n[:10]} ({r2:5.1f},{g2:5.1f},{b2:5.1f}) h{h2:5.1f} s{s2:4.2f} l{l2:4.2f} dl{l2 - l:+.2f}'
        print(line)
    for n, im in [('reference', ref)] + ims:
        runs, band = bulb_row(im)
        print(f'bulbs {n[:12]:12s} {len(runs)} runs, widths {runs[:3]}..{runs[-3:]} median {runs[len(runs) // 2] if runs else 0}, widest {max(runs or [0])}; band under luma {band:.0f}')
    if os.environ.get('BOXES'):
        d = ImageDraw.Draw(ref)
        for name, box in PATCHES.items():
            d.rectangle(box, outline=(0, 255, 0))
            d.text((box[0], box[1] - 10), name, fill=(0, 255, 0))
        ref.save(os.environ['BOXES'])


if __name__ == '__main__':
    main(sys.argv[1:] or [os.path.join(ROOT, 'review/round-1/lighting/raw/after.png')])
