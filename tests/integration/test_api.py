from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from fact_checker.api.app import create_app
from fact_checker.api.dependencies import get_pipeline
from fact_checker.models.response import (
    Claim,
    Classification,
    FactCheckResponse,
    Source,
)
from fact_checker.pipeline import FactCheckPipeline


def make_mock_pipeline(response: FactCheckResponse) -> AsyncMock:
    pipeline = AsyncMock(spec=FactCheckPipeline)
    pipeline.run = AsyncMock(return_value=response)
    return pipeline


SAMPLE_RESPONSE = FactCheckResponse(
    claims=[
        Claim(
            claim="The FDA authorized mRNA vaccines in December 2020.",
            classification=Classification.TRUE,
            confidence_score=0.92,
            explanation="Multiple authoritative sources confirm this.",
            sources=[
                Source(
                    title="FDA Authorization",
                    url="https://www.fda.gov/vaccines",
                    credibility_score=0.95,
                )
            ],
        )
    ],
    overall_assessment="The text contains 1 verifiable claim(s): 1 true, 0 false, 0 misleading, and 0 unverifiable. Overall reliability appears HIGH.",
    misinformation_patterns=[],
    emotional_manipulation_detected=False,
)


@pytest.fixture
def app_with_mock_pipeline():
    app = create_app()
    mock_pipeline = make_mock_pipeline(SAMPLE_RESPONSE)
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
    return app, mock_pipeline


class TestFactCheckEndpoint:
    def test_post_check_valid_request_returns_200(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.post(
                "/check",
                json={"text": "The FDA authorized mRNA vaccines in December 2020."},
            )
        assert response.status_code == 200

    def test_post_check_response_has_correct_schema(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.post(
                "/check",
                json={"text": "The FDA authorized mRNA vaccines in December 2020."},
            )
        data = response.json()
        assert "claims" in data
        assert "overall_assessment" in data
        assert "misinformation_patterns" in data
        assert "emotional_manipulation_detected" in data

    def test_post_check_claim_has_all_fields(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.post(
                "/check",
                json={"text": "The FDA authorized mRNA vaccines in December 2020."},
            )
        claim = response.json()["claims"][0]
        assert "claim" in claim
        assert "classification" in claim
        assert "confidence_score" in claim
        assert "explanation" in claim
        assert "sources" in claim

    def test_post_check_missing_text_returns_422(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.post("/check", json={"context": "some context"})
        assert response.status_code == 422

    def test_post_check_text_too_short_returns_422(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.post("/check", json={"text": "Hi"})
        assert response.status_code == 422

    def test_post_check_with_language_and_context(self, app_with_mock_pipeline):
        app, mock_pipeline = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.post(
                "/check",
                json={
                    "text": "O PIB do Brasil em 2023 foi de R$10,9 trilhões segundo o IBGE.",
                    "context": "Dados econômicos do IBGE.",
                    "language": "pt-BR",
                },
            )
        assert response.status_code == 200
        call_args = mock_pipeline.run.call_args
        request_arg = call_args.args[0]
        assert request_arg.language == "pt-BR"
        assert request_arg.context == "Dados econômicos do IBGE."

    def test_post_check_pipeline_called_once(self, app_with_mock_pipeline):
        app, mock_pipeline = app_with_mock_pipeline
        with TestClient(app) as client:
            client.post(
                "/check",
                json={"text": "The FDA authorized mRNA vaccines in December 2020."},
            )
        mock_pipeline.run.assert_called_once()

    def test_post_check_retriever_timeout_returns_504(self):
        app = create_app()
        timeout_pipeline = AsyncMock(spec=FactCheckPipeline)
        timeout_pipeline.run = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        app.dependency_overrides[get_pipeline] = lambda: timeout_pipeline

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/check",
                json={"text": "The FDA authorized mRNA vaccines in December 2020."},
            )
        assert response.status_code == 504
        assert response.json()["detail"] == "retriever_timeout"


class TestHealthEndpoint:
    def test_health_returns_200(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_health_includes_model(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.get("/health")
        assert "model" in response.json()


class TestModelsEndpoint:
    def test_models_returns_200(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.get("/models")
        assert response.status_code == 200

    def test_models_lists_retrievers(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.get("/models")
        data = response.json()
        assert "retrievers" in data
        assert "tavily" in data["retrievers"]

    def test_models_lists_llm_models(self, app_with_mock_pipeline):
        app, _ = app_with_mock_pipeline
        with TestClient(app) as client:
            response = client.get("/models")
        data = response.json()
        assert "llm_models" in data
        assert len(data["llm_models"]) > 0
