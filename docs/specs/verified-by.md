---
status: deferred
date: 2026-04-24
realizes:
  - P-verification-co-authored
  - P-specs-are-source
stressed_by:
  - platform-team
target-release: v0.3
fixtures_deferred: "Blocked on invariant-ids landing first."
---
# Spec: Verified-By — invariant-to-test traceability

## Intent

Link every spec invariant to the test(s) that enforce it, so that a failing test can be traced to the invariant it protects and a spec invariant can be audited for coverage. This spec defines the `verified_by` mapping, its syntax, and the validator that checks it.

This spec depends on `invariant-ids` (stable anchors must exist before traceability can reference them). It is a prerequisite for `fidelity-lock` (which needs machine-readable invariant→test mappings).

## Sketched invariants

1. **Frontmatter-based mapping.** Each spec carries an `invariant_coverage:` block in its YAML frontmatter mapping `INV-*` anchors to verification targets:
   ```yaml
   invariant_coverage:
     INV-aspects-aspect-identity:
       - tests/test_kit_integrity.py::test_kit_root_has_expected_top_level_entries
     INV-aspects-cross-aspect-ownership:
       - ci/check_kit_consistency.py
   ```
   This keeps invariant prose clean and supports many-to-many relationships.

2. **Target syntax.** Verification targets are either:
   - Pytest node: `tests/<path>.py::test_function` (covers all parametrized variants)
   - CI script: `ci/<script>.py` (no `::` suffix — the entire script is the verifier)
   - File path: `tests/<path>.py` (file-level coverage when function-level is impractical)

3. **Resolution.** The validator checks that every target file exists and, for `::test_function` targets, that `def test_function` appears in the file (static grep, no imports).

4. **`fixtures_deferred` interaction.** When a spec declares `fixtures_deferred:` in frontmatter, `invariant_coverage:` is optional. The validator warns on missing coverage but does not hard-fail. When `fixtures_deferred` is removed, `invariant_coverage` becomes mandatory.

5. **Many-to-many.** One invariant may list multiple targets. One target may appear under multiple invariants. The mapping is explicit — no inference.

## Why deferred

Depends on `invariant-ids` landing first (stable anchors are the keys in the mapping). Also depends on sufficient test coverage to make the mapping meaningful — the project is at 94% coverage with 182 tests, which is close but the `verified_by` audit across 100 invariants is a significant content effort. Defer until invariant-ids is proven and fidelity-lock is ready to consume the mapping.

## References

- [Spec: Invariant IDs](invariant-ids.md) — prerequisite (stable anchors)
- [Spec: Fidelity Lock](fidelity-lock.md) — consumer (needs invariant→test mappings)
- [ADR-0004](../decisions/0004-verification-co-authoritative-source.md) — verification as co-authoritative source
