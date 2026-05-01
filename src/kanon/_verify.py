"""Verification checks for ``kanon verify``.

Each ``check_*`` function appends to the provided ``errors`` and
``warnings`` lists.  The CLI command orchestrates them and emits the
final report.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from kanon._manifest import (
    _all_known_aspects,
    _aspect_depth_range,
    _aspect_depth_validators,
    _aspect_provides,
    _aspect_sections,
    _aspect_validators,
    _expected_files,
    _find_section_pair,
    _iter_markers,
    _namespaced_section,
    _parse_frontmatter,
)


def check_aspects_known(
    aspects: dict[str, int],
    errors: list[str],
    warnings: list[str],
) -> dict[str, int]:
    """Validate aspect names and depth ranges against the kit + project registry.

    Returns the subset of *aspects* registered (kit + active project overlay),
    safe for further checks.
    """
    known = _all_known_aspects()
    for name, depth in aspects.items():
        if name not in known:
            warnings.append(
                f"config.aspects.{name}: aspect not in installed kit registry."
            )
            continue
        min_d, max_d = _aspect_depth_range(name)
        if not (min_d <= depth <= max_d):
            errors.append(
                f"config.aspects.{name}.depth={depth}: outside range [{min_d},{max_d}]."
            )
    return {n: d for n, d in aspects.items() if n in known}


def check_required_files(
    target: Path,
    known_aspects: dict[str, int],
    errors: list[str],
) -> None:
    """Check that every file required by the active aspects exists."""
    for rel in _expected_files(known_aspects):
        p = target / rel
        if not p.exists():
            errors.append(f"missing required file: {rel}")


def check_agents_md_markers(
    target: Path,
    aspects: dict[str, int],
    known_aspects: dict[str, int],
    errors: list[str],
) -> None:
    """Check AGENTS.md for expected section markers and marker balance.

    Uses line-anchored, fenced-block-aware marker detection so quoted markers
    in user prose or code blocks do not influence the check.
    """
    agents_md_path = target / "AGENTS.md"
    if not agents_md_path.is_file():
        return
    agents_text = agents_md_path.read_text(encoding="utf-8")
    known = _all_known_aspects()
    for aspect, depth in aspects.items():
        if aspect not in known:
            continue
        for section in _aspect_sections(aspect, depth):
            namespaced = _namespaced_section(aspect, section)
            if _find_section_pair(agents_text, namespaced) is None:
                errors.append(
                    f"AGENTS.md missing marker pair for section '{namespaced}' "
                    f"(aspect {aspect}, depth {depth})."
                )
    begins = 0
    ends = 0
    for kind, _, _, _ in _iter_markers(agents_text):
        if kind == "begin":
            begins += 1
        else:
            ends += 1
    if begins != ends:
        errors.append(
            f"AGENTS.md marker imbalance: {begins} begin(s), {ends} end(s)."
        )


def check_fidelity_lock(
    target: Path,
    sdd_depth: int,
    warnings: list[str],
    spec_sha_fn: Any,
    accepted_specs_fn: Any,
) -> None:
    """Check fidelity lock for spec/fixture drift (sdd depth >= 2)."""
    if sdd_depth < 2:
        return
    lock_path = target / ".kanon" / "fidelity.lock"
    if not lock_path.is_file():
        return
    lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    if not isinstance(lock_data, dict) or "entries" not in lock_data:
        return
    lock_entries = lock_data["entries"] or {}
    specs_dir = target / "docs" / "specs"
    current_specs = accepted_specs_fn(specs_dir)
    for slug, entry in sorted(lock_entries.items()):
        spec_path = specs_dir / f"{slug}.md"
        if spec_path.is_file():
            current_sha = spec_sha_fn(spec_path)
            if current_sha != entry.get("spec_sha"):
                warnings.append(
                    f"fidelity: spec {slug} has changed since last fidelity update."  # nosec
                )
        for fpath, locked_sha in sorted(
            (entry.get("fixture_shas") or {}).items()
        ):
            full = target / fpath
            if not full.is_file():
                warnings.append(
                    f"fidelity: fixture {fpath} no longer exists (spec: {slug})."
                )
            elif spec_sha_fn(full) != locked_sha:
                warnings.append(
                    f"fidelity: fixture {fpath} has changed since last fidelity update (spec: {slug})."  # nosec
                )
    for p in current_specs:
        if p.stem not in lock_entries:
            warnings.append(
                f"fidelity: spec {p.stem} is not tracked in fidelity.lock."
            )


def check_verified_by(
    target: Path,
    sdd_depth: int,
    warnings: list[str],
) -> None:
    """Check invariant coverage completeness (sdd depth >= 2)."""
    if sdd_depth < 2:
        return
    inv_re = re.compile(r"<!--\s*(INV-[a-z][a-z0-9-]*-[a-z][a-z0-9-]*)\s*-->")
    specs_dir = target / "docs" / "specs"
    if not specs_dir.is_dir():
        return
    for sp in sorted(specs_dir.glob("*.md")):
        if sp.name.startswith("_") or sp.name == "README.md":
            continue
        text = sp.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if fm.get("status") != "accepted" or fm.get("fixtures_deferred"):
            continue
        anchors = inv_re.findall(text)
        if not anchors:
            continue
        coverage = fm.get("invariant_coverage") or {}
        missing = [a for a in anchors if a not in coverage]
        if missing:
            warnings.append(
                f"verified-by: {sp.name} missing invariant_coverage "
                f"for {len(missing)} anchor(s)."
            )


def run_project_validators(
    target: Path,
    aspects: dict[str, int],
    errors: list[str],
    warnings: list[str],
) -> None:
    """Invoke each enabled project-aspect's declared ``validators:`` in-process.

    Per ADR-0028 / project-aspects spec INV-7 the trust boundary is in-process:
    each ``validators:`` entry is a dotted Python module path that ``kanon
    verify`` ``importlib.import_module``s, then calls its ``check(target,
    errors, warnings) -> None`` entrypoint. Findings flow into the same
    ``errors``/``warnings`` lists the kit's structural checks populate.

    Per spec INV-9 (validator non-overriding), the kit's own structural
    checks are authoritative. Callers MUST invoke this function BEFORE the
    kit checks so any ``errors.clear()`` from a hostile project-validator is
    overwritten by the kit's subsequent appends. Failures raised by a
    validator (import error, missing entrypoint, exception during ``check``)
    are recorded as errors and verify continues with the remaining checks.
    """
    # Project validators use relative module paths (e.g. ``ci.validators.foo``)
    # resolved from the target directory.  Temporarily add *target* to
    # ``sys.path`` so ``importlib.import_module`` can find them.
    target_str = str(target)
    inserted = target_str not in sys.path
    if inserted:
        sys.path.insert(0, target_str)
    try:
        for aspect_name in sorted(aspects):
            if not aspect_name.startswith("project-"):
                continue
            try:
                module_paths = _aspect_validators(aspect_name)
            except Exception as exc:
                errors.append(
                    f"project-aspect {aspect_name!r}: failed to load manifest "
                    f"for validator discovery: {exc}"
                )
                continue
            for module_path in module_paths:
                try:
                    module = importlib.import_module(module_path)
                except ImportError as exc:
                    errors.append(
                        f"project-validator {module_path!r} (aspect {aspect_name!r}): "
                        f"import failed: {exc}"
                    )
                    continue
                check = getattr(module, "check", None)
                if not callable(check):
                    errors.append(
                        f"project-validator {module_path!r} (aspect {aspect_name!r}): "
                        f"module exposes no callable `check(target, errors, warnings)`."
                    )
                    continue
                try:
                    check(target, errors, warnings)
                except Exception as exc:
                    errors.append(
                        f"project-validator {module_path!r} (aspect {aspect_name!r}): "
                        f"raised {type(exc).__name__}: {exc}"
                    )
    finally:
        if inserted:
            sys.path.remove(target_str)


def run_kit_validators(
    target: Path,
    aspects: dict[str, int],
    errors: list[str],
    warnings: list[str],
) -> None:
    """Run depth-gated validators declared in kit-aspect manifests.

    Kit validators are trusted code shipped inside the ``kanon-kit`` package.
    They run AFTER the kit's structural checks (no INV-9 ordering concern).
    Each validator is a Python module with a ``check(target, errors, warnings)``
    entrypoint, discovered from ``depth-N: validators:`` entries in the
    aspect's sub-manifest using strict-superset union (depth-0..depth-N).
    """
    for aspect_name, depth in sorted(aspects.items()):
        if aspect_name.startswith("project-"):
            continue
        try:
            module_paths = _aspect_depth_validators(aspect_name, depth)
        except Exception as exc:
            warnings.append(
                f"verify: {aspect_name}: kit-validator lookup failed: {exc}"
            )
            continue
        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)
            except ImportError as exc:
                errors.append(
                    f"kit-validator {module_path!r} (aspect {aspect_name!r}): "
                    f"import failed: {exc}"
                )
                continue
            check_fn = getattr(module, "check", None)
            if not callable(check_fn):
                errors.append(
                    f"kit-validator {module_path!r} (aspect {aspect_name!r}): "
                    f"module exposes no callable `check`."
                )
                continue
            try:
                check_fn(target, errors, warnings)
            except Exception as exc:
                errors.append(
                    f"kit-validator {module_path!r} (aspect {aspect_name!r}): "
                    f"raised {type(exc).__name__}: {exc}"
                )


def check_fidelity_assertions(
    target: Path,
    aspects: dict[str, int],
    errors: list[str],
    warnings: list[str],
) -> None:
    """Run fidelity-fixture replay if any enabled aspect declares the
    ``behavioural-verification`` capability.

    Realises the verification-contract carve-out (INV-10, ratified by
    ADR-0029). Per ``docs/specs/fidelity.md`` INV-6 (aspect-gated) and INV-7
    (text-only bounds): when no enabled aspect declares the capability, this
    function returns immediately with zero filesystem reads under
    ``.kanon/fidelity/`` and emits no errors or warnings.

    Failure taxonomy (spec INV-8):
        - Missing required frontmatter, malformed lists, regex compilation
          errors, dogfood files with zero turns matching the configured
          actor, and any assertion failure → ``errors``.
        - Missing paired ``.dogfood.md`` capture → ``warnings``.
    """
    from kanon._fidelity import (
        BEHAVIOURAL_VERIFICATION_CAPABILITY,
        discover_fixtures,
        dogfood_path_for,
        evaluate_fixture,
        parse_fixture,
    )

    # INV-6 gate: any enabled aspect declaring the capability is sufficient.
    capability_aspect: str | None = None
    for name, depth in aspects.items():
        if depth < 1:
            continue
        try:
            provides = _aspect_provides(name)
        except Exception as exc:
            warnings.append(
                f"verify: {name}: capability lookup failed: {exc}"
            )
            continue
        if BEHAVIOURAL_VERIFICATION_CAPABILITY in provides:
            capability_aspect = name
            break
    if capability_aspect is None:
        return

    fixture_paths = discover_fixtures(target)
    if not fixture_paths:
        return  # Aspect enabled but no fixtures authored yet — silent.

    for fixture_path in fixture_paths:
        fixture, parse_errors = parse_fixture(fixture_path)
        if parse_errors:
            errors.extend(parse_errors)
            continue
        assert fixture is not None
        dogfood = dogfood_path_for(fixture_path)
        if not dogfood.is_file():
            warnings.append(
                f"fidelity: {fixture_path.name}: paired dogfood capture "
                f"({dogfood.name}) is missing"
            )
            continue
        try:
            dogfood_text = dogfood.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(
                f"fidelity: {dogfood.name}: cannot read capture: {exc}"
            )
            continue
        errors.extend(evaluate_fixture(fixture, dogfood_text))
