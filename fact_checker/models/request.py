from typing import Optional

from pydantic import BaseModel, Field


class FactCheckRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50_000)
    context: Optional[str] = Field(None, max_length=5_000)
    language: str = Field(default="en")
