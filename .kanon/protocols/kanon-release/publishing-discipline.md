---
status: accepted
date: 2026-04-28
depth-min: 1
invoke-when: A release is being prepared, or executing release publish steps
---
# Protocol: Publishing Discipline

## Purpose

Ensure every release follows a strict sequence with no skipped validation.

## Steps

### 1. Version bump

Update `__version__` in `__init__.py` (or the project's canonical version source) and add a CHANGELOG entry for the new version before any other release step.

### 2. Pre-release checks

All of the following must pass before tagging:

- Full test suite (`pytest`)
- Lint (`ruff check`)
- `kanon verify .`

### 3. Tag creation

Create an annotated tag `vX.Y.Z` only after all checks pass. Never tag a dirty tree or a commit with failing checks.

### 4. Publish

CI workflow triggered by tag push handles build and publish. Manual `twine upload` or equivalent is a fallback, not the default.

### 5. CHANGELOG

CHANGELOG is the source of truth for release notes. Every user-visible change gets an entry before the release tag is created.

## Anti-patterns

- **Publishing without passing preflight checks.** A release that skips validation is a rollback waiting to happen.

## Exit criteria

- All pre-release checks passed.
- Annotated tag created on a clean tree.
- CHANGELOG entry exists for the release version.
