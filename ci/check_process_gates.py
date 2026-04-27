#!/usr/bin/env python3
"""Enforce plan-before-build and spec-before-design process gates.

Checks two co-presence invariants on every PR or push:

1. **Plan co-presence.** If ``src/`` files changed, a ``docs/plans/*.md``
   file with ``status:`` set to ``done``, ``accepted``, or ``in-progress``
   must be present in the diff or referenced via a ``Plan:`` commit trailer.
   Exemptable via ``Trivial-change: <reason>`` commit trailer.

2. **Spec co-presence.** If the diff adds a new ``@cli.command()``,
   ``@cli.group()``, or ``@click.command()`` decorator under ``src/``,
   a ``docs/specs/*.md`` file with ``status:`` set to ``accepted`` or
   ``provisional`` must be present or referenced via ``Spec:`` trailer.
   Never exemptable.

Operating modes:

* ``--base-ref REF``  PR mode: diff ``REF..HEAD``.
* (default)            push mode: only the most-recent commit (``HEAD``).

Output is a JSON object to stdout with ``status`` (``ok``, ``warn``,
``fail``), ``errors``, and ``warnings``. Exit 0 for ok/warn, exit 1 for
fail.

This script is a kit-internal CI gate. It has zero imports from ``kanon.*``
and requires only the standard library and git on PATH.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_PLAN_VALID_STATUSES = frozenset({"done", "accepted", "in-progress"})
_SPEC_VALID_STATUSES = frozenset({"accepted", "provisional"})

_TRIVIAL_TRAILER = re.compile(
    r"^Trivial-change:\s*(.+?)\s*$", re.MULTILINE
)
_PLAN_REF = re.compile(
    r"^Plan:\s*(docs/plans/\S+\.md)\s*$", re.MULTILINE
)
_SPEC_REF = re.compile(
    r"^Spec:\s*(docs/specs/\S+\.md)\s*$", re.MULTILINE
)
_CLI_DECORATOR = re.compile(
    r"^\+.*@(?:cli\.command|cli\.group|click\.command)\("
)


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


def _parse_frontmatter_status(text: str) -> str | None:
    """Extract ``status:`` from YAML frontmatter without PyYAML."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("status:"):
            return stripped[len("status:"):].strip()
    return None


def _read_file_status(path: Path) -> str | None:
    """Read a file and return its frontmatter status, or None."""
    try:
        return _parse_frontmatter_status(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def _changed_files(base_ref: str | None, repo: Path) -> list[str]:
    """Return files changed in the range."""
    if base_ref is not None:
        out = _git(["diff", "--name-only", f"{base_ref}..HEAD"], repo)
    else:
        out = _git(["show", "--name-only", "--pretty=", "HEAD"], repo)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _commit_messages(base_ref: str | None, repo: Path) -> str:
    """Return concatenated commit messages for the range."""
    if base_ref is not None:
        return _git(["log", "--format=%B", f"{base_ref}..HEAD"], repo)
    return _git(["log", "-1", "--format=%B", "HEAD"], repo)


def _diff_content(base_ref: str | None, repo: Path) -> str:
    """Return the actual diff content for src/ files."""
    if base_ref is not None:
        return _git(["diff", f"{base_ref}..HEAD", "--", "src/"], repo)
    return _git(["diff", "HEAD~..HEAD", "--", "src/"], repo)


def _has_trivial_override(messages: str) -> bool:
    """True if any commit has a Trivial-change trailer with non-empty value."""
    return bool(_TRIVIAL_TRAILER.search(messages))


def _has_new_cli_command(diff: str) -> bool:
    """True if the diff adds a CLI command/group decorator."""
    return any(_CLI_DECORATOR.match(line) for line in diff.splitlines())


def _find_valid_plan(
    changed: list[str], messages: str, repo: Path
) -> bool:
    """Check if a valid plan file is present in diff or referenced in commits."""
    # Check files in the diff
    for f in changed:
        if f.startswith("docs/plans/") and f.endswith(".md"):
            status = _read_file_status(repo / f)
            if status in _PLAN_VALID_STATUSES:
                return True
    # Check commit message references
    for m in _PLAN_REF.finditer(messages):
        path = repo / m.group(1)
        status = _read_file_status(path)
        if status in _PLAN_VALID_STATUSES:
            return True
    return False


def _find_valid_spec(
    changed: list[str], messages: str, repo: Path
) -> bool:
    """Check if a valid spec file is present in diff or referenced in commits."""
    for f in changed:
        if f.startswith("docs/specs/") and f.endswith(".md"):
            status = _read_file_status(repo / f)
            if status in _SPEC_VALID_STATUSES:
                return True
    for m in _SPEC_REF.finditer(messages):
        path = repo / m.group(1)
        status = _read_file_status(path)
        if status in _SPEC_VALID_STATUSES:
            return True
    return False


def check_process_gates(
    repo_root: Path,
    base_ref: str | None = None,
) -> dict:
    """Run process-gate checks. Returns the JSON-serialisable report dict."""
    errors: list[str] = []
    warnings: list[str] = []

    changed = _changed_files(base_ref, repo_root)
    has_src = any(f.startswith("src/") for f in changed)

    if not has_src:
        return {"status": "ok", "errors": [], "warnings": []}

    messages = _commit_messages(base_ref, repo_root)
    trivial = _has_trivial_override(messages)

    # Plan co-presence check (exemptable by Trivial-change trailer)
    if not trivial and not _find_valid_plan(changed, messages, repo_root):
            errors.append(
                "Plan co-presence violation: src/ files changed but no "
                "docs/plans/ file with status done/accepted/in-progress "
                "found. Add a plan file or use 'Trivial-change: <reason>' "
                "commit trailer."
            )

    # Spec co-presence check (never exemptable)
    diff = _diff_content(base_ref, repo_root)
    if _has_new_cli_command(diff) and not _find_valid_spec(changed, messages, repo_root):
            errors.append(
                "Spec co-presence violation: new CLI command decorator "
                "added under src/ but no docs/specs/ file with status "
                "accepted/provisional found. Add a spec file or reference "
                "one via 'Spec: docs/specs/<slug>.md' commit trailer."
            )

    status = "fail" if errors else ("warn" if warnings else "ok")
    return {"status": status, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help=(
            "Compare diff of BASE_REF..HEAD (PR mode). "
            "Omit to check only the HEAD commit (push mode)."
        ),
    )
    parser.add_argument(
        "--repo", default=".", help="Repository root (default: cwd)."
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    report = check_process_gates(repo, args.base_ref)
    print(json.dumps(report))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
