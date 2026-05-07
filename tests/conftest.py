from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from fact_checker.models import SearchResult


def _build_response(text: str) -> MagicMock:
    """Create a fake anthropic.types.Message-shaped object."""
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


@pytest.fixture
def make_anthropic():
    """Factory: returns a mocked AsyncAnthropic client whose .messages.create
    yields the given JSON-serializable values, one per call."""

    def _factory(*responses: Any) -> AsyncMock:
        client = AsyncMock(spec=anthropic.AsyncAnthropic)
        client.messages = AsyncMock()
        texts = [json.dumps(r) if not isinstance(r, str) else r for r in responses]
        if len(texts) == 1:
            client.messages.create = AsyncMock(return_value=_build_response(texts[0]))
        else:
            iter_texts = iter(texts)
            async def side(**_: Any) -> MagicMock:
                return _build_response(next(iter_texts))
            client.messages.create = AsyncMock(side_effect=side)
        return client

    return _factory


@pytest.fixture
def sample_evidence() -> list[SearchResult]:
    return [
        SearchResult(
            title="FDA grants EUA for Pfizer-BioNTech vaccine",
            url="https://www.fda.gov/news-events/press-announcements/fda-pfizer",
            content="The FDA issued an Emergency Use Authorization for the Pfizer-BioNTech COVID-19 vaccine on December 11, 2020.",
            published_date="2020-12-11",
        ),
        SearchResult(
            title="CDC: COVID-19 mRNA vaccines",
            url="https://www.cdc.gov/coronavirus/2019-ncov/vaccines/different-vaccines/mrna.html",
            content="Both the Pfizer-BioNTech and Moderna mRNA vaccines were authorized in December 2020.",
            published_date="2021-01-05",
        ),
        SearchResult(
            title="NIH overview of COVID-19 vaccine timelines",
            url="https://www.nih.gov/coronavirus/timeline",
            content="Authorization timelines for COVID-19 vaccines, including Pfizer (Dec 11) and Moderna (Dec 18).",
            published_date="2021-02-01",
        ),
    ]


@pytest.fixture
def verifier_payload():
    """Factory for constructing verifier-shaped JSON payloads."""

    def _make(**overrides: Any) -> dict[str, Any]:
        base = {
            "classification": "true",
            "explanation": "Multiple authoritative sources confirm the claim.",
            "supporting_urls": [],
            "contradicting_urls": [],
            "misinformation_patterns": [],
            "emotional_language_detected": False,
            "is_outdated": False,
            "source_agreement_count": 2,
            "source_disagreement_count": 0,
        }
        base.update(overrides)
        return base

    return _make
