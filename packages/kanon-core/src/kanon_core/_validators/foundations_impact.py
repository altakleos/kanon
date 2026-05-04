"""Foundations impact validator (kanon-sdd depth 2).

Traces ``realizes:`` and ``stressed_by:`` frontmatter references in specs
to retired or superseded foundations and emits an affected-spec list.
Also flags broken references (slugs that resolve to no existing file).
"""
from __future__ import annotations

from pathlib import Path

import yaml


def _parse_frontmatter(path: Path) -> dict | None:
    """Return parsed YAML frontmatter or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    try:
        fm = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag specs referencing superseded or missing foundations."""
    specs_dir = target / "docs" / "specs"
    if not specs_dir.is_dir():
        return

    # Collect foundation slugs and their statuses
    foundation_slugs: dict[str, str] = {}  # slug -> status
    for subdir in ("principles", "personas"):
        d = target / "docs" / "foundations" / subdir
        if not d.is_dir():
            continue
        for p in d.glob("*.md"):
            if p.name in ("README.md", "_template.md"):
                continue
            fm = _parse_frontmatter(p)
            status = fm.get("status", "accepted") if fm else "accepted"
            foundation_slugs[p.stem] = status

    if not foundation_slugs:
        return

    superseded = {s for s, st in foundation_slugs.items() if st == "superseded"}

    for spec_path in sorted(specs_dir.glob("*.md")):
        if spec_path.name in ("README.md", "_template.md"):
            continue
        fm = _parse_frontmatter(spec_path)
        if not fm:
            continue
        for field in ("realizes", "stressed_by"):
            refs = fm.get(field)
            if not refs:
                continue
            if isinstance(refs, str):
                refs = [refs]
            for slug in refs:
                if slug in superseded:
                    warnings.append(
                        f"foundations-impact: {spec_path.name} references "
                        f"superseded foundation {slug} via {field}"
                    )
                elif slug not in foundation_slugs:
                    warnings.append(
                        f"foundations-impact: {spec_path.name} references "
                        f"unknown foundation {slug} via {field}"
                    )
