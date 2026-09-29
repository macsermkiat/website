"""Skeleton, pose maths and clip baking for the organizer's figures.

Conventions (Blender, Z up): the figure faces -Y, its left side is +X. Bone names use .L/.R.
A pose is a dict {bone: Quaternion} of rotations in *armature rest axes* about the bone's head,
relative to the parent, plus "_root": Vector, a translation of the hips. With that convention:
  +X rotation leans the torso forward, swings a hanging limb backward (knee bend = +X on the shin,
  elbow flex = -X on the forearm, thigh forward = -X); +Z turns toward the figure's left;
  +Y tilts an upright bone toward the figure's left (abducts the right arm, adducts the left).
"""
import math

import bpy
from mathutils import Vector, Matrix, Quaternion, Euler

BONES = [
    # name, head joint, tail joint, parent
    ("hips", "pelvis", "waist", None),
    ("spine", "waist", "chest", "hips"),
    ("chest", "chest", "neck", "spine"),
    ("neck", "neck", "head", "chest"),
    ("head", "head", "crown", "neck"),
]
for s in "LR":
    BONES += [
        (f"shoulder.{s}", f"clav.{s}", f"shoulder.{s}", "chest"),
        (f"upperarm.{s}", f"shoulder.{s}", f"elbow.{s}", f"shoulder.{s}"),
        (f"forearm.{s}", f"elbow.{s}", f"wrist.{s}", f"upperarm.{s}"),
        (f"hand.{s}", f"wrist.{s}", f"fingers.{s}", f"forearm.{s}"),
        (f"thigh.{s}", f"hip.{s}", f"knee.{s}", "hips"),
        (f"shin.{s}", f"knee.{s}", f"ankle.{s}", f"thigh.{s}"),
        (f"foot.{s}", f"ankle.{s}", f"toe.{s}", f"shin.{s}"),
    ]
# the mug rides on its own bone so each clip can show it (scale 1) or hide it (scale ~0)
BONES.append(("mug", "mug0", "mug1", "hand.R"))
PARENT = {b[0]: b[3] for b in BONES}
ORDER = [b[0] for b in BONES]


def Q(x=0.0, y=0.0, z=0.0):
    """Rotation from XYZ Euler angles in radians (armature axes)."""
    return Euler((x, y, z), 'XYZ').to_quaternion()


def sgn(side):
    return 1.0 if side == "L" else -1.0


# ------------------------------------------------------------------ proportions
def joints(P):
    """Joint positions from a proportion dict P (see figures.py BODY)."""
    J = {}
    H = P["H"]
    J["pelvis"] = Vector((0, 0.0, P["z_pelvis"]))
    J["waist"] = Vector((0, 0.005, P["z_waist"]))
    J["chest"] = Vector((0, 0.01, P["z_chest"]))
    J["neck"] = Vector((0, 0.02, P["z_neck"]))
    J["head"] = Vector((0, 0.012, P["z_headbase"]))
    J["crown"] = Vector((0, 0.0, H))
    for s in "LR":
        k = sgn(s)
        sx, sz = P["sh_x"], P["z_sh"]
        J[f"clav.{s}"] = Vector((k * 0.025 * P["s"], 0.0, P["z_neck"] - 0.035 * P["s"]))
        J[f"shoulder.{s}"] = Vector((k * sx, 0.015, sz))
        J[f"elbow.{s}"] = Vector((k * (sx + 0.035 * P["s"]), 0.03, sz - P["l_upper"]))
        J[f"wrist.{s}"] = Vector((k * (sx + 0.05 * P["s"]), -0.005, sz - P["l_upper"] - P["l_fore"] * 0.99))
        J[f"fingers.{s}"] = J[f"wrist.{s}"] + Vector((-k * 0.01, -0.02, -P["l_hand"])).normalized() * P["l_hand"]
        hx = P["hip_x"]
        J[f"hip.{s}"] = Vector((k * hx, 0.0, P["z_hip"]))
        J[f"knee.{s}"] = Vector((k * (hx + 0.004), -0.01, P["z_knee"]))
        J[f"ankle.{s}"] = Vector((k * (hx + 0.012), 0.015, P["z_ankle"]))
        J[f"toe.{s}"] = Vector((k * (hx + 0.03), -P["l_foot"] * 0.62, 0.022 * P["s"]))
    return J


# ------------------------------------------------------------------ armature
def make_armature(name, J, collection):
    arm = bpy.data.armatures.new(name + "_rig")
    ob = bpy.data.objects.new(name, arm)
    collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for bn, hj, tj, par in BONES:
        b = arm.edit_bones.new(bn)
        b.head = J[hj]
        b.tail = J[tj]
        b.align_roll(Vector((0, -1, 0)) if abs((J[tj] - J[hj]).normalized().y) < 0.8 else Vector((0, 0, 1)))
        if par:
            b.parent = eb[par]
            b.use_connect = False
        eb[bn] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


class Rest:
    """Rest data read from the armature (or computed from joints)."""

    def __init__(self, J):
        self.J = J
        self.head = {}
        self.tail = {}
        for bn, hj, tj, par in BONES:
            if hj not in J:
                continue
            self.head[bn] = J[hj].copy()
            self.tail[bn] = J[tj].copy()

    def length(self, b):
        return (self.tail[b] - self.head[b]).length

    def dir(self, b):
        return (self.tail[b] - self.head[b]).normalized()


def T(v):
    return Matrix.Translation(Vector(v))


