from typing import List, Tuple
from .schemas import AxisGrid
from .constants import (
    BAY_SPAN_TARGET_MIN_M, BAY_SPAN_TARGET_MAX_M,
    BAY_SPAN_ABSOLUTE_MIN_M, BAY_SPAN_ABSOLUTE_MAX_M,
)
IDEAL_SPAN = 7.0
def _x_label(i): return str(i + 1)
def _y_label(i):
    if i < 26: return chr(ord("A") + i)
    return chr(ord("A") + (i // 26) - 1) + chr(ord("A") + i % 26)
def generate_axes(L, direction):
    if L < BAY_SPAN_ABSOLUTE_MIN_M * 2:
        n_axes = 2
    else:
        n_bays = max(1, round(L / IDEAL_SPAN))
        n_axes = n_bays + 1
        span = L / n_bays
        while span > BAY_SPAN_ABSOLUTE_MAX_M and n_axes < 20:
            n_axes += 1; n_bays = n_axes - 1; span = L / n_bays
        while span < BAY_SPAN_ABSOLUTE_MIN_M and n_axes > 2:
            n_axes -= 1; n_bays = n_axes - 1; span = L / n_bays
    span = L / (n_axes - 1)
    coords = [round(i * span, 2) for i in range(n_axes)]
    coords[-1] = L
    label_fn = _x_label if direction == "X" else _y_label
    return coords, [label_fn(i) for i in range(n_axes)]
def generate_grid(Lx, Ly):
    xa, xl = generate_axes(Lx, "X")
    ya, yl = generate_axes(Ly, "Y")
    return AxisGrid(x_axes=xa, y_axes=ya, x_labels=xl, y_labels=yl)
def get_spans(axes): return [axes[i+1]-axes[i] for i in range(len(axes)-1)]
def validate_grid(grid):
    w = []
    for i, s in enumerate(get_spans(grid.x_axes)):
        if s < BAY_SPAN_ABSOLUTE_MIN_M: w.append(f"X {grid.x_labels[i]}-{grid.x_labels[i+1]} dar: {s:.2f}m")
        elif s > BAY_SPAN_ABSOLUTE_MAX_M: w.append(f"X {grid.x_labels[i]}-{grid.x_labels[i+1]} geniş: {s:.2f}m")
        elif not (BAY_SPAN_TARGET_MIN_M <= s <= BAY_SPAN_TARGET_MAX_M): w.append(f"X açıklık {s:.2f}m — hedef dışı")
    for i, s in enumerate(get_spans(grid.y_axes)):
        if s < BAY_SPAN_ABSOLUTE_MIN_M: w.append(f"Y dar: {s:.2f}m")
        elif s > BAY_SPAN_ABSOLUTE_MAX_M: w.append(f"Y geniş: {s:.2f}m")
    return w
