"""Pure-logic helpers extracted from ``kanon.cli``.

These functions contain validation, parsing, and predicate-checking logic
used by CLI commands but carry no ``@click`` decorators themselves.
"""

from __future__ import annotations

import operator
import re
from pathlib import Path
from typing import Any

import click
import yaml

from kernel._manifest import (
    _CAPABILITY_NAME_RE,
    _capability_suppliers,
    _normalise_aspect_name,
)

# Aspect config-key grammar (INV-aspect-config-key-format).
_CONFIG_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def _value_matches_schema_type(value: Any, expected: str) -> bool:
    """Return True iff a parsed YAML scalar satisfies the schema's ``type:``.

    `bool` is a subtype of `int` in Python; reject `bool` for integer / number
    checks so a stray `coverage_floor=true` does not silently pass.
    """
    if isinstance(value, bool):
        return expected == "boolean"
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int)
    if expected == "number":
        return isinstance(value, (int, float))
    return False


def _parse_config_pair(
    raw: str, schema: dict[str, dict[str, Any]] | None
) -> tuple[str, Any]:
    """Parse one ``key=value`` token for ``aspect set-config`` / ``aspect add --config``.

    Value parsed via :func:`yaml.safe_load` (INV-aspect-config-yaml-scalar-parsing);
    lists and mappings rejected. When *schema* is non-None, the key must appear
    in it and the parsed value's type must satisfy the declared schema ``type:``.
    """
    if "=" not in raw:
        raise click.ClickException(
            f"Invalid config token {raw!r}: expected key=value."
        )
    key, _, value_str = raw.partition("=")
    key = key.strip()
    if not _CONFIG_KEY_RE.match(key):
        raise click.ClickException(
            f"Invalid config key {key!r}: must match {_CONFIG_KEY_RE.pattern}."
        )
    try:
        parsed = yaml.safe_load(value_str)
    except yaml.YAMLError as exc:
        raise click.ClickException(
            f"Invalid config value for {key!r}: {exc}"
        ) from None
    if isinstance(parsed, (list, dict)):
        raise click.ClickException(
            f"Invalid config value for {key!r}: lists and mappings are not "
            f"supported on the CLI; hand-edit .kanon/config.yaml for structured values."
        )
    if schema is not None:
        if key not in schema:
            raise click.ClickException(
                f"Unknown config key {key!r}: not declared in this aspect's "
                f"config-schema. Allowed keys: {sorted(schema.keys())}."
            )
        # `type:` presence is enforced by `_validate_config_schema` at manifest
        # load time; cast to str here so mypy --strict is satisfied.
        expected = str(schema[key]["type"])
        if not _value_matches_schema_type(parsed, expected):
            raise click.ClickException(
                f"Invalid type for config key {key!r}: expected {expected}, "
                f"got {type(parsed).__name__} ({parsed!r})."
            )
    return key, parsed


def _parse_aspects_flag(raw: str, top: dict[str, Any]) -> dict[str, int]:
    """Parse ``--aspects sdd:1,worktrees:2`` into a validated dict.

    Bare aspect names sugar to the ``kanon`` namespace per ADR-0028
    (e.g., ``sdd`` → ``kanon-sdd``). Project-aspects must be referenced by
    their full ``project-<local>`` name.
    """
    result: dict[str, int] = {}
    if not raw.strip():
        return result
    for token in raw.split(","):
        token = token.strip()
        if ":" not in token:
            raise click.ClickException(
                f"Invalid aspect token {token!r}: expected name:depth."
            )
        raw_name, depth_s = token.split(":", 1)
        name = _normalise_aspect_name(raw_name)
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
    return result


_OPS: dict[str, Any] = {
    ">=": operator.ge,
    ">": operator.gt,
    "==": operator.eq,
    "<": operator.lt,
    "<=": operator.le,
}


def _classify_predicate(predicate: str) -> tuple[Any, ...]:
    """Classify a ``requires:`` predicate as a depth predicate or capability presence.

    Returns one of:
        ``("depth", name: str, op: str, depth: int)`` for a 3-token form like ``"sdd >= 1"``,
        ``("capability", name: str)`` for a 1-token form like ``"planning-discipline"``.

    Raises :class:`click.ClickException` on malformed input — designed to fire
    eagerly at manifest-load time so kit-author mistakes fail fast.
    """
    tokens = predicate.split()
    if len(tokens) == 3:
        raw_name, op, depth_s = tokens
        if op not in _OPS:
            raise click.ClickException(
                f"Invalid requires predicate {predicate!r}: unknown operator {op!r}; "
                f"expected one of {sorted(_OPS)}."
            )
        try:
            depth = int(depth_s)
        except ValueError:
            raise click.ClickException(
                f"Invalid requires predicate {predicate!r}: depth {depth_s!r} is not an integer."
            ) from None
        # Bare names sugar to `kanon-` per ADR-0028; namespaced names pass through.
        name = _normalise_aspect_name(raw_name)
        return ("depth", name, op, depth)
    if len(tokens) == 1:
        token = tokens[0]
        if not _CAPABILITY_NAME_RE.match(token):
            raise click.ClickException(
                f"Invalid requires predicate {predicate!r}: 1-token form must be a "
                f"capability name matching {_CAPABILITY_NAME_RE.pattern}."
            )
        return ("capability", token)
    raise click.ClickException(
        f"Invalid requires predicate {predicate!r}: expected either "
        f"'<aspect> <op> <depth>' (3 tokens) or '<capability>' (1 token), "
        f"got {len(tokens)} tokens."
    )


