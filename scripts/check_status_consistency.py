#!/usr/bin/env python3
"""Status consistency checker. Detects stale artifact statuses via cross-document heuristics.

Usage: python ci/check_status_consistency.py [--root DIR]

Findings are warnings (exit 0). Designed as a complement to the completion-checklist
protocol's Step 9 — catches what agents miss.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter as a simple key-value dict (flat, no nesting)."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(.+)$", line)
        if m:
            result[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return result


def check_design_spec_drift(root: Path) -> list[str]:
    """Warn if a design doc is draft but its implementing spec is accepted."""
    warnings: list[str] = []
    design_dir = root / "docs" / "design"
    if not design_dir.is_dir():
        return warnings
    for p in sorted(design_dir.glob("*.md")):
        if p.name.startswith("_") or p.name == "README.md":
            continue
        fm = _parse_frontmatter(p.read_text(encoding="utf-8"))
        if fm.get("status") != "draft":
            continue
        implements = fm.get("implements", "")
        if not implements:
            continue
        spec_path = root / implements
        if not spec_path.is_file():
            continue
        spec_fm = _parse_frontmatter(spec_path.read_text(encoding="utf-8"))
        if spec_fm.get("status") == "accepted":
            warnings.append(
                f"{p.name}: status is 'draft' but implements "
                f"{spec_path.name} which is 'accepted'"
            )
    return warnings


def check_plan_status_drift(root: Path) -> list[str]:
    """Warn if a plan's status contradicts its task checkbox state."""
    warnings: list[str] = []
    plans_dir = root / "docs" / "plans"
    if not plans_dir.is_dir():
        return warnings
    checked_re = re.compile(r"^- \[x\]", re.MULTILINE | re.IGNORECASE)
    unchecked_re = re.compile(r"^- \[ \]", re.MULTILINE)
    for p in sorted(plans_dir.glob("*.md")):
        if p.name.startswith("_") or p.name in ("README.md", "roadmap.md"):
            continue
        text = p.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        status = fm.get("status", "")
        checked = len(checked_re.findall(text))
        unchecked = len(unchecked_re.findall(text))
        if status == "done" and unchecked > 0:
            warnings.append(
                f"{p.name}: status is 'done' but has {unchecked} unchecked "
                f"task(s) (use `- [x]` for done, or `- [~]` with a NOTE to defer)"
            )
        if status == "planned" and checked > 0:
            warnings.append(
                f"{p.name}: status is 'planned' but has {checked} checked "
                f"task(s) — should be 'in-progress' or 'done'"
            )
    return warnings


def check(root: Path) -> tuple[list[str], list[str]]:
    """Run all status consistency checks. Returns (errors, warnings)."""
    warnings: list[str] = []
    warnings.extend(check_design_spec_drift(root))
    warnings.extend(check_plan_status_drift(root))
    return [], warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Status consistency checker")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    errors, warnings = check(root)
    status = "fail" if errors else "ok"
    report = {"root": str(root), "errors": errors, "warnings": warnings, "status": status}
    print(json.dumps(report, indent=2))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
