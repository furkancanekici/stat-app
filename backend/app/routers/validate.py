from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.ifc_reader import read_ifc
from app.core.excel_reader import read_excel
from app.core.element_matcher import match_elements, get_low_confidence

router = APIRouter()


@router.post("/validate")
async def validate_files(
    ifc_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
):
    """
    IFC + Excel dosyalarını okur, validasyon yapar.
    Enrichment başlamaz, sadece ön kontrol.
    """
    # Dosya uzantısı kontrolü
    if not ifc_file.filename.endswith(".ifc"):
        raise HTTPException(400, "Geçersiz dosya: .ifc uzantısı gerekli")
    if not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Geçersiz dosya: .xlsx veya .xls uzantısı gerekli")

    ifc_bytes = await ifc_file.read()
    excel_bytes = await excel_file.read()

    # IFC oku
    try:
        ifc_elements, ifc_version = read_ifc(ifc_bytes)
    except Exception as e:
        raise HTTPException(400, f"IFC okunamadı: {str(e)}")

    # Excel oku
    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(400, f"Eksik sütunlar: {missing_cols}")

    return {
        "ifc_elements": len(ifc_elements),
        "excel_rows":   len(excel_rows),
        "ifc_version":  ifc_version,
        "missing_cols": missing_cols,
    }


@router.post("/match-preview")
async def match_preview(
    ifc_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
):
    """
    Eşleştirme önizlemesi — kullanıcı onaylamadan enrich başlamaz.
    """
    ifc_bytes = await ifc_file.read()
    excel_bytes = await excel_file.read()

    ifc_elements, _ = read_ifc(ifc_bytes)
    excel_rows, missing_cols = read_excel(excel_bytes)

    if missing_cols:
        raise HTTPException(400, f"Eksik sütunlar: {missing_cols}")

    matched_elements = match_elements(ifc_elements, excel_rows)

    from app.models.unified_element import Status
    matched = sum(1 for el in matched_elements if el.status != Status.UNMATCHED)
    unmatched = sum(1 for el in matched_elements if el.status == Status.UNMATCHED)
    low_confidence = get_low_confidence(matched_elements)

    return {
        "matched":        matched,
        "unmatched":      unmatched,
        "low_confidence": low_confidence,
        "total":          len(matched_elements),
    }