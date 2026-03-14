from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.core.excel_reader import read_excel
from app.core.connectivity_reader import read_connectivity
from app.core.section_reader import read_sections
from app.core.element_matcher import match_elements
from app.core.rule_engine import apply_rules
from app.core.ifc_writer import write_enriched_ifc

router = APIRouter()

_B64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"

def _ifc_guid():
    import uuid as _uuid
    u = _uuid.uuid4().int
    chars = []
    for _ in range(22):
        chars.append(_B64[u % 64])
        u //= 64
    return "".join(chars)


@router.post("/enrich")
async def enrich_model(excel_file: UploadFile = File(...)):
    excel_bytes = await excel_file.read()
    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {missing_cols}")

    connectivity = read_connectivity(excel_bytes)
    section_map = read_sections(excel_bytes)
    ifc_elements = _build_ifc_elements_from_connectivity(connectivity, excel_rows, section_map)
    matched = match_elements(ifc_elements, excel_rows)
    enriched = apply_rules(matched)
    ifc_bytes = write_enriched_ifc(enriched, connectivity, section_map)

    return Response(
        content=ifc_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=enriched.ifc"},
    )


@router.post("/summary")
async def get_summary(excel_file: UploadFile = File(...)):
    excel_bytes = await excel_file.read()
    excel_rows, missing_cols = read_excel(excel_bytes)
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {missing_cols}")

    connectivity = read_connectivity(excel_bytes)
    section_map = read_sections(excel_bytes)
    print(f"[DEBUG] section_map keys: {len(section_map)}, first 3: {list(section_map.keys())[:3]}")
    ifc_elements = _build_ifc_elements_from_connectivity(connectivity, excel_rows, section_map)
    matched = match_elements(ifc_elements, excel_rows)
    enriched = apply_rules(matched)

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
        {"story": story, "total": counts["total"],
         "fail": counts.get("fail", 0), "warning": counts.get("warning", 0)}
        for story, counts in sorted(by_story_map.items())
    ]

    # DEBUG — ilk elemanın tüm key'lerini ve section_map boyutunu response'a ekle
    debug_info = {
        "section_map_size": len(section_map),
        "section_map_keys_sample": list(section_map.keys())[:5],
        "first_element_keys": list(enriched[0].keys()) if enriched else [],
        "first_element_sec": {
            "sec_depth": enriched[0].get("sec_depth") if enriched else None,
            "sec_width": enriched[0].get("sec_width") if enriched else None,
            "excel_section": enriched[0].get("excel_section") if enriched else None,
        }
    }

    return {
        "total": len(enriched),
        "status_counts": dict(status_counts),
        "by_story": by_story,
        "unmatched_elements": unmatched,
        "elements": enriched,
        "debug": debug_info,
    }


def _build_ifc_elements_from_connectivity(connectivity, excel_rows=None, section_map=None):
    from app.utils.normalize import normalize_label

    points = connectivity.get("points", {})
    beams = connectivity.get("beams", {})
    columns = connectivity.get("columns", {})
    if section_map is None:
        section_map = {}

    story_elevs = {}
    if excel_rows:
        stories = sorted(set(r.get("excel_story", "") for r in excel_rows if r.get("excel_story")))
        for i, s in enumerate(stories):
            story_elevs[s] = i * 3.0

    elements = []
    if not excel_rows:
        return elements

    seen = set()
    for row in excel_rows:
        label = row.get("excel_label", "")
        story = row.get("excel_story", "")
        key = (story, label)
        if key in seen or not label or not story:
            continue
        seen.add(key)

        elev = story_elevs.get(story, 0.0)
        el_type = "IfcBeam" if label.startswith("B") else "IfcColumn"

        x, y = 0.0, 0.0
        pi, pj = "", ""
        if el_type == "IfcBeam" and label in beams:
            pi = beams[label].get("pi", "")
            pj = beams[label].get("pj", "")
            if pi in points and pj in points:
                x = (points[pi]["x"] + points[pj]["x"]) / 2
                y = (points[pi]["y"] + points[pj]["y"]) / 2
        elif el_type == "IfcColumn" and label in columns:
            pi = columns[label].get("pi", "")
            if pi in points:
                x = points[pi]["x"]
                y = points[pi]["y"]

        # Kesit boyutları — section_map'ten al
        section_name = row.get("excel_section", "")
        sec_info = section_map.get(section_name, {})
        sec_depth = sec_info.get("depth", 0.3)
        sec_width = sec_info.get("width", 0.3)

        el_dict = {
            "ifc_global_id": _ifc_guid(),
            "ifc_name": label,
            "ifc_tag": normalize_label(label),
            "ifc_type": el_type,
            "ifc_story": story,
            "x": x, "y": y, "z": elev,
            "sec_depth": sec_depth,
            "sec_width": sec_width,
            "excel_section": section_name,
        }
        if el_type == "IfcBeam" and pi in points and pj in points:
            el_dict["pi_x"] = points[pi]["x"]
            el_dict["pi_y"] = points[pi]["y"]
            el_dict["pj_x"] = points[pj]["x"]
            el_dict["pj_y"] = points[pj]["y"]
        elements.append(el_dict)

    return elements