"""
Birleşim bölgesi (Joint) okuyucu.

ETABS Excel çıktısındaki 'Conc Jt Sum' tablosundan
BCRatio (beam-column capacity ratio) ve JSRatio (joint shear ratio) okur.
"""

import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label


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


def _safe_float(val):
    try:
        if val is None or str(val).strip() in ("", "nan"):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def read_joints(file_bytes: bytes) -> dict:
    """
    Excel'deki 'Conc Jt Sum' tablosundan birleşim bölgesi verilerini okur.

    Returns:
        dict: {(story, label): {bc_maj_ratio, bc_min_ratio, js_maj_ratio, js_min_ratio}}
        Tablo bulunamazsa boş dict döner.
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _find_sheet(xl, ["Conc Jt Sum", "Concrete Joint"])
    if not sheet:
        return {}

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Story", "Label", "Status"])
    if hrow is None:
        return {}

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Story"].notna() & (df["Story"].astype(str).str.strip() != "")]

    joint_map = {}

    for _, row in df.iterrows():
        story = normalize_story(str(row.get("Story", "") or ""))
        label = normalize_label(str(row.get("Label", "") or ""))
        if not story or not label:
            continue

        key = (story, label)
        joint_map[key] = {
            "bc_maj_ratio": _safe_float(row.get("BCMajRatio")),
            "bc_min_ratio": _safe_float(row.get("BCMinRatio")),
            "js_maj_ratio": _safe_float(row.get("JSMajRatio")),
            "js_min_ratio": _safe_float(row.get("JSMinRatio")),
        }

    return joint_map
