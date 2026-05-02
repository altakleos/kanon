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
from typing import Any

import click

from kanon import __version__
from kanon._cli_aspect import _commit_aspect_meta, _set_aspect_depth
from kanon._cli_helpers import (
    _OP_ASPECT_REMOVE,
    _OP_FIDELITY_UPDATE,
    _OP_INIT,
    _OP_SET_CONFIG,
    _OP_UPGRADE,
    _check_pending_recovery,
    _check_removal_dependents,
    _check_requires,
    _parse_aspects_flag,
    _parse_config_pair,
)
from kanon._fidelity import _accepted_or_draft_specs, _fixture_shas, _spec_sha
from kanon._graph import (
    ORPHAN_CANDIDATE_NAMESPACES,
    build_graph,
    compute_orphans,
)
from kanon._manifest import (
    _aspect_config_schema,
    _aspect_depth_range,
    _aspect_provides,
    _load_aspect_manifest,
    _load_aspect_registry,
    _load_yaml,
    _normalise_aspect_name,
    _now_iso,
)
from kanon._scaffold import (
    _DEFAULT_V4_EXTRAS,
    _aspects_with_meta,
    _assemble_agents_md,
    _build_bundle,
    _config_aspects,
    _detect_harnesses,
    _extras_from_config,
    _merge_agents_md,
    _migrate_flat_protocols,
    _migrate_legacy_config,
    _read_config,
    _render_shims,
    _write_config,
    _write_tree_atomically,
)

# Per ADR-0042 §1: the canonical exit-zero wording for `kanon verify`. Immutable
# under ADR-0032; surfaced verbatim on `kanon verify --help` and cited in
# verify-failure error messages. acme- publishers cite this constant by ID
# when documenting what their bundles claim about consumer conformance.
_ADR_0042_VERIFY_SCOPE = (
    "Verify TARGET conforms to its declared aspects.\n"
    "\n"
    "Per ADR-0042: `kanon verify` exit-0 means: the consumer repo conforms to the\n"
    "structural and behavioural contracts expressed in the discipline aspects the\n"
    "consumer has explicitly enabled, at the depths the consumer has declared.\n"
    "\n"
    "It MUST NOT be interpreted as — and the substrate MUST NOT represent it as:\n"
    "\n"
    "- a signal that the consumer's repository follows good engineering practices\n"
    "  beyond what the enabled aspects define;\n"
    "- a correctness or quality endorsement of any prose, protocol, or code in\n"
    "  the consumer's tree;\n"
    "- a guarantee that the consumer's declared agent will comply with the\n"
    "  enabled protocols at runtime — exit-0 is a static structural check, not a\n"
    "  runtime behavioural guarantee;\n"
    "- confirmation that resolution-replay invocations are semantically correct\n"
    "  realizations of their contracts."
)


@click.group()
@click.version_option(__version__, prog_name="kanon")
def main() -> None:
    """kanon — portable, self-hosting development-discipline kit for LLM-agent-driven repos."""


def _resolve_init_harnesses(
    harness_arg: tuple[str, ...], target: Path,
) -> set[str]:
    """Determine which harness shims to write."""
    if harness_arg:
        if "auto" in harness_arg:
            return _detect_harnesses(target) | {"claude-code"}
        return set(harness_arg)
    return _detect_harnesses(target) | {"claude-code"}


def _emit_init_hints(
    aspects_meta: dict[str, dict[str, Any]],
    aspects_to_enable: dict[str, int],
) -> None:
    """Print grow-when-ready hints to stderr.

    Phase A.4 (per ADR-0048 de-opinionation): the "Preflight readiness" section
    that read kanon-testing's runtime config-schema (test_cmd / lint_cmd /
    typecheck_cmd / format_cmd) was retired along with the schema itself.
    """
    grow_hints: list[str] = []
    if "kanon-sdd" in aspects_to_enable and aspects_to_enable["kanon-sdd"] < 2:
        # Per ADR-0045 Phase A.5: use canonical kanon-<local> names; the bare-name
        # shorthand (`sdd`, `worktrees`, etc.) is deprecated and emits a stderr
        # warning when used. Init hints recommending bare names would ironically
        # walk users into the very warning the deprecation surfaces.
        grow_hints.append("    kanon aspect set-depth . kanon-sdd 2     # add specs")
    if "kanon-testing" not in aspects_to_enable:
        grow_hints.append("    kanon aspect add . kanon-testing         # add test discipline")
    if "kanon-security" not in aspects_to_enable:
        grow_hints.append("    kanon aspect add . kanon-security        # add secure-by-default protocols")
    if "kanon-worktrees" not in aspects_to_enable:
        grow_hints.append("    kanon aspect add . kanon-worktrees       # add worktree isolation")
    grow_hints.append("    kanon verify .                      # check project health")
    grow_section = "\n".join(grow_hints)

    click.echo(
        f"\n  Next steps:\n"
        f"  1. Open this folder with your LLM coding agent\n"
        f"  2. The agent will read AGENTS.md and follow the process\n"
        f"\n  Grow when ready:\n"
        f"{grow_section}"
    )


