import bpy, os, math
from mathutils import Vector
B=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(B,"out/gluehwein_stall.glb"))
s=bpy.context.scene
w=bpy.data.worlds.new("w"); s.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.35,0.4,0.5,1)
ld=bpy.data.lights.new("sun","SUN"); ld.energy=3; o=bpy.data.objects.new("sun",ld); o.rotation_euler=(0.8,0,-0.5); s.collection.objects.link(o)
c=bpy.data.cameras.new("c"); c.lens=32; co=bpy.data.objects.new("c",c); s.collection.objects.link(co); s.camera=co
co.location=(-3.4,-1.9,5.6)  # glTF import is Y-up converted back to Z-up
co.location=(-3.4,-5.6,1.9); co.rotation_euler=(Vector((0.1,0,1.45))-co.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='CYCLES'; s.cycles.samples=16; s.render.resolution_x=960; s.render.resolution_y=540
s.render.filepath=os.path.join(B,"out/glb_check.png"); bpy.ops.render.render(write_still=True)
