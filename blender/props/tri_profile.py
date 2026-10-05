"""Triangle profile of prop sets by source line (vendor tool, no export):
    /home/claude/tools/bpy-venv/bin/python blender/props/tri_profile.py prop_deco_puffer [--lite] [--top 25]
Prints the set's total and the source lines (in blender/props/set_*.py) that add the most triangles."""
import collections
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vlib  # noqa: E402
import build_props  # noqa: E402

name = sys.argv[1]
lite = "--lite" in sys.argv
top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 25
acc = collections.Counter()
_add = vlib.Mesh.add


def add(self, verts, faces, uvs, *a, **k):
    n = sum(len(f) - 2 for f in faces)
    for fr in reversed(traceback.extract_stack()[:-1]):
        if os.path.basename(fr.filename).startswith(("set_", "goods")) and fr.name not in ("add",):
            acc[f"{os.path.basename(fr.filename)}:{fr.lineno} {fr.name}"] += n
            break
    return _add(self, verts, faces, uvs, *a, **k)


vlib.Mesh.add = add
d = build_props.all_sets()[name]
vlib.reset(d.get("seed", 1), lite)
ps = d["fn"]()
print(f"{name}{' lite' if lite else ''}: {ps.tris()} tris (static {ps.static.tris}, nodes "
      f"{sum(m.tris for m, *_ in ps.nodes)})")
for k, v in acc.most_common(top):
    print(f"  {v:6d}  {k}")
