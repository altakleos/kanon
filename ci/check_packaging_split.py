"""Phase A.1 packaging-split conformance gate.

Validates the three skeleton ``pyproject.toml`` files at ``packaging/{substrate,
reference,kit}/pyproject.toml`` against the canonical shapes specified in
``docs/design/distribution-boundary.md`` (per ADR-0043) and ratified by the
Phase A.1 plan ``docs/plans/phase-a.1-distribution-split.md``.

The skeletons are not yet runtime-functional (Phase A.2 wires entry-point
discovery; Phase A.3 retires kit-shape aspect content). This gate locks in
the *shape* so subsequent Phase A steps can rely on it.

Checks:

1. **Existence + parseability.** Each of the three files exists and parses
   as valid TOML.
2. **Substrate shape.** ``[project].name == "kanon-substrate"``;
   ``version == "1.0.0a1"``; ``requires-python == ">=3.10"``; dependencies
   include ``click>=8.1`` and ``pyyaml>=6.0``; the substrate exposes
   ``[project.scripts] kanon = "kanon.cli:main"``; the wheel build excludes
   ``../../src/kanon/kit/aspects/**``.
3. **Reference shape.** ``[project].name == "kanon-reference"``;
   ``version == "1.0.0a1"``; depends on ``kanon-substrate==1.0.0a1``;
   ``[project.entry-points."kanon.aspects"]`` declares the seven canonical
   aspect IDs each pointing at ``kanon_reference.aspects.kanon_<id>:MANIFEST``
   (Phase A.2.1).
4. **Kit-meta shape.** ``[project].name == "kanon-kit"``;
   ``version == "1.0.0a1"``; depends on both ``kanon-substrate==1.0.0a1``
   and ``kanon-reference==1.0.0a1``.

Exit codes:
    0 — all checks pass
    1 — one or more violations detected
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PACKAGING = _REPO_ROOT / "packaging"

_EXPECTED_VERSION = "1.0.0a1"
_EXPECTED_PYTHON = ">=3.10"
_SUBSTRATE_PIN = "kanon-substrate==1.0.0a1"
_REFERENCE_PIN = "kanon-reference==1.0.0a1"
_SUBSTRATE_EXCLUDE = "../../src/kanon/kit/aspects/**"
_SUBSTRATE_DEPS_REQUIRED = ("click>=8.1", "pyyaml>=6.0")

_REFERENCE_ASPECT_IDS = (
    "kanon-deps",
    "kanon-fidelity",
    "kanon-release",
    "kanon-sdd",
    "kanon-security",
    "kanon-testing",
    "kanon-worktrees",
)


def _load_toml(rel_path: str, errors: list[str]) -> dict[str, Any] | None:
    path = _PACKAGING / rel_path
    if not path.is_file():
        errors.append(f"missing: packaging/{rel_path}")
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"packaging/{rel_path}: invalid TOML — {exc}")
        return None


def _check_substrate(errors: list[str]) -> None:
    data = _load_toml("substrate/pyproject.toml", errors)
    if data is None:
        return
    project = data.get("project") or {}
    if project.get("name") != "kanon-substrate":
        errors.append(
            f"packaging/substrate/pyproject.toml: [project].name must be "
            f"'kanon-substrate' (got {project.get('name')!r})"
        )
    if project.get("version") != _EXPECTED_VERSION:
        errors.append(
            f"packaging/substrate/pyproject.toml: [project].version must be "
            f"{_EXPECTED_VERSION!r} (got {project.get('version')!r})"
        )
    if project.get("requires-python") != _EXPECTED_PYTHON:
        errors.append(
            f"packaging/substrate/pyproject.toml: [project].requires-python must be "
            f"{_EXPECTED_PYTHON!r} (got {project.get('requires-python')!r})"
        )
    deps = project.get("dependencies") or []
    for required in _SUBSTRATE_DEPS_REQUIRED:
        if required not in deps:
            errors.append(
                f"packaging/substrate/pyproject.toml: [project].dependencies "
                f"missing required pin {required!r}"
            )
    scripts = project.get("scripts") or {}
    if scripts.get("kanon") != "kanon.cli:main":
        errors.append(
            f"packaging/substrate/pyproject.toml: [project.scripts].kanon must be "
            f"'kanon.cli:main' (got {scripts.get('kanon')!r})"
        )
    wheel = (
        data.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
    )
    exclude = wheel.get("exclude") or []
    if _SUBSTRATE_EXCLUDE not in exclude:
        errors.append(
            f"packaging/substrate/pyproject.toml: "
            f"[tool.hatch.build.targets.wheel].exclude must contain "
            f"{_SUBSTRATE_EXCLUDE!r} (got {exclude!r})"
        )


def _check_reference(errors: list[str]) -> None:
    data = _load_toml("reference/pyproject.toml", errors)
    if data is None:
        return
    project = data.get("project") or {}
    if project.get("name") != "kanon-reference":
        errors.append(
            f"packaging/reference/pyproject.toml: [project].name must be "
            f"'kanon-reference' (got {project.get('name')!r})"
        )
    if project.get("version") != _EXPECTED_VERSION:
        errors.append(
            f"packaging/reference/pyproject.toml: [project].version must be "
            f"{_EXPECTED_VERSION!r} (got {project.get('version')!r})"
        )
    deps = project.get("dependencies") or []
    if _SUBSTRATE_PIN not in deps:
        errors.append(
            f"packaging/reference/pyproject.toml: [project].dependencies "
            f"must pin {_SUBSTRATE_PIN!r} (got {deps!r})"
        )
    _check_reference_entry_points(data, errors)


def _check_reference_entry_points(data: dict[str, Any], errors: list[str]) -> None:
    """Phase A.2.1: validate the active ``kanon.aspects`` entry-points block.

    Each of the seven canonical aspect IDs must resolve to
    ``kanon_reference.aspects.kanon_<id>:MANIFEST``.
    """
    entry_points = (
        data.get("project", {}).get("entry-points", {}).get("kanon.aspects") or {}
    )
    for aspect_id in _REFERENCE_ASPECT_IDS:
        expected_target = (
            f"kanon_reference.aspects.{aspect_id.replace('-', '_')}:MANIFEST"
        )
        actual = entry_points.get(aspect_id)
        if actual is None:
            errors.append(
                f"packaging/reference/pyproject.toml: "
                f"[project.entry-points.\"kanon.aspects\"] missing entry "
                f"{aspect_id!r}"
            )
            continue
        if actual != expected_target:
            errors.append(
                f"packaging/reference/pyproject.toml: "
                f"[project.entry-points.\"kanon.aspects\"].{aspect_id} must be "
                f"{expected_target!r} (got {actual!r})"
            )


def _check_kit_meta(errors: list[str]) -> None:
    data = _load_toml("kit/pyproject.toml", errors)
    if data is None:
        return
    project = data.get("project") or {}
    if project.get("name") != "kanon-kit":
        errors.append(
            f"packaging/kit/pyproject.toml: [project].name must be "
            f"'kanon-kit' (got {project.get('name')!r})"
        )
    if project.get("version") != _EXPECTED_VERSION:
        errors.append(
            f"packaging/kit/pyproject.toml: [project].version must be "
            f"{_EXPECTED_VERSION!r} (got {project.get('version')!r})"
        )
    deps = project.get("dependencies") or []
    for required in (_SUBSTRATE_PIN, _REFERENCE_PIN):
        if required not in deps:
            errors.append(
                f"packaging/kit/pyproject.toml: [project].dependencies "
                f"must pin {required!r} (got {deps!r})"
            )


def run_checks() -> list[str]:
    errors: list[str] = []
    _check_substrate(errors)
    _check_reference(errors)
    _check_kit_meta(errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.parse_args(argv)
    errors = run_checks()
    report: dict[str, Any] = {
        "errors": errors,
        "status": "fail" if errors else "ok",
    }
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
