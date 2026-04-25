"""Manifest loaders, aspect queries, and stateless helpers.

This is the dependency root of the kanon package — pure reads from kit
YAML manifests with no side effects except caching.
"""

from __future__ import annotations

import string
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
    return data


def _aspect_depth_range(aspect: str) -> tuple[int, int]:
    top = _load_top_manifest()
    rng = top["aspects"][aspect]["depth-range"]
    return int(rng[0]), int(rng[1])


def _aspect_path(aspect: str) -> Path:
    top = _load_top_manifest()
    return _kit_root() / str(top["aspects"][aspect]["path"])


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
