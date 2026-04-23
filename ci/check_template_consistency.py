"""Template-consistency validator (maintainer-side, CI hard-fail).

Asserts four invariants that keep the kanon kit self-hosted:

1. **Byte-equality** between the repo's canonical `docs/development-process.md`
   and the tier-1 template's copy. These two files MUST be identical
   byte-for-byte; the repo's own method doc and the one scaffolded into
   consumer projects cannot diverge.
2. **AGENTS.md marker balance** in every tier template — every
   ``<!-- kanon:begin:<name> -->`` has a matching
   ``<!-- kanon:end:<name> -->``.
3. **Known section names.** Every marker section name in any template
   AGENTS.md or agents-md-sections fragment is in the documented set
   (currently: plan-before-build, spec-before-design).
4. **harnesses.yaml structure.** Every entry has `path` and `body` (and
   optionally `frontmatter` and `name`).

Exit codes:
    0 — all checks pass
    1 — one or more violations detected

Per the template-bundle design doc: docs/design/template-bundle.md.
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
_CANONICAL_DEV_PROCESS = _REPO_ROOT / "docs" / "development-process.md"
_TEMPLATE_DEV_PROCESS = _KIT / "files" / "docs" / "development-process.md"

_KNOWN_SECTIONS: frozenset[str] = frozenset({"plan-before-build", "spec-before-design", "protocols-index"})

_SECTION_RE = re.compile(r"<!-- kanon:(begin|end):([a-z0-9-]+) -->")


def _check_dev_process_byte_equality(errors: list[str]) -> None:
    if not _CANONICAL_DEV_PROCESS.is_file():
        errors.append(f"missing canonical file: {_CANONICAL_DEV_PROCESS}")
        return
    if not _TEMPLATE_DEV_PROCESS.is_file():
        errors.append(f"missing template file: {_TEMPLATE_DEV_PROCESS}")
        return
    canon = _CANONICAL_DEV_PROCESS.read_bytes()
    tmpl = _TEMPLATE_DEV_PROCESS.read_bytes()
    if canon != tmpl:
        errors.append(
            f"byte-equality drift: {_CANONICAL_DEV_PROCESS.relative_to(_REPO_ROOT)} "
            f"and {_TEMPLATE_DEV_PROCESS.relative_to(_REPO_ROOT)} differ — "
            f"they must be byte-identical."
        )


def _check_agents_md_markers(errors: list[str]) -> None:
    for agents_md in sorted((_KIT / "agents-md").glob("tier-*.md")):
        if not agents_md.is_file():
            continue
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
    _check_dev_process_byte_equality(errors)
    _check_agents_md_markers(errors)
    _check_harnesses_yaml(errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    args = parser.parse_args(argv)  # noqa: F841 — reserved for future options
    errors = run_checks()
    report: dict[str, Any] = {"errors": errors, "status": "fail" if errors else "ok"}
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
