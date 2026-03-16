from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.excel_reader import read_excel
from app.core.connectivity_reader import read_connectivity
from app.core.section_reader import read_sections
from app.core.joint_reader import read_joints
from app.core.element_matcher import match_elements
from app.core.rule_engine import apply_rules

router = APIRouter()


@router.post("/compare")
async def compare_revisions(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...),
):
    """İki Excel dosyasını karşılaştırır — revizyon öncesi/sonrası fark analizi."""

    old_bytes = await old_file.read()
    new_bytes = await new_file.read()

    old_elements = _process_file(old_bytes)
    new_elements = _process_file(new_bytes)

    # Story+Label bazlı eşleştirme
    old_map = {(e["ifc_story"], e["ifc_name"]): e for e in old_elements}
    new_map = {(e["ifc_story"], e["ifc_name"]): e for e in new_elements}

    all_keys = set(old_map.keys()) | set(new_map.keys())

    improved = []
    worsened = []
    unchanged = []
    added = []
    removed = []

    for key in sorted(all_keys):
        old_el = old_map.get(key)
        new_el = new_map.get(key)

        if old_el and not new_el:
            removed.append({
                "story": key[0], "label": key[1],
                "old_status": old_el.get("status", ""),
                "old_uc": old_el.get("unity_check"),
            })
        elif new_el and not old_el:
            added.append({
                "story": key[0], "label": key[1],
                "new_status": new_el.get("status", ""),
                "new_uc": new_el.get("unity_check"),
            })
        else:
            old_status = old_el.get("status", "")
            new_status = new_el.get("status", "")
            old_uc = old_el.get("unity_check")
            new_uc = new_el.get("unity_check")

            entry = {
                "story": key[0], "label": key[1],
                "old_status": old_status, "new_status": new_status,
                "old_uc": old_uc, "new_uc": new_uc,
                "status_changed": old_status != new_status,
            }

            status_rank = {"OK": 0, "WARNING": 1, "FAIL": 2, "BRITTLE": 3, "UNMATCHED": -1}
            old_rank = status_rank.get(old_status, -1)
            new_rank = status_rank.get(new_status, -1)

            if new_rank < old_rank:
                improved.append(entry)
            elif new_rank > old_rank:
                worsened.append(entry)
            else:
                unchanged.append(entry)

    return {
        "old_total": len(old_elements),
        "new_total": len(new_elements),
        "improved": improved,
        "worsened": worsened,
        "unchanged_count": len(unchanged),
        "added": added,
        "removed": removed,
        "summary": {
            "improved_count": len(improved),
            "worsened_count": len(worsened),
            "added_count": len(added),
            "removed_count": len(removed),
            "unchanged_count": len(unchanged),
        }
    }


def _process_file(file_bytes):
    """Tek bir Excel dosyasını işleyip enriched element listesi döndürür."""
    from app.core.element_matcher import match_elements as _match
    from app.core.rule_engine import apply_rules as _rules

    excel_rows, _ = read_excel(file_bytes)
    if not excel_rows:
        return []

    connectivity = read_connectivity(file_bytes)
    section_map = read_sections(file_bytes)
    joint_map = read_joints(file_bytes)

    # Basit element oluşturma
    from app.utils.normalize import normalize_label
    import uuid

    _B64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
    def _guid():
        u = uuid.uuid4().int
        chars = []
        for _ in range(22):
            chars.append(_B64[u % 64])
            u //= 64
        return "".join(chars)

    points = connectivity.get("points", {})
    beams = connectivity.get("beams", {})
    columns = connectivity.get("columns", {})

    stories = sorted(set(r.get("excel_story", "") for r in excel_rows if r.get("excel_story")))
    story_elevs = {s: i * 3.0 for i, s in enumerate(stories)}

    elements = []
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

        section_name = row.get("excel_section", "")
        sec_info = section_map.get(section_name, {})

        elements.append({
            "ifc_global_id": _guid(),
            "ifc_name": label,
            "ifc_tag": normalize_label(label),
            "ifc_type": el_type,
            "ifc_story": story,
            "x": 0, "y": 0, "z": elev,
            "sec_depth": sec_info.get("depth", 0.3),
            "sec_width": sec_info.get("width", 0.3),
            "excel_section": section_name,
        })

    matched = _match(elements, excel_rows)
    enriched = _rules(matched, joint_map)
    return enriched
