import feedparser
from dispatch.podcast.registry import PodcastConfig
from dispatch.podcast.rss import build_xml


def _cfg():
    return PodcastConfig(
        project_slug="aether-focus",
        title="Aether Dev",
        description="Weekly engineering podcast.",
        author="Aether Team",
        itunes_category="Technology",
        cover_art="apps/backend/dispatch/podcast/assets/aether-focus/cover.jpg",
        cron="0 5 * * sat",
        compose_window_days=7,
        enabled=True,
    )


def test_rss_is_parseable():
    eps = [{
        "id": "01J...", "episode_no": 7, "week_start": "2026-05-04",
        "title": "Aether Dev — Week of 2026-05-04",
        "description": "Test description",
        "audio_key": "podcast/aether-focus/episode-007-2026-05-04.mp3",
        "audio_size_bytes": 12345678, "duration_seconds": 2495,
        "published_at": "2026-05-13T06:14:00+00:00",
    }]
    xml = build_xml(_cfg(), eps).decode()
    feed = feedparser.parse(xml)
    assert feed.feed.title == "Aether Dev"
    assert len(feed.entries) == 1
    assert feed.entries[0].title.startswith("Aether Dev")
    assert "podcast/aether-focus/episode-007" in feed.entries[0].enclosures[0].href \
        or "aether-focus/episode-007" in feed.entries[0].enclosures[0].href
