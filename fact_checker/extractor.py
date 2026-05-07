from __future__ import annotations

import anthropic

from fact_checker._llm import call_json
from fact_checker.config import settings
from fact_checker.exceptions import LLMOutputError
from fact_checker.prompts import EXTRACTOR_SYSTEM_PROMPT


class ClaimExtractor:
    """Extract atomic, verifiable factual claims from arbitrary text."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = settings.default_model,
    ) -> None:
        self._client = client
        self._model = model

    async def extract(
        self,
        text: str,
        context: str | None = None,
        language: str = "en",
    ) -> list[str]:
        user_content = self._build_user_message(text, context, language)
        result = await call_json(
            self._client,
            model=self._model,
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            user_content=user_content,
        )

        if not isinstance(result, list):
            raise LLMOutputError(f"Expected JSON array, got {type(result).__name__}")

        claims = [c.strip() for c in result if isinstance(c, str) and c.strip()]
        return claims[: settings.max_claims]

    @staticmethod
    def _build_user_message(text: str, context: str | None, language: str) -> str:
        parts = []
        if language.lower().startswith("pt"):
            parts.append(
                "The text is in Brazilian Portuguese (pt-BR). "
                "Preserve extracted claims in Portuguese."
            )
        if context:
            parts.append(f"<context>\n{context}\n</context>")
        parts.append(f"<text>\n{text}\n</text>")
        parts.append("Extract every atomic, verifiable factual claim from the text above.")
        return "\n\n".join(parts)
