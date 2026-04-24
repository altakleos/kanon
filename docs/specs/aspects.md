---
status: accepted
date: 2026-04-23
realizes:
  - P-prose-is-code
  - P-tiers-insulate
  - P-self-hosted-bootstrap
stressed_by:
  - solo-engineer
  - solo-with-agents
  - platform-team
  - onboarding-agent
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
  - tests/test_protocols.py
---
# Spec: Aspects — opt-in discipline bundles

## Intent

Define the *aspect* as the unit of opt-in discipline kanon packages. An aspect is a coherent bundle of prose rules, protocols, AGENTS.md section fragments, and scaffolded files that governs one dimension of development — Spec-Driven Development, versioning, worktree lifecycle, release publishing, and so on. Consumers opt in to the aspects they want; kanon stays insulated (a project with only `sdd` enabled never sees `release`-related files or rules, and vice versa).

The aspect layer extends the existing tier model rather than replacing it. Where tiers previously encoded *depth* of SDD discipline, aspects encode *breadth* of disciplines. Every aspect has its own depth dial; `sdd` becomes the first aspect and retains the 0–3 range as its depth. Non-SDD aspects may have narrower ranges.

The model's primary user is an LLM-driven repo — often a solo developer running several concurrent agents — not a traditional human team. Aspect identity, default activation, and adoption-trigger framing are anchored on agent dynamics (parallel-agent collision, plan-SHA drift, fresh-session discovery) rather than human-team dynamics (second contributor, code-review cadence).

## Invariants

<!-- INV-aspects-aspect-identity -->
1. **Aspect identity.** Each aspect has a unique kebab-case name, a stability label (`experimental | stable | deprecated`), a depth range (integer `min`–`max`), and optional `requires:` / `suggests:` declarations against other aspects. All four are declared in `src/kanon/kit/manifest.yaml` under `aspects.<name>`.

<!-- INV-aspects-sdd-is-an-aspect -->
2. **SDD is an aspect.** Every file currently scaffolded by the tier model (`docs/development-process.md`, `docs/{decisions,plans,specs,design,foundations}/`, the tier-specific `AGENTS.md` sections) lives under the `sdd` aspect at depth 0–3. Legacy `tier: N` in existing consumer `.kanon/config.yaml` auto-migrates to `aspects: {sdd: {depth: N}}` on first `kanon upgrade` after the aspect model ships.

<!-- INV-aspects-per-aspect-depth-dial -->
3. **Per-aspect depth dial.** Depth range is declared per-aspect in its sub-manifest. `sdd` spans 0–3; other aspects declare whatever range their scaffolds naturally partition into (e.g., `worktrees` is 0–2). Ghost cells (depth levels with no content) are not allowed.

<!-- INV-aspects-opt-in-explicit-primary -->
4. **Opt-in state is explicit and primary.** `.kanon/config.yaml` carries an `aspects:` mapping keyed by aspect name, each entry holding `depth`, `enabled_at` (ISO-8601), and a `config:` block for aspect-specific options. `kanon upgrade` replays only files for aspects present in the mapping. `kanon verify` warns (does not fail) when a config-named aspect is absent from the installed kit — the opt-in record survives a deprecation upstream.

<!-- INV-aspects-namespaced-discovery -->
5. **Namespaced discovery.** Protocol files live under `.kanon/protocols/<aspect>/<name>.md` in consumer repos and `src/kanon/kit/aspects/<aspect>/protocols/<name>.md` in the kit. AGENTS.md section markers gain an aspect prefix: `<!-- kanon:begin:<aspect>/<section> -->` / `<!-- kanon:end:<aspect>/<section> -->`. The `protocols-index` marker block renders a single unified table grouped by aspect. Existing flat-namespace protocols (`tier-up-advisor.md`, `verify-triage.md`, `spec-review.md`) migrate under `sdd/` in the v0.2 cut.

<!-- INV-aspects-cross-aspect-ownership-exclusive -->
6. **Cross-aspect file ownership is exclusive.** No two aspects may scaffold the same file path. `ci/check_kit_consistency.py` fails on conflict. Files outside every aspect's claim are consumer-authored and never touched by `init`, `upgrade`, `aspect add`, or `aspect remove`.

<!-- INV-aspects-non-destructive-add-remove -->
7. **Non-destructive add/remove.** `kanon aspect add <name>` is idempotent and additive — it scaffolds missing files and AGENTS.md sections without touching existing ones (ADR-0008 tier-up pattern, generalised). `kanon aspect remove <name>` deletes the aspect's AGENTS.md marker block and its `.kanon/config.yaml` entry, leaves its scaffolded files on disk, and reports them as "beyond required" (ADR-0008 tier-down pattern, generalised).

