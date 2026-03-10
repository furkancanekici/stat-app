import ifcopenshell
from io import BytesIO
from app.utils.normalize import normalize_story, normalize_label


# Desteklenen IFC eleman tipleri
SUPPORTED_TYPES = [
    "IfcBeam",
    "IfcColumn",
    "IfcSlab",
    "IfcWall",
    "IfcBrace",
    "IfcMember",
]


def read_ifc(file_bytes: bytes) -> tuple[list[dict], str]:
    """
    IFC dosyasını okur, eleman listesi ve versiyon döner.
    Returns: (elements, ifc_version)
    """
    # Geçici dosya yerine memory'den oku
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        model = ifcopenshell.open(tmp_path)
        ifc_version = model.schema  # "IFC2X3" veya "IFC4"

        elements = []
        for ifc_type in SUPPORTED_TYPES:
            for element in model.by_type(ifc_type):
                story = _get_story(element)
                elements.append({
                    "ifc_global_id": element.GlobalId,
                    "ifc_name":      element.Name,
                    "ifc_tag":       normalize_label(element.Tag or ""),
                    "ifc_type":      ifc_type,
                    "ifc_story":     normalize_story(story or ""),
                })

        return elements, ifc_version

    finally:
        os.unlink(tmp_path)


def _get_story(element) -> str | None:
    """
    Elemanın bulunduğu katı (IfcBuildingStorey) bulur.
    """
    try:
        for rel in element.ContainedInStructure:
            container = rel.RelatingStructure
            if container.is_a("IfcBuildingStorey"):
                return container.Name
            # Üst konteynere bak
            for rel2 in container.Decomposes:
                parent = rel2.RelatingObject
                if parent.is_a("IfcBuildingStorey"):
                    return parent.Name
    except Exception:
        pass
    return None