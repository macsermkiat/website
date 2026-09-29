"""Carpentry helpers built on geo.Part: plank walls, siding, shingles, valances, signs,
bulb strings, snow caps and fir garlands. All sizes in metres, Blender Z-up, front = -Y.

A roof slope is described by a `Slope`: an eave point, the direction along the eave, the
down-slope direction and the slope length, so the same helpers serve ridge-along-X roofs,
front gables, lean-tos and hoods.
"""
import math

from mathutils import Euler, Matrix, Vector, noise

from . import geo, state
from .geo import catenary


def R():
    return state.rng


# ------------------------------------------------------------------ walls
def plank_wall(part, a, b, z0, top, axis='x', at=0.0, pw=0.14, th=0.024, gap=0.004,
               lean=0.004, segs=1, tint=None, var=0.1, skip=None, bevel=None, band=None):
    """Vertical planks from a to b along `axis` ('x' or 'y') at depth `at`.
    `top` is a number or f(pos)->z. `skip(pos)` returns True to leave a gap (openings)."""
    pos, out = a, []
    while pos < b - 1e-4:
        w = min(pw * R().uniform(0.8, 1.2), b - pos)
        if b - (pos + w) < pw * 0.35:
            w = b - pos
        c = pos + w / 2
        if skip is None or not skip(c):
            t = top(c) if callable(top) else top
            t += R().uniform(-0.008, 0.008)
            h = t - z0
            d = R().uniform(-0.003, 0.003)
            r = R().uniform(-lean, lean)
            if axis == 'x':
                part.box((c, at + d, z0 + h / 2), (w - gap, th, h), rot=(0, r, 0), segs=segs,
                         tint=tint, var=var, grain=2, bevel=bevel, band=band)
            else:
                part.box((at + d, c, z0 + h / 2), (th, w - gap, h), rot=(r, 0, 0), segs=segs,
                         tint=tint, var=var, grain=2, bevel=bevel, band=band)
            out.append(c)
        pos += w
    return out


def lap_siding(part, a, b, z0, z1, axis='x', at=0.0, outward=-1, bh=0.15, lap=0.025,
               th=0.02, tint=None, var=0.1, segs=1, bevel=None):
    """Horizontal overlapping boards (Stuelpschalung) from z0 to z1, lower board edges kick out."""
    z = z0
    while z < z1 - 0.02:
        h = min(bh * R().uniform(0.92, 1.08), z1 - z + lap)
        tilt = math.radians(4.0) * outward
        L = b - a + R().uniform(-0.01, 0.01)
        cz = z + h / 2
        if axis == 'x':
            part.box(((a + b) / 2, at + outward * 0.012, cz), (L, th, h), rot=(-tilt, 0, 0),
                     segs=segs, tint=tint, var=var, grain=0, bevel=bevel)
        else:
            part.box((at + outward * 0.012, (a + b) / 2, cz), (th, L, h), rot=(0, tilt, 0),
                     segs=segs, tint=tint, var=var, grain=1, bevel=bevel)
        z += h - lap
    return z


def floor_boards(part, x0, x1, y0, y1, z, pw=0.14, th=0.035, tint=None):
    y = y0
    while y < y1 - 1e-4:
        w = min(pw * R().uniform(0.9, 1.1), y1 - y)
        part.box(((x0 + x1) / 2, y + w / 2, z - th / 2), (x1 - x0 + R().uniform(-0.01, 0.01), w - 0.005, th),
                 tint=tint, grain=0, bevel=0)
        y += w


def nails(part, pts, normal=(0, -1, 0), r=0.007):
    n = Vector(normal).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(n).to_euler()
    for p in pts:
        part.cyl(Vector(p) + n * 0.002, r, r * 0.8, 0.004, seg=6, rot=rot, smooth=False, var=0.2)


# ------------------------------------------------------------------ slopes / roofs
class Slope:
    """Roof plane: eave midpoint, eave direction, down-slope direction, slope length and extent
    along the eave (a0..a1). The basis is made right-handed so boxes are never mirrored."""

    def __init__(self, eave, along, down, length, a0, a1):
        self.E = Vector(eave)
        A = Vector(along).normalized()
        Dn = Vector(down).normalized()
        U = -Dn
        N = A.cross(U)
        if N.z < 0:
            A, a0, a1 = -A, -a1, -a0
            N = A.cross(U)
        self.A, self.U, self.N, self.Dn = A, U, N.normalized(), Dn
        self.L, self.a0, self.a1 = length, a0, a1

    def point(self, a, s, n=0.0):
        """a along the eave, s up-slope from the eave, n off the surface."""
        return self.E + self.A * a + self.U * s + self.N * n

    def basis(self):
        return Matrix((self.A, self.U, self.N)).transposed().to_4x4()


