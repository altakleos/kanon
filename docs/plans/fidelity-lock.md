# Plan: Implement Fidelity Lock (Phase 1)

Spec at `docs/specs/fidelity-lock.md` has been approved.

## Tasks

1. Add `kanon fidelity update` CLI command
2. Implement SHA-256 computation for spec files
3. Generate .kanon/fidelity.lock (YAML, sorted, with lock_version)
4. Add fidelity checks to kanon verify at depth ≥ 2
5. Self-host: run fidelity update on this repo
6. Tests

## Success Criteria

- `kanon fidelity update` generates valid lock file
- `kanon verify` warns on stale SHAs
- All tests pass, coverage above 90%
