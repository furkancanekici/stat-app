"""
Orchestrator — Preliminary Design Pipeline
"""
from typing import List, Optional
from .schemas import (
    PreliminaryInput, PreliminaryOutput, DesignWarning,
    ColumnOutput, WallOutput, CoreOutput,
)
from .constants import auto_select_material
from . import (
    axis_generator, load_calculator, column_sizer, beam_sizer,
    slab_designer, core_placer, wall_optimizer, seismic_validator,
)

MAX_WALL_ITERATION = 3


def run_preliminary_design(
    input_data: PreliminaryInput,
    skip_modal: bool = False,
    sa_iterations: Optional[int] = None,
) -> PreliminaryOutput:
    """
    Ana pipeline. PreliminaryInput → PreliminaryOutput.
    
    Args:
        skip_modal: True → OpenSeesPy modal analiz atlanır (hızlı debug)
        sa_iterations: None → dinamik; int → sabit SA iterasyonu
    """
    warnings: List[DesignWarning] = []
    inp = input_data
    
    # 1. GRID
    grid = axis_generator.generate_grid(inp.Lx, inp.Ly)
    grid_warnings = axis_generator.validate_grid(grid)
    for w in grid_warnings:
        warnings.append(DesignWarning(severity="warning", rule="aks düzeni", message=w))

    # 1.5 MALZEME AUTO-SELECT
    auto_fck, auto_fyk = auto_select_material(inp.story_count)
    _user_mat = inp.material
    if _user_mat is None:
        final_fck, final_fyk = auto_fck, auto_fyk
    else:
        final_fck = _user_mat.fck if _user_mat.fck is not None else auto_fck
        final_fyk = _user_mat.fyk if _user_mat.fyk is not None else auto_fyk
    auto_used = (inp.material is None) or (final_fck is None)
    if auto_used:
        warnings.append(DesignWarning(
            severity="info", rule="malzeme",
            message=f"Kat sayısı {inp.story_count} için otomatik seçim: "
                    f"C{int(final_fck)} beton, B{int(final_fyk)}C donatı"
        ))
    
    # 2. LOADS (faktörlü)
    design_loads = load_calculator.compute_column_design_loads(
        grid, inp.story_count, inp.usage
    )
    
    # 3. COLUMNS
    cols = column_sizer.size_all_columns(
        grid, design_loads, inp.story_count, final_fck
    )
    
    # 4. SLABS (asmolen, kirişten önce çünkü h=hf gerekir)
    slabs = slab_designer.design_all_slabs(grid, inp.story_count)
    
    # 5. BEAMS
    cols_zemin = {(c.x, c.y): c for c in cols if c.story == 1}
    cols_by_pos = {}
    for xi, xv in enumerate(grid.x_axes):
        for yi, yv in enumerate(grid.y_axes):
            cols_by_pos[(xi, yi)] = cols_zemin[(xv, yv)]
    beams = beam_sizer.size_all_beams(
        grid, cols_by_pos, inp.story_count, slabs[0].total_thickness_cm
    )
    
    # 6. CORE (top-2 aday döndürür)
    core_candidates = core_placer.place_core(
        grid, inp.Lx, inp.Ly, inp.core, cols, inp.story_count
    )
    
    # Çekirdek varsa kolonları temizle
    if core_candidates:
        primary_core = core_candidates[0]
        cols_cleaned = core_placer.remove_core_columns(
            cols, primary_core.removed_column_ids
        )
    else:
        primary_core = None
        cols_cleaned = cols
    
    # 7. WALL OPTIMIZATION
    if core_candidates:
        top_configs = wall_optimizer.optimize_wall_placement(
            grid, inp.Lx, inp.Ly, cols_cleaned, core_candidates,
            inp.story_count, top_n=3, iterations=sa_iterations, seed=42,
        )
    else:
        # Çekirdek yok → sadece çevresel perdeler
        # Bir "dummy" core olmadan optimize (TODO — basit versiyon)
        top_configs = []
    
    # 8. SEISMIC VALIDATION
    modal_result = None
    final_walls: List[WallOutput] = []
    
    if not skip_modal and top_configs:
        G, Q, n = load_calculator.get_loads_for_usage(inp.usage)
        best_config, modal_results = seismic_validator.validate_configurations(
            candidates=top_configs,
            columns=cols_cleaned,
            beams=beams,
            slabs=slabs,
            story_height_m=inp.story_height_m,
            fck_MPa=final_fck,
            Lx=inp.Lx, Ly=inp.Ly,
            story_count=inp.story_count,
            usage_G=G, usage_Q=Q, n_factor=n,
        )
        
        if best_config is not None:
            final_walls = wall_optimizer._placements_to_wall_outputs(best_config.placements)
            # Hangi adayın seçildiğini bul
            chosen_idx = top_configs.index(best_config)
            modal_result = modal_results[chosen_idx]
        else:
            # Hiçbiri geçmedi — en iyi skoru al
            final_walls = wall_optimizer._placements_to_wall_outputs(top_configs[0].placements)
            modal_result = modal_results[0]
            warnings.append(DesignWarning(
                severity="error", rule="TBDY 3.6",
                message=f"Burulma düzensizliği sınırı (ηbi<{seismic_validator.ETABI_LIMIT}) sağlanamadı. "
                        f"En düşük ηbi: X={modal_result.eta_bi_x:.3f}, Y={modal_result.eta_bi_y:.3f}"
            ))
    elif top_configs:
        # Modal skip — geometrik en iyi
        final_walls = wall_optimizer._placements_to_wall_outputs(top_configs[0].placements)
    
    # 9. TOPLAM BETON HACMİ
    total_concrete = 0.0
    for c in cols:
        total_concrete += (c.width_cm/100) * (c.depth_cm/100) * inp.story_height_m
    for b in beams:
        total_concrete += (b.width_cm/100) * (b.height_cm/100) * b.span_m
    for w in final_walls:
        total_concrete += (w.thickness_cm/100) * w.length_m * inp.story_height_m * \
                         (w.story_range[1] - w.story_range[0] + 1)
    for s in slabs:
        # Asmolen yaklaşık hacmi: dişler + üst plak
        # Basitlik için: 0.5 × toplam h × plan alanı (dişler yarısı dolu)
        total_concrete += 0.5 * (s.total_thickness_cm/100) * inp.Lx * inp.Ly
    
    # 10. PERDE ALAN ORANI
    Afloor = inp.Lx * inp.Ly
    wall_area_x = sum(w.length_m * (w.thickness_cm/100) for w in final_walls if w.orientation == "X")
    wall_area_y = sum(w.length_m * (w.thickness_cm/100) for w in final_walls if w.orientation == "Y")
    
    return PreliminaryOutput(
        input=inp,
        grid=grid,
        columns=[c for c in cols if c.id not in (primary_core.removed_column_ids if primary_core else [])],
        beams=beams,
        walls=final_walls,
        slabs=slabs,
        core=primary_core,
        total_concrete_volume_m3=total_concrete,
        total_wall_area_ratio_x=wall_area_x / Afloor,
        total_wall_area_ratio_y=wall_area_y / Afloor,
        modal_result=modal_result,
        warnings=warnings,
        design_iterations=1,
        success=(len(warnings) == 0 or all(w.severity != "error" for w in warnings)),
    )