def gable_slopes(W, D, eave_z, ridge_z, ov_eave=0.3, ov_gable=0.2, ridge_axis='x'):
    """Two Slopes of a symmetric gable roof over a W x D footprint centred on the origin."""
    half = (D if ridge_axis == 'x' else W) / 2
    rise = ridge_z - eave_z
    ang = math.atan2(rise, half)
    run = half + ov_eave
    L = run / math.cos(ang)
    ext = (W if ridge_axis == 'x' else D) / 2 + ov_gable
    slopes = []
    for s in (-1, 1):
        if ridge_axis == 'x':
            eave = (0, s * run, ridge_z - run * math.tan(ang))
            along, down = (1, 0, 0), (0, s * math.cos(ang), -math.sin(ang))
        else:
            eave = (s * run, 0, ridge_z - run * math.tan(ang))
            along, down = (0, 1, 0), (s * math.cos(ang), 0, -math.sin(ang))
        slopes.append(Slope(eave, along, down, L, -ext, ext))
    return slopes, ang


def roof_deck(part, sl, th=0.022, n=None, tint=None, rafters=5, rafter=(0.06, 0.10)):
    """Boards across the slope plus rafters (visible from below)."""
    B = sl.basis()
    n = n or max(3, int(sl.L / 0.16))
    step = sl.L / n
    for i in range(n):
        s = (i + 0.5) * step
        p = sl.point((sl.a0 + sl.a1) / 2, s, -th / 2)
        part.mbox(Matrix.Translation(p) @ B, (sl.a1 - sl.a0, step - 0.004, th), grain=0, tint=tint, bevel=0)
    for i in range(rafters):
        a = sl.a0 + 0.08 + i * (sl.a1 - sl.a0 - 0.16) / max(1, rafters - 1)
        p = sl.point(a, sl.L / 2, -th - rafter[1] / 2)
        part.mbox(Matrix.Translation(p) @ B, (rafter[0], sl.L, rafter[1]), grain=1, tint=tint, bevel=0.004)


def shingles(part, sl, sw=0.19, sh=0.30, st=0.016, expo=0.14, lift=0.012, tint="shingle",
             var=0.16, curl=2.0):
    """Split wood shingles in staggered rows from eave to ridge. Lite: one strip per row."""
    B = sl.basis()
    rows = int((sl.L + 0.02) / expo) + 1
    for r in range(rows):
        s0 = r * expo - 0.03                      # bottom edge of this course
        if state.lite():
            L = min(sh, sl.L - s0 + 0.02)
            p = sl.point((sl.a0 + sl.a1) / 2 - 0.02, s0 + L / 2, lift + st / 2 + 0.004)
            M = Matrix.Translation(p) @ B @ Euler((math.radians(-2), 0, 0)).to_matrix().to_4x4()
            part.mbox(M, (sl.a1 - sl.a0 + 0.04, L, st), grain=1, tint=tint, var=var)
            continue
        a = sl.a0 - 0.02 - (sw / 2) * (r % 2) * R().uniform(0.6, 1.0)
        while a < sl.a1 + 0.02:
            w = min(sw * R().uniform(0.65, 1.3), sl.a1 + 0.02 - a)
            if w < 0.035:
                break
            L = min(sh, sl.L - s0 + 0.03)
            if L < 0.04:
                break
            p = sl.point(a + w / 2, s0 + L / 2, lift + st / 2 + 0.004 * R().random() + 0.002 * (r % 2))
            jit = Euler((math.radians(R().uniform(-curl - 1.5, -1.0)), math.radians(R().uniform(-1.5, 1.5)),
                         math.radians(R().uniform(-2.5, 2.5)))).to_matrix().to_4x4()
            M = Matrix.Translation(p) @ B @ jit
            part.mbox(M, (w - 0.006, L, st * R().uniform(0.8, 1.25)), grain=1, tint=tint, var=var,
                      bevel=0.0)
            a += w


