"""Guided stroll (docs/adr/0003-guided-stroll-navigation.md): the stop order and the lane paths.

Plain Python 3 (numpy, scipy), no Blender.  It reads site/src/layout.json, the placed glbs (their
cam_view / cam_target empties and bounding boxes, through dump_nodes.mjs), site/src/crowd.json
(the people who stand still) and blender/square/out/furniture.json (lamps, string-light poles,
benches, bins and bollards, written by square.py), and writes the `stroll` key of layout.json:

  stroll.stops  ordered loop: id, label, eye [x,y,z], target [x,y,z] (three.js metres)
  stroll.legs   one leg per pair of stops (the loop's neighbours first, then every other pair, so a
                signpost choice can walk straight there): from, to, loop (true for neighbours),
                length_m and points [[x,y,z], ...] about 2 m apart, starting at `from`'s eye and
                ending at `to`'s eye.  A leg is walked backwards by reversing its points.

The planner is A* on a 0.1 m occupancy grid of the square with a cost that keeps to the middle of
the lanes, then string-pulled, smoothed and resampled.  Every leg is then checked on a
centripetal Catmull-Rom through its points: no point may come within CLEAR_M of a stall's, ride's
or the tree's surface in the walking band (0.05-2.2 m), within FURN_M of a piece of street
furniture, nor within PERSON_M of a person who stands still.
Walkers move, so they are only reported.  A top-down map goes to review/round-5/architect/.

Run:  python3 blender/square/stroll.py         (exit 1 when a leg fails the check)
      CHECK_ONLY=1 python3 blender/square/stroll.py   (check the legs already in layout.json)
"""
import json, math, os, subprocess, sys, heapq
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender", "lib"))
import architect_plan as P            # noqa: E402  (pure python: plaza outline, poles)

LAYOUT = os.path.join(REPO, "site", "src", "layout.json")
CROWD = os.path.join(REPO, "site", "src", "crowd.json")
MODELS = os.path.join(REPO, "site", "public", "models")
FURN = os.path.join(HERE, "out", "furniture.json")
NODES = os.path.join(HERE, "out", "stroll_nodes.json")
REVIEW = os.path.join(REPO, "review", "round-5", "architect")

EYE = 1.6               # walking eye height (m)
CLEAR_M = 0.7           # from a stall's, ride's or the tree's surface in the walking band (0.05-2.2 m)
FURN_M = 0.5            # from a pole, lamp, bench, bin or bollard
PERSON_M = 0.6          # from a standing person's centre
PERSON_R = 0.25
ROBUST = 0.35            # round 5 pass 2: every leg keeps this much spare on top of the clearances
RES = 0.1
EXT = 46.0              # grid covers [-EXT, EXT] in x and z
N = int(2 * EXT / RES)

# The walking order (stroll.py prints the loop length of every order; the shortest is 175.5 m, this one
# 179.9 m, the shortest that opens with Glühwein = About, the host's welcome):
# home -> Glühwein (left centre) -> up the left lane past the Lebkuchen row -> Riesenrad (the overview,
# a spur: the bandstand, the tree and the people round them close the middle of the back) -> back down
# to the Bratwurst (left front) -> along the front lane -> Musikpavillon -> Bierstand -> up the right
# side -> Karussell -> back to the Bücherstand (right front) -> home.  Each side is walked out and back
# once; no other lane is walked twice and no leg is longer than 35 m.
ORDER = ["home", "gluehwein", "riesenrad", "bratwurst", "bandstand", "bierstand", "karussell", "buecherstand"]
LABELS = {"home": ("Marktplatz", "Market square"), "gluehwein": ("Glühwein", "About"),
          "bratwurst": ("Bratwurst", "Writing"), "bierstand": ("Bierstand", "Projects"),
          "buecherstand": ("Bücherstand", "Reading"), "bandstand": ("Musikpavillon", "Music"),
          "riesenrad": ("Riesenrad", "Big questions"), "karussell": ("Karussell", "Contact")}


