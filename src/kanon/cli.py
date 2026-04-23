"""kanon CLI.

Subcommands:
    init <target>                  Scaffold a new kanon project at <target>.
    upgrade <target>               Refresh <target>'s .kanon/ to installed kit version.
    verify <target>                Validate <target> against its declared aspects.
    tier set <target> <N>          Back-compat sugar for `aspect set-depth <target> sdd <N>`.
    aspect list                    List available aspects in the installed kit.
    aspect info <name>             Show aspect metadata.
    aspect set-depth <target> <aspect> <N>
                                   Change an aspect's depth (mutable, non-destructive).

Per ADR-0012, the kit is aspect-structured: consumer config declares
`aspects: {name: {depth, enabled_at, config}}`. `sdd` is the only stable
aspect shipping at v0.2; its depth-dial replaces v0.1's tier. Legacy
`tier: N` in a consumer config auto-migrates to `aspects: {sdd: {depth: N}}`
on first `kanon upgrade`.

See docs/design/aspect-model.md and ADR-0012 / ADR-0013.
"""

from __future__ import annotations

import json
import os
import string
import sys
from datetime import datetime, timezone
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import click
import yaml

import kanon
from kanon import __version__

# Files the CLI always synthesizes (not sourced from any aspect's files/ tree).
_ALWAYS_SYNTHESIZED = ("AGENTS.md", ".kanon/config.yaml")

# Section names that stay unprefixed in AGENTS.md markers (cross-aspect by design).
_UNPREFIXED_SECTIONS = frozenset({"protocols-index"})


def _kit_root() -> Path:
    return Path(kanon.__file__).parent / "kit"


# --- Manifest loaders ---


