"""
Pydantic schemas for preliminary design input and output.
"""
from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, validator


# ==========================================================
# ENUMS
# ==========================================================

class SoilClass(str, Enum):
    ZA = "ZA"
    ZB = "ZB"
    ZC = "ZC"
    ZD = "ZD"
    ZE = "ZE"


class UsageType(str, Enum):
    RESIDENTIAL = "residential"
    STORAGE = "storage"


# NOT: Döşeme tipi her zaman ASMOLEN (nervürlü).
# Kullanıcıya seçtirilmez, proje kararı gereği sabit.


class ElementType(str, Enum):
    COLUMN = "column"
    BEAM = "beam"
    WALL = "wall"
    SLAB = "slab"


# ==========================================================
# INPUT
# ==========================================================

class MaterialInput(BaseModel):
    fck: Optional[float] = Field(None, ge=25.0, description="Boş bırakılırsa otomatik seçim")
    fyk: Optional[float] = Field(None, ge=400.0, description="Boş bırakılırsa otomatik seçim")


class LocationInput(BaseModel):
    il: str = Field(..., description="İl adı (örn: 'İstanbul')")
    ilce: str = Field(..., description="İlçe adı (örn: 'Kadıköy')")


class CoreInput(BaseModel):
    """Çekirdek. required=True → otomatik yerleştirilir, boyut kat sayısına göre."""
    required: bool = False
    width_m_override: Optional[float] = Field(None, ge=2.0, le=6.0)
    length_m_override: Optional[float] = Field(None, ge=2.0, le=8.0)


class PreliminaryInput(BaseModel):
    # Geometri
    Lx: float = Field(..., ge=8.0, le=60.0, description="Plan X boyutu (m)")
    Ly: float = Field(..., ge=8.0, le=60.0, description="Plan Y boyutu (m)")
    story_count: int = Field(..., ge=1, le=30)
    story_height_m: float = Field(3.0, ge=2.5, le=5.0)

    # Konum & zemin
    location: LocationInput
    soil_class: SoilClass

    # Kullanım
    usage: UsageType

    # Malzeme (None → tamamen otomatik)
    material: Optional[MaterialInput] = None

    # Çekirdek
    core: CoreInput = CoreInput()


# ==========================================================
# OUTPUT — GEOMETRİ
# ==========================================================

class AxisGrid(BaseModel):
    """Aks sistemi — X ve Y yönündeki aks koordinatları."""
    x_axes: List[float]  # X aksları (m), örn [0, 6, 12, 18]
    y_axes: List[float]  # Y aksları (m)
    x_labels: List[str]  # ["1", "2", "3", "4"]
    y_labels: List[str]  # ["A", "B", "C"]


class ColumnOutput(BaseModel):
    id: str
    x: float           # aks koordinatı m
    y: float
    story: int         # 1 = zemin
    width_cm: float    # b (X yönü)
    depth_cm: float    # h (Y yönü)
    axial_load_kN: float
    axis_label: str    # "1-A" gibi


class BeamOutput(BaseModel):
    id: str
    start: Tuple[float, float]   # (x, y) başlangıç
    end: Tuple[float, float]     # (x, y) bitiş
    story: int
    width_cm: float              # bw
    height_cm: float             # h
    span_m: float
    direction: str               # "X" | "Y"


class WallOutput(BaseModel):
    id: str
    center: Tuple[float, float]
    length_m: float              # lw
    thickness_cm: float          # bw
    orientation: str             # "X" | "Y"
    story_range: Tuple[int, int] # (1, 10) = 1'den 10'a


class SlabOutput(BaseModel):
    story: int
    # Her zaman asmolen (nervürlü).
    total_thickness_cm: float
    rib_width_cm: float
    rib_spacing_cm: float        # dişler arası net açıklık (e)
    top_flange_cm: float         # üst plak hf
    rib_direction: str           # "X" | "Y"
    transverse_rib_count: int    # enine dağıtıcı nervür sayısı (0/1/2)


class CoreOutput(BaseModel):
    center: Tuple[float, float]
    width_m: float
    length_m: float
    wall_thickness_cm: float
    opening_direction: str
    walls: List["WallOutput"] = []
    removed_column_ids: List[str] = []


# ==========================================================
# OUTPUT — ANALİZ SONUÇLARI
# ==========================================================

class ModalResult(BaseModel):
    period_1_s: float          # T1
    period_2_s: float
    period_3_s: float
    mass_participation_x: float
    mass_participation_y: float
    eta_bi_x: float            # burulma düzensizliği X
    eta_bi_y: float            # burulma düzensizliği Y
    passes_torsion_check: bool # ηbi < 1.2


class DesignWarning(BaseModel):
    severity: str              # "info" | "warning" | "error"
    rule: str                  # "TBDY 7.3.1.2" gibi
    message: str
    element_id: Optional[str] = None


# ==========================================================
# FİNAL OUTPUT
# ==========================================================

class PreliminaryOutput(BaseModel):
    # Input echo
    input: PreliminaryInput

    # Geometri
    grid: AxisGrid
    columns: List[ColumnOutput]
    beams: List[BeamOutput]
    walls: List[WallOutput]
    slabs: List[SlabOutput]
    core: Optional[CoreOutput] = None

    # Toplam değerler
    total_concrete_volume_m3: float
    total_wall_area_ratio_x: float   # ΣAwall_x / Afloor
    total_wall_area_ratio_y: float

    # Analiz
    modal_result: Optional[ModalResult] = None

    # Uyarılar
    warnings: List[DesignWarning] = []

    # Meta
    design_iterations: int = 1        # kaç kez yeniden tasarlandı
    success: bool = True
