---
status: draft
serves: docs/specs/scaffold-v2.md
design: "Supersedes ADR-0010 § enforcement-proximity (refines); extends ADR-0012, ADR-0016"
touches:
  - src/kanon/kit/manifest.yaml
  - src/kanon/kit/aspects/*/manifest.yaml
  - src/kanon/_manifest.py
  - src/kanon/_scaffold.py
  - src/kanon/cli.py
  - AGENTS.md
  - docs/development-process.md
  - .kanon/protocols/
  - tests/
---

# Plan: Scaffold v2 implementation

Implements `docs/specs/scaffold-v2.md` in 5 phases. Each phase is
independently mergeable and leaves the project in a passing state.

## Phase 1: Manifest schema (INV-1, INV-8)

Add the three file categories to the manifest.

- [ ] P1-T1: Add `files:` key to top-level manifest.yaml for kit-global
  files. Move `.kanon/kit.md` there. Create `src/kanon/kit/files/`
  directory.
- [ ] P1-T2: Add `files:` key support to each aspect sub-manifest
  (aspect-level files). Initially empty for all aspects.
- [ ] P1-T3: Update `_aspect_files()` in `_manifest.py` to prepend
  aspect-level `files:` before the depth union.
- [ ] P1-T4: Update `_build_bundle()` in `_scaffold.py` to read
  kit-global files first.
- [ ] P1-T5: Update `_expected_files()` to include kit-global and
  aspect-level files.
- [ ] P1-T6: Rewrite `kit.md` template to be aspect-neutral (no
  sdd-specific references).
- [ ] P1-T7: Tests for kit-global and aspect-level file resolution.

## Phase 2: Content moves (INV-5, INV-6, INV-7)

Move inlined AGENTS.md content to protocol files. Eliminate sections.

- [ ] P2-T1: Create protocol files for content that only exists as
  AGENTS.md sections today:
  - `.kanon/protocols/kanon-sdd/plan-before-build.md`
  - `.kanon/protocols/kanon-sdd/spec-before-design.md`
  - `.kanon/protocols/kanon-worktrees/branch-hygiene.md`
  - `.kanon/protocols/kanon-release/publishing-discipline.md`
  - `.kanon/protocols/kanon-fidelity/fidelity-discipline.md`
- [ ] P2-T2: Delete all `sections/` directories from kit aspects.
  Remove `sections:` keys from all sub-manifests.
- [ ] P2-T3: Delete all `agents-md/` body files from kit aspects.
- [ ] P2-T4: Rename `docs/development-process.md` →
  `docs/sdd-method.md`. Trim to ~50 lines (layer stack, routing,
  document authority, glossary). Remove duplicated gate prose.
  Move depth-specific content to artifact-directory READMEs.
- [ ] P2-T5: Update all cross-references to development-process.md
  (~30 living documents; leave ADR references as historical).
- [ ] P2-T6: Update byte-equality entries in sdd sub-manifest.
- [ ] P2-T7: Mirror new protocol files to kit aspect protocol dirs.

## Phase 3: AGENTS.md routing index (INV-3, INV-4, INV-9)

Rewrite AGENTS.md assembly to produce the slim routing index.

- [ ] P3-T1: Rewrite `agents-md-base.md` template to the ~80-line
  routing index (identity, boot chain, layout, constraints, hard-gates
  table, task playbook, quick-start, protocols-index placeholder,
  contribution conventions, references).
- [ ] P3-T2: Simplify `_assemble_agents_md()` — remove body injection,
  section filling, inactive-section cleanup. Keep only: load base +
  render protocols-index.
- [ ] P3-T3: Update `_render_protocols_index()` to include former
  discipline protocols (plan-before-build, spec-before-design,
  branch-hygiene, etc.) in the table.
- [ ] P3-T4: Remove marker-section logic from `_merge_agents_md()`
  (upgrade path).
- [ ] P3-T5: Update `ci/check_kit_consistency.py` to remove
  section-file byte-equality checks.

## Phase 4: sdd de-privileging (INV-2, INV-10)

Make sdd fully optional.

- [ ] P4-T1: Remove CLAUDE.md from sdd depth-0 files (it's a harness
  shim, handled by harnesses.yaml).
- [ ] P4-T2: Change worktrees `requires: "kanon-sdd >= 1"` to
  `suggests: "kanon-sdd >= 1"`. Audit other aspects for sdd
  hard-dependencies.
- [ ] P4-T3: Update `_default_aspects()` — move the sdd:1 default
  to CLI layer (init command default), not manifest truth.
- [ ] P4-T4: Handle zero-aspect edge case in `kanon verify` (warn,
  don't error).
- [ ] P4-T5: Test: `kanon init --aspects worktrees:1,testing:1`
  produces valid project with no sdd files.
- [ ] P4-T6: Test: `kanon init --aspects ""` (bare) produces minimal
  valid project.

## Phase 5: ADR + cleanup

- [ ] P5-T1: Write superseding ADR for ADR-0010 (refines
  enforcement-proximity: hard gates inline as compressed table,
  soft guidance protocol-only).
- [ ] P5-T2: Update `docs/specs/README.md` with scaffold-v2 entry.
- [ ] P5-T3: Update `docs/plans/README.md` with this plan.
- [ ] P5-T4: Update `CHANGELOG.md` with all changes.
- [ ] P5-T5: Regenerate `fidelity.lock`.
- [ ] P5-T6: Run full test suite + `kanon verify .` + all CI scripts.

## Acceptance criteria

1. `kanon init` with no flags produces a valid project (sdd:1 default).
2. `kanon init --aspects worktrees:1,testing:1` produces a valid
   project with zero sdd files.
3. AGENTS.md at depth 3 is ≤100 lines.
4. AGENTS.md at depth 1 is ≤70 lines.
5. No content is duplicated between AGENTS.md and protocol files.
6. All existing tests pass (updated as needed).
7. `kanon verify .` passes on the self-hosting repo.
8. All CI scripts pass.