@lru_cache(maxsize=1)
def _load_top_manifest() -> dict[str, Any]:
    """Load the aspect registry at src/kanon/kit/manifest.yaml."""
    path = _kit_root() / "manifest.yaml"
    if not path.is_file():
        raise click.ClickException(f"kit manifest missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise click.ClickException(f"malformed {path}: expected a YAML mapping.")
    aspects = data.get("aspects")
    if not isinstance(aspects, dict) or not aspects:
        raise click.ClickException(f"{path}: missing or empty 'aspects' mapping.")
    for name, entry in aspects.items():
        if not isinstance(entry, dict):
            raise click.ClickException(f"{path}: aspects.{name} must be a mapping.")
        for field in ("path", "stability", "depth-range", "default-depth"):
            if field not in entry:
                raise click.ClickException(
                    f"{path}: aspects.{name}: missing required field {field!r}."
                )
        if entry["stability"] not in {"experimental", "stable", "deprecated"}:
            raise click.ClickException(
                f"{path}: aspects.{name}: invalid stability {entry['stability']!r}."
            )
        rng = entry["depth-range"]
        if not (isinstance(rng, list) and len(rng) == 2):
            raise click.ClickException(
                f"{path}: aspects.{name}.depth-range must be [min, max]."
            )
    return data


@cache
def _load_aspect_manifest(aspect: str) -> dict[str, Any]:
    """Load src/kanon/kit/aspects/<aspect>/manifest.yaml."""
    top = _load_top_manifest()
    if aspect not in top["aspects"]:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    sub_path = _kit_root() / top["aspects"][aspect]["path"] / "manifest.yaml"
    if not sub_path.is_file():
        raise click.ClickException(f"aspect sub-manifest missing: {sub_path}")
    data = yaml.safe_load(sub_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise click.ClickException(f"malformed {sub_path}: expected a YAML mapping.")
    min_d, max_d = _aspect_depth_range(aspect)
    for d in range(min_d, max_d + 1):
        key = f"depth-{d}"
        if key not in data:
            raise click.ClickException(f"{sub_path}: missing {key!r} entry.")
        if not isinstance(data[key], dict):
            raise click.ClickException(f"{sub_path}: {key} must be a mapping.")
    return data


def _aspect_depth_range(aspect: str) -> tuple[int, int]:
    top = _load_top_manifest()
    rng = top["aspects"][aspect]["depth-range"]
    return int(rng[0]), int(rng[1])


def _aspect_path(aspect: str) -> Path:
    top = _load_top_manifest()
    return _kit_root() / top["aspects"][aspect]["path"]


def _aspect_files(aspect: str, depth: int) -> list[str]:
    sub = _load_aspect_manifest(aspect)
    min_d, _ = _aspect_depth_range(aspect)
    paths: list[str] = []
    for d in range(min_d, depth + 1):
        paths.extend(sub.get(f"depth-{d}", {}).get("files", []) or [])
    return paths


def _aspect_protocols(aspect: str, depth: int) -> list[str]:
    sub = _load_aspect_manifest(aspect)
    min_d, _ = _aspect_depth_range(aspect)
    paths: list[str] = []
    for d in range(min_d, depth + 1):
        paths.extend(sub.get(f"depth-{d}", {}).get("protocols", []) or [])
    return paths


def _aspect_sections(aspect: str, depth: int) -> list[str]:
    sub = _load_aspect_manifest(aspect)
    min_d, _ = _aspect_depth_range(aspect)
    sections: list[str] = []
    for d in range(min_d, depth + 1):
        sections.extend(sub.get(f"depth-{d}", {}).get("sections", []) or [])
    return sections


def _all_aspect_sections(aspect: str) -> set[str]:
    """Every section name across all depths of aspect."""
    sub = _load_aspect_manifest(aspect)
    min_d, max_d = _aspect_depth_range(aspect)
    seen: set[str] = set()
    for d in range(min_d, max_d + 1):
        for name in sub.get(f"depth-{d}", {}).get("sections", []) or []:
            seen.add(name)
    return seen


def _namespaced_section(aspect: str, section: str) -> str:
    """Section name as it appears in an AGENTS.md marker."""
    if section in _UNPREFIXED_SECTIONS:
        return section
    return f"{aspect}/{section}"


def _expected_files(aspects: dict[str, int]) -> list[str]:
    """Return the full path list a project with these aspects must have."""
    paths: list[str] = list(_ALWAYS_SYNTHESIZED)
    if (_kit_root() / "kit.md").is_file():
        paths.append(".kanon/kit.md")
    for aspect, depth in aspects.items():
        paths.extend(_aspect_files(aspect, depth))
        paths.extend(
            f".kanon/protocols/{aspect}/{p}" for p in _aspect_protocols(aspect, depth)
        )
    return paths


# --- Small helpers ---


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _fsync_dir(path: Path) -> None:
    if os.name != "posix":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _render_placeholder(text: str, context: dict[str, str]) -> str:
    return string.Template(text).safe_substitute(context)


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


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
        "Prose-as-code procedures available at this tier. When a trigger fires, "
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


# --- CLI commands ---


@click.group()
@click.version_option(__version__, prog_name="kanon")
def main() -> None:
    """kanon — portable, self-hosting SDD kit for LLM-agent-driven repos."""


@main.command()
@click.argument("target", type=click.Path(file_okay=False, path_type=Path))
@click.option(
    "--tier",
    "tier_arg",
    type=click.IntRange(0, 3),
    default=None,
    show_default=False,
    help="Shorthand for `sdd` aspect depth. Defaults to sdd's default-depth.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing .kanon/ directory.")
def init(target: Path, tier_arg: int | None, force: bool) -> None:
    """Scaffold a new kanon project at TARGET."""
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    config_path = target / ".kanon" / "config.yaml"
    if config_path.exists() and not force:
        raise click.ClickException(
            f"kanon project already exists at {target}. "
            f"Run `kanon upgrade` to refresh, or re-run with --force to reinitialise."
        )

    top = _load_top_manifest()
    sdd_default = int(top["aspects"]["sdd"]["default-depth"])
    depth = tier_arg if tier_arg is not None else sdd_default
    aspects_to_enable = {"sdd": depth}

    context = {"project_name": target.name, "tier": str(depth)}

    bundle = _build_bundle(aspects_to_enable, context)
    bundle["AGENTS.md"] = _assemble_agents_md(aspects_to_enable, target.name)
    kit_md = _render_kit_md(aspects_to_enable, target.name)
    if kit_md is not None:
        bundle[".kanon/kit.md"] = kit_md
    bundle.update(_render_shims())

    _write_tree_atomically(target, bundle, force=force)
    _write_config(target, __version__, _aspects_with_meta(aspects_to_enable))

    click.echo(f"Created kanon project at {target}.")
    click.echo(f"Wrote {len(bundle) + 1} files plus .kanon/config.yaml.")
    click.echo(
        "Aspects: " + ", ".join(f"{a}={d}" for a, d in sorted(aspects_to_enable.items()))
    )
    click.echo("Open this folder with any LLM coding agent to begin.")


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def upgrade(target: Path) -> None:
    """Refresh TARGET's .kanon/ from the installed kit (preserving docs/, AGENTS.md, config)."""
    target = target.resolve()
    config_path = target / ".kanon" / "config.yaml"
    if not config_path.is_file():
        raise click.ClickException(
            f"Not a kanon project: {target} (missing .kanon/config.yaml)."
        )
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise click.ClickException(f"Malformed {config_path}: expected a YAML mapping.")
    was_legacy = "aspects" not in raw and "tier" in raw
    config = _migrate_legacy_config(raw)
    aspects = _config_aspects(config)
    old_version = config.get("kit_version", "unknown")

    if old_version == __version__ and not was_legacy:
        click.echo(f"Already at {__version__}. Nothing to upgrade.")
        return

    from kanon._atomic import atomic_write_text

    migrated_flat = _migrate_flat_protocols(target, aspects)

    new_agents_md = _assemble_agents_md(aspects, target.name)
    agents_path = target / "AGENTS.md"
    if agents_path.is_file():
        existing = agents_path.read_text(encoding="utf-8")
        merged = _merge_agents_md(existing, new_agents_md)
        if merged != existing:
            atomic_write_text(agents_path, merged)
    else:
        atomic_write_text(agents_path, new_agents_md)

    kit_md = _render_kit_md(aspects, target.name)
    if kit_md is not None:
        atomic_write_text(target / ".kanon" / "kit.md", kit_md)

    _write_config(target, __version__, _aspects_with_meta(aspects))

    if was_legacy:
        click.echo("Migrated legacy tier config to aspect model.")
    if migrated_flat:
        click.echo("Namespaced flat .kanon/protocols/*.md under sdd/.")
    click.echo(f"Upgraded kanon project at {target}: {old_version} → {__version__}")


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def verify(target: Path) -> None:
    """Verify TARGET conforms to its declared aspects."""
    target = target.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = _read_config(target)
    except click.ClickException as exc:
        _emit_verify_report(
            target, {}, errors=[exc.message], warnings=[], status="fail"
        )
        sys.exit(2)

    aspects = _config_aspects(config)
    if not aspects:
        errors.append("config.aspects is empty; nothing to verify.")
        _emit_verify_report(target, aspects, errors=errors, warnings=warnings, status="fail")
        sys.exit(2)

    top = _load_top_manifest()
    for name, depth in aspects.items():
        if name not in top["aspects"]:
            errors.append(
                f"config.aspects.{name}: aspect not in installed kit registry."
            )
            continue
        min_d, max_d = _aspect_depth_range(name)
        if not (min_d <= depth <= max_d):
            errors.append(
                f"config.aspects.{name}.depth={depth}: outside range [{min_d},{max_d}]."
            )

    for rel in _expected_files(aspects):
        p = target / rel
        if not p.exists():
            errors.append(f"missing required file: {rel}")

    agents_md_path = target / "AGENTS.md"
    if agents_md_path.is_file():
        agents_text = agents_md_path.read_text(encoding="utf-8")
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

    status = "fail" if errors else "ok"
    _emit_verify_report(target, aspects, errors=errors, warnings=warnings, status=status)
    if errors:
        sys.exit(1)


def _emit_verify_report(
    target: Path,
    aspects: dict[str, int],
    errors: list[str],
    warnings: list[str],
    status: str,
) -> None:
    report = {
        "target": str(target),
        "aspects": aspects,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }
    click.echo(json.dumps(report, indent=2))
    if status == "ok":
        click.echo(f"OK — kanon project at {target} is valid.", err=True)
    else:
        click.echo(f"FAIL — {len(errors)} error(s) at {target}.", err=True)


@main.group()
def tier() -> None:
    """Back-compat: sugar for `aspect set-depth <target> sdd <N>`."""


@tier.command("set")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("n", type=click.IntRange(0, 3))
def tier_set(target: Path, n: int) -> None:
    """Migrate TARGET's sdd aspect depth to N (sugar for aspect set-depth)."""
    _set_aspect_depth(target, "sdd", n, legacy_tier_verb=True)


@main.group()
def aspect() -> None:
    """Aspect management (ADR-0012)."""


@aspect.command("list")
def aspect_list() -> None:
    """List aspects available in the installed kit."""
    top = _load_top_manifest()
    for name in sorted(top["aspects"]):
        entry = top["aspects"][name]
        rng = entry["depth-range"]
        click.echo(
            f"{name}\t{entry['stability']}\tdepth {rng[0]}-{rng[1]} "
            f"(default {entry['default-depth']})"
        )


@aspect.command("info")
@click.argument("name")
def aspect_info(name: str) -> None:
    """Print metadata for an aspect."""
    top = _load_top_manifest()
    if name not in top["aspects"]:
        raise click.ClickException(
            f"Unknown aspect: {name!r}. See `kanon aspect list`."
        )
    entry = top["aspects"][name]
    sub = _load_aspect_manifest(name)
    click.echo(f"Aspect: {name}")
    click.echo(f"  Stability:     {entry['stability']}")
    click.echo(f"  Depth range:   {entry['depth-range'][0]}-{entry['depth-range'][1]}")
    click.echo(f"  Default depth: {entry['default-depth']}")
    click.echo(f"  Requires:      {', '.join(entry.get('requires', [])) or '(none)'}")
    min_d, max_d = _aspect_depth_range(name)
    for d in range(min_d, max_d + 1):
        depth_entry = sub.get(f"depth-{d}", {})
        files = depth_entry.get("files", []) or []
        protos = depth_entry.get("protocols", []) or []
        click.echo(f"  Depth {d}: {len(files)} file(s), {len(protos)} protocol(s)")


@aspect.command("set-depth")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("aspect_name")
@click.argument("n", type=int)
def aspect_set_depth(target: Path, aspect_name: str, n: int) -> None:
    """Change TARGET's <aspect_name> depth to N (mutable, idempotent, non-destructive)."""
    _set_aspect_depth(target, aspect_name, n)


def _set_aspect_depth(
    target: Path, aspect_name: str, n: int, legacy_tier_verb: bool = False
) -> None:
    target = target.resolve()
    config = _read_config(target)
    top = _load_top_manifest()
    if aspect_name not in top["aspects"]:
        raise click.ClickException(f"Unknown aspect: {aspect_name!r}.")
    min_d, max_d = _aspect_depth_range(aspect_name)
    if not (min_d <= n <= max_d):
        raise click.ClickException(
            f"aspect {aspect_name}: depth {n} outside range [{min_d},{max_d}]."
        )

    aspects = _config_aspects(config)
    kit_version = config.get("kit_version", __version__)
    current = aspects.get(aspect_name, -1)
    aspects_meta = dict(config.get("aspects", {}))

    if current == n:
        entry = dict(aspects_meta.get(aspect_name, {}))
        entry["depth"] = n
        entry["enabled_at"] = _now_iso()
        entry.setdefault("config", {})
        aspects_meta[aspect_name] = entry
        _write_config(target, kit_version, aspects_meta)
        verb = "Tier" if legacy_tier_verb else f"Aspect {aspect_name} depth"
        click.echo(f"{verb} already {n}. Noop (timestamp refreshed).")
        return

    new_aspects_snapshot = dict(aspects)
    new_aspects_snapshot[aspect_name] = n
    context = {"project_name": target.name, "tier": str(n)}
    target_bundle = _build_bundle(new_aspects_snapshot, context)

    from kanon._atomic import atomic_write_text

    if n > current:
        added = 0
        for rel, content in sorted(target_bundle.items()):
            dst = target / rel
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(dst, content)
            added += 1
        verb = "Tier-up" if legacy_tier_verb else f"Aspect-up ({aspect_name})"
        click.echo(f"{verb} {current} → {n}: added {added} new file(s).")
    else:
        beyond: list[str] = []
        required = set(_expected_files(new_aspects_snapshot))
        for rel in _expected_files(aspects):
            if rel not in required and (target / rel).exists():
                beyond.append(rel)
        verb = "Tier-down" if legacy_tier_verb else f"Aspect-down ({aspect_name})"
        click.echo(f"{verb} {current} → {n} is non-destructive.")
        if beyond:
            click.echo("The following artifacts are now beyond required for this depth:")
            for rel in beyond:
                click.echo(f"  - {rel}")
            click.echo("You may keep, archive, or delete them as you choose.")

    new_agents = _assemble_agents_md(new_aspects_snapshot, target.name)
    existing_agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    merged = _merge_agents_md(existing_agents, new_agents)
    if merged != existing_agents:
        atomic_write_text(target / "AGENTS.md", merged)

    kit_md = _render_kit_md(new_aspects_snapshot, target.name)
    if kit_md is not None:
        atomic_write_text(target / ".kanon" / "kit.md", kit_md)

    entry = dict(aspects_meta.get(aspect_name, {}))
    entry["depth"] = n
    entry["enabled_at"] = _now_iso()
    entry.setdefault("config", {})
    aspects_meta[aspect_name] = entry
    _write_config(target, kit_version, aspects_meta)

    verb = "Tier" if legacy_tier_verb else f"Aspect {aspect_name} depth"
    click.echo(f"{verb} set to {n} in .kanon/config.yaml.")


if __name__ == "__main__":
    main()
