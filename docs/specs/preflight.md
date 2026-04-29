---
status: draft
date: 2026-04-28
realizes:
  - P-prose-is-code
stressed_by:
  - solo-engineer
fixtures_deferred: "Spec covers new CLI command; fixtures will be added with implementation"
---
# Spec: `kanon preflight` — staged local validation

## Intent

Provide a single CLI command that runs escalating checks before commit, push, or release — catching CI failures locally before they reach the remote. The command composes `kanon verify` (structural) with consumer-configured tool invocations (lint, tests, typecheck, release gates). Each stage is a strict superset of the previous.

## Invariants

<!-- INV-preflight-stages -->
1. **Three stages, strict superset.** `kanon preflight` supports three stages: `commit`, `push`, and `release`. Each stage includes all checks from the previous stage plus its own. `commit` is the default when no `--stage` flag is given.

<!-- INV-preflight-verify-first -->
2. **Verify is always first.** Every stage begins by running `kanon verify .` (structural checks). If verify fails, preflight stops and reports the structural errors. This preserves verify's role as the fast, always-safe baseline.

<!-- INV-preflight-consumer-configured -->
3. **Consumer-configured commands.** Checks beyond verify are shell commands declared in `.kanon/config.yaml` under `preflight-stages:`. Each entry has `run:` (the command) and `label:` (a human-readable name for reporting). Commands are language-agnostic strings — the consumer knows their toolchain.

<!-- INV-preflight-aspect-defaults -->
4. **Aspect-contributed defaults.** Aspects may declare `preflight:` entries in their sub-manifest `depth-N:` blocks. These are default checks contributed when the aspect is enabled at that depth. Consumer entries in `preflight-stages:` override aspect defaults by label (same label = consumer wins) or append (new label = added).

<!-- INV-preflight-testing-config -->
5. **Testing config keys.** The `kanon-testing` aspect gains four config-schema keys: `test_cmd`, `lint_cmd`, `typecheck_cmd`, `format_cmd`. These are shell command strings. When non-empty, they are contributed as aspect defaults to the appropriate preflight stages (format/lint → commit, test/typecheck → push).

<!-- INV-preflight-output -->
6. **Structured output.** Preflight prints per-check results to stderr (label, command, pass/fail, duration) and a JSON summary to stdout: `{stage, checks: [{label, command, passed, duration_s}], passed: bool}`. Exit 0 if all checks pass, non-zero otherwise.

<!-- INV-preflight-release-tag -->
7. **Release stage requires `--tag`.** `kanon preflight . --stage release --tag vX.Y.Z` passes the tag value to release-stage commands via the `$TAG` environment variable. Omitting `--tag` with `--stage release` is an error.

<!-- INV-preflight-verify-unchanged -->
8. **Verify contract unchanged.** `kanon verify` remains structural-only per verification-contract INV-9. Preflight is a separate command that composes verify; it does not extend or weaken verify's contract.

<!-- INV-preflight-fail-fast -->
9. **Fail-fast optional.** `--fail-fast` stops on the first failing check. Default: run all checks in the stage and report all failures.

## Rationale

Today's session produced 5 CI failures before a release succeeded. Three were locally catchable: mypy not run, process gates not run, stale wheel checker. The existing `kanon verify` is deliberately structural-only (INV-9). A separate `preflight` command fills the gap between "is the project shape valid?" (verify) and "will CI pass?" (preflight) without contaminating verify's contract.

The stage model (commit ⊂ push ⊂ release) maps to the developer workflow: fast checks on commit, thorough checks before push, exhaustive checks before tagging. Each stage adds checks; none removes them.

Consumer-configured commands keep the kit language-agnostic. The testing aspect's `*_cmd` config keys provide a natural home for tool declarations that preflight reads. Aspects contributing defaults via manifests means enabling `kanon-security` at depth 2 automatically adds the security scanner to the push stage — zero consumer config needed for kit-shipped checks.

## Out of Scope

- Git hook installation (consumers wire hooks manually or via pre-commit/lefthook).
- Parallel check execution (sequential in v1; parallel deferred).
- File-change-aware check filtering (run all checks in the stage, not just affected files).
- Auto-detection of tools from project config files (consumer declares commands explicitly).

## Decisions

Extends the CLI spec (new top-level command). Does not amend the verification-contract spec (verify stays structural). Extends the testing spec (new config-schema keys). Extends the release spec (release-checklist references preflight when available).
