import pandas as pd
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label, normalize_section


def _find_sheet(xl, keywords):
    for sheet in xl.sheet_names:
        if any(k in sheet for k in keywords):
            return sheet
    return None


def _read_sheet(file_bytes, sheet_name, header_markers):
    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name, header=None)
    for i, row in df_raw.iterrows():
        values = [str(v).strip() for v in row.values if pd.notna(v)]
        if all(m in values for m in header_markers):
            df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name, header=i)
            df.columns = df.columns.str.strip()
            df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0].astype(str).str.strip() != "")]
            return df
    return None


def read_connectivity(file_bytes: bytes) -> dict:
    xl = pd.ExcelFile(BytesIO(file_bytes))

    # Point Bays — koordinatlar
    point_sheet = _find_sheet(xl, ["Point Bays", "Point Bay"])
    points = {}
    if point_sheet:
        df = _read_sheet(file_bytes, point_sheet, ["Label", "X", "Y"])
        if df is not None:
            for _, row in df.iterrows():
                label = str(row.get("Label", "") or "").strip()
                try:
                    x = float(row.get("X") or 0)
                    y = float(row.get("Y") or 0)
                    dz = float(row.get("DZBelow") or 0)
                    points[label] = {"x": x, "y": y, "dz": dz}
                except (ValueError, TypeError):
                    pass

    # Beam Bays
    beam_sheet = _find_sheet(xl, ["Beam Bays", "Beam Bay"])
    beams = {}
    if beam_sheet:
        df = _read_sheet(file_bytes, beam_sheet, ["Label", "PointBayI", "PointBayJ"])
        if df is not None:
            for _, row in df.iterrows():
                label = str(row.get("Label", "") or "").strip()
                pi = str(row.get("PointBayI", "") or "").strip()
                pj = str(row.get("PointBayJ", "") or "").strip()
                if label:
                    beams[label] = {"pi": pi, "pj": pj}

    # Column Bays
    col_sheet = _find_sheet(xl, ["Column Bays", "Column Bay"])
    columns = {}
    if col_sheet:
        df = _read_sheet(file_bytes, col_sheet, ["Label", "PointBayI", "PointBayJ"])
        if df is not None:
            for _, row in df.iterrows():
                label = str(row.get("Label", "") or "").strip()
                pi = str(row.get("PointBayI", "") or "").strip()
                if label:
                    columns[label] = {"pi": pi}

    return {
        "points": points,
        "beams": beams,
        "columns": columns,
    }