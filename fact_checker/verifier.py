import json

import anthropic

from fact_checker.config import settings
from fact_checker.models.response import Classification
from fact_checker.retriever import SearchResult

VERIFIER_SYSTEM_PROMPT = """\
You are a rigorous fact-checker with deep expertise in identifying misinformation.
Your job is to evaluate whether a given claim is supported, contradicted, or unverifiable
based ONLY on the evidence provided to you.

STRICT RULES:
1. NEVER reference a URL that is not explicitly listed in the evidence block provided.
2. Base your verdict solely on the provided evidence. Do not use prior knowledge.
3. Classification definitions:
   - "true": The claim is clearly supported by the evidence and no significant contradictions exist.
   - "false": The claim is clearly contradicted by the evidence.
   - "misleading": The claim is technically true or partially true but omits crucial context,
     uses selective statistics, or frames data in a deceptive way.
   - "unverifiable": The evidence is absent, insufficient, too vague, or from unreliable sources.
4. Prefer "unverifiable" over guessing when evidence is insufficient or ambiguous.
5. Misinformation patterns to detect (use exact strings when present):
   - "cherry_picking": Only citing data that supports one side while ignoring contradicting evidence.
   - "missing_context": Omitting key facts that would materially change interpretation.
   - "statistical_manipulation": Misuse of percentages, base rates, absolute vs relative risk,
     or implying causation from correlation.
   - "outdated_info": Presenting outdated data as if it were current (set is_outdated=true).
   - "false_equivalence": Treating fundamentally unequal things as if they are comparable.
6. Set emotional_language_detected=true if the claim uses fear-inducing, outrage-triggering,
   or excessively emotive language intended to manipulate rather than inform.
7. Your explanation must be transparent about uncertainty. Cite evidence by URL when possible.
8. Respond in the same language as the claim (pt-BR or en).
9. Respond with ONLY valid JSON matching the schema below. No markdown fences, no preamble.

RESPONSE SCHEMA:
{
  "classification": "true|false|misleading|unverifiable",
  "explanation": "Clear reasoning referencing specific evidence. Be transparent about uncertainty.",
  "supporting_urls": ["only URLs that support the classification"],
  "contradicting_urls": ["only URLs that contradict the classification"],
  "misinformation_patterns": ["cherry_picking"|"missing_context"|"statistical_manipulation"|"outdated_info"|"false_equivalence"],
  "emotional_language_detected": true|false,
  "is_outdated": true|false,
  "source_agreement_count": <integer: number of sources supporting the claim>,
  "source_disagreement_count": <integer: number of sources contradicting the claim>
}
"""


class VerificationResult:
    __slots__ = (
        "classification",
        "explanation",
        "supporting_urls",
        "contradicting_urls",
        "misinformation_patterns",
        "emotional_language_detected",
        "is_outdated",
        "source_agreement_count",
        "source_disagreement_count",
    )

    def __init__(
        self,
        classification: Classification,
        explanation: str,
        supporting_urls: list[str],
        contradicting_urls: list[str],
        misinformation_patterns: list[str],
        emotional_language_detected: bool,
        is_outdated: bool,
        source_agreement_count: int,
        source_disagreement_count: int,
    ) -> None:
        self.classification = classification
        self.explanation = explanation
        self.supporting_urls = supporting_urls
        self.contradicting_urls = contradicting_urls
        self.misinformation_patterns = misinformation_patterns
        self.emotional_language_detected = emotional_language_detected
        self.is_outdated = is_outdated
        self.source_agreement_count = source_agreement_count
        self.source_disagreement_count = source_disagreement_count


_VALID_PATTERNS = {
    "cherry_picking",
    "missing_context",
    "statistical_manipulation",
    "outdated_info",
    "false_equivalence",
}


class Verifier:
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
                supporting_urls=[],
                contradicting_urls=[],
                misinformation_patterns=[],
                emotional_language_detected=False,
                is_outdated=False,
                source_agreement_count=0,
                source_disagreement_count=0,
            )

        evidence_block = self._build_evidence_block(evidence)
        allowed_urls = {r.url for r in evidence}

        lang_hint = ""
        if language.lower().startswith("pt"):
            lang_hint = "\nA afirmação está em português (pt-BR). Responda em português."

        user_content = (
            f"Verify the following claim against the provided evidence.{lang_hint}\n\n"
            f"<claim>\n{claim}\n</claim>\n\n"
            f"<evidence>\n{evidence_block}\n</evidence>"
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=[
                {
                    "type": "text",
                    "text": VERIFIER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text.strip()
        result = self._parse_response(raw)

        # Hard URL guard: strip any hallucinated URLs not in the evidence set
        result.supporting_urls = [u for u in result.supporting_urls if u in allowed_urls]
        result.contradicting_urls = [u for u in result.contradicting_urls if u in allowed_urls]

        return result

    def _build_evidence_block(self, evidence: list[SearchResult]) -> str:
        lines = []
        for i, item in enumerate(evidence, start=1):
            date_line = f"    Published: {item.published_date}" if item.published_date else ""
            lines.append(
                f"[{i}] Title: {item.title!r}\n"
                f"    URL: {item.url}\n"
                f"{date_line}\n"
                f"    Excerpt: {item.content[:500]}"
            )
        return "\n\n".join(lines)

    def _parse_response(self, raw: str) -> VerificationResult:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Verifier LLM returned invalid JSON: {raw!r}") from exc

        try:
            classification = Classification(data["classification"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid classification in verifier response: {data}") from exc

        patterns = [p for p in data.get("misinformation_patterns", []) if p in _VALID_PATTERNS]

        return VerificationResult(
            classification=classification,
            explanation=data.get("explanation", ""),
            supporting_urls=data.get("supporting_urls", []),
            contradicting_urls=data.get("contradicting_urls", []),
            misinformation_patterns=patterns,
            emotional_language_detected=bool(data.get("emotional_language_detected", False)),
            is_outdated=bool(data.get("is_outdated", False)),
            source_agreement_count=int(data.get("source_agreement_count", 0)),
            source_disagreement_count=int(data.get("source_disagreement_count", 0)),
        )