def rot(x, z, a):
    """three.js rotation about +Y by a (an asset's local x, z to world offsets)."""
    c, s = math.cos(a), math.sin(a)
    return x * c + z * s, -x * s + z * c


def load():
    L = json.load(open(LAYOUT))
    places = {p["id"]: p for p in L["places"]}
    return L, places


def dump_nodes(places):
    files = sorted({os.path.join(MODELS, p["asset"]) for p in places.values()
                    if p["kind"] in ("section", "landmark", "deco") or p["id"] in ("tree", "signpost")})
    newest = max(os.path.getmtime(f) for f in files)
    if not os.path.exists(NODES) or os.path.getmtime(NODES) < newest:
        subprocess.check_call(["node", os.path.join(HERE, "dump_nodes.mjs"), NODES] + files)
    return json.load(open(NODES))


def world(p, local):
    x, y, z = local
    dx, dz = rot(x, z, p.get("rotY", 0.0))
    return [p["pos"][0] + dx, y, p["pos"][1] + dz]


def stops_from(L, places, nodes):
    out = []
    for sid in ORDER:
        de, en = LABELS[sid]
        if sid == "home":
            h = L["camera"]["home"]
            out.append({"id": "home", "label": de, "label_en": en, "eye": h["pos"], "target": h["target"],
                        "source": "camera.home"})
            continue
        p = places[sid]
        n = nodes[p["asset"]]["nodes"]
        if sid == "riesenrad":
            # ferris.glb's cam_view sits 31 m in front of the wheel, in the middle of the market;
            # the stroll stops at the foot of the wheel, by the boarding queue, and looks up at it.
            # `overview` is the view from the top gondola over the whole market (the ADR's overview).
            eye, tgt = world(p, (0.0, 1.7, 12.5)), world(p, (0.0, 9.0, 0.0))
            top = world(p, (0.0, 23.0, 1.2))
            out.append({"id": sid, "label": de, "label_en": en, "eye": eye, "target": tgt,
                        "overview": {"eye": top, "target": [1.0, 1.5, -1.0]},
                        "source": "architect (ferris.glb cam_view is a wide view from mid-market)"})
            continue
        if sid == "karussell":
            # carousel.glb's cam_view sits 13.5 m out, squeezed between the bandstand and the Bierstand;
            # the stroll stops 10.5 m in front of the carousel, beside the children watching it.
            eye, tgt = world(p, (2.0, 1.75, 10.5)), world(p, (0.0, 2.3, 0.0))
            out.append({"id": sid, "label": de, "label_en": en, "eye": eye, "target": tgt,
                        "source": "architect (carousel.glb cam_view is boxed in by the bandstand and Bierstand)"})
            continue
        eye, tgt = world(p, n["cam_view"]), world(p, n["cam_target"])
        out.append({"id": sid, "label": de, "label_en": en, "eye": eye, "target": tgt,
                    "source": f"cam_view / cam_target of {p['asset']}"})
    for s in out:
        s["eye"] = [round(v, 3) for v in s["eye"]]
        s["target"] = [round(v, 3) for v in s["target"]]
    return out


# ------------------------------------------------------------------ obstacles
def to_ij(x, z):
    return int(round((x + EXT) / RES)), int(round((z + EXT) / RES))


def grid_xy():
    c = (np.arange(N) + 0.5) * RES - EXT
    return np.meshgrid(c, c, indexing="ij")        # X[i, j] = x, Z[i, j] = z


def raster_tris(tris_world):
    """Fill xz triangles (k, 6) into a grid mask (PIL polygon fill, then a 1-cell dilation)."""
    from PIL import Image, ImageDraw
    img = Image.new("L", (N, N), 0)
    dr = ImageDraw.Draw(img)
    g = (tris_world + EXT) / RES
    for t in g:
        dr.polygon([(t[0], t[1]), (t[2], t[3]), (t[4], t[5])], fill=1, outline=1)
    m = np.array(img, bool).T                       # [i (x), j (z)]
    return ndimage.binary_dilation(m)


