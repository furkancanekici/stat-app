import ifcopenshell
import ifcopenshell.api
import tempfile
import os
from app.models.unified_element import UnifiedElementData, Status
from app.core.rule_engine import get_status_color


PSET_NAME = "STAT_Analysis"


def enrich_ifc(
    file_bytes: bytes,
    elements: list[UnifiedElementData]
) -> bytes:
    """
    IFC dosyasına STAT_Analysis PropertySet yazar.
    Zenginleştirilmiş IFC'yi bytes olarak döner.
    """
    # Geçici dosyaya yaz
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp_in:
        tmp_in.write(file_bytes)
        tmp_in_path = tmp_in.name

    tmp_out_path = tmp_in_path.replace(".ifc", "_enriched.ifc")

    try:
        model = ifcopenshell.open(tmp_in_path)

        # GlobalId → UnifiedElementData map
        element_map = {el.ifc_global_id: el for el in elements}

        for ifc_element in model.by_type("IfcElement"):
            ued = element_map.get(ifc_element.GlobalId)
            if not ued:
                continue

            _write_pset(model, ifc_element, ued)

        model.write(tmp_out_path)

        with open(tmp_out_path, "rb") as f:
            return f.read()

    finally:
        os.unlink(tmp_in_path)
        if os.path.exists(tmp_out_path):
            os.unlink(tmp_out_path)


def _write_pset(model, ifc_element, ued: UnifiedElementData):
    """
    Tek bir elemana STAT_Analysis PropertySet yazar.
    """
    status_str = ued.status.value if ued.status else "UNMATCHED"
    color_str = get_status_color(ued.status) if ued.status else "#64748b"

    properties = {
        "Status":          status_str,
        "UnityCheck":      str(round(ued.unity_check, 4)) if ued.unity_check is not None else "",
        "FailureMode":     ued.failure_mode or "",
        "GoverningCombo":  ued.governing_combo or "",
        "MatchScore":      str(round(ued.match_score, 3)),
        "StatusColor":     color_str,
        "Source":          "STAT_v1",
    }

    # Mevcut STAT_Analysis pset'i varsa sil
    _remove_existing_pset(model, ifc_element)

    # Yeni pset oluştur
    pset = ifcopenshell.api.run(
        "pset.add_pset",
        model,
        product=ifc_element,
        name=PSET_NAME
    )

    for prop_name, prop_value in properties.items():
        ifcopenshell.api.run(
            "pset.edit_pset",
            model,
            pset=pset,
            properties={prop_name: prop_value}
        )


def _remove_existing_pset(model, ifc_element):
    """
    Varsa mevcut STAT_Analysis pset'ini siler (çift yazımı önler).
    """
    try:
        for rel in ifc_element.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                pdef = rel.RelatingPropertyDefinition
                if (pdef.is_a("IfcPropertySet") and
                        pdef.Name == PSET_NAME):
                    ifcopenshell.api.run(
                        "pset.remove_pset",
                        model,
                        product=ifc_element,
                        pset=pdef
                    )
    except Exception:
        pass