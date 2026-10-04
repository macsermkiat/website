"""Writing surfaces on the rides (docs/adr/0003 'Text lives in the market', BUILD.md write_ / cam_read_).

Each surface is the carpenter's `nmlib.boards.write_surface` (one flat quad `write_<name>`, UVs 0-1
across the writing area with +V up the text, material `paper_card`, never merged, no AO), framed
by an object that belongs to the place, plus the reading camera pair `cam_read_<name>` /
`cam_read_<name>_target` on the face normal, at the distance where the writing area fills
`fill` of a 16:9 frame at the site's 42 degree vertical field of view.

    F = boards.face_frame(center, yaw, lean)          # local +X right, +Y up the text, +Z to the reader
    surface("question_1", F, w, h, parent=gondola)     # quad + cam pair, re-parented if asked

Things that move (a gondola) carry their surface and its camera pair as children, so the engine
reads the world position at the moment it flies in.
"""
import math

from mathutils import Matrix, Vector

import rcommon as rc
from rcommon import Part, rod, state
from nmlib import boards


def _register():
    import art
    rc.IMAGE_MATS["write_card"] = (art.paper_plain(), 0.85)


_register()


def surface(name, F, w, h, z=0.0, fill=0.78, lift=0.04, side=0.0, parent=None, cam_dist=None, margin=0.0):
    """write_<name> (card) at F's origin plus cam_read_<name> and its target. Returns
    (write object, camera point, target point) in world coordinates.

    margin (m): the writing area is the sheet less this all round (round 6 pass 2: in the browser
    the engine's words ran to the very edge of the ticket and the sheet music). The whole w x h
    sheet is then a plain card (`card_<name>`, same paper) at z, with the smaller write_ quad
    0.6 mm above it; the reading camera still frames the whole sheet."""
    backing = None
    if margin > 0.0:
        ex, ey, ez = boards.frame_axes(F)
        o = F @ Vector((0, 0, z))
        ux, uy = ex.normalized() * (w / 2), ey.normalized() * (h / 2)
        backing = rc.picture(f"card_{name}", "write_card", [o - ux - uy, o + ux - uy, o + ux + uy, o - ux + uy])
        ob = boards.write_surface(name, F, w - 2 * margin, h - 2 * margin, z=z + 0.0006, surface="card")
    else:
        ob = boards.write_surface(name, F, w, h, z=z, surface="card")
    # a plain paper texture instead of the flat paper_card colour: gltf-transform's prune drops the
    # UVs of a mesh whose material has no texture, and the engine needs them
    ob.data.materials.clear()
    ob.data.materials.append(rc.mats.get("write_card"))
    ob["nm_mat"] = "write_card"
    ca = ob.data.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
    ca.data.foreach_set("color", [1.0, 1.0, 1.0, 1.0] * len(ob.data.loops))
    t = F @ Vector((0, 0, z))
    ex, ey, ez = boards.frame_axes(F)
    d = cam_dist or boards.read_distance(w, h, fill)
    p = t + ez.normalized() * d + Vector((0, 0, lift)) + ex.normalized() * side
    tgt = rc.node(f"cam_read_{name}_target", tuple(t))
    cam = rc.node(f"cam_read_{name}", tuple(p))
    cam.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
    if parent is not None:
        rc.attach(ob, parent)
        if backing is not None:
            rc.attach(backing, parent)
        rc.set_parent(tgt, parent)
        rc.set_parent(cam, parent)
    return ob, p, t


def local_box(part, F, cx, cy, cz, sx, sy, sz, **kw):
    part.mbox(F @ Matrix.Translation((cx, cy, cz)), (sx, sy, sz), **kw)


def pins(part, F, pts, z, r=0.0075, lite=False):
    """Brass drawing pins at local (x, y) points of F, standing `z` off the face."""
    for x, y in pts:
        part.sphere(F @ Vector((x, y, z + r * 0.4)), r, seg=6 if lite else 8, rings=3 if lite else 5,
                    scale=(1, 1, 0.45), rot=F.to_3x3().to_euler())


def paper_slip(part, F, cx, cy, w, h, rot=0.0, z=0.003, tint=(1, 1, 1)):
    """A loose sheet pinned to a board (plain, no writing): a thin box turned `rot` in the face."""
    M = F @ Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(rot, 4, 'Z')
    part.mbox(M, (w, h, 0.0012), tint=tint, bevel=0.0)
