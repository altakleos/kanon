---
status: done
date: 2026-04-30
adr: ../decisions/0036-secure-defaults-config-trust-carveout.md
---
# Plan: Preflight shell-trust-boundary carve-out

## Problem

`src/kanon/_preflight.py:96` runs `subprocess.run(cmd, shell=True, ...)` against commands sourced from `.kanon/config.yaml`. The kit-shipped `secure-defaults` protocol (`src/kanon/kit/aspects/kanon-security/protocols/secure-defaults.md:25`) forbids the pattern: *"Use subprocess APIs with argument lists, not shell=True with interpolated strings."* The kit prescribes a rule its own runtime breaks — a self-violation surfaced by the v0.3 audit.

## Why a refactor is rejected

Consumer commands rely on shell features. The kanon repo's own release-stage check uses `$TAG` env-var expansion through the shell:

```yaml
- run: .venv/bin/python -c "import kanon; v='$TAG'.lstrip('v'); ..."
```

Stripping `shell=True` (refactoring to `subprocess.run(shlex.split(cmd), ...)`) silently breaks any consumer using `&&`, pipes, redirection, or env-var expansion. The behavior break is uncalibrated: existing consumer configs would stop working without warning.

## Approach (Path A — protocol carve-out)

The trust boundary for preflight commands is *write-access to `.kanon/config.yaml`*. An attacker with that already owns the repo. The protocol prose was overbroad; the ADR-lite at `0036-secure-defaults-config-trust-carveout.md` records the boundary explicitly. The protocol gains a paragraph; the call site gains a `# nosec` comment naming the carve-out.

## Tasks

- [x] T1: Author `docs/decisions/0036-secure-defaults-config-trust-carveout.md` (ADR-lite).
- [x] T2: Index ADR-0036 in `docs/decisions/README.md`.
- [x] T3: Amend `src/kanon/kit/aspects/kanon-security/protocols/secure-defaults.md` with a "Trust-boundary carve-outs" subsection citing ADR-0036.
- [x] T4: Mirror the amendment to `.kanon/protocols/kanon-security/secure-defaults.md` (byte-equality enforced by `check_kit_consistency`).
- [x] T5: Add `# nosec` comment at `src/kanon/_preflight.py:96` referencing ADR-0036.
- [x] T6: Index this plan in `docs/plans/README.md`.
- [x] T7: Append a `## [Unreleased]` entry to `CHANGELOG.md`.
- [x] T8: `kanon verify .`, `ruff check`, full pytest — all clean.

## Acceptance criteria

- [x] Protocol prose carves out same-repo config commands explicitly.
- [x] Kit + namespaced protocol copies stay byte-equal.
- [x] `_preflight.py:96` carries a `# nosec` comment naming the carve-out.
- [x] ADR-0036 (lite) authored, indexed, dated.
- [x] `kanon verify` clean; `ruff` clean; `pytest` clean.

## Out of scope

- Extending `scripts/check_security_patterns.py` to honor an inline rationale annotation. Worth a follow-up plan once a second carve-out call site emerges.
- Refactor of `_preflight.py` to argv form. Rejected per Approach above.

## Addendum: process-gates regression fix (in-scope per user direction)

While running the AC pytest suite, 7 tests in `tests/scripts/test_check_process_gates.py` were failing locally. Root cause: `scripts/check_process_gates.py:_diff_content` calls `git diff` without `--no-ext-diff`, so a developer-environment `diff.external` setting (e.g., `difft`, `delta`) strips the `+` markers the `_CLI_DECORATOR` regex scans for, producing silent false negatives. CI was unaffected because the GitHub Actions runner has no `diff.external` configured.

Fix: add `--no-ext-diff` to the two `git diff` invocations in `_diff_content`. The other `_git` callers in the file use `--name-only` or `--format=`, neither of which is affected by `diff.external`.

- [x] T9: `scripts/check_process_gates.py:_diff_content` invokes `git diff --no-ext-diff`.
- [x] T10: `pytest tests/scripts/test_check_process_gates.py` — all 25 tests pass.
