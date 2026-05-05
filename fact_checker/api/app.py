from contextlib import asynccontextmanager
from typing import AsyncGenerator

import anthropic
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fact_checker.api.routes import router
from fact_checker.config import settings
from fact_checker.pipeline import build_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    http_client = httpx.AsyncClient(timeout=settings.retriever_timeout_seconds)
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    app.state.pipeline = build_pipeline(
        anthropic_client=anthropic_client,
        http_client=http_client,
    )
    try:
        yield
    finally:
        await http_client.aclose()
        await anthropic_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fact Checker API",
        description="RAG-based fact-checking using Claude and Tavily",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    @app.exception_handler(httpx.TimeoutException)
    async def timeout_handler(request: Request, exc: httpx.TimeoutException) -> JSONResponse:
        return JSONResponse(status_code=504, content={"detail": "retriever_timeout"})

    @app.exception_handler(anthropic.APIError)
    async def anthropic_error_handler(request: Request, exc: anthropic.APIError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": "llm_error", "message": str(exc)},
        )

    return app


app = create_app()
