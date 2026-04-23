# Changelog

All notable user-visible changes to `kanon` are recorded in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0a1] — 2026-04-23

### Added

- **Aspect model** — aspects are first-class opt-in discipline units per ADR-0012 + ADR-0013. SDD becomes the first shipping aspect (`sdd`); the kit gains a `kanon aspect` subgroup (`list`, `info`, `set-depth`); per-aspect opt-in recorded in `.kanon/config.yaml`. See [`docs/specs/aspects.md`](docs/specs/aspects.md) and [`docs/design/aspect-model.md`](docs/design/aspect-model.md).
- **`solo-with-agents` persona** — kanon's agent-first default user (one human, N concurrent LLM agents). See [`docs/foundations/personas/solo-with-agents.md`](docs/foundations/personas/solo-with-agents.md).
- **Namespaced protocols and AGENTS.md markers** — protocols live at `.kanon/protocols/<aspect>/<name>.md`; AGENTS.md marker sections use `<!-- kanon:begin:<aspect>/<section> -->` with `protocols-index` unprefixed as the cross-aspect catalog.
- **Protocol layer** at `.kanon/protocols/` — three prose-as-code judgment procedures scaffolded into consumer repos (under the `sdd/` namespace in the v0.2 layout):
  - `tier-up-advisor.md` (depth-min 1): signals collection → per-depth fit → tiebreaker ("prefer lower when in doubt; tier-up is cheap") → recommendation with rationale → halt if inconsistent with user intent.
  - `verify-triage.md` (depth-min 1): parse `kanon verify` JSON report → classify → prioritization tree → propose fix with confidence level → never mutate without approval.
  - `spec-review.md` (depth-min 2): structural checks → invariant falsifiability → ambiguity pass → steelman → three-tier feedback → readiness verdict.
  - See [docs/specs/protocols.md](docs/specs/protocols.md) and [ADR-0010](docs/decisions/0010-protocol-layer.md).
- **AGENTS.md marker section `protocols-index`** — unified cross-aspect table listing every active protocol grouped by aspect with name, depth-min, and invoke-when trigger. Regenerated dynamically at init/upgrade/set-depth.
- **Kit kernel doc** at `.kanon/kit.md` — scaffolded at every depth. Describes tier identity, boot chain, rules in force, protocol catalog, and migration pointer.
- **Reference automation snippets** carve-out in vision non-goals per ADR-0013 — aspects with cryptographic, irreversible, or stateful tails may ship CI templates (GitHub Actions YAML, pre-commit configs, Makefile targets) the consumer executes. Agent-behavior gating stays strictly prose-only.
- **80 total tests** (up from 41 at v0.1.0a1) covering the aspect model, the protocol layer, kit.md scaffolding, manifest resolution, tier-migration round-trip, and legacy-config auto-migration.

### Changed

- **Kit layout restructured** from `src/kanon/kit/{agents-md,sections,protocols,files}/` to `src/kanon/kit/aspects/sdd/{agents-md,sections,protocols,files}/` per ADR-0012. Top-level `src/kanon/kit/manifest.yaml` is now an aspect registry (`aspects: {sdd: {...}}`); per-aspect content moves into `aspects/sdd/manifest.yaml`. Strict-superset `depth-0..depth-3` replaces `tier-0..tier-3`; `tier-N.md` → `depth-N.md`.
- **`.kanon/config.yaml` schema v2** — `aspects: {name: {depth, enabled_at, config}}` replaces top-level `tier:` + `tier_set_at:`. Auto-migration runs transparently on first `kanon upgrade`.
- **Protocol frontmatter** — `tier-min:` → `depth-min:`.
- **CLI** — generalised to iterate aspects; `kanon init --tier N` and `kanon tier set <target> <N>` preserved as backwards-compat sugar routing to the `sdd` aspect.
- **Protocols spec** (`docs/specs/protocols.md`) — invariants carry aspect-prefix clauses for the namespaced layout.
- **Vision** (`docs/foundations/vision.md`) — § Non-Goals item #2 narrowed in place per ADR-0013; ADR-0013 is the archaeological trail for the wording change.
- **Initial pre-v0.2 kit-refactor work**: `src/kanon/templates/` → `src/kanon/kit/` with a manifest-driven layout per ADR-0011 (~4× duplication of shared files eliminated; byte-equality enforcement narrowed to a whitelist; hardcoded `_TIER_FILES` / `_TIER_SECTIONS` dicts gone).
- **CI validator renamed and rewritten**: `ci/check_template_consistency.py` → `ci/check_kit_consistency.py`. Walks aspect registry + per-aspect sub-manifests; enforces cross-aspect file-ownership exclusivity; per-aspect byte-equality whitelist; namespace discipline on marker sections.
- **Design doc renamed**: `docs/design/template-bundle.md` → `docs/design/kit-bundle.md`; new `docs/design/aspect-model.md` added for the aspect layer.

### Migration (from v0.1.0a1)

