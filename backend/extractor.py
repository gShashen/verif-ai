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

    video_id = None

    url = _normalize_url(url)
    parsed = urlparse(url)

    if parsed.hostname not in YOUTUBE_HOSTS:
        return None

    if parsed.hostname == "youtu.be":
        video_id = parsed.path.lstrip('/')

    if parsed.path == '/watch':
        video_id = parse_qs(parsed.query).get('v', [None])[0]

    if any(x in parsed.path for x in ['/shorts/', '/embed/', '/live/']):
        video_id = parsed.path.split('/')[-1]

    if video_id is not None and re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        return video_id
    else:
        None