@main.command()
@click.argument("target", type=click.Path(file_okay=False, path_type=Path))
@click.option(
    "--tier",
    "tier_arg",
    type=click.IntRange(0, 3),
    default=None,
    show_default=False,
    help="Uniform depth N for every default aspect, capped at each aspect's max (ADR-0035).",
)
@click.option(
    "--aspects",
    "aspects_arg",
    default=None,
    help="Comma-separated aspect:depth pairs (e.g., sdd:1,worktrees:2).",
)
@click.option("--force", is_flag=True, help="Overwrite an existing .kanon/ directory.")
@click.option(
    "--harness",
    "harness_arg",
    multiple=True,
    default=None,
    help="Harness shims to write (repeatable). 'auto' detects from existing dirs. Default: auto.",
)
@click.option("--lite", is_flag=True, help="Minimal setup: sdd at depth 0 (just AGENTS.md, no docs/).")
@click.option(
    "--profile",
    "profile_arg",
    type=click.Choice(["solo", "team", "all", "max"], case_sensitive=False),
    default=None,
    help=(
        "Preset aspect bundles (per ADR-0037). "
        "solo=sdd:1; "
        "team=sdd+testing+security+deps+worktrees at depth 1; "
        "all=every kit aspect at its default-depth; "
        "max=every kit aspect at the upper end of its depth-range."
    ),
)
@click.option(
    "--quiet", "-q",
    "quiet_arg",
    is_flag=True,
    help="Suppress banner and trailing advisory output.",
)
def init(
    target: Path,
    tier_arg: int | None,
    aspects_arg: str | None,
    force: bool,
    harness_arg: tuple[str, ...],
    lite: bool,
    profile_arg: str | None,
    quiet_arg: bool,
) -> None:
    """Scaffold a new kanon project at TARGET."""
    from kanon._banner import _BANNER, _should_emit_banner
    if _should_emit_banner(quiet_arg):
        click.echo(_BANNER, err=True, nl=False)

    exclusive_count = sum([
        tier_arg is not None,
        aspects_arg is not None,
        lite,
        profile_arg is not None,
    ])
    if exclusive_count > 1:
        raise click.ClickException("--tier, --aspects, --lite, and --profile are mutually exclusive.")

    target = target.resolve()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise click.ClickException(f"Cannot create target directory: {exc}") from exc

    config_path = target / ".kanon" / "config.yaml"
    if config_path.exists() and not force:
        raise click.ClickException(
            f"kanon project already exists at {target}. "
            f"Run `kanon upgrade` to refresh, or re-run with --force to reinitialise."
        )

    top = _load_aspect_registry(target)

    _PROFILES: dict[str, dict[str, int]] = {
        "solo": {"kanon-sdd": 1},
        "team": {"kanon-sdd": 1, "kanon-testing": 1, "kanon-security": 1, "kanon-deps": 1, "kanon-worktrees": 1},
        "all": {
            name: int(entry["default-depth"])
            for name, entry in top["aspects"].items()
            if name.startswith("kanon-")
        },
        "max": {
            name: int(entry["depth-range"][1])
            for name, entry in top["aspects"].items()
            if name.startswith("kanon-")
        },
    }

    if aspects_arg is not None:
        aspects_to_enable = _parse_aspects_flag(aspects_arg, top)
    elif tier_arg is not None:
        # Phase A.3 (per ADR-0048 de-opinionation): kit-global defaults: was
        # retired. --tier N now applies to every kit-shipped (kanon-) aspect,
        # capped per aspect's max depth.
        aspects_to_enable = {
            name: min(tier_arg, int(entry["depth-range"][1]))
            for name, entry in top["aspects"].items()
            if name.startswith("kanon-")
        }
    elif lite:
        aspects_to_enable = {"kanon-sdd": 0}
    elif profile_arg is not None:
        aspects_to_enable = _PROFILES[profile_arg]
    else:
        # Phase A.3: kit-global defaults: retired. `kanon init` with no flags
        # now scaffolds an empty project; consumer must opt in via --aspects,
        # --tier, --lite, or --profile.
        aspects_to_enable = {}

    # Use the kanon-sdd depth as the tier context value when enabled, else "0".
    tier_ctx = str(aspects_to_enable.get("kanon-sdd", 0))
    aspects_summary = "\n".join(
        f"- **{a}** at depth {d}" for a, d in sorted(aspects_to_enable.items())
    ) or "_No aspects enabled._"
    context = {
        "project_name": target.name,
        "tier": tier_ctx,
        "active_aspects_summary": aspects_summary,
    }

    bundle = _build_bundle(aspects_to_enable, context)
    # Per INV-cli-init-agents-md-merge / ADR-0038: three-branch merge into
    # an existing AGENTS.md. (1) absent → write full kit-rendered file;
    # (2) existing with kanon markers → refresh marker bodies via the same
    # primitive `kanon upgrade` uses; (3) existing without markers → prepend
    # kit content above the existing prose, separated by `## Project context`
    # so hard-gates retain enforcement proximity (ADR-0010 / ADR-0034).
    new_agents = _assemble_agents_md(aspects_to_enable, target.name)
    agents_path = target / "AGENTS.md"
    if agents_path.is_file():
        existing = agents_path.read_text(encoding="utf-8")
        if "<!-- kanon:begin:" in existing:
            bundle["AGENTS.md"] = _merge_agents_md(existing, new_agents)
        else:
            bundle["AGENTS.md"] = (
                new_agents.rstrip()
                + "\n\n## Project context\n\n"
                + existing.lstrip()
            )
    else:
        bundle["AGENTS.md"] = new_agents
    shim_names = _resolve_init_harnesses(harness_arg, target)
    bundle.update(_render_shims(only=shim_names))

    from kanon._atomic import atomic_write_text, clear_sentinel, write_sentinel

    # AGENTS.md is written out-of-band: `_write_tree_atomically` skips
    # files that exist when `force=False`, but per ADR-0038 init must
    # always update AGENTS.md (refresh markers or prepend kit content),
    # never silently leave it untouched.
    agents_md_content = bundle.pop("AGENTS.md")

    (target / ".kanon").mkdir(parents=True, exist_ok=True)
    write_sentinel(target / ".kanon", _OP_INIT)
    _write_tree_atomically(target, bundle, force=force)
    atomic_write_text(target / "AGENTS.md", agents_md_content)

    # Phase A.4 (per ADR-0048 de-opinionation): _detect.py auto-detection
    # of pytest/ruff/mypy/npm-test was retired. Consumers configure aspects
    # explicitly (e.g., via `kanon aspect set-config`).
    aspects_meta = _aspects_with_meta(aspects_to_enable)

    _write_config(target, __version__, aspects_meta, extra=_DEFAULT_V4_EXTRAS)
    clear_sentinel(target / ".kanon")

    aspect_summary = ", ".join(f"{a}={d}" for a, d in sorted(aspects_to_enable.items()))
    click.echo(f"\n✓ Created kanon project at {target} ({aspect_summary})")

    if quiet_arg:
        return

    if not quiet_arg:
        _emit_init_hints(aspects_meta, aspects_to_enable)


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--quiet", "-q",
    "quiet_arg",
    is_flag=True,
    help="Suppress banner output.",
)
def upgrade(target: Path, quiet_arg: bool) -> None:
    """Refresh TARGET's .kanon/ from the installed kit (preserving docs/, AGENTS.md, config)."""
    from kanon._banner import _BANNER, _should_emit_banner
    if _should_emit_banner(quiet_arg):
        click.echo(_BANNER, err=True, nl=False)

    target = target.resolve()
    config_path = target / ".kanon" / "config.yaml"
    if not config_path.is_file():
        raise click.ClickException(
            f"Not a kanon project: {target} (missing .kanon/config.yaml)."
        )
    _check_pending_recovery(target)
    # Side-effect: sets the active project-aspects overlay so downstream
    # `_aspect_*` helpers see project-aspects discovered under
    # <target>/.kanon/aspects/ (ADR-0028).
    _load_aspect_registry(target)
    raw = _load_yaml(config_path)
    was_legacy = "aspects" not in raw and "tier" in raw
    config = _migrate_legacy_config(raw)
    aspects = _config_aspects(config)
    old_version = config.get("kit_version", "unknown")

    version_changed = old_version != __version__ or was_legacy
    if not version_changed:
        click.echo(
            f"Already at {__version__}. Re-rendering kit-managed sections."
        )

    from kanon._atomic import atomic_write_text, clear_sentinel, write_sentinel

    write_sentinel(target / ".kanon", _OP_UPGRADE)
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

    # Phase A.3: kit-global files: retired (per ADR-0048 de-opinionation).
    # No kit-global file scaffolding. Aspects ship their own files via depth-N.

    for rel_path, content in _render_shims().items():
        shim_path = target / rel_path
        shim_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(shim_path, content)

    if version_changed:
        # Preserve per-aspect metadata (enabled_at, config) from existing config.
        existing_aspects = config.get("aspects", {})
        upgraded_aspects = {}
        now = _now_iso()
        for name, depth in aspects.items():
            old = existing_aspects.get(name, {})
            upgraded_aspects[name] = {
                "depth": depth,
                "enabled_at": old.get("enabled_at", now),
                "config": old.get("config", {}),
            }
        # Preserve root-level keys beyond kit_version and aspects.
        extra = {k: v for k, v in config.items() if k not in ("kit_version", "aspects")}
        _write_config(target, __version__, upgraded_aspects, extra=extra)
    clear_sentinel(target / ".kanon")

    if was_legacy:
        click.echo("Migrated legacy tier config to aspect model.")
    if migrated_flat:
        click.echo("Namespaced flat .kanon/protocols/*.md under kanon-sdd/.")
    if version_changed:
        click.echo(f"Upgraded kanon project at {target}: {old_version} → {__version__}")