def _check_requires(
    aspect_name: str, proposed_aspects: dict[str, int], top: dict[str, Any]
) -> str | None:
    """Return error message if requires: predicates are unmet, else None.

    Capability-presence predicates (1-token form, per ADR-0026) require a
    supplier at depth ≥ 1. A supplier whose depth is 0 — the opt-out /
    vibe-coding level for an aspect — does not satisfy the predicate;
    depth-0 means the aspect contributes no scaffolding, so it cannot be
    treated as actively providing the capability. See aspect-provides spec
    INV-resolution (Depth-0 corner case).
    """
    for predicate in top["aspects"][aspect_name].get("requires", []):
        classified = _classify_predicate(predicate)
        if classified[0] == "depth":
            _, dep_name, op, dep_depth = classified
            actual = proposed_aspects.get(dep_name, 0)
            if not _OPS[op](actual, dep_depth):
                return (
                    f"Aspect {aspect_name!r} requires {predicate!r}, "
                    f"but {dep_name!r} is at depth {actual}."
                )
        else:  # "capability"
            _, capability = classified
            suppliers = _capability_suppliers(top, capability)
            if not any(proposed_aspects.get(s, 0) >= 1 for s in suppliers):
                kit_suppliers = ", ".join(suppliers) if suppliers else "(none)"
                return (
                    f"Aspect {aspect_name!r} requires capability {capability!r}, "
                    f"but no enabled aspect provides it. "
                    f"Suppliers in this kit: {kit_suppliers}."
                )
    return None


def _check_removal_dependents(
    aspect_name: str, remaining_aspects: dict[str, int], top: dict[str, Any]
) -> str | None:
    """Return error if any remaining aspect depends on the one being removed.

    Handles both depth-predicate references (must name the aspect being removed)
    and capability-presence predicates (the removed aspect must be the *only*
    enabled supplier).
    """
    being_removed_provides = set(
        top["aspects"][aspect_name].get("provides", []) or []
    )
    for name, depth in remaining_aspects.items():
        if depth <= 0:
            continue
        for predicate in top["aspects"][name].get("requires", []):
            classified = _classify_predicate(predicate)
            if classified[0] == "depth":
                if classified[1] == aspect_name:
                    return (
                        f"Cannot remove {aspect_name!r}: "
                        f"aspect {name!r} requires {predicate!r}."
                    )
            else:  # capability
                capability = classified[1]
                if capability not in being_removed_provides:
                    continue
                # Removed aspect supplied this capability. Check whether any
                # other still-enabled aspect also supplies it.
                others = [
                    s for s in _capability_suppliers(top, capability)
                    if s != aspect_name
                ]
                if not any(remaining_aspects.get(s, 0) >= 1 for s in others):
                    return (
                        f"Cannot remove {aspect_name!r}: aspect {name!r} requires "
                        f"capability {capability!r}, which would no longer be provided."
                    )
    return None


# Sentinel operation strings written to .kanon/.pending. Single source of
# truth — every `write_sentinel(...)` callsite uses one of these constants,
# and `_check_pending_recovery` maps them to the correct user-facing
# command form via `_PENDING_OP_TO_COMMAND`.
_OP_INIT = "init"
_OP_UPGRADE = "upgrade"
_OP_SET_DEPTH = "set-depth"
_OP_SET_CONFIG = "set-config"
_OP_ASPECT_REMOVE = "aspect-remove"
_OP_FIDELITY_UPDATE = "fidelity-update"
_OP_GRAPH_RENAME = "graph-rename"

_PENDING_OP_TO_COMMAND: dict[str, str] = {
    _OP_INIT: "kanon init",
    _OP_UPGRADE: "kanon upgrade",
    _OP_SET_DEPTH: "kanon aspect set-depth",
    _OP_SET_CONFIG: "kanon aspect set-config",
    _OP_ASPECT_REMOVE: "kanon aspect remove",
    _OP_FIDELITY_UPDATE: "kanon fidelity update",
    _OP_GRAPH_RENAME: "kanon graph rename",
}


def _check_pending_recovery(target: Path) -> None:
    """If a previous operation was interrupted, recover or warn.

    Per ADR-0030 the recovery model is hybrid:

    - `graph-rename` carries an ops-manifest at `.kanon/graph-rename.ops`
      that captures the per-file rewrite plan. On detecting that sentinel,
      this function calls :func:`kernel._rename.recover_pending_rename` to
      replay the manifest idempotently, clear the sentinel, and emit a
      one-line "Recovered ..." message. No manual re-run required.
    - Other sentinels (init / upgrade / set-depth / set-config /
      aspect-remove / fidelity-update) point at idempotent commands; this
      function emits a warning naming the correct command to re-run via
      `_PENDING_OP_TO_COMMAND`. The user types the suggested command and
      it completes the partial state.
    """
    from kernel._atomic import read_sentinel

    pending = read_sentinel(target / ".kanon")
    if pending is None:
        return
    if pending == _OP_GRAPH_RENAME:
        # Auto-recover graph-rename: the ops-manifest replays idempotently.
        from kernel._rename import recover_pending_rename
        try:
            recovered = recover_pending_rename(target)
        except click.ClickException:
            recovered = False
        if recovered:
            click.echo(
                f"Recovered interrupted '{pending}' operation by replaying "
                f"the ops-manifest.",
                err=True,
            )
            return
        # No manifest on disk (or recovery failed) → fall through to warn.
    rerun = _PENDING_OP_TO_COMMAND.get(pending, f"kanon {pending}")
    click.echo(
        f"Warning: previous '{pending}' operation was interrupted. "
        f"Re-run '{rerun}' to complete it, or run "
        f"'kanon upgrade' to re-render all files.",
        err=True,
    )
