"""FastAPI entry point for the VerifAI backend."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from extractor import ExtractionError, extract_text
from models import ExtractResponse, VerifyRequest

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="VerifAI")


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
