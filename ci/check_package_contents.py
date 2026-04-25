"""Wheel contents validator (maintainer-side, CI only).

Asserts a built kanon-kit wheel ships the invariants the release pipeline
relies on:

- **Required files present.** The kit bundle ships complete — every aspect's
  manifest, agents-md templates, sections, protocols, and files declared in
  the kit's manifests are present in the wheel.
- **No forbidden path prefixes.** Repo-only content (consumer state under
  `.kanon/`, the kit's own `docs/`, `tests/`, `ci/`, `.github/`, `.venv/`,
  and the kit's own `AGENTS.md` / `CLAUDE.md`) never leaks into the wheel.
- **Version concordance.** `kanon/__init__.py.__version__` matches the
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

import yaml

# Core files that must always be present regardless of aspects.
_CORE_REQUIRED_FILES: tuple[str, ...] = (
    "kanon/__init__.py",
    "kanon/cli.py",
    "kanon/_atomic.py",
    "kanon/kit/manifest.yaml",
    "kanon/kit/kit.md",
    "kanon/kit/harnesses.yaml",
)

# Populated at wheel-check time from the manifest inside the wheel.
REQUIRED_FILES: tuple[str, ...] = ()
REQUIRED_DIRS: tuple[str, ...] = ()

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


def _derive_requirements_from_wheel(z: zipfile.ZipFile) -> tuple[list[str], list[str]]:
    """Read manifest.yaml from the wheel and derive required files and dirs."""
    required_files = list(_CORE_REQUIRED_FILES)
    required_dirs = ["kanon/kit/"]
    try:
        top = yaml.safe_load(z.read("kanon/kit/manifest.yaml").decode("utf-8"))
    except (KeyError, yaml.YAMLError):
        return required_files, required_dirs
    if not isinstance(top, dict) or not isinstance(top.get("aspects"), dict):
        return required_files, required_dirs
    for name, entry in top["aspects"].items():
        if not isinstance(entry, dict):
            continue
        aspect_base = "kanon/kit/" + entry.get("path", f"aspects/{name}")
        required_files.append(f"{aspect_base}/manifest.yaml")
        required_dirs.append(f"{aspect_base}/")
        # Load sub-manifest to get depth-specific files, protocols, sections
        sub_path = f"{aspect_base}/manifest.yaml"
        try:
            sub = yaml.safe_load(z.read(sub_path).decode("utf-8"))
        except (KeyError, yaml.YAMLError):
            continue
        if not isinstance(sub, dict):
            continue
        rng = entry.get("depth-range", [0, 0])
        for d in range(int(rng[0]), int(rng[1]) + 1):
            depth_entry = sub.get(f"depth-{d}", {})
            if not isinstance(depth_entry, dict):
                continue
            # agents-md depth file
            required_files.append(f"{aspect_base}/agents-md/depth-{d}.md")
            for rel in depth_entry.get("files", []) or []:
                required_files.append(f"{aspect_base}/files/{rel}")
            for rel in depth_entry.get("protocols", []) or []:
                required_files.append(f"{aspect_base}/protocols/{rel}")
            for sec in depth_entry.get("sections", []) or []:
                if sec == "protocols-index":
                    continue  # cross-aspect, not a file
                required_files.append(f"{aspect_base}/sections/{sec}.md")
        # Add subdirs that should be non-empty
        for subdir in ("agents-md", "files", "sections", "protocols"):
            sub_dir_path = f"{aspect_base}/{subdir}/"
            # Only require dirs that have entries in the manifest
            names = z.namelist()
            if any(n.startswith(sub_dir_path) for n in names):
                required_dirs.append(sub_dir_path)
    return required_files, required_dirs


def check_wheel(wheel_path: Path, tag: str, changelog_path: Path | None = None) -> tuple[int, dict[str, Any]]:
    """Validate `wheel_path` against `tag`. Returns (exit_code, report)."""
    with zipfile.ZipFile(wheel_path) as z:
        names = z.namelist()
        try:
            init_content = z.read("kanon/__init__.py").decode("utf-8")
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
