"""Wheel contents validator (maintainer-side, CI only).

Asserts a built wheel satisfies the invariants in docs/specs/release-process.md
and docs/specs/release-communication.md:

- **Required files present.** The engine bundle ships complete.
- **Required directories non-empty.** `prompts/`, `schemas/`, `profiles/` each
  contain at least one entry.
- **No forbidden path prefixes.** User-instance content never leaks into the
  wheel.
- **Version concordance.** `sensei/__init__.py.__version__` matches the
  supplied `--tag` (leading `v` stripped). Literal string comparison — the
  release process requires the maintainer to keep them exactly in sync.
- **Changelog entry.** `CHANGELOG.md` (repo root, not in the wheel — ships
  in the sdist) carries a dated entry for the tag's version.

Exit codes:
    0 — all checks pass
    1 — one or more required files or directories missing
    2 — one or more forbidden paths present
    3 — version concordance failure (or version unreadable)
    4 — changelog missing entry for the tag's version

Prints a single JSON report to stdout regardless of exit code.

Invoked by `.github/workflows/release.yml` as the final gate before the
publish job runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

REQUIRED_FILES: tuple[str, ...] = (
    "kanon/__init__.py",
    "kanon/cli.py",
    "kanon/_atomic.py",
    "kanon/templates/harnesses.yaml",
    "kanon/templates/tier-0/AGENTS.md",
    "kanon/templates/tier-0/CLAUDE.md",
    "kanon/templates/tier-1/AGENTS.md",
    "kanon/templates/tier-1/docs/development-process.md",
    "kanon/templates/tier-2/AGENTS.md",
    "kanon/templates/tier-3/AGENTS.md",
    "kanon/templates/agents-md-sections/plan-before-build.md",
    "kanon/templates/agents-md-sections/spec-before-design.md",
)

REQUIRED_DIRS: tuple[str, ...] = (
    "kanon/templates/tier-0/",
    "kanon/templates/tier-1/",
    "kanon/templates/tier-2/",
    "kanon/templates/tier-3/",
    "kanon/templates/agents-md-sections/",
)

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    # Consumer-state paths that should never leak into the distributed wheel.
    ".kanon/",
    "docs/",               # kit's own docs/ are not shipped in the wheel
    "tests/",
    "ci/",
    ".github/",
    ".venv/",
)

FORBIDDEN_EXACT: tuple[str, ...] = (
    "AGENTS.md",           # kit's own AGENTS.md not shipped (only templates)
    "CLAUDE.md",           # same — kit's own shim is not shipped
    ".gitignore",
)

_VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

# Keep a Changelog 1.1 version heading:  ## [0.1.0a1] — 2026-04-20  (em dash or hyphen separator).
_CHANGELOG_HEADING_PATTERN_TEMPLATE = r"^##\s+\[{version}\]\s*[\u2014\-]\s*\d{{4}}-\d{{2}}-\d{{2}}\s*$"

_DEFAULT_CHANGELOG_PATH = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def _strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def _extract_version(init_content: str) -> str | None:
    m = _VERSION_PATTERN.search(init_content)
    return m.group(1) if m else None


def _changelog_entry_status(changelog_path: Path, version: str) -> tuple[str, str | None]:
    """Return ('ok'|'missing_file'|'missing_entry', error-message-or-None)."""
    if not changelog_path.is_file():
        return "missing_file", f"CHANGELOG.md not found at {changelog_path}"
    content = changelog_path.read_text(encoding="utf-8")
    pattern = _CHANGELOG_HEADING_PATTERN_TEMPLATE.format(version=re.escape(version))
    if re.search(pattern, content, flags=re.MULTILINE):
        return "ok", None
    return "missing_entry", f"no dated entry for version {version!r} in {changelog_path}"


def check_wheel(wheel_path: Path, tag: str, changelog_path: Path | None = None) -> tuple[int, dict[str, Any]]:
    """Validate `wheel_path` against `tag`. Returns (exit_code, report)."""
    with zipfile.ZipFile(wheel_path) as z:
        names = z.namelist()
        try:
            init_content = z.read("kanon/__init__.py").decode("utf-8")
        except KeyError:
            init_content = ""
    name_set = set(names)

    missing_files = [f for f in REQUIRED_FILES if f not in name_set]
    missing_dirs = [d for d in REQUIRED_DIRS if not any(n.startswith(d) for n in names)]

    forbidden: list[str] = []
    for n in names:
        if any(n.startswith(p) for p in FORBIDDEN_PREFIXES) or n in FORBIDDEN_EXACT:
            forbidden.append(n)

    expected = _strip_v(tag)
    actual = _extract_version(init_content)

    changelog_path = changelog_path or _DEFAULT_CHANGELOG_PATH
    changelog_status, changelog_err = _changelog_entry_status(changelog_path, expected)

    report: dict[str, Any] = {
        "wheel": str(wheel_path),
        "tag": tag,
        "expected_version": expected,
        "actual_version": actual,
        "missing_files": missing_files,
        "missing_dirs": missing_dirs,
        "forbidden": forbidden,
        "changelog_path": str(changelog_path),
        "changelog_status": changelog_status,
    }

    if missing_files or missing_dirs:
        report["status"] = "missing"
        return 1, report
    if forbidden:
        report["status"] = "forbidden"
        return 2, report
    if actual != expected:
        report["status"] = "version_mismatch"
        return 3, report
    if changelog_status != "ok":
        report["status"] = "changelog_missing_entry"
        report["changelog_error"] = changelog_err
        return 4, report

    report["status"] = "ok"
    return 0, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--wheel", type=Path, required=True, help="Path to the built .whl file")
    parser.add_argument("--tag", required=True, help="Release tag, e.g. v0.1.0 or v0.1.0-alpha")
    parser.add_argument(
        "--changelog",
        type=Path,
        default=None,
        help=f"Path to CHANGELOG.md. Defaults to {_DEFAULT_CHANGELOG_PATH}",
    )
    args = parser.parse_args(argv)

    if not args.wheel.is_file():
        print(json.dumps({"status": "missing", "error": f"wheel not found: {args.wheel}"}))
        return 1

    rc, report = check_wheel(args.wheel, args.tag, changelog_path=args.changelog)
    print(json.dumps(report))
    return rc


if __name__ == "__main__":
    sys.exit(main())
