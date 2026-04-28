---
status: accepted
design: "Follows ADR-0020"
date: 2026-04-24
realizes:
  - P-verification-co-authored
  - P-specs-are-source
stressed_by:
  - platform-team
  - solo-with-agents
fixtures:
  - tests/ci/test_check_verified_by.py
  - tests/test_cli.py
invariant_coverage:
  INV-verified-by-frontmatter-mapping:
    - tests/ci/test_check_verified_by.py::test_real_repo_passes
  INV-verified-by-target-syntax:
    - tests/ci/test_check_verified_by.py::test_unresolved_target_detected
  INV-verified-by-resolution:
    - tests/ci/test_check_verified_by.py::test_unresolved_target_detected
  INV-verified-by-completeness:
    - tests/ci/test_check_verified_by.py::test_missing_coverage_detected
  INV-verified-by-stale-entries:
    - tests/ci/test_check_verified_by.py::test_stale_entry_detected
  INV-verified-by-many-to-many:
    - tests/ci/test_check_verified_by.py::test_real_repo_passes
  INV-verified-by-validator:
    - tests/ci/test_check_verified_by.py::test_real_repo_passes
    - tests/ci/test_check_verified_by.py::test_main_exits_zero_on_ok
  INV-verified-by-verify-integration:
    - tests/test_cli.py::test_init_verify_returns_ok
---
# Spec: Verified-By — invariant-to-test traceability

## Intent

Link every spec invariant to the test(s) that enforce it, so that a failing test can be traced to the invariant it protects and a spec invariant can be audited for coverage. A frontmatter mapping in each spec records which `INV-*` anchors are covered by which tests or CI scripts.

This spec depends on `invariant-ids` (stable anchors must exist before traceability can reference them). It enables `fidelity-lock` Phase 2 (fixture-SHA tracking keyed by invariant).

## Invariants

<!-- INV-verified-by-frontmatter-mapping -->
1. **Frontmatter-based mapping.** Each spec carries an `invariant_coverage:` block in its YAML frontmatter mapping `INV-*` anchors to verification targets:
   ```yaml
   invariant_coverage:
     INV-aspects-aspect-identity:
       - tests/test_kit_integrity.py::test_kit_root_has_expected_top_level_entries
     INV-aspects-cross-aspect-ownership-exclusive:
       - ci/check_kit_consistency.py
   ```
   Keys are `INV-*` anchor IDs that must exist in the spec's own `## Invariants` section. Values are lists of verification targets.

<!-- INV-verified-by-target-syntax -->
2. **Target syntax.** Verification targets are strings in one of three forms:
   - **Pytest node:** `tests/<path>.py::test_function` — references a test function. Covers all parametrized variants. Test classes are not supported (`TestClass::test_method` is out of scope).
   - **CI script:** `ci/<path>.py` — references an entire CI validation script.
   - **File path:** `tests/<path>.py` — file-level coverage when function-level is impractical.
   
   The `::` separator distinguishes pytest nodes from file/script targets.

<!-- INV-verified-by-resolution -->
3. **Resolution.** The validator checks that every target resolves:
   - File targets: the file must exist on disk.
   - Pytest node targets (`::test_function`): the file must exist AND `def test_function` or `async def test_function` must appear in the file (static grep, no imports, no execution).
   - CI script targets: the file must exist.

<!-- INV-verified-by-completeness -->
4. **Coverage completeness.** When a spec has `status: accepted` and does NOT declare `fixtures_deferred:`, every `INV-*` anchor in its `## Invariants` section must appear as a key in `invariant_coverage:`. Missing keys are hard errors. Specs with `fixtures_deferred:` may omit `invariant_coverage:` entirely or provide partial coverage — missing keys are warnings, not errors.

<!-- INV-verified-by-stale-entries -->
5. **Stale entry detection.** If an `INV-*` key in `invariant_coverage:` does not match any anchor in the spec's `## Invariants` section, the validator emits a hard error. This catches retired anchors that were not cleaned up from the mapping.

<!-- INV-verified-by-many-to-many -->
6. **Many-to-many.** One invariant may list multiple targets. One target may appear under multiple invariants across different specs. The mapping is explicit — no inference.

<!-- INV-verified-by-validator -->
7. **Validator.** A CI script `ci/check_verified_by.py` (standalone, following the `check_invariant_ids.py` pattern) performs all checks from invariants 1–6. It outputs a JSON report with `{errors: [...], warnings: [...], status: "ok"|"fail"}`. It is also wired into `kanon verify` at SDD depth ≥ 2 as warnings (not hard errors in the initial release).

<!-- INV-verified-by-verify-integration -->
8. **`kanon verify` integration.** At SDD depth ≥ 2, `kanon verify` warns on specs missing `invariant_coverage:` (when `fixtures_deferred` is absent). At SDD depth ≥ 3, it additionally warns on incomplete coverage (invariants without targets). Neither is a hard error in the initial release — the CI script is the enforcement point.

## Rationale

**Why frontmatter, not inline annotations.** Inline `verified_by:` appended to each invariant pollutes multi-line invariant prose and conflicts with the reader-first principle. Frontmatter keeps invariant text clean and puts the mapping in a machine-parseable location that existing infrastructure (`check_foundations.py`) already knows how to read.

**Why frontmatter per-spec, not a centralized mapping file.** A centralized file (e.g., `.kanon/coverage-map.yaml`) would decouple the mapping from the spec it describes, creating a maintenance burden when specs are renamed or moved. Per-spec frontmatter travels with the spec — rename the file and the mapping moves with it. The tradeoff is larger frontmatter blocks, but YAML frontmatter is already the established metadata location for specs.

**Why static resolution, not import-based.** The verification-contract spec (invariant 9) says `kanon verify` "does not execute code" and "never imports consumer Python." Static grep for `def test_function` is consistent with this constraint. The false-negative gap (dynamically generated tests) is acknowledged and accepted — the mapping is a best-effort audit trail, not a proof system.

**Why mandatory completeness for accepted specs.** A spec with `status: accepted` and no `fixtures_deferred` is claiming its invariants are verified. If the `invariant_coverage:` mapping is incomplete, that claim is unsubstantiated. Making completeness mandatory closes the gap between "we say it's verified" and "we can show which test verifies which invariant."

## Out of Scope

- **Centralized mapping file.** Considered and rejected (see Rationale).
- **Automated coverage inference.** The mapping is manually authored. Inferring which tests cover which invariants from code analysis is a research problem, not a v0.2 feature.
- **Coverage percentage thresholds.** The spec requires complete mapping (every anchor has a target), not a percentage. Partial coverage is handled via `fixtures_deferred`.
- **Test class targets.** `TestClass::test_method` syntax is not supported. Tests should be top-level functions.
- **Runtime resolution.** No pytest collection, no imports, no execution. Static file + grep only.
- **Parametrized variant targeting.** `test_foo[param]` is not a valid target. Targets reference the function, covering all variants.

## Decisions

See:
- **ADR-0020** — verified-by (frontmatter mapping, target syntax, completeness semantics, validator).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
