from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Classification(str, Enum):
    TRUE = "true"
    FALSE = "false"
    MISLEADING = "misleading"
    UNVERIFIABLE = "unverifiable"


class MisinformationPattern(str, Enum):
    CHERRY_PICKING = "cherry_picking"
    MISSING_CONTEXT = "missing_context"
    STATISTICAL_MANIPULATION = "statistical_manipulation"
    OUTDATED_INFO = "outdated_info"
    FALSE_EQUIVALENCE = "false_equivalence"


class Source(BaseModel):
    title: str
    url: str
    credibility_score: float = Field(ge=0.0, le=1.0)


class Claim(BaseModel):
    claim: str
    classification: Classification
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    sources: list[Source]


class FactCheckRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50_000)
    context: Optional[str] = Field(default=None, max_length=5_000)
    language: str = Field(default="en")


class FactCheckResponse(BaseModel):
    claims: list[Claim]
    overall_assessment: str
    misinformation_patterns: list[str] = Field(default_factory=list)
    emotional_manipulation_detected: bool = False


# --- Internal models (not part of public API contract) ---


class SearchResult(BaseModel):
    """Raw evidence returned by the retriever."""

    title: str
    url: str
    content: str
    published_date: Optional[str] = None


class VerificationResult(BaseModel):
    """LLM-produced verification record for a single claim."""

    classification: Classification
    explanation: str
    supporting_urls: list[str] = Field(default_factory=list)
    contradicting_urls: list[str] = Field(default_factory=list)
    misinformation_patterns: list[str] = Field(default_factory=list)
    emotional_language_detected: bool = False
    is_outdated: bool = False
    source_agreement_count: int = 0
    source_disagreement_count: int = 0
