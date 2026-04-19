import math
from typing import List, Dict, Tuple
from .schemas import BeamOutput, ColumnOutput, AxisGrid
from .constants import BEAM_MIN_WIDTH_CM, BEAM_MIN_HEIGHT_CM, BEAM_LN_H_MIN_RATIO
def round_up_to_5cm(v): return math.ceil(v/5.0)*5.0
def size_asmolen_main_beam(span, slab_t, col_w):
    h = slab_t
    bw_est = max(BEAM_MIN_WIDTH_CM, span*100.0/20.0)
    bw = min(bw_est, col_w)
    bw = max(bw, BEAM_MIN_WIDTH_CM)
    bw = round_up_to_5cm(bw)
    return bw, h
def size_all_beams(grid, cols_by_pos, story_count, slab_t):
    beams = []
    # X yönü
    for yi, yl in enumerate(grid.y_labels):
        for xi in range(len(grid.x_axes)-1):
            xs, xe = grid.x_axes[xi], grid.x_axes[xi+1]
            span = xe - xs
            cl = cols_by_pos[(xi, yi)]; cr = cols_by_pos[(xi+1, yi)]
            cw = min(cl.width_cm, cr.width_cm)
            bw, h = size_asmolen_main_beam(span, slab_t, cw)
            for s in range(1, story_count+1):
                beams.append(BeamOutput(
                    id=f"B-X-{grid.x_labels[xi]}{grid.x_labels[xi+1]}-{yl}-S{s}",
                    start=(xs, grid.y_axes[yi]), end=(xe, grid.y_axes[yi]),
                    story=s, width_cm=bw, height_cm=h, span_m=span, direction="X",
                ))
    # Y yönü
    for xi, xl in enumerate(grid.x_labels):
        for yi in range(len(grid.y_axes)-1):
            ys, ye = grid.y_axes[yi], grid.y_axes[yi+1]
            span = ye - ys
            cb = cols_by_pos[(xi, yi)]; ct = cols_by_pos[(xi, yi+1)]
            cw = min(cb.depth_cm, ct.depth_cm)
            bw, h = size_asmolen_main_beam(span, slab_t, cw)
            for s in range(1, story_count+1):
                beams.append(BeamOutput(
                    id=f"B-Y-{xl}-{grid.y_labels[yi]}{grid.y_labels[yi+1]}-S{s}",
                    start=(grid.x_axes[xi], ys), end=(grid.x_axes[xi], ye),
                    story=s, width_cm=bw, height_cm=h, span_m=span, direction="Y",
                ))
    return beams
def validate_beam(beam, col_w):
    e = []
    if beam.width_cm < BEAM_MIN_WIDTH_CM: e.append(f"bw<{BEAM_MIN_WIDTH_CM}")
    if beam.height_cm < BEAM_MIN_HEIGHT_CM: e.append(f"h<{BEAM_MIN_HEIGHT_CM}")
    if beam.width_cm > col_w: e.append(f"bw={beam.width_cm}>bc={col_w}")
    ln = beam.span_m - 0.5
    mn = BEAM_LN_H_MIN_RATIO*beam.height_cm/100.0
    if ln < mn: e.append(f"ln={ln:.2f}<4h")
    return e
