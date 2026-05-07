from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import anthropic
import httpx
import respx

from fact_checker.models import Classification, FactCheckRequest
from fact_checker.pipeline import build_pipeline


def _resp(text: str) -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _scripted_anthropic(extracted: list[str], verdict: dict[str, Any]) -> AsyncMock:
    """Mock Anthropic client: first call → extraction, rest → verification verdict."""
    client = AsyncMock(spec=anthropic.AsyncAnthropic)
    client.messages = AsyncMock()
    counter = {"n": 0}

    async def side(**_: Any) -> MagicMock:
        counter["n"] += 1
        if counter["n"] == 1:
            return _resp(json.dumps(extracted))
        return _resp(json.dumps(verdict))

    client.messages.create = AsyncMock(side_effect=side)
    return client


def _tavily_response(url: str = "https://www.nih.gov/p") -> dict[str, Any]:
    return {
        "results": [
            {
                "title": "NIH",
                "url": url,
                "content": "Relevant excerpt.",
                "published_date": "2024-06-01",
            }
        ]
    }


def _verdict(url: str, **overrides: Any) -> dict[str, Any]:
    base = {
        "classification": "true",
        "explanation": "Supported by evidence.",
        "supporting_urls": [url],
        "contradicting_urls": [],
        "misinformation_patterns": [],
        "emotional_language_detected": False,
        "is_outdated": False,
        "source_agreement_count": 1,
        "source_disagreement_count": 0,
    }
    base.update(overrides)
    return base


class TestPipeline:
    @respx.mock
    async def test_happy_path(self):
        url = "https://www.nih.gov/p"
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=_tavily_response(url))
        )

        async with httpx.AsyncClient() as http:
            anthropic_client = _scripted_anthropic(["FDA approved Pfizer in Dec 2020."], _verdict(url))
            pipeline = build_pipeline(anthropic_client, http)
            result = await pipeline.run(
                FactCheckRequest(text="FDA approved Pfizer vaccine in December 2020.")
            )

        assert len(result.claims) == 1
        assert result.claims[0].classification == Classification.TRUE
        assert "HIGH" in result.overall_assessment

    @respx.mock
    async def test_no_evidence_yields_unverifiable(self):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        async with httpx.AsyncClient() as http:
            anthropic_client = _scripted_anthropic(
                ["A claim."],
                _verdict("ignored", classification="unverifiable", supporting_urls=[]),
            )
            pipeline = build_pipeline(anthropic_client, http)
            result = await pipeline.run(FactCheckRequest(text="A claim about something."))

        assert result.claims[0].classification == Classification.UNVERIFIABLE

    @respx.mock
    async def test_misinformation_patterns_aggregated(self):
        url = "https://www.nih.gov/p"
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=_tavily_response(url))
        )
        verdict = _verdict(
            url,
            classification="misleading",
            misinformation_patterns=["cherry_picking", "missing_context"],
        )

        async with httpx.AsyncClient() as http:
            client = _scripted_anthropic(["A misleading claim."], verdict)
            pipeline = build_pipeline(client, http)
            result = await pipeline.run(FactCheckRequest(text="A misleading claim about X."))

        assert "cherry_picking" in result.misinformation_patterns
        assert "missing_context" in result.misinformation_patterns

    @respx.mock
    async def test_emotional_flag_aggregated(self):
        url = "https://www.nih.gov/p"
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=_tavily_response(url))
        )
        verdict = _verdict(url, emotional_language_detected=True)

        async with httpx.AsyncClient() as http:
            client = _scripted_anthropic(["SHOCKING claim."], verdict)
            pipeline = build_pipeline(client, http)
            result = await pipeline.run(FactCheckRequest(text="SHOCKING dangerous claim!"))

        assert result.emotional_manipulation_detected is True

    @respx.mock
    async def test_no_claims_extracted(self):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        async with httpx.AsyncClient() as http:
            client = _scripted_anthropic([], _verdict("ignored"))
            pipeline = build_pipeline(client, http)
            result = await pipeline.run(
                FactCheckRequest(text="Pure opinion with no verifiable facts at all.")
            )

        assert result.claims == []
        assert "No verifiable claims" in result.overall_assessment
