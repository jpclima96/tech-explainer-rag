from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from fact_checker.api import create_app, get_pipeline
from fact_checker.exceptions import RetrieverError
from fact_checker.models import (
    Claim,
    Classification,
    FactCheckResponse,
    Source,
)
from fact_checker.pipeline import FactCheckPipeline


SAMPLE_RESPONSE = FactCheckResponse(
    claims=[
        Claim(
            claim="The FDA approved Pfizer in December 2020.",
            classification=Classification.TRUE,
            confidence_score=0.92,
            explanation="Confirmed by NIH and FDA sources.",
            sources=[
                Source(
                    title="FDA",
                    url="https://www.fda.gov/x",
                    credibility_score=0.95,
                )
            ],
        )
    ],
    overall_assessment="Analyzed 1 verifiable claim(s): 1 true, 0 false. Overall reliability appears HIGH.",
    misinformation_patterns=[],
    emotional_manipulation_detected=False,
)


@pytest.fixture
def app_with_mock():
    app = create_app()
    pipeline = AsyncMock(spec=FactCheckPipeline)
    pipeline.run = AsyncMock(return_value=SAMPLE_RESPONSE)
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    return app, pipeline


class TestCheckEndpoint:
    def test_valid_request_returns_200(self, app_with_mock):
        app, _ = app_with_mock
        with TestClient(app) as c:
            res = c.post("/check", json={"text": "The FDA approved Pfizer in December 2020."})
        assert res.status_code == 200

    def test_response_schema(self, app_with_mock):
        app, _ = app_with_mock
        with TestClient(app) as c:
            res = c.post("/check", json={"text": "The FDA approved Pfizer in December 2020."})
        body = res.json()
        for key in ("claims", "overall_assessment", "misinformation_patterns", "emotional_manipulation_detected"):
            assert key in body
        for key in ("claim", "classification", "confidence_score", "explanation", "sources"):
            assert key in body["claims"][0]

    def test_missing_text_returns_422(self, app_with_mock):
        app, _ = app_with_mock
        with TestClient(app) as c:
            res = c.post("/check", json={})
        assert res.status_code == 422

    def test_text_too_short_returns_422(self, app_with_mock):
        app, _ = app_with_mock
        with TestClient(app) as c:
            res = c.post("/check", json={"text": "hi"})
        assert res.status_code == 422

    def test_pt_br_request_passes_through(self, app_with_mock):
        app, pipeline = app_with_mock
        with TestClient(app) as c:
            c.post(
                "/check",
                json={
                    "text": "O PIB do Brasil em 2023 foi de R$10,9 trilhões.",
                    "language": "pt-BR",
                    "context": "Dados do IBGE.",
                },
            )
        req = pipeline.run.call_args.args[0]
        assert req.language == "pt-BR"
        assert req.context == "Dados do IBGE."

    def test_retriever_timeout_returns_504(self):
        app = create_app()
        pipeline = AsyncMock(spec=FactCheckPipeline)
        pipeline.run = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        app.dependency_overrides[get_pipeline] = lambda: pipeline
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.post("/check", json={"text": "valid text content."})
        assert res.status_code == 504
        assert res.json()["detail"] == "retriever_timeout"

    def test_retriever_error_returns_502(self):
        app = create_app()
        pipeline = AsyncMock(spec=FactCheckPipeline)
        pipeline.run = AsyncMock(side_effect=RetrieverError("tavily failed"))
        app.dependency_overrides[get_pipeline] = lambda: pipeline
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.post("/check", json={"text": "valid text content."})
        assert res.status_code == 502
        assert res.json()["detail"] == "retriever_error"


class TestHealthEndpoint:
    def test_returns_ok(self, app_with_mock):
        app, _ = app_with_mock
        with TestClient(app) as c:
            res = c.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert "model" in res.json()


class TestModelsEndpoint:
    def test_lists_available_models(self, app_with_mock):
        app, _ = app_with_mock
        with TestClient(app) as c:
            res = c.get("/models")
        body = res.json()
        assert "claude-opus-4-7" in body["llm_models"]
        assert "tavily" in body["retrievers"]
