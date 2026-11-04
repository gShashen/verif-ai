"""Unit tests for tiers.py: domain lists, government and academic patterns, personal page demotion.

Interface these tests expect from tiers.py:
    TIER_1_DOMAINS: set[str]   hand-written, bare domains like "nature.com"
    TIER_2_DOMAINS: set[str]
    DEFAULT_TIER = 3
    get_tier(domain, path="") -> int   (1, 2 or 3)

domain arrives already cleaned (lowercase, no "www." or "m."). path is the URL path, any case.

Rule order: lists first, then government pattern (Tier 1), then academic pattern (Tier 2,
or Tier 3 if the page looks personal), then DEFAULT_TIER.
"""

import pytest

from tiers import DEFAULT_TIER, TIER_1_DOMAINS, TIER_2_DOMAINS, get_tier


# ---------- the lists ----------


def test_default_tier_is_3():
    assert DEFAULT_TIER == 3


def test_lists_hold_bare_lowercase_domains():
    for domain in TIER_1_DOMAINS | TIER_2_DOMAINS:
        assert domain == domain.lower()
        assert not domain.startswith("www.")
        assert "/" not in domain
        assert "://" not in domain


def test_lists_do_not_overlap():
    assert TIER_1_DOMAINS & TIER_2_DOMAINS == set()


@pytest.mark.parametrize("domain", ["who.int", "nature.com", "springer.com", "thelancet.com"])
def test_anchor_tier_1_domains(domain):
    assert get_tier(domain) == 1


@pytest.mark.parametrize(
    "domain",
    ["reuters.com", "bbc.co.uk", "bbc.com", "theguardian.com", "wikipedia.org", "snopes.com"],
)
def test_anchor_tier_2_domains(domain):
    assert get_tier(domain) == 2


@pytest.mark.parametrize("domain", ["reddit.com", "thermtest.com", "medium.com", "example.com"])
def test_unlisted_domains_get_default_tier(domain):
    assert get_tier(domain) == DEFAULT_TIER


# ---------- subdomains and lookalikes ----------


@pytest.mark.parametrize(
    "domain, expected",
    [
        ("link.springer.com", 1),
        ("en.wikipedia.org", 2),
        ("news.bbc.co.uk", 2),
    ],
)
def test_subdomain_of_listed_domain_matches(domain, expected):
    assert get_tier(domain) == expected


@pytest.mark.parametrize(
    "domain",
    [
        "notnature.com",          # ends with "nature.com" but is a different site
        "fakereuters.com",
        "nature.com.evil.io",     # listed domain in the middle, not at the end
        "wikipedia.org.example.net",
    ],
)
def test_lookalike_domains_do_not_match(domain):
    assert get_tier(domain) == DEFAULT_TIER


# ---------- government pattern (Tier 1) ----------


@pytest.mark.parametrize(
    "domain",
    [
        "cdc.gov",
        "pmc.ncbi.nlm.nih.gov",   # the PMC result from the Serper exploration
        "ons.gov.uk",
        "statistics.gov.lk",
        "abs.gov.au",
    ],
)
def test_government_domains_are_tier_1(domain):
    assert get_tier(domain) == 1


@pytest.mark.parametrize(
    "domain",
    [
        "evilgov.com",            # "gov" inside a label, not a label of its own
        "gov.example.com",        # "gov" label, but not in a government position
        "example.gov.com",        # second-level "gov" needs a 2-letter country code after it
        "mygov.uk",
    ],
)
def test_fake_government_domains_are_not_tier_1(domain):
    assert get_tier(domain) == DEFAULT_TIER


# ---------- academic pattern (Tier 2) ----------


@pytest.mark.parametrize(
    "domain",
    [
        "mit.edu",
        "news.mit.edu",
        "unimelb.edu.au",
        "ox.ac.uk",
        "cmb.ac.lk",
    ],
)
def test_academic_domains_are_tier_2(domain):
    assert get_tier(domain) == 2


@pytest.mark.parametrize(
    "domain",
    [
        "myedu.com",
        "edu.example.com",
        "ac.example.com",
        "example.ac.com",         # second-level "ac" needs a 2-letter country code after it
    ],
)
def test_fake_academic_domains_are_not_tier_2(domain):
    assert get_tier(domain) == DEFAULT_TIER


# ---------- personal academic pages (demoted to Tier 3) ----------


@pytest.mark.parametrize(
    "domain, path",
    [
        ("cs.stanford.edu", "/~jsmith/notes.html"),
        ("cs.stanford.edu", "/~JSmith/Notes.html"),       # path check ignores case
        ("mit.edu", "/people/jsmith/"),
        ("ox.ac.uk", "/students/jsmith/blog"),
        ("people.cs.cornell.edu", "/jsmith/"),            # personal subdomain
        ("students.unimelb.edu.au", "/projects/x.html"),
    ],
)
def test_personal_academic_pages_are_tier_3(domain, path):
    assert get_tier(domain, path) == 3


@pytest.mark.parametrize(
    "domain, path",
    [
        ("news.mit.edu", "/2024/diamond-cooling-1015"),
        ("ox.ac.uk", "/news/2024-01-01-study"),
        ("mit.edu", "/peoplesoft-guide"),                 # "people" only as a whole segment
        ("mit.edu", ""),
        ("mit.edu", "/"),
    ],
)
def test_normal_academic_pages_stay_tier_2(domain, path):
    assert get_tier(domain, path) == 2


@pytest.mark.parametrize(
    "domain, path, expected",
    [
        ("reuters.com", "/~jsmith/", 2),                  # demotion is for academic domains only
        ("nature.com", "/people/editors/", 1),
        ("cdc.gov", "/people/", 1),
        ("reddit.com", "/user/jsmith/", 3),
    ],
)
def test_personal_path_does_not_change_non_academic_domains(domain, path, expected):
    assert get_tier(domain, path) == expected


def test_path_defaults_to_empty():
    assert get_tier("mit.edu") == 2


@pytest.mark.parametrize("domain", ["localhost", "gov", "edu"])
def test_single_label_domains_do_not_crash(domain):
    assert get_tier(domain) == DEFAULT_TIER
