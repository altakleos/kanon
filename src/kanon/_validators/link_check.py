"""Markdown link validator (kanon-sdd depth 2+).

Walks every ``*.md`` file under ``docs/`` and verifies that each relative
markdown link resolves to an existing file on disk.
"""
from __future__ import annotations

import re
from pathlib import Path

_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_EXTERNAL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+\-.]*:")


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag broken internal markdown links under docs/."""
    docs_dir = target / "docs"
    if not docs_dir.is_dir():
        return
    for md_path in sorted(docs_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        in_code_block = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            for match in _LINK_PATTERN.finditer(line):
                raw = match.group(1).strip()
                if not raw or raw.startswith("#") or _EXTERNAL_SCHEME.match(raw):
                    continue
                file_part = raw.split("#", 1)[0].split("?", 1)[0]
                if not file_part:
                    continue
                resolved = (md_path.parent / file_part).resolve()
                if not resolved.exists():
                    try:
                        rel = md_path.relative_to(target)
                    except ValueError:
                        rel = md_path
                    errors.append(
                        f"link-check: {rel}:{lineno}: broken link → {raw}"
                    )
