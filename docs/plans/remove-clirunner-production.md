# Plan: Remove CliRunner from Production Code

## Problem

`click.testing.CliRunner` is used in two production code paths in `cli.py`:

1. **`preflight()`** (line ~560) — invokes `kanon verify <target>` via CliRunner
2. **`release_cmd()`** (line ~700) — invokes `kanon preflight <target> --stage release --tag <tag>` via CliRunner

`CliRunner` is a **test utility** that:
- Swallows exceptions (catches all, returns exit_code)
- Captures stdout/stderr (hides output from the user)
- Alters `sys.exit` behavior
- Creates an isolated Click context that may not inherit parent state

Both usages only check `exit_code == 0` for pass/fail — they don't use captured output.

## Solution

Replace CliRunner with `click.Context.invoke()` wrapped in `try/except SystemExit`:

### Change 1: `preflight()` — replace CliRunner verify invocation

```python
# Before:
from click.testing import CliRunner as _Runner
_vr = _Runner().invoke(main, ["verify", str(target)])
verify_passed = _vr.exit_code == 0

# After:
try:
    ctx.invoke(verify, target=target)
    verify_passed = True
except SystemExit as e:
    verify_passed = (e.code == 0 or e.code is None)
```

The `preflight` function needs `@click.pass_context` to access `ctx`.

### Change 2: `release_cmd()` — replace CliRunner preflight invocation

```python
# Before:
from click.testing import CliRunner as _Runner
pf = _Runner().invoke(main, ["preflight", str(target), "--stage", "release", "--tag", tag])
if pf.exit_code != 0:

# After:
try:
    ctx.invoke(preflight, target=target, stage="release", tag=tag, fail_fast=False)
    preflight_passed = True
except SystemExit as e:
    preflight_passed = (e.code == 0 or e.code is None)

if not preflight_passed:
```

The `release_cmd` function needs `@click.pass_context` to access `ctx`.

## Acceptance Criteria

1. `CliRunner` import is removed from both functions (no production usage remains)
2. `preflight` command still runs verify and reports pass/fail with timing
3. `release` command still gates on preflight pass/fail
4. Existing tests pass (`pytest`)
5. Manual smoke test: `kanon preflight . --stage commit` produces same behavior

## Files Modified

- `packages/kanon-core/src/kanon_core/cli.py` — both changes in one file

## Risk

Low — both call sites only use exit_code for boolean pass/fail. The replacement preserves identical semantics. `ctx.invoke()` is Click's documented way to call sibling commands.
