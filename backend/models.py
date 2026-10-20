from typing import Literal

from pydantic import BaseModel, model_validator


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


class VerifyRequest(BaseModel):
    """Input to /verify: exactly one of a URL or pasted text."""

    url: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def check_exactly_one_input(self):
        """Treat blank strings as missing, then require exactly one input."""
        if self.text is not None:
            self.text = self.text.strip() or None

        if self.url is not None:
            self.url = self.url.strip() or None

        if self.url is None and self.text is None:
            raise ValueError("Provide a URL or some text to check.")
        elif self.url and self.text:
            raise ValueError("Provide either a URL or text, not both.")

        return self
