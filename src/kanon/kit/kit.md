# kanon kit — ${project_name}

> **Kernel doc.** Scaffolded by `kanon init` and refreshed by `kanon upgrade` / `kanon aspect set-depth`. This file describes what the kanon kit gives this repo at its current depth, where to find the pieces, and which procedures are available to you (the operating LLM agent).

## This repo's identity

- **SDD depth:** ${sdd_depth}
- **Kit bundle path in-repo:** `.kanon/`
- **Config:** `.kanon/config.yaml` (kit version, aspects, depths, last set-depth timestamp)

## Boot chain

The expected reading order for a fresh session is:

1. **`AGENTS.md`** — the repo-canonical entry point. All harness shims (`CLAUDE.md`, `.cursor/rules/…`, `.github/copilot-instructions.md`, etc.) route here. Marker-delimited sections carry the in-force process gates.
2. **This file (`.kanon/kit.md`)** — for kit context: depth identity, protocol catalog, pointers below.
3. **`docs/sdd-method.md`** (depth ≥ 1) — the SDD method the gates are enforcing.
4. **`docs/decisions/README.md`** (depth ≥ 1) — what has already been decided.
5. **`docs/foundations/vision.md`** (depth 3 only) — product intent.

AGENTS.md is the canonical source of in-force rules; this file is the catalog and routing index.

## Rules in force at this depth

| Rule | Active at depth | Home | What it binds |
| --- | --- | --- | --- |
| Plan Before Build | ≥ 1 | AGENTS.md marker `plan-before-build` | Non-trivial source edits require an approved plan first |
| Spec Before Design | ≥ 2 | AGENTS.md marker `spec-before-design` | New user-visible capabilities require a spec before a design doc |

If your depth is 0, no gates are active — act directly.

## Protocols available at this depth

Protocol files live at `.kanon/protocols/*.md`. Each has YAML frontmatter with `status`, `date`, `depth-min`, and `invoke-when` (the trigger sentence). See the `protocols-index` marker block in `AGENTS.md` for the depth-gated catalog with names and triggers.

When a protocol's `invoke-when` trigger fires, read the matching file in full and follow its numbered steps. Protocols are *prose-as-code* — the steps are for you to execute, with judgment, not for an interpreter to compile.

## Depth migration

`kanon aspect set-depth <this-repo> sdd <N>` moves this project's `sdd` aspect to depth N. Migration is:

- **Mutable** — any depth is reachable from any depth.
- **Idempotent** — running `set-depth` at the current depth is a noop.
- **Non-destructive** — no user content is modified, moved, or deleted. Increasing depth adds new structure; decreasing depth relaxes gates but leaves existing artifacts in place.

See `docs/specs/tier-migration.md` (at depth ≥ 1) and ADR-0008 for the full contract.

## Further reading

- **Spec index** (depth ≥ 2): `docs/specs/README.md` — what the kit promises.
- **ADR index** (depth ≥ 1): `docs/decisions/README.md` — what has been decided.
- **Plan index** (depth ≥ 1): `docs/plans/README.md` — what has been and is being built.
- **Design index** (depth ≥ 3): `docs/design/README.md` — how features are built.

## Something missing or wrong?

Run `kanon verify .` to catch drift between this kit's claims and the repo's actual state. For `verify` failures, invoke the `verify-triage` protocol (depth ≥ 1).
