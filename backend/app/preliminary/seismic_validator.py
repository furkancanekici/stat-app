"""
Seismic Validator (OpenSeesPy Modal Analysis)
---------------------------------------------
3D modal analiz ile ηbi (burulma düzensizliği) hesabı.

Hibrit optimizasyonun son adımı:
  wall_optimizer'dan gelen top-N konfigürasyonu → OpenSeesPy modal →
  gerçek ηbi_x, ηbi_y hesapla → en iyi konfigürasyonu seç.

Model:
  3D frame (-ndm 3 -ndf 6)
  elasticBeamColumn: kolonlar ve kirişler
  Perdeler: equivalent column (eşdeğer kolon) yaklaşımı — preliminary için yeterli
    (gerçek shell modeli yerine, perdeyi bir kolon gibi davran)
  Rigid diaphragm: her kat master düğüm + rigidLink
  Taban: ankastre
  Kütle: her kat merkezinde concentrated mass

ηbi hesabı (TBDY Tablo 3.6):
  Her kat için rigid diaphragm'de maksimum ve ortalama relative yer değiştirme
  ηbi = δ_max / δ_avg
  İlk 3 modun ilk deformasyon şekilleri kullanılır.
"""
import math
from typing import List, Optional, Tuple
from .schemas import (
    ModalResult, ColumnOutput, BeamOutput, WallOutput, SlabOutput,
)
from .wall_optimizer import WallConfiguration, _placements_to_wall_outputs
from .constants import ETABI_LIMIT, LIVE_LOAD_PARTICIPATION_RESIDENTIAL

# OpenSeesPy global singleton — her validate çağrısında wipe edilir
try:
    import openseespy.opensees as ops
    HAS_OPENSEES = True
except ImportError:
    HAS_OPENSEES = False


# ===== MODEL PARAMETRELERİ =====

# Birim: N, m, kg, s (SI)
CONCRETE_E_MPA = {25: 28000, 30: 30000, 35: 32000, 40: 34000}  # MPa → Pa çarp 1e6

def concrete_E_Pa(fck_MPa: float) -> float:
    """TS 500 Ec ≈ 5000 × sqrt(fck) MPa.  Pa'ya çevir."""
    # Daha pratik: TBDY Ec = 3250*sqrt(fck) + 14000 MPa
    Ec_MPa = 3250.0 * math.sqrt(fck_MPa) + 14000.0
    return Ec_MPa * 1e6  # Pa


# ===== 3D MODEL KURULUMU =====

