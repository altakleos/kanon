---
status: accepted
date: 2026-04-24
---
# ADR-0020: Verified-By — invariant-to-test traceability

## Context

With 102 INV-* anchors across 13 specs and 190+ tests, there is no machine-readable mapping from spec invariants to the tests that enforce them. A failing test cannot be traced to the invariant it protects without manual grep.

## Decision

1. Each spec carries `invariant_coverage:` in YAML frontmatter mapping INV-* anchors to verification targets.
2. Target syntax: `tests/path.py::test_func` (pytest), `ci/script.py` (CI), `tests/path.py` (file-level).
3. Resolution is static: file exists + grep for `def test_func` or `async def test_func`. No imports.
4. Accepted specs without `fixtures_deferred` must have complete coverage (every INV-* anchor mapped).
5. CI validator at `ci/check_verified_by.py` enforces all checks.
6. `kanon verify` warns at depth ≥ 2.

## Alternatives Considered

**Inline verified_by annotations.** Rejected — pollutes multi-line invariant prose.
**Centralized mapping file.** Rejected — decouples mapping from spec, breaks on rename.

## Consequences

- Spec frontmatter grows with `invariant_coverage:` blocks.
- New CI script: `ci/check_verified_by.py`.
- Enables fidelity-lock Phase 2 (fixture-SHA tracking keyed by invariant).

## References

- [Spec: Verified-By](../specs/verified-by.md)
- [ADR-0018: Invariant IDs](0018-invariant-ids.md)
- [Spec: Fidelity Lock](../specs/fidelity-lock.md)
