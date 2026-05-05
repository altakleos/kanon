---
status: accepted
design: "Follows ADR-0018"
date: 2026-04-24
realizes:
  - P-specs-are-source
  - P-cross-link-dont-duplicate
stressed_by:
  - solo-with-agents
fixtures:
  - tests/scripts/test_check_invariant_ids.py
  - tests/test_cli.py
invariant_coverage:
  INV-invariant-ids-anchor-format:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
    - tests/scripts/test_check_invariant_ids.py::test_missing_anchor_detected
  INV-invariant-ids-spec-slug-derivation:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
  INV-invariant-ids-short-name-grammar:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
  INV-invariant-ids-anchors-append-only:
    - tests/scripts/test_check_invariant_ids.py::test_duplicate_anchor_detected
  INV-invariant-ids-reference-syntax:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
  INV-invariant-ids-validator:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
    - tests/scripts/test_check_invariant_ids.py::test_main_exits_zero_on_ok
  INV-invariant-ids-verify-integration:
    - tests/test_cli.py::test_init_verify_returns_ok
  INV-invariant-ids-spec-template-updated:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
  INV-invariant-ids-migration:
    - tests/scripts/test_check_invariant_ids.py::test_real_repo_passes
---
# Spec: Invariant IDs — stable anchors for spec invariants

## Intent

Give every spec invariant a stable, machine-addressable identifier that survives renumbering, insertion, and deletion. Today, plans, ADRs, and other specs reference invariants by ordinal ("invariant 3 of aspects.md"). Inserting a new invariant silently shifts all downstream references. This spec defines an anchor convention, a naming grammar, and a CI validator so that invariant references are stable and mechanically verifiable.

This spec covers **anchors and references only**. The companion spec `verified-by` (deferred) covers invariant-to-test traceability.

## Invariants

<!-- INV-invariant-ids-anchor-format -->
1. **Anchor format.** Each invariant in a spec's `## Invariants` section is preceded by a single-line HTML comment anchor: `<!-- INV-<spec-slug>-<short-name> -->`. The anchor appears on the line immediately before the numbered list item. Anchors are not kanon section markers and must not use the `kanon:begin/end` pattern.

<!-- INV-invariant-ids-spec-slug-derivation -->
2. **Spec-slug derivation.** `<spec-slug>` is the filename stem of the spec (e.g., `aspects` from `aspects.md`, `cross-harness-shims` from `cross-harness-shims.md`).

<!-- INV-invariant-ids-short-name-grammar -->
3. **Short-name grammar.** `<short-name>` is a kebab-case identifier matching `[a-z][a-z0-9-]{1,40}`, author-chosen, unique within the spec. It should derive from the invariant's bold name (e.g., `**Aspect identity.**` → `aspect-identity`). When the bold name would exceed 40 characters, abbreviate meaningfully.

<!-- INV-invariant-ids-anchors-append-only -->
4. **Anchors are append-only.** An anchor is never reused after its invariant is deleted. Renaming an anchor requires updating all references (enforced by the validator). Ordinal numbers in the markdown list may be renumbered for readability; the `INV-*` anchor is the stable identifier.

<!-- INV-invariant-ids-reference-syntax -->
5. **Reference syntax.** Plans, ADRs, and other specs reference invariants as `INV-<spec-slug>-<short-name>` in prose. These references are validated by the CI validator — every `INV-*` slug in `docs/plans/`, `docs/decisions/`, and `docs/specs/` must resolve to an existing anchor in a spec file.

<!-- INV-invariant-ids-validator -->
6. **Validator.** A CI check (extension to `check_foundations.py` or a new `check_invariant_ids.py`) performs:
   - Anchor uniqueness: no duplicate `INV-*` IDs within a spec.
   - Slug consistency: the `<spec-slug>` portion matches the file's stem.
   - Cross-reference resolution: every `INV-*` slug in docs/ resolves to an existing anchor.
   - For deferred specs (`## Sketched invariants`): missing anchors emit warnings, not errors.
   - For accepted specs (`## Invariants`): missing anchors are hard errors.

<!-- INV-invariant-ids-verify-integration -->
7. **`kanon verify` integration.** At SDD depth ≥ 2, `kanon verify` warns on specs with invariants lacking `INV-*` anchors. At SDD depth ≥ 3, it additionally warns on unresolved `INV-*` cross-references from plans and ADRs. Neither is a hard error in v0.2.

<!-- INV-invariant-ids-spec-template-updated -->
8. **Spec template updated.** `docs/specs/_template.md` is updated to show the anchor convention:
   ```markdown
   ## Invariants

   <!-- INV-<spec-slug>-<short-name> -->
   1. **<Short name>.** <Observable property.>
   ```

<!-- INV-invariant-ids-migration -->
9. **Migration.** All existing accepted specs are retrofitted with anchors in a single pass. Existing ordinal references in plans/ADRs are updated to use `INV-*` slugs. Deferred specs receive anchors opportunistically (not required until promotion to accepted).

## Rationale

**Why HTML comments, not heading IDs.** Heading IDs would pollute the document outline and break the clean `## Invariants` → numbered-list structure. HTML comments are invisible in rendered markdown, greppable in source, and don't conflict with kanon section markers.

**Why split from verified-by.** Anchors and references solve ordinal fragility (a naming problem). `verified_by` solves invariant-to-test traceability (a verification problem). They have different adoption costs, different validators, and different dependency profiles. Fidelity-lock depends on `verified_by` but not on anchors. Plans/ADRs depend on anchors but not on `verified_by`. Landing anchors first is low cost and high value.

**Why big-bang migration.** Incremental migration creates a mixed state where some invariants have IDs and some don't, making the validator harder to write and ordinal references fragile during the transition window. 100 invariants is ~2 hours of mechanical work — small enough for a single pass.

**Why append-only anchors.** Reusing a retired anchor would silently redirect old references to a different invariant. Append-only semantics make references permanently stable, even across spec amendments.

## Out of Scope

- **`verified_by` traceability.** Covered by the companion `verified-by` spec (deferred).
- **Automated anchor generation.** Anchors are author-chosen. A CLI helper could be added later but is not part of this spec.
- **Consumer-facing enforcement.** The validator runs on the kit's own specs. Consumer repos at SDD depth ≥ 2 get warnings from `kanon verify`, not hard errors.
- **Intra-spec ordinal references.** References within the same spec (e.g., "see invariant 3 above") are not validated. Authors should use `INV-*` slugs for these too, but it's a convention, not enforced.

## Decisions

See:
- **ADR-0018** — invariant IDs (anchor format, naming grammar, validator, migration strategy).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
