"""Quick triangle totals of prop sets without exporting (vendor tool):
    /home/claude/tools/bpy-venv/bin/python blender/props/tri_all.py [prefix] [--lite]"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vlib  # noqa: E402
import build_props  # noqa: E402
pre = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "prop_"
for name, d in build_props.all_sets().items():
    if not name.startswith(pre):
        continue
    out = []
    for lite in (False, True):
        vlib.reset(d.get("seed", 1), lite)
        ps = d["fn"]()
        out.append(ps.tris())
        acts = sorted(n for n in ps.items if n.startswith("act_"))
        fx = sorted(e for e, *_ in ps.empties if e.startswith("fx_"))
    print(f"{name:28s} {out[0]:6d} {out[1]:6d}  acts {len(acts):2d}  fx {fx}")
