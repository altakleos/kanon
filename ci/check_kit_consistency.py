"""Kit-bundle consistency validator (maintainer-side, CI hard-fail).

Asserts the invariants that keep kanon self-hosted. All checks operate on
`src/kanon/kit/` (see ADR-0011, ADR-0012, and docs/design/aspect-model.md).

1. **Byte-equality against repo canonical.** A narrow whitelist of files
   under each aspect's `files/` tree that have a counterpart at the repo
   root MUST be byte-identical to that counterpart. Per-aspect protocols
   at `aspects/<name>/protocols/*.md` must also match `.kanon/protocols/<name>/*.md`.

2. **Kernel doc exists.** `kit/kit.md` is present and has a top-level
   `# ` heading on the first non-blank line.

3. **Top-level manifest is an aspect registry.** Every aspect entry has
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
_KIT = _REPO_ROOT / "src" / "kanon" / "kit"

_UNPREFIXED_SECTIONS: frozenset[str] = frozenset({"protocols-index"})
_STABILITY_VALUES: frozenset[str] = frozenset({"experimental", "stable", "deprecated"})

_SECTION_RE = re.compile(r"<!-- kanon:(begin|end):([a-z0-9/_-]+) -->")


def _load_top_manifest() -> tuple[dict[str, Any], str | None]:
    path = _KIT / "manifest.yaml"
    if not path.is_file():
        return {}, f"missing: {path.relative_to(_REPO_ROOT)}"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, f"{path.relative_to(_REPO_ROOT)}: invalid YAML — {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("aspects"), dict):
        return {}, f"{path.relative_to(_REPO_ROOT)}: missing or malformed 'aspects' mapping"
    return data, None


def _load_aspect_manifest(
    aspect: str, top: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    entry = top["aspects"].get(aspect)
    if not entry:
        return {}, f"unknown aspect: {aspect}"
    sub_path = _KIT / entry["path"] / "manifest.yaml"
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
            aspect_path = _KIT / top["aspects"][aspect]["path"] / "files" / kit_rel
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
    # Per-aspect protocols byte-equality
    for aspect in top["aspects"]:
        aspect_root = _KIT / top["aspects"][aspect]["path"]
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
                continue
            if kit_proto.read_bytes() != repo_proto.read_bytes():
                errors.append(
                    f"byte-equality drift: .kanon/protocols/{aspect}/{kit_proto.name} and "
                    f"{kit_proto.relative_to(_REPO_ROOT)} differ — must be identical."
                )


def _check_kit_md_exists(errors: list[str]) -> None:
    kit_md = _KIT / "kit.md"
    if not kit_md.is_file():
        errors.append(f"missing kernel doc: {kit_md.relative_to(_REPO_ROOT)}")
        return
    text = kit_md.read_text(encoding="utf-8")
    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    if not first_line.startswith("# "):
        errors.append(
            f"{kit_md.relative_to(_REPO_ROOT)}: expected top-level `# ` heading "
            f"on first non-blank line, got {first_line!r}"
        )


def _check_registry_and_manifests(errors: list[str]) -> None:
    top, err = _load_top_manifest()
    if err:
        errors.append(err)
        return
    for name, entry in top["aspects"].items():
        if not isinstance(entry, dict):
            errors.append(f"manifest.yaml: aspects.{name}: must be a mapping")
            continue
        for field in ("path", "stability", "depth-range", "default-depth"):
            if field not in entry:
                errors.append(
                    f"manifest.yaml: aspects.{name}: missing required field {field!r}"
                )
        if entry.get("stability") not in _STABILITY_VALUES:
            errors.append(
                f"manifest.yaml: aspects.{name}.stability: invalid value "
                f"{entry.get('stability')!r}"
            )
        rng = entry.get("depth-range")
        if not (isinstance(rng, list) and len(rng) == 2):
            errors.append(
                f"manifest.yaml: aspects.{name}.depth-range must be [min, max]"
            )
            continue
        aspect_root = _KIT / entry["path"]
        if not aspect_root.is_dir():
            errors.append(
                f"manifest.yaml: aspects.{name}.path: {entry['path']} "
                f"does not exist under kit/"
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
                        f"{entry['path']}/files/"
                    )
            for rel in depth_entry.get("protocols", []) or []:
                p = aspect_root / "protocols" / rel
                if not p.is_file():
                    errors.append(
                        f"aspects.{name} {key}.protocols: {rel} missing under "
                        f"{entry['path']}/protocols/"
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
        entry = top["aspects"][name]
        agents_md_dir = _KIT / entry["path"] / "agents-md"
        if not agents_md_dir.is_dir():
            continue
        for agents_md in sorted(agents_md_dir.glob("depth-*.md")):
            text = agents_md.read_text(encoding="utf-8")
            begins: dict[str, int] = {}
            ends: dict[str, int] = {}
            for m in _SECTION_RE.finditer(text):
                kind, section = m.group(1), m.group(2)
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


def run_checks() -> list[str]:
    errors: list[str] = []
    _check_byte_equality(errors)
    _check_kit_md_exists(errors)
    _check_registry_and_manifests(errors)
    _check_cross_aspect_exclusivity(errors)
    _check_agents_md_markers(errors)
    _check_harnesses_yaml(errors)
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
