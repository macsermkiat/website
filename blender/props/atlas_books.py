"""The Bücherstand's own texture atlas: Mac's 55 books (spines and front covers), untitled filler spines,
page edges and the open guest book on the counter.

Every clickable book on the stall is one node with one material, book_cover_<nn>, that reads this atlas
(blender/out/vendor/books_*.png, shipped as prop_tex_books_*.webp). A book's spine (spine_b<nn>) and front
cover (cover_b<nn>) come from the same design (books_catalog), so the cover the engine shows when a book is
opened matches the spine the visitor clicked.

Region sizes follow each book's real proportions at one texel density (SPINE_PX_CM across and along the
spine, COVER_PX_CM on the cover), so no spine is stretched and every title reads at the same sharpness.
Round 3: the invented and borrowed stock titles of rounds 1-2 are gone; filler spines carry no text.
"""
import math

import numpy as np

import books_catalog
import vendor_atlas as va
from vendor_atlas import Tex, fbm, hexc, mix, shape_mask, smooth, text_mask

SPINE_PX_CM = (27, 20)        # px per cm across the spine (thickness) and along it (height)
COVER_PX_CM = 10              # px per cm on the front cover
N_FILLER = 18                 # untitled filler spines (not clickable, merged into each set's static mesh)
FILLER_PX = (40, 300)
SANS = ("oswald", "bebas", "josefin")


def book_meta(nn):
    """Book nn -> (title, author) as in categories.json."""
    b = dict(books_catalog.load())[nn]
    return b["title"], b["author"]


# ------------------------------------------------------------ spines
def spine_spec(b):
    """A g_spine spec for one book (vendor_atlas.g_spine draws it)."""
    fnt = b["font"]
    up = fnt in SANS
    title = b["spine_title"].upper() if up else b["spine_title"]
    author = b["spine_author"].upper() if up else b["spine_author"]
    two = "\n" in title
    acc = b["accent"]
    # layout along the spine (0 = head, 1 = foot): the title from near the head, the author's name before the
    # foot band; a long author name takes more length from the title
    aw = min(0.27, max(0.13, 0.0115 * len(author)))
    a_end = 0.91
    ax = a_end - aw / 2
    t0, t1 = 0.05, a_end - aw - 0.035
    tx, span = (t0 + t1) / 2, (t1 - t0)
    if b["binding"] == "cloth":
        light = b["col"] in ("e8dfc8", "d8c9a2", "b49a6a")
        return dict(col=b["col"], kind="cloth", gilt=not light and b["ink"] == "d9b25e", title=title, author=author,
                    font=fnt, wght=600, ink=b["ink"], x=tx, span=span, ax=ax, aw=aw, scale=1.0, afont=fnt)

    def extra(th, L, T, xx, yy):
        # the jacket's accent: a band at the foot, a publisher's mark inside it, and for some a head band
        th.paint(((xx > L * 0.935) & (xx < L * 0.975)).astype(float), hexc(acc), 0.45)
        m = smooth(T * 0.2, T * 0.16, np.hypot(xx - L * 0.955, yy - T * 0.5))
        th.paint(m, hexc(b["col"]), 0.45)
        if b["motif"] in ("bar", "split", "frame2", "grid"):
            th.paint(((xx > L * 0.02) & (xx < L * 0.04)).astype(float), hexc(acc), 0.45)
    return dict(col=b["col"], kind="paper", title=title, author=author, font=fnt,
                wght=700 if fnt in ("josefin", "playfair") else 600, ink=b["ink"], x=tx, span=span,
                ax=ax, aw=aw, afont="oswald" if up else fnt, extra=extra, rules=False, scale=1.0 if two else 0.92)


