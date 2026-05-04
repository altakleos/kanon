"""Dependency hygiene validator (kanon-deps depth 2).

Checks for unpinned versions and lockfile presence. Findings are warnings.
"""
from __future__ import annotations

import re
from pathlib import Path

_REQ_PINNED = re.compile(r"==")


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag dependency hygiene issues."""
    # Check 1: Lockfile presence
    lockfiles = [
        "uv.lock", "poetry.lock", "Pipfile.lock",
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    ]
    has_manifest = (
        (target / "pyproject.toml").is_file()
        or (target / "requirements.txt").is_file()
        or (target / "package.json").is_file()
    )
    has_lockfile = any((target / lf).is_file() for lf in lockfiles)
    if has_manifest and not has_lockfile:
        warnings.append(
            "deps-hygiene: no lockfile found. Commit a lockfile "
            "(uv.lock, poetry.lock, package-lock.json, etc.) for reproducible builds."
        )

    # Check 2: Unpinned versions in requirements.txt
    req_file = target / "requirements.txt"
    if req_file.is_file():
        try:
            lines = req_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        unpinned = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            pkg_spec = line.split(";")[0].strip()
            if not _REQ_PINNED.search(pkg_spec) and pkg_spec:
                unpinned.append(pkg_spec.split()[0])
        if unpinned:
            warnings.append(
                f"deps-hygiene: {len(unpinned)} unpinned deps in requirements.txt: "
                f"{', '.join(unpinned[:5])}{'...' if len(unpinned) > 5 else ''}. "
                f"Pin with == for reproducibility."
            )
