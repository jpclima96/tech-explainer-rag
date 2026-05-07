from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from fact_checker import scorer
from fact_checker.models import (
    Classification,
    SearchResult,
    VerificationResult,
)


def date_years_ago(years: float) -> str:
    dt = datetime.now(tz=timezone.utc) - timedelta(days=int(years * 365.25))
    return dt.strftime("%Y-%m-%d")


def evidence(urls: list[str], dates: list[str | None] | None = None) -> list[SearchResult]:
    if dates is None:
        dates = [None] * len(urls)
    return [
        SearchResult(title=f"S{i}", url=u, content="x", published_date=d)
        for i, (u, d) in enumerate(zip(urls, dates), start=1)
    ]


def verification(
    *,
    classification: Classification = Classification.TRUE,
    supporting: list[str] | None = None,
    contradicting: list[str] | None = None,
    agree: int = 2,
    disagree: int = 0,
    is_outdated: bool = False,
) -> VerificationResult:
    return VerificationResult(
        classification=classification,
        explanation="x",
        supporting_urls=supporting or [],
        contradicting_urls=contradicting or [],
        misinformation_patterns=[],
        emotional_language_detected=False,
        is_outdated=is_outdated,
        source_agreement_count=agree,
        source_disagreement_count=disagree,
    )


TIER1 = ["https://www.nih.gov/x", "https://who.int/y", "https://ibge.gov.br/z"]
TIER2 = ["https://bbc.com/a", "https://reuters.com/b"]
UNKNOWN = ["https://random.example/x", "https://blog.example/y"]


class TestRecencyScore:
    def test_within_one_year_returns_one(self):
        assert scorer.recency_score(date_years_ago(0.5)) == 1.0

    def test_one_to_three_years(self):
        assert scorer.recency_score(date_years_ago(2.0)) == 0.75

    def test_three_to_five_years(self):
        assert scorer.recency_score(date_years_ago(4.0)) == 0.50

    def test_over_five_years(self):
        assert scorer.recency_score(date_years_ago(6.0)) == 0.25

    def test_unknown_or_unparseable_is_neutral(self):
        assert scorer.recency_score(None) == 0.50
        assert scorer.recency_score("not-a-date") == 0.50


class TestAgreementRatio:
    @pytest.mark.parametrize(
        "agree, disagree, expected",
        [(0, 0, 0.0), (3, 0, 1.0), (0, 3, 0.0), (2, 2, 0.5), (3, 1, 0.75)],
    )
    def test_ratios(self, agree, disagree, expected):
        assert scorer.agreement_ratio(agree, disagree) == expected


class TestCompute:
    def test_tier1_recent_full_agreement_yields_high_score(self):
        ev = evidence(TIER1, [date_years_ago(0.5)] * 3)
        v = verification(supporting=TIER1, agree=3)
        score, sources = scorer.compute(v, ev)
        assert score >= 0.80
        assert len(sources) == 3

    def test_unknown_sources_lower_than_tier1(self):
        ev_a = evidence(TIER1, [date_years_ago(0.5)] * 3)
        ev_b = evidence(UNKNOWN, [date_years_ago(0.5)] * 2)
        a, _ = scorer.compute(verification(supporting=TIER1, agree=3), ev_a)
        b, _ = scorer.compute(verification(supporting=UNKNOWN, agree=2), ev_b)
        assert b < a

    def test_outdated_penalty(self):
        ev = evidence(TIER1, [date_years_ago(0.5)] * 3)
        a, _ = scorer.compute(verification(supporting=TIER1, agree=3, is_outdated=False), ev)
        b, _ = scorer.compute(verification(supporting=TIER1, agree=3, is_outdated=True), ev)
        assert b == pytest.approx(a * scorer.OUTDATED_PENALTY, abs=0.005)

    def test_unverifiable_capped(self):
        ev = evidence(TIER1, [date_years_ago(0.5)] * 3)
        v = verification(
            classification=Classification.UNVERIFIABLE, supporting=TIER1, agree=3
        )
        score, _ = scorer.compute(v, ev)
        assert score <= scorer.UNVERIFIABLE_CAP

    def test_zero_evidence(self):
        score, sources = scorer.compute(
            verification(supporting=[], agree=0, disagree=0), evidence=[]
        )
        assert score == 0.0
        assert sources == []

    def test_score_clamped_to_unit_interval(self):
        ev = evidence(TIER1, [date_years_ago(0.5)] * 3)
        v = verification(supporting=TIER1, agree=999, disagree=0)
        score, _ = scorer.compute(v, ev)
        assert 0.0 <= score <= 1.0

    def test_sources_deduplicated_by_url(self):
        url = "https://nih.gov/x"
        ev = evidence([url, url], [date_years_ago(0.5), date_years_ago(0.5)])
        v = verification(supporting=[url], agree=1)
        _, sources = scorer.compute(v, ev)
        assert len({s.url for s in sources}) == len(sources)

    def test_supporting_sources_listed_first(self):
        ev = evidence(TIER1 + UNKNOWN, [date_years_ago(0.5)] * 5)
        v = verification(supporting=TIER1, agree=3)
        _, sources = scorer.compute(v, ev)
        # First N sources should be the supporting ones.
        first_three = {s.url for s in sources[:3]}
        assert first_three == set(TIER1)
