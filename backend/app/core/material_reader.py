"""
Malzeme ve deprem parametreleri okuyucu.

Mat Prop - General → fck, fyk (beton ve donatı dayanımları)
Auto Seismic - TSC 2018 → R, D, I, SDS, SD1 (deprem parametreleri)
"""

import re
import pandas as pd
from io import BytesIO


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


def _parse_concrete_grade(grade_str):
    """C30/37, C25, C35/45 gibi grade'lerden fck çıkar."""
    if not grade_str:
        return None
    m = re.search(r"[Cc](\d+)", str(grade_str))
    if m:
        return int(m.group(1))  # MPa
    return None


def _parse_rebar_grade(material_name, grade_str):
    """S420, Grade 60 gibi grade'lerden fyk çıkar."""
    name = str(material_name or "").upper()
    grade = str(grade_str or "")

    # S420, S500 gibi
    m = re.search(r"[Ss](\d+)", name)
    if m:
        return int(m.group(1))  # MPa

    # Grade 60 → 420 MPa (ASTM)
    if "60" in grade:
        return 420
    if "40" in grade:
        return 280

    return None


def read_materials(file_bytes: bytes) -> dict:
    """
    Material Property tablosundan fck ve fyk değerlerini okur.

    Returns:
        dict: {
            "concrete": {"name": str, "fck": float_MPa, "grade": str},
            "rebar": {"name": str, "fyk": float_MPa, "grade": str},
            "steel": {"name": str, "fy": float_MPa, "grade": str},
        }
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _find_sheet(xl, ["Mat Prop"])
    if not sheet:
        return {}

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Material", "Type"])
    if hrow is None:
        return {}

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Material"].notna() & (df["Material"].astype(str).str.strip() != "")]

    result = {}

    for _, row in df.iterrows():
        mat_name = str(row.get("Material", "")).strip()
        mat_type = str(row.get("Type", "")).strip().lower()
        grade = str(row.get("Grade", "")).strip()

        if "concrete" in mat_type:
            fck = _parse_concrete_grade(grade)
            result["concrete"] = {
                "name": mat_name,
                "fck": fck or 30,  # varsayılan C30
                "grade": grade,
            }
        elif "rebar" in mat_type:
            fyk = _parse_rebar_grade(mat_name, grade)
            if "rebar" not in result:
                result["rebar"] = {
                    "name": mat_name,
                    "fyk": fyk or 420,  # varsayılan S420
                    "grade": grade,
                }
        elif "steel" in mat_type:
            # S355, S275 gibi
            m = re.search(r"[Ss](\d+)", mat_name)
            fy = int(m.group(1)) if m else 355
            result["steel"] = {
                "name": mat_name,
                "fy": fy,
                "grade": grade,
            }

    return result


def read_seismic_params(file_bytes: bytes) -> dict:
    """
    Auto Seismic tablosundan deprem parametrelerini okur.

    Returns:
        dict: {"R": float, "D": float, "I": float, "SDS": float, "SD1": float,
               "Ss": float, "S1": float, "site_class": str}
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _find_sheet(xl, ["Auto Seismic"])
    if not sheet:
        return {}

    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=None)
    hrow = _find_header_row(df_raw, ["Name", "R"])
    if hrow is None:
        return {}

    df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet, header=hrow)
    df.columns = df.columns.str.strip()
    df = df[df["Name"].notna() & (df["Name"].astype(str).str.strip() != "")]

    if df.empty:
        return {}

    # İlk satırı al (genellikle EQX)
    row = df.iloc[0]

    return {
        "R": _safe_float(row.get("R")),
        "D": _safe_float(row.get("D")),
        "I": _safe_float(row.get("I")),
        "SDS": _safe_float(row.get("SDS")),
        "SD1": _safe_float(row.get("SD1")),
        "Ss": _safe_float(row.get("Ss")),
        "S1": _safe_float(row.get("S1")),
        "site_class": str(row.get("Site Class", "")).strip(),
    }
