"""Podcast config loaded alongside projects from projects.yml."""
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PodcastConfig:
    project_slug: str
    title: str
    description: str
    author: str
    itunes_category: str
    cover_art: str               # repo-relative path
    cron: str                    # cron expression in DISPATCH_TZ
    compose_window_days: int
    enabled: bool

    @property
    def feed_url(self) -> str:
        import os
        base = os.environ.get("PODCAST_BASE_URL", "")
        return f"{base}/{self.project_slug}.xml"


def load_podcasts(projects_yml: Path) -> list[PodcastConfig]:
    data = yaml.safe_load(projects_yml.read_text())
    out: list[PodcastConfig] = []
    for p in data.get("projects", []):
        block = p.get("podcast")
        if not block:
            continue
        out.append(PodcastConfig(
            project_slug=p["slug"],
            title=block["title"],
            description=block.get("description", "").strip(),
            author=block.get("author", "Mark"),
            itunes_category=block.get("itunes_category", "Technology"),
            cover_art=block["cover_art"],
            cron=block.get("cron", "0 5 * * sat"),
            compose_window_days=int(block.get("compose_window_days", 7)),
            enabled=bool(block.get("enabled", True)),
        ))
    return out


def enabled_podcasts(projects_yml: Path) -> list[PodcastConfig]:
    return [p for p in load_podcasts(projects_yml) if p.enabled]
