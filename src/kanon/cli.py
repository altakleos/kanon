"""kanon CLI.

Subcommands:
    init <target>            Scaffold a new kanon project at <target>.
    upgrade <target>          Update target's .kanon/ to installed kit version.
    verify <target>           Validate target against its declared tier.
    tier set <target> <N>     Migrate target to tier N (0..3), mutable + non-destructive.

Per ADR-0008, tier migration affects AGENTS.md content inside HTML-comment-
delimited sections only; user content outside markers is never touched.

Tier membership (which files and protocols scaffold at which tier, and which
AGENTS.md marker sections are active) is data in src/kanon/kit/manifest.yaml.
See docs/design/kit-bundle.md and ADR-0011.
"""

from __future__ import annotations

import json
import os
import shutil
import string
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import click
import yaml

import kanon
from kanon import __version__

_VALID_TIERS = {0, 1, 2, 3}

# Files the CLI always synthesizes (not sourced from the kit's files/ tree).
# `.kanon/kit.md` is conditional — included only when kit/kit.md exists on disk.
_ALWAYS_SYNTHESIZED = ("AGENTS.md", ".kanon/config.yaml")


def _kit_root() -> Path:
    """Location of the vendored kit bundle inside the installed package."""
    return Path(kanon.__file__).parent / "kit"


@lru_cache(maxsize=1)
def _load_manifest() -> dict[str, Any]:
    """Load and validate kit/manifest.yaml. Cached across calls."""
    path = _kit_root() / "manifest.yaml"
    if not path.is_file():
        raise click.ClickException(f"kit manifest missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise click.ClickException(f"malformed {path}: expected a YAML mapping.")
    for n in range(4):
        key = f"tier-{n}"
        if key not in data:
            raise click.ClickException(f"{path}: missing required key {key!r}.")
        tier_entry = data[key]
        if not isinstance(tier_entry, dict):
            raise click.ClickException(f"{path}: {key} must be a mapping.")
        for bucket in ("files", "protocols"):
            if not isinstance(tier_entry.get(bucket, []), list):
                raise click.ClickException(f"{path}: {key}.{bucket} must be a list.")
    if "agents-md-sections" not in data or not isinstance(data["agents-md-sections"], dict):
        raise click.ClickException(f"{path}: missing or malformed 'agents-md-sections' mapping.")
    return data


def _manifest_tier_files(tier: int) -> list[str]:
    """Return union of files under `tier-0`..`tier-N` from the manifest."""
    manifest = _load_manifest()
    paths: list[str] = []
    for n in range(tier + 1):
        paths.extend(manifest.get(f"tier-{n}", {}).get("files", []))
    return paths


def _manifest_tier_protocols(tier: int) -> list[str]:
    """Return union of protocols under `tier-0`..`tier-N` from the manifest."""
    manifest = _load_manifest()
    paths: list[str] = []
    for n in range(tier + 1):
        paths.extend(manifest.get(f"tier-{n}", {}).get("protocols", []))
    return paths


def _manifest_tier_sections(tier: int) -> list[str]:
    """Return the list of AGENTS.md marker sections active at the given tier."""
    manifest = _load_manifest()
    sections = manifest["agents-md-sections"].get(f"tier-{tier}", [])
    if not isinstance(sections, list):
        raise click.ClickException(
            f"manifest.yaml: agents-md-sections.tier-{tier} must be a list."
        )
    return list(sections)


def _manifest_all_sections() -> set[str]:
    """Every section name referenced anywhere in manifest's agents-md-sections mapping."""
    manifest = _load_manifest()
    seen: set[str] = set()
    for sections in manifest["agents-md-sections"].values():
        if isinstance(sections, list):
            seen.update(sections)
    return seen


def _expected_files(tier: int) -> list[str]:
    """Return the full path list a project at *tier* must have.

    Includes always-synthesized files (AGENTS.md, .kanon/config.yaml, .kanon/kit.md),
    manifest file entries, and protocol entries scaffolded under .kanon/protocols/.
    """
    paths: list[str] = list(_ALWAYS_SYNTHESIZED)
    if (_kit_root() / "kit.md").is_file():
        paths.append(".kanon/kit.md")
    paths.extend(_manifest_tier_files(tier))
    paths.extend(f".kanon/protocols/{p}" for p in _manifest_tier_protocols(tier))
    return paths


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
    config = target / ".kanon" / "config.yaml"
    if not config.is_file():
        raise click.ClickException(
            f"Not a kanon project: {target} (missing .kanon/config.yaml)."
        )
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise click.ClickException(f"Malformed {config}: expected a YAML mapping.")
    return data


def _write_config(target: Path, kit_version: str, tier: int) -> None:
    config_dir = target / ".kanon"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "kit_version": kit_version,
        "tier": tier,
        "tier_set_at": _now_iso(),
    }
    config_path = config_dir / "config.yaml"
    from kanon._atomic import atomic_write_text

    atomic_write_text(config_path, yaml.safe_dump(payload, sort_keys=False))


