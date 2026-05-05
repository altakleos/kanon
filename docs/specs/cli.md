---
status: accepted
design: "Follows ADR-0024"
date: 2026-05-01
realizes:
  - P-prose-is-code
  - P-self-hosted-bootstrap
stressed_by:
  - solo-engineer
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/test_atomic.py
invariant_coverage:
  INV-cli-subcommands:
    - tests/test_cli.py::test_init_scaffolds_all_required_files
    - tests/test_cli.py::test_upgrade_bumps_version
    - tests/test_cli.py::test_init_verify_returns_ok
    - tests/test_cli_aspect.py::test_tier_set_idempotent
    - tests/test_cli_aspect.py::test_aspect_add
    - tests/test_cli_aspect.py::test_aspect_remove
    - tests/test_cli_fidelity.py::test_fidelity_update_creates_lock
    - tests/test_aspect_config.py::test_set_config_idempotent_apart_from_timestamp
    - tests/test_graph_orphans.py::test_inv1_cli_text_default_no_orphans
    - tests/test_graph_rename.py::test_inv1_type_required
  INV-cli-init:
    - tests/test_cli.py::test_init_scaffolds_all_required_files
    - tests/test_cli.py::test_init_force_overwrites
    - tests/test_cli_aspect.py::test_init_with_aspects_flag
    - tests/test_cli.py::test_init_rejects_existing_without_force
  INV-cli-init-profile:
    - tests/test_cli.py::test_profile_solo_enables_only_sdd
    - tests/test_cli.py::test_profile_team_enables_five_aspects
    - tests/test_cli.py::test_profile_all_uses_default_depths
    - tests/test_cli.py::test_profile_max_uses_max_depths
    - tests/test_cli.py::test_profile_full_is_rejected
  INV-cli-init-agents-md-merge:
    - tests/test_cli.py::test_init_writes_full_agents_md_when_absent
    - tests/test_cli.py::test_init_refreshes_marker_bodies_when_present
    - tests/test_cli.py::test_init_prepends_kit_content_when_no_markers
  INV-cli-upgrade:
    - tests/test_cli.py::test_upgrade_bumps_version
    - tests/test_cli.py::test_upgrade_already_current
  INV-cli-verify:
    - tests/test_cli.py::test_init_verify_returns_ok
    - tests/test_cli_verify.py::test_verify_fails_on_missing_file
    - tests/test_cli_verify.py::test_verify_marker_imbalance
  INV-cli-tier-set:
    - tests/test_cli_aspect.py::test_tier_set_idempotent
  INV-cli-aspect-group:
    - tests/test_cli_aspect.py::test_aspect_add
    - tests/test_cli_aspect.py::test_aspect_remove
    - tests/test_cli_aspect.py::test_aspect_set_depth
    - tests/test_cli_aspect.py::test_aspect_list
    - tests/test_aspect_config.py::test_set_config_idempotent_apart_from_timestamp
  INV-cli-fidelity-group:
    - tests/test_cli_fidelity.py::test_fidelity_update_creates_lock
  INV-cli-graph-group:
    - tests/test_graph_orphans.py::test_inv1_cli_text_default_no_orphans
    - tests/test_graph_rename.py::test_inv1_type_required
  INV-cli-version-flag:
    - tests/test_cli.py::test_version_flag
  INV-cli-exit-codes:
    - tests/test_cli.py::test_init_rejects_existing_without_force
    - tests/test_cli.py::test_init_verify_returns_ok
  INV-cli-atomicity:
    - tests/test_atomic.py::test_happy_path
    - tests/test_atomic.py::test_crash_on_replace_leaves_original_untouched
    - tests/test_atomic.py::test_fsyncs_parent_directory
    - tests/test_atomic.py::test_sentinel_write_and_read
    - tests/test_atomic.py::test_sentinel_clear
  INV-cli-consumer-friendly-errors:
    - tests/test_cli.py::test_init_rejects_existing_without_force
    - tests/test_cli.py::test_upgrade_not_a_kanon_project
  INV-cli-posix-only:
    - pyproject.toml
    - README.md
    - tests/test_atomic.py::test_fsyncs_parent_directory
  INV-cli-preflight:
    - tests/test_preflight.py::test_preflight_cli_commit_stage
    - tests/test_preflight.py::test_preflight_cli_failing_check
    - tests/test_preflight.py::test_preflight_release_requires_tag
  INV-cli-release:
    - tests/test_e2e_lifecycle.py::test_release_lifecycle
  INV-cli-resolve:
    - tests/test_cli_resolutions_contracts.py::test_resolve_emits_deferred_status
  INV-cli-resolutions-group:
    - tests/test_cli_resolutions_contracts.py::test_resolutions_check_missing_file_exits_zero
    - tests/test_cli_resolutions_contracts.py::test_resolutions_explain_emits_deferred_status
  INV-cli-contracts-group:
    - tests/test_cli_resolutions_contracts.py::test_contracts_validate_missing_manifest_errors
    - tests/test_cli_resolutions_contracts.py::test_contracts_validate_clean_empty_bundle_ok
  INV-cli-gates-group:
    - tests/test_declarative_gates.py::test_discovers_gates_from_frontmatter
