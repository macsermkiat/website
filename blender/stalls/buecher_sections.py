"""Bücherstand category sections: one source for the geometry (no bpy needed).

The six categories in content/books/categories.json each get a labelled section on the
Bücherstand: two angled side racks ("wings", two bays each) that stand at the front corners and
two book carts in front of the glazed cabinets. buecher.py builds the boards, signs and the
slot_cat_<key> empties from this module, and `python3 blender/stalls/buecher_sections.py`
writes blender/stalls/buecher_sections.json for the vendor, so the model and the json can not
drift apart.

Coordinates are the stall's own Blender frame: metres, Z up, origin on the ground at the hut's
footprint centre, front (visitor side) toward -Y. Each section has its own frame, which is the
frame of its slot_cat_<key> empty: +X runs along the boards from the visitor's left to right,
-Y points at the visitor (spines face -Y), +Z is up. The empty sits at the LEFT end of the
LOWEST board, on the board's top surface, at its front edge.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CATEGORIES = os.path.join(REPO, "content", "books", "categories.json")
OUT_JSON = os.path.join(HERE, "buecher_sections.json")

MEAN_SPINE = 0.042        # mean book thickness used for the capacity figures (the vendor's books: 2-6 cm)
BOARD_T = 0.025           # board thickness
BOARD_D = 0.26            # usable board depth (the vendor's books are up to 0.22 deep)
UPRIGHT = 0.04            # rack uprights / dividers

# ---- side racks ("wings"): two bays each, standing at the hut's front corners, splayed 50 degrees
WING_PHI = math.radians(50.0)     # angle between a wing's back line and the hut front (X axis)
WING_DEPTH = 0.32                 # carcass depth, front face to the back of the back boards
WING_ROOT = (2.08, -1.08)         # back corner of each wing's inner end (x mirrored for the left wing)
WING_BOARDS = (0.42, 0.80)        # board top surfaces (z), lowest first
WING_TOP = 1.17                   # underside of the rack's top cap
BOARD_SET = 0.01                  # boards' front edge sits 1 cm behind the uprights' front

# ---- carts: two stepped tiers, front tier low, back tier high and further back
CART_FRONT_Y = -2.28              # front face of both carts (stall frame)
CART_X = 1.40                     # cart centre at x = -1.40 (left) and +1.40 (right)
CART_TIERS = ((0.62, 0.02), (0.92, 0.27))   # (board top z, board front edge y from the cart front)
CART_SIGN_Z = 1.31                # underside of the cart signs (clear height of the back tier)

# Section plan, visitor's left to right: left wing (two bays), left cart, right cart, right wing.
# Bay / board widths are sized from the book count (0.34 m + 2.2 cm a book, rounded) and leave
# about two to four times the shelf length the titled books need.
PLAN = [
    # key,        unit,     bay index, board width
    ("physics",   "wing_l", 0, 0.56),
    ("mind",      "wing_l", 1, 0.54),
    ("lives",     "cart_l", 0, 0.52),
    ("decisions", "cart_r", 0, 0.60),
    ("people",    "wing_r", 0, 0.65),
    ("craft",     "wing_r", 1, 0.45),
]


def categories():
    with open(CATEGORIES) as f:
        return {c["key"]: c for c in json.load(f)["categories"]}


def wing_bays(unit):
    return [(k, w) for (k, u, i, w) in sorted(PLAN, key=lambda t: t[2]) if u == unit]


def wing_length(unit):
    bays = wing_bays(unit)
    return UPRIGHT * (len(bays) + 1) + sum(w for _, w in bays)


def rot2(a, x, y):
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))


def wing_frame(unit):
    """(origin xy, rotation about Z) of a wing's frame: origin at the front face, left end
    (as the visitor sees it), on the ground; +X along the wing, -Y toward the visitor."""
    L = wing_length(unit)
    if unit == "wing_l":
        a = WING_PHI                     # +X runs from the outer end toward the hut
        rx, ry = -WING_ROOT[0], WING_ROOT[1]
        dx, dy = rot2(a, L, WING_DEPTH)  # the root is the back corner at the right (inner) end
    else:
        a = -WING_PHI                    # +X runs from the hut outward
        rx, ry = WING_ROOT
        dx, dy = rot2(a, 0.0, WING_DEPTH)
    return (rx - dx, ry - dy), a


def cart_width(unit):
    w = [w for (k, u, i, w) in PLAN if u == unit][0]
    return w + 2 * UPRIGHT


def cart_frame(unit):
    """Origin at the cart body's front-left corner on the ground; no rotation (faces -Y)."""
    W = cart_width(unit)
    cx = -CART_X if unit == "cart_l" else CART_X
    return (cx - W / 2, CART_FRONT_Y), 0.0


