---
status: accepted
date: 2026-04-22
realizes:
  - P-prose-is-code
  - P-self-hosted-bootstrap
stressed_by:
  - solo-engineer
  - platform-team
fixtures_deferred: "Pytest CLI test suite lands in Phase D of v0.1 bootstrap (tests/test_cli.py)"
---
# Spec: `agent-sdd` CLI surface

## Intent

Provide a single `agent-sdd` command with a small set of subcommands that cover the full consumer lifecycle: adopt the kit, keep it up to date, change tier, verify the current state.

## Invariants

1. **Subcommands.** The CLI exposes exactly: `init`, `upgrade`, `verify`, `tier`, `--version`. No other top-level subcommands are added in v0.1.
2. **`init <target> [--tier N] [--force] [--learner-id ID]`** — scaffolds a new project at `<target>`. Default tier is 1. `--force` overwrites an existing `.agent-sdd/` directory; without it, an existing `.agent-sdd/` causes an error.
3. **`upgrade <target>`** — replaces `<target>/.agent-sdd/` with the installed kit's templates atomically, preserving consumer content outside `.agent-sdd/`. Uses the copy-to-tmp + fsync-dir + swap + fsync-dir pattern ported from Sensei's ADR-0004. A failed upgrade never corrupts an existing `.agent-sdd/`.
4. **`verify <target>`** — checks the consumer project against its declared tier (from `.agent-sdd/config.yaml`). Reports missing required files, failed foundation backreferences, failed link validations, AGENTS.md marker imbalance, and (warning-level) stale model-version compatibility declarations. Exit 0 on clean, non-zero otherwise.
5. **`tier set <target> <N>`** — see `tier-migration.md` spec. Exit 0 on success, non-zero on malformed target or invalid tier.
6. **`--version`** — prints `agent_sdd.__version__` and exits 0.
7. **Exit codes.** 0 on success. 1 on generic error / malformed input. 2 on contract violation the CLI caught (e.g., upgrading a target where `.agent-sdd/config.yaml` is missing). 3+ reserved for future use.
8. **Atomicity.** Every command that modifies files is atomic — the target repo is either in the pre-command state or the post-command state, never partial. Implemented via the tmp-dir swap pattern.
9. **Consumer-friendly errors.** Missing `.agent-sdd/config.yaml`, broken shim targets, or tier mismatches emit single-line human-readable messages with the offending path.

## Rationale

The CLI is deliberately small. Every additional subcommand is a contract; every contract is something consumers depend on; every dependency is a future compatibility constraint. Five is the minimum that covers the lifecycle.

The atomic-replace contract is load-bearing: users adopt the kit on projects where an interrupted command leaving `.agent-sdd/` corrupted would be catastrophic (their existing project content is adjacent). The pattern is proven by Sensei and must be preserved.

## Out of Scope

- Project discovery commands (`agent-sdd list-projects`, etc.) — not in v0.1.
- Ambiguity-budget invocations (deferred to `ambiguity-budget.md`).
- Automated fixture re-running (deferred per ADR-0005 and future specs).
- Machine-readable output formats (JSON) for every subcommand — only `verify` emits a structured report in v0.1, and its shape is documented in `verification-contract.md`.

## Decisions

See ADR-0001 (distribution), ADR-0008 (tier set semantics).