def board_roof(part, sl, bw=0.2, th=0.024, batten=0.05, tint=None, var=0.12):
    """Boards running down the slope with cover battens over the joints."""
    B = sl.basis()
    a = sl.a0
    while a < sl.a1 - 1e-3:
        w = min(bw * R().uniform(0.85, 1.15), sl.a1 - a)
        p = sl.point(a + w / 2, sl.L / 2, th / 2 + 0.003)
        part.mbox(Matrix.Translation(p) @ B, (w - 0.004, sl.L + 0.02, th), grain=1, tint=tint, var=var)
        if a + w < sl.a1 - 0.02:
            p = sl.point(a + w, sl.L / 2, th + 0.012)
            part.mbox(Matrix.Translation(p) @ B, (batten, sl.L + 0.03, 0.02), grain=1, tint=tint, var=var)
        a += w


def barge_boards(part, sl, h=0.18, th=0.03, tint=None, drop=0.04):
    B = sl.basis()
    for a in (sl.a0 - th / 2, sl.a1 + th / 2):
        p = sl.point(a, sl.L / 2, -drop + 0.03)
        part.mbox(Matrix.Translation(p) @ B, (th, sl.L + 0.02, h), grain=1, tint=tint)


def fascia(part, sl, h=0.14, th=0.028, tint=None, band=None):
    B = sl.basis()
    p = sl.point((sl.a0 + sl.a1) / 2, -th / 2, -0.03)
    M = Matrix.Translation(p) @ B
    part.mbox(M, (sl.a1 - sl.a0 + 0.04, th, h), grain=0, tint=tint, band=band)


def snow_cap(part, sl, thick=0.05, lip=0.05, nx=None, ns=None, edge_in=0.07, seed=0.0, cover=0.72,
             ridge_clear=0.2, patch_scale=1.7, base=0.03):
    """Thin, patchy snow on a slope with a soft lip curling over the eave.

    cover:       roughly the fraction of the slope under snow (the rest shows shingles);
    ridge_clear: metres below the ridge that the wind has scoured bare;
    patch_scale: frequency of the bare patches (per metre).
    Where the snow runs out its edge sinks below the roof surface, so the boundary cuts
    through the shingles like real thin snow instead of ending in a vertical wall.
    Faces with no snow at all are dropped (they cost nothing)."""
    import bmesh
    nx = nx or (12 if state.lite() else 34)
    ns = ns or (6 if state.lite() else 14)
    bm = bmesh.new()
    a0, a1 = sl.a0 + edge_in, sl.a1 - edge_in
    s0, s1 = -lip, sl.L - 0.03
    thr = 1.0 - cover
    grid, dens = [], []
    for j in range(ns + 1):
        row, drow = [], []
        t = j / ns
        s = s0 + (s1 - s0) * t
        for i in range(nx + 1):
            u = i / nx
            a = a0 + (a1 - a0) * u
            edge = min(u, 1 - u) * (a1 - a0)
            fall = min(1.0, edge / 0.10) ** 0.6
            p3 = Vector((a * 3.1 + seed, s * 3.1, seed * 0.7))
            lump = 0.75 + 0.45 * noise.noise(p3) + 0.15 * noise.noise(p3 * 3.3)
            q = Vector((a * patch_scale + seed * 1.7, s * patch_scale * 1.4, seed * 2.3 + 5.0))
            d = 0.5 + 0.55 * noise.noise(q) + 0.25 * noise.noise(q * 2.7)
            ridge = min(1.0, max(0.0, (sl.L - ridge_clear - s) / 0.25))   # scoured band under the ridge
            d = d * ridge
            k = max(0.0, min(1.0, (d - thr) / 0.18))
            k = k * k * (3 - 2 * k)
            h = thick * fall * max(0.25, lump) * k
            if s < 0:                       # the lip curls down past the eave
                kk = -s / lip
                pos = sl.point(a, s * 0.55, (h + base) * (1 - kk) - kk * kk * thick * 1.1 * k - (1 - k) * 0.03)
            else:
                pos = sl.point(a, s, base * k + h - (1 - k) * 0.012)
            row.append(bm.verts.new(pos))
            drow.append(k)
        grid.append(row)
        dens.append(drow)
    for j in range(ns):
        for i in range(nx):
            if max(dens[j][i], dens[j][i + 1], dens[j + 1][i + 1], dens[j + 1][i]) <= 0.0:
                continue
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    part.from_bmesh(bm, grain=0, smooth=True)


