"""Build a German Christmas-market Gluehwein stall, render a preview, bake, export GLB.
Run: venv/bin/python build_stall.py
"""
import bpy, bmesh, math, random, time, os
from mathutils import Matrix, Vector, Euler

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
TEX = os.path.join(BASE, "tex")
os.makedirs(OUT, exist_ok=True); os.makedirs(TEX, exist_ok=True)
random.seed(7)
T0 = time.time()

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
stall = bpy.data.collections.new("Stall"); scene.collection.children.link(stall)
env = bpy.data.collections.new("Env"); scene.collection.children.link(env)

# ---------------------------------------------------------------- helpers
class Builder:
    """Accumulates boxes/primitives into one bmesh with a per-part random colour attribute."""
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("partvar")

    def _tag(self, verts, val=None):
        v = random.random() if val is None else val
        faces = set()
        for vert in verts:
            faces.update(vert.link_faces)
        for f in faces:
            for l in f.loops:
                l[self.col] = (v, v, v, 1.0)

    def box(self, center, size, rot=(0, 0, 0), jitter=0.0):
        sx, sy, sz = size
        if jitter:
            sx *= 1 + random.uniform(-jitter, jitter)
            sz *= 1 + random.uniform(-jitter * 0.3, jitter * 0.3)
        M = (Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal((sx, sy, sz, 1)))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._tag(r["verts"])

    def matrix_box(self, M):
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._tag(r["verts"])

    def cyl(self, center, r1, r2, depth, seg=24, rot=(0, 0, 0), caps=True):
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        r = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=seg,
                                  radius1=r1, radius2=r2, depth=depth, matrix=M)
        self._tag(r["verts"])

    def sphere(self, center, radius, subd=2):
        M = Matrix.Translation(center)
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subd, radius=radius, matrix=M)
        self._tag(r["verts"])

    def uvsphere(self, center, radius, seg=16, rings=10, scale=(1, 1, 1)):
        M = Matrix.Translation(center) @ Matrix.Diagonal((*scale, 1))
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=radius, matrix=M)
        self._tag(r["verts"])

    def torus(self, center, R, r, seg=20, tseg=10, rot=(0, 0, 0), arc=2 * math.pi):
        M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        rings = []
        closed = abs(arc - 2 * math.pi) < 1e-6
        n = seg if closed else seg + 1
        for i in range(n):
            a = arc * i / seg
            ring = []
            for j in range(tseg):
                b = 2 * math.pi * j / tseg
                p = Vector(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
                ring.append(self.bm.verts.new(M @ p))
            rings.append(ring)
        pairs = [(i, (i + 1) % n) for i in range(n if closed else n - 1)]
        new = []
        for i, k in pairs:
            for j in range(tseg):
                jj = (j + 1) % tseg
                new.append(self.bm.faces.new((rings[i][j], rings[k][j], rings[k][jj], rings[i][jj])))
        self._tag([v for ring in rings for v in ring])

    def tube(self, pts, radius, tseg=6):
        """Simple tube along a polyline (for wires)."""
        rings = []
        for i, p in enumerate(pts):
            a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
            t = (b - a).normalized()
            up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n1 = t.cross(up).normalized(); n2 = t.cross(n1).normalized()
            rings.append([self.bm.verts.new(p + radius * (math.cos(2 * math.pi * j / tseg) * n1 + math.sin(2 * math.pi * j / tseg) * n2)) for j in range(tseg)])
        for i in range(len(rings) - 1):
            for j in range(tseg):
                jj = (j + 1) % tseg
                self.bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][jj], rings[i][jj]))
        self._tag([v for r in rings for v in r])

    def finish(self, mat, bevel=0.0, smooth=False, coll=stall):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        me.materials.append(mat)
        if bevel:
            m = ob.modifiers.new("Bevel", "BEVEL")
            m.width = bevel; m.segments = 2; m.limit_method = 'ANGLE'
            m.harden_normals = False
        if smooth:
            for p in me.polygons: p.use_smooth = True
        return ob


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    newme = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = newme
    newme.name = old.name
    bpy.data.meshes.remove(old)


# ---------------------------------------------------------------- materials
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes["Principled BSDF"], nt.links


