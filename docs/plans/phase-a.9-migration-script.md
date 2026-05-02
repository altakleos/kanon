---
status: approved
slug: phase-a.9-migration-script
date: 2026-05-02
design: docs/design/distribution-boundary.md
---

# Plan: Phase A.9 — `kanon migrate v0.3 → v0.4` (deprecated-on-arrival)

## Context

Per [ADR-0045](../decisions/0045-de-opinionation-transition.md) §Decision step 9, per [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md). The substrate's clean-break commitment means there is no backward compatibility shim path; the migration script is the one-time tool that handles the kanon repo's (and any historical v0.3 consumer's) transition from kit-shape to substrate-shape `.kanon/config.yaml`.

**Deprecated-on-arrival:** the script ships with an explicit deprecation comment and a "this will be removed before v1.0" warning to the user. It exists to handle the historical migration; it is not a long-term API.

## Scope

### In scope

#### A. New `kanon migrate` CLI verb (~80 LOC in `src/kanon/cli.py`)

```python
@main.command("migrate")
@click.option("--target", default=Path("."))
@click.option("--dry-run", is_flag=True)
def migrate(target: Path, dry_run: bool) -> None:
    """Migrate `.kanon/config.yaml` from v3 (kit-shape) to v4 (substrate-shape).

    Deprecated-on-arrival per ADR-0045 — this is a one-time migration tool
    for historical v0.3 consumers; it will be removed before v1.0.
    """
```

Behavior:
- If config already has `schema-version: 4` → no-op, exit 0
- If config has v3 shape (no `schema-version`) → add v4 fields:
  - `schema-version: 4`
  - `kanon-dialect: "2026-05-01"`
  - `provenance: [{recipe: "manual-migration", publisher: "kanon-migrate", recipe-version: "1.0", applied_at: <now>}]`
  - Strip retired config keys (e.g., kanon-testing's `test_cmd`/`lint_cmd`/`typecheck_cmd`/`format_cmd`/`coverage_floor` from `aspects.kanon-testing.config`)
- `--dry-run` prints proposed changes without writing
- Emits a deprecation banner: "warning: kanon migrate is deprecated-on-arrival; will be removed before v1.0"

#### B. `tests/test_cli_migrate.py` (~80 LOC, ~7 cases)

- Already-v4 config → no-op
- v3 config → augmented with v4 fields
- `--dry-run` doesn't write
- Stripping retired testing config keys
- Deprecation banner emitted to stderr
- Missing `.kanon/config.yaml` → error
- Empty/malformed config → error

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- Aspect content move
- _kit_root() retirement in _scaffold.py
- substrate-independence CI gate
- Recipe authoring or distribution split (already shipped)

## Acceptance criteria

- [ ] AC-M1: `src/kanon/cli.py` exposes `kanon migrate` verb with `--target` and `--dry-run` flags
- [ ] AC-M2: Already-v4 config → exit 0, no write
- [ ] AC-M3: v3 config → augmented with v4 fields; idempotent (re-running is no-op)
- [ ] AC-M4: Retired kanon-testing config keys stripped
- [ ] AC-M5: `--dry-run` prints diff without writing
- [ ] AC-M6: Deprecation banner emitted
- [ ] AC-T1: ≥7 tests passing
- [ ] AC-X1..X8: standard gates green; full pytest no regression