def _load_harnesses() -> list[dict[str, Any]]:
    path = _kit_root() / "harnesses.yaml"
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
    """Return {relative_path: rendered_content} for every file scaffolded at *tier*.

    Walks kit/files/ and kit/protocols/ filtered by manifest membership.
    Does NOT include always-synthesized files (AGENTS.md, .kanon/config.yaml,
    .kanon/kit.md) — those are assembled separately by the init/upgrade flow.
    """
    bundle: dict[str, str] = {}
    kit = _kit_root()
    files_root = kit / "files"
    protocols_root = kit / "protocols"

    for rel in _manifest_tier_files(tier):
        src = files_root / rel
        if not src.is_file():
            raise click.ClickException(f"kit file missing: {src}")
        bundle[rel] = _render_placeholder(src.read_text(encoding="utf-8"), context)

    for rel in _manifest_tier_protocols(tier):
        src = protocols_root / rel
        if not src.is_file():
            raise click.ClickException(f"kit protocol missing: {src}")
        bundle[f".kanon/protocols/{rel}"] = _render_placeholder(
            src.read_text(encoding="utf-8"), context
        )

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


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse a `---\\n…\\n---\\n` YAML frontmatter block. Empty dict if absent."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


def _render_protocols_index(tier: int) -> str:
    """Render the `protocols-index` marker section body from manifest + protocol frontmatter."""
    kit = _kit_root()
    rows: list[tuple[str, int, str]] = []
    for n in range(tier + 1):
        for name in _load_manifest().get(f"tier-{n}", {}).get("protocols", []):
            proto_path = kit / "protocols" / name
            if not proto_path.is_file():
                continue
            fm = _parse_frontmatter(proto_path.read_text(encoding="utf-8"))
            invoke_when = str(fm.get("invoke-when", "")).strip() or "(no trigger declared)"
            rows.append((name, n, invoke_when))
    lines = [
        "## Active protocols",
        "",
        "Prose-as-code procedures available at this tier. When a trigger fires, read the protocol file in full and follow its numbered steps.",
        "",
        "| Protocol | Tier min | Invoke when |",
        "| --- | --- | --- |",
    ]
    for name, tmin, when in rows:
        slug = name.removesuffix(".md")
        lines.append(f"| [`{slug}`](.kanon/protocols/{name}) | {tmin} | {when} |")
    return "\n".join(lines) + "\n"


def _render_kit_md(tier: int, project_name: str) -> str | None:
    """Render kit/kit.md with placeholder substitution. None if kit.md doesn't exist yet."""
    src = _kit_root() / "kit.md"
    if not src.is_file():
        return None
    return _render_placeholder(
        src.read_text(encoding="utf-8"),
        {"project_name": project_name, "tier": str(tier)},
    )


