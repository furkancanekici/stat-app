from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from .schemas import WallOutput, AxisGrid, CoreOutput, ColumnOutput
from .constants import (
    WALL_MIN_THICKNESS_CM, WALL_LW_BW_MIN_RATIO,
    WALL_AREA_RATIO_MIN, WALL_AREA_RATIO_TARGET,
    WALL_ECCENTRICITY_MAX_RATIO,
)

WALL_LENGTH_OPTIONS_M = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
WEIGHT_CORNER_PERIMETER = 3.0
WEIGHT_MIDDLE_PERIMETER = 2.0
WEIGHT_INTERIOR = 0.7

def get_wall_thickness(story_count):
    return WALL_MIN_THICKNESS_CM if story_count <= 10 else 30.0

@dataclass
class WallSlot:
    slot_id: str
    center: Tuple[float, float]
    orientation: str
    axis_label: str
    axis_coord: float
    segment_start: float
    segment_end: float
    max_length_m: float
    is_perimeter: bool
    is_corner_adjacent: bool
    weight: float

def _generate_slots_for_axis(axis_coord, perp_axes, orientation, is_perim, Lx, Ly, label):
    slots = []
    for i in range(len(perp_axes) - 1):
        seg_s, seg_e = perp_axes[i], perp_axes[i+1]
        seg_l = seg_e - seg_s
        is_corner = (i == 0 or i == len(perp_axes) - 2)
        weight = (WEIGHT_CORNER_PERIMETER if is_corner else WEIGHT_MIDDLE_PERIMETER) if is_perim else WEIGHT_INTERIOR
        seg_mid = (seg_s + seg_e) / 2
        center = (axis_coord, seg_mid) if orientation == "Y" else (seg_mid, axis_coord)
        slots.append(WallSlot(
            slot_id=f"{label}-seg{i}", center=center, orientation=orientation,
            axis_label=label, axis_coord=axis_coord,
            segment_start=seg_s, segment_end=seg_e, max_length_m=seg_l,
            is_perimeter=is_perim, is_corner_adjacent=is_corner, weight=weight,
        ))
    return slots

def generate_wall_slots(grid, Lx, Ly, core=None):
    slots = []
    for xi, xc in enumerate(grid.x_axes):
        is_p = (xi == 0 or xi == len(grid.x_axes) - 1)
        slots.extend(_generate_slots_for_axis(xc, grid.y_axes, "Y", is_p, Lx, Ly, f"X={grid.x_labels[xi]}"))
    for yi, yc in enumerate(grid.y_axes):
        is_p = (yi == 0 or yi == len(grid.y_axes) - 1)
        slots.extend(_generate_slots_for_axis(yc, grid.x_axes, "X", is_p, Lx, Ly, f"Y={grid.y_labels[yi]}"))
    if core is not None:
        slots = _filter_core_overlapping_slots(slots, core)
    return slots

def _filter_core_overlapping_slots(slots, core):
    """
    Çekirdekle çakışan slotları ele.
    Bir slot atılır eğer:
      (a) Slot merkezi U iç alanında VEYA
      (b) Bu slot aynı aks üstünde ve segmenti core perdesiyle kesişiyor
    """
    cx, cy = core.center
    W, L = core.width_m, core.length_m
    xmin, xmax = cx - W/2, cx + W/2
    ymin, ymax = cy - L/2, cy + L/2
    tol = 0.1  # 10cm tolerans (aks-çekirdek kenar çakışması için)
    filtered = []
    for s in slots:
        # (a) Slot merkezi U içinde mi?
        sx, sy = s.center
        if xmin <= sx <= xmax and ymin <= sy <= ymax:
            continue
        # (b) Slot aksı core sınırıyla çakışıyor mu?
        if s.orientation == "Y":
            # Dikey slot — X aksı core X aralığında mı VE
            # slot Y segmenti core Y aralığıyla kesişiyor mu
            axis_on_core = (xmin - tol) <= s.axis_coord <= (xmax + tol)
            seg_overlaps = not (s.segment_end <= ymin + tol or s.segment_start >= ymax - tol)
            if axis_on_core and seg_overlaps:
                continue
        else:  # "X"
            axis_on_core = (ymin - tol) <= s.axis_coord <= (ymax + tol)
            seg_overlaps = not (s.segment_end <= xmin + tol or s.segment_start >= xmax - tol)
            if axis_on_core and seg_overlaps:
                continue
        filtered.append(s)
    return filtered

