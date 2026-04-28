---
status: accepted
design: "Follows ADR-0024"
date: 2026-04-25
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
    - tests/test_cli.py::test_tier_set_idempotent
    - tests/test_cli.py::test_aspect_add
    - tests/test_cli.py::test_aspect_remove
    - tests/test_cli.py::test_fidelity_update_creates_lock
    - tests/test_aspect_config.py::test_set_config_idempotent_apart_from_timestamp
    - tests/test_graph_orphans.py::test_inv1_cli_text_default_no_orphans
    - tests/test_graph_rename.py::test_inv1_type_required
  INV-cli-init:
    - tests/test_cli.py::test_init_scaffolds_all_required_files
    - tests/test_cli.py::test_init_force_overwrites
    - tests/test_cli.py::test_init_with_aspects_flag
    - tests/test_cli.py::test_init_rejects_existing_without_force
  INV-cli-upgrade:
    - tests/test_cli.py::test_upgrade_bumps_version
    - tests/test_cli.py::test_upgrade_already_current
  INV-cli-verify:
    - tests/test_cli.py::test_init_verify_returns_ok
    - tests/test_cli.py::test_verify_fails_on_missing_file
    - tests/test_cli.py::test_verify_marker_imbalance
  INV-cli-tier-set:
    - tests/test_cli.py::test_tier_set_idempotent
  INV-cli-aspect-group:
    - tests/test_cli.py::test_aspect_add
    - tests/test_cli.py::test_aspect_remove
    - tests/test_cli.py::test_aspect_set_depth
    - tests/test_cli.py::test_aspect_list
    - tests/test_aspect_config.py::test_set_config_idempotent_apart_from_timestamp
  INV-cli-fidelity-group:
    - tests/test_cli.py::test_fidelity_update_creates_lock
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
---
# Spec: `kanon` CLI surface

## Intent

Provide a single `kanon` command with subcommands that cover the full consumer lifecycle: adopt the kit, keep it up to date, manage aspects and depths, verify the current state. The surface is deliberately small — every subcommand is a contract.

## Invariants

