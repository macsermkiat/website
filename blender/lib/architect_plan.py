"""Architect's shared site plan, in Blender coordinates (Z-up; three.js z = -Blender y).

The square (plaza) outline, the ring street, the exits between houses and the house line are
defined here so square.py and town.py agree.  Stall placement lives in site/src/layout.json.
Angles are radians from +X counter-clockwise (Blender top view).  The home camera sits at
Blender (3, -33, 9) looking toward +Y.
"""
import math, json, os

LIB = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(LIB))
LAYOUT = os.path.join(REPO, "site", "src", "layout.json")

GUTTER_W = 0.5        # plaza-side gutter (Rinne)
STREET_W = 7.0        # ring street carriageway
CURB_S = 8.0          # curb line, measured outward from the plaza edge
SIDEWALK_Z = 0.07
HOUSE_MIN_R = 47.0


def plaza_r(t):
    """Irregular plaza edge radius (m) at angle t: about 70 m across."""
    return (36.0 + 1.2 * math.sin(2 * t + 0.5) + 0.7 * math.sin(3 * t + 1.9)
            + 0.4 * math.sin(5 * t + 0.3) + 0.25 * math.sin(7 * t + 2.2))


def sidewalk_w(t):
    return 2.3 + 0.7 * math.sin(3 * t + 0.8) + 0.4 * math.sin(4 * t + 2.0)


def house_r(t):
    """Front line of the houses."""
    return max(HOUSE_MIN_R, plaza_r(t) + CURB_S + 0.3 + sidewalk_w(t))


# exits: (centre angle in degrees, width in metres at the house line)
EXITS = [(40, 6.5), (101, 7.0), (147, 6.0), (200, 7.5), (247, 6.0), (304, 7.0), (352, 6.0)]
CHURCH_POS = (8.0, 56.0)          # Blender coords of three.js [8, -56]
CHURCH_HALF_ANGLE = math.radians(9.5)


def angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def exit_at(t, r=None, pad=0.0):
    """Return the exit index if angle t lies inside an exit opening (at radius r), else -1."""
    r = r or house_r(t)
    for i, (deg, w) in enumerate(EXITS):
        half = (w / 2 + pad) / r
        if abs(angdiff(t, math.radians(deg))) < half:
            return i
    return -1


def church_angle():
    return math.atan2(CHURCH_POS[1], CHURCH_POS[0])


def load_layout():
    with open(LAYOUT) as f:
        return json.load(f)


def layout_places():
    """[(id, kind, x_blender, y_blender, rot_z)] for every placed item with pos."""
    L = load_layout()
    out = []
    for p in L["places"]:
        x, z = p["pos"]
        out.append((p["id"], p["kind"], x, -z, p.get("rotY", 0.0), p))
    return out


# string-light poles (three.js [x, z]) and spans, from the prototype, extended for the wider market.
# Round 1 pass 2: the back-row poles 16 and 17 stand clear of the tree (6.5 m+ from its axis at
# [6.5, -15]), poles 7 and 8 behind the bandstand moved 0.9 m inward to clear it too, and the spans
# behind the tree are re-routed so no wire or bulb passes through the fir
# (see blender/square/check_clash.py, which tests every wire and bulb vertex against the fir's needles).
TREE_THREE = (6.5, -15.0)
POLES_THREE = [[-15, 4], [-7.5, 6.5], [0, 7.5], [7.5, 6.5], [15, 4], [-10.5, -6.5], [10.5, -6.5],
               [-2.6, -9.6], [2.6, -9.6], [-17.5, -3], [-17.5, 5], [-17.5, 13], [17.5, -3], [17.5, 5],
               [17.5, 13], [-7, -18], [0, -20], [12.2, -19.6]]
SPANS = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [4, 6], [5, 7], [7, 8], [8, 6], [1, 7], [3, 8], [2, 7],
         [2, 8], [1, 5], [3, 6], [9, 10], [10, 11], [12, 13], [13, 14], [9, 12], [11, 1], [14, 3],
         [10, 13], [5, 9], [6, 12], [15, 16], [16, 17], [15, 7], [16, 7], [15, 5], [17, 6]]
POLE_H = 6.4
# spans that carry a light_string_NN empty (the rest have bulbs only): the four crossings over the
# lanes in front of the section stalls and the bandstand first, then two back spans (lite keeps 3)
STRING_LIGHT_SPANS = [11, 12, 9, 10, 20, 21]
# ride footprints (half-sizes in the asset's frame, three.js x across and z front-to-back), from the
# ride builder's ferris.glb and carousel.glb bounding boxes; furniture keeps out of them
RIDE_HALF = {"riesenrad": (12.5, 5.6), "karussell": (6.4, 6.4), "bandstand": (4.5, 4.9)}
TREE_BENCH_R = 6.6          # the tree benches' distance from the fir's axis
TREE_CLEAR_R = 6.5          # no pole within this distance of the fir's axis


def in_ride(x_b, y_b, pad=0.5):
    """True if Blender point (x, y) lies inside a ride's or the bandstand's footprint (+pad)."""
    for p in load_layout()["places"]:
        half = RIDE_HALF.get(p["id"])
        if not half:
            continue
        dx, dy = x_b - p["pos"][0], y_b + p["pos"][1]
        c, s = math.cos(-p.get("rotY", 0)), math.sin(-p.get("rotY", 0))
        lx, lz = dx * c - dy * s, -(dx * s + dy * c)
        if abs(lx) < half[0] + pad and abs(lz) < half[1] + pad:
            return True
    return False
