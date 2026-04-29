---
status: accepted
date: 2026-04-29
---
# ADR-0035: Tier as uniform aspect-depth raise

## Context

The `--tier N` flag on `kanon init`, and the `kanon tier set <target> N` subcommand, were defined by ADR-0006 and ADR-0008 in the v0.1 model where the only discipline the kit shipped was Spec-Driven Development. In that world a tier was a coherent ladder: tier-0 was no SDD, tier-1 was minimal SDD, tier-2 added specs, tier-3 added foundations.

ADR-0012 (v0.2) and ADR-0016 (aspect decoupling) replaced that single ladder with an aspect-oriented model: six aspects (`sdd`, `worktrees`, `release`, `testing`, `security`, `deps`), each with its own depth dial, opt-in independently. ADR-0016 retained `--tier N` as **back-compat sugar for `--aspects sdd:N`**, which silently re-elevated `sdd` as the implicitly-privileged aspect inside an otherwise symmetric model. The aspect ADRs and the tier ADRs both remain `status: accepted`, leaving the project with two unreconciled mental models in force at the same time.

The symptom is concrete: across the kit, "tier" and "aspect" appear as competing vocabulary in 1,144 occurrences in 85 files, with no single document giving a contributor a definitive rule for which to reach for. The CLI's `--tier`, `--aspects`, `--lite`, and `--profile` flags are mutually exclusive at the parser, and three of the four overlap conceptually.

This ADR commits to a single, mechanical rule for what `--tier N` means in the aspect-first world, supersedes ADR-0006's tier-as-SDD-ladder semantics, and clears the ground for downstream decisions about `--profile`, `--lite`, and the larger `tier`-vocabulary cleanup.

## Decision

`--tier N` is a uniform raise across every aspect listed in the kit manifest's `defaults:` key:

> For each aspect `a` enumerated in `defaults:`, set `a.depth = min(N, a.max_depth)`.
>
> Aspects not in `defaults:` are not touched by tier — they remain at their existing depth, or 0 if not yet enabled.

This rule applies to both surfaces:

- **`kanon init <target> --tier N`** — every default aspect is enabled at `min(N, max)` in the new project's `.kanon/config.yaml`.
- **`kanon tier set <target> N`** — every default aspect's depth is *raised* to `min(N, max)`. Aspects already above that level are not lowered. Aspects explicitly set to a non-zero depth that exceeds `N` are preserved. The migration is non-destructive in the sense ADR-0008 already requires.

Tier ceases to be a property the project stores. `.kanon/config.yaml` records aspect depths only; the `tier:` field (already migrated to `aspects:` in v0.2 per ADR-0012) is not reintroduced. `--tier N` is a transient input that resolves into the aspect set; no surface reads it back as state. The `${tier}` template variable (currently sourced from `kanon-sdd` depth) is removed in a follow-up.

## Alternatives Considered

1. **Keep `--tier N` as sugar for `--aspects sdd:N`** (status quo). Rejected: re-elevates `sdd` over its peer aspects despite ADR-0016 explicitly setting out to dismantle that privilege, and gives the README's onboarding flag (`kanon init --tier 1`) the *least* value-per-keystroke of any flag in the CLI surface. Pre-1.0 alpha is the cheapest moment to break this alias.

2. **Remove `--tier` entirely; standardize on `--aspects` and "depth" vocabulary.** Rejected: the README, `solo-engineer.md` persona, and `P-tiers-insulate.md` principle all anchor first-time-user vocabulary on "tier"; collapsing it loses a numerically-discoverable on-ramp (`--tier 1`) and forces newcomers onto colon-separated aspect syntax (`--aspects sdd:1`) on first contact. The 1,144 prose mentions of "tier" mostly become correct-as-written under the uniform-raise reading; removing the word would force a sweeping rewrite of artifacts (including immutable ADRs) for no gain in user-facing clarity.

