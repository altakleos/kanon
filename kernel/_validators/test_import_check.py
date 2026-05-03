"""Test-import validator (kanon-testing depth 2+).

Scans ``tests/scripts/test_*.py`` for the canonical CI-script path-construction
pattern and verifies the referenced script exists on disk.
"""
from __future__ import annotations

import re
from pathlib import Path

# Matches: _SCRIPT_PATH = _REPO_ROOT / "scripts" / "check_foo.py"
# Also:    _VALIDATOR_PATH = _REPO_ROOT / "scripts" / "release-preflight.py"
_CI_REF_RE = re.compile(
    r'_(?:SCRIPT|VALIDATOR)_PATH\s*=\s*_REPO_ROOT\s*/\s*"scripts"\s*/\s*"([^"]+)"'
)


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag CI checker scripts that are not imported by a test file."""
    tests_dir = target / "tests" / "scripts"
    if not tests_dir.is_dir():
        return
    for test_file in sorted(tests_dir.glob("test_*.py")):
        text = test_file.read_text(encoding="utf-8")
        for m in _CI_REF_RE.finditer(text):
            script_name = m.group(1)
            script_path = target / "scripts" / script_name
            if not script_path.is_file():
                errors.append(
                    f"test-import-check: tests/scripts/{test_file.name}: "
                    f"references scripts/{script_name} which does not exist"
                )
