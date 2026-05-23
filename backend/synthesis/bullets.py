"""Deterministic bullet derivation. Computed by collector, passed to model
as input — never inferred by the model."""
from typing import Iterable, Literal

Bullet = Literal["red", "amber", "sand"]


def derive_bullet(status: str, events: Iterable[dict]) -> Bullet:
    """Compute a project's bullet color from its status + window events.

    Rules (design spec section 8):
      red    if >=1 merged PR OR >=1 release OR (active AND >=3 commits)
      amber  if >=1 commit AND not red
      sand   otherwise (incl. all archived projects)
    """
    if status == "archived":
        return "sand"

    kinds = [e.get("kind") for e in events]
    commits = sum(1 for k in kinds if k == "commit")
    merged = any(k == "pr_merged" for k in kinds)
    released = any(k == "release" for k in kinds)

    if merged or released:
        return "red"
    if status == "active" and commits >= 3:
        return "red"
    if commits >= 1:
        return "amber"
    return "sand"


def derive_active_count(projects: list[dict]) -> str:
    """Count of projects with red bullet, zero-padded to 2 digits."""
    n = sum(1 for p in projects if p.get("bullet") == "red")
    return f"{n:02d}"