def get_available_lengths_for_slot(slot):
    return [L for L in WALL_LENGTH_OPTIONS_M if L <= slot.max_length_m]

def compute_mass_center(Lx, Ly, core=None):
    return (Lx / 2, Ly / 2)

def compute_stiffness_center(columns, walls, story=1):
    """
    Rijitlik merkezi (CR) — çapraz eksen kuralı:
      X_CR = Σ(k_y × x) / Σ k_y
      Y_CR = Σ(k_x × y) / Σ k_x
    """
    story_cols = [c for c in columns if c.story == story]
    sum_kx_y = sum_kx = sum_ky_x = sum_ky = 0.0
    for col in story_cols:
        # b=width(X), h=depth(Y)
        kx = col.depth_cm * (col.width_cm ** 3) / 12.0
        ky = col.width_cm * (col.depth_cm ** 3) / 12.0
        sum_kx_y += kx * col.y
        sum_kx += kx
        sum_ky_x += ky * col.x
        sum_ky += ky
    for w in walls:
        if not (w.story_range[0] <= story <= w.story_range[1]):
            continue
        bw_cm = w.thickness_cm
        lw_cm = w.length_m * 100
        k_strong = bw_cm * (lw_cm ** 3) / 12.0
        k_weak = lw_cm * (bw_cm ** 3) / 12.0
        if w.orientation == "X":
            kx = k_strong; ky = k_weak
        else:
            kx = k_weak; ky = k_strong
        sum_kx_y += kx * w.center[1]
        sum_kx += kx
        sum_ky_x += ky * w.center[0]
        sum_ky += ky
    if sum_kx == 0 or sum_ky == 0:
        return (0.0, 0.0)
    return (sum_ky_x / sum_ky, sum_kx_y / sum_kx)

def compute_eccentricity(cm, cr):
    ex = abs(cm[0] - cr[0]); ey = abs(cm[1] - cr[1])
    return ex, ey, (ex*ex + ey*ey) ** 0.5

def eccentricity_acceptable(cm, cr, Lx, Ly):
    ex, ey, _ = compute_eccentricity(cm, cr)
    max_e = WALL_ECCENTRICITY_MAX_RATIO * min(Lx, Ly)
    return ex <= max_e and ey <= max_e

# ============= PARÇA 2 =============

@dataclass
class WallPlacement:
    slot_id: str
    center: Tuple[float, float]
    orientation: str
    length_m: float
    thickness_cm: float
    is_core: bool = False

@dataclass
class WallConfiguration:
    placements: List[WallPlacement] = field(default_factory=list)
    core_candidate_index: int = 0
    mass_center: Tuple[float, float] = (0.0, 0.0)
    stiffness_center: Tuple[float, float] = (0.0, 0.0)
    eccentricity_x: float = 0.0
    eccentricity_y: float = 0.0
    total_area_x: float = 0.0
    total_area_y: float = 0.0
    score: float = 0.0

def compute_target_wall_area(Lx, Ly):
    A = Lx * Ly
    return (A * WALL_AREA_RATIO_MIN, A * WALL_AREA_RATIO_TARGET)

def _wall_placement_area(p):
    return p.length_m * (p.thickness_cm / 100.0)

def compute_placement_areas(placements):
    ax = sum(_wall_placement_area(p) for p in placements if p.orientation == "X")
    ay = sum(_wall_placement_area(p) for p in placements if p.orientation == "Y")
    return ax, ay

def _core_walls_to_placements(core):
    return [WallPlacement(
        slot_id=w.id, center=w.center, orientation=w.orientation,
        length_m=w.length_m, thickness_cm=w.thickness_cm, is_core=True,
    ) for w in core.walls]

def _mirror_slot(slot, Lx, Ly, axis):
    cx, cy = slot.center
    if axis == "X": return (cx, Ly - cy)
    if axis == "Y": return (Lx - cx, cy)
    return (Lx - cx, Ly - cy)

