from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.core.excel_reader import read_excel
from app.core.connectivity_reader import read_connectivity
from app.core.section_reader import read_sections
from app.core.joint_reader import read_joints
from app.core.drift_reader import read_story_drifts, read_torsion_irregularity
from app.core.material_reader import read_materials, read_seismic_params
from app.core.forces_reader import read_element_forces
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


def _read_all(excel_bytes):
    """Tüm tabloları oku, ortak fonksiyon."""
    excel_rows, missing = read_excel(excel_bytes)
    connectivity = read_connectivity(excel_bytes)
    section_map = read_sections(excel_bytes)
    joint_map = read_joints(excel_bytes)
    drift_map = read_story_drifts(excel_bytes)
    torsion_map = read_torsion_irregularity(excel_bytes)
    materials = read_materials(excel_bytes)
    seismic_params = read_seismic_params(excel_bytes)
    forces_map = read_element_forces(excel_bytes)
    return {
        "excel_rows": excel_rows, "missing": missing,
        "connectivity": connectivity, "section_map": section_map,
        "joint_map": joint_map, "drift_map": drift_map,
        "torsion_map": torsion_map, "materials": materials,
        "seismic_params": seismic_params, "forces_map": forces_map,
    }


@router.post("/enrich")
async def enrich_model(excel_file: UploadFile = File(...)):
    excel_bytes = await excel_file.read()
    data = _read_all(excel_bytes)

    if data["missing"]:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {data['missing']}")

    ifc_elements = _build_ifc_elements_from_connectivity(
        data["connectivity"], data["excel_rows"], data["section_map"]
    )
    matched = match_elements(ifc_elements, data["excel_rows"])
    enriched = apply_rules(
        matched,
        joint_map=data["joint_map"],
        drift_map=data["drift_map"],
        torsion_map=data["torsion_map"],
        forces_map=data["forces_map"],
        materials=data["materials"],
        seismic_params=data["seismic_params"],
    )
    ifc_bytes = write_enriched_ifc(enriched, data["connectivity"], data["section_map"])

    return Response(
        content=ifc_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=enriched.ifc"},
    )


@router.post("/summary")
async def get_summary(excel_file: UploadFile = File(...)):
    excel_bytes = await excel_file.read()
    data = _read_all(excel_bytes)

    if data["missing"]:
        raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {data['missing']}")

    ifc_elements = _build_ifc_elements_from_connectivity(
        data["connectivity"], data["excel_rows"], data["section_map"]
    )
    matched = match_elements(ifc_elements, data["excel_rows"])
    enriched = apply_rules(
        matched,
        joint_map=data["joint_map"],
        drift_map=data["drift_map"],
        torsion_map=data["torsion_map"],
        forces_map=data["forces_map"],
        materials=data["materials"],
        seismic_params=data["seismic_params"],
    )

    from collections import defaultdict
    status_counts = defaultdict(int)
    by_story_map = defaultdict(lambda: defaultdict(int))
    unmatched = []
    total_warnings = 0

    for el in enriched:
        status = el.get("status", "UNMATCHED")
        story = el.get("ifc_story", "")
        status_counts[status] += 1
        by_story_map[story]["total"] += 1
        if status == "FAIL": by_story_map[story]["fail"] += 1
        elif status == "WARNING": by_story_map[story]["warning"] += 1
        if status == "UNMATCHED": unmatched.append(el.get("ifc_name", ""))
        total_warnings += el.get("warning_count", 0)

    by_story = [
        {"story": s, "total": c["total"], "fail": c.get("fail", 0), "warning": c.get("warning", 0)}
        for s, c in sorted(by_story_map.items())
    ]

    return {
        "total": len(enriched),
        "status_counts": dict(status_counts),
        "by_story": by_story,
        "unmatched_elements": unmatched,
        "total_warnings": total_warnings,
        "materials": data["materials"],
        "seismic_params": data["seismic_params"],
        "drift_summary": data["drift_map"],
        "torsion_summary": data["torsion_map"],
        "elements": enriched,
    }


def _build_ifc_elements_from_connectivity(connectivity, excel_rows=None, section_map=None):
    from app.utils.normalize import normalize_label

    points = connectivity.get("points", {})
    beams = connectivity.get("beams", {})
    columns = connectivity.get("columns", {})
    if section_map is None: section_map = {}

    story_elevs = {}
    if excel_rows:
        stories = sorted(set(r.get("excel_story", "") for r in excel_rows if r.get("excel_story")))
        for i, s in enumerate(stories):
            story_elevs[s] = i * 3.0

    elements = []
    if not excel_rows: return elements

    seen = set()
    for row in excel_rows:
        label = row.get("excel_label", "")
        story = row.get("excel_story", "")
        key = (story, label)
        if key in seen or not label or not story: continue
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

        section_name = row.get("excel_section", "")
        sec_info = section_map.get(section_name, {})

        el_dict = {
            "ifc_global_id": _ifc_guid(),
            "ifc_name": label,
            "ifc_tag": normalize_label(label),
            "ifc_type": el_type,
            "ifc_story": story,
            "x": x, "y": y, "z": elev,
            "sec_depth": sec_info.get("depth", 0.3),
            "sec_width": sec_info.get("width", 0.3),
            "excel_section": section_name,
        }
        if el_type == "IfcBeam" and pi in points and pj in points:
            el_dict["pi_x"] = points[pi]["x"]
            el_dict["pi_y"] = points[pi]["y"]
            el_dict["pj_x"] = points[pj]["x"]
            el_dict["pj_y"] = points[pj]["y"]
        elements.append(el_dict)

    return elements