@main.command(help=_ADR_0042_VERIFY_SCOPE)
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def verify(target: Path) -> None:
    from kanon._verify import (
        check_agents_md_markers,
        check_aspects_known,
        check_fidelity_assertions,
        check_fidelity_lock,
        check_required_files,
        check_verified_by,
        run_kit_validators,
        run_project_validators,
    )

    target = target.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    _check_pending_recovery(target)

    # Side-effect: sets the active project-aspects overlay so the structural
    # checks below see project-aspects discovered under .kanon/aspects/.
    # A malformed project-aspect manifest (e.g., a kanon-namespace dir under
    # .kanon/aspects/, or a missing required field) surfaces here as a
    # verify-error rather than crashing the command.
    try:
        _load_aspect_registry(target)
    except click.ClickException as exc:
        _emit_verify_report(
            target, {}, errors=[exc.message], warnings=[], status="fail"
        )
        sys.exit(2)

    try:
        config = _read_config(target)
    except click.ClickException as exc:
        _emit_verify_report(
            target, {}, errors=[exc.message], warnings=[], status="fail"
        )
        sys.exit(2)

    aspects = _config_aspects(config)
    if not aspects:
        warnings.append("No aspects enabled; only kit-global files verified.")

    # Per project-aspects spec INV-9 (validator non-overriding), project-
    # aspect validators run BEFORE the kit's structural checks: any
    # `errors.clear()` from a hostile validator is overwritten by the kit's
    # subsequent appends, so kit-emitted errors cannot be suppressed.
    run_project_validators(target, aspects, errors, warnings)

    known_aspects = check_aspects_known(aspects, errors, warnings)
    check_required_files(target, known_aspects, errors)
    check_agents_md_markers(target, aspects, known_aspects, errors)
    check_fidelity_lock(
        target, aspects.get("kanon-sdd", 0), warnings,
        spec_sha_fn=_spec_sha, accepted_specs_fn=_accepted_or_draft_specs,
    )
    check_verified_by(target, aspects.get("kanon-sdd", 0), warnings)
    # Kit-aspect validators: trusted code, runs from the installed package.
    # Depth-gated via depth-N: validators: entries in aspect sub-manifests.
    run_kit_validators(target, aspects, errors, warnings)
    # Per docs/specs/verification-contract.md INV-10 (carve-out from INV-9,
    # ratified by ADR-0029): fidelity-fixture replay runs only when an
    # enabled aspect declares the `behavioural-verification` capability
    # (per ADR-0026). When no such aspect is enabled, this is a no-op.
    check_fidelity_assertions(target, aspects, errors, warnings)

    status = "fail" if errors else "ok"
    _emit_verify_report(target, aspects, errors=errors, warnings=warnings, status=status)
    if errors:
        sys.exit(1)


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--stage",
    type=click.Choice(["commit", "push", "release"], case_sensitive=False),
    default="commit",
    show_default=True,
    help="Validation stage: commit (fast), push (thorough), release (exhaustive).",
)
@click.option("--tag", default=None, help="Release tag (required for --stage release).")
@click.option("--fail-fast", is_flag=True, help="Stop on first failing check.")
def preflight(target: Path, stage: str, tag: str | None, fail_fast: bool) -> None:
    """Run staged local validation: verify + configured checks."""
    from kanon._preflight import _resolve_preflight_checks, _run_preflight

    if stage == "release" and not tag:
        raise click.ClickException("--tag is required for --stage release.")

    target = target.resolve()
    config = _read_config(target)
    aspects = _config_aspects(config)

    # Step 1: Run kanon verify via CliRunner (same process).
    import time as _time

    from click.testing import CliRunner as _Runner
    t0 = _time.monotonic()
    _vr = _Runner().invoke(main, ["verify", str(target)])
    verify_duration = round(_time.monotonic() - t0, 1)
    verify_passed = _vr.exit_code == 0
    verify_mark = "✓" if verify_passed else "✗"
    print(f"{verify_mark} verify (structural)  {verify_duration}s", file=sys.stderr)

    if not verify_passed:
        print(json.dumps({
            "stage": stage,
            "checks": [
                {"label": "verify", "command": "kanon verify .",
                 "passed": False, "duration_s": verify_duration},
            ],
            "passed": False,
        }, indent=2))
        sys.exit(1)

    # Step 2: Resolve and run stage checks.
    checks = _resolve_preflight_checks(aspects, config, stage)
    all_passed, results = _run_preflight(target, checks, tag, fail_fast)

    # Prepend verify result.
    results.insert(0, {"label": "verify", "command": "kanon verify .", "passed": True, "duration_s": verify_duration})

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    summary_mark = "──" if all_passed else "✗✗"
    print(f"{summary_mark} {stage}: {passed_count} of {total} checks passed {summary_mark}", file=sys.stderr)

    print(json.dumps({"stage": stage, "checks": results, "passed": all_passed}, indent=2))
    sys.exit(0 if all_passed else 1)


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
        if warnings:
            click.echo("  warnings:", err=True)
            for w in warnings:
                click.echo(f"    - {w}", err=True)
    else:
        click.echo(f"FAIL — {len(errors)} error(s) at {target}.", err=True)
        # Per ADR-0042 §1: surface the exit-zero scope at failure time so
        # consumers reading the error message see the canonical claim about
        # what verify does (and does not) certify.
        click.echo(
            "  Note: exit-zero certifies conformance to enabled aspects only — "
            "see ADR-0042 for the full claim.",
            err=True,
        )


