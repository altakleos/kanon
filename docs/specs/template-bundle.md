---
status: accepted
date: 2026-04-22
realizes:
  - P-self-hosted-bootstrap
  - P-cross-link-dont-duplicate
stressed_by:
  - solo-engineer
  - onboarding-agent
fixtures_deferred: "Template-integrity test suite lands in Phase D (tests/test_template_integrity.py)"
---
# Spec: Template bundle — what `init` scaffolds

## Intent

Define the exact file tree written by `agent-sdd init --tier <N>` for each of N ∈ {0, 1, 2, 3}. The bundle contents are the consumer's starting point; every file either comes from the kit or is a placeholder the consumer replaces.

## Invariants

1. **Four tiers ship in v0.1.** Each tier's bundle is a named directory under `src/agent_sdd/templates/`:
   - `tier-0/` — minimal: `AGENTS.md`, `CLAUDE.md`, `.agent-sdd/config.yaml`. No `docs/` structure.
   - `tier-1/` — adds `docs/development-process.md` (byte-identical to the kit's own), `docs/decisions/{README,_template}.md`, `docs/plans/{README,_template}.md`.
   - `tier-2/` — adds `docs/specs/{README,_template}.md`.
   - `tier-3/` — adds `docs/design/{README,_template}.md` and `docs/foundations/{README.md, vision.md, principles/README.md, personas/README.md}`.
2. **Strict-subset invariant.** For every pair (N, N+1), every file in `tier-N/` is byte-identical to its counterpart in `tier-(N+1)/`. Lower tiers are derived by omission, never by independent authoring.
3. **Tier-3 canonical with repo.** Every file in `tier-3/` that has a counterpart in the kit's own `docs/` or `AGENTS.md` is byte-identical to that counterpart. The kit's own repo *is* the tier-3 template (minus `src/`, `tests/`, `ci/`).
4. **Shims are pointers.** `CLAUDE.md` is always a single-line `See @AGENTS.md\n` file. Harness-specific shims (Cursor, Windsurf, etc.) are generated at `init` time from `harnesses.yaml` and are also single-file pointers (with any frontmatter each harness requires).
5. **HTML-comment markers.** Every AGENTS.md template has its kit-managed sections wrapped in `<!-- agent-sdd:begin:<section> -->` / `<!-- agent-sdd:end:<section> -->` comment pairs. The section list for each tier is defined in `tier-migration.md`.
6. **`.agent-sdd/config.yaml` seed.** Every tier writes this file with `{kit_version: "<installed-version>", tier: <N>, tier_set_at: "<ISO-8601>"}`. `init` errors out if `.agent-sdd/` already exists and `--force` wasn't given.
7. **No consumer state leaks into the wheel.** `ci/check_package_contents.py` hard-fails on any file under paths that look like consumer output (e.g., `.agent-sdd/`, `.kit/fidelity.lock`, test-only artifacts).
8. **Placeholders are replaced at init.** Files containing `{{PROJECT_NAME}}`-style placeholders (`string.Template` with safe substitution per Sensei's learner-id pattern) are rendered at `init` time.

## Rationale

Tier separation via directories (not flags + generation) keeps the templates auditable and the CI check simple. Byte-equality enforcement is the only mechanism that reliably prevents tier drift.

Shims as pointers (per `P-cross-link-dont-duplicate`) is the only approach that scales across 8+ harnesses without forcing each new harness to duplicate AGENTS.md content.

## Out of Scope

- Rendering templates via a full templating engine (Jinja, etc.). `string.Template` with a small placeholder vocabulary is sufficient.
- Per-harness opt-out at init time (`--skip-harness cursor`). v0.1 writes all shims; opt-out deferred.

## Decisions

See ADR-0003 (shims-as-pointers), ADR-0006 (tier content), ADR-0008 (section markers).
