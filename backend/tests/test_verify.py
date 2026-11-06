"""Tests for the /verify endpoint in main.py. Every pipeline stage is faked: no API or network calls.

Contract these tests expect from main.py:
- main.py imports extract_text, extract_claims, search_for_claim, evaluate_claim and SearchError
  at module level (so monkeypatch.setattr(main, "...") works).
- Constants main.SEARCH_TIMEOUT and main.EVALUATE_TIMEOUT (seconds) bound the two per-claim stages.
- Both API keys are read from os.environ inside the handler (not at import time).
- Extraction runs through asyncio.to_thread and its ExtractionError becomes HTTP 422.
- Claim id = position in the claims list + 1.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from extractor import ExtractionError
from models import Claim, ExtractedClaim, PipelineError, SearchSource, Source
from search import SearchError


# ---------- helpers ----------


def make_extracted(number):
    """Build one claim as claims.py returns it."""
    return ExtractedClaim(
        text=f"Claim text {number}",
        search_query=f"query {number}",
        checkworthiness=3,
    )


def make_search_source(number):
    """Build one search source."""
    return SearchSource(
        url=f"https://site{number}.example/page",
        title=f"Title {number}",
        domain=f"site{number}.example",
        tier=3,
        snippet="snippet",
        text="text",
    )


def make_claim(claim_id, text):
    """Build one finished claim as evaluate_claim returns it."""
    return Claim(
        id=claim_id,
        text=text,
        verdict="supported",
        confidence="medium",
        explanation="Because.",
        sources=[
            Source(
                url="https://site1.example/page",
                title="Title 1",
                domain="site1.example",
                tier=3,
                stance="support",
                evidence="Evidence.",
            )
        ],
    )


@pytest.fixture
def client(monkeypatch):
    """TestClient with dummy keys and happy-path fakes for all four stages."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-key")

    calls = {"search": [], "evaluate": []}

    def fake_extract_text(url, text):
        return ("article", "Some long article text.")

    async def fake_extract_claims(anthropic_client, text):
        return [make_extracted(1), make_extracted(2), make_extracted(3)], []

    async def fake_search_for_claim(http_client, query, claim_text, api_key, input_url=None):
        calls["search"].append({"query": query, "claim_text": claim_text, "input_url": input_url})
        return [make_search_source(1)]

    async def fake_evaluate_claim(anthropic_client, claim_id, claim_text, sources):
        calls["evaluate"].append(claim_id)
        return make_claim(claim_id, claim_text), []

    monkeypatch.setattr(main, "extract_text", fake_extract_text)
    monkeypatch.setattr(main, "extract_claims", fake_extract_claims)
    monkeypatch.setattr(main, "search_for_claim", fake_search_for_claim)
    monkeypatch.setattr(main, "evaluate_claim", fake_evaluate_claim)

    test_client = TestClient(main.app)
    test_client.calls = calls
    return test_client


URL_BODY = {"url": "https://example.com/article"}


# ---------- happy path ----------


def test_happy_path_returns_all_claims_in_order(client):
    """Three claims in, three claims out, same order, no errors."""
    response = client.post("/verify", json=URL_BODY)

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/article"
    assert data["source_type"] == "article"
    assert [c["text"] for c in data["claims"]] == ["Claim text 1", "Claim text 2", "Claim text 3"]
    assert data["errors"] == []


def test_claim_ids_are_index_plus_one(client):
    """Ids are 1, 2, 3 in claim order."""
    response = client.post("/verify", json=URL_BODY)

    assert [c["id"] for c in response.json()["claims"]] == [1, 2, 3]
    assert sorted(client.calls["evaluate"]) == [1, 2, 3]


def test_response_has_frozen_shape(client):
    """Top-level and claim keys match the frozen response shape."""
    data = client.post("/verify", json=URL_BODY).json()

    assert set(data.keys()) == {"url", "source_type", "claims", "errors"}
    assert set(data["claims"][0].keys()) == {
        "id", "text", "verdict", "confidence", "explanation", "sources",
    }
    assert set(data["claims"][0]["sources"][0].keys()) == {
        "url", "title", "domain", "tier", "stance", "evidence",
    }


def test_search_gets_query_claim_text_and_input_url(client):
    """Each claim is searched with its own query and the input URL for domain filtering."""
    client.post("/verify", json=URL_BODY)

    searched = client.calls["search"]
    assert len(searched) == 3
    assert {s["query"] for s in searched} == {"query 1", "query 2", "query 3"}
    assert {s["claim_text"] for s in searched} == {"Claim text 1", "Claim text 2", "Claim text 3"}
    assert all(s["input_url"] == "https://example.com/article" for s in searched)


def test_pasted_text_passes_no_input_url(client, monkeypatch):
    """For pasted text the response url is null and search gets input_url=None."""
    monkeypatch.setattr(main, "extract_text", lambda url, text: ("text", text))

    response = client.post("/verify", json={"text": "x" * 200})

    assert response.status_code == 200
    data = response.json()
    assert data["url"] is None
    assert data["source_type"] == "text"
    assert all(s["input_url"] is None for s in client.calls["search"])


# ---------- extraction failure ----------


def test_extraction_error_returns_422(client, monkeypatch):
    """ExtractionError becomes 422 with the user-facing message, like /extract."""

    def fail(url, text):
        raise ExtractionError("This video has no captions.")

    monkeypatch.setattr(main, "extract_text", fail)

    response = client.post("/verify", json=URL_BODY)

    assert response.status_code == 422
    assert "no captions" in response.json()["detail"]


def test_invalid_request_returns_422(client):
    """Sending neither url nor text is rejected by VerifyRequest."""
    response = client.post("/verify", json={})

    assert response.status_code == 422


