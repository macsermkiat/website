"""Bücherstand category cabinets: one source for the geometry (no bpy needed).

Round 8 (docs/adr/0004): the six categories in content/books/categories.json each get a glazed
cabinet with angled face-out boards. Two cabinets stand inside the hut's front, flanking the
counter; the other four stand in two short wings (two cabinets each) splayed out from the hut's
front corners under small shingled canopies. Each cabinet is sized for its category: up to five
covers per row, rows = ceil(books / 5), covers per row = ceil(books / rows) (people, 14 books:
three rows of five). buecher.py builds the cabinets, signs, doors and empties from this module,
and `python3 blender/stalls/buecher_sections.py` writes blender/stalls/buecher_sections.json for
the vendor, so the model and the json can not drift apart.

Coordinates are the stall's own Blender frame: metres, Z up, origin on the ground at the hut's
footprint centre, front (visitor side) toward -Y. Each cabinet has its own frame, which is the
frame of its slot_cat_<key> empty: +X runs along the boards from the visitor's left to right, -Y
points at the visitor (covers face -Y), +Z is up. The empty sits at the LEFT end of the LOWEST
face-out board, on the ledge's top surface, at the ledge's front edge (just behind its lip).
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CATEGORIES = os.path.join(REPO, "content", "books", "categories.json")
OUT_JSON = os.path.join(HERE, "buecher_sections.json")

HUT_W, HUT_D = 4.2, 2.5
Y_FRONT = -HUT_D / 2

# ---- covers and face-out boards
PER_ROW_MAX = 5
COVER_W, COVER_H, COVER_T = 0.145, 0.215, 0.035   # largest cover the boards take (w, h, thickness)
PITCH_X = 0.158                                   # cover centre spacing along a board
ROW_PITCH = 0.265                                 # vertical spacing of the face-out boards
TOP_ROW_Z = 1.36                                  # ledge top of the highest face-out board
LEAN_DEG = 15.0                                   # covers lean back against the backboard
LEDGE_D = 0.075                                   # ledge depth: lip inner face to backboard foot
LIP_H = 0.022                                     # lip height above the ledge top
SIDE_MARGIN = 0.02                                # board end to the first cover's edge
# ---- cabinet carcass
CAB_SIDE = 0.03                                   # side board thickness
CAB_DEPTH = 0.32                                  # outer depth, front face to back
CAB_TOP = 1.90                                    # top of the carcass (under the cornice)
GLASS_TOP = 1.86                                  # top of the glazed opening
SPINE_Z = 1.62                                    # spine board top (books at rest stand here as spines)
LEDGE_Y = 0.045                                   # lip front, behind the front face (door + rebate)
SIGN_H = 0.26                                     # crest sign on the cornice
SIGN_Z = 1.95                                     # sign bottom
GAP = 0.025                                       # between cabinets in a wing
# ---- wings
WING_PHI = math.radians(40.0)                     # angle between a wing's front line and the hut front
WING_ROOT = (2.38, Y_FRONT + 0.03)                # back corner of each wing's inner end (x mirrored left)
# ---- hut cabinets: front face protrudes in front of the hut front, outer side by the corner post
HUT_CAB_FRONT = Y_FRONT - 0.27
HUT_CAB_X = HUT_W / 2 - 0.1                        # outer side
# ---- close-up cameras: cam_cat_<key> on the cabinet's normal, framing its covers in 16:9
FOV_V = math.radians(42.0)
ASPECT = 16 / 9
CAM_FILL = 0.86

# Door hinge side per cabinet: each door opens 170 degrees and folds flat beside its cabinet, over a
# free side (open lane, the counter front or the neighbouring cabinet's door), so an open door never
# stands in its cabinet's cam_cat view and never cuts into another cabinet.
HINGE = {"lives": "left", "mind": "left", "physics": "right", "people": "left", "decisions": "right",
         "craft": "right"}
DOOR_OPEN_DEG = 170.0
DOOR_T = 0.022                                    # door frame thickness (in front of the carcass)

# visitor's left to right: left wing (outer, inner), hut left, hut right, right wing (inner, outer)
PLAN = [
    ("lives", "wing_l", 0),
    ("mind", "wing_l", 1),
    ("physics", "hut_l", 0),
    ("people", "hut_r", 0),
    ("decisions", "wing_r", 0),
    ("craft", "wing_r", 1),
]


def categories():
    with open(CATEGORIES) as f:
        return {c["key"]: c for c in json.load(f)["categories"]}


def layout(n):
    """(rows, covers per row) for n books: rows = ceil(n / 5), per row = ceil(n / rows)."""
    rows = max(1, math.ceil(n / PER_ROW_MAX))
    return rows, math.ceil(n / rows)


def board_width(per_row):
    return per_row * PITCH_X + 2 * SIDE_MARGIN


def cab_width(per_row):
    return board_width(per_row) + 2 * CAB_SIDE


def row_z(rows):
    """Ledge tops, lowest first."""
    return [round(TOP_ROW_Z - ROW_PITCH * (rows - 1 - i), 4) for i in range(rows)]


def glass_bottom(rows):
    """Bottom of the glazed opening (= top of the base cupboard)."""
    return round(row_z(rows)[0] - 0.07, 4)


def rot2(a, x, y):
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))


def to_stall(origin, a, x, y, z):
    px, py = rot2(a, x, y)
    return [round(origin[0] + px, 4), round(origin[1] + py, 4), round(z, 4)]


def cabinet_frames():
    """{key: (origin xy, rotation about Z, width)}: origin at the cabinet's front-left corner on
    the ground (visitor's view), +X along its width, +Y into it."""
    cats = categories()
    widths = {k: cab_width(layout(len(cats[k]["books"]))[1]) for k, _, _ in PLAN}
    out = {}
    for unit in ("wing_l", "wing_r"):
        keys = [k for (k, u, i) in sorted(PLAN, key=lambda t: t[2]) if u == unit]
        L = sum(widths[k] for k in keys) + GAP * (len(keys) - 1)
        if unit == "wing_l":
            a = WING_PHI                                  # +X runs from the outer end toward the hut
            rx, ry = -WING_ROOT[0], WING_ROOT[1]          # root = back corner at the inner (right) end
            dx, dy = rot2(a, L, CAB_DEPTH)
        else:
            a = -WING_PHI                                 # +X runs from the hut outward
            rx, ry = WING_ROOT
            dx, dy = rot2(a, 0.0, CAB_DEPTH)
        ox, oy = rx - dx, ry - dy                         # wing origin: front-left corner
        x = 0.0
        for k in keys:
            px, py = rot2(a, x, 0.0)
            out[k] = ((ox + px, oy + py), a, widths[k])
            x += widths[k] + GAP
    for k, u, _ in PLAN:
        if u == "hut_l":
            out[k] = ((-HUT_CAB_X, HUT_CAB_FRONT), 0.0, widths[k])
        elif u == "hut_r":
            out[k] = ((HUT_CAB_X - widths[k], HUT_CAB_FRONT), 0.0, widths[k])
    return out


def wing_units():
    """{unit: (origin, rotation, length)} of the two wings (front-left corner of the wing)."""
    fr = cabinet_frames()
    out = {}
    for unit in ("wing_l", "wing_r"):
        keys = [k for (k, u, i) in sorted(PLAN, key=lambda t: t[2]) if u == unit]
        o, a, _ = fr[keys[0]]
        L = sum(fr[k][2] for k in keys) + GAP * (len(keys) - 1)
        out[unit] = (o, a, L)
    return out


def cam_distance(w, h):
    """Distance at which a w x h area fills CAM_FILL of a 16:9 frame at the 42 degree vertical FOV."""
    t = math.tan(FOV_V / 2)
    return max(h / (2 * t * CAM_FILL), w / (2 * t * ASPECT * CAM_FILL))


def sections():
    """Every cabinet with its boards in its own (slot) frame and the slot in the stall frame."""
    cats = categories()
    frames = cabinet_frames()
    out = []
    for key, unit, idx in PLAN:
        c = cats[key]
        n = len(c["books"])
        rows, per = layout(n)
        origin, a, cw = frames[key]
        bw = board_width(per)
        zs = row_z(rows)
        slot_local = (CAB_SIDE, LEDGE_Y + 0.012, zs[0])          # behind the lip (12 mm thick)
        boards = []
        for i, z in enumerate(zs):
            cnt = per                                             # every board takes a full row
            boards.append({
                "index": i,
                "offset": [0.0, 0.0, round(z - zs[0], 4)],
                "width": round(bw, 4),
                "ledge_depth": LEDGE_D,
                "lean_deg": LEAN_DEG,
                "cover_slots_x": [round(SIDE_MARGIN + PITCH_X * (j + 0.5), 4) for j in range(cnt)],
                "clear_height": round((zs[i + 1] if i + 1 < rows else SPINE_Z - 0.03) - z - 0.03, 4),
            })
        spine = {"offset": [0.0, -0.012, round(SPINE_Z - zs[0], 4)], "width": round(bw, 4),
                 "depth": round(CAB_DEPTH - LEDGE_Y - 0.04, 4), "clear_height": round(GLASS_TOP - SPINE_Z - 0.01, 4)}
        # covers region (for the camera): all rows, cover tops included
        rw = per * PITCH_X
        top = zs[-1] + COVER_H * math.cos(math.radians(LEAN_DEG))
        rh = top - zs[0]
        tgt_local = (CAB_SIDE + bw / 2, LEDGE_Y + 0.04, zs[0] + rh / 2)
        d = cam_distance(rw, rh)
        cam_local = (tgt_local[0], tgt_local[1] - d, tgt_local[2] + 0.02)
        door_h = GLASS_TOP - glass_bottom(rows)
        side = HINGE[key]
        hinge_local = (CAB_SIDE if side == "left" else cw - CAB_SIDE, -DOOR_T - 0.001, glass_bottom(rows))
        open_deg = -DOOR_OPEN_DEG if side == "left" else DOOR_OPEN_DEG
        sign_local = (cw / 2, 0.02, SIGN_Z + SIGN_H / 2)
        out.append({
            "key": key,
            "label_de": c["label_de"],
            "label_en": c["label_en"],
            "books": n,
            "unit": unit,
            "kind": {"hut_l": "glazed cabinet in the hut front, left of the counter",
                     "hut_r": "glazed cabinet in the hut front, right of the counter",
                     "wing_l": "glazed cabinet in the left wing (%s)" % ("outer", "inner")[idx],
                     "wing_r": "glazed cabinet in the right wing (%s)" % ("inner", "outer")[idx]}[unit],
            "rows": rows,
            "covers_per_row": per,
            "capacity": rows * per,
            "cabinet": {"width": round(cw, 4), "depth": CAB_DEPTH, "height": CAB_TOP,
                        "origin": to_stall(origin, a, 0, 0, 0), "rotation_z_deg": round(math.degrees(a), 3),
                        "glass_bottom": glass_bottom(rows), "glass_top": GLASS_TOP},
            "slot": "slot_cat_" + key,
            "slot_position": to_stall(origin, a, *slot_local),
            "slot_rotation_z_deg": round(math.degrees(a), 3),
            "cover_max": {"width": COVER_W, "height": COVER_H, "thickness": COVER_T},
            "board_count": rows,
            "board_width": round(bw, 4),
            "board_spacing": ROW_PITCH,
            "boards": boards,
            "spine_board": spine,
            "door": {"node": "act_cab_" + key, "hinge_position": to_stall(origin, a, *hinge_local),
                     "hinge_side": side, "open_deg": open_deg,
                     "width": round(bw, 4), "height": round(door_h, 4),
                     "opens": "the glazed door swings outward (toward the visitor) about its hinge edge, the node's "
                              "origin (on the door's front face): rotate the node about its local vertical axis by "
                              "open_deg (Blender Z and three.js Y take the same sign; negative for a left hinge). Fully "
                              "open it folds flat beside the cabinet, out of the cam_cat view"},
            "sign": {"node": "sign_cat_" + key, "text": c["label_de"],
                     "center": to_stall(origin, a, *sign_local), "size": [round(cw - 0.03, 3), SIGN_H]},
            "cam": "cam_cat_" + key,
            "cam_position": to_stall(origin, a, *cam_local),
            "cam_target": "cam_cat_%s_target" % key,
            "cam_target_position": to_stall(origin, a, *tgt_local),
            "cam_distance": round(d, 3),
            "covers_area": [round(rw, 3), round(rh, 3)],
            "_local": {"origin": origin, "rot": a, "width": cw, "slot": slot_local, "sign": sign_local,
                       "rows": zs, "hinge": hinge_local, "per": per, "open_deg": open_deg},
        })
    return out


def build_doc():
    """The json document, built in memory from the plan (no file access except categories.json)."""
    secs = sections()
    doc = {
        "version": 2,
        "about": ("Bücherstand category cabinets (round 8, docs/adr/0004; owner: carpenter; built by "
                  "blender/stalls/buecher.py from blender/stalls/buecher_sections.py, so this file matches "
                  "stall_buecher.glb). One glazed cabinet per key in content/books/categories.json, with angled "
                  "face-out boards for up to five covers per row. The vendor parents prop_books_<key> to "
                  "slot_cat_<key>."),
        "frame": ("Positions are the stall's Blender frame (metres, Z up, origin on the ground at the footprint "
                  "centre, front toward -Y; three.js: x = x, y = z, z = -y). Each cabinet's frame is its slot "
                  "empty's frame: +X along the boards from the visitor's left to right, -Y toward the visitor "
                  "(covers face -Y), +Z up. slot_rotation_z_deg is that frame's rotation about Blender Z."),
        "slot": ("slot_cat_<key> sits at the LEFT end of the cabinet's LOWEST face-out board, on the ledge's top "
                 "surface, at its front edge (just behind the lip). Covers stand on a ledge, foot within "
                 "ledge_depth of the slot's y, and lean back lean_deg against the backboard; cover_slots_x are the "
                 "cover centres along +X. Boards are stacked board_spacing apart (offset = [x, y, z] of each board's "
                 "slot point). Above the top board, spine_board is a flat shelf for books at rest, as spines."),
        "door": ("act_cab_<key> is the cabinet's glazed door (frame + glass as child meshes), with its origin on "
                 "the hinge line (hinge_side edge, bottom corner, on the door's front face). The engine swings it "
                 "open by open_deg before the covers come forward."),
        "cam": ("cam_cat_<key> (cam_position) stands on the cabinet's normal and looks at cam_cat_<key>_target "
                "(cam_target_position), the centre of the covers area; at the site's 42 degree vertical field of "
                "view the covers area fills cam_fill of a 16:9 frame. Both are empties in stall_buecher.glb and "
                "stall_buecher.lite.glb; the camera empty is rotated to look at its target."),
        "cam_fill": CAM_FILL,
        "sections": [{k: v for k, v in s.items() if not k.startswith("_")} for s in secs],
        "units": {u: {"origin": [round(o[0], 4), round(o[1], 4)], "rotation_z_deg": round(math.degrees(a), 3),
                      "length": round(L, 4)} for u, (o, a, L) in wing_units().items()},
    }
    return doc


def write_json(path=OUT_JSON):
    doc = build_doc()
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return doc


def check_glb(path, json_path=OUT_JSON, tol=0.002):
    """Compare every slot_cat_<key>, cam_cat_<key>(_target) and act_cab_<key> node in a glb with
    buecher_sections.json. Returns a list of problems (empty = matches)."""
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
        for nk, pk in (("cam", "cam_position"), ("cam_target", "cam_target_position")):
            m = nodes.get(s[nk])
            if m is None:
                bad.append(f"{s[nk]} missing")
                continue
            tx, ty, tz = m.get("translation", [0, 0, 0])
            d = max(abs(tx - s[pk][0]), abs(-tz - s[pk][1]), abs(ty - s[pk][2]))
            if d > tol:
                bad.append(f"{s[nk]}: position off by {d:.4f} m")
            print(f"  {s[nk]:28s} {'ok' if d <= tol else 'MISMATCH'}")
        door = nodes.get(s["door"]["node"])
        if door is None:
            bad.append(f"{s['door']['node']} missing")
        else:
            tx, ty, tz = door.get("translation", [0, 0, 0])
            hp = s["door"]["hinge_position"]
            d = max(abs(tx - hp[0]), abs(-tz - hp[1]), abs(ty - hp[2]))
            kids = door.get("children", [])
            if d > tol or not kids:
                bad.append(f"{s['door']['node']}: hinge off by {d:.4f} m or no child meshes")
            print(f"  {s['door']['node']:28s} {'ok' if d <= tol and kids else 'MISMATCH'}  ({len(kids)} child meshes)")
    return bad


def check_json(json_path=OUT_JSON):
    """Compare buecher_sections.json with what this module would write, in memory (read-only).
    Returns a list of problems (empty = up to date)."""
    with open(json_path) as f:
        on_disk = json.load(f)
    fresh = json.loads(json.dumps(build_doc(), ensure_ascii=False))
    if on_disk == fresh:
        return []
    keys = [k for k in set(on_disk) | set(fresh) if on_disk.get(k) != fresh.get(k)]
    return [f"buecher_sections.json is out of date (differs in: {', '.join(sorted(keys))}); "
            f"run python3 blender/stalls/buecher_sections.py to rewrite it"]


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv[1:]:
        # read-only: compares the json with this module and every glb named (default: both
        # Bücherstand LODs) with the json. It never writes anything.
        paths = [p for p in sys.argv[1:] if p != "--check"] or [
            os.path.join(REPO, "site", "public", "models", n) for n in ("stall_buecher.glb", "stall_buecher.lite.glb")]
        problems = check_json()
        print("buecher_sections.json", "up to date" if not problems else "OUT OF DATE")
        for p in paths:
            print(os.path.basename(p))
            problems += check_glb(p)
        print("matches buecher_sections.json" if not problems else "PROBLEMS: " + "; ".join(problems))
        sys.exit(1 if problems else 0)
    d = write_json()
    for s in d["sections"]:
        print(f"{s['key']:10s} {s['label_de']:26s} {s['books']:3d} books  {s['rows']} x {s['covers_per_row']}"
              f"  cabinet {s['cabinet']['width']:.3f} m  slot {s['slot_position']} rotZ {s['slot_rotation_z_deg']}"
              f"  cam {s['cam_distance']:.2f} m")
    print("wrote", OUT_JSON)
