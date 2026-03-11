import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label, normalize_section

REQUIRED_COLUMNS_STEEL = ["Story", "Label", "PMM Ratio"]
REQUIRED_COLUMNS_CONC  = ["Story", "Label", "Status"]


def _find_header_row(df_raw, markers):
    for i, row in df_raw.iterrows():
        values = [str(v).strip() for v in row.values if pd.notna(v)]
        if all(m in values for m in markers):
            return i
    return None


def _read_steel(file_bytes: bytes) -> list[dict]:
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


def _read_concrete(file_bytes: bytes) -> list[dict]:
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = next((s for s in xl.sheet_names if "Conc Col" in s or "Concrete" in s), None)
    if not sheet:
        return []

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Label", "Status"])
    if hrow is None:
        return []

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]

    # Her kolon için sadece ilk station satırını al
    df = df.drop_duplicates(subset=["Story", "Label"], keep="first")

    rows = []
    for _, row in df.iterrows():
        label = normalize_label(str(row.get("Label", "") or ""))
        if not label:
            continue

        # Beton kolonlar için As/AsMin oranını unity check olarak kullan
        unity_check = None
        try:
            as_val  = float(row.get("As") or 0)
            as_min  = float(row.get("AsMin") or 0)
            if as_min > 0:
                unity_check = round(as_val / as_min, 3)
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


def read_excel(file_bytes: bytes) -> tuple[list[dict], list[str]]:
    steel_rows = _read_steel(file_bytes)
    conc_rows  = _read_concrete(file_bytes)
    all_rows   = steel_rows + conc_rows

    if not all_rows:
        return [], ["Story", "Label", "PMM Ratio"]

    return all_rows, []