def obstacles(places, nodes, furn):
    """Masks of what the camera must keep clear of: big (stalls, rides, tree) and furniture."""
    X, Z = grid_xy()
    big = np.zeros((N, N), bool)
    named = []                                      # (kind, name, mask) for the report
    for p in places.values():
        if p["kind"] not in ("section", "landmark", "deco") and p["id"] not in ("tree", "signpost"):
            continue
        tf = f"{NODES}.{p['asset']}.tri.bin"
        if os.path.exists(tf):
            t = np.fromfile(tf, np.float32).reshape(-1, 6).astype(float)
            a = p.get("rotY", 0.0)
            w = np.empty_like(t)
            for k in (0, 2, 4):
                dx, dz = rot(t[:, k], t[:, k + 1], a)
                w[:, k], w[:, k + 1] = p["pos"][0] + dx, p["pos"][1] + dz
            m = raster_tris(w)
        else:                                       # no triangles: the asset's bounding box
            b = nodes[p["asset"]]["bounds"]
            (x0, _, z0), (x1, _, z1) = b["min"], b["max"]
            lx, lz = rot(X - p["pos"][0], Z - p["pos"][1], -p.get("rotY", 0.0))
            m = (lx > x0) & (lx < x1) & (lz > z0) & (lz < z1)
        m = ndimage.binary_fill_holes(m)
        big |= m
        named.append(("ride" if p["kind"] == "landmark" else p["kind"], p["id"], m))
    small = np.zeros((N, N), bool)
    for kind, items in furn.items():
        for k, (x, z, r) in enumerate(items):
            m = (X - x) ** 2 + (Z - z) ** 2 < r ** 2
            small |= m
            named.append((kind, f"{kind}_{k}", m))
    # stay on the plaza: 2 m inside its edge (the gutter and the lamps)
    tb = np.arctan2(-Z, X)                                    # Blender angle (Blender y = -z)
    R = np.hypot(X, Z)
    pr = np.vectorize(P.plaza_r)(tb)
    edge = R > pr - 2.0
    return big, small, edge, named


def people(crowd):
    pts, movers = [], []
    for v in crowd.get("vendors", []):
        pts.append((v["pos"][0], v["pos"][2], v["id"]))
    for key in ("queues", "groups", "browsing", "benches"):
        for e in crowd.get(key, []):
            ex, ez = e["pos"]
            for k, m in enumerate(e.get("members", [])):
                pts.append((ex + m["pos"][0], ez + m["pos"][1], f"{e['id']}#{k}"))
    for key in ("walkers", "walkers_more"):
        for w in crowd.get(key, []):
            movers.append((w["id"], w["path"]))
    return pts, movers


# ------------------------------------------------------------------ planning
def astar(cost, start, goal):
    """8-connected A* on the cost grid (inf = blocked)."""
    si, sj = start; gi, gj = goal
    g = np.full(cost.shape, np.inf); g[si, sj] = 0
    came = {}
    h = lambda i, j: math.hypot(i - gi, j - gj)
    pq = [(h(si, sj), 0.0, si, sj)]
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    while pq:
        f, gc, i, j = heapq.heappop(pq)
        if (i, j) == (gi, gj):
            break
        if gc > g[i, j]:
            continue
        for di, dj, d in nb:
            a, b = i + di, j + dj
            if 0 <= a < N and 0 <= b < N:
                c = cost[a, b]
                if not np.isfinite(c):
                    continue
                ng = gc + d * c
                if ng < g[a, b]:
                    g[a, b] = ng; came[(a, b)] = (i, j)
                    heapq.heappush(pq, (ng + h(a, b), ng, a, b))
    if (gi, gj) not in came and (gi, gj) != (si, sj):
        raise RuntimeError(f"no path {start} -> {goal}")
    path = [(gi, gj)]
    while path[-1] != (si, sj):
        path.append(came[path[-1]])
    return path[::-1]


