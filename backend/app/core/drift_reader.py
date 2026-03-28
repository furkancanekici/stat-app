"""
Kat ötelemesi ve burulma düzensizliği okuyucu.

Story Drifts → δi/hi (göreli kat ötelemesi)
Diaphragm Max Over Avg Drifts → ηbi (burulma düzensizliği oranı)
"""

import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story


def _find_sheet(xl, keywords):
    for sheet in xl.sheet_names:
        if any(k.lower() in sheet.lower() for k in keywords):
            return sheet
    return None


def _find_header_row(df_raw, markers):
    for i, row in df_raw.iterrows():
        values = [str(v).strip() for v in row.values if pd.notna(v)]
        if all(m in values for m in markers):
            return i
    return None


def read_story_drifts(file_bytes: bytes) -> dict:
    """
    Story Drifts tablosundan her kat için maksimum öteleme okur.

    Returns:
        dict: {story: {"max_drift": float, "direction": str, "output_case": str, "drift_label": str}}
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _find_sheet(xl, ["Story Drifts"])
    if not sheet:
        return {}

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Direction", "Drift"])
    if hrow is None:
        return {}

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]

    # Sadece deprem yük durumlarını al (EQX, EQY veya Seismic içeren)
    eq_mask = df["Output Case"].astype(str).str.contains("EQ|Seismic|deprem", case=False, na=False)
    if eq_mask.sum() == 0:
        # Deprem yükü yoksa tüm kombinasyonları al
        eq_df = df
    else:
        eq_df = df[eq_mask]

    # Drift'i sayısal yap
    eq_df = eq_df.copy()
    eq_df["Drift"] = pd.to_numeric(eq_df["Drift"], errors="coerce")

    # Her kat için maksimum drift
    drift_map = {}
    for story in eq_df["Story"].unique():
        story_data = eq_df[eq_df["Story"] == story]
        if story_data.empty:
            continue
        max_row = story_data.loc[story_data["Drift"].idxmax()]
        norm_story = normalize_story(str(story))
        drift_map[norm_story] = {
            "max_drift": float(max_row["Drift"]),
            "direction": str(max_row.get("Direction", "")),
            "output_case": str(max_row.get("Output Case", "")),
            "drift_label": str(max_row.get("Drift/", "")),
        }

    return drift_map


def read_torsion_irregularity(file_bytes: bytes) -> dict:
    """
    Diaphragm Max Over Avg Drifts tablosundan burulma düzensizliği okur.

    Returns:
        dict: {story: {"max_ratio": float, "direction": str, "output_case": str}}
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _find_sheet(xl, ["Diaphragm Max Over Avg"])
    if not sheet:
        return {}

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Ratio"])
    if hrow is None:
        return {}

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]

    # Deprem yükleri
    eq_mask = df["Output Case"].astype(str).str.contains("EQ|Seismic", case=False, na=False)
    eq_df = df[eq_mask] if eq_mask.sum() > 0 else df

    eq_df = eq_df.copy()
    eq_df["Ratio"] = pd.to_numeric(eq_df["Ratio"], errors="coerce")

    torsion_map = {}
    for story in eq_df["Story"].unique():
        story_data = eq_df[eq_df["Story"] == story]
        if story_data.empty:
            continue
        max_row = story_data.loc[story_data["Ratio"].idxmax()]
        norm_story = normalize_story(str(story))
        torsion_map[norm_story] = {
            "max_ratio": float(max_row["Ratio"]),
            "direction": str(max_row.get("Output Case", "")),
        }

    return torsion_map
