import json
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from fact_checker.models.response import Classification
from fact_checker.retriever import SearchResult
from fact_checker.verifier import Verifier, VerificationResult


def make_client_returning(payload: dict) -> AsyncMock:
    client = AsyncMock(spec=anthropic.AsyncAnthropic)
    text_block = MagicMock()
    text_block.text = json.dumps(payload)
    mock_response = MagicMock()
    mock_response.content = [text_block]
    client.messages = AsyncMock()
    client.messages.create = AsyncMock(return_value=mock_response)
    return client


def make_verifier(client: AsyncMock) -> Verifier:
    return Verifier(client=client, model="claude-sonnet-4-6")


def _base_payload(**overrides) -> dict:
    base = {
        "classification": "true",
        "explanation": "Evidence supports the claim.",
        "supporting_urls": ["https://www.nih.gov/vaccine-history"],
        "contradicting_urls": [],
        "misinformation_patterns": [],
        "emotional_language_detected": False,
        "is_outdated": False,
        "source_agreement_count": 2,
        "source_disagreement_count": 0,
    }
    base.update(overrides)
    return base


SAMPLE_EVIDENCE = [
    SearchResult(
        title="NIH Vaccine History",
        url="https://www.nih.gov/vaccine-history",
        content="Both mRNA vaccines received EUA from the FDA in December 2020.",
        published_date="2021-01-05",
    ),
    SearchResult(
        title="CDC Guidance",
        url="https://www.cdc.gov/covid-vaccines",
        content="CDC issued guidance on COVID-19 vaccines following FDA authorization.",
        published_date="2021-02-01",
    ),
]


class TestVerifier:
    async def test_returns_true_classification(self):
        client = make_client_returning(_base_payload(classification="true"))
        verifier = make_verifier(client)

        result = await verifier.verify("COVID vaccines authorized in 2020.", SAMPLE_EVIDENCE)

        assert result.classification == Classification.TRUE

    async def test_returns_false_classification(self):
        client = make_client_returning(_base_payload(classification="false", supporting_urls=[]))
        verifier = make_verifier(client)

        result = await verifier.verify("Claim contradicted by evidence.", SAMPLE_EVIDENCE)

        assert result.classification == Classification.FALSE

    async def test_returns_misleading_classification(self):
        client = make_client_returning(_base_payload(classification="misleading"))
        verifier = make_verifier(client)

        result = await verifier.verify("Partially true but misleading.", SAMPLE_EVIDENCE)

        assert result.classification == Classification.MISLEADING

    async def test_returns_unverifiable_classification(self):
        client = make_client_returning(
            _base_payload(classification="unverifiable", supporting_urls=[])
        )
        verifier = make_verifier(client)

        result = await verifier.verify("Unknown claim.", SAMPLE_EVIDENCE)

        assert result.classification == Classification.UNVERIFIABLE

    async def test_url_hallucination_guard_strips_fake_urls(self):
        payload = _base_payload(
            supporting_urls=[
                "https://www.nih.gov/vaccine-history",     # real - in evidence
                "https://www.fake-invented-url.com/page",  # hallucinated - NOT in evidence
            ]
        )
        client = make_client_returning(payload)
        verifier = make_verifier(client)

        result = await verifier.verify("Some claim.", SAMPLE_EVIDENCE)

        assert "https://www.fake-invented-url.com/page" not in result.supporting_urls
        assert "https://www.nih.gov/vaccine-history" in result.supporting_urls

    async def test_all_hallucinated_urls_stripped(self):
        payload = _base_payload(
            supporting_urls=["https://completely.made.up/source"],
            contradicting_urls=["https://another.fake/source"],
        )
        client = make_client_returning(payload)
        verifier = make_verifier(client)

        result = await verifier.verify("Some claim.", SAMPLE_EVIDENCE)

        assert result.supporting_urls == []
        assert result.contradicting_urls == []

    async def test_misinformation_patterns_preserved(self):
        payload = _base_payload(
            classification="misleading",
            misinformation_patterns=["cherry_picking", "missing_context"],
        )
        client = make_client_returning(payload)
        verifier = make_verifier(client)

        result = await verifier.verify("Misleading claim.", SAMPLE_EVIDENCE)

        assert "cherry_picking" in result.misinformation_patterns
        assert "missing_context" in result.misinformation_patterns

    async def test_invalid_pattern_labels_filtered(self):
        payload = _base_payload(
            misinformation_patterns=["cherry_picking", "not_a_real_pattern", "false_equivalence"],
        )
        client = make_client_returning(payload)
        verifier = make_verifier(client)

        result = await verifier.verify("Claim.", SAMPLE_EVIDENCE)

        assert "not_a_real_pattern" not in result.misinformation_patterns
        assert "cherry_picking" in result.misinformation_patterns

    async def test_emotional_language_flag_propagated(self):
        client = make_client_returning(_base_payload(emotional_language_detected=True))
        verifier = make_verifier(client)

        result = await verifier.verify("SHOCKING claim!", SAMPLE_EVIDENCE)

        assert result.emotional_language_detected is True

    async def test_is_outdated_flag_propagated(self):
        client = make_client_returning(_base_payload(is_outdated=True))
        verifier = make_verifier(client)

        result = await verifier.verify("Claim with old data.", SAMPLE_EVIDENCE)

        assert result.is_outdated is True

    async def test_raises_on_invalid_json(self):
        client = make_client_returning.__wrapped__ if hasattr(make_client_returning, "__wrapped__") else None
        bad_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        text_block = MagicMock()
        text_block.text = "not valid json"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        bad_client.messages = AsyncMock()
        bad_client.messages.create = AsyncMock(return_value=mock_response)
        verifier = make_verifier(bad_client)

        with pytest.raises(ValueError, match="invalid JSON"):
            await verifier.verify("Some claim.", SAMPLE_EVIDENCE)

    async def test_raises_on_invalid_classification(self):
        bad_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        text_block = MagicMock()
        text_block.text = json.dumps({**_base_payload(), "classification": "unknown_value"})
        mock_response = MagicMock()
        mock_response.content = [text_block]
        bad_client.messages = AsyncMock()
        bad_client.messages.create = AsyncMock(return_value=mock_response)
        verifier = make_verifier(bad_client)

        with pytest.raises(ValueError, match="Invalid classification"):
            await verifier.verify("Some claim.", SAMPLE_EVIDENCE)

    async def test_empty_evidence_returns_unverifiable_without_llm_call(self):
        client = AsyncMock(spec=anthropic.AsyncAnthropic)
        client.messages = AsyncMock()
        client.messages.create = AsyncMock()
        verifier = make_verifier(client)

        result = await verifier.verify("Some claim.", evidence=[])

        assert result.classification == Classification.UNVERIFIABLE
        client.messages.create.assert_not_called()

    async def test_cache_control_in_system_prompt(self):
        client = make_client_returning(_base_payload())
        verifier = make_verifier(client)

        await verifier.verify("Some claim.", SAMPLE_EVIDENCE)

        call_kwargs = client.messages.create.call_args.kwargs
        system = call_kwargs["system"]
        assert system[0]["cache_control"] == {"type": "ephemeral"}

    async def test_pt_br_language_hint_in_message(self):
        client = make_client_returning(_base_payload())
        verifier = make_verifier(client)

        await verifier.verify("Uma afirmação.", SAMPLE_EVIDENCE, language="pt-BR")

        call_kwargs = client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "pt-BR" in user_content or "português" in user_content
