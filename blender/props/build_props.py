"""Build the vendor's prop sets: full + lite glb (with baked AO), props.json, items.json, reports and
Cycles previews.

    NM_DEVICE=CPU NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/props/build_props.py
        [--only a,b] [--no-render] [--no-lite] [--no-full] [--no-ao] [--samples 48] [--res 1280x720]
        [--render-only a,b] [--shots wide,hero]

Outputs
    site/public/models/prop_<set>.glb, prop_<set>.lite.glb, shared prop_tex_*.webp
    site/public/models/props.json      {"sets": [{set, stall, slot, model, lite, asset}]} (the engine's form)
                                       + "by_set": {set: {slot, stall, model, lite, asset}}
    site/public/models/items.json      every act_ node -> display name (books: title, author, cover)
    blender/out/props_report.json      triangles, bytes, bounding boxes, pivots, items per set
    blender/out/vendor/renders/*.png   the preview PNGs (deco frames as prop_deco_<key>.png; never the shared
                                       blender/out/renders/, where the carpenter's deco.py writes deco_<key>.png)
    review/round-10/vendor/*.jpg        wide and close-up previews per section set, a frame per deco set
                                       (the deco contact sheet is render_stalls.py --sheet's)
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import vlib  # noqa: E402  (imports bpy)
import vstage  # noqa: E402
import set_bier  # noqa: E402
import set_bookopen  # noqa: E402
import set_books  # noqa: E402
import set_decoscene  # noqa: E402
import set_schmuck  # noqa: E402
import set_gluehwein  # noqa: E402
import set_wurst  # noqa: E402

MODULES = [set_gluehwein, set_bier, set_wurst, set_books, set_decoscene, set_schmuck, set_bookopen]
# round 8 (Mac, 2026-10-05): the deco stalls' goods are cheap scenery, one merged glb per stall (set_decoscene.py,
# which reuses the set_deco / set_decofill builders); their old act_ goods and _shelf / _front sets are gone
STALL_ASSET = {"gluehwein": "stall_gluehwein.glb", "bratwurst": "stall_bratwurst.glb",
               "bierstand": "stall_bier.glb", "buecherstand": "stall_buecher.glb",
               "deco-schmuck": "stall_schmuck.glb"}   # round 8: the ornament shop replaces deco_schmuck (ADR 0004)
REPORT = os.path.join(vlib.state.OUT_DIR, "props_report.json")
# wide-shot camera elevation (radians) per preview stage: over the counter; level under the shelf above
WIDE_ELEV = {"counter": 0.42, "shelf": 0.1, "shelf2": 0.22, "section": 0.12}


def all_sets(retired=False):
    out = {}
    for mod in MODULES:
        out.update(mod.SETS)
    if retired:
        out.update(set_decoscene.RETIRED)       # buildable with --only, never listed as placed
    return out


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--no-ao", action="store_true", help="skip the AO bake (quick geometry checks only)")
    ap.add_argument("--samples", type=int, default=48)          # BUILD.md: final review renders 1280x720, 48 samples
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--render-only", default=None, help="comma list: render previews only for these sets")
    ap.add_argument("--shots", default="wide,hero", help="section previews to render: wide, hero, stall (in the stall glb)")
    ap.add_argument("--sheet-only", action="store_true", help="retired: use render_stalls.py --sheet")
    ap.add_argument("--json-only", action="store_true", help="only rewrite props.json and items.json from the report")
    a, _ = ap.parse_known_args(sys.argv[1:])
    return a


def build_variant(name, d, lite, ao):
    vlib.reset(d.get("seed", 1), lite)
    ps = d["fn"]()
    if ao and not d.get("no_ao"):
        full_px, lite_px = d.get("ao_size", (vlib.AO_FULL, vlib.AO_LITE))
        vstage.bake_ao(name + (".lite" if lite else ""), lite_px if lite else full_px,
                       samples=16 if lite else 32)
    return ps, vlib.export_set(name, lite, ps.items)


def render_previews(name, d, ps, a, res):
    """Section sets: a wide shot and a close-up. Deco sets: one framed shot (also the contact-sheet tile).
    A set with "in_stall" is also shot standing in the carpenter's shipped stall glb ("stall" shots)."""
    if d.get("fill"):
        # round 8: shelf, front, rail and ornament-shop sets are previewed standing in their stall
        # (blender/props/render_stalls.py), not one by one on a plain counter
        return None
    if d.get("section"):
        if {"wide", "hero"} & set(a.shots.split(",")):
            top = vstage.preview_scene(ps, d["kind"], d.get("width", 3.0), section=d.get("section_boards"))
            # round 6, preview only: bottles turned round to show their back labels, and stand-in text on the
            # write_ faces where the engine will print the section's words (nothing exported changes)
            if d.get("preview_turn"):
                vstage.preview_turn(d["preview_turn"])
            if d.get("preview_text"):
                vstage.preview_texts(d["preview_text"]())
            if "wide" in a.shots:
                # the wide shot frames the whole set (goods fill the width); "cam_fixed" keeps a hand-set camera
                cam = d["cam"] if d.get("cam_fixed") else vstage.frame_cam(ps, lens=28, elev=WIDE_ELEV[d["kind"]],
                                                                            margin=1.04)
                vstage.shot(cam, top, os.path.join(vlib.REVIEW, f"{name}.jpg"), a.samples, res)
            if d.get("hero") and "hero" in a.shots:
                vstage.shot(d["hero"], top, os.path.join(vlib.REVIEW, f"{name}_hero.jpg"), a.samples, res)
            # round 6 pass 2: further close-ups of one set ({tag: cam}, rendered with the hero)
            for tag, cam in d.get("heroes", {}).items():
                if tag in a.shots or "hero" in a.shots:
                    vstage.shot(cam, top, os.path.join(vlib.REVIEW, f"{name}_{tag}.jpg"), a.samples, res)
        if d.get("in_stall") and "stall" in a.shots:
            # last: the stall scene replaces the plain counter (the set is moved to the stall's slot)
            import bpy
            origin = vstage.stall_scene(ps, d["in_stall"], d.get("stall_lights", ()))
            # "stall_dim": {tag: factor} scales the stall's lamps and the fill for that shot only (the grill
            # close-up is shot with the lamps turned down so the coal bed's own glow reads)
            lamps = {o.name: o.data.energy for o in bpy.data.objects
                     if o.type == 'LIGHT' and (o.name.startswith("env_light_") or o.name == "env_fill")}
            for tag, cam in d.get("stall_cams", {}).items():
                k = d.get("stall_dim", {}).get(tag, 1.0)
                for ln, e in lamps.items():
                    bpy.data.objects[ln].data.energy = e * k
                vstage.shot_at(cam, origin, os.path.join(vlib.REVIEW, f"{name}_{tag}.jpg"), a.samples, res)
        return None
    top = vstage.preview_scene(ps, d["kind"], d.get("width", 3.0))
    key = name.replace("prop_deco_", "")
    # the frame PNG is named after the prop set (prop_deco_<key>.png) in the vendor's own render folder
    return vstage.shot(vstage.frame_cam(ps, lens=32), top, os.path.join(vlib.REVIEW, f"deco_{key}.jpg"),
                       a.samples, res, png_name=name)