class Poser:
    """Forward kinematics over a pose dict, plus two-bone IK."""

    def __init__(self, rest, pose=None):
        self.rest = rest
        self.pose = dict(pose or {})
        self._G = {}

    def dq(self, b):
        return self.pose.get(b, Quaternion())

    def set(self, b, q):
        self.pose[b] = q
        self._G = {}

    def G(self, b):
        g = self._G.get(b)
        if g is not None:
            return g
        h = self.rest.head[b]
        local = T(h) @ self.dq(b).to_matrix().to_4x4() @ T(-h)
        par = PARENT[b]
        if par is None:
            g = T(self.pose.get("_root", Vector())) @ local
        else:
            g = self.G(par) @ local
        self._G[b] = g
        return g

    def R(self, b):
        return self.G(b).to_quaternion()

    def pt(self, b, p):
        """Where rest point p (rigidly attached to bone b) is in this pose."""
        return self.G(b) @ Vector(p)

    def ik(self, b1, b2, target, pole, end=None, end_rot=None):
        """Point bone b1+b2 so b2's tail reaches target; pole: world direction the joint bends toward.
        end/end_rot: optionally give bone `end` (child of b2) a world rotation."""
        rest = self.rest
        par = PARENT[b1]
        Gp = self.G(par)
        s = Gp @ rest.head[b1]
        L1, L2 = rest.length(b1), (rest.tail[b2] - rest.head[b1] - (rest.tail[b1] - rest.head[b1])).length
        L2 = (rest.tail[b2] - rest.tail[b1]).length
        target = Vector(target)
        d = target - s
        dist = min(max(d.length, abs(L1 - L2) + 1e-3), (L1 + L2) * 0.9995)
        dn = d.normalized()
        a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
        h = math.sqrt(max(L1 * L1 - a * a, 0.0))
        pole = Vector(pole)
        pn = pole - dn * pole.dot(dn)
        if pn.length < 1e-6:
            pn = Vector((0, 0, 1)) - dn * dn.z
        pn.normalize()
        e = s + dn * a + pn * h
        t = s + dn * dist
        u1 = (e - s).normalized()
        u2 = (t - e).normalized()
        # rest frames: bone direction and bend-plane normal
        r1 = rest.dir(b1)
        r2 = (rest.tail[b2] - rest.tail[b1]).normalized()
        n_rest = r1.cross(r2)
        if n_rest.length < 1e-4:
            # straight in rest: use the given pole mapped back into the rest frame
            prest = Gp.to_quaternion().inverted() @ pole
            n_rest = r1.cross(prest)
        n_rest.normalize()
        n_new = u1.cross(u2)
        if n_new.length < 1e-4:
            n_new = u1.cross(pn)
        n_new.normalize()
        R1 = frame(u1, n_new) @ frame(r1, n_rest).transposed()
        R2 = frame(u2, n_new) @ frame(r2, n_rest).transposed()
        Rp = Gp.to_3x3()
        self.set(b1, (Rp.inverted() @ R1).to_quaternion())
        self.set(b2, (R1.inverted() @ R2).to_quaternion())
        if end and end_rot is not None:
            self.set(end, (R2.inverted() @ end_rot.to_matrix()).to_quaternion())
        return e

    def aim(self, b, direction, up=None):
        """Rotate bone b so its rest direction points along `direction` (world), minimal twist."""
        par = PARENT[b]
        Rp = self.G(par).to_quaternion() if par else Quaternion()
        cur = Rp @ self.rest.dir(b)
        q = cur.rotation_difference(Vector(direction).normalized())
        self.set(b, Rp.inverted() @ q @ Rp @ Quaternion())


def frame(d, n):
    """3x3 matrix with columns d, n, d x n."""
    d = Vector(d).normalized()
    n = Vector(n)
    n = (n - d * n.dot(d)).normalized()
    b = d.cross(n)
    m = Matrix((d, n, b)).transposed()
    return m


# ------------------------------------------------------------------ baking clips
def pose_to_bones(arm_ob, rest_mats, pose, prev=None):
    """Apply a pose dict to pose bones (rotation in bone local space)."""
    out = {}
    for b in ORDER:
        pb = arm_ob.pose.bones[b]
        Rr = rest_mats[b]
        q = (Rr.inverted() @ pose.get(b, Quaternion()).to_matrix() @ Rr).to_quaternion()
        if prev is not None and prev.get(b) is not None and prev[b].dot(q) < 0:
            q.negate()
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = q
        out[b] = q
    root = pose.get("_root", Vector())
    Rr = rest_mats["hips"]
    arm_ob.pose.bones["hips"].location = Rr.inverted() @ Vector(root)
    m = max(pose.get("_mug", 1.0), MUG_HIDDEN)
    arm_ob.pose.bones["mug"].scale = (m, m, m)
    return out


MUG_HIDDEN = 0.001


def bake_clip(arm_ob, name, fn, duration, fps=24, step=2):
    """fn(t) -> pose dict. Keys every `step` frames over [0, duration]; the last key equals t = duration
    so looping clips close exactly. Pushes the action onto its own NLA track."""
    rest_mats = {b.name: b.matrix_local.to_3x3() for b in arm_ob.data.bones}
    ad = arm_ob.animation_data or arm_ob.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    nf = max(2, int(round(duration * fps)))
    frames = list(range(0, nf + 1, step))
    if frames[-1] != nf:
        frames.append(nf)
    prev = None
    for f in frames:
        t = f / fps
        prev = pose_to_bones(arm_ob, rest_mats, fn(t), prev)
        for b in ORDER:
            arm_ob.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f, group=b)
        arm_ob.pose.bones["hips"].keyframe_insert("location", frame=f, group="hips")
        arm_ob.pose.bones["mug"].keyframe_insert("scale", frame=f, group="mug")
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    tr = ad.nla_tracks.new()
    tr.name = name
    st = tr.strips.new(name, 0, act)
    st.name = name
    ad.action = None
    return act


def clear_pose(arm_ob):
    for pb in arm_ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
        pb.scale = (1, 1, 1)
