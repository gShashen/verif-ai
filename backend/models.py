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


class PipelineError(BaseModel):
    """A failure in one pipeline stage, optionally tied to a specific claim."""

    stage: Literal["extract", "claims", "search", "evaluate"]
    message: str
    claim_id: int | None = None


class VerifyResponse(BaseModel):
    """Full /verify result: the input, its checked claims and any errors."""

    url: str | None
    source_type: Literal["youtube", "article", "text"]
    claims: list[Claim]
    errors: list[PipelineError]
