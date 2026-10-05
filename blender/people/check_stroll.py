"""Run the architect's stroll check (blender/square/stroll.py, CHECK_ONLY) against the current crowd.json
without writing into the architect's folders: its map, report and node cache go to a scratch directory.

    python3 blender/people/check_stroll.py [scratch_dir]      (exit status is the check's)
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
out = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="stroll_check_")
os.makedirs(os.path.join(out, "out"), exist_ok=True)
link = os.path.join(out, "dump_nodes.mjs")
if not os.path.exists(link):
    os.symlink(os.path.join(REPO, "blender", "square", "dump_nodes.mjs"), link)
os.environ["CHECK_ONLY"] = "1"
spec = importlib.util.spec_from_file_location("stroll", os.path.join(REPO, "blender", "square", "stroll.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.REVIEW = out
S.HERE = out
S.NODES = os.path.join(out, "out", "stroll_nodes.json")
print("[check_stroll] writing the map and report to", out)
S.main()