def g_filler(i):
    """An untitled filler spine: cloth with blind rules, leather with raised bands and a blank label, or a
    plain paper spine with a printed colour band. No lettering (filler books are not anyone's titles)."""
    cols = va.SPINE_COLS
    col = cols[(i * 7 + 3) % len(cols)]
    kind = ("cloth", "leather", "paper")[i % 3]
    if kind == "leather":
        col = ["5a3522", "3e2618", "6b2a1c", "2e2a22"][i % 4]

    def f(w, h, seed):
        L, T = h, w
        th = va.spine_base(L, T, seed, col, kind)
        xx = np.arange(L)[None, :] * np.ones((T, 1))
        yy = np.arange(T)[:, None] * np.ones((1, L))
        ink = hexc("c8a456" if kind != "paper" else cols[(i * 5 + 1) % len(cols)])
        if kind == "leather":
            for k in range(4):
                cx = L * (0.2 + 0.6 * k / 3)
                th.height += smooth(3.2, 0, np.abs(xx - cx)) * 1.2
                th.paint(smooth(0.8, 0, np.abs(np.abs(xx - cx) - 3.6)), ink, 0.4, 0.8)
            lab = ((np.abs(xx - L * 0.32) < L * 0.09) & (yy > T * 0.16) & (yy < T * 0.84)).astype(float)
            th.paint(lab, hexc(["6e1a1a", "1e1e1e", "25402a"][i % 3]), 0.5, 0.0, 0.2)
        elif kind == "cloth":
            for cx in (L * 0.06, L * 0.075, L * 0.925, L * 0.94):
                th.paint(smooth(0.9, 0.2, np.abs(xx - cx)), ink, 0.45, 0.6 if i % 2 else 0.0, 0.1)
            th.height -= smooth(0.9, 0.2, np.abs(xx - L * 0.45)) * 0.0
        else:
            th.paint(((xx > L * (0.82 + 0.02 * (i % 3))) & (xx < L * 0.95)).astype(float), ink, 0.45)
        t = Tex(w, h)
        t.col, t.rough = np.rot90(th.col, k=-1), np.rot90(th.rough, k=-1)
        t.metal, t.height = np.rot90(th.metal, k=-1), np.rot90(th.height, k=-1)
        t.hscale = 0.8
        return t
    return f, kind


def filler_kinds():
    return {f"spine_f{i}": ("cloth", "leather", "paper")[i % 3] for i in range(N_FILLER)}


# ------------------------------------------------------------ covers
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
    n = len(lines)
    return [(ln, fn, s, wght, (w / 2, y_mid + (i - (n - 1) / 2) * s * lead), "mm") for i, ln in enumerate(lines)]


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


