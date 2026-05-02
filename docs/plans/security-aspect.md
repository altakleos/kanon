---
status: done
date: 2026-04-24
spec: ../specs/security.md
adr: ../decisions/0022-security-aspect.md
---
# Plan: Security aspect implementation

## Goal

Ship the `security` aspect (depth 0–2) as the fifth kanon aspect, following the same manifest-driven pattern as sdd, worktrees, release, and testing.

## Acceptance Criteria

- [x] ADR-0022 authored and indexed.
- [x] `src/kanon/kit/aspects/security/` exists with manifest, agents-md (depth 0–2), sections, protocols, and files subdirectories.
- [x] Top-level `manifest.yaml` registers the security aspect (experimental, depth 0–2, default 1, requires: []).
- [x] `kanon aspect add <target> security` scaffolds protocol and AGENTS.md section at default depth.
- [x] `kanon aspect set-depth <target> security 2` scaffolds `scripts/check_security_patterns.py`.
- [x] Self-hosting: `.kanon/protocols/kanon-security/` contains canonical protocol copies; security enabled at depth 2 on this repo.
- [x] Kit integrity tests pass for the new aspect.
- [x] CLI tests cover add and depth-2 scaffolding.
- [x] All existing tests still pass; coverage ≥ 90%.
- [x] `kanon verify .`, `ruff check`, `mypy` all clean.

## Tasks

1. Author ADR-0022, update decision index.
2. Update specs index with security entry.
3. Create aspect directory tree: manifest.yaml, agents-md/depth-{0..2}.md, sections/secure-defaults.md, protocols/secure-defaults.md, files/scripts/check_security_patterns.py.
4. Register in top-level manifest.yaml.
5. Copy protocols to `.kanon/protocols/kanon-security/`.
6. Enable security at depth 2 on this repo.
7. Append kit integrity and CLI tests.
8. Verify: pytest, kit consistency, kanon verify, ruff.
