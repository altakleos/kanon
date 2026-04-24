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

import hashlib
import json
import operator
import sys
from pathlib import Path
from typing import Any

import click
import yaml

from kanon import __version__
from kanon._manifest import (
    _aspect_depth_range,
    _aspect_sections,
    _default_aspects,
    _expected_files,
    _load_aspect_manifest,
    _load_top_manifest,
    _namespaced_section,
    _now_iso,
    _parse_frontmatter,
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


def _parse_aspects_flag(raw: str, top: dict[str, Any]) -> dict[str, int]:
    """Parse ``--aspects sdd:1,worktrees:2`` into a validated dict."""
    result: dict[str, int] = {}
    for token in raw.split(","):
        token = token.strip()
        if ":" not in token:
            raise click.ClickException(
                f"Invalid aspect token {token!r}: expected name:depth."
            )
        name, depth_s = token.split(":", 1)
        if name not in top["aspects"]:
            raise click.ClickException(
                f"Unknown aspect {name!r}. See `kanon aspect list`."
            )
        try:
            depth = int(depth_s)
        except ValueError:
            raise click.ClickException(
                f"Invalid depth {depth_s!r} for aspect {name!r}: must be an integer."
            ) from None
        rng = top["aspects"][name]["depth-range"]
        min_d, max_d = int(rng[0]), int(rng[1])
        if not (min_d <= depth <= max_d):
            raise click.ClickException(
                f"Aspect {name!r}: depth {depth} outside range [{min_d},{max_d}]."
            )
        result[name] = depth
    if not result:
        raise click.ClickException("--aspects requires at least one aspect:depth pair.")
    return result


_OPS: dict[str, Any] = {
    ">=": operator.ge,
    ">": operator.gt,
    "==": operator.eq,
    "<": operator.lt,
    "<=": operator.le,
}


def _check_requires(
    aspect_name: str, proposed_aspects: dict[str, int], top: dict[str, Any]
) -> str | None:
    """Return error message if requires: predicates are unmet, else None."""
    for predicate in top["aspects"][aspect_name].get("requires", []):
        dep_name, op, dep_depth_s = predicate.split()
        dep_depth = int(dep_depth_s)
        actual = proposed_aspects.get(dep_name, 0)
        if not _OPS[op](actual, dep_depth):
            return (
                f"Aspect {aspect_name!r} requires {predicate!r}, "
                f"but {dep_name!r} is at depth {actual}."
            )
    return None


def _check_removal_dependents(
    aspect_name: str, remaining_aspects: dict[str, int], top: dict[str, Any]
) -> str | None:
    """Return error if any remaining aspect depends on the one being removed."""
    for name, depth in remaining_aspects.items():
        if depth <= 0:
            continue
        for predicate in top["aspects"][name].get("requires", []):
            dep_name = predicate.split()[0]
            if dep_name == aspect_name:
                return (
                    f"Cannot remove {aspect_name!r}: "
                    f"aspect {name!r} requires {predicate!r}."
                )
    return None


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
@click.option(
    "--aspects",
    "aspects_arg",
    default=None,
    help="Comma-separated aspect:depth pairs (e.g., sdd:1,worktrees:2).",
)
@click.option("--force", is_flag=True, help="Overwrite an existing .kanon/ directory.")
def init(target: Path, tier_arg: int | None, aspects_arg: str | None, force: bool) -> None:
    """Scaffold a new kanon project at TARGET."""
    if tier_arg is not None and aspects_arg is not None:
        raise click.ClickException("--tier and --aspects are mutually exclusive.")

    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    config_path = target / ".kanon" / "config.yaml"
    if config_path.exists() and not force:
        raise click.ClickException(
            f"kanon project already exists at {target}. "
            f"Run `kanon upgrade` to refresh, or re-run with --force to reinitialise."
        )

    top = _load_top_manifest()

    if aspects_arg is not None:
        aspects_to_enable = _parse_aspects_flag(aspects_arg, top)
    elif tier_arg is not None:
        # --tier is sugar for --aspects sdd:N (backward compat)
        aspects_to_enable = {"sdd": tier_arg}
    else:
        aspects_to_enable = _default_aspects()

    # Use the sdd depth as the tier context value if sdd is enabled, else "0".
    tier_ctx = str(aspects_to_enable.get("sdd", 0))
    context = {"project_name": target.name, "tier": tier_ctx}

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

    # Fidelity lock checks (depth >= 2, lock file present)
    sdd_depth = aspects.get("sdd", 0)
    lock_path = target / ".kanon" / "fidelity.lock"
    if sdd_depth >= 2 and lock_path.is_file():
        lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        if isinstance(lock_data, dict) and "entries" in lock_data:
            lock_entries = lock_data["entries"] or {}
            specs_dir = target / "docs" / "specs"
            current_specs = _accepted_or_draft_specs(specs_dir)
            for slug, entry in sorted(lock_entries.items()):
                spec_path = specs_dir / f"{slug}.md"
                if spec_path.is_file():
                    current_sha = _spec_sha(spec_path)
                    if current_sha != entry.get("spec_sha"):
                        warnings.append(
                            f"fidelity: spec {slug} has changed since last fidelity update."
                        )
                # Phase 2: check fixture SHAs
                for fpath, locked_sha in sorted(
                    (entry.get("fixture_shas") or {}).items()
                ):
                    full = target / fpath
                    if not full.is_file():
                        warnings.append(
                            f"fidelity: fixture {fpath} no longer exists (spec: {slug})."
                        )
                    elif _spec_sha(full) != locked_sha:
                        warnings.append(
                            f"fidelity: fixture {fpath} has changed since last fidelity update (spec: {slug})."
                        )
            for p in current_specs:
                if p.stem not in lock_entries:
                    warnings.append(
                        f"fidelity: spec {p.stem} is not tracked in fidelity.lock."
                    )

    # Verified-by checks (depth >= 2)
    if sdd_depth >= 2:
        import re as _re

        _inv_re = _re.compile(r"<!--\s*(INV-[a-z][a-z0-9-]*-[a-z][a-z0-9-]*)\s*-->")
        specs_dir = target / "docs" / "specs"
        if specs_dir.is_dir():
            for sp in sorted(specs_dir.glob("*.md")):
                if sp.name.startswith("_") or sp.name == "README.md":
                    continue
                text = sp.read_text(encoding="utf-8")
                fm = _parse_frontmatter(text)
                if fm.get("status") != "accepted" or fm.get("fixtures_deferred"):
                    continue
                anchors = _inv_re.findall(text)
                if not anchors:
                    continue
                coverage = fm.get("invariant_coverage") or {}
                missing = [a for a in anchors if a not in coverage]
                if missing:
                    warnings.append(
                        f"verified-by: {sp.name} missing invariant_coverage "
                        f"for {len(missing)} anchor(s)."
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


@aspect.command("add")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("aspect_name")
def aspect_add(target: Path, aspect_name: str) -> None:
    """Enable an aspect at its default depth."""
    target = target.resolve()
    config = _read_config(target)
    top = _load_top_manifest()
    if aspect_name not in top["aspects"]:
        raise click.ClickException(
            f"Unknown aspect: {aspect_name!r}. See `kanon aspect list`."
        )
    aspects = _config_aspects(config)
    if aspect_name in aspects and aspects[aspect_name] > 0:
        raise click.ClickException(
            f"Aspect {aspect_name!r} is already enabled at depth {aspects[aspect_name]}. "
            f"Use `kanon aspect set-depth` to change depth."
        )
    default_depth = int(top["aspects"][aspect_name]["default-depth"])
    # Check requires before enabling
    proposed = dict(aspects)
    proposed[aspect_name] = default_depth
    err = _check_requires(aspect_name, proposed, top)
    if err:
        raise click.ClickException(err)
    _set_aspect_depth(target, aspect_name, default_depth)


@aspect.command("remove")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("aspect_name")
def aspect_remove(target: Path, aspect_name: str) -> None:
    """Remove an aspect (non-destructive: scaffolded files are left on disk)."""
    target = target.resolve()
    config = _read_config(target)
    aspects = _config_aspects(config)
    if aspect_name not in aspects:
        raise click.ClickException(
            f"Aspect {aspect_name!r} is not enabled in this project."
        )

    # Check if other enabled aspects depend on this one
    top = _load_top_manifest()
    remaining = {k: v for k, v in aspects.items() if k != aspect_name}
    err = _check_removal_dependents(aspect_name, remaining, top)
    if err:
        raise click.ClickException(err)

    from kanon._atomic import atomic_write_text

    # Remove aspect from config
    aspects_meta = dict(config.get("aspects", {}))
    del aspects_meta[aspect_name]
    kit_version = config.get("kit_version", __version__)

    # Remaining aspects for AGENTS.md reassembly
    remaining = {k: int(v["depth"]) for k, v in aspects_meta.items()}

    # Re-assemble and merge AGENTS.md without the removed aspect
    new_agents = _assemble_agents_md(remaining, target.name)
    agents_path = target / "AGENTS.md"
    if agents_path.is_file():
        existing = agents_path.read_text(encoding="utf-8")
        merged = _merge_agents_md(existing, new_agents)
        if merged != existing:
            atomic_write_text(agents_path, merged)

    # Update kit.md
    kit_md = _render_kit_md(remaining, target.name)
    if kit_md is not None:
        atomic_write_text(target / ".kanon" / "kit.md", kit_md)

    _write_config(target, kit_version, aspects_meta)

    # List aspect-specific files left on disk
    from kanon._manifest import _aspect_files, _aspect_protocols

    depth = aspects[aspect_name]
    left: list[str] = list(_aspect_files(aspect_name, depth))
    left.extend(
        f".kanon/protocols/{aspect_name}/{p}"
        for p in _aspect_protocols(aspect_name, depth)
    )
    on_disk = [r for r in left if (target / r).exists()]
    click.echo(f"Removed aspect {aspect_name!r} from config and AGENTS.md.")
    if on_disk:
        click.echo("Scaffolded files left on disk (non-destructive):")
        for rel in on_disk:
            click.echo(f"  - {rel}")


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

    # Enforce requires: predicates
    proposed = dict(aspects)
    proposed[aspect_name] = n
    err = _check_requires(aspect_name, proposed, top)
    if err:
        raise click.ClickException(err)

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


# --- fidelity lock ---


def _spec_sha(path: Path) -> str:
    """Return ``sha256:<hex>`` of raw file bytes."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _accepted_or_draft_specs(specs_dir: Path) -> list[Path]:
    """Return sorted spec paths with status accepted or draft."""
    result: list[Path] = []
    if not specs_dir.is_dir():
        return result
    for p in sorted(specs_dir.glob("*.md")):
        if p.name.startswith("_") or p.name == "README.md":
            continue
        fm = _parse_frontmatter(p.read_text(encoding="utf-8"))
        if fm.get("status") in ("accepted", "draft"):
            result.append(p)
    return result


def _fixture_shas(spec_path: Path, target: Path) -> dict[str, str]:
    """Extract unique fixture file paths from invariant_coverage and compute their SHAs."""
    fm = _parse_frontmatter(spec_path.read_text(encoding="utf-8"))
    coverage = fm.get("invariant_coverage")
    if not coverage or not isinstance(coverage, dict):
        return {}
    paths: set[str] = set()
    for targets in coverage.values():
        if not isinstance(targets, list):
            continue
        for t in targets:
            # Strip ::test_func suffix to get the file path
            paths.add(t.split("::")[0])
    result: dict[str, str] = {}
    for fp in sorted(paths):
        full = target / fp
        if full.is_file():
            result[fp] = _spec_sha(full)
    return result


@main.group()
def fidelity() -> None:
    """Fidelity lock management."""


@fidelity.command("update")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def fidelity_update(target: Path) -> None:
    """Generate or refresh .kanon/fidelity.lock."""
    from kanon._atomic import atomic_write_text

    target = target.resolve()
    specs_dir = target / "docs" / "specs"
    specs = _accepted_or_draft_specs(specs_dir)
    if not specs:
        click.echo("No accepted/draft specs found. Nothing to lock.")
        return

    now = _now_iso()
    entries: dict[str, dict[str, str]] = {}
    fixture_map: dict[str, dict[str, str]] = {}
    for p in specs:
        entries[p.stem] = {"spec_sha": _spec_sha(p), "locked_at": now}
        fshas = _fixture_shas(p, target)
        if fshas:
            fixture_map[p.stem] = fshas

    lock_path = target / ".kanon" / "fidelity.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Generated by kanon fidelity update — do not edit manually.\n"]
    lines.append("lock_version: 1\n")
    lines.append("entries:\n")
    for slug in sorted(entries):
        e = entries[slug]
        lines.append(f"  {slug}:\n")
        lines.append(f"    spec_sha: \"{e['spec_sha']}\"\n")
        if slug in fixture_map:
            lines.append("    fixture_shas:\n")
            for fp in sorted(fixture_map[slug]):
                lines.append(f"      {fp}: \"{fixture_map[slug][fp]}\"\n")
        lines.append(f"    locked_at: \"{e['locked_at']}\"\n")

    atomic_write_text(lock_path, "".join(lines))
    click.echo(f"Wrote {lock_path} with {len(entries)} entries.")


if __name__ == "__main__":
    main()
