---
status: accepted
date: 2026-04-22
realizes:
  - P-cross-link-dont-duplicate
stressed_by:
  - onboarding-agent
fixtures_deferred: "Shim-integrity test suite lands in Phase D (tests/test_shims.py)"
---
# Spec: Cross-harness shims — the registry and per-harness contracts

## Intent

Define the shim set that makes a consumer repo's SDD rules discoverable to every supported LLM agent harness, regardless of which harness discovers which file.

## Invariants

1. **Registry externalised.** The set of harnesses and their shim paths + frontmatter is defined in `src/kanon/templates/harnesses.yaml`, not hardcoded in Python.
2. **Shims are pointers.** Every shim file is a single-line reference to `AGENTS.md`. The exact form depends on the harness:
   - `CLAUDE.md` — `See @AGENTS.md\n` (Claude Code reads `@AGENTS.md` as an import directive).
   - Harnesses that don't support imports — a one-line sentence `Read and follow the instructions in AGENTS.md at the repo root.` with any frontmatter the harness requires.
3. **V0.1 harness set.** `kanon init` writes all of these by default:
   - `CLAUDE.md` (Claude Code)
   - `.kiro/steering/kanon.md` (Kiro)
   - `.cursor/rules/kanon.mdc` (Cursor — `alwaysApply: true` frontmatter)
   - `.github/copilot-instructions.md` (GitHub Copilot)
   - `.windsurf/rules/kanon.md` (Windsurf — `trigger: always_on` frontmatter)
   - `.clinerules/kanon.md` (Cline)
   - `.roo/rules/kanon.md` (Roo Code)
   - `.aiassistant/rules/kanon.md` (JetBrains AI)
4. **`AGENTS.md` at repo root is the canonical root.** No shim duplicates content from it.
5. **Harness YAML schema.** Each registry entry carries:
   ```yaml
   - name: cursor
     path: .cursor/rules/kanon.mdc
     frontmatter:
       description: kanon boot chain
       alwaysApply: true
     body: |
       Read and follow the instructions in `AGENTS.md` at the repo root.
   ```
6. **Adding a new harness.** A new entry in `harnesses.yaml` + a new kit release is sufficient. No Python change required.
7. **Opt-out.** `init --skip-harness <name>` skipping is deferred to v0.2. In v0.1, all shims are written.

## Rationale

Sensei has shipped this exact shim set for months with no reliability issues. The `harnesses.yaml` externalisation is the only change from Sensei's pattern — motivated by wanting new-harness additions to be a data-file PR, not a code release.

## Out of Scope

- Auto-detecting which harness is currently in use at `init` time.
- Per-harness content customisation (every harness gets the same `AGENTS.md` pointer).

## Decisions

See ADR-0003.
