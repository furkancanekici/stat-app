from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.excel_reader import read_excel
from app.core.connectivity_reader import read_connectivity

router = APIRouter()

@router.post("/validate")
async def validate_files(
    excel_file: UploadFile = File(...),
):
    excel_bytes = await excel_file.read()

    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {missing_cols}")

    connectivity = read_connectivity(excel_bytes)
    points = connectivity.get("points", {})
    beams = connectivity.get("beams", {})
    columns = connectivity.get("columns", {})

    return {
        "excel_rows": len(excel_rows),
        "points": len(points),
        "beams": len(beams),
        "columns": len(columns),
        "version": "Excel-only",
    }