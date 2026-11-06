"""Unit tests for search.py, step 4: cleaning URLs, filtering Serper results, attaching tiers.

No network. Results are hand-made dicts shaped like serper_search output
(title, link, snippet), plus the saved real response in fixtures/serper/01_diamond.json.

Interface these tests expect from search.py:
    BLOCKED_DOMAINS: set[str]     bare domains of user-generated and social sites
    clean_url(url) -> (domain, path)
        domain: lowercase hostname, no port, leading "www." or "m." removed
        path: URL path with original case, no query string
        a link with no hostname gives ("", "")
    titles_are_similar(a, b) -> bool
        lowercase, split into words (letters and digits only); True when at least 80% of the
        words of the shorter title appear in the other title. An empty title is never similar.
    filter_results(results, input_url=None, limit=5) -> list[SearchSource]
        keeps Serper order. Drops, in this order of checks:
          1. links with no hostname
          2. the input URL's domain (and its subdomains)
          3. blocked domains (and their subdomains, not lookalikes)
          4. a second result from the same domain (exact cleaned domain)
          5. a result whose title is similar to a title already kept
        then returns at most `limit` SearchSource objects.
        Each has tier = get_tier(domain, path), snippet = Serper snippet, text = "" (step 5 fills it).
        A dropped result never blocks a later one (only kept results count for steps 4 and 5).
"""

import json
from pathlib import Path

import pytest

from models import SearchSource
from search import BLOCKED_DOMAINS, clean_url, filter_results, titles_are_similar

FIXTURE = Path(__file__).parent / "fixtures" / "serper" / "01_diamond.json"


def result(link, title="Some title", snippet="Some snippet"):
    """Build one Serper-style result dict."""
    return {"title": title, "link": link, "snippet": snippet}


# ---------- clean_url ----------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.example.com/a/b", ("example.com", "/a/b")),
        ("https://WWW.Example.COM/Path", ("example.com", "/Path")),
        ("https://m.youtube.com/watch?v=abc", ("youtube.com", "/watch")),
        ("https://news.bbc.co.uk/story", ("news.bbc.co.uk", "/story")),
        ("https://example.com:8080/x", ("example.com", "/x")),
        ("https://example.com", ("example.com", "")),
        ("https://example.com/", ("example.com", "/")),
        ("https://example.com/page?q=1#top", ("example.com", "/page")),
    ],
)
def test_clean_url(url, expected):
    assert clean_url(url) == expected


@pytest.mark.parametrize("url", ["", "not a url", "/just/a/path"])
def test_clean_url_without_hostname(url):
    assert clean_url(url) == ("", "")


def test_clean_url_only_strips_leading_prefix():
    assert clean_url("https://swww.example.com/")[0] == "swww.example.com"
    assert clean_url("https://mail.example.com/")[0] == "mail.example.com"


# ---------- titles_are_similar ----------


def test_identical_titles_are_similar():
    assert titles_are_similar("Diamond cooling for chips", "Diamond cooling for chips")


def test_case_and_punctuation_are_ignored():
    assert titles_are_similar("Diamond Cooling, for Chips!", "diamond cooling for chips")


def test_source_suffix_still_counts_as_similar():
    # the shorter title (4 words) is fully inside the longer one
    assert titles_are_similar("Diamond cooling for chips", "Diamond cooling for chips - BBC News")


def test_different_titles_are_not_similar():
    assert not titles_are_similar("Diamond cooling for chips", "How copper heat sinks work")


def test_half_overlap_is_not_similar():
    assert not titles_are_similar("alpha beta gamma delta", "alpha beta epsilon zeta")


def test_exactly_eighty_percent_is_similar():
    # 4 of the 5 words of the shorter title appear in the other
    assert titles_are_similar("one two three four five", "one two three four six seven eight")


def test_short_title_inside_a_longer_one_is_not_similar():
    # found at the Day 3 checkpoint: "Panama Canal" made every other Panama Canal title a duplicate
    assert not titles_are_similar("Panama Canal", "Panama Canal | Definition, History, Ownership")


