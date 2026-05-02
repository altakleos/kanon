---
status: approved
slug: phase-a.5-bare-name-deprecation
date: 2026-05-02
design: docs/design/distribution-boundary.md
---

# Plan: Phase A.5 — Bare-name CLI sugar deprecation

## Context

Per [ADR-0045](../decisions/0045-de-opinionation-transition.md) §Decision step 5: "Bare-name CLI sugar deprecated". Per [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) (de-opinionation, publisher-symmetry): the CLI's bare-name shorthand (`sdd` → `kanon-sdd`) implies that `kanon-` is a privileged namespace at the CLI surface. For protocol-substrate symmetry, this asymmetry violates `P-publisher-symmetry`: an `acme-fintech` aspect has no equivalent shorthand, so the convenience favours the reference publisher.

A.5 deprecates the sugar (warns when a bare name is used at a CLI surface) but does not delete it — that's a future cleanup once consumers and tests have migrated.

## Substrate consumers

`_normalise_aspect_name(raw)` at `src/kanon/_manifest.py:154-168` is the single point where bare names are sugared to `kanon-<raw>`. CLI sites that invoke it:

- `src/kanon/cli.py:697` — `aspect info <name>`
- `src/kanon/cli.py:751` — `aspect add <target> <name>`
- `src/kanon/cli.py:793` — `aspect remove <target> <name>`
- `src/kanon/cli.py:860` — `aspect set-depth <target> <name> <n>`
- `src/kanon/cli.py:870` — `aspect set-config <target> <name> <key=val>`
- `src/kanon/_cli_helpers.py:108, 163` — `--aspects` flag parsing (multi-aspect)

`_BARE_ASPECT_NAME_RE` at `src/kanon/_manifest.py:149` is also used by `src/kanon/_scaffold.py:90, 112` for AGENTS.md marker validation — out of A.5 scope (markers are an internal data shape, not user input).

## Goal

Single PR that:

1. Adds a deprecation warning emission inside `_normalise_aspect_name` whenever a bare name is sugared to a `kanon-` name. Warning goes to stderr (CLI surface), suggesting the user use the full `kanon-<X>` form.
2. Suppresses the warning in non-CLI contexts (e.g., when `_normalise_aspect_name` is called from internal substrate code with already-namespaced input — which is the no-op pass-through path; the warning only fires on actual sugaring).
3. Adds tests asserting the warning fires for bare names and does not fire for namespaced names.
4. Updates the function docstring to mark the sugar as deprecated.
5. CHANGELOG entry under `[Unreleased] § Deprecated`.

## Scope

### In scope

#### A. `_normalise_aspect_name` deprecation

```python
def _normalise_aspect_name(raw: str) -> str:
    """Return the canonical aspect name for *raw*.

    A prefixed name (matching ``_ASPECT_NAME_RE``) passes through unchanged.
    A bare name (matching ``_BARE_ASPECT_NAME_RE``) sugars to ``kanon-<raw>``
    AND emits a deprecation warning on stderr (Phase A.5; per ADR-0048
    publisher-symmetry — bare-name sugar privileges the `kanon-` namespace).

    Other inputs raise :class:`click.ClickException`.
    """
    if _ASPECT_NAME_RE.match(raw):
        return raw
    if _BARE_ASPECT_NAME_RE.match(raw):
        full = f"{_KANON_NAMESPACE}-{raw}"
        click.echo(
            f"warning: bare aspect name {raw!r} is deprecated; "
            f"use the full name {full!r} instead.",
            err=True,
        )
        return full
    raise click.ClickException(...)
```

#### B. Tests

New `tests/test_bare_name_deprecation.py` (or add to `tests/test_aspect_name_normalisation.py` if it exists):
- `test_bare_name_emits_deprecation_warning`: bare `sdd` → returns `kanon-sdd` AND emits stderr warning containing "deprecated"
- `test_namespaced_name_no_warning`: `kanon-sdd` → returns `kanon-sdd` AND emits no warning
- `test_project_name_no_warning`: `project-foo` → returns `project-foo` AND emits no warning

Use Click's `CliRunner` with stderr capture, OR call `_normalise_aspect_name` directly via `click.echo` capture (probably simplest with `pytest`'s `capsys`).

