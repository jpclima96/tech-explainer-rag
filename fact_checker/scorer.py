from datetime import datetime, timezone
from typing import Optional

from fact_checker.models.response import Classification, Source
from fact_checker.retriever import SearchResult, credibility_score_for_url
from fact_checker.verifier import VerificationResult

# Confidence formula weights (must sum to 1.0)
_W_AGREEMENT = 0.35
_W_CREDIBILITY = 0.30
_W_RECENCY = 0.20
_W_CONSISTENCY = 0.15

_OUTDATED_PENALTY = 0.75
_UNVERIFIABLE_CAP = 0.40


def _agreement_ratio(agree: int, disagree: int) -> float:
    total = agree + disagree
    if total == 0:
        return 0.0
    return agree / total


def _recency_score(published_date: Optional[str]) -> float:
    if not published_date:
        return 0.50  # unknown date → neutral

    _FORMATS = [
        ("%Y-%m-%d", 10),
        ("%Y-%m-%dT%H:%M:%SZ", 20),
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y/%m/%d", 10),
        ("%Y", 4),
    ]
    dt = None
    for fmt, length in _FORMATS:
        try:
            dt = datetime.strptime(published_date[:length], fmt).replace(tzinfo=timezone.utc)
            break
        except ValueError:
            continue
    if dt is None:
        return 0.50  # unparseable → neutral

    now = datetime.now(tz=timezone.utc)
    age_years = (now - dt).days / 365.25

    if age_years <= 1:
        return 1.00
    if age_years <= 3:
        return 0.75
    if age_years <= 5:
        return 0.50
    return 0.25


def _mean_credibility(urls: list[str]) -> float:
    if not urls:
        return 0.0
    scores = [credibility_score_for_url(u) for u in urls]
    return sum(scores) / len(scores)


def _mean_recency(sources: list[SearchResult], supporting_urls: set[str]) -> float:
    relevant = [s for s in sources if s.url in supporting_urls]
    if not relevant:
        return 0.0
    scores = [_recency_score(s.published_date) for s in relevant]
    return sum(scores) / len(scores)


def _consistency_score(
    all_sources: list[SearchResult],
    supporting_urls: set[str],
    contradicting_urls: set[str],
) -> float:
    total = len(all_sources)
    if total == 0:
        return 0.0
    contradicting = sum(1 for s in all_sources if s.url in contradicting_urls)
    return max(0.0, (total - contradicting) / total)


class Scorer:
    def compute(
        self,
        verification: VerificationResult,
        all_evidence: list[SearchResult],
    ) -> tuple[float, list[Source]]:
        supporting_urls = set(verification.supporting_urls)
        contradicting_urls = set(verification.contradicting_urls)

        agreement = _agreement_ratio(
            verification.source_agreement_count,
            verification.source_disagreement_count,
        )
        credibility = _mean_credibility(list(supporting_urls))
        recency = _mean_recency(all_evidence, supporting_urls)
        consistency = _consistency_score(all_evidence, supporting_urls, contradicting_urls)

        raw_score = (
            _W_AGREEMENT * agreement
            + _W_CREDIBILITY * credibility
            + _W_RECENCY * recency
            + _W_CONSISTENCY * consistency
        )

        if verification.is_outdated:
            raw_score *= _OUTDATED_PENALTY

        if verification.classification == Classification.UNVERIFIABLE:
            raw_score = min(raw_score, _UNVERIFIABLE_CAP)

        confidence = round(max(0.0, min(1.0, raw_score)), 4)

        sources = self._build_sources(all_evidence, supporting_urls)
        return confidence, sources

    def _build_sources(
        self, evidence: list[SearchResult], supporting_urls: set[str]
    ) -> list[Source]:
        seen: set[str] = set()
        sources: list[Source] = []
        # Supporting sources first, then the rest
        ordered = sorted(evidence, key=lambda e: e.url not in supporting_urls)
        for item in ordered:
            if item.url in seen:
                continue
            seen.add(item.url)
            sources.append(
                Source(
                    title=item.title,
                    url=item.url,
                    credibility_score=credibility_score_for_url(item.url),
                )
            )
        return sources