# ------------------------------------------------------------------ decoration
def valance(part, x0, x1, y, z_top, h, drop, n, style="scallop", holes=None, depth=0.022,
            band=None, tint=None, axis='x', hole_r=None, M=None):
    """Carved board along an eave. style: scallop | point | wave | step | straight.
    holes: None | 'star' | 'circle' | 'heart' cut through above each tongue.
    The outline is drawn in local X (x0..x1) / Y (height, top at z_top); by default it stands
    in the XZ plane at depth y (axis 'x') or the YZ plane at x=y (axis 'y'); pass M to place
    it anywhere else (e.g. along a rake)."""
    zb = z_top - h
    w = (x1 - x0) / n
    outer = [(x0, z_top)]
    bottom = []
    seg = 3 if state.lite() else 8
    for k in range(n):
        xa = x0 + k * w
        if style == "scallop":
            for i in range(seg + 1):
                t = math.pi * i / seg
                bottom.append((xa + w / 2 - (w / 2) * math.cos(t), zb - drop * math.sin(t)))
        elif style == "point":
            bottom += [(xa, zb), (xa + w / 2, zb - drop), (xa + w, zb)]
        elif style == "wave":
            for i in range(seg + 1):
                t = i / seg
                bottom.append((xa + w * t, zb - drop * 0.5 * (1 - math.cos(2 * math.pi * t))))
        elif style == "step":
            bottom += [(xa, zb), (xa + w * 0.2, zb), (xa + w * 0.2, zb - drop), (xa + w * 0.8, zb - drop),
                       (xa + w * 0.8, zb), (xa + w, zb)]
        else:
            bottom += [(xa, zb), (xa + w, zb)]
    # remove duplicate consecutive points
    pts = []
    for p in bottom:
        if not pts or (abs(pts[-1][0] - p[0]) > 1e-5 or abs(pts[-1][1] - p[1]) > 1e-5):
            pts.append(p)
    outer = [(x0, z_top)] + pts + [(x1, z_top)]
    outer = [outer[0]] + outer[1:]
    outer.reverse()  # counter-clockwise
    hl = []
    if holes and not state.lite():
        r = hole_r or min(w, h) * 0.26
        for k in range(n):
            cx = x0 + (k + 0.5) * w
            cy = zb + (h - 0.02) * 0.45 - (drop * 0.15 if style != "straight" else 0)
            if holes == "star":
                hl.append(geo.star_polygon(cx, cy, r, r * 0.45, 5))
            elif holes == "circle":
                hl.append(geo.circle_polygon(cx, cy, r * 0.6, 10))
            elif holes == "heart":
                hl.append(geo.heart_polygon(cx, cy - r * 0.2, r * 1.6))
    if M is not None:
        pass
    elif axis == 'x':
        M = Matrix.Translation((0, y, 0)) @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    else:  # along Y at x=y (plane YZ), outward along -X
        M = Matrix.Translation((y, 0, 0)) @ Euler((math.pi / 2, 0, -math.pi / 2)).to_matrix().to_4x4()
    part.shape(outer, hl, depth=depth, M=M, band=band, tint=tint)


