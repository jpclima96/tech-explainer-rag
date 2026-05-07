from __future__ import annotations

import pytest

from fact_checker.exceptions import LLMOutputError
from fact_checker.models import Classification, SearchResult
from fact_checker.verifier import Verifier


class TestVerifier:
    async def test_returns_each_classification(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        for value in ("true", "false", "misleading", "unverifiable"):
            client = make_anthropic(verifier_payload(classification=value))
            result = await Verifier(client).verify("claim", sample_evidence)
            assert result.classification == Classification(value)

    async def test_strips_hallucinated_supporting_urls(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        payload = verifier_payload(
            supporting_urls=[
                sample_evidence[0].url,            # real
                "https://made-up-url.example/foo",  # invented
            ]
        )
        client = make_anthropic(payload)
        result = await Verifier(client).verify("claim", sample_evidence)

        assert "https://made-up-url.example/foo" not in result.supporting_urls
        assert sample_evidence[0].url in result.supporting_urls

    async def test_strips_hallucinated_contradicting_urls(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        payload = verifier_payload(
            classification="false",
            contradicting_urls=["https://invented.example/bar"],
        )
        client = make_anthropic(payload)
        result = await Verifier(client).verify("claim", sample_evidence)
        assert result.contradicting_urls == []

    async def test_misinformation_patterns_filtered(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        payload = verifier_payload(
            misinformation_patterns=["cherry_picking", "made_up_pattern", "missing_context"]
        )
        client = make_anthropic(payload)
        result = await Verifier(client).verify("claim", sample_evidence)

        assert "cherry_picking" in result.misinformation_patterns
        assert "missing_context" in result.misinformation_patterns
        assert "made_up_pattern" not in result.misinformation_patterns

    async def test_empty_evidence_short_circuits_to_unverifiable(self, make_anthropic):
        client = make_anthropic({"this": "should not be called"})
        result = await Verifier(client).verify("claim", evidence=[])
        assert result.classification == Classification.UNVERIFIABLE
        client.messages.create.assert_not_called()

    async def test_invalid_classification_raises(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        client = make_anthropic(verifier_payload(classification="not_real"))
        with pytest.raises(LLMOutputError):
            await Verifier(client).verify("claim", sample_evidence)

    async def test_emotional_and_outdated_flags_propagate(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        client = make_anthropic(
            verifier_payload(emotional_language_detected=True, is_outdated=True)
        )
        result = await Verifier(client).verify("SHOCKING claim", sample_evidence)
        assert result.emotional_language_detected
        assert result.is_outdated

    async def test_pt_br_hint_in_message(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        client = make_anthropic(verifier_payload())
        await Verifier(client).verify("uma afirmação", sample_evidence, language="pt-BR")
        msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "português" in msg.lower()

    async def test_cache_control_present(
        self, make_anthropic, verifier_payload, sample_evidence
    ):
        client = make_anthropic(verifier_payload())
        await Verifier(client).verify("claim", sample_evidence)
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