---
# Spec: `kanon` CLI surface

## Intent

Provide a single `kanon` command with subcommands that cover the full consumer lifecycle: adopt the kit, keep it up to date, manage aspects and depths, verify the current state. The surface is deliberately small — every subcommand is a contract.

## Invariants

<!-- INV-cli-subcommands -->
1. **Subcommands.** The CLI exposes these top-level entries: `init`, `upgrade`, `verify`, `preflight`, `release`, `resolve`, `tier` (back-compat group), `aspect` (group), `fidelity` (group), `graph` (group), `resolutions` (group), `contracts` (group), `gates` (group), and `--version`. The `tier` group contains `set`. The `aspect` group contains `list`, `info`, `add`, `remove`, `set-depth`, `set-config`. The `fidelity` group contains `update`. The `graph` group contains `orphans`, `rename`, `impact`. The `resolutions` group contains `check`, `explain`. The `contracts` group contains `validate`. The `gates` group contains `check`, `list`.
<!-- INV-cli-init -->
2. **`init <target> [--tier N] [--aspects SPEC] [--profile NAME] [--lite] [--force] [--harness NAME] [--quiet]`** — scaffolds a new project at `<target>`. Without flags, every aspect in the manifest's `defaults:` set is scaffolded at depth 1 (per ADR-0035). `--aspects` accepts comma-separated `aspect:depth` pairs (e.g., `sdd:2,worktrees:1`). `--tier N` is a uniform aspect-depth raise — every aspect in `defaults:` is raised to `min(N, max-depth)` (ADR-0035). `--profile NAME` selects a preset bundle (see INV-cli-init-profile). `--lite` is sugar for `kanon-sdd:0`. `--tier`, `--aspects`, `--profile`, and `--lite` are mutually exclusive. `--force` overwrites an existing `.kanon/` directory; without it, an existing `.kanon/` causes an error. `--harness` (repeatable) selects which harness shims to write; defaults to auto-detection from existing config directories, falling back to `CLAUDE.md` only. `--quiet` / `-q` suppresses the banner and the trailing "Next steps" advisory.
<!-- INV-cli-init-profile -->
3. **`--profile` profile names and depths.** The `--profile` flag accepts exactly one of: `solo` (`kanon-sdd:1`), `team` (`kanon-sdd:1`, `kanon-testing:1`, `kanon-security:1`, `kanon-deps:1`, `kanon-worktrees:1`), `all` (every kit-shipped `kanon-*` aspect at its `default-depth`), and `max` (every kit-shipped `kanon-*` aspect at the upper end of its `depth-range`). Any other value is a CLI error with a one-line message listing the four accepted values. Profile depths are strictly closed-form: a future `default-depth` change in the manifest changes `all`'s output but never `solo` or `team`'s, which name aspect-depth pairs explicitly. The pre-v0.3.0a8 name `full` is removed (no deprecation period — kanon has no public consumers yet); `kanon init --profile full` is rejected with the standard click choice error.
<!-- INV-cli-init-agents-md-merge -->
4. **`init`'s `AGENTS.md` write semantics.** When `kanon init` runs against `<target>`, the `AGENTS.md` write follows three branches by precedence:
   - **Absent.** The full kit-rendered `AGENTS.md` (per scaffold-v2 INV-9) is written.
   - **Existing, has at least one `<!-- kanon:begin:<section> -->` marker.** Kit-managed marker bodies are refreshed; content outside markers is preserved byte-for-byte. Same merge primitive `kanon upgrade` uses — `init` and `upgrade` converge on this branch.
   - **Existing, no markers.** Existing prose is treated as project-author content and *prepended* with the full kit-rendered `AGENTS.md`, separated by a `## Project context` H2. The kit content sits at the top of the file so the hard-gates table retains enforcement proximity (per [ADR-0010](../decisions/0010-protocol-layer.md) / [ADR-0034](../decisions/0034-routing-index-agents-md.md)). The existing prose is preserved verbatim under the H2.

   `--force` is not required for any of these branches; init never destroys existing user-authored prose. See [ADR-0038](../decisions/0038-init-merge-into-existing-agents-md.md).
