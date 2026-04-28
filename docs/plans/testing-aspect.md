---
status: accepted
date: 2026-04-24
spec: ../specs/testing.md
adr: ../decisions/0021-testing-aspect.md
---
# Plan: Testing aspect implementation

## Goal

Ship the `testing` aspect (depth 0–3) as the fourth kanon aspect, following the same manifest-driven pattern as sdd, worktrees, and release.

## Acceptance Criteria

- [ ] ADR-0021 authored and indexed.
- [ ] `src/kanon/kit/aspects/testing/` exists with manifest, agents-md (depth 0–3), sections, protocols, and files subdirectories.
- [ ] Top-level `manifest.yaml` registers the testing aspect (experimental, depth 0–3, default 1, requires: [], suggests: ["sdd >= 1"]).
- [ ] `kanon aspect add <target> testing` scaffolds protocol and AGENTS.md section at default depth.
- [ ] `kanon aspect set-depth <target> testing 3` scaffolds `ci/check_test_quality.py`.
- [ ] Self-hosting: `.kanon/protocols/kanon-testing/` contains canonical protocol copies; testing enabled at depth 3 on this repo.
- [ ] Kit integrity tests pass for the new aspect.
- [ ] CLI tests cover add and depth-3 scaffolding.
- [ ] All existing tests still pass; coverage ≥ 90%.
- [ ] `kanon verify .`, `ruff check`, `mypy` all clean.

## Tasks

1. Author ADR-0021, update decision index.
2. Update specs index with testing entry.
3. Create aspect directory tree: manifest.yaml, agents-md/depth-{0..3}.md, sections/test-discipline.md, protocols/{test-discipline,ac-first-tdd}.md, files/ci/check_test_quality.py.
4. Register in top-level manifest.yaml.
5. Copy protocols to `.kanon/protocols/kanon-testing/`.
6. Enable testing at depth 3 on this repo.
7. Append kit integrity and CLI tests.
8. Verify: pytest, kit consistency, kanon verify, ruff, mypy.
