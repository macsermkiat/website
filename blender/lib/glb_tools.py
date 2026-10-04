"""Plain-Python GLB tools (no bpy needed): inspect, check named nodes, externalise shared textures.

    python3 blender/lib/glb_tools.py report  site/public/models/stall_bier.glb
    python3 blender/lib/glb_tools.py check   site/public/models/stall_bier.glb   (stall node contract)

Used by nmlib.export; importable on its own.
"""
import json
import os
import struct
import sys
import hashlib

STALL_REQUIRED = ["slot_counter", "slot_shelf_1", "slot_shelf_2", "slot_vendor", "slot_sign",
                  "slot_front", "cam_view", "cam_target"]
STALL_PREFIXES = ["light_", "bulbs_", "snow_"]


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", f"{path} is not a GLB"
    off = 12
    js, binchunk = None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<I4s", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            binchunk = chunk
        off += 8 + clen
    return js, binchunk


def write_glb(path, js, binchunk):
    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    binchunk = bytes(binchunk)
    binchunk += b"\x00" * ((4 - len(binchunk) % 4) % 4)
    total = 12 + 8 + len(jb) + (8 + len(binchunk) if binchunk else 0)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(jb), b"JSON"))
        f.write(jb)
        if binchunk:
            f.write(struct.pack("<I4s", len(binchunk), b"BIN\x00"))
            f.write(binchunk)


def triangle_count(js):
    """Triangles drawn by the default scene (mesh instances counted once per node)."""
    acc = js.get("accessors", [])
    per_mesh = []
    for m in js.get("meshes", []):
        t = 0
        for p in m["primitives"]:
            if p.get("mode", 4) != 4:
                continue
            if "indices" in p:
                t += acc[p["indices"]]["count"] // 3
            else:
                t += acc[p["attributes"]["POSITION"]]["count"] // 3
        per_mesh.append(t)
    total = 0
    for n in js.get("nodes", []):
        if "mesh" in n:
            k = 1
            inst = n.get("extensions", {}).get("EXT_mesh_gpu_instancing")
            if inst:
                k = acc[inst["attributes"]["TRANSLATION"]]["count"] if "TRANSLATION" in inst["attributes"] else 1
            total += per_mesh[n["mesh"]] * k
    return total


def node_names(js):
    return [n.get("name", "") for n in js.get("nodes", [])]


def buecher_required():
    """slot_cat_<key>, sign_cat_<key>, cam_cat_<key> and cam_cat_<key>_target for every key in content/books/categories.json."""
    import json
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(repo, "content", "books", "categories.json")) as f:
        keys = [c["key"] for c in json.load(f)["categories"]]
    return ([f"slot_cat_{k}" for k in keys] + [f"sign_cat_{k}" for k in keys] + [f"cam_cat_{k}" for k in keys]
            + [f"cam_cat_{k}_target" for k in keys])


# round 6 (docs/adr/0003): the writing surfaces each section stall carries
# (write_<name> mesh, cam_read_<name> and cam_read_<name>_target empties)
WRITE_REQUIRED = {"stall_gluehwein": ["about"], "stall_bier": ["projects_board"],
                  "stall_bratwurst": ["writing_menu"]}


def write_required(base):
    names = []
    for stall, keys in WRITE_REQUIRED.items():
        if base == stall + ".glb" or base == stall + ".lite.glb":
            for k in keys:
                names += [f"write_{k}", f"cam_read_{k}", f"cam_read_{k}_target"]
    return names


def check_stall(path, extra_required=()):
    js, _ = read_glb(path)
    names = node_names(js)
    base = os.path.basename(path)
    if base.startswith("stall_buecher"):
        extra_required = list(extra_required) + buecher_required()
    extra_required = list(extra_required) + write_required(base)
    missing = [r for r in list(STALL_REQUIRED) + list(extra_required) if r not in names]
    for p in STALL_PREFIXES:
        if not any(n.startswith(p) for n in names):
            missing.append(p + "*")
    mats = [m.get("name") for m in js.get("materials", [])]
    if not any(m in ("bulb_warm", "bulb_cold") for m in mats):
        missing.append("material bulb_warm|bulb_cold")
    return missing


