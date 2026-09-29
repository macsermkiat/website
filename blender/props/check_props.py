"""Check the vendor's prop sets against the build contract (plain Python, no bpy).

    python3 blender/props/check_props.py

- props.json maps every prop_*.glb to a stall and slot, and every set has a .lite.glb
- the required act_ nodes exist (mugs, taps, glasses + foam, grill, sausages, books)
- section stall + its prop sets stay within 60k triangles (full) and 3 MB (with the shared atlas)
- bounding boxes and pivots from blender/out/props_report.json (written by build_props.py)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
import glb_tools  # noqa: E402

MODELS = os.path.join(REPO, "site", "public", "models")
REQUIRED = {
    "prop_gluehwein_counter": ["act_pot_lid", "act_mug_0", "act_mug_7"],
    "prop_bier_counter": ["act_tap_0", "act_tap_1", "act_tap_2", "act_glass_0", "foam_0"],
    "prop_wurst_counter": ["act_grill", "act_sausage_0"],
    "prop_books_shelf_1": ["act_book_0"],
    "prop_books_shelf_2": ["act_book_100"],
    "prop_books_counter": ["light_lamp"],
}
SECTION = {"gluehwein": "stall_gluehwein", "bierstand": "stall_bier", "bratwurst": "stall_bratwurst",
           "buecherstand": "stall_buecher"}
DECO_KEYS = ["lebkuchen", "mandeln", "kerzen", "spielzeug", "schmuck", "kaese", "crepes", "maroni", "puffer"]


def main():
    ok = True
    with open(os.path.join(MODELS, "props.json")) as f:
        pj = json.load(f)
    sets = {k: v for k, v in pj.items() if k.startswith("prop_")}
    files = sorted(f[:-4] for f in os.listdir(MODELS) if f.startswith("prop_") and f.endswith(".glb")
                   and not f.endswith(".lite.glb"))
    for f in files:
        if f not in sets:
            print("NOT IN props.json:", f)
            ok = False
    for d in DECO_KEYS:
        if f"prop_deco_{d}" not in sets:
            print("missing deco set", d)
            ok = False
    rep = {}
    rp = os.path.join(REPO, "blender", "out", "props_report.json")
    if os.path.exists(rp):
        with open(rp) as f:
            rep = json.load(f)
    tex = sum(os.path.getsize(os.path.join(MODELS, t)) for t in os.listdir(MODELS)
              if t.startswith("prop_tex_") and ".lite." not in t)
    tex_lite = sum(os.path.getsize(os.path.join(MODELS, t)) for t in os.listdir(MODELS)
                   if t.startswith("prop_tex_") and ".lite." in t)
    per_stall = {}
    print(f"{'set':26s} {'stall':16s} {'slot':13s} {'tris':>6s} {'lite':>6s} {'kB':>5s} {'lite kB':>7s}  size (m)")
    for name, e in sets.items():
        full = os.path.join(MODELS, e["model"])
        lite = os.path.join(MODELS, e["lite"])
        for p in (full, lite):
            if not os.path.exists(p):
                print("MISSING FILE", p)
                ok = False
        rf, rl = glb_tools.report(full), glb_tools.report(lite)
        for n in REQUIRED.get(name, []):
            for r in (rf, rl):
                if n not in r["nodes"]:
                    print(f"{name}: node {n} missing in {os.path.basename(r['file'])}")
                    ok = False
        size = rep.get(name, {}).get("size")
        print(f"{name:26s} {e['stall']:16s} {e['slot']:13s} {rf['triangles']:6d} {rl['triangles']:6d} "
              f"{rf['bytes'] / 1e3:5.0f} {rl['bytes'] / 1e3:7.0f}  {size}")
        if size and (size[1] > 0.5 + 1e-3):
            print(f"  ! {name} is {size[1]:.3f} m deep (> 0.5)")
            ok = False
        per_stall.setdefault(e["stall"], []).append((rf, rl))
    print(f"\nshared atlas textures: {tex / 1e6:.2f} MB (lite {tex_lite / 1e6:.2f} MB), loaded once for all sets")
    print(f"\n{'section stall':16s} {'stall tris':>10s} {'+ props':>8s} {'= total':>8s} {'budget':>7s} {'MB total':>9s}")
    for stall, base in SECTION.items():
        sr = glb_tools.report(os.path.join(MODELS, base + ".glb"))
        pt = sum(r[0]["triangles"] for r in per_stall.get(stall, []))
        pb = sum(r[0]["bytes"] for r in per_stall.get(stall, []))
        tot = sr["triangles"] + pt
        mb = (sr["bytes"] + pb + tex) / 1e6
        flag = "OK" if tot <= 60000 and mb <= 3.0 else "OVER"
        ok &= flag == "OK"
        print(f"{stall:16s} {sr['triangles']:10d} {pt:8d} {tot:8d} {60000:7d} {mb:9.2f}  {flag}")
    print(f"\n{'deco stall':16s} {'stall tris':>10s} {'+ goods':>8s} {'= total':>8s} {'budget':>7s}")
    for d in DECO_KEYS:
        sid = "deco-" + ("kartoffelpuffer" if d == "puffer" else d)
        sr = glb_tools.report(os.path.join(MODELS, f"deco_{d}.glb"))
        pt = sum(r[0]["triangles"] for r in per_stall.get(sid, []))
        tot = sr["triangles"] + pt
        print(f"{d:16s} {sr['triangles']:10d} {pt:8d} {tot:8d} {20000:7d}  {'OK' if tot <= 20000 else 'over'}")
    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
