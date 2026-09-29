"""The Bücherstand's own texture atlas: spines, front covers, page edges and the open spread.

Every book on the stall is one node with one material, book_cover_<n>, that reads this atlas
(blender/out/vendor/books_*.png, shipped as prop_tex_books_*.webp). The spine and the front
cover of a book come from the same spec, so the cover the engine shows when a book is opened
matches the spine the visitor clicked.

Book metadata (display title and full author) lives here too, for items.json.
"""
import math

import numpy as np

import vendor_atlas as va
from vendor_atlas import Tex, fbm, fit_size, hexc, mix, shape_mask, smooth, text_mask

COVER_W, COVER_H = 160, 232

# Named books: spine region key -> (display title, author, subtitle for the cover)
NAMED_META = {
    "order_of_time": ("The Order of Time", "Carlo Rovelli", None),
    "geb": ("Gödel, Escher, Bach", "Douglas R. Hofstadter", "an Eternal Golden Braid"),
    "feynman_1": ("The Feynman Lectures on Physics, Vol. I", "Richard P. Feynman, Robert B. Leighton, Matthew Sands", None),
    "feynman_2": ("The Feynman Lectures on Physics, Vol. II", "Richard P. Feynman, Robert B. Leighton, Matthew Sands", None),
    "feynman_3": ("The Feynman Lectures on Physics, Vol. III", "Richard P. Feynman, Robert B. Leighton, Matthew Sands", None),
    "being_you": ("Being You", "Anil Seth", "A New Science of Consciousness"),
    "book_of_why": ("The Book of Why", "Judea Pearl and Dana Mackenzie", "The New Science of Cause and Effect"),
}

# Full author names for the generic shelf titles (the spines print the short form)
FULL_AUTHOR = {
    "Goethe": "Johann Wolfgang von Goethe", "Kant": "Immanuel Kant", "Nietzsche": "Friedrich Nietzsche",
    "Mann": "Thomas Mann", "Hesse": "Hermann Hesse", "Thoreau": "Henry David Thoreau", "Melville": "Herman Melville",
    "Newton": "Isaac Newton", "Aurelius": "Marcus Aurelius", "Abbott": "Edwin A. Abbott", "Hawking": "Stephen Hawking",
    "Rovelli": "Carlo Rovelli", "Feynman": "Richard P. Feynman", "Hofstadter": "Douglas R. Hofstadter",
    "Hofstadter & Dennett": "Douglas R. Hofstadter and Daniel C. Dennett", "Dennett": "Daniel C. Dennett",
    "Deutsch": "David Deutsch", "Kahneman": "Daniel Kahneman", "Pearl": "Judea Pearl",
    "Wittgenstein": "Ludwig Wittgenstein", "Kuhn": "Thomas S. Kuhn", "Sagan": "Carl Sagan", "Greene": "Brian Greene",
    "Nagel & Newman": "Ernest Nagel and James R. Newman", "Penrose": "Roger Penrose", "Schrödinger": "Erwin Schrödinger",
    "Prigogine": "Ilya Prigogine and Isabelle Stengers", "Jaynes": "E. T. Jaynes", "": "Brüder Grimm",
    "Kafka": "Franz Kafka", "Dawkins": "Richard Dawkins", "Eliot": "T. S. Eliot", "Nagel": "Thomas Nagel",
    "Damasio": "Antonio Damasio", "Spinoza": "Baruch de Spinoza", "Schopenhauer": "Arthur Schopenhauer",
}
FULL_AUTHOR_BY_TITLE = {"Surfaces and Essences": "Douglas R. Hofstadter and Emmanuel Sander"}


def book_meta(spine_key):
    """spine region key ('spine_geb', 'spine_g12') -> (title, author)."""
    k = spine_key.replace("spine_", "")
    if k in NAMED_META:
        return NAMED_META[k][:2]
    i = int(k[1:])
    title, short, _ = va.GENERIC_TITLES[i]
    return title, FULL_AUTHOR_BY_TITLE.get(title, FULL_AUTHOR.get(short, short))


# ------------------------------------------------------------ cover art
def _wrap(text, fn, wght, max_w, size, max_lines):
    """Greedy word wrap at the largest size (<= size) that fits max_lines lines of max_w px."""
    words = text.split()
    s = size
    while s > 6:
        f = va.font(fn, s * 3, wght)
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if f.getlength(trial) / 3 <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        lines.append(cur)
        if len(lines) <= max_lines and all(f.getlength(ln) / 3 <= max_w for ln in lines):
            return lines, s
        s -= 0.5
    return [text], s