- **v1 config → v2**: `kanon upgrade` auto-migrates `tier: N` + `tier_set_at:` to `aspects: {sdd: {depth: N, enabled_at: ..., config: {}}}`. One-way; older kanon CLIs cannot parse v2 config.
- **Flat protocols → namespaced**: `kanon upgrade` relocates `.kanon/protocols/*.md` under `.kanon/protocols/sdd/`.
- **AGENTS.md markers**: unprefixed v1 markers (`plan-before-build`, `spec-before-design`) are rewritten to namespaced v2 form (`sdd/plan-before-build`, `sdd/spec-before-design`) during `upgrade`. `protocols-index` stays unprefixed (cross-aspect).

## [0.1.0a1] — 2026-04-22

First public alpha under the name `kanon`. The project was previously developed internally under the name `agent-sdd`; per ADR-0009, the rename happened before first external release. Architecture-validation release — the kit works end-to-end for the author's company's future projects; public adoption is not yet a goal.

### Added

- **Repo skeleton** at tier-3 self-hosting: `AGENTS.md` with HTML-comment-delimited kit-managed sections, `CLAUDE.md` shim, `docs/development-process.md` (project-agnostic SDD method, ported from the Sensei reference implementation), Apache-2.0 `LICENSE`, `pyproject.toml`, `README.md`.
- **Foundations** — six principles (prose-is-code, specs-are-source, tiers-insulate, self-hosted-bootstrap, cross-link-dont-duplicate, verification-co-authored) and three personas (solo-engineer, platform-team, onboarding-agent).
- **Six core specs** — cli, template-bundle, cross-harness-shims, tiers, tier-migration, verification-contract.
- **Six deferred specs** (status: deferred) for v0.2+ capabilities: fidelity-lock, spec-graph-tooling, ambiguity-budget, multi-agent-coordination, expand-and-contract-lifecycle, invariant-ids. Indexed from `docs/plans/roadmap.md`.
- **Design doc** — `docs/design/template-bundle.md` covering the four-tier bundle construction.
- **Eight critical ADRs**:
  - 0001 Distribution as pip package.
  - 0002 Self-hosted bootstrap — commits 1–3 are pre-SDD.
  - 0003 AGENTS.md as canonical root; shims are pointers.
  - 0004 Verification is a co-authoritative source, not compiled output.
  - 0005 Model-version compatibility contract (`validated-against:`).
  - 0006 Tier model semantics.
  - 0007 Status taxonomy — adds `deferred` as a first-class value.
  - 0008 Tier migration is mutable, idempotent, non-destructive.
- **CLI** — `kanon init|upgrade|verify|tier|--version`.
  - `init <target> --tier {0,1,2,3}` scaffolds any tier with cross-harness shims and atomic writes.
  - `tier set <target> <N>` migrates between any two tiers: additive tier-up, non-destructive tier-down, AGENTS.md marker-delimited rewrite never touching user content outside markers.
  - `upgrade` refreshes the kit-managed AGENTS.md sections and `.kanon/config.yaml`.
  - `verify` validates a consumer project against its declared tier.
- **Four tier templates** at `src/kanon/templates/tier-{0,1,2,3}/`. Tier-3 shares source of truth (byte-equality) with the kit's own `docs/` and `AGENTS.md` marker sections — CI enforces this via `check_template_consistency.py`.
- **Cross-harness shim registry** at `src/kanon/templates/harnesses.yaml` covering Claude Code, Kiro, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, and JetBrains AI. Pointers only, never duplicates.
- **Four CI validators** — `check_foundations.py`, `check_links.py`, `check_package_contents.py` (ported from Sensei), and `check_template_consistency.py` (new: enforces byte-equality between repo canonical artifacts and tier-3 template).
- **39-test pytest suite** — atomic-write, CLI happy/unhappy paths, tier-migration round-trips (0→1→2→3→2→1→0 and arbitrary hops preserving user-authored files), template integrity across all four tiers. Coverage 77% (floor 70% for v0.1; will ratchet upward).
- **GitHub Actions** — `verify.yml` (py3.10-3.13 matrix, ruff, mypy --strict, all four validators) and `release.yml` (tag-triggered, OIDC trusted publishing, human-approval gate via `pypi` environment).
- **Self-hosting property.** This repo itself is a tier-3 `kanon` project. `kanon verify .` against the repo returns `status: ok`.

### Known limitations

- Python tests can't be mechanically derived from specs (addressed by ADR-0004 — tests are a co-authoritative source alongside specs).
- `kanon verify` emits warning-level (not hard-fail) signals for model-version compatibility per ADR-0005. Automated fixture re-running is deferred to v0.3+.
- Spec-graph tooling (rename, orphan detection, spec-diff rendering) is deferred to v0.2. See `docs/specs/spec-graph-tooling.md`.
- Multi-agent coordination primitives (reservations ledger, plan-SHA pins, decision handshake) deferred to v0.2. See `docs/specs/multi-agent-coordination.md`.

[Unreleased]: https://github.com/altakleos/kanon/compare/v0.2.0a1...HEAD
[0.2.0a1]: https://github.com/altakleos/kanon/releases/tag/v0.2.0a1
[0.1.0a1]: https://github.com/makutaku/kanon/releases/tag/v0.1.0a1
