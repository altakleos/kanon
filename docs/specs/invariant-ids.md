---
status: deferred
date: 2026-04-22
realizes:
  - P-verification-co-authored
  - P-specs-are-source
target-release: v0.2
---
# Spec: Invariant IDs — stable anchors + `verified_by:` references

## Intent

Every spec invariant gets a stable, machine-addressable ID (e.g., `<!-- INV-hints-3 -->` as an inline HTML comment anchor). Plans, ADRs, test fixtures, and other artifacts can reference invariants by these IDs. Each invariant additionally carries a `verified_by:` reference pointing at the test or fixture that enforces it.

## Problem

Today, the only way a plan can reference a spec invariant is "invariant 3 of `specs/hints.md`" — an ordinal that depends on the spec's current numbering. A spec edit that inserts a new invariant shifts every reference silently. Auditors can't trace an invariant to its enforcing test without grep. Reviewers can't confirm "this plan change relaxes which invariant?" without reading the whole spec.

## Sketched invariants

1. **Inline anchors.** Each invariant in a spec's Invariants section is preceded by an HTML comment anchor: `<!-- INV-<spec-slug>-<short-name> -->`. The anchor is stable across edits that don't change the invariant's intent.
2. **`verified_by:` field.** Each invariant carries an inline trailing reference: `[... invariant text ...] verified_by: tests/path/test_name.py::test_case`. The path must resolve; the test name must exist.
3. **Validator support.** `ci/check_foundations.py` (or a new validator) walks every spec's invariant anchors and `verified_by:` references, asserts anchors are unique per spec, asserts every `verified_by:` target resolves.
4. **Reference syntax.** Plans and ADRs can reference invariants via `INV-<spec-slug>-<short-name>` slugs. These resolve the same way principle slugs resolve in `serves:`/`realizes:`.
5. **V0.1 is opt-in.** Consumers may adopt this convention in their own specs; the kit's own specs will adopt it in v0.1 where natural (but no hard-fail gate yet). Promotion to mandatory happens in a follow-on when tooling lands.

## Out of Scope in v0.1

The hard-fail validator (warn-only in v0.1).

## Why deferred

Requires a new validator or an extension to `check_foundations.py`. Not hard but adds a dependency on the frontmatter-parsing infrastructure. v0.2 is the right time once fidelity-lock is also in flight (they use similar parsing).

## References

- Reader-first designer agent report during v0.1 planning.
- ADR-0004 for the co-authoritative frame.
