from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from fact_checker.models.response import Classification
from fact_checker.retriever import SearchResult
from fact_checker.verifier import VerificationResult


@pytest.fixture
def sample_claim() -> str:
    return "The COVID-19 mRNA vaccines were authorized by the FDA in December 2020."


@pytest.fixture
def sample_claim_pt() -> str:
    return "O PIB do Brasil em 2023 foi de R$10,9 trilhões."


@pytest.fixture
def sample_evidence() -> list[SearchResult]:
    return [
        SearchResult(
            title="FDA Authorizes COVID-19 Vaccines",
            url="https://www.fda.gov/emergency-use-authorization-vaccines",
            content="The FDA issued emergency use authorization for the Pfizer-BioNTech COVID-19 vaccine in December 2020.",
            published_date="2020-12-11",
            raw_score=0.95,
        ),
        SearchResult(
            title="COVID-19 Vaccine Authorization Timeline",
            url="https://www.cdc.gov/covid19-vaccine-authorization",
            content="Emergency use authorization was granted for the Moderna vaccine on December 18, 2020.",
            published_date="2020-12-18",
            raw_score=0.90,
        ),
        SearchResult(
            title="Vaccine Development History",
            url="https://www.nih.gov/vaccine-history",
            content="Both mRNA vaccines received EUA from the FDA within weeks of each other in December 2020.",
            published_date="2021-01-05",
            raw_score=0.85,
        ),
    ]


@pytest.fixture
def sample_verification_true(sample_evidence: list[SearchResult]) -> VerificationResult:
    return VerificationResult(
        classification=Classification.TRUE,
        explanation="Multiple authoritative sources confirm the FDA authorized mRNA vaccines in December 2020.",
        supporting_urls=[e.url for e in sample_evidence],
        contradicting_urls=[],
        misinformation_patterns=[],
        emotional_language_detected=False,
        is_outdated=False,
        source_agreement_count=3,
        source_disagreement_count=0,
    )


@pytest.fixture
def sample_verification_false() -> VerificationResult:
    return VerificationResult(
        classification=Classification.FALSE,
        explanation="Evidence contradicts this claim.",
        supporting_urls=[],
        contradicting_urls=["https://www.nih.gov/vaccine-history"],
        misinformation_patterns=[],
        emotional_language_detected=False,
        is_outdated=False,
        source_agreement_count=0,
        source_disagreement_count=2,
    )


@pytest.fixture
def sample_verification_unverifiable() -> VerificationResult:
    return VerificationResult(
        classification=Classification.UNVERIFIABLE,
        explanation="No sufficient evidence was found.",
        supporting_urls=[],
        contradicting_urls=[],
        misinformation_patterns=[],
        emotional_language_detected=False,
        is_outdated=False,
        source_agreement_count=0,
        source_disagreement_count=0,
    )


@pytest.fixture
def mock_anthropic_response_factory():
    """Factory for creating mock Anthropic message responses."""

    def _make(content: str) -> MagicMock:
        response = MagicMock(spec=anthropic.types.Message)
        text_block = MagicMock()
        text_block.text = content
        response.content = [text_block]
        return response

    return _make


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response_factory) -> AsyncMock:
    client = AsyncMock(spec=anthropic.AsyncAnthropic)
    client.messages = AsyncMock()
    client.messages.create = AsyncMock(
        return_value=mock_anthropic_response_factory('["Sample factual claim."]')
    )
    return client


@pytest.fixture
def mock_tavily_response() -> dict:
    return {
        "results": [
            {
                "title": "FDA Authorizes COVID-19 Vaccines",
                "url": "https://www.fda.gov/emergency-use-authorization-vaccines",
                "content": "The FDA issued emergency use authorization in December 2020.",
                "published_date": "2020-12-11",
                "score": 0.95,
            },
            {
                "title": "CDC Vaccine Guidance",
                "url": "https://www.cdc.gov/covid19-vaccine-authorization",
                "content": "CDC guidance on the COVID-19 vaccination program.",
                "published_date": "2021-01-01",
                "score": 0.88,
            },
        ]
    }
