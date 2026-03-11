from app.utils.normalize import normalize_label, normalize_story

MIN_SCORE = 0.5  # Story olmadığı için eşik düşürüldü
LOW_CONFIDENCE_THRESHOLD = 0.7


def match_elements(
    ifc_elements: list[dict],
    excel_rows: list[dict],
) -> list[dict]:
    results = []

    for ifc_el in ifc_elements:
        ifc_tag = normalize_label(ifc_el.get("ifc_tag") or ifc_el.get("ifc_name") or "")
        best_match = None
        best_score = 0.0

        for ex_row in excel_rows:
            score = _score(ifc_el, ifc_tag, ex_row)
            if score > best_score:
                best_score = score
                best_match = ex_row

        merged = dict(ifc_el)

        if best_match and best_score >= MIN_SCORE:
            merged.update({
                "excel_label":      best_match.get("excel_label", ""),
                "excel_story":      best_match.get("excel_story", ""),
                "excel_section":    best_match.get("excel_section", ""),
                "unity_check":      best_match.get("unity_check"),
                "failure_mode":     best_match.get("failure_mode", ""),
                "governing_combo":  best_match.get("governing_combo", ""),
                "match_score":      round(best_score, 3),
                "matched":          True,
                # Story'yi Excel'den al
                "ifc_story":        best_match.get("excel_story", ifc_el.get("ifc_story", "")),
            })
        else:
            merged.update({
                "excel_label": "",
                "excel_story": "",
                "excel_section": "",
                "unity_check": None,
                "failure_mode": "",
                "governing_combo": "",
                "match_score": 0.0,
                "matched": False,
            })

        results.append(merged)

    return results


def _score(ifc_el: dict, ifc_tag: str, ex_row: dict) -> float:
    ex_label = normalize_label(ex_row.get("excel_label", ""))

    # Label eşleşmesi — tek kriter (story yok)
    if not ifc_tag or not ex_label:
        return 0.0

    if ifc_tag == ex_label:
        return 1.0

    # Kısmi eşleşme
    if ifc_tag in ex_label or ex_label in ifc_tag:
        return 0.6

    return 0.0