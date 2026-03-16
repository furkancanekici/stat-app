from app.models.unified_element import Status

# ═══════ EŞİK DEĞERLERİ ═══════

THRESHOLDS = {
    "ok": 0.90,
    "warning": 1.00,
    "fail": 1.00,
}

BRITTLE_KEYWORDS = [
    "shear", "kesme", "torsion", "burulma",
    "buckling", "burkulma", "compression", "basinc"
]

# TS 500 / TBDY varsayılan malzeme değerleri
DEFAULT_FYK = 420   # MPa — S420 donatı çeliği
DEFAULT_FCK = 30    # MPa — C30 beton

# Donatı oranı limitleri
RHO_MIN_BEAM = 0.8 / DEFAULT_FYK          # TS 500 7.3 → ≈ 0.0019
RHO_MAX_BEAM = 0.04                        # TS 500 max
RHO_MIN_COL = 0.01                         # TBDY 7.3.4.1 min → %1
RHO_MAX_COL = 0.04                         # TBDY 7.3.4.1 max → %4

# Birleşim bölgesi eşikleri (BCRatio = ΣMr_beam / ΣMr_column)
BC_RATIO_SAFE = 1.0 / 1.2                  # ≈ 0.833 → güçlü kolon sağlanıyor
BC_RATIO_FAIL = 1.0                        # ≥ 1.0 → zayıf kolon

# Joint Shear eşiği
JS_RATIO_FAIL = 1.0                        # ≥ 1.0 → birleşim kesme aşımı


# ═══════ ANA SINIFLANDIRMA ═══════

def classify_status(
    unity_check: float | None,
    failure_mode: str | None
) -> Status:
    if unity_check is None:
        return Status.UNMATCHED

    fm = (failure_mode or "").lower()
    is_brittle = any(kw in fm for kw in BRITTLE_KEYWORDS)

    if unity_check >= THRESHOLDS["fail"]:
        if is_brittle:
            return Status.BRITTLE
        return Status.FAIL

    if unity_check >= THRESHOLDS["ok"]:
        return Status.WARNING

    return Status.OK


def get_status_color(status: Status) -> str:
    colors = {
        Status.OK:        "#22c55e",
        Status.WARNING:   "#eab308",
        Status.FAIL:      "#ef4444",
        Status.BRITTLE:   "#f97316",
        Status.UNMATCHED: "#64748b",
    }
    return colors.get(status, "#64748b")


# ═══════ DONATI ORANI KONTROLÜ ═══════

def check_rebar_ratio(el: dict) -> dict:
    """
    TS 500 / TBDY minimum ve maksimum donatı oranı kontrolü.
    Kesit boyutları (sec_depth, sec_width) ve donatı miktarı (as_total) gerekli.

    Returns:
        dict: rho, rho_min, rho_max, rho_status, rho_warning
    """
    result = {
        "rho": None,
        "rho_min": None,
        "rho_max": None,
        "rho_status": None,      # "OK", "MIN_FAIL", "MAX_FAIL"
        "rho_warning": None,     # Uyarı mesajı
    }

    sec_d = el.get("sec_depth")
    sec_w = el.get("sec_width")
    is_beam = el.get("ifc_type") == "IfcBeam"
    is_column = el.get("ifc_type") == "IfcColumn"

    if not sec_d or not sec_w or sec_d <= 0 or sec_w <= 0:
        return result

    # Brüt kesit alanı (mm²)
    b_mm = sec_w * 1000   # m → mm
    h_mm = sec_d * 1000   # m → mm
    gross_area = b_mm * h_mm  # mm²

    if is_column:
        as_total = el.get("as_total")
        if as_total is None or as_total <= 0:
            return result

        rho = as_total / gross_area
        rho_min = RHO_MIN_COL
        rho_max = RHO_MAX_COL

    elif is_beam:
        # Kiriş: üst veya alt donatı — efektif yükseklik d ≈ 0.9h
        as_top = el.get("as_top") or 0
        as_bot = el.get("as_bot") or 0
        as_max = max(as_top, as_bot)
        if as_max <= 0:
            return result

        d_eff = h_mm * 0.9  # efektif yükseklik yaklaşımı
        rho = as_max / (b_mm * d_eff)
        rho_min = RHO_MIN_BEAM
        rho_max = RHO_MAX_BEAM
    else:
        return result

    result["rho"] = round(rho, 5)
    result["rho_min"] = round(rho_min, 5)
    result["rho_max"] = round(rho_max, 5)

    if rho < rho_min:
        result["rho_status"] = "MIN_FAIL"
        result["rho_warning"] = f"ρ = {rho:.4f} < ρ_min = {rho_min:.4f} — Minimum donatı yetersiz"
    elif rho > rho_max:
        result["rho_status"] = "MAX_FAIL"
        result["rho_warning"] = f"ρ = {rho:.4f} > ρ_max = {rho_max:.4f} — Aşırı donatı, sünek davranış riski"
    else:
        result["rho_status"] = "OK"
        result["rho_warning"] = None

    return result


# ═══════ KESME DONATISI KONTROLÜ ═══════