def _motif(name, w, h, cy):
    """A cover graphic as a mask (0..1) centred at height cy. Simple original shapes, one per design."""
    cx = w / 2
    r = w * 0.26

    def draw(fn):
        return shape_mask(w, h, fn)
    if name == "waves":
        return draw(lambda d, s: [d.line([((x) * s, (cy + 6 * k + 4 * math.sin(x / w * 2 * math.pi * 2 + k)) * s)
                                          for x in range(0, w + 1, 2)], fill=255, width=int(1.6 * s)) for k in range(-3, 4)])
    if name == "orbit":
        return draw(lambda d, s: [d.ellipse([(cx - r * f) * s, (cy - r * f * 0.45) * s, (cx + r * f) * s,
                                             (cy + r * f * 0.45) * s], outline=255, width=int(1.4 * s))
                                  for f in (0.5, 0.8, 1.1)] + [d.ellipse([(cx - 5) * s, (cy - 5) * s, (cx + 5) * s,
                                                                          (cy + 5) * s], fill=255)])
    if name == "field":
        return draw(lambda d, s: [d.line([((cx - r * 1.2) * s, (cy + k * 5) * s), ((cx + r * 1.2) * s, (cy + k * 5 + 3 * math.sin(k)) * s)],
                                         fill=255, width=int(1.2 * s)) for k in range(-4, 5)])
    if name in ("rings", "sun"):
        out = draw(lambda d, s: [d.ellipse([(cx - r * f) * s, (cy - r * f) * s, (cx + r * f) * s, (cy + r * f) * s],
                                           outline=255, width=int(1.4 * s)) for f in (0.4, 0.7, 1.0)])
        if name == "sun":
            out = np.maximum(out, draw(lambda d, s: d.ellipse([(cx - r * 0.3) * s, (cy - r * 0.3) * s,
                                                               (cx + r * 0.3) * s, (cy + r * 0.3) * s], fill=255)))
        return out
    if name == "spiral":
        pts = [(cx + r * (t / 40) * math.cos(t * 0.45), cy + r * (t / 40) * math.sin(t * 0.45)) for t in range(41)]
        return draw(lambda d, s: d.line([(x * s, y * s) for x, y in pts], fill=255, width=int(1.5 * s)))
    if name == "clock":
        def f(d, s):
            for i in range(60):
                a = 2 * math.pi * i / 60
                ln = 8 if i % 5 == 0 else 3.5
                d.line([((cx + r * math.cos(a)) * s, (cy + r * math.sin(a)) * s),
                        ((cx + (r - ln) * math.cos(a)) * s, (cy + (r - ln) * math.sin(a)) * s)], fill=255, width=int(1.2 * s))
        return draw(f)
    if name == "split":
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        return ((yy > cy) & (yy < cy + h * 0.16)).astype(float)
    if name == "curve":
        pts = [(w * 0.15 + w * 0.7 * t / 30, cy + r - (r * 2) * (t / 30) ** 2) for t in range(31)]
        return draw(lambda d, s: d.line([(x * s, y * s) for x, y in pts], fill=255, width=int(2 * s)))
    if name == "burst":
        def f(d, s):
            for i in range(24):
                a = 2 * math.pi * i / 24
                d.line([(cx * s, cy * s), ((cx + r * 1.2 * math.cos(a)) * s, (cy + r * 1.2 * math.sin(a)) * s)],
                       fill=255, width=int(1.0 * s))
            d.ellipse([(cx - r * 0.3) * s, (cy - r * 0.3) * s, (cx + r * 0.3) * s, (cy + r * 0.3) * s], fill=255)
        return draw(f)
    if name == "bongo":
        return draw(lambda d, s: [d.ellipse([(cx + dx - r * 0.45) * s, (cy - r * 0.45) * s, (cx + dx + r * 0.45) * s,
                                             (cy + r * 0.45) * s], outline=255, width=int(2 * s)) for dx in (-r * 0.5, r * 0.55)])
    if name in ("bar", "frame2"):
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        m = ((yy > cy - 3) & (yy < cy + 3) & (xx > w * 0.15) & (xx < w * 0.85)).astype(float)
        return np.maximum(m, _frame(w, h, 8, 2)) if name == "frame2" else m
    if name == "dots":
        return draw(lambda d, s: [d.ellipse([(cx + i * 11 - 2.6) * s, (cy + j * 11 - 2.6) * s, (cx + i * 11 + 2.6) * s,
                                             (cy + j * 11 + 2.6) * s], fill=255) for i in range(-3, 4) for j in range(-1, 2)])
    if name == "grid":
        def f(d, s):
            for k in range(-3, 4):
                d.line([((cx + k * 9) * s, (cy - 27) * s), ((cx + k * 9) * s, (cy + 27) * s)], fill=255, width=int(1 * s))
                d.line([((cx - 27) * s, (cy + k * 9) * s), ((cx + 27) * s, (cy + k * 9) * s)], fill=255, width=int(1 * s))
        return draw(f)
    if name == "arch":
        return draw(lambda d, s: d.arc([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], 180, 360, fill=255,
                                       width=int(3 * s)))
    if name == "bubble":
        return draw(lambda d, s: [d.rounded_rectangle([(cx - r + dx) * s, (cy - r * 0.45 + dy) * s, (cx + r * 0.4 + dx) * s,
                                                       (cy + r * 0.2 + dy) * s], radius=int(6 * s), outline=255,
                                                      width=int(1.6 * s)) for dx, dy in ((0, 0), (r * 0.6, r * 0.55))])
    if name == "crack":
        pts = [(w * 0.2, cy - 10), (w * 0.38, cy + 3), (w * 0.5, cy - 6), (w * 0.62, cy + 8), (w * 0.8, cy - 2)]
        return draw(lambda d, s: d.line([(x * s, y * s) for x, y in pts], fill=255, width=int(1.6 * s)))
    if name == "swan":
        def f(d, s):
            d.ellipse([(cx - r * 0.7) * s, (cy) * s, (cx + r * 0.5) * s, (cy + r * 0.55) * s], fill=255)
            d.arc([(cx + r * 0.1) * s, (cy - r * 0.9) * s, (cx + r * 0.75) * s, (cy + r * 0.3) * s], 180, 330,
                  fill=255, width=int(3 * s))
        return draw(f)
    if name == "pencil":
        return draw(lambda d, s: d.line([((cx - r) * s, (cy + r * 0.3) * s), ((cx + r) * s, (cy - r * 0.3) * s)],
                                        fill=255, width=int(4 * s)))
    if name == "dag":
        def f(d, s):
            pts = [(w * 0.3, cy - 6), (w * 0.7, cy - 6), (w * 0.5, cy + 8)]
            for (x0, y0), (x1, y1) in ((pts[0], pts[1]), (pts[0], pts[2]), (pts[1], pts[2])):
                d.line([(x0 * s, y0 * s), (x1 * s, y1 * s)], fill=255, width=int(1.5 * s))
            for x, y in pts:
                d.ellipse([(x - 4.5) * s, (y - 4.5) * s, (x + 4.5) * s, (y + 4.5) * s], fill=255)
        return draw(f)
    if name == "arrow":
        def f(d, s):
            d.line([((cx - r) * s, cy * s), ((cx + r * 0.6) * s, cy * s)], fill=255, width=int(2.5 * s))
            d.polygon([((cx + r) * s, cy * s), ((cx + r * 0.5) * s, (cy - 7) * s), ((cx + r * 0.5) * s, (cy + 7) * s)], fill=255)
        return draw(f)
    return np.zeros((h, w))