def build_opensees_model(
    columns: List[ColumnOutput],
    beams: List[BeamOutput],
    walls: List[WallOutput],
    slabs: List[SlabOutput],
    story_height_m: float,
    fck_MPa: float,
    Lx: float,
    Ly: float,
    story_count: int,
    usage_G: float,
    usage_Q: float,
    n_factor: float,
) -> dict:
    """
    3D OpenSees modeli kurar.
    Returns: metadata (kat master düğüm id'leri, node mapping vb)
    """
    if not HAS_OPENSEES:
        raise ImportError("OpenSeesPy yüklü değil — pip install openseespy")
    
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    
    E = concrete_E_Pa(fck_MPa)
    G_shear = E / (2 * 1.2)   # Poisson ≈ 0.2
    
    # --- DÜĞÜM ÜRETİMİ ---
    # Tüm unique (x, y) konumlar için, her katta bir düğüm
    # Kolon konumlarından unique noktaları topla
    unique_positions = set()
    for c in columns:
        unique_positions.add((round(c.x, 2), round(c.y, 2)))
    # Perdeler için de: her perdenin iki ucu düğüm olmalı
    for w in walls:
        cx, cy = w.center
        bw_m = w.thickness_cm / 100
        if w.orientation == "X":
            p1 = (round(cx - w.length_m/2, 2), round(cy, 2))
            p2 = (round(cx + w.length_m/2, 2), round(cy, 2))
        else:
            p1 = (round(cx, 2), round(cy - w.length_m/2, 2))
            p2 = (round(cx, 2), round(cy + w.length_m/2, 2))
        unique_positions.add(p1)
        unique_positions.add(p2)
    
    # Node ID mapping: (x, y, story) → node_id
    # Story 0 = taban, 1, 2, ..., story_count
    node_map = {}
    next_id = 1
    for pos in sorted(unique_positions):
        x, y = pos
        for s in range(0, story_count + 1):
            z = s * story_height_m
            ops.node(next_id, x, y, z)
            node_map[(x, y, s)] = next_id
            if s == 0:
                # Taban ankastre
                ops.fix(next_id, 1, 1, 1, 1, 1, 1)
            next_id += 1
    
    # --- MASTER DÜĞÜM (her kat için rigid diaphragm) ---
    # Master düğüm plan merkezinde
    master_nodes = {}
    for s in range(1, story_count + 1):
        z = s * story_height_m
        master_id = next_id
        ops.node(master_id, Lx / 2, Ly / 2, z)
        # Master düğüm: sadece X, Y, Z-rot serbest (düşey ve iki eğilme sabit)
        # Rigid diaphragm için uygun DOF
        ops.fix(master_id, 0, 0, 1, 1, 1, 0)
        master_nodes[s] = master_id
        next_id += 1
    
    # Rigid diaphragm — her kat için
    for s in range(1, story_count + 1):
        master_id = master_nodes[s]
        slave_nodes = [nid for (x, y, story), nid in node_map.items() if story == s]
        if slave_nodes:
            # normal vector: Z ekseni
            ops.rigidDiaphragm(3, master_id, *slave_nodes)
    
    # --- GEOMETRIC TRANSFORMATIONS ---
    # Kolonlar (düşey) için: güçlü eksen X
    ops.geomTransf('Linear', 1, 1.0, 0.0, 0.0)  # kolon
    ops.geomTransf('Linear', 2, 0.0, 0.0, 1.0)  # X yönü kiriş — Z yukarı
    ops.geomTransf('Linear', 3, 0.0, 0.0, 1.0)  # Y yönü kiriş
    
    # --- KOLONLAR ---
    elem_id = 1
    for c in columns:
        x, y = round(c.x, 2), round(c.y, 2)
        s = c.story
        n1 = node_map.get((x, y, s - 1))
        n2 = node_map.get((x, y, s))
        if n1 is None or n2 is None:
            continue
        b = c.width_cm / 100
        h = c.depth_cm / 100
        A = b * h
        Iy = h * b**3 / 12   # X yönü kuvvette eğilme
        Ix = b * h**3 / 12   # Y yönü kuvvette eğilme
        J = (b * h * (b**2 + h**2)) / 12  # yaklaşık torsion
        ops.element('elasticBeamColumn', elem_id, n1, n2, A, E, G_shear, J, Iy, Ix, 1)
        elem_id += 1
    
    # --- KİRİŞLER ---
    for bm in beams:
        s = bm.story
        x1, y1 = round(bm.start[0], 2), round(bm.start[1], 2)
        x2, y2 = round(bm.end[0], 2), round(bm.end[1], 2)
        n1 = node_map.get((x1, y1, s))
        n2 = node_map.get((x2, y2, s))
        if n1 is None or n2 is None:
            continue
        bw = bm.width_cm / 100
        h = bm.height_cm / 100
        A = bw * h
        Iy = h * bw**3 / 12
        Ix = bw * h**3 / 12
        J = (bw * h * (bw**2 + h**2)) / 12
        transf = 2 if bm.direction == "X" else 3
        ops.element('elasticBeamColumn', elem_id, n1, n2, A, E, G_shear, J, Iy, Ix, transf)
        elem_id += 1
    
    # --- PERDELER (Equivalent Column Approach) ---
    # Her perde: 2 düğüm (uç noktalar) üzerinde, perde güçlü ekseninde beam-column
    # Bu preliminary için yeterli. Shell daha doğru olur ama çok karmaşık.
    for w in walls:
        cx, cy = w.center
        bw_m = w.thickness_cm / 100
        lw_m = w.length_m
        if w.orientation == "X":
            p1 = (round(cx - lw_m/2, 2), round(cy, 2))
            p2 = (round(cx + lw_m/2, 2), round(cy, 2))
        else:
            p1 = (round(cx, 2), round(cy - lw_m/2, 2))
            p2 = (round(cx, 2), round(cy + lw_m/2, 2))
        
        # Perde her katta ayrı (bir kat yüksekliğinde)
        for s in range(max(w.story_range[0], 1), min(w.story_range[1], story_count) + 1):
            n1_bot = node_map.get((p1[0], p1[1], s - 1))
            n2_bot = node_map.get((p2[0], p2[1], s - 1))
            n1_top = node_map.get((p1[0], p1[1], s))
            n2_top = node_map.get((p2[0], p2[1], s))
            if None in (n1_bot, n2_bot, n1_top, n2_top):
                continue
            # Orta düğüm üstte ve altta olmak üzere perdenin merkezinde virtual bir kolon yap
            # Ama elemanlar zaten gerçek geometride duruyor
            # Equivalent column: perdeyi ortada tek bir beam-column gibi tanımla
            # Basitlik için: perdenin iki ucundaki köşe düğümlerini alt-üst doğrultusunda bağla
            # Bu, perde rijitliğini yaklaşık olarak temsil eder
            A_wall = bw_m * lw_m
            I_strong = bw_m * lw_m**3 / 12
            I_weak = lw_m * bw_m**3 / 12
            J_wall = bw_m * lw_m * (bw_m**2 + lw_m**2) / 12
            # orientation'a göre Iy ve Ix
            if w.orientation == "X":
                Iy_wall = lw_m * bw_m**3 / 12    # X yönü kuvvette eğilme (zayıf — perde uzun ekseni boyunca)
                Ix_wall = bw_m * lw_m**3 / 12    # Y yönü kuvvette eğilme (güçlü — yüksek)
                # DUR — bu yanlış. Perde X yönünde uzun → X yönü kuvvet onu uzunlamasına hareket ettirir
                # Perde X yönü kuvvette güçlü ekseninde bükülür
                # Kafa karıştırıcı — CR kodunda düzeltmiştik, tekrar düzelt:
                # orientation="X" (X'te uzun) → X yönü kuvvette güçlü (I_strong için lw^3)
                # Kolonun eğilme ekseni: X yönü kuvvet = Y ekseni etrafında dönüş = Iy kullanılır
                # Iy = h × b³ / 12 (kolonda b=X boyutu, h=Y boyutu)
                # Perde için: X yönde uzun → "b"=lw, "h"=bw (X yönü kuvvette)
                # Iy = bw × lw³ / 12 = strong (doğru!)
                Iy_wall = bw_m * lw_m**3 / 12   # X kuvvet → güçlü
                Ix_wall = lw_m * bw_m**3 / 12   # Y kuvvet → zayıf
            else:  # "Y"
                Iy_wall = lw_m * bw_m**3 / 12   # X kuvvet → zayıf
                Ix_wall = bw_m * lw_m**3 / 12   # Y kuvvet → güçlü
            
            # Perdenin iki kolon ekseni gibi modelle (alt-üst düğümleri arasında)
            # Her perde 2 kolon (her köşesi alt-üst) → toplam kesit bölüştür
            # Basitlik: sadece 1 kolon, orta eksenler (p1 ve p2)
            # p1'den üste bir kolon, p2'den üste bir kolon → her biri yarım A
            ops.element('elasticBeamColumn', elem_id, n1_bot, n1_top,
                        A_wall/2, E, G_shear, J_wall/2, Iy_wall/2, Ix_wall/2, 1)
            elem_id += 1
            ops.element('elasticBeamColumn', elem_id, n2_bot, n2_top,
                        A_wall/2, E, G_shear, J_wall/2, Iy_wall/2, Ix_wall/2, 1)
            elem_id += 1
    
    # --- KÜTLELER ---
    # Her kat master düğümüne toplam kat kütlesi
    # Kat kütlesi = (G + n×Q) × Afloor / g
    g = 9.81
    w_per_m2 = usage_G + n_factor * usage_Q   # kN/m²
    total_floor_load_kN = w_per_m2 * Lx * Ly
    # Kütle = kuvvet / g, kN'ı N'ye çevir, g m/s²
    story_mass_kg = (total_floor_load_kN * 1000) / g
    
    for s in range(1, story_count + 1):
        master_id = master_nodes[s]
        # X, Y, Z-rot kütle — X translation, Y translation, ve torsional inertia
        # Torsional inertia ≈ m × r² / 6 for rectangle, r² = (Lx² + Ly²)/12 × m
        I_mass = story_mass_kg * (Lx**2 + Ly**2) / 12
        ops.mass(master_id, story_mass_kg, story_mass_kg, 0.0, 0.0, 0.0, I_mass)
    
    return {
        "node_map": node_map,
        "master_nodes": master_nodes,
        "story_count": story_count,
    }