3. **Repurpose `--tier N` as a curated bundle table** (e.g. `tier 2 = sdd:2, worktrees:1, testing:1, security:1`). Rejected: requires a manifest schema addition (`tiers:` map), a per-aspect `tier-min:` declaration, or a hardcoded table in `cli.py`; every new aspect requires a tier-table edit; the bundle's contents become a recurring design argument. The uniform-raise rule produces approximately the same outcome with no new schema and no new policy artifact.

4. **Uniform raise restricted to `stable` aspects.** Rejected as over-conservative for a pre-1.0 kit where five of six aspects are `experimental` — the restriction would make `--tier 1` produce `sdd:1` only (i.e. status quo), defeating the rule. The manifest's `defaults:` set is the right knob: a contributor uncomfortable shipping an experimental aspect in tier-1 by default omits it from `defaults:` in the manifest. Tier follows manifest policy; the CLI does not encode stability.

## Consequences

**Positive:**

- Resolves the ADR-0006/0016 tension by giving "tier" a single concrete meaning in the aspect model.
- Collapses one of the four overlapping `kanon init` flags into something complementary: `--tier` for the uniform raise, `--aspects` for precision, with `--profile` and `--lite` separately re-evaluated downstream.
- Most of the 1,144 prose occurrences of "tier" remain correct after this ADR — "a tier-2 project" still means a coherent class of project, just defined as the uniform-raise outcome instead of an SDD-only ladder.
- Future aspects participate in tier scaling automatically by being added to `defaults:`. No `cli.py` edit, no per-aspect tier table.

**Negative:**

- Backward-incompatible behavior change for `--tier 1`: previously produced `sdd:1` only; now produces every default aspect at depth 1. The strict-superset property holds (existing users get more, never less, never a removal), but `tests/test_cli.py` expectations that assert exactly which directories appear at tier-1 break and need to widen.
- ADR-0006 (tier model semantics) and ADR-0008 (tier migration) become at least partially superseded; their immutable bodies stand as period documents but their `status:` transitions to `superseded` with `superseded-by: 0035`.
- `docs/specs/tiers.md` and `docs/specs/tier-migration.md` need substantive rewrites to describe the uniform-raise semantics. Their `status: accepted` invariant set (INV-tiers-*, INV-tier-migration-*) must be re-derived; some invariants survive verbatim, others are dropped, others gain a successor.
- Behavior change is shipped in alpha, surfaced in the v0.3.0 release notes; consumer scripts running `--tier 1` against the new CLI will scaffold more files than before. Pre-1.0 frees us from a deprecation window but raises the bar on the release-note clarity.

**Neutral:**

- The `${tier}` template variable in scaffolded artifacts continues to work in the immediate term (sourced from `kanon-sdd` depth). A follow-up ADR or spec amendment removes it once consumers have migrated.

## Config Impact

- No new manifest field. The existing `defaults:` key (introduced by ADR-0016) is the single policy surface for which aspects participate in tier scaling.
- `.kanon/config.yaml` schema unchanged. `aspects:` is still the only state surface; tier remains an input verb, not stored state.
- `--tier`, `--aspects`, `--lite`, `--profile` remain mutually exclusive at the parser. A future ADR may revisit whether `--tier` becomes a *floor* that `--aspects` overrides on top of.

## References

- ADR-0006 (tier model semantics) — partially superseded by this ADR.
- ADR-0008 (tier migration) — partially superseded by this ADR.
- ADR-0012 (aspect model) — establishes aspects as orthogonal axes.
- ADR-0016 (aspect decoupling) — introduces `--aspects` and `defaults:`; this ADR completes the work that ADR-0016 began.
- `docs/foundations/principles/P-tiers-insulate.md` — the principle this ADR re-grounds in aspect terms.
- `docs/specs/tiers.md`, `docs/specs/tier-migration.md` — to be rewritten as a follow-up to this ADR.