def guard_paths():
    """Refuse to run if any output location is empty or falls outside the vendor's owned paths (a launch with
    an empty path variable once wrote a log into /). Every path is derived from this file's location."""
    repo = os.path.realpath(vlib.REPO or "")
    if not repo or repo == "/" or not os.path.isfile(os.path.join(repo, "docs", "BUILD.md")):
        raise SystemExit(f"[props] refusing to run: repo root {repo!r} is not the website repo")
    owned = {"review": (vlib.REVIEW, "review/round-10/vendor"), "models": (vlib.MODELS, "site/public/models"),
             "report": (os.path.dirname(REPORT), "blender/out"), "renders": (vstage.RENDERS, "blender/out/vendor/renders"),
             "atlas": (vlib.ATLAS_DIR, "blender/out/vendor")}
    for key, (path, rel) in owned.items():
        if not path or os.path.realpath(path) != os.path.join(repo, rel):
            raise SystemExit(f"[props] refusing to run: {key} output {path!r} is not {rel} inside {repo}")


def main():
    guard_paths()
    a = args()
    sets = all_sets(retired=True)
    if a.sheet_only:
        raise SystemExit("[props] the deco contact sheet is built by blender/props/render_stalls.py --sheet (round 8)")
    if a.json_only:
        placed = all_sets()
        write_props_json(placed)
        write_items_json(placed, load_report())
        return
    only = a.only.split(",") if a.only else None
    if only:
        unknown = [n for n in only if n not in sets]
        if unknown:
            raise SystemExit(f"unknown set(s): {unknown}")
    reports = {}
    if os.path.exists(REPORT):
        with open(REPORT) as f:
            reports = json.load(f)
    os.makedirs(vlib.REVIEW, exist_ok=True)
    res = tuple(int(v) for v in a.res.split("x"))
    for name, d in sets.items():
        if only and name not in only:
            continue
        t0 = time.time()
        r = reports.get(name, {})
        rep_lite = None
        if not a.no_lite:
            _, rep_lite = build_variant(name, d, True, not a.no_ao)
            r["lite"] = {"bytes": rep_lite["bytes"], "triangles": rep_lite["triangles"]}
        if not a.no_full:
            ps, rep_full = build_variant(name, d, False, not a.no_ao)
            r.update(vlib.set_report(ps, rep_full, rep_lite))
            if rep_lite is None and "lite" in reports.get(name, {}):
                r["lite"] = reports[name]["lite"]
            r["items"] = ps.items
            r.update(getattr(ps, "report_extra", {}))
            want = a.render_only is None or name in a.render_only.split(",")
            if not a.no_render and want:
                png = render_previews(name, d, ps, a, res)
                if png:
                    r["frame_png"] = os.path.relpath(png, vlib.REPO)
        r["seconds"] = round(time.time() - t0, 1)
        r["slot"], r["stall"] = d["slot"], d["stall"]
        r["label"] = d.get("label", name)
        reports[name] = r
        print(f"[props] {name}: {json.dumps({k: r.get(k) for k in ('full', 'lite', 'size')})}")
        reports = save_report(name, r)
    # round 8 pass 2: the deco contact sheet is render_stalls.py --sheet's (the stocked stalls from the lane);
    # a build no longer rebuilds it from the old per-set frames, which showed the retired act_ goods
    shrink_shared_textures()
    placed = all_sets()
    write_props_json(placed)
    write_items_json(placed, load_report())


