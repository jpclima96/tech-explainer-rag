from datetime import datetime, timedelta, timezone

import pytest

from fact_checker.models.response import Classification
from fact_checker.retriever import SearchResult
from fact_checker.scorer import (
    Scorer,
    _OUTDATED_PENALTY,
    _UNVERIFIABLE_CAP,
    _agreement_ratio,
    _recency_score,
)
from fact_checker.verifier import VerificationResult


def _date_years_ago(years: float) -> str:
    dt = datetime.now(tz=timezone.utc) - timedelta(days=int(years * 365.25))
    return dt.strftime("%Y-%m-%d")


def make_evidence(urls: list[str], dates: list[str | None] | None = None) -> list[SearchResult]:
    if dates is None:
        dates = [None] * len(urls)
    return [
        SearchResult(title=f"Source {i}", url=url, content="Content.", published_date=date)
        for i, (url, date) in enumerate(zip(urls, dates), start=1)
    ]


def make_verification(
    classification: Classification = Classification.TRUE,
    supporting_urls: list[str] | None = None,
    contradicting_urls: list[str] | None = None,
    agree: int = 2,
    disagree: int = 0,
    is_outdated: bool = False,
) -> VerificationResult:
    return VerificationResult(
        classification=classification,
        explanation="Test.",
        supporting_urls=supporting_urls or [],
        contradicting_urls=contradicting_urls or [],
        misinformation_patterns=[],
        emotional_language_detected=False,
        is_outdated=is_outdated,
        source_agreement_count=agree,
        source_disagreement_count=disagree,
    )


TIER1_URLS = [
    "https://www.nih.gov/vaccine-history",
    "https://who.int/news",
    "https://ibge.gov.br/stats",
]
TIER2_URLS = [
    "https://bbc.com/news/article",
    "https://reuters.com/business",
]
UNKNOWN_URLS = [
    "https://randomblog.com/post",
    "https://forum.example.com/thread",
]


class TestAgreementRatio:
    @pytest.mark.parametrize(
        "agree, disagree, expected",
        [
            (0, 0, 0.0),
            (3, 0, 1.0),
            (0, 3, 0.0),
            (2, 2, 0.5),
            (1, 3, 0.25),
            (3, 1, 0.75),
        ],
    )
    def test_parametrized(self, agree: int, disagree: int, expected: float):
        assert _agreement_ratio(agree, disagree) == expected


class TestRecencyScore:
    def test_within_one_year(self):
        assert _recency_score(_date_years_ago(0.5)) == 1.0

    def test_one_to_three_years(self):
        assert _recency_score(_date_years_ago(2.0)) == 0.75

    def test_three_to_five_years(self):
        assert _recency_score(_date_years_ago(4.0)) == 0.50

    def test_over_five_years(self):
        assert _recency_score(_date_years_ago(6.0)) == 0.25

    def test_unknown_date_returns_neutral(self):
        assert _recency_score(None) == 0.50

    def test_unparseable_date_returns_neutral(self):
        assert _recency_score("not-a-date") == 0.50


class TestScorer:
    def test_tier1_sources_produce_high_credibility(self):
        scorer = Scorer()
        recent = _date_years_ago(0.5)
        evidence = make_evidence(TIER1_URLS, [recent] * 3)
        verification = make_verification(
            supporting_urls=TIER1_URLS,
            agree=3,
            disagree=0,
        )
        confidence, sources = scorer.compute(verification, evidence)
        # Tier 1 + recent + full agreement should yield high confidence
        assert confidence >= 0.80

    def test_unknown_sources_produce_lower_confidence_than_tier1(self):
        scorer = Scorer()
        recent = _date_years_ago(0.5)
        evidence_tier1 = make_evidence(TIER1_URLS, [recent] * 3)
        evidence_unknown = make_evidence(UNKNOWN_URLS, [recent] * 2)
        v_tier1 = make_verification(supporting_urls=TIER1_URLS, agree=3)
        v_unknown = make_verification(supporting_urls=UNKNOWN_URLS, agree=2)

        conf_tier1, _ = scorer.compute(v_tier1, evidence_tier1)
        conf_unknown, _ = scorer.compute(v_unknown, evidence_unknown)

        assert conf_unknown < conf_tier1

    def test_is_outdated_applies_penalty(self):
        scorer = Scorer()
        recent = _date_years_ago(0.5)
        evidence = make_evidence(TIER1_URLS, [recent] * 3)

        v_fresh = make_verification(supporting_urls=TIER1_URLS, agree=3, is_outdated=False)
        v_old = make_verification(supporting_urls=TIER1_URLS, agree=3, is_outdated=True)

        conf_fresh, _ = scorer.compute(v_fresh, evidence)
        conf_old, _ = scorer.compute(v_old, evidence)

        assert conf_old == pytest.approx(conf_fresh * _OUTDATED_PENALTY, abs=0.01)

    def test_unverifiable_capped_at_threshold(self):
        scorer = Scorer()
        recent = _date_years_ago(0.5)
        evidence = make_evidence(TIER1_URLS, [recent] * 3)
        verification = make_verification(
            classification=Classification.UNVERIFIABLE,
            supporting_urls=TIER1_URLS,
            agree=3,
        )
        confidence, _ = scorer.compute(verification, evidence)
        assert confidence <= _UNVERIFIABLE_CAP

    def test_zero_sources_gives_zero_agreement(self):
        scorer = Scorer()
        evidence: list[SearchResult] = []
        verification = make_verification(
            supporting_urls=[],
            contradicting_urls=[],
            agree=0,
            disagree=0,
        )
        confidence, sources = scorer.compute(verification, evidence)
        assert confidence == 0.0
        assert sources == []

    def test_confidence_is_clamped_to_zero_one(self):
        scorer = Scorer()
        evidence = make_evidence(TIER1_URLS)
        verification = make_verification(supporting_urls=TIER1_URLS, agree=100, disagree=0)
        confidence, _ = scorer.compute(verification, evidence)
        assert 0.0 <= confidence <= 1.0

    def test_sources_list_populated(self):
        scorer = Scorer()
        evidence = make_evidence(TIER1_URLS[:2], [_date_years_ago(0.5), _date_years_ago(1.5)])
        verification = make_verification(supporting_urls=TIER1_URLS[:2])
        _, sources = scorer.compute(verification, evidence)
        assert len(sources) == 2
        assert all(0.0 <= s.credibility_score <= 1.0 for s in sources)

    def test_sources_no_duplicates(self):
        dup_url = "https://www.nih.gov/page"
        evidence = make_evidence([dup_url, dup_url])
        verification = make_verification(supporting_urls=[dup_url], agree=1)
        scorer = Scorer()
        _, sources = scorer.compute(verification, evidence)
        urls = [s.url for s in sources]
        assert len(urls) == len(set(urls))

    def test_confidence_rounded_to_four_decimals(self):
        scorer = Scorer()
        evidence = make_evidence(TIER2_URLS, ["2024-01-01"] * 2)
        verification = make_verification(supporting_urls=TIER2_URLS, agree=2)
        confidence, _ = scorer.compute(verification, evidence)
        assert confidence == round(confidence, 4)

    def test_false_classification_with_full_disagreement(self):
        scorer = Scorer()
        evidence = make_evidence(TIER2_URLS, [_date_years_ago(0.5)] * 2)
        verification = make_verification(
            classification=Classification.FALSE,
            supporting_urls=[],
            contradicting_urls=TIER2_URLS,
            agree=0,
            disagree=2,
        )
        confidence, _ = scorer.compute(verification, evidence)
        # With zero agreement, agreement component = 0, so confidence should be low
        assert confidence < 0.40
