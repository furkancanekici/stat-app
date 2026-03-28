"""
Yapısal kural motoru — TBDY 2018 + TS 500

Kontroller:
1. Kapasite (Unity Check) sınıflandırması
2. Gevrek/sünek ayrımı
3. TS 500 min/max donatı oranı (ρ)
4. Kesme donatısı yeterliliği
5. Birleşim bölgesi (BC ratio, JS ratio)
6. Göreli kat ötelemesi (δi/hi) — TBDY Tablo 4.9
7. Burulma düzensizliği (ηbi) — TBDY Tablo 3.6
8. Kesme kapasitesi / kesme talebi (Vr/Vd)
9. Süneklik düzeyi bazlı kontroller
"""

from app.models.unified_element import Status

# ═══════ EŞİK DEĞERLERİ ═══════

THRESHOLDS = {"ok": 0.90, "warning": 1.00, "fail": 1.00}

BRITTLE_KEYWORDS = [
    "shear", "kesme", "torsion", "burulma",
    "buckling", "burkulma", "compression", "basinc"
]

# TBDY 2018 Tablo 4.9 — Göreli kat ötelemesi sınırları
DRIFT_LIMITS = {
    "concrete": 0.008,   # Betonarme çerçeve
    "steel": 0.016,      # Çelik çerçeve
    "default": 0.008,
}

# TBDY Tablo 3.6 — Burulma düzensizliği
TORSION_LIMIT = 1.2  # ηbi > 1.2 → A1b düzensizliği

# TS 500 / TBDY donatı oranı limitleri (varsayılan C30, S420)
DEFAULT_FYK = 420
DEFAULT_FCK = 30


# ═══════ ANA SINIFLANDIRMA ═══════

def classify_status(uc, fm):
    if uc is None:
        return Status.UNMATCHED
    is_brittle = any(kw in (fm or "").lower() for kw in BRITTLE_KEYWORDS)
    if uc >= THRESHOLDS["fail"]:
        return Status.BRITTLE if is_brittle else Status.FAIL
    if uc >= THRESHOLDS["ok"]:
        return Status.WARNING
    return Status.OK


def get_status_color(status):
    return {
        Status.OK: "#22c55e", Status.WARNING: "#eab308",
        Status.FAIL: "#ef4444", Status.BRITTLE: "#f97316",
        Status.UNMATCHED: "#64748b",
    }.get(status, "#64748b")


# ═══════ DONATI ORANI KONTROLÜ ═══════

def check_rebar_ratio(el, fck=DEFAULT_FCK, fyk=DEFAULT_FYK):
    result = {"rho": None, "rho_min": None, "rho_max": None, "rho_status": None, "rho_warning": None}

    sec_d = el.get("sec_depth")
    sec_w = el.get("sec_width")
    is_beam = el.get("ifc_type") == "IfcBeam"
    is_column = el.get("ifc_type") == "IfcColumn"
    if not sec_d or not sec_w or sec_d <= 0 or sec_w <= 0:
        return result

    b_mm = sec_w * 1000
    h_mm = sec_d * 1000
    gross_area = b_mm * h_mm

    if is_column:
        as_total = el.get("as_total")
        if not as_total or as_total <= 0:
            return result
        rho = as_total / gross_area
        rho_min = 0.01          # TBDY 7.3.4.1 → %1
        rho_max = 0.04          # TBDY 7.3.4.1 → %4
    elif is_beam:
        as_max = max(el.get("as_top") or 0, el.get("as_bot") or 0)
        if as_max <= 0:
            return result
        d_eff = h_mm * 0.9
        rho = as_max / (b_mm * d_eff)
        rho_min = 0.8 / fyk     # TS 500 7.3
        rho_max = 0.04
    else:
        return result

    result["rho"] = round(rho, 5)
    result["rho_min"] = round(rho_min, 5)
    result["rho_max"] = round(rho_max, 5)

    if rho < rho_min:
        result["rho_status"] = "MIN_FAIL"
        result["rho_warning"] = f"ρ={rho:.4f} < ρ_min={rho_min:.4f} — Min. donatı yetersiz (TS 500)"
    elif rho > rho_max:
        result["rho_status"] = "MAX_FAIL"
        result["rho_warning"] = f"ρ={rho:.4f} > ρ_max={rho_max:.2f} — Aşırı donatı (TBDY 7.3.4)"
    else:
        result["rho_status"] = "OK"
    return result


# ═══════ KESME DONATISI ═══════

def check_shear_rebar(el):
    result = {"shear_status": None, "shear_warning": None}
    v_rebar = el.get("v_rebar")
    if v_rebar is None:
        return result
    if v_rebar > 1000:
        result["shear_status"] = "CRITICAL"
        result["shear_warning"] = f"Kesme donatısı çok yüksek ({v_rebar:.0f} mm²/m) — gevrek göçme riski"
    elif v_rebar > 500:
        result["shear_status"] = "WARNING"
        result["shear_warning"] = f"Kesme donatısı yüksek ({v_rebar:.0f} mm²/m)"
    else:
        result["shear_status"] = "OK"
    return result


