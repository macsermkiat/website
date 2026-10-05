"""Round 10 (Mac, 2026-10-05: "Beer stand should have more beer bottle decorated on shelf (non-interactive)"):
decorative beer bottles for the Bierstand's back shelves, all merged into a set's static mesh (no act_ nodes,
no items.json entries).

Kinds, each standing on its base (origin), its label facing -Y (the lane):
    euro       the brown or green 0.5 l Euro bottle (NRW) with a crown cap, body and neck label
    longneck   a taller 0.5 l Weißbier bottle with a crown cap
    buegel     a swing-top Bügelflasche: porcelain stopper, wire bail, an oval label
    stein      a salt-glazed stoneware Steinkrug bottle: cream body with the brewery's cobalt stamp, the
               shoulder and neck dipped in brown glaze, a cork under a white stopper

The bottles stand against the stall's back wall, so only their front is ever seen. Each body is lathed over the
front 240 degrees only (BACK_ARC_OPEN): it reads as a 9-sided bottle from the lane for two thirds of the
triangles. Their tops (cap, stopper) are closed discs, since the lower shelf's tops are seen from above. Glass is
opaque glossy (vendor_glaze): a full, dark beer bottle shows no depth anyway, and opaque bottles cost the engine
no transparency sorting. Labels are the print atlas's pr_beer_<brewery> regions (atlas_labels.py)."""
import math

from mathutils import Matrix

import vlib
from vlib import C, T, WHITE, jit, lite, seg

TWO_PI = 2 * math.pi
ARC = TWO_PI * 2 / 3                 # the front two thirds of a bottle body
A0 = -math.pi / 2 - ARC / 2          # centred on -Y

GLASS = {"brown": C("3a1806"), "amber": C("5a2a08"), "green": C("173f1c"), "dark_green": C("0f2a14")}
CAPS = {"nachtmarkt": C("c8a040"), "kloster": C("2a4a2a"), "tannenhof": C("e8e4da"), "sternwirt": C("2a4a8a"),
        "laterne": C("b0281a"), "eichwald": C("8a2a18")}

PROFILES = {
    # (r, z) of the glass, bottom to the top of the glass under the cap
    "euro": [(0.0300, 0.0), (0.0305, 0.135), (0.0240, 0.165), (0.0145, 0.192), (0.0135, 0.222)],
    "longneck": [(0.0300, 0.0), (0.0305, 0.150), (0.0255, 0.176), (0.0150, 0.206), (0.0135, 0.246)],
    "buegel": [(0.0315, 0.0), (0.0320, 0.13), (0.0255, 0.158), (0.0165, 0.186), (0.0172, 0.214)],
}
LABEL_Z = {"euro": (0.035, 0.105), "longneck": (0.04, 0.118), "buegel": (0.035, 0.1)}
NECK_Z = {"euro": (0.196, 0.212), "longneck": (0.215, 0.232)}


def _r_at(prof, z):
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return prof[-1][0]


def _n():
    return seg(5, 4)                  # facets over the 240 degree front (48 degrees each: a smooth-shaded 7.5-gon)


