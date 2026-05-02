"""Aspect-depth engine helpers extracted from cli.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from kanon import __version__
from kanon._cli_helpers import (
    _OP_SET_DEPTH,
    _check_pending_recovery,
    _check_requires,
)
from kanon._manifest import (
    _aspect_depth_range,
    _expected_files,
    _load_aspect_registry,
    _now_iso,
)
from kanon._scaffold import (
    _assemble_agents_md,
    _build_bundle,
    _config_aspects,
    _merge_agents_md,
    _read_config,
    _write_config,
)


def _validate_aspect_and_depth(
    aspect_name: str, n: int, top: dict[str, Any]
) -> None:
    """Raise ``click.ClickException`` if *aspect_name* is unknown or *n* is out of range."""
    if aspect_name not in top["aspects"]:
        raise click.ClickException(f"Unknown aspect: {aspect_name!r}.")
    min_d, max_d = _aspect_depth_range(aspect_name)
    if not (min_d <= n <= max_d):
        raise click.ClickException(
            f"aspect {aspect_name}: depth {n} outside range [{min_d},{max_d}]."
        )


def _apply_tier_up(target: Path, target_bundle: dict[str, str]) -> int:
    """Write any new-bundle files that don't yet exist; return the count added."""
    from kanon._atomic import atomic_write_text

    added = 0
    for rel, content in sorted(target_bundle.items()):
        dst = target / rel
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dst, content)
        added += 1
    return added


def _apply_tier_down(
    target: Path, old_aspects: dict[str, int], new_aspects: dict[str, int]
) -> list[str]:
    """Return paths that exist on disk but are no longer required at the new depth.

    Pure compute: no file writes, no deletions. Tier-down is non-destructive
    by design (ADR-0008); the caller surfaces the list to the user.
    """
    required = set(_expected_files(new_aspects))
    return [
        rel
        for rel in _expected_files(old_aspects)
        if rel not in required and (target / rel).exists()
    ]


def _rewrite_assembled_views(
    target: Path, new_aspects: dict[str, int], project_name: str
) -> None:
    """Re-merge AGENTS.md. Skips no-op writes.

    Phase A.3: kit.md re-render retired (kit-global files: deleted per ADR-0048).
    """
    from kanon._atomic import atomic_write_text

    new_agents = _assemble_agents_md(new_aspects, project_name)
    agents_path = target / "AGENTS.md"
    if not agents_path.is_file():
        return
    existing_agents = agents_path.read_text(encoding="utf-8")
    merged = _merge_agents_md(existing_agents, new_agents)
    if merged != existing_agents:
        atomic_write_text(target / "AGENTS.md", merged)


def _commit_aspect_meta(
    target: Path,
    kit_version: str,
    aspects_meta: dict[str, dict[str, Any]],
    aspect_name: str,
    depth: int,
    extra_config: dict[str, Any] | None = None,
) -> None:
    """Stamp ``aspects_meta[aspect_name]`` and atomically write config.yaml.

    config.yaml is the commit marker for the multi-file `aspect set-depth`
    sequence (ADR-0024); this is the single callsite that mutates it during
    that operation.

    When *extra_config* is supplied, its keys are merged into the entry's
    ``config:`` block (overwriting prior values for shared keys). This lets
    ``aspect add --config k=v`` populate config keys at enable time without a
    second config write.
    """
    entry = dict(aspects_meta.get(aspect_name, {}))
    entry["depth"] = depth
    entry["enabled_at"] = _now_iso()
    config_block = dict(entry.get("config") or {})
    if extra_config:
        config_block.update(extra_config)
    entry["config"] = config_block
    aspects_meta[aspect_name] = entry
    _write_config(target, kit_version, aspects_meta)


def _set_aspect_depth(
    target: Path,
    aspect_name: str,
    n: int,
    legacy_tier_verb: bool = False,
    extra_config: dict[str, Any] | None = None,
) -> None:
    target = target.resolve()
    config = _read_config(target)
    _check_pending_recovery(target)
    top = _load_aspect_registry(target)
    _validate_aspect_and_depth(aspect_name, n, top)

    aspects = _config_aspects(config)
    proposed = {**aspects, aspect_name: n}
    err = _check_requires(aspect_name, proposed, top)
    if err:
        raise click.ClickException(err)

    kit_version = config.get("kit_version", __version__)
    current = aspects.get(aspect_name, -1)
    aspects_meta = dict(config.get("aspects", {}))

    from kanon._atomic import clear_sentinel, write_sentinel

    # Single sentinel wraps every mutation (file writes + AGENTS.md rewrite +
    # config.yaml). Cleared only on the success path; if any call below
    # raises, the sentinel persists for the next invocation to detect.
    # Phase A.3: kit.md rewrite retired (kit-global files: deleted per ADR-0048).
    write_sentinel(target / ".kanon", _OP_SET_DEPTH)

    if current == n:
        _commit_aspect_meta(
            target, kit_version, aspects_meta, aspect_name, n,
            extra_config=extra_config,
        )
        clear_sentinel(target / ".kanon")
        verb = "Tier" if legacy_tier_verb else f"Aspect {aspect_name} depth"
        click.echo(f"{verb} already {n}. Noop (timestamp refreshed).")
        return

    new_aspects = {**aspects, aspect_name: n}
    target_bundle = _build_bundle(
        new_aspects, {"project_name": target.name, "tier": str(n)}
    )

    if n > current:
        added = _apply_tier_up(target, target_bundle)
        verb = "Tier-up" if legacy_tier_verb else f"Aspect-up ({aspect_name})"
        click.echo(f"{verb} {current} → {n}: added {added} new file(s).")
    else:
        beyond = _apply_tier_down(target, aspects, new_aspects)
        verb = "Tier-down" if legacy_tier_verb else f"Aspect-down ({aspect_name})"
        click.echo(f"{verb} {current} → {n} is non-destructive.")
        if beyond:
            click.echo("The following artifacts are now beyond required for this depth:")
            for rel in beyond:
                click.echo(f"  - {rel}")
            click.echo("You may keep, archive, or delete them as you choose.")

    _rewrite_assembled_views(target, new_aspects, target.name)
    _commit_aspect_meta(
        target, kit_version, aspects_meta, aspect_name, n,
        extra_config=extra_config,
    )
    clear_sentinel(target / ".kanon")

    verb = "Tier" if legacy_tier_verb else f"Aspect {aspect_name} depth"
    click.echo(f"{verb} set to {n} in .kanon/config.yaml.")
