"""iTunes-compatible RSS feed generator."""
import os
from datetime import datetime, timezone

from feedgen.feed import FeedGenerator
from core.db import Database
from dispatch.podcast.registry import PodcastConfig
from dispatch.publish import r2


def _base_url() -> str:
    return os.environ.get("PODCAST_BASE_URL", "")


async def _episodes_for(db: Database, project_slug: str) -> list[dict]:
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT id, episode_no, week_start, title, description, audio_key, "
            "       audio_size_bytes, duration_seconds, published_at "
            "FROM episodes WHERE project_slug=? AND status='ready' "
            "ORDER BY published_at DESC",
            (project_slug,),
        )
        cols = ["id","episode_no","week_start","title","description",
                "audio_key","audio_size_bytes","duration_seconds","published_at"]
        return [dict(zip(cols, r)) for r in await cur.fetchall()]


def build_xml(podcast: PodcastConfig, episodes: list[dict]) -> bytes:
    base = _base_url()
    fg = FeedGenerator()
    fg.load_extension("podcast", rss=True)
    fg.title(podcast.title)
    fg.link(href=f"{base}/{podcast.project_slug}", rel="alternate")
    fg.description(podcast.description)
    fg.language("en")
    fg.author({"name": podcast.author})
    fg.podcast.itunes_author(podcast.author)
    fg.podcast.itunes_category(podcast.itunes_category)
    fg.podcast.itunes_image(f"{base}/{podcast.project_slug}/cover.jpg")
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_type("episodic")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for e in episodes:
        url = f"{base}/{podcast.project_slug}/{e['audio_key'].rsplit('/', 1)[-1]}"
        fe = fg.add_entry()
        fe.id(f"dispatch-{podcast.project_slug}-{e['episode_no']}")
        fe.title(e["title"])
        fe.description(e["description"])
        fe.link(href=url)
        pub = e["published_at"]
        if pub:
            fe.pubDate(datetime.fromisoformat(pub.replace("Z", "+00:00")))
        fe.enclosure(url, str(e["audio_size_bytes"]), "audio/mpeg")
        fe.podcast.itunes_duration(int(e["duration_seconds"]))
        fe.podcast.itunes_episode(e["episode_no"])

    return fg.rss_str(pretty=True)


async def regenerate(db: Database, podcast: PodcastConfig) -> str:
    """Build the RSS XML, upload to R2, return the R2 key."""
    episodes = await _episodes_for(db, podcast.project_slug)
    xml = build_xml(podcast, episodes)
    key = f"podcast/{podcast.project_slug}.xml"
    await r2.upload_bytes(xml, key, "application/rss+xml")
    return key


async def upload_cover_art(podcast: PodcastConfig) -> str:
    """Upload the project's cover art to R2 (idempotent — run once per setup)."""
    from pathlib import Path
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    cover_path = repo_root / podcast.cover_art
    key = f"podcast/{podcast.project_slug}/cover.jpg"
    await r2.upload_bytes(cover_path.read_bytes(), key, "image/jpeg")
    return key
