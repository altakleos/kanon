"""Manifest loaders, aspect queries, and stateless helpers.

This is the dependency root of the kanon package — pure reads from kit
YAML manifests with no side effects except caching.
"""

from __future__ import annotations

import re
import string
from collections.abc import Iterator
from datetime import datetime, timezone
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import click
import yaml

import kanon


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
    return Path(kanon.__file__).parent / "kit"


# --- Manifest loaders ---


@lru_cache(maxsize=1)
def _load_top_manifest() -> dict[str, Any]:
    """Load the aspect registry at src/kanon/kit/manifest.yaml."""
    path = _kit_root() / "manifest.yaml"
    if not path.is_file():
        raise click.ClickException(f"kit manifest missing: {path}")
    data: dict[str, Any] = _load_yaml(path)
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


@cache
def _load_aspect_manifest(aspect: str) -> dict[str, Any]:
    """Load src/kanon/kit/aspects/<aspect>/manifest.yaml."""
    top = _load_top_manifest()
    if aspect not in top["aspects"]:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    sub_path = _kit_root() / top["aspects"][aspect]["path"] / "manifest.yaml"
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
    return data


def _aspect_config_schema(aspect: str) -> dict[str, dict[str, Any]] | None:
    """Return the aspect's ``config-schema:`` mapping, or None when none is declared."""
    sub = _load_aspect_manifest(aspect)
    schema = sub.get("config-schema")
    if schema is None:
        return None
    return dict(schema)


def _aspect_depth_range(aspect: str) -> tuple[int, int]:
    top = _load_top_manifest()
    rng = top["aspects"][aspect]["depth-range"]
    return int(rng[0]), int(rng[1])


def _aspect_path(aspect: str) -> Path:
    top = _load_top_manifest()
    return _kit_root() / str(top["aspects"][aspect]["path"])


def _aspect_items(aspect: str, depth: int, key: str) -> list[str]:
    """Return the union of *key* entries from depth-0 through *depth*."""
    sub = _load_aspect_manifest(aspect)
    min_d, _ = _aspect_depth_range(aspect)
    items: list[str] = []
    for d in range(min_d, depth + 1):
        items.extend(sub.get(f"depth-{d}", {}).get(key, []) or [])
    return items


def _aspect_files(aspect: str, depth: int) -> list[str]:
    return _aspect_items(aspect, depth, "files")


def _aspect_protocols(aspect: str, depth: int) -> list[str]:
    return _aspect_items(aspect, depth, "protocols")


def _aspect_sections(aspect: str, depth: int) -> list[str]:
    return _aspect_items(aspect, depth, "sections")


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


def _default_aspects() -> dict[str, int]:
    """Read the ``defaults:`` key from the top manifest and return {name: default-depth}."""
    top = _load_top_manifest()
    names: list[str] = top.get("defaults", [])
    result: dict[str, int] = {}
    for name in names:
        if name not in top["aspects"]:
            raise click.ClickException(
                f"defaults: lists unknown aspect {name!r}."
            )
        result[name] = int(top["aspects"][name]["default-depth"])
    return result


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
