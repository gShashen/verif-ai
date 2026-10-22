"""Unit tests for URL type detection and YouTube ID parsing in extractor.py."""

import pytest

from extractor import detect_source_type, get_youtube_id

VIDEO_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com/watch?v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42s",
        f"https://www.youtube.com/watch?feature=share&v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}?si=AbC123xyz",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://youtube.com/shorts/{VIDEO_ID}?feature=share",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}?si=AbC123xyz",
        f"https://www.youtube.com/shorts/{VIDEO_ID}/",
        f"https://www.youtube.com/embed/{VIDEO_ID}/extra",
        f"http://youtu.be/{VIDEO_ID}",
        f"https://YouTu.be/{VIDEO_ID}",
        f"youtu.be/{VIDEO_ID}",
        f"www.youtube.com/watch?v={VIDEO_ID}",
    ],
)
def test_valid_youtube_urls_return_id(url):
    assert get_youtube_id(url) == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        "https://www.bbc.co.uk/news/articles/c1234567890o",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/@SomeChannel",
        "https://youtu.be/abc",
        f"https://notyoutube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com.evil.example/watch?v={VIDEO_ID}",
        "",
    ],
)
def test_non_youtube_or_invalid_urls_return_none(url):
    assert get_youtube_id(url) is None


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"youtu.be/{VIDEO_ID}",
        "https://m.youtube.com/shorts/abc",
        "https://www.youtube.com/@SomeChannel",
        "https://www.youtube.com/",
    ],
)
def test_youtube_hosts_detected_as_youtube(url):
    assert detect_source_type(url) == "youtube"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.bbc.co.uk/news/articles/c1234567890o",
        "example.com/some-article",
        f"https://notyoutube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com.evil.example/watch?v={VIDEO_ID}",
    ],
)
def test_other_hosts_detected_as_article(url):
    assert detect_source_type(url) == "article"
