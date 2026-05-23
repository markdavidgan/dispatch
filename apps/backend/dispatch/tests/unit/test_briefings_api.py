"""Unit tests for /briefings routes — tested directly without ASGI transport.

We call the route handler coroutines with mocked Request objects
because TestClient/ASGITransport in starlette 0.41.x do not handle
lifespan state reliably in this container environment.
"""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from dispatch.api.briefings import list_briefings, get_briefing, _audio_url


@pytest.fixture
def mock_request(db):
    req = MagicMock()
    req.app.state.db = db
    return req


@pytest_asyncio.fixture
async def seeded_db(db):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO filings (date, kind, issue_no, covers_from, covers_until, "
            "lead_headline, lead_body, active_count, project_lines, model, prompt_hash, generated_at) "
            "VALUES ('2026-05-14', 'lead', 134, '2026-05-13T00:00:00Z', '2026-05-13T23:59:59Z', "
            "'AGOS clears the WebSocket bug.', 'Body.', 6, '[]', 'kimi', 'h1', '2026-05-14T02:00:00Z')"
        )
        await cur.execute(
            "INSERT INTO filings (date, kind, issue_no, covers_from, covers_until, "
            "lead_headline, lead_body, active_count, project_lines, model, prompt_hash, generated_at) "
            "VALUES ('2026-05-13', 'lead', 133, '2026-05-12T00:00:00Z', '2026-05-12T23:59:59Z', "
            "'Quiet day.', 'Body.', 4, '[]', 'kimi', 'h2', '2026-05-13T02:00:00Z')"
        )
    await db._conn.commit()
    return db


@pytest.mark.asyncio
async def test_get_briefings_returns_list_newest_first(seeded_db, mock_request):
    r = await list_briefings(mock_request, limit=50, offset=0)
    assert [b.date for b in r.briefings] == ["2026-05-14", "2026-05-13"]
    assert r.briefings[0].issue_no == 134
    assert r.total == 2


@pytest.mark.asyncio
async def test_get_briefings_respects_limit_and_offset(seeded_db, mock_request):
    r = await list_briefings(mock_request, limit=1, offset=1)
    assert len(r.briefings) == 1
    assert r.briefings[0].date == "2026-05-13"


@pytest.mark.asyncio
async def test_get_single_briefing_returns_full_payload(seeded_db, mock_request):
    r = await get_briefing(mock_request, date="2026-05-14")
    assert r.date == "2026-05-14"
    assert r.issue_no == 134
    assert r.lead_headline == "AGOS clears the WebSocket bug."
    assert r.lead_body == "Body."


@pytest.mark.asyncio
async def test_get_single_briefing_unknown_date_returns_404(mock_request):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_briefing(mock_request, date="2099-01-01")
    assert exc_info.value.status_code == 404


# ---------- audio URL derivation ----------


def test_audio_url_uses_R2_PUBLIC_BASE_URL_when_set(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://podcasts.marklab.uk")
    assert _audio_url("2026-05-14", "lead") == (
        "https://podcasts.marklab.uk/dispatch/audio/2026-05-14-lead.mp3"
    )
    assert _audio_url("2026-05-14", "addendum") == (
        "https://podcasts.marklab.uk/dispatch/audio/2026-05-14-addendum.mp3"
    )


def test_audio_url_trims_trailing_slash(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://podcasts.marklab.uk/")
    # No double-slash before /dispatch
    assert _audio_url("2026-05-14", "lead") == (
        "https://podcasts.marklab.uk/dispatch/audio/2026-05-14-lead.mp3"
    )


def test_audio_url_returns_none_when_base_unset(monkeypatch):
    monkeypatch.delenv("R2_PUBLIC_BASE_URL", raising=False)
    assert _audio_url("2026-05-14", "lead") is None


@pytest.mark.asyncio
async def test_list_briefings_populates_audio_url(seeded_db, mock_request, monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://podcasts.marklab.uk")
    r = await list_briefings(mock_request, limit=50, offset=0)
    assert r.briefings[0].audio_url == (
        "https://podcasts.marklab.uk/dispatch/audio/2026-05-14-lead.mp3"
    )


# ---------- recent_events from R2 archive ----------


@pytest.mark.asyncio
async def test_get_briefing_pulls_recent_events_from_archive(seeded_db, mock_request, monkeypatch):
    """The detail endpoint reads recent_events from the R2 snapshot archive."""
    fake_archive = {
        "recent_events": [
            {"project_slug": "agos", "kind": "commit", "external_id": "abc",
             "title": "fix websocket", "occurred_at": "2026-05-13T08:00:00Z", "url": None},
            {"project_slug": "marklab", "kind": "commit", "external_id": "def",
             "title": "ship dispatch", "occurred_at": "2026-05-13T09:00:00Z", "url": None},
        ]
    }
    import json as _json
    monkeypatch.setattr(
        "dispatch.api.briefings.download_bytes",
        AsyncMock(return_value=_json.dumps(fake_archive).encode()),
    )
    r = await get_briefing(mock_request, date="2026-05-14")
    assert len(r.recent_events) == 2
    assert r.recent_events[0]["title"] == "fix websocket"


@pytest.mark.asyncio
async def test_get_briefing_returns_empty_events_when_archive_missing(seeded_db, mock_request):
    """No R2 archive → recent_events is [] (defensive, not 404)."""
    async def _raise(_key):
        raise FileNotFoundError("not in r2")
    with patch("dispatch.api.briefings.download_bytes", new=AsyncMock(side_effect=_raise)):
        r = await get_briefing(mock_request, date="2026-05-14")
    assert r.recent_events == []


@pytest.mark.asyncio
async def test_get_briefing_returns_empty_events_when_archive_malformed(seeded_db, mock_request):
    """Malformed JSON archive → recent_events is [] (warn but don't crash)."""
    with patch(
        "dispatch.api.briefings.download_bytes",
        new=AsyncMock(return_value=b"not-json{"),
    ):
        r = await get_briefing(mock_request, date="2026-05-14")
    assert r.recent_events == []


@pytest.mark.asyncio
async def test_get_briefing_audio_addendum_url_only_when_addendum_filed(seeded_db, mock_request, monkeypatch):
    """audio_addendum_url is None when no addendum filing exists for the date."""
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://podcasts.marklab.uk")
    # seeded_db only has lead filings — no addendums.
    with patch("dispatch.api.briefings.download_bytes", new=AsyncMock(return_value=b"{}")):
        r = await get_briefing(mock_request, date="2026-05-14")
    assert r.audio_lead_url == (
        "https://podcasts.marklab.uk/dispatch/audio/2026-05-14-lead.mp3"
    )
    assert r.audio_addendum_url is None
