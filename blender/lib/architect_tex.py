"""Architect's texture generators: tileable PBR textures made in numpy.

Every generator returns a dict of float arrays in 0..1:
  color (H,W,3, linear-ish sRGB values to be saved as sRGB), rough (H,W), height (H,W),
  and optionally alpha / emit.  normal maps are derived with normal_from_height().
All textures tile seamlessly (periodic noise, wrap-around distance transforms).
"""
import numpy as np
from scipy import ndimage

# ------------------------------------------------------------------ basics

def rng(seed):
    return np.random.default_rng(seed)


def pnoise(n, cells, octaves=4, persistence=0.5, seed=0, m=None):
    """Periodic value noise on an n x m grid, base frequency `cells` per tile. Returns 0..1."""
    m = m or n
    r = rng(seed)
    out = np.zeros((n, m))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = int(cells * 2 ** o)
        cy = max(2, int(round(c * n / m))) if m != n else c
        g = r.random((cy, c))
        z = ndimage.zoom(g, (n / cy, m / c), order=3, mode="grid-wrap", grid_mode=True)
        out += amp * z[:n, :m]
        tot += amp
        amp *= persistence
    out /= tot
    lo, hi = np.percentile(out, 0.5), np.percentile(out, 99.5)
    return np.clip((out - lo) / (hi - lo + 1e-9), 0, 1)


def stretched_noise(n, cells_u, cells_v, octaves=3, seed=0):
    """Periodic noise with different frequencies along u (x) and v (y)."""
    r = rng(seed)
    out = np.zeros((n, n)); amp = 1; tot = 0
    for o in range(octaves):
        cu, cv = int(cells_u * 2 ** o), int(cells_v * 2 ** o)
        g = r.random((max(cv, 2), max(cu, 2)))
        z = ndimage.zoom(g, (n / g.shape[0], n / g.shape[1]), order=3, mode="grid-wrap", grid_mode=True)
        out += amp * z[:n, :n]; tot += amp; amp *= 0.5
    out /= tot
    lo, hi = out.min(), out.max()
    return (out - lo) / (hi - lo + 1e-9)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def wrap_edt(mask):
    """Euclidean distance (pixels) to nearest True pixel of `mask`, periodic."""
    h, w = mask.shape
    big = np.tile(~mask, (3, 3))
    d = ndimage.distance_transform_edt(big)
    return d[h:2 * h, w:2 * w]


def id_edges(ids):
    """True where an id differs from a 4-neighbour (periodic)."""
    e = np.zeros(ids.shape, bool)
    for ax in (0, 1):
        for s in (1, -1):
            e |= ids != np.roll(ids, s, axis=ax)
    return e


def hash01(ids, salt=0):
    """Deterministic pseudo-random 0..1 per integer id."""
    x = (ids.astype(np.int64) * 2654435761 + salt * 97531) & 0xFFFFFFFF
    x = (x ^ (x >> 15)) * 2246822519 & 0xFFFFFFFF
    x = (x ^ (x >> 13)) * 3266489917 & 0xFFFFFFFF
    x = x ^ (x >> 16)
    return (x & 0xFFFFFF) / float(0xFFFFFF)


