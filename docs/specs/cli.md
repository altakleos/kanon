---
status: accepted
date: 2026-04-25
realizes:
  - P-prose-is-code
  - P-self-hosted-bootstrap
stressed_by:
  - solo-engineer
  - platform-team
fixtures_deferred: "Pytest CLI test suite lands in Phase D of v0.1 bootstrap (tests/test_cli.py)"
invariant_coverage:
  INV-cli-posix-only:
    - pyproject.toml
    - README.md
    - tests/test_atomic.py::test_fsyncs_parent_directory
---
# Spec: `kanon` CLI surface

## Intent

Provide a single `kanon` command with a small set of subcommands that cover the full consumer lifecycle: adopt the kit, keep it up to date, change tier, verify the current state.

## Invariants

<!-- INV-cli-subcommands -->
1. **Subcommands.** The CLI exposes exactly: `init`, `upgrade`, `verify`, `tier`, `--version`. No other top-level subcommands are added in v0.1.
<!-- INV-cli-init -->
2. **`init <target> [--tier N] [--force] [--learner-id ID]`** — scaffolds a new project at `<target>`. Default tier is 1. `--force` overwrites an existing `.kanon/` directory; without it, an existing `.kanon/` causes an error.
<!-- INV-cli-upgrade -->
3. **`upgrade <target>`** — replaces `<target>/.kanon/` with the installed kit's templates atomically, preserving consumer content outside `.kanon/`. Uses the copy-to-tmp + fsync-dir + swap + fsync-dir pattern ported from Sensei's ADR-0004. A failed upgrade never corrupts an existing `.kanon/`.
<!-- INV-cli-verify -->
4. **`verify <target>`** — checks the consumer project against its declared tier (from `.kanon/config.yaml`). Reports missing required files, failed foundation backreferences, failed link validations, AGENTS.md marker imbalance, and (warning-level) stale model-version compatibility declarations. Exit 0 on clean, non-zero otherwise.
<!-- INV-cli-tier-set -->
5. **`tier set <target> <N>`** — see `tier-migration.md` spec. Exit 0 on success, non-zero on malformed target or invalid tier.
<!-- INV-cli-version-flag -->
6. **`--version`** — prints `kanon.__version__` and exits 0.
<!-- INV-cli-exit-codes -->
7. **Exit codes.** 0 on success. 1 on generic error / malformed input. 2 on contract violation the CLI caught (e.g., upgrading a target where `.kanon/config.yaml` is missing). 3+ reserved for future use.
<!-- INV-cli-atomicity -->
8. **Atomicity.** Every command that modifies files is atomic — the target repo is either in the pre-command state or the post-command state, never partial. Implemented via the tmp-dir swap pattern.
<!-- INV-cli-consumer-friendly-errors -->
9. **Consumer-friendly errors.** Missing `.kanon/config.yaml`, broken shim targets, or tier mismatches emit single-line human-readable messages with the offending path.
<!-- INV-cli-posix-only -->
10. **POSIX-only.** The `kanon` CLI assumes a POSIX filesystem (Linux, macOS) for its atomic-write primitives (write-to-tmp + `fsync` of parent directory + `rename`). Windows is not supported. The `pyproject.toml` `classifiers` and the README quickstart record this constraint.

## Rationale

The CLI is deliberately small. Every additional subcommand is a contract; every contract is something consumers depend on; every dependency is a future compatibility constraint. Five is the minimum that covers the lifecycle.

The atomic-replace contract is load-bearing: users adopt the kit on projects where an interrupted command leaving `.kanon/` corrupted would be catastrophic (their existing project content is adjacent). The pattern is proven by Sensei and must be preserved.

## Out of Scope

- Project discovery commands (`kanon list-projects`, etc.) — not in v0.1.
- Ambiguity-budget invocations (deferred to `ambiguity-budget.md`).
- Automated fixture re-running (deferred per ADR-0005 and future specs).
- Machine-readable output formats (JSON) for every subcommand — only `verify` emits a structured report in v0.1, and its shape is documented in `verification-contract.md`.

## Decisions

See ADR-0001 (distribution), ADR-0008 (tier set semantics).
