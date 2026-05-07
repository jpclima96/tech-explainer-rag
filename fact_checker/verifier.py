from __future__ import annotations

import anthropic

from fact_checker._llm import call_json
from fact_checker.config import settings
from fact_checker.exceptions import LLMOutputError
from fact_checker.models import (
    Classification,
    MisinformationPattern,
    SearchResult,
    VerificationResult,
)
from fact_checker.prompts import VERIFIER_SYSTEM_PROMPT

_VALID_PATTERNS = {p.value for p in MisinformationPattern}


class Verifier:
    """Verify a single claim against retrieved evidence."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = settings.default_model,
    ) -> None:
        self._client = client
        self._model = model

    async def verify(
        self,
        claim: str,
        evidence: list[SearchResult],
        language: str = "en",
    ) -> VerificationResult:
        if not evidence:
            return VerificationResult(
                classification=Classification.UNVERIFIABLE,
                explanation="No evidence was retrieved for this claim.",
            )

        user_content = self._build_user_message(claim, evidence, language)
        data = await call_json(
            self._client,
            model=self._model,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            user_content=user_content,
            max_tokens=1500,
        )

        result = self._parse(data)

        # Hard guard: strip any URL the model invented that isn't in the evidence.
        allowed = {e.url for e in evidence}
        result.supporting_urls = [u for u in result.supporting_urls if u in allowed]
        result.contradicting_urls = [u for u in result.contradicting_urls if u in allowed]
        return result

    @staticmethod
    def _build_user_message(
        claim: str, evidence: list[SearchResult], language: str
    ) -> str:
        evidence_block = "\n\n".join(
            f"[{i}] Title: {e.title!r}\n    URL: {e.url}\n"
            f"    Published: {e.published_date or 'unknown'}\n"
            f"    Excerpt: {e.content[:600]}"
            for i, e in enumerate(evidence, start=1)
        )

        lang_hint = (
            "A afirmação está em português. Responda em português.\n"
            if language.lower().startswith("pt")
            else ""
        )

        return (
            f"{lang_hint}"
            f"<claim>\n{claim}\n</claim>\n\n"
            f"<evidence>\n{evidence_block}\n</evidence>"
        )

    @staticmethod
    def _parse(data: dict) -> VerificationResult:
        try:
            classification = Classification(data["classification"])
        except (KeyError, ValueError) as exc:
            raise LLMOutputError(f"Invalid classification in verifier output: {data}") from exc

        patterns = [
            p for p in data.get("misinformation_patterns", []) if p in _VALID_PATTERNS
        ]

        return VerificationResult(
            classification=classification,
            explanation=str(data.get("explanation", "")),
            supporting_urls=list(data.get("supporting_urls", [])),
            contradicting_urls=list(data.get("contradicting_urls", [])),
            misinformation_patterns=patterns,
            emotional_language_detected=bool(data.get("emotional_language_detected", False)),
            is_outdated=bool(data.get("is_outdated", False)),
            source_agreement_count=int(data.get("source_agreement_count", 0)),
            source_disagreement_count=int(data.get("source_disagreement_count", 0)),
        )
