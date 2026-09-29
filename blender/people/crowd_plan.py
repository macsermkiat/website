"""Generate site/src/crowd.json: who stands where, who walks which path, which clip each plays.

    python3 blender/people/crowd_plan.py [--map review/round-1/organizer/crowd_map.jpg]

Coordinates are three.js: pos [x, z] in metres on the ground, rotY in radians (0 = facing +Z).
Positions come from site/src/layout.json (architect) plus the stall glbs' slot_vendor / slot_front
empties, so the crowd follows the layout when it changes: re-run this script.
"""
import argparse
import json
import math
import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LAYOUT = os.path.join(REPO, "site", "src", "layout.json")
MODELS = os.path.join(REPO, "site", "public", "models")
OUT = os.path.join(REPO, "site", "src", "crowd.json")

R = random.Random(1225)

BASE = ["people_man_coat", "people_woman_coat", "people_man_parka", "people_woman_older", "people_man_older",
        "people_woman_young", "people_child_boy", "people_child_girl"]
VENDORS = {"gluehwein": "people_vendor_gluehwein", "bierstand": "people_vendor_bier",
           "bratwurst": "people_vendor_wurst", "buecherstand": "people_vendor_buecher"}
VARIANTS = BASE + [VENDORS[k] for k in ("gluehwein", "bierstand", "bratwurst", "buecherstand")]
ADULTS = [0, 1, 2, 3, 4, 5]
KIDS = [6, 7]
MEN, WOMEN = [0, 2, 4], [1, 3, 5]

COATS = ["#3a3d44", "#27344a", "#5b5750", "#2f4a3a", "#6a2e3a", "#8a6a4a", "#1f2226", "#4a3b32", "#5c1f2e",
         "#2e5e6e", "#6b6f78", "#a8814f", "#3b4452", "#56402e"]
SCARVES = ["#9e2a2b", "#c8962c", "#e8dcc6", "#2e6f73", "#7b2b2b", "#d9667a", "#2f5f9e", "#6d8b3a", "#b0403a",
           "#d9d2c4", "#5a3d6e", "#c45a2a"]
HATS = ["#6b6158", "#7a2436", "#3d5a3e", "#6a2e4f", "#3b2f27", "#8f8a86", "#e0a33a", "#f0e6d6", "#1f2a44",
        "#a3242c", "#2a2a2e", "#4b6a8a"]
KID_COATS = ["#b23a2e", "#2f5f9e", "#2e5e6e", "#e0a33a", "#6d8b3a", "#8a2f5a"]


# ------------------------------------------------------------------ geometry helpers
def rot(v, a):
    """three.js rotation about +Y: local (x, z) -> world offset."""
    x, z = v
    return (x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a))


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def r2(v):
    return [round(v[0], 2), round(v[1], 2)]


def face(frm, to):
    """rotY that turns a figure at frm to face the point to."""
    return math.atan2(to[0] - frm[0], to[1] - frm[1])


def glb_nodes(path):
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    return {nd["name"]: nd.get("translation", [0, 0, 0]) for nd in j["nodes"] if "name" in nd}


def load_places():
    L = json.load(open(LAYOUT))
    P = {}
    for p in L["places"]:
        P[p["id"]] = dict(pos=tuple(p["pos"]), rot=p.get("rotY", 0.0), asset=p.get("asset"), kind=p["kind"])
    return P


