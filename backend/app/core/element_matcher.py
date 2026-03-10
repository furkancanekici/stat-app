from app.models.unified_element import UnifiedElementData, Status
from app.utils.normalize import normalize_label, normalize_story
from app.core.rule_engine import classify_status

MIN_SCORE = 0.6
LOW_CONFIDENCE_THRESHOLD = 0.75


def match_elements(
    ifc_elements: list[dict],
    excel_rows: list[dict]
) -> list[UnifiedElementData]:
    results = []

    for ifc_el in ifc_elements:
        best_match = None
        best_score = 0.0

        for excel_row in excel_rows:
            score = _calculate_score(ifc_el, excel_row)
            if score > best_score:
                best_score = score
                best_match = excel_row

        if best_match and best_score >= MIN_SCORE:
            status = classify_status(
                best_match.get("unity_check"),
                best_match.get("failure_mode")
            )
            results.append(UnifiedElementData(
                ifc_global_id=ifc_el["ifc_global_id"],
                ifc_name=ifc_el.get("ifc_name"),
                ifc_tag=ifc_el.get("ifc_tag"),
                ifc_type=ifc_el["ifc_type"],
                ifc_story=ifc_el.get("ifc_story"),
                excel_label=best_match.get("excel_label"),
                unity_check=best_match.get("unity_check"),
                failure_mode=best_match.get("failure_mode"),
                governing_combo=best_match.get("governing_combo"),
                status=status,
                match_score=round(best_score, 3),
            ))
        else:
            results.append(UnifiedElementData(
                ifc_global_id=ifc_el["ifc_global_id"],
                ifc_name=ifc_el.get("ifc_name"),
                ifc_tag=ifc_el.get("ifc_tag"),
                ifc_type=ifc_el["ifc_type"],
                ifc_story=ifc_el.get("ifc_story"),
                status=Status.UNMATCHED,
                match_score=0.0,
            ))

    return results


def _calculate_score(ifc_el: dict, excel_row: dict) -> float:
    score = 0.0
    weights = {
        "tag_label": 0.60,
        "story":     0.30,
        "type":      0.10,
    }

    ifc_tag = ifc_el.get("ifc_tag") or ""
    ifc_name = normalize_label(ifc_el.get("ifc_name") or "")
    excel_label = excel_row.get("excel_label") or ""

    if excel_label:
        if ifc_tag == excel_label:
            score += weights["tag_label"] * 1.0
        elif ifc_name == excel_label:
            score += weights["tag_label"] * 0.9
        elif excel_label in ifc_tag or ifc_tag in excel_label:
            score += weights["tag_label"] * 0.7
        elif excel_label in ifc_name or ifc_name in excel_label:
            score += weights["tag_label"] * 0.6

    ifc_story = ifc_el.get("ifc_story") or ""
    excel_story = excel_row.get("excel_story") or ""

    if ifc_story and excel_story:
        if ifc_story == excel_story:
            score += weights["story"] * 1.0
        elif ifc_story in excel_story or excel_story in ifc_story:
            score += weights["story"] * 0.7
    elif not ifc_story and not excel_story:
        score += weights["story"] * 0.5

    ifc_type = ifc_el.get("ifc_type", "").lower()
    excel_label_lower = excel_label.lower()

    type_hints = {
        "ifcbeam":   ["b", "kir", "beam"],
        "ifccolumn": ["c", "col", "kolon"],
        "ifcslab":   ["s", "slab", "doseme"],
        "ifcwall":   ["w", "wall", "perde"],
        "ifcbrace":  ["br", "brace", "capraz"],
    }

    hints = type_hints.get(ifc_type, [])
    if any(excel_label_lower.startswith(h) for h in hints):
        score += weights["type"] * 1.0

    return min(score, 1.0)


def get_low_confidence(elements: list[UnifiedElementData]) -> list[str]:
    return [
        el.ifc_global_id
        for el in elements
        if el.status != Status.UNMATCHED
        and el.match_score < LOW_CONFIDENCE_THRESHOLD
    ]