#### C. Audit existing tests

Some tests use bare names (`sdd`, `worktrees`, etc.) at `kanon` CLI invocations:
- `kanon init --aspects sdd:1`
- `kanon aspect add . worktrees`
- etc.

These will now emit deprecation warnings to stderr. Most tests don't capture/assert on stderr beyond exit code, so they'll continue passing — the warning is just additional output. **Action: leave existing tests as-is; the warning is informational.**

If any test asserts on stderr content (e.g., "no extraneous output"), update it to allow the warning.

#### D. CHANGELOG

Paragraph under `[Unreleased] § Deprecated` (NEW section if not present, otherwise append).

### Out of scope

- **Deletion of `_normalise_aspect_name` bare-name path.** Future cleanup; the deprecation warning is the user-visible signal that migration is expected.
- **Aspect content move** — separate sub-plan.
- **`_kit_root()` retirement in `_scaffold.py`** — separate sub-plan.
- **`_BARE_ASPECT_NAME_RE` use in `_scaffold.py:90, 112`** — markers are internal data shape, not user input; not deprecated.
- **No new ADR / spec / design / principle changes.**

## Approach

1. Edit `_normalise_aspect_name` in `_manifest.py` to emit a `click.echo(..., err=True)` warning when sugaring a bare name.
2. Add a `tests/test_bare_name_deprecation.py` with 3 tests (bare→warns; namespaced→silent; project→silent).
3. Run all gates + full pytest. Existing tests should pass (warning is additive stderr noise).
4. Recapture `.kanon/fidelity.lock` if any spec SHAs cascade.
5. CHANGELOG entry under `[Unreleased] § Deprecated`.
6. Commit + push + auto-merge per "when done, merge".

## Acceptance criteria

### Substrate

- [ ] AC-S1: `_normalise_aspect_name(bare_name)` emits a stderr warning containing "deprecated" and the full `kanon-<X>` name.
- [ ] AC-S2: `_normalise_aspect_name(namespaced_name)` (e.g., `kanon-sdd`, `project-foo`) emits no warning.
- [ ] AC-S3: Function still returns the correct sugared name (behaviour preserved).
- [ ] AC-S4: Function docstring updated to mark sugar as deprecated.

### Tests

- [ ] AC-T1: New `tests/test_bare_name_deprecation.py` covers the 3 scenarios above.
- [ ] AC-T2: Full pytest passes (existing tests' stderr assertions, if any, accommodate the new warning).

### CHANGELOG

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Deprecated` gains a paragraph naming Phase A.5.

### Cross-cutting

- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3..X7: standard gates pass (`check_links`, `check_foundations`, `check_kit_consistency`, `check_invariant_ids`, `check_packaging_split`, `check_verified_by`).
- [ ] AC-X8: No `src/kanon_reference/` change.
- [ ] AC-X9: No aspect content moved.
- [ ] AC-X10: `_normalise_aspect_name`'s sugar path still functions (only warns; doesn't fail).

## Risks / concerns

- **Risk: a real user (or downstream tool) parses `kanon` CLI stderr and breaks on the warning.** Mitigation: the warning is single-line, prefixed `warning:` — standard for CLI tools. Stderr is conventionally informational; tools that parse exit-code-only continue to work.
- **Risk: tests emit massive stderr noise** (every bare-name use in 800+ tests now emits). Mitigation: stderr is suppressed by pytest's default capture; this is cosmetic, not a failure.
- **Risk: tests that explicitly assert stderr content break.** Audit during implementation; update assertions if needed.
- **Risk: the deprecation warning loops** (e.g., `kanon aspect set-config` parses bare names twice — once in CLI, once in `set_config_pair_*`). Mitigation: review all 7 call sites; ensure deduplication isn't needed (single warning per CLI invocation is fine; multiple is acceptable but noisy).

## Documentation impact

- **Touched files:** `src/kanon/_manifest.py` (single function); `CHANGELOG.md`.
- **New files:** `docs/plans/phase-a.5-bare-name-deprecation.md`, `tests/test_bare_name_deprecation.py`.
- **No changes to:** `src/kanon_reference/`, aspect manifests, specs, designs, ADRs, foundations, principles, top-level `pyproject.toml`, other source files.
