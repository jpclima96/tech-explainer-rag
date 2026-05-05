import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from fact_checker.claim_extractor import ClaimExtractor


def make_extractor(client: AsyncMock) -> ClaimExtractor:
    return ClaimExtractor(client=client, model="claude-sonnet-4-6")


def make_client(response_text: str) -> AsyncMock:
    client = AsyncMock(spec=anthropic.AsyncAnthropic)
    text_block = MagicMock()
    text_block.text = response_text
    mock_response = MagicMock()
    mock_response.content = [text_block]
    client.messages = AsyncMock()
    client.messages.create = AsyncMock(return_value=mock_response)
    return client


class TestClaimExtractor:
    async def test_extract_returns_list_of_strings(self):
        claims = ["The Earth orbits the Sun.", "Water boils at 100°C at sea level."]
        client = make_client(json.dumps(claims))
        extractor = make_extractor(client)

        result = await extractor.extract("Some text with facts.")

        assert result == claims
        assert all(isinstance(c, str) for c in result)

    async def test_extract_empty_text_returns_empty_list(self):
        client = make_client("[]")
        extractor = make_extractor(client)

        result = await extractor.extract("This is purely an opinion and nothing else.")

        assert result == []

    async def test_extract_caps_at_max_claims(self):
        many_claims = [f"Claim number {i}." for i in range(30)]
        client = make_client(json.dumps(many_claims))
        extractor = make_extractor(client)

        with patch("fact_checker.claim_extractor.settings") as mock_settings:
            mock_settings.max_claims_per_request = 5
            result = await extractor.extract("Text with many claims.")

        assert len(result) <= 5

    async def test_extract_filters_empty_strings(self):
        claims_with_blanks = ["Valid claim.", "", "  ", "Another valid claim."]
        client = make_client(json.dumps(claims_with_blanks))
        extractor = make_extractor(client)

        result = await extractor.extract("Some text.")

        assert "" not in result
        assert "  " not in result
        assert len(result) == 2

    async def test_extract_raises_on_invalid_json(self):
        client = make_client("not valid json at all")
        extractor = make_extractor(client)

        with pytest.raises(ValueError, match="invalid JSON"):
            await extractor.extract("Some text.")

    async def test_extract_raises_on_non_array_json(self):
        client = make_client('{"key": "value"}')
        extractor = make_extractor(client)

        with pytest.raises(ValueError, match="JSON array"):
            await extractor.extract("Some text.")

    async def test_cache_control_present_in_api_call(self):
        client = make_client('["A claim."]')
        extractor = make_extractor(client)

        await extractor.extract("Some text.")

        call_kwargs = client.messages.create.call_args
        system_param = call_kwargs.kwargs.get("system") or call_kwargs.args[0] if call_kwargs.args else None
        system_param = call_kwargs.kwargs.get("system")
        assert system_param is not None
        assert len(system_param) == 1
        assert system_param[0]["cache_control"] == {"type": "ephemeral"}

    async def test_extract_with_context(self):
        client = make_client('["GDP was R$10.9 trillion in 2023."]')
        extractor = make_extractor(client)

        result = await extractor.extract(
            "Brazil had a large GDP in 2023.",
            context="Economic data from IBGE report.",
        )

        assert len(result) == 1
        # Verify context was included in the user message
        call_kwargs = client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert "Economic data from IBGE report." in messages[0]["content"]

    async def test_extract_pt_br_language_hint(self):
        client = make_client('["O PIB do Brasil foi de R$10 trilhões."]')
        extractor = make_extractor(client)

        await extractor.extract("Texto em português.", language="pt-BR")

        call_kwargs = client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert "pt-BR" in messages[0]["content"] or "Portuguese" in messages[0]["content"]

    async def test_llm_called_with_correct_model(self):
        client = make_client('["A claim."]')
        extractor = ClaimExtractor(client=client, model="claude-opus-4-7")

        await extractor.extract("Some text.")

        call_kwargs = client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-4-7"
