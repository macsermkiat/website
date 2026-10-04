"""Close-up night preview of the SHIPPED site/public/models/signpost.glb (round 5 pass 2).

Imports the delivered file (meshopt stripped by decode_glb.mjs) instead of rebuilding, so the render
shows exactly what the browser gets.  Same camera and lights as signpost.py's PREVIEW block; the
lantern light sits on the glb's own light_sign_0 empty.
    /home/claude/tools/bpy-venv/bin/python blender/square/signpost_preview.py [samples] [out.jpg]
"""
import os, sys, math, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy
import architect_common as C

HERE = os.path.dirname(os.path.abspath(__file__))
samples = int(sys.argv[1]) if len(sys.argv) > 1 else 48
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(C.REPO, "review", "round-5", "architect", "signpost.jpg")
src = os.path.join(C.MODELS, "signpost.glb")
dec = os.path.join(HERE, "out", "signpost_decoded.glb")
subprocess.run(["node", os.path.join(HERE, "decode_glb.mjs"), src, dec], check=True)

scene = C.reset()
bpy.ops.import_scene.gltf(filepath=dec)
lamp = next(o for o in bpy.data.objects if o.name.startswith("light_sign_0"))
lp = lamp.matrix_world.translation.copy()
print("[preview] light_sign_0 at", tuple(round(v, 2) for v in lp))
print("[preview] act_sign nodes:", sorted(o.name for o in bpy.data.objects if o.name.startswith("act_sign_")))

C.setup_cycles(samples=samples, res=(1280, 720))
C.night_world(0.6)
gp = bpy.data.meshes.new("pv_ground")
gp.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
gpo = bpy.data.objects.new("pv_ground", gp); bpy.context.scene.collection.objects.link(gpo)
gpo.data.materials.append(C.solid("pv_cobble", (0.06, 0.055, 0.05), rough=0.35))
C.add_light("lantern", "POINT", (lp.x, lp.y, lp.z), 60, (1.0, 0.72, 0.45), size=0.05)
C.add_light("market_glow", "AREA", (-3, -6, 4), 400, (1.0, 0.7, 0.45), size=6, rot=(math.radians(60), 0, math.radians(-25)))
C.add_light("moon", "SUN", (0, 0, 10), 0.25, (0.6, 0.7, 1.0), rot=(math.radians(50), 0, math.radians(30)))
C.camera((1.6, -5.2, 2.6), (0, 0, 3.05), lens=40)
C.compositor_fog_glare(near=8, far=60, fog_amount=0.2)
C.render(out)