@main.command("release")
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--tag", required=True, help="Release tag, e.g. v1.2.0")
@click.option("--dry-run", is_flag=True, help="Run preflight but don't create tag.")
def release_cmd(target: Path, tag: str, dry_run: bool) -> None:
    """Gate a release tag on preflight checks (release depth >= 2)."""
    import re as _re
    import subprocess as _sp

    target = target.resolve()
    config = _read_config(target)
    aspects = _config_aspects(config)

    # Check release aspect depth >= 2.
    release_depth = aspects.get("kanon-release", 0)
    if release_depth < 2:
        raise click.ClickException(
            f"release aspect depth >= 2 required (current: {release_depth}). "
            f"Run: kanon aspect set-depth {target} release 2"
        )

    # Validate tag format.
    if not _re.match(r"^v?\d+\.\d+\.\d+", tag):
        raise click.ClickException(f"Invalid tag format: {tag!r}")

    # Check clean working tree.
    st = _sp.run(
        ["git", "status", "--porcelain"],
        cwd=str(target), capture_output=True, text=True,
    )
    if st.stdout.strip():
        raise click.ClickException("Working tree is dirty. Commit first.")

    # Run preflight --stage release.
    from click.testing import CliRunner as _Runner
    pf = _Runner().invoke(
        main, ["preflight", str(target), "--stage", "release", "--tag", tag],
    )

    if pf.exit_code != 0:
        click.echo("✗ Preflight failed — tag NOT created.", err=True)
        sys.exit(1)

    if dry_run:
        click.echo(
            f"✓ Preflight passed (dry-run) — tag {tag} would be created.",
            err=True,
        )
        sys.exit(0)

    # Create annotated tag.
    _sp.run(
        ["git", "tag", "-a", tag, "-m", f"Release {tag}"],
        cwd=str(target), check=True,
    )
    click.echo(f"✓ Tagged {tag}", err=True)
    click.echo(f"  Push with: git push origin {tag}", err=True)


@main.group()
def tier() -> None:
    """Tier verbs (uniform aspect-depth raise per ADR-0035)."""


@tier.command("set")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("n", type=click.IntRange(0, 3))
def tier_set(target: Path, n: int) -> None:
    """Raise every enabled aspect to depth N (capped per aspect).

    Per ADR-0035: a uniform raise. Aspects already at or above the per-aspect
    target depth (min(N, max)) are not lowered.

    Phase A.3 (per ADR-0048 de-opinionation): operates on the consumer's
    currently-enabled aspect set (read from .kanon/config.yaml) rather than
    the retired kit-global ``defaults:`` block.
    """
    target_resolved = target.resolve()
    config = _read_config(target_resolved)
    aspects = _config_aspects(config)
    top = _load_aspect_registry(target_resolved)

    raised: list[str] = []
    for name in sorted(aspects):
        if name not in top["aspects"]:
            continue
        max_depth = int(top["aspects"][name]["depth-range"][1])
        target_depth = min(n, max_depth)
        current = aspects.get(name, -1)
        if current < target_depth:
            _set_aspect_depth(target, name, target_depth, legacy_tier_verb=True)
            raised.append(name)

    if not raised:
        click.echo(f"All enabled aspects already at or above tier {n}. Noop.")


