"""Tests for the verdict and confidence rule (pure Python, no API)."""

import pytest

from evaluator import compute_confidence, compute_verdict


# ---------- compute_verdict ----------


def test_no_sources_is_insufficient():
    assert compute_verdict([]) == "insufficient_evidence"


def test_one_tier1_support_is_supported():
    assert compute_verdict([(1, "support")]) == "supported"


def test_one_tier2_support_alone_is_insufficient():
    assert compute_verdict([(2, "support")]) == "insufficient_evidence"


def test_tier2_plus_tier3_support_is_supported():
    assert compute_verdict([(2, "support"), (3, "support")]) == "supported"


def test_tier3_support_only_never_supported():
    pairs = [(3, "support")] * 4
    assert compute_verdict(pairs) == "insufficient_evidence"


def test_tier3_contradict_only_never_contradicted():
    pairs = [(3, "contradict")] * 4
    assert compute_verdict(pairs) == "insufficient_evidence"


def test_one_tier1_contradict_is_contradicted():
    assert compute_verdict([(1, "contradict")]) == "contradicted"


def test_tier2_plus_tier3_contradict_is_contradicted():
    assert compute_verdict([(2, "contradict"), (3, "contradict")]) == "contradicted"


def test_tier1_support_ignores_tier3_contradictions():
    pairs = [(1, "support"), (3, "contradict"), (3, "contradict"), (3, "contradict")]
    assert compute_verdict(pairs) == "supported"


def test_tier1_contradict_ignores_tier3_support():
    pairs = [(1, "contradict"), (3, "support"), (3, "support"), (3, "support")]
    assert compute_verdict(pairs) == "contradicted"


def test_strong_sources_on_both_sides_is_disputed():
    pairs = [(1, "support"), (1, "contradict")]
    assert compute_verdict(pairs) == "disputed"


def test_tier2_pair_on_both_sides_with_tier3_is_disputed():
    pairs = [(2, "support"), (3, "support"), (2, "contradict"), (3, "contradict")]
    assert compute_verdict(pairs) == "disputed"


def test_strong_both_sides_but_one_side_below_three_is_insufficient():
    pairs = [(1, "support"), (2, "contradict")]
    assert compute_verdict(pairs) == "insufficient_evidence"


def test_not_addressed_sources_do_not_count():
    pairs = [(1, "not_addressed"), (1, "not_addressed"), (2, "support")]
    assert compute_verdict(pairs) == "insufficient_evidence"


def test_many_tier3_contradict_against_tier2_support_is_not_contradicted():
    pairs = [(2, "support"), (3, "contradict"), (3, "contradict"), (3, "contradict")]
    assert compute_verdict(pairs) == "insufficient_evidence"


# ---------- compute_confidence ----------


@pytest.mark.parametrize("verdict", ["disputed", "insufficient_evidence"])
def test_disputed_and_insufficient_are_always_low(verdict):
    pairs = [(1, "support"), (1, "support"), (1, "contradict")]
    assert compute_confidence(verdict, pairs) == "low"


def test_supported_weight_three_is_low():
    assert compute_confidence("supported", [(1, "support")]) == "low"


def test_supported_weight_four_is_medium():
    assert compute_confidence("supported", [(1, "support"), (3, "support")]) == "medium"


def test_supported_weight_five_is_medium():
    assert compute_confidence("supported", [(1, "support"), (2, "support")]) == "medium"


def test_supported_weight_six_is_high():
    assert compute_confidence("supported", [(1, "support"), (1, "support")]) == "high"


def test_contradicted_uses_contradict_weight_only():
    pairs = [(1, "contradict"), (1, "contradict"), (1, "support")]
    assert compute_confidence("contradicted", pairs) == "high"


def test_confidence_counts_tier3_on_the_winning_side():
    pairs = [(1, "support"), (3, "support"), (3, "support"), (3, "contradict")]
    assert compute_confidence("supported", pairs) == "medium"
