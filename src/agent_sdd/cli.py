"""agent-sdd CLI.

Subcommands:
    init <target>            Scaffold a new agent-sdd project at <target>.
    upgrade <target>          Update target's .agent-sdd/ to installed kit version.
    verify <target>           Validate target against its declared tier.
    tier set <target> <N>     Migrate target to tier N (0..3), mutable + non-destructive.

Per ADR-0008, tier migration affects AGENTS.md content inside HTML-comment-
delimited sections only; user content outside markers is never touched.
"""

from __future__ import annotations

import json
import os
import shutil
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml

import agent_sdd
from agent_sdd import __version__

_VALID_TIERS = {0, 1, 2, 3}

# Section names per tier — each is a named block inside AGENTS.md wrapped in
# <!-- agent-sdd:begin:<name> --> / <!-- agent-sdd:end:<name> --> markers.
_TIER_SECTIONS: dict[int, list[str]] = {
    0: [],
    1: ["plan-before-build"],
    2: ["plan-before-build", "spec-before-design"],
    3: ["plan-before-build", "spec-before-design"],
}

# Tier -> list of paths (relative to target) that the tier requires, in
# addition to everything the lower tier requires. Strict superset semantics.
_TIER_FILES: dict[int, list[str]] = {
    0: ["AGENTS.md", "CLAUDE.md", ".agent-sdd/config.yaml"],
    1: [
        "docs/development-process.md",
        "docs/decisions/README.md",
        "docs/decisions/_template.md",
        "docs/plans/README.md",
        "docs/plans/_template.md",
    ],
    2: [
        "docs/specs/README.md",
        "docs/specs/_template.md",
    ],
    3: [
        "docs/design/README.md",
        "docs/design/_template.md",
        "docs/foundations/README.md",
        "docs/foundations/vision.md",
        "docs/foundations/principles/README.md",
        "docs/foundations/personas/README.md",
    ],
}


def _expected_files(tier: int) -> list[str]:
    """Return the full path list a project at *tier* must have."""
    paths: list[str] = []
    for n in range(tier + 1):
        paths.extend(_TIER_FILES[n])
    return paths


def _templates_root() -> Path:
    """Location of the vendored template bundles inside the installed package."""
    return Path(agent_sdd.__file__).parent / "templates"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _fsync_dir(path: Path) -> None:
    """fsync *path* as a directory so recent rename dirents are durable. POSIX-only."""
    if os.name != "posix":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_config(target: Path) -> dict[str, Any]:
    config = target / ".agent-sdd" / "config.yaml"
    if not config.is_file():
        raise click.ClickException(
            f"Not an agent-sdd project: {target} (missing .agent-sdd/config.yaml)."
        )
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise click.ClickException(f"Malformed {config}: expected a YAML mapping.")
    return data


def _write_config(target: Path, kit_version: str, tier: int) -> None:
    config_dir = target / ".agent-sdd"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "kit_version": kit_version,
        "tier": tier,
        "tier_set_at": _now_iso(),
    }
    config_path = config_dir / "config.yaml"
    from agent_sdd._atomic import atomic_write_text

    atomic_write_text(config_path, yaml.safe_dump(payload, sort_keys=False))


def _load_harnesses() -> list[dict[str, Any]]:
    path = _templates_root() / "harnesses.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise click.ClickException(f"Malformed {path}: expected a YAML list.")
    return data


def _render_placeholder(text: str, context: dict[str, str]) -> str:
    """Safe-substitute ${placeholder} tokens; unknown placeholders pass through."""
    return string.Template(text).safe_substitute(context)


def _build_bundle(tier: int, context: dict[str, str]) -> dict[str, str]:
    """Return {relative_path: rendered_content} for every file in tier."""
    bundle: dict[str, str] = {}
    templates = _templates_root()
    for n in range(tier + 1):
        src_dir = templates / f"tier-{n}"
        if not src_dir.is_dir():
            continue
        for src_file in sorted(src_dir.rglob("*")):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(src_dir)
            rel_str = rel.as_posix()
            text = src_file.read_text(encoding="utf-8")
            bundle[rel_str] = _render_placeholder(text, context)
    return bundle


def _render_shims() -> dict[str, str]:
    """Return {relative_path: rendered_shim_content} for every registered harness."""
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


