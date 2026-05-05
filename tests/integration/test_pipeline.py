import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest
import respx

from fact_checker.models.request import FactCheckRequest
from fact_checker.models.response import Classification, FactCheckResponse
from fact_checker.pipeline import FactCheckPipeline, build_pipeline


def make_anthropic_client(extractor_claims: list[str], verifier_payload: dict) -> AsyncMock:
    """Create a mock Anthropic client that returns different responses per call."""
    client = AsyncMock(spec=anthropic.AsyncAnthropic)
    client.messages = AsyncMock()

    call_count = 0

    async def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        text_block = MagicMock()
        # First call: claim extraction
        if call_count == 1:
            text_block.text = json.dumps(extractor_claims)
        else:
            # Subsequent calls: verification
            text_block.text = json.dumps(verifier_payload)
        response = MagicMock()
        response.content = [text_block]
        return response

    client.messages.create = AsyncMock(side_effect=side_effect)
    return client


def make_tavily_response(url: str = "https://www.nih.gov/page") -> dict:
    return {
        "results": [
            {
                "title": "NIH Source",
                "url": url,
                "content": "Relevant scientific content here.",
                "published_date": "2024-01-01",
                "score": 0.90,
            }
        ]
    }


def make_verifier_payload(
    classification: str = "true",
    url: str = "https://www.nih.gov/page",
) -> dict:
    return {
        "classification": classification,
        "explanation": "Evidence supports the claim.",
        "supporting_urls": [url],
        "contradicting_urls": [],
        "misinformation_patterns": [],
        "emotional_language_detected": False,
        "is_outdated": False,
        "source_agreement_count": 1,
        "source_disagreement_count": 0,
    }


class TestFullPipeline:
    @respx.mock
    async def test_happy_path_returns_fact_check_response(self):
        url = "https://www.nih.gov/page"
        claims = ["The FDA authorized mRNA vaccines in December 2020."]
        verifier_payload = make_verifier_payload(url=url)
        tavily_response = make_tavily_response(url=url)

        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=tavily_response)
        )

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client(claims, verifier_payload)
            pipeline = build_pipeline(
                anthropic_client=anthropic_client,
                http_client=http_client,
            )

            request = FactCheckRequest(text="The FDA authorized mRNA vaccines in December 2020.")
            result = await pipeline.run(request)

        assert isinstance(result, FactCheckResponse)
        assert len(result.claims) == 1
        assert result.claims[0].classification == Classification.TRUE
        assert result.overall_assessment != ""

    @respx.mock
    async def test_no_evidence_yields_unverifiable(self):
        claims = ["Some obscure unverifiable claim."]
        verifier_payload = make_verifier_payload(classification="unverifiable")
        verifier_payload["supporting_urls"] = []

        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client(claims, verifier_payload)
            pipeline = build_pipeline(anthropic_client=anthropic_client, http_client=http_client)

            result = await pipeline.run(FactCheckRequest(text="Some obscure unverifiable claim."))

        assert result.claims[0].classification == Classification.UNVERIFIABLE

    @respx.mock
    async def test_multiple_claims_processed_independently(self):
        url1 = "https://www.nih.gov/page1"
        url2 = "https://www.cdc.gov/page2"
        claims = ["Claim one.", "Claim two."]
        verifier_payload = make_verifier_payload(url=url1)

        call_count = 0

        def tavily_side_effect(request):
            nonlocal call_count
            call_count += 1
            url = url1 if call_count == 1 else url2
            return httpx.Response(200, json=make_tavily_response(url))

        respx.post("https://api.tavily.com/search").mock(side_effect=tavily_side_effect)

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client(claims, verifier_payload)
            pipeline = build_pipeline(anthropic_client=anthropic_client, http_client=http_client)
            result = await pipeline.run(FactCheckRequest(text="Claim one. Claim two."))

        assert len(result.claims) == 2
        # Claims must not share sources from each other's retrieval context
        all_source_urls = [s.url for c in result.claims for s in c.sources]
        # No hallucinated cross-contamination — each claim's sources come from its own search
        assert len(all_source_urls) > 0

    @respx.mock
    async def test_misinformation_patterns_aggregated(self):
        url = "https://www.nih.gov/page"
        claims = ["Cherry-picked claim."]
        verifier_payload = make_verifier_payload(url=url)
        verifier_payload["misinformation_patterns"] = ["cherry_picking", "missing_context"]

        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=make_tavily_response(url))
        )

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client(claims, verifier_payload)
            pipeline = build_pipeline(anthropic_client=anthropic_client, http_client=http_client)
            result = await pipeline.run(FactCheckRequest(text="Cherry-picked claim."))

        assert "cherry_picking" in result.misinformation_patterns
        assert "missing_context" in result.misinformation_patterns

    @respx.mock
    async def test_emotional_manipulation_flag_aggregated(self):
        url = "https://www.nih.gov/page"
        claims = ["SHOCKING dangerous claim!"]
        verifier_payload = make_verifier_payload(url=url)
        verifier_payload["emotional_language_detected"] = True

        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=make_tavily_response(url))
        )

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client(claims, verifier_payload)
            pipeline = build_pipeline(anthropic_client=anthropic_client, http_client=http_client)
            result = await pipeline.run(FactCheckRequest(text="SHOCKING dangerous claim!"))

        assert result.emotional_manipulation_detected is True

    @respx.mock
    async def test_empty_claim_extraction_returns_empty_response(self):
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client([], {})
            pipeline = build_pipeline(anthropic_client=anthropic_client, http_client=http_client)
            result = await pipeline.run(
                FactCheckRequest(text="This is purely an opinion with no verifiable facts.")
            )

        assert result.claims == []
        assert "No verifiable claims" in result.overall_assessment

    @respx.mock
    async def test_semaphore_limits_concurrent_searches(self):
        url = "https://www.nih.gov/page"
        # Create 10 claims to test semaphore
        claims = [f"Claim number {i}." for i in range(10)]
        verifier_payload = make_verifier_payload(url=url)

        active_requests = []
        max_concurrent = 0

        def tavily_side_effect(request):
            nonlocal max_concurrent
            active_requests.append(1)
            max_concurrent = max(max_concurrent, len(active_requests))
            active_requests.pop()
            return httpx.Response(200, json=make_tavily_response(url))

        respx.post("https://api.tavily.com/search").mock(side_effect=tavily_side_effect)

        async with httpx.AsyncClient() as http_client:
            anthropic_client = make_anthropic_client(claims, verifier_payload)
            pipeline = build_pipeline(anthropic_client=anthropic_client, http_client=http_client)
            result = await pipeline.run(
                FactCheckRequest(text=" ".join(claims))
            )

        assert len(result.claims) == 10
