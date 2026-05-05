"""Kit-bundle consistency validator (maintainer-side, CI hard-fail).

Asserts the invariants that keep kanon self-hosted. All checks operate on
`kanon_core/kit/` (see ADR-0011, ADR-0012, and docs/design/aspect-model.md).

1. **Byte-equality against repo canonical.** A narrow whitelist of files
   under each aspect's `files/` tree that have a counterpart at the repo
   root MUST be byte-identical to that counterpart. Per-aspect protocols
   at `aspects/<name>/protocols/*.md` must also match `.kanon/protocols/<name>/*.md`.

2. **Top-level manifest is an aspect registry.** Every aspect entry has
   required fields (`path`, `stability`, `depth-range`, `default-depth`);
   `stability ∈ {experimental, stable, deprecated}`; `path` resolves to
   an extant directory under `kit/`.

4. **Per-aspect sub-manifests resolve.** Every `aspects/<name>/manifest.yaml`
   exists; every path listed under any `depth-N.files` or `depth-N.protocols`
   resolves under that aspect's `files/` or `protocols/`.

5. **AGENTS.md marker discipline.** Markers in each aspect's
   `agents-md/depth-*.md` use either a known unprefixed cross-aspect name
   (e.g., `protocols-index`) or `<aspect>/<section>` where `<aspect>` is
   a registered aspect. Marker pairs are balanced.

6. **Cross-aspect file-ownership exclusivity.** No two aspects scaffold
   the same consumer-relative path across any of their depths.

7. **harnesses.yaml structure.** Every entry has `path` and `body`.

Exit codes:
    0 — all checks pass
    1 — one or more violations detected
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_KIT = _REPO_ROOT / "packages" / "kanon-core" / "src" / "kanon_core" / "kit"

# Allow this script to run from a fresh clone without an installed kanon.
sys.path.insert(0, str(_REPO_ROOT / "packages" / "kanon-core" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "src"))
from kanon_core._cli_helpers import _classify_predicate  # noqa: E402
from kanon_core._manifest import _iter_markers  # noqa: E402

_UNPREFIXED_SECTIONS: frozenset[str] = frozenset({"protocols-index"})
_STABILITY_VALUES: frozenset[str] = frozenset({"experimental", "stable", "deprecated"})

# Kit-side aspect-name grammar (ADR-0028). Every kit-shipped aspect must match
# this pattern; any other namespace (e.g., `project-`) is forbidden in a kit
# directory because project-aspects live under `.kanon/aspects/` in the consumer.
_KIT_ASPECT_NAME_RE = re.compile(r"^kanon-[a-z][a-z0-9-]*$")

# Per plan T1 (panel-ratified): the top-level aspect registry's source of truth
# is `pyproject.toml`'s `[project.entry-points."kanon.aspects"]` table + each
# aspect's per-aspect `manifest.yaml` (canonical per ADR-0055). The kit YAML at
# `kanon_core/kit/manifest.yaml` is retired in T4; this gate no longer reads it.
_TOML_STRING_KV = re.compile(
    r'^\s*(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"(?P<value>[^"]+)"\s*(?:#.*)?$'
)
_ENTRY_POINTS_HEADER = re.compile(
    r'^\s*\[project\.entry-points\."kanon\.aspects"\]\s*$', re.MULTILINE,
)


def _extract_aspect_slugs_from_pyproject(pyproject_path: Path) -> tuple[list[str], str | None]:
    """Return aspect slugs from the pyproject's `kanon.aspects` entry-point table.

    Returns ``(slugs, None)`` on success; ``([], error_msg)`` on absence /
    malformation. Same regex-based parsing as `scripts/gen_reference_aspects.py`
    (avoids a `tomli`/`tomllib` dependency for the 3.10 CI matrix).
    """
    if not pyproject_path.is_file():
        return [], f"missing: {pyproject_path.relative_to(_REPO_ROOT)}"
    text = pyproject_path.read_text(encoding="utf-8")
    match = _ENTRY_POINTS_HEADER.search(text)
    if match is None:
        return [], (
            f"{pyproject_path.relative_to(_REPO_ROOT)}: missing "
            f'[project.entry-points."kanon.aspects"] section.'
        )
    rest = text[match.end():]
    next_section = re.search(r"^\s*\[", rest, re.MULTILINE)
    section_body = rest[: next_section.start()] if next_section else rest
    slugs: list[str] = []
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        kv = _TOML_STRING_KV.match(line)
        if kv is not None:
            slugs.append(kv.group("key"))
    if not slugs:
        return [], (
            f"{pyproject_path.relative_to(_REPO_ROOT)}: "
            f'[project.entry-points."kanon.aspects"] is empty.'
        )
    return sorted(slugs), None


def _load_top_manifest() -> tuple[dict[str, Any], str | None]:
    """Synthesize a top-level registry from pyproject + per-aspect manifests.

    Per plan T1 (panel-ratified): reads `pyproject.toml`'s entry-points table
    for the aspect slug list, then loads each aspect's per-aspect `manifest.yaml`
    (canonical per ADR-0055) for stability / depth-range / default-depth /
    requires / provides / suggests. Returns the same shape downstream checks
    expect (`{"aspects": {slug: entry, ...}}`), with `entry` carrying every
    field except the legacy `path` (which was a kit-YAML-only artifact —
    aspect path is now resolved by slug, not by registry path field).
    """
    pyproject_path = _REPO_ROOT / "pyproject.toml"
    slugs, err = _extract_aspect_slugs_from_pyproject(pyproject_path)
    if err is not None:
        return {}, err
    top: dict[str, Any] = {"aspects": {}}
    for slug in slugs:
        sub_path = (
            _REPO_ROOT
            / "packages" / "kanon-aspects" / "src" / "kanon_aspects"
            / "aspects" / slug.replace("-", "_") / "manifest.yaml"
        )
        if not sub_path.is_file():
            return {}, (
                f"per-aspect manifest missing for {slug!r}: "
                f"{sub_path.relative_to(_REPO_ROOT)}"
            )
        try:
            sub = yaml.safe_load(sub_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            return {}, f"{sub_path.relative_to(_REPO_ROOT)}: invalid YAML — {exc}"
        if not isinstance(sub, dict):
            return {}, f"{sub_path.relative_to(_REPO_ROOT)}: expected a YAML mapping"
        # Project the per-aspect manifest's registry-relevant fields into the
        # top-level shape downstream checks consume. No `path` field — aspect
        # path resolution goes through slug-based lookup in `_aspect_root`.
        top["aspects"][slug] = {
            "stability": sub.get("stability"),
            "depth-range": sub.get("depth-range"),
            "default-depth": sub.get("default-depth"),
            "requires": sub.get("requires", []) or [],
            "provides": sub.get("provides", []) or [],
            "suggests": sub.get("suggests", []) or [],
        }
    return top, None


def _aspect_root(aspect: str, top: dict[str, Any]) -> Path | None:
    """Resolve an aspect's on-disk root directory by slug.

    Per ADR-0049 Migration PR A (bundle collapse): kanon-* aspect bundles
    live under `packages/kanon-aspects/src/kanon_aspects/aspects/kanon_<slug>/`
    (underscore in directory name for Python import compatibility; the slug
    itself retains hyphens). Per plan T1, the kit YAML's `path` field is no
    longer authoritative; resolution is purely slug-based.
    """
    if aspect not in top["aspects"]:
        return None
    bundle_root = (
        _REPO_ROOT
        / "packages" / "kanon-aspects" / "src" / "kanon_aspects"
        / "aspects" / aspect.replace("-", "_")
    )
    if bundle_root.is_dir():
        return bundle_root
    return None


def _load_aspect_manifest(
    aspect: str, top: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    entry = top["aspects"].get(aspect)
    if not entry:
        return {}, f"unknown aspect: {aspect}"
    root = _aspect_root(aspect, top)
    if root is None:
        return {}, f"missing aspect dir for {aspect}"
    sub_path = root / "manifest.yaml"
    if not sub_path.is_file():
        return {}, f"missing aspect sub-manifest: {sub_path.relative_to(_REPO_ROOT)}"
    try:
        data = yaml.safe_load(sub_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, f"{sub_path.relative_to(_REPO_ROOT)}: invalid YAML — {exc}"
    if not isinstance(data, dict):
        return {}, f"{sub_path.relative_to(_REPO_ROOT)}: expected a YAML mapping"
    return data, None


def _depth_range(aspect: str, top: dict[str, Any]) -> tuple[int, int]:
    rng = top["aspects"][aspect]["depth-range"]
    return int(rng[0]), int(rng[1])


def _check_byte_equality(errors: list[str]) -> None:
    top, err = _load_top_manifest()
    if err:
        return
    # Build whitelist from per-aspect sub-manifests' byte-equality key
    for aspect in top["aspects"]:
        sub, err2 = _load_aspect_manifest(aspect, top)
        if err2:
            continue
        for entry in sub.get("byte-equality", []) or []:
            kit_rel = entry["kit"]
            repo_rel = entry["repo"]
            aspect_path = _aspect_root(aspect, top) / "files" / kit_rel  # type: ignore[operator]
            repo_path = _REPO_ROOT / repo_rel
            if not aspect_path.is_file():
                errors.append(f"missing kit file: {aspect_path.relative_to(_REPO_ROOT)}")
                continue
            if not repo_path.is_file():
                errors.append(f"missing repo canonical: {repo_rel}")
                continue
            if aspect_path.read_bytes() != repo_path.read_bytes():
                errors.append(
                    f"byte-equality drift: {repo_rel} and "
                    f"{aspect_path.relative_to(_REPO_ROOT)} differ — must be identical."
                )
    # Per-aspect protocols presence check (per ADR-0049 D1: byte-mirror clause
    # loosened to behavioural conformance — the repo-canonical protocol mirror
    # MUST exist in `.kanon/protocols/<aspect>/`, but its content may drift from
    # the kit-side source-of-truth at `aspects/kanon_<slug>/protocols/<file>.md`.
    # ADR-0044 §2's self-host probe is satisfied by `kanon verify .` exit-0,
    # not by filesystem byte-equality. Existence is the structural anchor;
    # behavioural conformance is the content guarantee.
    for aspect in top["aspects"]:
        aspect_root = _aspect_root(aspect, top)
        if aspect_root is None:
            continue
        protocols_dir = aspect_root / "protocols"
        repo_protocols_dir = _REPO_ROOT / ".kanon" / "protocols" / aspect
        if not protocols_dir.is_dir():
            continue
        for kit_proto in sorted(protocols_dir.glob("*.md")):
            repo_proto = repo_protocols_dir / kit_proto.name
            if not repo_proto.is_file():
                errors.append(
                    f"missing repo-canonical protocol: .kanon/protocols/{aspect}/{kit_proto.name}"
                )
                # Note: NO byte-equality check here per ADR-0049 D1.


# Phase A.3: _check_kit_md_exists() retired. Per ADR-0048 de-opinionation,
# the kit-global kit.md template was deleted (along with `defaults:` and
# `files:` blocks in kanon_core/kit/manifest.yaml).


def _check_registry_and_manifests(errors: list[str]) -> None:
    top, err = _load_top_manifest()
    if err:
        errors.append(err)
        return
    for name, entry in top["aspects"].items():
        if not isinstance(entry, dict):
            errors.append(f"manifest.yaml: aspects.{name}: must be a mapping")
            continue
        # Kit-side aspect names must use the `kanon-` namespace per ADR-0028.
        # The corresponding runtime check in `kanon._manifest._load_top_manifest`
        # is the load-time gate; this CI check is the kit-author belt-and-
        # suspenders against an accidentally-misnamed kit-side aspect.
        if not isinstance(name, str) or not _KIT_ASPECT_NAME_RE.match(name):
            errors.append(
                f"manifest.yaml: aspects.{name!r}: kit-side aspect names must "
                f"match `^kanon-[a-z][a-z0-9-]*$` (ADR-0028 namespace ownership)."
            )
            continue
        # Per plan T1: required-fields list no longer includes `path` (the
        # kit-YAML-only legacy field). The remaining fields all live in the
        # per-aspect manifest, canonical per ADR-0055.
        for field in ("stability", "depth-range", "default-depth"):
            if field not in entry or entry[field] is None:
                errors.append(
                    f"aspects.{name}: missing required field {field!r} "
                    f"in per-aspect manifest"
                )
        if entry.get("stability") not in _STABILITY_VALUES:
            errors.append(
                f"aspects.{name}.stability: invalid value "
                f"{entry.get('stability')!r}"
            )
        rng = entry.get("depth-range")
        if not (isinstance(rng, list) and len(rng) == 2):
            errors.append(
                f"aspects.{name}.depth-range must be [min, max]"
            )
            continue
        aspect_root = _aspect_root(name, top)
        if aspect_root is None:
            errors.append(
                f"aspects.{name}: bundle directory missing under "
                f"packages/kanon-aspects/src/kanon_aspects/aspects/{name.replace('-', '_')}/"
            )
            continue
        sub, err2 = _load_aspect_manifest(name, top)
        if err2:
            errors.append(err2)
            continue
        min_d, max_d = int(rng[0]), int(rng[1])
        for d in range(min_d, max_d + 1):
            key = f"depth-{d}"
            depth_entry = sub.get(key)
            if depth_entry is None:
                errors.append(f"aspects.{name} sub-manifest: missing {key}")
                continue
            if not isinstance(depth_entry, dict):
                errors.append(f"aspects.{name} sub-manifest: {key} must be a mapping")
                continue
            for rel in depth_entry.get("files", []) or []:
                p = aspect_root / "files" / rel
                if not p.is_file():
                    errors.append(
                        f"aspects.{name} {key}.files: {rel} missing under "
                        f"{aspect_root.relative_to(_REPO_ROOT)}/files/"
                    )
            for rel in depth_entry.get("protocols", []) or []:
                p = aspect_root / "protocols" / rel
                if not p.is_file():
                    errors.append(
                        f"aspects.{name} {key}.protocols: {rel} missing under "
                        f"{aspect_root.relative_to(_REPO_ROOT)}/protocols/"
                    )


def _check_cross_aspect_exclusivity(errors: list[str]) -> None:
    top, err = _load_top_manifest()
    if err:
        return
    owners: dict[str, list[str]] = {}
    for name in top["aspects"]:
        sub, err2 = _load_aspect_manifest(name, top)
        if err2:
            continue
        min_d, max_d = _depth_range(name, top)
        for d in range(min_d, max_d + 1):
            depth_entry = sub.get(f"depth-{d}", {})
            for rel in depth_entry.get("files", []) or []:
                owners.setdefault(rel, []).append(name)
            for rel in depth_entry.get("protocols", []) or []:
                owners.setdefault(f".kanon/protocols/{name}/{rel}", []).append(name)
    for rel, owning in owners.items():
        unique = set(owning)
        if len(unique) > 1:
            errors.append(
                f"cross-aspect ownership conflict: {rel} scaffolded by {sorted(unique)}"
            )


def _check_agents_md_markers(errors: list[str]) -> None:
    top, err = _load_top_manifest()
    if err:
        return
    aspect_names = set(top["aspects"])
    for name in aspect_names:
        root = _aspect_root(name, top)
        if root is None:
            continue
        agents_md_dir = root / "agents-md"
        if not agents_md_dir.is_dir():
            continue
        for agents_md in sorted(agents_md_dir.glob("depth-*.md")):
            text = agents_md.read_text(encoding="utf-8")
            begins: dict[str, int] = {}
            ends: dict[str, int] = {}
            for kind, section, _, _ in _iter_markers(text):
                if section in _UNPREFIXED_SECTIONS:
                    pass  # cross-aspect sections are allowed unprefixed
                elif "/" in section:
                    prefix, _, _leaf = section.partition("/")
                    if prefix not in aspect_names:
                        errors.append(
                            f"{agents_md.relative_to(_REPO_ROOT)}: unknown aspect "
                            f"prefix {prefix!r} in marker {section!r}"
                        )
                else:
                    errors.append(
                        f"{agents_md.relative_to(_REPO_ROOT)}: unprefixed marker "
                        f"{section!r} (only "
                        f"{sorted(_UNPREFIXED_SECTIONS)} may be unprefixed)"
                    )
                if kind == "begin":
                    begins[section] = begins.get(section, 0) + 1
                else:
                    ends[section] = ends.get(section, 0) + 1
            for section in set(begins) | set(ends):
                if begins.get(section, 0) != ends.get(section, 0):
                    errors.append(
                        f"{agents_md.relative_to(_REPO_ROOT)}: marker imbalance for "
                        f"{section!r} ({begins.get(section, 0)} begin, "
                        f"{ends.get(section, 0)} end)"
                    )


def _check_harnesses_yaml(errors: list[str]) -> None:
    path = _KIT / "harnesses.yaml"
    if not path.is_file():
        errors.append(f"missing: {path.relative_to(_REPO_ROOT)}")
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"{path.relative_to(_REPO_ROOT)}: invalid YAML — {exc}")
        return
    if not isinstance(data, list):
        errors.append(
            f"{path.relative_to(_REPO_ROOT)}: expected a list of harness entries"
        )
        return
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(
                f"{path.relative_to(_REPO_ROOT)} entry {idx}: expected a mapping"
            )
            continue
        for field in ("path", "body"):
            if field not in entry:
                errors.append(
                    f"{path.relative_to(_REPO_ROOT)} entry {idx} "
                    f"(name={entry.get('name', '?')!r}): missing required field {field!r}"
                )


def _check_requires_resolution(errors: list[str]) -> None:
    """Hard-fail when any `requires:` predicate cannot resolve in this kit.

    For depth predicates: the named aspect must be registered.
    For capability predicates: at least one aspect must declare it in `provides:`.
    Malformed predicates are also reported.
    """
    top, err = _load_top_manifest()
    if err:
        return
    aspects = top.get("aspects", {})
    # Build the universe of provided capabilities once.
    provided: set[str] = set()
    for entry in aspects.values():
        for cap in entry.get("provides", []) or []:
            if isinstance(cap, str):
                provided.add(cap)
    for name, entry in aspects.items():
        for predicate in entry.get("requires", []) or []:
            try:
                classified = _classify_predicate(predicate)
            except Exception as exc:
                errors.append(
                    f"manifest.yaml: aspects.{name}.requires: {exc}"
                )
                continue
            if classified[0] == "depth":
                ref = classified[1]
                if ref not in aspects:
                    errors.append(
                        f"manifest.yaml: aspects.{name}.requires {predicate!r} "
                        f"references unknown aspect {ref!r}."
                    )
            else:  # capability
                cap = classified[1]
                if cap not in provided:
                    errors.append(
                        f"manifest.yaml: aspects.{name}.requires {predicate!r} "
                        f"references capability {cap!r} that no aspect provides."
                    )


def run_checks() -> list[str]:
    errors: list[str] = []
    _check_byte_equality(errors)
    _check_registry_and_manifests(errors)
    _check_cross_aspect_exclusivity(errors)
    _check_agents_md_markers(errors)
    _check_harnesses_yaml(errors)
    _check_requires_resolution(errors)
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
