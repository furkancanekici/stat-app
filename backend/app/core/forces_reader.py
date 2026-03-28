"""
Eleman kuvvetleri okuyucu.

Element Forces - Beams/Columns tablosundan
her eleman için maksimum kesme kuvvetini (Vd) çıkarır.
"""

import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label


def _find_sheet(xl, keywords):
    for sheet in xl.sheet_names:
        if all(k.lower() in sheet.lower() for k in keywords):
            return sheet
    return None


def _find_header_row(df_raw, markers):
    for i, row in df_raw.iterrows():
        values = [str(v).strip() for v in row.values if pd.notna(v)]
        if all(m in values for m in markers):
            return i
    return None


def read_element_forces(file_bytes: bytes) -> dict:
    """
    Element Forces tablosundan her eleman için max kesme kuvvetini okur.

    Returns:
        dict: {(story, label): {"v_max": float_kN, "p_max": float_kN, "m_max": float_kN}}
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    forces_map = {}

    # Kolonlar
    col_sheet = _find_sheet(xl, ["Element Forces", "Columns"])
    if col_sheet:
        _read_forces_sheet(file_bytes, col_sheet, "Column", forces_map)

    # Kirişler
    beam_sheet = _find_sheet(xl, ["Element Forces", "Beams"])
    if beam_sheet:
        _read_forces_sheet(file_bytes, beam_sheet, "Beam", forces_map)

    return forces_map


def _read_forces_sheet(file_bytes, sheet, label_col, forces_map):
    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", label_col, "V2"])
    if hrow is None:
        # Alternatif marker dene
        hrow = _find_header_row(df_raw, ["Story", "Output Case", "V2"])
    if hrow is None:
        return

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]

    # Sayısal dönüşüm
    for col in ["V2", "V3", "P", "M2", "M3"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # V2 ve V3'ten max kesme
    if "V3" in df.columns:
        df["_Vmax"] = df[["V2", "V3"]].abs().max(axis=1)
    else:
        df["_Vmax"] = df["V2"].abs()

    df["_Pmax"] = df["P"].abs() if "P" in df.columns else 0
    df["_Mmax"] = df[["M2", "M3"]].abs().max(axis=1) if "M3" in df.columns else df["M2"].abs() if "M2" in df.columns else 0

    # Her eleman+kat için max değerler
    for (story, label), group in df.groupby(["Story", label_col]):
        norm_story = normalize_story(str(story))
        norm_label = normalize_label(str(label))
        key = (norm_story, norm_label)

        forces_map[key] = {
            "v_max": round(float(group["_Vmax"].max()), 2),
            "p_max": round(float(group["_Pmax"].max()), 2),
            "m_max": round(float(group["_Mmax"].max()), 2),
        }
