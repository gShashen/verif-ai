import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def _normalize_url(url: str) -> str:
    """Add https:// to a URL that has no scheme."""
    if url.startswith(("http://", "https://")):
        return url
    return "https://" + url

def detect_source_type(url: str) -> Literal["youtube", "article"]:
    """Return "youtube" if the URL is on a YouTube domain, otherwise "article"."""
    
    url = _normalize_url(url)
    parsed_url = urlparse(url)

    if parsed_url.hostname in YOUTUBE_HOSTS:
        return "youtube"
    else:
        return "article"


def get_youtube_id(url: str) -> str | None:
    """Return the 11-character YouTube video ID from a URL, or None if it is not a YouTube video link."""
    return None
    