---
feature: tier-uniform-raise
serves: docs/specs/tiers.md
status: in-progress
date: 2026-04-29
---
# Plan: Tier as uniform aspect-depth raise

## Context

ADR-0035 (accepted 2026-04-29, supersedes ADR-0006 and ADR-0008) redefines `--tier N` to be a uniform raise across every aspect listed in the kit manifest's `defaults:` key, with the rule `a.depth = min(N, a.max_depth)`. This plan implements the rule across the CLI, the kit manifest, the spec docs, and the test suite, and documents the user-visible behavior change in the changelog.

One open design question that the ADR deferred to this plan: today `defaults:` in `src/kanon/kit/manifest.yaml` contains only `kanon-sdd`. If we leave it untouched, ADR-0035's rule produces the same observable behavior `--tier N` already produces (only sdd is raised). The whole point of the ADR was to make `--tier N` participate across aspects, so this plan must also decide which aspects are listed in `defaults:`.

**Decision (T1 below):** widen `defaults:` to include every aspect the kit ships (`kanon-sdd`, `kanon-worktrees`, `kanon-release`, `kanon-testing`, `kanon-security`, `kanon-deps`, `kanon-fidelity`). Rationale: the ADR explicitly rejected stability-based filtering ("Tier follows manifest policy; the CLI does not encode stability"). For pre-1.0 alpha, listing every shipped aspect is the most honest reading of "uniform raise". A future ADR can split `defaults:` into a `tier-aspects:` set if the no-flag-init behavior diverges from tier behavior.

The `--profile` flag (`lean` / `standard` / `full`) and the `--lite` flag are not touched by this plan. ADR-0035 explicitly leaves their relationship with `--tier` for a downstream decision.

## Tasks

- [ ] T1: Widen `defaults:` in `src/kanon/kit/manifest.yaml` to enumerate every shipped `kanon-` aspect → `src/kanon/kit/manifest.yaml`.
- [ ] T2: Replace the `--tier N → {kanon-sdd: N}` dispatch in `init` with an iteration over `defaults:` applying `min(N, depth-range[1])` per aspect → `src/kanon/cli.py` (around line 464–465). (depends: T1)
- [ ] T3: Apply the same rule in `kanon tier set <target> N`: for each aspect in `defaults:`, raise `current_depth → max(current_depth, min(N, max))`. Never lower. Aspects already above N are preserved. → `src/kanon/cli.py` (around line 760–775, the `tier_set` subcommand). (depends: T1)
- [ ] T4: Decide and implement: keep deriving `tier_ctx` from `kanon-sdd` depth for template rendering (back-compat for scaffolded `${tier}` placeholders) or replace with the requested tier integer. Recommend: keep current derivation; add a `# TODO(0036): remove after ${tier} placeholder migration` comment. → `src/kanon/cli.py` (line 473–480). (depends: T2)
- [ ] T5: Rewrite `docs/specs/tiers.md` to describe uniform-raise semantics. Drop the four-tier-as-strict-superset table; replace with the rule and a worked example showing tier-1/2/3 outcomes given the current `defaults:` set. Re-derive `INV-tiers-*` invariants — `INV-tiers-tier-taxonomy`, `INV-tiers-strict-inclusion`, and `INV-tiers-tier-stored-explicitly` need replacement; `INV-tiers-tier-is-mutable` survives; new invariant `INV-tiers-uniform-raise` codifies the rule. → `docs/specs/tiers.md`. (depends: T2)
- [ ] T6: Rewrite `docs/specs/tier-migration.md` to describe the floor semantics ("raises only, never lowers"). Drop SDD-specific phrasing; generalise to all aspects in `defaults:`. Re-derive `INV-tier-migration-*` — `INV-tier-migration-tier-up-additive` survives in spirit; `INV-tier-migration-tier-down-non-destructive` is replaced by "tier set never lowers depth". → `docs/specs/tier-migration.md`. (depends: T3)
- [ ] T7: Update `tests/test_cli.py` tier-related tests to assert multi-aspect outcomes. Affected tests include `test_init_scaffolds_all_required_files`, `test_tier_up_additive_only`, `test_tier_set_idempotent`, `test_tier_down_is_non_destructive`, `test_protocols_index_marker_present_tier1_plus`, `test_protocols_index_present_at_tier_0`, `test_init_preserves_user_content_outside_markers`, `test_tier_migration_round_trip_preserves_user_file`. → `tests/test_cli.py`. (depends: T2, T3)
- [ ] T8: Add new test `test_tier_raises_all_default_aspects` asserting that `kanon init --tier 2` produces every aspect in `defaults:` at `min(2, max_depth)` — explicit positive test for ADR-0035's rule. → `tests/test_cli.py`. (depends: T2)
- [ ] T9: Add new test `test_tier_set_never_lowers` asserting that `kanon tier set` from a high-depth manually-configured aspect does not reduce depth. → `tests/test_cli.py`. (depends: T3)
- [ ] T10: Update `--tier` flag help text in `cli.py` (currently "Shorthand for `sdd` aspect depth") to reflect the new semantics. Recommended: "Uniform depth for every aspect in the manifest defaults set." → `src/kanon/cli.py` (line 397). (depends: T2)
- [ ] T11: CHANGELOG entry under `## [Unreleased]` ### Changed: behavior change for `--tier N` and `kanon tier set`. Call out that fresh `kanon init` with no flags now scaffolds more aspects (consequence of T1). → `CHANGELOG.md`. (depends: T1, T2, T3)
- [ ] T12: Update README.md Quickstart if the no-flag init behavior changed (T1) — currently it shows `kanon init ~/myproject --tier 1` with the implicit promise of an SDD-shaped project. The example may need a brief note that tier-1 now also enables worktrees/testing/etc. → `README.md`. (depends: T1)
- [ ] T13: Run `kanon verify .` and full test suite locally before merge. Confirm `status: ok`. → no file. (depends: T2-T12)

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
