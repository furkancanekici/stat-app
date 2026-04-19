from typing import Dict, Tuple
from .schemas import AxisGrid, UsageType
from .constants import (
    DEAD_LOAD_RESIDENTIAL, LIVE_LOAD_RESIDENTIAL,
    DEAD_LOAD_STORAGE, LIVE_LOAD_STORAGE,
    LIVE_LOAD_PARTICIPATION_RESIDENTIAL, LIVE_LOAD_PARTICIPATION_STORAGE,
    LOAD_FACTOR_DEAD, LOAD_FACTOR_LIVE,
    LIVE_LOAD_REDUCTION_RESIDENTIAL, LIVE_LOAD_REDUCTION_STORAGE,
)
def get_loads_for_usage(u):
    if u==UsageType.RESIDENTIAL: return DEAD_LOAD_RESIDENTIAL, LIVE_LOAD_RESIDENTIAL, LIVE_LOAD_PARTICIPATION_RESIDENTIAL
    if u==UsageType.STORAGE: return DEAD_LOAD_STORAGE, LIVE_LOAD_STORAGE, LIVE_LOAD_PARTICIPATION_STORAGE
    raise ValueError(f"{u}")
def get_live_load_reduction(usage, stories_above):
    t = LIVE_LOAD_REDUCTION_RESIDENTIAL if usage==UsageType.RESIDENTIAL else LIVE_LOAD_REDUCTION_STORAGE
    if stories_above<=1: return 1.0
    if stories_above>=10: return t[10]
    return t[stories_above]
def compute_tributary_area(grid, xi, yi):
    xs, ys = grid.x_axes, grid.y_axes
    if xi==0: dx=(xs[1]-xs[0])/2
    elif xi==len(xs)-1: dx=(xs[-1]-xs[-2])/2
    else: dx=(xs[xi+1]-xs[xi-1])/2
    if yi==0: dy=(ys[1]-ys[0])/2
    elif yi==len(ys)-1: dy=(ys[-1]-ys[-2])/2
    else: dy=(ys[yi+1]-ys[yi-1])/2
    return dx*dy
def compute_column_design_loads(grid, story_count, usage):
    G, Q, _ = get_loads_for_usage(usage)
    loads = {}
    for xi in range(len(grid.x_axes)):
        for yi in range(len(grid.y_axes)):
            ta = compute_tributary_area(grid, xi, yi)
            for s in range(1, story_count+1):
                sa = story_count - s + 1
                b = get_live_load_reduction(usage, sa)
                loads[(xi,yi,s)] = ta * sa * (LOAD_FACTOR_DEAD*G + LOAD_FACTOR_LIVE*b*Q)
    return loads
def compute_column_seismic_loads(grid, story_count, usage):
    G, Q, n = get_loads_for_usage(usage)
    w = G + n*Q
    loads = {}
    for xi in range(len(grid.x_axes)):
        for yi in range(len(grid.y_axes)):
            ta = compute_tributary_area(grid, xi, yi)
            for s in range(1, story_count+1):
                loads[(xi,yi,s)] = ta * w * (story_count - s + 1)
    return loads
def compute_story_mass(grid, Lx, Ly, usage):
    G, Q, n = get_loads_for_usage(usage)
    return Lx * Ly * (G + n*Q)