def los(clear, a, b, need):
    """True if the straight segment a-b (metres) keeps `need` clearance everywhere."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(2, int(L / (RES * 0.5)))
    for k in range(n + 1):
        t = k / n
        i, j = to_ij(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        if not (0 <= i < N and 0 <= j < N) or clear[i, j] < need:
            return False
    return True


def catmull(pts, per=8, alpha=0.5):
    """Catmull-Rom through pts (list of 3-vectors); alpha 0.5 is centripetal (what the engine should
    use), 0 uniform and 1 chordal (checked too, so a different curve tension cannot clip anything)."""
    P_ = [np.array(p, float) for p in pts]
    P_ = [2 * P_[0] - P_[1]] + P_ + [2 * P_[-1] - P_[-2]]
    out = []
    for k in range(1, len(P_) - 2):
        p0, p1, p2, p3 = P_[k - 1], P_[k], P_[k + 1], P_[k + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-4) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-4) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-4) ** alpha
        for s in range(per):
            t = t1 + (t2 - t1) * s / per
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P_[-2])
    return np.array(out)


def resample(poly, step):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    n = max(2, int(round(d[-1] / step)) + 1)
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, poly[:, k]) for k in range(poly.shape[1])], 1), d[-1]


def approach_point(stop, back=2.4):
    """A point `back` metres behind a stop's eye, along its view, so the walk arrives facing it."""
    e, t = np.array(stop["eye"]), np.array(stop["target"])
    f = np.array([t[0] - e[0], t[2] - e[2]]); f /= np.linalg.norm(f)
    return (e[0] - f[0] * back, e[2] - f[1] * back)


def plan_leg(cost, clear, A, B):
    a2, b2 = (A["eye"][0], A["eye"][2]), (B["eye"][0], B["eye"][2])
    if A["id"] == "home":
        a_out = (1.0, 17.0)           # walk down from the home view onto the front lane
    else:
        a_out = approach_point(A)
    b_in = (1.0, 17.0) if B["id"] == "home" else approach_point(B)
    cells = astar(cost, to_ij(*a_out), to_ij(*b_in))
    xy = [((i + 0.5) * RES - EXT, (j + 0.5) * RES - EXT) for i, j in cells]
    # string-pull: keep the farthest point still in sight with full clearance (+ a margin)
    pulled = [xy[0]]; k = 0
    while k < len(xy) - 1:
        far = k + 1
        for m in range(len(xy) - 1, k, -1):
            if los(clear, xy[k], xy[m], 0.5):
                far = m; break
        pulled.append(xy[far]); k = far
    # dense polyline -> Chaikin smoothing (corners cut, ends kept) -> resample
    poly = np.array(([a2] if A["id"] != "home" else []) + pulled + ([b2] if B["id"] != "home" else []), float)
    for _ in range(4):
        q = [poly[0]]
        for u, v in zip(poly[:-1], poly[1:]):
            q += [0.75 * u + 0.25 * v, 0.25 * u + 0.75 * v]
        q.append(poly[-1]); poly = np.array(q)
    pts2, length = resample(poly, 2.0)
    # heights: eye height on the lane, easing into each stop's own camera height over the last 4 m
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts2, axis=0), axis=1))]
    ys = np.full(len(pts2), EYE)
    ease = lambda u: u * u * (3 - 2 * u)
    for k in range(len(pts2)):
        if A["id"] != "home":
            ys[k] += (A["eye"][1] - EYE) * (1 - ease(min(1.0, d[k] / 4.0)))
        if B["id"] != "home":
            ys[k] += (B["eye"][1] - EYE) * (1 - ease(min(1.0, (d[-1] - d[k]) / 4.0)))
    pts2 = push_clear(pts2, clear, keep_first=A["id"] != "home", keep_last=B["id"] != "home")
    pts = [[round(x, 3), round(y, 3), round(z, 3)] for (x, z), y in zip(pts2, ys)]
    # the home end: from the home camera (9 m up) down onto the front lane, a gentle descent
    if A["id"] == "home":
        pts = home_descent(A["eye"], pts[0]) + pts[1:]
    if B["id"] == "home":
        pts = pts[:-1] + home_descent(B["eye"], pts[-1])[::-1]
    return pts


