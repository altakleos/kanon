---
status: accepted
design: "Follows ADR-0021"
date: 2026-04-24
realizes:
  - P-verification-co-authored
  - P-specs-are-source
stressed_by:
  - solo-engineer
  - solo-with-agents
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
  - tests/ci/test_check_test_quality.py
invariant_coverage:
  INV-testing-depth-range:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_testing_manifest_has_expected_depths
  INV-testing-test-discipline-protocol:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli_aspect.py::test_aspect_add_testing
  INV-testing-ac-first-protocol:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli_aspect.py::test_aspect_add_testing
  INV-testing-agents-md-section:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
  INV-testing-coverage-floor-config:
    - tests/test_cli_aspect.py::test_aspect_add_testing
  INV-testing-ci-validator:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli_aspect.py::test_testing_depth_3_has_ci_script
    - tests/ci/test_check_test_quality.py::test_trivial_pass_body_detected
  INV-testing-no-dependency:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_testing_manifest_paths_resolve
  INV-testing-language-agnostic:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/ci/test_check_test_quality.py::test_find_test_files_patterns
  INV-testing-stability:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_kit_testing_aspect_dir_exists
---
# Spec: Testing — test discipline for LLM-agent-driven repos

## Intent

Package the discipline of writing, maintaining, and enforcing tests as an opt-in aspect. LLM agents default to implementation-first and optimize for "tests pass" rather than "tests protect." Without explicit discipline, agents silently delete failing tests, weaken assertions, write tests that verify mocks instead of behavior, and skip edge cases. This aspect ships prose procedures that make agents test-disciplined contributors: tests accompany code, acceptance criteria become executable tests before implementation begins, and test quality is mechanically auditable.

The aspect is language-agnostic at all depths. The protocols describe *when* and *why* to test, not *which framework* to use.

## Invariants

<!-- INV-testing-depth-range -->
1. **Depth range is 0–3.** The `testing` aspect declares `depth-range: [0, 3]`.
   - **Depth 0** — opt-out. Aspect enabled in config but no files scaffolded.
   - **Depth 1** — test discipline. Protocol and AGENTS.md section scaffolded. Agents write tests alongside code, never silently delete or weaken tests, prefer test-first.
   - **Depth 2** — AC-first + TDD. Second protocol scaffolded. Agents translate plan acceptance criteria into failing tests before implementation. For spec invariants, agents follow red-green-refactor. Feeds `verified-by` traceability.
   - **Depth 3** — automated enforcement. CI validator scaffolded for test anti-pattern detection.

<!-- INV-testing-test-discipline-protocol -->
2. **Test-discipline protocol.** The aspect ships a protocol at `.kanon/protocols/kanon-testing/test-discipline.md` (depth ≥ 1) covering:
   - Tests accompany code changes — every new function/behavior gets a test in the same commit or adjacent commit.
   - Tests are not deleted without justification. When removing a test, document what now covers the behavior it protected, or acknowledge the coverage gap. Never delete a test solely because it's failing — fix the code or fix the test.
   - Assertions are not weakened to make tests pass. Changing an expected value requires explaining why the old value was wrong.
   - Prefer test-first: before implementing, consider "how will I verify this works?" and let that shape the implementation.
   - Coverage floor: maintain coverage at or above the floor declared in `.kanon/config.yaml` (`aspects.testing.config.coverage_floor`, default 80 if unset).
   - Frontmatter `invoke-when`: writing or modifying code.

<!-- INV-testing-ac-first-protocol -->
3. **AC-first + TDD protocol.** The aspect ships a second protocol at `.kanon/protocols/kanon-testing/ac-first-tdd.md` (depth ≥ 2) covering:
   - **AC-first testing:** Before implementing a plan's tasks, read its `## Acceptance Criteria` (or `## Success Criteria`) section. For each criterion that can be expressed as an executable test, write a failing test. Implement until all AC tests pass. If a criterion is untestable as written, rewrite it to be testable — vague AC is a plan defect, not a testing problem.
   - **TDD from spec invariants:** When implementing a task that touches a spec invariant (`INV-*`), write a failing test for that invariant first. Implement until it passes. Refactor while keeping it green. Update the spec's `invariant_coverage:` frontmatter to reference the test.
   - **The implementation loop:** The agent iterates on implementation, not on weakening tests. A failing test is a signal that the implementation is wrong, not that the test is wrong. This loop (test → implement → fail → fix → repeat) converges because the test encodes the intended behavior and the agent adjusts implementation to match.
   - **Escape hatches:** Config changes, prose/documentation edits, and UI/template work that cannot be meaningfully unit-tested are exempt from test-first. Document how you verified these changes instead.
   - Frontmatter `invoke-when`: implementing a plan or spec invariant at testing depth ≥ 2.

