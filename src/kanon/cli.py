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
import sys
from pathlib import Path

import click
import yaml

from kanon import __version__
from kanon._manifest import (
    _aspect_depth_range,
    _aspect_sections,
    _expected_files,
    _load_aspect_manifest,
    _load_top_manifest,
    _namespaced_section,
    _now_iso,
)
from kanon._scaffold import (
    _aspects_with_meta,
    _assemble_agents_md,
    _build_bundle,
    _config_aspects,
    _merge_agents_md,
    _migrate_flat_protocols,
    _migrate_legacy_config,
    _read_config,
    _render_kit_md,
    _render_shims,
    _write_config,
    _write_tree_atomically,
)

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
