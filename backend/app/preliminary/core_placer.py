from typing import List, Tuple, Optional
from dataclasses import dataclass
from .schemas import AxisGrid, CoreInput, CoreOutput, WallOutput, ColumnOutput
from .constants import WALL_MIN_THICKNESS_CM

CORE_DIMENSIONS_BY_STORY = [
    (5,  2.40, 2.50, 25.0),
    (10, 2.40, 2.70, 25.0),
    (15, 2.60, 2.90, 30.0),
    (99, 2.80, 3.10, 30.0),
]
TOP_N_CANDIDATES = 2

def get_core_dimensions(story_count):
    for ms, w, l, bw in CORE_DIMENSIONS_BY_STORY:
        if story_count <= ms: return w, l, bw
    return CORE_DIMENSIONS_BY_STORY[-1][1:]

@dataclass
class CoreCandidate:
    center_x: float
    center_y: float
    score: float

def _generate_candidates(grid, Lx, Ly, W, L):
    cxt, cyt = Lx/2, Ly/2
    cands = []
    for cx in grid.x_axes:
        for cy in grid.y_axes:
            x_min, x_max = cx - W/2, cx + W/2
            y_min, y_max = cy - L/2, cy + L/2
            if x_min < 0 or x_max > Lx or y_min < 0 or y_max > Ly: continue
            dist = ((cx - cxt)**2 + (cy - cyt)**2)**0.5
            edge_dist = min(x_min, y_min, Lx - x_max, Ly - y_max)
            edge_penalty = max(0, 1.5 - edge_dist)
            score = dist + edge_penalty * 2.0
            cands.append(CoreCandidate(cx, cy, score))
    return sorted(cands, key=lambda c: c.score)

def _determine_default_opening_direction(Lx, Ly):
    return "+Y" if Lx >= Ly else "+X"

def _build_u_walls(cx, cy, W, L, bw, opening, story_range):
    x_min, x_max = cx - W/2, cx + W/2
    y_min, y_max = cy - L/2, cy + L/2
    bw_m = bw / 100.0
    walls = []
    if opening in ("+X", "-X"):
        back_x = x_max if opening == "-X" else x_min
        offset = bw_m/2 if opening == "+X" else -bw_m/2
        walls.append(WallOutput(id="CORE-BACK", center=(back_x + offset, cy),
            length_m=L, thickness_cm=bw, orientation="Y", story_range=story_range))
        walls.append(WallOutput(id="CORE-SIDE-TOP", center=(cx, y_max - bw_m/2),
            length_m=W, thickness_cm=bw, orientation="X", story_range=story_range))
        walls.append(WallOutput(id="CORE-SIDE-BOT", center=(cx, y_min + bw_m/2),
            length_m=W, thickness_cm=bw, orientation="X", story_range=story_range))
    else:
        back_y = y_max if opening == "-Y" else y_min
        offset = bw_m/2 if opening == "+Y" else -bw_m/2
        walls.append(WallOutput(id="CORE-BACK", center=(cx, back_y + offset),
            length_m=W, thickness_cm=bw, orientation="X", story_range=story_range))
        walls.append(WallOutput(id="CORE-SIDE-LEFT", center=(x_min + bw_m/2, cy),
            length_m=L, thickness_cm=bw, orientation="Y", story_range=story_range))
        walls.append(WallOutput(id="CORE-SIDE-RIGHT", center=(x_max - bw_m/2, cy),
            length_m=L, thickness_cm=bw, orientation="Y", story_range=story_range))
    return walls

def _identify_overlapping_columns(columns, cx, cy, W, L, tol=0.3):
    x_min, x_max = cx - W/2 - tol, cx + W/2 + tol
    y_min, y_max = cy - L/2 - tol, cy + L/2 + tol
    return [c.id for c in columns if x_min <= c.x <= x_max and y_min <= c.y <= y_max]

def _build_core_from_candidate(cand, W, L, bw, opening, story_count, columns):
    walls = _build_u_walls(cand.center_x, cand.center_y, W, L, bw, opening, (1, story_count))
    removed = _identify_overlapping_columns(columns, cand.center_x, cand.center_y, W, L)
    return CoreOutput(
        center=(cand.center_x, cand.center_y),
        width_m=W, length_m=L, wall_thickness_cm=bw,
        opening_direction=opening, walls=walls,
        removed_column_ids=removed,
    )

def place_core(grid, Lx, Ly, core_input, columns, story_count):
    if not core_input.required: return []
    W, L, bw = get_core_dimensions(story_count)
    if core_input.width_m_override: W = core_input.width_m_override
    if core_input.length_m_override: L = core_input.length_m_override
    cands = _generate_candidates(grid, Lx, Ly, W, L)
    if not cands: return []
    opening = _determine_default_opening_direction(Lx, Ly)
    return [_build_core_from_candidate(c, W, L, bw, opening, story_count, columns)
            for c in cands[:TOP_N_CANDIDATES]]

def remove_core_columns(columns, removed_ids):
    return [c for c in columns if c.id not in removed_ids]
