import math
from typing import List
from .schemas import SlabOutput, AxisGrid
from .constants import (
    SLAB_RIB_WIDTH_MIN_CM, SLAB_RIB_CLEAR_SPACING_MAX_CM,
    SLAB_TOP_FLANGE_MIN_CM, SLAB_RIB_H_BW_MAX_RATIO,
    SLAB_DEPTH_CONTINUOUS_RATIO,
)
RIB_WIDTH_OPTIONS = [10, 12, 15]
def find_max_span(grid):
    xs = [grid.x_axes[i+1]-grid.x_axes[i] for i in range(len(grid.x_axes)-1)]
    ys = [grid.y_axes[i+1]-grid.y_axes[i] for i in range(len(grid.y_axes)-1)]
    return max(max(xs), max(ys))
def determine_rib_direction(grid):
    ax = sum(grid.x_axes[i+1]-grid.x_axes[i] for i in range(len(grid.x_axes)-1))/(len(grid.x_axes)-1)
    ay = sum(grid.y_axes[i+1]-grid.y_axes[i] for i in range(len(grid.y_axes)-1))/(len(grid.y_axes)-1)
    return "X" if ax >= ay else "Y"
def compute_transverse_rib_count(span):
    if span > 7.0: return 2
    if span > 4.0: return 1
    return 0
def round_up_to_5cm(v): return math.ceil(v/5.0)*5.0
def design_asmolen_slab(max_span, story, direction):
    h_total = max(max_span*100.0/SLAB_DEPTH_CONTINUOUS_RATIO, 25.0)
    h_total = round_up_to_5cm(h_total)
    hf = SLAB_TOP_FLANGE_MIN_CM
    h_rib = h_total - hf
    bw = None
    for cand in RIB_WIDTH_OPTIONS:
        if h_rib/cand <= SLAB_RIB_H_BW_MAX_RATIO:
            bw = cand; break
    if bw is None:
        bw = 15
        h_total = round_up_to_5cm(hf + 3.5*bw)
    spacing = bw + 40.0
    return SlabOutput(
        story=story, total_thickness_cm=h_total,
        rib_width_cm=bw, rib_spacing_cm=spacing, top_flange_cm=hf,
        rib_direction=direction, transverse_rib_count=compute_transverse_rib_count(max_span),
    )
def design_all_slabs(grid, story_count):
    ms = find_max_span(grid); d = determine_rib_direction(grid)
    return [design_asmolen_slab(ms, s, d) for s in range(1, story_count+1)]