def _assemble_agents_md(tier: int, project_name: str) -> str:
    """Build AGENTS.md content by combining the tier-<N> AGENTS.md template
    with the tier-specific marker-delimited section fragments."""
    templates = _templates_root()
    agents_template = templates / f"tier-{tier}" / "AGENTS.md"
    if not agents_template.is_file():
        raise click.ClickException(f"Missing template: {agents_template}")
    text = _render_placeholder(
        agents_template.read_text(encoding="utf-8"),
        {"project_name": project_name, "tier": str(tier)},
    )
    # Fill marker-delimited blocks with their tier-<N> fragment content.
    for section in _TIER_SECTIONS[tier]:
        fragment = templates / "agents-md-sections" / f"{section}.md"
        if not fragment.is_file():
            continue
        fragment_text = fragment.read_text(encoding="utf-8")
        text = _replace_section(text, section, fragment_text)
    # Remove any sections not active at this tier (their markers may be absent).
    all_sections = {s for secs in _TIER_SECTIONS.values() for s in secs}
    inactive = all_sections - set(_TIER_SECTIONS[tier])
    for section in inactive:
        text = _remove_section(text, section)
    return text


def _replace_section(text: str, section: str, content: str) -> str:
    """Replace content between <!-- agent-sdd:begin:<section> --> and
    <!-- agent-sdd:end:<section> -->. If markers are absent, return text unchanged."""
    begin = f"<!-- agent-sdd:begin:{section} -->"
    end = f"<!-- agent-sdd:end:{section} -->"
    bi = text.find(begin)
    ei = text.find(end, bi + len(begin)) if bi >= 0 else -1
    if bi < 0 or ei < 0:
        return text
    before = text[: bi + len(begin)]
    after = text[ei:]
    return f"{before}\n{content.strip()}\n{after}"


def _remove_section(text: str, section: str) -> str:
    """Remove the marker pair and everything between them."""
    begin = f"<!-- agent-sdd:begin:{section} -->"
    end = f"<!-- agent-sdd:end:{section} -->"
    bi = text.find(begin)
    ei = text.find(end, bi + len(begin)) if bi >= 0 else -1
    if bi < 0 or ei < 0:
        return text
    # Strip a single leading blank line to avoid leaving a gap.
    before = text[:bi].rstrip() + "\n"
    after = text[ei + len(end):]
    if after.startswith("\n"):
        after = after.lstrip("\n")
        after = "\n\n" + after if after else "\n"
    return before + after


def _write_tree_atomically(
    target: Path,
    files: dict[str, str],
    force: bool = False,
) -> None:
    """Write *files* relative to *target*, atomically per-file.

    Uses the parent-dir fsync helper from _atomic. This is a simpler form
    than Sensei's full engine-swap because init/upgrade operate on distinct
    subpaths rather than an entire bundle directory.
    """
    from agent_sdd._atomic import atomic_write_text

    for rel, content in sorted(files.items()):
        dst = target / rel
        if dst.exists() and not force:
            # init() callers handle the force check upstream; this branch
            # only triggers if callers forgot. Be explicit.
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dst, content)


def _atomic_replace_dir(src: Path, dst: Path) -> None:
    """Replace *dst* with the contents of *src* atomically.

    Ports Sensei's _atomic_replace_engine pattern. *dst* after this call
    contains the exact contents of *src*; on failure, the previous *dst*
    (if any) is restored.
    """
    parent = dst.parent
    tmp = parent / f"{dst.name}.tmp"
    old = parent / f"{dst.name}.old"

    if old.exists() and not dst.exists():
        old.rename(dst)
        _fsync_dir(parent)
    elif old.exists() and dst.exists():
        shutil.rmtree(old)
    if tmp.exists():
        shutil.rmtree(tmp)

    try:
        shutil.copytree(src, tmp)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    swapped = False
    try:
        if dst.exists():
            dst.rename(old)
            _fsync_dir(parent)
            swapped = True
        tmp.rename(dst)
        _fsync_dir(parent)
    except Exception:
        if swapped and old.exists() and not dst.exists():
            old.rename(dst)
            _fsync_dir(parent)
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    if old.exists():
        shutil.rmtree(old, ignore_errors=True)


@click.group()
@click.version_option(__version__, prog_name="agent-sdd")
def main() -> None:
    """agent-sdd — portable, self-hosting SDD kit for LLM-agent-driven repos."""


