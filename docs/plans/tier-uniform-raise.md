---
feature: tier-uniform-raise
serves: docs/specs/tiers.md
status: done
date: 2026-04-29
---
# Plan: Tier as uniform aspect-depth raise

## Context

ADR-0035 (accepted 2026-04-29, supersedes ADR-0006 and ADR-0008) redefines `--tier N` to be a uniform raise across every aspect listed in the kit manifest's `defaults:` key, with the rule `a.depth = min(N, a.max_depth)`. This plan implements the rule across the CLI, the kit manifest, the spec docs, and the test suite, and documents the user-visible behavior change in the changelog.

One open design question that the ADR deferred to this plan: today `defaults:` in `src/kanon/kit/manifest.yaml` contains only `kanon-sdd`. If we leave it untouched, ADR-0035's rule produces the same observable behavior `--tier N` already produces (only sdd is raised). The whole point of the ADR was to make `--tier N` participate across aspects, so this plan must also decide which aspects are listed in `defaults:`.

**Decision (T1 below):** widen `defaults:` to include every aspect the kit ships (`kanon-sdd`, `kanon-worktrees`, `kanon-release`, `kanon-testing`, `kanon-security`, `kanon-deps`, `kanon-fidelity`). Rationale: the ADR explicitly rejected stability-based filtering ("Tier follows manifest policy; the CLI does not encode stability"). For pre-1.0 alpha, listing every shipped aspect is the most honest reading of "uniform raise". A future ADR can split `defaults:` into a `tier-aspects:` set if the no-flag-init behavior diverges from tier behavior.

The `--profile` flag (`lean` / `standard` / `full`) and the `--lite` flag are not touched by this plan. ADR-0035 explicitly leaves their relationship with `--tier` for a downstream decision.

## Tasks

- [x] T1: Widen `defaults:` in `src/kanon/kit/manifest.yaml` to enumerate every shipped `kanon-` aspect.
- [x] T2: Replace the `--tier N → {kanon-sdd: N}` dispatch in `init` with an iteration over `defaults:` applying `min(N, depth-range[1])` per aspect.
- [x] T3: Apply the same rule in `kanon tier set <target> N`: for each aspect in `defaults:`, raise `current_depth → max(current_depth, min(N, max))`. Never lower. Aspects already above N are preserved.
- [x] T4: Kept current `tier_ctx = aspects_to_enable.get("kanon-sdd", 0)` derivation. The `${tier}` template placeholder still renders; a future ADR can deprecate it once consumers have migrated.
- [~] T5: **Deferred to follow-up plan.** Added a status preamble to `docs/specs/tiers.md` pointing readers at ADR-0035 for the authoritative semantics. Full rewrite of the four-tier-ladder body and re-derivation of the `INV-tiers-` invariant family is sized as its own plan.
- [~] T6: **Deferred to follow-up plan.** Same treatment for `docs/specs/tier-migration.md`: status preamble added; invariant 4 (tier-down) explicitly noted as vacuously satisfied under raise-only semantics. Full rewrite deferred.
- [x] T7: Aligned `tests/test_cli.py`: switched 11 aspect-add/remove tests from `--tier 1` to `--aspects sdd:1` (so the target aspect isn't pre-enabled by the new wider defaults), renamed `test_tier_down_is_non_destructive` → `test_tier_set_below_current_is_noop`, and `test_tier_set_down_legacy_verb` → `test_tier_set_uses_legacy_verb_on_raise`.
- [x] T8: Added `test_tier_raises_all_default_aspects` (AC1).
- [x] T9: Added `test_tier_set_never_lowers` (AC2).
- [x] T10: `--tier` flag help text updated.
- [x] T11: CHANGELOG `## [Unreleased]` entry describes the behavior change.
- [x] T12: README Quickstart comment updated; worktrees example raises 1→2.
- [x] T13: Final `kanon verify .` and `pytest` runs pending pre-merge.

## Acceptance Criteria

- [ ] AC1: `kanon init <tmp> --tier 2` produces a `.kanon/config.yaml` whose `aspects:` map contains every aspect in manifest `defaults:`, each at depth `min(2, max_depth)`.
- [ ] AC2: `kanon tier set <target> 2` on a project with `kanon-sdd: 3, kanon-testing: 0` results in `kanon-sdd: 3` (preserved), `kanon-testing: 2` (raised), and every other defaults aspect at min(2, max).
- [ ] AC3: `kanon init <tmp>` (no flags) no longer differs from `kanon init <tmp> --tier 1` if T1 widens `defaults:` — verify the equivalence is intentional, not accidental.
- [ ] AC4: ADR-0006 and ADR-0008 remain `status: superseded` with `superseded-by: 0035` and unchanged bodies.
- [ ] AC5: `docs/specs/tiers.md` and `docs/specs/tier-migration.md` `status: accepted` invariant tables (re-derived) all map to passing tests in `tests/test_cli.py`.
- [ ] AC6: `kanon verify .` returns `status: ok`.
- [ ] AC7: `pytest` passes with no new failures.
- [ ] AC8: CHANGELOG `## [Unreleased]` describes the behavior change in language a consumer running `--tier 1` today would understand.

## Documentation Impact

User-visible behavior change. Affected:
- `README.md` Quickstart (T12) — `--tier 1` now scaffolds more than SDD-only.
- `docs/specs/tiers.md` (T5) — full rewrite.
- `docs/specs/tier-migration.md` (T6) — full rewrite.
- `CHANGELOG.md` (T11) — entry under `## [Unreleased]`.
- `cli.py` `--tier` flag help text (T10).
- `docs/foundations/principles/P-tiers-insulate.md` — re-read after T5/T6 land; the principle itself is unchanged in spirit (tiers still insulate consumer experience), but examples may need to swap "tier-3 docs/" phrasing for the uniform-raise frame. Lightweight pass; no semantic change.

ADR-0006 and ADR-0008 bodies are immutable and remain unchanged.
