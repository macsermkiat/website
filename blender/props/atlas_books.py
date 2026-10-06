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

SPINE_PX_CM = (20, 14)        # px per cm across the spine (thickness) and along it (height); round 8: covers matter more
COVER_PX_CM = 22              # px per cm on the front cover (round 10: up from 15, so titles stay sharp at cam_cat)
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


def _lines(f, p, lw):
    """Anti-aliased lines where the scalar field f crosses multiples of p (lw px wide)."""
    d = np.mod(f, p)
    d = np.minimum(d, p - d)
    return smooth(lw * 0.5 + 0.6, lw * 0.5 - 0.4, d)


def _pattern(name, w, h, seed):
    """Round 8: the category's background pattern over the whole cover, as a mask (0..1)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    rg = np.random.default_rng(seed)
    u = w / 14.0                                      # about a centimetre
    if name == "orbits":                              # physics: tilted orbits round a star, and a starfield
        cx, cy = w * rg.uniform(0.6, 0.9), h * rg.uniform(0.12, 0.3)
        a = math.radians(rg.uniform(15, 35))
        dx, dy = xx - cx, yy - cy
        f = np.hypot(dx * math.cos(a) + dy * math.sin(a), (-dx * math.sin(a) + dy * math.cos(a)) * 2.4)
        m = _lines(f, 2.4 * u, 1.3) * smooth(w * 1.2, w * 0.2, f)
        for _ in range(int(w * h / 900)):
            x, y, r = rg.uniform(0, w), rg.uniform(0, h), rg.uniform(0.6, 1.6)
            m = np.maximum(m, smooth(r + 0.6, r - 0.4, np.hypot(xx - x, yy - y)))
        return m
    if name == "lattice":                             # lives: a fine diamond lattice with dots at the crossings
        p = 1.5 * u
        m = np.maximum(_lines(xx + yy, p, 1.0), _lines(xx - yy, p, 1.0))
        return m * 0.7
    if name == "ripples":                             # mind: ripples spreading from a corner
        x0, y0 = w * rg.uniform(-0.2, 0.1), h * rg.uniform(0.9, 1.15)
        f = np.hypot(xx - x0, yy - y0)
        return _lines(f, 1.25 * u, 1.2 + 0.6 * np.sin(f / (3 * u)) ** 2)
    if name == "circles":                             # people: rows of overlapping rings
        p = 2.0 * u
        row = np.floor(yy / (p * 0.75))
        lx = np.mod(xx + (row % 2) * p / 2, p) - p / 2
        ly = np.mod(yy, p * 0.75) - p * 0.375
        r = np.hypot(lx, ly)
        return smooth(1.4, 0.4, np.abs(r - p * 0.42))
    if name == "branches":                            # decisions: a faint grid and a branching decision tree
        g = np.maximum(_lines(xx, 1.2 * u, 0.8), _lines(yy, 1.2 * u, 0.8)) * 0.45

        def tree(d, s):
            def br(x, y, ln, ang, depth):
                if depth == 0:
                    return
                x1, y1 = x + ln * math.sin(ang), y - ln * math.cos(ang)
                d.line([(x * s, y * s), (x1 * s, y1 * s)], fill=255, width=max(1, int((0.6 + depth * 0.35) * s)))
                d.ellipse([(x1 - 2.2) * s, (y1 - 2.2) * s, (x1 + 2.2) * s, (y1 + 2.2) * s], fill=255)
                for sgn in (-1, 1):
                    br(x1, y1, ln * 0.7, ang + sgn * rg.uniform(0.35, 0.6), depth - 1)
            br(w * rg.uniform(0.35, 0.65), h * 1.02, h * 0.22, rg.uniform(-0.1, 0.1), 5)
        return np.maximum(g, shape_mask(w, h, tree))
    if name == "chevrons":                            # craft: stacked chevrons, like a woven strap
        p = 1.6 * u
        f = yy + np.abs(np.mod(xx, p) - p / 2)
        return _lines(f, p * 0.75, 1.6)
    return np.zeros((h, w))


# Round 10 (Mac, 2026-10-06: "Some of the book titles are hard to read"): the title owns the cover. One heavy
# condensed face for every title (Oswald 700, capitals), light on a dark panel or dark on a light one; the panel
# takes two thirds of the cover; long titles wrap onto up to six lines before the type shrinks, and a word too
# long for the panel at the minimum size breaks at a syllable (TITLE_HYPHEN) instead of shrinking further.
TITLE_FONT, TITLE_WGHT = "oswald", 700
AUTHOR_FONT, AUTHOR_WGHT = "oswald", 700
TITLE_MIN_CAP = 0.084         # smallest title cap height, as a fraction of the cover's height
TITLE_MAX_CAP = 0.15          # largest (a one-word title does not fill the panel edge to edge)
TITLE_MAX_LINES = 6
TITLE_LEAD = 1.06             # line pitch in em
PANEL_Y = (0.080, 0.755)      # title panel, top and bottom (fractions of the height, from the head)
AUTHOR_Y = (0.768, 0.872)     # the author's band (the cabinet's lip hides the cover below about 0.875)
HEAD_Y = 0.062                # the head band with the category's English name
# syllable breaks for the long words that would otherwise force a title below TITLE_MIN_CAP
TITLE_HYPHEN = {"SUPERCOMMUNICATORS": ("SUPER", "COMMUNI", "CATORS"), "CONVERSATIONS": ("CONVER", "SATIONS"),
                "CONVERSATION": ("CONVER", "SATION"), "HOSPITALITY": ("HOSPI", "TALITY"),
                "UNREASONABLE": ("UNREASON", "ABLE"), "ULTRALEARNING": ("ULTRA", "LEARNING"),
                "MISBEHAVIOR": ("MIS", "BEHAVIOR"), "ULTRA-PROCESSED": ("ULTRA", "PROCESSED"),
                "ANTIFRAGILE": ("ANTI", "FRAGILE"), "PROGRAMMER": ("PROGRAM", "MER"),
                "MECHANICS": ("MECHAN", "ICS"), "BOUNDARIES": ("BOUND", "ARIES"), "ALGORITHMS": ("ALGO", "RITHMS")}


def _cap(fn, wght):
    """Cap height of a face per px of font size."""
    f = va.font(fn, 200, wght)
    return -f.getbbox("H", anchor="ls")[1] / 200.0


def _best_lines(tokens, widths, space, max_w, max_lines):
    """Split tokens (with their widths at the reference size) into 1..max_lines lines; for each line count the
    split whose widest line is narrowest. tokens ending in '-' join the next without a space.
    Returns {n: (widest, [line strings])}."""
    n_tok = len(tokens)
    out = {}

    def width(i, j):
        w = 0.0
        for k in range(i, j):
            w += widths[k]
            if k < j - 1 and not tokens[k].endswith("-"):
                w += space
        return w

    def text(i, j):
        t = ""
        for k in range(i, j):
            t += tokens[k] + ("" if tokens[k].endswith("-") or k == j - 1 else " ")
        return t
    # dp[n][j]: (widest, cuts) for the first j tokens in n lines
    INF = float("inf")
    dp = [[(INF, None)] * (n_tok + 1) for _ in range(max_lines + 1)]
    dp[0][0] = (0.0, [])
    for n in range(1, max_lines + 1):
        for j in range(1, n_tok + 1):
            best = (INF, None)
            for i in range(n - 1, j):
                prev = dp[n - 1][i]
                if prev[1] is None:
                    continue
                w = max(prev[0], width(i, j))
                if w < best[0]:
                    best = (w, prev[1] + [(i, j)])
            dp[n][j] = best
        if dp[n][n_tok][1] is not None:
            out[n] = (dp[n][n_tok][0], [text(i, j) for i, j in dp[n][n_tok][1]])
    return out


def _tokens(text, hyphenate):
    toks = []
    for wd in text.split():
        core = wd.rstrip(",:;!?")
        parts = TITLE_HYPHEN.get(core) if hyphenate else None
        if parts:
            toks += [p + "-" for p in parts[:-1]] + [parts[-1] + wd[len(core):]]
        else:
            toks.append(wd)
    return toks


def _title_fit(text, fn, wght, box_w, box_h, cap_min_px, cap_max_px, max_lines=TITLE_MAX_LINES, lead=TITLE_LEAD):
    """The largest type that sets `text` in the box: (lines, size_px). More lines win over smaller type; a long
    word breaks at a syllable only when the unbroken setting would fall below cap_min_px."""
    capr = _cap(fn, wght)
    ref = 100.0
    f = va.font(fn, ref * 3, wght)
    space = f.getlength(" ") / 3

    def solve(hyph):
        toks = _tokens(text, hyph)
        widths = [f.getlength(t) / 3 for t in toks]
        best = None
        for n, (widest, lines) in _best_lines(toks, widths, space, box_w, max_lines).items():
            s_w = box_w / max(widest, 1e-6) * ref
            s_h = box_h / ((n - 1) * lead + capr)
            s = min(s_w, s_h, cap_max_px / capr)
            # prefer fewer lines unless more lines give clearly bigger type
            if best is None or s > best[1] * 1.04:
                best = (lines, s)
        return best
    lines, s = solve(False)
    if s * capr < cap_min_px and any(w.rstrip(",:;!?") in TITLE_HYPHEN for w in text.split()):
        l2, s2 = solve(True)
        if s2 > s * 1.08:
            lines, s = l2, s2
    # the largest size the real glyphs fit (the reference widths are measured, so this only trims rounding)
    while s > 6:
        g = va.font(fn, s * 3, wght)
        if all(g.getlength(ln) / 3 <= box_w for ln in lines):
            break
        s -= 0.25
    return lines, s


def _set_lines(lines, fn, wght, s, cx, y_mid, lead=TITLE_LEAD):
    """Rows for text_mask: lines centred on cx, the block's cap-height extent centred on y_mid."""
    capr = _cap(fn, wght)
    n = len(lines)
    block = (n - 1) * lead * s + capr * s
    base0 = y_mid - block / 2 + capr * s
    return [(ln, fn, s, wght, (cx, base0 + i * lead * s), "ms") for i, ln in enumerate(lines)]


