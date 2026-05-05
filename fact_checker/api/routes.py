from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from fact_checker.api.dependencies import get_pipeline
from fact_checker.config import settings
from fact_checker.models.request import FactCheckRequest
from fact_checker.models.response import FactCheckResponse
from fact_checker.pipeline import FactCheckPipeline

router = APIRouter()


@router.post("/check", response_model=FactCheckResponse, status_code=200)
async def check_facts(
    request: FactCheckRequest,
    pipeline: FactCheckPipeline = Depends(get_pipeline),
) -> FactCheckResponse:
    return await pipeline.run(request)


@router.get("/health", status_code=200)
async def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.default_model}


@router.get("/models", status_code=200)
async def list_models() -> dict[str, list[str]]:
    return {
        "llm_models": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
        "retrievers": ["tavily"],
    }
