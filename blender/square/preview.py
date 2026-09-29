"""Night preview renders of the architect's assets, assembled from the raw glbs + layout.json.

Usage: NM_DEVICE=METAL NM_THREADS=0 ~/nachtmarkt-tools/bpy-venv/bin/python blender/square/preview.py <shot> [samples] [out.jpg]
shots: home | street | tree | cobbles | church | roofs
Renders at 1920x1080 (RES_X overrides), keeps the PNG in blender/square/out/renders/ and writes a
1280 px review JPEG.  Stalls and landmarks are plain stand-ins at the real assets' sizes (other roles
build the real ones).
"""
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy
from mathutils import Vector, Matrix
import architect_common as C
import architect_plan as P

shot = sys.argv[1] if len(sys.argv) > 1 else "home"
samples = int(sys.argv[2]) if len(sys.argv) > 2 else 128
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(C.REPO, "review", "round-1", "architect", f"{shot}.jpg")
os.makedirs(os.path.dirname(out), exist_ok=True)
random.seed(1)

scene = C.reset()
C.setup_cycles(samples, (int(os.environ.get("RES_X", 1920)), int(os.environ.get("RES_X", 1920)) * 9 // 16))
C.night_world(1.0)
stand = C.collection("StandIns")


def imp(path, loc=(0, 0, 0), rot=0.0):
    if not os.path.exists(path):
        C.log("missing", path); return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = list(set(bpy.data.objects) - before)
    for o in new:
        if o.parent is None:
            o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(rot, 4, "Z") @ o.matrix_world
    return new


want_town = True
want_square = True
objs = []
objs += imp(os.path.join(C.REPO, "blender", "square", "out", "square_raw.glb"))
if want_town:
    objs += imp(os.path.join(C.REPO, "blender", "town", "out", "town_raw.glb"))
layout = P.load_layout()
tree_p = next(p for p in layout["places"] if p["id"] == "tree")
tp = C.three_to_blender(*tree_p["pos"])
objs += imp(os.path.join(C.REPO, "blender", "square", "out", "tree_raw.glb"), tp, tree_p.get("rotY", 0))

# light_ empties -> warm point lights (what the browser does with real-time lights)
church_tower = C.three_to_blender(8, -56)
for o in list(bpy.data.objects):
    if o.type == "EMPTY" and o.name.startswith("light_church"):
        # floodlights at the tower foot, aimed up the tower face (the browser may use a spot here)
        p = o.matrix_world.translation
        aim = Vector((church_tower.x, church_tower.y, 22.0))
        C.add_light("L_" + o.name, "SPOT", p, 9000.0, (1.0, 0.72, 0.45), size=0.3,
                    rot=(aim - p).to_track_quat("-Z", "Y").to_euler())
        bpy.data.lights["L_" + o.name].spot_size = math.radians(38)
        bpy.data.lights["L_" + o.name].spot_blend = 0.6
    elif o.type == "EMPTY" and o.name.startswith("light_") and not o.name.startswith("light_string"):
        C.add_light("L_" + o.name, "POINT", o.matrix_world.translation, 45.0, (1.0, 0.62, 0.32), size=0.12)
    if o.type == "MESH":
        for m in o.data.materials:
            if m and m.name.startswith("snow"):
                o.hide_render = True        # previews show the market without snow

# stand-ins for stalls and landmarks
clay = C.solid("standin_clay", (0.42, 0.40, 0.38), rough=0.8)
glow = C.solid("standin_glow", (1, 0.7, 0.4), emit=(1.0, 0.6, 0.28), strength=4.0)
for p in layout["places"]:
    kind = p["kind"]
    if kind == "scenery":
        continue
    x, y = p["pos"][0], -p["pos"][1]
    F = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(p.get("rotY", 0), 4, "Z")
    g = C.Geo("standin_" + p["id"], clay); g.frame = F
    gl = C.Geo("standin_glow_" + p["id"], glow); gl.frame = F
    if kind in ("section", "deco"):
        w, d, h = (3.6, 2.4, 2.4) if kind == "section" else (3.0, 2.0, 2.2)
        g.box((0, 0, h / 2), (w, d, h))
        g.prism([(-w / 2 - 0.2, -d / 2 - 0.3, h), (w / 2 + 0.2, -d / 2 - 0.3, h), (w / 2 + 0.2, 0, h + 1.0), (-w / 2 - 0.2, 0, h + 1.0)], (0, 0, 0.05))
        g.prism([(w / 2 + 0.2, d / 2 + 0.3, h), (-w / 2 - 0.2, d / 2 + 0.3, h), (-w / 2 - 0.2, 0, h + 1.0), (w / 2 + 0.2, 0, h + 1.0)], (0, 0, 0.05))
        for k in range(12):
            gl.bulb((-w / 2 + w * (k + 0.5) / 12, -d / 2 - 0.32, h - 0.1 - 0.06 * math.sin(math.pi * ((k % 4) + 0.5) / 4)), 0.03)
        C.add_light("SL_" + p["id"], "AREA", F @ Vector((0, -d / 2 + 0.3, h - 0.2)), 120 if kind == "section" else 70,
                    (1.0, 0.6, 0.3), size=w * 0.7, rot=(0, 0, 0))
    elif p["id"] == "bandstand":
        g.cyl((0, 0, 0.4), 4.0, 4.0, 0.8, seg=8)
        for k in range(8):
            a = k * math.pi / 4
            g.cyl((3.6 * math.cos(a), 3.6 * math.sin(a), 2.4), 0.12, 0.12, 3.2, seg=6)
        g.cyl((0, 0, 4.6), 4.6, 0.3, 1.8, seg=8)
        C.add_light("SL_band", "POINT", F @ Vector((0, 0, 3.4)), 400, (1.0, 0.6, 0.3), size=1)
    elif p["id"] == "riesenrad":
        R = 12.0
        g.cyl((0, 0, 0.3), 4, 4, 0.6, seg=4, rot=(0, 0, math.pi / 4), scale=(1.6, 0.6, 1))
        for sx in (-1, 1):
            g.beam((sx * 4, -1.2, 0), (0, -1.2, R + 1.5), 0.3, 0.3)
            g.beam((sx * 4, 1.2, 0), (0, 1.2, R + 1.5), 0.3, 0.3)
        pts = []
        for k in range(33):
            a = 2 * math.pi * k / 32
            pts.append((R * math.cos(a), 0, R + 1.5 + R * math.sin(a)))
        g.tube(pts, 0.18, tseg=6)
        for k in range(16):
            a = 2 * math.pi * k / 16
            g.beam((0, 0, R + 1.5), (R * math.cos(a), 0, R + 1.5 + R * math.sin(a)), 0.08, 0.08)
            gl.bulb((R * math.cos(a), -0.3, R + 1.5 + R * math.sin(a)), 0.15)
            g.box((R * math.cos(a), 0, R + 1.5 + R * math.sin(a) - 1.0), (1.2, 1.4, 1.3))
    elif p["id"] == "karussell":
        g.cyl((0, 0, 0.3), 6.0, 6.0, 0.6, seg=16)
        g.cyl((0, 0, 2.6), 0.5, 0.5, 4.6, seg=10)
        g.cyl((0, 0, 5.6), 6.3, 0.5, 2.0, seg=16)
        for k in range(16):
            a = 2 * math.pi * k / 16
            gl.bulb((6.2 * math.cos(a), 6.2 * math.sin(a), 4.65), 0.08)
        C.add_light("SL_car", "POINT", F @ Vector((0, 0, 3.2)), 500, (1.0, 0.6, 0.3), size=1)
    g.finish(stand); gl.finish(stand)

C.add_light("MarketGlow", "POINT", (0, 0, 14), float(os.environ.get("GLOW", 9000)), (1.0, 0.62, 0.35), size=10)
C.add_light("Moon", "SUN", (0, 0, 50), 0.10, (0.55, 0.65, 1.0), rot=(math.radians(55), 0, math.radians(200)))

# cameras
home = layout["camera"]["home"]
hp = home["pos"]; ht = home["target"]
if shot == "home":
    vf = math.radians(home.get("fov", 42))
    hf = 2 * math.atan(math.tan(vf / 2) * 16 / 9)
    C.camera((hp[0], -hp[2], hp[1]), (ht[0], -ht[2], ht[1]), lens=18 / math.tan(hf / 2))
    C.compositor_fog_glare(near=30, far=150, fog_amount=0.45)
elif shot == "street":
    t0, t1 = math.radians(218), math.radians(262)
    r0 = P.plaza_r(t0) - 4
    r1 = P.house_r(t1) + 2
    C.camera((r0 * math.cos(t0), r0 * math.sin(t0), 1.75), (r1 * math.cos(t1), r1 * math.sin(t1), 6.5), lens=24)
    C.compositor_fog_glare(near=40, far=180, fog_amount=0.3)
elif shot == "church":
    C.camera((-7.5, 28.0, 1.7), (9, 56, 19), lens=19)
    C.compositor_fog_glare(near=40, far=180, fog_amount=0.3)
elif shot == "tree":
    C.camera((tp.x - 1.5, tp.y - 13.8, 1.8), (tp.x, tp.y, 6.6), lens=18)
    C.compositor_fog_glare(near=40, far=180, fog_amount=0.35)
elif shot == "roofs":
    # from the top of the Ferris wheel over the ring's roofs (where the wedge gaps used to show)
    fw = next(p for p in layout["places"] if p["id"] == "riesenrad")
    fp = C.three_to_blender(*fw["pos"])
    C.camera((fp.x, fp.y, 25.0), (30.0, 52.0, 8.0), lens=24)
    C.compositor_fog_glare(near=50, far=220, fog_amount=0.3)
elif shot == "cobbles":
    t0, t1 = math.radians(286), math.radians(300)
    r0 = P.plaza_r(t0) - 5.5
    r1 = P.plaza_r(t1) + 1.0
    C.camera((r0 * math.cos(t0), r0 * math.sin(t0), 1.25), (r1 * math.cos(t1), r1 * math.sin(t1), 0.2), lens=26)
    C.compositor_fog_glare(near=30, far=150, fog_amount=0.3)

scene.view_settings.exposure = float(os.environ.get("EXPOSURE", "0.6"))
C.render(out, samples)
