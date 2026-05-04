"""Foundations coherence validator (kanon-sdd depth 2).

Warns when vision.md has changed but no principle or persona file has been
updated since, indicating the foundations layer may be internally inconsistent.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag stale foundations when vision.md changes without downstream updates."""
    vision = target / "docs" / "foundations" / "vision.md"
    if not vision.is_file():
        return

    principles = target / "docs" / "foundations" / "principles"
    personas = target / "docs" / "foundations" / "personas"
    if not principles.is_dir() and not personas.is_dir():
        return

    current_hash = hashlib.sha256(vision.read_bytes()).hexdigest()

    sha_file = target / ".kanon" / "foundations-vision.sha"
    if not sha_file.is_file():
        sha_file.parent.mkdir(parents=True, exist_ok=True)
        sha_file.write_text(current_hash, encoding="utf-8")
        return

    stored_hash = sha_file.read_text(encoding="utf-8").strip()
    if current_hash == stored_hash:
        return

    # Vision changed — check if any downstream .md file is newer than vision.md
    vision_mtime = vision.stat().st_mtime
    for d in (principles, personas):
        if not d.is_dir():
            continue
        for md in d.glob("*.md"):
            if md.stat().st_mtime > vision_mtime:
                # Downstream file updated after vision change — auto-clear
                sha_file.write_text(current_hash, encoding="utf-8")
                return

    warnings.append(
        "foundations-coherence: vision.md has changed; "
        "principles/ and personas/ may need review for alignment."
    )