# ------------------------------------------------------------------ obstacles (for clearance checks)
def obstacles(P):
    obs = []   # ("rect", centre, rot, half_x, half_z) or ("circle", centre, r)
    for k, p in P.items():
        if p["kind"] == "section":
            obs.append(("rect", add(p["pos"], rot((0, 0.2), p["rot"])), p["rot"], 1.95, 1.4, k))
        elif p["kind"] == "deco":
            obs.append(("rect", p["pos"], p["rot"], 1.6, 1.3, k))
    obs.append(("circle", P["bandstand"]["pos"], 4.05, "bandstand"))
    bs = P["bandstand"]["pos"]
    obs.append(("rect", (bs[0], bs[1] + 4.3), 0.0, 1.3, 0.9, "bandstand steps"))
    obs.append(("circle", P["tree"]["pos"], 3.0, "tree"))
    obs.append(("circle", P["karussell"]["pos"], 7.4, "karussell"))
    obs.append(("rect", P["riesenrad"]["pos"], P["riesenrad"]["rot"], 5.2, 3.6, "riesenrad"))
    poles = [[-15, 4], [-7.5, 6.5], [0, 7.5], [7.5, 6.5], [15, 4], [-10.5, -6.5], [10.5, -6.5], [-3.5, -9.5],
             [3.5, -9.5], [-17.5, -3], [-17.5, 5], [-17.5, 13], [17.5, -3], [17.5, 5], [17.5, 13], [-7, -18],
             [1, -18], [10, -18]]
    for q in poles:
        obs.append(("circle", tuple(q), 0.45, "pole"))
    for b in BENCHES:
        obs.append(("rect", b[0], b[1], 1.0, 0.35, "bench"))
    return obs


# benches by the tree (architect's square.py: Blender (x, y, rot) -> three [x, -y], rotY = rot)
BENCHES = [((6.5 - 4.2, -(15 - 2.6)), math.radians(-30)), ((6.5 + 4.4, -(15 - 2.4)), math.radians(28))]


def clearance(pt, obs, ignore=()):
    best = (1e9, None)
    for o in obs:
        if o[-1] in ignore:
            continue
        if o[0] == "circle":
            d = math.hypot(pt[0] - o[1][0], pt[1] - o[1][1]) - o[2]
        else:
            _, c, a, hx, hz, _n = o
            lx, lz = rot((pt[0] - c[0], pt[1] - c[1]), -a)
            dx, dz = abs(lx) - hx, abs(lz) - hz
            d = math.hypot(max(dx, 0), max(dz, 0)) + min(max(dx, dz), 0)
        if d < best[0]:
            best = (d, o[-1])
    return best


# ------------------------------------------------------------------ people
def person(variant, clip="chat", mug=None, **kw):
    kid = variant in KIDS
    if mug is None:
        mug = (not kid and R.random() < 0.72) or (kid and R.random() < 0.25)
    if not mug and clip in ("idle", "chat", "laugh", "sit", "walk"):
        clip = clip + "_free"
    colors = {
        "coat": R.choice(KID_COATS if kid else COATS),
        "scarf": R.choice(SCARVES),
        "hat": R.choice(HATS),
    }
    d = dict(variant=variant, model=VARIANTS[variant] + ".glb", clip=clip, mug=bool(mug) or clip == "drink",
             colors=colors, phase=round(R.random() * 6, 2))
    d.update(kw)
    return d


def pick_adult(sex=None):
    return R.choice(MEN if sex == "m" else WOMEN if sex == "f" else ADULTS)


def chat_clip():
    return R.choice(["chat", "chat", "idle", "drink", "laugh", "chat", "idle"])


def group(name, centre, n, radius=0.62, kids=0, spin=0.0, clips=None, note=None):
    members = []
    for i in range(n):
        a = spin + TAU * i / n + R.uniform(-0.25, 0.25)
        rr = radius * R.uniform(0.9, 1.12)
        off = (math.sin(a) * rr, math.cos(a) * rr)
        v = R.choice(KIDS) if i < kids else pick_adult()
        clip = clips[i] if clips else chat_clip()
        m = person(v, clip)
        m["pos"] = r2(off)
        members.append(m)
    g = dict(id=name, kind="group", pos=r2(centre), members=members)
    if note:
        g["note"] = note
    return g


