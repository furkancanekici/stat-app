import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label, normalize_section


def _find_header_row(df_raw, markers):
    for i, row in df_raw.iterrows():
        values = [str(v).strip() for v in row.values if pd.notna(v)]
        if all(m in values for m in markers):
            return i
    return None


def _safe_float(val):
    try:
        if val is None or str(val).strip() in ("", "nan"):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def _read_steel(file_bytes: bytes) -> list[dict]:
    """Çelik kiriş/kolon: Stl Frm Sum - AISC 360-16"""
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = next((s for s in xl.sheet_names if "Stl Frm Sum" in s or "Steel Frame" in s), None)
    if not sheet:
        return []

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Label", "PMM Ratio"])
    if hrow is None:
        return []

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]

    rows = []
    for _, row in df.iterrows():
        label = normalize_label(str(row.get("Label", "") or ""))
        if not label:
            continue

        unity_check = _safe_float(row.get("PMM Ratio"))
        v_ratio = _safe_float(row.get("V Major Ratio"))

        failure_mode = ""
        if v_ratio is not None and unity_check is not None:
            failure_mode = "Shear" if v_ratio > unity_check else "Moment"

        status_raw = str(row.get("Status", "") or "")
        if "Overstressed" in status_raw:
            failure_mode = failure_mode or "Overstressed"

        rows.append({
            "excel_label":     label,
            "excel_story":     normalize_story(str(row.get("Story", "") or "")),
            "excel_section":   normalize_section(str(row.get("Design Section", "") or "")),
            "unity_check":     unity_check,
            "failure_mode":    failure_mode,
            "governing_combo": str(row.get("PMM Combo", "") or ""),
            # Çelik profillerde donatı yok
            "as_total":        None,
            "as_min":          None,
            "as_top":          None,
            "as_bot":          None,
            "v_rebar":         None,
            "rebar_ratio":     None,
        })
    return rows


def _read_concrete_col(file_bytes: bytes) -> list[dict]:
    """Beton kolon: Conc Col Sum - TS 500-2000"""
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = next((s for s in xl.sheet_names if "Conc Col" in s or "Concrete Column" in s), None)
    if not sheet:
        return []

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Label", "Status"])
    if hrow is None:
        return []

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["Story", "Label"], keep="first")

    rows = []
    for _, row in df.iterrows():
        label = normalize_label(str(row.get("Label", "") or ""))
        if not label:
            continue

        as_val = _safe_float(row.get("As"))
        as_min = _safe_float(row.get("AsMin"))
        v_maj = _safe_float(row.get("VMajRebar"))
        v_min = _safe_float(row.get("VMinRebar"))

        # UC = AsMin / As → küçükse yeterli
        unity_check = None
        if as_val and as_val > 0:
            unity_check = round((as_min or 0) / as_val, 3)

        # Donatı oranı (yaklaşık) — As / AsMin
        rebar_ratio = None
        if as_min and as_min > 0 and as_val:
            rebar_ratio = round(as_val / as_min, 2)

        status_raw = str(row.get("Status", "") or "")
        failure_mode = "Overstressed" if "Overstressed" in status_raw else "PMM"

        rows.append({
            "excel_label":     label,
            "excel_story":     normalize_story(str(row.get("Story", "") or "")),
            "excel_section":   normalize_section(str(row.get("DesignSect", "") or "")),
            "unity_check":     unity_check,
            "failure_mode":    failure_mode,
            "governing_combo": str(row.get("PMMCombo", "") or ""),
            "as_total":        as_val,
            "as_min":          as_min,
            "as_top":          None,
            "as_bot":          None,
            "v_rebar":         max(v_maj or 0, v_min or 0) if (v_maj or v_min) else None,
            "rebar_ratio":     rebar_ratio,
        })
    return rows


def _read_concrete_beam(file_bytes: bytes) -> list[dict]:
    """Beton kiriş: Conc Bm Sum - TS 500-2000"""
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = next((s for s in xl.sheet_names if "Conc Bm" in s or "Concrete Beam" in s), None)
    if not sheet:
        return []

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Label", "Status"])
    if hrow is None:
        return []

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["Story", "Label"], keep="first")

    rows = []
    for _, row in df.iterrows():
        label = normalize_label(str(row.get("Label", "") or ""))
        if not label:
            continue

        as_top = _safe_float(row.get("AsTop"))
        as_min_top = _safe_float(row.get("AsMinTop"))
        as_bot = _safe_float(row.get("AsBot"))
        as_min_bot = _safe_float(row.get("AsMinBot"))
        v_rebar = _safe_float(row.get("VRebar"))

        # UC = max(AsMin/As) → küçükse yeterli
        unity_check = None
        failure_mode = ""
        ratios = []
        if as_top and as_top > 0:
            ratios.append((as_min_top or 0) / as_top)
        if as_bot and as_bot > 0:
            ratios.append((as_min_bot or 0) / as_bot)
        if ratios:
            unity_check = round(max(ratios), 3)
            failure_mode = "Moment"

        if v_rebar and v_rebar > 0 and unity_check is not None and unity_check >= 1.0:
            failure_mode = "Shear"

        # Donatı oranı — toplam As / toplam AsMin
        total_as = (as_top or 0) + (as_bot or 0)
        total_as_min = (as_min_top or 0) + (as_min_bot or 0)
        rebar_ratio = None
        if total_as_min > 0:
            rebar_ratio = round(total_as / total_as_min, 2)

        status_raw = str(row.get("Status", "") or "")
        if "Overstressed" in status_raw:
            failure_mode = failure_mode or "Overstressed"

        combo = str(row.get("AsTopCombo", "") or "")

        rows.append({
            "excel_label":     label,
            "excel_story":     normalize_story(str(row.get("Story", "") or "")),
            "excel_section":   normalize_section(str(row.get("DesignSect", "") or "")),
            "unity_check":     unity_check,
            "failure_mode":    failure_mode,
            "governing_combo": combo,
            "as_total":        total_as if total_as > 0 else None,
            "as_min":          total_as_min if total_as_min > 0 else None,
            "as_top":          as_top,
            "as_bot":          as_bot,
            "v_rebar":         v_rebar,
            "rebar_ratio":     rebar_ratio,
        })
    return rows


def read_excel(file_bytes: bytes) -> tuple[list[dict], list[str]]:
    steel_rows = _read_steel(file_bytes)
    conc_col_rows = _read_concrete_col(file_bytes)
    conc_beam_rows = _read_concrete_beam(file_bytes)
    all_rows = steel_rows + conc_col_rows + conc_beam_rows

    if not all_rows:
        return [], ["Desteklenen tablo bulunamadı (Steel Frame, Conc Col, veya Conc Beam)"]

    return all_rows, []