<!-- INV-cli-subcommands -->
1. **Subcommands.** The CLI exposes these top-level entries: `init`, `upgrade`, `verify`, `tier` (back-compat group), `aspect` (group), `fidelity` (group), `graph` (group), and `--version`. The `tier` group contains `set`. The `aspect` group contains `list`, `info`, `add`, `remove`, `set-depth`, `set-config`. The `fidelity` group contains `update`. The `graph` group contains `orphans`, `rename`.
<!-- INV-cli-init -->
2. **`init <target> [--tier N] [--aspects SPEC] [--force]`** — scaffolds a new project at `<target>`. Default tier is 1 (equivalent to `sdd:1`). `--aspects` accepts comma-separated `aspect:depth` pairs (e.g., `sdd:2,worktrees:1`); mutually exclusive with `--tier`. `--force` overwrites an existing `.kanon/` directory; without it, an existing `.kanon/` causes an error.
<!-- INV-cli-upgrade -->
3. **`upgrade <target>`** — re-renders AGENTS.md sections, kit.md, and harness shims from the installed kit's templates, preserving consumer content outside kanon-managed markers. Migrates legacy config formats (v1 → v2, flat protocols → namespaced). Each file is written atomically; `config.yaml` is written last as the commit marker. A failed upgrade never corrupts an existing file — see INV-cli-atomicity.
<!-- INV-cli-verify -->
4. **`verify <target>`** — checks the consumer project against its declared aspects and depths (from `.kanon/config.yaml`). Reports: missing required files, AGENTS.md marker imbalance, unknown aspects (warning), fidelity lock staleness (at sdd depth ≥ 2), and invariant coverage gaps (at sdd depth ≥ 2). Emits a JSON report to stdout and a human summary to stderr. Exit 0 on clean, non-zero otherwise.
<!-- INV-cli-tier-set -->
5. **`tier set <target> <N>`** — back-compatibility sugar for `aspect set-depth <target> sdd <N>`. See `tier-migration.md` spec. Exit 0 on success, non-zero on malformed target or invalid tier.
<!-- INV-cli-aspect-group -->
6. **`aspect` group.** `list` shows all available aspects with stability and depth ranges. `info <name>` shows detail for one aspect. `add <target> <name>` enables an aspect at its default depth, validating dependencies. `remove <target> <name>` disables an aspect, checking for dependents. `set-depth <target> <name> <N>` changes an aspect's depth within its declared range. `set-config <target> <name> <key>=<value>` sets one config value on an enabled aspect. See `aspects.md` and `aspect-config.md` specs for invariants governing aspect lifecycle and configuration.
<!-- INV-cli-fidelity-group -->
7. **`fidelity` group.** `update <target>` recomputes the fidelity lock (`.kanon/fidelity.lock`) from current spec and fixture SHAs. See `fidelity-lock.md` spec.
<!-- INV-cli-graph-group -->
8. **`graph` group.** `orphans [--type <namespace>] [--format json|text] [--target DIR]` reports unreferenced nodes in the cross-link graph. `rename --type <namespace> <old> <new> [--dry-run] [--target DIR]` atomically renames a slug across every artifact that references it. See `spec-graph-orphans.md` and `spec-graph-rename.md` for behavioral invariants.
<!-- INV-cli-version-flag -->
9. **`--version`** — prints `kanon.__version__` and exits 0.
<!-- INV-cli-exit-codes -->
10. **Exit codes.** 0 on success. 1 on generic error / malformed input. 2 on contract violation the CLI caught (e.g., upgrading a target where `.kanon/config.yaml` is missing). 3+ reserved for future use.
<!-- INV-cli-atomicity -->
11. **Atomicity.** Every file write is individually atomic via write-to-tmp + fsync + `os.replace()` + fsync parent directory. Multi-file commands are crash-consistent, not instantaneous: a `.kanon/.pending` sentinel is written before the first mutation and cleared after the last; if present on the next invocation, the user is notified to re-run the same command, and idempotency guarantees the re-run completes the operation. All mutating commands are idempotent. `config.yaml` is always written last as the commit marker. See ADR-0024.
<!-- INV-cli-consumer-friendly-errors -->
12. **Consumer-friendly errors.** Missing `.kanon/config.yaml`, unknown aspects, depth-range violations, and dependency conflicts emit single-line human-readable messages with the offending path or value.
<!-- INV-cli-posix-only -->
13. **POSIX-only.** The `kanon` CLI assumes a POSIX filesystem (Linux, macOS) for its atomic-write primitives (write-to-tmp + `fsync` of parent directory + `rename`). Windows is not supported. The `pyproject.toml` `classifiers` and the README quickstart record this constraint.

## Rationale

The CLI surface grows only when a new lifecycle verb is needed. The `aspect` group was added when aspects subsumed tiers (ADR-0012); `fidelity` was added for spec-SHA drift detection (ADR-0019). Each group is a contract — additions require a spec amendment.

The crash-consistent atomicity model (ADR-0024) replaces the original tmp-dir swap aspiration. True instantaneous multi-file atomicity is impossible on POSIX when files span multiple directories (AGENTS.md is in the project root per ADR-0003; `.kanon/` is a subdirectory). The sentinel + idempotent-rerun model provides automatic recovery with zero user intervention.

## Out of Scope

- Project discovery commands (`kanon list-projects`, etc.).
- Machine-readable output formats (JSON) for every subcommand — only `verify` emits a structured report, documented in `verification-contract.md`.
- Automated fixture re-running (deferred per ADR-0005).

## Decisions

See ADR-0001 (distribution), ADR-0008 (tier set semantics), ADR-0012 (aspect model), ADR-0024 (crash-consistent atomicity).
