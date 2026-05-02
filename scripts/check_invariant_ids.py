"""CI validator for INV-* invariant anchors.

Checks:
- Accepted specs: every invariant has an INV-* anchor (hard error if missing).
- Anchor uniqueness within each spec.
- Spec-slug in anchor matches the file's stem.
- Cross-reference resolution: every INV-* reference in docs/ resolves to an anchor.

Exit codes:
    0 — all checks pass
    1 — one or more errors
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SPECS = _REPO_ROOT / "docs" / "specs"
_DEFAULT_DOCS = _REPO_ROOT / "docs"

_ANCHOR_RE = re.compile(r"<!--\s*(INV-[a-z][a-z0-9-]*-[a-z][a-z0-9-]*)\s*-->")
_INVARIANT_RE = re.compile(r"^\d+\.\s+\*\*")
_REF_RE = re.compile(r"INV-[a-z][a-z0-9-]*-[a-z][a-z0-9-]*")


def _parse_status(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    fm = yaml.safe_load(text[4:end])
    if isinstance(fm, dict):
        return fm.get("status")
    return None


def check(specs_root: Path, docs_root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    all_anchors: set[str] = set()

    # Scan spec files
    for spec_path in sorted(specs_root.glob("*.md")):
        if spec_path.name.startswith("_") or spec_path.name == "README.md":
            continue
        text = spec_path.read_text(encoding="utf-8")
        status = _parse_status(text)
        slug = spec_path.stem
        lines = text.split("\n")

        # Find anchors in this file
        file_anchors: list[str] = []
        for line in lines:
            m = _ANCHOR_RE.search(line)
            if m:
                file_anchors.append(m.group(1))

        # Check anchor uniqueness
        seen: set[str] = set()
        for anchor in file_anchors:
            if anchor in seen:
                errors.append(f"{spec_path.name}: duplicate anchor {anchor}")
            seen.add(anchor)
            all_anchors.add(anchor)

        # Check slug consistency
        for anchor in file_anchors:
            parts = anchor.split("-", 2)  # INV-<slug>-<name>
            if len(parts) >= 3:
                # Reconstruct slug: everything between first "INV-" and last "-<short-name>"
                anchor_slug = anchor[4:]  # strip "INV-"
                # The slug is everything up to the last component that matches the short-name
                # We need to match against the file stem
                if not anchor_slug.startswith(slug + "-"):
                    errors.append(
                        f"{spec_path.name}: anchor {anchor} slug does not match "
                        f"file stem '{slug}'"
                    )

        # For accepted specs: check every invariant has an anchor
        if status == "accepted":
            in_invariants = False
            for i, line in enumerate(lines):
                if line.strip() == "## Invariants":
                    in_invariants = True
                    continue
                if in_invariants and line.startswith("## "):
                    break
                if in_invariants and _INVARIANT_RE.match(line):
                    # Check previous line for anchor
                    if i > 0 and _ANCHOR_RE.search(lines[i - 1]):
                        pass  # good
                    else:
                        errors.append(
                            f"{spec_path.name}: accepted spec invariant at line "
                            f"{i + 1} missing INV-* anchor"
                        )

    # Cross-reference resolution: scan all docs for INV-* references
    for md_path in sorted(docs_root.rglob("*.md")):
        if md_path.name.startswith("_") and md_path.name != "_template.md":
            continue
        text = md_path.read_text(encoding="utf-8")
        for m in _REF_RE.finditer(text):
            ref = m.group(0)
            # Skip if this is an anchor definition (inside <!-- -->)
            line_start = text.rfind("\n", 0, m.start()) + 1
            line = text[line_start:text.find("\n", m.end())]
            if "<!--" in line and "-->" in line:
                continue
            # Skip template/example references
            if "<spec-slug>" in ref or "<short-name>" in ref:
                continue
            if ref not in all_anchors:
                rel = md_path.relative_to(docs_root)
                errors.append(f"docs/{rel}: unresolved reference {ref}")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--specs", type=Path, default=_DEFAULT_SPECS)
    parser.add_argument("--docs", type=Path, default=_DEFAULT_DOCS)
    args = parser.parse_args(argv)

    errors, warnings = check(args.specs, args.docs)

    report: dict[str, Any] = {
        "specs": str(args.specs),
        "errors": errors,
        "warnings": warnings,
        "status": "fail" if errors else "ok",
    }
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