@main.group()
def aspect() -> None:
    """Aspect management (ADR-0012)."""


@aspect.command("list")
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="When set, also list project-aspects discovered under "
         "<target>/.kanon/aspects/. Without --target, only kit-shipped "
         "aspects are listed.",
)
def aspect_list(target: Path | None) -> None:
    """List aspects available in the installed kit (and project-aspects, when --target given)."""
    top = _load_aspect_registry(target)
    for name in sorted(top["aspects"]):
        entry = top["aspects"][name]
        rng = entry["depth-range"]
        desc = entry.get("description", "")
        desc_suffix = f"  {desc}" if desc else ""
        click.echo(
            f"{name}\t{entry['stability']}\tdepth {rng[0]}-{rng[1]} "
            f"(default {entry['default-depth']}){desc_suffix}"
        )


@aspect.command("info")
@click.argument("name")
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="When the queried aspect is a project-aspect (`project-<local>`), "
         "supply --target to point at the consumer repo whose "
         ".kanon/aspects/ defines it.",
)
def aspect_info(name: str, target: Path | None) -> None:
    """Print metadata for an aspect."""
    name = _normalise_aspect_name(name)
    top = _load_aspect_registry(target)
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
    click.echo(f"  Provides:      {', '.join(_aspect_provides(name)) or '(none)'}")
    min_d, max_d = _aspect_depth_range(name)
    for d in range(min_d, max_d + 1):
        depth_entry = sub.get(f"depth-{d}", {})
        files = depth_entry.get("files", []) or []
        protos = depth_entry.get("protocols", []) or []
        click.echo(f"  Depth {d}: {len(files)} file(s), {len(protos)} protocol(s)")
    schema = _aspect_config_schema(name)
    if schema:
        click.echo("  Config keys:")
        for key in sorted(schema):
            descriptor = schema[key]
            tline = f"    {key}: {descriptor.get('type', '?')}"
            if "default" in descriptor:
                tline += f" (default: {descriptor['default']!r})"
            click.echo(tline)
            description = descriptor.get("description")
            if description:
                click.echo(f"      {description}")


@aspect.command("add")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("aspect_name")
@click.option("--depth", type=int, default=None, help="Initial depth (default: aspect's default-depth).")
@click.option(
    "--config",
    "config_pairs",
    multiple=True,
    metavar="KEY=VALUE",
    help="Set an aspect-config key at enable time. Repeatable. "
         "VALUE is parsed as a YAML scalar (e.g., 80, true, foo).",
)
def aspect_add(
    target: Path,
    aspect_name: str,
    depth: int | None,
    config_pairs: tuple[str, ...],
) -> None:
    """Enable an aspect at its default depth (or --depth N)."""
    target = target.resolve()
    aspect_name = _normalise_aspect_name(aspect_name)
    config = _read_config(target)
    top = _load_aspect_registry(target)
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
    chosen_depth = depth if depth is not None else int(top["aspects"][aspect_name]["default-depth"])
    min_d, max_d = _aspect_depth_range(aspect_name)
    if not (min_d <= chosen_depth <= max_d):
        raise click.ClickException(
            f"Depth {chosen_depth} is outside range [{min_d},{max_d}] for aspect {aspect_name!r}."
        )
    # Check requires before enabling
    proposed = dict(aspects)
    proposed[aspect_name] = chosen_depth
    err = _check_requires(aspect_name, proposed, top)
    if err:
        raise click.ClickException(err)
    # Parse --config pairs against the aspect's optional schema before any I/O.
    schema = _aspect_config_schema(aspect_name)
    config_values: dict[str, Any] = {}
    for raw in config_pairs:
        key, value = _parse_config_pair(raw, schema)
        config_values[key] = value
    _set_aspect_depth(
        target, aspect_name, chosen_depth, extra_config=config_values or None
    )


@aspect.command("remove")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("aspect_name")
def aspect_remove(target: Path, aspect_name: str) -> None:
    """Remove an aspect (non-destructive: scaffolded files are left on disk)."""
    target = target.resolve()
    aspect_name = _normalise_aspect_name(aspect_name)
    config = _read_config(target)
    _check_pending_recovery(target)
    aspects = _config_aspects(config)
    if aspect_name not in aspects:
        raise click.ClickException(
            f"Aspect {aspect_name!r} is not enabled in this project."
        )

    # Check if other enabled aspects depend on this one
    top = _load_aspect_registry(target)
    remaining = {k: v for k, v in aspects.items() if k != aspect_name}
    err = _check_removal_dependents(aspect_name, remaining, top)
    if err:
        raise click.ClickException(err)

    from kanon._atomic import atomic_write_text, clear_sentinel, write_sentinel

    # Remove aspect from config
    aspects_meta = dict(config.get("aspects", {}))
    del aspects_meta[aspect_name]
    kit_version = config.get("kit_version", __version__)

    # Remaining aspects for AGENTS.md reassembly
    remaining = {k: int(v["depth"]) for k, v in aspects_meta.items()}

    # Sentinel wraps the multi-file mutation: AGENTS.md + config.yaml.
    # (Phase A.3: kit.md retired per ADR-0048 de-opinionation.)
    # Cleared only on the success path; an exception below leaves the sentinel
    # so the next CLI invocation warns the user (ADR-0024 contract).
    write_sentinel(target / ".kanon", _OP_ASPECT_REMOVE)

    # Re-assemble and merge AGENTS.md without the removed aspect
    new_agents = _assemble_agents_md(remaining, target.name)
    agents_path = target / "AGENTS.md"
    if agents_path.is_file():
        existing = agents_path.read_text(encoding="utf-8")
        merged = _merge_agents_md(existing, new_agents)
        if merged != existing:
            atomic_write_text(agents_path, merged)

    _write_config(target, kit_version, aspects_meta, extra=_extras_from_config(config))
    clear_sentinel(target / ".kanon")

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
    _set_aspect_depth(target, _normalise_aspect_name(aspect_name), n)