# ═══════ BİRLEŞİM BÖLGESİ ═══════

def check_joint(joint_data):
    result = {
        "bc_ratio_maj": None, "bc_ratio_min": None, "bc_status": None, "bc_warning": None,
        "js_ratio_maj": None, "js_ratio_min": None, "js_status": None, "js_warning": None,
    }
    bc_maj = joint_data.get("bc_maj_ratio")
    bc_min = joint_data.get("bc_min_ratio")
    js_maj = joint_data.get("js_maj_ratio")
    js_min = joint_data.get("js_min_ratio")

    if bc_maj is not None:
        result["bc_ratio_maj"] = round(bc_maj, 3)
        result["bc_ratio_min"] = round(bc_min, 3) if bc_min else None
        bc_max = max(bc_maj, bc_min or 0)
        if bc_max >= 1.0:
            result["bc_status"] = "FAIL"
            result["bc_warning"] = f"Zayıf kolon — BCRatio={bc_max:.3f} ≥ 1.0 (TBDY 7.3.3 ihlali)"
        elif bc_max >= 1.0 / 1.2:
            result["bc_status"] = "WARNING"
            result["bc_warning"] = f"Sınırda — BCRatio={bc_max:.3f} (limit ≤ 0.833)"
        else:
            result["bc_status"] = "OK"

    if js_maj is not None:
        result["js_ratio_maj"] = round(js_maj, 3)
        result["js_ratio_min"] = round(js_min, 3) if js_min else None
        js_max = max(js_maj, js_min or 0)
        if js_max >= 1.0:
            result["js_status"] = "FAIL"
            result["js_warning"] = f"Birleşim kesme aşımı — JSRatio={js_max:.3f} ≥ 1.0"
        else:
            result["js_status"] = "OK"

    return result


# ═══════ KAT ÖTELEMESİ (TBDY 4.9) ═══════

def check_drift(story, drift_map, structure_type="concrete"):
    """
    story: normalize edilmiş kat adı
    drift_map: {story: {max_drift, direction, ...}}
    """
    result = {"drift_value": None, "drift_limit": None, "drift_status": None, "drift_warning": None}

    data = drift_map.get(story)
    if not data:
        return result

    drift = data.get("max_drift")
    if drift is None:
        return result

    limit = DRIFT_LIMITS.get(structure_type, DRIFT_LIMITS["default"])
    result["drift_value"] = round(drift, 6)
    result["drift_limit"] = limit

    if drift > limit:
        result["drift_status"] = "FAIL"
        result["drift_warning"] = f"Kat ötelemesi δ={drift:.5f} > {limit} (TBDY Tablo 4.9)"
    elif drift > limit * 0.8:
        result["drift_status"] = "WARNING"
        result["drift_warning"] = f"Kat ötelemesi sınıra yakın δ={drift:.5f} (limit: {limit})"
    else:
        result["drift_status"] = "OK"

    return result


# ═══════ BURULMA DÜZENSİZLİĞİ (TBDY 3.6) ═══════

def check_torsion(story, torsion_map):
    result = {"torsion_ratio": None, "torsion_status": None, "torsion_warning": None}

    data = torsion_map.get(story)
    if not data:
        return result

    ratio = data.get("max_ratio")
    if ratio is None:
        return result

    result["torsion_ratio"] = round(ratio, 3)

    if ratio > 2.0:
        result["torsion_status"] = "FAIL"
        result["torsion_warning"] = f"Ağır burulma düzensizliği ηbi={ratio:.3f} > 2.0 (TBDY Tablo 3.6)"
    elif ratio > TORSION_LIMIT:
        result["torsion_status"] = "WARNING"
        result["torsion_warning"] = f"Burulma düzensizliği ηbi={ratio:.3f} > {TORSION_LIMIT} (A1b düzensizliği)"
    else:
        result["torsion_status"] = "OK"

    return result


# ═══════ KESME KAPASİTESİ / KESME TALEBİ ═══════

