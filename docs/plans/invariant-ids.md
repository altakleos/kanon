# Plan: Implement Invariant IDs

Spec at `docs/specs/invariant-ids.md` has been approved.

## Tasks

1. Update docs/specs/_template.md with anchor convention
2. Retrofit all accepted specs with INV-* anchors (~125 invariants)
3. Update ordinal references in plans/ADRs to INV-* slugs (~17 references)
4. Add CI validator (check_invariant_ids.py or extend check_foundations.py)
5. Wire into kanon verify at depth ≥ 2
6. Tests

## Success Criteria

- Every accepted spec invariant has an INV-* anchor
- CI validator passes
- kanon verify passes