def _find_slot_at_position(slots, target, orientation, tolerance=0.5):
    tx, ty = target
    best = None; best_dist = tolerance
    for s in slots:
        if s.orientation != orientation: continue
        d = ((s.center[0] - tx)**2 + (s.center[1] - ty)**2) ** 0.5
        if d < best_dist:
            best = s; best_dist = d
    return best

def _slot_to_placement(slot, length_m, thickness_cm):
    seg_mid = (slot.segment_start + slot.segment_end) / 2
    center = (slot.axis_coord, seg_mid) if slot.orientation == "Y" else (seg_mid, slot.axis_coord)
    return WallPlacement(
        slot_id=slot.slot_id, center=center, orientation=slot.orientation,
        length_m=length_m, thickness_cm=thickness_cm, is_core=False,
    )

def _placements_to_wall_outputs(placements):
    return [WallOutput(
        id=p.slot_id, center=p.center, length_m=p.length_m,
        thickness_cm=p.thickness_cm, orientation=p.orientation,
        story_range=(1, 99),
    ) for p in placements]

def _is_interior_placement(p, grid):
    tol = 0.1
    if p.orientation == "Y":
        coord = p.center[0]
        return not (abs(coord - grid.x_axes[0]) < tol or abs(coord - grid.x_axes[-1]) < tol)
    coord = p.center[1]
    return not (abs(coord - grid.y_axes[0]) < tol or abs(coord - grid.y_axes[-1]) < tol)

MAX_WALLS_PER_AXIS = 2  # bir aksa maksimum kaç perde konulabilir


def _axis_count(placements, axis_label):
    """Bir aksta kaç perde var (core dahil)."""
    count = 0
    for p in placements:
        if p.slot_id.startswith(axis_label + "-"):
            count += 1
    return count

def _add_phase(slots, placements, used, missing_x, missing_y, Lx, Ly, bw_cm, grid):
    """
    Bir faz (köşe/orta/iç) için simetrik perde yerleştirmesi.
    Her aksa max MAX_WALLS_PER_AXIS perde.
    """
    def dfc(slot):
        return ((slot.center[0] - Lx/2)**2 + (slot.center[1] - Ly/2)**2) ** 0.5

    def _try_add(slot):
        if slot.slot_id in used:
            return 0.0
        if _axis_count(placements, slot.axis_label) >= MAX_WALLS_PER_AXIS:
            return 0.0
        avail = get_available_lengths_for_slot(slot)
        if not avail:
            return 0.0
        chosen = avail[-1]
        p = _slot_to_placement(slot, chosen, bw_cm)
        placements.append(p)
        used.add(slot.slot_id)
        return _wall_placement_area(p)

    y_slots = sorted([s for s in slots if s.orientation == "Y" and s.slot_id not in used],
                     key=dfc, reverse=True)
    for slot in y_slots:
        if missing_y <= 0:
            break
        added = _try_add(slot)
        if added <= 0:
            continue
        missing_y -= added
        mpos = _mirror_slot(slot, Lx, Ly, "XY")
        mirror = _find_slot_at_position(slots, mpos, "Y")
        if mirror is not None:
            missing_y -= _try_add(mirror)

    x_slots = sorted([s for s in slots if s.orientation == "X" and s.slot_id not in used],
                     key=dfc, reverse=True)
    for slot in x_slots:
        if missing_x <= 0:
            break
        added = _try_add(slot)
        if added <= 0:
            continue
        missing_x -= added
        mpos = _mirror_slot(slot, Lx, Ly, "XY")
        mirror = _find_slot_at_position(slots, mpos, "X")
        if mirror is not None:
            missing_x -= _try_add(mirror)

    return missing_x, missing_y


