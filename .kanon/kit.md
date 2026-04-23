# kanon kit — kanon

> **Kernel doc.** Scaffolded by `kanon init` and refreshed by `kanon upgrade` / `kanon tier set`. This file describes what the kanon kit gives this repo at its current tier, where to find the pieces, and which procedures are available to you (the operating LLM agent).

## This repo's identity

- **Tier:** 3
- **Kit bundle path in-repo:** `.kanon/`
- **Config:** `.kanon/config.yaml` (kit version, tier, last tier-set timestamp)

## Boot chain

The expected reading order for a fresh session is:

1. **`AGENTS.md`** — the repo-canonical entry point. All harness shims (`CLAUDE.md`, `.cursor/rules/…`, `.github/copilot-instructions.md`, etc.) route here. Marker-delimited sections carry the in-force process gates.
2. **This file (`.kanon/kit.md`)** — for kit context: tier identity, protocol catalog, pointers below.
3. **`docs/development-process.md`** (tier ≥ 1) — the SDD method the gates are enforcing.
4. **`docs/decisions/README.md`** (tier ≥ 1) — what has already been decided.
5. **`docs/foundations/vision.md`** (tier 3 only) — product intent.

AGENTS.md is the canonical source of in-force rules; this file is the catalog and routing index.

## Rules in force at this tier

| Rule | Active at tier | Home | What it binds |
| --- | --- | --- | --- |
| Plan Before Build | ≥ 1 | AGENTS.md marker `plan-before-build` | Non-trivial source edits require an approved plan first |
| Spec Before Design | ≥ 2 | AGENTS.md marker `spec-before-design` | New user-visible capabilities require a spec before a design doc |

If your tier is 0, no gates are active — act directly.

## Protocols available at this tier

Protocol files live at `.kanon/protocols/*.md`. Each has YAML frontmatter with `status`, `date`, `tier-min`, and `invoke-when` (the trigger sentence). See the `protocols-index` marker block in `AGENTS.md` for the tier-gated catalog with names and triggers.

When a protocol's `invoke-when` trigger fires, read the matching file in full and follow its numbered steps. Protocols are *prose-as-code* — the steps are for you to execute, with judgment, not for an interpreter to compile.

## Tier migration

`kanon tier set <this-repo> <N>` moves this project to tier N. Migration is:

- **Mutable** — any tier is reachable from any tier.
- **Idempotent** — running `tier set <current>` is a noop.
- **Non-destructive** — no user content is modified, moved, or deleted. Tier-up adds new structure; tier-down relaxes gates but leaves existing artifacts in place.

See `docs/specs/tier-migration.md` (at tier ≥ 1) and ADR-0008 for the full contract.

## Further reading

- **Spec index** (tier ≥ 2): `docs/specs/README.md` — what the kit promises.
- **ADR index** (tier ≥ 1): `docs/decisions/README.md` — what has been decided.
- **Plan index** (tier ≥ 1): `docs/plans/README.md` — what has been and is being built.
- **Design index** (tier ≥ 3): `docs/design/README.md` — how features are built.

## Something missing or wrong?

Run `kanon verify .` to catch drift between this kit's claims and the repo's actual state. For `verify` failures, invoke the `verify-triage` protocol (tier ≥ 1).
