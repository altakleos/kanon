"""Scaffold assembly, config I/O, and file-tree writing.

Imports from ``_manifest`` (the dependency root) and provides the
content-construction layer that CLI commands orchestrate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml

from kanon_core import __version__
from kanon_core._manifest import (
    _ASPECT_NAME_RE,
    _BARE_ASPECT_NAME_RE,
    _UNPREFIXED_SECTIONS,
    _all_aspect_sections,
    _all_known_aspects,
    _aspect_depth_range,
    _aspect_files,
    _aspect_path,
    _aspect_protocols,
    _find_section_pair,
    _iter_markers,
    _kit_root,
    _load_aspect_manifest,
    _load_top_manifest,
    _load_yaml,
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
    data = _load_yaml(config_path)
    return _migrate_legacy_config(data)


# Per ADR-0045 Phase 0.5 + ADR-0041: every kanon-managed config carries a
# schema-version + dialect pin. New configs (kanon init) get these by default;
# config-mutating verbs (kanon aspect add/remove/set-config/set-depth, upgrade)
# preserve them across writes via _extras_from_config below.
_DEFAULT_V4_EXTRAS: dict[str, Any] = {
    "schema-version": 4,
    "kanon-dialect": "2026-05-01",
}

_CANONICAL_CONFIG_KEYS: frozenset[str] = frozenset({"kit_version", "aspects"})


def _extras_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return non-canonical top-level config keys for round-trip preservation.

    Used by config-mutating verbs to round-trip schema-version, kanon-dialect,
    provenance, preflight-stages, and any other publisher-added top-level keys
    through _write_config without clobbering them.
    """
    return {k: v for k, v in config.items() if k not in _CANONICAL_CONFIG_KEYS}


# Legacy v1 (tier:) and v2 (bare aspects:) → v3 (namespaced aspects:) migration.
# v1: `tier: N` (kanon < 0.2)
# v2: `aspects: {sdd: {...}, worktrees: {...}}` (kanon 0.2.x; bare aspect names)
# v3: `aspects: {kanon-sdd: {...}, kanon-worktrees: {...}}` (kanon 0.3+; namespaced
#     per ADR-0028, with `project-<local>` reserved for project-aspects)
def _migrate_legacy_config(config: dict[str, Any]) -> dict[str, Any]:
    """One-way v1/v2 → v3 transformer. Idempotent if already v3.

    v1 (`tier: N`) → v3 (`aspects: {kanon-sdd: {depth: N, ...}}`).
    v2 (`aspects: {sdd: {...}}`) → v3 (`aspects: {kanon-sdd: {...}}`).
    v3 (already-namespaced) → no-op.
    """
    # v1 → v3: synthesise `aspects:` from the legacy `tier:` field.
    if "aspects" not in config:
        if "tier" not in config:
            return config
        return {
            "kit_version": config.get("kit_version", __version__),
            "aspects": {
                "kanon-sdd": {
                    "depth": int(config["tier"]),
                    "enabled_at": config.get("tier_set_at") or _now_iso(),
                    "config": {},
                }
            },
        }
    # v2 → v3: rewrite bare aspect keys to the `kanon-<local>` form. Idempotent
    # for already-namespaced keys (which match `_ASPECT_NAME_RE`).
    aspects = config["aspects"]
    if not isinstance(aspects, dict):
        raise click.ClickException(
            "Malformed .kanon/config.yaml: 'aspects' must be a mapping, "
            f"got {type(aspects).__name__}. Hand-edit the file to fix."
        )
    bare_keys = [
        name for name in aspects
        if isinstance(name, str)
        and not _ASPECT_NAME_RE.match(name)
        and _BARE_ASPECT_NAME_RE.match(name)
    ]
    if not bare_keys:
        return config
    # Mixed-state defence (project-aspects spec INV-5 / plan T17): a config
    # with both `<local>` and `kanon-<local>` keys is ambiguous — silently
    # auto-migrating the bare key would overwrite the namespaced entry. Hard-
    # fail with a message that names every collision and asks the user to
    # deduplicate manually before re-running upgrade.
    collisions = sorted(
        bare for bare in bare_keys if f"kanon-{bare}" in aspects
    )
    if collisions:
        details = ", ".join(f"`{c}` and `kanon-{c}`" for c in collisions)
        raise click.ClickException(
            f"Cannot migrate .kanon/config.yaml: both bare and namespaced "
            f"aspect keys present for the same local name ({details}). "
            f"Hand-edit the config to keep only the `kanon-<local>` form, "
            f"then re-run `kanon upgrade`."
        )
    new_aspects: dict[str, Any] = {}
    for name, entry in aspects.items():
        if isinstance(name, str) and _BARE_ASPECT_NAME_RE.match(name) \
                and not _ASPECT_NAME_RE.match(name):
            new_aspects[f"kanon-{name}"] = entry
        else:
            new_aspects[name] = entry
    out = dict(config)
    out["aspects"] = new_aspects
    return out