def test_short_titles_with_identical_words_are_similar():
    assert titles_are_similar("Panama Canal", "panama canal!")


def test_empty_title_is_never_similar():
    assert not titles_are_similar("", "anything")
    assert not titles_are_similar("anything", "")
    assert not titles_are_similar("", "")
    assert not titles_are_similar("!!!", "???")


# ---------- the blocklist ----------


def test_blocklist_holds_bare_lowercase_domains():
    for domain in BLOCKED_DOMAINS:
        assert domain == domain.lower()
        assert not domain.startswith("www.")
        assert "/" not in domain


@pytest.mark.parametrize(
    "domain",
    ["reddit.com", "quora.com", "medium.com", "substack.com", "blogspot.com", "wordpress.com",
     "youtube.com", "tiktok.com", "facebook.com", "x.com", "twitter.com", "instagram.com", "pinterest.com"],
)
def test_blocklist_has_the_agreed_sites(domain):
    assert domain in BLOCKED_DOMAINS


@pytest.mark.parametrize(
    "link",
    [
        "https://www.reddit.com/r/science/x",
        "https://old.reddit.com/r/science/x",       # subdomain
        "https://someone.substack.com/p/post",
        "https://myblog.blogspot.com/2024/01/x.html",
        "https://m.youtube.com/watch?v=abc",
        "https://x.com/user/status/1",
    ],
)
def test_blocked_sites_are_dropped(link):
    assert filter_results([result(link)]) == []


@pytest.mark.parametrize("link", ["https://box.com/file", "https://notreddit.com/x", "https://reddit.com.evil.io/x"])
def test_lookalikes_of_blocked_sites_are_kept(link):
    assert len(filter_results([result(link)])) == 1


# ---------- the input URL's domain ----------


def test_input_domain_is_dropped():
    results = [result("https://www.bbc.co.uk/news/a", "A"), result("https://nature.com/b", "B")]
    kept = filter_results(results, input_url="https://www.bbc.co.uk/news/original-article")
    assert [s.domain for s in kept] == ["nature.com"]


def test_input_subdomain_matches_the_same_site():
    results = [result("https://news.bbc.co.uk/a", "A"), result("https://nature.com/b", "B")]
    kept = filter_results(results, input_url="https://bbc.co.uk/news/x")
    assert [s.domain for s in kept] == ["nature.com"]


def test_input_domain_does_not_drop_lookalikes():
    kept = filter_results([result("https://notbbc.co.uk/a")], input_url="https://bbc.co.uk/x")
    assert len(kept) == 1


def test_no_input_url_drops_nothing_extra():
    assert len(filter_results([result("https://bbc.co.uk/a")], input_url=None)) == 1


def test_unparseable_input_url_does_not_crash():
    assert len(filter_results([result("https://bbc.co.uk/a")], input_url="not a url")) == 1


# ---------- one per domain, near-duplicate titles ----------


def test_one_result_per_domain_keeps_the_first():
    results = [
        result("https://nature.com/first", "First article about diamonds"),
        result("https://nature.com/second", "Completely different heat sinks"),
    ]
    kept = filter_results(results)
    assert [s.url for s in kept] == ["https://nature.com/first"]


def test_same_site_different_subdomain_counts_as_different_domain():
    results = [
        result("https://en.wikipedia.org/a", "Diamond"),
        result("https://simple.wikipedia.org/b", "Graphite heat"),
    ]
    assert len(filter_results(results)) == 2


def test_near_duplicate_title_from_another_domain_is_dropped():
    results = [
        result("https://bbc.com/a", "Diamond cooling for chips"),
        result("https://reuters.com/b", "Diamond cooling for chips - Reuters"),
    ]
    kept = filter_results(results)
    assert [s.domain for s in kept] == ["bbc.com"]


def test_dropped_result_does_not_block_a_later_one():
    # second is a duplicate title (dropped); third shares its domain and must survive
    results = [
        result("https://bbc.com/a", "Diamond cooling for chips"),
        result("https://reuters.com/b", "Diamond cooling for chips"),
        result("https://reuters.com/c", "Copper versus aluminium heat sinks"),
    ]
    kept = filter_results(results)
    assert [s.url for s in kept] == ["https://bbc.com/a", "https://reuters.com/c"]


