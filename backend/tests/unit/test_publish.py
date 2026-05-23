"""Unit tests for publish module."""
import json
import pytest
from dispatch.publish.snapshot import build_snapshot, _sign_payload
from dispatch.publish.r2 import _api_url, _bucket, _public_base


def test_sign_payload_deterministic():
    payload = {"version": 1, "brief": None}
    sig1 = _sign_payload(payload)
    sig2 = _sign_payload(payload)
    assert sig1 == sig2
    assert len(sig1) == 32


def test_sign_payload_changes_with_data():
    sig1 = _sign_payload({"version": 1})
    sig2 = _sign_payload({"version": 2})
    assert sig1 != sig2


@pytest.mark.asyncio
async def test_build_snapshot_empty_db(db):
    snapshot = await build_snapshot(db)
    assert snapshot["version"] == 1
    assert "generated_at" in snapshot
    assert snapshot["brief"] is None
    assert snapshot["projects"] == []
    assert snapshot["recent_events"] == []
    assert snapshot["episodes"] == []
    assert "signature" in snapshot


@pytest.mark.asyncio
async def test_build_snapshot_with_lead(db):
    # Seed a project and a lead filing
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, kind) VALUES (?, ?, ?, ?)",
            ("agos", "Agos", "active", "app"),
        )
        await cur.execute(
            """INSERT INTO filings (date, kind, issue_no, covers_from, covers_until, lead_headline, lead_body, active_count, project_lines, model, prompt_hash, generated_at)
               VALUES (?, 'lead', 1, '2026-05-14T00:00:00Z', '2026-05-14T23:59:59Z', 'Headline', 'Body', 3, '[{\"slug\": \"agos\", \"name\": \"Agos\", \"status\": \"active\", \"stat\": \"1 commit\", \"bullet\": \"red\"}]', 'kimi-k2.6', 'abc123', '2026-05-14T02:00:00Z')""",
            ("2026-05-14",),
        )

    snapshot = await build_snapshot(db)
    brief = snapshot["brief"]
    assert brief is not None
    assert brief["lead_headline"] == "Headline"
    assert brief["active_count"] == "03"
    assert len(brief["projects"]) == 1
    assert brief["projects"][0]["bullet"] == "red"
    assert snapshot["signature"]


def test_r2_api_url():
    url = _api_url("acct123", "my-bucket", "dispatch/snapshot.json")
    assert "accounts/acct123/r2/buckets/my-bucket/objects/dispatch/snapshot.json" in url
