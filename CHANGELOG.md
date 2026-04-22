# Changelog

All notable user-visible changes to `agent-sdd` are recorded in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0a1] — 2026-04-22

First public alpha. Architecture-validation release — the kit works end-to-end for the author's company's future projects; public adoption is not yet a goal.

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
- **CLI** — `agent-sdd init|upgrade|verify|tier|--version`.
  - `init <target> --tier {0,1,2,3}` scaffolds any tier with cross-harness shims and atomic writes.
  - `tier set <target> <N>` migrates between any two tiers: additive tier-up, non-destructive tier-down, AGENTS.md marker-delimited rewrite never touching user content outside markers.
  - `upgrade` refreshes the kit-managed AGENTS.md sections and `.agent-sdd/config.yaml`.
  - `verify` validates a consumer project against its declared tier.
- **Four tier templates** at `src/agent_sdd/templates/tier-{0,1,2,3}/`. Tier-3 shares source of truth (byte-equality) with the kit's own `docs/` and `AGENTS.md` marker sections — CI enforces this via `check_template_consistency.py`.
- **Cross-harness shim registry** at `src/agent_sdd/templates/harnesses.yaml` covering Claude Code, Kiro, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, and JetBrains AI. Pointers only, never duplicates.
- **Four CI validators** — `check_foundations.py`, `check_links.py`, `check_package_contents.py` (ported from Sensei), and `check_template_consistency.py` (new: enforces byte-equality between repo canonical artifacts and tier-3 template).
- **39-test pytest suite** — atomic-write, CLI happy/unhappy paths, tier-migration round-trips (0→1→2→3→2→1→0 and arbitrary hops preserving user-authored files), template integrity across all four tiers. Coverage 77% (floor 70% for v0.1; will ratchet upward).
- **GitHub Actions** — `verify.yml` (py3.10-3.13 matrix, ruff, mypy --strict, all four validators) and `release.yml` (tag-triggered, OIDC trusted publishing, human-approval gate via `pypi` environment).
- **Self-hosting property.** This repo itself is a tier-3 `agent-sdd` project. `agent-sdd verify .` against the repo returns `status: ok`.

### Known limitations

- Python tests can't be mechanically derived from specs (addressed by ADR-0004 — tests are a co-authoritative source alongside specs).
- `agent-sdd verify` emits warning-level (not hard-fail) signals for model-version compatibility per ADR-0005. Automated fixture re-running is deferred to v0.3+.
- Spec-graph tooling (rename, orphan detection, spec-diff rendering) is deferred to v0.2. See `docs/specs/spec-graph-tooling.md`.
- Multi-agent coordination primitives (reservations ledger, plan-SHA pins, decision handshake) deferred to v0.2. See `docs/specs/multi-agent-coordination.md`.

[Unreleased]: https://github.com/makutaku/agent-sdd/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/makutaku/agent-sdd/releases/tag/v0.1.0a1
