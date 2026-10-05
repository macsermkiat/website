"""Generate site/src/crowd.json: who stands where, who walks which path, which clip each plays.

    python3 blender/people/crowd_plan.py [--map review/round-8/organizer/crowd_topdown.jpg]

Coordinates are three.js: pos [x, z] in metres on the ground, rotY in radians (0 = facing +Z).
Positions come from site/src/layout.json (architect: places and the guided stroll) plus the stall glbs'
slot_ empties and footprints (blender/people/crowd_field.py), so the crowd follows the layout when it
changes: re-run this script, then the architect's check  CHECK_ONLY=1 python3 blender/square/stroll.py.

Round 8 (docs/adr/0004): about 80 people over the whole market, a vendor in every deco stall and the
ornament shop, customers at the deco counters, walkers and small groups on every lane and at the edges of
the square. Nobody stands within KEEP_LEG of any stroll leg, inside a stall or prop, or in the near part of a
stop's view. The people at the deco stalls (scenery, Mac: "no need to fully render object in side stores")
name the lite figure file as their model, so the full market never loads or draws a full figure there.

Order matters: the engine flattens the lists in file order and the lite market keeps the first 40 people.
The file is written as vendors, walkers, queues, browsing, groups, benches, walkers_more; the head of that
order (13 vendors, 6 walkers on six lanes, the Gluehwein and Bier queues, one customer per deco counter,
the Buecherstand browsers and the band's listeners) is the lite crowd.
"""
import argparse
import heapq
import json
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "site", "src", "crowd.json")

import crowd_field as CF  # noqa: E402

R = random.Random(1225)
TAU = 2 * math.pi

BASE = ["people_man_coat", "people_woman_coat", "people_man_parka", "people_woman_older", "people_man_older",
        "people_woman_young", "people_child_boy", "people_child_girl", "people_woman_parka"]
VENDORS = {"gluehwein": "people_vendor_gluehwein", "bierstand": "people_vendor_bier",
           "bratwurst": "people_vendor_wurst", "buecherstand": "people_vendor_buecher"}
DECO_M, DECO_F = "people_vendor_deco_m", "people_vendor_deco_f"
VARIANTS = BASE + [VENDORS[k] for k in ("gluehwein", "bierstand", "bratwurst", "buecherstand")] + [DECO_M, DECO_F]
ADULTS = [0, 1, 2, 3, 4, 5, 8]
KIDS = [6, 7]
MEN, WOMEN = [0, 2, 4], [1, 3, 5, 8]
# figures whose lite file the lite market loads anyway (site/src/crowd.js LITE_ALIAS maps the others onto these):
# the lite-only people at the deco stalls use these, so they cost the lite market no extra download
LITE_SAFE_ADULTS = [0, 1, 3, 4]
LITE_SAFE_KIDS = [6]
# the woman in the parka (round 8) is not in the engine's lite alias table: keep her out of the lite crowd
NOT_IN_LITE = {8}

COATS = ["#3a3d44", "#27344a", "#5b5750", "#2f4a3a", "#6a2e3a", "#8a6a4a", "#1f2226", "#4a3b32", "#5c1f2e",
         "#2e5e6e", "#6b6f78", "#a8814f", "#3b4452", "#56402e"]
SCARVES = ["#9e2a2b", "#c8962c", "#e8dcc6", "#2e6f73", "#7b2b2b", "#d9667a", "#2f5f9e", "#6d8b3a", "#b0403a",
           "#d9d2c4", "#5a3d6e", "#c45a2a"]
HATS = ["#6b6158", "#7a2436", "#3d5a3e", "#6a2e4f", "#3b2f27", "#8f8a86", "#e0a33a", "#f0e6d6", "#1f2a44",
        "#a3242c", "#2a2a2e", "#4b6a8a"]
KID_COATS = ["#b23a2e", "#2f5f9e", "#2e5e6e", "#e0a33a", "#6d8b3a", "#8a2f5a"]
GROUP_RADIUS = 0.72     # m from a group's centre; 0.62 in pass 1 let chat hands graze a neighbour's coat

# which clips each figure file carries (blender/people/build.py CLIPSETS); crowd.json only names these
CLIPS_FULL = {"crowd": ["idle", "walk", "chat", "drink", "laugh", "sit", "idle_free", "walk_free", "chat_free"],
              "band": ["play", "rest", "idle", "walk", "chat", "drink"],
              "vendor": ["serve", "wipe", "idle", "walk", "chat", "drink"]}
CLIPS_LITE = {"crowd": ["idle", "walk", "chat", "drink", "sit"], "band": ["play", "rest"], "vendor": ["serve", "wipe"]}
# what site/src/crowd.js plays when a lite figure lacks the clip: idle for standers, walk for walkers (mug hidden
# for *_free clips); every other clip must be in the lite file, because the full market draws far people lite too
LITE_FALLBACK = {"idle_free": "idle", "chat_free": "idle", "laugh": "idle", "walk_free": "walk"}
LITE_CAP = 40
BUECHER_BROWSE_Z = 2.6   # three.js local z of the Buecherstand browsers (in front of the cabinets)
# vendors who sell no drinks serve without the mug (specs.py serve_mug=False)
SERVE_MUG = {"gluehwein": True, "bierstand": True, "bratwurst": False, "buecherstand": False}

# clearances (m) for people who stand still
KEEP_LEG = 1.0          # from every stroll leg (the architect's check fails at 0.6 and warns below 0.95)
KEEP_STALL = 0.35       # centre to a stall, ride or prop surface in the body band
KEEP_FURN = 0.45        # centre to a lamp, pole, bench, bin or bollard disc
KEEP_EDGE = 1.5         # inside the plaza edge
KEEP_PERSON = 0.55      # centre to centre
# walkers: their path keeps this far from stalls and furniture, and prefers to keep off the stroll's loop
WALK_STALL, WALK_FURN, WALK_PERSON = 0.55, 0.35, 0.75

# The close views of the stops. Nobody may stand in the near part of the eye -> target frustum, where they
# would fill the edge of the panel shot, nor in a corridor down the middle to the target (the counter and the
# vendor, the band), where they would stand with their back to the camera in front of what it looks at.
VIEW_NEAR, VIEW_FAR = -1.0, 2.6        # m along the view direction: the near wedge
VIEW_HALF, VIEW_SLOPE = 0.8, 0.75      # its half-width at the camera and growth per metre (desktop fov ~70 deg wide)
VIEW_CORRIDOR = 1.1                    # half-width of the corridor from VIEW_FAR to the target (stalls and the band)

