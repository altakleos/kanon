"""Scaffold assembly, config I/O, and file-tree writing.

Imports from ``_manifest`` (the dependency root) and provides the
content-construction layer that CLI commands orchestrate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml

from kanon import __version__
from kanon._manifest import (
    _UNPREFIXED_SECTIONS,
    _all_aspect_sections,
    _aspect_depth_range,
    _aspect_files,
    _aspect_path,
    _aspect_protocols,
    _aspect_sections,
    _kit_root,
    _load_aspect_manifest,
    _load_top_manifest,
    _namespaced_section,
    _now_iso,
    _parse_frontmatter,
    _render_placeholder,
)

# --- Config (v2 aspects / v1 tier auto-migration) ---


def _read_config(target: Path) -> dict[str, Any]:
    """Read .kanon/config.yaml. Auto-migrate legacy v1 to v2 in memory."""
    config_path = target / ".kanon" / "config.yaml"
    if not config_path.is_file():
        raise click.ClickException(
            f"Not a kanon project: {target} (missing .kanon/config.yaml)."
        )
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise click.ClickException(f"Malformed {config_path}: expected a YAML mapping.")
    return _migrate_legacy_config(data)


def _migrate_legacy_config(config: dict[str, Any]) -> dict[str, Any]:
    """One-way v1 (tier:) → v2 (aspects:) transformer. Idempotent if already v2."""
    if "aspects" in config:
        return config
    if "tier" not in config:
        return config
    return {
        "kit_version": config.get("kit_version", __version__),
        "aspects": {
            "sdd": {
                "depth": int(config["tier"]),
                "enabled_at": config.get("tier_set_at") or _now_iso(),
                "config": {},
            }
        },
    }


def _config_aspects(config: dict[str, Any]) -> dict[str, int]:
    """Extract {aspect_name: depth} from a v2 config."""
    aspects = config.get("aspects", {})
    return {name: int(entry["depth"]) for name, entry in aspects.items()}


def _write_config(
    target: Path,
    kit_version: str,
    aspects_with_meta: dict[str, dict[str, Any]],
) -> None:
    """Write a v2 .kanon/config.yaml atomically."""
    from kanon._atomic import atomic_write_text

    config_dir = target / ".kanon"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {"kit_version": kit_version, "aspects": aspects_with_meta}
    atomic_write_text(config_dir / "config.yaml", yaml.safe_dump(payload, sort_keys=False))


def _aspects_with_meta(aspects_to_enable: dict[str, int]) -> dict[str, dict[str, Any]]:
    now = _now_iso()
    return {
        name: {"depth": depth, "enabled_at": now, "config": {}}
        for name, depth in aspects_to_enable.items()
    }


# --- Harness shims ---


def _load_harnesses() -> list[dict[str, Any]]:
    path = _kit_root() / "harnesses.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise click.ClickException(f"Malformed {path}: expected a YAML list.")
    return data


def _render_shims() -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in _load_harnesses():
        path = entry["path"]
        body = entry.get("body", "Read and follow the instructions in `AGENTS.md`.\n")
        frontmatter = entry.get("frontmatter")
        if frontmatter:
            fm_text = yaml.safe_dump(frontmatter, sort_keys=False).strip()
            rendered = f"---\n{fm_text}\n---\n{body}"
        else:
            rendered = body
        result[path] = rendered
    return result


# --- Bundle construction ---


def _build_bundle(
    aspects: dict[str, int], context: dict[str, str]
) -> dict[str, str]:
    """{relative_path: content} for every file scaffolded for these aspects.

    Excludes always-synthesized files (AGENTS.md, .kanon/config.yaml, .kanon/kit.md).
    Protocol files go to `.kanon/protocols/<aspect>/<name>.md` (namespaced).
    """
    bundle: dict[str, str] = {}
    for aspect, depth in aspects.items():
        aspect_root = _aspect_path(aspect)
        files_root = aspect_root / "files"
        protocols_root = aspect_root / "protocols"
        for rel in _aspect_files(aspect, depth):
            src = files_root / rel
            if not src.is_file():
                raise click.ClickException(f"kit file missing: {src}")
            bundle[rel] = _render_placeholder(src.read_text(encoding="utf-8"), context)
        for rel in _aspect_protocols(aspect, depth):
            src = protocols_root / rel
            if not src.is_file():
                raise click.ClickException(f"kit protocol missing: {src}")
            bundle[f".kanon/protocols/{aspect}/{rel}"] = _render_placeholder(
                src.read_text(encoding="utf-8"), context
            )
    return bundle


def _render_protocols_index(aspects: dict[str, int]) -> str:
    """Render the cross-aspect unified protocols-index block (grouped by aspect)."""
    lines = [
        "## Active protocols",
        "",
        "Prose-as-code procedures available at this depth. When a trigger fires, "
        "read the protocol file in full and follow its numbered steps.",
        "",
    ]
    any_rows = False
    for aspect, depth in sorted(aspects.items()):
        aspect_root = _aspect_path(aspect)
        sub = _load_aspect_manifest(aspect)
        min_d, _ = _aspect_depth_range(aspect)
        rows: list[tuple[str, int, str]] = []
        for d in range(min_d, depth + 1):
            for name in sub.get(f"depth-{d}", {}).get("protocols", []) or []:
                proto = aspect_root / "protocols" / name
                if not proto.is_file():
                    continue
                fm = _parse_frontmatter(proto.read_text(encoding="utf-8"))
                invoke = str(fm.get("invoke-when", "")).strip() or "(no trigger declared)"
                rows.append((name, d, invoke))
        if rows:
            any_rows = True
            lines.append(f"### {aspect} (depth {depth})")
            lines.append("")
            lines.append("| Protocol | Depth-min | Invoke when |")
            lines.append("| --- | --- | --- |")
            for name, dmin, invoke in rows:
                slug = name.removesuffix(".md")
                lines.append(
                    f"| [`{slug}`](.kanon/protocols/{aspect}/{name}) | {dmin} | {invoke} |"
                )
            lines.append("")
    if not any_rows:
        lines.append("_No protocols active at current aspect depths._")
        lines.append("")
    return "\n".join(lines) + "\n"


def _render_kit_md(aspects: dict[str, int], project_name: str) -> str | None:
    """Render kit/kit.md with placeholder substitution. Uses sdd's depth for ${tier}."""
    src = _kit_root() / "kit.md"
    if not src.is_file():
        return None
    sdd_depth = aspects.get("sdd", 0)
    return _render_placeholder(
        src.read_text(encoding="utf-8"),
        {"project_name": project_name, "tier": str(sdd_depth)},
    )


