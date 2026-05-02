---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: A release is being prepared, or the user asks to cut a release
---
# Protocol: Release checklist

## Purpose

Guide agents through the full release lifecycle — from preparation through validation, tagging, publishing, and post-release verification. The goal is zero broken releases: every publish is preceded by automated checks.

## Steps

### 1. Prepare

- Confirm the target version number with the user.
- Ensure all planned changes are merged to the release branch.
- Verify no open blockers or critical issues remain.

### 2. Bump

- Update `__version__` in the project's canonical version source.
- Add a CHANGELOG entry for the new version with all user-visible changes.
- Commit the version bump: `git commit -m "release: vX.Y.Z"`.

### 3. Validate

Run the full preflight suite:

- `pytest` — all tests pass.
- `ruff check` — no lint violations.
- `kanon verify .` — project shape is valid.
- If depth 2: `python ci/release-preflight.py --tag vX.Y.Z` — automated preflight.

### 4. Tag

- Create an annotated tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
- Push the tag: `git push origin vX.Y.Z`.

### 5. Publish

- CI workflow triggers on tag push and handles build + publish.
- Monitor the workflow run for failures.
- If CI is unavailable, build and publish manually as a fallback.

### 6. Verify

- Confirm the package is available on the target registry.
- Install the published version in a clean environment and run a smoke test.

## Exit criteria

- The tagged version is published and installable.
- CHANGELOG reflects all changes in the release.
- No preflight check was skipped.