@main.command()
@click.argument("target", type=click.Path(file_okay=False, path_type=Path))
@click.option("--tier", "tier_arg", type=click.IntRange(0, 3), default=1, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite an existing .agent-sdd/ directory.")
def init(target: Path, tier_arg: int, force: bool) -> None:
    """Scaffold a new agent-sdd project at TARGET."""
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    config_path = target / ".agent-sdd" / "config.yaml"
    if config_path.exists() and not force:
        raise click.ClickException(
            f"agent-sdd project already exists at {target}. "
            f"Run `agent-sdd upgrade` to refresh, or re-run with --force to reinitialise."
        )

    context = {"project_name": target.name, "tier": str(tier_arg)}

    # Build the bundle (tier-0 ∪ tier-1 ∪ ... ∪ tier-N) and render AGENTS.md separately.
    bundle = _build_bundle(tier_arg, context)
    bundle.pop("AGENTS.md", None)  # assembled below with section fragments
    bundle["AGENTS.md"] = _assemble_agents_md(tier_arg, target.name)
    bundle.update(_render_shims())

    _write_tree_atomically(target, bundle, force=force)
    _write_config(target, __version__, tier_arg)

    click.echo(f"Created agent-sdd project at {target} (tier {tier_arg}).")
    click.echo(f"Wrote {len(bundle) + 1} files plus .agent-sdd/config.yaml.")
    click.echo("Open this folder with any LLM coding agent to begin.")


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def upgrade(target: Path) -> None:
    """Refresh TARGET's .agent-sdd/ from the installed kit (preserving docs/, AGENTS.md, config)."""
    target = target.resolve()
    config = _read_config(target)
    tier_arg = int(config.get("tier", 1))
    old_version = config.get("kit_version", "unknown")

    if old_version == __version__:
        click.echo(f"Already at {__version__}. Nothing to upgrade.")
        return

    # For v0.1, upgrade rewrites AGENTS.md (marker sections only) and config;
    # tier-specific docs/ templates that exist in consumer's repo are
    # untouched (non-destructive). A future version may atomically refresh
    # individual template files the consumer hasn't customised.
    new_agents_md = _assemble_agents_md(tier_arg, target.name)
    existing = (target / "AGENTS.md").read_text(encoding="utf-8")
    from agent_sdd._atomic import atomic_write_text

    merged = _merge_agents_md(existing, new_agents_md)
    if merged != existing:
        atomic_write_text(target / "AGENTS.md", merged)
    _write_config(target, __version__, tier_arg)

    click.echo(f"Upgraded agent-sdd project at {target}: {old_version} → {__version__}")


_SECTION_INSERT_ANCHOR = "## Contribution Conventions"


def _insert_section(text: str, section: str, content: str) -> str:
    """Insert a new marker-delimited section into *text* at a sensible anchor.

    Preferred anchor: just before the first ``## Contribution Conventions``
    header. Fallback: append at end of file, preserving any trailing newline.
    User content outside the kit-managed markers is preserved — the
    inserted block is bracketed by new marker pairs.
    """
    begin = f"<!-- agent-sdd:begin:{section} -->"
    end = f"<!-- agent-sdd:end:{section} -->"
    block = f"{begin}\n{content.strip()}\n{end}\n"
    anchor_idx = text.find(_SECTION_INSERT_ANCHOR)
    if anchor_idx >= 0:
        before = text[:anchor_idx].rstrip() + "\n\n"
        after = text[anchor_idx:]
        return before + block + "\n" + after
    # Fallback: append.
    if text and not text.endswith("\n"):
        text = text + "\n"
    return text + "\n" + block


def _merge_agents_md(existing: str, new: str) -> str:
    """Copy marker-delimited sections from *new* into *existing*.

    - Sections present in both are replaced in-place (preserves existing
      user content outside the markers).
    - Sections present only in *new* are inserted at a sensible anchor
      (before ``## Contribution Conventions`` or at end of file).
    - Sections present only in *existing* are removed (their content is
      kit-managed; the new tier doesn't want them active).

    User content outside all marker pairs is never modified.
    """
    all_sections = {s for secs in _TIER_SECTIONS.values() for s in secs}
    result = existing
    for section in all_sections:
        begin = f"<!-- agent-sdd:begin:{section} -->"
        end = f"<!-- agent-sdd:end:{section} -->"
        # Extract new-section content.
        nb = new.find(begin)
        ne = new.find(end, nb + len(begin)) if nb >= 0 else -1
        if nb < 0 or ne < 0:
            # New AGENTS.md has removed this section; strip it from existing.
            result = _remove_section(result, section)
            continue
        new_section_body = new[nb + len(begin): ne].strip()
        if begin in result and end in result:
            result = _replace_section(result, section, new_section_body)
        else:
            # Section required by new tier but absent in existing — insert it.
            result = _insert_section(result, section, new_section_body)
    return result


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def verify(target: Path) -> None:
    """Verify TARGET conforms to its declared tier."""
    target = target.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = _read_config(target)
    except click.ClickException as exc:
        _emit_verify_report(target, None, errors=[exc.message], warnings=[], status="fail")
        sys.exit(2)

    tier_arg = int(config.get("tier", -1))
    if tier_arg not in _VALID_TIERS:
        errors.append(f"config.tier is {tier_arg!r}; must be one of {sorted(_VALID_TIERS)}.")
        _emit_verify_report(target, None, errors=errors, warnings=warnings, status="fail")
        sys.exit(2)

    # Required-file check.
    for rel in _expected_files(tier_arg):
        p = target / rel
        if not p.exists():
            errors.append(f"missing required file: {rel}")

    # AGENTS.md marker integrity.
    agents_md_path = target / "AGENTS.md"
    if agents_md_path.is_file():
        agents_text = agents_md_path.read_text(encoding="utf-8")
        for section in _TIER_SECTIONS[tier_arg]:
            begin = f"<!-- agent-sdd:begin:{section} -->"
            end = f"<!-- agent-sdd:end:{section} -->"
            if begin not in agents_text or end not in agents_text:
                errors.append(f"AGENTS.md missing marker pair for section '{section}' (tier {tier_arg}).")
        # Unbalanced markers at all?
        all_begins = agents_text.count("<!-- agent-sdd:begin:")
        all_ends = agents_text.count("<!-- agent-sdd:end:")
        if all_begins != all_ends:
            errors.append(
                f"AGENTS.md marker imbalance: {all_begins} begin(s), {all_ends} end(s)."
            )

    status = "fail" if errors else "ok"
    _emit_verify_report(target, tier_arg, errors=errors, warnings=warnings, status=status)
    if errors:
        sys.exit(1)


def _emit_verify_report(
    target: Path,
    tier: int | None,
    errors: list[str],
    warnings: list[str],
    status: str,
) -> None:
    report = {
        "target": str(target),
        "tier": tier,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }
    click.echo(json.dumps(report, indent=2))
    if status == "ok":
        click.echo(f"OK — tier-{tier} agent-sdd project at {target} is valid.", err=True)
    else:
        click.echo(f"FAIL — {len(errors)} error(s) at {target}.", err=True)


@main.group()
def tier() -> None:
    """Tier management: move a project between tiers (mutable, idempotent, non-destructive)."""


@tier.command("set")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("n", type=click.IntRange(0, 3))
def tier_set(target: Path, n: int) -> None:
    """Migrate TARGET to tier N (one of 0, 1, 2, 3)."""
    target = target.resolve()
    config = _read_config(target)
    current = int(config.get("tier", -1))
    if current not in _VALID_TIERS:
        raise click.ClickException(f"Invalid current tier {current!r} in config.")

    if current == n:
        # Idempotent: still update timestamp for auditability.
        _write_config(target, config.get("kit_version", __version__), n)
        click.echo(f"Tier already {n}. Noop (timestamp refreshed).")
        return

    context = {"project_name": target.name, "tier": str(n)}
    target_bundle = _build_bundle(n, context)
    target_bundle.pop("AGENTS.md", None)

    if n > current:
        # Tier-up: write new files that don't exist yet, rewrite AGENTS.md.
        added = 0
        for rel, content in sorted(target_bundle.items()):
            dst = target / rel
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            from agent_sdd._atomic import atomic_write_text

            atomic_write_text(dst, content)
            added += 1
        click.echo(f"Tier-up {current} → {n}: added {added} new file(s).")
    else:
        # Tier-down: retain all existing content; warn about artifacts beyond required.
        beyond: list[str] = []
        required = set(_expected_files(n))
        for current_rel in _expected_files(current):
            if current_rel not in required and (target / current_rel).exists():
                beyond.append(current_rel)
        click.echo(f"Tier-down {current} → {n} is non-destructive.")
        if beyond:
            click.echo("The following artifacts are now beyond required for this tier:")
            for rel in beyond:
                click.echo(f"  - {rel}")
            click.echo("You may keep, archive, or delete them as you choose.")

    # Rewrite AGENTS.md to match the new tier's sections.
    new_agents = _assemble_agents_md(n, target.name)
    existing_agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    merged = _merge_agents_md(existing_agents, new_agents)
    if merged != existing_agents:
        from agent_sdd._atomic import atomic_write_text

        atomic_write_text(target / "AGENTS.md", merged)

    _write_config(target, config.get("kit_version", __version__), n)
    click.echo(f"Tier set to {n} in .agent-sdd/config.yaml.")


if __name__ == "__main__":
    main()
