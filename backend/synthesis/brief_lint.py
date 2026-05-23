"""Post-synthesis quality heuristics. Returns warnings; never blocks."""
import re
from dispatch.synthesis.schema import LeadFiling, AddendumFiling

BANNED_PHRASES = [
    "excited to announce",
    "in today's fast-paced",
    "leverage", "leveraging",
    "best-in-class",
    "robust",
    "game-changing",
    "synergize", "synergy",
    "delighted to share",
    "stay tuned",
]


def lint_lead(f: LeadFiling) -> list[str]:
    warnings: list[str] = []
    blob = (f.lead_headline + " " + f.lead_body).lower()
    for phrase in BANNED_PHRASES:
        if phrase in blob:
            warnings.append(f"banned phrase: '{phrase}'")
    if "!" in f.lead_headline:
        warnings.append("exclamation in headline")
    if len(f.lead_headline) > 100:
        warnings.append(f"headline too long: {len(f.lead_headline)} chars")
    if f.active_count != f"{sum(1 for b in f.project_lines if b.bullet == 'red'):02d}":
        warnings.append("active_count disagrees with project red bullet count")
    return warnings


def lint_addendum(a: AddendumFiling) -> list[str]:
    warnings: list[str] = []
    blob = a.addendum_body.lower()
    for phrase in BANNED_PHRASES:
        if phrase in blob:
            warnings.append(f"banned phrase: '{phrase}'")
    if "!" in a.addendum_body:
        warnings.append("exclamation in addendum")
    return warnings
