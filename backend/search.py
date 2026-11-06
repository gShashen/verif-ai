import asyncio
import bisect
import re

import httpx
import trafilatura
from urllib.parse import urlparse
from models import SearchSource
from tiers import get_tier, _matches_list

SERPER_URL = "https://google.serper.dev/search"
MIN_WORDS_FOR_OVERLAP = 4
PAGE_TIMEOUT = 6.0
PAGE_CHARS = 2000
MIN_PAGE_CHARS = 200
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}
STOPWORDS = {
    "about", "above", "after", "also", "been", "before", "being", "between", "both", "could", "does",
    "during", "each", "from", "have", "having", "into", "more", "most", "much", "only", "other", "over",
    "same", "should", "some", "such", "than", "that", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "under", "very", "what", "when", "where", "which", "while", "will",
    "with", "would", "your",
}
BLOCKED_DOMAINS = {
    "reddit.com",
    "quora.com",
    "medium.com",
    "substack.com",
    "blogspot.com",
    "wordpress.com",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "instagram.com",
    "pinterest.com",
}
# Google sometimes returns redirect links (google.com/goto?url=opaque-token) instead of the real
# page. The real site is unrecoverable, so its domain and tier would be wrong; drop them.
REDIRECT_PATHS = {"/goto", "/url"}

