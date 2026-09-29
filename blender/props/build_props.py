"""Build the vendor's prop sets: full + lite glb (with baked AO), props.json, items.json, reports and
Cycles previews.

    NPM_CONFIG_PREFIX=~/nachtmarkt-tools/npm NM_DEVICE=METAL NM_THREADS=0 \\
    ~/nachtmarkt-tools/bpy-venv/bin/python blender/props/build_props.py [--only a,b] [--no-render]
        [--no-lite] [--no-full] [--no-ao] [--samples 128] [--res 1920x1080] [--render-only a,b]

Outputs
    site/public/models/prop_<set>.glb, prop_<set>.lite.glb, shared prop_tex_*.webp
    site/public/models/props.json      {"sets": [{set, stall, slot, model, lite, asset}]} (the engine's form)
    site/public/models/items.json      every act_ node -> display name (books: title, author, cover)
    blender/out/props_report.json      triangles, bytes, bounding boxes, pivots, items per set
    review/round-1/vendor/*.jpg        wide and close-up previews per section set, a frame per deco set
                                       and the deco contact sheet
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
import set_books  # noqa: E402
import set_deco  # noqa: E402
import set_gluehwein  # noqa: E402
import set_wurst  # noqa: E402

MODULES = [set_gluehwein, set_bier, set_wurst, set_books, set_deco]
STALL_ASSET = {"gluehwein": "stall_gluehwein.glb", "bratwurst": "stall_bratwurst.glb",
               "bierstand": "stall_bier.glb", "buecherstand": "stall_buecher.glb"}
REPORT = os.path.join(vlib.state.OUT_DIR, "props_report.json")


def all_sets():
    out = {}
    for mod in MODULES:
        out.update(mod.SETS)
    return out


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--no-ao", action="store_true", help="skip the AO bake (quick geometry checks only)")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--render-only", default=None, help="comma list: render previews only for these sets")
    a, _ = ap.parse_known_args(sys.argv[1:])
    return a


def build_variant(name, d, lite, ao):
    vlib.reset(d.get("seed", 1), lite)
    ps = d["fn"]()
    if ao:
        vstage.bake_ao(name + (".lite" if lite else ""), vlib.AO_LITE if lite else vlib.AO_FULL,
                       samples=16 if lite else 32)
    return ps, vlib.export_set(name, lite)


def render_previews(name, d, ps, a, res):
    """Section sets: a wide shot and a close-up. Deco sets: one framed shot (also the contact-sheet tile)."""
    top = vstage.preview_scene(ps, d["kind"], d.get("width", 3.0))
    if d.get("section"):
        vstage.shot(d["cam"], top, os.path.join(vlib.REVIEW, f"{name}.jpg"), a.samples, res)
        if d.get("hero"):
            vstage.shot(d["hero"], top, os.path.join(vlib.REVIEW, f"{name}_hero.jpg"), a.samples, res)
        return None
    key = name.replace("prop_deco_", "")
    return vstage.shot(vstage.frame_cam(ps, lens=32), top, os.path.join(vlib.REVIEW, f"deco_{key}.jpg"),
                       a.samples, res)


def main():
    a = args()
    sets = all_sets()
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
            want = a.render_only is None or name in a.render_only.split(",")
            if not a.no_render and want:
                png = render_previews(name, d, ps, a, res)
                if png:
                    r["frame_png"] = png
        r["seconds"] = round(time.time() - t0, 1)
        r["slot"], r["stall"] = d["slot"], d["stall"]
        r["label"] = d.get("label", name)
        reports[name] = r
        print(f"[props] {name}: {json.dumps({k: r.get(k) for k in ('full', 'lite', 'size')})}")
        with open(REPORT, "w") as f:
            json.dump(reports, f, indent=1, ensure_ascii=False)
    sheet = [(reports[n]["frame_png"], reports[n]["label"]) for n in sets
             if n.startswith("prop_deco_") and os.path.exists(reports.get(n, {}).get("frame_png", ""))]
    if len(sheet) == 9 and not a.no_render:
        from nmlib import render
        render.contact_sheet(sheet, os.path.join(vlib.REVIEW, "deco_goods_contact_sheet.jpg"), cols=3,
                             tile=(416, 234), title="Deco stall goods (vendor, round 1 pass 2)")
    write_props_json(sets)
    write_items_json(sets, reports)


def write_props_json(sets):
    """One form only, the list the engine reads (site/src/engine/props.js)."""
    lst = []
    for name, d in sets.items():
        stall = d["stall"]
        key = stall.replace("deco-", "").replace("kartoffelpuffer", "puffer")
        lst.append({"set": name, "stall": stall, "slot": d["slot"], "model": f"{name}.glb",
                    "lite": f"{name}.lite.glb", "asset": STALL_ASSET.get(stall, f"deco_{key}.glb")})
    out = {"about": "Vendor prop sets. Each glb's root node is the set origin: parent it to the named slot_ empty "
                    "of the stall (layout.json id in 'stall', stall file in 'asset').",
           "sets": lst}
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
    out = {"about": "Display names for the vendor's act_ nodes (node names are unique across all prop sets). "
                    "Books also carry title, author, their cover material (book_cover_<n>) and the cover's UV "
                    "rect [u_min, v_min, u_max, v_max] in glTF texture space (origin top-left, as three.js samples glTF "
                    "textures) in prop_tex_books_color.webp.",
           "items": dict(sorted(items.items(), key=lambda kv: (kv[1]["set"], kv[0])))}
    path = os.path.join(vlib.MODELS, "items.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[props] wrote {path} ({len(items)} items)")


if __name__ == "__main__":
    main()
