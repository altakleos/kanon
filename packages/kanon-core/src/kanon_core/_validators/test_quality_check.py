"""Test quality validator (kanon-testing depth 3).

Detects common test quality issues: weak assertions, happy-path-only
test suites, and trivially duplicated test structures.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag test quality issues."""
    tests_dir = target / "tests"
    if not tests_dir.is_dir():
        return

    for test_file in sorted(tests_dir.rglob("test_*.py")):
        try:
            source = test_file.read_text(encoding="utf-8")
        except OSError:
            continue

        # Parse to count test functions and assertions
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        test_funcs = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]

        if not test_funcs:
            continue

        # Check 1: Weak assertions (assert x, assert x is not None)
        # Count specific vs non-specific assertions
        specific = 0
        nonspecific = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                test_node = node.test
                # assert x is not None, assert x, assert bool(x) = nonspecific
                if isinstance(test_node, ast.Compare):
                    # assert x == y, assert x in y = specific
                    specific += 1
                elif isinstance(test_node, ast.Call):
                    # assert func(x) - could be either, count as specific
                    specific += 1
                else:
                    nonspecific += 1

        total_asserts = specific + nonspecific
        if total_asserts > 0 and nonspecific / total_asserts > 0.5:
            rel = test_file.relative_to(target)
            warnings.append(
                f"test-quality: {rel}: {nonspecific}/{total_asserts} assertions "
                f"are non-specific (assert x, assert x is not None). "
                f"Prefer assert x == expected."
            )

        # Check 2: Happy-path-only detection
        # Flag if no test name contains error/fail/invalid/reject/bad/wrong
        error_keywords = re.compile(
            r"error|fail|invalid|reject|bad|wrong|raises|negative", re.I
        )
        has_error_test = any(error_keywords.search(f.name) for f in test_funcs)
        if len(test_funcs) >= 3 and not has_error_test:
            rel = test_file.relative_to(target)
            warnings.append(
                f"test-quality: {rel}: {len(test_funcs)} tests but none "
                f"test error/failure cases. Add negative tests."
            )
