# Plan: Implement Release Aspect

Spec at `docs/specs/release.md` has been approved.

## Deliverables

1. Kit bundle at `src/kanon/kit/aspects/release/`
2. Top-level manifest registration
3. Self-hosting canonical protocol copy
4. Tests

## Success Criteria

- All tests pass, coverage above 90%
- `kanon verify .` passes
- `kanon aspect add . release` works
