"""Manifest loaders, aspect queries, and stateless helpers.

This is the dependency root of the kanon package — pure reads from kit
YAML manifests with no side effects except caching.
"""

from __future__ import annotations

import importlib.metadata
import os
import re
import string
import sys
import warnings
from collections.abc import Iterator
from datetime import datetime, timezone
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import click
import yaml

import kernel


def _load_yaml(path: Path, expected_type: type = dict) -> Any:
    """Load a YAML file and validate its top-level type.

    Wraps ``yaml.safe_load`` so that parse errors produce a clear
    :class:`click.ClickException` instead of a raw ``yaml.YAMLError``
    traceback.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Invalid YAML in {path}: {exc}") from None
    if not isinstance(data, expected_type):
        type_name = "mapping" if expected_type is dict else expected_type.__name__
        raise click.ClickException(
            f"Malformed {path}: expected a YAML {type_name}."
        )
    return data


# Files the CLI always synthesizes (not sourced from any aspect's files/ tree).
_ALWAYS_SYNTHESIZED = ("AGENTS.md", ".kanon/config.yaml")

# Section names that stay unprefixed in AGENTS.md markers (cross-aspect by design).
_UNPREFIXED_SECTIONS = frozenset({"protocols-index"})

# Marker grammar — line-anchored (whitespace tolerated either side) so that a
# quoted marker inside user prose, an inline-code span, or a fenced code block
# is never mistaken for kit-managed content.
_MARKER_RE = re.compile(
    r"^[ \t]*<!-- kanon:(begin|end):([a-z0-9/_-]+) -->[ \t]*$",
    re.MULTILINE,
)
# A fence opener is a line beginning with 3+ backticks or 3+ tildes (the two
# CommonMark fence delimiters). The closing fence must use the same character.
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*$", re.MULTILINE)


def _fenced_ranges(text: str) -> list[tuple[int, int]]:
    """Byte ranges covered by fenced code blocks.

    A range starts at the opening fence's first character and ends one past the
    closing fence's trailing newline (or end-of-text if unclosed).
    """
    ranges: list[tuple[int, int]] = []
    matches = list(_FENCE_RE.finditer(text))
    i = 0
    while i < len(matches):
        opener = matches[i]
        delim_char = opener.group(1)[0]
        delim_len = len(opener.group(1))
        j = i + 1
        while j < len(matches):
            cand = matches[j]
            if cand.group(1)[0] == delim_char and len(cand.group(1)) >= delim_len:
                break
            j += 1
        if j < len(matches):
            close_end = matches[j].end()
            if close_end < len(text) and text[close_end] == "\n":
                close_end += 1
            ranges.append((opener.start(), close_end))
            i = j + 1
        else:
            ranges.append((opener.start(), len(text)))
            i = len(matches)
    return ranges


def _iter_markers(text: str) -> Iterator[tuple[str, str, int, int]]:
    """Yield ``(kind, section, line_start, line_end)`` for each kanon marker.

    Only matches markers that occupy a line by themselves (leading or trailing
    tabs and spaces tolerated) and are not inside a fenced code block.
    ``line_end`` is one past the marker line's trailing newline (or ``len(text)``).
    """
    fences = _fenced_ranges(text)
    for m in _MARKER_RE.finditer(text):
        if any(s <= m.start() < e for s, e in fences):
            continue
        line_end = m.end() + 1 if m.end() < len(text) and text[m.end()] == "\n" else m.end()
        yield m.group(1), m.group(2), m.start(), line_end


def _find_section_pair(
    text: str, section: str
) -> tuple[int, int, int, int] | None:
    """Find the first well-ordered begin/end pair for *section*.

    Returns ``(begin_line_start, begin_line_end, end_line_start, end_line_end)``
    or ``None`` if the section has no recognised pair (only-begin and only-end
    both return ``None``). End markers without a preceding begin are ignored.
    """
    begin_bounds: tuple[int, int] | None = None
    for kind, sec, ls, le in _iter_markers(text):
        if sec != section:
            continue
        if kind == "begin":
            if begin_bounds is None:
                begin_bounds = (ls, le)
        elif begin_bounds is not None:
            return (begin_bounds[0], begin_bounds[1], ls, le)
    return None


def _kit_root() -> Path:
    return Path(kernel.__file__).parent / "kit"


# --- Manifest loaders ---


# Capability name grammar (INV-aspect-provides-capability-name-format).
# No underscores — keeps the namespace visually distinct from aspect names
# (which permit underscores) and prevents 1-token capability predicates from
# colliding with the depth-predicate parser's whitespace-tokenised form.
_CAPABILITY_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


# Aspect-name grammar (INV-project-aspects-namespace-grammar). Source-namespace
# prefixes: `kanon-` (kit-shipped) and `project-` (consumer-defined). Bare names
# at input surfaces sugar to `kanon-` (see `_normalise_aspect_name`). Other
# namespaces (e.g., `acme-`) are reserved by the grammar but not defined.
_ASPECT_NAME_RE = re.compile(r"^(kanon|project)-[a-z][a-z0-9-]*$")
_BARE_ASPECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_KANON_NAMESPACE = "kanon"
_PROJECT_NAMESPACE = "project"


def _normalise_aspect_name(raw: str) -> str:
    """Return the canonical aspect name for *raw*.

    A prefixed name (matching ``_ASPECT_NAME_RE``) passes through unchanged.
    A bare name (matching ``_BARE_ASPECT_NAME_RE``) sugars to ``kanon-<raw>``
    AND emits a deprecation warning on stderr (Phase A.5; per ADR-0048
    publisher-symmetry — bare-name sugar privileges the ``kanon-`` namespace
    at the CLI surface, breaking the substrate's symmetry between ``kanon-``,
    ``project-``, and ``acme-`` publishers).

    Other inputs raise :class:`click.ClickException`.

    Per ADR-0028 the bare-name shorthand resolves only to the ``kanon`` namespace;
    project-aspects must always be referenced by their full ``project-<local>`` name.
    """
    if _ASPECT_NAME_RE.match(raw):
        return raw
    if _BARE_ASPECT_NAME_RE.match(raw):
        full = f"{_KANON_NAMESPACE}-{raw}"
        # Use sys.stderr.write directly so capsys/capfd both capture cleanly
        # (click.echo's stderr handle is not always captured under pytest).
        sys.stderr.write(
            f"warning: bare aspect name {raw!r} is deprecated; "
            f"use the full name {full!r} instead "
            f"(per ADR-0048 publisher-symmetry).\n"
        )
        return full
    raise click.ClickException(
        f"Invalid aspect name {raw!r}: must match {_ASPECT_NAME_RE.pattern} "
        f"or be a bare name (will sugar to `kanon-<raw>`)."
    )


def _split_aspect_name(name: str) -> tuple[str, str]:
    """Return ``(namespace, local)`` for a canonical aspect name.

    Assumes *name* is already in canonical form (i.e., post-``_normalise_aspect_name``).
    The first dash separates namespace from local; subsequent dashes are part of local.
    """
    namespace, _, local = name.partition("-")
    return namespace, local


def _validate_provides_field(path: Path, name: str, provides: Any) -> None:
    """Validate the optional ``provides:`` block at top-manifest load time."""
    if not isinstance(provides, list):
        raise click.ClickException(
            f"{path}: aspects.{name}.provides must be a list (got {type(provides).__name__})."
        )
    for capability in provides:
        if not isinstance(capability, str):
            raise click.ClickException(
                f"{path}: aspects.{name}.provides entry {capability!r} must be a string."
            )
        if not _CAPABILITY_NAME_RE.match(capability):
            raise click.ClickException(
                f"{path}: aspects.{name}.provides entry {capability!r} is invalid; "
                f"capability names must match {_CAPABILITY_NAME_RE.pattern}."
            )


def _validate_namespace_ownership(slug: str, dist: Any) -> None:
    """Per ADR-0040 §5: an entry-point may only register aspect slugs in its
    distribution's namespace.

    - ``kanon-*`` slugs require dist name ``kanon-aspects`` or ``kanon-kit``
      (the latter is transitional while the top-level pyproject ships both).
    - ``project-*`` slugs are forbidden via entry-points; project-aspects live
      under ``<target>/.kanon/aspects/`` per ADR-0028.
    - ``acme-*`` and unknown namespaces emit a warning (no hard fail until the
      grammar is fully ratified).
    """
    if not _ASPECT_NAME_RE.match(slug):
        # Bare names and unknown namespaces — warn rather than fail.
        warnings.warn(
            f"entry-point aspect slug {slug!r} does not match canonical grammar "
            f"`kanon-<local>` or `project-<local>`; loading anyway.",
            stacklevel=3,
        )
        return
    namespace, _ = _split_aspect_name(slug)
    dist_name = dist.metadata["name"] if dist is not None else None
    if namespace == _KANON_NAMESPACE:
        if dist_name not in ("kanon-aspects", "kanon-kit"):
            raise click.ClickException(
                f"entry-point {slug!r} uses 'kanon-' namespace but is registered "
                f"by distribution {dist_name!r}, not 'kanon-aspects' (ADR-0040)."
            )
    elif namespace == _PROJECT_NAMESPACE:
        raise click.ClickException(
            f"entry-point {slug!r} uses 'project-' namespace; project-aspects "
            f"must be declared in <target>/.kanon/aspects/, not via entry-points "
            f"(ADR-0028, ADR-0040)."
        )


def _load_aspects_from_entry_points() -> dict[str, dict[str, Any]]:
    """Read the seven (or more) aspects registered under group ``kanon.aspects``.

    Each MANIFEST is expected to be a dict containing the registry fields
    (``stability``, ``depth-range``, ``default-depth``, ``description``,
    ``requires``, ``provides``, optional ``suggests``) plus the content fields
    from the per-aspect sub-manifest (``files``, ``depth-N``, etc.).

    The substrate synthesizes a ``path`` field for transitional callers
    (``_scaffold.py`` reads ``entry["path"]``); after Phase A.3 moves aspect
    data under each publisher, the synthesized ``path`` is removed.

    Test overlay: when ``KANON_TEST_OVERLAY_PATH`` is set, the loader skips
    real entry-points and returns aspects discovered under the overlay path
    (used by tests to inject synthetic aspects without touching pip install).
    """
    overlay_path = os.environ.get("KANON_TEST_OVERLAY_PATH")
    if overlay_path:
        return _load_overlay_aspects(Path(overlay_path))

    aspects: dict[str, dict[str, Any]] = {}
    for ep in importlib.metadata.entry_points(group="kanon.aspects"):
        _validate_namespace_ownership(ep.name, ep.dist)
        try:
            manifest = ep.load()
        except Exception as exc:
            raise click.ClickException(
                f"entry-point {ep.name!r}: failed to load MANIFEST — {exc}"
            ) from exc
        if not isinstance(manifest, dict):
            raise click.ClickException(
                f"entry-point {ep.name!r}: MANIFEST must be a dict "
                f"(got {type(manifest).__name__})."
            )
        entry = dict(manifest)
        # Synthesized backward-compat `path` field — A.3 retires this when
        # aspect data moves under the publisher's filesystem location.
        if "path" not in entry and ep.name.startswith(f"{_KANON_NAMESPACE}-"):
            entry["path"] = f"aspects/{ep.name}"
        # Per INV-dialect-grammar-pin-required: every aspect manifest MUST pin
        # `kanon-dialect:`. Validates the pin is recognized; emits stderr
        # deprecation warning if pin matches DEPRECATION_WARNING_BEFORE.
        from kernel._dialects import validate_dialect_pin

        validate_dialect_pin(entry.get("kanon-dialect"), source=ep.name)
        # Validate required registry fields surface from the LOADER MANIFEST.
        for field in ("stability", "depth-range", "default-depth"):
            if field not in entry:
                raise click.ClickException(
                    f"entry-point {ep.name!r}: MANIFEST missing required "
                    f"registry field {field!r}."
                )
        if entry["stability"] not in {"experimental", "stable", "deprecated"}:
            raise click.ClickException(
                f"entry-point {ep.name!r}: invalid stability "
                f"{entry['stability']!r}."
            )
        rng = entry["depth-range"]
        if not (isinstance(rng, list) and len(rng) == 2):
            raise click.ClickException(
                f"entry-point {ep.name!r}: depth-range must be [min, max]."
            )
        if "provides" in entry:
            _validate_provides_field(
                Path(f"<entry-point {ep.name}>"), ep.name, entry["provides"]
            )
        if ep.name in aspects:
            raise click.ClickException(
                f"entry-point {ep.name!r}: duplicate registration."
            )
        aspects[ep.name] = entry
    return aspects


def _load_overlay_aspects(overlay_root: Path) -> dict[str, dict[str, Any]]:
    """Read aspects from a test-overlay directory.

    Each subdirectory of *overlay_root* whose name matches the canonical aspect
    grammar carries a ``manifest.yaml`` with the unified registry+content shape.
    Used by tests to substitute the entry-point-sourced registry without
    requiring pip-installed wheels.
    """
    aspects: dict[str, dict[str, Any]] = {}
    if not overlay_root.is_dir():
        return aspects
    for sub in sorted(overlay_root.iterdir()):
        if not sub.is_dir():
            continue
        name = sub.name
        if not _ASPECT_NAME_RE.match(name):
            continue
        manifest_path = sub / "manifest.yaml"
        if not manifest_path.is_file():
            continue
        manifest = _load_yaml(manifest_path)
        entry = dict(manifest)
        if "path" not in entry:
            entry["path"] = f"aspects/{name}"
        aspects[name] = entry
    return aspects


@lru_cache(maxsize=1)
def _load_top_manifest() -> dict[str, Any]:
    """Load the substrate's top-level manifest.

    Phase A.2.2: ``aspects:`` are sourced from Python entry-points (group
    ``kanon.aspects``) per ADR-0040, NOT from the kit YAML's ``aspects:``
    block. The kit YAML at ``kernel/kit/manifest.yaml`` is still read for
    kit-globals (``defaults:``, ``files:``); Phase A.3 retires those.
    """
    path = _kit_root() / "manifest.yaml"
    yaml_data: dict[str, Any] = _load_yaml(path) if path.is_file() else {}
    yaml_data["aspects"] = _load_aspects_from_entry_points()
    return yaml_data


def _aspect_provides(aspect: str) -> list[str]:
    """Return the capabilities declared by *aspect* (empty list when none)."""
    entry = _aspect_entry(aspect)
    if entry is None:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    return list(entry.get("provides", []) or [])


def _capability_suppliers(top: dict[str, Any], capability: str) -> list[str]:
    """Return the aspect names whose ``provides:`` includes *capability*.

    Iterates the supplied ``top`` registry. Callers that want kit + project
    coverage should pass the unified registry from :func:`_load_aspect_registry`.
    For pure-kit queries, callers may pass ``_load_top_manifest()`` directly.
    """
    return sorted(
        name
        for name, entry in top["aspects"].items()
        if capability in (entry.get("provides", []) or [])
    )


# --- Project-aspect discovery + active overlay (ADR-0028) ---


# Module-level overlay set by `_load_aspect_registry(target)` at CLI command
# entry. Existing `_aspect_*` helpers consult this transparently — see
# `_aspect_entry`. Tests reset via `_set_project_aspects_overlay(None)`.
_PROJECT_ASPECTS_OVERLAY: dict[str, dict[str, Any]] | None = None


def _set_project_aspects_overlay(
    overlay: dict[str, dict[str, Any]] | None,
) -> None:
    """Set or clear the active project-aspect overlay.

    Called by every CLI command at entry that operates against a target (via
    :func:`_load_aspect_registry`). Invalidates the cached sub-manifest reads
    so a different target's project-aspects don't return stale data.
    """
    global _PROJECT_ASPECTS_OVERLAY
    _PROJECT_ASPECTS_OVERLAY = overlay
    _load_aspect_manifest.cache_clear()


def _aspect_entry(aspect: str) -> dict[str, Any] | None:
    """Find the registry entry for *aspect*, consulting kit + active overlay.

    Returns the entry dict or ``None`` if no source registers *aspect*.
    Project entries carry ``_source`` (absolute path); kit entries carry
    only ``path`` (relative to ``_kit_root()``).
    """
    top = _load_top_manifest()
    if aspect in top["aspects"]:
        kit_entry: dict[str, Any] = top["aspects"][aspect]
        return kit_entry
    if _PROJECT_ASPECTS_OVERLAY is not None and aspect in _PROJECT_ASPECTS_OVERLAY:
        return _PROJECT_ASPECTS_OVERLAY[aspect]
    return None


def _all_known_aspects() -> dict[str, dict[str, Any]]:
    """Union of kit + active project-overlay aspect entries.

    Used by helpers that need to iterate over every registered aspect (e.g.,
    cross-source capability lookups). Project entries are appended after kit
    entries; the namespace grammar (ADR-0028) prevents key collisions.
    """
    top = _load_top_manifest()
    if _PROJECT_ASPECTS_OVERLAY is None:
        return dict(top["aspects"])
    return {**top["aspects"], **_PROJECT_ASPECTS_OVERLAY}


def _discover_project_aspects(target: Path) -> dict[str, dict[str, Any]]:
    """Walk ``<target>/.kanon/aspects/`` and return registry entries for each
    project-aspect found.

    Each entry includes ``_source`` set to the aspect's absolute directory
    path. Per ADR-0028 the consumer-side ``aspects/`` may only declare aspects
    in the ``project-`` namespace; ``kanon-`` (or any other prefix) directories
    under that path are rejected at load time with a single-line error naming
    the offending path and the namespace-ownership rule.
    """
    aspects_dir = target / ".kanon" / "aspects"
    if not aspects_dir.is_dir():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for sub in sorted(aspects_dir.iterdir()):
        if not sub.is_dir():
            continue
        name = sub.name
        if name.startswith("."):
            continue
        # Namespace ownership (ADR-0028): only `project-<local>` is allowed.
        if not _ASPECT_NAME_RE.match(name) or not name.startswith(
            f"{_PROJECT_NAMESPACE}-"
        ):
            raise click.ClickException(
                f"Project-aspect directory '{sub.relative_to(target)}': aspect "
                f"name {name!r} must match `project-[a-z][a-z0-9-]*` "
                f"(ADR-0028 namespace ownership)."
            )
        manifest_path = sub / "manifest.yaml"
        if not manifest_path.is_file():
            raise click.ClickException(
                f"Project-aspect {name!r}: missing manifest.yaml at "
                f"'{manifest_path.relative_to(target)}'."
            )
        full = _load_yaml(manifest_path)
        for field in ("stability", "depth-range", "default-depth"):
            if field not in full:
                raise click.ClickException(
                    f"Project-aspect {name!r}: missing required field {field!r} "
                    f"in '{manifest_path.relative_to(target)}'."
                )
        if full["stability"] not in {"experimental", "stable", "deprecated"}:
            raise click.ClickException(
                f"Project-aspect {name!r}: invalid stability "
                f"{full['stability']!r} in '{manifest_path.relative_to(target)}'."
            )
        rng = full["depth-range"]
        if not (isinstance(rng, list) and len(rng) == 2):
            raise click.ClickException(
                f"Project-aspect {name!r}.depth-range must be [min, max] in "
                f"'{manifest_path.relative_to(target)}'."
            )
        if "provides" in full:
            _validate_provides_field(manifest_path, name, full["provides"])
        entry: dict[str, Any] = {
            "stability": full["stability"],
            "depth-range": full["depth-range"],
            "default-depth": full["default-depth"],
            "requires": full.get("requires", []) or [],
            "_source": str(sub),
            "path": str(sub),  # kit-shape compat for any path-only consumer
        }
        if "provides" in full:
            entry["provides"] = full["provides"]
        if "suggests" in full:
            entry["suggests"] = full["suggests"]
        result[name] = entry
    return result


def _load_aspect_registry(target: Path | None = None) -> dict[str, Any]:
    """Return the unified aspect registry (kit + project) for *target*.

    Mirrors the shape of :func:`_load_top_manifest` (``{aspects: {...}, ...}``)
    while side-effecting the active project-aspects overlay so downstream
    ``_aspect_*`` helpers see project-aspects without needing to thread
    *target* explicitly. Calling with ``target=None`` clears the overlay and
    returns the kit-only registry.

    Each entry in the returned ``aspects`` mapping carries ``_source`` (the
    absolute path to the aspect's directory) so collision detection and
    sub-manifest resolution work source-agnostically.
    """
    top = _load_top_manifest()
    kit_aspects: dict[str, dict[str, Any]] = {}
    for name, entry in top["aspects"].items():
        e = dict(entry)
        # Per substrate-content-move sub-plan: kanon-* aspect data lives at
        # src/kanon_reference/aspects/<slug>/ (per ADR-0044 substrate-independence;
        # substrate ships zero aspect data). Other slugs (acme-*) come from the
        # entry-point publisher's distribution root via importlib.metadata.
        if name.startswith(f"{_KANON_NAMESPACE}-"):
            try:
                import kanon_reference

                e["_source"] = str(
                    Path(kanon_reference.__file__).parent / "aspects" / name.replace("-", "_")
                )
            except ImportError:
                # kanon_reference not installed — fall back to legacy kit
                # location for transitional consumers (will be empty after
                # content move; substrate-independence gate enforces).
                e["_source"] = str(_kit_root() / e["path"])
        else:
            e["_source"] = str(_kit_root() / e["path"])
        kit_aspects[name] = e
    if target is None:
        _set_project_aspects_overlay(None)
        unified_top = dict(top)
        unified_top["aspects"] = kit_aspects
        return unified_top
    project = _discover_project_aspects(target)
    collisions = sorted(set(kit_aspects) & set(project))
    if collisions:
        raise click.ClickException(
            f"Aspect-name collision between kit and project sources: "
            f"{collisions}. Project-aspects must use the `project-` namespace "
            f"per ADR-0028."
        )
    _set_project_aspects_overlay(project)
    unified_top = dict(top)
    unified_top["aspects"] = {**kit_aspects, **project}
    return unified_top


# Recognised value types in an aspect's `config-schema:`. Anything else is
# rejected at sub-manifest load time.
_CONFIG_SCHEMA_TYPES = frozenset({"string", "integer", "boolean", "number"})
# Permitted descriptor fields under each `config-schema.<key>` entry.
_CONFIG_SCHEMA_FIELDS = frozenset({"type", "default", "description"})


def _validate_config_schema(sub_path: Path, schema: Any) -> None:
    """Validate the optional ``config-schema:`` block at sub-manifest load time."""
    if not isinstance(schema, dict):
        raise click.ClickException(
            f"{sub_path}: 'config-schema' must be a mapping of key → descriptor."
        )
    for key, descriptor in schema.items():
        if not isinstance(key, str) or not key:
            raise click.ClickException(
                f"{sub_path}: config-schema key must be a non-empty string, got {key!r}."
            )
        if not isinstance(descriptor, dict):
            raise click.ClickException(
                f"{sub_path}: config-schema.{key} must be a mapping (got {type(descriptor).__name__})."
            )
        if "type" not in descriptor:
            raise click.ClickException(
                f"{sub_path}: config-schema.{key} is missing required field 'type'."
            )
        type_val = descriptor["type"]
        if type_val not in _CONFIG_SCHEMA_TYPES:
            raise click.ClickException(
                f"{sub_path}: config-schema.{key}.type {type_val!r} is invalid; "
                f"expected one of {sorted(_CONFIG_SCHEMA_TYPES)}."
            )
        unknown = set(descriptor) - _CONFIG_SCHEMA_FIELDS
        if unknown:
            raise click.ClickException(
                f"{sub_path}: config-schema.{key} has unknown field(s) {sorted(unknown)!r}; "
                f"only {sorted(_CONFIG_SCHEMA_FIELDS)} are permitted."
            )


# Module-path grammar for `validators:` entries (ADR-0028 / project-aspects
# spec INV-7). A validator is an importable Python module whose dotted path
# appears as a YAML scalar — e.g., `my_pkg.checks.greenlight`. Each segment
# follows Python identifier rules; the joining `.` separators matter.
_VALIDATOR_MODULE_PATH_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$"
)


def _validate_validators_field(sub_path: Path, validators: Any) -> None:
    """Validate the optional ``validators:`` block at sub-manifest load time.

    The field is a list of dotted module paths; each module is expected to
    expose a callable ``check(target, errors, warnings) -> None`` (verified at
    invocation time, not here — schema validation is path-grammar only).
    """
    if not isinstance(validators, list):
        raise click.ClickException(
            f"{sub_path}: 'validators' must be a list (got "
            f"{type(validators).__name__})."
        )
    for entry in validators:
        if not isinstance(entry, str):
            raise click.ClickException(
                f"{sub_path}: validators entry {entry!r} must be a string "
                f"(dotted module path)."
            )
        if not _VALIDATOR_MODULE_PATH_RE.match(entry):
            raise click.ClickException(
                f"{sub_path}: validators entry {entry!r} is not a valid "
                f"dotted module path (expected `pkg.mod[.sub]`)."
            )


@cache
def _load_aspect_manifest(aspect: str) -> dict[str, Any]:
    """Load the aspect's per-aspect ``manifest.yaml``.

    For kit-aspects the file lives at ``kernel/kit/aspects/<aspect>/manifest.yaml``.
    For project-aspects the file lives at ``<target>/.kanon/aspects/<aspect>/manifest.yaml``
    (resolved via the active overlay set by :func:`_load_aspect_registry`).
    """
    entry = _aspect_entry(aspect)
    if entry is None:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    sub_path = _aspect_path(aspect) / "manifest.yaml"
    if not sub_path.is_file():
        raise click.ClickException(f"aspect sub-manifest missing: {sub_path}")
    data: dict[str, Any] = _load_yaml(sub_path)
    min_d, max_d = _aspect_depth_range(aspect)
    for d in range(min_d, max_d + 1):
        key = f"depth-{d}"
        if key not in data:
            raise click.ClickException(f"{sub_path}: missing {key!r} entry.")
        if not isinstance(data[key], dict):
            raise click.ClickException(f"{sub_path}: {key} must be a mapping.")
    if "config-schema" in data:
        _validate_config_schema(sub_path, data["config-schema"])
    if "validators" in data:
        _validate_validators_field(sub_path, data["validators"])
    return data


def _aspect_validators(aspect: str) -> list[str]:
    """Return the dotted module paths declared under ``validators:`` (project-
    aspects spec INV-7). Empty list when none.
    """
    sub = _load_aspect_manifest(aspect)
    raw = sub.get("validators") or []
    return [str(v) for v in raw if isinstance(v, str)]


def _aspect_config_schema(aspect: str) -> dict[str, dict[str, Any]] | None:
    """Return the aspect's ``config-schema:`` mapping, or None when none is declared."""
    sub = _load_aspect_manifest(aspect)
    schema = sub.get("config-schema")
    if schema is None:
        return None
    return dict(schema)


def _aspect_depth_range(aspect: str) -> tuple[int, int]:
    entry = _aspect_entry(aspect)
    if entry is None:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    rng = entry["depth-range"]
    return int(rng[0]), int(rng[1])


def _aspect_path(aspect: str) -> Path:
    """Return the on-disk directory holding *aspect*'s sub-manifest, files, etc.

    Project-aspect entries (set by :func:`_discover_project_aspects`) carry an
    absolute ``_source``; kit-aspect entries set ``_source`` via
    :func:`_load_aspect_registry`. When neither is available (callers that
    look up via :func:`_aspect_entry` without first calling the registry),
    the fallback synthesizes the path from kanon_reference for kanon-* aspects.

    Per ADR-0044 substrate-independence: the substrate (kanon-core) MUST
    NOT silently fall back to a dead legacy path when kanon_reference is
    absent. After Phase A.7 (substrate-content-move), kernel/kit/aspects/
    no longer exists for kanon-* aspects; returning that path would resolve
    to a non-existent directory and downstream callers (_load_aspect_manifest,
    file readers, scaffolders) would fail with confusing FileNotFoundError
    chains. Fail fast with a helpful diagnostic instead.
    """
    entry = _aspect_entry(aspect)
    if entry is None:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    if "_source" in entry:
        return Path(entry["_source"])
    if aspect.startswith(f"{_KANON_NAMESPACE}-"):
        try:
            import kanon_reference

            return Path(kanon_reference.__file__).parent / "aspects" / aspect.replace("-", "_")
        except ImportError as exc:
            raise click.ClickException(
                f"Cannot resolve aspect {aspect!r}: kanon_reference is not "
                f"installed. kanon-core ships no kanon-* aspect data per "
                f"ADR-0044 substrate-independence; install kanon-kit (which "
                f"depends on both kanon-core and kanon-aspects) or "
                f"install kanon-aspects directly. ({exc})"
            ) from exc
    return _kit_root() / str(entry["path"])


def _aspect_items(aspect: str, depth: int, key: str) -> list[str]:
    """Return the union of *key* entries from depth-0 through *depth*."""
    sub = _load_aspect_manifest(aspect)
    min_d, _ = _aspect_depth_range(aspect)
    items: list[str] = []
    for d in range(min_d, depth + 1):
        items.extend(sub.get(f"depth-{d}", {}).get(key, []) or [])
    return items


def _aspect_files(aspect: str, depth: int) -> list[str]:
    sub = _load_aspect_manifest(aspect)
    base = list(sub.get("files", []) or [])
    base.extend(_aspect_items(aspect, depth, "files"))
    return base


def _aspect_protocols(aspect: str, depth: int) -> list[str]:
    return _aspect_items(aspect, depth, "protocols")


def _aspect_sections(aspect: str, depth: int) -> list[str]:
    return _aspect_items(aspect, depth, "sections")


def _aspect_depth_validators(aspect: str, depth: int) -> list[str]:
    """Return depth-gated validator module paths (union of depth-0..depth)."""
    return _aspect_items(aspect, depth, "validators")


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


# Phase A.3: _default_aspects() retired. Per ADR-0048 de-opinionation, the
# kit-global defaults: block was deleted from kernel/kit/manifest.yaml;
# `kanon init` with no flags now scaffolds an empty project.


def _expected_files(aspects: dict[str, int]) -> list[str]:
    """Return the full path list a project with these aspects must have."""
    paths: list[str] = list(_ALWAYS_SYNTHESIZED)
    # Phase A.3: kit-global files: retired per ADR-0048.
    for aspect, depth in aspects.items():
        paths.extend(_aspect_files(aspect, depth))
        paths.extend(
            f".kanon/protocols/{aspect}/{p}" for p in _aspect_protocols(aspect, depth)
        )
    return paths


# --- Small helpers ---


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


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