def bottle(m, M, kind="euro", brewery="nachtmarkt", glass="brown", z_from=0.0, neck_label=True, back=False):
    """One decorative bottle into mesh m. z_from > 0 builds only the part above that height (a bottle standing
    in a crate shows only its top). back=True (round 10 pass 2): a back-row bottle, half hidden behind the front
    row, with 4 facets over the front and no neck label (about 46 triangles instead of about 64)."""
    M = M or Matrix()
    if kind == "stein":
        return stein_bottle(m, M, brewery)
    prof = PROFILES[kind]
    if z_from > 0:
        rest = [p for p in prof if p[1] > z_from]
        if rest and rest[0][1] - z_from < 0.012:
            rest = rest[1:]           # a sliver of a band just above the crate's side: not worth its triangles
        prof = [(_r_at(prof, z_from), z_from)] + rest
    n = seg(4, 4) if back else _n()
    col = jit(GLASS[glass], 0.08)
    m.lathe(prof, n, "sw_vgloss", M, col, "glaze", v_by="z", arc=ARC, u0=A0)
    top = prof[-1][1]
    if kind == "buegel":
        # porcelain stopper with a red rubber ring, a wire bail from the neck bead over it, the lever on the side
        # (round 10: a red rubber ring painted as the stopper's lowest band, via its own vertex colour row)
        m.lathe([(0.0158, top), (0.0158, top + 0.003)], _n(), "sw_satin", M, C("a8281c"), arc=ARC, u0=A0)
        m.lathe([(0.0152, top + 0.003), (0.0128, top + 0.016)], seg(6, 5), "ceramic", M, C("f2eee6"), "glaze")
        m.disc(0.0128, seg(6, 5), "ceramic", M @ T(0, 0, top + 0.016), C("f2eee6"), "glaze")
        for sx in (-1, 1):
            # the wire bail's two legs (front faces only: a thin strip each)
            m.quad([(sx * 0.0178 - 0.0008, -0.004, top - 0.02), (sx * 0.0178 + 0.0008, -0.004, top - 0.02),
                    (sx * 0.0168 + 0.0008, -0.004, top + 0.012), (sx * 0.0168 - 0.0008, -0.004, top + 0.012)],
                   "sw_metal_rough", C("8a8a88"), "atlas", M)
    else:
        # crown cap: a short fluted skirt (one band) and its top
        cap = CAPS.get(brewery, C("c8a040"))
        r = prof[-1][0] + 0.0013
        # (round 10 pass 2: 3 facets over the front, from 5: a 1.6 cm cap reads round at any shelf distance)
        m.lathe([(r, top - 0.001), (r, top + 0.008)], 3, "sw_metal", M, cap, "atlas", arc=ARC, u0=A0)
        m.disc(r, seg(6, 5), "sw_metal", M @ T(0, 0, top + 0.008), cap, "atlas")
    # body label over the front
    lz = LABEL_Z[kind]
    if z_from < lz[0]:
        la = TWO_PI * (0.3 if kind == "buegel" else 0.36)
        band = [(_r_at(PROFILES[kind], z) + 0.0008, z) for z in lz]
        m.lathe(band, seg(3, 2), f"pr_beer_{brewery}", M, WHITE, "print", v_by="z", arc=la, u0=-math.pi / 2 - la / 2)
    if neck_label and not back and kind in NECK_Z and not lite():
        nz = NECK_Z[kind]
        na = TWO_PI * 0.42
        band = [(_r_at(PROFILES[kind], z) + 0.0007, z) for z in nz]
        m.lathe(band, 3, f"pr_beerneck_{brewery}", M, WHITE, "print", v_by="z", arc=na, u0=-math.pi / 2 - na / 2)


def stein_bottle(m, M, brewery="eichwald"):
    """A stoneware beer bottle (Steinkrug): straight cream body under the cobalt stamp band, a brown-dipped
    rounded shoulder and neck, a cork under a white porcelain stopper."""
    n = _n()
    low = [(0.033, 0.0), (0.034, 0.118)]
    m.lathe(low, n, "pr_stoneware", M, WHITE, "print", v_by="z", arc=ARC, u0=A0)
    up = [(0.034, 0.118), (0.0335, 0.16), (0.027, 0.185), (0.016, 0.2), (0.014, 0.222), (0.0165, 0.228)]
    m.lathe(up, n, "ceramic", M, jit(C("6a3a18"), 0.08), "glaze", v_by="z", arc=ARC, u0=A0)
    m.lathe([(0.012, 0.228), (0.0125, 0.236)], seg(8, 5), "kraft", M, C("b08a5a"))
    m.disc(0.0125, seg(8, 5), "ceramic", M @ T(0, 0, 0.236), C("f2eee6"), "glaze")


def crate(m, M, cols, rows, kind, brewery, glass, brand=None, w_step=0.082, h=0.15, wood=C("a87850")):
    """A wooden beer crate of cols x rows bottles (only their tops show over the sides), a burnt-in brand on the
    front board (print atlas pr_crate_<brand>). Origin at the crate's bottom centre."""
    import goods as G
    w, d = cols * w_step + 0.03, rows * w_step + 0.03
    G.crate(m, M, w, d, h, wood, slats=1)
    if brand:
        bw, bh = min(w - 0.06, 0.26), 0.055
        m.quad([(-bw / 2, -d / 2 - 0.0015, h * 0.75 - bh / 2), (bw / 2, -d / 2 - 0.0015, h * 0.75 - bh / 2),
                (bw / 2, -d / 2 - 0.0015, h * 0.75 + bh / 2), (-bw / 2, -d / 2 - 0.0015, h * 0.75 + bh / 2)],
               f"pr_crate_{brand}", WHITE, "print", M)
    for i in range(cols):
        for j in range(rows):
            x = (i - (cols - 1) / 2) * w_step
            y = (j - (rows - 1) / 2) * w_step
            bottle(m, M @ T(x, y, 0.012), kind, brewery, glass, z_from=h - 0.02, neck_label=j == 0, back=j > 0)
    return w, d


def riser(m, M, w, d=0.075, h=0.045, wood=C("6a4a30")):
    """A plain wooden step for a back row of bottles, so their shoulders and labels show over the front row.
    Origin at its bottom centre; no bottom or back face (it stands on the shelf against the wall)."""
    import vlib as _v
    m.box((w, d, h), M @ T(0, 0, h / 2), _v.RW("wood"), jit(wood, 0.05), skip=("nz", "py"))
    return h
