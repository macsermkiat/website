"""Check the vendor's prop sets against the build contract (plain Python, no bpy).

    python3 blender/props/check_props.py          (any Python 3; no third-party modules)

FAIL (exit 1):
- props.json lists every prop_*.glb with a stall, slot, full and lite file; all 19 sets exist
- required act_ nodes: >= 8 mugs, taps 0..2 pivoting at their base, glasses with foam, the grill and its
  swing, sausages riding the swing, books, 8-12 wine bottles, wine glasses, rolls
- no prop set adds a light_ empty (the stalls already carry their 2 or 1)
- every act_book_<n> has a book_cover_<n> material and its title and author in its node extras;
  act_ names are unique across all sets
- items.json names every act_ node of every set, and books carry title and author
- every set fits a 0.5 m deep counter or shelf, stands on the slot (z >= 0) and stays under the
  1.15 m front opening; clickable goods have their origin at their base
- every material except glass, liquids and emissives has a baked occlusion texture (TEXCOORD_1)
- section stall + its props <= 60k triangles with >= 2000 headroom (500 in round 6 pass 1), and <= 3 MB with shared textures
- deco stall + its goods <= 20k triangles and <= 1 MB counted as the stall glb + goods glb (the shared prop_tex_*
  textures load once for the market and are listed apart; round 8 pass 2)
- the full and lite glb of a set carry the same act_ nodes, at the same place, with the same extras
  (name, kind, title, author, cover_material), and items.json lists no act_ node a glb lacks
- seat check (blender/props/seat_check.mjs, node): no prop triangle cuts into its stall (counter,
  firebox, hearth plate, posts, braces, back boards) at its slot, and every set stays inside the y-range
  of the board it stands on (so nothing hangs past the counter's back edge)
- full / lite bounds parity: every act_ node's subtree (the node and everything under it) has the same
  world bounding box in the lite glb as in the full glb within 1 cm, and every named mesh node within 2 cm
  (so a lite simplification that changes the shape, e.g. a foam head growing into a column, fails)
- round 8 (ADR 0004): every deco stall <= 20k with its goods and no act_ nodes (scenery since 2026-10-05).
- round 9 (ADR 0004 revision): the ornament shop (stall_schmuck.glb) <= 60k triangles and 3 MB with its goods
  and their shared textures; exactly three interactive groups: act_orn_harmonica_0..11 in one row (left to
  right, one level), act_orn_mirrorball with cam_dive / cam_dive_target, act_orn_schwibbogen with
  act_orn_candle_0..6; no other act_orn_ node and no items.json entry for anything else in the shop; rot_pyramid,
  at least two tinsel_<n> meshes, fx_smoke_1 and a bulb_warm (the Herrnhut stars) present.
  Sets with a 'seat' of hang / stand / ground skip the board y-range test (collisions are still tested).
WARN (listed, exit 0): lite versions above 38 % of the full triangles (target about a third).

    python3 blender/props/check_props.py --notes   also rewrites the budget tables in
                                                   review/round-9/vendor/NOTES.md from the current glbs
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
import glb_tools  # noqa: E402

MODELS = os.path.join(REPO, "site", "public", "models")
REPORT = os.path.join(REPO, "blender", "out", "props_report.json")
SECTION = {"gluehwein": "stall_gluehwein", "bierstand": "stall_bier", "bratwurst": "stall_bratwurst",
           "buecherstand": "stall_buecher"}
CATEGORIES = os.path.join(REPO, "content", "books", "categories.json")
with open(CATEGORIES) as _f:
    BOOK_CATS = json.load(_f)["categories"]
SECTION_SETS = ["prop_gluehwein_counter", "prop_gluehwein_shelf", "prop_gluehwein_wine", "prop_bier_counter",
                "prop_bier_back", "prop_bier_shelf", "prop_wurst_counter", "prop_books_shelf_1", "prop_books_shelf_2",
                "prop_books_counter"] + [f"prop_books_{c['key']}" for c in BOOK_CATS]
# BUILD.md: the Bücherstand with all its props may use 80k triangles and 4 MB; the other section stalls 60k / 3 MB
STALL_BUDGET = {"buecherstand": (80000, 4.0)}
DECO_KEYS = ["lebkuchen", "mandeln", "kerzen", "spielzeug", "schmuck", "kaese", "crepes", "maroni", "puffer"]
FILL_KEYS = [d for d in DECO_KEYS if d != "schmuck"]
SCHMUCK_SETS = [f"prop_schmuck_{g}" for g in ("harmonica", "mirrorball", "pyramid", "garland", "tinsel_1", "tinsel_3",
                                               "rail_2", "rail_3", "rail_4", "counter", "shelf", "case", "tree")]
SCHMUCK_TRIS, SCHMUCK_MB = 60000, 3.0         # BUILD.md round 9: the ornament shop with its goods
# BUILD.md: a deco stall with its goods <= 1 MB. Round 8 pass 2 (judges): counted as the stall glb plus its own
# goods glb only; the shared prop textures (prop_tex_*) load once for the whole market, so they are reported in
# their own column and not charged to every stall (the ornament shop still counts them, the stricter reading)
DECO_MB = 1.0
NO_AO = ("vendor_glass", "flame", "lamp_glow", "bulb_warm", "coal_glow", "vendor_beer", "vendor_liquid", "vendor_lamp_shade",
         "write_", "vendor_mercury", "vendor_gloss", "tinsel")
BASE_PIVOT = re.compile(r"^act_(mug|glass|bottle|wineglass|book|roll|tap|served|sausage|coaster)_\d+$|^act_grill$"
                        r"|^act_writing_paper$")
# round 6 pass 2 (judges): back to 2k of headroom under each section stall's 60k, after trimming the props
# (round 6 pass 1 had dropped it to 500 when the carpenter's stalls grew by about 1.7k each)
HEADROOM, SECTION_TRIS, SECTION_MB, DECO_TRIS = 2000, 60000, 3.0, 20000
LITE_RATIO = 0.38
ACT_BBOX_TOL, MESH_BBOX_TOL = 0.01, 0.02          # m: full vs lite bounds of act_ subtrees / mesh nodes
NOTES = os.path.join(REPO, "review", "round-9", "vendor", "NOTES.md")
SEAT = os.path.join(HERE, "seat_check.mjs")

fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print("  FAIL", msg)


def warn(msg):
    warns.append(msg)
    print("  WARN", msg)


def acts(nodes, prefix):
    return sorted((n for n in nodes if re.match(rf"^{prefix}\d+$", n)), key=lambda n: int(n.rsplit("_", 1)[1]))


def is_act(n):
    """An action node the engine sees: act_x, not its geometry child act_x_mesh (engine/conventions.js)."""
    return n.startswith("act_") and not n.endswith("_mesh")


def uris(path):
    js, _ = glb_tools.read_glb(path)
    return {im["uri"] for im in js.get("images", []) if im.get("uri")}


def parents(js):
    out = {}
    for i, nd in enumerate(js.get("nodes", [])):
        for c in nd.get("children", []):
            out[js["nodes"][c].get("name")] = nd.get("name")
    return out


def check_nodes(name, js, nodes):
    par = parents(js)
    lights = [n for n in nodes if n.startswith("light_")]
    if lights:
        fail(f"{name}: adds light_ empties {lights} (the stall has its own)")
    need = {
        "prop_gluehwein_counter": lambda: len(acts(nodes, "act_mug_")) >= 8 and "act_pot_lid" in nodes,
        "prop_gluehwein_wine": lambda: 8 <= len(acts(nodes, "act_bottle_")) <= 12 and acts(nodes, "act_wineglass_"),
        "prop_bier_counter": lambda: all(f"act_tap_{i}" in nodes for i in range(3)) and acts(nodes, "act_glass_")
        and all(par.get(f"foam_{g.rsplit('_', 1)[1]}") == g for g in acts(nodes, "act_glass_")),
        "prop_wurst_counter": lambda: "act_grill" in nodes and "act_grill_swing" in nodes
        and acts(nodes, "act_sausage_") and acts(nodes, "act_roll_"),
    }
    for c in BOOK_CATS:
        need[f"prop_books_{c['key']}"] = (lambda c=c: len(acts(nodes, "act_book_")) == len(c["books"]))
    if name in need and not need[name]():
        fail(f"{name}: required act_ nodes missing")
    if name == "prop_wurst_counter":
        on_grate = [n for n in acts(nodes, "act_sausage_") if par.get(n) == "act_grill_swing"]
        if len(on_grate) < 8:
            fail(f"{name}: only {len(on_grate)} sausages are children of act_grill_swing")
    mats = set(m.get("name") for m in js.get("materials", []))
    extras = {nd.get("name"): nd.get("extras") or {} for nd in js.get("nodes", [])}
    for b in acts(nodes, "act_book_"):
        if f"book_cover_{b.rsplit('_', 1)[1]}" not in mats:
            fail(f"{name}: {b} has no book_cover material")
        if not (extras[b].get("title") and extras[b].get("author")):
            fail(f"{name}: {b} carries no title/author in its node extras")


def check_ao(name, js):
    for m in js.get("materials", []):
        mn = m.get("name", "")
        if mn.startswith(NO_AO):
            continue
        occ = m.get("occlusionTexture")
        if not occ or occ.get("texCoord") != 1:
            fail(f"{name}: material {mn} has no occlusion texture on TEXCOORD_1")
            return


SCENERY_FULL, SCENERY_LITE = 4000, 1500


def check_scenery(name, js, nodes, variant):
    """Round 8 (Mac, 2026-10-05): a deco stall's goods are one or two merged meshes, no act_ / fx_ nodes, at
    most about 4k triangles (1.5k lite)."""
    bad = [n for n in nodes if n.startswith(("act_", "fx_", "light_"))]
    if bad:
        fail(f"{name}: scenery carries {bad[:5]}")
    meshes = [n for n in js["nodes"] if "mesh" in n]
    if len(meshes) > 2:
        fail(f"{name}: {len(meshes)} mesh nodes (scenery is one or two merged meshes)")
    tris = glb_tools.triangle_count(js)
    cap = SCENERY_FULL if variant == "full" else SCENERY_LITE
    if tris > cap * 1.05:
        fail(f"{name}: {tris} triangles (> about {cap})")


def check_geometry(name, r, seat="board"):
    size, lo, hi = r.get("size"), r.get("bbox_min"), r.get("bbox_max")
    if not size:
        fail(f"{name}: no bounding box in props_report.json (rebuild)")
        return
    if seat == "hang":
        # round 8: ornaments hang under a rail (clip-on birds sit on it)
        if hi[2] > 0.1:
            fail(f"{name} reaches {hi[2]:.3f} m above its rail")
    elif seat in ("stand", "ground"):
        if lo[2] < -0.002:
            fail(f"{name} reaches {lo[2]:.3f} m below its slot")
        if hi[2] > 1.45 + 1e-3:
            fail(f"{name} is {hi[2]:.3f} m tall (> 1.45)")
    elif seat == "span":
        # round 8 scenery: one set at slot_counter reaching the crate bench (0.71 m below, 0.5 m in front), the
        # rail (0.97 m above) and both back shelves (1.96 m behind); it must stay inside the hut's opening
        if lo[2] < -0.72 or hi[2] > 1.16 or lo[1] < -0.73 or hi[1] > 2.095:
            fail(f"{name}: scenery reaches outside the hut (bbox {lo} .. {hi})")
    elif size[1] > 0.5 + 1e-3:
        fail(f"{name} is {size[1]:.3f} m deep (> 0.5)")
    floor = r.get("grill_seat", {}).get("floor_z")
    if seat != "board":
        pass
    elif floor is not None and lo[2] < floor - 0.002:
        fail(f"{name} reaches {lo[2]:.3f} m, below the grill opening's deck at {floor:.3f}")
    elif floor is None and lo[2] < -0.002:
        fail(f"{name} reaches {lo[2]:.3f} m below its slot")
    if seat == "board" and hi[2] > 1.15 + 1e-3:
        fail(f"{name} is {hi[2]:.3f} m tall (front opening is 1.15)")
    for node, p in r.get("pivots", {}).items():
        # rest_min_z: lowest point of the node's geometry above its origin, measured along world Z, so an
        # upside-down mug (rotated node) whose origin is on its rim counts as based correctly
        z = p.get("rest_min_z", p["local_min"][2])
        if BASE_PIVOT.match(node) and not (-0.004 <= z <= 0.004):
            fail(f"{name}: {node} pivot is not at its base (geometry starts at z {z:+.3f})")
        # round 4: deco goods. "base" items rest on their origin; "hang" items have it at the ribbon's knot on
        # the rod (nothing but the knot above it, everything else below)
        it = r.get("items", {}).get(node, {})
        if it.get("kind") == "deco":
            pv = str(it.get("pivot", "base"))
            if pv == "base" and not (-0.004 <= z <= 0.004):
                fail(f"{name}: {node} pivot is not at its base (geometry starts at z {z:+.3f})")
            if pv.startswith("hang") and not (0.0 <= p["local_max"][2] <= 0.012 and p["local_min"][2] < -0.05):
                fail(f"{name}: {node} does not hang from its origin (z {p['local_min'][2]:+.3f}..{p['local_max'][2]:+.3f})")
            if not it.get("detail"):
                fail(f"{name}: {node} has no detail line for the engine's tag")


def act_nodes(js):
    """{act_ name: (translation, rotation, extras)} for the engine-visible act_ nodes of a glb."""
    out = {}
    for nd in js.get("nodes", []):
        n = nd.get("name", "")
        if is_act(n):
            out[n] = (nd.get("translation", [0, 0, 0]), nd.get("rotation", [0, 0, 0, 1]), nd.get("extras") or {})
    return out


def check_parity(name, js_full, js_lite):
    """Full and lite must be the same set, node for node: same act_ names, places and extras."""
    a, b = act_nodes(js_full), act_nodes(js_lite)
    only_f, only_l = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    if only_f:
        fail(f"{name}: lite lacks {len(only_f)} act_ node(s) the full set has: {only_f[:8]}")
    if only_l:
        fail(f"{name}: lite has act_ node(s) the full set lacks: {only_l[:8]}")
    moved, differ = [], []
    for n in sorted(set(a) & set(b)):
        (tf, rf, ef), (tl, rl, el) = a[n], b[n]
        if max(abs(x - y) for x, y in zip(tf, tl)) > 0.001 or max(abs(x - y) for x, y in zip(rf, rl)) > 0.001:
            moved.append(n)
        if ef != el:
            differ.append(n)
    if moved:
        fail(f"{name}: {len(moved)} act_ node(s) sit elsewhere in lite: {moved[:8]}")
    if differ:
        fail(f"{name}: {len(differ)} act_ node(s) carry other extras in lite (title/author/cover): {differ[:8]}")


# ------------------------------------------------------------ full / lite bounds parity
_CT_MAX = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _node_matrix(nd):
    if "matrix" in nd:
        m = nd["matrix"]
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    tx, ty, tz = nd.get("translation", [0, 0, 0])
    x, y, z, w = nd.get("rotation", [0, 0, 0, 1])
    sx, sy, sz = nd.get("scale", [1, 1, 1])
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[r[0][0] * sx, r[0][1] * sy, r[0][2] * sz, tx], [r[1][0] * sx, r[1][1] * sy, r[1][2] * sz, ty],
            [r[2][0] * sx, r[2][1] * sy, r[2][2] * sz, tz], [0, 0, 0, 1]]


def _mesh_local_box(js, mi):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for p in js["meshes"][mi]["primitives"]:
        a = js["accessors"][p["attributes"]["POSITION"]]
        mn, mx = a.get("min"), a.get("max")
        if mn is None or mx is None:
            continue
        if a.get("normalized") and max(abs(v) for v in mn + mx) > 1.0:
            k = _CT_MAX.get(a["componentType"], 1.0)
            mn, mx = [v / k for v in mn], [v / k for v in mx]
        lo = [min(l, v) for l, v in zip(lo, mn)]
        hi = [max(h, v) for h, v in zip(hi, mx)]
    return lo, hi


def node_boxes(js):
    """{node name: (own mesh world box or None, subtree world box or None)} in the glb's scene frame."""
    nodes = js.get("nodes", [])
    world, own, sub = {}, {}, {}

    def walk(i, M):
        nd = nodes[i]
        W = _mat_mul(M, _node_matrix(nd))
        lo, hi = [1e9] * 3, [-1e9] * 3
        if "mesh" in nd:
            ml, mh = _mesh_local_box(js, nd["mesh"])
            if ml[0] < 1e8:
                for cx in (ml[0], mh[0]):
                    for cy in (ml[1], mh[1]):
                        for cz in (ml[2], mh[2]):
                            p = [W[r][0] * cx + W[r][1] * cy + W[r][2] * cz + W[r][3] for r in range(3)]
                            lo = [min(a, b) for a, b in zip(lo, p)]
                            hi = [max(a, b) for a, b in zip(hi, p)]
                own[i] = (lo[:], hi[:])
        for c in nd.get("children", []):
            cl, ch = walk(c, W)
            lo = [min(a, b) for a, b in zip(lo, cl)]
            hi = [max(a, b) for a, b in zip(hi, ch)]
        sub[i] = (lo, hi)
        return lo, hi

    ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    roots = set(range(len(nodes))) - {c for nd in nodes for c in nd.get("children", [])}
    for scene in js.get("scenes", [{"nodes": sorted(roots)}]):
        for r in scene.get("nodes", []):
            walk(r, ident)
    out = {}
    for i, nd in enumerate(nodes):
        name = nd.get("name")
        if not name or i not in sub:
            continue
        s = sub[i] if sub[i][0][0] < 1e8 else None
        out[name] = (own.get(i), s)
    return out


