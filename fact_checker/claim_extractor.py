import json
from typing import Optional

import anthropic

from fact_checker.config import settings

EXTRACTOR_SYSTEM_PROMPT = """\
You are a fact-checking assistant specialized in extracting verifiable factual claims from text.

Your task is to identify and extract ONLY atomic, independently verifiable factual claims.

STRICT RULES:
1. Each claim must be independently verifiable against external sources.
2. Each claim must be atomic — one assertion per claim. Do not combine multiple facts.
3. Exclude pure opinions, personal preferences, and subjective judgments.
4. Exclude future predictions and hypotheticals that cannot be verified today.
5. Exclude rhetorical questions and emotional language with no factual content.
6. Preserve the original meaning without paraphrasing — extract claims verbatim or near-verbatim.
7. If the text is in Portuguese (pt-BR), preserve claims in Portuguese.
8. If a sentence contains both an opinion and an embedded fact, extract only the factual part.
9. Return ONLY a valid JSON array of strings. No preamble, no explanation, no markdown fences.
10. If no verifiable claims exist, return an empty JSON array: []

EXAMPLES of claims to INCLUDE:
- "Brazil's GDP in 2023 was R$10.9 trillion"
- "The COVID-19 mRNA vaccines were authorized by the FDA in December 2020"
- "The Amazon rainforest covers approximately 5.5 million square kilometers"
- "Scientists at MIT developed a new battery with 40% more capacity"

EXAMPLES to EXCLUDE:
- "The economy will improve next year" (future prediction)
- "The government is corrupt" (pure opinion)
- "This is the worst policy ever" (subjective judgment)
- "We should invest more in education" (normative claim)
- "Could you believe they did that?" (rhetorical question)

IMPORTANT: Respond with ONLY the JSON array. Nothing else. Example:
["Claim one here.", "Claim two here."]
"""


class ClaimExtractor:
    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = settings.default_model,
    ) -> None:
        self._client = client
        self._model = model

    async def extract(self, text: str, context: Optional[str] = None, language: str = "en") -> list[str]:
        messages = self._build_messages(text, context, language)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": EXTRACTOR_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
        raw = response.content[0].text.strip()
        return self._parse_claims(raw)

    def _build_messages(
        self, text: str, context: Optional[str], language: str
    ) -> list[dict[str, str]]:
        lang_hint = ""
        if language.lower().startswith("pt"):
            lang_hint = "\nNote: The text is in Brazilian Portuguese (pt-BR). Extract and preserve claims in Portuguese."

        context_block = ""
        if context:
            context_block = f"\n\n<context>\n{context}\n</context>"

        user_content = (
            f"Extract all atomic, verifiable factual claims from the following text."
            f"{lang_hint}"
            f"{context_block}"
            f"\n\n<text>\n{text}\n</text>"
        )
        return [{"role": "user", "content": user_content}]

    def _parse_claims(self, raw: str) -> list[str]:
        try:
            claims = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON for claim extraction: {raw!r}") from exc

        if not isinstance(claims, list):
            raise ValueError(f"Expected a JSON array, got: {type(claims)}")

        claims = [c for c in claims if isinstance(c, str) and c.strip()]
        return claims[: settings.max_claims_per_request]
