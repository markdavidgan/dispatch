"""Display-name resolution for projects.

Resolution order (first non-empty wins):

    1. Explicit `display_name` from projects.yml (the override layer).
    2. First H1 of `<local_path>/README.md` (auto-discovered SoT).
    3. Titleize slug, respecting acronyms.yml.

Step 2 makes the README the canonical source of truth for project identity;
step 1 exists for cases where the README H1 isn't what we want surfaced
(e.g. `aether-focus` whose README says "Made with Aether" — that's a
podcast, not the umbrella name).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

# Match a markdown H1 line: optional leading space, `#`, at least one
# space/tab (NOT a newline — `\s` would let the capture group leak into the
# next line and pick up body text), then the headline, then trailing
# space/tab. MULTILINE so `^`/`$` anchor to each line.
_H1_RE = re.compile(r"^[ \t]*#[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def load_acronyms(path: Path) -> set[str]:
    """Read acronyms.yml and return a set of uppercase tokens."""
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text()) or {}
    return {str(a).upper() for a in data.get("acronyms", [])}


def extract_readme_h1(local_path: str | Path | None) -> str | None:
    """Return the first H1 in `<local_path>/README.md`, or None.

    Returns None if the path is missing, the README is missing, or no H1
    is found. Empty strings are treated as missing.
    """
    if not local_path:
        return None
    readme = Path(local_path) / "README.md"
    if not readme.exists():
        return None
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _H1_RE.search(text)
    if not match:
        return None
    headline = match.group(1).strip()
    return headline or None


def titleize_slug(slug: str, acronyms: set[str]) -> str:
    """Convert a kebab/underscore slug into a display name.

    Tokens whose uppercase form is in `acronyms` are kept ALL-CAPS.
    Other tokens get a leading capital letter only.
    """
    tokens = re.split(r"[-_]+", slug)
    out = []
    for tok in tokens:
        if not tok:
            continue
        if tok.upper() in acronyms:
            out.append(tok.upper())
        else:
            out.append(tok[:1].upper() + tok[1:])
    return " ".join(out)


def resolve_display_name(
    *,
    slug: str,
    override: str | None,
    local_path: str | Path | None,
    acronyms: set[str],
) -> str:
    """Return the canonical display name for a project.

    Follows the 3-step resolution chain. Always returns a non-empty
    string — the titleize fallback handles any slug.
    """
    if override and override.strip():
        return override.strip()
    h1 = extract_readme_h1(local_path)
    if h1:
        return h1
    return titleize_slug(slug, acronyms)
