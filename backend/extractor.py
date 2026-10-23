import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import CouldNotRetrieveTranscript, NoTranscriptFound, YouTubeTranscriptApi

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


class ExtractionError(Exception):
    """Raised when text cannot be extracted from a URL. The message is shown to the user."""


def _normalize_url(url: str) -> str:
    """Add https:// to a URL that has no scheme."""
    if url.startswith(("http://", "https://")):
        return url
    return "https://" + url


def _clean_text(text: str) -> str:
    """Collapse all whitespace (including non-breaking spaces and newlines) into single spaces."""

    return " ".join(text.split())


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

    if parsed.path.startswith(('/shorts/', '/embed/', '/live/')):
        video_id = parsed.path.strip('/').split('/')[1]

    if video_id is not None and re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        return video_id
    else:
        return None


def get_transcript_youtube(video_id: str) -> str:
    """Fetch the English transcript of a YouTube video as one string."""

    ytt_api = YouTubeTranscriptApi()

    try:
        transcript = ytt_api.fetch(video_id, languages=["en"])
    except NoTranscriptFound as err:
        raise ExtractionError("This video has no English transcript.") from err
    except CouldNotRetrieveTranscript as err:
        raise ExtractionError("Couldn't get a transcript for this video.") from err

    text = []

    for snippet in transcript:
        text.append(snippet.text)

    result = " ".join(text)
    result = _clean_text(result)

    if result == "":
        raise ExtractionError("The transcript is empty.")
    else:
        return result