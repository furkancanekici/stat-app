from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.core.excel_reader import read_excel
from app.core.connectivity_reader import read_connectivity
from app.core.element_matcher import match_elements
from app.core.rule_engine import apply_rules
from app.core.ifc_writer import write_enriched_ifc

router = APIRouter()

@router.post("/enrich")
async def enrich_model(
    excel_file: UploadFile = File(...),
):
    excel_bytes = await excel_file.read()

    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {missing_cols}")

    connectivity = read_connectivity(excel_bytes)

    # IFC elemanlarını connectivity'den oluştur
    ifc_elements = _build_ifc_elements_from_connectivity(connectivity, excel_rows)

    matched = match_elements(ifc_elements, excel_rows)
    enriched = apply_rules(matched)

    ifc_bytes = write_enriched_ifc(enriched, connectivity)

    return Response(
        content=ifc_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=enriched.ifc"},
    )

@router.post("/summary")
async def get_summary(
    excel_file: UploadFile = File(...),
):
    excel_bytes = await excel_file.read()

    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {missing_cols}")

    connectivity = read_connectivity(excel_bytes)
    ifc_elements = _build_ifc_elements_from_connectivity(connectivity, excel_rows)

    matched = match_elements(ifc_elements, excel_rows)
    enriched = apply_rules(matched)

    # Özet istatistikler
    from collections import defaultdict
    status_counts = defaultdict(int)
    by_story_map = defaultdict(lambda: defaultdict(int))
    unmatched = []

    for el in enriched:
        status = el.get("status", "UNMATCHED")
        story = el.get("ifc_story", "")
        status_counts[status] += 1
        by_story_map[story]["total"] += 1
        if status == "FAIL":
            by_story_map[story]["fail"] += 1
        elif status == "WARNING":
            by_story_map[story]["warning"] += 1
        if status == "UNMATCHED":
            unmatched.append(el.get("ifc_name", ""))

    by_story = [
        {
            "story": story,
            "total": counts["total"],
            "fail": counts.get("fail", 0),
            "warning": counts.get("warning", 0),
        }
        for story, counts in sorted(by_story_map.items())
    ]

    return {
        "total": len(enriched),
        "status_counts": dict(status_counts),
        "by_story": by_story,
        "unmatched_elements": unmatched,
        "elements": enriched,
    }


def _build_ifc_elements_from_connectivity(connectivity: dict, excel_rows: list[dict] = None) -> list[dict]:
    from app.utils.normalize import normalize_label
    import uuid

    points = connectivity.get("points", {})
    beams = connectivity.get("beams", {})
    columns = connectivity.get("columns", {})

    # Story elevasyonları — Story1=0, Story2=3, Story3=6 vb.
    story_elevs = {}
    if excel_rows:
        stories = sorted(set(r.get("excel_story", "") for r in excel_rows if r.get("excel_story")))
        for i, s in enumerate(stories):
            story_elevs[s] = i * 3.0

    elements = []

    # Excel'deki her Story+Label kombinasyonu için eleman oluştur
    if excel_rows:
        seen = set()
        for row in excel_rows:
            label = row.get("excel_label", "")
            story = row.get("excel_story", "")
            key = (story, label)
            if key in seen or not label or not story:
                continue
            seen.add(key)

            elev = story_elevs.get(story, 0.0)

            x, y = 0.0, 0.0
            pi, pj = "", ""

            # Eleman tipini ismindeki harfe göre değil, Excel'deki tabloda nerede olduğuna göre belirle
            if label in beams:
                el_type = "IfcBeam"
                pi = beams[label].get("pi", "")
                pj = beams[label].get("pj", "")
                if pi in points and pj in points:
                    x = (points[pi]["x"] + points[pj]["x"]) / 2
                    y = (points[pi]["y"] + points[pj]["y"]) / 2
            elif label in columns:
                el_type = "IfcColumn"
                pi = columns[label].get("pi", "")
                if pi in points:
                    x = points[pi]["x"]
                    y = points[pi]["y"]
            else:
                el_type = "IfcColumn" # Varsayılan durum

            el_dict = {
                "ifc_global_id": str(uuid.uuid4()).replace("-", "")[:22],
                "ifc_name": label,
                "ifc_tag": normalize_label(label),
                "ifc_type": el_type,
                "ifc_story": story,
                "x": x,
                "y": y,
                "z": elev,
            }
            if el_type == "IfcBeam" and pi in points and pj in points:
                el_dict["pi_x"] = points[pi]["x"]
                el_dict["pi_y"] = points[pi]["y"]
                el_dict["pj_x"] = points[pj]["x"]
                el_dict["pj_y"] = points[pj]["y"]
            elements.append(el_dict)

    return elements