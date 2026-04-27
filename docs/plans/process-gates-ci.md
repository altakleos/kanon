---
status: done
spec: docs/specs/process-gates.md
---

# Plan: Process-Gate CI Enforcement

Spec: `docs/specs/process-gates.md` (accepted).

## Deliverables

1. `ci/check_process_gates.py` — standalone git-aware CI script
2. `.github/workflows/verify.yml` update — add the new check step
3. `tests/ci/test_check_process_gates.py` — unit tests

## Implementation Approach

Follow `ci/check_adr_immutability.py` as the structural template:
- `_git()` helper for subprocess calls
- `--base-ref` for PR mode, HEAD-only for push mode
- `main(argv=None) -> int` for testability
- JSON report to stdout

### Core Logic

1. Collect changed files via `git diff --name-only <base>..HEAD`
2. If no `src/` files changed → report `ok`, exit 0
3. Check for `Trivial-change:` trailer in any commit → if found, exempt plan check
4. **Plan check:** scan diff for `docs/plans/` files, or scan commit messages for `Plan: docs/plans/<slug>.md` references. Verify referenced file exists at HEAD with `status:` in {done, accepted, in-progress}.
5. **Spec check:** scan diff for new `@cli.command()`/`@cli.group()`/`@click.command()` decorators (lines starting with `+` in diff). If found, scan for `docs/specs/` files or `Spec: docs/specs/<slug>.md` references. Verify status in {accepted, provisional}.
6. Emit JSON report, exit 1 if errors.

## Acceptance Criteria

- [x] Script detects missing plan when `src/` files change (INV-process-gates-plan-co-presence)
- [x] Script detects missing spec when new CLI command added (INV-process-gates-spec-co-presence)
- [x] `Trivial-change:` trailer exempts plan check (INV-process-gates-trivial-override)
- [x] Commit message `Plan:`/`Spec:` references resolve against repo (INV-process-gates-reference-semantics)
- [x] PR mode (`--base-ref`) and push mode both work (INV-process-gates-git-aware)
- [x] Zero kanon imports (INV-process-gates-standalone)
- [x] JSON report with status/errors/warnings (INV-process-gates-json-report)
- [x] Docs-only changes skip all checks (INV-process-gates-docs-only-exempt)
- [x] Tests cover all 8 invariants
- [x] `kanon verify` passes
- [x] Existing test suite stays green
