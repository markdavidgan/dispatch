"""Sitemap generator — serves XML sitemap for search engines."""
from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import Response

from core.db import Database

router = APIRouter()

SITEMAP_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
URLSET_OPEN = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
URLSET_CLOSE = "</urlset>"


def _base_url(request: Request) -> str:
    """Resolve the public base URL for this instance.

    Priority:
    1. DISPATCH_PUBLIC_URL env var
    2. X-Forwarded-Proto + X-Forwarded-Host headers (reverse proxy)
    3. Request URL scheme + Host header
    4. Demo fallback
    """
    env_url = os.environ.get("DISPATCH_PUBLIC_URL", "").rstrip("/")
    if env_url:
        return env_url

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"

    host = request.headers.get("host")
    if host:
        scheme = forwarded_proto or request.url.scheme
        return f"{scheme}://{host}"

    return "https://dispatch-demo.markdavidgan.com"


def _url_xml(
    loc: str,
    priority: str = "0.5",
    changefreq: str = "daily",
    lastmod: str | None = None,
) -> str:
    parts = [f"  <url><loc>{loc}</loc>"]
    if lastmod:
        parts.append(f"<lastmod>{lastmod}</lastmod>")
    parts.append(f"<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>")
    return "".join(parts)


@router.get("/sitemap.xml")
async def sitemap(request: Request) -> Response:
    db: Database = request.app.state.db
    base = _base_url(request)

    urls: list[str] = [
        _url_xml(f"{base}/", priority="1.0"),
        _url_xml(f"{base}/briefings", priority="0.9"),
        _url_xml(f"{base}/projects", priority="0.9"),
        _url_xml(f"{base}/podcast", priority="0.9"),
    ]

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT date FROM filings WHERE kind='lead' ORDER BY date DESC"
        )
        briefing_dates = [row[0] for row in await cur.fetchall()]

    for d in briefing_dates:
        urls.append(
            _url_xml(
                f"{base}/briefings/{d}",
                priority="0.7",
                changefreq="never",
                lastmod=d,
            )
        )

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug FROM projects WHERE kind != 'meta' ORDER BY slug"
        )
        project_slugs = [row[0] for row in await cur.fetchall()]

    for slug in project_slugs:
        urls.append(
            _url_xml(
                f"{base}/projects/{slug}",
                priority="0.8",
                changefreq="weekly",
            )
        )

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT project_slug FROM podcasts WHERE enabled = 1 ORDER BY project_slug"
        )
        podcast_slugs = [row[0] for row in await cur.fetchall()]

    for slug in podcast_slugs:
        urls.append(
            _url_xml(
                f"{base}/podcast/{slug}",
                priority="0.6",
                changefreq="weekly",
            )
        )

    body = "\n".join([SITEMAP_HEADER, URLSET_OPEN, *urls, URLSET_CLOSE])
    return Response(content=body, media_type="application/xml")
