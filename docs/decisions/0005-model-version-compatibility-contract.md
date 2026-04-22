---
status: accepted
date: 2026-04-22
---
# ADR-0005: Model-version compatibility contract

## Context

`agent-sdd`-managed projects use transcript fixtures (prose-as-code fixtures per the pattern inherited from Sensei's ADR-0011) as verification artifacts for protocol behaviour. A fixture that passes on `claude-sonnet-4-6` may not pass on `claude-opus-5` — the model is part of the implementation the fixture verifies.

Today, there is no explicit mechanism to track this. A model version bump can silently invalidate fixture coverage; the consumer only finds out when a production protocol misbehaves against the newer model.

The methodology researcher agent surfaced this as the single most important open question v0.1 should address. The user explicitly requested this ADR in Phase A.

## Decision

Every transcript fixture (and by extension any verification artifact whose outcome depends on model behaviour) carries a `validated-against:` frontmatter field listing the model version(s) the fixture was captured and confirmed on.

```yaml
---
validated-against:
  - claude-sonnet-4-6
  - claude-opus-4-6
last-validated: 2026-04-20
---
```

`agent-sdd verify` compares the consumer project's declared default model (from its own `AGENTS.md` configuration or `.agent-sdd/config.yaml`) against each fixture's `validated-against:` list. When the current default is not listed, `verify` emits a **warning** (not a hard fail) naming the fixture and the missing version. The consumer is then obligated to either (a) re-run the fixture against the new model and update the list, or (b) document a waiver in the fixture's frontmatter (`waiver: <reason>`, `waiver-expires: <date>`).

## v0.1 scope

What v0.1 ships:
- The `validated-against:` / `last-validated:` frontmatter convention in spec and fixture templates.
- Warning-level detection in `agent-sdd verify`.
- Documentation of the convention in `docs/specs/verification-contract.md`.

What v0.1 **does not** ship, and why:
- **Automated fixture re-running** (deferred to v0.3+). Re-running requires invoking the target model(s), which requires per-consumer API keys and orchestration this kit is not ready to own. The fixture spec at `docs/specs/ambiguity-budget.md` (status: deferred) will absorb part of this when it lands.
- **Hard-fail promotion.** v0.1 warns only. Promotion to hard-fail happens once automated re-running lands; warning users who can't respond mechanically yet would be annoying.

## Alternatives Considered

1. **Implicit via pytest parametrisation.** Run every fixture against every model in CI. Prohibitive cost and requires API keys in CI. Rejected.
2. **Model-pinning in the kit itself.** Kit declares a supported-model matrix and consumers are assumed to use one of those. Wrong abstraction — each consumer picks its own model. Rejected.
3. **`validated-against:` + warn-level verify** (chosen). Prose-level, no API dependency, actionable.

## Consequences

- Consumers get visible signal when their fixture coverage is stale relative to their declared model.
- Waivers are explicit (dated, reasoned), which makes stale waivers discoverable.
- The convention is portable — any verification artifact can adopt it, not just transcript fixtures.

## Config Impact

Consumer `.agent-sdd/config.yaml` optionally carries `default-model:` (for future automated re-running). Consumer AGENTS.md's project-specific section is the canonical place today.

## References

- Methodology researcher agent report — "what triggers revalidation when the model version changes?" (v0.1 design synthesis, second round).
- Sensei's ADR-0011 — transcript fixtures — for the underlying fixture convention.
