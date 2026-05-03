#!/usr/bin/env python3
"""Release preflight checks. Usage: python ci/release-preflight.py --tag vX.Y.Z"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _local_python() -> str:
    """Return the Python interpreter from the local ``.venv/``.

    When running inside a git worktree, the worktree must have its own
    ``.venv/`` (created by ``uv sync``) so that editable installs,
    console-script entry points, and all tool invocations resolve to
    the worktree's source — not the main tree's.
    """
    venv_python = Path.cwd() / ".venv" / "bin" / "python"
    if not venv_python.exists():
        sys.exit(
            "ERROR: No local .venv/bin/python found.\n"
            "Run `uv sync` in this directory first.\n"
            "(Git worktrees need their own .venv — see worktree-lifecycle protocol.)"
        )
    return str(venv_python)


def _find_version() -> str | None:
    # Per ADR-0050 Option A: substrate kernel source is at `kernel/` (was `src/kanon/`).
    # Scan both for backward compatibility with any consumer-side layout.
    for root in ("kernel", "src"):
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        for candidate in root_path.rglob("__init__.py"):
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

    # All tool invocations use the local venv's Python so that
    # editable installs and console-script entry points resolve to
    # the current working directory's source tree.
    py = _local_python()
    venv_bin = str(Path(py).parent)

    # Test suite
    results["tests"] = _check("pytest", [py, "-m", "pytest", "-q"])

    # Lint
    results["lint"] = _check("ruff", [py, "-m", "ruff", "check", "."])

    # kanon verify — use the local venv's kanon entry point, not the
    # tool-installed one (which has a hardcoded shebang to a different
    # Python interpreter and would import from the wrong source tree).
    kanon_bin = str(Path(venv_bin) / "kanon")
    results["verify"] = _check("kanon", [kanon_bin, "verify", "."])

    ok = all(results.values())
    print(json.dumps({"tag": args.tag, "ok": ok, "checks": results}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
