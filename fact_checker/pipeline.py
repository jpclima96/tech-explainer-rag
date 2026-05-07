from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass

import anthropic
import httpx

from fact_checker import scorer
from fact_checker.config import settings
from fact_checker.extractor import ClaimExtractor
from fact_checker.models import (
    Claim,
    FactCheckRequest,
    FactCheckResponse,
    VerificationResult,
)
from fact_checker.retriever import Retriever, default_retriever
from fact_checker.verifier import Verifier

# Templated overall-assessment strings — generated without an extra LLM call.
_ASSESSMENT_TEMPLATES = {
    "en": (
        "Analyzed {total} verifiable claim(s): "
        "{true} true, {false} false, {misleading} misleading, {unverifiable} unverifiable. "
        "{reliability}"
    ),
    "pt": (
        "Foram analisadas {total} afirmação(ões) verificável(eis): "
        "{true} verdadeira(s), {false} falsa(s), {misleading} enganosa(s), {unverifiable} inverificável(eis). "
        "{reliability}"
    ),
}

_RELIABILITY = {
    "en": {
        "high": "Overall reliability appears HIGH.",
        "moderate": "Overall reliability appears MODERATE — verify key claims independently.",
        "low": "Overall reliability appears LOW — significant concerns detected.",
        "mixed": "Overall reliability is MIXED — text contains both accurate and inaccurate claims.",
    },
    "pt": {
        "high": "A confiabilidade geral parece ALTA.",
        "moderate": "A confiabilidade geral parece MODERADA — verifique as principais afirmações.",
        "low": "A confiabilidade geral parece BAIXA — preocupações significativas detectadas.",
        "mixed": "A confiabilidade geral é MISTA — o texto contém afirmações precisas e imprecisas.",
    },
}


def _assess(claims: list[Claim], language: str) -> str:
    lang = "pt" if language.lower().startswith("pt") else "en"
    if not claims:
        return (
            "No verifiable claims were found in the text."
            if lang == "en"
            else "Nenhuma afirmação verificável foi encontrada no texto."
        )

    counts = Counter(c.classification.value for c in claims)
    true_n = counts.get("true", 0)
    false_n = counts.get("false", 0)
    misleading_n = counts.get("misleading", 0)
    unverifiable_n = counts.get("unverifiable", 0)
    verified = true_n + false_n + misleading_n
    bad = false_n + misleading_n

    if verified == 0:
        label = "mixed"
    elif bad == 0:
        label = "high"
    elif true_n == 0:
        label = "low"
    elif bad / verified > 0.5:
        label = "low"
    elif bad / verified > 0.25:
        label = "moderate"
    else:
        label = "mixed"

    return _ASSESSMENT_TEMPLATES[lang].format(
        total=len(claims),
        true=true_n,
        false=false_n,
        misleading=misleading_n,
        unverifiable=unverifiable_n,
        reliability=_RELIABILITY[lang][label],
    )


@dataclass
class _ProcessedClaim:
    claim: Claim
    verification: VerificationResult


class FactCheckPipeline:
    """Orchestrates extraction → retrieval → verification → scoring."""

    def __init__(
        self,
        extractor: ClaimExtractor,
        retriever: Retriever,
        verifier: Verifier,
    ) -> None:
        self._extractor = extractor
        self._retriever = retriever
        self._verifier = verifier

    async def run(self, request: FactCheckRequest) -> FactCheckResponse:
        claims_text = await self._extractor.extract(
            request.text, request.context, request.language
        )

        sem = asyncio.Semaphore(settings.concurrency_limit)
        processed = await asyncio.gather(
            *(self._process(c, request.language, sem) for c in claims_text)
        )

        claims = [p.claim for p in processed]
        patterns = sorted({
            p for proc in processed for p in proc.verification.misinformation_patterns
        })
        emotional = any(p.verification.emotional_language_detected for p in processed)

        return FactCheckResponse(
            claims=claims,
            overall_assessment=_assess(claims, request.language),
            misinformation_patterns=patterns,
            emotional_manipulation_detected=emotional,
        )

    async def _process(
        self,
        claim_text: str,
        language: str,
        sem: asyncio.Semaphore,
    ) -> _ProcessedClaim:
        async with sem:
            evidence = await self._retriever.search(
                claim_text, num_results=settings.results_per_claim
            )
            verification = await self._verifier.verify(claim_text, evidence, language)
            confidence, sources = scorer.compute(verification, evidence)

        return _ProcessedClaim(
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
    return FactCheckPipeline(
        extractor=ClaimExtractor(anthropic_client),
        retriever=default_retriever(http_client),
        verifier=Verifier(anthropic_client),
    )
