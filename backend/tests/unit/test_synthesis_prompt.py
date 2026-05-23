from dispatch.synthesis.prompt import build_lead_prompt
from dispatch.synthesis.shaping import shape_events, group_by_project
from dispatch.synthesis.schema import LeadFiling, ProjectLine


def test_prompt_includes_window_and_data():
    text, h = build_lead_prompt(
        issue_no=134, date_local="Thu 14 May 2026", tz="Asia/Manila",
        covers_from="2026-05-13T00:00", covers_until="2026-05-13T23:59",
        projects_input=[
            {"slug": "agos", "name": "AGOS", "status": "active",
             "stat": "9 commits · 1 PR", "bullet": "red"},
        ],
        events_by_project={"agos": [
            {"kind": "commit", "title": "fix(import): resolve cycle",
             "occurred_at": "2026-05-13T09:12:00Z"},
        ]},
    )
    assert "Issue No. 134" in text
    assert "fix(import)" in text
    assert "Asia/Manila" in text
    assert "lead_headline" in text
    assert "agos (AGOS)" in text
    assert "### agos (AGOS)" in text
    assert len(h) == 16


def test_prompt_is_deterministic():
    args = dict(
        issue_no=1, date_local="d", tz="UTC",
        covers_from="a", covers_until="b",
        projects_input=[], events_by_project={},
    )
    _, h1 = build_lead_prompt(**args)
    _, h2 = build_lead_prompt(**args)
    assert h1 == h2


def test_shape_drops_bots_and_sorts():
    raw = [
        {"project_slug": "a", "kind": "commit", "title": "x",
         "author": "dependabot[bot]", "occurred_at": "2026-05-13T11:00:00Z"},
        {"project_slug": "a", "kind": "commit", "title": "y",
         "author": "mark", "occurred_at": "2026-05-13T10:00:00Z"},
        {"project_slug": "a", "kind": "commit", "title": "z",
         "author": "mark", "occurred_at": "2026-05-13T12:00:00Z"},
    ]
    out = shape_events(raw)
    assert len(out) == 2  # bot dropped
    assert [e["title"] for e in out] == ["y", "z"]  # sorted by time


def test_group_by_project():
    events = [
        {"project_slug": "a", "kind": "commit", "title": "x", "occurred_at": "2026-05-13T10:00:00Z"},
        {"project_slug": "b", "kind": "commit", "title": "y", "occurred_at": "2026-05-13T11:00:00Z"},
        {"project_slug": "a", "kind": "commit", "title": "z", "occurred_at": "2026-05-13T12:00:00Z"},
    ]
    g = group_by_project(events)
    assert set(g.keys()) == {"a", "b"}
    assert len(g["a"]) == 2
    assert len(g["b"]) == 1


def test_lead_filing_schema_rejects_bad_active_count():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LeadFiling(lead_headline="h", lead_body="b",
                   active_count="7",  # not 2 digits
                   project_lines=[])