def build_initial_configuration(grid, Lx, Ly, core, story_count, core_candidate_index=0):
    """
    Hiyerarşik greedy — Seçenek C:
      FAZ 1: Çevresel köşe slotları (max uzunluk, simetrik)
      FAZ 2: Çevresel orta slotları
      FAZ 3: İç aks slotları (son çare)
    """
    bw_cm = get_wall_thickness(story_count)
    placements = _core_walls_to_placements(core)
    slots = generate_wall_slots(grid, Lx, Ly, core=core)
    
    _, target = compute_target_wall_area(Lx, Ly)
    ax, ay = compute_placement_areas(placements)
    miss_x = max(0, target - ax)
    miss_y = max(0, target - ay)
    
    used = set(p.slot_id for p in placements)
    
    # FAZ 1 — Çevresel köşe
    phase1_slots = [s for s in slots if s.is_perimeter and s.is_corner_adjacent]
    miss_x, miss_y = _add_phase(phase1_slots, placements, used,
                                 miss_x, miss_y, Lx, Ly, bw_cm, grid)
    
    # FAZ 2 — Çevresel orta (köşe DEĞİL, ama çevresel)
    if miss_x > 0 or miss_y > 0:
        phase2_slots = [s for s in slots if s.is_perimeter and not s.is_corner_adjacent]
        miss_x, miss_y = _add_phase(phase2_slots, placements, used,
                                     miss_x, miss_y, Lx, Ly, bw_cm, grid)
    
    # FAZ 3 — İç aks (son çare)
    if miss_x > 0 or miss_y > 0:
        phase3_slots = [s for s in slots if not s.is_perimeter]
        miss_x, miss_y = _add_phase(phase3_slots, placements, used,
                                     miss_x, miss_y, Lx, Ly, bw_cm, grid)
    
    return WallConfiguration(placements=placements, core_candidate_index=core_candidate_index)


def evaluate_configuration(config, grid, Lx, Ly, columns):
    wos = _placements_to_wall_outputs(config.placements)
    config.mass_center = compute_mass_center(Lx, Ly)
    config.stiffness_center = compute_stiffness_center(columns, wos, story=1)
    ex, ey, _ = compute_eccentricity(config.mass_center, config.stiffness_center)
    config.eccentricity_x = ex
    config.eccentricity_y = ey
    config.total_area_x, config.total_area_y = compute_placement_areas(config.placements)
    
    max_e = WALL_ECCENTRICITY_MAX_RATIO * min(Lx, Ly)
    ecc_score = (ex/max_e)**2 + (ey/max_e)**2
    A = Lx * Ly
    balance = abs(config.total_area_x - config.total_area_y) / A
    min_area = A * WALL_AREA_RATIO_MIN
    area_penalty = 0.0
    if config.total_area_x < min_area:
        area_penalty += (min_area - config.total_area_x) / min_area
    if config.total_area_y < min_area:
        area_penalty += (min_area - config.total_area_y) / min_area
    interior_ct = sum(1 for p in config.placements if not p.is_core and _is_interior_placement(p, grid))
    interior_pen = interior_ct * 0.05
    
    config.score = ecc_score + balance * 2.0 + area_penalty * 3.0 + interior_pen
    return config

# ============= PARÇA 3 — SIMULATED ANNEALING =============
import math
import random
import copy

# SA parametreleri
SA_INITIAL_TEMP = 1.0
SA_COOLING_ALPHA = 0.99
SA_MIN_TEMP = 0.001
SA_ITER_PER_SLOT = 75        # iterasyon = max(500, slot × 75)
SA_MIN_ITERATIONS = 500
SA_SWAP_TEMP_THRESHOLD = 0.3  # T < T0×0.3 → SWAP devre dışı
RESIZE_STEP_M = 1.0            # RESIZE adımı (mimari modül)

# Maksimum alan sınırları (over-design kontrolü)
WALL_AREA_RATIO_SOFT_MAX = 0.035
WALL_AREA_RATIO_HARD_MAX = 0.040


