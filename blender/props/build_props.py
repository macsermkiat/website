"""Build the vendor's prop sets: full + lite glb, props.json, reports and Cycles previews.

    /home/claude/tools/bpy-venv/bin/python blender/props/build_props.py [--only a,b] [--no-render]
        [--no-lite] [--samples 48] [--sheet]

Outputs
    site/public/models/prop_<set>.glb, prop_<set>.lite.glb, shared prop_tex_*.webp
    site/public/models/props.json      set -> {stall, slot, model, lite}; plus "sets" (engine list form)
    blender/out/props_report.json      triangles, bytes, bounding boxes, act_ nodes per set
    review/round-1/vendor/*.jpg        close-ups and the deco contact sheet
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import vlib  # noqa: E402  (imports bpy)
import set_gluehwein  # noqa: E402

MODULES = [set_gluehwein]
for modname in ("set_bier", "set_wurst", "set_books", "set_deco"):
    try:
        MODULES.append(__import__(modname))
    except ImportError as e:
        if "No module named" not in str(e):
            raise

STALL_ASSET = {"gluehwein": "stall_gluehwein.glb", "bratwurst": "stall_bratwurst.glb",
               "bierstand": "stall_bier.glb", "buecherstand": "stall_buecher.glb"}


def all_sets():
    out = {}
    for mod in MODULES:
        out.update(mod.SETS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--sheet", action="store_true", help="render the deco contact sheet")
    ap.add_argument("--render-only", default=None, help="comma list: render previews only for these sets")
    a, _ = ap.parse_known_args(sys.argv[1:])
    sets = all_sets()
    only = a.only.split(",") if a.only else None
    rep_path = os.path.join(vlib.state.OUT_DIR, "props_report.json")
    reports = {}
    if os.path.exists(rep_path):
        with open(rep_path) as f:
            reports = json.load(f)
    os.makedirs(vlib.REVIEW, exist_ok=True)
    res = tuple(int(v) for v in a.res.split("x"))
    sheet = []
    for name, d in sets.items():
        if only and name not in only:
            continue
        t0 = time.time()
        r = reports.get(name, {})
        rep_lite = rep_full = None
        if not a.no_lite:
            vlib.reset(d.get("seed", 1), True)
            ps = d["fn"]()
            rep_lite = vlib.export_set(name, True)
            r["lite"] = {"bytes": rep_lite["bytes"], "triangles": rep_lite["triangles"]}
        if not a.no_full:
            vlib.reset(d.get("seed", 1), False)
            ps = d["fn"]()
            rep_full = vlib.export_set(name, False)
            r.update(vlib.set_report(ps, rep_full, rep_lite))
            if rep_lite:
                r["lite"] = {"bytes": rep_lite["bytes"], "triangles": rep_lite["triangles"]}
            want = a.render_only is None or name in a.render_only.split(",")
            if not a.no_render and d.get("cam"):
                if d.get("section"):
                    jpg = os.path.join(vlib.REVIEW, f"{name}.jpg")
                    want and vlib.preview(ps, d["cam"], jpg, samples=a.samples, res=res, kind=d["kind"],
                                 width=d.get("width", 3.0))
                elif a.sheet:
                    jpg = os.path.join(vlib.state.OUT_DIR, "renders", f"{name}_tile.jpg")
                    png = vlib.preview(ps, d["cam"], jpg, samples=min(a.samples, 32), res=(640, 360),
                                       kind=d["kind"], width=d.get("width", 3.0))
                    sheet.append((png, d.get("label", name)))
        r["seconds"] = round(time.time() - t0, 1)
        r["slot"], r["stall"] = d.get("slot", r.get("slot")), d.get("stall", r.get("stall"))
        reports[name] = r
        print(f"[props] {name}: {json.dumps({k: r.get(k) for k in ('full', 'lite', 'size')})}")
        with open(rep_path, "w") as f:
            json.dump(reports, f, indent=1)
    if sheet and not only:
        from nmlib import render
        render.contact_sheet(sheet, os.path.join(vlib.REVIEW, "deco_goods_contact_sheet.jpg"), cols=3,
                             tile=(416, 234), title="Deco stall goods (vendor, round 1)")
    write_props_json(sets, reports)


def write_props_json(sets, reports):
    """props.json: {set: {slot, stall, model, lite, asset}} plus a "sets" list the engine reads today."""
    out = {"about": "Vendor prop sets. Each glb's root node is the set origin: parent it to the named slot_ "
                    "empty of the stall (layout.json id). 'sets' repeats the same data as a list for the engine."}
    lst = []
    for name, d in sets.items():
        r = reports.get(name, {})
        stall = r.get("stall") or d.get("stall")
        slot = r.get("slot") or d.get("slot")
        e = {"slot": slot, "stall": stall, "model": f"{name}.glb", "lite": f"{name}.lite.glb",
             "asset": STALL_ASSET.get(stall, f"deco_{stall.replace('deco-', '').replace('kartoffelpuffer', 'puffer')}.glb")}
        out[name] = e
        lst.append({"set": name, **e})
    out["sets"] = lst
    path = os.path.join(vlib.MODELS, "props.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[props] wrote {path} ({len(lst)} sets)")


if __name__ == "__main__":
    main()