def _assemble_agents_md(aspects: dict[str, int], project_name: str) -> str:
    """Build AGENTS.md for a project with the given aspect→depth mapping.

    Uses sdd's depth-N.md as the base template. Fills namespaced marker sections
    from each aspect's sections/ fragments; renders the unified protocols-index.
    Removes inactive sections from the base template.
    """
    sdd_depth = aspects.get("sdd", 0)
    base = _aspect_path("sdd") / "agents-md" / f"depth-{sdd_depth}.md"
    if not base.is_file():
        raise click.ClickException(f"Missing AGENTS.md base: {base}")
    text = _render_placeholder(
        base.read_text(encoding="utf-8"),
        {"project_name": project_name, "tier": str(sdd_depth)},
    )
    # Fill active marker sections for each aspect.
    for aspect, depth in sorted(aspects.items()):
        aspect_root = _aspect_path(aspect)
        for section in _aspect_sections(aspect, depth):
            namespaced = _namespaced_section(aspect, section)
            if section == "protocols-index":
                fragment_text = _render_protocols_index(aspects)
            else:
                fragment = aspect_root / "sections" / f"{section}.md"
                if not fragment.is_file():
                    continue
                fragment_text = fragment.read_text(encoding="utf-8")
            text = _replace_section(text, namespaced, fragment_text)
    # Remove inactive marker sections the base template may carry.
    active: set[str] = set()
    for aspect, depth in aspects.items():
        for section in _aspect_sections(aspect, depth):
            active.add(_namespaced_section(aspect, section))
    top = _load_top_manifest()
    possible: set[str] = set()
    for aspect_name in top["aspects"]:
        for section in _all_aspect_sections(aspect_name):
            possible.add(_namespaced_section(aspect_name, section))
    for section in possible - active:
        text = _remove_section(text, section)
    return text


def _replace_section(text: str, section: str, content: str) -> str:
    begin = f"<!-- kanon:begin:{section} -->"
    end = f"<!-- kanon:end:{section} -->"
    bi = text.find(begin)
    ei = text.find(end, bi + len(begin)) if bi >= 0 else -1
    if bi < 0 or ei < 0:
        return text
    before = text[: bi + len(begin)]
    after = text[ei:]
    return f"{before}\n{content.strip()}\n{after}"