def evaluate_configuration_relaxed(config, grid, Lx, Ly, columns):
    """
    SA için esnetilmiş skor:
    - %2.0 altı: hard penalty (drift riski)
    - %2.0-%2.5: soft penalty (mühendis isterse)
    - %2.5-%3.5: ceza yok
    - %3.5-%4.0: soft ceza (over-design uyarısı)
    - %4.0 üstü: hard penalty (mimari katliam)
    """
    wos = _placements_to_wall_outputs(config.placements)
    config.mass_center = compute_mass_center(Lx, Ly)
    config.stiffness_center = compute_stiffness_center(columns, wos, story=1)
    ex, ey, _ = compute_eccentricity(config.mass_center, config.stiffness_center)
    config.eccentricity_x = ex; config.eccentricity_y = ey
    config.total_area_x, config.total_area_y = compute_placement_areas(config.placements)

    max_e = WALL_ECCENTRICITY_MAX_RATIO * min(Lx, Ly)
    ecc_score = (ex/max_e)**2 + (ey/max_e)**2
    A = Lx * Ly
    balance = abs(config.total_area_x - config.total_area_y) / A

    # Alan cezaları — iki yönlü
    def area_cost(area_ratio):
        if area_ratio < WALL_AREA_RATIO_MIN:
            # %2.0 altı — hard
            deficit = (WALL_AREA_RATIO_MIN - area_ratio) / WALL_AREA_RATIO_MIN
            return 10.0 * deficit   # sert
        elif area_ratio < WALL_AREA_RATIO_TARGET:
            # %2.0-%2.5 — soft
            deficit = (WALL_AREA_RATIO_TARGET - area_ratio) / WALL_AREA_RATIO_TARGET
            return 0.5 * deficit
        elif area_ratio <= WALL_AREA_RATIO_SOFT_MAX:
            # %2.5-%3.5 — optimal bölge
            return 0.0
        elif area_ratio <= WALL_AREA_RATIO_HARD_MAX:
            # %3.5-%4.0 — over-design uyarısı
            excess = (area_ratio - WALL_AREA_RATIO_SOFT_MAX) / WALL_AREA_RATIO_SOFT_MAX
            return 0.5 * excess
        else:
            # %4.0 üstü — hard
            excess = (area_ratio - WALL_AREA_RATIO_HARD_MAX) / WALL_AREA_RATIO_HARD_MAX
            return 10.0 * excess

    ax_ratio = config.total_area_x / A
    ay_ratio = config.total_area_y / A
    area_penalty = area_cost(ax_ratio) + area_cost(ay_ratio)

    # İç perde cezası
    interior_ct = sum(1 for p in config.placements if not p.is_core and _is_interior_placement(p, grid))
    interior_pen = interior_ct * 0.05

    config.score = ecc_score + balance * 2.0 + area_penalty + interior_pen
    return config


# ===================================================
# HAMLE OPERATÖRLERİ (4 tür)
# ===================================================

def _move_add(config, slots, story_count, grid, Lx, Ly):
    """Boş slota max uzunlukta perde ekle. Aks başına max MAX_WALLS_PER_AXIS kuralına uyar."""
    bw_cm = get_wall_thickness(story_count)
    used = {p.slot_id for p in config.placements}
    empty = []
    for s in slots:
        if s.slot_id in used:
            continue
        if _axis_count(config.placements, s.axis_label) >= MAX_WALLS_PER_AXIS:
            continue
        empty.append(s)
    if not empty:
        return False
    weights = [s.weight for s in empty]
    slot = random.choices(empty, weights=weights, k=1)[0]
    avail = get_available_lengths_for_slot(slot)
    if not avail:
        return False
    chosen = avail[-1]
    p = _slot_to_placement(slot, chosen, bw_cm)
    config.placements.append(p)
    return True


def _move_remove(config):
    """Core olmayan bir perdeyi sil."""
    non_core = [i for i, p in enumerate(config.placements) if not p.is_core]
    if not non_core:
        return False
    idx = random.choice(non_core)
    config.placements.pop(idx)
    return True


def _move_resize(config, slots):
    """Core olmayan bir perdenin uzunluğunu 1m artır/azalt."""
    non_core = [i for i, p in enumerate(config.placements) if not p.is_core]
    if not non_core:
        return False
    idx = random.choice(non_core)
    p = config.placements[idx]
    slot = next((s for s in slots if s.slot_id == p.slot_id), None)
    if slot is None:
        return False
    avail = get_available_lengths_for_slot(slot)
    if len(avail) <= 1:
        return False
    # Mevcut uzunluğun indeksi
    try:
        cur_idx = avail.index(p.length_m)
    except ValueError:
        # Mevcut uzunluk listede yok (ör. özel değer) — skip
        return False
    # Yukarı veya aşağı
    direction = random.choice([-1, 1])
    new_idx = cur_idx + direction
    if new_idx < 0 or new_idx >= len(avail):
        return False
    new_length = avail[new_idx]
    p.length_m = new_length
    # Center da güncellenir (segment ortasında kalıyor)
    seg_mid = (slot.segment_start + slot.segment_end) / 2
    if slot.orientation == "Y":
        p.center = (slot.axis_coord, seg_mid)
    else:
        p.center = (seg_mid, slot.axis_coord)
    return True