def g_cover(b):
    """Round 10 (Mac, 2026-10-06): the title owns the cover. The category colour and pattern behind; at the head a
    narrow band with the category's English name; a solid title panel over two thirds of the cover with the title in
    heavy condensed capitals (light on dark, or dark on the people cabinet's cream), wrapped onto up to six lines
    before it shrinks and never below TITLE_MIN_CAP; under it the author in heavy capitals on their own band. The
    cabinet's lip hides the cover below about 0.875 of its height, so nothing is printed there. Original typography
    only, no publisher artwork."""
    def f(w, h, seed):
        t = _cover_base(w, h, seed + 5, b["col"], "paper")
        ink, acc, panel = hexc(b["ink"]), hexc(b["accent"]), hexc(b["panel"])
        pat = _pattern(b["motif"], w, h, seed + 11)
        t.paint(pat * 0.16, ink, None)
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        # head band with the category's English name
        hb = h * HEAD_Y
        t.paint((yy < hb).astype(float) * 0.92, panel, 0.5)
        t.paint(((yy > hb) & (yy < hb + max(1.5, h * 0.005))).astype(float), acc, 0.4)
        # the title panel, a thin accent frame just inside it
        x0, x1, y0, y1 = w * 0.04, w * 0.96, h * PANEL_Y[0], h * PANEL_Y[1]
        t.paint(((xx > x0) & (xx < x1) & (yy > y0) & (yy < y1)).astype(float) * 0.97, panel, 0.5)
        ins, lw = max(3.0, w * 0.014), max(1.2, w * 0.005)
        fr = ((xx > x0 + ins) & (xx < x1 - ins) & (yy > y0 + ins) & (yy < y1 - ins)) & \
            ~((xx > x0 + ins + lw) & (xx < x1 - ins - lw) & (yy > y0 + ins + lw) & (yy < y1 - ins - lw))
        t.paint(fr.astype(float) * 0.9, acc, 0.4)
        # the author's band
        a0, a1 = h * AUTHOR_Y[0], h * AUTHOR_Y[1]
        t.paint(((yy > a0) & (yy < a1) & (xx > x0) & (xx < x1)).astype(float) * 0.97, panel, 0.5)
        tink = ink
        # title
        bw = (x1 - x0) - 2 * (ins + lw) - w * 0.035
        bh = (y1 - y0) - 2 * (ins + lw) - h * 0.04
        lines, s = _title_fit(b["title"].upper(), TITLE_FONT, TITLE_WGHT, bw, bh, h * TITLE_MIN_CAP, h * TITLE_MAX_CAP)
        rows_t = _set_lines(lines, TITLE_FONT, TITLE_WGHT, s, w / 2, (y0 + y1) / 2)
        # author: one line if it keeps a decent size, else two
        acap = _cap(AUTHOR_FONT, AUTHOR_WGHT)
        al, as_ = _title_fit(b["author"].upper(), AUTHOR_FONT, AUTHOR_WGHT, (x1 - x0) * 0.92, (a1 - a0) * 0.76,
                             h * 0.034, h * 0.044, max_lines=2, lead=1.14)
        rows_a = _set_lines(al, AUTHOR_FONT, AUTHOR_WGHT, as_, w / 2, (a0 + a1) / 2, lead=1.14)
        # the category's English name at the head
        lab = b["label_en"].upper()
        ls = va.fit_size(lab, "oswald", h * 0.034 / _cap("oswald", 600), 600, w * 0.9)
        rows_l = _set_lines([lab], "oswald", 600, ls, w / 2, hb / 2)
        t.paint(text_mask(w, h, rows_t), tink, 0.5, 0.0, 0.05)
        t.paint(text_mask(w, h, rows_a), tink, 0.5, 0.0, 0.02)
        t.paint(text_mask(w, h, rows_l), acc, 0.45)
        t.cover_title = (lines, s * _cap(TITLE_FONT, TITLE_WGHT) / h)     # for the build's report
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
