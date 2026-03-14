"""
Frame Section Property okuyucu.

ETABS Excel çıktısındaki 'Frame Prop - Summary' tablosundan
her kesitin gerçek boyutlarını (depth x width) hesaplar.

Kullanım:
    section_map = read_sections(file_bytes)
    # section_map = {"Column400x300": {"depth": 0.4, "width": 0.3}, ...}
    # Normalize edilmiş anahtarlar da eklenir: "COLUMN400X300" → aynı değer
"""

import math
import pandas as pd
from io import BytesIO

SQRT12 = math.sqrt(12)


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


def _normalize_key(name):
    """Kesit adını normalize et — boşluk sil, büyük harf yap."""
    return name.strip().upper().replace(" ", "")


def read_sections(file_bytes: bytes) -> dict:
    """
    Excel'deki 'Frame Prop - Summary' tablosundan kesit boyutlarını okur.

    Returns:
        dict: {section_name: {"depth": float_m, "width": float_m}}
        Hem orijinal ad hem normalize edilmiş ad ile erişilebilir.
        Tablo bulunamazsa boş dict döner.
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _find_sheet(xl, ["Frame Prop", "Frame Section"])
    if not sheet:
        return {}

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Name", "Shape"])
    if hrow is None:
        return {}

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Name"].notna() & (df["Name"].astype(str).str.strip() != "")]

    section_map = {}

    for _, row in df.iterrows():
        name = str(row.get("Name", "")).strip()
        if not name:
            continue

        r33 = _safe_float(row.get("R33"))  # mm
        r22 = _safe_float(row.get("R22"))  # mm

        if r33 > 0 and r22 > 0:
            depth = r33 * SQRT12 / 1000  # mm → m
            width = r22 * SQRT12 / 1000  # mm → m
        else:
            area = _safe_float(row.get("Area"))  # cm²
            i33 = _safe_float(row.get("I33"))    # cm⁴

            if area > 0 and i33 > 0:
                depth = math.sqrt(12 * i33 / area) / 100
                width = (area / (depth * 100)) / 100
            else:
                depth = 0.3
                width = 0.3

        depth = max(depth, 0.05)
        width = max(width, 0.05)

        val = {"depth": round(depth, 4), "width": round(width, 4)}

        # Orijinal ad ile kaydet
        section_map[name] = val

        # Normalize edilmiş ad ile de kaydet (eşleşme garantisi)
        norm = _normalize_key(name)
        if norm != name:
            section_map[norm] = val

    return section_map


def _safe_float(val):
    try:
        if val is None or str(val).strip() in ("", "nan"):
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0