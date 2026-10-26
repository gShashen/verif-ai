"""Unit tests for claims.py: chunking, parsing, retry rule, top-6 selection and error handling.

No test calls the real API. FakeClient stands in for AsyncAnthropic and returns canned replies.

Interface these tests expect from claims.py:
    MODEL, TOOL (dict with "name"), MAX_WORDS (int)
    class ClaimsParseError(Exception)
    count_words(text) -> int
    split_into_chunks(text, max_words=MAX_WORDS) -> list[str]
    parse_tool_response(response) -> ClaimsOutput            raises ClaimsParseError
    select_top_claims(claims, limit=6) -> list[ExtractedClaim]
    async extract_claims_from_chunk(client, text) -> ClaimsOutput   raises ClaimsParseError
    async extract_claims(client, text, max_words=MAX_WORDS) -> (list[ExtractedClaim], list[PipelineError])
"""

import asyncio
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from claims import (
    MODEL,
    TOOL,
    ClaimsParseError,
    count_words,
    extract_claims,
    extract_claims_from_chunk,
    parse_tool_response,
    select_top_claims,
    split_into_chunks,
)
from models import ClaimsOutput, ExtractedClaim, PipelineError

AUTO_CHOICE = {"type": "auto"}
FORCED_CHOICE = {"type": "tool", "name": TOOL["name"]}


# ---------- helpers ----------


def make_claim(text, score=3):
    """Build one claim dict in the shape the tool returns."""
    return {"text": text, "search_query": f"query for {text}", "checkworthiness": score}


def tool_reply(claims):
    """A fake API reply where the model called the tool with these claims."""
    block = SimpleNamespace(type="tool_use", name=TOOL["name"], input={"claims": claims})
    return SimpleNamespace(content=[block], stop_reason="tool_use")


def text_reply(stop_reason="end_turn"):
    """A fake API reply where the model answered in plain text and never called the tool."""
    block = SimpleNamespace(type="text", text="There are no checkable claims here.")
    return SimpleNamespace(content=[block], stop_reason=stop_reason)


def thinking_then_tool_reply(claims):
    """A fake API reply with a thinking block before the tool call."""
    thinking = SimpleNamespace(type="thinking", thinking="")
    tool = SimpleNamespace(type="tool_use", name=TOOL["name"], input={"claims": claims})
    return SimpleNamespace(content=[thinking, tool], stop_reason="tool_use")


THREE_GOOD = [make_claim("Claim A", 5), make_claim("Claim B", 3), make_claim("Claim C", 1)]


class FakeMessages:
    """Records every create() call and returns replies from a list or a function."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    async def create(self, **kwargs):
        """Return the next canned reply, or raise it if it is an exception."""
        self.calls.append(kwargs)
        if callable(self.replies):
            reply = self.replies(kwargs)
        else:
            reply = self.replies[len(self.calls) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeClient:
    """Stands in for AsyncAnthropic: only client.messages.create is used."""

    def __init__(self, replies):
        self.messages = FakeMessages(replies)


def connection_error():
    """An Anthropic API error like the one the SDK raises after its own retries run out."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(request=request)


def words(n, prefix="w"):
    """A text of n distinct words: w0 w1 w2 ..."""
    return " ".join(f"{prefix}{i}" for i in range(n))


# ---------- count_words ----------


def test_count_words_ignores_extra_whitespace():
    assert count_words("  one   two\nthree\tfour  ") == 4


# ---------- split_into_chunks ----------


def test_short_text_is_one_unchanged_chunk():
    text = words(50)
    assert split_into_chunks(text, max_words=100) == [text]


def test_text_exactly_at_cap_is_one_chunk():
    text = words(100)
    assert split_into_chunks(text, max_words=100) == [text]


def test_one_word_over_cap_gives_two_balanced_chunks():
    chunks = split_into_chunks(words(11), max_words=10)
    assert len(chunks) == 2
    assert sorted(count_words(c) for c in chunks) == [5, 6]


def test_long_text_chunks_respect_cap_and_lose_no_words():
    text = words(25)
    chunks = split_into_chunks(text, max_words=10)
    assert len(chunks) == 3
    assert all(count_words(c) <= 10 for c in chunks)
    assert " ".join(chunks) == text


# ---------- parse_tool_response ----------


