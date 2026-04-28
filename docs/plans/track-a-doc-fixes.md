---
status: done
design: "Follows existing patterns — prose corrections only"
---

# Plan: Track A documentation/config fixes

Three factual inaccuracies found during SOP audit. All are prose or config
corrections — no behavioral changes.

## Fix 1: Coverage floor contradiction (config.yaml 80% vs pyproject.toml 90%)

- `.kanon/config.yaml` declares `coverage_floor: 80`
- `pyproject.toml` enforces `--cov-fail-under=90`
- The pyproject.toml value is what actually runs. Update config.yaml to `90`.

Files: `.kanon/config.yaml`

## Fix 2: False claim about check_test_quality.py

AGENTS.md and the kit bundle say the script "validates test quality (no empty
tests, no assert-True-only, coverage floor)." The script does not check
coverage — that's pytest's `--cov-fail-under`. Remove the false claim.

Files: `AGENTS.md`, `src/kanon/kit/aspects/kanon-testing/agents-md/depth-3.md`

## Fix 3: "no CI gate" for commit messages is false

AGENTS.md says "Convention only, no CI gate" but `check_commit_messages.py`
runs in verify.yml (soft/warn-only). Update to reflect reality.

Files: `AGENTS.md`, `src/kanon/kit/agents-md-base.md`

## Acceptance criteria

- [ ] config.yaml coverage_floor matches pyproject.toml (90)
- [ ] check_test_quality.py description no longer mentions coverage floor
- [ ] Commit message convention text accurately describes the soft CI check
- [ ] Kit bundle files match their AGENTS.md counterparts (check_kit_consistency passes)
