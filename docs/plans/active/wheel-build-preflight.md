---
slug: wheel-build-preflight
status: approved
owner: makutaku
created: 2026-05-03
related-pr: 99 100
---

# Plan — Pre-tag wheel-build validator

## Context

The v0.5.0a2 release cycle required two CI-on-tag-push hotfixes (PRs #99 and #100) that local CI did not catch:

1. `scripts/check_package_contents.py` had hardcoded `kanon/` paths in its `_CORE_REQUIRED_FILES` after the kernel-rename. The unit tests in `tests/scripts/test_check_package_contents.py` built synthetic wheels with the same hardcoded prefix and were internally consistent — but disconnected from the real `pyproject.toml`-driven wheel.
2. `[tool.hatch.build.targets.sdist].include` was missing `src/kanon_reference`, so `python -m build` (sdist+wheel pipeline as run by `release.yml`) shipped only `kernel/` + a few README.md files. Direct `python -m build --wheel` (which I used for local validation) bypasses the sdist filter and produced a complete wheel — masking the bug until the actual tag push.

The lesson: the validator must run against the **actual** sdist+wheel built via `python -m build` (CI's exact pipeline), not against synthetic wheels built in tests' `tmp_path`.

## Goal

A pre-tag check that any developer can run locally, and that the `release-checklist` protocol gates on:

```
$ make wheel-check
[1/3] cleaning dist/
[2/3] building sdist + wheel via python -m build
[3/3] validating wheel against tag v0.5.0a3
status: ok
```

Integrate into:
- `Makefile` target `wheel-check`
- `.kanon/config.yaml` preflight-stages `release:` (a second check after the version-match one)

When the next ADR-0049 §1(7) (`aspects/` flatten) or any other `pyproject.toml` build-config change happens, this check fails locally before the tag push.

## Acceptance criteria

- AC1: `scripts/check_wheel_build.py` exists, takes `--tag vX.Y.Z`, builds a fresh sdist+wheel into `dist/`, runs `check_package_contents.py` against the produced wheel, returns exit 0 on success and clear non-zero on any phase's failure.
- AC2: Output is JSON-readable on success (single object: `{"ok": true, "wheel": "...", "validation": {...}}`) — same shape as `release-preflight.py` for consistency.
- AC3: `make wheel-check` invokes the script with a placeholder tag derived from `kernel.__version__` (so `make wheel-check` works without arguments for the dev-loop case).
- AC4: `.kanon/config.yaml` preflight-stages `release:` gains a `wheel-build-validate` step that runs the script with `--tag $TAG`.
- AC5: Tests at `tests/scripts/test_check_wheel_build.py` exercise the success path (against this repo's actual build) AND a failure path (corrupt the script's input to assert exit non-zero with diagnostic message).
- AC6: Builds use `uv tool run --from build python -m build` to avoid requiring `build` to be in the project's deps (the build environment is isolated per PEP 517).
- AC7: All standalone gates green; full pytest passes.

## Steps

1. Author `scripts/check_wheel_build.py` (~80 LOC).
2. Wire `Makefile` `wheel-check` target.
3. Add the `wheel-build-validate` step to `.kanon/config.yaml` `preflight-stages.release`.
4. Author `tests/scripts/test_check_wheel_build.py` (~60 LOC, 2-3 test cases).
5. Run `make wheel-check` locally end-to-end against the current `kernel.__version__` (0.5.0a2).
6. Run all gates + pytest.
7. Commit, push, PR, auto-merge.

## Out of scope

- Changing `release.yml` to invoke this script as a separate stage. The CI workflow already runs the moral-equivalent validation via the existing `Validate wheel contents against tag` step. This script is for the **local pre-tag** flow — close the gap that bit us in PRs #99/#100.
- Auto-detecting tag (the script accepts `--tag` arg explicitly; the Makefile convenience target derives from `kernel.__version__`).
- Smoke-installing the produced wheel into a clean venv (separate concern; `release-checklist` Step 6 covers post-publish).

## Risks

- `uv tool run --from build python -m build` requires network access on the first invocation (to install build's deps). Mitigation: document in the script's docstring; add a `--no-network` flag that fails clearly if isolated build env is unavailable.
- The build is slow (~2 minutes). Acceptable for a pre-tag gate; not for a per-commit gate.
- A stale `dist/` directory could mask issues. Script wipes `dist/` at start.
