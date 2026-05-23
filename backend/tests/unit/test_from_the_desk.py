"""Tests for the weekly From-the-desk synthesis job.

Pure-function tests on `generate_from_the_desk(...)`. The DB/scheduler
wiring is covered separately in B5 (snapshot persistence) and via
integration smoke once deployed.
"""
import pytest
from unittest.mock import AsyncMock, patch
from dispatch.synthesis.from_the_desk import generate_from_the_desk


@pytest.mark.asyncio
async def test_quiet_project_uses_literal_fallback_no_llm_call():
    """<2 events in window → 'Quiet this week.' without an LLM call."""
    events = [
        {"kind": "commit", "title": "single commit", "occurred_at": "2026-05-10T08:00:00Z"},
    ]
    with patch("dispatch.synthesis.from_the_desk.call_kimi", new=AsyncMock()) as mock:
        result = await generate_from_the_desk(
            project_slug="agos", display_name="AGOS", events=events,
        )
    assert result["body"] == "Quiet this week."
    assert "generated_at" in result
    mock.assert_not_called()


@pytest.mark.asyncio
async def test_zero_events_uses_literal_fallback_no_llm_call():
    """0 events also short-circuits to the fallback."""
    with patch("dispatch.synthesis.from_the_desk.call_kimi", new=AsyncMock()) as mock:
        result = await generate_from_the_desk(
            project_slug="signalstack", display_name="SignalStack", events=[],
        )
    assert result["body"] == "Quiet this week."
    mock.assert_not_called()


@pytest.mark.asyncio
async def test_active_project_calls_kimi_with_event_window():
    events = [
        {"kind": "commit", "title": "fix websocket", "occurred_at": "2026-05-10T08:00:00Z"},
        {"kind": "commit", "title": "refactor harvest loop", "occurred_at": "2026-05-11T09:00:00Z"},
        {"kind": "pr_merged", "title": "Slippage audit (#83)", "occurred_at": "2026-05-12T10:00:00Z"},
    ]
    canned_response = "A productive week on AGOS. The WebSocket fix landed."
    with patch(
        "dispatch.synthesis.from_the_desk.call_kimi",
        new=AsyncMock(return_value=canned_response),
    ) as mock:
        result = await generate_from_the_desk(
            project_slug="agos", display_name="AGOS", events=events,
        )
    assert result["body"] == canned_response
    assert "generated_at" in result
    mock.assert_called_once()
    # The prompt passed to call_kimi should mention the display name and
    # at least one of the event titles.
    (prompt_arg,), _ = mock.call_args
    assert "AGOS" in prompt_arg
    assert "websocket" in prompt_arg.lower()


@pytest.mark.asyncio
async def test_returned_body_is_stripped():
    """Trim leading/trailing whitespace from Kimi's output."""
    events = [{"kind": "commit", "title": "a", "occurred_at": "2026-05-10T08:00:00Z"}] * 3
    with patch(
        "dispatch.synthesis.from_the_desk.call_kimi",
        new=AsyncMock(return_value="\n\n  the body  \n"),
    ):
        result = await generate_from_the_desk(
            project_slug="agos", display_name="AGOS", events=events,
        )
    assert result["body"] == "the body"


@pytest.mark.asyncio
async def test_generated_at_is_iso8601_utc():
    """The timestamp on the result is an ISO8601 string."""
    import re
    events = []
    result = await generate_from_the_desk(
        project_slug="agos", display_name="AGOS", events=events,
    )
    # Looser pattern — Python's `datetime.isoformat()` doesn't include 'Z'
    # by default, but does include +HH:MM or similar.
    assert re.match(r"\d{4}-\d{2}-\d{2}T", result["generated_at"]), result["generated_at"]