# per-stall vendor looks at the deco stalls and the ornament shop: (figure, coat, scarf, hat, clip)
DECO_LOOK = {
    "deco-schmuck": (DECO_F, "#2f4a3a", "#9e2a2b", "#a3242c", "serve"),
    "deco-lebkuchen": (DECO_F, "#6a2e3a", "#e8dcc6", "#c8962c", "serve"),
    "deco-mandeln": (DECO_M, "#3b4452", "#b0403a", "#7a2436", "serve"),
    "deco-kerzen": (DECO_F, "#4a3b32", "#c8962c", "#f0e6d6", "wipe"),
    "deco-spielzeug": (DECO_M, "#56402e", "#2e6f73", "#a3242c", "wipe"),
    "deco-kaese": (DECO_F, "#27344a", "#e8dcc6", "#6d8b3a", "serve"),
    "deco-crepes": (DECO_M, "#5c1f2e", "#d9d2c4", "#2a2a2e", "serve"),
    "deco-maroni": (DECO_M, "#2f4a3a", "#c45a2a", "#6b6158", "serve"),
    "deco-kartoffelpuffer": (DECO_F, "#3a3d44", "#2e6f73", "#e0a33a", "wipe"),
}
DECO_ORDER = ["deco-lebkuchen", "deco-mandeln", "deco-kerzen", "deco-kaese", "deco-spielzeug", "deco-crepes",
              "deco-maroni", "deco-kartoffelpuffer"]


# ------------------------------------------------------------------ geometry helpers
def rot(v, a):
    """three.js rotation about +Y: local (x, z) -> world offset."""
    x, z = v
    return (x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a))


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def r2(v):
    return [round(v[0], 2), round(v[1], 2)]


def face(frm, to):
    """rotY that turns a figure at frm to face the point to."""
    return math.atan2(to[0] - frm[0], to[1] - frm[1])


def seg_dist(p, a, b):
    ax, az = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + az * az or 1e-9
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * az) / L2))
    return math.hypot(p[0] - a[0] - ax * t, p[1] - a[1] - az * t)


# ------------------------------------------------------------------ people
def person(variant, clip="chat", mug=None, lite_only=False, **kw):
    kid = variant in KIDS
    if mug is None:
        mug = (not kid and R.random() < 0.72) or (kid and R.random() < 0.25)
    if clip in ("laugh", "sit", "drink"):
        mug = True          # laugh_free and sit_free are not shipped; drink needs the mug
    if clip.endswith("_free"):
        mug = False
    if not mug and clip in ("idle", "chat", "walk"):
        clip = clip + "_free"
    colors = {
        "coat": R.choice(KID_COATS if kid else COATS),
        "scarf": R.choice(SCARVES),
        "hat": R.choice(HATS),
    }
    model = VARIANTS[variant] + (".lite.glb" if lite_only else ".glb")
    d = dict(variant=variant, model=model, clip=clip, mug=bool(mug) or clip == "drink", colors=colors,
             phase=round(R.random() * 6, 2))
    if lite_only:
        d["lod"] = "lite"
    d.update(kw)
    return d


def pick_adult(sex=None, lite_safe=False, lite_head=False):
    """lite_safe: a figure whose lite file the lite market loads anyway (for lod 'lite' people);
    lite_head: anyone the lite market can draw (it aliases every round-4 figure, not the round-8 parka)."""
    if lite_head:
        pool = [v for v in (MEN if sex == "m" else WOMEN if sex == "f" else ADULTS) if v not in NOT_IN_LITE]
        return R.choice(pool)
    if lite_safe:
        pool = [v for v in LITE_SAFE_ADULTS if sex is None or v in (MEN if sex == "m" else WOMEN)]
        return R.choice(pool)
    return R.choice(MEN if sex == "m" else WOMEN if sex == "f" else ADULTS)


def chat_clip():
    return R.choice(["chat", "chat", "idle", "drink", "laugh", "chat", "idle"])


def vary_coats(members):
    """No two people in one group, queue or bench share a coat colour."""
    used = set()
    for m in members:
        pal = KID_COATS if m["variant"] in KIDS else COATS
        if m["colors"]["coat"] in used:
            free = [c for c in pal if c not in used] or pal
            m["colors"]["coat"] = R.choice(free)
        used.add(m["colors"]["coat"])
    return members