def _box_diff(a, b):
    return max(max(abs(x - y) for x, y in zip(a[0], b[0])), max(abs(x - y) for x, y in zip(a[1], b[1])))


def check_bounds_parity(name, js_full, js_lite):
    """The lite glb must keep the full glb's shapes: each act_ subtree within ACT_BBOX_TOL, each mesh node
    within MESH_BBOX_TOL (glTF frame, metres). Returns the worst difference seen (for the summary)."""
    bf, bl = node_boxes(js_full), node_boxes(js_lite)
    worst, bad_act, bad_mesh = 0.0, [], []
    inst = {nd.get("name") for js in (js_full, js_lite) for nd in js.get("nodes", [])
            if "EXT_mesh_gpu_instancing" in nd.get("extensions", {})}
    for n in sorted(set(bf) & set(bl)):
        if n in inst:
            # round 9: an instanced batch's own box is its proto in quantised space, not where its copies stand;
            # the copies' places are the same in both builds (one layout), only the proto's segment count differs
            continue
        (of, sf), (ol, sl) = bf[n], bl[n]
        if is_act(n) and sf and sl:
            d = _box_diff(sf, sl)
            worst = max(worst, d)
            if d > ACT_BBOX_TOL:
                bad_act.append((n, d, sf, sl))
        if of and ol:
            d = _box_diff(of, ol)
            worst = max(worst, d)
            if d > MESH_BBOX_TOL:
                bad_mesh.append((n, d, of, ol))
    for n, d, f, l in bad_act[:6]:
        fail(f"{name}: act_ subtree {n} bounds differ full/lite by {d * 100:.1f} cm "
             f"(full max y {f[1][1]:.3f}, lite max y {l[1][1]:.3f})")
    for n, d, f, l in bad_mesh[:6]:
        fail(f"{name}: mesh {n} bounds differ full/lite by {d * 100:.1f} cm "
             f"(full {['%.3f' % v for v in f[0] + f[1]]}, lite {['%.3f' % v for v in l[0] + l[1]]})")
    if len(bad_act) + len(bad_mesh) > 12:
        fail(f"{name}: {len(bad_act) + len(bad_mesh) - 12} more bounds mismatches not listed")
    return worst


