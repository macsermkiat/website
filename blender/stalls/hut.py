"""Parametric market hut used by the four section stalls and the deco kit.

A Hut owns one Part per material and builds the common carcass: plinth, floor, posts, walls,
counter (top exactly at 1.05 m), back shelves, roof with bargeboards, eave bulbs, snow caps
and the named empties. Stall scripts pass parameters and then add their own character.
Blender: Z up, front (the visitor side) toward -Y, origin on the ground at the footprint centre.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import bpy  # noqa: E402,F401  (must precede mathutils)
from mathutils import Euler, Matrix, Vector  # noqa: E402

from nmlib import carpentry as cp  # noqa: E402
from nmlib import export, geo, state  # noqa: E402
from nmlib.geo import Part  # noqa: E402

COUNTER_TOP = 1.05
OPEN_TOP = 2.2
# counter tints are multipliers of the oak kit (which is already oak-brown)
OAK_TINT = {"oak": (1.0, 1.0, 1.0), "honey": (1.08, 1.0, 0.86), "pine": (1.12, 1.08, 0.95),
            "dark": (0.62, 0.56, 0.52), "walnut": (0.55, 0.45, 0.40), "soot": (0.40, 0.37, 0.35)}


def grime(z_clean=0.45, strength=0.35):
    """Shade function: splash grime and damp near the ground."""
    def f(p):
        t = min(1.0, max(0.0, p.z / z_clean))
        return 1.0 - strength * (1 - t) ** 1.6
    return f


def _smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def counter_wear(y_front, x0, x1, top=COUNTER_TOP, strength=0.5, band=0.10, seed=0.0):
    """Shade function (edge-wear mask) for a counter: hands and sleeves darken a band along the
    front edge of the top and the upper part of the front lip, most where people are served
    (the middle) and in a few blotches; the ends stay cleaner. Works on per-vertex colour, so
    the counter boards carry a vertex grid (see Hut.build_counter)."""
    from mathutils import noise as mnoise
    L = max(x1 - x0, 1e-3)

    def f(p):
        if p.z < top - 0.11:
            return 1.0
        dy = p.y - y_front                           # 0 at the front edge, grows inward
        edge = 1.0 - _smooth(0.0, band, max(dy, 0.0))
        if dy < 0.0:                                 # front lip face: upper part worn
            edge = _smooth(top - 0.10, top - 0.01, p.z)
        u = (p.x - x0) / L
        use = 0.35 + 0.65 * math.sin(math.pi * min(1.0, max(0.0, u))) ** 0.7
        blot = 0.75 + 0.5 * mnoise.noise(Vector((p.x * 3.7 + seed, p.y * 9.0, seed * 0.3)))
        d = strength * edge * use * max(0.3, blot)
        d = min(d, 0.62)
        return (1.0 - d * 0.92, 1.0 - d, 1.0 - d * 1.08)
    return f


class Hut:
    def __init__(self, key, W=3.6, D=2.4, eave=2.5, ridge=3.45, ridge_axis='x', ov_eave=0.38,
                 ov_gable=0.24, wall="vertical", wall_tint="honey", frame_tint="oak",
                 roof="shingles", roof_tint="shingle", inner_tint="pine", counter_tint="oak",
                 counter_depth=0.6, counter_over=0.22, shelves=(1.38, 1.78), shade=None,
                 plank_w=0.14, bulbs_sides=False, bulb_spacing=0.2, front_posts=None,
                 header_h=0.16, open_top=OPEN_TOP, wall_band=None, plank_bevel=None,
                 shingle_size=(0.19, 0.14), bulb_detail=(None, None), lap_segs=1):
        self.key = key
        self.W, self.D, self.eave, self.ridge = W, D, eave, ridge
        self.ridge_axis = ridge_axis
        self.ov_eave, self.ov_gable = ov_eave, ov_gable
        self.wall, self.wall_tint, self.frame_tint = wall, wall_tint, frame_tint
        self.roof, self.roof_tint, self.inner_tint = roof, roof_tint, inner_tint
        self.counter_tint = counter_tint
        self.counter_depth, self.counter_over = counter_depth, counter_over
        self.shelves = shelves
        self.plank_w = plank_w
        self.bulbs_sides = bulbs_sides
        self.bulb_spacing = bulb_spacing
        self.header_h = header_h
        self.open_top = open_top
        self.wall_band = wall_band
        self.plank_bevel = plank_bevel
        self.shingle_size = shingle_size
        self.lap_segs = lap_segs                # vertex columns per lap board (soot/grime detail)
        self.bulb_detail = bulb_detail          # (seg, rings) of the eave bulbs; None = library default
        self.x0, self.x1 = -W / 2, W / 2
        self.yF, self.yB = -D / 2, D / 2
        self.front_posts = front_posts or [self.x0 + 0.05, self.x1 - 0.05]
        sh = shade or grime()
        self.wood = Part(f"{key}_wood", "wood", shade=sh)
        self.frame = Part(f"{key}_frame", "wood", shade=sh, bevel=0.007)
        self.roofp = Part(f"{key}_roof", "wood", shade=None)
        self.paint = Part(f"{key}_paint", "paint", shade=sh, var=0.04)
        self.iron = Part(f"{key}_iron", "iron")
        self.counter = Part(f"{key}_counter", "oak", var=0.06)       # oak top + lip, edge-wear shaded
        self.bulbs = Part("bulbs_0", "bulb_warm", var=0.03)
        self.wire = Part(f"{key}_wire", "wire", var=0.0)
        self.fir = Part(f"{key}_fir", "fir", var=0.2)
        self.beads = {"ornament_red": Part(f"{key}_baubles_red", "ornament_red", var=0.05),
                      "ornament_gold": Part(f"{key}_baubles_gold", "ornament_gold", var=0.05)}
        self.extra = []          # further Parts created by the stall script
        self.snow = []
        self.slopes, self.pitch = cp.gable_slopes(W, D, eave, ridge, ov_eave, ov_gable, ridge_axis)
        self.front_slope = min(self.slopes, key=lambda s: s.E.y) if ridge_axis == 'x' else None

    # -------------------------------------------------------------- geometry helpers
    def top_at(self, axis, pos):
        """Top of a wall at `pos` along `axis` (gable walls rise to the ridge)."""
        rise = self.ridge - self.eave
        if self.ridge_axis == 'x' and axis == 'y':
            return self.eave + rise * (1 - abs(pos) / (self.D / 2)) - 0.05
        if self.ridge_axis == 'y' and axis == 'x':
            return self.eave + rise * (1 - abs(pos) / (self.W / 2)) - 0.05
        return self.eave - 0.02

    def part(self, name, mat, **kw):
        p = Part(f"{self.key}_{name}", mat, **kw)
        self.extra.append(p)
        return p

    # -------------------------------------------------------------- carcass
    def build_carcass(self, front_lower=True, front_upper=True, sides=True, back=True, lower_top=None):
        W, D = self.W, self.D
        x0, x1, yF, yB = self.x0, self.x1, self.yF, self.yB
        fr, wt = self.frame_tint, self.wall_tint
        # plinth sill beams and floor
        for y in (yF + 0.05, yB - 0.05):
            self.frame.box((0, y, 0.05), (W + 0.02, 0.1, 0.1), tint="dark")
        for x in (x0 + 0.05, x1 - 0.05):
            self.frame.box((x, 0, 0.05), (0.1, D - 0.2, 0.1), tint="dark")
        cp.floor_boards(self.wood, x0 + 0.1, x1 - 0.1, yF + 0.1, yB - 0.1, 0.13, tint="dark")
        # corner posts and front posts
        for x in (x0 + 0.05, x1 - 0.05):
            self.frame.box((x, yB - 0.05, self.eave / 2), (0.1, 0.1, self.eave), tint=fr, segs=3)
        for x in self.front_posts:
            self.frame.box((x, yF + 0.05, self.eave / 2), (0.1, 0.1, self.eave), tint=fr, segs=3)
        # top plates (wall plates) front and back
        for y in (yF + 0.05, yB - 0.05):
            self.frame.box((0, y, self.eave - 0.06), (W + 0.04, 0.12, 0.12), tint=fr)
        for x in (x0 + 0.05, x1 - 0.05):
            self.frame.box((x, 0, self.eave - 0.06), (0.12, D, 0.12), tint=fr)
        # front header over the opening
        self.frame.box((0, yF + 0.02, self.open_top + self.header_h / 2), (W - 0.02, 0.14, self.header_h),
                       tint=fr, bevel_segments=2)
        pw = self.plank_w
        # walls
        if back:
            self._wall('x', x0 + 0.1, x1 - 0.1, yB - 0.02, lambda c: self.top_at('x', c), outward=1)
        if sides:
            for sx, out in ((x0 + 0.02, -1), (x1 - 0.02, 1)):
                self._wall('y', yF + 0.1, yB - 0.1, sx, lambda c: self.top_at('y', c), outward=out)
        if front_lower:
            self._wall('x', x0 + 0.1, x1 - 0.1, yF + 0.02, lower_top or (lambda c: COUNTER_TOP - 0.07),
                       outward=-1, z0=0.1)
            # rails on the lower front
            for z in (0.28, 0.82):
                self.frame.box((0, yF - 0.012, z), (W - 0.16, 0.03, 0.09), tint=fr)
        if front_upper:
            zt = self.open_top + self.header_h
            if self.ridge_axis == 'y' or self.eave - zt > 0.08:
                cp.plank_wall(self.paint if self.wall_band else self.wood, x0 + 0.1, x1 - 0.1, zt,
                              lambda c: self.top_at('x', c), axis='x', at=yF + 0.03, pw=self.pw, tint=wt, var=0.12,
                              band=self.wall_band)

    @property
    def pw(self):
        """Plank width; lite builds use wider boards (fewer boxes, same look at phone distance)."""
        return self.plank_w * (1.7 if state.lite() else 1.0)

    def _lsegs(self, length):
        if self.lap_segs <= 1 or state.lite():
            return 1
        return max(1, int(round(self.lap_segs * length / self.W)))

    def _wall(self, axis, a, b, at, top, outward, z0=0.1):
        if self.wall == "lap":
            zmax = max(top(a), top((a + b) / 2), top(b))
            if axis == 'x' and self.ridge_axis == 'y' or axis == 'y' and self.ridge_axis == 'x':
                # gable wall: lap boards up to eave, vertical boards in the gable triangle
                cp.lap_siding(self.wood, a, b, z0, min(zmax, self.eave - 0.05), axis=axis, at=at,
                              outward=outward, tint=self.wall_tint, var=0.12, bevel=self.plank_bevel,
                              segs=self._lsegs(b - a))
                if zmax > self.eave:
                    cp.plank_wall(self.wood, a, b, self.eave - 0.08, top, axis=axis, at=at,
                                  pw=self.pw, tint=self.wall_tint, var=0.12, bevel=self.plank_bevel)
            else:
                cp.lap_siding(self.wood, a, b, z0, zmax, axis=axis, at=at, outward=outward,
                              tint=self.wall_tint, var=0.12, bevel=self.plank_bevel, segs=self._lsegs(b - a))
            # inner lining so gaps never show daylight
            self._lining(axis, a, b, at - outward * 0.03, top, z0)
        else:
            wp = self.paint if self.wall_band else self.wood
            cp.plank_wall(wp, a, b, z0, top, axis=axis, at=at, pw=self.pw,
                          tint=None if self.wall_band else self.wall_tint, var=0.13 if not self.wall_band else 0.05,
                          band=self.wall_band, bevel=self.plank_bevel)
            if self.wall == "batten":
                pos = a + self.pw
                while pos < b - 0.05:
                    t = top(pos)
                    h = t - z0 - 0.02
                    if axis == 'x':
                        self.wood.box((pos, at + outward * 0.02, z0 + h / 2), (0.045, 0.02, h),
                                      tint=self.wall_tint, grain=2, bevel=self.plank_bevel)
                    else:
                        self.wood.box((at + outward * 0.02, pos, z0 + h / 2), (0.02, 0.045, h),
                                      tint=self.wall_tint, grain=2, bevel=self.plank_bevel)
                    pos += self.pw * 1.02
            self._lining(axis, a, b, at - outward * 0.028, top, z0)

    def _lining(self, axis, a, b, at, top, z0):
        """Cheap inner skin: one board per 0.6 m, darker, only to close the wall visually."""
        pos = a
        step = 1.2 if state.lite() else 0.6
        while pos < b - 1e-3:
            w = min(step, b - pos)
            c = pos + w / 2
            t = min(top(pos + 0.02), top(pos + w - 0.02)) - 0.02
            h = t - z0
            if axis == 'x':
                self.wood.box((c, at, z0 + h / 2), (w, 0.012, h), tint=self.inner_tint, var=0.05, grain=2, bevel=0)
            else:
                self.wood.box((at, c, z0 + h / 2), (0.012, w, h), tint=self.inner_tint, var=0.05, grain=2, bevel=0)
            pos += w

    def build_counter(self, x0=None, x1=None, brackets=4, front_band=None, wear=0.5, grid=0.16,
                      extra_shade=None):
        """Counter top exactly at COUNTER_TOP, overhanging to the front, on brackets.
        Oak kit boards; the front board has a rounded, worn nosing, and the top and lip carry a
        vertex grid shaded by counter_wear (darkened front edge where hands rest)."""
        x0 = self.x0 + 0.1 if x0 is None else x0
        x1 = self.x1 - 0.1 if x1 is None else x1
        yF = self.yF
        th = 0.05
        y_front = y_front0 = yF - self.counter_over
        y_back = y_front + self.counter_depth
        C = self.counter
        cw = counter_wear(y_front, x0, x1, strength=wear, seed=len(self.key))
        if extra_shade is None:
            C.shade = cw
        else:                                        # e.g. scorch under a grill (multiplied in)
            def C_shade(p, cw=cw, ex=extra_shade):
                a, b = cw(p), ex(p)
                a = (a, a, a) if isinstance(a, (int, float)) else a
                b = (b, b, b) if isinstance(b, (int, float)) else b
                return tuple(a[i] * b[i] for i in range(3))
            C.shade = C_shade
        L = x1 - x0 + 0.06
        nx = max(2, int(L / (0.3 if state.lite() else grid)))       # wear-grid columns
        # three thick boards along X; the front one is split lengthwise into a grid for the wear
        n = 3
        bw = (y_back - y_front) / n
        for i in range(n):
            front = i == 0
            C.box(((x0 + x1) / 2 + state.rng.uniform(-0.01, 0.01), y_front + (i + 0.5) * bw,
                   COUNTER_TOP - th / 2), (L, bw - 0.004, th),
                  tint=OAK_TINT.get(self.counter_tint, self.counter_tint), grain=0, var=0.1,
                  bevel=0.012 if front else 0.005, bevel_segments=2,
                  segs=(nx, 3, 1) if front else max(1, nx // 3))
        # front edge lip board
        C.box(((x0 + x1) / 2, y_front0 - 0.012, COUNTER_TOP - 0.06), (x1 - x0 + 0.08, 0.024, 0.09),
              tint=OAK_TINT.get(self.counter_tint, self.counter_tint), grain=0, segs=(nx, 1, 2), bevel=0.006,
              bevel_segments=2)
        for i in range(brackets):
            x = x0 + 0.12 + i * (x1 - x0 - 0.24) / max(1, brackets - 1)
            M = Matrix.Translation((x, yF - 0.1, COUNTER_TOP - 0.19)) @ Euler((math.radians(45), 0, 0)).to_matrix().to_4x4()
            self.frame.mbox(M, (0.05, 0.05, 0.3), grain=2, tint=self.frame_tint)
        self.counter_y = (y_front + y_back) / 2

    def build_shelves(self, depth=0.3, x0=None, x1=None, band=None):
        x0 = self.x0 + 0.15 if x0 is None else x0
        x1 = self.x1 - 0.15 if x1 is None else x1
        yb = self.yB - 0.04
        for z in self.shelves:
            self.frame.box(((x0 + x1) / 2, yb - depth / 2, z - 0.015), (x1 - x0, depth, 0.03),
                           tint=self.inner_tint, grain=0)
            self.frame.box(((x0 + x1) / 2, yb - depth + 0.01, z + 0.02), (x1 - x0, 0.015, 0.05),
                           tint=self.inner_tint, grain=0, band=band)
            for x in (x0 + 0.1, (x0 + x1) / 2, x1 - 0.1):
                M = Matrix.Translation((x, yb - 0.1, z - 0.1)) @ Euler((math.radians(-45), 0, 0)).to_matrix().to_4x4()
                self.frame.mbox(M, (0.03, 0.03, 0.22), grain=2, tint=self.frame_tint)
        self.shelf_y = yb - depth / 2

    def build_roof(self, cover=None, deck=True, barge=True, ridge_cap=True, fascia_band=None,
                   barge_band=None, fascia_part=None, barge_part=None):
        """fascia_part: a Part for the fascia boards instead of paint/frame (e.g. a pattern).
        barge_part: a paint-band Part for painted bargeboards instead of self.paint (e.g. a
        'paint_glow' trim Part that keeps them readable under the site's moonlight)."""
        cover = cover or self.roof
        self.roof = cover
        self.battens = []
        for sl in self.slopes:
            if deck:
                cp.roof_deck(self.wood, sl, tint=self.inner_tint)
            if cover == "shingles":
                cp.shingles(self.roofp, sl, tint=self.roof_tint, sw=self.shingle_size[0],
                            expo=self.shingle_size[1], sh=self.shingle_size[1] * 2.1)
            elif cover == "boards":
                self.battens.append(cp.board_roof(self.roofp, sl, tint=self.roof_tint))
            if barge:
                if barge_band:
                    B = sl.basis()
                    for a in (sl.a0 - 0.015, sl.a1 + 0.015):
                        p = sl.point(a, sl.L / 2, -0.01)
                        (barge_part or self.paint).mbox(Matrix.Translation(p) @ B, (0.03, sl.L + 0.02, 0.18),
                                                        grain=1, band=barge_band)
                else:
                    cp.barge_boards(self.frame, sl, tint=self.frame_tint)
            if fascia_part is not None:
                cp.fascia(fascia_part, sl)
            else:
                cp.fascia(self.paint if fascia_band else self.frame, sl, band=fascia_band, tint=self.frame_tint)
        if ridge_cap:
            L = (self.W if self.ridge_axis == 'x' else self.D) + 2 * self.ov_gable + 0.06
            for sl in self.slopes:
                p = sl.point((sl.a0 + sl.a1) / 2, sl.L - 0.06, 0.05)
                self.roofp.mbox(Matrix.Translation(p) @ sl.basis(), (L, 0.16, 0.03), grain=0,
                                tint=self.roof_tint)

    def build_snow(self, start=0, **kw):
        """Thin, patchy snow caps (snow_<n>); kw go to carpentry.snow_cap (cover, thick, ...)."""
        for i, sl in enumerate(self.slopes):
            p = Part(f"snow_{start + i}", "snow", var=0.02)
            opts = {}
            if self.roof == "shingles":      # one strip per course; every shingle row shows
                opts = dict(courses=(self.shingle_size[1], -0.03), thick=0.024, base=0.034)
            elif self.roof == "boards":      # the snow drapes over the cover battens as soft ridges
                opts = dict(thick=0.022, base=0.036)
                if i < len(getattr(self, "battens", [])):
                    opts.update(ridges=self.battens[i], ridge_cover=0.006, ridge_soft=0.07)
            opts.update(kw)
            cp.snow_cap(p, sl, seed=i * 3.7 + start + len(self.key) * 1.3, **opts)
            self.snow.append(p)

    def eave_bulbs(self, sides=None, sag=0.05, extra_anchors=None):
        """Bulb string under the front eave (and down the gable edges when sides)."""
        sides = self.bulbs_sides if sides is None else sides
        if self.ridge_axis == 'x':
            sl = self.front_slope
            y = sl.point(0, 0).y - 0.02
            z = sl.point(0, 0, -0.08).z
            xa, xb = sl.a0 + 0.05, sl.a1 - 0.05
            anchors = [(xa + (xb - xa) * i / 4, y, z) for i in range(5)]
            cp.bulb_string(self.bulbs, self.wire, anchors, sag=sag, spacing=self.bulb_spacing,
                           seg=self.bulb_detail[0], rings=self.bulb_detail[1])
            if sides:
                for a in (sl.a0 - 0.02, sl.a1 + 0.02):
                    pts = [sl.point(a, s, -0.06) for s in (0.05, sl.L * 0.5, sl.L - 0.05)]
                    cp.bulb_string(self.bulbs, self.wire, pts, sag=0.03, spacing=self.bulb_spacing,
                           seg=self.bulb_detail[0], rings=self.bulb_detail[1])
        else:
            # front gable: follow both rake edges up to the apex
            for sl in self.slopes:
                a = sl.a0 - 0.03 if sl.A.y > 0 else sl.a1 + 0.03
                pts = [sl.point(a, s, -0.07) for s in (0.02, sl.L * 0.35, sl.L * 0.7, sl.L - 0.02)]
                cp.bulb_string(self.bulbs, self.wire, pts, sag=0.035, spacing=self.bulb_spacing,
                           seg=self.bulb_detail[0], rings=self.bulb_detail[1])
            if sides:
                for sl in self.slopes:
                    pts = [sl.point(a, -0.02, -0.08) for a in (sl.a0 + 0.1, 0, sl.a1 - 0.1)]
                    cp.bulb_string(self.bulbs, self.wire, pts, sag=0.05, spacing=self.bulb_spacing,
                           seg=self.bulb_detail[0], rings=self.bulb_detail[1])
        if extra_anchors:
            cp.bulb_string(self.bulbs, self.wire, extra_anchors, sag=sag, spacing=self.bulb_spacing,
                           seg=self.bulb_detail[0], rings=self.bulb_detail[1])

    def interior_bulbs(self, xs=(-0.9, 0.0, 0.9), y=0.1, z=None):
        z = z or self.eave - 0.35
        for x in xs:
            top = Vector((x, y, self.eave - 0.02))
            bot = Vector((x, y, z))
            self.wire.tube([top, bot], 0.004, tseg=4)
            self.wire.cyl(bot + Vector((0, 0, -0.02)), 0.02, 0.018, 0.05, seg=10)
            self.bulbs.sphere(bot + Vector((0, 0, -0.09)), 0.045, seg=10 if not state.lite() else 6,
                              rings=6 if not state.lite() else 4, scale=(1, 1, 1.3))

    def sign_lamps(self, xs, y, z_top, reach=0.3):
        """Gooseneck lamps above a sign: iron arm reaching forward, a small shade, a bulb."""
        for x in xs:
            a = Vector((x, y + 0.02, z_top - 0.02))
            b = Vector((x, y - reach, z_top + 0.14))
            self.iron.slab(a, a + Vector((0, 0, 0.16)), 0.018, 0.018, up=(1, 0, 0), bevel=0)
            self.iron.slab(a + Vector((0, 0, 0.16)), b, 0.016, 0.016, up=(1, 0, 0), bevel=0)
            self.iron.cyl(b + Vector((0, 0, -0.03)), 0.02, 0.07, 0.07, seg=10, caps=False,
                          rot=(math.radians(-25), 0, 0))
            self.bulbs.sphere(b + Vector((0, 0.01, -0.07)), 0.028, seg=8, rings=6)

    def markers(self, sign_pos, lights, cam_dist=3.4, cam_h=1.75, extra=None):
        yF = self.yF
        export.stall_markers(
            counter_top=COUNTER_TOP, counter_y=self.counter_y,
            shelf_1=(0, self.shelf_y, self.shelves[0]), shelf_2=(0, self.shelf_y, self.shelves[1]),
            vendor=(0, (self.yB - 0.35 + yF + self.counter_depth - self.counter_over) / 2, 0.13),
            sign=sign_pos, front=(0, yF - self.counter_over - 0.9, 0.0),
            cam_view=(0, yF - cam_dist, cam_h), cam_target=(0, yF + 0.35, 1.4), lights=lights)

    # -------------------------------------------------------------- finish
    def finish(self):
        objs = []
        for p in [self.wood, self.frame, self.counter, self.roofp, self.paint, self.iron, self.bulbs, self.wire, self.fir,
                  *self.beads.values(), *self.extra, *self.snow]:
            ob = p.finish()
            if ob is not None:
                objs.append(ob)
        return objs


def report_tris(objs):
    t = 0
    for o in objs:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            n = len(o.data.loop_triangles)
            t += n
            print(f"   {o.name:28s} {n:6d}")
    print(f"   {'TOTAL':28s} {t:6d}")
    return t
