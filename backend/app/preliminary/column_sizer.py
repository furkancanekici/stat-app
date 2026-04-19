import math
from typing import List, Dict, Tuple
from .schemas import ColumnOutput, AxisGrid
from .constants import (
    COLUMN_MIN_DIMENSION_CM, COLUMN_MIN_AREA_CM2, COLUMN_AXIAL_LOAD_RATIO,
    COLUMN_H_B_MAX_RATIO, COLUMN_SIZE_ROUNDING_CM,
    COLUMN_K_INTERIOR, COLUMN_K_EDGE, COLUMN_K_CORNER,
)
STORY_GROUPING = 2
def classify_position(grid, xi, yi):
    nx, ny = len(grid.x_axes), len(grid.y_axes)
    xe = (xi==0 or xi==nx-1)
    ye = (yi==0 or yi==ny-1)
    if xe and ye: return "corner"
    if xe or ye: return "edge"
    return "interior"
def get_k_factor(pos):
    return {"interior":COLUMN_K_INTERIOR, "edge":COLUMN_K_EDGE, "corner":COLUMN_K_CORNER}[pos]
def round_up_to_5cm(v): return math.ceil(v/COLUMN_SIZE_ROUNDING_CM)*COLUMN_SIZE_ROUNDING_CM
def compute_required_area_cm2(Nd, fck, pos):
    k = get_k_factor(pos)
    A = Nd*1000.0/(k*fck*100.0)
    return max(A, COLUMN_MIN_AREA_CM2)
def determine_long_axis(grid, xi, yi):
    xs, ys = grid.x_axes, grid.y_axes
    dx = (xs[1]-xs[0]) if xi==0 else ((xs[-1]-xs[-2]) if xi==len(xs)-1 else (xs[xi+1]-xs[xi-1]))
    dy = (ys[1]-ys[0]) if yi==0 else ((ys[-1]-ys[-2]) if yi==len(ys)-1 else (ys[yi+1]-ys[yi-1]))
    return "X" if dx >= dy else "Y"
def size_single_column(Nd, fck, pos, long_axis="Y"):
    Ac = compute_required_area_cm2(Nd, fck, pos)
    b = math.sqrt(Ac/1.15); h = 1.15*b
    b = max(b, COLUMN_MIN_DIMENSION_CM); h = max(h, COLUMN_MIN_DIMENSION_CM)
    b = round_up_to_5cm(b); h = round_up_to_5cm(h)
    if b==h: h += COLUMN_SIZE_ROUNDING_CM
    if long_axis=="X": return max(b,h), min(b,h)
    return min(b,h), max(b,h)
def _group_sizes(sizes, g=STORY_GROUPING):
    out = {}; ss = sorted(sizes.keys()); i = 0
    while i < len(ss):
        grp = ss[i:i+g]; ref = sizes[grp[0]]
        for s in grp: out[s] = ref
        i += g
    return out
def _vertical_continuity(sizes):
    out = {}; ss = sorted(sizes.keys())
    pb, ph = sizes[ss[0]]; out[ss[0]] = (pb, ph)
    for s in ss[1:]:
        b, h = sizes[s]; b = min(b, pb); h = min(h, ph)
        out[s] = (b, h); pb, ph = b, h
    return out
def size_all_columns(grid, loads, story_count, fck):
    result = []
    for xi in range(len(grid.x_axes)):
        for yi in range(len(grid.y_axes)):
            pos = classify_position(grid, xi, yi)
            la = determine_long_axis(grid, xi, yi)
            raw = {}
            for s in range(1, story_count+1):
                Nd = loads[(xi,yi,s)]
                raw[s] = size_single_column(Nd, fck, pos, la)
            grouped = _group_sizes(raw); final = _vertical_continuity(grouped)
            for s in range(1, story_count+1):
                b, h = final[s]; Nd = loads[(xi,yi,s)]
                result.append(ColumnOutput(
                    id=f"C-{grid.x_labels[xi]}{grid.y_labels[yi]}-S{s}",
                    x=grid.x_axes[xi], y=grid.y_axes[yi], story=s,
                    width_cm=b, depth_cm=h, axial_load_kN=Nd,
                    axis_label=f"{grid.x_labels[xi]}-{grid.y_labels[yi]}",
                ))
    return result
def validate_column(b, h, Nd, fck):
    errors = []
    Ac = b*h
    if min(b,h) < COLUMN_MIN_DIMENSION_CM: errors.append("Min kenar altı")
    if Ac < COLUMN_MIN_AREA_CM2: errors.append(f"Ac={Ac:.0f}<900")
    r = max(b,h)/min(b,h)
    if r >= COLUMN_H_B_MAX_RATIO: errors.append(f"h/b={r:.2f}≥6")
    cap = COLUMN_AXIAL_LOAD_RATIO * fck * Ac * 100 / 1000
    if Nd > cap: errors.append(f"Nd={Nd:.0f}>cap={cap:.0f}")
    return errors
