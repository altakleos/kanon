---
status: accepted (lite)
date: 2026-04-30
weight: lite
---
# ADR-0037: `--profile full` renamed to `all`, new `max` profile added

## Decision

The `--profile` flag on `kanon init` accepts four named values: `solo`, `team`, `all`, `max`. The pre-v0.3.0a8 name `full` is removed outright (no deprecation alias) — kanon has no public consumers yet, so the migration cost is zero. Any other value is rejected with the standard click choice error.

`all` and `max` are differentiated by their depth source:

- **`all`** — every kit-shipped `kanon-*` aspect at its `default-depth` (currently `1` for every aspect).
- **`max`** — every kit-shipped `kanon-*` aspect at the upper end of its `depth-range` (`kanon-sdd:3`, `kanon-release:2`, `kanon-testing:3`, `kanon-security:2`, `kanon-deps:2`, `kanon-worktrees:2`, `kanon-fidelity:1`).

`solo` and `team` continue to name aspect-depth pairs explicitly so a future `default-depth` change in the manifest cannot drift their semantics.

## Why

The original `--profile full` was computed as "every aspect at its `default-depth`". A user who typed `kanon init --profile full` and saw every aspect end up at depth 1 read the result as a defect: "full" reads as "everything cranked", not "everything at the kit author's recommended starting position". The lived UX surfaced this on first use after v0.3.0a7 shipped.

Renaming `full → all` makes the semantics honest (every aspect is enabled, nothing more) and frees the word `full` from the false-maximum reading. Adding `max` provides the behaviour users expected from `full` — every aspect cranked to its declared upper bound — under a name that says exactly that.

`all` is preserved (rather than dropped in favour of just `max`) because there is genuine value in "all aspects at the kit's recommended starting depth": it gives a consumer the kit's full surface area without prescribing where to deepen first. `max` is a separate verb because for most projects it is too aggressive (depth-3 sdd is platform-team territory; tier-up-advisor exists precisely because depth growth should track project maturity).

## Alternative

Keep `full` and add a new `max` alongside it. Rejected — `full`'s name is the actual defect; renaming it is the load-bearing fix. Keeping the misleading name preserves the surprise.

## References

- [`docs/specs/cli.md`](../specs/cli.md) — INV-cli-init-profile.
- [`docs/plans/profile-rename.md`](../plans/archive/profile-rename.md) — implementing plan.
- Per-aspect [`packages/kanon-aspects/src/kanon_aspects/aspects/<slug>/manifest.yaml`](../../packages/kanon-aspects/src/kanon_aspects) — `default-depth` and `depth-range` source (canonical per ADR-0055; runtime-discovered via the `kanon.aspects` entry-point group per ADR-0040).