# ------------------------------------------------------------------ the planner
class Planner:
    def __init__(self):
        self.F = CF.Field()
        self.P = self.F.places
        self.standing = []          # (x, z, who)
        self.walk_segs = []         # ((x0, z0), (x1, z1), who)
        self.problems = []
        self.views = self._views()

    # ---- the stops' close views
    def _views(self):
        out = []
        for s in self.F.layout["stroll"]["stops"]:
            if s["id"] == "home":
                continue
            c = (s["eye"][0], s["eye"][2])
            t = (s["target"][0], s["target"][2])
            L = math.hypot(t[0] - c[0], t[1] - c[1]) or 1.0
            p = self.P.get(s["id"], {})
            corridor = p.get("kind") in ("section",) or s["id"] in ("bandstand", "deco-schmuck")
            out.append((c, ((t[0] - c[0]) / L, (t[1] - c[1]) / L), L, corridor, s["id"]))
        return out

    def in_view(self, pt):
        for c, u, L, corridor, sid in self.views:
            dx, dz = pt[0] - c[0], pt[1] - c[1]
            sa = dx * u[0] + dz * u[1]
            lat = abs(-dx * u[1] + dz * u[0])
            if VIEW_NEAR <= sa <= VIEW_FAR and lat < VIEW_HALF + VIEW_SLOPE * max(sa, 0.0):
                return sid
            if corridor and VIEW_FAR < sa < L and lat < VIEW_CORRIDOR:
                return sid
        return None

    # ---- rules for one standing person
    def why_not(self, pt, ignore_stall=False, ignore_furn=False, ignore_view=False, keep_leg=KEEP_LEG):
        db, ds, dl, de = self.F.at(*pt)
        if not ignore_stall and db < KEEP_STALL:
            return f"{db:.2f} m from {self.F.stall_at(pt[0], pt[1], 0.6) or 'a stall'}"
        if not ignore_furn and ds < KEEP_FURN:
            return f"{ds:.2f} m from furniture"
        if dl < keep_leg:
            return f"{dl:.2f} m from the stroll"
        if de < KEEP_EDGE:
            return "at the plaza edge"
        if not ignore_view:
            v = self.in_view(pt)
            if v:
                return f"in the {v} view"
        for x, z, who in self.standing:
            if math.hypot(pt[0] - x, pt[1] - z) < KEEP_PERSON:
                return f"on {who}"
        for a, b, who in self.walk_segs:
            if seg_dist(pt, a, b) < WALK_PERSON:
                return f"on {who}'s path"
        return None

    def take(self, pt, who):
        self.standing.append((pt[0], pt[1], who))

    def stall_pt(self, pid, local):
        p = self.P[pid]
        return add(tuple(p["pos"]), rot(local, p.get("rotY", 0.0)))

    def slot(self, pid, name, default):
        s = self.F.slots(pid).get(name)
        return s if s else default

    def front_z(self, pid):
        """three.js local z of the stall's counter front (its footprint's front edge)."""
        b = self.F.nodes.get(self.P[pid]["asset"], {}).get("bounds")
        return b["max"][2] if b else 1.76

    # ---- a group of n round a free centre near `want`
    def group(self, name, want, n, kids=0, clips=None, note=None, radius=GROUP_RADIUS, kind="group",
              lite_only=False, search=6.0, variants=None):
        for rr in [0.0] + [0.4 * k for k in range(1, int(search / 0.4) + 1)]:
            for k in range(16 if rr else 1):
                a = TAU * k / 16 + 0.3 * rr
                c = (want[0] + math.sin(a) * rr, want[1] + math.cos(a) * rr)
                spin = R.random() * TAU
                offs = []
                for i in range(n):
                    aa = spin + TAU * i / n + R.uniform(-0.2, 0.2)
                    r_ = radius * R.uniform(0.92, 1.1)
                    offs.append((math.sin(aa) * r_, math.cos(aa) * r_))
                pts = [add(c, o) for o in offs]
                if any(self.why_not(q) for q in pts):
                    continue
                if any(math.hypot(q[0] - x, q[1] - z) < 1.1 for q in pts for x, z, _ in self.standing):
                    continue        # a little air between groups
                members = []
                for i, o in enumerate(offs):
                    if variants:
                        v = variants[i]
                    elif i < kids:
                        v = R.choice(LITE_SAFE_KIDS if lite_only else KIDS)
                    else:
                        v = pick_adult(lite_safe=lite_only)
                    m = person(v, clips[i] if clips else chat_clip(), lite_only=lite_only)
                    m["pos"] = r2(o)
                    members.append(m)
                    self.take(pts[i], name)
                g = dict(id=name, kind=kind, pos=r2(c), members=vary_coats(members))
                if note:
                    g["note"] = note
                if rr > 2.5:
                    print(f"  {name}: moved {rr:.1f} m from {r2(want)} to {r2(c)}")
                return g
        self.problems.append(f"{name}: no free spot within {search} m of {r2(want)}")
        return None

    # ---- walkers: A* on a 0.2 m grid between waypoints, string-pulled
    def build_walk_grid(self):
        F = self.F
        s = 2
        db = F.d_big[::s, ::s]
        ds = F.d_small[::s, ::s]
        de = F.d_edge[::s, ::s]
        dloop = F.d_loop[::s, ::s]
        dleg = F.d_leg[::s, ::s]
        cost = np.where((db >= WALK_STALL) & (ds >= WALK_FURN) & (de >= 1.2), 1.0, np.inf)
        # keep off the loop's line, and a little off the signpost jumps, so the stroll camera rarely meets a walker
        cost = cost + np.where(dloop < 0.8, 6.0, np.where(dloop < 1.1, 1.5, 0.0)) + np.where(dleg < 0.8, 1.5, 0.0)
        # and stay a little off stall fronts, where customers stand
        cost = cost + np.where(db < 1.0, 0.8, 0.0)
        X = F.X[::s, ::s]
        Z = F.Z[::s, ::s]
        for x, z, _ in self.standing:
            cost[(X - x) ** 2 + (Z - z) ** 2 < WALK_PERSON ** 2] = np.inf
        for c, u, L, corridor, sid in self.views:          # walk round the panel views, not through them
            dx, dz = X - c[0], Z - c[1]
            sa = dx * u[0] + dz * u[1]
            lat = np.abs(-dx * u[1] + dz * u[0])
            m = (sa >= VIEW_NEAR) & (sa <= min(L, 5.0)) & (lat < VIEW_HALF + VIEW_SLOPE * np.maximum(sa, 0))
            cost = cost + np.where(m, 4.0, 0.0)
        self.wcost = cost
        self.ws = s * CF.RES

    def w_ij(self, x, z):
        n = self.wcost.shape[0]
        i = int((x + CF.EXT) / self.ws)
        j = int((z + CF.EXT) / self.ws)
        return min(max(i, 0), n - 1), min(max(j, 0), n - 1)

    def w_xz(self, i, j):
        return ((i + 0.5) * self.ws - CF.EXT, (j + 0.5) * self.ws - CF.EXT)

    def astar(self, a, b):
        cost = self.wcost
        n = cost.shape[0]
        si, sj = self.w_ij(*a)
        gi, gj = self.w_ij(*b)
        si, sj = self.free_cell(si, sj, a)
        gi, gj = self.free_cell(gi, gj, b)
        g = {(si, sj): 0.0}
        came = {}
        pq = [(0.0, 0.0, si, sj)]
        nb = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142),
              (-1, 1, 1.4142), (-1, -1, 1.4142)]
        while pq:
            f, gc, i, j = heapq.heappop(pq)
            if (i, j) == (gi, gj):
                break
            if gc > g.get((i, j), 1e18):
                continue
            for di, dj, d in nb:
                p, q = i + di, j + dj
                if 0 <= p < n and 0 <= q < n:
                    c = cost[p, q]
                    if c == np.inf:
                        continue
                    ng = gc + d * c
                    if ng < g.get((p, q), 1e18):
                        g[(p, q)] = ng
                        came[(p, q)] = (i, j)
                        heapq.heappush(pq, (ng + math.hypot(p - gi, q - gj), ng, p, q))
        if (gi, gj) not in came and (gi, gj) != (si, sj):
            raise RuntimeError(f"no walk from {r2(a)} to {r2(b)}")
        path = [(gi, gj)]
        while path[-1] != (si, sj):
            path.append(came[path[-1]])
        return [self.w_xz(i, j) for i, j in reversed(path)]

    def free_cell(self, i, j, xz):
        """The nearest plain-floor cell to a waypoint that landed on something (within 3 m)."""
        cost = self.wcost
        n = cost.shape[0]
        if cost[i, j] < 1.9:
            return i, j
        best = None
        R_ = int(3.0 / self.ws)
        for di in range(-R_, R_ + 1):
            for dj in range(-R_, R_ + 1):
                p, q = i + di, j + dj
                if 0 <= p < n and 0 <= q < n and cost[p, q] < 1.9:
                    d = di * di + dj * dj
                    if best is None or d < best[0]:
                        best = (d, p, q)
        if best is None:
            raise RuntimeError(f"walker waypoint {r2(xz)} is blocked")
        return best[1], best[2]

    def seg_ok(self, a, b):
        """A straight walk from a to b stays on cells as cheap as the plain floor (no stall, furniture, person,
        loop line or panel view)."""
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(2, int(L / (self.ws * 0.5)))
        for k in range(n + 1):
            t = k / n
            i, j = self.w_ij(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if self.wcost[i, j] > 1.9:
                return False
        return True

    def pull(self, pts):
        out = [pts[0]]
        i = 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and not self.seg_ok(pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            i = j
        return out

    def walk(self, wid, waypoints, v=None, speed=None, mug=None, start=None, lite_safe=False):
        pts = []
        for a, b in zip(waypoints[:-1], waypoints[1:]):
            seg = self.astar(a, b)
            pts += seg if not pts else seg[1:]
        pts = self.pull(pts)
        if v is None:
            v = R.choice(KIDS) if R.random() < 0.1 else pick_adult(lite_safe=lite_safe)
        sp = speed or round(R.uniform(0.75, 1.05) * (0.8 if v in KIDS else 1.0), 2)
        m = person(v, "walk", mug=mug)
        m.update(dict(id=wid, kind="walker", path=[r2(q) for q in pts], speed=sp,
                      start=round(R.random() if start is None else start, 2)))
        for a, b in zip(m["path"][:-1], m["path"][1:]):
            self.walk_segs.append((tuple(a), tuple(b), wid))
        return m

    def offset_ok(self, path):
        for a, b in zip(path[:-1], path[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            n = max(2, int(L / (self.ws * 0.5)))
            for k in range(n + 1):
                i, j = self.w_ij(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                if not np.isfinite(self.wcost[i, j]):
                    return False
        return True

    def pair(self, w, v, side=1, mug=None, gap=0.7, quiet=False):
        """A second person walking beside w (a couple, a parent and child): the same path offset sideways, on
        whichever side stays clear of stalls, furniture and people."""
        P = w["path"]
        out = None
        for sd, gp in ((side, gap), (-side, gap), (side, 0.55), (-side, 0.55)):
            cand = []
            for k, q in enumerate(P):
                a = P[max(0, k - 1)]
                b = P[min(len(P) - 1, k + 1)]
                L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
                nx, nz = -(b[1] - a[1]) / L * gp * sd, (b[0] - a[0]) / L * gp * sd
                cand.append(r2((q[0] + nx, q[1] + nz)))
            if self.offset_ok(cand):
                out = cand
                break
        if out is None:
            if not quiet:
                self.problems.append(f"{w['id']}: no room for a companion beside the path")
            return None
        m = person(v, "walk", mug=mug)
        m.update(dict(id=w["id"] + "_pair", kind="walker", path=out,
                      speed=round(min(w["speed"], 0.85 if v in KIDS else 1.0), 2), start=w["start"]))
        if v in KIDS or w["variant"] in KIDS:
            w["speed"] = m["speed"]
        for a, b in zip(out[:-1], out[1:]):
            self.walk_segs.append((tuple(a), tuple(b), m["id"]))
        return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=os.path.join(REPO, "review", "round-8", "organizer", "crowd_topdown.jpg"))
    a = ap.parse_args()
    PL = Planner()
    P = PL.P

    # ================================================================ vendors
    vend = []
    for sid, fig in VENDORS.items():
        sv = PL.slot(sid, "slot_vendor", [0, 0.13, 0])
        w = PL.stall_pt(sid, (sv[0], sv[2]))
        vend.append(dict(id=f"vendor_{sid}", kind="vendor", stall=sid, slot="slot_vendor",
                         pos=[round(w[0], 2), round(sv[1], 2), round(w[1], 2)], rotY=round(P[sid]["rotY"], 3),
                         variant=VARIANTS.index(fig), model=fig + ".glb", clip="serve", idle_clip="wipe",
                         mug=SERVE_MUG[sid], phase=round(R.random() * 6, 2)))
        PL.take(w, f"vendor_{sid}")
    for sid in ["deco-schmuck"] + DECO_ORDER:
        if sid not in P:
            continue
        fig, coat, scarf, hat, clip = DECO_LOOK[sid]
        sv = PL.slot(sid, "slot_vendor", [0, 0.13, 0.03])
        w = PL.stall_pt(sid, (sv[0], sv[2]))
        lite_only = sid != "deco-schmuck"      # the ornament shop is a stop with a close view; the rest is scenery
        e = dict(id=f"vendor_{sid}", kind="vendor", stall=sid, slot="slot_vendor",
                 pos=[round(w[0], 2), round(sv[1], 2), round(w[1], 2)], rotY=round(P[sid]["rotY"], 3),
                 variant=VARIANTS.index(fig), model=fig + (".lite.glb" if lite_only else ".glb"), clip=clip,
                 idle_clip="wipe" if clip == "serve" else "serve", mug=False,
                 colors={"coat": coat, "scarf": scarf, "hat": hat}, phase=round(R.random() * 6, 2))
        if lite_only:
            e["lod"] = "lite"
        vend.append(e)
        PL.take(w, e["id"])

    # ================================================================ queues at the Gluehwein and Bier stands
    # The queue starts at the counter's outer end and runs along the front and round the stall's corner.
    # side: -1 = the stall's local -x (away from the centre of the square).
    queues = []
    for sid, n, side in (("gluehwein", 4, -1), ("bierstand", 3, 1)):
        sc = PL.slot(sid, "slot_counter", [0, 1.05, 1.17])
        counter = PL.stall_pt(sid, (sc[0], sc[2]))
        members = []
        prev = None
        for i in range(n):
            # the preferred spot, then the nearest free one (round 8: the Bier stall's front props reach out to
            # local z 2.5 on its +x side, so its queue stands a little farther out)
            want = (side * (1.42 + 0.6 * i), 1.95 - 0.26 * max(0, i - 2))
            # the Bier stall's barrel tables fill its front right, so its second person waits beyond them
            gap = 1.9 if (sid == "bierstand" and i == 1) else 0.85
            spread = 16 if sid == "bierstand" else 6
            cands = sorted(((want[0] + dx * 0.1, want[1] + dz * 0.1) for dx in range(-spread, spread + 1)
                            for dz in range(-3, 13)),
                           key=lambda q: math.hypot(q[0] - want[0], q[1] - want[1]))
            w = None
            for lq in cands:
                wq = PL.stall_pt(sid, lq)
                if prev and not 0.5 < math.hypot(wq[0] - prev[0], wq[1] - prev[1]) < gap:
                    continue
                if not PL.why_not(wq):
                    w = wq
                    break
            if w is None:
                PL.problems.append(f"queue_{sid} #{i}: no free spot near local {r2(want)}")
                break
            prev = w
            m = person(pick_adult(lite_head=True) if i != 2 or sid != "gluehwein" else R.choice(KIDS),
                       "idle" if i else "drink", mug=(i == 0))
            m["pos"] = r2(sub(w, counter))
            members.append(m)
            PL.take(w, f"queue_{sid}")
            print(f"  queue_{sid} #{i}: local {r2(rot(sub(w, tuple(P[sid]['pos'])), -P[sid]['rotY']))}")
        queues.append(dict(id=f"queue_{sid}", kind="queue", stall=sid, pos=r2(counter), members=vary_coats(members),
                           note="members face the counter; the first is being served"))

    # ================================================================ customers at the deco counters
    # One or two people about 0.45 m in front of each counter, beside the crate at slot_front, facing the goods.
    # They are scenery like the stall: lite figures only (lod "lite").
    first_cust, second_cust = [], []
    two = {"deco-crepes", "deco-maroni"}
    for sid in DECO_ORDER:
        if sid not in P:
            continue
        zf = PL.front_z(sid)
        rotY = P[sid]["rotY"]
        spots = []
        for lx in ((-0.95, 0.9) if R.random() < 0.5 else (0.9, -0.95)):
            for dz in (0.42, 0.5, 0.6, 0.72, 0.85):
                w = PL.stall_pt(sid, (lx, zf + dz))
                if not PL.why_not(w):
                    spots.append((lx, zf + dz, w))
                    break
            else:
                PL.problems.append(f"{sid}: no customer spot at local x {lx}: "
                                   f"{PL.why_not(PL.stall_pt(sid, (lx, zf + 0.6)))}")
        for k, (lx, lz, w) in enumerate(spots[:2 if sid in two else 1]):
            kid = k == 1 and sid == "deco-maroni"
            v = R.choice(LITE_SAFE_KIDS) if kid else pick_adult(lite_safe=True)
            m = person(v, R.choice(["idle", "idle", "chat"]) if not kid else "idle_free", lite_only=True,
                       mug=None if not kid else False)
            m["rotY"] = round(face(w, PL.stall_pt(sid, (lx * 0.7, zf - 0.4))), 3)
            c = PL.stall_pt(sid, (0, zf + 1.4))
            m["pos"] = r2(sub(w, c))
            PL.take(w, f"browsing_{sid}")
            e = dict(id=f"browsing_{sid.replace('deco-', '')}" + ("_2" if k else ""), kind="browsing", stall=sid,
                     pos=r2(c), members=[m], note="at the counter, looking at the goods (scenery: lite figure)")
            (first_cust if k == 0 else second_cust).append(e)

    # the Buecherstand: two browsers in front of the cabinets, each facing his cabinet
    bc = PL.stall_pt("buecherstand", (0, BUECHER_BROWSE_Z))
    br = []
    for i, lx in enumerate((-1.5, 1.5)):
        w = PL.stall_pt("buecherstand", (lx, BUECHER_BROWSE_Z))
        why = PL.why_not(w, ignore_view=True)
        if why:
            PL.problems.append(f"browsing_buecherstand #{i}: {why}")
        m = person(pick_adult(lite_head=True), "idle", mug=False)
        m["pos"] = r2(sub(w, bc))
        m["rotY"] = round(face(w, PL.stall_pt("buecherstand", (lx * 0.95, 1.9))), 3)
        br.append(m)
        PL.take(w, "browsing_buecherstand")
    first_cust.append(dict(id="browsing_buecherstand", kind="browsing", stall="buecherstand", pos=r2(bc),
                           members=vary_coats(br), note="browsing the book cabinets"))

    # the ornament shop (a stop with its own close view): two customers at the ends of the counter
    sid = "deco-schmuck"
    zf = PL.front_z(sid)
    sc = PL.stall_pt(sid, (0, zf + 1.2))
    sm = []
    for lx in (-1.85, 1.9):
        for dz in (0.45, 0.6, 0.8):
            w = PL.stall_pt(sid, (lx, zf + dz))
            if not PL.why_not(w):
                break
        else:
            PL.problems.append(f"ornament shop customer at x {lx}: {PL.why_not(w)}")
        m = person(pick_adult("f" if lx < 0 else None), "idle" if lx < 0 else "chat", mug=lx > 0)
        m["pos"] = r2(sub(w, sc))
        m["rotY"] = round(face(w, PL.stall_pt(sid, (lx * 0.8, zf - 0.5))), 3)
        sm.append(m)
        PL.take(w, "browsing_schmuck")
    shop = dict(id="browsing_schmuck", kind="browsing", stall=sid, pos=r2(sc), members=vary_coats(sm),
                note="looking at the baubles on the rails")

    # ================================================================ fixed groups
    groups = []
    # listening to the band, facing the bandstand, in an arc clear of the band view and the legs
    bs = tuple(P["bandstand"]["pos"])
    listen = []
    for deg in list(range(-75, -20, 6)) + list(range(25, 80, 6)):
        if len(listen) >= 4:
            break
        a2 = math.radians(deg)
        q = (bs[0] + 4.85 * math.sin(a2), bs[1] + 4.85 * math.cos(a2))
        if PL.why_not(q) or any(math.hypot(q[0] - bs[0] - m_["pos"][0], q[1] - bs[1] - m_["pos"][1]) < 1.0
                                for m_ in listen):
            continue
        m = person(pick_adult(lite_head=True), R.choice(["idle", "idle", "drink", "chat"]))
        m["pos"] = r2(sub(q, bs))
        listen.append(m)
        PL.take(q, "listening_bandstand")
    if len(listen) < 4:
        PL.problems.append(f"listening_bandstand: only {len(listen)} spots")
    listening = dict(id="listening_bandstand", kind="group", pos=r2(bs), members=vary_coats(listen),
                     note="facing the band")

    # benches by the tree (architect: square.py, backs to the tree at -140 and -52 degrees, Blender)
    benches = []
    tb = (6.5, -15.0)
    tree_benches = []
    for bx, bz in PL.F.benches:
        if abs(math.hypot(bx - tb[0], bz - tb[1]) - 6.6) < 0.3:
            a_bl = math.atan2(-bz - 15.0, bx - 6.5)          # Blender angle round the tree
            tree_benches.append(((bx, bz), a_bl + math.pi / 2))
    tree_benches.sort(key=lambda b: b[0][0])
    for k, ((bx, bz), brot) in enumerate(tree_benches[:2]):
        fwd = rot((0, 1), brot)
        front = (bx + fwd[0] * 3.0, bz + fwd[1] * 3.0)
        mem = []
        seats = (-0.38, 0.36) if k == 0 else (0.3,)
        for i, lx in enumerate(seats):
            w = add((bx, bz), rot((lx, -0.02), brot))
            v = ([0, 1][i] if k == 0 else 4)
            m = person(v, "sit", mug=True)
            m["pos"] = r2(sub(w, front))
            m["rotY"] = round(brot, 3)
            mem.append(m)
            PL.take(w, "bench")
        benches.append(dict(id="bench_couple" if k == 0 else "bench_single", kind="bench", bench=[round(bx, 2), round(bz, 2)],
                            pos=r2(front), members=vary_coats(mem),
                            note=("a couple with mugs, seated with clip sit (seat 0.475 m); pos is a point ahead of the bench"
                                  if k == 0 else "an older man resting with a mug")))

    # the Riesenrad queue at the Kasse
    rr = P["riesenrad"]
    booth = PL.stall_pt("riesenrad", (3.6, 3.9))
    q = []
    for i in range(3):
        for dz in (0.0, 0.3, -0.3, 0.6):
            w = PL.stall_pt("riesenrad", (3.0 + 0.1 * i, 5.0 + 0.75 * i + dz))
            if not PL.why_not(w, ignore_view=True):
                break
        else:
            PL.problems.append(f"queue_riesenrad #{i}: {PL.why_not(w, ignore_view=True)}")
        m = person(pick_adult() if i != 1 else R.choice(KIDS), "idle")
        m["pos"] = r2(sub(w, booth))
        q.append(m)
        PL.take(w, "queue_riesenrad")
    riesen_q = dict(id="queue_riesenrad", kind="queue", stall="riesenrad", pos=r2(booth), members=vary_coats(q),
                    note="at the Kasse")

    # children at the carousel rail with a parent, on the side that faces the market
    cs = tuple(P["karussell"]["pos"])
    toward = math.atan2(10.0 - cs[0], -4.0 - cs[1])
    kids = []
    for da in [0, 0.12, -0.12, 0.24, -0.24, 0.36, -0.36, 0.48, -0.48, 0.6, -0.6, 0.72, -0.72, 0.84, -0.84, 0.96]:
        if len(kids) >= 3:
            break
        ang = toward + da
        for rad in (7.75, 7.95):
            pt = (cs[0] + math.sin(ang) * rad, cs[1] + math.cos(ang) * rad)
            if not PL.why_not(pt) and all(math.hypot(pt[0] - cs[0] - k_["pos"][0], pt[1] - cs[1] - k_["pos"][1]) > 0.6
                                          for k_ in kids):
                v = KIDS[len(kids) % 2]
                m = person(v, "idle_free", mug=False)
                m["pos"] = r2(sub(pt, cs))
                kids.append(m)
                PL.take(pt, "kids_karussell")
                break
    if kids:
        ka = math.atan2(sum(k_["pos"][0] for k_ in kids), sum(k_["pos"][1] for k_ in kids))
        for rad in (8.75, 9.1, 9.5):
            for da in (0.0, 0.1, -0.1, 0.2, -0.2):
                pt = (cs[0] + math.sin(ka + da) * rad, cs[1] + math.cos(ka + da) * rad)
                if not PL.why_not(pt):
                    m = person(pick_adult("f"), "chat")
                    m["pos"] = r2(sub(pt, cs))
                    kids.append(m)
                    PL.take(pt, "kids_karussell")
                    break
            else:
                continue
            break
    karussell = dict(id="kids_karussell", kind="group", pos=r2(cs), members=vary_coats(kids),
                     note="children at the carousel rail, watching the horses, with a mother behind them")

    # a family at the tree, looking up at it (two adults, two children)
    tr = tuple(P["tree"]["pos"])
    fam = PL.group("family_tree", (5.6, -9.9), 3, kids=1, clips=["idle_free", "chat", "idle"],
                   variants=[7, 0, 1], note="looking at the tree", search=4.0)
    if fam:
        # they all face the tree, not the middle of their group
        c = tuple(fam["pos"])
        for m in fam["members"]:
            w = add(c, tuple(m["pos"]))
            m["rotY"] = round(face(w, tr), 3)

    # ================================================================ free groups, most important first
    free = [
        # by the section stalls
        ("group_gluehwein", PL.stall_pt("gluehwein", (2.9, 2.4)), 3, 0),
        ("group_bratwurst", PL.stall_pt("bratwurst", (2.5, 3.0)), 2, 0),
        # the open square in front
        ("group_square_front", (-3.0, 7.2), 3, 0),
        # the left deco lane, between the lane and the Bratwurst / Riesenrad
        ("group_lane_left", (-14.2, -3.5), 2, 0),
        # the right deco lane, between the Bierstand and the carousel
        ("group_lane_right", (13.6, -5.0), 2, 0),
        # the back row, across the lane from the stalls
        ("group_back_row", (-2.0, -19.5), 3, 1),
        # the edges of the square, in the home view's foreground
        ("group_edge_left", (-15.5, 17.5), 2, 0),
        ("group_edge_right", (14.5, 18.5), 2, 0),
    ]
    free_groups = []
    for name, want, n, nk in free:
        g = PL.group(name, want, n, kids=nk)
        if g:
            free_groups.append(g)

    # ================================================================ walkers on every lane
    PL.build_walk_grid()
    W = []
    lanes = [
        # (id, waypoints) - the first six are the lite crowd's walkers, one per lane
        ("walker_front_edge", [(21.0, 19.5), (8.0, 22.5), (-8.0, 22.5), (-21.0, 18.5)]),
        ("walker_lane_left", [(-12.5, -12.0), (-15.6, -5.0), (-15.4, 3.0), (-14.0, 12.5)]),
        ("walker_lane_right", [(12.5, -8.0), (16.0, -2.0), (16.5, 2.0), (20.0, 15.0)]),
        ("walker_back_row", [(-13.0, -16.0), (-6.0, -17.6), (0.3, -17.6), (0.0, -12.5)]),
        ("walker_bandstand", [(-4.7, -1.5), (-5.2, -8.0), (0.0, -11.2), (5.0, -9.8)]),
        ("walker_middle", [(-1.5, 17.0), (-1.0, 12.5), (-0.8, 5.0)]),
        # more, for the full market
        ("walker_front_edge_2", [(-20.0, 16.0), (-6.0, 20.0), (8.0, 20.0), (21.0, 16.5)]),
        ("walker_lane_left_2", [(-13.0, 13.5), (-14.5, 5.0), (-14.6, -4.0), (-11.5, -10.5)]),
        ("walker_lane_right_2", [(19.5, 17.0), (15.5, 7.5), (15.0, -1.0), (11.5, -7.5)]),
        ("walker_back_row_2", [(-7.2, -26.0), (-6.8, -20.5), (-8.5, -13.5)]),     # out between Crepes and Maroni
        ("walker_back_row_3", [(9.0, -27.5), (3.0, -27.0), (-1.0, -24.5), (-14.0, -22.5)]),   # behind the back stalls
        ("walker_tree", [(-8.0, -9.0), (-3.5, -14.0), (0.0, -18.0)]),
        ("walker_karussell", [(9.5, -7.0), (13.0, -8.5), (14.5, -11.5)]),
    ]
    for k, (wid, wps) in enumerate(lanes):
        try:
            lite_head = k < 6
            v = pick_adult() if not lite_head else R.choice([x for x in ADULTS if x not in NOT_IN_LITE])
            W.append(PL.walk(wid, wps, v=v))
        except RuntimeError as e:
            PL.problems.append(f"{wid}: {e}")
    byid = {w["id"]: w for w in W}
    pairs = []
    # two couples with mugs, a father with his son and a mother with her daughter, each beside a walker whose
    # path has room for two (tried in this order)
    wanted = [("couple", 1, True), ("couple", 3, True), ("son", 6, False), ("daughter", 7, False)]
    for wid in ("walker_front_edge", "walker_lane_left_2", "walker_front_edge_2", "walker_back_row_2",
                "walker_lane_right_2", "walker_tree", "walker_middle", "walker_bandstand", "walker_karussell"):
        if not wanted or wid not in byid:
            continue
        what, v, mug = wanted[0]
        lead = byid[wid]
        if what == "couple" and lead["clip"] == "walk_free":
            lead.update(clip="walk", mug=True)
        pm = PL.pair(lead, v, side=1 if len(pairs) % 2 == 0 else -1, mug=mug, quiet=True)
        if pm:
            if what in ("son", "daughter"):
                pm["note"] = f"a {what} walking beside a parent"
            pairs.append(pm)
            wanted.pop(0)
    for what, v, mug in wanted:
        PL.problems.append(f"no walker path with room for a {what}")

    # ================================================================ assemble in lite order
    head_walkers = [w for w in W if w["id"] in [x[0] for x in lanes[:6]]]
    more_walkers = [w for w in W if w not in head_walkers] + pairs
    data = {
        "version": 1,
        "about": ("The market crowd (owner: organizer). Coordinates are three.js: pos [x, z] in metres, rotY in radians "
                  "(0 = facing +Z). Group, queue, browsing and bench members give pos relative to the entry's pos and "
                  "face it unless they carry rotY. Each person names a figure (model = file; variant = index into "
                  "variants), the clip to play, whether the Gluehwein mug shows (it always matches the clip: clips "
                  "ending in _free, play, rest and wipe hide it, and so does serve for every vendor who sells no "
                  "drinks), recolours for the coat / scarf / hat materials, and a phase (s) to offset the clip. groups "
                  "hold 2 to 5 people; single browsers are under browsing, sitters under benches. People marked "
                  "lod 'lite' stand at the deco stalls, which are scenery (ADR 0004, Mac: no need to fully render the "
                  "side stalls): their model is the lite file itself, so the full market never loads or draws a full "
                  "figure there. Nobody stands within 1.0 m of a stroll leg, inside a stall or prop, or in the near "
                  "part of a stop's view. The lite market keeps the first 40 people in file order. Generated by "
                  "blender/people/crowd_plan.py from site/src/layout.json and the placed glbs; re-run after layout "
                  "changes."),
        "clips": {
            "full": CLIPS_FULL,
            "lite": CLIPS_LITE,
            "notes": {
                "walk": "in place, one 1.2 s cycle, about 1.0 m/s for adults (0.8 m/s for children)",
                "sit": "origin on the ground under the hips; seat top at 0.475 m (the square's benches); feet forward (+Z)",
                "mug": "the mug is the node 'mug', skinned to the bone 'mug'; clips without it scale that bone to 0",
                "lite": "lite files carry only what a lite figure plays (the lite market, far people in the full "
                        "market and the lod 'lite' people at the deco stalls). Missing crowd clips fall back as "
                        "site/src/crowd.js does: idle_free, chat_free and laugh play idle, walk_free plays walk, and "
                        "the mug mesh stays hidden for *_free clips",
                "fallback": LITE_FALLBACK,
            },
        },
        "variants": [],
        "lite": {"cap": LITE_CAP, "order": ("people are listed most important first; the lite market keeps the first 40: "
                                            "13 vendors, a walker on six lanes, the Gluehwein and Bier queues, one "
                                            "customer per deco counter, the Buecherstand browsers and the band's listeners")},
        "shared_anims": {
            "file": "people_anims.glb",
            "clips": ["idle", "walk", "chat", "drink", "laugh", "sit", "idle_free", "walk_free", "chat_free",
                      "laugh_free", "sit_free", "serve", "wipe"],
            "reference": "people_man_coat",
            "note": ("every crowd and vendor clip on one skeleton with no mesh (bone names are the same in every "
                     "figure). Optional: an engine that plays these on any figure can ship figures without clips. "
                     "hips.position keys are absolute for the reference; add (figure hips_rest - reference hips_rest) "
                     "to them, with hips_rest from blender/out/people/report.json or the figure's own hips node."),
        },
        "vendors": vend,
        "walkers": head_walkers,
        "queues": queues,
        "browsing": first_cust,
        "groups": [listening] + second_cust + [shop, riesen_q, karussell] + ([fam] if fam else []) + free_groups,
        "benches": benches,
        "walkers_more": more_walkers,
    }
    data["musicians"] = [
        dict(id=f"band_{k}", kind="musician", slot=f"slot_{k}", model=f"people_band_{k}.glb", instrument=f"instr_{k}.glb",
             clip="play", rest_clip="rest", seated=k in ("piano", "drums"),
             note="origin = the instrument's origin (the player's floor spot); use the slot's world transform")
        for k in ("sax", "piano", "bass", "drums")]

    # ---------------- variants: every figure file the crowd names (and no other, so the full market loads
    # nothing it does not draw); each person's variant indexes this list
    order = []
    for key in ("vendors", "walkers", "queues", "browsing", "groups", "benches", "walkers_more"):
        for e in data[key]:
            order += e["members"] if "members" in e else [e]
    files = []
    for m in order:
        if m["model"] not in files:
            files.append(m["model"])
    for m in order:
        m["variant"] = files.index(m["model"])
    data["variants"] = files

    check(PL, data, order)
    data["count"] = {"people": len(order), "musicians": 4, "lite": LITE_CAP}
    json.dump(data, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(order)} people + 4 musicians")
    for p in PL.problems:
        print("  PROBLEM", p)
    if a.map:
        draw_map(PL, data, a.map)
    return 1 if PL.problems else 0


# ------------------------------------------------------------------ checks
def check(PL, data, order):
    F = PL.F
    pr = PL.problems
    standing = []
    for key in ("vendors", "queues", "browsing", "groups", "benches"):
        for e in data[key]:
            if "members" in e:
                for k, m in enumerate(e["members"]):
                    standing.append((add(tuple(e["pos"]), tuple(m["pos"])), f"{e['id']}#{k}", e))
            else:
                standing.append(((e["pos"][0], e["pos"][2]), e["id"], e))
    for pt, who, e in standing:
        db, ds, dl, de = F.at(*pt)
        if dl < KEEP_LEG - 0.02:
            pr.append(f"{who} at {r2(pt)} is {dl:.2f} m from a stroll leg")
        if e.get("kind") == "vendor":
            continue
        if db < KEEP_STALL - 0.05:
            pr.append(f"{who} at {r2(pt)} is {db:.2f} m from {F.stall_at(pt[0], pt[1], 0.6)}")
        if ds < KEEP_FURN - 0.05 and e.get("kind") != "bench":
            pr.append(f"{who} at {r2(pt)} is {ds:.2f} m from furniture")
        if F.stall_at(pt[0], pt[1]):
            pr.append(f"{who} at {r2(pt)} stands inside {F.stall_at(pt[0], pt[1])}")
    for i, (p, a, _) in enumerate(standing):
        for q, b, _ in standing[i + 1:]:
            if math.hypot(p[0] - q[0], p[1] - q[1]) < 0.42:
                pr.append(f"{a} and {b} overlap at {r2(p)}")
    for e in data["groups"]:
        if e["kind"] == "group" and not 2 <= len(e["members"]) <= 5:
            pr.append(f"{e['id']} has {len(e['members'])} people (groups hold 2 to 5)")
    walkers = data["walkers"] + data["walkers_more"]
    PL.walker_report = []
    for w in walkers:
        pts = w["path"]
        near_loop = 0.0
        total = 0.0
        for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
            L = math.hypot(x1 - x0, z1 - z0)
            n = max(1, int(L / 0.1))
            for t in [i / n for i in range(n + 1)]:
                x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
                db, ds, dl, de = F.at(x, z)
                if db < 0.3:
                    pr.append(f"{w['id']} walks through {F.stall_at(x, z, 0.4)} at {r2((x, z))}")
                    break
                for p, who, _ in standing:
                    if math.hypot(x - p[0], z - p[1]) < 0.5:
                        pr.append(f"{w['id']} walks through {who} at {r2((x, z))}")
                        break
            for t in [i / 10 for i in range(10)]:
                x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
                if F.sample(F.d_loop, x, z) < 0.8:
                    near_loop += L / 10
            total += L
        PL.walker_report.append((w["id"], round(total, 1), round(near_loop, 1)))
    # clips: the mug flag must match the clip, every clip must exist in the figure file, and the people the
    # lite market keeps (the first LITE_CAP) must not need a clip the lite files lack
    for i, m in enumerate(order):
        role = "vendor" if "vendor" in m["model"] else "band" if "band" in m["model"] else "crowd"
        mug_clip = not (m["clip"].endswith("_free") or m["clip"] in ("play", "rest", "wipe"))
        if role == "vendor" and m["clip"] == "serve":
            mug_clip = SERVE_MUG.get(m["stall"], False)
        if m["mug"] != mug_clip:
            pr.append(f"{m.get('id', m['model'])}: mug {m['mug']} does not match clip {m['clip']}")
        lite_file = m["model"].endswith(".lite.glb")
        have = CLIPS_LITE[role] if lite_file else CLIPS_FULL[role]
        if m["clip"] not in have and not (lite_file and m["clip"] in LITE_FALLBACK):
            pr.append(f"{m['model']}: clip {m['clip']} is not in the figure file")
        if m["clip"] not in CLIPS_LITE[role] and m["clip"] not in LITE_FALLBACK:
            pr.append(f"person {i} ({m['model']}) needs {m['clip']}, which the lite file (far level) lacks")
        if not os.path.exists(os.path.join(CF.MODELS, m["model"])):
            pr.append(f"person {i}: {m['model']} does not exist")
        if i < LITE_CAP and VARIANTS.index(m["model"].replace(".lite.glb", "").replace(".glb", "")) in NOT_IN_LITE:
            pr.append(f"person {i} ({m['model']}) is in the lite crowd but not in the engine's lite alias table")


# ------------------------------------------------------------------ top-down map
def draw_map(PL, data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    F = PL.F
    N = CF.N
    img = np.zeros((N, N, 3))
    img[:] = (0.13, 0.14, 0.17)
    img[F.d_edge < 0] = (0.07, 0.07, 0.08)
    near = F.d_leg < KEEP_LEG
    img[near] = (0.22, 0.17, 0.17)
    img[F.big] = (0.55, 0.42, 0.3)
    img[F.small] = (0.35, 0.38, 0.6)
    fig, ax = plt.subplots(figsize=(14.2, 12.8), dpi=90)
    ax.imshow(np.transpose(img, (1, 0, 2)), extent=(-CF.EXT, CF.EXT, CF.EXT, -CF.EXT), interpolation="nearest")
    for f_, t_, loop, d in F.leg_pts:
        ax.plot(d[:, 0], d[:, 2], color=(0.95, 0.35, 0.25) if loop else (0.45, 0.6, 0.45),
                lw=1.6 if loop else 0.6, alpha=0.95 if loop else 0.5, zorder=2)
    for c, u, L, corridor, sid in PL.views:
        prof = [(VIEW_NEAR, VIEW_HALF), (VIEW_FAR, VIEW_HALF + VIEW_SLOPE * VIEW_FAR)]
        if corridor:
            prof += [(VIEW_FAR, VIEW_CORRIDOR), (L, VIEW_CORRIDOR)]
        pts = [(c[0] + u[0] * sa - u[1] * h, c[1] + u[1] * sa + u[0] * h) for sa, h in prof]
        pts += [(c[0] + u[0] * sa + u[1] * h, c[1] + u[1] * sa - u[0] * h) for sa, h in reversed(prof)]
        xs, zs = zip(*(pts + pts[:1]))
        ax.plot(xs, zs, color=(0.6, 0.6, 0.75), lw=0.7, ls=":", zorder=2)
    for w in data["walkers"] + data["walkers_more"]:
        xs, zs = zip(*w["path"])
        ax.plot(xs, zs, color=(0.4, 0.65, 0.95), lw=1.1, ls="--", zorder=3)
        ax.plot(xs[0], zs[0], "o", ms=3.5, color=(0.5, 0.75, 1.0), zorder=3)
    col = {"queue": (0.95, 0.8, 0.3), "group": (0.92, 0.5, 0.36), "bench": (0.8, 0.5, 0.9),
           "browsing": (1.0, 0.62, 0.2)}
    for key in ("queues", "browsing", "groups", "benches"):
        for g in data[key]:
            for m in g["members"]:
                x, z = add(tuple(g["pos"]), tuple(m["pos"]))
                c = (0.45, 0.9, 0.55) if "child" in m["model"] else col.get(g["kind"], (0.92, 0.5, 0.36))
                ax.add_patch(Circle((x, z), 0.27, color=c, zorder=4))
                if m.get("lod") == "lite":
                    ax.add_patch(Circle((x, z), 0.42, fill=False, ec=(1, 1, 1), lw=0.6, zorder=4))
    for v in data["vendors"]:
        x, z = v["pos"][0], v["pos"][2]
        ax.add_patch(plt.Rectangle((x - 0.28, z - 0.28), 0.56, 0.56, color=(0.97, 0.97, 0.97), zorder=4))
    for pid, p in F.places.items():
        if p["kind"] in ("section", "deco", "landmark") or pid == "tree":
            ax.text(p["pos"][0], p["pos"][1], p.get("label", pid), color="w", fontsize=6.5, ha="center",
                    va="center", zorder=5)
    for s in F.layout["stroll"]["stops"]:
        if s["id"] != "home":
            ax.plot(s["eye"][0], s["eye"][2], "*", ms=9, color=(1, 0.85, 0.3), zorder=5)
    n_people = data["count"]["people"]
    ax.set_title(f"crowd.json round 8, top view (three.js x right, z down): {n_people} people + 4 musicians. "
                 "White squares vendors, orange groups, gold browsing / queues, green children, violet benches,\n"
                 "white ring = lite figure (deco stall scenery). Blue dashes walkers. Red: the stroll loop, green: "
                 "signpost legs, dark red band: 1.0 m kept clear of every leg. Dotted: stop views kept clear. "
                 "Stars: stops.", fontsize=8)
    ax.set_xlim(-31, 31)
    ax.set_ylim(27, -30)
    ax.tick_params(labelsize=7)
    ax.set_aspect("equal")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pil_kwargs={"quality": 88})
    print("map ->", path)


if __name__ == "__main__":
    sys.exit(main())
