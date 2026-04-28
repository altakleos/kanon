---
status: done
---
# Plan: Close Test Coverage Gaps

## Goal

Add missing tests for:
1. The `upgrade` CLI command (currently untested in `test_cli.py`)
2. CI scripts `check_foundations.py`, `check_links.py`, `check_package_contents.py` (no test files)

## Out of Scope

- Pre-commit hooks (deferred to dev-process pipeline)
- `cli.py` monolith decomposition (separate effort)

---

## Task 1: `upgrade` CLI Command Tests

**File:** `tests/test_cli.py` (append to existing)

**Test cases:**

| Test | Setup | Assert |
|------|-------|--------|
| `test_upgrade_bumps_version` | Init at tier 1, patch config to old version | exit 0, config has current `__version__`, output mentions version transition |
| `test_upgrade_already_current` | Init at tier 1 (already current version) | exit 0, output contains "Already at" |
| `test_upgrade_not_a_kanon_project` | Empty tmp_path (no `.kanon/config.yaml`) | exit != 0, error mentions "Not a kanon project" |
| `test_upgrade_malformed_config` | Write non-dict YAML to `.kanon/config.yaml` | exit != 0, error mentions "Malformed" |
| `test_upgrade_legacy_v1_migration` | Init, rewrite config with `tier: N` key (no `aspects:`), old version | exit 0, config migrated to aspects format, version bumped |
| `test_upgrade_preserves_user_content` | Init, append custom section to AGENTS.md, patch old version, upgrade | AGENTS.md still contains custom section |
| `test_upgrade_creates_agents_md_if_missing` | Init, delete AGENTS.md, patch old version, upgrade | AGENTS.md recreated |

**Pattern:** Same as existing tests — `CliRunner`, `tmp_path`, init first then test.

---

## Task 2: CI Script Tests

Three new test files following the `test_check_kit_consistency.py` pattern.

### 2a. `tests/ci/test_check_foundations.py`

| Test | What |
|------|------|
| `test_real_repo_passes` | Run against actual repo foundations + specs, assert no errors |
| `test_main_exits_zero_on_ok` | Call `main()` with repo paths, check rc=0 and JSON status="ok" |
| `test_missing_foundation_ref` | Create spec referencing non-existent foundation slug, assert error |
| `test_invalid_principle_kind` | Create principle with bad `kind:`, assert error |

### 2b. `tests/ci/test_check_links.py`

| Test | What |
|------|------|
| `test_real_repo_passes` | Run against actual repo docs, assert no broken links |
| `test_main_exits_zero_on_ok` | Call `main()` with repo docs path, check rc=0 and JSON status="ok" |
| `test_broken_link_detected` | Create md file with broken relative link, assert error returned |
| `test_external_links_skipped` | Create md file with `https://` link, assert no error |
| `test_code_block_links_skipped` | Create md file with link inside fenced code block, assert no error |

### 2c. `tests/ci/test_check_package_contents.py`

| Test | What |
|------|------|
| `test_valid_wheel_passes` | Build a minimal valid wheel (zipfile with required entries), assert exit 0 |
| `test_missing_required_file` | Wheel missing `kanon/__init__.py`, assert exit 1 |
| `test_forbidden_path_detected` | Wheel containing `docs/something.md`, assert exit 2 |
| `test_version_mismatch` | Wheel `__version__` differs from tag, assert exit 3 |

---

## Execution Order

1. Task 1 — upgrade tests (single file edit, can verify immediately)
2. Task 2a, 2b, 2c — CI script tests (independent, can be parallelized)
3. Run full test suite: `pytest -v`
4. Run linter: `ruff check tests/`
5. Run type checker: `mypy src/kanon`

## Success Criteria

- All new tests pass
- Existing tests still pass
- `ruff check` clean
- `mypy` clean
- Coverage improves (currently 70% threshold)