def _move_swap(config, slots, story_count):
    """Mevcut bir perdeyi boş bir slota taşı (aynı yönde). Aks limiti korunur."""
    bw_cm = get_wall_thickness(story_count)
    non_core = [i for i, p in enumerate(config.placements) if not p.is_core]
    if not non_core:
        return False
    idx = random.choice(non_core)
    old_p = config.placements[idx]
    old_axis = old_p.slot_id.split('-seg')[0] if '-seg' in old_p.slot_id else old_p.slot_id
    used = {p.slot_id for p in config.placements}

    def _target_ok(s):
        if s.slot_id in used:
            return False
        if s.orientation != old_p.orientation:
            return False
        target_axis = s.axis_label
        if target_axis == old_axis:
            return True
        current = _axis_count(config.placements, target_axis)
        return current < MAX_WALLS_PER_AXIS

    empty_ok = [s for s in slots if _target_ok(s)]
    if not empty_ok:
        return False
    new_slot = random.choice(empty_ok)
    avail = get_available_lengths_for_slot(new_slot)
    if not avail:
        return False
    target_len = old_p.length_m
    chosen = min(avail, key=lambda L: abs(L - target_len))
    new_p = _slot_to_placement(new_slot, chosen, bw_cm)
    config.placements[idx] = new_p
    return True


def _apply_random_move(config, slots, story_count, grid, Lx, Ly, temperature, t_initial):
    """Rastgele bir hamle uygula. SWAP sadece sıcak fazda."""
    swap_allowed = temperature > t_initial * SA_SWAP_TEMP_THRESHOLD
    moves = ["add", "remove", "resize"]
    if swap_allowed:
        moves.append("swap")
    weights = [2, 1, 3, 2] if swap_allowed else [2, 1, 3]
    move = random.choices(moves, weights=weights, k=1)[0]

    if move == "add":
        return _move_add(config, slots, story_count, grid, Lx, Ly), move
    elif move == "remove":
        return _move_remove(config), move
    elif move == "resize":
        return _move_resize(config, slots), move
    elif move == "swap":
        return _move_swap(config, slots, story_count), move
    return False, move


# ===================================================
# SIMULATED ANNEALING
# ===================================================