@aspect.command("set-config")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("aspect_name")
@click.argument("pair", metavar="KEY=VALUE")
def aspect_set_config(target: Path, aspect_name: str, pair: str) -> None:
    """Set one config value on an enabled aspect (KEY=VALUE; YAML-scalar value)."""
    target = target.resolve()
    aspect_name = _normalise_aspect_name(aspect_name)
    config = _read_config(target)
    _check_pending_recovery(target)
    top = _load_aspect_registry(target)
    if aspect_name not in top["aspects"]:
        raise click.ClickException(
            f"Unknown aspect: {aspect_name!r}. See `kanon aspect list`."
        )
    aspects = _config_aspects(config)
    if aspect_name not in aspects or aspects[aspect_name] <= 0:
        raise click.ClickException(
            f"Aspect {aspect_name!r} is not enabled in this project. "
            f"Run `kanon aspect add {target} {aspect_name}` first."
        )
    schema = _aspect_config_schema(aspect_name)
    key, value = _parse_config_pair(pair, schema)

    from kanon._atomic import clear_sentinel, write_sentinel

    aspects_meta = dict(config.get("aspects", {}))
    kit_version = config.get("kit_version", __version__)
    write_sentinel(target / ".kanon", _OP_SET_CONFIG)
    _commit_aspect_meta(
        target, kit_version, aspects_meta, aspect_name, aspects[aspect_name],
        extra_config={key: value},
    )
    clear_sentinel(target / ".kanon")
    click.echo(
        f"Set aspects.{aspect_name}.config.{key} = {value!r} in .kanon/config.yaml."
    )





# --- fidelity lock ---


@main.group()
def fidelity() -> None:
    """Fidelity lock management."""


@fidelity.command("update")
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
def fidelity_update(target: Path) -> None:
    """Generate or refresh .kanon/fidelity.lock."""
    from kanon._atomic import atomic_write_text, clear_sentinel, write_sentinel

    target = target.resolve()
    _check_pending_recovery(target)
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

    write_sentinel(target / ".kanon", _OP_FIDELITY_UPDATE)
    atomic_write_text(lock_path, "".join(lines))
    clear_sentinel(target / ".kanon")
    click.echo(f"Wrote {lock_path} with {len(entries)} entries.")


@main.group()
def graph() -> None:
    """Cross-link graph queries (orphans, rename)."""


@graph.command("orphans")
@click.option(
    "--type",
    "namespace",
    type=click.Choice(list(ORPHAN_CANDIDATE_NAMESPACES)),
    default=None,
    help="Filter to one namespace (default: all candidate namespaces).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Repo root (default: current directory).",
)
def graph_orphans(
    namespace: str | None,
    output_format: str,
    target: Path | None,
) -> None:
    """Report unreferenced nodes in the cross-link graph.

    Per docs/specs/spec-graph-orphans.md: a node is an orphan when no
    other live artifact in the graph cites it. Deferred and superseded
    specs are excluded both as inbound-edge sources and as orphan
    candidates. Exit code is always 0 — orphans are informational.
    """
    root = Path(target).resolve() if target else Path.cwd()
    graph_data = build_graph(root)
    orphans = compute_orphans(graph_data, filter_namespace=namespace)

    if output_format == "json":
        payload = {
            "orphans": {
                ns: [
                    {"slug": r.slug, "exempt": r.exempt, "reason": r.reason}
                    for r in rows
                ]
                for ns, rows in orphans.items()
            },
            "status": "ok",
        }
        click.echo(json.dumps(payload, indent=2))
        return

    # Text mode: one line per orphan, "<namespace>: <slug>" with optional
    # "(orphan-exempt: <reason>)" suffix when the node opts out.
    total = sum(len(v) for v in orphans.values())
    if total == 0:
        click.echo("No orphans found.")
        return
    for ns in sorted(orphans):
        for record in orphans[ns]:
            line = f"{ns}: {record.slug}"
            if record.exempt:
                reason = record.reason or "no reason given"
                line += f" (orphan-exempt: {reason})"
            click.echo(line)


@graph.command("rename")
@click.option(
    "--type",
    "namespace",
    required=True,
    help="Slug namespace (one of: principle, persona, spec, aspect, "
         "capability, inv-anchor, adr).",
)
@click.argument("old_slug")
@click.argument("new_slug")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the rewrite plan without writing any files.",
)
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Repo root (default: current directory).",
)
def graph_rename(
    namespace: str,
    old_slug: str,
    new_slug: str,
    dry_run: bool,
    target: Path | None,
) -> None:
    """Atomically rename a slug across the cross-link graph.

    Per docs/specs/spec-graph-rename.md: rewrites every frontmatter
    citation, markdown link target, and INV-anchor that names the slug,
    in one atomic transaction protected by an ops-manifest at
    .kanon/graph-rename.ops (ADR-0027). The CLI fleet
    (check_foundations, check_invariant_ids, check_verified_by,
    check_links, check_kit_consistency, kanon verify) is run as a
    self-check before the sentinel is cleared.

    Use --dry-run to preview the rewrite plan without modifying anything.
    """
    from kanon._rename import perform_rename

    root = Path(target).resolve() if target else Path.cwd()
    if not dry_run:
        _check_pending_recovery(root)
    report = perform_rename(root, namespace, old_slug, new_slug, dry_run=dry_run)
    if dry_run:
        click.echo(report["plan"])
        click.echo(f"-- {report['files']} file(s) would change --")
        return
    click.echo(f"Renamed {old_slug} -> {new_slug} ({report['files']} file(s) updated).")


