from __future__ import annotations

import pytest

from fact_checker.exceptions import LLMOutputError
from fact_checker.extractor import ClaimExtractor


class TestClaimExtractor:
    async def test_returns_list_of_claims(self, make_anthropic):
        client = make_anthropic(["The Earth orbits the Sun.", "Water boils at 100C."])
        extractor = ClaimExtractor(client)

        result = await extractor.extract("Some text with facts.")

        assert result == ["The Earth orbits the Sun.", "Water boils at 100C."]

    async def test_empty_array_returns_empty(self, make_anthropic):
        client = make_anthropic([])
        extractor = ClaimExtractor(client)

        assert await extractor.extract("All opinions, nothing factual.") == []

    async def test_blank_strings_filtered(self, make_anthropic):
        client = make_anthropic(["Real claim.", "", "  ", "Another."])
        extractor = ClaimExtractor(client)

        assert await extractor.extract("Some text.") == ["Real claim.", "Another."]

    async def test_caps_at_max_claims(self, make_anthropic, monkeypatch):
        from fact_checker import extractor as extractor_module
        monkeypatch.setattr(extractor_module.settings, "max_claims", 3)
        client = make_anthropic([f"claim {i}" for i in range(20)])
        extractor = ClaimExtractor(client)

        result = await extractor.extract("Some text.")
        assert len(result) == 3

    async def test_invalid_json_raises_llm_output_error(self, make_anthropic):
        client = make_anthropic("not-valid-json")
        extractor = ClaimExtractor(client)

        with pytest.raises(LLMOutputError):
            await extractor.extract("Some text.")

    async def test_non_array_json_raises(self, make_anthropic):
        client = make_anthropic({"not": "an array"})
        extractor = ClaimExtractor(client)

        with pytest.raises(LLMOutputError):
            await extractor.extract("Some text.")

    async def test_strips_markdown_fences(self, make_anthropic):
        client = make_anthropic('```json\n["A claim."]\n```')
        extractor = ClaimExtractor(client)

        assert await extractor.extract("Some text.") == ["A claim."]

    async def test_cache_control_in_system_prompt(self, make_anthropic):
        client = make_anthropic(["A claim."])
        extractor = ClaimExtractor(client)
        await extractor.extract("Some text.")

        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}

    async def test_pt_br_hint_in_user_message(self, make_anthropic):
        client = make_anthropic(["Uma afirmação."])
        extractor = ClaimExtractor(client)

        await extractor.extract("Texto em português.", language="pt-BR")
        kwargs = client.messages.create.call_args.kwargs
        user = kwargs["messages"][0]["content"]
        assert "Portuguese" in user or "pt-BR" in user

    async def test_context_included_in_user_message(self, make_anthropic):
        client = make_anthropic(["A claim."])
        extractor = ClaimExtractor(client)

        await extractor.extract("Text.", context="Background info from IBGE.")
        user = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Background info from IBGE." in user

    async def test_default_model_is_opus(self, make_anthropic):
        client = make_anthropic(["A claim."])
        extractor = ClaimExtractor(client)
        await extractor.extract("Some text.")

        assert client.messages.create.call_args.kwargs["model"] == "claude-opus-4-7"