def wood_material(name, c_light, c_dark, rough=0.7, scale=(6, 6, 0.5)):
    m, nt, bsdf, L = node_mat(name)
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = scale
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    # grain: stretched noise
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4.0
    nz.inputs["Detail"].default_value = 10; nz.inputs["Distortion"].default_value = 1.5
    L.new(mp.outputs["Vector"], nz.inputs["Vector"])
    # per-plank variation from colour attribute
    at = N.new("ShaderNodeVertexColor"); at.layer_name = "partvar"
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c_dark, 1)
    ramp.color_ramp.elements[1].color = (*c_light, 1)
    L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    hsv = N.new("ShaderNodeHueSaturation")
    L.new(ramp.outputs["Color"], hsv.inputs["Color"])
    mr = N.new("ShaderNodeMapRange")  # attribute 0..1 -> value 0.75..1.2
    mr.inputs["To Min"].default_value = 0.72; mr.inputs["To Max"].default_value = 1.18
    L.new(at.outputs["Color"], mr.inputs["Value"])
    L.new(mr.outputs["Result"], hsv.inputs["Value"])
    L.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    # roughness variation
    rr = N.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.15; rr.inputs["To Max"].default_value = rough + 0.15
    L.new(nz.outputs["Fac"], rr.inputs["Value"]); L.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    # bump
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.01
    L.new(nz.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def simple_mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, coat=0.0):
    m, nt, bsdf, L = node_mat(name)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if coat: bsdf.inputs["Coat Weight"].default_value = coat
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return m

M_WOOD = wood_material("Wood", (0.42, 0.25, 0.13), (0.16, 0.08, 0.035), 0.7)
M_ROOF = wood_material("Shingles", (0.30, 0.17, 0.09), (0.08, 0.045, 0.025), 0.8, scale=(10, 10, 10))
M_BULB = simple_mat("Bulb", (1.0, 0.8, 0.5), 0.2, emit=(1.0, 0.62, 0.28), strength=25.0)
M_METAL = simple_mat("DarkMetal", (0.03, 0.03, 0.03), 0.4, metal=0.8)
M_RED = simple_mat("OrnamentRed", (0.55, 0.02, 0.03), 0.2, coat=0.8)
M_GOLD = simple_mat("OrnamentGold", (0.9, 0.62, 0.2), 0.25, metal=1.0)
M_GREEN = simple_mat("Fir", (0.02, 0.12, 0.04), 0.6)
M_MUG = simple_mat("MugCeramic", (0.5, 0.04, 0.05), 0.25, coat=0.5)
M_WINE = simple_mat("Gluehwein", (0.12, 0.005, 0.01), 0.05)
M_PAINT = simple_mat("SignPaint", (0.9, 0.82, 0.62), 0.5)
M_COPPER = simple_mat("Copper", (0.85, 0.45, 0.25), 0.3, metal=1.0)
M_SNOW = simple_mat("Snow", (0.8, 0.85, 0.95), 0.6)

# ---------------------------------------------------------------- dimensions
W, D = 3.0, 2.0          # footprint
WALL_H = 2.2
RIDGE_Z = 3.05
EAVE_OUT = 0.3           # roof overhang front/back
GABLE_OUT = 0.2
x0, x1 = -W / 2, W / 2
yF, yB = -D / 2, D / 2

wood = Builder("Stall_Wood")

# floor platform: planks along X
py = yF
while py < yB - 1e-6:
    pw = 0.14
    wood.box((0, py + pw / 2, 0.06), (W + 0.1, pw - 0.006, 0.04), jitter=0.0)
    py += pw
for sx in (x0 + 0.1, 0, x1 - 0.1):  # joists
    wood.box((sx, 0, 0.02), (0.08, D, 0.04))

def plank_wall_vertical(xa, xb, y, h_fn, z0=0.08, pw=0.13, th=0.035, axis='x'):
    """vertical planks between xa..xb at depth y. h_fn(pos)->top z"""
    p = xa
    while p < xb - 1e-6:
        w = min(pw * random.uniform(0.85, 1.15), xb - p)
        c = p + w / 2
        top = h_fn(c) + random.uniform(-0.01, 0.01)
        h = top - z0
        rz = random.uniform(-0.004, 0.004)
        if axis == 'x':
            wood.box((c, y + random.uniform(-0.004, 0.004), z0 + h / 2), (w - 0.006, th, h), rot=(0, rz, 0))
        else:
            wood.box((y + random.uniform(-0.004, 0.004), c, z0 + h / 2), (th, w - 0.006, h), rot=(rz, 0, 0))
        p += w

# back wall
plank_wall_vertical(x0, x1, yB - 0.02, lambda c: WALL_H)
rise = RIDGE_Z - WALL_H
gable = lambda c: WALL_H + rise * (1 - abs(c) / (D / 2 + EAVE_OUT)) - 0.08
# side walls with gable tops
for sx in (x0 + 0.02, x1 - 0.02):
    plank_wall_vertical(yF, yB, sx, gable, axis='y')
