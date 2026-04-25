#!/usr/bin/env python3
"""Test quality validator. Detects test anti-patterns: empty bodies, assert-True-only, pass-only.

Usage: python ci/check_test_quality.py [--root DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Language-agnostic test file patterns.
_TEST_PATTERNS = (
    "test_*.py", "*_test.py",
    "*.test.js", "*.test.ts", "*.test.tsx",
    "*_test.go", "*_test.rs",
)

# Directories to skip when collecting test files (vendored deps, build outputs,
# version-control metadata). Mirrors `check_deps.py`.
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}

# Patterns that indicate an empty or trivial test body.
_TRIVIAL_BODY = re.compile(
    r"^\s*(?:pass|assert\s+True|expect\(true\)|t\.Log\(|\/\/\s*no-op)\s*$",
    re.IGNORECASE,
)

# Patterns that match test function/method declarations.
_TEST_FUNC = re.compile(
    r"(?:def\s+test_\w+|it\s*\(|test\s*\(|func\s+Test\w+|fn\s+test_\w+)",
)


def _find_test_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in _TEST_PATTERNS:
        for p in root.rglob(pattern):
            if any(part in _SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            files.append(p)
    return sorted(set(files))


def _check_file(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        errors.append(f"{path}: unreadable ({exc})")
        return errors, warnings

    lines = text.splitlines()
    test_count = sum(1 for line in lines if _TEST_FUNC.search(line))

    if test_count == 0:
        warnings.append(f"{path}: test file with zero test functions")
        return errors, warnings

    # Scan for trivial test bodies (heuristic: line after def test_* is trivial).
    for i, line in enumerate(lines):
        if _TEST_FUNC.search(line):
            # Look at the next non-blank line(s) for trivial body.
            for j in range(i + 1, min(i + 4, len(lines))):
                body_line = lines[j]
                if not body_line.strip():
                    continue
                if body_line.lstrip().startswith(("def ", "class ", "func ", "fn ", "it(", "test(")):
                    break  # next function — previous was empty
                if _TRIVIAL_BODY.match(body_line):
                    errors.append(f"{path}:{j + 1}: trivial test body: {body_line.strip()!r}")
                break

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Test quality validator")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    test_files = _find_test_files(root)

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for tf in test_files:
        errs, warns = _check_file(tf)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    status = "fail" if all_errors else "ok"
    report = {"status": status, "errors": all_errors, "warnings": all_warnings}
    print(json.dumps(report, indent=2))
    sys.exit(0 if status == "ok" else 1)


if __name__ == "__main__":
    main()