# --- Phase A.7: resolutions + contracts CLI verbs ---


@main.group()
def resolutions() -> None:
    """Resolutions management — replay, stale-check, explain (per ADR-0039)."""


@resolutions.command("check")
@click.option(
    "--target",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    help="Project root containing .kanon/resolutions.yaml.",
)
def resolutions_check(target: Path) -> None:
    """Pin-check phase only — report staleness without executing realizations.

    Per ADR-0039 INV-resolutions-stale-fails. Cheap; suitable for IDE
    integration and the development loop before invoking `kanon preflight`.
    """
    from kanon._resolutions import stale_check

    target = target.resolve()
    report = stale_check(target)
    out: dict[str, Any] = {
        "target": str(target),
        "errors": [
            {
                k: v
                for k, v in {
                    "code": e.code,
                    "contract": e.contract,
                    "path": e.path,
                    "reason": e.reason,
                }.items()
                if v is not None
            }
            for e in report.errors
        ],
        "status": "ok" if report.ok else "fail",
    }
    click.echo(json.dumps(out, indent=2))
    if not report.ok:
        sys.exit(1)


@resolutions.command("explain")
@click.argument("contract_id")
@click.option(
    "--target",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
)
def resolutions_explain(contract_id: str, target: Path) -> None:
    """Phase A.7 stub: contract registry not yet populated.

    The full implementation (per ADR-0039 design's `kanon resolutions explain`
    verb) requires an aspect to ship `realization-shape:` frontmatter on at
    least one contract; no aspect ships contracts today. This stub surfaces
    the verb in the CLI and reports its deferral.
    """
    click.echo(
        json.dumps(
            {
                "contract": contract_id,
                "target": str(target.resolve()),
                "status": "deferred",
                "reason": (
                    "Phase A.7 stub: contract registry not yet populated. "
                    "Wiring lands when an aspect ships a realization-shape contract."
                ),
            },
            indent=2,
        )
    )


@main.group()
def contracts() -> None:
    """Contract bundle management — validate (per ADR-0041)."""