# front lower wall (below counter)
plank_wall_vertical(x0, x1, yF + 0.02, lambda c: 1.0)
# horizontal battens on front lower wall
for z in (0.25, 0.8):
    wood.box((0, yF - 0.01, z), (W - 0.1, 0.03, 0.09))
# corner posts
for sx in (x0 + 0.06, x1 - 0.06):
    for sy in (yF + 0.06, yB - 0.06):
        wood.box((sx, sy, WALL_H / 2 + 0.04), (0.12, 0.12, WALL_H))
# front header beam + top plates
wood.box((0, yF + 0.02, WALL_H - 0.08), (W + 0.05, 0.1, 0.16))
wood.box((0, yB - 0.02, WALL_H - 0.08), (W + 0.05, 0.1, 0.16))
# counter: thick planks with overhang, plus brackets
for i, cy in enumerate((yF - 0.12, yF + 0.02, yF + 0.16)):
    wood.box((0, cy, 1.03), (W - 0.02, 0.135, 0.05), jitter=0.0)
for sx in (-1.2, -0.4, 0.4, 1.2):
    wood.box((sx, yF - 0.1, 0.93), (0.05, 0.16, 0.16), rot=(math.radians(0), 0, 0))
# back shelf with brackets
wood.box((0, yB - 0.2, 1.55), (W - 0.2, 0.3, 0.035))
wood.box((0, yB - 0.2, 1.15), (W - 0.2, 0.3, 0.035))
# sign board on front header
wood.box((0, yF - 0.05, 0.55), (1.6, 0.04, 0.34))
# roof structure: rafters and ridge beam (visible from underneath)
wood.box((0, 0, RIDGE_Z - 0.06), (W + 2 * GABLE_OUT, 0.08, 0.14))
roof_ang = math.atan2(rise, D / 2 + EAVE_OUT)
L_slope = (D / 2 + EAVE_OUT) / math.cos(roof_ang)
for side in (-1, 1):
    for rx in [x0 - GABLE_OUT + 0.05 + i * (W + 2 * GABLE_OUT - 0.1) / 6 for i in range(7)]:
        mid = Vector((rx, side * (D / 2 + EAVE_OUT) / 2, (WALL_H + RIDGE_Z) / 2 - 0.1))
        wood.box(mid, (0.06, L_slope, 0.1), rot=(-side * roof_ang, 0, 0))
    # roof deck boards (under the shingles)
    nb = 12
    for i in range(nb):
        s = (i + 0.5) / nb * L_slope
        yy = side * ((D / 2 + EAVE_OUT) - s * math.cos(roof_ang))
        zz = WALL_H + s * math.sin(roof_ang) - 0.02
        wood.box((0, yy, zz), (W + 2 * GABLE_OUT, L_slope / nb - 0.004, 0.02), rot=(-side * roof_ang, 0, 0))
    # barge boards on gable ends
    for gx in (x0 - GABLE_OUT, x1 + GABLE_OUT):
        mid = Vector((gx, side * (D / 2 + EAVE_OUT) / 2, (WALL_H + RIDGE_Z) / 2 + 0.03))
        wood.box(mid, (0.035, L_slope + 0.05, 0.18), rot=(-side * roof_ang, 0, 0))
    # fascia along eave
    wood.box((0, side * (D / 2 + EAVE_OUT), WALL_H + 0.0), (W + 2 * GABLE_OUT, 0.035, 0.14), rot=(-side * roof_ang * 0.3, 0, 0))

wood_ob = wood.finish(M_WOOD, bevel=0.006)