def _remove_section(text: str, section: str) -> str:
    begin = f"<!-- kanon:begin:{section} -->"
    end = f"<!-- kanon:end:{section} -->"
    bi = text.find(begin)
    ei = text.find(end, bi + len(begin)) if bi >= 0 else -1
    if bi < 0 or ei < 0:
        return text
    before = text[:bi].rstrip() + "\n"
    after = text[ei + len(end):]
    if after.startswith("\n"):
        after = after.lstrip("\n")
        after = "\n\n" + after if after else "\n"
    return before + after


_SECTION_INSERT_ANCHOR = "## Contribution Conventions"


def _insert_section(text: str, section: str, content: str) -> str:
    begin = f"<!-- kanon:begin:{section} -->"
    end = f"<!-- kanon:end:{section} -->"
    block = f"{begin}\n{content.strip()}\n{end}\n"
    anchor_idx = text.find(_SECTION_INSERT_ANCHOR)
    if anchor_idx >= 0:
        before = text[:anchor_idx].rstrip() + "\n\n"
        after = text[anchor_idx:]
        return before + block + "\n" + after
    if text and not text.endswith("\n"):
        text = text + "\n"
    return text + "\n" + block


def _rewrite_legacy_markers(text: str) -> str:
    """Rename v1 unprefixed section markers to v2 namespaced form.

    Only runs on sections that are known to belong to the `sdd` aspect in v2
    (plan-before-build, spec-before-design). `protocols-index` stays unprefixed.
    """
    top = _load_top_manifest()
    if "sdd" not in top["aspects"]:
        return text
    for section in _all_aspect_sections("sdd"):
        if section in _UNPREFIXED_SECTIONS:
            continue
        namespaced = f"sdd/{section}"
        # Skip if already namespaced in this text.
        if f"<!-- kanon:begin:{namespaced} -->" in text:
            continue
        text = text.replace(
            f"<!-- kanon:begin:{section} -->",
            f"<!-- kanon:begin:{namespaced} -->",
        )
        text = text.replace(
            f"<!-- kanon:end:{section} -->",
            f"<!-- kanon:end:{namespaced} -->",
        )
    return text


def _merge_agents_md(existing: str, new: str) -> str:
    """Copy marker-delimited sections from *new* into *existing*.

    - Sections present in both: replaced in-place.
    - Sections present only in *new*: inserted at a sensible anchor.
    - Sections present only in *existing* (active at a different aspect-depth): removed.
    User content outside marker pairs is never modified.

    Also migrates v1 unprefixed markers to v2 namespaced form.
    """
    top = _load_top_manifest()
    possible: set[str] = set()
    for aspect_name in top["aspects"]:
        for section in _all_aspect_sections(aspect_name):
            possible.add(_namespaced_section(aspect_name, section))

    result = _rewrite_legacy_markers(existing)

    for section in possible:
        begin = f"<!-- kanon:begin:{section} -->"
        end = f"<!-- kanon:end:{section} -->"
        nb = new.find(begin)
        ne = new.find(end, nb + len(begin)) if nb >= 0 else -1
        if nb < 0 or ne < 0:
            result = _remove_section(result, section)
            continue
        new_body = new[nb + len(begin): ne].strip()
        if begin in result and end in result:
            result = _replace_section(result, section, new_body)
        else:
            result = _insert_section(result, section, new_body)
    return result


def _write_tree_atomically(
    target: Path, files: dict[str, str], force: bool = False
) -> None:
    from kanon._atomic import atomic_write_text

    for rel, content in sorted(files.items()):
        dst = target / rel
        if dst.exists() and not force:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dst, content)


def _migrate_flat_protocols(target: Path, aspects: dict[str, int]) -> bool:
    """Move .kanon/protocols/*.md (flat, v1) under .kanon/protocols/sdd/ (v2 namespace).

    Returns True if any file was migrated.
    """
    protocols_dir = target / ".kanon" / "protocols"
    if not protocols_dir.is_dir():
        return False
    flat = [p for p in protocols_dir.glob("*.md") if p.is_file()]
    if not flat:
        return False
    if "sdd" not in aspects:
        return False
    sdd_dir = protocols_dir / "sdd"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    for p in flat:
        dest = sdd_dir / p.name
        if dest.exists():
            p.unlink()
        else:
            p.rename(dest)
    return True
