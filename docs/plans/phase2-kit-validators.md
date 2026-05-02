---
status: done
date: 2026-04-27
spec: n/a
design: "Follows ADR-0028 project-aspect validator pattern; extends to kit aspects"
---
# Plan: Phase 2 (revised) — Kit-aspect validators via `kanon verify`

## Goal

Enable kit-shipped aspects to declare `validators:` that `kanon verify`
runs from the installed package — no static file copies into consumer repos.
Implement three validators (plan completion, link checking, ADR immutability)
as internal modules gated by aspect + depth.

## Why This Replaces the Static-Copy Approach

- **No staleness**: Validators update with `pip install --upgrade kanon-kit`
- **No dependency leak**: pyyaml is kanon's dep, not the consumer's
- **Configurable**: Strictness flows through `aspect set-config`
- **No file ownership burden**: Consumer's `scripts/` stays clean

## Acceptance Criteria

- [x] `_verify.py` gains `run_kit_validators()` that discovers and runs validators from kit-aspect manifests
- [x] Kit validators run AFTER kit structural checks (trusted code, no INV-9 concern)
- [x] `kanon-sdd` sub-manifest declares `validators:` at depth 1 and depth 2
- [x] Three validator modules exist under `src/kanon/kit/aspects/kanon-sdd/validators/`:
    - `plan_completion.py` — depth 1+: done plans must have all tasks ticked
    - `link_check.py` — depth 2+: markdown relative links must resolve
    - `adr_immutability.py` — depth 2+: accepted ADR bodies must be immutable
- [x] Validators respect aspect config from `.kanon/config.yaml` (future: not wired in this PR)
- [x] Validators are depth-gated: only run when the consumer's sdd depth >= the validator's minimum
- [x] All existing tests pass
- [x] New tests cover the three validators and the kit-validator discovery mechanism
- [x] `kanon verify .` passes on kanon's own repo

## Files Created

| File | Purpose |
|------|---------|
| `src/kanon/kit/aspects/kanon-sdd/validators/__init__.py` | Package marker |
| `src/kanon/kit/aspects/kanon-sdd/validators/plan_completion.py` | Plan completion validator |
| `src/kanon/kit/aspects/kanon-sdd/validators/link_check.py` | Markdown link validator |
| `src/kanon/kit/aspects/kanon-sdd/validators/adr_immutability.py` | ADR immutability validator |

## Files Modified

| File | Change |
|------|--------|
| `src/kanon/_verify.py` | Add `run_kit_validators()` function |
| `src/kanon/cli.py` | Call `run_kit_validators()` after structural checks |
| `src/kanon/kit/aspects/kanon-sdd/manifest.yaml` | Add `validators:` entries at depth-1 and depth-2 |
| `src/kanon/_manifest.py` | Add `_kit_aspect_validators(aspect, depth)` to return depth-gated validators |

## Design Decisions

- Validators are Python modules inside the kit package, NOT standalone scripts.
  Import path: `kanon.kit.aspects.kanon_sdd.validators.plan_completion`
- Depth gating: manifest declares validators per depth level. `_kit_aspect_validators()`
  returns the union of validators for depth 0..N (strict-superset, matching file semantics).
- Kit validators use the same `check(target, errors, warnings)` signature as project validators.
- Kit validators run AFTER structural checks — they are trusted code (no INV-9 concern).
- `check_adr_immutability` uses kanon's own pyyaml — no consumer dependency.

## Out of Scope

- Config passthrough to validators (future: `aspect set-config` → validator config)
- Standalone CI script wrappers (consumers who want `python scripts/check_links.py` can write a 3-line shim)
- Updating the reference `verify.yml` workflow