# ---------------------------------------------------------------- shingles
sh = Builder("Stall_Shingles")
SH_W, SH_L, SH_T, EXPO = 0.16, 0.26, 0.014, 0.115
for side in (-1, 1):
    # local frame for this slope
    down = Vector((0, side * math.cos(roof_ang), -math.sin(roof_ang)))  # towards eave
    nrm = Vector((0, side * math.sin(roof_ang), math.cos(roof_ang)))
    eave_pt = Vector((0, side * (D / 2 + EAVE_OUT + 0.04), WALL_H + 0.005))
    rows = int((L_slope + 0.04) / EXPO)
    for r in range(rows):
        s = r * EXPO                       # distance up-slope from eave to shingle bottom edge
        centre_line = eave_pt - down * (s + SH_L / 2)
        offset = (SH_W / 2) * (r % 2)
        x = x0 - GABLE_OUT - 0.02 - offset
        while x < x1 + GABLE_OUT + 0.02:
            w = SH_W * random.uniform(0.75, 1.25)
            w = min(w, x1 + GABLE_OUT + 0.02 - x)
            if w < 0.04: break
            c = centre_line + Vector((x + w / 2, 0, 0)) + nrm * (0.012 + SH_T / 2 + 0.006 * random.random())
            # rotation: align to slope, tilt bottom edge up a bit, small random yaw
            ax_x = Vector((1, 0, 0)); ax_y = -down; ax_z = nrm
            basis = Matrix((ax_x, ax_y, ax_z)).transposed().to_4x4()
            jitter = Euler((math.radians(random.uniform(-3, -1)), math.radians(random.uniform(-1.5, 1.5)),
                            math.radians(random.uniform(-2.5, 2.5)))).to_matrix().to_4x4()
            M = Matrix.Translation(c) @ basis @ jitter @ Matrix.Diagonal((w - 0.008, SH_L, SH_T * random.uniform(0.85, 1.2), 1))
            sh.matrix_box(M)
            x += w
