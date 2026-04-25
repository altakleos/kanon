---
feature: aspect-provides
serves: docs/specs/aspect-provides.md
design: "ADR-0026-lite captures the generalize-requires + token-count-discriminator choice. Pattern instantiation: ADR-0012 (aspect model)."
status: done
date: 2026-04-25
---
# Plan: `provides:` capability registry + generalised `requires:`

## Context

Implements `docs/specs/aspect-provides.md` (10 invariants). Adds a `provides:` field on each top-level aspect entry; generalises `requires:` to accept either depth predicates (`"sdd >= 1"`) or capability-presence predicates (`"planning-discipline"`) via a token-count discriminator. Declares capabilities on all six shipped aspects. Adds CI validation that every capability-presence predicate is provided by some aspect in the kit.

## Tasks

### Manifest layer

- [x] T1: Extend `_load_top_manifest` validation in `src/kanon/_manifest.py` to accept an optional `provides: [...]` field on each top-level aspect entry. Each capability name must match `^[a-z][a-z0-9-]*$`; a non-list value or a malformed name raises a clear `click.ClickException` at load time. → `src/kanon/_manifest.py`

- [x] T2: Add `_aspect_provides(aspect: str) -> list[str]` returning the declared capabilities (empty list when none). Add `_capability_suppliers(top, capability: str) -> list[str]` returning the aspect names that declare the capability in their `provides:`. → `src/kanon/_manifest.py`

### Predicate parser

- [x] T3: Add `_classify_predicate(predicate: str) -> tuple[str, ...]` (or similar) to `src/kanon/cli.py`. Tokenises on whitespace; returns `("depth", name, op, depth_int)` for a 3-token form or `("capability", name)` for a 1-token form whose token matches the capability regex. Anything else is a manifest-load error naming the offending predicate. The classification runs at *manifest load* (eagerly) so a bad predicate is caught before any aspect operation. → `src/kanon/cli.py`

- [x] T4: Refactor `_check_requires(aspect_name, proposed_aspects, top)` in `src/kanon/cli.py` to use `_classify_predicate`. Depth-predicate branch keeps existing behaviour byte-for-byte. Capability branch: collect every supplier name from `top["aspects"][*]["provides"]`; the predicate is satisfied iff at least one supplier appears in `proposed_aspects` with depth ≥ 1. The error message names which form (depth or capability) failed. → `src/kanon/cli.py`

- [x] T5: Refactor `_check_removal_dependents(aspect_name, remaining_aspects, top)` in `src/kanon/cli.py` symmetrically: a removal is blocked if removing the aspect leaves another enabled aspect with an unsatisfied capability-presence predicate. Depth-predicate side keeps existing behaviour. → `src/kanon/cli.py`

### CLI surface

- [x] T6: Update `aspect info` rendering in `src/kanon/cli.py` to print a `Provides: <comma-list>` line (or `Provides: (none)`) after the existing `Requires:` line. The `Requires:` listing already shows raw predicate strings, so capability-presence predicates appear there alongside depth predicates with no extra rendering. → `src/kanon/cli.py`

### Kit-side data — declare capabilities on all six aspects (INV-9)

- [x] T7: Add `provides:` to each top-level entry in `src/kanon/kit/manifest.yaml`:
    - `sdd: [planning-discipline, spec-discipline]`
    - `worktrees: [worktree-isolation]`
    - `release: [release-discipline]`
    - `testing: [test-discipline]`
    - `security: [security-discipline]`
    - `deps: [dependency-hygiene]`
   No existing `requires:` entries are migrated.

### CI validation

- [x] T8: Extend `ci/check_kit_consistency.py` with a new check that walks every aspect's `requires:` predicates, classifies each via the same logic as T3 (or imports `_classify_predicate` from `kanon.cli`), and hard-fails if a capability-presence predicate references a capability that no aspect provides. Depth-predicate references to unknown aspect names are checked the same way (existing manifest validation already covers this; verify it does and extend if not). → `ci/check_kit_consistency.py`

### Tests

