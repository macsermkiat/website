"""Architect's Blender helpers: geometry accumulation with real-world UVs, PBR materials from
numpy textures, AO baking, glb export + web optimisation, and night preview renders.

Used by blender/square/*.py and blender/town/*.py. Run scripts with
/home/claude/tools/bpy-venv/bin/python <script>.py (cloud machine; see docs/BUILD.md "Where things run").
Every Cycles render and bake honours NM_DEVICE (CPU, or METAL/CUDA/OPTIX/HIP/ONEAPI for the GPU) and
NM_THREADS (0 = all cores), as blender/lib/nmlib/render.py does.
"""
import bpy, bmesh, math, random, os, sys, json, subprocess, time
import numpy as np
from mathutils import Matrix, Vector, Euler

LIB = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(LIB))
MODELS = os.path.join(REPO, "site", "public", "models")
sys.path.insert(0, LIB)
import architect_tex as TX  # noqa: E402


def log(*a):
    print("[arch]", *a, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def three_to_blender(x, z, y=0.0):
    """layout [x, z] (three.js, Y-up) -> Blender (x, y, z) Z-up."""
    return Vector((x, -z, y))


# ------------------------------------------------------------------ geometry accumulator

_AX = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]


class Geo:
    """Accumulates primitives for ONE material into one bmesh, with UVs in metres / uv_m.

    `frame` is a matrix applied after each primitive (e.g. a house's placement); UVs are computed
    in frame-local space so facades line up.  `uv_m` = (metres per texture repeat along u, along v).
    """

    def __init__(self, name, mat, uv_m=(1.0, 1.0)):
        self.name, self.mat = name, mat
        self.uv_m = uv_m
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.frame = Matrix.Identity(4)
        self.col = None

    # --- uv helpers
    def _planar_uv(self, faces, uv_m=None, off=(0, 0)):
        su, sv = uv_m or self.uv_m
        for f in faces:
            n = f.normal
            if n.length < 1e-9:
                f.normal_update(); n = f.normal
            if abs(n.z) < 0.7:
                ua = Vector((0, 0, 1)).cross(n).normalized()
                va = n.cross(ua).normalized()
                if va.z < 0: va = -va
            else:
                ua, va = Vector((1, 0, 0)), Vector((0, 1, 0)) if n.z > 0 else Vector((0, -1, 0))
            for l in f.loops:
                p = l.vert.co
                l[self.uv].uv = (p.dot(ua) / su + off[0], p.dot(va) / sv + off[1])

    def _finish_prim(self, verts, M_after):
        bmesh.ops.transform(self.bm, matrix=self.frame @ M_after, verts=verts)

    def _faces_of(self, verts):
        fs = set()
        for v in verts:
            fs.update(v.link_faces)
        return list(fs)

    # --- primitives (coordinates in frame-local space)
    def box(self, center, size, rot=(0, 0, 0), uv_m=None, skip_bottom=False, rand_off=True, skip_back=False):
        """Box with UVs mapped per face, u along the face's longer side (wood grain along beams)."""
        sx, sy, sz = size
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        vs = r["verts"]
        faces = self._faces_of(vs)
        su, sv = uv_m or self.uv_m
        dims = (sx, sy, sz)
        o = (random.random() * 7, random.random() * 7) if rand_off else (0, 0)
        kill = []
        for f in faces:
            f.normal_update()
            n = f.normal
            a = max(range(3), key=lambda i: abs(n[i]))
            if (skip_bottom and a == 2 and n[2] < 0) or (skip_back and a == 1 and n[1] > 0):
                kill.append(f); continue
            b, c = [i for i in range(3) if i != a]
            if dims[c] > dims[b] and a != 2:
                pass
            # for side faces keep v vertical unless the face is much longer horizontally than tall
            for l in f.loops:
                p = l.vert.co
                ub, vc = (p[b] + 0.5) * dims[b], (p[c] + 0.5) * dims[c]
                if dims[c] > dims[b] * 1.0 and a == 2:
                    ub, vc = vc, ub
                l[self.uv].uv = (ub / su + o[0], vc / sv + o[1])
        if kill:
            bmesh.ops.delete(self.bm, geom=kill, context="FACES_ONLY")
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((sx, sy, sz, 1))
        self._finish_prim(vs, M)
        return vs

    def beam(self, a, b, w, d, up=(0, 0, 1), uv_m=None, skip_back=False, skip_ends=False):
        """Box from a to b (centre line); w = width across (perpendicular to `up`), d = size along `up`.
        skip_ends drops the two end caps (for members whose ends butt into another member)."""
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        x = (b - a).normalized()
        upv = Vector(up)
        if abs(x.dot(upv)) > 0.99: upv = Vector((0, 1, 0))
        y = upv.cross(x).normalized(); z = x.cross(y)
        # y: depth direction (normal to wall for up=(0,0,1) only if x horizontal) -> use provided frame
        R = Matrix((x, y, z)).transposed().to_4x4()
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        vs = r["verts"]
        su, sv = uv_m or self.uv_m
        o = (random.random() * 7, random.random() * 7)
        for f in self._faces_of(vs):
            for l in f.loops:
                p = l.vert.co
                f.normal_update()
                n = f.normal
                ax = max(range(3), key=lambda i: abs(n[i]))
                if ax == 0:
                    l[self.uv].uv = ((p[1] + 0.5) * w / su + o[0], (p[2] + 0.5) * d / sv + o[1])
                else:
                    other = 2 if ax == 1 else 1
                    dim = d if other == 2 else w
                    l[self.uv].uv = ((p[0] + 0.5) * L / su + o[0], (p[other] + 0.5) * dim / sv + o[1])
        if skip_back or skip_ends:
            kill = [f for f in self._faces_of(vs)
                    if (skip_back and all(v.co.z < -0.499 for v in f.verts))
                    or (skip_ends and (all(v.co.x < -0.499 for v in f.verts) or all(v.co.x > 0.499 for v in f.verts)))]
            bmesh.ops.delete(self.bm, geom=kill, context="FACES_ONLY")
            vs = [v for v in vs if v.is_valid]
        M = Matrix.Translation((a + b) / 2) @ R @ Matrix.Diagonal((L, w, d, 1))
        self._finish_prim(vs, M)
        return vs

    def wall_beam(self, a, b, w, depth, y0, ends=True):
        """Timber on a facade in the local x-z plane (facade at y=y0, proud toward -y by `depth`).
        a, b are (x, z) points of the beam centreline.  ends=False drops the end caps (posts between
        sill and plate, rails and braces between posts, mullions inside a frame)."""
        ax, az = a; bx, bz = b
        return self.beam((ax, y0 - depth / 2, az), (bx, y0 - depth / 2, bz), w, depth, up=(0, -1, 0), skip_back=True,
                         skip_ends=not ends)

    def frame_ring(self, x, zb, ww, wh, fw, fd, y0, outer=False):
        """Rectangular window frame on a facade (plane y=y0, facing -y): front ring, inner reveal and
        outer edges, no back faces (24 tris)."""
        xo0, xo1, zo0, zo1 = x - ww / 2 - fw, x + ww / 2 + fw, zb - fw, zb + wh + fw
        xi0, xi1, zi0, zi1 = x - ww / 2, x + ww / 2, zb, zb + wh
        yF = y0 - fd
        O = [(xo0, zo0), (xo1, zo0), (xo1, zo1), (xo0, zo1)]
        I = [(xi0, zi0), (xi1, zi0), (xi1, zi1), (xi0, zi1)]
        vs = []
        def V(p, y): 
            v = self.bm.verts.new((p[0], y, p[1])); vs.append(v); return v
        of = [V(p, yF) for p in O]; ifr = [V(p, yF) for p in I]
        ob = [V(p, y0) for p in O]; ib = [V(p, y0) for p in I]
        fs = []
        for i in range(4):
            j = (i + 1) % 4
            fs.append(self.bm.faces.new((of[i], of[j], ifr[j], ifr[i])))    # front ring
            fs.append(self.bm.faces.new((ifr[i], ifr[j], ib[j], ib[i])))    # reveal
            if outer:
                fs.append(self.bm.faces.new((ob[i], ob[j], of[j], of[i])))  # outer edge
        for f in fs:
            f.normal_update()
        self._planar_uv(fs)
        self._finish_prim(vs, Matrix.Identity(4))

    def prism(self, pts, depth_vec, uv_m=None, caps=True, off=(0, 0)):
        """Extrude a planar polygon `pts` (list of 3-tuples, CCW seen from the front) along depth_vec."""
        dv = Vector(depth_vec)
        v0 = [self.bm.verts.new(Vector(p)) for p in pts]
        v1 = [self.bm.verts.new(Vector(p) + dv) for p in pts]
        faces = []
        if caps:
            faces.append(self.bm.faces.new(v0[::-1]))
            faces.append(self.bm.faces.new(v1))
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            faces.append(self.bm.faces.new((v0[i], v0[j], v1[j], v1[i])))
        for f in faces: f.normal_update()
        # make sure caps face outward: front cap normal should oppose depth_vec
        if caps and faces[0].normal.dot(dv) > 0:
            for f in faces: f.normal_flip()
        self._planar_uv(faces, uv_m, off)
        self._finish_prim(v0 + v1, Matrix.Identity(4))
        return faces

    def poly(self, pts, uv_m=None, uv_rect=None, off=(0, 0)):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        f = self.bm.faces.new(vs)
        f.normal_update()
        if uv_rect:
            self._rect_uv([f], uv_rect)
        else:
            self._planar_uv([f], uv_m, off)
        self._finish_prim(vs, Matrix.Identity(4))
        return f

    def _rect_uv(self, faces, rect):
        """Map the faces' planar bounds onto a uv rectangle (u0, v0, u1, v1) - for atlas cells."""
        u0, v0, u1, v1 = rect
        for f in faces:
            n = f.normal
            if abs(n.z) < 0.7:
                ua = Vector((0, 0, 1)).cross(n).normalized(); va = n.cross(ua).normalized()
                if va.z < 0: va = -va
            else:
                ua, va = Vector((1, 0, 0)), Vector((0, 1, 0))
            us = [l.vert.co.dot(ua) for l in f.loops]; vs = [l.vert.co.dot(va) for l in f.loops]
            a0, a1, b0, b1 = min(us), max(us), min(vs), max(vs)
            for l in f.loops:
                p = l.vert.co
                tu = (p.dot(ua) - a0) / max(a1 - a0, 1e-6); tv = (p.dot(va) - b0) / max(b1 - b0, 1e-6)
                l[self.uv].uv = (u0 + (u1 - u0) * tu, v0 + (v1 - v0) * tv)

    def quad_rect(self, center, w, h, normal_axis="-y", uv_rect=None, uv_m=None):
        """Axis-aligned rectangle in frame space. normal_axis '-y' = facade facing front."""
        cx, cy, cz = center
        if normal_axis == "-y":
            pts = [(cx - w / 2, cy, cz - h / 2), (cx + w / 2, cy, cz - h / 2), (cx + w / 2, cy, cz + h / 2), (cx - w / 2, cy, cz + h / 2)]
        elif normal_axis == "+y":
            pts = [(cx + w / 2, cy, cz - h / 2), (cx - w / 2, cy, cz - h / 2), (cx - w / 2, cy, cz + h / 2), (cx + w / 2, cy, cz + h / 2)]
        elif normal_axis == "+x":
            pts = [(cx, cy - w / 2, cz - h / 2), (cx, cy + w / 2, cz - h / 2), (cx, cy + w / 2, cz + h / 2), (cx, cy - w / 2, cz + h / 2)]
        elif normal_axis == "-x":
            pts = [(cx, cy + w / 2, cz - h / 2), (cx, cy - w / 2, cz - h / 2), (cx, cy - w / 2, cz + h / 2), (cx, cy + w / 2, cz + h / 2)]
        else:  # +z
            pts = [(cx - w / 2, cy - h / 2, cz), (cx + w / 2, cy - h / 2, cz), (cx + w / 2, cy + h / 2, cz), (cx - w / 2, cy + h / 2, cz)]
        return self.poly(pts, uv_m=uv_m, uv_rect=uv_rect)

    def cyl(self, center, r1, r2, depth, seg=12, rot=(0, 0, 0), caps=True, uv_m=None, scale=(1, 1, 1), bottom=True):
        """Truncated cone along local z. bottom=False drops the lower cap (pieces standing on something)."""
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1))
        r = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=seg,
                                  radius1=r1, radius2=r2, depth=depth)
        vs = r["verts"]
        if caps and not bottom:
            kill = [f for f in self._faces_of(vs) if len(f.verts) == seg and all(v.co.z < -depth / 2 + 1e-6 for v in f.verts)]
            bmesh.ops.delete(self.bm, geom=kill, context="FACES_ONLY")
            vs = [v for v in vs if v.is_valid]
        su, sv = uv_m or self.uv_m
        for f in self._faces_of(vs):
            f.normal_update()
            for l in f.loops:
                p = l.vert.co
                a = math.atan2(p.y, p.x)
                if abs(f.normal.z) > 0.9:
                    l[self.uv].uv = (p.x / su, p.y / sv)
                else:
                    l[self.uv].uv = ((a + math.pi) * max(r1, r2) / su, p.z / sv)
        # fix the seam: faces spanning -pi..pi
        for f in self._faces_of(vs):
            us = [l[self.uv].uv[0] for l in f.loops]
            if abs(f.normal.z) < 0.9 and max(us) - min(us) > math.pi * max(r1, r2) / su:
                for l in f.loops:
                    if l[self.uv].uv[0] < math.pi * max(r1, r2) / su:
                        l[self.uv].uv = (l[self.uv].uv[0] + 2 * math.pi * max(r1, r2) / su, l[self.uv].uv[1])
        self._finish_prim(vs, M)
        return vs

    def sphere(self, center, radius, subd=1, scale=(1, 1, 1)):
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subd, radius=radius)
        vs = r["verts"]
        self._planar_uv(self._faces_of(vs))
        self._finish_prim(vs, Matrix.Translation(center) @ Matrix.Diagonal((*scale, 1)))
        return vs

    def uvsphere(self, center, radius, seg=12, rings=8, scale=(1, 1, 1), rot=(0, 0, 0)):
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=radius)
        vs = r["verts"]
        self._planar_uv(self._faces_of(vs))
        self._finish_prim(vs, Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1)))
        return vs

    def bulb(self, center, radius, stretch=1.35, sides=6):
        """Cheap fairy-bulb: bipyramid (2*sides tris)."""
        c = Vector(center)
        top = self.bm.verts.new(c + Vector((0, 0, radius * stretch)))
        bot = self.bm.verts.new(c + Vector((0, 0, -radius * stretch * 1.1)))
        a0 = random.random()
        ring = [self.bm.verts.new(c + Vector((radius * math.cos(a), radius * math.sin(a), 0)))
                for a in [a0 + i * 2 * math.pi / sides for i in range(sides)]]
        fs = []
        for i in range(sides):
            j = (i + 1) % sides
            fs.append(self.bm.faces.new((ring[i], ring[j], top)))
            fs.append(self.bm.faces.new((ring[j], ring[i], bot)))
        self._planar_uv(fs)
        self._finish_prim([top, bot] + ring, Matrix.Identity(4))

    def tube(self, pts, radius, tseg=4, caps=False):
        rings = []
        for i, p in enumerate(pts):
            a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
            t = (Vector(b) - Vector(a)).normalized()
            up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n1 = t.cross(up).normalized(); n2 = t.cross(n1).normalized()
            rings.append([self.bm.verts.new(Vector(p) + radius * (math.cos(2 * math.pi * j / tseg) * n1 + math.sin(2 * math.pi * j / tseg) * n2)) for j in range(tseg)])
        fs = []
        for i in range(len(rings) - 1):
            for j in range(tseg):
                jj = (j + 1) % tseg
                fs.append(self.bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][jj], rings[i][jj])))
        su = self.uv_m[0]
        acc = 0
        for i in range(len(rings) - 1):
            pass
        self._planar_uv(fs)
        self._finish_prim([v for r in rings for v in r], Matrix.Identity(4))

    def raw(self, verts, faces, uvs=None):
        """Add raw geometry (verts in frame space). uvs: per-face list of per-loop uv tuples, or None -> planar."""
        vs = [self.bm.verts.new(Vector(v)) for v in verts]
        fs = []
        for fi, f in enumerate(faces):
            try:
                face = self.bm.faces.new([vs[i] for i in f])
            except ValueError:
                continue
            fs.append((fi, face))
        for fi, face in fs:
            face.normal_update()
            if uvs is not None:
                for l, uv in zip(face.loops, uvs[fi]):
                    l[self.uv].uv = uv
        if uvs is None:
            self._planar_uv([f for _, f in fs])
        self._finish_prim(vs, Matrix.Identity(4))
        return vs

    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def finish(self, coll=None, name=None, smooth=False):
        if not self.bm.faces:
            self.bm.free(); return None
        me = bpy.data.meshes.new(name or self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(name or self.name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        if self.mat: me.materials.append(self.mat)
        if smooth:
            for p in me.polygons: p.use_smooth = True
        return ob


class GeoSet:
    """Dict of Geo per material key, sharing one current frame."""

    def __init__(self, prefix, mats, uvs=None):
        self.prefix = prefix
        self.mats = mats
        self.uvs = uvs or {}
        self.g = {}
        self._frame = Matrix.Identity(4)

    def __getitem__(self, k):
        if k not in self.g:
            self.g[k] = Geo(f"{self.prefix}_{k}", self.mats[k], self.uvs.get(k, (1, 1)))
            self.g[k].frame = self._frame
        return self.g[k]

    def set_frame(self, M):
        self._frame = M
        for g in self.g.values(): g.frame = M

    def finish(self, coll, smooth_keys=()):
        out = {}
        for k, g in self.g.items():
            ob = g.finish(coll, smooth=k in smooth_keys)
            if ob: out[k] = ob
        return out

    def tris(self):
        return sum(g.tris() for g in self.g.values())


# ------------------------------------------------------------------ textures and materials

def tex_dir(area):
    d = os.path.join(REPO, "blender", area, "tex")
    os.makedirs(d, exist_ok=True)
    return d


def make_texture_set(area, name, gen, normal_strength=4.0, force=False):
    """Generate (or reuse cached) colour / roughness / normal PNGs; returns dict of paths."""
    d = tex_dir(area)
    paths = {k: os.path.join(d, f"{name}_{k}.png") for k in ("color", "rough", "normal")}
    if force or os.environ.get("FORCE_TEX") or not all(os.path.exists(p) for p in paths.values()):
        t0 = time.time()
        t = gen()
        TX.save_png(paths["color"], t["color"] ** (1 / 2.2))
        TX.save_png(paths["rough"], t["rough"])
        TX.save_png(paths["normal"], TX.normal_from_height(t["height"], normal_strength))
        log(f"texture {name} generated in {time.time() - t0:.1f}s")
    return paths


def lite_texture_set(paths, size=256, keep=("color", "rough", "normal")):
    """Downsized copies of a texture set for the lite market (cached next to the originals as
    <name>_<key>_<size>.png).  Keys left out of `keep` are dropped (e.g. no normal map on small props)."""
    from PIL import Image
    out = {}
    for k in keep:
        src = paths.get(k)
        if not src:
            continue
        dst = src[:-4] + f"_{size}.png"
        if os.environ.get("FORCE_TEX") or not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            im = Image.open(src)
            im.resize((size, size), Image.LANCZOS).save(dst)
        out[k] = dst
    return out


def load_img(path, noncolor=False, extension="REPEAT"):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return img


def _gltf_output_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g: return g
    g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat")
    return g


def pbr(name, tex=None, color=(0.5, 0.5, 0.5), factor=None, rough=0.6, metal=0.0, normal_strength=1.0,
        emit_color=None, emit_strength=0.0, emit_tex=None, alpha_tex=None, ao_img=None, ao_uv="lightmap",
        vcol=None, coat=0.0, base_tex=None):
    """Principled material from texture paths. factor multiplies the colour texture (exported as
    baseColorFactor). vcol multiplies by a colour attribute (exported as COLOR_0)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N["Principled BSDF"]
    uvn = N.new("ShaderNodeUVMap"); uvn.uv_map = "UVMap"
    bsdf.inputs["Metallic"].default_value = metal
    if coat: bsdf.inputs["Coat Weight"].default_value = coat
    col_out = None
    ctex = (tex or {}).get("color") or base_tex
    if ctex:
        ci = N.new("ShaderNodeTexImage"); ci.image = load_img(ctex)
        L.new(uvn.outputs["UV"], ci.inputs["Vector"])
        col_out = ci.outputs["Color"]
        if alpha_tex is True:   # alpha clip -> glTF alphaMode MASK
            gt = N.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
            L.new(ci.outputs["Alpha"], gt.inputs[0]); L.new(gt.outputs[0], bsdf.inputs["Alpha"])
        if factor:
            mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
            mx.inputs["Factor"].default_value = 1.0
            L.new(col_out, mx.inputs[6]); mx.inputs[7].default_value = (*factor, 1)
            col_out = mx.outputs[2]
    else:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
    if vcol:
        ca = N.new("ShaderNodeVertexColor"); ca.layer_name = vcol
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        if col_out is None:
            mx.inputs[6].default_value = (*color, 1)
        else:
            L.new(col_out, mx.inputs[6])
        L.new(ca.outputs["Color"], mx.inputs[7])
        col_out = mx.outputs[2]
    if col_out is not None:
        L.new(col_out, bsdf.inputs["Base Color"])
    if tex and tex.get("rough"):
        ri = N.new("ShaderNodeTexImage"); ri.image = load_img(tex["rough"], True)
        L.new(uvn.outputs["UV"], ri.inputs["Vector"])
        L.new(ri.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    if tex and tex.get("normal"):
        ni = N.new("ShaderNodeTexImage"); ni.image = load_img(tex["normal"], True)
        L.new(uvn.outputs["UV"], ni.inputs["Vector"])
        nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal_strength
        nm.uv_map = "UVMap"
        L.new(ni.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if emit_tex:
        ei = N.new("ShaderNodeTexImage"); ei.image = load_img(emit_tex)
        L.new(uvn.outputs["UV"], ei.inputs["Vector"])
        L.new(ei.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    elif emit_color:
        bsdf.inputs["Emission Color"].default_value = (*emit_color, 1)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if ao_img is not None:
        g = N.new("ShaderNodeGroup"); g.node_tree = _gltf_output_group()
        u2 = N.new("ShaderNodeUVMap"); u2.uv_map = ao_uv
        ai = N.new("ShaderNodeTexImage"); ai.image = ao_img; ai.extension = "REPEAT"  # may be packed with tiled roughness (shared sampler)
        L.new(u2.outputs["UV"], ai.inputs["Vector"])
        sep = N.new("ShaderNodeSeparateColor")
        L.new(ai.outputs["Color"], sep.inputs["Color"])
        L.new(sep.outputs["Red"], g.inputs["Occlusion"])
        # for Cycles previews: darken base colour slightly by AO as well is NOT done (no lighting in base colour)
    return m


def solid(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, coat=0.0):
    return pbr(name, color=color, rough=rough, metal=metal, emit_color=emit, emit_strength=strength, coat=coat)


# ------------------------------------------------------------------ AO bake

def add_lightmap_uv_planar(ob, x0, y0, size):
    me = ob.data
    uvl = me.uv_layers.new(name="lightmap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            w = ob.matrix_world @ v
            uvl.data[li].uv = ((w.x - x0) / size, (w.y - y0) / size)
    return uvl


def add_lightmap_uv_pack(ob, margin=0.004):
    me = ob.data
    uvl = me.uv_layers.new(name="lightmap")
    me.uv_layers.active = uvl
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    me.uv_layers.active = me.uv_layers["UVMap"]
    return uvl


def lightmap_atlas(objs, reserve_u=0.03, margin=0.0015, angle=66.0, face_filter=None, const_v=None, ramp=None):
    """One shared 'lightmap' UV atlas for several meshes: smart-project them together in
    multi-object edit mode (islands scaled by world area, packed jointly), then squeeze the atlas
    into u < 1 - reserve_u.  The reserved strip on the right is free for constant values (white =
    unoccluded, or a ramp) that meshes outside the bake can point at.

    face_filter(poly) -> bool keeps texels for the faces that need them (large, visible); the others
    point into the strip: at their own per-corner occlusion when `ramp` (ob.name -> per-loop values
    from bake_vertex_ao) is given, else at const_v(poly)."""
    t0 = time.time()
    for o in bpy.context.view_layer.objects: o.select_set(False)
    skipped = {}
    for ob in objs:
        me = ob.data
        uvl = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
        me.uv_layers.active = uvl
        if face_filter:
            keep = np.array([bool(face_filter(p)) for p in me.polygons])
            me.vertices.foreach_set("select", np.zeros(len(me.vertices), bool))
            me.edges.foreach_set("select", np.zeros(len(me.edges), bool))
            me.polygons.foreach_set("select", keep)
            skipped[ob.name] = [(p.index, const_v(p) if const_v else 0.9) for p, k in zip(me.polygons, keep) if not k]
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode="EDIT")
    if not face_filter:
        bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    k = 1.0 - reserve_u
    uc = 1.0 - reserve_u / 2
    n_skip = 0
    for ob in objs:
        me = ob.data
        uvl = me.uv_layers["lightmap"]
        a = np.zeros(len(uvl.data) * 2, np.float32)
        uvl.data.foreach_get("uv", a)
        a[0::2] *= k
        rv = (ramp or {}).get(ob.name)
        for pi, v in skipped.get(ob.name, []):
            p = me.polygons[pi]
            for li in p.loop_indices:
                a[2 * li] = uc; a[2 * li + 1] = min(0.996, max(0.004, rv[li] if rv is not None else v))
            n_skip += 1
        uvl.data.foreach_set("uv", a)
        me.uv_layers.active = me.uv_layers["UVMap"]
        ob.select_set(False)
    log(f"lightmap atlas for {len(objs)} meshes in {time.time() - t0:.1f}s ({n_skip} faces use the ramp)")


def lightmap_const(ob, u, v=0.5):
    """Point every loop's lightmap UV at one texel (for meshes outside the bake)."""
    me = ob.data
    uvl = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
    a = np.zeros(len(uvl.data) * 2, np.float32)
    a[0::2] = u; a[1::2] = v
    uvl.data.foreach_set("uv", a)
    me.uv_layers.active = me.uv_layers["UVMap"]


def lightmap_values(ob, fn, u0, u1):
    """Per-vertex occlusion as lightmap UVs into a vertical ramp stored in the reserved strip:
    u in [u0, u1] (strip centre), v = occlusion value (0..1).  fn(world_co) -> occlusion."""
    me = ob.data
    uvl = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
    uc = (u0 + u1) / 2
    vals = [min(0.995, max(0.005, fn(ob.matrix_world @ v.co))) for v in me.vertices]
    a = np.zeros(len(uvl.data) * 2, np.float32)
    idx = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", idx)
    a[0::2] = uc
    a[1::2] = np.array(vals, np.float32)[idx]
    uvl.data.foreach_set("uv", a)
    me.uv_layers.active = me.uv_layers["UVMap"]


def attach_ao(mat, img, uv="lightmap"):
    """Wire an AO image into the glTF occlusion slot (glTF Material Output group, red channel)."""
    nt = mat.node_tree; N = nt.nodes; L = nt.links
    for n in list(N):
        if n.type == "GROUP" and n.node_tree and n.node_tree.name == "glTF Material Output":
            N.remove(n)
    g = N.new("ShaderNodeGroup"); g.node_tree = _gltf_output_group()
    u2 = N.new("ShaderNodeUVMap"); u2.uv_map = uv
    ai = N.new("ShaderNodeTexImage"); ai.image = img; ai.extension = "EXTEND"
    ai.interpolation = "Linear"
    L.new(u2.outputs["UV"], ai.inputs["Vector"])
    sep = N.new("ShaderNodeSeparateColor")
    L.new(ai.outputs["Color"], sep.inputs["Color"])
    L.new(sep.outputs["Red"], g.inputs["Occlusion"])


def finish_ao_image(img, path, lift=0.25, strip=None, denoise=True):
    """Post-process a baked AO image: light denoise, lift (glTF AO only scales ambient light), and
    fill the reserved strip.  strip = (u0, fill) with fill 'white' or 'ramp'."""
    res_x, res_y = img.size
    px = np.array(img.pixels[:], np.float32).reshape(res_y, res_x, 4)
    ao = px[..., 0].copy()
    if denoise:
        from scipy import ndimage as ndi
        ao = ndi.median_filter(ao, size=3)
        ao = 0.5 * ao + 0.5 * ndi.gaussian_filter(ao, 0.8)
    ao = np.clip(lift + (1 - lift) * ao, 0, 1)
    if strip:
        u0, fill = strip
        c0 = int(u0 * res_x)
        if fill == "white":
            ao[:, c0:] = 1.0
        else:
            ao[:, c0:] = np.linspace(0, 1, res_y)[:, None]
    px[..., 0] = px[..., 1] = px[..., 2] = ao
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path; img.file_format = "PNG"; img.save()
    return img


def use_device(scene=None):
    """Cycles device and thread count from NM_DEVICE / NM_THREADS (defaults: CPU, 2 threads)."""
    scene = scene or bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    dev = os.environ.get("NM_DEVICE", "CPU").upper()
    if dev in ("METAL", "CUDA", "OPTIX", "HIP", "ONEAPI"):
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = dev
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    threads = int(os.environ.get("NM_THREADS", "2"))
    if threads > 0:
        scene.render.threads_mode = "FIXED"; scene.render.threads = threads
    else:
        scene.render.threads_mode = "AUTO"
    return scene


def bake_ao(targets, img_name, res, path, samples=24, distance=3.0, post=True, margin=4):
    """Bake AO for `targets` (objects sharing one 'lightmap' UV atlas) into one image.
    post=False leaves the raw bake for finish_ao_image()."""
    scene = use_device()
    scene.cycles.samples = samples
    bpy.context.scene.world.light_settings.distance = distance
    img = bpy.data.images.new(img_name, res, res)
    img.colorspace_settings.name = "Non-Color"
    temp_nodes = []
    for ob in targets:
        ob.data.uv_layers.active = ob.data.uv_layers["lightmap"]
        for mat in ob.data.materials:
            nt = mat.node_tree
            n = nt.nodes.new("ShaderNodeTexImage"); n.image = img
            u = nt.nodes.new("ShaderNodeUVMap"); u.uv_map = "lightmap"
            nt.links.new(u.outputs["UV"], n.inputs["Vector"])
            nt.nodes.active = n
            temp_nodes.append((nt, n, u))
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for ob in targets: ob.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    t0 = time.time()
    bpy.ops.object.bake(type="AO", margin=margin, use_clear=True)
    log(f"AO bake {img_name} {res}px in {time.time() - t0:.1f}s")
    if post:
        # soften and lift: AO in glTF only affects ambient light
        px = np.array(img.pixels[:]).reshape(res, res, 4)
        px[..., :3] = np.clip(0.25 + 0.75 * px[..., :3], 0, 1)
        img.pixels.foreach_set(px.astype(np.float32).ravel())
        img.filepath_raw = path; img.file_format = "PNG"; img.save()
    for nt, n, u in temp_nodes:
        nt.nodes.remove(n); nt.nodes.remove(u)
    for ob in targets:
        ob.data.uv_layers.active = ob.data.uv_layers["UVMap"]
    return img


def bake_vertex_ao(objs, samples=32, distance=1.0, lift=0.25, gamma=1.0):
    """Bake AO per face corner (Cycles, colour-attribute target).  Returns {ob.name: per-loop
    occlusion, lifted (glTF occlusion only scales ambient light)}."""
    scene = use_device()
    scene.cycles.samples = samples
    scene.world.light_settings.distance = distance
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for ob in objs:
        me = ob.data
        if "ao_bake" in me.color_attributes:
            me.color_attributes.remove(me.color_attributes["ao_bake"])
        a = me.color_attributes.new("ao_bake", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = a
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    t0 = time.time()
    bpy.ops.object.bake(type="AO", target="VERTEX_COLORS", use_clear=True)
    log(f"vertex AO for {len(objs)} meshes in {time.time() - t0:.1f}s")
    out = {}
    for ob in objs:
        me = ob.data
        a = me.color_attributes["ao_bake"]
        col = np.zeros(len(a.data) * 4, np.float32)
        a.data.foreach_get("color", col)
        ao = np.clip(col[0::4], 0, 1) ** gamma
        out[ob.name] = np.clip(lift + (1 - lift) * ao, 0.004, 0.996)
        me.color_attributes.remove(a)
        ob.select_set(False)
    return out


def ramp_uv(ob, ao, u0, u1, v0=0.0, v1=1.0):
    """Every loop's 'lightmap' UV points into the ramp strip [u0, u1] at its occlusion value
    (the ramp runs from v0 (black) to v1 (white))."""
    me = ob.data
    uvl = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
    uv = np.zeros(len(uvl.data) * 2, np.float32)
    uv[0::2] = (u0 + u1) / 2; uv[1::2] = v0 + (v1 - v0) * ao
    uvl.data.foreach_set("uv", uv)
    me.uv_layers.active = me.uv_layers["UVMap"]


def vertex_ao_to_ramp(objs, u0, u1, samples=32, distance=1.0, lift=0.25, gamma=1.0):
    """Occlusion for small or numerous parts (timbers, frames, needles, baubles) that an atlas would
    waste texels on: bake AO per face corner, then store each corner's value as a 'lightmap' UV
    pointing into the vertical ramp kept in the atlas's reserved strip [u0, u1] (fill it with
    finish_ao_image(strip=(u0, 'ramp'))).  The glTF occlusion texture then returns the baked value,
    interpolated across each face."""
    vals = bake_vertex_ao(objs, samples, distance, lift, gamma)
    for ob in objs:
        ramp_uv(ob, vals[ob.name], u0, u1)


# ------------------------------------------------------------------ export

def empty(name, loc, coll, size=0.3, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.location = loc
    coll.objects.link(e)
    if parent: e.parent = parent
    return e


def count_tris(objs):
    t = 0
    for o in objs:
        if o.type == "MESH":
            o.data.calc_loop_triangles(); t += len(o.data.loop_triangles)
    return t


def export_glb(objs, path):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_image_format="AUTO", export_cameras=False,
                              export_lights=False, export_extras=False)
    log("exported", path, os.path.getsize(path))
    return path


OPT_FLAGS = ["--compress", "meshopt", "--texture-compress", "webp",
             # keep light_/cam_ empties, named bulbs_/snow_ nodes and material names intact:
             "--join", "false", "--flatten", "false", "--prune", "false", "--palette", "false",
             "--instance", "false",
             # the meshoptimizer simplifier collapsed the plaza's camber, relief and street UVs
             # (round 1: 187 triangles of cobbles survived); geometry is budgeted by hand instead
             "--simplify", "false"]


def optimize(raw, out, tex_size=1024):
    cmd = ["gltf-transform", "optimize", raw, out, *OPT_FLAGS, "--texture-size", str(tex_size)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log(r.stdout[-2000:], r.stderr[-2000:])
        raise RuntimeError("optimize failed")
    log("optimized", out, os.path.getsize(out))
    return out


def glb_stats(path):
    """Triangles, node names, material names of a glb (reads the JSON chunk)."""
    import struct
    with open(path, "rb") as f:
        b = f.read()
    ln = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + ln])
    tris = 0
    mesh_tris = []
    for m in j.get("meshes", []):
        t = 0
        for p in m["primitives"]:
            if "indices" in p:
                t += j["accessors"][p["indices"]]["count"] // 3
            else:
                t += j["accessors"][p["attributes"]["POSITION"]]["count"] // 3
        mesh_tris.append(t)
    for n in j.get("nodes", []):
        if "mesh" in n:
            tris += mesh_tris[n["mesh"]]
    return dict(tris=tris, size=len(b), nodes=[n.get("name", "") for n in j.get("nodes", [])],
                materials=[m.get("name", "") for m in j.get("materials", [])])


# ------------------------------------------------------------------ preview rendering

def setup_cycles(samples=48, res=(1280, 720)):
    s = use_device()
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    try:
        s.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    s.cycles.max_bounces = 6
    s.cycles.light_sampling_threshold = 0.01
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Punchy"
    s.view_settings.exposure = 0.0
    return s


def night_world(strength=1.0, zenith=(0.004, 0.008, 0.028), horizon=(0.03, 0.035, 0.06)):
    s = bpy.context.scene
    w = bpy.data.worlds.new("Night"); s.world = w; w.use_nodes = True
    nt = w.node_tree; N = nt.nodes; L = nt.links
    bg = N["Background"]
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[0].color = (*horizon, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (*zenith, 1)
    L.new(sep.outputs["Z"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    return w


def add_light(name, kind, loc, energy, color, size=0.2, rot=(0, 0, 0), coll=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == "AREA": ld.size = size
    elif kind in ("POINT", "SPOT"): ld.shadow_soft_size = size
    elif kind == "SUN": ld.angle = math.radians(1.0)
    ob = bpy.data.objects.new(name, ld); ob.location = loc; ob.rotation_euler = rot
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def camera(loc, target, lens=35, coll=None, name="PreviewCam"):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 800
    cam = bpy.data.objects.new(name, cd)
    (coll or bpy.context.scene.collection).objects.link(cam)
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def compositor_fog_glare(fog_color=(0.035, 0.04, 0.07), near=25, far=160, fog_amount=0.55, glare=True):
    s = bpy.context.scene
    s.use_nodes = True
    s.view_layers[0].use_pass_z = True
    nt = s.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    rl = N.new("CompositorNodeRLayers")
    comp = N.new("CompositorNodeComposite")
    mr = N.new("CompositorNodeMapRange")
    mr.inputs[1].default_value = near; mr.inputs[2].default_value = far
    mr.inputs[3].default_value = 0; mr.inputs[4].default_value = fog_amount
    mr.use_clamp = True
    L.new(rl.outputs["Depth"], mr.inputs[0])
    mix = N.new("CompositorNodeMixRGB")
    L.new(mr.outputs[0], mix.inputs[0])
    img_out = rl.outputs["Image"]
    if glare:
        gl = N.new("CompositorNodeGlare"); gl.glare_type = "FOG_GLOW"; gl.quality = "HIGH"
        gl.threshold = 1.2; gl.size = 7; gl.mix = -0.55
        L.new(img_out, gl.inputs["Image"]); img_out = gl.outputs["Image"]
    L.new(img_out, mix.inputs[1])
    mix.inputs[2].default_value = (*fog_color, 1)
    L.new(mix.outputs[0], comp.inputs["Image"])


def render(path, samples=None, review_width=1280):
    """Render the scene camera. A .jpg path gets a full-size PNG next to the build output
    (blender/square/out/renders/) and a review JPEG at most `review_width` px wide."""
    s = bpy.context.scene
    if samples: s.cycles.samples = samples
    jpg = path.lower().endswith((".jpg", ".jpeg"))
    png = path
    if jpg:
        rd = os.path.join(REPO, "blender", "square", "out", "renders")
        os.makedirs(rd, exist_ok=True)
        png = os.path.join(rd, os.path.splitext(os.path.basename(path))[0] + ".png")
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = png
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    log(f"rendered {png} in {time.time() - t0:.1f}s")
    if jpg:
        from PIL import Image
        im = Image.open(png).convert("RGB")
        if im.width > review_width:
            im = im.resize((review_width, round(im.height * review_width / im.width)), Image.LANCZOS)
        im.save(path, quality=88)
        log("review jpeg", path)