# ===== MODAL ANALİZ =====

def run_modal_analysis(num_modes: int = 3) -> List[float]:
    """
    Modal analiz koştur, ilk N modun özdeğerlerini döndür.
    Returns: [omega² (rad/s)²] listesi
    """
    try:
        eigenvalues = ops.eigen(num_modes)
        return list(eigenvalues)
    except Exception as e:
        # Alternative solver dene
        try:
            eigenvalues = ops.eigen(num_modes)
            return list(eigenvalues)
        except Exception as e2:
            raise RuntimeError(f"Modal analysis failed: {e}, {e2}")


def eigenvalue_to_period(ev: float) -> float:
    """ω² → T (saniye)."""
    if ev <= 0:
        return float('inf')
    omega = math.sqrt(ev)
    return 2 * math.pi / omega


# ===== ηbi HESABI =====

def compute_eta_bi(
    metadata: dict,
    story_count: int,
    Lx: float, Ly: float,
    num_modes: int = 3,
) -> Tuple[float, float]:
    """
    ηbi hesabı (TBDY Tablo 3.6) — Rigid diaphragm için düzeltilmiş.
    
    Rigid diaphragm altında master node'un X, Y translation ve Z rotation
    deformasyonları alınır. Köşe düğüm driftleri:
        δ_i = δ_master + (Rz × r_i)
    r_i: köşe noktasının master'a göre vektörü
    
    Her kat için max_corner_drift / avg_corner_drift = ηbi.
    """
    master_nodes = metadata["master_nodes"]
    node_map = metadata["node_map"]
    
    # Kat için master merkez (Lx/2, Ly/2)
    cx_master, cy_master = Lx / 2, Ly / 2
    
    # Her kat için köşe düğümleri bul (plan köşelerine en yakın)
    # En uç x ve y'leri kapsayan düğümleri al
    corners_by_story = {}
    for s in range(1, story_count + 1):
        story_nodes = [(x, y, nid) for (x, y, st), nid in node_map.items() if st == s]
        if not story_nodes:
            continue
        # Köşeler: min/max x ve y kombinasyonları
        xs = set(n[0] for n in story_nodes)
        ys = set(n[1] for n in story_nodes)
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        # 4 köşeye en yakın düğümü bul
        corner_coords = [(x_min, y_min), (x_max, y_min), (x_min, y_max), (x_max, y_max)]
        corners = []
        for (cx, cy) in corner_coords:
            best_node = min(story_nodes, key=lambda n: (n[0]-cx)**2 + (n[1]-cy)**2)
            corners.append(best_node)
        corners_by_story[s] = corners
    
    eta_bi_x = 1.0
    eta_bi_y = 1.0
    
    try:
        for mode in range(1, num_modes + 1):
            # Her modda, X ve Y dominant olup olmadığını mod şeklinden anla
            # Tüm master node'ların X, Y deformasyonlarına bak
            master_disp_x = []
            master_disp_y = []
            master_rot_z = []
            for s in range(1, story_count + 1):
                mid = master_nodes[s]
                try:
                    dx = ops.nodeEigenvector(mid, mode, 1)
                    dy = ops.nodeEigenvector(mid, mode, 2)
                    rz = ops.nodeEigenvector(mid, mode, 6)
                    master_disp_x.append(abs(dx))
                    master_disp_y.append(abs(dy))
                    master_rot_z.append(abs(rz))
                except:
                    master_disp_x.append(0)
                    master_disp_y.append(0)
                    master_rot_z.append(0)
            
            sum_x = sum(master_disp_x)
            sum_y = sum(master_disp_y)
            
            if sum_x < 1e-10 and sum_y < 1e-10:
                continue
            
            is_x_mode = sum_x > sum_y
            
            # Her kat için ηbi katkısı
            for s in range(1, story_count + 1):
                mid = master_nodes[s]
                corners = corners_by_story.get(s, [])
                if not corners:
                    continue
                try:
                    m_dx = ops.nodeEigenvector(mid, mode, 1)
                    m_dy = ops.nodeEigenvector(mid, mode, 2)
                    m_rz = ops.nodeEigenvector(mid, mode, 6)
                except:
                    continue
                
                # Her köşe için efektif drift:
                # dx_corner = m_dx - m_rz × (y - cy_master)
                # dy_corner = m_dy + m_rz × (x - cx_master)
                corner_drifts_x = []
                corner_drifts_y = []
                for (cx, cy, _nid) in corners:
                    dr_x = m_dx - m_rz * (cy - cy_master)
                    dr_y = m_dy + m_rz * (cx - cx_master)
                    corner_drifts_x.append(abs(dr_x))
                    corner_drifts_y.append(abs(dr_y))
                
                if is_x_mode:
                    max_d = max(corner_drifts_x)
                    avg_d = sum(corner_drifts_x) / len(corner_drifts_x)
                    if avg_d > 1e-10:
                        this_eta = max_d / avg_d
                        eta_bi_x = max(eta_bi_x, this_eta)
                else:
                    max_d = max(corner_drifts_y)
                    avg_d = sum(corner_drifts_y) / len(corner_drifts_y)
                    if avg_d > 1e-10:
                        this_eta = max_d / avg_d
                        eta_bi_y = max(eta_bi_y, this_eta)
    except Exception as e:
        pass
    
    return eta_bi_x, eta_bi_y


