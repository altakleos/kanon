"""Test-import validator (kanon-testing depth 2+).

Scans ``tests/ci/test_*.py`` for the canonical CI-script path-construction
pattern and verifies the referenced script exists on disk.
"""
from __future__ import annotations

import re
from pathlib import Path

# Matches: _SCRIPT_PATH = _REPO_ROOT / "ci" / "check_foo.py"
# Also:    _VALIDATOR_PATH = _REPO_ROOT / "ci" / "release-preflight.py"
_CI_REF_RE = re.compile(
    r'_(?:SCRIPT|VALIDATOR)_PATH\s*=\s*_REPO_ROOT\s*/\s*"ci"\s*/\s*"([^"]+)"'
)


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    tests_ci = target / "tests" / "ci"
    if not tests_ci.is_dir():
        return
    for test_file in sorted(tests_ci.glob("test_*.py")):
        text = test_file.read_text(encoding="utf-8")
        for m in _CI_REF_RE.finditer(text):
            script_name = m.group(1)
            script_path = target / "ci" / script_name
            if not script_path.is_file():
                errors.append(
                    f"test-import-check: tests/ci/{test_file.name}: "
                    f"references ci/{script_name} which does not exist"
                )
