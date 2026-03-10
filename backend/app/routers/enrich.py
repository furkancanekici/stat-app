from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.core.ifc_reader import read_ifc
from app.core.excel_reader import read_excel
from app.core.element_matcher import match_elements
from app.core.ifc_enricher import enrich_ifc
from app.models.unified_element import Status

router = APIRouter()


@router.post("/enrich")
async def enrich(
    ifc_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
):
    """
    IFC + Excel alır, enriched IFC döner.
    """
    if not ifc_file.filename.endswith(".ifc"):
        raise HTTPException(400, "Geçersiz dosya: .ifc uzantısı gerekli")
    if not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Geçersiz dosya: .xlsx veya .xls uzantısı gerekli")

    ifc_bytes = await ifc_file.read()
    excel_bytes = await excel_file.read()

    # Oku
    try:
        ifc_elements, ifc_version = read_ifc(ifc_bytes)
    except Exception as e:
        raise HTTPException(400, f"IFC okunamadı: {str(e)}")

    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(400, f"Eksik sütunlar: {missing_cols}")

    # Eşleştir
    matched_elements = match_elements(ifc_elements, excel_rows)

    # Zenginleştir
    try:
        enriched_bytes = enrich_ifc(ifc_bytes, matched_elements)
    except Exception as e:
        raise HTTPException(500, f"IFC zenginleştirme hatası: {str(e)}")

    filename = ifc_file.filename.replace(".ifc", "_enriched.ifc")

    return Response(
        content=enriched_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/summary")
async def summary(
    ifc_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
):
    """
    Enrichment sonrası özet istatistikler.
    """
    ifc_bytes = await ifc_file.read()
    excel_bytes = await excel_file.read()

    ifc_elements, _ = read_ifc(ifc_bytes)
    excel_rows, missing_cols = read_excel(excel_bytes)

    if missing_cols:
        raise HTTPException(400, f"Eksik sütunlar: {missing_cols}")

    matched_elements = match_elements(ifc_elements, excel_rows)

    # Durum sayıları
    status_counts = {}
    for el in matched_elements:
        key = el.status.value if el.status else "UNMATCHED"
        status_counts[key] = status_counts.get(key, 0) + 1

    # Kat bazlı dağılım
    story_map = {}
    for el in matched_elements:
        story = el.ifc_story or "Bilinmiyor"
        if story not in story_map:
            story_map[story] = {"story": story, "total": 0, "fail": 0, "warning": 0}
        story_map[story]["total"] += 1
        if el.status == Status.FAIL:
            story_map[story]["fail"] += 1
        if el.status == Status.WARNING:
            story_map[story]["warning"] += 1

    # Eşleşmeyen elemanlar
    unmatched = [
        el.ifc_global_id
        for el in matched_elements
        if el.status == Status.UNMATCHED
    ]

    return {
        "total":             len(matched_elements),
        "status_counts":     status_counts,
        "by_story":          list(story_map.values()),
        "unmatched_elements": unmatched,
    }