<!-- INV-cli-upgrade -->
5. **`upgrade <target>`** — re-renders AGENTS.md sections, kit.md, and harness shims from the installed kit's templates, preserving consumer content outside kanon-managed markers. Migrates legacy config formats (v1 → v2, flat protocols → namespaced). Each file is written atomically; `config.yaml` is written last as the commit marker. A failed upgrade never corrupts an existing file — see INV-cli-atomicity.
<!-- INV-cli-verify -->
6. **`verify <target>`** — checks the consumer project against its declared aspects and depths (from `.kanon/config.yaml`). Reports: missing required files, AGENTS.md marker imbalance, unknown aspects (warning), fidelity lock staleness (at sdd depth ≥ 2), and invariant coverage gaps (at sdd depth ≥ 2). Emits a JSON report to stdout and a human summary to stderr. Exit 0 on clean, non-zero otherwise.
<!-- INV-cli-tier-set -->
7. **`tier set <target> <N>`** — back-compatibility sugar for `aspect set-depth <target> sdd <N>`. See `tier-migration.md` spec. Exit 0 on success, non-zero on malformed target or invalid tier.
<!-- INV-cli-aspect-group -->
8. **`aspect` group.** `list` shows all available aspects with stability and depth ranges. `info <name>` shows detail for one aspect. `add <target> <name>` enables an aspect at its default depth, validating dependencies. `remove <target> <name>` disables an aspect, checking for dependents. `set-depth <target> <name> <N>` changes an aspect's depth within its declared range. `set-config <target> <name> <key>=<value>` sets one config value on an enabled aspect. See `aspects.md` and `aspect-config.md` specs for invariants governing aspect lifecycle and configuration.
<!-- INV-cli-fidelity-group -->
9. **`fidelity` group.** `update <target>` recomputes the fidelity lock (`.kanon/fidelity.lock`) from current spec and fixture SHAs. See `fidelity-lock.md` spec.
<!-- INV-cli-graph-group -->
10. **`graph` group.** `orphans [--type <namespace>] [--format json|text] [--target DIR]` reports unreferenced nodes in the cross-link graph. `rename --type <namespace> <old> <new> [--dry-run] [--target DIR]` atomically renames a slug across every artifact that references it. `impact [--target DIR] [--format json|text]` shows downstream nodes affected by changes to a given node. See `spec-graph-orphans.md` and `spec-graph-rename.md` for behavioral invariants.
<!-- INV-cli-version-flag -->
11. **`--version`** — prints `kanon.__version__` and exits 0.
<!-- INV-cli-exit-codes -->
12. **Exit codes.** 0 on success. 1 on generic error / malformed input. 2 on contract violation the CLI caught (e.g., upgrading a target where `.kanon/config.yaml` is missing). 3+ reserved for future use.
<!-- INV-cli-atomicity -->
13. **Atomicity.** Every file write is individually atomic via write-to-tmp + fsync + `os.replace()` + fsync parent directory. Multi-file commands are crash-consistent, not instantaneous: a `.kanon/.pending` sentinel is written before the first mutation and cleared after the last; if present on the next invocation, the user is notified to re-run the same command, and idempotency guarantees the re-run completes the operation. All mutating commands are idempotent. `config.yaml` is always written last as the commit marker. See ADR-0024.
<!-- INV-cli-consumer-friendly-errors -->
14. **Consumer-friendly errors.** Missing `.kanon/config.yaml`, unknown aspects, depth-range violations, and dependency conflicts emit single-line human-readable messages with the offending path or value.
<!-- INV-cli-preflight -->
15. **`preflight <target> [--stage commit|push|release] [--tag TAG] [--fail-fast]`** — runs staged local validation: first `kanon verify`, then consumer-configured checks for the given stage. Outputs per-check results to stderr and a JSON summary to stdout. Exit 0 if all checks pass. See `preflight.md` spec.
<!-- INV-cli-release -->
16. **`release <target> --tag TAG [--dry-run]`** — gates a release tag on preflight checks (requires `kanon-release` aspect at depth ≥ 2). Validates tag format, checks clean working tree, runs `preflight --stage release`, then creates an annotated git tag. `--dry-run` runs preflight without creating the tag.
<!-- INV-cli-resolve -->
17. **`resolve <target>`** — invokes the consumer's LLM harness to resolve open contracts. Phase A.7 stub: currently emits a deferred-status JSON message.
<!-- INV-cli-resolutions-group -->
18. **`resolutions` group.** `check <target>` validates existing resolution records (quadruple-pin, staleness, evidence-grounding). `explain <target> <contract-id>` explains a contract's resolution status. Phase A.7 stub for `explain`.
<!-- INV-cli-contracts-group -->
19. **`contracts` group.** `validate <target>` validates contract definitions against their schemas.
<!-- INV-cli-gates-group -->
20. **`gates` group.** `check <target>` discovers active hard gates from protocol frontmatter and evaluates their check commands (or reports `judgment` status for gates without a check command). `list <target>` lists all active gates with their priorities and labels.
<!-- INV-cli-posix-only -->
21. **POSIX-only.** The `kanon` CLI assumes a POSIX filesystem (Linux, macOS) for its atomic-write primitives (write-to-tmp + `fsync` of parent directory + `rename`). Windows is not supported. The `pyproject.toml` `classifiers` and the README quickstart record this constraint.

## Rationale

The CLI surface grows only when a new lifecycle verb is needed. The `aspect` group was added when aspects subsumed tiers (ADR-0012); `fidelity` was added for spec-SHA drift detection (ADR-0019). Each group is a contract — additions require a spec amendment.

The crash-consistent atomicity model (ADR-0024) replaces the original tmp-dir swap aspiration. True instantaneous multi-file atomicity is impossible on POSIX when files span multiple directories (AGENTS.md is in the project root per ADR-0003; `.kanon/` is a subdirectory). The sentinel + idempotent-rerun model provides automatic recovery with zero user intervention.

## Out of Scope

- Project discovery commands (`kanon list-projects`, etc.).
- Machine-readable output formats (JSON) for every subcommand — only `verify` emits a structured report, documented in `verification-contract.md`.
- Automated fixture re-running (deferred per ADR-0005).

## Decisions

See ADR-0001 (distribution), ADR-0008 (tier set semantics), ADR-0012 (aspect model), ADR-0024 (crash-consistent atomicity).