def sign(board, letters, text, font, center, w, h, depth=0.03, text_depth=0.012, rot_z=0.0,
         board_band="black", text_band="gold", frame_band=None, text_size=None, spacing=1.0,
         board_shape="rect", tint=None, text_tint=None, resolution=2, max_fill=0.86, text_dy=0.0,
         text_bevel=None):
    """Painted sign board with raised 3D letters. The board face looks toward -Y (rotated by
    rot_z about Z). board / letters are Parts (usually both 'paint'). Returns the text size."""
    c = Vector(center)
    Rz = Euler((0, 0, rot_z)).to_matrix().to_4x4()
    Mb = Matrix.Translation(c) @ Rz @ Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    if board_shape == "rect":
        outer = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    elif board_shape == "arch":      # flat bottom, arched top
        outer = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 4)]
        for i in range(1, 12):
            t = math.pi * i / 12
            outer.append((w / 2 * math.cos(t), h / 4 + h / 4 * math.sin(t)))
        outer.append((-w / 2, h / 4))
    elif board_shape == "banner":    # swallow-tail ends
        k = h * 0.35
        outer = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2 - k, 0), (w / 2, h / 2), (-w / 2, h / 2), (-w / 2 + k, 0)]
    elif board_shape == "oval":
        outer = [(w / 2 * math.cos(2 * math.pi * i / 28), h / 2 * math.sin(2 * math.pi * i / 28)) for i in range(28)]
    board.shape(outer, depth=depth, M=Mb, band=board_band, tint=tint, bevel=0.003)
    if frame_band:
        fw = 0.03
        inset = 0.035
        for (x, z, ww, hh) in ((0, h / 2 - inset, w - 2 * inset, fw), (0, -h / 2 + inset, w - 2 * inset, fw),
                               (-w / 2 + inset, 0, fw, h - 2 * inset), (w / 2 - inset, 0, fw, h - 2 * inset)):
            if board_shape != "rect" and abs(z) > 0 and z > 0:
                continue
            p = c + (Rz.to_3x3() @ Vector((x, -depth / 2 - 0.006, z)))
            board.box(p, (ww, 0.012, hh), rot=(0, 0, rot_z), band=frame_band, grain=0 if ww > hh else 2)
    size = text_size or h * 0.55
    Mt = Matrix.Translation(c + Rz.to_3x3() @ Vector((0, -depth / 2 - text_depth / 2 - 0.004, text_dy))) @ Rz @ \
        Euler((math.pi / 2, 0, 0)).to_matrix().to_4x4()
    return letters.text(text, font, size, text_depth, M=Mt, max_width=w * max_fill, band=text_band,
                        tint=text_tint, spacing=spacing, resolution=resolution, bevel=text_bevel)


def bulb_string(bulbs, wire, anchors, sag=0.06, spacing=0.2, bulb_r=0.028, drop=0.05, seg=None):
    """Fairy bulbs hanging from a sagging wire through `anchors`. bulbs: Part('bulb_warm')."""
    seg = seg or (5 if state.lite() else 8)
    rings = 3 if state.lite() else 6
    for a, b in zip(anchors[:-1], anchors[1:]):
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        n = max(1, round(L / spacing))
        pts = catenary(a, b, sag, max(3, n) if state.lite() else max(4, n * 3))
        wire.tube(pts, 0.004, tseg=3 if state.lite() else 5)
        for i in range(n):
            t = (i + 0.5) / n
            p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
            if not state.lite():
                wire.cyl(p - Vector((0, 0, drop * 0.45)), 0.011, 0.009, drop * 0.5, seg=6, caps=False)
            bulbs.sphere(p - Vector((0, 0, drop + bulb_r * 0.6)), bulb_r, seg=seg, rings=rings,
                         scale=(1, 1, 1.35), var=0.05)


def fir_garland(fir, beads, a, b, sag=0.25, radius=0.05, tufts_per_m=None, bead_every=0.16,
                bead_bands=("ornament_red", "ornament_gold")):
    """Fir rope between a and b; `beads` is a dict {material key: Part} for the baubles."""
    a, b = Vector(a), Vector(b)
    n = 18 if not state.lite() else 8
    pts = catenary(a, b, sag, n)
    fir.tube(pts, radius * 0.6, tseg=5, var=0.1)
    L = (b - a).length
    tpm = tufts_per_m or (46 if not state.lite() else 14)
    count = int(L * tpm)
    for k in range(count):
        t = (k + R().random()) / count
        p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        off = Vector((R().uniform(-1, 1), R().uniform(-1, 1), R().uniform(-1, 1))).normalized() * radius * 0.7
        rot = Euler((R().uniform(0, 3.14), R().uniform(0, 3.14), R().uniform(0, 3.14)))
        fir.sphere(p + off, radius * 0.85, seg=5, rings=3, scale=(1.7, 0.5, 0.45), rot=rot, var=0.2)
    nb = max(1, int(L / bead_every))
    keys = list(bead_bands)
    for k in range(nb):
        t = (k + 0.5) / nb
        p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t))) + Vector((0, -radius * 0.9, -radius * 0.4))
        part = beads[keys[k % len(keys)]]
        part.sphere(p, R().uniform(0.016, 0.024), seg=10 if not state.lite() else 6,
                    rings=7 if not state.lite() else 4, var=0.05)