def load_report():
    if os.path.exists(REPORT):
        with open(REPORT) as f:
            return json.load(f)
    return {}


def save_report(name, r):
    """Merge this set's entry into the report on disk (re-read first, so two builds running side by side for
    different sets do not overwrite each other's entries), write it atomically and return the merged dict."""
    reports = load_report()
    reports[name] = r
    tmp = REPORT + f".{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(reports, f, indent=1, ensure_ascii=False)
    os.replace(tmp, REPORT)
    return reports


# Full-size shared maps that do not need 2048 px: the books' normal and roughness carry cloth weave
# and wear, which read the same at 1024; the spine lettering lives in the colour map, which stays 2048.
# Keeps the Bücherstand (stall + props + shared textures) under its 3 MB budget.
SHRINK = {"prop_tex_books_normal.webp": 1024, "prop_tex_books_rm.webp": 1024}


def shrink_shared_textures():
    from PIL import Image
    for fn, size in SHRINK.items():
        path = os.path.join(vlib.MODELS, fn)
        if not os.path.exists(path):
            continue
        im = Image.open(path)
        if im.size[0] <= size:
            continue
        before = os.path.getsize(path)
        new = (size, round(im.size[1] * size / im.size[0]))          # keep the aspect (the books atlas is tall)
        im.resize(new, Image.LANCZOS).save(path, "WEBP", quality=82, method=6)
        print(f"[props] {fn}: {im.size} -> {new} px, {before / 1e3:.0f} -> {os.path.getsize(path) / 1e3:.0f} kB")


