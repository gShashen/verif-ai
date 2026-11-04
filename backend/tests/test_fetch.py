"""Unit tests for search.py, step 5: page text fetch and the full search stage for one claim.

No network. httpx.MockTransport serves the saved Serper response and canned HTML pages.

Interface under test (search.py):
    extract_keywords(claim_text) -> list[str]
    extract_relevant_text(page_text, keywords, max_chars=2000) -> str
    async fetch_page_text(client, url, timeout=6.0) -> str          "" on ANY failure
    async fetch_sources(client, sources, claim_text, timeout=6.0) -> list[SearchSource]
    async search_for_claim(client, query, claim_text, api_key, input_url=None) -> list[SearchSource]
"""

import asyncio
import json
import time
from pathlib import Path

import httpx

from models import SearchSource
from search import (
    extract_keywords,
    extract_relevant_text,
    fetch_page_text,
    fetch_sources,
    search_for_claim,
)

FIXTURE = Path(__file__).parent / "fixtures" / "serper" / "01_diamond.json"

PARAGRAPH = (
    "Diamond conducts heat far better than copper, which is why researchers study it for chip cooling. "
    "Its thermal conductivity is roughly 2000 watts per metre kelvin at room temperature, "
    "about five times higher than copper. Engineers are testing diamond layers inside processors. "
)


def html_page(body_text, repeat=3):
    """Wrap text in a minimal article page that trafilatura can read."""
    paragraphs = "".join(f"<p>{body_text}</p>" for _ in range(repeat))
    return f"<html><head><title>T</title></head><body><article><h1>Heading</h1>{paragraphs}</article></body></html>"


def make_source(url="https://example.com/a", snippet="the snippet", tier=3):
    """Build a SearchSource with empty text."""
    return SearchSource(url=url, title="Title", domain="example.com", tier=tier, snippet=snippet, text="")


def run(coro):
    """Run a coroutine to completion."""
    return asyncio.run(coro)


def with_client(handler, func):
    """Run func(client) against a MockTransport client and return its result."""

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await func(client)

    return run(go())


def html_response(text):
    """200 reply with an HTML content type."""
    return httpx.Response(200, text=text, headers={"content-type": "text/html; charset=utf-8"})


# ---------- extract_keywords ----------


def test_keywords_drop_short_words_and_stopwords():
    keywords = extract_keywords("The diamond is one of the best heat conductors that exist")
    assert "diamond" in keywords
    assert "conductors" in keywords
    assert "the" not in keywords
    assert "that" not in keywords


def test_keywords_keep_numbers_even_when_short():
    assert "70" in extract_keywords("Chip temperature fell by 70 degrees")


def test_keywords_are_lowercase_unique_and_in_order():
    assert extract_keywords("Diamond heat DIAMOND copper heat") == ["diamond", "heat", "copper"]


def test_keywords_of_empty_text():
    assert extract_keywords("") == []


# ---------- extract_relevant_text ----------


def test_short_page_is_returned_whole():
    assert extract_relevant_text("short page", ["short"], max_chars=100) == "short page"


def test_long_page_is_cut_to_max_chars():
    page = "filler " * 1000
    assert len(extract_relevant_text(page, ["nothing"], max_chars=500)) == 500


def test_window_is_placed_around_the_keywords():
    page = ("filler " * 500) + "the panama canal is 82 kilometres long " + ("filler " * 500)
    window = extract_relevant_text(page, ["panama", "canal", "kilometres"], max_chars=300)
    assert "panama canal" in window
    assert len(window) == 300


def test_window_with_most_matches_wins_over_a_lone_early_match():
    early = "zebra " + ("filler " * 400)
    late = "zebra giraffe lion tiger zebra giraffe lion tiger"
    page = early + late + (" filler" * 400)
    window = extract_relevant_text(page, ["zebra", "giraffe", "lion", "tiger"], max_chars=200)
    assert "giraffe lion tiger" in window


def test_no_keyword_match_falls_back_to_page_start():
    page = "START " + ("filler " * 1000)
    assert extract_relevant_text(page, ["absent"], max_chars=100).startswith("START")


def test_no_keywords_falls_back_to_page_start():
    page = "START " + ("filler " * 1000)
    assert extract_relevant_text(page, [], max_chars=100).startswith("START")


def test_keyword_match_ignores_case_and_regex_characters():
    page = ("filler " * 500) + "Costs $5.00 (approx) today" + (" filler" * 500)
    assert "$5.00" in extract_relevant_text(page, ["$5.00"], max_chars=100)


# ---------- fetch_page_text ----------


def test_fetch_page_text_returns_article_text():
    text = with_client(lambda request: html_response(html_page(PARAGRAPH)), lambda c: fetch_page_text(c, "https://a.com/x"))
    assert "thermal conductivity" in text


def test_fetch_page_text_sends_a_browser_user_agent():
    seen = {}

    def handler(request):
        seen["agent"] = request.headers.get("user-agent", "")
        return html_response(html_page(PARAGRAPH))

    with_client(handler, lambda c: fetch_page_text(c, "https://a.com/x"))
    assert "Mozilla" in seen["agent"]


def test_fetch_page_text_follows_redirects():
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://a.com/new"})
        return html_response(html_page(PARAGRAPH))

    assert "thermal" in with_client(handler, lambda c: fetch_page_text(c, "https://a.com/old"))


def test_fetch_page_text_http_error_gives_empty_string():
    assert with_client(lambda request: httpx.Response(403), lambda c: fetch_page_text(c, "https://a.com/x")) == ""


