"""Tests for the display-name resolution chain.

The chain (highest priority first):
  1. Explicit `display_name` override.
  2. First H1 of <local_path>/README.md.
  3. Titleize slug, respecting acronyms.yml.

These tests pin the three behaviors against the resolution chain, and
cover the edge cases that arise in practice (mixed-case overrides,
acronym-laden slugs, absent local_path, missing README).
"""
from pathlib import Path

import pytest

from dispatch.registry.resolve import (
    extract_readme_h1,
    load_acronyms,
    resolve_display_name,
    titleize_slug,
)


@pytest.fixture
def acronyms() -> set[str]:
    return {"AI", "API", "CLI", "HTTP", "JSON", "MCP", "SDK", "TTS", "UI", "URL"}


def test_override_wins(acronyms, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Should Not Win\n")
    assert (
        resolve_display_name(
            slug="my-api",
            override="My API",
            local_path=tmp_path,
            acronyms=acronyms,
        )
        == "My API"
    )


def test_override_lowercase_preserved(acronyms):
    assert (
        resolve_display_name(
            slug="dispatch",
            override="dispatch",
            local_path=None,
            acronyms=acronyms,
        )
        == "dispatch"
    )


def test_override_with_punctuation_preserved(acronyms):
    assert (
        resolve_display_name(
            slug="node-js",
            override="Node.js",
            local_path=None,
            acronyms=acronyms,
        )
        == "Node.js"
    )


def test_override_whitespace_trimmed(acronyms):
    assert (
        resolve_display_name(
            slug="x",
            override="  Astro  ",
            local_path=None,
            acronyms=acronyms,
        )
        == "Astro"
    )


def test_readme_h1_wins_over_titleize(acronyms, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Knowledge Vault\n\nA second brain.\n")
    assert (
        resolve_display_name(
            slug="knowledge-vault",
            override=None,
            local_path=tmp_path,
            acronyms=acronyms,
        )
        == "Knowledge Vault"
    )


def test_empty_override_falls_through_to_readme(acronyms, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# From The README\n")
    assert (
        resolve_display_name(
            slug="x",
            override="",
            local_path=tmp_path,
            acronyms=acronyms,
        )
        == "From The README"
    )


def test_missing_readme_falls_through_to_titleize(acronyms, tmp_path):
    # tmp_path exists but has no README.md
    assert (
        resolve_display_name(
            slug="agent-plugins",
            override=None,
            local_path=tmp_path,
            acronyms=acronyms,
        )
        == "Agent Plugins"
    )


def test_missing_local_path_falls_through_to_titleize(acronyms):
    assert (
        resolve_display_name(
            slug="personal-skills",
            override=None,
            local_path=None,
            acronyms=acronyms,
        )
        == "Personal Skills"
    )


def test_titleize_respects_acronyms(acronyms):
    assert titleize_slug("http-api-client", acronyms) == "HTTP API Client"


def test_titleize_handles_underscore_separators(acronyms):
    assert titleize_slug("knowledge_vault", acronyms) == "Knowledge Vault"


def test_titleize_single_token_acronym(acronyms):
    assert titleize_slug("api", acronyms) == "API"


def test_titleize_single_token_non_acronym(acronyms):
    assert titleize_slug("astro", acronyms) == "Astro"


def test_titleize_ignores_empty_tokens(acronyms):
    # Doubled separators shouldn't produce empty " Foo  Bar"
    assert titleize_slug("foo--bar", acronyms) == "Foo Bar"


def test_acronym_matching_case_insensitive(acronyms):
    # User wrote `mcp-server` lowercase; acronyms list stores `MCP` uppercase
    assert titleize_slug("mcp-server", acronyms) == "MCP Server"


def test_readme_h1_skips_h2_and_text(acronyms, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "Some preamble.\n\n## A Section\n\n# Real Title\n\nbody\n"
    )
    # First H1 wins, not the H2
    assert extract_readme_h1(tmp_path) == "Real Title"


def test_readme_h1_empty_returns_none(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("#   \n\nbody\n")
    assert extract_readme_h1(tmp_path) is None


def test_load_acronyms_missing_file_returns_empty(tmp_path):
    assert load_acronyms(tmp_path / "nope.yml") == set()


def test_load_acronyms_normalizes_to_upper(tmp_path):
    f = tmp_path / "acronyms.yml"
    f.write_text("acronyms:\n  - api\n  - Sdk\n  - HTTP\n")
    assert load_acronyms(f) == {"API", "SDK", "HTTP"}


def test_real_project_acronyms_file_loads():
    # The shipped acronyms.yml must parse and contain common tech acronyms.
    path = (
        Path(__file__).parent.parent.parent
        / "registry"
        / "acronyms.yml"
    )
    loaded = load_acronyms(path)
    assert {"API", "URL", "HTTP", "CLI", "SDK"}.issubset(loaded)
