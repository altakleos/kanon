---
status: superseded
superseded-by: 0035
date: 2026-04-29
---
# ADR-0008: Tier migration is mutable, idempotent, non-destructive

## Context

Projects evolve. A repo that starts as a vibe-coded prototype (tier-0) may become a shipped tool (tier-1), then gain user-facing promises (tier-2), then platform-scale responsibilities (tier-3). Tier selected at `init` is not a commitment for the project's lifetime. The kit must support tier migration as a first-class workflow — not a manual folder shuffle.

The user raised this explicitly after seeing the first version of the v0.1 plan: "a project starts as vibe coding and grows to a team project. Users should be able to change tiers as much as they want."

## Decision

`kanon tier set <target> <N>` moves any consumer project from its current tier to tier `N` (any of 0, 1, 2, 3). The migration satisfies six invariants:

1. **Mutable.** Tier is stored in `.kanon/config.yaml` and is writable by `tier set`. Not a repo tag, not inferred from filesystem contents.
2. **Idempotent.** `tier set <target> <N>` run twice with the same target tier is a noop (exit 0, no filesystem changes beyond a timestamp update on the config file).
3. **Tier-up is additive only.** Moving from tier-N to tier-(N+k) creates new layer directories and their README/templates, and enables new AGENTS.md sections. **No existing user content is modified, moved, or deleted.**
4. **Tier-down is non-destructive.** Moving from tier-N to tier-(N-k) updates `.kanon/config.yaml` and disables relaxed AGENTS.md sections. Existing artifact directories (like `docs/specs/` when moving from tier-2 to tier-1) **remain on disk**. The command prints a warning listing artifacts now "beyond required" so the user can archive or delete them if desired — the kit never deletes them unilaterally.
5. **AGENTS.md rewriting is HTML-comment-marker-delimited.** Sections managed by the kit are wrapped in `<!-- kanon:begin:<section-name> -->` / `<!-- kanon:end:<section-name> -->` comment pairs. The rewriter touches only content inside these pairs. User-authored content outside the markers is never modified. When a tier transition enables or disables a section, the rewriter inserts or removes the delimited block; markers themselves are preserved across noop-migrations.
6. **Atomic.** Migration uses the same atomic-replace primitives as `upgrade` (copy-to-tmp + fsync-dir + swap + fsync-dir — ported from Sensei's ADR-0004 pattern). An interrupted migration leaves the project in either the pre-migration state or the post-migration state, never a mixed state.

`kanon verify` validates the project against the tier declared in `.kanon/config.yaml`. If a user manually tier-downs by deleting config fields without running `tier set`, `verify` fails with an actionable error.

## Alternatives Considered

1. **Tier inferred from filesystem contents.** If `docs/specs/` exists, assume tier ≥ 2. Ambiguous when the user deleted `docs/specs/` during exploration (is the project now tier-1 or is the user mid-migration?). Rejected.
2. **Destructive tier-down** — removing now-optional directories on demotion. Violates the kit's "never delete user content" stance. Users' specs, ADRs, and plans are history; they shouldn't vanish because of a tier change. Rejected.
3. **Separate commands for tier-up and tier-down.** `kanon tier up/down` with different semantics. Forces callers to know their current tier; more error-prone than `tier set <N>`. Rejected.
4. **Unified `tier set <N>` with the six invariants above** (chosen). Cleanest API, consistent with "do the right thing regardless of starting state."

## Consequences

- Consumer projects can freely experiment with tier levels without fear of losing work.
- Users migrating tier-2 → tier-1 see a warning inviting them to delete `docs/specs/` if they want; the kit does not decide for them.
- Migration tests (Phase D) must cover round-trips (0 → 1 → 2 → 3 → 2 → 1 → 0) with user-authored files at each stage; no user file may be changed across the chain.
- AGENTS.md's HTML-comment markers are now part of the kit's public contract. Templates ship with them; consumers who edit AGENTS.md should leave them intact.

## Config Impact

`.kanon/config.yaml`:

```yaml
kit_version: "0.1.0a1"
tier: 2                  # current tier
tier_set_at: "2026-05-15T14:22:00Z"   # optional; updated on every `tier set`
```

## References

- User feedback during v0.1 scoping: "users should be able to change tiers as much as they want."
- Fair-adversary agent report — tier-migration failure modes (ratcheting, mixed-tier teams, etc.).
- Sensei's ADR-0004 — atomic-write primitives — reused for migration atomicity.