<!-- INV-testing-agents-md-section -->
4. **AGENTS.md section.** At depth ≥ 1, the aspect contributes one marker-delimited section `testing/test-discipline` to AGENTS.md — a short prose summary of the core rules (tests accompany code, no silent deletion, prefer test-first, coverage floor) so an operating agent sees the discipline on the boot chain.

<!-- INV-testing-coverage-floor-config -->
5. **Coverage floor in config.** The coverage floor is declared in `.kanon/config.yaml` under `aspects.testing.config.coverage_floor` as an integer (percentage). Default is 80 if the key is absent. The protocol references this value. Enforcement is prose-based at depths 1–2 (the agent reads the value and maintains coverage). At depth 3, the CI validator checks it mechanically.

<!-- INV-testing-ci-validator -->
6. **CI validator (depth 3).** The aspect scaffolds `ci/check_test_quality.py` — a language-agnostic CI script that detects test anti-patterns:
   - Tests with no assertions (empty test bodies, `assert True`, `pass`-only).
   - Tests where assertions target only mock return values (best-effort pattern-based detection — language-specific mock frameworks may not be recognized).
   - Test files with zero test functions.
   - Coverage below the configured floor (reads `coverage_floor` from config, delegates to the project's coverage tool).
   The script outputs a JSON report with `{errors: [...], warnings: [...], status: "ok"|"fail"}` following the established CI script pattern.

<!-- INV-testing-no-dependency -->
7. **No cross-aspect dependency.** `testing` declares `requires: []`. Test discipline is independently useful without SDD, worktrees, or release. At depth 2, the AC-first protocol references plans and spec invariants — if `sdd` is not enabled, those steps are skipped gracefully. The manifest declares `suggests: ["sdd >= 1"]` to recommend SDD for the full AC-first workflow.

<!-- INV-testing-language-agnostic -->
8. **Language-agnostic at all depths.** Protocols describe testing principles, not framework-specific commands. The CI validator at depth 3 uses generic heuristics (empty test bodies, no-assertion detection) that make no language-specific assumptions. No language-specific config templates are scaffolded — consumers configure their own test runners.

<!-- INV-testing-stability -->
9. **Stability: experimental.** First release ships as experimental until self-hosted and validated on at least one real project.

## Rationale

**Why test-first preference, not strict TDD mandate.** Strict TDD (you MUST write a failing test before every implementation line) over-prescribes for config changes, prose edits, UI work, and exploratory prototyping. "Prefer test-first" captures the design benefit (thinking about verification before implementation) without blocking legitimate workflows. The escape hatches at depth 2 make this explicit.

**Why AC-first is the headline at depth 2.** Research shows LLMs benefit enormously from tests-as-stopping-conditions — the agent iterates against a concrete oracle rather than declaring victory prematurely. Plan acceptance criteria are written by humans, so the agent isn't inventing what to test — it's translating human intent into executable checks. This sidesteps the "LLM writes tests that mirror its own implementation" problem.

**Why depth 0–3, not 0–2.** Unlike worktrees and release (which have two layers: knowledge + automation), testing has three distinct layers: (1) behavioral rules (don't delete tests), (2) workflow discipline (AC-first, TDD loop), and (3) mechanical enforcement (CI validator). Each layer adds genuine, separable value. A project can want "don't delete my tests" without TDD, and TDD without CI enforcement.

**Why no cross-aspect dependency.** A project might want test discipline without SDD ceremony. "Write tests with your code" is useful at sdd depth 0 (vibe-coding). The `suggests: ["sdd >= 1"]` field recommends SDD for the full AC-first workflow without gating it.

**Why language-agnostic.** kanon is portable across languages. Prescribing pytest config would exclude JavaScript, Go, and Rust projects. The protocols describe *principles* (test-first, no silent deletion, coverage floor); consumers choose their framework. The depth-3 CI validator uses generic heuristics that work across languages.

**Why "tests protect" not "tests pass."** The core insight: LLM agents optimize for green CI. The testing aspect reframes the goal — tests exist to protect behavior, not to produce a green badge. Every rule in the protocol (no silent deletion, no assertion weakening, test-first preference) serves this reframing.

## Out of Scope

- **Language-specific test framework configuration.** No pytest.ini, jest.config, or Cargo.toml test sections. Consumers configure their own runners.
- **Mocking strategy prescriptions.** Too language-specific and opinionated.
- **Performance, load, or stress testing.** Different discipline entirely.
- **Test data management.** Too project-specific.
- **Mutation testing.** Interesting but too heavy for an aspect.
- **Cross-agent test coordination.** Belongs in the deferred `multi-agent-coordination` spec.
- **Test generation from specs.** The "generate code from specs" non-goal (vision doc) applies here too.
- **Coverage percentage as a hard gate in `kanon verify`.** Coverage is prose-enforced at depths 1–2 and CI-enforced at depth 3. `kanon verify` does not run test suites.

## Decisions

See:
- **ADR-0021** — testing aspect (depth model, AC-first protocol, language-agnostic design, coverage floor config).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
