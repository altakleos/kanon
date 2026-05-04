---
status: accepted
date: 2026-05-04
depth-min: 2
invoke-when: Preparing a release at depth 2, or the user asks to automate release preflight checks
---
# Protocol: Preflight Automation

## Purpose

Ensure release preflight checks are configured as executable automation rather than manual steps, so `kanon preflight` enforces them automatically.

## Steps

### 1. Check existing preflight configuration

Read `.kanon/config.yaml` for `preflight-stages:` entries. If a `release` stage already exists with commands, verify they cover the project's needs and skip to step 4.

### 2. Derive checks from the release checklist

Read the `release-checklist` protocol (depth 1). Identify which validation steps can be automated: test suite, linter, type checker, `kanon verify`, changelog entry check, version-string consistency.

### 3. Configure preflight stages

Add a `release` stage to `.kanon/config.yaml` `preflight-stages:` with commands for each automatable check. Example:

```yaml
preflight-stages:
  release:
    - label: tests
      cmd: pytest -x -q
    - label: lint
      cmd: ruff check src/ tests/
    - label: verify
      cmd: kanon verify .
```

### 4. Verify the automation

Run `kanon preflight . --stage release` and confirm all checks pass or produce actionable failures.

## Exit criteria

- `.kanon/config.yaml` has a `release` preflight stage with at least one command.
- `kanon preflight . --stage release` executes without configuration errors.