def test_parse_valid_tool_reply():
    output = parse_tool_response(tool_reply(THREE_GOOD))
    assert isinstance(output, ClaimsOutput)
    assert [c.text for c in output.claims] == ["Claim A", "Claim B", "Claim C"]


def test_parse_accepts_a_single_claim():
    """Option B: a text with only one checkable fact returns one claim instead of padding to 3."""
    output = parse_tool_response(tool_reply([make_claim("Only one")]))
    assert len(output.claims) == 1


def test_parse_finds_tool_block_after_thinking_block():
    output = parse_tool_response(thinking_then_tool_reply(THREE_GOOD))
    assert len(output.claims) == 3


def test_parse_no_tool_block_raises_with_stop_reason():
    with pytest.raises(ClaimsParseError) as exc_info:
        parse_tool_response(text_reply("end_turn"))
    assert "end_turn" in str(exc_info.value)


def test_parse_cut_off_reply_raises_with_stop_reason():
    with pytest.raises(ClaimsParseError) as exc_info:
        parse_tool_response(text_reply("max_tokens"))
    assert "max_tokens" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_claims",
    [
        [],
        [make_claim(f"Claim {i}") for i in range(7)],
        [make_claim("A", 7), make_claim("B"), make_claim("C")],
        [make_claim("A", 0), make_claim("B"), make_claim("C")],
        [make_claim(""), make_claim("B"), make_claim("C")],
        [{"text": "A", "search_query": "q", "check_worthiness": 3}, make_claim("B"), make_claim("C")],
    ],
    ids=["no_claims", "too_many", "score_above_5", "score_below_1", "empty_text", "misnamed_field"],
)
def test_parse_invalid_claims_raise(bad_claims):
    with pytest.raises(ClaimsParseError):
        parse_tool_response(tool_reply(bad_claims))


# ---------- extract_claims_from_chunk: the request ----------


def test_first_call_uses_auto_tool_choice_and_correct_request():
    client = FakeClient([tool_reply(THREE_GOOD)])
    asyncio.run(extract_claims_from_chunk(client, "Some source text."))

    call = client.messages.calls[0]
    assert call["model"] == MODEL
    assert call["tool_choice"] == AUTO_CHOICE
    assert call["tools"] == [TOOL]
    assert call["messages"] == [{"role": "user", "content": "Some source text."}]
    assert call["output_config"] == {"effort": "high"}
    assert "temperature" not in call
    assert "top_p" not in call
    assert "top_k" not in call


def test_good_first_reply_makes_exactly_one_call():
    client = FakeClient([tool_reply(THREE_GOOD)])
    output = asyncio.run(extract_claims_from_chunk(client, "text"))
    assert len(output.claims) == 3
    assert len(client.messages.calls) == 1


# ---------- extract_claims_from_chunk: the retry rule (option b) ----------


def test_no_tool_call_retries_once_with_forced_tool():
    client = FakeClient([text_reply("end_turn"), tool_reply(THREE_GOOD)])
    output = asyncio.run(extract_claims_from_chunk(client, "text"))

    assert len(output.claims) == 3
    assert len(client.messages.calls) == 2
    assert client.messages.calls[0]["tool_choice"] == AUTO_CHOICE
    assert client.messages.calls[1]["tool_choice"] == FORCED_CHOICE


def test_invalid_claims_retry_once_with_forced_tool():
    bad = [make_claim("A", 9), make_claim("B"), make_claim("C")]
    client = FakeClient([tool_reply(bad), tool_reply(THREE_GOOD)])
    output = asyncio.run(extract_claims_from_chunk(client, "text"))

    assert len(output.claims) == 3
    assert client.messages.calls[1]["tool_choice"] == FORCED_CHOICE


def test_two_failures_raise_and_stop_after_two_calls():
    client = FakeClient([text_reply("end_turn"), text_reply("max_tokens"), tool_reply(THREE_GOOD)])
    with pytest.raises(ClaimsParseError):
        asyncio.run(extract_claims_from_chunk(client, "text"))
    assert len(client.messages.calls) == 2


def test_api_error_is_not_retried_by_our_code():
    """The SDK already retries network errors, so our one retry is only for bad output."""
    client = FakeClient([connection_error(), tool_reply(THREE_GOOD)])
    with pytest.raises(anthropic.APIError):
        asyncio.run(extract_claims_from_chunk(client, "text"))
    assert len(client.messages.calls) == 1