def clean_url(url):
    """Return (domain, path) for a URL: lowercase host without port or leading www./m., path with its case.

    Returns ("", "") when the URL has no usable hostname.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.hostname
    except ValueError:
        return "", ""

    if not domain:
        return "", ""

    if domain.startswith("www."):
        domain = domain[4:]
    elif domain.startswith("m."):
        domain = domain[2:]

    path = parsed.path

    return domain, path

def titles_are_similar(a, b):
    """Return True when at least 80% of the words of the shorter title appear in the other title.

    Case and punctuation are ignored. An empty title is never similar to anything.
    If the shorter title has fewer than MIN_WORDS_FOR_OVERLAP words, the two must have identical
    word sets (a title like "Panama Canal" sits inside almost any longer title).
    """
    words_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    words_b = set(re.findall(r"[a-z0-9]+", b.lower()))

    if not words_a or not words_b:
        return False

    smaller = words_a if len(words_a) <= len(words_b) else words_b
    larger = words_b if len(words_a) <= len(words_b) else words_a

    if len(smaller) < MIN_WORDS_FOR_OVERLAP:
        return words_a == words_b

    similarity = len(smaller & larger) / len(smaller)

    return similarity >= 0.8

class SearchError(Exception):
    """Raised when the Serper search fails; the message is safe to show to a user."""

async def serper_search(client,query,api_key,num=10):
    """Run one Serper search and return the organic results that have a title and a link.

    Raises SearchError on a bad HTTP status, a network error or a non-JSON reply.
    """

    payload = {
            "q": query,
            "num": num,
            "gl": "us",
            "hl": "en"
        }
    
    headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

    try:
        response = await client.post(
            SERPER_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        raise SearchError(f"Search failed with status {e.response.status_code}.") from None
    except httpx.RequestError:
        raise SearchError("Search could not be reached (timeout or network error).") from None
    except ValueError:
        raise SearchError("Search returned an unreadable reply.") from None

    results = []

    for item in data.get("organic",[]):
        if item.get("title") and item.get("link"):
            results.append(
                {
                    "title": item["title"],
                    "link": item["link"],
                    "snippet": item.get("snippet", ""),
                }
            )

    return results
        
def filter_results(results, input_url=None, limit=5):
    """Filter Serper results and return up to `limit` SearchSource objects with tiers attached.

    Drops, in order: links with no hostname, the input URL's domain, blocked sites, a second
    result from the same domain, and titles similar to one already kept. Serper order is kept.
    Only kept results count towards the domain and title checks. text is left empty for the page fetch.
    """
    if input_url:
        input_domain, input_path = clean_url(input_url)
    else:
        input_domain = ""

    kept = []
    seen_domains = set()
    kept_titles = []

    for item in results:
        domain, path = clean_url(item["link"])

        if domain == "":
            continue
        elif input_domain != "" and _matches_list(domain, {input_domain}):
            continue
        elif _matches_list(domain, BLOCKED_DOMAINS):
            continue
        elif domain == "google.com" and path in REDIRECT_PATHS:
            continue
        elif domain in seen_domains:
            continue

        is_duplicate = False
        for title in kept_titles:
            if titles_are_similar(item["title"], title):
                is_duplicate = True
                break

        if is_duplicate:
            continue

        seen_domains.add(domain)
        kept_titles.append(item["title"])
        kept.append(
            SearchSource(
                url=item["link"],
                title=item["title"],
                domain=domain,
                tier=get_tier(domain, path),
                snippet=item.get("snippet", ""),
                text="",
            )
        )

        if len(kept) == limit:
            break

    return kept


def extract_keywords(claim_text):
    """Return the distinctive words of a claim (lowercase, in order, no repeats).

    Words shorter than 4 characters and common stopwords are dropped, but any word with a digit is kept.
    """
    keywords = []

    for word in re.findall(r"[a-z0-9]+", claim_text.lower()):
        if word in keywords or word in STOPWORDS:
            continue
        elif len(word) >= 4 or any(char.isdigit() for char in word):
            keywords.append(word)

    return keywords


def extract_relevant_text(page_text, keywords, max_chars=PAGE_CHARS):
    """Return at most max_chars of page_text, from the window that contains the most keyword matches.

    A page that already fits is returned whole. With no keyword match the start of the page is used.
    """
    if len(page_text) <= max_chars:
        return page_text

    if not keywords:
        return page_text[:max_chars]

    pattern = re.compile("|".join(re.escape(word) for word in keywords), re.IGNORECASE)
    positions = [match.start() for match in pattern.finditer(page_text)]

    if not positions:
        return page_text[:max_chars]

    best_start = 0
    best_count = -1

    for position in positions:
        start = max(0, position - max_chars // 4)
        count = bisect.bisect_left(positions, start + max_chars) - bisect.bisect_left(positions, start)
        if count > best_count:
            best_start = start
            best_count = count

    return page_text[best_start:best_start + max_chars]


async def _download_and_extract(client, url):
    """Download one page and return its main text ("" when it is not an HTML page or has no text)."""
    response = await client.get(url, headers=BROWSER_HEADERS, follow_redirects=True)
    response.raise_for_status()

    if "html" not in response.headers.get("content-type", "").lower():
        return ""

    text = await asyncio.to_thread(trafilatura.extract, response.text)

    if text:
        return text
    else:
        return ""


async def fetch_page_text(client, url, timeout=PAGE_TIMEOUT):
    """Return the main text of a page, or "" on any failure; one bad page must never stop a claim.

    timeout is a hard cap on download plus extraction together.
    """
    try:
        return await asyncio.wait_for(_download_and_extract(client, url), timeout)
    except Exception:
        return ""


async def fetch_sources(client, sources, claim_text, timeout=PAGE_TIMEOUT):
    """Fetch all pages in parallel and return copies of the sources with text filled in.

    text is ~2,000 chars around the claim keywords. When a page failed or has under
    MIN_PAGE_CHARS of text, the Serper snippet is used instead.
    """
    keywords = extract_keywords(claim_text)
    pages = await asyncio.gather(*(fetch_page_text(client, source.url, timeout) for source in sources))

    filled = []

    for source, page in zip(sources, pages):
        if len(page) >= MIN_PAGE_CHARS:
            text = extract_relevant_text(page, keywords)
        else:
            text = source.snippet
        filled.append(source.model_copy(update={"text": text}))

    return filled


async def search_for_claim(client, query, claim_text, api_key, input_url=None):
    """Run the whole search stage for one claim: Serper, filter, tier, fetch page text.

    Returns up to 5 SearchSource objects with text filled in. Raises SearchError if Serper fails.
    """
    results = await serper_search(client, query, api_key)
    sources = filter_results(results, input_url)
    return await fetch_sources(client, sources, claim_text)
