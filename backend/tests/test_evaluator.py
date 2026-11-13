"""Tests for evaluator.py with a fake client (no API calls)."""

import asyncio
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from evaluator import (
    EvaluationParseError,
    PROMPT,
    TOOL,
    build_claim,
    build_user_message,
    evaluate_claim,
    parse_evaluation,
)
from models import EvaluationOutput, SearchSource


# ---------- helpers ----------


def make_source(number, tier=3):
    """Build one search source."""
    return SearchSource(
        url=f"https://site{number}.example/page",
        title=f"Title {number}",
        domain=f"site{number}.example",
        tier=tier,
        snippet=f"snippet {number}",
        text=f"text {number}",
    )


def entry(number, stance="support"):
    """One stance entry in the shape the tool returns."""
    return {"source_number": number, "stance": stance, "evidence": f"evidence {number}"}


def tool_reply(entries, explanation="Overall explanation."):
    """A fake API reply where the model called the tool."""
    block = SimpleNamespace(
        type="tool_use", name=TOOL["name"], input={"sources": entries, "explanation": explanation}
    )
    return SimpleNamespace(content=[block], stop_reason="tool_use")


def text_reply():
    """A fake API reply with plain text and no tool call."""
    block = SimpleNamespace(type="text", text="I cannot decide.")
    return SimpleNamespace(content=[block], stop_reason="end_turn")


class FakeMessages:
    """Records every create() call and returns canned replies in order."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    async def create(self, **kwargs):
        """Return the next canned reply, or raise it if it is an exception."""
        self.calls.append(kwargs)
        reply = self.replies[len(self.calls) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_prompt_says_older_figures_are_not_contradictions():
    """Day 8: a stale statistic (CDC 6.7 million vs a 2026 claim) must not be labelled contradict."""
    assert "different year or period" in PROMPT


class FakeClient:
    """Stands in for AsyncAnthropic: only client.messages.create is used."""

    def __init__(self, replies):
        self.messages = FakeMessages(replies)


def connection_error():
    """An Anthropic API error like the one the SDK raises after its own retries run out."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(request=request)


def run(coro):
    """Run one coroutine to completion."""
    return asyncio.run(coro)


# ---------- build_user_message ----------


def test_user_message_numbers_sources_from_one_and_hides_tier():
    sources = [make_source(1, tier=1), make_source(2, tier=3)]
    message = build_user_message("The claim.", sources)
    assert "Claim: The claim." in message
    assert "Source 1" in message
    assert "Source 2" in message
    assert "text 2" in message
    assert "tier" not in message.lower()


# ---------- parse_evaluation ----------


def test_parse_accepts_one_entry_per_source():
    output = parse_evaluation(tool_reply([entry(1), entry(2)]), 2)
    assert isinstance(output, EvaluationOutput)
    assert len(output.sources) == 2


def test_parse_accepts_entries_in_any_order():
    output = parse_evaluation(tool_reply([entry(2), entry(1)]), 2)
    assert len(output.sources) == 2


def test_parse_rejects_missing_tool_call():
    with pytest.raises(EvaluationParseError, match="did not call the tool"):
        parse_evaluation(text_reply(), 2)


def test_parse_rejects_bad_stance():
    bad = [entry(1), {"source_number": 2, "stance": "maybe", "evidence": "x"}]
    with pytest.raises(EvaluationParseError, match="validation"):
        parse_evaluation(tool_reply(bad), 2)


def test_parse_rejects_missing_entry():
    with pytest.raises(EvaluationParseError, match="one entry"):
        parse_evaluation(tool_reply([entry(1)]), 2)


def test_parse_rejects_duplicate_number():
    with pytest.raises(EvaluationParseError, match="one entry"):
        parse_evaluation(tool_reply([entry(1), entry(1)]), 2)


def test_parse_rejects_number_out_of_range():
    with pytest.raises(EvaluationParseError, match="one entry"):
        parse_evaluation(tool_reply([entry(1), entry(3)]), 2)


