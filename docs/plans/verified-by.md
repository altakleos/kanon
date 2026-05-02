---
status: done
---
# Plan: Implement Verified-By

Spec at `docs/specs/verified-by.md` has been approved.

## Tasks

1. Create scripts/check_verified_by.py validator
2. Add invariant_coverage: to specs that have test coverage (non-fixtures_deferred specs)
3. Wire warnings into kanon verify at depth ≥ 2
4. Tests for the validator
5. Regenerate fidelity.lock (spec SHAs changed due to frontmatter additions)

## Success Criteria

- scripts/check_verified_by.py passes on this repo
- kanon verify passes
- All tests pass, coverage above 90%
