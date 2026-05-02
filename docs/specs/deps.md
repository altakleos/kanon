---
status: accepted
design: "Follows ADR-0023"
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
  - tests/ci/test_check_deps.py
invariant_coverage:
  INV-deps-depth-range:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_deps_manifest_has_expected_depths
  INV-deps-protocol:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli_aspect.py::test_aspect_add_deps
  INV-deps-agents-md-section:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
  INV-deps-ci-validator:
    - tests/ci/test_check_deps.py::test_requirements_unpinned_detected
  INV-deps-no-dependency:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_deps_manifest_paths_resolve
  INV-deps-language-agnostic:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/ci/test_check_deps.py::test_package_json_caret_detected
  INV-deps-stability:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_kit_deps_aspect_dir_exists
---
# Spec: Deps — dependency hygiene for LLM-agent-driven repos

## Intent

Package the discipline of managing dependencies as an opt-in aspect. LLM agents add dependencies casually — unpinned versions, phantom imports without manifest entries, duplicate-purpose libraries, and typosquatting-suspicious packages. When multiple concurrent agents each add libraries independently, dependency sprawl becomes the #1 silent tech-debt vector. This aspect ships prose procedures that make agents dependency-aware before they run any install command.

The aspect is language-agnostic at all depths. The protocols describe *principles* of dependency hygiene, not package-manager-specific commands.

## Invariants

<!-- INV-deps-depth-range -->
1. **Depth range is 0–2.** The `deps` aspect declares `depth-range: [0, 2]`.
   - **Depth 0** — opt-out. Aspect enabled in config but no files scaffolded.
   - **Depth 1** — prose guidance. Protocol and AGENTS.md section scaffolded. Agents check existing dependencies before adding new ones, pin exact versions, and justify non-obvious additions.
   - **Depth 2** — prose guidance plus automation. CI validator scaffolded for dependency hygiene checks.

<!-- INV-deps-protocol -->
2. **Dependency-hygiene protocol.** The aspect ships one protocol at `.kanon/protocols/kanon-deps/dependency-hygiene.md` (depth ≥ 1) covering:
   - **Check before adding.** Before installing a new dependency, check if an existing dependency or the standard library already provides the functionality.
   - **Pin exact versions.** Use exact or pinned versions (`==`, not `>=` or `^`), not open ranges. Lock files are the source of truth for transitive dependencies.
   - **Justify additions.** Non-obvious dependencies get a comment or ADR explaining why they were chosen over alternatives.
   - **Prefer well-known packages.** Prefer actively maintained, widely adopted packages. Flag unusual or low-download-count packages that could be typosquatting variants.
   - **Manifest completeness.** Every import must have a corresponding entry in the project's dependency manifest (requirements.txt, pyproject.toml, package.json, Cargo.toml, go.mod, etc.). Phantom dependencies — imports that work locally but aren't declared — are bugs.
   - **Minimize dependency weight.** Don't add a 50MB library to parse a date string. Prefer lightweight alternatives or stdlib when the functionality needed is simple.
   - Frontmatter `invoke-when`: adding, removing, or updating a dependency.

<!-- INV-deps-agents-md-section -->
3. **AGENTS.md section.** At depth ≥ 1, the aspect contributes one marker-delimited section `deps/dependency-hygiene` to AGENTS.md — a short prose summary of the core rules so an operating agent sees the dependency discipline on the boot chain.

<!-- INV-deps-ci-validator -->
4. **CI validator (depth 2).** The aspect scaffolds `ci/check_deps.py` — a language-agnostic CI script that detects:
   - Unpinned version specifiers in common manifest formats (requirements.txt `>=`, pyproject.toml `>=`, package.json `^` or `~`).
   - Duplicate-purpose packages (best-effort heuristic — e.g., multiple HTTP libraries, multiple date-parsing libraries).
   The script outputs a JSON report with `{errors: [...], warnings: [...], status: "ok"|"fail"}` following the established CI script pattern. Detection is best-effort pattern-based.

<!-- INV-deps-no-dependency -->
5. **No cross-aspect dependency.** `deps` declares `requires: []`. Dependency hygiene is independently useful without SDD, testing, or any other aspect.

<!-- INV-deps-language-agnostic -->
6. **Language-agnostic at all depths.** Protocols describe dependency principles, not package-manager commands. The CI validator recognizes common manifest formats (requirements.txt, pyproject.toml, package.json, Cargo.toml, go.mod) but does not require any specific toolchain.

<!-- INV-deps-stability -->
7. **Stability: experimental.** First release ships as experimental until self-hosted and validated.

## Rationale

**Why an aspect.** Dependency decisions are judgment-shaped — "should I add this library?" is a question an agent answers before running a command. Prose guidance at the decision point is more effective than post-hoc scanning alone.

**Why depth 0–2.** Two natural layers: knowledge (when and how to add dependencies) and detection (automated scanning for hygiene violations). No meaningful third layer exists that isn't covered by dedicated tools (Dependabot, Renovate, pip-audit).

**Why no cross-aspect dependency.** A vibe-coding prototype (sdd depth 0) still shouldn't have phantom dependencies or unpinned versions.

**Why best-effort detection.** The CI validator uses pattern matching on manifest files, not full dependency resolution. This means it can't detect transitive conflicts or phantom imports (which require language-specific tooling). It catches the most common issues — unpinned versions and obvious duplicates — without requiring any runtime toolchain.

## Out of Scope

- **Vulnerability scanning.** pip-audit, npm audit, cargo-audit are dedicated tools. The CI validator does not check CVE databases.
- **License compliance.** Important but requires license-database integration, not prose.
- **Lockfile generation or management.** The protocol recommends lockfiles; it doesn't generate them.
- **Transitive dependency resolution.** Requires language-specific tooling.
- **Monorepo dependency deduplication.** Too project-specific.

## Decisions

See:
- **ADR-0023** — deps aspect (dependency-hygiene protocol, CI validator, language-agnostic design).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