def check_shear_demand(el, forces_data, fck=DEFAULT_FCK):
    """
    Basit kesme kapasitesi kontrolü.
    Vr = 0.65 × fctd × bw × d (beton katkısı, TS 500 8.1)
    fctd = 0.35 × √fck (TS 500)
    """
    result = {"vd": None, "vr_approx": None, "vr_vd_ratio": None, "vr_vd_status": None, "vr_vd_warning": None}

    if not forces_data:
        return result

    vd = forces_data.get("v_max")
    if not vd or vd <= 0:
        return result

    sec_d = el.get("sec_depth")
    sec_w = el.get("sec_width")
    if not sec_d or not sec_w:
        return result

    # TS 500 beton kesme kapasitesi (basitleştirilmiş)
    import math
    fctd = 0.35 * math.sqrt(fck)  # MPa
    bw = sec_w * 1000  # mm
    d = sec_d * 1000 * 0.9  # mm (efektif yükseklik)
    vr_concrete = 0.65 * fctd * bw * d / 1000  # kN

    result["vd"] = round(vd, 1)
    result["vr_approx"] = round(vr_concrete, 1)

    ratio = vr_concrete / vd if vd > 0 else 999
    result["vr_vd_ratio"] = round(ratio, 2)

    if ratio < 1.0:
        result["vr_vd_status"] = "FAIL"
        result["vr_vd_warning"] = f"Kesme talebi > beton kapasitesi: Vd={vd:.0f}kN > Vr={vr_concrete:.0f}kN — donatı gerekli"
    elif ratio < 1.5:
        result["vr_vd_status"] = "WARNING"
        result["vr_vd_warning"] = f"Kesme talebi yüksek: Vd={vd:.0f}kN, Vr={vr_concrete:.0f}kN (oran: {ratio:.2f})"
    else:
        result["vr_vd_status"] = "OK"

    return result


# ═══════ ANA UYGULAMA ═══════

def apply_rules(
    elements,
    joint_map=None,
    drift_map=None,
    torsion_map=None,
    forces_map=None,
    materials=None,
    seismic_params=None,
):
    if joint_map is None: joint_map = {}
    if drift_map is None: drift_map = {}
    if torsion_map is None: torsion_map = {}
    if forces_map is None: forces_map = {}
    if materials is None: materials = {}
    if seismic_params is None: seismic_params = {}

    # Malzeme dayanımları
    fck = materials.get("concrete", {}).get("fck", DEFAULT_FCK)
    fyk = materials.get("rebar", {}).get("fyk", DEFAULT_FYK)

    # Yapı tipi (süneklik için R değerine bak)
    r_val = seismic_params.get("R")
    ductility_level = "high" if r_val and r_val >= 6 else "limited" if r_val else "unknown"

    for el in elements:
        uc = el.get("unity_check")
        fm = el.get("failure_mode", "")
        story = el.get("ifc_story", "")
        label = el.get("ifc_name", "")

        # 1) Temel status
        status = classify_status(uc, fm)
        el["status"] = status.value
        el["status_color"] = get_status_color(status)

        # 2) Overstressed
        el["overstressed"] = "overstressed" in (fm or "").lower()

        # 3) Donatı oranı
        rebar = check_rebar_ratio(el, fck, fyk)
        el.update(rebar)

        # 4) Kesme donatısı
        shear = check_shear_rebar(el)
        el.update(shear)

        # 5) Birleşim bölgesi (kolon)
        jt_key = (story, label)
        jt_data = joint_map.get(jt_key, {})
        if jt_data:
            jt = check_joint(jt_data)
            el.update(jt)

        # 6) Kat ötelemesi
        drift = check_drift(story, drift_map)
        el.update(drift)

        # 7) Burulma düzensizliği
        torsion = check_torsion(story, torsion_map)
        el.update(torsion)

        # 8) Kesme kapasitesi/talebi
        force_key = (story, label)
        force_data = forces_map.get(force_key, {})
        vr_vd = check_shear_demand(el, force_data, fck)
        el.update(vr_vd)

        # 9) Süneklik düzeyi bilgisi
        el["ductility_level"] = ductility_level
        el["fck"] = fck
        el["fyk"] = fyk

        # Malzeme bilgisi
        el["material_concrete"] = materials.get("concrete", {}).get("grade", f"C{fck}")
        el["material_rebar"] = materials.get("rebar", {}).get("name", f"S{fyk}")

        # Deprem parametreleri
        if seismic_params:
            el["seismic_R"] = seismic_params.get("R")
            el["seismic_SDS"] = seismic_params.get("SDS")

        # 10) Toplam uyarı listesi
        warnings = []
        if rebar.get("rho_warning"): warnings.append(rebar["rho_warning"])
        if shear.get("shear_warning"): warnings.append(shear["shear_warning"])
        if jt_data:
            jt_res = check_joint(jt_data)
            if jt_res.get("bc_warning"): warnings.append(jt_res["bc_warning"])
            if jt_res.get("js_warning"): warnings.append(jt_res["js_warning"])
        if drift.get("drift_warning"): warnings.append(drift["drift_warning"])
        if torsion.get("torsion_warning"): warnings.append(torsion["torsion_warning"])
        if vr_vd.get("vr_vd_warning"): warnings.append(vr_vd["vr_vd_warning"])

        el["warnings"] = warnings
        el["warning_count"] = len(warnings)

    return elements
