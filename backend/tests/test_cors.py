"""Unit tests for the CORS origin list built from the FRONTEND_ORIGINS setting."""

from main import LOCAL_ORIGINS, build_allowed_origins


def test_empty_setting_gives_only_local_origins():
    assert build_allowed_origins("") == LOCAL_ORIGINS


def test_extra_origin_is_added_after_local_ones():
    result = build_allowed_origins("https://verifai.vercel.app")
    assert result == LOCAL_ORIGINS + ["https://verifai.vercel.app"]


def test_comma_list_trailing_slash_and_blanks_are_cleaned():
    result = build_allowed_origins(" https://a.vercel.app/ , ,https://b.com ")
    assert result[len(LOCAL_ORIGINS):] == ["https://a.vercel.app", "https://b.com"]


def test_duplicates_are_not_added_twice():
    result = build_allowed_origins("http://localhost:5173,https://a.vercel.app,https://a.vercel.app")
    assert result.count("http://localhost:5173") == 1
    assert result.count("https://a.vercel.app") == 1
