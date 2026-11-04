"""Unit tests for search.py, step 3: the Serper call only (no filtering, no page fetch yet).

No test calls the real API. httpx.MockTransport returns the saved response in
fixtures/serper/01_diamond.json (10 organic results) or a canned error.

Interface these tests expect from search.py:
    SERPER_URL = "https://google.serper.dev/search"
    class SearchError(Exception)          user-facing message, main.py never sees httpx errors
    async serper_search(client, query, api_key, num=10) -> list[dict]
        returns the "organic" list, each dict has at least "title", "link", "snippet"
        results missing "link" or "title" are dropped
        no "organic" key -> []
        raises SearchError on: HTTP status >= 400, timeout/network error, body that is not JSON
Request rules: POST, header X-API-KEY = api_key, JSON body has q, num, gl="us", hl="en".
"""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from search import SERPER_URL, SearchError, serper_search

FIXTURE = Path(__file__).parent / "fixtures" / "serper" / "01_diamond.json"


def make_client(handler):
    """Build an AsyncClient whose requests go to handler instead of the network."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def run_search(handler, query="diamond heat", api_key="test-key", num=10):
    """Run serper_search against a mock handler and return its result."""

    async def go():
        async with make_client(handler) as client:
            return await serper_search(client, query, api_key, num)

    return asyncio.run(go())


def fixture_handler(request):
    """Reply with the saved real Serper response."""
    return httpx.Response(200, json=json.loads(FIXTURE.read_text(encoding="utf-8")))


# ---------- happy path ----------


def test_returns_all_ten_organic_results():
    results = run_search(fixture_handler)
    assert len(results) == 10


def test_results_keep_title_link_snippet():
    results = run_search(fixture_handler)
    first = results[0]
    assert first["link"].startswith("https://")
    assert first["title"]
    assert first["snippet"]


def test_request_is_post_to_serper_with_key_and_body():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("X-API-KEY")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"organic": []})

    run_search(handler, query="panama canal length", api_key="abc123", num=7)

    assert seen["method"] == "POST"
    assert seen["url"] == SERPER_URL
    assert seen["key"] == "abc123"
    assert seen["body"] == {"q": "panama canal length", "num": 7, "gl": "us", "hl": "en"}


# ---------- odd but valid responses ----------


def test_missing_organic_key_gives_empty_list():
    assert run_search(lambda request: httpx.Response(200, json={"credits": 1})) == []


def test_empty_organic_gives_empty_list():
    assert run_search(lambda request: httpx.Response(200, json={"organic": []})) == []


def test_results_without_link_or_title_are_dropped():
    body = {
        "organic": [
            {"title": "Good", "link": "https://a.com/x", "snippet": "s"},
            {"title": "No link", "snippet": "s"},
            {"link": "https://b.com/y", "snippet": "s"},
        ]
    }
    results = run_search(lambda request: httpx.Response(200, json=body))
    assert [r["link"] for r in results] == ["https://a.com/x"]


def test_missing_snippet_becomes_empty_string():
    body = {"organic": [{"title": "T", "link": "https://a.com/x"}]}
    results = run_search(lambda request: httpx.Response(200, json=body))
    assert results[0]["snippet"] == ""


# ---------- failures become SearchError ----------


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
def test_http_error_status_raises_search_error(status):
    with pytest.raises(SearchError):
        run_search(lambda request: httpx.Response(status, json={"message": "nope"}))


def test_timeout_raises_search_error():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(SearchError):
        run_search(handler)


def test_network_error_raises_search_error():
    def handler(request):
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(SearchError):
        run_search(handler)


def test_non_json_body_raises_search_error():
    with pytest.raises(SearchError):
        run_search(lambda request: httpx.Response(200, text="<html>oops</html>"))


def test_error_message_does_not_leak_the_api_key():
    with pytest.raises(SearchError) as info:
        run_search(lambda request: httpx.Response(401, json={}), api_key="SECRET-KEY-123")
    assert "SECRET-KEY-123" not in str(info.value)
