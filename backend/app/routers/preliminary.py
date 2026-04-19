"""
Preliminary Design Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.preliminary.schemas import PreliminaryInput, PreliminaryOutput
from app.preliminary.orchestrator import run_preliminary_design
from app.preliminary.viewer_adapter import preliminary_to_elements, preliminary_to_stories

router = APIRouter(prefix="/preliminary", tags=["preliminary"])


class DesignWithViewerResponse(BaseModel):
    design: PreliminaryOutput
    elements: List[Dict[str, Any]]
    stories: List[str]


@router.post("/design", response_model=DesignWithViewerResponse)
async def design(input_data: PreliminaryInput) -> DesignWithViewerResponse:
    try:
        result = run_preliminary_design(input_data)
        return DesignWithViewerResponse(
            design=result,
            elements=preliminary_to_elements(result),
            stories=preliminary_to_stories(result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline hatası: {str(e)}")


@router.post("/design-fast", response_model=DesignWithViewerResponse)
async def design_fast(input_data: PreliminaryInput) -> DesignWithViewerResponse:
    try:
        result = run_preliminary_design(input_data, skip_modal=True)
        return DesignWithViewerResponse(
            design=result,
            elements=preliminary_to_elements(result),
            stories=preliminary_to_stories(result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline hatası: {str(e)}")