def check_shear_rebar(el: dict) -> dict:
    """
    Kesme donatısı yeterliliği kontrolü.
    VRebar > 0 ise kesme donatısı gerekli.
    Çok yüksek VRebar → gevrek göçme riski.
    """
    result = {
        "shear_status": None,
        "shear_warning": None,
    }

    v_rebar = el.get("v_rebar")
    if v_rebar is None:
        return result

    if v_rebar <= 0:
        result["shear_status"] = "OK"
    elif v_rebar > 1000:  # mm²/m — çok yüksek kesme donatısı
        result["shear_status"] = "CRITICAL"
        result["shear_warning"] = f"Kesme donatısı çok yüksek ({v_rebar:.0f} mm²/m) — gevrek göçme riski"
    elif v_rebar > 500:
        result["shear_status"] = "WARNING"
        result["shear_warning"] = f"Kesme donatısı yüksek ({v_rebar:.0f} mm²/m)"
    else:
        result["shear_status"] = "OK"

    return result


# ═══════ BİRLEŞİM BÖLGESİ KONTROLÜ ═══════

def check_joint(joint_data: dict) -> dict:
    """
    Kolon-kiriş birleşim bölgesi kontrolü.
    BCRatio = ΣMr_beam / ΣMr_column
    JSRatio = birleşim kesme oranı
    """
    result = {
        "bc_ratio_maj": None,
        "bc_ratio_min": None,
        "bc_status": None,       # "OK", "WARNING", "FAIL"
        "bc_warning": None,
        "js_ratio_maj": None,
        "js_ratio_min": None,
        "js_status": None,       # "OK", "FAIL"
        "js_warning": None,
    }

    bc_maj = joint_data.get("bc_maj_ratio")
    bc_min = joint_data.get("bc_min_ratio")
    js_maj = joint_data.get("js_maj_ratio")
    js_min = joint_data.get("js_min_ratio")

    # Güçlü kolon — zayıf kiriş kontrolü
    if bc_maj is not None:
        result["bc_ratio_maj"] = round(bc_maj, 3)
        result["bc_ratio_min"] = round(bc_min, 3) if bc_min is not None else None
        bc_max_val = max(bc_maj, bc_min or 0)

        if bc_max_val >= BC_RATIO_FAIL:
            result["bc_status"] = "FAIL"
            result["bc_warning"] = f"Zayıf kolon — BCRatio = {bc_max_val:.3f} ≥ 1.0 (TBDY 7.3.3 ihlali)"
        elif bc_max_val >= BC_RATIO_SAFE:
            result["bc_status"] = "WARNING"
            result["bc_warning"] = f"Sınırda — BCRatio = {bc_max_val:.3f} (TBDY limiti: ≤ 0.833)"
        else:
            result["bc_status"] = "OK"

    # Birleşim kesme kontrolü
    if js_maj is not None:
        result["js_ratio_maj"] = round(js_maj, 3)
        result["js_ratio_min"] = round(js_min, 3) if js_min is not None else None
        js_max_val = max(js_maj, js_min or 0)

        if js_max_val >= JS_RATIO_FAIL:
            result["js_status"] = "FAIL"
            result["js_warning"] = f"Birleşim kesme aşımı — JSRatio = {js_max_val:.3f} ≥ 1.0"
        else:
            result["js_status"] = "OK"

    return result


# ═══════ ANA UYGULAMA ═══════

def apply_rules(elements: list[dict], joint_map: dict = None) -> list[dict]:
    """
    Tüm kuralları uygula.

    Args:
        elements: eleman listesi
        joint_map: {label: {bc_maj_ratio, bc_min_ratio, js_maj_ratio, js_min_ratio}}
    """
    if joint_map is None:
        joint_map = {}

    for el in elements:
        uc = el.get("unity_check")
        fm = el.get("failure_mode", "")

        # 1) Temel status sınıflandırma
        status = classify_status(uc, fm)
        el["status"] = status.value
        el["status_color"] = get_status_color(status)

        # 2) Overstressed özel kontrol
        if fm and "overstressed" in fm.lower():
            el["overstressed"] = True
        else:
            el["overstressed"] = False

        # 3) Donatı oranı kontrolü
        rebar_check = check_rebar_ratio(el)
        el["rho"] = rebar_check["rho"]
        el["rho_min"] = rebar_check["rho_min"]
        el["rho_max"] = rebar_check["rho_max"]
        el["rho_status"] = rebar_check["rho_status"]
        el["rho_warning"] = rebar_check["rho_warning"]

        # 4) Kesme donatısı kontrolü
        shear_check = check_shear_rebar(el)
        el["shear_status"] = shear_check["shear_status"]
        el["shear_warning"] = shear_check["shear_warning"]

        # 5) Birleşim bölgesi kontrolü (kolon ise)
        label = el.get("ifc_name", "")
        story = el.get("ifc_story", "")
        jt_key = (story, label)
        jt_data = joint_map.get(jt_key, {})
        if jt_data:
            jt_check = check_joint(jt_data)
            el["bc_ratio_maj"] = jt_check["bc_ratio_maj"]
            el["bc_ratio_min"] = jt_check["bc_ratio_min"]
            el["bc_status"] = jt_check["bc_status"]
            el["bc_warning"] = jt_check["bc_warning"]
            el["js_ratio_maj"] = jt_check["js_ratio_maj"]
            el["js_ratio_min"] = jt_check["js_ratio_min"]
            el["js_status"] = jt_check["js_status"]
            el["js_warning"] = jt_check["js_warning"]

        # 6) Toplam uyarı sayısı
        warnings = []
        if rebar_check["rho_warning"]:
            warnings.append(rebar_check["rho_warning"])
        if shear_check["shear_warning"]:
            warnings.append(shear_check["shear_warning"])
        if jt_data:
            if jt_check.get("bc_warning"):
                warnings.append(jt_check["bc_warning"])
            if jt_check.get("js_warning"):
                warnings.append(jt_check["js_warning"])
        el["warnings"] = warnings
        el["warning_count"] = len(warnings)

    return elements