def write_props_json(sets):
    """One form only, the list the engine reads (site/src/engine/props.js)."""
    lst, alone = [], []
    for name, d in sets.items():
        if d.get("standalone"):
            # not placed at a slot: the engine loads it on its own (book_open.glb: the book a visitor opens)
            alone.append({"model": f"{name}.glb", "lite": f"{name}.lite.glb", "root": name,
                          "use": "the open hardback shown when a book is clicked (blender/props/set_bookopen.py)"})
            continue
        stall = d["stall"]
        key = stall.replace("deco-", "").replace("kartoffelpuffer", "puffer")
        e = {"set": name, "stall": stall, "slot": d["slot"], "model": f"{name}.glb",
             "lite": f"{name}.lite.glb", "asset": STALL_ASSET.get(stall, f"deco_{key}.glb")}
        if d.get("standin"):
            # round 9: a slot the stall glb does not carry yet (the carpenter adds it): where to put the set until
            # then, in the stall's frame (Blender axes, Z up; three.js: x, z, -y), with the slot's data
            e["standin_position"] = d["standin"]["position"]
            e["standin_note"] = (d["standin"].get("about", "") + f" ({d['slot']} is not yet in "
                                 f"{STALL_ASSET.get(stall, 'the stall glb')})")
        if d.get("seat", "board") != "board":
            # round 8: how the set meets its stall: "hang" from a rail, "stand" on a dais it overhangs (the
            # tree), "ground" in front of the hut; the default "board" sets stand on a counter or shelf
            e["seat"] = d["seat"]
        lst.append(e)
    retired = []
    for name, d in set_decoscene.RETIRED.items():
        if os.path.exists(os.path.join(vlib.MODELS, f"{name}.glb")):
            retired.append({"set": name, "stall": d["stall"], "slot": d["slot"], "model": f"{name}.glb",
                            "lite": f"{name}.lite.glb", "asset": "deco_schmuck.glb",
                            "why": "round 8: the old Christbaumschmuck hut's scenery goods (no act_ nodes), superseded "
                                   "by the ornament shop's prop_schmuck_* sets in stall_schmuck.glb (ADR 0004). Place "
                                   "it only if deco_schmuck.glb is used instead of stall_schmuck.glb."})
    out = {"about": "Vendor prop sets. Each glb's root node is the set origin: parent it to the named slot_ empty "
                    "of the stall (layout.json id in 'stall', stall file in 'asset'). 'sets' is the list the engine "
                    "reads; 'by_set' is the same data keyed by set name ({set: {slot, stall, model, lite, asset}}). "
                    "'standalone' lists vendor models that are not placed at a slot (book_open.glb). "
                    "Round 8: each deco stall has ONE scenery set, prop_deco_<key> at slot_counter: a single merged "
                    "mesh holding the counter goods, the goods hung from slot_rail_1, both back shelves and the "
                    "crate on the slot_crate bench (no act_ nodes, not clickable; Mac, 2026-10-05). The ornament shop's prop_schmuck_* "
                    "sets stand at stall_schmuck.glb's slots (rails, counter, shelf tiers, glass case, tree dais). "
                    "'seat' (when present) says how a set meets its stall: hang (from a rail), stand (on a dais it "
                    "overhangs), ground (in front of the hut); otherwise it stands on a counter or shelf board. "
                    "'retired' lists sets that are no longer placed.",
           "sets": lst,
           "standalone": alone,
           "retired": retired,
           "by_set": {e["set"]: {k: e[k] for k in ("slot", "stall", "model", "lite", "asset")} for e in lst}}
    path = os.path.join(vlib.MODELS, "props.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[props] wrote {path} ({len(lst)} sets)")


def write_items_json(sets, reports):
    items = {}
    for name in sets:
        for node, data in reports.get(name, {}).get("items", {}).items():
            if node in items:
                raise RuntimeError(f"act_ node {node} appears in two sets ({items[node]['set']}, {name})")
            items[node] = {"set": name, "stall": sets[name]["stall"], **data}
    out = {"about": "Display names for the vendor's act_ nodes (node names are unique across all prop sets; the "
                    "full and the lite glb of a set carry the same act_ nodes at the same places). 'pivot' says "
                    "where the node's origin is: 'base' is the point the item rests on. 'action' says what a click does; "
                    "round 10, the Bratwurst plate (ADR 0004 revision): 'plate' puts a fresh copy of the item on act_plate "
                    "at the next free plate_spot_<n> (its 'spots', at most 'max_items'), 'sauce' squeezes a squiggle of "
                    "'colour' from the bottle's 'fx' empty over the plate, 'dust' shakes curry powder ('colour') from "
                    "the shaker's 'fx' empty, 'clear' empties the plate ('clear_note'). Books also carry title, author, their cover material (book_cover_<n>) and the cover's UV "
                    "rect [u_min, v_min, u_max, v_max] in glTF texture space (origin top-left, as three.js samples glTF "
                    "textures) in prop_tex_books_color.webp.",
           "items": dict(sorted(items.items(), key=lambda kv: (kv[1]["set"], kv[0])))}
    path = os.path.join(vlib.MODELS, "items.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[props] wrote {path} ({len(items)} items)")


if __name__ == "__main__":
    main()
