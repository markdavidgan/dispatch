"""Tests for the post-synthesis mention extraction pass.

Pure regex + registry lookup — no LLM call. Called by the orchestrator
immediately after a successful `synthesis:lead` or `synthesis:addendum`.
"""
import pytest
from dispatch.synthesis.mention_extraction import extract_mentions


def test_extract_mentions_finds_project_name_anywhere_in_sentence():
    projects = {
        "agos": "AGOS",
        "aether-focus": "Made with Aether",
        "knowledge-vault": "Knowledge Vault",
    }
    lead = (
        "AGOS clears the WebSocket reconnection bug; funding-harvest loop now runs unattended. "
        "Made with Aether shipped a refactor of its thought-parking flow. "
        "Knowledge Vault landed the threading-and-memory P6 slice."
    )
    mentions = extract_mentions(lead, projects)
    slugs = [m["project_slug"] for m in mentions]
    assert slugs == ["agos", "aether-focus", "knowledge-vault"]
    assert "WebSocket reconnection" in mentions[0]["excerpt"]


def test_extract_mentions_case_insensitive():
    projects = {"agos": "AGOS"}
    mentions = extract_mentions("agos clears the bug today.", projects)
    assert len(mentions) == 1
    assert mentions[0]["project_slug"] == "agos"


def test_extract_mentions_records_position_order():
    projects = {"a": "Alpha", "b": "Beta"}
    text = "Beta shipped. Alpha shipped too."
    mentions = extract_mentions(text, projects)
    assert [m["position"] for m in mentions] == [0, 1]
    assert [m["project_slug"] for m in mentions] == ["b", "a"]


def test_extract_mentions_dedupes_per_sentence():
    # Don't record the same project twice for one sentence containing
    # multiple matches; record once per appearance.
    projects = {"agos": "AGOS"}
    text = "AGOS clears the AGOS regression today."
    mentions = extract_mentions(text, projects)
    assert len(mentions) == 1


def test_extract_mentions_empty_text_returns_empty():
    assert extract_mentions("", {"agos": "AGOS"}) == []


def test_extract_mentions_no_projects_returns_empty():
    assert extract_mentions("AGOS clears bugs.", {}) == []


def test_extract_mentions_longest_match_first():
    # "Made with Aether" should match before any substring it contains.
    projects = {"aether-focus": "Made with Aether", "aether": "Aether"}
    text = "Made with Aether shipped a refactor."
    mentions = extract_mentions(text, projects)
    # Should record aether-focus, not aether (longest-display-name preference)
    assert mentions == [
        {"project_slug": "aether-focus", "excerpt": "Made with Aether shipped a refactor.", "position": 0}
    ]
    # Explicit anchor: the shorter slug must be absent — guards against a
    # future regression where overlap-suppression breaks but length-equality
    # accidentally still passes.
    slugs = [m["project_slug"] for m in mentions]
    assert "aether" not in slugs


def test_extract_mentions_respects_word_boundaries():
    # "AGOS" must not match inside "Pagos" — word-boundary lookarounds
    # prevent the substring false-positive that .find() would emit.
    projects = {"agos": "AGOS"}
    text = "Pagos checked in today."
    assert extract_mentions(text, projects) == []


def test_extract_mentions_handles_regex_metachars_in_display_name():
    # Display names like "mark.id" contain regex metachars — the matcher
    # must treat them literally (re.escape inside the pattern).
    projects = {"mark-id": "mark.id"}
    # Negative case: a name with the metachar acting as wildcard would
    # also match "markxid"; verify it does NOT.
    assert extract_mentions("markxid was renamed.", projects) == []
    # Positive case: literal "mark.id" inside a sentence does match.
    out = extract_mentions("mark.id was retired today.", projects)
    assert len(out) == 1
    assert out[0]["project_slug"] == "mark-id"


def test_extract_mentions_falls_back_to_titleized_slug():
    # When the LLM uses the slug form (e.g. "Bellegan") instead of the
    # display name ("Belle Gan"), the extractor should still match.
    projects = {"bellegan": "Belle Gan"}
    out = extract_mentions("Bellegan runs 41 commits today.", projects)
    assert len(out) == 1
    assert out[0]["project_slug"] == "bellegan"


def test_extract_mentions_display_name_preferred_over_slug():
    # When both the display name and titleized slug could match, the
    # display name should win (longest match + checked first).
    projects = {"bellegan": "Belle Gan"}
    text = "Belle Gan runs 41 commits today."
    out = extract_mentions(text, projects)
    assert len(out) == 1
    assert out[0]["project_slug"] == "bellegan"
    assert "Belle Gan" in out[0]["excerpt"]
