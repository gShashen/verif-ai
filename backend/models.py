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