def _assemble_agents_md(tier: int, project_name: str) -> str:
    """Build AGENTS.md content from kit/agents-md/tier-<N>.md + kit/sections/*.md."""
    kit = _kit_root()
    base = kit / "agents-md" / f"tier-{tier}.md"
    if not base.is_file():
        raise click.ClickException(f"Missing AGENTS.md base: {base}")
    text = _render_placeholder(
        base.read_text(encoding="utf-8"),
        {"project_name": project_name, "tier": str(tier)},
    )
    # Fill marker-delimited blocks with their fragment content.
    for section in _manifest_tier_sections(tier):
        if section == "protocols-index":
            fragment_text = _render_protocols_index(tier)
        else:
            fragment = kit / "sections" / f"{section}.md"
            if not fragment.is_file():
                continue
            fragment_text = fragment.read_text(encoding="utf-8")
        text = _replace_section(text, section, fragment_text)
    # Remove any sections not active at this tier (their markers may be absent).
    inactive = _manifest_all_sections() - set(_manifest_tier_sections(tier))
    for section in inactive:
        text = _remove_section(text, section)
    return text


def _replace_section(text: str, section: str, content: str) -> str:
    """Replace content between <!-- kanon:begin:<section> --> and
    <!-- kanon:end:<section> -->. If markers are absent, return text unchanged."""
    begin = f"<!-- kanon:begin:{section} -->"
    end = f"<!-- kanon:end:{section} -->"
    bi = text.find(begin)
    ei = text.find(end, bi + len(begin)) if bi >= 0 else -1
    if bi < 0 or ei < 0:
        return text
    before = text[: bi + len(begin)]
    after = text[ei:]
    return f"{before}\n{content.strip()}\n{after}"


def _remove_section(text: str, section: str) -> str:
    """Remove the marker pair and everything between them."""
    begin = f"<!-- kanon:begin:{section} -->"
    end = f"<!-- kanon:end:{section} -->"
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
    """Write *files* relative to *target*, atomically per-file."""
    from kanon._atomic import atomic_write_text

    for rel, content in sorted(files.items()):
        dst = target / rel
        if dst.exists() and not force:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dst, content)


def _atomic_replace_dir(src: Path, dst: Path) -> None:
    """Replace *dst* with the contents of *src* atomically."""
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
@click.version_option(__version__, prog_name="kanon")
def main() -> None:
    """kanon — portable, self-hosting SDD kit for LLM-agent-driven repos."""