def seat_check(sets):
    """Run seat_check.mjs on every set (full and lite) against its stall at its slot."""
    jobs, seats = [], {}
    for name, e in sets.items():
        for variant in ("model", "lite"):
            seats[f"{name}|{variant}"] = e.get("seat", "board")
            jobs.append({"set": f"{name}|{variant}", "prop": os.path.join(MODELS, e[variant]),
                         "stall": os.path.join(MODELS, e["asset"]), "slot": e["slot"]})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(jobs, f)
        path = f.name
    try:
        out = subprocess.run(["node", SEAT, path], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as ex:
        fail(f"seat check could not run ({ex}); it needs node and @gltf-transform (npm -g)")
        return {}
    finally:
        os.unlink(path)
    if out.returncode:
        fail(f"seat check failed: {out.stderr.strip()[-400:]}")
        return {}
    res = json.loads(out.stdout)
    print(f"\n{'seat check':32s} {'board y':>15s} {'set y':>15s}  cuts into the stall")
    for key, r in res.items():
        name, variant = key.split("|")
        tag = f"{name} ({'full' if variant == 'model' else 'lite'})"
        if r.get("error"):
            fail(f"{tag}: seat check: {r['error']}")
            continue
        sup, bb = r.get("support"), r["bbox"]
        cuts = r.get("collisions", [])
        print(f"{tag:32s} {('%.3f..%.3f' % (sup['y_min'], sup['y_max'])) if sup else 'none':>15s} "
              f"{'%.3f..%.3f' % (bb['min'][1], bb['max'][1]):>15s}  "
              + (", ".join(f"{c['node']} at {c['at']}" for c in cuts[:4]) or "none"))
        for c in cuts:
            if c.get("sunk") and seats.get(key) == "hang":
                continue     # under a rail's footprint is where hanging goods belong (the rail is not a solid top)
            how = "sunk under a stall top by" if c.get("sunk") else "reaching behind a stall face by"
            fail(f"{tag}: {c['node']} cuts into the stall at {c['at']} (slot frame, m), {how} {c['depth'] * 100:.1f} cm")
        if seats.get(key, "board") != "board":
            continue                     # hangs from a rail, overhangs a dais or stands on the lane: no board test
        if not sup:
            fail(f"{tag}: no board at the slot height under the set")
        elif bb["min"][1] < sup["y_min"] - 0.005 or bb["max"][1] > sup["y_max"] + 0.005:
            fail(f"{tag}: reaches y {bb['min'][1]:.3f}..{bb['max'][1]:.3f}, past the board it stands on "
                 f"(y {sup['y_min']:.3f}..{sup['y_max']:.3f})")
    return res


# ------------------------------------------------------------ round 6: writing surfaces (docs/adr/0003)
_DECODED = {}


def decoded(path):
    """The glb with its meshopt compression undone (blender/lib/decode.mjs) as (json, bin), cached."""
    if path not in _DECODED:
        tmp = os.path.join(tempfile.mkdtemp(prefix="vendor_check_"), os.path.basename(path))
        subprocess.run(["node", os.path.join(REPO, "blender", "lib", "decode.mjs"), path, tmp], check=True,
                       capture_output=True, timeout=300)
        _DECODED[path] = glb_tools.read_glb(tmp)
    return _DECODED[path]


def _accessor_values(js, binchunk, ai):
    import struct
    acc = js["accessors"][ai]
    bv = js["bufferViews"][acc["bufferView"]]
    fmt = {5126: "f", 5123: "H", 5121: "B", 5122: "h", 5120: "b"}[acc["componentType"]]
    size = struct.calcsize(fmt)
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    stride = bv.get("byteStride", size * n)
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    k = _CT_MAX.get(acc["componentType"], 1.0) if acc.get("normalized") else 1.0
    return [tuple(v / k for v in struct.unpack_from("<" + fmt * n, binchunk, base + i * stride))
            for i in range(acc["count"])]


def uv_range(js, mesh_index, binchunk=None):
    """(min u, min v, max u, max v) of a mesh's TEXCOORD_0, read from the decoded data."""
    lo, hi = [1e9, 1e9], [-1e9, -1e9]
    for p in js["meshes"][mesh_index]["primitives"]:
        a = p["attributes"].get("TEXCOORD_0")
        if a is None:
            return None
        for u, v in _accessor_values(js, binchunk, a):
            lo[0], lo[1] = min(lo[0], u), min(lo[1], v)
            hi[0], hi[1] = max(hi[0], u), max(hi[1], v)
    return lo[0], lo[1], hi[0], hi[1]


def check_write_nodes(label, path, want):
    """Every write_ node named in `want` exists with a mesh child whose UVs span 0..1, and the parent (if
    given) is right: want = {write_name: parent_name or None}."""
    js, binchunk = decoded(path)
    nodes = js.get("nodes", [])
    by = {nd.get("name"): nd for nd in nodes}
    par = parents(js)
    for w, parent in want.items():
        nd = by.get(w)
        if nd is None:
            fail(f"{label}: no {w}")
            continue
        if parent and par.get(w) != parent:
            fail(f"{label}: {w} is under {par.get(w)}, not {parent}")
        mesh = nd.get("mesh")
        if mesh is None:
            for c in nd.get("children", []):
                if "mesh" in nodes[c]:
                    mesh = nodes[c]["mesh"]
                    break
        if mesh is None:
            fail(f"{label}: {w} has no mesh")
            continue
        r = uv_range(js, mesh, binchunk)
        if r is None or max(abs(r[0]), abs(r[1]), abs(r[2] - 1), abs(r[3] - 1)) > 0.01:
            fail(f"{label}: {w} UVs do not span 0..1 ({r})")
        mats = {js["materials"][p.get("material", 0)].get("name", "") for p in js["meshes"][mesh]["primitives"]}
        if not all(m.startswith("write_") for m in mats):
            fail(f"{label}: {w} is not on a plain write_ material ({sorted(mats)})")


def check_writing(sets, items, pj):
    """Round 6: a Bierdeckel per project (content/projects.md ### headings) plus spares, each with a front and
    a back write_ face; the Marktblatt; a back label per wine bottle; book_open.glb with its pages, the leaf
    and the reading camera; all in full and lite."""
    sys.path.insert(0, HERE)
    import content_projects
    projects = content_projects.projects()
    for variant in ("model", "lite"):
        bpath = os.path.join(MODELS, sets["prop_bier_counter"][variant])
        js, _ = glb_tools.read_glb(bpath)
        nodes = glb_tools.node_names(js)
        cs = acts(nodes, "act_coaster_")
        if len(cs) != len(projects) + content_projects.N_SPARES:
            fail(f"prop_bier_counter ({variant}): {len(cs)} coasters for {len(projects)} projects "
                 f"+ {content_projects.N_SPARES} spares")
        want = {}
        for c in cs:
            n = c.rsplit("_", 1)[1]
            want[f"write_coaster_{n}_front"] = c
            want[f"write_coaster_{n}_back"] = c
        check_write_nodes(f"prop_bier_counter ({variant})", bpath, want)
    for p in projects:
        it = items.get(f"act_coaster_{p['i']}", {})
        if it.get("project") != p["name"]:
            fail(f"items.json: act_coaster_{p['i']} is not the coaster of {p['name']!r} ({it.get('project')!r})")
    for variant in ("model", "lite"):
        wpath = os.path.join(MODELS, sets["prop_wurst_counter"][variant])
        js, _ = glb_tools.read_glb(wpath)
        nodes = glb_tools.node_names(js)
        check_write_nodes(f"prop_wurst_counter ({variant})", wpath, {"write_writing_paper": "act_writing_paper"})
        for e in ("cam_read_writing_paper", "cam_read_writing_paper_target"):
            if e not in nodes:
                fail(f"prop_wurst_counter ({variant}): no {e}")
        gpath = os.path.join(MODELS, sets["prop_gluehwein_wine"][variant])
        js, _ = glb_tools.read_glb(gpath)
        nodes = glb_tools.node_names(js)
        bottles = acts(nodes, "act_bottle_")
        check_write_nodes(f"prop_gluehwein_wine ({variant})", gpath,
                          {f"write_label_{b.rsplit('_', 1)[1]}": b for b in bottles})
        for b in bottles:
            if f"cam_read_label_{b.rsplit('_', 1)[1]}" not in nodes:
                fail(f"prop_gluehwein_wine ({variant}): no cam_read_label for {b}")
    alone = {e.get("root"): e for e in pj.get("standalone", [])}
    if "book_open" not in alone:
        fail("props.json: book_open.glb is not listed under 'standalone'")
        return
    jss = {}
    for variant in ("model", "lite"):
        path = os.path.join(MODELS, alone["book_open"][variant])
        if not os.path.exists(path):
            fail(f"missing {os.path.basename(path)}")
            return
        js, _ = glb_tools.read_glb(path)
        jss[variant] = js
        nodes = glb_tools.node_names(js)
        check_write_nodes(f"book_open ({variant})", path, {"write_page_left": "book_open", "write_page_right": "book_open",
                                                          "write_page_turn_front": "act_page_turn",
                                                          "write_page_turn_back": "act_page_turn"})
        for e in ("act_page_turn", "cam_read_book", "cam_read_book_target", "book_open_cover"):
            if e not in nodes:
                fail(f"book_open ({variant}): no {e}")
        mats = {m.get("name") for m in js.get("materials", [])}
        if "book_cover_open" not in mats:
            fail(f"book_open ({variant}): no book_cover_open material")
        rf = glb_tools.report(path)
        print(f"book_open ({variant}): {rf['triangles']} triangles, {rf['bytes'] / 1e3:.0f} kB")
    check_parity("book_open", jss["model"], jss["lite"])
    if "act_page_turn" not in items:
        fail("items.json has no act_page_turn")


def check_books(items, seen):
    """Mac's 55 books: each title in categories.json is exactly one act_book_<nn> in its category's set
    prop_books_<key>, items.json carries name, author, slug and category, every slug has its summary file, and
    no act_book_ node anywhere carries a title that is not in categories.json (no invented titles)."""
    want = {}
    for c in BOOK_CATS:
        for b in c["books"]:
            want[b["slug"]] = (b["title"], b["author"], c["key"])
    got = {}
    for n, it in items.items():
        if not re.match(r"^act_book_\d+$", n):
            continue
        slug = it.get("slug")
        if slug not in want:
            fail(f"items.json: {n} ({it.get('title')!r}) is not one of Mac's books (slug {slug!r})")
            continue
        t, a, k = want[slug]
        if (it.get("name"), it.get("title"), it.get("author"), it.get("category")) != (t, t, a, k):
            fail(f"items.json: {n} does not match categories.json for {slug} "
                 f"({it.get('name')!r}, {it.get('author')!r}, {it.get('category')!r})")
        if it.get("set") != f"prop_books_{k}":
            fail(f"{n} ({slug}) is in {it.get('set')}, not prop_books_{k}")
        if slug in got:
            fail(f"{slug} appears twice: {got[slug]} and {n}")
        got[slug] = n
        if not os.path.exists(os.path.join(REPO, "content", "books", slug + ".md")):
            fail(f"{n}: content/books/{slug}.md does not exist")
    missing = sorted(set(want) - set(got))
    if missing:
        fail(f"{len(missing)} of Mac's books have no act_book_ node: {missing[:6]}")
    print(f"\nbooks: {len(got)} of {len(want)} titles from categories.json, one act_book_ node each")


def check_fill(sets, items, seen):
    """Round 9 (ADR 0004 revision): the ornament shop has exactly its three interactive groups."""
    for n, st in seen.items():
        it = items.get(n, {})
        if it.get("kind") == "deco" and not (it.get("label") and it.get("action")):
            fail(f"items.json: {n} ({st}) lacks label or action")
    orn = {n for n, st in seen.items() if st in SCHMUCK_SETS}
    want = {f"act_orn_harmonica_{i}" for i in range(12)} | {"act_orn_mirrorball", "act_orn_schwibbogen"} | \
        {f"act_orn_candle_{i}" for i in range(7)}
    if orn - want:
        fail(f"ornament shop: act_ nodes beyond the three interactive groups: {sorted(orn - want)}")
    if want - orn:
        fail(f"ornament shop: missing {sorted(want - orn)}")
    stale = sorted(k for k, it in items.items() if it.get("stall") == "deco-schmuck" and k not in want)
    if stale:
        fail(f"items.json: stale ornament shop entries {stale[:8]}")
    rep = json.load(open(REPORT)) if os.path.exists(REPORT) else {}
    piv = rep.get("prop_schmuck_harmonica", {}).get("pivots", {})
    org = [piv.get(f"act_orn_harmonica_{i}", {}).get("origin") for i in range(12)]
    if all(org):
        xs = [o[0] for o in org]
        if any(b <= a for a, b in zip(xs[:-1], xs[1:])):
            fail("ornament shop: act_orn_harmonica_0..11 do not run left to right")
        if max(o[2] for o in org) - min(o[2] for o in org) > 0.005 or max(o[1] for o in org) - min(o[1] for o in org) > 0.005:
            fail("ornament shop: the harmonica's knots are not in one row")
    else:
        fail("ornament shop: no pivot report for the harmonica (run build_props.py)")
    names = {}
    for name in SCHMUCK_SETS:
        if name not in sets:
            fail(f"ornament shop: {name} missing from props.json")
            continue
        js, _ = glb_tools.read_glb(os.path.join(MODELS, sets[name]["model"]))
        names[name] = (glb_tools.node_names(js), {m.get("name", "") for m in js.get("materials", [])})
    alln = [n for v, _ in names.values() for n in v]
    allm = set().union(*(m for _, m in names.values())) if names else set()
    mb = names.get("prop_schmuck_mirrorball", ([], set()))[0]
    for e in ("cam_dive", "cam_dive_target"):
        if e not in mb:
            fail(f"ornament shop: prop_schmuck_mirrorball has no {e}")
    if "rot_pyramid" not in names.get("prop_schmuck_pyramid", ([], set()))[0]:
        fail("ornament shop: prop_schmuck_pyramid has no rot_pyramid")
    tins = sorted({n for n in alln if re.match(r"^tinsel_\d+$", n)})
    if len(tins) < 2:
        fail(f"ornament shop: {len(tins)} tinsel_<n> swags (want at least 2)")
    if "fx_smoke_1" not in alln:
        fail("ornament shop: the smoker has no fx_smoke_1")
    if "bulb_warm" not in allm:
        fail("ornament shop: no bulb_warm (the Herrnhut stars' cores)")
    print(f"\nornament shop: {len(orn)} act_orn nodes (harmonica 12, mirror ball, Schwibbogen + 7 candles), "
          f"{len(tins)} tinsel swags {tins}, rot_pyramid, cam_dive")


def write_notes(rows, section_rows, deco_rows, tex, tex_lite, glb_full, glb_lite):
    """Replace the generated budget block in NOTES.md (between the check_props markers)."""
    L = ["<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->", "",
         "Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the "
         "shared atlases are counted once below. Size is the set's bounding box in metres.", "",
         "| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} ({r[5]:.0%}) | {r[6]:.0f} / {r[7]:.0f} | "
                 f"{r[8][0]:.2f} × {r[8][1]:.2f} × {r[8][2]:.2f} |")
    L += ["", f"All prop glbs together: {glb_full / 1e6:.2f} MB full and {glb_lite / 1e6:.2f} MB lite. Shared textures "
          f"(`prop_tex_*`): {tex / 1e6:.2f} MB full and {tex_lite / 1e6:.2f} MB lite, loaded once for all sets.", "",
          "Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared "
          "textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2000 headroom):", "",
          "| stall | stall tris | + props | total / budget | headroom | MB / budget |", "|---|---|---|---|---|---|"]
    for st, a, b, tot, room, mb, lt, lmb in section_rows:
        L.append(f"| {st} | {a} | {b} | {tot} / {lt // 1000}k {'OK' if room >= HEADROOM else 'FAIL'} | {room} | "
                 f"{mb:.2f} / {lmb:.0f} |")
    L += ["", "Deco stalls, stall plus its one scenery goods set against 20k (the ornament shop, stall_schmuck.glb, with its "
          f"{len(SCHMUCK_SETS)} goods sets against 60k and 3 MB; check_props fails over)." " MB is the stall glb plus its goods glb against the 1 MB budget; the "
          "shared prop textures load once for the whole market and are listed apart (the ornament shop's MB includes "
          "them, against its 3 MB):", "",
          "| deco stall | stall tris | goods | total / budget | room | act_ nodes (0: scenery) | MB stall + goods / budget "
          "| shared textures used (loaded once) |",
          "|---|---|---|---|---|---|---|---|"]
    for d, a, b, tot, lim, n_act, mb, mb_tex, lim_mb in deco_rows:
        L.append(f"| {d} | {a} | {b} | {tot} / {lim // 1000}k {'OK' if tot <= lim else 'over'} | {lim - tot} | "
                 f"{n_act} | {mb:.2f} / {lim_mb:.0f} {'OK' if mb <= lim_mb else 'over'} | {mb_tex:.2f} MB |")
    L += ["", "<!-- check_props:end -->"]
    block = "\n".join(L)
    txt = open(NOTES).read() if os.path.exists(NOTES) else ""
    a, b = txt.find("<!-- check_props:begin"), txt.find("<!-- check_props:end -->")
    if a < 0 or b < 0:
        print("NOTES.md has no check_props markers; table not written")
        return
    txt = txt[:a] + block + txt[b + len("<!-- check_props:end -->"):]
    with open(NOTES, "w") as f:
        f.write(txt)
    print(f"wrote the budget tables into {NOTES}")


def main():
    with open(os.path.join(MODELS, "props.json")) as f:
        pj = json.load(f)
    if set(pj) - {"about", "sets", "by_set", "standalone", "retired"}:
        fail(f"props.json has extra top-level keys {sorted(set(pj) - {'about', 'sets', 'by_set', 'standalone', 'retired'})}")
    retired = {e["set"] for e in pj.get("retired", [])}
    by = pj.get("by_set", {})
    if {e.get("set") for e in pj.get("sets", [])} != set(by) or any(
            by[e["set"]] != {k: e[k] for k in ("slot", "stall", "model", "lite", "asset")} for e in pj.get("sets", [])):
        fail("props.json by_set does not mirror the sets list")
    sets = {e["set"]: e for e in pj["sets"]}
    with open(os.path.join(MODELS, "items.json")) as f:
        items = json.load(f)["items"]
    rep = {}
    if os.path.exists(REPORT):
        with open(REPORT) as f:
            rep = json.load(f)
    files = sorted(f[:-4] for f in os.listdir(MODELS) if f.startswith("prop_") and f.endswith(".glb")
                   and not f.endswith(".lite.glb"))
    for f in files:
        if f not in sets and f not in retired:
            fail(f"{f}.glb is not in props.json")
    for n in SECTION_SETS + [f"prop_deco_{d}" for d in FILL_KEYS] + SCHMUCK_SETS:
        if n not in sets:
            fail(f"missing set {n}")
    tex = sum(os.path.getsize(os.path.join(MODELS, t)) for t in os.listdir(MODELS)
              if t.startswith("prop_tex_") and ".lite." not in t)
    tex_lite = sum(os.path.getsize(os.path.join(MODELS, t)) for t in os.listdir(MODELS)
                   if t.startswith("prop_tex_") and ".lite." in t)
    per_stall, seen, rows, bounds_worst = {}, {}, [], {}
    glb_full = glb_lite = 0
    print(f"{'set':24s} {'stall':14s} {'slot':13s} {'tris':>6s} {'lite':>5s} {'ratio':>5s} {'kB':>4s} {'lite':>4s}"
          f"  size x y z (m)")
    for name, e in sets.items():
        paths = [os.path.join(MODELS, e["model"]), os.path.join(MODELS, e["lite"])]
        if not all(os.path.exists(p) for p in paths):
            fail(f"{name}: missing {[os.path.basename(p) for p in paths if not os.path.exists(p)]}")
            continue
        rf, rl = glb_tools.report(paths[0]), glb_tools.report(paths[1])
        r = rep.get(name, {})
        ratio = rl["triangles"] / max(1, rf["triangles"])
        size = r.get("size") or [0, 0, 0]
        print(f"{name:24s} {e['stall']:14s} {e['slot']:13s} {rf['triangles']:6d} {rl['triangles']:5d} {ratio:5.0%} "
              f"{rf['bytes'] / 1e3:4.0f} {rl['bytes'] / 1e3:4.0f}  {size[0]:.2f} {size[1]:.2f} {size[2]:.2f}")
        rows.append((name, e["stall"], e["slot"], rf["triangles"], rl["triangles"], ratio, rf["bytes"] / 1e3,
                     rl["bytes"] / 1e3, size))
        glb_full += rf["bytes"]
        glb_lite += rl["bytes"]
        jss = {}
        for variant, p in zip(("full", "lite"), paths):
            js, _ = glb_tools.read_glb(p)
            jss[variant] = js
            nodes = glb_tools.node_names(js)
            check_nodes(f"{name} ({variant})", js, nodes)
            if e.get("seat") == "span":
                check_scenery(f"{name} ({variant})", js, nodes, variant)
            else:
                check_ao(f"{name} ({variant})", js)
        check_parity(name, jss["full"], jss["lite"])
        bounds_worst[name] = check_bounds_parity(name, jss["full"], jss["lite"])
        for n in glb_tools.node_names(jss["full"]):
            if is_act(n):
                if n in seen:
                    fail(f"{n} is in both {seen[n]} and {name}")
                seen[n] = name
                if n not in items:
                    fail(f"items.json has no entry for {n} ({name})")
                elif items[n].get("kind") == "book" and not (items[n].get("title") and items[n].get("author")):
                    fail(f"items.json: {n} lacks title or author")
        check_geometry(name, r, e.get("seat", "board"))
        if ratio > LITE_RATIO:
            warn(f"{name}: lite has {ratio:.0%} of the full triangles (target about a third)")
        per_stall.setdefault(e["stall"], []).append((rf, rl, uris(paths[0])))
    print("\nfull/lite bounds parity, worst difference per set (cm): "
          + ", ".join(f"{n.replace('prop_', '')} {d * 100:.1f}" for n, d in bounds_worst.items()))
    stale = sorted(n for n, it in items.items() if it.get("set") in sets and n not in seen)
    if stale:
        fail(f"items.json lists {len(stale)} act_ node(s) no glb carries: {stale[:8]}")
    print(f"\nshared textures: {tex / 1e6:.2f} MB (lite {tex_lite / 1e6:.2f} MB), loaded once for all sets")
    section_rows, deco_rows = [], []
    print(f"\n{'section stall':14s} {'stall':>6s} {'props':>6s} {'total':>6s} {'room':>6s} {'MB':>5s}")
    for stall, base in SECTION.items():
        sr = glb_tools.report(os.path.join(MODELS, base + ".glb"))
        pt = sum(r[0]["triangles"] for r in per_stall.get(stall, []))
        pb = sum(r[0]["bytes"] for r in per_stall.get(stall, []))
        # the shared prop textures this stall's sets actually reference (each counted once)
        used = set().union(*(r[2] for r in per_stall.get(stall, []))) if per_stall.get(stall) else set()
        tb = sum(os.path.getsize(os.path.join(MODELS, u)) for u in used)
        tot = sr["triangles"] + pt
        mb = (sr["bytes"] + pb + tb) / 1e6
        lim_t, lim_mb = STALL_BUDGET.get(stall, (SECTION_TRIS, SECTION_MB))
        print(f"{stall:14s} {sr['triangles']:6d} {pt:6d} {tot:6d} {lim_t - tot:6d} {mb:5.2f} (of {lim_t // 1000}k, {lim_mb:.0f} MB)")
        section_rows.append((stall, sr["triangles"], pt, tot, lim_t - tot, mb, lim_t, lim_mb))
        if tot > lim_t - HEADROOM:
            fail(f"{stall}: {tot} triangles leaves {lim_t - tot} headroom (< {HEADROOM})")
        if mb > lim_mb:
            fail(f"{stall}: {mb:.2f} MB with the shared textures (> {lim_mb})")
    print(f"\n{'deco stall':14s} {'stall':>6s} {'goods':>6s} {'total':>6s} {'acts':>5s}")
    for d in DECO_KEYS:
        sid = "deco-" + ("kartoffelpuffer" if d == "puffer" else d)
        asset = "stall_schmuck.glb" if d == "schmuck" else f"deco_{d}.glb"
        lim = SCHMUCK_TRIS if d == "schmuck" else DECO_TRIS
        sr = glb_tools.report(os.path.join(MODELS, asset))
        pt = sum(r[0]["triangles"] for r in per_stall.get(sid, []))
        tot = sr["triangles"] + pt
        n_act = sum(1 for n, st in seen.items() if sets[st]["stall"] == sid)
        used = set().union(*(r[2] for r in per_stall.get(sid, []))) if per_stall.get(sid) else set()
        mb_own = (sr["bytes"] + sum(r[0]["bytes"] for r in per_stall.get(sid, []))) / 1e6
        mb_tex = sum(os.path.getsize(os.path.join(MODELS, u)) for u in used) / 1e6
        # deco stalls: the stall's own files (shared textures apart); the ornament shop: with its shared textures
        mb = mb_own + mb_tex if d == "schmuck" else mb_own
        lim_mb = SCHMUCK_MB if d == "schmuck" else DECO_MB
        print(f"{d:14s} {sr['triangles']:6d} {pt:6d} {tot:6d} {n_act:5d}  {mb:.2f} MB of {lim_mb:.0f} "
              f"(+ {mb_tex:.2f} MB shared textures{' included' if d == 'schmuck' else ', loaded once'})  "
              f"({asset}, of {lim // 1000}k)")
        deco_rows.append((d, sr["triangles"], pt, tot, lim, n_act, mb, mb_tex, lim_mb))
        if d != "schmuck" and mb > DECO_MB:
            fail(f"deco {d}: stall + goods glbs {mb:.2f} MB (> {DECO_MB})")
        if tot > lim:
            fail(f"deco {d}: stall {sr['triangles']} + goods {pt} = {tot} > {lim} "
                 f"({'the stall alone leaves ' + str(max(0, lim - sr['triangles'])) + ' for goods'})")
        if d == "schmuck" and n_act != 21:
            fail(f"ornament shop: {n_act} clickable act_ nodes (want 21: 12 harmonica, mirror ball, Schwibbogen, 7 candles)")
        if d != "schmuck" and n_act:
            fail(f"deco {d}: {n_act} act_ nodes (deco stalls are scenery since 2026-10-05)")
        if d != "schmuck" and any(it.get("stall") == sid for it in items.values()):
            fail(f"deco {d}: items.json still has entries for this scenery stall")
        if d == "schmuck" and mb > SCHMUCK_MB:
            fail(f"ornament shop: {mb:.2f} MB with its goods and their shared textures (> {SCHMUCK_MB})")
    check_fill(sets, items, seen)
    check_books(items, seen)
    check_writing(sets, items, pj)
    # the beer heads as the browser decodes them (meshopt, quantised node transforms): no tall foam columns
    fc = subprocess.run(["node", os.path.join(HERE, "foam_check.mjs")], capture_output=True, text=True, timeout=300)
    print("\nfoam check: " + " | ".join(fc.stdout.strip().splitlines()))
    if fc.returncode:
        fail("foam check: a beer head is too tall for its glass (blender/props/foam_check.mjs)")
    if "--no-seat" not in sys.argv:
        seat_check(sets)
    if "--notes" in sys.argv:
        write_notes(rows, section_rows, deco_rows, tex, tex_lite, glb_full, glb_lite)
    if fails:
        print(f"\nFAILED: {len(fails)} check(s) failed, {len(warns)} warning(s)")
        return 1
    print(f"\nPASSED WITH {len(warns)} WARNING(S)" if warns else "\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
