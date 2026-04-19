"""
Preliminary Design Module
-------------------------
Rule-based preliminary structural design for RC buildings per TBDY 2018 + TS 500.

Pipeline:
    INPUT -> axis_generator -> core_placer -> load_calculator ->
    column_sizer -> beam_sizer -> slab_designer -> wall_optimizer ->
    seismic_validator (OpenSeesPy) -> OUTPUT

Entry point: orchestrator.run_preliminary_design(input)
"""