_GRAD = {}


def push_clear(pts2, margin, want=0.7, keep_first=True, keep_last=True):
    """Nudge path points uphill on the clearance margin until each has `want` metres to spare, then
    re-check the Catmull-Rom between them and nudge the curve's worst spots' neighbours too."""
    if "g" not in _GRAD:
        sm = ndimage.gaussian_filter(np.clip(margin, -1, 3), 3)
        _GRAD["g"] = (np.gradient(sm, RES), sm)
    (gx, gz), sm = _GRAD["g"]
    pts2 = np.array(pts2, float)
    lo, hi = (1 if keep_first else 0), (len(pts2) - 1 if keep_last else len(pts2))

    def m_at(x, z):
        i, j = to_ij(x, z)
        return margin[i, j] if (0 <= i < N and 0 <= j < N) else -9

    def nudge(k):
        for _ in range(40):
            x, z = pts2[k]
            if m_at(x, z) >= want:
                return
            i, j = to_ij(x, z)
            g = np.array([gx[i, j], gz[i, j]])
            n = np.linalg.norm(g)
            if n < 1e-6:
                return
            pts2[k] += g / n * 0.05

    for k in range(lo, hi):
        nudge(k)
    for _ in range(14):                      # the curve between points can still cut a corner
        bad = []
        for al in (0.5, 0.0, 1.0):           # centripetal, uniform and chordal
            cur = catmull([[x, 0, z] for x, z in pts2], per=10, alpha=al)
            bad += [q for q, p in enumerate(cur) if m_at(p[0], p[2]) < ROBUST]
        if not bad:
            break
        for q in sorted(set(bad)):
            k = q // 10
            for kk in (k, k + 1):
                if lo <= kk < hi:
                    pts2[kk] = pts2[kk]          # copy
                    x, z = pts2[kk]
                    i, j = to_ij(x, z)
                    g = np.array([gx[i, j], gz[i, j]]); n = np.linalg.norm(g)
                    if n > 1e-6:
                        pts2[kk] += g / n * 0.08
    return pts2


def home_descent(home, lane):
    """Points from the home camera down to `lane` (on the front lane at eye height)."""
    h, l = np.array(home, float), np.array(lane, float)
    out = []
    n = 6
    for k in range(n):
        u = k / (n - 1)
        p = h + (l - h) * u
        p[1] = h[1] + (l[1] - h[1]) * (u * u * (3 - 2 * u))
        out.append([round(float(v), 3) for v in p])
    return out


# ------------------------------------------------------------------ check
def check_leg(pts, margin, d_big, d_small, named, ppl, edge):
    """Check the Catmull-Rom through a leg's points; returns (worst margin, nearest person, failures)."""
    dense = np.concatenate([catmull(pts, per=10, alpha=al) for al in (0.5, 0.0, 1.0)])
    worst = (99.0, None)
    fails = []
    for p in dense:
        x, y, z = p
        if y > 3.5:                       # the descent from the home camera is above everything here
            continue
        i, j = to_ij(x, z)
        if not (0 <= i < N and 0 <= j < N):
            fails.append(("off grid", (x, z))); continue
        mb, ms = d_big[i, j] - CLEAR_M, d_small[i, j] - FURN_M
        c = min(mb, ms)
        if c < worst[0]:
            worst = (round(float(c), 2), (round(float(x), 2), round(float(z), 2)))
        if c < 0:
            who = [nm for kind, nm, m in named if m[max(0, i - 15):i + 16, max(0, j - 15):j + 16].any()]
            fails.append((f"{'stall/ride/tree' if mb < ms else 'furniture'} {c:+.2f} m", (round(float(x), 2), round(float(z), 2)), who[:3]))
        if edge[i, j]:
            fails.append(("off the plaza", (round(float(x), 2), round(float(z), 2))))
    pmin = (99.0, None)
    low = dense[dense[:, 1] <= 3.5]
    for (px, pz, pid) in ppl:
        if not len(low):
            break
        dd = float(np.hypot(low[:, 0] - px, low[:, 2] - pz).min())
        if dd < pmin[0]:
            pmin = (round(dd, 2), pid)
        if dd < PERSON_M:
            fails.append((f"person {pid} at {dd:.2f} m", (px, pz)))
    return worst, pmin, fails


