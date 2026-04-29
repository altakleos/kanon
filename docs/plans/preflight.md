---
status: draft
serves: docs/specs/preflight.md
design: docs/design/preflight.md
touches:
  - src/kanon/cli.py
  - src/kanon/_preflight.py
  - src/kanon/kit/aspects/kanon-testing/manifest.yaml
  - src/kanon/kit/aspects/kanon-security/manifest.yaml
  - src/kanon/kit/aspects/kanon-release/manifest.yaml
  - tests/test_preflight.py
---

# Plan: Implement `kanon preflight`

## Tasks

- [ ] T1: Create `src/kanon/_preflight.py` with:
  - `_resolve_preflight_checks(aspects, config, stage)` — the
    resolution algorithm from the design doc
  - `_run_preflight(target, checks, fail_fast)` — subprocess runner
    with structured output
- [ ] T2: Add `preflight` Click command to `cli.py`
- [ ] T3: Add `config-schema` keys (`test_cmd`, `lint_cmd`,
  `typecheck_cmd`, `format_cmd`) to kanon-testing manifest
- [ ] T4: Add `preflight:` entries to kanon-testing, kanon-security,
  and kanon-release manifests
- [ ] T5: Update `_load_aspect_manifest()` to accept optional
  `preflight:` key in depth-N blocks
- [ ] T6: Add tests in `tests/test_preflight.py`
- [ ] T7: Self-host: configure preflight for the kanon repo itself

## Acceptance criteria

1. `kanon preflight . --stage commit` runs verify + configured
   commit-stage checks.
2. `kanon preflight . --stage push` runs commit + push checks.
3. `kanon preflight . --stage release --tag v1.0` runs all stages.
4. Empty `*_cmd` config values are skipped (not errors).
5. Consumer `preflight-stages:` overrides aspect defaults by label.
6. JSON output to stdout, human output to stderr.
7. `--fail-fast` stops on first failure.
8. All existing tests pass.