def normal_from_height(h, strength):
    """Tangent-space normal map (0..1) from a periodic height map; strength in height-units per pixel."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    # image row 0 is the top (v=1) in Blender, so +y in image rows is -v
    nx, ny, nz = -dx, dy, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5], -1)


def palette_pick(t, cols, weights=None):
    """t: 0..1 array -> colour from a weighted list of RGB tuples."""
    cols = np.array(cols, float)
    w = np.array(weights if weights is not None else [1] * len(cols), float)
    cw = np.cumsum(w) / w.sum()
    idx = np.searchsorted(cw, np.clip(t, 0, 0.99999))
    return cols[idx]


def warp_coords(n, amount_px, cells, seed):
    wx = (pnoise(n, cells, 3, 0.5, seed) - 0.5) * 2 * amount_px
    wy = (pnoise(n, cells, 3, 0.5, seed + 1) - 0.5) * 2 * amount_px
    return wx, wy


def stone_finish(ids, n, px_per_m, round_m, seed, height_var=0.25, tilt=0.35, joint_w_m=0.008):
    """Shared treatment for stones given an id map: joints, rounded tops, per-stone tilt."""
    edges = id_edges(ids)
    edges = ndimage.binary_dilation(edges, iterations=max(1, int(joint_w_m * px_per_m / 2)))
    d = wrap_edt(edges) / px_per_m                     # metres to the joint
    prof = smoothstep(0.0, round_m, d)
    prof = np.sqrt(prof)                               # domed, worn tops
    hv = hash01(ids, 1)
    yy, xx = np.mgrid[0:n, 0:n] / px_per_m
    ta, tb = (hash01(ids, 2) - 0.5) * tilt, (hash01(ids, 3) - 0.5) * tilt
    # tilt relative to a per-stone local origin (use sin to stay periodic-safe)
    tiltf = ta * np.sin(xx * 9.0 + hv * 6.28) * 0.02 + tb * np.cos(yy * 9.0 + hv * 3.1) * 0.02
    h = prof * (1.0 - height_var + height_var * hv) + tiltf
    return h, d, edges


# ------------------------------------------------------------------ cobbles (fan pattern, Segmentbogenpflaster)

def cobble_fan(n=1024, tile_m=3.2, seed=11):
    px = n / tile_m
    r = rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    wx, wy = warp_coords(n, 0.018 * px, 10, seed + 5)
    hx, hy = warp_coords(n, 0.007 * px, 48, seed + 6)   # small-scale wobble: no two stones share a shape
    X = (xx + wx + hx) / px; Y = (yy + wy + hy) / px  # metres
    W, H = 1.6, 0.8                                   # arch width and row step (tile holds 2 x 4)
    Rs = 1.45                                         # arc radius; fields are circle j minus the circles below
    s = 0.092                                         # course width (stone size across the arc)
    X = X % tile_m; Y = Y % tile_m
    best_row = np.full((n, n), 1e9); best = np.zeros((n, n), np.int64)
    loc_d = np.zeros((n, n)); loc_a = np.zeros((n, n))
    rows = int(round(tile_m / H)); cols = int(round(tile_m / W))
    for j in range(-3, rows + 3):
        for i in range(-2, cols + 3):
            cx = i * W + (j % 2) * W / 2
            cy = j * H
            dx = X - cx; dy = Y - cy
            d = np.sqrt(dx * dx + dy * dy)
            inside = d < Rs
            upd = inside & (cy < best_row)             # lowest covering circle wins
            best_row[upd] = cy
            best[upd] = ((j % rows) * cols + (i % cols))
            loc_d[upd] = d[upd]
            loc_a[upd] = np.arctan2(dx[upd], dy[upd])
    ring = np.floor((Rs - loc_d) / s).astype(np.int64)
    rr = np.maximum(loc_d, 0.05)
    phase = hash01(best * 131 + ring, 7)
    length = s * (1.05 + 0.35 * hash01(best * 131 + ring, 8))
    along = rr * loc_a / length + phase * 3.0
    k = np.floor(along).astype(np.int64)
    ids = best * 100000 + ring * 1000 + (k + 500)
    h, dj, edges = stone_finish(ids, n, px, 0.03, seed, height_var=0.3, tilt=0.5)
    fine = pnoise(n, 64, 3, 0.55, seed + 9)
    h = h + 0.05 * fine * (dj > 0.004)
    # stone colours: granite greys, some blue basalt, some warm porphyry
    t = hash01(ids, 11)
    base = palette_pick(t, [(0.36, 0.35, 0.34), (0.30, 0.30, 0.31), (0.42, 0.40, 0.37), (0.23, 0.24, 0.27),
                             (0.40, 0.33, 0.29), (0.47, 0.45, 0.42), (0.19, 0.19, 0.20)],
                        [5, 5, 4, 3, 2, 2, 1])
    lum = 0.82 + 0.3 * hash01(ids, 12)
    speck = pnoise(n, 180, 2, 0.6, seed + 13)
    col = base * lum[..., None] * (0.8 + 0.4 * speck[..., None])
    # worn polish: tops slightly lighter, low-frequency grime
    grime = pnoise(n, 3, 4, 0.55, seed + 21)
    col *= (0.82 + 0.3 * grime)[..., None]
    joint_col = np.array([0.075, 0.068, 0.06])
    jm = 1 - smoothstep(0.0, 0.012, dj)
    col = col * (1 - jm[..., None]) + joint_col * jm[..., None]
    # moss / dark sand in some joints
    moss = (pnoise(n, 6, 3, 0.5, seed + 30) > 0.72) * jm
    col = col * (1 - 0.6 * moss[..., None]) + np.array([0.05, 0.07, 0.035]) * 0.6 * moss[..., None]
    rough = 0.42 + 0.22 * hash01(ids, 14) - 0.18 * smoothstep(0.02, 0.05, dj) + 0.1 * speck
    rough = np.where(jm > 0.5, 0.3, rough)            # wet joints
    rough = np.clip(rough - 0.12 * (grime < 0.35), 0.12, 0.9)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ setts in rows (Reihenpflaster), gutters, streets

def setts(n=1024, tile_m=2.4, row_m=0.12, len_range=(0.11, 0.19), seed=21, warm=False):
    px = n / tile_m
    r = rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    wx, wy = warp_coords(n, 0.012 * px, 12, seed + 3)
    X = ((xx + wx) / px) % tile_m; Y = ((yy + wy) / px) % tile_m
    nrows = int(round(tile_m / row_m)); rh = tile_m / nrows
    row = np.floor(Y / rh).astype(np.int64) % nrows
    ids = np.zeros((n, n), np.int64)
    for j in range(nrows):
        lens = []
        tot = 0
        while tot < tile_m:
            l = r.uniform(*len_range); lens.append(l); tot += l
        lens = np.array(lens) * tile_m / tot
        edges = np.concatenate([[0], np.cumsum(lens)])
        off = r.uniform(0, tile_m)
        m = row == j
        u = (X[m] + off) % tile_m
        k = np.searchsorted(edges, u, side="right") - 1
        ids[m] = j * 1000 + k
    h, dj, _ = stone_finish(ids, n, px, 0.025, seed, height_var=0.3, tilt=0.4)
    fine = pnoise(n, 48, 3, 0.55, seed + 9)
    h = h + 0.05 * fine
    t = hash01(ids, 11)
    if warm:
        pal = [(0.44, 0.41, 0.37), (0.38, 0.36, 0.33), (0.50, 0.47, 0.42), (0.33, 0.31, 0.29)]
    else:
        pal = [(0.33, 0.33, 0.34), (0.28, 0.28, 0.30), (0.39, 0.38, 0.36), (0.22, 0.22, 0.24), (0.36, 0.31, 0.28)]
    base = palette_pick(t, pal)
    speck = pnoise(n, 160, 2, 0.6, seed + 13)
    col = base * (0.8 + 0.3 * hash01(ids, 12))[..., None] * (0.8 + 0.4 * speck[..., None])
    grime = pnoise(n, 3, 4, 0.55, seed + 21)
    col *= (0.82 + 0.3 * grime)[..., None]
    jm = 1 - smoothstep(0.0, 0.01, dj)
    col = col * (1 - jm[..., None]) + np.array([0.07, 0.065, 0.058]) * jm[..., None]
    rough = np.clip(0.45 + 0.2 * hash01(ids, 14) - 0.15 * smoothstep(0.015, 0.04, dj) + 0.1 * speck, 0.15, 0.9)
    rough = np.where(jm > 0.5, 0.3, rough)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ granite (curbs, bollard stone)

def granite(n=512, seed=31):
    a = pnoise(n, 90, 2, 0.6, seed); b = pnoise(n, 30, 3, 0.5, seed + 1); c = pnoise(n, 4, 3, 0.5, seed + 2)
    col = np.array([0.40, 0.39, 0.37]) * (0.75 + 0.35 * b)[..., None]
    dark = (a > 0.72)[..., None]
    col = np.where(dark, col * 0.35, col)
    light = (a < 0.18)[..., None]
    col = np.where(light, col * 1.35, col)
    col *= (0.85 + 0.2 * c)[..., None]
    rough = np.clip(0.55 + 0.2 * b - 0.15 * c, 0.2, 0.9)
    h = 0.6 * b + 0.4 * a
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ plaster (neutral, tinted per house with a factor)

def plaster(n=1024, seed=41):
    lo = pnoise(n, 3, 5, 0.55, seed)
    mid = pnoise(n, 14, 4, 0.5, seed + 1)
    trowel = stretched_noise(n, 30, 9, 3, seed + 2)
    fine = pnoise(n, 200, 2, 0.6, seed + 3)
    drips = stretched_noise(n, 40, 2, 2, seed + 4)
    v = 0.86 + 0.08 * (lo - 0.5) + 0.05 * (mid - 0.5) + 0.03 * (fine - 0.5)
    stain = smoothstep(0.62, 0.95, drips) * smoothstep(0.35, 0.8, lo)
    v = v - 0.12 * stain
    col = np.stack([v, v * 0.985, v * 0.96], -1)
    # patched areas, a few hairline cracks
    patch = smoothstep(0.78, 0.82, pnoise(n, 5, 2, 0.5, seed + 5))
    col = col * (1 - 0.05 * patch[..., None])
    crack_n = pnoise(n, 7, 4, 0.5, seed + 6)
    crack = np.exp(-((crack_n - 0.5) / 0.004) ** 2) * smoothstep(0.7, 0.9, pnoise(n, 3, 2, 0.5, seed + 7))
    col = col * (1 - 0.35 * crack[..., None])
    h = 0.5 * mid + 0.3 * trowel + 0.2 * fine - 0.5 * crack
    rough = np.clip(0.82 + 0.1 * (fine - 0.5) - 0.1 * stain, 0.5, 0.95)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ timber (aged oak beams, grain along u)

def timber(n=512, seed=51):
    grain = stretched_noise(n, 3, 60, 4, seed)
    rings = np.sin(grain * 40.0) * 0.5 + 0.5
    lo = pnoise(n, 3, 3, 0.5, seed + 1)
    checks_n = stretched_noise(n, 2, 18, 3, seed + 2)
    checks = np.exp(-((checks_n - 0.5) / 0.006) ** 2) * (pnoise(n, 4, 2, 0.5, seed + 3) > 0.5)
    adze = stretched_noise(n, 10, 5, 2, seed + 4)
    v = 0.5 + 0.18 * (rings - 0.5) + 0.2 * (lo - 0.5) + 0.1 * (adze - 0.5)
    base = np.array([0.30, 0.20, 0.13])
    col = base * (0.6 + 0.8 * v)[..., None]
    col = col * (1 - 0.75 * checks[..., None])
    h = 0.4 * rings + 0.4 * adze - 0.8 * checks
    rough = np.clip(0.72 + 0.12 * (v - 0.5), 0.4, 0.95)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


def painted_wood(n=512, seed=61, boards=5):
    grain = stretched_noise(n, 60, 3, 3, seed)       # grain along v (boards vertical)
    xx = np.mgrid[0:n, 0:n][1] / n
    bpos = (xx * boards) % 1.0
    groove = np.exp(-((bpos - 0.0) / 0.012) ** 2) + np.exp(-((bpos - 1.0) / 0.012) ** 2)
    chip = smoothstep(0.8, 0.83, pnoise(n, 16, 4, 0.6, seed + 1)) * smoothstep(0.45, 0.7, pnoise(n, 3, 2, 0.5, seed + 5))
    lo = pnoise(n, 3, 3, 0.5, seed + 2)
    paint = 0.82 + 0.06 * (lo - 0.5) + 0.04 * (grain - 0.5)
    col = np.stack([paint] * 3, -1)
    wood = np.array([0.32, 0.27, 0.22]) * (0.8 + 0.4 * grain)[..., None]
    col = col * (1 - chip[..., None]) + wood * chip[..., None]
    col *= (1 - 0.6 * groove)[..., None]
    h = 0.3 * grain - 1.0 * groove - 0.2 * chip
    rough = np.clip(0.55 + 0.3 * chip + 0.05 * grain, 0.3, 0.95)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ roof tiles (Biberschwanz) and slate

def roof_tiles(n=1024, tile_w_m=2.16, tile_h_m=2.10, cols=12, rows=14, seed=71, slate=False):
    """Beaver-tail clay tiles, staggered rows, rounded lower ends.  Texture u across the roof, v up the slope."""
    r = rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    wx, wy = warp_coords(n, 1.5, 16, seed + 1)
    U = ((xx + wx) / n) * cols                          # tile units across
    V = ((n - 1 - yy + wy) / n) * rows                  # rows up the slope
    row = np.floor(V).astype(np.int64)
    ids = np.zeros((n, n), np.int64); tpos = np.zeros((n, n))
    for dj in (0, 1):
        pass
    # rounded bottom edge: point belongs to row j if V - j >= bump_j(u); else to row j-1
    def bump(u, j):
        off = 0.5 * (j % 2)
        f = ((u + off) % 1.0) * 2 - 1
        return 0.32 * (1 - np.sqrt(np.clip(1 - f * f, 0, 1))) if not slate else 0.22 * np.abs(f)
    fv = V - row
    b = bump(U, row)
    below = fv < b
    rj = np.where(below, row - 1, row)
    col_i = np.floor(U + 0.5 * (rj % 2)).astype(np.int64)
    ids = (rj % rows) * 1000 + (col_i % cols)
    tpos = V - rj - bump(U, rj)                         # 0 at the tile's lower edge
    tpos = np.clip(tpos, 0, 2)
    px = n / cols                                        # pixels per tile width
    edges = id_edges(ids)
    d = wrap_edt(edges)
    prof = smoothstep(0, px * 0.06, d)
    h = prof * (0.6 + 0.4 * (1 - np.clip(tpos, 0, 1))) + 0.15 * hash01(ids, 3)
    t = hash01(ids, 4)
    if slate:
        pal = [(0.10, 0.11, 0.13), (0.13, 0.14, 0.16), (0.08, 0.09, 0.10), (0.15, 0.15, 0.17)]
    else:
        pal = [(0.42, 0.14, 0.07), (0.36, 0.12, 0.06), (0.48, 0.20, 0.10), (0.30, 0.10, 0.06),
               (0.40, 0.18, 0.11), (0.24, 0.09, 0.06)]
    col = palette_pick(t, pal) * (0.8 + 0.35 * hash01(ids, 5))[..., None]
    fine = pnoise(n, 120, 2, 0.6, seed + 7)
    col *= (0.85 + 0.3 * fine)[..., None]
    grime = pnoise(n, 4, 4, 0.5, seed + 8)
    col *= (0.75 + 0.35 * grime)[..., None]
    if not slate:
        moss = smoothstep(0.62, 0.8, pnoise(n, 5, 4, 0.55, seed + 9)) * (1 - np.clip(tpos, 0, 1)) ** 0.5
        col = col * (1 - 0.6 * moss[..., None]) + np.array([0.12, 0.13, 0.05]) * 0.6 * moss[..., None]
    shadow = 1 - 0.6 * np.exp(-np.clip(tpos, 0, 5) * 0.0) * (1 - prof)
    col *= shadow[..., None]
    rough = np.clip(0.7 + 0.15 * fine - (0.2 if slate else 0.0), 0.3, 0.95)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ sandstone ashlar

def sandstone(n=1024, tile_m=2.4, seed=81, red=True):
    """Ashlar masonry: courses of varied height (some thin 'Binder' courses), blocks of varied length,
    fine tooled faces, soft arrises, thin lime joints and rain streaks.  Block colour varies only a
    little so the wall reads as one stone at a distance, not as a regular brick grid."""
    px = n / tile_m
    r = rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    X = xx / px; Y = (n - 1 - yy) / px
    course_h = []
    tot = 0
    while tot < tile_m:
        c = r.uniform(0.22, 0.36) if r.random() > 0.18 else r.uniform(0.14, 0.19)
        course_h.append(c); tot += c
    course_h = np.array(course_h) * tile_m / tot
    ce = np.concatenate([[0], np.cumsum(course_h)])
    row = np.clip(np.searchsorted(ce, Y, side="right") - 1, 0, len(course_h) - 1)
    ids = np.zeros((n, n), np.int64)
    for j in range(len(course_h)):
        lens = []; t = 0
        while t < tile_m:
            l = r.uniform(0.3, 0.85) if course_h[j] > 0.2 else r.uniform(0.5, 1.1)
            lens.append(l); t += l
        lens = np.array(lens) * tile_m / t
        e = np.concatenate([[0], np.cumsum(lens)]); off = r.uniform(0, tile_m)
        m = row == j
        u = (X[m] + off) % tile_m
        ids[m] = j * 100 + np.searchsorted(e, u, side="right") - 1
    edges = id_edges(ids)
    edges = ndimage.binary_dilation(edges, iterations=1)
    d = wrap_edt(edges) / px
    prof = smoothstep(0, 0.02, d) ** 0.7                     # soft, slightly worn arrises
    tex = pnoise(n, 60, 4, 0.55, seed + 3)
    fine = pnoise(n, 180, 2, 0.5, seed + 9)
    bed = stretched_noise(n, 2, 50, 3, seed + 4)              # bedding layers in the stone
    tool = np.sin(X * 2 * np.pi / 0.012 + 3 * tex) * 0.5 + 0.5  # fine vertical tooling
    t = hash01(ids, 5)
    if red:
        pal = [(0.52, 0.30, 0.22), (0.55, 0.33, 0.24), (0.49, 0.28, 0.21), (0.57, 0.38, 0.28), (0.53, 0.35, 0.27)]
    else:
        pal = [(0.60, 0.52, 0.40), (0.62, 0.55, 0.42), (0.57, 0.49, 0.38), (0.64, 0.57, 0.45)]
    col = palette_pick(t, pal) * (0.93 + 0.1 * hash01(ids, 6))[..., None]
    col *= (0.86 + 0.18 * tex + 0.08 * (bed - 0.5) + 0.05 * (fine - 0.5))[..., None]
    # rain streaks and soot: long vertical runs that ignore the joints (periodic in both axes)
    streak = stretched_noise(n, 22, 2, 3, seed + 11)
    grime = pnoise(n, 3, 4, 0.55, seed + 7)
    col *= (0.72 + 0.22 * grime + 0.14 * (streak - 0.5))[..., None]
    mortar = np.array([0.62, 0.58, 0.52]) * (0.8 if red else 0.9)
    jm = 1 - prof
    col = col * (1 - jm[..., None]) + mortar * jm[..., None] * (0.8 + 0.3 * tex)[..., None]
    h = prof * (0.85 + 0.1 * tex + 0.03 * tool) + 0.06 * bed + 0.03 * fine
    rough = np.clip(0.78 + 0.1 * tex + 0.06 * (1 - prof), 0.5, 0.97)
    return dict(color=np.clip(col, 0, 1), rough=rough, height=h)


# ------------------------------------------------------------------ bark and fir needles (tree)

def bark(n=512, seed=91):
    ridges = stretched_noise(n, 14, 2, 4, seed)
    lo = pnoise(n, 4, 3, 0.5, seed + 1)
    v = 0.5 + 0.35 * (ridges - 0.5) + 0.15 * (lo - 0.5)
    col = np.array([0.20, 0.14, 0.10]) * (0.5 + 0.9 * v)[..., None]
    return dict(color=np.clip(col, 0, 1), rough=np.full((n, n), 0.85), height=ridges)


def fir_frond(w=512, h=256, seed=101):
    """A fir branch tip seen from above: twig along u, needles both sides. Returns RGBA with alpha."""
    r = rng(seed)
    img = np.zeros((h, w, 4))
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    cy = h / 2
    # main twig
    twig = np.exp(-((yy - cy) / 3.0) ** 2) * (xx > 4) * (xx < w - 6)
    alpha = np.clip(twig, 0, 1)
    shade = np.zeros((h, w))
    colacc = np.zeros((h, w, 3))
    # needles: short strokes angled forward from the twig
    for side in (-1, 1):
        x = 8.0
        while x < w - 12:
            L = r.uniform(0.28, 0.42) * h * (0.55 + 0.45 * min(1, (w - x) / (w * 0.4)))
            ang = np.radians(r.uniform(38, 62))
            x0, y0 = x, cy
            x1, y1 = x0 + np.cos(ang) * L * 0.55, cy + side * np.sin(ang) * L
            # distance to segment
            vx, vy = x1 - x0, y1 - y0
            t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / (vx * vx + vy * vy), 0, 1)
            dx = xx - (x0 + t * vx); dy = yy - (y0 + t * vy)
            thick = 2.4 * (1 - 0.6 * t)
            m = np.exp(-(dx * dx + dy * dy) / (thick * thick))
            m = np.where(m > 0.35, 1.0, m / 0.35 * 0.8)
            tone = r.uniform(0.75, 1.15)
            sel = m > alpha
            shade = np.where(sel, tone * (0.75 + 0.4 * t), shade)
            alpha = np.maximum(alpha, m)
            x += r.uniform(3.5, 5.5)
    base = np.array([0.035, 0.085, 0.04])
    tip = np.array([0.06, 0.13, 0.06])
    tt = (xx / w)[..., None]
    col = (base * (1 - tt) + tip * tt) * np.clip(shade, 0.5, 1.4)[..., None]
    col = np.where(twig[..., None] > 0.5, np.array([0.12, 0.08, 0.05]), col)
    img[..., :3] = col
    img[..., 3] = (alpha > 0.5).astype(float)
    # bleed colour into transparent area so mip edges are not black
    return img


def snow_frond(frond):
    img = frond.copy()
    a = img[..., 3]
    # snow sits on the upper side: keep a blobby subset
    h, w = a.shape
    n = pnoise(max(h, w), 12, 3, 0.5, 5)[:h, :w]
    keep = (n > 0.42).astype(float)
    alpha = ndimage.binary_dilation(a > 0.5, iterations=3) * keep
    alpha = ndimage.binary_opening(alpha, iterations=2).astype(float)
    img[..., :3] = np.array([0.82, 0.85, 0.9]) * (0.9 + 0.1 * n[..., None])
    img[..., 3] = alpha
    return img


# ------------------------------------------------------------------ window atlas (emissive)

def window_atlas(n=512, cells=4, seed=121):
    """4x4 cells of window panes. Cells 0..9 lit (variants), 10..15 dark.
    Returns (base, emit): base colour of glass, emission colour."""
    r = rng(seed)
    cs = n // cells
    base = np.zeros((n, n, 3)); emit = np.zeros((n, n, 3))
    yy, xx = np.mgrid[0:cs, 0:cs].astype(float) / cs
    for c in range(cells * cells):
        cy, cx = divmod(c, cells)
        sl = (slice(cy * cs, (cy + 1) * cs), slice(cx * cs, (cx + 1) * cs))
        glass = np.array([0.02, 0.025, 0.03]) + 0.02 * pnoise(cs, 4, 2, 0.5, seed + c)[..., None]
        base[sl] = glass
        if c == 9:          # stained glass (church lancets): small leaded quarries, warm-lit from inside
            ids = (np.floor(xx * 7 + 0.25 * np.sin(yy * 11)) * 17 + np.floor(yy * 12 + 0.25 * np.sin(xx * 9))).astype(np.int64)
            tint = palette_pick(hash01(ids, 3), [(0.9, 0.55, 0.22), (0.62, 0.16, 0.08), (0.18, 0.22, 0.5), (0.95, 0.75, 0.38), (0.25, 0.4, 0.2), (0.8, 0.62, 0.4)], [5, 2, 2, 4, 1, 4])
            lead = id_edges(ids)
            lead = ndimage.binary_dilation(lead, iterations=2)
            e = tint * (0.35 + 0.35 * (1 - yy))[..., None] * (0.75 + 0.25 * hash01(ids, 4))[..., None]
            e[lead] = 0.01
            emit[sl] = e
            base[sl] = glass
            continue
        if c < 10:
            warm = np.array([1.0, 0.55, 0.22]) * r.uniform(0.55, 1.0)
            if c % 3 == 0:
                warm = np.array([1.0, 0.68, 0.35]) * r.uniform(0.6, 1.0)
            # room light gradient (brighter at top, vignette)
            g = (0.55 + 0.45 * (1 - yy)) * (1 - 0.5 * ((xx - 0.5) * 2) ** 2)
            e = warm * g[..., None]
            # curtains on the sides
            cw = r.uniform(0.12, 0.28)
            curt = ((xx < cw) | (xx > 1 - cw)).astype(float)
            fold = 0.6 + 0.4 * np.sin(xx * 60 + r.uniform(0, 6)) ** 2
            e = e * (1 - curt[..., None]) + e * curt[..., None] * 0.45 * fold[..., None]
            kind = c % 5
            if kind == 1:   # candle arch (Schwibbogen) on the sill: thin arc, a row of candle flames
                ax = (xx - 0.5) / 0.36
                arch_y = 0.9 - 0.3 * np.sqrt(np.clip(1 - ax ** 2, 0, 1))
                band = (np.abs(yy - arch_y) < 0.022) & (np.abs(ax) <= 1)
                base_bar = (yy > 0.88) & (yy < 0.93) & (np.abs(ax) <= 1.05)
                e = np.where((band | base_bar)[..., None], e * 0.1, e)
                for k in range(7):
                    bx = 0.5 + (k - 3) * 0.1
                    by = 0.9 - 0.3 * np.sqrt(max(0, 1 - ((bx - 0.5) / 0.36) ** 2)) - 0.045
                    d = np.sqrt((xx - bx) ** 2 + ((yy - by) * 0.6) ** 2)
                    e = e + np.array([2.6, 1.7, 0.7])[None, None] * np.exp(-(d / 0.014) ** 2)[..., None]
            elif kind == 2:  # paper star (Herrnhuter Stern) glow
                d = np.sqrt((xx - 0.5) ** 2 + (yy - 0.38) ** 2)
                ang = np.arctan2(yy - 0.38, xx - 0.5)
                star = d < (0.1 + 0.06 * np.cos(ang * 8))
                e = e * 0.5 + np.where(star[..., None], np.array([2.5, 1.6, 0.8]), 0)
            elif kind == 3:  # table lamp in a corner: bright pool, dark shade edge
                lx = 0.28 if c % 2 else 0.72
                d = np.sqrt((xx - lx) ** 2 + ((yy - 0.62) * 1.4) ** 2)
                e = e * 0.55 + np.array([1.6, 0.95, 0.45])[None, None] * np.exp(-(d / 0.16) ** 2)[..., None]
                shade = (np.abs(xx - lx) < 0.07 + (yy - 0.52) * 0.4) & (yy > 0.52) & (yy < 0.6)
                e = np.where(shade[..., None], e * 1.5, e)
            elif kind == 4:  # dim, lace curtain drawn
                lace = 0.7 + 0.3 * (np.sin(xx * 90) * np.sin(yy * 90) > 0.3)
                e = e * 0.5 * lace[..., None]
            elif kind == 0 and c > 0:  # curtains nearly closed, a warm gap
                gap = np.exp(-((xx - 0.5) / 0.08) ** 2)
                e = e * (0.25 + 0.9 * gap)[..., None]
            emit[sl] = e
            base[sl] = glass + e * 0.05
        else:
            # dark: faint reflection streak, curtains barely visible
            refl = 0.04 * np.exp(-((xx + yy - 0.9) / 0.12) ** 2)
            base[sl] = glass + refl[..., None]
            if c in (12, 15):  # very dim room (TV-less glow)
                emit[sl] = np.array([0.18, 0.1, 0.05]) * (0.4 + 0.6 * (1 - yy))[..., None]
    return base, emit


# ------------------------------------------------------------------ io

def to_u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def save_png(path, arr):
    from PIL import Image
    a = to_u8(arr)
    if a.ndim == 2:
        Image.fromarray(a, "L").save(path)
    elif a.shape[2] == 3:
        Image.fromarray(a, "RGB").save(path)
    else:
        Image.fromarray(a, "RGBA").save(path)
    return path
