"""Scaffold assembly, config I/O, and file-tree writing.

Imports from ``_manifest`` (the dependency root) and provides the
content-construction layer that CLI commands orchestrate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import click
import yaml

from kanon import __version__
from kanon._manifest import (
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
        return config
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


def _config_aspects(config: dict[str, Any]) -> dict[str, int]:
    """Extract {aspect_name: depth} from a v2 config."""
    aspects = config.get("aspects", {})
    return {name: int(entry["depth"]) for name, entry in aspects.items()}


def _write_config(
    target: Path,
    kit_version: str,
    aspects_with_meta: dict[str, dict[str, Any]],
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a v2 .kanon/config.yaml atomically."""
    from kanon._atomic import atomic_write_text

    config_dir = target / ".kanon"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"kit_version": kit_version, "aspects": aspects_with_meta}
    if extra:
        # Defensive: never let extra overwrite canonical keys.
        payload.update({k: v for k, v in extra.items() if k not in ("kit_version", "aspects")})
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

    # Kit-global files (top-level manifest `files:`).
    top = _load_top_manifest()
    kit_files_root = _kit_root() / "files"
    for rel in top.get("files", []) or []:
        src = kit_files_root / rel
        if not src.is_file():
            raise click.ClickException(f"kit-global file missing: {src}")
        file_owners[rel] = "_kit_global"
        bundle[rel] = _render_placeholder(src.read_text(encoding="utf-8"), context)

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


class _HardGate(TypedDict):
    aspect: str
    depth_min: int
    protocol: str
    label: str
    summary: str
    audit: str
    fires: str


_HARD_GATES: list[_HardGate] = [
    {
        "aspect": "kanon-sdd",
        "depth_min": 1,
        "protocol": "plan-before-build.md",
        "label": "Plan Before Build",
        "summary": "non-trivial changes require an approved plan before source edits.",
        "audit": 'Plan at `<path>` has been approved.',
        "fires": "About to modify source for a non-trivial change",
    },
    {
        "aspect": "kanon-sdd",
        "depth_min": 2,
        "protocol": "spec-before-design.md",
        "label": "Spec Before Design",
        "summary": "new user-visible capabilities require an approved spec before design/plan/implementation.",
        "audit": 'Spec at `<path>` has been approved.',
        "fires": "About to introduce a new user-visible capability",
    },
    {
        "aspect": "kanon-worktrees",
        "depth_min": 1,
        "protocol": "branch-hygiene.md",
        "label": "Worktree Isolation",
        "summary": "all file modifications happen in `.worktrees/<slug>/` on branch `wt/<slug>`.",
        "audit": 'Working in worktree `.worktrees/<slug>/` on branch `wt/<slug>`.',
        "fires": "About to modify any file",
    },
]


def _render_hard_gates(aspects: dict[str, int]) -> str:
    """Render the hard-gates table, including only gates whose aspects are enabled at sufficient depth."""
    rows: list[str] = []
    for gate in _HARD_GATES:
        aspect = gate["aspect"]
        if aspect not in aspects or aspects[aspect] < gate["depth_min"]:
            continue
        slug = gate["protocol"].removesuffix(".md")
        rows.append(
            f'| **{gate["label"]}** — {gate["summary"]} '
            f'Audit: "{gate["audit"]}" '
            f'| {gate["fires"]} '
            f'| [`{slug}`](.kanon/protocols/{aspect}/{gate["protocol"]}) |'
        )
    if not rows:
        return "## Hard Gates\n\n_No hard gates active at current aspect configuration._\n"
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
        "This is the intended enforcement mechanism — prose is source code "
        "([P-prose-is-code](docs/foundations/principles/P-prose-is-code.md)), "
        "not a stopgap for a missing CI gate.",
        "",
        "**Before every source-modifying tool call, answer these questions:**",
        "",
        "1. Is this change trivial? (Trivial = typo, single assertion fix, "
        "local rename, provably unreachable deletion. Everything else is "
        "non-trivial.)",
        "2. If non-trivial: does a plan exist at `docs/plans/<slug>.md` "
        "and has the user approved it? If not — **stop and write the plan.**",
        "3. State the audit sentence from the relevant gate before proceeding.",
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


def _render_kit_md(aspects: dict[str, int], project_name: str) -> str | None:
    """Render kit/kit.md with placeholder substitution.

    Context uses ``${<aspect>_depth}`` for each enabled aspect.
    ``${tier}`` is preserved as a backward-compat alias for ``${sdd_depth}``.
    """
    src = _kit_root() / "kit.md"
    if not src.is_file():
        return None
    context: dict[str, str] = {"project_name": project_name}
    for aspect, depth in aspects.items():
        # Strip the `kanon-` prefix for context keys so existing templates'
        # `${sdd_depth}` / `${worktrees_depth}` placeholders keep working
        # (ADR-0028 backward-compat for kit-aspect templates). For project-
        # aspects, replace hyphens with underscores so `${project_foo_depth}`
        # is a valid `string.Template` identifier.
        if aspect.startswith("kanon-"):
            _ctx_local = aspect[len("kanon-"):]
            context[f"{_ctx_local}_depth"] = str(depth)
        else:
            context[f"{aspect.replace('-', '_')}_depth"] = str(depth)
    # Backward-compat alias: ${tier} → sdd depth.
    context.setdefault("tier", context.get("sdd_depth", "0"))
    return _render_placeholder(src.read_text(encoding="utf-8"), context)


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
    return text[:begin_line_end] + content.strip() + "\n" + text[end_line_start:]


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
    # Iterate kit + active project-overlay aspects so project-aspect sections
    # also participate in the merge (ADR-0028).
    possible: set[str] = set()
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
        new_body = new[nbe:nes].strip()
        if _find_section_pair(result, section) is not None:
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
    sdd_dir.mkdir(parents=True, exist_ok=True)
    for p in flat:
        dest = sdd_dir / p.name
        if dest.exists():
            p.unlink()
        else:
            p.rename(dest)
    return True
