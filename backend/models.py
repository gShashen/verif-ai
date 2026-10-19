from typing import Literal

from pydantic import BaseModel


class Source(BaseModel):
    """One web source found for a claim, with its tier and stance."""

    url: str
    title: str
    domain: str
    tier: Literal[1, 2, 3]
    stance: Literal["support", "contradict", "not_addressed"]
    evidence: str


class Claim(BaseModel):
    """One checkable claim with its verdict, confidence and supporting sources."""

    id: int
    text: str
    verdict: Literal["supported", "contradicted", "disputed", "insufficient_evidence"]
    confidence: Literal["high", "medium", "low"]
    explanation: str
    sources: list[Source]