def test_blocked_result_does_not_use_up_its_domain_or_title():
    results = [
        result("https://reddit.com/r/x", "Diamond cooling for chips"),
        result("https://bbc.com/a", "Diamond cooling for chips"),
    ]
    assert [s.domain for s in filter_results(results)] == ["bbc.com"]


# ---------- limit, order, bad rows ----------


def test_limit_defaults_to_five():
    results = [result(f"https://site{i}.com/a", f"unique title number{i} word{i}") for i in range(9)]
    assert len(filter_results(results)) == 5


def test_custom_limit():
    results = [result(f"https://site{i}.com/a", f"unique title number{i} word{i}") for i in range(9)]
    assert len(filter_results(results, limit=2)) == 2


def test_serper_order_is_kept():
    results = [result(f"https://site{i}.com/a", f"unique title number{i} word{i}") for i in range(4)]
    assert [s.domain for s in filter_results(results)] == [f"site{i}.com" for i in range(4)]


def test_empty_input_gives_empty_list():
    assert filter_results([]) == []


def test_link_without_hostname_is_dropped():
    assert filter_results([result("not a url"), result("https://bbc.com/a")])[0].domain == "bbc.com"


# ---------- the output objects ----------


def test_google_redirect_links_are_dropped():
    """Google /goto and /url redirect links hide the real site, so they are dropped."""
    results = [
        result("https://www.google.com/goto?url=CAESaAHEIkXX", title="Redirect one"),
        result("https://www.google.com/url?q=https://example.org/page", title="Redirect two"),
        result("https://example.org/real", title="A real page"),
    ]

    kept = filter_results(results)

    assert [s.url for s in kept] == ["https://example.org/real"]


def test_google_redirect_does_not_use_up_a_slot():
    """A dropped redirect never blocks later results, so the limit is still filled."""
    results = [result("https://www.google.com/goto?url=AAA", title="Redirect")]
    for number in range(5):
        results.append(result(f"https://site{number}.example/page", title=f"Unique title {number} alpha"))

    kept = filter_results(results, limit=5)

    assert len(kept) == 5
    assert all(s.domain != "google.com" for s in kept)


def test_other_google_pages_are_not_dropped():
    """Only the redirect paths are dropped, not every google.com page."""
    results = [result("https://support.google.com/accounts/answer/1", title="Google help")]

    kept = filter_results(results)

    assert len(kept) == 1


def test_output_is_search_source_with_tier_and_empty_text():
    kept = filter_results([result("https://www.who.int/news/x", "WHO says", "WHO snippet")])
    source = kept[0]
    assert isinstance(source, SearchSource)
    assert source.url == "https://www.who.int/news/x"
    assert source.title == "WHO says"
    assert source.domain == "who.int"
    assert source.tier == 1
    assert source.snippet == "WHO snippet"
    assert source.text == ""


def test_tier_uses_the_path_for_personal_academic_pages():
    kept = filter_results([result("https://cs.stanford.edu/~jsmith/notes.html", "Notes")])
    assert kept[0].tier == 3


def test_tiers_for_a_mixed_list():
    results = [
        result("https://www.cdc.gov/a", "CDC page"),
        result("https://www.bbc.com/b", "BBC page"),
        result("https://random-blog.com/c", "Random page"),
    ]
    assert [s.tier for s in filter_results(results)] == [1, 2, 3]


# ---------- the real saved Serper response ----------


def test_real_fixture_filters_cleanly():
    organic = json.loads(FIXTURE.read_text(encoding="utf-8"))["organic"]
    kept = filter_results(organic)

    assert 1 <= len(kept) <= 5
    assert len({s.domain for s in kept}) == len(kept)            # one per domain
    assert all(s.tier in (1, 2, 3) for s in kept)
    assert all("reddit.com" not in s.domain for s in kept)       # result 1 in the fixture is Reddit
    assert all(s.text == "" for s in kept)
