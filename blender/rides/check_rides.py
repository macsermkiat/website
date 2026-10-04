"""Check the ride builder's delivered glbs against docs/BUILD.md (plain Python, no Blender).

For ferris, carousel, bandstand and the instr_* files, full and lite:
  * triangles and file size (the file plus the external textures it points at that no other
    role ships, i.e. rides_kit_*) against the budget rows;
  * every node the contract and the round 6 brief name (rot_, gondola_/horse_, seats, slots,
    cam_view/cam_target, write_/cam_read_ pairs);
  * every external texture URI exists in site/public/models;
  * write_ meshes have UVs (the engine recovers the writing area from them);
  * the lite file has the same named nodes as the full one (the engine grafts full onto lite).

    python3 blender/rides/check_rides.py            # exit 1 on any failure
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
import glb_tools  # noqa: E402

MODELS = os.path.join(REPO, "site", "public", "models")
PAIRS = lambda *ks: [n for k in ks for n in (f"write_{k}", f"cam_read_{k}", f"cam_read_{k}_target")]  # noqa: E731
REQ = {
    "ferris": (["rot_wheel", "cam_view", "cam_target", "gondola_seat_0"] + [f"gondola_{i}" for i in range(16)]
               + PAIRS("question_1", "question_2", "question_3", "questions_board"), 80_000, 3.0),
    "carousel": (["rot_platform", "cam_view", "cam_target", "horse_seat_2"] + [f"horse_{i}" for i in range(12)]
                 + PAIRS("contact"), 80_000, 3.0),
    "bandstand": (["cam_view", "cam_target", "slot_sax", "slot_piano", "slot_bass", "slot_drums", "light_0", "light_1"]
                  + PAIRS("music"), None, None),
    "instr_sax": (["instr_sax"], None, None),
    "instr_piano": (["instr_piano"], None, None),
    "instr_bass": (["instr_bass"], None, None),
    "instr_drums": (["instr_drums"], None, None),
    "instr_sax_stand": (["instr_sax_stand"], None, None),
}
BAND_BUDGET = (50_000, 2.0)       # bandstand with the four instruments
BAND_SET = ["bandstand", "instr_sax", "instr_piano", "instr_bass", "instr_drums"]


def info(name):
    p = os.path.join(MODELS, name + ".glb")
    js, binc = glb_tools.read_glb(p)
    names = glb_tools.node_names(js)
    tris = glb_tools.triangle_count(js)
    uris = [im["uri"] for im in js.get("images", []) if "uri" in im]
    own = sum(os.path.getsize(os.path.join(MODELS, u)) for u in uris
              if u.startswith("rides_kit_") and os.path.exists(os.path.join(MODELS, u)))
    missing = [u for u in uris if not os.path.exists(os.path.join(MODELS, u))]
    # write_ meshes must carry TEXCOORD_0
    nodes = js.get("nodes", [])
    no_uv = []
    for n in nodes:
        if n.get("name", "").startswith("write_"):
            m = n.get("mesh")
            if m is None:
                kids = [nodes[c] for c in n.get("children", []) if "mesh" in nodes[c]]
                m = kids[0]["mesh"] if kids else None
            if m is None or not all("TEXCOORD_0" in pr["attributes"] for pr in js["meshes"][m]["primitives"]):
                no_uv.append(n["name"])
    return dict(names=set(names), tris=tris, bytes=os.path.getsize(p), uris=uris, missing=missing,
                no_uv=no_uv, shared_bytes=own)


def main():
    bad = 0
    rows = []
    band = {"full": [0, 0], "lite": [0, 0]}
    for name, (req, tmax, mbmax) in REQ.items():
        full = info(name)
        lite = info(name + ".lite")
        for tag, d in (("full", full), ("lite", lite)):
            miss = [r for r in req if r not in d["names"]]
            errs = []
            if miss:
                errs.append(f"missing nodes {miss}")
            if d["missing"]:
                errs.append(f"missing textures {d['missing']}")
            if d["no_uv"]:
                errs.append(f"write_ without UVs {d['no_uv']}")
            if tag == "full" and tmax and (d["tris"] > tmax or d["bytes"] / 1e6 > mbmax):
                errs.append(f"over budget ({tmax} tris / {mbmax} MB)")
            if name in BAND_SET:
                band[tag][0] += d["tris"]
                band[tag][1] += d["bytes"]
            rows.append((name + (".lite" if tag == "lite" else ""), d["tris"], d["bytes"], errs))
            bad += bool(errs)
        keep = {n for n in full["names"] if n.startswith(("write_", "cam_", "slot_", "rot_", "gondola_", "horse_",
                                                          "light_", "instr_", "act_"))}
        diff = sorted(keep - lite["names"])
        if diff:
            rows.append((name + " lite vs full", 0, 0, [f"lite lacks {diff}"]))
            bad += 1
    print(f"{'file':26s} {'triangles':>10s} {'MB':>7s}  status")
    for n, t, b, e in rows:
        print(f"{n:26s} {t:10,d} {b / 1e6:7.2f}  {'OK' if not e else '; '.join(e)}")
    for tag in ("full", "lite"):
        t, b = band[tag]
        over = tag == "full" and (t > BAND_BUDGET[0] or b / 1e6 > BAND_BUDGET[1])
        print(f"{'bandstand + 4 instr (' + tag + ')':26s} {t:10,d} {b / 1e6:7.2f}  "
              f"{'OVER ' + str(BAND_BUDGET) if over else 'OK'}")
        bad += over
    shared = sorted(f for f in os.listdir(MODELS) if f.startswith("rides_kit_"))
    print("shared rides_kit files:", ", ".join(f"{f} ({os.path.getsize(os.path.join(MODELS, f)) // 1024} KB)"
                                            for f in shared))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
