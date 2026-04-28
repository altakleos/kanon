---
status: accepted
design: "Follows ADR-0003"
date: 2026-04-22
realizes:
  - P-cross-link-dont-duplicate
stressed_by:
  - onboarding-agent
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
invariant_coverage:
  INV-cross-harness-shims-registry-externalised:
    - tests/test_kit_integrity.py::test_harnesses_yaml_is_valid
  INV-cross-harness-shims-shims-are-pointers:
    - tests/test_cli.py::test_shims_are_pointers_not_duplicates
  INV-cross-harness-shims-v01-harness-set:
    - tests/test_cli.py::test_init_writes_all_shims
  INV-cross-harness-shims-agents-md-canonical-root:
    - tests/test_cli.py::test_shims_are_pointers_not_duplicates
  INV-cross-harness-shims-harness-yaml-schema:
    - tests/test_kit_integrity.py::test_harnesses_yaml_is_valid
  INV-cross-harness-shims-adding-new-harness:
    - tests/test_cli.py::test_load_harnesses_missing_file
  INV-cross-harness-shims-harness-selection:
    - tests/test_cli.py::test_init_writes_all_shims
---
# Spec: Cross-harness shims — the registry and per-harness contracts

## Intent

Define the shim set that makes a consumer repo's SDD rules discoverable to every supported LLM agent harness, regardless of which harness discovers which file.

## Invariants

<!-- INV-cross-harness-shims-registry-externalised -->
1. **Registry externalised.** The set of harnesses and their shim paths + frontmatter is defined in `src/kanon/kit/harnesses.yaml`, not hardcoded in Python.
<!-- INV-cross-harness-shims-shims-are-pointers -->
2. **Shims are pointers.** Every shim file is a single-line reference to `AGENTS.md`. The exact form depends on the harness:
   - `CLAUDE.md` — `See @AGENTS.md\n` (Claude Code reads `@AGENTS.md` as an import directive).
   - Harnesses that don't support imports — a one-line sentence `Read and follow the instructions in AGENTS.md at the repo root.` with any frontmatter the harness requires.
<!-- INV-cross-harness-shims-v01-harness-set -->
3. **Harness set.** The kit registry contains shims for all supported harnesses (see INV-5 for the schema). `kanon init` writes a subset determined by the `--harness` flag:
   - `--harness <name>` (repeatable) — write only the named shims. Names match the `name:` field in `harnesses.yaml`.
   - `--harness auto` (the default when no `--harness` flag is given) — detect which harness config directories already exist in the target (e.g., `.cursor/` → write the Cursor shim). If none detected, write only `CLAUDE.md`.
   - `AGENTS.md` is always written regardless of `--harness` selection.
   - `kanon upgrade` writes all shims unconditionally (backward-compatible; existing projects have already committed their shims).
<!-- INV-cross-harness-shims-agents-md-canonical-root -->
4. **`AGENTS.md` at repo root is the canonical root.** No shim duplicates content from it.
<!-- INV-cross-harness-shims-harness-yaml-schema -->
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
<!-- INV-cross-harness-shims-adding-new-harness -->
6. **Adding a new harness.** A new entry in `harnesses.yaml` + a new kit release is sufficient. No Python change required.
<!-- INV-cross-harness-shims-harness-selection -->
7. **Harness selection.** `--harness auto` inspects the target directory for existing harness config directories (the parent directory of each shim's `path:` in the registry). A match means the consumer uses that harness. When no directories match, `CLAUDE.md` is the sole default — it is the most widely adopted agent harness file.

## Rationale

Sensei has shipped this exact shim set for months with no reliability issues. The `harnesses.yaml` externalisation is the only change from Sensei's pattern — motivated by wanting new-harness additions to be a data-file PR, not a code release.

## Out of Scope

- Per-harness content customisation (every harness gets the same `AGENTS.md` pointer).

## Decisions

See ADR-0003.
