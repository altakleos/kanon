---
status: done
date: 2026-04-30
---
# Plan: CI DRY + narrow exception handling

## Goal

1. Extract shared CI steps from verify.yml and release.yml into a reusable workflow.
2. Narrow `except Exception` to specific types in _verify.py, _preflight.py, _atomic.py.

## Tasks

### CI DRY
- [x] Create `.github/workflows/checks.yml` as a reusable workflow (workflow_call) containing the shared lint/typecheck/ci-check steps
- [x] Refactor `verify.yml` to call the reusable workflow
- [x] Refactor `release.yml` to call the reusable workflow

### Narrow exceptions
- [x] `_verify.py:220` — `_aspect_validators()` loads YAML manifests → narrow to `(OSError, yaml.YAMLError, KeyError, TypeError)`
- [x] `_verify.py:244,296` — `check(target, errors, warnings)` calls user/kit validators → keep `except Exception` (intentional: arbitrary third-party code)
- [x] `_verify.py:273` — `_aspect_depth_validators()` loads kit manifests → narrow to `(OSError, yaml.YAMLError, KeyError, TypeError)`
- [x] `_verify.py:339` — `_aspect_provides()` reads manifest capabilities → narrow to `(OSError, yaml.YAMLError, KeyError, TypeError)`
- [x] `_preflight.py:108` — `subprocess.run()` → narrow to `OSError`
- [x] `_atomic.py:41` — file I/O (open, write, fsync, replace) → narrow to `OSError`

## Acceptance criteria

- [x] verify.yml and release.yml share a single reusable workflow for checks
- [x] Exception types are narrowed where safe; validator callouts remain broad
- [x] All existing tests pass (822 passed)
