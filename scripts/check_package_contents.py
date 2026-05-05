"""Wheel contents validator (maintainer-side, CI only).

Asserts a built kanon-kit wheel ships the invariants the release pipeline
relies on:

- **Required files present.** The kit bundle ships complete — every aspect's
  manifest, agents-md templates, sections, protocols, and files declared in
  the kit's manifests are present in the wheel.
- **No forbidden path prefixes.** Repo-only content (consumer state under
  `.kanon/`, the kit's own `docs/`, `tests/`, `scripts/`, `.github/`,
  `.venv/`, and the kit's own `AGENTS.md` / `CLAUDE.md`) never leaks into
  the wheel.
- **Version concordance.** `packages/kanon-core/src/kanon_core/__init__.py.__version__` matches the
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
import configparser
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import yaml

# Core files that must always be present regardless of aspects.
# Per Phase A.3 (kit-globals deletion): kanon_core/kit/kit.md was retired and
# is no longer in the wheel. Per ADR-0050 Option A: substrate Python module
# is `kernel/` (was `kanon/`); aspect data lives at `kanon_aspects/aspects/`.
# Per plan T6: kanon_core/kit/manifest.yaml is no longer required — T4
# deletes the file. The wheel-internal external oracle for aspect enumeration
# is now `<dist-info>/entry_points.txt` (parsed by
# `_derive_requirements_from_wheel` per plan T2).
_CORE_REQUIRED_FILES: tuple[str, ...] = (
    "kanon_core/__init__.py",
    "kanon_core/cli.py",
    "kanon_core/_atomic.py",
    "kanon_core/kit/harnesses.yaml",
)

# Populated at wheel-check time from the manifest inside the wheel.
REQUIRED_FILES: tuple[str, ...] = ()
REQUIRED_DIRS: tuple[str, ...] = ()

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    # Consumer-state paths that should never leak into the distributed wheel.
    ".kanon/",
    "docs/",               # kit's own docs/ are not shipped in the wheel
    "tests/",
    "scripts/",
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


def _derive_requirements_from_wheel(z: zipfile.ZipFile) -> tuple[list[str], list[str]]:
    """Derive wheel-required files and dirs from `<dist-info>/entry_points.txt`.

    Per plan T2 (panel-ratified): the external oracle for which aspects must
    ship is the wheel's `entry_points.txt` (reproducibly derived at build
    time from the source-tree pyproject's `[project.entry-points."kanon.aspects"]`
    table by hatchling). For each declared aspect slug, the per-aspect
    manifest's `depth-range` (canonical per ADR-0055) drives required-files
    enumeration.

    Replaces the previous behavior that read `kanon_core/kit/manifest.yaml`
    from the wheel — that file is retired in T4, and the new oracle is not
    self-referential because pyproject's entry-points table is hand-edited
    and version-controlled, while the wheel's `entry_points.txt` is a build
    artifact derived from it.
    """
    required_files = list(_CORE_REQUIRED_FILES)
    required_dirs = ["kanon_core/kit/"]

    names = z.namelist()
    # Find entry_points.txt under any *.dist-info/ in the wheel.
    entry_points_path: str | None = next(
        (
            n for n in names
            if n.endswith("/entry_points.txt") and ".dist-info/" in n
        ),
        None,
    )
    if entry_points_path is None:
        return required_files, required_dirs

    try:
        ep_text = z.read(entry_points_path).decode("utf-8")
    except KeyError:
        return required_files, required_dirs

    # entry_points.txt is INI-format; preserve key case (slugs are lowercase
    # but the parser default is to lowercase them anyway, this is defensive).
    parser = configparser.ConfigParser()
    parser.optionxform = str  # type: ignore[method-assign]
    try:
        parser.read_string(ep_text)
    except configparser.Error:
        return required_files, required_dirs

    if "kanon.aspects" not in parser:
        return required_files, required_dirs

    for slug in parser["kanon.aspects"]:
        # Per ADR-0049 PR A bundle collapse: aspect bundles live at
        # kanon_aspects/aspects/<slug.replace('-', '_')>/ in the wheel.
        aspect_base = f"kanon_aspects/aspects/{slug.replace('-', '_')}"
        required_files.append(f"{aspect_base}/manifest.yaml")
        required_dirs.append(f"{aspect_base}/")
        sub_path = f"{aspect_base}/manifest.yaml"
        try:
            sub = yaml.safe_load(z.read(sub_path).decode("utf-8"))
        except (KeyError, yaml.YAMLError):
            continue
        if not isinstance(sub, dict):
            continue
        # depth-range comes from the per-aspect manifest itself (ADR-0055
        # canonical). T2 closes the bug class where stale kit-YAML
        # depth-range silently skipped required-files checks for newly-
        # extended depths — every read here is from the same authoritative
        # artifact.
        rng = sub.get("depth-range", [0, 0])
        for d in range(int(rng[0]), int(rng[1]) + 1):
            depth_entry = sub.get(f"depth-{d}", {})
            if not isinstance(depth_entry, dict):
                continue
            for rel in depth_entry.get("files", []) or []:
                required_files.append(f"{aspect_base}/files/{rel}")
            for rel in depth_entry.get("protocols", []) or []:
                required_files.append(f"{aspect_base}/protocols/{rel}")
        for subdir in ("files", "protocols"):
            sub_dir_path = f"{aspect_base}/{subdir}/"
            if any(n.startswith(sub_dir_path) for n in names):
                required_dirs.append(sub_dir_path)
    return required_files, required_dirs


def check_wheel(wheel_path: Path, tag: str, changelog_path: Path | None = None) -> tuple[int, dict[str, Any]]:
    """Validate `wheel_path` against `tag`. Returns (exit_code, report)."""
    with zipfile.ZipFile(wheel_path) as z:
        names = z.namelist()
        try:
            init_content = z.read("kanon_core/__init__.py").decode("utf-8")
        except KeyError:
            init_content = ""
        required_files, required_dirs = _derive_requirements_from_wheel(z)
    name_set = set(names)

    missing_files = [f for f in required_files if f not in name_set]
    missing_dirs = [d for d in required_dirs if not any(n.startswith(d) for n in names)]

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
