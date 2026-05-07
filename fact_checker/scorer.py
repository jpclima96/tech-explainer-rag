"""Confidence scoring — pure functions, no I/O."""
from __future__ import annotations

from datetime import datetime, timezone

from fact_checker.models import (
    Classification,
    SearchResult,
    Source,
    VerificationResult,
)
from fact_checker.retriever import credibility_score_for_url

# Weights for the confidence formula (must sum to 1.0)
W_AGREEMENT = 0.35
W_CREDIBILITY = 0.30
W_RECENCY = 0.20
W_CONSISTENCY = 0.15

OUTDATED_PENALTY = 0.75
UNVERIFIABLE_CAP = 0.40

_DATE_FORMATS = [
    ("%Y-%m-%d", 10),
    ("%Y-%m-%dT%H:%M:%SZ", 20),
    ("%Y-%m-%dT%H:%M:%S", 19),
    ("%Y/%m/%d", 10),
    ("%Y", 4),
]


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt, length in _DATE_FORMATS:
        try:
            return datetime.strptime(raw[:length], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def recency_score(published_date: str | None) -> float:
    """Map a published date to a recency score in [0, 1]."""
    dt = _parse_date(published_date)
    if dt is None:
        return 0.50  # neutral when unknown
    age_years = (datetime.now(tz=timezone.utc) - dt).days / 365.25
    if age_years <= 1:
        return 1.00
    if age_years <= 3:
        return 0.75
    if age_years <= 5:
        return 0.50
    return 0.25


def agreement_ratio(agree: int, disagree: int) -> float:
    total = agree + disagree
    return 0.0 if total == 0 else agree / total


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _consistency(
    evidence: list[SearchResult], contradicting: set[str]
) -> float:
    if not evidence:
        return 0.0
    against = sum(1 for e in evidence if e.url in contradicting)
    return max(0.0, (len(evidence) - against) / len(evidence))


def compute(
    verification: VerificationResult,
    evidence: list[SearchResult],
) -> tuple[float, list[Source]]:
    """Return (confidence_score, ordered Source list) for a verified claim."""
    supporting = set(verification.supporting_urls)
    contradicting = set(verification.contradicting_urls)

    cred = _mean([credibility_score_for_url(u) for u in supporting])
    rec = _mean([recency_score(e.published_date) for e in evidence if e.url in supporting])
    agree = agreement_ratio(
        verification.source_agreement_count,
        verification.source_disagreement_count,
    )
    cons = _consistency(evidence, contradicting)

    score = (
        W_AGREEMENT * agree
        + W_CREDIBILITY * cred
        + W_RECENCY * rec
        + W_CONSISTENCY * cons
    )

    if verification.is_outdated:
        score *= OUTDATED_PENALTY

    if verification.classification == Classification.UNVERIFIABLE:
        score = min(score, UNVERIFIABLE_CAP)

    confidence = round(max(0.0, min(1.0, score)), 4)
    sources = _build_sources(evidence, supporting)
    return confidence, sources


def _build_sources(
    evidence: list[SearchResult], supporting: set[str]
) -> list[Source]:
    seen: set[str] = set()
    out: list[Source] = []
    # Supporting first, then everything else, deduplicated by URL.
    ordered = sorted(evidence, key=lambda e: e.url not in supporting)
    for item in ordered:
        if not item.url or item.url in seen:
            continue
        seen.add(item.url)
        out.append(
            Source(
                title=item.title or item.url,
                url=item.url,
                credibility_score=credibility_score_for_url(item.url),
            )
        )
    return out