# ridge cap boards
for side in (-1, 1):
    wood_cap = Matrix.Translation((0, side * 0.06, RIDGE_Z + 0.05)) @ Euler((-side * roof_ang, 0, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((W + 2 * GABLE_OUT + 0.1, 0.16, 0.03, 1))
    sh.matrix_box(wood_cap)
sh_ob = sh.finish(M_ROOF, bevel=0.003)

# ---------------------------------------------------------------- light bulbs along both eaves + wire
bulbs = Builder("Stall_Bulbs")
sockets = Builder("Stall_Wires")
for side in (-1,):
    ye = side * (D / 2 + EAVE_OUT + 0.02)
    ze = WALL_H - 0.08
    n = 17
    xs = [x0 - GABLE_OUT + 0.1 + i * (W + 2 * GABLE_OUT - 0.2) / (n - 1) for i in range(n)]
    wire = []
    for i in range(n - 1):
        for k in range(8):
            t = k / 8
            xx = xs[i] + (xs[i + 1] - xs[i]) * t
            wire.append(Vector((xx, ye, ze - 0.06 * math.sin(math.pi * t))))
    wire.append(Vector((xs[-1], ye, ze)))
    sockets.tube(wire, 0.004)
    for xx in xs:
        sockets.cyl(Vector((xx, ye, ze - 0.03)), 0.014, 0.012, 0.045, seg=12)
        bulbs.uvsphere(Vector((xx, ye, ze - 0.085)), 0.03, seg=16, rings=10, scale=(1, 1, 1.35))
# interior hanging bulbs
for xx in (-0.8, 0.0, 0.8):
    top = Vector((xx, 0.1, RIDGE_Z - 0.13)); bot = Vector((xx, 0.1, 2.0))
    sockets.tube([top, bot], 0.004)
    sockets.cyl(bot + Vector((0, 0, -0.02)), 0.02, 0.018, 0.05, seg=12)
    bulbs.uvsphere(bot + Vector((0, 0, -0.09)), 0.045, seg=16, rings=10, scale=(1, 1, 1.3))
bulb_ob = bulbs.finish(M_BULB, smooth=True)
wire_ob = sockets.finish(M_METAL, smooth=True)

# ---------------------------------------------------------------- garland: fir rope + ornament beads under the counter-front header
fir = Builder("Stall_Garland_Fir"); red = Builder("Stall_Garland_Red"); gold = Builder("Stall_Garland_Gold")
yg = yF - 0.08
anchors = [x0 + 0.05, -0.5, 0.5, x1 - 0.05]
bead = 0
for a, b in zip(anchors[:-1], anchors[1:]):
    steps = 34
    pts = []
    for k in range(steps + 1):
        t = k / steps
        xx = a + (b - a) * t
        zz = WALL_H - 0.12 - 0.28 * math.sin(math.pi * t)
        pts.append(Vector((xx, yg, zz)))
    # fir rope: many small elongated needles clusters around the curve
    for p in pts:
        for j in range(5):
            off = Vector((random.uniform(-0.02, 0.02), random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03)))
            fir.uvsphere(p + off, 0.028, seg=8, rings=5, scale=(1.6, 0.7, 0.7))
    for k, p in enumerate(pts):
        if k % 2 == 0:
            tgt = red if bead % 2 == 0 else gold
            tgt.sphere(p + Vector((0, -0.045, -0.02)), random.uniform(0.018, 0.026), subd=2)
            bead += 1
    # bow-like baubles at anchors
    red.sphere(Vector((a, yg - 0.05, WALL_H - 0.18)), 0.045, subd=3)
fir.finish(M_GREEN, smooth=True); red.finish(M_RED, smooth=True); gold.finish(M_GOLD, smooth=True)

# ---------------------------------------------------------------- mugs on counter
mugs = Builder("Stall_Mugs"); wine = Builder("Stall_Wine")
for i, (mx, my) in enumerate([(-1.05, -1.1), (-0.8, -1.05), (-0.55, -1.12), (0.55, -1.08), (0.85, -1.1)]):
    zb = 1.055
    h = 0.11; r = 0.042
    c = Vector((mx, my, zb + h / 2))
    # body: outer wall, slight bulge via 3 stacked cones
    mugs.cyl(c + Vector((0, 0, -h / 4)), r * 0.92, r, h / 2, seg=28)
    mugs.cyl(c + Vector((0, 0, h / 4)), r, r * 0.95, h / 2, seg=28, caps=True)
    ang = random.uniform(0, 2 * math.pi)
    hc = c + Vector((math.cos(ang) * r * 1.05, math.sin(ang) * r * 1.05, 0))
    mugs.torus(hc, 0.028, 0.007, seg=16, tseg=8, rot=(math.pi / 2, 0, ang))
    wine.cyl(c + Vector((0, 0, h / 2 + 0.001)), r * 0.86, r * 0.86, 0.004, seg=28)
mugs.finish(M_MUG, smooth=True); wine.finish(M_WINE, smooth=True)

# big copper Gluehwein pot with lid + ladle handle on the counter
pot = Builder("Stall_Pot")
pot.cyl(Vector((0.05, -0.85, 1.055 + 0.15)), 0.2, 0.22, 0.3, seg=40)
pot.cyl(Vector((0.05, -0.85, 1.055 + 0.31)), 0.23, 0.08, 0.04, seg=40)
pot.uvsphere(Vector((0.05, -0.85, 1.055 + 0.345)), 0.025, seg=12, rings=8)
for sgn in (-1, 1):
    pot.torus(Vector((0.05 + sgn * 0.225, -0.85, 1.055 + 0.25)), 0.035, 0.008, seg=16, tseg=8, rot=(math.pi / 2, 0, 0))
pot.finish(M_COPPER, smooth=True)

# ---------------------------------------------------------------- sign text
cu = bpy.data.curves.new("SignText", "FONT"); cu.body = "Glühwein"
cu.size = 0.22; cu.extrude = 0.008; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
tob = bpy.data.objects.new("SignTextTmp", cu); stall.objects.link(tob)
tob.location = (0, yF - 0.075, 0.55); tob.rotation_euler = (math.pi / 2, 0, 0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
tme = bpy.data.meshes.new_from_object(tob.evaluated_get(dg))
sign = bpy.data.objects.new("Stall_SignText", tme); stall.objects.link(sign)
sign.matrix_world = tob.matrix_world.copy()
bpy.data.objects.remove(tob)
tme.materials.clear(); tme.materials.append(M_PAINT)

# apply bevels
for ob in list(stall.objects):
    if ob.modifiers: apply_modifiers(ob)

# ---------------------------------------------------------------- environment (render only)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
ground = bpy.context.active_object; ground.name = "Ground"
for c in ground.users_collection: c.objects.unlink(ground)
env.objects.link(ground); ground.data.materials.append(M_SNOW)

world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.006, 0.012, 0.04, 1); bg.inputs["Strength"].default_value = 1.0

def add_light(name, kind, loc, energy, color, size=0.3, rot=(0, 0, 0)):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == 'AREA': ld.size = size
    elif kind == 'POINT': ld.shadow_soft_size = size
    ob = bpy.data.objects.new(name, ld); ob.location = loc; ob.rotation_euler = rot
    env.objects.link(ob); return ob

add_light("InteriorWarm", 'AREA', (0, 0.1, 2.6), 350, (1.0, 0.6, 0.3), size=2.0)
add_light("CounterWarm", 'POINT', (0, -0.4, 1.6), 120, (1.0, 0.55, 0.25), size=0.3)
add_light("Moon", 'SUN', (0, 0, 10), 0.15, (0.6, 0.7, 1.0), rot=(math.radians(50), 0, math.radians(-30)))
add_light("FrontFill", 'POINT', (0, -2.2, 2.0), 60, (1.0, 0.65, 0.35), size=0.5)

cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 32
cam = bpy.data.objects.new("Cam", cam_d); env.objects.link(cam); scene.camera = cam
cam.location = (-3.4, -5.6, 1.9)
direction = Vector((0.1, 0, 1.45)) - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- render
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
try:
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception as e:
    print("OIDN not available:", e)
scene.cycles.max_bounces = 6
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
scene.render.threads_mode = 'AUTO'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Punchy'
scene.render.filepath = os.path.join(OUT, "preview.png")
scene.render.image_settings.file_format = 'PNG'
print(f"build done in {time.time()-T0:.1f}s")
if not os.environ.get("SKIP_RENDER"):
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_TIME {time.time()-t:.1f}s")

# ---------------------------------------------------------------- bake procedural materials to images
def uv_unwrap(ob):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')

def bake_object(ob, src_mat, res):
    t = time.time()
    uv_unwrap(ob)
    nt = src_mat.node_tree
    imgs = {}
    scene.cycles.samples = 4
    scene.render.bake.margin = 6
    for kind, colorspace in (("DIFFUSE", "sRGB"), ("ROUGHNESS", "Non-Color"), ("NORMAL", "Non-Color")):
        img = bpy.data.images.new(f"{ob.name}_{kind.lower()}", res, res)
        img.colorspace_settings.name = colorspace
        node = nt.nodes.new("ShaderNodeTexImage"); node.image = img
        nt.nodes.active = node
        for o in bpy.context.view_layer.objects: o.select_set(False)
        ob.select_set(True); bpy.context.view_layer.objects.active = ob
        kw = dict(type=kind, margin=6, use_clear=True)
        if kind == "DIFFUSE":
            kw["pass_filter"] = {'COLOR'}
        if kind == "NORMAL":
            kw["normal_space"] = 'TANGENT'
        bpy.ops.object.bake(**kw)
        img.filepath_raw = os.path.join(TEX, f"{img.name}.png"); img.file_format = 'PNG'; img.save()
        nt.nodes.remove(node)
        imgs[kind] = img
    # baked material
    m, bnt, bsdf, L = node_mat(src_mat.name + "_Baked")
    N = bnt.nodes
    c = N.new("ShaderNodeTexImage"); c.image = imgs["DIFFUSE"]
    r = N.new("ShaderNodeTexImage"); r.image = imgs["ROUGHNESS"]
    n = N.new("ShaderNodeTexImage"); n.image = imgs["NORMAL"]
    nm = N.new("ShaderNodeNormalMap")
    L.new(c.outputs["Color"], bsdf.inputs["Base Color"])
    L.new(r.outputs["Color"], bsdf.inputs["Roughness"])
    L.new(n.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    ob.data.materials.clear(); ob.data.materials.append(m)
    # drop the colour attribute so glTF does not export it as COLOR_0 (would multiply base colour in three.js)
    for a in list(ob.data.color_attributes): ob.data.color_attributes.remove(a)
    print(f"BAKED {ob.name} in {time.time()-t:.1f}s")

bake_object(wood_ob, M_WOOD, 2048)
bake_object(sh_ob, M_ROOF, 2048)
# strip partvar colour attribute from all other stall meshes too
for ob in stall.objects:
    if ob.type == 'MESH':
        for a in list(ob.data.color_attributes): ob.data.color_attributes.remove(a)

# ---------------------------------------------------------------- export glb
for o in bpy.context.view_layer.objects: o.select_set(False)
for o in stall.objects: o.select_set(True)
tris = 0
for o in stall.objects:
    o.data.calc_loop_triangles(); tris += len(o.data.loop_triangles)
print("TRIANGLES", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stall.blend"))
glb = os.path.join(OUT, "gluehwein_stall.glb")
common = dict(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
              export_image_format='JPEG', export_jpeg_quality=85, export_yup=True)
try:
    bpy.ops.export_scene.gltf(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, **common)
    print("DRACO yes")
except Exception as e:
    print("Draco failed, plain export:", e)
    bpy.ops.export_scene.gltf(**common)
glb2 = os.path.join(OUT, "gluehwein_stall_nodraco.glb")
common["filepath"] = glb2
bpy.ops.export_scene.gltf(**common)
print("GLB_SIZE", os.path.getsize(glb), "NODRACO", os.path.getsize(glb2))
print(f"TOTAL {time.time()-T0:.1f}s")
