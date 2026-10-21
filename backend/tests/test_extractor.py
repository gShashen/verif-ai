"""Unit tests for YouTube URL parsing in extractor.py."""

import pytest

from extractor import get_youtube_id

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
