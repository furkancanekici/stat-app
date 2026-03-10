from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Status(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    FAIL = "FAIL"
    BRITTLE = "BRITTLE"
    UNMATCHED = "UNMATCHED"


class UnifiedElementData(BaseModel):
    # IFC tarafından gelir
    ifc_global_id: str
    ifc_name: Optional[str] = None
    ifc_tag: Optional[str] = None
    ifc_type: str
    ifc_story: Optional[str] = None

    # Excel tarafından gelir
    excel_label: Optional[str] = None
    unity_check: Optional[float] = None
    failure_mode: Optional[str] = None
    governing_combo: Optional[str] = None

    # Rule engine yazar
    status: Optional[Status] = None
    match_score: float = 0.0


class MatchResult(BaseModel):
    matched: int
    unmatched: int
    low_confidence: list[str] = []
    elements: list[UnifiedElementData] = []


class SummaryResult(BaseModel):
    total: int
    status_counts: dict[str, int]
    by_story: list[dict]
    unmatched_elements: list[str] = []