_RETIRED_TESTING_CONFIG_KEYS = (
    "test_cmd",
    "lint_cmd",
    "typecheck_cmd",
    "format_cmd",
    "coverage_floor",
)


def _apply_v3_to_v4_migration(
    config: dict[str, Any],
    target: Path,
) -> tuple[dict[str, Any], list[str], list[Path]]:
    """One-way v3 → v4 transformer + cleanup. Idempotent if already v4.

    Promotes a v3-shape config (`kit_version` + `aspects:` namespaced) to v4
    by adding the v4 fields (`schema-version: 4`, `kanon-dialect`,
    `provenance:`), strips deprecated config keys (Phase A.4 retired
    kanon-testing keys), and identifies stale `.kanon/protocols/<aspect>/`
    directories whose aspect is no longer in the active set.

    The stale-protocols directories are returned as a list of paths; the
    caller decides whether to delete them (so dry-run callers can preview).

    Returns:
        (new_config, change_descriptions, stale_protocols_dirs)

    Raises:
        click.ClickException for v5+ configs (forward-version guard).
    """
    schema_version = config.get("schema-version")

    # Forward-version guard: refuse v5+ rather than silently mangling.
    if schema_version is not None:
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise click.ClickException(
                f"Unsupported schema-version type: {schema_version!r} "
                f"(got {type(schema_version).__name__}; must be an integer "
                f"like `schema-version: 4`)."
            )
        if schema_version > 4:
            raise click.ClickException(
                f"Unknown schema-version: {schema_version}. This kanon only knows how "
                f"to handle v3 → v4. To handle v{schema_version}, install a newer "
                f"kanon-core."
            )

    changes: list[str] = []
    out = dict(config)

    # Promote to v4 if not already.
    if "schema-version" not in out:
        out["schema-version"] = 4
        changes.append("added schema-version: 4")
    if "kanon-dialect" not in out:
        out["kanon-dialect"] = "2026-05-01"
        changes.append('added kanon-dialect: "2026-05-01"')
    if "provenance" not in out:
        out["provenance"] = [
            {
                "recipe": "manual-migration",
                "publisher": "kanon-migrate",
                "recipe-version": "1.0",
                "applied_at": _now_iso(),
            }
        ]
        changes.append("added provenance entry")

    # Strip retired kanon-testing config keys (Phase A.4 deletion).
    aspects = out.get("aspects") or {}
    if isinstance(aspects, dict):
        testing_entry = aspects.get("kanon-testing")
        if isinstance(testing_entry, dict):
            testing_config = testing_entry.get("config") or {}
            if isinstance(testing_config, dict):
                stripped = []
                for key in _RETIRED_TESTING_CONFIG_KEYS:
                    if key in testing_config:
                        del testing_config[key]
                        stripped.append(key)
                if stripped:
                    changes.append(
                        f"stripped retired kanon-testing config keys: {stripped}"
                    )
                testing_entry["config"] = testing_config

    # Reorder: v4 fields at top.
    reordered: dict[str, Any] = {}
    for key in ("schema-version", "kanon-dialect", "provenance"):
        if key in out:
            reordered[key] = out[key]
    for key, value in out.items():
        if key not in reordered:
            reordered[key] = value

    # Detect stale .kanon/protocols/<aspect>/ dirs.
    stale_dirs: list[Path] = []
    enabled_aspects: set[str] = set()
    aspects_block = reordered.get("aspects")
    if isinstance(aspects_block, dict):
        enabled_aspects = {name for name in aspects_block if isinstance(name, str)}
    protocols_dir = target / ".kanon" / "protocols"
    if protocols_dir.is_dir():
        for entry in sorted(protocols_dir.iterdir()):
            if entry.is_dir() and entry.name not in enabled_aspects:
                stale_dirs.append(entry)
                changes.append(
                    f"would remove stale protocols dir: .kanon/protocols/{entry.name}/"
                )

    return reordered, changes, stale_dirs


