"""Mac's 55 books for the Bücherstand: what each one is (from content/books/categories.json, the only source
for titles, authors, slugs and categories) and how its copy looks on the shelf (binding, size, colours, type).

Every book gets a fixed number nn (00..54) in the order of categories.json, so act_book_<nn> stays the same
book from build to build. The spine prints a short title and the author's surname(s); items.json carries the
full title and author, the slug and the category key.

The designs are original typographic spines and covers in the spirit of each book (colour, type style),
not reproductions of any publisher's artwork. Plain Python, no bpy (vendor_atlas / atlas_books use it).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CATEGORIES = os.path.join(REPO, "content", "books", "categories.json")

# Spine titles: the full title unless it is too long for one line; "\n" splits it over two lines.
SPINE_TITLE = {
    "the-many-hidden-worlds-of-quantum-mechanics": "The Many Hidden Worlds\nof Quantum Mechanics",
    "the-biggest-ideas-in-the-universe": "The Biggest Ideas\nin the Universe",
    "reality-is-not-what-it-seems": "Reality Is Not\nWhat It Seems",
    "mysteries-of-modern-physics-time": "Mysteries of Modern\nPhysics: Time",
    "something-deeply-hidden": "Something\nDeeply Hidden",
    "the-making-of-the-atomic-bomb": "The Making of\nthe Atomic Bomb",
    "surely-youre-joking-mr-feynman": "Surely You're Joking,\nMr. Feynman!",
    "what-do-you-care-what-other-people-think": "What Do You Care What\nOther People Think?",
    "the-laws-of-human-nature": "The Laws of\nHuman Nature",
    "mans-search-for-meaning": "Man's Search\nfor Meaning",
    "the-courage-to-be-happy": "The Courage\nto Be Happy",
    "the-courage-to-be-disliked": "The Courage\nto Be Disliked",
    "the-almanack-of-naval-ravikant": "The Almanack of\nNaval Ravikant",
    "unreasonable-hospitality": "Unreasonable\nHospitality",
    "set-boundaries-find-peace": "Set Boundaries,\nFind Peace",
    "how-to-know-a-person": "How to Know\na Person",
    "crucial-conversations": "Crucial\nConversations",
    "never-split-the-difference": "Never Split\nthe Difference",
    "unf-ck-your-boundaries": "Unf*ck Your\nBoundaries",
    "how-to-win-friends-and-influence-people": "How to Win Friends\n& Influence People",
    "stop-walking-on-eggshells": "Stop Walking\non Eggshells",
    "poor-charlies-almanack": "Poor Charlie’s\nAlmanack",
    "the-misbehavior-of-markets": "The Misbehavior\nof Markets",
    "algorithms-to-live-by": "Algorithms\nto Live By",
    "thinking-fast-and-slow": "Thinking,\nFast and Slow",
    "the-pragmatic-programmer": "The Pragmatic\nProgrammer",
    "ultra-processed-people": "Ultra-Processed\nPeople",
    "the-meaning-of-it-all": "The Meaning\nof It All",
    "on-the-origin-of-time": "On the Origin\nof Time",
}
# Spine authors where the automatic surname rule would read badly
SPINE_AUTHOR = {
    "crucial-conversations": "Grenny et al.", "framers": "Cukier et al.",
    "the-almanack-of-naval-ravikant": "Jorgenson", "ultra-processed-people": "van Tulleken",
    "cues": "Van Edwards", "captivate": "Van Edwards", "poor-charlies-almanack": "Munger",
    "what-do-you-care-what-other-people-think": "Feynman", "never-split-the-difference": "Voss",
    "the-misbehavior-of-markets": "Mandelbrot", "set-boundaries-find-peace": "Tawwab",
}

# slug -> (binding, (thickness, height, depth) cm, cover/spine colour, ink, font, accent colour, motif)
#   binding: "jacket" (hardback in a printed dust jacket), "paper" (paperback), "cloth" (cloth case, jacket lost,
#   gilt or ink stamping; the secondhand copies)
#   motif: the cover's graphic (atlas_books.MOTIFS)
D = {
    # physics
    "the-many-hidden-worlds-of-quantum-mechanics": ("paper", (2.4, 22.8, 15.2), "13233f", "e9e2cf", "josefin", "7fc4c9", "waves"),
    "the-biggest-ideas-in-the-universe": ("jacket", (2.8, 24.0, 16.2), "0e0e14", "f2ead8", "oswald", "e0a43a", "orbit"),
    "quanta-and-fields": ("jacket", (3.0, 24.0, 16.2), "1d3b6b", "f2ead8", "oswald", "e0a43a", "field"),
    "chaos": ("cloth", (3.4, 23.5, 15.5), "2b4a3a", "d9b25e", "baskerville", "d9b25e", "frame"),
    "reality-is-not-what-it-seems": ("paper", (2.2, 19.8, 12.9), "e8e1d0", "1b1b1b", "playfair", "b8322a", "rings"),
    "on-the-origin-of-time": ("jacket", (3.0, 24.0, 16.0), "1a1a22", "efc25a", "playfair", "efc25a", "spiral"),
    "mysteries-of-modern-physics-time": ("paper", (2.2, 22.8, 15.2), "6e1a22", "f4efe4", "garamond", "d9b25e", "clock"),
    "something-deeply-hidden": ("jacket", (3.2, 24.0, 16.0), "f1ece0", "1a1a1a", "bebas", "2f6fb0", "split"),
    "the-order-of-time": ("jacket", (2.4, 21.6, 14.5), "182a4f", "f3efe4", "oswald", "e5a33a", "clock"),
    "infinite-powers": ("jacket", (3.4, 24.0, 16.2), "f2efe6", "1c1c1c", "playfair", "c0392b", "curve"),
    # lives
    "elon-musk": ("jacket", (5.0, 24.2, 16.5), "f4f2ee", "111111", "bebas", "111111", "none"),
    "the-making-of-the-atomic-bomb": ("paper", (5.6, 23.4, 15.5), "1a1a1a", "e8d8b0", "garamond", "c8501e", "burst"),
    "the-meaning-of-it-all": ("cloth", (2.0, 21.0, 14.0), "7a2e2a", "d9b25e", "garamond", "d9b25e", "frame"),
    "einstein": ("cloth", (4.6, 24.0, 16.0), "1f2f52", "d9b25e", "cinzel", "d9b25e", "frame"),
    "surely-youre-joking-mr-feynman": ("paper", (2.6, 20.3, 13.5), "e2b23a", "1c1a18", "playfair", "a8261e", "bongo"),
    "what-do-you-care-what-other-people-think": ("paper", (2.4, 20.3, 13.5), "2e5f63", "f4efe4", "playfair", "e2b23a", "rings"),
    # mind
    "the-laws-of-human-nature": ("jacket", (5.0, 24.0, 16.0), "121212", "c9a45a", "cinzel", "c9a45a", "frame"),
    "mans-search-for-meaning": ("cloth", (2.0, 19.0, 12.5), "3b3f46", "e8dfc8", "garamond", "e8dfc8", "frame"),
    "grit": ("jacket", (3.0, 24.0, 16.0), "f3efe6", "1b1b1b", "bebas", "e2583a", "bar"),
    "how-to-be-bold": ("jacket", (2.8, 23.5, 15.8), "f2c230", "141414", "oswald", "141414", "bar"),
    "the-courage-to-be-happy": ("paper", (2.4, 21.0, 14.0), "f4f1ea", "1e1e1e", "josefin", "e8a33a", "sun"),
    "the-courage-to-be-disliked": ("paper", (2.4, 21.0, 14.0), "f4f1ea", "1e1e1e", "josefin", "3a8ac0", "sun"),
    "ultra-processed-people": ("jacket", (3.4, 24.0, 16.0), "e23a2a", "fbf6ea", "bebas", "fbf6ea", "dots"),
    "breath": ("jacket", (2.8, 24.0, 16.0), "e9f0f2", "1d3a4a", "josefin", "5aa0c8", "waves"),
    "the-almanack-of-naval-ravikant": ("paper", (2.0, 22.8, 15.2), "f2ede2", "1a1a1a", "playfair", "8a6a22", "none"),
    # people
    "unreasonable-hospitality": ("jacket", (3.0, 24.0, 16.0), "f3eee4", "1b1b1b", "playfair", "b8322a", "bar"),
    "six-minute-x-ray": ("paper", (2.4, 22.8, 15.2), "141414", "f2f2f2", "oswald", "d8282a", "grid"),
    "set-boundaries-find-peace": ("paper", (2.4, 21.6, 14.0), "f0d8c8", "2a2a2a", "josefin", "c86a4a", "arch"),
    "cues": ("paper", (2.6, 23.0, 15.2), "1e8a8a", "fbf6ea", "bebas", "f2c230", "dots"),
    "captivate": ("paper", (2.8, 23.0, 15.2), "f2f0ea", "c8282a", "bebas", "1b1b1b", "bar"),
    "how-to-know-a-person": ("jacket", (2.8, 24.0, 16.0), "e8a33a", "1a1a1a", "playfair", "1a1a1a", "none"),
    "crucial-conversations": ("paper", (2.4, 22.8, 15.2), "f2f0ea", "1a3a6a", "oswald", "e2583a", "bubble"),
    "the-next-conversation": ("jacket", (2.4, 21.6, 14.5), "f4f2ec", "1b1b1b", "oswald", "2a6ab0", "bubble"),
    "supercommunicators": ("jacket", (3.0, 24.0, 16.0), "f0b43a", "1b1b1b", "bebas", "1b1b1b", "waves"),
    "influence": ("cloth", (3.6, 23.5, 15.5), "1a3a5a", "e8dfc8", "baskerville", "e8dfc8", "frame"),
    "never-split-the-difference": ("paper", (2.6, 22.8, 15.2), "f4f2ec", "1b1b1b", "bebas", "c8282a", "split"),
    "unf-ck-your-boundaries": ("paper", (2.2, 17.8, 12.7), "2a2a2a", "f2c230", "bebas", "e05a8a", "none"),
    "how-to-win-friends-and-influence-people": ("cloth", (2.4, 21.0, 14.0), "5a1a1e", "d9b25e", "baskerville", "d9b25e", "frame"),
    "stop-walking-on-eggshells": ("paper", (3.0, 23.0, 15.2), "dfe8ee", "1d3a5a", "playfair", "5a8ac0", "rings"),
    # decisions
    "quit": ("jacket", (2.8, 24.0, 16.0), "f3efe6", "d8282a", "bebas", "1b1b1b", "none"),
    "poor-charlies-almanack": ("cloth", (4.2, 26.0, 19.0), "1e3a2a", "d9b25e", "cinzel", "d9b25e", "frame"),
    "the-misbehavior-of-markets": ("cloth", (2.8, 23.5, 15.5), "4a4f58", "e8dfc8", "garamond", "e8dfc8", "frame"),
    "antifragile": ("paper", (3.4, 23.0, 15.2), "f2f0ea", "1b1b1b", "garamond", "c8282a", "crack"),
    "the-black-swan": ("paper", (2.8, 23.0, 15.2), "141414", "f4f2ec", "garamond", "f4f2ec", "swan"),
    "algorithms-to-live-by": ("paper", (2.6, 21.6, 14.0), "f2f0ea", "1a1a1a", "josefin", "e2583a", "grid"),
    "framers": ("jacket", (2.6, 24.0, 16.0), "2a2a6a", "f2ead8", "oswald", "f2c230", "frame2"),
    "think-again": ("jacket", (2.6, 24.0, 16.0), "f4f2ec", "1b1b1b", "bebas", "2a8ac0", "arrow"),
    "calling-bullshit": ("jacket", (3.0, 24.0, 16.0), "f2c230", "1b1b1b", "oswald", "1b1b1b", "bar"),
    "thinking-fast-and-slow": ("paper", (3.6, 23.0, 15.2), "f4f2ec", "1b1b1b", "garamond", "c8282a", "pencil"),
    "the-book-of-why": ("jacket", (3.0, 24.0, 16.0), "f4f1ea", "161616", "josefin", "2a5aa8", "dag"),
    # craft
    "the-pragmatic-programmer": ("paper", (2.4, 23.5, 18.7), "1e2a3a", "f2ead8", "josefin", "e0a43a", "grid"),
    "clean-code": ("paper", (2.6, 23.5, 17.8), "f2efe6", "1a1a1a", "garamond", "2a6a4a", "bar"),
    "deep-work": ("jacket", (2.6, 21.6, 14.5), "f2efe6", "1b1b1b", "playfair", "1b1b1b", "none"),
    "atomic-habits": ("jacket", (2.6, 23.5, 15.5), "f4f2ec", "1b1b1b", "bebas", "e0a43a", "dots"),
    "ultralearning": ("jacket", (2.6, 24.0, 16.0), "e8eef2", "1a2a4a", "oswald", "e2583a", "arrow"),
}

LIGHT_COLS = {"e8e1d0", "f1ece0", "f2efe6", "f4f2ee", "f3efe6", "f4f1ea", "e9f0f2", "f2ede2", "f3eee4", "f2f0ea",
              "f4f2ec", "f0d8c8", "dfe8ee", "e8eef2", "e2b23a", "f2c230", "e8a33a", "f0b43a"}


def short_author(author):
    """'Judea Pearl and Dana Mackenzie' -> 'Pearl & Mackenzie'; 'Joseph Grenny et al.' -> 'Grenny et al.'."""
    a = author.replace(" et al.", "")
    parts = [p.strip() for p in a.replace(" and ", ",").split(",") if p.strip()]
    sur = []
    for p in parts:
        w = p.split()
        sur.append(w[-1] if w else p)
    s = " & ".join(sur)
    if "et al." in author:
        s += " et al."
    return s


def load():
    """[(nn, book)] with book = {title, author, slug, category, label_de, label_en, spine_title,
    spine_author, binding, dims (m), col, ink, font, accent, motif}, in categories.json order."""
    with open(CATEGORIES) as f:
        cats = json.load(f)["categories"]
    out = []
    nn = 0
    for c in cats:
        for b in c["books"]:
            slug = b["slug"]
            if slug not in D:
                raise KeyError(f"books_catalog: no design for {slug!r} (new book in categories.json?)")
            binding, (t, h, d), col, ink, fnt, acc, motif = D[slug]
            out.append((nn, dict(title=b["title"], author=b["author"], slug=slug, category=c["key"],
                                 label_de=c["label_de"], label_en=c["label_en"],
                                 spine_title=SPINE_TITLE.get(slug, b["title"]),
                                 spine_author=SPINE_AUTHOR.get(slug, short_author(b["author"])),
                                 binding=binding, dims=(t / 100, h / 100, d / 100), col=col, ink=ink, font=fnt,
                                 accent=acc, motif=motif, light=col in LIGHT_COLS)))
            nn += 1
    missing = set(D) - {b["slug"] for _, b in out}
    if missing:
        raise KeyError(f"books_catalog: designs for books not in categories.json: {sorted(missing)}")
    return out


def categories():
    with open(CATEGORIES) as f:
        return json.load(f)["categories"]


def key(nn):
    """Atlas key suffix for book nn: spine_b07 / cover_b07."""
    return f"b{nn:02d}"


if __name__ == "__main__":
    for nn, b in load():
        print(f"{nn:02d} {b['category']:9s} {b['binding']:6s} {b['spine_title']!r:48s} {b['spine_author']}")
