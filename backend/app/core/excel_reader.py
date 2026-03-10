import pandas as pd
from io import BytesIO
from app.models.unified_element import UnifiedElementData
from app.utils.normalize import normalize_story, normalize_label, normalize_section


# Zorunlu sütunlar
REQUIRED_COLUMNS = ["ElementLabel", "UnityCheck"]

# Opsiyonel ama beklenen sütunlar
OPTIONAL_COLUMNS = ["Story", "Section", "FailureMode", "Combo"]


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Eksik zorunlu sütunları döner."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return missing


def read_excel(file_bytes: bytes) -> tuple[list[dict], list[str]]:
    """
    Excel dosyasını okur, normalize eder.
    Returns: (rows, missing_columns)
    """
    df = pd.read_excel(BytesIO(file_bytes))

    # Sütun adlarını temizle
    df.columns = df.columns.str.strip()

    missing = validate_columns(df)
    if missing:
        return [], missing

    rows = []
    for _, row in df.iterrows():
        label = normalize_label(str(row.get("ElementLabel", "") or ""))
        if not label:
            continue

        unity_check = None
        try:
            uc = row.get("UnityCheck")
            if uc is not None and str(uc).strip() != "":
                unity_check = float(uc)
        except (ValueError, TypeError):
            pass

        rows.append({
            "excel_label":      label,
            "excel_story":      normalize_story(str(row.get("Story", "") or "")),
            "excel_section":    normalize_section(str(row.get("Section", "") or "")),
            "unity_check":      unity_check,
            "failure_mode":     str(row.get("FailureMode", "") or ""),
            "governing_combo":  str(row.get("Combo", "") or ""),
        })

    return rows, []