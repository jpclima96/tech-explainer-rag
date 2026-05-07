"""FastAPI app — single file because the surface is small."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import anthropic
import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fact_checker.config import settings
from fact_checker.exceptions import LLMOutputError, RetrieverError
from fact_checker.models import FactCheckRequest, FactCheckResponse
from fact_checker.pipeline import FactCheckPipeline, build_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    http_client = httpx.AsyncClient(timeout=settings.retriever_timeout_seconds)
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    app.state.pipeline = build_pipeline(anthropic_client, http_client)
    try:
        yield
    finally:
        await http_client.aclose()
        await anthropic_client.close()


def get_pipeline(request: Request) -> FactCheckPipeline:
    return request.app.state.pipeline  # type: ignore[no-any-return]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fact Checker API",
        description="RAG-based fact-checking with Claude Opus and Tavily.",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS — open by default for the bundled local frontend.
    # Tighten via env in real deployments.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(httpx.TimeoutException)
    async def _timeout(_: Request, __: httpx.TimeoutException) -> JSONResponse:
        return JSONResponse(status_code=504, content={"detail": "retriever_timeout"})

    @app.exception_handler(RetrieverError)
    async def _retriever_err(_: Request, exc: RetrieverError) -> JSONResponse:
        return JSONResponse(
            status_code=502, content={"detail": "retriever_error", "message": str(exc)}
        )

    @app.exception_handler(anthropic.APIError)
    async def _anthropic_err(_: Request, exc: anthropic.APIError) -> JSONResponse:
        return JSONResponse(
            status_code=502, content={"detail": "llm_error", "message": str(exc)}
        )

    @app.exception_handler(LLMOutputError)
    async def _llm_output_err(_: Request, exc: LLMOutputError) -> JSONResponse:
        return JSONResponse(
            status_code=502, content={"detail": "llm_output_error", "message": str(exc)}
        )

    @app.post("/check", response_model=FactCheckResponse)
    async def check(
        request: FactCheckRequest,
        pipeline: FactCheckPipeline = Depends(get_pipeline),
    ) -> FactCheckResponse:
        return await pipeline.run(request)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "model": settings.default_model}

    @app.get("/models")
    async def models() -> dict[str, list[str]]:
        return {
            "llm_models": [
                "claude-opus-4-7",
                "claude-sonnet-4-6",
                "claude-haiku-4-5-20251001",
            ],
            "retrievers": ["tavily"],
        }

    return app


app = create_app()
