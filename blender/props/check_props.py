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
- section stall + its props <= 60k triangles with >= 2k headroom, and <= 3 MB with shared textures
- deco stall + its goods <= 20k triangles (BUILD.md budget)
- the full and lite glb of a set carry the same act_ nodes, at the same place, with the same extras
  (name, kind, title, author, cover_material), and items.json lists no act_ node a glb lacks
- seat check (blender/props/seat_check.mjs, node): no prop triangle cuts into its stall (counter,
  firebox, hearth plate, posts, braces, back boards) at its slot, and every set stays inside the y-range
  of the board it stands on (so nothing hangs past the counter's back edge)
- full / lite bounds parity: every act_ node's subtree (the node and everything under it) has the same
  world bounding box in the lite glb as in the full glb within 1 cm, and every named mesh node within 2 cm
  (so a lite simplification that changes the shape, e.g. a foam head growing into a column, fails)
WARN (listed, exit 0): lite versions above 38 % of the full triangles (target about a third).

    python3 blender/props/check_props.py --notes   also rewrites the budget tables in
                                                   review/round-4/vendor/NOTES.md from the current glbs
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
NO_AO = ("vendor_glass", "flame", "lamp_glow", "bulb_warm", "coal_glow", "vendor_beer", "vendor_liquid", "vendor_lamp_shade")
BASE_PIVOT = re.compile(r"^act_(mug|glass|bottle|wineglass|book|roll|tap|served|sausage)_\d+$|^act_grill$")
HEADROOM, SECTION_TRIS, SECTION_MB, DECO_TRIS = 2000, 60000, 3.0, 20000
LITE_RATIO = 0.38
ACT_BBOX_TOL, MESH_BBOX_TOL = 0.01, 0.02          # m: full vs lite bounds of act_ subtrees / mesh nodes
NOTES = os.path.join(REPO, "review", "round-4", "vendor", "NOTES.md")
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


def check_geometry(name, r):
    size, lo, hi = r.get("size"), r.get("bbox_min"), r.get("bbox_max")
    if not size:
        fail(f"{name}: no bounding box in props_report.json (rebuild)")
        return
    if size[1] > 0.5 + 1e-3:
        fail(f"{name} is {size[1]:.3f} m deep (> 0.5)")
    floor = r.get("grill_seat", {}).get("floor_z")
    if floor is not None and lo[2] < floor - 0.002:
        fail(f"{name} reaches {lo[2]:.3f} m, below the grill opening's deck at {floor:.3f}")
    elif floor is None and lo[2] < -0.002:
        fail(f"{name} reaches {lo[2]:.3f} m below its slot")
    if hi[2] > 1.15 + 1e-3:
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
    for n in sorted(set(bf) & set(bl)):
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
    jobs = []
    for name, e in sets.items():
        for variant in ("model", "lite"):
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
            how = "sunk under a stall top by" if c.get("sunk") else "reaching behind a stall face by"
            fail(f"{tag}: {c['node']} cuts into the stall at {c['at']} (slot frame, m), {how} {c['depth'] * 100:.1f} cm")
        if not sup:
            fail(f"{tag}: no board at the slot height under the set")
        elif bb["min"][1] < sup["y_min"] - 0.005 or bb["max"][1] > sup["y_max"] + 0.005:
            fail(f"{tag}: reaches y {bb['min'][1]:.3f}..{bb['max'][1]:.3f}, past the board it stands on "
                 f"(y {sup['y_min']:.3f}..{sup['y_max']:.3f})")
    return res


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
          "textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2k headroom):", "",
          "| stall | stall tris | + props | total / budget | headroom | MB / budget |", "|---|---|---|---|---|---|"]
    for st, a, b, tot, room, mb, lt, lmb in section_rows:
        L.append(f"| {st} | {a} | {b} | {tot} / {lt // 1000}k {'OK' if room >= HEADROOM else 'FAIL'} | {room} | "
                 f"{mb:.2f} / {lmb:.0f} |")
    L += ["", "Deco stalls, stall plus goods against 20k (check_props fails over):", "",
          "| deco stall | stall tris | goods | total / 20k | room |", "|---|---|---|---|---|"]
    for d, a, b, tot in deco_rows:
        L.append(f"| {d} | {a} | {b} | {tot} {'OK' if tot <= DECO_TRIS else 'over'} | {DECO_TRIS - tot} |")
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
    if set(pj) - {"about", "sets", "by_set"}:
        fail(f"props.json has extra top-level keys {sorted(set(pj) - {'about', 'sets', 'by_set'})}")
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
        if f not in sets:
            fail(f"{f}.glb is not in props.json")
    for n in SECTION_SETS + [f"prop_deco_{d}" for d in DECO_KEYS]:
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
        check_geometry(name, r)
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
    print(f"\n{'deco stall':14s} {'stall':>6s} {'goods':>6s} {'total':>6s}")
    for d in DECO_KEYS:
        sid = "deco-" + ("kartoffelpuffer" if d == "puffer" else d)
        sr = glb_tools.report(os.path.join(MODELS, f"deco_{d}.glb"))
        pt = sum(r[0]["triangles"] for r in per_stall.get(sid, []))
        tot = sr["triangles"] + pt
        print(f"{d:14s} {sr['triangles']:6d} {pt:6d} {tot:6d}")
        deco_rows.append((d, sr["triangles"], pt, tot))
        if tot > DECO_TRIS:
            fail(f"deco {d}: stall {sr['triangles']} + goods {pt} = {tot} > {DECO_TRIS} "
                 f"({'the stall alone leaves ' + str(max(0, DECO_TRIS - sr['triangles'])) + ' for goods'})")
    check_books(items, seen)
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