def main():
    L, places = load()
    nodes = dump_nodes(places)
    furn = json.load(open(FURN))
    crowd = json.load(open(CROWD)) if os.path.exists(CROWD) else {}
    big, small, edge, named = obstacles(places, nodes, furn)
    ppl, movers = people(crowd)
    pc = np.zeros((N, N), bool)
    for (px, pz, _) in ppl:
        i, j = to_ij(px, pz)
        if 0 <= i < N and 0 <= j < N:
            pc[i, j] = True
    d_big = ndimage.distance_transform_edt(~big) * RES
    d_small = ndimage.distance_transform_edt(~small) * RES
    d_ppl = ndimage.distance_transform_edt(~pc) * RES if pc.any() else np.full((N, N), 99.0)
    # margin: how far the camera could still move toward the nearest thing before it is too close
    margin = np.minimum(np.minimum(d_big - CLEAR_M, d_small - FURN_M), d_ppl - PERSON_M)
    margin[edge] = -1
    solid = big | small

    if os.environ.get("CHECK_ONLY"):
        stops = L["stroll"]["stops"]; legs = L["stroll"]["legs"]
    else:
        stops = stops_from(L, places, nodes)
        # cost: blocked below the clearance; otherwise favour the middle of the lanes
        cost = np.where(margin >= 0.3, 1.0 + 1.6 / np.maximum(margin + 0.4, 0.3) ** 1.5, np.inf)
        # let the planner leave and reach the stops even where a stop sits a little tight
        for s in stops:
            for pt in ((s["eye"][0], s["eye"][2]), approach_point(s) if s["id"] != "home" else (1.0, 17.0)):
                i, j = to_ij(*pt)
                cost[max(0, i - 6):i + 7, max(0, j - 6):j + 7] = np.where(
                    np.isfinite(cost[max(0, i - 6):i + 7, max(0, j - 6):j + 7]), cost[max(0, i - 6):i + 7, max(0, j - 6):j + 7], 3.0)
        byid = {s["id"]: s for s in stops}
        pairs = [(ORDER[k], ORDER[(k + 1) % len(ORDER)], True) for k in range(len(ORDER))]
        for a in range(len(ORDER)):
            for b in range(a + 2, len(ORDER)):
                if (a, b) != (0, len(ORDER) - 1):
                    pairs.append((ORDER[a], ORDER[b], False))
        legs = []
        unplanned = []
        for a, b, loop in pairs:
            try:
                pts = plan_leg(cost, margin, byid[a], byid[b])
            except RuntimeError as e:
                print(f"[stroll] {a} -> {b}: {e}"); unplanned.append((a, b)); continue
            length = float(np.sum(np.linalg.norm(np.diff(np.array(pts), axis=0), axis=1)))
            legs.append({"from": a, "to": b, "loop": loop, "length_m": round(length, 1), "points": pts})
            print(f"[stroll] {a:>12} -> {b:<12} {'loop' if loop else 'jump'} {length:5.1f} m, {len(pts)} points")

    # ---- check every leg
    bad = 0
    warn = 0
    report = []
    for lg in legs:
        worst, pmin, fails = check_leg(lg["points"], margin, d_big, d_small, named, ppl, edge)
        wm = []
        for wid, path in movers:
            wp = np.array(path, float)
            dense = catmull(lg["points"], per=10)
            dd = min(float(np.min(np.hypot(*(seg_pts(wp) - np.array([p[0], p[2]])).T))) for p in dense if p[1] <= 3.5) if len(dense) else 99
            if dd < 0.8:
                wm.append(f"{wid} ({dd:.2f} m)")
        line = (f"{lg['from']:>12} -> {lg['to']:<12} {lg['length_m']:5.1f} m  spare clearance {worst[0]:.2f} m at {worst[1]}"
                f"  nearest standing person {pmin[0]:.2f} m ({pmin[1]})")
        if wm:
            line += "  crosses walker paths: " + ", ".join(wm[:4])
        if worst[0] < ROBUST or pmin[0] < PERSON_M + ROBUST:
            line += f"  WARN below the {ROBUST} m robustness target"
            warn += 1
        report.append(line)
        print("[check]", line)
        for f in fails:
            print("   FAIL", f); bad += 1
    # stops themselves
    for s in stops[1:]:
        i, j = to_ij(s["eye"][0], s["eye"][2])
        print(f"[stop] {s['id']:>12} eye {s['eye']} spare clearance {margin[i, j]:.2f} m")

    if not os.environ.get("CHECK_ONLY"):
        path_nodes = []
        k = 0
        for lg in legs:
            if lg["loop"]:
                lg["path_nodes"] = [f"path_{k:03d}", f"path_{k + len(lg['points']) - 1:03d}"]
                k += len(lg["points"])
        L["stroll"] = {
            "about": ("Guided stroll (docs/adr/0003). stops is the loop in walking order (prev/next walk to the "
                      "neighbouring stop); a stop's eye/target are three.js metres and match the place's cam_view / "
                      "cam_target (riesenrad: the foot of the wheel, with `overview` the view from the top gondola). "
                      "legs holds one path per pair of stops: loop legs join neighbours, the rest let a signpost "
                      "choice walk straight to any stop. points run from `from`'s eye to `to`'s eye, about 2 m "
                      "apart, at eye height 1.6 m on the lanes and easing into each stop's own camera height; walk a "
                      "leg backwards by reversing it. Interpolate with a centripetal Catmull-Rom: stroll.py checks "
                      "that curve keeps 0.7 m from every stall, ride and the tree (their surfaces between 0.05 and 2.2 m "
                      "up), 0.5 m from every pole, lamp, bench, bin and bollard and 0.6 m from the centre of every "
                      "standing person in crowd.json (walkers move, so the crowd should let them yield). Look along the path and turn toward the "
                      "stop's target over the last few metres. square.glb carries the loop legs as empties "
                      "path_000... in order (path_nodes gives each loop leg's first and last). Generated by "
                      "blender/square/stroll.py; re-run it after layout or crowd changes."),
            "eye_height": EYE,
            "order": ORDER,
            "stops": stops,
            "legs": legs,
        }
        write_layout(L)
    draw_map(stops, legs, solid, ppl, movers, places, furn)
    with open(os.path.join(HERE, "out", "stroll_check.txt"), "w") as f:
        f.write("\n".join(report) + f"\nfailures: {bad}\nlegs below the {ROBUST} m robustness target: {warn}\n"
                "(checked on centripetal, uniform and chordal Catmull-Rom curves)\n")
    if not os.environ.get("CHECK_ONLY"):
        bad += len(unplanned)
    print(f"[stroll] failures: {bad}")
    sys.exit(1 if bad else 0)