# ---------- build_claim ----------


def test_build_claim_applies_verdict_rule_with_tiers():
    sources = [make_source(1, tier=1), make_source(2, tier=3)]
    output = EvaluationOutput.model_validate(
        {"sources": [entry(1, "contradict"), entry(2, "support")], "explanation": "Why."}
    )
    claim = build_claim(7, "A claim.", sources, output)
    assert claim.id == 7
    assert claim.verdict == "contradicted"
    assert claim.confidence == "low"
    assert claim.explanation == "Why."
    assert [s.stance for s in claim.sources] == ["contradict", "support"]
    assert claim.sources[0].tier == 1
    assert claim.sources[0].evidence == "evidence 1"


# ---------- evaluate_claim ----------


def test_evaluate_claim_happy_path_one_call():
    sources = [make_source(1, tier=1), make_source(2, tier=1)]
    client = FakeClient([tool_reply([entry(1, "support"), entry(2, "support")])])
    claim, errors = run(evaluate_claim(client, 1, "A claim.", sources))
    assert errors == []
    assert claim.verdict == "supported"
    assert claim.confidence == "high"
    assert len(client.messages.calls) == 1


def test_evaluate_claim_never_sends_forced_tool_choice_or_sampling_params():
    client = FakeClient([tool_reply([entry(1)])])
    run(evaluate_claim(client, 1, "A claim.", [make_source(1)]))
    call = client.messages.calls[0]
    assert call["tool_choice"] == {"type": "auto"}
    assert call["model"] == "claude-sonnet-5-5"
    for name in ("temperature", "top_p", "top_k"):
        assert name not in call


def test_evaluate_claim_retries_once_when_no_tool_call():
    sources = [make_source(1, tier=1)]
    client = FakeClient([text_reply(), tool_reply([entry(1, "support")])])
    claim, errors = run(evaluate_claim(client, 1, "A claim.", sources))
    assert errors == []
    assert claim.verdict == "supported"
    assert len(client.messages.calls) == 2
    assert "must answer by calling" in client.messages.calls[1]["system"]
    assert "must answer by calling" not in client.messages.calls[0]["system"]


def test_evaluate_claim_retries_when_entries_do_not_match_sources():
    sources = [make_source(1), make_source(2)]
    client = FakeClient([tool_reply([entry(1)]), tool_reply([entry(1), entry(2)])])
    claim, errors = run(evaluate_claim(client, 1, "A claim.", sources))
    assert errors == []
    assert claim is not None
    assert len(client.messages.calls) == 2


def test_evaluate_claim_two_bad_replies_gives_error_and_no_claim():
    client = FakeClient([text_reply(), text_reply()])
    claim, errors = run(evaluate_claim(client, 4, "A claim.", [make_source(1)]))
    assert claim is None
    assert len(errors) == 1
    assert errors[0].stage == "evaluate"
    assert errors[0].claim_id == 4
    assert len(client.messages.calls) == 2


def test_evaluate_claim_api_error_gives_error_and_no_claim():
    client = FakeClient([connection_error()])
    claim, errors = run(evaluate_claim(client, 2, "A claim.", [make_source(1)]))
    assert claim is None
    assert errors[0].stage == "evaluate"
    assert errors[0].claim_id == 2


def test_evaluate_claim_with_no_sources_skips_the_api():
    client = FakeClient([])
    claim, errors = run(evaluate_claim(client, 3, "A claim.", []))
    assert errors == []
    assert claim.verdict == "insufficient_evidence"
    assert claim.confidence == "low"
    assert claim.sources == []
    assert client.messages.calls == []


def test_evaluate_claim_unexpected_exception_is_not_swallowed():
    client = FakeClient([ValueError("bug")])
    with pytest.raises(ValueError):
        run(evaluate_claim(client, 1, "A claim.", [make_source(1)]))
