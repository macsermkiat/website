"""Where people may stand and walk: distance fields on a 0.1 m grid of the square, for crowd_plan.py.

Plain Python 3 (numpy, scipy, Pillow). It reads the same sources as the architect's stroll check
(blender/square/stroll.py), so the crowd passes that check by construction:
  - every stall, ride, the tree and the signpost: their triangles in the body band (0.05-2.0 m), placed by
    site/src/layout.json, plus every vendor prop set on its slot (site/public/models/props.json), so nobody
    stands in a crate or a barrel in front of a counter;
  - street furniture (blender/square/out/furniture.json: lamps, benches, bins, bollards) and the string-light
    poles of blender/lib/architect_plan.py;
  - the guided stroll: every leg of layout.json stroll.legs, on the centripetal Catmull-Rom the engine walks;
  - the plaza edge.
Footprints come from blender/people/dump_tris.mjs, cached under blender/out/people/field/.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
import architect_plan as AP  # noqa: E402  (pure python: plaza outline, poles)

LAYOUT = os.path.join(REPO, "site", "src", "layout.json")
MODELS = os.path.join(REPO, "site", "public", "models")
FURN = os.path.join(REPO, "blender", "square", "out", "furniture.json")
CACHE = os.path.join(REPO, "blender", "out", "people", "field", "nodes.json")

RES = 0.1
EXT = 46.0
N = int(2 * EXT / RES)


def rot(x, z, a):
    """three.js rotation about +Y (an asset's local x, z to world offsets); works on arrays."""
    c, s = np.cos(a), np.sin(a)
    return x * c + z * s, -x * s + z * c


def to_ij(x, z):
    return int(round((x + EXT) / RES - 0.5)), int(round((z + EXT) / RES - 0.5))


def catmull(pts, per=8, alpha=0.5):
    """Centripetal Catmull-Rom through pts (3-vectors), as blender/square/stroll.py and the engine walk it."""
    P = [np.array(p, float) for p in pts]
    if len(P) < 2:
        return np.array(P)
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-4) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-4) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-4) ** alpha
        for t in np.linspace(t1, t2, per, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    return np.array(out)


def raster(tris):
    from PIL import Image, ImageDraw
    img = Image.new("L", (N, N), 0)
    dr = ImageDraw.Draw(img)
    g = (tris + EXT) / RES
    for t in g:
        dr.polygon([(t[0], t[1]), (t[2], t[3]), (t[4], t[5])], fill=1, outline=1)
    return np.array(img, bool).T          # [i (x), j (z)]


class Field:
    def __init__(self):
        L = json.load(open(LAYOUT))
        self.layout = L
        self.places = {p["id"]: p for p in L["places"]}
        props = json.load(open(os.path.join(MODELS, "props.json")))
        solid = [p for p in self.places.values() if p["kind"] in ("section", "landmark", "deco")
                 or p["id"] in ("tree", "signpost")]
        args, owners = [], []
        for p in solid:
            args.append(os.path.join(MODELS, p["asset"]))
            owners.append((p["asset"], p))
        # stall slots, then the prop sets on them
        self.nodes = self._dump(args)
        for s in props.get("sets", []):
            p = self.places.get(s["stall"])
            f = os.path.join(MODELS, s["model"])
            if not p or not os.path.exists(f):
                continue
            sl = self.nodes.get(p["asset"], {}).get("nodes", {}).get(s["slot"])
            if not sl:
                continue
            args.append(f"{f}@{sl[0]:.3f},{sl[1]:.3f},{sl[2]:.3f}")
            owners.append((f"{s['model']}@{sl[0]:.3f},{sl[1]:.3f},{sl[2]:.3f}", p))
        self.nodes = self._dump(args)
        X = (np.arange(N) + 0.5) * RES - EXT
        self.X, self.Z = np.meshgrid(X, X, indexing="ij")
        big = np.zeros((N, N), bool)
        self.owner = np.full((N, N), "", dtype=object)
        self.masks = {}
        for key, p in owners:
            tf = f"{CACHE}.{key}.tri.bin"
            if not os.path.exists(tf):
                continue
            t = np.fromfile(tf, np.float32).reshape(-1, 6).astype(float)
            if not len(t):
                continue
            a = p.get("rotY", 0.0)
            w = np.empty_like(t)
            for k in (0, 2, 4):
                dx, dz = rot(t[:, k], t[:, k + 1], a)
                w[:, k], w[:, k + 1] = p["pos"][0] + dx, p["pos"][1] + dz
            m = ndimage.binary_fill_holes(ndimage.binary_dilation(raster(w)))
            big |= m
            self.masks[p["id"]] = self.masks.get(p["id"], np.zeros((N, N), bool)) | m
        self.big = big
        self.d_big = ndimage.distance_transform_edt(~big) * RES
        # furniture (radius already part of each disc) and the string-light poles
        furn = json.load(open(FURN))
        small = np.zeros((N, N), bool)
        self.benches = []
        for kind, items in furn.items():
            if kind == "poles":
                continue
            for x, z, r in items:
                small |= (self.X - x) ** 2 + (self.Z - z) ** 2 < r ** 2
                if kind == "benches":
                    self.benches.append((x, z))
        for k, (x, z) in enumerate(AP.POLES_THREE):
            if k in getattr(AP, "RETIRED_POLES", ()):
                continue
            small |= (self.X - x) ** 2 + (self.Z - z) ** 2 < 0.2 ** 2
        self.small = small
        self.d_small = ndimage.distance_transform_edt(~small) * RES
        # the stroll: every leg on the curve the engine walks
        legs = L["stroll"]["legs"]
        self.legs = legs
        lm = np.zeros((N, N), bool)
        self.leg_pts = []
        for lg in legs:
            d = catmull(lg["points"], per=10)
            self.leg_pts.append((lg["from"], lg["to"], lg.get("loop", False), d))
            for q in d:
                i, j = to_ij(q[0], q[2])
                if 0 <= i < N and 0 <= j < N:
                    lm[i, j] = True
        self.d_leg = ndimage.distance_transform_edt(~lm) * RES
        loop = np.zeros((N, N), bool)
        for f_, t_, is_loop, d in self.leg_pts:
            if is_loop:
                for q in d:
                    i, j = to_ij(q[0], q[2])
                    if 0 <= i < N and 0 <= j < N:
                        loop[i, j] = True
        self.d_loop = ndimage.distance_transform_edt(~loop) * RES
        # the plaza: people keep 1.5 m inside its edge (gutter, lamps)
        tb = np.arctan2(-self.Z, self.X)
        pr = np.vectorize(AP.plaza_r)(tb)
        self.d_edge = pr - np.hypot(self.X, self.Z)

    def _dump(self, args):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        files = [a.split("@")[0] for a in args]
        stale = (not os.path.exists(CACHE) or os.path.getmtime(CACHE) < max(os.path.getmtime(f) for f in files)
                 or set(json.load(open(CACHE)).keys()) != {os.path.basename(a) for a in args})
        if stale:
            subprocess.check_call(["node", os.path.join(HERE, "dump_tris.mjs"), CACHE] + args,
                                  stdout=subprocess.DEVNULL)
        return json.load(open(CACHE))

    def slots(self, pid):
        p = self.places[pid]
        return self.nodes.get(p["asset"], {}).get("nodes", {})

    def sample(self, arr, x, z):
        i, j = to_ij(x, z)
        if not (0 <= i < N and 0 <= j < N):
            return -9.0
        return float(arr[i, j])

    def at(self, x, z):
        """(distance to a stall or prop surface, to furniture, to a stroll leg, to the plaza edge)."""
        return (self.sample(self.d_big, x, z), self.sample(self.d_small, x, z), self.sample(self.d_leg, x, z),
                self.sample(self.d_edge, x, z))

    def stall_at(self, x, z, r=0.0):
        """Which place's footprint (dilated by r m) holds the point, or None."""
        i, j = to_ij(x, z)
        k = max(0, int(round(r / RES)))
        for pid, m in self.masks.items():
            if m[max(0, i - k):i + k + 1, max(0, j - k):j + k + 1].any():
                return pid
        return None
