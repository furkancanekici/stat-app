"""
ETABS API endpoint'leri.

/api/etabs/status  — ETABS erişilebilir mi, model açık mı?
/api/etabs/analyze — ETABS'tan tabloları çek + STAT analizi yap (summary döndür)
/api/etabs/export  — ETABS'tan tabloları çekip Excel olarak indir
"""

import os
import re
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/etabs", tags=["etabs"])


@router.get("/status")
async def etabs_status():
    """
    ETABS API erişilebilirliğini kontrol eder.
    available_tables: modeldeki tüm tablo isimleri (debug için)
    """
    try:
        from app.core.etabs_exporter import check_etabs_available
        result = check_etabs_available()

        # Model açıksa mevcut tabloları da listele
        if result.get("model_open"):
            try:
                from app.core.etabs_exporter import _connect_etabs, _get_available_tables, _match_tables, STAT_TABLE_KEYWORDS
                _, SapModel = _connect_etabs(None)
                available = _get_available_tables(SapModel)
                matched = _match_tables(available, STAT_TABLE_KEYWORDS)
                result["available_tables_count"] = len(available)
                result["matched_tables"] = matched
                result["matched_count"] = len(matched)
            except Exception:
                pass

        return result
    except ImportError:
        return {
            "available": False,
            "message": "ETABS modülü yüklenemedi.",
            "model_open": False,
            "model_name": "",
        }
    except Exception as e:
        return {
            "available": False,
            "message": str(e),
            "model_open": False,
            "model_name": "",
        }


@router.post("/analyze")
async def etabs_analyze(
    model_path: str = Query(default=None, description=".EDB dosya yolu (boş ise açık modele bağlanır)"),
    skip_analysis: bool = Query(default=False, description="Analizi atla"),
    skip_design: bool = Query(default=False, description="Design'ı atla"),
):
    """
    ETABS'tan tabloları çekip doğrudan STAT analizinden geçirir.

    Akış:
    1. ETABS'a bağlan (açık model veya .EDB yolu)
    2. Analiz + Concrete Frame Design çalıştır
    3. Tabloları çek → Excel bytes
    4. Excel bytes'ı STAT reader'larına ver
    5. Summary (elements, status, drift, torsion, vb.) döndür

    Frontend bu endpoint'in sonucunu doğrudan ViewerPage'e yönlendirir —
    tıpkı Excel yükleme akışındaki /api/summary gibi.
    """
    try:
        from app.core.etabs_exporter import export_from_etabs
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"ETABS modülü yüklenemedi: {e}")

    # 1) ETABS'tan tabloları çek
    try:
        excel_bytes = export_from_etabs(
            model_path=model_path,
            run_analysis=not skip_analysis,
            run_design=not skip_design,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETABS hatası: {e}")

    # 2) Mevcut STAT pipeline'ından geçir (enrich.py'deki _read_all ile aynı)
    from app.core.excel_reader import read_excel
    from app.core.connectivity_reader import read_connectivity
    from app.core.section_reader import read_sections
    from app.core.joint_reader import read_joints
    from app.core.drift_reader import read_story_drifts, read_torsion_irregularity
    from app.core.material_reader import read_materials, read_seismic_params
    from app.core.forces_reader import read_element_forces
    from app.core.element_matcher import match_elements
    from app.core.rule_engine import apply_rules
    from collections import defaultdict

    try:
        excel_rows, missing = read_excel(excel_bytes)
        if missing:
            raise HTTPException(status_code=400, detail=f"Eksik sütunlar: {missing}")

        connectivity = read_connectivity(excel_bytes)
        section_map = read_sections(excel_bytes)
        joint_map = read_joints(excel_bytes)
        drift_map = read_story_drifts(excel_bytes)
        torsion_map = read_torsion_irregularity(excel_bytes)
        materials = read_materials(excel_bytes)
        seismic_params = read_seismic_params(excel_bytes)
        forces_map = read_element_forces(excel_bytes)

        # enrich.py'deki _build_ifc_elements_from_connectivity'yi kullan
        from app.routers.enrich import _build_ifc_elements_from_connectivity
        ifc_elements = _build_ifc_elements_from_connectivity(
            connectivity, excel_rows, section_map
        )

        matched = match_elements(ifc_elements, excel_rows)
        enriched = apply_rules(
            matched,
            joint_map=joint_map,
            drift_map=drift_map,
            torsion_map=torsion_map,
            forces_map=forces_map,
            materials=materials,
            seismic_params=seismic_params,
        )

        # Summary oluştur (enrich.py'deki /summary ile aynı format)
        status_counts = defaultdict(int)
        by_story_map = defaultdict(lambda: defaultdict(int))
        unmatched = []
        total_warnings = 0

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
            total_warnings += el.get("warning_count", 0)

        by_story = [
            {"story": s, "total": c["total"], "fail": c.get("fail", 0), "warning": c.get("warning", 0)}
            for s, c in sorted(by_story_map.items())
        ]

        return {
            "source": "etabs",
            "total": len(enriched),
            "status_counts": dict(status_counts),
            "by_story": by_story,
            "unmatched_elements": unmatched,
            "total_warnings": total_warnings,
            "materials": materials,
            "seismic_params": seismic_params,
            "drift_summary": drift_map,
            "torsion_summary": torsion_map,
            "elements": enriched,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STAT analiz hatası: {e}")


@router.post("/export")
async def etabs_export_excel(
    model_path: str = Query(default=None, description=".EDB dosya yolu"),
    skip_analysis: bool = Query(default=False),
    skip_design: bool = Query(default=False),
):
    """
    ETABS'tan tabloları çekip Excel dosyası olarak indirir.
    Kullanıcı ileride bu Excel'i tekrar yükleyebilir.
    """
    try:
        from app.core.etabs_exporter import export_from_etabs
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"ETABS modülü yüklenemedi: {e}")

    try:
        excel_bytes = export_from_etabs(
            model_path=model_path,
            run_analysis=not skip_analysis,
            run_design=not skip_design,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    model_name = "etabs_export"
    if model_path:
        raw_name = os.path.splitext(os.path.basename(model_path))[0]
        model_name = re.sub(r"[^\x00-\x7F]", "_", raw_name)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={model_name}_tables.xlsx"},
    )