def _config_aspects(config: dict[str, Any]) -> dict[str, int]:
    """Extract {aspect_name: depth} from a v2 config."""
    aspects = config.get("aspects", {})
    result: dict[str, int] = {}
    for name, entry in aspects.items():
        if not isinstance(entry, dict) or "depth" not in entry:
            raise click.ClickException(
                f"Malformed .kanon/config.yaml: aspect {name!r} must be a "
                f"mapping with a 'depth' key."
            )
        try:
            result[name] = int(entry["depth"])
        except (ValueError, TypeError) as exc:
            raise click.ClickException(
                f"Malformed .kanon/config.yaml: aspect {name!r} has "
                f"non-integer depth {entry['depth']!r}."
            ) from exc
    return result


def _ensure_within(path: Path, base: Path) -> Path:
    """Resolve *path* and verify it stays inside *base*."""
    resolved = path.resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise click.ClickException(f"Path escapes target directory: {path}")
    return resolved


def _write_config(
    target: Path,
    kit_version: str,
    aspects_with_meta: dict[str, dict[str, Any]],
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a v4 .kanon/config.yaml atomically.

    Per ADR-0054 + the `migrate-expanded` plan (2026-05-04): new configs
    ship in v4 shape (`schema-version: 4` + `kanon-dialect` + `provenance`
    at the top), with `kit_version` + `aspects:` retained for the v3
    reader carve-out. Extras passed in win over defaults so callers can
    override any field.
    """
    from kanon_core._atomic import atomic_write_text

    config_dir = _ensure_within(target / ".kanon", target)
    config_dir.mkdir(parents=True, exist_ok=True)
    extra = extra or {}
    payload: dict[str, Any] = {}
    # v4 fields at the top of the file.
    payload["schema-version"] = extra.get("schema-version", 4)
    payload["kanon-dialect"] = extra.get("kanon-dialect", "2026-05-01")
    payload["provenance"] = extra.get(
        "provenance",
        [
            {
                "recipe": "manual-migration",
                "publisher": "kanon-migrate",
                "recipe-version": "1.0",
                "applied_at": _now_iso(),
            }
        ],
    )
    # v3 fields (kit_version + aspects) — kept for backward-readability.
    payload["kit_version"] = kit_version
    payload["aspects"] = aspects_with_meta
    # Any other extras (publisher fields, etc.) preserved verbatim.
    canonical = {"schema-version", "kanon-dialect", "provenance", "kit_version", "aspects"}
    payload.update({k: v for k, v in extra.items() if k not in canonical})
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
    result: list[dict[str, Any]] = _load_yaml(path, expected_type=list)
    return result


def _render_shims(only: set[str] | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in _load_harnesses():
        if only is not None and entry["name"] not in only:
            continue
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


def _detect_harnesses(target: Path) -> set[str]:
    """Return harness names whose config directories already exist in *target*."""
    found: set[str] = set()
    for entry in _load_harnesses():
        shim_path = Path(entry["path"])
        # For root-level files (CLAUDE.md), skip — they don't indicate harness usage.
        if shim_path.parent == Path("."):
            continue
        # Check the top-level dotdir (first component of the shim path).
        top_dir = shim_path.parts[0]
        if (target / top_dir).is_dir():
            found.add(entry["name"])
    return found


# --- Bundle construction ---


def _build_bundle(
    aspects: dict[str, int], context: dict[str, str]
) -> dict[str, str]:
    """{relative_path: content} for every file scaffolded for these aspects.

    Excludes always-synthesized files (AGENTS.md, .kanon/config.yaml).
    Kit-global files (top-level manifest ``files:``) are included first,
    then per-aspect files and protocols.

    Raises a ``ClickException`` when two enabled aspects (kit or project, any
    combination) declare the same consumer-relative ``files/`` path. Per
    ``docs/specs/project-aspects.md`` INV-6 / ADR-0028 ownership exclusivity:
    project-aspects can introduce file-path collisions the kit's CI cannot see,
    so the runtime guard is load-bearing here. Protocol paths are inherently
    namespaced (``.kanon/protocols/<aspect>/...``), so collisions across
    aspects are structurally impossible and not tracked.
    """
    bundle: dict[str, str] = {}
    file_owners: dict[str, str] = {}  # rel-path → first aspect that scaffolded it

    # Phase A.3: kit-global files (`files:` in top manifest) retired per ADR-0048.

    for aspect, depth in aspects.items():
        aspect_root = _aspect_path(aspect)
        files_root = aspect_root / "files"
        protocols_root = aspect_root / "protocols"
        for rel in _aspect_files(aspect, depth):
            src = files_root / rel
            if not src.is_file():
                raise click.ClickException(f"kit file missing: {src}")
            prior_owner = file_owners.get(rel)
            if prior_owner is not None and prior_owner != aspect:
                raise click.ClickException(
                    f"Cross-source scaffold collision: aspects "
                    f"{prior_owner!r} and {aspect!r} both declare "
                    f"`files/{rel}`. Per ADR-0028 INV-6 ownership exclusivity, "
                    f"a consumer-relative path may be claimed by at most one "
                    f"aspect across kit + project sources."
                )
            file_owners[rel] = aspect
            bundle[rel] = _render_placeholder(src.read_text(encoding="utf-8"), context)
        for rel in _aspect_protocols(aspect, depth):
            src = protocols_root / rel
            if not src.is_file():
                raise click.ClickException(f"kit protocol missing: {src}")
            bundle[f".kanon/protocols/{aspect}/{rel}"] = _render_placeholder(
                src.read_text(encoding="utf-8"), context
            )
    return bundle


def _render_hard_gates(aspects: dict[str, int]) -> str:
    """Render the hard-gates table from protocol frontmatter declarations."""
    gates: list[dict[str, Any]] = []
    for aspect, depth in aspects.items():
        aspect_root = _aspect_path(aspect)
        for proto_file in _aspect_protocols(aspect, depth):
            proto_path = aspect_root / "protocols" / proto_file
            if not proto_path.exists():
                continue
            fm = _parse_frontmatter(proto_path.read_text(encoding="utf-8"))
            if fm.get("gate") != "hard":
                continue
            # INV-gate-frontmatter-schema: required fields when gate: hard.
            _required = ("label", "summary", "audit")
            missing = [f for f in _required if f not in fm]
            if missing:
                raise click.ClickException(
                    f"{aspect}/{proto_file}: gate: hard requires {', '.join(missing)}"
                )
            fm_depth_min = fm.get("depth-min", 1)
            if depth < fm_depth_min:
                continue
            gates.append({
                "aspect": aspect,
                "protocol": proto_file,
                "label": fm["label"],
                "summary": fm["summary"],
                "audit": fm["audit"],
                "fires": fm.get("invoke-when", ""),
                "priority": fm.get("priority", 500),
                "question": fm.get("question", ""),
                "skip_when": fm.get("skip-when", ""),
            })

    gates.sort(key=lambda g: g["priority"])

    # INV-gate-priority-unique: no two active gates may share a priority.
    seen_priorities: dict[int, str] = {}
    for gate in gates:
        p = gate["priority"]
        if p in seen_priorities:
            raise click.ClickException(
                f"Hard gate priority {p} collision: "
                f"{seen_priorities[p]} and {gate['aspect']}/{gate['protocol']}"
            )
        seen_priorities[p] = f"{gate['aspect']}/{gate['protocol']}"

    if not gates:
        return "## Hard Gates\n\n_No hard gates active at current aspect configuration._\n"

    rows: list[str] = []
    for gate in gates:
        slug = gate["protocol"].removesuffix(".md")
        rows.append(
            f'| **{gate["label"]}** \u2014 {gate["summary"]} '
            f'Audit: "{gate["audit"]}" '
            f'| {gate["fires"]} '
            f'| [`{slug}`](.kanon/protocols/{gate["aspect"]}/{gate["protocol"]}) |'
        )

    # Generate decision tree from active gates
    questions: list[str] = []
    q_num = 1
    questions.append(
        f"{q_num}. Is this change trivial? (Trivial = typo, single assertion fix, "
        "local rename, provably unreachable deletion. Everything else is non-trivial.)"
    )
    for gate in gates:
        if gate["question"]:
            q_num += 1
            q_line = f"{q_num}. {gate['question']}"
            if gate["skip_when"]:
                q_line += f"\n   Skip if: {gate['skip_when']}"
            questions.append(q_line)
    q_num += 1
    questions.append(f"{q_num}. State the audit sentence from the relevant gate before proceeding.")

    lines = [
        "## Hard Gates",
        "",
        "These gates apply to ALL task types. When a gate fires, "
        "read the linked protocol **in full** before proceeding.",
        "",
        "| Gate | Fires when | Protocol |",
        "|------|-----------|----------|",
        *rows,
        "",
        "The audit-trail sentence from the relevant protocol must appear "
        "before your first source-modifying tool call. "
        "Its absence in a transcript is how violations get caught. "
        "This is the intended enforcement mechanism \u2014 prose is source code "
        "([P-prose-is-code](docs/foundations/principles/P-prose-is-code.md)), "
        "not a stopgap for a missing CI gate.",
        "",
        "**Before every source-modifying tool call, answer these questions:**",
        "",
        *questions,
        "",
        "**Mechanical pre-check:** Before your first source-modifying tool call "
        "in a task, run `kanon gates check .` and read its output. "
        "If any gate has status `\"fail\"`, resolve it before proceeding. "
        "For gates with status `\"judgment\"`, evaluate the `question` yourself and "
        "emit the `audit` sentence if satisfied.",
        "",
    ]
    return "\n".join(lines) + "\n"


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


def _assemble_agents_md(aspects: dict[str, int], project_name: str) -> str:
    """Build AGENTS.md for a project with the given aspect→depth mapping.

    Loads the kit-level base template (a slim routing index), renders
    placeholders, and fills the protocols-index marker with the unified
    cross-aspect protocol catalog.
    """
    base = _kit_root() / "agents-md-base.md"
    if not base.is_file():
        raise click.ClickException(f"Missing AGENTS.md base: {base}")
    context: dict[str, str] = {"project_name": project_name}
    for aspect, depth in aspects.items():
        if aspect.startswith("kanon-"):
            _ctx_local = aspect[len("kanon-"):]
            context[f"{_ctx_local}_depth"] = str(depth)
        else:
            context[f"{aspect.replace('-', '_')}_depth"] = str(depth)
    context.setdefault("tier", context.get("sdd_depth", "0"))
    text = _render_placeholder(base.read_text(encoding="utf-8"), context)

    # Render the brand banner above the H1 (single source: kernel/_banner.py).
    from kanon_core._banner import _BANNER
    text = _replace_section(text, "banner", _BANNER)

    # Render the hard-gates table (only gates whose aspects are enabled).
    gates_text = _render_hard_gates(aspects)
    text = _replace_section(text, "hard-gates", gates_text)

    # Render the protocols-index into the single remaining marker.
    index = _render_protocols_index(aspects)
    text = _replace_section(text, "protocols-index", index)

    return text


def _replace_section(text: str, section: str, content: str) -> str:
    pair = _find_section_pair(text, section)
    if pair is None:
        return text
    _, begin_line_end, end_line_start, _ = pair
    # strip("\n") (not strip()) so leading whitespace inside the section content
    # is preserved — required by the banner ASCII art (kanon-banner spec INV-5).
    return text[:begin_line_end] + content.strip("\n") + "\n" + text[end_line_start:]


def _remove_section(text: str, section: str) -> str:
    pair = _find_section_pair(text, section)
    if pair is None:
        return text
    begin_line_start, _, _, end_line_end = pair
    head = text[:begin_line_start].rstrip() + "\n"
    tail = text[end_line_end:]
    if tail.startswith("\n"):
        stripped = tail.lstrip("\n")
        tail = ("\n\n" + stripped) if stripped else "\n"
    return head + tail


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
    """Migrate legacy AGENTS.md markers to v3 (namespaced) form.

    Two legacy shapes are recognised and rewritten:

    - **v0.1 unprefixed**: ``<!-- kanon:begin:plan-before-build -->`` →
      ``<!-- kanon:begin:kanon-sdd/plan-before-build -->`` for sections that
      belong to ``kanon-sdd`` per the kit registry.
    - **v0.2 bare-prefixed**: ``<!-- kanon:begin:sdd/plan-before-build -->``
      → ``<!-- kanon:begin:kanon-sdd/plan-before-build -->``. Same rewrite
      for the other five bare aspect names registered in the kit.

    ``protocols-index`` stays unprefixed (cross-aspect catalog by design).
    Markers inside fenced code blocks or with leading non-whitespace prefixes
    are skipped (see ``_iter_markers``). Idempotent on already-namespaced markers.
    """
    top = _load_top_manifest()
    # Map of bare aspect name → kanon-prefixed canonical, for currently-registered aspects.
    bare_to_canonical: dict[str, str] = {}
    for canonical in top["aspects"]:
        if canonical.startswith("kanon-"):
            bare_to_canonical[canonical[len("kanon-"):]] = canonical

    # v0.1 → v0.3: only kanon-sdd's section names are unprefixed legacy candidates.
    sdd_sections: set[str] = set()
    if "kanon-sdd" in top["aspects"]:
        sdd_sections = {
            s for s in _all_aspect_sections("kanon-sdd") if s not in _UNPREFIXED_SECTIONS
        }

    pieces: list[str] = []
    last = 0
    for kind, sec, line_start, line_end in _iter_markers(text):
        new_sec: str | None = None
        if "/" in sec:
            prefix, _, leaf = sec.partition("/")
            if prefix in bare_to_canonical:
                # v0.2 bare-prefixed → v0.3 namespaced.
                new_sec = f"{bare_to_canonical[prefix]}/{leaf}"
        elif sec in sdd_sections:
            # v0.1 unprefixed → v0.3 namespaced (kanon-sdd's own sections).
            new_sec = f"kanon-sdd/{sec}"
        if new_sec is None:
            continue
        pieces.append(text[last:line_start])
        new_line = f"<!-- kanon:{kind}:{new_sec} -->"
        if line_end > 0 and text[line_end - 1: line_end] == "\n":
            new_line += "\n"
        pieces.append(new_line)
        last = line_end
    pieces.append(text[last:])
    return "".join(pieces)


def _merge_agents_md(existing: str, new: str) -> str:
    """Copy marker-delimited sections from *new* into *existing*.

    - Sections present in both: replaced in-place.
    - Sections present only in *new*: inserted at a sensible anchor.
    - Sections present only in *existing* (active at a different aspect-depth): removed.
    User content outside marker pairs is never modified.

    Also migrates v1 unprefixed markers to v2 namespaced form.
    """
    # Kit-level sections not owned by any single aspect.
    _KIT_SECTIONS = {"hard-gates", "banner"}

    # Iterate kit + active project-overlay aspects so project-aspect sections
    # also participate in the merge (ADR-0028).
    possible: set[str] = _KIT_SECTIONS.copy()
    for aspect_name in _all_known_aspects():
        possible.add(f"{aspect_name}/body")
        for section in _all_aspect_sections(aspect_name):
            possible.add(_namespaced_section(aspect_name, section))

    result = _rewrite_legacy_markers(existing)

    for section in possible:
        new_pair = _find_section_pair(new, section)
        if new_pair is None:
            result = _remove_section(result, section)
            continue
        _, nbe, nes, _ = new_pair
        new_body = new[nbe:nes].strip("\n")
        if _find_section_pair(result, section) is not None:
            result = _replace_section(result, section, new_body)
        else:
            result = _insert_section(result, section, new_body)
    return result


def _write_tree_atomically(
    target: Path, files: dict[str, str], force: bool = False
) -> None:
    from kanon_core._atomic import atomic_write_text

    for rel, content in sorted(files.items()):
        dst = target / rel
        _ensure_within(dst, target)
        if dst.exists() and not force:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dst, content)


def _migrate_flat_protocols(target: Path, aspects: dict[str, int]) -> bool:
    """Move .kanon/protocols/*.md (flat, v0.1) under .kanon/protocols/kanon-sdd/.

    Per ADR-0028 the v3 namespace is `kanon-sdd` (was bare `sdd` in v0.2 and
    flat in v0.1). Returns True if any file was migrated.
    """
    protocols_dir = target / ".kanon" / "protocols"
    if not protocols_dir.is_dir():
        return False
    flat = [p for p in protocols_dir.glob("*.md") if p.is_file()]
    if not flat:
        return False
    if "kanon-sdd" not in aspects:
        return False
    sdd_dir = protocols_dir / "kanon-sdd"
    _ensure_within(sdd_dir, target)
    sdd_dir.mkdir(parents=True, exist_ok=True)
    for p in flat:
        dest = sdd_dir / p.name
        if dest.exists():
            p.unlink()
        else:
            p.rename(dest)
    return True
