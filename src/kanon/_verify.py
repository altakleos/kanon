"""Verification checks for ``kanon verify``.

Each ``check_*`` function appends to the provided ``errors`` and
``warnings`` lists.  The CLI command orchestrates them and emits the
final report.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from kanon._manifest import (
    _aspect_depth_range,
    _aspect_sections,
    _expected_files,
    _load_top_manifest,
    _namespaced_section,
    _parse_frontmatter,
)


def check_aspects_known(
    aspects: dict[str, int],
    errors: list[str],
    warnings: list[str],
) -> dict[str, int]:
    """Validate aspect names and depth ranges against the kit registry.

    Returns the subset of *aspects* that the installed kit recognises
    (safe for further checks).
    """
    top = _load_top_manifest()
    for name, depth in aspects.items():
        if name not in top["aspects"]:
            warnings.append(
                f"config.aspects.{name}: aspect not in installed kit registry."
            )
            continue
        min_d, max_d = _aspect_depth_range(name)
        if not (min_d <= depth <= max_d):
            errors.append(
                f"config.aspects.{name}.depth={depth}: outside range [{min_d},{max_d}]."
            )
    return {n: d for n, d in aspects.items() if n in top["aspects"]}


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
    """Check AGENTS.md for expected section markers and marker balance."""
    agents_md_path = target / "AGENTS.md"
    if not agents_md_path.is_file():
        return
    agents_text = agents_md_path.read_text(encoding="utf-8")
    top = _load_top_manifest()
    for aspect, depth in aspects.items():
        if aspect not in top["aspects"]:
            continue
        for section in _aspect_sections(aspect, depth):
            namespaced = _namespaced_section(aspect, section)
            begin = f"<!-- kanon:begin:{namespaced} -->"
            end = f"<!-- kanon:end:{namespaced} -->"
            if begin not in agents_text or end not in agents_text:
                errors.append(
                    f"AGENTS.md missing marker pair for section '{namespaced}' "
                    f"(aspect {aspect}, depth {depth})."
                )
    begins = agents_text.count("<!-- kanon:begin:")
    ends = agents_text.count("<!-- kanon:end:")
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
                    f"fidelity: spec {slug} has changed since last fidelity update."
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
                    f"fidelity: fixture {fpath} has changed since last fidelity update (spec: {slug})."
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