TAU = 2 * math.pi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=os.path.join(REPO, "review", "round-1", "organizer", "crowd_map.jpg"))
    a = ap.parse_args()
    P = load_places()
    obs = obstacles(P)
    slots = {}
    for sid, p in P.items():
        if p["kind"] == "section":
            f = os.path.join(MODELS, p["asset"])
            if os.path.exists(f):
                n = glb_nodes(f)
                slots[sid] = {k: v for k, v in n.items() if k.startswith("slot_")}

    def stall_pt(sid, local):
        p = P[sid]
        return add(p["pos"], rot(local, p["rot"]))

    def slot(sid, name, fallback):
        s = slots.get(sid, {}).get(name)
        return (s[0], s[2]) if s else fallback

    data = {
        "version": 1,
        "about": ("The market crowd (owner: organizer). Coordinates are three.js: pos [x, z] in metres, rotY in radians "
                  "(0 = facing +Z). Group and queue members give pos relative to the group's pos and face it. "
                  "Each person names a figure (variant = index into variants, model = file), the clip to play, whether "
                  "the Gluehwein mug shows (clips ending in _free hide it by scaling the mug bone, so mug always matches "
                  "the clip), recolours for the coat / scarf / hat materials, and a phase (s) to offset the clip. "
                  "Generated by blender/people/crowd_plan.py from site/src/layout.json; re-run after layout changes."),
        "clips": {
            "crowd": ["idle", "walk", "chat", "drink", "laugh", "sit", "idle_free", "walk_free", "chat_free",
                      "laugh_free", "sit_free"],
            "band": ["play", "rest"],
            "vendor": ["serve", "wipe"],
            "notes": {
                "walk": "in place, 1.2 s per cycle, about 1.0 m/s for adults (0.8 m/s for children)",
                "sit": "origin on the ground under the hips; seat top at 0.475 m (the square's benches); feet forward (+Z)",
                "mug": "the mug is the node 'mug', skinned to the bone 'mug'; *_free, play, rest and wipe scale it to 0",
            },
        },
        "variants": [v + ".glb" for v in VARIANTS],
        "lite": {"cap": 40, "order": "entries are listed most important first; the lite market keeps the first 40"},
    }

    # ---------------- vendors at slot_vendor, facing out of the stall
    vend = []
    for sid, fig in VENDORS.items():
        sv = slots.get(sid, {}).get("slot_vendor", [0, 0.13, 0])
        w = stall_pt(sid, (sv[0], sv[2]))
        vend.append(dict(id=f"vendor_{sid}", kind="vendor", stall=sid, slot="slot_vendor",
                         pos=[round(w[0], 2), round(sv[1], 2), round(w[1], 2)], rotY=round(P[sid]["rot"], 3),
                         variant=VARIANTS.index(fig), model=fig + ".glb", clip="serve", idle_clip="wipe", mug=True,
                         phase=round(R.random() * 6, 2)))
    data["vendors"] = vend

    # ---------------- queues at the Gluehwein and Bier stands, facing the counter
    queues = []
    for sid, n in (("gluehwein", 5), ("bierstand", 4)):
        counter = stall_pt(sid, (0.0, slot(sid, "slot_counter", (0, 1.17))[1] if False else 1.2))
        sc = slots.get(sid, {}).get("slot_counter", [0, 1.05, 1.17])
        sf = slots.get(sid, {}).get("slot_front", [0, 0, 2.37])
        counter = stall_pt(sid, (sc[0], sc[2]))
        members = []
        for i in range(n):
            lz = sf[2] - 0.62 + 0.78 * i
            lx = (0.18 if i % 2 else -0.1) + R.uniform(-0.08, 0.08)
            w = stall_pt(sid, (lx, lz))
            m = person(pick_adult() if i != 3 or sid != "gluehwein" else R.choice(KIDS),
                       "idle" if i else "drink", mug=(i == 0))
            m["pos"] = r2((w[0] - counter[0], w[1] - counter[1]))
            members.append(m)
        queues.append(dict(id=f"queue_{sid}", kind="queue", stall=sid, pos=r2(counter), members=members,
                           note="members face the counter; the first is being served"))
    data["queues"] = queues

    # ---------------- walkers: lanes, the front of the square, round the bandstand and to the tree
    paths = [
        [(-15.0, 9.8), (-7.0, 10.6), (0.0, 11.2), (7.0, 10.6), (15.0, 9.6)],    # across the front
        [(-12.5, 6.2), (-4.0, 4.6), (3.5, 4.4), (12.0, 5.9)],                   # in front of the section stalls
        [(-18.2, 14.0), (-18.25, 6.0), (-18.15, -2.0), (-18.3, -8.5)],          # left lane
        [(18.3, 14.2), (18.0, 9.8), (18.3, 5.8), (18.2, -1.5), (18.3, -3.2)],   # right lane
        [(-3.6, 1.2), (-4.7, -2.5), (-4.9, -6.2), (-4.9, -9.3), (-2.6, -11.6), (0.0, -11.7), (4.3, -10.8)],  # round the bandstand
        [(3.6, 1.2), (4.7, -2.5), (4.9, -6.2), (8.2, -8.4), (11.0, -9.6)],       # east side toward the carousel
        [(-13.5, -10.5), (-7.0, -12.8), (-1.0, -15.0), (1.6, -17.0)],            # toward the tree
        [(-14.0, -18.6), (-4.0, -19.1), (4.5, -19.0), (13.5, -18.9)],            # the back row
        [(-11.5, 12.0), (-16.2, 6.0), (-16.3, -3.5)],                            # behind the Bratwurst stand
        [(11.5, 12.0), (16.2, 6.0), (16.3, -3.5)],                               # behind the Buecherstand
        [(-2.0, 16.0), (-1.2, 8.8), (-0.9, 4.3)],                                # up the middle to the bandstand
        [(9.0, 15.5), (5.0, 9.0), (2.8, 3.2)],
    ]
    walkers = []
    k = 0
    for pi, path in enumerate(paths):
        for j in range(2 if pi < 6 else 1):
            v = R.choice(KIDS) if R.random() < 0.12 else pick_adult()
            sp = round(R.uniform(0.75, 1.05) * (0.8 if v in KIDS else 1.0), 2)
            m = person(v, "walk")
            pts = path if j == 0 else list(reversed(path))
            jit = R.uniform(-0.1, 0.1) if pi in (2, 3) else R.uniform(-0.18, 0.18)
            pts = [(x + jit, z + jit * 0.6) for x, z in pts]
            m.update(dict(id=f"walker_{k}", kind="walker", path=[r2(q) for q in pts], speed=sp,
                          start=round(R.random(), 2)))
            walkers.append(m)
            k += 1
    # pairs walking together: a second person 0.7 m beside some walkers
    pairs = []
    for w in [walkers[i] for i in (0, 1, 2, 3, 12)]:
        (x0, z0), (x1, z1) = w["path"][0], w["path"][1]
        L = math.hypot(x1 - x0, z1 - z0) or 1
        nx, nz = -(z1 - z0) / L * 0.7, (x1 - x0) / L * 0.7
        m = person(pick_adult(), "walk")
        m.update(dict(id=w["id"] + "_pair", kind="walker", path=[r2((x + nx, z + nz)) for x, z in w["path"]],
                      speed=w["speed"], start=w["start"]))
        pairs.append(m)
    data["walkers"] = walkers[:8] + pairs[:2]

    # ---------------- groups chatting near the stalls, the bandstand and the tree
    groups = []
    for sid, local, n in (("gluehwein", (2.9, 2.2), 3), ("gluehwein", (-2.8, 2.6), 2), ("bierstand", (-2.9, 2.3), 3),
                          ("bierstand", (2.8, 2.9), 2), ("bratwurst", (2.4, 3.0), 3), ("bratwurst", (-2.5, 2.8), 2),
                          ("buecherstand", (-2.4, 2.9), 2), ("buecherstand", (2.6, 2.6), 2)):
        c = stall_pt(sid, local)
        groups.append(("FREE", f"group_{sid}_{len(groups)}", c, n))
    # browsing at the Buecherstand counter
    bc = stall_pt("buecherstand", (0, 1.2))
    br = []
    for i, lx in enumerate((-0.55, 0.45)):
        w = stall_pt("buecherstand", (lx, 2.15))
        m = person(pick_adult(), "idle", mug=False)
        m["pos"] = r2((w[0] - bc[0], w[1] - bc[1]))
        br.append(m)
    groups.append(dict(id="browsing_buecherstand", kind="group", pos=r2(bc), members=br,
                       note="browsing the books, facing the counter"))
    # the open square in front: the busiest part of the home view
    for c, n in (((-3.3, 6.7), 3), ((4.4, 6.3), 3), ((-9.6, 8.2), 2), ((9.6, 8.6), 3), ((0.4, 9.6), 2),
                 ((-1.8, 14.2), 3), ((5.2, 16.4), 2)):
        groups.append(("FREE", f"group_square_{len(groups)}", c, n))
    # listening to the band, facing the bandstand
    bs = P["bandstand"]["pos"]
    listen = []
    for i, (x, z) in enumerate(((-2.3, 1.9), (-1.6, 2.2), (2.2, 2.0), (2.9, 1.6), (0.5, 3.0))):
        m = person(pick_adult(), R.choice(["idle", "idle", "drink", "chat"]))
        m["pos"] = r2((x - bs[0], z - bs[1]))
        listen.append(m)
    groups.append(dict(id="listening_bandstand", kind="group", pos=r2(bs), members=listen,
                       note="facing the band"))
    # a family at the tree, looking up at it
    tr = P["tree"]["pos"]
    fam = []
    for i, (v, (x, z)) in enumerate(((0, (5.6, -10.9)), (1, (6.4, -10.8)), (7, (5.95, -11.3)), (6, (7.1, -11.2)))):
        m = person(v, "idle_free" if v in KIDS else R.choice(["idle", "chat"]), mug=v not in KIDS and R.random() < 0.5)
        m["pos"] = r2((x - tr[0], z - tr[1]))
        fam.append(m)
    groups.append(dict(id="family_tree", kind="group", pos=r2(tr), members=fam, note="looking at the tree"))
    for c, n in (((1.6, -10.0), 3),):
        groups.append(("FREE", f"group_tree_{len(groups)}", c, n))
    # a couple on the bench by the tree (sitting, facing out of the bench's front)
    (bx, bz), brot = BENCHES[0]
    fwd = rot((0, 1), brot)
    front = (bx + fwd[0] * 3.0, bz + fwd[1] * 3.0)
    couple = []
    for i, lx in enumerate((-0.38, 0.36)):
        w = add((bx, bz), rot((lx, -0.02), brot))
        m = person([0, 1][i], "sit", mug=True)
        m["pos"] = r2((w[0] - front[0], w[1] - front[1]))
        m["rotY"] = round(brot, 3)
        couple.append(m)
    groups.append(dict(id="bench_couple", kind="bench", bench=[round(bx, 2), round(bz, 2)], pos=r2(front),
                       members=couple, note="seated with clip sit (seat 0.475 m); pos is a point ahead of the bench so "
                                        "an engine that faces members to pos keeps them facing out"))
    (bx, bz), brot = BENCHES[1]
    fwd = rot((0, 1), brot)
    front = (bx + fwd[0] * 3.0, bz + fwd[1] * 3.0)
    w = add((bx, bz), rot((0.3, -0.02), brot))
    m = person(4, "sit", mug=False)
    m["pos"] = r2((w[0] - front[0], w[1] - front[1]))
    m["rotY"] = round(brot, 3)
    groups.append(dict(id="bench_single", kind="bench", bench=[round(bx, 2), round(bz, 2)], pos=r2(front),
                       members=[m], note="an older man resting"))
    # children at the carousel fence with two parents
    cs = P["karussell"]["pos"]
    kids = []
    for i, ang in enumerate((-0.7, -0.55, -0.4, -0.88)):
        rr = 7.85 if i < 4 else 8.6
        x, z = cs[0] + math.sin(ang) * rr, cs[1] + math.cos(ang) * rr
        v = KIDS[i % 2] if i < 3 else pick_adult()
        m = person(v, "idle_free" if v in KIDS else "chat", mug=None if v not in KIDS else False)
        m["pos"] = r2((x - cs[0], z - cs[1]))
        kids.append(m)
    groups.append(dict(id="kids_karussell", kind="group", pos=r2(cs), members=kids,
                       note="children at the carousel rail, watching the horses"))
    # browsing the deco lanes
    for gid, did, n in (("lebkuchen", "deco-lebkuchen", 1), ("schmuck", "deco-schmuck", 1), ("crepes", "deco-crepes", 2)):
        p = P[did]
        c = add(p["pos"], rot((0, 0.9), p["rot"]))
        mem = []
        for i in range(n):
            w = add(p["pos"], rot((-0.5 + i * 0.6 + R.uniform(-0.1, 0.1), 1.72 + R.uniform(-0.04, 0.08)), p["rot"]))
            m = person(R.choice(ADULTS) if R.random() > 0.15 else R.choice(KIDS), R.choice(["idle", "idle_free", "chat"]))
            m["pos"] = r2((w[0] - c[0], w[1] - c[1]))
            mem.append(m)
        groups.append(dict(id=f"browsing_{gid}", kind="group", pos=r2(c), members=mem, note=f"at the {gid} stall"))
    # the Riesenrad queue at the ticket booth
    rr = P["riesenrad"]
    booth = add(rr["pos"], rot((3.6, 3.9), rr["rot"]))
    q = []
    for i in range(3):
        w = add(rr["pos"], rot((3.0 + 0.1 * i, 5.0 + 0.75 * i), rr["rot"]))
        m = person(pick_adult() if i != 1 else R.choice(KIDS), "idle")
        m["pos"] = r2((w[0] - booth[0], w[1] - booth[1]))
        q.append(m)
    queues.append(dict(id="queue_riesenrad", kind="queue", stall="riesenrad", pos=r2(booth), members=q,
                       note="at the Kasse"))

    # free-standing groups: nudge each to the nearest spot clear of stalls, walker paths and other people
    all_walk = walkers + pairs
    wsegs = [(tuple(a), tuple(b)) for w in all_walk for a, b in zip(w["path"][:-1], w["path"][1:])]
    placed = []
    for g in queues + [g for g in groups if isinstance(g, dict)]:
        for m in g["members"]:
            placed.append(add(tuple(g["pos"]), tuple(m["pos"])))

    def seg_dist(p, a, b):
        ax, az = b[0] - a[0], b[1] - a[1]
        L2 = ax * ax + az * az or 1e-9
        t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * az) / L2))
        return math.hypot(p[0] - a[0] - ax * t, p[1] - a[1] - az * t)

    def ok(c, rad):
        d, _ = clearance(c, obs)
        if d < rad + 0.3:
            return False
        if any(seg_dist(c, a, b) < rad + 0.6 for a, b in wsegs):
            return False
        return all(math.hypot(c[0] - q[0], c[1] - q[1]) > rad + 0.65 for q in placed)

    def free_spot(c, rad):
        for r in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.5, 3.0, 3.6, 4.2):
            for k in range(12 if r else 1):
                a2 = TAU * k / 12
                q = (c[0] + math.sin(a2) * r, c[1] + math.cos(a2) * r)
                if ok(q, rad):
                    return q
        print("  no free spot near", c)
        return c
    final = []
    for g in groups:
        if isinstance(g, tuple):
            _, name, c, n = g
            c = free_spot(c, 0.7)
            g = group(name, c, n, spin=R.random())
            for m in g["members"]:
                placed.append(add(tuple(g["pos"]), tuple(m["pos"])))
        final.append(g)
    groups = final
    data["groups"] = groups
    data["walkers_more"] = [walkers[8], walkers[10]]
    # ---------------- musicians: placed by the engine at the bandstand's slot_* with the instrument
    data["musicians"] = [
        dict(id=f"band_{k}", kind="musician", slot=f"slot_{k}", model=f"people_band_{k}.glb", instrument=f"instr_{k}.glb",
             clip="play", rest_clip="rest", seated=k in ("piano", "drums"),
             note="origin = the instrument's origin (the player's floor spot); use the slot's world transform")
        for k in ("sax", "piano", "bass", "drums")]

    # ---------------- checks
    problems = []
    count = 0

    def chk(pt, who, ignore=()):
        d, name = clearance(pt, obs, ignore)
        if d < 0.25:
            problems.append(f"{who} at {r2(pt)} is {d:.2f} m from {name}")

    for g in data["queues"] + data["groups"]:
        for m in g["members"]:
            pt = add(tuple(g["pos"]), tuple(m["pos"]))
            ign = ("bench",) if g.get("kind") == "bench" else (g.get("stall"),) if g.get("kind") == "queue" else ()
            chk(pt, g["id"], ign)
            count += 1
    for w in data["walkers"] + data["walkers_more"]:
        pts = w["path"]
        for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
            for t in [i / 10 for i in range(11)]:
                chk((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t), w["id"])
        count += 1
    count += len(data["vendors"])
    standing = []
    for g in data["queues"] + data["groups"]:
        for m in g["members"]:
            standing.append((add(tuple(g["pos"]), tuple(m["pos"])), g["id"]))
    for i, (p, gi) in enumerate(standing):
        for q, gj in standing[i + 1:]:
            if math.hypot(p[0] - q[0], p[1] - q[1]) < 0.42:
                problems.append(f"{gi} and {gj} overlap at {r2(p)}")
    for w in data["walkers"] + data["walkers_more"]:
        pts = w["path"]
        for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
            for t in [i / 20 for i in range(21)]:
                pt = (x0 + (x1 - x0) * t, z0 + (z1 - z0) * t)
                for p, gi in standing:
                    if math.hypot(pt[0] - p[0], pt[1] - p[1]) < 0.55:
                        problems.append(f"{w['id']} walks through {gi} at {r2(pt)}")
                        break
    data["count"] = {"people": count, "musicians": 4}
    json.dump(data, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {count} people + 4 musicians")
    for p in problems:
        print("  CLEARANCE", p)
    if a.map:
        draw_map(data, P, obs, a.map)


def draw_map(data, P, obs, path):
    from PIL import Image, ImageDraw
    S, W = 22, 1280
    H = 1000
    ox, oz = W / 2, H / 2 + 60

    def px(p):
        return (ox + p[0] * S, oz + p[1] * S)
    im = Image.new("RGB", (W, H), (24, 26, 34))
    d = ImageDraw.Draw(im)
    for o in obs:
        if o[0] == "circle":
            c, r = o[1], o[2]
            x, y = px(c)
            d.ellipse([x - r * S, y - r * S, x + r * S, y + r * S], outline=(120, 110, 90), width=2)
        else:
            _, c, a, hx, hz, n = o
            pts = [px(add(c, rot((sx * hx, sz * hz), a))) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            d.polygon(pts, outline=(170, 130, 80) if n != "bench" else (120, 120, 140), width=2)
    for w in data["walkers"] + data["walkers_more"]:
        d.line([px(q) for q in w["path"]], fill=(90, 140, 200), width=2)
        x, y = px(w["path"][0])
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(120, 170, 230))
    col = {"queue": (240, 200, 90), "group": (230, 120, 90), "bench": (200, 120, 220)}
    for g in data["queues"] + data["groups"]:
        for m in g["members"]:
            x, y = px(add(tuple(g["pos"]), tuple(m["pos"])))
            c = (120, 220, 140) if m["variant"] in KIDS else col.get(g["kind"], (230, 120, 90))
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=c)
    for v in data["vendors"]:
        x, y = px((v["pos"][0], v["pos"][2]))
        d.rectangle([x - 4, y - 4, x + 4, y + 4], fill=(250, 250, 250))
    d.text((12, 10), "crowd.json, top view (three.js x right, z down): orange = groups, yellow = queues, green = children, "
                     "violet = bench, white = vendors, blue = walker paths", fill=(220, 220, 220))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, quality=90)


if __name__ == "__main__":
    main()
