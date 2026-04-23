---
status: accepted
date: 2026-04-23
---
# ADR-0009: Project rename from `agent-sdd` to `kanon`

## Context

The kit was initially developed under the name `agent-sdd` through v0.1.0a1 (local tag, never pushed, never published to PyPI, no external consumers). Before the first external release, the maintainer decided a different name was preferable: `kanon` — short, pronounceable, evocative of canon/rule/standard without being overly methodology-branded.

The rename window is narrow: adoption cost grows sharply once the package is on PyPI, the repo is on a public remote, or any consumer project has run `kanon init`. This ADR is cut in that window.

## Decision

Rename the project from `agent-sdd` to `kanon` comprehensively. Apply the rename to every identifier, path, and prose reference:

| Category | Old | New |
|---|---|---|
| PyPI package | `agent-sdd` | `kanon` |
| Python import / src dir | `agent_sdd` | `kanon` |
| CLI command | `agent-sdd` | `kanon` |
| Consumer config dir | `.agent-sdd/` | `.kanon/` |
| Atomic-swap runtime dirs | `.agent-sdd.tmp/`, `.agent-sdd.old/` | `.kanon.tmp/`, `.kanon.old/` (derived from config-dir name; no hardcode) |
| HTML comment markers | `<!-- agent-sdd:begin:X -->` | `<!-- kanon:begin:X -->` |
| Shim filenames | `.cursor/rules/agent-sdd.mdc`, etc. | `.cursor/rules/kanon.mdc`, etc. |
| Kit implementation doc | `docs/agent-sdd-implementation.md` | `docs/kanon-implementation.md` |
| Repo directory | `/platform/agent-sdd/` | `/platform/kanon/` |

`CLAUDE.md` and `AGENTS.md` filenames are unchanged — they are cross-vendor harness conventions, not kit-specific identifiers (ADR-0003).

The prior `v0.1.0a1` git tag was deleted and re-tagged against the renamed commit, on the same date, because no external consumer had seen the tag. Release history shows `kanon v0.1.0a1` as the first (and so far only) release.

## Alternatives Considered

1. **Keep the old name.** Rejected. `agent-sdd` is descriptive but generic and risks collision as more "SDD" tools appear. The user's strong preference for `kanon` is itself a signal the old name wasn't sticky.
2. **Rename later, after first external release.** Rejected. Downstream references (pip-installs, `kanon init` output in consumer repos, docs that cite the package) compound adoption cost. Rename cost rises roughly linearly with the number of consumers; doing it at zero is free.
3. **Ship parallel packages under both names** (e.g., `agent-sdd` as a stub that re-exports `kanon`). Rejected. Creates a maintenance tail for no user benefit; there are no existing consumers to compensate.
4. **Bump the version** (e.g., ship the rename as v0.1.0a2, keeping `agent-sdd` v0.1.0a1 as the historical package). Rejected. No one has consumed v0.1.0a1; preserving it leaves two dangling release identities. A clean retag is cheaper.

## Consequences

- Future git log readers see commits 1–10 authored under the old name (that's history; bulk-rewriting commit messages would break SHAs and serve no purpose). The rename commit itself documents the change.
- Accepted ADRs 0001–0008 have their product-name token updated to `kanon`. The decisions they capture are unchanged; only the name changed. This is not a reversal — immutability applies to decision content, not to cosmetic identifiers.
- The `v0.1.0a1` tag was re-issued against the renamed commit. Anyone comparing the tag's commit SHA across time would see a change, but no one has reason to do that (no external reference exists).
- CI and release pipelines (`.github/workflows/*`) carry the new name for mypy path, ruff targets, and package install lines.
- The CHANGELOG's `[0.1.0a1]` entry was rewritten to say "First public alpha under the name `kanon`" with a note that internal development happened under the earlier name. Per Keep-a-Changelog conventions, release entries are narrative-stable but cosmetic edits are acceptable before the release is externally published.

## Config Impact

Every consumer repo created by `kanon init` now writes `.kanon/config.yaml`. Consumers who may have scaffolded against a pre-rename dev build must either (a) re-run `kanon init --force` or (b) manually rename `.agent-sdd/` → `.kanon/` and update AGENTS.md markers. In practice no such consumers exist.

## References

- Session plan at `~/.claude/plans/implement-1-thru-7-whimsical-backus.md` — the approved rename plan, executed over this commit series.
- The rename commit: `4ae9f52 refactor: rename project from agent-sdd to kanon`.
- ADR-0003 (AGENTS.md canonical root) — explains why AGENTS.md and CLAUDE.md filenames do not change.
