import asyncio
from collections import Counter

import anthropic
import httpx

from fact_checker.claim_extractor import ClaimExtractor
from fact_checker.config import settings
from fact_checker.models.request import FactCheckRequest
from fact_checker.models.response import Claim, FactCheckResponse
from fact_checker.retriever import BaseRetriever, TavilyRetriever
from fact_checker.scorer import Scorer
from fact_checker.verifier import VerificationResult, Verifier

_CONCURRENCY_LIMIT = 5

_ASSESSMENT_TEMPLATES = {
    "en": (
        "The text contains {total} verifiable claim(s): "
        "{true} true, {false} false, {misleading} misleading, and {unverifiable} unverifiable. "
        "{reliability}"
    ),
    "pt": (
        "O texto contém {total} afirmação(ões) verificável(eis): "
        "{true} verdadeira(s), {false} falsa(s), {misleading} enganosa(s) e {unverifiable} inverificável(eis). "
        "{reliability}"
    ),
}

_RELIABILITY_LABELS = {
    "en": {
        "high": "Overall reliability appears HIGH.",
        "medium": "Overall reliability appears MODERATE — verify key claims independently.",
        "low": "Overall reliability appears LOW — significant concerns detected.",
        "mixed": "Content is MIXED — contains both accurate and inaccurate claims.",
    },
    "pt": {
        "high": "A confiabilidade geral parece ALTA.",
        "medium": "A confiabilidade geral parece MODERADA — verifique as principais afirmações de forma independente.",
        "low": "A confiabilidade geral parece BAIXA — preocupações significativas detectadas.",
        "mixed": "O conteúdo é MISTO — contém afirmações precisas e imprecisas.",
    },
}


def _build_overall_assessment(claims: list[Claim], language: str) -> str:
    lang = "pt" if language.lower().startswith("pt") else "en"
    counts: Counter[str] = Counter(c.classification.value for c in claims)
    total = len(claims)

    if total == 0:
        if lang == "pt":
            return "Nenhuma afirmação verificável foi encontrada no texto."
        return "No verifiable claims were found in the text."

    true_n = counts.get("true", 0)
    false_n = counts.get("false", 0)
    misleading_n = counts.get("misleading", 0)
    unverifiable_n = counts.get("unverifiable", 0)

    verified = true_n + false_n + misleading_n
    if verified == 0:
        label = "mixed"
    elif false_n + misleading_n == 0:
        label = "high"
    elif true_n == 0:
        label = "low"
    elif (false_n + misleading_n) / verified > 0.5:
        label = "low"
    elif (false_n + misleading_n) / verified > 0.25:
        label = "medium"
    else:
        label = "mixed"

    reliability = _RELIABILITY_LABELS[lang][label]
    template = _ASSESSMENT_TEMPLATES[lang]
    return template.format(
        total=total,
        true=true_n,
        false=false_n,
        misleading=misleading_n,
        unverifiable=unverifiable_n,
        reliability=reliability,
    )


# Internal result bundle returned by _process_claim
class _ClaimBundle:
    __slots__ = ("claim", "verification")

    def __init__(self, claim: Claim, verification: VerificationResult) -> None:
        self.claim = claim
        self.verification = verification


class FactCheckPipeline:
    def __init__(
        self,
        extractor: ClaimExtractor,
        retriever: BaseRetriever,
        verifier: Verifier,
        scorer: Scorer,
    ) -> None:
        self._extractor = extractor
        self._retriever = retriever
        self._verifier = verifier
        self._scorer = scorer

    async def run(self, request: FactCheckRequest) -> FactCheckResponse:
        claims_text = await self._extractor.extract(
            request.text, request.context, request.language
        )

        semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)
        tasks = [
            self._process_claim(claim_text, request.language, semaphore)
            for claim_text in claims_text
        ]
        bundles: list[_ClaimBundle] = list(await asyncio.gather(*tasks))

        claims = [b.claim for b in bundles]

        all_patterns = list(
            {p for b in bundles for p in b.verification.misinformation_patterns}
        )
        any_emotional = any(b.verification.emotional_language_detected for b in bundles)

        overall = _build_overall_assessment(claims, request.language)

        return FactCheckResponse(
            claims=claims,
            overall_assessment=overall,
            misinformation_patterns=sorted(all_patterns),
            emotional_manipulation_detected=any_emotional,
        )

    async def _process_claim(
        self,
        claim_text: str,
        language: str,
        semaphore: asyncio.Semaphore,
    ) -> _ClaimBundle:
        async with semaphore:
            evidence = await self._retriever.search(
                claim_text, num_results=settings.retriever_results_per_claim
            )
            verification = await self._verifier.verify(claim_text, evidence, language)
            confidence, sources = self._scorer.compute(verification, evidence)

        return _ClaimBundle(
            claim=Claim(
                claim=claim_text,
                classification=verification.classification,
                confidence_score=confidence,
                explanation=verification.explanation,
                sources=sources,
            ),
            verification=verification,
        )


def build_pipeline(
    anthropic_client: anthropic.AsyncAnthropic,
    http_client: httpx.AsyncClient,
) -> FactCheckPipeline:
    extractor = ClaimExtractor(client=anthropic_client, model=settings.default_model)
    retriever = TavilyRetriever(api_key=settings.tavily_api_key, http_client=http_client)
    verifier = Verifier(client=anthropic_client, model=settings.default_model)
    scorer = Scorer()
    return FactCheckPipeline(
        extractor=extractor,
        retriever=retriever,
        verifier=verifier,
        scorer=scorer,
    )