@main.command()
@click.argument("target", type=click.Path(file_okay=False, path_type=Path))
@click.option("--tier", "tier_arg", type=click.IntRange(0, 3), default=1, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite an existing .kanon/ directory.")
def init(target: Path, tier_arg: int, force: bool) -> None:
    """Scaffold a new kanon project at TARGET."""
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    config_path = target / ".kanon" / "config.yaml"
    if config_path.exists() and not force:
        raise click.ClickException(
            f"kanon project already exists at {target}. "
            f"Run `kanon upgrade` to refresh, or re-run with --force to reinitialise."
        )

    context = {"project_name": target.name, "tier": str(tier_arg)}

    bundle = _build_bundle(tier_arg, context)
    bundle["AGENTS.md"] = _assemble_agents_md(tier_arg, target.name)
    kit_md = _render_kit_md(tier_arg, target.name)
    if kit_md is not None:
        bundle[".kanon/kit.md"] = kit_md
    bundle.update(_render_shims())

    _write_tree_atomically(target, bundle, force=force)
    _write_config(target, __version__, tier_arg)

    click.echo(f"Created kanon project at {target} (tier {tier_arg}).")
    click.echo(f"Wrote {len(bundle) + 1} files plus .kanon/config.yaml.")
    click.echo("Open this folder with any LLM coding agent to begin.")


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def upgrade(target: Path) -> None:
    """Refresh TARGET's .kanon/ from the installed kit (preserving docs/, AGENTS.md, config)."""
    target = target.resolve()
    config = _read_config(target)
    tier_arg = int(config.get("tier", 1))
    old_version = config.get("kit_version", "unknown")

    if old_version == __version__:
        click.echo(f"Already at {__version__}. Nothing to upgrade.")
        return

    # v0.2: upgrade rewrites AGENTS.md marker sections, kit.md, and config.
    # Consumer-authored content outside markers is preserved.
    from kanon._atomic import atomic_write_text

    new_agents_md = _assemble_agents_md(tier_arg, target.name)
    existing = (target / "AGENTS.md").read_text(encoding="utf-8")
    merged = _merge_agents_md(existing, new_agents_md)
    if merged != existing:
        atomic_write_text(target / "AGENTS.md", merged)

    kit_md = _render_kit_md(tier_arg, target.name)
    if kit_md is not None:
        atomic_write_text(target / ".kanon" / "kit.md", kit_md)

    _write_config(target, __version__, tier_arg)

    click.echo(f"Upgraded kanon project at {target}: {old_version} → {__version__}")


_SECTION_INSERT_ANCHOR = "## Contribution Conventions"


def _insert_section(text: str, section: str, content: str) -> str:
    """Insert a new marker-delimited section into *text* at a sensible anchor."""
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


def _merge_agents_md(existing: str, new: str) -> str:
    """Copy marker-delimited sections from *new* into *existing*.

    - Sections present in both are replaced in-place.
    - Sections present only in *new* are inserted at a sensible anchor.
    - Sections present only in *existing* are removed.
    User content outside all marker pairs is never modified.
    """
    all_sections = _manifest_all_sections()
    result = existing
    for section in all_sections:
        begin = f"<!-- kanon:begin:{section} -->"
        end = f"<!-- kanon:end:{section} -->"
        nb = new.find(begin)
        ne = new.find(end, nb + len(begin)) if nb >= 0 else -1
        if nb < 0 or ne < 0:
            result = _remove_section(result, section)
            continue
        new_section_body = new[nb + len(begin): ne].strip()
        if begin in result and end in result:
            result = _replace_section(result, section, new_section_body)
        else:
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
        for section in _manifest_tier_sections(tier_arg):
            begin = f"<!-- kanon:begin:{section} -->"
            end = f"<!-- kanon:end:{section} -->"
            if begin not in agents_text or end not in agents_text:
                errors.append(f"AGENTS.md missing marker pair for section '{section}' (tier {tier_arg}).")
        all_begins = agents_text.count("<!-- kanon:begin:")
        all_ends = agents_text.count("<!-- kanon:end:")
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
        click.echo(f"OK — tier-{tier} kanon project at {target} is valid.", err=True)
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
        _write_config(target, config.get("kit_version", __version__), n)
        click.echo(f"Tier already {n}. Noop (timestamp refreshed).")
        return

    context = {"project_name": target.name, "tier": str(n)}
    target_bundle = _build_bundle(n, context)

    if n > current:
        added = 0
        for rel, content in sorted(target_bundle.items()):
            dst = target / rel
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            from kanon._atomic import atomic_write_text

            atomic_write_text(dst, content)
            added += 1
        click.echo(f"Tier-up {current} → {n}: added {added} new file(s).")
    else:
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
    from kanon._atomic import atomic_write_text

    new_agents = _assemble_agents_md(n, target.name)
    existing_agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    merged = _merge_agents_md(existing_agents, new_agents)
    if merged != existing_agents:
        atomic_write_text(target / "AGENTS.md", merged)

    # Rewrite .kanon/kit.md to reflect the new tier.
    kit_md = _render_kit_md(n, target.name)
    if kit_md is not None:
        atomic_write_text(target / ".kanon" / "kit.md", kit_md)

    _write_config(target, config.get("kit_version", __version__), n)
    click.echo(f"Tier set to {n} in .kanon/config.yaml.")


if __name__ == "__main__":
    main()
