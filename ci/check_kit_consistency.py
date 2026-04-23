"""Kit-bundle consistency validator (maintainer-side, CI hard-fail).

Asserts the invariants that keep kanon self-hosted. All checks operate on
`src/kanon/kit/` (see ADR-0011 and docs/design/kit-bundle.md).

1. **Byte-equality against repo canonical.** A narrow whitelist of files
   in `kit/files/` and `kit/protocols/` that also live at the repo root
   MUST be byte-identical to the repo-root copy. Covers
   `docs/development-process.md`, the `_template.md` files under
   `docs/{decisions,plans,specs,design}/`, and every `.kanon/protocols/*.md`.

2. **Kernel doc exists.** `kit/kit.md` is present and has a top-level
   `# ` heading on the first non-blank line.

3. **Manifest paths resolve.** Every path declared in
   `kit/manifest.yaml` under `tier-*.files` or `tier-*.protocols` points
   to an extant file in `kit/files/` or `kit/protocols/` respectively.
   Every section name under `agents-md-sections.tier-*` is in the
   known set.

4. **AGENTS.md marker balance.** Each per-tier base in `kit/agents-md/`
   has balanced `<!-- kanon:begin:<name> -->` / `<!-- kanon:end:<name> -->`
   pairs, and every section name is in `_KNOWN_SECTIONS`.

5. **harnesses.yaml structure.** Every entry has `path` and `body`
   (and optionally `frontmatter` and `name`).

Exit codes:
    0 — all checks pass
    1 — one or more violations detected

Per docs/design/kit-bundle.md.
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

_KNOWN_SECTIONS: frozenset[str] = frozenset(
    {"plan-before-build", "spec-before-design", "protocols-index"}
)

# Files in kit/ that must be byte-identical to their repo-root counterparts.
# (kit_relative_to_subdir, repo_relative_to_repo_root, subdir)
_BYTE_EQUAL_WHITELIST: tuple[tuple[str, str, str], ...] = (
    ("docs/development-process.md", "docs/development-process.md", "files"),
    ("docs/decisions/_template.md", "docs/decisions/_template.md", "files"),
    ("docs/plans/_template.md", "docs/plans/_template.md", "files"),
    ("docs/specs/_template.md", "docs/specs/_template.md", "files"),
    ("docs/design/_template.md", "docs/design/_template.md", "files"),
)

_SECTION_RE = re.compile(r"<!-- kanon:(begin|end):([a-z0-9-]+) -->")


def _check_byte_equality(errors: list[str]) -> None:
    """Static whitelist + kit/protocols/*.md ↔ .kanon/protocols/*.md."""
    for kit_rel, repo_rel, subdir in _BYTE_EQUAL_WHITELIST:
        kit_path = _KIT / subdir / kit_rel
        repo_path = _REPO_ROOT / repo_rel
        if not kit_path.is_file():
            errors.append(f"missing kit file: {kit_path.relative_to(_REPO_ROOT)}")
            continue
        if not repo_path.is_file():
            errors.append(f"missing repo canonical: {repo_rel}")
            continue
        if kit_path.read_bytes() != repo_path.read_bytes():
            errors.append(
                f"byte-equality drift: {repo_rel} and {kit_path.relative_to(_REPO_ROOT)} "
                f"differ — must be identical."
            )

    kit_protocols = _KIT / "protocols"
    repo_protocols = _REPO_ROOT / ".kanon" / "protocols"
    if kit_protocols.is_dir():
        for kit_proto in sorted(kit_protocols.glob("*.md")):
            repo_proto = repo_protocols / kit_proto.name
            if not repo_proto.is_file():
                errors.append(
                    f"missing repo-canonical protocol: .kanon/protocols/{kit_proto.name}"
                )
                continue
            if kit_proto.read_bytes() != repo_proto.read_bytes():
                errors.append(
                    f"byte-equality drift: .kanon/protocols/{kit_proto.name} and "
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
            f"{kit_md.relative_to(_REPO_ROOT)}: expected top-level `# ` heading on "
            f"first non-blank line, got {first_line!r}"
        )


def _load_manifest() -> tuple[dict[str, Any], str | None]:
    path = _KIT / "manifest.yaml"
    if not path.is_file():
        return {}, f"missing: {path.relative_to(_REPO_ROOT)}"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, f"{path.relative_to(_REPO_ROOT)}: invalid YAML — {exc}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(_REPO_ROOT)}: expected a YAML mapping"
    return data, None


def _check_manifest(errors: list[str]) -> None:
    manifest, err = _load_manifest()
    if err:
        errors.append(err)
        return

    for n in range(4):
        key = f"tier-{n}"
        entry = manifest.get(key)
        if not isinstance(entry, dict):
            errors.append(f"manifest.yaml: {key} missing or not a mapping")
            continue
        for rel in entry.get("files", []):
            p = _KIT / "files" / rel
            if not p.is_file():
                errors.append(
                    f"manifest.yaml {key}.files: {rel} does not exist under kit/files/"
                )
        for rel in entry.get("protocols", []):
            p = _KIT / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"manifest.yaml {key}.protocols: {rel} does not exist under kit/protocols/"
                )

    sections_map = manifest.get("agents-md-sections", {})
    if not isinstance(sections_map, dict):
        errors.append("manifest.yaml: agents-md-sections must be a mapping")
        return
    for tier_key, sections in sections_map.items():
        if not isinstance(sections, list):
            errors.append(f"manifest.yaml agents-md-sections.{tier_key} must be a list")
            continue
        for name in sections:
            if name not in _KNOWN_SECTIONS:
                errors.append(
                    f"manifest.yaml agents-md-sections.{tier_key}: unknown section {name!r}"
                )


def _check_agents_md_markers(errors: list[str]) -> None:
    agents_md_dir = _KIT / "agents-md"
    if not agents_md_dir.is_dir():
        errors.append("missing kit/agents-md/ directory")
        return
    for agents_md in sorted(agents_md_dir.glob("tier-*.md")):
        text = agents_md.read_text(encoding="utf-8")
        begins: dict[str, int] = {}
        ends: dict[str, int] = {}
        for m in _SECTION_RE.finditer(text):
            kind, section = m.group(1), m.group(2)
            if section not in _KNOWN_SECTIONS:
                errors.append(
                    f"{agents_md.relative_to(_REPO_ROOT)}: unknown marker section {section!r}"
                )
                continue
            if kind == "begin":
                begins[section] = begins.get(section, 0) + 1
            else:
                ends[section] = ends.get(section, 0) + 1
        for section in set(begins) | set(ends):
            if begins.get(section, 0) != ends.get(section, 0):
                errors.append(
                    f"{agents_md.relative_to(_REPO_ROOT)}: marker imbalance for {section!r} "
                    f"({begins.get(section, 0)} begin, {ends.get(section, 0)} end)"
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
        errors.append(f"{path.relative_to(_REPO_ROOT)}: expected a list of harness entries")
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
    _check_manifest(errors)
    _check_agents_md_markers(errors)
    _check_harnesses_yaml(errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.parse_args(argv)
    errors = run_checks()
    report: dict[str, Any] = {"errors": errors, "status": "fail" if errors else "ok"}
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
