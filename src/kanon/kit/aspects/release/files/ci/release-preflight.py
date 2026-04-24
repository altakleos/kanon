#!/usr/bin/env python3
"""Release preflight checks. Usage: python ci/release-preflight.py --tag vX.Y.Z"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _find_version() -> str | None:
    for candidate in Path("src").rglob("__init__.py"):
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', candidate.read_text())
        if m:
            return m.group(1)
    return None


def _check(name: str, cmd: list[str]) -> bool:
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Release preflight checks")
    parser.add_argument("--tag", required=True, help="Release tag, e.g. v1.2.3")
    args = parser.parse_args()

    expected = args.tag.lstrip("v")
    results: dict[str, bool] = {}

    # Version match
    actual = _find_version()
    results["version_match"] = actual == expected

    # CHANGELOG entry
    changelog = Path("CHANGELOG.md")
    results["changelog_entry"] = changelog.exists() and expected in changelog.read_text()

    # Test suite
    results["tests"] = _check("pytest", [sys.executable, "-m", "pytest", "-q"])

    # Lint
    results["lint"] = _check("ruff", [sys.executable, "-m", "ruff", "check", "."])

    # kanon verify
    results["verify"] = _check("kanon", ["kanon", "verify", "."])

    ok = all(results.values())
    print(json.dumps({"tag": args.tag, "ok": ok, "checks": results}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
