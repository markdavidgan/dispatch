"""Sitemap generator — serves XML sitemap for search engines."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from core.db import Database

router = APIRouter()


SITEMAP_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
URLSET_OPEN = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
URLSET_CLOSE = "</urlset>"


def _url_xml(loc: str, priority: str = "0.5", changefreq: str = "daily") -> str:
    return f"  <url><loc>{loc}</loc><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>"


@router.get("/sitemap.xml")
async def sitemap(request: Request) -> Response:
    db: Database = request.app.state.db
    base = "https://dispatch-demo.markdavidgan.com"

    urls: list[str] = [
        _url_xml(f"{base}/", priority="1.0"),
        _url_xml(f"{base}/briefings", priority="0.9"),
        _url_xml(f"{base}/projects", priority="0.9"),
        _url_xml(f"{base}/podcast", priority="0.9"),
    ]

    async with db.cursor() as cur:
        await cur.execute("SELECT date FROM filings WHERE kind='lead' ORDER BY date DESC")
        briefing_dates = [row[0] for row in await cur.fetchall()]

    for d in briefing_dates:
        urls.append(_url_xml(f"{base}/briefings/{d}", priority="0.7", changefreq="never"))

    async with db.cursor() as cur:
        await cur.execute("SELECT slug FROM projects WHERE kind != 'meta' ORDER BY slug")
        project_slugs = [row[0] for row in await cur.fetchall()]

    for slug in project_slugs:
        urls.append(_url_xml(f"{base}/projects/{slug}", priority="0.8", changefreq="weekly"))

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT project_slug FROM podcasts WHERE enabled = 1 ORDER BY project_slug"
        )
        podcast_slugs = [row[0] for row in await cur.fetchall()]

    for slug in podcast_slugs:
        urls.append(_url_xml(f"{base}/podcast/{slug}", priority="0.6", changefreq="weekly"))

    body = "\n".join([SITEMAP_HEADER, URLSET_OPEN, *urls, URLSET_CLOSE])
    return Response(content=body, media_type="application/xml")
