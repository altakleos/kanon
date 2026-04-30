"""Index consistency validator (kanon-sdd depth 1+).

Scans scaffolded index README files for duplicate link-target entries.
"""
from __future__ import annotations

import re
from pathlib import Path

# Matches markdown table cells with links: | [slug](filename.md) | ... |
_LINK_CELL_RE = re.compile(r"\|\s*\[[^\]]*\]\(([^)]+)\)")

_INDEX_DIRS = ("decisions", "plans", "specs", "design")


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag docs/ files missing from their directory's README index."""
    docs_dir = target / "docs"
    if not docs_dir.is_dir():
        return
    for subdir in _INDEX_DIRS:
        readme = docs_dir / subdir / "README.md"
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        seen: dict[str, int] = {}  # link-target -> first line number
        in_code_block = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            m = _LINK_CELL_RE.search(line)
            if not m:
                continue
            link_target = m.group(1).strip()
            if link_target in seen:
                errors.append(
                    f"index-consistency: docs/{subdir}/README.md:{lineno}: "
                    f"duplicate entry '{link_target}' "
                    f"(first seen at line {seen[link_target]})"
                )
            else:
                seen[link_target] = lineno
