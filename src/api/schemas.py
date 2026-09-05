"""Request and response schemas for the STOCKSENSE AI API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CopilotRequest(BaseModel):
    """A non-empty natural-language retail question."""

    question: str = Field(..., min_length=1, max_length=1_000)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be empty")
        return value


class PolicyEvidence(BaseModel):
    """A policy citation supplied by the Gemini grounding response."""

    policy_id: str
    source: str
    reason: str


class CopilotResponse(BaseModel):
    """Grounded response contract, including controlled non-sensitive failures."""

    answer: str
    key_facts: list[str] = Field(default_factory=list)
    recommendation: str
    evidence: list[PolicyEvidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    status: str = "ok"