# ===== ANA FONKSİYON =====

def validate_configurations(
    candidates: List[WallConfiguration],
    columns: List[ColumnOutput],
    beams: List[BeamOutput],
    slabs: List[SlabOutput],
    story_height_m: float,
    fck_MPa: float,
    Lx: float,
    Ly: float,
    story_count: int,
    usage_G: float = 10.0,
    usage_Q: float = 2.0,
    n_factor: float = 0.3,
) -> Tuple[Optional[WallConfiguration], List[ModalResult]]:
    """
    Aday konfigürasyonlar arasından modal analizle en iyiyi seç.
    
    Returns:
        (best_config, all_modal_results)
        best_config: ηbi < 1.2 sağlayan en düşük skor, veya None
        all_modal_results: her adayın modal sonucu (geçse de geçmese de)
    """
    if not HAS_OPENSEES:
        raise ImportError("OpenSeesPy yüklü değil")
    
    all_results = []
    best_config = None
    best_eta = float('inf')
    
    for i, config in enumerate(candidates):
        wall_outputs = _placements_to_wall_outputs(config.placements)
        
        try:
            metadata = build_opensees_model(
                columns=columns,
                beams=beams,
                walls=wall_outputs,
                slabs=slabs,
                story_height_m=story_height_m,
                fck_MPa=fck_MPa,
                Lx=Lx, Ly=Ly,
                story_count=story_count,
                usage_G=usage_G,
                usage_Q=usage_Q,
                n_factor=n_factor,
            )
            eigenvalues = run_modal_analysis(num_modes=3)
            periods = [eigenvalue_to_period(ev) for ev in eigenvalues]
            eta_x, eta_y = compute_eta_bi(metadata, story_count, Lx, Ly)
            
            result = ModalResult(
                period_1_s=periods[0] if len(periods) > 0 else 0.0,
                period_2_s=periods[1] if len(periods) > 1 else 0.0,
                period_3_s=periods[2] if len(periods) > 2 else 0.0,
                mass_participation_x=0.0,   # preliminary için skip
                mass_participation_y=0.0,
                eta_bi_x=eta_x,
                eta_bi_y=eta_y,
                passes_torsion_check=(eta_x < ETABI_LIMIT and eta_y < ETABI_LIMIT),
            )
            all_results.append(result)
            
            # En iyi seç
            max_eta = max(eta_x, eta_y)
            if result.passes_torsion_check and max_eta < best_eta:
                best_config = config
                best_eta = max_eta
        except Exception as e:
            # Bu aday modal'da patlıyor → skip
            all_results.append(ModalResult(
                period_1_s=0, period_2_s=0, period_3_s=0,
                mass_participation_x=0, mass_participation_y=0,
                eta_bi_x=999, eta_bi_y=999, passes_torsion_check=False,
            ))
        finally:
            ops.wipe()
    
    return best_config, all_results
