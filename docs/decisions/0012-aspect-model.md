---
status: accepted
date: 2026-04-23
---
# ADR-0012: Aspect model — aspects subsume tiers; SDD becomes the first aspect

## Context

The v0.1 kit packages one discipline: Spec-Driven Development. The tier model (ADR-0006), tier migration (ADR-0008), manifest-driven bundle (ADR-0011), and protocol layer (ADR-0010) together shape a kit that scaffolds SDD at depths 0–3.

The ambition for v0.2+ is broader: kanon should package *multiple* disciplines — SDD, worktree lifecycle, versioning, release publishing, and more — as opt-in bundles. The machinery is largely present; what's missing is a first-class concept for the opt-in unit.

Three shaping constraints:

1. **kanon is agent-first.** The default user is a solo developer running several concurrent LLM agents, not a traditional team. Aspect identity, default activations, and adoption-trigger framing anchor on agent dynamics (parallel-agent collision, plan-SHA drift, fresh-session discovery) ahead of human-team dynamics. `worktrees`-style coordination is day-one for this user, not "eventually."
2. **Prose-as-code has a floor.** Releasing, signing, and publishing are cryptographic and irreversible; no LLM agency turns "sign this tag" into a prose-executable step. The kit's prose-only non-goal (vision.md § Non-Goals) was authored when SDD — a prose-gate-shaped discipline — was the only target. Absorbing deterministic-tail disciplines forces a narrowing of that non-goal; see ADR-0013.
3. **Maintenance cost explodes multiplicatively.** Tier × aspect × harness × model-version is a combinatorial grid; the byte-equality whitelist in `check_kit_consistency.py` (ADR-0011) and the `validated-against:` fixture convention (ADR-0005) become load-bearing at scale. The chosen model must degrade gracefully under aspect-count growth.

See `docs/specs/aspects.md` for the full invariant surface this ADR implements.

## Decision

Adopt **aspects as the primary unit of opt-in discipline**. Aspects subsume tiers.

### Aspects subsume tiers

SDD becomes the first aspect. Every file currently scaffolded by the tier model lives under an `sdd` aspect at depth 0–3. Other aspects declare their own depth range (`worktrees` is 0–1; `release` partitions however its scaffolds naturally divide). Legacy `tier: N` in existing consumer `.kanon/config.yaml` auto-migrates to `aspects: {sdd: {depth: N}}` on first `kanon upgrade` after this ADR lands. The user-facing mental model is continuous, not forked.

### Manifest shape

Top-level `src/kanon/kit/manifest.yaml` becomes an aspect registry:

```yaml
aspects:
  sdd:
    path: aspects/sdd
    stability: stable
    depth-range: [0, 3]
    default-depth: 1
    requires: []
  worktrees:
    path: aspects/worktrees
    stability: experimental
    depth-range: [0, 1]
    default-depth: 1
    requires: []
```

Each aspect has a sub-manifest at `src/kanon/kit/aspects/<name>/manifest.yaml` declaring per-depth file/protocol/section membership — the same shape the current top-level manifest has today, just scoped.

### Namespaced discovery

- Protocols: `.kanon/protocols/<aspect>/<name>.md` in consumers; `src/kanon/kit/aspects/<aspect>/protocols/<name>.md` in the kit.
- AGENTS.md section markers: `<!-- kanon:begin:<aspect>/<section> -->` / `<!-- kanon:end:<aspect>/<section> -->`.
- The unified `protocols-index` marker block renders rows grouped by aspect.
- Existing flat-namespace protocols (`tier-up-advisor.md`, `verify-triage.md`, `spec-review.md`) migrate under `sdd/` in the v0.2 cut.

### Opt-in state is explicit

`.kanon/config.yaml` gains an `aspects:` mapping of `{name: {depth, enabled_at, config}}`. `kanon upgrade` replays only files for aspects in the mapping. `kanon verify` warns (does not fail) when a config-named aspect is absent from the installed kit.

### CLI

A new `kanon aspect` subgroup mirrors `kanon tier`:

- `kanon aspect list [--installed <target>]`
- `kanon aspect info <name>`
- `kanon aspect add <target> <name> [--depth N] [--config key=value]` — idempotent, additive (tier-up semantics).
- `kanon aspect remove <target> <name>` — removes AGENTS.md markers and config entry, leaves scaffolded files reporting "beyond required" (tier-down semantics, ADR-0008).
- `kanon aspect set-config <target> <name> key=value`

`kanon tier set <target> <N>` remains as backwards-compatible sugar for `kanon aspect set-depth <target> sdd <N>`.

## Alternatives Considered

1. **Tier × aspect 2D grid.** Each aspect has its own independent 0–3 depth parallel to SDD's. Rejected: forces aspects without a depth dimension (binary worktrees, two-level release) to fake ghost cells. Per-aspect depth range is a cleaner primitive.
2. **Kernel + sibling kits.** Keep kanon SDD-only; spawn `kanon-versioning`, `kanon-worktrees`, etc. as sibling packages reusing kanon's primitives. Rejected for v0.2: coordination cost of N published packages exceeds in-tree at current scale. Revive if in-tree fails past ~10 aspects.
3. **Aspect flat-namespace (no depth).** Every aspect is on/off. Rejected: SDD has four meaningful depths; collapsing them would force tier-0 vibe-coders and tier-3 platform teams into the same mold.
4. **Per-aspect semver independent of `kit_version`.** Rejected for v0.2: adds a whole versioning model before the aspect contract has stabilised. Revisit at v1.0+.
5. **Aspect marketplace / third-party registry.** Rejected for v0.2: supply-chain risk (mise/asdf precedent). Centralised curation until the contract is proven.

## Consequences

- **CLI surface grows** by one subgroup (~5 verbs, ~250 LOC in `cli.py`). Must stay under the ~1500 LOC cap (maintenance red line).
- **`.kanon/config.yaml` schema is backwards-incompatible for readers.** Old kanon CLIs reading a new aspect-config produce undefined behavior; the aspects-aware CLI auto-migrates legacy `tier:` into `aspects.sdd` on first `upgrade`.
- **`check_kit_consistency.py` grows** per-aspect file-ownership check + namespaced byte-equality whitelist. Whitelist stays under ~50 entries total (maintenance red line); per-aspect scoping helps.
- **Protocols spec needs amendment.** `docs/specs/protocols.md` invariants 1, 2, and 4 reference flat-namespace layout; they gain aspect-prefix clauses.
- **Self-hosting sharpens.** `P-self-hosted-bootstrap` moves from "every release dogfoods" to "every `stable` aspect dogfoods." `experimental` aspects may ship without full self-hosting.
- **Personas extend.** The `stressed_by` persona set needs a `solo-with-agents` archetype to capture kanon's agent-first default user. Current `solo-engineer` implicitly assumes single-executor.
- **Release-gates preconditioned by aspect-count.** Before aspect count exceeds ~5: automate model-version fixture replay (ADR-0005 follow-on); CI wall-clock must stay ≤10 min; `check_kit_consistency.py` whitelist ≤50 entries.

## Config Impact

`.kanon/config.yaml` schema v2:

```yaml
kit_version: <semver>
aspects:
  <name>:
    depth: <int>
    enabled_at: <ISO-8601>
    config: {<aspect-specific>}
```

Legacy keys (`tier:`, `tier_set_at:`) are removed after migration. Auto-migration on first `kanon upgrade` after the aspect-model release emits: `Migrated legacy tier config to aspect model.`

## References

- `docs/specs/aspects.md` — invariants this ADR implements.
- ADR-0006 — tier semantics (depth dial preserved as `sdd` aspect's depth).
- ADR-0008 — tier migration (non-destructive contract generalises to `aspect add/remove`).
- ADR-0010 — protocol layer (namespace extended to `<aspect>/<name>`).
- ADR-0011 — kit-bundle refactor (manifest-driven data is what makes this extension cheap).
- ADR-0013 — vision amendment (reference automation snippets are kit-shippable; supersedes the prose-only clause).
- `P-prose-is-code`, `P-tiers-insulate`, `P-self-hosted-bootstrap` — principles realized.