# ---------- claims stage ----------


def test_zero_claims_skips_search_and_evaluate(client, monkeypatch):
    """No claims: 200, empty claims list, the claims error is passed through, nothing searched."""

    async def no_claims(anthropic_client, text):
        error = PipelineError(stage="claims", message="Could not extract claims from this text: boom")
        return [], [error]

    monkeypatch.setattr(main, "extract_claims", no_claims)

    response = client.post("/verify", json=URL_BODY)

    assert response.status_code == 200
    data = response.json()
    assert data["claims"] == []
    assert len(data["errors"]) == 1
    assert data["errors"][0]["stage"] == "claims"
    assert client.calls["search"] == []
    assert client.calls["evaluate"] == []


def test_claims_stage_errors_are_kept_alongside_claims(client, monkeypatch):
    """A partial claims failure (one chunk) keeps the good claims and the error."""

    async def partial(anthropic_client, text):
        error = PipelineError(stage="claims", message="Could not extract claims from part 2 of 2: boom")
        return [make_extracted(1)], [error]

    monkeypatch.setattr(main, "extract_claims", partial)

    data = client.post("/verify", json=URL_BODY).json()

    assert len(data["claims"]) == 1
    assert [e["stage"] for e in data["errors"]] == ["claims"]


# ---------- per-claim failures ----------


def test_search_error_on_one_claim_does_not_kill_the_others(client, monkeypatch):
    """Claim 2 fails in search: claims 1 and 3 still return, one search error with claim_id 2."""

    async def flaky_search(http_client, query, claim_text, api_key, input_url=None):
        if query == "query 2":
            raise SearchError("Serper returned 500")
        return [make_search_source(1)]

    monkeypatch.setattr(main, "search_for_claim", flaky_search)

    data = client.post("/verify", json=URL_BODY).json()

    assert [c["id"] for c in data["claims"]] == [1, 3]
    assert len(data["errors"]) == 1
    assert data["errors"][0]["stage"] == "search"
    assert data["errors"][0]["claim_id"] == 2
    assert 2 not in client.calls["evaluate"]


def test_evaluate_error_on_one_claim_is_reported(client, monkeypatch):
    """evaluate_claim returns (None, [error]) for claim 3: that claim is dropped, its error kept."""

    async def flaky_evaluate(anthropic_client, claim_id, claim_text, sources):
        if claim_id == 3:
            error = PipelineError(stage="evaluate", message="Could not evaluate this claim: x", claim_id=3)
            return None, [error]
        return make_claim(claim_id, claim_text), []

    monkeypatch.setattr(main, "evaluate_claim", flaky_evaluate)

    data = client.post("/verify", json=URL_BODY).json()

    assert [c["id"] for c in data["claims"]] == [1, 2]
    assert [(e["stage"], e["claim_id"]) for e in data["errors"]] == [("evaluate", 3)]


def test_search_timeout_becomes_search_error(client, monkeypatch):
    """A search that hangs past SEARCH_TIMEOUT is cancelled and reported as a search error."""

    async def slow_search(http_client, query, claim_text, api_key, input_url=None):
        if query == "query 1":
            await asyncio.sleep(5)
        return [make_search_source(1)]

    monkeypatch.setattr(main, "search_for_claim", slow_search)
    monkeypatch.setattr(main, "SEARCH_TIMEOUT", 0.05)

    data = client.post("/verify", json=URL_BODY).json()

    assert [c["id"] for c in data["claims"]] == [2, 3]
    assert [(e["stage"], e["claim_id"]) for e in data["errors"]] == [("search", 1)]


def test_evaluate_timeout_becomes_evaluate_error(client, monkeypatch):
    """An evaluation that hangs past EVALUATE_TIMEOUT is cancelled and reported as an evaluate error."""

    async def slow_evaluate(anthropic_client, claim_id, claim_text, sources):
        if claim_id == 2:
            await asyncio.sleep(5)
        return make_claim(claim_id, claim_text), []

    monkeypatch.setattr(main, "evaluate_claim", slow_evaluate)
    monkeypatch.setattr(main, "EVALUATE_TIMEOUT", 0.05)

    data = client.post("/verify", json=URL_BODY).json()

    assert [c["id"] for c in data["claims"]] == [1, 3]
    assert [(e["stage"], e["claim_id"]) for e in data["errors"]] == [("evaluate", 2)]


def test_claims_run_concurrently(client, monkeypatch):
    """All three evaluations are in flight at the same time (peak of 3), so claims are not sequential."""
    state = {"running": 0, "peak": 0}

    async def slow_evaluate(anthropic_client, claim_id, claim_text, sources):
        state["running"] += 1
        state["peak"] = max(state["peak"], state["running"])
        await asyncio.sleep(0.1)
        state["running"] -= 1
        return make_claim(claim_id, claim_text), []

    monkeypatch.setattr(main, "evaluate_claim", slow_evaluate)

    response = client.post("/verify", json=URL_BODY)

    assert len(response.json()["claims"]) == 3
    assert state["peak"] == 3


def test_http_client_uses_explicit_timeout(client, monkeypatch):
    """The shared httpx client is built with main.HTTP_TIMEOUT, not httpx's 5 s default."""
    seen = {}
    real_client = main.httpx.AsyncClient

    def recording_client(*args, **kwargs):
        seen.update(kwargs)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(main.httpx, "AsyncClient", recording_client)

    client.post("/verify", json=URL_BODY)

    assert seen.get("timeout") == main.HTTP_TIMEOUT
    assert main.HTTP_TIMEOUT > 5


# ---------- CORS ----------


def test_cors_allows_vite_dev_origin(client):
    """A preflight from the Vite dev server gets an allow-origin header."""
    response = client.options(
        "/verify",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
