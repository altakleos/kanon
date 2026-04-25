#!/usr/bin/env python3
"""Dependency hygiene scanner. Checks manifest files for unpinned versions and duplicates.

Usage: python ci/check_deps.py [--root DIR]

Best-effort safety net — not a full dependency auditor. Findings are warnings (exit 0).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Directories to skip.
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}

# Groups of packages that serve the same purpose.
_DUPLICATE_GROUPS: dict[str, list[str]] = {
    "http": ["requests", "httpx", "urllib3", "aiohttp", "httplib2"],
    "date": ["arrow", "pendulum", "python-dateutil", "maya", "delorean"],
    "cli": ["click", "typer", "argparse", "fire", "docopt"],
    "test": ["pytest", "nose", "unittest2", "nose2"],
    "yaml": ["pyyaml", "ruamel.yaml", "strictyaml"],
    "json-schema": ["jsonschema", "fastjsonschema", "pydantic"],
}

# Patterns for unpinned versions in requirements.txt lines.
_REQ_UNPINNED = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*\s*$")
_REQ_RANGE = re.compile(r"[><!~]=?")
_REQ_PINNED = re.compile(r"==")

# Patterns for unpinned versions in pyproject.toml dependency strings.
_PYPROJECT_UNPINNED = re.compile(r'[">]\s*(?:>=|>|~=|!=)')

# Patterns for unpinned versions in package.json.
_PKG_JSON_UNPINNED = re.compile(r':\s*"[\^~]')


def _find_manifests(root: Path) -> list[Path]:
    """Collect manifest files under root."""
    manifests: list[Path] = []
    for p in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.name in ("requirements.txt", "pyproject.toml", "package.json") and p.is_file():
            manifests.append(p)
    return manifests


def _check_requirements_txt(path: Path) -> list[dict[str, Any]]:
    """Check requirements.txt for unpinned versions."""
    findings: list[dict[str, Any]] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Pinned with == is fine.
        if _REQ_PINNED.search(line):
            continue
        # Has a range specifier but not == — unpinned.
        if _REQ_RANGE.search(line):
            findings.append({"file": str(path), "line": i, "rule": "unpinned-version",
                             "message": f"Unpinned version: {line}"})
        # Bare package name with no version at all.
        elif _REQ_UNPINNED.match(line):
            findings.append({"file": str(path), "line": i, "rule": "unpinned-version",
                             "message": f"No version pin: {line}"})
    return findings


def _check_pyproject_toml(path: Path) -> list[dict[str, Any]]:
    """Check pyproject.toml for unpinned dependency versions.

    Only the bodies of `dependencies = [...]` and `<group> = [...]` arrays
    inside `[project.optional-dependencies]` are scanned. Scalar fields like
    `requires-python`, `name`, `version`, etc. — which can match the unpinned
    regex incidentally — are not dependency declarations and are skipped.
    """
    findings: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    in_deps = False
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        # Trigger on `dependencies = [` or any `<name> = [` (covers
        # `optional-dependencies` blocks like `dev = [...]`). The `[project]`
        # section header itself is no longer a state-flip trigger.
        if not in_deps and re.match(r"^[A-Za-z_][\w-]*\s*=\s*\[\s*$", line):
            in_deps = True
            continue
        if in_deps and line.startswith("]"):
            in_deps = False
            continue
        if in_deps and _PYPROJECT_UNPINNED.search(line):
            findings.append({"file": str(path), "line": i, "rule": "unpinned-version",
                             "message": f"Unpinned dependency: {line.strip(',').strip()}"})
    return findings


def _check_package_json(path: Path) -> list[dict[str, Any]]:
    """Check package.json for ^ or ~ version prefixes."""
    findings: list[dict[str, Any]] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _PKG_JSON_UNPINNED.search(raw):
            findings.append({"file": str(path), "line": i, "rule": "unpinned-version",
                             "message": f"Unpinned version: {raw.strip().rstrip(',')}"})
    return findings


def _check_duplicates(root: Path) -> list[dict[str, Any]]:
    """Best-effort detection of duplicate-purpose packages across manifests."""
    findings: list[dict[str, Any]] = []
    all_deps: set[str] = set()

    for p in _find_manifests(root):
        for raw in p.read_text(encoding="utf-8").splitlines():
            line = raw.strip().lower()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Extract bare package name.
            name = re.split(r"[>=<!\[~;,\s\"']", line)[0].strip('"').strip()
            if name:
                all_deps.add(name)

    for group_name, members in _DUPLICATE_GROUPS.items():
        found = [m for m in members if m in all_deps]
        if len(found) > 1:
            findings.append({"file": "(project)", "line": 0, "rule": "duplicate-purpose",
                             "message": f"Multiple {group_name} libraries: {', '.join(found)}"})
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Dependency hygiene scanner")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    all_findings: list[dict[str, Any]] = []

    for manifest in _find_manifests(root):
        if manifest.name == "requirements.txt":
            all_findings.extend(_check_requirements_txt(manifest))
        elif manifest.name == "pyproject.toml":
            all_findings.extend(_check_pyproject_toml(manifest))
        elif manifest.name == "package.json":
            all_findings.extend(_check_package_json(manifest))

    all_findings.extend(_check_duplicates(root))

    status = "warn" if all_findings else "ok"
    report = {"status": status, "findings": all_findings}
    print(json.dumps(report, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
