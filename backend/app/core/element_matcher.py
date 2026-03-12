from app.utils.normalize import normalize_label, normalize_story

MIN_SCORE = 0.5
LOW_CONFIDENCE_THRESHOLD = 0.7


def match_elements(
    ifc_elements: list[dict],
    excel_rows: list[dict],
) -> list[dict]:
    results = []

    for ifc_el in ifc_elements:
        ifc_tag = normalize_label(ifc_el.get("ifc_tag") or ifc_el.get("ifc_name") or "")
        ifc_story = ifc_el.get("ifc_story", "")
        best_match = None
        best_score = 0.0

        for ex_row in excel_rows:
            score = _score(ifc_tag, ifc_story, ex_row)
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
                # Story'yi orijinal ifc_story'den koru (match story'yi ezmesin)
                "ifc_story":        ifc_el.get("ifc_story", ""),
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


def _score(ifc_tag: str, ifc_story: str, ex_row: dict) -> float:
    ex_label = normalize_label(ex_row.get("excel_label", ""))
    ex_story = ex_row.get("excel_story", "")

    if not ifc_tag or not ex_label:
        return 0.0

    # Label eşleşmesi
    label_score = 0.0
    if ifc_tag == ex_label:
        label_score = 1.0
    elif ifc_tag in ex_label or ex_label in ifc_tag:
        label_score = 0.6
    else:
        return 0.0

    # Story eşleşmesi — aynı story ise bonus, farklıysa ceza
    if ifc_story and ex_story:
        if ifc_story == ex_story:
            return label_score  # Tam eşleşme (story + label)
        else:
            return label_score * 0.3  # Label eşleşiyor ama story farklı → çok düşük skor
    
    # Story bilgisi yoksa sadece label skoru
    return label_score