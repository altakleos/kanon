#!/usr/bin/env python3
"""Check commit messages against Conventional Commits format.

Validates that commit messages in a PR or push follow the Conventional
Commits convention used by this project::

    <type>: <description>

Where ``<type>`` is one of: feat, fix, docs, refactor, test, chore.

This is a **soft check** — it reports warnings but never fails the build.
The project treats Conventional Commits as convention, not a hard gate.

Operating modes:

* ``--base-ref REF``  PR mode: check every commit in ``REF..HEAD``.
* (default)            push mode: only the most-recent commit (``HEAD``).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_VALID_TYPES = frozenset({"feat", "fix", "docs", "refactor", "test", "chore"})

_CONVENTIONAL = re.compile(
    r"^(?P<type>[a-z]+)(?:\(.+?\))?!?:\s+\S"
)

# Merge commits are always acceptable.
_MERGE = re.compile(r"^Merge ")


def _git(args: list[str], cwd: Path) -> str:
    """Run git; return stdout (or empty string on non-zero exit)."""
    result = subprocess.run(  # noqa: S603 — args fixed by caller
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _commit_subjects(base_ref: str | None, repo: Path) -> list[tuple[str, str]]:
    """Return list of (short-sha, subject) tuples for the range."""
    if base_ref is not None:
        out = _git(["log", "--format=%h %s", f"{base_ref}..HEAD"], repo)
    else:
        out = _git(["log", "-1", "--format=%h %s", "HEAD"], repo)
    pairs = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, subject = line.partition(" ")
        pairs.append((sha, subject))
    return pairs


def check_commit_messages(
    repo_root: Path,
    base_ref: str | None = None,
) -> dict:
    """Run commit-message checks. Returns the JSON-serialisable report."""
    warnings: list[str] = []

    for sha, subject in _commit_subjects(base_ref, repo_root):
        if _MERGE.match(subject):
            continue

        match = _CONVENTIONAL.match(subject)
        if not match:
            warnings.append(
                f"{sha}: not Conventional Commits format — expected "
                f"'<type>: <description>' where type is one of: "
                f"{', '.join(sorted(_VALID_TYPES))}. "
                f"Got: {subject!r}"
            )
            continue

        commit_type = match.group("type")
        if commit_type not in _VALID_TYPES:
            warnings.append(
                f"{sha}: unknown type '{commit_type}' — expected one of: "
                f"{', '.join(sorted(_VALID_TYPES))}. "
                f"Got: {subject!r}"
            )

    status = "warn" if warnings else "ok"
    return {"status": status, "errors": [], "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check commit messages against Conventional Commits format."
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Compare commits in BASE_REF..HEAD (PR mode).",
    )
    parser.add_argument(
        "--repo", default=".", help="Repository root (default: cwd).",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    report = check_commit_messages(repo, args.base_ref)
    print(json.dumps(report, indent=2))
    return 0  # Always exit 0 — soft check, warnings only


if __name__ == "__main__":
    sys.exit(main())
