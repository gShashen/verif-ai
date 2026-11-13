import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

import trafilatura
from newspaper import Article, ArticleException
from youtube_transcript_api import CouldNotRetrieveTranscript, NoTranscriptFound, RequestBlocked, YouTubeTranscriptApi, TranscriptsDisabled

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
MIN_ARTICLE_CHARS = 500
MIN_TEXT_CHARS = 100


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


def _extract_with_trafilatura(url: str) -> str | None:
    """Download and extract article text with trafilatura, or return None if either step fails."""
    downloaded = trafilatura.fetch_url(url)

    if downloaded:
        extracted = trafilatura.extract(downloaded,include_comments=False)
        return extracted
    else:
        return None


def _extract_with_newspaper(url: str) -> str | None:
    """Download and extract article text with newspaper4k, or return None if it fails."""
    article = Article(url)
    try:
        article.download()
        article.parse()
        return article.text
    except ArticleException:
        return None


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
    except TranscriptsDisabled as err:
        raise ExtractionError("This video has no captions.") from err
    except RequestBlocked as err:
        # Must come before CouldNotRetrieveTranscript: RequestBlocked (and IpBlocked) are subclasses of it.
        raise ExtractionError("YouTube is blocking our server right now. Paste the video's transcript as text instead.") from err
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


def get_article_text(url: str) -> str:
    """Return cleaned article text, trying trafilatura then newspaper4k; raise ExtractionError if both fail."""
    url = _normalize_url(url)

    trafilatura_extraction = _extract_with_trafilatura(url)

    if trafilatura_extraction is None or len(_clean_text(trafilatura_extraction)) < MIN_ARTICLE_CHARS:
        newspaper_extraction = _extract_with_newspaper(url)
        if newspaper_extraction is None or len(_clean_text(newspaper_extraction)) < MIN_ARTICLE_CHARS:
            raise ExtractionError("Couldn't read the article at this link. Try pasting the text instead.")
        else:
            result = _clean_text(newspaper_extraction)
            return result
    else:
        result = _clean_text(trafilatura_extraction)
        return result

def extract_text(url: str | None, text: str | None) -> tuple[Literal["youtube", "article", "text"], str]:
    """Return (source_type, cleaned_text) for either a URL or pasted text."""

    if text is not None:
        text = _clean_text(text)
        if len(text) < MIN_TEXT_CHARS:
            raise ExtractionError("Paste at least a couple of sentences to check.")
        else:
            return "text", text

    source_type = detect_source_type(url)

    if source_type == "youtube":
        yt_id = get_youtube_id(url)

        if yt_id is None:
            raise ExtractionError("That YouTube link isn't a video.")
        else:
            yt_transcript = get_transcript_youtube(yt_id)
            return "youtube", yt_transcript
    else:
        article_text = get_article_text(url)
        return "article", article_text