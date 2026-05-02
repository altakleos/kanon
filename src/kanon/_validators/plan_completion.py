"""Plan completion validator (kanon-sdd depth 1+).

Checks that plans with ``status: done`` in YAML frontmatter have all
top-level task checkboxes ticked (``- [x]`` or ``- [~]``).
"""
from __future__ import annotations

import re
from pathlib import Path


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag plans whose status conflicts with their acceptance criteria."""
    plans_dir = target / "docs" / "plans"
    if not plans_dir.is_dir():
        return
    unchecked_re = re.compile(r"^- \[ \]", re.MULTILINE)
    # Per ADR-0049 PR D: plans partitioned into active/ + archive/.
    # rglob recurses into subdirs while preserving root-level scan.
    for p in sorted(plans_dir.rglob("*.md")):
        if p.name.startswith("_") or p.name in ("README.md", "roadmap.md"):
            continue
        text = p.read_text(encoding="utf-8")
        status = _parse_status(text)
        if status != "done":
            continue
        unchecked = unchecked_re.findall(text)
        if unchecked:
            errors.append(
                f"plan-completion: {p.name}: status is 'done' but has "
                f"{len(unchecked)} unchecked task(s)"
            )


def _parse_status(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    if end < 0:
        return ""
    for line in text[4:end].splitlines():
        m = re.match(r"^status:\s*(.+)$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return ""
