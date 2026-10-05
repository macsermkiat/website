"""Rewrite the stroll's path_ empties in square.glb and square.lite.glb from site/src/layout.json.

Plain Python 3, no Blender.  square.py writes path_000... from the loop legs when it builds the square;
after stroll.py re-plans the legs (round 9: the ornament shop's cam_view moved), this patches only the
glTF JSON chunk: the old path_ nodes go, the new ones are appended as scene roots in walking order.
Meshes, textures and buffers are untouched.

Run:  python3 blender/square/refresh_paths.py
"""
import json, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LAYOUT = os.path.join(REPO, "site", "src", "layout.json")
MODELS = os.path.join(REPO, "site", "public", "models")


def read_glb(path):
    b = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", b, 0)
    assert magic == 0x46546C67 and ver == 2
    off, chunks = 12, []
    while off < total:
        ln, typ = struct.unpack_from("<II", b, off)
        chunks.append([typ, b[off + 8: off + 8 + ln]])
        off += 8 + ln
    return chunks


def write_glb(path, chunks):
    out = b""
    for typ, data in chunks:
        pad = (b" " if typ == 0x4E4F534A else b"\0") * ((4 - len(data) % 4) % 4)
        data = data + pad
        out += struct.pack("<II", len(data), typ) + data
    with open(path + ".tmp", "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + len(out)) + out)
    os.replace(path + ".tmp", path)


def patch(path, points):
    chunks = read_glb(path)
    g = json.loads(chunks[0][1].decode("utf8"))
    nodes = g["nodes"]
    keep = [i for i, n in enumerate(nodes) if not n.get("name", "").startswith("path_")]
    remap = {old: new for new, old in enumerate(keep)}
    # a path_ node must be a childless root (as square.py makes them)
    for i, n in enumerate(nodes):
        if n.get("name", "").startswith("path_"):
            assert not n.get("children") and "mesh" not in n, n
    new_nodes = [nodes[i] for i in keep]
    for n in new_nodes:
        if "children" in n:
            n["children"] = [remap[c] for c in n["children"]]
    for key in ("skins", "animations"):
        assert not g.get(key), f"{key} present; extend the remap"
    added = []
    for k, (x, y, z) in enumerate(points):
        added.append(len(new_nodes))
        new_nodes.append({"name": f"path_{k:03d}", "translation": [x, y, z]})
    g["nodes"] = new_nodes
    for s in g["scenes"]:
        s["nodes"] = [remap[i] for i in s["nodes"] if i in remap] + added
    chunks[0][1] = json.dumps(g, separators=(",", ":")).encode("utf8")
    write_glb(path, chunks)
    print(f"[paths] {os.path.basename(path)}: {len(nodes) - len(keep)} old path_ nodes -> {len(points)} new")


def main():
    L = json.load(open(LAYOUT))
    pts = [p for lg in L["stroll"]["legs"] if lg["loop"] for p in lg["points"]]
    for f in ("square.glb", "square.lite.glb"):
        patch(os.path.join(MODELS, f), pts)


if __name__ == "__main__":
    main()
