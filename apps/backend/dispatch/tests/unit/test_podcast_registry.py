"""Tests for the per-project podcast registry loader.

The shipped showcase `projects.yml` does not ship any podcast configs (the
three showcase projects are demo data, not real podcasts), so the loader
must gracefully return an empty list. When podcast configs are present, the
loader must parse them and derive the feed URL from the project slug.
"""
from pathlib import Path

from dispatch.podcast.registry import load_podcasts, enabled_podcasts


def test_shipped_registry_has_no_podcasts():
    path = Path(__file__).parent.parent.parent / "projects.yml"
    assert load_podcasts(path) == []
    assert enabled_podcasts(path) == []


def test_loader_parses_inline_podcast_config(tmp_path):
    yml = tmp_path / "projects.yml"
    yml.write_text(
        """
version: 1
projects:
  - slug: alpha
    display_name: Alpha
    status: active
    kind: app
    podcast:
      title: "Alpha Weekly"
      description: "Weekly digest."
      itunes_category: "Technology"
      cron: "0 5 * * sat"
      compose_window_days: 7
      enabled: true
  - slug: beta
    display_name: Beta
    status: active
    kind: app
    podcast:
      title: "Beta Weekly"
      description: "Quiet podcast."
      itunes_category: "Technology"
      cron: "0 5 * * sat"
      compose_window_days: 7
      enabled: false
"""
    )
    casts = load_podcasts(yml)
    assert {c.project_slug for c in casts} == {"alpha", "beta"}
    assert {c.project_slug for c in enabled_podcasts(yml)} == {"alpha"}


def test_feed_url_uses_project_slug(tmp_path):
    yml = tmp_path / "projects.yml"
    yml.write_text(
        """
version: 1
projects:
  - slug: gamma
    display_name: Gamma
    status: active
    kind: app
    podcast:
      title: "Gamma"
      description: ""
      itunes_category: "Technology"
      cron: "0 5 * * sat"
      compose_window_days: 7
      enabled: true
"""
    )
    casts = {c.project_slug: c for c in load_podcasts(yml)}
    assert casts["gamma"].feed_url.endswith("/gamma.xml")
