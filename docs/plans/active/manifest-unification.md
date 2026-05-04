---
status: in-progress
date: 2026-05-04
adr: ../decisions/0055-manifest-unification.md
---
# Plan: Manifest unification (ADR-0055)

## Goal

Collapse the triple manifest representation into one YAML per aspect + a mechanical trampoline loader.

## Tasks

### Phase 1: Merge registry fields into per-aspect manifest.yaml (7 aspects)
- [ ] kanon-sdd: merge stability/depth-range/default-depth/description/requires/provides/suggests from kit/manifest.yaml into aspect manifest.yaml
- [ ] kanon-worktrees: same
- [ ] kanon-testing: same
- [ ] kanon-release: same
- [ ] kanon-security: same
- [ ] kanon-deps: same
- [ ] kanon-fidelity: same

### Phase 2: Replace loader.py with trampoline (7 aspects)
- [ ] Replace all 7 loader.py files with the 3-line importlib.resources trampoline
- [ ] Add pyyaml to kanon-aspects pyproject.toml dependencies (explicit, not just transitive)
- [ ] Verify manifest.yaml is included in wheel package data

### Phase 3: Simplify core loading
- [ ] Simplify _load_aspect_manifest() to return entry-point dict for kanon-* aspects
- [ ] Remove kit/manifest.yaml aspects block (or reduce to path-only)
- [ ] Update check_kit_consistency.py if it reads the old structure

### Phase 4: Cleanup
- [ ] Delete or simplify test_kanon_reference_manifests.py (drift test no longer needed)
- [ ] Update any other tests that reference the old loader.py structure
- [ ] Verify all tests pass

## Acceptance criteria

- Each aspect has exactly one source of truth: manifest.yaml
- Each loader.py is ≤5 lines (trampoline only)
- _load_aspect_manifest() has one code path for kit aspects (entry-point dict)
- All existing tests pass
- `kanon verify .` passes on the self-hosted repo
