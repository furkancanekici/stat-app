from app.models.unified_element import Status


# Eşik değerleri — ileride config dosyasına taşınabilir
THRESHOLDS = {
    "ok": 0.90,        # UC < 0.90 → Yeterli
    "warning": 1.00,   # 0.90 ≤ UC < 1.00 → Sınırda
    "fail": 1.00,      # UC ≥ 1.00 → Yetersiz
}

BRITTLE_KEYWORDS = [
    "shear", "kesme", "torsion", "burulma",
    "buckling", "burkulma", "compression", "basinc"
]


def classify_status(
    unity_check: float | None,
    failure_mode: str | None
) -> Status:
    """
    Unity check ve failure mode'a göre eleman durumunu belirler.
    """
    if unity_check is None:
        return Status.UNMATCHED

    fm = (failure_mode or "").lower()

    # Gevrek kontrol — failure mode'a bakılır
    is_brittle = any(kw in fm for kw in BRITTLE_KEYWORDS)

    if unity_check >= THRESHOLDS["fail"]:
        if is_brittle:
            return Status.BRITTLE
        return Status.FAIL

    if unity_check >= THRESHOLDS["ok"]:
        return Status.WARNING

    return Status.OK


def get_status_color(status: Status) -> str:
    """
    Viewer'da kullanılacak hex renk kodları.
    """
    colors = {
        Status.OK:        "#22c55e",  # yeşil
        Status.WARNING:   "#eab308",  # sarı
        Status.FAIL:      "#ef4444",  # kırmızı
        Status.BRITTLE:   "#f97316",  # turuncu
        Status.UNMATCHED: "#64748b",  # gri
    }
    return colors.get(status, "#64748b")


def apply_rules(elements: list[dict]) -> list[dict]:
    for el in elements:
        uc = el.get("unity_check")
        fm = el.get("failure_mode", "")
        status = classify_status(uc, fm)
        el["status"] = status.value
        el["status_color"] = get_status_color(status)
    return elements