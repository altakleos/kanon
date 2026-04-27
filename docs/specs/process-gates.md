---
status: accepted
date: 2026-04-27
fixtures_deferred: spec is draft; fixtures will be added when status reaches accepted
---

# Spec: Process-Gate CI Enforcement

## Intent

The two most important process gates — plan-before-build and spec-before-design — have no automated enforcement. They rely entirely on audit-trail sentences in agent transcripts, which are only detectable by manual review. A CI script that checks the structural evidence of gate compliance (plan and spec files exist alongside source changes) would catch the most common violation: an agent going straight to code without producing a plan or spec.

The script does not enforce *ordering* (plan came before code) — CI sees the final commit state, not the sequence. It enforces *co-presence*: if source files changed, a plan file must exist; if a new CLI command was added, a spec file must exist.

## Invariants

<!-- INV-process-gates-plan-co-presence -->
1. **Plan co-presence.** When a PR's diff modifies files under `src/` (excluding `__pycache__`, `*.pyc`), the same PR must include or reference a file under `docs/plans/` with `status:` frontmatter set to `done`, `accepted`, or `in-progress`. Violation produces an **error**.

<!-- INV-process-gates-spec-co-presence -->
2. **Spec co-presence.** When a PR's diff adds a new `@cli.command()`, `@cli.group()`, or `@click.command()` decorator in files under `src/`, the same PR must include or reference a file under `docs/specs/` with `status:` set to `accepted` or `provisional`. Violation produces an **error**.

<!-- INV-process-gates-trivial-override -->
3. **Trivial-change override.** A commit trailer `Trivial-change: <reason>` on any commit in the PR exempts that PR from the plan co-presence check (invariant 1). The trailer value must be non-empty. The spec co-presence check (invariant 2) is never exemptable — new CLI commands always need a spec.

<!-- INV-process-gates-reference-semantics -->
4. **Reference semantics.** "Include or reference" means either: (a) the plan/spec file appears in the PR's diff (added or modified), or (b) a commit message in the PR contains `Plan: docs/plans/<slug>.md` or `Spec: docs/specs/<slug>.md` and that file exists in the repo at HEAD with the required status.

<!-- INV-process-gates-git-aware -->
5. **Git-aware operation.** The script operates in two modes: PR mode (`--base-ref REF`, compares `REF..HEAD`) and push mode (default, HEAD commit only). Follows the precedent set by `ci/check_adr_immutability.py`.

<!-- INV-process-gates-standalone -->
6. **Standalone.** The script has zero imports from `kanon.*`. It is a standalone Python script runnable with only the standard library and git on PATH.

<!-- INV-process-gates-json-report -->
7. **JSON report.** Output is a JSON object to stdout with `status` (`ok`, `warn`, `fail`), `errors` (list of strings), and `warnings` (list of strings). Exit 0 for ok/warn, exit 1 for fail.

<!-- INV-process-gates-docs-only-exempt -->
8. **Docs-only exempt.** If the PR's diff touches only files under `docs/`, `*.md`, `.kanon/`, or `ci/` (no `src/` changes), both checks are skipped and the script reports `ok`.

## Rationale

- **Co-presence over ordering.** CI cannot observe the temporal sequence of agent actions within a session. But it can observe the final artifact set. A PR that ships source changes without a plan file is the most common and most impactful violation — catching it covers the 80% case.
- **Commit trailer for trivial overrides.** Matches the `Allow-ADR-edit:` trailer pattern from `check_adr_immutability.py`. Explicit opt-out is better than heuristic detection of "trivial" changes, which would be fragile and gameable.
- **Spec detection is narrow by design.** Only new CLI commands are mechanically detectable. Other spec-needing changes (new output dimensions, new guarantees) require human judgment. The script catches what it can and leaves the rest to the audit-trail sentence. This is an honest limitation, not a gap to fill with heuristics.
- **Errors, not warnings.** The existing honor-system gates are already the "soft" layer. The CI script is the "hard" layer — it should fail the build, not just warn.

## Out of Scope

- Enforcing that the plan was approved *before* implementation (temporal ordering).
- Detecting all spec-needing changes (only new CLI commands are caught).
- Validating plan acceptance criteria match the implementation.
- Integrating into `kanon verify` (this is a standalone CI script, like all others).
- Scaffolding this script via an aspect (it is kit-internal, not consumer-facing).

## Decisions

- Follows the git-aware CI script pattern established by [ADR-0032](../decisions/0032-adr-immutability-gate.md) and `ci/check_adr_immutability.py`.
- Commit trailer pattern (`Trivial-change:`) mirrors `Allow-ADR-edit:` from the same ADR.