def report(path):
    js, _ = read_glb(path)
    imgs = []
    for im in js.get("images", []):
        if "bufferView" in im:
            imgs.append((im.get("name"), js["bufferViews"][im["bufferView"]]["byteLength"], "embedded"))
        else:
            imgs.append((im.get("name"), 0, im.get("uri")))
    return {
        "file": path,
        "bytes": os.path.getsize(path),
        "triangles": triangle_count(js),
        "nodes": node_names(js),
        "materials": [m.get("name") for m in js.get("materials", [])],
        "images": imgs,
    }


def externalize_images(path, match, uri_for, out_dir):
    """Move images whose name satisfies match(name) out of the GLB into out_dir/uri_for(name).

    The BIN chunk is repacked and every bufferView index is remapped (core accessors,
    sparse accessors, images) including EXT_meshopt_compression ranges.
    Returns {uri: sha1} for the files written or verified.
    """
    js, binc = read_glb(path)
    bvs = js.get("bufferViews", [])
    drop = set()
    written = {}
    for im in js.get("images", []):
        if "bufferView" not in im or not match(im.get("name", "")):
            continue
        bv = bvs[im["bufferView"]]
        blob = binc[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        uri = uri_for(im["name"])
        dst = os.path.join(out_dir, uri)
        sha = hashlib.sha1(blob).hexdigest()
        if os.path.exists(dst):
            with open(dst, "rb") as f:
                old = hashlib.sha1(f.read()).hexdigest()
            if old != sha:  # a shared texture must be byte-identical across variants
                with open(dst, "wb") as f:
                    f.write(blob)
                print(f"[glb_tools] WARNING {uri} differed between variants; overwritten")
        else:
            with open(dst, "wb") as f:
                f.write(blob)
        written[uri] = sha
        drop.add(im["bufferView"])
        del im["bufferView"]
        im["uri"] = uri
    if not drop:
        return written
    # repack buffer 0 (the GLB BIN buffer)
    newbin = bytearray()
    remap_range = {}

    def move(offset, length):
        key = (offset, length)
        if key not in remap_range:
            while len(newbin) % 16:
                newbin.append(0)
            remap_range[key] = len(newbin)
            newbin.extend(binc[offset: offset + length])
        return remap_range[key]

    new_bvs, index_map = [], {}
    for i, bv in enumerate(bvs):
        if i in drop:
            continue
        bv = dict(bv)
        if bv.get("buffer", 0) == 0:
            bv["byteOffset"] = move(bv.get("byteOffset", 0), bv["byteLength"])
        ext = bv.get("extensions", {}).get("EXT_meshopt_compression")
        if ext and ext.get("buffer", 0) == 0:
            ext = dict(ext)
            ext["byteOffset"] = move(ext.get("byteOffset", 0), ext["byteLength"])
            bv["extensions"] = dict(bv["extensions"])
            bv["extensions"]["EXT_meshopt_compression"] = ext
        index_map[i] = len(new_bvs)
        new_bvs.append(bv)
    js["bufferViews"] = new_bvs
    for a in js.get("accessors", []):
        if "bufferView" in a:
            a["bufferView"] = index_map[a["bufferView"]]
        sp = a.get("sparse")
        if sp:
            sp["indices"]["bufferView"] = index_map[sp["indices"]["bufferView"]]
            sp["values"]["bufferView"] = index_map[sp["values"]["bufferView"]]
    for im in js.get("images", []):
        if "bufferView" in im:
            im["bufferView"] = index_map[im["bufferView"]]
    js["buffers"][0]["byteLength"] = len(newbin)
    write_glb(path, js, newbin)
    return written


if __name__ == "__main__":
    cmd, *paths = sys.argv[1:]
    bad = 0
    for p in paths:
        if cmd == "report":
            r = report(p)
            print(f"{os.path.basename(p)}: {r['bytes']/1e6:.2f} MB, {r['triangles']} tris")
            print("  nodes:", ", ".join(r["nodes"]))
            print("  materials:", ", ".join(str(m) for m in r["materials"]))
            for n, b, where in r["images"]:
                print(f"  image {n}: {b/1e3:.0f} kB {where}")
        elif cmd == "check":
            miss = check_stall(p)
            print(os.path.basename(p), "OK" if not miss else f"MISSING {miss}")
            bad += bool(miss)
    sys.exit(1 if bad else 0)
