"""
Preliminary output → ViewerPage elements[] format adapter.

STAT'ın 3D viewer'ı (IFCScene.jsx) elements[] formatında veri bekler.
Field'lar:
  - ifc_global_id, ifc_type, ifc_name, ifc_story
  - status, unity_check
  - story_height (her element için, hardcoded yerine)
  - Kolon/Perde: x, y, z (taban), sec_width, sec_depth
  - Kiriş: pi_x, pi_y, pj_x, pj_y, z, sec_width, sec_depth
  - Döşeme: x, y, z, slab_lx, slab_ly, slab_thickness (yeni tip IfcSlab)
"""
from typing import List, Dict, Any
from .schemas import PreliminaryOutput


def preliminary_to_elements(out: PreliminaryOutput) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = []
    story_h = out.input.story_height_m
    Lx = out.input.Lx
    Ly = out.input.Ly

    # --- KOLONLAR ---
    for c in out.columns:
        z_base = (c.story - 1) * story_h
        elements.append({
            "ifc_global_id": f"COL-{c.id}",
            "ifc_type": "IfcColumn",
            "ifc_name": f"K-{c.id}",
            "ifc_story": f"Kat-{c.story}",
            "status": "OK",
            "unity_check": None,
            "story_height": story_h,
            "x": c.x,
            "y": c.y,
            "z": z_base,
            "sec_width": c.width_cm / 100.0,
            "sec_depth": c.depth_cm / 100.0,
        })

    # --- KİRİŞLER ---
    for b in out.beams:
        # Kiriş üst kat seviyesinde: elev = (b.story) * story_h
        # IFCScene bunu (el.z + el.story_height) olarak hesaplayacak
        # Yani z = (b.story - 1) * story_h, story_height kendisi eklenecek
        z_bottom = (b.story - 1) * story_h
        elements.append({
            "ifc_global_id": f"BEAM-{b.id}",
            "ifc_type": "IfcBeam",
            "ifc_name": f"B-{b.id}",
            "ifc_story": f"Kat-{b.story}",
            "status": "OK",
            "unity_check": None,
            "story_height": story_h,
            "pi_x": b.start[0],
            "pi_y": b.start[1],
            "pj_x": b.end[0],
            "pj_y": b.end[1],
            "z": z_bottom,
            "sec_width": b.width_cm / 100.0,
            "sec_depth": b.height_cm / 100.0,
        })

    # --- PERDELER ---
    for w in out.walls:
        for story in range(max(w.story_range[0], 1),
                           min(w.story_range[1], out.input.story_count) + 1):
            z_base = (story - 1) * story_h
            if w.orientation == "X":
                sec_w = w.length_m
                sec_d = w.thickness_cm / 100.0
            else:
                sec_w = w.thickness_cm / 100.0
                sec_d = w.length_m
            is_core = w.id.startswith("CORE")
            name_prefix = "Ç" if is_core else "P"
            elements.append({
                "ifc_global_id": f"WALL-{w.id}-S{story}",
                "ifc_type": "IfcWall",
                "ifc_name": f"{name_prefix}-{w.id}",
                "ifc_story": f"Kat-{story}",
                "status": "UNMATCHED",
                "unity_check": None,
                "story_height": story_h,
                "x": w.center[0],
                "y": w.center[1],
                "z": z_base,
                "sec_width": sec_w,
                "sec_depth": sec_d,
            })

    # --- DÖŞEMELER ---
    # Her kat için bir plak
    # Asmolen toplam kalınlık: rib + hf (örn 30+7 = 37cm)
    for slab_data in out.slabs:
        story = slab_data.story
        # Tüm döşeme üst kat seviyesinde (asmolen alt kısmı kiriş üstü)
        # slab üst yüzey: story * story_h
        # slab alt yüzey: story * story_h - slab_thickness
        thickness = slab_data.total_thickness_cm / 100.0
        z_top = story * story_h  # üst yüzey
        z_bottom = z_top - thickness
        # Plan alanı tüm bina (basitleştirilmiş — gerçekte çekirdek açıklığı var ama
        # 3D görselde dolu gösterim kabul edilebilir, kat planı belli olur)
        elements.append({
            "ifc_global_id": f"SLAB-S{story}",
            "ifc_type": "IfcSlab",
            "ifc_name": f"D-Kat{story}",
            "ifc_story": f"Kat-{story}",
            "status": "OK",
            "unity_check": None,
            "story_height": story_h,
            # Merkez + boyutlar
            "x": Lx / 2.0,
            "y": Ly / 2.0,
            "z": z_bottom,
            "slab_lx": Lx,
            "slab_ly": Ly,
            "slab_thickness": thickness,
        })

    return elements


def preliminary_to_stories(out: PreliminaryOutput) -> List[str]:
    return [f"Kat-{i}" for i in range(1, out.input.story_count + 1)]
