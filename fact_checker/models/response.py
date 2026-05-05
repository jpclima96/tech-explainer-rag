from enum import Enum

from pydantic import BaseModel, Field


class Classification(str, Enum):
    TRUE = "true"
    FALSE = "false"
    MISLEADING = "misleading"
    UNVERIFIABLE = "unverifiable"


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


class FactCheckResponse(BaseModel):
    claims: list[Claim]
    overall_assessment: str
    misinformation_patterns: list[str] = Field(default_factory=list)
    emotional_manipulation_detected: bool = False
