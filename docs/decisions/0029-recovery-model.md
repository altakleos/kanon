---
status: accepted (lite)
date: 2026-04-27
weight: lite
---
# ADR-0029: Recovery model — auto-replay for graph-rename, idempotent re-run for the rest

## Decision

Amend ADR-0024 §Consequences. The recovery model after an interrupted CLI operation is **hybrid**, not uniformly automatic:

- **`graph-rename` auto-recovers.** When `_check_pending_recovery` finds the sentinel `graph-rename` and the ops-manifest at `.kanon/graph-rename.ops` is present, it calls `kanon._rename.recover_pending_rename(target)`, which replays the manifest's per-file rewrites idempotently and clears the sentinel. The user sees `Recovered interrupted 'graph-rename' operation by replaying ops-manifest.` rather than the warn-and-rerun message. This closes spec-graph-rename INV-3.
- **All other sentinels emit a warning and require manual re-run.** `init`, `upgrade`, `aspect set-depth`, `aspect set-config`, `aspect remove`, `fidelity update` are all idempotent — re-running the named command (or `kanon upgrade`) completes the partial state. The warning suggests the correct user-facing command via `_PENDING_OP_TO_COMMAND`.

ADR-0024's per-file atomic-write guarantee (write-tmp + fsync + replace) is unchanged. Only the cross-file recovery story is amended.

## Why

ADR-0024 §Consequences originally promised *"after any interruption, the next `kanon` invocation completes the transition before doing anything else. No manual intervention required."* That sentence was authored before the spec-graph-rename ops-manifest landed and assumed every sentinel could recover the same way. It oversold the implementation: `_check_pending_recovery` only emitted a warning and `recover_pending_rename` (added in PR #22 for graph-rename) was never wired in. The honest picture is that only `graph-rename` carries enough state on disk (the ops-manifest) to reconstruct the work without user input; for the other sentinels, the recovery path *is* the user re-running the idempotent command — which is fine, just not what the prose said.

This ADR-lite captures the model the implementation now matches. The user-visible contract becomes: "no half-written files; multi-file consistency requires re-running the command we tell you to run, except for `graph-rename` which auto-recovers."

## Alternative

Auto-recovery for every sentinel by serializing each command's full ops-manifest before mutation. Rejected as overengineering: the existing commands are already idempotent (re-running `kanon upgrade` after a partial `aspect set-depth` produces the same final state); a per-command WAL adds ~80 LOC and storage of file content hashes for a recovery model the user can already invoke by typing the suggested command.

## References

- [ADR-0024](0024-crash-consistent-atomicity.md) — crash-consistent atomicity (this ADR amends §Consequences).
- [ADR-0027](0027-graph-rename-ops-manifest.md) — ops-manifest extension that makes `graph-rename` recoverable.
- [`docs/specs/spec-graph-rename.md`](../specs/spec-graph-rename.md) — INV-3 (atomicity + ops-manifest replay) is what the wiring closes.
- [`docs/plans/review-followups-batch-1.md`](../plans/review-followups-batch-1.md) — the batch this ratifies.