# ---------- select_top_claims ----------


def test_select_top_claims_sorts_by_checkworthiness():
    claims = [ExtractedClaim(**make_claim(t, s)) for t, s in [("low", 1), ("high", 5), ("mid", 3)]]
    assert [c.text for c in select_top_claims(claims)] == ["high", "mid", "low"]


def test_select_top_claims_keeps_at_most_limit():
    claims = [ExtractedClaim(**make_claim(f"c{i}", (i % 5) + 1)) for i in range(10)]
    top = select_top_claims(claims, limit=6)
    assert len(top) == 6
    assert min(c.checkworthiness for c in top) >= max(
        c.checkworthiness for c in claims if c not in top
    )


def test_select_top_claims_ties_keep_original_order():
    claims = [ExtractedClaim(**make_claim(t, 4)) for t in ["first", "second", "third"]]
    assert [c.text for c in select_top_claims(claims)] == ["first", "second", "third"]


# ---------- extract_claims: the whole stage, never raises ----------


def test_short_text_success_returns_claims_and_no_errors():
    client = FakeClient([tool_reply(THREE_GOOD)])
    claims, errors = asyncio.run(extract_claims(client, words(50), max_words=100))

    assert [c.text for c in claims] == ["Claim A", "Claim B", "Claim C"]
    assert errors == []
    assert len(client.messages.calls) == 1


def test_short_text_total_failure_returns_empty_claims_and_one_error():
    client = FakeClient([text_reply("end_turn"), text_reply("end_turn")])
    claims, errors = asyncio.run(extract_claims(client, words(50), max_words=100))

    assert claims == []
    assert len(errors) == 1
    assert isinstance(errors[0], PipelineError)
    assert errors[0].stage == "claims"
    assert errors[0].claim_id is None
    assert "end_turn" in errors[0].message


def test_api_error_becomes_pipeline_error_not_crash():
    client = FakeClient([connection_error()])
    claims, errors = asyncio.run(extract_claims(client, words(50), max_words=100))

    assert claims == []
    assert len(errors) == 1
    assert errors[0].stage == "claims"


def test_long_text_is_chunked_one_call_per_chunk():
    client = FakeClient(lambda kwargs: tool_reply(THREE_GOOD))
    asyncio.run(extract_claims(client, words(25), max_words=10))
    assert len(client.messages.calls) == 3


def test_long_text_merges_chunks_and_keeps_top_six_by_score():
    def reply_for_chunk(kwargs):
        """Give each chunk different claims, identified by the first word of the chunk."""
        text = kwargs["messages"][0]["content"]
        if text.startswith("a0"):
            return tool_reply([make_claim("a-5", 5), make_claim("a-2", 2), make_claim("a-1", 1)])
        else:
            return tool_reply([make_claim("b-4", 4), make_claim("b-3", 3), make_claim("b-5", 5)])

    text = words(10, prefix="a") + " " + words(10, prefix="b")
    client = FakeClient(reply_for_chunk)
    claims, errors = asyncio.run(extract_claims(client, text, max_words=10))

    assert errors == []
    assert [c.text for c in claims] == ["a-5", "b-5", "b-4", "b-3", "a-2", "a-1"]


def test_long_text_drops_lowest_when_over_six():
    client = FakeClient(lambda kwargs: tool_reply([make_claim("x", 5), make_claim("y", 3), make_claim("z", 1)]))
    claims, errors = asyncio.run(extract_claims(client, words(25), max_words=10))

    assert errors == []
    assert len(claims) == 6
    assert [c.checkworthiness for c in claims] == [5, 5, 5, 3, 3, 3]


def test_one_failed_chunk_keeps_claims_from_good_chunks():
    def reply_for_chunk(kwargs):
        """The chunk starting with b0 always fails; the other chunk succeeds."""
        text = kwargs["messages"][0]["content"]
        if text.startswith("b0"):
            return text_reply("end_turn")
        else:
            return tool_reply(THREE_GOOD)

    text = words(10, prefix="a") + " " + words(10, prefix="b")
    client = FakeClient(reply_for_chunk)
    claims, errors = asyncio.run(extract_claims(client, text, max_words=10))

    assert [c.text for c in claims] == ["Claim A", "Claim B", "Claim C"]
    assert len(errors) == 1
    assert errors[0].stage == "claims"
    assert errors[0].claim_id is None
