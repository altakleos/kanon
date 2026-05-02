---
status: approved
slug: phase-a.7-cli-verbs
date: 2026-05-02
design: docs/design/resolutions-engine.md
---

# Plan: Phase A.7 — CLI verbs (`kanon resolutions check`, `kanon contracts validate`, plus `resolve` / `explain` stubs)

## Context

Per [ADR-0045](../../decisions/0045-de-opinionation-transition.md) §Decision step 7. The substrate's user surface for the contract-resolution + dialect-grammar + composition machinery (Phase A.6a/b/c/d). Per the resolutions design and dialect-grammar design.

CLI verbs to add:

- `kanon resolutions check [--target PATH]` — fully-implemented; wraps `_resolutions.stale_check`
- `kanon contracts validate [--bundle PATH]` — fully-implemented; wraps `_dialects.validate_dialect_pin` + `_realization_shape.parse_realization_shape` + `_composition.compose`
- `kanon resolve [--target PATH] [--contracts SLUG[,SLUG...]]` — **stub**; emits a structured prompt to stderr explaining that real harness integration awaits a future ADR
- `kanon resolutions explain <CONTRACT-ID>` — **stub**; emits a placeholder explaining that the contract registry doesn't exist yet

The two stub verbs surface as commands users can invoke, but defer their actual integration. This makes the CLI shape complete (publishers and consumers know the verbs exist) while honestly acknowledging the work remaining.

## Scope

### In scope

#### A. `src/kanon/cli.py` extensions (~150 LOC)

Two `click.group`s:

```python
@main.group()
def resolutions() -> None:
    """Resolutions management (per ADR-0039)."""

@resolutions.command("check")
@click.option("--target", ..., default=Path("."))
def resolutions_check(target: Path) -> None:
    """Check .kanon/resolutions.yaml for staleness without executing realizations."""
    report = stale_check(target)
    click.echo(json.dumps({
        "errors": [...], "executions": [], "status": "ok" if report.ok else "fail"
    }, indent=2))
    sys.exit(0 if report.ok else 1)

@resolutions.command("explain")
@click.argument("contract_id")
@click.option("--target", ..., default=Path("."))
def resolutions_explain(contract_id: str, target: Path) -> None:
    """A.7 stub: contract registry not yet populated. Emits placeholder."""
    ...

@main.group()
def contracts() -> None:
    """Contract bundle management (per ADR-0041)."""

@contracts.command("validate")
@click.argument("bundle_path", type=click.Path(exists=True, file_okay=False))
def contracts_validate(bundle_path: str) -> None:
    """Validate a publisher bundle's dialect, realization-shapes, composition."""
    ... # uses _dialects, _realization_shape, _composition

@main.command("resolve")
@click.option("--target", ..., default=Path("."))
@click.option("--contracts", ...)
def resolve(target: Path, contracts: str | None) -> None:
    """A.7 stub: harness integration not yet wired. Emits structured prompt."""
    ...
```

#### B. `tests/test_cli_resolutions.py` + `tests/test_cli_contracts.py` (~200 LOC, ~14 cases)

- `kanon resolutions check`: missing file → exit 0, status ok; clean resolution → exit 0; stale → exit 1
- `kanon contracts validate`: bundle without manifest → error; manifest with bad dialect → error; manifest with missing realization-shape → error; clean bundle → status ok
- `kanon resolve` stub: emits "harness integration deferred"; exit 0
- `kanon resolutions explain` stub: emits "contract registry deferred"; exit 0

#### C. CHANGELOG entry

### Out of scope

- Real harness integration for `kanon resolve`
- Real contract-registry lookup for `kanon resolutions explain`
- Wiring composition/realization-shape into substrate runtime
- Migration of aspect manifests to declare `kanon-dialect:` / `realization-shape:` (separate sub-plan)

## Acceptance criteria

- [ ] AC-M1: `src/kanon/cli.py` exposes `kanon resolutions check`, `kanon resolutions explain`, `kanon contracts validate`, `kanon resolve` verbs
- [ ] AC-M2: `kanon resolutions check` returns `status: ok` for clean / missing resolution; `status: fail` exit 1 for stale
- [ ] AC-M3: `kanon contracts validate <missing>` errors; `kanon contracts validate <valid-empty-bundle>` returns ok
- [ ] AC-M4: `kanon resolve` and `kanon resolutions explain` exit 0 with stub messaging
- [ ] AC-T1: ≥10 tests passing across two new test files
- [ ] AC-X1..X8: standard gates green; full pytest no regression
