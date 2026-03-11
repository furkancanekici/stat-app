import ifcopenshell
import tempfile
import os
from app.utils.normalize import normalize_story, normalize_label

SUPPORTED_TYPES = [
    "IfcBeam",
    "IfcColumn",
    "IfcSlab",
    "IfcWall",
    "IfcMember",
]

def fix_turkish_chars(content: bytes) -> bytes:
    replacements = {
        'İ': 'I', 'Ş': 'S', 'Ğ': 'G', 'Ü': 'U', 'Ö': 'O', 'Ç': 'C',
        'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c',
    }
    text = content.decode('utf-8', errors='replace')
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    return text.encode('utf-8')


def read_ifc(file_bytes: bytes) -> tuple[list[dict], str]:
    file_bytes = fix_turkish_chars(file_bytes)

    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        model = ifcopenshell.open(tmp_path)
        ifc_version = model.schema

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
    try:
        for rel in element.ContainedInStructure:
            container = rel.RelatingStructure
            if container.is_a("IfcBuildingStorey"):
                return container.Name
            for rel2 in container.Decomposes:
                parent = rel2.RelatingObject
                if parent.is_a("IfcBuildingStorey"):
                    return parent.Name
    except Exception:
        pass
    return None