def g_cover(b):
    """Front cover of one of Mac's books: cloth cases get a blind-stamped frame and stamped title and author;
    jackets and paperbacks a typographic layout with the design's motif in its accent colour."""
    def f(w, h, seed):
        cloth = b["binding"] == "cloth"
        kind = "cloth" if cloth else "paper"
        t = _cover_base(w, h, seed + 5, b["col"], kind)
        ink = hexc(b["ink"])
        gilt = cloth and b["ink"] == "d9b25e"
        metal, rough = (1.0, 0.35) if gilt else (0.0, 0.55)
        fn = b["font"]
        up = fn in SANS
        wg = 700 if fn in ("josefin", "playfair") else 600
        rows = []
        title, author = b["title"], b["author"]
        if cloth:
            t.height = t.height - _frame(w, h, 10, 1.5) * 0.8          # blind-stamped panel
            t.paint(_frame(w, h, 14, 1.0) * 0.6, ink, rough, metal, -0.2)
            rows += _text_block(w, h, title, fn, wg, 20, w * 0.7, h * 0.34, 4)
            rows += _text_block(w, h, author.upper(), fn, 500, 10, w * 0.7, h * 0.8, 2)
        else:
            m = _motif(b["motif"], w, h, h * 0.66)
            t.paint(m, hexc(b["accent"]), 0.45)
            rows += _text_block(w, h, title.upper() if up else title, fn, wg, 24, w * 0.8, h * 0.28, 4)
            rows += _text_block(w, h, author.upper() if up else author, "oswald" if up else fn, 500, 11, w * 0.8,
                                h * 0.87, 2)
        t.paint(text_mask(w, h, rows), ink, rough, metal, -0.15 if cloth else 0.0)
        return t
    return f


# ------------------------------------------------------------ the open guest book on the counter
GREETINGS = [
    ("Frohe Weihnachten aus Leipzig! Wir kommen wieder.", "caveat"),
    ("Danke für den Tipp mit dem Rovelli. A. & J.", "caveat"),
    ("Best Glühwein, best books. Merry Christmas!", "caveat"),
    ("Schöne Bescherung und ein gutes neues Jahr", "caveat"),
    ("Hier war Lena (7) mit Oma", "caveat"),
    ("Ein Buch ist ein Geschenk, das man immer wieder öffnen kann.", "caveat"),
    ("Grüße aus Bangkok! Merry Christmas from far away.", "caveat"),
    ("Für Mac: danke für die Empfehlung, K.", "caveat"),
]