def _text_block(w, h, text, fn, wght, size, max_w, y_mid, max_lines=4, lead=1.12):
    lines, s = _wrap(text, fn, wght, max_w, size, max_lines)
    rows = []
    n = len(lines)
    for i, ln in enumerate(lines):
        rows.append((ln, fn, s, wght, (w / 2, y_mid + (i - (n - 1) / 2) * s * lead), "mm"))
    return rows


def _frame(w, h, inset, width):
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    outer = (xx > inset) & (xx < w - 1 - inset) & (yy > inset) & (yy < h - 1 - inset)
    inner = (xx > inset + width) & (xx < w - 1 - inset - width) & (yy > inset + width) & (yy < h - 1 - inset - width)
    return (outer & ~inner).astype(float)


def _cover_base(w, h, seed, col, kind):
    t = va.spine_base(w, h, seed, col, kind)
    # boards wear at the corners and along the fore-edge (right); the spine hinge (left) is creased
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    corner = smooth(28, 0, np.minimum(np.hypot(w - xx, yy), np.hypot(w - xx, h - yy)))
    light = np.array(hexc("d8cdb8"))
    t.col = mix(t.col, light * 0.8, corner * (0.45 if kind != "paper" else 0.3))
    hinge = smooth(3, 0, np.abs(xx - 7))
    t.height = t.height - hinge * 0.6
    t.col = mix(t.col, t.col * 0.8, hinge * 0.5)
    return t


def g_cover(spec, meta, key):
    """Front cover for a spine spec. meta = (title, author, subtitle)."""
    title, author, sub = meta

    def f(w, h, seed):
        kind = spec["kind"]
        t = _cover_base(w, h, seed + 5, spec["col"], kind)
        ink = hexc(spec.get("ink", "d9b25e"))
        gilt = spec.get("gilt", False)
        metal, rough = (1.0, 0.35) if gilt else (0.0, 0.55)
        fn = spec.get("font", "garamond")
        wg = spec.get("wght", 600)
        rows = []
        if kind == "leather":
            t.paint(_frame(w, h, 9, 2), ink, rough, metal, -0.2)
            t.paint(_frame(w, h, 14, 1), ink, rough, metal, -0.2)
            lab = hexc(spec.get("label") or "6e1a1a")
            yy, xx = np.mgrid[0:h, 0:w].astype(float)
            panel = ((xx > w * 0.2) & (xx < w * 0.8) & (yy > h * 0.3) & (yy < h * 0.52)).astype(float)
            t.paint(panel, lab, 0.5, 0.0, 0.15)
            rows += _text_block(w, h, title, fn, wg, 20, w * 0.54, h * 0.41, 3)
        elif kind == "cloth":
            t.height = t.height - _frame(w, h, 10, 1.5) * 0.8          # blind-stamped panel
            rows += _text_block(w, h, title, fn, wg, 22, w * 0.72, h * 0.33, 4)
            if author:
                rows += _text_block(w, h, author.upper(), fn, 500, 11, w * 0.7, h * 0.8, 2)
        else:
            extra = spec.get("cover_extra")
            if extra:
                extra(t, w, h, seed)
            else:
                # a publisher's colour block across the lower third
                yy = np.mgrid[0:h, 0:w][0].astype(float)
                c2 = hexc(va.SPINE_COLS[(seed * 5 + 1) % len(va.SPINE_COLS)])
                t.paint(((yy > h * 0.64) & (yy < h * 0.7)).astype(float), c2, 0.45)
            rows += _text_block(w, h, spec["title"] if spec["title"].isupper() else title, fn, wg,
                                spec.get("cover_size", 26), w * 0.8, h * spec.get("cover_y", 0.34), 4)
            if sub:
                rows += _text_block(w, h, sub, "garamond", 500, 11, w * 0.76, h * spec.get("sub_y", 0.56), 2)
            if author:
                afn = spec.get("afont", fn)
                rows += _text_block(w, h, author.upper() if afn in ("oswald", "bebas", "josefin") else author,
                                    afn, 500, 12, w * 0.8, h * 0.86, 2)
        m = text_mask(w, h, rows)
        t.paint(m, ink, rough, metal, -0.15 if kind != "paper" else 0.0)
        return t
    return f


