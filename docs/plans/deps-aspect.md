---
status: done
date: 2026-04-24
spec: ../specs/deps.md
adr: ../decisions/0023-deps-aspect.md
---
# Plan: Deps aspect implementation

## Goal

Ship the `deps` aspect (depth 0–2) as the sixth kanon aspect, following the same manifest-driven pattern as sdd, worktrees, release, testing, and security.

## Acceptance Criteria

- [x] ADR-0023 authored and indexed.
- [x] `src/kanon/kit/aspects/deps/` exists with manifest, agents-md (depth 0–2), sections, protocols, and files subdirectories.
- [x] Top-level `manifest.yaml` registers the deps aspect (experimental, depth 0–2, default 1, requires: []).
- [x] `kanon aspect add <target> deps` scaffolds protocol and AGENTS.md section at default depth.
- [x] `kanon aspect set-depth <target> deps 2` scaffolds `ci/check_deps.py`.
- [x] Self-hosting: `.kanon/protocols/kanon-deps/` contains canonical protocol copies; deps enabled at depth 2 on this repo.
- [x] Kit integrity tests pass for the new aspect.
- [x] CLI tests cover add and depth-2 scaffolding.
- [x] All existing tests still pass; coverage ≥ 90%.
- [x] `kanon verify .`, `ruff check` all clean.

## Tasks

1. Author ADR-0023, update decision index.
2. Update specs index with deps entry.
3. Create aspect directory tree: manifest.yaml, agents-md/depth-{0..2}.md, sections/dependency-hygiene.md, protocols/dependency-hygiene.md, files/ci/check_deps.py.
4. Register in top-level manifest.yaml.
5. Copy protocols to `.kanon/protocols/kanon-deps/`.
6. Enable deps at depth 2 on this repo.
7. Append kit integrity and CLI tests.
8. Verify: pytest, kit consistency, kanon verify, ruff.
