from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas import PipelineRunResult
from app.services import pipeline as pipeline_service
from app.storage import run_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class RunPipelineRequest(BaseModel):
    target_count: int = 2
    max_candidates: int = 5


class RunPipelineResponse(BaseModel):
    run_id: str
    result: PipelineRunResult


@router.post("/run", response_model=RunPipelineResponse)
async def run_pipeline(payload: RunPipelineRequest) -> RunPipelineResponse:
    try:
        result = await pipeline_service.run_pipeline(
            target_count=payload.target_count,
            max_candidates=payload.max_candidates,
        )
    except Exception as exc:
        logger.exception("Pipeline run failed")
        raise HTTPException(status_code=502, detail=f"Pipeline run failed: {exc}") from exc
    run_id = run_store.create(result)
    return RunPipelineResponse(run_id=run_id, result=result)


@router.get("/run/{run_id}", response_model=RunPipelineResponse)
async def get_pipeline_run(run_id: str) -> RunPipelineResponse:
    result = run_store.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunPipelineResponse(run_id=run_id, result=result)
