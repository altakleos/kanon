---
status: accepted
design: "Follows ADR-0008"
date: 2026-04-22
realizes:
  - P-tiers-insulate
  - P-cross-link-dont-duplicate
stressed_by:
  - solo-engineer
fixtures:
  - tests/test_cli.py
invariant_coverage:
  INV-tier-migration-mutable-tier:
    - tests/test_cli.py::test_tier_set_idempotent
  INV-tier-migration-idempotent:
    - tests/test_cli.py::test_tier_set_idempotent
  INV-tier-migration-tier-up-additive:
    - tests/test_cli.py::test_tier_up_additive_only
  INV-tier-migration-tier-down-non-destructive:
    - tests/test_cli.py::test_tier_set_below_current_is_noop
  INV-tier-migration-agents-md-marker-delimited:
    - tests/test_cli.py::test_init_preserves_user_content_outside_markers
  INV-tier-migration-atomic:
    - tests/test_cli.py::test_tier_migration_round_trip_preserves_user_file
  INV-tier-migration-section-list-per-tier:
    - tests/test_cli.py::test_tier_up_additive_only
  INV-tier-migration-invalid-targets-rejected:
    - tests/test_cli.py::test_aspect_set_depth_invalid
---
# Spec: Tier migration — `kanon tier set`

## Intent

Define the behaviour of `kanon tier set <target> <N>`: what it changes, what it guarantees, what it never does.

## Invariants

<!-- INV-tier-migration-mutable-tier -->
1. **Mutable tier.** Tier is stored in `.kanon/config.yaml`. `tier set` writes this field to `<N>` and updates `tier_set_at` to the current ISO-8601 timestamp.
<!-- INV-tier-migration-idempotent -->
2. **Idempotent.** `tier set <target> <N>` run twice with the same target tier is a noop (exit 0, no filesystem changes beyond `tier_set_at`). This means the command can be safely run from scripts and CI.
<!-- INV-tier-migration-tier-up-additive -->
3. **Tier-up is additive only.** Moving tier-N to tier-(N+k) creates only the *new* files: the layer directories (`docs/specs/` if moving to tier-2, etc.), the new READMEs and _templates, and the newly enabled AGENTS.md sections. Existing user content is never modified, moved, or deleted. No files are renamed or reorganised.
<!-- INV-tier-migration-tier-down-non-destructive -->
4. **Tier-down is non-destructive.** Moving tier-N to tier-(N-k) updates `.kanon/config.yaml` and removes the now-disabled AGENTS.md sections (marker-delimited content only). **Existing artifact directories stay on disk.** The command prints a warning listing artifacts that are now "beyond required" so the consumer can choose to archive or delete. The kit does not delete artifacts unilaterally — they may still be valuable history.
<!-- INV-tier-migration-agents-md-marker-delimited -->
5. **AGENTS.md rewriting is marker-delimited.** The section-marker rewriter touches only content between `<!-- kanon:begin:<section-name> -->` and `<!-- kanon:end:<section-name> -->`. When a tier transition enables a new section, the rewriter inserts the delimited block in the canonical position (documented in `template-bundle.md`). When it disables a section, it removes the block including the markers. Content outside the markers is never modified. Manual edits inside the markers will be overwritten on the next `tier set` or `upgrade`.
<!-- INV-tier-migration-atomic -->
6. **Atomic.** Migration is a single filesystem transaction using the same atomic-replace primitives as `upgrade`. An interrupted migration leaves the target repo in either the pre-migration state or the post-migration state, never a mixed state.
<!-- INV-tier-migration-section-list-per-tier -->
7. **Section-list per tier.** The AGENTS.md sections enabled at each tier are:
   - Tier-0: (none beyond the boot chain and project-layout blocks, which are not marker-delimited)
   - Tier-1: `plan-before-build`
   - Tier-2: `plan-before-build`, `spec-before-design`
   - Tier-3: `plan-before-build`, `spec-before-design` (additional tier-3 sections may be added later; in v0.1 tier-2 and tier-3 have the same marker sections, but tier-3 additionally has `docs/foundations/` and `docs/design/` directories).
<!-- INV-tier-migration-invalid-targets-rejected -->
8. **Invalid targets rejected.** `tier set <target> <N>` with N ∉ {0, 1, 2, 3} exits with code 2 and a clear error message. A target path without `.kanon/config.yaml` exits with a clear error.

## Rationale

Non-destructive tier-down is the single choice that makes experimentation safe. Users will try tier-up, feel it's too much, tier-down, and expect their specs and plans to still be there. Silently deleting them would lose real work. Printing a warning and letting the user choose is the correct respect for user work.

Marker-delimited rewriting solves the "kit wants to update AGENTS.md without touching user content" problem cleanly. Sensei has run without marker delimiters for months; the evidence of that working-without-markers is that no one has wanted to heavily customise `AGENTS.md` outside the kit sections. Adding markers from day 1 in `kanon` preserves the option.

## Out of Scope

- Tier-migration runbooks for cross-tier dependency management (producer concern, deferred).
- Automatic content injection during tier-up beyond what templates and markers specify.

## Decisions

See ADR-0008.
