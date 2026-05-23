from pathlib import Path

from dispatch.podcast.registry import load_podcasts, enabled_podcasts


def test_loads_two_initial_podcasts():
    path = Path(__file__).parent.parent.parent / "projects.yml"
    casts = load_podcasts(path)
    slugs = {c.project_slug for c in casts}
    assert "aether-focus" in slugs
    assert "agos" in slugs


def test_feed_url_uses_project_slug():
    path = Path(__file__).parent.parent.parent / "projects.yml"
    casts = {c.project_slug: c for c in load_podcasts(path)}
    aether = casts["aether-focus"]
    assert aether.feed_url.endswith("/aether-focus.xml")
