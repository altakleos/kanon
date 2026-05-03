---
status: done
shipped-in: PR #73
slug: phase-a.8-scaffolded-ci-retirement
date: 2026-05-02
design: docs/design/distribution-boundary.md
---

# Plan: Phase A.8 — scaffolded `scripts/check_*.py` retirement

## Context

Per [ADR-0045](../../decisions/0045-de-opinionation-transition.md) §Decision step 8 / [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) de-opinionation. The substrate currently scaffolds CI scripts into consumer repos via four aspects' `files:` lists at depth-N:

- `kanon-deps` depth-2: `scripts/check_deps.py`
- `kanon-security` depth-2: `scripts/check_security_patterns.py`
- `kanon-testing` depth-3: `scripts/check_test_quality.py`
- `kanon-release` depth-2: `scripts/release-preflight.py`, `.github/workflows/release.yml`

Per de-opinionation, the substrate has no opinion about which CI tooling a consumer wires. Consumers compose their own CI; pre-baked scripts violate `P-protocol-not-product`.

**Important distinction:** the kanon repo's own `scripts/check_*.py` scripts at top-level are INTERNAL gates (not scaffolded to consumers). They stay. Only the SCAFFOLDED-to-consumer scripts are retired.

## Scope

### In scope

#### A. Delete scaffolded files from kit aspects

- `src/kanon/kit/aspects/kanon-deps/files/scripts/check_deps.py`
- `src/kanon/kit/aspects/kanon-security/files/scripts/check_security_patterns.py`
- `src/kanon/kit/aspects/kanon-testing/files/scripts/check_test_quality.py`
- `src/kanon/kit/aspects/kanon-release/files/scripts/release-preflight.py`
- `src/kanon/kit/aspects/kanon-release/files/.github/workflows/release.yml`

#### B. Remove from each aspect's `files:` list (LOADER MANIFEST + YAML)

For each of kanon-deps, kanon-security, kanon-testing, kanon-release:
- Delete `files: [ci/...]` entries at the relevant depth
- Delete `preflight:` blocks that referenced the scaffolded scripts (kanon-deps depth-2's `push:` `python scripts/check_deps.py`, kanon-security depth-2's `push:` `python scripts/check_security_patterns.py`, kanon-release depth-2's `release:` `python scripts/release-preflight.py --tag $TAG`)

In both:
- `src/kanon_reference/aspects/kanon_<X>.py` MANIFEST literals
- `src/kanon/kit/aspects/kanon-<X>/manifest.yaml`

#### C. Recapture `.kanon/fidelity.lock`

#### D. Audit tests

- `tests/test_e2e_lifecycle.py` and others may reference the scaffolded files. Update or delete obsolete assertions.

#### E. CHANGELOG entry under `[Unreleased] § Removed`.

### Out of scope

- The kanon repo's own internal `scripts/check_*.py` scripts (e.g., `scripts/check_links.py`, `scripts/check_foundations.py`, `scripts/check_kit_consistency.py`, etc.) — these are gates the kanon repo runs against itself, not scaffolded.
- Aspect content move — separate sub-plan.
- `_kit_root()` retirement in `_scaffold.py` — separate sub-plan.
- Substrate-independence CI gate — separate sub-plan.
- Migration script — A.9.

## Acceptance criteria

- [x] AC-D1..D5: 5 files deleted (4 ci/*.py + 1 .github/workflows/release.yml)
- [x] AC-M1..M4: 4 aspects' `files:` and `preflight:` lists updated in both LOADER MANIFEST + YAML
- [x] AC-F1: `.kanon/fidelity.lock` regenerated; `kanon verify .` returns ok
- [x] AC-T1: full pytest passes
- [x] AC-X1: CHANGELOG entry under § Removed
- [x] AC-X2..X8: standard gates green