@contracts.command("validate")
@click.argument(
    "bundle_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
def contracts_validate(bundle_path: Path) -> None:
    """Pre-flight a publisher's bundle: dialect, realization-shapes, composition.

    Per ADR-0041 design `docs/design/dialect-grammar.md` §"The
    `kanon contracts validate <bundle-path>` walk". Exits 1 on errors.
    """
    import yaml

    from kanon._composition import ContractRef, compose
    from kanon._dialects import validate_dialect_pin
    from kanon._realization_shape import parse_realization_shape

    bundle_path = bundle_path.resolve()
    manifest_path = bundle_path / "manifest.yaml"
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not manifest_path.is_file():
        errors.append(
            {"code": "missing-manifest", "detail": f"no manifest.yaml at {bundle_path}"}
        )
        # Per JSON-schema parity with the success path: missing-manifest
        # branch carries `dialect: null` and `contracts: []` so consumers
        # don't have to special-case the failure shape.
        click.echo(
            json.dumps(
                {
                    "bundle": str(bundle_path),
                    "dialect": None,
                    "contracts": [],
                    "errors": errors,
                    "warnings": warnings,
                    "status": "fail",
                },
                indent=2,
            )
        )
        sys.exit(1)

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    dialect_pin = manifest.get("kanon-dialect") if isinstance(manifest, dict) else None
    try:
        validate_dialect_pin(dialect_pin, source=str(manifest_path))
    except click.ClickException as exc:
        # DialectPinError carries spec-aligned `code` (missing-dialect-pin
        # | unknown-dialect) per docs/specs/dialect-grammar.md INV 1-2.
        # Fallback to "dialect-invalid" preserves backward-compat for any
        # plain ClickException raised by future code paths.
        code = getattr(exc, "code", "dialect-invalid")
        errors.append({"code": code, "detail": exc.message})

    contract_refs: list[ContractRef] = []
    if isinstance(manifest, dict):
        for c in manifest.get("contracts") or []:
            if not isinstance(c, dict):
                errors.append(
                    {"code": "invalid-contract-entry", "detail": str(c)}
                )
                continue
            cid = c.get("contract-id")
            if "realization-shape" not in c:
                errors.append(
                    {
                        "code": "missing-realization-shape",
                        "contract": cid,
                    }
                )
            elif dialect_pin in ("2026-05-01",):
                try:
                    parse_realization_shape(
                        c["realization-shape"], dialect=dialect_pin, source=cid
                    )
                except click.ClickException as exc:
                    # ShapeParseError carries spec-aligned `code:
                    # invalid-realization-shape`. Fallback preserves backcompat.
                    code = getattr(exc, "code", "invalid-realization-shape")
                    errors.append(
                        {
                            "code": code,
                            "contract": cid,
                            "detail": exc.message,
                        }
                    )
            if isinstance(cid, str) and isinstance(c.get("surface"), str):
                contract_refs.append(
                    ContractRef(
                        contract_id=cid,
                        surface=c["surface"],
                        before=tuple(c.get("before") or ()),
                        after=tuple(c.get("after") or ()),
                        replaces=tuple(c.get("replaces") or ()),
                    )
                )
    surfaces = {c.surface for c in contract_refs}
    # Per docs/specs/dialect-grammar.md INV 5-6: composition-cycle and
    # replacement-cycle are both hard errors; ambiguous-composition is a warn.
    _CYCLE_ERROR_CODES = {"composition-cycle", "replacement-cycle"}
    for surface in sorted(surfaces):
        _ordering, findings = compose(contract_refs, surface=surface)
        for f in findings:
            entry = {"code": f.code, "surface": f.surface, "detail": f.detail}
            if f.code in _CYCLE_ERROR_CODES:
                errors.append(entry)
            else:
                warnings.append(entry)

    out = {
        "bundle": str(bundle_path),
        "dialect": dialect_pin,
        "contracts": [c.contract_id for c in contract_refs],
        "errors": errors,
        "warnings": warnings,
        "status": "ok" if not errors else "fail",
    }
    click.echo(json.dumps(out, indent=2))
    if errors:
        sys.exit(1)


@main.command("resolve")
@click.option(
    "--target",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
)
@click.option(
    "--contracts",
    "contracts_arg",
    default=None,
    help="Comma-separated contract IDs to resolve (default: all enabled).",
)
def resolve_cmd(target: Path, contracts_arg: str | None) -> None:
    """Phase A.7 stub: harness integration not yet wired.

    Per ADR-0039 design's `kanon resolve` verb: invoke the consumer's installed
    LLM harness, present it the contract prose, and accept the YAML response.
    Real harness integration lands when the substrate's harness adapter API is
    designed (a future ADR). This stub surfaces the verb and emits the
    structured prompt skeleton a future harness adapter will receive.
    """
    target = target.resolve()
    requested = (
        [c.strip() for c in contracts_arg.split(",") if c.strip()]
        if contracts_arg
        else []
    )
    click.echo(
        json.dumps(
            {
                "target": str(target),
                "contracts_requested": requested or "all-enabled",
                "status": "deferred",
                "reason": (
                    "Phase A.7 stub: harness integration not yet wired. "
                    "A future ADR designs the harness-adapter API for invoking "
                    "the consumer's LLM (Claude Code, Cursor, etc.) with "
                    "contract prose and accepting the YAML resolution output."
                ),
            },
            indent=2,
        )
    )


# --- Phase A.9: kanon migrate v0.3 → v0.4 (deprecated-on-arrival) ---


_RETIRED_TESTING_CONFIG_KEYS = (
    "test_cmd",
    "lint_cmd",
    "typecheck_cmd",
    "format_cmd",
    "coverage_floor",
)


@main.command("migrate")
@click.option(
    "--target",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    help="Project root containing .kanon/config.yaml.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print proposed changes without writing.",
)
def migrate(target: Path, dry_run: bool) -> None:
    """Migrate `.kanon/config.yaml` from v3 (kit-shape) to v4 (substrate-shape).

    Deprecated-on-arrival per ADR-0045 — this is a one-time migration tool for
    historical v0.3 consumers; it will be removed before v1.0. The kanon repo
    itself was migrated manually in Phase 0.5; this verb exists for any
    consumer resurrecting an old v0.3 install.
    """
    import yaml

    from kanon._atomic import atomic_write_text

    deprecation_warning = (
        "`kanon migrate` is deprecated-on-arrival per ADR-0045; "
        "it will be removed before v1.0."
    )

    target = target.resolve()
    config_path = target / ".kanon" / "config.yaml"
    if not config_path.is_file():
        raise click.ClickException(
            f"no .kanon/config.yaml at {target}; nothing to migrate."
        )

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise click.ClickException(
            f"failed to parse {config_path}: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise click.ClickException(
            f"{config_path}: top-level must be a mapping (got {type(config).__name__})."
        )

    changes: list[str] = []

    schema_version = config.get("schema-version")
    if schema_version == 4:
        click.echo(
            json.dumps(
                {
                    "target": str(target),
                    "status": "noop",
                    "reason": "already v4",
                    "deprecation": deprecation_warning,
                },
                indent=2,
            )
        )
        return

    # Forward-version + type guard: a v5+ config is from a future kanon and
    # this migrate verb does not know how to forward-port. Refuse loudly
    # rather than silently mangling the file (e.g., adding v4 fields beneath
    # a v5 schema header — a hybrid that no reader understands). Type-check
    # first because YAML quirks (`schema-version: "5"` parses to str;
    # `schema-version: 5.0` parses to float) bypass a naive isinstance(int)
    # check; bools are excluded because `True`/`False` are technically int
    # subclasses in Python.
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
                f"to migrate v3 → v4. To migrate forward from v{schema_version}, install "
                f"a newer kanon-substrate."
            )

    # v3 → v4 augmentation: prepend v4 fields.
    if "schema-version" not in config:
        config["schema-version"] = 4
        changes.append("added schema-version: 4")
    if "kanon-dialect" not in config:
        config["kanon-dialect"] = "2026-05-01"
        changes.append('added kanon-dialect: "2026-05-01"')
    if "provenance" not in config:
        config["provenance"] = [
            {
                "recipe": "manual-migration",
                "publisher": "kanon-migrate",
                "recipe-version": "1.0",
                "applied_at": _now_iso(),
            }
        ]
        changes.append("added provenance entry")

    # Strip retired kanon-testing config keys (Phase A.4 deletion).
    aspects = config.get("aspects") or {}
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

    out = {
        "target": str(target),
        "status": "would-write" if dry_run else "written",
        "changes": changes,
        "deprecation": deprecation_warning,
    }

    if not dry_run:
        # Move v4 fields to top of file via a re-assembled ordered dict.
        reordered: dict[str, Any] = {}
        for key in ("schema-version", "kanon-dialect", "provenance"):
            if key in config:
                reordered[key] = config[key]
        for key, value in config.items():
            if key not in reordered:
                reordered[key] = value
        atomic_write_text(
            config_path,
            yaml.safe_dump(reordered, sort_keys=False),
        )

    click.echo(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
