---
id: P-tiers-insulate
kind: product
status: accepted
date: 2026-04-22
---
# Tiers insulate consumer experience, not producer experience

## Statement

`agent-sdd`'s tier model cleanly insulates consumers: a tier-0 project never sees tier-3 artifacts, terminology, or process gates. That consumer insulation is load-bearing. The tier model does **not** insulate producers (the kit's maintainers) from the friction of tier migrations, cross-tier dependencies, or retroactive artifact manufacturing. Those are real producer-facing concerns the kit addresses separately via runbooks and non-destructive migration.

## Rationale

Two different problems are often conflated under "tiering":
1. **Sledgehammer problem.** A simple change shouldn't require a 16-criterion user-story exercise. Solution: don't show simple projects the heavy artifacts at all. This is what tier insulation buys.
2. **Ratcheting problem.** A project that grows across tiers needs to migrate without losing work, without retroactively manufacturing artifacts that are already derived from the code they're supposed to govern. Solution: non-destructive migration + explicit runbooks.

The principle is that (1) is a kit design property — solved structurally by which artifacts a tier includes — and (2) is a producer-facing operational concern — solved by CLI semantics and runbook docs, not by hiding anything.

## Implications

- `agent-sdd init --tier 0` literally does not write any `docs/` directory. The tier-0 user has no mental model of tier-3 artifacts to carry.
- `agent-sdd tier set` is designed assuming the user knows about tier migration (producer concern), not assuming they know about every artifact they're adding (consumer concern — handled by README-per-layer auto-generation).
- Tier-up operations print a terse summary of what was added, not a tutorial on how to use the new layer (the README of each new directory does that).
- Tier-down operations print a warning listing artifacts now "beyond required" — deliberately surfacing the producer-facing choice (keep, archive, delete) rather than hiding it.

## Exceptions / Tensions

- A team mid-migration between tiers has a temporarily mixed experience. Acceptable; migration is a bounded operation.
- Cross-tier dependencies (tier-3 library depending on tier-0 utility) are a known producer concern that v0.1 does not fully solve — runbook deferred to v0.2 per the fair-adversary's note in ADR-0006.

## Source

Fair-adversary agent report during v0.1 design synthesis; user confirmation that tier-3 is agent-sdd's own dogfood tier.
