---
status: done
date: 2026-05-04
adr: ../decisions/0055-manifest-unification.md
---
# Plan: Manifest unification (ADR-0055)

## Goal

Collapse the triple manifest representation into one YAML per aspect + a mechanical trampoline loader.

## Tasks

### Phase 1: Merge registry fields into per-aspect manifest.yaml (7 aspects)
- [x] kanon-sdd: merge stability/depth-range/default-depth/description/requires/provides/suggests from kit/manifest.yaml into aspect manifest.yaml
- [x] kanon-worktrees: same
- [x] kanon-testing: same
- [x] kanon-release: same
- [x] kanon-security: same
- [x] kanon-deps: same
- [x] kanon-fidelity: same

### Phase 2: Replace loader.py with trampoline (7 aspects)
- [x] Replace all 7 loader.py files with the 3-line importlib.resources trampoline
- [x] Add pyyaml to kanon-aspects pyproject.toml dependencies (already present)
- [x] Verify manifest.yaml is included in wheel package data

### Phase 3: Simplify core loading
- [x] Simplify _load_aspect_manifest() to return entry-point dict for kanon-* aspects
- [x] Add deprecation comment to kit/manifest.yaml aspects block
- [x] check_kit_consistency.py unchanged (still works)

### Phase 4: Cleanup
- [x] Simplify test_kanon_reference_manifests.py (drift test → key presence test)
- [x] All 967 tests pass
- [x] 93% coverage maintained

## Acceptance criteria

- [x] Each aspect has exactly one source of truth: manifest.yaml
- [x] Each loader.py is ≤5 lines (trampoline only)
- [x] _load_aspect_manifest() has one code path for kit aspects (entry-point dict)
- [x] All existing tests pass
