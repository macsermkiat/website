"""Cycles previews of the organizer's figures (render-only scene; nothing here is exported).

    /home/claude/tools/bpy-venv/bin/python blender/people/preview.py lineup|band|group|test [--samples N] [--res WxH]
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))

import bpy  # noqa: E402
from mathutils import Vector, Matrix, Euler  # noqa: E402

import build  # noqa: E402
import rig  # noqa: E402
import specs  # noqa: E402

REVIEW = os.path.join(REPO, "review", "round-1", "organizer")
TMP = os.path.join(REPO, "blender", "out", "people", "renders")


def mat(name, color, rough=0.8, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def cobble_material():
    m = bpy.data.materials.new("env_cobbles")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    vor = N.new("ShaderNodeTexVoronoi")
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = 9.0
    L.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.02, 0.018, 0.017, 1)
    ramp.color_ramp.elements[1].position = 0.08
    ramp.color_ramp.elements[1].color = (0.09, 0.085, 0.08, 1)
    L.new(vor.outputs["Distance"], ramp.inputs[0])
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    snow = N.new("ShaderNodeMapRange")
    snow.inputs["From Min"].default_value = 0.64
    snow.inputs["From Max"].default_value = 0.7
    L.new(nz.outputs["Fac"], snow.inputs["Value"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    L.new(snow.outputs[0], mix.inputs[0])
    L.new(ramp.outputs[0], mix.inputs[6])
    mix.inputs[7].default_value = (0.32, 0.34, 0.4, 1)
    L.new(mix.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    L.new(vor.outputs["Distance"], bump.inputs["Height"])
    L.new(bump.outputs[0], b.inputs["Normal"])
    return m


def env(scene, backdrop=True, ground=True):
    env_c = bpy.data.collections.new("Env")
    scene.collection.children.link(env_c)
    w = bpy.data.worlds.new("night")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.016, 0.03, 1)
    bg.inputs["Strength"].default_value = 1.0
    if ground:
        me = bpy.data.meshes.new("env_ground")
        s = 30
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new("env_ground", me)
        env_c.objects.link(g)
        me.materials.append(cobble_material())
    return env_c


def light(env_c, name, kind, loc, energy, color, size=0.5, target=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'AREA':
        ld.size = size
    else:
        ld.shadow_soft_size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if target is not None:
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    env_c.objects.link(ob)
    return ob


def camera(env_c, loc, target, lens=50):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cam = bpy.data.objects.new("cam", cd)
    env_c.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    return cam


def bokeh_strings(env_c, y=9.0, n=40, z=3.2, spread=18):
    m = mat("env_bulb", (1, 0.8, 0.5), 0.3, (1.0, 0.6, 0.28), 30)
    import random
    R = random.Random(3)
    for k in range(2):
        for i in range(n):
            x = -spread / 2 + spread * i / n + R.uniform(-0.1, 0.1)
            zz = z + k * 0.7 + 0.45 * math.cos((x + k) * 0.5) ** 2
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, segments=8, ring_count=5, location=(x, y + k * 3, zz))
            o = bpy.context.active_object
            for c in o.users_collection:
                c.objects.unlink(o)
            env_c.objects.link(o)
            o.data.materials.append(m)


def pose_figure(arm, fn, t):
    rest_mats = {b.name: b.matrix_local.to_3x3() for b in arm.data.bones}
    rig.pose_to_bones(arm, rest_mats, fn(t))


def place(spec, coll, loc, rot_z, clip, t, lite=False, name=None):
    fig, arm, body, mug, _ = build.assemble(spec, lite, coll, bake=False, name=name)
    c, clips = build.clip_list(fig, spec)
    fn = dict((n, f) for n, f, d in clips)[clip]
    pose_figure(arm, fn, t)
    arm.location = loc
    arm.rotation_euler = (0, 0, rot_z)
    return fig, arm


def render(scene, path, samples=48, res=(1280, 720), exposure=0.0):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.max_bounces = 6
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Punchy'
    scene.view_settings.exposure = exposure
    scene.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    png = path if path.endswith(".png") else path.rsplit(".", 1)[0] + ".png"
    scene.render.filepath = png
    bpy.ops.render.render(write_still=True)
    if path.endswith(".jpg"):
        from PIL import Image
        Image.open(png).convert("RGB").save(path, quality=90)
    return path


def market_lights(env_c, center=(0, 0, 0), span=6.0):
    cx, cy, cz = center
    light(env_c, "key", 'AREA', (cx - 2.5, cy - 4.5, 3.4), 520, (1.0, 0.72, 0.45), size=2.0, target=(cx, cy, 1.0))
    light(env_c, "fill", 'AREA', (cx + 4.0, cy - 3.0, 2.2), 140, (1.0, 0.78, 0.55), size=3.0, target=(cx, cy, 1.0))
    light(env_c, "rim", 'AREA', (cx + 1.5, cy + 4.0, 3.2), 360, (0.55, 0.65, 1.0), size=2.5, target=(cx, cy, 1.2))
    light(env_c, "moon", 'SUN', (0, 0, 10), 0.15, (0.6, 0.7, 1.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--only", default="")
    ap.add_argument("--clip", default="idle")
    ap.add_argument("--t", type=float, default=1.0)
    ap.add_argument("--cam", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--lite", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    res = tuple(int(x) for x in a.res.split("x"))
    scene, coll = build.reset()
    env_c = env(scene)
    what = a.what
    if what == "test":
        names = a.only.split(",")
        n = len(names)
        for i, nm in enumerate(names):
            place(specs.BY_NAME[nm], coll, (-(n - 1) * 0.45 + i * 0.9, 0, 0), 0.0, a.clip, a.t, lite=a.lite, name=f"f{i}")
        market_lights(env_c)
        if a.cam:
            v = [float(x) for x in a.cam.split(",")]
            camera(env_c, v[:3], v[3:6], v[6] if len(v) > 6 else 50)
        else:
            camera(env_c, (0.6, -4.2, 1.35), (0, 0, 0.95), 50)
        render(scene, a.out or os.path.join(TMP, "test.jpg"), a.samples, res)
    elif what == "clips":
        nm = a.only.split(",")[0]
        items = [x.split("@") for x in a.clip.split(",")]
        n = len(items)
        for i, (cl, tt) in enumerate(items):
            place(specs.BY_NAME[nm], coll, (-(n - 1) * 0.5 + i * 1.0, 0, 0), float(a.t), cl, float(tt), lite=a.lite,
                  name=f"c{i}")
        # a bench for the sitters
        bench = bpy.data.meshes.new("env_bench")
        market_lights(env_c)
        v = [float(x) for x in a.cam.split(",")] if a.cam else [0.8, -5.5, 1.3, 0, 0, 0.8, 40]
        camera(env_c, v[:3], v[3:6], v[6] if len(v) > 6 else 50)
        render(scene, a.out or os.path.join(TMP, "clips.jpg"), a.samples, res)
    elif what == "lineup":
        people = specs.BASE + specs.VENDORS + specs.BAND
        clips = {"crowd": "idle", "vendor": "idle_free", "band": "rest"}
        n = len(people)
        # two rows: base figures in front, vendors and band behind
        front = specs.BASE
        back = specs.VENDORS + [s for s in specs.BAND]
        for i, sp in enumerate(front):
            x = -(len(front) - 1) * 0.42 + i * 0.84
            clip = ["idle", "chat", "idle_free", "drink", "idle", "chat_free", "idle_free", "laugh_free"][i]
            place(sp, coll, (x, 0, 0), 0.0 + 0.12 * math.sin(i * 1.7), clip, 1.3 + i * 0.7, name=f"a{i}")
        for i, sp in enumerate(back):
            x = -(len(back) - 1) * 0.47 + i * 0.94
            clip = "idle_free" if sp["role"] == "vendor" else "chat_free"
            place(sp, coll, (x, 1.25, 0), 0.08 * math.sin(i * 2.3), clip, 0.8 + i * 0.9, name=f"b{i}")
        market_lights(env_c)
        bokeh_strings(env_c, y=8.0)
        camera(env_c, (0.0, -8.6, 1.55), (0, 0.5, 0.95), 42)
        render(scene, a.out or os.path.join(REVIEW, "lineup.jpg"), a.samples, res)
    elif what == "band":
        # the ride builder's bandstand and instruments (raw exports), players at the slot_* empties
        RAWD = os.path.join(REPO, "blender", "out", "raw")

        def imp(path):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=path)
            new = [o for o in bpy.data.objects if o not in before]
            for o in new:
                for c in list(o.users_collection):
                    c.objects.unlink(o)
                env_c.objects.link(o)
            return new
        stand = imp(os.path.join(RAWD, "bandstand.glb"))
        bpy.context.view_layer.update()
        for o in stand:
            if o.name.startswith("snow_"):
                o.hide_render = True
        slots = {o.name.split(".")[0][5:]: o for o in stand if o.name.startswith("slot_")}
        for sp in specs.BAND:
            inst = sp["inst"]
            M = slots[inst].matrix_world.copy()
            loc = M.translation.copy()
            yaw = M.to_euler().z
            objs = imp(os.path.join(RAWD, f"instr_{inst}.glb"))
            root = bpy.data.objects.new(f"instr_root_{inst}", None)
            env_c.objects.link(root)
            for o in objs:
                if o.parent is None:
                    o.parent = root
            root.location = loc
            root.rotation_euler = (0, 0, yaw)
            place(sp, coll, loc, yaw, "play", a.t, name=f"m_{inst}")
        light(env_c, "key", 'AREA', (1.5, -5.2, 4.6), 700, (1.0, 0.7, 0.42), size=2.5, target=(0, 0.2, 1.6))
        light(env_c, "fill", 'AREA', (-4.5, -3.5, 3.0), 200, (1.0, 0.8, 0.55), size=3.0, target=(0, 0.2, 1.6))
        light(env_c, "stage", 'POINT', (0.0, -0.5, 3.3), 120, (1.0, 0.68, 0.38), size=0.3)
        light(env_c, "rim", 'AREA', (0.5, 5.0, 4.0), 300, (0.55, 0.65, 1.0), size=3.0, target=(0, 0, 1.6))
        light(env_c, "moon", 'SUN', (0, 0, 10), 0.12, (0.6, 0.7, 1.0))
        if a.cam:
            v = [float(x) for x in a.cam.split(",")]
            camera(env_c, v[:3], v[3:6], v[6] if len(v) > 6 else 40)
        else:
            camera(env_c, (0.9, -6.6, 2.5), (-0.1, -0.3, 1.55), 36)
        render(scene, a.out or os.path.join(REVIEW, "band.jpg"), a.samples, res)
    elif what == "group":
        grp = [("people_woman_coat", (0.55, 0.05), "chat", 1.2), ("people_man_coat", (-0.5, 0.15), "drink", 2.2),
               ("people_man_parka", (0.05, 0.75), "laugh", 1.3), ("people_woman_older", (-0.05, -0.55), "idle", 2.5)]
        for i, (nm, (x, y), clip, t) in enumerate(grp):
            yaw = math.atan2(-x, -y) + math.pi / 2 + math.pi   # face the centre
            d = Vector((0, 0, 0)) - Vector((x, y, 0))
            yaw = math.atan2(d.y, d.x) + math.pi / 2
            place(specs.BY_NAME[nm], coll, (x, y, 0), yaw, clip, t, name=f"g{i}")
        place(specs.BY_NAME["people_child_girl"], coll, (1.5, -0.35, 0), 2.6, "idle_free", 0.5, name="g5")
        market_lights(env_c)
        bokeh_strings(env_c, y=7.0)
        camera(env_c, (1.6, -3.9, 1.7), (0.1, 0.1, 1.05), 45)
        render(scene, a.out or os.path.join(REVIEW, "group_chat.jpg"), a.samples, res)


if __name__ == "__main__":
    main()