def test_fetch_page_text_network_error_gives_empty_string():
    def handler(request):
        raise httpx.ConnectError("no route", request=request)

    assert with_client(handler, lambda c: fetch_page_text(c, "https://a.com/x")) == ""


def test_fetch_page_text_non_html_gives_empty_string():
    def handler(request):
        return httpx.Response(200, content=b"%PDF-1.4 ...", headers={"content-type": "application/pdf"})

    assert with_client(handler, lambda c: fetch_page_text(c, "https://a.com/x.pdf")) == ""


def test_fetch_page_text_page_with_no_text_gives_empty_string():
    assert with_client(lambda request: html_response("<html><body></body></html>"), lambda c: fetch_page_text(c, "https://a.com/x")) == ""


def test_fetch_page_text_hard_timeout():
    async def handler(request):
        await asyncio.sleep(2)
        return html_response(html_page(PARAGRAPH))

    start = time.perf_counter()
    text = with_client(handler, lambda c: fetch_page_text(c, "https://a.com/slow", timeout=0.1))
    assert text == ""
    assert time.perf_counter() - start < 1.0


# ---------- fetch_sources ----------


def test_fetch_sources_fills_text_from_the_page():
    sources = [make_source("https://a.com/1")]
    result = with_client(
        lambda request: html_response(html_page(PARAGRAPH)),
        lambda c: fetch_sources(c, sources, "Diamond conducts heat better than copper"),
    )
    assert "thermal conductivity" in result[0].text
    assert len(result[0].text) <= 2000


def test_fetch_sources_does_not_change_the_input_objects():
    sources = [make_source("https://a.com/1")]
    with_client(lambda request: html_response(html_page(PARAGRAPH)), lambda c: fetch_sources(c, sources, "diamond heat"))
    assert sources[0].text == ""


def test_fetch_sources_falls_back_to_snippet_on_failure():
    sources = [make_source("https://a.com/1", snippet="snippet one")]
    result = with_client(lambda request: httpx.Response(500), lambda c: fetch_sources(c, sources, "diamond heat"))
    assert result[0].text == "snippet one"


def test_fetch_sources_falls_back_to_snippet_when_page_text_is_too_short():
    sources = [make_source("https://a.com/1", snippet="snippet one")]
    tiny = html_page("Cookies.", repeat=1)
    result = with_client(lambda request: html_response(tiny), lambda c: fetch_sources(c, sources, "diamond heat"))
    assert result[0].text == "snippet one"


def test_fetch_sources_one_failure_does_not_affect_the_others():
    def handler(request):
        if request.url.host == "bad.com":
            return httpx.Response(500)
        return html_response(html_page(PARAGRAPH))

    sources = [make_source("https://good.com/1", "s1"), make_source("https://bad.com/2", "s2")]
    result = with_client(handler, lambda c: fetch_sources(c, sources, "diamond heat"))
    assert "thermal" in result[0].text
    assert result[1].text == "s2"


def test_fetch_sources_keeps_order_and_other_fields():
    sources = [make_source(f"https://site{i}.com/a", f"s{i}", tier=(i % 3) + 1) for i in range(5)]
    result = with_client(lambda request: httpx.Response(500), lambda c: fetch_sources(c, sources, "diamond heat"))
    assert [s.url for s in result] == [s.url for s in sources]
    assert [s.tier for s in result] == [s.tier for s in sources]


def test_fetch_sources_runs_pages_in_parallel():
    async def handler(request):
        await asyncio.sleep(0.3)
        return html_response(html_page(PARAGRAPH))

    sources = [make_source(f"https://site{i}.com/a") for i in range(5)]
    start = time.perf_counter()
    with_client(handler, lambda c: fetch_sources(c, sources, "diamond heat"))
    assert time.perf_counter() - start < 1.0          # sequential would be 1.5 s


def test_fetch_sources_empty_list():
    assert with_client(lambda request: httpx.Response(500), lambda c: fetch_sources(c, [], "diamond")) == []


# ---------- search_for_claim ----------


def full_handler(request):
    """Serve the saved Serper response for the search call and an article for every page."""
    if request.url.host == "google.serper.dev":
        return httpx.Response(200, json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    return html_response(html_page(PARAGRAPH))


def test_search_for_claim_returns_up_to_five_tiered_sources_with_text():
    sources = with_client(
        full_handler,
        lambda c: search_for_claim(c, "diamond heat", "Diamond conducts heat better than copper", "key"),
    )
    assert 1 <= len(sources) <= 5
    assert all(s.tier in (1, 2, 3) for s in sources)
    assert all(len(s.text) > 0 for s in sources)
    assert len({s.domain for s in sources}) == len(sources)


def test_search_for_claim_drops_the_input_domain():
    first = json.loads(FIXTURE.read_text(encoding="utf-8"))["organic"][1]["link"]
    host = httpx.URL(first).host.removeprefix("www.")
    sources = with_client(
        full_handler,
        lambda c: search_for_claim(c, "diamond heat", "diamond heat", "key", input_url=f"https://{host}/original"),
    )
    assert all(s.domain != host for s in sources)


def test_search_for_claim_serper_failure_raises_search_error():
    import pytest

    from search import SearchError

    with pytest.raises(SearchError):
        with_client(lambda request: httpx.Response(401, json={}), lambda c: search_for_claim(c, "q", "claim text", "key"))