def to_stall(origin, a, x, y, z):
    px, py = rot2(a, x, y)
    return [round(origin[0] + px, 4), round(origin[1] + py, 4), round(z, 4)]


def sections():
    """Every section with its boards in its own (slot) frame and the slot in the stall frame."""
    cats = categories()
    out = []
    for key, unit, idx, bw in PLAN:
        c = cats[key]
        if unit.startswith("wing"):
            origin, a = wing_frame(unit)
            x0 = UPRIGHT
            for k, w in wing_bays(unit):
                if k == key:
                    break
                x0 += w + UPRIGHT
            slot_local = (x0, BOARD_SET, WING_BOARDS[0])
            tops = list(WING_BOARDS) + [WING_TOP]
            boards = []
            for i, z in enumerate(WING_BOARDS):
                boards.append({"index": i, "offset": [0.0, 0.0, round(z - WING_BOARDS[0], 4)],
                               "width": bw, "depth": BOARD_D,
                               "clear_height": round(tops[i + 1] - BOARD_T * (i + 1 < len(WING_BOARDS)) - z, 4)})
            sign_local = (x0 + bw / 2, -0.005, WING_TOP + 0.03 + 0.135)
            sign_size = (bw + 0.03, 0.24)
            kind = "side rack (%s wing, bay %d of 2 from the visitor's left)" % (
                "left" if unit == "wing_l" else "right", idx + 1)
        else:
            origin, a = cart_frame(unit)
            W = cart_width(unit)
            x0 = UPRIGHT
            (z0, y0), (z1, y1) = CART_TIERS
            slot_local = (x0, y0, z0)
            boards = [
                {"index": 0, "offset": [0.0, 0.0, 0.0], "width": bw, "depth": round(y1 - y0 - 0.01, 4),
                 "clear_height": None},
                {"index": 1, "offset": [0.0, round(y1 - y0, 4), round(z1 - z0, 4)], "width": bw,
                 "depth": round(y1 - y0 - 0.01, 4), "clear_height": round(CART_SIGN_Z - z1, 4)},
            ]
            sign_local = (W / 2, y1 + 0.21, CART_SIGN_Z + 0.12)
            sign_size = (W + 0.30, 0.24)
            kind = "book cart (%s of the counter)" % ("left" if unit == "cart_l" else "right")
        n = len(c["books"])
        length = sum(b["width"] for b in boards)
        out.append({
            "key": key,
            "label_de": c["label_de"],
            "label_en": c["label_en"],
            "books": n,
            "unit": unit,
            "kind": kind,
            "slot": "slot_cat_" + key,
            "slot_position": to_stall(origin, a, *slot_local),
            "slot_rotation_z_deg": round(math.degrees(a), 3),
            "board_count": len(boards),
            "board_width": bw,
            "board_depth": boards[0]["depth"],
            "board_thickness": BOARD_T,
            "board_spacing": round(boards[1]["offset"][2] - boards[0]["offset"][2], 4),
            "boards": boards,
            "capacity_at_mean_spine": int(length / MEAN_SPINE),
            "shelf_length_needed": round(n * MEAN_SPINE, 3),
            "sign": {"node": "sign_cat_" + key, "text": c["label_de"],
                     "center": to_stall(origin, a, *sign_local),
                     "size": [round(sign_size[0], 3), sign_size[1]]},
            "_local": {"origin": origin, "rot": a, "slot": slot_local, "sign": sign_local,
                       "sign_size": sign_size},
        })
    return out