def simulated_annealing(
    initial_config,
    grid, Lx, Ly, columns,
    story_count,
    iterations: Optional[int] = None,
    verbose: bool = False,
    seed: Optional[int] = None,
):
    """
    Simulated annealing ile konfigürasyonu iyileştir.

    Args:
        initial_config: build_initial_configuration'dan gelen
        iterations: None → dinamik (slot × 75, min 500)
        verbose: True → ara sonuçları yazdır
        seed: rastgele tohum (reproducibility)

    Returns:
        (best_config, history)  — en iyi bulunan ve skor geçmişi
    """
    if seed is not None:
        random.seed(seed)

    slots = generate_wall_slots(grid, Lx, Ly, core=None)  # tüm slotlar

    if iterations is None:
        iterations = max(SA_MIN_ITERATIONS, len(slots) * SA_ITER_PER_SLOT)

    # Başlangıç skorunu hesapla
    current = copy.deepcopy(initial_config)
    current = evaluate_configuration_relaxed(current, grid, Lx, Ly, columns)
    best = copy.deepcopy(current)
    best_score = current.score

    t_initial = SA_INITIAL_TEMP
    T = t_initial
    alpha = SA_COOLING_ALPHA ** (1.0 / max(1, iterations // 100))  # 100 adımda α^(1/100)
    # Yukarıdaki α ayarı: toplam cooling'in SA_COOLING_ALPHA'ya düşmesi için iterasyonla normalize

    # Aslında daha standart: geometric cooling, T *= alpha her adımda
    # alpha'yı öyle seçeriz ki iterations adım sonunda T = T_min
    # T_min = T_initial × α^N  →  α = (T_min / T_initial) ^ (1/N)
    alpha = (SA_MIN_TEMP / t_initial) ** (1.0 / iterations)

    history = []
    accepted = 0
    move_counts = {"add": 0, "remove": 0, "resize": 0, "swap": 0}

    for it in range(iterations):
        # Hamleyi bir kopya üzerinde dene
        candidate = copy.deepcopy(current)
        success, move = _apply_random_move(
            candidate, slots, story_count, grid, Lx, Ly, T, t_initial
        )
        if not success:
            T *= alpha
            continue

        candidate = evaluate_configuration_relaxed(candidate, grid, Lx, Ly, columns)
        delta = candidate.score - current.score

        if delta <= 0:
            # Daha iyi, kabul et
            current = candidate
            accepted += 1
            move_counts[move] += 1
            if candidate.score < best_score:
                best = copy.deepcopy(candidate)
                best_score = candidate.score
        else:
            # Olasılıkla kabul
            if T > 0 and random.random() < math.exp(-delta / T):
                current = candidate
                accepted += 1
                move_counts[move] += 1

        history.append((it, T, current.score, best_score))
        T *= alpha

        if verbose and it % max(1, iterations // 20) == 0:
            print(f"  iter {it:5d}  T={T:.4f}  cur={current.score:.4f}  best={best_score:.4f}")

    if verbose:
        print(f"  Toplam {iterations} iter, kabul={accepted} ({accepted*100//iterations}%)")
        print(f"  Hamleler: {move_counts}")

    return best, history


# ===================================================
# ANA FONKSİYON
# ===================================================

def optimize_wall_placement(
    grid, Lx: float, Ly: float,
    columns: List[ColumnOutput],
    core_candidates: List[CoreOutput],
    story_count: int,
    top_n: int = 3,
    iterations: Optional[int] = None,
    verbose: bool = False,
    seed: Optional[int] = None,
) -> List[WallConfiguration]:
    """
    Ana optimizasyon — Parça 2 + Parça 3.

    1. Her core aday için greedy başlangıç + SA optimizasyonu
    2. Bir de random restart (farklı perde başlangıçlı SA)
    3. Top N konfigürasyonu döndür (skor sıralı)

    seismic_validator bu listeyi alıp her birini modal analize sokacak.
    """
    if not core_candidates:
        return []

    all_results = []

    # Her core aday için SA
    for i, core in enumerate(core_candidates):
        if verbose:
            print(f"\n--- Core aday {i}: {core.center} ---")

        initial = build_initial_configuration(grid, Lx, Ly, core, story_count, i)
        # Greedy skoru
        initial_eval = copy.deepcopy(initial)
        initial_eval = evaluate_configuration_relaxed(initial_eval, grid, Lx, Ly, columns)
        if verbose:
            print(f"  Greedy skor: {initial_eval.score:.4f}")

        best, _ = simulated_annealing(
            initial, grid, Lx, Ly, columns, story_count,
            iterations=iterations, verbose=verbose,
            seed=(seed + i) if seed is not None else None,
        )
        all_results.append(best)

    # Random restart — 1 tane ek
    if top_n >= 3 and core_candidates:
        if verbose:
            print(f"\n--- Random restart ---")
        # En iyi core ile başla, ama SA başlangıcını rastgele bozuk al
        core = core_candidates[0]
        initial = build_initial_configuration(grid, Lx, Ly, core, story_count, 0)
        # Birkaç rastgele REMOVE/ADD yap (bozarak yeniden başla)
        if seed is not None:
            random.seed(seed + 100)
        slots_all = generate_wall_slots(grid, Lx, Ly, core=None)
        for _ in range(min(5, len(initial.placements) // 2)):
            if random.random() < 0.5:
                _move_remove(initial)
            else:
                _move_add(initial, slots_all, story_count, grid, Lx, Ly)
        best_rr, _ = simulated_annealing(
            initial, grid, Lx, Ly, columns, story_count,
            iterations=iterations, verbose=False,
            seed=(seed + 200) if seed is not None else None,
        )
        all_results.append(best_rr)

    # Skor sırasına göre en iyileri döndür
    all_results.sort(key=lambda c: c.score)
    return all_results[:top_n]
