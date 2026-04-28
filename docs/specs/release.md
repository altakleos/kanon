---
status: accepted
design: "Follows ADR-0017"
date: 2026-04-24
realizes:
  - P-prose-is-code
  - P-tiers-insulate
stressed_by:
  - solo-with-agents
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
invariant_coverage:
  INV-release-depth-range:
    - tests/test_kit_integrity.py::test_release_manifest_has_expected_depths
  INV-release-protocol-shaped:
    - tests/test_cli.py::test_aspect_add_release
  INV-release-agents-md-section:
    - tests/test_kit_integrity.py::test_release_agents_md_exists_per_depth
  INV-release-reference-automation-snippets:
    - tests/test_cli.py::test_release_depth_2_has_ci_files
  INV-release-non-destructive-lifecycle:
    - tests/test_cli.py::test_aspect_remove_leaves_files
  INV-release-no-cross-aspect-dependency:
    - tests/test_kit_integrity.py::test_release_manifest_paths_resolve
  INV-release-stability-experimental:
    - tests/test_kit_integrity.py::test_kit_release_aspect_dir_exists
---
# Spec: Release — disciplined release publishing for LLM-agent-driven repos

## Intent

Package the discipline of cutting releases — version bumping, changelog enforcement, tag signing, wheel validation, and PyPI publishing — as an opt-in aspect. Today, kanon's own release process is manual knowledge encoded in CI workflows and contributor memory. This spec defines a `release` aspect that ships prose procedures and reference automation snippets (per ADR-0013) so agents can execute a release with the same rigor as a human who has done it before.

The primary user is a solo developer with LLM agents who wants a repeatable, auditable release process without reinventing the pipeline for each project.

## Invariants

<!-- INV-release-depth-range -->
1. **Depth range is 0–2.** The `release` aspect declares `depth-range: [0, 2]`.
   - **Depth 0** — opt-out. Aspect enabled in config but no files scaffolded.
   - **Depth 1** — prose guidance. Protocol file and AGENTS.md section are scaffolded. Agents understand the release checklist and apply judgment on when/how to cut a release.
   - **Depth 2** — prose guidance plus automation. Reference CI templates (GitHub Actions workflow) and a pre-release validation script are scaffolded alongside the protocol and AGENTS.md section.

<!-- INV-release-protocol-shaped -->
2. **Protocol-shaped.** The aspect ships one protocol at `.kanon/protocols/kanon-release/release-checklist.md` (depth ≥ 1) covering: version bump procedure, changelog validation, pre-release checks (tests pass, lint clean, verify ok), tag creation, wheel build + validation, and the publish gate (the final step where the built artifact is pushed to the package registry — typically triggered by a CI workflow on tag push, not by the agent directly). Frontmatter `invoke-when` names **a release is being prepared** as the trigger.

<!-- INV-release-agents-md-section -->
3. **AGENTS.md section.** At depth ≥ 1, the aspect contributes one marker-delimited section `release/publishing-discipline` to AGENTS.md — a short prose summary of the release checklist so an operating agent sees the rules on the boot chain.

<!-- INV-release-reference-automation-snippets -->
4. **Reference automation snippets** (per ADR-0013, depth-2 only). The aspect scaffolds:
   - `ci/release-preflight.py` — a standalone validation script that checks: version in `__init__.py` matches tag, CHANGELOG has an entry for the version, tests pass, lint clean, `kanon verify` passes. Exit 0 or 1.
   - `.github/workflows/release.yml` — a reference GitHub Actions workflow for build + validate + publish via trusted publishing.
   
   These are copy-in templates the consumer adapts to their needs. Byte-equality is **not** enforced after scaffolding — consumers are expected to customize CI workflows and validation scripts for their project's specific needs.

<!-- INV-release-non-destructive-lifecycle -->
5. **Non-destructive lifecycle.** Adding the release aspect does not modify existing CI files. Removing it leaves scaffolded files on disk. The reference workflow is a template — consumers adapt it to their needs.

<!-- INV-release-no-cross-aspect-dependency -->
6. **No cross-aspect dependency.** `release` declares `requires: []`. Release discipline is independently useful — a project may want a repeatable release process without SDD ceremony. Projects that also use `sdd` benefit from plan-before-build, but it is not a prerequisite.

<!-- INV-release-stability-experimental -->
7. **Stability: experimental.** First release ships as experimental until self-hosted and validated on at least one real release cycle.

## Rationale

**Why an aspect, not just CI templates.** CI templates are mechanical — they run commands. The judgment layer (when to release, what version to bump, how to validate the changelog) is prose that agents read. Packaging both as an aspect means the prose and automation travel together and depth-dial controls how much ceremony a project wants.

**Why depth 0–2, not binary.** Same reasoning as worktrees: the knowledge layer (protocol + AGENTS.md section) and the automation layer (CI templates + validation script) are independently useful. A project using GitLab CI doesn't want GitHub Actions templates but still wants the release checklist.

**Why no sdd dependency.** Release discipline is independently useful. A project using kanon solely for release automation shouldn't be forced into plan-before-build. Projects that also enable `sdd` get the plan gate naturally; the release protocol's checklist works either way.

## Out of Scope

- **Package manager support beyond PyPI.** npm, cargo, etc. are future aspects or consumer extensions.
- **Automated version bumping logic.** The protocol describes the decision; the human/agent chooses the version.
- **Tag signing key management.** The protocol mentions signing; key setup is the consumer's responsibility.
- **Release notes generation from git log.** The changelog is the source of truth, not generated.
- **Multi-package monorepo releases.** Single-package repos only.

## Decisions

See:
- **ADR-0017** — release aspect (scaffolding shape, depth progression, reference automation).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