def write_json(path=OUT_JSON):
    secs = sections()
    doc = {
        "version": 1,
        "about": ("Bücherstand category sections (owner: carpenter; built by blender/stalls/buecher.py from "
                  "blender/stalls/buecher_sections.py, so this file matches stall_buecher.glb). One section per "
                  "key in content/books/categories.json. The vendor parents prop_books_<key> to slot_cat_<key>."),
        "frame": ("Positions are the stall's Blender frame (metres, Z up, origin on the ground at the footprint "
                  "centre, front toward -Y; three.js: x = x, y = z, z = -y). Each section's frame is its slot "
                  "empty's frame: +X along the boards from the visitor's left to right, -Y toward the visitor "
                  "(spines face -Y), +Z up. slot_rotation_z_deg is that frame's rotation about Blender Z."),
        "slot": ("slot_cat_<key> sits at the LEFT end of the section's LOWEST board, on its top surface, at its "
                 "front edge. Books stand on +Z from there, run along +X for board width and reach back "
                 "(+Y) at most board depth."),
        "boards": ("offset is each board's [x, y, z] in the slot frame (same left end, front edge and top surface "
                   "convention). clear_height is the free height above a board's top surface (null = open above). "
                   "The cart's upper tier is stepped back (+Y) behind the lower tier's books."),
        "mean_spine": MEAN_SPINE,
        "sections": [{k: v for k, v in s.items() if not k.startswith("_")} for s in secs],
        "units": {
            "wing_l": {"length": round(wing_length("wing_l"), 3), "depth": WING_DEPTH,
                       "phi_deg": math.degrees(WING_PHI)},
            "wing_r": {"length": round(wing_length("wing_r"), 3), "depth": WING_DEPTH,
                       "phi_deg": math.degrees(WING_PHI)},
            "cart_l": {"width": round(cart_width("cart_l"), 3), "front_y": CART_FRONT_Y},
            "cart_r": {"width": round(cart_width("cart_r"), 3), "front_y": CART_FRONT_Y},
        },
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return doc


def check_glb(path, json_path=OUT_JSON, tol=0.002):
    """Compare every slot_cat_<key> node in a glb with buecher_sections.json (position and
    rotation about the vertical axis). Returns a list of problems (empty = matches)."""
    import sys
    sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
    import glb_tools
    js, _ = glb_tools.read_glb(path)
    nodes = {n.get("name"): n for n in js.get("nodes", [])}
    with open(json_path) as f:
        doc = json.load(f)
    bad = []
    for s in doc["sections"]:
        n = nodes.get(s["slot"])
        if n is None:
            bad.append(f"{s['slot']} missing")
            continue
        if s["sign"]["node"] not in nodes:
            bad.append(f"{s['sign']['node']} missing")
        tx, ty, tz = n.get("translation", [0, 0, 0])
        bx, by, bz = tx, -tz, ty                     # glTF (Y up) -> Blender (Z up)
        d = max(abs(bx - s["slot_position"][0]), abs(by - s["slot_position"][1]), abs(bz - s["slot_position"][2]))
        qx, qy, qz, qw = n.get("rotation", [0, 0, 0, 1])
        yaw = math.degrees(2 * math.atan2(qy, qw))   # rotation about glTF +Y = Blender +Z
        yaw = (yaw + 180) % 360 - 180
        dr = abs(yaw - s["slot_rotation_z_deg"])
        status = "ok" if d <= tol and dr < 0.2 else "MISMATCH"
        if status != "ok":
            bad.append(f"{s['slot']}: position off by {d:.4f} m, rotation {yaw:.2f} vs {s['slot_rotation_z_deg']}")
        print(f"  {s['slot']:22s} {status}  pos {[round(bx, 4), round(by, 4), round(bz, 4)]}  rotZ {yaw:.2f}")
    return bad


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        problems = []
        for p in sys.argv[2:]:
            print(os.path.basename(p))
            problems += check_glb(p)
        print("matches buecher_sections.json" if not problems else "PROBLEMS: " + "; ".join(problems))
        sys.exit(1 if problems else 0)
    d = write_json()
    for s in d["sections"]:
        print(f"{s['key']:10s} {s['label_de']:26s} {s['books']:3d} books  {s['board_count']} x {s['board_width']:.2f} m"
              f"  cap {s['capacity_at_mean_spine']:3d}  slot {s['slot_position']} rotZ {s['slot_rotation_z_deg']}")
    print("wrote", OUT_JSON)
