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


def grime(z_clean=0.45, strength=0.35):
    """Shade function: splash grime and damp near the ground."""
    def f(p):
        t = min(1.0, max(0.0, p.z / z_clean))
        return 1.0 - strength * (1 - t) ** 1.6
    return f


class Hut:
    def __init__(self, key, W=3.6, D=2.4, eave=2.5, ridge=3.45, ridge_axis='x', ov_eave=0.38,
                 ov_gable=0.24, wall="vertical", wall_tint="honey", frame_tint="oak",
                 roof="shingles", roof_tint="shingle", inner_tint="pine", counter_tint="oak",
                 counter_depth=0.6, counter_over=0.22, shelves=(1.38, 1.78), shade=None,
                 plank_w=0.14, bulbs_sides=False, bulb_spacing=0.2, front_posts=None,
                 header_h=0.16, open_top=OPEN_TOP, wall_band=None, plank_bevel=None,
                 shingle_size=(0.19, 0.14)):
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
        self.x0, self.x1 = -W / 2, W / 2
        self.yF, self.yB = -D / 2, D / 2
        self.front_posts = front_posts or [self.x0 + 0.05, self.x1 - 0.05]
        sh = shade or grime()
        self.wood = Part(f"{key}_wood", "wood", shade=sh)
        self.frame = Part(f"{key}_frame", "wood", shade=sh, bevel=0.007)
        self.roofp = Part(f"{key}_roof", "wood", shade=None)
        self.paint = Part(f"{key}_paint", "paint", shade=sh, var=0.04)
        self.iron = Part(f"{key}_iron", "iron")
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
                              lambda c: self.top_at('x', c), axis='x', at=yF + 0.03, pw=pw, tint=wt, var=0.12,
                              band=self.wall_band)

    def _wall(self, axis, a, b, at, top, outward, z0=0.1):
        if self.wall == "lap":
            zmax = max(top(a), top((a + b) / 2), top(b))
            if axis == 'x' and self.ridge_axis == 'y' or axis == 'y' and self.ridge_axis == 'x':
                # gable wall: lap boards up to eave, vertical boards in the gable triangle
                cp.lap_siding(self.wood, a, b, z0, min(zmax, self.eave - 0.05), axis=axis, at=at,
                              outward=outward, tint=self.wall_tint, var=0.12, bevel=self.plank_bevel)
                if zmax > self.eave:
                    cp.plank_wall(self.wood, a, b, self.eave - 0.08, top, axis=axis, at=at,
                                  pw=self.plank_w, tint=self.wall_tint, var=0.12, bevel=self.plank_bevel)
            else:
                cp.lap_siding(self.wood, a, b, z0, zmax, axis=axis, at=at, outward=outward,
                              tint=self.wall_tint, var=0.12, bevel=self.plank_bevel)
            # inner lining so gaps never show daylight
            self._lining(axis, a, b, at - outward * 0.03, top, z0)
        else:
            wp = self.paint if self.wall_band else self.wood
            cp.plank_wall(wp, a, b, z0, top, axis=axis, at=at, pw=self.plank_w,
                          tint=None if self.wall_band else self.wall_tint, var=0.13 if not self.wall_band else 0.05,
                          band=self.wall_band, bevel=self.plank_bevel)
            if self.wall == "batten":
                pos = a + self.plank_w
                while pos < b - 0.05:
                    t = top(pos)
                    h = t - z0 - 0.02
                    if axis == 'x':
                        self.wood.box((pos, at + outward * 0.02, z0 + h / 2), (0.045, 0.02, h),
                                      tint=self.wall_tint, grain=2, bevel=self.plank_bevel)
                    else:
                        self.wood.box((at + outward * 0.02, pos, z0 + h / 2), (0.02, 0.045, h),
                                      tint=self.wall_tint, grain=2, bevel=self.plank_bevel)
                    pos += self.plank_w * 1.02
            self._lining(axis, a, b, at - outward * 0.028, top, z0)

    def _lining(self, axis, a, b, at, top, z0):
        """Cheap inner skin: one board per 0.6 m, darker, only to close the wall visually."""
        pos = a
        while pos < b - 1e-3:
            w = min(0.6, b - pos)
            c = pos + w / 2
            t = min(top(pos + 0.02), top(pos + w - 0.02)) - 0.02
            h = t - z0
            if axis == 'x':
                self.wood.box((c, at, z0 + h / 2), (w, 0.012, h), tint=self.inner_tint, var=0.05, grain=2, bevel=0)
            else:
                self.wood.box((at, c, z0 + h / 2), (0.012, w, h), tint=self.inner_tint, var=0.05, grain=2, bevel=0)
            pos += w

    def build_counter(self, x0=None, x1=None, brackets=4, front_band=None):
        """Counter top exactly at COUNTER_TOP, overhanging to the front, on brackets."""
        x0 = self.x0 + 0.1 if x0 is None else x0
        x1 = self.x1 - 0.1 if x1 is None else x1
        yF = self.yF
        th = 0.05
        y_front = yF - self.counter_over
        y_back = y_front + self.counter_depth
        # three thick boards along X
        n = 3
        bw = (y_back - y_front) / n
        for i in range(n):
            self.frame.box(((x0 + x1) / 2 + state.rng.uniform(-0.01, 0.01), y_front + (i + 0.5) * bw,
                            COUNTER_TOP - th / 2), (x1 - x0 + 0.06, bw - 0.004, th),
                           tint=self.counter_tint, grain=0, bevel=0.006, bevel_segments=2, var=0.1)
        # front edge lip board
        self.frame.box(((x0 + x1) / 2, y_front - 0.012, COUNTER_TOP - 0.06), (x1 - x0 + 0.08, 0.024, 0.09),
                       tint=self.counter_tint, grain=0, band=front_band)
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
                   barge_band=None):
        cover = cover or self.roof
        for sl in self.slopes:
            if deck:
                cp.roof_deck(self.wood, sl, tint=self.inner_tint)
            if cover == "shingles":
                cp.shingles(self.roofp, sl, tint=self.roof_tint, sw=self.shingle_size[0],
                            expo=self.shingle_size[1], sh=self.shingle_size[1] * 2.1)
            elif cover == "boards":
                cp.board_roof(self.roofp, sl, tint=self.roof_tint)
            if barge:
                if barge_band:
                    B = sl.basis()
                    for a in (sl.a0 - 0.015, sl.a1 + 0.015):
                        p = sl.point(a, sl.L / 2, -0.01)
                        self.paint.mbox(Matrix.Translation(p) @ B, (0.03, sl.L + 0.02, 0.18), grain=1,
                                        band=barge_band)
                else:
                    cp.barge_boards(self.frame, sl, tint=self.frame_tint)
            cp.fascia(self.paint if fascia_band else self.frame, sl, band=fascia_band, tint=self.frame_tint)
        if ridge_cap:
            L = (self.W if self.ridge_axis == 'x' else self.D) + 2 * self.ov_gable + 0.06
            for sl in self.slopes:
                p = sl.point((sl.a0 + sl.a1) / 2, sl.L - 0.06, 0.05)
                self.roofp.mbox(Matrix.Translation(p) @ sl.basis(), (L, 0.16, 0.03), grain=0,
                                tint=self.roof_tint)

    def build_snow(self, start=0):
        for i, sl in enumerate(self.slopes):
            p = Part(f"snow_{start + i}", "snow", var=0.02)
            cp.snow_cap(p, sl, seed=i * 3.7 + start)
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
            cp.bulb_string(self.bulbs, self.wire, anchors, sag=sag, spacing=self.bulb_spacing)
            if sides:
                for a in (sl.a0 - 0.02, sl.a1 + 0.02):
                    pts = [sl.point(a, s, -0.06) for s in (0.05, sl.L * 0.5, sl.L - 0.05)]
                    cp.bulb_string(self.bulbs, self.wire, pts, sag=0.03, spacing=self.bulb_spacing)
        else:
            # front gable: follow both rake edges up to the apex
            for sl in self.slopes:
                a = sl.a0 - 0.03 if sl.A.y > 0 else sl.a1 + 0.03
                pts = [sl.point(a, s, -0.07) for s in (0.02, sl.L * 0.35, sl.L * 0.7, sl.L - 0.02)]
                cp.bulb_string(self.bulbs, self.wire, pts, sag=0.035, spacing=self.bulb_spacing)
            if sides:
                for sl in self.slopes:
                    pts = [sl.point(a, -0.02, -0.08) for a in (sl.a0 + 0.1, 0, sl.a1 - 0.1)]
                    cp.bulb_string(self.bulbs, self.wire, pts, sag=0.05, spacing=self.bulb_spacing)
        if extra_anchors:
            cp.bulb_string(self.bulbs, self.wire, extra_anchors, sag=sag, spacing=self.bulb_spacing)

    def interior_bulbs(self, xs=(-0.9, 0.0, 0.9), y=0.1, z=None):
        z = z or self.eave - 0.35
        for x in xs:
            top = Vector((x, y, self.eave - 0.02))
            bot = Vector((x, y, z))
            self.wire.tube([top, bot], 0.004, tseg=4)
            self.wire.cyl(bot + Vector((0, 0, -0.02)), 0.02, 0.018, 0.05, seg=10)
            self.bulbs.sphere(bot + Vector((0, 0, -0.09)), 0.045, seg=12, rings=8, scale=(1, 1, 1.3))

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
        for p in [self.wood, self.frame, self.roofp, self.paint, self.iron, self.bulbs, self.wire, self.fir,
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
