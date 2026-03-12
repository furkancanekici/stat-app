import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label, normalize_section


def _find_header_row(df_raw, markers):
    for i, row in df_raw.iterrows():
        values = [str(v).strip() for v in row.values if pd.notna(v)]
        if all(m in values for m in markers):
            return i
    return None


def _read_steel(file_bytes: bytes) -> list[dict]:
    """Çelik kiriş/kolon: Stl Frm Sum - AISC 360-16
    UC = PMM Ratio (direkt). UC ≥ 1.0 → yetersiz.
    """
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

        unity_check = None
        try:
            uc = row.get("PMM Ratio")
            if uc is not None and str(uc).strip() not in ("", "nan"):
                unity_check = float(uc)
        except (ValueError, TypeError):
            pass

        v_ratio = None
        try:
            vr = row.get("V Major Ratio")
            if vr is not None and str(vr).strip() not in ("", "nan"):
                v_ratio = float(vr)
        except (ValueError, TypeError):
            pass

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
        })
    return rows


def _read_concrete_col(file_bytes: bytes) -> list[dict]:
    """Beton kolon: Conc Col Sum - TS 500-2000
    As/AsMin > 1.0 → donatı yeterli (iyi).
    UC olarak AsMin/As kullanılır → UC < 1.0 = yeterli, UC ≥ 1.0 = yetersiz.
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = next((s for s in xl.sheet_names if "Conc Col" in s), None)
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

        # UC = AsMin / As  →  küçükse yeterli, ≥1.0 ise yetersiz
        unity_check = None
        try:
            as_val = float(row.get("As") or 0)
            as_min = float(row.get("AsMin") or 0)
            if as_val > 0:
                unity_check = round(as_min / as_val, 3)
        except (ValueError, TypeError):
            pass

        status_raw = str(row.get("Status", "") or "")
        failure_mode = "Overstressed" if "Overstressed" in status_raw else "PMM"

        rows.append({
            "excel_label":     label,
            "excel_story":     normalize_story(str(row.get("Story", "") or "")),
            "excel_section":   normalize_section(str(row.get("DesignSect", "") or "")),
            "unity_check":     unity_check,
            "failure_mode":    failure_mode,
            "governing_combo": str(row.get("PMMCombo", "") or ""),
        })
    return rows


def _read_concrete_beam(file_bytes: bytes) -> list[dict]:
    """Beton kiriş: Conc Bm Sum - TS 500-2000
    AsTop ≥ AsMinTop → donatı yeterli.
    UC = max(AsMinTop/AsTop, AsMinBot/AsBot) → küçükse yeterli, ≥1.0 ise yetersiz.
    """
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

        unity_check = None
        failure_mode = ""
        try:
            as_top = float(row.get("AsTop") or 0)
            as_min_top = float(row.get("AsMinTop") or 0)
            as_bot = float(row.get("AsBot") or 0)
            as_min_bot = float(row.get("AsMinBot") or 0)

            # UC = AsMin/As → küçükse yeterli, ≥1.0 ise yetersiz
            ratios = []
            if as_top > 0:
                ratios.append(as_min_top / as_top)
            if as_bot > 0:
                ratios.append(as_min_bot / as_bot)

            if ratios:
                unity_check = round(max(ratios), 3)
                failure_mode = "Moment"
        except (ValueError, TypeError):
            pass

        # Kesme kontrolü
        try:
            v_rebar = row.get("VRebar")
            if v_rebar is not None and str(v_rebar).strip() not in ("", "nan"):
                v_val = float(v_rebar)
                if v_val > 0 and unity_check is not None and unity_check >= 1.0:
                    failure_mode = "Shear"
        except (ValueError, TypeError):
            pass

        status_raw = str(row.get("Status", "") or "")
        if "Overstressed" in status_raw:
            failure_mode = failure_mode or "Overstressed"

        combo = ""
        try:
            combo = str(row.get("AsTopCombo", "") or "")
        except Exception:
            pass

        rows.append({
            "excel_label":     label,
            "excel_story":     normalize_story(str(row.get("Story", "") or "")),
            "excel_section":   normalize_section(str(row.get("DesignSect", "") or "")),
            "unity_check":     unity_check,
            "failure_mode":    failure_mode,
            "governing_combo": combo,
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