<!-- INV-aspects-reference-automation-shippable -->
8. **Reference automation snippets are kit-shippable.** Aspects governing cryptographic, irreversible, or persistent-state operations (e.g., `release` — tag signing, PyPI trusted publishing) may include reference CI templates under their scaffolded files (GitHub Actions YAML, pre-commit configs, Makefile snippets). These snippets do not gate agent behavior — they are copy-in templates the consumer executes deterministically. This narrows the previous "kit is prose-only" non-goal; see ADR-0013.

<!-- INV-aspects-every-aspect-self-hosted -->
9. **Every shipping aspect is self-hosted.** This repo enables every `stability: stable` aspect kanon ships before the release that ships it, per `P-self-hosted-bootstrap`. An aspect that cannot be used to develop kanon itself is not ready for the `stable` label.

## Rationale

**Why aspects subsume tiers.** A 2D `tier × aspect` grid would force every aspect to fit a 0–3 depth analog. Versioning has no "tier-3 foundations"; worktrees spans 0–2. Making depth a per-aspect property lets `sdd` keep 0–3 while other aspects declare whatever partitioning fits, without ghost cells. Legacy `tier: N` auto-migrates to `aspects: {sdd: {depth: N}}`, so the user-facing mental model is continuous rather than forked on day 1.

**Why agent-first framing.** kanon's default user is a solo developer running several concurrent LLM agents, not a human team. The adoption trigger for `worktrees` is the first time a second concurrent agent reads what a first agent is writing — not the day a second human joins the repo. Aspects that solve agent-agent collisions (worktrees, plan-SHA pins from the deferred `multi-agent-coordination` spec, decision-handshake protocols) belong early in the recommended adoption sequence, ahead of human-team aspects such as code review or RFC ceremony. The personas under `docs/foundations/personas/` should be extended with at least one solo-human-plus-N-agents archetype before the v0.2 aspect model ships broadly — the current `solo-engineer` persona implicitly assumes a single executor.

**Why explicit opt-in state in config.** The Copier prior-art failure mode called "answer drift" — a consumer deletes a scaffolded file, runs upgrade, the file resurrects silently because the answer file still says the aspect is enabled — is closed by making `.kanon/config.yaml` the declarative source of truth. `kanon upgrade` replays only what config declares is enabled; a file removed from config stops being replayed.

**Why namespaced protocols and markers.** The flat `.kanon/protocols/` layout worked for three kit-authored protocols but collides as soon as multiple aspects contribute protocols independently. The `<aspect>/<name>` prefix is additive over the protocols-spec contract (byte-equality still holds per aspect) and makes protocol ownership visible in the file path. The same rationale applies to AGENTS.md section markers.

**Why the prose-only non-goal bends here.** Releasing, signing, and publishing are cryptographic and irreversible; no LLM-agency trajectory turns "sign this tag" into a prose-executable step. The non-goal's intent — "kit does not gate *agent behavior* through runtime hooks" — is preserved. What is narrowed is the separate question of whether the kit may ship *copy-in templates* for deterministic operations the consumer runs without kit involvement. ADR-0013 supersedes the relevant clause of `foundations/vision.md` § Non-Goals; the vision itself is not edited in place, per foundations' immutability-with-trail convention.

## Out of Scope

- **Aspect marketplace / third-party aspect packages.** v0.2 ships aspects in the kit wheel. Community aspect registries are deferred until the aspect contract has stabilised — the supply-chain lesson from decentralised plugin ecosystems is to centralise curation until the shape is proven.
- **Runtime dispatch.** There is no `kanon aspect invoke <name>` CLI. The operating agent reads the protocol file directly, as with the existing protocol layer.
- **Per-aspect semver independent of `kit_version`.** Aspects ship with the kit and move at the kit's version. A future revision may split them.
- **Filesystem-inferred opt-in.** Opt-in is always explicit in `.kanon/config.yaml`; `kanon verify` does not scan the repo and propose aspects to enable.
- **Aspect-specific `kanon verify` semantics beyond structural checks.** `verify` validates that scaffolded files exist, AGENTS.md markers are balanced, and config-declared aspects resolve in the manifest. It does not execute aspect-specific correctness checks (e.g., "is this release properly signed").

## Decisions

See:
- **ADR-0012** — aspect model: aspects subsume tiers, depth is per-aspect, namespaced protocols and sections, explicit `.kanon/config.yaml` opt-in, non-destructive add/remove mirroring ADR-0008.
- **ADR-0013** — vision amendment: reference automation snippets are kit-shippable for cryptographic / irreversible / persistent-state operations; supersedes the prose-only clause of `foundations/vision.md` § Non-Goals.

ADR numbers are provisional until authored alongside this spec's promotion from `draft` to `accepted`.
