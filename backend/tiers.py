"""Maps a source's domain to a trust tier (1, 2 or 3)."""

DEFAULT_TIER = 3

# Tier 1: primary or peer-reviewed evidence
TIER_1_DOMAINS = {
    # Intergovernmental bodies
    "who.int",
    "un.org",
    "worldbank.org",
    "imf.org",
    "oecd.org",
    "europa.eu",
    "ipcc.ch",
    # Major journals
    "nature.com",
    "thelancet.com",
    "science.org",
    "nejm.org",
    "bmj.com",
    "jamanetwork.com",
    "cell.com",
    "pnas.org",
    # Academic publishers and databases (subdomains where the parent site also sells things)
    "springer.com",
    "sciencedirect.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "academic.oup.com",
    "cochranelibrary.com",
    "plos.org",
    # Central banks without a .gov domain
    "bankofengland.co.uk",
}

# Tier 2: established editorial or secondary sources
TIER_2_DOMAINS = {
    # Wire services
    "reuters.com",
    "apnews.com",
    # Major news
    "bbc.co.uk",
    "bbc.com",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
    "npr.org",
    "economist.com",
    "ft.com",
    "wsj.com",
    "bloomberg.com",
    "aljazeera.com",
    "pbs.org",
    # Science journalism
    "scientificamerican.com",
    "newscientist.com",
    "spectrum.ieee.org",
    "nationalgeographic.com",
    "statnews.com",
    # Reference
    "wikipedia.org",
    "britannica.com",
    "ourworldindata.org",
    # Fact-checkers
    "snopes.com",
    "politifact.com",
    "factcheck.org",
    "fullfact.org",
    # Preprint servers (not yet peer reviewed)
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
}

def _matches_list(domain: str, domains: set) -> bool:
    """it returns True when the domain is in the set or is a subdomain of something in the set."""

    for entry in domains:
        if domain == entry or domain.endswith("."+entry):
            return True

    return False

def _has_suffix(domain: str, top: str, second: str) -> bool:
    """Return True for "name.<top>" (cdc.gov) or "name.<second>.xx" with a 2-letter country code (ons.gov.uk).

    <top> is the label that may end the domain on its own (gov, edu).
    <second> is the label allowed before a country code (gov, edu, ac).
    """
    labels = domain.split(".")

    if len(labels) < 2:
        return False
    elif labels[-1] == top:
        return True
    elif len(labels) >= 3 and labels[-2] == second and len(labels[-1]) == 2:
        return True
    else:
        return False


def _is_government(domain: str) -> bool:
    """Return True for .gov and .gov.xx domains."""
    return _has_suffix(domain, "gov", "gov")


def _is_academic(domain: str) -> bool:
    """Return True for .edu, .edu.xx and .ac.xx domains."""
    return _has_suffix(domain, "edu", "edu") or _has_suffix(domain, "edu", "ac")


def _looks_personal(domain: str, path: str) -> bool:
    """Return True when an academic page looks like a personal page.

    Personal means: the first subdomain label is people or students, or a whole path segment
    is people or students, or starts with "~". The path check ignores case.
    """
    first_label = domain.split(".")[0]
    if first_label in ("people", "students"):
        return True

    for segment in path.lower().split("/"):
        if segment.startswith("~") or segment in ("people", "students"):
            return True

    return False


def get_tier(domain, path=""):
    """Return the trust tier (1, 2 or 3) for a source.

    domain arrives cleaned: lowercase, no "www." or "m." prefix.
    path is the URL path in any case; it is only used to spot personal academic pages.
    """

    if _matches_list(domain, TIER_1_DOMAINS):
        return 1
    elif _matches_list(domain, TIER_2_DOMAINS):
        return 2
    elif _is_government(domain):
        return 1
    elif _is_academic(domain):
        if _looks_personal(domain, path):
            return 3
        else:
            return 2
    else:
        return DEFAULT_TIER