def _named_cover_extras():
    """Original cover graphics for the five reading-list titles (typographic, no publisher art)."""
    def order_of_time(t, w, h, seed):
        # a ring of clock ticks behind the title, and a warm band at the foot
        def ring(d, ss):
            cx, cy, r = w / 2, h * 0.36, w * 0.36
            for i in range(60):
                a = 2 * math.pi * i / 60
                l = 9 if i % 5 == 0 else 4
                d.line([((cx + r * math.cos(a)) * ss, (cy + r * math.sin(a)) * ss),
                        ((cx + (r - l) * math.cos(a)) * ss, (cy + (r - l) * math.sin(a)) * ss)],
                       fill=255, width=int(1.2 * ss))
        t.paint(shape_mask(w, h, ring) * 0.5, hexc("e5a33a"), 0.5)
        yy = np.mgrid[0:h, 0:w][0].astype(float)
        t.paint(((yy > h * 0.93) & (yy < h * 0.97)).astype(float), hexc("e5a33a"), 0.5)

    def geb(t, w, h, seed):
        yy = np.mgrid[0:h, 0:w][0].astype(float)
        t.paint(((yy > h * 0.04) & (yy < h * 0.12)).astype(float), hexc("9c1f24"), 0.5)

        def braid(d, ss):
            cx, cy = w / 2, h * 0.7
            for k in range(3):
                x = cx + (k - 1) * 18
                d.ellipse([(x - 12) * ss, (cy - 12) * ss, (x + 12) * ss, (cy + 12) * ss], outline=255, width=int(2 * ss))
        t.paint(shape_mask(w, h, braid), hexc("9c1f24"), 0.5)

    def being_you(t, w, h, seed):
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        t.paint(((yy > h * 0.93) & (yy < h * 0.97)).astype(float), hexc("e24a2a"), 0.5)
        r = np.hypot(xx - w / 2, yy - h * 0.34)
        t.paint(smooth(w * 0.34, w * 0.33, r) * smooth(w * 0.3, w * 0.31, r) * 0.8, hexc("f2c230"), 0.5)

    def book_of_why(t, w, h, seed):
        yy = np.mgrid[0:h, 0:w][0].astype(float)
        t.paint(((yy > h * 0.03) & (yy < h * 0.08)).astype(float), hexc("2a5aa8"), 0.5)

        def dag(d, ss):
            pts = [(w * 0.3, h * 0.68), (w * 0.7, h * 0.68), (w * 0.5, h * 0.76)]
            for (x0, y0), (x1, y1) in ((pts[0], pts[1]), (pts[0], pts[2]), (pts[1], pts[2])):
                d.line([(x0 * ss, y0 * ss), (x1 * ss, y1 * ss)], fill=255, width=int(1.5 * ss))
            for x, y in pts:
                d.ellipse([(x - 5) * ss, (y - 5) * ss, (x + 5) * ss, (y + 5) * ss], fill=255)
        t.paint(shape_mask(w, h, dag), hexc("2a5aa8"), 0.5)

    def feynman(t, w, h, seed):
        t.paint(_frame(w, h, 10, 1.5), hexc("e2bd6a"), 0.35, 1.0, -0.2)
    return {"order_of_time": order_of_time, "geb": geb, "being_you": being_you, "book_of_why": book_of_why,
            "feynman_1": feynman, "feynman_2": feynman, "feynman_3": feynman}


def named_cover_specs():
    specs = va.named_spines()
    extras = _named_cover_extras()
    out = {}
    for key, spec in specs.items():
        s = dict(spec)
        s["cover_extra"] = extras[key]
        if key == "being_you":
            s["sub_y"] = 0.7
        if key.startswith("feynman"):
            s["kind"] = "paper"            # print the lettering flat, then the frame is gilt
            s["title"] = "THE FEYNMAN LECTURES ON PHYSICS"
            s["cover_size"] = 20
            s["cover_y"] = 0.3
        title, author, sub = NAMED_META[key]
        if key.startswith("feynman"):
            sub = "Volume " + key.split("_")[1].replace("1", "I").replace("2", "II").replace("3", "III")
            author = "Feynman · Leighton · Sands"
        out[key] = (s, (title, author, sub))
    return out


# ------------------------------------------------------------ open spread, swatch
def g_book_swatch(w, h, seed):
    return Tex(w, h, (1, 1, 1), 0.5)


def books_specs():
    """[(name, w, h, generator)] for the books atlas."""
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    add("bk_satin", 16, 16, g_book_swatch)
    add("pages_edge", 256, 48, va.g_pages_edge)
    add("pages_open", 512, 352, va.g_pages_open)
    for key, (spec, meta) in named_cover_specs().items():
        add("spine_" + key, 80, 448, va.g_spine(va.named_spines()[key]))
        add("cover_" + key, COVER_W, COVER_H, g_cover(spec, meta, key))
    rng = np.random.default_rng(3)
    for i, (title, author, kind) in enumerate(va.GENERIC_TITLES):
        spec = va.generic_spine(i, title, author, kind, rng)
        add(f"spine_g{i}", 48, 304, va.g_spine(spec))
        full = FULL_AUTHOR_BY_TITLE.get(title, FULL_AUTHOR.get(author, author))
        add(f"cover_g{i}", COVER_W, COVER_H, g_cover(spec, (title, full, None), f"g{i}"))
    return R
