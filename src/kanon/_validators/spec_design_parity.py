"""Spec-design parity validator (kanon-sdd depth 3).

Warns when an accepted spec has no companion design doc and no explicit
skip declaration in its frontmatter.  A spec may declare ``design: skip``
or ``design: "Follows ADR-NNNN"`` to suppress the warning.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    specs_dir = target / "docs" / "specs"
    design_dir = target / "docs" / "design"
    if not specs_dir.is_dir():
        return

    design_slugs: set[str] = set()
    if design_dir.is_dir():
        design_slugs = {
            p.stem
            for p in design_dir.glob("*.md")
            if p.name not in ("README.md", "_template.md")
        }

    for spec_path in sorted(specs_dir.glob("*.md")):
        if spec_path.name in ("README.md", "_template.md"):
            continue
        try:
            text = spec_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end < 0:
            continue
        try:
            fm = yaml.safe_load(text[3:end])
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue
        status = fm.get("status", "")
        if status != "accepted":
            continue
        # Check for explicit skip
        design_field = fm.get("design")
        if design_field is not None:
            continue  # Any value = explicit declaration (skip, ADR ref, etc.)
        # Check for companion design doc
        if spec_path.stem not in design_slugs:
            warnings.append(
                f"spec-design-parity: {spec_path.name}: accepted spec "
                f"has no companion design doc and no 'design:' frontmatter skip"
            )
