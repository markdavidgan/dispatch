from dispatch.synthesis.bullets import derive_bullet, derive_active_count


def test_red_on_merged_pr():
    events = [{"kind": "pr_merged"}, {"kind": "commit"}]
    assert derive_bullet("active", events) == "red"


def test_red_on_release():
    assert derive_bullet("active", [{"kind": "release"}]) == "red"


def test_red_on_three_or_more_commits_when_active():
    events = [{"kind": "commit"}] * 3
    assert derive_bullet("active", events) == "red"


def test_amber_on_some_commits():
    assert derive_bullet("active", [{"kind": "commit"}]) == "amber"
    assert derive_bullet("active", [{"kind": "commit"}, {"kind": "issue_opened"}]) == "amber"


def test_held_stays_sand_by_default():
    assert derive_bullet("held", []) == "sand"


def test_held_promotes_on_commit():
    assert derive_bullet("held", [{"kind": "commit"}]) == "amber"


def test_archived_returns_sand():
    assert derive_bullet("archived", [{"kind": "commit"}]) == "sand"


def test_active_count_counts_red_bullets():
    projects = [
        {"slug": "agos", "bullet": "red"},
        {"slug": "aether-focus", "bullet": "amber"},
        {"slug": "marcos", "bullet": "red"},
        {"slug": "signalstack", "bullet": "sand"},
    ]
    assert derive_active_count(projects) == "02"
