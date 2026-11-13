"""FastAPI entry point for the VerifAI backend."""

import asyncio
import os
from pathlib import Path

import anthropic
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from claims import extract_claims
from evaluator import evaluate_claim
from extractor import ExtractionError, extract_text
from models import ExtractResponse, PipelineError, VerifyRequest, VerifyResponse
from search import SearchError, search_for_claim

load_dotenv(Path(__file__).parent / ".env")

SEARCH_TIMEOUT = 20
EVALUATE_TIMEOUT = 30
HTTP_TIMEOUT = 15  # seconds per Serper request; httpx's default of 5 s timed out under parallel load

app = FastAPI(title="VerifAI")

LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def build_allowed_origins(extra_origins):
    """Return the CORS origins: the two local dev origins plus any comma-separated extras.

    extra_origins is the FRONTEND_ORIGINS setting (for example the Vercel URL). Blanks are
    skipped and a trailing slash is removed, because browsers send origins without one.
    """
    origins = list(LOCAL_ORIGINS)

    for origin in extra_origins.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned and cleaned not in origins:
            origins.append(cleaned)

    return origins


ALLOWED_ORIGINS = build_allowed_origins(os.getenv("FRONTEND_ORIGINS", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    """Simple liveness check for local testing and the deploy platform."""
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractResponse)
def extract(request: VerifyRequest) -> ExtractResponse:
    """Return the cleaned text for a URL or pasted text, without checking any claims."""
    try:
        source_type, extracted_text = extract_text(request.url, request.text)
    except ExtractionError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    word_count = len(extracted_text.split())
    response = ExtractResponse(url=request.url, source_type=source_type, text=extracted_text, word_count=word_count)

    return response



async def process_claim(anthropic_client, http_client, serper_key, claim_id, extracted, input_url):
    """Search and evaluate one claim; return (Claim or None, errors) and never raise for stage failures.

    A search failure or timeout skips evaluation. Any failure is reported as a PipelineError
    tied to claim_id, so the other claims running in the same gather are unaffected.
    """
    claim = None
    errors = []
    sources = None

    try:
        sources = await asyncio.wait_for(
            search_for_claim(http_client, extracted.search_query, extracted.text, serper_key, input_url),
            SEARCH_TIMEOUT,
        )
    except asyncio.TimeoutError:
        errors.append(
            PipelineError(stage="search", message="Searching for sources took too long.", claim_id=claim_id)
        )
    except SearchError as err:
        errors.append(
            PipelineError(stage="search", message=f"Could not search for this claim: {err}", claim_id=claim_id)
        )

    if sources is not None:
        try:
            claim, evaluate_errors = await asyncio.wait_for(
                evaluate_claim(anthropic_client, claim_id, extracted.text, sources),
                EVALUATE_TIMEOUT,
            )
            errors.extend(evaluate_errors)
        except asyncio.TimeoutError:
            errors.append(
                PipelineError(stage="evaluate", message="Evaluating this claim took too long.", claim_id=claim_id)
            )

    return claim, errors


@app.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest) -> VerifyResponse:
    """Run the full pipeline for a URL or pasted text and return one verdict per claim."""
    try:
        source_type, text = await asyncio.to_thread(extract_text, request.url, request.text)
    except ExtractionError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    serper_key = os.environ["SERPER_API_KEY"]

    async with anthropic.AsyncAnthropic() as anthropic_client, httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http_client:
        extracted_claims, errors = await extract_claims(anthropic_client, text)

        if len(extracted_claims) > 0:
            results = await asyncio.gather(
                *[
                    process_claim(anthropic_client, http_client, serper_key, index + 1, extracted, request.url)
                    for index, extracted in enumerate(extracted_claims)
                ]
            )
        else:
            results = []

    claims = []
    for claim, claim_errors in results:
        if claim is not None:
            claims.append(claim)
        errors.extend(claim_errors)

    return VerifyResponse(url=request.url, source_type=source_type, claims=claims, errors=errors)
