"""Night preview renders in Cycles (render-only environment, never exported)."""
import math
import os
import time

import bpy
from mathutils import Vector

from . import state


def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def ground_material():
    """Trodden snow with slushy patches, render only."""
    m, nt, b = _mat("env_ground")
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.45
    nz.inputs["Detail"].default_value = 8
    nz.inputs["Roughness"].default_value = 0.6
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    slush = N.new("ShaderNodeMapRange")
    slush.inputs["From Min"].default_value = 0.56
    slush.inputs["From Max"].default_value = 0.66
    L.new(nz.outputs["Fac"], slush.inputs["Value"])
    fine = N.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 9.0
    fine.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], fine.inputs["Vector"])
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    L.new(slush.outputs[0], mix.inputs[0])
    mix.inputs[6].default_value = (0.66, 0.70, 0.78, 1)
    mix.inputs[7].default_value = (0.20, 0.20, 0.22, 1)
    L.new(mix.outputs[2], b.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.62
    rr.inputs["To Max"].default_value = 0.25
    L.new(slush.outputs[0], rr.inputs["Value"])
    L.new(rr.outputs[0], b.inputs["Roughness"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    L.new(fine.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs[0], b.inputs["Normal"])
    return m


def night_scene(ground_size=40, bokeh=False):
    """World, moon, ground and a few far-off market lights for depth."""
    scene = bpy.context.scene
    env = state.env_collection()
    world = scene.world or bpy.data.worlds.new("Night")
    scene.world = world
    world.use_nodes = True
    wn = world.node_tree
    bg = wn.nodes["Background"]
    grad = wn.nodes.new("ShaderNodeTexGradient")
    tc = wn.nodes.new("ShaderNodeTexCoord")
    sep = wn.nodes.new("ShaderNodeSeparateXYZ")
    wn.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = wn.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.48
    ramp.color_ramp.elements[0].color = (0.020, 0.018, 0.030, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.004, 0.009, 0.028, 1)
    wn.links.new(sep.outputs[2], ramp.inputs[0])
    wn.links.new(ramp.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    del grad

    me = bpy.data.meshes.new("env_ground")
    s = ground_size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("env_ground", me)
    env.objects.link(g)
    me.materials.append(ground_material())

    add_light("env_moon", 'SUN', (0, 0, 20), 0.22, (0.62, 0.72, 1.0),
              rot=(math.radians(55), 0, math.radians(-40)))
    add_light("env_skyfill", 'AREA', (-6, -8, 7), 60, (0.55, 0.65, 1.0), size=6,
              rot=(math.radians(50), 0, math.radians(-35)))
    if bokeh:
        m, nt, b = _mat("env_bokeh")
        b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.30, 1)
        b.inputs["Emission Strength"].default_value = 12
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        import random
        R = random.Random(4)
        for k in range(3):
            y = 9 + 4 * k
            for i in range(26):
                x = -12 + i * 0.95 + R.uniform(-0.1, 0.1)
                z = 3.2 + 0.5 * math.sin(i * 0.8 + k) + k * 0.6
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, segments=8, ring_count=6,
                                                     location=(x, y, z))
                o = bpy.context.active_object
                for c in o.users_collection:
                    c.objects.unlink(o)
                env.objects.link(o)
                o.data.materials.append(m)
    return scene


def add_light(name, kind, loc, energy, color=(1.0, 0.62, 0.32), size=0.3, rot=(0, 0, 0),
              spot_size=None, spot_blend=None, size_y=None, target=None):
    """Render-only light. `target` aims a SPOT/AREA/SUN at a point (overrides rot)."""
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'AREA':
        ld.size = size
        if size_y:
            ld.shape = 'RECTANGLE'
            ld.size_y = size_y
    elif kind in ('POINT', 'SPOT'):
        ld.shadow_soft_size = size
    if kind == 'SPOT':
        if spot_size:
            ld.spot_size = spot_size
        if spot_blend is not None:
            ld.spot_blend = spot_blend
    if target is not None:
        rot = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    ob.rotation_euler = rot
    state.env_collection().objects.link(ob)
    return ob


def lights_at_markers(energy=90, color=(1.0, 0.6, 0.3), size=0.25):
    """Point lights where the engine will put its real-time lights (light_* empties)."""
    for o in list(state.export_collection().objects):
        if o.name.startswith("light_"):
            add_light("env_" + o.name, 'POINT', o.location, energy, color, size)


def camera(loc, target, lens=32, dof=None):
    scene = bpy.context.scene
    cd = bpy.data.cameras.new("env_cam")
    cd.lens = lens
    cam = bpy.data.objects.new("env_cam", cd)
    state.env_collection().objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = (Vector(target) - Vector(loc)).length
        cd.dof.aperture_fstop = dof
    scene.camera = cam
    return cam


def render(path_png, samples=48, res=(1280, 720), exposure=0.0, jpeg=None, jpeg_width=1280):
    """Render the scene camera to PNG (and a review JPEG). Device/threads from NM_DEVICE/NM_THREADS, OIDN denoise."""
    scene = bpy.context.scene
    state.configure_cycles(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    scene.cycles.max_bounces = 6
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Punchy'
    scene.view_settings.exposure = exposure
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = path_png
    os.makedirs(os.path.dirname(path_png), exist_ok=True)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[nmlib] rendered {os.path.basename(path_png)} in {time.time() - t0:.1f}s")
    if jpeg:
        to_jpeg(path_png, jpeg, jpeg_width)
    return path_png


def to_jpeg(png, jpg, width=1280, quality=88):
    from PIL import Image
    im = Image.open(png).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(jpg), exist_ok=True)
    im.save(jpg, quality=quality)


def contact_sheet(items, out_jpg, cols=3, tile=(420, 236), pad=6, title=None):
    """items: [(image_path, label)] -> one JPEG grid with labels."""
    from PIL import Image, ImageDraw, ImageFont
    rows = (len(items) + cols - 1) // cols
    top = 34 if title else 0
    W = cols * tile[0] + (cols + 1) * pad
    H = rows * (tile[1] + 22) + (rows + 1) * pad + top
    sheet = Image.new("RGB", (W, H), (14, 14, 20))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(os.path.join(state.FONTS_DIR, "AlegreyaSC-ExtraBold.ttf"), 17)
        ft = ImageFont.truetype(os.path.join(state.FONTS_DIR, "AlegreyaSC-ExtraBold.ttf"), 24)
    except Exception:
        f = ft = ImageFont.load_default()
    if title:
        d.text((pad + 4, 4), title, fill=(240, 220, 180), font=ft)
    for i, (p, label) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (tile[0] + pad)
        y = top + pad + r * (tile[1] + 22 + pad)
        im = Image.open(p).convert("RGB")
        im = im.resize(tile, Image.LANCZOS)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + tile[1] + 2), label, fill=(235, 215, 170), font=f)
    sheet.save(out_jpg, quality=88)