def g_pages_open(w, h, seed):
    """Two-page spread of the bookseller's guest book: handwritten greetings in several inks on the left,
    a pressed paper star and a few more lines on the right. No printed book title anywhere."""
    from PIL import Image, ImageDraw
    t = Tex(w, h, hexc("efe6cf"), 0.9)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    t.col = mix(t.col, np.array(hexc("d9cba8")), smooth(0.04 * w, 0.0, np.abs(xx - w / 2)) * 0.6)   # gutter
    t.col = mix(t.col, np.array(hexc("d9cba8")), fbm(h, w, 60, seed) * 0.25)
    # faint ruled lines on both pages
    rule = (np.abs(((yy - h * 0.1) % 22) - 0) < 0.8) & (yy > h * 0.08) & (yy < h * 0.92)
    t.col = mix(t.col, np.array(hexc("b8c4d0")), rule * 0.35)
    inks = ["1f2f6a", "2a2420", "6a1a1a", "1f4a2a"]
    rngl = np.random.default_rng(seed)
    for i, (txt, fn) in enumerate(GREETINGS):
        page = 0 if i < 5 else 1
        x0 = w * (0.07 if page == 0 else 0.56)
        y = h * 0.1 + (i if page == 0 else i - 5) * 44 + 14
        im = Image.new("L", (w * 3, h * 3), 0)
        d = ImageDraw.Draw(im)
        f = va.font("caveat", 17 * 3, 500)
        words, line, ly = txt.split(), "", y
        for wd in words:
            if f.getlength(line + wd + " ") / 3 > w * 0.38:
                d.text((x0 * 3, ly * 3), line, fill=255, font=f)
                line, ly = "", ly + 20
            line += wd + " "
        d.text((x0 * 3, ly * 3), line, fill=255, font=f)
        m = np.asarray(im.resize((w, h), Image.LANCZOS), float) / 255.0
        t.paint(m * 0.92, hexc(inks[int(rngl.integers(len(inks)))]), 0.6)

    def star(d, s):
        cx, cy, R = w * 0.78, h * 0.78, h * 0.1
        pts = []
        for k in range(10):
            rr = R if k % 2 == 0 else R * 0.45
            a = -math.pi / 2 + k * math.pi / 5
            pts.append(((cx + rr * math.cos(a)) * s, (cy + rr * math.sin(a)) * s))
        d.polygon(pts, fill=255)
    t.paint(shape_mask(w, h, star) * 0.9, hexc("b8322a"), 0.6, height=0.3)
    t.height += fbm(h, w, 5, seed + 2) * 0.15
    return t


# ------------------------------------------------------------ swatch
def g_book_swatch(w, h, seed):
    return Tex(w, h, (1, 1, 1), 0.5)


def spine_px(b):
    t, h, _ = b["dims"]
    return max(40, round(t * 100 * SPINE_PX_CM[0])), round(h * 100 * SPINE_PX_CM[1])


def cover_px(b):
    _, h, d = b["dims"]
    return round(d * 100 * COVER_PX_CM), round(h * 100 * COVER_PX_CM)


def books_specs():
    """[(name, w, h, generator)] for the books atlas."""
    R = []
    add = lambda n, w, h, g: R.append((n, w, h, g))
    add("bk_satin", 16, 16, g_book_swatch)
    add("pages_edge", 256, 48, va.g_pages_edge)
    add("pages_open", 512, 352, g_pages_open)
    for nn, b in books_catalog.load():
        k = books_catalog.key(nn)
        add("spine_" + k, *spine_px(b), va.g_spine(spine_spec(b)))
        add("cover_" + k, *cover_px(b), g_cover(b))
    for i in range(N_FILLER):
        add(f"spine_f{i}", *FILLER_PX, g_filler(i)[0])
    return R


if __name__ == "__main__":
    import os
    import sys
    # quick look: render a few spines and covers to the scratch folder given as argv[1]
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
    from PIL import Image
    specs = books_specs()
    pick = [s for s in specs if s[0].startswith(("spine_b", "cover_b", "spine_f"))]
    for name, w, h, g in pick:
        tx = g(w, h, 7)
        Image.fromarray((np.clip(tx.col, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, name + ".png"))
    print(len(pick), "written to", out)