- [x] T9: `tests/test_aspect_provides.py` covering INV-1 through INV-10. Concrete cases:
    - **INV-1**: an aspect manifest with `provides: [foo, bar]` round-trips through `_load_top_manifest` and `_aspect_provides("aspect")` returns `["foo", "bar"]`.
    - **INV-1**: `provides: []` is valid and equivalent to absence.
    - **INV-1**: `provides: "not-a-list"` is rejected at manifest load with a clear error.
    - **INV-2**: `_classify_predicate("sdd >= 1")` returns the depth-predicate tuple; `_classify_predicate("planning-discipline")` returns the capability tuple; `_classify_predicate("two tokens")` raises; `_classify_predicate("Bad-Cap")` (uppercase) raises naming the regex.
    - **INV-3**: capabilities cannot collide with valid depth-predicate first tokens (the regex prohibits underscores; aspect names today don't contain underscores either, but the discriminator is token-count, not lookalike disambiguation — this test asserts that `["sdd"]` (1 token, valid capability shape) is interpreted as a capability lookup, not a degenerate depth predicate).
    - **INV-4**: `_check_requires` against a proposed aspect-set where the capability is supplied returns `None`; against a set where it's missing returns a single-line error naming the capability.
    - **INV-5** *(was INV-coexists, now folded into INV-2)*: an aspect declaring `requires: ["sdd >= 1", "planning-discipline"]` succeeds when both forms are satisfied; fails clearly when one is unsatisfied; the error message indicates which form failed.
    - **INV-5 (removal)**: `kanon aspect remove` against an aspect whose capability is required by another enabled aspect errors with a single-line message.
    - **INV-6 (info)**: `kanon aspect info sdd` output includes `Provides: planning-discipline, spec-discipline`.
    - **INV-7 (CI)**: `ci/check_kit_consistency.py` against a synthetic kit with a dangling capability-presence predicate exits non-zero with an error naming the missing capability.
    - **INV-8 (multiple suppliers)**: a proposed aspect-set with two suppliers of the same capability satisfies the predicate; removing one supplier still satisfies the predicate as long as the other is enabled.
    - **INV-9**: every shipped aspect's `provides:` matches the spec table (test reads `kit/manifest.yaml` and asserts each aspect's declared capability list).
    - **INV-10**: every existing-on-`main` `requires:` predicate (collected by reading the current manifest) classifies as a depth predicate and resolves identically before and after the parser change.

- [x] T10: Update `tests/test_kit_integrity.py` (or extend `test_aspect_provides.py`) with an assertion that no capability declared in the kit is unprovided — i.e., the CI check from T8 itself runs clean against the live kit.

### Documentation

- [x] T11: Write **ADR-0026-lite** at `docs/decisions/0026-aspect-provides-and-generalised-requires.md` covering: decision (capability registry + generalised `requires:`); why one field over two (less mental routing for kit authors); why opt-in migration; alternative (parallel `requires-capabilities:` field) and why rejected. → `docs/decisions/0026-aspect-provides-and-generalised-requires.md`

- [x] T12: Add ADR-0026 to `docs/decisions/README.md`.

- [x] T13: Add this plan to `docs/plans/README.md`.

- [x] T14: Update `CHANGELOG.md` `## [Unreleased] / ### Added` with a single consolidated entry covering `provides:`, generalised `requires:`, the six declared capabilities, and the CI validation.

### Self-host

- [x] T15: Run `kanon verify .` against the repo. Confirm `status: ok` and that no fidelity warnings appear unrelated to this PR's changes. Run `python ci/check_kit_consistency.py` and confirm exit 0.

- [x] T16: Refresh `.kanon/fidelity.lock` via `kanon fidelity update .` so the new `aspect-provides` spec is tracked.

## Acceptance Criteria

- [x] AC1: `pytest` passes; full suite ≥ 90% coverage; new tests in T9/T10 all pass.
- [x] AC2: `mypy src/kanon` clean.
- [x] AC3: `ruff check src/ tests/ ci/` clean.
- [x] AC4: `python ci/check_kit_consistency.py` returns exit 0 against the live kit.
- [x] AC5: `kanon verify .` returns `status: ok`.
- [x] AC6: `kanon aspect info sdd` output contains `Provides: planning-discipline, spec-discipline`.
- [x] AC7: All 10 spec invariants have at least one entry in `invariant_coverage:` in the spec frontmatter (added before promoting status from `draft` to `accepted`).
- [x] AC8: Manual trace: every existing-on-`main` `requires:` predicate (six aspects, currently `worktrees: ["sdd >= 1"]` and a `suggests:` on `testing`) classifies as a depth predicate post-refactor; behaviour byte-identical.

## Documentation Impact

- `CHANGELOG.md` `## [Unreleased] / ### Added` (T14).
- New ADR-lite at `docs/decisions/0026-aspect-provides-and-generalised-requires.md` (T11).
- `docs/specs/aspect-provides.md` promoted from `draft` → `accepted` once tests cover all 10 invariants (status flip in same commit as the implementation lands).
- `docs/decisions/README.md` and `docs/plans/README.md` index entries (T12, T13).
- `src/kanon/kit/manifest.yaml` gains `provides:` blocks on six aspects (T7).
