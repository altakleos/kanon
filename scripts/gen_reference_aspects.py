#!/usr/bin/env python3
"""Generate `docs/reference-aspects.md` from `pyproject.toml` entry-points + per-aspect manifests.

Implements T7 of `docs/plans/active/retire-kit-aspects-yaml.md`. Replaces
the `aspects:` block in `packages/kanon-core/src/kanon_core/kit/manifest.yaml`
as the human-readable roster, with a publisher-neutral artifact regenerated
from the substrate's actual oracle (the source-tree pyproject's entry-points
table + each aspect's own manifest.yaml per ADR-0055).

Three guardrails per panel R2 (Q1):
1. **Neutral name + framing**: file is `docs/reference-aspects.md`, NOT
   `docs/kit-aspects.md`. Prose says "Aspects shipped by this distribution"
   not "kanon's aspects" or "the curated set" (per `P-protocol-not-product`
   §Implications, which forbids "kit's aspects" framing).
2. **Generation notice**: file header cites `pyproject.toml` + the per-aspect
   `manifest.yaml` files as the source of truth.
3. **CI gate**: `--check` mode regenerates and diffs against the committed
   file; exits 1 on drift. Same pattern as `mypy --strict` lockfiles or
   `ruff format --check`.

Why regex parse pyproject.toml instead of `tomllib` / `tomli`: matches the
repo's existing precedent in `scripts/check_deps.py`, avoids a new dev-dep
floor, and works identically on the Python 3.10 CI matrix where `tomllib`
is unavailable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_ASPECTS_PKG_ROOT = _REPO_ROOT / "packages" / "kanon-aspects" / "src" / "kanon_aspects"
_OUTPUT_PATH = _REPO_ROOT / "docs" / "reference-aspects.md"

# Match `[project.entry-points."kanon.aspects"]` on a line of its own (with
# optional surrounding whitespace). Capturing nothing — purely a section anchor.
_ENTRY_POINTS_HEADER = re.compile(
    r'^\s*\[project\.entry-points\."kanon\.aspects"\]\s*$',
    re.MULTILINE,
)

# Match a top-level TOML key-value line with a quoted string value. The
# entry-points table consists of these alone; we stop at the next `[` line.
_TOML_STRING_KV = re.compile(
    r'^\s*(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"(?P<value>[^"]+)"\s*(?:#.*)?$'
)


def _extract_aspect_slugs(pyproject_text: str) -> list[str]:
    """Return aspect slugs declared under [project.entry-points."kanon.aspects"].

    Aborts (raises ValueError) if the section is absent or contains no entries.
    Order: the slugs are sorted alphabetically so the generated artifact is
    stable across reorderings of the pyproject's entries.
    """
    match = _ENTRY_POINTS_HEADER.search(pyproject_text)
    if match is None:
        raise ValueError(
            f"{_PYPROJECT.relative_to(_REPO_ROOT)}: missing "
            f"[project.entry-points.\"kanon.aspects\"] section."
        )
    # Walk lines from the section header to the next `[` or EOF.
    rest = pyproject_text[match.end():]
    next_section = re.search(r"^\s*\[", rest, re.MULTILINE)
    section_body = rest[: next_section.start()] if next_section else rest

    slugs: list[str] = []
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        kv = _TOML_STRING_KV.match(line)
        if kv is None:
            continue
        slugs.append(kv.group("key"))
    if not slugs:
        raise ValueError(
            f"{_PYPROJECT.relative_to(_REPO_ROOT)}: "
            f"[project.entry-points.\"kanon.aspects\"] is empty."
        )
    return sorted(slugs)


def _load_aspect_manifest(slug: str) -> dict[str, object]:
    """Read the per-aspect manifest.yaml for *slug* (e.g., kanon-sdd).

    The directory name is the slug with hyphens replaced by underscores
    (Python import compatibility); the slug itself retains hyphens.
    """
    dir_name = slug.replace("-", "_")
    manifest_path = _ASPECTS_PKG_ROOT / "aspects" / dir_name / "manifest.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"per-aspect manifest missing for {slug!r}: "
            f"{manifest_path.relative_to(_REPO_ROOT)}"
        )
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"{manifest_path.relative_to(_REPO_ROOT)}: expected a YAML mapping, "
            f"got {type(data).__name__}"
        )
    return data


def _render_markdown(slugs: list[str]) -> str:
    """Build the markdown body. Stable output across runs."""
    lines: list[str] = [
        "# Reference aspects shipped by this distribution",
        "",
        "<!-- GENERATED FILE — DO NOT EDIT MANUALLY.",
        "Source of truth: `pyproject.toml` `[project.entry-points.\"kanon.aspects\"]`",
        "+ each aspect's `packages/kanon-aspects/src/kanon_aspects/aspects/<slug>/manifest.yaml`.",
        "Regenerate via: `python scripts/gen_reference_aspects.py`.",
        "Drift is enforced by CI via `python scripts/gen_reference_aspects.py --check`.",
        "Per ADR-0055 the per-aspect manifest is canonical; this file mirrors it for human review. -->",
        "",
        "Aspects shipped by this distribution. The substrate (`kanon-core`) ships zero aspects per ADR-0044 substrate-independence; the table below enumerates the demonstrations the `kanon-aspects` distribution publishes via the `kanon.aspects` Python entry-point group (per ADR-0040).",
        "",
        "Per `P-protocol-not-product`, these are reference implementations — not the substrate's product. A third-party publisher (an `acme-<vendor>-aspects` distribution) shipping its own aspects via the same entry-point group resolves through the same substrate code paths and would render an analogous table from its own pyproject.",
        "",
        "| Aspect | Stability | Depth range | Default depth | Description |",
        "|---|---|---|---|---|",
    ]
    for slug in slugs:
        manifest = _load_aspect_manifest(slug)
        stability = str(manifest.get("stability", ""))
        depth_range = manifest.get("depth-range", [])
        if isinstance(depth_range, list) and len(depth_range) == 2:
            range_str = f"{depth_range[0]}–{depth_range[1]}"
        else:
            range_str = "?"
        default_depth = manifest.get("default-depth", "")
        description = str(manifest.get("description", "")).strip()
        lines.append(
            f"| `{slug}` | {stability} | {range_str} | {default_depth} | {description} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate and diff against the committed file; exit 1 on drift.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_OUTPUT_PATH,
        help=f"Output path (default: {_OUTPUT_PATH.relative_to(_REPO_ROOT)}).",
    )
    args = parser.parse_args(argv)

    pyproject_text = _PYPROJECT.read_text(encoding="utf-8")
    try:
        slugs = _extract_aspect_slugs(pyproject_text)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    try:
        rendered = _render_markdown(slugs)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not args.output.is_file():
            print(f"FAIL: committed file missing: {args.output}", file=sys.stderr)
            print(f"Run: python scripts/gen_reference_aspects.py", file=sys.stderr)
            return 1
        committed = args.output.read_text(encoding="utf-8")
        if committed != rendered:
            print(
                f"FAIL: {args.output.relative_to(_REPO_ROOT)} is stale. "
                f"Regenerate via: python scripts/gen_reference_aspects.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {args.output.relative_to(_REPO_ROOT)} is in sync.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output.relative_to(_REPO_ROOT)} ({len(slugs)} aspects).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
