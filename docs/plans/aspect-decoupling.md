# Plan: Aspect Decoupling

Spec at `docs/specs/aspect-decoupling.md` has been approved.

## Goal

Remove all hardcoded `sdd` references from Python source. Make aspects truly data-driven.

## Phases

### Phase 1: AGENTS.md base template (Invariant 3)
- Create `src/kanon/kit/agents-md-base.md` with aspect-neutral skeleton
- Update `_assemble_agents_md()` in `_scaffold.py` to use base template instead of sdd's depth-N.md
- Existing sdd depth templates become section-content-only (their agents-md/ files may become unused or repurposed)
- Verify: `kanon init --tier 1`, `kanon verify`, all tests pass

### Phase 2: Generic init (Invariant 2)
- Add `--aspects` flag to `kanon init` in `cli.py`
- Add `defaults:` key to `src/kanon/kit/manifest.yaml`
- Preserve `--tier N` as sugar for `--aspects sdd:N`
- Remove hardcoded `aspects_to_enable = {"sdd": depth}` from init
- Verify: `kanon init --aspects sdd:1,worktrees:1`, `kanon verify`

### Phase 3: aspect add / aspect remove (Invariant 4)
- Add `aspect add` and `aspect remove` commands to `cli.py`
- `add`: enable at default-depth, enforce requires
- `remove`: delete config entry, remove AGENTS.md markers, leave files
- Verify: `kanon aspect add worktrees`, `kanon aspect remove worktrees`

### Phase 4: requires enforcement (Invariant 5)
- Add dependency predicate parser (grammar: `<aspect> <op> <depth>`)
- Wire into `_set_aspect_depth`, `aspect add`, `aspect remove`
- Verify: `kanon aspect add worktrees` fails without sdd >= 1

### Phase 5: Generic placeholders (Invariant 7)
- Replace `${tier}` with `${sdd_depth}` in kit.md and agents-md templates
- Update `_render_placeholder` context to use `${<aspect>_depth}` pattern
- Preserve `${tier}` as backward-compat alias
- Verify: kit.md renders correctly

### Phase 6: Manifest-driven CI (Invariant 6)
- Update `check_package_contents.py` to read manifest for required paths
- Add `byte-equality:` key to sdd sub-manifest
- Update `check_kit_consistency.py` to read from sub-manifests
- Verify: CI scripts pass, `grep -rE "'sdd'|\"sdd\"" ci/` returns zero

### Phase 7: Clean sweep (Invariant 1)
- Remove remaining sdd literals from `_scaffold.py` (legacy migration behind version guard)
- Remove sdd literals from `cli.py` (tier command wiring)
- Final verification: `grep -rE "'sdd'|\"sdd\"" src/kanon/ ci/` returns zero outside version guards
- Full test suite, CI scripts, kanon verify

## Success Criteria

- `grep -rE "'sdd'|\"sdd\"" src/kanon/ ci/` returns zero results outside version-guarded legacy migration
- `kanon init --aspects worktrees:1` works (no sdd required)
- `kanon aspect add/remove` work with requires enforcement
- All existing tests pass
- Coverage stays above 90%
- `kanon verify .` passes on self-hosted repo