def seg_pts(wp, step=0.2):
    out = []
    for a, b in zip(wp[:-1], wp[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        for k in range(n):
            out.append(a + (b - a) * k / n)
    out.append(wp[-1])
    return np.array(out)


def write_layout(L):
    """Keep layout.json readable: one place per line, one leg's points on a line."""
    places = L.pop("places"); stroll = L.pop("stroll")
    head = "{\n" + ",\n".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in L.items())
    s = head + ',\n  "places": [\n' + ",\n".join("    " + json.dumps(p, ensure_ascii=False) for p in places) + "\n  ],\n"
    s += '  "stroll": {\n'
    s += f'    "about": {json.dumps(stroll["about"], ensure_ascii=False)},\n'
    s += f'    "eye_height": {stroll["eye_height"]},\n'
    s += f'    "order": {json.dumps(stroll["order"])},\n'
    s += '    "stops": [\n' + ",\n".join("      " + json.dumps(st, ensure_ascii=False) for st in stroll["stops"]) + "\n    ],\n"
    s += '    "legs": [\n' + ",\n".join("      " + json.dumps(lg, ensure_ascii=False) for lg in stroll["legs"]) + "\n    ]\n"
    s += "  }\n}\n"
    json.loads(s)
    with open(LAYOUT, "w") as f:
        f.write(s)
    L["places"] = places; L["stroll"] = stroll


def draw_map(stops, legs, solid, ppl, movers, places, furn):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[stroll] no matplotlib, map skipped"); return
    os.makedirs(REVIEW, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12.8, 12.8), dpi=100)
    ax.set_facecolor("#1c1f26")
    ax.imshow(solid.T, origin="lower", extent=[-EXT, EXT, -EXT, EXT], cmap="Greys", alpha=0.85, vmin=0, vmax=1.4)
    th = np.linspace(0, 2 * np.pi, 400)
    pr = np.array([P.plaza_r(t) for t in th])
    ax.plot(pr * np.cos(th), -pr * np.sin(th), color="#777", lw=1)
    for wid, path in movers:
        w = np.array(path); ax.plot(w[:, 0], w[:, 1], color="#4a6b8a", lw=0.8, ls=":")
    for px, pz, _ in ppl:
        ax.add_patch(plt.Circle((px, pz), PERSON_R, color="#e0a040"))
        ax.add_patch(plt.Circle((px, pz), PERSON_M, fill=False, color="#e0a040", lw=0.4))
    for kind, items in furn.items():
        for x, z, r in items:
            ax.add_patch(plt.Circle((x, z), r + FURN_M, fill=False, color="#6fa0d0", lw=0.4))
    for lg in legs:
        d = catmull(lg["points"], per=10)
        if lg["loop"]:
            ax.plot(d[:, 0], d[:, 2], color="#ff5a3c", lw=2.4, zorder=5)
            ax.scatter([p[0] for p in lg["points"]], [p[2] for p in lg["points"]], s=6, color="#ffd0a0", zorder=6)
        else:
            ax.plot(d[:, 0], d[:, 2], color="#7fd07f", lw=0.7, alpha=0.6, zorder=4)
    for k, s in enumerate(stops):
        ax.scatter([s["eye"][0]], [s["eye"][2]], s=80, color="#fff", zorder=7, edgecolor="#ff5a3c")
        ax.annotate(f"{k}. {s['label']}", (s["eye"][0], s["eye"][2]), xytext=(6, 6), textcoords="offset points",
                    color="w", fontsize=11, zorder=8)
        ax.annotate("", xy=(s["target"][0], s["target"][2]), xytext=(s["eye"][0], s["eye"][2]),
                    arrowprops=dict(arrowstyle="->", color="#fff", lw=0.8))
    for p in places.values():
        if p["kind"] in ("section", "landmark", "deco"):
            ax.text(p["pos"][0], p["pos"][1], p["label"], color="#bbb", fontsize=7, ha="center", va="center")
    ax.set_xlim(-34, 34); ax.set_ylim(36, -32)        # +z toward the bottom: the home camera is at the bottom
    ax.set_aspect("equal")
    ax.set_title("Guided stroll, top-down (three.js x right, z down). Red: loop legs; green: direct legs; "
                 "grey: stalls, rides, tree (0.05-2.2 m), furniture; orange: standing people (0.6 m ring); blue: furniture + 0.5 m; dotted: walkers",
                 color="w", fontsize=9)
    fig.patch.set_facecolor("#111")
    ax.tick_params(colors="#aaa")
    fig.tight_layout()
    fig.savefig(os.path.join(REVIEW, "stroll_topdown.jpg"), dpi=100, facecolor="#111")
    print("[stroll] map ->", os.path.join(REVIEW, "stroll_topdown.jpg"))


if __name__ == "__main__":
    main()
