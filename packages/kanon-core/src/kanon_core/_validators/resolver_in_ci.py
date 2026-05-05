"""INV-resolutions-resolver-not-in-ci validator.

Detects CI configurations that invoke ``kanon resolve`` — a violation of the
resolutions spec invariant 5: the resolver runs only on developer machines;
CI replays cached resolutions.

Detection is best-effort (spec says "where detectable").
"""
from __future__ import annotations

import re
from pathlib import Path

_KANON_RESOLVE_RE = re.compile(r"\bkanon\s+resolve\b")

# Common CI config paths (relative to project root).
_CI_GLOBS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
    "buildspec.yml",
    "buildspec.yaml",
    ".buildkite/pipeline.yml",
    ".buildkite/pipeline.yaml",
]


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    """Flag CI configs that invoke ``kanon resolve``."""
    ci_files: list[Path] = []
    for pattern in _CI_GLOBS:
        ci_files.extend(target.glob(pattern))

    for ci_file in ci_files:
        try:
            content = ci_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if _KANON_RESOLVE_RE.search(line):
                rel = ci_file.relative_to(target)
                errors.append(
                    f"resolver-in-ci: {rel}:{lineno} invokes `kanon resolve`. "
                    f"CI must replay cached resolutions, not invoke the resolver "
                    f"(INV-resolutions-resolver-not-in-ci)."
                )
