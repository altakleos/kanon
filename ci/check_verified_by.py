"""CI validator for invariant_coverage: frontmatter in specs.

Checks:
- Accepted specs without fixtures_deferred: every INV-* anchor has a key
  in invariant_coverage: (hard error if missing).
- Every key in invariant_coverage: matches an INV-* anchor (stale entry error).
- Every verification target resolves: file exists, and for ::test_func targets
  the function definition is found via static grep.
- Specs with fixtures_deferred: missing keys are warnings, not errors.

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

_ANCHOR_RE = re.compile(r"<!--\s*(INV-[a-z][a-z0-9-]*-[a-z][a-z0-9-]*)\s*-->")
_FUNC_RE = re.compile(r"(?:async\s+)?def\s+(\w+)\s*\(")


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    fm = yaml.safe_load(text[4:end])
    return fm if isinstance(fm, dict) else {}


def _find_anchors(text: str) -> list[str]:
    return _ANCHOR_RE.findall(text)


def check(
    specs_root: Path, repo_root: Path | None = None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if repo_root is None:
        repo_root = specs_root.parent.parent

    for spec_path in sorted(specs_root.glob("*.md")):
        if spec_path.name.startswith("_") or spec_path.name == "README.md":
            continue
        text = spec_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        status = fm.get("status")
        if status != "accepted":
            continue

        anchors = _find_anchors(text)
        anchor_set = set(anchors)
        coverage = fm.get("invariant_coverage") or {}
        is_deferred = bool(fm.get("fixtures_deferred"))
        report = warnings if is_deferred else errors

        # Check every anchor has a coverage key
        for anchor in anchors:
            if anchor not in coverage:
                report.append(
                    f"{spec_path.name}: anchor {anchor} missing from invariant_coverage"
                )

        # Check for stale entries
        for key in coverage:
            if key not in anchor_set:
                errors.append(
                    f"{spec_path.name}: invariant_coverage key {key} "
                    f"does not match any anchor in spec"
                )

        # Resolve targets
        for key, targets in coverage.items():
            if not isinstance(targets, list):
                errors.append(
                    f"{spec_path.name}: invariant_coverage.{key} must be a list"
                )
                continue
            for target in targets:
                if "::" in target:
                    file_part, func_name = target.rsplit("::", 1)
                    fpath = repo_root / file_part
                    if not fpath.is_file():
                        errors.append(
                            f"{spec_path.name}: target {target} — file not found"
                        )
                        continue
                    src = fpath.read_text(encoding="utf-8")
                    funcs = {m.group(1) for m in _FUNC_RE.finditer(src)}
                    if func_name not in funcs:
                        errors.append(
                            f"{spec_path.name}: target {target} — "
                            f"function {func_name} not found in {file_part}"
                        )
                else:
                    fpath = repo_root / target
                    if not fpath.is_file():
                        errors.append(
                            f"{spec_path.name}: target {target} — file not found"
                        )

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--specs", type=Path, default=_DEFAULT_SPECS)
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    args = parser.parse_args(argv)

    errors, warnings = check(args.specs, args.repo_root)

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
